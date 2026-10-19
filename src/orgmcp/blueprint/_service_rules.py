"""``ServiceBlueprintRules``: the ``services:`` list of a blueprint, and a first request in ``task``. Errors here block apply; they are written for the LLM."""
from __future__ import annotations
import math
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import cast
from ..kernel import NAME_RE, JsonObject, OrgError
from ..services import DESCRIPTION_MAX, ContractNormalizer
from ._budgeting import TIGHT
from ._protocols import BudgetPlanning, OrgContext, PathChecking, ServiceRules
from ._rules import delivers_directly, vague
from ._view import REQUEST_KEYS, SERVICE_KEYS, is_request, s, svc_criteria, svc_deliverable, unknown
from .api import Agent, Issue

class ServiceBlueprintRules(ServiceRules):

    def __init__(self, normalizer: ContractNormalizer, paths: PathChecking, budgets: BudgetPlanning) -> None:
        self._normalizer = normalizer
        self._paths = paths
        self._budgets = budgets

    def check(self, bp: Mapping[str, object], agents: Sequence[Agent], tops: Sequence[Agent], cap: int | None, est_total: int, org: OrgContext, roots: Sequence[Path], issues: list[Issue]) -> None:
        raise NotImplementedError('red: C-blueprint-1')

    def _request(self, task: JsonObject, by_name: Mapping[str, JsonObject], top: Agent | None, issues: list[Issue]) -> None:
        """``task: {service, inputs, title, note}``: a first request, checked like ``request()`` checks it."""
        raise NotImplementedError('red: C-blueprint-1')
