"""The one place where the roles of the scheduler are put together: the run lifecycle, and the loop over it (called by ``app.wire_scheduler`` and by ``testing``)."""

from __future__ import annotations

from dataclasses import dataclass

from ..access import ModelResolver
from ..agents import AgentDirectory
from ..attention import HumanQueue, OpenWork, WaitingOnUser
from ..budget import BudgetQuery
from ..daemon import ExitMarker, SchedulerLock
from ..delivery import MessageDelivery
from ..eligibility import FailureCounter, PauseStore, RunnableQuery
from ..kernel import Clock, EventSink, OrgLayout, Provider
from ..kiro import RunCommandBuilder
from ..mail import BatchStore, MailboxReader
from ..processes import OrphanJudge, ProcessInspector, ProcessSignaller, ProcessSpawner
from ..prompts import RunPromptBuilder
from ..review import HealthReviewer
from ..runs import RunLogReader, RunLogWriter, RunRegistry
from ..settings import OrgSettings
from ..snapshots import IgnoreList, OrgSnapshotter
from ..stalls import StallLadder
from ..strays import StrayProbe, StrayRegistry
from ..telemetry import EventRetention, ProcessLabel
from ..templates import Notices
from ._admission import BudgetGate
from ._events import LifecycleEvents, SchedulerEvents, SessionAnnouncer
from ._exit import GraceExitPolicy, GraceWait
from ._failures import CountingFailures, PausingEscalation
from ._guard import LoggingPhaseGuard
from ._loop import HeartbeatLoop, PollPacing
from ._orphans import LedgerOrphanSettler, LogRunNotes
from ._phases import FailureLedgerRepair, FundedResume, GuardedPhase, OrphanCheck, ReapPhase, ReviewCheck, RunLaunch, StallCheck
from ._ports import Console, Lifecycle, PhaseGuard
from ._reaper import ExitWatcher, PollingRunReaper, RunSettlement, ShutdownTerminator
from ._run import LoopMemory, LoopState, RunCount
from ._session import BatchRecovery, ClaimedSession, ProcessClaim
from ._starter import AgentRunLauncher, BatchPreparer, CommandSpawner, SingleRunStarter, StartAnnouncer, StartFailureHandler
from ._strays import StrayCheck
from ._throttle import CreditingThrottles
from ._tracker import RunTracker
from ._upkeep import HeartbeatUpkeep
from ._work import QueriedWork


@dataclass(frozen=True)
class LifecyclePorts:
    """Everything the run lifecycle takes from the rest of the system."""

    agents: AgentDirectory
    settings: OrgSettings
    mail: MailboxReader
    batches: BatchStore
    pauses: PauseStore
    failure_counter: FailureCounter
    budgets: BudgetQuery
    delivery: MessageDelivery
    notices: Notices
    models: ModelResolver
    logs: RunLogWriter
    registry: RunRegistry
    prompts: RunPromptBuilder
    stray_probe: StrayProbe
    stray_registry: StrayRegistry
    snapshots: OrgSnapshotter
    events: EventSink
    spawner: ProcessSpawner
    inspector: ProcessInspector
    layout: OrgLayout
    commands: RunCommandBuilder
    log_reader: RunLogReader


def assemble(ports: LifecyclePorts, run_clock: Clock, console: Console, guard: PhaseGuard, count: RunCount) -> Lifecycle:
    """The starter and the reaper over ``ports``; ``run_clock`` times the runs, ``count`` is where the runs started are counted."""
    p = ports
    scheduler_events = SchedulerEvents(p.events)
    run_events = LifecycleEvents(scheduler_events, p.models, p.budgets, p.agents, run_clock)
    failures = CountingFailures(p.failure_counter, PausingEscalation(p.pauses, p.delivery, p.notices, p.settings, p.layout), scheduler_events, console)
    tracker = RunTracker(p.registry, p.inspector, p.layout)
    strays = StrayCheck(p.stray_probe, p.stray_registry, console)
    single = SingleRunStarter(
        BatchPreparer(p.batches, p.budgets, p.logs, p.prompts, count), CommandSpawner(p.commands, p.spawner), strays, guard,
        StartFailureHandler(p.batches, run_events, failures), StartAnnouncer(run_events, tracker, guard, console), run_clock,
    )
    starter = AgentRunLauncher(p.agents, p.settings, BudgetGate(p.mail, p.pauses, p.budgets, p.delivery, p.notices, console), single, count)
    reaper = PollingRunReaper(
        ExitWatcher(p.agents, p.settings, run_clock), tracker, guard, strays,
        RunSettlement(p.agents, p.batches, failures, p.snapshots, run_events, console, p.layout, CreditingThrottles(p.log_reader, p.mail, p.delivery, console)),
        run_clock,
        ShutdownTerminator(p.batches, run_events, tracker),
    )
    return Lifecycle(starter, reaper)


@dataclass(frozen=True)
class LoopPorts:
    """Everything the loop takes from the rest of the system besides what the run lifecycle takes."""

    lifecycle: LifecyclePorts
    label: ProcessLabel
    lock: SchedulerLock
    marker: ExitMarker
    ignore: IgnoreList
    judge: OrphanJudge
    signaller: ProcessSignaller
    retention: EventRetention
    queue: HumanQueue
    runnable: RunnableQuery
    open_work: OpenWork
    waiting: WaitingOnUser
    ladder: StallLadder
    reviewer: HealthReviewer
    version: Provider[str]


def assemble_loop(ports: LoopPorts, run_clock: Clock, cadence: Clock, console: Console, state: LoopState, memory: LoopMemory) -> HeartbeatLoop:
    """The loop over ``ports``. ``run_clock`` times the runs, ``cadence`` the stall ladder, the review, the heartbeat, the grace and the guard;
    ``state`` is what the loop owns and ``memory`` what its collaborators remember (both survive a loop made again over other ports)."""
    p, life = ports, ports.lifecycle
    events = SchedulerEvents(life.events)
    guard = LoggingPhaseGuard(console, events, cadence, memory.guard)
    lifecycle = assemble(life, run_clock, console, guard, state.count)
    settler = LedgerOrphanSettler(life.registry, p.judge, p.signaller, LogRunNotes(life.logs), events, console)
    work = QueriedWork(p.open_work, p.runnable, p.waiting)
    phases = [
        FailureLedgerRepair(life.failure_counter, console),
        ReapPhase(lifecycle.reaper),
        GuardedPhase("orphan check", OrphanCheck(settler), guard),
        FundedResume(life.agents, life.pauses, life.budgets, console),
        RunLaunch(lifecycle.starter),
        GuardedPhase("stall check", StallCheck(p.ladder, console), guard),
        GuardedPhase("health review", ReviewCheck(p.reviewer, cadence, console), guard),
        GuardedPhase("event log upkeep", HeartbeatUpkeep(cadence, life.settings, events, p.retention, p.queue, p.runnable, memory.upkeep), guard),
    ]
    session = ClaimedSession(
        ProcessClaim(p.label, p.lock, p.marker, p.ignore), SessionAnnouncer(events, life.settings, p.version), settler,
        BatchRecovery(life.batches, console), lifecycle.reaper,
    )
    grace = GraceWait(work, life.settings, cadence, console, memory.grace)
    return HeartbeatLoop(session, phases, lifecycle, work, GraceExitPolicy(work, grace, p.marker, console), PollPacing(life.settings, run_clock), state)
