"""``MailClientRework``: the reworks of a service case that the client sent back, found in the boxes of the sender and the receiver.

The analyzer's suites (``test_client_rework.py``) pin what the flags and counters say; this pins the function itself on a few messages."""

from __future__ import annotations

from pathlib import Path

from orgmcp.health._rework import MailClientRework
from orgmcp.kernel import Message, latest_results
from orgmcp.mail.testing import MailHarness, MemoryMailbox, memory_mailbox


def build(tmp_path: Path) -> tuple[MailHarness, MailClientRework]:
    mail = memory_mailbox(tmp_path)
    box = mail.reader
    assert isinstance(box, MemoryMailbox)
    for addr in ("ceo", "ceo/eng", "ops"):
        mail.agent(addr)
    return mail, MailClientRework(box.agents, mail.reader)


def put(mail: MailHarness, n: int, sender: str, to: str, type: str = "task", **fields: object) -> Message:
    msg = Message(sender=sender, to=to, type=type, title="t", body="b", id=f"20260101T0000{n:02d}000000-{sender.replace('/', '.')}-{n:04x}",
                  created="2026-01-01T00:00:00+00:00", **fields)  # type: ignore[arg-type]
    mail.writer.store(msg)
    return msg


def test_nothing_is_driven_without_reworks(tmp_path: Path) -> None:
    mail, rework = build(tmp_path)
    task = put(mail, 1, "root", "ceo")
    assert rework.driven([task], {}) == set()
    assert rework.driven([], {}) == set()


def test_a_service_rework_after_a_done_result_is_driven(tmp_path: Path) -> None:
    mail, rework = build(tmp_path)
    first = put(mail, 1, "root", "ceo", service="memo")
    result = put(mail, 2, "ceo", "root", "result", reply_to=first.id, status="done")
    again = put(mail, 3, "root", "ceo", service="memo", revises=first.id)
    assert rework.driven([first, again], latest_results([result])) == {again.id}


def test_a_service_rework_is_not_driven_by_a_result_that_is_not_done_or_that_came_later(tmp_path: Path) -> None:
    mail, rework = build(tmp_path)
    first = put(mail, 1, "root", "ceo", service="memo")
    again = put(mail, 2, "root", "ceo", service="memo", revises=first.id)
    late = put(mail, 3, "ceo", "root", "result", reply_to=first.id, status="done")
    blocked = put(mail, 4, "ceo", "root", "result", reply_to=first.id, status="blocked")
    assert rework.driven([first, again], latest_results([late])) == set()  # the delivery came after the rework: it was not what was sent back
    assert rework.driven([first, again], latest_results([blocked])) == set()
    assert rework.driven([first, again], {}) == set()


def test_two_agents_that_send_each_other_reworks_end_the_search(tmp_path: Path) -> None:
    mail, rework = build(tmp_path)
    base_a = put(mail, 1, "root", "ceo")
    base_b = put(mail, 2, "root", "ops")
    to_ceo = put(mail, 3, "ops", "ceo", revises=base_a.id)
    to_ops = put(mail, 4, "ceo", "ops", revises=base_b.id)
    assert rework.driven([base_a, to_ceo], {}) == set() and rework.driven([base_b, to_ops], {}) == set()
