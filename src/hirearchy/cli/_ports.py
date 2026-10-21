"""The ports the command line consumes, owned by it (ARCHITECTURE.md 3.36): the commands, the organization a command opens, what it prints to, the terminal, the
text of an argument, the recording of a finished command, and the launchers of the other entry points (the scheduler, the MCP server, the dashboard).

An entry point does not import another one, so what ``run``, ``mcp`` and ``dash`` start is a port here and the composition root puts the real thing behind it. The
features a command uses (``Hiring``, ``OrgSnapshotter``, ...) are the Protocols of their ``api`` and reach a command as ``Provider`` thunks that ask the organization
the session opened last, so a command is built before it is known which organization it works on.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Protocol, TypeVar, runtime_checkable

from ..kernel import JsonObject

T = TypeVar("T")

Arguments = argparse.Namespace

__all__ = [
    "Arguments", "Command", "CommandRecording", "DashboardRunner", "EventTail", "EventTails", "JsonDump", "McpRunner", "OrgOpener", "OrgPorts", "OrgSession", "Output",
    "SchedulerRunner", "Terminal", "TextSource",
]


@runtime_checkable
class Command(Protocol):
    """One sub-command: its place in the parser (names, flags and help text are the interface and do not change) and what it does."""

    def add_arguments(self, sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
        """Register the sub-parser and set ``fn`` to :meth:`run`."""
        ...

    def run(self, args: Arguments) -> None:
        """Execute. An ``OrgError`` is the command's way to say what is wrong; ``SystemExit`` its way to exit with a status."""
        ...


@runtime_checkable
class Output(Protocol):
    """What a command says: the standard output (a result) and the standard error (what it is about to do, what went wrong)."""

    def say(self, text: str = "", flush: bool = False) -> None:
        """``text`` and a newline on the standard output."""
        ...

    def write(self, text: str) -> None:
        """``text`` as it is on the standard output (no newline)."""
        ...

    def warn(self, text: str) -> None:
        """``text`` and a newline on the standard error, flushed (it must come before what a command does next)."""
        ...


@runtime_checkable
class Terminal(Protocol):
    def is_interactive(self) -> bool:
        """The standard input and the standard output are terminals (decides ``dash``: the full screen, or the text of ``--once``)."""
        ...

    def stdout_is_tty(self) -> bool:
        """The standard output is a terminal (``obs now --watch`` clears the screen only then)."""
        ...


@runtime_checkable
class TextSource(Protocol):
    def read(self, value: str) -> str:
        """``value`` as it is, or the text of the file when it is ``@path/to/file``."""
        ...


@runtime_checkable
class OrgPorts(Protocol):
    """An organization that was opened: its root, and the object that is its port ``port`` (asked for by the composition root only)."""

    @property
    def root(self) -> Path: ...

    def get(self, port: type[T]) -> T: ...


@runtime_checkable
class OrgOpener(Protocol):
    def open(self, root: Path) -> OrgPorts:
        """The ports of the organization at ``root``; an ``OrgError`` ``not an organization (no ORG.md): <root>`` when there is none."""
        ...

    def prepare(self, root: Path) -> OrgPorts:
        """The ports of an organization that is yet to be made at ``root`` (no ORG.md is needed)."""
        ...


@runtime_checkable
class OrgSession(Protocol):
    """The organization a command line is about: named by ``--root``, else by ``$ORG_ROOT`` or the working directory; opened once; announced when changed."""

    def named(self, args: Arguments) -> Path:
        """The root the command line names (resolved): ``--root``, else the organization found from the working directory (an ``OrgError`` when none is)."""
        ...

    def open(self, args: Arguments, mutating: bool = False) -> Path:
        """Open the organization the command line names and return its root. A ``mutating`` command first says on the standard error which organization it
        is about to change, before anything is read: also when the path turns out not to be an organization."""
        ...

    def present(self, args: Arguments) -> bool:
        """Open the organization the command line names if there is one (nothing is announced); False when there is none."""
        ...

    def create(self, path: str) -> Path:
        """Say which organization ``path`` is about to be made (standard error) and prepare it; returns its root (resolved)."""
        ...

    def ports(self) -> OrgPorts:
        """The organization that was opened last (``OrgError`` while none was)."""
        ...


@runtime_checkable
class CommandRecording(Protocol):
    def record(self, args: Arguments, started: float, failure: BaseException | None) -> None:
        """Emit the ``cli.command`` event of a finished command into the organization it was about to work on. Never raises."""
        ...


@runtime_checkable
class SchedulerRunner(Protocol):
    def run(self, root: Path, kiro_bin: str, once: bool, until_idle: bool, until_done: bool, max_runs: int | None) -> None:
        """Run the scheduler of the organization at ``root`` with the kiro binary ``kiro_bin``: one pass (``once``) or until it is told to stop."""
        ...


@runtime_checkable
class McpRunner(Protocol):
    def run(self) -> None:
        """Serve the MCP tools on the standard input and output until the client leaves."""
        ...


@runtime_checkable
class DashboardRunner(Protocol):
    def run(self, root: Path, interval: float) -> None:
        """Run the full-screen dashboard of the organization at ``root`` (refreshing every ``interval`` seconds) until it is quit."""
        ...


@runtime_checkable
class JsonDump(Protocol):
    def dump(self, data: object) -> str:
        """``data`` as indented JSON: datetimes as ISO text, tuples and sets as lists, paths as text."""
        ...


@runtime_checkable
class EventTail(Protocol):
    def poll(self) -> list[JsonObject]:
        """The events written since the last call (or since the tail was started), oldest first."""
        ...


@runtime_checkable
class EventTails(Protocol):
    def follow(self, agent: str | None, kind: str | None, trace: str | None, errors: bool) -> EventTail:
        """Start tailing the events that match the filter: what is in the files already is not returned."""
        ...

    def any(self) -> bool:
        """The organization has event files."""
        ...
