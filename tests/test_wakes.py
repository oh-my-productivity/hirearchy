"""Non-waking messages (D2) and orphaned runs of a dead scheduler (D4), ACCEPTANCE.md."""

import os

from orgmcp import core
from orgmcp.core import ROOT
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


def test_unreadable_inbox_file_still_counts_as_mail(org):
    (org.dir("ceo") / "inbox" / "broken.md").write_bytes(b"---\nfrom: [unclosed\n---\n\xff\xfe")
    assert org.unread("ceo") == 1


# ------------------------------------------------- orphans of a dead scheduler
import json  # noqa: E402
import signal  # noqa: E402
import subprocess  # noqa: E402
import time  # noqa: E402

import pytest  # noqa: E402

from orgmcp.scheduler import _start_time, judge_orphan  # noqa: E402
