"""In-memory event log, the authoring helpers of the tests, and the registry the contract suites iterate over.

``MemoryEventLog`` is the reader and the followers at once, over files that are byte strings in a dictionary (so a partial last
line can be written to it, as a live writer leaves one). The contract suites run against it and against the disk readers.
``EventLogHarness`` writes event lines "the way the runtime does" (one file per process per UTC day, ``seq`` counting the lines of
one file) into whichever of the two the suite is checking: the tests never import the writer.
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

from orgmcp.kernel import Clock, JsonObject, OrgPaths
from orgmcp.kernel.testing import T0, FakeClock

from ._follower import FsEventFollowers
from ._reader import FsEventReader
from .api import EVENTS_REL, EventFile, EventFollower, EventFollowers, EventReader, event_file


class EventStore(Protocol):
    """Where the bytes of an event log are: the two primitives that the authoring helper needs."""

    def append(self, day: str, name: str, data: bytes) -> None:
        """Append to ``<day>/<name>`` (the file and the directory are created)."""
        ...

    def touch(self, day: str, name: str, when: datetime) -> None:
        """Set the modification time of ``<day>/<name>``."""
        ...


class MemoryEventLog(EventReader, EventFollowers, EventStore):
    """The event log in memory: ``files`` of ``day -> name -> bytes``, each with a modification time."""

    def __init__(self, clock: Clock | None = None) -> None:
        raise NotImplementedError("red: the in-memory event log is not written yet")

    def append(self, day: str, name: str, data: bytes) -> None:
        raise NotImplementedError

    def touch(self, day: str, name: str, when: datetime) -> None:
        raise NotImplementedError

    def files(self, since: datetime | None = None, until: datetime | None = None) -> list[EventFile]:
        raise NotImplementedError

    def read_file(self, file: EventFile) -> Iterator[tuple[datetime, JsonObject]]:
        raise NotImplementedError

    def timed(self, since: datetime | None = None, until: datetime | None = None) -> Iterator[tuple[datetime, JsonObject]]:
        raise NotImplementedError

    def events(self, since: datetime | None = None, until: datetime | None = None) -> Iterator[JsonObject]:
        raise NotImplementedError

    def tail(self, file: EventFile, nbytes: int = 65536) -> list[JsonObject]:
        raise NotImplementedError

    def head(self, file: EventFile) -> JsonObject | None:
        raise NotImplementedError

    def follow(self, match: Callable[[JsonObject], bool] | None = None, now: datetime | None = None) -> EventFollower:
        raise NotImplementedError


class DiskEventStore(EventStore):
    """``<root>/.runtime/events`` on the disk, written by hand."""

    def __init__(self, events_dir: Path) -> None:
        self.base = events_dir

    def append(self, day: str, name: str, data: bytes) -> None:
        path = self.base / day / name
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "ab") as f:
            f.write(data)

    def touch(self, day: str, name: str, when: datetime) -> None:
        stamp = when.timestamp()
        os.utime(self.base / day / name, (stamp, stamp))


class EventLogAuthor(Protocol):
    """Writes event lines into a log the way the runtime does, for the tests."""

    def file(self, day: str, proc: str, pid: int) -> EventFile:
        """The file of this process on this day (its name carries the start of the process, allocated on first use)."""
        ...

    def emit(self, ts: datetime, kind: str = "tool.call", *, proc: str = "mcp", pid: int = 4242, **fields: object) -> JsonObject:
        """Append one complete line to the file of ``proc``/``pid`` on the UTC day of ``ts``; the file is last written at the latest
        ``ts`` it holds. Returns the event."""
        ...

    def raw(self, day: str, proc: str, pid: int, text: str) -> EventFile:
        """Append text as it is (a line being written has no newline yet)."""
        ...

    def foreign(self, day: str, name: str, data: bytes = b"") -> None:
        """Put a file of any name (not an event file when the name says so) in a day directory."""
        ...

    def touch(self, file: EventFile, when: datetime) -> None:
        """Set the time the file was last written."""
        ...


class StoreEventLogAuthor(EventLogAuthor):
    def __init__(self, store: EventStore, base: Path) -> None:
        self._store = store
        self._base = base
        self._started: dict[tuple[str, int], int] = {}
        self._seq: dict[tuple[str, str], int] = {}
        self._mtime: dict[tuple[str, str], datetime] = {}

    def file(self, day: str, proc: str, pid: int) -> EventFile:
        start_ms = self._started.setdefault((proc, pid), int(T0.timestamp() * 1000) + len(self._started))
        return event_file(self._base / day / f"{proc}-{pid}-{start_ms}.jsonl")

    def emit(self, ts: datetime, kind: str = "tool.call", *, proc: str = "mcp", pid: int = 4242, **fields: object) -> JsonObject:
        target = self.file(ts.astimezone(timezone.utc).strftime("%Y-%m-%d"), proc, pid)
        key = (target.day, target.path.name)
        self._seq[key] = self._seq.get(key, 0) + 1
        event: JsonObject = {
            "v": 1, "ts": ts.isoformat(), "seq": self._seq[key], "proc": proc, "pid": pid, "kind": kind,
            "actor": "runtime", "run": None, "trace": None, **fields,
        }
        self._store.append(*key, (json.dumps(event) + "\n").encode())
        self._mtime[key] = max(self._mtime.get(key, ts), ts)
        self._store.touch(*key, self._mtime[key])
        return event

    def raw(self, day: str, proc: str, pid: int, text: str) -> EventFile:
        target = self.file(day, proc, pid)
        self._store.append(day, target.path.name, text.encode())
        return target

    def foreign(self, day: str, name: str, data: bytes = b"") -> None:
        self._store.append(day, name, data)

    def touch(self, file: EventFile, when: datetime) -> None:
        self._store.touch(file.day, file.path.name, when)


@dataclass(frozen=True)
class EventLogHarness:
    """One implementation under test: the readers, the clock they use, and the way to put events where they look."""

    reader: EventReader
    followers: EventFollowers
    clock: FakeClock
    log: EventLogAuthor


def fs_event_log(tmp_path: Path) -> EventLogHarness:
    paths = OrgPaths(tmp_path)
    clock = FakeClock()
    reader = FsEventReader(paths)
    return EventLogHarness(
        reader, FsEventFollowers(reader, clock), clock, StoreEventLogAuthor(DiskEventStore(paths.events_dir()), paths.events_dir())
    )


def memory_event_log(tmp_path: Path) -> EventLogHarness:
    clock = FakeClock()
    memory = MemoryEventLog(clock)
    return EventLogHarness(memory, memory, clock, StoreEventLogAuthor(memory, EVENTS_REL))


IMPLEMENTATIONS: Mapping[type, Sequence[Callable[[Path], object]]] = {
    EventReader: [fs_event_log, memory_event_log],
    EventFollower: [fs_event_log, memory_event_log],
    EventFollowers: [fs_event_log, memory_event_log],
}
