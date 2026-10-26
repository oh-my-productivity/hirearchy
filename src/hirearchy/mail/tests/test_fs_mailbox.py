"""``FsMailbox`` only: what depends on the file system, the injected parser and the injected atomic writer.

Everything the in-memory mailbox does as well is in the contract suites (``test_contract_*``)."""

from __future__ import annotations

from pathlib import Path

import pytest

from hirearchy.kernel import Message, OrgPaths
from hirearchy.kernel.testing import FailingAtomicWriter, MemoryAtomicWriter
from hirearchy.mail import MailboxReader, MailboxWriter, MailFingerprint, MessageParser
from hirearchy.mail._mailbox import FsMailbox
from hirearchy.mail._parser import CachingMessageParser
from hirearchy.mail._rules import RECEIVED_BOXES
from hirearchy.mail.testing import CountingMessageParser, MovingMessageParser

from ._support import BAD_BUDGET, BAD_YAML, message_text, mid, note, raises_a_parse_error


CEO_INBOX = "ceo/inbox"


def inbox(root: Path, n: int, **kw: object) -> Path:
    path = root / CEO_INBOX / f"{mid(n)}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(message_text(mid(n), to="ceo", **kw), encoding="utf-8")  # type: ignore[arg-type]
    return path


def mailbox(root: Path, parser: CachingMessageParser | None = None, writer: object | None = None) -> FsMailbox:
    return FsMailbox(OrgPaths(root), parser or CountingMessageParser(), writer or MemoryAtomicWriter())  # type: ignore[arg-type]


def test_it_implements_the_three_roles() -> None:
    box = mailbox(Path("/nowhere"))
    assert isinstance(box, MailboxReader) and isinstance(box, MailboxWriter) and isinstance(box, MailFingerprint)


def test_building_one_touches_nothing(tmp_path: Path) -> None:
    mailbox(tmp_path / "absent")
    assert not (tmp_path / "absent").exists()


# ------------------------------------------------------------------------------ the parse cache is what makes a re-read cheap


def test_a_second_listing_parses_no_file(tmp_path: Path) -> None:
    """ARCHITECTURE.md 10.1 risk 1: the count is the guard (a time would flap)."""
    parser = CountingMessageParser()
    box = mailbox(tmp_path, parser)
    for n in range(40):
        inbox(tmp_path, n)
    assert len(box.messages("ceo", "inbox")) == 40 and parser.parses == 40
    for _ in range(3):
        assert len(box.messages("ceo", "inbox")) == 40
    assert parser.parses == 40  # the loads were served by the cache
    assert len(parser.loaded) == 160  # ... but the reader did ask for each file every time


def test_unread_and_received_use_the_same_cache(tmp_path: Path) -> None:
    parser = CountingMessageParser()
    box = mailbox(tmp_path, parser)
    for n in range(5):
        inbox(tmp_path, n)
    box.messages("ceo", "inbox")
    box.unread("ceo")
    box.received("ceo")
    box.find_received("ceo", mid(2))
    assert parser.parses == 5


def test_a_changed_file_is_parsed_again_and_only_that_one(tmp_path: Path) -> None:
    parser = CountingMessageParser()
    box = mailbox(tmp_path, parser)
    paths = [inbox(tmp_path, n) for n in range(40)]
    box.messages("ceo", "inbox")
    paths[0].write_text(paths[0].read_text(encoding="utf-8") + "\nmore", encoding="utf-8")
    box.messages("ceo", "inbox")
    assert parser.parses == 41


def test_every_listing_gives_new_messages(tmp_path: Path) -> None:
    box = mailbox(tmp_path)
    inbox(tmp_path, 1)
    [first] = box.messages("ceo", "inbox")
    first.body = "mutated"
    [second] = box.messages("ceo", "inbox")
    assert second is not first and second.body == "body"


# ------------------------------------------------------------------------------ files that cannot be read


@pytest.mark.parametrize("text", [BAD_YAML, BAD_BUDGET])
def test_listing_a_box_with_a_file_that_does_not_parse_raises(tmp_path: Path, text: str) -> None:
    box = mailbox(tmp_path)
    inbox(tmp_path, 1)
    (tmp_path / CEO_INBOX / f"{mid(2)}.md").write_text(text, encoding="utf-8")
    raises_a_parse_error(lambda: box.messages("ceo", "inbox"))  # the yaml error or the bad number, as they always did


def test_unread_counts_a_file_that_cannot_be_decoded(tmp_path: Path) -> None:
    box = mailbox(tmp_path)
    inbox(tmp_path, 1, wake=False)
    (tmp_path / CEO_INBOX / f"{mid(2)}.md").write_bytes(b"\xff\xfe not utf-8")
    assert box.unread("ceo") == 1


def test_a_file_that_vanishes_between_the_listing_and_the_read_counts_as_mail(tmp_path: Path) -> None:
    """An unreadable file still counts as mail: a run should look at it."""

    class Vanishing(MessageParser):
        def parse(self, path: Path) -> Message:
            raise FileNotFoundError(path)

    inbox(tmp_path, 1)
    assert FsMailbox(OrgPaths(tmp_path), Vanishing(), MemoryAtomicWriter()).unread("ceo") == 1


def test_find_anywhere_says_none_for_a_file_that_cannot_be_decoded(tmp_path: Path) -> None:
    box = mailbox(tmp_path)
    inbox(tmp_path, 1)
    (tmp_path / CEO_INBOX / f"{mid(2)}.md").write_bytes(b"\xff\xfe")
    assert box.find_anywhere("ceo", mid(2)) is None and box.find_anywhere("ceo", mid(1)) is not None


def test_find_anywhere_does_not_follow_a_directory_named_like_a_message(tmp_path: Path) -> None:
    box = mailbox(tmp_path)
    (tmp_path / CEO_INBOX / f"{mid(1)}.md").mkdir(parents=True)
    assert box.find_anywhere("ceo", mid(1)) is None


# ------------------------------------------------------------------------------ the writes go through the injected writer


def test_both_copies_are_written_through_the_atomic_writer_in_order(tmp_path: Path) -> None:
    writer = MemoryAtomicWriter()
    box = mailbox(tmp_path, writer=writer)
    msg = note(1)
    box.store(msg)
    assert list(writer.files) == [tmp_path / "ceo" / "sent" / f"{msg.id}.md", tmp_path / "ceo" / "eng" / "inbox" / f"{msg.id}.md"]
    assert set(writer.files.values()) == {msg.to_text()}


def test_a_failing_writer_fails_the_store_after_the_sender_copy(tmp_path: Path) -> None:
    writer = FailingAtomicWriter(MemoryAtomicWriter(), fails=lambda path: path.parent.name == "inbox")
    box = mailbox(tmp_path, writer=writer)
    msg = note(1)
    with pytest.raises(OSError, match="No space"):
        box.store(msg)
    assert [p.parent.name for p in writer.attempts] == ["sent", "inbox"]


def test_the_runtime_is_charged_nothing(tmp_path: Path) -> None:
    writer = FailingAtomicWriter(MemoryAtomicWriter(), fails=lambda path: path.parent.name == "sent")  # would fail, if it were tried
    box = mailbox(tmp_path, writer=writer)
    box.store(note(1, sender="runtime", to="ceo", kind="note"))
    assert [p.parent.name for p in writer.attempts] == ["inbox"]


# ------------------------------------------------------------------------------ fingerprint: directories only


def test_the_fingerprint_reads_no_file(tmp_path: Path) -> None:
    parser = CountingMessageParser()
    box = mailbox(tmp_path, parser)
    for n in range(10):
        inbox(tmp_path, n)
    assert len(box.fingerprint("ceo")[0]) == 10 and parser.loaded == []


# ------------------------------------------------------------------------------ a message that moves between the listing and the read (F-G0-3)


def at(root: Path, box: str, n: int = 1) -> Path:
    """The file of message ``n`` in a box of ``ceo`` (the directory is made, the file is not)."""
    path = root / "ceo" / box / f"{mid(n)}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def put_in(root: Path, box: str, n: int = 1) -> Path:
    path = at(root, box, n)
    path.write_text(message_text(mid(n), to="ceo"), encoding="utf-8")
    return path


def ids(messages: list[Message]) -> list[str]:
    return [m.id for m in messages]


@pytest.mark.parametrize(
    ("start", "end"),
    [("inflight", "read"), ("inbox", "inflight"), ("inbox", "read"), ("inflight", "inbox")],
    ids=["forward-inflight-to-read", "forward-inbox-to-inflight", "forward-inbox-to-read", "back-inflight-to-inbox"],
)
def test_a_received_message_that_moves_to_another_asked_box_is_read_there_once(tmp_path: Path, start: str, end: str) -> None:
    """The move is injected between the listing and the read (``MovingMessageParser``); the message is returned once, wherever the walk meets it."""
    source = put_in(tmp_path, start)
    parser = MovingMessageParser({source: at(tmp_path, end)})
    box = mailbox(tmp_path, parser)
    assert ids(box.messages("ceo", *RECEIVED_BOXES)) == [mid(1)]
    assert parser.moved == [source]
    assert not source.exists() and box.messages("ceo", *RECEIVED_BOXES)[0].path == at(tmp_path, end)


def test_a_message_that_moves_twice_is_read_at_its_last_place_once(tmp_path: Path) -> None:
    source = put_in(tmp_path, "inbox")
    middle = at(tmp_path, "inflight")
    parser = MovingMessageParser({source: middle, middle: at(tmp_path, "read")})
    assert ids(mailbox(tmp_path, parser).messages("ceo", *RECEIVED_BOXES)) == [mid(1)]
    assert parser.moved == [source, middle]


def test_the_moved_message_keeps_its_place_in_the_order_by_id(tmp_path: Path) -> None:
    put_in(tmp_path, "inbox", 1)
    source = put_in(tmp_path, "inbox", 2)
    put_in(tmp_path, "read", 3)
    parser = MovingMessageParser({source: at(tmp_path, "read", 2)})
    assert ids(mailbox(tmp_path, parser).messages("ceo", *RECEIVED_BOXES)) == [mid(1), mid(2), mid(3)]
    assert parser.moved == [source]


def test_a_message_that_moves_to_a_box_the_call_did_not_ask_for_is_left_out(tmp_path: Path) -> None:
    source = put_in(tmp_path, "inflight")
    parser = MovingMessageParser({source: at(tmp_path, "read")})
    assert mailbox(tmp_path, parser).messages("ceo", "inflight") == []
    assert parser.moved == [source]


def test_a_message_that_is_removed_is_left_out(tmp_path: Path) -> None:
    source = put_in(tmp_path, "inflight")
    other = put_in(tmp_path, "inflight", 2)
    parser = MovingMessageParser({source: tmp_path / "gone.md"})
    assert ids(mailbox(tmp_path, parser).messages("ceo", *RECEIVED_BOXES)) == [mid(2)]
    assert parser.moved == [source] and other.is_file()


def test_a_sent_file_that_is_gone_still_raises(tmp_path: Path) -> None:
    """Guard: the race is the one of a received message that ``inbox`` moves; no writer moves a sent copy."""
    source = put_in(tmp_path, "sent")
    parser = MovingMessageParser({source: tmp_path / "gone.md"})
    with pytest.raises(FileNotFoundError):
        mailbox(tmp_path, parser).messages("ceo", "sent")
    assert parser.moved == [source]


def test_a_received_listing_with_no_move_is_what_it_was(tmp_path: Path) -> None:
    """Guard: no move, today's list."""
    for n, box in enumerate(("read", "inbox", "inflight", "read"), 1):
        put_in(tmp_path, box, n)
    parser = MovingMessageParser({})
    assert ids(mailbox(tmp_path, parser).messages("ceo", *RECEIVED_BOXES)) == [mid(n) for n in (1, 2, 3, 4)]
    assert ids(mailbox(tmp_path, parser).messages("ceo", "read", "inbox")) == [mid(1), mid(2), mid(4)]
    assert parser.moved == []
