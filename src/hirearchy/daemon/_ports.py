"""The ports ``daemon`` defines for its own classes (consumer-owned, narrower than the provider's): who recognises a scheduler, who reaps its children,
and the parts of starting and stopping one."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Protocol, runtime_checkable

from ..processes import ProcessHandle


@runtime_checkable
class SchedulerRecognizer(Protocol):
    def recognises(self, command: str, root: Path) -> bool:
        """Does this command line plausibly start the scheduler of the organization at ``root``?"""
        ...


@runtime_checkable
class Children(Protocol):
    def adopt(self, handle: ProcessHandle) -> None:
        """Remember a scheduler this process started: it is reaped when it ends, so that it never lingers as a zombie."""
        ...

    def reap(self) -> None:
        """Forget (and so reap) the children that have ended."""
        ...


@runtime_checkable
class LaunchSite(Protocol):
    def directory(self) -> Path:
        """The organization directory: where the scheduler is started."""
        ...

    def prepare(self) -> Path:
        """Get the organization ready for a scheduler: ``.runtime`` exists, the files that change constantly are kept out of its git snapshots,
        and the reason of the last exit is forgotten. Returns the log the scheduler's output is appended to."""
        ...

    def announce(self, log: Path, argv: Sequence[str]) -> None:
        """Put the line that says when, and with what command, a scheduler was started at the end of the log."""
        ...


@runtime_checkable
class LaunchEnvironment(Protocol):
    def variables(self) -> dict[str, str]:
        """The environment of the scheduler: this process's, bound to the organization, unbuffered, and without the identity of an agent."""
        ...


@runtime_checkable
class StartupWatch(Protocol):
    def await_start(self, pid: int, log: Path) -> int:
        """Wait for the scheduler that was just started as ``pid`` (not our child) to say it is up (it writes its pid). Returns the pid in the pid file.
        Raises ``OrgError`` when it exits at once."""
        ...


@runtime_checkable
class SchedulerLauncher(Protocol):
    def start(self, max_runs: int | None, until_done: bool) -> int:
        """``SchedulerControl.start``."""
        ...


@runtime_checkable
class SchedulerStopper(Protocol):
    def stop(self, wait: float) -> str:
        """``SchedulerControl.stop``."""
        ...
