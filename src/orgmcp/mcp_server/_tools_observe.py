"""The root-only, read-only tool ``observe``."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..kernel import Provider
from ..observability import ObservabilityText
from ._ports import ToolGroup

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP


class ObservabilityTools(ToolGroup):
    def __init__(self, text: Provider[ObservabilityText]) -> None:
        self._text = text

    def register(self, mcp: FastMCP, me: str) -> None:
        @mcp.tool()
        def observe(view: str = "now", target: str | None = None, since: str = "24h", by: str | None = None,
                    errors_only: bool = False, limit: int = 50) -> str:
            """Read-only look at how the organization is running. view=
        "now": what runs, what is queued and why, what waits on you, errors of the last 15 min.
        "trace" (target=root task id): every message, run, tool call and refusal of one request, with time spent
        queued, running and waiting on you. "metrics" (since=15m|24h|7d|ISO, by=agent|tool|service|trace): runs,
        failures, refusal rates, latency percentiles, budget spent. "events" (target=agent, trace id or kind,
        errors_only): the raw record. "check": is the runtime consistent (budget, messages, stuck runs)?"""
            return self._text().observe_text(view, target, since, by, errors_only, limit)
