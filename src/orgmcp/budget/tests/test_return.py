# mypy: ignore-errors
# A test moved from tests/ by tools/relocate_tests.py: untyped until it is converted. Delete the first line when this file is typed.

import pytest
from testkit.legacy.orgmcp.core import ROOT, Message, Org, OrgError

ENG = "ceo/eng"


def run(org, addr):
    """One run of ``addr``: it reads its mail and consumes one run of budget (left open: nothing ends it)."""
    org.begin_run(addr)
    org.start_run_log(addr)


def finish(org, addr):
    org.end_run(addr, ok=True)


def results(org, addr):
    return [m for m in org.received(addr) if m.type == "result"]


def total(org):
    """Everything root ever handed out: budget still held + runs used + budget root got back in results."""
    agents = org.agents()
    held = sum(org.budget(a) for a in agents)
    used = sum(org.runs_used(a) for a in agents)
    back = sum(m.budget for m in org.received(ROOT) if m.type == "result")
    return held + used + back


def assign(org, to, budget, title="Work"):
    return org.delegate(ROOT if "/" not in to else Org.parent(to), to, title, "goal", "criteria", budget=budget)


# ------------------------------------------------------------------ return with the result
def test_done_returns_everything_that_is_left(org):
    task = assign(org, "ceo", 5)
    run(org, "ceo")
    msg = org.report("ceo", task.id, "done", "ok")
    assert msg.budget == 4 and msg.status == "done"  # 5 received - 1 run
    assert org.budget("ceo") == 0
    assert total(org) == 5


def test_failed_returns_too(org):
    task = assign(org, "ceo", 3)
    run(org, "ceo")
    assert org.report("ceo", task.id, "failed", "could not").budget == 2


def test_blocked_returns_nothing_and_a_later_final_report_returns(org):
    task = assign(org, "ceo", 6)
    run(org, "ceo")
    blocked = org.report("ceo", task.id, "blocked", "waiting for a decision")
    assert blocked.budget == 0 and org.budget("ceo") == 5  # kept: the re-report needs a run
    finish(org, "ceo")
    run(org, "ceo")
    final = org.report("ceo", task.id, "done", "now ok")
    assert final.supersedes == blocked.id and final.budget == 4
    assert org.budget("ceo") == 0 and total(org) == 6


def test_a_run_with_nothing_left_returns_zero(org):
    task = assign(org, "ceo", 1)
    run(org, "ceo")
    msg = org.report("ceo", task.id, "done", "ok")
    assert msg.budget == 0 and "budget" not in msg.meta()
    assert org.budget("ceo") == 0


def test_the_result_says_it_returns_runs(org):
    task = assign(org, "ceo", 5)
    run(org, "ceo")
    msg = org.report("ceo", task.id, "done", "ok")
    assert "returns 4 run(s)" in msg.render() and "budget:" not in msg.render()
    assert [m.budget for m in org.messages(ROOT, "inbox")] == [4]  # it is in root's inbox, parsed back from the file
    note = org.send(ROOT, "ceo", "extra", budget=2)
    assert "budget: 2 runs" in note.render()  # grants read as before


def test_cascade_through_two_levels_conserves_the_total(org):
    top = assign(org, "ceo", 10)
    run(org, "ceo")
    sub = org.delegate("ceo", ENG, "Sub", "goal", "criteria", budget=4)
    assert org.budget("ceo") == 10 - 1 - 4
    finish(org, "ceo")
    run(org, ENG)
    run(org, ENG)
    eng_result = org.report(ENG, sub.id, "done", "ok")
    assert eng_result.budget == 2 and org.budget(ENG) == 0  # 4 - 2 runs
    assert org.budget("ceo") == 5 + 2 and total(org) == 10
    finish(org, ENG)

    run(org, "ceo")  # the result wakes ceo
    ceo_result = org.report("ceo", top.id, "done", "ok")
    assert ceo_result.budget == 10 - 4 + 2 - 2  # received - handed down + returned - its two runs
    assert org.budget("ceo") == 0 and org.budget(ENG) == 0
    assert total(org) == 10  # nothing minted, nothing lost
    assert [m.budget for m in results(org, ROOT)] == [ceo_result.budget]


def test_no_return_while_another_task_is_open(org):
    first, second = assign(org, "ceo", 4, "A"), assign(org, "ceo", 4, "B")
    run(org, "ceo")
    assert org.report("ceo", first.id, "done", "ok").budget == 0
    assert org.budget("ceo") == 7
    last = org.report("ceo", second.id, "done", "ok")
    assert last.budget == 7 and org.budget("ceo") == 0 and total(org) == 8


def test_no_return_while_another_task_is_blocked_and_can_be_re_reported(org):
    first, second = assign(org, "ceo", 4, "A"), assign(org, "ceo", 4, "B")
    run(org, "ceo")
    org.report("ceo", first.id, "blocked", "stuck")
    assert org.report("ceo", second.id, "done", "ok").budget == 0
    assert org.report("ceo", first.id, "done", "unstuck").budget == 7


def test_no_return_while_a_delegation_is_outstanding(org):
    task = assign(org, "ceo", 6)
    run(org, "ceo")
    org.delegate("ceo", ENG, "Sub", "goal", "criteria", budget=2)
    msg = org.report("ceo", task.id, "done", "reporting early")
    assert msg.budget == 0 and org.budget("ceo") == 3  # the reserve for the delegation's result stays


def test_no_return_while_mail_waits_for_a_run(org):
    task = assign(org, "ceo", 5)
    run(org, "ceo")
    org.send(ROOT, "ceo", "one more thing")  # arrives during the run: it will wake ceo again
    assert org.report("ceo", task.id, "done", "ok").budget == 0
    assert org.budget("ceo") == 4


def test_a_non_waking_note_does_not_hold_the_return_back(org):
    task = assign(org, "ceo", 5)
    run(org, "ceo")
    org.notify("ceo", "fyi", "no run needed", wake=False)
    assert org.report("ceo", task.id, "done", "ok").budget == 4


def test_rework_gets_its_own_fresh_budget(org):
    first = assign(org, "ceo", 4)
    run(org, "ceo")
    org.report("ceo", first.id, "done", "draft")
    finish(org, "ceo")
    again = org.delegate(ROOT, "ceo", "Work", "goal", "criteria", budget=3, revises=first.id)
    assert org.budget("ceo") == 3  # the rework carries the budget the assigner chose
    run(org, "ceo")
    assert org.report("ceo", again.id, "done", "better").budget == 2


def test_only_the_parent_can_receive_a_return(org):
    org.send(ROOT, ENG, "grant", budget=5)
    task = org.send(ROOT, ENG, "do it", type="task")  # a task from root to a deep agent: not eng's parent
    run(org, ENG)
    assert org.report(ENG, task.id, "done", "ok").budget == 0
    assert org.budget(ENG) == 4


# -------------------------------------------------- redelivery (at-least-once runs) cannot double-return
def test_a_second_final_report_is_refused_and_returns_nothing_more(org):
    task = assign(org, "ceo", 5)
    run(org, "ceo")
    org.report("ceo", task.id, "done", "ok")
    with pytest.raises(OrgError, match="final"):
        org.report("ceo", task.id, "done", "again")
    assert total(org) == 5 and len(results(org, ROOT)) == 1


def test_a_redelivered_batch_cannot_return_twice(org):
    assign(org, "ceo", 8)
    run(org, "ceo")
    sub = org.delegate("ceo", ENG, "Sub", "goal", "criteria", budget=3)
    finish(org, "ceo")
    run(org, ENG)
    org.report(ENG, sub.id, "done", "ok")
    org.end_run(ENG, ok=False)  # the run crashed after reporting: its batch comes back
    run(org, ENG)
    with pytest.raises(OrgError):
        org.report(ENG, sub.id, "done", "ok")
    # the redelivered run is charged like any run (at-least-once), but it returns nothing: the total is unchanged
    assert org.budget(ENG) <= 0 and total(org) == 8
    assert org.redeliver_orphans() == []  # the result reached ceo: nothing to deliver again
    assert org.budget("ceo") == 8 - 3 - 1 + 2 and len(results(org, "ceo")) == 1


def test_a_result_lost_between_the_two_writes_is_charged_once_and_credited_once(org):
    assign(org, "ceo", 8)
    run(org, "ceo")
    sub = org.delegate("ceo", ENG, "Sub", "goal", "criteria", budget=3)
    finish(org, "ceo")
    run(org, ENG)
    msg = org.report(ENG, sub.id, "done", "ok")
    (org.dir("ceo") / "inbox" / f"{msg.id}.md").unlink()  # crash: sender's copy exists, recipient's does not
    assert org.budget(ENG) == 0 and org.budget("ceo") == 8 - 3 - 1  # charged, not yet credited
    assert org.redeliver_orphans() == [msg.id]
    assert org.redeliver_orphans() == []
    assert org.budget("ceo") == 8 - 3 - 1 + 2 and total(org) == 8


def test_old_messages_mean_what_they_always_meant(org):
    """A result written before budget returns existed has no budget; budgets derived from it are unchanged."""
    task = assign(org, "ceo", 5)
    run(org, "ceo")
    old = Message(
        sender="ceo", to=ROOT, type="result", body="## Summary\nok", reply_to=task.id, status="done", title=task.title,
        id="20200101T000000000000-ceo-aaaa",
    )
    org.deliver(old)  # exactly what the previous `report` wrote
    assert Message.load(org.dir("ceo") / "sent" / f"{old.id}.md").budget == 0
    assert org.budget("ceo") == 4 and "returns" not in old.render()


# ------------------------------------------------------------------------ voluntary return
def test_an_agent_can_return_budget_to_its_parent(org):
    org.send(ROOT, "ceo", "grant", budget=10)
    org.send("ceo", ENG, "grant", budget=6)
    note = org.send(ENG, "ceo", "I do not need these", budget=4)
    assert note.type == "note" and note.budget == 4
    assert org.budget(ENG) == 2 and org.budget("ceo") == 10 - 6 + 4
    assert total_held(org) == 10


def total_held(org):
    return sum(org.budget(a) + org.runs_used(a) for a in org.agents())


def test_a_manager_cannot_return_what_its_delegations_need(org):
    org.hire("ceo", "ops", "Ops", "Run.", can_hire=True)
    org.hire("ceo/ops", "dev", "Dev", "Code.")
    org.send(ROOT, "ceo", "grant", budget=10)
    org.send("ceo", "ceo/ops", "grant", budget=5)
    org.delegate("ceo/ops", "ceo/ops/dev", "t", "g", "c", budget=2)  # ops: 3 left, 1 reserved for dev's result
    with pytest.raises(OrgError, match="not enough budget"):
        org.send("ceo/ops", "ceo", "give back", budget=3)
    org.send("ceo/ops", "ceo", "give back", budget=2)
    assert org.budget("ceo/ops") == 1 and org.budget("ceo") == 5 + 2


def test_budget_still_goes_nowhere_but_down_and_to_the_parent(org):
    org.hire("ceo", "ops", "Ops", "Run.")
    org.send(ROOT, "ceo", "grant", budget=10)
    org.send("ceo", ENG, "grant", budget=5)
    with pytest.raises(OrgError, match="direct reports, or returned to your parent"):
        org.send(ENG, "ceo/ops", "to my sibling", budget=1)
    org.hire(ROOT, "other", "Other", "x")
    with pytest.raises(OrgError):
        org.send(ENG, "other", "somewhere else", budget=1)
    with pytest.raises(OrgError, match="negative"):
        org.send(ENG, "ceo", "mint", budget=-1)
    with pytest.raises(OrgError, match="not enough budget"):
        org.send(ENG, "ceo", "more than I have", budget=6)
    org.send(ENG, "ceo", "plain note, no budget")


def test_a_return_raises_the_parents_budget(org):
    org.send(ROOT, "ceo", "grant", budget=2)
    org.send("ceo", ENG, "grant", budget=2)
    assert org.budget("ceo") == 0
    org.send(ENG, "ceo", "have one back", budget=1)
    assert org.budget("ceo") == 1
