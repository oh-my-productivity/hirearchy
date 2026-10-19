"""The scheduler over the ports of a runtime (ARCHITECTURE.md 6.3): the loop, and the run lifecycle it holds.

The loop and its starter and reaper are not ports of the runtime (``NOT_A_FIELD`` of ``fields_scheduler``): they need what is the scheduler's own (its
output, its command builder, the run clock and the cadence clock, the table of runs and the count of the runs it started), so they are made per
scheduler. ``loop_of`` makes the loop over a runtime; the legacy ``Scheduler``, which is given an ``Org`` whose ``runtime`` tests replace, calls it again
when that happens, handing the new loop the state and the memory of the old. ``lifecycle_of`` makes the lifecycle alone.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import TypeVar, cast

from ..access import ModelResolver
from ..agents import AgentDirectory
from ..attention import HumanQueue, OpenWork, WaitingOnUser
from ..budget import BudgetQuery
from ..daemon import ExitMarker, SchedulerLock
from ..delivery import MessageDelivery
from ..eligibility import FailureCounter, PauseStore, RunnableQuery
from ..kernel import Clock, EventSink, OrgLayout
from ..kernel._system import SystemClock
from ..kiro import RunCommandBuilder
from ..mail import BatchStore, MailboxReader, MailFingerprint, TaskQuery
from ..processes import OrphanJudge, ProcessInspector, ProcessSignaller, ProcessSpawner
from ..prompts import RunPromptBuilder
from ..review import HealthReviewer
from ..runs import RunLogWriter, RunRegistry
from ..scheduler._assembly import LifecyclePorts, LoopPorts, assemble, assemble_loop
from ..scheduler._loop import HeartbeatLoop
from ..scheduler._ports import Console, Lifecycle, PhaseGuard
from ..scheduler._run import LoopMemory, LoopState, RunCount
from ..scheduler._upkeep import package_version
from ..settings import OrgSettings
from ..snapshots import IgnoreList, OrgSnapshotter
from ..stalls import StallLadder
from ..stalls._views import FingerprintTaskViews
from ..strays import StrayProbe, StrayRegistry
from ..telemetry import EventRetention, ProcessLabel
from ..templates import Notices
from ._builder import Builder
from ._lazy import PortResolver
from .runtime import OrgRuntime
from .wire_stalls import RuntimePorts, ladder_on

T = TypeVar("T")


def lifecycle_ports(b: PortResolver, commands: RunCommandBuilder) -> LifecyclePorts:
    """What the lifecycle takes from the ports ``b`` builds, and the command builder it is given."""
    return LifecyclePorts(
        b.get(AgentDirectory), b.get(OrgSettings), b.get(MailboxReader), b.get(BatchStore), b.get(PauseStore), b.get(FailureCounter),
        b.get(BudgetQuery), b.get(MessageDelivery), b.get(Notices), b.get(ModelResolver), b.get(RunLogWriter), b.get(RunRegistry),
        b.get(RunPromptBuilder), b.get(StrayProbe), b.get(StrayRegistry), b.get(OrgSnapshotter), b.get(EventSink), b.get(ProcessSpawner),
        b.get(ProcessInspector), b.get(OrgLayout), commands,
    )


def lifecycle_of(runtime: OrgRuntime, commands: RunCommandBuilder, console: Console, guard: PhaseGuard, count: RunCount) -> Lifecycle:
    """The starter and the reaper over the ports of ``runtime``; runs are timed with the system clock (the run clock), not with the cadence of the loop."""
    return assemble(lifecycle_ports(RuntimePorts(runtime), commands), SystemClock(), console, guard, count)


class OverridePorts(PortResolver):
    """The ports of ``inner``, except the ones in ``overrides`` (what a test puts in place of a port of the runtime, as ``open_runtime`` overrides do)."""

    def __init__(self, inner: PortResolver, overrides: Mapping[type, object]) -> None:
        self._inner, self._overrides = inner, overrides

    @property
    def root(self) -> Path:
        return self._inner.root

    def get(self, port: type[T]) -> T:
        return self._overrides[port] if port in self._overrides else self._inner.get(port)  # type: ignore[return-value]


def loop_ports(b: PortResolver, commands: RunCommandBuilder, ladder: StallLadder) -> LoopPorts:
    """What the loop takes from the ports ``b`` builds, and the command builder and the stall ladder (timed by the cadence clock) it is given."""
    return LoopPorts(
        lifecycle_ports(b, commands), b.get(ProcessLabel), b.get(SchedulerLock), b.get(ExitMarker), b.get(IgnoreList), b.get(OrphanJudge),
        b.get(ProcessSignaller), b.get(EventRetention), b.get(HumanQueue), b.get(RunnableQuery), b.get(OpenWork), b.get(WaitingOnUser),
        ladder, b.get(HealthReviewer), package_version,
    )


def loop_of(
    runtime: OrgRuntime, commands: RunCommandBuilder, console: Console, cadence: Clock, state: LoopState, memory: LoopMemory | None = None,
    overrides: Mapping[type, object] | None = None,
) -> HeartbeatLoop:
    """The loop over the ports of ``runtime``. Runs are timed with the system clock (the run clock), not with ``cadence``; ``state`` and ``memory`` are what
    the loop owns and what its collaborators remember: pass the ones of a loop made before to go on where it was. ``overrides`` put other objects in the
    place of ports of the runtime (a test's failing ladder)."""
    memory = memory or LoopMemory()
    ports = OverridePorts(RuntimePorts(runtime), overrides or {})
    stalls = (overrides or {}).get(StallLadder)  # a ladder put in place of the runtime's is not timed again
    if stalls is None:
        views = memory.stall_views
        memory.stall_views = fresh = (  # the memo of the task views goes on over the ports of the new runtime
            FingerprintTaskViews(ports.get(TaskQuery), ports.get(MailFingerprint)) if views is None
            else cast(FingerprintTaskViews, views).rebound(ports.get(TaskQuery), ports.get(MailFingerprint))
        )
        stalls = ladder_on(ports, cadence, fresh)
    return assemble_loop(loop_ports(ports, commands, cast(StallLadder, stalls)), SystemClock(), cadence, console, state, memory)


def register(b: Builder) -> None:
    """The loop has no port of its own (see the module docstring)."""
