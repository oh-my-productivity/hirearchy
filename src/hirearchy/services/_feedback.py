"""The client rates a delivered request."""

from __future__ import annotations

from collections.abc import Sequence

from ..agents import AgentDirectory
from ..dispatch import MessageSender
from ..kernel import ROOT, Message, OrgError, latest_results
from ..mail import MailboxReader
from ._protocols import ClientFeedback
from .api import FEEDBACK_HEADER, FEEDBACK_MAX, LINK_HEADER, VERDICTS, ServiceEvidence, normalize_links

CLIENT_ONLY = (
    "criterion and confirms are root's: they record what the human client said a rejection was about. An agent client's verdict is a "
    "hypothesis and names no criterion."
)


class RuleClientFeedback(ClientFeedback):
    """A verdict is ``accept`` or ``reject`` (a rejection says what was wrong), on a request that has a result; it is a quiet note to the owner.

    Root may say what a rejection is about (``criterion``: ids the contract or the earlier rejections have, see ``ServiceEvidence.links``) and where
    the verdict comes from (``source``). When the user answers only after the rejection was recorded, ``confirms`` names it and a link note
    carries the ids: a note that refers to the rejection and is no verdict."""

    def __init__(self, agents: AgentDirectory, mail: MailboxReader, sender: MessageSender, evidence: ServiceEvidence) -> None:
        self._agents = agents
        self._mail = mail
        self._sender = sender
        self._evidence = evidence

    def feedback(
        self, actor: str, task_id: str, verdict: str, note: str = "", *, source: str | None = None, criterion: Sequence[str] | None = None,
        confirms: str | None = None,
    ) -> Message:
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
        if actor != ROOT and (criterion or confirms):
            raise OrgError(CLIENT_ONLY)
        ids = normalize_links(criterion)
        if ids and verdict == "accept":
            raise OrgError("criterion says what a rejection was about; an accept has none: leave criterion out.")
        if confirms is not None:
            self._check_confirmation(actor, task.id, verdict, ids, confirms)
        if ids:
            ids = self._evidence.links(task.to, task.service, ids, verdict=confirms)
        if confirms is not None:
            return self._sender.send(
                actor, task.to, LINK_HEADER.format(confirms=confirms) + "\n\n" + note, type="note",
                title=f'criterion link on "{task.title}": {", ".join(ids)}', reply_to=confirms, criterion=", ".join(ids), source=source, wake=False,
            )
        body = FEEDBACK_HEADER + "\n\n" + (note or "accepted")
        return self._sender.send(
            actor, task.to, body, type="note", title=f'feedback on "{task.title}": {verdict}',
            reply_to=task.id, feedback=verdict, criterion=", ".join(ids) or None, source=source, wake=False,
        )

    def _check_confirmation(self, actor: str, task_id: str, verdict: str, ids: Sequence[str], confirms: str) -> None:
        """F7-F9: ``confirms`` is a rejection ``actor`` recorded on this task, and the answer to it is a rejection that names what it was about."""
        prior = next((m for m in self._mail.sent(actor) if m.id == confirms and m.feedback and m.reply_to == task_id), None)
        if prior is None:
            raise OrgError(f"confirms must be the id of a rejection you recorded on {task_id} (the message id `feedback` returned): {confirms}")
        if prior.feedback != "reject":
            raise OrgError(f"{confirms} is an accept: only a rejection is linked to a criterion.")
        if verdict != "reject":
            raise OrgError('confirm a rejection with verdict "reject" (the verdict it repeats).')
        if not ids:
            raise OrgError("a confirmation records what the rejection was about: pass criterion (C<k>, R<k> or none).")
