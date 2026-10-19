"""The state of a root task (moved from ``progress._state``)."""

from __future__ import annotations

from collections.abc import Sequence

from ..attention import short, summary
from ..eligibility import PauseStore
from ..kernel import Message
from ..mail import MailboxReader, TaskQuery
from ._ports import TaskState, TaskStates


class MailTaskStates(TaskStates):
    def __init__(self, mail: MailboxReader, pauses: PauseStore, tasks: TaskQuery) -> None:
        self._mail = mail
        self._pauses = pauses
        self._tasks = tasks

    def state_of(self, task: Message, result: Message | None, team: Sequence[str]) -> TaskState:
        if result is not None and result.status in ("done", "failed"):
            return TaskState(result.status, "")
        if result is not None:  # blocked
            return TaskState(f"blocked: {short(summary(result.body)) or 'no reason given'}", "")
        if not team:
            return TaskState(f"failed: {task.to} no longer exists", "")
        running = [a for a in team if self._mail.has_inflight(a)]
        unread = [a for a in team if self._mail.unread(a) and not self._pauses.paused(a) and a not in running]
        who = "; ".join(
            x for x in (
                "running: " + ", ".join(running) if running else "",
                "unread work: " + ", ".join(unread) if unread else "",
            ) if x
        )
        if running or unread:
            return TaskState("working", who)
        holders = [a for a in team if self._tasks.open_tasks(a) and not self._tasks.outstanding(a)]
        if holders == [task.to]:
            why = self._pauses.paused(task.to)
            return TaskState(f"stalled ({task.to} {'is paused: ' + why if why else 'has not reported and nothing is running'})", "")
        names = ", ".join(a + (f" (paused: {self._pauses.paused(a)})" if self._pauses.paused(a) else "") for a in holders)
        return TaskState(f"waiting on {names or task.to}", "")
