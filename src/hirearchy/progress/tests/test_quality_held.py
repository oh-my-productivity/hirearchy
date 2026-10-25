"""``held_tasks``, ``left_blocked`` and ``blocked_listing``: the tasks a blocked result holds runs on, and those the sender moved past (0b 4.5; pure)."""

from __future__ import annotations

from hirearchy.kernel import Message, latest_results
from hirearchy.mail import moved_past
from hirearchy.progress._quality import blocked_listing, held_tasks, left_blocked


def stamp(n: int, who: str = "root") -> str:
    return f"20260101T0000{n:02d}000000-{who}-{n:04d}"


def task(n: int, sender: str = "root", revises: str | None = None, to: str = "ceo") -> Message:
    return Message(id=stamp(n, sender), sender=sender, to=to, type="task", title=f"T{n}", body="b", revises=revises)


def blocked_result(n: int, of: Message) -> Message:
    return Message(id=stamp(n, of.to), sender=of.to, to=of.sender, type="result", status="blocked", reply_to=of.id, body="stuck", title="r")


def verdict(n: int, on: Message, sender: str = "root") -> Message:
    return Message(id=stamp(n, sender), sender=sender, to="ceo", type="note", feedback="accept", reply_to=on.id, body="ok", title="n")


def latest(*blocks: Message) -> dict[str, Message]:
    return latest_results(blocks)


def test_a_blocked_task_that_moved_past_releases_is_not_held() -> None:
    first = task(1)
    block = blocked_result(2, first)
    received = [first, task(3, revises=first.id)]
    assert moved_past(first, block, received)
    assert held_tasks([first], latest(block), received) == []


def test_a_blocked_task_superseded_by_a_rework_is_released() -> None:
    original = task(1)
    first_rework = task(2, revises=original.id)
    block = blocked_result(3, first_rework)
    received = [original, first_rework, task(4, revises=original.id)]  # a second rework of the same delivery
    assert held_tasks([first_rework], latest(block), received) == []


def test_a_verdict_after_the_block_releases_it() -> None:
    first = task(1)
    block = blocked_result(2, first)
    assert held_tasks([first], latest(block), [first, verdict(3, first)]) == []
    assert held_tasks([first], latest(block), [first, verdict(0, first)]) == [first]  # a verdict before the block does not


def test_a_later_task_inside_the_chain_does_not_leave_it_blocked() -> None:
    first = task(1)
    sibling = task(2, revises=first.id)  # another rework of the same delivery, older than the blocked one
    held = task(3, revises=first.id)
    block = blocked_result(4, held)
    inside = task(5, revises=sibling.id)  # sent after the block, connected to the chain through the sibling; it revises neither `held` nor `first`
    received = [first, sibling, held, inside]
    assert not moved_past(held, block, received)  # so the block still holds runs ...
    assert held_tasks([held], latest(block), received) == [held]
    assert left_blocked(held, block, received) == 0  # ... but the sender has not moved past it: the task is inside the chain
    assert left_blocked(held, block, [*received, task(6)]) == 1  # an unrelated task of the sender is outside it


def test_a_task_from_the_sender_outside_the_chain_leaves_it_blocked_with_the_count_sent_since() -> None:
    first = task(1)
    block = blocked_result(2, first)
    unrelated = task(3)  # revises nothing: outside the chain
    another = task(4)
    before = task(0)  # sent before the block: not counted
    stranger = task(5, sender="ops")  # another sender: not counted
    received = [before, first, unrelated, another, stranger]
    assert held_tasks([first], latest(block), received) == [first]
    assert left_blocked(first, block, received) == 2
    assert left_blocked(first, block, [first]) == 0


def test_a_held_task_with_nothing_sent_since_is_listed_beside_a_left_blocked_one() -> None:
    left, quiet = task(1), task(2, sender="ceo/lead", to="ceo")
    left_block, quiet_block = blocked_result(3, left), blocked_result(4, quiet)
    received = [left, quiet, task(5)]  # root sent ceo another task after the first block
    listed = blocked_listing([left, quiet], latest(left_block, quiet_block), received)
    assert [(h.task.id, h.blocked.id, h.sent_since, h.left_blocked) for h in listed] == [
        (left.id, left_block.id, 1, True), (quiet.id, quiet_block.id, 0, False),
    ]


def test_an_agent_without_a_left_blocked_task_is_not_listed() -> None:
    quiet = task(1)
    block = blocked_result(2, quiet)
    assert held_tasks([quiet], latest(block), [quiet]) == [quiet]  # it is held, so its assignee is busy ...
    assert blocked_listing([quiet], latest(block), [quiet]) == ()  # ... but none is left blocked, so the agent is not listed
    assert blocked_listing([], {}, []) == ()


def test_the_listing_is_oldest_block_first() -> None:
    a, b = task(1), task(2)
    late, early = blocked_result(8, a), blocked_result(3, b)
    listed = blocked_listing([a, b], latest(late, early), [a, b, task(9)])
    assert [h.task.id for h in listed] == [b.id, a.id]
