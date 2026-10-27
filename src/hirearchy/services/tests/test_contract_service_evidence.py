"""Contract of ``ServiceEvidence``: what the history of a service proves, for the ids a client's verdict may name and for a playbook item.

Every implementation is built over an organization where ``ceo`` offers ``weekly-brief`` with two criteria (``C1``, ``C2``) and no case yet. What the
callers rely on: ``admit_item`` returns rule ``b`` or ``c`` with the ids that make its ``why``, or raises an ``OrgError`` (never anything else); the
ids come back normalized."""

from __future__ import annotations

from pathlib import Path

import pytest

from hirearchy.kernel import OrgError
from hirearchy.services import Admission, AmendmentBasis, ItemWatch, Rejection, ServiceEvidence
from hirearchy.services.testing import IMPLEMENTATIONS, AdmittingServiceEvidence, RefusingServiceEvidence

from ._support import implementations

OWNER, SERVICE = "ceo", "weekly-brief"


@pytest.fixture(params=implementations(IMPLEMENTATIONS[ServiceEvidence]))
def evidence(request: pytest.FixtureRequest, tmp_path: Path) -> ServiceEvidence:
    made = request.param(tmp_path)
    assert isinstance(made, ServiceEvidence)
    return made


@pytest.mark.parametrize("kind", ["step", "rule"])
def test_admit_item_returns_the_ids_normalized(evidence: ServiceEvidence, kind: str) -> None:
    """Whatever the gate says, an admission carries the cited ids in their fixed form: stripped, upper-cased, once."""
    try:
        got = evidence.admit_item(OWNER, SERVICE, [" c1 ", "C2", "c1"], "why", kind=kind, text="A new line", when=None)
    except OrgError as refusal:
        assert str(refusal)
    else:
        assert got.evidence == ("C1", "C2")


def test_admit_item_with_no_evidence_is_admitted_or_refused_never_exempt(evidence: ServiceEvidence) -> None:
    """The exemptions (the first version, a move, a retire, a formatting fix) are `services`' own: the gate never returns them."""
    try:
        got = evidence.admit_item(OWNER, SERVICE, [], "why", kind="step", text="A new line", when=None)
    except OrgError as refusal:
        assert str(refusal)
    else:
        assert got.rule in ("b", "c") and got.evidence == ()


def test_admit_item_returns_rule_b_or_c_with_a_why_or_raises_an_org_error(evidence: ServiceEvidence) -> None:
    """One item is judged (design 6.2): a gate that admits returns the rule, the normalized ids, a detail line and the ``why`` ids the runtime writes."""
    for kind, text, when in (("step", "A new step", None), ("rule", "cite the source", "a claim has none")):
        try:
            got = evidence.admit_item(OWNER, SERVICE, ["c1"], "why", kind=kind, text=text, when=when)
        except OrgError as refusal:
            assert str(refusal)
        else:
            assert isinstance(got, Admission) and got.rule in ("b", "c") and got.evidence == ("C1",) and got.detail
            assert isinstance(got.why, tuple) and got.why and all(isinstance(x, str) and x[:1] in "RC" for x in got.why)


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


def test_the_admitting_stand_in_admits_an_item_with_a_why_and_the_refusing_one_refuses_it() -> None:
    got = AdmittingServiceEvidence().admit_item(OWNER, SERVICE, ["r2", "C1", "r2"], "why", kind="step", text="A new step", when=None)
    assert (got.rule, got.evidence, got.why) == ("b", ("R2", "C1"), ("R2", "C1"))
    assert AdmittingServiceEvidence().admit_item(OWNER, SERVICE, [], "why", kind="step", text="A new step", when=None).why == ("R1",)
    with pytest.raises(OrgError, match="^no thanks$"):
        RefusingServiceEvidence("no thanks").admit_item(OWNER, SERVICE, ["R1"], "why", kind="step", text="A new step", when=None)


def test_the_stand_in_hands_back_the_watch_it_was_given() -> None:
    given = (ItemWatch("P1", "step", "kept", 1), ItemWatch("P2", "rule", "warning", 2, related=("R1",)))
    assert AdmittingServiceEvidence(watch=given).watch(OWNER, SERVICE) == given
    assert AdmittingServiceEvidence().watch(OWNER, SERVICE) == ()
