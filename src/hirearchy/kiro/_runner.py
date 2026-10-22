"""``KiroRunCommandBuilder``: the command line, directory and environment of one agent run (docs/design/kiro-runtime-v3.md 5, 13.2)."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from ..access import AccessScopes, ModelResolver
from ..agents import CharterReader
from ..kernel import Environment, OrgLayout
from ._env import run_environment
from ._placement import placement_problem, readable_places
from ._state import planted_problem
from .api import (
    CHARTER_TOOLS, START_DEADLINE, KiroHomeAudit, KiroPlaces, KiroRunRefused, KiroStateDirs, ProfileProvisioner, RunCommand, RunCommandBuilder,
)

KIRO_FLAGS = ("--v3", "--require-mcp-startup", "--output-format", "stream-json")  # the engine, a hard stop when the MCP server fails, the transcript


def _tools_of(meta: Mapping[str, object]) -> list[str]:
    """The charter's ``tools``: none when missing, else a list of strings (anything else refuses the run)."""
    tools = meta.get("tools") or []
    if not isinstance(tools, list) or not all(isinstance(t, str) for t in tools):
        raise KiroRunRefused(f"kiro: the charter's tools must be a list of names ({', '.join(CHARTER_TOOLS)})")
    return list(tools)


class KiroRunCommandBuilder(RunCommandBuilder):
    """``launcher`` is what comes before the kiro command: the interpreter, its isolation flags and the launcher script."""

    def __init__(
        self, kiro_bin: str, launcher: tuple[str, ...], layout: OrgLayout, charters: CharterReader, scopes: AccessScopes, models: ModelResolver,
        provisioner: ProfileProvisioner, environment: Environment, places: KiroPlaces, dirs: KiroStateDirs, audit: KiroHomeAudit,
    ) -> None:
        self._kiro_bin = kiro_bin
        self._launcher = launcher
        self._layout = layout
        self._charters = charters
        self._scopes = scopes
        self._models = models
        self._provisioner = provisioner
        self._environment = environment
        self._places = places
        self._dirs = dirs
        self._audit = audit

    def build(self, addr: str, prompt: str) -> RunCommand:
        meta, _ = self._charters.charter(addr)
        tools = _tools_of(meta)
        home = self._checked_home(addr)
        profile = self._provisioner.ensure_profile(tools, workspace=self._scopes.workspace_of(addr), inputs=self._scopes.inputs_of(addr))
        scratch = self._places.scratch(addr)
        self._dirs.fresh(scratch)  # kiro loads configuration from its working directory: an empty one holds none
        cmd = [*self._launcher, "--start-deadline", f"{START_DEADLINE:g}", "--"]
        cmd += [self._kiro_bin, "chat", "--no-interactive", "--agent", profile]
        cmd += ["--model", self._models.model_for(addr)]  # always explicit: charter model > org default_model > DEFAULT_MODEL
        cmd += KIRO_FLAGS
        # The prompt is not an argument: it can be arbitrarily long (E2BIG) and visible in `ps`.
        # `kiro-cli chat --no-interactive` without INPUT reads it from stdin; the scheduler feeds it there.
        env = {**run_environment(self._environment.variables(), home), "ORG_ROOT": str(self._layout.root), "ORG_AGENT": addr}
        return RunCommand(tuple(cmd), scratch, env)

    def _checked_home(self, addr: str) -> Path:
        """The kiro home of the organization, made private, once the places, the placement of this agent and the home's contents allow the run."""
        problem = self._places.problem()
        if problem is None:
            problem = placement_problem(self._places.roots(), readable_places(self._layout.root, self._scopes, addr))
        if problem is not None:
            raise KiroRunRefused(f"kiro: {problem}")
        home = self._places.home()
        self._dirs.private_dir(home)
        problem = planted_problem(home, self._audit.planted(home))
        if problem is not None:
            raise KiroRunRefused(f"kiro: {problem}")
        return home
