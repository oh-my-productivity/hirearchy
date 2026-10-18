"""Contract of ``ProcessSignaller``: real signals and the fake table pass the same tests.

Only processes the test started are ever signalled. The refusals (pgid <= 1, our own pid and group) cannot be shown with the real
signals without risking the test run itself: ``test_os_process_signaller.py`` shows them with the system calls replaced.
"""

from __future__ import annotations

import signal
from collections.abc import Iterator
from pathlib import Path

import pytest

from orgmcp.processes import ProcessGone, ProcessSignaller
from orgmcp.processes.testing import IMPLEMENTATIONS, ProcessWorld

from ._support import eventually, make_world


@pytest.fixture(params=IMPLEMENTATIONS[ProcessSignaller], ids=lambda factory: factory.__name__)
def world(request: pytest.FixtureRequest, tmp_path: Path) -> Iterator[ProcessWorld]:
    yield from make_world(request, tmp_path)


def test_kill_group_kills_the_leader_and_reports_it_gone(world: ProcessWorld) -> None:
    leader = world.start_leader()
    assert world.signaller.kill_group(leader.pid) is True
    assert leader.wait(timeout=10) == -signal.SIGKILL


def test_kill_group_kills_the_grandchildren_too(world: ProcessWorld) -> None:
    leader, grandchild = world.start_group()
    assert world.inspector.is_alive(grandchild)
    assert world.signaller.kill_group(leader.pid) is True
    assert eventually(lambda: not world.inspector.is_alive(grandchild))
    assert leader.wait(timeout=10) == -signal.SIGKILL


def test_kill_group_kills_a_process_that_ignores_sigterm(world: ProcessWorld) -> None:
    leader = world.start_term_proof()
    assert world.signaller.kill_group(leader.pid) is True
    assert leader.wait(timeout=10) == -signal.SIGKILL


def test_kill_group_of_a_group_that_does_not_exist_is_true(world: ProcessWorld) -> None:
    assert world.signaller.kill_group(world.gone_pid()) is True


def test_kill_group_counts_a_leader_that_is_a_zombie_as_gone(world: ProcessWorld) -> None:
    leader = world.start_leader()
    assert world.signaller.kill_group(leader.pid, wait=5.0) is True
    info = world.inspector.info(leader.pid)  # killed, not yet reaped by us
    assert info is None or info.state.startswith("Z")


def test_terminate_sends_sigterm_to_the_process(world: ProcessWorld) -> None:
    child = world.start_leader()
    world.signaller.terminate(child.pid)
    assert child.wait(timeout=10) == -signal.SIGTERM


def test_terminate_leaves_the_rest_of_the_group_alone(world: ProcessWorld) -> None:
    leader, grandchild = world.start_group()
    world.signaller.terminate(leader.pid)
    assert leader.wait(timeout=10) == -signal.SIGTERM
    assert world.inspector.is_alive(grandchild)
    leader.signal_group(signal.SIGKILL)
    assert eventually(lambda: not world.inspector.is_alive(grandchild))


def test_terminate_of_a_process_that_does_not_exist_raises_process_gone(world: ProcessWorld) -> None:
    with pytest.raises(ProcessGone):
        world.signaller.terminate(world.gone_pid())
