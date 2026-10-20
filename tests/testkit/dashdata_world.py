"""The data of the dashboard as the tests of ``dashdata`` ask for it: the old call shapes of ``orgmcp.dashboard_data`` and ``orgmcp.observe`` over the new API.

Those two modules are legacy adapters (deleted by step E3), so a moved test does not import them; it imports this world and its lines stay as they were::

    from testkit.dashdata_world import dd, observe       # was: from orgmcp import dashboard_data as dd, observe

``dd`` is the api of ``orgmcp.dashdata`` (``dd.classify``, ``dd.doc_text``, ``dd.LOG_LINES`` ...) plus the two shapes the api does not have:
``dd.DashData(root, now=None, scheduler_ttl=3.0)`` (the five queries of one dashboard in one object, over ``wire_dashdata.dashboard_runtime(root)``) and
``dd.render_once(data, width=110)``. ``observe`` answers the three reads the dashboard tests compare with (``now_view``, ``trace``, ``render_trace``) from the
ports of the runtime of an ``Org``.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from orgmcp import dashdata as _api
from orgmcp.app import wire_dashdata, wire_observability
from orgmcp.dashdata._render import TextSnapshotRenderer
from orgmcp.dashdata import (
    AgentDetail,
    AgentDetailQuery,
    DashboardState,
    EventFeed,
    EventLine,
    HealthQuery,
    HealthView,
    MsgRow,
    RequestQuery,
    RequestRow,
    RunLog,
    Section,
    ServiceQuery,
    ServiceRow,
    Snapshot,
    SnapshotQuery,
)
from orgmcp.kernel import JsonObject, OrgError


class DashData(SnapshotQuery, AgentDetailQuery, RequestQuery, ServiceQuery, HealthQuery):
    """Everything the dashboard shows, with the caches that keep a refresh tick cheap: the five queries of ``dashdata`` over the runtime of one
    dashboard. Not thread-safe: use it from one thread at a time (the app serialises its refreshes)."""

    def __init__(self, root: str | Path, now: Callable[[], datetime] | None = None, scheduler_ttl: float = 3.0) -> None:
        path = Path(root).expanduser().resolve()
        if not (path / "ORG.md").is_file():
            raise OrgError(f"not an organization (no ORG.md): {path}")
        self.runtime = wire_dashdata.dashboard_runtime(path, now, scheduler_ttl)
        self._state: DashboardState = self.runtime.dashboard_state
        self._snapshots = self.runtime.snapshot_query
        self._details = self.runtime.agent_detail_query
        self._requests = self.runtime.request_query
        self._services = self.runtime.service_query
        self._health = self.runtime.health_query

    # ---------------------------------------------------------------------------------------- what the dashboard keeps
    @property
    def feed(self) -> EventFeed | None:
        return self._state.feed

    @property
    def snap(self) -> Snapshot | None:
        return self._state.snap

    @property
    def check_result(self) -> tuple[datetime, str, bool] | None:
        return self._state.check_result

    def now(self) -> datetime:
        return self._state.now()

    # ---------------------------------------------------------------------------------------- the queries
    def snapshot(self) -> Snapshot:
        return self._snapshots.snapshot()

    def agent_detail(self, addr: str, snap: Snapshot | None = None, raw: bool = False) -> AgentDetail:
        return self._details.agent_detail(addr, snap, raw)

    def run_log(self, addr: str, live: bool) -> RunLog:
        return self._details.run_log(addr, live)

    def message_text(self, row: MsgRow) -> str:
        return self._details.message_text(row)

    def message_lookup(self, agent: str, mid: str) -> tuple[str, str, str] | None:
        return self._details.message_lookup(agent, mid)

    def event_lines(self, events: list[JsonObject], me: str | None = None, actor: bool = False, raw: bool = False) -> list[EventLine]:
        return self._details.event_lines(events, me, actor, raw)

    def requests(self, snap: Snapshot | None = None) -> list[RequestRow]:
        return self._requests.requests(snap)

    def request_line(self, task_id: str) -> str:
        return self._requests.request_line(task_id)

    def trace_text(self, task_id: str) -> str:
        return self._requests.trace_text(task_id)

    def services(self, snap: Snapshot | None = None) -> list[ServiceRow]:
        return self._services.services(snap)

    def service_detail(self, owner: str, name: str) -> list[Section]:
        return self._services.service_detail(owner, name)

    def health(self, snap: Snapshot | None = None) -> HealthView:
        return self._health.health(snap)

    def run_check(self) -> tuple[datetime, str, bool]:
        return self._health.run_check()


def render_once(data: DashData, width: int = 110) -> str:
    """The ``orgmcp dash --once`` output: header, the agent tree with states, requests, services."""
    return TextSnapshotRenderer(data, data, data).render_once(width)


class _Dd:
    """``dd.<name>``: the api of ``orgmcp.dashdata``, and the two entry points above."""

    DashData = DashData
    render_once = staticmethod(render_once)

    def __getattr__(self, name: str) -> Any:
        return getattr(_api, name)


dd = _Dd()


class _Observe:
    """The reads of ``orgmcp.observe`` the dashboard tests compare with, from the ports of the runtime of ``org``."""

    @staticmethod
    def now_view(org: Any, now: datetime | None = None) -> Any:
        return wire_observability.now_queries_of(org.runtime).now_view(now)

    @staticmethod
    def trace(org: Any, task_id: str, now: datetime | None = None) -> Any:
        return wire_observability.trace_queries_of(org.runtime).trace(task_id, now)

    @staticmethod
    def render_trace(tr: Any, max_lines: int | None = None) -> str:
        return wire_observability.system_renderer().render_trace(tr, max_lines)


observe = _Observe()
