"""Providers of the ``budget`` ports (ARCHITECTURE.md 6.1), and the dashboard's lenient variant for the legacy ``LenientOrg``.

``lenient`` goes away with ``LenientOrg`` (C-dashdata), whose per-refresh cache of the run count is the decorator of the runs package.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Callable

from ..agents import AgentDirectory, CharterReader
from ..budget import AllocationPolicy, BudgetQuery, BudgetReclaimer
from ..budget._policy import ReserveAllocationPolicy
from ..budget._ports import RunCounter
from ..budget._query import DerivedBudgetQuery
from ..budget._reclaim import NoteBudgetReclaimer
from ..delivery import MessageDelivery
from ..mail import MailboxReader, TaskQuery
from ..runs import RunLogReader
from ..settings import OrgSettings
from ._builder import Builder
from .runtime import OrgRuntime


def register(b: Builder) -> None:
    b.provide(
        BudgetQuery,
        lambda b: DerivedBudgetQuery(b.get(MailboxReader), b.get(RunLogReader), b.get(AgentDirectory), b.get(CharterReader), b.get(TaskQuery)),
    )
    b.provide(
        AllocationPolicy, lambda b: ReserveAllocationPolicy(b.get(BudgetQuery), b.get(TaskQuery), b.get(MailboxReader), b.get(OrgSettings)),
    )
    b.provide(
        BudgetReclaimer,
        lambda b: NoteBudgetReclaimer(b.get(MessageDelivery), b.get(BudgetQuery), b.get(TaskQuery), b.get(MailboxReader), b.get(AgentDirectory)),
    )


class CallableRunCounter(RunCounter):
    """The number of runs an agent has made, answered by a function (the dashboard's ``LenientOrg.runs_used``, which caches it per refresh)."""

    def __init__(self, count: Callable[[str], int]) -> None:
        self._count = count

    def count(self, addr: str) -> int:
        return self._count(addr)


def lenient(runtime: OrgRuntime, runs_used: Callable[[str], int]) -> OrgRuntime:
    """``runtime`` with the budget ports over ITS mailboxes, task views and agents (so the lenient ones, when ``wire_agents.lenient`` and
    ``wire_mail.lenient`` were applied first) and over ``runs_used`` for the number of runs made (the dashboard's cache of it)."""
    query = DerivedBudgetQuery(runtime.mailbox, CallableRunCounter(runs_used), runtime.agents, runtime.charters, runtime.task_query)
    return dataclasses.replace(
        runtime,
        budget_query=query,
        allocation_policy=ReserveAllocationPolicy(query, runtime.task_query, runtime.mailbox, runtime.settings),
        budget_reclaimer=NoteBudgetReclaimer(runtime.delivery, query, runtime.task_query, runtime.mailbox, runtime.agents),
    )
