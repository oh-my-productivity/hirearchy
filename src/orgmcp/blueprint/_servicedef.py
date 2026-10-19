"""``PlaybookServiceDefiner``: the services of a blueprint, defined for its top-level agent."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from ..services import ContractNormalizer, ServiceCommands
from ._protocols import BudgetPlanning, PlaybookWriting, ServiceDefining
from ._shapes import Built
from .api import Agent


class PlaybookServiceDefiner(ServiceDefining):
    def __init__(
        self, commands: ServiceCommands, normalizer: ContractNormalizer, playbooks: PlaybookWriting, budgets: BudgetPlanning,
    ) -> None:
        self._commands = commands
        self._normalizer = normalizer
        self._playbooks = playbooks
        self._budgets = budgets

    def define(self, bp: Mapping[str, object], agents: Sequence[Agent], built: Built) -> None:
        raise NotImplementedError
