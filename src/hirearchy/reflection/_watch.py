"""The watch of the playbook's items (design 3 and 8): what the files say about each item, derived, never stored.

Pure: every function reads values (cases, results, contract versions, playbook versions), never a file. Its one caller is
``CaseServiceEvidence.watch``, so every reader of a watch state goes through one derivation path.

The facts it reads come first: the records as of a moment, the subjects of a rejection, the lineage of a criterion as of a time (B3, B4),
coverage and refs. Then the items' texts over time, the candidate cases and the window of a watched change, and ``watch_states``."""

from __future__ import annotations

import math
import re
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from fractions import Fraction
from datetime import datetime, timezone

from ..kernel import Message, link_ids, msg_time, verdict_tier
from ..services import (
    Contract, Criterion, ItemWatch, Playbook, PlaybookItem, amendment_ids, line_key, migrate_body, number_criteria, text_tokens,
)
from ._quality_rules import deliveries_of
from .api import Assertion, Case, Delivery, Verdict, regressions

K_DEFAULT = 3  # the clean cases a watch needs unless the failure's recurrence rate is known (8.4)

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


def answered_at(notes: Sequence[Message], contracts: Sequence[Contract], rejection: str) -> datetime:
    """When a rejection was answered (B4): the earlier of its first human link (``notes``, oldest first) and the ``defined`` of the first contract
    version whose ``answers`` is the rejection's note id ``rejection``; for a corrected link (a second human link), the time of the link that is
    effective. ``EPOCH`` for a rejection with no answer."""
    if len(notes) > 1:
        return when_of(notes[-1])
    answer = next((c for c in contracts if c.answers == rejection), None)
    times = [when_of(notes[0])] if notes else []
    if answer is not None:
        times.append(answer.defined or EPOCH)
    return min(times, default=EPOCH)


def answer_time(records: Records, a: Assertion) -> datetime:
    """When the rejection ``a`` was answered (B4): ``answered_at`` over its human link notes and the stored versions."""
    return answered_at(human_notes(a), records.contracts, a.verdict.message.id)


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


def lineage_class(contracts: Sequence[Contract], criterion: str, when: datetime) -> frozenset[str]:
    """The lineage class of ``criterion`` as of ``when`` (design 3, 10.5): the criterion and its lineage as of ``when``. Two rejections fail "the same
    criterion" when the classes of their subjects meet."""
    return frozenset({criterion, *lineage_as_of(contracts, criterion, when)})


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


# ----------------------------------------------------------------------------------------------------------------- the texts of an item over time

_Tokens = tuple[tuple[str, ...], tuple[str, ...]]  # the text tokens of an item's text and, for a rule, of its condition


@dataclass
class _Seg:
    """One text of an item, live from the version that gave it to the next change of it (its ``end``; None while it is live)."""

    item: str
    version: int
    start: datetime
    end: datetime | None
    kind: str
    text: str
    when: str
    why: tuple[str, ...]
    refs: frozenset[str]
    tokens: _Tokens


@dataclass
class _Change:
    """A watched change (section 3): the change that put a text on trial, live from ``at``. The cases of its ``why`` assertions are no candidates;
    the item is "live in the watched text" while its text has ``tokens`` (W1)."""

    version: int
    at: datetime
    excluded: frozenset[str]
    tokens: _Tokens


@dataclass
class _Watch:
    """A watch (section 8.1): the changes that put texts of an item on trial (a restart adds one: W2), the texts the item had meanwhile, and the
    watches it continues (a carried watch: their related rejections count as they are). ``ended``: the item left the body, or the runtime's retire
    brought its previous text back (W3)."""

    start: datetime
    changes: list[_Change]
    segs: list[_Seg]
    inherited: list[_Watch] = field(default_factory=list)
    carried: str = ""
    ended: bool = False
    k: int = K_DEFAULT
    r: tuple[int, int] = (0, 0)


@dataclass
class _Track:
    """What the versions say of one item: its texts over time, whether it is live, the watch it is on trial in (None: never watched, or the watch is
    over and its text is another), the version whose text the runtime's retire brought back (0: none) and the watches its retires ended (``ended``)."""

    id: str
    kind: str
    segs: list[_Seg]
    live: bool = True
    watch: _Watch | None = None
    restored: int = 0
    ended: list[tuple[int, _Watch]] = field(default_factory=list)  # the retires 8.6 keeps out: (version, the watch it ended), whatever the item does next


@dataclass(frozen=True)
class _Retired:
    """A text its owner retired while it was in ``warning``: what a restore, an add or a gated edit of the same words continues (carried watch (i))."""

    item: str
    key: str
    watch: _Watch


@dataclass
class _Tracking:
    """The versions read so far: every item's track, the items live in the last version that parsed, and the retired warned texts."""

    rec: Records
    tracks: dict[str, _Track]
    live: dict[str, PlaybookItem]
    retired: list[_Retired]


def _tokens_of(item: PlaybookItem) -> _Tokens:
    """The text tokens of an item (section 3): two texts with equal tokens differ only in spacing, case, markdown and sentence punctuation."""
    return tuple(text_tokens(item.text)), tuple(text_tokens(item.when)) if item.kind == "rule" else ()


def _words_of(item: PlaybookItem) -> str:
    """The words refs are read from: a step's text, a rule's condition and action."""
    return item.text if item.kind == "step" or item.when in ("", "always") else f"{item.when} {item.text}"


def _line_key(item: PlaybookItem) -> str:
    """The text key of the line an item renders (4.4), without its list marker: what a repair migration keeps as the words of a step."""
    why = ", ".join(item.why)
    if item.kind == "rule":
        return line_key(f"[{item.id}] WHEN {item.when} THEN {item.text}" + (f" WHY {why}" if why else ""))
    return line_key(f"[{item.id}] {item.text}" + (f" (WHY {why})" if why else ""))


def _same(a: PlaybookItem, b: PlaybookItem) -> bool:
    """Is ``b`` the item ``a``, word for word? Its place in the body is not part of it (a move changes none)."""
    return (a.kind, a.text, a.when, a.why) == (b.kind, b.text, b.when, b.why)


def _seg_at(segs: Sequence[_Seg], when: datetime) -> _Seg | None:
    """The text that was live at ``when``, None when none was."""
    return next((s for s in segs if s.start <= when and (s.end is None or when < s.end)), None)


# ----------------------------------------------------------------------------------------------------------------- candidates and the window


@dataclass(frozen=True)
class _Candidate:
    """A candidate case of a watched change (section 3): the deliveries of the case made after the change's live-from, and the first of them."""

    case: Case
    deliveries: tuple[Delivery, ...]
    first: Message  # the first such done result: candidates are ordered by it


def _candidates(rec: Records, change: _Change) -> list[_Candidate]:
    """The candidate cases of ``change``, in the order of their first delivery after its live-from. A case of the change's ``why`` is none."""
    found = []
    for case in rec.cases:
        if case.id in change.excluded:
            continue
        made = tuple(d for d in deliveries_of(case, rec.latest, {}) if when_of(d.result) > change.at)
        if made:
            found.append(_Candidate(case, made, min((d.result for d in made), key=lambda r: r.id)))
    return sorted(found, key=lambda c: c.first.id)


def _judging(candidate: _Candidate) -> tuple[Verdict, Delivery] | None:
    """``judged(c)``: the delivery of the candidate that carries its first counted verdict (the human-tier verdict with the lowest note id among
    those on its deliveries after the live-from), with that verdict. A delivery superseded with no verdict holds nothing."""
    best: tuple[Verdict, Delivery] | None = None
    for d in candidate.deliveries:
        for v in d.counted:
            if best is None or v.message.id < best[0].message.id:
                best = (v, d)
    return best


@dataclass(frozen=True)
class _Window:
    """The first k candidates of a watched change, their judged deliveries and the window over them (section 3): the rejections in it, each with
    the result it was given on. ``closed``: ``E`` is defined, each of the first k candidates has its judged delivery."""

    first: list[_Candidate]
    judged: list[tuple[Verdict, Delivery] | None]
    closed: bool
    judging: Message | None  # the verdict note that closes the window: the latest judging verdict of the first k candidates (``D``)
    members: list[tuple[Assertion, Message]]


def _window(rec: Records, change: _Change, k: int, upto: Moment | None = None) -> _Window:
    """The window of ``change`` over ``rec`` (section 3): a human rejection on a result created at or after the live-from that was created at or
    before ``E`` or recorded before ``D`` (every one while ``E`` is undefined); with ``upto`` (``K``), only those recorded at or before it."""
    first = _candidates(rec, change)[:k]
    judged = [_judging(c) for c in first]
    done = [j for j in judged if j is not None]
    closed = len(first) == k and len(done) == k
    e = max(when_of(d.result) for _, d in done) if closed else None
    judging = max((v.message for v, _ in done), key=lambda m: m.id) if closed else None
    members: list[tuple[Assertion, Message]] = []
    for a in rec.assertions:
        if upto is not None and moment_of(a.verdict.message) > upto:
            continue
        result = rejected_result(rec, a)
        if result is None or when_of(result) < change.at:
            continue
        if e is None or judging is None or when_of(result) <= e or a.verdict.message.id < judging.id:
            members.append((a, result))
    return _Window(first, judged, closed, judging, members)


def _relations(rec: Records, segs: Sequence[_Seg], members: Sequence[tuple[Assertion, Message]]) -> tuple[list[Assertion], list[Assertion]]:
    """Of rejections with the result each was given on: those related to the item (not pending, given on a result created while a text of it was
    live, and their subjects meet that text's refs) and those pending (no answer yet)."""
    pending = [a for a, _ in members if pending_rejection(rec, a.id)]
    held = {a.id for a in pending}
    related = []
    for a, result in members:
        seg = _seg_at(segs, when_of(result))
        if a.id not in held and seg is not None and subjects_of(rec, a.id) & seg.refs:
            related.append(a)
    return related, pending


def _records(rec: Records) -> list[Moment]:
    """The places of the records that can change what the files derive: every verdict note, every human link note and every answering contract version."""
    found = {moment_of(v.message) for c in rec.cases for v in c.verdicts}
    found |= {moment_of(n) for c in rec.cases for v in c.verdicts for n in v.link_notes}
    found |= {defined_moment(c) for c in rec.contracts if c.answers}
    return sorted(found)


def _union(windows: Sequence[_Window]) -> list[tuple[Assertion, Message]]:
    """The rejections of several windows, each once (a restarted or carried watch reads the union of its changes' windows)."""
    found: dict[str, tuple[Assertion, Message]] = {}
    for window in windows:
        for a, result in window.members:
            found.setdefault(a.id, (a, result))
    return list(found.values())


def _watch_end(rec: Records, w: _Watch) -> Moment | None:
    """``K``, the end of the watch (section 3): the earliest record at or after ``D`` such that the files created up to and including it derive ``kept``
    (``E`` defined, every rejection in the window answered and unrelated, no related rejection carried). None while it has not reached ``kept``."""
    judging = _window(rec, w.changes[-1], w.k).judging
    if judging is None:
        return None
    for place in _records(rec):
        if place < moment_of(judging):
            continue
        view = until(rec, place)
        windows = [_window(view, c, w.k) for c in w.changes]
        related, pending = _relations(view, w.segs, _union(windows))
        if windows[-1].closed and not related and not pending and not any(_derive_watch(view, i).related for i in w.inherited):
            return place
    return None


@dataclass(frozen=True)
class _Derived:
    """What one watch derives: its related and pending rejections, the counts over the first k candidates of its latest change, whether it reached ``kept``."""

    related: tuple[str, ...]
    pending: tuple[str, ...]
    clean: int
    waiting: int
    kept: bool


def _warned_window(rec: Records, w: _Watch, known: set[str]) -> list[tuple[Assertion, Message]]:
    """The warned window of a watch (B1): every human rejection on a result created at or after the live-from of one of its changes, recorded while
    the item was live in that change's watched text, whatever ``E``, ``D`` and ``K`` are. Those in the window already (``known``) are left out."""
    found = []
    for a in rec.assertions:
        result = rejected_result(rec, a)
        if a.id in known or result is None:
            continue
        seg = _seg_at(w.segs, when_of(a.verdict.message))
        if seg is not None and any(when_of(result) >= c.at and seg.tokens == c.tokens for c in w.changes):
            found.append((a, result))
    return found


def _derive_watch(rec: Records, w: _Watch) -> _Derived:
    """The counts of a watch over ``rec``: ``K``, the union of its changes' windows closed at it, related and pending rejections, the related ones of
    the watches it continues, and, once it has a related rejection, the warned window in which a second retires it whatever the order of the records."""
    end = _watch_end(rec, w)
    windows = [_window(rec, c, w.k, end) for c in w.changes]
    members = _union(windows)
    related, pending = _relations(rec, w.segs, members)
    ids = {a.id for a in related} | {x for i in w.inherited for x in _derive_watch(rec, i).related}
    if ids:
        ids |= {a.id for a in _relations(rec, w.segs, _warned_window(rec, w, {a.id for a, _ in members}))[0]}
    unclean = {rec.by_id[x].case for x in ids} | {a.case for a in pending}
    latest = windows[-1]
    return _Derived(
        tuple(sorted(ids, key=number_of)), tuple(sorted((a.id for a in pending), key=number_of)),
        sum(1 for c, j in zip(latest.first, latest.judged) if j is not None and c.case.id not in unclean),
        sum(1 for j in latest.judged if j is None), end is not None,
    )


# ----------------------------------------------------------------------------------------------------------------- changes during a watch (W1-W3)


def _status(tr: _Tracking, w: _Watch, at: datetime) -> str:
    """The state of the watch ``w`` just before ``at`` (``new``, ``warning`` or ``kept``): what the files created before ``at`` derive."""
    found = _derive_watch(until(tr.rec, before(at)), w)
    return "warning" if found.related else "kept" if found.kept else "new"


def _new_seg(tr: _Tracking, item: PlaybookItem, version: int, at: datetime) -> _Seg:
    return _Seg(
        item.id, version, at, None, item.kind, item.text, item.when, item.why, refs_of(tr.rec, _words_of(item), item.why, at), _tokens_of(item),
    )


def _change_of(tr: _Tracking, item: PlaybookItem, v: Playbook, at: datetime, seg: _Seg) -> _Change:
    return _Change(v.version, at, frozenset(tr.rec.by_id[x].case for x in item.why if x in tr.rec.by_id), seg.tokens)


def _carry(tr: _Tracking, item: PlaybookItem, v: Playbook, before_item: PlaybookItem | None, gated: bool) -> _Retired | None:
    """The retired warned watch an owner's restore, add or gated edit continues (carried watch (i), B2): a restore of the item its owner retired
    in ``warning``; an add, a gated edit (of any live item) or a gated restore whose text key equals that of such a retired text. The latest wins."""
    key = line_key(item.text)
    if v.op == "restore" and before_item is None:
        found = [r for r in tr.retired if r.item == item.id]
        if found:
            return found[-1]
    if gated and v.op in ("add", "edit", "restore") and key:
        found = [r for r in tr.retired if r.key == key]
        return found[-1] if found else None
    return None


def watch_k(failed: int, judged: int) -> int:
    """The clean cases a watch needs (8.4): 3, unless the recurrence rate ``r = failed / judged`` is known (at least 10 judged cases and 1 failure);
    then ``max(3, ceil(ln 0.1 / ln(1 - r)))``, exactly (r = 0.5 gives 4, 0.3 gives 7, 0.2 gives 11, 0.1 gives 22). Never capped; r = 1 gives 3."""
    if judged < 10 or failed < 1 or failed >= judged:
        return K_DEFAULT
    left = Fraction(judged - failed, judged)
    n = max(1, math.ceil(math.log(0.1) / math.log(float(left))))
    while left ** (n - 1) <= Fraction(1, 10) and n > 1:  # the least n with (1 - r) ** n <= 0.1, whatever the rounding of the logarithms
        n -= 1
    while left**n > Fraction(1, 10):
        n += 1
    return max(K_DEFAULT, n)


def _rate(rec: Records, refs: frozenset[str], start: datetime) -> tuple[int, int]:
    """``r`` (8.4) as the files stood at the watch start: ``(judged cases with a human rejection whose subjects meet the refs, judged cases)``, over the
    cases with a result created before it and the verdicts, link notes and answering versions ``defined`` before it."""
    view = until(rec, before(start))
    judged = {c.id for c in view.cases if any(d.judged for d in deliveries_of(c, view.latest, {}))}
    failed = {a.case for a in view.assertions if a.case in judged and subjects_of(view, a.id) & refs}
    return len(failed), len(judged)


def _begin(tr: _Tracking, track: _Track, change: _Change, seg: _Seg, carry: _Retired | None) -> None:
    """A new watch of ``track`` starting at ``change``; it continues the watch of ``carry`` (same start, k, r and its related rejections counted)."""
    start = min(change.at, carry.watch.start) if carry is not None else change.at
    r = carry.watch.r if carry is not None else _rate(tr.rec, seg.refs, change.at)
    track.watch = _Watch(
        start, [change], [seg], [carry.watch] if carry is not None else [], carry.item if carry is not None else "",
        k=carry.watch.k if carry is not None else watch_k(*r), r=r,
    )
    track.restored = 0


def _restart(w: _Watch, change: _Change, seg: _Seg, carry: _Retired | None) -> None:
    """W2: the watch ``w`` goes on with a new watched change; its related rejections found so far stay, and a carried watch joins it (B2)."""
    w.changes.append(change)
    w.segs.append(seg)
    if carry is not None:
        w.inherited.append(carry.watch)
        w.carried = carry.item
        w.start = min(w.start, carry.watch.start)


def _repaired(tr: _Tracking, item: PlaybookItem, at: datetime, version: int, sources: Sequence[tuple[PlaybookItem, _Watch]]) -> bool:
    """Carried watch (ii): an item of a repair migration whose text key equals that of the line of an item that was in its watch continues that
    watch (same start, k, refs and related rejections), and its repaired text becomes the watched text (W1). True when it did."""
    key = line_key(item.text)
    for old, w in sources:
        if key and key == _line_key(old):
            seg = _new_seg(tr, item, version, at)
            changes = [replace(c) for c in w.changes]
            changes[-1].tokens = seg.tokens
            track = tr.tracks.setdefault(item.id, _Track(item.id, item.kind, []))
            track.segs.append(seg)
            track.watch = _Watch(w.start, changes, [*w.segs, seg], list(w.inherited), old.id, k=w.k, r=w.r)
            return True
    return False


def _due(tr: _Tracking, w: _Watch, at: datetime) -> bool:
    """Was the runtime's retire of the watch ``w`` due just before ``at`` (two related rejections by the files created before it)?"""
    return len(_derive_watch(until(tr.rec, before(at)), w).related) >= 2


def _gone(tr: _Tracking, track: _Track, v: Playbook, at: datetime) -> None:
    """The item left the body: an owner's retire (a warned text is remembered: carried watch (i)), the runtime's retire, a repair or a hand edit."""
    track.live = False
    track.segs[-1].end = at
    w = track.watch
    if w is not None and v.item == track.id and (v.op == "watch" or (v.op == "retire" and not w.ended and _due(tr, w, at))):
        track.ended.append((v.version, w))
    if w is None or w.ended:
        return
    if v.op == "retire" and v.item == track.id and _status(tr, w, at) == "warning":
        tr.retired.append(_Retired(track.id, line_key(track.segs[-1].text), w))
    w.ended = True


def _changed(tr: _Tracking, v: Playbook, at: datetime, item: PlaybookItem, previous: PlaybookItem | None) -> None:
    """The item appears in version ``v`` or has another text: classify the change (sections 3 and 8.1) and update its watch."""
    track = tr.tracks.setdefault(item.id, _Track(item.id, item.kind, []))
    seg = _new_seg(tr, item, v.version, at)
    if previous is not None and track.segs:
        track.segs[-1].end = at
    track.segs.append(seg)
    track.live = True
    track.kind = item.kind
    target = v.item == item.id
    gated = v.admitted in ("b", "c") and target
    exempt_restore = v.op == "restore" and v.admitted == "restore" and target
    w = track.watch
    active = w is not None and not w.ended
    if v.op == "watch" and target and previous is not None:  # W3: the runtime's retire brought a previous text back
        if w is not None:
            w.ended = True
            track.ended.append((v.version, w))
        track.restored = max(v.restores, 1)
        return
    carry = _carry(tr, item, v, previous, gated) if target else None
    if gated or exempt_restore:
        in_watch = w is not None and active and _status(tr, w, at) in ("new", "warning")
        if gated or in_watch or carry is not None:  # an exempt restore outside a watch, and carrying none, changes nothing
            change = _change_of(tr, item, v, at, seg)
            if in_watch and w is not None:
                _restart(w, change, seg, carry)  # W2: a gated change, or an exempt restore, in the watch
            else:
                _begin(tr, track, change, seg, carry)
            return
    if previous is None:  # appears outside a watch: the first version, a migration, a restore of a client-written text
        track.watch = None
        track.restored = 0
        return
    if w is not None and active:  # W1: a move, a formatting edit, a hand edit: the watch goes on
        w.segs.append(seg)


def _tracks(versions: Sequence[Playbook], rec: Records) -> dict[str, _Track]:
    """The texts and watches of every item, version by version (oldest first; ``versions`` all parse)."""
    tr = _Tracking(rec, {}, {}, [])
    for v in versions:
        at = v.revised or EPOCH
        now = {i.id: i for i in v.items or ()}
        previous = tr.live
        sources: list[tuple[PlaybookItem, _Watch]] = []
        if v.op == "migrate" and previous:  # a repair migration: the watches of its items carry by text key
            for old in previous.values():
                w = tr.tracks[old.id].watch
                if w is not None and not w.ended and _status(tr, w, at) in ("new", "warning"):
                    sources.append((old, w))
        for gone in [x for x in previous if x not in now]:
            _gone(tr, tr.tracks[gone], v, at)
        for item in now.values():
            before_item = previous.get(item.id)
            if before_item is not None and _same(before_item, item):
                continue
            if before_item is None and sources and _repaired(tr, item, at, v.version, sources):
                continue
            _changed(tr, v, at, item, before_item)
        tr.live = now
    return tr.tracks


def _virtual(versions: Sequence[Playbook]) -> tuple[ItemWatch, ...]:
    """A legacy playbook has no items yet: it reads as it would migrate (4.4), every item ``kept`` (it predates the watch)."""
    last = versions[-1] if versions else None
    if last is None or last.items is not None or last.parse_error or not last.body.strip():
        return ()
    return tuple(ItemWatch(i.id, i.kind, "kept", last.version) for i in migrate_body(last.body).items)


def _retires(rec: Records, track: _Track, known: tuple[_Watch, _Derived] | None = None) -> tuple[tuple[int, tuple[str, ...]], ...]:
    """``ItemWatch.retires`` of an item: for each retire its watch ended, the rejections still related to that watch over the files as they stand
    (design 8.6; ``known``: the current watch and what it derives, not derived twice)."""
    return tuple(
        (version, (known[1] if known is not None and known[0] is w else _derive_watch(rec, w)).related) for version, w in track.ended
    )


def watch_states(
    versions: Sequence[Playbook], cases: Sequence[Case], results: Mapping[str, Sequence[Message]], criteria: Sequence[Criterion],
    contract_versions: Sequence[Contract],
) -> tuple[ItemWatch, ...]:
    """The watch of every playbook item, derived (design 8.1; pure). ``versions`` are every stored playbook version, oldest first; ``cases`` the
    service's, from the mail alone; ``results`` every result of every task the client sent, by task id, oldest first; ``criteria`` the contract's;
    ``contract_versions`` every stored version of the contract, for the answering versions. One ``ItemWatch`` per item, retired ones included, by
    number; ``()`` for no playbook. A legacy playbook gives its virtual items, all kept."""
    parseable = [v for v in versions if v.items is not None]
    if not parseable:
        return _virtual(versions)
    rec = records_of(cases, results, contract_versions)
    out = []
    for track in sorted(_tracks(parseable, rec).values(), key=lambda t: number_of(t.id)):
        last = track.segs[-1]
        coverage = coverage_of(last.refs, criteria, rec.assertions)
        w = track.watch
        if w is None:
            state = "retired" if not track.live else "restored" if track.restored else "kept"
            out.append(ItemWatch(track.id, track.kind, state, last.version, restores=track.restored, coverage=coverage, retires=_retires(rec, track)))
            continue
        found = _derive_watch(rec, w)
        state = (
            "retired" if not track.live else "restored" if track.restored else "kept" if w.ended
            else "warning" if found.related else "kept" if found.kept else "new"
        )
        out.append(ItemWatch(
            track.id, track.kind, state, w.changes[-1].version, w.start, w.k, w.r, found.clean, found.waiting, found.related, found.pending,
            track.restored, coverage, len(found.related) >= 2 and track.live and not w.ended, w.carried, _retires(rec, track, (w, found)),
        ))
    return tuple(out)
