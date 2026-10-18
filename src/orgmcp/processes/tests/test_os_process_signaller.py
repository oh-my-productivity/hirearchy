"""``OsProcessSignaller``: which system calls it makes, what it refuses, and how it waits (system calls replaced, nothing is signalled)."""

from __future__ import annotations

import os
import signal
from dataclasses import dataclass

import pytest

from orgmcp.kernel.testing import FakeClock
from orgmcp.processes import ProcessDenied, ProcessGone, ProcessSignaller
from orgmcp.processes._signal import OsProcessSignaller
from orgmcp.processes.testing import FakeProcessTable

pytestmark = pytest.mark.xfail(strict=True, reason="red: A-processes")

OWN_PID, OWN_PGID = 4000, 3990
LEADER = 5000


@dataclass
class Calls:
    killpg: list[tuple[int, int]]
    kill: list[tuple[int, int]]


@pytest.fixture
def calls(monkeypatch: pytest.MonkeyPatch) -> Calls:
    """Every signal call of the process is recorded and none is made: a refusal that fails would otherwise kill the test run."""
    seen = Calls([], [])
    monkeypatch.setattr(os, "killpg", lambda pgid, sig: seen.killpg.append((pgid, sig)))
    monkeypatch.setattr(os, "kill", lambda pid, sig: seen.kill.append((pid, sig)))
    return seen


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def table(clock: FakeClock) -> FakeProcessTable:
    return FakeProcessTable(clock, own_pid=OWN_PID, own_pgid=OWN_PGID)


@pytest.fixture
def signaller(table: FakeProcessTable, clock: FakeClock) -> OsProcessSignaller:
    return OsProcessSignaller(table, clock)


def test_it_is_a_process_signaller(signaller: OsProcessSignaller) -> None:
    assert isinstance(signaller, ProcessSignaller)


@pytest.mark.parametrize("pgid", [0, 1, -1, -LEADER, OWN_PID, OWN_PGID])
def test_a_group_that_is_not_a_run_is_never_signalled(signaller: OsProcessSignaller, calls: Calls, pgid: int) -> None:
    assert signaller.kill_group(pgid) is False
    assert calls.killpg == [] and calls.kill == []


@pytest.mark.parametrize("pid", [0, 1, -1, -LEADER, OWN_PID, OWN_PGID])
def test_a_process_that_is_not_ours_to_terminate_is_never_signalled(signaller: OsProcessSignaller, calls: Calls, pid: int) -> None:
    with pytest.raises(ProcessDenied):
        signaller.terminate(pid)
    assert calls.killpg == [] and calls.kill == []


def test_kill_group_sends_sigkill_to_the_group(signaller: OsProcessSignaller, table: FakeProcessTable, calls: Calls) -> None:
    table.add(LEADER, state="Z")
    assert signaller.kill_group(LEADER) is True
    assert calls.killpg == [(LEADER, signal.SIGKILL)] and calls.kill == []


def test_a_group_that_does_not_exist_is_gone_without_waiting(
    signaller: OsProcessSignaller, clock: FakeClock, monkeypatch: pytest.MonkeyPatch
) -> None:
    def no_such_group(pgid: int, sig: int) -> None:
        raise ProcessLookupError()

    monkeypatch.setattr(os, "killpg", no_such_group)
    start = clock.time()
    assert signaller.kill_group(LEADER) is True
    assert clock.time() - start < 0.01


def test_a_group_that_may_not_be_signalled_is_not_killed(
    signaller: OsProcessSignaller, table: FakeProcessTable, monkeypatch: pytest.MonkeyPatch
) -> None:
    def not_ours(pgid: int, sig: int) -> None:
        raise PermissionError()

    table.add(LEADER)
    monkeypatch.setattr(os, "killpg", not_ours)
    assert signaller.kill_group(LEADER) is False


def test_it_waits_for_the_leader_to_go_and_gives_up_after_the_time_it_was_given(
    signaller: OsProcessSignaller, table: FakeProcessTable, clock: FakeClock, calls: Calls
) -> None:
    table.add(LEADER)  # the signal call does nothing here, so the leader stays
    start = clock.time()
    assert signaller.kill_group(LEADER, wait=0.5) is False
    assert 0.5 <= clock.time() - start < 1.0
    assert calls.killpg == [(LEADER, signal.SIGKILL)]


def test_a_leader_that_goes_while_it_waits_is_reported_gone(
    signaller: OsProcessSignaller, table: FakeProcessTable, clock: FakeClock, calls: Calls
) -> None:
    table.add(LEADER)
    table.exit_after(LEADER, 0.2)  # gone 0.2 s into the wait
    start = clock.time()
    assert signaller.kill_group(LEADER, wait=5.0) is True
    assert 0.2 <= clock.time() - start < 1.0


def test_a_zombie_leader_counts_as_gone(signaller: OsProcessSignaller, table: FakeProcessTable, calls: Calls) -> None:
    table.add(LEADER, state="Z")
    assert signaller.kill_group(LEADER) is True


def test_when_ps_fails_during_the_wait_the_group_is_not_reported_gone(
    signaller: OsProcessSignaller, table: FakeProcessTable, calls: Calls
) -> None:
    table.add(LEADER)
    table.ps_works = False
    assert signaller.kill_group(LEADER) is False


def test_terminate_sends_sigterm_to_the_one_process(signaller: OsProcessSignaller, calls: Calls) -> None:
    signaller.terminate(LEADER)
    assert calls.kill == [(LEADER, signal.SIGTERM)] and calls.killpg == []


def test_terminate_of_a_process_that_is_gone_raises_process_gone(signaller: OsProcessSignaller, monkeypatch: pytest.MonkeyPatch) -> None:
    def gone(pid: int, sig: int) -> None:
        raise ProcessLookupError()

    monkeypatch.setattr(os, "kill", gone)
    with pytest.raises(ProcessGone):
        signaller.terminate(LEADER)


def test_terminate_of_a_process_that_is_not_ours_raises_process_denied(signaller: OsProcessSignaller, monkeypatch: pytest.MonkeyPatch) -> None:
    def denied(pid: int, sig: int) -> None:
        raise PermissionError()

    monkeypatch.setattr(os, "kill", denied)
    with pytest.raises(ProcessDenied):
        signaller.terminate(LEADER)
