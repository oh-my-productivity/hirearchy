# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

import time

import pytest
from testkit.reach.hirearchy.core import ROOT, OrgError
from testkit.reflection_world import summarize
from testkit.services_world import ENG, define, deliver, request, svc, write_version

from hirearchy.services import FEEDBACK_HEADER, LINK_HEADER


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
    with pytest.raises(OrgError, match="is not a task you sent"):
        org.feedback(ROOT, task.id, "accept")  # root did not send it
    with pytest.raises(OrgError, match="not a service request you sent"):
        org.feedback("ceo", "nope", "accept")
    plain = org.delegate(ROOT, "ceo", "Plain", "g", "c", budget=2)
    with pytest.raises(OrgError, match="has no result yet"):
        org.feedback(ROOT, plain.id, "accept")  # a one-off task of root's: it takes a verdict once it has a result
    assert org.feedback("ceo", task.id, "accept").to == ENG


def test_feedback_on_a_rework_belongs_to_the_case_and_the_latest_is_the_final_verdict(svc):
    org = svc
    first = request(org)
    deliver(org, "ceo", first)
    org.feedback(ROOT, first.id, "reject", "Too long.")
    rework = request(org, revises=first.id, budget=3, source="human")  # root sends a request back with `request` (`delegate` is refused, P4)
    deliver(org, "ceo", rework)
    (case,) = org.runtime.case_history.cases("ceo", "weekly-brief")
    assert case.verdict == "reject"  # feedback on the first task counts for the case
    time.sleep(0.002)
    org.feedback(ROOT, rework.id, "accept")
    (case,) = org.runtime.case_history.cases("ceo", "weekly-brief")
    assert case.verdict == "accept" and case.feedback.reply_to == rework.id
    assert summarize([case]).accept == 1 and summarize([case]).reject == 0


# ----------------------------------------------------------------------------------------- confirms after an answer (P2, one answer per rejection)
V1 = ["At most 600 words", "Every factual claim has a source URL"]
NEW_RULE = "The memo starts with a Summary line"
YES = "Yes, add it."


def rejected(org, words="Always start with a Summary line."):
    task = request(org)
    deliver(org, "ceo", task)
    return task, org.feedback(ROOT, task.id, "reject", words, source="human")


def links_on(org, rejection):
    return [m for m in org.sent(ROOT) if m.reply_to == rejection.id and m.criterion]


def test_confirms_after_an_answering_version_with_a_link_is_answered(svc):
    org = svc
    task, no = rejected(org)
    org.define_service(ROOT, "ceo", "weekly-brief", add_acceptance=[NEW_RULE], answers=no.id, about="C1", words=YES)
    (link,) = links_on(org, no)
    with pytest.raises(OrgError) as info:
        org.feedback(ROOT, task.id, "reject", "Also this.", source="human", criterion=["C3"], confirms=no.id)
    assert str(info.value) == (
        f"refused: rejection {no.id} was answered by contract v2 of `weekly-brief` (define_service(..., answers=\"{no.id}\"); CLI: define-service "
        f"--answers) and its link {link.id} records the user's yes: one rejection gets one answer. A different answer needs a new rejection and its "
        "question. Nothing was recorded."
    )
    assert links_on(org, no) == [link]  # nothing was recorded
    other_task, other = rejected(org, "Another thing entirely.")
    assert org.feedback(ROOT, other_task.id, "reject", "No.", source="human", criterion=["none"], confirms=other.id).criterion == "none"  # unanswered: as ever


def test_confirms_after_an_answering_version_without_a_link_takes_only_the_recovery_link(svc):
    org = svc
    task, no = rejected(org)
    write_version(org, 2, [*V1, NEW_RULE, "Names its week"], answers=no.id, about="C1", words=YES)  # the contract answers it; its link was never written
    recovery = (
        f"refused: rejection {no.id} was answered by contract v2 of `weekly-brief`, and its link is missing (its write failed). The only link it "
        f'still takes is that one: feedback(task_id="{task.id}", verdict="reject", confirms="{no.id}", criterion=["C3", "C4"], source="human", '
        "note=<the user's answer, verbatim>) (CLI: --confirms, --criterion, --source human, --note). Nothing was recorded."
    )
    for wrong in ({"criterion": ["C3"]}, {"criterion": ["none"]}, {"criterion": ["C3", "C4"], "source": "relayed"}, {"criterion": ["C4", "C3", "C1"]}):
        with pytest.raises(OrgError) as info:
            org.feedback(ROOT, task.id, "reject", YES, **{"source": "human", **wrong}, confirms=no.id)
        assert str(info.value) == recovery
    link = org.feedback(ROOT, task.id, "reject", YES, source="human", criterion=["c4", "C3"], confirms=no.id)  # the same ids as a set
    assert (link.criterion, link.source, link.reply_to) == ("C4, C3", "human", no.id)
    assert org.runtime.service_evidence.confirmed("ceo", "weekly-brief") == frozenset({"C3", "C4"})  # the amendment is confirmed by its own link
    with pytest.raises(OrgError, match=f"^refused: rejection {no.id} was answered by contract v2 of `weekly-brief` \\(define_service"):
        org.feedback(ROOT, task.id, "reject", YES, source="human", criterion=["C3", "C4"], confirms=no.id)  # one link only


def test_a_second_confirms_without_a_contract_change_is_still_accepted(svc):
    """0a.1: the user may correct an answer; the latest human link decides what the rejection is about. Only an answering contract version closes it."""
    org = svc
    task, no = rejected(org)
    first = org.feedback(ROOT, task.id, "reject", "A one-off.", source="human", criterion=["none"], confirms=no.id)
    second = org.feedback(ROOT, task.id, "reject", "On reflection, about C1.", source="human", criterion=["C1"], confirms=no.id)
    assert (first.criterion, second.criterion) == ("none", "C1") and links_on(org, no) == [first, second]


def test_the_confirms_link_note_is_byte_identical(svc):
    org = svc
    task, no = rejected(org)
    link = org.feedback(ROOT, task.id, "reject", YES, source="human", criterion=["C1", "C2"], confirms=no.id)
    assert (link.sender, link.to, link.type, link.wake, link.source, link.criterion, link.reply_to, link.feedback) == (
        ROOT, "ceo", "note", False, "human", "C1, C2", no.id, None,
    )
    assert link.title == f'criterion link on "{task.title}": C1, C2'
    assert link.body == LINK_HEADER.format(confirms=no.id) + "\n\n" + YES
    assert link.body == (
        f"The client says what their rejection {no.id} was about, for reflection only: it does not change any task's acceptance criteria or outcome."
        "\n\nYes, add it."
    )


# ----------------------------------------------------------------------------------------- feedback on a one-off task (design 8.1, 8.3)
def one_off(org, to="ceo", status="done", title="Plain"):
    """Root's task without a service, answered by ``to``."""
    task = org.delegate(ROOT, to, title, "g", "c", budget=2)
    deliver(org, to, task, status=status)
    return task


def test_root_records_a_verdict_on_a_one_off_task_as_a_quiet_note(svc):
    org = svc
    task = one_off(org)
    ceo_unread = org.unread("ceo")
    note = org.feedback(ROOT, task.id, "reject", "  Too long.  ", source="human")
    assert (note.sender, note.to, note.type, note.reply_to, note.feedback, note.wake) == (ROOT, "ceo", "note", task.id, "reject", False)
    assert (note.source, note.criterion, note.budget) == ("human", None, 0)
    assert note.title == f'feedback on "{task.title}": reject'
    assert note.body == FEEDBACK_HEADER + "\n\nToo long."
    assert org.unread("ceo") == ceo_unread
    accepted = org.feedback(ROOT, task.id, "accept")
    assert accepted.body == FEEDBACK_HEADER + "\n\naccepted" and accepted.source == "relayed"  # the default of a root verdict


def test_a_one_off_verdict_on_a_blocked_or_failed_result_is_recorded(svc):
    org = svc
    for status in ("blocked", "failed"):
        task = one_off(org, status=status, title=f"Plain {status}")
        assert org.feedback(ROOT, task.id, "reject", "No.", source="human").reply_to == task.id


def test_a_one_off_task_without_a_result_keeps_todays_text(svc):
    org = svc
    task = org.delegate(ROOT, "ceo", "Plain", "g", "c", budget=2)
    with pytest.raises(OrgError) as info:
        org.feedback(ROOT, task.id, "accept")
    assert str(info.value) == f"task {task.id} has no result yet: wait for the result, then give feedback."


def test_a_one_off_verdict_with_criterion_or_confirms_is_refused_one_off_no_link(svc):
    org = svc
    task = one_off(org)
    refusal = (
        f"refused: {task.id} is a one-off task: it has no contract, so its verdict names no criterion and answers no rejection. "
        "Leave out criterion and confirms (CLI: --criterion, --confirms). Nothing was recorded."
    )
    for extra in ({"criterion": ["none"]}, {"criterion": ["C1"]}, {"confirms": "20261017T000000000000-root-abcd"}):
        with pytest.raises(OrgError) as info:
            org.feedback(ROOT, task.id, "reject", "No.", source="human", **extra)
        assert str(info.value) == refusal
    assert not [m for m in org.sent(ROOT) if m.feedback]  # nothing was recorded


def test_a_one_off_verdict_on_a_retired_assignees_task_is_refused_one_off_gone(svc):
    org = svc
    org.hire(ROOT, "ops", "Operations", "Run ops.")
    task = one_off(org, to="ops")
    org.retire(ROOT, "ops", "closed")
    with pytest.raises(OrgError) as info:
        org.feedback(ROOT, task.id, "reject", "No.", source="human")
    assert str(info.value) == f"refused: ops, who did {task.id}, was retired, so the verdict has no one to tell. Nothing was recorded."
    assert not [m for m in org.sent(ROOT) if m.feedback]


def test_an_unknown_task_id_is_refused_one_off_unknown_with_roots_newest_ten_with_a_result(svc):
    org = svc
    with pytest.raises(OrgError) as info:
        org.feedback(ROOT, "nope", "accept")
    assert str(info.value) == (
        "refused: nope is not a task you sent: feedback records the user's verdict on one of your service requests or one-off tasks that has a "
        "result. Your newest: none. Nothing was recorded."
    )
    open_task = org.delegate(ROOT, "ceo", "Still open", "g", "c", budget=2)  # no result: not listed
    ids = []
    for n in range(6):
        service_task = request(org, topic=f"t{n}")
        deliver(org, "ceo", service_task)
        ids.append(service_task.id)
        ids.append(one_off(org, title=f"Plain {n}").id)
    with pytest.raises(OrgError) as info:
        org.feedback(ROOT, "nope", "accept")
    newest = ", ".join(sorted(ids, reverse=True)[:10])
    assert open_task.id not in newest and len(ids) == 12
    assert str(info.value) == (
        "refused: nope is not a task you sent: feedback records the user's verdict on one of your service requests or one-off tasks that has a "
        f"result. Your newest: {newest}. Nothing was recorded."
    )


def test_a_reject_needs_a_note_and_the_note_limit_holds_for_one_offs(svc):
    org = svc
    task = one_off(org)
    with pytest.raises(OrgError, match="rejection needs a note"):
        org.feedback(ROOT, task.id, "reject", "  ")
    with pytest.raises(OrgError, match="limit is 1000"):
        org.feedback(ROOT, task.id, "reject", "x" * 1001)
    with pytest.raises(OrgError, match="verdict must be"):
        org.feedback(ROOT, task.id, "meh")


def test_an_agents_feedback_on_a_non_service_task_keeps_todays_refusal(svc):
    org = svc
    org.send(ROOT, "ceo", "runs", budget=5)
    delegated = org.delegate("ceo", ENG, "Plain", "g", "c", budget=1)
    deliver(org, ENG, delegated)
    with pytest.raises(OrgError) as info:
        org.feedback("ceo", delegated.id, "accept")
    assert str(info.value) == f"{delegated.id} is not a service request you sent. Feedback is for requests made with `request`. Yours: none"
