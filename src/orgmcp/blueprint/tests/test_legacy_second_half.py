"""The old module-level functions of the second half of ``orgmcp.blueprint`` are adapters over the classes of the package.

``apply`` builds with the ports its ``Org`` has *now* (``org.runtime``): an ``Org`` whose runtime was opened with other ports applies through them. The
old private helpers of the plan and the application are gone from ``_legacy``; the block, the details, the id and the playbook are the classes' output."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import cast

import pytest

import orgmcp.blueprint as bpm
from orgmcp.blueprint import _legacy, api

from ._plans import base_dir, golden, scrub, template_at


def bp_of(key: str, base: Path) -> dict[str, object]:
    label, _, variant = key.partition("/")
    return bpm.load_text(template_at(label, variant, base))


@pytest.mark.parametrize("key", ["research/filled", "code-service/raw"])
def test_the_functions_of_the_plan_answer_what_the_flat_module_answered(key: str, tmp_path: Path) -> None:
    base = base_dir(tmp_path)
    bp, expected = bp_of(key, base), golden()["plans"][key]
    issues = bpm.validate(bp, allowed_roots=[base])
    assert scrub(bpm.render_plan(bp, issues, allowed_roots=[base]), base) == expected["details"]
    assert scrub(bpm.plan_for_user(bp, issues, allowed_roots=[base]), base) == expected["block"]
    assert scrub(bpm.render_plan(bp, allowed_roots=[base]), base) == expected["details"]  # the issues default to what validate finds
    assert bpm.plan_id(bp) == bpm.plan_id(dict(reversed(list(bp.items()))))


def test_the_playbook_function_is_the_class_text(tmp_path: Path) -> None:
    base = base_dir(tmp_path)
    bp = bp_of("research-service/filled", base)
    agents = bpm._resolve(bp, None, [base], [])
    service = cast(list[dict[str, object]], bp["services"])[0]
    budget = bpm.service_budget(service, cast(int, bpm.estimate(agents)["total"]), 25)
    assert scrub(bpm.default_playbook(agents[0], agents, service, budget), base) == golden()["playbooks"]["research-service/my-service"]


def test_the_private_helper_of_the_user_block_is_the_words_of_the_access_report() -> None:
    a = api.Agent(addr="a", name="a", parent=None, where="agents[a]", kind="author", tools=["write"], workspace="/w")
    assert bpm._agent_access(a) == "changes files only in /w"


MOVED = [
    "_charter", "_tree_lines", "_user_tree", "_user_budget", "_failure_policy", "_input_words", "_svc_delivery", "_request_words",
    "_reflection_line", "_user_services", "_models_line", "Summary",
]


def defined_in_legacy() -> set[str]:
    names: set[str] = set()
    for node in ast.parse(Path(_legacy.__file__).read_text(encoding="utf-8")).body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            names.add(node.name)
    return names


@pytest.mark.parametrize("name", MOVED)
def test_a_helper_that_a_class_replaced_is_not_defined_in_the_legacy_module_any_more(name: str) -> None:
    assert name not in defined_in_legacy()


def test_the_summary_is_the_one_of_the_api() -> None:
    assert bpm.Summary is api.Summary and "Summary" not in defined_in_legacy()


def test_the_legacy_module_is_nothing_but_adapters_and_constants() -> None:
    tree = ast.parse(Path(_legacy.__file__).read_text(encoding="utf-8"))
    assert not [n.name for n in tree.body if isinstance(n, ast.ClassDef)]
    assert not Path(_legacy.__file__).read_text(encoding="utf-8").startswith("# mypy: ignore-errors")
