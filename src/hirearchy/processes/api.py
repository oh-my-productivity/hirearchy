"""The public surface of ``processes``: the operating system's process table behind ports.

Starting a process in its own session, reading what ``ps`` says about a pid, signalling a process group, and judging whether
a process recorded by a dead scheduler is still ours. Nothing here knows about organizations, agents or runs.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable

__all__ = [
    "OrphanJudge",
    "ProcessDenied",
    "ProcessGone",
    "ProcessHandle",
    "ProcessInfo",
    "ProcessInspector",
    "ProcessSignaller",
    "ProcessSpawner",
    "ProcessTableError",
]


class ProcessTableError(Exception):
    """``ps`` (the process table) could not be run, so nothing is known about the process."""


class ProcessGone(Exception):
    """The process to signal does not exist (any more)."""


class ProcessDenied(Exception):
    """The process exists but may not be signalled (it is not ours, or its pid is not one we may signal)."""


@dataclass(frozen=True)
class ProcessInfo:
    """What ``ps`` reports about one process (run with ``LC_ALL=C TZ=UTC``, so the text is the same whatever the caller's locale)."""

    state: str  # ``ps -o stat``: starts with ``Z`` for a zombie
    started: str  # ``ps -o lstart``: e.g. ``Sun Oct 18 10:00:00 2026``, blanks collapsed to one space


@runtime_checkable
class ProcessHandle(Protocol):
    """A process this program started (and so is its parent: it can wait for it)."""

    @property
    def pid(self) -> int:
        """The process id; the process leads its own session, so this is also its process group id."""
        ...

    @property
    def returncode(self) -> int | None:
        """The exit code once ``poll`` or ``wait`` saw it (negative: killed by that signal); None while running."""
        ...

    def poll(self) -> int | None:
        """Exit code or None while running."""
        ...

    def wait(self, timeout: float | None = None) -> int:
        """Block until exit. Raises ``subprocess.TimeoutExpired`` when ``timeout`` seconds pass first."""
        ...

    def signal_group(self, sig: int) -> None:
        """Signal the process group; fall back to the process; ignore gone/denied."""
        ...


@runtime_checkable
class ProcessSpawner(Protocol):
    def spawn(
        self, argv: Sequence[str], *, cwd: Path, env: Mapping[str, str], stdin: object | None, stdout: object | None
    ) -> ProcessHandle:
        """Start in its own session (pgid == pid), stderr merged into stdout."""
        ...

    def spawn_detached(self, argv: Sequence[str], *, cwd: Path, env: Mapping[str, str], log: Path) -> int:
        """Start ``argv`` so that it is no descendant of this process: an intermediate process starts it in a session of its own (stdin /dev/null,
        stdout and stderr appended to ``log``, created if missing), reports its pid and exits at once, so it is re-parented (to launchd or init, or
        to the nearest subreaper on Linux) and outlives this process and every process of this process's tree. Returns its pid. ``OSError`` when
        the intermediate cannot be started, fails, or reports no pid within 10 seconds."""
        ...


@runtime_checkable
class ProcessInspector(Protocol):
    def info(self, pid: int) -> ProcessInfo | None:
        """None: no such process. Raises ProcessTableError if ps cannot run."""
        ...

    def command_line(self, pid: int) -> str | None:
        """`ps -o command=`; None when there is no such process, it has no command line, or ps cannot run."""
        ...

    def start_time(self, pid: int) -> str | None:
        """lstart or None (no such process, or ps cannot run)."""
        ...

    def is_session_leader(self, pgid: int) -> bool | None:
        """pgid and sid equal pgid; None if undecidable."""
        ...

    def is_alive(self, pid: int) -> bool:
        """kill(pid, 0) semantics (EPERM = alive); ``pid`` must be positive. A zombie is alive until its parent reaps it."""
        ...

    def own_ids(self) -> tuple[int, int]:
        """(pid, pgid) of this process."""
        ...


@runtime_checkable
class ProcessSignaller(Protocol):
    def kill_group(self, pgid: int, wait: float = 5.0) -> bool:
        """SIGKILL the group; True when its leader is gone. Never signals a group <= 1, nor this process's own pid or group."""
        ...

    def terminate(self, pid: int) -> None:
        """SIGTERM; raises ProcessGone / ProcessDenied (also for a pid <= 1 or this process's own pid or group)."""
        ...


@runtime_checkable
class OrphanJudge(Protocol):
    def judge(self, record: Mapping[str, object]) -> str:
        """'gone', 'foreign', 'ours' or 'doubt' (rules of today's judge_orphan).

        ``record`` is a ``.runtime/running.json`` entry: ``pgid`` (int) and ``lstart`` (str). The rules, in this order:

        * ``foreign``: ``pgid`` is not an int, is <= 1, or is this process's own pid or group (nothing is asked of ``ps``);
        * ``doubt``: ``ps`` cannot run;
        * ``gone``: no such process, or a zombie;
        * ``doubt``: no ``lstart`` recorded;
        * ``foreign``: the recorded ``lstart`` differs from the process's (the pid was reused);
        * ``doubt``: whether it leads its own session cannot be decided;
        * ``ours``: it leads its own session and process group; otherwise ``foreign``.

        Only ``ours`` may be killed.
        """
        ...
