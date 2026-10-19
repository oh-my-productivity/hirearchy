"""The public surface of ``attention``: what remains to be done, and by whom.

Root is the human's seat. Three questions about it are asked all over the system (the scheduler's exit, ``progress``, ``observe now``, the dashboard,
the MCP ``start`` tool): *what waits for a decision* (``HumanQueue``), *can anything still move without the human* (``WaitingOnUser``) and *is there
anything left to run at all* (``OpenWork``). All three only read.
"""

from __future__ import annotations

from collections.abc import Collection
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

__all__ = [
    "HumanQueue",
    "OpenWork",
    "Waiting",
    "WaitingOnUser",
]


@dataclass(frozen=True)
class Waiting:
    """Why open root tasks cannot move without the user. ``text``: ``"waiting on you: ..."``; ``options``: what the user can do (``"Your options: ..."``);
    ``settled``: False while the stall ladder (reminders to the holder) may still wake someone."""

    text: str
    options: str
    settled: bool = True


@runtime_checkable
class WaitingOnUser(Protocol):
    def analyze(self, *, running: Collection[str] | None = None, blocked: Collection[str] = (), can_start: bool = True) -> Waiting | None:
        """Is every open root task unable to progress without the user? ``None`` if not (or root has no open task).

        True when nothing runs and no agent could start a run (``running`` / ``blocked``: the scheduler's own view of the runs in flight and of the
        agents whose orphaned run may still be alive, default the inflight mailboxes and none; ``can_start=False``: the run cap is spent), yet root
        still waits for a result. The holders are then paused for budget or repeated failures, or stalled with nothing happening, or gone. Read-only."""
        ...


@runtime_checkable
class HumanQueue(Protocol):
    def items(self) -> list[tuple[str, str]]:
        """``(message id, line)`` for each unread root message that asks for a decision, oldest first: a ``blocked`` or ``failed`` result, and every
        note or runtime notice that wakes (budget requests, questions, escalations). Not listed: a ``done`` result (the task line already summarises
        it) and quiet messages (``wake: false``: budget returned or reclaimed, refunds, playbook-revision and contract-change notices), which
        only carry runs or news."""
        ...

    def lines(self) -> list[str]:
        """The lines of ``items``: ``Needs you: <what> "<title>": <first line> (message <id>)``."""
        ...


@runtime_checkable
class OpenWork(Protocol):
    def nothing_to_do(self) -> bool:
        """Would an until-done scheduler exit at once: root has no open task and no agent has work it could start."""
        ...
