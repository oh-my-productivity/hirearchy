"""The quality view (0b): the tasks a blocked result holds runs on, and those left blocked (4.5), pure over what ``mail`` reads."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from ..kernel import Message
from ..mail import moved_past


@dataclass(frozen=True)
class HeldTask:
    """A task whose blocked result still holds runs on its assignee (``task``), with that result (``blocked``) and the number of tasks its sender has
    sent the assignee since, outside the chain (``sent_since``): above 0 it is left blocked, the sender moved past it without a verdict."""

    task: Message
    blocked: Message
    sent_since: int = 0

    @property
    def left_blocked(self) -> bool:
        return self.sent_since > 0


def held_tasks(tasks: Sequence[Message], latest: Mapping[str, Message], received: Sequence[Message]) -> list[Message]:
    """The tasks of ``tasks`` (the assignee's tasks whose latest result is ``blocked``) that ``mail.moved_past`` does not release (pure): the ones
    ``budget_to_return`` holds the assignee's runs on. ``latest`` maps a task id to its latest result; ``received`` is what the assignee received."""
    return [t for t in tasks if (blocked := latest.get(t.id)) is not None and not moved_past(t, blocked, received)]


def _chain(task: Message, received: Sequence[Message]) -> set[str]:
    """The ids of the tasks the sender of ``task`` sent the assignee that are connected to it through ``revises``, in both directions, ``task`` itself
    included: the chain of ``mail.moved_past`` (the same closure, kept here because ``mail`` does not publish it)."""
    mine = [t for t in received if t.type == "task" and t.sender == task.sender]
    chain = {task.id}
    grown = True
    while grown:
        more = {t.id for t in mine if t.revises in chain} | {t.revises for t in mine if t.id in chain and t.revises}
        grown = not more <= chain
        chain |= more
    return chain


def left_blocked(task: Message, blocked: Message, received: Sequence[Message]) -> int:
    """How many tasks the sender of the held ``task`` has sent its assignee since ``blocked`` (the task's latest result), outside the task's chain
    (pure): 0 when none, otherwise the task is left blocked, "moved past without a verdict" in the gate's words (4.5)."""
    chain = _chain(task, received)
    return sum(1 for t in received if t.type == "task" and t.sender == task.sender and t.id > blocked.id and t.id not in chain)


def blocked_listing(tasks: Sequence[Message], latest: Mapping[str, Message], received: Sequence[Message]) -> tuple[HeldTask, ...]:
    """The held tasks of one agent, oldest block first, when at least one of them is left blocked; else none (pure). The moved-past section lists an
    agent with every task it holds, because while any exists its later results return no runs (4.5)."""
    held = sorted(
        (HeldTask(t, latest[t.id], left_blocked(t, latest[t.id], received)) for t in held_tasks(tasks, latest, received)), key=lambda h: h.blocked.id,
    )
    return tuple(held) if any(h.left_blocked for h in held) else ()
