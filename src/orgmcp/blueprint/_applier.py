"""``HiringBlueprintApplier``: a checked blueprint becomes an organization."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

from ..snapshots import OrgSnapshotter
from ._protocols import BuildUndoing, BudgetPlanning, FirstTasking, PlanBasis, ServiceDefining, TeamBuilding
from .api import BlueprintApplier, Summary


class HiringBlueprintApplier(BlueprintApplier):
    def __init__(
        self, basis: PlanBasis, budgets: BudgetPlanning, team: TeamBuilding, services: ServiceDefining, first_task: FirstTasking,
        rollback: BuildUndoing, snapshots: OrgSnapshotter,
    ) -> None:
        self._basis = basis
        self._budgets = budgets
        self._team = team
        self._services = services
        self._first_task = first_task
        self._rollback = rollback
        self._snapshots = snapshots

    def apply(self, bp: Mapping[str, object], *, allowed_roots: Sequence[str | Path] | None = None) -> Summary:
        raise NotImplementedError
