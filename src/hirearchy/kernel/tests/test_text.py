"""Text helpers: ``word_count``, ``strip_markers``, ``artifact_paths``, ``clip``, ``clip_line``, ``single``; oracle tests against the frozen copies (``_oracle``) and ``hirearchy.core``."""

from __future__ import annotations

import pytest

from hirearchy.kernel import TITLE_MAX, artifact_paths, clip, clip_line, single, strip_markers, word_count
from hirearchy.kernel.tests import _oracle
from hirearchy.kernel.tests._reach import reach


def test_word_count_ignores_markdown_markers() -> None:  # moved from tests/test_core_safety.py (assertions unchanged)
    text = "\n".join([
        "# Title here", "", "## Sub", "- one two", "* three", "+ four", "  - nested five", "1. six", "12) seven",
        "> quoted eight", "- [x] done nine", "| a | b |", "|---|:--:|", "| c | d |", "---", "***", "```python", "ten", "```",
        "**bold** and `code` -5 degrees", "No marker 3. here",
    ])
    # Title here(2) Sub(1) one two(2) three four(2) nested five(2) six seven(2) quoted eight(2) done nine(2)
    # a b c d(4) ten(1) bold and code -5 degrees(5) No marker 3. here(4)
    assert word_count(text) == 2 + 1 + 2 + 2 + 2 + 2 + 2 + 2 + 4 + 1 + 5 + 4
    assert word_count("") == 0 and word_count("plain words stay") == 3 and word_count("- \n#\n") == 0


def test_word_count_counts_unicode_words_and_blank_lines_as_nothing() -> None:
    assert word_count("héllo wörld\n\n\n  \n✓ done") == 4
    assert word_count("one\ttwo  three\r\nfour") == 4


WORDS = [
    "", "x", "two words", "# h", "- a\n- b", "1. one\n2. two", "> quote here", "| a | b |\n|---|---|\n| c | d |", "```\ncode here\n```",
    "- [ ] todo\n- [x] done", "**bold** text", "--- ", "a - b", "-5 degrees", "12) twelve", "1234) not a marker", "• bullet", "+++ ===",
]


@pytest.mark.parametrize("text", WORDS)
def test_word_count_equals_the_core_count(text: str) -> None:
    assert word_count(text) == reach("core").word_count(text)


def test_strip_markers_removes_leading_markdown_markers() -> None:
    assert strip_markers("- [ ] x") == "x"
    assert strip_markers("> # 1. x") == "x"
    assert strip_markers("\u2022 x") == "x"
    assert strip_markers("12) x") == "x"
    assert strip_markers("  * - [x] nested x") == "nested x"


def test_strip_markers_keeps_what_is_not_a_marker() -> None:
    assert strip_markers("plain words") == "plain words"
    assert strip_markers("1234) not a marker") == "1234) not a marker"
    assert strip_markers("-5 degrees") == "-5 degrees"
    assert strip_markers("") == "" and strip_markers("- ") == ""


NESTED = ["> - [x] done nine", "  * 1. nested", "# - [ ] todo", "> > quote", "- 12) twelve\n- [ ] a\n> # b"]


@pytest.mark.parametrize("text", [*NESTED, *WORDS])
def test_word_count_is_unchanged_by_the_extraction(text: str) -> None:
    assert word_count(text) == reach("core").word_count(text)
    flat = [strip_markers(ln.replace("|", " ") if ln.lstrip().startswith("|") else ln) for ln in text.splitlines()]
    assert all(not ln.lstrip().startswith(("> ", "- ", "# ")) for ln in flat)


def test_clip_leaves_short_text_alone_and_marks_a_cut() -> None:
    assert TITLE_MAX == 80
    assert clip("abc", 3) == "abc"
    assert clip("abcd", 3) == "ab…"
    assert clip("x" * 100) == "x" * 79 + "…"
    assert clip("x" * 80) == "x" * 80
    assert clip(12345, 4) == "123…"
    assert clip(None) == "None"
    assert clip("abc", 0) == "…" and clip("abc", 1) == "…"


def test_clip_line_collapses_blanks_and_trims_before_the_mark() -> None:
    assert clip_line("  a \n b\t c ", 20) == "a b c"
    assert clip_line("alpha beta gamma", 8) == "alpha b…"
    assert clip_line("alpha beta gamma", 7) == "alpha…"  # the blank before the mark is dropped
    assert clip_line("alpha beta", 10) == "alpha beta"
    assert clip_line(["x", 1], 40) == "['x', 1]"


def test_single_is_the_one_distinct_non_null_item() -> None:
    assert single([]) is None
    assert single([None, None]) is None
    assert single(["t1"]) == "t1"
    assert single(["t1", "t1", None]) == "t1"
    assert single(["t1", "t2"]) is None
    assert single(t for t in ("a", "a")) == "a"


def _clip_inputs() -> list[tuple[object, int]]:
    values: list[object] = ["", "a", "abc def", "  spaced   out  ", "line\nbreak", "é" * 30, "x" * 200, 12345, None, 3.5, ["a", "b"], "a " * 50]
    return [(v, n) for v in values for n in (0, 1, 2, 5, 10, 40, 80, 500)]


@pytest.mark.parametrize(("value", "limit"), _clip_inputs())
def test_clip_line_equals_the_frozen_clip(value: object, limit: int) -> None:
    assert clip_line(value, limit) == _oracle._clip(value, limit)


def test_artifact_paths_reads_the_artifacts_section() -> None:
    body = "## Summary\nx\n## ARTIFACTS\n- ceo/a.md (12 words)\n\n* ceo/b.md\n  ceo/c.md  \n## Lessons\n- not me"
    assert artifact_paths(body) == ["ceo/a.md", "ceo/b.md", "ceo/c.md"]
    assert artifact_paths("## artifacts\n-   ceo/dir with space/d.md (1 words) (2)") == ["ceo/dir with space/d.md"]
    assert artifact_paths("## Artifacts\n- a.md\n## Artifacts\n- b.md") == ["a.md", "b.md"]  # one section, however often it is headed


def test_no_artifacts_section_gives_no_paths() -> None:
    assert artifact_paths("") == []
    assert artifact_paths("no sections") == []
    assert artifact_paths("## Summary\n- ceo/a.md\n### Artifacts\n- ceo/b.md") == []  # a deeper heading is not the section
    assert artifact_paths("## Artifacts\n\n   \n## Lessons\n- x") == []
