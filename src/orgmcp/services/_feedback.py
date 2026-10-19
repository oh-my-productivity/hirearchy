"""The client rates a delivered request."""

from __future__ import annotations

from ..agents import AgentDirectory
from ..dispatch import MessageSender
from ..kernel import Message, OrgError, latest_results
from ..mail import MailboxReader
from ._protocols import ClientFeedback
from .api import FEEDBACK_HEADER, FEEDBACK_MAX, VERDICTS


class RuleClientFeedback(ClientFeedback):
    """A verdict is ``accept`` or ``reject`` (a rejection says what was wrong), on a request that has a result; it is a quiet note to the owner."""

    def __init__(self, agents: AgentDirectory, mail: MailboxReader, sender: MessageSender) -> None:
        self._agents = agents
        self._mail = mail
        self._sender = sender

    def feedback(self, actor: str, task_id: str, verdict: str, note: str = "") -> Message:
        raise NotImplementedError
