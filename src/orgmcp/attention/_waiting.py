"""``RootTaskWaitingOnUser``: whether every open root task is unable to progress without the user (moved from ``scheduler.waiting_on_user``)."""

from __future__ import annotations

from collections.abc import Collection

from ..agents import AgentDirectory
from ..budget import BudgetQuery
from ..eligibility import PauseStore, RunnableQuery
from ..mail import MailboxReader, TaskQuery
from ..stalls import NudgeLedger
from .api import Waiting, WaitingOnUser


def names(addrs: list[str]) -> str:
    raise NotImplementedError("red: C-attention")


class RootTaskWaitingOnUser(WaitingOnUser):
    def __init__(
        self, tasks: TaskQuery, agents: AgentDirectory, mail: MailboxReader, pauses: PauseStore, budgets: BudgetQuery, runnable: RunnableQuery,
        nudges: NudgeLedger,
    ) -> None:
        self._tasks = tasks
        self._agents = agents
        self._mail = mail
        self._pauses = pauses
        self._budgets = budgets
        self._runnable = runnable
        self._nudges = nudges

    def analyze(self, *, running: Collection[str] | None = None, blocked: Collection[str] = (), can_start: bool = True) -> Waiting | None:
        raise NotImplementedError("red: C-attention")
