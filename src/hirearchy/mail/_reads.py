"""The reads of a mailbox that follow from listing it: every implementation of ``MailboxReader`` derives them the same way."""

from __future__ import annotations

from ..kernel import Message
from .api import MailboxReader
from ._rules import RECEIVED_BOXES


class DerivedMailboxReads(MailboxReader):
    """``received``, ``sent`` and ``find_received`` in terms of ``messages``; the rest is for the implementation."""

    def received(self, addr: str) -> list[Message]:
        return self.messages(addr, *RECEIVED_BOXES)

    def sent(self, addr: str) -> list[Message]:
        return self.messages(addr, "sent")

    def find_received(self, addr: str, msg_id: str) -> Message | None:
        return next((m for m in self.received(addr) if m.id == msg_id), None)
