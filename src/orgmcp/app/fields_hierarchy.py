"""Runtime fields of ``hierarchy`` (ARCHITECTURE.md 3.19): one field per port that ``wire_hierarchy.py`` builds."""

from __future__ import annotations

from dataclasses import dataclass

from ..hierarchy import Hiring, Retirement

STEP: str | None = "B-hierarchy"  # the step that filled this part (see test_runtime_fields)
NOT_A_FIELD: dict[str, str] = {}  # port -> why it is not a runtime field (a value, a factory, ...)


@dataclass(frozen=True)
class Fields:
    hiring: Hiring
    retirement: Retirement
