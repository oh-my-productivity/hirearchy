"""The changes D7 weighs besides the amendments and the playbook items (design 4.4, rows 3 and 4; pure): the charter edits and the structural changes.

A change that is the effect of an item of a held brief is weighed by its target: a ``service`` item by the requests of the new service (exercised) and a later one-off task of the
same shape (recurred); a ``checker-add`` or ``checker-fix`` item by the later judged cases of the service (exercised) and a later rejection on the criterion's class (recurred). A
change that is the effect of no item reads ``no target recorded: not evaluated``. A change of the plan the user first approved, or one a later change took back, is not listed:
D8 names the first, and the second has no outcome."""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import replace
from datetime import datetime

from ._changes import BACK_LABEL, PLAN_LABEL, Change, changes_of
from ._facts import Facts
from ._items import renamed
from ._shapes import criteria_key
from ._views import Occasion, Tracked
from .api import BriefRecord, RecordedItem

_ITEM = re.compile(r", item (B\d+)\.(\d+)$")
_NOT_LISTED = (PLAN_LABEL.split("{")[0], BACK_LABEL.split("{")[0])  # "from the plan you approved (" and "taken back: the change "


def _after(occasions: Sequence[Occasion], when: datetime | None) -> tuple[Occasion, ...]:
    return tuple(o for o in occasions if when is not None and o.when is not None and o.when > when)


def _item_of(change: Change, briefs: Sequence[BriefRecord], facts: Facts) -> tuple[str, RecordedItem] | None:
    """The item of a held brief the change is the effect of, with its id: the one its label names (``, item B1.2``), else, for a service, the item whose shape the new service has."""
    found = _ITEM.search(change.label)
    for record in briefs:
        if change.when is None or record.at >= change.when:
            continue
        for item in record.items:
            named = found is not None and (record.id, str(item.n)) == found.groups()
            shaped = found is None and change.kind == "service-defined" and item.kind == "service" and renamed(item, facts.effects) == change.subject
            if named or shaped:
                return f"{record.id}.{item.n}", item
    return None


def _weighed(change: Change, item: RecordedItem, facts: Facts) -> tuple[tuple[Occasion, ...], tuple[Occasion, ...]]:
    """Where the change was exercised after it was made, and where its target recurred."""
    when = change.when
    if item.kind == "service":
        keys = {k for case in item.evidence if (k := facts.effects.shapes.get(case))}
        again = tuple(Occasion(o.id, "", o.created) for o in facts.one_offs if o.judged and o.created is not None and when is not None and o.created > when and criteria_key(o.criteria) in keys)
        return _after(facts.judged.get(change.subject.split("/", 1)[-1], ()), when), again
    parts = item.key.split("|")
    if item.kind not in ("checker-add", "checker-fix") or len(parts) < 3:
        return (), ()
    service, criterion = parts[1], parts[-1]
    again = tuple(
        Occasion(r.case, "", r.when) for r in facts.rejected.get(service, ()) if r.when is not None and when is not None and r.when > when and any(criterion in k for k in r.classes)
    )
    return _after(facts.judged.get(service, ()), when), again


def structural_tracked(facts: Facts, briefs: tuple[BriefRecord, ...]) -> tuple[Tracked, ...]:
    """The charter edits and the structural changes D7 weighs, oldest first. The limit and the lines one extension made belong to the item its agent or service has."""
    changes = [c for c in changes_of(replace(facts.changes, briefs=briefs, effects=facts.effects), None).changes if c.when is not None and not c.label.startswith(_NOT_LISTED)]
    items = [_item_of(c, briefs, facts) for c in changes]
    by_plan = {c.plan_id: found for c, found in zip(changes, items) if c.plan_id and found is not None}
    out: list[Tracked] = []
    for c, found in zip(changes, items):
        found = found or by_plan.get(c.plan_id)
        kind = "charter" if c.kind in ("charter", "depth") else "structural"
        if found is None:
            out.append(Tracked(c.text, kind, c.when, False))
            continue
        ref, item = found
        exercised, again = _weighed(c, item, facts)
        out.append(Tracked(f"{c.text}, item {ref}", kind, c.when, True, exercised, again))
    return tuple(out)
