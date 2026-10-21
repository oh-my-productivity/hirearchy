"""D of SOLID: every class with behaviour subclasses the port it implements (ARCHITECTURE.md R6), and the data is plain data."""

from __future__ import annotations

import inspect

from hirearchy.daemon import EXIT_FILE, FINISHED, ExitMarker, SchedulerCommand, SchedulerControl, SchedulerLock, SchedulerState, SchedulerStatus
from hirearchy.daemon import api
from hirearchy.daemon._children import ChildRegistry
from hirearchy.daemon._command import VenvSchedulerCommand
from hirearchy.daemon._control import DetachedSchedulerControl
from hirearchy.daemon._identity import SchedulerIdentity
from hirearchy.daemon._launch import DetachedLauncher
from hirearchy.daemon._lock import PidFileSchedulerLock
from hirearchy.daemon._marker import FileExitMarker
from hirearchy.daemon._ports import Children, LaunchEnvironment, LaunchSite, SchedulerLauncher, SchedulerRecognizer, SchedulerStopper, StartupWatch
from hirearchy.daemon._site import RuntimeLaunchSite, ScrubbedLaunchEnvironment
from hirearchy.daemon._status import PidFileSchedulerStatus
from hirearchy.daemon._stop import SignalSchedulerStopper
from hirearchy.daemon._watch import PidFileStartupWatch


def test_each_class_subclasses_the_port_it_implements() -> None:
    assert SchedulerStatus in PidFileSchedulerStatus.__mro__
    assert SchedulerControl in DetachedSchedulerControl.__mro__
    assert SchedulerLock in PidFileSchedulerLock.__mro__
    assert ExitMarker in FileExitMarker.__mro__
    assert SchedulerCommand in VenvSchedulerCommand.__mro__
    assert SchedulerRecognizer in SchedulerIdentity.__mro__
    assert Children in ChildRegistry.__mro__
    assert SchedulerLauncher in DetachedLauncher.__mro__
    assert SchedulerStopper in SignalSchedulerStopper.__mro__
    assert LaunchSite in RuntimeLaunchSite.__mro__ and LaunchEnvironment in ScrubbedLaunchEnvironment.__mro__
    assert StartupWatch in PidFileStartupWatch.__mro__


def test_the_scheduler_state_is_a_plain_value_with_defaults() -> None:
    assert SchedulerState("stopped") == ("stopped", None, None, "")
    assert SchedulerState("running", 7, "x")._asdict() == {"state": "running", "pid": 7, "since": "x", "detail": ""}


def test_the_constants_are_what_the_files_and_the_messages_say() -> None:
    assert EXIT_FILE == ".runtime/scheduler.exit" and FINISHED == "finished: no open tasks"


def test_the_public_surface_is_exactly_the_api() -> None:
    assert sorted(api.__all__) == sorted(
        ["EXIT_FILE", "ExitMarker", "FINISHED", "SchedulerCommand", "SchedulerControl", "SchedulerLock", "SchedulerState", "SchedulerStatus"]
    )


def test_no_class_takes_more_than_seven_collaborators() -> None:
    classes = [PidFileSchedulerStatus, DetachedLauncher, SignalSchedulerStopper, RuntimeLaunchSite, PidFileStartupWatch]
    for cls in classes:
        assert len(inspect.signature(cls).parameters) <= 7, cls.__name__

