"""Event emission (telemetry).

``emit`` goes through the event sink of the runtime (ARCHITECTURE.md 5.3 and 6.4). Importing this module also hands the legacy functions
of ``orgmcp.telemetry`` the defaults of the process (``wire_telemetry.ProcessTelemetry``): the callers that still import them have no
runtime at hand, and a feature package may not import the composition root."""

from __future__ import annotations

from typing import Any

from ..telemetry import _process
from . import wire_telemetry
from .runtime import OrgRuntime

_process.install(wire_telemetry.ProcessTelemetry())


class TelemetryMixin:
    """Event emission (telemetry)."""

    runtime: OrgRuntime

    def emit(self, kind: str, **fields: Any) -> None:  # Any: the envelope fields (actor, run, trace, proc) and the free ones, as before
        """Append an event to the org's event log (see :mod:`orgmcp.telemetry`). Never raises."""
        return self.runtime.events.emit(kind, **fields)
