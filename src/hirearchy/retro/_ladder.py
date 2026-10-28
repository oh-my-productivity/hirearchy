"""The change ladder of 08 4.4 (design section 3): the seven rungs, cheapest first, and the line that names an item's rung and why a cheaper one is not enough (pure)."""

from __future__ import annotations

RUNGS = ("clarify", "adjust the standard", "add slack", "add a checker or integrator", "split", "add a layer", "merge or retire")


def rung_line(kind: str, rung: int, why: str) -> str:
    """``{kind} (rung {r} of 7, {rung name}: {why not cheaper})``; an item with no rung (a budget, not a structure) says so."""
    if not 1 <= rung <= len(RUNGS):
        return f"{kind} (no rung: it moves budget, not structure)"
    return f"{kind} (rung {rung} of {len(RUNGS)}, {RUNGS[rung - 1]}: {why})"
