"""The watch of the playbook's items (design 3 and 8): what the files say about each item, derived, never stored.

Pure: every function reads values (cases, results, contract versions, playbook versions), never a file. Its one caller is
``CaseServiceEvidence.watch``, so every reader of a watch state goes through one derivation path.

This part holds the facts the watch reads: the records as of a moment, the subjects of a rejection, the lineage of a criterion as of a time
(B3, B4), coverage and refs."""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone

from ..kernel import Message, link_ids, msg_time, verdict_tier
from ..services import Contract, Criterion, amendment_ids, number_criteria
from .api import Assertion, Case, Verdict, regressions

EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)
Moment = tuple[datetime, int, str]  # (when, rank, id): where a record sits among the records; a contract version (rank 0) comes before a message (rank 1)
_REF = re.compile(r"(?<![A-Za-z0-9])([CR]\d+)(?![0-9])", re.IGNORECASE)  # a C<k> or R<k> as a standalone token (``quoting_lines``' rule)


def when_of(m: Message) -> datetime:
    """When a message was created: the microsecond stamp of its id (``EPOCH`` when it says none). Aware."""
    return msg_time(m) or EPOCH


def moment_of(m: Message) -> Moment:
    """The place of a note or a result among the records: its creation time, then its id (ids never tie)."""
    return (when_of(m), 1, m.id)


def defined_moment(c: Contract) -> Moment:
    """The place of a contract version among the records (B3): its ``defined``, written once per version, never the contract's ``created``, which
    every version carries from v1. At an equal microsecond it comes before any message, the link note ``define_service`` writes after it."""
    return (c.defined or EPOCH, 0, "")


def before(when: datetime) -> Moment:
    """The moment just before the messages created at ``when``."""
    return (when, 0, "")


def number_of(item_id: str) -> int:
    """The number in ``P12``, ``R4``, ``C9`` (0 when there is none)."""
    return int(item_id[1:]) if item_id[1:].isdigit() else 0


def _human_links(v: Verdict, seen: Callable[[Moment], bool]) -> Verdict:
    """``v`` with only the human-tier link notes created by then, and the effective link they give (the latest one): relayed and agent links
    weigh nothing in the watch (0a's tiers)."""
    notes = tuple(sorted((m for m in v.link_notes if verdict_tier(m) == "human" and link_ids(m) and seen(moment_of(m))), key=lambda m: m.id))
    confirmed = tuple(dict.fromkeys(x for m in notes for x in link_ids(m) if x.startswith("C")))
    return replace(
        v, links=link_ids(notes[-1]) if notes else (), links_tier="human" if notes else "", confirmed=confirmed, link_notes=notes,
    )


@dataclass(frozen=True)
class Records:
    """The records of a service as the files stood at ``cutoff`` (all of them when None): the cases with the human links created by then, their
    assertions, the results, the contract versions. Build with :func:`records_of`, read an earlier moment with :func:`until`."""

    cases: list[Case]
    results: dict[str, tuple[Message, ...]]  # every result of every task by then, oldest first
    latest: dict[str, Message]  # the latest result of each task
    contracts: list[Contract]  # the stored contract versions by then, oldest first
    stored: list[tuple[int, str, list[str]]]  # ``(version, defined_by, acceptance)`` of each, as ``number_criteria`` takes them
    assertions: list[Assertion]
    by_id: dict[str, Assertion]
    cutoff: Moment | None = None
    source: tuple[Sequence[Case], Mapping[str, Sequence[Message]], Sequence[Contract]] = ((), {}, ())  # the unfiltered inputs, kept by the root
    views: dict[Moment, Records] = field(default_factory=dict)  # the root's cache of ``until``
    root: Records | None = None  # the records ``until`` started from (None for the root itself)


def records_of(
    cases: Sequence[Case], results: Mapping[str, Sequence[Message]], contracts: Sequence[Contract], cutoff: Moment | None = None,
    *, root: Records | None = None,
) -> Records:
    """The records of a service at ``cutoff`` (all of them when None). ``cases`` are the service's, from the mail alone; ``results`` every result
    of every task the client sent, by task id, oldest first; ``contracts`` every stored version of its contract."""

    def seen(m: Moment) -> bool:
        return cutoff is None or m <= cutoff

    kept = {task: tuple(r for r in found if seen(moment_of(r))) for task, found in results.items()}
    found = {task: rs for task, rs in kept.items() if rs}
    held = sorted((c for c in contracts if seen(defined_moment(c))), key=lambda c: c.version)
    visible = [replace(c, verdicts=[_human_links(v, seen) for v in c.verdicts if seen(moment_of(v.message))]) for c in cases]
    assertions = regressions(visible)
    return Records(
        visible, found, {task: rs[-1] for task, rs in found.items()}, held, [(c.version, c.defined_by or "", c.acceptance) for c in held],
        assertions, {a.id: a for a in assertions}, cutoff, (cases, results, contracts) if root is None else ((), {}, ()), {}, root,
    )


def until(records: Records, moment: Moment) -> Records:
    """These records as they stood at ``moment`` (inclusive)."""
    base = records.root or records
    if moment not in base.views:
        cases, results, contracts = base.source
        base.views[moment] = records_of(cases, results, contracts, moment, root=base)
    return base.views[moment]


def human_notes(a: Assertion) -> tuple[Message, ...]:
    """The user's link notes on the rejection ``a`` by then, oldest first; the last one is its effective link."""
    return a.verdict.link_notes


def answering(records: Records, a: Assertion) -> Contract | None:
    """The first stored contract version that answers the rejection ``a`` (``answers`` is its note id), None when there is none."""
    return next((c for c in records.contracts if c.answers == a.verdict.message.id), None)


def rejected_result(records: Records, a: Assertion) -> Message | None:
    """The result the rejection ``a`` was given on: its task's latest result, done or blocked, created before the rejection note."""
    found = [r for r in records.results.get(a.verdict.task_id, ()) if r.status in ("done", "blocked") and r.id < a.verdict.message.id]
    return found[-1] if found else None


def pending_rejection(records: Records, rejection: str, _seen: frozenset[str] = frozenset()) -> bool:
    """Is the rejection ``R<k>`` without an answer (section 3)? It has no human link and no answering version, or its human link names an
    earlier rejection that is itself pending ("same as R<j>": its subjects are not known until R<j> is answered)."""
    a = records.by_id[rejection]
    notes = human_notes(a)
    if not notes:
        return answering(records, a) is None
    named = [x for x in link_ids(notes[-1]) if x in records.by_id and x != rejection and x not in _seen]
    return any(pending_rejection(records, x, _seen | {rejection}) for x in named)


def answer_time(records: Records, a: Assertion) -> datetime:
    """When the rejection ``a`` was answered (B4): the earlier of its first human link and its answering version's ``defined``; for a corrected
    link (a second human link), the time of the link that is effective. ``EPOCH`` for a rejection with no answer."""
    notes = human_notes(a)
    if len(notes) > 1:
        return when_of(notes[-1])
    answer = answering(records, a)
    times = [when_of(notes[0])] if notes else []
    if answer is not None:
        times.append(answer.defined or EPOCH)
    return min(times, default=EPOCH)


def lineage_as_of(contracts: Sequence[Contract], criterion: str, when: datetime) -> tuple[str, ...]:
    """The criteria ``criterion`` replaced, as the contract stood at ``when`` (B4), oldest id first: those removed by the latest stored version
    defined at or before ``when`` that added its text (present in it, absent from the version before it), and their lineage as of ``when`` in turn,
    each id once (a cycle ends). A criterion no such version added (a v1 criterion never removed and re-added), or one a user-initiated change
    added, has none."""
    ordered = sorted(contracts, key=lambda c: c.version)
    stored = [(c.version, c.defined_by or "", c.acceptance) for c in ordered]
    text_of = {c.id: c.text for c in number_criteria(stored)}

    def replaced(cid: str) -> tuple[str, ...]:
        text = text_of.get(cid)
        adding = None
        for index, c in enumerate(ordered):
            if index and (c.defined or EPOCH) <= when and text in c.acceptance and text not in ordered[index - 1].acceptance:
                adding = c
        if adding is None or adding.initiated == "user":
            return ()
        return amendment_ids(stored, adding.version)[1]

    found: list[str] = []
    todo = [criterion]
    while todo:
        for cid in replaced(todo.pop(0)):
            if cid != criterion and cid not in found:
                found.append(cid)
                todo.append(cid)
    return tuple(sorted(found, key=number_of))


def subjects_of(records: Records, rejection: str) -> frozenset[str]:
    """What the rejection ``R<k>`` is about (section 3): itself; the ids its effective human link names (the criteria and the earlier rejections
    it resolves through); the question's id of its answering contract version, the ids that version adds (or, adding none, removes: what the link
    names or would name, so a failed link write changes nothing) and the ids it removes; and the lineage as of the time of its answer of every
    criterion among them (B4). A pending rejection is only itself."""
    if pending_rejection(records, rejection):
        return frozenset({rejection})
    a = records.by_id[rejection]
    notes = human_notes(a)
    found = {rejection, *a.about}
    if notes:
        found |= {x for x in link_ids(notes[-1]) if x != "none"}
    answer = answering(records, a)
    if answer is not None:
        added, removed = amendment_ids(records.stored, answer.version)
        found |= {*([answer.about] if answer.about else []), *(added or removed), *removed}
    when = answer_time(records, a)
    for cid in [x for x in found if x.startswith("C")]:
        found |= set(lineage_as_of(records.contracts, cid, when))
    return frozenset(found)


def coverage_of(refs: Iterable[str], criteria: Sequence[Criterion], assertions: Sequence[Assertion]) -> tuple[str, ...]:
    """Of an item's ``refs`` (section 3): the current criteria among them, and the assertions among them that the user confirmed and that are about
    a current criterion or about no criterion at all. A removed criterion is no coverage; neither is an assertion marked "no lasting rule", nor one
    only about removed criteria: the client lowered that bar herself. ``R`` ids first, each by number."""
    current = {c.id for c in criteria if c.current}
    by_id = {a.id: a for a in assertions}
    covered: set[str] = set()
    for x in refs:
        if x in current:
            covered.add(x)
        elif x in by_id and by_id[x].link == "confirmed":
            named = [c for c in by_id[x].about if c.startswith("C")]
            if not named or any(c in current for c in named):
                covered.add(x)
    return tuple(sorted(covered, key=lambda x: (x[0] != "R", number_of(x), x)))


def refs_of(records: Records, text: str, why: Sequence[str], live_from: datetime) -> frozenset[str]:
    """The refs of an item text (section 3): its ``why`` entry (a gated item), else the ``C<k>`` and ``R<k>`` tokens of its words; plus, for every
    ``R<k>`` among them, the criteria that assertion was about when the text went live (its links created before ``live_from``), so the refs of a
    text never change."""
    found = {x.upper() for x in why} if why else {m.upper() for m in _REF.findall(text)}
    asof = until(records, before(live_from))
    for x in [x for x in found if x.startswith("R")]:
        a = asof.by_id.get(x)
        if a is not None:
            found |= {c for c in a.about if c.startswith("C")}
    return frozenset(found)
