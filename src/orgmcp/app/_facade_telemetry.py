"""Event emission (telemetry).

Moved verbatim from ``core.Org`` in step M2 (ARCHITECTURE.md 5.3 and 6.4); a later step replaces the bodies by calls
to the interfaces of the package named above."""

from __future__ import annotations

from .. import telemetry


class TelemetryMixin:
    """Event emission (telemetry)."""

    def emit(self, kind: str, **fields) -> None:
        """Append an event to the org's event log (see :mod:`orgmcp.telemetry`). Never raises."""
        telemetry.emit(self.root, kind, **fields)
