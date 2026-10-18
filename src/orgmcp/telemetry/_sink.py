"""The sink of an organization: stamps an event with the envelope and appends it to the process's file for the day."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from ..kernel import Clock, Environment, EventSink, OrgLayout
from ..settings import EventSwitch
from ..snapshots import IgnoreList
from ._pool import DropLog, LineWriters
from .api import EventSinks, ProcessLabel

RETRY_AFTER = 5.0  # seconds before an unwritable events directory is tried again


class FsEventSink(EventSink):
    def __init__(
        self,
        layout: OrgLayout,
        writers: LineWriters,
        drops: DropLog,
        switch: EventSwitch,
        label: ProcessLabel,
        clock: Clock,
        environment: Environment,
        ignore: IgnoreList,
        retry_after: float = RETRY_AFTER,
    ) -> None:
        raise NotImplementedError("red: A-telemetry")

    def emit(
        self,
        kind: str,
        /,
        *,
        actor: str | None = None,
        run: str | None = None,
        trace: str | None = None,
        proc: str | None = None,
        **fields: object,
    ) -> None:
        raise NotImplementedError("red: A-telemetry")


class FsEventSinks(EventSinks):
    def __init__(self, drops: DropLog, factory: Callable[[Path], EventSink]) -> None:
        raise NotImplementedError("red: A-telemetry")

    def for_root(self, root: Path) -> EventSink:
        raise NotImplementedError("red: A-telemetry")

    def dropped(self) -> int:
        raise NotImplementedError("red: A-telemetry")

    def reset(self) -> None:
        """Forget the sinks (and what they know of ORG.md)."""
        raise NotImplementedError("red: A-telemetry")
