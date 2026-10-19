"""Run budget: held, handed down, taken back (budget).

The bodies call the ports of ``self.runtime`` (step B-budget; ARCHITECTURE.md 5.3 and 6.4)."""

from __future__ import annotations

from ..kernel import Message
from .runtime import OrgRuntime


class BudgetMixin:
    """Run budget: held, handed down, taken back (budget)."""

    runtime: OrgRuntime

    def budget(self, addr: str) -> int | None:
        """Runs this agent may still use. None = unlimited (root)."""
        return self.runtime.budget_query.budget(addr)

    def delegable(self, addr: str) -> tuple[int, int, int]:
        """(budget, outstanding delegations, the most ``addr`` can hand down with one more delegation).

        The most is ``budget - outstanding - 1`` (one run kept per outstanding delegation to process its result, one
        for the new delegation's own result), never below 0.
        """
        return self.runtime.budget_query.delegable(addr)

    def grant_hint(self, addr: str) -> str:
        """What a direct report can do with its budget now (shown to whoever just granted it runs); "" if it cannot hire."""
        return self.runtime.budget_query.grant_hint(addr)

    def _check_allocation(self, actor: str, amount: int, new_delegation: bool) -> None:
        self.runtime.allocation_policy.check_allocation(actor, amount, new_delegation)

    def _default_budget(self, actor: str) -> int:
        """Runs a delegation gets when the caller names none: what the actor can afford, capped at default_budget.

        min(default_budget, remaining - reserve), where the reserve keeps one run per outstanding delegation plus
        one for the result of this new one. Root has no limit.
        """
        return self.runtime.allocation_policy.default_budget(actor)

    def _budget_to_return(self, actor: str, task: Message, status: str) -> int:
        """Runs that travel up with the final result of ``task``: everything the reporter has left, or 0.

        Only a final result (``done``/``failed``) returns budget, and only when nothing else needs the reporter's
        runs after it: no other open task, no other task reported ``blocked`` (it may be re-reported), no outstanding
        delegation (their results need the reserve) and no mail waiting for a run. It goes to the assigner, and only
        when that is the reporter's parent (the one route budget may travel up). The amount is read from the files
        at the moment of the report and the transfer is the result message itself, so it is counted exactly once: a
        redelivered run finds the task already final (a second ``report`` is refused) and nothing left to return.
        """
        return self.runtime.allocation_policy.budget_to_return(actor, task, status)

    def reclaim(self, actor: str, report: str, budget: int | None = None) -> Message:
        """Pull unspent budget back from an idle DIRECT report (short name or full address). Default: all of it.

        Budget is derived from messages, so this is one: a note from the report to ``actor`` carrying the budget,
        written by the runtime on the report's behalf (it lands in the report's ``sent/``, which charges it, and in the
        actor's inbox, which credits it). Nothing is minted or destroyed. It does not wake the actor, who is running
        now. The report receives nothing, so it is not woken either. Root may reclaim from its direct reports (the
        runs go back to root, who has no limit). Never from deeper down: a manager reclaims from its own reports, and
        those reclaim from theirs.

        Refused unless the report is idle: it has no open task, nothing delegated and still outstanding, no run in
        flight and no unread mail that would wake it; its budget has to be above zero.
        """
        return self.runtime.budget_reclaimer.reclaim(actor, report, budget)
