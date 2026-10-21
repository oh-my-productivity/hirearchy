"""``wire_daemon``: the runtime has the five ports of ``daemon``, built from the ports of the runtime; the schedulers this process started are one registry
for the whole process; and the status is built over the ports the runtime has."""

from __future__ import annotations

import sys
from pathlib import Path

from hirearchy.app import wiring
from hirearchy.attention import Waiting, WaitingOnUser
from hirearchy.attention.testing import FixedWaiting
from hirearchy.daemon import FINISHED, ExitMarker, SchedulerCommand, SchedulerControl, SchedulerLock, SchedulerState, SchedulerStatus
from hirearchy.daemon._command import VenvSchedulerCommand
from hirearchy.daemon._control import DetachedSchedulerControl
from hirearchy.daemon._lock import PidFileSchedulerLock
from hirearchy.daemon._marker import FileExitMarker
from hirearchy.daemon._status import PidFileSchedulerStatus
from hirearchy.daemon.testing import FakeSchedulerCommand, FixedTasks, MemoryExitMarker, ScriptedSchedulerSpawner
from hirearchy.kernel import OrgPaths
from hirearchy.kernel.testing import FakeClock
from hirearchy.mail import TaskQuery
from hirearchy.processes import ProcessInspector, ProcessSignaller, ProcessSpawner
from hirearchy.processes.testing import FakeProcessTable
from hirearchy.snapshots import IgnoreList
from hirearchy.snapshots.testing import MemoryIgnoreList


def test_the_runtime_has_the_five_ports(tmp_path: Path) -> None:
    runtime = wiring.open_runtime(tmp_path)
    assert isinstance(runtime.scheduler_status, PidFileSchedulerStatus) and isinstance(runtime.scheduler_status, SchedulerStatus)
    assert isinstance(runtime.scheduler_control, DetachedSchedulerControl) and isinstance(runtime.scheduler_control, SchedulerControl)
    assert isinstance(runtime.scheduler_lock, PidFileSchedulerLock) and isinstance(runtime.scheduler_lock, SchedulerLock)
    assert isinstance(runtime.exit_marker, FileExitMarker) and isinstance(runtime.exit_marker, ExitMarker)
    assert isinstance(runtime.scheduler_command, VenvSchedulerCommand) and isinstance(runtime.scheduler_command, SchedulerCommand)


def test_building_the_ports_does_no_io(tmp_path: Path) -> None:
    runtime = wiring.open_runtime(tmp_path)
    assert all(port is not None for port in (runtime.scheduler_status, runtime.scheduler_control, runtime.scheduler_lock, runtime.exit_marker))
    assert list(tmp_path.iterdir()) == []


def test_an_override_replaces_a_port(tmp_path: Path) -> None:
    fake = MemoryExitMarker("why\n")
    runtime = wiring.open_runtime(tmp_path, {ExitMarker: fake})
    assert runtime.exit_marker is fake
    assert isinstance(runtime.scheduler_command, VenvSchedulerCommand)


def test_the_command_is_the_one_of_this_virtual_environment_for_the_organization(tmp_path: Path) -> None:
    script = Path(sys.executable).with_name("hirearchy")
    program = [str(script)] if script.exists() else [sys.executable, "-m", "hirearchy"]
    runtime = wiring.open_runtime(tmp_path)
    assert runtime.scheduler_command.argv(3, True) == [*program, "--root", str(tmp_path), "run", "--max-runs", "3", "--until-done"]
    assert wiring.open_runtime(tmp_path).scheduler_command.argv(None, False) == [*program, "--root", str(tmp_path), "run"]


def test_the_schedulers_this_process_started_are_one_registry_for_every_runtime(tmp_path: Path) -> None:
    first, second = tmp_path / "a", tmp_path / "b"
    assert wiring.open_runtime(first).resources.children is wiring.open_runtime(second).resources.children is wiring.process_resources().children


def test_a_child_started_through_one_control_is_reaped_through_another_status(tmp_path: Path) -> None:
    """The registry is the process's: the scheduler a control started is reaped by whatever status asks next (the former ``scheduler._children``)."""
    org = tmp_path / "org"
    (org / ".runtime").mkdir(parents=True)
    table = FakeProcessTable(FakeClock())
    spawner = ScriptedSchedulerSpawner(table, OrgPaths(org))
    runtime = wiring.open_runtime(org, {ProcessSpawner: spawner, ProcessInspector: table, ProcessSignaller: table, IgnoreList: MemoryIgnoreList()})
    pid = runtime.scheduler_control.start()
    table.exit(pid, 0)
    other = wiring.open_runtime(org, {ProcessInspector: table})
    assert other.scheduler_status.state() == SchedulerState("stopped")
    assert table.info(pid) is None  # reaped by the second runtime's status


def test_the_status_and_the_control_decide_over_the_process_table_of_the_runtime(tmp_path: Path) -> None:
    org = tmp_path / "org"
    (org / ".runtime").mkdir(parents=True)
    table = FakeProcessTable(FakeClock())
    spawner = ScriptedSchedulerSpawner(table, OrgPaths(org))
    runtime = wiring.open_runtime(org, {
        ProcessSpawner: spawner, ProcessInspector: table, ProcessSignaller: table, IgnoreList: MemoryIgnoreList(),
        SchedulerCommand: FakeSchedulerCommand(OrgPaths(org), ["/v/bin/hirearchy"]),
    })
    assert runtime.scheduler_status.state() == SchedulerState("stopped")
    pid = runtime.scheduler_control.start(5, True)
    assert table.spawned[0].argv == ("/v/bin/hirearchy", "--root", str(org), "run", "--max-runs", "5", "--until-done")
    assert runtime.scheduler_status.state().pid == pid and runtime.scheduler_status.state().state == "running"
    assert runtime.scheduler_control.stop() == f"scheduler stopped (pid {pid})"


def test_the_ignore_list_of_the_runtime_keeps_the_runtime_files_out_of_the_snapshots_when_a_scheduler_starts(tmp_path: Path) -> None:
    org = tmp_path / "org"
    org.mkdir()
    table = FakeProcessTable(FakeClock())
    ignore = MemoryIgnoreList()
    runtime = wiring.open_runtime(org, {
        ProcessSpawner: ScriptedSchedulerSpawner(table, OrgPaths(org)), ProcessInspector: table, ProcessSignaller: table, IgnoreList: ignore,
        SchedulerCommand: FakeSchedulerCommand(OrgPaths(org)),
    })
    runtime.scheduler_control.start()
    assert ignore.text is not None and ".runtime/scheduler.log" in ignore.text.split() and ".runtime/scheduler.exit" in ignore.text.split()


def test_a_stopped_scheduler_is_explained_by_what_attention_says(tmp_path: Path) -> None:
    waiting = FixedWaiting(Waiting("waiting on you: x", "Your options: y"))
    runtime = wiring.open_runtime(tmp_path, {WaitingOnUser: waiting})
    assert runtime.scheduler_status.describe() == "scheduler: stopped (waiting on you: x)"


def test_the_status_follows_the_parts_the_runtime_was_opened_with(tmp_path: Path) -> None:
    """The status is built over the ports the runtime has (what stops a scheduler, if nothing else does, is what ``attention`` says over them)."""
    (tmp_path / ".runtime").mkdir()
    before = wiring.open_runtime(tmp_path).scheduler_status
    assert before.describe() == "scheduler: stopped"
    after = wiring.open_runtime(tmp_path, {ExitMarker: MemoryExitMarker(FINISHED + "\n"), TaskQuery: FixedTasks()}).scheduler_status
    assert after.describe() == f"scheduler: stopped ({FINISHED})"
    stale = wiring.open_runtime(tmp_path, {ExitMarker: MemoryExitMarker(FINISHED + "\n"), TaskQuery: FixedTasks(root_waits=True)}).scheduler_status
    assert stale.exit_reason() == ""  # root waits for a result again: the reason of the exit is stale
    assert stale.describe().startswith('scheduler: stopped (waiting on you: "Ship it"')  # and attention, over the same tasks, says why
