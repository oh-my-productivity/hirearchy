# mypy: ignore-errors
# A test moved from tests/ by tools/relocate_tests.py: untyped until it is converted. Delete the first line when this file is typed.

import time

from testkit.legacy.orgmcp.core import ROOT
from testkit.services_world import deliver, request, svc, work

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


def test_the_digest_shows_the_rejection_with_her_words_and_then_the_accept(svc):
    rejected_then_accepted(svc)
    digest = svc.runtime.reflection_digest.reflection_digest("ceo", WEEKDAY)
    assert 'client feedback: reject "Sam\'s \'before Friday\' needs a date." -> accept "this version is right"' in digest
    # the client's verdicts come before the lessons
    assert digest.index("client feedback:") < digest.index("lessons")
    # the lesson of the rework was written after the reject: the digest says so
    assert 'lessons (written after the reject: check it against her words): "Applied the date rule."' in digest


def test_a_bare_accept_has_no_quotes_and_a_clean_case_is_unchanged(svc):
    first = request(svc, "ai")
    deliver(svc, "ceo", first, lessons="Fine.")
    svc.feedback(ROOT, first.id, "accept")
    digest = svc.runtime.reflection_digest.reflection_digest("ceo", WEEKDAY)
    assert "; client feedback: accept; lessons: " in digest and "written after" not in digest
    assert "feedback 1 accept, 0 reject" in digest and "after a reject" not in digest


def test_digest_is_none_without_new_evidence(svc):
    org = svc
    assert org.runtime.reflection_digest.reflection_digest("ceo", "weekly-brief") is None  # no cases
    request(org)
    work(org, "ceo")
    assert org.runtime.reflection_digest.reflection_digest("ceo", "weekly-brief") is None  # an open case is no evidence yet


def test_digest_shows_finished_cases_feedback_and_stats(svc):
    org = svc
    task = request(org, "ai")
    deliver(org, "ceo", task, runs=2, lessons="Sources first.")
    digest = org.runtime.reflection_digest.reflection_digest("ceo", "weekly-brief")  # no playbook: any finished case is evidence
    assert digest is not None and task.id in digest and "done" in digest and "2 of 10 runs" in digest
    assert 'lessons: "Sources first."' in digest and "By playbook version:" in digest and "- v0: 1 request(s): 1 done" in digest
    org.feedback(ROOT, task.id, "reject", "No week-over-week changes.")
    digest = org.runtime.reflection_digest.reflection_digest("ceo", "weekly-brief")
    assert 'client feedback: reject "No week-over-week changes."' in digest


def test_a_revision_resets_the_evidence_and_later_feedback_counts_as_new(svc):
    org = svc
    task = request(org)
    deliver(org, "ceo", task)
    assert org.runtime.reflection_digest.reflection_digest("ceo", "weekly-brief") is not None
    org.revise_playbook("ceo", "weekly-brief", "Steps v1.", "first draft")
    assert org.runtime.reflection_digest.reflection_digest("ceo", "weekly-brief") is None  # everything so far is older than v1
    time.sleep(0.002)
    org.feedback(ROOT, task.id, "reject", "Missing sources.")  # feedback after the revision: new evidence
    digest = org.runtime.reflection_digest.reflection_digest("ceo", "weekly-brief")
    assert digest is not None and "Missing sources." in digest and task.id in digest
    org.revise_playbook("ceo", "weekly-brief", "Steps v2.", "added sources")
    assert org.runtime.reflection_digest.reflection_digest("ceo", "weekly-brief") is None
    nxt = request(org)
    deliver(org, "ceo", nxt, runs=1)
    assert org.runtime.reflection_digest.reflection_digest("ceo", "weekly-brief") is not None  # a case finished after v2


def test_digest_is_compact(svc):
    org = svc
    for i in range(9):
        t = request(org, f"topic {i} " + "x" * 60)
        deliver(org, "ceo", t, lessons="L" * 790)
    digest = org.runtime.reflection_digest.reflection_digest("ceo", "weekly-brief")
    assert len(digest) <= 3000
    assert digest.count("\n- case ") <= 6 and "- v0: 9 request(s)" in digest
