# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

import copy
from pathlib import Path

import pytest
import testkit
import yaml
from testkit.blueprint_world import ex
from testkit.reach.hirearchy.core import DEFAULT_MODEL, Org
from testkit.blueprint_world import kiro_runner

from testkit.blueprint_world import bpm

EXAMPLES = testkit.REPO / "examples"


def model_arg(cmd: list[str]) -> str:
    assert cmd.count("--model") == 1
    return cmd[cmd.index("--model") + 1]


# ------------------------------------------------------------------------------------------ blueprints
@pytest.fixture
def research(tmp_path):
    (tmp_path / "deliverables").mkdir(exist_ok=True)
    bp = yaml.safe_load((EXAMPLES / "blueprint-research.yaml").read_text())
    bp["needs"]["deliverable"]["path"] = str(tmp_path / "deliverables" / "competitors.md")
    return bp


def tiered(bp):
    bp["needs"]["models"] = {"cheap": "claude-haiku-4.5", "strong": "claude-sonnet-4.6"}
    bp["needs"]["model_policy"] = "cheap drafting, strong review"
    return bp


def codes(found, level=None):
    return {i.code for i in found if level is None or i.level == level}


def models_of(bp, tmp_path, org=None):
    return {a.addr: a.model for a in bpm._resolve(bp, org, [tmp_path], [])}


def test_without_needs_models_every_tier_is_the_default(research, tmp_path):
    for drop in (lambda b: b["needs"].pop("models"), lambda b: b["needs"].update(models={}),
                 lambda b: b["needs"].update(models={"cheap": "claude-sonnet-5.5"})):
        bp = copy.deepcopy(research)
        drop(bp)
        assert set(models_of(bp, tmp_path).values()) == {DEFAULT_MODEL}


def test_a_tier_missing_from_needs_models_uses_the_orgs_default_model(research, tmp_path):
    org = Org.init(tmp_path / "org", "m", {"default_model": "claude-opus-5.5"})
    research["needs"].pop("models")
    assert set(models_of(research, tmp_path, org).values()) == {"claude-opus-5.5"}
    research["needs"]["models"] = {"cheap": "claude-sonnet-5.5"}  # strong is not mapped: the org default
    got = models_of(research, tmp_path, org)
    assert got["lead"] == "claude-opus-5.5" and got["lead/writer"] == "claude-sonnet-5.5"


def test_the_default_policy_is_single_model_and_raises_no_warning(research, tmp_path):
    found = bpm.validate(research, allowed_roots=[tmp_path])
    assert not bpm.errors(found)
    assert codes(found) <= {"path-delivery"}  # only the delivery note of the example; nothing about models
    unmapped = copy.deepcopy(research)
    unmapped["needs"].pop("models")
    unmapped["needs"].pop("model_policy")
    assert not codes(bpm.validate(unmapped, allowed_roots=[tmp_path])) - {"path-delivery"}
    assert set(models_of(research, tmp_path).values()) == {DEFAULT_MODEL}


def test_the_plan_says_plainly_that_every_agent_runs_on_the_default(research, tmp_path):
    plan = bpm.plan_for_user(research, allowed_roots=[tmp_path])
    assert "- Models: claude-sonnet-5.5 for every agent" in plan.splitlines()
    assert "lead (Research lead, model claude-sonnet-5.5)" in plan and "haiku" not in plan and "sonnet-4" not in plan
    assert "model=claude-sonnet-5.5" in bpm.render_plan(research, allowed_roots=[tmp_path])


def test_tiering_on_request_resolves_each_tier_and_the_plan_names_them(research, tmp_path):
    bp = tiered(research)
    assert models_of(bp, tmp_path) == {"lead": "claude-sonnet-4.6", "lead/researcher": "claude-haiku-4.5",
                                       "lead/writer": "claude-haiku-4.5", "lead/factcheck": "claude-sonnet-4.6"}
    plan = bpm.plan_for_user(bp, allowed_roots=[tmp_path])
    assert "- Models: claude-sonnet-4.6 for 2 agents, claude-haiku-4.5 for 2 agents (cheap drafting, strong review)" in plan.splitlines()
    assert "for every agent" not in plan


def test_tiering_still_warns_when_the_lead_is_cheap_and_never_when_the_tiers_are_equal(research, tmp_path):
    cheap_lead = tiered(research)
    cheap_lead["agents"][0]["model"] = "cheap"
    assert "manager-cheap-model" in codes(bpm.validate(cheap_lead, allowed_roots=[tmp_path]), "warning")
    equal = copy.deepcopy(cheap_lead)
    equal["needs"]["models"] = {"cheap": "claude-sonnet-5.5", "strong": "claude-sonnet-5.5"}
    equal["needs"]["model_policy"] = "one model for all"
    assert not codes(bpm.validate(equal, allowed_roots=[tmp_path])) & {"manager-cheap-model", "model-policy", "model-single"}


def test_a_tiered_policy_without_two_models_is_still_an_error(research, tmp_path):
    research["needs"]["model_policy"] = "cheap drafting, strong review"
    assert "model-single" in codes(bpm.validate(research, allowed_roots=[tmp_path]), "error")


def test_apply_pins_the_resolved_model_in_the_charters(research, tmp_path):
    org = Org.init(tmp_path / "org", "m", {"poll_seconds": 0.05})
    bpm.apply(org, research, allowed_roots=[tmp_path])
    assert {a: org.model_for(a) for a in org.agents()} == {a: DEFAULT_MODEL for a in org.agents()}
    assert model_arg(kiro_runner()(org, "lead", "P")[0]) == DEFAULT_MODEL


# ------------------------------------------------------------------------------------------ templates and examples
def fill(text: str, base: Path) -> str:
    for n in ("docs", "data", "proj", "deliverables"):
        (base / n).mkdir(exist_ok=True)
    return (text.replace("<folder-with-your-files>", "docs").replace("<folder-with-your-data>", "data")
            .replace("<project-folder>", "proj").replace("<name>", "briefs").replace("<service-name>", "my-service")
            .replace("<input-name>", "topic"))


@pytest.mark.parametrize("service", [False, True])
@pytest.mark.parametrize("kind", ex.KINDS)
def test_every_template_defaults_to_the_default_model_and_validates(kind, service, tmp_path):
    text = ex.example(kind, tmp_path, service=service)
    assert "haiku" not in text and "sonnet-4" not in text
    bp = bpm.load_text(fill(text, tmp_path))
    assert bp["needs"]["models"] == {"cheap": DEFAULT_MODEL, "strong": DEFAULT_MODEL}
    assert not bpm.errors(bpm.validate(bp, allowed_roots=[tmp_path]))
    assert set(models_of(bp, tmp_path).values()) == {DEFAULT_MODEL}
    assert "claude-sonnet-5.5 for every agent" in bpm.plan_for_user(bp, allowed_roots=[tmp_path])
    assert not codes(bpm.validate(bp, allowed_roots=[tmp_path])) & {"model-policy", "model-single", "manager-cheap-model", "model-review"}


@pytest.mark.parametrize("name", sorted(p.name for p in EXAMPLES.glob("*.yaml")))
def test_shipped_example_blueprints_default_to_the_default_model(name, tmp_path):
    raw = (EXAMPLES / name).read_text()
    assert "haiku" not in raw and "sonnet-4" not in raw
    bp = yaml.safe_load(raw)
    if "models" in bp.get("needs", {}):
        assert bp["needs"]["models"] == {"cheap": DEFAULT_MODEL, "strong": DEFAULT_MODEL}
