"""The launcher of the dashboard: opens the queries of an organization and hands them to the screen."""

from __future__ import annotations

from pathlib import Path

from ._ports import DashboardQueries, QueriesOpener, ScreenRunner
from .api import DashboardLauncher


class TextualDashboardLauncher(DashboardLauncher):
    """RED skeleton."""

    def __init__(self, opener: QueriesOpener, screens: ScreenRunner) -> None:
        raise NotImplementedError("red: D-dashboard")

    def run_dashboard(self, root: Path, interval: float = 2.0) -> None:
        raise NotImplementedError("red: D-dashboard")


class TextualScreenRunner(ScreenRunner):
    """RED skeleton."""

    def run(self, queries: DashboardQueries, interval: float) -> None:
        raise NotImplementedError("red: D-dashboard")
