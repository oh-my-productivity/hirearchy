"""RED skeleton (B-traces): the lookup of traces in the mailboxes."""

from __future__ import annotations

from ..mail import MailboxReader
from ._ports import AgentPresence
from .api import TraceLookup


class MailboxTraceLookup(TraceLookup):
    """What the mailboxes of an agent say about traces."""

    def __init__(self, mail: MailboxReader, agents: AgentPresence) -> None:
        self._mail = mail
        self._agents = agents

    def trace_of(self, addr: str, msg_id: str | None) -> str | None:
        raise NotImplementedError("red: B-traces")

    def open_task_traces(self, addr: str) -> list[str | None]:
        raise NotImplementedError("red: B-traces")

    def context_trace(self, addr: str) -> tuple[str | None, str, list[str]]:
        raise NotImplementedError("red: B-traces")
