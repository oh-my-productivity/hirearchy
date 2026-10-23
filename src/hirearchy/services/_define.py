"""The client defines a service for a direct report, or amends its contract."""

from __future__ import annotations

from collections.abc import Collection, Mapping, Sequence

from ..agents import AgentDirectory
from ..delivery import MessageDelivery
from ..kernel import NAME_RE, ROOT, Clock, EventSink, JsonObject, Message, OrgError, clip_line, parent, stamp_of
from ._criteria import amendment_ids, answering_version, in_force, stored_basis, stored_versions
from ._lines import criteria_lines
from ._protocols import ContractAmendment, ContractDefinitions, LinkNotes, OwnerAddresses, PlaybookTexts, PlaybookWriter, ServicePlaces
from .api import (
    DESCRIPTION_MAX, FEEDBACK_MAX, Contract, ContractNormalizer, Criterion, Rejection, ServiceCatalog, ServiceEvidence, ServiceStore, criteria_of,
    number_criteria, quoting_lines, repeats_rejection,
)

WORDS_CLIP = 160  # characters of the user's words in the reply and in the owner's note
ROOT_ONLY = (
    "refused: answers, about and words are root's: they record the human client's answer. An agent client amends its report's contract "
    "without them. Nothing was written."
)
NOT_AN_AMENDMENT = (
    "refused: answers, about and words record the user's answer to a change of the acceptance criteria; this call changes none. Pass them only "
    "with acceptance, add_acceptance or remove_acceptance on an existing service (CLI: --acceptance, --add-acceptance, --remove-acceptance). "
    "Nothing was written."
)
PAIR = (
    "refused: answers and about go together: answers=<the rejection's message id>, about=<the C or R id your question named> "
    "(CLI: --answers, --about). Nothing was written."
)
WORDS_LONG = (
    "refused: words (CLI: --words) is {n} characters; the limit is " + str(FEEDBACK_MAX) + ": the user's answer, verbatim, not a summary. "
    "Nothing was written."
)
UNREADABLE = "refused: the record of `{name}` cannot be read ({error}), so the contract was not changed. Try again; if it persists, tell the user."
NOT_A_REJECTION = (
    'refused: answers (CLI: --answers) must be the message id of a rejection you recorded with feedback(..., source="human") '
    "(CLI: hirearchy feedback <task id> reject --note ...) on a request of `{name}`: {answers}. Its rejections: {listed}. Nothing was written."
)
ANSWERED = (
    "refused: rejection {assertion} (message {note}) already has its answer ({how}): one rejection gets one answer. A new lasting rule needs a new "
    "rejection and its question, or words alone (CLI: --words) when the user asks for it on their own. Nothing was written."
)
ABOUT = (
    "refused: about (CLI: --about) must be the id your one question named: a criterion of contract v{version}, in force when {assertion} was "
    "recorded ({criteria}), or an earlier rejection ({earlier}): {about}. A criterion this change creates cannot be what the question was about. "
    "Nothing was written."
)
WORDS_ARE_THE_REJECTION = (
    "refused: words (CLI: --words) repeats rejection {assertion}'s own note (or the note is part of it). The answer is what the user said to your "
    'one question after the rejection (e.g. "Yes, add it."); an "always ..." inside the rejection is not it. Nothing was written.'
)
LINK_FAILED = (
    "the contract of `{name}` is now v{version} (it answers rejection {note}), but the link that records the user's yes could not be written "
    '({error}). Record it with feedback(task_id="{task}", verdict="reject", confirms="{note}", criterion=[{ids}], source="human", '
    "note=<their answer, verbatim>) (CLI: --confirms, --criterion, --source human, --note){told}."
)
LINK_LOST = "The link that records the client's yes to {assertion} could not be written; it follows as a criterion link."
YES_RECORDED = "The client's yes to {assertion} (about {about}) is recorded: {ids} {are} client-confirmed."
ASKED_OWN = 'The client asked for this change on their own ("{words}"){tail}.'
ANSWER_REPLY = "Recorded as the user's answer to {assertion} (rejection {note}; your question named {about}): link {link} names {ids}."
CONFIRMED_REPLY = " {ids} {are} client-confirmed: a playbook revision citing {it} may add {its} words (rule (c))."
OWN_REPLY = 'Recorded as a change the user asked for on their own: "{words}".'
USER_INITIATED_REPLY = " {ids} {are} user-initiated: {it} with every request but never {admit} a playbook revision (rule (c))."


def _are(ids: Sequence[str]) -> str:
    return "is" if len(ids) == 1 else "are"


class RuleContractDefiner(ContractDefinitions):
    """Only the parent of the owner defines or amends; a first definition is complete, an amendment keeps what it does not name."""

    def __init__(
        self, agents: AgentDirectory, catalog: ServiceCatalog, store: ServiceStore, places: ServicePlaces, normalizer: ContractNormalizer,
        amendment: ContractAmendment, texts: PlaybookTexts, owners: OwnerAddresses, playbooks: PlaybookWriter, delivery: MessageDelivery,
        clock: Clock, events: EventSink, evidence: ServiceEvidence, links: LinkNotes,
    ) -> None:
        self._agents = agents
        self._catalog = catalog
        self._store = store
        self._places = places
        self._normalizer = normalizer
        self._amendment = amendment
        self._texts = texts
        self._owners = owners
        self._playbooks = playbooks
        self._delivery = delivery
        self._clock = clock
        self._events = events
        self._evidence = evidence
        self._links = links

    def _confirmed(self, owner: str, name: str) -> Collection[str]:
        """The criteria the client confirmed, for the mark of the note. The mark is advisory, so a record that cannot be read marks every amended
        criterion (``frozenset()``), which errs safe; any other error is a bug and propagates."""
        try:
            return self._evidence.confirmed(owner, name)
        except (OrgError, OSError):
            return frozenset()

    def _quoting(self, owner: str, name: str, removed: Sequence[Criterion]) -> tuple[dict[str, list[str]], int]:
        """The lines of the current playbook that quote each removed criterion, and its version, for the owner's note. The note is advisory, so a
        playbook that cannot be read says nothing; any other error is a bug and propagates."""
        if not removed:
            return {}, 0
        try:
            playbook = self._catalog.read_playbook(owner, name)
        except (OrgError, OSError):
            return {}, 0
        return {c.id: quoting_lines(playbook.body, c) for c in removed}, playbook.version

    def define_service(
        self, actor: str, owner: str, name: str, *, description: str | None, inputs: object, acceptance: object,
        deliverable: Mapping[str, object] | None, budget: int | None, playbook: str | None, locked: bool | None, notes: str | None,
        add_acceptance: object, remove_acceptance: object, answers: str | None, about: str | None, words: str | None,
    ) -> str:
        actor = self._agents.require(actor)
        owner = self._owners.resolve(actor, owner)
        if owner == ROOT or not self._agents.exists(owner):
            raise OrgError(f"no such agent: {owner}. A service is offered by one of your direct reports (root: a top-level agent).")
        client = parent(owner) or ROOT
        if actor != client:
            raise OrgError(
                f"only {client}, the parent of {owner}, can define its services (you are {actor}): the contract belongs "
                f"to the client. Ask {client}, or define services for your own direct reports."
            )
        if actor != ROOT and (answers is not None or about is not None or words is not None):
            raise OrgError(ROOT_ONLY)
        answers_n, about_n, words_n = (answers or "").strip(), (about or "").strip().upper(), (words or "").strip()
        given = bool(answers_n or about_n or words_n)  # what root says about where an amendment comes from
        if not NAME_RE.fullmatch(name or ""):
            raise OrgError("a service name is lowercase letters, digits and dashes, starting with a letter (max 32), e.g. weekly-brief")
        for sibling in self._agents.children(client):
            if sibling != owner and name in self._catalog.service_names(sibling):
                raise OrgError(
                    f"a service called `{name}` already exists at {sibling}. Requests name the service only, so names "
                    f"must be unique among the agents that report to {client}: pick another name."
                )
        old = self._catalog.read_contract(owner, name)
        if old is None and given:
            raise OrgError(NOT_AN_AMENDMENT)
        if old is not None and playbook is not None:
            raise OrgError(
                f"the playbook belongs to {owner}, which revises it with revise_playbook: do not pass `playbook` when "
                "you redefine the contract. Leave it out; the existing playbook stays."
            )
        if acceptance is not None and (add_acceptance is not None or remove_acceptance is not None):
            raise OrgError(
                "`acceptance` replaces all criteria; do not combine it with add_acceptance / remove_acceptance. Use "
                "add_acceptance / remove_acceptance alone to change single criteria."
            )
        if old is None:
            if add_acceptance is not None or remove_acceptance is not None:
                raise OrgError(
                    f"service `{name}` does not exist yet: add_acceptance / remove_acceptance amend an existing contract. "
                    "Give the full `acceptance` list for a first definition."
                )
            missing = [k for k, v in (("description", description), ("acceptance", acceptance), ("deliverable", deliverable),
                                      ("budget", budget)) if v is None]
            if missing:
                raise OrgError(f"a first definition of `{name}` needs {', '.join(missing)} (it does not exist yet, so there is nothing to keep)")

        if description is not None:
            description = description.strip() if isinstance(description, str) else ""
            if not description or len(description) > DESCRIPTION_MAX or "\n" in description:
                raise OrgError(f"description is one line of at most {DESCRIPTION_MAX} characters saying what the service delivers")
        if budget is not None and (isinstance(budget, bool) or not isinstance(budget, int) or budget < 1):
            raise OrgError("budget is the number of runs handed down with each request: a whole number, at least 1")
        if locked is not None and not isinstance(locked, bool):
            raise OrgError("locked must be true or false")
        inputs_n = self._normalizer.inputs(inputs) if inputs is not None or old is None else old.inputs
        deliverable_n = self._normalizer.deliverable(deliverable) if deliverable is not None else (old.deliverable if old else {})
        stored = stored_versions(self._store, owner, name) if old is not None else []  # the ids of the versions on disk (3.3)
        basis = stored_basis(self._store, owner, name) if old is not None else {}  # what each of them records
        current = criteria_of(number_criteria(stored, basis), old.acceptance) if old is not None else []  # the old contract's criteria, with ids
        if acceptance is not None:
            accept_n = criteria_lines(acceptance, "acceptance", required=True)
        elif old is None:
            accept_n = []
        else:
            accept_n = self._amendment.amended_criteria(name, current, add_acceptance, remove_acceptance)
        playbook_body = self._texts.body(playbook) if playbook is not None else None

        now = self._clock.now().isoformat(timespec="microseconds")
        notes_n = (notes if notes is not None else (old.notes if old else "") or "").strip()
        new = Contract(
            name=name, owner=owner, description=description if description is not None else (old.description if old else ""),
            inputs=inputs_n, acceptance=accept_n, deliverable=deliverable_n,
            budget=budget if budget is not None else (old.budget if old else 1),
            locked=locked if locked is not None else (old.locked if old else False),
            version=1 if old is None else old.version + 1, notes=notes_n,
        )
        meta: JsonObject = {
            "name": name, "description": new.description, "inputs": new.inputs, "acceptance": new.acceptance,
            "deliverable": new.deliverable, "budget": new.budget, "locked": new.locked, "version": new.version, "defined_by": actor,
            "defined": now, "created": now if old is None or old.created is None else old.created.isoformat(timespec="microseconds"),
        }
        changes: list[str] = []
        confirmed: Collection[str] = frozenset()
        numbered = [*stored, (new.version, actor, accept_n)]  # the new version is numbered in memory, before it is written
        after = number_criteria(numbered, basis)
        answered: Rejection | None = None
        if old is not None:
            changes = self._amendment.changes(old, new, {c.text: c.id for c in after})
            if not changes:
                raise OrgError(
                    f"no change: the amendment leaves the contract of `{name}` exactly as it is (v{old.version}). "
                    f"Current criteria:\n{self._amendment.listed(current)}"
                )
            if given and set(accept_n) == set(old.acceptance):
                raise OrgError(NOT_AN_AMENDMENT)
            if given:
                answered = self._check_answer(owner, name, answers_n, about_n, words_n)
                meta.update({"answers": answered.note, "about": about_n, "words": words_n} if answered else {"initiated": "user", "words": words_n})
            confirmed = self._confirmed(owner, name)  # read before the write: the note marks what the client has not yet confirmed
        added, removed = amendment_ids(numbered, new.version) if given else ((), ())
        where = self._store.write_contract(owner, name, meta, notes_n, old.version if old is not None else None)
        self._events.emit("service.define", actor=actor, owner=owner, service=name, version=new.version, by=actor, amendment=old is not None)
        if old is None:
            text = f"defined service `{name}` (contract v1) for {owner}: {where}"
            if playbook_body is not None:
                text += f"; playbook v1: {self._playbooks.write(owner, name, 1, playbook_body, actor, 'initial playbook')}"
            else:
                text += f". It has no playbook yet: {owner} writes v1 with revise_playbook after its first request."
            return text
        link: Message | None = None
        link_error: Exception | None = None
        if answered is not None:  # the user's yes is recorded by the product itself, after the contract it is about and before the owner is told
            try:
                link = self._links.write(actor, owner, answered.title, answered.note, added or removed, words_n)
            except (OrgError, OSError) as error:
                link_error = error
        marked = after if not given else number_criteria(numbered, {**basis, new.version: (answered.note if answered else "", answered is None)})
        shown = criteria_of(marked, accept_n)
        quoting, version = self._quoting(owner, name, [c for c in current if c.text not in accept_n])
        told: OrgError | OSError | None = None
        try:
            self._delivery.notify(
                owner, f"contract of service {name} changed to v{new.version}",
                self._amendment.diff(
                    old, new, [*changes, *self._basis_lines(answered, about_n, words_n, added, removed, link is not None)], where, shown,
                    {*confirmed, *((added or removed) if link is not None else ())}, quoting, version,
                ), wake=False,
            )
        except (OrgError, OSError) as error:
            if link_error is None:
                raise
            told = error
        if link_error is not None and answered is not None:
            raise OrgError(LINK_FAILED.format(
                name=name, version=new.version, note=answered.note, error=link_error, task=answered.task,
                ids=", ".join(f'"{x}"' for x in added or removed), told=f"; the owner was not told either ({told})" if told is not None else "",
            ))
        kept = self._places.rel(self._places.history_file(owner, name, "SERVICE", old.version))
        return (
            f"redefined service `{name}` of {owner}: contract v{old.version} -> v{new.version} ({where}); the old one "
            f"is kept at {kept}. {owner} was told (without waking it).\n"
            "Changed:\n" + "\n".join(changes)
            + f"\nAcceptance criteria now ({len(accept_n)}):\n{self._amendment.listed(shown)}"
            + self._recorded(answered, link, about_n, words_n, added, removed)
        )

    def _check_answer(self, owner: str, name: str, answers: str, about: str, words: str) -> Rejection | None:
        """Root's acceptance amendment with the user's words (steps 3.1, 3.3-3.5): the rejection it answers, or None for a change the user asked
        for on their own (``words`` alone). A refusal writes nothing."""
        try:
            basis = self._evidence.amendment_basis(owner, name)
        except (OrgError, OSError) as error:
            raise OrgError(UNREADABLE.format(name=name, error=error)) from error
        if len(words) > FEEDBACK_MAX:
            raise OrgError(WORDS_LONG.format(n=len(words)))
        if bool(answers) != bool(about):
            raise OrgError(PAIR)
        if not answers:
            return None
        found = next((r for r in basis.rejections if r.note == answers), None)
        if found is None:
            listed = ", ".join(f"{r.assertion} (message {r.note})" for r in basis.rejections) or "none yet"
            raise OrgError(NOT_A_REJECTION.format(name=name, answers=answers, listed=listed))
        answering = answering_version(self._store, owner, name, found.note)
        if found.answered or answering:
            how = f"link note {found.answered}" if found.answered else f"contract v{answering}"
            raise OrgError(ANSWERED.format(assertion=found.assertion, note=found.note, how=how))
        version, criteria = in_force(self._store, owner, name, stamp_of(found.note))
        ids = [c.id for c in criteria]
        if about not in ids and about not in found.earlier:
            raise OrgError(ABOUT.format(
                version=version, assertion=found.assertion, criteria=", ".join(ids), earlier=", ".join(found.earlier) or "none", about=about,
            ))
        if repeats_rejection(words, found.words):
            raise OrgError(WORDS_ARE_THE_REJECTION.format(assertion=found.assertion))
        return found

    @staticmethod
    def _basis_lines(
        answered: Rejection | None, about: str, words: str, added: Sequence[str], removed: Sequence[str], linked: bool,
    ) -> list[str]:
        """The line the owner's note carries after the changes: what the amendment answers (the yes, or its missing link), or that the user asked
        for it on their own."""
        if answered is not None:
            if not linked:
                return [LINK_LOST.format(assertion=answered.assertion)]
            ids = added or removed
            return [YES_RECORDED.format(assertion=answered.assertion, about=about, ids=", ".join(ids), are=_are(ids))]
        if words:
            tail = f": {', '.join(added)} {_are(added)} user-initiated" if added else ""
            return [ASKED_OWN.format(words=clip_line(words, WORDS_CLIP), tail=tail)]
        return []

    @staticmethod
    def _recorded(answered: Rejection | None, link: Message | None, about: str, words: str, added: Sequence[str], removed: Sequence[str]) -> str:
        """The sentence the reply ends with: the answer recorded as the user's, or the change recorded as theirs alone (``""`` for neither)."""
        if answered is not None and link is not None:
            ids = added or removed
            text = ANSWER_REPLY.format(assertion=answered.assertion, note=answered.note, about=about, link=link.id, ids=", ".join(ids))
            if added:
                one = len(added) == 1
                text += CONFIRMED_REPLY.format(ids=", ".join(added), are=_are(added), it="it" if one else "them", its="its" if one else "their")
            return "\n" + text
        if words:
            text = OWN_REPLY.format(words=clip_line(words, WORDS_CLIP))
            if added:
                one = len(added) == 1
                text += USER_INITIATED_REPLY.format(
                    ids=", ".join(added), are=_are(added), it="it travels" if one else "they travel", admit="admits" if one else "admit",
                )
            return "\n" + text
        return ""
