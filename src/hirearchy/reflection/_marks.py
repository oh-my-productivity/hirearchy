"""The marks of the timeline that the stored files give (design 7): the contract versions, the playbook versions and the top-ups of the cases.

Pure: the stored versions, the criteria and the cases are read by the caller. The marks are facts; no count is split by them and none says that
a bar improved. Free text an agent wrote (a playbook's reason and lines) is not in a mark's words; the lines are data for the JSON only."""

from __future__ import annotations

import re
from collections.abc import Sequence

from ..kernel import ROOT, JsonObject, clip_line, link_ids, parent, stamp_of, verdict_tier
from ..services import (
    Criterion, Playbook, amendment_ids, changed_lines, contract_of, criterion_words, number_criteria,
)
from .api import Case, ContractMark, PlaybookMark, TopUpMark, confirmed_criteria, regressions

LINES_LISTED = 10  # changed lines of a playbook version that a mark carries
LINE_CLIP = 600  # characters of one of them
_EVIDENCE_ID = re.compile(r"C\d+|R\d+|\d{8}T\d{12}-[a-z0-9./-]+")  # the cited ids that are shown; any other is agent-written and only counted
_CRITERION = re.compile(r"C\d+")
_TAG = re.compile(r"(?<![A-Za-z0-9])[CR]\d+(?![0-9])")  # a line that carries a criterion or assertion id
_BASES = ("c", "b", "first", "restore", "migrate", "exempt", "watch")  # the admissions a version can record (the last three: item form only)


def contract_marks(owner: str, name: str, versions: Sequence[tuple[int, JsonObject, str]], cases: Sequence[Case]) -> tuple[ContractMark, ...]:
    """One mark per stored version of the contract, oldest first. ``versions`` are ``(version, frontmatter, body)`` as ``ServiceStore.versions``
    lists them; ``cases`` are the service's, for the user's links."""
    contracts = [contract_of(owner, name, meta, body, None) for _, meta, body in versions]
    stored = [(c.version, c.defined_by or "", c.acceptance) for c in contracts]
    numbered = number_criteria(stored, {c.version: (c.answers, c.initiated == "user") for c in contracts})
    ids = {c.text: c.id for c in numbered}
    confirmed = confirmed_criteria(cases, numbered)
    rejections = {a.verdict.message.id: a.id for a in regressions(cases)}
    links: dict[str, list[tuple[str, str]]] = {}  # criterion -> (the rejection, the user's link note), oldest link first
    for case in cases:
        for verdict in case.verdicts:
            for note in verdict.link_notes:
                if verdict_tier(note) == "human":
                    for x in link_ids(note):
                        links.setdefault(x, []).append((verdict.message.id, note.id))
    for found in links.values():
        found.sort(key=lambda pair: pair[1])
    marks: list[ContractMark] = []
    for position, c in enumerate(contracts):
        if position == 0:
            marks.append(ContractMark(c.version, c.defined, c.defined_by, tuple(ids[t] for t in c.acceptance), (), "first"))
            continue
        added, removed = amendment_ids(stored, c.version)
        if c.answers:
            basis, named = "answers", added or removed
            parts = tuple((x, next((link for rejection, link in links.get(x, []) if rejection == c.answers), "")) for x in named)
        elif c.initiated == "user":
            basis, parts = "user", ()
        elif c.defined_by in ("", ROOT):
            basis = "legacy"
            parts = tuple((x, links[x][0][1] if x in confirmed and links.get(x) else "") for x in added)
        else:
            basis, parts = "agent", ()
        marks.append(ContractMark(c.version, c.defined, c.defined_by, added, removed, basis, rejections.get(c.answers, c.answers), parts))
    return tuple(marks)


def _item_kind(p: Playbook, before: Playbook | None) -> str:
    """``step`` or ``rule`` for the item ``p`` changed: found in ``p`` or, for a retired one, in the version before; ``""`` when there is none."""
    for version in (p, before):
        for found in (version.items or ()) if version is not None else ():
            if found.id == p.item:
                return found.kind
    return ""


def playbook_marks(owner: str, playbooks: Sequence[Playbook], criteria: Sequence[Criterion], cases: Sequence[Case]) -> tuple[PlaybookMark, ...]:
    """One mark per stored version of the playbook (``playbooks``, oldest first), counted against the version before it. ``criteria`` are the
    service's, ``cases`` its cases (the user's link notes that a version may cite)."""
    by_id = {c.id: c for c in criteria}
    link_notes = {note.id: note for case in cases for verdict in case.verdicts for note in verdict.link_notes}
    client = parent(owner) or ROOT
    marks: list[PlaybookMark] = []
    for position, p in enumerate(playbooks):
        before = playbooks[position - 1].body if position else ""
        changed, removed = changed_lines(before, p.body), changed_lines(p.body, before)
        shown = tuple(x for x in p.evidence if _EVIDENCE_ID.fullmatch(x))
        cited: dict[str, Criterion] = {}
        for x in p.evidence:
            note = link_notes.get(x)
            if _CRITERION.fullmatch(x) and x in by_id:
                cited.setdefault(x, by_id[x])
            elif note is not None and verdict_tier(note) == "human":  # the user's recorded yes stands for the criteria it names (P1)
                cited.update({k: by_id[k] for k in link_ids(note) if k in by_id})
        own = [criterion_words(line, list(cited.values())) is not None for line in changed]
        tagged = [_TAG.search(line) is not None for line in changed]
        basis = p.admitted if p.admitted in _BASES else "client" if p.by == client else "legacy"
        if p.op:  # an item version says what it restores in its file
            restores = p.restores or None
        else:  # a legacy one by the text it came back to
            restores = next((q.version for q in reversed(playbooks[:position]) if q.body == p.body), None) if basis == "restore" else None
        marks.append(PlaybookMark(
            p.version, p.revised, p.by, basis,
            restores=restores,
            evidence=shown, evidence_other=len(p.evidence) - len(shown), changed=len(changed), removed=len(removed),
            own_words=sum(own) if basis == "c" else None, beyond=len(own) - sum(own) if basis == "c" else None,
            tagged=sum(tagged) if basis == "b" else None, untagged=len(tagged) - sum(tagged) if basis == "b" else None,
            cited=tuple((c.id, c.text) for c in cited.values()),
            lines=tuple((clip_line(line, LINE_CLIP), is_own) for line, is_own in zip(changed[:LINES_LISTED], own)),
            lines_more=max(0, len(changed) - LINES_LISTED),
            op=p.op, item=p.item, item_kind=_item_kind(p, playbooks[position - 1] if position else None) if p.item else "",
            related=tuple(p.related), acknowledged=p.acknowledged, acknowledged_by=client if p.acknowledged else "",
            items=len(p.items or ()) if p.op == "migrate" else 0,
        ))
    return tuple(marks)


def top_up_marks(cases: Sequence[Case]) -> tuple[TopUpMark, ...]:
    """One mark per top-up of the cases, in the order of the cases and, inside a case, of the ids."""
    return tuple(TopUpMark(stamp_of(t.id), case.id, t.id, t.kind, t.amount) for case in cases for t in case.top_ups.items)
