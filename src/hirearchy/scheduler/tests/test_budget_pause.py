# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

import os

from testkit.reach.hirearchy import core
from testkit.reach.hirearchy.core import ROOT, Message

from testkit.scheduler_loop import loop_over, runnable_of

SILENT = dict(echo=lambda _: None)


def true_runner(org, addr, prompt):
    return ["true"], org.dir(addr), dict(os.environ)


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
    sched = loop_over(org, true_runner, **SILENT)
    sched.tick()
    assert org.paused("ceo") == "budget" and org.runs_used("ceo") == 2
    refund_note(org, "ceo", 3)  # does not wake by itself, but the budget counts at once
    assert org.budget("ceo") == 3 and "ceo" in runnable_of(org, sched)
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
    sched = loop_over(org, true_runner, **SILENT)
    assert sched.tick() is False
    assert org.paused("ceo") is None and org.runs_used("ceo") == 1  # state is honest; still no run


def test_a_failure_pause_is_not_lifted_by_a_refund(org):
    org.pause("ceo", "failures")
    refund_note(org, "ceo", 2)
    loop_over(org, true_runner, **SILENT).tick()
    assert org.paused("ceo") == "failures"
