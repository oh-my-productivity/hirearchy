"""``moved_past``: has the assigner of a blocked task moved past it? A later rework or a verdict after the block says yes (pure)."""

from __future__ import annotations

from hirearchy.kernel import Message
from hirearchy.mail import moved_past


def stamp(n: int, who: str = "root") -> str:
    return f"20260101T0000{n:02d}000000-{who}-{n:04d}"


def task(n: int, sender: str = "root", revises: str | None = None) -> Message:
    return Message(id=stamp(n, sender), sender=sender, to="ceo", type="task", title=f"T{n}", body="b", revises=revises)


def blocked_result(n: int, of: Message) -> Message:
    return Message(id=stamp(n, "ceo"), sender="ceo", to=of.sender, type="result", status="blocked", reply_to=of.id, body="stuck", title="r")


def verdict(n: int, on: Message, sender: str = "root") -> Message:
    return Message(id=stamp(n, sender), sender=sender, to="ceo", type="note", feedback="accept", reply_to=on.id, body="ok", title="n")


def test_a_later_rework_of_the_task_moves_past_it() -> None:
    first = task(1)
    block = blocked_result(2, first)
    rework = task(3, revises=first.id)
    assert moved_past(first, block, [first, rework])


def test_a_second_rework_of_the_same_delivery_moves_past_it() -> None:
    original = task(1)
    first_rework = task(2, revises=original.id)
    block = blocked_result(3, first_rework)
    second_rework = task(4, revises=original.id)  # sent back from the same delivery, not from the blocked rework
    assert moved_past(first_rework, block, [original, first_rework, second_rework])


def test_a_verdict_after_the_block_moves_past_it() -> None:
    first = task(1)
    block = blocked_result(2, first)
    assert moved_past(first, block, [first, verdict(3, first)])
    rework = task(4, revises=first.id)
    assert moved_past(rework, blocked_result(5, rework), [first, rework, verdict(6, first)])  # a verdict on the chain's other task counts


def test_a_verdict_before_the_block_does_not() -> None:
    first = task(1)
    early = verdict(2, first)
    block = blocked_result(3, first)
    assert not moved_past(first, block, [first, early])


def test_another_senders_task_or_verdict_does_not() -> None:
    first = task(1)
    block = blocked_result(2, first)
    stranger_rework = task(3, sender="ops", revises=first.id)
    stranger_verdict = verdict(4, first, sender="ops")
    assert not moved_past(first, block, [first, stranger_rework, stranger_verdict])


def test_without_a_later_task_or_verdict_nothing_moves_past() -> None:
    first = task(1)
    block = blocked_result(2, first)
    earlier = task(0, revises=first.id)  # older than the task: not a later one
    unrelated = task(3)  # a later task that revises nothing of the chain
    result = blocked_result(4, first)
    plain_note = Message(id=stamp(5), sender="root", to="ceo", type="note", reply_to=first.id, body="fyi", title="n")  # no verdict
    assert not moved_past(first, block, [])
    assert not moved_past(first, block, [first, earlier, unrelated, result, plain_note])
