"""``CaseServiceEvidence``: the gate behind ``revise_playbook`` (rules (b) and (c)) and the ids a verdict may name, judged from the cases of a service.

The services suite of ``ServiceEvidence`` runs against it too (the pattern of ``services/tests/test_service_rework_context.py``), over a world
where ``ceo`` offers ``weekly-brief`` (``C1``, ``C2``, no case yet); the behaviour tests follow."""

from __future__ import annotations

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
    test_admit_returns_rule_b_or_c_or_raises_an_org_error,
    test_an_exempt_admit_returns_the_exemption_with_normalized_ids,
    test_an_exempt_admit_with_no_evidence_returns_the_exemption,
    test_links_accepts_none_alone,
    test_links_returns_normalized_ids_or_raises,
)

from ._support import SERVICE, ask, define, deliver, nested, note_on, populated, rework

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
    w.s.commands.define_service("root", "ceo", SERVICE, **over)


def refusal(evidence: ServiceEvidence, ids: list[str], reason: str = "why", owner: str = "ceo", service: str = SERVICE) -> str:
    with pytest.raises(OrgError) as e:
        evidence.admit(owner, service, ids, reason)
    return str(e.value)


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


def test_g0_comes_before_an_exemption(w: ReflectionWorld, evidence: ServiceEvidence) -> None:
    with pytest.raises(OrgError, match="^unknown evidence for `weekly-brief`: R4"):
        evidence.admit("ceo", SERVICE, ["R4"], "why", exempt="first")


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
    assert cited.admit("ceo/eng", "inner", ["C1"], "why", exempt="restore").rule == "restore"
    with pytest.raises(OrgError, match="^unknown evidence for `inner`: R1"):
        cited.admit("ceo/eng", "inner", ["R1"], "why")


# ------------------------------------------------------------------------------ rule (b)


def test_b_admits_two_human_rejections_in_two_cases_linked_to_one_criterion(w: ReflectionWorld, evidence: ServiceEvidence) -> None:
    first, _ = rejected(w, "No source.", criterion="C2")
    second, _ = rejected(w, "Still no source.", topic="b", criterion="C2")
    expected = f"C2 failed in 2 {CASES}: {first.id}, {second.id}"
    assert evidence.admit("ceo", SERVICE, ["c2"], "why") == Admission("b", ("C2",), expected)
    assert evidence.admit("ceo", SERVICE, ["R1", "R2"], "why") == Admission("b", ("R1", "R2"), expected)
    assert evidence.admit("ceo", SERVICE, ["R2"], "why") == Admission("b", ("R2",), expected)


def test_b_admits_through_a_link_note_the_client_gave_later(w: ReflectionWorld, evidence: ServiceEvidence) -> None:
    first, no = rejected(w, "No source.")
    note_on(w, first, reply_to=no.id, criterion="C2", source="human")
    second, _ = rejected(w, "Still none.", topic="b", criterion="C2")
    assert evidence.admit("ceo", SERVICE, ["C2"], "why").detail == f"C2 failed in 2 {CASES}: {first.id}, {second.id}"


def test_b_admits_through_the_same_as_rj(w: ReflectionWorld, evidence: ServiceEvidence) -> None:
    first, _ = rejected(w, "No source.")  # no link of its own
    second, _ = rejected(w, "Same as before.", topic="b", criterion="R1")
    assert evidence.admit("ceo", SERVICE, ["R1"], "why") == Admission("b", ("R1",), f"R1 failed in 2 {CASES}: {first.id}, {second.id}")


def test_b_resolves_the_same_as_rj_to_the_criterion_of_rj(w: ReflectionWorld, evidence: ServiceEvidence) -> None:
    first, _ = rejected(w, "No source.", criterion="C2")
    second, _ = rejected(w, "Same as before.", topic="b", criterion="R1")
    assert evidence.admit("ceo", SERVICE, ["C2"], "why") == Admission("b", ("C2",), f"C2 failed in 2 {CASES}: {first.id}, {second.id}")


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
    cited = CaseServiceEvidence(FixedCaseHistory([fixed]), w.s.catalog)
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
    assert evidence.admit("ceo", SERVICE, ["c3"], "why") == Admission(
        "c", ("C3",), "cites C3, which root added to the contract (v2) and the client confirmed",
    )
    amend(w, add_acceptance=["Ends with one open question"])
    rejected(w, "No question.", topic="b", criterion="C4")
    assert evidence.admit("ceo", SERVICE, ["C3", "C4"], "why").detail == (
        "cites C3, C4, which root added to the contract (v2, v3) and the client confirmed"
    )
    assert evidence.admit("ceo", SERVICE, ["C1", "C4"], "why").detail == "cites C4, which root added to the contract (v3) and the client confirmed"


def test_rule_c_admits_a_confirmed_amendment(w: ReflectionWorld, evidence: ServiceEvidence) -> None:
    amend(w, add_acceptance=["Names the week it covers", "Ends with one open question"])  # C3, C4
    rejected(w, "No week.", criterion="C3")
    assert evidence.admit("ceo", SERVICE, ["C3"], "why").detail == "cites C3, which root added to the contract (v2) and the client confirmed"
    assert "C4 was added to the contract by an amendment (v2), but the client's yes to it is not recorded (not confirmed)." in refusal(
        evidence, ["C4"],
    )  # only C3 is confirmed: citing C4 alone gets no admission
    assert evidence.admit("ceo", SERVICE, ["C3", "C4"], "why").detail == "cites C3, which root added to the contract (v2) and the client confirmed"


def test_rule_c_refuses_an_amendment_without_a_confirmation(w: ReflectionWorld, evidence: ServiceEvidence) -> None:
    amend(w, add_acceptance=["Names the week it covers"])
    task, no = rejected(w, "No week.")
    note_on(w, task, reply_to=no.id, criterion="C3", source="relayed")  # the assistant's own reading is no confirmation
    message = refusal(evidence, ["C3"])
    assert message.startswith(
        "refused: none of this evidence is the client's own: C3 was added to the contract by an amendment (v2), but the client's yes to it is not "
        "recorded (not confirmed). "
    )
    assert "(c) it cites a criterion root added to the contract by an amendment the client confirmed (none yet)." in message


def test_a_user_initiated_amendment_is_never_rule_c_eligible(w: ReflectionWorld, evidence: ServiceEvidence) -> None:
    """DR-27: root amends with no rejection at all, so no `confirms` link can name the new criterion."""
    amend(w, add_acceptance=["Names the week it covers"])
    message = refusal(evidence, ["C3"])
    assert "C3 was added to the contract by an amendment (v2), but the client's yes to it is not recorded (not confirmed)." in message
    assert "amendment the client confirmed (none yet)." in message


def test_c_admits_an_amended_criterion_reached_through_an_assertion(w: ReflectionWorld, evidence: ServiceEvidence) -> None:
    amend(w, add_acceptance=["Names the week it covers"])
    rejected(w, "No week named.", criterion="C3")
    assert evidence.admit("ceo", SERVICE, ["R1"], "why") == Admission(
        "c", ("R1",), "cites C3, which root added to the contract (v2) and the client confirmed",
    )


def test_c_refuses_a_v1_criterion_with_its_note(w: ReflectionWorld, evidence: ServiceEvidence) -> None:
    amend(w, add_acceptance=["Names the week it covers"])
    reason = "Always give the sources first"
    assert refusal(evidence, ["C1"], reason) == (
        "refused: none of this evidence is the client's own: C1 is in the contract since v1, not added by an amendment, and failed in no case the "
        "client rejected. A revision is admitted only when (b) the same criterion or regression assertion failed in 2 different cases the client "
        "rejected, or (c) it cites a criterion root added to the contract by an amendment the client confirmed (none yet). Your team's lessons, relayed verdicts (the "
        "assistant's own reading) and an agent client's verdicts weigh nothing. Nothing was written: follow the playbook and the contract.\n"
        "If you think the client wants this from now on, send root (`send`) this question once, and do not wait for an answer (it reaches you as a "
        "contract change or a criterion link): \"We would change how we deliver weekly-brief: Always give the sources first. Is that what you want "
        "from now on? If yes, please add it to the contract as a criterion.\""
    )


def test_no_evidence_at_all_is_a_g1_refusal_that_says_so(w: ReflectionWorld, evidence: ServiceEvidence) -> None:
    assert refusal(evidence, []).startswith(
        "refused: none of this evidence is the client's own: no evidence given. A revision is admitted only when (b) "
    )
    assert "(c) it cites a criterion root added to the contract by an amendment the client confirmed (none yet)." in refusal(evidence, [])


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
    admitted = evidence.admit("ceo", SERVICE, [link.id], "why")
    assert admitted == Admission("c", (link.id,), "cites C3, which root added to the contract (v2) and the client confirmed")
    assert evidence.admit("ceo", SERVICE, [no.id], "why").rule == "c"  # the rejection itself resolves through its human link as before


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


# ------------------------------------------------------------------------------ criteria the client removed


def test_a_cited_removed_criterion_adds_no_subject_and_says_so(w: ReflectionWorld, evidence: ServiceEvidence) -> None:
    amend(w, add_acceptance=["Names the week it covers"])
    amend(w, remove_acceptance=["Names the week it covers"])
    message = refusal(evidence, ["C3"])
    assert "C3 is no longer in the contract: cite a current criterion (see `services`)." in message
    assert "(c) it cites a criterion root added to the contract by an amendment the client confirmed (none yet)." in message


def test_two_rejections_linked_only_to_a_removed_criterion_do_not_admit(w: ReflectionWorld, evidence: ServiceEvidence) -> None:
    amend(w, add_acceptance=["Names the week it covers"])
    rejected(w, "No week.", criterion="C3")
    rejected(w, "Still no week.", topic="b", criterion="C3")
    assert evidence.admit("ceo", SERVICE, ["C3"], "why").rule == "c"  # while the criterion is in the contract, the amendment admits it
    amend(w, remove_acceptance=["Names the week it covers"])
    assert "C3 is no longer in the contract" in refusal(evidence, ["C3"])
    message = refusal(evidence, ["R1", "R2"])
    assert message.startswith("refused: the client rejected this in one case only (")
    assert 'a new one, or a clarification of an existing one?" Revise when the answer is in the contract' in message


# ------------------------------------------------------------------------------ ids that resolve to something else


def test_a_cited_case_resolves_to_its_human_rejections(w: ReflectionWorld, evidence: ServiceEvidence) -> None:
    first, _ = rejected(w, "No source.", criterion="C2")
    second, _ = rejected(w, "Still none.", topic="b", criterion="C2")
    assert evidence.admit("ceo", SERVICE, [first.id, second.id], "why") == Admission(
        "b", (first.id, second.id), f"C2 failed in 2 {CASES}: {first.id}, {second.id}",
    )
    again = rework(w, second)  # any task of the chain names the case
    assert evidence.admit("ceo", SERVICE, [first.id, again.id], "why").rule == "b"


def test_a_cited_verdict_id_resolves_to_its_assertion(w: ReflectionWorld, evidence: ServiceEvidence) -> None:
    _, one = rejected(w, "No source.", criterion="C2")
    _, two = rejected(w, "Still none.", topic="b", criterion="C2")
    assert evidence.admit("ceo", SERVICE, [one.id, two.id], "why").rule == "b"


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
    assert 'which criterion should say it: a new one, or a clarification of C2?" Revise when the answer is in the contract' in message
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
