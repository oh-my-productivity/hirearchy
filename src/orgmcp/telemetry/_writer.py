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
    the pool's: numbering, opening and writing of all the files of a process happen one at a time."""

    def __init__(self, events_dir: str, stem: str, lock: threading.Lock) -> None:
        self._events = events_dir
        self._stem = stem
        self._lock = lock
        self._fd: int | None = None
        self._day = ""
        self._seq = 0
        self._retry_at = 0.0  # on the clock's monotonic scale: the directory is not tried before

    def append(self, record: JsonObject, day: str, clock: Clock, retry_after: float, on_fresh: Callable[[], None]) -> None:
        with self._lock:
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
