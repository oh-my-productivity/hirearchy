"""The watch of the playbook's items (design 3 and 8): what the files say about each item, derived, never stored.

Pure: every function reads values (cases, results, contract versions, playbook versions), never a file. Its one caller is
``CaseServiceEvidence.watch``, so every reader of a watch state goes through one derivation path.

The facts it reads come first: the records as of a moment, the subjects of a rejection, the lineage of a criterion as of a time (B3, B4),
coverage and refs. Then the items' texts over time, the candidate cases and the window of a watched change, and ``watch_states``."""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone

from ..kernel import Message, link_ids, msg_time, verdict_tier
from ..services import Contract, Criterion, ItemWatch, Playbook, PlaybookItem, amendment_ids, migrate_body, number_criteria, text_tokens
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
    """A watched change (section 3): the gated change that put a text on trial, live from ``at``. The cases of its ``why`` assertions are no candidates."""

    version: int
    at: datetime
    excluded: frozenset[str]
    tokens: _Tokens  # the tokens of the watched text: the item is "live in the watched text" while its text has them (W1)


@dataclass
class _Track:
    """What the versions say of one item: its texts over time, whether it is live, and the watched change it is on trial for (None: never watched)."""

    id: str
    kind: str
    segs: list[_Seg]
    live: bool = True
    changes: list[_Change] = field(default_factory=list)


def _tokens_of(item: PlaybookItem) -> _Tokens:
    """The text tokens of an item (section 3): two texts with equal tokens differ only in spacing, case, markdown and sentence punctuation."""
    return tuple(text_tokens(item.text)), tuple(text_tokens(item.when)) if item.kind == "rule" else ()


def _words_of(item: PlaybookItem) -> str:
    """The words refs are read from: a step's text, a rule's condition and action."""
    return item.text if item.kind == "step" or item.when in ("", "always") else f"{item.when} {item.text}"


def _tracks(versions: Sequence[Playbook], rec: Records) -> dict[str, _Track]:
    """The texts and watched changes of every item, version by version (oldest first; ``versions`` all parse)."""
    tracks: dict[str, _Track] = {}
    live: dict[str, PlaybookItem] = {}
    for v in versions:
        at = v.revised or EPOCH
        now = {i.id: i for i in v.items or ()}
        for gone in [x for x in live if x not in now]:
            tracks[gone].live = False
            tracks[gone].segs[-1].end = at
        for item in now.values():
            if live.get(item.id) == item:
                continue
            track = tracks.setdefault(item.id, _Track(item.id, item.kind, []))
            if track.segs and track.live:
                track.segs[-1].end = at
            track.live = True
            track.kind = item.kind
            tokens = _tokens_of(item)
            track.segs.append(_Seg(
                item.id, v.version, at, None, item.kind, item.text, item.when, item.why, refs_of(rec, _words_of(item), item.why, at), tokens,
            ))
            if v.admitted in ("b", "c") and v.item == item.id:  # a gated change puts the text on trial
                track.changes = [_Change(v.version, at, frozenset(rec.by_id[x].case for x in item.why if x in rec.by_id), tokens)]
        live = now
    return tracks


def _seg_at(track: _Track, when: datetime) -> _Seg | None:
    """The text of the item that was live at ``when``, None when it was not live then."""
    return next((s for s in track.segs if s.start <= when and (s.end is None or when < s.end)), None)


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


def _relations(rec: Records, track: _Track, members: Sequence[tuple[Assertion, Message]]) -> tuple[list[Assertion], list[Assertion]]:
    """Of rejections with the result each was given on: those related to the item (not pending, given on a result created while a text of it was
    live, and their subjects meet that text's refs) and those pending (no answer yet)."""
    pending = [a for a, _ in members if pending_rejection(rec, a.id)]
    held = {a.id for a in pending}
    related = []
    for a, result in members:
        seg = _seg_at(track, when_of(result))
        if a.id not in held and seg is not None and subjects_of(rec, a.id) & seg.refs:
            related.append(a)
    return related, pending


def _records(rec: Records) -> list[Moment]:
    """The places of the records that can change what the files derive: every verdict note, every human link note and every answering contract version."""
    found = {moment_of(v.message) for c in rec.cases for v in c.verdicts}
    found |= {moment_of(n) for c in rec.cases for v in c.verdicts for n in v.link_notes}
    found |= {defined_moment(c) for c in rec.contracts if c.answers}
    return sorted(found)


def _watch_end(rec: Records, track: _Track, change: _Change, k: int) -> Moment | None:
    """``K``, the end of the watch (section 3): the earliest record at or after ``D`` such that the files created up to and including it derive ``kept``
    (``E`` defined, every rejection in the window answered and unrelated). None while the item has not reached ``kept``."""
    judging = _window(rec, change, k).judging
    if judging is None:
        return None
    for place in _records(rec):
        if place < moment_of(judging):
            continue
        view = until(rec, place)
        found = _window(view, change, k)
        related, pending = _relations(view, track, found.members)
        if found.closed and not related and not pending:
            return place
    return None


@dataclass(frozen=True)
class _Derived:
    """What one watched change derives: its related and pending rejections, the counts over its first k candidates and whether it reached ``kept``."""

    related: tuple[str, ...]
    pending: tuple[str, ...]
    clean: int
    waiting: int
    kept: bool


def _warned_window(rec: Records, track: _Track, change: _Change, known: set[str]) -> list[tuple[Assertion, Message]]:
    """The warned window of ``change`` (B1): every human rejection on a result created at or after its live-from, recorded while the item was live
    in the watched text, whatever ``E``, ``D`` and ``K`` are. Those in the window already (``known``) are left out."""
    found = []
    for a in rec.assertions:
        result = rejected_result(rec, a)
        if a.id in known or result is None or when_of(result) < change.at:
            continue
        seg = _seg_at(track, when_of(a.verdict.message))
        if seg is not None and seg.tokens == change.tokens:
            found.append((a, result))
    return found


def _derive(rec: Records, track: _Track, change: _Change, k: int) -> _Derived:
    """The counts of ``change`` over ``rec``: ``K``, the window closed at it, related and pending rejections, and, once the item has one related
    rejection, the warned window in which a second retires it whatever the order of the records."""
    end = _watch_end(rec, track, change, k)
    window = _window(rec, change, k, end)
    related, pending = _relations(rec, track, window.members)
    if related:
        extra = _warned_window(rec, track, change, {a.id for a, _ in window.members})
        related += _relations(rec, track, extra)[0]
    unclean = {a.case for a in (*pending, *related)}
    return _Derived(
        tuple(sorted((a.id for a in related), key=number_of)), tuple(sorted((a.id for a in pending), key=number_of)),
        sum(1 for c, j in zip(window.first, window.judged) if j is not None and c.case.id not in unclean),
        sum(1 for j in window.judged if j is None), end is not None,
    )


def _virtual(versions: Sequence[Playbook]) -> tuple[ItemWatch, ...]:
    """A legacy playbook has no items yet: it reads as it would migrate (4.4), every item ``kept`` (it predates the watch)."""
    last = versions[-1] if versions else None
    if last is None or last.items is not None or last.parse_error or not last.body.strip():
        return ()
    return tuple(ItemWatch(i.id, i.kind, "kept", last.version) for i in migrate_body(last.body).items)


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
        if not track.changes:
            out.append(ItemWatch(track.id, track.kind, "kept" if track.live else "retired", last.version, coverage=coverage))
            continue
        change = track.changes[-1]
        found = _derive(rec, track, change, K_DEFAULT)
        due = len(found.related) >= 2
        state = "retired" if not track.live else "warning" if found.related else "kept" if found.kept else "new"
        out.append(ItemWatch(
            track.id, track.kind, state, change.version, change.at, K_DEFAULT, (0, 0), found.clean, found.waiting, found.related, found.pending,
            0, coverage, due and track.live,
        ))
    return tuple(out)
