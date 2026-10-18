"""``StampedEventSwitch``: one look at the stamp per call, one read of ORG.md per change."""

from __future__ import annotations

from orgmcp.settings import EventSwitch, OrgDocumentStore
from orgmcp.settings._stamp import OrgDocumentStamp
from orgmcp.settings._switch import StampedEventSwitch
from orgmcp.settings.tests._red import red


class ScriptedStamp(OrgDocumentStamp):
    def __init__(self) -> None:
        self.value: tuple[int, int] | OSError = (1, 10)
        self.looks = 0

    def stamp(self) -> tuple[int, int]:
        self.looks += 1
        if isinstance(self.value, OSError):
            raise self.value
        return self.value


class CountingDocument(OrgDocumentStore):
    def __init__(self, text: str | Exception) -> None:
        self.text = text
        self.reads = 0

    def exists(self) -> bool:
        return True

    def read_raw(self) -> str:
        self.reads += 1
        if isinstance(self.text, Exception):
            raise self.text
        return self.text

    def write_raw(self, text: str) -> None:
        raise AssertionError("the switch never writes")


def make(text: str | Exception) -> tuple[StampedEventSwitch, ScriptedStamp, CountingDocument]:
    stamp, document = ScriptedStamp(), CountingDocument(text)
    return StampedEventSwitch(stamp, document), stamp, document


def test_it_is_an_event_switch() -> None:
    assert isinstance(make("")[0], EventSwitch)


def test_building_it_looks_at_nothing() -> None:
    _, stamp, document = make("---\nevents: false\n---\n")
    assert (stamp.looks, document.reads) == (0, 0)


@red
def test_the_document_is_read_once_per_stamp() -> None:
    switch, stamp, document = make("---\nevents: false\n---\n")
    assert [switch.enabled() for _ in range(5)] == [False] * 5
    assert (stamp.looks, document.reads) == (5, 1)
    stamp.value = (2, 10)
    document.text = "---\nevents: true\n---\n"
    assert [switch.enabled() for _ in range(3)] == [True] * 3
    assert (stamp.looks, document.reads) == (8, 2)


@red
def test_a_stamp_that_cannot_be_looked_at_means_off_and_the_document_is_not_read() -> None:
    switch, stamp, document = make("---\nevents: true\n---\n")
    stamp.value = FileNotFoundError("ORG.md")
    assert switch.enabled() is False
    stamp.value = PermissionError("ORG.md")
    assert switch.enabled() is False
    assert document.reads == 0


@red
def test_what_was_read_stays_in_force_while_the_stamp_cannot_be_looked_at_and_is_not_forgotten() -> None:
    switch, stamp, document = make("---\nevents: false\n---\n")
    assert switch.enabled() is False
    stamp.value = OSError("gone")
    assert switch.enabled() is False
    stamp.value = (1, 10)  # back with the stamp it had: nothing to read again
    assert switch.enabled() is False
    assert document.reads == 1


@red
def test_a_document_that_cannot_be_read_leaves_events_on_and_is_not_read_again_for_the_same_stamp() -> None:
    switch, stamp, document = make(OSError("unreadable"))
    assert switch.enabled() is True
    assert switch.enabled() is True
    assert document.reads == 1
    stamp.value = (2, 10)
    document.text = "---\nevents: off\n---\n"
    assert switch.enabled() is False


@red
def test_a_document_that_is_not_text_leaves_events_on() -> None:
    switch, _, _ = make(UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalid start byte"))
    assert switch.enabled() is True
