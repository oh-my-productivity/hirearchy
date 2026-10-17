"""The shipped role templates: they load, pass the blueprint checks, and carry the verification behaviours the
validation studies (A2, B2, C) showed were missing."""

import pytest

from orgmcp import blueprint as bpm
from orgmcp.core import Org

NAMES = bpm.role_names()
SECTIONS = ("## Purpose", "## Responsibilities", "## Decision rights", "## Escalation", "## Quality bar", "## Budget")
KNOWN_TOOLS = {"read", "write", "shell", "web_search", "web_fetch"}
VERIFIERS = ("reviewer", "fact-checker", "code-reviewer", "tester")


def body(name: str) -> str:
    return " ".join(bpm.get_role(name).body.lower().split())


def has(name: str, *phrases: str) -> None:
    text = body(name)
    for p in phrases:
        assert p.lower() in text, f"{name} template lacks: {p!r}"


def research_bp(tmp_path):
    return {
        "mission": "Compare five apps from public sources.",
        "needs": {"scope": "five apps", "deliverable": {"description": "comparison", "format": "markdown", "max_words": 900},
                  "quality_bar": "every claim cites the page that states it", "sources": "web, official pages",
                  "budget_runs": 40, "model_policy": "one model for all", "review": True, "approval": "plan",
                  "progress": "on request"},
        "agents": [{"name": "lead", "template": "manager", "children": [
            {"name": "res", "template": "researcher"}, {"name": "wr", "template": "writer"},
            {"name": "rev", "template": "reviewer"}, {"name": "fc", "template": "fact-checker"}]}],
        "task": {"title": "Compare", "goal": "Write the comparison", "acceptance": [
            "At most 900 words (as counted by read)", "Every claim cites the URL of the page that states it"]},
    }


def code_bp(tmp_path):
    ws = tmp_path / "proj"
    ws.mkdir(exist_ok=True)
    return {
        "mission": "Build a small CLI.",
        "needs": {"scope": "csv2md only", "kind": "code", "deliverable": {"description": "A Python package", "format": "python package"},
                  "quality_bar": "tests pass", "workspace": str(ws), "budget_runs": 40, "model_policy": "one model for all",
                  "review": True, "approval": "plan", "progress": "on request",
                  "code": {"tests": "pytest", "packaging": "uv", "commits": "local only"}},
        "agents": [{"name": "lead", "template": "manager", "children": [
            {"name": "dev", "template": "engineer"}, {"name": "qa", "template": "tester"},
            {"name": "cr", "template": "code-reviewer"}]}],
        "task": {"title": "Build", "goal": "Implement the CLI", "acceptance": [
            "`uv run pytest -q` passes with at least 5 tests", "`csv2md in.csv` prints a markdown table to stdout"]},
    }


# ------------------------------------------------------------------------------- every shipped template


def test_all_expected_templates_ship():
    assert {"manager", "researcher", "writer", "reviewer", "fact-checker", "engineer", "tester", "code-reviewer"} <= set(NAMES)


@pytest.mark.parametrize("name", NAMES)
def test_template_loads_with_valid_metadata_and_sections(name):
    r = bpm.get_role(name)
    assert r is not None and r.name == name
    assert r.kind in bpm.KINDS and r.tier in ("cheap", "strong") and r.summary and r.title
    assert set(r.tools) <= KNOWN_TOOLS and r.base_runs >= 0
    assert (r.kind == "manager") == (name == "manager")
    for section in SECTIONS:
        assert section in r.body, (name, section)


@pytest.mark.parametrize("name", NAMES)
def test_template_never_tells_anyone_to_edit_another_agents_file(name):
    assert bpm.edits_others_files(bpm.get_role(name).body) is None


@pytest.mark.parametrize("name", VERIFIERS)
def test_verifiers_never_edit_and_write_in_their_own_directory(name):
    has(name, "never edit", "your own")


@pytest.mark.parametrize("name", [n for n in NAMES if n != "manager"])
def test_template_estimate_is_computed(name):
    role = bpm.get_role(name)
    agent = bpm.Agent(f"x/{name}", name, "x", f"agents[x/{name}]", template=role, kind=role.kind)
    est = bpm.estimate([agent])["per"][agent.addr]
    assert est["pass"] == role.base_runs and est["rework"] == bpm.REWORK_RUNS[role.kind]
    assert est["total"] == est["pass"] + est["rework"] >= 1
    assert bpm.estimate([agent])["total"] == est["total"]


@pytest.mark.parametrize("make", [research_bp, code_bp])
def test_blueprint_with_shipped_templates_has_no_errors_and_an_estimate(make, tmp_path):
    bp = make(tmp_path)
    issues = bpm.validate(bp, allowed_roots=[tmp_path])
    assert not bpm.errors(issues), [i.render() for i in issues]
    agents = bpm._resolve(bp, None, [tmp_path], [])
    est = bpm.estimate(agents)
    assert est["total"] == sum(v["total"] for v in est["per"].values()) > 0
    assert bpm.planned_total(bp, est["total"]) >= est["total"]
    assert "Plan for approval" in bpm.render_plan(bp, issues, allowed_roots=[tmp_path])


@pytest.mark.parametrize("make", [research_bp, code_bp])
def test_blueprint_with_shipped_templates_applies(make, tmp_path):
    org = Org.init(tmp_path / "org", "role template tests", {"poll_seconds": 0.05})
    bp = make(tmp_path)
    s = bpm.apply(org, bp, allowed_roots=[tmp_path])
    assert len(s.agents) == len(list(_all(bp["agents"])))
    for a in s.agents:
        tpl = bpm.get_role(next(c for c in _all(bp["agents"]) if c["name"] == a.rsplit("/", 1)[-1])["template"])
        assert tpl.body.splitlines()[0] in org.charter(a)[1]


def _all(agents):
    for a in agents:
        yield a
        yield from _all(a.get("children", []))


# ------------------------------------------------------------------------------------------ fact-checker


def test_fact_checker_builds_a_claim_ledger_of_every_claim():
    has("fact-checker", "claim ledger", "work/ledger.md", "every sentence, table cell and list item",
        "id", "cited source", "verified", "wrong", "unsupported", "not-checkable", "evidence")


def test_fact_checker_requires_the_source_to_state_the_claim():
    has("fact-checker", "open and read every cited source", "must state the claim", "homepage, repo root", "unsupported",
        "points to the file or page the fact actually comes from")


def test_fact_checker_treats_negative_absolute_and_numeric_claims_as_high_risk():
    has("fact-checker", "negative and absolute claims", '"only"', '"never"', '"all"', "numbers, dates", "licenses", "prices",
        "cannot verify a negative claim by finding nothing")


def test_fact_checker_checks_arithmetic_and_word_counts_with_read():
    has("fact-checker", "word counts come from `read`", "never from an estimate")


def test_fact_checker_reports_coverage_and_fails_unless_every_claim_is_verified():
    has("fact-checker", "n of m claims verified, k wrong, j unsupported", "ledger path", "pass only if n = m", "fail",
        "never present a partial check as complete", "a sample")


def test_fact_checker_works_with_web_tools_and_with_local_inputs():
    r = bpm.get_role("fact-checker")
    assert {"web_search", "web_fetch"} <= set(r.tools)
    has("fact-checker", "`web_fetch` for pages", "`read` for files from the inputs", "no web tools")


# ------------------------------------------------------------------------------------ reviewer and code-reviewer


def test_reviewer_checks_every_criterion_one_by_one_with_evidence():
    has("reviewer", "one by one", "one line per criterion", "not met", "evidence", "criteria met: n of m",
        "counts come from `read`", "even if the author disclosed it")


def test_code_reviewer_can_run_things_and_runs_the_tests():
    r = bpm.get_role("code-reviewer")
    assert set(r.tools) == {"read", "shell"} and "write" not in r.tools and r.kind == "verifier"
    has("code-reviewer", "run what the criteria name", "test suite", "cli", "edge cases", "each command you ran and its result",
        "tests are then unverified", "you may not approve")


def test_code_reviewer_never_edits_and_says_shell_is_not_confined():
    has("code-reviewer", "you never edit the code", "cannot be technically confined", "never change, create or delete files",
        "git status --short")


def test_code_reviewer_with_shell_needs_a_workspace_like_the_engineer(tmp_path):
    bp = code_bp(tmp_path)
    assert not bpm.errors(bpm.validate(bp, allowed_roots=[tmp_path]))
    agents = {a.addr: a for a in bpm._resolve(bp, None, [tmp_path], [])}
    assert agents["lead/cr"].tools == ["read", "shell"] and agents["lead/cr"].workspace == str((tmp_path / "proj").resolve())
    assert set(agents["lead"].tools) >= {"read", "shell", "write"}  # the manager holds what it hands down
    no_ws = code_bp(tmp_path)
    del no_ws["needs"]["workspace"]
    codes = {i.code for i in bpm.validate(no_ws, allowed_roots=[tmp_path]) if i.level == "error"}
    assert "workspace-confinement" in codes


# ------------------------------------------------------------------------------------------------ manager


def test_manager_quotes_counts_and_facts_from_read_not_memory():
    has("manager", "from your own `read` output", "never from memory", "what a report says", "stale copy")


def test_manager_compares_against_both_tasks_criteria():
    has("manager", "every criterion of the task you delegated and every criterion of the task assigned to you", "one by one")


def test_manager_never_reports_done_with_a_known_deviation():
    has("manager", "revises", "`send` your parent the deviation", "never report `done` with a known deviation",
        "disclosing it afterwards does not make the criterion met")


def test_manager_requires_the_verifiers_coverage_report_for_done():
    has("manager", "coverage report is a precondition for `done`", "n of m claims verified, k wrong, j unsupported",
        "n = m", "a sampled check is not enough")


def test_manager_keeps_its_budget_reserve_and_does_not_skip_a_review():
    has("manager", "one review and one rework", "never hand down more than the budget plan says", "grants are explicit",
        "not skipped")


# --------------------------------------------------------------------------------- author roles and tester


def test_writer_values_relevance_over_length_and_cites_precisely():
    has("writer", "relevance over length", "never pad", "too thin", "cite precisely", "count words with `read`")


def test_researcher_cites_the_page_that_states_the_claim_with_a_retrieval_date():
    has("researcher", "page that states the claim", "not the homepage or repository root", "retrieval date", "quoted sentence")


def test_engineer_runs_the_tests_and_reports_exact_commands():
    has("engineer", "run them before every report", "exact commands", "failing or unrun tests", "do not substitute silently")


def test_tester_exercises_every_criterion_with_commands_and_edge_cases():
    has("tester", "every acceptance criterion with commands", "every edge case and error path the criteria name", "not verified", "criteria passed n of m")
