# mypy: ignore-errors
# A test moved from tests/ by tools/relocate_tests.py: untyped until it is converted. Delete the first line when this file is typed.

import copy

import pytest
import testkit
import yaml
from testkit.blueprints import code_bp
from testkit.legacy.orgmcp.core import DEFAULT_MODEL

from testkit.blueprint_world import bpm

EXAMPLE = testkit.REPO / "examples" / "blueprint-research.yaml"


@pytest.fixture
def base(tmp_path):
    """tmp_path as the only allowed root; the example research blueprint with its deliverable inside it."""
    (tmp_path / "deliverables").mkdir()
    bp = yaml.safe_load(EXAMPLE.read_text())
    bp["needs"]["deliverable"]["path"] = str(tmp_path / "deliverables" / "competitors.md")
    return bp


def tiered(bp):
    """The example blueprint with the cheap-drafting / strong-review tiers the user asked for."""
    bp["needs"]["models"] = {"cheap": "claude-haiku-4.5", "strong": "claude-sonnet-4.6"}
    bp["needs"]["model_policy"] = "cheap drafting, strong review"
    return bp


@pytest.fixture
def roots(tmp_path):
    return [tmp_path]


def codes(issues, level=None):
    return {i.code for i in issues if level is None or i.level == level}


def check(bp, roots, **kw):
    return bpm.validate(bp, allowed_roots=roots, **kw)


def mutate(bp, fn):
    out = copy.deepcopy(bp)
    fn(out)
    return out


def test_manager_tools_and_workspace_default_to_what_it_must_grant(tmp_path, roots):
    agents = bpm._resolve(code_bp(tmp_path), None, roots, [])
    lead = next(a for a in agents if a.name == "lead")
    assert {"read", "write", "shell"} <= set(lead.tools) and lead.workspace == str((tmp_path / "proj").resolve())
    assert lead.can_hire and lead.max_children == 3


def test_budget_cap_and_estimate(base, roots):
    assert bpm.estimate(bpm._resolve(base, None, roots, []))["total"] == 17
    over = mutate(base, lambda b: b["task"].update(budget=30))
    assert "budget-cap" in codes(check(over, roots), "error")
    low = mutate(base, lambda b: b["task"].update(budget=12))
    assert "budget-low" in codes(check(low, roots), "error")
    capped_low = mutate(base, lambda b: b["needs"].update(budget_runs=10))
    assert "budget-low" in codes(check(capped_low, roots), "error")
    tight = mutate(base, lambda b: b["task"].update(budget=18))
    t = check(tight, roots)
    assert "budget-tight" in codes(t, "warning") and not bpm.errors(t)
    assert "budget" in codes(check(mutate(base, lambda b: b["needs"].pop("budget_runs")), roots), "warning")


def test_estimate_formula(base, roots):
    est = bpm.estimate(bpm._resolve(base, None, roots, []))
    assert est["per"]["lead"] == {"pass": 5, "rework": 2, "total": 7}  # 1 + 3 reports + 1; rework 2
    assert est["per"]["lead/researcher"] == {"pass": 3, "rework": 1, "total": 4}
    assert est["per"]["lead/writer"]["total"] == 3 and est["per"]["lead/factcheck"]["total"] == 4 - 1
    scaled = mutate(base, lambda b: b["agents"][0]["children"][0].update(scale=2))
    assert bpm.estimate(bpm._resolve(scaled, None, roots, []))["per"]["lead/researcher"]["pass"] == 6


def test_budget_split_keeps_a_reserve(base, roots):
    agents = bpm._resolve(base, None, roots, [])
    split = bpm.budget_split(agents, 22)
    grants = {a: v["grant"] for a, v in split.items()}
    # a worker is granted its pass plus its rework (author) or re-check (verifier) run
    assert grants == {"lead": 22, "lead/researcher": 4, "lead/writer": 3, "lead/factcheck": 3}
    assert split["lead"]["keeps"] == 12 and sum(grants.values()) - 22 + split["lead"]["keeps"] == 22


def test_nested_manager_gets_its_whole_subtree(roots, tmp_path):
    bp = {"agents": [{"name": "boss", "template": "manager", "children": [
        {"name": "sub", "template": "manager", "children": [{"name": "w", "template": "writer"}, {"name": "rv", "template": "reviewer"}]}]}]}
    agents = bpm._resolve(bp, None, roots, [])
    est = bpm.estimate(agents)
    split = bpm.budget_split(agents, est["total"])
    assert split["boss/sub"]["grant"] == est["per"]["boss/sub"]["total"] + est["per"]["boss/sub/w"]["total"] + est["per"]["boss/sub/rv"]["total"]
    assert split["boss"]["keeps"] == est["per"]["boss"]["total"]


def test_tier_without_mapping_is_the_default_model_and_no_policy_warns_only_when_models_differ(base, roots):
    unmapped = mutate(base, lambda b: b["needs"].pop("models"))
    assert "model-tier" not in codes(check(unmapped, roots)) and "model-policy" not in codes(check(unmapped, roots))
    assert {a.model for a in bpm._resolve(unmapped, None, roots, [])} == {DEFAULT_MODEL}
    assert "model-policy" not in codes(check(mutate(base, lambda b: b["needs"].pop("model_policy")), roots))  # one model: nothing to state
    no_policy = mutate(tiered(copy.deepcopy(base)), lambda b: b["needs"].pop("model_policy"))
    assert "model-policy" in codes(check(no_policy, roots), "warning")
    single = mutate(base, lambda b: (b["needs"].update(model_policy="one model for everyone"), b["needs"].pop("models"),
                                     [a.pop("model", None) for a in (b["agents"][0], *b["agents"][0]["children"])]))
    assert not bpm.errors(check(single, roots))
