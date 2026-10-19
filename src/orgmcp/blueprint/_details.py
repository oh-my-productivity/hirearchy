"""``TextPlanDetails``: the full plan, for the assistant (the user is shown the block of ``_userplan``)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

from ._protocols import AccessReport, BudgetPlanning, PlanBasis, PlanDetailing, PlanWords, PlaybookWriting
from .api import Issue


class TextPlanDetails(PlanDetailing):
    def __init__(
        self, basis: PlanBasis, budgets: BudgetPlanning, access: AccessReport, playbooks: PlaybookWriting, words: PlanWords,
    ) -> None:
        self._basis = basis
        self._budgets = budgets
        self._access = access
        self._playbooks = playbooks
        self._words = words

    def render(self, bp: Mapping[str, object], issues: Sequence[Issue] | None, allowed_roots: Sequence[str | Path] | None) -> str:
        raise NotImplementedError
