"""Membership of the team: ``hire`` and ``retire``."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..hierarchy import Hiring, Retirement
from ..kernel import Provider
from ._ports import ToolGroup

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP


class HiringTools(ToolGroup):
    def __init__(self, hiring: Provider[Hiring], retirement: Provider[Retirement]) -> None:
        self._hiring = hiring
        self._retirement = retirement

    def register(self, mcp: FastMCP, me: str) -> None:
        @mcp.tool()
        def hire(
            name: str,
            role: str,
            charter: str,
            model: str | None = None,
            tools: list[str] | None = None,
            can_hire: bool = False,
            max_children: int = 5,
            workspace: str | None = None,
            inputs: list[str] | None = None,
        ) -> str:
            """Create a direct report (only if your charter allows hiring).

        name: lowercase-dashed (becomes the address <you>/<name>). role: a short job title.
        charter: markdown with purpose, responsibilities, decision rights, what to escalate, quality bar.
        model: kiro model id (optional; unset = the organization's default model, claude-sonnet-5.5). tools: kiro built-in tools to grant, only ones you have yourself
        (e.g. "read", "write", "shell"). can_hire: whether the report may build its own team.
        workspace: directory the report works in (must be inside yours).
        inputs: absolute folders the report may only READ (never change); a manager can give only folders inside its
        own inputs or workspace. A report with `read` and no workspace/inputs reads nothing outside the org.
        A new report has no budget until you delegate a task to it.
        """
            addr = self._hiring().hire(me, name, role, charter, model=model, tools=tools or [], can_hire=can_hire,
                                       max_children=max_children, workspace=workspace, inputs=inputs)
            return f"hired {addr}"

        @mcp.tool()
        def retire(name: str, reason: str) -> str:
            """Remove a direct report and its team (name: its short name or full address, e.g. "eng" or "ceo/eng").

        Their open tasks are reported to you as failed, and the team's unspent budget is returned to you.
        """
            r = self._retirement().retire_team(me, name, reason)
            refund = f"; {r.refunded} unspent run(s) of budget returned to {r.refunded_to}" if r.refunded else ""
            return f"retired {r.addr}{refund}"
