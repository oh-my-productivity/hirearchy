"""``IndexedMessageHistory``: the messages of the organization, one record per id, from the front matter the index read."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from orgmcp.kernel import Message
from orgmcp.mail.testing import MailHarness, fs_mailbox, memory_mailbox
from orgmcp.observability._history import IndexedMessageHistory
from orgmcp.observability._ports import MessageHistory

from ._support import implementations


EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)
ID1 = "20261018T100000000001-root-0001"
ID2 = "20261018T100005000001-ceo-0002"


@pytest.fixture(params=implementations([fs_mailbox, memory_mailbox]))
def mail(request: pytest.FixtureRequest, tmp_path: Path) -> MailHarness:
    made: MailHarness = request.param(tmp_path)
    made.agent("ceo")
    made.agent("ceo/eng")
    return made


def history(mail: MailHarness) -> MessageHistory:
    made = IndexedMessageHistory(mail.index)
    assert isinstance(made, MessageHistory)
    return made


def put(mail: MailHarness, where: str, **fields: object) -> Message:
    msg = Message(**{"sender": "root", "to": "ceo", "type": "task", "body": "b", "id": ID1, "created": "2026-10-18T10:00:00+00:00", **fields})  # type: ignore[arg-type]
    mail.put(f"{where}/{msg.id}.md", msg.to_text())
    return msg


def test_a_message_is_one_record_with_every_box_that_holds_a_copy(mail: MailHarness) -> None:
    put(mail, "sent", title="Ship", budget=6)
    put(mail, "ceo/read", title="Ship", budget=6)
    (m,) = history(mail).messages().values()
    assert (m.id, m.sender, m.to, m.type, m.title, m.budget, m.wake, m.status) == (ID1, "root", "ceo", "task", "Ship", 6, True, None)
    assert sorted(m.boxes) == [("ceo", "read"), ("root", "sent")]
    assert m.t == datetime(2026, 10, 18, 10, 0, 0, 1, tzinfo=timezone.utc)  # the time of the id, to the microsecond


def test_optional_fields_are_none_when_absent_and_read_when_there(mail: MailHarness) -> None:
    put(mail, "ceo/inbox", reply_to="R", revises="V", service="memo", feedback="accept", trace="T", wake=False, status="done", id=ID2, sender="ceo", to="root")
    put(mail, "ceo/inbox", id="20261018T100009000001-root-0003")
    by_id = history(mail).messages()
    full, bare = by_id[ID2], by_id["20261018T100009000001-root-0003"]
    assert (full.reply_to, full.revises, full.service, full.feedback, full.trace, full.wake, full.status) == ("R", "V", "memo", "accept", "T", False, "done")
    assert (bare.reply_to, bare.revises, bare.service, bare.feedback, bare.trace, bare.wake, bare.title) == (None, None, None, None, None, True, "")


def test_the_trace_of_a_later_copy_is_taken_when_the_first_has_none(mail: MailHarness) -> None:
    put(mail, "sent")
    put(mail, "ceo/inbox", trace="T")
    (m,) = history(mail).messages().values()
    assert m.trace == "T" and len(m.boxes) == 2


def test_the_time_is_the_id_else_created_else_the_epoch(mail: MailHarness) -> None:
    put(mail, "ceo/inbox", id="noid-1", created="2026-10-18T11:30:00+00:00")
    put(mail, "ceo/inbox", id="noid-2", created="garbage")
    by_id = history(mail).messages()
    assert by_id["noid-1"].t == datetime(2026, 10, 18, 11, 30, tzinfo=timezone.utc) and by_id["noid-2"].t == EPOCH


def test_files_that_do_not_parse_are_left_out(mail: MailHarness) -> None:
    put(mail, "ceo/inbox")
    mail.put(f"ceo/inbox/{ID2}.md", "no front matter at all")
    mail.put(f"ceo/inbox/{ID2[:-1]}9.md", "---\nfrom: root\n---\nlacks to and type\n")
    assert list(history(mail).messages()) == [ID1]


def test_an_empty_organization_has_no_messages(mail: MailHarness) -> None:
    assert history(mail).messages() == {}


def test_each_call_is_a_new_dictionary(mail: MailHarness) -> None:
    put(mail, "ceo/inbox")
    first = history(mail).messages()
    first.clear()
    assert len(history(mail).messages()) == 1

