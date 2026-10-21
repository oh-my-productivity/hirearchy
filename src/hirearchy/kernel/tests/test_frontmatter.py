"""Frontmatter: ``split_frontmatter`` and ``join_frontmatter``."""

from __future__ import annotations

import pytest
import yaml

from hirearchy.kernel import flow_text, join_frontmatter, split_frontmatter


def test_round_trip() -> None:
    meta: dict[str, object] = {"id": "x", "n": 3, "flag": False, "items": ["a", "b"], "nested": {"k": "v"}, "text": "é: ü"}
    text = join_frontmatter(meta, "body line\n\nsecond paragraph")
    assert split_frontmatter(text) == (meta, "body line\n\nsecond paragraph\n")


def test_join_layout_and_key_order() -> None:
    assert join_frontmatter({"b": 1, "a": 2}, "hello") == "---\nb: 1\na: 2\n---\nhello\n"  # sort_keys is off


def test_join_ends_with_exactly_one_newline() -> None:
    assert join_frontmatter({"a": 1}, "x\n\n\n") == "---\na: 1\n---\nx\n"
    assert join_frontmatter({"a": 1}, "") == "---\na: 1\n---\n\n"


def test_join_keeps_non_ascii_readable() -> None:
    assert "héllo ✓" in join_frontmatter({"title": "héllo ✓"}, "b")


def test_text_without_a_frontmatter_block_is_all_body() -> None:
    assert split_frontmatter("just text\n") == ({}, "just text\n")
    assert split_frontmatter("") == ({}, "")


def test_an_unterminated_block_is_not_a_block() -> None:
    text = "---\na: 1\nbody"
    assert split_frontmatter(text) == ({}, text)


def test_an_empty_block_has_no_meta() -> None:
    assert split_frontmatter("---\n\n---\nbody") == ({}, "body")


def test_a_block_that_is_not_a_mapping_has_no_meta_but_is_still_removed() -> None:
    assert split_frontmatter("---\n- a\n- b\n---\nbody\n") == ({}, "body\n")
    assert split_frontmatter("---\njust a scalar\n---\nbody\n") == ({}, "body\n")


def test_crlf_text_is_not_split_callers_normalise_newlines_first() -> None:
    crlf = "---\r\na: 1\r\n---\r\nbody\r\n"
    assert split_frontmatter(crlf) == ({}, crlf)
    assert split_frontmatter(crlf.replace("\r\n", "\n")) == ({"a": 1}, "body\n")


def test_only_the_first_block_is_frontmatter() -> None:
    text = "---\na: 1\n---\nbody\n---\nb: 2\n---\nmore\n"
    assert split_frontmatter(text) == ({"a": 1}, "body\n---\nb: 2\n---\nmore\n")


def test_yaml_uses_the_c_loader_when_present() -> None:  # moved from tests/test_scheduler_robustness.py (core._YAML_LOADER)
    from hirearchy.kernel import _frontmatter

    assert _frontmatter._YAML_LOADER is getattr(yaml, "CSafeLoader", yaml.SafeLoader)
    assert split_frontmatter("---\na: 1\nb: [x, y]\n---\nbody\n") == ({"a": 1, "b": ["x", "y"]}, "body\n")


@pytest.mark.parametrize(
    ("value", "text"),
    [
        ("plain", "plain"), (5, "5"), (2.5, "2.5"), (None, "null"), (True, "true"), (["read", "write"], "[read, write]"), ([], "[]"),
        ({}, "{}"), ({"a": 1, "b": [1, 2]}, "{a: 1, b: [1, 2]}"), ("two\nlines", "'two lines'"), ("é世", "é世"), ("a   b", "a b"),
    ],
)
def test_flow_text_is_a_value_in_yaml_flow_style_on_one_line_blanks_collapsed(value: object, text: str) -> None:
    assert flow_text(value) == text


def test_flow_text_is_not_wrapped_however_long_and_has_no_document_end_marker() -> None:
    long = flow_text(["word"] * 100)
    assert "\n" not in long and long == "[" + ", ".join(["word"] * 100) + "]"
    assert flow_text("x") == "x" and flow_text("") == "''"


def test_flow_text_of_a_long_scalar_with_blanks_collapses_them() -> None:
    assert flow_text("a \t b\n\nc") == '"a \\t b\\n\\nc"'
