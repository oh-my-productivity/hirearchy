"""Contract of ``SchedulerLock``: the pidfile keeps two schedulers off one organization.

Over a file and a scripted process table, over a file and the machine's processes (only processes the test started exist in it besides the test
run), and over the in-memory fake."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from hirearchy.daemon import SchedulerLock
from hirearchy.daemon.testing import IMPLEMENTATIONS, LockWorld
from hirearchy.kernel import OrgError

from ._support import build, worlds


@pytest.fixture(params=worlds(IMPLEMENTATIONS[SchedulerLock]))
def w(request: pytest.FixtureRequest, tmp_path: Path) -> Iterator[LockWorld]:
    world = build(request, tmp_path, LockWorld)
    assert isinstance(world.lock, SchedulerLock)
    yield world
    world.close()


def test_the_lock_writes_the_pid_of_the_process_that_takes_it(w: LockWorld) -> None:
    assert w.pidfile() is None
    w.lock.acquire()
    assert w.pidfile() == str(w.own_pid)


def test_a_pidfile_of_a_live_process_refuses_the_lock_and_is_left_alone(w: LockWorld) -> None:
    pid = w.live_pid()
    w.put(str(pid))
    with pytest.raises(OrgError, match=rf"^a scheduler is already running for this org \(pid {pid}\)$"):
        w.lock.acquire()
    assert w.pidfile() == str(pid)


def test_a_pidfile_of_a_process_that_is_gone_is_replaced(w: LockWorld) -> None:
    w.put(str(w.gone_pid()))
    w.lock.acquire()
    assert w.pidfile() == str(w.own_pid)


@pytest.mark.parametrize("text", ["not a pid", "", "\n", "-5", "0"])
def test_a_pidfile_that_names_no_process_is_replaced(w: LockWorld, text: str) -> None:
    w.put(text)
    w.lock.acquire()
    assert w.pidfile() == str(w.own_pid)


def test_a_process_that_holds_the_lock_cannot_take_it_twice(w: LockWorld) -> None:
    w.lock.acquire()
    with pytest.raises(OrgError, match=rf"already running for this org \(pid {w.own_pid}\)"):
        w.lock.acquire()


def test_release_removes_the_pidfile(w: LockWorld) -> None:
    w.lock.acquire()
    w.lock.release()
    assert w.pidfile() is None


def test_release_without_a_pidfile_is_harmless(w: LockWorld) -> None:
    w.lock.release()
    w.lock.acquire()
    w.lock.release()
    w.lock.release()
    assert w.pidfile() is None


def test_after_a_release_the_lock_can_be_taken_again(w: LockWorld) -> None:
    w.lock.acquire()
    w.lock.release()
    w.lock.acquire()
    assert w.pidfile() == str(w.own_pid)
