"""The text and the JSON of the retro brief (design 4.7; pure): the block the assistant shows to the user exactly as written, then Details and the items for the assistant."""

from __future__ import annotations

from ..kernel import JsonObject
from ._ladder import rung_line
from ._texts import (
    BLOCK_END, DETAILS, HEADING, HEADING_AGAIN, LEDGER_NOTES, NEXT, NO_ITEMS, NO_QUESTIONS, OBJECTION, PROPOSALS, QUESTIONS, QUESTIONS_AGAIN,
)
from .api import Brief, Item, Section

BLOCK_SECTIONS = (("d1", "What you said"), ("d2", "What got past a check"), ("d7", "Did past changes hold"), ("d8", "Changes to your organization"))


def _section(brief: Brief, key: str) -> Section | None:
    return next((s for s in brief.sections if s.key == key), None)


def _heading(brief: Brief) -> str:
    if brief.shown_again:
        return HEADING_AGAIN.format(id=brief.id, at=brief.shown_again)
    return HEADING.format(id=brief.id, since_words=brief.since_words, v=brief.verdicts, c=brief.cases)


def _question(item: Item) -> str:
    return f"{item.n}. {item.question}" + (" (taken)" if item.state == "taken" else " (no longer suggested)" if item.state == "no longer suggested" else "")


def _item_lines(item: Item) -> list[str]:
    lines = [f"{item.n}. {rung_line(item.kind, item.rung, item.rung_why)}", f"   Evidence: {', '.join(item.evidence)}"]
    if item.state:
        lines.append(f"   State: {item.state}")
    if item.cost:
        lines.append(f"   Cost: {item.cost}")
    if item.objection:
        lines.append(f"   {OBJECTION.format(result=item.objection)}")
    lines.append(f"   On yes: {item.call}")
    lines += [f"   {x}" for x in item.blueprint.splitlines()]
    lines.append(f"   Revert: {item.revert}")
    lines += [f"   {x}" for x in item.revert_blueprint.splitlines()]
    lines += [f"   Note: {x}" for x in item.notes]
    return lines


def render_brief(brief: Brief) -> str:
    """The brief as text: the block from ``RETRO BRIEF`` to ``RETRO BRIEF END``, then Details, the items and the instruction to the assistant."""
    out = [_heading(brief), *(n for n in brief.notes if n.startswith(LEDGER_NOTES))]
    for key, heading in BLOCK_SECTIONS:
        if (section := _section(brief, key)) is not None:
            out += [f"{heading}:", *section.block]
    if (proposals := _section(brief, "d10")) is not None and dict(proposals.counts).get("proposals_refused"):
        out += [PROPOSALS.format(n=dict(proposals.counts)["proposals_refused"]), *proposals.block]
    if brief.items:
        out += [QUESTIONS_AGAIN.format(id=brief.id) if brief.shown_again else QUESTIONS, *(_question(i) for i in brief.items)]
    else:
        out.append(NO_QUESTIONS)
    out += [BLOCK_END, DETAILS]
    out += [f"{n}" for n in brief.notes if not n.startswith(LEDGER_NOTES)]
    for section in brief.sections:
        out += [f"{section.key.upper()} {section.heading}:", *(section.details if not section.error else [f"- cannot be read ({section.error})"])]
    if brief.items:
        out.append("Items:")
        for item in brief.items:
            out += _item_lines(item)
    else:
        out.append(NO_ITEMS.format(k=len(brief.held_back)))
    out.append(NEXT)
    return "\n".join(out)


def _item_json(item: Item) -> JsonObject:
    return {
        "n": item.n, "kind": item.kind, "key": item.key, "evidence": list(item.evidence), "weight": item.weight, "rung": item.rung, "rung_why": item.rung_why,
        "question": item.question, "cost": item.cost, "objection": item.objection, "call": item.call, "revert": item.revert, "blueprint": item.blueprint,
        "revert_blueprint": item.revert_blueprint, "effect": dict(item.effect), "notes": list(item.notes), "state": item.state,
    }


def brief_json(brief: Brief) -> JsonObject:
    """The brief for a program (``hirearchy retro --json``): every section as a key with its lines and every count with its N, the items and the held-back candidates."""
    sections: JsonObject = {
        s.key: {"heading": s.heading, "block": list(s.block), "details": list(s.details), "counts": dict(s.counts), "error": s.error} for s in brief.sections
    }
    return {
        "id": brief.id, "at": brief.at.isoformat(), "since": brief.since.isoformat() if brief.since is not None else None, "since_words": brief.since_words,
        "verdicts": brief.verdicts, "cases": brief.cases, "recorded": brief.recorded, "shown_again": brief.shown_again or None, "notes": list(brief.notes),
        "sections": sections, "items": [_item_json(i) for i in brief.items], "held_back": [_item_json(i) for i in brief.held_back],
    }

