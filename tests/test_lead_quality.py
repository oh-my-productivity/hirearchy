"""Lead quality (study A4): the manager sequences, routes rework to the author, follows the failure policy and keeps
the authors' rework runs; the fact-checker prints one final coverage line from the fetched text; a cheap lead is warned."""

import copy
from pathlib import Path

import pytest
import yaml

from orgmcp import blueprint as bpm
from orgmcp.blueprint_examples import example
from orgmcp.core import split_frontmatter

EXAMPLE = Path(__file__).resolve().parent.parent / "examples" / "blueprint-research.yaml"


def body(name: str) -> str:
    return " ".join(bpm.get_role(name).body.lower().split())


def has(name: str, *phrases: str) -> None:
    text = body(name)
    for p in phrases:
        assert p.lower() in text, f"{name} template lacks: {p!r}"


@pytest.fixture
def base(tmp_path):
    (tmp_path / "deliverables").mkdir()
    bp = yaml.safe_load(EXAMPLE.read_text())
    bp["needs"]["deliverable"]["path"] = str(tmp_path / "deliverables" / "competitors.md")
    return bp


def tiered(bp):
    """The tiering a user gets only by asking for cheaper drafting models."""
    bp["needs"]["models"] = {"cheap": "claude-haiku-4.5", "strong": "claude-sonnet-4.6"}
    bp["needs"]["model_policy"] = "cheap drafting, strong review"
    return bp


def mutate(bp, fn):
    out = copy.deepcopy(bp)
    fn(out)
    return out


def issues(bp, tmp_path):
    return bpm.validate(bp, allowed_roots=[tmp_path])


def codes(found, level=None):
    return {i.code for i in found if level is None or i.level == level}


# ----------------------------------------------------------------------------------------- manager template


def test_manager_delegates_a_step_only_when_its_inputs_exist():
    has("manager", "delegate a step only when its inputs exist", "research, then write, then check",
        "never pre-delegate a downstream step", "in one batch only the steps that need nothing from a teammate")


def test_manager_never_sends_status_or_waiting_messages():
    has("manager", "never send status, waiting or \"are you done\" messages", "do not poll", "results wake you")


def test_manager_routes_rework_to_the_author_with_revises_and_quotes_the_checker():
    has("manager", "required changes go to the author of the failing artifact", "the agent whose file failed",
        "revises=<that author's task id>", "quoting the checker's required changes verbatim",
        "never send a deliverable's fixes to the researcher")


def test_manager_rechecks_the_same_file_that_failed():
    has("manager", "the re-check is `delegate(to=<checker>, revises=<checker's task id>)`", "names the same file that failed")


def test_manager_failure_policy_is_one_rework_one_recheck_then_blocked_with_options():
    has("manager", "after one failed check, exactly one cut-or-reframe rework by the author and one re-check of that file",
        "do not start another research cycle", "make no extra re-checks", "report `blocked` to your parent",
        "options", "the checker's coverage line")


def test_manager_budget_keeps_author_rework_and_checker_recheck_runs_and_mentions_reclaim():
    has("manager", "for each author one rework run", "for each checker one re-check run",
        "reclaim(report=<sibling>, budget=n)", "before you ask your parent")


def test_manager_still_pastes_the_coverage_line_verbatim():
    has("manager", "pastes the verifier's final coverage line verbatim")


def test_manager_default_tier_is_strong_and_says_why():
    role = bpm.get_role("manager")
    assert role.tier == "strong"
    meta = split_frontmatter((bpm.ROLES_DIR / "manager.md").read_text(encoding="utf-8"))[0]
    assert "strong" in meta["model_note"] and "studies A3/A4" in meta["model_note"]


# ------------------------------------------------------------------------------------- fact-checker template


def test_fact_checker_computes_totals_once_and_prints_one_final_coverage_line():
    has("fact-checker", "compute the totals once, from the finished ledger", "print one coverage line as the last line of your report",
        "never recount inside the deliverable, the author's file or another agent's files", "do not post a second, corrected line")


def test_fact_checker_quote_must_come_from_the_fetch_or_read_output():
    has("fact-checker", "copy the quote from the text your `web_fetch` or `read` call returned",
        "if the fetched text lacks the sentence, the row is `unsupported`", "even if the page might render it")


# ----------------------------------------------------------------------------------------- budget split


def agents_of(bp, tmp_path):
    return bpm._resolve(bp, None, [tmp_path], [])


def test_split_gives_every_worker_its_pass_plus_rework_or_recheck(base, tmp_path):
    agents = agents_of(base, tmp_path)
    est = bpm.estimate(agents)["per"]
    split = bpm.budget_split(agents, 22)
    for name in ("researcher", "writer", "factcheck"):
        addr = f"lead/{name}"
        assert split[addr]["grant"] == est[addr]["pass"] + est[addr]["rework"] == est[addr]["total"]
    assert split["lead/writer"]["grant"] >= 3  # an empty first run no longer leaves it without its rework run
    assert split["lead/factcheck"]["grant"] == est["lead/factcheck"]["pass"] + 1


def test_split_keeps_the_managers_own_runs_and_a_reserve(base, tmp_path):
    agents = agents_of(base, tmp_path)
    est = bpm.estimate(agents)
    total = bpm.planned_total(base, est["total"])
    split = bpm.budget_split(agents, total)
    assert (total, split["lead"]["keeps"]) == (22, 12)
    assert split["lead"]["keeps"] >= est["per"]["lead"]["total"]
    handed = sum(split[a]["grant"] for a in ("lead/researcher", "lead/writer", "lead/factcheck"))
    assert handed + split["lead"]["keeps"] == total


def test_split_at_the_estimate_leaves_exactly_the_managers_own_pass_and_rework(base, tmp_path):
    agents = agents_of(base, tmp_path)
    est = bpm.estimate(agents)
    split = bpm.budget_split(agents, est["total"])
    assert split["lead"]["keeps"] == est["per"]["lead"]["total"]


def test_charter_and_plan_carry_the_new_numbers(base, tmp_path):
    from orgmcp.core import Org
    org = Org.init(tmp_path / "org", "lead quality", {"poll_seconds": 0.05})
    plan = bpm.render_plan(base, allowed_roots=[tmp_path])
    assert ("lead: starts with 22, hands down researcher 4, writer 3, factcheck 3 (each includes its rework/re-check run), "
            "keeps 12 (own 7 + slack 5)") in plan
    assert "lead starts with 22, hands down researcher 4, writer 3, factcheck 3 and keeps 12" in bpm.plan_for_user(base, allowed_roots=[tmp_path])
    bpm.apply(org, base, allowed_roots=[tmp_path])
    _, charter = org.charter("lead")
    assert "lead/writer 3" in charter and "already includes that worker's one rework" in charter


# ------------------------------------------------------------------------------- manager-cheap-model warning


def test_cheap_manager_gets_a_warning_not_an_error(base, tmp_path):
    bp = mutate(tiered(base), lambda b: b["agents"][0].update(model="cheap"))
    found = issues(bp, tmp_path)
    hit = [i for i in found if i.code == "manager-cheap-model"]
    assert len(hit) == 1 and hit[0].level == "warning" and hit[0].path == "agents[lead]"
    assert "the lead decides how every other run is spent; cheap leads misroute rework and waste runs (studies A3/A4)" in hit[0].message
    assert not bpm.errors(found)


def test_manager_on_the_cheap_model_id_is_flagged(base, tmp_path):
    bp = mutate(tiered(base), lambda b: b["agents"][0].update(model="claude-haiku-4.5"))
    assert "manager-cheap-model" in codes(issues(bp, tmp_path), "warning")


def test_manager_sharing_the_drafters_model_while_strong_is_available_is_flagged(base, tmp_path):
    def both_on_one(b):
        b["needs"]["models"] = {"cheap": "m-small", "strong": "m-big"}
        b["agents"][0]["model"] = "m-small-custom"
        for kid in b["agents"][0]["children"]:
            if kid["name"] in ("researcher", "writer"):
                kid["model"] = "m-small-custom"
    assert "manager-cheap-model" in codes(issues(mutate(base, both_on_one), tmp_path), "warning")


def test_strong_manager_is_not_flagged(base, tmp_path):
    base = tiered(base)
    assert "manager-cheap-model" not in codes(issues(base, tmp_path))
    by_id = mutate(base, lambda b: b["agents"][0].update(model="claude-sonnet-4.6"))
    assert "manager-cheap-model" not in codes(issues(by_id, tmp_path))
    default = mutate(base, lambda b: b["agents"][0].pop("model"))  # the template's default tier is strong
    assert "manager-cheap-model" not in codes(issues(default, tmp_path))


def test_one_model_for_all_is_not_flagged(base, tmp_path):
    def single(b):
        b["needs"].pop("models")
        b["needs"]["model_policy"] = "one model for all"
        b["agents"][0].pop("model")
    assert "manager-cheap-model" not in codes(issues(mutate(base, single), tmp_path))


# ------------------------------------------------------------------------------------------- research example


def test_default_single_model_policy_never_warns_about_the_lead(base, tmp_path):
    for bp in (base, mutate(base, lambda b: b["agents"][0].update(model="cheap")),  # the cheap tier IS the strong model here
               mutate(base, lambda b: b["needs"].pop("models"))):
        found = issues(bp, tmp_path)
        assert not codes(found, "error") and not codes(found) & {"manager-cheap-model", "model-policy", "model-review", "model-single"}
    only_cheap = mutate(base, lambda b: b["needs"].update(models={"cheap": "claude-sonnet-5.5"}))
    assert not codes(issues(only_cheap, tmp_path)) & {"manager-cheap-model"}


def test_tiering_on_request_still_warns_when_the_lead_is_cheap(base, tmp_path):
    cheap_lead = mutate(tiered(base), lambda b: b["agents"][0].update(model="cheap"))
    assert "manager-cheap-model" in codes(issues(cheap_lead, tmp_path), "warning")
    assert "manager-cheap-model" not in codes(issues(tiered(base), tmp_path))
    equal = mutate(tiered(base), lambda b: b["needs"].update(models={"cheap": "m", "strong": "m"}))
    assert "manager-cheap-model" not in codes(issues(mutate(equal, lambda b: b["agents"][0].update(model="cheap")), tmp_path))


def test_research_example_proposes_cleanly_under_25(base, tmp_path):
    base = tiered(base)
    found = issues(base, tmp_path)
    assert not bpm.errors(found) and "manager-cheap-model" not in codes(found)
    agents = agents_of(base, tmp_path)
    est = bpm.estimate(agents)["total"]
    total = bpm.planned_total(base, est)
    assert est == 17 and total == 22 <= base["needs"]["budget_runs"] == 25
    models = {a.addr: a.model for a in agents}
    assert models == {"lead": "claude-sonnet-4.6", "lead/researcher": "claude-haiku-4.5", "lead/writer": "claude-haiku-4.5",
                      "lead/factcheck": "claude-sonnet-4.6"}
    plan = bpm.propose(yaml.safe_dump(base), allowed_roots=[tmp_path])
    assert "Reply 'approve'" in plan and "Errors" not in plan


def test_research_blueprint_example_text_keeps_the_lead_strong(tmp_path):
    bp = yaml.safe_load(example("research", tmp_path).replace("<", "").replace(">", ""))
    lead = bp["agents"][0]
    assert lead["template"] == "manager" and lead["model"] == "strong"
