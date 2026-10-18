"""The open files of a process and what it could not write."""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol, runtime_checkable

from ..kernel import Clock, JsonObject


@runtime_checkable
class LineWriter(Protocol):
    """The open file of one process for one organization."""

    def append(self, record: JsonObject, day: str, clock: Clock, retry_after: float, on_fresh: Callable[[], None]) -> None:
        """Number the record, open the day's file if needed, write the line. Raises ``OSError`` when it cannot."""
        ...

    def close(self) -> None:
        """Close the file (it is opened again by the next ``append``)."""
        ...


@runtime_checkable
class LineWriters(Protocol):
    def writer(self, root: str, proc: str, pid: int) -> LineWriter:
        """The writer of this process for the organization at ``root`` (the same object every time)."""
        ...


@runtime_checkable
class DropLog(Protocol):
    def drop(self, why: BaseException | str) -> None:
        """Count an event that could not be written; the first one per process is reported on stderr."""
        ...

    def dropped(self) -> int:
        """How many were counted."""
        ...


class EventWriterPool(LineWriters, DropLog):
    def __init__(self, clock: Clock) -> None:
        raise NotImplementedError("red: A-telemetry")

    def writer(self, root: str, proc: str, pid: int) -> LineWriter:
        raise NotImplementedError("red: A-telemetry")

    def drop(self, why: BaseException | str) -> None:
        raise NotImplementedError("red: A-telemetry")

    def dropped(self) -> int:
        raise NotImplementedError("red: A-telemetry")

    def reset(self) -> None:
        """Close every file and forget the counters (tests; also what a fork child would need)."""
        raise NotImplementedError("red: A-telemetry")
