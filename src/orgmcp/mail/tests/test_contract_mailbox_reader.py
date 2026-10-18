"""Contract of ``MailboxReader``: the mailboxes on disk, the in-memory ones and the dashboard's caching decorator pass the same tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from orgmcp.mail import MailboxReader
from orgmcp.mail.testing import IMPLEMENTATIONS, MailHarness

from ._support import BAD_BUDGET, BAD_YAML, agents, make, mid, put, where


@pytest.fixture(params=IMPLEMENTATIONS[MailboxReader], ids=lambda factory: factory.__name__)
def h(request: pytest.FixtureRequest, tmp_path: Path) -> MailHarness:
    made = make(request, tmp_path)
    assert isinstance(made.reader, MailboxReader)
    agents(made, "ceo", "ceo/eng")
    return made


# ------------------------------------------------------------------------------ messages


def test_messages_are_sorted_by_id_across_the_boxes(h: MailHarness) -> None:
    put(h, "ceo", "read", 3)
    put(h, "ceo", "inbox", 1)
    put(h, "ceo", "inflight", 2)
    assert [m.id for m in h.reader.messages("ceo", "inbox", "inflight", "read")] == [mid(1), mid(2), mid(3)]
    assert [m.id for m in h.reader.messages("ceo", "read", "inbox", "inflight")] == [mid(1), mid(2), mid(3)]


def test_only_the_boxes_asked_for_are_read(h: MailHarness) -> None:
    put(h, "ceo", "inbox", 1)
    put(h, "ceo", "sent", 2, sender="ceo", to="root")
    assert [m.id for m in h.reader.messages("ceo", "inbox")] == [mid(1)]
    assert h.reader.messages("ceo") == []


def test_a_box_that_is_not_there_is_empty(h: MailHarness) -> None:
    assert h.reader.messages("ceo", "inbox", "inflight", "read", "sent") == []
    assert h.reader.messages("nobody", "inbox") == []


def test_files_that_are_not_messages_are_ignored(h: MailHarness) -> None:
    put(h, "ceo", "inbox", 1)
    h.put("ceo/inbox/notes.txt", "not a message")
    h.put("ceo/inbox/.tmp-1234-x.md", "---\nfrom: root\n---\nhalf written")
    assert [m.id for m in h.reader.messages("ceo", "inbox")] == [mid(1)]


def test_the_boxes_of_root_are_in_the_organization_itself(h: MailHarness) -> None:
    put(h, "root", "inbox", 1, sender="ceo")
    put(h, "root", "sent", 2, sender="root", to="ceo")
    assert [m.id for m in h.reader.messages("root", "inbox")] == [mid(1, "ceo")]
    assert [m.id for m in h.reader.sent("root")] == [mid(2)]
    assert h.reader.unread("root") == 1


@pytest.mark.parametrize("spelling", ["ceo", " ceo ", "/ceo/", "ceo\n"])
def test_an_address_is_normalized(h: MailHarness, spelling: str) -> None:
    put(h, "ceo", "inbox", 1)
    assert [m.id for m in h.reader.messages(spelling, "inbox")] == [mid(1)]


def test_a_message_knows_its_file_and_takes_its_id_from_the_front_matter(h: MailHarness) -> None:
    put(h, "ceo", "inbox", 1)
    [m] = h.reader.messages("ceo", "inbox")
    assert m.path == h.path_of(where("ceo", "inbox", mid(1))) and m.sender == "root" and m.to == "ceo" and m.type == "task"


def test_the_id_of_a_message_without_one_is_its_file_name(h: MailHarness) -> None:
    h.put(f"ceo/inbox/{mid(5)}.md", "---\nfrom: root\nto: ceo\ntype: note\n---\nhi\n")
    assert [m.id for m in h.reader.messages("ceo", "inbox")] == [mid(5)]


def test_every_field_of_the_message_is_read(h: MailHarness) -> None:
    put(h, "ceo", "inbox", 1, reply_to="x", status="done", budget=4, hops=2, wake=False, revises="r", supersedes="s", service="svc",
        contract=3, playbook=0, feedback="accept", trace="t1", kind="result")
    [m] = h.reader.messages("ceo", "inbox")
    assert (m.reply_to, m.status, m.budget, m.hops, m.wake, m.revises, m.supersedes, m.service, m.contract, m.playbook, m.feedback, m.trace) == (
        "x", "done", 4, 2, False, "r", "s", "svc", 3, 0, "accept", "t1",
    )


# ------------------------------------------------------------------------------ received, sent, find_received


def test_received_is_inbox_inflight_and_read_and_sent_is_sent(h: MailHarness) -> None:
    put(h, "ceo", "inbox", 1)
    put(h, "ceo", "inflight", 2)
    put(h, "ceo", "read", 3)
    put(h, "ceo", "sent", 4, sender="ceo", to="eng")
    assert [m.id for m in h.reader.received("ceo")] == [mid(1), mid(2), mid(3)]
    assert [m.id for m in h.reader.sent("ceo")] == [mid(4, "ceo")]


def test_find_received_looks_in_the_three_received_boxes_only(h: MailHarness) -> None:
    for n, box in enumerate(("inbox", "inflight", "read"), 1):
        put(h, "ceo", box, n)
    put(h, "ceo", "sent", 4, sender="ceo", to="eng")
    assert [getattr(h.reader.find_received("ceo", mid(n)), "id", None) for n in (1, 2, 3)] == [mid(1), mid(2), mid(3)]
    assert h.reader.find_received("ceo", mid(4, "ceo")) is None
    assert h.reader.find_received("ceo", "missing") is None


# ------------------------------------------------------------------------------ find_anywhere


@pytest.mark.parametrize("box", ["inbox", "inflight", "read", "sent"])
def test_find_anywhere_looks_in_all_four_boxes_by_file_name(h: MailHarness, box: str) -> None:
    put(h, "ceo", box, 1, sender="ceo", to="eng", trace="t9")
    found = h.reader.find_anywhere("ceo", mid(1, "ceo"))
    assert found is not None and found.id == mid(1, "ceo") and found.trace == "t9"


def test_find_anywhere_is_per_agent(h: MailHarness) -> None:
    put(h, "ceo", "inbox", 1)
    assert h.reader.find_anywhere("ceo/eng", mid(1)) is None


def test_find_anywhere_finds_nothing_that_is_not_there(h: MailHarness) -> None:
    assert h.reader.find_anywhere("ceo", mid(1)) is None
    assert h.reader.find_anywhere("nobody", mid(1)) is None


@pytest.mark.parametrize("msg_id", ["", "../ceo/AGENT", "a/b", "a b", "x\n", "*", "..\\x"])
def test_find_anywhere_refuses_an_id_that_is_not_a_plain_file_name(h: MailHarness, msg_id: str) -> None:
    put(h, "ceo", "inbox", 1)
    h.put("ceo/AGENT.md.md", "---\nfrom: root\nto: ceo\ntype: note\n---\nx\n")
    assert h.reader.find_anywhere("ceo", msg_id) is None


def test_find_anywhere_gives_none_for_a_file_that_does_not_parse(h: MailHarness) -> None:
    h.put(f"ceo/inbox/{mid(1)}.md", BAD_YAML)
    h.put(f"ceo/inbox/{mid(2)}.md", BAD_BUDGET)
    assert h.reader.find_anywhere("ceo", mid(1)) is None and h.reader.find_anywhere("ceo", mid(2)) is None


# ------------------------------------------------------------------------------ unread


def test_unread_counts_the_waking_messages_of_the_inbox_only(h: MailHarness) -> None:
    put(h, "ceo", "inbox", 1)
    put(h, "ceo", "inbox", 2)
    put(h, "ceo", "inflight", 3)
    put(h, "ceo", "read", 4)
    put(h, "ceo", "sent", 5, sender="ceo", to="eng")
    assert h.reader.unread("ceo") == 2


def test_a_held_message_does_not_count(h: MailHarness) -> None:
    put(h, "ceo", "inbox", 1, wake=False)
    put(h, "ceo", "inbox", 2, wake=False, kind="note")
    assert h.reader.unread("ceo") == 0
    put(h, "ceo", "inbox", 3)
    assert h.reader.unread("ceo") == 1


def test_an_unreadable_file_counts_as_mail(h: MailHarness) -> None:
    h.put(f"ceo/inbox/{mid(1)}.md", BAD_YAML)
    h.put(f"ceo/inbox/{mid(2)}.md", BAD_BUDGET)
    put(h, "ceo", "inbox", 3, wake=False)
    assert h.reader.unread("ceo") == 2


def test_unread_of_an_agent_without_an_inbox_is_zero(h: MailHarness) -> None:
    assert h.reader.unread("ceo") == 0 and h.reader.unread("nobody") == 0


def test_hidden_files_and_other_files_are_not_mail(h: MailHarness) -> None:
    h.put("ceo/inbox/.tmp-1-x.md", "---\nfrom: root\n---\nx")
    h.put("ceo/inbox/readme.txt", "x")
    assert h.reader.unread("ceo") == 0


# ------------------------------------------------------------------------------ has_inflight


def test_a_batch_in_flight_is_a_run_going(h: MailHarness) -> None:
    assert h.reader.has_inflight("ceo") is False
    put(h, "ceo", "inflight", 1)
    assert h.reader.has_inflight("ceo") is True


def test_other_boxes_and_hidden_files_are_no_batch(h: MailHarness) -> None:
    put(h, "ceo", "inbox", 1)
    put(h, "ceo", "read", 2)
    h.put("ceo/inflight/.tmp-1-x.md", "x")
    assert h.reader.has_inflight("ceo") is False and h.reader.has_inflight("nobody") is False


def test_an_unreadable_file_in_flight_is_still_a_batch(h: MailHarness) -> None:
    h.put(f"ceo/inflight/{mid(1)}.md", BAD_YAML)
    assert h.reader.has_inflight("ceo") is True
