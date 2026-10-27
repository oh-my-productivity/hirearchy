"""``text_tokens`` and ``content_words`` (design 3, 6.1, B9): what a wording fix may change (spacing, case, markdown, sentence punctuation) and what
an item's content words count."""

from __future__ import annotations

import pytest

from hirearchy.services import PlaybookItem, content_words, text_tokens

GATED = [
    ("within 3.5 days", "within 35 days"), ("steps 1, 2", "steps 12"), ("3,5", "3.5"), ("é", "e"), ("value > 100", "value < 100"),
    ("x = 5", "x ≠ 5"), ("at most 5%", "at most 5"), ("$5", "€5"), ("UTC+2", "UTC-2"), ("-3 days", "3 days"), ("✓", "✗"),
    (">5 rows", "5 rows"), ("> 5 action items", "5 action items"), ("+ 2 days to each due date", "2 days to each due date"),
    ("[x] reviewed", "[ ] reviewed"), ("- step", "1. step"),
    ("within ~5 days", "within 5 days"), ("see #3", "see 3"),  # B9
]

FORMATTING = [
    ("**Due:**  ISO", "Due: iso"), ("Check the date.", "check the date"),
    ("first line\n   - sub", "first line\n   1. sub"),  # a continuation line's own list marker (L13)
    ("~~old~~ new", "old new"), ("first line\n   ## Sub", "first line\n   Sub"),  # B9
]


@pytest.mark.parametrize("old, new", GATED)
def test_a_changed_word_number_or_symbol_changes_the_tokens(old: str, new: str) -> None:
    assert text_tokens(old) != text_tokens(new)


@pytest.mark.parametrize("old, new", FORMATTING)
def test_formatting_keeps_the_tokens(old: str, new: str) -> None:
    assert text_tokens(old) == text_tokens(new)


def test_the_tokens_are_numbers_with_their_separators_letters_and_every_other_symbol() -> None:
    assert text_tokens("Within 3.5 days, 2024-05-01 (UTC+2) é%") == ["within", "3.5", "days", "2024-05-01", "utc", "+", "2", "é", "%"]
    assert text_tokens("3,5 and 35 and 1, 2") == ["3,5", "and", "35", "and", "1", "2"]
    assert text_tokens("") == [] and text_tokens("  .,;:!?'\"()[]*_`  ") == []


def test_markers_are_stripped_on_continuation_lines_only() -> None:
    assert text_tokens("- a\n- b\n1. c\n## d\n[ ] e\n> f") == ["-", "a", "b", "c", "d", "e", "f"]
    assert text_tokens("1. a") == ["1", "a"] and text_tokens("> a") == [">", "a"] and text_tokens("## a") == ["a"]


def item(text: str, when: str = "", id: str = "P1", kind: str = "step", section: str = "## Steps", why: tuple[str, ...] = ()) -> PlaybookItem:
    return PlaybookItem(id, kind, section, text, when, why)


def test_content_words_count_texts_whens_and_headings_never_markers_why_or_ids() -> None:
    items = (
        item("Read the request  first."),
        item("Convert the date", "a Due cell is relative", id="P2", kind="rule", section="## Rules", why=("R2", "R3", "C6")),
    )
    # 4 + (3 + 5) + the headings "## Steps" and "## Rules" (2 + 2); the ids, the WHY ids and the WHEN/THEN keywords are no words
    assert content_words(items, ("## Steps", "## Rules")) == 4 + 8 + 4
    assert content_words((), ()) == 0 and content_words((), ("# Title",)) == 2


def test_content_words_count_every_line_of_a_multi_line_item() -> None:
    assert content_words((item("one two\n   - three four\n\nfive"),), ()) == 2 + 3 + 1


def test_a_when_of_always_counts_no_word() -> None:
    assert content_words((item("Start with a summary", "always", kind="rule"),), ()) == 4


def test_a_legacy_body_counts_its_split_words() -> None:
    body = "## Steps\n1. Read the request.\n- [ ] Check\n\n---"
    assert content_words(None, (), body=body) == len(body.split()) == 11
