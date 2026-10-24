"""What root does next after a rejection or a rework: the one question to ask the user, and the calls that record their answer."""

from __future__ import annotations

from collections.abc import Sequence

from ..agents import AgentDirectory

from ..kernel import Message, client_questions, clip_line, latest_results, link_ids, verdict_tier
from ..mail import MailboxReader
from ..services import ServiceCatalog
from .api import CaseHistory, ServiceSteps, regressions, user_approved, user_committed

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
REWORK = (
    "{revised}'s result asked the client: {questions}. Ask the user these questions, unless the user asked for this change: "
    "a rework does not answer them."
)
TOPUP = (  # a rework the user asked for gets less than one round of the team needs (design 4.5)
    "This rework has {budget} run(s), and a rework of this team needs about {need} (1, plus 2 for each agent below {owner}). {left} Ask the user now "
    'for {ask} more run(s), with that number; on yes, grant {grant}: send(to="{owner}", budget={grant}, body=<why>) '
    '(CLI: hirearchy send {owner} "<why>" --budget {grant}).'
)
NOTHING_LEFT = "Nothing else is left of the runs the user approved for this case."
SOME_LEFT = "{spare} more of the {approved} runs the user approved for this case are left."
QUESTION_CHARS = 160  # each repeated question is cut to this many characters
QUESTIONS_SHOWN = 5  # at most this many are repeated; the rest are counted


def client_round(agents: AgentDirectory, owner: str) -> int:
    """The runs one round of the client's questions or a rejection takes the team of ``owner``: the owner reads the client's rework (1), and each
    agent below it gets one rework or re-check delegation of about 2 runs (its run and the run of its manager that processes the result)."""
    return 1 + 2 * (len(agents.subtree(owner)) - 1)


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
    """Reads the rejection and the cases of its service; the rejections are numbered service-wide, as ``services`` numbers them."""

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

    def rework_step(self, task: Message) -> str:
        if task.type != "task" or not task.revises:
            return ""
        if task.source == "human":
            return self._top_up(task)
        if task.source != "relayed":
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

    def _top_up(self, task: Message) -> str:
        """What to ask the user for when the rework they asked for carries less than one round of the owner's team and the approved runs not yet used
        do not cover the rest; "" when the case, its contract or its human client cannot be found, and when nothing needs asking."""
        case = self._history.case_of(task)
        contract = self._catalog.read_contract(task.to, task.service) if task.service else None
        if case is None or contract is None or case.client_kind != "human":
            return ""
        need = client_round(self._agents, task.to)
        if task.budget >= need:
            return ""
        approved = user_approved(case, contract.budget)
        spare = max(0, approved - user_committed(case))  # the case now holds this rework's budget too
        ask = need - task.budget - spare
        if ask <= 0:
            return ""  # what is approved and unused covers the round: root may grant it without asking
        left = SOME_LEFT.format(spare=spare, approved=approved) if spare else NOTHING_LEFT
        return TOPUP.format(budget=task.budget, need=need, owner=task.to, left=left, ask=ask, grant=need - task.budget)

