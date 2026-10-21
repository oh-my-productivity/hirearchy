# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

import json

import pytest
import testkit

from testkit.blueprint_world import bpm
from hirearchy.blueprint import BlueprintError

EXAMPLE = testkit.REPO / "examples" / "blueprint-research.yaml"


# ------------------------------------------------------------------------------------------- loading
def test_load_from_yaml_text_json_and_path(tmp_path):
    text = EXAMPLE.read_text()
    from_text = bpm.load(text)
    assert from_text["needs"]["budget_runs"] == 25 and from_text["agents"][0]["template"] == "manager"
    assert bpm.load(EXAMPLE) == from_text
    assert bpm.load(str(EXAMPLE)) == from_text
    assert bpm.load(json.dumps(from_text)) == from_text


def test_load_acceptance_text_becomes_list():
    bp = bpm.load("mission: m\ntask:\n  acceptance: |\n    - first criterion here\n    2. second criterion here\n")
    assert bp["task"]["acceptance"] == ["first criterion here", "second criterion here"]


@pytest.mark.parametrize("text", ["- a\n- b\n", "just text", "a: [unclosed"])
def test_load_rejects_non_blueprints(text):
    with pytest.raises(BlueprintError):
        bpm.load(text)
