"""The item grammar of an item-format ``PLAYBOOK.md`` (design 4.1): ``render_items`` writes the canonical markdown, ``parse_items`` reads it back,
and ``parse_items(render_items(x)) == x`` for every item list the runtime writes. Pure: no file is read or written here."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from ..kernel import JsonObject
from .api import PlaybookItem, PlaybookSection

HEADING = re.compile(r"#{1,6}(?:\s|$)")
ITEM_LINE = re.compile(r"(?:(\d+)\.|-) \[P(\d+)\](?: |$)")  # `<n>. [P<k>] ` or `- [P<k>] ` (the space may be gone at the end of a line)
STEPS_HEADING = "## Steps"
RULES_HEADING = "## Rules"
CONTINUATION = "   "  # what every further line of an item renders after
_WHEN, _THEN = "WHEN ", " THEN "


def default_numbered(heading: str) -> bool:
    """Whether the steps of a section that holds none render numbered: only the runtime's own ``## Steps`` does (a section emptied by retires keeps
    no memory of its list style, so the next item of any other heading renders as a bullet)."""
    return heading.rstrip() == STEPS_HEADING


@dataclass(frozen=True)
class ItemsParse:
    """What ``parse_items`` found: the items in body order and the sections, or ``error`` (``"line {n}: {why}"``) with neither."""

    items: tuple[PlaybookItem, ...] = ()
    sections: tuple[PlaybookSection, ...] = ()
    error: str = ""


def _id_number(item_id: str) -> int:
    digits = item_id[1:]
    return int(digits) if digits.isdigit() else 0


def canonical_why(ids: Sequence[str]) -> tuple[str, ...]:
    """The ``WHY`` ids of an item in their one order: the ``R`` ids by number, then the others (the ``C`` ids) by number; each once."""
    unique = dict.fromkeys(str(i).strip().upper() for i in ids if str(i).strip())
    return tuple(sorted(unique, key=lambda i: (i[:1] != "R", i[:1], _id_number(i), i)))


def why_text(ids: Sequence[str]) -> str:
    """The ids after ``WHY``: ``R2, R3; C6`` (the groups by letter, ``; `` between them, an empty group left out)."""
    ids = canonical_why(ids)
    groups = [[i for i in ids if i[:1] == "R"], [i for i in ids if i[:1] != "R"]]
    return "; ".join(", ".join(g) for g in groups if g)


def _item_lines(item: PlaybookItem, numbered: bool, position: int) -> list[str]:
    suffix = f" WHY {why_text(item.why)}" if item.why else ""
    if item.kind == "rule":
        return [f"- [{item.id}] {_WHEN}{item.when}{_THEN}{item.text}{suffix}"]
    lines = item.text.split("\n")
    if item.why:
        lines[-1] += f" (WHY {why_text(item.why)})"
    marker = f"{position}. [{item.id}] " if numbered else f"- [{item.id}] "
    return [marker + lines[0], *(CONTINUATION + line if line else "" for line in lines[1:])]


def render_items(items: Sequence[PlaybookItem], sections: Sequence[PlaybookSection]) -> str:
    """The canonical body of an item-format playbook (pure). Every section renders its heading line verbatim, empty or not (the section ``""``
    renders none), one blank line before every heading but the first line; a step is ``<n>. [P<k>] ...`` in a numbered section and ``- [P<k>] ...``
    in the others, a gated one ending ``(WHY ids)``, its further lines after 3 spaces; a rule is one line ``- [P<k>] WHEN w THEN t WHY ids``."""
    by_id = {i.id: i for i in items}
    out: list[str] = []
    for section in sections:
        if section.heading:
            if out:
                out.append("")
            out.append(section.heading)
        for position, item_id in enumerate(section.ids, start=1):
            out.extend(_item_lines(by_id[item_id], section.numbered, position))
    return "\n".join(out)


def _meta_rules(meta: Mapping[str, object]) -> tuple[str, ...]:
    value = meta.get("rules")
    return tuple(str(i).strip().upper() for i in value) if isinstance(value, list) else ()


def _meta_why(meta: Mapping[str, object]) -> dict[str, tuple[str, ...]]:
    value = meta.get("why")
    if not isinstance(value, dict):
        return {}
    return {str(k).strip().upper(): canonical_why([str(x) for x in v]) for k, v in value.items() if isinstance(v, list) and v}


@dataclass
class _Draft:
    """An item being read: its lines and where it starts."""

    id: str
    line: int
    lines: list[str]
    section: int


def parse_items(body: str, meta: JsonObject) -> ItemsParse:
    """The items and sections of an item-format ``body`` (pure; ``meta`` is the frontmatter: ``rules`` and ``why`` matter). A body that does not
    parse gives ``ItemsParse.error`` instead of items, never an exception; the grammar is design 4.1's."""
    rules = _meta_rules(meta)
    why = _meta_why(meta)
    headings: list[str] = []
    firsts: list[bool | None] = []  # per section: whether its first item was numbered (None: it holds none)
    drafts: list[_Draft] = []
    blank = 0
    current: _Draft | None = None
    for n, raw in enumerate(body.split("\n"), start=1):
        line = raw.rstrip("\r")
        if not line.strip():
            blank += 1
            continue
        if HEADING.match(line):
            headings.append(line)
            firsts.append(None)
            current, blank = None, 0
        elif (m := ITEM_LINE.match(line)) is not None:
            item_id = f"P{int(m.group(2))}"
            if any(d.id == item_id for d in drafts):
                return ItemsParse(error=f"line {n}: the id {item_id} is used twice")
            if not headings:  # the text before the first heading
                headings.append("")
                firsts.append(None)
            if firsts[-1] is None:
                firsts[-1] = m.group(1) is not None
            current = _Draft(item_id, n, [line[m.end():]], len(headings) - 1)
            drafts.append(current)
            blank = 0
        elif current is not None and line.startswith(CONTINUATION):
            current.lines.extend([""] * blank)
            current.lines.append(line[len(CONTINUATION):])
            blank = 0
        else:
            return ItemsParse(error=f"line {n}: not a heading, an item (`<n>. [P<k>] ` or `- [P<k>] `) or a line indented by 3 spaces under one")
    items: list[PlaybookItem] = []
    for d in drafts:
        built = _built(d, headings[d.section], why.get(d.id, ()), d.id in rules)
        if isinstance(built, str):
            return ItemsParse(error=built)
        items.append(built)
    sections = tuple(
        PlaybookSection(headings[k], default_numbered(headings[k]) if firsts[k] is None else firsts[k] is True, tuple(d.id for d in drafts if d.section == k))
        for k in range(len(headings))
    )
    error = _rules_error(drafts, headings, rules)
    return ItemsParse(error=error) if error else ItemsParse(tuple(items), sections)


def _built(draft: _Draft, heading: str, why: tuple[str, ...], is_rule: bool) -> PlaybookItem | str:
    """The item a draft is, or the parse error of its line."""
    lines = list(draft.lines)
    if why:
        suffix = f" WHY {why_text(why)}" if is_rule else f" (WHY {why_text(why)})"
        if not lines[-1].endswith(suffix):
            return f"line {draft.line}: the WHY of {draft.id} is not the one in the frontmatter (`{suffix.strip()}` is expected at the end)"
        lines[-1] = lines[-1][: -len(suffix)]
    if not is_rule:
        return PlaybookItem(draft.id, "step", heading, "\n".join(lines), "", why)
    if len(lines) > 1 or not lines[0].startswith(_WHEN) or _THEN not in lines[0]:
        return f"line {draft.line}: the rule {draft.id} is not one line `WHEN ... THEN ...`"
    when, _, then = lines[0][len(_WHEN):].partition(_THEN)
    return PlaybookItem(draft.id, "rule", heading, then, when, why)


def _rules_error(drafts: Sequence[_Draft], headings: Sequence[str], rules: tuple[str, ...]) -> str:
    """With rules in the frontmatter, the last section must be headed ``## Rules`` and hold exactly the rule items, in order; else the error."""
    if not rules:
        return ""
    last = len(headings) - 1
    for d in drafts:
        inside = d.section == last and headings[last].rstrip() == RULES_HEADING
        if (d.id in rules) != inside:
            return f"line {d.line}: " + (
                f"the rule {d.id} is not in the last section, `{RULES_HEADING}`" if d.id in rules else f"the step {d.id} is in the rules section"
            )
    present = [d.id for d in drafts if d.id in rules]
    if present != list(rules):
        missing = [r for r in rules if r not in present]
        return f"line {max((d.line for d in drafts), default=1)}: " + (
            f"the rule {missing[0]} is not in the body" if missing else "the rules are not in the order of the frontmatter"
        )
    return ""
