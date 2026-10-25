"""The open event file of one process for one organization."""

from __future__ import annotations

import os
import threading
from collections.abc import Callable

from ..kernel import Clock, JsonObject
from ._encode import encode_line
from ._ports import LineWriter


class FileLineWriter(LineWriter):
    """``<events dir>/<day>/<stem>.jsonl``, opened once per day with ``O_APPEND`` and kept open: a line is one ``write()``. ``lock`` is
    the pool's, re-entrant: numbering, opening and writing of all the files of a process happen one at a time, and a line a signal handler
    appends while another is written is queued and follows it."""

    def __init__(self, events_dir: str, stem: str, lock: threading.RLock) -> None:
        self._events = events_dir
        self._stem = stem
        self._lock = lock
        self._fd: int | None = None
        self._day = ""
        self._seq = 0
        self._retry_at = 0.0  # on the clock's monotonic scale: the directory is not tried before
        self._queue: list[tuple[JsonObject, str, Clock, float, Callable[[], None]]] = []
        self._writing = False

    def append(self, record: JsonObject, day: str, clock: Clock, retry_after: float, on_fresh: Callable[[], None]) -> None:
        with self._lock:  # re-entrant: a signal handler of the thread that holds it gets in
            self._queue.append((record, day, clock, retry_after, on_fresh))  # one C call: a handler cannot split it
            if self._writing:
                return  # a handler that interrupted a line of this writer: that line's loop writes this one right after it
            while True:
                try:
                    item = self._queue.pop(0)
                except IndexError:
                    return  # nothing left (a handler that came in between may have written the rest itself)
                self._writing = True
                try:
                    self._write(*item)
                finally:
                    self._writing = False

    def _write(self, record: JsonObject, day: str, clock: Clock, retry_after: float, on_fresh: Callable[[], None]) -> None:
        self._seq += 1
        record["seq"] = self._seq
        fd = self._fd
        if fd is None or self._day != day:
            if clock.monotonic() < self._retry_at:
                raise OSError("events directory not writable (retrying later)")
            try:
                fd = self._open(day, on_fresh)
            except OSError:
                self.close()
                self._retry_at = clock.monotonic() + retry_after
                raise
            record["seq"] = self._seq = 1
        data = encode_line(record)
        try:
            os.write(fd, data)
        except OSError:
            self.close()
            self._retry_at = clock.monotonic() + retry_after
            raise

    def close(self) -> None:
        if self._fd is not None:
            try:
                os.close(self._fd)
            except OSError:
                pass
        self._fd, self._day = None, ""

    def _open(self, day: str, on_fresh: Callable[[], None]) -> int:
        fresh = not os.path.isdir(self._events)
        folder = os.path.join(self._events, day)
        os.makedirs(folder, exist_ok=True)
        if fresh:
            on_fresh()
        fd = os.open(os.path.join(folder, self._stem + ".jsonl"), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
        self.close()
        self._fd, self._day, self._seq = fd, day, 0
        return fd
