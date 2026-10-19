"""Providers of the ``hierarchy`` ports (ARCHITECTURE.md 6.1).

The place of an agent (``AgentSlots``, hierarchy's own narrow port) is the directory of the organization's layout, so ``FsAgentSlots`` is made here,
where classes are constructed, and not offered as a port of the runtime."""

from __future__ import annotations

from ..access import AccessScopes, AuthorityPolicy, ModelResolver
from ..agents import AgentDirectory, AgentRegistry, CharterReader
from ..budget import BudgetQuery
from ..delivery import MessageDelivery
from ..hierarchy import Hiring, Retirement
from ..hierarchy._hiring import RuleHiring
from ..hierarchy._retirement import RuleRetirement
from ..hierarchy._slots import FsAgentSlots
from ..kernel import Clock, EventSink, OrgLayout
from ..mail import TaskQuery
from ..settings import OrgSettings
from ..templates import DocumentTemplates, Notices
from ._builder import Builder


def register(b: Builder) -> None:
    b.provide(
        Hiring,
        lambda b: RuleHiring(
            b.get(AgentDirectory), b.get(CharterReader), b.get(AgentRegistry), FsAgentSlots(b.get(OrgLayout)), b.get(OrgSettings),
            b.get(DocumentTemplates), b.get(AccessScopes), b.get(AuthorityPolicy), b.get(ModelResolver), b.get(Clock), b.get(EventSink),
        ),
    )
    b.provide(
        Retirement,
        lambda b: RuleRetirement(
            b.get(AgentDirectory), b.get(AgentRegistry), b.get(TaskQuery), b.get(BudgetQuery), b.get(MessageDelivery), b.get(Notices),
            b.get(Clock), b.get(EventSink),
        ),
    )
