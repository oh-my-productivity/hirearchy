"""``check_root_send``: what ``Org.send`` refuses to send for root, and ``GuardedRootSender``, the sender the facade hands out (P4, design 7.5).

The rule classes (``request``, ``delegate``, ``feedback``) send these shapes through the unguarded ``MessageSender`` after their own rules; the facade's
free-form ``send`` is the one door that did not apply them. Every other message passes, with every argument unchanged."""

from __future__ import annotations

import pytest

from hirearchy.delivery.testing import RecordingDelivery
from hirearchy.dispatch import GuardedSender, MessageSender, check_root_send
from hirearchy.dispatch._guarded import GuardedRootSender
from hirearchy.dispatch._root_send import FACADE_ACKNOWLEDGES, FACADE_ROOT_TASK, FACADE_ROOT_VERDICT
from hirearchy.dispatch.testing import RecordingSender
from hirearchy.kernel import Message, OrgError
from hirearchy.kernel.testing import FakeClock, SequenceIdGenerator

TEXT = (
    "refused: a root task for a service, or a rework, goes through request(...) or delegate(...), which apply the case rules (the contract, the "
    "base, the verdicts). Nothing was sent."
)


VERDICT = (
    "refused: a verdict or a link from root goes through feedback(...), which applies the rules of a case (a delivered request, one answer per "
    "rejection). Nothing was sent."
)


def test_the_text_of_the_refusal() -> None:
    assert FACADE_ROOT_TASK == TEXT and FACADE_ROOT_VERDICT == VERDICT


@pytest.mark.parametrize("actor", ["root", " /root/ "])
@pytest.mark.parametrize("fields", [{"service": "weekly-brief"}, {"revises": "20260101T000000000001-root-aaaa"}, {"service": "s", "revises": "r"}])
def test_check_root_send_refuses_a_root_task_with_service_or_revises(actor: str, fields: dict[str, str]) -> None:
    with pytest.raises(OrgError) as refusal:
        check_root_send(actor, "task", fields.get("service"), fields.get("revises"), None, None)
    assert str(refusal.value) == TEXT


@pytest.mark.parametrize("actor", ["root", " /root/ "])
@pytest.mark.parametrize("fields", [{"feedback": "reject"}, {"feedback": "accept"}, {"criterion": "C1"}, {"feedback": "reject", "criterion": "C1, R2"}])
def test_check_root_send_refuses_a_root_note_with_feedback_or_criterion(actor: str, fields: dict[str, str]) -> None:
    with pytest.raises(OrgError) as refusal:
        check_root_send(actor, "note", None, None, fields.get("feedback"), fields.get("criterion"))
    assert str(refusal.value) == VERDICT


def test_the_task_rule_comes_first_and_a_task_with_a_verdict_field_is_refused_as_a_task() -> None:
    with pytest.raises(OrgError) as refusal:
        check_root_send("root", "task", "weekly-brief", None, "reject", "C1")
    assert str(refusal.value) == TEXT


@pytest.mark.parametrize(("actor", "type", "service", "revises"), [
    ("root", "task", None, None),  # a one-off task
    ("root", "task", "", ""),
    ("root", "note", None, None),  # a plain note, a budget grant
    ("root", "note", "weekly-brief", "r1"),  # service and revises mean something on a task only
    ("root", "result", "weekly-brief", "r1"),
    ("ceo", "task", "weekly-brief", "r1"),  # an agent's rework of a service request keeps its case
    ("ceo", "task", "weekly-brief", None),
    ("ceo/eng", "task", None, "r1"),
])
def test_other_messages_pass(actor: str, type: str, service: str | None, revises: str | None) -> None:
    check_root_send(actor, type, service, revises, None, None)


@pytest.mark.parametrize(("actor", "type"), [("ceo", "note"), ("ceo/eng", "note"), ("root", "task"), ("root", "result"), ("ceo", "task")])
def test_a_verdict_or_link_field_is_refused_for_root_notes_only(actor: str, type: str) -> None:
    check_root_send(actor, type, None, None, "reject", "C1")  # an agent's note is refused later, by provenance (S1); a task or result is no verdict


class Spy(MessageSender):
    """Keeps the arguments of every send."""

    def __init__(self) -> None:
        self.calls: list[tuple[tuple[str, str, str], dict[str, object]]] = []

    def send(self, actor: str, to: str, body: str, **kw: object) -> Message:
        self.calls.append(((actor, to, body), kw))
        return Message(sender=actor, to=to, type="note", body=body, id="FROM-THE-INNER")


def test_the_guarded_sender_is_a_message_sender_and_a_guarded_one() -> None:
    guard = GuardedRootSender(Spy())
    assert isinstance(guard, MessageSender) and isinstance(guard, GuardedSender)


def test_the_guarded_sender_passes_every_other_message_unchanged() -> None:
    inner = Spy()
    fields = dict(
        type="task", title="T", reply_to="r1", status="done", budget=3, revises="r2", supersedes="r3", service="svc", contract=2, playbook=4,
        feedback="accept", source="human", criterion="C1", wake=False, skip_route_check=True, inherited="human", acknowledges=None,
    )
    sent = GuardedRootSender(inner).send("ceo", "ceo/eng", "body", **fields)  # type: ignore[arg-type]
    assert sent.id == "FROM-THE-INNER" and inner.calls == [(("ceo", "ceo/eng", "body"), fields)]
    GuardedRootSender(inner).send("root", "ceo", "a budget", type="note", budget=4)
    assert inner.calls[1] == (("root", "ceo", "a budget"), {
        "type": "note", "title": "", "reply_to": None, "status": None, "budget": 4, "revises": None, "supersedes": None, "service": None,
        "contract": None, "playbook": None, "feedback": None, "source": None, "criterion": None, "wake": True, "skip_route_check": False,
        "inherited": None, "acknowledges": None,
    })


def test_the_guarded_sender_sends_nothing_when_it_refuses() -> None:
    inner = Spy()
    with pytest.raises(OrgError):
        GuardedRootSender(inner).send("root", "ceo", "again", type="task", revises="r1", source="human")
    with pytest.raises(OrgError):
        GuardedRootSender(inner).send("root", "ceo", "a request", type="task", service="weekly-brief")
    assert inner.calls == []


def test_the_guard_is_over_any_sender() -> None:
    clock = FakeClock()
    recording = RecordingSender(RecordingDelivery(clock, SequenceIdGenerator(clock)))
    assert GuardedRootSender(recording).send("root", "ceo", "one-off", type="task").type == "task" and len(recording.messages) == 1


ACKNOWLEDGES = (
    "refused: an acknowledgement of a playbook change is written by acknowledge_playbook(...), which checks that its writer is the owner's parent. "
    "Nothing was sent."
)


def test_the_text_of_the_acknowledgement_refusal() -> None:
    assert FACADE_ACKNOWLEDGES == ACKNOWLEDGES


@pytest.mark.parametrize("actor", ["root", " /root/ ", "ceo", "ceo/eng"])
@pytest.mark.parametrize("type", ["note", "task", "result"])
def test_check_root_send_refuses_acknowledges_from_any_actor(actor: str, type: str) -> None:
    with pytest.raises(OrgError) as refusal:
        check_root_send(actor, type, None, None, None, None, "weekly-brief retire P3")
    assert str(refusal.value) == ACKNOWLEDGES


def test_the_facade_sender_refuses_acknowledges() -> None:
    inner = Spy()
    for actor in ("root", "ceo"):
        with pytest.raises(OrgError) as refusal:
            GuardedRootSender(inner).send(actor, "ceo/eng", "yes", acknowledges="weekly-brief retire P3")
        assert str(refusal.value) == ACKNOWLEDGES
    assert inner.calls == []
    clock = FakeClock()
    recording = RecordingSender(RecordingDelivery(clock, SequenceIdGenerator(clock)))
    with pytest.raises(OrgError):
        GuardedRootSender(recording).send("root", "ceo", "forged", acknowledges="weekly-brief retire P3")
    assert recording.messages == []
