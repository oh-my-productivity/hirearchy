"""Contract of ``MailboxWriter``: the mailboxes on disk and the in-memory ones pass the same tests.

The order of the two writes is the contract (ARCHITECTURE.md 10.1, risk 3): budget is derived from ``sent/`` and ``inbox/``, so a
crash between the writes may leave a message charged but undelivered, never delivered but uncharged.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from orgmcp.mail import MailboxWriter
from orgmcp.mail.testing import IMPLEMENTATIONS, MailHarness

from ._support import agents, make, mid, note, where


pytestmark = pytest.mark.xfail(strict=True, reason="red: A-mail")


@pytest.fixture(params=IMPLEMENTATIONS[MailboxWriter], ids=lambda factory: factory.__name__)
def h(request: pytest.FixtureRequest, tmp_path: Path) -> MailHarness:
    made = make(request, tmp_path)
    assert isinstance(made.writer, MailboxWriter)
    agents(made, "ceo", "ceo/eng")
    return made


def test_a_stored_message_is_in_the_sent_box_of_the_sender_and_the_inbox_of_the_recipient(h: MailHarness) -> None:
    msg = note(1)
    h.writer.store(msg)
    assert h.read(where("ceo", "sent", msg.id)) == msg.to_text() and h.read(where("ceo/eng", "inbox", msg.id)) == msg.to_text()
    assert [m.id for m in h.reader.sent("ceo")] == [msg.id] and [m.id for m in h.reader.received("ceo/eng")] == [msg.id]


def test_what_is_stored_reads_back_as_the_same_message(h: MailHarness) -> None:
    msg = note(1, budget=3, trace="t1", wake=False, hops=1)
    h.writer.store(msg)
    [back] = h.reader.messages("ceo/eng", "inbox")
    assert (back.id, back.sender, back.to, back.type, back.body, back.budget, back.trace, back.wake, back.hops) == (
        msg.id, "ceo", "ceo/eng", "task", "do it", 3, "t1", False, 1,
    )


def test_the_sent_copy_is_written_before_the_recipients_copy(h: MailHarness) -> None:
    order: list[str] = []

    def record(path: str) -> bool:
        order.append(path)
        return False  # records the writes, lets them through

    h.fail_writes(record)
    msg = note(1)
    h.writer.store(msg)
    assert order == [where("ceo", "sent", msg.id), where("ceo/eng", "inbox", msg.id)]


def test_a_failing_recipient_write_leaves_the_message_charged_but_undelivered(h: MailHarness) -> None:
    h.fail_writes(lambda path: "/inbox/" in path)
    msg = note(1)
    with pytest.raises(OSError):
        h.writer.store(msg)
    assert h.read(where("ceo", "sent", msg.id)) == msg.to_text()
    assert h.read(where("ceo/eng", "inbox", msg.id)) is None


def test_a_failing_sender_write_stores_nothing(h: MailHarness) -> None:
    h.fail_writes(lambda path: "/sent/" in path)
    msg = note(1)
    with pytest.raises(OSError):
        h.writer.store(msg)
    assert h.read(where("ceo", "sent", msg.id)) is None and h.read(where("ceo/eng", "inbox", msg.id)) is None


def test_the_runtime_has_no_sent_copy(h: MailHarness) -> None:
    msg = note(1, sender="runtime", to="ceo", kind="note")
    h.writer.store(msg)
    assert h.read(where("ceo", "inbox", msg.id)) == msg.to_text()
    assert h.listing("runtime") is None and h.listing("runtime/sent") is None


def test_root_writes_and_reads_the_boxes_of_the_organization_itself(h: MailHarness) -> None:
    out, back = note(1, sender="root", to="ceo"), note(2, sender="ceo", to="root", kind="result")
    h.writer.store(out)
    h.writer.store(back)
    assert h.read(f"sent/{out.id}.md") == out.to_text() and h.read(f"inbox/{back.id}.md") == back.to_text()


def test_the_recipients_box_is_made_when_it_is_not_there(h: MailHarness) -> None:
    msg = note(1, to="ceo/new")
    h.writer.store(msg)
    assert h.read(where("ceo/new", "inbox", msg.id)) == msg.to_text()


def test_the_recipient_address_is_normalized(h: MailHarness) -> None:
    msg = note(1, to=" /ceo/eng/ ")
    h.writer.store(msg)
    assert h.read(where("ceo/eng", "inbox", msg.id)) == msg.to_text()


def test_a_message_to_oneself_is_written_to_both_boxes(h: MailHarness) -> None:
    msg = note(1, sender="ceo", to="ceo", kind="note")
    h.writer.store(msg)
    assert h.read(where("ceo", "sent", msg.id)) == h.read(where("ceo", "inbox", msg.id)) == msg.to_text()


def test_messages_stored_later_sort_after_earlier_ones(h: MailHarness) -> None:
    for n in (3, 1, 2):
        h.writer.store(note(n))
    assert [m.id for m in h.reader.messages("ceo/eng", "inbox")] == [mid(1, "ceo"), mid(2, "ceo"), mid(3, "ceo")]
