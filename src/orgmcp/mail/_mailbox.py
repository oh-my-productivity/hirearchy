"""The mailboxes on disk (skeleton: red step of A-mail)."""

from __future__ import annotations

from ..kernel import AtomicWriter, Message, OrgLayout
from .api import MailboxReader, MailboxWriter, MailFingerprint, MessageParser


class FsMailbox(MailboxReader, MailboxWriter, MailFingerprint):
    def __init__(self, layout: OrgLayout, parser: MessageParser, writer: AtomicWriter) -> None:
        raise NotImplementedError

    def messages(self, addr: str, *boxes: str) -> list[Message]:
        raise NotImplementedError

    def received(self, addr: str) -> list[Message]:
        raise NotImplementedError

    def sent(self, addr: str) -> list[Message]:
        raise NotImplementedError

    def find_received(self, addr: str, msg_id: str) -> Message | None:
        raise NotImplementedError

    def find_anywhere(self, addr: str, msg_id: str) -> Message | None:
        raise NotImplementedError

    def unread(self, addr: str) -> int:
        raise NotImplementedError

    def has_inflight(self, addr: str) -> bool:
        raise NotImplementedError

    def store(self, msg: Message) -> None:
        raise NotImplementedError

    def fingerprint(self, addr: str) -> tuple[frozenset[str], frozenset[str]]:
        raise NotImplementedError
