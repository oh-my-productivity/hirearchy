"""Providers of the ``dispatch`` ports (ARCHITECTURE.md 6.1).

``ReworkContext`` is a port that ``services`` implements (``ServiceReworkContext``): ``wire_services`` provides it."""

from __future__ import annotations

from ..access import AccessScopes
from ..agents import AgentDirectory
from ..budget import AllocationPolicy
from ..delivery import MessageDelivery
from ..dispatch import ArtifactNormalizer, HopCounter, MessageSender, ReworkContext, RoutePolicy, TaskAssigner, TaskReporter
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
    """The rules the three commands are made of (route policy, hop counter, artifact annotator) are ports of the package: the commands take them
    from the runtime, and so does the facade. The lessons policy is stateless and private to the reporter."""
    b.provide(RoutePolicy, lambda b: ParentSiblingRoutePolicy(b.get(MailboxReader)))
    b.provide(HopCounter, lambda b: InflightHopCounter(b.get(MailboxReader)))
    b.provide(ArtifactNormalizer, lambda b: ArtifactAnnotator(b.get(OrgLayout), b.get(AccessScopes)))
    b.provide(
        MessageSender,
        lambda b: RuleMessageSender(
            b.get(AgentDirectory), b.get(OrgSettings), b.get(RoutePolicy), b.get(AllocationPolicy), b.get(HopCounter), b.get(MessageDelivery),
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
            b.get(ArtifactNormalizer), b.get(MessageSender),
        ),
    )
