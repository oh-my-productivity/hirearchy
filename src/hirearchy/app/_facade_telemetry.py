"""Event emission (telemetry).

``emit`` goes through the event sink of the runtime (ARCHITECTURE.md 5.3 and 6.4)."""

from __future__ import annotations

from typing import Any

from .runtime import OrgRuntime


class TelemetryMixin:
    """Event emission (telemetry)."""

    runtime: OrgRuntime

    def emit(self, kind: str, **fields: Any) -> None:  # Any: the envelope fields (actor, run, trace, proc) and the free ones, as before
        """Append an event to the org's event log (see :mod:`hirearchy.telemetry`). Never raises."""
        return self.runtime.events.emit(kind, **fields)
