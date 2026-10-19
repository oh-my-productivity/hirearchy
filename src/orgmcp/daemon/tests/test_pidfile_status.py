"""``PidFileSchedulerStatus`` over a scripted process table: what the contract does not show - zombies, command lines that cannot be read, a symlinked
root, the reaping of children, and what is asked of whom (and only when it is needed)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from orgmcp.attention import Waiting
from orgmcp.attention.testing import FixedWaiting
from orgmcp.daemon import FINISHED, SchedulerState
from orgmcp.daemon._children import ChildRegistry
from orgmcp.daemon._identity import SchedulerIdentity
from orgmcp.daemon._marker import FileExitMarker
from orgmcp.daemon._status import PidFileSchedulerStatus
from orgmcp.daemon.testing import AT, SINCE, FixedTasks
from orgmcp.kernel import OrgPaths
from orgmcp.kernel.testing import FakeClock, fs_atomic_writer
from orgmcp.processes.testing import FakeProcessTable

pytestmark = pytest.mark.xfail(strict=True, reason="red: C-daemon")


class Rig:
    def __init__(self, tmp_path: Path, root: Path | None = None) -> None:
        self.root = root or tmp_path / "org"
        self.root.mkdir(exist_ok=True)
        self.layout = OrgPaths(self.root)
        self.table = FakeProcessTable(FakeClock())
        self.children = ChildRegistry()
        self.tasks = FixedTasks()
        self.waiting = FixedWaiting()
        self.marker = FileExitMarker(self.layout, fs_atomic_writer(tmp_path).writer)
        self.status = PidFileSchedulerStatus(
            self.layout, self.table, SchedulerIdentity(), self.children, self.marker, self.tasks, self.waiting,
        )

    def pidfile(self, text: str, at: float = AT.timestamp()) -> Path:
        path = self.root / ".runtime" / "scheduler.pid"
        path.parent.mkdir(exist_ok=True)
        path.write_text(text)
        os.utime(path, (at, at))
        return path


def test_a_zombie_is_a_process_that_is_gone(tmp_path: Path) -> None:
    rig = Rig(tmp_path)
    rig.table.add(9001, state="Z", command="orgmcp --root x run")
    rig.pidfile("9001")
    assert rig.status.state() == SchedulerState("stopped")


def test_the_pid_is_read_with_the_blanks_around_it_dropped(tmp_path: Path) -> None:
    rig = Rig(tmp_path)
    rig.table.add(9001, command=f"orgmcp --root {rig.root} run")
    rig.pidfile(" 9001\n")
    assert rig.status.state() == SchedulerState("running", 9001, SINCE)


def test_since_is_the_modification_time_of_the_pidfile_in_utc(tmp_path: Path) -> None:
    rig = Rig(tmp_path)
    rig.table.add(9001, command=f"orgmcp --root {rig.root} run")
    rig.pidfile("9001", at=1_800_000_000.0)  # 2027-01-15 08:00:00 UTC
    assert rig.status.state().since == "2027-01-15 08:00:00Z"


def test_a_process_without_a_command_line_is_unverified(tmp_path: Path) -> None:
    rig = Rig(tmp_path)
    rig.table.add(9001, command="")
    rig.pidfile("9001")
    assert rig.status.state() == SchedulerState("unverified", 9001, SINCE, "its command line is unknown")
    assert rig.status.describe() == (
        "scheduler: unknown - .runtime/scheduler.pid names pid 9001, which is alive but not verified to be this org's scheduler "
        "(its command line is unknown); not trusted"
    )


def test_a_process_table_that_cannot_be_read_leaves_the_pid_unverified(tmp_path: Path) -> None:
    rig = Rig(tmp_path)
    rig.table.add(9001, command=f"orgmcp --root {rig.root} run")
    rig.pidfile("9001")
    rig.table.ps_works = False
    assert rig.status.state() == SchedulerState("unverified", 9001, SINCE, "the process table could not be read")


def test_the_same_directory_under_another_spelling_is_this_organization(tmp_path: Path) -> None:
    real = tmp_path / "real" / "org"
    real.mkdir(parents=True)
    link = tmp_path / "link"
    link.symlink_to(tmp_path / "real")  # like /tmp -> /private/tmp
    rig = Rig(tmp_path, real)
    rig.table.add(9001, command=f"/v/bin/orgmcp --root {link}/org run --until-idle")
    rig.table.add(9002, command=f"/v/bin/orgmcp --root={link}/org run")
    rig.pidfile("9001")
    assert rig.status.state().state == "running"
    rig.pidfile("9002")
    assert rig.status.state().state == "running"


def test_a_relative_root_cannot_be_compared_and_is_unverified(tmp_path: Path) -> None:
    rig = Rig(tmp_path)
    rig.table.add(9001, command="/v/bin/orgmcp --root org run")
    rig.pidfile("9001")
    assert rig.status.state().state == "unverified"


def test_asking_for_the_state_reaps_the_children_that_ended(tmp_path: Path) -> None:
    rig = Rig(tmp_path)
    handle = rig.table.spawn_detached(["orgmcp", "run"], cwd=tmp_path, env={}, log=tmp_path / "log")
    rig.children.adopt(handle)
    rig.table.exit(handle.pid, 0)
    rig.pidfile(str(handle.pid))
    assert rig.status.state() == SchedulerState("stopped")
    assert rig.table.info(handle.pid) is None  # looked at by its parent


def test_the_process_table_is_not_asked_without_a_usable_pid(tmp_path: Path) -> None:
    rig = Rig(tmp_path)
    rig.table.ps_works = False  # a call would raise
    assert rig.status.state() == SchedulerState("stopped")
    rig.pidfile("1")
    assert rig.status.state() == SchedulerState("stopped")


def test_the_tasks_are_asked_only_when_there_is_a_reason_to_doubt(tmp_path: Path) -> None:
    rig = Rig(tmp_path)
    assert rig.status.exit_reason() == "" and rig.tasks.asked == []
    rig.marker.write(FINISHED)
    assert rig.status.exit_reason() == FINISHED and rig.tasks.asked == ["root"]


def test_what_waits_for_the_user_is_asked_only_when_nothing_else_explains_the_stop(tmp_path: Path) -> None:
    rig = Rig(tmp_path)
    rig.waiting.waiting = Waiting("waiting on you: x", "Your options: y")
    rig.marker.write(FINISHED)
    assert rig.status.describe() == f"scheduler: stopped ({FINISHED})" and rig.waiting.asked == []
    rig.marker.clear()
    assert rig.status.describe() == "scheduler: stopped (waiting on you: x)" and rig.waiting.asked == [(None, (), True)]


def test_a_running_scheduler_is_not_asked_why_it_stopped(tmp_path: Path) -> None:
    rig = Rig(tmp_path)
    rig.table.add(9001, command=f"orgmcp --root {rig.root} run")
    rig.pidfile("9001")
    rig.marker.write(FINISHED)
    rig.status.describe()
    assert rig.waiting.asked == [] and rig.tasks.asked == []
