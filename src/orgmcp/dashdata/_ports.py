"""The roles ``dashdata`` is made of: one small Protocol each (package-private; the public ones are in ``api``).

A query of the dashboard asks these for what it shows; wiring builds the classes behind them over the ports of the runtime of one dashboard.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from datetime import datetime
from typing import Protocol, runtime_checkable

from ..eventlog import EventFile
from ..kernel import JsonObject, Message
from ..reflection import Case
from ._data import AgentRow, MsgRow, RequestRow, RunLog, SchedulerView, Section, Snapshot
from ._events import EventLine


@runtime_checkable
class MtimeProbe(Protocol):
    def tick(self) -> None:
        """A new refresh begins: directory times are looked at again (within one refresh each is stat'ed once)."""
        ...

    def mtime(self, addr: str, name: str) -> int:
        """``mtime_ns`` of ``<addr>/<name>`` (``name`` ``""``: the agent's directory itself); -1 when it is missing."""
        ...


@runtime_checkable
class DashClock(Protocol):
    def now(self) -> datetime:
        """The time of the dashboard (aware): the clock's, or the one the dashboard was given."""
        ...

    def monotonic(self) -> float:
        """Seconds that only go forward (for the lifetime of a memoised answer)."""
        ...


@runtime_checkable
class UnreadableSource(Protocol):
    @property
    def bad(self) -> Mapping[str, str]:
        """Files that could not be read: path (relative to the organization) -> why."""
        ...


@runtime_checkable
class OrgSite(Protocol):
    """The organization as a place: its name, where it is, what was retired, what changed on disk, what could not be read."""

    def name(self) -> str: ...

    def root(self) -> str: ...

    def retired(self) -> int:
        """Directories in ``.retired`` (0 when there are none)."""
        ...

    def signature(self, agents: Sequence[str]) -> tuple[object, ...]:
        """ORG.md's time and, per agent (root first), the times of its boxes, ``runs`` and ``.paused``: it changes when anything shown did."""
        ...

    def unreadable(self) -> dict[str, str]:
        """The files that were skipped (path -> why)."""
        ...


@runtime_checkable
class AgentProfile(Protocol):
    def profile(self, addr: str) -> tuple[str, str]:
        """``(role, model)``: the charter's role (``?`` when it has none) and model (the organization's default when it names none)."""
        ...


@runtime_checkable
class AgentWork(Protocol):
    def running(self, addr: str) -> bool: ...

    def unread(self, addr: str) -> int: ...

    def open_tasks(self, addr: str) -> list[Message]: ...

    def outstanding(self, addr: str) -> list[Message]: ...


@runtime_checkable
class Elapsed(Protocol):
    def since_start(self, running: Sequence[str], now: datetime) -> dict[str, float | None]:
        """Seconds each of the running agents has been running (``None``: unknown), from the registry or else its latest run log."""
        ...


@runtime_checkable
class RowSource(Protocol):
    def running(self, agents: Sequence[str]) -> list[str]:
        """Those of ``agents`` with a run in flight."""
        ...

    def root(self) -> AgentRow:
        """The row of root, the human: it is never in a state of its own, only what waits for it."""
        ...

    def build(self, agents: Sequence[str], running: Sequence[str], now: datetime, scheduler_up: bool, free: int,
              max_parallel: int) -> dict[str, AgentRow]:
        """The row of each agent (one state each), by address; ``running``: those of ``agents`` with a run in flight."""
        ...


@runtime_checkable
class SchedulerViews(Protocol):
    def view(self, now: datetime) -> SchedulerView: ...


@runtime_checkable
class EventFileStamps(Protocol):
    def stamp(self, file: EventFile) -> tuple[int, int] | None:
        """``(size, mtime_ns)`` of the event file; ``None`` when it cannot be looked at."""
        ...


@runtime_checkable
class ReadableEvents(Protocol):
    """Events as lines a human reads, the batch of a run told with the titles of its messages."""

    def lines(self, events: list[JsonObject], me: str | None = None, actor: bool = False, raw: bool = False) -> list[EventLine]: ...

    def message(self, agent: str, mid: str) -> tuple[str, str, str] | None:
        """``(type, title, sender)`` of a message in the mailbox of ``agent`` (inbox, in flight or read), ``None`` when it is not there."""
        ...


@runtime_checkable
class EventFilters(Protocol):
    def build(self, agent: str | None, errors: bool) -> Callable[[JsonObject], bool]:
        """Which events a filter lets through: those of ``agent`` (actor, agent, or an end of the message), and only the errors when asked."""
        ...


@runtime_checkable
class RequestFacts(Protocol):
    """What ``progress`` says of a task of root's, piece by piece."""

    def state_of(self, task: Message, result: Message | None, team: Sequence[str]) -> tuple[str, str]:
        """``(state, who is busy)``."""
        ...

    def runs_text(self, task: Message, result: Message | None, team: Sequence[str]) -> str: ...

    def last_activity(self, team: Sequence[str]) -> datetime | None: ...

    def artifacts(self, result: Message) -> list[str]: ...


@runtime_checkable
class RequestSource(Protocol):
    def rows(self, snap: Snapshot) -> list[RequestRow]:
        """Root's requests, newest first."""
        ...


@runtime_checkable
class RequestTexts(Protocol):
    def line(self, task_id: str, now: datetime) -> str: ...

    def trace(self, task_id: str, now: datetime) -> str: ...


@runtime_checkable
class CaseVerdicts(Protocol):
    def chain(self, case: Case) -> str:
        """The client's verdicts on a case, in order, as one phrase."""
        ...


@runtime_checkable
class AgentOverviews(Protocol):
    def overview(self, addr: str, row: AgentRow, snap: Snapshot, events: list[JsonObject]) -> list[Section]: ...


@runtime_checkable
class MessageViews(Protocol):
    def rows(self, addr: str, limit: int = 300) -> list[MsgRow]:
        """The messages of an agent in every box, newest first."""
        ...

    def text(self, row: MsgRow) -> str:
        """The message as it renders, whole (capped), or why it cannot be read."""
        ...


@runtime_checkable
class AgentTexts(Protocol):
    def memory(self, addr: str) -> str: ...

    def charter(self, addr: str) -> str: ...


@runtime_checkable
class RunLogViews(Protocol):
    def run_log(self, addr: str, live: bool) -> RunLog: ...
