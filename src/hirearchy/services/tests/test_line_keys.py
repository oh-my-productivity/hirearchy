"""``line_key`` and ``changed_lines``: playbook lines compared on their words (P1, 4.1): punctuation, spacing, case, list numbering,
bullets and checkboxes never make two lines differ; a changed word or number does."""

from __future__ import annotations

from hirearchy.services import Criterion, changed_lines, line_key, quoting_lines


def test_line_key_ignores_punctuation_spacing_case_and_markers() -> None:
    assert line_key("- Cut to 600 words, before reporting!") == line_key("  * cut  to 600 WORDS before reporting")
    assert line_key("> ## Cut to 600 words") == "cutto600words"
    assert line_key("Hello, wörld") == "hellowörld"
    assert line_key("---") == "" and line_key("```") == "" and line_key("-") == "" and line_key("#") == "" and line_key("   ") == ""


def test_renumbered_steps_are_no_change() -> None:
    current = "1. Search.\n2. Write.\n3. Check every claim."
    new = "1. Search.\n2. Write.\n3. Add a summary.\n4. Check every claim."
    assert changed_lines(current, new) == ["3. Add a summary."]
    assert changed_lines(current, "2) Search.\n3) Write.\n4) Check every claim.") == []


def test_a_checkbox_toggle_is_no_change() -> None:
    assert changed_lines("- [ ] Check the dates", "- [x] Check the dates") == []
    assert line_key("- [ ] x") == line_key("- [x] x") == "x"


def test_a_changed_word_or_number_is_a_change() -> None:
    assert changed_lines("Cut to 600 words.", "Cut to 500 words.") == ["Cut to 500 words."]
    assert changed_lines("Use the table.", "Use the tables.") == ["Use the tables."]
    assert changed_lines("Use the table.", "Never use the table.") == ["Never use the table."]


def test_a_repeated_line_counts_once_more() -> None:
    assert changed_lines("Keep it short.", "Keep it short.\nKeep it short.") == ["Keep it short."]
    assert changed_lines("Keep it short.\nKeep it short.", "Keep it short.\nKeep it short.") == []
    assert changed_lines("Keep it short.\nKeep it short.", "Keep it short.") == []


def test_lines_with_an_empty_key_are_never_changes() -> None:
    assert changed_lines("a", "a\n\n---\n```\n-\n#\n   ") == []
    assert changed_lines("", "") == [] and changed_lines("", "\n\n") == []


def test_changed_lines_are_stripped_in_order_and_everything_is_new_without_a_current() -> None:
    assert changed_lines("", "  first line  \n\n- second line\n") == ["first line", "- second line"]


def test_changed_lines_reversed_gives_the_removed_lines() -> None:
    old = "Keep one.\nKeep two.\nKeep three."
    new = "Keep one.\nKeep three.\nKeep four."
    assert changed_lines(old, new) == ["Keep four."]
    assert changed_lines(new, old) == ["Keep two."]


# ------------------------------------------------------------------------------ quoting_lines (4.5)


def criterion(text: str, id: str = "C9") -> Criterion:
    return Criterion(id, text, 2, "root", False)


def test_quoting_lines_by_id_or_by_verbatim_text() -> None:
    body = "\n".join([
        "## Steps", "- **C9 – Relative deadlines**: resolve them", "Every Due value is an ISO date, always.", "  - every due VALUE is an iso date  ",
        "Mention C90 in passing", "xC9 is not an id", "A different rule", "", "---",
    ])
    assert quoting_lines(body, criterion("Every Due value is an ISO date")) == [
        "- **C9 – Relative deadlines**: resolve them", "Every Due value is an ISO date, always.", "- every due VALUE is an iso date",
    ]
    assert quoting_lines("Cites c9 lower-case", criterion("Another rule")) == ["Cites c9 lower-case"]
    assert quoting_lines("", criterion("x")) == [] and quoting_lines("nothing here", criterion("Another rule")) == []


def test_an_empty_key_criterion_is_quoted_by_id_only() -> None:
    """A criterion with no letter or digit has an empty key, which every line would "contain": it is matched by its id alone."""
    assert quoting_lines("- ???\n- C9: the rule\nplain", criterion("???")) == ["- C9: the rule"]



def test_criterion_words_names_the_criterion_whose_own_words_a_line_is() -> None:
    from hirearchy.services import criterion_words

    c9 = criterion("Every Due value is an ISO date.", "C9")
    c10 = criterion("Next meeting is stated.", "C10")
    for line in ("- C9: Every Due value is an ISO date.", "2. C9: every due value is an iso date", "Every Due value is an ISO date. (C9)"):
        assert criterion_words(line, [c9, c10]) == "C9"
    assert criterion_words("- C10: Next meeting is stated.", [c9, c10]) == "C10"
    assert criterion_words("- C9: Every Due value is an ISO date, always.", [c9]) is None
    assert criterion_words("Every Due value is an ISO date.", [c9]) is None  # its words without its id are not its words


def test_a_criterion_with_an_empty_key_admits_no_line() -> None:
    from hirearchy.services import criterion_words

    assert criterion_words("- C9: ---", [criterion("---", "C9")]) is None
    assert criterion_words("C9", [criterion("", "C9")]) is None
