"""``DerivedAgentStates``: the state word of an agent, from its mailbox and its pause flag."""

from __future__ import annotations

from ..mail import MailboxReader
from .api import AgentStates, PauseStore


class DerivedAgentStates(AgentStates):
    def __init__(self, mail: MailboxReader, pauses: PauseStore) -> None:
        raise NotImplementedError("red: B-eligibility")

    def state(self, addr: str) -> str:
        raise NotImplementedError("red: B-eligibility")
