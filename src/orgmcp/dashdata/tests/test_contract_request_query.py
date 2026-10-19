"""Contract of ``RequestQuery``: root's requests, newest first, with what ``progress`` says of each; the line and the trace of one. Over the strict ports and over the dashboard's."""

from __future__ import annotations

from pathlib import Path

import pytest

from orgmcp.dashdata import RequestQuery
from orgmcp.dashdata.testing import IMPLEMENTATIONS, DashWorld
from orgmcp.observability.testing import stamp

from ._support import make_world, team


@pytest.fixture(params=IMPLEMENTATIONS[RequestQuery], ids=lambda factory: factory.__name__)
def w(request: pytest.FixtureRequest, tmp_path: Path) -> DashWorld:
    made = make_world(request, tmp_path)
    assert isinstance(made.requests, RequestQuery)
    return made


def test_an_organization_without_requests_has_none(w: DashWorld) -> None:
    assert w.requests.requests() == []


def test_a_request_is_a_row_with_what_progress_says_of_it(w: DashWorld) -> None:
    team(w)
    task = w.obs.send("root", "ceo", "task", 10, title="Ship it", budget=12, trace="self")
    w.facts.states[task.id] = ("working", "running: ceo")
    w.facts.runs[task.id] = "runs 3 of 12"
    w.facts.activity = stamp(150)
    (row,) = w.requests.requests()
    assert (row.id, row.title, row.assignee, row.state, row.klass, row.who) == (task.id, "Ship it", "ceo", "working", "working", "running: ceo")
    assert (row.runs_used, row.runs_given, row.runs_text, row.last_activity_s) == (3, 12, "runs 3 of 12", 50.0)
    assert row.created == stamp(10) and row.needs_you == 0 and row.artifacts == [] and row.service is None and row.revises is None


def test_the_class_of_a_request_is_the_first_word_of_its_state(w: DashWorld) -> None:
    team(w)
    states = {"waiting on ops/deploy (paused: x)": "waiting", "blocked: need a decision": "blocked", "stalled": "stalled", "done": "done", "failed": "failed"}
    for n, state in enumerate(states):
        task = w.obs.send("root", "ceo", "task", 10 + n, title=f"T{n}", budget=1, trace="self")
        w.facts.states[task.id] = (state, "")
    assert [r.klass for r in w.requests.requests()] == list(reversed(list(states.values())))


def test_requests_come_newest_first(w: DashWorld) -> None:
    team(w)
    for n, title in enumerate(("Old", "Middle", "New")):
        w.obs.send("root", "ceo", "task", 10 + n, title=title, budget=1, trace="self")
    assert [r.title for r in w.requests.requests()] == ["New", "Middle", "Old"]


def test_only_the_tasks_root_gave_are_requests(w: DashWorld) -> None:
    team(w)
    w.obs.send("root", "ceo", "note", 10, title="A note")
    w.obs.send("ceo", "ceo/analyst", "task", 11, title="Not root's", budget=1)
    assert w.requests.requests() == []


def test_a_finished_request_lists_its_artifacts(w: DashWorld) -> None:
    team(w)
    task = w.obs.send("root", "ceo", "task", 10, title="Ship it", budget=3, trace="self", box="read")
    result = w.obs.send("ceo", "root", "result", 20, title="Ship it", status="done", reply_to=task.id, trace=task.id, box="read")
    w.facts.states[task.id] = ("done", "")
    w.facts.delivered[result.id] = ["ceo/work/report.md"]
    (row,) = w.requests.requests()
    assert row.klass == "done" and row.artifacts == ["ceo/work/report.md"]


def test_a_request_that_needs_the_user_is_marked(w: DashWorld) -> None:
    team(w)
    task = w.obs.send("root", "ceo", "task", 10, title="Ship it", budget=3, trace="self", box="read")
    question = w.obs.send("ceo", "root", "result", 20, title="Need a decision", status="blocked", reply_to=task.id, trace=task.id)
    w.obs.waiting.entries.append((question.id, "Needs you: blocked result from ceo"))
    snap = w.snapshots.snapshot()
    (row,) = w.requests.requests(snap)
    assert row.needs_you == 1


def test_a_request_whose_state_cannot_be_told_does_not_hide_the_others(w: DashWorld) -> None:
    team(w)
    odd = w.obs.send("root", "ceo", "task", 10, title="Odd", budget=1, trace="self")
    w.obs.send("root", "ceo", "task", 11, title="Fine", budget=1, trace="self")
    w.facts.broken.add(odd.id)
    rows = {r.title: r for r in w.requests.requests()}
    assert rows["Odd"].state == "? (OrgError)" and rows["Odd"].runs_text == "runs ?" and rows["Odd"].last_activity_s is None
    assert rows["Fine"].state == "working"


def test_the_answer_is_kept_while_nothing_changes_and_made_again_when_something_does(w: DashWorld) -> None:
    team(w)
    task = w.obs.send("root", "ceo", "task", 10, title="Ship it", budget=1, trace="self")
    snap = w.snapshots.snapshot()
    first = w.requests.requests(snap)
    w.facts.states[task.id] = ("done", "")
    assert w.requests.requests(snap) is first  # kept for a few seconds while the signature is the same
    w.clock.advance(6)
    assert w.requests.requests(snap) is not first and w.requests.requests(snap)[0].state == "done"


def test_the_progress_line_of_a_request_is_the_first_line_of_the_report(w: DashWorld) -> None:
    w.reporter.text = "first line (task t1)\nsecond line"
    assert w.requests.request_line("t1") == "first line (task t1)"
    assert w.reporter.calls[-1][:3] == ("progress", "t1", w.shown.now)


def test_a_progress_report_that_fails_is_told_not_raised(w: DashWorld) -> None:
    w.reporter.text = ""  # nothing to say: no first line
    assert w.requests.request_line("t1").startswith("(no progress line:")


def test_the_trace_of_an_unknown_request_is_a_note(w: DashWorld) -> None:
    assert w.requests.trace_text("nope").startswith("no trace: no message nope")


def test_the_trace_of_a_request_is_rendered_without_escape_codes(w: DashWorld) -> None:
    team(w)
    task = w.obs.send("root", "ceo", "task", 10, title="Ship it", budget=3, trace="self", box="read")
    text = w.requests.trace_text(task.id)
    assert "Ship it" in text and "\x1b" not in text
