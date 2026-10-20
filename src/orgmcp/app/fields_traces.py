"""Runtime fields of ``traces`` (ARCHITECTURE.md 3.14): one field per port that ``wire_traces.py`` builds."""

from __future__ import annotations

from dataclasses import dataclass

from ..traces import TraceLookup, TraceStamper

STEP: str | None = "B-traces"  # the step that filled this part (see test_runtime_fields)
NOT_A_FIELD: dict[str, str] = {}  # port -> why it is not a runtime field (a value, a factory, ...)


@dataclass(frozen=True)
class Fields:
    trace_lookup: TraceLookup
    trace_stamper: TraceStamper
