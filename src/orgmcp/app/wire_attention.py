"""Providers of the ``attention`` ports (ARCHITECTURE.md 6.1), and the same objects over the runtime in force for the legacy functions.

``waiting_on_user_of``, ``human_queue_of`` and ``open_work_of`` serve ``scheduler.waiting_on_user`` / ``nothing_to_do`` and ``progress._human_items`` until
those modules are converted (D-sched-1, C-progress): they are handed an ``Org`` whose ``runtime`` tests replace (a ledger of the stall ladder, the
notices) and the dashboard's lenient ``Org`` replaces the mailboxes, the budgets and the pause flags of, so each call builds the objects over the
ports the runtime has *now*, as the functions it replaces read them through the ``Org``. Both go when the legacy functions do.
"""

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
from .runtime import OrgRuntime
from .wire_stalls import RuntimePorts


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


# ------------------------------------------------------------------------------ the legacy functions' objects


def waiting_on_user_of(runtime: OrgRuntime) -> WaitingOnUser:
    """``WaitingOnUser`` over the ports ``runtime`` has now."""
    return waiting_on_user(RuntimePorts(runtime))


def human_queue_of(runtime: OrgRuntime) -> HumanQueue:
    """``HumanQueue`` over the mailboxes ``runtime`` has now."""
    return human_queue(RuntimePorts(runtime))


def open_work_of(runtime: OrgRuntime) -> OpenWork:
    """``OpenWork`` over the ports ``runtime`` has now."""
    return open_work(RuntimePorts(runtime))
