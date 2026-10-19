"""``BudgetPlanner``: how many runs a blueprint needs, and how they are split down the tree (package-private).

The model behind the budget check of ``validate`` and the budget split of the plan and of the charters."""
from __future__ import annotations
import math
from collections.abc import Mapping, Sequence
from ._protocols import BudgetPlanning
from ._shapes import AgentRuns, Estimate, Split
from ._view import cap_of, needs_of, s, services_of, task_of
from .api import Agent
SLACK = 1.25
TIGHT = 1.1
REWORK_RUNS = {'manager': 2, 'author': 1, 'verifier': 1}
KINDS = ('manager', 'author', 'verifier')

class BudgetPlanner(BudgetPlanning):

    def estimate(self, agents: Sequence[Agent]) -> Estimate:
        """Runs one pass plus one rework cycle needs. The model behind the budget check and the budget split.

        Per agent, one *pass* of the work and one *rework* cycle (one review finds problems, the author fixes them):

        * worker (author or verifier): ``pass = template.base_runs * scale`` (researcher 3, writer 2, engineer 4,
          fact-checker 2, reviewer 1, tester 2, code-reviewer 2, analyst 4, data-checker 2; a custom charter counts 2). ``rework = 1``
          (an author fixes its file; a verifier re-checks).
        * manager: ``pass = 1 (plan and delegate) + 1 per direct report (process its result) + 1 (final check and report)``;
          ``rework = 2`` (send the findings back, process the revised result).

        ``total`` is the sum over all agents of pass + rework: the minimum budget for a pipeline with one review and one rework cycle
        (``budget_split`` hands each worker its pass and its rework/re-check run together).
        The planned budget is ``ceil(total * 1.25)`` unless the task names one; below ``total * 1.1`` is flagged as having no slack.
        """
        raise NotImplementedError('red: C-blueprint-1')

    def planned_total(self, bp: Mapping[str, object], est_total: int) -> int:
        raise NotImplementedError('red: C-blueprint-1')

    def budget_split(self, agents: Sequence[Agent], total: int) -> dict[str, Split]:
        """addr -> {grant, keeps}: what the parent hands down at first, and what the agent keeps for itself.

        Every child is granted its whole subtree, pass AND rework: an author keeps one rework run and a verifier one
        re-check run on top of its pass (the writer of the research example gets 3, not 2, so an empty first run cannot
        leave it unable to apply the checker's changes). Unspent runs come back with the child's final report anyway.
        The agent keeps the rest: its own pass and rework runs plus the reserve. The top agent receives ``total``.
        """
        raise NotImplementedError('red: C-blueprint-1')

    def service_budget(self, sv: Mapping[str, object], est_total: int, cap: int | None) -> int:
        """Runs handed down with each request of service ``sv``: its own ``budget``, else the estimate plus slack within the cap."""
        raise NotImplementedError('red: C-blueprint-1')

    def service_budgets(self, bp: Mapping[str, object], agents: Sequence[Agent]) -> dict[str, int]:
        """The runs per request of every service of the blueprint, by name."""
        raise NotImplementedError('red: C-blueprint-1')
