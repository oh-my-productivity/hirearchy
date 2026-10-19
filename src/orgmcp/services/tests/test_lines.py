"""``criteria_lines``: criteria as callers write them (a list, or one newline-separated string)."""

from __future__ import annotations

import pytest

from orgmcp.kernel import OrgError
from orgmcp.services._lines import criteria_lines


def test_nothing_is_no_criteria() -> None:
    assert criteria_lines(None, "acceptance", required=False) == []


def test_a_string_is_split_into_lines_stripped_and_unbulleted() -> None:
    assert criteria_lines("- one\n* two\n  three  \n\n-\n*\n", "acceptance", required=False) == ["one", "two", "three"]


def test_a_list_is_split_the_same_way_item_by_item() -> None:
    assert criteria_lines(["- a\nb", " c "], "acceptance", required=False) == ["a", "b", "c"]
    assert criteria_lines(("x",), "acceptance", required=False) == ["x"]


def test_a_bullet_without_a_space_is_text() -> None:
    assert criteria_lines("-x\n*y", "acceptance", required=False) == ["-x", "*y"]


def test_required_criteria_cannot_be_empty() -> None:
    for empty in ([], "", " \n- \n", ["-", "  "]):
        with pytest.raises(OrgError) as e:
            criteria_lines(empty, "acceptance", required=True)
        assert str(e.value) == "acceptance needs at least one non-empty criterion: concrete, checkable conditions the delivery must meet"


def test_other_types_are_refused_with_the_name_of_the_field() -> None:
    with pytest.raises(OrgError) as e:
        criteria_lines(5, "extra_acceptance", required=False)
    assert str(e.value) == "extra_acceptance must be a list of strings (or one newline-separated string)"
    with pytest.raises(OrgError) as e:
        criteria_lines(["ok", None], "extra_acceptance", required=False)
    assert str(e.value) == "extra_acceptance must contain only strings (got None)"
