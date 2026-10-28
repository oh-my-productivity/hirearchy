# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

import copy

import pytest
import testkit
import yaml
from testkit.blueprints import code_bp
from testkit.reach.hirearchy.app import wiring
from testkit.reach.hirearchy.core import ROOT, Org, OrgError

from testkit.blueprint_world import bpm
from hirearchy.blueprint import BlueprintError
from hirearchy.blueprint.testing import FlakyHiring, FlakyTaskAssigner
from hirearchy.dispatch import TaskAssigner
from hirearchy.hierarchy import Hiring

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


def apply_through(org, overrides):
    """``org`` applied through other ports (the tests make one step fail this way): its runtime is opened again with the ports in ``overrides``."""
    org.runtime = wiring.open_runtime(org.root, overrides)


def mutate(bp, fn):
    out = copy.deepcopy(bp)
    fn(out)
    return out


# ------------------------------------------------------------------------------------------- apply
def test_apply_creates_tree_charters_and_task(base, roots, empty_org):
    base = tiered(base)
    s = bpm.apply(empty_org, base, allowed_roots=roots)
    assert s.agents == ["lead", "lead/researcher", "lead/writer", "lead/factcheck"] and s.to == "lead" and s.budget == 22
    assert empty_org.agents() == ["lead", "lead/factcheck", "lead/researcher", "lead/writer"]
    meta, body = empty_org.charter("lead")
    assert meta["model"] == "claude-opus-5.5" and meta["can_hire"] and meta["max_children"] == 3
    assert meta["tools"] == ["web_fetch", "web_search"] and meta["role"] == "Research lead"
    assert "Budget plan: you start with 22 runs" in body and "lead/researcher 4, lead/writer 3, lead/factcheck 3" in body and "You keep 12 runs" in body
    assert "Review loop:" in body and "Never hand down more than the budget plan says" in body
    rmeta, rbody = empty_org.charter("lead/researcher")
    assert rmeta["model"] == "claude-sonnet-5.5" and "Cite" not in rbody and "primary-source URL" in rbody
    assert "Reports to: lead" in rbody
    _, fbody = empty_org.charter("lead/factcheck")
    assert "You never edit the deliverable" in fbody and empty_org.charter("lead/factcheck")[0]["model"] == "claude-opus-5.5"
    task = empty_org.find_received("lead", s.task_id)
    assert task.budget == 22 and task.sender == ROOT and task.title.startswith("Competitor analysis")
    assert "1. Covers exactly Obsidian" in task.body and "7. The final report names the path" in task.body
    assert "at most 1500 words" in task.body and "Report its path as an artifact" in task.body
    assert empty_org.budget("lead") == 22


class SpyHiring(Hiring):
    """Forwards to the real hiring and keeps the keywords of every hire."""

    def __init__(self, inner):
        self._inner = inner
        self.seen = []

    def hire(self, actor, name, role, charter, **kw):
        self.seen.append((actor, name, kw))
        return self._inner.hire(actor, name, role, charter, **kw)


def test_apply_hires_with_approved_so_a_planned_sub_lead_gets_can_hire(base, roots, empty_org):
    def nest(bp):
        sub = {"name": "sub", "template": "manager", "role": "Research sub-lead",
               "children": [{"name": "a", "template": "researcher"}, {"name": "b", "template": "researcher"},
                            {"name": "c", "template": "researcher"}]}
        bp["agents"][0]["children"].append(sub)
        bp["needs"]["budget_runs"] = 80

    bp = mutate(base, nest)
    assert not bpm.errors(bpm.validate(bp, allowed_roots=roots)), bpm.validate(bp, allowed_roots=roots)
    spy = SpyHiring(empty_org.runtime.hiring)
    apply_through(empty_org, {Hiring: spy})
    bpm.apply(empty_org, bp, allowed_roots=roots)
    assert len(spy.seen) == 8 and all(kw.get("approved") is True for _, _, kw in spy.seen)  # every hire of an applied plan
    lead, _ = empty_org.charter("lead")
    sub, _ = empty_org.charter("lead/sub")
    # the sub-lead was hired by the lead, who is not root: only the approved plan could give it the right to hire and more children than the lead has
    assert lead["max_children"] == 4 and sub["can_hire"] is True and sub["max_children"] == 3
    assert empty_org.charter("lead/sub/a")[0]["can_hire"] is False and empty_org.charter("lead/sub/a")[0]["max_children"] == 0


def test_every_agent_of_an_applied_plan_has_its_kind_and_approved_in_plan_id(base, roots, empty_org):
    plan_id = bpm.plan_id(base)  # the id propose_org returns for it
    bpm.apply(empty_org, base, allowed_roots=roots)
    kinds = {}
    for addr in empty_org.agents():
        meta, _ = empty_org.charter(addr)
        assert meta["approved_in"] == f"plan {plan_id}", addr
        kinds[addr] = meta["kind"]
    assert kinds == {"lead": "manager", "lead/researcher": "author", "lead/writer": "author", "lead/factcheck": "verifier"}


def test_apply_budget_plan_is_executable_by_the_manager(base, roots, empty_org):
    s = bpm.apply(empty_org, base, allowed_roots=roots)
    for name, n in (("researcher", 3), ("writer", 2), ("factcheck", 2)):
        empty_org.delegate("lead", f"lead/{name}", "t", "g", "a", budget=n)
    assert empty_org.budget("lead") == 22 - 7 and empty_org.budget("lead/writer") == 2
    empty_org.delegate("lead", "lead/writer", "rework", "g", "a", budget=1, revises=empty_org.sent("lead")[1].id)  # rework still affordable
    assert s.budget == 22


def test_apply_code_blueprint_sets_workspace_and_tools(tmp_path, roots, empty_org):
    bpm.apply(empty_org, code_bp(tmp_path), allowed_roots=roots)
    ws = str((tmp_path / "proj").resolve())
    for a in ("lead", "lead/dev", "lead/qa"):
        assert empty_org.charter(a)[0]["workspace"] == ws, a
    meta, body = empty_org.charter("lead/dev")
    assert meta["tools"] == ["read", "shell", "write"] and "Never `git push`" in body and "Engineering rules: tests: pytest" in body
    cr_meta, _ = empty_org.charter("lead/cr")
    assert cr_meta["tools"] == ["read", "shell"] and cr_meta["workspace"] == ws  # shell, so confined like the engineer


def test_apply_extra_charter_text_is_appended(base, roots, empty_org):
    base["agents"][0]["children"][0]["charter"] = "Cover pricing pages last."
    bpm.apply(empty_org, base, allowed_roots=roots)
    body = empty_org.charter("lead/researcher")[1]
    assert body.rstrip().endswith("Cover pricing pages last.") and "## Additional instructions" in body


def test_apply_custom_charter_without_template(base, roots, empty_org):
    base["agents"][0]["children"][1] = {"name": "writer", "role": "Poet", "charter": "Write haiku only.", "tools": []}
    bpm.apply(empty_org, base, allowed_roots=roots)
    meta, body = empty_org.charter("lead/writer")
    assert meta["role"] == "Poet" and "Write haiku only." in body


def test_apply_refuses_errors_and_creates_nothing(base, roots, empty_org):
    bad = mutate(base, lambda b: b["task"].pop("acceptance"))
    with pytest.raises(BlueprintError, match="task.acceptance"):
        bpm.apply(empty_org, bad, allowed_roots=roots)
    assert empty_org.agents() == [] and not (empty_org.root / "lead").exists() and not (empty_org.root / ".retired").exists()


def test_apply_refuses_a_plan_below_the_model_floor_and_creates_nobody(base, roots, empty_org):
    base["needs"]["models"] = {"cheap": "claude-haiku-4.5", "strong": "claude-sonnet-4.6"}
    with pytest.raises(BlueprintError, match=r'needs.models.cheap: model "claude-haiku-4.5" is not allowed for org agents; allowed: claude-sonnet-5.5, claude-opus-5.5'):
        bpm.apply(empty_org, base, allowed_roots=roots)
    assert empty_org.agents() == [] and not (empty_org.root / "lead").exists()


def test_apply_refuses_existing_names(base, roots, empty_org):
    empty_org.hire(ROOT, "lead", "someone", "x")
    before = sorted(p.name for p in empty_org.root.iterdir())
    with pytest.raises(BlueprintError, match="already exists"):
        bpm.apply(empty_org, base, allowed_roots=roots)
    assert sorted(p.name for p in empty_org.root.iterdir()) == before
    with pytest.raises(BlueprintError):
        bpm.apply(Org.init(roots[0] / "org2"), mutate(base, lambda b: b["needs"].pop("deliverable")), allowed_roots=roots)


def test_apply_twice_is_refused(base, roots, empty_org):
    bpm.apply(empty_org, base, allowed_roots=roots)
    with pytest.raises(BlueprintError, match="already exists"):
        bpm.apply(empty_org, base, allowed_roots=roots)


@pytest.mark.parametrize("fail_on", [1, 3, 4])
def test_apply_midway_hire_failure_leaves_no_agents(base, roots, empty_org, fail_on):
    apply_through(empty_org, {Hiring: FlakyHiring(empty_org.runtime.hiring, fail_on=fail_on)})
    with pytest.raises(OrgError, match="disk full"):
        bpm.apply(empty_org, base, allowed_roots=roots)
    assert empty_org.agents() == [] and empty_org.messages(ROOT, "inbox") == []
    assert not any(empty_org.exists(a) for a in ("lead", "lead/writer"))


def test_apply_delegate_failure_rolls_back(base, roots, empty_org):
    apply_through(empty_org, {TaskAssigner: FlakyTaskAssigner(empty_org.runtime.task_assigner)})
    with pytest.raises(OrgError, match="delegate failed"):
        bpm.apply(empty_org, base, allowed_roots=roots)
    assert empty_org.agents() == []


def test_apply_creates_missing_workspace_and_removes_it_on_failure(tmp_path, roots, empty_org):
    bp = code_bp(tmp_path)
    bp["needs"]["workspace"] = str(tmp_path / "fresh")
    bpm.apply(empty_org, bp, allowed_roots=roots)
    assert (tmp_path / "fresh").is_dir()

    org2 = Org.init(tmp_path / "org2")
    bp["needs"]["workspace"] = str(tmp_path / "fresh2")
    apply_through(org2, {TaskAssigner: FlakyTaskAssigner(org2.runtime.task_assigner, error="nope")})
    with pytest.raises(OrgError):
        bpm.apply(org2, bp, allowed_roots=roots)
    assert not (tmp_path / "fresh2").exists() and org2.agents() == []


def test_apply_commits(base, roots, empty_org):
    import subprocess
    bpm.apply(empty_org, base, allowed_roots=roots)
    log = subprocess.run(["git", "log", "--oneline"], cwd=empty_org.root, capture_output=True, text=True).stdout
    assert "applied blueprint (4 agents)" in log


# ------------------------------------------------------------------------------------------ roles
def test_role_library():
    assert {"manager", "researcher", "writer", "reviewer", "fact-checker", "engineer", "tester", "code-reviewer"} <= set(bpm.role_names())
    for name in bpm.role_names():
        r = bpm.get_role(name)
        assert r.kind in bpm.KINDS and r.tier in ("cheap", "strong") and r.summary
        for section in ("## Purpose", "## Responsibilities", "## Decision rights", "## Escalation", "## Quality bar", "## Budget"):
            assert section in r.body, (name, section)
    assert set(bpm.get_role("researcher").tools) == {"web_search", "web_fetch"}
    assert {"write", "shell"} <= set(bpm.get_role("engineer").tools)
    assert bpm.get_role("manager").tier == "strong" and bpm.get_role("writer").tier == "cheap"
    assert "keep" in bpm.get_role("manager").body.lower() and "one review and one rework" in bpm.get_role("manager").body
    assert bpm.get_role("nope") is None and bpm.get_role("../x") is None


@pytest.mark.parametrize("name", ["reviewer", "fact-checker", "code-reviewer", "tester"])
def test_verifier_templates_never_edit_others_files(name):
    body = bpm.get_role(name).body
    assert "never edit" in body.lower() and "own" in body.lower()


def test_skill_frontmatter_is_well_formed_and_the_skill_stays_short():
    text = (testkit.REPO / "skills" / "hirearchy" / "SKILL.md").read_text()
    meta = yaml.safe_load(text.split("---")[1])
    assert meta["name"] == "hirearchy" and meta["description"]
    assert len(text.splitlines()) <= 125  # the example blueprints live in the blueprint_example tool (tests/test_assistant_ux.py)
