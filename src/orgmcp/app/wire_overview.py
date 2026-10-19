"""Providers of the ``overview`` ports (ARCHITECTURE.md 6.1).

The tree reads the agents, their charters, the mailboxes, the tasks, the budgets, the states and the services of the runtime it is built from."""

from __future__ import annotations

from ..agents import AgentDirectory, CharterReader
from ..budget import BudgetQuery
from ..eligibility import AgentStates
from ..mail import MailboxReader, TaskQuery
from ..overview import OrgTree
from ..overview._tree import TextOrgTree
from ..services import ServiceCatalog
from ._builder import Builder


def register(b: Builder) -> None:
    b.provide(
        OrgTree,
        lambda b: TextOrgTree(
            b.get(AgentDirectory), b.get(CharterReader), b.get(MailboxReader), b.get(TaskQuery), b.get(BudgetQuery), b.get(AgentStates),
            b.get(ServiceCatalog),
        ),
    )
