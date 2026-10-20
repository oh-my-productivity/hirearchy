"""Providers of the ``budget`` ports (ARCHITECTURE.md 6.1)."""

from __future__ import annotations

from ..agents import AgentDirectory, CharterReader
from ..budget import AllocationPolicy, BudgetQuery, BudgetReclaimer
from ..budget._policy import ReserveAllocationPolicy
from ..budget._query import DerivedBudgetQuery
from ..budget._reclaim import NoteBudgetReclaimer
from ..delivery import MessageDelivery
from ..mail import MailboxReader, TaskQuery
from ..runs import RunLogReader
from ..settings import OrgSettings
from ._builder import Builder


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
