"""The opener of the queries of a dashboard over an organization on disk.

Its own module because it is made of the dashboard package, which loads Textual when it is imported: ``wire_dashboard`` (which every runtime loads, with
every ``wire_*``) imports this module only when a dashboard is asked for."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from ..dashboard._ports import DashboardQueries, QueriesOpener
from ..dashboard._queries import ComposedQueries
from ..kernel import OrgError
from .wire_dashdata import dashboard_runtime


class RuntimeQueriesOpener(QueriesOpener):
    """The queries of an organization on disk, over the runtime of ``hirearchy dash``. ``now``: the time the dashboard shows (default: the clock's);
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
