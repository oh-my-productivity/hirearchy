"""What is happening right now. (RED: skeleton.)"""

from __future__ import annotations

from datetime import datetime

from ..agents import AgentDirectory
from ..attention import HumanQueue
from ..daemon import ExitMarker, SchedulerStatus
from ..eligibility import PauseStore
from ..eventlog import EventReader
from ..kernel import Clock, JsonObject
from ..budget import BudgetQuery
from ..mail import MailboxReader, MessageIndex, TaskQuery
from ..runs import RunLogReader, RunRegistry
from ..settings import OrgSettings
from ._ports import (
    BatchItem,
    FlightReport,
    InflightBatches,
    MailboxFiles,
    MessageHistory,
    QueueReport,
    RecentEvents,
    RootDesk,
    SchedulerReport,
    TraceDerivers,
)
from .api import NowQueries


class EventSchedulerReport(SchedulerReport):
    def __init__(self, status: SchedulerStatus, marker: ExitMarker, events: EventReader) -> None:
        self._status, self._marker, self._events = status, marker, events

    def info(self, now: datetime) -> JsonObject:
        raise NotImplementedError("red: C-obs-2")


class MailInflightBatches(InflightBatches):
    def __init__(self, agents: AgentDirectory, mailbox: MailboxReader, files: MailboxFiles, index: MessageIndex) -> None:
        self._agents, self._mailbox, self._files, self._index = agents, mailbox, files, index

    def of_running(self) -> dict[str, list[BatchItem]]:
        raise NotImplementedError("red: C-obs-2")


class BatchRunsInFlight(FlightReport):
    def __init__(
        self, batches: InflightBatches, registry: RunRegistry, run_logs: RunLogReader, history: MessageHistory, derivers: TraceDerivers
    ) -> None:
        self._batches, self._registry, self._run_logs, self._history, self._derivers = batches, registry, run_logs, history, derivers

    def runs(self, now: datetime) -> list[JsonObject]:
        raise NotImplementedError("red: C-obs-2")


class ReasonedQueue(QueueReport):
    def __init__(self, agents: AgentDirectory, mailbox: MailboxReader, pauses: PauseStore, budgets: BudgetQuery, files: MailboxFiles) -> None:
        self._agents, self._mailbox, self._pauses, self._budgets, self._files = agents, mailbox, pauses, budgets, files

    def queued(self, now: datetime, scheduler_up: bool, running: int, max_parallel: int) -> list[JsonObject]:
        raise NotImplementedError("red: C-obs-2")

    def paused(self) -> dict[str, str]:
        raise NotImplementedError("red: C-obs-2")


class LoggedRecentEvents(RecentEvents):
    def __init__(self, events: EventReader) -> None:
        self._events = events

    def errors(self, now: datetime) -> JsonObject:
        raise NotImplementedError("red: C-obs-2")

    def last(self, now: datetime) -> datetime | None:
        raise NotImplementedError("red: C-obs-2")


class MailRootDesk(RootDesk):
    def __init__(self, queue: HumanQueue, tasks: TaskQuery) -> None:
        self._queue, self._tasks = queue, tasks

    def waiting(self) -> list[str]:
        raise NotImplementedError("red: C-obs-2")

    def open_tasks(self) -> int:
        raise NotImplementedError("red: C-obs-2")


class FileNowQueries(NowQueries):
    def __init__(
        self, settings: OrgSettings, scheduler: SchedulerReport, flight: FlightReport, queue: QueueReport, events: RecentEvents, desk: RootDesk,
        clock: Clock,
    ) -> None:
        self._settings, self._scheduler, self._flight, self._queue, self._events, self._desk, self._clock = (
            settings, scheduler, flight, queue, events, desk, clock,
        )

    def now_view(self, now: datetime | None = None) -> JsonObject:
        raise NotImplementedError("red: C-obs-2")
