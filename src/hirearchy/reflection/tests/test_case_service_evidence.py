"""``CaseServiceEvidence``: the gate behind ``revise_playbook`` (rules (b) and (c)) and the ids a verdict may name, judged from the cases of a service.

The services suite of ``ServiceEvidence`` runs against it too (the pattern of ``services/tests/test_service_rework_context.py``), over a world
where ``ceo`` offers ``weekly-brief`` (``C1``, ``C2``, no case yet); the behaviour tests follow."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
import testkit.services_world as services_world
from testkit.services_world import svc  # noqa: F401  (a fixture: the wired application with ceo offering weekly-brief)

from hirearchy.kernel import ROOT, Message, OrgError, clip_line
from hirearchy.reflection import Case, CaseHistory, Verdict
from hirearchy.reflection._evidence import CaseServiceEvidence
from hirearchy.reflection.testing import FixedCaseHistory, ReflectionWorld, fs_world, memory_world
from hirearchy.services import Admission, ServiceEvidence

# The suite that every ``ServiceEvidence`` passes: the same functions, run against this package's implementation.
from hirearchy.services.tests.test_contract_service_evidence import (  # noqa: F401  (imported to be collected here)
    test_admit_item_returns_rule_b_or_c_with_a_why_or_raises_an_org_error,
    test_admit_item_returns_the_ids_normalized,
    test_admit_item_with_no_evidence_is_admitted_or_refused_never_exempt,
    test_a_basis_rejection_carries_its_case,
    test_amendment_basis_of_a_service_without_cases_is_empty,
    test_links_accepts_none_alone,
    test_links_returns_normalized_ids_or_raises,
    test_watch_gives_one_item_watch_per_item,
    test_watch_of_a_service_without_a_playbook_is_empty,
)

from ._support import SERVICE, amend_legacy, ask, define, deliver, legacy_playbook, nested, note_on, populated, rate, rework

CASES = "cases the client rejected"


@pytest.fixture(params=[fs_world, memory_world], ids=lambda f: f.__name__)
def w(request: pytest.FixtureRequest, tmp_path: Path) -> ReflectionWorld:
    made = populated(request.param(tmp_path))
    define(made)
    return made


@pytest.fixture
def evidence(w: ReflectionWorld) -> ServiceEvidence:
    assert isinstance(w.evidence, CaseServiceEvidence)
    return w.evidence


def rejected(w: ReflectionWorld, words: str = "Too long.", *, topic: str = "ai", source: str = "human", **kw: str) -> tuple[Message, Message]:
    """A new case: the request, its delivery and the client's rejection; returns (request, verdict). A human ``criterion=...`` is the user's yes,
    so it is recorded as a ``confirms`` link note after the verdict (the verdict's own criterion would be relayed tier); a relayed or agent one
    stays on the verdict."""
    task = ask(w, topic)
    deliver(w, task)
    own = {} if source == "human" else kw
    verdict = note_on(w, task, verdict="reject", source=source, body=words, **own)
    if source == "human" and "criterion" in kw:
        note_on(w, task, reply_to=verdict.id, source="human", criterion=kw["criterion"])
    return task, verdict


def amend(w: ReflectionWorld, **over: Any) -> None:
    """Root's amendment as a contract version was written before 0a.2 (no basis): the legacy rule is what these tests are about. The amendments
    of today carry the user's words: ``test_a_user_initiated_amendment_is_never_rule_c_eligible`` and the answered ones are tested apart."""
    amend_legacy(w, **over)


def admit(
    evidence: ServiceEvidence, ids: list[str], text: str = "Anything the team writes.", *, owner: str = "ceo", service: str = SERVICE, reason: str = "why",
    kind: str = "step", when: str | None = None,
) -> Admission:
    """One item (design 6.2) offered to the gate: a step with these words, unless ``kind`` and ``when`` say a rule."""
    return evidence.admit_item(owner, service, ids, reason, kind=kind, text=text, when=when)


def refusal(
    evidence: ServiceEvidence, ids: list[str], reason: str = "why", owner: str = "ceo", service: str = SERVICE, text: str = "Anything the team writes.",
) -> str:
    with pytest.raises(OrgError) as e:
        admit(evidence, ids, text, owner=owner, service=service, reason=reason)
    return str(e.value)


def triple(got: Admission) -> tuple[str, tuple[str, ...], str]:
    return got.rule, got.evidence, got.detail


# ------------------------------------------------------------------------------ G0 and G3


def test_g0_names_every_kind_of_unknown_id_and_lists_the_valid_ones(w: ReflectionWorld, evidence: ServiceEvidence) -> None:
    assert refusal(evidence, ["C9", "R1", "nonsense"]) == (
        "unknown evidence for `weekly-brief`: C9, R1, nonsense. Evidence is a criterion (C1, C2), a regression assertion (none yet), or the "
        "id of a verdict or a case of this service: see the regression list and the digest in your prompt. Nothing was written."
    )
    rejected(w)
    assert refusal(evidence, ["R2", "c3", "x"]) == (
        "unknown evidence for `weekly-brief`: R2, C3, x. Evidence is a criterion (C1, C2), a regression assertion (R1), or the "
        "id of a verdict or a case of this service: see the regression list and the digest in your prompt. Nothing was written."
    )


def test_g0_names_the_unknown_id_before_it_judges_the_item(w: ReflectionWorld, evidence: ServiceEvidence) -> None:
    with pytest.raises(OrgError, match="^unknown evidence for `weekly-brief`: R4"):
        admit(evidence, ["R4"])


def test_g3_refuses_any_revision_for_an_agent_client(w: ReflectionWorld, evidence: ServiceEvidence) -> None:
    nested(w)
    cited = evidence
    message = refusal(cited, ["C1"], owner="ceo/eng", service="inner")
    assert message == (
        "refused: the client of `inner` is ceo, an agent, so its verdicts are hypotheses and nothing in this service's history can admit a "
        "revision (rules (b) and (c) need the human client). Nothing was written. Follow the playbook and the contract; if you think the "
        "playbook must change, send ceo (`send`) what you would change and why."
    )
    assert refusal(cited, [], owner="ceo/eng", service="inner") == message
    with pytest.raises(OrgError, match="^unknown evidence for `inner`: R1"):
        admit(cited, ["R1"], owner="ceo/eng", service="inner")


# ------------------------------------------------------------------------------ rule (b)


def test_b_admits_two_human_rejections_in_two_cases_linked_to_one_criterion(w: ReflectionWorld, evidence: ServiceEvidence) -> None:
    first, _ = rejected(w, "No source.", criterion="C2")
    second, _ = rejected(w, "Still no source.", topic="b", criterion="C2")
    expected = f"C2 failed in 2 {CASES}: {first.id}, {second.id}"
    assert triple(admit(evidence, ["c2"])) == ("b", ("C2",), expected)
    assert triple(admit(evidence, ["R1", "R2"])) == ("b", ("R1", "R2"), expected)
    assert triple(admit(evidence, ["R2"])) == ("b", ("R2",), expected)


def test_b_admits_through_a_link_note_the_client_gave_later(w: ReflectionWorld, evidence: ServiceEvidence) -> None:
    first, no = rejected(w, "No source.")
    note_on(w, first, reply_to=no.id, criterion="C2", source="human")
    second, _ = rejected(w, "Still none.", topic="b", criterion="C2")
    assert admit(evidence, ["C2"]).detail == f"C2 failed in 2 {CASES}: {first.id}, {second.id}"


def test_b_admits_through_the_same_as_rj(w: ReflectionWorld, evidence: ServiceEvidence) -> None:
    first, _ = rejected(w, "No source.")  # no link of its own
    second, _ = rejected(w, "Same as before.", topic="b", criterion="R1")
    assert triple(admit(evidence, ["R1"])) == ("b", ("R1",), f"R1 failed in 2 {CASES}: {first.id}, {second.id}")


def test_b_resolves_the_same_as_rj_to_the_criterion_of_rj(w: ReflectionWorld, evidence: ServiceEvidence) -> None:
    first, _ = rejected(w, "No source.", criterion="C2")
    second, _ = rejected(w, "Same as before.", topic="b", criterion="R1")
    assert triple(admit(evidence, ["C2"])) == ("b", ("C2",), f"C2 failed in 2 {CASES}: {first.id}, {second.id}")


def test_two_rejections_in_one_case_are_one_case_g2(w: ReflectionWorld, evidence: ServiceEvidence) -> None:
    task, _ = rejected(w, "First words.", criterion="C2")
    again = rework(w, task)
    deliver(w, again)
    second = note_on(w, again, verdict="reject", source="human", body="Second words.")
    note_on(w, again, reply_to=second.id, source="human", criterion="C2")
    message = refusal(evidence, ["C2"])
    assert message.startswith(f"refused: the client rejected this in one case only ({task.id}), and the evidence cites no criterion root added")
    assert f'"In case {task.id} you said: "Second words.". Is that a lasting requirement?' in message


def test_rule_b_ignores_criteria_given_on_the_verdicts(w: ReflectionWorld, evidence: ServiceEvidence) -> None:
    """A criterion on the rejection itself is relayed tier whatever its source: two such rejections in two cases are not the client's evidence."""
    for topic in ("a", "b"):
        task = ask(w, topic)
        deliver(w, task)
        note_on(w, task, verdict="reject", source="human", criterion="C2", body="No source.")
    assert refusal(evidence, ["C2"]).startswith(
        "refused: none of this evidence is the client's own: C2 is in the contract since v1, not added by an amendment, and failed in no case "
        "the client rejected. "
    )
    assert refusal(evidence, ["R1", "R2"]).startswith("refused: the client rejected this in one case only (")  # both are assertions, about nothing


# ------------------------------------------------------------------------------ what weighs nothing


def test_relayed_and_agent_rejections_weigh_nothing_g1_notes(w: ReflectionWorld, evidence: ServiceEvidence) -> None:
    _, one = rejected(w, "Relayed one.", source="relayed", criterion="C2")
    _, two = rejected(w, "Relayed two.", topic="b", source="relayed", criterion="C2")
    note = "relayed (the assistant's own reading)"
    message = refusal(evidence, [one.id, two.id], reason="Add a source line")
    assert message.startswith(f"refused: none of this evidence is the client's own: verdict {one.id} is {note}; verdict {two.id} is {note}. ")
    assert "\nIf you think the client wants this from now on, send root (`send`) this question once" in message
    accepted = ask(w, "c")
    deliver(w, accepted)
    yes = note_on(w, accepted, verdict="accept", source="human")
    assert f"verdict {yes.id} is an accept." in refusal(evidence, [yes.id])


def test_an_agent_clients_verdict_note_is_a_hypothesis(w: ReflectionWorld) -> None:
    task = ask(w)
    deliver(w, task)
    human = note_on(w, task, verdict="reject", source="human", body="x")
    case = w.history.cases("ceo", SERVICE)[0]
    agent = Verdict("reject", "y", None, task.id, 0, human, tier="agent")
    fixed: Case = replace(case, verdicts=[agent])
    cited = CaseServiceEvidence(FixedCaseHistory([fixed]), w.s.catalog, w.s.store, w.s.d.mail)
    assert f"verdict {human.id} is an agent client's (a hypothesis)." in refusal(cited, [human.id])


def test_relayed_and_agent_rejections_are_never_counted_by_a_cited_case(w: ReflectionWorld, evidence: ServiceEvidence) -> None:
    task, _ = rejected(w, "Relayed.", source="relayed", criterion="C2")
    again = rework(w, task, source="relayed")
    deliver(w, again)
    message = refusal(evidence, [task.id])
    assert f"case {task.id} has no rejection by the client; 1 of its reworks were relayed (the assistant's own reading)." in message


def test_an_unconfirmed_link_weighs_nothing(w: ReflectionWorld, evidence: ServiceEvidence) -> None:
    for topic in ("a", "b"):
        task, no = rejected(w, "Too long.", topic=topic)
        note_on(w, task, reply_to=no.id, criterion="C2", source="relayed")  # the assistant's own reading of what it was about
    message = refusal(evidence, ["C2"])
    assert message.startswith(
        "refused: none of this evidence is the client's own: C2 is in the contract since v1, not added by an amendment, and failed in no "
        "case the client rejected. "
    )


# ------------------------------------------------------------------------------ rule (c)


def test_c_admits_a_cited_amended_criterion_the_client_confirmed(w: ReflectionWorld, evidence: ServiceEvidence) -> None:
    amend(w, add_acceptance=["Names the week it covers"])
    rejected(w, "No week.", criterion="C3")  # the user's yes to the new criterion: a confirms link
    assert triple(admit(evidence, ["c3"], WEEK)) == ("c", ("C3",), "cites C3, which root added to the contract (v2) and the client confirmed")
    amend(w, add_acceptance=["Ends with one open question"])
    rejected(w, "No question.", topic="b", criterion="C4")
    assert admit(evidence, ["C3", "C4"], WEEK).detail == "cites C3, which root added to the contract (v2) and the client confirmed"  # the item is C3's words
    assert admit(evidence, ["C3", "C4"], "Ends with one open question").detail == (
        "cites C4, which root added to the contract (v3) and the client confirmed"
    )
    assert admit(evidence, ["C1", "C4"], "Ends with one open question").detail == "cites C4, which root added to the contract (v3) and the client confirmed"


def test_rule_c_admits_a_confirmed_amendment(w: ReflectionWorld, evidence: ServiceEvidence) -> None:
    amend(w, add_acceptance=["Names the week it covers", "Ends with one open question"])  # C3, C4
    rejected(w, "No week.", criterion="C3")
    assert admit(evidence, ["C3"], WEEK).detail == "cites C3, which root added to the contract (v2) and the client confirmed"
    assert "C4 was added to the contract by an amendment (v2), but the client's yes to it is not recorded (not confirmed)." in refusal(
        evidence, ["C4"],
    )  # only C3 is confirmed: citing C4 alone gets no admission
    assert admit(evidence, ["C3", "C4"], WEEK).detail == "cites C3, which root added to the contract (v2) and the client confirmed"


def test_rule_c_refuses_an_amendment_without_a_confirmation(w: ReflectionWorld, evidence: ServiceEvidence) -> None:
    amend(w, add_acceptance=["Names the week it covers"])
    task, no = rejected(w, "No week.")
    note_on(w, task, reply_to=no.id, criterion="C3", source="relayed")  # the assistant's own reading is no confirmation
    message = refusal(evidence, ["C3"])
    assert message.startswith(
        "refused: none of this evidence is the client's own: C3 was added to the contract by an amendment (v2), but the client's yes to it is not "
        "recorded (not confirmed). "
    )
    assert "(c) it is the own words of a criterion root added to the contract by an amendment the client confirmed (none yet)." in message


def test_a_user_initiated_amendment_is_never_rule_c_eligible(w: ReflectionWorld, evidence: ServiceEvidence) -> None:
    """DR-27: root amends with no rejection at all, so no `confirms` link can name the new criterion; since 0a.2 the amendment is recorded as the
    user's own request (``words`` alone), which no link confirms (``test_pure_functions`` tests a link that names it)."""
    w.s.commands.define_service("root", "ceo", SERVICE, add_acceptance=["Names the week it covers"], words="Name the week, please.")
    message = refusal(evidence, ["C3"])
    assert "C3 was added to the contract by an amendment (v2), but the client's yes to it is not recorded (not confirmed)." in message
    assert "amendment the client confirmed (none yet)." in message


def test_c_admits_an_amended_criterion_reached_through_an_assertion(w: ReflectionWorld, evidence: ServiceEvidence) -> None:
    amend(w, add_acceptance=["Names the week it covers"])
    rejected(w, "No week named.", criterion="C3")
    assert triple(admit(evidence, ["R1"], WEEK)) == ("c", ("R1",), "cites C3, which root added to the contract (v2) and the client confirmed")


def test_c_refuses_a_v1_criterion_with_its_note(w: ReflectionWorld, evidence: ServiceEvidence) -> None:
    amend(w, add_acceptance=["Names the week it covers"])
    reason = "Always give the sources first"
    assert refusal(evidence, ["C1"], reason) == (
        "refused: none of this evidence is the client's own: C1 is in the contract since v1, not added by an amendment, and failed in no case the "
        "client rejected. An item is admitted only when (b) the same criterion or regression assertion failed in 2 different cases the client "
        "rejected, or (c) it is the own words of a criterion root added to the contract by an amendment the client confirmed (none yet). Your team's lessons, relayed verdicts (the "
        "assistant's own reading) and an agent client's verdicts weigh nothing. Nothing was written: follow the playbook and the contract.\n"
        "If you think the client wants this from now on, send root (`send`) this question once, and do not wait for an answer (it reaches you as a "
        "contract change or a criterion link): \"We would change how we deliver weekly-brief: Always give the sources first. Is that what you want "
        "from now on? If yes, please add it to the contract as a criterion.\""
    )


def test_no_evidence_at_all_is_a_g1_refusal_that_says_so(w: ReflectionWorld, evidence: ServiceEvidence) -> None:
    assert refusal(evidence, []).startswith(
        "refused: none of this evidence is the client's own: no evidence given. An item is admitted only when (b) "
    )
    assert "(c) it is the own words of a criterion root added to the contract by an amendment the client confirmed (none yet)." in refusal(evidence, [])


# ------------------------------------------------------------------------------ a link-note id is evidence (F-E4-7)


def link_note(w: ReflectionWorld, source: str, criterion: str = "C3") -> tuple[Message, Message]:
    """A new case rejected by the client, then a link note of the given ``source`` naming ``criterion``; returns (verdict, link note)."""
    task = ask(w)
    deliver(w, task)
    no = note_on(w, task, verdict="reject", source="human", body="No week.")
    return no, note_on(w, task, reply_to=no.id, source=source, criterion=criterion)


def test_a_human_link_note_id_is_evidence_for_the_criteria_it_names(w: ReflectionWorld, evidence: ServiceEvidence) -> None:
    amend(w, add_acceptance=["Names the week it covers"])  # C3
    no, link = link_note(w, "human")
    admitted = admit(evidence, [link.id], WEEK)
    assert triple(admitted) == ("c", (link.id,), "cites C3, which root added to the contract (v2) and the client confirmed")
    assert admit(evidence, [no.id], WEEK).rule == "c"  # the rejection itself resolves through its human link as before


def test_a_relayed_link_note_id_weighs_nothing_and_is_noted(w: ReflectionWorld, evidence: ServiceEvidence) -> None:
    amend(w, add_acceptance=["Names the week it covers"])
    _, link = link_note(w, "relayed")
    message = refusal(evidence, [link.id])
    assert message.startswith(f"refused: none of this evidence is the client's own: link {link.id} is relayed (the assistant's own reading). ")


def test_an_unknown_id_is_still_unknown_evidence(w: ReflectionWorld, evidence: ServiceEvidence) -> None:
    amend(w, add_acceptance=["Names the week it covers"])
    link_note(w, "human")
    other = "20990101T000000000000-root-0000"
    assert refusal(evidence, [other]).startswith(f"unknown evidence for `weekly-brief`: {other}. Evidence is a criterion (")


# ------------------------------------------------------------------------------ item by item (design 5.4: P1's line stage, folded in)

WEEK = "Names the week it covers"


def confirmed_c3(w: ReflectionWorld) -> None:
    """C3 (``WEEK``) is added by an amendment and the user's yes to it is recorded."""
    amend(w, add_acceptance=[WEEK])
    rejected(w, "No week.", criterion="C3")


def failed_twice(w: ReflectionWorld, criterion: str = "C2") -> tuple[Message, Message]:
    """``criterion`` failed in two cases the client rejected (rule (b)); returns the two requests."""
    first, _ = rejected(w, "No source.", criterion=criterion)
    second, _ = rejected(w, "Still none.", topic="b", criterion=criterion)
    return first, second


def test_rule_c_admits_only_the_cited_criterions_words(w: ReflectionWorld, evidence: ServiceEvidence) -> None:
    confirmed_c3(w)
    detail = "cites C3, which root added to the contract (v2) and the client confirmed"
    for words in (WEEK, f"C3: {WEEK}", f"{WEEK} (C3)", f"- C3: {WEEK}"):
        assert triple(admit(evidence, ["C3"], words)) == ("c", ("C3",), detail)  # with or without its id: the item's WHY names it anyway


def test_rule_c_refuses_an_elaboration_of_the_cited_criterion(w: ReflectionWorld, evidence: ServiceEvidence) -> None:
    confirmed_c3(w)
    message = refusal(evidence, ["C3"], text=f"{WEEK}, in ISO format")
    assert message.startswith("refused: C3 is confirmed by the client, so an item citing it may be only its own words: this item is not.")
    assert f'Write it as a step with text "{WEEK}" (or a rule with then "{WEEK}" and no when) to add C3.' in message


def test_a_criterion_with_an_empty_key_admits_no_c_item(w: ReflectionWorld, evidence: ServiceEvidence) -> None:
    amend(w, add_acceptance=["???"])  # C3: no letter or digit, so its key is empty
    rejected(w, "No marks.", criterion="C3")
    for words in ("C3", "???", "- C3: ???"):
        message = refusal(evidence, ["C3"], text=words)
        assert message.startswith("refused: C3 is confirmed by the client, so an item citing it may be only its own words: this item is not.")
        assert "Write it as a step" not in message  # there is no way to write it: an empty key is no words


def test_rule_b_admits_any_words_the_runtime_writes_the_why(w: ReflectionWorld, evidence: ServiceEvidence) -> None:
    failed_twice(w)
    got = admit(evidence, ["C2"], "Cite a URL for every claim")
    assert got.rule == "b" and got.why == ("R1", "R2", "C2")  # no tag in the words: the WHY is the runtime's


def test_a_cited_assertion_reaches_its_about_in_the_why(w: ReflectionWorld, evidence: ServiceEvidence) -> None:
    failed_twice(w)
    assert admit(evidence, ["R2"], "Cite a URL for every claim").why == ("R1", "R2", "C2")  # R2 is about C2: C2 qualifies, and so do both rejections


def test_g1_and_g2_are_the_same_whatever_the_words(w: ReflectionWorld, evidence: ServiceEvidence) -> None:
    assert refusal(evidence, ["C1"], text="a line") == refusal(evidence, ["C1"])  # G1: no client evidence
    rejected(w, "First words.", criterion="C2")
    one_case = refusal(evidence, ["R1"])
    assert one_case.startswith("refused: the client rejected this in one case only (") and refusal(evidence, ["R1"], text="a line") == one_case


# ------------------------------------------------------------------------------ criteria the client removed


def test_a_cited_removed_criterion_adds_no_subject_and_says_so(w: ReflectionWorld, evidence: ServiceEvidence) -> None:
    amend(w, add_acceptance=["Names the week it covers"])
    amend(w, remove_acceptance=["Names the week it covers"])
    message = refusal(evidence, ["C3"])
    assert "C3 is no longer in the contract: cite a current criterion (see `services`)." in message
    assert "(c) it is the own words of a criterion root added to the contract by an amendment the client confirmed (none yet)." in message


def test_two_rejections_linked_only_to_a_removed_criterion_do_not_admit(w: ReflectionWorld, evidence: ServiceEvidence) -> None:
    amend(w, add_acceptance=["Names the week it covers"])
    rejected(w, "No week.", criterion="C3")
    rejected(w, "Still no week.", topic="b", criterion="C3")
    assert admit(evidence, ["C3"], WEEK).rule == "c"  # while the criterion is in the contract, the amendment admits it
    amend(w, remove_acceptance=["Names the week it covers"])
    assert "C3 is no longer in the contract" in refusal(evidence, ["C3"])
    message = refusal(evidence, ["R1", "R2"])
    assert message.startswith("refused: the client rejected this in one case only (")
    assert 'a new one, or a clarification of an existing one?" Add the item when the answer is in the contract' in message


# ------------------------------------------------------------------------------ ids that resolve to something else


def test_a_cited_case_resolves_to_its_human_rejections(w: ReflectionWorld, evidence: ServiceEvidence) -> None:
    first, _ = rejected(w, "No source.", criterion="C2")
    second, _ = rejected(w, "Still none.", topic="b", criterion="C2")
    assert triple(admit(evidence, [first.id, second.id])) == ("b", (first.id, second.id), f"C2 failed in 2 {CASES}: {first.id}, {second.id}")
    again = rework(w, second)  # any task of the chain names the case
    assert admit(evidence, [first.id, again.id]).rule == "b"


def test_a_cited_verdict_id_resolves_to_its_assertion(w: ReflectionWorld, evidence: ServiceEvidence) -> None:
    _, one = rejected(w, "No source.", criterion="C2")
    _, two = rejected(w, "Still none.", topic="b", criterion="C2")
    assert admit(evidence, [one.id, two.id]).rule == "b"


def test_a_case_without_a_rejection_is_a_g1_note(w: ReflectionWorld, evidence: ServiceEvidence) -> None:
    task = ask(w)
    deliver(w, task)
    assert f"case {task.id} has no rejection by the client." in refusal(evidence, [task.id])


def test_a_result_id_gives_the_lessons_note(w: ReflectionWorld, evidence: ServiceEvidence) -> None:
    task = ask(w)
    result = deliver(w, task, lessons="Always cite sources first.")
    assert f"{result.id} is a result: its lessons are your team's view." in refusal(evidence, [result.id])


# ------------------------------------------------------------------------------ the questions


def test_g1_question_carries_the_reason_clipped_to_200(w: ReflectionWorld, evidence: ServiceEvidence) -> None:
    reason = "word " * 60
    message = refusal(evidence, ["C1"], reason)
    assert f"We would change how we deliver weekly-brief: {clip_line(reason, 200)}. Is that what you want" in message
    assert clip_line(reason, 200).endswith("…") and reason.strip() not in message


def test_g2_quotes_the_words_clipped_to_300_and_picks_the_highest_note_id(w: ReflectionWorld, evidence: ServiceEvidence) -> None:
    task, _ = rejected(w, "The first words.", criterion="C2")
    again = rework(w, task)
    deliver(w, again)
    long = "long words " * 50
    latest = note_on(w, again, verdict="reject", source="human", body=long)
    note_on(w, again, reply_to=latest.id, source="human", criterion="C2")
    message = refusal(evidence, ["C2"])
    assert f'you said: "{clip_line(long, 300)}". Is that a lasting requirement?' in message and "The first words." not in message


def test_g2_asks_about_the_current_criteria_of_the_assertion_only(w: ReflectionWorld, evidence: ServiceEvidence) -> None:
    amend(w, add_acceptance=["Names the week it covers"])
    rejected(w, "Wrong week.", criterion="C2, C3")
    amend(w, remove_acceptance=["Names the week it covers"])
    message = refusal(evidence, ["R1"])
    assert 'which criterion should say it: a new one, or a clarification of C2?" Add the item when the answer is in the contract' in message
    assert "C3" not in message.split("a new one, or a clarification of")[1]


def test_g2_asks_about_an_existing_one_when_every_linked_criterion_was_removed(w: ReflectionWorld, evidence: ServiceEvidence) -> None:
    amend(w, add_acceptance=["Names the week it covers"])
    rejected(w, "Wrong week.", criterion="C3")
    amend(w, remove_acceptance=["Names the week it covers"])
    assert "which criterion should say it: a new one, or a clarification of an existing one?\"" in refusal(evidence, ["R1"])


def test_g2_joins_several_current_criteria_with_a_slash(w: ReflectionWorld, evidence: ServiceEvidence) -> None:
    rejected(w, "Both wrong.", criterion="C1, C2")
    assert "or a clarification of C1 / C2?\"" in refusal(evidence, ["R1"])


# ------------------------------------------------------------------------------ links


def test_links_f5_names_unknown_ids_and_lists_criteria_and_assertions(w: ReflectionWorld, evidence: ServiceEvidence) -> None:
    with pytest.raises(OrgError) as e:
        evidence.links("ceo", SERVICE, ["C9", "R1", "C1"])
    assert str(e.value) == (
        "unknown criterion or assertion for `weekly-brief`: C9, R1. Its criteria: C1, C2; its regression assertions: none yet (see `services`)."
    )
    rejected(w)
    with pytest.raises(OrgError) as e:
        evidence.links("ceo", SERVICE, ["R2"])
    assert str(e.value) == (
        "unknown criterion or assertion for `weekly-brief`: R2. Its criteria: C1, C2; its regression assertions: R1 (see `services`)."
    )


def test_links_f6_refuses_the_rejection_itself(w: ReflectionWorld, evidence: ServiceEvidence) -> None:
    _, first = rejected(w, "No source.")
    _, second = rejected(w, "Same again.", topic="b")
    assert evidence.links("ceo", SERVICE, ["R1"], verdict=second.id) == ("R1",)
    with pytest.raises(OrgError) as e:
        evidence.links("ceo", SERVICE, ["C2", "R2"], verdict=second.id)
    assert str(e.value) == "R2 is this rejection itself: name the criterion it is about, or the earlier rejection it repeats."
    assert evidence.links("ceo", SERVICE, ["R2"]) == ("R2",) and first.id < second.id


def test_links_accepts_none_and_removed_criteria(w: ReflectionWorld, evidence: ServiceEvidence) -> None:
    amend(w, add_acceptance=["Names the week it covers"])
    amend(w, remove_acceptance=["Names the week it covers"])
    assert evidence.links("ceo", SERVICE, ["none"]) == ("none",)
    assert evidence.links("ceo", SERVICE, ["c3", "C1"]) == ("C3", "C1")


def test_a_service_nobody_defined_has_no_valid_ids(w: ReflectionWorld, evidence: ServiceEvidence) -> None:
    with pytest.raises(OrgError, match="unknown criterion or assertion for `nope`: C1. Its criteria: none; its regression assertions: none yet"):
        evidence.links("ceo", "nope", ["C1"])


def test_the_history_it_reads_is_the_one_of_the_world(w: ReflectionWorld) -> None:
    assert isinstance(w.history, CaseHistory)


# ------------------------------------------------------------------------------ through the wired application


def test_feedback_through_the_wired_application_raises_f5_and_f6(svc: Any) -> None:
    wired: Any = services_world  # the helpers of the wired world are untyped
    task = wired.request(svc, "ai")
    wired.deliver(svc, "ceo", task)
    with pytest.raises(OrgError) as e:
        svc.feedback(ROOT, task.id, "reject", "Too long.", source="human", criterion=["C9"])
    assert str(e.value) == (
        "unknown criterion or assertion for `weekly-brief`: C9. Its criteria: C1, C2; its regression assertions: none yet (see `services`)."
    )
    no = svc.feedback(ROOT, task.id, "reject", "Too long.", source="human", criterion=["C1"])
    with pytest.raises(OrgError) as e:
        svc.feedback(ROOT, task.id, "reject", "Yes, always.", source="human", criterion=["R1"], confirms=no.id)
    assert str(e.value) == "R1 is this rejection itself: name the criterion it is about, or the earlier rejection it repeats."
    with pytest.raises(OrgError, match="^unknown criterion or assertion for `weekly-brief`: R2. Its criteria: C1, C2; its regression assertions: R1 "):
        svc.feedback(ROOT, task.id, "reject", "Yes.", source="human", criterion=["R2"], confirms=no.id)
    link = svc.feedback(ROOT, task.id, "reject", "Yes, always.", source="human", criterion=["c2"], confirms=no.id)
    assert (link.criterion, link.reply_to, link.feedback) == ("C2", no.id, None)


# ------------------------------------------------------------------------------ amendment_basis (P2: what an amendment may answer)


def test_amendment_basis_lists_human_rejections_oldest_first_with_their_answers(w: ReflectionWorld, evidence: ServiceEvidence) -> None:
    first, one = rejected(w, "Too long.", criterion="C1")  # answered by the user's link
    second, two = rejected(w, "No dates.", topic="b")  # waiting for its answer
    third, three = rejected(w, "Wrong tone.", topic="c")
    w.s.d.clock.advance(1)
    basis = evidence.amendment_basis("ceo", SERVICE)
    assert [(r.note, r.assertion, r.task, r.title, r.earlier, r.words) for r in basis.rejections] == [
        (one.id, "R1", first.id, first.title, (), "Too long."),
        (two.id, "R2", second.id, second.title, ("R1",), "No dates."),
        (three.id, "R3", third.id, third.title, ("R1", "R2"), "Wrong tone."),
    ]
    link = next(m for m in w.s.d.mail.sent("root") if m.reply_to == one.id and m.criterion)
    assert [r.answered for r in basis.rejections] == [link.id, "", ""]
    assert basis.unrated == ()  # every delivery has its verdict


def test_amendment_basis_names_the_case_of_each_rejection(w: ReflectionWorld, evidence: ServiceEvidence) -> None:
    """``Rejection.case`` is ``Assertion.case``: the id of the case's first task, shared by a rework of it and by a rejection of the rework."""
    first, one = rejected(w, "Too long.", criterion="C1")
    again = rework(w, first)
    deliver(w, again)
    two = rate(w, again, "reject", "Still long.")  # a second rejection in the same case, answered by the user's link
    note_on(w, again, reply_to=two.id, source="human", criterion="C2")
    second, three = rejected(w, "No dates.", topic="b")  # a new request: its own case
    basis = evidence.amendment_basis("ceo", SERVICE)
    assert [(r.note, r.case) for r in basis.rejections] == [(one.id, first.id), (two.id, first.id), (three.id, second.id)]
    assert first.id != second.id


def test_a_relayed_rejection_is_not_in_the_basis(w: ReflectionWorld, evidence: ServiceEvidence) -> None:
    rejected(w, "The assistant's reading.", source="relayed")
    _, human = rejected(w, "The user's.", topic="b")
    basis = evidence.amendment_basis("ceo", SERVICE)
    assert [(r.note, r.assertion) for r in basis.rejections] == [(human.id, "R1")]  # R<k> counts human rejections only, as `services` shows


def test_a_human_reject_of_a_blocked_result_is_in_the_basis(w: ReflectionWorld, evidence: ServiceEvidence) -> None:
    """The shape of DR-41: a rejection of a result that is not ``done`` is a rejection to answer; a blocked case is not a delivery to rate."""
    task = ask(w, "ai")
    deliver(w, task, status="blocked")
    verdict = rate(w, task, "reject", "Not what I asked.")
    basis = evidence.amendment_basis("ceo", SERVICE)
    assert [(r.note, r.task, r.answered) for r in basis.rejections] == [(verdict.id, task.id, "")]
    assert basis.unrated == ()


def test_the_basis_names_the_deliveries_without_a_verdict(w: ReflectionWorld, evidence: ServiceEvidence) -> None:
    rated_task, unrated_task, open_task = ask(w, "a"), ask(w, "b"), ask(w, "c")
    deliver(w, rated_task)
    deliver(w, unrated_task)
    rate(w, rated_task, "accept")
    assert open_task.id and evidence.amendment_basis("ceo", SERVICE).unrated == (unrated_task.id,)  # the open request has no delivery yet


def test_answered_is_the_first_human_link_note_on_it(w: ReflectionWorld, evidence: ServiceEvidence) -> None:
    task, verdict = rejected(w, "Too long.")
    relayed = note_on(w, task, reply_to=verdict.id, source="relayed", criterion="C1")
    assert evidence.amendment_basis("ceo", SERVICE).rejections[0].answered == ""  # a relayed link answers nothing
    first = note_on(w, task, reply_to=verdict.id, source="human", criterion="C2")
    note_on(w, task, reply_to=verdict.id, source="human", criterion="none")  # a correction: the first human link stays the answer
    assert relayed.id < first.id
    assert evidence.amendment_basis("ceo", SERVICE).rejections[0].answered == first.id


def test_the_basis_question_is_the_replys_question(w: ReflectionWorld, evidence: ServiceEvidence) -> None:
    """``Rejection.question`` is the question of the reply that followed the rejection, byte for byte, with its ids filled in."""
    _, plain = rejected(w, "First.", source="human")
    _, with_c = rejected(w, "Second.", topic="b", source="human")
    task = ask(w, "c")
    deliver(w, task)
    by_c = rate(w, task, "reject", "Third.", criterion=["C2"])
    rejections = evidence.amendment_basis("ceo", SERVICE).rejections
    assert [r.note for r in rejections] == [plain.id, with_c.id, by_c.id]
    third = rejections[2]
    assert third.question == 'About C2: add "<the rule, in their words>" as a lasting rule? Yes or no.'
    assert f'in these words: "{third.question}"' in w.steps.feedback_step(by_c)
    assert rejections[0].question == 'About <its id>: add "<the rule, in their words>" as a lasting rule? Yes or no.'
    assert f'names the criterion you read the rejection as: "{rejections[0].question}"' in w.steps.feedback_step(plain)


# ------------------------------------------------------------------------------ the watch (design 8.1, 20.1): derived once per call from the files

BRIEF_ACCEPTANCE = ["At most 600 words", "Every factual claim has a source URL"]  # C1, C2 of the world's contract
ITEMS = "## Steps\n1. [P1] Search the sources."
RULE = ITEMS + "\n\n## Rules\n- [P2] WHEN always THEN cite every claim. WHY {why}"


def write_items(w: ReflectionWorld, version: int, body: str, why: dict[str, list[str]] | None = None) -> None:
    """The owner's playbook in item form, written to the store at the world's clock (the commands write the legacy form until the ops arrive)."""
    w.s.d.clock.advance(1)
    meta: dict[str, Any] = {
        "service": SERVICE, "version": version, "revised": w.s.d.clock.now().isoformat(timespec="microseconds"), "by": "ceo", "reason": "why",
        "evidence": [], "admitted": "c" if version > 1 else "first", "items_max": 2 if version > 1 else 1, "rules": ["P2"] if version > 1 else [],
        "why": why or {}, "op": "add" if version > 1 else "first",
    }
    if version > 1:
        meta["item"] = "P2"
    w.s.store.write_playbook("ceo", SERVICE, version, meta, body, (version - 1) or None)
    w.s.d.clock.advance(1)


def test_watch_reads_every_result_of_every_task_from_the_clients_mail(w: ReflectionWorld, evidence: ServiceEvidence) -> None:
    """The rejection of a delivery that was blocked first and done later was given on the blocked result: a watch that read only each task's latest
    result would find no result that came before the note, and the rule would not be warned."""
    write_items(w, 1, ITEMS)
    write_items(w, 2, RULE.format(why="C1"), {"P2": ["C1"]})
    task = ask(w, "ai")
    deliver(w, task, status="blocked")
    verdict = note_on(w, task, verdict="reject", source="human", body="No.")
    note_on(w, task, reply_to=verdict.id, source="human", criterion="C1")
    deliver(w, task)  # done, after the rejection
    found = {i.id: i for i in evidence.watch("ceo", SERVICE)}
    assert (found["P1"].state, found["P2"].state, found["P2"].related, found["P2"].waiting) == ("kept", "warning", ("R1",), 1)


def test_watch_reads_the_contract_versions_through_the_store(w: ReflectionWorld, evidence: ServiceEvidence) -> None:
    """The answering version alone relates the rejection to the rule that cites the criterion it removes (no link note was written)."""
    write_items(w, 1, ITEMS)
    write_items(w, 2, RULE.format(why="C2"), {"P2": ["C2"]})
    task = ask(w, "ai")
    deliver(w, task)
    verdict = note_on(w, task, verdict="reject", source="human", body="No.")
    found = w.s.store.read_contract("ceo", SERVICE)
    assert found is not None
    meta, body = found
    w.s.d.clock.advance(1)
    answer = {
        **meta, "version": 2, "acceptance": [BRIEF_ACCEPTANCE[0], "Every claim has a date"], "defined_by": "root", "answers": verdict.id,
        "about": "C1", "words": "Yes, add it.", "defined": w.s.d.clock.now().isoformat(timespec="microseconds"),
    }
    w.s.store.write_contract("ceo", SERVICE, answer, body, 1)  # removes C2, adds C3
    watched = {i.id: i for i in evidence.watch("ceo", SERVICE)}["P2"]
    assert (watched.state, watched.related, watched.pending) == ("warning", ("R1",), ())


def test_watch_gives_one_item_watch_per_item_of_a_legacy_playbook(w: ReflectionWorld, evidence: ServiceEvidence) -> None:
    legacy_playbook(w)  # the free text of three steps: it reads as it would migrate, every item kept
    found = evidence.watch("ceo", SERVICE)
    assert [(i.id, i.state) for i in found] == [("P1", "kept"), ("P2", "kept"), ("P3", "kept")]


def test_watch_of_a_service_nobody_offers_is_empty(w: ReflectionWorld, evidence: ServiceEvidence) -> None:
    assert evidence.watch("ceo", "no-such-service") == () and evidence.watch("ops", SERVICE) == ()
