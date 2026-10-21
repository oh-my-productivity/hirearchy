"""``SoleUpstreamTask``: the one task of an agent that a delegation probably serves."""

from __future__ import annotations

import pytest

from hirearchy.kernel import Message
from hirearchy.mail.testing import MemoryMailbox
from hirearchy.prompts._ports import UpstreamTasks
from hirearchy.prompts._upstream import SoleUpstreamTask



def at(n: int, sender: str = "root") -> str:
    return f"20260101T0000000000{n:02d}-{sender}-aaaa"


class Story:
    """``ceo`` receives tasks and delegates to ``ceo/eng``; ids grow with the number."""

    def __init__(self) -> None:
        self.box = MemoryMailbox()
        self.upstream: UpstreamTasks = SoleUpstreamTask(self.box)

    def task(self, n: int, to: str = "ceo", sender: str = "root") -> Message:
        msg = Message(sender=sender, to=to, type="task", title=f"T{n}", body="b", id=at(n, sender))
        self.box.store(msg)
        return msg

    def result(self, n: int, task: Message, status: str) -> Message:
        msg = Message(sender="ceo", to="root", type="result", title="r", body="b", id=at(n, "ceo"), reply_to=task.id, status=status)
        self.box.store(msg)
        return msg


def test_the_one_task_received_before_the_delegation_and_still_open() -> None:
    s = Story()
    mine = s.task(1)
    sub = s.task(5, "ceo/eng", "ceo")
    assert s.upstream.upstream("ceo", sub) == (mine, None)


def test_a_task_received_after_the_delegation_is_not_a_candidate() -> None:
    s = Story()
    sub = s.task(1, "ceo/eng", "ceo")
    s.task(5)
    assert s.upstream.upstream("ceo", sub) is None


def test_two_candidates_mean_no_answer() -> None:
    s = Story()
    s.task(1)
    s.task(2)
    assert s.upstream.upstream("ceo", s.task(5, "ceo/eng", "ceo")) is None


def test_a_task_reported_done_before_the_delegation_is_not_a_candidate() -> None:
    s = Story()
    s.result(2, s.task(1), "done")
    assert s.upstream.upstream("ceo", s.task(5, "ceo/eng", "ceo")) is None


def test_a_task_reported_blocked_is_a_candidate_with_its_result() -> None:
    s = Story()
    mine = s.task(1)
    blocked = s.result(2, mine, "blocked")
    assert s.upstream.upstream("ceo", s.task(5, "ceo/eng", "ceo")) == (mine, blocked)


def test_a_task_reported_after_the_delegation_is_a_candidate_with_its_result() -> None:
    s = Story()
    mine = s.task(1)
    sub = s.task(5, "ceo/eng", "ceo")
    done = s.result(7, mine, "done")
    assert s.upstream.upstream("ceo", sub) == (mine, done)


def test_only_tasks_count_not_notes() -> None:
    s = Story()
    s.box.store(Message(sender="root", to="ceo", type="note", title="n", body="b", id=at(1)))
    assert s.upstream.upstream("ceo", s.task(5, "ceo/eng", "ceo")) is None
