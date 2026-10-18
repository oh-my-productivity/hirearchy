"""The process defaults that the legacy functions of ``orgmcp.telemetry`` delegate to, installed by the composition root.

The legacy callers (the MCP server, the CLI, the scheduler, the facade) have no runtime at hand, and a feature package may not import
the composition root: ``orgmcp.app`` installs the defaults of the process with ``install`` when it is loaded (as it installs
``Message.load`` into the kernel). The only state here is that installed reference. Deleted with the legacy functions (E3).
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from ..kernel import EventSink, TraceTap
from ..snapshots import IgnoreList
from ._ports import DropLog
from .api import EventRetention, ProcessLabel, TraceScope


class TraceChannel(TraceScope, TraceTap, Protocol):
    """The scope that collects and the tap that is noted into: one object in the process."""


class ProcessDefaults(Protocol):
    """What the legacy functions need from the process they run in; ``orgmcp.app`` provides it."""

    def sink(self, root: Path) -> EventSink:
        """The sink of the organization at ``root`` (the same one every time)."""
        ...

    def retention(self, root: Path) -> EventRetention:
        """The retention of the event log of the organization at ``root``."""
        ...

    def ignore_list(self, root: Path) -> IgnoreList:
        """The ``.gitignore`` of the organization at ``root``."""
        ...

    def label(self) -> ProcessLabel:
        """The name of this process."""
        ...

    def channel(self) -> TraceChannel:
        """The traces of the tool call of this thread."""
        ...

    def drops(self) -> DropLog:
        """The count of the events this process could not write."""
        ...

    def reset(self) -> None:
        """Forget open files, counters, the process name and the sinks (tests)."""
        ...


_installed: ProcessDefaults | None = None


def install(process_defaults: ProcessDefaults) -> None:
    """Called by ``orgmcp.app`` once, when it is loaded: the process defaults the legacy functions delegate to."""
    global _installed
    _installed = process_defaults


def defaults() -> ProcessDefaults:
    """The installed defaults; ``RuntimeError`` when ``orgmcp.app`` has not been loaded."""
    if _installed is None:
        raise RuntimeError("orgmcp.app is not loaded: the telemetry defaults of this process are not installed")
    return _installed


def count_dropped(exc: BaseException) -> None:
    """Count an event lost because the sink could not even be looked up; never raises."""
    try:
        defaults().drops().drop(f"{type(exc).__name__}: {exc}")
    except Exception:  # noqa: BLE001
        pass
