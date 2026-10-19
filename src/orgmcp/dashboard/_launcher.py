"""The launcher of the dashboard: opens the queries of an organization and hands them to the screen."""

from __future__ import annotations

from pathlib import Path

from ._app import DashApp
from ._ports import DashboardQueries, QueriesOpener, ScreenRunner
from .api import DashboardLauncher


class TextualDashboardLauncher(DashboardLauncher):
    """Opens the queries of the organization at ``root`` and puts them on the screen. What is not an organization is refused by the opener, before the screen is
    taken (the terminal is not switched to the full-screen mode for an error)."""

    def __init__(self, opener: QueriesOpener, screens: ScreenRunner) -> None:
        self._opener = opener
        self._screens = screens

    def run_dashboard(self, root: Path, interval: float = 2.0) -> None:
        self._screens.run(self._opener.open(Path(root)), interval)


class TextualScreenRunner(ScreenRunner):
    """The screen is a Textual app (``DashApp``) on the queries: it takes over the terminal until the user quits. Making the app is this class's job, it is
    what it exists to run."""

    def run(self, queries: DashboardQueries, interval: float) -> None:
        DashApp(queries, interval).run()
