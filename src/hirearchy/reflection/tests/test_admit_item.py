"""``CaseServiceEvidence.admit_item``: the evidence gate for ONE playbook item (design 6.2, 6.3): rules (b) and (c), the ``WHY`` the runtime writes
from the admission, PB-C-WORDS, and the two refusals (G1, G2) that say what an item needs. The evidence stage is the one ``admit`` has; the item
stage replaces the line stage."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from hirearchy.kernel import Message, OrgError, clip_line
from hirearchy.reflection import Verdict
from hirearchy.reflection._evidence import CaseServiceEvidence
from hirearchy.reflection.testing import FixedCaseHistory, ReflectionWorld, fs_world, memory_world
from hirearchy.services import Admission

from ._support import SERVICE, amend_legacy, ask, define, deliver, nested, note_on, populated, rework

WEEK = "Names the week it covers"
ACCEPTANCE = ["At most 600 words", "Every factual claim has a source URL"]  # C1, C2 of the world's contract
CASES = "cases the client rejected"


@pytest.fixture(params=[fs_world, memory_world], ids=lambda f: f.__name__)
def w(request: pytest.FixtureRequest, tmp_path: Path) -> ReflectionWorld:
    made = populated(request.param(tmp_path))
    define(made)
    return made


@pytest.fixture
def evidence(w: ReflectionWorld) -> CaseServiceEvidence:
    assert isinstance(w.evidence, CaseServiceEvidence)
    return w.evidence


def rejected(w: ReflectionWorld, words: str = "Too long.", *, topic: str = "ai", source: str = "human", **kw: str) -> tuple[Message, Message]:
    """A new case: the request, its delivery and the client's rejection; returns (request, verdict). A human ``criterion=...`` is the user's yes,
    recorded as a ``confirms`` link note after the verdict; a relayed or agent one stays on the verdict."""
    task = ask(w, topic)
    deliver(w, task)
    own = {} if source == "human" else kw
    verdict = note_on(w, task, verdict="reject", source=source, body=words, **own)
    if source == "human" and "criterion" in kw:
        note_on(w, task, reply_to=verdict.id, source="human", criterion=kw["criterion"])
    return task, verdict


def confirmed_c3(w: ReflectionWorld, text: str = WEEK) -> tuple[Message, Message]:
    """C3 (``text``) is added by an amendment and the user's yes to it is recorded on a rejection of the client's own."""
    amend_legacy(w, add_acceptance=[text])
    return rejected(w, "No week.", criterion="C3")


def failed_twice(w: ReflectionWorld, criterion: str = "C2") -> tuple[Message, Message]:
    """``criterion`` failed in two cases the client rejected (rule (b)); returns the two requests."""
    first, _ = rejected(w, "No source.", criterion=criterion)
    second, _ = rejected(w, "Still none.", topic="b", criterion=criterion)
    return first, second


def item(evidence: CaseServiceEvidence, ids: list[str], text: str, *, kind: str = "step", when: str | None = None, reason: str = "why", **over: Any) -> Admission:
    return evidence.admit_item("ceo", SERVICE, ids, reason, kind=kind, text=text, when=when, **over)


def refusal(evidence: CaseServiceEvidence, ids: list[str], text: str = "Cite every claim.", **kw: Any) -> str:
    with pytest.raises(OrgError) as e:
        item(evidence, ids, text, **kw)
    return str(e.value)


# ------------------------------------------------------------------------------ rule (c): an item is a confirmed criterion's own words


def test_c_admits_a_step_that_is_a_confirmed_criterions_words_with_or_without_its_id(w: ReflectionWorld, evidence: CaseServiceEvidence) -> None:
    confirmed_c3(w)
    detail = "cites C3, which root added to the contract (v2) and the client confirmed"
    for words in (WEEK, f"C3: {WEEK}", f"{WEEK} (C3)", "names the week it covers."):
        got = item(evidence, ["C3"], words)
        assert (got.rule, got.evidence, got.detail) == ("c", ("C3",), detail)
    assert item(evidence, ["R1"], WEEK).rule == "c"  # reached through the assertion that confirmed it


def test_c_admits_a_rule_whose_then_is_the_words_with_no_when_or_always(w: ReflectionWorld, evidence: CaseServiceEvidence) -> None:
    confirmed_c3(w)
    assert item(evidence, ["C3"], WEEK, kind="rule", when=None).rule == "c"
    assert item(evidence, ["C3"], WEEK, kind="rule", when="always").rule == "c"
    assert item(evidence, ["C3"], WEEK, kind="rule", when="ALWAYS").rule == "c"
    message = refusal(evidence, ["C3"], WEEK, kind="rule", when="the memo has a date")  # a condition makes it more than the criterion's words
    assert message.startswith("refused: C3 is confirmed by the client, so an item citing it may be only its own words: this item is not.")


def test_c_refuses_a_criterion_confirmed_only_by_a_link_on_a_relayed_rejection(w: ReflectionWorld, evidence: CaseServiceEvidence) -> None:
    """``feedback(confirms=...)`` does not check the rejected note's tier, so a human link on a relayed rejection confirms a criterion that has no
    answer: rule (c) needs a rejection of the client's own (``added_h``)."""
    amend_legacy(w, add_acceptance=[WEEK])
    task, relayed = rejected(w, "The assistant's reading.", source="relayed")
    note_on(w, task, reply_to=relayed.id, source="human", criterion="C3")
    assert "C3" in evidence.confirmed("ceo", SERVICE)  # the premise: the criterion counts as confirmed, by a link on a relayed rejection
    message = refusal(evidence, ["C3"], WEEK)
    assert message.startswith(
        "refused: none of this evidence is the client's own: C3 was confirmed only by a link on a relayed rejection (the assistant's own reading): "
        "rule (c) needs a rejection of the client's own. An item is admitted only when (b) "
    )


def test_c_is_the_item_stage_even_when_a_human_rejection_confirms_the_criterion_too(w: ReflectionWorld, evidence: CaseServiceEvidence) -> None:
    amend_legacy(w, add_acceptance=[WEEK])
    task, relayed = rejected(w, "The assistant's reading.", source="relayed")
    note_on(w, task, reply_to=relayed.id, source="human", criterion="C3")
    rejected(w, "No week.", topic="b", criterion="C3")  # a rejection of the client's own now confirms it as well
    assert item(evidence, ["C3"], WEEK).rule == "c"


# ------------------------------------------------------------------------------ rule (b): any words on two human rejections of two cases


def test_b_admits_any_words_on_two_human_rejections_of_two_cases(w: ReflectionWorld, evidence: CaseServiceEvidence) -> None:
    first, second = failed_twice(w)
    expected = f"C2 failed in 2 {CASES}: {first.id}, {second.id}"
    for kind, words in (("step", "Cite the source of every claim."), ("rule", "cite the source of every claim")):
        got = item(evidence, ["c2"], words, kind=kind, when="a claim has no source" if kind == "rule" else None)
        assert (got.rule, got.evidence, got.detail) == ("b", ("C2",), expected)
    assert item(evidence, ["R1", "R2"], "Anything the team wants.").rule == "b"


def test_b_why_holds_every_rejection_that_makes_a_subject_qualify_whether_cited_by_case_verdict_or_criterion(
    w: ReflectionWorld, evidence: CaseServiceEvidence,
) -> None:
    first, v1 = rejected(w, "No source.", criterion="C2")
    second, v2 = rejected(w, "Still none.", topic="b", criterion="C2")
    rejected(w, "Unrelated.", topic="c")  # R3: about nothing, not a reason
    for cited in (["C2"], ["R1"], ["R2"], [v1.id], [first.id], [second.id]):
        assert item(evidence, cited, "Cite the source.").why == ("R1", "R2", "C2"), cited
    assert "R3" not in item(evidence, ["C2"], "Cite the source.").why


def test_c_why_holds_the_criterion_and_its_rejection_even_with_an_empty_answers(w: ReflectionWorld, evidence: CaseServiceEvidence) -> None:
    confirmed_c3(w)  # a legacy amendment: its ``answers`` is empty
    assert w.s.catalog.criteria("ceo", SERVICE)[2].answers == ""
    assert item(evidence, ["C3"], WEEK).why == ("R1", "C3")


def test_c_why_holds_the_rejection_the_answering_version_answers(w: ReflectionWorld, evidence: CaseServiceEvidence) -> None:
    task, verdict = rejected(w, "No week.")
    found = w.s.store.read_contract("ceo", SERVICE)
    assert found is not None
    meta, body = found
    w.s.d.clock.advance(1)
    w.s.store.write_contract(
        "ceo", SERVICE,
        {**meta, "version": 2, "acceptance": [*ACCEPTANCE, WEEK], "defined_by": "root", "answers": verdict.id, "about": "C1",
         "words": "Yes, add it.", "defined": w.s.d.clock.now().isoformat(timespec="microseconds")},
        body, 1,
    )
    note_on(w, task, reply_to=verdict.id, source="human", criterion="C3")  # the product's own link of the answer
    assert item(evidence, ["C3"], WEEK).why == ("R1", "C3")


def test_every_admitted_why_holds_an_r_id(w: ReflectionWorld, evidence: CaseServiceEvidence) -> None:
    failed_twice(w)
    assert any(x.startswith("R") for x in item(evidence, ["C2"], "Cite the source.").why)
    confirmed_c3(w)
    assert any(x.startswith("R") for x in item(evidence, ["C3"], WEEK).why)


# ------------------------------------------------------------------------------ PB-C-WORDS


def test_pb_c_words_quotes_the_full_text_one_sentence_per_id(w: ReflectionWorld, evidence: CaseServiceEvidence) -> None:
    amend_legacy(w, add_acceptance=[WEEK, "Ends with one open question"])  # C3, C4
    rejected(w, "No week.", criterion="C3")
    rejected(w, "No question.", topic="b", criterion="C4")
    text = "Put the week first and end the memo with a question"
    expected = (
        "refused: C3, C4 are confirmed by the client, so an item citing them may be only their own words: this item is not. "
        'Write it as a step with text "Names the week it covers" (or a rule with then "Names the week it covers" and no when) to add C3. '
        'Write it as a step with text "Ends with one open question" (or a rule with then "Ends with one open question" and no when) to add C4. '
        "A different way of doing it needs a second case the client rejected on the same criterion (rule (b)). Nothing was written: change it again "
        "with those words, or send root (`send`) this question once: "
        f'"We would add to how we deliver weekly-brief: {text}. Is that what you want from now on? If yes, please add it to the contract as a criterion."'
    )
    assert refusal(evidence, ["C3", "C4"], text) == expected
    assert refusal(evidence, ["C3"], text) == expected.replace("C3, C4 are", "C3 is").replace("them may be only their", "it may be only its").replace(
        'Write it as a step with text "Ends with one open question" (or a rule with then "Ends with one open question" and no when) to add C4. ', "",
    )


def test_pb_c_words_over_300_characters_says_as_services_lists_them(w: ReflectionWorld, evidence: CaseServiceEvidence) -> None:
    long = "Names the week it covers " + "and the sources it used " * 14
    assert len(long) > 300
    confirmed_c3(w, long)
    message = refusal(evidence, ["C3"], "Something else.")
    assert (
        "Write it as a step whose text is C3's words exactly as `services` lists them (or a rule with those words as then and no when) to add C3. "
    ) in message
    assert long not in message
    from hirearchy.reflection._evidence import PB_C_WORDS  # the template the sentences above fill

    assert PB_C_WORDS.startswith("refused: {ids} ")


def test_the_question_of_pb_c_words_quotes_the_first_160_characters_of_the_item(w: ReflectionWorld, evidence: CaseServiceEvidence) -> None:
    confirmed_c3(w)
    text = " ".join(["word"] * 60)
    assert f'"We would add to how we deliver weekly-brief: {clip_line(text, 160)}. Is that what you want' in refusal(evidence, ["C3"], text)
    rule = refusal(evidence, ["C3"], "do it", kind="rule", when="a date is relative")
    assert 'deliver weekly-brief: WHEN a date is relative THEN do it. Is that what you want' in rule


def test_a_second_case_is_the_other_way_to_a_different_wording(w: ReflectionWorld, evidence: CaseServiceEvidence) -> None:
    """PB-C-WORDS says rule (b) is the other way: when the confirmed criterion also failed in two cases, any wording is admitted."""
    confirmed_c3(w)
    rejected(w, "No week again.", topic="b", criterion="C3")
    got = item(evidence, ["C3"], "Always put the week in the title.")
    assert got.rule == "b" and got.why == ("R1", "R2", "C3")


# ------------------------------------------------------------------------------ G1 and G2 say "item"


def test_g1_and_g2_read_item_for_revision(w: ReflectionWorld, evidence: CaseServiceEvidence) -> None:
    amend_legacy(w, add_acceptance=[WEEK])
    g1 = refusal(evidence, ["C1"], reason="Always give the sources first")
    assert g1 == (
        "refused: none of this evidence is the client's own: C1 is in the contract since v1, not added by an amendment, and failed in no case the "
        "client rejected. An item is admitted only when (b) the same criterion or regression assertion failed in 2 different cases the client "
        "rejected, or (c) it is the own words of a criterion root added to the contract by an amendment the client confirmed (none yet). Your team's "
        "lessons, relayed verdicts (the assistant's own reading) and an agent client's verdicts weigh nothing. Nothing was written: follow the "
        "playbook and the contract.\n"
        "If you think the client wants this from now on, send root (`send`) this question once, and do not wait for an answer (it reaches you as a "
        "contract change or a criterion link): \"We would change how we deliver weekly-brief: Always give the sources first. Is that what you want "
        "from now on? If yes, please add it to the contract as a criterion.\""
    )
    task, _ = rejected(w, "First words.", criterion="C2")
    g2 = refusal(evidence, ["C2"])
    assert g2.startswith(f"refused: the client rejected this in one case only ({task.id}), and the evidence cites no criterion root added")
    assert 'a new one, or a clarification of C2?" Add the item when the answer is in the contract (its new criterion\'s own words, citing it), or when a second case shows the same criterion failing.' in g2
    assert "Revise when" not in g2


# ------------------------------------------------------------------------------ what weighs nothing


def test_an_agent_client_admits_nothing(w: ReflectionWorld, evidence: CaseServiceEvidence) -> None:
    nested(w)
    with pytest.raises(OrgError) as e:
        evidence.admit_item("ceo/eng", "inner", ["C1"], "why", kind="step", text="Cite every claim.", when=None)
    assert str(e.value) == (
        "refused: the client of `inner` is ceo, an agent, so its verdicts are hypotheses and nothing in this service's history can admit a "
        "revision (rules (b) and (c) need the human client). Nothing was written. Follow the playbook and the contract; if you think the "
        "playbook must change, send ceo (`send`) what you would change and why."
    )


def test_lessons_relayed_and_agent_verdicts_admit_nothing(w: ReflectionWorld, evidence: CaseServiceEvidence) -> None:
    task = ask(w)
    result = deliver(w, task, lessons="- Cite every claim.")
    _, one = rejected(w, "Relayed one.", topic="b", source="relayed", criterion="C2")
    _, two = rejected(w, "Relayed two.", topic="c", source="relayed", criterion="C2")
    human = note_on(w, task, verdict="reject", source="human", body="x")
    case = w.history.cases("ceo", SERVICE)[0]
    agent = Verdict("reject", "y", None, task.id, 0, human, tier="agent")
    cited = CaseServiceEvidence(FixedCaseHistory([replace(case, verdicts=[agent])]), w.s.catalog, w.s.store, w.s.d.mail)
    note = "relayed (the assistant's own reading)"
    message = refusal(evidence, [one.id, two.id, result.id])
    assert message.startswith(f"refused: none of this evidence is the client's own: verdict {one.id} is {note}; verdict {two.id} is {note}; ")
    assert f"{result.id} is a result: its lessons are your team's view" in message
    assert f"verdict {human.id} is an agent client's (a hypothesis)." in refusal(cited, [human.id])


def test_unknown_evidence_is_refused_as_today(w: ReflectionWorld, evidence: CaseServiceEvidence) -> None:
    assert refusal(evidence, ["C9", "R1", "nonsense"]) == (
        "unknown evidence for `weekly-brief`: C9, R1, nonsense. Evidence is a criterion (C1, C2), a regression assertion (none yet), or the "
        "id of a verdict or a case of this service: see the regression list and the digest in your prompt. Nothing was written."
    )


def test_a_removed_criterion_adds_no_subject(w: ReflectionWorld, evidence: CaseServiceEvidence) -> None:
    failed_twice(w)
    w.s.commands.define_service("root", "ceo", SERVICE, remove_acceptance=["Every factual claim has a source URL"], words="Drop it.")
    assert "C2 is no longer in the contract" in refusal(evidence, ["C2"])


def test_the_case_of_a_rework_is_one_case(w: ReflectionWorld, evidence: CaseServiceEvidence) -> None:
    task, _ = rejected(w, "First words.", criterion="C2")
    again = rework(w, task)
    deliver(w, again)
    second = note_on(w, again, verdict="reject", source="human", body="Second words.")
    note_on(w, again, reply_to=second.id, source="human", criterion="C2")
    assert refusal(evidence, ["C2"]).startswith(f"refused: the client rejected this in one case only ({task.id})")


# ------------------------------------------------------------------------------ the rules compose (6.2: (c) first, then (b), then PB-C-WORDS)


@pytest.mark.parametrize("kind", ["step", "rule"])
def test_a_step_and_a_rule_are_judged_alike_by_rule_b(w: ReflectionWorld, evidence: CaseServiceEvidence, kind: str) -> None:
    first, second = failed_twice(w)
    got = item(evidence, ["C2"], "Cite every claim.", kind=kind, when="a claim has no source" if kind == "rule" else None)
    assert (got.rule, got.why, got.detail) == ("b", ("R1", "R2", "C2"), f"C2 failed in 2 {CASES}: {first.id}, {second.id}")


def test_admit_item_reads_the_record_and_writes_nothing(w: ReflectionWorld, evidence: CaseServiceEvidence) -> None:
    failed_twice(w)
    before = (w.s.rels(), len(w.s.d.inbox("ceo")), len(w.s.d.inbox("root")))
    item(evidence, ["C2"], "Cite every claim.")
    assert refusal(evidence, ["C1"])
    assert (w.s.rels(), len(w.s.d.inbox("ceo")), len(w.s.d.inbox("root"))) == before


def test_the_same_item_and_evidence_give_the_same_admission(w: ReflectionWorld, evidence: CaseServiceEvidence) -> None:
    confirmed_c3(w)
    failed_twice(w)
    assert item(evidence, ["C3"], WEEK) == item(evidence, ["C3"], WEEK)
    assert item(evidence, ["C2"], "Cite every claim.") == item(evidence, ["C2"], "Cite every claim.")
    assert refusal(evidence, ["C1"]) == refusal(evidence, ["C1"])


def test_a_blank_when_is_always_for_rule_c(w: ReflectionWorld, evidence: CaseServiceEvidence) -> None:
    confirmed_c3(w)
    for when in ("", "   ", " Always "):
        assert item(evidence, ["C3"], WEEK, kind="rule", when=when).rule == "c"


def test_each_confirmed_criterion_admits_only_its_own_words(w: ReflectionWorld, evidence: CaseServiceEvidence) -> None:
    confirmed_c3(w)  # v2 adds C3, confirmed on R1
    amend_legacy(w, add_acceptance=["Ends with one open question"])  # v3 adds C4
    rejected(w, "No question.", topic="b", criterion="C4")  # confirmed on R2
    assert (item(evidence, ["C3", "C4"], WEEK).detail, item(evidence, ["C3", "C4"], WEEK).why) == (
        "cites C3, which root added to the contract (v2) and the client confirmed", ("R1", "C3"),
    )
    assert (item(evidence, ["C3", "C4"], "Ends with one open question").detail, item(evidence, ["C3", "C4"], "Ends with one open question").why) == (
        "cites C4, which root added to the contract (v3) and the client confirmed", ("R2", "C4"),
    )


def test_rule_c_comes_before_rule_b_when_the_words_are_the_criterions(w: ReflectionWorld, evidence: CaseServiceEvidence) -> None:
    confirmed_c3(w)
    rejected(w, "No week again.", topic="b", criterion="C3")  # C3 also qualifies by rule (b): two cases
    assert item(evidence, ["C3"], WEEK).rule == "c"
    assert item(evidence, ["C3"], "Always name the week in the title.").rule == "b"  # other words: rule (b), with the same WHY ids
    assert item(evidence, ["C3"], WEEK).why == item(evidence, ["C3"], "Always name the week in the title.").why == ("R1", "R2", "C3")


def test_rule_b_admits_other_words_even_when_a_confirmed_criterion_is_cited_too(w: ReflectionWorld, evidence: CaseServiceEvidence) -> None:
    confirmed_c3(w)
    failed_twice(w, "C2")  # R2, R3: C2 qualifies by rule (b)
    got = item(evidence, ["C3", "C2"], "Cite every claim.")
    assert got.rule == "b" and got.why == ("R2", "R3", "C2")  # C3 is confirmed, but a single case: it is not a reason for these words


def test_pb_c_words_names_the_ids_in_id_order(w: ReflectionWorld, evidence: CaseServiceEvidence) -> None:
    confirmed_c3(w)
    amend_legacy(w, add_acceptance=["Ends with one open question"])
    rejected(w, "No question.", topic="b", criterion="C4")
    message = refusal(evidence, ["C4", "C3"], "Something else.")
    assert message.startswith("refused: C3, C4 are confirmed by the client, so an item citing them may be only their own words: this item is not.")
    assert message.index("to add C3.") < message.index("to add C4.")


def test_the_why_orders_the_r_ids_by_number_then_the_others() -> None:
    from hirearchy.reflection._evidence import _by_number

    assert _by_number({"C10", "C9", "R10", "R2", "R1"}) == ("R1", "R2", "R10", "C9", "C10")
