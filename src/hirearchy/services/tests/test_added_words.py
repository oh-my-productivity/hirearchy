"""``added_words`` (design 3, 10.1; PC-3): the words of a criterion that neither the user's quote nor the question they answered holds."""

from __future__ import annotations

from hirearchy.services import added_words


def test_added_words_are_the_criterion_tokens_not_in_the_quote_or_the_question_in_order_without_repeats() -> None:
    assert added_words("Every row has a date and a date", "every row", "Which date?") == ("has", "a", "and")
    assert added_words("b a b c a", "", "") == ("b", "a", "c")  # in order of first sight, each once
    assert added_words("Owners: initials", "Owners are written as initials.", "") == ()  # case and punctuation never make a word new


def test_p1s_widened_criterion_adds_decisions_and_actions_own() -> None:
    assert added_words(
        "decisions and actions use the notes' own words", "Use the words from the notes.", "Owners: initials or full names?",
    ) == ("decisions", "and", "actions", "own")


def test_no_added_word_reads_none() -> None:
    assert added_words("use the notes", "Use the notes.", "") == ()
    assert added_words("", "anything", "anything") == ()
    assert added_words("full names", "", "Owners: initials or full names?") == ()  # the question's words are not added
