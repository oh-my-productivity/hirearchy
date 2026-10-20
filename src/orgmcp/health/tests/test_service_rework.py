# mypy: ignore-errors
# A test moved from tests/ by tools/relocate_tests.py: untyped until it is converted. Delete the first line when this file is typed.

from testkit.legacy.orgmcp.core import ROOT
from testkit.services_world import ENG, deliver, request, svc, work

from orgmcp.health import agent_health

WEEKDAY = "weekly-brief"


# ----------------------------------------------------------------------------------------- 6. health
def first_pass_and_client_rework(org, rounds=3):
    """root requests a service from ceo; ceo has eng review it; root sends the delivery back; ceo has eng re-check."""
    first = org.request(ROOT, WEEKDAY, {"topic": "ai"}, budget=20)
    work(org, "ceo")
    review = org.delegate("ceo", ENG, "Review", "Review the brief", "a verdict", budget=2)
    org.end_run("ceo", ok=True)
    work(org, ENG)
    org.report(ENG, review.id, "done", "PASS")
    org.end_run(ENG, ok=True)
    work(org, "ceo")
    org.report("ceo", first.id, "done", "Delivered.", lessons="Fine.")
    org.end_run("ceo", ok=True)
    rework = org.request(ROOT, WEEKDAY, {"topic": "ai"}, revises=first.id, budget=10)  # the client rejects
    work(org, "ceo")
    prev, checks = review, []
    for i in range(rounds):
        prev = org.delegate("ceo", ENG, f"Re-check {i}", "Review again", "a verdict", budget=1, revises=prev.id)
        checks.append(prev)
    return first, rework, checks


def test_reworks_that_come_from_the_client_of_a_service_case_are_not_held_against_the_agent(svc):
    first_pass_and_client_rework(svc)
    eng, ceo = agent_health(svc, ENG), agent_health(svc, "ceo")
    assert (eng.tasks_received, eng.rework, eng.client_rework) == (4, 0, 3)
    assert (ceo.rework, ceo.client_rework) == (0, 1)
    assert "low_quality" not in eng.flags and "low_quality" not in ceo.flags


def test_the_same_chain_without_a_service_still_counts_as_rework(svc):
    svc.delegate(ROOT, "ceo", "Plan", "Plan", "a plan", budget=20)
    work(svc, "ceo")
    prev = svc.delegate("ceo", ENG, "Review", "Review", "a verdict", budget=1)
    for i in range(3):
        prev = svc.delegate("ceo", ENG, f"Re-check {i}", "Review again", "a verdict", budget=1, revises=prev.id)
    eng = agent_health(svc, ENG)
    assert (eng.rework, eng.client_rework) == (3, 0) and "low_quality" in eng.flags


def test_a_rework_in_the_first_pass_of_a_service_request_still_counts(svc):
    request(svc, "ai")
    work(svc, "ceo")
    first = svc.delegate("ceo", ENG, "Write", "Write", "a draft", budget=1)
    svc.delegate("ceo", ENG, "Fix", "Fix it", "a draft", budget=1, revises=first.id)  # the lead's own quality control
    eng = agent_health(svc, ENG)
    assert (eng.rework, eng.client_rework) == (1, 0)


def test_the_rework_a_client_sends_after_a_failed_service_request_is_not_exempt(svc):
    first = request(svc, "ai")
    deliver(svc, "ceo", first, status="failed")
    svc.request(ROOT, WEEKDAY, {"topic": "ai"}, revises=first.id, budget=2)
    ceo = agent_health(svc, "ceo")
    assert (ceo.rework, ceo.client_rework) == (1, 0)
