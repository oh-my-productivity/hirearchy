"""Runtime fields of ``observability`` (ARCHITECTURE.md 3.31): one field per port that ``wire_observability.py`` builds."""

from __future__ import annotations

from dataclasses import dataclass

from ..observability import (
    EventQueries,
    IntegrityChecks,
    MetricQueries,
    NowQueries,
    ObservabilityRenderer,
    ObservabilityText,
    TraceQueries,
)

STEP: str | None = "C-obs-2"  # the step that filled this part (see test_runtime_fields)
NOT_A_FIELD: dict[str, str] = {}  # port -> why it is not a runtime field (a value, a factory, ...)


@dataclass(frozen=True)
class Fields:
    event_queries: EventQueries
    trace_queries: TraceQueries
    metric_queries: MetricQueries
    now_queries: NowQueries
    integrity_checks: IntegrityChecks
    observability_renderer: ObservabilityRenderer
    observability_text: ObservabilityText  # the text of one view by its name: what the MCP tool and the command line ask
