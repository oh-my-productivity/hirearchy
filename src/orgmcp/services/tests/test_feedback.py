# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

import time

import pytest
from testkit.legacy.orgmcp.core import ROOT, OrgError
from testkit.reflection_world import summarize
from testkit.services_world import ENG, define, deliver, request, svc

from orgmcp.services import FEEDBACK_HEADER


# ----------------------------------------------------------------------------------------- feedback
def test_feedback_is_a_quiet_note_from_the_requester(svc):
    org = svc
    task = request(org)
    with pytest.raises(OrgError, match="wait for the result"):
        org.feedback(ROOT, task.id, "accept")
    deliver(org, "ceo", task)
    with pytest.raises(OrgError, match="verdict must be"):
        org.feedback(ROOT, task.id, "meh")
    with pytest.raises(OrgError, match="rejection needs a note"):
        org.feedback(ROOT, task.id, "reject")
    with pytest.raises(OrgError, match="limit is 1000"):
        org.feedback(ROOT, task.id, "reject", "x" * 1001)
    ceo_unread = org.unread("ceo")
    note = org.feedback(ROOT, task.id, "reject", "No week-over-week changes.")
    assert (note.type, note.to, note.reply_to, note.feedback, note.wake) == ("note", "ceo", task.id, "reject", False)
    assert note.title == f'feedback on "{task.title}": reject'
    assert note.body == FEEDBACK_HEADER + "\n\nNo week-over-week changes."
    assert org.unread("ceo") == ceo_unread and note.budget == 0
    assert "feedback: reject" in org.runtime.message_parser.parse(org.dir("ceo") / "inbox" / f"{note.id}.md").render()
    assert org.feedback(ROOT, task.id, "accept").body == FEEDBACK_HEADER + "\n\naccepted"


def test_only_the_requester_gives_feedback_on_a_service_request(org):
    define(org, owner=ENG, actor="ceo", name="eng-brief")
    org.delegate(ROOT, "ceo", "Project", "g", "c", budget=10)
    task = org.request("ceo", "eng-brief", {"topic": "x"}, budget=3)
    deliver(org, ENG, task)
    with pytest.raises(OrgError, match="not a service request you sent"):
        org.feedback(ROOT, task.id, "accept")  # root did not send it
    with pytest.raises(OrgError, match="not a service request you sent"):
        org.feedback("ceo", "nope", "accept")
    plain = org.delegate(ROOT, "ceo", "Plain", "g", "c", budget=2)
    with pytest.raises(OrgError, match="not a service request you sent"):
        org.feedback(ROOT, plain.id, "accept")  # not a service task
    assert org.feedback("ceo", task.id, "accept").to == ENG


def test_feedback_on_a_rework_belongs_to_the_case_and_the_latest_is_the_final_verdict(svc):
    org = svc
    first = request(org)
    deliver(org, "ceo", first)
    org.feedback(ROOT, first.id, "reject", "Too long.")
    rework = org.delegate(ROOT, "ceo", "Shorten", "g", "c", budget=3, revises=first.id)
    deliver(org, "ceo", rework)
    (case,) = org.runtime.case_history.cases("ceo", "weekly-brief")
    assert case.verdict == "reject"  # feedback on the first task counts for the case
    time.sleep(0.002)
    org.feedback(ROOT, rework.id, "accept")
    (case,) = org.runtime.case_history.cases("ceo", "weekly-brief")
    assert case.verdict == "accept" and case.feedback.reply_to == rework.id
    assert summarize([case]).accept == 1 and summarize([case]).reject == 0
