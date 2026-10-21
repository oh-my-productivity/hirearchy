"""Contract of ``DocumentTemplates``: every registered implementation renders the documents byte for byte as before the move."""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import cast

import pytest

from hirearchy.templates import DocumentTemplates
from hirearchy.templates.testing import IMPLEMENTATIONS

from ._cases import DOCUMENT_CASES, Case
from ._golden import expected, render


@pytest.fixture(params=IMPLEMENTATIONS[DocumentTemplates], ids=lambda factory: factory.__name__)
def templates(request: pytest.FixtureRequest) -> DocumentTemplates:
    made = cast(Callable[[], DocumentTemplates], request.param)()
    assert isinstance(made, DocumentTemplates)
    return made


@pytest.mark.parametrize("case", DOCUMENT_CASES, ids=lambda case: case.name)
def test_the_text_is_byte_identical_to_the_text_before_the_move(templates: DocumentTemplates, case: Case) -> None:
    assert render(templates, case) == expected(case.name)


def test_the_rules_are_numbered_without_gaps(templates: DocumentTemplates) -> None:
    numbers = [int(n) for n in re.findall(r"^(\d+)\. ", templates.org_rules("m"), re.M)]
    assert len(numbers) >= 10 and numbers == list(range(1, len(numbers) + 1))


def test_the_rules_are_filled_in_completely(templates: DocumentTemplates) -> None:
    assert "{" not in templates.org_rules("m") and "}" not in templates.org_rules("m")


def test_the_mission_is_stripped_and_a_missing_one_gets_the_placeholder(templates: DocumentTemplates) -> None:
    assert "## Mission\nShip it.\n\n## How" in templates.org_rules("  Ship it.\n")
    for missing in (None, ""):
        assert "## Mission\n(Describe the mission of this organization here.)\n\n## How" in templates.org_rules(missing)
    assert "## Mission\n\n\n## How" in templates.org_rules("  \n")  # a blank (but not empty) mission is stripped to nothing, as before


@pytest.mark.parametrize("charter", ["Build things.", "# Role: Builder\n\nBuild things.", "\n# Lead builder\n\nBuild things.\n", "## Duties\nBuild things."])
def test_a_charter_has_exactly_one_h1(templates: DocumentTemplates, charter: str) -> None:
    body = templates.charter_body("Builder", charter)
    assert len(re.findall(r"^# .*$", body, flags=re.M)) == 1
    assert "Build things." in body and body.endswith("\n") and not body.endswith("\n\n")


def test_the_hirers_own_heading_wins_over_the_generated_one(templates: DocumentTemplates) -> None:
    assert templates.charter_body("Builder", "# Lead builder\nx").startswith("# Lead builder\n")
    assert templates.charter_body("Builder", "x").startswith("# Role: Builder\n\n")


def test_a_task_lists_its_inputs_only_when_it_has_some(templates: DocumentTemplates) -> None:
    assert "## Inputs" not in templates.task_body("g", "a", [])
    assert templates.task_body("g", "a", ("x.md", "y.md")).endswith("## Inputs\n- x.md\n- y.md")  # any sequence, not only a list


def test_a_result_orders_summary_lessons_artifacts(templates: DocumentTemplates) -> None:
    body = templates.result_body("s", ("a.md",), "l")
    assert body.index("## Summary") < body.index("## Lessons") < body.index("## Artifacts")
    assert "## Lessons" not in templates.result_body("s", [], " \n")


def test_rendering_twice_gives_the_same_text(templates: DocumentTemplates) -> None:
    assert templates.org_rules("m") == templates.org_rules("m")
    assert templates.result_body("s", ["a"], "l") == templates.result_body("s", ["a"], "l")
