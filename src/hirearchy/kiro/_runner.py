"""``KiroRunCommandBuilder``: the command line, directory and environment of one agent run."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import cast

from ..access import AccessScopes, ModelResolver
from ..agents import CharterReader
from ..kernel import Environment, OrgLayout
from .api import CHARTER_TOOLS, KiroRunRefused, ProfileProvisioner, RunCommand, RunCommandBuilder


def _tools_of(meta: Mapping[str, object]) -> list[str]:
    """The charter's ``tools``: none when missing, else a list of strings (anything else refuses the run)."""
    tools = meta.get("tools") or []
    if not isinstance(tools, list) or not all(isinstance(t, str) for t in tools):
        raise KiroRunRefused(f"kiro: the charter's tools must be a list of names ({', '.join(CHARTER_TOOLS)})")
    return list(tools)


class KiroRunCommandBuilder(RunCommandBuilder):
    def __init__(
        self, kiro_bin: str, layout: OrgLayout, charters: CharterReader, scopes: AccessScopes, models: ModelResolver,
        provisioner: ProfileProvisioner, environment: Environment,
    ) -> None:
        self._kiro_bin = kiro_bin
        self._layout = layout
        self._charters = charters
        self._scopes = scopes
        self._models = models
        self._provisioner = provisioner
        self._environment = environment

    def build(self, addr: str, prompt: str) -> RunCommand:
        meta, _ = self._charters.charter(addr)
        tools = _tools_of(meta)
        profile = self._provisioner.ensure_profile(tools, workspace=self._scopes.workspace_of(addr), inputs=self._scopes.inputs_of(addr))
        cmd = [self._kiro_bin, "chat", "--no-interactive", "--agent", profile]
        cmd += ["--model", self._models.model_for(addr)]  # always explicit: charter model > org default_model > DEFAULT_MODEL
        # The prompt is not an argument: it can be arbitrarily long (E2BIG) and visible in `ps`.
        # `kiro-cli chat --no-interactive` without INPUT reads it from stdin; the scheduler feeds it there.
        ws = meta.get("workspace")
        cwd = Path(cast(str, ws)).expanduser() if ws else self._layout.agent_dir(addr)
        env = {**self._environment.variables(), "ORG_ROOT": str(self._layout.root), "ORG_AGENT": addr}
        return RunCommand(tuple(cmd), cwd, env)
