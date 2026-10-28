#!/usr/bin/env python3
"""P1 independent re-derivation of the watch and of the spend figures (Phase 1 design 18.6; F-G0-4).

Written from the design TEXT only: `docs/design/org-growth-phase-1.md` sections 3 (definitions), 4.1-4.2 (the item file), 8 (the watch) and
24 (B1-B4), with the record formats and numbering rules of the 0a/0a.2 texts (3.3 criterion ids, 3.4 `R<k>`, the link and contract
frontmatter) and the 0b/0b.1 texts (case, delivery, verdict on a delivery, counted verdict, judged; `case_spend`, `user_spend`,
`user_committed`, `user_approved`). The author did NOT open `src/hirearchy/` while writing it (harness/CHANGES.md says so); the file
formats were read from the kept G0 and E7 evidence and from the design. It imports no product code; it needs Python 3.11 and PyYAML
(the system python3's, a third-party parser, not the product's).

    python3 -B rederive_watch.py <stream dir> --out <dir>
        re-derives every item of the study service as of every snapshot (quality/calls.txt and services/calls.txt give each snapshot's
        start and end, with microseconds), compares it with the product's `watch` list of quality/<tag>.json on the 11 keys of 14.4 and
        with the watch suffix of root's `services` listing (services/<tag>.txt, 14.3), and writes <out>/watch-rederived.json,
        <out>/watch-mismatches.txt and <out>/watch-items.txt (judged(c), E, D, K, the window and the warned window per item, reported,
        never compared). A key matches when it equals the re-derivation at the snapshot's start, at its end, or at any record time between
        them (protocol 12.1 G1(f): the org keeps writing during a snapshot); a key that matches only the re-derivation at a time in
        [start - 5 s, start) (a record stamped just before the snapshot but written after the product read it) is `RACE-LOWER`, reported,
        not a mismatch. Each mismatch line says whether the design pins that key for the item's state (`pinned`: every key of a `new` or
        `warning` item; `item`, `kind`, `state` of every item; `related` of a `kept` or `retired` one; `k`, `r` and `since` of an item never
        watched, 25.2 item 14) or not (`unpinned`). A snapshot whose calls.txt line has an exit code other than 0, or whose output file is
        missing, empty or (quality) not valid JSON, or a turn of turn-times.txt with no calls.txt line at all, is unread: `UNREAD <tag>
        <kind>: <reason>` (and `traceback through the product` when its stderr file shows one). Lines: `MISMATCH <tag> <item> <key>
        pinned|unpinned: ...`, `MISSING <tag>: ...`, `SERVICES-MISMATCH <tag> <item> <key>: ...`, `SERVICES-UNREAD <tag>: <line>`,
        `RACE-LOWER <tag> <item> <key>: ...`, `UNREAD <tag> <kind>: ...`; the last line counts them.
    python3 -B rederive_watch.py --spend <ledger.json> [--quality <end.json>] [--stream <stream dir>] --out <dir>
        the spend figures from a hand ledger (G0's "D14" ledger of Lena's approvals plus the per-case facts read by hand from the files),
        by 0b.1 3.2's arithmetic; compared with the product's `user_cost`, `spend` and approval when --quality is given; with --stream, the
        service's cases are read from the stream's mail and `missing_cases` (in the mail, not in the ledger) and `extra_cases` (in the
        ledger, not in the mail) are written beside the figures (protocol 6.3).

Readings this file takes where the text leaves an implementation choice open (each stated in protocol.md section 13.4):
  * times: a message's time is its id's stamp (`20261026T055114787042` = 2026-10-26 05:51:14.787042 UTC); a contract version's is its
    `defined`; a playbook version's is its `revised`; all compared as aware datetimes; at an equal microsecond a contract version comes
    before a message (B3).
  * "after the live-from" is strict for a candidate's done result and for judged(c); "at or after the watch start" for the window (3).
  * a verdict is on a delivery when it replies to the delivery's task and its id is greater than the delivery's result id (0b 3).
  * v1 adds no criterion for lineage (3: "a v1 criterion never removed and re-added ... has none"); answer_ids = the ids a version added,
    else the ids it removed (0a.2); the ids a version removes are subjects too.
  * tiers (0a 3.1): a root note without `source` is `human` (the legacy reading), `source: human` is human, any other value `relayed`.
  * refs (3): an R<k>'s `Assertion.about` keeps only the criteria current when the text went live (the latest contract version defined at
    or before the live-from).
  * carried watch (ii) (3, 4.4): an item of a repair migration (op migrate after a version that does not parse) whose text key equals the
    text key of an item live and in its watch in the last parseable version, rendered as `[P<k>] <its line>` without its list marker,
    continues that watch (same start, changes and refs; W1 makes its text the watched text from the repair on).
  * a contract version's time is its `defined` (B3); a version above 1 without `defined` stops the run with an error naming its file (B3:
    "never the contract's `created`"); v1 alone may fall back to `created` (the service's creation is v1's definition).
  * strip_markers (section 3 names the product's function, not its pattern): a leading run of Markdown list or heading markers,
    `^\\s*(?:#{1,6}\\s+|[-*+•]\\s+|\\d+[.)]\\s+|\\[[ xX]\\]\\s+)+` (_MARKER), is dropped from each continuation line (the second and later
    lines, which only migrated items have, 4.4) before its tokens are read, and from the start of a text before its text key is taken;
    an item's first line keeps its leading symbols as tokens (section 3). Its rows (`   - sub` -> `   1. sub`, `   ## Sub` -> `   Sub`)
    are formatting, as section 3's unit rows say.
"""
from __future__ import annotations

import json
import math
import re
import sys
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    import yaml  # PyYAML (system python3); not the product
except ImportError:  # pragma: no cover
    yaml = None

UTC = timezone.utc
ROOT = "root"
STAMP = re.compile(r"^(\d{8})T(\d{6})(\d{6})")


# ------------------------------------------------------------------------------------------------------------------ time
def stamp_of(msg_id: str) -> datetime:
    m = STAMP.match(msg_id)
    if not m:
        raise ValueError(f"not a message id: {msg_id}")
    d, t, us = m.groups()
    return datetime(int(d[:4]), int(d[4:6]), int(d[6:8]), int(t[:2]), int(t[2:4]), int(t[4:6]), int(us), tzinfo=UTC)


def parse_time(v) -> datetime | None:
    if v is None or v == "":
        return None
    if isinstance(v, datetime):
        return v if v.tzinfo else v.replace(tzinfo=UTC)
    s = str(v).strip().replace("Z", "+00:00")
    d = datetime.fromisoformat(s)
    return d if d.tzinfo else d.replace(tzinfo=UTC)


def iso(d: datetime | None) -> str | None:
    return None if d is None else d.astimezone(UTC).isoformat()


# ------------------------------------------------------------------------------------------------------------------ records
@dataclass(frozen=True)
class Task:
    id: str
    service: str
    to: str
    revises: str = ""
    source: str = ""
    budget: int = 0
    title: str = ""
    inputs: str = ""

    @property
    def t(self) -> datetime:
        return stamp_of(self.id)


@dataclass(frozen=True)
class Result:
    id: str
    task: str
    status: str

    @property
    def t(self) -> datetime:
        return stamp_of(self.id)


@dataclass(frozen=True)
class Verdict:
    id: str
    task: str
    verdict: str  # accept | reject
    tier: str  # human | relayed | agent

    @property
    def t(self) -> datetime:
        return stamp_of(self.id)


@dataclass(frozen=True)
class Link:
    id: str
    rejection: str
    ids: tuple[str, ...]
    tier: str

    @property
    def t(self) -> datetime:
        return stamp_of(self.id)


@dataclass(frozen=True)
class Contract:
    version: int
    defined: datetime
    acceptance: tuple[str, ...]
    defined_by: str = ROOT
    answers: str = ""
    about: str = ""
    words: str = ""
    initiated: str = ""
    locked: bool = False

    @property
    def t(self) -> datetime:
        return self.defined


@dataclass(frozen=True)
class Item:
    id: str
    kind: str  # step | rule
    text: str
    when: str = "always"
    section: str = ""

    def tokens(self) -> tuple[str, ...]:
        return tuple(text_tokens(self.text)) + (tuple(text_tokens(self.when)) if self.kind == "rule" else ())

    def key(self) -> str:
        return line_key(self.text)


@dataclass(frozen=True)
class PVersion:
    version: int
    revised: datetime
    by: str
    op: str
    item: str = ""
    admitted: str = ""
    items: tuple[Item, ...] | None = None  # None: legacy (no items_max) or unparseable
    why: dict = field(default_factory=dict)
    related: tuple[str, ...] = ()
    restores: int = 0
    parse_error: str = ""
    legacy: bool = False

    @property
    def t(self) -> datetime:
        return self.revised

    def live(self) -> dict[str, Item]:
        return {i.id: i for i in (self.items or ())}


@dataclass
class World:
    service: str
    owner: str
    client: str = ROOT
    created: datetime | None = None
    tasks: list[Task] = field(default_factory=list)
    results: list[Result] = field(default_factory=list)
    verdicts: list[Verdict] = field(default_factory=list)
    links: list[Link] = field(default_factory=list)
    contracts: list[Contract] = field(default_factory=list)
    playbooks: list[PVersion] = field(default_factory=list)

    def as_of(self, t: datetime | None) -> "World":
        if t is None:
            return self
        return World(self.service, self.owner, self.client, self.created,
                     [x for x in self.tasks if x.t <= t], [x for x in self.results if x.t <= t],
                     [x for x in self.verdicts if x.t <= t], [x for x in self.links if x.t <= t],
                     [x for x in self.contracts if x.t <= t], [x for x in self.playbooks if x.t <= t])

    def before(self, t: datetime) -> "World":
        """Records created strictly before t (8.4: the data as it stood at the watch start)."""
        return World(self.service, self.owner, self.client, self.created,
                     [x for x in self.tasks if x.t < t], [x for x in self.results if x.t < t],
                     [x for x in self.verdicts if x.t < t], [x for x in self.links if x.t < t],
                     [x for x in self.contracts if x.t < t], [x for x in self.playbooks if x.t < t])

    def as_of_b3(self, t: datetime) -> "World":
        """B3's order at an equal microsecond: the contract versions (and playbook versions) up to and including t, the messages strictly
        before t (a contract version comes before the link note define_service writes after it)."""
        return World(self.service, self.owner, self.client, self.created,
                     [x for x in self.tasks if x.t < t], [x for x in self.results if x.t < t],
                     [x for x in self.verdicts if x.t < t], [x for x in self.links if x.t < t],
                     [x for x in self.contracts if x.t <= t], [x for x in self.playbooks if x.t <= t])

    def record_times(self) -> list[datetime]:
        """Every record's creation time (messages, contract versions, playbook versions), sorted, distinct."""
        ts = [x.t for x in self.tasks] + [x.t for x in self.results] + [x.t for x in self.verdicts] + [x.t for x in self.links]
        ts += [c.defined for c in self.contracts if c.defined] + [p.revised for p in self.playbooks if p.revised]
        return sorted(set(ts))


# ------------------------------------------------------------------------------------------------------------------ text (section 3)
TOKEN = re.compile(r"\d+(?:[.,:/-]\d+)*|[^\W\d_]+|[^\w\s.,;:!?'\"()\[\]*_`]")
_MARKER = re.compile(r"^\s*(?:#{1,6}\s+|[-*+•]\s+|\d+[.)]\s+|\[[ xX]\]\s+)+")


def strip_markers(line: str) -> str:
    return _MARKER.sub("", line)


def plain(line: str) -> str:
    return re.sub(r"^\s*#+", "", line.replace("~~", ""))


def text_tokens(t: str) -> list[str]:
    return [tok for i, line in enumerate((t or "").splitlines())
            for tok in TOKEN.findall(plain(strip_markers(line) if i else line).casefold())]


def line_key(t: str) -> str:
    """The letters and digits of a text, case-folded, after its leading markdown markers (section 3, text key)."""
    return "".join(ch for ch in strip_markers(t or "").casefold() if ch.isalnum())


def id_num(x: str) -> int:
    m = re.search(r"(\d+)", x)
    return int(m.group(1)) if m else 0


def render_why(ids) -> str:
    rs = sorted({i for i in ids if i.upper().startswith("R")}, key=id_num)
    cs = sorted({i for i in ids if i.upper().startswith("C")}, key=id_num)
    return "; ".join(g for g in (", ".join(rs), ", ".join(cs)) if g)


ID_TOKEN = re.compile(r"\b([CR]\d+)\b")


# ------------------------------------------------------------------------------------------------------------------ the item file (4.1)
_HEAD = re.compile(r"^#{1,6}(\s|$)")
_ITEM = re.compile(r"^(?:\d+\. |- )\[P(\d+)\](?: (.*)|)$")


def parse_items(body: str, meta: dict) -> tuple[tuple[Item, ...] | None, str]:
    rules = {str(x).upper() for x in (meta.get("rules") or [])}
    why = {str(k).upper(): [str(v) for v in (vs or [])] for k, vs in (meta.get("why") or {}).items()}
    items: list[tuple[str, list[str], str]] = []
    section = ""
    pending_blank = 0
    lines = (body or "").replace("\r\n", "\n").split("\n")
    for n, line in enumerate(lines, 1):
        if _HEAD.match(line):
            section, pending_blank = line, 0
            continue
        m = _ITEM.match(line)
        if m:
            items.append(("P" + m.group(1), [m.group(2) or ""], section))
            pending_blank = 0
            continue
        if line.strip() == "":
            pending_blank += 1
            continue
        if line.startswith("   ") and items:
            items[-1][1].extend([""] * pending_blank)
            items[-1][1].append(line[3:])
            pending_blank = 0
            continue
        return None, f"line {n}: neither a heading, an item nor a continuation"
    out = []
    for iid, ls, sec in items:
        first = ls[0]
        w = why.get(iid)
        if iid in rules:
            if not first.startswith("WHEN ") or " THEN " not in first[5:]:
                return None, f"{iid}: a rule without WHEN ... THEN"
            when, then = first[5:].split(" THEN ", 1)
            if w:
                suf = " WHY " + render_why(w)
                if then.endswith(suf):
                    then = then[: -len(suf)]
            out.append(Item(iid, "rule", "\n".join([then] + ls[1:]), when, sec))
        else:
            text = "\n".join(ls)
            if w:
                suf = " (WHY " + render_why(w) + ")"
                if text.endswith(suf):
                    text = text[: -len(suf)]
            out.append(Item(iid, "step", text, "always", sec))
    return tuple(out), ""


def legacy_items(body: str) -> tuple[Item, ...]:
    """A legacy body as it would migrate (4.4's per-block split, simplified): its virtual items, all `kept` (8.7)."""
    blocks: list[list[str]] = []
    cur: list[str] | None = None
    fence = False
    for line in (body or "").replace("\r\n", "\n").split("\n"):
        if fence:
            cur.append(line)
            if line.strip().startswith("```"):
                fence = False
            continue
        if re.match(r"^#{1,6}(\s|$)", line):
            cur = None
            continue
        if line.strip() == "":
            cur = None if (cur is not None and not re.match(r"^\s*([-*+]|\d+[.)])\s", cur[0])) else cur
            continue
        if line.strip().startswith("```"):
            cur = [line]
            blocks.append(cur)
            fence = True
            continue
        if re.match(r"^([-*+]|\d+[.)])\s", line) or cur is None:
            cur = [line]
            blocks.append(cur)
        else:
            cur.append(line)
    return tuple(Item(f"P{i}", "step", strip_markers(b[0]) + ("\n" + "\n".join(b[1:]) if len(b) > 1 else ""))
                 for i, b in enumerate(blocks, 1))


# ------------------------------------------------------------------------------------------------------------------ criteria (0a 3.3)
def number_criteria(contracts: list[Contract]) -> tuple[dict[str, str], dict[int, list[str]]]:
    """text -> id, and version -> the ids of its acceptance in order (the first time a text is seen it gets the next id)."""
    ids: dict[str, str] = {}
    per: dict[int, list[str]] = {}
    for c in sorted(contracts, key=lambda c: c.version):
        row = []
        for text in c.acceptance:
            if text not in ids:
                ids[text] = f"C{len(ids) + 1}"
            row.append(ids[text])
        per[c.version] = row
    return ids, per


class Criteria:
    def __init__(self, contracts: list[Contract]):
        self.contracts = sorted(contracts, key=lambda c: c.version)
        self.ids, self.per = number_criteria(self.contracts)
        self.by_version = {c.version: c for c in self.contracts}

    def added(self, v: int) -> list[str]:
        if v not in self.per or (v - 1) not in self.per:
            return []
        prev = set(self.per[v - 1])
        return [i for i in self.per[v] if i not in prev]

    def removed(self, v: int) -> list[str]:
        if v not in self.per or (v - 1) not in self.per:
            return []
        now = set(self.per[v])
        return [i for i in self.per[v - 1] if i not in now]

    def answer_ids(self, v: int) -> list[str]:
        return self.added(v) or self.removed(v)

    def current(self) -> set[str]:
        return set(self.per[self.contracts[-1].version]) if self.contracts else set()

    def current_at(self, t: datetime) -> set[str]:
        """The criteria of the latest contract version defined at or before t."""
        cs = [c for c in self.contracts if c.defined <= t]
        return set(self.per[max(cs, key=lambda c: (c.defined, c.version)).version]) if cs else set()

    def readded(self, v: int) -> list[str]:
        """The ids version v added whose text an earlier version already had (number_criteria gives a text that comes back its first id)."""
        earlier = {i for c in self.contracts if c.version < v - 1 for i in self.per.get(c.version, [])}
        return [i for i in self.added(v) if i in earlier]

    def answering(self, rejection_id: str) -> Contract | None:
        for c in self.contracts:
            if c.answers == rejection_id:
                return c
        return None

    def lineage(self, cid: str, t: datetime, seen: set[str] | None = None) -> set[str]:
        """Section 3, B4: the criteria removed by the latest version defined at or before t that added cid's text, and theirs."""
        seen = set() if seen is None else seen
        seen.add(cid)
        cands = [c for c in self.contracts if c.defined <= t and cid in self.added(c.version)]
        if not cands:
            return set()
        v = max(cands, key=lambda c: (c.defined, c.version)).version
        out: set[str] = set()
        for r in self.removed(v):
            if r in seen:
                continue
            out.add(r)
            out |= self.lineage(r, t, seen)
        return out


# ------------------------------------------------------------------------------------------------------------------ cases (0b 3)
class Mail:
    def __init__(self, w: World):
        self.w = w
        self.tasks = {t.id: t for t in w.tasks if t.service == w.service and t.to == w.owner
                      and (w.created is None or t.t >= w.created)}
        self.head: dict[str, str] = {}
        for tid in sorted(self.tasks):
            t, seen = self.tasks[tid], set()
            while t.revises and t.revises in self.tasks and t.revises not in seen and self.tasks[t.revises].to == t.to:
                seen.add(t.id)
                t = self.tasks[t.revises]
            self.head[tid] = t.id
        self.results_of: dict[str, list[Result]] = {}
        for r in sorted(w.results, key=lambda r: r.id):
            if r.task in self.tasks:
                self.results_of.setdefault(r.task, []).append(r)
        self.verdicts = sorted((v for v in w.verdicts if v.task in self.tasks), key=lambda v: v.id)
        self.links = sorted(w.links, key=lambda x: x.id)
        self.crit = Criteria(w.contracts)
        rej = [v for v in self.verdicts if v.verdict == "reject" and v.tier == "human"]
        self.rid = {v.id: f"R{i}" for i, v in enumerate(rej, 1)}
        self.by_id = {v.id: v for v in rej}
        self.by_rid = {r: self.by_id[v] for v, r in self.rid.items()}
        self.rejections = rej

    def case_of(self, task_id: str) -> str:
        return self.head.get(task_id, "")

    def tasks_of(self, case: str) -> set[str]:
        return {t for t, hd in self.head.items() if hd == case}

    def cases(self) -> list[str]:
        return sorted(set(self.head.values()))

    def deliveries(self, case: str) -> list[tuple[Task, Result]]:
        out = []
        for tid, t in self.tasks.items():
            if self.head[tid] != case:
                continue
            rs = self.results_of.get(tid) or []
            if rs and rs[-1].status == "done":
                out.append((t, rs[-1]))
        return sorted(out, key=lambda d: d[1].id)

    def verdicts_on(self, task: Task, result: Result) -> list[Verdict]:
        return [v for v in self.verdicts if v.task == task.id and v.id > result.id]

    def rejected_result(self, rej: Verdict) -> Result | None:
        rs = [r for r in self.results_of.get(rej.task) or [] if r.id < rej.id]
        return rs[-1] if rs else None

    def human_links(self, rej_id: str) -> list[Link]:
        return [x for x in self.links if x.rejection == rej_id and x.tier == "human"]

    # --- pending, answer time, subjects (section 3)
    def pending(self, rej_id: str, seen: set[str] | None = None) -> bool:
        seen = set() if seen is None else seen
        if rej_id in seen:
            return False
        seen.add(rej_id)
        links = self.human_links(rej_id)
        if not links and self.crit.answering(rej_id) is None:
            return True
        if links:
            for i in links[-1].ids:
                if i.upper().startswith("R") and i.upper() in self.by_rid and self.pending(self.by_rid[i.upper()].id, seen):
                    return True
        return False

    def answered(self, rej_id: str) -> bool:
        """Clause 2's notion (13): a human link (any, "same as" included) or an answering version."""
        return bool(self.human_links(rej_id)) or self.crit.answering(rej_id) is not None

    def answer_time(self, rej_id: str) -> datetime | None:
        links = self.human_links(rej_id)
        v = self.crit.answering(rej_id)
        if len(links) >= 2:
            return links[-1].t  # a corrected link: that link's time
        times = [x.t for x in links[:1]] + ([v.defined] if v else [])
        return min(times) if times else None

    def subjects(self, rej_id: str, seen: set[str] | None = None) -> set[str]:
        rid = self.rid.get(rej_id, "")
        if self.pending(rej_id):
            return {rid}
        seen = set() if seen is None else seen
        seen.add(rej_id)
        out = {rid}
        links = self.human_links(rej_id)
        if links:
            for i in links[-1].ids:
                i = i.upper()
                if i == "NONE":
                    continue
                out.add(i)
                if i.startswith("R") and i in self.by_rid and self.by_rid[i].id not in seen:
                    out |= self.subjects(self.by_rid[i].id, seen)
        v = self.crit.answering(rej_id)
        if v is not None:
            if v.about:
                out.add(v.about.upper())
            out |= set(self.crit.answer_ids(v.version)) | set(self.crit.removed(v.version))
        t = self.answer_time(rej_id)
        for c in [x for x in out if x.startswith("C")]:
            out |= self.crit.lineage(c, t)
        return out

    def about_before(self, rid: str, t: datetime) -> set[str]:
        """The C ids an assertion R<k> was about over the human links created before t (refs of a text, section 3), kept only when they
        are criteria current at t (0a's `Assertion.about` holds current criteria only)."""
        rej = self.by_rid.get(rid)
        if rej is None:
            return set()
        links = [x for x in self.human_links(rej.id) if x.t < t]
        if not links:
            return set()
        cur = self.crit.current_at(t)
        out = set()
        for i in links[-1].ids:
            i = i.upper()
            if i.startswith("C"):
                if i in cur:
                    out.add(i)
            elif i.startswith("R") and i != rid:
                out |= self.about_before(i, t)
        return out


# ------------------------------------------------------------------------------------------------------------------ item history
_EPS = timedelta(microseconds=1)
_FAR = datetime(2100, 1, 1, tzinfo=UTC)


@dataclass(frozen=True)
class Text:
    """One text of an item (pass 1): the version that gave it, its live-from, whether that change was gated (section 3)."""
    item: str
    version: int
    live_from: datetime
    obj: Item
    why: tuple[str, ...]
    gated: bool
    op: str  # the version's op as it touched this item: add|edit|restore|first|migrate|watch|other
    client_restore: bool = False  # an exempt restore of a client-written text (W2 when in a watch)


def refs_of(text: Text, mail: "Mail") -> set[str]:
    if text.why:
        ids = {i.upper() for i in text.why}
    else:
        ids = {m.upper() for m in ID_TOKEN.findall(text.obj.text + " " + (text.obj.when or ""))}
    for r in [i for i in ids if i.startswith("R")]:
        ids |= mail.about_before(r, text.live_from)
    return ids


@dataclass
class Change:
    """A watched change (8.1): its live-from, the start of its window (the watch start for the first; its own live-from after a W2
    restart, section 3 'window'), its text and watched tokens (W1 keeps the change and replaces the tokens: `earlier` holds the tokens it
    had before each W1 change, with the time it ended), its `why`."""
    live_from: datetime
    start: datetime
    text: Text
    tokens: tuple[str, ...]
    earlier: list = field(default_factory=list)

    def tokens_at(self, t: datetime) -> tuple[str, ...]:
        for until, toks in self.earlier:
            if t < until:
                return toks
        return self.tokens


@dataclass
class Watch:
    item: str
    start: datetime
    changes: list[Change]
    carried: str = ""
    carried_watch: "Watch | None" = None
    carried_at: datetime | None = None  # when the carried watch's item left the body
    ended_at: datetime | None = None
    end_kind: str = ""
    alias: str = ""  # carried watch (ii): the id the watch had before a repair migration
    alias_until: datetime | None = None

    def key(self):
        return (self.item, self.start, len(self.changes), self.carried, self.ended_at)

    def id_at(self, t: datetime) -> str:
        return self.alias if self.alias and self.alias_until and t < self.alias_until else self.item


def rendered_key(it: Item, why) -> str:
    """The text key of an item's line as 4.1 renders it, with its `[P<k>]` marker and without its list marker (carried watch (ii), 4.4)."""
    w = f"{render_why(why)}" if why else ""
    lines = (it.text or "").split("\n")
    if it.kind == "rule":
        first = f"[{it.id}] WHEN {it.when} THEN {lines[0]}" + (f" WHY {w}" if w and len(lines) == 1 else "")
    else:
        first = f"[{it.id}] {lines[0]}" + (f" (WHY {w})" if w and len(lines) == 1 else "")
    return line_key("\n".join([first] + lines[1:]))


def item_texts(pbs: list[PVersion], client: str) -> dict[str, list[Text]]:
    """Pass 1: every text every item had, from the versions alone (no mail)."""
    out: dict[str, list[Text]] = {}
    ctexts: set[tuple[str, ...]] = set()
    prev: dict[str, Item] = {}
    broken = False  # the last version did not parse: a migration now is the repair migration (4.4)
    for p in pbs:
        if p.items is None:
            if p.legacy:
                prev = {}
            else:
                broken = True
            continue  # an unparseable version: readers skip it (25.2 item 18)
        repair = p.op == "migrate" and broken
        broken = False
        live = p.live()
        for iid, it in live.items():
            old = prev.get(iid)
            if old is not None and old.tokens() == it.tokens() and old.kind == it.kind:
                continue  # W1: a move or a formatting edit
            mine = p.item.upper() == iid
            why = tuple(p.why.get(iid, ()))
            if p.op == "add" and mine:
                out.setdefault(iid, []).append(Text(iid, p.version, p.revised, it, why, True, "add"))
            elif p.op == "edit" and mine:
                out.setdefault(iid, []).append(Text(iid, p.version, p.revised, it, why, True, "edit"))
            elif p.op == "restore" and mine:
                client_written = it.tokens() in ctexts
                out.setdefault(iid, []).append(Text(iid, p.version, p.revised, it, why, not client_written, "restore", client_written))
            elif p.op == "watch" and mine:
                out.setdefault(iid, []).append(Text(iid, p.version, p.revised, it, why, False, "watch"))
            else:
                out.setdefault(iid, []).append(Text(iid, p.version, p.revised, it, why, False, "repair" if repair else (p.op or "other")))
        if p.by == client:
            ctexts |= {i.tokens() for i in live.values()}
        prev = dict(live)
    return out


class Derivation:
    """The states of every item of one service, from the files up to a time (8.1)."""

    def __init__(self, world: World):
        self.full = world
        self.pbs = sorted((p for p in world.playbooks), key=lambda p: p.version)
        self.texts = item_texts(self.pbs, world.client)
        self.cache: dict = {}

    # -- views of the files as of t
    def mail(self, t: datetime | None, b3: bool = False) -> Mail:
        k = ("mail", t, b3)
        if k not in self.cache:
            self.cache[k] = Mail(self.full.as_of_b3(t) if b3 and t is not None else self.full.as_of(t))
        return self.cache[k]

    def pbs_upto(self, t: datetime | None) -> list[PVersion]:
        return [p for p in self.pbs if t is None or p.revised <= t]

    def item_at(self, iid: str, t: datetime) -> Item | None:
        ps = [p for p in self.pbs_upto(t) if p.items is not None or p.legacy]
        return ps[-1].live().get(iid) if ps else None

    def texts_of(self, iid: str, t: datetime | None) -> list[Text]:
        return [x for x in self.texts.get(iid, []) if t is None or x.live_from <= t]

    def text_live_at(self, iid: str, t: datetime) -> Text | None:
        if self.item_at(iid, t) is None:
            return None
        xs = self.texts_of(iid, t)
        return xs[-1] if xs else None

    # -- k and r (8.4)
    def k_r(self, w: Watch) -> tuple[int, tuple[int, int]]:
        ck = ("kr", w.item, w.start)
        if ck in self.cache:
            return self.cache[ck]
        ws = w.start
        mail = Mail(self.full.before(ws))
        refs = refs_of(w.changes[0].text, mail)
        den = num = 0
        for case in mail.cases():
            dels = mail.deliveries(case)
            if not any(any(v.tier == "human" for v in mail.verdicts_on(t, r)) for t, r in dels):
                continue
            den += 1
            tasks = mail.tasks_of(case)
            if any(mail.subjects(v.id) & refs for v in mail.rejections if v.task in tasks):
                num += 1
        if den >= 10 and num >= 1:
            r = num / den
            k = 3 if r >= 1 else max(3, math.ceil(math.log(0.1) / math.log(1 - r)))
        else:
            k = 3
        self.cache[ck] = (k, (num, den))
        return self.cache[ck]

    # -- one watched change: candidates, judged(c), J(c), E, D
    def change_facts(self, ch: Change, k: int, mail: Mail) -> dict:
        why_cases = {mail.case_of(mail.by_rid[r.upper()].task) for r in ch.text.why if r.upper() in mail.by_rid}
        firsts = []
        for case in mail.cases():
            if case in why_cases:
                continue
            ds = [(t, r) for t, r in mail.deliveries(case) if r.t > ch.live_from]
            if ds:
                firsts.append((min(r.t for _, r in ds), case, ds))
        firsts.sort(key=lambda x: (x[0], x[1]))
        cands = []
        for first_t, case, ds in firsts[:k]:
            best = None
            for t, r in ds:
                hv = [v for v in mail.verdicts_on(t, r) if v.tier == "human"]
                if hv and (best is None or hv[0].id < best[2].id):
                    best = (t, r, hv[0])
            sup = sum(1 for t, r in ds if best and r.id < best[1].id)
            cands.append({"case": case, "first_done": first_t, "task": best[0].id if best else None,
                          "result": best[1].id if best else None, "J": best[1].t if best else None,
                          "verdict": best[2].id if best else None, "Dn": best[2].t if best else None, "superseded_before": sup})
        E = D = None
        if len(cands) == k and all(c["J"] for c in cands):
            E = max(c["J"] for c in cands)
            D = max(c["Dn"] for c in cands)
        return {"cands": cands, "E": E, "D": D, "start": ch.start, "live_from": ch.live_from}

    @staticmethod
    def in_window(rej: Verdict, f: dict, mail: Mail) -> bool:
        rr = mail.rejected_result(rej)
        if rr is None or rr.t < f["start"]:
            return False
        return f["E"] is None or rr.t <= f["E"] or rej.t < f["D"]

    def related(self, rej: Verdict, iid: str, mail: Mail, w: "Watch | None" = None) -> bool:
        """Section 3: not pending; the text T live when the rejected result was created; subjects meet T's refs. With a watch carried by a
        repair migration (ii), T before the repair is the text under the watch's old id."""
        if mail.pending(rej.id):
            return False
        rr = mail.rejected_result(rej)
        if rr is None:
            return False
        tx = self.text_live_at(w.id_at(rr.t) if w is not None else iid, rr.t)
        return tx is not None and bool(mail.subjects(rej.id) & refs_of(tx, mail))

    def evaluate(self, w: Watch, t: datetime, b3: bool = False) -> dict:
        """The watch from the files up to t, before K is applied: window, related (window, then the warned window, B1), pending,
        clean, waiting, and whether the kept condition holds at t. b3: B3's order at t (contract versions at t, messages before t)."""
        ck = ("ev", w.key(), t, b3)
        if ck in self.cache:
            return self.cache[ck]
        mail = self.mail(t, b3)
        k, r = self.k_r(w)
        facts = [self.change_facts(ch, k, mail) for ch in w.changes]
        window = [x for x in mail.rejections if any(self.in_window(x, f, mail) for f in facts)]
        rel = [x for x in window if self.related(x, w.item, mail, w)]
        pend = [x for x in window if mail.pending(x.id)]
        carried: list[str] = []
        if w.carried_watch is not None:
            cw = self.evaluate(w.carried_watch, min(t, (w.carried_at or t) - _EPS))
            carried = list(cw["related_ids"])
            # a corrected link on an old rejection reaches the carrying item: re-read the carried ones over the files up to t
            carried = [x for x in carried if x in mail.rid and self.related(mail.by_id[x], w.carried_watch.item, mail, w.carried_watch)
                       or x in mail.rid and self.related(mail.by_id[x], w.item, mail, w)]
        warned, rel_w = [], []
        if rel or carried:
            for ch in w.changes:
                for x in mail.rejections:
                    rr = mail.rejected_result(x)
                    if rr is None or rr.t < ch.start or x in warned:
                        continue
                    it = self.item_at(w.id_at(x.t), x.t)
                    if it is not None and it.tokens() == ch.tokens_at(x.t):
                        warned.append(x)
            rel_w = [x for x in warned if x not in rel and self.related(x, w.item, mail, w)]
        related_ids = list(dict.fromkeys([x.id for x in rel] + carried + [x.id for x in rel_w]))
        last = facts[-1]
        clean = waiting = 0
        for c in last["cands"]:
            if not c["task"]:
                waiting += 1
                continue
            rs = [x for x in window if x.task in mail.tasks_of(c["case"])]
            if not any(x in rel or x in pend for x in rs):
                clean += 1
        res = {"k": k, "r": r, "facts": facts, "window": [x.id for x in window], "warned": [x.id for x in warned],
               "related_ids": related_ids, "pending_ids": [x.id for x in pend], "clean": clean, "waiting": waiting,
               "kept_ok": last["E"] is not None and not pend and not related_ids}
        self.cache[ck] = res
        return res

    def record_times(self, after: datetime, upto: datetime | None) -> list[tuple[datetime, bool]]:
        """(time, is a contract version's `defined`) of every record K may fall on (section 3), from `after` on."""
        w = self.full
        ts = [(v.t, False) for v in w.verdicts] + [(x.t, False) for x in w.links if x.tier == "human"]
        ts += [(c.defined, True) for c in w.contracts if c.answers]
        return sorted({x for x in ts if x[0] >= after and (upto is None or x[0] <= upto)})

    def k_time(self, w: Watch, upto: datetime | None) -> datetime | None:
        """K (section 3): the earliest record at or after D at which the files up to it derive `kept` (never for a warned item). At an
        equal microsecond a contract version comes before the link note written after it (B3): a contract version's time is tested
        first with the messages of that microsecond left out."""
        ck = ("K", w.key(), upto)
        if ck in self.cache:
            return self.cache[ck]
        ans, ans_b3 = None, False
        top = upto or _FAR
        if w.ended_at is not None:
            top = min(top, w.ended_at - _EPS)
        D = self.evaluate(w, top)["facts"][-1]["D"]
        if D is not None:
            # every record from D on is tested in order (section 3); a warned item fails the kept condition at each of them, so K stays
            # undefined for it (B1), unless a corrected link unrelates its related rejections (8.1's one exception): then K is the first
            # record at which the files derive kept again (warning -> kept, or warning -> new before it)
            for tr, is_contract in self.record_times(D, top):
                for b3 in ((True, False) if is_contract else (False,)):
                    st = self.evaluate(w, tr, b3)
                    if st["kept_ok"]:
                        ans, ans_b3 = tr, b3
                        break
                if ans is not None:
                    break
        self.cache[ck] = ans
        self.cache[("K_b3", w.key(), upto)] = ans_b3
        return ans

    # -- pass 2: the watches, walking the versions (W1-W3, carried watches (i) and B2)
    def watches(self, t: datetime | None) -> dict[str, list[Watch]]:
        ck = ("watches", t)
        if ck in self.cache:
            return self.cache[ck]
        ws: dict[str, list[Watch]] = {}
        warned_out: list[tuple[str, Watch, datetime]] = []  # (text key, watch, retired at): owner retires while in warning
        prev: dict[str, Item] = {}
        prev_why: dict = {}
        for p in self.pbs_upto(t):
            if p.items is None:
                if p.legacy:
                    prev, prev_why = {}, {}
                continue
            live = p.live()
            for tx in [x for xs in self.texts.values() for x in xs if x.version == p.version]:
                iid = tx.item
                cur = ws.get(iid, [None])[-1] if ws.get(iid) else None
                active = cur is not None and cur.ended_at is None and self.k_time(cur, p.revised - _EPS) is None
                if tx.op == "watch":
                    if active:
                        cur.ended_at, cur.end_kind = p.revised, "watch"
                    continue
                if tx.op == "repair":
                    # carried watch (ii): the repaired item whose text key equals an item's rendered line, live and in its watch in the
                    # last parseable version, continues that watch (same start, changes and refs); W1: its text is the watched text now
                    for oid, oit in prev.items():
                        ow = ws.get(oid, [None])[-1] if ws.get(oid) else None
                        if ow is None or ow.ended_at is not None or self.k_time(ow, p.revised - _EPS) is not None:
                            continue
                        if rendered_key(oit, prev_why.get(oid, ())) != tx.obj.key():
                            continue
                        chs = [Change(c.live_from, c.start, c.text, c.tokens, list(c.earlier)) for c in ow.changes]
                        chs[-1].earlier.append((p.revised, chs[-1].tokens))
                        chs[-1].tokens = tx.obj.tokens()
                        ow.ended_at, ow.end_kind = p.revised, "repair"
                        ws.setdefault(iid, []).append(Watch(iid, ow.start, chs, oid, ow.carried_watch, ow.carried_at,
                                                            alias=oid, alias_until=p.revised))
                        break
                    continue
                if not (tx.gated or tx.client_restore):
                    continue
                if tx.client_restore and not tx.gated:
                    if active:
                        cur.changes.append(Change(p.revised, p.revised, tx, tx.obj.tokens()))  # W2 by an exempt restore
                    continue
                carried = None
                for key, w0, at in reversed(warned_out):
                    if key == tx.obj.key() or (tx.op == "restore" and w0.item == iid):
                        carried = (w0, at)
                        break
                ch = Change(p.revised, p.revised, tx, tx.obj.tokens())
                if active and tx.op != "add":
                    cur.changes.append(ch)  # W2: a gated change restarts the count; related kept (D4)
                    if carried is not None and cur.carried_watch is None:
                        cur.carried, cur.carried_watch, cur.carried_at = carried[0].item, carried[0], carried[1]
                elif carried is not None:
                    w0, at = carried
                    ch.start = w0.start if tx.op != "edit" else p.revised
                    ws.setdefault(iid, []).append(Watch(iid, w0.start, [ch], w0.item, w0, at))
                else:
                    ws.setdefault(iid, []).append(Watch(iid, p.revised, [ch]))
            for iid, old in prev.items():
                if iid in live:
                    continue
                cur = ws.get(iid, [None])[-1] if ws.get(iid) else None
                if cur is None or cur.ended_at is not None or self.k_time(cur, p.revised - _EPS) is not None:
                    continue
                if p.op not in ("watch", "migrate"):  # an owner's retire; a repair that could not carry is L6's, never carried on
                    st = self.evaluate(cur, p.revised - _EPS)
                    if st["related_ids"]:
                        warned_out.append((old.key(), cur, p.revised))
                cur.ended_at, cur.end_kind = p.revised, p.op
            prev, prev_why = dict(live), dict(p.why)
        self.cache[ck] = ws
        return ws

    # -- the states (8.1) as of t
    def states(self, t: datetime | None) -> list[dict]:
        pbs = self.pbs_upto(t)
        if not pbs:
            return []
        lastp = next((p for p in reversed(pbs) if p.items is not None or p.legacy), None)
        if lastp is None:
            return []
        if lastp.legacy:
            return [row(i.id, i.kind, "kept") for i in legacy_items_of(lastp)]
        mail = self.mail(t)
        top = t or _FAR
        ws = self.watches(t)
        live = lastp.live()
        ever = sorted({i.id for p in pbs if p.items for i in p.items}, key=id_num)
        out = []
        for iid in ever:
            w = ws[iid][-1] if ws.get(iid) else None
            it = live.get(iid)
            kind = (it or last_item(iid, pbs)).kind
            if it is None:
                r = row(iid, kind, "retired")
                if w is not None:
                    r.update(self.fields(w, self.evaluate(w, min(top, (w.ended_at or top)) - _EPS), None, mail))
                    r["state"] = "retired"
                out.append(r)
                continue
            if w is None or w.ended_at is not None:
                st = "kept"
                rp = [p for p in pbs if p.op == "watch" and p.item.upper() == iid and p.restores]
                if rp and not any(x.gated and x.live_from > rp[-1].revised for x in self.texts_of(iid, t)):
                    st = "restored"
                r = row(iid, kind, st)
                if w is not None:
                    r.update(self.fields(w, self.evaluate(w, (w.ended_at or top) - _EPS), None, mail))
                    r["state"] = st
                out.append(r)
                continue
            K = self.k_time(w, t)
            if K is not None:
                st = self.evaluate(w, K, self.cache.get(("K_b3", w.key(), t), False))
                win = [mail.by_id[x] for x in st["window"] if x in mail.by_id and mail.by_id[x].t <= K]
                rel = [x for x in win if self.related(x, iid, mail, w)]  # after K only a corrected link can relate one (8.1)
                r = row(iid, kind, "warning" if rel else "kept")
                r.update(self.fields(w, st, K, mail))
                r["state"] = "warning" if rel else "kept"
                r["related"] = sorted({mail.rid[x.id] for x in rel}, key=id_num)
                r["retire_due"] = len(rel) >= 2
                out.append(r)
                continue
            st = self.evaluate(w, top)
            r = row(iid, kind, "warning" if st["related_ids"] else "new")
            r.update(self.fields(w, st, None, mail))
            r["retire_due"] = len(st["related_ids"]) >= 2 and it.tokens() == w.changes[-1].tokens
            out.append(r)
        return out

    @staticmethod
    def fields(w: Watch, st: dict, K, mail: Mail) -> dict:
        rid = lambda x: mail.rid.get(x, x)  # noqa: E731
        last = st["facts"][-1]
        return {"k": st["k"], "r": list(st["r"]), "clean": st["clean"], "waiting": st["waiting"],
                "related": sorted({rid(x) for x in st["related_ids"]}, key=id_num),
                "pending": sorted({rid(x) for x in st["pending_ids"]}, key=id_num), "since": iso(w.start), "carried": w.carried,
                "judged": [{"case": c["case"], "judged_task": c["task"], "J": iso(c["J"]), "judging_verdict": c["verdict"],
                            "superseded_before": c["superseded_before"]} for c in last["cands"]],
                "E": iso(last["E"]), "D": iso(last["D"]), "K": iso(K),
                "window": sorted({rid(x) for x in st["window"]}, key=id_num), "warned_window": sorted({rid(x) for x in st["warned"]}, key=id_num)}


def row(iid: str, kind: str, state: str) -> dict:
    return {"item": iid, "kind": kind, "state": state, "k": 0, "r": [0, 0], "clean": 0, "waiting": 0, "related": [], "pending": [],
            "since": None, "carried": "", "retire_due": False, "judged": [], "E": None, "D": None, "K": None, "window": [],
            "warned_window": []}


def last_item(iid: str, pbs: list[PVersion]) -> Item:
    for p in reversed(pbs):
        if p.items and iid in p.live():
            return p.live()[iid]
    return Item(iid, "step", "")


def legacy_items_of(p: PVersion) -> tuple[Item, ...]:
    return getattr(p, "_legacy_items", ())


# ------------------------------------------------------------------------------------------------------------------ loading evidence
def split_frontmatter(text: str) -> tuple[dict, str]:
    text = text.replace("\r\n", "\n")
    if text.startswith("---\n"):
        end = text.find("\n---", 4)
        if end != -1:
            meta = yaml.safe_load(text[4:end]) or {}
            rest = text[end + 4:]
            return (meta if isinstance(meta, dict) else {}), rest[1:] if rest.startswith("\n") else rest
    return {}, text


def tier_of(meta: dict) -> str:
    """0a 3.1-3.2: an agent's note is `agent`; a root note without `source` (written before sources existed) is `human`; `source: human`
    is human; any other value (`relayed`, or an unknown value: the safe side) is `relayed`."""
    if str(meta.get("from", "")) != ROOT:
        return "agent"
    src = str(meta.get("source", "") or "").strip()
    return "human" if src in ("", "human") else "relayed"


def load_messages(dirs: list[Path]) -> list[tuple[dict, str]]:
    seen, out = set(), []
    for d in dirs:
        for f in sorted(d.glob("*.md")) if d.is_dir() else []:
            meta, body = split_frontmatter(f.read_text(errors="replace"))
            mid = str(meta.get("id", f.stem))
            if mid in seen:
                continue
            seen.add(mid)
            out.append((meta, body))
    return out


def ids_of_header(v) -> tuple[str, ...]:
    if v is None:
        return ()
    if isinstance(v, list):
        return tuple(str(x).strip() for x in v)
    return tuple(x.strip() for x in str(v).split(",") if x.strip())


def load_world(stream: Path, service: str | None = None) -> World:
    sent = load_messages([stream / "msgs" / "sent"])
    recv = load_messages([stream / "msgs" / "read", stream / "msgs" / "inbox"])
    tasks = [Task(str(m["id"]), str(m.get("service", "")), str(m.get("to", "")), str(m.get("revises", "") or ""),
                  str(m.get("source", "") or ""), int(m.get("budget", 0) or 0), str(m.get("title", "")))
             for m, _ in sent if m.get("type") == "task"]
    if service is None:
        svc = [t.service for t in tasks if t.service]
        service = max(set(svc), key=svc.count) if svc else ""
    owner = next((t.to for t in tasks if t.service == service), "")
    results = [Result(str(m["id"]), str(m.get("reply_to", "")), str(m.get("status", ""))) for m, _ in recv if m.get("type") == "result"]
    verdicts, links = [], []
    for m, _ in sent:
        if m.get("type") != "note":
            continue
        if m.get("feedback"):
            verdicts.append(Verdict(str(m["id"]), str(m.get("reply_to", "")), str(m["feedback"]), tier_of(m)))
        elif m.get("criterion") is not None and m.get("reply_to"):
            links.append(Link(str(m["id"]), str(m["reply_to"]), ids_of_header(m.get("criterion")), tier_of(m)))
    contracts, created = load_contracts(stream / "service")
    playbooks = load_playbooks(stream / "playbook")
    return World(service, owner, ROOT, created, tasks, results, verdicts, links, contracts, playbooks)


def _version_files(d: Path, kind: str, with_path: bool = False) -> list:
    out: dict[int, tuple] = {}
    if not d.is_dir():
        return []
    for f in sorted(d.glob("*.md")):
        meta, body = split_frontmatter(f.read_text(errors="replace"))
        if "version" not in meta:
            continue
        is_contract = "acceptance" in meta
        if (kind == "SERVICE") != is_contract:
            continue
        out.setdefault(int(meta["version"]), (meta, body, f))
    return [out[v] if with_path else out[v][:2] for v in sorted(out)]


def load_contracts(d: Path) -> tuple[list[Contract], datetime | None]:
    """Each contract version timed by its `defined` (B3: never the contract's `created`). A version above 1 without `defined` stops the
    run with an error naming its file (protocol 13.4); v1 alone may fall back to `created` (the service's creation is v1's definition)."""
    out, created = [], None
    for meta, _, f in _version_files(d, "SERVICE", with_path=True):
        created = created or parse_time(meta.get("created"))
        v = int(meta["version"])
        defined = parse_time(meta.get("defined"))
        if defined is None and v > 1:
            raise ValueError(f"contract version {v} in {f} has no `defined` (B3: a contract version's time is its `defined`, never the "
                             f"contract's `created`): the re-derivation stops (protocol 13.4)")
        out.append(Contract(v, defined or parse_time(meta.get("created")),
                            tuple(str(x) for x in (meta.get("acceptance") or [])), str(meta.get("defined_by", ROOT) or ROOT),
                            str(meta.get("answers", "") or ""), str(meta.get("about", "") or ""), str(meta.get("words", "") or ""),
                            str(meta.get("initiated", "") or ""), bool(meta.get("locked", False))))
    return out, created


def load_playbooks(d: Path) -> list[PVersion]:
    out = []
    for meta, body in _version_files(d, "PLAYBOOK"):
        out.append(pversion_of(meta, body))
    return out


def pversion_of(meta: dict, body: str) -> PVersion:
    legacy = "items_max" not in meta
    if legacy:
        items, err = None, ""
    else:
        items, err = parse_items(body, meta)
    p = PVersion(int(meta["version"]), parse_time(meta.get("revised")), str(meta.get("by", "")), str(meta.get("op", "") or ""),
                 str(meta.get("item", "") or "").upper(), str(meta.get("admitted", "") or ""), items,
                 {str(k).upper(): tuple(str(x) for x in (v or [])) for k, v in (meta.get("why") or {}).items()},
                 tuple(str(x) for x in (meta.get("related") or [])), int(meta.get("restores", 0) or 0), err, legacy)
    if legacy:
        object.__setattr__(p, "_legacy_items", legacy_items(body))
    return p


# ------------------------------------------------------------------------------------------------------------------ comparison (14.4)
KEYS = ("item", "kind", "state", "k", "r", "clean", "waiting", "related", "pending", "since", "carried")


def product_watch(qjson: dict, service: str, owner: str) -> list[dict] | None:
    """The study service's `watch` list in a quality JSON (the entry naming the service, and its owner when the entry names one)."""
    for s in qjson.get("services") or []:
        vals = {str(v) for v in s.values() if isinstance(v, (str, int))}
        if service in vals and (not owner or s.get("owner") in (None, owner)):
            return s.get("watch")
    return None


def norm_value(key: str, v):
    if key in ("related", "pending"):
        return sorted(str(x) for x in (v or []))
    if key == "r":
        return [int(x) for x in (v or [0, 0])]
    if key == "since":
        d = parse_time(v) if v else None
        return iso(d.replace(microsecond=d.microsecond)) if d else None
    return v


def compare(mine: list[dict], prod: list[dict] | None, tag: str) -> list[str]:
    """One re-derivation against the product (the self-check's form): compare_window with one time."""
    return compare_window([mine], prod, tag)


def pinned(key: str, state: str | None, never_watched: bool = False) -> bool:
    """Whether the design states this key for an item in this state (protocol 12.1 G1(f)): every key of a `new` or `warning` item (in its
    watch: 8.1, 14.4); `item`, `kind`, `state` of every item; `related` of a `kept` item (its window answered and unrelated: none) and of
    a `retired` one (it keeps the related of its last watch, 8.1), not of a `restored` one (8.1 says nothing of it); `k` 0, `r` (0, 0)
    and `since` None of an item never watched (25.2 item 14)."""
    if state in ("new", "warning") or key in ("item", "kind", "state"):
        return True
    if key == "related":
        return state in ("kept", "retired")
    return never_watched and key in ("k", "r", "since")


RACE_LOWER = timedelta(seconds=5)  # protocol 12.1 G1(f): the race rule's lower margin, pre-registered


def compare_window(cands: list[list[dict]], prod: list[dict] | None, tag: str, lower: list[list[dict]] | None = None) -> list[str]:
    """The product's watch list against the re-derivation at each candidate time of one snapshot (its start, every record time inside
    it, its end): a key matches when it equals the re-derivation at any of them (protocol 12.1 G1(f), the race rule). `lower` holds the
    re-derivation at the start minus 5 s and at every record time in [start - 5 s, start): a key that matches only there is reported as
    `RACE-LOWER` (a record stamped before the snapshot's start but written after the product read the files), never a mismatch."""
    lower = lower or []
    if prod is None:
        if not any(cands):
            return []  # no item yet (the service or its playbook does not exist yet): nothing to compare
        return [f"MISSING {tag}: no `watch` list for the service in the product's quality JSON"]
    lines = []
    pm = {str(x.get("item")): x for x in prod}
    mms = [{x["item"]: x for x in c} for c in cands]
    lms = [{x["item"]: x for x in c} for c in lower]
    ids = set(pm) | {i for m in mms for i in m}
    for iid in sorted(ids, key=id_num):
        b = pm.get(iid)
        rows = [m.get(iid) for m in mms]
        have = [r for r in rows if r is not None]
        if b is None or not have:
            if b is None and all(r is not None for r in rows):
                if any(m.get(iid) is None for m in lms):
                    lines.append(f"RACE-LOWER {tag} {iid} item: missing from the product, absent from the re-derivation just before the "
                                 f"snapshot's start (reported)")
                else:
                    lines.append(f"MISMATCH {tag} {iid} item pinned: item missing from the product")
            elif b is not None and not have:
                lines.append(f"MISMATCH {tag} {iid} item pinned: item missing from the re-derivation")
            continue
        never = all(r.get("since") is None for r in have)
        for k in KEYS:
            if any(norm_value(k, r.get(k)) == norm_value(k, b.get(k)) for r in have):
                continue
            if any(m.get(iid) is not None and norm_value(k, m[iid].get(k)) == norm_value(k, b.get(k)) for m in lms):
                lines.append(f"RACE-LOWER {tag} {iid} {k}: product {norm_value(k, b.get(k))!r} matches the re-derivation only in "
                             f"[start - 5 s, start) (reported)")
                continue
            ref = have[0]
            lines.append(f"MISMATCH {tag} {iid} {k} {'pinned' if pinned(k, ref.get('state'), never) else 'unpinned'}: re-derived "
                         f"{norm_value(k, ref.get(k))!r}, product {norm_value(k, b.get(k))!r}")
    return lines


# ------------------------------------------------------------------------------------------------------------------ services (14.3)
_SV_ITEM = re.compile(r"\b(P\d+) (new|warning|restored|kept|retired)\b(?: \(([^()]*)\))?")


def services_watched(text: str, service: str) -> tuple[dict | None, str]:
    """Root's `services` listing: the watch suffix of the service's playbook line (14.3) -> {item: {state, related, clean, k, retire_due}},
    or (None, reason) when the line cannot be read. ({} when the service is listed with nothing watched or is not listed at all.)"""
    lines = (text or "").splitlines()
    head = next((n for n, ln in enumerate(lines) if re.match(rf"^\s*- {re.escape(service)} \(offered by ", ln)), None)
    if head is None:
        return {}, "service not listed"
    pb = None
    for ln in lines[head + 1:]:
        if re.match(r"^\s*- \S", ln) and not ln.startswith("    "):
            break
        if re.match(r"^\s*playbook v\d+", ln):
            pb = ln
            break
    if pb is None:
        return {}, "no playbook line"
    if "watched:" in pb:
        out = {}
        for m in _SV_ITEM.finditer(pb.split("watched:", 1)[1]):
            body = m.group(3) or ""
            c = re.search(r"(\d+) of (\d+) clean", body)
            k = re.search(r"\bk (\d+)", body)
            out[m.group(1)] = {"state": m.group(2), "related": sorted(re.findall(r"\bR\d+\b", body), key=id_num),
                               "clean": int(c.group(1)) if c else None, "k": int(k.group(1)) if k else None,
                               "retire_due": "retire due" in body}
        return out, ""
    if re.search(r"none watched|free text|no items|not in item form", pb):
        return {}, ""
    return None, pb.strip()


def compare_services(cands: list[list[dict]], text: str, service: str, tag: str, lower: list[list[dict]] | None = None) -> list[str]:
    """The watched items of root's listing against the re-derivation's items in their watch (new, warning) at any candidate time; a
    value that matches only the re-derivation in [start - 5 s, start) is `RACE-LOWER`, reported (compare_window's lower margin)."""
    got, why = services_watched(text, service)
    if got is None:
        return [f"SERVICES-UNREAD {tag}: {why}"]
    if why == "service not listed" and not any(cands):
        return []
    lines = []
    sets = [{r["item"]: r for r in c if r["state"] in ("new", "warning")} for c in cands]
    lsets = [{r["item"]: r for r in c if r["state"] in ("new", "warning")} for c in (lower or [])]
    for iid in sorted(set(got) | {i for s in sets for i in s}, key=id_num):
        g = got.get(iid)
        rows = [s.get(iid) for s in sets]
        if g is None:
            if all(r is not None for r in rows):
                if any(s.get(iid) is None for s in lsets):
                    lines.append(f"RACE-LOWER {tag} {iid} item: not in the listing, not watched just before the snapshot's start (reported)")
                else:
                    lines.append(f"SERVICES-MISMATCH {tag} {iid} item: watched in the re-derivation, not in the listing")
            continue
        have = [r for r in rows if r is not None]
        if not have:
            if any(s.get(iid) is not None for s in lsets):
                lines.append(f"RACE-LOWER {tag} {iid} item: in the listing ({g['state']}), watched only just before the snapshot's start "
                             f"(reported)")
            else:
                lines.append(f"SERVICES-MISMATCH {tag} {iid} item: in the listing ({g['state']}), not watched in the re-derivation")
            continue
        for key in ("state", "related", "clean", "k", "retire_due"):
            if key in ("clean", "k") and (g[key] is None or g["state"] != "new"):
                continue
            if key == "related" and g["state"] != "warning":
                continue
            if any(norm_value(key, r.get(key)) == norm_value(key, g[key]) for r in have):
                continue
            if any(s.get(iid) is not None and norm_value(key, s[iid].get(key)) == norm_value(key, g[key]) for s in lsets):
                lines.append(f"RACE-LOWER {tag} {iid} {key}: listing {g[key]!r} matches the re-derivation only in [start - 5 s, start) "
                             f"(reported)")
                continue
            lines.append(f"SERVICES-MISMATCH {tag} {iid} {key}: re-derived {norm_value(key, have[0].get(key))!r}, listing {g[key]!r}")
    return lines


SNAP_LINE = re.compile(r"^(turn-\d+|end) start (\S+) end (\S+) exit (\d+)")
NO_ORG = re.compile(r"^(turn-\d+|end) \S+: no org yet")
TRACEBACK = re.compile(r"^Traceback \(most recent call last\):", re.M)
PRODUCT_FRAME = re.compile(r'File "[^"]*(?:[/\\]src[/\\]hirearchy[/\\]|[/\\]site-packages[/\\]hirearchy[/\\])[^"]*"')


def snapshot_times(stream: Path, kind: str = "quality") -> list[tuple[str, datetime, datetime]]:
    calls = stream / kind / "calls.txt"
    out = []
    if not calls.exists():
        return out
    for ln in calls.read_text().splitlines():
        m = SNAP_LINE.match(ln)
        if m:
            out.append((m.group(1), parse_time(m.group(2)), parse_time(m.group(3))))
    return out


def unread_snapshots(stream: Path) -> dict[tuple[str, str], dict]:
    """Protocol 12.1's unread rule. A `turn-NN` or `end` snapshot taken after ORG.md existed (a calls.txt line with start, end and exit) is
    unread when its exit is not 0, or its output file is missing or empty, or (quality) its output is not valid JSON; a turn of
    turn-times.txt, or the end, with no calls.txt line of either form (taken, or `no org yet`) is unread too (no snapshot recorded). Each
    entry: {kind, tag, reasons, traceback (the stderr file shows a Python traceback through the product's package), files}."""
    out: dict[tuple[str, str], dict] = {}
    turns = []
    tt = stream / "turn-times.txt"
    if tt.exists():
        turns = [f"turn-{int(m.group(1)):02d}" for m in re.finditer(r"^turn (\d+): ", tt.read_text(), re.M)]
    for kind, ext in (("quality", "json"), ("services", "txt")):
        calls = stream / kind / "calls.txt"
        text = calls.read_text(errors="replace") if calls.exists() else ""
        seen = set()
        for ln in text.splitlines():
            m, n = SNAP_LINE.match(ln), NO_ORG.match(ln)
            if n:
                seen.add(n.group(1))
            if not m:
                continue
            tag, rc = m.group(1), int(m.group(4))
            seen.add(tag)
            f, err = stream / kind / f"{tag}.{ext}", stream / kind / f"{tag}.stderr.txt"
            reasons = []
            if rc != 0:
                reasons.append(f"exit {rc}")
            if not f.exists():
                reasons.append("no output file")
            elif f.stat().st_size == 0:
                reasons.append("empty output")
            elif kind == "quality":
                try:
                    json.loads(f.read_text(errors="replace"))
                except json.JSONDecodeError as e:
                    reasons.append(f"not valid JSON ({e.msg} at line {e.lineno})")
            if reasons:
                es = err.read_text(errors="replace") if err.exists() else ""
                out[(kind, tag)] = {"kind": kind, "tag": tag, "reasons": reasons,
                                    "traceback": bool(TRACEBACK.search(es) and PRODUCT_FRAME.search(es)),
                                    "files": [str(x.relative_to(stream)) for x in (f, err, calls) if x.exists()]}
        if calls.exists() or turns:
            for tag in turns + ["end"]:
                if tag not in seen:
                    out[(kind, tag)] = {"kind": kind, "tag": tag, "reasons": ["no snapshot recorded in calls.txt"], "traceback": False,
                                        "files": [str(calls.relative_to(stream))] if calls.exists() else []}
    return out


def window_times(w: World, start: datetime, end: datetime) -> list[datetime]:
    return [start] + [x for x in w.record_times() if start < x <= end] + ([end] if end > start else [])


def lower_times(w: World, start: datetime) -> list[datetime]:
    """The race rule's lower margin (protocol 12.1 G1(f)): start - 5 s and every record time in [start - 5 s, start)."""
    lo = start - RACE_LOWER
    return [lo] + [x for x in w.record_times() if lo <= x < start and x != lo]


def run_stream(stream: Path, out: Path) -> int:
    w = load_world(stream)
    der = Derivation(w)
    out.mkdir(parents=True, exist_ok=True)
    rows, mism, items_txt = {}, [], []
    unread = unread_snapshots(stream)
    snaps = snapshot_times(stream)
    for tag, t0, t1 in snaps + [("files-end", None, None)]:
        cand_t = window_times(w, t0, t1) if t0 else [None]
        cands = [der.states(t) for t in cand_t]
        st = cands[0]
        rows[tag] = st
        q = stream / "quality" / f"{tag}.json"
        if tag != "files-end" and ("quality", tag) not in unread:
            prod = product_watch(json.loads(q.read_text()), w.service, w.owner)
            mism += compare_window(cands, prod, tag, [der.states(t) for t in lower_times(w, t0)])
        for r in st:
            items_txt.append(f"{tag} {r['item']} {r['kind']} {r['state']} k={r['k']} r={r['r']} clean={r['clean']} waiting={r['waiting']} "
                             f"related={r['related']} pending={r['pending']} since={r['since']} carried={r['carried']!r} "
                             f"retire_due={r['retire_due']} E={r['E']} D={r['D']} K={r['K']} window={r['window']} "
                             f"warned_window={r['warned_window']} judged={json.dumps(r['judged'])}")
    for tag, t0, t1 in snapshot_times(stream, "services"):
        f = stream / "services" / f"{tag}.txt"
        if ("services", tag) not in unread:
            mism += compare_services([der.states(t) for t in window_times(w, t0, t1)], f.read_text(errors="replace"), w.service, tag,
                                     [der.states(t) for t in lower_times(w, t0)])
    for (kind, tag), u in sorted(unread.items(), key=lambda x: (x[0][1], x[0][0])):
        mism.append(f"UNREAD {tag} {kind}: {'; '.join(u['reasons'])}" + ("; traceback through the product" if u["traceback"] else "")
                    + f" ({', '.join(u['files'])})")
    (out / "watch-rederived.json").write_text(json.dumps({"service": w.service, "owner": w.owner, "states": rows}, indent=1, default=str))
    (out / "watch-items.txt").write_text("\n".join(items_txt) + "\n")
    n_p = sum(1 for m in mism if m.startswith(("MISMATCH", "MISSING")) and " unpinned:" not in m)
    n_u = sum(1 for m in mism if m.startswith("MISMATCH") and " unpinned:" in m)
    n_s = sum(1 for m in mism if m.startswith("SERVICES-MISMATCH"))
    n_r = sum(1 for m in mism if m.startswith("SERVICES-UNREAD"))
    n_l = sum(1 for m in mism if m.startswith("RACE-LOWER"))
    n_x = sum(1 for m in mism if m.startswith("UNREAD"))
    total = (f"{n_p + n_u} mismatches ({n_p} on pinned keys, {n_u} on unpinned keys); {n_s} services mismatches; {n_r} services lines "
             f"unread; {n_l} lower-margin race matches (reported); {n_x} snapshots unread")
    (out / "watch-mismatches.txt").write_text("\n".join(mism + [total]) + "\n")
    print(f"rederive_watch: {len(rows)} snapshots, {total}")
    return 0


# ------------------------------------------------------------------------------------------------------------------ spend (0b 3, 0b.1 3.2)
def spend_figures(case: dict) -> dict:
    """One case of the hand ledger -> the design's figures. Ledger keys (each read by hand from the raw files, with its file):
    state (done|failed|open|blocked), runs (charged runs of the chain), relayed_runs, budget (the tasks' budgets handed down),
    user_budget (the user's requests' budgets), user_granted (root's grant notes inside a user interval), returned (runs results gave
    back, each at most its task's budget), user_returned, relayed_overlap (0 unless a ruling says otherwise), contract_budget (the
    per-request budget in force at the head task), ceilings (the user ceilings root set at each hand-down), lena_plan_budget (the plan
    Lena approved, after H4) and lena_grants (each L-FUND yes, with its runs: G0's "D14" ledger)."""
    runs, rel = int(case["runs"]), int(case.get("relayed_runs", 0))
    open_ = case["state"] not in ("done", "failed")
    still_out = max(0, int(case["budget"]) + int(case.get("user_granted", 0)) - runs - int(case.get("returned", 0))) if open_ else 0
    case_spend = runs + still_out
    user_runs = runs - rel
    user_committed = user_runs + max(0, int(case.get("user_budget", case["budget"])) + int(case.get("user_granted", 0)) - user_runs
                                     - int(case.get("user_returned", case.get("returned", 0))))
    user_spend = user_committed if open_ else user_runs
    user_cost = user_spend - int(case.get("relayed_overlap", 0))
    user_approved = max([int(case["contract_budget"])] + [int(x) for x in case.get("ceilings", [])])
    d14_approved = int(case.get("lena_plan_budget", case["contract_budget"])) + sum(int(g["runs"]) for g in case.get("lena_grants", []))
    return {"case_spend": case_spend, "user_spend": user_spend, "user_committed": user_committed, "user_cost": user_cost,
            "user_approved": user_approved, "ratio": f"{user_cost / user_approved:.2f}" if user_approved else "n/a",
            "d14_approved": d14_approved, "d14_used": int(case.get("d14_used", user_runs)),
            "d14_within": int(case.get("d14_used", user_runs)) <= d14_approved}


def run_spend(ledger: Path, quality: Path | None, out: Path, stream: Path | None = None) -> int:
    led = json.loads(ledger.read_text())
    out.mkdir(parents=True, exist_ok=True)
    res, lines = {}, []
    q = json.loads(quality.read_text()) if quality and quality.exists() else None
    for cid, case in sorted(led.get("cases", {}).items()):
        if cid.startswith("<"):
            continue  # the template's placeholder entry
        f = spend_figures(case)
        res[cid] = f
        lines.append(f"{cid}: {json.dumps(f)}")
        if q is not None:
            pc = find_case(q, cid)
            if pc is None:
                lines.append(f"MISSING {cid}: no case in the product's quality JSON")
                continue
            for mine, theirs in (("user_cost", "user_cost"), ("case_spend", "spend"), ("user_approved", "approved")):
                if theirs in pc and int(pc[theirs]) != f[mine]:
                    lines.append(f"MISMATCH {cid} {mine}: re-derived {f[mine]}, product {pc[theirs]}")
    if stream is not None:
        # protocol 6.3: every case of the service, read from the stream's mail, must have its ledger entry (a missing one is NOT
        # DETERMINED, never a pass); an entry that names no case of the mail is listed too
        cases = Mail(load_world(stream)).cases()
        res["missing_cases"] = [c for c in cases if c not in res]
        res["extra_cases"] = [c for c in res if c not in cases and c not in ("missing_cases", "extra_cases")]
        lines.append(f"cases in the mail: {len(cases)}; missing from the ledger: {res['missing_cases'] or 'none'}; in the ledger, not in "
                     f"the mail: {res['extra_cases'] or 'none'}")
    (out / "spend-rederived.json").write_text(json.dumps(res, indent=1))
    (out / "spend-mismatches.txt").write_text("\n".join(lines + [f"{sum(1 for x in lines if x.startswith('MISMATCH'))} mismatches"]) + "\n")
    print(f"spend: {len([k for k in res if k not in ('missing_cases', 'extra_cases')])} cases, "
          f"{sum(1 for x in lines if x.startswith('MISMATCH'))} mismatches"
          + (f"; missing from the ledger: {res['missing_cases'] or 'none'}" if "missing_cases" in res else ""))
    return 0


def find_case(q, cid):
    stack = [q]
    while stack:
        o = stack.pop()
        if isinstance(o, dict):
            if o.get("id") == cid or o.get("case") == cid:
                return o
            stack.extend(o.values())
        elif isinstance(o, list):
            stack.extend(o)
    return None


def main(argv: list[str]) -> int:
    args = list(argv)

    def opt(name, default=None):
        if name in args:
            i = args.index(name)
            v = args[i + 1]
            del args[i:i + 2]
            return v
        return default
    out = opt("--out")
    spend = opt("--spend")
    quality = opt("--quality")
    stream = opt("--stream")
    if spend:
        return run_spend(Path(spend), Path(quality) if quality else None, Path(out or "."), Path(stream) if stream else None)
    if len(args) != 1 or not out:
        print(__doc__)
        return 2
    return run_stream(Path(args[0]), Path(out))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
