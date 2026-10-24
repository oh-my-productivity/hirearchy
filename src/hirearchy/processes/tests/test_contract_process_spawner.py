"""Contract of ``ProcessSpawner``: real child processes and the fake table pass the same tests."""

from __future__ import annotations

import signal
from collections.abc import Iterator
from pathlib import Path

import pytest

from hirearchy.processes import ProcessSpawner
from hirearchy.processes.testing import IMPLEMENTATIONS, ProcessWorld

from ._support import env, eventually, make_world


@pytest.fixture(params=IMPLEMENTATIONS[ProcessSpawner], ids=lambda factory: factory.__name__)
def world(request: pytest.FixtureRequest, tmp_path: Path) -> Iterator[ProcessWorld]:
    yield from make_world(request, tmp_path)


def test_a_spawned_process_runs_and_has_a_pid(world: ProcessWorld) -> None:
    handle = world.spawner.spawn(["sleep", "60"], cwd=world.directory, env=env(), stdin=None, stdout=None)
    assert handle.pid > 1 and handle.poll() is None
    assert world.inspector.is_alive(handle.pid)


def test_a_spawned_process_leads_its_own_session_and_group(world: ProcessWorld) -> None:
    handle = world.spawner.spawn(["sleep", "60"], cwd=world.directory, env=env(), stdin=None, stdout=None)
    assert world.inspector.is_session_leader(handle.pid) is True  # pgid == sid == pid
    assert handle.pid != world.inspector.own_ids()[1]


def test_spawned_processes_are_distinct(world: ProcessWorld) -> None:
    first = world.spawner.spawn(["sleep", "60"], cwd=world.directory, env=env(), stdin=None, stdout=None)
    second = world.spawner.spawn(["sleep", "60"], cwd=world.directory, env=env(), stdin=None, stdout=None)
    assert first.pid != second.pid
    first.signal_group(signal.SIGKILL)
    assert first.wait(timeout=10) == -signal.SIGKILL
    assert second.poll() is None  # signalling one group leaves the other alone


def test_a_detached_process_is_no_child_of_this_process(world: ProcessWorld) -> None:
    log = world.directory / "scheduler.log"
    pid = world.spawner.spawn_detached(["sleep", "60"], cwd=world.directory, env=env(), log=log)
    assert pid > 1 and world.inspector.is_alive(pid)
    assert world.is_child(pid) is False  # it is re-parented: nothing of this process's tree reaches it


def test_a_detached_process_leads_its_own_session_and_group(world: ProcessWorld) -> None:
    log = world.directory / "scheduler.log"
    pid = world.spawner.spawn_detached(["sleep", "60"], cwd=world.directory, env=env(), log=log)
    assert world.inspector.is_session_leader(pid) is True
    assert pid != world.inspector.own_ids()[1]


def test_a_detached_process_appends_its_output_to_the_log(world: ProcessWorld) -> None:
    log = world.directory / "scheduler.log"
    log.write_text("# earlier\n", encoding="utf-8")
    world.start_echo("hello from the scheduler\n", log)
    assert eventually(lambda: log.read_text(encoding="utf-8") == "# earlier\nhello from the scheduler\n")  # there is no handle to wait for


def test_a_detached_process_creates_a_missing_log(world: ProcessWorld) -> None:
    log = world.directory / "new.log"
    world.start_echo("first line\n", log)
    assert eventually(lambda: log.is_file() and log.read_text(encoding="utf-8") == "first line\n")


def test_a_detached_process_that_prints_nothing_still_leaves_the_log(world: ProcessWorld) -> None:
    log = world.directory / "quiet.log"
    world.spawner.spawn_detached(["sleep", "60"], cwd=world.directory, env=env(), log=log)
    assert log.is_file()


def test_a_log_that_cannot_be_opened_is_an_os_error(world: ProcessWorld) -> None:
    log = world.directory / "no-such-directory" / "scheduler.log"
    with pytest.raises(OSError):
        world.spawner.spawn_detached(["sleep", "60"], cwd=world.directory, env=env(), log=log)
