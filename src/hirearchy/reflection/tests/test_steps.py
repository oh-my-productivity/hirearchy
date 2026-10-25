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


TOPUP = (
    "This rework has {budget} run(s), and a rework of this team needs about {need} (1, plus 2 for each agent below {owner}). {left} Ask the user now "
    'for {ask} more run(s), with that number; on yes, grant {grant}: send(to="{owner}", budget={grant}, body=<why>) '
    '(CLI: hirearchy send {owner} "<why>" --budget {grant}).'
)
NOTHING_LEFT = "Nothing else is left of the runs the user approved for this case."
SOME_LEFT = "{spare} more of the {approved} runs the user approved for this case are left."
HELD = "The team still holds {held} of the user's runs for {revised}; the rework can use them."


def deliver_asking(w: ReflectionWorld, task: Message, *questions: str, block: str | None = None) -> Message:
    """The owner answers ``task`` with a done result whose summary ends in a ``Questions for the client:`` block (``block`` replaces it). D-E6-1: the
    callers pass items that name a criterion id (``C<k>``), the questions the relayed rework repeats; items without one are notes."""
    w.use_run(task.to)
    listing = block if block is not None else "Questions for the client:\n" + "\n".join(f"- {q}" for q in questions)
    return w.s.d.post(Message(
        sender=task.to, to=task.sender, type="result", status="done", reply_to=task.id, body=f"## Summary\nDelivered.\n\n{listing}\n", title="Result",
    ))


def test_rework_step_repeats_the_revised_results_questions(w: ReflectionWorld) -> None:
    first = ask(w)
    deliver_asking(w, first, "C1: Keep Marta's row?", "C2: Which Friday?")
    rework = ask(w, "ai", revises=first.id)  # root's own reading: relayed
    assert rework.source == "relayed"
    assert w.steps.rework_step(rework) == REWORK.format(revised=first.id, questions="C1: Keep Marta's row?; C2: Which Friday?")


def test_rework_step_is_empty_for_a_human_rework_or_a_result_without_questions(w: ReflectionWorld) -> None:
    """The user asked for the human rework, so it answers the client questions; and 0a.3's top-up step is empty too, because the round of ``ceo``'s
    team (1, plus 2 for each of its 2 reports: 5) fits the 10 runs the rework carries (D-E5-1)."""
    first = ask(w)
    deliver_asking(w, first, "C1: Keep Marta's row?")
    assert w.steps.rework_step(ask(w, "ai", revises=first.id, source="human")) == ""  # the user asked for it: it answers them; its 10 runs cover the round of 5
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
    deliver_asking(w, first, "C1: Old question?")
    w.s.d.post(Message(sender="ceo", to="root", type="result", status="done", reply_to=first.id, body="Questions for the client: none.", title="Again"))
    assert w.steps.rework_step(ask(w, "ai", revises=first.id)) == ""


def test_a_relayed_rework_of_a_result_with_only_notes_gets_no_reply(w: ReflectionWorld) -> None:
    """D-E6-1 (A2): the items that name no criterion id are notes; they are passed on with the delivery and the rework does not repeat them."""
    first = ask(w)
    deliver_asking(w, first, "Style: 'himself' in Sam's row (reviewer: harmless).", "Keep or delete the Open section?")
    assert w.steps.rework_step(ask(w, "ai", revises=first.id)) == ""


def test_a_relayed_rework_lists_only_the_questions_of_a_result_with_both(w: ReflectionWorld) -> None:
    first = ask(w)
    deliver_asking(w, first, "Style: 'himself' (reviewer: harmless).", "C3: Keep Marta's row?", "A typo in row 2.", "C4: Which Friday?")
    rework = ask(w, "ai", revises=first.id)
    assert w.steps.rework_step(rework) == REWORK.format(revised=first.id, questions="C3: Keep Marta's row?; C4: Which Friday?")


def test_rework_step_clips_and_counts(w: ReflectionWorld) -> None:
    long = "C1: " + "Is this the long question? " * 12
    first = ask(w, "a")
    deliver_asking(w, first, long, "C2: second?")
    text = w.steps.rework_step(ask(w, "a", revises=first.id))
    assert clip_line(long, 160) in text and len(clip_line(long, 160)) == 160 and long.strip() not in text
    five = ask(w, "b")
    deliver_asking(w, five, *[f"C{i}: q{i}?" for i in range(1, 6)])
    assert w.steps.rework_step(ask(w, "b", revises=five.id)) == REWORK.format(revised=five.id, questions="C1: q1?; C2: q2?; C3: q3?; C4: q4?; C5: q5?")  # no suffix
    six = ask(w, "c")
    deliver_asking(w, six, *[f"C{i}: q{i}?" for i in range(1, 7)])
    assert w.steps.rework_step(ask(w, "c", revises=six.id)) == REWORK.format(revised=six.id, questions="C1: q1?; C2: q2?; C3: q3?; C4: q4?; C5: q5?; and 1 more")
    seven = ask(w, "d")
    deliver_asking(w, seven, *[f"C{i}: q{i}?" for i in range(1, 8)])
    assert "C5: q5?; and 2 more. Ask the user" in w.steps.rework_step(ask(w, "d", revises=seven.id))


# ------------------------------------------------------------------------------ the top-up of a rework the user asked for (D-E5-1, design 4.5)
def test_a_user_rework_below_the_round_with_nothing_spare_asks_for_the_rest(w: ReflectionWorld) -> None:
    """Design 4.5's first example (contract 10 here): 8 used and 2 back, so 8 are committed and the rework gets the 2 that are left; ``ceo`` has 2
    reports, so a round is 5."""
    first = ask(w)
    deliver(w, first, runs=8, budget=2)
    again = w.s.commands.request("root", SERVICE, {"topic": "ai"}, revises=first.id, budget=2, source="human")  # what the default hands down
    text = w.steps.rework_step(again)
    assert text == TOPUP.format(budget=2, need=5, owner="ceo", left=NOTHING_LEFT, ask=3, grant=3)
    assert 'send(to="ceo", budget=3, body=<why>) (CLI: hirearchy send ceo "<why>" --budget 3).' in text


def test_a_user_rework_of_one_run_asks_for_the_four_more_it_needs(w: ReflectionWorld) -> None:
    """Design 4.5's second example: nothing was left, the rework was sent with 1 run."""
    first = ask(w)
    deliver(w, first, runs=8)  # 10 handed down, 8 used, none back
    again = w.s.commands.request("root", SERVICE, {"topic": "ai"}, revises=first.id, budget=1, source="human")
    assert w.steps.rework_step(again) == TOPUP.format(budget=1, need=5, owner="ceo", left=NOTHING_LEFT, ask=4, grant=4)


def test_a_user_rework_with_some_runs_spare_says_how_many_are_left(w: ReflectionWorld) -> None:
    """Contract 3: 1 used, 2 back, the rework gets 1: approved 3, committed 2, so 1 run is spare and the user is asked for the other 3 (a grant of 4)."""
    define(w, name="small", budget=3)
    first = w.s.commands.request("root", "small", {"topic": "ai"})
    deliver(w, first, runs=1, budget=2)
    again = w.s.commands.request("root", "small", {"topic": "ai"}, revises=first.id, budget=1, source="human")
    assert w.steps.rework_step(again) == TOPUP.format(
        budget=1, need=5, owner="ceo", left="1 more of the 3 runs the user approved for this case are left.", ask=3, grant=4,
    )


def test_a_user_rework_at_the_round_or_covered_by_spare_runs_has_no_top_up(w: ReflectionWorld) -> None:
    first = ask(w)
    deliver(w, first, runs=1, budget=9)
    assert w.steps.rework_step(w.s.commands.request("root", SERVICE, {"topic": "ai"}, revises=first.id, budget=5, source="human")) == ""  # at the round
    second = ask(w, "again")
    deliver(w, second, runs=1, budget=9)
    spare = w.s.commands.request("root", SERVICE, {"topic": "ai"}, revises=second.id, budget=2, source="human")
    assert w.steps.rework_step(spare) == ""  # 2 + the 7 that are spare cover the round of 5: root may grant them without asking


def open_request(w: ReflectionWorld, name: str = SERVICE, *, runs: int = 0, status: str | None = None, **over: Any) -> Message:
    """A request the team has used ``runs`` runs for; ``status`` answers it with that result (``blocked`` or ``done``), else it stays unanswered."""
    first = w.s.commands.request("root", name, {"topic": "ai"}, **over)
    if status is not None:
        deliver(w, first, status=status, runs=runs)
    else:
        for _ in range(runs):
            w.use_run("ceo")
    return first


def human_rework(w: ReflectionWorld, first: Message, budget: int, name: str = SERVICE) -> Message:
    return w.s.commands.request("root", name, {"topic": "ai"}, revises=first.id, budget=budget, source="human")


def test_an_open_request_whose_team_holds_the_rest_of_the_round_says_so_and_asks_nothing(w: ReflectionWorld) -> None:
    """D-E6-2, B2 (design 5.3; E6 s3's bc02): 10 handed down, 2 used and the case open: the team holds 10 - 2 = 8 of the user's runs, and the rework's
    1 run plus 8 cover the round of 5, so the step is the HELD sentence alone (0a.3 asked for 4 more)."""
    first = open_request(w, runs=2)
    assert w.steps.rework_step(human_rework(w, first, 1)) == HELD.format(held=8, revised=first.id)


def test_a_blocked_request_is_open_too(w: ReflectionWorld) -> None:
    first = open_request(w, runs=2, status="blocked")
    assert w.steps.rework_step(human_rework(w, first, 1)) == HELD.format(held=8, revised=first.id)


def test_held_runs_that_cover_part_of_the_round_are_in_the_left_part_and_reduce_the_ask_and_the_grant(w: ReflectionWorld) -> None:
    """D-E6-2, B2 (design 5.4's example): round 5, a rework of 1 run, nothing spare, 2 held: the team holds 2, the user is asked for the other 2 and a
    grant of 2 raises the ceiling by exactly the ask."""
    define(w, name="small", budget=3)
    first = open_request(w, "small", runs=1)
    text = w.steps.rework_step(human_rework(w, first, 1, "small"))
    assert text == TOPUP.format(
        budget=1, need=5, owner="ceo", left=f"{HELD.format(held=2, revised=first.id)} {NOTHING_LEFT}", ask=2, grant=2,
    )
    assert 'Ask the user now for 2 more run(s), with that number; on yes, grant 2: send(to="ceo", budget=2, body=<why>)' in text


def test_held_runs_and_spare_runs_together_use_the_some_left_wording(w: ReflectionWorld) -> None:
    """D-E6-2, B2: contract 5, a request of 2 runs with 1 used: the rework (1 run) makes 3 committed, so 2 of the 5 approved are spare and 1 is held;
    5 - 1 - 2 - 1 leaves 1 to ask, and the grant is 5 - 1 - 1 = 3."""
    define(w, name="five", budget=5)
    first = open_request(w, "five", runs=1, budget=2)
    text = w.steps.rework_step(human_rework(w, first, 1, "five"))
    left = f"{HELD.format(held=1, revised=first.id)} {SOME_LEFT.format(spare=2, approved=5)}"
    assert text == TOPUP.format(budget=1, need=5, owner="ceo", left=left, ask=1, grant=3)


def test_a_closed_revised_task_holds_nothing_and_keeps_todays_top_up(w: ReflectionWorld) -> None:
    """D-E6-2, B2 (design 5.7): the same numbers as the first test, with the request delivered: 0a.3's top-up, no HELD sentence."""
    first = open_request(w, runs=2, status="done")
    assert w.steps.rework_step(human_rework(w, first, 1)) == TOPUP.format(budget=1, need=5, owner="ceo", left=NOTHING_LEFT, ask=4, grant=4)


def test_an_open_request_whose_team_holds_nothing_keeps_todays_top_up(w: ReflectionWorld) -> None:
    """D-E6-2, B2: contract 3, all 3 runs used, the case still open: nothing is held, so the step is 0a.3's."""
    define(w, name="small", budget=3)
    first = open_request(w, "small", runs=3)
    assert w.steps.rework_step(human_rework(w, first, 1, "small")) == TOPUP.format(budget=1, need=5, owner="ceo", left=NOTHING_LEFT, ask=4, grant=4)


def test_an_open_request_with_spare_runs_covering_the_round_has_no_step(w: ReflectionWorld) -> None:
    """D-E6-2, B2: what is approved and unused covers the round: root may grant it without asking, whether or not the revised task is open."""
    define(w, name="big", budget=30)
    first = open_request(w, "big", runs=1, budget=2)
    assert w.steps.rework_step(human_rework(w, first, 1, "big")) == ""


def test_an_owner_with_no_agent_below_needs_a_round_of_one_so_no_top_up_is_asked(w: ReflectionWorld) -> None:
    define(w, "ops", "ops-brief")
    first = w.s.commands.request("root", "ops-brief", {"topic": "ai"})
    deliver(w, first, runs=10)
    again = w.s.commands.request("root", "ops-brief", {"topic": "ai"}, revises=first.id, budget=1, source="human")
    assert w.steps.rework_step(again) == ""


def test_an_agent_clients_rework_has_no_top_up(w: ReflectionWorld) -> None:
    w.s.d.post(Message(sender="root", to="ceo", type="note", body="runs for you", title="grant", budget=60))
    define(w, "ceo/eng", "inner", actor="ceo")
    first = w.s.commands.request("ceo", "inner", {"topic": "ai"})
    deliver(w, first, runs=10)
    again = w.s.d.post(Message(
        sender="ceo", to="ceo/eng", type="task", title="inner: ai", body="again", budget=1, revises=first.id, service="inner", source="human",
    ))
    assert w.steps.rework_step(again) == ""


def test_a_human_rework_of_a_retired_service_has_no_top_up(w: ReflectionWorld) -> None:
    first = ask(w)
    deliver(w, first, runs=10)
    again = w.s.commands.request("root", SERVICE, {"topic": "ai"}, revises=first.id, budget=1, source="human")
    w.s.commands.retire_service("root", "ceo", SERVICE, "obsolete")
    assert w.steps.rework_step(again) == ""
