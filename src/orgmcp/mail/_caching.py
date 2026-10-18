"""The dashboard's decorator of the mailbox reader (skeleton: red step of A-mail)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ..kernel import Clock, Message, OrgLayout
from .api import MailboxReader, MessageParser



CACHE_TRUST = 2.0  # a directory modified less than this many seconds before it was listed is listed again next time


@runtime_checkable
class DirectoryProbe(Protocol):
    def mtime(self, addr: str, name: str) -> int:
        """``mtime_ns`` of ``<addr>/<name>`` (the agent's directory itself for ``name`` ``""``); -1 when it is not there."""
        ...


class FsDirectoryProbe(DirectoryProbe):
    def __init__(self, layout: OrgLayout) -> None:
        raise NotImplementedError

    def mtime(self, addr: str, name: str) -> int:
        raise NotImplementedError


class DirMtimeCachingMailbox(MailboxReader):
    def __init__(self, inner: MailboxReader, layout: OrgLayout, parser: MessageParser, probe: DirectoryProbe, clock: Clock) -> None:
        raise NotImplementedError

    @property
    def bad(self) -> dict[str, str]:
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
