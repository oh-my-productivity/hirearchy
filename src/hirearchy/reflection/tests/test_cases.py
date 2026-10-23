# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

import time

from testkit.reach.hirearchy.core import ROOT
from testkit.services_world import contract_meta, define, deliver, request, svc, work

from hirearchy.reflection import stats_by_version, summarize

WEEKDAY = "weekly-brief"


def rejected_then_accepted(org, *, reject="Sam's 'before Friday' needs a date.", accept="this version is right", runs=(2, 3)):
    """A request, rejected after its delivery, sent back with ``request(revises=...)``, delivered again and accepted."""
    first = request(org, "ai")
    deliver(org, "ceo", first, runs=runs[0], lessons="Clean run; no issues.")
    org.feedback(ROOT, first.id, "reject", reject)
    time.sleep(0.002)
    rework = org.request(ROOT, WEEKDAY, {"topic": "ai"}, revises=first.id, budget=6)
    deliver(org, "ceo", rework, runs=runs[1], lessons="Applied the date rule.")
    time.sleep(0.002)
    org.feedback(ROOT, rework.id, "accept", accept)
    return first, rework


# ------------------------------------------------------------------------------- 1. every verdict stays
def test_a_case_keeps_every_verdict_in_order_with_the_task_it_was_given_on(svc):
    first, rework = rejected_then_accepted(svc)
    (case,) = svc.runtime.case_history.cases("ceo", WEEKDAY)
    assert [(v.verdict, v.note, v.task_id, v.step) for v in case.verdicts] == [
        ("reject", "Sam's 'before Friday' needs a date.", first.id, 0),
        ("accept", "this version is right", rework.id, 1),
    ]
    assert all(v.created is not None for v in case.verdicts)
    assert case.verdict == "accept" and case.rejected and case.accepted_after_reject
    assert case.feedback.reply_to == rework.id  # the final verdict is the latest note


def test_a_verdict_lists_its_link_notes_in_id_order(svc):
    """F-E4-7: the link notes that reply to a verdict (every tier) travel with it, so a cited link-note id can be resolved."""
    task = request(svc, "ai")
    deliver(svc, "ceo", task)
    no = svc.feedback(ROOT, task.id, "reject", "Too long.", source="human")
    plain = request(svc, "chips")
    deliver(svc, "ceo", plain)
    svc.feedback(ROOT, plain.id, "reject", "Too short.", source="human")
    time.sleep(0.002)
    first = svc.feedback(ROOT, task.id, "reject", "I read it as C1.", source="relayed", criterion=["C1"], confirms=no.id)
    time.sleep(0.002)
    second = svc.feedback(ROOT, task.id, "reject", "No: C2.", source="human", criterion=["C2"], confirms=no.id)
    cases = {c.id: c for c in svc.runtime.case_history.cases("ceo", WEEKDAY)}
    (verdict,) = cases[task.id].verdicts
    assert [m.id for m in verdict.link_notes] == [first.id, second.id]
    (other,) = cases[plain.id].verdicts
    assert other.link_notes == ()


def test_lesson_sources_parallel_lessons(svc):
    """Each lesson carries the ``source`` of the task its result answers, so the digest can mark the ones a relayed rework wrote (4.4)."""
    first = request(svc, "ai")
    deliver(svc, "ceo", first, lessons="One.")
    svc.feedback(ROOT, first.id, "reject", "Too long.", source="human")
    human = svc.request(ROOT, WEEKDAY, {"topic": "ai"}, revises=first.id, source="human")
    deliver(svc, "ceo", human, lessons="Two.")
    relayed = svc.request(ROOT, WEEKDAY, {"topic": "ai"}, revises=human.id)  # no source: the assistant's own rework is relayed
    deliver(svc, "ceo", relayed, lessons="Three.")
    (case,) = svc.runtime.case_history.cases("ceo", WEEKDAY)
    assert case.lessons == ["One.", "Two.", "Three."]
    assert case.lesson_sources == ["", "human", "relayed"]
    assert len(case.lesson_sources) == len(case.lesson_ids) == len(case.lessons)


def test_stats_keep_the_final_counts_and_say_how_many_accepts_came_after_a_reject(svc):
    rejected_then_accepted(svc)
    plain = request(svc, "chips")
    deliver(svc, "ceo", plain)
    svc.feedback(ROOT, plain.id, "accept")
    bad = request(svc, "bio")
    deliver(svc, "ceo", bad)
    svc.feedback(ROOT, bad.id, "reject", "Too long.")
    items = svc.runtime.case_history.cases("ceo", WEEKDAY)
    total = summarize(items)
    assert (total.accept, total.reject, total.accept_after_reject) == (2, 1, 1)
    assert total.line().endswith("feedback 2 accept (1 after a reject), 1 reject")
    record = svc.runtime.service_reports.services_text(ROOT)
    assert "feedback 2 accept (1 after a reject), 1 reject" in record


def test_stats_per_playbook_version_carry_the_after_a_reject_count(svc):
    rejected_then_accepted(svc)
    (v0,) = stats_by_version(svc.runtime.case_history.cases("ceo", WEEKDAY)).values()
    assert v0.line().endswith("feedback 1 accept (1 after a reject), 0 reject")


def test_a_case_rejected_twice_ends_as_a_reject_and_shows_both_verdicts(svc):
    first = request(svc, "ai")
    deliver(svc, "ceo", first)
    svc.feedback(ROOT, first.id, "reject", "No summary.", source="human")
    time.sleep(0.002)
    rework = svc.request(ROOT, WEEKDAY, {"topic": "ai"}, revises=first.id, budget=4)
    deliver(svc, "ceo", rework)
    svc.feedback(ROOT, rework.id, "reject", "Still no summary.", source="human")
    (case,) = svc.runtime.case_history.cases("ceo", WEEKDAY)
    assert case.verdict == "reject" and not case.accepted_after_reject
    assert 'client feedback: reject R1 "No summary." -> reject R2 "Still no summary."' in svc.runtime.reflection_digest.reflection_digest("ceo", WEEKDAY)
    assert summarize([case]).line().endswith("feedback 0 accept, 1 reject")


def test_a_long_verdict_history_is_cut_to_the_latest_ones(svc):
    first = request(svc, "ai")
    deliver(svc, "ceo", first)
    task = first
    for i in range(5):
        svc.feedback(ROOT, task.id, "reject", f"problem {i}")
        time.sleep(0.002)
        task = svc.request(ROOT, WEEKDAY, {"topic": "ai"}, revises=task.id, budget=2)
        deliver(svc, "ceo", task)
    line = svc.runtime.reflection_digest.reflection_digest("ceo", WEEKDAY)
    assert "client feedback: … -> reject" in line and "problem 4" in line and "problem 0" not in line


# ------------------------------------------------------------------------- cases, stats, digest
def test_cases_group_rework_chains_and_derive_runs_budget_and_lessons(svc):
    org = svc
    first = request(org, "ai")
    deliver(org, "ceo", first, runs=2, lessons="First pass was thin.")
    rework = request(org, "ai", revises=first.id, budget=4)
    deliver(org, "ceo", rework, runs=1, lessons="Added sources.")
    second = request(org, "chips")
    work(org, "ceo", 1)
    one, two = org.runtime.case_history.cases("ceo", "weekly-brief")
    assert one.id == first.id and [t.id for t in one.tasks] == [first.id, rework.id]
    assert (one.state, one.reworks, one.playbook, one.budget, one.runs) == ("done", 1, 0, 14, 3)
    assert one.lessons == ["First pass was thin.", "Added sources."] and one.result.reply_to == rework.id
    assert one.finished is not None and one.feedback is None
    assert (two.id, two.state, two.reworks, two.finished) == (second.id, "open", 0, None)
    assert two.runs == 1
    assert one.title == "weekly-brief: ai"


def test_a_blocked_case_is_not_finished_and_a_failed_one_counts_as_failed(svc):
    org = svc
    a, b = request(org, "a"), request(org, "b")
    work(org, "ceo")
    org.report("ceo", a.id, "blocked", "Need data.", lessons="Input was missing.")
    org.report("ceo", b.id, "failed", "Could not.", lessons="Source was down.")
    org.end_run("ceo", ok=True)
    blocked, failed = org.runtime.case_history.cases("ceo", "weekly-brief")
    assert (blocked.state, blocked.finished) == ("blocked", None) and failed.state == "failed"
    stats = summarize([blocked, failed])
    assert (stats.requests, stats.done, stats.failed, stats.open) == (2, 0, 1, 1)


def test_stats_per_playbook_version_and_the_one_line_summary(svc):
    org = svc
    a = request(org, "a")
    deliver(org, "ceo", a, runs=2)
    org.feedback(ROOT, a.id, "reject", "Bad.")
    org.revise_playbook("ceo", "weekly-brief", "Better steps.", "case a rejected", [])
    b = request(org, "b")
    deliver(org, "ceo", b, runs=1)
    org.feedback(ROOT, b.id, "accept")
    c = request(org, "c")
    deliver(org, "ceo", c, status="failed", runs=3)
    all_cases = org.runtime.case_history.cases("ceo", "weekly-brief")
    per = stats_by_version(all_cases)
    assert sorted(per) == [0, 1]
    v0, v1 = per[0], per[1]
    assert (v0.requests, v0.done, v0.reject, v0.avg_runs) == (1, 1, 1, 2.0)
    assert (v1.requests, v1.done, v1.failed, v1.accept, v1.avg_runs) == (2, 1, 1, 1, 2.0)
    assert v1.line() == "2 request(s): 1 done, 1 failed, 0 open; 0 reworked; avg 2 runs; feedback 1 accept, 0 reject"
    total = summarize(all_cases)
    assert total.requests == 3 and total.reworked == 0


def test_a_service_defined_again_after_a_delivery_continues_its_cases(svc):
    """Design 5.10 (Rule C): a service retired after a request that has a result and defined again is the same service, so its earlier request is
    a case of it again; the contract is v2 with the old ``created`` (a copy none of whose requests has a result starts fresh: test_contract_case_history)."""
    org = svc
    old = request(org)
    deliver(org, "ceo", old)
    org.feedback(ROOT, old.id, "accept", "dropped", source="relayed")  # a service is retired only after the verdict on its delivery (design 5.2a)
    created = contract_meta(org)[0]["created"]
    org.retire_service(ROOT, "ceo", "weekly-brief", "redo")
    time.sleep(0.002)
    define(org)
    assert [c.id for c in org.runtime.case_history.cases("ceo", "weekly-brief")] == [old.id]
    meta = contract_meta(org)[0]
    assert meta["version"] == 2 and meta["created"] == created
