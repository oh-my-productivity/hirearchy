"""``SoleUpstreamTask``: the one task a delegation probably serves (moved from ``Org._upstream``)."""

from __future__ import annotations

from ..kernel import Message
from ..mail import MailboxReader
from ._ports import UpstreamTasks


class SoleUpstreamTask(UpstreamTasks):
    def __init__(self, mail: MailboxReader) -> None:
        self._mail = mail

    def upstream(self, addr: str, delegated: Message) -> tuple[Message, Message | None] | None:
        raise NotImplementedError("red: C-prompts")
