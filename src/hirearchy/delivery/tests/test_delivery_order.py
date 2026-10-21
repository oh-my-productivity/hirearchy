"""The order of the two writes, and what a failure between them leaves (ARCHITECTURE.md 10.1, risk 3), over the mailboxes on disk and in memory.

The budget is derived from ``sent/`` and ``inbox/``: a crash between the two writes must never deliver without charging. So the sender's copy is
written first, and what is charged but undelivered is finished by ``BatchStore.recover``."""

from __future__ import annotations

from pathlib import Path

import pytest

from hirearchy.delivery.testing import DeliveryHarness, fs_pipeline, memory_pipeline
from hirearchy.kernel import RUNTIME, Message

from ._support import make, task


@pytest.fixture(params=[fs_pipeline, memory_pipeline], ids=lambda factory: factory.__name__)
def h(request: pytest.FixtureRequest, tmp_path: Path) -> DeliveryHarness:
    made = make(request, tmp_path)
    assert made.mail is not None and made.events is not None and made.tap is not None
    return made


def writes_into(h: DeliveryHarness, box: str) -> None:
    """From now on every write into a ``box`` directory fails like a full disk."""
    assert h.mail is not None
    h.mail.fail_writes(lambda rel: f"/{box}/" in f"/{rel}")


def test_the_sent_copy_is_written_before_the_inbox_copy(h: DeliveryHarness) -> None:
    assert h.mail is not None
    order: list[str] = []

    def spy(rel: str) -> bool:
        order.append(rel.split("/")[-2])
        return False

    h.mail.fail_writes(spy)
    h.delivery.deliver(task("root", "ceo"))
    assert order == ["sent", "inbox"]


def test_the_runtime_writes_only_the_inbox_copy(h: DeliveryHarness) -> None:
    assert h.mail is not None
    order: list[str] = []

    def spy(rel: str) -> bool:
        order.append(rel.split("/")[-2])
        return False

    h.mail.fail_writes(spy)
    h.delivery.deliver(Message(sender=RUNTIME, to="ceo", type="note", body="b"))
    assert order == ["inbox"]


def test_a_failing_inbox_write_leaves_the_sent_copy_and_raises(h: DeliveryHarness) -> None:
    writes_into(h, "inbox")
    msg = task("ceo", "ceo/eng")
    with pytest.raises(OSError):
        h.delivery.deliver(msg)
    assert [m.id for m in h.sent("ceo")] == [msg.id] and h.inbox("ceo/eng") == []


def test_a_failing_inbox_write_emits_nothing_and_notes_no_trace(h: DeliveryHarness) -> None:
    assert h.events is not None and h.tap is not None
    writes_into(h, "inbox")
    with pytest.raises(OSError):
        h.delivery.deliver(task("ceo", "ceo/eng"))
    assert h.events.events == [] and h.tap.notes == []


def test_a_failing_sent_write_delivers_nothing(h: DeliveryHarness) -> None:
    writes_into(h, "sent")
    with pytest.raises(OSError):
        h.delivery.deliver(task("ceo", "ceo/eng"))
    assert h.sent("ceo") == [] and h.inbox("ceo/eng") == []


def test_recover_finishes_a_delivery_that_stopped_between_the_two_writes(h: DeliveryHarness) -> None:
    assert h.mail is not None
    writes_into(h, "inbox")
    msg = task("ceo", "ceo/eng")
    with pytest.raises(OSError):
        h.delivery.deliver(msg)
    h.mail.fail_writes(None)
    assert h.mail.batches.recover() == []  # no interrupted run: only the delivery is finished
    assert [m.to_text() for m in h.inbox("ceo/eng")] == [msg.to_text()]
    assert h.mail.batches.recover() == []  # and once only
    assert len(h.inbox("ceo/eng")) == 1 and len(h.sent("ceo")) == 1


def test_a_delivery_after_the_disk_is_back_is_a_normal_one(h: DeliveryHarness) -> None:
    assert h.mail is not None
    writes_into(h, "inbox")
    with pytest.raises(OSError):
        h.delivery.deliver(task("ceo", "ceo/eng"))
    h.mail.fail_writes(None)
    again = h.delivery.deliver(task("ceo", "ceo/eng"))
    assert again.id in [m.id for m in h.inbox("ceo/eng")]
