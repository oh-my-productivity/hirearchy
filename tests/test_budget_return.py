"""Budget travels back up with the final result, or by hand to the parent; and stranded budget is flagged."""

from datetime import timedelta

import pytest

from orgmcp import templates
from orgmcp.core import ROOT, utcnow
from orgmcp.health import agent_health
from orgmcp.review import review

ENG = "ceo/eng"


def run(org, addr):
    """One run of ``addr``: it reads its mail and consumes one run of budget (left open: nothing ends it)."""
    org.begin_run(addr)
    org.start_run_log(addr)


# ---------------------------------------------------------------------------- stranded_budget
def later(hours):
    return utcnow() + timedelta(hours=hours)


@pytest.fixture
def stranded(org):
    """eng holds 3 runs, nothing to do, and its parent (ceo) is not root."""
    org.send(ROOT, "ceo", "grant", budget=10)
    org.send("ceo", ENG, "grant", budget=3)
    for a in ("ceo", ENG):
        org.begin_run(a)
        org.end_run(a, ok=True)  # both read their grant: no unread mail
    return org


def test_idle_budget_is_flagged_after_the_threshold(stranded):
    assert "stranded_budget" not in agent_health(stranded, ENG, now=utcnow()).flags
    flags = agent_health(stranded, ENG, now=later(1)).flags
    assert "stranded_budget" in flags and "3 unused run(s)" in flags["stranded_budget"]


def test_stranded_budget_threshold_is_configurable(stranded):
    from orgmcp.core import join_frontmatter, split_frontmatter

    path = stranded.root / "ORG.md"
    meta, body = split_frontmatter(path.read_text(encoding="utf-8"))
    path.write_text(join_frontmatter({**meta, "health": {"stranded_after_seconds": 7200}}, body), encoding="utf-8")
    assert "stranded_budget" not in agent_health(stranded, ENG, now=later(1)).flags
    assert "stranded_budget" in agent_health(stranded, ENG, now=later(3)).flags


def test_no_flag_when_there_is_work_or_no_budget_or_the_parent_is_root(stranded):
    org = stranded
    task = org.delegate("ceo", ENG, "t", "g", "c", budget=1)  # open task
    assert "stranded_budget" not in agent_health(org, ENG, now=later(1)).flags
    run(org, ENG)
    org.report(ENG, task.id, "done", "ok")  # returns everything: nothing left to strand
    assert org.budget(ENG) == 0 and "stranded_budget" not in agent_health(org, ENG, now=later(1)).flags
    assert "stranded_budget" not in agent_health(org, "ceo", now=later(1)).flags  # parent is root


def test_no_flag_while_waiting_on_a_delegation(org):
    org.hire("ceo", "ops", "Ops", "Run.", can_hire=True)
    org.hire("ceo/ops", "dev", "Dev", "Code.")
    org.send(ROOT, "ceo", "grant", budget=10)
    org.send("ceo", "ceo/ops", "grant", budget=6)
    org.begin_run("ceo/ops")
    org.end_run("ceo/ops", ok=True)
    org.delegate("ceo/ops", "ceo/ops/dev", "t", "g", "c", budget=2)
    assert "stranded_budget" not in agent_health(org, "ceo/ops", now=later(2)).flags


def test_the_review_tells_the_manager_what_to_do(stranded):
    result = review(stranded, now=later(1))
    ceo_note = next(n for n in result.notes if n.to == "ceo")
    assert "`ceo/eng` stranded_budget" in ceo_note.body
    assert templates.REVIEW_ACTIONS["stranded_budget"].format(a=ENG) in ceo_note.body
    assert "return its budget" in ceo_note.body and "retire" in ceo_note.body


# ------------------------------------------------------------------------------- the rules
def test_new_organizations_get_the_budget_and_review_rules(org):
    rules = org.rules()
    assert 'your remaining budget returns with the result' in rules and "`budget=N`" in rules
    assert "9. Reviews and fact-checks: a reviewer never edits another agent's file" in rules
    assert "Never write acceptance criteria" in rules and "revises=<task id>" in rules
    assert "{" not in rules  # the template was filled in completely
