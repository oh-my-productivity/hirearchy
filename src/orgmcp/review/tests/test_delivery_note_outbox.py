"""``DeliveryNoteOutbox``: the notes of a review, written to their recipients."""

from __future__ import annotations

from pathlib import Path

from orgmcp.delivery.testing import DeliveryHarness, RecordingDelivery, recording_delivery
from orgmcp.review import Note
from orgmcp.review._outbox import DeliveryNoteOutbox
from orgmcp.review._ports import NoteOutbox


def made(tmp_path: Path) -> tuple[NoteOutbox, RecordingDelivery]:
    harness: DeliveryHarness = recording_delivery(tmp_path)
    assert isinstance(harness.delivery, RecordingDelivery)
    outbox = DeliveryNoteOutbox(harness.delivery)
    assert isinstance(outbox, NoteOutbox)
    return outbox, harness.delivery


def test_each_note_is_a_runtime_note_that_wakes_its_recipient(tmp_path: Path) -> None:
    outbox, delivery = made(tmp_path)
    outbox.deliver([Note("ceo", "t1", "b1"), Note("root", "t2", "b2")])
    assert [(m.sender, m.to, m.type, m.title, m.body, m.wake) for m in delivery.messages] == [
        ("runtime", "ceo", "note", "t1", "b1", True),
        ("runtime", "root", "note", "t2", "b2", True),
    ]


def test_no_notes_deliver_nothing(tmp_path: Path) -> None:
    outbox, delivery = made(tmp_path)
    outbox.deliver([])
    assert delivery.messages == []
