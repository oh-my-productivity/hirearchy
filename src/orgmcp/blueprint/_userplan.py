"""``TextUserPlan``: the compact block the assistant shows to the user."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

from ._protocols import AccessWording, BudgetPlanning, PlanBasis, PlanWords, UserPlanning
from .api import Issue


class TextUserPlan(UserPlanning):
    def __init__(self, basis: PlanBasis, budgets: BudgetPlanning, access: AccessWording, words: PlanWords) -> None:
        self._basis = basis
        self._budgets = budgets
        self._access = access
        self._words = words

    def render(self, bp: Mapping[str, object], issues: Sequence[Issue] | None, allowed_roots: Sequence[str | Path] | None) -> str:
        raise NotImplementedError
