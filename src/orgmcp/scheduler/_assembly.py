"""The one place where the roles of the run lifecycle are put together (called by ``app.wire_scheduler`` and by ``testing``)."""

from __future__ import annotations

from dataclasses import dataclass

from ..access import ModelResolver
from ..agents import AgentDirectory
from ..budget import BudgetQuery
from ..delivery import MessageDelivery
from ..eligibility import FailureCounter, PauseStore
from ..kernel import Clock, EventSink, OrgLayout
from ..kiro import RunCommandBuilder
from ..mail import BatchStore, MailboxReader
from ..processes import ProcessInspector, ProcessSpawner
from ..prompts import RunPromptBuilder
from ..runs import RunLogWriter, RunRegistry
from ..settings import OrgSettings
from ..snapshots import OrgSnapshotter
from ..strays import StrayProbe, StrayRegistry
from ..templates import Notices
from ._admission import BudgetGate
from ._events import LifecycleEvents, SchedulerEvents
from ._failures import CountingFailures, PausingEscalation
from ._ports import Console, PhaseGuard, RunReaper, RunStarter
from ._reaper import ExitWatcher, PollingRunReaper, RunSettlement, ShutdownTerminator
from ._run import RunCount
from ._starter import AgentRunLauncher, BatchPreparer, CommandSpawner, SingleRunStarter, StartAnnouncer, StartFailureHandler
from ._strays import StrayCheck
from ._tracker import RunTracker


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


@dataclass(frozen=True)
class Lifecycle:
    """The two halves of a run's life, which the loop holds."""

    starter: RunStarter
    reaper: RunReaper


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
        RunSettlement(p.agents, p.batches, failures, p.snapshots, run_events, console, p.layout), run_clock,
        ShutdownTerminator(p.batches, run_events, tracker),
    )
    return Lifecycle(starter, reaper)
