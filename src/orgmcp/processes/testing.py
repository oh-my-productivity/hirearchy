"""RED skeleton of the in-memory process table and of the registry the contract suites iterate over (step A-processes)."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from orgmcp.kernel import Clock

from .api import OrphanJudge, ProcessHandle, ProcessInfo, ProcessInspector, ProcessSignaller, ProcessSpawner


class FakeProcessHandle(ProcessHandle):
    @property
    def pid(self) -> int:
        raise NotImplementedError

    @property
    def returncode(self) -> int | None:
        raise NotImplementedError

    def poll(self) -> int | None:
        raise NotImplementedError

    def wait(self, timeout: float | None = None) -> int:
        raise NotImplementedError

    def signal_group(self, sig: int) -> None:
        raise NotImplementedError


@dataclass(frozen=True)
class SpawnRecord:
    """One call of ``spawn`` / ``spawn_detached`` on the fake table."""

    argv: tuple[str, ...]
    cwd: Path
    env: Mapping[str, str]
    pid: int
    log: Path | None = None


class FakeProcessTable(ProcessSpawner, ProcessInspector, ProcessSignaller):
    """One in-memory process table that is the spawner, the inspector and the signaller at once."""

    ps_works: bool
    spawned: list[SpawnRecord]
    signals: list[tuple[str, int, int]]  # (kind, target, signal) of every signal that reached a live process

    def __init__(self, clock: Clock | None = None, *, own_pid: int = 4000, own_pgid: int = 3990) -> None:
        raise NotImplementedError

    def will_exit(self, code: int, *, after: float = 0.0, output: str = "") -> None:
        raise NotImplementedError

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
        raise NotImplementedError

    def add_member(self, group: int) -> int:
        raise NotImplementedError

    def exit(self, pid: int, code: int = 0) -> None:
        raise NotImplementedError

    def exit_after(self, pid: int, seconds: float, code: int = 0) -> None:
        raise NotImplementedError

    def deny(self, pid: int) -> None:
        raise NotImplementedError

    def ignore_term(self, pid: int) -> None:
        raise NotImplementedError

    def spawn(
        self, argv: Sequence[str], *, cwd: Path, env: Mapping[str, str], stdin: object | None, stdout: object | None
    ) -> ProcessHandle:
        raise NotImplementedError

    def spawn_detached(self, argv: Sequence[str], *, cwd: Path, env: Mapping[str, str], log: Path) -> ProcessHandle:
        raise NotImplementedError

    def info(self, pid: int) -> ProcessInfo | None:
        raise NotImplementedError

    def command_line(self, pid: int) -> str | None:
        raise NotImplementedError

    def start_time(self, pid: int) -> str | None:
        raise NotImplementedError

    def is_session_leader(self, pgid: int) -> bool | None:
        raise NotImplementedError

    def is_alive(self, pid: int) -> bool:
        raise NotImplementedError

    def own_ids(self) -> tuple[int, int]:
        raise NotImplementedError

    def kill_group(self, pgid: int, wait: float = 5.0) -> bool:
        raise NotImplementedError

    def terminate(self, pid: int) -> None:
        raise NotImplementedError


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
    start_echo: Callable[[str, Path], ProcessHandle]  # spawn_detached: prints the text, exits 0
    start_bystander: Callable[[], int]  # alive, in the test's own process group, not a session leader
    start_zombie: Callable[[], int]  # exited and not reaped
    gone_pid: Callable[[], int]  # a pid of a process that does not exist
    close: Callable[[], None]  # kills what the world started (only that)


def real_world(tmp_path: Path) -> ProcessWorld:
    raise NotImplementedError("red: the real implementations are not written yet")


def fake_world(tmp_path: Path) -> ProcessWorld:
    raise NotImplementedError("red: the fake process table is not written yet")


IMPLEMENTATIONS: Mapping[type, Sequence[Callable[[Path], object]]] = {
    ProcessHandle: [real_world, fake_world],
    ProcessSpawner: [real_world, fake_world],
    ProcessInspector: [real_world, fake_world],
    ProcessSignaller: [real_world, fake_world],
    OrphanJudge: [real_world, fake_world],
}
