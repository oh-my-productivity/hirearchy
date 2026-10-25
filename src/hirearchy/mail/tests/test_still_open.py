"""``still_open`` (D-E7-2 F-E7-7): does the assignee of a task still owe a report on it? No result, or a ``blocked`` one its assigner has not moved past (pure)."""

from __future__ import annotations

from hirearchy.kernel import Message
from hirearchy.mail import still_open


def stamp(n: int, who: str = "root") -> str:
    return f"20260101T0000{n:02d}000000-{who}-{n:04d}"


def task(n: int, sender: str = "root", revises: str | None = None) -> Message:
    return Message(id=stamp(n, sender), sender=sender, to="ceo", type="task", title=f"T{n}", body="b", revises=revises)


def result(n: int, of: Message, status: str) -> Message:
    return Message(id=stamp(n, "ceo"), sender="ceo", to=of.sender, type="result", status=status, reply_to=of.id, body="r", title="r")


def verdict(n: int, on: Message, kind: str = "accept", sender: str = "root", source: str | None = "human") -> Message:
    return Message(id=stamp(n, sender), sender=sender, to="ceo", type="note", feedback=kind, reply_to=on.id, body="v", title="n", source=source)


def test_a_task_without_a_result_is_open() -> None:
    first = task(1)
    assert still_open(first, None, [first])


def test_a_done_or_failed_result_closes_the_task() -> None:
    first = task(1)
    assert not still_open(first, result(2, first, "done"), [first])
    assert not still_open(first, result(2, first, "failed"), [first])


def test_a_final_result_that_superseded_a_blocked_one_closes_the_task() -> None:
    """The latest result decides: the lead re-reported the blocked task ``done``."""
    first = task(1)
    assert not still_open(first, result(3, first, "done"), [first, verdict(4, first)])


def test_a_blocked_result_with_nothing_after_it_is_open() -> None:
    first = task(1)
    assert still_open(first, result(2, first, "blocked"), [first])


def test_a_grant_note_after_the_block_leaves_it_open() -> None:
    """E7 s1's 0036: root's note after the block carries runs, not a verdict (no ``feedback``)."""
    first = task(1)
    grant = Message(id=stamp(3), sender="root", to="ceo", type="note", reply_to=first.id, body="3 runs", title="grant", budget=3)
    assert still_open(first, result(2, first, "blocked"), [first, grant])


def test_a_verdict_of_the_sender_on_the_task_after_the_block_closes_it() -> None:
    """E7 s3's dd46: the user's accept after the block."""
    first = task(1)
    block = result(2, first, "blocked")
    for kind, source in (("accept", "human"), ("reject", "human"), ("accept", "relayed"), ("reject", None)):
        assert not still_open(first, block, [first, verdict(3, first, kind, source=source)]), (kind, source)


def test_a_relayed_verdict_on_another_task_of_the_chain_closes_it() -> None:
    """Design 6.2, Deviation 5: ``moved_past`` is the one rule, so a verdict on the chain's head closes the blocked rework, any tier."""
    head = task(1)
    rework = task(2, revises=head.id)
    block = result(3, rework, "blocked")
    assert not still_open(rework, block, [head, rework, verdict(4, head, "reject", source="relayed")])


def test_a_later_rework_of_the_task_closes_it() -> None:
    first = task(1)
    assert not still_open(first, result(2, first, "blocked"), [first, task(3, revises=first.id)])


def test_a_verdict_before_the_block_leaves_it_open() -> None:
    first = task(1)
    assert still_open(first, result(3, first, "blocked"), [first, verdict(2, first)])


def test_a_verdict_or_rework_of_another_sender_leaves_it_open() -> None:
    first = task(1)
    block = result(2, first, "blocked")
    assert still_open(first, block, [first, verdict(3, first, sender="ops"), task(4, sender="ops", revises=first.id)])
