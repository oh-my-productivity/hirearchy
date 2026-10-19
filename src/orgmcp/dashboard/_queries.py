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

RED = "red: D-dashboard"


class ComposedQueries(DashboardQueries):
    """RED skeleton."""

    def __init__(
        self, snapshots: SnapshotQuery, details: AgentDetailQuery, requests: RequestQuery, services: ServiceQuery, health: HealthQuery,
        state: DashboardState,
    ) -> None:
        raise NotImplementedError(RED)

    @property
    def feed(self) -> EventFeed | None:
        raise NotImplementedError(RED)

    def snapshot(self) -> Snapshot:
        raise NotImplementedError(RED)

    def agent_detail(self, addr: str, snap: Snapshot | None = None, raw: bool = False) -> AgentDetail:
        raise NotImplementedError(RED)

    def run_log(self, addr: str, live: bool) -> RunLog:
        raise NotImplementedError(RED)

    def message_text(self, row: MsgRow) -> str:
        raise NotImplementedError(RED)

    def message_lookup(self, agent: str, mid: str) -> tuple[str, str, str] | None:
        raise NotImplementedError(RED)

    def event_lines(self, events: list[JsonObject], me: str | None = None, actor: bool = False, raw: bool = False) -> list[EventLine]:
        raise NotImplementedError(RED)

    def requests(self, snap: Snapshot | None = None) -> list[RequestRow]:
        raise NotImplementedError(RED)

    def trace_text(self, task_id: str) -> str:
        raise NotImplementedError(RED)

    def request_line(self, task_id: str) -> str:
        raise NotImplementedError(RED)

    def services(self, snap: Snapshot | None = None) -> list[ServiceRow]:
        raise NotImplementedError(RED)

    def service_detail(self, owner: str, name: str) -> list[Section]:
        raise NotImplementedError(RED)

    def health(self, snap: Snapshot | None = None) -> HealthView:
        raise NotImplementedError(RED)

    def run_check(self) -> tuple[datetime, str, bool]:
        raise NotImplementedError(RED)
