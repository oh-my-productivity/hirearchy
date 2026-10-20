# mypy: ignore-errors
# A test moved from tests/ by tools/relocate_tests.py: untyped until it is converted. Delete the first line when this file is typed.

import os

from testkit.legacy.orgmcp.core import ROOT
from testkit.mail_world import scheduler_over


def true_runner(org, addr, prompt):
    return ["true"], org.dir(addr), dict(os.environ)


def ceo_with_funded_report(org, budget=20, grant=5):
    """ceo has handled its task; it has a report ``ops`` holding ``grant`` unspent runs."""
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=budget)
    org.begin_run("ceo")
    org.end_run("ceo", ok=True)
    org.hire("ceo", "ops", "Ops", "Do ops.")
    org.send("ceo", "ceo/ops", "grant", budget=grant)


def test_non_waking_note_alone_starts_no_run(org):
    ceo_with_funded_report(org)
    org.retire_team("ceo", "ops", "done")
    sched = scheduler_over(org, true_runner)
    assert org.runtime.runnable_query.runnable(exclude=set()) == []
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

    sched = scheduler_over(org, runner)
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
