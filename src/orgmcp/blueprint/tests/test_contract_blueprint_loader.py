"""Contract of ``BlueprintLoader``: a blueprint from a dict, a file or text, and the lenient forms made strict."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from orgmcp.blueprint import BlueprintError, BlueprintLoader
from orgmcp.blueprint.testing import IMPLEMENTATIONS, LoaderHarness

from ._support import implementations, make

TEXT = "mission: a mission\nneeds: {scope: s}\n"


@pytest.fixture(params=implementations(IMPLEMENTATIONS[BlueprintLoader]))
def h(request: pytest.FixtureRequest, tmp_path: Path) -> LoaderHarness:
    made = make(request, tmp_path, LoaderHarness)
    assert isinstance(made.loader, BlueprintLoader)
    return made


def test_yaml_text_is_a_blueprint(h: LoaderHarness) -> None:
    assert h.loader.load_text(TEXT) == {"mission": "a mission", "needs": {"scope": "s"}}
    assert h.loader.load(TEXT) == {"mission": "a mission", "needs": {"scope": "s"}}


def test_json_text_is_a_blueprint(h: LoaderHarness) -> None:
    bp = {"mission": "m", "agents": [{"name": "lead", "template": "manager"}]}
    assert h.loader.load_text(json.dumps(bp)) == bp


@pytest.mark.parametrize("text", ["- a\n- b\n", "just text", "", "42"])
def test_text_that_is_not_a_mapping_is_refused(h: LoaderHarness, text: str) -> None:
    with pytest.raises(BlueprintError, match="a blueprint is a mapping with mission, needs, agents and task"):
        h.loader.load_text(text)


def test_text_that_is_not_yaml_is_refused_with_the_reason(h: LoaderHarness) -> None:
    with pytest.raises(BlueprintError, match="^blueprint is not valid YAML/JSON: ") as err:
        h.loader.load_text("a: [unclosed")
    assert isinstance(err.value, BlueprintError)


def test_load_text_never_reads_a_file_whatever_the_text_looks_like(h: LoaderHarness) -> None:
    path = h.directory / "bp.yaml"
    h.put_file(path, TEXT)
    with pytest.raises(BlueprintError, match="a blueprint is a mapping"):
        h.loader.load_text(str(path))  # the text of a file name is text
    assert h.reads() == []


def test_a_path_is_read(h: LoaderHarness) -> None:
    path = h.directory / "sub" / "bp.yaml"
    h.put_file(path, TEXT)
    assert h.loader.load(path) == {"mission": "a mission", "needs": {"scope": "s"}}
    assert h.reads() == [path]


def test_the_name_of_an_existing_file_is_read(h: LoaderHarness) -> None:
    path = h.directory / "bp.yaml"
    h.put_file(path, TEXT)
    assert h.loader.load(str(path)) == {"mission": "a mission", "needs": {"scope": "s"}}
    assert h.reads() == [path]


def test_the_name_of_a_file_that_is_not_there_is_text(h: LoaderHarness) -> None:
    with pytest.raises(BlueprintError, match="a blueprint is a mapping"):
        h.loader.load(str(h.directory / "nothing.yaml"))
    assert h.reads() == []


def test_text_with_a_line_break_is_never_taken_for_a_file_name(h: LoaderHarness) -> None:
    path = h.directory / "two\nlines.yaml"  # a file that exists, whose name has a line break
    h.put_file(path, TEXT)
    with pytest.raises(BlueprintError, match="a blueprint is a mapping"):
        h.loader.load(str(path))
    assert h.loader.load("mission: m\n") == {"mission": "m"}
    assert h.reads() == []


def test_a_dict_is_a_blueprint_and_no_file_is_read(h: LoaderHarness) -> None:
    bp = {"mission": "m", "agents": []}
    assert h.loader.load(bp) == bp
    assert h.reads() == []


def test_a_value_that_is_neither_is_read_as_its_text(h: LoaderHarness) -> None:
    with pytest.raises(BlueprintError, match="a blueprint is a mapping"):
        h.loader.load(42)


def test_acceptance_given_as_a_bullet_or_numbered_text_becomes_a_list(h: LoaderHarness) -> None:
    bp = h.loader.load_text("mission: m\ntask:\n  acceptance: |\n    - first criterion here\n    2. second criterion here\n    * third one\n\n    4) fourth\n")
    assert bp["task"] == {"acceptance": ["first criterion here", "second criterion here", "third one", "fourth"]}


def test_a_services_acceptance_gets_the_same_leniency(h: LoaderHarness) -> None:
    bp = h.loader.load_text("mission: m\nservices:\n  - {name: a, acceptance: \"- one two three four\\n- five six seven eight\"}\n  - {name: b, acceptance: [x y z w]}\n  - plain text\n")
    assert bp["services"] == [{"name": "a", "acceptance": ["one two three four", "five six seven eight"]}, {"name": "b", "acceptance": ["x y z w"]}, "plain text"]


def test_a_list_of_criteria_is_left_alone(h: LoaderHarness) -> None:
    given = {"mission": "m", "task": {"acceptance": ["- keeps its dash"]}}
    assert h.loader.load(given) == given


def test_the_given_dict_is_not_changed(h: LoaderHarness) -> None:
    given = {"mission": "m", "task": {"acceptance": "- a b c d\n- e f g h"}, "services": [{"name": "s", "acceptance": "- i j k l"}]}
    before = copy.deepcopy(given)
    loaded = h.loader.load(given)
    assert given == before
    assert loaded["task"] == {"acceptance": ["a b c d", "e f g h"]}
