"""D of SOLID: every class with behaviour subclasses the port it implements (ARCHITECTURE.md R6), and the api is what ``__init__`` exports."""

from __future__ import annotations

import orgmcp.reflection as reflection
from orgmcp.reflection import (
    CaseHistory,
    ReflectionDigest,
    ServicePromptSections,
    ServiceReports,
    Stats,
    StatsReport,
    api,
)
from orgmcp.reflection._cases import DerivedCaseHistory
from orgmcp.reflection._digest import DigestBuilder
from orgmcp.reflection._files import OrgServicePaths
from orgmcp.reflection._ports import (
    ConfigSource,
    PlaybookSection,
    PlaybookTimelines,
    RejectedServices,
    ReflectSection,
    RunCounter,
    ServicePaths,
    ServicesListing,
)
from orgmcp.reflection._reports import TextServiceReports
from orgmcp.reflection._runs import LogRunCounter
from orgmcp.reflection._sections import EvidenceReflectSection, MailRejectedServices, OwnedServicesListing, OwnerPromptSections, QuotedPlaybookSection
from orgmcp.reflection._timeline import StorePlaybookTimelines
from orgmcp.reflection._assembly import CallableConfig
from orgmcp.reflection.testing import FixedCaseHistory


def test_the_counts_subclass_their_port() -> None:
    assert StatsReport in Stats.__mro__


def test_each_port_has_its_implementation() -> None:
    assert CaseHistory in DerivedCaseHistory.__mro__ and CaseHistory in FixedCaseHistory.__mro__
    assert ReflectionDigest in DigestBuilder.__mro__
    assert ServiceReports in TextServiceReports.__mro__
    assert ServicePromptSections in OwnerPromptSections.__mro__


def test_each_role_inside_the_package_has_its_implementation() -> None:
    assert PlaybookTimelines in StorePlaybookTimelines.__mro__
    assert RunCounter in LogRunCounter.__mro__
    assert ServicePaths in OrgServicePaths.__mro__
    assert RejectedServices in MailRejectedServices.__mro__
    assert PlaybookSection in QuotedPlaybookSection.__mro__
    assert ReflectSection in EvidenceReflectSection.__mro__
    assert ConfigSource in CallableConfig.__mro__
    assert ServicesListing in OwnedServicesListing.__mro__


def test_the_package_exports_the_api_and_the_legacy_names_only() -> None:
    legacy = {"CLIP_LESSON", "CLIP_NOTE", "DIGEST_CASES", "DIGEST_CHARS", "MAX_VERDICTS", "case_of", "case_total", "cases", "playbook_timeline",
              "prompt_sections", "reflection_digest", "services_text"}
    assert set(reflection.__all__) == set(api.__all__) | legacy and all(hasattr(reflection, n) for n in reflection.__all__)


def test_the_api_names_what_the_ports_return() -> None:
    assert {"Case", "Verdict", "Stats", "summarize", "stats_by_version", "version_at", "lessons_of"} <= set(api.__all__)
