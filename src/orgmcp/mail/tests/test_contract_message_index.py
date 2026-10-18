"""Contract of ``MessageIndex``: the mailboxes on disk and the in-memory ones list the same files with the same findings."""

from __future__ import annotations

from pathlib import Path

import pytest

from orgmcp.mail import MessageIndex
from orgmcp.mail.testing import IMPLEMENTATIONS, MailHarness

from ._support import agents, make, message_text, mid, put, still_red, where




@pytest.fixture(params=still_red(IMPLEMENTATIONS[MessageIndex]), ids=lambda factory: factory.__name__)
def h(request: pytest.FixtureRequest, tmp_path: Path) -> MailHarness:
    made = make(request, tmp_path)
    assert isinstance(made.index, MessageIndex)
    agents(made, "ceo", "ceo/eng")
    return made


def found(h: MailHarness) -> list[tuple[str, str, str]]:
    return [(f.owner, f.box, f.id) for f in h.index.scan()]


def test_an_organization_without_mail_has_no_files(h: MailHarness) -> None:
    assert h.index.scan() == []


def test_every_file_of_root_and_the_agents_is_listed_in_owner_then_box_then_name_order(h: MailHarness) -> None:
    put(h, "ceo/eng", "inbox", 4, to="ceo/eng")
    put(h, "ceo", "sent", 3, sender="ceo", to="root")
    put(h, "ceo", "inbox", 2)
    put(h, "ceo", "inbox", 1)
    put(h, "root", "inbox", 5, sender="ceo")
    put(h, "root", "read", 6, sender="ceo")
    assert found(h) == [
        ("root", "inbox", mid(5, "ceo")),
        ("root", "read", mid(6, "ceo")),
        ("ceo", "inbox", mid(1)),
        ("ceo", "inbox", mid(2)),
        ("ceo", "sent", mid(3, "ceo")),
        ("ceo/eng", "inbox", mid(4)),
    ]


def test_the_boxes_are_taken_in_the_order_of_the_protocol(h: MailHarness) -> None:
    for n, box in enumerate(("sent", "read", "inflight", "inbox"), 1):
        put(h, "ceo", box, n, sender="ceo" if box == "sent" else "root")
    assert [box for _, box, _ in found(h)] == ["inbox", "inflight", "read", "sent"]


def test_a_file_carries_its_path_front_matter_and_time(h: MailHarness) -> None:
    put(h, "ceo", "inbox", 1, title="Hello", budget=2)
    [f] = h.index.scan()
    assert f.path == h.path_of(where("ceo", "inbox", mid(1))) and f.error is None and f.mtime > 0
    assert f.meta is not None and f.meta["title"] == "Hello" and f.meta["budget"] == 2 and f.meta["from"] == "root"


def test_the_id_is_the_one_in_the_front_matter_else_the_file_name(h: MailHarness) -> None:
    h.put(f"ceo/inbox/{mid(1)}.md", message_text("an-explicit-id"))
    h.put(f"ceo/inbox/{mid(2)}.md", "---\nfrom: root\nto: ceo\ntype: note\n---\nno id\n")
    assert [f.id for f in h.index.scan()] == ["an-explicit-id", mid(2)]


def test_hidden_files_and_other_files_are_not_listed(h: MailHarness) -> None:
    put(h, "ceo", "inbox", 1)
    h.put("ceo/inbox/.tmp-1-x.md", "x")
    h.put("ceo/inbox/notes.txt", "x")
    assert found(h) == [("ceo", "inbox", mid(1))]


def test_directories_that_are_no_agents_are_not_scanned(h: MailHarness) -> None:
    h.put(f"ghost/inbox/{mid(1)}.md", message_text(mid(1), to="ghost"))
    h.put(f".retired/ceo-1/inbox/{mid(2)}.md", message_text(mid(2)))
    assert h.index.scan() == []


@pytest.mark.parametrize(
    ("text", "error"),
    [
        ("just text, no front matter\n", "no frontmatter"),
        ("---\n---\nbody\n", "no frontmatter"),
        ("---\nfrom: root\nto: ceo\n---\nno type\n", "frontmatter lacks from/to/type"),
        ("---\nfrom: root\ntype: note\n---\nno recipient\n", "frontmatter lacks from/to/type"),
        ("---\nto: ceo\ntype: note\n---\nno sender\n", "frontmatter lacks from/to/type"),
        ("---\nfrom: root\nto: ceo\ntype: task\nbudget: lots\n---\nx\n", "budget is not a number: 'lots'"),
        ("---\nfrom: root\nto: ceo\ntype: task\nbudget: [1]\n---\nx\n", "budget is not a number: [1]"),
        ("---\nfrom: [unclosed\nto: ceo\n---\nx\n", "frontmatter does not parse (ParserError)"),
    ],
)
def test_a_file_that_cannot_be_used_is_listed_with_the_reason(h: MailHarness, text: str, error: str) -> None:
    h.put(f"ceo/inbox/{mid(1)}.md", text)
    [f] = h.index.scan()
    assert f.error == error and f.id == mid(1)


def test_a_file_with_a_bad_budget_still_has_its_front_matter(h: MailHarness) -> None:
    h.put(f"ceo/inbox/{mid(1)}.md", "---\nfrom: root\nto: ceo\ntype: task\nbudget: lots\n---\nx\n")
    [f] = h.index.scan()
    assert f.meta == {"from": "root", "to": "ceo", "type": "task", "budget": "lots"}


def test_a_file_that_does_not_parse_has_no_front_matter(h: MailHarness) -> None:
    h.put(f"ceo/inbox/{mid(1)}.md", "---\nfrom: [unclosed\n---\nx\n")
    [f] = h.index.scan()
    assert f.meta is None


def test_a_zero_or_missing_budget_is_fine(h: MailHarness) -> None:
    put(h, "ceo", "inbox", 1, budget=0)
    put(h, "ceo", "inbox", 2)
    assert [f.error for f in h.index.scan()] == [None, None]


def test_a_changed_file_is_read_again(h: MailHarness) -> None:
    put(h, "ceo", "inbox", 1)
    assert [f.error for f in h.index.scan()] == [None]
    h.put(f"ceo/inbox/{mid(1)}.md", "no front matter any more, and a different size\n")
    assert [f.error for f in h.index.scan()] == ["no frontmatter"]
