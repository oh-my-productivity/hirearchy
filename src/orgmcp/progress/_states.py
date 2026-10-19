"""The state of a root task (moved from ``progress._state``)."""

from __future__ import annotations

from collections.abc import Sequence

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
        raise NotImplementedError("red: C-progress")
