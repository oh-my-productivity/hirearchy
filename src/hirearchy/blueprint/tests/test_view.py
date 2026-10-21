"""The accessors over the normalized blueprint: what they answer for what is missing or of the wrong type."""

from __future__ import annotations

from pathlib import Path

import pytest

from hirearchy.blueprint._view import (
    cap_of,
    criteria_of,
    deliverable_of,
    has_plain_task,
    is_plain,
    is_request,
    items,
    mapping_or_empty,
    needs_of,
    s,
    services_of,
    svc_criteria,
    svc_deliverable,
    task_of,
    unknown,
)
from hirearchy.blueprint.api import Issue
from hirearchy.kernel import inside




def test_text_is_stripped_and_none_is_empty() -> None:
    assert (s(None), s("  a b  "), s(7), s(["x"])) == ("", "a b", "7", "['x']")


def test_items_split_text_on_commas_and_blanks_and_strip_a_list() -> None:
    assert items("read, write shell") == ["read", "write", "shell"]
    assert items([" a ", "", "b"]) == ["a", "b"]
    assert items(None) == [] and items("") == []


def test_a_mapping_or_nothing() -> None:
    assert mapping_or_empty({"a": 1}) == {"a": 1}
    assert [mapping_or_empty(v) for v in (None, "x", [1], 3)] == [{}, {}, {}, {}]


def test_unknown_keys_are_warnings_that_list_the_known_ones() -> None:
    issues: list[Issue] = []
    unknown({"a": 1, "z": 2, "b": 3}, {"a", "b"}, "needs", issues)
    assert issues == [Issue("warning", "needs", "unknown key 'z' is ignored; check the spelling (known: a, b)", "unknown-key")]


def test_needs_task_and_deliverable_default_to_empty() -> None:
    assert needs_of({}) == {} and task_of({"task": "text"}) == {} and deliverable_of({}) == {}
    assert deliverable_of({"needs": {"deliverable": "a report"}}) == {"description": "a report"}
    assert deliverable_of({"needs": {"deliverable": {"description": "d"}}}) == {"description": "d"}
    assert svc_deliverable({"deliverable": "one file"}) == {"description": "one file"} and svc_deliverable({}) == {}


def test_criteria_are_the_stripped_list_of_the_task_or_of_a_service() -> None:
    assert criteria_of({"task": {"acceptance": [" a b ", 2]}}) == ["a b", "2"]
    assert criteria_of({"task": {"acceptance": "text"}}) == [] and criteria_of({"task": "x"}) == [] and criteria_of({}) == []
    assert svc_criteria({"acceptance": ["a", "", "  ", "b"]}) == ["a", "b"] and svc_criteria({"acceptance": "x"}) == []


def test_services_are_the_mappings_of_the_list() -> None:
    assert services_of({"services": [{"name": "a"}, "b", 3, {"name": "c"}]}) == [{"name": "a"}, {"name": "c"}]
    assert services_of({"services": "a"}) == [] and services_of({}) == []


def test_a_request_is_a_task_with_a_service_key() -> None:
    assert is_request({"task": {"service": "x"}}) and not is_request({"task": {"title": "t"}}) and not is_request({"task": "t"})


def test_plain_task_rules_apply_without_services_or_beside_a_task_that_is_not_a_request() -> None:
    svc = {"services": [{"name": "a"}]}
    assert is_plain({}) and is_plain({"task": {"title": "t"}})
    assert not is_plain(svc) and not is_plain({**svc, "task": {"service": "a"}}) and is_plain({**svc, "task": {"title": "t"}})
    assert has_plain_task({"task": {"title": "t"}}) and not has_plain_task({"task": {"service": "a"}}) and not has_plain_task({})


@pytest.mark.parametrize("value, cap", [(25, 25), (1, 1), (0, None), (-3, None), (True, None), ("25", None), (None, None), (2.5, None)])
def test_the_cap_is_a_whole_number_of_runs(value: object, cap: int | None) -> None:
    assert cap_of({"budget_runs": value}) == cap


