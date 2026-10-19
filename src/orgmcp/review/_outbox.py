"""``DeliveryNoteOutbox``: the notes of a review, delivered (moved from the loop in ``review.review``)."""

from __future__ import annotations

from collections.abc import Sequence

from ..delivery import MessageDelivery
from ._ports import NoteOutbox
from .api import Note


class DeliveryNoteOutbox(NoteOutbox):
    def __init__(self, delivery: MessageDelivery) -> None:
        self._delivery = delivery

    def deliver(self, notes: Sequence[Note]) -> None:
        raise NotImplementedError("red: C-review")
