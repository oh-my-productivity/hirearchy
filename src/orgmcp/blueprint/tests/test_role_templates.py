# mypy: ignore-errors
# A test moved from tests/ by tools/relocate_tests.py: untyped until it is converted. Delete the first line when this file is typed.

import pytest
from testkit.legacy.orgmcp.core import Org

from testkit.blueprint_world import bpm

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
    assert {"manager", "researcher", "writer", "reviewer", "fact-checker", "engineer", "tester", "code-reviewer",
            "analyst", "data-checker"} <= set(NAMES)


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
def test_fact_checker_builds_a_ledger_of_every_statement_split_into_fact_and_judgement():
    has("fact-checker", "work/ledger.md", "every sentence, table cell and list item", "`fact` or a `judgement`", "id", "type",
        "cited source", "verified", "wrong", "unsupported", "not-checkable", "evidence")


def test_fact_checker_defines_facts_by_what_they_contain():
    has("fact-checker", "number, name, version, license, price, date", '"no / only / never / all / every / free"',
        "a sentence that mixes fact and opinion is a fact row")


def test_fact_checker_requires_the_verbatim_sentence_from_the_source():
    has("fact-checker", "open and read every cited source", "copy the sentence that states the claim, verbatim",
        "a `verified` row without that quote is not verified", "must state the claim")


@pytest.mark.parametrize("weak", ["universally known", "not contradicted", "a homepage, repo root or index page",
                                  "a page that exists and is on topic", "a search snippet", "memory"])
def test_fact_checker_names_what_is_not_verification(weak):
    has("fact-checker", weak)


def test_fact_checker_checks_high_risk_claim_types_at_the_specific_page_with_exceptions():
    has("fact-checker", "high-risk claims get the specific page and an exception check", "license file of the specific package",
        "sub-packages", "non-commercial", "pricing page", "regional and tier differences", "sync, hosting and encryption models",
        "platform availability", "negative or absolute claims", "cannot verify a negative claim by finding nothing")


def test_fact_checker_checks_judgement_rows_for_label_citations_and_basis():
    has("fact-checker", "labelled as the author's assessment", "carry no citation", "a citation on an opinion is decoration",
        "rest on facts that are already verified", "`ok`", "`fix`")


def test_fact_checker_checks_arithmetic_and_word_counts_with_read():
    has("fact-checker", "word counts come from `read`", "never from an estimate")


def test_fact_checker_coverage_line_separates_facts_from_judgements_and_fails_unless_complete():
    has("fact-checker", "Coverage: n of m factual claims verified (n = m required)", "k wrong, u unsupported, p not-checkable",
        "j judgement statements, each resting on verified facts: yes", "pastes verbatim", "ledger path",
        "pass only if n = m and the judgement answer is yes", "fail", "never present a partial check as complete", "a sample")


def test_fact_checker_fixes_unverifiable_claims_by_cutting_or_reframing_never_from_memory():
    has("fact-checker", "cut it", "restate it as a labelled judgement", "never propose a fix that depends on memory",
        "a replacement is a new claim")


def test_fact_checker_reverifies_every_changed_sentence_after_rework():
    has("fact-checker", "every changed or new sentence as a new claim", "not only the rows you flagged",
        "no judgement picked up a citation or a new fact", "a claim is closed only when verified")


def test_fact_checker_works_with_web_tools_and_with_local_inputs():
    r = bpm.get_role("fact-checker")
    assert {"web_search", "web_fetch"} <= set(r.tools)
    has("fact-checker", "`web_fetch` for pages", "`read` for files from the inputs")


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
    has("manager", "coverage report is a precondition for `done`", "n of m factual claims verified", "n = m",
        "a sampled check is not enough", "judgement answer yes")


def test_manager_pastes_the_coverage_line_verbatim_and_never_calls_changes_claims():
    has("manager", "every `done` report pastes the verifier's final coverage line verbatim", "path of its ledger",
        "never describe re-checked changes as claim coverage", '"8 of 8 changes verified" is not "n of m claims verified"',
        "no coverage line from the latest verification of the final file, no `done`")


def test_manager_cuts_instead_of_another_research_cycle_and_escalates_with_options():
    has("manager", "a verification cycle is: verify, rework, re-verify", "do not start another research cycle",
        "prefer cutting", "cut every claim the verifier could not verify", "restate it as a labelled judgement",
        "report `blocked` to your parent", "the position (what is verified, what is not)", "options and a recommended decision",
        "instead of spending the reserve on a second full cycle")


def test_manager_template_limits_its_own_overhead():
    has("manager", "in one batch", "end your run", "do not poll", "only the new messages", "act on everything that arrived in that one run")
    assert len(bpm.get_role("manager").body.splitlines()) <= 50  # concise: every wake pays for the template


def test_manager_keeps_its_budget_reserve_and_does_not_skip_a_review():
    has("manager", "one review and one rework", "never hand down more than the budget plan says", "grants are explicit",
        "not skipped")


# --------------------------------------------------------------------------------- author roles and tester
def test_writer_values_relevance_over_length_and_cites_precisely():
    has("writer", "relevance over length", "never pad", "too thin", "cite precisely", "count words with `read`")


def test_researcher_cites_the_page_that_states_the_claim_with_a_retrieval_date():
    has("researcher", "page that states the claim", "not the homepage or repository root", "retrieval date", "quoted sentence")


def test_researcher_quotes_the_sentence_and_checks_exceptions_for_high_risk_claims():
    has("researcher", "copy the sentence that states the fact word for word", "a search snippet is a pointer, not a source",
        "neither are memory or \"everyone knows\"", "license file of the specific package", "server, client and sub-packages separately",
        "pricing page", "tiers, regions", "unverified", "the writer may only state what these entries state")


def test_writer_separates_factual_claims_from_labelled_judgement():
    has("writer", "a factual claim is any sentence, table cell or list item with a number, name, version, license, price, date",
        '"no / only / never / all / free"', "carries the exact source", "if no finding does, cut the claim",
        "do not write it from memory", "analysis and recommendations are judgement", "clearly labelled section",
        "no citations and no new facts", "may only rest on claims you have already stated and cited",
        "never decorate an opinion with citations")


def test_writer_reworks_by_cutting_or_reframing_and_never_swaps_in_facts_from_memory():
    has("writer", "change as little as possible", "cut it or restate it as a labelled judgement", "never swap in another fact from memory",
        "every sentence you change is a new claim for the verifier", "which sentences you changed")


def test_engineer_runs_the_tests_and_reports_exact_commands():
    has("engineer", "run them before every report", "exact commands", "failing or unrun tests", "do not substitute silently")


def test_tester_checks_each_figure_together_with_its_label_not_just_the_number():
    has("tester", "together with their labels", "each number next to the label or key it belongs to",
        "not that the number appears somewhere in the output", "a matching number under the wrong label is a failure")


def test_reviewer_opens_the_files_it_reviews_and_checks_figures_with_their_labels():
    has("reviewer", "start the review with the files you opened", "any you could not open", "report `blocked`",
        "never review text pasted into a task as if it were the file", "together with its label or subject")


# --------------------------------------------------------------------------- analysis roles
def test_analyst_template_is_read_and_shell_only_in_a_workspace_and_never_touches_the_data():
    r = bpm.get_role("analyst")
    assert set(r.tools) == {"read", "shell"} and r.kind == "author"
    has("analyst", "read-only input", "never create, edit or delete anything there", "workspace", "orgmcp `write`")


def test_analyst_explores_every_dimension_and_pair_and_binds_figures_to_labels():
    has("analyst", "one script", "run it twice", "every available dimension", "every pair of the strongest dimensions",
        "return reason x region", "counts and the base rate", "strongest effects", "too small", "fewer rows than the criteria's minimum",
        "appears with its label in the script's output", "never retype it from memory")


def test_data_checker_recomputes_with_its_own_script_and_checks_label_number_pairs():
    r = bpm.get_role("data-checker")
    assert set(r.tools) == {"read", "shell"} and r.kind == "verifier"
    has("data-checker", "your own script", "without copying the analyst's code", "together with their labels, never by presence",
        "(label, number)", "a number that matches under a different label", "fails", "every pair you checked")


def test_data_checker_checks_exploration_coverage_reproducibility_and_the_data():
    has("data-checker", "every pair of the strongest dimensions", "your own scan over all pairs", "a strong effect the report omits is a required change",
        "minimum-sample rule", "twice from a clean state", "checksums before and after",
        "Figures checked: n of m match (each with its label; n = m required)", "dimensions covered: k of d", "pass only if")


def test_data_checker_never_edits_the_analysts_work():
    has("data-checker", "you never edit the analyst's work", "never change the data")

    has("tester", "every acceptance criterion with commands", "every edge case and error path the criteria name", "not verified", "criteria passed n of m")
