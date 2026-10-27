"""``migrate_body`` (design 4.4): a free-text playbook becomes step items without losing a line; the loss check and the two fallbacks."""

from __future__ import annotations

import pytest

from hirearchy.services import PlaybookItem, PlaybookSection
from hirearchy.services._items import (
    FALLBACK_SECTIONS, FALLBACK_WHOLE, Migration, migrate_body, parse_items, render_items, split_blocks, split_check, split_sections, split_whole,
)

Shape = list[tuple[str, bool, list[str]]]


def shape(m: Migration) -> Shape:
    """The sections of a migration as (heading, numbered, the texts of its items)."""
    by_id = {i.id: i for i in m.items}
    return [(s.heading, s.numbered, [by_id[i].text for i in s.ids]) for s in m.sections]


def round_trips(m: Migration) -> None:
    back = parse_items(render_items(m.items, m.sections), {"items_max": len(m.items)})
    assert (back.error, back.items, back.sections) == ("", m.items, m.sections)


def test_blocks_are_headings_list_items_fences_tables_and_paragraphs() -> None:
    body = "\n".join([
        "# Title", "## Steps", "1. one", "continued lazily", "2) two", "", "   indented after a blank line", "- three", "",
        "```", "fenced", "", "still fenced", "```", "| a | b |", "|---|---|", "| 1 | 2 |", "a paragraph", "of two lines", "",
        "* star", "+ plus", "- [ ] box",
    ])
    m = migrate_body(body)
    assert m.reason == "" and [i.id for i in m.items] == [f"P{k}" for k in range(1, 10)]
    assert shape(m) == [
        ("# Title", False, []),
        ("## Steps", True, [
            "one\ncontinued lazily", "two\n\n   indented after a blank line", "three", "```\nfenced\n\nstill fenced\n```", "| a | b |\n|---|---|\n| 1 | 2 |",
            "a paragraph\nof two lines", "star", "plus", "[ ] box",
        ]),
    ]
    round_trips(m)


def test_an_unterminated_fence_runs_to_the_end_and_a_list_item_ends_at_unindented_text_after_a_blank_line() -> None:
    assert shape(migrate_body("## S\n- a\n\nplain\n```\nopen\n\n")) == [("## S", False, ["a", "plain", "```\nopen"])]


def test_a_section_is_numbered_when_its_first_item_was() -> None:
    assert [s.numbered for s in migrate_body("## A\n1. a\n- b\n## B\n- a\n2. b\n## C\nintro\n1. a").sections] == [True, False, False]


def test_nothing_numbered_is_remembered_for_a_section_without_items() -> None:
    assert [(s.heading, s.numbered) for s in migrate_body("## Steps\n## Other\n").sections] == [("## Steps", True), ("## Other", False)]


CASES = {
    "table": ("## T\n| a | b |\n|---|---|\n| 1 | 2 |\n\nafter", [("## T", False, ["| a | b |\n|---|---|\n| 1 | 2 |", "after"])]),
    "fence": (
        "## S\n```\n## not a heading\n- [P1] x\n\n```\nafter",
        [("## S", False, ["```\n## not a heading\n- [P1] x\n\n```", "after"])],
    ),
    "nested lists": ("- a\n  - b\n    - c\n- d", [("", False, ["a\n  - b\n    - c", "d"])]),
    "two headings with the same text": ("## A\n- x\n## A\n- y", [("## A", False, ["x"]), ("## A", False, ["y"])]),
    "text before the first heading": ("intro text\n\n## S\n- x", [("", False, ["intro text"]), ("## S", False, ["x"])]),
    "an H1 directly before a ##": ("# Title\n## Steps\n1. a", [("# Title", False, []), ("## Steps", True, ["a"])]),
    "two consecutive headings": ("## A\n## B\n- x", [("## A", False, []), ("## B", False, ["x"])]),
    "a body ending with a heading": ("## A\n- x\n## End", [("## A", False, ["x"]), ("## End", False, [])]),
    "headings only": ("# A\n## B", [("# A", False, []), ("## B", False, [])]),
    "a paragraph ending in (WHY C6)": ("## S\nDo it (WHY C6)", [("## S", False, ["Do it (WHY C6)"])]),
    "list items separated by blank lines": ("- a\n\n- b\n\n- c", [("", False, ["a", "b", "c"])]),
    "CRLF": ("## S\r\n1. a\r\n2. b\r\n", [("## S", True, ["a", "b"])]),
    "trailing spaces": ("- a  \n   b  \n- c ", [("", False, ["a  \n   b  ", "c "])]),
    "a literal [P1]": ("see [P1] here\n\n- [P1] x", [("", False, ["see [P1] here", "[P1] x"])]),
    "the empty body": ("", []),
    "blank lines only": ("\n  \n\t\n", []),
    "a lone marker": ("-\n- a", [("", False, ["", "a"])]),
}


@pytest.mark.parametrize("case", CASES)
def test_each_constructed_body_migrates_in_the_form_its_case_names(case: str) -> None:
    body, expected = CASES[case]
    m = migrate_body(body)
    assert shape(m) == expected and m.reason == ""  # the per-block split, no fallback
    assert all(i.kind == "step" and i.why == () and i.when == "" for i in m.items)
    assert [i.id for i in m.items] == [f"P{k}" for k in range(1, len(m.items) + 1)]
    assert split_check(body, m.items, m.sections)
    round_trips(m)


def test_the_text_before_the_first_heading_is_a_section_only_while_it_holds_an_item() -> None:
    assert [s.heading for s in migrate_body("\n\n## A\n- x").sections] == ["## A"]


def test_the_loss_check_compares_the_non_empty_line_keys() -> None:
    body = "## Steps\n1. Read the request.\n2. Write it.\n\n---\n```\n```\n-"
    m = migrate_body(body)
    assert split_check(body, m.items, m.sections)  # list numbering, bullets, blank lines, '---', fences and lone markers are invisible
    assert split_check("- x", (PlaybookItem("P1", "step", "", "X"),), (PlaybookSection("", False, ("P1",)),))  # case is no difference
    one = PlaybookItem("P1", "step", "", "x")
    only = (PlaybookSection("", False, ("P1",)),)
    assert not split_check("x\nx", (one,), only)  # a line repeated is a line lost
    assert not split_check("x\ny", (one,), only) and not split_check("x", (PlaybookItem("P1", "step", "", "y"),), only)
    assert not split_check("x", (one, PlaybookItem("P2", "step", "", "x")), (PlaybookSection("", False, ("P1", "P2")),))
    assert split_check("x\n---\n", (one,), only)


def lossy(body: str) -> tuple[tuple[PlaybookItem, ...], tuple[PlaybookSection, ...]]:
    """A splitter that drops the last line: it fails the check on every body of two or more lines."""
    return split_blocks("\n".join(body.splitlines()[:-1]))


BODY = "# Title\n## Steps\n1. First step\n   detail line\n\n2. Second step\n\n## Pitfalls\n- Watch out\n\nclosing words"


def test_the_per_section_fallback_names_itself_in_the_reason() -> None:
    m = migrate_body(BODY, splitters=(lossy, split_sections, split_whole))
    assert m.reason == FALLBACK_SECTIONS == "; one item per section: the per-block split did not keep every line"
    assert shape(m) == [
        ("# Title", False, []),
        ("## Steps", False, ["1. First step\n   detail line\n\n2. Second step"]),
        ("## Pitfalls", False, ["- Watch out\n\nclosing words"]),
    ]
    assert split_check(BODY, m.items, m.sections)
    round_trips(m)


def test_the_single_item_fallback_passes_by_construction() -> None:
    m = migrate_body(BODY, splitters=(lossy, lossy, split_whole))
    assert m.reason == FALLBACK_WHOLE == "; one item: neither split kept every line"
    assert shape(m) == [("", False, [BODY])] and [i.id for i in m.items] == ["P1"]
    assert split_check(BODY, m.items, m.sections)
    round_trips(m)
    tricky = "## A\n```\n## B\n- [P1] x\n```\n\n   indented"
    whole = migrate_body(tricky, splitters=(lossy, lossy, split_whole))
    assert shape(whole) == [("", False, [tricky])] and split_check(tricky, whole.items, whole.sections)
    round_trips(whole)
    assert migrate_body("", splitters=(lossy, lossy, split_whole)).items == ()


def test_a_split_that_cannot_pass_is_an_assertion_never_a_user_path() -> None:
    with pytest.raises(AssertionError):
        migrate_body(BODY, splitters=(lossy, lossy, lossy))


def test_the_real_splitter_never_needs_a_fallback_on_the_awkward_bodies() -> None:
    for body, _ in CASES.values():
        assert migrate_body(body).reason == ""


def test_no_block_becomes_a_rule_and_no_item_has_a_why() -> None:
    body = "## Rules\n- WHEN a THEN b WHY R1; C2\n- Fix it (WHY C6)\n\nWHEN x THEN y"
    m = migrate_body(body)
    assert [(i.kind, i.when, i.why) for i in m.items] == [("step", "", ())] * 3
    assert [i.text for i in m.items] == ["WHEN a THEN b WHY R1; C2", "Fix it (WHY C6)", "WHEN x THEN y"]
    back = parse_items(render_items(m.items, m.sections), {"items_max": 3})
    assert back.error == "" and back.items == m.items
