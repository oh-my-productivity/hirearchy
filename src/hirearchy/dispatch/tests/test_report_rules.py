# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

import time

import pytest
from testkit.reach.hirearchy.core import ROOT, OrgError
from testkit.reflection_world import lessons_of

ENG = "ceo/eng"
CRITERIA = "exactly 33 words; a non-author reviews the final text"


def drain(org, addr):
    org.begin_run(addr)
    org.end_run(addr, ok=True)


@pytest.fixture
def blocked(org):
    """root -> ceo task; ceo delegated to eng (serving it); eng reported done; ceo reported the root task blocked."""
    task = org.delegate(ROOT, "ceo", "Strict blurb", "Write it.", CRITERIA, budget=20)
    drain(org, "ceo")
    sub = org.delegate("ceo", ENG, "Draft blurb", "Draft it.", "exactly 33 words", budget=4)
    first = org.report("ceo", task.id, "blocked", "review judged a stale draft; no budget to rework")
    result = org.report(ENG, sub.id, "done", "33 words")
    return task, sub, first, result


def results_for(org, task):
    return sorted((m for m in org.received(ROOT) if m.type == "result" and m.reply_to == task.id), key=lambda m: m.id)


# ------------------------------------------------------------------ report
def test_blocked_can_be_re_reported_and_the_new_result_supersedes_it(org, blocked):
    task, _, first, _ = blocked
    assert first.supersedes is None
    second = org.report("ceo", task.id, "done", "reviewed the final text; all criteria met")
    assert second.supersedes == first.id and second.status == "done"
    stored = org.find_received(ROOT, second.id)
    assert stored.supersedes == first.id
    assert "supersedes: " + first.id in stored.render()
    assert f"supersedes: {first.id}" in stored.path.read_text()
    assert [m.id for m in results_for(org, task)] == [first.id, second.id]


def test_second_re_report_after_a_resolved_blocker_is_refused(org, blocked):
    task, *_ = blocked
    org.report("ceo", task.id, "done", "all criteria met")
    with pytest.raises(OrgError, match="already reported done.*final.*rule 6.*`send`"):
        org.report("ceo", task.id, "done", "again")
    with pytest.raises(OrgError, match="already reported done"):
        org.report("ceo", task.id, "blocked", "or not")


def test_blocked_may_be_re_reported_blocked_once_per_prior_blocked(org, blocked):
    task, _, first, _ = blocked
    second = org.report("ceo", task.id, "blocked", "still waiting for a reviewer")
    assert second.supersedes == first.id
    third = org.report("ceo", task.id, "failed", "giving up")
    assert third.supersedes == second.id
    with pytest.raises(OrgError, match="already reported failed.*final"):
        org.report("ceo", task.id, "done", "no")


@pytest.mark.parametrize("status", ["done", "failed"])
def test_done_and_failed_are_final(org, status):
    task = org.delegate(ROOT, "ceo", "Job", "g", "a", budget=5)
    drain(org, "ceo")
    org.report("ceo", task.id, status, "x")
    with pytest.raises(OrgError, match=f"already reported {status}.*final"):
        org.report("ceo", task.id, "done", "y")
    assert all(m.supersedes is None for m in org.sent("ceo"))


# ------------------------------------------------------------------------------------------ 3. feedback
SERVICE = dict(
    description="A brief.", acceptance=["At most 600 words"], budget=10,
    deliverable={"description": "one markdown file", "format": "markdown", "max_words": 600},
    inputs=[{"name": "topic", "description": "subject", "required": True}],
)


@pytest.fixture
def svc(org):
    org.define_service(ROOT, "ceo", "brief", **SERVICE)
    return org


def work(org, addr, runs=1):
    batch = org.begin_run(addr)
    for _ in range(runs):
        org.start_run_log(addr)
        time.sleep(0.002)
    return batch


# ------------------------------------------------------------------------------------------ 4. blocked lessons
def test_a_blocked_report_on_a_service_request_requires_lessons(svc):
    task = svc.request(ROOT, "brief", {"topic": "ai"})
    work(svc, "ceo")
    with pytest.raises(OrgError, match="pass `lessons`.*blocked"):
        svc.report("ceo", task.id, "blocked", "Cannot read the notes.")
    res = svc.report("ceo", task.id, "blocked", "Cannot read the notes.", lessons="Reviewer had no inputs.")
    assert lessons_of(res) == "Reviewer had no inputs."
    plain = svc.delegate(ROOT, "ceo", "Plain", "g", "c", budget=2)
    assert svc.report("ceo", plain.id, "blocked", "Waiting.").status == "blocked"  # plain tasks: still optional
