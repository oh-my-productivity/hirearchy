# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

import copy

import pytest
import testkit
import yaml
from testkit.blueprints import code_bp
from testkit.reach.hirearchy.core import Org

from testkit.blueprint_world import bpm
from hirearchy.blueprint import Issue

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
    bp["needs"]["models"] = {"cheap": "claude-sonnet-5.5", "strong": "claude-opus-5.5"}
    bp["needs"]["model_policy"] = "cheap drafting, strong review"
    return bp


@pytest.fixture
def roots(tmp_path):
    return [tmp_path]


@pytest.fixture
def empty_org(tmp_path):
    return Org.init(tmp_path / "org", "bp tests", {"poll_seconds": 0.05})


def mutate(bp, fn):
    out = copy.deepcopy(bp)
    fn(out)
    return out


def test_planned_budget_has_slack_and_respects_cap(base, roots):
    assert bpm.planned_total(base, 17) == 22  # ceil(17 * 1.25), under the cap of 25
    assert bpm.planned_total(mutate(base, lambda b: b["needs"].update(budget_runs=18)), 17) == 18
    assert bpm.planned_total(mutate(base, lambda b: b["task"].update(budget=19)), 17) == 19


# ------------------------------------------------------------------------------------------ the plan
def test_render_plan_contents(base, roots):
    base = tiered(base)
    text = bpm.render_plan(base, bpm.validate(base, allowed_roots=roots), allowed_roots=roots)
    for expected in ("Goal:", "Obsidian, Logseq, Joplin", "max 1500 words", "lead/researcher", "model=claude-sonnet-5.5",
                     "model=claude-opus-5.5", "tools=web_fetch,web_search", "Budget: 22 runs planned (your cap: 25), estimate 17",
                     "factcheck", "nobody edits another agent's file", "competitors.md", "copied there by the assistant",
                     "1. Covers exactly", "Checkpoints:", "Warnings (1):", "Reply 'approve' or tell me what to change."):
        assert expected in text, expected
    assert text.rstrip().endswith("Reply 'approve' or tell me what to change.")
    assert len(text.splitlines()) < 70


def test_render_plan_with_errors_does_not_offer_approval(base, roots):
    bp = mutate(base, lambda b: b["task"].pop("acceptance"))
    text = bpm.render_plan(bp, bpm.validate(bp, allowed_roots=roots), allowed_roots=roots)
    assert "Errors (1)" in text and "Reply 'approve'" not in text and "tell me what to change" in text


def test_render_plan_code_goal_shows_workspace_and_engineering(tmp_path, roots):
    bp = code_bp(tmp_path)
    text = bpm.render_plan(bp, bpm.validate(bp, allowed_roots=roots), allowed_roots=roots)
    assert str((tmp_path / "proj").resolve()) in text and "pytest" in text and "never push" in text


def test_propose_is_load_validate_render(base, roots):
    text = bpm.propose(yaml.safe_dump(base), allowed_roots=roots)
    assert text == bpm.render_plan(base, bpm.validate(base, allowed_roots=roots), allowed_roots=roots)


def test_issue_render():
    assert Issue("error", "a.b", "fix it").render() == "error: a.b: fix it"


def test_plan_and_manager_charter_say_unspent_budget_returns_automatically(base, roots, empty_org):
    plan = bpm.render_plan(base, org=empty_org, allowed_roots=roots)
    assert "come back automatically" in plan
    bpm.apply(empty_org, base, allowed_roots=roots)
    charter = (empty_org.root / "lead" / "AGENT.md").read_text()
    assert "return to your parent automatically" in charter
    assert "returns to you with its final" in charter  # from the manager template
