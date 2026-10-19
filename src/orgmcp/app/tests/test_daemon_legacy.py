"""The legacy names of ``scheduler`` that stand for the scheduler as a process - ``scheduler_state``, ``describe_scheduler``, ``start_scheduler``,
``stop_scheduler``, ``scheduler_command``, ``EXIT_FILE``, ``FINISHED``, ``SchedulerState`` - and the pidfile and exit marker of ``Scheduler``. The texts and the
decisions are pinned by ``tests/test_bootstrap``, ``test_finish`` and ``test_assistant_ux`` (unchanged); here are the seams."""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from orgmcp import scheduler as sched_module
from orgmcp.app import Org
from orgmcp.daemon import EXIT_FILE, FINISHED, SchedulerState
from orgmcp.daemon.testing import FakeSchedulerCommand, MemoryExitMarker, MemorySchedulerLock, ScriptedSchedulerSpawner
from orgmcp.kernel import OrgError, OrgPaths
from orgmcp.kernel.testing import FakeClock
from orgmcp.processes.testing import FakeProcessTable
from orgmcp.scheduler import Scheduler
from orgmcp.snapshots.testing import MemoryIgnoreList


@pytest.fixture
def org(tmp_path: Path) -> Org:
    return Org.init(tmp_path / "org", "mission")


def with_table(org: Org) -> FakeProcessTable:
    """The organization's processes are a scripted table, and a started scheduler is the stand-in that writes its pid."""
    table = FakeProcessTable(FakeClock())
    org.runtime = dataclasses.replace(
        org.runtime, process_inspector=table, process_signaller=table, process_spawner=ScriptedSchedulerSpawner(table, OrgPaths(org.root)),
        ignore_list=MemoryIgnoreList(), scheduler_command=FakeSchedulerCommand(OrgPaths(org.root), ["/v/bin/orgmcp"]),
    )
    return table


def test_the_constants_and_the_state_are_those_of_the_package() -> None:
    assert getattr(sched_module, "EXIT_FILE") is EXIT_FILE and getattr(sched_module, "FINISHED") is FINISHED
    assert getattr(sched_module, "SchedulerState") is SchedulerState


def test_the_command_of_the_legacy_function_is_the_one_of_the_package(org: Org) -> None:
    assert sched_module.scheduler_command(org.root, 3, True) == org.runtime.scheduler_command.argv(3, True)
    assert sched_module.scheduler_command(org.root)[-3:] == ["--root", str(org.root), "run"]


def test_a_command_line_is_recognised_as_the_package_does(tmp_path: Path) -> None:
    assert sched_module._looks_like_scheduler_of("/v/bin/orgmcp --root /orgs/one run", Path("/orgs/one")) is True
    assert sched_module._looks_like_scheduler_of("/v/bin/orgmcp --root /orgs/two run", Path("/orgs/one")) is False


def test_the_state_and_the_description_ask_the_process_table_of_the_runtime(org: Org) -> None:
    table = with_table(org)
    assert sched_module.scheduler_state(org) == SchedulerState("stopped") and sched_module.describe_scheduler(org) == "scheduler: stopped"
    table.add(9001, command=f"/v/bin/orgmcp --root {org.root} run")
    (org.root / ".runtime").mkdir(exist_ok=True)
    (org.root / ".runtime" / "scheduler.pid").write_text("9001")
    state = sched_module.scheduler_state(org)
    assert (state.state, state.pid) == ("running", 9001)
    assert sched_module.describe_scheduler(org) == f"scheduler: running (pid 9001, since {state.since})"


def test_start_and_stop_go_through_the_control_of_the_runtime(org: Org) -> None:
    table = with_table(org)
    pid = sched_module.start_scheduler(org, 4, True)
    assert table.spawned[0].argv == ("/v/bin/orgmcp", "--root", str(org.root), "run", "--max-runs", "4", "--until-done")
    assert sched_module.scheduler_state(org).pid == pid
    with pytest.raises(OrgError, match="already running"):
        sched_module.start_scheduler(org)
    assert sched_module.stop_scheduler(org) == f"scheduler stopped (pid {pid})"
    assert sched_module.stop_scheduler(org) == "no scheduler is running for this org"


def test_a_scheduler_takes_and_gives_back_the_pidfile_through_the_lock_of_the_runtime(org: Org) -> None:
    lock = MemorySchedulerLock(FakeProcessTable())
    org.runtime = dataclasses.replace(org.runtime, scheduler_lock=lock)
    scheduler = Scheduler(org, echo=lambda _: None)
    scheduler.acquire()
    assert lock.text == "4000"  # the pid the lock's process table calls its own
    assert not (org.root / ".runtime" / "scheduler.pid").exists()
    scheduler.release()
    assert lock.text is None


def test_a_scheduler_refused_the_lock_does_not_forget_why_the_last_one_exited(org: Org) -> None:
    table = FakeProcessTable()
    table.add(9001, command="whatever")
    marker = MemoryExitMarker(FINISHED + "\n")
    org.runtime = dataclasses.replace(org.runtime, scheduler_lock=MemorySchedulerLock(table, "9001"), exit_marker=marker)
    with pytest.raises(OrgError, match=r"already running for this org \(pid 9001\)"):
        Scheduler(org, echo=lambda _: None).acquire()
    assert marker.text == FINISHED + "\n"


def test_a_scheduler_that_starts_forgets_why_the_last_one_exited(org: Org) -> None:
    marker = MemoryExitMarker("old reason\n")
    org.runtime = dataclasses.replace(org.runtime, scheduler_lock=MemorySchedulerLock(FakeProcessTable()), exit_marker=marker)
    scheduler = Scheduler(org, echo=lambda _: None)
    scheduler.acquire()
    assert marker.text is None
    scheduler.release()


def test_a_scheduler_that_finishes_leaves_the_reason_in_the_marker_of_the_runtime(org: Org) -> None:
    marker = MemoryExitMarker()
    org.runtime = dataclasses.replace(org.runtime, scheduler_lock=MemorySchedulerLock(FakeProcessTable()), exit_marker=marker)
    lines: list[str] = []
    Scheduler(org, echo=lines.append).serve(until_done=True)
    assert f"scheduler exiting: {FINISHED}" in lines and marker.text == FINISHED + "\n"
