"""How long the chain of messages is that a sender is working on (moved from ``Org._next_hops``)."""

from __future__ import annotations

from ..kernel import ROOT, RUNTIME
from ..mail import MailboxReader
from ._protocols import HopCounter


class InflightHopCounter(HopCounter):
    """One more than the longest chain among the messages in the sender's current batch."""

    def __init__(self, mail: MailboxReader) -> None:
        self._mail = mail

    def next_hops(self, actor: str) -> int:
        if actor in (ROOT, RUNTIME):
            return 0
        return max((m.hops for m in self._mail.messages(actor, "inflight")), default=0) + 1
