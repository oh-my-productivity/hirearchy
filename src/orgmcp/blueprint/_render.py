"""``TextPlanRenderer``: the plan as text - the block for the user, the details, and what ``propose_org`` returns."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

from ._protocols import PlanBasis, PlanDetailing, UserPlanning
from .api import BlueprintLoader, Issue, PlanIdentity, PlanRenderer


class TextPlanRenderer(PlanRenderer):
    def __init__(
        self, loader: BlueprintLoader, basis: PlanBasis, details: PlanDetailing, user_plan: UserPlanning, identity: PlanIdentity,
    ) -> None:
        self._loader = loader
        self._basis = basis
        self._details = details
        self._user_plan = user_plan
        self._identity = identity

    def render_plan(self, bp: Mapping[str, object], issues: Sequence[Issue] | None = None, *, allowed_roots: Sequence[str | Path] | None = None) -> str:
        raise NotImplementedError

    def plan_for_user(self, bp: Mapping[str, object], issues: Sequence[Issue] | None = None, *, allowed_roots: Sequence[str | Path] | None = None) -> str:
        raise NotImplementedError

    def propose_text(self, bp: Mapping[str, object], *, target: str = "", allowed_roots: Sequence[str | Path] | None = None) -> str:
        raise NotImplementedError

    def propose(self, source: object, *, allowed_roots: Sequence[str | Path] | None = None) -> str:
        raise NotImplementedError
