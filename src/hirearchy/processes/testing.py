"""In-memory process table and the registry the contract suites iterate over.

``FakeProcessTable`` is the spawner, the inspector and the signaller at once: processes are rows in a dictionary, time is the
``Clock`` it was given (a ``FakeClock``: it moves only when told), and exits are scripted. It obeys the same contract suites as
the real implementations (``tests/test_contract_*.py``), so a consumer's unit test may use it instead of real processes.
"""

from __future__ import annotations

import copy
import itertools
import os
import signal
import subprocess
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from hirearchy.kernel import Clock
from hirearchy.kernel.testing import DictEnvironment, FakeClock, os_environment, system_clock

from ._inspect import PsProcessInspector
from ._judge import PsOrphanJudge
from ._signal import OsProcessSignaller
from ._spawn import PopenProcessSpawner
from .api import (
    OrphanJudge,
    ProcessDenied,
    ProcessGone,
    ProcessHandle,
    ProcessInfo,
    ProcessInspector,
    ProcessSignaller,
    ProcessSpawner,
    ProcessTableError,
)

FIRST_PID = 20_000  # pids handed out by ``spawn`` and ``add_member``
TOLERANCE = 1e-6  # clocks have microsecond resolution


@dataclass
class _Process:
    pid: int
    pgid: int
    sid: int
    state: str
    started: str
    command: str
    ours: bool = False  # a child of the judging process: a zombie when it exits, until its handle polls
    running: bool = True
    code: int | None = None  # exit code once it exited (negative: killed by that signal)
    exit_at: float | None = None  # clock time of a scripted exit
    exit_code: int = 0  # the code of the scripted exit
    denied: bool = False  # belongs to someone else: signals to it are refused
    ignores_term: bool = False
    survives_kill: bool = False


@dataclass(frozen=True)
class SpawnRecord:
    """One call of ``spawn`` / ``spawn_detached`` on the fake table."""

    argv: tuple[str, ...]
    cwd: Path
    env: Mapping[str, str]
    pid: int
    log: Path | None = None


@dataclass
class _Script:
    code: int
    after: float
    output: str


class FakeProcessHandle(ProcessHandle):
    """The parent's view of a process spawned on a ``FakeProcessTable``."""

    def __init__(self, table: FakeProcessTable, process: _Process) -> None:
        self._table = table
        self._process = process
        self._returncode: int | None = None

    @property
    def pid(self) -> int:
        return self._process.pid

    @property
    def returncode(self) -> int | None:
        return self._returncode

    def poll(self) -> int | None:
        if self._returncode is None:
            self._table._settle()
            if not self._process.running:
                self._returncode = self._table._reap(self._process)
        return self._returncode

    def wait(self, timeout: float | None = None) -> int:
        code = self.poll()
        if code is not None:
            return code
        process, clock = self._process, self._table._clock
        if process.exit_at is None:
            if timeout is None:
                raise RuntimeError(f"wait() on process {process.pid} that nothing will end: script an exit or signal it")
            clock.sleep(timeout)
            self._table._settle()
            if process.running:
                raise subprocess.TimeoutExpired(process.command, timeout)
        else:
            remaining = process.exit_at - clock.time()
            if timeout is not None and remaining > timeout + TOLERANCE:
                clock.sleep(timeout)
                raise subprocess.TimeoutExpired(process.command, timeout)
            if remaining > 0:
                clock.sleep(remaining)
            if process.running:
                self._table._die(process, process.exit_code)
        self._returncode = self._table._reap(process)
        return self._returncode

    def signal_group(self, sig: int) -> None:
        self._table._signal_group(self._process.pid, sig)


class FakeProcessTable(ProcessSpawner, ProcessInspector, ProcessSignaller):
    """One in-memory process table that is the spawner, the inspector and the signaller at once.

    ``own_ids()`` is the judging process: ``own_pid`` in the group ``own_pgid`` (both are rows of the table, neither leads a
    session). ``ps_works = False`` makes ``info`` raise ``ProcessTableError`` and the rest of ``ps`` answer None, as when the
    ``ps`` program is missing; signals keep working.
    """

    ps_works: bool
    spawned: list[SpawnRecord]
    signals: list[tuple[str, int, int]]  # (kind, target, signal) of every signal that was sent

    def __init__(self, clock: Clock | None = None, *, own_pid: int = 4000, own_pgid: int = 3990) -> None:
        self._clock: Clock = clock or FakeClock()
        self._own = (own_pid, own_pgid)
        self._processes: dict[int, _Process] = {}
        self._pids = itertools.count(FIRST_PID)
        self._script: _Script | None = None
        self.ps_works = True
        self.spawned = []
        self.signals = []
        self.add(own_pgid, command="-zsh")
        self.add(own_pid, pgid=own_pgid, sid=own_pgid, command="pytest")

    # ------------------------------------------------------------------------------------------------------- scripting

    def will_exit(self, code: int, *, after: float = 0.0, output: str = "") -> None:
        """The NEXT spawned process prints ``output`` as it starts and exits with ``code`` ``after`` seconds later."""
        self._script = _Script(code, after, output)

    def add(
        self,
        pid: int,
        *,
        pgid: int | None = None,
        sid: int | None = None,
        state: str = "S",
        started: str | None = None,
        command: str = "",
        denied: bool = False,
        ignores_term: bool = False,
        survives_kill: bool = False,
    ) -> int:
        """A process that is not our child (init reaps it when it exits): by default a session leader. State ``Z``: a zombie."""
        if pid in self._processes:
            raise ValueError(f"process {pid} exists")
        group = pid if pgid is None else pgid
        self._processes[pid] = _Process(
            pid, group, group if sid is None else sid, state, started or self._lstart(), command,
            running=not state.startswith("Z"), code=None if not state.startswith("Z") else 0,
            denied=denied, ignores_term=ignores_term, survives_kill=survives_kill,
        )
        return pid

    def add_member(self, group: int) -> int:
        """A new process in the process group ``group`` (a grandchild of whoever leads it); returns its pid."""
        leader = self._processes.get(group)
        return self.add(self._new_pid(), pgid=group, sid=leader.sid if leader else group, command="sleep 60")

    def exit(self, pid: int, code: int = 0) -> None:
        """The process exits now: a zombie if it is our child (until its handle polls), else gone."""
        process = self._processes[pid]
        if process.running:
            self._die(process, code)

    def exit_after(self, pid: int, seconds: float, code: int = 0) -> None:
        """The process exits when the clock has moved ``seconds`` on."""
        process = self._processes[pid]
        process.exit_at, process.exit_code = self._clock.time() + seconds, code

    def deny(self, pid: int) -> None:
        """Signals to the process are refused (it belongs to someone else)."""
        self._processes[pid].denied = True

    def ignore_term(self, pid: int) -> None:
        """The process ignores SIGTERM."""
        self._processes[pid].ignores_term = True

    def without_ps(self) -> FakeProcessTable:
        """The same table (same processes, same clock) as seen when ``ps`` cannot be run."""
        view = copy.copy(self)
        view.ps_works = False
        return view

    # ---------------------------------------------------------------------------------------------------------- spawner

    def spawn(
        self, argv: Sequence[str], *, cwd: Path, env: Mapping[str, str], stdin: object | None, stdout: object | None
    ) -> ProcessHandle:
        script = self._script
        handle = self._start(argv, cwd, env, None)
        if script is not None and script.output:
            _write(stdout, script.output)
        return handle

    def spawn_detached(self, argv: Sequence[str], *, cwd: Path, env: Mapping[str, str], log: Path) -> int:
        """Not our child (its row has ``ours=False``): when it exits it is gone, there is no zombie and no handle to poll."""
        script = self._script
        with open(log, "ab") as out:  # like the real one: created if missing, appended to
            handle = self._start(argv, cwd, env, log, ours=False)
            if script is not None and script.output:
                out.write(script.output.encode("utf-8"))
        return handle.pid

    def is_child(self, pid: int) -> bool:
        """Is the process a child of the judging process (a zombie when it exits, until its handle polls)?"""
        process = self._processes.get(pid)
        return process is not None and process.ours

    def _start(self, argv: Sequence[str], cwd: Path, env: Mapping[str, str], log: Path | None, *, ours: bool = True) -> ProcessHandle:
        pid = self._new_pid()
        process = _Process(pid, pid, pid, "S", self._lstart(), " ".join(argv), ours=ours)
        script, self._script = self._script, None
        if script is not None:
            process.exit_at, process.exit_code = self._clock.time() + script.after, script.code
        self._processes[pid] = process
        self.spawned.append(SpawnRecord(tuple(argv), cwd, dict(env), pid, log))
        return FakeProcessHandle(self, process)

    # -------------------------------------------------------------------------------------------------------- inspector

    def info(self, pid: int) -> ProcessInfo | None:
        if not self.ps_works:
            raise ProcessTableError("ps: command not found")
        self._settle()
        process = self._processes.get(pid)
        return ProcessInfo(process.state, process.started) if process else None

    def command_line(self, pid: int) -> str | None:
        if not self.ps_works:
            return None
        self._settle()
        process = self._processes.get(pid)
        return (process.command or None) if process else None

    def start_time(self, pid: int) -> str | None:
        if not self.ps_works:
            return None
        self._settle()
        process = self._processes.get(pid)
        return process.started if process else None

    def is_session_leader(self, pgid: int) -> bool | None:
        self._settle()
        process = self._processes.get(pgid)
        return None if process is None else process.pgid == pgid and process.sid == pgid

    def is_alive(self, pid: int) -> bool:
        self._settle()
        return pid in self._processes

    def own_ids(self) -> tuple[int, int]:
        return self._own

    # -------------------------------------------------------------------------------------------------------- signaller

    def kill_group(self, pgid: int, wait: float = 5.0) -> bool:
        if self._refused(pgid):
            return False
        self._settle()
        members = [p for p in self._processes.values() if p.pgid == pgid]
        if not members:
            return True
        if all(p.denied for p in members):
            return False
        self._signal_members("group", pgid, members, signal.SIGKILL)
        deadline = self._clock.time() + wait
        while self._clock.time() < deadline:
            try:
                info = self.info(pgid)
            except ProcessTableError:
                return False
            if info is None or info.state.startswith("Z"):
                return True
            self._clock.sleep(0.05)
        return False

    def terminate(self, pid: int) -> None:
        if self._refused(pid):
            raise ProcessDenied(f"not signalling pid {pid}")
        self._settle()
        process = self._processes.get(pid)
        if process is None:
            raise ProcessGone(f"no process {pid}")
        if process.denied:
            raise ProcessDenied(f"not allowed to signal pid {pid}")
        self._signal_members("process", pid, [process], signal.SIGTERM)

    # ----------------------------------------------------------------------------------------------------------- inside

    def _refused(self, pid: int) -> bool:
        return pid <= 1 or pid in self._own

    def _new_pid(self) -> int:
        pid = next(self._pids)
        while pid in self._processes or pid in self._own:
            pid = next(self._pids)
        return pid

    def _lstart(self) -> str:
        """``ps -o lstart`` with ``LC_ALL=C TZ=UTC`` and the blanks collapsed, for the time of the clock."""
        now = self._clock.now()
        return f"{now:%a %b} {now.day} {now:%H:%M:%S %Y}"

    def _settle(self) -> None:
        """Let the scripted exits whose time has come happen."""
        now = self._clock.time()
        for process in list(self._processes.values()):
            if process.running and process.exit_at is not None and process.exit_at <= now + TOLERANCE:
                self._die(process, process.exit_code)

    def _die(self, process: _Process, code: int) -> None:
        process.running, process.code, process.exit_at = False, code, None
        if process.ours:
            process.state = "Z"  # until its handle polls
        else:
            del self._processes[process.pid]

    def _reap(self, process: _Process) -> int:
        self._processes.pop(process.pid, None)
        return process.code if process.code is not None else 0

    def _signal_group(self, pgid: int, sig: int) -> None:
        self._settle()
        members = [p for p in self._processes.values() if p.pgid == pgid]
        if members:
            self._signal_members("group", pgid, members, sig)

    def _signal_members(self, kind: str, target: int, members: list[_Process], sig: int) -> None:
        allowed = [p for p in members if not p.denied]
        if not allowed:
            return
        self.signals.append((kind, target, sig))
        for process in allowed:
            if not process.running or sig == 0 or process.survives_kill:
                continue
            if sig == signal.SIGTERM and process.ignores_term:
                continue
            self._die(process, -sig)


def _write(target: object | None, text: str) -> None:
    """What a process prints into the file it was given."""
    write = getattr(target, "write", None)
    if write is None:
        return
    try:
        write(text)
    except TypeError:
        write(text.encode("utf-8"))
    flush = getattr(target, "flush", None)
    if flush is not None:
        flush()


@dataclass
class ProcessWorld:
    """What a contract test needs of one implementation: the ports, and ways to bring processes into being.

    A real world starts real processes (and kills, at ``close``, only the ones it started); the fake world scripts a
    ``FakeProcessTable``. Every ``start_*`` returns a process the test owns.
    """

    spawner: ProcessSpawner
    inspector: ProcessInspector
    signaller: ProcessSignaller
    judge: OrphanJudge
    blind_inspector: ProcessInspector  # the same implementation when ``ps`` cannot be run
    blind_judge: OrphanJudge
    directory: Path
    start_leader: Callable[[], ProcessHandle]  # lives until signalled; leads its own session
    start_group: Callable[[], tuple[ProcessHandle, int]]  # such a leader and the pid of a grandchild in its group
    start_term_proof: Callable[[], ProcessHandle]  # ignores SIGTERM
    start_exiting: Callable[[int], ProcessHandle]  # exits at once with the code
    start_echo: Callable[[str, Path], int]  # spawn_detached: prints the text, exits 0; returns the pid
    is_child: Callable[[int], bool]  # the process is a child of this process (real: ``os.waitpid`` finds it; fake: the row's ``ours``)
    start_bystander: Callable[[], int]  # alive, in the test's own process group, not a session leader
    start_zombie: Callable[[], int]  # exited and not reaped
    gone_pid: Callable[[], int]  # a pid of a process that does not exist
    close: Callable[[], None]  # kills what the world started (only that)


class _TrackingSpawner(PopenProcessSpawner):
    """The real spawner that remembers every process it started, so that the world can kill those and only those."""

    def __init__(self) -> None:
        self.started: list[ProcessHandle] = []
        self.detached: list[int] = []  # pids; each leads its own group and is nobody's child

    def spawn(
        self, argv: Sequence[str], *, cwd: Path, env: Mapping[str, str], stdin: object | None, stdout: object | None
    ) -> ProcessHandle:
        handle = super().spawn(argv, cwd=cwd, env=env, stdin=stdin, stdout=stdout)
        self.started.append(handle)
        return handle

    def spawn_detached(self, argv: Sequence[str], *, cwd: Path, env: Mapping[str, str], log: Path) -> int:
        pid = super().spawn_detached(argv, cwd=cwd, env=env, log=log)
        self.detached.append(pid)
        return pid


def _wait_for(condition: Callable[[], bool], what: str, timeout: float = 10.0) -> None:
    deadline = time.monotonic() + timeout
    while not condition():
        if time.monotonic() > deadline:
            raise TimeoutError(f"gave up waiting for {what}")
        time.sleep(0.01)


def judge_over(inspector: ProcessInspector) -> OrphanJudge:
    """The real judge over this process table (for a consumer that has a table of its own and judges the runs a dead scheduler left)."""
    return PsOrphanJudge(inspector)


def real_world(tmp_path: Path) -> ProcessWorld:
    """Real processes. They are all started by this world, and ``close`` signals those and nothing else."""
    environment = os_environment(tmp_path).env
    inspector = PsProcessInspector(environment)
    blind = PsProcessInspector(DictEnvironment({"PATH": str(tmp_path / "no-ps-here")}))  # ``ps`` is not found
    spawner = _TrackingSpawner()
    own: list[subprocess.Popen[bytes]] = []  # children that are not run through the spawner
    grandchildren: list[tuple[int, int]] = []  # (pid of the leader we started, pid of a process it started)
    counter = itertools.count()

    def env() -> dict[str, str]:
        return dict(os.environ)

    def spawn(*argv: str) -> ProcessHandle:
        return spawner.spawn(list(argv), cwd=tmp_path, env=env(), stdin=None, stdout=None)

    def leader() -> ProcessHandle:
        return spawn("sleep", "60")

    def group() -> tuple[ProcessHandle, int]:
        pidfile = tmp_path / f"grandchild-{next(counter)}.pid"
        handle = spawn("sh", "-c", f"sleep 60 & echo $! > '{pidfile}'; wait")
        _wait_for(lambda: pidfile.is_file() and pidfile.read_text().endswith("\n"), "the grandchild to start")
        grandchild = int(pidfile.read_text())
        grandchildren.append((handle.pid, grandchild))
        return handle, grandchild

    def term_proof() -> ProcessHandle:
        ready = tmp_path / f"ready-{next(counter)}"
        handle = spawn("sh", "-c", f"trap '' TERM; touch '{ready}'; while :; do sleep 1; done")
        _wait_for(ready.is_file, "the shell to ignore SIGTERM")
        return handle

    def exiting(code: int) -> ProcessHandle:
        return spawn("sh", "-c", f"exit {code}")

    def echo(text: str, log: Path) -> int:
        return spawner.spawn_detached(["sh", "-c", 'printf %s "$0"', text], cwd=tmp_path, env=env(), log=log)

    def is_child(pid: int) -> bool:
        try:
            os.waitpid(pid, os.WNOHANG)
        except ChildProcessError:
            return False
        return True

    def bystander() -> int:
        proc = subprocess.Popen(["sleep", "60"])  # same session and group as the test run itself
        own.append(proc)
        return proc.pid

    def zombie() -> int:
        proc = subprocess.Popen(["true"], start_new_session=True)  # reaped by ``close``, not before
        own.append(proc)
        _wait_for(lambda: (info := inspector.info(proc.pid)) is not None and info.state.startswith("Z"), "the child to exit")
        return proc.pid

    def gone() -> int:
        proc = subprocess.Popen(["true"], start_new_session=True)
        proc.wait()
        return proc.pid

    def close() -> None:
        for handle in spawner.started:
            if handle.poll() is None:  # not yet reaped, so the pid is still ours
                handle.signal_group(signal.SIGKILL)
        for leader_pid, member in grandchildren:
            try:  # the leader may be reaped: only a member that is still in the leader's group is signalled
                if os.getpgid(member) == leader_pid:
                    os.kill(member, signal.SIGKILL)
            except OSError:
                pass
        for pid in spawner.detached:  # started by the world, each leads its own group: only that group is signalled
            try:
                if os.getpgid(pid) == pid:
                    os.killpg(pid, signal.SIGKILL)
            except OSError:
                pass
        for handle in spawner.started:
            handle.wait(timeout=10)
        for proc in own:
            if proc.poll() is None:
                proc.kill()
            proc.wait()

    return ProcessWorld(
        spawner=spawner, inspector=inspector, signaller=OsProcessSignaller(inspector, system_clock(tmp_path)),
        judge=PsOrphanJudge(inspector), blind_inspector=blind, blind_judge=PsOrphanJudge(blind), directory=tmp_path,
        start_leader=leader, start_group=group, start_term_proof=term_proof, start_exiting=exiting, start_echo=echo,
        is_child=is_child, start_bystander=bystander, start_zombie=zombie, gone_pid=gone, close=close,
    )


def fake_world(tmp_path: Path) -> ProcessWorld:
    table = FakeProcessTable()
    blind = table.without_ps()
    env: dict[str, str] = {}

    def leader() -> ProcessHandle:
        return table.spawn(["sleep", "60"], cwd=tmp_path, env=env, stdin=None, stdout=None)

    def group() -> tuple[ProcessHandle, int]:
        handle = leader()
        return handle, table.add_member(handle.pid)

    def term_proof() -> ProcessHandle:
        handle = leader()
        table.ignore_term(handle.pid)
        return handle

    def exiting(code: int) -> ProcessHandle:
        table.will_exit(code)
        return table.spawn(["sh", "-c", f"exit {code}"], cwd=tmp_path, env=env, stdin=None, stdout=None)

    def echo(text: str, log: Path) -> int:
        table.will_exit(0, output=text)
        return table.spawn_detached(["sh", "-c", "echo"], cwd=tmp_path, env=env, log=log)

    def bystander() -> int:
        return table.add(table._new_pid(), pgid=table.own_ids()[1], sid=table.own_ids()[1], command="sleep 60")

    def zombie() -> int:
        table.will_exit(0)
        return table.spawn(["true"], cwd=tmp_path, env=env, stdin=None, stdout=None).pid

    def gone() -> int:
        return table._new_pid()

    return ProcessWorld(
        spawner=table, inspector=table, signaller=table, judge=PsOrphanJudge(table), blind_inspector=blind, blind_judge=PsOrphanJudge(blind),
        directory=tmp_path, start_leader=leader, start_group=group, start_term_proof=term_proof, start_exiting=exiting,
        start_echo=echo, is_child=table.is_child, start_bystander=bystander, start_zombie=zombie, gone_pid=gone, close=lambda: None,
    )


IMPLEMENTATIONS: Mapping[type, Sequence[Callable[[Path], object]]] = {
    ProcessHandle: [real_world, fake_world],
    ProcessSpawner: [real_world, fake_world],
    ProcessInspector: [real_world, fake_world],
    ProcessSignaller: [real_world, fake_world],
    OrphanJudge: [real_world, fake_world],
}
