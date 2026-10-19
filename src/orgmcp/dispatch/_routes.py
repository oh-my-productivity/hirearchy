"""Who may message whom. Skeleton: RED."""

from __future__ import annotations

from ..mail import MailboxReader
from ._protocols import RoutePolicy


class ParentSiblingRoutePolicy(RoutePolicy):
    """Parent, direct reports, siblings, and whoever sent the message being answered."""

    def __init__(self, mail: MailboxReader) -> None:
        self._mail = mail

    def can_message(self, sender: str, to: str, reply_to: str | None = None) -> bool:
        raise NotImplementedError
