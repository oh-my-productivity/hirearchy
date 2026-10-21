"""Contract of ``ContractNormalizer``: the free input of a contract in its fixed form (pure logic: one implementation)."""

from __future__ import annotations

from pathlib import Path

import pytest

from hirearchy.kernel import OrgError
from hirearchy.services import ContractNormalizer
from hirearchy.services.testing import IMPLEMENTATIONS

from ._support import implementations


@pytest.fixture(params=implementations(IMPLEMENTATIONS[ContractNormalizer]))
def n(request: pytest.FixtureRequest, tmp_path: Path) -> ContractNormalizer:
    made = request.param(tmp_path)
    assert isinstance(made, ContractNormalizer)
    return made


# ------------------------------------------------------------------------------ parse_input_spec


@pytest.mark.parametrize("spec, expected", [
    ("topic*:what it is about", {"name": "topic", "description": "what it is about", "required": True}),
    ("topic:what", {"name": "topic", "description": "what", "required": False}),
    ("topic", {"name": "topic", "description": "", "required": False}),
    ("  topic * : with: colon ", {"name": "topic", "description": "with: colon", "required": True}),
    ("*", {"name": "", "description": "", "required": True}),
])
def test_an_input_spec_is_a_name_a_star_for_required_and_a_description(n: ContractNormalizer, spec: str, expected: dict[str, object]) -> None:
    assert n.parse_input_spec(spec) == expected


# ------------------------------------------------------------------------------ inputs


def test_no_inputs_is_an_empty_list(n: ContractNormalizer) -> None:
    assert n.inputs(None) == [] and n.inputs([]) == [] and n.inputs(()) == []


def test_an_input_is_a_name_a_description_and_whether_it_is_required(n: ContractNormalizer) -> None:
    assert n.inputs([{"name": "topic"}, {"name": "week", "description": "  ISO week ", "required": False}, "extra*:more"]) == [
        {"name": "topic", "description": "", "required": True},
        {"name": "week", "description": "ISO week", "required": False},
        {"name": "extra", "description": "more", "required": True},
    ]


@pytest.mark.parametrize("value, text", [
    ("topic", "inputs must be a list of {name, description, required} (or may be empty)"),
    ({"name": "a"}, "inputs must be a list of {name, description, required} (or may be empty)"),
    ([5], "each input must be {name, description, required} (got 5)"),
    ([{"name": "a", "x": 1, "y": 2}], "unknown key(s) in input 'a': x, y. Use name, description, required"),
    ([{"name": "A"}], "input name must be lowercase letters, digits and underscores, starting with a letter (max 32): 'A'"),
    ([{"name": ""}], "input name must be lowercase letters, digits and underscores, starting with a letter (max 32): ''"),
    ([{"name": "a" * 33}], "input name must be lowercase letters, digits and underscores, starting with a letter (max 32): '" + "a" * 33 + "'"),
    ([{"name": "a"}, "a"], "input name used twice: a"),
    ([{"name": "a", "required": 1}], "input a: required must be true or false"),
])
def test_what_inputs_refuses_and_says(n: ContractNormalizer, value: object, text: str) -> None:
    with pytest.raises(OrgError) as e:
        n.inputs(value)
    assert str(e.value) == text


def test_a_name_of_thirty_two_characters_is_the_longest(n: ContractNormalizer) -> None:
    name = "a" + "b_1" * 10 + "c"
    assert len(name) == 32 and n.inputs([{"name": name}])[0]["name"] == name


# ------------------------------------------------------------------------------ deliverable


def test_a_deliverable_is_a_description_and_the_optional_rest(n: ContractNormalizer) -> None:
    assert n.deliverable({"description": " a report "}) == {"description": "a report"}
    assert n.deliverable({"description": "a report", "format": " pdf ", "max_words": 90, "path": "/data/out.pdf"}) == {
        "description": "a report", "format": "pdf", "max_words": 90, "path": "/data/out.pdf",
    }


def test_empty_optional_parts_are_left_out(n: ContractNormalizer) -> None:
    assert n.deliverable({"description": "d", "format": "", "max_words": None, "path": ""}) == {"description": "d"}
    assert n.deliverable({"description": "d", "max_words": ""}) == {"description": "d"}


@pytest.mark.parametrize("value, text", [
    (None, "deliverable must be {description, format?, max_words?, path?}"),
    ("a file", "deliverable must be {description, format?, max_words?, path?}"),
    ({}, "deliverable needs a description: what the owner hands back (e.g. one markdown file)"),
    ({"description": "  "}, "deliverable needs a description: what the owner hands back (e.g. one markdown file)"),
    ({"description": "d", "z": 1, "a": 2}, "unknown key(s) in deliverable: a, z. Use description, format, max_words, path"),
    ({"description": "d", "max_words": 0}, "deliverable.max_words must be a whole number of at least 1"),
    ({"description": "d", "max_words": True}, "deliverable.max_words must be a whole number of at least 1"),
    ({"description": "d", "max_words": 2.5}, "deliverable.max_words must be a whole number of at least 1"),
    ({"description": "d", "path": "out/x.md"}, "deliverable.path must be an absolute path (got 'out/x.md')"),
])
def test_what_deliverable_refuses_and_says(n: ContractNormalizer, value: object, text: str) -> None:
    with pytest.raises(OrgError) as e:
        n.deliverable(value)
    assert str(e.value) == text


def test_the_normal_form_does_not_change_when_it_is_normalized_again(n: ContractNormalizer) -> None:
    inputs = n.inputs(["topic*:what", {"name": "week", "required": False}])
    assert n.inputs(inputs) == inputs
    deliverable = n.deliverable({"description": "d", "max_words": 5})
    assert n.deliverable(deliverable) == deliverable
