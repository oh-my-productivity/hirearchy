"""Contract of ``BlueprintExamples``: the ready-to-edit templates. A template is a pure function of (kind, base, service): one implementation, no fake."""

from __future__ import annotations

import pytest
import yaml

from orgmcp.blueprint import EXAMPLE_KINDS, BlueprintExamples
from orgmcp.blueprint._examples import TemplateBlueprintExamples
from orgmcp.kernel import OrgError

from ._plans import FIXED_BASE, LABELS, golden
from ._support import RED

pytestmark = RED


@pytest.fixture
def examples() -> BlueprintExamples:
    made = TemplateBlueprintExamples()
    assert isinstance(made, BlueprintExamples)
    return made


@pytest.mark.parametrize("label", LABELS)
def test_every_template_is_the_text_the_flat_module_made_byte_for_byte(examples: BlueprintExamples, label: str) -> None:
    kind, _, service = label.partition("-")
    assert examples.example(kind, FIXED_BASE, bool(service)) == golden()["examples"][label]


@pytest.mark.parametrize("label", LABELS)
def test_every_template_is_valid_yaml_with_the_four_keys(examples: BlueprintExamples, label: str) -> None:
    kind, _, service = label.partition("-")
    bp = yaml.safe_load(examples.example(kind, "/b", bool(service)))
    assert {"mission", "needs", "agents"} <= set(bp) and ("services" in bp) == bool(service)


def test_the_default_is_the_research_template_in_the_working_directory(examples: BlueprintExamples) -> None:
    assert examples.example() == examples.example("research", ".", False)
    assert "path: ./deliverables/<name>.md" in examples.example()


def test_the_base_is_made_into_an_absolute_looking_prefix_without_a_trailing_slash(examples: BlueprintExamples) -> None:
    assert examples.example("code", "/work/") == examples.example("code", "/work")
    assert "path: //deliverables/<name>.md" in examples.example("research", "/")  # (the root is kept as the one slash, as it always was)


def test_the_kind_is_trimmed_and_case_insensitive(examples: BlueprintExamples) -> None:
    assert examples.example("  Research ", "/b") == examples.example("research", "/b")
    assert examples.example("", "/b") == examples.example("research", "/b")


def test_another_kind_is_refused_and_the_kinds_are_listed(examples: BlueprintExamples) -> None:
    with pytest.raises(OrgError, match=r"unknown kind 'poetry': use one of research, documents, code, analysis \(research = web sources"):
        examples.example("poetry")


def test_the_service_template_has_no_deliverable_of_its_own_in_needs(examples: BlueprintExamples) -> None:
    plain, service = yaml.safe_load(examples.example("research", "/b")), yaml.safe_load(examples.example("research", "/b", True))
    assert "deliverable" in plain["needs"] and "deliverable" not in service["needs"] and "task" not in service
