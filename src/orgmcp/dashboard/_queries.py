"""The five queries of ``dashdata`` and the state they share, as the one object the app asks."""

from __future__ import annotations

from datetime import datetime

from ..dashdata import (
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
from ..kernel import JsonObject
from ._ports import DashboardQueries


class ComposedQueries(DashboardQueries):
    """The five queries of one dashboard and the state they share, asked as one object (what ``DashData`` was). Each question goes to the query that
    answers it, unchanged. NOT THREAD-SAFE, like the cache the queries share: the app asks from one thread at a time (``DashCache``)."""

    def __init__(
        self, snapshots: SnapshotQuery, details: AgentDetailQuery, requests: RequestQuery, services: ServiceQuery, health: HealthQuery,
        state: DashboardState,
    ) -> None:
        self._snapshots = snapshots
        self._details = details
        self._requests = requests
        self._services = services
        self._health = health
        self._state = state

    @property
    def feed(self) -> EventFeed | None:
        return self._state.feed

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

    def trace_text(self, task_id: str) -> str:
        return self._requests.trace_text(task_id)

    def request_line(self, task_id: str) -> str:
        return self._requests.request_line(task_id)

    def services(self, snap: Snapshot | None = None) -> list[ServiceRow]:
        return self._services.services(snap)

    def service_detail(self, owner: str, name: str) -> list[Section]:
        return self._services.service_detail(owner, name)

    def health(self, snap: Snapshot | None = None) -> HealthView:
        return self._health.health(snap)

    def run_check(self) -> tuple[datetime, str, bool]:
        return self._health.run_check()
