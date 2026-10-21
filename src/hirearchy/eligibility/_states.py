"""``DerivedAgentStates``: the state word of an agent, from its mailbox and its pause flag."""

from __future__ import annotations

from ..mail import MailboxReader
from .api import AgentStates, PauseStore


class DerivedAgentStates(AgentStates):
    def __init__(self, mail: MailboxReader, pauses: PauseStore) -> None:
        self._mail = mail
        self._pauses = pauses

    def state(self, addr: str) -> str:
        if self._mail.has_inflight(addr):
            return "running"
        reason = self._pauses.paused(addr)
        if reason:
            return f"paused({reason})"
        return "pending" if self._mail.unread(addr) else "idle"
