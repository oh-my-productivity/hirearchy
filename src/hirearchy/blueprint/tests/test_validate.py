# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

import copy
from pathlib import Path

import pytest
import testkit
import yaml
from testkit.blueprints import code_bp
from testkit.reach.hirearchy.core import ROOT, Org

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
    bp["needs"]["models"] = {"cheap": "claude-sonnet-5.5", "strong": "claude-opus-5.5"}
    bp["needs"]["model_policy"] = "cheap drafting, strong review"
    return bp


@pytest.fixture
def roots(tmp_path):
    return [tmp_path]


@pytest.fixture
def empty_org(tmp_path):
    return Org.init(tmp_path / "org", "bp tests", {"poll_seconds": 0.05})


def codes(issues, level=None):
    return {i.code for i in issues if level is None or i.level == level}


def check(bp, roots, **kw):
    return bpm.validate(bp, allowed_roots=roots, **kw)


def mutate(bp, fn):
    out = copy.deepcopy(bp)
    fn(out)
    return out


def test_example_is_valid_with_one_expected_warning(base, roots):
    issues = check(base, roots)
    assert not bpm.errors(issues)
    assert codes(issues) == {"path-delivery"}


# ----------------------------------------------------------------------------------------- the rules
def test_missing_mission_needs_task_agents(roots):
    issues = check({}, roots)
    assert {"mission", "needs", "task", "agents"} <= codes(issues, "error")


def test_missing_deliverable_is_error(base, roots):
    assert "deliverable" in codes(check(mutate(base, lambda b: b["needs"].pop("deliverable")), roots), "error")


def test_missing_deliverable_format_is_warning(base, roots):
    issues = check(mutate(base, lambda b: b["needs"]["deliverable"].pop("format")), roots)
    assert "deliverable-format" in codes(issues, "warning")


def test_missing_acceptance_criteria_is_error(base, roots):
    assert "criteria" in codes(check(mutate(base, lambda b: b["task"].pop("acceptance")), roots), "error")
    assert "criteria" in codes(check(mutate(base, lambda b: b["task"].update(acceptance=[])), roots), "error")


def test_vague_criterion_is_warning_and_names_the_criterion(base, roots):
    issues = check(mutate(base, lambda b: b["task"]["acceptance"].append("The report is high quality and comprehensive")), roots)
    vague = [i for i in issues if i.code == "vague-criterion"]
    assert [i.level for i in vague] == ["warning"] and "high quality" in vague[0].message


def test_word_limit_must_appear_in_a_criterion(base, roots):
    bp = mutate(base, lambda b: b["task"].update(acceptance=["Covers all five apps with a table", "Cites a URL per claim"]))
    assert "limit-criterion" in codes(check(bp, roots), "warning")


def test_deliverable_path_without_delivery_step_warns(base, roots):
    warn = [i for i in check(base, roots) if i.code == "path-delivery"]
    assert len(warn) == 1 and warn[0].level == "warning" and "copy" in warn[0].message


def test_deliverable_path_written_by_a_workspace_agent_does_not_warn(tmp_path, roots):
    bp = code_bp(tmp_path)
    bp["needs"]["deliverable"]["path"] = str(tmp_path / "proj" / "dist" / "csv2md.tar.gz")
    assert "path-delivery" not in codes(check(bp, roots))


def test_deliverable_path_outside_allowed_roots_is_error(base, roots):
    bp = mutate(base, lambda b: b["needs"]["deliverable"].update(path="/etc/competitors.md"))
    assert "path-root" in codes(check(bp, roots), "error")
    bp = mutate(base, lambda b: b["needs"]["deliverable"].update(path="relative/competitors.md"))
    assert "path" in codes(check(bp, roots), "error")


def test_web_needs_without_web_tools_is_error(base, roots):
    def strip(b):
        for c in b["agents"][0]["children"]:
            c["tools"] = []
        b["agents"][0]["tools"] = []

    assert "web-tools" in codes(check(mutate(base, strip), roots), "error")


def test_web_search_without_fetch_is_warning(base, roots):
    def only_search(b):
        for c in b["agents"][0]["children"]:
            if c["name"] != "writer":
                c["tools"] = ["web_search"]

    issues = check(mutate(base, only_search), roots)
    assert "web-tools-partial" in codes(issues, "warning") and "web-tools" not in codes(issues)


def test_verifier_without_web_access_warns(base, roots):
    def blind_checker(b):
        for c in b["agents"][0]["children"]:
            if c["name"] == "factcheck":
                c["tools"] = []

    assert "verifier-web" in codes(check(mutate(base, blind_checker), roots), "warning")


def test_current_facts_without_web_is_warning(base, roots):
    def offline(b):
        b["needs"].pop("sources")
        b["needs"]["quality_bar"] = "uses the latest published numbers"
        b["task"]["acceptance"] = ["At most 1500 words", "uses the latest prices"]
        b["mission"] = "Summarize the notes"
        b["needs"]["deliverable"]["description"] = "A summary"
        b["task"]["goal"] = "Summarize"
        for c in b["agents"][0]["children"]:
            c["tools"] = []
        b["agents"][0]["tools"] = []

    assert "web-current" in codes(check(mutate(base, offline), roots), "warning")


def test_code_goal_needs_write_shell_and_workspace(tmp_path, roots):
    bp = code_bp(tmp_path)
    assert not bpm.errors(check(bp, roots))
    no_tools = mutate(bp, lambda b: [c.update(tools=["read"]) for c in b["agents"][0]["children"]])
    assert "code-tools" in codes(check(no_tools, roots), "error")
    no_ws = mutate(bp, lambda b: b["needs"].pop("workspace"))
    assert "workspace-confinement" in codes(check(no_ws, roots), "error")


def test_code_goal_needs_tests_packaging_commits_decisions(tmp_path, roots):
    bp = mutate(code_bp(tmp_path), lambda b: (b["needs"].pop("code"), b["task"].update(acceptance=["`csv2md in.csv` prints a table"])))
    w = [i for i in check(bp, roots) if i.level == "warning"]
    assert {"needs.code.tests", "needs.code.packaging", "needs.code.commits"} <= {i.path for i in w}
    assert "code-criteria" in {i.code for i in w}


def test_workspace_checks(tmp_path, roots, empty_org):
    bp = code_bp(tmp_path)
    for bad, code in (("/etc", "path-root"), (str(tmp_path), "path-root"), (str(tmp_path / "missing" / "deep"), "workspace"),
                      ("relative/dir", "path")):
        issues = check(mutate(bp, lambda b, bad=bad: b["needs"].update(workspace=bad)), roots)
        assert code in codes(issues, "error"), bad
    (tmp_path / "afile").write_text("x")
    assert "workspace" in codes(check(mutate(bp, lambda b: b["needs"].update(workspace=str(tmp_path / "afile"))), roots), "error")
    new = check(mutate(bp, lambda b: b["needs"].update(workspace=str(tmp_path / "newproj"))), roots)
    assert "workspace-new" in codes(new, "warning") and not bpm.errors(new)
    # the organization directory and ~/.kiro are never a workspace
    org_ws = check(mutate(bp, lambda b: b["needs"].update(workspace=str(empty_org.root / "ceo"))), roots, org=empty_org)
    assert "path-root" in codes(org_ws, "error")
    kiro = Path.home() / ".kiro" / "x"
    kiro.mkdir(parents=True)
    assert "path-root" in codes(bpm.validate(mutate(bp, lambda b: b["needs"].update(workspace=str(kiro))), allowed_roots=[Path.home()]), "error")


def test_authority_only_narrows(tmp_path, roots):
    bp = code_bp(tmp_path)
    narrow = mutate(bp, lambda b: b["agents"][0].update(tools=["read"]))
    assert "authority" in codes(check(narrow, roots), "error")
    other = tmp_path / "other"
    other.mkdir()
    outside = mutate(bp, lambda b: (b["agents"][0].update(workspace=str(tmp_path / "proj")), b["agents"][0]["children"][0].update(workspace=str(other))))
    assert "authority" in codes(check(outside, roots), "error")
    broad = mutate(bp, lambda b: b["agents"][0]["children"][0].update(workspace=str(other)))  # derived manager workspace would be tmp_path
    assert "path-root" in codes(check(broad, roots), "error")


def test_review_required_without_reviewer_is_error(base, roots):
    def drop(b):
        b["agents"][0]["children"] = [c for c in b["agents"][0]["children"] if c["name"] != "factcheck"]

    issues = check(mutate(base, drop), roots)
    assert "review" in codes(issues, "error")
    assert "review" not in codes(check(mutate(base, lambda b: (drop(b), b["needs"].update(review=False))), roots), "error")
    undecided = check(mutate(base, lambda b: (drop(b), b["needs"].pop("review"))), roots)
    assert "review" in codes(undecided, "warning") and "review" not in codes(undecided, "error")


def test_review_without_author_is_error(base, roots):
    def only_reviewer(b):
        b["agents"][0]["children"] = [c for c in b["agents"][0]["children"] if c["name"] == "factcheck"]

    assert "review" in codes(check(mutate(base, only_reviewer), roots), "error")


@pytest.mark.parametrize("text", [
    "Apply corrections directly to the report file and note what changed.",
    "Document corrections and apply them to the report.",
    "Fix the draft in place.",
    "Edit the writer's report to correct errors.",
])
def test_reviewer_told_to_edit_others_files_is_error(base, roots, text):
    def custom(b):
        b["agents"][0]["children"][2] = {"name": "factcheck", "role": "Fact-checker", "kind": "verifier",
                                         "tools": ["web_search", "web_fetch"], "charter": f"Verify claims. {text}"}

    issues = check(mutate(base, custom), roots)
    assert "edits-others" in codes(issues, "error"), text


def test_negated_edit_rules_and_shipped_reviewers_are_fine(base, roots):
    def custom(b):
        b["agents"][0]["children"][2]["charter"] = "You never edit the report; write findings in your own work/ directory."

    assert "edits-others" not in codes(check(mutate(base, custom), roots))
    for name in bpm.role_names():
        assert bpm.edits_others_files(bpm.get_role(name).body) is None, name


def test_criterion_asking_reviewer_to_edit_is_error(base, roots):
    bp = mutate(base, lambda b: b["task"]["acceptance"].append("Corrections applied directly in lead/writer/work/report.md by the reviewer"))
    assert "edits-others" in codes(check(bp, roots), "error")
    ok = mutate(base, lambda b: b["task"]["acceptance"].append("The writer applies every required change to the report"))
    assert "edits-others" not in codes(check(ok, roots))


def test_single_model_with_tiered_policy_is_error(base, roots):
    def one_model(b):
        tiered(b)
        b["needs"].pop("models")
        for a in (b["agents"][0], *b["agents"][0]["children"]):
            a["model"] = "claude-opus-5.5"

    assert "model-single" in codes(check(mutate(base, one_model), roots), "error")
    assert "model-single" not in codes(check(tiered(copy.deepcopy(base)), roots))
    same_review = mutate(tiered(copy.deepcopy(base)), lambda b: b["agents"][0]["children"][2].update(model="claude-sonnet-5.5"))
    assert "model-review" in codes(check(same_review, roots), "warning")


def test_depth_and_children_limits(roots, empty_org, base):
    deep = {"name": "a", "template": "manager", "children": [{"name": "b", "template": "manager", "children": [
        {"name": "c", "template": "manager", "children": [{"name": "d", "template": "manager", "children": [{"name": "e", "template": "writer"}]}]}]}]}
    assert "depth" in codes(check(mutate(base, lambda b: b.update(agents=[deep])), roots, org=empty_org), "error")
    many = mutate(base, lambda b: b["agents"][0].update(max_children=2))
    assert "children" in codes(check(many, roots), "error")
    no_hire = mutate(base, lambda b: b["agents"][0].update(can_hire=False))
    assert "children" in codes(check(no_hire, roots), "error")


@pytest.mark.parametrize("name", ["Lead", "1lead", "has space", "a" * 33, "root", "work", "inbox", ""])
def test_invalid_names(base, roots, name):
    bp = mutate(base, lambda b: b["agents"][0]["children"][1].update(name=name))
    assert "name" in codes(check(bp, roots), "error")


def test_duplicate_unknown_template_and_missing_charter(base, roots):
    dup = mutate(base, lambda b: b["agents"][0]["children"][1].update(name="researcher"))
    assert "name" in codes(check(dup, roots), "error")
    assert "template" in codes(check(mutate(base, lambda b: b["agents"][0]["children"][1].update(template="wizard")), roots), "error")
    bare = mutate(base, lambda b: b["agents"][0]["children"][1].pop("template"))
    assert "template" in codes(check(bare, roots), "error")


def test_unknown_keys_warn(base, roots):
    bp = mutate(base, lambda b: b["needs"].update(budget_run=3))
    assert "unknown-key" in codes(check(bp, roots), "warning")


def test_existing_name_and_multiple_tops(base, roots, empty_org):
    empty_org.hire(ROOT, "lead", "someone", "x")
    assert "exists" in codes(check(base, roots, org=empty_org), "error")
    two = mutate(base, lambda b: b["agents"].append({"name": "other", "template": "writer"}))
    assert "agents" in codes(check(two, roots), "error")
    bad_to = mutate(base, lambda b: b["task"].update(to="nobody"))
    assert "task" in codes(check(bad_to, roots), "error")


def test_unelicited_preferences_warn(base, roots):
    bp = mutate(base, lambda b: [b["needs"].pop(k) for k in ("scope", "approval", "progress")])
    assert {"needs-scope", "needs-approval", "needs-progress"} <= codes(check(bp, roots), "warning")
