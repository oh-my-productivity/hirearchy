# mypy: ignore-errors
# A test moved from tests/ by tools/relocate_tests.py: untyped until it is converted. Delete the first line when this file is typed.

from datetime import timedelta

import pytest
from testkit.legacy.orgmcp.core import ROOT, OrgError, utcnow

from orgmcp.progress import progress

ENG = "ceo/eng"


def run(org, addr):
    org.begin_run(addr)
    org.start_run_log(addr)


def read(org, addr):
    org.begin_run(addr)
    org.end_run(addr, ok=True)


def lines(org, *args, **kw):
    return progress(org, *args, **kw).splitlines()


@pytest.fixture
def task(org):
    return org.delegate(ROOT, "ceo", "Write the report", "goal", "criteria", budget=8)


def test_no_tasks(org):
    assert progress(org) == "No open tasks."


def test_a_task_nobody_has_started_is_working_with_unread_work(org, task):
    (line,) = lines(org)
    assert line.startswith('"Write the report": working. unread work: ceo. runs 0 of 8.')
    assert "last activity" in line and line.endswith(f"(task {task.id})")


def test_a_running_agent_is_named_with_the_runs_used_so_far(org, task):
    run(org, "ceo")  # in flight
    (line,) = lines(org)
    assert '"Write the report": working. running: ceo. runs 1 of 8.' in line


def test_working_covers_the_whole_subtree(org, task):
    read(org, "ceo")
    org.delegate("ceo", ENG, "Sub", "goal", "criteria", budget=3)  # eng has unread work
    (line,) = lines(org)
    assert "working. unread work: ceo/eng." in line


def test_waiting_on_the_agent_that_holds_the_work(org, task):
    run(org, "ceo")
    org.delegate("ceo", ENG, "Sub", "goal", "criteria", budget=3)
    org.end_run("ceo", ok=True)
    read(org, ENG)  # eng has read its task and nothing is running
    (line,) = lines(org)
    assert '"Write the report": waiting on ceo/eng.' in line and "running" not in line
    org.pause(ENG, "budget")
    assert "waiting on ceo/eng (paused: budget)." in lines(org)[0]


def test_stalled_when_the_assignee_itself_holds_the_task(org, task):
    read(org, "ceo")
    assert '"Write the report": stalled (ceo has not reported and nothing is running).' in lines(org)[0]
    org.pause("ceo", "failures")
    assert "stalled (ceo is paused: failures)." in lines(org)[0]


def test_blocked_shows_the_reason_and_asks_the_human(org, task):
    run(org, "ceo")
    org.report("ceo", task.id, "blocked", "Need the 2025 sales figures.\nMore detail here.")
    first, second = lines(org)
    assert '"Write the report": blocked: Need the 2025 sales figures. runs' in first
    assert "More detail" not in first
    assert second.startswith('Needs you: blocked result from ceo "Write the report": Need the 2025 sales figures (message')


def test_done_shows_status_artifacts_and_returned_runs(org, task):
    run(org, "ceo")
    org.write("ceo", "ceo/work/report.md", "# Report\nsome words here")
    org.write("ceo", "ceo/work/notes.md", "notes")
    org.report("ceo", task.id, "done", "All good.", ["ceo/work/report.md", "ceo/work/notes.md"])
    (line,) = lines(org)  # a done result is not something that needs the human
    assert '"Write the report": done.' in line
    assert "runs 1 of 8 (7 returned)." in line
    assert "artifacts: ceo/work/report.md, ceo/work/notes.md." in line
    assert "words" not in line  # the runtime's annotations are dropped


def test_failed_shows_failed_and_asks_the_human(org, task):
    run(org, "ceo")
    org.report("ceo", task.id, "failed", "The source site is gone.")
    first, second = lines(org)
    assert '"Write the report": failed.' in first and "no artifacts" in first
    assert second.startswith("Needs you: failed result from ceo") and "source site is gone" in second


def test_one_task_by_id_in_any_state_and_unknown_ids_are_refused(org, task):
    other = org.delegate(ROOT, ENG, "Other", "goal", "criteria", budget=2)
    assert len(lines(org)) == 2
    (line,) = lines(org, other.id)
    assert line.startswith('"Other": working.')
    with pytest.raises(OrgError, match="no task nope"):
        progress(org, "nope")
    run(org, "ceo")
    org.report("ceo", task.id, "done", "ok")
    old = utcnow() + timedelta(days=3)
    assert progress(org, task.id, now=old).startswith('"Write the report": done.')


def test_finished_tasks_are_listed_for_a_day_then_only_as_the_last_one(org, task):
    run(org, "ceo")
    org.report("ceo", task.id, "done", "ok")
    assert lines(org)[0].startswith('"Write the report": done.')
    later = progress(org, now=utcnow() + timedelta(days=3)).splitlines()
    assert later[0] == "No open tasks." and later[1].startswith('"Write the report": done.')


def test_open_tasks_come_first_and_old_finished_ones_are_dropped(org, task):
    run(org, "ceo")
    org.report("ceo", task.id, "done", "ok")
    org.delegate(ROOT, ENG, "Newer", "goal", "criteria", budget=2)
    out = progress(org, now=utcnow() + timedelta(days=3))
    assert out.startswith('"Newer": working.') and "Write the report" not in out


def test_last_activity_is_measured_from_the_newest_message_or_run(org, task):
    run(org, "ceo")
    (line,) = lines(org, now=utcnow() + timedelta(hours=2))
    assert "last activity 2h ago" in line


def test_notes_and_runtime_notices_are_listed_and_quiet_ones_are_not(org):
    org.send("ceo", ROOT, "I am out of budget and need 3 more runs.\nPlease advise.", title="Budget request")
    org.notify(ROOT, "ceo is out of budget", "`ceo` has 1 unread message(s) but no budget left, so it is paused.")
    org.notify(ROOT, "refund", "returned", wake=False)
    out = lines(org)
    assert out[0] == "No open tasks."
    assert out[1].startswith('Needs you: note from ceo "Budget request": I am out of budget and need 3 more runs (message')
    assert out[2].startswith('Needs you: runtime notice "ceo is out of budget": `ceo` has 1 unread')
    assert len(out) == 3


def test_read_messages_no_longer_ask_for_attention(org):
    org.send("ceo", ROOT, "question", title="Q")
    assert len(lines(org)) == 2
    org.begin_run(ROOT)
    org.end_run(ROOT, ok=True)
    assert lines(org) == ["No open tasks."]


def test_a_retired_assignee_shows_as_failed(org, task):
    org.retire(ROOT, "ceo", "done with it")  # retire closes its open tasks as failed
    assert '"Write the report": failed.' in lines(org)[0]


def test_runs_are_counted_per_task_even_when_an_agent_has_several(org, task):
    run(org, "ceo")
    org.report("ceo", task.id, "done", "ok")
    org.end_run("ceo", ok=True)
    second = org.delegate(ROOT, "ceo", "Second", "goal", "criteria", budget=3)
    run(org, "ceo")
    run(org, "ceo")
    assert "runs 2 of 3." in lines(org, second.id)[0]
    assert "runs 1 of 8 (7 returned)." in lines(org, task.id)[0]
