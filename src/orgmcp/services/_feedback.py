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
        actor = self._agents.require(actor)
        task = next((m for m in self._mail.sent(actor) if m.id == task_id and m.type == "task"), None)
        if task is None or not task.service:
            mine = ", ".join(m.id for m in self._mail.sent(actor) if m.type == "task" and m.service) or "none"
            raise OrgError(
                f"{task_id} is not a service request you sent. Feedback is for requests made with `request`. Yours: {mine}"
            )
        if verdict not in VERDICTS:
            raise OrgError(f"verdict must be one of {VERDICTS}")
        note = (note or "").strip()
        if verdict == "reject" and not note:
            raise OrgError("a rejection needs a note: say what was wrong, so the owner can change its playbook")
        if len(note) > FEEDBACK_MAX:
            raise OrgError(f"the note is {len(note)} characters; the limit is {FEEDBACK_MAX}. Keep it to what was wrong or good.")
        if task.id not in latest_results(self._mail.received(actor)):
            raise OrgError(f"task {task_id} has no result yet: wait for the result, then give feedback.")
        body = FEEDBACK_HEADER + "\n\n" + (note or "accepted")
        return self._sender.send(
            actor, task.to, body, type="note", title=f'feedback on "{task.title}": {verdict}',
            reply_to=task.id, feedback=verdict, wake=False,
        )
