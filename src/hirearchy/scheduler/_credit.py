"""Giving a run back: the steps that the credit of a throttled run and the credit of an effort-stopped run share."""

from __future__ import annotations

from ..delivery import MessageDelivery
from ..kernel import Message, credited_stems
from ..mail import MailboxReader
from ..runs import RunLogReader
from ._run import RunRecord

STAMP = 21  # characters of a log stem or a message id that are its time


def return_run(run: RunRecord, logs: RunLogReader, mail: MailboxReader, delivery: MessageDelivery, note: Message) -> str:
    """Deliver ``note`` (the credit of ``run``) unless the run sent something (it had an effect): ``"free"``, ``"counted"`` (the run before it was
    credited too) or ``""`` (no credit exists). Every fallible read comes first and the delivery is the last fallible step; errors propagate."""
    stem = run.log.stem
    if any(message.id[:STAMP] >= stem[:STAMP] for message in mail.sent(run.addr)):  # the run sent something: it had an effect
        return ""
    stems = [file.stem for file in logs.files(run.addr)]
    before = stems[stems.index(stem) - 1] if stem in stems and stems.index(stem) > 0 else None
    kind = "counted" if before is not None and before in credited_stems(mail.received(run.addr)) else "free"
    delivery.deliver(note)
    return kind
