"""What Phase 1's watch says of a service's playbook, for D11 (design 4.3, 10.4; pure): the retire candidates of the cap, and each item the watch retired with the way its
related rejections touched it.

A rejection is **direct** when its own id, the criteria its effective human link names or the criteria the user confirmed meet the refs the item cited; it is a
**refinement** when it meets them only through the answering contract version (the question's id, the ids it removes) or through the lineage of a criterion it names.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timezone

from ..reflection import Assertion, ContractMark, ServiceRecord, lineage_class
from ..services import ItemWatch, Playbook
from ._views import WatchRetire

_END = datetime.max.replace(tzinfo=timezone.utc)


def _number(item: str) -> int:
    return int(item[1:]) if item[1:].isdigit() else 0


def retire_candidates(current: Playbook, versions: Sequence[Playbook], watches: Sequence[ItemWatch]) -> tuple[str, ...]:
    """The retire candidates of Phase 1 10 (the lists of the cap's refusal): the live items in ``new`` that continue no other watch and whose watch rests on no
    regression assertion, oldest text first."""
    by_version = {p.version: p for p in versions}
    by_item = {w.id: w for w in watches}
    found: list[tuple[int, int, str]] = []
    for item in current.items or ():
        w = by_item.get(item.id)
        why = by_version[w.text_version].why.get(item.id) if w is not None and w.text_version in by_version else None
        if w is not None and w.state == "new" and not w.carried and why is not None and not any(x.startswith("R") for x in why):
            found.append((w.text_version, _number(item.id), item.id))
    return tuple(i for _, _, i in sorted(found))


def _answering(record: ServiceRecord, a: Assertion) -> ContractMark | None:
    return next((m for m in record.timeline if isinstance(m, ContractMark) and m.basis == "answers" and m.answers == a.id), None)


def _classified(record: ServiceRecord, a: Assertion, refs: frozenset[str]) -> tuple[str, frozenset[str]]:
    """How the rejection ``a`` meets ``refs``: ``direct`` (with the refs it meets) or ``refined``; a rejection the files cannot place is read as direct."""
    mark = _answering(record, a)
    answer = next((c for c in record.contracts if c.answers == a.verdict.message.id), None)
    links = {x for x in a.verdict.links if x != "none"} if a.verdict.links_tier == "human" else set()
    own = {a.id, *a.about, *links, *a.verdict.confirmed}
    if met := own & refs:
        return "direct", frozenset(met)
    when = (mark.when if mark is not None else None) or a.verdict.created or _END
    through = {*([answer.about] if answer is not None and answer.about else []), *(mark.removes if mark is not None else ())}
    for cid in [x for x in own | through if x.startswith("C")]:
        through |= lineage_class(record.contracts, cid, when)
    return ("refined", frozenset(through & refs)) if through & refs else ("direct", frozenset())


def _replaced(record: ServiceRecord, a: Assertion, refs: frozenset[str]) -> tuple[tuple[str, str], ...]:
    """The (old, new) criteria the answer to ``a`` replaced, among the criteria the item cited or their lineage."""
    mark = _answering(record, a)
    when = (mark.when if mark is not None else None) or a.verdict.created or _END
    if mark is not None:
        return tuple(sorted((old, new) for old in mark.removes for new in mark.adds if old in refs or old in lineage_class(record.contracts, new, when)))
    return tuple(sorted((old, cid) for cid in a.about for old in lineage_class(record.contracts, cid, when) - {cid} if old in refs))


def watch_retires(record: ServiceRecord, versions: Sequence[Playbook]) -> tuple[WatchRetire, ...]:
    """Every retire of an item by the watch (``ItemWatch.retires``) with its related rejections split into direct ones and refinements."""
    by_version = {p.version: p for p in versions}
    by_id = {a.id: a for a in record.assertions}
    found: list[WatchRetire] = []
    for w in record.watch:
        refs = frozenset(by_version[w.text_version].why.get(w.id, ())) if w.text_version in by_version else frozenset()
        for version, rejections in w.retires:
            direct: list[str] = []
            refined: list[str] = []
            met: set[str] = set()
            replaced: set[tuple[str, str]] = set()
            for ref in rejections:
                a = by_id.get(ref)
                if a is None:
                    continue
                how, hit = _classified(record, a, refs)
                if how == "direct":
                    direct.append(ref)
                    met |= hit
                else:
                    refined.append(ref)
                    replaced |= set(_replaced(record, a, refs))
            criterion = ", ".join(sorted((x for x in met if x.startswith("C")), key=_number)) or ", ".join(sorted((x for x in refs if x.startswith("C")), key=_number))
            found.append(WatchRetire(w.id, version, tuple(direct), criterion, tuple(refined), tuple(sorted(replaced))))
    return tuple(found)
