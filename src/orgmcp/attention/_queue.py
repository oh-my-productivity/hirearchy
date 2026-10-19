"""``InboxHumanQueue``: the unread messages of root that wait for a decision (moved from ``progress._human_items`` and ``_needs_human``)."""

from __future__ import annotations

from ..mail import MailboxReader
from .api import HumanQueue


class InboxHumanQueue(HumanQueue):
    def __init__(self, mail: MailboxReader) -> None:
        self._mail = mail

    def items(self) -> list[tuple[str, str]]:
        raise NotImplementedError("red: C-attention")

    def lines(self) -> list[str]:
        raise NotImplementedError("red: C-attention")
