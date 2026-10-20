"""The public surface of ``telemetry``: what the runtime does, appended to the event log as structured events.

The emitting port itself, ``EventSink``, and the tap that tool calls listen on, ``TraceTap``, are in the kernel (every package emits);
this package provides their real implementations and the roles around them: the sinks of the organizations of a process
(``EventSinks``), the name of the process (``ProcessLabel``), the deletion of expired days (``EventRetention``), the safe summary of a
tool call's arguments (``ArgumentSummarizer``) and the collection of the traces a call delivered (``TraceScope``). The format of the
files is defined by ``eventlog``; this package is their only writer (ARCHITECTURE.md 2.3). Emission is cheap and never raises.
"""

from __future__ import annotations

from collections.abc import Mapping
from contextlib import AbstractContextManager
from datetime import datetime
from pathlib import Path
from typing import Protocol, runtime_checkable

from ..kernel import EventSink, JsonObject

__all__ = ["ArgumentSummarizer", "EventRetention", "EventSinks", "ProcessLabel", "TraceScope"]


@runtime_checkable
class EventSinks(Protocol):
    def for_root(self, root: Path) -> EventSink:
        """The sink of the organization at ``root`` (the same object every time): what a caller without a runtime emits through."""
        ...

    def dropped(self) -> int:
        """How many events this process could not write."""
        ...


@runtime_checkable
class ProcessLabel(Protocol):
    def get(self) -> str:
        """``scheduler``, ``mcp`` or ``cli``: the ``proc`` of the events of this process, and the start of its file names."""
        ...

    def set(self, name: str) -> None:
        """Name this process; any name other than those three means ``cli``."""
        ...


@runtime_checkable
class EventRetention(Protocol):
    def prune(self, keep_days: int, today: datetime | None = None) -> list[str]:
        """Delete the day directories older than ``keep_days`` days (at least 1), counted from ``today`` (default: now).
        Returns the removed names, oldest first. Never raises."""
        ...


@runtime_checkable
class ArgumentSummarizer(Protocol):
    def summarize(self, arguments: Mapping[str, object]) -> JsonObject:
        """What a tool call put in its arguments, safe to log: ids, names, lengths; never a body."""
        ...


@runtime_checkable
class TraceScope(Protocol):
    def collect(self) -> AbstractContextManager[list[str | None]]:
        """Collect, in this thread, the traces of the messages delivered while the block runs (nested blocks do not mix)."""
        ...
