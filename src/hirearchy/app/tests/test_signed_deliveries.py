"""``CaseSignedDeliveries``: reflection's deliveries and typed escapes, converted for health, which may not import ``reflection`` (design 10, I5).

The first two tests convert values; the others run over a real organization on disk: the services world of E3's chain (a lead that offers a service, a
writer and a reviewer under it, the reviewer signing every delivery off, root judging them)."""

from __future__ import annotations

from pathlib import Path

import pytest

from hirearchy.app import Org
from hirearchy.app._signed_deliveries import CaseSignedDeliveries
from hirearchy.health._ports import Signed, SignedDelivery, SignedDeliveries
from hirearchy.kernel import ROOT, Message
from hirearchy.reflection import Cause, Delivery, OwnerDeliveries, Verdict
from hirearchy.reflection.testing import FixedCaseRecords

SERVICE = "weekly-memo"
LEAD, WRITER, REVIEWER = "lead", "lead/writer", "lead/reviewer"


def task(n: int) -> Message:
    return Message(id=f"20261021T15{n:02d}00000000-root-{n:04d}", sender=ROOT, to=LEAD, type="task", title="Memo", body="goal", service=SERVICE)


def delivery(n: int, signer: str, *kinds: str) -> Delivery:
    """The delivery of request ``n``, signed off by ``signer``, with one human-tier verdict per kind."""
    request = task(n)
    result = Message(id=f"20261021T15{n:02d}30000000-lead-{n:04d}", sender=LEAD, to=ROOT, type="result", title="re", body="b", reply_to=request.id, status="done")
    verdicts = tuple(
        Verdict(kind, "words", None, request.id, 0, Message(id=f"20261021T15{n:02d}4{i}000000-root-{n:04d}", sender=ROOT, to=LEAD, type="note", title="f", body="words", feedback=kind, reply_to=request.id, source="human"))
        for i, kind in enumerate(kinds)
    )
    return Delivery(request.id, request, result, 0, signer, verdicts)


def convert(*pairs: tuple[Delivery, Cause | None], unknown: str = "") -> Signed:
    found = OwnerDeliveries(tuple(d for d, _ in pairs), tuple(c for _, c in pairs), unknown)
    return CaseSignedDeliveries(FixedCaseRecords(deliveries={LEAD: found})).deliveries(LEAD)


def test_case_signed_deliveries_converts_with_reflections_attribution() -> None:
    converter = CaseSignedDeliveries(FixedCaseRecords())
    assert isinstance(converter, SignedDeliveries) and converter.deliveries(LEAD) == Signed((), "")  # an owner with no delivery has none
    signed = convert(
        (delivery(1, REVIEWER, "accept"), None),
        (delivery(2, REVIEWER, "reject"), Cause("reviewer-miss", "link")),
        (delivery(3, WRITER, "reject"), Cause("untyped", "none")),
        (delivery(4, REVIEWER, "reject"), Cause("contract-gap", "words", ("always",))),
        (delivery(5, LEAD, "reject"), Cause("relayed-error", "relayed task", ("t",))),
        (delivery(6, LEAD, "reject"), Cause("relayed-carry-over", "carry-over", ("t", "a.md"))),
        (delivery(7, LEAD), None),
        unknown="x: y",
    )
    assert signed.unknown == "x: y"
    assert signed.items == (
        SignedDelivery(REVIEWER, True, False, True, ""),  # accepted: judged, no escape, no cause
        SignedDelivery(REVIEWER, True, True, True, "reviewer-miss"),
        SignedDelivery(WRITER, True, True, True, "untyped"),
        SignedDelivery(REVIEWER, True, True, False, "contract-gap"),  # not its
        SignedDelivery(LEAD, True, True, False, "relayed-error"),
        SignedDelivery(LEAD, True, True, False, "relayed-carry-over"),
        SignedDelivery(LEAD, False, False, True, ""),  # no verdict: not judged
    )


def test_a_reject_followed_by_an_accept_converts_to_an_escape() -> None:
    signed = convert((delivery(1, REVIEWER, "reject", "accept"), Cause("untyped", "none")))
    assert signed.items == (SignedDelivery(REVIEWER, True, True, True, "untyped"),)


# ------------------------------------------------------------------------------------------------------------------------ over files


@pytest.fixture
def org(tmp_path: Path) -> Org:
    """root -> lead (offers `weekly-memo`) -> writer, reviewer."""
    made = Org.init(tmp_path / "org", "Mission.", {"poll_seconds": 0.05})
    made.hire(ROOT, LEAD, "Lead", "Run the memos.", can_hire=True, max_children=2)
    made.hire(LEAD, "writer", "Writer", "Write.")
    made.hire(LEAD, "reviewer", "Reviewer", "Check.")
    made.define_service(
        ROOT, LEAD, SERVICE, description="A memo.", inputs=[{"name": "topic", "description": "what", "required": True}],
        acceptance=["At most 600 words", "Every claim has a source"], deliverable={"description": "one markdown file"}, budget=15,
    )
    return made


def run(org: Org, addr: str, task_id: str, status: str = "done") -> None:
    org.begin_run(addr)
    org.start_run_log(addr)
    org.report(addr, task_id, status, "Done.", lessons="Worked.")
    org.end_run(addr, ok=True)


def delivered(org: Org, n: int) -> Message:
    """One request, the way E3's chain went: the lead has the writer draft, has the reviewer pass it, and reports ``done``; the reviewer signed it off."""
    request = org.request(ROOT, SERVICE, {"topic": f"t{n}"})
    org.begin_run(LEAD)
    draft = org.delegate(LEAD, WRITER, "Draft", "goal", "criteria", budget=2)
    run(org, WRITER, draft.id)
    check = org.delegate(LEAD, REVIEWER, "Check", "goal", "criteria", budget=2)
    run(org, REVIEWER, check.id)
    org.start_run_log(LEAD)
    org.report(LEAD, request.id, "done", "Delivered.", lessons="Worked.")
    org.end_run(LEAD, ok=True)
    return request


def test_e3_files_give_lead_reviewer_0_of_5_with_2_not_its(org: Org) -> None:
    requests = [delivered(org, n) for n in range(5)]
    org.feedback(ROOT, requests[0].id, "reject", "Always put the summary line first.", source="human")  # a lasting word: the contract's gap
    org.feedback(ROOT, requests[1].id, "reject", "Never cite a blog.", source="human")
    for each in requests[2:]:
        org.feedback(ROOT, each.id, "accept", source="human")
    signed = CaseSignedDeliveries(org.runtime.case_records).deliveries(LEAD)
    assert [d.signer for d in signed.items] == [REVIEWER] * 5 and signed.unknown == ""
    assert [(d.judged, d.escape, d.counted, d.cause) for d in signed.items] == [
        (True, True, False, "contract-gap"), (True, True, False, "contract-gap"), (True, False, True, ""), (True, False, True, ""), (True, False, True, ""),
    ]
    counts = org.runtime.health_analyzer.agent_health(REVIEWER)
    assert (counts.escapes, counts.judged, counts.not_its, counts.causes_unknown) == (0, 5, {"contract-gap": 2}, "")


def test_an_unreadable_contract_is_untyped_and_unknown(org: Org) -> None:
    request = delivered(org, 0)
    org.feedback(ROOT, request.id, "reject", "Always put the summary line first.", source="human")
    (org.root / LEAD / "services" / SERVICE / "SERVICE.md").write_text("---\nkey: [unclosed\n---\n", encoding="utf-8")
    signed = CaseSignedDeliveries(org.runtime.case_records).deliveries(LEAD)
    (item,) = signed.items
    assert item == SignedDelivery(REVIEWER, True, True, True, "untyped")  # the conservative side: the escape stays in the verifier's count
    assert signed.unknown.startswith(f"{SERVICE}: SERVICE.md: does not parse (")
    counts = org.runtime.health_analyzer.agent_health(REVIEWER)
    assert (counts.escapes, counts.judged, counts.not_its) == (1, 1, {}) and counts.causes_unknown == signed.unknown
