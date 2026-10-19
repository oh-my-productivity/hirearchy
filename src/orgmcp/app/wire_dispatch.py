"""Providers of the ``dispatch`` ports (ARCHITECTURE.md 6.1).

``ReworkContext`` is a port that ``services`` implements (``ServiceReworkContext``): ``wire_services`` provides it."""

from __future__ import annotations

from ..access import AccessScopes
from ..agents import AgentDirectory
from ..budget import AllocationPolicy
from ..delivery import MessageDelivery
from ..dispatch import MessageSender, ReworkContext, TaskAssigner, TaskReporter
from ..dispatch._artifacts import ArtifactAnnotator
from ..dispatch._assigner import RuleTaskAssigner
from ..dispatch._hops import InflightHopCounter
from ..dispatch._lessons import LessonsPolicy
from ..dispatch._reporter import RuleTaskReporter
from ..dispatch._routes import ParentSiblingRoutePolicy
from ..dispatch._sender import RuleMessageSender
from ..kernel import OrgLayout
from ..mail import MailboxReader, TaskQuery
from ..settings import OrgSettings
from ..templates import DocumentTemplates
from ._builder import Builder


def register(b: Builder) -> None:
    """The collaborators among the rules of the package (route policy, hop counter, artifact annotator, lessons policy) are private to it: they
    are made here, inside the providers of the ports that use them."""
    b.provide(
        MessageSender,
        lambda b: RuleMessageSender(
            b.get(AgentDirectory), b.get(OrgSettings), ParentSiblingRoutePolicy(b.get(MailboxReader)), b.get(AllocationPolicy),
            InflightHopCounter(b.get(MailboxReader)), b.get(MessageDelivery),
        ),
    )
    b.provide(
        TaskAssigner,
        lambda b: RuleTaskAssigner(
            b.get(AgentDirectory), b.get(MailboxReader), b.get(DocumentTemplates), b.get(AllocationPolicy), b.get(ReworkContext), b.get(MessageSender),
        ),
    )
    b.provide(
        TaskReporter,
        lambda b: RuleTaskReporter(
            b.get(AgentDirectory), b.get(MailboxReader), b.get(TaskQuery), b.get(DocumentTemplates), b.get(AllocationPolicy), LessonsPolicy(),
            ArtifactAnnotator(b.get(OrgLayout), b.get(AccessScopes)), b.get(MessageSender),
        ),
    )
