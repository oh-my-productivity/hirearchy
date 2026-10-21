"""Runtime fields of ``review`` (ARCHITECTURE.md 3.26): one field per port that ``wire_review.py`` builds."""

from __future__ import annotations

from dataclasses import dataclass

from ..review import HealthReviewer

STEP: str | None = "C-review"  # the step that filled this part (see test_runtime_fields)
NOT_A_FIELD: dict[str, str] = {
    "ReviewReport": "what a review can show of itself (``render``): ``Review`` is data that ``HealthReviewer`` returns, not a port built once",
}


@dataclass(frozen=True)
class Fields:
    health_reviewer: HealthReviewer
