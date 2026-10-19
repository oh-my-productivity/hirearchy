"""The Textual app of the dashboard."""

from __future__ import annotations

from textual.app import App
from textual.pilot import Pilot

from ._ports import DashboardQueries


class DashApp(App[None]):
    """RED skeleton."""

    def __init__(self, queries: DashboardQueries, interval: float = 2.0) -> None:
        raise NotImplementedError("red: D-dashboard")

    data: DashboardQueries
    interval: float
    selected: str
    refreshes: int
    last_error: str | None
    flow_open: str | None

    async def settle(self, pilot: Pilot[None] | None = None) -> None:
        raise NotImplementedError("red: D-dashboard")
