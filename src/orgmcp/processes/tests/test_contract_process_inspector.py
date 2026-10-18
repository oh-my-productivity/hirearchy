"""Contract of ``ProcessInspector``: ``ps`` and the signals of the real table, and the fake table, pass the same tests."""

from __future__ import annotations

import signal
from collections.abc import Iterator
from pathlib import Path

import pytest

from orgmcp.processes import ProcessInfo, ProcessInspector, ProcessTableError
from orgmcp.processes.testing import IMPLEMENTATIONS, ProcessWorld

from ._support import implementations, eventually, make_world


@pytest.fixture(params=implementations(ProcessInspector, IMPLEMENTATIONS[ProcessInspector]))
def world(request: pytest.FixtureRequest, tmp_path: Path) -> Iterator[ProcessWorld]:
    yield from make_world(request, tmp_path)


def test_info_of_a_running_child_is_its_state_and_start_time(world: ProcessWorld) -> None:
    child = world.start_leader()
    info = world.inspector.info(child.pid)
    assert isinstance(info, ProcessInfo)
    assert info.state and not info.state.startswith("Z")
    assert info.started and info.started == info.started.strip() and "  " not in info.started


def test_info_of_a_process_that_does_not_exist_is_none(world: ProcessWorld) -> None:
    assert world.inspector.info(world.gone_pid()) is None


def test_info_of_a_zombie_says_so(world: ProcessWorld) -> None:
    zombie = world.start_zombie()
    info = world.inspector.info(zombie)
    assert info is not None and info.state.startswith("Z")


def test_info_when_ps_cannot_run_raises_a_process_table_error(world: ProcessWorld) -> None:
    child = world.start_leader()
    with pytest.raises(ProcessTableError):
        world.blind_inspector.info(child.pid)


def test_the_start_time_is_the_one_info_reports_and_does_not_change(world: ProcessWorld) -> None:
    child = world.start_leader()
    info = world.inspector.info(child.pid)
    assert info is not None
    assert world.inspector.start_time(child.pid) == info.started == world.inspector.start_time(child.pid)


def test_the_start_time_of_a_missing_process_or_without_ps_is_none(world: ProcessWorld) -> None:
    child = world.start_leader()
    assert world.inspector.start_time(world.gone_pid()) is None
    assert world.blind_inspector.start_time(child.pid) is None


def test_the_command_line_of_a_child_names_its_program(world: ProcessWorld) -> None:
    child = world.start_leader()
    command = world.inspector.command_line(child.pid)
    assert command is not None and "sleep" in command and command == command.strip()


def test_the_command_line_of_a_missing_process_or_without_ps_is_none(world: ProcessWorld) -> None:
    child = world.start_leader()
    assert world.inspector.command_line(world.gone_pid()) is None
    assert world.blind_inspector.command_line(child.pid) is None


def test_a_spawned_child_leads_its_session_and_a_bystander_does_not(world: ProcessWorld) -> None:
    child = world.start_leader()
    bystander = world.start_bystander()
    assert world.inspector.is_session_leader(child.pid) is True
    assert world.inspector.is_session_leader(bystander) is False


def test_whether_a_missing_process_leads_a_session_cannot_be_decided(world: ProcessWorld) -> None:
    assert world.inspector.is_session_leader(world.gone_pid()) is None


def test_a_running_process_is_alive_and_a_missing_one_is_not(world: ProcessWorld) -> None:
    child = world.start_leader()
    assert world.inspector.is_alive(child.pid) is True
    assert world.inspector.is_alive(world.gone_pid()) is False


def test_a_zombie_is_alive_until_its_parent_reaps_it(world: ProcessWorld) -> None:
    zombie = world.start_zombie()
    assert world.inspector.is_alive(zombie) is True


def test_a_killed_and_reaped_child_is_not_alive(world: ProcessWorld) -> None:
    child = world.start_leader()
    child.signal_group(signal.SIGKILL)
    assert child.wait(timeout=10) == -signal.SIGKILL
    assert eventually(lambda: not world.inspector.is_alive(child.pid))


def test_own_ids_are_positive_and_the_process_is_alive(world: ProcessWorld) -> None:
    pid, pgid = world.inspector.own_ids()
    assert pid > 1 and pgid > 1
    assert world.inspector.is_alive(pid)
    assert world.inspector.info(pid) is not None
