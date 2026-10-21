"""The public surface of ``runs``: the durable record of agent runs.

A run leaves a log (``<agent>/runs/<UTC stamp>.log``); the existence of the file is what consumes one run of budget. The scheduler
writes it, and budget, health, observe and the dashboard read it. A run in flight is also an entry of the registry
(``.runtime/running.json``), which is how a new scheduler finds the runs of a dead one.

The text format of a log is defined once (``_format``) and used by both sides: the pure ``log_*`` functions write its lines, the readers
parse them. Header: ``# run of``, ``# senders:``, ``# cwd``, ``# cmd``, ``# ---- prompt ----``, ``# ---- output ----``. Closing line:
``# exit N after Ns``, ``# killed after Ns timeout``, ``# killed: ...``, ``# failed to start: ...`` or ``# interrupted by scheduler
shutdown``. Nothing here knows about mail, budget or policy.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import NamedTuple, Protocol, runtime_checkable

from ..kernel import JsonObject
from ._format import (
    log_exit,
    log_failed_start,
    log_header,
    log_interrupted,
    log_invocation,
    log_note,
    log_prompt,
    log_retired,
    log_timeout,
    run_id_of,
    run_record,
)

__all__ = [
    "RunLogFile",
    "RunLogReader",
    "RunLogSink",
    "RunLogWriter",
    "RunOutcomes",
    "RunRegistry",
    "RunWindow",
    "log_exit",
    "log_failed_start",
    "log_header",
    "log_interrupted",
    "log_invocation",
    "log_note",
    "log_prompt",
    "log_retired",
    "log_timeout",
    "run_id_of",
    "run_record",
]


class RunWindow(NamedTuple):
    """When a run was active: it started at the time in the name of its log and ended when the log was last written."""

    start: datetime
    end: datetime


@dataclass(frozen=True)
class RunOutcomes:
    """What the logs of one agent say about how its runs ended and what woke them, keyed by the start of each run."""

    failed: frozenset[datetime]  # crashed (non-zero exit), failed to start, timed out or interrupted
    runtime_only: frozenset[datetime]  # the whole batch came from the runtime (stall reminders, reviews, refunds)


@dataclass(frozen=True)
class RunLogFile:
    """One run log: ``stem`` is the file name without ``.log`` (the run id is ``<agent>@<stem>``), ``start`` the time in it (None for
    a log whose name is not a timestamp)."""

    stem: str
    path: Path
    start: datetime | None


@runtime_checkable
class RunLogSink(Protocol):
    @property
    def path(self) -> Path:
        """The log this sink appends to."""
        ...

    def write(self, text: str) -> None:
        """Append (raises ``ValueError`` once closed, like a file)."""
        ...

    def flush(self) -> None:
        """Make what was written visible to readers of the log."""
        ...

    def close(self) -> None:
        """Flush and release; closing twice is harmless."""
        ...


@runtime_checkable
class RunLogWriter(Protocol):
    def create(self, addr: str) -> Path:
        """Create ``<addr>/runs/<UTC stamp>.log`` (empty): its existence consumes one run of budget. The agent's directory must exist."""
        ...

    def open_sink(self, path: Path) -> RunLogSink:
        """Open a log for appending (UTF-8)."""
        ...

    def append_note(self, rel_path: str, text: str) -> None:
        """Append ``# <text>`` (on a line of its own) to an old log given by its path below the organization; silent when there is no
        such file or it cannot be written."""
        ...


@runtime_checkable
class RunLogReader(Protocol):
    def count(self, addr: str) -> int:
        """The visible ``*.log`` files of the agent (hidden ones are ignored): the runs it has used."""
        ...

    def files(self, addr: str) -> list[RunLogFile]:
        """The visible logs, oldest first (by name)."""
        ...

    def windows(self, addr: str) -> list[RunWindow]:
        """One window per log whose name is a timestamp: start from the name, end from the mtime (never before the start)."""
        ...

    def outcomes(self, addr: str) -> RunOutcomes:
        """Failed runs and runs whose whole batch came from the runtime; only the first 4 KB and the last 2 KB of a log are read."""
        ...

    def last_end(self, addr: str) -> float:
        """The latest mtime (epoch seconds) of any ``*.log`` of the agent; 0.0 without any."""
        ...

    def facts(self, path: Path) -> JsonObject:
        """What the closing lines in the last 4 KB say: ``exit_code`` and ``seconds``, ``timed_out``, ``killed``, ``failed_start``;
        ``{}`` when the log cannot be read."""
        ...

    def tail(self, path: Path, max_bytes: int, max_lines: int) -> tuple[str, bool]:
        """The end of a log and whether anything was cut. At most ``max_bytes`` are read from the end (the partial first line is then
        dropped), then at most ``max_lines`` lines are kept (a final newline is not a line). Raises ``OSError`` when unreadable."""
        ...

    def head(self, path: Path, max_bytes: int) -> str:
        """The first ``max_bytes`` bytes of a log as text (undecodable bytes replaced). Raises ``OSError`` when unreadable."""
        ...


@runtime_checkable
class RunRegistry(Protocol):
    def all(self) -> dict[str, JsonObject]:
        """Agent -> the record of its run in flight (``run_record``); entries that are not objects are dropped."""
        ...

    def record(self, addr: str, record: JsonObject) -> None:
        """Set the record of the agent's run, keeping the others."""
        ...

    def forget(self, *addrs: str) -> None:
        """Remove the record of the first of ``addrs`` that has one (the scheduler has always done so); nothing is written when none has."""
        ...

    def replace(self, records: Mapping[str, JsonObject]) -> None:
        """Replace all records."""
        ...
