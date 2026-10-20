"""The ports the views are made of, owned by the package (not part of its api): the history of the messages, the derivation of a message's
trace, the runs, the parts of ``now`` (the scheduler, the batches in flight, the queue, the recent events, the desk of root) and the parts of ``check``
(one invariant, a live run). Each has one implementation in the package; the views take them by these types so that a test puts a fake in."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from ..kernel import JsonObject
from ..mail import MessageFile

if TYPE_CHECKING:
    from ._messages import Msg
    from ._runs import RunRec


@runtime_checkable
class MessageHistory(Protocol):
    def messages(self) -> dict[str, Msg]:
        """Every message of the organization once, by id: the front matter of the first copy, every copy's ``(owner, box)``. Files that do not
        parse are left out."""
        ...


@runtime_checkable
class TraceDeriver(Protocol):
    def of(self, mid: str) -> tuple[str | None, str]:
        """``(trace id or None, source)`` of a message; the source is ``recorded``, ``derived:<rule>`` or ``unknown``."""
        ...


@runtime_checkable
class TraceDerivers(Protocol):
    def derive(self, msgs: Mapping[str, Msg], batches: Mapping[str, list[str]] | None = None) -> TraceDeriver:
        """A deriver over these messages; ``batches`` maps a run id to the ids it was started with (from ``run.start`` events)."""
        ...


@runtime_checkable
class RunCollection(Protocol):
    def collect(
        self,
        since: datetime | None,
        until: datetime | None,
        events: Mapping[str, Mapping[str, JsonObject]] | None = None,
        agents: Sequence[str] | None = None,
    ) -> list[RunRec]:
        """Every run that STARTED in ``[since, until]``, oldest first: the run logs of the live agents (the file truth: one log = one run = one
        run of budget), completed with ``run.start`` / ``run.end`` events where there are some, plus (with no ``agents`` given) the runs known
        only from events, of agents that were retired since. ``events`` is ``run_events`` of the window, read when not given."""
        ...

    def team_runs(
        self, team: Sequence[str], in_windows: Callable[[str], bool], events: Mapping[str, Mapping[str, JsonObject]]
    ) -> list[RunRec]:
        """The runs of the agents of ``team`` whose log stem ``in_windows`` accepts, oldest first (the runs of one request)."""
        ...


# ------------------------------------------------------------------------------ the files the views look at


@runtime_checkable
class MailboxFiles(Protocol):
    def names(self, addr: str, box: str) -> list[str]:
        """The names of the message files in a box of an agent, sorted (``*.md``, not hidden); ``[]`` when the box is not there."""
        ...

    def path(self, addr: str, box: str, name: str) -> Path:
        """Where the file ``name`` of the box is (it need not be there)."""
        ...

    def mtime(self, addr: str, box: str, name: str) -> float | None:
        """When the file was last written (epoch seconds); None when it is not there."""
        ...


@runtime_checkable
class SchedulerPidFile(Protocol):
    def exists(self) -> bool:
        """Is there a pid file: does some scheduler claim to run?"""
        ...


# ------------------------------------------------------------------------------ now


@dataclass(frozen=True)
class BatchItem:
    """One message of the batch a run was started with: what ``now`` says of it."""

    id: str
    title: str
    sender: str
    trace: str | None  # the trace recorded in its front matter


@runtime_checkable
class SchedulerReport(Protocol):
    def info(self, now: datetime) -> JsonObject:
        """The scheduler as ``now`` shows it: ``state``, ``pid``, ``since``, ``detail``, ``mode``, ``uptime_s``, ``last_heartbeat_age_s``,
        ``last_exit`` and ``heartbeats`` (and ``heartbeat_running`` / ``last_exit_ts`` when there are some)."""
        ...


@runtime_checkable
class InflightBatches(Protocol):
    def of_running(self) -> dict[str, list[BatchItem]]:
        """For every agent with a batch inflight (a run is going), its messages in name order: those whose front matter can be read."""
        ...


@runtime_checkable
class FlightReport(Protocol):
    def runs(self, now: datetime) -> list[JsonObject]:
        """One entry per agent with a run going: ``agent``, ``run``, ``elapsed_s``, ``batch`` (titles) and ``traces``."""
        ...


@runtime_checkable
class QueueReport(Protocol):
    def queued(self, now: datetime, scheduler_up: bool, running: int, max_parallel: int) -> list[JsonObject]:
        """Every agent with unread mail and why it has not started: ``agent``, ``unread``, ``reason``, ``waiting_s``."""
        ...

    def paused(self) -> dict[str, str]:
        """The paused agents and why."""
        ...


@runtime_checkable
class RecentEvents(Protocol):
    def errors(self, now: datetime) -> JsonObject:
        """``{"count", "events"}`` of the errors of the last fifteen minutes (the last five events)."""
        ...

    def last(self, now: datetime) -> datetime | None:
        """When the last event of the last three days was written; None when there is none."""
        ...


@runtime_checkable
class RootDesk(Protocol):
    def waiting(self) -> list[str]:
        """What waits for the decision of root, one line each."""
        ...

    def open_tasks(self) -> int:
        """How many tasks root has outstanding."""
        ...


# ------------------------------------------------------------------------------ check


@runtime_checkable
class IntegrityCheck(Protocol):
    def run(self, files: Sequence[MessageFile], now: float) -> JsonObject:
        """One invariant: ``{"id", "name", "ok", "details"}``. ``files`` is the scan of the messages, ``now`` epoch seconds."""
        ...


@runtime_checkable
class LiveRuns(Protocol):
    def live(self, record: Mapping[str, object] | None) -> bool:
        """Is the process recorded for a run (an entry of the registry) still alive, or in doubt?"""
        ...


# ------------------------------------------------------------------------------ the text


@runtime_checkable
class TargetedEvents(Protocol):
    def view(self, target: str | None, since: str, errors_only: bool, limit: int, now: datetime | None) -> JsonObject:
        """The event view for the ``target`` a person typed (a trace id, an agent address or an event kind), with ``any``: whether the organization
        has event files at all."""
        ...
