# mypy: ignore-errors
"""Run budget: held, handed down, taken back (budget).

Moved verbatim from ``core.Org`` in step M2 (ARCHITECTURE.md 5.3 and 6.4); a later step replaces the bodies by calls
to the interfaces of the package named above."""

from __future__ import annotations

from ..kernel import Message, OrgError, ROOT


class BudgetMixin:
    """Run budget: held, handed down, taken back (budget)."""

    def budget(self, addr: str) -> int | None:
        """Runs this agent may still use. None = unlimited (root)."""
        a = self.norm(addr)
        if a == ROOT:
            return None
        got = sum(m.budget for m in self.received(a))
        given = sum(m.budget for m in self.sent(a))
        return got - given - self.runs_used(a)

    def delegable(self, addr: str) -> tuple[int, int, int]:
        """(budget, outstanding delegations, the most ``addr`` can hand down with one more delegation).

        The most is ``budget - outstanding - 1`` (one run kept per outstanding delegation to process its result, one
        for the new delegation's own result), never below 0.
        """
        budget = self.budget(addr) or 0
        out = len(self.outstanding(addr))
        return budget, out, max(0, budget - out - 1)

    def grant_hint(self, addr: str) -> str:
        """What a direct report can do with its budget now (shown to whoever just granted it runs); "" if it cannot hire."""
        if not self.exists(addr) or not self.charter(addr)[0].get("can_hire"):
            return ""
        budget, out, most = self.delegable(addr)
        head = f"`{addr}` now has {budget} run(s) and {out} outstanding delegation(s)"
        if most > 0:
            return f"{head}; with one more delegation it can hand down at most {most} run(s)."
        need = out + 2  # budget - out - 1 >= 1
        return (
            f"{head}: with {budget} run(s) and {out} outstanding delegation(s) it cannot delegate anything; it can "
            f"only process results or work itself - grant at least {max(0, need - budget)} more (a budget of {need}) "
            "to allow one delegation of 1 run."
        )

    def _check_allocation(self, actor: str, amount: int, new_delegation: bool) -> None:
        if actor == ROOT or amount == 0:
            return
        remaining = self.budget(actor) or 0
        reserve = len(self.outstanding(actor)) + (1 if new_delegation else 0)
        if remaining - amount < reserve:
            raise OrgError(
                f"not enough budget: you have {remaining} run(s) and must keep {reserve} in reserve "
                f"(one per outstanding delegation, to process its result), so you can hand down at most "
                f"{max(0, remaining - reserve)}. Ask your parent for more budget or do less."
            )

    def _default_budget(self, actor: str) -> int:
        """Runs a delegation gets when the caller names none: what the actor can afford, capped at default_budget.

        min(default_budget, remaining - reserve), where the reserve keeps one run per outstanding delegation plus
        one for the result of this new one. Root has no limit.
        """
        default = int(self.config["default_budget"])
        if actor == ROOT:
            return default
        remaining = self.budget(actor) or 0
        reserve = len(self.outstanding(actor)) + 1
        affordable = remaining - reserve
        if affordable < 1:
            raise OrgError(
                f"you cannot afford this delegation: you have {remaining} run(s) and must keep {reserve} in reserve "
                "(one per outstanding delegation, plus one to process the result of this one), so nothing is left "
                "to hand down. Options: ask your parent for more budget with `send` and end your run; do the work "
                "yourself; or, if the task cannot be completed without this step, report `blocked` (never `done`) "
                "and say what is missing."
            )
        return min(default, affordable)

    def _budget_to_return(self, actor: str, task: Message, status: str) -> int:
        """Runs that travel up with the final result of ``task``: everything the reporter has left, or 0.

        Only a final result (``done``/``failed``) returns budget, and only when nothing else needs the reporter's
        runs after it: no other open task, no other task reported ``blocked`` (it may be re-reported), no outstanding
        delegation (their results need the reserve) and no mail waiting for a run. It goes to the assigner, and only
        when that is the reporter's parent (the one route budget may travel up). The amount is read from the files
        at the moment of the report and the transfer is the result message itself, so it is counted exactly once: a
        redelivered run finds the task already final (a second ``report`` is refused) and nothing left to return.
        """
        if status == "blocked" or task.sender != self.parent(actor):
            return 0
        busy = (
            [t for t in self.open_tasks(actor) if t.id != task.id]
            or [t for t in self._blocked_tasks(actor) if t.id != task.id]
            or self.outstanding(actor)
            or self.unread(actor)
        )
        return 0 if busy else max(0, self.budget(actor) or 0)

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
        actor = self.require(actor)
        short = self.norm(report)
        addr = short if "/" in short else self.child_addr(actor, short)
        if addr == ROOT or not self.exists(addr) or self.parent(addr) != actor:
            reports = ", ".join(self.children(actor)) or "none"
            raise OrgError(
                f"you can only reclaim budget from your direct reports (yours: {reports}); {report!r} is not one. "
                "Ask a manager to reclaim from its own team."
            )
        if budget is not None and int(budget) < 1:
            raise OrgError("budget must be at least 1 run (omit it to reclaim everything the report has left)")
        why = [
            text for text in (
                "it is running now" if self.running(addr) else "",
                f"it has {len(self.open_tasks(addr))} open task(s)" if self.open_tasks(addr) else "",
                f"it has {len(self.outstanding(addr))} delegation(s) still outstanding" if self.outstanding(addr) else "",
                f"it has {self.unread(addr)} unread message(s) that will wake it" if self.unread(addr) else "",
            ) if text
        ]
        if why:
            raise OrgError(
                f"{addr} is busy ({'; '.join(why)}), so its runs are not stranded. Wait until it has reported, or "
                "leave its budget with it."
            )
        available = max(0, self.budget(addr) or 0)
        if available < 1:
            raise OrgError(f"{addr} has no unspent budget to reclaim ({self.budget(addr)} run(s) left)")
        amount = available if budget is None else int(budget)
        if amount > available:
            raise OrgError(f"{addr} has only {available} unspent run(s); you asked for {amount}")
        return self.deliver(Message(
            sender=addr, to=actor, type="note", budget=amount, wake=False, hops=0,
            title=f"budget reclaimed by {actor}",
            body=f"{actor} reclaimed {amount} unspent run(s) from {addr} ({available - amount} left with it). "
                 f"The runtime wrote this note on {addr}'s behalf; {addr} received nothing and was not woken.",
        ))
