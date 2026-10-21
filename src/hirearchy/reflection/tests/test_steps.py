"""``TextServiceSteps``: what root is told to do next after it recorded a rejection, and after it amended a contract (design 3.4, DR-19, DR-27).

The user's yes is what makes a link the client's, so both texts name the one question to ask and the one call that records the answer; they are
advice and never write anything."""

from __future__ import annotations

from pathlib import Path

import pytest

from hirearchy.kernel import Message, OrgError
from hirearchy.reflection.testing import ReflectionWorld, fs_world, memory_world

from ._support import SERVICE, ask, define, deliver, nested, note_on, populated, rate

QUESTION = (
    'ask the user ONE yes/no question that names what it is about by an id, a criterion ({criteria}) or an earlier rejection ({rejections}), e.g. '
    '"About C<k>: add \'<the rule in their words>\' as a criterion?" or "Same as R<j>: a one-off?". "Always ..." is not their yes: ask anyway. '
    "Only after their yes call define_service (when the answer changes the contract), then record the answer: "
    'feedback(task_id="{task}", verdict="reject", confirms="{note}", criterion=["<the id>"], source="human", note="<their answer, verbatim>").'
)
NOT_YET = (
    'Rejection {rejection} (message {note}) has no recorded yes. The yes is the user\'s answer to your ONE yes/no question naming {names}; an "Always ..." '
    'in the rejection is not it. If you have not asked that question, ask it now and record nothing. Only after they answer yes: '
    'feedback(task_id="{task}", verdict="reject", confirms="{note}", criterion=[{quoted}], source="human", note="<their answer, verbatim>").'
)


@pytest.fixture(params=[fs_world, memory_world], ids=lambda f: f.__name__)
def w(request: pytest.FixtureRequest, tmp_path: Path) -> ReflectionWorld:
    made = populated(request.param(tmp_path))
    define(made)
    return made


def amend(w: ReflectionWorld, **over: object) -> None:
    w.s.commands.define_service("root", "ceo", SERVICE, **over)  # type: ignore[arg-type]


def rejected(w: ReflectionWorld, words: str = "Too long.", *, topic: str = "ai", **kw: object) -> tuple[Message, Message]:
    """A new case: the request, its delivery and the user's rejection; returns (request, verdict note)."""
    task = ask(w, topic)
    deliver(w, task)
    return task, rate(w, task, "reject", words, **kw)


# ------------------------------------------------------------------------------ feedback_step


def test_feedback_step_names_the_ids_and_the_confirmation(w: ReflectionWorld) -> None:
    rejected(w, "First.", topic="a")  # two earlier human rejections, in other cases: the new one is the third of the service (DR-19)
    rejected(w, "Second.", topic="b")
    task, note = rejected(w, "Third.", topic="c")
    assert w.steps.feedback_step(note) == "This rejection is R3. Next, before define_service: " + QUESTION.format(
        criteria="C1, C2", rejections="R1, R2", task=task.id, note=note.id,
    )


def test_feedback_step_with_no_other_rejection_says_none(w: ReflectionWorld) -> None:
    _, note = rejected(w)
    text = w.steps.feedback_step(note)
    assert text.startswith("This rejection is R1. Next, before define_service: ") and "or an earlier rejection (none), e.g." in text


def test_feedback_step_says_an_own_criterion_is_not_confirmed(w: ReflectionWorld) -> None:
    task, note = rejected(w, criterion=["C2"])
    text = w.steps.feedback_step(note)
    assert text.startswith("The criterion on the rejection itself (C2) is recorded as not confirmed. This rejection is R1. Next, ")
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


# ------------------------------------------------------------------------------ amendment_step


def test_amendment_step_after_an_unconfirmed_reject(w: ReflectionWorld) -> None:
    task, note = rejected(w, "Needs a week.")
    amend(w, add_acceptance=["Names the week it covers", "Ends with one open question"])  # C3 and C4
    assert w.steps.amendment_step("ceo", SERVICE) == "Not client-confirmed: C3, C4. " + NOT_YET.format(
        rejection="R1", note=note.id, task=task.id, names="C3, C4", quoted='"C3", "C4"',
    )


def test_amendment_step_after_a_confirmed_reject_says_only_not_confirmed(w: ReflectionWorld) -> None:
    task, note = rejected(w, "Needs a source.")
    note_on(w, task, reply_to=note.id, criterion="C1", source="human")  # the latest rejection already has the user's answer
    amend(w, add_acceptance=["Ends with one open question"])
    assert w.steps.amendment_step("ceo", SERVICE) == "Not client-confirmed: C3."


def test_amendment_step_after_a_none_answer_says_only_not_confirmed(w: ReflectionWorld) -> None:
    task, note = rejected(w, "Only this once.")
    note_on(w, task, reply_to=note.id, criterion="none", source="human")
    amend(w, add_acceptance=["Ends with one open question"])
    assert w.steps.amendment_step("ceo", SERVICE) == "Not client-confirmed: C3."


def test_amendment_step_names_the_latest_rejection(w: ReflectionWorld) -> None:
    rejected(w, "First.", topic="a")
    task, latest = rejected(w, "Second.", topic="b")
    amend(w, add_acceptance=["Names the week it covers"])
    text = w.steps.amendment_step("ceo", SERVICE)
    assert f"Rejection R2 (message {latest.id}) has no recorded yes." in text and f'task_id="{task.id}"' in text


def test_amendment_step_names_only_what_the_latest_version_added(w: ReflectionWorld) -> None:
    rejected(w)
    amend(w, add_acceptance=["Names the week it covers"])  # v2: C3
    amend(w, add_acceptance=["Ends with one open question"])  # v3: C4
    assert w.steps.amendment_step("ceo", SERVICE).startswith("Not client-confirmed: C4. Rejection R1 ")


def test_amendment_step_is_empty_outside_a_rejection_or_when_everything_is_confirmed(w: ReflectionWorld) -> None:
    amend(w, add_acceptance=["Names the week it covers"])  # no rejection at all: DR-27, the user's own amendment gets no step
    assert w.steps.amendment_step("ceo", SERVICE) == ""
    task, note = rejected(w, "No question.")
    amend(w, add_acceptance=["Ends with one open question"])  # C4, after a rejection
    assert w.steps.amendment_step("ceo", SERVICE) != ""
    note_on(w, task, reply_to=note.id, criterion="C4", source="human")  # the user said yes to it
    assert w.steps.amendment_step("ceo", SERVICE) == ""
    amend(w, budget=12)  # nothing added
    assert w.steps.amendment_step("ceo", SERVICE) == ""
    assert w.steps.amendment_step("ceo", "no-such-service") == ""  # a service without a contract


def test_amendment_step_refuses_an_unknown_owner(w: ReflectionWorld) -> None:
    with pytest.raises(OrgError, match="no such agent: ghost"):
        w.steps.amendment_step("ghost", SERVICE)
