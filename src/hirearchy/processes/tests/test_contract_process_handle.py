"""Contract of ``ProcessHandle``: a real child process and the fake one pass the same tests."""

from __future__ import annotations

import signal
import subprocess
from collections.abc import Iterator
from pathlib import Path

import pytest

from hirearchy.processes import ProcessHandle
from hirearchy.processes.testing import IMPLEMENTATIONS, ProcessWorld

from ._support import eventually, make_world


@pytest.fixture(params=IMPLEMENTATIONS[ProcessHandle], ids=lambda factory: factory.__name__)
def world(request: pytest.FixtureRequest, tmp_path: Path) -> Iterator[ProcessWorld]:
    yield from make_world(request, tmp_path)


def test_a_running_process_has_a_pid_and_no_exit_code(world: ProcessWorld) -> None:
    handle = world.start_leader()
    assert isinstance(handle, ProcessHandle)
    assert handle.pid > 1
    assert handle.poll() is None and handle.returncode is None


def test_wait_returns_the_exit_code_and_poll_and_returncode_agree(world: ProcessWorld) -> None:
    handle = world.start_exiting(3)
    assert handle.wait(timeout=10) == 3
    assert handle.poll() == 3 and handle.returncode == 3


def test_poll_sees_the_exit_of_a_process_that_ended(world: ProcessWorld) -> None:
    handle = world.start_exiting(0)
    assert eventually(lambda: handle.poll() is not None)
    assert handle.returncode == 0


def test_waiting_with_a_timeout_raises_while_the_process_runs(world: ProcessWorld) -> None:
    handle = world.start_leader()
    with pytest.raises(subprocess.TimeoutExpired):
        handle.wait(timeout=0.05)
    assert handle.poll() is None


def test_sigterm_to_the_group_ends_the_process(world: ProcessWorld) -> None:
    handle = world.start_leader()
    handle.signal_group(signal.SIGTERM)
    assert handle.wait(timeout=10) == -signal.SIGTERM


def test_sigkill_to_the_group_takes_the_grandchild_along(world: ProcessWorld) -> None:
    handle, grandchild = world.start_group()
    assert world.inspector.is_alive(grandchild)
    handle.signal_group(signal.SIGKILL)
    assert handle.wait(timeout=10) == -signal.SIGKILL
    assert eventually(lambda: not world.inspector.is_alive(grandchild))


def test_a_process_that_ignores_sigterm_survives_it_and_not_sigkill(world: ProcessWorld) -> None:
    handle = world.start_term_proof()
    handle.signal_group(signal.SIGTERM)
    with pytest.raises(subprocess.TimeoutExpired):
        handle.wait(timeout=0.3)
    handle.signal_group(signal.SIGKILL)
    assert handle.wait(timeout=10) == -signal.SIGKILL


def test_the_group_can_still_be_signalled_after_its_leader_was_reaped(world: ProcessWorld) -> None:
    handle, grandchild = world.start_group()
    world.signaller.terminate(handle.pid)  # the leader only: the grandchild stays in the group
    assert handle.wait(timeout=10) == -signal.SIGTERM
    assert world.inspector.is_alive(grandchild)
    handle.signal_group(signal.SIGKILL)  # what the scheduler does to reap tool subprocesses that outlive the run
    assert eventually(lambda: not world.inspector.is_alive(grandchild))


def test_signalling_a_process_that_is_gone_does_not_raise(world: ProcessWorld) -> None:
    handle = world.start_exiting(0)
    handle.wait(timeout=10)
    handle.signal_group(signal.SIGTERM)
    handle.signal_group(signal.SIGKILL)
    assert handle.returncode == 0


def test_signal_zero_checks_without_ending_the_process(world: ProcessWorld) -> None:
    handle = world.start_leader()
    handle.signal_group(0)
    assert handle.poll() is None

