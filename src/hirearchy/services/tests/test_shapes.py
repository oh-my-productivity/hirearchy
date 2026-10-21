"""The classes of ``services`` implement the interfaces they are known by (the ports of the api, and the collaborators among them)."""

from __future__ import annotations

import pytest

from hirearchy.dispatch import ReworkContext
from hirearchy.kernel import OrgError
from hirearchy.services import (
    EVIDENCE_ID_MAX,
    EVIDENCE_MAX,
    LINK_HEADER,
    LINKS_MAX,
    ContractNormalizer,
    ServiceCatalog,
    ServiceCommands,
    ServiceEvidence,
    ServiceHints,
    ServiceStore,
    normalize_evidence,
    normalize_links,
)
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
from hirearchy.services.testing import AdmittingServiceEvidence, MemoryServiceStore, RefusingServiceEvidence


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


def test_the_stand_ins_for_the_gate_are_known_by_their_interface() -> None:
    assert issubclass(AdmittingServiceEvidence, ServiceEvidence) and issubclass(RefusingServiceEvidence, ServiceEvidence)


# ------------------------------------------------------------------------------ the ids of evidence and links

P1 = (
    "evidence is a list of at most 20 ids, each 1-80 characters without spaces: the regression assertions (R<k>), criteria (C<k>), verdict ids and "
    "case ids this revision rests on (see the regression list and the digest in your prompt). Pass [] only for the first playbook, or to restore "
    "unchanged a version your parent wrote."
)
F3 = (
    "criterion is 1-5 ids: C<k> (a criterion of the contract, see `services`), R<k> (an earlier rejection this one repeats) or none (the client "
    'said there is no lasting rule), e.g. ["C6"]. Not understood: {items}'
)
F4 = "none stands alone: it records that the client said this rejection is no lasting rule."
MESSAGE_ID = "20260101T000000000001-root-aB3d"


def test_the_limits_of_the_ids() -> None:
    assert (EVIDENCE_MAX, EVIDENCE_ID_MAX, LINKS_MAX) == (20, 80, 5)


def test_the_link_header_says_it_is_for_reflection_only() -> None:
    assert LINK_HEADER.format(confirms="X1") == (
        "The client says what their rejection X1 was about, for reflection only: it does not change any task's acceptance criteria or outcome."
    )


def test_normalize_evidence_strips_upper_cases_and_drops_blanks_and_duplicates() -> None:
    assert normalize_evidence([" r1 ", "c2", "", "   ", "R1", MESSAGE_ID, "c2", "cx1", "c10"]) == ("R1", "C2", MESSAGE_ID, "cx1", "C10")
    assert normalize_evidence([]) == () and normalize_evidence(("c1",)) == ("C1",) and normalize_evidence([" ", ""]) == ()
    assert normalize_evidence(["x" * EVIDENCE_ID_MAX]) == ("x" * EVIDENCE_ID_MAX,)
    assert len(normalize_evidence([f"R{i}" for i in range(EVIDENCE_MAX)])) == EVIDENCE_MAX


@pytest.mark.parametrize(
    "bad",
    [
        pytest.param("R1", id="a bare string"), pytest.param(None, id="none"), pytest.param(5, id="a number"),
        pytest.param([1], id="a number in the list"), pytest.param(["R1", None], id="none in the list"),
        pytest.param([f"R{i}" for i in range(EVIDENCE_MAX + 1)], id="more than 20"),
        pytest.param(["x" * (EVIDENCE_ID_MAX + 1)], id="a long id"), pytest.param(["R 1"], id="a spaced id"),
        pytest.param(["R1", "two words"], id="a spaced id after a good one"),
    ],
)
def test_normalize_evidence_refuses_more_than_20_or_a_long_or_spaced_id_with_p1(bad: object) -> None:
    with pytest.raises(OrgError) as e:
        normalize_evidence(bad)
    assert str(e.value) == P1


def test_normalize_links_strips_upper_cases_and_drops_blanks_and_duplicates() -> None:
    assert normalize_links([" c6", "r2 ", "", "C6", "c7"]) == ("C6", "R2", "C7")
    assert normalize_links([" None "]) == ("none",) and normalize_links(["NONE", "none"]) == ("none",)
    assert normalize_links(None) == () and normalize_links([]) == () and normalize_links(["", " "]) == ()
    assert normalize_links(["c1", "c2", "c3", "c4", "c5"]) == ("C1", "C2", "C3", "C4", "C5")


def test_normalize_links_refuses_a_bad_shape_with_f3_and_none_with_another_id_with_f4() -> None:
    for bad, items in (
        (["C6", "x"], "x"), (["c"], "c"), (["R"], "R"), (["Cx", "6"], "Cx, 6"), (["C1", "C2", "C3", "C4", "C5", "C6"], "C6"),
        ("C6", "C6"), (5, "5"),
    ):
        with pytest.raises(OrgError) as e:
            normalize_links(bad)
        assert str(e.value) == F3.format(items=items)
    for mixed in (["none", "C1"], ["r2", "NONE"]):
        with pytest.raises(OrgError) as e:
            normalize_links(mixed)
        assert str(e.value) == F4
