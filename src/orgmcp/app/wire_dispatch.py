"""Providers of the ``dispatch`` ports (ARCHITECTURE.md 6.1), and the legacy source of the service fields of a rework.

``ReworkContext`` is a port that ``services`` implements (``ServiceReworkContext``, step C-services). Until then the legacy ``services.rework_fields``
answers, over an ``Org`` of the same root: ``LegacyReworkContext`` is the one seam. C-services deletes it together with its provider below (the
provider of ``ReworkContext`` moves to ``wire_services``: two providers of one port are refused)."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from pathlib import Path
from typing import TYPE_CHECKING, cast

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

if TYPE_CHECKING:
    from .facade import Org


class LegacyReworkContext(ReworkContext):
    """The service fields of a rework, answered by the legacy ``services.rework_fields`` over an ``Org`` of ``root``.

    The ``Org`` is made when a rework is asked for (a rework is rare, and constructing an ``Org`` does no I/O), and ``services`` is imported then:
    it imports the facade, which imports this package of the composition root."""

    def __init__(self, open_org: Callable[[], object], rework_fields: Callable[[object, str, str], Mapping[str, object]] | None = None) -> None:
        self._open_org = open_org
        self._rework_fields = rework_fields

    def fields_for(self, actor: str, revises: str) -> Mapping[str, object]:
        org = self._open_org()
        if self._rework_fields is not None:
            return dict(self._rework_fields(org, actor, revises))
        from .. import services  # the legacy home of the rule, until C-services

        return dict(services.rework_fields(cast("Org", org), actor, revises))


def legacy_rework_context(root: Path) -> ReworkContext:
    """The legacy source of the rework fields for the organization at ``root``."""

    def open_org() -> object:
        from .facade import Org

        return Org(root)

    return LegacyReworkContext(open_org)


def register(b: Builder) -> None:
    """The collaborators among the rules of the package (route policy, hop counter, artifact annotator, lessons policy) are private to it: they
    are made here, inside the providers of the ports that use them."""
    b.provide(ReworkContext, lambda b: legacy_rework_context(b.root))
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
