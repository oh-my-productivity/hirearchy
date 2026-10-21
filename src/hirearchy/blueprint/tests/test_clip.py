"""The sentence clip of the plan's one-line fields."""

from __future__ import annotations

from hirearchy.blueprint._text import CLIP, GOAL_CLIP, clip




def test_a_short_text_is_one_line_unchanged() -> None:
    assert clip("Short.") == "Short."
    assert clip("two\n  lines   and   gaps") == "two lines and gaps"
    assert clip(None) == ""


def test_whole_sentences_are_kept_while_they_fit_and_the_cut_is_said() -> None:
    text = "First sentence. Second sentence here. " + "Third one is far too long. " * 10
    out = clip(text, 60)
    assert out == "First sentence. Second sentence here. (the rest is in the details)"


def test_the_first_sentence_is_always_kept_whole() -> None:
    long_first = "word " * 100 + "end. Second."
    out = clip(long_first, 50)
    assert out.startswith("word word") and "end." in out and out.endswith("(the rest is in the details)")


