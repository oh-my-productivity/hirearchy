"""``create_org``: the one tool a root server offers before an organization exists."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ._ports import ToolGroup
from .api import OrgBindingPort

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP


class RootSetupTools(ToolGroup):
    def __init__(self, binding: OrgBindingPort) -> None:
        self._binding = binding

    def register(self, mcp: FastMCP, me: str) -> None:
        @mcp.tool()
        def create_org(mission: str, default_model: str | None = None, path: str | None = None) -> str:
            """Create the organization this server is bound to (only possible while none exists).

        mission: what the organization is for, in a few sentences. default_model: kiro model for all agents
        (optional; unset = claude-sonnet-5.5). path: absolute directory; only needed (and only accepted) when the server is not bound to
        one by ORG_ROOT. The directory must be missing or empty. Afterwards every tool works, no restart needed.
        """
            self._binding.create(mission, default_model, path)
            return (f"created the organization at {self._binding.location()}. Next: hire a team (hire), give it work (delegate), then "
                    "start() the scheduler. Use only this organization.")
