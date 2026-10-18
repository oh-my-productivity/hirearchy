"""The open files of a process and the count of what it could not write."""

from __future__ import annotations

import os
import sys
import threading

from ..eventlog import EVENTS_REL
from ..kernel import Clock
from ._ports import DropLog, LineWriter, LineWriters
from ._writer import FileLineWriter


class EventWriterPool(LineWriters, DropLog):
    """One writer per (organization root, process name, pid), whatever number of sinks and runtimes write through it: that is what keeps
    one file per process and day. Created once per process by the composition root."""

    def __init__(self, clock: Clock) -> None:
        self._clock = clock
        self._lock = threading.Lock()
        self._writers: dict[tuple[str, str, int], LineWriter] = {}
        self._dropped = 0
        self._warned = False

    def writer(self, root: str, proc: str, pid: int) -> LineWriter:
        key = (root, proc, pid)
        found = self._writers.get(key)
        if found is None:
            with self._lock:
                stem = f"{proc}-{pid}-{int(self._clock.time() * 1000)}"
                found = self._writers.setdefault(key, FileLineWriter(os.path.join(root, str(EVENTS_REL)), stem, self._lock))
        return found

    def drop(self, why: BaseException | str) -> None:
        self._dropped += 1
        if not self._warned:
            self._warned = True
            try:
                print(f"orgmcp: the event log is unavailable ({why}); events are being dropped "
                      "(the operation itself is not affected)", file=sys.stderr, flush=True)
            except Exception:  # noqa: BLE001 - even a closed stderr must not matter
                pass

    def dropped(self) -> int:
        return self._dropped

    def reset(self) -> None:
        """Close every file and forget the counters (tests; also what a fork child would need)."""
        with self._lock:
            for writer in self._writers.values():
                writer.close()
            self._writers.clear()
        self._dropped, self._warned = 0, False
