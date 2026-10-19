"""The run lifecycle of the scheduler over the ports of a runtime (ARCHITECTURE.md 6.3: ``SubprocessRunStarter`` and ``PollingRunReaper`` with their roles).

The starter and the reaper are not ports of the runtime: they need what is the scheduler's own (its output, its guard, its command builder, the run
clock and the count of the runs it started), so they are made per scheduler. ``lifecycle_of`` serves the legacy ``Scheduler``, which is given an ``Org``
whose ``runtime`` tests replace; ``build_scheduler`` of the loop (D-sched-2) will make them over the runtime it opens.
"""

from __future__ import annotations

from ..access import ModelResolver
from ..agents import AgentDirectory
from ..budget import BudgetQuery
from ..delivery import MessageDelivery
from ..eligibility import FailureCounter, PauseStore
from ..kernel import EventSink, OrgLayout
from ..kernel._system import SystemClock
from ..kiro import RunCommandBuilder
from ..mail import BatchStore, MailboxReader
from ..processes import ProcessInspector, ProcessSpawner
from ..prompts import RunPromptBuilder
from ..runs import RunLogWriter, RunRegistry
from ..scheduler._assembly import Lifecycle, LifecyclePorts, assemble
from ..scheduler._ports import Console, PhaseGuard
from ..scheduler._run import RunCount
from ..settings import OrgSettings
from ..snapshots import OrgSnapshotter
from ..strays import StrayProbe, StrayRegistry
from ..templates import Notices
from ._builder import Builder
from ._lazy import PortResolver
from .runtime import OrgRuntime
from .wire_stalls import RuntimePorts


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


def register(b: Builder) -> None:
    """The lifecycle has no port of its own yet (see the module docstring)."""
