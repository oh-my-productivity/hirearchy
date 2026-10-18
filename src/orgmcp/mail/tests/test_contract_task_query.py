"""Contract of ``TaskQuery``: derived over the mailboxes on disk and over the in-memory ones, it gives the same answers."""

from __future__ import annotations

from pathlib import Path

import pytest

from orgmcp.kernel import Message
from orgmcp.mail import TaskQuery
from orgmcp.mail.testing import IMPLEMENTATIONS, MailHarness

from ._support import agents, make, mid, put, still_red




@pytest.fixture(params=still_red(IMPLEMENTATIONS[TaskQuery]), ids=lambda factory: factory.__name__)
def h(request: pytest.FixtureRequest, tmp_path: Path) -> MailHarness:
    made = make(request, tmp_path)
    assert isinstance(made.tasks, TaskQuery)
    agents(made, "ceo", "ceo/eng")
    return made


def task_to_ceo(h: MailHarness, n: int, box: str = "inbox", **kw: object) -> str:
    return put(h, "ceo", box, n, kind="task", **kw)


def result_from_ceo(h: MailHarness, n: int, task_id: str, status: str = "done", **kw: object) -> str:
    return put(h, "ceo", "sent", n, sender="ceo", to="root", kind="result", reply_to=task_id, status=status, **kw)


def ids(messages: list[Message]) -> list[str]:
    return [m.id for m in messages]


# ------------------------------------------------------------------------------ open_tasks


def test_a_received_task_is_open_until_a_result_answers_it(h: MailHarness) -> None:
    t1, t2 = task_to_ceo(h, 1), task_to_ceo(h, 2)
    assert ids(h.tasks.open_tasks("ceo")) == [t1, t2]
    result_from_ceo(h, 3, t1)
    assert ids(h.tasks.open_tasks("ceo")) == [t2]


def test_a_task_counts_in_every_received_box(h: MailHarness) -> None:
    a, b, c = task_to_ceo(h, 1, "inbox"), task_to_ceo(h, 2, "inflight"), task_to_ceo(h, 3, "read")
    assert ids(h.tasks.open_tasks("ceo")) == [a, b, c]


def test_notes_and_results_are_not_tasks(h: MailHarness) -> None:
    put(h, "ceo", "inbox", 1, kind="note")
    put(h, "ceo", "inbox", 2, kind="result", reply_to="x", status="done")
    assert h.tasks.open_tasks("ceo") == []


def test_only_a_result_the_agent_sent_answers_a_task(h: MailHarness) -> None:
    t = task_to_ceo(h, 1)
    put(h, "ceo", "inbox", 2, kind="result", reply_to=t, status="done", sender="ceo/eng")  # somebody else's result
    put(h, "ceo", "sent", 3, sender="ceo", to="ceo/eng", kind="note", reply_to=t)  # a note is no result
    assert ids(h.tasks.open_tasks("ceo")) == [t]


def test_any_status_of_result_closes_the_task_for_open_tasks(h: MailHarness) -> None:
    t = task_to_ceo(h, 1)
    result_from_ceo(h, 2, t, status="blocked")
    assert h.tasks.open_tasks("ceo") == []


def test_the_address_is_normalized(h: MailHarness) -> None:
    t = task_to_ceo(h, 1)
    assert ids(h.tasks.open_tasks(" /ceo/ ")) == [t]


def test_an_agent_with_no_mail_has_no_tasks(h: MailHarness) -> None:
    assert h.tasks.open_tasks("ceo/eng") == [] and h.tasks.outstanding("ceo/eng") == [] and h.tasks.blocked_tasks("ceo/eng") == []


# ------------------------------------------------------------------------------ outstanding


def sent_task(h: MailHarness, n: int, to: str = "ceo/eng") -> str:
    return put(h, "ceo", "sent", n, sender="ceo", to=to, kind="task")


def test_a_sent_task_is_outstanding_until_a_result_comes_back(h: MailHarness) -> None:
    t1, t2 = sent_task(h, 1), sent_task(h, 2)
    assert ids(h.tasks.outstanding("ceo")) == [t1, t2]
    put(h, "ceo", "inbox", 3, sender="ceo/eng", kind="result", reply_to=t1, status="done")
    assert ids(h.tasks.outstanding("ceo")) == [t2]


def test_a_result_in_any_received_box_answers_a_sent_task(h: MailHarness) -> None:
    ts = [sent_task(h, n) for n in (1, 2, 3)]
    for n, (box, t) in enumerate(zip(("inbox", "inflight", "read"), ts), 4):
        put(h, "ceo", box, n, sender="ceo/eng", kind="result", reply_to=t, status="done")
    assert h.tasks.outstanding("ceo") == []


def test_a_sent_note_is_not_outstanding(h: MailHarness) -> None:
    put(h, "ceo", "sent", 1, sender="ceo", to="ceo/eng", kind="note")
    assert h.tasks.outstanding("ceo") == []


def test_a_result_sent_by_the_agent_does_not_answer_its_own_task(h: MailHarness) -> None:
    t = sent_task(h, 1)
    result_from_ceo(h, 2, t)
    assert ids(h.tasks.outstanding("ceo")) == [t]


# ------------------------------------------------------------------------------ blocked_tasks


def test_a_task_whose_latest_result_is_blocked_is_blocked(h: MailHarness) -> None:
    t = task_to_ceo(h, 1)
    result_from_ceo(h, 2, t, status="blocked")
    assert ids(h.tasks.blocked_tasks("ceo")) == [t]


def test_a_later_result_supersedes_a_blocked_one(h: MailHarness) -> None:
    t = task_to_ceo(h, 1)
    result_from_ceo(h, 2, t, status="blocked")
    result_from_ceo(h, 3, t, status="done", supersedes=mid(2, "ceo"))
    assert h.tasks.blocked_tasks("ceo") == []


def test_the_latest_result_is_the_one_with_the_highest_id(h: MailHarness) -> None:
    t = task_to_ceo(h, 1)
    result_from_ceo(h, 2, t, status="done")
    result_from_ceo(h, 3, t, status="blocked")
    assert ids(h.tasks.blocked_tasks("ceo")) == [t]


def test_a_task_without_a_result_is_not_blocked(h: MailHarness) -> None:
    task_to_ceo(h, 1)
    assert h.tasks.blocked_tasks("ceo") == []


def test_blocked_tasks_are_open_tasks_too_in_the_sense_that_they_were_answered_once(h: MailHarness) -> None:
    t = task_to_ceo(h, 1)
    result_from_ceo(h, 2, t, status="blocked")
    assert h.tasks.open_tasks("ceo") == [] and ids(h.tasks.blocked_tasks("ceo")) == [t]
