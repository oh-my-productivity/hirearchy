"""Providers of the ``attention`` ports (ARCHITECTURE.md 6.1)."""

from __future__ import annotations

from ..agents import AgentDirectory
from ..attention import HumanQueue, OpenWork, WaitingOnUser
from ..attention._queue import InboxHumanQueue
from ..attention._waiting import RootTaskWaitingOnUser
from ..attention._work import RunnableOpenWork
from ..budget import BudgetQuery
from ..eligibility import PauseStore, RunnableQuery
from ..mail import MailboxReader, TaskQuery
from ..stalls import NudgeLedger
from ._builder import Builder
from ._lazy import PortResolver


def waiting_on_user(b: PortResolver) -> RootTaskWaitingOnUser:
    """The decision over the tasks, agents, mailboxes, flags, budgets and runnable query of ``b``, and the ledger of the stall ladder."""
    return RootTaskWaitingOnUser(
        b.get(TaskQuery), b.get(AgentDirectory), b.get(MailboxReader), b.get(PauseStore), b.get(BudgetQuery), b.get(RunnableQuery), b.get(NudgeLedger),
    )


def human_queue(b: PortResolver) -> InboxHumanQueue:
    """The queue over the mailboxes of ``b``."""
    return InboxHumanQueue(b.get(MailboxReader))


def open_work(b: PortResolver) -> RunnableOpenWork:
    """The question over the task views and the runnable query of ``b``."""
    return RunnableOpenWork(b.get(TaskQuery), b.get(RunnableQuery))


def register(b: Builder) -> None:
    b.provide(WaitingOnUser, waiting_on_user)
    b.provide(HumanQueue, human_queue)
    b.provide(OpenWork, open_work)

