"""Runtime fields of ``health`` (ARCHITECTURE.md 3.25): one field per port that ``wire_health.py`` builds."""

from __future__ import annotations

from dataclasses import dataclass

from ..health import HealthAnalyzer, HealthRenderer, HealthThresholds

STEP: str | None = "C-health"  # the step that filled this part (see test_runtime_fields)
NOT_A_FIELD: dict[str, str] = {
    "HealthReport": "what a report can do (``flagged``, ``to_dict``): ``OrgHealth`` is data that ``HealthAnalyzer`` returns, not a port built once",
}


@dataclass(frozen=True)
class Fields:
    health_thresholds: HealthThresholds
    health_analyzer: HealthAnalyzer
    health_renderer: HealthRenderer
