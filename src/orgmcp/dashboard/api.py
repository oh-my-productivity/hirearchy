"""The public surface of ``dashboard``: the terminal dashboard of ``orgmcp dash`` (a Textual app) and the launcher that runs it.

Read-only: the dashboard never writes inside the organization and emits no event. It shows what the queries of :mod:`orgmcp.dashdata` answer,
refreshes them in a worker thread (one refresh at a time: the queries share one cache that is not thread-safe) and keeps selection, scroll position
and the folds of the agent tree across refreshes. The widgets, the screens and the app itself are private (``_widgets``, ``_render``, ``_state``,
``_app``): a terminal application is not a service other code calls.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

__all__ = ["DashboardLauncher"]


@runtime_checkable
class DashboardLauncher(Protocol):
    def run_dashboard(self, root: Path, interval: float = 2.0) -> None:
        """Run the dashboard of the organization at ``root`` full screen until the user quits, refreshing every ``interval`` seconds (at least 0.2).
        A ``root`` that is not an organization is an ``OrgError``, raised before the terminal is taken over."""
        ...
