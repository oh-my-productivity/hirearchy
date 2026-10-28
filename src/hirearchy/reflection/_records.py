"""``DerivedCaseRecords``: what the files show of every service and of root's one-off tasks, for the quality view and for health (design 12.1).

Everything is derived per call and nothing is stored. A file of the organization whose frontmatter does not parse raises a YAML error out of the
readers, and a file that is not UTF-8 raises ``UnicodeDecodeError``; PyYAML may be imported by ``kernel`` and ``blueprint`` only, so every read that can
meet one goes through ``_read``, which words the failure by its type and turns it into the record's ``error``. The rules that compute from what was read
are never inside that catch."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from typing import TypeVar

from ..agents import AgentDirectory
from ..kernel import ROOT, JsonObject, Message, OrgError, clip_line, latest_results, msg_time, parent
from ..mail import MailboxReader
from ..services import (
    Contract, Criterion, ServiceCatalog, ServiceEvidence, amendment_ids, contract_of, number_criteria, version_in_force,
)
from ._marks import contract_marks, playbook_marks, top_up_marks
from ._ports import BarHistory, ContractVersions
from .api import (
    LASTING_WORDS, Assertion, BarChanges, Case, CaseHistory, CaseRecords, Cause, CharterMark, DeliverableChecks, DeliverableFinding, Delivery, Mark,
    ModelMark, OwnerDeliveries, ServiceRecord, cause_of, deliveries_of, regressions, signer_of,
)

T = TypeVar("T")
ORG_MD = "ORG.md"
_ERROR_CLIP = 200  # characters of an exception's words in a record's error
_EARLIEST = datetime.min.replace(tzinfo=timezone.utc)
_KIND_RANK = {"ContractMark": 0, "PlaybookMark": 1, "TopUpMark": 2, "CharterMark": 3, "ModelMark": 4}  # marks of one moment, in this order


class _Unreadable(Exception):
    """A read failed: the text is the record's ``error``, ``{read}: {words}``."""


def _words(exc: BaseException) -> str:
    """How an exception reads in a record's error. ``OrgError``/``OSError`` keep their own words; text that is not UTF-8 and a YAML error are named by
    what they mean, without importing PyYAML (a YAML exception is recognised by the module of its class); any other exception shows its type and words,
    so a programming error is not worded as a file that does not parse."""
    if isinstance(exc, (OrgError, OSError)):
        return clip_line(str(exc), _ERROR_CLIP)
    if isinstance(exc, UnicodeDecodeError):
        return "is not UTF-8"
    kind = type(exc)
    if kind.__module__.startswith("yaml"):
        return f"does not parse ({kind.__name__})"
    return f"cannot be read ({kind.__name__}: {clip_line(str(exc), _ERROR_CLIP)})"


def _read(label: str, read: Callable[[], T]) -> T:
    """``read()``, or ``_Unreadable("{label}: {words}")`` when it raises anything."""
    try:
        return read()
    except Exception as exc:  # noqa: BLE001 - yaml errors of any kind, text that is not UTF-8
        raise _Unreadable(f"{label}: {_words(exc)}") from exc


@dataclass(frozen=True)
class _Versions:
    """The stored versions of one contract, parsed once: the contracts, their ``(version, defined_by, acceptance)`` and each criterion text's id."""

    contracts: tuple[Contract, ...]
    stored: tuple[tuple[int, str, list[str]], ...]
    ids: Mapping[str, str]


def _versions_of(owner: str, name: str, raw: Sequence[tuple[int, JsonObject, str]]) -> _Versions:
    contracts = tuple(contract_of(owner, name, meta, body, None) for _, meta, body in raw)
    stored = tuple((c.version, c.defined_by or "", c.acceptance) for c in contracts)
    return _Versions(contracts, stored, {c.text: c.id for c in number_criteria(list(stored))})


def _carried(facts: _Versions, task: Message) -> tuple[int, frozenset[str] | None]:
    """The contract version ``task`` carried and its criteria ids: the version it records, else (a legacy task) the version in force when it was
    sent; ``None`` for the ids when that version is not stored."""
    if task.contract is not None:
        number = task.contract
    else:
        chosen = version_in_force(list(facts.contracts), msg_time(task))
        number = chosen.version if chosen is not None else 0
    found = next((c for c in facts.contracts if c.version == number), None)
    return number, None if found is None else frozenset(facts.ids[text] for text in found.acceptance)


def _answering(facts: _Versions, rejection: str) -> tuple[int, tuple[str, ...]]:
    """The oldest stored version that answers the rejection ``rejection`` and the criteria it removes; ``(0, ())`` when none does."""
    found = next((c for c in facts.contracts if rejection and c.answers == rejection), None)
    return (0, ()) if found is None else (found.version, amendment_ids(list(facts.stored), found.version)[1])


@dataclass
class _Boxes:
    """The mailboxes one call reads, each once."""

    mail: MailboxReader
    agents: AgentDirectory
    received: dict[str, list[Message]] = field(default_factory=dict)
    sent: dict[str, list[Message]] = field(default_factory=dict)
    results: dict[str, dict[str, Message]] = field(default_factory=dict)


def _received(boxes: _Boxes, addr: str) -> list[Message]:
    if addr not in boxes.received:
        boxes.received[addr] = boxes.mail.received(addr)
    return boxes.received[addr]


def _sent(boxes: _Boxes, addr: str) -> list[Message]:
    if addr not in boxes.sent:
        boxes.sent[addr] = boxes.mail.sent(addr)
    return boxes.sent[addr]


def _results(boxes: _Boxes, client: str) -> dict[str, Message]:
    """The latest result of each task the client sent."""
    if client not in boxes.results:
        boxes.results[client] = latest_results(_received(boxes, client))
    return boxes.results[client]


def _deliveries_in(boxes: _Boxes, client: str, case: Case) -> tuple[Delivery, ...]:
    """The deliveries of ``case`` with the agent that signed each off."""
    results, owner = _results(boxes, client), case.owner
    reports = set(boxes.agents.children(owner))
    signers = {
        t.id: signer_of(owner, t.id, done.id, _sent(boxes, owner), _received(boxes, owner), reports)
        for t in case.tasks if (done := results.get(t.id)) is not None and done.status == "done"
    }
    return deliveries_of(case, results, signers)


def _attributed(deliveries: Sequence[Delivery], findings: Sequence[DeliverableFinding]) -> tuple[Delivery, ...]:
    """The deliveries with what the deliverable folders say (design 4.3): a delivery a ``differs`` finding names is not as delivered since the earliest
    write time among its files (``edited_at``; 0 when no time is known, and then nothing is voided); the delivery a ``relayed`` or a ``given`` finding names
    is the one the user was given, and is not a deviation. Other kinds name no delivery."""
    writes: dict[str, list[int]] = {}
    given: set[str] = set()
    for found in findings:
        if found.kind == "differs":
            writes.setdefault(found.task, []).append(found.written)
        elif found.kind in ("relayed", "given"):
            given.add(found.task)
    out = []
    for d in deliveries:
        if d.task.id in writes:
            d = replace(d, edited=True, edited_at=min((t for t in writes[d.task.id] if t > 0), default=0))
        if d.task.id in given:
            d = replace(d, given=True)
        out.append(d)
    return tuple(out)


def _cause(delivery: Delivery, case: Case, assertions: Mapping[str, Assertion], facts: _Versions | None, results: Mapping[str, Message]) -> Cause | None:
    """The cause of ``delivery`` when it is an escape, else None. ``assertions`` maps a verdict's note id to its ``R<k>``; ``facts`` are the stored
    contract versions, ``None`` for a one-off case (no contract, no criterion named)."""
    verdict = delivery.decisive
    if not delivery.escape or verdict is None:
        return None
    assertion = assertions.get(verdict.message.id) or Assertion("", case.id, verdict, (), "")
    if facts is None:
        return cause_of(delivery, case, assertion, frozenset(), (), results, LASTING_WORDS)
    version, carried = _carried(facts, delivery.task)
    answering, removes = _answering(facts, verdict.message.id)
    return cause_of(delivery, case, assertion, carried, removes, results, LASTING_WORDS, version=version, answering=answering)


def _when(mark: Mark) -> tuple[datetime, int]:
    return (getattr(mark, "when", None) or _EARLIEST, _KIND_RANK[type(mark).__name__])


class DerivedCaseRecords(CaseRecords):
    def __init__(
        self, history: CaseHistory, catalog: ServiceCatalog, agents: AgentDirectory, mail: MailboxReader, versions: ContractVersions, bars: BarHistory,
        deliverables: DeliverableChecks, evidence: ServiceEvidence,
    ) -> None:
        self._history = history
        self._catalog = catalog
        self._agents = agents
        self._mail = mail
        self._versions = versions
        self._bars = bars
        self._deliverables = deliverables
        self._evidence = evidence

    # ---------------------------------------------------------------------------------------------------- records

    def records(self, service: str | None = None) -> list[ServiceRecord]:
        addrs = self._agents.agents()
        listed = [(addr, name) for addr in addrs for name in self._catalog.service_names(addr)]
        top = sorted((o, n) for o, n in listed if (parent(o) or ROOT) == ROOT)
        nested = sorted((o, n) for o, n in listed if (parent(o) or ROOT) != ROOT)
        if service is not None and not any(n == service for _, n in listed):
            names = ", ".join(dict.fromkeys(n for _, n in [*top, *nested])) or "none"
            raise OrgError(f"no service named `{service}`: the services are {names}. Call quality() without a service for everything.")
        chosen = [(o, n) for o, n in [*top, *nested] if service is None or n == service]
        mail = _Boxes(self._mail, self._agents)
        findings, files_error = self._findings()
        bars = self._bars.changes(addrs)
        out = [r for owner, name in chosen if (r := self._service(mail, owner, name, findings, files_error, bars)) is not None]
        if service is None:
            out.append(self._one_off(mail, findings, files_error, bars))
        return out

    def _findings(self) -> tuple[list[DeliverableFinding], str]:
        """The one P3 call of a ``records()`` call: the findings, or the error that stopped it (then no delivery is counted as not as delivered)."""
        try:
            return _read("the deliverable folders", lambda: self._deliverables.findings(ROOT, None, settled=True)), ""
        except _Unreadable as unreadable:
            return [], str(unreadable)

    def _service(
        self, mail: _Boxes, owner: str, name: str, findings: Sequence[DeliverableFinding], files_error: str, bars: BarChanges,
    ) -> ServiceRecord | None:
        client = parent(owner) or ROOT
        kind = "human" if client == ROOT else "agent"
        try:
            contract = _read("SERVICE.md", lambda: self._catalog.read_contract(owner, name))
            if contract is None:
                return None
            criteria = _read("the criteria", lambda: self._catalog.criteria(owner, name))
            raw = _read("the stored contract versions", lambda: self._versions.versions(owner, name, "SERVICE"))
            facts = _read("the stored contract versions", lambda: _versions_of(owner, name, raw))
            playbooks = _read("the playbook versions", lambda: self._catalog.playbook_versions(owner, name))
            watch = _read("the playbook watch", lambda: self._evidence.watch(owner, name))  # the one derivation every reader of a watch state shares
            cases = _read("the cases", lambda: self._history.cases(owner, name))  # the cases ``case_total`` reads: built with the contract's per-request budget
            deliveries = _attributed(_read("the mailboxes", lambda: self._all(mail, client, cases)), findings)
            assertions = regressions(cases)
            marks: list[Mark] = [
                *_read("the stored contract versions", lambda: contract_marks(owner, name, raw, cases)),
                *_read("the playbook versions", lambda: playbook_marks(owner, playbooks, criteria, cases)),
                *top_up_marks(cases), *self._bar_marks(bars, set(self._agents.subtree(owner))),
            ]
            results = _read("the mailboxes", lambda: _results(mail, client))
            escapes = self._escapes(deliveries, cases, assertions, facts, results)
        except _Unreadable as unreadable:
            return ServiceRecord(owner, name, client, kind, error=str(unreadable))
        return ServiceRecord(
            owner, name, client, kind, contract=contract.version, playbook=playbooks[-1].version if playbooks else 0, budget=contract.budget,
            cases=tuple(cases), deliveries=deliveries, assertions=tuple(assertions), escapes=escapes,
            timeline=tuple(sorted(marks, key=_when)), history=_scoped(bars, set(self._agents.subtree(owner))), files_error=files_error, watch=watch,
            contracts=facts.contracts,
        )

    def _one_off(self, mail: _Boxes, findings: Sequence[DeliverableFinding], files_error: str, bars: BarChanges) -> ServiceRecord:
        try:
            cases = _read("the cases", lambda: self._history.one_off_cases())
            deliveries = _attributed(_read("the mailboxes", lambda: tuple(d for c in cases for d in _deliveries_in(mail, ROOT, c))), findings)
            team = {addr for c in cases for addr in self._agents.subtree(c.owner)}
            marks: list[Mark] = [*top_up_marks(cases), *self._bar_marks(bars, team)]
            results = _read("the mailboxes", lambda: _results(mail, ROOT))
            escapes = self._escapes(deliveries, cases, [], None, results)
        except _Unreadable as unreadable:
            return ServiceRecord("", "", ROOT, "human", error=str(unreadable))
        return ServiceRecord(
            "", "", ROOT, "human", cases=tuple(cases), deliveries=deliveries, escapes=escapes, timeline=tuple(sorted(marks, key=_when)),
            history=_scoped(bars, team), files_error=files_error,
        )

    @staticmethod
    def _all(mail: _Boxes, client: str, cases: Sequence[Case]) -> tuple[Delivery, ...]:
        return tuple(d for c in cases for d in _deliveries_in(mail, client, c))

    @staticmethod
    def _bar_marks(bars: BarChanges, team: set[str]) -> list[Mark]:
        return list(_scoped(bars, team).marks)

    @staticmethod
    def _escapes(
        deliveries: Sequence[Delivery], cases: Sequence[Case], assertions: Sequence[Assertion], facts: _Versions | None, results: Mapping[str, Message],
    ) -> tuple[tuple[Delivery, Cause], ...]:
        """The escapes among ``deliveries``, each typed by ``cause_of``, the oldest decisive verdict first. ``facts`` are the stored contract versions
        (``None`` for a one-off case, which has no contract and names no criterion)."""
        by_case = {c.id: c for c in cases}
        by_verdict = {a.verdict.message.id: a for a in assertions}
        found = [(d, cause) for d in deliveries if (cause := _cause(d, by_case[d.case], by_verdict, facts, results)) is not None]
        return tuple(sorted(found, key=lambda pair: pair[0].decisive.message.id if pair[0].decisive else ""))

    # ---------------------------------------------------------------------------------------------------- deliveries

    def deliveries(self, owner: str) -> OwnerDeliveries:
        mail = _Boxes(self._mail, self._agents)
        client = parent(owner) or ROOT
        items: list[Delivery] = []
        causes: list[Cause | None] = []
        unknown: list[str] = []
        for name in self._catalog.service_names(owner):
            try:
                contract = _read("SERVICE.md", lambda: self._catalog.read_contract(owner, name))
                if contract is None:
                    continue
                facts: _Versions | None = _read(
                    "the stored contract versions", lambda: _versions_of(owner, name, self._versions.versions(owner, name, "SERVICE")),
                )
                cases = self._history.chains(owner, name, since=contract.created, runs=False)
                error = ""
            except _Unreadable as unreadable:  # the cases from the mailboxes alone; every escape is untyped (counted: no escape disappears)
                facts, error = None, str(unreadable)
                cases = self._history.chains(owner, name, since=None, runs=False)
                unknown.append(f"{name}: {error}")
            self._add(mail, client, cases, facts, error, items, causes)
        self._add(mail, ROOT, [c for c in self._history.one_off_cases(runs=False) if c.owner == owner], None, "", items, causes)
        return OwnerDeliveries(tuple(items), tuple(causes), "; ".join(unknown))

    @staticmethod
    def _add(
        mail: _Boxes, client: str, cases: Sequence[Case], facts: _Versions | None, error: str, items: list[Delivery], causes: list[Cause | None],
    ) -> None:
        """Append the deliveries of ``cases`` and their causes. ``facts`` are the stored contract versions; with an ``error`` (they could not be read)
        every escape is ``untyped`` and counted; with neither (a one-off case) no criterion is named."""
        by_case = {c.id: c for c in cases}
        by_verdict = {a.verdict.message.id: a for a in (regressions(cases) if facts is not None else [])}
        results = _results(mail, client)
        for d in (d for c in cases for d in _deliveries_in(mail, client, c)):
            items.append(d)
            if error:
                causes.append(Cause("untyped", "unreadable", (clip_line(error, _ERROR_CLIP),)) if d.escape else None)
            else:
                causes.append(_cause(d, by_case[d.case], by_verdict, facts, results))


def _scoped(bars: BarChanges, team: set[str]) -> BarChanges:
    """The changes of ``bars`` that belong to a record: the charters and models of its team, and ORG.md's."""
    if not bars.known:
        return bars
    marks = tuple(m for m in bars.marks if isinstance(m, (CharterMark, ModelMark)) and (m.addr in team or m.addr == ORG_MD))
    return replace(bars, marks=marks)
