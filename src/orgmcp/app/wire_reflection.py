"""Providers of the ``reflection`` ports (ARCHITECTURE.md 6.1).

The history is built from the ports of the organization it reads; the small parts the digest, the listing and the prompt sections are made of (who counts
the runs, when a playbook was written, where the files are named, which services a batch rejects, the two sections) are private to the package and made
here, inside the providers of the ports that use them.
"""

from __future__ import annotations

from ..agents import AgentDirectory
from ..kernel import OrgLayout
from ..mail import MailboxReader, TaskQuery
from ..reflection import CaseHistory, ReflectionDigest, ServicePromptSections, ServiceReports
from ..reflection._cases import DerivedCaseHistory
from ..reflection._digest import DigestBuilder
from ..reflection._files import OrgServicePaths
from ..reflection._reports import TextServiceReports
from ..reflection._runs import LogRunCounter
from ..reflection._sections import EvidenceReflectSection, MailRejectedServices, OwnedServicesListing, OwnerPromptSections, QuotedPlaybookSection
from ..reflection._timeline import StorePlaybookTimelines
from ..runs import RunLogReader
from ..services import ServiceCatalog, ServiceHints, ServiceStore
from ..settings import OrgSettings
from ._builder import Builder


def register(b: Builder) -> None:
    b.provide(
        CaseHistory,
        lambda b: DerivedCaseHistory(
            b.get(ServiceCatalog), b.get(AgentDirectory), b.get(MailboxReader), b.get(ServiceHints),
            StorePlaybookTimelines(b.get(ServiceStore)), LogRunCounter(b.get(RunLogReader)),
        ),
    )
    b.provide(ReflectionDigest, lambda b: DigestBuilder(b.get(ServiceCatalog), b.get(CaseHistory)))
    b.provide(
        ServiceReports,
        lambda b: TextServiceReports(b.get(AgentDirectory), b.get(ServiceCatalog), b.get(CaseHistory), OrgServicePaths(b.get(OrgLayout))),
    )
    b.provide(ServicePromptSections, _sections)


def _sections(b: Builder) -> ServicePromptSections:
    catalog, paths = b.get(ServiceCatalog), OrgServicePaths(b.get(OrgLayout))
    return OwnerPromptSections(
        catalog, OwnedServicesListing(catalog, b.get(CaseHistory), paths), b.get(ReflectionDigest), b.get(TaskQuery),
        MailRejectedServices(b.get(MailboxReader)), QuotedPlaybookSection(catalog, paths), EvidenceReflectSection(catalog, b.get(OrgSettings), paths),
    )
