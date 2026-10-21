"""The public surface of ``daemon``: the scheduler as a process of its own, started, found and stopped from outside.

A scheduler is one detached process per organization. It writes its pid to ``.runtime/scheduler.pid`` when it starts and removes it when it ends;
when it exits by itself (``run --until-done``) it leaves the reason in ``.runtime/scheduler.exit``. Everything else is read from the process
table: a pidfile is only believed when the process it names is alive and its command line is that of *this* organization's scheduler, so a pid
that was reused by something else is never signalled.
"""

from __future__ import annotations

from typing import NamedTuple, Protocol, runtime_checkable

__all__ = [
    "EXIT_FILE",
    "ExitMarker",
    "FINISHED",
    "SchedulerCommand",
    "SchedulerControl",
    "SchedulerLock",
    "SchedulerState",
    "SchedulerStatus",
]

EXIT_FILE = ".runtime/scheduler.exit"  # why the last scheduler exited by itself (until-done); removed when one starts
FINISHED = "finished: no open tasks"


class SchedulerState(NamedTuple):
    """``state``: ``stopped`` | ``running`` (verified to be this org's scheduler) | ``unverified`` (pid alive, not trusted)."""

    state: str
    pid: int | None = None
    since: str | None = None
    detail: str = ""


@runtime_checkable
class SchedulerStatus(Protocol):
    def state(self) -> SchedulerState:
        """Is a scheduler running for the organization? Read from ``.runtime/scheduler.pid`` and checked against the process table: ``stopped``
        (no pidfile, a pidfile that holds no pid, a pid of 1 or less, a process that is gone or a zombie), ``running`` (alive, and its command
        line is that of this organization's scheduler) or ``unverified`` (alive but not recognised, or the process table cannot be read;
        ``detail`` says which). ``since`` is the modification time of the pidfile, ``%Y-%m-%d %H:%M:%SZ`` in UTC."""
        ...

    def describe(self) -> str:
        """``scheduler: running (pid N, since T)``; ``scheduler: unknown - .runtime/scheduler.pid names pid N, which is alive but not verified to
        be this org's scheduler (D); not trusted``; or ``scheduler: stopped (R)``, where R is why the last scheduler exited by itself, else what
        the user must do (``attention.Waiting.text``), else ``scheduler: stopped``."""
        ...

    def exit_reason(self) -> str:
        """Why the last scheduler exited by itself, while that is still true (root has no outstanding task); else ``""``."""
        ...


@runtime_checkable
class SchedulerControl(Protocol):
    def start(self, max_runs: int | None = None, until_done: bool = False) -> int:
        """Launch a detached scheduler (its own session; output appended to ``.runtime/scheduler.log``) and return its pid.

        ``max_runs``: stop starting agent runs after this many (``None``: no cap; a negative cap is refused). ``until_done``: it exits by itself
        when root has no open task and nothing is running or runnable. Refused while one is running, or a live process the pidfile names cannot
        be verified. Waits up to ten seconds for the scheduler to write its pidfile; a scheduler that exits at once is an error (with the end of
        the log), unless it exited 0 leaving an exit marker (it had nothing left to do)."""
        ...

    def stop(self, wait: float = 15.0) -> str:
        """SIGTERM the scheduler named by the pidfile, only after checking that it is really this organization's scheduler, then wait up to
        ``wait`` seconds for it to end. A process that cannot be verified is never signalled."""
        ...


@runtime_checkable
class SchedulerLock(Protocol):
    def acquire(self) -> None:
        """Called by the scheduler process as it starts: refuse (``OrgError``) if the pidfile names a live process, else replace a stale or
        garbled pidfile with this process's pid."""
        ...

    def release(self) -> None:
        """Remove the pidfile (when it is already gone, nothing happens)."""
        ...


@runtime_checkable
class ExitMarker(Protocol):
    def write(self, reason: str) -> None:
        """Leave ``reason`` (one line) as the reason the scheduler exits by itself."""
        ...

    def clear(self) -> None:
        """Forget the reason (a scheduler starts; nothing happens when there is none)."""
        ...

    def read(self) -> str:
        """The reason, stripped; ``""`` when there is none."""
        ...


@runtime_checkable
class SchedulerCommand(Protocol):
    def argv(self, max_runs: int | None, until_done: bool) -> list[str]:
        """``<this venv's hirearchy> --root <org> run [--max-runs N] [--until-done]`` (``python -m hirearchy`` when the script is missing)."""
        ...
