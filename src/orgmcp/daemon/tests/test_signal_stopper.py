"""``SignalSchedulerStopper``: SIGTERM the scheduler of the organization - after checking that it is - and wait for it to end."""

from __future__ import annotations

import signal
from pathlib import Path

import pytest

from orgmcp.daemon import SchedulerState
from orgmcp.daemon._children import ChildRegistry
from orgmcp.daemon._stop import SignalSchedulerStopper
from orgmcp.daemon.testing import FakeSchedulerStatus
from orgmcp.kernel import OrgError
from orgmcp.kernel.testing import FakeClock
from orgmcp.processes import ProcessDenied, ProcessGone, ProcessHandle, ProcessSignaller
from orgmcp.processes.testing import FakeProcessTable

pytestmark = pytest.mark.xfail(strict=True, reason="red: C-daemon")

RUNNING = "2026-10-18 10:00:00Z"


class Rig:
    def __init__(self, tmp_path: Path) -> None:
        self.clock = FakeClock()
        self.table = FakeProcessTable(self.clock)
        self.children = ChildRegistry()
        self.handle: ProcessHandle = self.table.spawn_detached(["orgmcp", "run"], cwd=tmp_path, env={}, log=tmp_path / "log")
        self.pid = self.handle.pid
        self.status = FakeSchedulerStatus(SchedulerState("running", self.pid, RUNNING))
        self.stopper = SignalSchedulerStopper(self.status, self.table, self.table, self.children, self.clock)

    def waited(self) -> float:
        return round(self.clock.monotonic(), 2)


def test_nothing_is_signalled_when_no_scheduler_runs(tmp_path: Path) -> None:
    rig = Rig(tmp_path)
    rig.status.current = SchedulerState("stopped")
    assert rig.stopper.stop(15.0) == "no scheduler is running for this org"
    assert rig.table.signals == []


def test_a_process_that_is_not_verified_is_never_signalled(tmp_path: Path) -> None:
    rig = Rig(tmp_path)
    rig.status.current = SchedulerState("unverified", rig.pid, RUNNING, "its command line is 'vim'")
    with pytest.raises(OrgError) as raised:
        rig.stopper.stop(15.0)
    assert str(raised.value) == (
        f"not signalling pid {rig.pid}: it is alive but not verified to be this org's scheduler (its command line is 'vim'). "
        f"If it is, stop it yourself (kill {rig.pid})"
    )
    assert rig.table.signals == [] and rig.table.is_alive(rig.pid)


def test_the_scheduler_is_sent_sigterm_and_waited_for(tmp_path: Path) -> None:
    rig = Rig(tmp_path)
    assert rig.stopper.stop(15.0) == f"scheduler stopped (pid {rig.pid})"
    assert rig.table.signals == [("process", rig.pid, signal.SIGTERM)]


def test_a_scheduler_that_needs_a_moment_is_waited_for_in_tenths_of_a_second(tmp_path: Path) -> None:
    rig = Rig(tmp_path)
    rig.table.ignore_term(rig.pid)
    rig.table.exit_after(rig.pid, 0.5)  # it shuts down by itself after a while
    rig.children.adopt(rig.handle)
    assert rig.stopper.stop(15.0) == f"scheduler stopped (pid {rig.pid})"
    assert 0.5 <= rig.waited() < 0.7


def test_the_children_this_process_started_are_reaped_while_waiting(tmp_path: Path) -> None:
    rig = Rig(tmp_path)
    rig.children.adopt(rig.handle)  # a zombie after SIGTERM until its parent looks
    assert rig.stopper.stop(15.0) == f"scheduler stopped (pid {rig.pid})"


def test_a_scheduler_that_is_still_shutting_down_is_reported_after_the_wait(tmp_path: Path) -> None:
    rig = Rig(tmp_path)
    rig.table.ignore_term(rig.pid)
    text = rig.stopper.stop(1.0)
    assert text == (
        f"sent SIGTERM to the scheduler (pid {rig.pid}); it is still shutting down (it interrupts agent runs first). Check status() shortly"
    )
    assert 1.0 <= rig.waited() < 1.2 and rig.table.is_alive(rig.pid)


def test_a_process_table_that_cannot_be_read_ends_the_wait(tmp_path: Path) -> None:
    rig = Rig(tmp_path)
    rig.table.ignore_term(rig.pid)
    blind = SignalSchedulerStopper(rig.status, rig.table, rig.table.without_ps(), rig.children, rig.clock)
    assert blind.stop(15.0).startswith(f"sent SIGTERM to the scheduler (pid {rig.pid});")
    assert rig.waited() < 1


class Vanished(ProcessSignaller):
    """The scheduler ended between the check and the signal."""

    def kill_group(self, pgid: int, wait: float = 5.0) -> bool:
        raise AssertionError("a group is not killed here")

    def terminate(self, pid: int) -> None:
        raise ProcessGone(f"pid {pid} is already gone")


class Refusing(ProcessSignaller):
    def kill_group(self, pgid: int, wait: float = 5.0) -> bool:
        raise AssertionError("a group is not killed here")

    def terminate(self, pid: int) -> None:
        raise ProcessDenied(f"not allowed to signal pid {pid}")


def test_a_scheduler_that_has_just_ended_is_reported_as_gone(tmp_path: Path) -> None:
    rig = Rig(tmp_path)
    stopper = SignalSchedulerStopper(rig.status, Vanished(), rig.table, rig.children, rig.clock)
    assert stopper.stop(15.0) == f"scheduler (pid {rig.pid}) was already gone"


def test_a_scheduler_of_someone_else_cannot_be_signalled(tmp_path: Path) -> None:
    rig = Rig(tmp_path)
    stopper = SignalSchedulerStopper(rig.status, Refusing(), rig.table, rig.children, rig.clock)
    with pytest.raises(OrgError, match=rf"^not allowed to signal pid {rig.pid}$"):
        stopper.stop(15.0)


def test_a_wait_of_zero_does_not_wait(tmp_path: Path) -> None:
    rig = Rig(tmp_path)
    rig.table.ignore_term(rig.pid)
    assert rig.stopper.stop(0.0).startswith("sent SIGTERM")
    assert rig.waited() == 0
