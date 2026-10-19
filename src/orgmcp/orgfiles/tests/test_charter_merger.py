"""``CharterMerger``: the frontmatter a rewritten charter gets, and the note that tells the writer what happened to it."""

from __future__ import annotations

import pytest

from orgmcp.orgfiles._charter_merge import CharterMerger, _short, charter_change_note


NOTE_END = "A key you leave out is kept; to remove one, set it explicitly (e.g. `tools: []`)."


def test_keys_the_new_text_leaves_out_are_kept_after_the_new_ones() -> None:
    merged, _ = CharterMerger().merge("a", {"role": "Old", "tools": ["read"], "model": "m"}, {"role": "New"})
    assert merged == {"role": "New", "tools": ["read"], "model": "m"} and list(merged) == ["role", "tools", "model"]


def test_the_order_is_the_new_keys_then_the_kept_ones_in_their_old_order() -> None:
    merged, _ = CharterMerger().merge("a", {"a": 1, "b": 2, "c": 3, "d": 4}, {"d": 40, "role": "R", "b": 20})
    assert list(merged) == ["d", "role", "b", "a", "c"] and merged["d"] == 40 and merged["b"] == 20


def test_a_key_set_to_an_empty_value_wins() -> None:
    merged, _ = CharterMerger().merge("a", {"tools": ["read"], "model": "m", "inputs": ["/x"]}, {"role": "R", "tools": [], "model": None, "inputs": ""})
    assert merged == {"role": "R", "tools": [], "model": None, "inputs": ""}


def test_nothing_to_keep_gives_the_new_keys() -> None:
    merged, note = CharterMerger().merge("ceo/eng", {"role": "Old"}, {"role": "New", "tools": []})
    assert merged == {"role": "New", "tools": []}
    assert note == "charter frontmatter of `ceo/eng`: nothing kept from the old frontmatter (your text set every key). changed (old -> new): role: Old -> New. added: tools: []. " + NOTE_END


def test_the_note_of_a_rewrite_that_changes_nothing() -> None:
    _, note = CharterMerger().merge("a", {"role": "R", "tools": ["read"]}, {"role": "R", "tools": ["read"]})
    assert note == "charter frontmatter of `a`: nothing kept from the old frontmatter (your text set every key). no key changed. " + NOTE_END


def test_the_note_lists_kept_changed_and_added_in_that_order() -> None:
    _, note = CharterMerger().merge("lead/rev", {"role": "R", "model": "m", "max_children": 5, "tools": ["read"]}, {"role": "S", "tools": ["read"], "new": 1, "max_children": 2})
    assert note == (
        "charter frontmatter of `lead/rev`: kept from the old frontmatter (not in your text): model. "
        "changed (old -> new): role: R -> S; max_children: 5 -> 2. added: new: 1. " + NOTE_END
    )


def test_a_note_without_changes_but_with_kept_keys_says_so() -> None:
    _, note = CharterMerger().merge("a", {"role": "R", "model": "m"}, {"role": "R"})
    assert note == "charter frontmatter of `a`: kept from the old frontmatter (not in your text): model. no key changed. " + NOTE_END


def test_the_note_of_the_function_ignores_the_merged_mapping_but_keeps_its_text() -> None:
    assert charter_change_note("a", {"role": "R"}, {"role": "S"}, {"anything": "at all"}) == (
        "charter frontmatter of `a`: nothing kept from the old frontmatter (your text set every key). changed (old -> new): role: R -> S. " + NOTE_END
    )


@pytest.mark.parametrize(
    ("value", "text"),
    [
        ("plain", "plain"), (5, "5"), (None, "null"), (True, "true"), (["read", "write"], "[read, write]"), ([], "[]"), ({}, "{}"),
        ({"a": 1}, "{a: 1}"), ("two\nlines", "'two lines'"), ("é世", "é世"), (2.5, "2.5"),
    ],
)
def test_a_value_is_shown_as_flow_yaml_on_one_line(value: object, text: str) -> None:
    assert _short(value) == text


def test_a_long_value_is_cut_to_the_limit_with_an_ellipsis() -> None:
    assert _short("x" * 80) == "x" * 80
    assert _short("x" * 81) == "x" * 79 + "…" and len(_short("x" * 81)) == 80
    assert _short(["item"] * 40, 20) == "[item, item, item, …" and len(_short(["item"] * 40, 20)) == 20


def test_blanks_inside_a_long_value_are_collapsed_before_it_is_cut() -> None:
    assert _short("a   b\t\tc") == '"a b\\t\\tc"'  # a quoted scalar: the escapes stay, the runs of blanks are one
