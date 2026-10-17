"""Non-waking messages (D2) and orphaned runs of a dead scheduler (D4), ACCEPTANCE.md."""

import os
from orgmcp import core
from orgmcp.core import ROOT, Message
from orgmcp.scheduler import Scheduler

SILENT = dict(echo=lambda _: None)


def true_runner(org, addr, prompt):
    return ["true"], org.dir(addr), dict(os.environ)


def ceo_with_funded_report(org, budget=20, grant=5):
    """ceo has handled its task; it has a report ``ops`` holding ``grant`` unspent runs."""
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=budget)
    org.begin_run("ceo")
    org.end_run("ceo", ok=True)
    org.hire("ceo", "ops", "Ops", "Do ops.")
    org.send("ceo", "ceo/ops", "grant", budget=grant)


# --------------------------------------------------------------- non-waking


def test_wake_flag_roundtrips_and_defaults_to_true(org):
    quiet = org.notify("ceo", "fyi", "x", wake=False)
    loud = org.notify("ceo", "ping", "y")
    assert "wake: false" in (org.dir("ceo") / "inbox" / f"{quiet.id}.md").read_text()
    got = {m.id: m for m in org.messages("ceo", "inbox")}
    assert got[quiet.id].wake is False and got[loud.id].wake is True
    assert "wake" not in loud.meta()  # normal messages stay byte-identical to before
    assert org.unread("ceo") == 1


def test_retire_refund_is_non_waking_and_counts_immediately(org):
    ceo_with_funded_report(org)
    before = org.budget("ceo")
    ret = org.retire_team("ceo", "ops", "done")
    assert ret.refunded == 5
    (note,) = org.messages("ceo", "inbox")
    assert note.wake is False and note.budget == 5 and note.sender == core.RUNTIME
    assert org.unread("ceo") == 0 and org.state("ceo") == "idle"
    assert org.budget("ceo") == before + 5  # budget is derived from files, wake or not


def test_non_waking_note_alone_starts_no_run(org):
    ceo_with_funded_report(org)
    org.retire_team("ceo", "ops", "done")
    sched = Scheduler(org, true_runner, **SILENT)
    assert sched._runnable() == []
    assert sched.tick() is False  # nothing to do, nothing started
    assert org.runs_used("ceo") == 0 and len(org.messages("ceo", "inbox")) == 1


def test_non_waking_note_joins_the_next_real_run(org):
    ceo_with_funded_report(org)
    org.retire_team("ceo", "ops", "done")
    task = org.delegate(ROOT, "ceo", "Next", "g2", "a2", budget=3)
    assert org.unread("ceo") == 1  # only the task wakes
    batch = org.begin_run("ceo")
    assert {m.title for m in batch} == {"Next", "Budget returned from ceo/ops"} and task.id in {m.id for m in batch}
    org.end_run("ceo", ok=True)
    assert org.messages("ceo", "inbox") == [] and len(org.messages("ceo", "read")) == 3


def test_run_started_by_a_real_message_carries_the_held_note(org):
    ceo_with_funded_report(org)
    org.retire_team("ceo", "ops", "done")
    org.delegate(ROOT, "ceo", "Next", "g2", "a2", budget=3)
    prompts = []

    def runner(o, a, p):
        prompts.append(p)
        return ["true"], o.dir(a), dict(os.environ)

    sched = Scheduler(org, runner, **SILENT)
    sched.acquire()
    try:
        for _ in range(100):
            if not sched.tick():
                break
    finally:
        sched.release()
    assert len(prompts) == 1 and "Budget returned from ceo/ops" in prompts[0] and "Next" in prompts[0]
    assert org.runs_used("ceo") == 1 and org.messages("ceo", "inbox") == []


def refund_note(org, to, runs):
    return org.deliver(Message(sender=core.RUNTIME, to=to, type="note", budget=runs, wake=False,
                               title="Budget returned", body="x"))


def test_refund_unpauses_an_agent_paused_for_budget_that_has_waking_mail(org):
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=2)
    org.begin_run("ceo")
    org.end_run("ceo", ok=True)
    org.start_run_log("ceo")
    org.start_run_log("ceo")  # both runs spent
    org.send(ROOT, "ceo", "one more thing")  # waking mail, no budget to handle it
    sched = Scheduler(org, true_runner, **SILENT)
    sched.tick()
    assert org.paused("ceo") == "budget" and org.runs_used("ceo") == 2
    refund_note(org, "ceo", 3)  # does not wake by itself, but the budget counts at once
    assert org.budget("ceo") == 3 and "ceo" in sched._runnable()
    sched.acquire()
    try:
        for _ in range(100):
            if not sched.tick():
                break
    finally:
        sched.release()
    assert org.paused("ceo") is None and org.runs_used("ceo") == 3
    assert org.unread("ceo") == 0 and org.messages("ceo", "inbox") == []


def test_a_refund_alone_lifts_a_budget_pause_without_a_run(org):
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=1)
    org.start_run_log("ceo")
    org.begin_run("ceo")
    org.end_run("ceo", ok=True)
    org.pause("ceo", "budget")
    refund_note(org, "ceo", 2)
    sched = Scheduler(org, true_runner, **SILENT)
    assert sched.tick() is False
    assert org.paused("ceo") is None and org.runs_used("ceo") == 1  # state is honest; still no run


def test_a_failure_pause_is_not_lifted_by_a_refund(org):
    org.pause("ceo", "failures")
    refund_note(org, "ceo", 2)
    Scheduler(org, true_runner, **SILENT).tick()
    assert org.paused("ceo") == "failures"


def test_unreadable_inbox_file_still_counts_as_mail(org):
    (org.dir("ceo") / "inbox" / "broken.md").write_bytes(b"---\nfrom: [unclosed\n---\n\xff\xfe")
    assert org.unread("ceo") == 1
