"""The client rates a delivered request."""

from __future__ import annotations

from collections.abc import Sequence

from ..agents import AgentDirectory
from ..dispatch import MessageSender
from ..kernel import ROOT, Message, OrgError, latest_results, link_ids, verdict_tier
from ..mail import MailboxReader
from ._criteria import answer_ids, answering_version, unanswered
from ._protocols import ClientFeedback, LinkNotes, WatchSettlement
from ._watch import watch_before
from .api import FEEDBACK_HEADER, FEEDBACK_MAX, LINK_HEADER, VERDICTS, ServiceEvidence, ServiceStore, normalize_links

CLIENT_ONLY = (
    "criterion and confirms are root's: they record what the human client said a rejection was about. An agent client's verdict is a "
    "hypothesis and names no criterion."
)
CONFIRMS_ANSWERED = (
    "refused: rejection {confirms} was answered by contract v{n} of `{service}` (define_service(..., answers=\"{confirms}\"); CLI: define-service "
    "--answers) and its link {link} records the user's yes: one rejection gets one answer. A different answer needs a new rejection and its "
    "question. Nothing was recorded."
)
CONFIRMS_RECOVERY = (
    "refused: rejection {confirms} was answered by contract v{n} of `{service}`, and its link is missing (its write failed). The only link it "
    'still takes is that one: feedback(task_id="{task}", verdict="reject", confirms="{confirms}", criterion=[{ids}], source="human", '
    "note=<the user's answer, verbatim>) (CLI: --confirms, --criterion, --source human, --note). Nothing was recorded."
)
ONE_OFF_UNKNOWN = (  # root only: a one-off task is a task root sent without a service (design 8.3)
    "refused: {task_id} is not a task you sent: feedback records the user's verdict on one of your service requests or one-off tasks that has a "
    "result. Your newest: {newest}. Nothing was recorded."
)
ONE_OFF_NO_LINK = (
    "refused: {task_id} is a one-off task: it has no contract, so its verdict names no criterion and answers no rejection. Leave out criterion "
    "and confirms (CLI: --criterion, --confirms). Nothing was recorded."
)
ONE_OFF_GONE = "refused: {to}, who did {task_id}, was retired, so the verdict has no one to tell. Nothing was recorded."
NEWEST = 10  # the ids ONE_OFF_UNKNOWN names
FEEDBACK_UNANSWERED = (  # FEEDBACK-UNANSWERED (clause 2, design 13.2): {more} is "" or " (and {k} more: {R ids})"
    "refused: rejection {assertion} (message {note}) on task {task} of this case of `{service}` has no recorded answer yet{more}, so the user's "
    "accept waits: a case is closed only after its rejections have the user's answers. Record the answer first, then this accept again. "
    "Ask the user the one question first if you have not: {question}. On yes: "
    'define_service(owner="{owner}", name="{service}", ..., answers="{note}", about=<the id you asked about>, words=<their answer, verbatim>) '
    "(CLI: hirearchy define-service ... --answers, --about, --words). "
    'On no, a one-off or "as it is": feedback(task_id="{task}", verdict="reject", confirms="{note}", criterion=["none"], '
    '["R<j>"] or ["C<k>"], source="human", note=<their answer, verbatim>) '
    "(CLI: hirearchy feedback <task> reject --confirms ... --criterion ... --source human --note ...). Nothing was recorded."
)
FEEDBACK_UNREADABLE = (  # FEEDBACK-UNREADABLE (design 13.2)
    "refused: the record of `{service}` cannot be read ({error}), so the verdict was not recorded. Try again; if it persists, tell the user."
)


class SenderLinkNotes(LinkNotes):
    """The link note that says what a rejection was about, written through the message sender: one shape for ``feedback(confirms=...)`` and for
    ``define_service(answers=...)``."""

    def __init__(self, sender: MessageSender) -> None:
        self._sender = sender

    def write(self, actor: str, owner: str, title: str, rejection: str, ids: Sequence[str], words: str, source: str | None = "human") -> Message:
        return self._sender.send(
            actor, owner, LINK_HEADER.format(confirms=rejection) + "\n\n" + words, type="note",
            title=f'criterion link on "{title}": {", ".join(ids)}', reply_to=rejection, criterion=", ".join(ids), source=source, wake=False,
        )


class RuleClientFeedback(ClientFeedback):
    """A verdict is ``accept`` or ``reject`` (a rejection says what was wrong), on a request that has a result; it is a quiet note to the owner.
    Root also rates its one-off tasks (tasks without a service) the same way, but names no criterion on them: a one-off has no contract.

    Root may say what a rejection is about (``criterion``: ids the contract or the earlier rejections have, see ``ServiceEvidence.links``) and where
    the verdict comes from (``source``). When the user answers only after the rejection was recorded, ``confirms`` names it and a link note
    carries the ids: a note that refers to the rejection and is no verdict."""

    def __init__(
        self, agents: AgentDirectory, mail: MailboxReader, sender: MessageSender, evidence: ServiceEvidence, store: ServiceStore,
        settler: WatchSettlement,
    ) -> None:
        self._settler = settler
        self._agents = agents
        self._mail = mail
        self._sender = sender
        self._evidence = evidence
        self._store = store
        self._links: LinkNotes = SenderLinkNotes(sender)

    def feedback(
        self, actor: str, task_id: str, verdict: str, note: str = "", *, source: str | None = None, criterion: Sequence[str] | None = None,
        confirms: str | None = None,
    ) -> Message:
        actor = self._agents.require(actor)
        task = next((m for m in self._mail.sent(actor) if m.id == task_id and m.type == "task"), None)
        if task is None or not task.service:
            if actor == ROOT:
                return self._one_off(actor, task_id, task, verdict, note, source, criterion, confirms)
            mine = ", ".join(m.id for m in self._mail.sent(actor) if m.type == "task" and m.service) or "none"
            raise OrgError(
                f"{task_id} is not a service request you sent. Feedback is for requests made with `request`. Yours: {mine}"
            )
        note = self._checked(actor, task_id, verdict, note)
        if actor == ROOT and verdict == "accept" and source == "human":
            self._answered_first(actor, task)
        if actor != ROOT and (criterion or confirms):
            raise OrgError(CLIENT_ONLY)
        ids = normalize_links(criterion)
        if ids and verdict == "accept":
            raise OrgError("criterion says what a rejection was about; an accept has none: leave criterion out.")
        if confirms is not None:
            self._check_confirmation(actor, task, verdict, ids, confirms, source)
        if ids:
            ids = self._evidence.links(task.to, task.service, ids, verdict=confirms)
        if confirms is not None:
            return self._linked(actor, task, confirms, ids, note, source)
        return self._record(actor, task, verdict, note, source, ", ".join(ids) or None)

    def _linked(self, actor: str, task: Message, confirms: str, ids: Sequence[str], note: str, source: str | None) -> Message:
        """The link note, and, when it is the user's (human tier), the watch settled (design 8.5): a rejection becomes related to an item only through
        a human link or an answering version, so this is a moment a retire can fall due. ``before`` is read first; the settler never raises here."""
        service = task.service or ""
        before = watch_before(self._evidence, task.to, service) if source == "human" else None
        link = self._links.write(actor, task.to, task.title, confirms, ids, note, source=source)
        if verdict_tier(link) == "human":
            self._settler.settle(task.to, service, before)
        return link

    def _checked(self, actor: str, task_id: str, verdict: str, note: str) -> str:
        """The checks every verdict takes, in this order: the verdict, the note (a rejection needs one, at most ``FEEDBACK_MAX`` characters) and
        the task's result. Returns the note, stripped."""
        if verdict not in VERDICTS:
            raise OrgError(f"verdict must be one of {VERDICTS}")
        note = (note or "").strip()
        if verdict == "reject" and not note:
            raise OrgError("a rejection needs a note: say what was wrong, so the owner can change its playbook")
        if len(note) > FEEDBACK_MAX:
            raise OrgError(f"the note is {len(note)} characters; the limit is {FEEDBACK_MAX}. Keep it to what was wrong or good.")
        if task_id not in latest_results(self._mail.received(actor)):
            raise OrgError(f"task {task_id} has no result yet: wait for the result, then give feedback.")
        return note

    def _answered_first(self, actor: str, task: Message) -> None:
        """Clause 2 (design 13.2): the user's accept of a case waits while an earlier human rejection of the same case has no recorded answer
        (``unanswered``), unless the accepted task is one whose delivery has no verdict yet (``basis.unrated``): P2-UNRATED makes the answer wait for
        exactly that verdict. The case is the one of the head of the task's ``revises`` chain; a record that cannot be read refuses too."""
        service = task.service or ""
        try:
            head = self._case_head(actor, task)
            basis = self._evidence.amendment_basis(task.to, service)
            waiting = [r for r in unanswered(basis, self._store, task.to, service) if r.case == head]
        except (OrgError, OSError) as error:
            raise OrgError(FEEDBACK_UNREADABLE.format(service=service, error=error)) from error
        if not waiting or task.id in basis.unrated:
            return
        oldest, others = waiting[0], waiting[1:]
        more = f" (and {len(others)} more: {', '.join(r.assertion for r in others)})" if others else ""
        raise OrgError(FEEDBACK_UNANSWERED.format(
            assertion=oldest.assertion, note=oldest.note, task=oldest.task, service=service, more=more, question=oldest.question.removesuffix("."),
            owner=task.to,
        ))

    def _case_head(self, actor: str, task: Message) -> str:
        """The id of the first task of ``task``'s ``revises`` chain in ``actor``'s sent mail, followed only through tasks of the same service sent to
        the same assignee (the head ``CaseHistory`` uses): a task that revises one sent to another assignee starts its own case."""
        sent = {m.id: m for m in self._mail.sent(actor) if m.type == "task"}
        head, seen = task, {task.id}
        while head.revises and head.revises not in seen:
            earlier = sent.get(head.revises)
            if earlier is None or earlier.service != task.service or earlier.to != task.to:
                break
            head = earlier
            seen.add(head.id)
        return head.id

    def _record(self, actor: str, task: Message, verdict: str, note: str, source: str | None, criterion: str | None) -> Message:
        """The verdict as a quiet note to the task's assignee: it wakes nobody and costs no run."""
        return self._sender.send(
            actor, task.to, FEEDBACK_HEADER + "\n\n" + (note or "accepted"), type="note", title=f'feedback on "{task.title}": {verdict}',
            reply_to=task.id, feedback=verdict, criterion=criterion, source=source, wake=False,
        )

    def _one_off(
        self, actor: str, task_id: str, task: Message | None, verdict: str, note: str, source: str | None, criterion: Sequence[str] | None,
        confirms: str | None,
    ) -> Message:
        """Root's verdict on a task it sent without a service (design 8.1): the same quiet note, no criterion and no confirmation (there is no
        contract to name one in), and an assignee that still exists to receive it."""
        if task is None:
            results = latest_results(self._mail.received(actor))
            sent = sorted((m.id for m in self._mail.sent(actor) if m.type == "task" and m.id in results), reverse=True)
            raise OrgError(ONE_OFF_UNKNOWN.format(task_id=task_id, newest=", ".join(sent[:NEWEST]) or "none"))
        if criterion or confirms:
            raise OrgError(ONE_OFF_NO_LINK.format(task_id=task_id))
        note = self._checked(actor, task_id, verdict, note)
        if not self._agents.exists(task.to):
            raise OrgError(ONE_OFF_GONE.format(to=task.to, task_id=task_id))
        return self._record(actor, task, verdict, note, source, None)

    def _check_confirmation(
        self, actor: str, task: Message, verdict: str, ids: Sequence[str], confirms: str, source: str | None,
    ) -> None:
        """F7-F9: ``confirms`` is a rejection ``actor`` recorded on this task, and the answer to it is a rejection that names what it was about.
        Then one rejection has one answer (P2): when a contract version answers it (``define_service(answers=...)``), the link the product wrote
        is that answer, and nothing else is recorded on it, except the same link when its write failed."""
        prior = next((m for m in self._mail.sent(actor) if m.id == confirms and m.feedback and m.reply_to == task.id), None)
        if prior is None:
            raise OrgError(f"confirms must be the id of a rejection you recorded on {task.id} (the message id `feedback` returned): {confirms}")
        if prior.feedback != "reject":
            raise OrgError(f"{confirms} is an accept: only a rejection is linked to a criterion.")
        if verdict != "reject":
            raise OrgError('confirm a rejection with verdict "reject" (the verdict it repeats).')
        if not ids:
            raise OrgError("a confirmation records what the rejection was about: pass criterion (C<k>, R<k> or none).")
        n = answering_version(self._store, task.to, task.service or "", confirms)
        if n == 0:
            return
        link = next(
            (m for m in self._mail.sent(actor) if m.reply_to == confirms and m.type == "note" and not m.feedback and link_ids(m) and verdict_tier(m) == "human"),
            None,
        )
        if link is not None:
            raise OrgError(CONFIRMS_ANSWERED.format(confirms=confirms, n=n, service=task.service, link=link.id))
        expected = answer_ids(self._store, task.to, task.service or "", n)
        if source != "human" or set(ids) != set(expected):
            raise OrgError(CONFIRMS_RECOVERY.format(
                confirms=confirms, n=n, service=task.service, task=task.id, ids=", ".join(f'"{x}"' for x in expected),
            ))
