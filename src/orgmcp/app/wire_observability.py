"""Providers of the ``observability`` ports (ARCHITECTURE.md 6.1).

The seven ports of the package (the event, trace, metric and now queries, the integrity checks, the renderer and the text of the views) are fields of the
runtime. The parts they are made of (the scheduler report, the batches in flight, the queue, the recent events, the desk of root, one class per
invariant, the targeted events) are private to the package and made here, inside the provider of the port that uses them.
"""

from __future__ import annotations

from ..agents import AgentDirectory, RetiredArchive
from ..attention import HumanQueue
from ..budget import BudgetQuery
from ..daemon import ExitMarker, SchedulerStatus
from ..eligibility import PauseStore
from ..eventlog import EventFollowers, EventReader
from ..kernel import Clock, OrgLayout
from ..mail import MailboxReader, MessageIndex, TaskQuery
from ..observability import (
    EventQueries,
    IntegrityChecks,
    MetricQueries,
    NowQueries,
    ObservabilityRenderer,
    ObservabilityText,
    TraceQueries,
)
from ..observability._checks import (
    BudgetConserved,
    FileIntegrityChecks,
    InflightAccounted,
    JudgedLiveRuns,
    MessagesIntact,
    PidfileSane,
    RunsAccounted,
    SeqGapless,
)
from ..observability._derive import LogTraceDerivers
from ..observability._dispatch import AgentTargetedEvents, ViewDispatcher
from ..observability._events import LogEventQueries
from ..observability._files import FsMailboxFiles, FsSchedulerPidFile
from ..observability._history import IndexedMessageHistory
from ..observability._metrics import DerivedMetricQueries
from ..observability._now import (
    BatchRunsInFlight,
    EventSchedulerReport,
    FileNowQueries,
    LoggedRecentEvents,
    MailInflightBatches,
    MailRootDesk,
    ReasonedQueue,
)
from ..observability._ports import IntegrityCheck, MessageHistory, RunCollection, TraceDerivers
from ..observability._render import TextObservabilityRenderer
from ..observability._runs import RunCollector
from ..observability._trace import DerivedTraceQueries
from ..processes import OrphanJudge
from ..runs import RunLogReader, RunRegistry
from ..settings import OrgSettings
from ._builder import Builder
from ._lazy import PortResolver


def event_queries(b: PortResolver) -> LogEventQueries:
    """The event queries over the event files, the followers and the clock of ``b``."""
    return LogEventQueries(b.get(EventReader), b.get(EventFollowers), b.get(Clock))


def message_history(b: PortResolver) -> MessageHistory:
    """The history of the messages from the index of ``b``."""
    return IndexedMessageHistory(b.get(MessageIndex))


def trace_derivers(b: PortResolver) -> TraceDerivers:
    """The derivation of a message's trace over the run logs of ``b``."""
    return LogTraceDerivers(b.get(RunLogReader))


def run_collection(b: PortResolver) -> RunCollection:
    """The collection of runs over the run logs, registry, agents, mailboxes and event files of ``b``."""
    return RunCollector(b.get(RunLogReader), b.get(RunRegistry), b.get(AgentDirectory), b.get(MailboxReader), b.get(EventReader))


def trace_queries(b: PortResolver) -> DerivedTraceQueries:
    """The trace of a request over the messages, run logs, events and agents of ``b``."""
    return DerivedTraceQueries(message_history(b), trace_derivers(b), b.get(EventReader), run_collection(b), b.get(AgentDirectory), b.get(Clock))


def metric_queries(b: PortResolver) -> DerivedMetricQueries:
    """The metrics over the events, runs and messages of ``b``."""
    return DerivedMetricQueries(b.get(EventReader), run_collection(b), message_history(b), b.get(Clock))


def now_queries(b: PortResolver) -> FileNowQueries:
    """The now view over the settings, scheduler status, exit marker, events, agents, mailboxes, flags, budgets, files, run logs, registry, messages, queue and
    tasks of ``b``."""
    agents, mail, layout = b.get(AgentDirectory), b.get(MailboxReader), b.get(OrgLayout)
    files = FsMailboxFiles(layout)
    batches = MailInflightBatches(agents, mail, files, b.get(MessageIndex))
    flight = BatchRunsInFlight(batches, b.get(RunRegistry), b.get(RunLogReader), message_history(b), trace_derivers(b))
    queue = ReasonedQueue(agents, mail, b.get(PauseStore), b.get(BudgetQuery), files)
    scheduler = EventSchedulerReport(b.get(SchedulerStatus), b.get(ExitMarker), b.get(EventReader))
    return FileNowQueries(
        b.get(OrgSettings), scheduler, flight, queue, LoggedRecentEvents(b.get(EventReader)), MailRootDesk(b.get(HumanQueue), b.get(TaskQuery)),
        b.get(Clock),
    )


def integrity_checks(b: PortResolver) -> FileIntegrityChecks:
    """The six invariants over the files, flags, budgets, run logs, registry, archive, events, judge and scheduler status of ``b``."""
    agents, layout, events, registry = b.get(AgentDirectory), b.get(OrgLayout), b.get(EventReader), b.get(RunRegistry)
    live, scheduler, run_logs = JudgedLiveRuns(b.get(OrphanJudge)), b.get(SchedulerStatus), b.get(RunLogReader)
    checks: list[IntegrityCheck] = [
        MessagesIntact(layout, agents),
        BudgetConserved(agents, b.get(BudgetQuery), run_logs, b.get(RetiredArchive)),
        InflightAccounted(agents, FsMailboxFiles(layout), registry, live, scheduler),
        RunsAccounted(events, registry, live, agents, run_logs),
        SeqGapless(events),
        PidfileSane(FsSchedulerPidFile(layout), scheduler),
    ]
    return FileIntegrityChecks(b.get(MessageIndex), checks, b.get(Clock))


def renderer(b: PortResolver) -> TextObservabilityRenderer:
    """The text of the views (it needs nothing)."""
    return TextObservabilityRenderer()


def observe_text(b: PortResolver) -> ViewDispatcher:
    """The text of one view by its name, over the queries, checks and renderer of ``b``."""
    targeted = AgentTargetedEvents(b.get(EventQueries), b.get(AgentDirectory), b.get(EventReader))
    return ViewDispatcher(targeted, b.get(TraceQueries), b.get(MetricQueries), b.get(NowQueries), b.get(IntegrityChecks), b.get(ObservabilityRenderer))


def register(b: Builder) -> None:
    b.provide(EventQueries, event_queries)
    b.provide(TraceQueries, trace_queries)
    b.provide(MetricQueries, metric_queries)
    b.provide(NowQueries, now_queries)
    b.provide(IntegrityChecks, integrity_checks)
    b.provide(ObservabilityRenderer, renderer)
    b.provide(ObservabilityText, observe_text)
