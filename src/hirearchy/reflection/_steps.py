"""What root does next after a rejection or an amendment: the one question to ask the user, and the call that records their yes."""

from __future__ import annotations

from ..agents import AgentDirectory
from ..kernel import Message, client_questions, clip_line, latest_results, verdict_tier
from ..mail import MailboxReader
from ..services import ServiceCatalog
from .api import CaseHistory, ServiceSteps, confirmed_criteria, regressions

QUESTION = (
    'Next, before define_service: ask the user ONE yes/no question that names what it is about by an id, a criterion ({criteria}) or an earlier '
    'rejection ({rejections}), e.g. "About C<k>: add \'<the rule in their words>\' as a criterion?" or "Same as R<j>: a one-off?". "Always ..." is '
    "not their yes: ask anyway. Only after their yes call define_service (when the answer changes the contract), then record the answer: "
    'feedback(task_id="{task}", verdict="reject", confirms="{note}", criterion=["<the id>"], source="human", note="<their answer, verbatim>").'
)
NO_YES_YET = (
    'Rejection {rejection} (message {note}) has no recorded yes. The yes is the user\'s answer to your ONE yes/no question naming {names}; an '
    '"Always ..." in the rejection is not it. If you have not asked that question, ask it now and record nothing. Only after they answer yes: '
    'feedback(task_id="{task}", verdict="reject", confirms="{note}", criterion=[{quoted}], source="human", note="<their answer, verbatim>").'
)
REWORK = (
    "{revised}'s result asked the client: {questions}. Ask the user these questions, unless the user asked for this change: "
    "a rework does not answer them."
)
QUESTION_CHARS = 160  # each repeated question is cut to this many characters
QUESTIONS_SHOWN = 5  # at most this many are repeated; the rest are counted


class TextServiceSteps(ServiceSteps):
    """Reads the rejection (or the contract) and the cases of its service; the rejections are numbered service-wide, as ``services`` numbers them."""

    def __init__(self, agents: AgentDirectory, catalog: ServiceCatalog, history: CaseHistory, mail: MailboxReader) -> None:
        self._agents = agents
        self._catalog = catalog
        self._history = history
        self._mail = mail

    def feedback_step(self, note: Message) -> str:
        if note.feedback != "reject" or verdict_tier(note) != "human" or not note.reply_to:
            return ""
        task = next((m for m in self._mail.sent(note.sender) if m.id == note.reply_to and m.type == "task"), None)
        if task is None or not task.service or self._history.case_of(task) is None:
            return ""
        found = regressions(self._history.cases(task.to, task.service))
        mine = next((a for a in found if a.verdict.message.id == note.id), None)
        if mine is None:
            return ""
        criteria = ", ".join(c.id for c in self._catalog.criteria(task.to, task.service) if c.current) or "none"
        earlier = ", ".join(a.id for a in found if a.id != mine.id) or "none"
        own = f"The criterion on the rejection itself ({note.criterion}) is recorded as not confirmed. " if note.criterion else ""
        return f"{own}This rejection is {mine.id}. " + QUESTION.format(criteria=criteria, rejections=earlier, task=note.reply_to, note=note.id)

    def amendment_step(self, owner: str, service: str) -> str:
        owner = self._agents.require(owner)
        contract = self._catalog.read_contract(owner, service)
        if contract is None:
            return ""
        cases = self._history.cases(owner, service)
        criteria = self._catalog.criteria(owner, service)
        confirmed = confirmed_criteria(cases, criteria)
        added = [c.id for c in criteria if c.current and c.amended and c.since == contract.version and c.id not in confirmed]
        if not added:
            return ""
        latest = max(regressions(cases), key=lambda a: a.verdict.message.id, default=None)
        if latest is None:
            return ""  # an amendment outside any rejection gets no step: nothing records the user's yes to it
        head = f"Not client-confirmed: {', '.join(added)}."
        if latest.link in ("confirmed", "none"):
            return head  # the latest rejection already has the user's answer
        return f"{head} " + NO_YES_YET.format(
            rejection=latest.id, note=latest.verdict.message.id, names=", ".join(added), task=latest.verdict.task_id,
            quoted=", ".join(f'"{x}"' for x in added),
        )

    def rework_step(self, task: Message) -> str:
        if task.type != "task" or task.source != "relayed" or not task.revises:
            return ""
        results = latest_results(m for m in self._mail.received(task.sender) if m.reply_to == task.revises)
        revised = results.get(task.revises)
        questions = client_questions(revised.body) if revised is not None else []
        if not questions:
            return ""
        shown = [clip_line(q, QUESTION_CHARS) for q in questions[:QUESTIONS_SHOWN]]
        more = len(questions) - len(shown)
        listing = "; ".join(shown) + (f"; and {more} more" if more > 0 else "")
        return REWORK.format(revised=task.revises, questions=listing)
