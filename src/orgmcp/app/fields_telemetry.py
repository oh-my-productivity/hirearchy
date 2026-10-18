"""Runtime fields of ``telemetry`` (ARCHITECTURE.md 3.7): one field per port that ``wire_telemetry.py`` builds."""

from __future__ import annotations

from dataclasses import dataclass

from ..telemetry import ArgumentSummarizer, EventRetention, EventSinks, ProcessLabel, TraceScope

STEP: str | None = "A-telemetry"  # the step that filled this part (see test_runtime_fields)
# (the fields ``events: EventSink`` and ``trace_tap: TraceTap`` are the kernel's ports: they are in fields_kernel.py, built by wire_telemetry.py)
NOT_A_FIELD: dict[str, str] = {}  # port -> why it is not a runtime field (a value, a factory, ...)


@dataclass(frozen=True)
class Fields:
    event_sinks: EventSinks
    process_label: ProcessLabel
    event_retention: EventRetention
    argument_summarizer: ArgumentSummarizer
    trace_scope: TraceScope
