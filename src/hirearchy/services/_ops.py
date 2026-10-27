"""``revise_playbook`` changes one item per call (design 5): the rules that judge a change, and the owner's reviser.

Pure rules first: the 30% rule (7), the two lists of the cap's refusal (10) and the weakening rule (9.1). Each refusal text is a constant beside its rule."""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from typing import TypeVar

from ..agents import AgentDirectory
from ..delivery import MessageDelivery
from ..kernel import NAME_RE, ROOT, OrgError, clip_line, parent, split_frontmatter
from ..mail import MailboxReader
from ._items import RULES_HEADING, RUNTIME_MIGRATION, PlacementError, canonical_why, checked_body, item_extra, migrate_body, place_add, place_restore
from ._protocols import PlaybookRevisions, PlaybookTexts, PlaybookWriter
from .api import (
    REASON_MAX, Admission, Contract, Criterion, ItemWatch, PlaybookChange, PlaybookItem, PlaybookRace, PlaybookSection, ServiceCatalog, ServiceEvidence,
    Playbook, item_words, normalize_evidence, text_tokens,
)

# ----------------------------------------------------------------------------------------------------------------------- the 30% rule (7)

SPLIT_FLOOR = 50  # words: the limit of a small playbook (this design's labelled default, not configurable)
PB_SPLIT = (
    "refused: this change touches {changed} of the playbook's {base} words, more than about 30% ({limit}): make it as smaller changes (one item, or "
    "part of an item, per call), each with its own reason and evidence, so each one is judged and watched on its own. Nothing was written."
)


def item_tokens(item: PlaybookItem) -> list[str]:
    """The content words of one item as text tokens (pure): its ``text`` and, for a rule, its ``when`` (``always`` counts none)."""
    always = item.when.strip().lower() in ("", "always")
    return [*text_tokens(item.text), *([] if always else text_tokens(item.when))]


def content_tokens(items: Sequence[PlaybookItem], headings: Sequence[str] = ()) -> list[str]:
    """The content words of a playbook as text tokens (pure): those of every live item (:func:`item_tokens`) and of the section headings. Item
    markers, the WHEN/THEN/WHY keywords and the ids after WHY are no words, so a migration's markers never count."""
    return [*(tok for h in headings for tok in text_tokens(h)), *(tok for i in items for tok in item_tokens(i))]


def split_limit(base: int) -> int:
    """The most words one gated change may touch in a playbook of ``base`` content words: about 30% (rounded up), and at least 50."""
    return max(-(-3 * base // 10), SPLIT_FLOOR)


def split_check(current: Sequence[str], new: Sequence[str]) -> None:
    """Refuse (PB-SPLIT) a change that touches more than ``max(ceil(0.3 x base), 50)`` words (pure). ``current`` and ``new`` are the content words
    (:func:`content_tokens`) of the playbook before and after; ``changed`` is the size of the multiset difference both ways, ``base`` the size of
    ``current`` (0 for an empty playbook: the limit is then the floor)."""
    before, after = Counter(current), Counter(new)
    changed = sum((after - before).values()) + sum((before - after).values())
    limit = split_limit(len(current))
    if changed > limit:
        raise OrgError(PB_SPLIT.format(changed=changed, base=len(current), limit=limit))


# ----------------------------------------------------------------------------------------------------------------------- the cap (10)

CAP_LISTED = 5  # items each list of the cap's refusal names, at most
PB_CAP = (
    "refused: the playbook would have {n} words; the limit is {cap} (playbook_max_words). Retire an item first.{candidates}{uncovered}{rest} "
    "Nothing was written."
)
PB_CAP_CANDIDATES = " Candidates, oldest first (new items whose watch rests on no regression assertion): {items}."
PB_CAP_UNCOVERED = " Items that cover no criterion or assertion (no acknowledgement needed): {items}."
PB_CAP_EMPTY = " Every item covers a criterion or an assertion: retire one yourself (it needs {client}'s acknowledgement), or shorten one."
PB_CAP_SHORTEN = ' Or shorten an item (op="edit").'


@dataclass(frozen=True)
class CapCandidate:
    """A new item whose watch rests on no regression assertion (10): its id, the version that gave it its text, and what it covers."""

    id: str
    since: int
    covers: tuple[str, ...] = ()


def _number(item_id: str) -> int:
    return int(item_id[1:]) if item_id[1:].isdigit() else 0


def cap_lists(
    items: Sequence[PlaybookItem], watches: Mapping[str, ItemWatch], started: Mapping[str, Sequence[str]], current: int = 0,
) -> tuple[list[CapCandidate], list[tuple[str, int]]]:
    """The two lists of the cap's refusal (pure), each at most 5. First: the live items in ``new`` that continue no other watch and whose watch
    rests on no ``R<k>``, oldest first; ``started`` maps an item to the ``why`` ids of the gated change that started its watch (an item without
    an entry, such as one whose watch an exempt restore started, is none). Second: the oldest live items that cover no criterion or assertion
    (their retire needs no acknowledgement); an item the watch does not know counts as ``current`` (the version it is read in). ``watches`` maps
    an item to its ``ItemWatch``."""
    live = [i.id for i in items]

    def since(item_id: str) -> int:
        return watches[item_id].text_version if item_id in watches else current

    candidates = sorted(
        (
            i for i in live
            if i in watches and watches[i].state == "new" and not watches[i].carried and i in started
            and not any(x.startswith("R") for x in started[i])
        ),
        key=lambda i: (since(i), _number(i)),
    )
    uncovered = sorted((i for i in live if not (watches[i].coverage if i in watches else ())), key=lambda i: (since(i), _number(i)))
    return (
        [CapCandidate(i, since(i), watches[i].coverage) for i in candidates[:CAP_LISTED]],
        [(i, since(i)) for i in uncovered[:CAP_LISTED]],
    )


def cap_refusal(n: int, cap: int, candidates: Sequence[CapCandidate], uncovered: Sequence[tuple[str, int]], client: str) -> str:
    """PB-CAP (pure): the playbook would have ``n`` content words, over ``cap``; the two lists say what to retire. With both empty, the refusal says
    that every item covers something, so retiring one needs ``client``'s acknowledgement."""
    named = [
        f"{c.id} (since v{c.since}; cites {', '.join(c.covers)}: retiring it needs {client}'s acknowledgement)" if c.covers else f"{c.id} (since v{c.since})"
        for c in candidates
    ]
    old = [f"{item_id} (since v{since})" for item_id, since in uncovered]
    return PB_CAP.format(
        n=n, cap=cap,
        candidates=PB_CAP_CANDIDATES.format(items=", ".join(named)) if named else "",
        uncovered=PB_CAP_UNCOVERED.format(items=", ".join(old)) if old else "",
        rest=PB_CAP_SHORTEN if named or old else PB_CAP_EMPTY.format(client=client),
    )


# ----------------------------------------------------------------------------------------------------------------------- weakening (9.1)


def weakening(old: PlaybookItem | None, new: PlaybookItem, old_coverage: Sequence[str], new_coverage: Sequence[str]) -> bool:
    """Whether replacing the live text ``old`` with ``new`` lowers a bar (pure): (i) the new text's coverage lacks an id of the old text's, or (ii)
    the new text's content words are a strict sub-multiset of the old text's (it only deletes words). A formatting fix (equal tokens) is never
    weakening, and neither is a restore of a retired item (``old`` is None: it replaces no live text)."""
    if old is None:
        return False
    before, after = Counter(item_tokens(old)), Counter(item_tokens(new))
    if before == after:
        return False
    return any(i not in new_coverage for i in old_coverage) or not after - before


# ----------------------------------------------------------------------------------------------------------------------- the refusals (5.3)

PB_FORM = (
    "refused: revise_playbook changes one item of the playbook per call; it no longer takes the whole text (`content`). Use op=\"add\" (kind "
    "\"step\" with text and after, or kind \"rule\" with when and then), \"edit\" (item and the new text), \"retire\" (item), \"restore\" (item, "
    "version) or \"move\" (item, after). Your playbook's items and their ids are in your prompt under \"# Playbook\". Nothing was written."
)
PB_OP = "refused: op is one of first, add, edit, retire, restore, move: {op}. Nothing was written."
PB_ARGS = "refused: op=\"{op}\" takes {needed}; {wrong}. Nothing was written."
PB_FIRST_EXISTS = (
    "refused: `{service}` already has playbook v{n}: op=\"first\" writes only the first version. Change it one item at a time "
    "(op=\"add\", \"edit\", \"retire\", \"restore\" or \"move\"). Nothing was written."
)
PB_FIRST_LATE = (
    "refused: `{service}` already has evidence ({what}), so its playbook is built one item at a time: op=\"add\" with evidence (your Reflect "
    "section says what is admitted). The first version is only for the procedure of the first request. Nothing was written."
)
PB_ITEM = "refused: `{service}` has no live item {id}. Its items: {ids}{retired}. Nothing was written."
PB_ITEM_RETIRED = "; retired: {ids} (op=\"restore\" brings one back)"
PB_SAME = "refused: no change: {id} {what}. Change an item only when the evidence calls for a different way of working. Nothing was written."
PB_TEXT = "refused: {rule}. Nothing was written."
PB_RACE = "refused: the playbook of `{service}` changed while this call ran (now v{n}), so this change was not written: call again."
PB_UNREADABLE = (
    "refused: the record of `{service}` cannot be read ({error}), so the playbook was not changed. Try again; if it persists, tell your parent."
)
LOCKED = (
    "the contract of `{service}` is locked by {client}: you may not revise its playbook. Follow the current one, and if you think it must change, "
    "tell {client} (`send`)."
)
REASON_ERROR = (
    f"reason is 1-{REASON_MAX} characters: say what changed and which cases it rests on (case ids from the evidence), so the next revision can judge it"
)
NOT_OWNER = (
    "you do not own a service called `{name}`. Services you own: {mine}. Only the owner revises a playbook, and services are defined for you by "
    "your parent (define_service)."
)

OPS = ("first", "add", "edit", "retire", "restore", "move")
KINDS = ("step", "rule")
FIRST_NEEDED = "text (the whole first version, in markdown)"
NEEDED = {
    "first": FIRST_NEEDED,
    "add": 'kind ("step" with text, or "rule" with then), and optionally when (a rule) and after (an item id)',
    "edit": "item and the new text (a step: text; a rule: then and/or when), and optionally acknowledged",
    "retire": "item, and optionally acknowledged",
    "restore": "item, and optionally version and acknowledged",
    "move": 'item and after (an item id of its section, or "start")',
}
ARG_ORDER = ("item", "kind", "text", "when", "then", "after", "version", "acknowledged")
TAKES: dict[str, tuple[str, ...]] = {
    "first": ("text",), "edit": ("item", "text", "when", "then", "acknowledged"), "retire": ("item", "acknowledged"),
    "restore": ("item", "version", "acknowledged"), "move": ("item", "after"),
}
REQUIRED: dict[str, tuple[str, ...]] = {"first": ("text",), "edit": ("item",), "retire": ("item",), "restore": ("item",), "move": ("item", "after")}
STEP_LIMIT, THEN_LIMIT, WHEN_LIMIT, WORDS_LIMIT = 1200, 600, 300, 150  # characters of a step, a rule's then and when; words of an item with its when
ITEM_ID = re.compile(r"\[P\d+\]", re.IGNORECASE)
THEN_WORD = re.compile(r"\bTHEN\b")
EXEMPT = "no evidence needed"
LINE_CLIP = 200  # characters of an item's text in the note to an agent client


@dataclass(frozen=True)
class _Call:
    """The arguments of one ``revise_playbook`` call, as the checks leave them: ``item`` and ``after`` in their ids' form, ``when`` of a rule
    normalised (``always`` for none)."""

    actor: str
    service: str
    client: str
    op: str
    reason: str
    ids: tuple[str, ...]
    item: str = ""
    kind: str = ""
    text: str | None = None
    when: str | None = None
    then: str | None = None
    after: str = ""
    version: int | None = None
    acknowledged: str | None = None


@dataclass(frozen=True)
class _Book:
    """The playbook one op judges: its items and sections, the highest id ever used and the version it is. ``migrated`` is the version a migration
    wrote first in this call (None: none) with the sentence of the client's note and of the reply that say so."""

    version: int
    items: tuple[PlaybookItem, ...]
    sections: tuple[PlaybookSection, ...]
    items_max: int
    migrated: int | None = None
    note: str = ""
    reply: str = ""


T = TypeVar("T")


def _normal_when(when: str | None) -> str:
    """A rule's ``when`` as it is stored: ``always`` for none."""
    text = (when or "").strip()
    return "always" if not text or text.lower() == "always" else text


def _rebuilt_in_order(items: Sequence[PlaybookItem], sections: Sequence[PlaybookSection]) -> tuple[tuple[PlaybookItem, ...], tuple[PlaybookSection, ...]]:
    """The items in the order of the sections (the body order), each carrying the heading of its section."""
    by_id = {i.id: i for i in items}
    return tuple(replace(by_id[i], section=s.heading) for s in sections for i in s.ids), tuple(sections)


def _after(after: str | None) -> str:
    """An ``after`` as an id (upper case), or ``start`` as it is."""
    text = (after or "").strip()
    return text.lower() if text.lower() == "start" else text.upper()


def _heading_name(heading: str) -> str:
    return heading.lstrip("#").strip()


def _item_line(item: PlaybookItem) -> str:
    """An item's words on one line (the note to an agent client)."""
    words = item.text if item.kind == "step" else f"WHEN {item.when} THEN {item.text}"
    return clip_line(words, LINE_CLIP)


def _without(
    items: Sequence[PlaybookItem], sections: Sequence[PlaybookSection], gone: PlaybookItem,
) -> tuple[tuple[PlaybookItem, ...], tuple[PlaybookSection, ...]]:
    """The items and sections without ``gone``, in the two normal forms of 4.1: the text before the first heading is in the body only while it
    holds a live item, and the rules section only while a rule is live (a heading of the owner's own that is left with no item stays)."""
    kept = tuple(i for i in items if i.id != gone.id)
    out = [replace(s, ids=tuple(i for i in s.ids if i != gone.id)) for s in sections]
    if out and out[0].heading == "" and not out[0].ids and gone.section == "":
        out.pop(0)
    if gone.kind == "rule" and not any(i.kind == "rule" for i in kept) and out and out[-1].heading.rstrip() == RULES_HEADING and not out[-1].ids:
        out.pop()
    return kept, tuple(out)


class RuleItemReviser(PlaybookRevisions):
    """The owner changes one item of its playbook per call (design 5): first, add, edit and retire. The order of the checks is 5.1's: the form, the
    owner, the lock, the reason, the op and its arguments (all read-only), the migration of a free-text playbook, the item, the gate; then the
    write, a compare-and-swap, and the client's quiet note. A refusal writes nothing, except the migration, which changes no word."""

    def __init__(
        self, agents: AgentDirectory, catalog: ServiceCatalog, texts: PlaybookTexts, playbooks: PlaybookWriter, delivery: MessageDelivery,
        evidence: ServiceEvidence, mail: MailboxReader,
    ) -> None:
        self._agents = agents
        self._catalog = catalog
        self._texts = texts
        self._playbooks = playbooks
        self._delivery = delivery
        self._evidence = evidence
        self._mail = mail

    def revise_playbook(
        self, actor: str, service: str, op: str | None, reason: str, evidence: Sequence[str], *, item: str | None = None, kind: str | None = None,
        text: str | None = None, when: str | None = None, then: str | None = None, after: str | None = None, version: int | None = None,
        acknowledged: str | None = None, content: str | None = None,
    ) -> PlaybookChange:
        if content is not None or op is None:
            raise OrgError(PB_FORM)
        actor = self._agents.require(actor)
        contract = self._owned(actor, service)
        client = parent(actor) or ROOT
        if contract.locked:
            raise OrgError(LOCKED.format(service=service, client=client))
        reason = (reason or "").strip()
        if not reason or len(reason) > REASON_MAX:
            raise OrgError(REASON_ERROR)
        ids = normalize_evidence(evidence)
        name = op.strip().lower()
        if name not in OPS:
            raise OrgError(PB_OP.format(op=op))
        given = {"item": item, "kind": kind, "text": text, "when": when, "then": then, "after": after, "version": version, "acknowledged": acknowledged}
        self._shaped(name, given)
        criteria = [c for c in self._read(service, lambda: self._catalog.criteria(actor, service)) if c.current]
        self._texts_ok(name, text, then, when, criteria)
        call = _Call(
            actor, service, client, name, reason, ids, item=(item or "").strip().upper(), kind=(kind or "").strip().lower(),
            text=None if text is None else text.strip(), when=None if when is None else _normal_when(when), then=None if then is None else then.strip(),
            after=_after(after), version=version, acknowledged=acknowledged,
        )
        current = self._read(service, lambda: self._catalog.read_playbook(actor, service))
        if name == "first":
            return self._first(call, current.version)
        book = self._migrated(call, current)
        try:
            return self._change(call, book)
        except OrgError:
            if book.migrated is not None:  # the migration stays written: the client is told of it on its own
                said = book.note[0].upper() + book.note[1:]
                self._delivery.notify(client, f"playbook of {service}: v{book.migrated} (items)", f"{said} Nothing else changed.", wake=False)
            raise

    # ------------------------------------------------------------------------------------------------------ step 1: the arguments

    @staticmethod
    def _shaped(op: str, given: Mapping[str, object]) -> None:
        """PB-ARGS: which arguments go with ``op``, which one is missing, a ``kind`` that is neither step nor rule."""
        kind = str(given["kind"]).strip().lower() if given["kind"] is not None else None
        takes = set(TAKES.get(op, ()))
        required = set(REQUIRED.get(op, ()))
        if op == "add":
            takes = {"kind", "after", *({"text"} if kind == "step" else {"then", "when"} if kind == "rule" else {"text", "then", "when"})}
            required = {"kind", *({"text"} if kind == "step" else {"then"} if kind == "rule" else set())}
        wrong: list[str] = []
        for arg in ARG_ORDER:
            value = given[arg]
            if op == "add" and arg == "kind" and value is not None and kind not in KINDS:
                wrong.append(f'kind is "{str(value).strip()}", not "step" or "rule"')
            elif value is None and arg in required:
                wrong.append(f"{arg} is missing")
            elif value is None and op == "edit" and arg == "text" and given["then"] is None and given["when"] is None:
                wrong.append("text is missing")
            elif value is not None and arg not in takes:
                wrong.append(f'{arg} does not go with op="{op}"')
        if wrong:
            raise OrgError(PB_ARGS.format(op=op, needed=NEEDED[op], wrong="; ".join(wrong)))

    def _texts_ok(self, op: str, text: str | None, then: str | None, when: str | None, criteria: Sequence[Criterion]) -> None:
        """PB-TEXT (19.2): the one-line, length, word and marker rules of the words an op carries, but for a text that is a current criterion's own
        words (exempt from the length, word, bracket and heading rules)."""
        if op == "first":
            body = self._first_body(text or "")
            cap = self._texts.cap()
            if not body:
                raise OrgError(PB_TEXT.format(rule="text is empty"))
            if len(body.split()) > cap:
                raise OrgError(PB_TEXT.format(rule=f"text has {len(body.split())} words; the limit is {cap} (playbook_max_words)"))
            return
        words = len((when or "").split()) if when is not None and _normal_when(when) != "always" else 0
        for field, value, limit in (("text", text, STEP_LIMIT), ("then", then, THEN_LIMIT)):
            if value is not None:
                self._words_ok(field, value.strip(), limit, words, criteria)
        if when is not None:
            self._when_ok(when)

    @staticmethod
    def _words_ok(field: str, value: str, limit: int, when_words: int, criteria: Sequence[Criterion]) -> None:
        if not value:
            raise OrgError(PB_TEXT.format(rule=f"{field} is empty"))
        lines = value.splitlines()
        if len(lines) > 1:
            raise OrgError(PB_TEXT.format(rule=f"{field} has more than one line ({len(lines)} lines)"))
        if item_words(value, criteria) is not None:
            return
        if len(value) > limit:
            raise OrgError(PB_TEXT.format(rule=f"{field} has more than {limit} characters ({len(value)})"))
        if len(value.split()) + when_words > WORDS_LIMIT:
            raise OrgError(PB_TEXT.format(rule=f"text and then have more than {WORDS_LIMIT} words with when ({len(value.split()) + when_words})"))
        found = ITEM_ID.search(value)
        if found:
            raise OrgError(PB_TEXT.format(rule=f"{field} has an item id in brackets ({found.group()}): ids are the runtime's"))
        if field == "text" and value.startswith("#"):
            raise OrgError(PB_TEXT.format(rule='text starts with "#": a heading is no item'))

    @staticmethod
    def _when_ok(when: str) -> None:
        value = when.strip()
        lines = value.splitlines()
        if len(lines) > 1:
            raise OrgError(PB_TEXT.format(rule=f"when has more than one line ({len(lines)} lines)"))
        if len(value) > WHEN_LIMIT:
            raise OrgError(PB_TEXT.format(rule=f"when has more than {WHEN_LIMIT} characters ({len(value)})"))
        found = ITEM_ID.search(value)
        if found:
            raise OrgError(PB_TEXT.format(rule=f"when has an item id in brackets ({found.group()}): ids are the runtime's"))
        if THEN_WORD.search(value):
            raise OrgError(PB_TEXT.format(rule='when has the word "THEN" in capitals: it would split the rule there; write the condition without it'))

    @staticmethod
    def _first_body(text: str) -> str:
        """The text of a first version: the frontmatter the caller wrote (the runtime writes it) stripped."""
        body = text.replace("\r\n", "\n")
        return (split_frontmatter(body)[1] if body.startswith("---\n") else body).strip()

    def _read(self, service: str, read: Callable[[], T]) -> T:
        try:
            return read()
        except OSError as error:
            raise OrgError(PB_UNREADABLE.format(service=service, error=error)) from error

    def _owned(self, actor: str, name: str) -> Contract:
        """The contract of ``name`` among the services ``actor`` owns, or an error listing the ones it owns."""
        contract = self._catalog.read_contract(actor, name) if NAME_RE.fullmatch(name or "") else None
        if contract is None:
            mine = ", ".join(self._catalog.service_names(actor)) or "none"
            raise OrgError(NOT_OWNER.format(name=name, mine=mine))
        return contract

    # ------------------------------------------------------------------------------------------------------ the first version

    def _first(self, call: _Call, version: int) -> PlaybookChange:
        """``first`` (5.1): the whole first version as step items, only while there is no playbook (PB-FIRST-EXISTS) and no verdict or rework
        (PB-FIRST-LATE). Exempt."""
        if version:
            raise OrgError(PB_FIRST_EXISTS.format(service=call.service, n=version))
        late = self._read(call.service, lambda: self._late(call))
        if late:
            raise OrgError(PB_FIRST_LATE.format(service=call.service, what=late))
        migration = migrate_body(self._first_body(call.text or ""))
        admission = Admission("first", call.ids, "the first playbook (no evidence needed)")
        book = _Book(0, (), (), 0)
        items, sections = migration.items, migration.sections
        path = self._write(call, book, items, sections, len(items), admission, reason=call.reason + migration.reason)
        change = PlaybookChange(
            1, "first", "", "", admission, None, len(items), client=call.client, sections=tuple(_heading_name(s.heading) for s in sections if s.heading),
        )
        return self._told(call, book, path, change, f"wrote the first playbook ({len(items)} items)", "")

    def _late(self, call: _Call) -> str:
        """The oldest verdict (of any tier) or rework of the service in its client's mail, as PB-FIRST-LATE names it; "" when there is none."""
        sent = self._mail.sent(call.client)
        tasks = {m.id for m in sent if m.type == "task" and m.service == call.service and m.to == call.actor}
        found: list[tuple[str, str]] = []
        for m in sent:
            if m.to != call.actor:
                continue
            if m.type == "task" and m.service == call.service and m.revises:
                found.append((m.id, f"a rework {m.id}"))
            elif m.type == "note" and m.feedback and m.reply_to in tasks:
                found.append((m.id, f"a verdict on {m.reply_to}"))
        return min(found)[1] if found else ""

    # ------------------------------------------------------------------------------------------------------ step 2: the migration (4.4)

    def _migrated(self, call: _Call, current: Playbook) -> _Book:
        """The playbook as the op judges it: its items, or the items of a free-text playbook, which are written first as the next version (the
        migration changes no word, so it stays written when the op is refused)."""
        version = current.version
        if not version:
            return _Book(0, (), (), 0)
        if current.items is not None:
            return _Book(version, current.items, current.sections, current.items_max)
        migration = migrate_body(current.body)
        count = len(migration.items)
        reason = f"the free-text v{version} as {count} items (no change of words)" + migration.reason
        extra = item_extra(migration.items, count, "migrate", admitted="migrate")
        body = checked_body(migration.items, migration.sections, extra)
        try:
            self._playbooks.write(call.actor, call.service, version + 1, body, RUNTIME_MIGRATION, reason, version, extra)
        except PlaybookRace as race:
            raise OrgError(PB_RACE.format(service=call.service, n=race.current)) from race
        span = f"P1-P{count}" if count else "no items"
        return _Book(
            version + 1, migration.items, migration.sections, count, version + 1,
            f"the free text of v{version} as {count} items ({span}), no change of words{migration.reason}.",
            f"playbook v{version + 1} is the free-text v{version} as {count} items ({span}, no change of words{migration.reason}). ",
        )

    # ------------------------------------------------------------------------------------------------------ steps 4 to 6: the item, the gate, the write

    def _change(self, call: _Call, book: _Book) -> PlaybookChange:
        live = {i.id: i for i in book.items}
        if call.op == "add":
            return self._add(call, book)
        if call.op == "restore" and call.item not in live and self._retired(call.item, book):
            return self._restore(call, book, None)
        if call.item not in live:
            raise OrgError(self._no_item(call, book))
        if call.op == "retire":
            return self._retire(call, book, live[call.item])
        if call.op == "restore":
            return self._restore(call, book, live[call.item])
        if call.op == "move":
            return self._move(call, book, live[call.item])
        return self._edit(call, book, live[call.item])

    @staticmethod
    def _retired(item_id: str, book: _Book) -> bool:
        """Whether ``item_id`` is an id this playbook used and no longer holds (an id is never reused)."""
        number = item_id[1:]
        return item_id[:1] == "P" and number.isdigit() and 1 <= int(number) <= book.items_max and item_id not in {i.id for i in book.items}

    def _no_item(self, call: _Call, book: _Book) -> str:
        """PB-ITEM: the item is not live; the live and the retired ids are listed."""
        live = [i.id for i in book.items]
        gone = [f"P{n}" for n in range(1, book.items_max + 1) if f"P{n}" not in live]
        return PB_ITEM.format(
            service=call.service, id=call.item, ids=", ".join(live) or "none yet",
            retired=PB_ITEM_RETIRED.format(ids=", ".join(gone)) if gone else "",
        )

    def _args_error(self, call: _Call, wrong: str) -> OrgError:
        return OrgError(PB_ARGS.format(op=call.op, needed=NEEDED[call.op], wrong=wrong))

    def _add(self, call: _Call, book: _Book) -> PlaybookChange:
        rule = call.kind == "rule"
        text = (call.then if rule else call.text) or ""
        when = call.when if rule else None
        new = PlaybookItem(f"P{book.items_max + 1}", call.kind, "", text, (when or "always") if rule else "")
        try:
            items, sections = place_add(book.items, book.sections, new, call.after or None)
        except PlacementError as error:
            raise self._args_error(call, str(error)) from error
        admission = self._evidence.admit_item(call.actor, call.service, call.ids, call.reason, kind=call.kind, text=text, when=when)
        items = tuple(replace(i, why=canonical_why(admission.why)) if i.id == new.id else i for i in items)
        path = self._write(call, book, items, sections, book.items_max + 1, admission, item=new.id)
        change = PlaybookChange(
            book.version + 1, "add", new.id, call.kind, admission, None, len(items), client=call.client,
        )
        return self._told(call, book, path, change, f"added {new.id} ({call.kind})", _item_line(next(i for i in items if i.id == new.id)))

    def _edit(self, call: _Call, book: _Book, old: PlaybookItem) -> PlaybookChange:
        if old.kind == "step":
            if call.then is not None or call.when is not None:
                raise self._args_error(call, f"{old.id} is a step: pass text")
            text, when = call.text or "", ""
        else:
            if call.text is not None:
                raise self._args_error(call, f"{old.id} is a rule: pass then and/or when")
            text, when = (call.then if call.then is not None else old.text), (call.when if call.when is not None else old.when)
        if (text, when) == (old.text, old.when):
            raise OrgError(PB_SAME.format(id=old.id, what="already reads so"))
        formatting = text_tokens(text) == text_tokens(old.text) and text_tokens(when) == text_tokens(old.when)
        if formatting:
            admission = Admission("exempt", (), EXEMPT)
            new = replace(old, text=text, when=when)
        else:
            admission = self._evidence.admit_item(call.actor, call.service, call.ids, call.reason, kind=old.kind, text=text, when=when or None)
            new = replace(old, text=text, when=when, why=canonical_why(admission.why))
        items = tuple(new if i.id == old.id else i for i in book.items)
        path = self._write(call, book, items, book.sections, book.items_max, admission, item=old.id)
        change = PlaybookChange(book.version + 1, "edit", old.id, old.kind, admission, None, len(items), formatting=formatting, client=call.client)
        what = f"fixed the formatting of {old.id}" if formatting else f"edited {old.id}"
        return self._told(call, book, path, change, what, _item_line(new))

    def _retire(self, call: _Call, book: _Book, old: PlaybookItem) -> PlaybookChange:
        items, sections = _without(book.items, book.sections, old)
        admission = Admission("exempt", (), EXEMPT)
        path = self._write(call, book, items, sections, book.items_max, admission, item=old.id)
        change = PlaybookChange(book.version + 1, "retire", old.id, old.kind, admission, None, len(items), client=call.client)
        return self._told(call, book, path, change, f"retired {old.id}", _item_line(old))

    # ------------------------------------------------------------------------------------------------------ restore and move

    def _restore(self, call: _Call, book: _Book, live: PlaybookItem | None) -> PlaybookChange:
        """``restore`` (5.1): the item's text of ``version`` comes back; by default its latest text before the current one, and for a retired item
        its last live text. A live item keeps its place; a retired one goes back where 4.1 says. Exempt for a text the client wrote (its ``why`` is
        the one the text had), else gated (the ``why`` of the new admission)."""
        versions = self._read(call.service, lambda: self._catalog.playbook_versions(call.actor, call.service))
        held = {p.version: i for p in versions if p.items is not None for i in p.items if i.id == call.item}
        if call.version is not None:
            if call.version not in held:
                raise self._args_error(call, f"version={call.version} does not hold {call.item}")
            source = call.version
        elif live is None:
            source = max(held, default=0)
            if not source:
                raise OrgError(self._no_item(call, book))
        else:
            earlier = [v for v, i in held.items() if v < book.version and (i.text, i.when) != (live.text, live.when)]
            if not earlier:
                since = min((v for v in held if all((held[u].text, held[u].when) == (live.text, live.when) for u in held if u >= v)), default=book.version)
                raise self._args_error(call, f"{call.item} has no earlier text: it has read so since v{since}, so there is nothing to restore")
            source = max(earlier)
        old = held[source]
        if live is not None and (old.text, old.when) == (live.text, live.when):
            raise OrgError(PB_SAME.format(id=live.id, what="already reads so"))
        if self._written_by(versions, held, source) == call.client:
            admission = Admission("restore", (), EXEMPT)
            restored = old
        else:
            admission = self._evidence.admit_item(call.actor, call.service, call.ids, call.reason, kind=old.kind, text=old.text, when=old.when or None)
            restored = replace(old, why=canonical_why(admission.why))
        if live is not None:
            items = tuple(restored if i.id == live.id else i for i in book.items)
            sections = book.sections
        else:
            layout = next(p.sections for p in versions if p.version == source)
            items, sections = place_restore(book.items, book.sections, restored, layout)
        path = self._write(call, book, items, sections, book.items_max, admission, item=call.item, restores=source)
        change = PlaybookChange(
            book.version + 1, "restore", call.item, old.kind, admission, None, len(items), restored_from=source, client=call.client,
        )
        return self._told(call, book, path, change, f"restored {call.item} to the text of v{source}", _item_line(restored))

    @staticmethod
    def _written_by(versions: Sequence[Playbook], held: Mapping[int, PlaybookItem], source: int) -> str:
        """Who wrote the text the item had in version ``source``: the author of the first version of the unbroken run that holds exactly that text
        (the version before it, when that one is the migration: the migration changed no word)."""
        text = (held[source].text, held[source].when)
        start = source
        while start - 1 in held and (held[start - 1].text, held[start - 1].when) == text:
            start -= 1
        by = {p.version: p.by for p in versions}
        return by.get(start - 1, "") if by.get(start) == RUNTIME_MIGRATION else by.get(start, "")

    def _move(self, call: _Call, book: _Book, old: PlaybookItem) -> PlaybookChange:
        """``move`` (5.1): the item goes right after ``after`` (an item of its section) or first (``start``); exempt. A move that changes nothing is
        PB-SAME."""
        at = next(k for k, s in enumerate(book.sections) if old.id in s.ids)
        ids = list(book.sections[at].ids)
        if call.after != "start" and call.after not in ids:
            raise self._args_error(call, f"after={call.after} is not an item of {old.id}'s section")
        before = list(ids)
        if call.after != old.id:
            ids.remove(old.id)
            ids.insert(0 if call.after == "start" else ids.index(call.after) + 1, old.id)
        if ids == before:  # after the item itself, or the item it already follows (``start``: it is already first)
            what = "is already first in its section" if call.after == "start" else f"already comes after {call.after}"
            raise OrgError(PB_SAME.format(id=old.id, what=what))
        sections = tuple(replace(s, ids=tuple(ids)) if k == at else s for k, s in enumerate(book.sections))
        admission = Admission("exempt", (), EXEMPT)
        items, sections = _rebuilt_in_order(book.items, sections)
        path = self._write(call, book, items, sections, book.items_max, admission, item=old.id)
        change = PlaybookChange(book.version + 1, "move", old.id, old.kind, admission, None, len(items), client=call.client, after=call.after)
        return self._told(call, book, path, change, f"moved {old.id} after {call.after}", "")

    def _write(
        self, call: _Call, book: _Book, items: Sequence[PlaybookItem], sections: Sequence[PlaybookSection], items_max: int, admission: Admission, *,
        item: str = "", reason: str = "", restores: int = 0,
    ) -> str:
        """The round-trip assertion (4.1), then the write: a compare-and-swap against the version this call judged (4.3)."""
        extra = item_extra(items, items_max, call.op, evidence=list(admission.evidence), admitted=admission.rule, item=item, restores=restores)
        body = checked_body(items, sections, extra)
        try:
            return self._playbooks.write(call.actor, call.service, book.version + 1, body, call.actor, reason or call.reason, book.version or None, extra)
        except PlaybookRace as race:
            raise OrgError(PB_RACE.format(service=call.service, n=race.current)) from race

    def _told(self, call: _Call, book: _Book, path: str, change: PlaybookChange, what: str, shown: str) -> PlaybookChange:
        """The client's quiet note (5.2): the op, the item, the admission, the evidence and the reason, never an item's words for a human client (D12);
        an ``acknowledged`` the change did not need is ignored. Returns the change with what the reply needs."""
        a = change.admission
        if call.op == "first":
            how = "the first playbook (no evidence needed)"
        elif a.rule == "restore":
            how = f"restores the text of v{change.restored_from}, which you wrote ({EXEMPT})"
        elif a.rule == "exempt":
            how = EXEMPT
        elif change.restored_from:
            how = f"restores the text of v{change.restored_from}; admitted: {a.detail}"
        else:
            how = f"admitted: {a.detail}"
        lines = [
            (f"Playbook v{book.migrated} is {book.note}\n" if book.migrated is not None else "")
            + f"{call.actor} revised the playbook of service `{call.service}` to v{change.version}: {what}.",
            f"Reason: {call.reason}",
            f"Evidence: {', '.join(a.evidence) or 'none'}; {how}",
        ]
        if shown and call.client != ROOT:
            lines.append(f"Text: {shown}")
        lines.append(f"File: {path}")
        self._delivery.notify(call.client, f"playbook of {call.service} revised to v{change.version}", "\n".join(lines), wake=False)
        ignored = call.acknowledged or "" if call.op in ("edit", "retire", "restore") else ""
        return replace(change, migrated=book.migrated, migration=book.reply, ack_ignored=ignored)
