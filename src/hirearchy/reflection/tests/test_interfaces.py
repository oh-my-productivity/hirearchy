"""D of SOLID: every class with behaviour subclasses the port it implements (ARCHITECTURE.md R6), and the api is what ``__init__`` exports."""

from __future__ import annotations

import hirearchy.reflection as reflection
from hirearchy.reflection import (
    CaseHistory,
    DeliverableChecks,
    ReflectionDigest,
    ServicePromptSections,
    ServiceReports,
    Stats,
    StatsReport,
    api,
)
from hirearchy.reflection._cases import DerivedCaseHistory
from hirearchy.reflection._deliverable_checks import FolderDeliverableChecks
from hirearchy.reflection._deliverables import FsDeliverableFolder
from hirearchy.reflection._digest import DigestBuilder
from hirearchy.reflection._files import OrgServicePaths
from hirearchy.reflection._ports import (
    BlobIds,
    CheckedVersions,
    DeliverableFolder,
    PlaybookSection,
    PlaybookTimelines,
    RegressionSection,
    RejectedServices,
    ReflectSection,
    RunCounter,
    ServicePaths,
    ServicesListing,
)
from hirearchy.reflection._reports import TextServiceReports
from hirearchy.reflection._runs import LogRunCounter
from hirearchy.reflection._sections import EvidenceReflectSection, MailRejectedServices, OwnedServicesListing, OwnerPromptSections, QuotedPlaybookSection, RegressionListSection
from hirearchy.reflection._timeline import StorePlaybookTimelines
from hirearchy.reflection.testing import FixedCaseHistory, FixedCheckedVersions, FixedDeliverableChecks, HashBlobIds, MemoryDeliverableFolder


def test_the_counts_subclass_their_port() -> None:
    assert StatsReport in Stats.__mro__


def test_each_port_has_its_implementation() -> None:
    assert CaseHistory in DerivedCaseHistory.__mro__ and CaseHistory in FixedCaseHistory.__mro__
    assert ReflectionDigest in DigestBuilder.__mro__
    assert ServiceReports in TextServiceReports.__mro__
    assert ServicePromptSections in OwnerPromptSections.__mro__
    assert DeliverableChecks in FolderDeliverableChecks.__mro__ and DeliverableChecks in FixedDeliverableChecks.__mro__


def test_each_role_inside_the_package_has_its_implementation() -> None:
    assert PlaybookTimelines in StorePlaybookTimelines.__mro__
    assert RunCounter in LogRunCounter.__mro__
    assert ServicePaths in OrgServicePaths.__mro__
    assert RejectedServices in MailRejectedServices.__mro__
    assert RegressionSection in RegressionListSection.__mro__
    assert PlaybookSection in QuotedPlaybookSection.__mro__
    assert ReflectSection in EvidenceReflectSection.__mro__
    assert ServicesListing in OwnedServicesListing.__mro__
    assert DeliverableFolder in FsDeliverableFolder.__mro__ and DeliverableFolder in MemoryDeliverableFolder.__mro__
    assert CheckedVersions in FixedCheckedVersions.__mro__
    assert BlobIds in HashBlobIds.__mro__


def test_the_package_exports_the_api_and_nothing_else() -> None:
    assert set(reflection.__all__) == set(api.__all__) and all(hasattr(reflection, n) for n in reflection.__all__)


def test_the_api_names_what_the_ports_return() -> None:
    assert {"Case", "Verdict", "Stats", "summarize", "stats_by_version", "version_at", "lessons_of"} <= set(api.__all__)
