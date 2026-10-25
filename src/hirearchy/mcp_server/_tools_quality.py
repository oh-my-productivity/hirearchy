"""``quality``: how the work the user asked for has gone (0b 9.1): the cases, the user's verdicts, escapes and their causes, runs, alarms and bar changes."""

from __future__ import annotations

from typing import TYPE_CHECKING

import anyio

from ..kernel import Provider
from ..progress import QualityReport
from ._ports import SetupMode, ToolGroup

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP


class QualityTools(ToolGroup):
    def __init__(self, setup: SetupMode, report: Provider[QualityReport]) -> None:
        self._setup = setup
        self._report = report

    def register(self, mcp: FastMCP, me: str) -> None:
        @mcp.tool()
        async def quality(service: str | None = None) -> str:
            """How the work you asked for has gone, from the files: per service, and for your one-off tasks, the cases; the user's verdicts on first
        deliveries, in their words; escapes (the team reported done, then the user rejected it) with the verifier that signed them off and the
        cause a rule typed; deliveries without a verdict (never counted as accepts) and files not as delivered; runs per case, the user's against
        the runs you approved, with top-ups, your own relayed reworks (your own spend) and runs not charged shown apart; blocked tasks moved past without a verdict and the runs
        held behind them; two alarms (repeat, cost; tunable defaults) and the timeline of bar changes. Read-only, root only: agents never see it,
        and you never pass these counts to an agent. service: one service's block (default: everything). Use it when the user asks how a service
        or the org is doing, and say what it shows in plain words.
        """
            if self._setup.active():
                return self._setup.state()
            report = self._report()
            return await anyio.to_thread.run_sync(report.quality_text, (service or "").strip() or None)
