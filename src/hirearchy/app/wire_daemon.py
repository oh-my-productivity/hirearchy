"""Providers of the ``daemon`` ports (ARCHITECTURE.md 6.1).

The schedulers this process started are a process resource (``ProcessResources.children``, the former ``scheduler._children``): every status and every control
of the process reaps and adopts through the same registry.
"""

from __future__ import annotations

import sys

from ..attention import WaitingOnUser
from ..daemon import ExitMarker, SchedulerCommand, SchedulerControl, SchedulerLock, SchedulerStatus
from ..daemon._command import VenvSchedulerCommand
from ..daemon._control import DetachedSchedulerControl
from ..daemon._identity import SchedulerIdentity
from ..daemon._launch import DetachedLauncher
from ..daemon._lock import PidFileSchedulerLock
from ..daemon._marker import FileExitMarker
from ..daemon._ports import SchedulerRecognizer
from ..daemon._site import RuntimeLaunchSite, ScrubbedLaunchEnvironment
from ..daemon._status import PidFileSchedulerStatus
from ..daemon._stop import SignalSchedulerStopper
from ..daemon._watch import PidFileStartupWatch
from ..kernel import AtomicWriter, Clock, Environment, OrgLayout
from ..mail import TaskQuery
from ..processes import ProcessInspector, ProcessSignaller, ProcessSpawner
from ..snapshots import IgnoreList
from ._builder import Builder
from ._lazy import PortResolver
from ._resources import ProcessResources


def identity() -> SchedulerRecognizer:
    """How a command line is recognised as the scheduler of an organization (it needs nothing)."""
    return SchedulerIdentity()


def exit_marker(b: PortResolver) -> FileExitMarker:
    """The marker over the layout and the atomic writer of ``b``."""
    return FileExitMarker(b.get(OrgLayout), b.get(AtomicWriter))


def command(b: PortResolver) -> VenvSchedulerCommand:
    """The command of this interpreter's virtual environment, for the organization of ``b``."""
    return VenvSchedulerCommand(b.get(OrgLayout), sys.executable)


def lock(b: PortResolver) -> PidFileSchedulerLock:
    """The pidfile lock over the layout and the process table of ``b``."""
    return PidFileSchedulerLock(b.get(OrgLayout), b.get(ProcessInspector))


def status(b: PortResolver, waiting: WaitingOnUser) -> PidFileSchedulerStatus:
    """The status over the layout, process table, marker and tasks of ``b``, explaining a stop by ``waiting``."""
    return PidFileSchedulerStatus(
        b.get(OrgLayout), b.get(ProcessInspector), identity(), b.get(ProcessResources).children, b.get(ExitMarker), b.get(TaskQuery), waiting,
    )


def control(b: PortResolver, scheduler_status: SchedulerStatus) -> DetachedSchedulerControl:
    """Start and stop over the ports of ``b``, deciding by ``scheduler_status``."""
    layout, marker, clock, children = b.get(OrgLayout), b.get(ExitMarker), b.get(Clock), b.get(ProcessResources).children
    launcher = DetachedLauncher(
        scheduler_status, RuntimeLaunchSite(layout, b.get(IgnoreList), marker, clock), ScrubbedLaunchEnvironment(layout, b.get(Environment)),
        b.get(SchedulerCommand), b.get(ProcessSpawner), PidFileStartupWatch(layout, marker, clock, b.get(ProcessInspector)),
    )
    return DetachedSchedulerControl(
        launcher, SignalSchedulerStopper(scheduler_status, b.get(ProcessSignaller), b.get(ProcessInspector), children, clock),
    )


def register(b: Builder) -> None:
    b.provide(ExitMarker, exit_marker)
    b.provide(SchedulerCommand, command)
    b.provide(SchedulerLock, lock)
    b.provide(SchedulerStatus, lambda b: status(b, b.get(WaitingOnUser)))
    b.provide(SchedulerControl, lambda b: control(b, b.get(SchedulerStatus)))
