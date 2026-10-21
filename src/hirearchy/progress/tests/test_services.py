# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

import time

from testkit.reach.hirearchy.core import ROOT
from testkit.services_world import deliver, request, svc

from hirearchy.progress import progress

WEEKDAY = "weekly-brief"


def test_progress_lines_of_a_rework_chain_show_the_case_total(svc):
    first = request(svc, "ai")
    deliver(svc, "ceo", first, runs=3)
    svc.feedback(ROOT, first.id, "reject", "Too long.")
    time.sleep(0.002)
    rework = svc.request(ROOT, WEEKDAY, {"topic": "ai"}, revises=first.id, budget=6)
    deliver(svc, "ceo", rework, runs=2)
    text = progress(svc)
    assert text.count("case total: 5 runs used of 16 handed down (contract: 10 per request)") == 2  # one per task line
    assert "exceeds the per-request budget of 10: tell the user" in text
    assert ".." not in text.replace("...", "")  # the sentences join cleanly
    # the rework is delivered and not yet rated by the client; the first one has her verdict
    lines = {line.split("(task ")[1].rstrip(")"): line for line in text.splitlines() if "(task " in line}
    assert "no feedback yet" in lines[rework.id] and "no feedback yet" not in lines[first.id]


def test_a_single_request_case_has_no_case_total_line(svc):
    first = request(svc, "ai")
    deliver(svc, "ceo", first)
    assert "case total" not in progress(svc)


# ---------------------------------------------------------------------------- progress and status
def test_progress_tags_service_tasks_and_notes_missing_feedback(svc):
    org = svc
    org.revise_playbook("ceo", "weekly-brief", "Steps.", "r", [])
    task = request(org, "ai")
    (line,) = progress(org).splitlines()
    assert line.startswith('"weekly-brief: ai" [service weekly-brief v1]: working.') and "no feedback yet" not in line
    deliver(org, "ceo", task)
    org.delegate(ROOT, "ceo", "Plain", "g", "c", budget=2)
    out = progress(org)
    line = next(x for x in out.splitlines() if "weekly-brief: ai" in x)
    assert "[service weekly-brief v1]: done." in line and line.count("no feedback yet") == 1
    assert "[service" not in next(x for x in out.splitlines() if '"Plain"' in x)
    assert "Needs you" not in out  # neither the missing feedback nor the revision note asks for the human
    org.feedback(ROOT, task.id, "accept")
    assert "no feedback yet" not in progress(org)


def test_playbook_revisions_are_quiet_notices_for_root(svc):
    org = svc
    org.revise_playbook("ceo", "weekly-brief", "Steps.", "first", [])
    assert org.messages(ROOT, "inbox") and "Needs you" not in progress(org)
    org.notify(ROOT, "loud", "Needs a decision")
    assert "Needs you: runtime notice" in progress(org)
