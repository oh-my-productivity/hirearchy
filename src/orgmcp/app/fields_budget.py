"""Runtime fields of ``budget`` (ARCHITECTURE.md 3.18): one field per port that ``wire_budget.py`` builds."""

from __future__ import annotations

from dataclasses import dataclass

from ..budget import AllocationPolicy, BudgetQuery, BudgetReclaimer

STEP: str | None = "B-budget"  # the step that filled this part (see test_runtime_fields)
NOT_A_FIELD: dict[str, str] = {}  # port -> why it is not a runtime field (a value, a factory, ...)


@dataclass(frozen=True)
class Fields:
    budget_query: BudgetQuery
    allocation_policy: AllocationPolicy
    budget_reclaimer: BudgetReclaimer
