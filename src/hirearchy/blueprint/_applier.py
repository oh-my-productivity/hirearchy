"""``HiringBlueprintApplier``: a checked blueprint becomes an organization."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

from ..snapshots import OrgSnapshotter
from ._protocols import BudgetPlanning, BuildUndoing, FirstTasking, PlanBasis, ServiceDefining, TeamBuilding
from ._shapes import Built
from ._view import s, task_of
from .api import BlueprintApplier, BlueprintError, Summary, errors


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
        """Create the agents (parents first, as root through each parent), define the services, and give the first task.

        The first task is a plain task, a first request for a service (``task.service``), or none (services only: they
        are ready to be requested). Refuses on any validation error or existing name, before writing anything. If a hire,
        a service definition or the delegation fails midway, everything created is retired again and the error is raised.
        """
        issues = self._basis.issues(bp, allowed_roots)
        errs = errors(issues)
        if errs:
            raise BlueprintError("blueprint has errors, nothing was created:\n" + "\n".join(f"- {i.path}: {i.message}" for i in errs))
        agents = self._basis.agents(bp, allowed_roots)
        task = task_of(bp) if isinstance(bp.get("task"), dict) else None
        est = self._budgets.estimate(agents)
        total = self._budgets.planned_total(bp, est["total"])
        split = self._budgets.budget_split(agents, total)
        top = agents[0]
        built = Built()
        msg = None
        try:
            self._team.build(agents, bp, split, built)
            self._services.define(bp, agents, built)
            msg = self._first_task.give(bp, top, total)
        except Exception:
            self._rollback.undo(built)
            raise
        what = (f"task {msg.id} -> {top.addr}" if msg is not None else "no task") + (f", services: {', '.join(built.defined)}" if built.defined else "")
        self._snapshots.commit(f"root: applied blueprint ({len(built.created)} agents), {what}")
        return Summary(built.created, msg.id if msg is not None else "", top.addr, msg.budget if msg is not None else 0,
                       [i for i in issues if i.level == "warning"], built.defined, s(task["service"]) if msg is not None and task and "service" in task else "")
