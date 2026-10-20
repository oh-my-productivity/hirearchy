"""The event log as the tests of ``telemetry`` (and of whoever else writes events) have always called it: ``reset()``, ``set_process(name)``, ``dropped()``,
``emit(root, kind, ...)``, ``prune(root, keep_days, today)``, over the ports of the composition root.

The resources of the process (the open event files, the drop counter, the name of the process) are ``wiring.process_resources()``; the sink and the retention
of an organization are the ports of its runtime (``wiring.open_runtime(root)``).
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from orgmcp.app import wiring
from orgmcp.eventlog import LINE_MAX as LINE_MAX
from orgmcp.kernel import clip as clip


def reset() -> None:
    """Forget open files and counters (a new process)."""
    wiring.process_resources().reset()


def set_process(name: str) -> None:
    wiring.process_resources().process_label.set(name)


def dropped() -> int:
    return wiring.process_resources().event_pool.dropped()


def emit(root: str | Path, kind: str, /, **fields: object) -> None:
    wiring.open_runtime(Path(root)).events.emit(kind, **fields)


def prune(root: str | Path, keep_days: int, today: datetime | None = None) -> list[str]:
    return wiring.open_runtime(Path(root)).event_retention.prune(keep_days, today)
