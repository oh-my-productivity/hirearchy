"""Runtime fields of ``daemon`` (ARCHITECTURE.md 3.29): one field per port that ``wire_daemon.py`` builds."""

from __future__ import annotations

from dataclasses import dataclass

from ..daemon import ExitMarker, SchedulerCommand, SchedulerControl, SchedulerLock, SchedulerStatus

STEP: str | None = "C-daemon"  # the step that filled this part (see test_runtime_fields)
NOT_A_FIELD: dict[str, str] = {}  # port -> why it is not a runtime field (a value, a factory, ...)


@dataclass(frozen=True)
class Fields:
    scheduler_status: SchedulerStatus
    scheduler_control: SchedulerControl
    scheduler_lock: SchedulerLock
    exit_marker: ExitMarker
    scheduler_command: SchedulerCommand
