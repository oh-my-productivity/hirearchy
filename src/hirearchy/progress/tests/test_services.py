# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

import time

from testkit.reach.hirearchy.core import ROOT
from testkit.services_world import deliver, request, svc

from hirearchy.progress import progress

WEEKDAY = "weekly-brief"


def test_progress_lines_of_a_rework_chain_show_the_case_total_in_its_relayed_form(svc):
    """D-E5-1 (A3): root's rework without a source is relayed, so its 8 runs are named apart as the assistant's own spend and 3 + 8 = 11 runs, the
    user's 3 of the 10 approved, warn of nothing (0a.2 said "exceeds ... tell the user" here, on the relayed runs)."""
    first = request(svc, "ai")
    deliver(svc, "ceo", first, runs=3)
    svc.feedback(ROOT, first.id, "reject", "Too long.")
    time.sleep(0.002)
    rework = svc.request(ROOT, WEEKDAY, {"topic": "ai"}, revises=first.id, budget=10)
    deliver(svc, "ceo", rework, runs=8)  # 11 runs used in all: past the contract's 10, but 8 of them are the relayed rework's
    text = progress(svc)
    total = f"case total: 11 runs used: 3 by the user's requests, 8 by your relayed rework {rework.id}; 20 handed down (contract: 10 per request)"
    assert text.count(total) == 2  # one per task line
    assert "The runs of your relayed rework are your own spend, not the user's: report them to the user as yours" in text
    assert "exceeds" not in text and "tell the user" not in text
    assert ".." not in text.replace("...", "")  # the sentences join cleanly
    # the rework is delivered and not yet rated by the client; the first one has her verdict
    lines = {line.split("(task ")[1].rstrip(")"): line for line in text.splitlines() if "(task " in line}
    assert "no feedback yet" in lines[rework.id] and "no feedback yet" not in lines[first.id]


def test_progress_lines_of_a_rework_chain_warn_when_the_users_requests_overspend(svc):
    """D-E5-1 (A3): the user's own rework (source "human", budget 2, within the 10 approved) runs 11 runs: the user's requests cost 14 against
    10 approved and no relayed rework is in the chain, so the warning stays, in 0a.2's words, and the line joins its sentences cleanly."""
    first = request(svc, "ai")
    deliver(svc, "ceo", first, runs=3)
    svc.feedback(ROOT, first.id, "reject", "Too long.")
    time.sleep(0.002)
    rework = svc.request(ROOT, WEEKDAY, {"topic": "ai"}, revises=first.id, budget=2, source="human")
    deliver(svc, "ceo", rework, runs=11)
    text = progress(svc)
    assert text.count("case total: 14 runs used of 12 handed down (contract: 10 per request). This case now exceeds the per-request budget of 10: tell the user.") == 2
    assert "tell the user. (task " in text
    assert ".." not in text.replace("...", "")


def test_a_single_request_case_has_no_case_total_line(svc):
    first = request(svc, "ai")
    deliver(svc, "ceo", first)
    assert "case total" not in progress(svc)


# ---------------------------------------------------------------------------- progress and status
def test_progress_tags_service_tasks_and_notes_missing_feedback(svc):
    org = svc
    org.revise_playbook("ceo", "weekly-brief", "first", "r", [], text="Steps.")
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
    org.revise_playbook("ceo", "weekly-brief", "first", "first", [], text="Steps.")
    assert org.messages(ROOT, "inbox") and "Needs you" not in progress(org)
    org.notify(ROOT, "loud", "Needs a decision")
    assert "Needs you: runtime notice" in progress(org)
