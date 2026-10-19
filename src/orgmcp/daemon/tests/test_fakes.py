"""The fakes a consumer's test uses instead of a process: each answers as the real one does for the state it is given and keeps what it was asked."""

from __future__ import annotations

from pathlib import Path

import pytest

from orgmcp.attention import Waiting
from orgmcp.attention.testing import FixedWaiting
from orgmcp.daemon import ExitMarker, SchedulerCommand, SchedulerControl, SchedulerLock, SchedulerState, SchedulerStatus
from orgmcp.daemon.testing import (
    FakeSchedulerCommand,
    FakeSchedulerControl,
    FakeSchedulerStatus,
    FixedSchedulerCommand,
    FixedTasks,
    MemoryExitMarker,
    MemorySchedulerLock,
    RecordingSchedulerCommand,
    ScriptedSchedulerSpawner,
)
from orgmcp.kernel import OrgError, OrgPaths
from orgmcp.processes.testing import FakeProcessTable

RUNNING = SchedulerState("running", 7000, "2026-10-18 10:00:00Z")


def test_the_fakes_are_the_ports(tmp_path: Path) -> None:
    assert isinstance(FakeSchedulerStatus(), SchedulerStatus) and SchedulerStatus in FakeSchedulerStatus.__mro__
    assert isinstance(FakeSchedulerControl(), SchedulerControl) and SchedulerControl in FakeSchedulerControl.__mro__
    assert isinstance(FixedSchedulerCommand(["a"]), SchedulerCommand) and SchedulerCommand in FixedSchedulerCommand.__mro__
    assert isinstance(FakeSchedulerCommand(OrgPaths(tmp_path)), SchedulerCommand) and SchedulerCommand in FakeSchedulerCommand.__mro__
    assert isinstance(RecordingSchedulerCommand(FixedSchedulerCommand(["a"])), SchedulerCommand)
    assert isinstance(MemoryExitMarker(), ExitMarker) and ExitMarker in MemoryExitMarker.__mro__
    assert isinstance(MemorySchedulerLock(FakeProcessTable()), SchedulerLock) and SchedulerLock in MemorySchedulerLock.__mro__


# ------------------------------------------------------------------------------ FakeSchedulerStatus


def test_the_status_is_stopped_until_it_is_told_otherwise() -> None:
    fake = FakeSchedulerStatus()
    assert fake.state() == SchedulerState("stopped") and fake.describe() == "scheduler: stopped" and fake.exit_reason() == ""


def test_the_status_answers_the_state_it_holds_and_counts_the_questions() -> None:
    fake = FakeSchedulerStatus(RUNNING)
    assert fake.state() is RUNNING and fake.state() is RUNNING and fake.asked == 2
    assert fake.describe() == "scheduler: running (pid 7000, since 2026-10-18 10:00:00Z)"
    fake.current = SchedulerState("unverified", 5, "x", "its command line is 'vim'")
    assert fake.describe().startswith("scheduler: unknown - .runtime/scheduler.pid names pid 5,")


def test_the_status_explains_a_stop_by_the_reason_then_by_what_waits_for_the_user() -> None:
    fake = FakeSchedulerStatus(waiting=FixedWaiting(Waiting("waiting on you: x", "o")))
    assert fake.describe() == "scheduler: stopped (waiting on you: x)"
    fake.reason = "finished: no open tasks"
    assert fake.exit_reason() == "finished: no open tasks" and fake.describe() == "scheduler: stopped (finished: no open tasks)"
    fake.open_tasks = True  # the reason is only true while root has no task that was not answered
    assert fake.exit_reason() == "" and fake.describe() == "scheduler: stopped (waiting on you: x)"


# ------------------------------------------------------------------------------ FakeSchedulerControl


def test_a_start_makes_the_status_running_and_is_recorded() -> None:
    control = FakeSchedulerControl(pid=100)
    assert control.start(3, True) == 100
    assert control.status.state().state == "running" and control.status.state().pid == 100
    assert control.starts == [(3, True)]
    assert control.status.state().since == "2026-10-18 10:00:00Z"


def test_pids_count_up_from_the_first() -> None:
    control = FakeSchedulerControl(pid=100)
    control.start()
    control.stop()
    assert control.start() == 101


def test_a_start_is_refused_as_the_real_one_refuses_it() -> None:
    control = FakeSchedulerControl(FakeSchedulerStatus(RUNNING))
    with pytest.raises(OrgError, match="already running"):
        control.start()
    control.status.current = SchedulerState("unverified", 5, "x", "d")
    with pytest.raises(OrgError, match="^not starting"):
        control.start()
    with pytest.raises(OrgError, match="^max_runs must be 0 or more$"):
        control.start(-1)
    assert control.starts == []


def test_a_stop_signals_the_scheduler_and_is_recorded() -> None:
    control = FakeSchedulerControl(FakeSchedulerStatus(RUNNING))
    assert control.stop(2.0) == "scheduler stopped (pid 7000)"
    assert control.signalled == [7000] and control.stops == [2.0] and control.status.state().state == "stopped"
    assert control.stop() == "no scheduler is running for this org" and control.stops == [2.0, 15.0]


def test_a_stop_never_signals_a_process_that_is_not_trusted() -> None:
    control = FakeSchedulerControl(FakeSchedulerStatus(SchedulerState("unverified", 5, "x", "d")))
    with pytest.raises(OrgError, match="^not signalling pid 5"):
        control.stop()
    assert control.signalled == []


# ------------------------------------------------------------------------------ the commands


def test_the_fixed_command_is_what_it_was_given_whatever_it_is_asked() -> None:
    command = FixedSchedulerCommand(["python", "-c", "pass"])
    got = command.argv(3, True)
    got.append("x")
    assert command.argv(None, False) == ["python", "-c", "pass"] and command.calls == [(3, True), (None, False)]


def test_the_fake_command_has_the_flags_of_the_real_one(tmp_path: Path) -> None:
    command = FakeSchedulerCommand(OrgPaths(tmp_path), ["/v/orgmcp"])
    assert command.argv(2, True) == ["/v/orgmcp", "--root", str(tmp_path), "run", "--max-runs", "2", "--until-done"]
    assert command.calls == [(2, True)]


def test_the_recording_command_passes_the_question_on_and_keeps_both() -> None:
    inner = FixedSchedulerCommand(["a", "b"])
    command = RecordingSchedulerCommand(inner)
    assert command.argv(1, False) == ["a", "b"]
    assert command.calls == [(1, False)] and command.issued == [["a", "b"]] and inner.calls == [(1, False)]


# ------------------------------------------------------------------------------ the rest


def test_the_memory_marker_holds_the_text_of_its_file() -> None:
    marker = MemoryExitMarker()
    assert marker.read() == "" and marker.text is None
    marker.write("why")
    assert marker.text == "why\n" and marker.read() == "why"
    marker.clear()
    assert marker.text is None


def test_only_root_waits_in_the_fixed_tasks() -> None:
    tasks = FixedTasks()
    assert tasks.outstanding("root") == [] and tasks.open_tasks("root") == [] and tasks.blocked_tasks("root") == []
    tasks.root_waits = True
    assert len(tasks.outstanding("root")) == 1 and tasks.outstanding("ceo") == []
    assert tasks.asked == ["root", "root", "ceo"]


def test_the_scripted_spawner_plays_the_scheduler_that_comes_up(tmp_path: Path) -> None:
    layout = OrgPaths(tmp_path)
    table = FakeProcessTable()
    spawner = ScriptedSchedulerSpawner(table, layout)
    handle = spawner.spawn_detached(["orgmcp", "run"], cwd=tmp_path, env={}, log=tmp_path / "scheduler.log")
    assert (tmp_path / ".runtime" / "scheduler.pid").read_text() == str(handle.pid)
    assert table.spawned[0].argv == ("orgmcp", "run") and table.is_alive(handle.pid)


def test_the_scripted_spawner_can_play_a_scheduler_that_ends_at_once_with_a_reason(tmp_path: Path) -> None:
    layout = OrgPaths(tmp_path)
    table = FakeProcessTable()
    spawner = ScriptedSchedulerSpawner(table, layout)
    spawner.starts_up, spawner.exit_reason = False, "finished: no open tasks"
    table.will_exit(0)
    handle = spawner.spawn_detached(["orgmcp", "run"], cwd=tmp_path, env={}, log=tmp_path / "scheduler.log")
    assert not (tmp_path / ".runtime" / "scheduler.pid").exists()
    assert (tmp_path / ".runtime" / "scheduler.exit").read_text() == "finished: no open tasks\n" and handle.poll() == 0
