import copy
import json
from pathlib import Path

import pytest
import yaml

from orgmcp import blueprint as bpm
from orgmcp.blueprint import BlueprintError, Issue
from orgmcp.cli import main
from orgmcp.core import ROOT, Org, OrgError

EXAMPLE = Path(__file__).resolve().parent.parent / "examples" / "blueprint-research.yaml"


@pytest.fixture
def base(tmp_path):
    """tmp_path as the only allowed root; the example research blueprint with its deliverable inside it."""
    (tmp_path / "deliverables").mkdir()
    bp = yaml.safe_load(EXAMPLE.read_text())
    bp["needs"]["deliverable"]["path"] = str(tmp_path / "deliverables" / "competitors.md")
    return bp


@pytest.fixture
def roots(tmp_path):
    return [tmp_path]


@pytest.fixture
def empty_org(tmp_path):
    return Org.init(tmp_path / "org", "bp tests", {"poll_seconds": 0.05})


def code_bp(tmp_path):
    ws = tmp_path / "proj"
    ws.mkdir(exist_ok=True)
    return {
        "mission": "Build a small CLI that converts CSV to markdown tables.",
        "needs": {
            "scope": "csv2md CLI only; no web UI",
            "deliverable": {"description": "A Python package csv2md with a CLI", "format": "python package"},
            "quality_bar": "tests pass from a clean checkout",
            "workspace": str(ws),
            "budget_runs": 30,
            "model_policy": "one model for all",
            "review": True,
            "approval": "approve plan first",
            "progress": "one line on request",
            "code": {"tests": "pytest, one per criterion", "packaging": "uv + pyproject", "commits": "local commits, never push"},
        },
        "agents": [{
            "name": "lead", "template": "manager",
            "children": [{"name": "dev", "template": "engineer"}, {"name": "qa", "template": "tester"},
                         {"name": "cr", "template": "code-reviewer"}],
        }],
        "task": {
            "title": "Build csv2md",
            "goal": "Implement the csv2md CLI in the workspace",
            "acceptance": ["`uv run pytest -q` passes with at least 5 tests", "`csv2md in.csv` prints a markdown table to stdout",
                           "the work is committed locally and nothing is pushed"],
        },
    }


def codes(issues, level=None):
    return {i.code for i in issues if level is None or i.level == level}


def check(bp, roots, **kw):
    return bpm.validate(bp, allowed_roots=roots, **kw)


def mutate(bp, fn):
    out = copy.deepcopy(bp)
    fn(out)
    return out


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


def test_manager_tools_and_workspace_default_to_what_it_must_grant(tmp_path, roots):
    agents = bpm._resolve(code_bp(tmp_path), None, roots, [])
    lead = next(a for a in agents if a.name == "lead")
    assert {"read", "write", "shell"} <= set(lead.tools) and lead.workspace == str((tmp_path / "proj").resolve())
    assert lead.can_hire and lead.max_children == 3


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


def test_planned_budget_has_slack_and_respects_cap(base, roots):
    assert bpm.planned_total(base, 17) == 22  # ceil(17 * 1.25), under the cap of 25
    assert bpm.planned_total(mutate(base, lambda b: b["needs"].update(budget_runs=18)), 17) == 18
    assert bpm.planned_total(mutate(base, lambda b: b["task"].update(budget=19)), 17) == 19


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


def test_single_model_with_tiered_policy_is_error(base, roots):
    def one_model(b):
        b["needs"].pop("models")
        for a in (b["agents"][0], *b["agents"][0]["children"]):
            a["model"] = "claude-sonnet-4.6"

    assert "model-single" in codes(check(mutate(base, one_model), roots), "error")
    assert "model-single" not in codes(check(base, roots))
    same_review = mutate(base, lambda b: b["agents"][0]["children"][2].update(model="claude-haiku-4.5"))
    assert "model-review" in codes(check(same_review, roots), "warning")


def test_tier_without_mapping_is_error_and_no_policy_warns(base, roots):
    assert "model-tier" in codes(check(mutate(base, lambda b: b["needs"].pop("models")), roots), "error")
    assert "model-policy" in codes(check(mutate(base, lambda b: b["needs"].pop("model_policy")), roots), "warning")
    single = mutate(base, lambda b: (b["needs"].update(model_policy="one model for everyone"), b["needs"].pop("models"),
                                     [a.pop("model", None) for a in (b["agents"][0], *b["agents"][0]["children"])]))
    assert not bpm.errors(check(single, roots))


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


# ------------------------------------------------------------------------------------------ the plan


def test_render_plan_contents(base, roots):
    text = bpm.render_plan(base, bpm.validate(base, allowed_roots=roots), allowed_roots=roots)
    for expected in ("Goal:", "Obsidian, Logseq, Joplin", "max 1500 words", "lead/researcher", "model=claude-haiku-4.5",
                     "model=claude-sonnet-4.6", "tools=web_fetch,web_search", "Budget: 22 runs planned (your cap: 25), estimate 17",
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


# ------------------------------------------------------------------------------------------- apply


def test_apply_creates_tree_charters_and_task(base, roots, empty_org):
    s = bpm.apply(empty_org, base, allowed_roots=roots)
    assert s.agents == ["lead", "lead/researcher", "lead/writer", "lead/factcheck"] and s.to == "lead" and s.budget == 22
    assert empty_org.agents() == ["lead", "lead/factcheck", "lead/researcher", "lead/writer"]
    meta, body = empty_org.charter("lead")
    assert meta["model"] == "claude-sonnet-4.6" and meta["can_hire"] and meta["max_children"] == 3
    assert meta["tools"] == ["web_fetch", "web_search"] and meta["role"] == "Research lead"
    assert "Budget plan: you start with 22 runs" in body and "lead/researcher 4, lead/writer 3, lead/factcheck 3" in body and "You keep 12 runs" in body
    assert "Review loop:" in body and "Never hand down more than the budget plan says" in body
    rmeta, rbody = empty_org.charter("lead/researcher")
    assert rmeta["model"] == "claude-haiku-4.5" and "Cite" not in rbody and "primary-source URL" in rbody
    assert "Reports to: lead" in rbody
    _, fbody = empty_org.charter("lead/factcheck")
    assert "You never edit the deliverable" in fbody and empty_org.charter("lead/factcheck")[0]["model"] == "claude-sonnet-4.6"
    task = empty_org.find_received("lead", s.task_id)
    assert task.budget == 22 and task.sender == ROOT and task.title.startswith("Competitor analysis")
    assert "1. Covers exactly Obsidian" in task.body and "7. The final report names the path" in task.body
    assert "at most 1500 words" in task.body and "Report its path as an artifact" in task.body
    assert empty_org.budget("lead") == 22


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
def test_apply_midway_hire_failure_leaves_no_agents(base, roots, empty_org, monkeypatch, fail_on):
    real, calls = Org.hire, []

    def flaky(self, *a, **kw):
        calls.append(a)
        if len(calls) == fail_on:
            raise OrgError("disk full")
        return real(self, *a, **kw)

    monkeypatch.setattr(Org, "hire", flaky)
    with pytest.raises(OrgError, match="disk full"):
        bpm.apply(empty_org, base, allowed_roots=roots)
    assert empty_org.agents() == [] and empty_org.messages(ROOT, "inbox") == []
    assert not any(empty_org.exists(a) for a in ("lead", "lead/writer"))


def test_apply_delegate_failure_rolls_back(base, roots, empty_org, monkeypatch):
    def boom(self, *a, **kw):
        raise OrgError("delegate failed")

    monkeypatch.setattr(Org, "delegate", boom)
    with pytest.raises(OrgError, match="delegate failed"):
        bpm.apply(empty_org, base, allowed_roots=roots)
    assert empty_org.agents() == []


def test_apply_creates_missing_workspace_and_removes_it_on_failure(tmp_path, roots, empty_org, monkeypatch):
    bp = code_bp(tmp_path)
    bp["needs"]["workspace"] = str(tmp_path / "fresh")
    bpm.apply(empty_org, bp, allowed_roots=roots)
    assert (tmp_path / "fresh").is_dir()

    org2 = Org.init(tmp_path / "org2")
    bp["needs"]["workspace"] = str(tmp_path / "fresh2")
    monkeypatch.setattr(Org, "delegate", lambda self, *a, **k: (_ for _ in ()).throw(OrgError("nope")))
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


# --------------------------------------------------------------------------------------------- CLI


def write_bp(tmp_path, bp, name="bp.yaml"):
    p = tmp_path / name
    p.write_text(yaml.safe_dump(bp, sort_keys=False))
    return str(p)


def test_cli_plan_ok_and_errors(base, tmp_path, empty_org, capsys):
    good = write_bp(tmp_path, base)
    main(["--root", str(empty_org.root), "plan", good, "--allow-root", str(tmp_path)])
    out = capsys.readouterr().out
    assert "Plan for approval" in out and "Reply 'approve'" in out
    bad = write_bp(tmp_path, mutate(base, lambda b: b["task"].pop("acceptance")), "bad.yaml")
    with pytest.raises(SystemExit) as e:
        main(["--root", str(empty_org.root), "plan", bad, "--allow-root", str(tmp_path)])
    assert e.value.code == 1
    assert "Errors (1)" in capsys.readouterr().out
    assert empty_org.agents() == []


def test_cli_plan_works_without_an_org(base, tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("ORG_ROOT", raising=False)
    main(["plan", write_bp(tmp_path, base), "--allow-root", str(tmp_path)])
    assert "Plan for approval" in capsys.readouterr().out


def test_cli_apply(base, tmp_path, empty_org, capsys):
    path = write_bp(tmp_path, base)
    main(["--root", str(empty_org.root), "apply", path, "--allow-root", str(tmp_path)])
    cap = capsys.readouterr()
    assert f"org: {empty_org.root}" in cap.err  # announced on stderr before anything is changed
    assert "created 4 agents" in cap.out and "-> lead (budget 22)" in cap.out
    assert empty_org.exists("lead/factcheck")
    with pytest.raises(SystemExit) as e:  # second apply: names exist
        main(["--root", str(empty_org.root), "apply", path, "--allow-root", str(tmp_path)])
    assert e.value.code == 1
    assert "already exists" in capsys.readouterr().err


def test_cli_apply_error_exit(base, tmp_path, empty_org, capsys):
    bad = write_bp(tmp_path, mutate(base, lambda b: b["needs"].pop("deliverable")), "bad.yaml")
    with pytest.raises(SystemExit) as e:
        main(["--root", str(empty_org.root), "apply", bad, "--allow-root", str(tmp_path)])
    assert e.value.code == 1 and "nothing was created" in capsys.readouterr().err
    assert empty_org.agents() == []


def test_issue_render():
    assert Issue("error", "a.b", "fix it").render() == "error: a.b: fix it"


def test_skill_frontmatter_is_well_formed_and_the_skill_stays_short():
    text = (Path(__file__).resolve().parent.parent / "skills" / "orgmcp" / "SKILL.md").read_text()
    meta = yaml.safe_load(text.split("---")[1])
    assert meta["name"] == "orgmcp" and meta["description"]
    assert len(text.splitlines()) <= 125  # the example blueprints live in the blueprint_example tool (tests/test_assistant_ux.py)


def test_plan_and_manager_charter_say_unspent_budget_returns_automatically(base, roots, empty_org):
    plan = bpm.render_plan(base, org=empty_org, allowed_roots=roots)
    assert "come back automatically" in plan
    bpm.apply(empty_org, base, allowed_roots=roots)
    charter = (empty_org.root / "lead" / "AGENT.md").read_text()
    assert "return to your parent automatically" in charter
    assert "returns to you with its final" in charter  # from the manager template
