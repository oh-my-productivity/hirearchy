"""Runtime fields of ``reflection`` (ARCHITECTURE.md 3.22): one field per port that ``wire_reflection.py`` builds."""

from __future__ import annotations

from dataclasses import dataclass

from ..reflection import CaseHistory, CaseRecords, DeliverableChecks, ReflectionDigest, ServicePromptSections, ServiceReports, ServiceSteps

STEP: str | None = "C-reflection"  # the step that filled this part (see test_runtime_fields)
NOT_A_FIELD: dict[str, str] = {
    "StatsReport": "what a set of counts can say of itself (``finished``, ``avg_runs``, ``line``): ``Stats`` is data that ``summarize`` returns, not a port built once",
}


@dataclass(frozen=True)
class Fields:
    case_history: CaseHistory
    reflection_digest: ReflectionDigest
    service_reports: ServiceReports
    service_prompt_sections: ServicePromptSections
    service_steps: ServiceSteps
    deliverable_checks: DeliverableChecks
    case_records: CaseRecords
