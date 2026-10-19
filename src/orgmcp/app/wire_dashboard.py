"""The dashboard over the ports of an organization (ARCHITECTURE.md 6.3): the queries of one dashboard, the opener of them, the launcher.

The dashboard needs no port of the runtime of its own (``NOT_A_FIELD`` of ``fields_dashboard``): the five queries and the state they share are the
fields of ``fields_dashdata``, built over the lenient ports of ``wire_dashdata.dashboard_runtime``, and ``ComposedQueries`` is the one object the app asks. The
Textual app is made by the screen (``TextualScreenRunner``), never by the wiring, so that opening an organization (and refusing a directory that is none)
happens before the terminal is taken over.

Read-only, like the queries: the dashboard writes nothing inside the organization and emits no event.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from ..dashboard import DashboardLauncher
from ..dashboard._launcher import TextualDashboardLauncher, TextualScreenRunner
from ..dashboard._ports import DashboardQueries, QueriesOpener, ScreenRunner
from ..dashboard._queries import ComposedQueries
from ..kernel import OrgError
from ._builder import Builder
from .wire_dashdata import dashboard_runtime

__all__ = ["RuntimeQueriesOpener", "dashboard_launcher", "queries_of", "register"]


def register(b: Builder) -> None:
    """The dashboard has no port of its own (see the module docstring)."""


class RuntimeQueriesOpener(QueriesOpener):
    """The queries of an organization on disk, over the runtime of ``orgmcp dash``. ``now``: the time the dashboard shows (default: the clock's);
    ``scheduler_ttl``: how long the state of the scheduler is trusted."""

    def __init__(self, now: Callable[[], datetime] | None = None, scheduler_ttl: float = 3.0) -> None:
        self._now = now
        self._scheduler_ttl = scheduler_ttl

    def open(self, root: Path) -> DashboardQueries:
        path = Path(root).expanduser().resolve()
        if not (path / "ORG.md").is_file():
            raise OrgError(f"not an organization (no ORG.md): {path}")
        runtime = dashboard_runtime(path, self._now, self._scheduler_ttl)
        return ComposedQueries(
            runtime.snapshot_query, runtime.agent_detail_query, runtime.request_query, runtime.service_query, runtime.health_query, runtime.dashboard_state,
        )


def queries_of(root: str | Path, now: Callable[[], datetime] | None = None, scheduler_ttl: float = 3.0) -> DashboardQueries:
    """The queries of one dashboard of the organization at ``root`` (``OrgError`` when it is not one)."""
    return RuntimeQueriesOpener(now, scheduler_ttl).open(Path(root))


def dashboard_launcher(screens: ScreenRunner | None = None) -> DashboardLauncher:
    """The launcher of ``orgmcp dash``: it opens the queries of a root and puts them on ``screens`` (default: the Textual app)."""
    return TextualDashboardLauncher(RuntimeQueriesOpener(), screens or TextualScreenRunner())
