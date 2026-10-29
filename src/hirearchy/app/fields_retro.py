"""Runtime fields of ``retro`` (ARCHITECTURE.md 3.35): one field per port that ``wire_retro.py`` builds."""

from __future__ import annotations

from dataclasses import dataclass

from ..retro import RetroBriefs, RetroDue, RetroRecords

STEP: str | None = "C-retro"  # the step that filled this part (see test_runtime_fields)
NOT_A_FIELD: dict[str, str] = {
    "BriefSources": "the facts of one brief, read through the other packages' ports: private to ``retro``, built inside the provider of ``RetroBriefs``",
    "CharterHistory": "the committed charters as pairs: a consumer port of ``retro`` that ``app`` implements over ``OrgHistory`` (``_charter_history``), built inside the provider of ``RetroBriefs``",
    "ServiceRetirements": "the retired copies of services: a consumer port of ``retro`` that ``app`` implements over the layout (``_service_retirements``), built inside the provider of ``RetroBriefs``",
}


@dataclass(frozen=True)
class Fields:
    retro_records: RetroRecords
    retro_briefs: RetroBriefs
    retro_due: RetroDue
