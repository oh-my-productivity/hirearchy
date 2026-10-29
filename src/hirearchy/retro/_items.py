"""Items (design 4.5a; pure): the candidates of the signals become at most three numbered items.

The order is total (weight, then rung, then the oldest evidence, then the kind, then the key), so two runs give the same brief. A candidate whose key a recorded brief already
offered is suppressed until its evidence holds an id that item did not have; a ``clarify`` is asked once per wording; a ``cause`` lapses at most twice; a candidate whose effect
is already in the files is dropped. An item of the last brief that was not taken lapses at the next recorded brief."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace

from ..services import line_key
from ._views import EffectFacts, Fate
from .api import ITEM_KINDS, BriefRecord, Item, RecordedItem

__all__ = ["EffectFacts", "Selection", "fates", "select", "taken_by", "to_record"]

LAPSES_MAX = 2  # a cause is asked again after it lapsed, but not a third time


@dataclass(frozen=True)
class Selection:
    """The items (numbered from 1), the candidates held back beyond the cap, and the keys of the last brief's items that lapse now (not taken)."""

    items: tuple[Item, ...]
    held_back: tuple[Item, ...]
    lapsed: tuple[str, ...] = ()


def _order(item: Item) -> tuple[int, int, str, int, str]:
    kind = ITEM_KINDS.index(item.kind) if item.kind in ITEM_KINDS else len(ITEM_KINDS)
    return (-item.weight, item.rung, item.oldest or "\uffff", kind, item.key)


def _lapses(key: str, records: Sequence[BriefRecord], taken: frozenset[str]) -> int:
    """How often the item with this key lapsed: the most any record counted, plus one when the last brief offered it and it was not taken."""
    last = records[-1] if records else None
    before = max((i.lapsed for r in records for i in r.items if i.key == key), default=0)
    return before + (1 if last is not None and key not in taken and any(i.key == key for i in last.items) else 0)


def select(candidates: Sequence[Item], records: Sequence[BriefRecord], asked: frozenset[str], taken: frozenset[str], cap: int) -> Selection:
    """The items of a brief from the candidates, given the records held, the keys ever asked, the keys whose effect is already seen and the cap (1 to 3)."""
    seen: dict[str, set[str]] = {}
    for record in records:
        for item in record.items:
            seen.setdefault(item.key, set()).update(item.evidence)
    kept: list[Item] = []
    for c in candidates:
        if c.key in taken:
            continue
        if c.key in asked:
            if c.kind == "clarify" or (c.kind == "cause" and _lapses(c.key, records, taken) >= LAPSES_MAX):
                continue
            if c.kind != "cause" and (c.key not in seen or not set(c.evidence) - seen[c.key]):
                continue
        kept.append(c)
    ranked = sorted(kept, key=_order)
    last = records[-1] if records else None
    lapsed = tuple(i.key for i in last.items if i.key not in taken) if last is not None else ()
    return Selection(tuple(replace(c, n=n) for n, c in enumerate(ranked[:cap], start=1)), tuple(ranked[cap:]), lapsed)


def to_record(items: Sequence[Item], records: Sequence[BriefRecord], taken: frozenset[str]) -> tuple[RecordedItem, ...]:
    """The items as the ledger keeps them: ids and keys only, with how often each key lapsed before."""
    return tuple(RecordedItem(i.n, i.kind, i.key, i.evidence, dict(i.effect), _lapses(i.key, records, taken)) for i in items)


def _renamed(item: RecordedItem, facts: EffectFacts) -> str:
    """The service an extension defined for the owner of a ``service`` item under another name: its criteria key equals that of one of the item's tasks (``""`` for none)."""
    owner = str(item.effect.get("service", "")).split("/")[0]
    keys = {k for case in item.evidence if (k := facts.shapes.get(case))}
    return next((f"{o}/{n}" for o, n, key in facts.defined if o == owner and key in keys), "")


def _seen(item: RecordedItem, facts: EffectFacts) -> str:
    """What the files show of an item's effect (``""`` for none), by kind."""
    e = item.effect
    checks: dict[str, Callable[[], str]] = {
        "service": lambda: f"{named} defined" if (named := e.get("service") if e.get("service") in facts.services else _renamed(item, facts)) else "",
        "checker-add": lambda: f"a checker joined {e.get('owner')}'s team" if e.get("owner") in facts.checkers else "",
        "checker-fix": lambda: f"the line is in {e.get('agent')}'s charter" if f"{e.get('agent')}|{line_key(e.get('line', ''))}" in facts.lines else "",
        "worker": lambda: f"a worker joined {e.get('lead')}'s team" if e.get("lead") in facts.workers else "",
        "retire": lambda: f"{e.get('agent')} retired" if e.get("agent") in facts.retired else "",
        "reclaim": lambda: f"{e.get('agent')}'s runs came back" if e.get("agent") in facts.reclaimed else "",
        "clarify": lambda: f"{e.get('service')} {e.get('criterion')} was settled" if f"{e.get('service')}/{e.get('criterion')}" in facts.clarified else "",
        "cause": lambda: f"{e.get('rejection')} was answered" if e.get("rejection") in facts.answered else "",
        "answer": lambda: f"{e.get('rejection')} was answered" if e.get("rejection") in facts.answered else "",
    }
    return checks.get(item.kind, lambda: "")()


def taken_by(item: RecordedItem, facts: EffectFacts) -> str:
    """The effect of ``item`` the files show (the words D13 puts in parentheses), ``""`` when it is not taken."""
    return _seen(item, facts)


def fates(last: BriefRecord | None, facts: EffectFacts, *, recorded: bool) -> tuple[Fate, ...]:
    """What became of each item of the last brief: ``taken`` with the effect seen, else ``lapsed`` (when a new brief is being recorded) or ``open``."""
    if last is None:
        return ()
    found = []
    for item in last.items:
        seen = taken_by(item, facts)
        found.append(Fate(f"{last.id}.{item.n}", item.kind, "taken" if seen else "lapsed" if recorded else "open", seen))
    return tuple(found)
