"""Contract of ``ServiceEvidence``: what the history of a service proves, for the ids a client's verdict may name and for a playbook revision.

Every implementation is built over an organization where ``ceo`` offers ``weekly-brief`` with two criteria (``C1``, ``C2``) and no case yet. What the
callers rely on: an exempt ``admit`` only resolves the ids and returns the exemption; any other ``admit`` returns rule ``b`` or ``c`` or raises an
``OrgError`` (never anything else); the ids come back normalized."""

from __future__ import annotations

from pathlib import Path

import pytest

from hirearchy.kernel import OrgError
from hirearchy.services import Admission, AmendmentBasis, ItemWatch, Rejection, ServiceEvidence
from hirearchy.services.testing import IMPLEMENTATIONS, AdmittingServiceEvidence

from ._support import implementations

OWNER, SERVICE = "ceo", "weekly-brief"


@pytest.fixture(params=implementations(IMPLEMENTATIONS[ServiceEvidence]))
def evidence(request: pytest.FixtureRequest, tmp_path: Path) -> ServiceEvidence:
    made = request.param(tmp_path)
    assert isinstance(made, ServiceEvidence)
    return made


@pytest.mark.parametrize("exempt", ["first", "restore"])
def test_an_exempt_admit_returns_the_exemption_with_normalized_ids(evidence: ServiceEvidence, exempt: str) -> None:
    got = evidence.admit(OWNER, SERVICE, [" c1 ", "C2", "c1"], "why", exempt=exempt)
    assert isinstance(got, Admission) and (got.rule, got.evidence) == (exempt, ("C1", "C2"))


@pytest.mark.parametrize("exempt", ["first", "restore"])
def test_an_exempt_admit_with_no_evidence_returns_the_exemption(evidence: ServiceEvidence, exempt: str) -> None:
    got = evidence.admit(OWNER, SERVICE, [], "why", exempt=exempt)
    assert (got.rule, got.evidence) == (exempt, ())


def test_admit_returns_rule_b_or_c_or_raises_an_org_error(evidence: ServiceEvidence) -> None:
    try:
        got = evidence.admit(OWNER, SERVICE, ["c1"], "why")
    except OrgError as refusal:
        assert str(refusal)
    else:
        assert isinstance(got, Admission) and got.rule in ("b", "c") and got.evidence == ("C1",) and got.detail


def test_admit_accepts_lines(evidence: ServiceEvidence) -> None:
    """The changed lines of a revision (P1): a gate that admits returns, with each line, the id that admits it; an exempt one ignores them."""
    lines = ["A new line", "Another one"]
    try:
        got = evidence.admit(OWNER, SERVICE, ["c1"], "why", lines=lines)
    except OrgError as refusal:
        assert str(refusal)
    else:
        assert got.rule in ("b", "c") and all(isinstance(i, str) and line in lines for i, line in got.lines)
    assert evidence.admit(OWNER, SERVICE, [], "why", exempt="first", lines=lines).lines == ()


def test_links_returns_normalized_ids_or_raises(evidence: ServiceEvidence) -> None:
    try:
        got = evidence.links(OWNER, SERVICE, ["c2", "C1", "c2"])
    except OrgError as refusal:
        assert str(refusal)
    else:
        assert got == ("C2", "C1")


def test_links_accepts_none_alone(evidence: ServiceEvidence) -> None:
    assert evidence.links(OWNER, SERVICE, ["None"], verdict="20260101T000000000001-root-0001") == ("none",)


def test_confirmed_is_a_frozenset_of_criterion_ids(evidence: ServiceEvidence) -> None:
    got = evidence.confirmed(OWNER, SERVICE)
    assert isinstance(got, frozenset) and all(isinstance(x, str) and x.startswith("C") for x in got)


def test_amendment_basis_of_a_service_without_cases_is_empty(evidence: ServiceEvidence) -> None:
    """No request yet: no rejection to answer and no delivery without a verdict (0a.2 adds no division: the empty case is the zero case)."""
    got = evidence.amendment_basis(OWNER, SERVICE)
    assert isinstance(got, AmendmentBasis) and got.rejections == () and got.unrated == ()


def test_a_basis_rejection_carries_its_case(evidence: ServiceEvidence) -> None:
    """Every rejection of the basis names its case (the id of the case's first task); a rejection built without one has the empty default, and the
    stand-in that is given a basis hands it back with the case it was given."""
    assert Rejection("n1", "R1", "t1", "title", (), "words", "").case == ""
    assert all(rejection.case for rejection in evidence.amendment_basis(OWNER, SERVICE).rejections)
    given = AmendmentBasis((Rejection("n1", "R1", "t1", "title", (), "words", "", case="t0"),), ())
    assert AdmittingServiceEvidence(basis=given).amendment_basis(OWNER, SERVICE).rejections[0].case == "t0"


def test_watch_of_a_service_without_a_playbook_is_empty(evidence: ServiceEvidence) -> None:
    """No playbook yet: no item to watch (8.7). A service nobody defined has none either."""
    assert evidence.watch(OWNER, SERVICE) == ()
    assert evidence.watch(OWNER, "no-such-service") == ()


def test_watch_gives_one_item_watch_per_item(evidence: ServiceEvidence) -> None:
    """Whatever the service has, the watch is a tuple of ``ItemWatch``, one per item id, by number."""
    found = evidence.watch(OWNER, SERVICE)
    assert isinstance(found, tuple) and all(isinstance(i, ItemWatch) for i in found)
    assert [i.id for i in found] == sorted({i.id for i in found}, key=lambda x: int(x[1:]))


def test_the_stand_in_hands_back_the_watch_it_was_given() -> None:
    given = (ItemWatch("P1", "step", "kept", 1), ItemWatch("P2", "rule", "warning", 2, related=("R1",)))
    assert AdmittingServiceEvidence(watch=given).watch(OWNER, SERVICE) == given
    assert AdmittingServiceEvidence().watch(OWNER, SERVICE) == ()
