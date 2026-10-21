"""``indent``: every line of a text moved right by a number of spaces."""

from __future__ import annotations

import pytest

from hirearchy.prompts._text import indent



def test_every_line_is_indented() -> None:
    assert indent("a\nb", 2) == "  a\n  b"


def test_a_blank_line_is_indented_too() -> None:
    assert indent("a\n\nb", 4) == "    a\n    \n    b"


def test_an_empty_text_stays_empty_and_a_trailing_newline_is_dropped() -> None:
    assert indent("", 3) == "" and indent("a\n", 1) == " a"


def test_no_indent_leaves_the_lines_alone() -> None:
    assert indent("a\nb", 0) == "a\nb"
