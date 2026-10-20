"""The public surface of ``stalls``: the escalation ladder for open tasks whose assignee has gone quiet.

A task is *stalled* when its assignee is not running, has no unread mail, is not paused and waits for no delegated work, and nothing has happened
for ``stall_after`` seconds (since the latest of the task's creation, the assignee's last run and the previous step). The ladder then climbs one
step per ``stall_after``: a reminder to the assignee, a note to the assigner, then to each ancestor in turn, up to root, and stops. What it has
done is kept in ``.runtime/nudges.json`` (``NudgeLedger``), which ``attention`` reads to tell whether the ladder may still wake someone.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ..kernel import Message

__all__ = [
    "NudgeLedger",
    "StallLadder",
]


@runtime_checkable
class StallLadder(Protocol):
    def check(self) -> list[str]:
        """One pass of the ladder over every agent's open tasks: remind the assignee, then tell the assigner, then each ancestor up to root.
        Delivers the notes, emits a ``stall.nudge`` event for each and keeps the steps taken in the ledger (dropping those of tasks that are no
        longer open). Returns the operator lines (``<agent>: reminded about open task <id>`` / ``<agent>: stalled on <id>, told <who>``)."""
        ...


@runtime_checkable
class NudgeLedger(Protocol):
    def entries(self) -> dict[str, dict[str, float]]:
        """Task id -> ``{"step": last step taken, "at": when}``. The legacy form (a text: ``"nudged"`` is step 0, anything else ``"escalated"``,
        step 1, both at time 0) is accepted; an entry that is malformed, and a ledger that is, is dropped: never raises."""
        ...

    def chain(self, addr: str, task: Message) -> list[str]:
        """Who hears about a stalled task, in the order of the steps: the assignee ``addr``, its assigner (the task's sender, when that agent
        still exists, else the assignee's parent), then each ancestor up to root."""
        ...
