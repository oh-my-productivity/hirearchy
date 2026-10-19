"""The words of a message as one line: ``section``, ``summary`` and ``short`` (moved from ``progress``, whose own copies the progress step will replace)."""

from __future__ import annotations

import pytest

from orgmcp.attention._text import SHORT, section, short, summary



def test_a_section_is_the_non_empty_lines_under_its_heading() -> None:
    body = "intro\n## Summary\n\n  one \ntwo\n## Artifacts\n- a\n"
    assert section(body, "summary") == ["one", "two"]
    assert section(body, "artifacts") == ["- a"]


def test_a_heading_is_matched_whatever_its_case_and_spacing() -> None:
    assert section("##   SuMMary  \nx", "summary") == ["x"]


def test_a_body_without_the_heading_has_an_empty_section() -> None:
    assert section("just text\n### Summary\nx", "summary") == []
    assert section("", "summary") == []


def test_the_summary_of_a_result_is_the_first_line_of_its_section() -> None:
    assert summary("## Summary\n\nthe reason\nmore\n") == "the reason"


def test_without_a_summary_section_it_is_the_first_line_of_the_body() -> None:
    assert summary("first\nsecond") == "first"
    assert summary("\nsecond") == ""  # the first line of the body is the empty one
    assert summary("") == ""


@pytest.mark.parametrize(
    ("text", "limit", "expected"),
    [
        ("plain", SHORT, "plain"),
        ("  many   spaces\n and\tlines ", SHORT, "many spaces and lines"),
        ("ends with a period.", SHORT, "ends with a period"),
        ("many periods...", SHORT, "many periods"),
        ("abcdefghij", 10, "abcdefghij"),
        ("abcdefghijk", 10, "abcdefghi…"),
        ("abcdefgh jk", 10, "abcdefgh…"),  # the cut drops the blank it leaves
        ("", SHORT, ""),
    ],
)
def test_a_line_is_one_line_cut_to_its_limit(text: str, limit: int, expected: str) -> None:
    assert short(text, limit) == expected


def test_the_default_limit_is_a_line_of_110_characters() -> None:
    assert SHORT == 110 and len(short("x" * 300)) == 110
