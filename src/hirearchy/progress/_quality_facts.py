"""What the quality view shows of a record, as values (0b 4, 9.2): the first deliveries, the delivery counts, the escapes with their causes and the
verifiers. The text and the JSON of the view are both made from these, so the two cannot disagree. Pure: nothing here reads a file."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from ..kernel import Message
from ..reflection import (
    Case, Cause, Delivery, QualityThresholds, ServiceRecord, attribution, not_on_a_delivery, unjudged_cases, user_approved,
)

COUNTED_CAUSES = ("reviewer-miss", "untyped")  # the verifier's possible misses (``attribution`` says ``counted``), in the view's order
NOT_ITS_CAUSES = ("contract-gap", "relayed-error", "relayed-carry-over")  # ``not its``, in the view's order


@dataclass(frozen=True)
class RecordView:
    """A record with what the view adds to it: which open cases are stalled now (``stalled_error`` when that could not be read), the ids of the latest
    tasks of its cases that are left blocked, and each signer's FAIL counts (``(re-checks, author rework runs)``, or the error that stopped them)."""

    record: ServiceRecord
    stalled: Mapping[str, bool] = field(default_factory=dict)
    stalled_error: str = ""
    left_blocked: frozenset[str] = frozenset()
    fails: Mapping[str, tuple[int, int]] = field(default_factory=dict)
    fails_errors: Mapping[str, str] = field(default_factory=dict)


def approved_of(record: ServiceRecord, case: Case) -> int:
    """The runs the user approved for ``case`` (``user_approved``): the contract's budget for a service, the head task's own for a one-off case."""
    return user_approved(case, record.budget if record.service else case.tasks[0].budget)


@dataclass(frozen=True)
class FirstLine:
    """The first delivery of a case (4.3: its delivery with the lowest step) and how it stands: ``outcome`` is ``accepted``, ``rejected``, ``neither``
    (judged after the file changed), ``none`` (no verdict) or ``never`` (no task of the case was delivered). ``superseded`` is the task that took
    the place of an undelivered-verdict delivery."""

    case: Case
    delivery: Delivery | None
    outcome: str
    superseded: Message | None = None


def first_lines(record: ServiceRecord) -> tuple[FirstLine, ...]:
    """The first delivery of every case of ``record``, in the order of its cases (pure; PC-6: the lowest step wins, not the first one listed)."""
    out = []
    for case in record.cases:
        mine = [d for d in record.deliveries if d.case == case.id]
        first = min(mine, key=lambda d: d.step) if mine else None
        if first is None:
            out.append(FirstLine(case, None, "never"))
            continue
        later = next((t for t in case.tasks if t.id == first.superseded), None) if first.superseded else None
        out.append(FirstLine(case, first, first.outcome, later))
    return tuple(out)


@dataclass(frozen=True)
class DeliveryFacts:
    """The counts of a record's deliveries (4.3): how many, how many judged, the cases without a verdict (and those with only a relayed or agent verdict,
    and those with a later relayed delivery the user was not given), the deliveries not as delivered or judged after the file changed, the legacy
    verdicts and the verdicts that are on no delivery."""

    total: int = 0
    judged: int = 0
    unjudged: tuple[str, ...] = ()
    relayed_only: tuple[str, ...] = ()
    unseen_relayed: tuple[str, ...] = ()
    not_as_delivered: tuple[Delivery, ...] = ()
    neither: tuple[Delivery, ...] = ()
    legacy: int = 0
    not_on_a_delivery: tuple[str, ...] = ()


def delivery_facts(record: ServiceRecord) -> DeliveryFacts:
    ds = record.deliveries
    unseen = []
    for case in record.cases:
        given = next((d for d in ds if d.case == case.id and d.given), None)
        if given is not None and any(d.case == case.id and d.step > given.step and d.task.source == "relayed" for d in ds):
            unseen.append(case.id)
    return DeliveryFacts(
        total=len(ds), judged=sum(1 for d in ds if d.judged), unjudged=unjudged_cases(record.cases, ds),
        relayed_only=unjudged_cases(record.cases, ds, relayed_only=True), unseen_relayed=tuple(unseen),
        not_as_delivered=tuple(d for d in ds if d.edited), neither=tuple(d for d in ds if d.outcome == "neither"),
        legacy=sum(1 for c in record.cases for v in c.verdicts if v.tier == "human" and v.message.source is None),
        not_on_a_delivery=tuple(m.id for c in record.cases for m in not_on_a_delivery(c, ds)),
    )


@dataclass(frozen=True)
class EscapeRow:
    """An escape: ``assertion`` is its ``R<k>`` ("" in the one-off record, where a rejection is no ``R<k>``)."""

    assertion: str
    case: Case
    delivery: Delivery
    cause: Cause


def escape_rows(record: ServiceRecord) -> tuple[EscapeRow, ...]:
    by_verdict = {a.verdict.message.id: a.id for a in record.assertions}
    by_case = {c.id: c for c in record.cases}
    return tuple(
        EscapeRow(by_verdict.get(d.decisive.message.id, "") if d.decisive is not None else "", by_case[d.case], d, cause) for d, cause in record.escapes
    )


@dataclass(frozen=True)
class VerifierFacts:
    """A signer other than the owner: its judged deliveries and its escapes, ``counted`` (its possible misses) and ``not its``, each by cause."""

    addr: str
    judged: int
    counted: tuple[tuple[str, int], ...] = ()
    not_its: tuple[tuple[str, int], ...] = ()

    @property
    def escapes(self) -> int:
        return sum(n for _, n in self.counted)


def verifiers(record: ServiceRecord) -> tuple[VerifierFacts, ...]:
    """The signers other than the owner of their case, by address (pure; 4.4)."""
    owner_of = {c.id: c.owner for c in record.cases}
    signers = sorted({d.signer for d in record.deliveries if d.signer != owner_of.get(d.case)})
    out = []
    for addr in signers:
        causes = [cause for d, cause in record.escapes if d.signer == addr]
        counted = [c.type for c in causes if attribution(c) == "counted"]
        not_its = [c.type for c in causes if attribution(c) == "not its"]
        out.append(VerifierFacts(
            addr, sum(1 for d in record.deliveries if d.signer == addr and d.judged),
            tuple((k, counted.count(k)) for k in COUNTED_CAUSES if k in counted), tuple((k, not_its.count(k)) for k in NOT_ITS_CAUSES if k in not_its),
        ))
    return tuple(out)



@dataclass(frozen=True)
class HeldTask:
    """A task whose blocked result still holds runs on its assignee (``task``), with that result (``blocked``) and the number of tasks its sender has
    sent the assignee since, outside the chain (``sent_since``): above 0 it is left blocked, the sender moved past it without a verdict."""

    task: Message
    blocked: Message
    sent_since: int = 0

    @property
    def left_blocked(self) -> bool:
        return self.sent_since > 0


@dataclass(frozen=True)
class MovedPast:
    """An agent of the moved-past section (4.5): the runs it holds (``held``; ``held_error`` says why that is unknown), its held tasks, or ``error``
    when its mailbox could not be read."""

    addr: str
    held: int | None
    held_error: str = ""
    error: str = ""
    tasks: tuple[HeldTask, ...] = ()


@dataclass(frozen=True)
class QualityView:
    """Everything the text and the JSON of the quality view are made of: the thresholds in force with the notes about them, the records in the view's
    order (top-level services, nested ones, then root's one-off tasks), the moved-past section, and the ``service`` asked for (``None``: everything)."""

    thresholds: QualityThresholds
    notes: tuple[str, ...]
    records: tuple[RecordView, ...]
    moved_past: tuple[MovedPast, ...] = ()
    service: str | None = None
