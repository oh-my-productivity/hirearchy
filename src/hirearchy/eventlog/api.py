"""The public surface of ``eventlog``: the format of the event log on disk, and how to read it.

One append-only JSONL file per process per UTC day, ``.runtime/events/<YYYY-MM-DD>/<proc>-<pid>-<start_epoch_ms>.jsonl``;
every line is one JSON object whose envelope is ``ENVELOPE``. This package only reads: the writer is ``telemetry``, which takes the
format constants from here (a reader never imports the writer). The readers tolerate what a live system produces: a partial last
line, unknown kinds and fields, missing directories, files of other days, and an organization with no events at all.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Protocol, runtime_checkable

from ..kernel import JsonObject

__all__ = [
    "DAY_RE",
    "ENVELOPE",
    "EVENTS_REL",
    "EventFile",
    "EventFollower",
    "EventFollowers",
    "EventReader",
    "LINE_MAX",
    "PROCS",
    "SCHEMA_VERSION",
    "event_file",
]

SCHEMA_VERSION = 1  # the ``v`` of every line
LINE_MAX = 8192  # bytes per line
EVENTS_REL = Path(".runtime") / "events"  # where the day directories are, relative to the organization root
DAY_RE = re.compile(r"\d{4}-\d{2}-\d{2}\Z")  # a day directory
ENVELOPE = ("v", "ts", "seq", "proc", "pid", "kind", "actor", "run", "trace")  # the fields every line has, in this order
PROCS = ("scheduler", "mcp", "cli")  # the processes that write events

_NAME = re.compile(r"(?P<proc>.+)-(?P<pid>\d+)-(?P<ms>\d+)")


@dataclass(frozen=True)
class EventFile:
    """One event file: ``<day>/<proc>-<pid>-<start_epoch_ms>.jsonl``. A name of another shape has ``proc == ""`` and ``pid == 0``."""

    path: Path
    day: str  # the name of the day directory, ``YYYY-MM-DD``
    proc: str  # scheduler, mcp or cli
    pid: int
    stem: str  # the name without ``.jsonl``

    @property
    def start_ms(self) -> int:
        """When the writing process started, in epoch milliseconds (0 when the name does not say)."""
        match = _NAME.fullmatch(self.stem)
        return int(match.group("ms")) if match else 0


def event_file(path: Path) -> EventFile:
    """The ``EventFile`` that the path names (nothing is read: the day is the name of the directory)."""
    match = _NAME.fullmatch(path.stem)
    return EventFile(
        path=path,
        day=path.parent.name,
        proc=match.group("proc") if match else "",
        pid=int(match.group("pid")) if match else 0,
        stem=path.stem,
    )


@runtime_checkable
class EventReader(Protocol):
    """Reads the event files of one organization."""

    def files(self, since: datetime | None = None, until: datetime | None = None) -> list[EventFile]:
        """The event files that can hold events in ``[since, until]``: the day directories of the window first, then their files by
        name (a file not written since ``since`` has nothing newer). Hidden files, other extensions and other directories are not
        event files."""
        ...

    def read_file(self, file: EventFile) -> Iterator[tuple[datetime, JsonObject]]:
        """(time, event) of every line of the file that is a JSON object with a readable ``ts``; a partial last line and foreign
        lines are skipped; a file that cannot be opened has no events."""
        ...

    def timed(self, since: datetime | None = None, until: datetime | None = None) -> Iterator[tuple[datetime, JsonObject]]:
        """Events in ``[since, until]`` as (time, event), merged over all files in time order (every file is time-ordered by its
        single writer)."""
        ...

    def events(self, since: datetime | None = None, until: datetime | None = None) -> Iterator[JsonObject]:
        """The events of ``timed``, without their times."""
        ...

    def tail(self, file: EventFile, nbytes: int = 65536) -> list[JsonObject]:
        """The complete events among the last ``nbytes`` bytes of the file (a line that the cut makes partial is dropped)."""
        ...

    def head(self, file: EventFile) -> JsonObject | None:
        """The first line of the file as an event; None when the file is empty, unreadable or starts with something else."""
        ...


@runtime_checkable
class EventFollower(Protocol):
    """Tails the event files from the point where it was started."""

    def poll(self, emit: bool = True, now: datetime | None = None) -> list[JsonObject]:
        """The complete new lines, since the last call, of the files of the day before to the day after ``now`` (default: the clock),
        in time order. A file that appears later (a new process) is read from its start. ``emit=False`` only moves the position."""
        ...


@runtime_checkable
class EventFollowers(Protocol):
    """Starts followers."""

    def follow(self, match: Callable[[JsonObject], bool] | None = None, now: datetime | None = None) -> EventFollower:
        """Start tailing: what is already in the files is not returned; only events that ``match`` (default: all) are."""
        ...
