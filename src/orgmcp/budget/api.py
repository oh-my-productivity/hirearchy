"""The public surface of ``budget``: how many runs an agent may still use, and how runs are handed down, returned and taken back.

Budget is derived, never stored: what an agent received (grants, tasks, results, notes that carry runs) minus what it handed down minus the run logs it
has made. Root has no limit. ``BudgetQuery`` answers that, ``AllocationPolicy`` holds the reserve rule every hand-down obeys, and ``BudgetReclaimer`` is
the one way a manager takes unspent runs back: a note, delivered like any other.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ..kernel import Message

__all__ = [
    "AllocationPolicy",
    "BudgetQuery",
    "BudgetReclaimer",
]


@runtime_checkable
class BudgetQuery(Protocol):
    def budget(self, addr: str) -> int | None:
        """Runs this agent may still use: what it received (inbox, inflight, read) minus what it sent minus its run logs. It can be negative
        (a redelivered run is charged like any run). ``None`` is unlimited: root."""
        ...

    def delegable(self, addr: str) -> tuple[int, int, int]:
        """``(budget, outstanding delegations, the most ``addr`` can hand down with one more delegation)``. The most is
        ``budget - outstanding - 1`` (one run kept per outstanding delegation to process its result, one for the new delegation's own result),
        never below 0. Root's budget counts as 0."""
        ...

    def grant_hint(self, addr: str) -> str:
        """What an agent can do with its budget now, in words, for whoever just granted it runs; ``""`` for an agent that does not exist or
        cannot hire."""
        ...


@runtime_checkable
class AllocationPolicy(Protocol):
    def check_allocation(self, actor: str, amount: int, new_delegation: bool) -> None:
        """Raise ``OrgError`` unless ``actor`` can hand down ``amount`` runs and keep one in reserve per outstanding delegation (plus one for
        the result of the new delegation when ``new_delegation``). Root and an amount of 0 always pass."""
        ...

    def default_budget(self, actor: str) -> int:
        """Runs a delegation gets when the caller names none: ``min(default_budget, remaining - reserve)``, the reserve being one per
        outstanding delegation plus one for this one. Root has no limit and gets ``default_budget``. ``OrgError`` (with the options) when
        less than 1 can be afforded."""
        ...

    def budget_to_return(self, actor: str, task: Message, status: str) -> int:
        """Runs that travel up with the result ``actor`` reports for ``task``: everything it has left, or 0. Only a final result
        (``done``/``failed``) returns budget, only to the assigner when that is ``actor``'s parent, and only when nothing else needs ``actor``'s
        runs after it: no other open task, no other task reported ``blocked``, no outstanding delegation and no mail waiting for a run."""
        ...


@runtime_checkable
class BudgetReclaimer(Protocol):
    def reclaim(self, actor: str, report: str, budget: int | None = None) -> Message:
        """Pull unspent runs (all of them by default) back from an idle DIRECT report of ``actor`` (short name or full address) and return
        the delivered note: from the report to ``actor``, carrying the runs, not waking anybody. Refused (``OrgError``) for an agent that is
        not a direct report, an amount below 1 or above what is left, a report that is busy (running, open tasks, outstanding delegations,
        waking mail) and a report with nothing left."""
        ...
