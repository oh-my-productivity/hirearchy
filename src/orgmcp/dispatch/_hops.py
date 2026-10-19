"""How long the chain of messages is that a sender is working on. Skeleton: RED."""

from __future__ import annotations

from ..mail import MailboxReader
from ._protocols import HopCounter


class InflightHopCounter(HopCounter):
    """One more than the longest chain among the messages in the sender's current batch."""

    def __init__(self, mail: MailboxReader) -> None:
        self._mail = mail

    def next_hops(self, actor: str) -> int:
        raise NotImplementedError
