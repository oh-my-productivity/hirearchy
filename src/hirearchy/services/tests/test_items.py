"""The item grammar (design 4.1): ``render_items`` and ``parse_items`` are exact inverses over every item list the runtime can write."""

from __future__ import annotations

import random

from hirearchy.kernel import JsonObject
from hirearchy.services import PlaybookItem, PlaybookSection
from hirearchy.services._items import ItemsParse, canonical_why, default_numbered, parse_items, render_items


def step(n: int, text: str, section: str = "## Steps", why: tuple[str, ...] = ()) -> PlaybookItem:
    return PlaybookItem(f"P{n}", "step", section, text, "", why)


def rule(n: int, then: str, when: str = "always", why: tuple[str, ...] = ()) -> PlaybookItem:
    return PlaybookItem(f"P{n}", "rule", "## Rules", then, when, why)


def sec(heading: str, ids: tuple[str, ...], numbered: bool | None = None) -> PlaybookSection:
    return PlaybookSection(heading, default_numbered(heading) if numbered is None else numbered, ids)


def meta_of(items: tuple[PlaybookItem, ...]) -> JsonObject:
    return {
        "items_max": max((int(i.id[1:]) for i in items), default=0), "rules": [i.id for i in items if i.kind == "rule"],
        "why": {i.id: list(i.why) for i in items if i.why},
    }


def parsed(body: str, meta: JsonObject | None = None) -> ItemsParse:
    return parse_items(body, {"items_max": 9} if meta is None else meta)


def test_steps_render_numbered_or_bulleted_by_their_sections_first_item() -> None:
    items = (step(1, "Read."), step(2, "Write."), step(3, "Check", "## Budget plan"), step(4, "Pay", "## Budget plan"))
    sections = (sec("## Steps", ("P1", "P2"), True), sec("## Budget plan", ("P3", "P4"), False))
    assert render_items(items, sections) == "## Steps\n1. [P1] Read.\n2. [P2] Write.\n\n## Budget plan\n- [P3] Check\n- [P4] Pay"
    back = parsed(render_items(items, sections))
    assert (back.items, back.sections, back.error) == (items, sections, "")


def test_a_gated_step_ends_with_its_why_and_a_rule_is_one_line_with_sorted_ids() -> None:
    raw = (
        step(12, "Compare every Due cell with the notes.", why=("R2", "R3", "C6")),
        step(13, "Check", why=("R10", "R9")),
        rule(9, "Start with a Summary.", why=("C9", "R1")),
        rule(14, "Convert it.", "a Due cell is relative", why=("R2", "R3", "C6")),
    )
    assert canonical_why(("C6", "R3", "R10", "R2", "C10")) == ("R2", "R3", "R10", "C6", "C10")
    sections = (sec("## Steps", ("P12", "P13"), True), sec("## Rules", ("P9", "P14")))
    items = tuple(PlaybookItem(i.id, i.kind, i.section, i.text, i.when, canonical_why(i.why)) for i in raw)
    body = render_items(items, sections)
    assert body == (
        "## Steps\n1. [P12] Compare every Due cell with the notes. (WHY R2, R3; C6)\n2. [P13] Check (WHY R9, R10)\n\n## Rules\n"
        "- [P9] WHEN always THEN Start with a Summary. WHY R1; C9\n"
        "- [P14] WHEN a Due cell is relative THEN Convert it. WHY R2, R3; C6"
    )
    back = parsed(body, meta_of(items))
    assert (back.items, back.sections, back.error) == (items, sections, "")


def test_a_group_of_why_ids_that_is_empty_is_left_out() -> None:
    only_c = rule(1, "x", why=("C3",))
    only_r = rule(2, "y", why=("R3",))
    assert render_items((only_c, only_r), (sec("## Rules", ("P1", "P2")),)) == "## Rules\n- [P1] WHEN always THEN x WHY C3\n- [P2] WHEN always THEN y WHY R3"


def test_every_heading_renders_and_the_rules_section_only_while_a_rule_is_live() -> None:
    # a heading with nothing under it is part of the text; the section "" renders no heading line; one blank line precedes each heading
    items = (step(1, "Intro"), step(2, "Go"))
    sections = (sec("", ("P1",), False), sec("# Title", ()), sec("## Steps", ("P2",), True), sec("### Empty", ()))
    body = render_items(items, sections)
    assert body == "- [P1] Intro\n\n# Title\n\n## Steps\n1. [P2] Go\n\n### Empty"
    back = parsed(body)
    assert (back.sections, back.items) == (sections, (PlaybookItem("P1", "step", "", "Intro"), PlaybookItem("P2", "step", "## Steps", "Go")))
    assert render_items((), ()) == "" and render_items((), (sec("## Rules", ()),)) == "## Rules"
    # no rule live: the parse of a body without rules needs no rules section
    only_steps = parsed("## Steps\n1. [P1] a", {"items_max": 1, "rules": []})
    assert [s.heading for s in only_steps.sections] == ["## Steps"]


def test_continuations_render_with_three_spaces_and_inner_blank_lines_stay() -> None:
    items = (step(1, "first\n    - nested\n\n```\n## not a heading\n- [P9] not an item\n```\nlast"), step(2, "next"))
    sections = (sec("## Steps", ("P1", "P2"), False),)
    body = render_items(items, sections)
    assert body == (
        "## Steps\n- [P1] first\n       - nested\n\n   ```\n   ## not a heading\n   - [P9] not an item\n   ```\n   last\n- [P2] next"
    )
    back = parsed(body)
    assert (back.items, back.error) == (items, "") and [i.id for i in back.items] == ["P1", "P2"]


def test_a_blank_line_that_is_not_followed_by_a_continuation_is_a_separator() -> None:
    back = parsed("## Steps\n- [P1] a\n\n\n- [P2] b\n   c\n\n## Next\n")
    assert back.error == "" and [(i.id, i.text) for i in back.items] == [("P1", "a"), ("P2", "b\nc")]


def test_an_item_with_an_empty_first_line_keeps_its_continuations() -> None:
    items = (step(1, "\nsecond"),)
    body = render_items(items, (sec("## Steps", ("P1",), False),))
    assert body == "## Steps\n- [P1] \n   second"
    assert parsed(body).items == items
    assert parsed("## Steps\n- [P1]\n   second").items == items  # an editor that dropped the trailing blank


def test_the_kind_comes_from_the_frontmatter_rules_never_from_the_words() -> None:
    body = "## Steps\n1. [P1] WHEN a THEN b\n\n## Rules\n- [P2] WHEN a THEN b"
    as_rule = parsed(body, {"items_max": 2, "rules": ["P2"]})
    assert as_rule.error == "" and [(i.kind, i.when, i.text) for i in as_rule.items] == [("step", "", "WHEN a THEN b"), ("rule", "a", "b")]
    no_rules = parsed(body, {"items_max": 2})  # a legacy-looking `## Rules` section is an ordinary step section
    assert no_rules.error == "" and [i.kind for i in no_rules.items] == ["step", "step"]


def test_a_why_suffix_is_stripped_only_when_it_equals_the_frontmatter_entry() -> None:
    body = "## Steps\n1. [P1] Check (WHY R2; C6)\n2. [P2] Keep (WHY R2; C6)\n\n## Rules\n- [P3] WHEN a THEN b WHY R1"
    meta: JsonObject = {"items_max": 3, "rules": ["P3"], "why": {"P1": ["R2", "C6"], "P3": ["R1"]}}
    got = parsed(body, meta)
    assert got.error == "" and [(i.id, i.text, i.why) for i in got.items] == [
        ("P1", "Check", ("R2", "C6")), ("P2", "Keep (WHY R2; C6)", ()), ("P3", "b", ("R1",)),
    ]
    # an item without an entry keeps whatever its words end with
    assert parsed("## Steps\n1. [P1] Fix it (WHY C6)", {"items_max": 1}).items[0].text == "Fix it (WHY C6)"


def test_a_suffix_that_differs_from_the_entry_is_a_parse_error() -> None:
    meta: JsonObject = {"items_max": 1, "why": {"P1": ["R2"]}}
    for body in ("## Steps\n1. [P1] Check (WHY R3)", "## Steps\n1. [P1] Check", "## Steps\n1. [P1] Check (WHY R2; C6)"):
        got = parsed(body, meta)
        assert got.items == () and got.error.startswith("line 2: ") and "WHY" in got.error
    rule_meta: JsonObject = {"items_max": 1, "rules": ["P1"], "why": {"P1": ["R2"]}}
    got = parsed("## Rules\n- [P1] WHEN a THEN b WHY R9", rule_meta)
    assert got.error.startswith("line 2: ")


def test_a_rule_outside_the_last_rules_section_or_a_step_inside_it_is_a_parse_error() -> None:
    meta: JsonObject = {"items_max": 3, "rules": ["P2"]}
    assert parsed("## Rules\n- [P2] WHEN a THEN b\n\n## Steps\n1. [P1] x", meta).error.startswith("line 2: ")  # the last section is not the rules
    assert parsed("## Steps\n1. [P1] x\n- [P2] WHEN a THEN b", meta).error.startswith("line 3: ")  # a rule in a step section, not last-and-headed
    assert parsed("## Steps\n1. [P1] x\n\n## Rules\n- [P3] a step\n- [P2] WHEN a THEN b", meta).error.startswith("line 5: ")  # a step in it
    assert parsed("## Steps\n1. [P1] x", meta).error != ""  # the rule is missing from the body
    assert parsed("## Steps\n1. [P1] x\n\n## Rules\n- [P2] not a rule line", meta).error.startswith("line 5: ")
    two: JsonObject = {"items_max": 3, "rules": ["P2", "P3"]}
    assert parsed("## Rules\n- [P3] WHEN a THEN b\n- [P2] WHEN a THEN b", two).error != ""  # the order is the frontmatter's


def test_any_other_column_zero_line_is_a_parse_error_naming_its_line() -> None:
    assert parsed("## Steps\nstray words\n1. [P1] x").error.startswith("line 2: ")
    assert parsed("1. [P1] x\n\nstray").error.startswith("line 3: ")
    assert parsed("stray\n1. [P1] x").error.startswith("line 1: ")
    assert parsed("## Steps\n   indented before any item").error.startswith("line 2: ")
    assert parsed("## Steps\n 1. [P1] one space").error.startswith("line 2: ")
    assert parsed("## Steps\n1. [P1] a\n1. [P1] b").error.startswith("line 3: ")  # an id twice
    got = parsed("## Steps\nstray")
    assert got.items == () and got.sections == ()


def test_a_legacy_section_headed_rules_is_an_ordinary_step_section() -> None:
    got = parsed("## Rules\n- [P1] keep it short\n\n## Steps\n1. [P2] go", {"items_max": 2})
    assert got.error == "" and [(s.heading, s.ids) for s in got.sections] == [("## Rules", ("P1",)), ("## Steps", ("P2",))]
    assert [i.kind for i in got.items] == ["step", "step"]


def test_when_then_and_why_inside_an_owners_words_stay_words() -> None:
    items = (step(1, "WHEN done THEN stop WHY not"), rule(2, "stop THEN again WHY not (WHY C1)", "x WHY y"))
    sections = (sec("## Steps", ("P1",), True), sec("## Rules", ("P2",)))
    back = parsed(render_items(items, sections), meta_of(items))
    assert (back.items, back.error) == (items, "")


def seeded_lists(seed: int) -> tuple[tuple[PlaybookItem, ...], tuple[PlaybookSection, ...]]:
    rng = random.Random(seed)
    words = ["Read", "the", "request.", "C6", "R2,", "WHEN", "THEN", "WHY", "(WHY C6)", "[P1]", "- x", "1.", "é", "3.5", "|", "#", "**b**", "`c`"]
    lines = ["- sub", "   1. sub", "## Sub", "    nested", "```", "[P3] x", "", "> quote", "| a | b |"]

    def sentence(low: int = 1, high: int = 6, no_then: bool = False) -> str:
        pool = [w for w in words if not (no_then and w == "THEN")]
        return " ".join(rng.choice(pool) for _ in range(rng.randint(low, high)))

    def why() -> tuple[str, ...]:
        if rng.random() < 0.6:
            return ()
        ids = {f"R{rng.randint(1, 12)}" for _ in range(rng.randint(0, 3))} | {f"C{rng.randint(1, 12)}" for _ in range(rng.randint(0, 3))}
        return canonical_why(tuple(ids))

    headings = ["# Title", "## Steps", "## Budget plan", "## Steps", "### Pitfalls", "## Rules", "## Steps  "]
    numbers = iter(rng.sample(range(1, 200), 60))
    items: list[PlaybookItem] = []
    sections: list[PlaybookSection] = []
    plan = [""] if rng.random() < 0.3 else []
    plan += [rng.choice(headings) for _ in range(rng.randint(0, 4))]
    for heading in plan:
        ids: list[str] = []
        for _ in range(rng.randint(0, 3)):
            n = next(numbers)
            gated = why()
            extra = [] if gated or rng.random() < 0.7 else [rng.choice(lines) for _ in range(rng.randint(1, 3))]  # a gated step is one line
            if extra and not extra[-1]:
                extra.append("tail")
            items.append(PlaybookItem(f"P{n}", "step", heading, "\n".join([sentence(), *extra]), "", gated))
            ids.append(f"P{n}")
        if heading == "" and not ids:
            continue  # normal form: the "" section is in the body only while it holds an item
        sections.append(PlaybookSection(heading, rng.random() < 0.5 if ids else default_numbered(heading), tuple(ids)))
    if rng.random() < 0.5:
        ids = []
        for _ in range(rng.randint(1, 3)):
            n = next(numbers)
            items.append(PlaybookItem(f"P{n}", "rule", "## Rules", sentence(), "always" if rng.random() < 0.4 else sentence(no_then=True), why()))
            ids.append(f"P{n}")
        sections.append(PlaybookSection("## Rules", False, tuple(ids)))
    by_id = {i.id: i for i in items}
    return tuple(by_id[i] for s in sections for i in s.ids), tuple(sections)


def test_the_round_trip_is_exact_over_seeded_random_item_lists() -> None:
    for seed in range(100):
        items, sections = seeded_lists(seed)
        body = render_items(items, sections)
        back = parse_items(body, meta_of(items))
        assert back.error == "", (seed, body, back.error)
        assert (back.items, back.sections) == (items, sections), (seed, body)
        assert render_items(back.items, back.sections) == body


def test_the_random_lists_cover_the_shapes_the_round_trip_claims() -> None:
    seen = [seeded_lists(seed) for seed in range(100)]
    assert any(any(i.kind == "rule" for i in items) for items, _ in seen)
    assert any(any("\n" in i.text for i in items) for items, _ in seen)
    assert any(any(i.why for i in items) for items, _ in seen)
    assert any(any(not s.ids for s in sections) for _, sections in seen) and any(not items for items, _ in seen)
    assert any(sections and sections[0].heading == "" for _, sections in seen)
    headings = [[s.heading for s in sections] for _, sections in seen]
    assert any(len(h) != len(set(h)) for h in headings)  # two sections with the same heading line


def test_the_two_normal_forms() -> None:
    # the "" section is in the body only while it holds an item: with none, the parse of the rendering has no such section
    assert parsed(render_items((), (sec("", (), False), sec("## Steps", ())))).sections == (sec("## Steps", ()),)
    # a section's numbering is read from its first item; an emptied section reads as numbered only when its heading is `## Steps`
    assert default_numbered("## Steps") and not default_numbered("## Other") and not default_numbered("## Rules") and not default_numbered("")
    body = "## Steps\n\n## Other\n"
    assert [(s.heading, s.numbered) for s in parsed(body).sections] == [("## Steps", True), ("## Other", False)]
    two = parsed("## Other\n- [P1] a\n2. [P2] b")
    assert [s.numbered for s in two.sections] == [False]
    assert parsed("## Other\n7. [P1] a\n- [P2] b").sections[0].numbered is True
