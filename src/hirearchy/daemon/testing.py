"""The ``daemon`` ports over an organization directory and a process table, the fakes a consumer's test uses, and the registry the contract suites iterate over.

Every world is built twice (three times where real processes are cheap to start): the real classes over the files of a temporary directory and a
``FakeProcessTable`` (``pidfile_*``), the same over real processes (``real_*``: only processes the world started are ever signalled, and ``close`` kills
those and nothing else), and the in-memory fake (``memory_*``). All of them pass the same contract suite.

``FakeSchedulerStatus``, ``FakeSchedulerControl``, ``FakeSchedulerCommand``/``FixedSchedulerCommand`` and ``MemoryExitMarker`` are what the tests of ``progress``,
``observability``, ``dashdata``, ``mcp_server``, ``cli`` and ``scheduler`` use instead of a process: each answers as the real one does for the state it is
given, and keeps a record of what it was asked.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from ..attention import Waiting, WaitingOnUser
from ..attention.testing import FixedWaiting
from ..kernel import ROOT, Clock, Message, OrgError, OrgLayout, OrgPaths
from ..kernel.testing import FakeClock, fs_atomic_writer, os_environment, system_clock
from ..mail import TaskQuery
from ..processes import ProcessHandle, ProcessInspector, ProcessSignaller, ProcessSpawner
from ..processes.testing import FakeProcessTable, real_world
from ..snapshots.testing import MemoryIgnoreList
from ._children import ChildRegistry
from ._command import VenvSchedulerCommand
from ._control import DetachedSchedulerControl
from ._describe import describe_state
from ._files import exit_file_of, pidfile_of
from ._identity import SchedulerIdentity
from ._launch import DetachedLauncher
from ._lock import PidFileSchedulerLock
from ._marker import FileExitMarker
from ._refusals import NO_SCHEDULER, SINCE_FORMAT, check_startable, check_stoppable
from ._site import RuntimeLaunchSite, ScrubbedLaunchEnvironment
from ._status import PidFileSchedulerStatus
from ._stop import SignalSchedulerStopper
from ._watch import PidFileStartupWatch
from .api import REFUSED_START, ExitMarker, SchedulerCommand, SchedulerControl, SchedulerLock, SchedulerState, SchedulerStatus

LIVE = ("sh", "-c", "sleep 60; :")  # a process that lives until it is signalled; the semicolon keeps the shell from replacing itself with ``sleep``
LIVE_TEXT = " ".join(LIVE)  # how the process table shows it, before the words that follow
AT = datetime(2026, 10, 18, 10, 0, 0, tzinfo=timezone.utc)  # when the pidfile of a world was written
SINCE = "2026-10-18 10:00:00Z"  # ``SchedulerState.since`` for ``AT``

# ------------------------------------------------------------------------------ the fakes


class FakeSchedulerStatus(SchedulerStatus):
    """The state is ``current``; ``reason`` is what the exit marker holds and ``open_tasks`` says whether root still waits for a result (the marker is
    only believed while it does not); ``waiting`` is asked when nothing else explains a stopped scheduler."""

    def __init__(
        self, current: SchedulerState = SchedulerState("stopped"), *, reason: str = "", open_tasks: bool = False, waiting: WaitingOnUser | None = None
    ) -> None:
        self.current = current
        self.reason = reason
        self.open_tasks = open_tasks
        self.waiting: WaitingOnUser = waiting or FixedWaiting()
        self.asked = 0  # how often ``state`` was asked

    def state(self) -> SchedulerState:
        self.asked += 1
        return self.current

    def describe(self) -> str:
        return describe_state(self.current, self.exit_reason, self.waiting)

    def exit_reason(self) -> str:
        return self.reason if self.reason and (self.reason.startswith(REFUSED_START) or not self.open_tasks) else ""


class FakeSchedulerControl(SchedulerControl):
    """Starts and stops the scheduler of ``status``, with the refusals of the real control, and keeps what it was asked in ``starts`` and ``stops``."""

    def __init__(self, status: FakeSchedulerStatus | None = None, *, pid: int = 4242, clock: Clock | None = None) -> None:
        self.status = status or FakeSchedulerStatus()
        self.next_pid = pid
        self.clock: Clock = clock or FakeClock()
        self.starts: list[tuple[int | None, bool]] = []
        self.stops: list[float] = []
        self.signalled: list[int] = []

    def start(self, max_runs: int | None = None, until_done: bool = False) -> int:
        if max_runs is not None and max_runs < 0:
            raise OrgError("max_runs must be 0 or more")
        check_startable(self.status.state())
        self.starts.append((max_runs, until_done))
        pid, self.next_pid = self.next_pid, self.next_pid + 1
        self.status.current = SchedulerState("running", pid, self.clock.now().strftime(SINCE_FORMAT))
        return pid

    def stop(self, wait: float = 15.0) -> str:
        self.stops.append(wait)
        state = self.status.state()
        if state.state == "stopped":
            return NO_SCHEDULER
        check_stoppable(state)
        assert state.pid is not None
        self.signalled.append(state.pid)
        self.status.current = SchedulerState("stopped")
        return f"scheduler stopped (pid {state.pid})"


class FixedSchedulerCommand(SchedulerCommand):
    """``argv`` is exactly ``fixed``, whatever it is asked (a scheduler that dies at once, or a stand-in program)."""

    def __init__(self, fixed: Sequence[str]) -> None:
        self.fixed = list(fixed)
        self.calls: list[tuple[int | None, bool]] = []

    def argv(self, max_runs: int | None, until_done: bool) -> list[str]:
        self.calls.append((max_runs, until_done))
        return list(self.fixed)


class FakeSchedulerCommand(SchedulerCommand):
    """The command line of the real one with another program: ``<program> --root <org> run [--max-runs N] [--until-done]``."""

    def __init__(self, layout: OrgLayout, program: Sequence[str] = ("/venv/bin/hirearchy",)) -> None:
        self._layout = layout
        self.program = list(program)
        self.calls: list[tuple[int | None, bool]] = []

    def argv(self, max_runs: int | None, until_done: bool) -> list[str]:
        self.calls.append((max_runs, until_done))
        return [
            *self.program, "--root", str(self._layout.root), "run",
            *(["--max-runs", str(max_runs)] if max_runs is not None else []), *(["--until-done"] if until_done else []),
        ]


class RecordingSchedulerCommand(SchedulerCommand):
    """Asks ``inner`` and keeps the question in ``calls`` and the answer in ``issued``."""

    def __init__(self, inner: SchedulerCommand) -> None:
        self._inner = inner
        self.calls: list[tuple[int | None, bool]] = []
        self.issued: list[list[str]] = []

    def argv(self, max_runs: int | None, until_done: bool) -> list[str]:
        self.calls.append((max_runs, until_done))
        answer = self._inner.argv(max_runs, until_done)
        self.issued.append(list(answer))
        return answer


class MemoryExitMarker(ExitMarker):
    """The marker as the text of the file (``None``: there is no file)."""

    def __init__(self, text: str | None = None) -> None:
        self.text = text

    def write(self, reason: str) -> None:
        self.text = reason + "\n"

    def clear(self) -> None:
        self.text = None

    def read(self) -> str:
        return (self.text or "").strip()


class MemorySchedulerLock(SchedulerLock):
    """The pidfile as a text (``None``: there is none); who is alive is asked of ``inspector``; ``own_pid`` is the process that takes the lock."""

    def __init__(self, inspector: ProcessInspector, text: str | None = None) -> None:
        self._inspector = inspector
        self.text = text

    def acquire(self) -> None:
        if self.text is not None:
            try:
                pid = int(self.text.strip())
            except ValueError:
                pid = 0  # garbled: nobody holds it
            if pid > 0 and self._inspector.is_alive(pid):
                raise OrgError(f"a scheduler is already running for this org (pid {pid})")
        self.text = str(self._inspector.own_ids()[0])

    def release(self) -> None:
        self.text = None


class FixedTasks(TaskQuery):
    """Root has one outstanding task while ``root_waits`` is true; nobody has anything else. ``asked`` keeps the addresses ``outstanding`` was asked about."""

    def __init__(self, root_waits: bool = False) -> None:
        self.root_waits = root_waits
        self.asked: list[str] = []

    def open_tasks(self, addr: str) -> list[Message]:
        return []

    def outstanding(self, addr: str) -> list[Message]:
        self.asked.append(addr)
        if addr == ROOT and self.root_waits:
            return [Message(sender=ROOT, to="ceo", type="task", title="Ship it", body="goal")]
        return []

    def blocked_tasks(self, addr: str) -> list[Message]:
        return []


class ScriptedSchedulerSpawner(ProcessSpawner):
    """Starts schedulers on a ``FakeProcessTable`` and plays what the scheduler process does as it starts: with ``starts_up`` it writes its pid to the
    pidfile, with ``exit_reason`` it leaves that in the exit marker. A process that is to end at once is scripted on the table (``will_exit``)."""

    def __init__(self, table: FakeProcessTable, layout: OrgLayout) -> None:
        self._table = table
        self._layout = layout
        self.starts_up = True
        self.exit_reason: str | None = None

    def spawn(
        self, argv: Sequence[str], *, cwd: Path, env: Mapping[str, str], stdin: object | None, stdout: object | None
    ) -> ProcessHandle:
        return self._table.spawn(argv, cwd=cwd, env=env, stdin=stdin, stdout=stdout)

    def spawn_detached(self, argv: Sequence[str], *, cwd: Path, env: Mapping[str, str], log: Path) -> ProcessHandle:
        handle = self._table.spawn_detached(argv, cwd=cwd, env=env, log=log)
        if self.starts_up:
            path = pidfile_of(self._layout)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(str(handle.pid))
        if self.exit_reason is not None:
            path = exit_file_of(self._layout)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(self.exit_reason + "\n")
        return handle


# ------------------------------------------------------------------------------ the process stage


@dataclass(frozen=True)
class ProcessStage:
    """Processes for a world: a table that is scripted (``FakeProcessTable``) or the machine's (only what ``start`` started is ever touched)."""

    inspector: ProcessInspector
    blind_inspector: ProcessInspector  # the same when ``ps`` cannot be run
    spawner: ProcessSpawner
    signaller: ProcessSignaller
    clock: Clock
    own_pid: int
    start: Callable[[Sequence[str]], int]  # a live process whose command line is ``LIVE_TEXT`` and these words; its pid
    gone: Callable[[], int]  # the pid of a process that existed and is gone
    close: Callable[[], None]  # kills what the stage started (only that)
    table: FakeProcessTable | None = None  # the scripted table, when there is one


def fake_stage(tmp_path: Path) -> ProcessStage:
    clock = FakeClock()
    table = FakeProcessTable(clock)

    def start(words: Sequence[str]) -> int:
        return table.spawn([*LIVE, *words], cwd=tmp_path, env={}, stdin=None, stdout=None).pid

    def gone() -> int:
        handle = table.spawn(["true"], cwd=tmp_path, env={}, stdin=None, stdout=None)
        table.exit(handle.pid, 0)
        handle.poll()  # reaped
        return handle.pid

    return ProcessStage(table, table.without_ps(), table, table, clock, table.own_ids()[0], start, gone, lambda: None, table)


def real_stage(tmp_path: Path) -> ProcessStage:
    world = real_world(tmp_path)

    def start(words: Sequence[str]) -> int:
        return world.spawner.spawn([*LIVE, *words], cwd=tmp_path, env=dict(os.environ), stdin=None, stdout=None).pid

    return ProcessStage(
        world.inspector, world.blind_inspector, world.spawner, world.signaller, system_clock(tmp_path), world.inspector.own_ids()[0], start,
        world.gone_pid, world.close,
    )


def _organization(tmp_path: Path) -> OrgPaths:
    root = tmp_path / "org"
    root.mkdir(exist_ok=True)
    return OrgPaths(root)


def _put_pidfile(layout: OrgLayout, text: str, at: datetime = AT) -> None:
    path = pidfile_of(layout)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    os.utime(path, (at.timestamp(), at.timestamp()))


# ------------------------------------------------------------------------------ SchedulerStatus


@dataclass(frozen=True)
class StatusWorld:
    """A ``SchedulerStatus`` over one organization, and the means to put the organization in a state."""

    status: SchedulerStatus
    root: Path
    scheduler: Callable[[], int]  # the pidfile names a live process that is this organization's scheduler; its pid
    process: Callable[[Sequence[str]], int]  # the pidfile names a live process whose command line is ``LIVE_TEXT`` and these words; its pid
    gone: Callable[[], int]  # the pidfile names a process that does not exist; its pid
    pidfile: Callable[[str], None]  # the pidfile holds this text (a pid that is not one, or 1 or less: it names no scheduler)
    no_pidfile: Callable[[], None]
    blind: Callable[[], SchedulerStatus]  # the same status when the process table cannot be read
    mark_exit: Callable[[str], None]  # the exit marker holds this text
    open_task: Callable[[bool], None]  # root has (or has not) a task that was not answered
    wait_on_user: Callable[[Waiting | None], None]  # what ``attention`` says about the user
    close: Callable[[], None]


def _status_world(tmp_path: Path, stage: ProcessStage) -> StatusWorld:
    layout = _organization(tmp_path)
    children = ChildRegistry()
    marker = FileExitMarker(layout, fs_atomic_writer(tmp_path).writer)
    tasks = FixedTasks()
    waiting = FixedWaiting()

    def status_over(inspector: ProcessInspector) -> SchedulerStatus:
        return PidFileSchedulerStatus(layout, inspector, SchedulerIdentity(), children, marker, tasks, waiting)

    def scheduler() -> int:
        pid = stage.start(["hirearchy", "--root", str(layout.root), "run"])
        _put_pidfile(layout, str(pid))
        return pid

    def process(words: Sequence[str]) -> int:
        pid = stage.start(words)
        _put_pidfile(layout, str(pid))
        return pid

    def gone() -> int:
        pid = stage.gone()
        _put_pidfile(layout, str(pid))
        return pid

    def no_pidfile() -> None:
        pidfile_of(layout).unlink(missing_ok=True)

    def mark_exit(text: str) -> None:
        path = exit_file_of(layout)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def wait_on_user(value: Waiting | None) -> None:
        waiting.waiting = value

    def open_task(value: bool) -> None:
        tasks.root_waits = value

    return StatusWorld(
        status_over(stage.inspector), layout.root, scheduler, process, gone, lambda text: _put_pidfile(layout, text), no_pidfile,
        lambda: status_over(stage.blind_inspector), mark_exit, open_task, wait_on_user, stage.close,
    )


def pidfile_status_world(tmp_path: Path) -> StatusWorld:
    """``PidFileSchedulerStatus`` over files and a scripted process table."""
    return _status_world(tmp_path, fake_stage(tmp_path))


def real_status_world(tmp_path: Path) -> StatusWorld:
    """``PidFileSchedulerStatus`` over files and the machine's process table (the processes are started by the world)."""
    return _status_world(tmp_path, real_stage(tmp_path))


def memory_status_world(tmp_path: Path) -> StatusWorld:
    """``FakeSchedulerStatus``: the state is set directly."""
    fake = FakeSchedulerStatus()
    pids = iter(range(30_000, 40_000))

    def scheduler() -> int:
        pid = next(pids)
        fake.current = SchedulerState("running", pid, SINCE)
        return pid

    def process(words: Sequence[str]) -> int:
        pid = next(pids)
        command = " ".join([*LIVE, *words])
        fake.current = SchedulerState("unverified", pid, SINCE, f"its command line is {command!r}")
        return pid

    def gone() -> int:
        fake.current = SchedulerState("stopped")
        return next(pids)

    def pidfile(text: str) -> None:
        fake.current = SchedulerState("stopped")

    def blind() -> SchedulerStatus:
        pid = fake.current.pid
        return FakeSchedulerStatus(
            SchedulerState("unverified", pid, fake.current.since, "the process table could not be read") if pid else fake.current,
            reason=fake.reason, open_tasks=fake.open_tasks, waiting=fake.waiting,
        )

    def mark_exit(text: str) -> None:
        fake.reason = text.strip()

    def open_task(value: bool) -> None:
        fake.open_tasks = value

    def wait_on_user(value: Waiting | None) -> None:
        fake.waiting = FixedWaiting(value)

    return StatusWorld(
        fake, tmp_path, scheduler, process, gone, pidfile, lambda: setattr(fake, "current", SchedulerState("stopped")), blind, mark_exit,
        open_task, wait_on_user, lambda: None,
    )


# ------------------------------------------------------------------------------ SchedulerControl


@dataclass(frozen=True)
class ControlWorld:
    """A ``SchedulerControl`` and the status that reads what it did. Starting launches a stand-in scheduler that writes its pid and waits to be told to go."""

    control: SchedulerControl
    status: SchedulerStatus
    root: Path
    impostor: Callable[[], int]  # the pidfile names a live process that is not a scheduler; its pid
    alive: Callable[[int], bool]  # the process (one the world started) has not been signalled
    stale: Callable[[], int]  # the pidfile names a process that is gone; its pid
    close: Callable[[], None]


STAND_IN = (
    "import os, sys, time, pathlib; root = pathlib.Path(sys.argv[2]); (root / '.runtime').mkdir(exist_ok=True); "
    "(root / '.runtime' / 'scheduler.pid').write_text(str(os.getpid())); time.sleep(60)"
)  # what a scheduler does as it starts, and then it waits; SIGTERM ends it


def _control_world(tmp_path: Path, stage: ProcessStage, spawner: ProcessSpawner, command: SchedulerCommand) -> ControlWorld:
    layout = _organization(tmp_path)
    children = ChildRegistry()
    marker = FileExitMarker(layout, fs_atomic_writer(tmp_path).writer)
    status = PidFileSchedulerStatus(layout, stage.inspector, SchedulerIdentity(), children, marker, FixedTasks(), FixedWaiting())
    launcher = DetachedLauncher(
        status, RuntimeLaunchSite(layout, MemoryIgnoreList(), marker, stage.clock), ScrubbedLaunchEnvironment(layout, os_environment(tmp_path).env), command, spawner,
        children, PidFileStartupWatch(layout, marker, stage.clock),
    )
    stopper = SignalSchedulerStopper(status, stage.signaller, stage.inspector, children, stage.clock)

    def impostor() -> int:
        pid = stage.start(["vim", "notes.txt"])
        _put_pidfile(layout, str(pid))
        return pid

    def stale() -> int:
        pid = stage.gone()
        _put_pidfile(layout, str(pid))
        return pid

    def alive(pid: int) -> bool:
        info = stage.inspector.info(pid)
        return info is not None and not info.state.startswith("Z")

    return ControlWorld(DetachedSchedulerControl(launcher, stopper), status, layout.root, impostor, alive, stale, stage.close)


def pidfile_control_world(tmp_path: Path) -> ControlWorld:
    """``DetachedSchedulerControl`` over files and a scripted process table; the scheduler it starts writes its pid and lives."""
    stage = fake_stage(tmp_path)
    assert stage.table is not None
    layout = _organization(tmp_path)
    return _control_world(tmp_path, stage, ScriptedSchedulerSpawner(stage.table, layout), FakeSchedulerCommand(layout))


def real_control_world(tmp_path: Path) -> ControlWorld:
    """``DetachedSchedulerControl`` over files and the machine's processes; the scheduler it starts is a stand-in program that the world's close kills."""
    stage = real_stage(tmp_path)
    layout = _organization(tmp_path)
    return _control_world(
        tmp_path, stage, stage.spawner, FixedSchedulerCommand([sys.executable, "-c", STAND_IN, "--root", str(layout.root), "run"]),
    )


def memory_control_world(tmp_path: Path) -> ControlWorld:
    """``FakeSchedulerControl`` over a ``FakeSchedulerStatus``."""
    status = FakeSchedulerStatus()
    control = FakeSchedulerControl(status)

    def impostor() -> int:
        status.current = SchedulerState("unverified", 777, SINCE, "its command line is 'vim notes.txt'")
        return 777

    def stale() -> int:
        status.current = SchedulerState("stopped")
        return 778

    return ControlWorld(control, status, tmp_path, impostor, lambda pid: pid not in control.signalled, stale, lambda: None)


# ------------------------------------------------------------------------------ SchedulerLock


@dataclass(frozen=True)
class LockWorld:
    lock: SchedulerLock
    root: Path
    own_pid: int  # the process that takes the lock
    pidfile: Callable[[], str | None]  # the text of the pidfile; None when there is none
    put: Callable[[str], None]  # the pidfile holds this text
    live_pid: Callable[[], int]  # a live process other than this one
    gone_pid: Callable[[], int]
    close: Callable[[], None]


def _lock_world(tmp_path: Path, stage: ProcessStage, make: Callable[[OrgLayout, ProcessInspector], SchedulerLock]) -> LockWorld:
    layout = _organization(tmp_path)

    def pidfile() -> str | None:
        path = pidfile_of(layout)
        return path.read_text() if path.is_file() else None

    return LockWorld(
        make(layout, stage.inspector), layout.root, stage.own_pid, pidfile, lambda text: _put_pidfile(layout, text),
        lambda: stage.start(["hirearchy", "run"]), stage.gone, stage.close,
    )


def pidfile_lock_world(tmp_path: Path) -> LockWorld:
    """``PidFileSchedulerLock`` over a file and a scripted process table."""
    return _lock_world(tmp_path, fake_stage(tmp_path), PidFileSchedulerLock)


def real_lock_world(tmp_path: Path) -> LockWorld:
    """``PidFileSchedulerLock`` over a file and the machine's processes."""
    return _lock_world(tmp_path, real_stage(tmp_path), PidFileSchedulerLock)


def memory_lock_world(tmp_path: Path) -> LockWorld:
    """``MemorySchedulerLock`` (the pidfile is a text) over a scripted process table."""
    stage = fake_stage(tmp_path)
    lock = MemorySchedulerLock(stage.inspector)

    def put(text: str) -> None:
        lock.text = text

    return LockWorld(lock, tmp_path, stage.own_pid, lambda: lock.text, put, lambda: stage.start(["hirearchy", "run"]), stage.gone, stage.close)


# ------------------------------------------------------------------------------ ExitMarker


@dataclass(frozen=True)
class MarkerWorld:
    marker: ExitMarker
    raw: Callable[[], str | None]  # the text of the marker's file; None when there is none
    put: Callable[[str], None]  # the file holds this text


def file_exit_marker_world(tmp_path: Path) -> MarkerWorld:
    layout = _organization(tmp_path)
    path = exit_file_of(layout)

    def put(text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    return MarkerWorld(FileExitMarker(layout, fs_atomic_writer(tmp_path).writer), lambda: path.read_text(encoding="utf-8") if path.is_file() else None, put)


def memory_exit_marker_world(tmp_path: Path) -> MarkerWorld:
    marker = MemoryExitMarker()

    def put(text: str) -> None:
        marker.text = text

    return MarkerWorld(marker, lambda: marker.text, put)


# ------------------------------------------------------------------------------ SchedulerCommand


@dataclass(frozen=True)
class CommandWorld:
    command: SchedulerCommand
    root: Path
    program: list[str]  # how every command line starts


def venv_command_world(tmp_path: Path) -> CommandWorld:
    layout = _organization(tmp_path)
    script = Path(sys.executable).with_name("hirearchy")
    program = [str(script)] if script.exists() else [sys.executable, "-m", "hirearchy"]
    return CommandWorld(VenvSchedulerCommand(layout, sys.executable), layout.root, program)


def fake_command_world(tmp_path: Path) -> CommandWorld:
    layout = _organization(tmp_path)
    return CommandWorld(FakeSchedulerCommand(layout, ["/venv/bin/hirearchy"]), layout.root, ["/venv/bin/hirearchy"])



IMPLEMENTATIONS: Mapping[type, Sequence[Callable[[Path], object]]] = {
    SchedulerStatus: [pidfile_status_world, real_status_world, memory_status_world],
    SchedulerControl: [pidfile_control_world, real_control_world, memory_control_world],
    SchedulerLock: [pidfile_lock_world, real_lock_world, memory_lock_world],
    ExitMarker: [file_exit_marker_world, memory_exit_marker_world],
    SchedulerCommand: [venv_command_world, fake_command_world],
}
