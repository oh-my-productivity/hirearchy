"""``KiroRunCommandBuilder``: the command line, directory and environment of one agent run."""

from __future__ import annotations

from pathlib import Path
from typing import cast

from ..access import AccessScopes, ModelResolver
from ..agents import CharterReader
from ..kernel import Environment, OrgLayout
from .api import FILE_TOOLS, ProfileProvisioner, RunCommand, RunCommandBuilder


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
        tools = list(cast("list[str]", meta.get("tools") or []))
        # An agent with built-in read/write gets a profile that confines them by path. The one exception is a legacy
        # charter (built-in `read` only, no workspace, no `inputs` key), which keeps the unconfined profile it always had.
        legacy = "write" not in tools and self._scopes.unconfined_read(meta)
        if set(tools) & set(FILE_TOOLS) and not legacy:
            profile = self._provisioner.ensure_profile(
                tools, workspace=self._scopes.workspace_of(addr), inputs=self._scopes.inputs_of(addr), confine=True
            )
        else:
            profile = self._provisioner.ensure_profile(tools)
        cmd = [self._kiro_bin, "chat", "--no-interactive", "--agent", profile]
        cmd += ["--model", self._models.model_for(addr)]  # always explicit: charter model > org default_model > DEFAULT_MODEL
        # The prompt is not an argument: it can be arbitrarily long (E2BIG) and visible in `ps`.
        # `kiro-cli chat --no-interactive` without INPUT reads it from stdin; the scheduler feeds it there.
        ws = meta.get("workspace")
        cwd = Path(cast(str, ws)).expanduser() if ws else self._layout.agent_dir(addr)
        env = {**self._environment.variables(), "ORG_ROOT": str(self._layout.root), "ORG_AGENT": addr}
        return RunCommand(tuple(cmd), cwd, env)
