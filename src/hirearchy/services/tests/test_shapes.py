"""The classes of ``services`` implement the interfaces they are known by (the ports of the api, and the collaborators among them)."""

from __future__ import annotations

from hirearchy.dispatch import ReworkContext
from hirearchy.services import ContractNormalizer, ServiceCatalog, ServiceCommands, ServiceHints, ServiceStore
from hirearchy.services._amend import ContractAmender
from hirearchy.services._catalog import ContractServiceCatalog
from hirearchy.services._commands import RuleServiceCommands
from hirearchy.services._define import RuleContractDefiner
from hirearchy.services._feedback import RuleClientFeedback
from hirearchy.services._hints import ServiceReportHints
from hirearchy.services._normalizer import TextContractNormalizer
from hirearchy.services._places import OrgServicePlaces
from hirearchy.services._playbook import RulePlaybookReviser
from hirearchy.services._protocols import (
    ClientFeedback,
    ContractAmendment,
    ContractDefinitions,
    OwnerAddresses,
    PlaybookRevisions,
    PlaybookTexts,
    PlaybookWriter,
    RequestBodies,
    ServicePlaces,
    ServiceRequests,
    ServiceRetirement,
)
from hirearchy.services._request import RuleServiceRequester, TextRequestBodies
from hirearchy.services._retire import RuleServiceRetirement
from hirearchy.services._rework import ServiceReworkContext
from hirearchy.services._store import FsServiceStore
from hirearchy.services._texts import CappedPlaybookTexts, DirectReportOwners, EventedPlaybookWriter
from hirearchy.services.testing import MemoryServiceStore


def test_the_real_classes_are_known_by_their_interfaces() -> None:
    assert issubclass(FsServiceStore, ServiceStore)
    assert issubclass(ContractServiceCatalog, ServiceCatalog)
    assert issubclass(RuleServiceCommands, ServiceCommands)
    assert issubclass(ServiceReportHints, ServiceHints)
    assert issubclass(TextContractNormalizer, ContractNormalizer)
    assert issubclass(ServiceReworkContext, ReworkContext)


def test_the_parts_of_the_commands_are_known_by_their_interfaces() -> None:
    assert issubclass(RuleContractDefiner, ContractDefinitions)
    assert issubclass(RuleServiceRetirement, ServiceRetirement)
    assert issubclass(RulePlaybookReviser, PlaybookRevisions)
    assert issubclass(RuleServiceRequester, ServiceRequests)
    assert issubclass(RuleClientFeedback, ClientFeedback)


def test_the_small_rules_among_them_are_known_by_their_interfaces() -> None:
    assert issubclass(ContractAmender, ContractAmendment)
    assert issubclass(TextRequestBodies, RequestBodies)
    assert issubclass(OrgServicePlaces, ServicePlaces)
    assert issubclass(DirectReportOwners, OwnerAddresses)
    assert issubclass(CappedPlaybookTexts, PlaybookTexts)
    assert issubclass(EventedPlaybookWriter, PlaybookWriter)


def test_the_fake_is_known_by_its_interface() -> None:
    assert issubclass(MemoryServiceStore, ServiceStore)
