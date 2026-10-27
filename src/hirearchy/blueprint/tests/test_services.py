# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

import copy
import re
from pathlib import Path

import pytest
import testkit
import yaml
from testkit.reach.hirearchy.app import wiring
from testkit.reach.hirearchy.core import ROOT, Org, OrgError

from testkit.blueprint_world import bpm, services_mod
from hirearchy.blueprint.testing import FlakyServiceCommands
from hirearchy.services import ServiceCommands

ROOT_DIR = testkit.REPO
RESEARCH = ROOT_DIR / "examples" / "blueprint-research.yaml"
CRITERIA = [
    "At most 600 words as counted by read.",
    'Has exactly the sections "This week" and "Our assessment", in that order.',
    "Every sentence with a number, name, version, date or price cites the URL of the page that states it; the fact-checker fetched that page.",
]


def service(**over) -> dict:
    sv = {
        "name": "weekly-brief",
        "description": "A one-page, sourced brief on the past week's news about a topic.",
        "inputs": [{"name": "topic", "description": "what the brief is about", "required": True},
                   {"name": "week", "description": "ISO week", "required": False}],
        "acceptance": list(CRITERIA),
        "deliverable": {"description": "One markdown file", "format": "markdown", "max_words": 600},
        "budget": 22,
    }
    sv.update(over)
    return sv


@pytest.fixture
def roots(tmp_path):
    return [tmp_path]


@pytest.fixture
def svc_bp(tmp_path):
    """The research team offering one service: no needs.deliverable and no task (services only)."""
    (tmp_path / "deliverables").mkdir()
    bp = yaml.safe_load(RESEARCH.read_text())
    bp["needs"].pop("deliverable")
    bp.pop("task")
    bp["services"] = [service(deliverable={"description": "One markdown file", "format": "markdown", "max_words": 600,
                                           "path": str(tmp_path / "deliverables" / "briefs")})]
    return bp


@pytest.fixture
def plain_bp(tmp_path):
    """The shipped research blueprint (a plain task) with its deliverable inside the allowed root."""
    (tmp_path / "deliverables").mkdir(exist_ok=True)
    bp = yaml.safe_load(RESEARCH.read_text())
    bp["needs"]["deliverable"]["path"] = str(tmp_path / "deliverables" / "competitors.md")
    return bp


@pytest.fixture
def empty_org(tmp_path):
    return Org.init(tmp_path / "org", "service blueprint tests", {"poll_seconds": 0.05})


def mutate(bp, fn):
    out = copy.deepcopy(bp)
    fn(out)
    return out


def issues(bp, roots, **kw):
    return bpm.validate(bp, allowed_roots=roots, **kw)


def codes(found, level=None):
    return {i.code for i in found if level is None or i.level == level}


def paths(found, code):
    return [i.path for i in found if i.code == code]


def e5_blueprint(tmp_path, **service_over):
    """The blueprint of the E5 run: lead with a writer and a reviewer (estimate 11, a client round of 5), cap 12, one service with budget 12."""
    (tmp_path / "deliverables").mkdir(exist_ok=True)
    bp = yaml.safe_load(RESEARCH.read_text())
    bp["needs"].pop("deliverable"), bp["needs"].pop("sources"), bp.pop("task")
    bp["needs"].update(budget_runs=12, quality_bar="Every decision and action is taken from the notes.")
    bp["agents"] = [{"name": "lead", "template": "manager", "children": [{"name": "writer", "template": "writer"}, {"name": "reviewer", "template": "reviewer"}]}]
    bp["services"] = [service(name="weekly-meeting-memo", budget=12, acceptance=["At most 600 words as counted by read.", 'Has exactly the sections "Decisions" and "Actions", in that order.'],
                              deliverable={"description": "One markdown file", "format": "markdown", "max_words": 600, "path": str(tmp_path / "deliverables" / "memos")})]
    bp["services"][0].update(service_over)
    return bp


E5_TIGHT = ("{total} runs per request covers one pass and one internal rework (the estimate is 11), not a round of your questions or a rejection, "
            "which takes about 5 more (1, plus 2 for each agent below lead): 16 per request covers one such round")


def block(bp, roots, **kw) -> str:
    text = bpm.plan_for_user(bp, allowed_roots=roots, **kw)
    return text


# ------------------------------------------------------------------------------------------ validation
def test_a_services_only_blueprint_needs_no_deliverable_task_or_acceptance(svc_bp, roots):
    """D-E5-2: the services-only blueprint asks for 24 runs per request (the estimate 17 plus one client round of 7), so it gets no budget warning."""
    found = issues(mutate(svc_bp, lambda b: b["services"][0].update(budget=24)), roots)
    assert not bpm.errors(found), [i.render() for i in found]
    assert codes(found, "warning") <= {"path-delivery", "path-parent"}


def test_plain_task_blueprints_are_unchanged(svc_bp, roots, plain_bp):
    plain = plain_bp
    assert not bpm.errors(issues(plain, roots))
    no_deliverable = mutate(plain, lambda b: b["needs"].pop("deliverable"))
    assert "deliverable" in codes(issues(no_deliverable, roots), "error")
    no_task = mutate(plain, lambda b: b.pop("task"))
    err = [i for i in issues(no_task, roots) if i.code == "task"]
    assert err and "task is missing" in err[0].message and "services" in err[0].message  # points at services
    no_criteria = mutate(plain, lambda b: b["task"].pop("acceptance"))
    assert "criteria" in codes(issues(no_criteria, roots), "error")


def test_a_plain_task_next_to_services_keeps_every_plain_check(svc_bp, roots, plain_bp):
    bp = mutate(svc_bp, lambda b: b.update(task={"to": "lead", "title": "One-off", "goal": "Do it once"}))
    found = issues(bp, roots)
    assert {"deliverable", "criteria"} <= codes(found, "error")  # a plain task still needs its own deliverable and criteria
    good = plain_bp
    good["services"] = [service()]
    assert not bpm.errors(issues(good, roots))


def test_services_is_known_and_an_unknown_service_key_warns(svc_bp, roots):
    assert "unknown-key" not in codes(issues(svc_bp, roots))
    bp = mutate(svc_bp, lambda b: b["services"][0].update(schedule="weekly"))
    found = [i for i in issues(bp, roots) if i.code == "unknown-key"]
    assert found and found[0].path == "services[weekly-brief]" and "schedule" in found[0].message


@pytest.mark.parametrize("over, code, needle", [
    ({"name": "Weekly Brief"}, "service-name", "invalid service name"),
    ({"name": ""}, "service-name", "invalid service name"),
    ({"owner": "lead/writer"}, "service-owner", "must be the top-level agent (lead)"),
    ({"owner": "nobody"}, "service-owner", "must be the top-level agent (lead)"),
    ({"description": ""}, "service", "description is one line"),
    ({"description": "two\nlines"}, "service", "description is one line"),
    ({"description": "x" * 301}, "service", "at most 300"),
    ({"inputs": "topic"}, "service-inputs", "list"),
    ({"inputs": [{"name": "Topic"}]}, "service-inputs", "input name"),
    ({"inputs": [{"name": "topic"}, {"name": "topic"}]}, "service-inputs", "used twice"),
    ({"inputs": [{"name": "topic", "color": "red"}]}, "service-inputs", "unknown key"),
    ({"acceptance": []}, "criteria", "acceptance criteria"),
    ({"acceptance": "just words"}, "criteria", "acceptance criteria"),
    ({"deliverable": {"format": "markdown"}}, "deliverable", "needs a description"),
    ({"deliverable": {"description": "d", "max_words": 0}}, "deliverable", "max_words"),
    ({"deliverable": {"description": "d", "path": "relative/dir"}}, "deliverable", "absolute"),
    ({"deliverable": {"description": "d", "colour": "red"}}, "deliverable", "unknown key"),
    ({"budget": 0}, "service", "whole number"),
    ({"budget": True}, "service", "whole number"),
    ({"budget": "lots"}, "service", "whole number"),
    ({"budget": 26}, "budget-cap", "above the user's cap of 25"),
    ({"budget": 10}, "budget-low", "cannot cover the pipeline"),
    ({"playbook": "  "}, "playbook", "workflow as markdown"),
    ({"playbook": "word " * 1001}, "playbook", "limit is 1000"),
    ({"locked": "yes"}, "service", "true or false"),
])
def test_bad_services_are_errors_with_a_fix(svc_bp, roots, over, code, needle):
    bp = mutate(svc_bp, lambda b: b["services"][0].update(over))
    found = [i for i in issues(bp, roots) if i.level == "error" and i.code == code]
    assert found, [i.render() for i in issues(bp, roots)]
    assert any(needle in i.message for i in found), [i.message for i in found]


def test_service_errors_name_the_service_in_their_path(svc_bp, roots):
    bp = mutate(svc_bp, lambda b: b["services"][0].update(acceptance=[]))
    assert "services[weekly-brief].acceptance" in paths(issues(bp, roots), "criteria")
    bp = mutate(svc_bp, lambda b: b["services"][0].update(budget=26))
    assert paths(issues(bp, roots), "budget-cap") == ["services[weekly-brief].budget"]


def test_services_must_be_a_list_of_mappings_with_unique_names(svc_bp, roots):
    for bad in ("weekly-brief", {"name": "x"}):
        found = issues(mutate(svc_bp, lambda b: b.update(services=bad)), roots)
        assert any(i.path == "services" and i.level == "error" for i in found)
    assert any(i.path == "services[0]" for i in issues(mutate(svc_bp, lambda b: b.update(services=["x"])), roots))
    assert any("services is empty" in i.message for i in issues(mutate(svc_bp, lambda b: b.update(services=["x"])), roots))
    dup = mutate(svc_bp, lambda b: b["services"].append(service(description="Another")))
    assert any("duplicate service name" in i.message for i in issues(dup, roots))
    two = mutate(svc_bp, lambda b: b["services"].append(service(name="daily-digest")))
    assert not bpm.errors(issues(two, roots))
    empty = mutate(svc_bp, lambda b: b.update(services=[]))  # an empty list is no services: the task is missing
    assert "task" in codes(issues(empty, roots), "error")


def test_a_service_name_taken_in_the_organization_is_an_error(svc_bp, roots, empty_org):
    empty_org.hire(ROOT, "other", "Other team", "Does things.", can_hire=True)
    empty_org.define_service(ROOT, "other", "weekly-brief", description="Other", inputs=[], acceptance=["a b c d"],
                             deliverable={"description": "d"}, budget=3)
    found = issues(svc_bp, roots, org=empty_org)
    assert any(i.code == "service-name" and "already exists in this organization" in i.message for i in found)
    with pytest.raises(bpm.BlueprintError, match="already exists in this organization"):
        bpm.apply(empty_org, svc_bp, allowed_roots=roots)
    assert empty_org.agents() == ["other"]  # nothing was created


def test_service_acceptance_gets_the_vague_criteria_checks(svc_bp, roots):
    bp = mutate(svc_bp, lambda b: b["services"][0].update(acceptance=["Good quality", *CRITERIA]))
    found = [i for i in issues(bp, roots) if i.code == "vague-criterion"]
    assert [i.path for i in found] == ["services[weekly-brief].acceptance[1]"]
    no_limit = mutate(svc_bp, lambda b: b["services"][0].update(acceptance=CRITERIA[1:]))
    assert paths(issues(no_limit, roots), "limit-criterion") == ["services[weekly-brief].acceptance"]


def test_service_acceptance_as_a_bullet_text_is_accepted_like_the_task_one(svc_bp, roots):
    text = yaml.safe_dump(mutate(svc_bp, lambda b: b["services"][0].update(acceptance="\n".join(f"- {c}" for c in CRITERIA))))
    bp = bpm.load_text(text)
    assert bp["services"][0]["acceptance"] == CRITERIA
    assert not bpm.errors(issues(bp, roots))


def test_reviewers_cannot_be_told_to_edit_in_service_criteria(svc_bp, roots):
    bad = "The fact-checker applies the corrections directly to the report."
    bp = mutate(svc_bp, lambda b: b["services"][0]["acceptance"].append(bad))
    found = [i for i in issues(bp, roots) if i.code == "edits-others"]
    assert [i.path for i in found] == ["services[weekly-brief].acceptance[4]"]


def test_code_service_needs_tests_in_its_criteria(tmp_path, roots):
    ws = tmp_path / "proj"
    ws.mkdir()
    bp = {
        "mission": "Build small software changes on request.",
        "needs": {"kind": "code", "scope": "csv2md", "workspace": str(ws), "budget_runs": 30, "model_policy": "one model for all",
                  "review": True, "approval": "plan first", "progress": "on request",
                  "code": {"tests": "pytest", "packaging": "uv", "commits": "local"}},
        "agents": [{"name": "lead", "template": "manager",
                    "children": [{"name": "dev", "template": "engineer"}, {"name": "qa", "template": "tester"},
                                 {"name": "cr", "template": "code-reviewer"}]}],
        "services": [service(name="feature", description="One feature of the software, tested and committed.",
                             acceptance=["The change is committed locally in the workspace.", "Nothing was pushed to any remote repository."],
                             deliverable={"description": "the change in the workspace", "format": "code"}, budget=23)],
    }
    found = issues(bp, roots)
    assert not bpm.errors(found)
    assert paths(found, "code-criteria") == ["services[feature].acceptance"]


def test_a_budget_that_keeps_the_estimate_but_not_a_client_round_says_what_covers_one(tmp_path):
    """D-E5-2: the E5 blueprint (cap 12, budget 12, estimate 11, round 5) is told the number that covers one round of the user's questions."""
    found = issues(e5_blueprint(tmp_path), [tmp_path])
    assert not bpm.errors(found), [i.render() for i in found]
    (tight,) = [i for i in found if i.code == "budget-tight"]
    assert tight.level == "warning" and tight.path == "services[weekly-meeting-memo].budget" and tight.message == E5_TIGHT.format(total=12)


def test_a_default_budget_that_a_cap_keeps_under_a_client_round_says_so_at_the_cap(tmp_path):
    bp = e5_blueprint(tmp_path)
    bp["services"][0].pop("budget")
    found = issues(bp, [tmp_path])
    assert not bpm.errors(found), [i.render() for i in found]
    (tight,) = [i for i in found if i.code == "budget-tight"]
    assert tight.path == "needs.budget_runs" and tight.message == E5_TIGHT.format(total=12)


def test_a_budget_that_covers_the_estimate_and_a_client_round_gets_no_warning(tmp_path):
    bp = e5_blueprint(tmp_path, budget=16)
    bp["needs"]["budget_runs"] = 20
    assert "budget-tight" not in codes(issues(bp, [tmp_path]))
    just_under = e5_blueprint(tmp_path, budget=15)
    just_under["needs"]["budget_runs"] = 20
    assert [i.message for i in issues(just_under, [tmp_path]) if i.code == "budget-tight"] == [E5_TIGHT.format(total=15)]


def test_a_budget_under_the_estimate_keeps_the_budget_low_error(tmp_path):
    found = issues(e5_blueprint(tmp_path, budget=10), [tmp_path])
    (low,) = [i for i in found if i.code == "budget-low"]
    assert low.level == "error" and low.path == "services[weekly-meeting-memo].budget"
    assert low.message == ("10 runs per request cannot cover the pipeline: the estimate with one review and one rework cycle is 11 (see estimate()); "
                           "raise the budget or drop a role")
    assert "budget-tight" not in codes(found)


def test_without_a_cap_the_default_budget_is_the_estimate_plus_one_client_round(tmp_path):
    bp = e5_blueprint(tmp_path)
    bp["services"][0].pop("budget"), bp["needs"].pop("budget_runs")
    found = issues(bp, [tmp_path])
    assert not bpm.errors(found) and "budget-tight" not in codes(found)
    assert "Budget: up to 16 runs per request" in bpm.plan_for_user(bp, found, allowed_roots=[tmp_path])


def test_the_budget_cap_is_per_request(svc_bp, roots, plain_bp):
    no_budget = mutate(svc_bp, lambda b: b["services"][0].pop("budget"))
    assert not bpm.errors(issues(no_budget, roots))  # default: the estimate plus one client round (24), within the cap of 25
    assert bpm.service_budget(no_budget["services"][0], 17, 25) == 22 and bpm.service_budget({}, 17, 20) == 20
    assert bpm.service_budget({"budget": 7}, 17, 20) == 7 and bpm.service_budget({}, 17, None) == 22
    low_cap = mutate(svc_bp, lambda b: (b["services"][0].pop("budget"), b["needs"].update(budget_runs=15)))
    err = [i for i in issues(low_cap, roots) if i.code == "budget-low"]
    assert err and err[0].path == "needs.budget_runs" and "cannot cover the pipeline" in err[0].message
    tight = mutate(svc_bp, lambda b: b["services"][0].update(budget=18))
    assert paths(issues(tight, roots), "budget-tight") == ["services[weekly-brief].budget"]
    # a plain task blueprint's budget messages keep their wording and paths
    plain = plain_bp
    plain["task"]["budget"] = 30
    assert paths(issues(plain, roots), "budget-cap") == ["task.budget"]


def test_each_service_is_checked_against_the_same_cap(svc_bp, roots):
    bp = mutate(svc_bp, lambda b: b["services"].append(service(name="daily-digest", budget=40)))
    assert paths(issues(bp, roots), "budget-cap") == ["services[daily-digest].budget"]


def test_web_and_code_checks_see_the_services_text(svc_bp, roots):
    no_web = mutate(svc_bp, lambda b: [a.update(tools=[]) for a in b["agents"][0]["children"]])
    # services-only text with URLs but no web tool anywhere
    for child in no_web["agents"][0]["children"]:
        child.pop("template")
        child["charter"] = "Do the work."
    no_web["needs"]["sources"] = "the team's own knowledge"
    no_web["needs"]["quality_bar"] = "Careful."
    no_web["mission"] = "Offer a brief."
    no_web["needs"]["scope"] = "A topic."
    found = issues(no_web, roots)
    assert "web-tools" in codes(found, "error")  # from the service's acceptance ("cites the URL")
    assert bpm._is_code({"mission": "x", "services": [service(description="Implement a library feature")]})
    assert not bpm._is_code({"mission": "x", "services": [service()]})
    assert "URL" in bpm._blob(svc_bp) and "what the brief is about" in bpm._blob(svc_bp)


def test_plan_id_changes_when_services_change(svc_bp):
    base = bpm.plan_id(svc_bp)
    assert base == bpm.plan_id(copy.deepcopy(svc_bp)) and len(base) == bpm.PLAN_ID_LENGTH
    for fn in (lambda b: b["services"][0].update(budget=21),
               lambda b: b["services"][0]["acceptance"].append("Another exact criterion here."),
               lambda b: b["services"][0].update(locked=True),
               lambda b: b["services"][0].update(playbook="## Steps\n1. Do it."),
               lambda b: b["services"].append(service(name="other-service")),
               lambda b: b.update(task={"service": "weekly-brief", "inputs": {"topic": "ai"}})):
        assert bpm.plan_id(mutate(svc_bp, fn)) != base
    assert bpm.plan_id(mutate(svc_bp, lambda b: b.pop("services"))) != base


# ----------------------------------------------------------------------------------------- first request
def request_bp(svc_bp, **task):
    return mutate(svc_bp, lambda b: b.update(task={"service": "weekly-brief", "inputs": {"topic": "solid-state batteries"}, **task}))


def test_a_task_may_be_a_first_request(svc_bp, roots, plain_bp):
    bp = request_bp(svc_bp, title="Brief on batteries")
    assert not bpm.errors(issues(bp, roots))
    assert bpm._is_request(bp) and not bpm._plain(bp)
    assert not bpm._is_request(svc_bp) and bpm._plain(plain_bp)


@pytest.mark.parametrize("task, needle", [
    ({"service": "nope", "inputs": {"topic": "x"}}, "not one of the blueprint's services (weekly-brief)"),
    ({"service": "weekly-brief", "inputs": {"week": "2026-W43"}}, "missing required input(s) for `weekly-brief`: topic"),
    ({"service": "weekly-brief", "inputs": {"topic": "  "}}, "missing required input(s)"),
    ({"service": "weekly-brief", "inputs": {"topic": "x", "colour": "red"}}, "unknown input(s) for `weekly-brief`: colour"),
    ({"service": "weekly-brief", "inputs": ["topic"]}, "mapping"),
    ({"service": "weekly-brief", "inputs": {"topic": "x"}, "to": "lead/writer"}, "must be the top-level agent (lead)"),
])
def test_a_bad_first_request_is_an_error(svc_bp, roots, task, needle):
    bp = mutate(svc_bp, lambda b: b.update(task=task))
    found = [i for i in issues(bp, roots) if i.level == "error" and i.path.startswith("task.")]
    assert any(needle in i.message for i in found), [i.render() for i in issues(bp, roots)]


def test_a_request_without_services_is_an_error(svc_bp, roots):
    bp = mutate(svc_bp, lambda b: (b.pop("services"), b.update(task={"service": "weekly-brief"})))
    assert any(i.path == "task.service" and "no `services:`" in i.message for i in issues(bp, roots))


def test_request_tasks_warn_about_keys_that_come_from_the_service(svc_bp, roots):
    bp = request_bp(svc_bp, goal="Do it", acceptance=["x"])
    unknown = [i for i in issues(bp, roots) if i.code == "unknown-key" and i.path == "task"]
    assert {"goal", "acceptance"} <= {re.search(r"'(\w+)'", i.message).group(1) for i in unknown}


def test_optional_inputs_may_stay_out_and_a_service_without_inputs_takes_none(svc_bp, roots):
    assert not bpm.errors(issues(request_bp(svc_bp), roots))
    bare = mutate(svc_bp, lambda b: (b["services"][0].update(inputs=[]), b.update(task={"service": "weekly-brief"})))
    assert not bpm.errors(issues(bare, roots))


# ------------------------------------------------------------------------------------------------ plan
def test_the_block_has_a_compact_services_part(svc_bp, roots):
    text = block(svc_bp, roots)
    assert text.startswith(bpm.PLAN_HEADING) and bpm.PLAN_END not in text
    lines = text.splitlines()
    i = lines.index("Services (kept ready, requested whenever you want):")
    part = lines[i:i + 12]
    assert part[1] == "- weekly-brief: A one-page, sourced brief on the past week's news about a topic."
    assert part[2] == "  You provide: topic (required), week (optional)"
    assert part[3] == "  Each request: up to 22 runs"
    assert part[4] == "  Checks:" and part[5].startswith("    1. At most 600 words")
    assert part[8].startswith("  Delivered to: ") and part[8].endswith("(I copy each result there after checking it)")
    assert len(lines) <= 42, len(lines)  # compact: it is shown verbatim to non-technical users


def test_the_block_says_what_reflection_does_and_who_can_change_the_checks(svc_bp, roots):
    text = block(svc_bp, roots)
    assert ("After each request the lead records lessons; before the next one it reviews them with your feedback and may "
            "improve how the team works (its playbook). It cannot change these checks: only you can, through me.") in text
    other = mutate(svc_bp, lambda b: b["agents"][0].update(name="ceo"))
    other["services"][0]["owner"] = "ceo"
    assert "After each request the lead (ceo) records lessons" in block(other, roots)


def test_without_a_first_task_the_block_says_nothing_runs_until_a_request(svc_bp, roots):
    text = block(svc_bp, roots)
    assert "Nothing runs until you ask for a request" in text and "First request" not in text
    assert "Done when" not in text and "Deliverable:" not in text.replace("deliverable", "")  # per service instead
    with_request = block(request_bp(svc_bp), roots)
    assert "Nothing runs until" not in with_request
    assert "First request, started on approval: weekly-brief (topic: solid-state batteries)." in with_request


def test_budget_lines_of_a_services_blueprint_are_per_request(svc_bp, roots):
    text = block(svc_bp, roots)
    assert "Budget: up to 22 runs per request" in text and "your cap per request is 25" in text
    assert "lead starts with 22, hands down researcher 4, writer 3, factcheck 3 and keeps 12" in text
    assert "nothing beyond a request's budget is spent without your OK" in text
    assert "every service check below" in text
    two = mutate(svc_bp, lambda b: b["services"].append(service(name="daily-digest", budget=20)))
    text = block(two, roots)
    assert "up to 22 runs per request" in text and "lead starts with" not in text  # no single split to show
    assert text.count("  Each request: up to") == 2


def test_up_to_ten_checks_are_shown(svc_bp, roots):
    ten = [f"Section number {n} is present and has exactly 3 bullets." for n in range(1, 11)]
    bp = mutate(svc_bp, lambda b: b["services"][0].update(acceptance=ten))
    text = block(bp, roots)
    assert all(f"    {n}. {c}" in text for n, c in enumerate(ten, 1))
    assert "more (see the details)" not in text


def test_more_than_the_shown_criteria_are_counted_not_hidden_silently(svc_bp, roots):
    many = [f"Section number {n} is present and has exactly 3 bullets." for n in range(1, 13)]
    bp = mutate(svc_bp, lambda b: b["services"][0].update(acceptance=many))
    text = block(bp, roots)
    assert "    10. Section number 10" in text and "    11. Section" not in text
    assert "... and 2 more (see the details)" in text
    assert all(f"{n}. {c}" in bpm.render_plan(bp, allowed_roots=roots) for n, c in enumerate(many, 1))  # all in the details


def test_a_plain_task_plan_has_no_services_part(roots, plain_bp):
    plain = plain_bp
    text = block(plain, roots)
    assert "Services" not in text and "playbook" not in text and "Done when ALL of these hold:" in text
    assert "Budget: 22 runs planned" in text
    assert "Services" not in bpm.render_plan(plain, allowed_roots=roots)


def test_a_plain_task_next_to_services_shows_both(roots, plain_bp):
    bp = plain_bp
    bp["services"] = [service()]
    text = block(bp, roots)
    assert "Done when ALL of these hold:" in text and "Services (kept ready" in text
    assert "Nothing runs until" not in text and "Budget: 22 runs planned" in text


def test_the_details_have_the_full_contract_and_the_generated_playbook(svc_bp, roots):
    details = bpm.render_plan(svc_bp, allowed_roots=roots)
    assert "Services (1), offered by lead" in details and "inputs: topic (required), week (optional)" in details
    assert "    3. Every sentence with a number" in details  # every criterion, in full
    assert "playbook v1: generated from the team" in details and "## Budget plan" in details
    assert "No first task: nothing runs until you ask for a request" in details
    assert "Budget per request" in details and "service weekly-brief: 22 runs per request" in details
    given = mutate(svc_bp, lambda b: b["services"][0].update(playbook="## Steps\n1. Do the work."))
    assert "playbook v1: given in the blueprint (6 words)" in bpm.render_plan(given, allowed_roots=roots)
    assert "First request: service weekly-brief" in bpm.render_plan(request_bp(svc_bp, title="T"), allowed_roots=roots)


def test_propose_text_shows_the_services_and_a_plan_id(svc_bp, roots):
    out = bpm.propose_text(svc_bp, allowed_roots=roots)
    assert bpm.PLAN_HEADING in out and "Services (kept ready" in out and f"plan_id: {bpm.plan_id(svc_bp)}" in out
    bad = mutate(svc_bp, lambda b: b["services"][0].update(acceptance=[]))
    out = bpm.propose_text(bad, allowed_roots=roots)
    assert bpm.PLAN_DRAFT_HEADING in out and "plan_id: none" in out


# ------------------------------------------------------------------------------------------------ apply
def test_apply_services_only_defines_the_service_and_gives_no_task(svc_bp, roots, empty_org):
    s = bpm.apply(empty_org, svc_bp, allowed_roots=roots)
    assert s.agents == ["lead", "lead/researcher", "lead/writer", "lead/factcheck"] and s.services == ["weekly-brief"]
    assert s.task_id == "" and s.budget == 0 and s.to == "lead"
    assert empty_org.received("lead") == [] and empty_org.open_tasks("lead") == []  # nothing was requested
    text = s.text()
    assert "defined 1 service(s) of lead: weekly-brief" in text and "nothing runs yet" in text
    assert "request(service, inputs)" in text and "start()" in text and "task " not in text.replace("no task", "")
    c = services_mod.read_contract(empty_org, "lead", "weekly-brief")
    assert (c.version, c.budget, c.locked, c.defined_by) == (1, 22, False, ROOT)
    assert c.description.startswith("A one-page, sourced brief") and c.acceptance == CRITERIA
    assert [(i["name"], i["required"]) for i in c.inputs] == [("topic", True), ("week", False)]
    assert c.deliverable["max_words"] == 600 and c.deliverable["path"].endswith("deliverables/briefs")
    pb = services_mod.read_playbook(empty_org, "lead", "weekly-brief")
    assert pb.version == 1 and pb.by == ROOT and pb.reason == "initial playbook"
    assert "weekly-brief" in services_mod.services_text(empty_org, ROOT)


def test_apply_writes_the_generated_v1_in_item_form(svc_bp, roots, empty_org):
    """`apply_org` writes the service through `define_service`, so the generated v1 is step items (`op: first`, no `admitted`)."""
    bpm.apply(empty_org, svc_bp, allowed_roots=roots)
    pb = services_mod.read_playbook(empty_org, "lead", "weekly-brief")
    assert pb.items is not None and pb.parse_error == "" and pb.op == "first" and pb.admitted == "" and pb.items_max == len(pb.items) > 0
    assert all(i.kind == "step" and i.why == () for i in pb.items) and pb.rules == ()
    assert pb.body.count("[P1]") == 1 and f"[P{pb.items_max}]" in pb.body


def test_apply_with_a_first_request_creates_a_service_task(svc_bp, roots, empty_org):
    s = bpm.apply(empty_org, request_bp(svc_bp, title="Brief on batteries", note="Keep it short."), allowed_roots=roots)
    assert s.service_request == "weekly-brief" and s.budget == 22 and s.task_id
    assert f"first request: service weekly-brief, task {s.task_id} -> lead (budget 22)" in s.text()
    task = empty_org.find_received("lead", s.task_id)
    assert (task.service, task.contract, task.playbook, task.budget) == ("weekly-brief", 1, 1, 22)
    assert task.title == "Brief on batteries" and task.sender == ROOT
    assert "- topic: solid-state batteries" in task.body and "## Acceptance criteria\n- C1: At most 600 words" in task.body
    assert "- C3: Every sentence with a number" in task.body and "## Note from the requester\nKeep it short." in task.body
    assert empty_org.budget("lead") == 22


def test_apply_a_first_request_gets_the_default_title(svc_bp, roots, empty_org):
    s = bpm.apply(empty_org, request_bp(svc_bp), allowed_roots=roots)
    assert empty_org.find_received("lead", s.task_id).title == "weekly-brief: solid-state batteries"


def test_apply_a_plain_task_next_to_services(roots, empty_org, plain_bp):
    bp = plain_bp
    bp["services"] = [service()]
    s = bpm.apply(empty_org, bp, allowed_roots=roots)
    task = empty_org.find_received("lead", s.task_id)
    assert task.service is None and task.budget == 22 and s.service_request == "" and s.services == ["weekly-brief"]
    assert "task " + s.task_id + " -> lead (budget 22)" in s.text()
    assert services_mod.read_contract(empty_org, "lead", "weekly-brief") is not None


def test_apply_a_plain_blueprint_defines_no_service(roots, empty_org, plain_bp):
    s = bpm.apply(empty_org, plain_bp, allowed_roots=roots)
    assert s.services == [] and empty_org.service_names("lead") == [] and "service" not in s.text()
    assert not (empty_org.dir("lead") / "services").exists()
    _, charter = empty_org.charter("lead")
    assert "Services you offer" not in charter and "Budget plan: you start with 22 runs" in charter


def test_apply_uses_the_blueprints_playbook_and_lock(svc_bp, roots, empty_org):
    bp = mutate(svc_bp, lambda b: b["services"][0].update(playbook="## Steps\n1. Search.\n2. Write.\n", locked=True))
    bpm.apply(empty_org, bp, allowed_roots=roots)
    pb = services_mod.read_playbook(empty_org, "lead", "weekly-brief")
    assert pb.body == "## Steps\n1. [P1] Search.\n2. [P2] Write." and pb.version == 1
    assert services_mod.read_contract(empty_org, "lead", "weekly-brief").locked is True


def test_apply_two_services_and_the_default_budget(svc_bp, roots, empty_org):
    bp = mutate(svc_bp, lambda b: (b["services"][0].pop("budget"), b["services"].append(service(name="daily-digest", budget=19))))
    s = bpm.apply(empty_org, bp, allowed_roots=roots)
    assert s.services == ["weekly-brief", "daily-digest"]
    assert services_mod.read_contract(empty_org, "lead", "weekly-brief").budget == 24  # the estimate plus one client round
    digest = services_mod.read_playbook(empty_org, "lead", "daily-digest").body
    assert "Request budget: 19 runs" in digest and "you (lead): keep 9 runs" in digest


def test_apply_rolls_back_agents_when_a_service_cannot_be_defined(svc_bp, roots, empty_org):
    empty_org.runtime = wiring.open_runtime(empty_org.root, {ServiceCommands: FlakyServiceCommands(empty_org.runtime.service_commands, fail_define_on=1)})
    with pytest.raises(OrgError, match="disk full"):
        bpm.apply(empty_org, svc_bp, allowed_roots=roots)
    assert empty_org.agents() == []  # the hires were undone


def test_apply_refuses_a_blueprint_with_service_errors_before_writing(svc_bp, roots, empty_org):
    bad = mutate(svc_bp, lambda b: b["services"][0].update(acceptance=[]))
    with pytest.raises(bpm.BlueprintError, match="services\\[weekly-brief\\].acceptance"):
        bpm.apply(empty_org, bad, allowed_roots=roots)
    assert empty_org.agents() == []


def test_the_applied_service_works_end_to_end_with_request_and_feedback(svc_bp, roots, empty_org):
    bpm.apply(empty_org, svc_bp, allowed_roots=roots)
    msg = empty_org.request(ROOT, "weekly-brief", {"topic": "ai chips"})
    assert msg.budget == 22 and msg.playbook == 1 and msg.contract == 1
    prompt_org = empty_org.run_prompt("lead", empty_org.begin_run("lead"))
    assert "# Your services" in prompt_org and "# Playbook: weekly-brief (v1, yours to improve)" in prompt_org
    assert "> ## Steps" in prompt_org


# --------------------------------------------------------------------------------- playbook and charter
def test_the_generated_playbook_has_the_three_sections_in_order(svc_bp):
    agents = bpm._resolve(svc_bp, None, [Path("/")], [])
    text = bpm.default_playbook(agents[0], agents, svc_bp["services"][0], 22)
    assert [m.group(0) for m in re.finditer(r"^## .*$", text, re.M)] == ["## Steps", "## Budget plan", "## Pitfalls"]
    assert text.rstrip().endswith("## Pitfalls\nnone yet: add them from lessons and feedback")


def test_the_generated_playbook_carries_the_teams_procedure(svc_bp):
    agents = bpm._resolve(svc_bp, None, [Path("/")], [])
    text = bpm.default_playbook(agents[0], agents, svc_bp["services"][0], 22)
    steps = text.split("## Budget plan")[0]
    # who drafts, who verifies, in this order
    assert steps.index("`researcher`") < steps.index("`writer`") < steps.index("`factcheck`")
    assert "`budget=4`" in steps and "`budget=3`" in steps
    assert "only the steps that need nothing from a teammate" not in steps  # no first-run leftover: the manager template says it, once per task
    assert "Never delegate a step before its inputs exist" in steps
    assert "AUTHOR of the failing file" in steps and "revises=<that author's task id>" in steps  # author-routed rework
    assert "revises=<the checker's task id>" in steps and "One rework and one re-check" in steps
    assert "EVERY criterion of the request" in steps and "coverage line verbatim" in steps  # the final check
    assert "`lessons`" in steps and "what to change in this playbook" in steps  # report with lessons
    budget = text.split("## Budget plan")[1].split("## Pitfalls")[0]
    assert "- researcher: 4 runs (3 work + 1 rework or re-check)" in budget
    assert "- writer: 3 runs (2 work + 1 rework or re-check)" in budget
    assert "- factcheck: 3 runs (2 work + 1 rework or re-check)" in budget
    assert "- you (lead): keep 12 runs: your own 7" in budget and "5 of slack" in budget
    assert "Unspent runs return to your parent" in budget


def test_the_playbook_budget_plan_follows_the_service_budget(svc_bp):
    agents = bpm._resolve(svc_bp, None, [Path("/")], [])
    sv = svc_bp["services"][0]
    for budget, keeps in ((17, 7), (30, 20)):
        text = bpm.default_playbook(agents[0], agents, sv, budget)
        assert f"Request budget: {budget} runs" in text and f"keep {keeps} runs" in text
    assert "slack" not in bpm.default_playbook(agents[0], agents, sv, 17)  # exactly the estimate: no slack


def test_the_playbook_names_the_delivery_path_only_when_there_is_one(svc_bp):
    agents = bpm._resolve(svc_bp, None, [Path("/")], [])
    with_path = bpm.default_playbook(agents[0], agents, svc_bp["services"][0], 22)
    assert "(the assistant copies it to " in with_path and "deliverables/briefs)" in with_path
    sv = copy.deepcopy(svc_bp["services"][0])
    sv["deliverable"].pop("path")
    assert "the assistant copies" not in bpm.default_playbook(agents[0], agents, sv, 22)


def test_the_playbook_of_a_big_team_stays_under_the_cap(roots, tmp_path):
    kids = [{"name": f"w{i}", "template": "writer"} for i in range(5)]
    bp = {"mission": "m", "needs": {"budget_runs": 99}, "agents": [{"name": "lead", "template": "manager", "children": kids}],
          "services": [service(name="big", budget=60)]}
    agents = bpm._resolve(bp, None, roots, [])
    text = bpm.default_playbook(agents[0], agents, bp["services"][0], 60)
    assert len(text.split()) < 1000
    assert all(f"`w{i}`" in text for i in range(5))


def test_a_single_agent_gets_a_playbook_that_does_the_work_itself(roots):
    bp = {"mission": "m", "needs": {"budget_runs": 20}, "agents": [{"name": "solo", "charter": "Does it all."}],
          "services": [service(name="solo-brief", budget=8)]}
    agents = bpm._resolve(bp, None, roots, [])
    text = bpm.default_playbook(agents[0], agents, bp["services"][0], 8)
    assert "Do the work yourself" in text and "delegate(" not in text and "Delegate to" not in text
    assert "you (solo): keep 8 runs" in text


def test_the_leads_charter_says_the_playbook_is_the_procedure(svc_bp, roots, empty_org):
    bpm.apply(empty_org, svc_bp, allowed_roots=roots)
    _, charter = empty_org.charter("lead")
    assert "Services you offer: weekly-brief" in charter
    assert "the playbook shown in your prompt is the procedure" in charter and "the playbook wins" in charter
    assert "You own the playbook and improve it with `revise_playbook`" in charter and "never lower it" in charter
    assert "improve it with `revise_playbook` when the client's evidence calls for it (ORG.md rule 10)" in charter
    assert "from the evidence shown before a new request" not in charter
    # a services-only lead is not given numbers that could contradict the playbook's budget plan
    assert "you start with" not in charter and "the budget of its service" in charter and "`## Budget plan`" in charter
    assert "Review loop:" in charter and "Your team (fixed by the plan" in charter
    for worker in ("lead/researcher", "lead/writer", "lead/factcheck"):
        assert "Services you offer" not in empty_org.charter(worker)[1]


def test_a_lead_with_a_plain_task_and_services_keeps_the_task_budget_plan(roots, empty_org, plain_bp):
    bp = plain_bp
    bp["services"] = [service()]
    bpm.apply(empty_org, bp, allowed_roots=roots)
    _, charter = empty_org.charter("lead")
    assert "Budget plan: you start with 22 runs" in charter and "Services you offer: weekly-brief" in charter
