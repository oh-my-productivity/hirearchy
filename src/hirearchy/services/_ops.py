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
from ..kernel import NAME_RE, ROOT, OrgError, clip_line, parent, split_frontmatter, stamp_of
from ..mail import MailboxReader
from ._acknowledge import text_hash
from ._items import (
    RUNTIME_MIGRATION, SPLITTERS, PlacementError, Splitter, and_ids, canonical_why, checked_body, item_extra, migrate_body, place_add, place_restore,
    repair_of, without,
)
from ._protocols import PlaybookRevisions, PlaybookTexts, PlaybookWriter, WatchSettlement
from .api import (
    REASON_MAX, Admission, Contract, Criterion, ItemWatch, PlaybookChange, PlaybookItem, PlaybookRace, PlaybookSection, ServiceCatalog, ServiceEvidence,
    Playbook, content_words, item_words, line_key, normalize_evidence, text_tokens,
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
PB_ITEM = "refused: {lead}`{service}` has no live item {id}. Its items: {ids}{retired}. Nothing was written."
PB_ITEM_RETIRED = "; retired: {ids} (op=\"restore\" brings one back)"
PB_ITEM_LEAD = "The watch retired {id} in v{n} (rejections {rejections}). "  # B7: only when step 3 of this call wrote the retire of the item the op names
PB_ITEM_WATCHED = "{id} (retired by the watch in v{n}: it comes back only as a confirmed criterion's own words)"  # B7: in the list of the retired
PB_SAME = "refused: no change: {id} {what}. Change an item only when the evidence calls for a different way of working. Nothing was written."
PB_TEXT = "refused: {rule}. Nothing was written."
PB_WATCHED_OUT = (
    "refused: this text is {id}'s text that {how} in v{n}, because the client rejected {rejections} on what it cited ({ids}). It comes back only as the "
    "own words of a criterion the client confirms after that (rule (c)). Nothing was written. If you think the client wants it, send {client} (`send`) "
    "this question once: \"Your rejections {rejections} retired this from how we deliver {service}: {first}. Do you want it back from now on? If yes, "
    "please add it to the contract as a criterion.\""
)
PB_RACE = "refused: the playbook of `{service}` changed while this call ran (now v{n}), so this change was not written: call again."
PB_ACK = (
    "refused: {id} covers {ids} (what the client required or rejected), so {change} lowers the bar: it needs {parent}'s acknowledgement. "
    "Nothing was written. Send {parent} (`send`) this once: \"May we {ask} {id} of {service} ({ids}) because {reason}? If yes: "
    "acknowledge_playbook(owner=\"{owner}\", service=\"{service}\", item=\"{id}\", op=\"{op}\"{hash}{words}).\" When the acknowledgement "
    "arrives (a note \"playbook acknowledgement\"), call this again with acknowledged=<its id>."
)
PB_ACK_RETIRE = "retiring it"  # the {change} of a retire, of an edit and of a restore
PB_ACK_EDIT = "this edit, which {how},"
PB_ACK_RESTORE = "restoring it to the text of v{k}, which {how},"
PB_ACK_DROPS = "drops {ids}"  # the {how}: a covered id the new text lacks (i), else the new text only deletes words (ii)
PB_ACK_DELETES = "only deletes words"
PB_ACK_ASK = {"retire": "retire", "edit": "change", "restore": "restore to v{k}"}  # the {ask} of the question to the parent
PB_ACK_HASH = ', text_hash="{hash}"'
PB_ACK_WORDS = ", words=<the user's yes, verbatim>"  # only when the parent is root
PB_ACK_BAD = "refused: acknowledged={id} is not {parent}'s acknowledgement of this change ({failed}). Nothing was written."
PB_ACK_MISSING = "not found in your mail"  # the {failed} conditions of PB-ACK-BAD, in the order they are judged
PB_ACK_SENDER = "not from {parent}"
PB_ACK_OTHER = "for {what}"
PB_ACK_NOT_ONE = "for no change: it is not an acknowledgement"
PB_ACK_TEXT = "for another text (hash {hash})"
PB_ACK_OLD = "older than the current text of {item}"
PB_ACK_USED = "already used by v{k}"
PB_ACK_USER = "not the user's (no source human)"
ACK_NOT_AN_ID = "acknowledged is not a message id ({x})"  # a PB-ARGS clause, judged only when the change needs an acknowledgement
MESSAGE_ID = re.compile(r"\d{8}T\d{12}-[A-Za-z0-9._-]+-[0-9a-f]{4}")  # a message id: its 21 timestamp characters, the sender (/ as .), 4 hex digits
REF = re.compile(r"\b[CR]\d+\b")  # a criterion or assertion id in an item's words
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
WATCH_TEXT_CLIP = 160  # characters of the retired text in the question of PB-WATCHED-OUT
THE_WATCH = "the watch retired"
YOU_WHILE_DUE = "you retired while the watch's retire of it was due"


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
    used: str = ""  # the id of the acknowledgement note the guard accepted for this call ("" when the change needed none)


@dataclass(frozen=True)
class _Book:
    """The playbook one op judges: its items and sections, the highest id ever used and the version it is. ``migrated`` is the version a migration
    wrote first in this call (None: none) with the sentence of the client's note and of the reply that say so."""

    version: int
    items: tuple[PlaybookItem, ...]
    sections: tuple[PlaybookSection, ...]
    items_max: int
    migrated: int | None = None
    note: str = ""  # what follows "Playbook v{n} is " in the note of an op that was written after a migration
    alone: str = ""  # the note of a migration whose op was then refused
    reply: str = ""
    retired_now: tuple[str, ...] = ()  # the ids the watch settler retired at step 3 of this call (B7)


T = TypeVar("T")


def _normal_when(when: str | None) -> str:
    """A rule's ``when`` as it is stored: ``always`` for none."""
    text = (when or "").strip()
    return "always" if not text or text.lower() == "always" else text


def _rebuilt_in_order(items: Sequence[PlaybookItem], sections: Sequence[PlaybookSection]) -> tuple[tuple[PlaybookItem, ...], tuple[PlaybookSection, ...]]:
    """The items in the order of the sections (the body order), each carrying the heading of its section."""
    by_id = {i.id: i for i in items}
    return tuple(replace(by_id[i], section=s.heading) for s in sections for i in s.ids), tuple(sections)


def _headings(sections: Sequence[PlaybookSection]) -> list[str]:
    """The heading lines of the sections (the text before the first heading has none)."""
    return [s.heading for s in sections if s.heading]


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


class RuleItemReviser(PlaybookRevisions):
    """The owner changes one item of its playbook per call (design 5): first, add, edit and retire. The order of the checks is 5.1's: the form, the
    owner, the lock, the reason, the op and its arguments (all read-only), the migration of a free-text playbook, the item, the gate; then the
    write, a compare-and-swap, and the client's quiet note. A refusal writes nothing, except the migration, which changes no word."""

    def __init__(
        self, agents: AgentDirectory, catalog: ServiceCatalog, texts: PlaybookTexts, playbooks: PlaybookWriter, delivery: MessageDelivery,
        evidence: ServiceEvidence, mail: MailboxReader, settler: WatchSettlement, *, splitters: Sequence[Splitter] = SPLITTERS,
    ) -> None:
        self._settler = settler
        self._splitters = splitters
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
            return self._change(call, self._settled(call, book))
        except OrgError:
            if book.migrated is not None:  # the migration stays written: the client is told of it on its own
                self._delivery.notify(client, f"playbook of {service}: v{book.migrated} (items)", f"{book.alone} Nothing else changed.", wake=False)
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
        migration changes no word, so it stays written when the op is refused). A file in item form that no longer parses (a hand edit of
        ``services/**``) is treated like a free text: its words become new items with ids after the highest one used, so no id is reused and the
        old ids read retired; the watches of the lines that were left alone are carried by the watch, by text key."""
        version = current.version
        if not version:
            return _Book(0, (), (), 0)
        if current.items is not None:
            return _Book(version, current.items, current.sections, current.items_max)
        migration = migrate_body(current.body, splitters=self._splitters)
        if current.parse_error:
            fix = repair_of(migration, version, current.items_max, current.parse_error)
            items, sections, top, reason = fix.items, fix.sections, fix.top, fix.reason
            note, alone, reply = fix.note, fix.alone, fix.reply
        else:
            items, sections = migration.items, migration.sections
            count = top = len(items)
            span = f"P{items[0].id[1:]}-{items[-1].id}" if count else "no items"
            reason = f"the free-text v{version} as {count} items (no change of words)" + migration.reason
            note = f"the free text of v{version} as {count} items ({span}), no change of words{migration.reason}."
            alone = f"The free text of v{version} as {count} items ({span}), no change of words{migration.reason}."
            reply = f"playbook v{version + 1} is the free-text v{version} as {count} items ({span}, no change of words{migration.reason}). "
        extra = item_extra(items, top, "migrate", admitted="migrate")
        body = checked_body(items, sections, extra)
        try:
            self._playbooks.write(call.actor, call.service, version + 1, body, RUNTIME_MIGRATION, reason, version, extra)
        except PlaybookRace as race:
            raise OrgError(PB_RACE.format(service=call.service, n=race.current)) from race
        return _Book(version + 1, items, sections, top, version + 1, note, alone, reply)

    # ------------------------------------------------------------------------------------------------------ step 3: the watch settler (8.5)

    def _settled(self, call: _Call, book: _Book) -> _Book:
        """A retire that is due is written first (``strict``: a write that races refuses the op with PB-RACE, any other failure propagates), on the
        migrated body when step 2 wrote one, so a hand-broken file cannot hold a due retire back. The op then judges the playbook as the settler left it."""
        try:
            report = self._settler.settle(call.actor, call.service, None, strict=True)
        except PlaybookRace as race:
            raise OrgError(PB_RACE.format(service=call.service, n=race.current)) from race
        if not report.retired:
            return book
        current = self._read(call.service, lambda: self._catalog.read_playbook(call.actor, call.service))
        return replace(book, version=current.version, items=current.items or (), sections=current.sections, items_max=current.items_max, retired_now=report.retired)

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
        """PB-ITEM: the item is not live; the live and the retired ids are listed. An id the watch retired is marked, and, when step 3 of this call
        wrote that retire, the refusal says so first (B7)."""
        live = [i.id for i in book.items]
        gone = [f"P{n}" for n in range(1, book.items_max + 1) if f"P{n}" not in live]
        by_watch = self._by_watch(call) if gone else {}
        listed = [PB_ITEM_WATCHED.format(id=g, n=by_watch[g][0]) if g in by_watch else g for g in gone]
        lead = ""
        if call.item in book.retired_now and call.item in by_watch:
            n, rejections = by_watch[call.item]
            lead = PB_ITEM_LEAD.format(id=call.item, n=n, rejections=", ".join(rejections))
        return PB_ITEM.format(
            lead=lead, service=call.service, id=call.item, ids=", ".join(live) or "none yet",
            retired=PB_ITEM_RETIRED.format(ids=", ".join(listed)) if gone else "",
        )

    def _by_watch(self, call: _Call) -> dict[str, tuple[int, tuple[str, ...]]]:
        """The ids whose latest removal from the body was the watch's retire, with the version of it and the rejections it rested on (B7): an id
        that is live again, or that its owner retired later, is not one."""
        versions = [v for v in self._read(call.service, lambda: self._catalog.playbook_versions(call.actor, call.service)) if v.items is not None]
        out: dict[str, tuple[int, tuple[str, ...]]] = {}
        for earlier, v in zip(versions, versions[1:]):
            now = {i.id for i in v.items or ()}
            for item_id in out.keys() & now:
                del out[item_id]
            for item_id in {i.id for i in earlier.items or ()} - now:
                if v.op == "watch" and v.item == item_id:
                    out[item_id] = (v.version, v.related)
                else:
                    out.pop(item_id, None)
        return out

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
        self._limits(call, book, items, sections, admission)
        self._watched_out(call, text, admission)
        path = self._write(call, book, items, sections, book.items_max + 1, admission, item=new.id)
        change = PlaybookChange(
            book.version + 1, "add", new.id, call.kind, admission, None, len(items), client=call.client,
        )
        change = self._with_watch(call, change)
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
        if not formatting:
            self._limits(call, book, items, book.sections, admission)
            self._watched_out(call, text, admission)
            call = self._guarded(call, book, old, new, admission.why)
        path = self._write(call, book, items, book.sections, book.items_max, admission, item=old.id)
        change = PlaybookChange(book.version + 1, "edit", old.id, old.kind, admission, None, len(items), formatting=formatting, client=call.client)
        if not formatting:
            change = self._with_watch(call, change)
        what = f"fixed the formatting of {old.id}" if formatting else f"edited {old.id}"
        return self._told(call, book, path, change, what, _item_line(new))

    def _retire(self, call: _Call, book: _Book, old: PlaybookItem) -> PlaybookChange:
        items, sections = without(book.items, book.sections, old)
        admission = Admission("exempt", (), EXEMPT)
        call = self._guarded(call, book, old, None, ())
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
        self._limits(call, book, items, sections, admission)
        self._watched_out(call, old.text, admission)
        if live is not None:  # a restore of a retired item replaces no live text: it lowers no bar
            call = self._guarded(call, book, live, restored, self._refs(restored), restored_from=source)
        path = self._write(call, book, items, sections, book.items_max, admission, item=call.item, restores=source)
        change = PlaybookChange(
            book.version + 1, "restore", call.item, old.kind, admission, None, len(items), restored_from=source, client=call.client,
        )
        change = self._with_watch(call, change)
        return self._told(call, book, path, change, f"restored {call.item} to the text of v{source}", _item_line(restored))

    def _written_by(self, versions: Sequence[Playbook], held: Mapping[int, PlaybookItem], source: int) -> str:
        """Who wrote the text the item had in version ``source``: the author of the first version of the unbroken run that holds exactly that text
        (the version before it, when that one is the migration: the migration changed no word)."""
        start = self._run_start(held, source)
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

    # ------------------------------------------------------------------------------------------------------ the parent's acknowledgement (9)

    @staticmethod
    def _refs(item: PlaybookItem) -> tuple[str, ...]:
        """The ids a text stands on (3): its ``WHY`` entry when it has one (a gated item), else the ``C<k>`` and ``R<k>`` in its words."""
        return item.why or tuple(dict.fromkeys(REF.findall(f"{item.text} {item.when}")))

    def _covered(self, call: _Call, item: str) -> tuple[str, ...]:
        """What ``item`` covers now (its ``ItemWatch.coverage``). A watch that cannot be read refuses the op, as an unreadable record does everywhere
        else in this class: a guard that could not be judged is not skipped."""
        try:
            found = self._evidence.watch(call.actor, call.service)
        except (OrgError, OSError) as error:
            raise OrgError(PB_UNREADABLE.format(service=call.service, error=error)) from error
        return next((w.coverage for w in found if w.id == item), ())

    def _guarded(
        self, call: _Call, book: _Book, old: PlaybookItem, new: PlaybookItem | None, refs: Sequence[str], *, restored_from: int = 0,
    ) -> _Call:
        """The guard (9.1), last in step 5: retiring an item with coverage, or replacing its live text (``new``; its ``refs`` are the ids the new text
        stands on) with one that drops a covered id or only deletes words, needs the parent's acknowledgement. Without ``acknowledged``: PB-ACK; with
        one: it is checked (PB-ACK-BAD) and the call carries it, so the version records it. A change that needs none is returned as it is."""
        covered = self._covered(call, old.id)
        if not covered:
            return call
        dropped = [i for i in covered if new is not None and i not in refs]
        if new is not None and not weakening(old, new, covered, refs):
            return call
        op = "retire" if new is None else "edit"
        stored = text_hash(new.kind, new.text, new.when) if new is not None else ""
        if call.acknowledged is None:
            raise OrgError(self._ack_request(call, old, new, covered, dropped, stored, restored_from))
        return replace(call, used=self._acknowledgement(call, book, old, f"{call.service} {op} {old.id}" + (f" {stored}" if stored else "")))

    @staticmethod
    def _ack_request(
        call: _Call, old: PlaybookItem, new: PlaybookItem | None, covered: Sequence[str], dropped: Sequence[str], stored: str, restored_from: int,
    ) -> str:
        """PB-ACK (9.2): why the change lowers the bar, the question to send the parent once and the call that answers it."""
        how = PB_ACK_DROPS.format(ids=and_ids(dropped)) if dropped else PB_ACK_DELETES
        if new is None:
            change, ask = PB_ACK_RETIRE, PB_ACK_ASK["retire"]
        elif call.op == "restore":
            change, ask = PB_ACK_RESTORE.format(k=restored_from, how=how), PB_ACK_ASK["restore"].format(k=restored_from)
        else:
            change, ask = PB_ACK_EDIT.format(how=how), PB_ACK_ASK["edit"]
        return PB_ACK.format(
            id=old.id, ids=", ".join(covered), change=change, parent=call.client, ask=ask, service=call.service, reason=clip_line(call.reason, LINE_CLIP),
            owner=call.actor, op="retire" if new is None else "edit", hash=PB_ACK_HASH.format(hash=stored) if stored else "",
            words=PB_ACK_WORDS if call.client == ROOT else "",
        )

    def _acknowledgement(self, call: _Call, book: _Book, item: PlaybookItem, expected: str) -> str:
        """The acknowledgement ``call.acknowledged`` names, checked (9.2): it is in the owner's received mail, from its parent, for this very change
        (``expected``: ``{service} {op} {item}`` and, for an edit or a restore, the hash of the new text), written after the item's current text went
        live, not cited by any stored version and, for root, the user's (``source: human``). Returns its id; PB-ACK-BAD names the condition that fails."""
        ack = (call.acknowledged or "").strip()
        if not MESSAGE_ID.fullmatch(ack):
            raise self._args_error(call, ACK_NOT_AN_ID.format(x=ack))

        def bad(failed: str) -> OrgError:
            return OrgError(PB_ACK_BAD.format(id=ack, parent=call.client, failed=failed))

        note = self._read(call.service, lambda: self._mail.find_received(call.actor, ack))
        if note is None:
            raise bad(PB_ACK_MISSING)
        if note.sender != call.client:
            raise bad(PB_ACK_SENDER.format(parent=call.client))
        header, wanted = (note.acknowledges or "").split(), expected.split()
        if header[:3] != wanted[:3]:
            what = f"{header[1]} {header[2]} of {header[0]}" if len(header) >= 3 else ""
            raise bad(PB_ACK_OTHER.format(what=what) if what else PB_ACK_NOT_ONE)
        if header[3:] != wanted[3:]:
            raise bad(PB_ACK_TEXT.format(hash=header[3] if len(header) > 3 else "none"))
        versions = self._read(call.service, lambda: self._catalog.playbook_versions(call.actor, call.service))
        held = {p.version: i for p in versions if p.items is not None for i in p.items if i.id == item.id}
        live = next((p.revised for p in versions if p.version == self._run_start(held, book.version)), None)
        sent = stamp_of(note.id)
        if live is not None and sent is not None and sent <= live:
            raise bad(PB_ACK_OLD.format(item=item.id))
        used = next((p.version for p in versions if p.acknowledged == ack), None)
        if used is not None:
            raise bad(PB_ACK_USED.format(k=used))
        if call.client == ROOT and note.source != "human":
            raise bad(PB_ACK_USER)
        return ack

    def _watched_out(self, call: _Call, text: str, admission: Admission) -> None:
        """PB-WATCHED-OUT (8.6, B2): an add, a gated edit (of any live item) or a restore whose text key is the key of a text the watch retired, or of
        a text its owner retired while its watch retire was due, is refused while at least 2 of that retire's rejections are still related (a corrected
        link can undo the relation), unless a rule-(c) admission rests on a criterion the user confirmed after that retire. A rule's key is that of its
        ``then``, so a rule re-added as a step is caught."""
        key = line_key(text)
        versions = self._read(call.service, lambda: self._catalog.playbook_versions(call.actor, call.service))
        retires = [(k, v) for k, v in enumerate(versions) if v.op in ("watch", "retire") and v.item and v.items is not None]
        if not key or not retires:
            return
        try:
            watches = {w.id: w for w in self._evidence.watch(call.actor, call.service)}
        except (OrgError, OSError):
            watches = {}
        for k, v in retires:
            before = next((p for p in reversed(versions[:k]) if p.items is not None), None)
            gone = next((i for i in (before.items if before and before.items else ()) if i.id == v.item), None)
            if gone is None or line_key(gone.text) != key or v.item not in watches:
                continue
            related = set(watches[v.item].related)
            still = sorted(related & set(v.related)) if v.op == "watch" else sorted(related)
            if len(still) < 2:
                continue
            confirmed = stamp_of(admission.confirmed) if admission.rule == "c" and admission.confirmed else None
            if confirmed is not None and v.revised is not None and confirmed > v.revised:
                continue
            raise OrgError(PB_WATCHED_OUT.format(
                id=gone.id, how=THE_WATCH if v.op == "watch" else YOU_WHILE_DUE, n=v.version, rejections=and_ids(still),
                ids=", ".join(gone.why or ()) or "nothing", client=call.client, service=call.service, first=clip_line(gone.text, WATCH_TEXT_CLIP),
            ))

    def _with_watch(self, call: _Call, change: PlaybookChange) -> PlaybookChange:
        """The watch of the item that was just written, read once more from the files (one definition of a carried watch, ``reflection``): the id it
        continues and the rejections it holds. A read that fails after the write leaves the change as it is, and the reply says where the states are."""
        try:
            found = {w.id: w for w in self._evidence.watch(call.actor, call.service)}
        except (OrgError, OSError):
            return replace(change, watch_unread=True)
        mine = found.get(change.item)
        if mine is None:
            return change
        old = found.get(mine.carried) if mine.carried else None
        return replace(change, carried=mine.carried, related=mine.related, carried_related=old.related if old is not None else ())

    def _limits(
        self, call: _Call, book: _Book, items: Sequence[PlaybookItem], sections: Sequence[PlaybookSection], admission: Admission,
    ) -> None:
        """Step 5 after the gate (design 7, 10): the 30% rule (not for a (c) admission: a criterion's words cannot be split), then the cap, counted
        in content words so that the markers never push a playbook over."""
        if admission.rule != "c":
            split_check(content_tokens(book.items, _headings(book.sections)), content_tokens(items, _headings(sections)))
        words = content_words(items, _headings(sections))
        cap = self._texts.cap()
        if words > cap:
            raise OrgError(self._cap_error(call, book, words, cap))

    def _cap_error(self, call: _Call, book: _Book, words: int, cap: int) -> str:
        """PB-CAP with its two lists (10): the new items whose watch rests on no regression assertion, and the oldest items that cover nothing. The
        watch is read once; an unreadable watch only shortens the lists (every item then counts as uncovered, since the version that gave it its text)."""
        versions = self._read(call.service, lambda: self._catalog.playbook_versions(call.actor, call.service))
        try:
            watches = {w.id: w for w in self._evidence.watch(call.actor, call.service)}
        except (OrgError, OSError):
            watches = {}
        held = {i.id: {p.version: x for p in versions if p.items is not None for x in p.items if x.id == i.id} for i in book.items}
        for i in book.items:  # an item the watch does not know: the version that gave it its current text
            watches.setdefault(i.id, ItemWatch(i.id, i.kind, "kept", self._run_start(held[i.id], max(held[i.id], default=book.version))))
        by_version = {p.version: p for p in versions}
        started = {
            i.id: by_version[watches[i.id].text_version].why[i.id] for i in book.items
            if watches[i.id].text_version in by_version and i.id in by_version[watches[i.id].text_version].why
        }
        candidates, uncovered = cap_lists(book.items, watches, started, book.version)
        return cap_refusal(words, cap, candidates, uncovered, call.client)

    @staticmethod
    def _run_start(held: Mapping[int, PlaybookItem], source: int) -> int:
        """The first version of the unbroken run, ending at ``source``, in which the item has exactly the text it has in ``source``."""
        text = (held[source].text, held[source].when) if source in held else None
        start = source
        while text is not None and start - 1 in held and (held[start - 1].text, held[start - 1].when) == text:
            start -= 1
        return start

    def _write(
        self, call: _Call, book: _Book, items: Sequence[PlaybookItem], sections: Sequence[PlaybookSection], items_max: int, admission: Admission, *,
        item: str = "", reason: str = "", restores: int = 0,
    ) -> str:
        """The round-trip assertion (4.1), then the write: a compare-and-swap against the version this call judged (4.3)."""
        extra = item_extra(
            items, items_max, call.op, evidence=list(admission.evidence), admitted=admission.rule, item=item, restores=restores, acknowledged=call.used,
        )
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
        ignored = (call.acknowledged or "") if call.op in ("edit", "retire", "restore") and not call.used else ""
        return replace(change, migrated=book.migrated, migration=book.reply, acknowledged=call.used, ack_ignored=ignored)
