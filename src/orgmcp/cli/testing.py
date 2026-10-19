"""Fakes for ``cli``: the output that keeps what is said in the order it was said, a terminal that is told what it is, a session over a set of directories (and one that
answers what it is told, for the tests of the commands), the launchers of the other entry points that only record, the recording of a command that keeps what it is
given, and the program (``CliWorld``) made of them and of commands that do what the test says.

A test of a command builds the command over fakes of the ports it takes (``Provider`` thunks that return them), runs it with the arguments its own parser makes,
and reads what was said (``out.stdout`` / ``out.stderr``) and what the fakes were asked.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import TypeVar

from ..kernel import JsonObject, OrgError
from ..kernel.testing import FakeClock
from ..locator.testing import FixedOrgLocator
from ..telemetry.testing import MemoryEventSinks, MemoryProcessLabel
from ._app import ArgparseCliApp
from ._args import AtFileText
from ._ports import (
    Arguments,
    Command,
    CommandRecording,
    DashboardRunner,
    EventTail,
    EventTails,
    JsonDump,
    McpRunner,
    OrgOpener,
    OrgPorts,
    OrgSession,
    Output,
    SchedulerRunner,
    Terminal,
    TextSource,
)
from ._record import EventCommandRecorder
from ._session import AnnouncingOrgSession
from .api import CliApp

T = TypeVar("T")

# ------------------------------------------------------------------------------------------------------ what is said


class MemoryOutput(Output):
    """The standard output and error, each as the text a terminal would have shown, and what was said in what order (``events``)."""

    def __init__(self, journal: list[str] | None = None) -> None:
        self.events: list[tuple[str, str]] = []  # ("out" | "err", text as printed, with its newline)
        self.journal = journal  # a list shared with the other fakes of a test: ``say:<text>``, ``write:<text>``, ``warn:<text>``, in the order of the calls

    def say(self, text: str = "", flush: bool = False) -> None:
        self.events.append(("out", text + "\n"))
        self._note(f"say:{text}")

    def write(self, text: str) -> None:
        self.events.append(("out", text))
        self._note(f"write:{text}")

    def warn(self, text: str) -> None:
        self.events.append(("err", text + "\n"))
        self._note(f"warn:{text}")

    def _note(self, entry: str) -> None:
        if self.journal is not None:
            self.journal.append(entry)

    @property
    def stdout(self) -> str:
        return "".join(text for stream, text in self.events if stream == "out")

    @property
    def stderr(self) -> str:
        return "".join(text for stream, text in self.events if stream == "err")


class ScriptedTerminal(Terminal):
    def __init__(self, interactive: bool = False, stdout_tty: bool | None = None) -> None:
        self.interactive = interactive
        self.stdout_tty = interactive if stdout_tty is None else stdout_tty

    def is_interactive(self) -> bool:
        return self.interactive

    def stdout_is_tty(self) -> bool:
        return self.stdout_tty


class MemoryText(TextSource):
    """``@name`` is the text of ``files[name]`` (a missing file is the ``FileNotFoundError`` the real one raises)."""

    def __init__(self, files: Mapping[str, str] | None = None) -> None:
        self.files = dict(files or {})

    def read(self, value: str) -> str:
        if not value.startswith("@"):
            return value
        try:
            return self.files[value[1:]]
        except KeyError:
            raise FileNotFoundError(f"[Errno 2] No such file or directory: {value[1:]!r}") from None


class StaticJson(JsonDump):
    """``json.dumps(data, sort_keys=True)``: stable, and different from the text of the view."""

    def dump(self, data: object) -> str:
        import json

        return json.dumps(data, sort_keys=True, default=str)


# --------------------------------------------------------------------------------------------------- the organization


class MemoryOrgPorts(OrgPorts):
    """An opened organization: its root and the objects it answers for each port (``put``)."""

    def __init__(self, root: Path, objects: Mapping[type, object] | None = None) -> None:
        self._root = root
        self._objects: dict[type, object] = dict(objects or {})

    @property
    def root(self) -> Path:
        return self._root

    def put(self, port: type[T], obj: T) -> None:
        self._objects[port] = obj

    def get(self, port: type[T]) -> T:
        return self._objects[port]  # type: ignore[return-value]


class MemoryOrgOpener(OrgOpener):
    """The organizations are the set ``organizations`` of directories (no file is looked at); every opening is kept in ``opened`` (``prepared`` for a new one)."""

    def __init__(self, organizations: set[Path] | None = None, objects: Mapping[type, object] | None = None, events: list[str] | None = None) -> None:
        self.organizations = organizations if organizations is not None else set()
        self.objects = dict(objects or {})
        self.opened: list[Path] = []
        self.prepared: list[Path] = []
        self.events = events if events is not None else []  # what was done, in order, shared with the output of the test

    def open(self, root: Path) -> OrgPorts:
        self.events.append(f"open {root}")
        if root not in self.organizations:
            raise OrgError(f"not an organization (no ORG.md): {root}")
        self.opened.append(root)
        return MemoryOrgPorts(root, self.objects)

    def prepare(self, root: Path) -> OrgPorts:
        self.events.append(f"prepare {root}")
        self.prepared.append(root)
        return MemoryOrgPorts(root, self.objects)


class ScriptedOrgSession(OrgSession):
    """A session that answers what it is told: the organization is ``root`` (``exists`` says whether there is one) and every call is kept in ``calls``.

    ``open(args, mutating)`` is ``("open", mutating)`` and fails like the real one (``OrgError``) while the organization does not exist."""

    def __init__(self, root: Path, exists: bool = True, ports: MemoryOrgPorts | None = None) -> None:
        self.root = root
        self.exists = exists
        self.calls: list[tuple[str, object]] = []
        self.org = ports if ports is not None else MemoryOrgPorts(root)
        self._open = False

    def named(self, args: Arguments) -> Path:
        return Path(getattr(args, "root", None) or self.root)

    def open(self, args: Arguments, mutating: bool = False) -> Path:
        self.calls.append(("open", mutating))
        if not self.exists:
            raise OrgError(f"not an organization (no ORG.md): {self.root}")
        self._open = True
        return self.root

    def present(self, args: Arguments) -> bool:
        self.calls.append(("present", None))
        self._open = self.exists
        return self.exists

    def create(self, path: str) -> Path:
        self.calls.append(("create", path))
        self._open = True
        return Path(path)

    def ports(self) -> OrgPorts:
        if not self._open:
            raise OrgError("no organization is open")
        return self.org


# ------------------------------------------------------------------------------------------ the other entry points


@dataclass
class RecordingSchedulerRunner(SchedulerRunner):
    runs: list[tuple[Path, str, bool, bool, bool, int | None]] = field(default_factory=list)

    def run(self, root: Path, kiro_bin: str, once: bool, until_idle: bool, until_done: bool, max_runs: int | None) -> None:
        self.runs.append((root, kiro_bin, once, until_idle, until_done, max_runs))


@dataclass
class RecordingMcpRunner(McpRunner):
    runs: int = 0

    def run(self) -> None:
        self.runs += 1


@dataclass
class RecordingDashboardRunner(DashboardRunner):
    runs: list[tuple[Path, float]] = field(default_factory=list)

    def run(self, root: Path, interval: float) -> None:
        self.runs.append((root, interval))


class ListEventTail(EventTail):
    """Polls return the batches in order (then nothing); an exception in the script is raised by the poll that reaches it."""

    def __init__(self, polls: Sequence[Sequence[JsonObject] | BaseException]) -> None:
        self._polls = list(polls)

    def poll(self) -> list[JsonObject]:
        if not self._polls:
            return []
        step = self._polls.pop(0)
        if isinstance(step, BaseException):
            raise step
        return list(step)


class ScriptedEventTails(EventTails):
    def __init__(self, has_events: bool = True, polls: Sequence[Sequence[JsonObject] | BaseException] = ()) -> None:
        self.has_events = has_events
        self.tail = ListEventTail(polls)
        self.follows: list[tuple[str | None, str | None, str | None, bool]] = []

    def follow(self, agent: str | None, kind: str | None, trace: str | None, errors: bool) -> EventTail:
        self.follows.append((agent, kind, trace, errors))
        return self.tail

    def any(self) -> bool:
        return self.has_events


# -------------------------------------------------------------------------------------------------- the record


@dataclass
class RecordingRecorder(CommandRecording):
    """What the program told the recorder: (command, started, the failure or None)."""

    records: list[tuple[str, float, BaseException | None]] = field(default_factory=list)

    def record(self, args: Arguments, started: float, failure: BaseException | None) -> None:
        self.records.append((args.cmd, started, failure))


# ------------------------------------------------------------------------------------------------------ the program


class ScriptedCommand(Command):
    """A command named ``name`` that runs ``action(args)``: the arguments it takes are the flags ``flags`` (``--x`` -> ``args.x``, all optional text)."""

    def __init__(self, name: str, action: Callable[[Arguments], None] | None = None, flags: Sequence[str] = ()) -> None:
        self.name = name
        self.action = action
        self.flags = tuple(flags)
        self.ran: list[Arguments] = []

    def add_arguments(self, sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
        s = sub.add_parser(self.name, help=f"the command {self.name}")
        for flag in self.flags:
            s.add_argument(f"--{flag}")
        s.set_defaults(fn=self.run)

    def run(self, args: Arguments) -> None:
        self.ran.append(args)
        if self.action is not None:
            self.action(args)


@dataclass
class CliWorld:
    """A program of ``commands`` over fakes: ``out`` is what it said, ``recorder`` what it recorded, ``label`` the name of the process, ``clock`` its time."""

    app: CliApp
    commands: dict[str, ScriptedCommand]  # by name
    out: MemoryOutput
    recorder: RecordingRecorder
    label: MemoryProcessLabel
    clock: FakeClock


def cli_world(tmp_path: Path) -> CliWorld:
    """Three commands: ``ok`` (does nothing), ``bad`` (an ``OrgError``) and ``exit`` (``SystemExit`` with the code of its flag ``--code``)."""
    from ..kernel.testing import FakeClock

    def refuse(args: Arguments) -> None:
        raise OrgError("no such agent: nobody")

    def leave(args: Arguments) -> None:
        raise SystemExit(None if args.code is None else int(args.code))

    commands = [ScriptedCommand("ok"), ScriptedCommand("bad", refuse), ScriptedCommand("exit", leave, ("code",))]
    out, recorder, label, clock = MemoryOutput(), RecordingRecorder(), MemoryProcessLabel(), FakeClock()
    return CliWorld(ArgparseCliApp(commands, recorder, label, clock, out), {c.name: c for c in commands}, out, recorder, label, clock)


@dataclass
class RecordedWorld:
    """The recorder over the in-memory sinks and a session of a root: what ``cli.command`` events were written, and where."""

    recorder: CommandRecording
    sinks: MemoryEventSinks
    session: ScriptedOrgSession
    clock: FakeClock


def recorded_world(tmp_path: Path) -> RecordedWorld:
    from ..kernel.testing import FakeClock

    clock, sinks = FakeClock(), MemoryEventSinks()
    session = ScriptedOrgSession(tmp_path / "org")
    return RecordedWorld(EventCommandRecorder(sinks, session, clock), sinks, session, clock)


@dataclass
class SessionWorld:
    """The real session over a set of directories that are organizations, a locator that always finds ``found`` and the output of the test."""

    session: OrgSession
    opener: MemoryOrgOpener
    out: MemoryOutput
    found: Path


def session_world(tmp_path: Path) -> SessionWorld:
    out = MemoryOutput()
    base = tmp_path.resolve()
    found = base / "found"
    opener = MemoryOrgOpener({found, base / "given"})
    return SessionWorld(AnnouncingOrgSession(FixedOrgLocator(found), opener, out), opener, out, found)


@dataclass
class TextWorld:
    reader: TextSource
    make_file: Callable[[str, str], str]  # (name, text) -> the argument that names it: ``@<path>``


def _fs_text(tmp_path: Path) -> TextWorld:
    def make(name: str, text: str) -> str:
        (tmp_path / name).write_text(text, encoding="utf-8")
        return f"@{tmp_path / name}"

    return TextWorld(AtFileText(), make)


def _memory_text(tmp_path: Path) -> TextWorld:
    reader = MemoryText()

    def make(name: str, text: str) -> str:
        reader.files[str(tmp_path / name)] = text
        return f"@{tmp_path / name}"

    return TextWorld(reader, make)


IMPLEMENTATIONS: Mapping[type, Sequence[Callable[[Path], object]]] = {
    CliApp: [cli_world],
    TextSource: [_fs_text, _memory_text],
}

PURE = {"CliApp"}  # the program orchestrates commands and ports and has no input or output of its own: one implementation, tested over fakes of its ports
