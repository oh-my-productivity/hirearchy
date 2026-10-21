# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

from pathlib import Path

import pytest
import testkit
import yaml
from testkit.blueprint_world import ex
from testkit.reach.hirearchy.core import Org, OrgError

from testkit.blueprint_world import bpm

EXAMPLE_YAML = testkit.REPO / "examples" / "blueprint-research.yaml"


def filled(kind: str, base: Path) -> dict:
    for name in ("docs", "data", "proj", "deliverables"):
        (base / name).mkdir(exist_ok=True)
    text = ex.example(kind, base)
    text = (text.replace("<folder-with-your-files>", "docs").replace("<folder-with-your-data>", "data")
            .replace("<project-folder>", "proj").replace("<name>", "result"))
    return yaml.safe_load(text)


@pytest.fixture
def cwd(tmp_path, monkeypatch):
    monkeypatch.setenv("HIREARCHY_WORKSPACE_ROOTS", str(tmp_path))
    work = tmp_path / "cwd"
    work.mkdir()
    monkeypatch.chdir(work)
    return work


def codes(issues) -> set[str]:
    return {i.code for i in issues}


# ----------------------------------------------------------------------------------- research criteria
@pytest.fixture(params=["example-tool", "example-yaml"])
def research_criteria(request, cwd):
    if request.param == "example-tool":
        return filled("research", cwd)["task"]["acceptance"]
    return yaml.safe_load(EXAMPLE_YAML.read_text())["task"]["acceptance"]


def test_research_criteria_separate_facts_from_judgement(research_criteria):
    text = " ".join(research_criteria)
    for needle in ("number, name, version, license, price, date", "cites the URL of the page that states it",
                   "quoted the sentence", "judgement", "no citations or new facts", "rests only on claims verified"):
        assert needle in text, needle


def test_research_coverage_criterion_counts_factual_claims_only_and_matches_the_checkers_line(research_criteria):
    coverage = next(c for c in research_criteria if "coverage line" in c)
    assert "n of m factual claims verified' with n = m" in coverage and "each resting on verified facts: yes" in coverage
    assert "none wrong, unsupported or not-checkable" in coverage
    checker = " ".join(bpm.get_role("fact-checker").body.split())
    assert "n of m factual claims verified (n = m required)" in checker and "each resting on verified facts: yes" in checker
    # the old unwinnable form counted every claim, opinions included
    assert not any("every claim verified" in c for c in research_criteria)


def test_research_criteria_make_the_final_report_paste_the_coverage_line(research_criteria):
    assert any("pastes that coverage line verbatim" in c for c in research_criteria)


def test_research_example_yaml_is_clean_and_names_the_section_as_judgement(tmp_path):
    bp = yaml.safe_load(EXAMPLE_YAML.read_text())
    bp["needs"]["deliverable"]["path"] = str(tmp_path / "out" / "c.md")
    (tmp_path / "out").mkdir()
    assert not bpm.errors(bpm.validate(bp, allowed_roots=[tmp_path]))
    assert "marked as our assessment" in bp["needs"]["deliverable"]["description"]
    assert any('"Where we can win"' in c and "judgement" in c for c in bp["task"]["acceptance"])


def test_judgement_section_wording_is_consistent_across_writer_checker_and_manager():
    for role in ("writer", "fact-checker"):
        assert "judgement" in bpm.get_role(role).body
    assert "labelled" in bpm.get_role("writer").body and "labelled" in bpm.get_role("fact-checker").body


# ------------------------------------------------------------------------------------ analysis example
def test_analysis_example_is_a_known_kind_and_proposes_cleanly_once_filled(cwd):
    assert "analysis" in ex.KINDS
    bp = filled("analysis", cwd)
    issues = bpm.validate(bp, allowed_roots=[cwd.parent])
    assert not bpm.errors(issues), [i.render() for i in issues]
    assert codes(issues) <= {"path-delivery", "path-parent", "workspace-new", "shell-unconfined"}
    out = bpm.propose_text(bp, allowed_roots=[cwd.parent])
    assert bpm.PLAN_HEADING in out and "Errors (" not in out


def test_analysis_example_roles_inputs_and_workspace(cwd):
    bp = filled("analysis", cwd)
    agents = {a.addr: a for a in bpm._resolve(bp, None, [cwd.parent], [])}
    data, ws = str((cwd / "data").resolve()), str((cwd / "analysis-work").resolve())
    assert bp["needs"]["kind"] == "analysis" and bp["needs"]["inputs"] == [str(cwd / "data")]
    assert not (Path(ws) == Path(data) or Path(data) in Path(ws).parents or Path(ws) in Path(data).parents)  # scratch is outside the data
    analyst, checker, writer = agents["lead/analyst"], agents["lead/checker"], agents["lead/writer"]
    assert analyst.tools == ["read", "shell"] and checker.tools == ["read", "shell"] and "write" not in analyst.tools + checker.tools
    assert analyst.workspace == ws and checker.workspace == ws
    assert analyst.kind == "author" and checker.kind == "verifier" and analyst.template.name == "analyst" and checker.template.name == "data-checker"
    assert analyst.inputs == [data] and checker.inputs == [data]  # the data is read-only for everyone
    assert writer.tools == ["read"] and ws in writer.inputs and data in writer.inputs and writer.workspace is None
    assert set(agents["lead"].tools) == {"read", "shell"} and agents["lead"].workspace == ws


def test_analysis_example_criteria_are_reproducible_complete_label_bound_and_sample_safe(cwd):
    crit = filled("analysis", cwd)["task"]["acceptance"]
    text = " ".join(crit)
    for needle in ("One script in the workspace regenerates every figure", "running it twice", "identical output",
                   "every available column and against every pair of the strongest dimensions", "(for example reason x region)",
                   "strongest effects with their counts", "appears together with its label in the script output",
                   "every label and number pair, not only that the number occurs", "fewer than 30 rows", '"too small"',
                   "unchanged", "Figures checked: n of m match' with n = m", "dimensions covered: k of d' with k = d",
                   "recommendations are in a section labelled as our assessment"):
        assert needle in text, needle
    checker = " ".join(bpm.get_role("data-checker").body.split())
    assert "Figures checked: n of m match" in checker and "dimensions covered: k of d" in checker


def test_analysis_example_applies_and_the_data_stays_read_only(cwd, tmp_path):
    bp = filled("analysis", cwd)
    o = Org.init(tmp_path / "org", "analysis", {"poll_seconds": 0.05})
    s = bpm.apply(o, bp, allowed_roots=[tmp_path])
    assert sorted(s.agents) == ["lead", "lead/analyst", "lead/checker", "lead/writer"]
    data = (cwd / "data").resolve()
    for a in s.agents:
        assert o.workspace_of(a) is None or not (data in o.workspace_of(a).parents or o.workspace_of(a) == data)
        assert data in o.inputs_of(a)
    assert "Read-only inputs" in o.charter("lead/analyst")[1] and "analysis" in o.charter("lead/analyst")[1].lower()


# ------------------------------------------------------ verifiers read what they review (read-only inputs)
def ws_bp(tmp_path, verifier: dict, authors=None):
    """A project with a workspace: an analyst writes there, one verifier checks it."""
    ws, data = tmp_path / "work", tmp_path / "data"
    ws.mkdir(exist_ok=True)
    data.mkdir(exist_ok=True)
    return {
        "mission": "Analyse the orders.",
        "needs": {"scope": "orders 2025", "kind": "analysis", "inputs": [str(data)], "workspace": str(ws),
                  "deliverable": {"description": "report", "format": "markdown", "max_words": 800},
                  "quality_bar": "numbers reproducible", "sources": "the files only, no web", "budget_runs": 40,
                  "model_policy": "one model for all", "review": True, "approval": "plan", "progress": "on request"},
        "agents": [{"name": "lead", "template": "manager", "children": [
            {"name": "analyst", "template": "analyst", **(authors or {})}, verifier]}],
        "task": {"title": "Analyse", "goal": "Explain returns", "acceptance": ["At most 800 words as counted by read", "Each figure appears with its label"]},
    }


@pytest.mark.parametrize("verifier", [
    {"name": "rev", "template": "reviewer"},                       # the D study: tools [] , hirearchy read only
    {"name": "rev", "template": "reviewer", "tools": ["read"]},
    {"name": "rev", "template": "fact-checker"},                   # web tools only, no built-in read
])
def test_a_verifier_without_write_access_gets_the_workspace_read_only_and_can_read_the_work(tmp_path, verifier):
    bp = ws_bp(tmp_path, verifier)
    assert not bpm.errors(bpm.validate(bp, allowed_roots=[tmp_path]))
    o = Org.init(tmp_path / "org", "ro", {"poll_seconds": 0.05})
    bpm.apply(o, bp, allowed_roots=[tmp_path])
    ws, data = (tmp_path / "work").resolve(), (tmp_path / "data").resolve()
    (ws / "report.md").write_text("West | Late delivery: 30 of 47\n")
    meta, _ = o.charter("lead/rev")
    assert "workspace" not in meta and ws in o.inputs_of("lead/rev") and data in o.inputs_of("lead/rev")
    assert "30 of 47" in o.read(str(ws / "report.md"), "lead/rev")  # hirearchy read opens it
    with pytest.raises(OrgError):
        o.resolve_write("lead/rev", str(ws / "report.md"))  # but it can never change it
    with pytest.raises(OrgError):
        o.read(str(tmp_path), "lead/rev")  # and only what it reviews is opened, not the whole tree
    # the manager holds what its team holds (the workspace is its own, the data is an input): authority only narrows
    assert data in o.inputs_of("lead") and o.workspace_of("lead") == ws and "30 of 47" in o.read(str(ws / "report.md"), "lead")


def test_the_charter_of_a_verifier_names_the_workspace_as_read_only_input(tmp_path):
    bp = ws_bp(tmp_path, {"name": "rev", "template": "reviewer"})
    o = Org.init(tmp_path / "org", "ro", {"poll_seconds": 0.05})
    bpm.apply(o, bp, allowed_roots=[tmp_path])
    body = o.charter("lead/rev")[1]
    assert f"Read-only inputs: {tmp_path.resolve() / 'data'}" in body and str(tmp_path.resolve() / "work") in body


def test_a_verifier_with_write_access_in_the_workspace_gets_no_read_only_copy_of_it(tmp_path):
    bp = ws_bp(tmp_path, {"name": "chk", "template": "data-checker"})
    agents = {a.addr: a for a in bpm._resolve(bp, None, [tmp_path], [])}
    ws = str((tmp_path / "work").resolve())
    assert agents["lead/chk"].workspace == ws and ws not in agents["lead/chk"].inputs  # it writes there; a read-only copy would contradict that
    assert agents["lead/chk"].inputs == [str((tmp_path / "data").resolve())]


def test_a_verifier_reads_each_authors_separate_workspace_but_not_its_own(tmp_path):
    proj = tmp_path / "proj"
    for d in (proj, proj / "dev", proj / "qa"):
        d.mkdir(exist_ok=True)
    bp = {
        "mission": "Build a small CLI.",
        "needs": {"scope": "csv2md", "kind": "code", "deliverable": {"description": "pkg", "format": "python package"},
                  "quality_bar": "tests pass", "workspace": str(proj), "budget_runs": 40, "model_policy": "one model for all",
                  "review": True, "approval": "plan", "progress": "on request",
                  "code": {"tests": "pytest", "packaging": "uv", "commits": "local"}},
        "agents": [{"name": "lead", "template": "manager", "children": [
            {"name": "dev", "template": "engineer", "workspace": str(proj / "dev")},
            {"name": "qa", "template": "tester", "workspace": str(proj / "qa")},
            {"name": "cr", "template": "code-reviewer", "workspace": str(proj / "qa")}]}],
        "task": {"title": "Build", "goal": "Implement", "acceptance": ["`uv run pytest -q` passes with at least 5 tests", "`csv2md in.csv` prints a table"]},
    }
    issues = bpm.validate(bp, allowed_roots=[tmp_path])
    assert not bpm.errors(issues) and "verifier-cannot-read" not in codes(issues)
    agents = {a.addr: a for a in bpm._resolve(bp, None, [tmp_path], [])}
    dev, qa = str((proj / "dev").resolve()), str((proj / "qa").resolve())
    assert agents["lead/qa"].inputs == [dev] and agents["lead/cr"].inputs == [dev]
    o = Org.init(tmp_path / "org", "ro", {"poll_seconds": 0.05})
    bpm.apply(o, bp, allowed_roots=[tmp_path])
    (proj / "dev" / "app.py").write_text("print('hi')\n")
    assert "print" in o.read(str(proj / "dev" / "app.py"), "lead/qa")
    with pytest.raises(OrgError):
        o.resolve_write("lead/qa", str(proj / "dev" / "app.py"))


def test_default_blueprints_with_verifiers_have_no_unreadable_warning(tmp_path):
    for verifier in ({"name": "rev", "template": "reviewer"}, {"name": "chk", "template": "data-checker"},
                     {"name": "fc", "template": "fact-checker"}):
        issues = bpm.validate(ws_bp(tmp_path, verifier), allowed_roots=[tmp_path])
        assert "verifier-cannot-read" not in codes(issues), verifier


def test_warning_when_a_verifier_with_explicit_inputs_cannot_read_what_it_reviews(tmp_path):
    other = tmp_path / "other"
    other.mkdir()
    bp = ws_bp(tmp_path, {"name": "rev", "template": "reviewer", "tools": ["read"], "inputs": [str(other)]})
    issues = bpm.validate(bp, allowed_roots=[tmp_path])
    warn = [i for i in issues if i.code == "verifier-cannot-read"]
    assert len(warn) == 1 and warn[0].level == "warning" and not bpm.errors(issues)
    assert "lead/rev" in warn[0].message and str((tmp_path / "work").resolve()) in warn[0].message and "pasted text" in warn[0].message
    assert "cannot read it" in bpm.render_plan(bp, issues, allowed_roots=[tmp_path])
    ok = ws_bp(tmp_path, {"name": "rev", "template": "reviewer", "tools": ["read"],
                          "inputs": [str(other), str(tmp_path / "work")]})
    assert "verifier-cannot-read" not in codes(bpm.validate(ok, allowed_roots=[tmp_path]))


def test_explicit_inputs_are_kept_as_the_blueprint_says(tmp_path):
    other = tmp_path / "other"
    other.mkdir()
    bp = ws_bp(tmp_path, {"name": "rev", "template": "reviewer", "tools": ["read"], "inputs": [str(other)]})
    agents = {a.addr: a for a in bpm._resolve(bp, None, [tmp_path], [])}
    assert agents["lead/rev"].inputs == [str(other.resolve())]
