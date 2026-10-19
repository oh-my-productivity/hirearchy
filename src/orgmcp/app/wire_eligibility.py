"""Providers of the ``eligibility`` ports (ARCHITECTURE.md 6.1), and the dashboard's lenient variant for the legacy ``LenientOrg``.

``lenient`` goes away with ``LenientOrg`` (C-dashdata), whose caching role for the flag files is the decorator of this package.
"""

from __future__ import annotations

import dataclasses

from ..agents import AgentDirectory
from ..budget import BudgetQuery
from ..eligibility import AgentStates, FailureCounter, PauseStore, RunnableQuery
from ..eligibility._caching import CachingPauseStore
from ..eligibility._failures import LedgerFailureCounter
from ..eligibility._pause import FsPauseStore
from ..eligibility._ports import DirectoryProbe, FsLedgerShape
from ..eligibility._runnable import DerivedRunnableQuery
from ..eligibility._states import DerivedAgentStates
from ..kernel import EventSink, LedgerStore, OrgLayout
from ..mail import MailboxReader
from ._builder import Builder
from .runtime import OrgRuntime


def register(b: Builder) -> None:
    b.provide(PauseStore, lambda b: FsPauseStore(b.get(OrgLayout), b.get(EventSink)))
    b.provide(FailureCounter, lambda b: LedgerFailureCounter(b.get(LedgerStore), FsLedgerShape(b.get(OrgLayout))))
    b.provide(AgentStates, lambda b: DerivedAgentStates(b.get(MailboxReader), b.get(PauseStore)))
    b.provide(
        RunnableQuery, lambda b: DerivedRunnableQuery(b.get(AgentDirectory), b.get(MailboxReader), b.get(PauseStore), b.get(BudgetQuery)),
    )


def lenient(runtime: OrgRuntime, probe: DirectoryProbe) -> OrgRuntime:
    """``runtime`` with the dashboard's decorator on the pause store (a flag file read per change of its mtime, ``probe`` tells it), and the state
    and runnable queries over ITS mailboxes, agents and budgets (so the lenient ones, when ``wire_agents.lenient``, ``wire_mail.lenient`` and
    ``wire_budget.lenient`` were applied first)."""
    pauses = CachingPauseStore(runtime.pause_store, probe)
    return dataclasses.replace(
        runtime,
        pause_store=pauses,
        agent_states=DerivedAgentStates(runtime.mailbox, pauses),
        runnable_query=DerivedRunnableQuery(runtime.agents, runtime.mailbox, pauses, runtime.budget_query),
    )
