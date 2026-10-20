"""What each agent was granted: model, workspace, inputs, tools (access).

The bodies call the ports of ``self.runtime`` (step B-access; ARCHITECTURE.md 5.3 and 6.4); ``default_model`` is the settings'."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

from ..access import unconfined_read as _unconfined_read
from .runtime import OrgRuntime


class AccessMixin:
    """What each agent was granted: model, workspace, inputs, tools (access)."""

    runtime: OrgRuntime

    @property
    def default_model(self) -> str:
        """The org-wide model: the config's ``default_model``, else DEFAULT_MODEL (also for ``null`` or a missing key)."""
        return self.runtime.settings.default_model()

    def model_for(self, addr: str) -> str:
        """The model a run of ``addr`` uses: its charter's ``model``, else the org config's ``default_model``, else DEFAULT_MODEL."""
        return self.runtime.model_resolver.model_for(addr)

    def _check_authority(self, actor: str, tools: Sequence[str], workspace: str | None, inputs: Sequence[str] | None = None) -> None:
        """Authority only narrows down the tree: a parent cannot grant what it does not have."""
        return self.runtime.authority_policy.check_authority(actor, tools, workspace, inputs)

    def workspace_of(self, addr: str) -> Path | None:
        """The agent's workspace (read-write for its built-in tools) as a resolved path, if its charter has one."""
        return self.runtime.access_scopes.workspace_of(addr)

    def inputs_of(self, addr: str) -> list[Path]:
        """The agent's read-only inputs (charter ``inputs``) as resolved paths."""
        return self.runtime.access_scopes.inputs_of(addr)

    @staticmethod
    def unconfined_read(meta: Mapping[str, object]) -> bool:
        """Legacy charter: no workspace and no ``inputs`` key. Its built-in ``read`` is not confined (as before)."""
        return _unconfined_read(meta)

    def _check_inputs(self, inputs: object) -> list[str]:
        """Inputs are absolute paths outside the organization directory (kiro reads them; the org owns its own)."""
        return self.runtime.authority_policy.check_inputs(inputs)

    def readable_roots(self, addr: str) -> list[Path]:
        """Directories outside the org that ``read`` shows to ``addr`` by absolute path: its workspace and inputs, and
        the workspace of every agent in its subtree (so a manager can verify what its team made)."""
        return self.runtime.access_scopes.readable_roots(addr)

    def tool_names(self, addr: str) -> dict[str, str]:
        """The names under which ``addr`` has orgmcp's ``read`` and ``write`` tools.

        kiro exposes MCP tools by their plain names, so a built-in ``read``/``write`` of the same name SHADOWS the orgmcp
        tool (the agent sees only kiro's; studies/F-read-experiment, F2-tool-names). An agent whose charter holds the
        built-in gets orgmcp's tool as ``org_read`` / ``org_write`` instead; everyone else (and root) keeps the plain names.
        """
        return self.runtime.tool_naming.tool_names(addr)
