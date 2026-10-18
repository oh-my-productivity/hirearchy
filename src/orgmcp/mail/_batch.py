"""The batch of a run between the boxes (skeleton: red step of A-mail)."""

from __future__ import annotations

from ..agents import AgentDirectory
from ..kernel import AtomicWriter, Message, OrgLayout
from .api import BatchStore, MailboxReader, MessageParser


class FsBatchStore(BatchStore):
    def __init__(
        self, layout: OrgLayout, agents: AgentDirectory, reader: MailboxReader, parser: MessageParser, writer: AtomicWriter
    ) -> None:
        raise NotImplementedError

    def begin(self, addr: str) -> list[Message]:
        raise NotImplementedError

    def end(self, addr: str, ok: bool) -> None:
        raise NotImplementedError

    def recover(self) -> list[str]:
        raise NotImplementedError

    def redeliver_orphans(self) -> list[str]:
        raise NotImplementedError
