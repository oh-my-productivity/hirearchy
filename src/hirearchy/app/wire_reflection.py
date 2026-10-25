"""Providers of the ``reflection`` ports (ARCHITECTURE.md 6.1), and of ``ServiceEvidence`` and ``JudgedVersions``, the ports of ``services`` that ``reflection``
implements.

``DeliverableChecks`` is joined here: ``reflection`` reads the deliverable folders itself, and the team's checked versions come from the organization's
git history (``snapshots``), which only the composition root may put beside it.

The history is built from the ports of the organization it reads; the small parts the digest, the listing and the prompt sections are made of (who counts
the runs, when a playbook was written, where the files are named, which services a batch rejects, the two sections) are private to the package and made
here, inside the providers of the ports that use them.
"""

from __future__ import annotations

from ..agents import AgentDirectory, CharterReader
from ..kernel import Clock, OrgLayout
from ..mail import MailboxReader
from ..reflection import CaseHistory, DeliverableChecks, ReflectionDigest, ServicePromptSections, ServiceReports, ServiceSteps
from ..reflection._cases import DerivedCaseHistory
from ..reflection._deliverable_checks import FolderDeliverableChecks
from ..reflection._deliverables import FsDeliverableFolder
from ..reflection._digest import DigestBuilder
from ..reflection._evidence import CaseServiceEvidence
from ..reflection._files import OrgServicePaths
from ..reflection._allowance import CaseAllowanceOf
from ..reflection._judged import CaseJudgedVersions
from ..reflection._reports import TextServiceReports
from ..reflection._runs import LogRunCounter
from ..reflection._sections import EvidenceReflectSection, MailRejectedServices, OwnedServicesListing, OwnerPromptSections, QuotedPlaybookSection, RegressionListSection
from ..reflection._steps import TextServiceSteps
from ..reflection._timeline import StorePlaybookTimelines
from ..runs import RunLogReader
from ..services import CaseAllowance, JudgedVersions, ServiceCatalog, ServiceEvidence, ServiceHints, ServiceStore
from ..settings import OrgSettings
from ..snapshots import OrgHistory
from ._builder import Builder
from ._checked_versions import GitBlobIds, GitCheckedVersions


def register(b: Builder) -> None:
    b.provide(
        CaseHistory,
        lambda b: DerivedCaseHistory(
            b.get(ServiceCatalog), b.get(AgentDirectory), b.get(MailboxReader), b.get(ServiceHints),
            StorePlaybookTimelines(b.get(ServiceStore)), LogRunCounter(b.get(RunLogReader), b.get(MailboxReader)), b.get(CharterReader),
        ),
    )
    b.provide(ReflectionDigest, lambda b: DigestBuilder(b.get(ServiceCatalog), b.get(CaseHistory)))
    b.provide(ServiceEvidence, lambda b: CaseServiceEvidence(b.get(CaseHistory), b.get(ServiceCatalog)))
    b.provide(
        JudgedVersions,
        lambda b: CaseJudgedVersions(b.get(CaseHistory), b.get(MailboxReader), GitCheckedVersions(b.get(OrgHistory), b.get(OrgLayout))),
    )
    b.provide(CaseAllowance, lambda b: CaseAllowanceOf(b.get(CaseHistory), b.get(ServiceCatalog)))
    b.provide(
        ServiceReports,
        lambda b: TextServiceReports(b.get(AgentDirectory), b.get(ServiceCatalog), b.get(CaseHistory), OrgServicePaths(b.get(OrgLayout))),
    )
    b.provide(
        ServiceSteps,
        lambda b: TextServiceSteps(b.get(AgentDirectory), b.get(ServiceCatalog), b.get(CaseHistory), b.get(MailboxReader)),
    )
    b.provide(ServicePromptSections, _sections)
    b.provide(
        DeliverableChecks,
        lambda b: FolderDeliverableChecks(
            b.get(ServiceCatalog), b.get(CaseHistory), b.get(MailboxReader), FsDeliverableFolder(),
            GitCheckedVersions(b.get(OrgHistory), b.get(OrgLayout)), GitBlobIds(), b.get(Clock),
        ),
    )


def _sections(b: Builder) -> ServicePromptSections:
    catalog, history, paths = b.get(ServiceCatalog), b.get(CaseHistory), OrgServicePaths(b.get(OrgLayout))
    return OwnerPromptSections(
        catalog, OwnedServicesListing(catalog, history, paths), b.get(ReflectionDigest), b.get(MailboxReader),
        MailRejectedServices(b.get(MailboxReader)), QuotedPlaybookSection(catalog, paths), EvidenceReflectSection(catalog, b.get(OrgSettings), paths, history),
        RegressionListSection(catalog, history),
    )
