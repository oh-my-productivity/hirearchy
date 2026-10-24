"""``DetachedLauncher``: refuse what must be refused, then prepare the site, start the scheduler detached (no child of ours) and wait for it."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

import pytest

from hirearchy.daemon import SchedulerState
from hirearchy.daemon._launch import DetachedLauncher
from hirearchy.daemon._ports import LaunchEnvironment, LaunchSite, StartupWatch
from hirearchy.daemon.testing import FakeSchedulerCommand, FakeSchedulerStatus
from hirearchy.kernel import OrgError, OrgPaths
from hirearchy.processes import ProcessHandle, ProcessSpawner
from hirearchy.processes.testing import FakeProcessTable


class Calls:
    """What the launcher did, in order."""

    def __init__(self) -> None:
        self.events: list[str] = []


class SpySite(LaunchSite):
    def __init__(self, calls: Calls, log: Path) -> None:
        self._calls, self._log = calls, log

    def directory(self) -> Path:
        return self._log.parent.parent

    def prepare(self) -> Path:
        self._calls.events.append("prepare")
        self._log.parent.mkdir(exist_ok=True)
        return self._log

    def announce(self, log: Path, argv: Sequence[str]) -> None:
        self._calls.events.append("announce " + " ".join(argv))


class SpyEnvironment(LaunchEnvironment):
    def variables(self) -> dict[str, str]:
        return {"ORG_ROOT": "/org", "PYTHONUNBUFFERED": "1"}


class SpyWatch(StartupWatch):
    def __init__(self, calls: Calls) -> None:
        self._calls = calls
        self.watched: list[tuple[int, Path]] = []
        self.reads: int | None = None  # the pid the scheduler says is its own, when it is not the one that was started

    def await_start(self, pid: int, log: Path) -> int:
        self._calls.events.append("watch")
        self.watched.append((pid, log))
        return pid if self.reads is None else self.reads


class SpySpawner(ProcessSpawner):
    def __init__(self, calls: Calls, table: FakeProcessTable) -> None:
        self._calls, self._table = calls, table
        self.given: list[tuple[list[str], Path, dict[str, str], Path]] = []

    def spawn(
        self, argv: Sequence[str], *, cwd: Path, env: Mapping[str, str], stdin: object | None, stdout: object | None
    ) -> ProcessHandle:
        raise AssertionError("a scheduler is started detached")

    def spawn_detached(self, argv: Sequence[str], *, cwd: Path, env: Mapping[str, str], log: Path) -> int:
        self._calls.events.append("spawn")
        self.given.append((list(argv), cwd, dict(env), log))
        return self._table.spawn_detached(argv, cwd=cwd, env=env, log=log)


class Rig:
    def __init__(self, tmp_path: Path, state: SchedulerState = SchedulerState("stopped")) -> None:
        self.root = tmp_path / "org"
        self.root.mkdir()
        self.calls = Calls()
        self.table = FakeProcessTable()
        self.status = FakeSchedulerStatus(state)
        self.command = FakeSchedulerCommand(OrgPaths(self.root), ["/v/bin/hirearchy"])
        self.spawner = SpySpawner(self.calls, self.table)
        self.watch = SpyWatch(self.calls)
        self.log = self.root / ".runtime" / "scheduler.log"
        self.launcher = DetachedLauncher(
            self.status, SpySite(self.calls, self.log), SpyEnvironment(), self.command, self.spawner, self.watch,
        )


def test_it_starts_the_command_of_the_caps_in_the_environment_of_the_organization(tmp_path: Path) -> None:
    rig = Rig(tmp_path)
    pid = rig.launcher.start(3, True)
    (argv, cwd, env, log) = rig.spawner.given[0]
    assert argv == ["/v/bin/hirearchy", "--root", str(rig.root), "run", "--max-runs", "3", "--until-done"]
    assert cwd == rig.root and env == {"ORG_ROOT": "/org", "PYTHONUNBUFFERED": "1"} and log == rig.log
    assert rig.command.calls == [(3, True)] and pid == rig.table.spawned[0].pid


def test_it_prepares_announces_starts_and_then_waits_in_that_order(tmp_path: Path) -> None:
    rig = Rig(tmp_path)
    rig.launcher.start(None, False)
    assert rig.calls.events == ["prepare", f"announce /v/bin/hirearchy --root {rig.root} run", "spawn", "watch"]


def test_it_waits_for_the_process_it_started_with_the_log(tmp_path: Path) -> None:
    rig = Rig(tmp_path)
    pid = rig.launcher.start(None, False)
    assert rig.watch.watched == [(pid, rig.log)]


def test_it_returns_the_pid_the_watch_read_from_the_pidfile(tmp_path: Path) -> None:
    rig = Rig(tmp_path)
    rig.watch.reads = 31337
    assert rig.launcher.start(None, False) == 31337


def test_it_adopts_nothing_the_scheduler_it_started_is_no_child_of_ours(tmp_path: Path) -> None:
    rig = Rig(tmp_path)
    pid = rig.launcher.start(None, False)
    rig.table.exit(pid, 0)
    assert rig.table.info(pid) is None  # nobody has to reap it: it was never ours


def test_a_negative_cap_is_refused_before_anything_is_looked_at(tmp_path: Path) -> None:
    rig = Rig(tmp_path)
    with pytest.raises(OrgError, match="^max_runs must be 0 or more$"):
        rig.launcher.start(-1, False)
    assert rig.status.asked == 0 and rig.calls.events == []


def test_a_running_scheduler_is_not_started_twice(tmp_path: Path) -> None:
    rig = Rig(tmp_path, SchedulerState("running", 4242, "2026-10-18 10:00:00Z"))
    with pytest.raises(OrgError, match=r"^a scheduler is already running for this org \(pid 4242, since 2026-10-18 10:00:00Z\); call stop\(\) first to restart it$"):
        rig.launcher.start(None, False)
    assert rig.calls.events == []


def test_a_live_process_that_cannot_be_verified_blocks_the_start(tmp_path: Path) -> None:
    rig = Rig(tmp_path, SchedulerState("unverified", 4242, "x", "its command line is 'vim'"))
    with pytest.raises(OrgError) as raised:
        rig.launcher.start(None, False)
    assert str(raised.value) == (
        "not starting: .runtime/scheduler.pid names pid 4242, which is alive but not verified to be this org's scheduler "
        "(its command line is 'vim'). Check that process; if it is stale, remove that file"
    )
    assert rig.calls.events == []


def test_a_cap_of_zero_is_a_cap(tmp_path: Path) -> None:
    rig = Rig(tmp_path)
    rig.launcher.start(0, False)
    assert rig.spawner.given[0][0][-2:] == ["--max-runs", "0"]


def test_the_error_of_a_scheduler_that_cannot_be_watched_up_reaches_the_caller_after_the_start(tmp_path: Path) -> None:
    rig = Rig(tmp_path)

    class Dies(StartupWatch):
        def await_start(self, pid: int, log: Path) -> int:
            raise OrgError("the scheduler exited at once")

    rig.launcher = DetachedLauncher(rig.status, SpySite(rig.calls, rig.log), SpyEnvironment(), rig.command, rig.spawner, Dies())
    with pytest.raises(OrgError, match="exited at once"):
        rig.launcher.start(None, False)
    assert "spawn" in rig.calls.events
