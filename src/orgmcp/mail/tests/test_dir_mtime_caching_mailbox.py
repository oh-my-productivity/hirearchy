"""``DirMtimeCachingMailbox``: the dashboard's decorator of the mailbox reader (it replaces ``LenientOrg._box/_trusted/messages/unread/running``).

A box is read again only when its directory changed, or changed so recently when it was read that a second change in the same tick could
have gone unseen (``CACHE_TRUST``: coarse file system timestamps). A file that does not parse is skipped and reported in ``bad``. The
reader contract (``test_contract_mailbox_reader``) holds as well: this file has what is specific to the decorator.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from orgmcp.kernel import Message, OrgPaths
from orgmcp.kernel.testing import FakeClock, MemoryAtomicWriter
from orgmcp.mail import MailboxReader, MessageParser
from orgmcp.mail._caching import CACHE_TRUST, DirectoryProbe, DirMtimeCachingMailbox, FsDirectoryProbe
from orgmcp.mail._mailbox import FsMailbox
from orgmcp.mail.testing import CountingMessageParser

from ._support import BAD_BUDGET, BAD_YAML, message_text, mid


pytestmark = pytest.mark.xfail(strict=True, reason="red: A-mail")

NS = 1_000_000_000


class FakeProbe(DirectoryProbe):
    """The mtime of every directory is whatever the test says; every question is logged."""

    def __init__(self) -> None:
        self.mtimes: dict[tuple[str, str], int] = {}
        self.asked: list[tuple[str, str]] = []

    def mtime(self, addr: str, name: str) -> int:
        self.asked.append((addr, name))
        return self.mtimes.get((addr, name), -1)


class Setup:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.layout = OrgPaths(root)
        self.parser = CountingMessageParser()
        self.clock = FakeClock()
        self.probe = FakeProbe()
        self.inner = FsMailbox(self.layout, self.parser, MemoryAtomicWriter())
        self.box = DirMtimeCachingMailbox(self.inner, self.layout, self.parser, self.probe, self.clock)

    def put(self, n: int, name: str | None = None, text: str | None = None, box: str = "inbox", addr: str = "ceo") -> Path:
        path = self.root / addr / box / (name or f"{mid(n)}.md")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text if text is not None else message_text(mid(n), to=addr), encoding="utf-8")
        return path

    def quiet(self, box: str = "inbox", addr: str = "ceo", seconds: float = 100) -> None:
        """The directory was last changed ``seconds`` before now (by the clock the decorator reads)."""
        self.probe.mtimes[(addr, box)] = int((self.clock.time() - seconds) * NS)

    def changed(self, box: str = "inbox", addr: str = "ceo") -> None:
        """The directory changed just now."""
        self.probe.mtimes[(addr, box)] = int(self.clock.time() * NS)


@pytest.fixture
def s(tmp_path: Path) -> Setup:
    return Setup(tmp_path)


def test_it_is_a_mailbox_reader(s: Setup) -> None:
    assert isinstance(s.box, MailboxReader)


# ------------------------------------------------------------------------------ the cache


def test_a_quiet_box_is_read_once(s: Setup) -> None:
    for n in range(3):
        s.put(n)
    s.quiet()
    first = s.box.messages("ceo", "inbox")
    s.put(9)  # the directory did not change, as far as the probe says
    assert s.box.messages("ceo", "inbox") is first and len(first) == 3 and s.parser.parses == 3


def test_an_unchanged_box_gives_the_very_same_list_so_that_what_is_derived_from_it_stays_valid(s: Setup) -> None:
    s.put(1)
    s.quiet()
    assert s.box.messages("ceo", "inbox") is s.box.messages("ceo", "inbox")
    assert s.box.messages("ceo", "inbox", "read") is s.box.messages("ceo", "inbox", "read")


def test_a_change_of_the_directory_reads_the_box_again(s: Setup) -> None:
    s.put(1)
    s.quiet()
    assert len(s.box.messages("ceo", "inbox")) == 1
    s.put(2)
    s.quiet(seconds=50)  # a new mtime, again quiet for long
    assert [m.id for m in s.box.messages("ceo", "inbox")] == [mid(1), mid(2)]


def test_a_box_changed_a_moment_before_it_was_read_is_read_again_next_time(s: Setup) -> None:
    """Coarse timestamps: a second change within the same tick leaves the mtime as it was."""
    s.put(1)
    s.changed()
    assert len(s.box.messages("ceo", "inbox")) == 1
    s.put(2)  # no change of mtime is visible
    assert len(s.box.messages("ceo", "inbox")) == 2


def test_a_box_quiet_for_just_over_the_window_is_trusted_and_one_quiet_for_just_under_is_not(s: Setup) -> None:
    assert CACHE_TRUST == 2.0
    s.put(1)
    s.quiet(seconds=CACHE_TRUST + 0.5)
    s.box.messages("ceo", "inbox")
    s.put(2)
    assert len(s.box.messages("ceo", "inbox")) == 1  # trusted
    s2 = Setup(s.root / "other")
    s2.put(1)
    s2.quiet(seconds=CACHE_TRUST - 0.5)
    s2.box.messages("ceo", "inbox")
    s2.put(2)
    assert len(s2.box.messages("ceo", "inbox")) == 2  # not trusted


def test_a_file_seen_before_is_the_same_message_when_the_box_is_read_again(s: Setup) -> None:
    """Messages are immutable: a file whose name is known is not parsed again, and its message object is kept."""
    s.put(1)
    s.quiet()
    [first] = s.box.messages("ceo", "inbox")
    s.put(2)
    s.quiet(seconds=50)
    again = s.box.messages("ceo", "inbox")
    assert again[0] is first and s.parser.parses == 2


def test_a_box_that_is_not_there_is_empty_and_forgotten(s: Setup) -> None:
    s.put(1)
    s.quiet()
    assert len(s.box.messages("ceo", "inbox")) == 1
    s.probe.mtimes.pop(("ceo", "inbox"))  # the directory is gone
    assert s.box.messages("ceo", "inbox") == []
    assert s.box.unread("ceo") == 0


def test_the_probe_is_asked_once_per_box_and_call(s: Setup) -> None:
    s.put(1)
    s.quiet()
    s.box.messages("ceo", "inbox", "read")
    assert s.probe.asked == [("ceo", "inbox"), ("ceo", "read")]
    s.probe.asked.clear()
    s.box.unread("ceo")
    s.box.has_inflight("ceo")
    assert s.probe.asked == [("ceo", "inbox"), ("ceo", "inflight")]


def test_received_and_sent_come_from_the_cached_boxes(s: Setup) -> None:
    s.put(1)
    s.put(2, box="read")
    s.put(3, box="sent", addr="ceo")
    for box in ("inbox", "read", "sent", "inflight"):
        s.quiet(box)
    assert [m.id for m in s.box.received("ceo")] == [mid(1), mid(2)] and [m.id for m in s.box.sent("ceo")] == [mid(3)]
    assert s.box.find_received("ceo", mid(2)) is not None and s.box.find_received("ceo", mid(3)) is None


# ------------------------------------------------------------------------------ files that do not parse


@pytest.mark.parametrize("text", [BAD_YAML, BAD_BUDGET])
def test_a_file_that_does_not_parse_is_skipped_and_reported(s: Setup, text: str) -> None:
    s.put(1)
    s.put(2, text=text)
    s.quiet()
    assert [m.id for m in s.box.messages("ceo", "inbox")] == [mid(1)]
    assert list(s.box.bad) == [f"ceo/inbox/{mid(2)}.md"]


def test_the_report_names_the_error_and_its_first_line(s: Setup) -> None:
    s.put(1, text=BAD_BUDGET)
    s.quiet()
    s.box.messages("ceo", "inbox")
    [reason] = s.box.bad.values()
    assert reason == "ValueError: invalid literal for int() with base 10: 'lots'"


def test_a_long_reason_is_cut_to_eighty_characters(s: Setup) -> None:
    class Failing(MessageParser):
        def parse(self, path: Path) -> Message:
            raise ValueError("x" * 200 + "\nsecond line")

    s.put(1)
    s.quiet()
    box = DirMtimeCachingMailbox(s.inner, s.layout, Failing(), s.probe, s.clock)
    box.messages("ceo", "inbox")
    assert list(box.bad.values()) == ["ValueError: " + "x" * 80]


def test_an_error_without_a_message_is_reported_by_its_name(s: Setup) -> None:
    class Failing(MessageParser):
        def parse(self, path: Path) -> Message:
            raise KeyError

    s.put(1)
    s.quiet()
    box = DirMtimeCachingMailbox(s.inner, s.layout, Failing(), s.probe, s.clock)
    box.messages("ceo", "inbox")
    assert list(box.bad.values()) == ["KeyError"]


def test_a_file_that_is_fixed_is_no_longer_reported(s: Setup) -> None:
    path = s.put(1, text=BAD_YAML)
    s.quiet()
    s.box.messages("ceo", "inbox")
    assert s.box.bad
    path.write_text(message_text(mid(1), to="ceo"), encoding="utf-8")
    s.quiet(seconds=50)
    assert [m.id for m in s.box.messages("ceo", "inbox")] == [mid(1)] and s.box.bad == {}


def test_the_report_goes_with_the_box_when_it_disappears(s: Setup) -> None:
    s.put(1, text=BAD_YAML)
    s.quiet()
    s.box.messages("ceo", "inbox")
    s.probe.mtimes.pop(("ceo", "inbox"))
    s.box.messages("ceo", "inbox")
    assert s.box.bad == {}


def test_a_file_that_moves_away_between_the_listing_and_the_read_is_neither_listed_nor_reported(s: Setup) -> None:
    class Moved(MessageParser):
        def parse(self, path: Path) -> Message:
            raise FileNotFoundError(path)

    s.put(1)
    s.quiet()
    box = DirMtimeCachingMailbox(s.inner, s.layout, Moved(), s.probe, s.clock)
    assert box.messages("ceo", "inbox") == [] and box.bad == {}


def test_the_reports_of_all_boxes_are_together(s: Setup) -> None:
    s.put(1, text=BAD_YAML)
    s.put(2, text=BAD_YAML, box="read")
    s.quiet("inbox")
    s.quiet("read")
    s.box.messages("ceo", "inbox", "read")
    assert sorted(s.box.bad) == [f"ceo/inbox/{mid(1)}.md", f"ceo/read/{mid(2)}.md"]


def test_a_file_outside_the_organization_is_reported_by_its_whole_path(s: Setup, tmp_path: Path) -> None:
    class Elsewhere(OrgPaths):
        def rel(self, path: Path) -> str:
            raise ValueError("not below the root")

    s.put(1, text=BAD_YAML)
    s.quiet()
    box = DirMtimeCachingMailbox(s.inner, Elsewhere(s.root), s.parser, s.probe, s.clock)
    box.messages("ceo", "inbox")
    assert list(box.bad) == [str(s.root / "ceo" / "inbox" / f"{mid(1)}.md")]


# ------------------------------------------------------------------------------ unread and has_inflight


def test_an_unreadable_file_is_mail_and_a_held_message_is_not(s: Setup) -> None:
    s.put(1)
    s.put(2, text=message_text(mid(2), to="ceo", wake=False))
    s.put(3, text=BAD_YAML)
    s.quiet()
    assert s.box.unread("ceo") == 2


def test_unread_is_counted_from_the_cached_box(s: Setup) -> None:
    for n in range(3):
        s.put(n)
    s.quiet()
    assert s.box.unread("ceo") == 3
    s.put(9)
    assert s.box.unread("ceo") == 3 and s.parser.parses == 3


def test_a_batch_that_does_not_parse_is_still_a_batch(s: Setup) -> None:
    s.put(1, box="inflight", text=BAD_YAML)
    s.quiet("inflight")
    assert s.box.has_inflight("ceo") is True and s.box.messages("ceo", "inflight") == []


def test_no_batch_when_the_box_is_not_there(s: Setup) -> None:
    assert s.box.has_inflight("ceo") is False


# ------------------------------------------------------------------------------ the rest is the inner reader's


def test_find_anywhere_is_the_inner_readers(s: Setup) -> None:
    s.put(1)
    found = s.box.find_anywhere("ceo", mid(1))
    assert found is not None and found.id == mid(1)
    assert s.box.find_anywhere("ceo", "absent") is None


# ------------------------------------------------------------------------------ the probe on the real file system


def test_the_probe_reports_the_mtime_of_a_directory_and_minus_one_for_a_missing_one(tmp_path: Path) -> None:
    probe = FsDirectoryProbe(OrgPaths(tmp_path))
    (tmp_path / "ceo" / "inbox").mkdir(parents=True)
    os.utime(tmp_path / "ceo" / "inbox", ns=(5 * NS, 7 * NS))
    os.utime(tmp_path / "ceo", ns=(5 * NS, 9 * NS))
    assert probe.mtime("ceo", "inbox") == 7 * NS and probe.mtime("ceo", "") == 9 * NS
    assert probe.mtime("ceo", "read") == -1 and probe.mtime("nobody", "") == -1


def test_the_probe_of_root_is_the_organization_directory(tmp_path: Path) -> None:
    os.utime(tmp_path, ns=(1 * NS, 3 * NS))
    assert FsDirectoryProbe(OrgPaths(tmp_path)).mtime("root", "") == 3 * NS
