"""``PidFileStartupWatch``: a scheduler that was just started has ten seconds to write its pid; one that ends at once is an error."""

from __future__ import annotations

from pathlib import Path

import pytest

from orgmcp.daemon._watch import PidFileStartupWatch
from orgmcp.daemon.testing import MemoryExitMarker
from orgmcp.kernel import OrgError, OrgPaths
from orgmcp.kernel.testing import FakeClock
from orgmcp.processes import ProcessHandle
from orgmcp.processes.testing import FakeProcessTable


class WritesPidAt(FakeClock):
    """A clock that, when it has moved on ``after`` seconds, lets the scheduler write ``text`` to the pidfile."""

    def __init__(self, pidfile: Path, text: str, after: float) -> None:
        super().__init__()
        self._pidfile, self._text, self._after = pidfile, text, after

    def sleep(self, seconds: float) -> None:
        super().sleep(seconds)
        if self.monotonic() >= self._after:
            self._pidfile.write_text(self._text)


class Rig:
    def __init__(self, tmp_path: Path, clock: FakeClock | None = None) -> None:
        self.root = tmp_path / "org"
        (self.root / ".runtime").mkdir(parents=True)
        self.pidfile = self.root / ".runtime" / "scheduler.pid"
        self.log = self.root / ".runtime" / "scheduler.log"
        self.clock = clock or FakeClock()
        self.table = FakeProcessTable(self.clock)
        self.marker = MemoryExitMarker()
        self.watch = PidFileStartupWatch(OrgPaths(self.root), self.marker, self.clock)

    def start(self) -> ProcessHandle:
        self.log.write_text("# --- scheduler started\n")
        return self.table.spawn_detached(["orgmcp", "run"], cwd=self.root, env={}, log=self.log)

    def waited(self) -> float:
        return round(self.clock.monotonic(), 3)


def test_a_scheduler_that_has_written_its_pid_is_up_at_once(tmp_path: Path) -> None:
    rig = Rig(tmp_path)
    handle = rig.start()
    rig.pidfile.write_text(str(handle.pid))
    rig.watch.await_start(handle, rig.log)
    assert rig.waited() == 0


def test_a_scheduler_that_writes_its_pid_a_moment_later_is_waited_for(tmp_path: Path) -> None:
    clock = WritesPidAt(tmp_path / "org" / ".runtime" / "scheduler.pid", "", 0.3)
    rig = Rig(tmp_path, clock)
    handle = rig.start()
    clock._text = str(handle.pid)
    rig.watch.await_start(handle, rig.log)
    assert 0.3 <= rig.waited() < 0.5  # it looks every 0.05 seconds


def test_a_pidfile_of_another_process_is_not_the_scheduler_coming_up(tmp_path: Path) -> None:
    rig = Rig(tmp_path)
    handle = rig.start()
    rig.pidfile.write_text("99999")  # the stale pidfile of an earlier scheduler
    rig.watch.await_start(handle, rig.log)
    assert rig.waited() >= 10  # waited all the time it had, then gave up quietly: the caller returns the pid anyway


def test_a_garbled_pidfile_is_waited_through_too(tmp_path: Path) -> None:
    rig = Rig(tmp_path)
    handle = rig.start()
    rig.pidfile.write_text("garbage")
    rig.watch.await_start(handle, rig.log)
    assert rig.waited() >= 10


def test_a_scheduler_that_never_writes_its_pid_is_given_ten_seconds(tmp_path: Path) -> None:
    rig = Rig(tmp_path)
    handle = rig.start()
    rig.watch.await_start(handle, rig.log)
    assert 10 <= rig.waited() < 10.1


def test_a_scheduler_that_ends_at_once_is_an_error_with_the_end_of_its_log(tmp_path: Path) -> None:
    rig = Rig(tmp_path)
    rig.table.will_exit(3, output="one\ntwo\nthree\nfour\nfive\nboom\n")
    handle = rig.start()
    with pytest.raises(OrgError) as raised:
        rig.watch.await_start(handle, rig.log)
    assert str(raised.value) == f"the scheduler exited at once (exit 3); {rig.log} ends with:\ntwo\nthree\nfour\nfive\nboom"


def test_a_short_log_is_shown_whole(tmp_path: Path) -> None:
    rig = Rig(tmp_path)
    rig.table.will_exit(1, output="boom\n")
    handle = rig.start()
    with pytest.raises(OrgError, match=r"exited at once \(exit 1\); .*scheduler\.log ends with:\n# --- scheduler started\nboom$"):
        rig.watch.await_start(handle, rig.log)


def test_a_scheduler_that_exits_zero_leaving_a_reason_had_nothing_left_to_do(tmp_path: Path) -> None:
    rig = Rig(tmp_path)
    rig.table.will_exit(0)
    handle = rig.start()
    rig.marker.write("finished: no open tasks")
    rig.watch.await_start(handle, rig.log)  # no error
    assert rig.waited() == 0


def test_a_scheduler_that_exits_zero_without_a_reason_is_an_error(tmp_path: Path) -> None:
    rig = Rig(tmp_path)
    rig.table.will_exit(0)
    handle = rig.start()
    with pytest.raises(OrgError, match=r"exited at once \(exit 0\)"):
        rig.watch.await_start(handle, rig.log)


def test_a_scheduler_that_ends_after_a_while_is_an_error_at_that_moment(tmp_path: Path) -> None:
    rig = Rig(tmp_path)
    rig.table.will_exit(2, after=1.0)
    handle = rig.start()
    with pytest.raises(OrgError, match=r"exited at once \(exit 2\)"):
        rig.watch.await_start(handle, rig.log)
    assert 1.0 <= rig.waited() < 1.1
