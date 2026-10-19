"""Providers of the ``observability`` ports (ARCHITECTURE.md 6.1), and the same objects over the runtime in force for the legacy functions.

The seven ports of the package (the event, trace, metric and now queries, the integrity checks, the renderer and the text of the views) are fields of the
runtime. The parts they are made of (the scheduler report, the batches in flight, the queue, the recent events, the desk of root, one class per
invariant, the targeted events) are private to the package and made here, inside the provider of the port that uses them.

``event_queries_of``, ``trace_queries_of``, ``metric_queries_of``, ``now_queries_of``, ``integrity_checks_of``, ``renderer_of``, ``observe_text_of``, ``event_queries_sleeping``,
``system_renderer``, ``trace_derivers_of`` and ``run_collection_of`` serve the functions of ``observe.py`` that are still there (the legacy
module, the dashboard): they are handed an ``Org`` whose ``runtime`` tests replace (the clock, the scheduler status, the processes) and the
dashboard's lenient ``Org`` replaces the mailboxes of, so each call builds the objects over the ports the runtime has *now*, as the functions they
replace read them through the ``Org``. They go when the legacy functions do.

The legacy module also needs a few names of the package that are not public (``plain``, ``matcher``, ``Msg``, ``build_messages``, ``RunRec``, the thresholds
...): it reaches them here, since only the composition root may import a private module.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

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
from ..observability._checks import COPY_GRACE as COPY_GRACE  # re-exported for observe.py
from ..observability._checks import INFLIGHT_GRACE as INFLIGHT_GRACE  # re-exported for observe.py
from ..observability._checks import RECV_BOXES as RECV_BOXES  # re-exported for observe.py
from ..observability._derive import LogTraceDerivers
from ..observability._dispatch import VIEWS as VIEWS  # re-exported for observe.py
from ..observability._dispatch import AgentTargetedEvents, ViewDispatcher
from ..observability._events import LogEventQueries
from ..observability._files import FsMailboxFiles, FsSchedulerPidFile
from ..observability._history import IndexedMessageHistory
from ..observability._messages import Msg as Msg  # re-exported for observe.py
from ..observability._messages import build_messages as build_messages  # re-exported for observe.py
from ..observability._metrics import DerivedMetricQueries
from ..observability._now import ERROR_WINDOW as ERROR_WINDOW  # re-exported for observe.py
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
from ..observability._runs import RunRec as RunRec  # re-exported for observe.py
from ..observability._runs import run_events as run_events  # re-exported for observe.py
from ..observability._trace import READ_ONLY_TOOLS as READ_ONLY_TOOLS  # re-exported for observe.py
from ..observability._trace import DerivedTraceQueries
from ..observability._trace import run_window as run_window  # re-exported for observe.py
from ..observability._util import matcher as matcher  # re-exported for observe.py
from ..observability._util import plain as plain  # re-exported for observe.py
from ..processes import OrphanJudge
from ..runs import RunLogReader, RunRegistry
from ..settings import OrgSettings
from ._builder import Builder
from ._lazy import PortResolver
from .runtime import OrgRuntime
from .wire_stalls import RuntimePorts


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


# ------------------------------------------------------------------------------ the legacy functions' objects


def event_queries_of(runtime: OrgRuntime) -> EventQueries:
    """``EventQueries`` over the ports ``runtime`` has now."""
    return event_queries(RuntimePorts(runtime))


class SleepingClock(Clock):
    """``clock`` that sleeps by the function it was given (``observe.follow_events`` has always taken one)."""

    def __init__(self, clock: Clock, sleep: Callable[[float], None]) -> None:
        self._clock, self._sleep = clock, sleep

    def now(self) -> datetime:
        return self._clock.now()

    def time(self) -> float:
        return self._clock.time()

    def monotonic(self) -> float:
        return self._clock.monotonic()

    def sleep(self, seconds: float) -> None:
        self._sleep(seconds)


def event_queries_sleeping(runtime: OrgRuntime, sleep: Callable[[float], None]) -> EventQueries:
    """``EventQueries`` over the ports ``runtime`` has now that waits between polls with ``sleep`` (``follow_events``)."""
    return LogEventQueries(runtime.event_reader, runtime.event_followers, SleepingClock(runtime.clock, sleep))


def trace_queries_of(runtime: OrgRuntime) -> TraceQueries:
    """``TraceQueries`` over the ports ``runtime`` has now."""
    return trace_queries(RuntimePorts(runtime))


def metric_queries_of(runtime: OrgRuntime) -> MetricQueries:
    """``MetricQueries`` over the ports ``runtime`` has now."""
    return metric_queries(RuntimePorts(runtime))


def trace_derivers_of(runtime: OrgRuntime) -> TraceDerivers:
    """``TraceDerivers`` over the run logs ``runtime`` has now."""
    return trace_derivers(RuntimePorts(runtime))


def run_collection_of(runtime: OrgRuntime) -> RunCollection:
    """``RunCollection`` over the ports ``runtime`` has now."""
    return run_collection(RuntimePorts(runtime))


def now_queries_of(runtime: OrgRuntime) -> NowQueries:
    """``NowQueries`` over the ports ``runtime`` has now."""
    return now_queries(RuntimePorts(runtime))


def integrity_checks_of(runtime: OrgRuntime) -> IntegrityChecks:
    """``IntegrityChecks`` over the ports ``runtime`` has now."""
    return integrity_checks(RuntimePorts(runtime))


def renderer_of(runtime: OrgRuntime) -> ObservabilityRenderer:
    """``ObservabilityRenderer`` (the text of the views does not depend on the runtime)."""
    return renderer(RuntimePorts(runtime))


def system_renderer() -> ObservabilityRenderer:
    """``ObservabilityRenderer`` for the legacy ``render_*`` functions, which are given a view and no organization."""
    return TextObservabilityRenderer()


def observe_text_of(runtime: OrgRuntime) -> ObservabilityText:
    """``ObservabilityText`` over the queries, checks and renderer ``runtime`` has now."""
    ports = RuntimePorts(runtime)
    targeted = AgentTargetedEvents(event_queries(ports), ports.get(AgentDirectory), ports.get(EventReader))
    return ViewDispatcher(targeted, trace_queries(ports), metric_queries(ports), now_queries(ports), integrity_checks(ports), renderer(ports))
