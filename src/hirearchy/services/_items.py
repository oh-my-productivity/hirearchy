"""The item grammar of an item-format ``PLAYBOOK.md`` (design 4.1): ``render_items`` writes the canonical markdown, ``parse_items`` reads it back,
and ``parse_items(render_items(x)) == x`` for every item list the runtime writes. Pure: no file is read or written here."""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace

from ..kernel import JsonObject
from .api import PlaybookItem, PlaybookSection, line_key

HEADING = re.compile(r"#{1,6}(?:\s|$)")
ITEM_LINE = re.compile(r"(?:(\d+)\.|-) \[P(\d+)\](?: |$)")  # `<n>. [P<k>] ` or `- [P<k>] ` (the space may be gone at the end of a line)
STEPS_HEADING = "## Steps"
RULES_HEADING = "## Rules"
CONTINUATION = "   "  # what every further line of an item renders after
_WHEN, _THEN = "WHEN ", " THEN "
RUNTIME_WATCH = "runtime (watch)"  # `by` of a version the watch retire wrote
RUNTIME_MIGRATION = "runtime (migration)"  # `by` of a version the migration wrote


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


def rules_of(meta: Mapping[str, object]) -> tuple[str, ...]:
    """The ids of the live rule items in a frontmatter (``rules``); none for a value that is no list."""
    value = meta.get("rules")
    return tuple(str(i).strip().upper() for i in value) if isinstance(value, list) else ()


def why_of(meta: Mapping[str, object]) -> dict[str, tuple[str, ...]]:
    """The ``why`` map of a frontmatter: the canonical ``WHY`` ids of every gated item; empty for a value that is no map."""
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
    rules = rules_of(meta)
    why = why_of(meta)
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


# ----------------------------------------------------------------------------------------------------------------------- migration (4.4)

LIST_MARKER = re.compile(r"(?:[-*+]|\d+[.)])(?:[ \t]+|$)")  # a top-level list item: its marker, the blanks after it
FENCE = re.compile(r"(`{3,}|~{3,})")
FALLBACK_SECTIONS = "; one item per section: the per-block split did not keep every line"
FALLBACK_WHOLE = "; one item: neither split kept every line"

Split = tuple[tuple[PlaybookItem, ...], tuple[PlaybookSection, ...]]
Splitter = Callable[[str], Split]


@dataclass(frozen=True)
class Migration:
    """A legacy body as step items: the items (ids ``P1..Pm`` in file order), the sections, and ``reason``, the suffix a fallback adds to the
    migration's reason (``""`` for the per-block split)."""

    items: tuple[PlaybookItem, ...] = ()
    sections: tuple[PlaybookSection, ...] = ()
    reason: str = ""


def _fence_end(lines: Sequence[str], start: int) -> int:
    """The index of the line that closes the fence opened at ``start`` (the last line when it never closes)."""
    mark = FENCE.match(lines[start])
    assert mark is not None
    for k in range(start + 1, len(lines)):
        closing = lines[k].strip()
        if closing and closing[0] == mark.group(1)[0] and set(closing) == {closing[0]} and len(closing) >= len(mark.group(1)):
            return k
    return len(lines) - 1


def _parts(lines: Sequence[str]) -> list[tuple[str, list[str]]]:
    """The lines of a body as ``(heading, content lines)`` per section, in order; a heading inside a fence is no heading. The first section's heading
    is ``""`` (the text before the first heading) and it is kept only when it holds a line."""
    parts: list[tuple[str, list[str]]] = [("", [])]
    k = 0
    while k < len(lines):
        line = lines[k]
        if HEADING.match(line):
            parts.append((line, []))
        elif FENCE.match(line):
            end = _fence_end(lines, k)
            parts[-1][1].extend(lines[k : end + 1])
            k = end
        else:
            parts[-1][1].append(line)
        k += 1
    return parts if any(line.strip() for line in parts[0][1]) else parts[1:]


def _starts_block(line: str) -> bool:
    return bool(HEADING.match(line) or FENCE.match(line) or LIST_MARKER.match(line) or line.startswith("|"))


def _blocks(lines: Sequence[str]) -> list[list[str]]:
    """The blocks of the content lines of one section: list items (with their indented and lazy continuation lines and the blank lines between),
    fenced blocks (with their inner blank lines), tables and paragraphs; every non-blank line in exactly one block."""
    blocks: list[list[str]] = []
    k = 0
    while k < len(lines):
        line = lines[k]
        if not line.strip():
            k += 1
            continue
        end = k
        if FENCE.match(line):
            end = _fence_end(lines, k)
        elif LIST_MARKER.match(line):
            while end + 1 < len(lines):
                nxt = lines[end + 1]
                if not nxt.strip():
                    ahead = next((j for j in range(end + 2, len(lines)) if lines[j].strip()), None)
                    if ahead is None or not lines[ahead][:1].isspace():
                        break
                    end = ahead - 1
                elif nxt[:1].isspace() or not _starts_block(nxt):  # indented, or a lazy continuation
                    end += 1
                else:
                    break
        elif line.startswith("|"):
            while end + 1 < len(lines) and lines[end + 1].startswith("|"):
                end += 1
        else:
            while end + 1 < len(lines) and lines[end + 1].strip() and not _starts_block(lines[end + 1]):
                end += 1
        block = list(lines[k : end + 1])
        while not block[-1].strip():
            block.pop()
        blocks.append(block)
        k = end + 1
    return blocks


def _text_of(lines: Sequence[str]) -> str:
    """The lines of an item as its text: a blank line is empty, every other line verbatim."""
    return "\n".join(line if line.strip() else "" for line in lines)


def _assemble(sections: Sequence[tuple[str, bool | None, list[list[str]]]]) -> Split:
    """Items ``P1..Pm`` in order and their sections from ``(heading, numbered, item lines)``; ``numbered`` None: the heading's default."""
    items: list[PlaybookItem] = []
    out: list[PlaybookSection] = []
    for heading, numbered, texts in sections:
        ids: list[str] = []
        for lines in texts:
            ids.append(f"P{len(items) + 1}")
            items.append(PlaybookItem(ids[-1], "step", heading, _text_of(lines)))
        out.append(PlaybookSection(heading, default_numbered(heading) if numbered is None or not ids else numbered, tuple(ids)))
    return tuple(items), tuple(out)


def split_blocks(body: str) -> Split:
    """The per-block split (4.4): a heading starts a section, and each block becomes one step; its first line loses its list marker."""
    sections: list[tuple[str, bool | None, list[list[str]]]] = []
    for heading, content in _parts(body.splitlines()):
        texts: list[list[str]] = []
        numbered: bool | None = None
        for block in _blocks(content):
            marker = LIST_MARKER.match(block[0])
            if numbered is None:
                numbered = marker is not None and block[0][:1].isdigit()
            texts.append([block[0][marker.end():] if marker else block[0], *block[1:]])
        sections.append((heading, numbered, texts))
    return _assemble(sections)


def split_sections(body: str) -> Split:
    """The first fallback: each section is one multi-line step (its lines verbatim)."""
    sections: list[tuple[str, bool | None, list[list[str]]]] = []
    for heading, content in _parts(body.splitlines()):
        lines = list(content)
        while lines and not lines[0].strip():
            lines.pop(0)
        while lines and not lines[-1].strip():
            lines.pop()
        sections.append((heading, False, [lines] if lines else []))
    return _assemble(sections)


def split_whole(body: str) -> Split:
    """The last fallback: the whole body is the single step ``P1`` (every line after the first is a continuation)."""
    lines = body.splitlines()
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return _assemble([("", False, [lines])] if lines else [])


def split_check(body: str, items: Sequence[PlaybookItem], sections: Sequence[PlaybookSection]) -> bool:
    """The loss check (4.4): the multiset of the non-empty ``line_key`` values of the lines of ``body`` equals the one of the lines of the rendering of
    the items, each with its item marker removed first. List numbering, bullet style, indentation and blank lines are invisible to it."""

    def keys(lines: Sequence[str]) -> Counter[str]:
        return Counter(key for line in lines if (key := line_key(line)))

    rendered = [line[m.end():] if (m := ITEM_LINE.match(line)) else line for line in render_items(items, sections).split("\n")]
    return keys(body.splitlines()) == keys(rendered)


SPLITTERS: tuple[Splitter, ...] = (split_blocks, split_sections, split_whole)
_REASONS = ("", FALLBACK_SECTIONS, FALLBACK_WHOLE)


def migrate_body(body: str, *, splitters: Sequence[Splitter] = SPLITTERS) -> Migration:
    """A legacy playbook body as step items without losing a line (pure). The first split that passes the loss check wins: the per-block split, else
    one item per section, else one item for the whole body (which passes by construction). A fallback is named in ``Migration.reason``. No block
    becomes a rule and no item gets a ``why``. The last split failing the check is an ``AssertionError``, never a user path."""
    for splitter, reason in zip(splitters, _REASONS):
        items, sections = splitter(body)
        if split_check(body, items, sections):
            return Migration(items, sections, reason)
    raise AssertionError("the migration of the playbook lost a line")


# ----------------------------------------------------------------------------------------------------------------------- placement (4.1)


class PlacementError(ValueError):
    """An ``after`` that names no place for the item: the message is the clause of the PB-ARGS refusal (5.3)."""


def _rebuilt(items: Sequence[PlaybookItem], sections: Sequence[PlaybookSection]) -> Split:
    """The items in the order of the sections, each carrying the heading of its section."""
    by_id = {i.id: i for i in items}
    return tuple(replace(by_id[i], section=s.heading) for s in sections for i in s.ids), tuple(sections)


def _inserted(sections: Sequence[PlaybookSection], at: int, position: int, item_id: str) -> list[PlaybookSection]:
    """``sections`` with ``item_id`` at ``position`` among the ids of the section ``at``."""
    s = sections[at]
    out = list(sections)
    out[at] = PlaybookSection(s.heading, s.numbered, (*s.ids[:position], item_id, *s.ids[position:]))
    return out


def _rules_section(items: Sequence[PlaybookItem], sections: Sequence[PlaybookSection]) -> int | None:
    """The index of the rules section: the last one, while a rule is live."""
    return len(sections) - 1 if sections and any(i.kind == "rule" for i in items) else None


def _holding(sections: Sequence[PlaybookSection], item_id: str) -> int | None:
    return next((k for k, s in enumerate(sections) if item_id in s.ids), None)


def place_add(items: Sequence[PlaybookItem], sections: Sequence[PlaybookSection], new: PlaybookItem, after: str | None = None) -> Split:
    """The items and sections with ``new`` (its ``section`` is set here) placed by 4.1's rule (pure). A step without ``after`` goes after the last item
    of the first section headed ``## Steps``, else of the first section whose first item is numbered, else into a new ``## Steps`` section placed
    first (after the text before the first heading); with ``after``, a live step, right after it. A rule goes to the end of the rules section (created
    last when no rule is live), or right after ``after``, a live rule. ``PlacementError`` (the PB-ARGS clause) when ``after`` is none of those."""
    by_id = {i.id: i for i in items}
    target = after.strip().upper() if after else None
    if new.kind == "rule":
        at = _rules_section(items, sections)
        if target is not None and (by_id.get(target) is None or by_id[target].kind != "rule"):
            raise PlacementError(f"after={after} is not a live rule")
        if at is None:
            return _rebuilt([*items, new], [*sections, PlaybookSection(RULES_HEADING, False, (new.id,))])
        position = len(sections[at].ids) if target is None else sections[at].ids.index(target) + 1
        return _rebuilt([*items, new], _inserted(sections, at, position, new.id))
    if target is not None:
        if target not in by_id:
            raise PlacementError(f"after={after} is not a live item")
        if by_id[target].kind == "rule":
            raise PlacementError(f"after={after} is a rule: a step goes after a step (or leave after out)")
        at = _holding(sections, target)
        assert at is not None
        return _rebuilt([*items, new], _inserted(sections, at, sections[at].ids.index(target) + 1, new.id))
    named = next((k for k, s in enumerate(sections) if s.heading.rstrip() == STEPS_HEADING), None)
    numbered = next((k for k, s in enumerate(sections) if s.ids and s.numbered and by_id[s.ids[0]].kind == "step"), None)
    at = named if named is not None else numbered
    if at is not None:
        return _rebuilt([*items, new], _inserted(sections, at, len(sections[at].ids), new.id))
    first = 1 if sections and sections[0].heading == "" else 0
    created = PlaybookSection(STEPS_HEADING, True, (new.id,))
    return _rebuilt([*items, new], [*sections[:first], created, *sections[first:]])


def place_restore(
    items: Sequence[PlaybookItem], sections: Sequence[PlaybookSection], restored: PlaybookItem, earlier: Sequence[PlaybookSection],
) -> Split:
    """The items and sections with ``restored`` back where it was (pure). ``earlier`` is the layout of the version in which it was last live: it goes
    back to the section it was in there (found by its heading line and its occurrence among the headings with that line; the section ``""`` is
    recreated first when it is gone), right after the nearest item that preceded it there and is still live in that section, else first. A rule goes
    to the rules section (created last) after the nearest preceding rule that is still live. An item that was in no section of ``earlier``, or
    whose section is gone, is placed like an add."""
    old = _holding(earlier, restored.id)
    if old is None:
        return place_add(items, sections, restored)
    before = list(reversed(earlier[old].ids[: earlier[old].ids.index(restored.id)]))
    if restored.kind == "rule":
        at = _rules_section(items, sections)
        if at is None:
            return _rebuilt([*items, restored], [*sections, PlaybookSection(RULES_HEADING, False, (restored.id,))])
        position = next((sections[at].ids.index(i) + 1 for i in before if i in sections[at].ids), 0)
        return _rebuilt([*items, restored], _inserted(sections, at, position, restored.id))
    heading = earlier[old].heading
    occurrence = sum(1 for s in earlier[:old] if s.heading == heading)
    same = [k for k, s in enumerate(sections) if s.heading == heading]
    if occurrence < len(same):
        at = same[occurrence]
        position = next((sections[at].ids.index(i) + 1 for i in before if i in sections[at].ids), 0)
        return _rebuilt([*items, restored], _inserted(sections, at, position, restored.id))
    if heading == "":
        return _rebuilt([*items, restored], [PlaybookSection("", earlier[old].numbered, (restored.id,)), *sections])
    return place_add(items, sections, restored)
