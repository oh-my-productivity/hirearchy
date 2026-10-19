"""The public surface of ``dashdata``: what ``orgmcp dash`` shows, as small data classes and the queries that fill them.

Everything here is *derived from the files*, with the same ports ``status`` / ``progress`` / ``observe`` use, so the dashboard cannot
disagree with them. Nothing is written inside the organization and no event is emitted. What is added on top is only what a screen that
refreshes every second needs:

* the snapshot (header counts, the agent tree with exact state words), the detail of an agent, the requests, the services and the health:
  ``SnapshotQuery``, ``AgentDetailQuery``, ``RequestQuery``, ``ServiceQuery``, ``HealthQuery``, each returning small dataclasses or plain text;
* the event log kept in memory and extended incrementally (``EventFeed``, started by an ``EventFeedFactory``);
* ``DashboardState``, what the five queries of one running dashboard share: its time, the answers they keep for a few seconds, the
  directory times of the refresh in progress, the event feed and the last snapshot;
* ``SnapshotRenderer``, the plain text of ``orgmcp dash --once``.

The pure vocabulary: ``classify`` (the one state of an agent), ``clean_text``, ``pause_text``, ``doc_text`` and the wording of events
(``describe``, ``humanize``, ``event_lines``).

Every query tolerates what a live system produces: no events directory, no agents, a scheduler that is not running, retired agents, files that
are being written, a message that does not parse. A dashboard is not thread-safe: the queries share one ``DashboardState`` and rely on the
application to serialise its refreshes.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import datetime
from typing import Protocol, TypeVar, runtime_checkable

from ..kernel import JsonObject
from ._const import (
    ERROR_WINDOW,
    ERROR_WINDOW_TEXT,
    FEED_BACKFILL,
    FEED_KEEP,
    GLYPHS,
    HEALTH_TTL,
    LOG_BYTES,
    LOG_LINES,
    REQUESTS_TTL,
    SERVICES_TTL,
    STATE_KINDS,
    TEXT_CAP,
)
from ._data import (
    AgentDetail,
    AgentRow,
    HealthView,
    MsgRow,
    RequestRow,
    RunLog,
    SchedulerView,
    Section,
    ServiceRow,
    Snapshot,
    doc_text,
)
from ._events import BATCH_SHOWN, WHO_WIDTH, EventLine, Lookup, clock, describe, event_lines, humanize, who
from ._states import AgentState, classify
from ._text import clean_text, pause_text

__all__ = [
    "AgentDetail",
    "AgentDetailQuery",
    "AgentRow",
    "AgentState",
    "BATCH_SHOWN",
    "DashboardState",
    "ERROR_WINDOW",
    "ERROR_WINDOW_TEXT",
    "EventFeed",
    "EventFeedFactory",
    "EventLine",
    "FEED_BACKFILL",
    "FEED_KEEP",
    "GLYPHS",
    "HEALTH_TTL",
    "HealthQuery",
    "HealthView",
    "LOG_BYTES",
    "LOG_LINES",
    "Lookup",
    "MsgRow",
    "REQUESTS_TTL",
    "RequestQuery",
    "RequestRow",
    "RunLog",
    "SERVICES_TTL",
    "STATE_KINDS",
    "SchedulerView",
    "Section",
    "ServiceQuery",
    "ServiceRow",
    "Snapshot",
    "SnapshotQuery",
    "SnapshotRenderer",
    "TEXT_CAP",
    "WHO_WIDTH",
    "classify",
    "clean_text",
    "clock",
    "describe",
    "doc_text",
    "event_lines",
    "humanize",
    "pause_text",
    "who",
]

T = TypeVar("T")


@runtime_checkable
class SnapshotQuery(Protocol):
    def snapshot(self) -> Snapshot:
        """The organization now: the header counts, the scheduler, and one row per agent (root first, then depth-first) with its one state
        in words. Starts a refresh: directory times are looked at again, the event feed is created (first call) or polled."""
        ...


@runtime_checkable
class AgentDetailQuery(Protocol):
    def agent_detail(self, addr: str, snap: Snapshot | None = None, raw: bool = False) -> AgentDetail:
        """Everything about one agent: overview, messages (newest first), the tail of its run log, memory, charter, its events and them as
        lines (``raw``: as the log has them). An unknown agent gets a one-line overview saying so. ``snap``: the snapshot to read the
        agent's row from (default: the last one, else a new one)."""
        ...

    def run_log(self, addr: str, live: bool) -> RunLog:
        """The tail of the agent's current run log (``live``) or latest run log: at most the last ~1 MB and ``LOG_LINES`` lines, cleaned
        of escape codes, read again only when the file changed."""
        ...

    def message_text(self, row: MsgRow) -> str:
        """The message as it renders, whole (capped at ``TEXT_CAP``), or why it cannot be read."""
        ...

    def message_lookup(self, agent: str, mid: str) -> tuple[str, str, str] | None:
        """``(type, title, sender)`` of a message in the mailbox of ``agent`` (inbox, in flight or read), for the batch of a 'run started'
        line; ``None`` when it is not there."""
        ...

    def event_lines(self, events: list[JsonObject], me: str | None = None, actor: bool = False, raw: bool = False) -> list[EventLine]:
        """Events as lines a human reads (``raw``: as the log has them), the messages of a run's batch told by their titles. ``me``: the view
        of one agent; ``actor``: put who it is about in front."""
        ...


@runtime_checkable
class RequestQuery(Protocol):
    def requests(self, snap: Snapshot | None = None) -> list[RequestRow]:
        """Root's requests, newest first, each with the state, who is busy, the runs and the artifacts ``progress`` says; kept for
        ``REQUESTS_TTL`` seconds while nothing changed on disk."""
        ...

    def trace_text(self, task_id: str) -> str:
        """The trace of one request (``TraceQueries`` rendered), or why there is none."""
        ...

    def request_line(self, task_id: str) -> str:
        """The ``progress`` line of one request."""
        ...


@runtime_checkable
class ServiceQuery(Protocol):
    def services(self, snap: Snapshot | None = None) -> list[ServiceRow]:
        """Every service of every agent with its record; kept for ``SERVICES_TTL`` seconds while nothing changed on disk."""
        ...

    def service_detail(self, owner: str, name: str) -> list[Section]:
        """One service: contract, playbook, record, cases by playbook version, or why it cannot be read."""
        ...


@runtime_checkable
class HealthQuery(Protocol):
    def health(self, snap: Snapshot | None = None) -> HealthView:
        """What is happening now, and the agents the health analysis flags; kept for ``HEALTH_TTL`` seconds while nothing changed on disk."""
        ...

    def run_check(self) -> tuple[datetime, str, bool]:
        """The integrity checks, on demand: ``(when, rendered text, all passed)``."""
        ...


@runtime_checkable
class EventFeed(Protocol):
    """The event log in memory: the last events (oldest first), extended by polls."""

    events: Sequence[JsonObject]
    any: bool  # is there any event at all (a log with files but no events in the window counts)
    version: int  # counts the polls that added something (a screen redraws when it changes)
    last_ts: datetime | None

    def poll(self, now: datetime | None = None) -> int:
        """Read what was appended since the last poll; returns how many events were added."""
        ...

    def error_count(self, now: datetime) -> int:
        """Errors of the last ``ERROR_WINDOW`` before ``now``."""
        ...

    def matching(self, text: str = "", errors: bool = False, agent: str | None = None, limit: int = 1000) -> list[JsonObject]:
        """The newest ``limit`` events that match, oldest first. ``text``: words, all of which must appear (case insensitive) in the agent /
        kind / trace / run fields or in what the readable line says; ``agent``: only events of that agent; ``errors``: only errors."""
        ...


@runtime_checkable
class EventFeedFactory(Protocol):
    def create(self, keep: int = FEED_KEEP, backfill: str = FEED_BACKFILL, now: datetime | None = None) -> EventFeed:
        """A feed that starts following first (so that no event falls between the backlog and the polls), then loads the last ``backfill``
        of the log (at most ``keep`` events) and the errors of the last ``ERROR_WINDOW``. A damaged log means an empty feed."""
        ...


@runtime_checkable
class DashboardState(Protocol):
    """What the queries of one dashboard share. Not thread-safe: the application serialises its refreshes."""

    feed: EventFeed | None
    snap: Snapshot | None  # the last snapshot
    check_result: tuple[datetime, str, bool] | None  # the last ``run_check``

    def now(self) -> datetime:
        """The time of the dashboard (aware)."""
        ...

    def refresh(self) -> None:
        """A new refresh begins: directory times are looked at again."""
        ...

    def mtime(self, addr: str, name: str) -> int:
        """``mtime_ns`` of ``<addr>/<name>`` (``name`` ``""``: the agent's directory), -1 when missing; looked at once per refresh."""
        ...

    def memoised(self, name: str, sig: tuple[object, ...], ttl: float, fn: Callable[[], T]) -> T:
        """``fn()``, kept under ``name`` for ``ttl`` seconds as long as ``sig`` does not change."""
        ...

    def following(self, now: datetime) -> EventFeed:
        """The event feed: created at the first call, polled at the following ones."""
        ...


@runtime_checkable
class SnapshotRenderer(Protocol):
    def render_once(self, width: int = 110) -> str:
        """The plain-text snapshot of ``orgmcp dash --once``: header, the agent tree with states, what needs you, requests, services,
        unreadable files. Whole lines: it is read by people and scripts, never cut."""
        ...
