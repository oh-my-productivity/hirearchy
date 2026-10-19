"""Who may message whom (moved from ``Org.can_message``)."""

from __future__ import annotations

from ..kernel import ROOT, RUNTIME, parent
from ..mail import MailboxReader
from ._protocols import RoutePolicy


class ParentSiblingRoutePolicy(RoutePolicy):
    """Parent, direct reports, siblings, and whoever sent the message being answered."""

    def __init__(self, mail: MailboxReader) -> None:
        self._mail = mail

    def can_message(self, sender: str, to: str, reply_to: str | None = None) -> bool:
        if sender in (ROOT, RUNTIME):
            return True  # the human and the runtime may address anyone
        if to == sender:
            return False
        if to == parent(sender) or parent(to) == sender or parent(to) == parent(sender):
            return True
        if reply_to:  # anyone may answer a message they received
            original = self._mail.find_received(sender, reply_to)
            return original is not None and original.sender == to
        return False
