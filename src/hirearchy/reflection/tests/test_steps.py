"""``TextServiceSteps``: what root is told to do next after it recorded a rejection, and after it sent a rework (design 3.4, 5.6, DR-19).

The user's yes is what makes a link the client's, so the rejection's text names the one question to ask and the calls that record the answer; they
are advice and never write anything. No step follows an amendment: the gate refuses one that does not carry the user's words."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from hirearchy.kernel import Message, clip_line
from hirearchy.reflection.testing import ReflectionWorld, fs_world, memory_world

from ._support import SERVICE, amend_legacy, ask, define, deliver, nested, note_on, populated, rate

FORM_C = (
    'Next: ask the user exactly ONE yes/no question, in these words: "About {id}: add "<the rule, in their words>" as a lasting rule? Yes or no." '
    'Change nothing in this turn: an "always ..." in the rejection is not their yes. '
    'On yes: define_service(owner="ceo", name="weekly-brief", add_acceptance=["<the rule>"], answers="{note}", about="{id}", '
    'words="<their answer, verbatim>"). On no, a one-off or "as it is": feedback(task_id="{task}", verdict="reject", confirms="{note}", '
    'criterion=["none"] or ["{id}"], source="human", note="<their answer, verbatim>").'
)
FORM_R = (
    'Next: ask the user exactly ONE yes/no question, in these words: "Same as {id}: a one-off? Yes or no." '
    'Change nothing in this turn: an "always ..." in the rejection is not their yes. '
    'On yes: feedback(task_id="{task}", verdict="reject", confirms="{note}", criterion=["{id}"], source="human", note="<their answer, verbatim>"). '
    'On no, when their answer asks for a lasting rule: define_service(owner="ceo", name="weekly-brief", add_acceptance=["<the rule>"], '
    'answers="{note}", about="{id}", words="<their answer, verbatim>"); otherwise feedback(task_id="{task}", verdict="reject", confirms="{note}", '
    'criterion=["none"], source="human", note="<their answer, verbatim>").'
)
FORM_NONE = (
    'Next: ask the user exactly ONE yes/no question that names the criterion you read the rejection as: "About <its id>: add "<the rule, in their '
    'words>" as a lasting rule? Yes or no.", with <its id> one of {criteria}{repeat}. Next time, pass your reading as criterion on the rejection and '
    'this reply gives the question with its id. Change nothing in this turn: an "always ..." in the rejection is not their yes. '
    'On yes: define_service(owner="ceo", name="weekly-brief", add_acceptance=["<the rule>"], answers="{note}", about="<the id you asked about>", '
    'words="<their answer, verbatim>"). On no, a one-off or "as it is": feedback(task_id="{task}", verdict="reject", confirms="{note}", '
    'criterion=["none"], ["R<j>"] or ["C<k>"], source="human", note="<their answer, verbatim>").'
)
REPEAT = '; for a repeat: "Same as R<j>: a one-off? Yes or no.", with R<j> one of {rejections}'


@pytest.fixture(params=[fs_world, memory_world], ids=lambda f: f.__name__)
def w(request: pytest.FixtureRequest, tmp_path: Path) -> ReflectionWorld:
    made = populated(request.param(tmp_path))
    define(made)
    return made


def amend(w: ReflectionWorld, **over: Any) -> None:
    """Root's amendment as a contract version was written before 0a.2 (no basis in its frontmatter): the step texts are about the legacy rule."""
    if "add_acceptance" in over or "remove_acceptance" in over:
        amend_legacy(w, **over)
    else:
        w.s.commands.define_service("root", "ceo", SERVICE, **over)


def rejected(w: ReflectionWorld, words: str = "Too long.", *, topic: str = "ai", **kw: object) -> tuple[Message, Message]:
    """A new case: the request, its delivery and the user's rejection; returns (request, verdict note)."""
    task = ask(w, topic)
    deliver(w, task)
    return task, rate(w, task, "reject", words, **kw)


# ------------------------------------------------------------------------------ feedback_step


def test_feedback_step_names_the_ids_and_the_confirmation(w: ReflectionWorld) -> None:
    rejected(w, "First.", topic="a")  # two earlier human rejections, in other cases: the new one is the third of the service (DR-19)
    rejected(w, "Second.", topic="b")
    task, note = rejected(w, "Third.", topic="c")  # no reading: the third form lists the ids
    assert w.steps.feedback_step(note) == "This rejection is R3. " + FORM_NONE.format(
        criteria="C1, C2", repeat=REPEAT.format(rejections="R1, R2"), task=task.id, note=note.id,
    )


def test_a_reading_ck_gives_about_ck_add_and_about_ck(w: ReflectionWorld) -> None:
    task, note = rejected(w, criterion=["C2", "C1"])  # root's reading: the first id that is a current criterion
    assert w.steps.feedback_step(note) == (
        "The criterion on the rejection itself (C2, C1) is recorded as not confirmed. This rejection is R1. "
        + FORM_C.format(id="C2", task=task.id, note=note.id)
    )
    amend(w, add_acceptance=["Names the week it covers"], remove_acceptance=["At most 600 words"])  # C1 is no longer current: the next reading skips it
    task, second = rejected(w, "Again.", topic="b", criterion=["C1", "C3"])
    assert w.steps.feedback_step(second).endswith(FORM_C.format(id="C3", task=task.id, note=second.id))


def test_a_reading_rj_gives_same_as_rj_a_one_off(w: ReflectionWorld) -> None:
    rejected(w, "First.", topic="a")
    task, second = rejected(w, "Second.", topic="b", criterion=["R1"])
    assert w.steps.feedback_step(second) == (
        "The criterion on the rejection itself (R1) is recorded as not confirmed. This rejection is R2. "
        + FORM_R.format(id="R1", task=task.id, note=second.id)
    )


def test_no_reading_or_none_gives_the_third_form_listing_the_ids_and_no_ck_is_one_of(w: ReflectionWorld) -> None:
    rejected(w, "First.", topic="a")
    task, plain = rejected(w, "Second.", topic="b")
    expected = FORM_NONE.format(criteria="C1, C2", repeat=REPEAT.format(rejections="R1"), task=task.id, note=plain.id)
    assert w.steps.feedback_step(plain) == "This rejection is R2. " + expected
    assert "C<k> is one of" not in expected and "with <its id> one of C1, C2" in expected


@pytest.mark.parametrize("ids", [["none"], ["C9"], ["R1"]], ids=["none", "an-id-the-service-lacks", "the-rejection-itself"])
def test_an_id_that_is_no_reading_gives_the_third_form(w: ReflectionWorld, ids: list[str]) -> None:
    task, note = rejected(w, criterion=ids)  # the first rejection: no earlier R<j>, and none, C9 and R1 (itself) name no criterion in force
    text = w.steps.feedback_step(note)
    assert text.endswith(FORM_NONE.format(criteria="C1, C2", repeat="", task=task.id, note=note.id))
    assert f"The criterion on the rejection itself ({ids[0]}) is recorded as not confirmed. " in text and "C<k> is one of" not in text


def test_no_earlier_rejection_leaves_out_the_repeat_sentence(w: ReflectionWorld) -> None:
    task, note = rejected(w)
    text = w.steps.feedback_step(note)
    assert text == "This rejection is R1. " + FORM_NONE.format(criteria="C1, C2", repeat="", task=task.id, note=note.id)
    assert "for a repeat" not in text and "R<j> one of" not in text


def test_question_for_is_the_quoted_question_of_the_reply(w: ReflectionWorld) -> None:
    from hirearchy.reflection._steps import question_for

    _, first = rejected(w, "First.", topic="a")
    _, with_c = rejected(w, "Second.", topic="b", criterion=["C2"])
    _, with_r = rejected(w, "Third.", topic="c", criterion=["R1"])
    criteria, earlier = ["C1", "C2"], ["R1", "R2"]
    ask_c = 'About C2: add "<the rule, in their words>" as a lasting rule? Yes or no.'
    ask_r = "Same as R1: a one-off? Yes or no."
    ask_none = 'About <its id>: add "<the rule, in their words>" as a lasting rule? Yes or no.'
    assert question_for(with_c, criteria, earlier) == ask_c and question_for(with_r, criteria, earlier) == ask_r
    assert question_for(first, criteria, earlier) == ask_none
    assert f'in these words: "{ask_c}"' in w.steps.feedback_step(with_c) and f'in these words: "{ask_r}"' in w.steps.feedback_step(with_r)
    assert f'names the criterion you read the rejection as: "{ask_none}"' in w.steps.feedback_step(first)  # the third form quotes it the same way
    assert question_for(with_c, ["C1"], earlier) == ask_none  # C2 is not a criterion in force: no reading


def test_feedback_step_says_an_own_criterion_is_not_confirmed(w: ReflectionWorld) -> None:
    task, note = rejected(w, criterion=["C2"])
    text = w.steps.feedback_step(note)
    assert text.startswith("The criterion on the rejection itself (C2) is recorded as not confirmed. This rejection is R1. Next: ")
    assert f'confirms="{note.id}"' in text


def test_feedback_step_is_empty_for_accepts_relayed_rejects_and_links(w: ReflectionWorld) -> None:
    task = ask(w)
    deliver(w, task)
    assert w.steps.feedback_step(rate(w, task, "accept")) == ""
    _, relayed = rejected(w, "Maybe.", topic="b", source="relayed")
    assert w.steps.feedback_step(relayed) == ""
    third, human = rejected(w, "No.", topic="c")
    link = note_on(w, third, reply_to=human.id, criterion="C1", source="human")
    assert w.steps.feedback_step(link) == "" and w.steps.feedback_step(human) != ""
    answered = nested(w)  # an agent client's rejection is a hypothesis
    agent = w.s.commands.feedback("ceo", answered.reply_to or "", "reject", "No.")
    assert w.steps.feedback_step(agent) == ""


def test_feedback_step_is_empty_for_a_note_it_cannot_place(w: ReflectionWorld) -> None:
    lost = Message(sender="root", to="ceo", type="note", body="x", feedback="reject", source="human", reply_to="20260101T000000000000-root-0001")
    assert w.steps.feedback_step(lost) == ""
    assert w.steps.feedback_step(Message(sender="root", to="ceo", type="note", body="x", feedback="reject", source="human")) == ""
    plain = w.s.d.post(Message(sender="root", to="ceo", type="task", title="Plain", body="Do it."))  # a task that is no service request
    assert w.steps.feedback_step(Message(sender="root", to="ceo", type="note", body="x", feedback="reject", source="human", reply_to=plain.id)) == ""


# ------------------------------------------------------------------------------ no step before the yes


@pytest.mark.parametrize(
    "criterion", [None, ["none"], ["C9"], ["C1"], ["R1"], ["C2", "R1"]],
    ids=["no-reading", "none", "an-id-the-service-lacks", "ck", "rj", "the-first-valid-one"],
)
def test_no_text_names_a_yes_before_the_answer(w: ReflectionWorld, criterion: list[str] | None) -> None:
    """Whatever root's reading, the step asks the question first and says the contract changes only with the answer (``answers=<this rejection>``);
    nothing names a "yes" that is not recorded, and the old texts are gone."""
    rejected(w, "First.", topic="a")
    task, note = rejected(w, "Second.", topic="b", **({"criterion": criterion} if criterion else {}))
    text = w.steps.feedback_step(note)
    assert 'Change nothing in this turn: an "always ..." in the rejection is not their yes.' in text
    assert f'confirms="{note.id}"' in text and f'task_id="{task.id}"' in text
    for gone in ("Not client-confirmed", "has no recorded yes", "Only after their yes", "Next, before define_service"):
        assert gone not in text
    assert "answers=" in text  # every form can end in define_service(answers=...)


def test_an_answered_amendment_needs_no_further_step(w: ReflectionWorld) -> None:
    """After define_service(answers=...) the product's link is a note, not a verdict: it gets no step, and there is no amendment step to ask."""
    task, note = rejected(w)
    link = note_on(w, task, reply_to=note.id, source="human", criterion="C1")
    assert w.steps.feedback_step(link) == "" and not hasattr(w.steps, "amendment_step")


# ------------------------------------------------------------------------------ rework_step

REWORK = (
    "{revised}'s result asked the client: {questions}. Ask the user these questions, unless the user asked for this change: "
    "a rework does not answer them."
)


def deliver_asking(w: ReflectionWorld, task: Message, *questions: str, block: str | None = None) -> Message:
    """The owner answers ``task`` with a done result whose summary ends in a ``Questions for the client:`` block (``block`` replaces it)."""
    w.use_run(task.to)
    listing = block if block is not None else "Questions for the client:\n" + "\n".join(f"- {q}" for q in questions)
    return w.s.d.post(Message(
        sender=task.to, to=task.sender, type="result", status="done", reply_to=task.id, body=f"## Summary\nDelivered.\n\n{listing}\n", title="Result",
    ))


def test_rework_step_repeats_the_revised_results_questions(w: ReflectionWorld) -> None:
    first = ask(w)
    deliver_asking(w, first, "Keep Marta's row?", "Which Friday?")
    rework = ask(w, "ai", revises=first.id)  # root's own reading: relayed
    assert rework.source == "relayed"
    assert w.steps.rework_step(rework) == REWORK.format(revised=first.id, questions="Keep Marta's row?; Which Friday?")


def test_rework_step_is_empty_for_a_human_rework_or_a_result_without_questions(w: ReflectionWorld) -> None:
    first = ask(w)
    deliver_asking(w, first, "Keep Marta's row?")
    assert w.steps.rework_step(ask(w, "ai", revises=first.id, source="human")) == ""  # the user asked for it: it answers them
    quiet = ask(w, "b")
    deliver_asking(w, quiet, block="Questions for the client: none.")
    assert w.steps.rework_step(ask(w, "b", revises=quiet.id)) == ""  # zero questions
    plain = ask(w, "c")
    deliver(w, plain)
    assert w.steps.rework_step(ask(w, "c", revises=plain.id)) == ""  # no block at all
    undelivered = ask(w, "d")
    assert w.steps.rework_step(ask(w, "d", revises=undelivered.id)) == ""  # no result yet
    assert w.steps.rework_step(ask(w, "e")) == ""  # not a rework


def test_rework_step_reads_the_latest_result_of_the_revised_task(w: ReflectionWorld) -> None:
    first = ask(w)
    deliver_asking(w, first, "Old question?")
    w.s.d.post(Message(sender="ceo", to="root", type="result", status="done", reply_to=first.id, body="Questions for the client: none.", title="Again"))
    assert w.steps.rework_step(ask(w, "ai", revises=first.id)) == ""


def test_rework_step_clips_and_counts(w: ReflectionWorld) -> None:
    long = "Is this the long question? " * 12
    first = ask(w, "a")
    deliver_asking(w, first, long, "second?")
    text = w.steps.rework_step(ask(w, "a", revises=first.id))
    assert clip_line(long, 160) in text and len(clip_line(long, 160)) == 160 and long.strip() not in text
    five = ask(w, "b")
    deliver_asking(w, five, *[f"q{i}?" for i in range(1, 6)])
    assert w.steps.rework_step(ask(w, "b", revises=five.id)) == REWORK.format(revised=five.id, questions="q1?; q2?; q3?; q4?; q5?")  # no suffix
    six = ask(w, "c")
    deliver_asking(w, six, *[f"q{i}?" for i in range(1, 7)])
    assert w.steps.rework_step(ask(w, "c", revises=six.id)) == REWORK.format(revised=six.id, questions="q1?; q2?; q3?; q4?; q5?; and 1 more")
    seven = ask(w, "d")
    deliver_asking(w, seven, *[f"q{i}?" for i in range(1, 8)])
    assert "q5?; and 2 more. Ask the user" in w.steps.rework_step(ask(w, "d", revises=seven.id))
