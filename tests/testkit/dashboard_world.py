"""The dashboard app over the queries of a real organization, with failures injected through the queries (not by patching the app).

``dash_app(root, interval, now)`` is ``DashApp(queries, interval)`` with the queries of ``orgmcp.app.wire_dashboard.queries_of`` (what the legacy
``DashApp(root, interval, now)`` of ``dashboard/_legacy.py`` built for itself), wrapped in ``FailableQueries``: they answer exactly as the real ones do, until
a test says ``app.data.fail_snapshot(exc)`` (the refresh fails) or ``app.data.break_requests(exc)`` (the rows of the requests cannot be shown).
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from orgmcp.app.wire_dashboard import queries_of
from orgmcp.dashboard._app import DashApp
from orgmcp.dashboard._ports import DashboardQueries
from orgmcp.dashdata import AgentDetail, EventFeed, EventLine, HealthView, MsgRow, RequestRow, RunLog, Section, ServiceRow, Snapshot
from orgmcp.kernel import JsonObject


class _BrokenRow:
    """A row of the requests that cannot be read: the table of the app fails on the first thing it asks of it."""

    def __init__(self, exc: Exception) -> None:
        self._exc = exc

    @property
    def id(self) -> str:
        raise self._exc


class FailableQueries(DashboardQueries):
    """The queries of ``inner``, which fail when a test says so."""

    def __init__(self, inner: DashboardQueries) -> None:
        self._inner = inner
        self._snapshot_error: Exception | None = None
        self._requests_error: Exception | None = None

    def fail_snapshot(self, exc: Exception | None) -> None:
        """Every ``snapshot()`` raises ``exc`` from now on (``None``: answers again)."""
        self._snapshot_error = exc

    def break_requests(self, exc: Exception | None) -> None:
        """``requests()`` answers one row that raises ``exc`` as soon as it is read (``None``: answers again)."""
        self._requests_error = exc

    @property
    def feed(self) -> EventFeed | None:
        return self._inner.feed

    def snapshot(self) -> Snapshot:
        if self._snapshot_error is not None:
            raise self._snapshot_error
        return self._inner.snapshot()

    def agent_detail(self, addr: str, snap: Snapshot | None = None, raw: bool = False) -> AgentDetail:
        return self._inner.agent_detail(addr, snap, raw)

    def run_log(self, addr: str, live: bool) -> RunLog:
        return self._inner.run_log(addr, live)

    def message_text(self, row: MsgRow) -> str:
        return self._inner.message_text(row)

    def message_lookup(self, agent: str, mid: str) -> tuple[str, str, str] | None:
        return self._inner.message_lookup(agent, mid)

    def event_lines(self, events: list[JsonObject], me: str | None = None, actor: bool = False, raw: bool = False) -> list[EventLine]:
        return self._inner.event_lines(events, me, actor, raw)

    def requests(self, snap: Snapshot | None = None) -> list[RequestRow]:
        if self._requests_error is not None:
            return [_BrokenRow(self._requests_error)]  # type: ignore[list-item]
        return self._inner.requests(snap)

    def trace_text(self, task_id: str) -> str:
        return self._inner.trace_text(task_id)

    def request_line(self, task_id: str) -> str:
        return self._inner.request_line(task_id)

    def services(self, snap: Snapshot | None = None) -> list[ServiceRow]:
        return self._inner.services(snap)

    def service_detail(self, owner: str, name: str) -> list[Section]:
        return self._inner.service_detail(owner, name)

    def health(self, snap: Snapshot | None = None) -> HealthView:
        return self._inner.health(snap)

    def run_check(self) -> tuple[datetime, str, bool]:
        return self._inner.run_check()


def dash_app(root: str | Path, interval: float = 2.0, now: Callable[[], datetime] | None = None) -> Any:
    """The app of the organization at ``root`` (``now``: the time it shows)."""
    return DashApp(FailableQueries(queries_of(root, now)), interval)
