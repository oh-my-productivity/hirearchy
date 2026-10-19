"""Data layer of the terminal dashboard (``orgmcp dash``): pure, UI-free snapshots of an organization.

The names this module has always had, over the package :mod:`orgmcp.dashdata`, which holds the data classes, the queries and the caches that keep
a refresh tick cheap. What stays here is the old shape of the entry points: ``DashData(root, now=..., scheduler_ttl=...)`` (the five queries of
one dashboard in one object, built over the runtime that ``app.wire_dashdata`` makes for it), ``render_once(data)`` and ``EventFeed(org, ...)``.
``LenientOrg``, the ``Org`` that skipped what it could not read and cached the mailboxes, is gone: its roles are decorators of the read ports
(``agents``, ``mail``, ``settings``, ``runs``, ``eligibility``) that ``wire_dashdata.dashboard_runtime`` puts in the runtime of the dashboard.

Everything is *derived from the files*, with the same ports ``status`` / ``progress`` / ``observe`` use, so the dashboard cannot disagree with
them. Nothing is written inside the organization and no event is emitted. These names go with the other legacy modules (step E3).
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from . import dashdata as _dashdata
from .app import wire_dashdata
from .core import Org
from .dashboard_events import EventLine
from .dashdata import (
    AgentDetailQuery,
    DashboardState,
    EventFeed as _EventFeed,
    HealthQuery,
    RequestQuery,
    ServiceQuery,
    SnapshotQuery,
)
from .kernel import JsonObject, OrgError

ERROR_WINDOW = _dashdata.ERROR_WINDOW
ERROR_WINDOW_TEXT = _dashdata.ERROR_WINDOW_TEXT
LOG_LINES = _dashdata.LOG_LINES
LOG_BYTES = _dashdata.LOG_BYTES
FEED_KEEP = _dashdata.FEED_KEEP
FEED_BACKFILL = _dashdata.FEED_BACKFILL
TEXT_CAP = _dashdata.TEXT_CAP
CACHE_TRUST = 2.0  # the decorators of the mailboxes carry their own (mail/_caching.py); kept as the export it always was
SERVICES_TTL = _dashdata.SERVICES_TTL
HEALTH_TTL = _dashdata.HEALTH_TTL
REQUESTS_TTL = _dashdata.REQUESTS_TTL

STATE_KINDS = _dashdata.STATE_KINDS
GLYPHS = _dashdata.GLYPHS

clean_text = _dashdata.clean_text
AgentState = _dashdata.AgentState
pause_text = _dashdata.pause_text
classify = _dashdata.classify
Section = _dashdata.Section
doc_text = _dashdata.doc_text
AgentRow = _dashdata.AgentRow
SchedulerView = _dashdata.SchedulerView
Snapshot = _dashdata.Snapshot
MsgRow = _dashdata.MsgRow
RunLog = _dashdata.RunLog
AgentDetail = _dashdata.AgentDetail
RequestRow = _dashdata.RequestRow
ServiceRow = _dashdata.ServiceRow
HealthView = _dashdata.HealthView

_read_tail = wire_dashdata.read_tail


def EventFeed(org: Org, keep: int = FEED_KEEP, backfill: str = FEED_BACKFILL, now: datetime | None = None) -> _EventFeed:  # noqa: N802
    """The event log of ``org`` in memory: the last ``keep`` events (oldest first), extended by ``poll()`` (it was a class)."""
    return org.runtime.event_feed_factory.create(keep, backfill, now)


class DashData(SnapshotQuery, AgentDetailQuery, RequestQuery, ServiceQuery, HealthQuery):
    """Everything the dashboard shows, with the caches that keep a refresh tick cheap: the five queries of ``dashdata`` over the runtime of one
    dashboard. Not thread-safe: use it from one thread at a time (the app serialises its refreshes)."""

    def __init__(self, root: str | Path, now: Callable[[], datetime] | None = None, scheduler_ttl: float = 3.0):
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
    def feed(self) -> _dashdata.EventFeed | None:
        return self._state.feed

    @property
    def snap(self) -> _dashdata.Snapshot | None:
        return self._state.snap

    @property
    def check_result(self) -> tuple[datetime, str, bool] | None:
        return self._state.check_result

    def now(self) -> datetime:
        return self._state.now()

    # ---------------------------------------------------------------------------------------- the queries
    def snapshot(self) -> _dashdata.Snapshot:
        return self._snapshots.snapshot()

    def agent_detail(self, addr: str, snap: _dashdata.Snapshot | None = None, raw: bool = False) -> _dashdata.AgentDetail:
        return self._details.agent_detail(addr, snap, raw)

    def run_log(self, addr: str, live: bool) -> _dashdata.RunLog:
        return self._details.run_log(addr, live)

    def message_text(self, row: _dashdata.MsgRow) -> str:
        return self._details.message_text(row)

    def message_lookup(self, agent: str, mid: str) -> tuple[str, str, str] | None:
        return self._details.message_lookup(agent, mid)

    def event_lines(self, events: list[JsonObject], me: str | None = None, actor: bool = False, raw: bool = False) -> list[EventLine]:
        return self._details.event_lines(events, me, actor, raw)

    def requests(self, snap: _dashdata.Snapshot | None = None) -> list[_dashdata.RequestRow]:
        return self._requests.requests(snap)

    def request_line(self, task_id: str) -> str:
        return self._requests.request_line(task_id)

    def trace_text(self, task_id: str) -> str:
        return self._requests.trace_text(task_id)

    def services(self, snap: _dashdata.Snapshot | None = None) -> list[_dashdata.ServiceRow]:
        return self._services.services(snap)

    def service_detail(self, owner: str, name: str) -> list[_dashdata.Section]:
        return self._services.service_detail(owner, name)

    def health(self, snap: _dashdata.Snapshot | None = None) -> _dashdata.HealthView:
        return self._health.health(snap)

    def run_check(self) -> tuple[datetime, str, bool]:
        return self._health.run_check()


def render_once(data: DashData, width: int = 110) -> str:
    """The ``orgmcp dash --once`` output: header, the agent tree with states, requests, services."""
    return wire_dashdata.renderer_over(data, data, data).render_once(width)
