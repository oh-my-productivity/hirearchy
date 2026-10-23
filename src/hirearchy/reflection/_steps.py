"""What root does next after a rejection or an amendment: the one question to ask the user, and the call that records their yes."""

from __future__ import annotations

from ..agents import AgentDirectory
from collections.abc import Sequence

from ..kernel import Message, client_questions, clip_line, latest_results, link_ids, verdict_tier
from ..mail import MailboxReader
from ..services import ServiceCatalog
from .api import CaseHistory, ServiceSteps, confirmed_criteria, regressions

ASK_C = 'About {id}: add "<the rule, in their words>" as a lasting rule? Yes or no.'
ASK_R = "Same as {id}: a one-off? Yes or no."
ASK_NONE = 'About <its id>: add "<the rule, in their words>" as a lasting rule? Yes or no.'
NOT_THEIR_YES = 'Change nothing in this turn: an "always ..." in the rejection is not their yes. '
STEP_C = (  # root read the rejection as a criterion in force
    'Next: ask the user exactly ONE yes/no question, in these words: "{question}" ' + NOT_THEIR_YES
    + 'On yes: define_service(owner="{owner}", name="{service}", add_acceptance=["<the rule>"], answers="{note}", about="{id}", '
    'words="<their answer, verbatim>"). On no, a one-off or "as it is": feedback(task_id="{task}", verdict="reject", confirms="{note}", '
    'criterion=["none"] or ["{id}"], source="human", note="<their answer, verbatim>").'
)
STEP_R = (  # root read the rejection as a repeat of an earlier one
    'Next: ask the user exactly ONE yes/no question, in these words: "{question}" ' + NOT_THEIR_YES
    + 'On yes: feedback(task_id="{task}", verdict="reject", confirms="{note}", criterion=["{id}"], source="human", note="<their answer, verbatim>"). '
    'On no, when their answer asks for a lasting rule: define_service(owner="{owner}", name="{service}", add_acceptance=["<the rule>"], '
    'answers="{note}", about="{id}", words="<their answer, verbatim>"); otherwise feedback(task_id="{task}", verdict="reject", confirms="{note}", '
    'criterion=["none"], source="human", note="<their answer, verbatim>").'
)
STEP_NONE = (  # no reading: the question names the id root chooses now
    'Next: ask the user exactly ONE yes/no question that names the criterion you read the rejection as: "{question}", with <its id> one of '
    '{criteria}{repeat}. Next time, pass your reading as criterion on the rejection and this reply gives the question with its id. ' + NOT_THEIR_YES
    + 'On yes: define_service(owner="{owner}", name="{service}", add_acceptance=["<the rule>"], answers="{note}", about="<the id you asked about>", '
    'words="<their answer, verbatim>"). On no, a one-off or "as it is": feedback(task_id="{task}", verdict="reject", confirms="{note}", '
    'criterion=["none"], ["R<j>"] or ["C<k>"], source="human", note="<their answer, verbatim>").'
)
REPEAT = '; for a repeat: "Same as R<j>: a one-off? Yes or no.", with R<j> one of {rejections}'
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


def reading_of(note: Message, criteria: Sequence[str], earlier: Sequence[str]) -> str:
    """What root read the rejection ``note`` as: the first id of its own ``criterion`` that is a criterion in force (``criteria``) or an earlier
    rejection (``earlier``); ``""`` for none, for no ``criterion`` and for ids the service lacks. It is a reading, not the user's yes."""
    return next((x for x in link_ids(note) if x in criteria or x in earlier), "")


def question_for(note: Message, criteria: Sequence[str], earlier: Sequence[str]) -> str:
    """The one yes/no question to ask the user about the rejection ``note``, with root's reading filled in (``About C3: add "..."``, ``Same as R1:
    a one-off?``); without a reading, the question root completes with the id it chooses. The reply to the rejection quotes this text, and so
    does every refusal that waits for the answer: one function words it."""
    reading = reading_of(note, criteria, earlier)
    if not reading:
        return ASK_NONE
    return (ASK_C if reading.startswith("C") else ASK_R).format(id=reading)


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
        criteria = [c.id for c in self._catalog.criteria(task.to, task.service) if c.current]
        earlier = [a.id for a in found[: found.index(mine)]]
        own = f"The criterion on the rejection itself ({note.criterion}) is recorded as not confirmed. " if note.criterion else ""
        reading = reading_of(note, criteria, earlier)
        ids = {"owner": task.to, "service": task.service, "task": note.reply_to, "note": note.id, "question": question_for(note, criteria, earlier)}
        if reading:
            step = (STEP_C if reading.startswith("C") else STEP_R).format(id=reading, **ids)
        else:
            repeat = REPEAT.format(rejections=", ".join(earlier)) if earlier else ""
            step = STEP_NONE.format(criteria=", ".join(criteria) or "none", repeat=repeat, **ids)
        return f"{own}This rejection is {mine.id}. " + step

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
