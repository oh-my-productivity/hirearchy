"""``MemoryMailbox`` only: what makes the fake trustworthy beyond the contract suites (it shares the file tree of a ``MemoryAgents``)."""

from __future__ import annotations

from pathlib import Path

import pytest

from orgmcp.agents.testing import MemoryAgents
from orgmcp.mail import BatchStore, MailboxReader, MailboxWriter, MailFingerprint, MessageIndex
from orgmcp.mail.testing import MemoryMailbox

from ._support import message_text, mid, note, raises_a_parse_error


def agent(box: MemoryMailbox, addr: str) -> None:
    box.agents.put(f"{addr}/AGENT.md", "---\nrole: R\n---\nx\n")


def test_it_implements_all_five_ports() -> None:
    box = MemoryMailbox()
    assert all(isinstance(box, port) for port in (MailboxReader, MailboxWriter, BatchStore, MailFingerprint, MessageIndex))


def test_it_lives_in_the_file_tree_of_the_agents_it_is_given() -> None:
    agents = MemoryAgents()
    box = MemoryMailbox(agents)
    agent(box, "ceo")
    msg = note(1, to="ceo")
    box.store(msg)
    assert agents.read(f"ceo/inbox/{msg.id}.md") == msg.to_text() and box.agents is agents


def test_a_file_put_in_the_tree_is_a_message() -> None:
    box = MemoryMailbox()
    agent(box, "ceo")
    box.agents.put(f"ceo/inbox/{mid(1)}.md", message_text(mid(1)))
    [m] = box.messages("ceo", "inbox")
    assert m.id == mid(1) and m.path == box.agents.root / "ceo" / "inbox" / f"{mid(1)}.md"


def test_every_listing_gives_new_messages() -> None:
    box = MemoryMailbox()
    agent(box, "ceo")
    box.agents.put(f"ceo/inbox/{mid(1)}.md", message_text(mid(1)))
    [first] = box.messages("ceo", "inbox")
    first.body = "mutated"
    assert box.messages("ceo", "inbox")[0].body == "body"


def test_a_failing_write_raises_and_writes_nothing() -> None:
    box = MemoryMailbox()
    agent(box, "ceo")
    box.fails = lambda path: path.endswith("/inbox/" + mid(1, "ceo") + ".md")
    with pytest.raises(OSError):
        box.store(note(1, to="ceo", sender="ceo"))
    assert box.agents.read(f"ceo/inbox/{mid(1, 'ceo')}.md") is None


def test_a_file_that_does_not_parse_raises_like_the_files_do() -> None:
    box = MemoryMailbox()
    agent(box, "ceo")
    box.agents.put(f"ceo/inbox/{mid(1)}.md", "---\nfrom: [unclosed\n---\nx\n")
    raises_a_parse_error(lambda: box.messages("ceo", "inbox"))


def test_the_fake_keeps_no_times_every_file_is_as_old_as_the_epoch_plus_one_second() -> None:
    box = MemoryMailbox()
    agent(box, "ceo")
    box.agents.put(f"ceo/inbox/{mid(1)}.md", message_text(mid(1)))
    assert [f.mtime for f in box.scan()] == [1.0]
