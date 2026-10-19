"""The legacy surface of the dashboard: the two ways in that the command line and the tests have always used.

``DashApp(root, interval, now)`` was the app that built its own data from a root path; the app of the package is given its queries
(:class:`orgmcp.dashboard._app.DashApp`). The subclass here asks the wiring for the queries of ``root`` and passes them on, so a caller that still says
``DashApp(root, interval=..., now=...)`` gets the same app. ``run_dashboard(root, interval)`` is what ``orgmcp dash`` calls: a thin function over the
``DashboardLauncher`` that the wiring makes.

The composition root's module is looked up late: an entry point may not import ``orgmcp.app`` (the layers contract). Both go with the legacy surface (E3), when the
command line is given a launcher instead of importing this function.
"""

from __future__ import annotations

import importlib
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from ._app import DashApp as _DashApp


def _wire() -> Any:
    return importlib.import_module("orgmcp.app.wire_dashboard")


class DashApp(_DashApp):
    """The app of the organization at ``root`` (``now``: the time it shows, for tests and screenshots)."""

    def __init__(self, root: str | Path, interval: float = 2.0, now: Callable[[], datetime] | None = None):
        super().__init__(_wire().queries_of(root, now), interval)


def run_dashboard(root: str | Path, interval: float = 2.0) -> None:
    """Show the dashboard of the organization at ``root`` full screen until the user quits (``orgmcp dash``)."""
    _wire().dashboard_launcher().run_dashboard(Path(root), interval)
