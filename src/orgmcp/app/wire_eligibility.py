"""Providers of the ``eligibility`` ports (ARCHITECTURE.md 6.1)."""

from __future__ import annotations

from ..agents import AgentDirectory
from ..budget import BudgetQuery
from ..eligibility import AgentStates, FailureCounter, PauseStore, RunnableQuery
from ..eligibility._failures import LedgerFailureCounter
from ..eligibility._pause import FsPauseStore
from ..eligibility._ports import FsLedgerShape
from ..eligibility._runnable import DerivedRunnableQuery
from ..eligibility._states import DerivedAgentStates
from ..kernel import EventSink, LedgerStore, OrgLayout
from ..mail import MailboxReader
from ._builder import Builder


def register(b: Builder) -> None:
    b.provide(PauseStore, lambda b: FsPauseStore(b.get(OrgLayout), b.get(EventSink)))
    b.provide(FailureCounter, lambda b: LedgerFailureCounter(b.get(LedgerStore), FsLedgerShape(b.get(OrgLayout))))
    b.provide(AgentStates, lambda b: DerivedAgentStates(b.get(MailboxReader), b.get(PauseStore)))
    b.provide(
        RunnableQuery, lambda b: DerivedRunnableQuery(b.get(AgentDirectory), b.get(MailboxReader), b.get(PauseStore), b.get(BudgetQuery)),
    )
