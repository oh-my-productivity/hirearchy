# mypy: ignore-errors
# A test moved from tests/ by tools/relocate_tests.py: untyped until it is converted. Delete the first line when this file is typed.

import pytest
from testkit.legacy.orgmcp.core import ROOT, Message, OrgError

ENG, QA = "ceo/eng", "ceo/qa"


def run(org, addr):
    org.begin_run(addr)
    org.start_run_log(addr)


def finish(org, addr):
    org.end_run(addr, ok=True)


def total(org):
    """Everything root ever handed out: budget still held + runs used + budget root got back in results."""
    agents = org.agents()
    held = sum(org.budget(a) for a in agents)
    used = sum(org.runs_used(a) for a in agents)
    back = sum(m.budget for m in org.received(ROOT) if m.type == "result")
    return held + used + back


@pytest.fixture
def team(org):
    """root gave ceo 12 runs; ceo gave eng 4 and qa 3. eng and qa have read their tasks and reported: idle, with runs left."""
    org.hire("ceo", "qa", "Tester", "Test things.")
    top = org.delegate(ROOT, "ceo", "Project", "goal", "criteria", budget=12)
    run(org, "ceo")
    a = org.delegate("ceo", ENG, "Build", "goal", "criteria", budget=4)
    b = org.delegate("ceo", QA, "Test", "goal", "criteria", budget=3)
    finish(org, "ceo")
    for addr, task in ((ENG, a), (QA, b)):
        run(org, addr)
        # reported "blocked" keeps the budget with the reporter (a final report would have returned it by itself)
        org.report(addr, task.id, "blocked", "waiting for a decision")
        finish(org, addr)
    run(org, "ceo")  # the blocked results woke ceo; it reads them
    finish(org, "ceo")
    assert (org.budget("ceo"), org.budget(ENG), org.budget(QA)) == (3, 3, 2)
    return top


def test_reclaim_moves_everything_by_default_and_conserves_the_total(team, org):
    before = total(org)
    ceo_before = org.budget("ceo")
    msg = org.reclaim("ceo", "eng")
    assert msg.budget == 3 and msg.sender == ENG and msg.to == "ceo" and msg.wake is False
    assert msg.title == "budget reclaimed by ceo"
    assert org.budget(ENG) == 0 and org.budget("ceo") == ceo_before + 3
    assert total(org) == before  # nothing minted, nothing lost
    # recorded in the report's sent/ (so the arithmetic stays derived) and in the manager's inbox
    assert msg.id in [m.id for m in org.sent(ENG)] and msg.id in [m.id for m in org.messages("ceo", "inbox")]
    assert not org.unread("ceo") and not org.unread(ENG)  # nobody is woken
    assert not org.messages(ENG, "inbox")  # the report received nothing


def test_a_partial_amount_leaves_the_rest_with_the_report(team, org):
    before = total(org)
    msg = org.reclaim("ceo", ENG, 2)  # a full address works too
    assert msg.budget == 2 and org.budget(ENG) == 1 and total(org) == before
    assert org.reclaim("ceo", "eng", 1).budget == 1 and org.budget(ENG) == 0
    with pytest.raises(OrgError, match="no unspent budget"):
        org.reclaim("ceo", "eng")


def test_reclaimed_runs_can_be_handed_to_the_sibling_that_needs_them(team, org):
    """The A4 deadlock: one sibling is out of runs with work, the other holds unspent ones."""
    before = total(org)
    org.reclaim("ceo", "eng")
    task = org.delegate("ceo", QA, "Rework", "goal", "criteria", budget=3, revises=next(
        t.id for t in org.sent("ceo") if t.to == QA
    ))
    assert task.budget == 3 and org.budget(QA) == 2 + 3 and total(org) == before


def test_refuses_more_than_is_available_or_less_than_one(team, org):
    with pytest.raises(OrgError, match="only 3 unspent run"):
        org.reclaim("ceo", "eng", 4)
    for bad in (0, -2):
        with pytest.raises(OrgError, match="at least 1"):
            org.reclaim("ceo", "eng", bad)
    assert org.budget(ENG) == 3


def test_refuses_a_busy_report_and_says_why(team, org):
    org.delegate("ceo", ENG, "More", "goal", "criteria", budget=1)  # unread, wakes eng, and an open task
    with pytest.raises(OrgError, match=r"busy.*1 open task.*1 unread message"):
        org.reclaim("ceo", "eng")
    run(org, ENG)  # running now
    with pytest.raises(OrgError, match="running now"):
        org.reclaim("ceo", "eng")
    assert not [m for m in org.sent(ENG) if m.title.startswith("budget reclaimed")]  # nothing moved


def test_refuses_a_report_with_outstanding_delegations(org):
    org.hire("ceo", "lead", "Lead", "Lead.", can_hire=True)
    org.hire("ceo/lead", "w", "Worker", "work")
    org.delegate(ROOT, "ceo", "P", "goal", "criteria", budget=10)
    run(org, "ceo")
    t = org.delegate("ceo", "ceo/lead", "T", "goal", "criteria", budget=6)
    finish(org, "ceo")
    run(org, "ceo/lead")
    org.delegate("ceo/lead", "ceo/lead/w", "S", "goal", "criteria", budget=2)
    org.report("ceo/lead", t.id, "blocked", "waiting for w")  # no open task left, but the delegation is outstanding
    finish(org, "ceo/lead")
    run(org, "ceo")  # ceo reads the blocked result
    finish(org, "ceo")
    assert not org.open_tasks("ceo/lead") and not org.unread("ceo/lead") and org.budget("ceo/lead") == 3
    with pytest.raises(OrgError, match="1 delegation"):
        org.reclaim("ceo", "lead")


def test_refuses_a_report_with_unread_waking_mail_but_not_with_quiet_mail(team, org):
    org.send("ceo", ENG, "question")
    with pytest.raises(OrgError, match="unread message"):
        org.reclaim("ceo", "eng")
    run(org, ENG)
    finish(org, ENG)  # the question is read
    org.notify(ENG, "fyi", "quiet notice", wake=False)  # held without waking: not a reason to refuse
    left = org.budget(ENG)
    assert left == 2 and org.reclaim("ceo", "eng").budget == left


def test_only_direct_reports_no_cascade(org):
    org.hire("ceo", "lead", "Lead", "Lead.", can_hire=True)
    org.hire("ceo/lead", "w", "Worker", "work")
    org.delegate(ROOT, "ceo", "P", "goal", "criteria", budget=10)
    org.send("ceo", "ceo/lead", "runs", budget=4)
    org.send("ceo/lead", "ceo/lead/w", "runs", budget=2)
    for actor, target in (
        (ROOT, "ceo/lead"),  # a grandchild of root
        (ROOT, "ceo/lead/w"),
        ("ceo", "ceo/lead/w"),  # a grandchild of ceo
        ("ceo/lead/w", "ceo/lead"),  # a report reclaiming from its manager
        ("ceo/lead", "ceo/eng"),  # a cousin
        ("ceo/lead", "ceo/lead"),  # itself
        ("ceo", "ceo"),
        ("ceo", "root"),
        ("ceo", "nobody"),
    ):
        with pytest.raises(OrgError, match="direct reports"):
            org.reclaim(actor, target)
    assert org.budget("ceo/lead/w") == 2 and org.budget("ceo/lead") == 2  # 4 received - 2 handed down


def test_root_reclaims_from_its_direct_report_and_the_runs_leave_the_org(org):
    org.hire(ROOT, "ops", "Ops", "ops")
    org.send(ROOT, "ops", "runs", budget=5)
    with pytest.raises(OrgError, match="unread message"):  # the grant itself is unread mail
        org.reclaim(ROOT, "ops")
    org.begin_run("ops")  # read, no run counted
    org.end_run("ops", ok=True)
    msg = org.reclaim(ROOT, "ops", 2)
    assert msg.to == ROOT and msg.sender == "ops" and msg.budget == 2
    assert org.budget("ops") == 3 and org.budget(ROOT) is None
    assert not org.unread(ROOT)  # quiet: root is the caller
    assert org.reclaim(ROOT, "ops").budget == 3 and org.budget("ops") == 0


def test_redelivery_does_not_count_the_transfer_twice(team, org):
    before = total(org)
    msg = org.reclaim("ceo", "eng")
    ceo_budget = org.budget("ceo")
    assert org.redeliver_orphans() == []  # delivered: nothing to repair
    # crash between the two writes: the sender's copy exists, the manager's does not
    (org.dir("ceo") / "inbox" / f"{msg.id}.md").unlink()
    assert org.budget("ceo") == ceo_budget - 3 and org.budget(ENG) == 0  # charged, not yet credited
    assert org.redeliver_orphans() == [msg.id]
    assert org.budget("ceo") == ceo_budget and org.budget(ENG) == 0 and total(org) == before
    assert org.redeliver_orphans() == []
    # the delivered copy is counted once however the manager's boxes move it: inbox -> inflight -> read
    org.begin_run("ceo")
    assert org.budget("ceo") == ceo_budget
    org.end_run("ceo", ok=False)  # a failed run puts it back; the retry may find it again
    assert org.budget("ceo") == ceo_budget
    org.end_run("ceo", ok=True)
    assert org.budget("ceo") == ceo_budget and sum(m.budget for m in org.received("ceo") if m.id == msg.id) == 3


def test_the_note_is_marked_and_read_back_from_the_file(team, org):
    msg = org.reclaim("ceo", "eng")
    loaded = Message.load(org.dir("ceo") / "inbox" / f"{msg.id}.md")
    assert loaded.budget == 3 and loaded.wake is False and loaded.sender == ENG
    assert "budget reclaimed by ceo" in loaded.render() and "on ceo/eng's behalf" in loaded.body


def test_a_second_reclaim_after_the_first_finds_nothing(team, org):
    org.reclaim("ceo", "eng")
    with pytest.raises(OrgError, match="no unspent budget"):
        org.reclaim("ceo", "eng")
