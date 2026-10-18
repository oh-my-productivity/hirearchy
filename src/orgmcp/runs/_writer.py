"""Creating run logs and appending to them."""

from __future__ import annotations

from pathlib import Path
from typing import IO

from ..kernel import STAMP_FORMAT, Clock, OrgLayout
from ._format import log_note
from .api import RunLogSink, RunLogWriter


class FileRunLogSink(RunLogSink):
    """A log file opened for appending. It has a file descriptor (``fileno``), so the scheduler can hand it to the agent as its
    standard output."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._file: IO[str] = open(path, "a", encoding="utf-8")

    @property
    def path(self) -> Path:
        return self._path

    def write(self, text: str) -> None:
        self._file.write(text)

    def flush(self) -> None:
        self._file.flush()

    def close(self) -> None:
        self._file.close()

    def fileno(self) -> int:
        return self._file.fileno()


class FsRunLogWriter(RunLogWriter):
    def __init__(self, paths: OrgLayout, clock: Clock) -> None:
        self._paths = paths
        self._clock = clock

    def create(self, addr: str) -> Path:
        d = self._paths.agent_dir(addr) / "runs"
        d.mkdir(exist_ok=True)
        p = d / f"{self._clock.now():{STAMP_FORMAT}}.log"
        p.touch()
        return p

    def open_sink(self, path: Path) -> RunLogSink:
        return FileRunLogSink(path)

    def append_note(self, rel_path: str, text: str) -> None:
        try:
            log = self._paths.root / rel_path
            if log.is_file():
                with open(log, "a", encoding="utf-8") as f:
                    f.write(log_note(text))
        except OSError:
            pass
