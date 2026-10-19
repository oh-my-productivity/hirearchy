"""``StepsPlaybookWriter``: playbook v1 of a service that the blueprint gives none."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from ._protocols import BudgetPlanning, PlaybookWriting
from .api import Agent


class StepsPlaybookWriter(PlaybookWriting):
    def __init__(self, budgets: BudgetPlanning) -> None:
        self._budgets = budgets

    def default_playbook(self, owner: Agent, agents: Sequence[Agent], service: Mapping[str, object], budget: int) -> str:
        raise NotImplementedError
