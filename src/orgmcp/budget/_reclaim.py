"""Taking unspent runs back as a note (moved from ``Org.reclaim``)."""

from __future__ import annotations

from ..agents import AgentDirectory
from ..delivery import MessageDelivery
from ..kernel import ROOT, Message, OrgError, child_addr, norm, parent
from ..mail import MailboxReader, TaskQuery
from .api import BudgetQuery, BudgetReclaimer


class NoteBudgetReclaimer(BudgetReclaimer):
    """Writes, on an idle report's behalf, the note that moves its unspent runs to its manager.

    Budget is derived from messages, so reclaiming is one: a note from the report to ``actor`` carrying the budget (it lands in the report's
    ``sent/``, which charges it, and in the actor's inbox, which credits it). Nothing is minted or destroyed. It does not wake the actor, who is
    running now. The report receives nothing, so it is not woken either. Root may reclaim from its direct reports (the runs go back to root, who
    has no limit). Never from deeper down: a manager reclaims from its own reports, and those reclaim from theirs.

    Refused unless the report is idle: it has no open task, nothing delegated and still outstanding, no run in flight and no unread mail that
    would wake it; its budget has to be above zero.
    """

    def __init__(
        self, delivery: MessageDelivery, budget: BudgetQuery, tasks: TaskQuery, mail: MailboxReader, agents: AgentDirectory,
    ) -> None:
        self._delivery = delivery
        self._budget = budget
        self._tasks = tasks
        self._mail = mail
        self._agents = agents

    def reclaim(self, actor: str, report: str, budget: int | None = None) -> Message:
        actor = self._agents.require(actor)
        short = norm(report)
        addr = short if "/" in short else child_addr(actor, short)
        if addr == ROOT or not self._agents.exists(addr) or parent(addr) != actor:
            reports = ", ".join(self._agents.children(actor)) or "none"
            raise OrgError(
                f"you can only reclaim budget from your direct reports (yours: {reports}); {report!r} is not one. "
                "Ask a manager to reclaim from its own team."
            )
        if budget is not None and int(budget) < 1:
            raise OrgError("budget must be at least 1 run (omit it to reclaim everything the report has left)")
        why = [
            text for text in (
                "it is running now" if self._mail.has_inflight(addr) else "",
                f"it has {len(self._tasks.open_tasks(addr))} open task(s)" if self._tasks.open_tasks(addr) else "",
                f"it has {len(self._tasks.outstanding(addr))} delegation(s) still outstanding" if self._tasks.outstanding(addr) else "",
                f"it has {self._mail.unread(addr)} unread message(s) that will wake it" if self._mail.unread(addr) else "",
            ) if text
        ]
        if why:
            raise OrgError(
                f"{addr} is busy ({'; '.join(why)}), so its runs are not stranded. Wait until it has reported, or "
                "leave its budget with it."
            )
        available = max(0, self._budget.budget(addr) or 0)
        if available < 1:
            raise OrgError(f"{addr} has no unspent budget to reclaim ({self._budget.budget(addr)} run(s) left)")
        amount = available if budget is None else int(budget)
        if amount > available:
            raise OrgError(f"{addr} has only {available} unspent run(s); you asked for {amount}")
        return self._delivery.deliver(Message(
            sender=addr, to=actor, type="note", budget=amount, wake=False, hops=0,
            title=f"budget reclaimed by {actor}",
            body=f"{actor} reclaimed {amount} unspent run(s) from {addr} ({available - amount} left with it). "
                 f"The runtime wrote this note on {addr}'s behalf; {addr} received nothing and was not woken.",
        ))
