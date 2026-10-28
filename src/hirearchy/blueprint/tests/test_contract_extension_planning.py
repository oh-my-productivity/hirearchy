"""Contract of ``ExtensionPlanning``: the plan of an extension as text; it only reads, and an extension with errors is a draft."""

from __future__ import annotations

from pathlib import Path

import pytest

from hirearchy.blueprint._protocols import ExtensionPlanning

from ._extension_world import World, extension, world

GOOD = extension(limits=[{"agent": "lead", "max_children": 3}])
BAD = extension(limits=[{"agent": "ghost", "max_children": 3}])


@pytest.fixture
def planning(tmp_path: Path) -> tuple[ExtensionPlanning, World]:
    w = world(tmp_path)
    made = w.planner()
    assert isinstance(made, ExtensionPlanning)
    return made, w


def test_a_valid_extension_is_a_plan_for_the_user(planning: tuple[ExtensionPlanning, World]) -> None:
    made, w = planning
    text = made.plan(GOOD, allowed_roots=[w.tmp])
    assert text.block.startswith("PLAN FOR YOU (a change to your organization)") and not [i for i in text.issues if i.level == "error"]
    assert text.block == made.plan(GOOD, allowed_roots=[w.tmp]).block


def test_an_extension_with_errors_is_a_draft(planning: tuple[ExtensionPlanning, World]) -> None:
    made, w = planning
    text = made.plan(BAD, allowed_roots=[w.tmp])
    assert text.block.startswith("DRAFT - NOT READY") and text.block.endswith("Cannot apply yet.") and [i.code for i in text.issues] == ["extend-limit"]


def test_planning_changes_nothing(planning: tuple[ExtensionPlanning, World]) -> None:
    made, w = planning
    before = sorted(str(p.relative_to(w.org.root)) for p in w.org.root.rglob("*"))
    made.plan(GOOD, allowed_roots=[w.tmp])
    assert sorted(str(p.relative_to(w.org.root)) for p in w.org.root.rglob("*")) == before
