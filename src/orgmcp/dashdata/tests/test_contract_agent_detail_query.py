"""Contract of ``AgentDetailQuery``: everything about one agent - overview, messages, run log, memory, charter, events. Over the strict ports and over the dashboard's."""

from __future__ import annotations

from pathlib import Path

import pytest

from orgmcp.dashdata import AgentDetailQuery, doc_text
from orgmcp.dashdata.testing import IMPLEMENTATIONS, DashWorld
from orgmcp.kernel import ROOT

from ._support import make_world, running_scheduler, stamp, team


@pytest.fixture(params=IMPLEMENTATIONS[AgentDetailQuery], ids=lambda factory: factory.__name__)
def w(request: pytest.FixtureRequest, tmp_path: Path) -> DashWorld:
    made = make_world(request, tmp_path)
    assert isinstance(made.details, AgentDetailQuery)
    return made


def test_an_agent_that_is_not_there_says_so(w: DashWorld) -> None:
    detail = w.details.agent_detail("ghost")
    assert detail.row is None and doc_text(detail.overview) == "ghost: no such agent (any more)\n"
    assert (detail.messages, detail.memory, detail.charter, detail.events) == ([], "", "", [])


def test_the_overview_of_an_agent_is_its_state_and_what_it_holds(w: DashWorld) -> None:
    team(w)
    w.obs.send("root", "ceo/writer", "task", 10, title="Write it", budget=2, box="read")
    text = doc_text(w.details.agent_detail("ceo/writer").overview)
    assert "state    ◆ working on 1 task(s)" in text and "parent   ceo" in text and "role     Worker" in text
    assert "budget   2 run(s) left; 0 run(s) used" in text and 'Open tasks (1)\n"Write it"  from root  budget 2' in text
    assert "Delegated, outstanding (0)\nnone" in text and "(no events for this agent)" in text


def test_the_acceptance_criteria_of_a_task_are_listed_and_cut_at_six(w: DashWorld) -> None:
    team(w)
    criteria = "\n".join(f"- criterion {n}" for n in range(8))
    w.obs.send("root", "ceo/writer", "task", 10, title="Write it", budget=2, box="read", body=f"Goal.\n\n## Acceptance criteria\n{criteria}\n")
    text = doc_text(w.details.agent_detail("ceo/writer").overview)
    assert "    · criterion 0" in text and "    · criterion 5" in text and "criterion 6" not in text and "    · … 2 more" in text


def test_a_running_agent_has_its_batch_in_the_overview(w: DashWorld) -> None:
    team(w)
    running_scheduler(w)
    w.obs.send("root", "ceo", "task", 10, title="Busy", budget=1)
    w.obs.begin_run("ceo")
    w.obs.running("ceo", w.obs.run_log("ceo", 0))
    w.obs.send("root", "ceo", "note", 150, title="While you run")
    text = doc_text(w.details.agent_detail("ceo").overview)
    assert "Current run\nelapsed 3m20s\nbatch of 1 message(s):\n  task \"Busy\" from root" in text
    assert "1 more message(s) wait for the next run" in text


def test_a_queued_and_a_paused_agent_say_why(w: DashWorld) -> None:
    team(w)
    w.obs.send("root", "ops", "note", 10, title="Hello")
    assert "Queued\n1 unread message(s) wait: scheduler is not running" in doc_text(w.details.agent_detail("ops").overview)
    w.obs.pause("ops", "broken")
    paused = w.details.agent_detail("ops", w.snapshots.snapshot()).overview
    assert "Paused\npaused: broken\n1 unread message(s) wait; nothing starts until it is resumed" in doc_text(paused)


def test_an_agent_out_of_budget_says_what_it_waits_for(w: DashWorld) -> None:
    team(w)
    w.obs.budgets.held["ops"] = 0
    w.obs.send("root", "ops", "note", 10, title="Hello")
    assert "Out of budget\nno runs left; 1 unread message(s) wait until budget is granted" in doc_text(w.details.agent_detail("ops").overview)


def test_the_delegations_of_an_agent_say_where_they_stand(w: DashWorld) -> None:
    team(w)
    w.obs.send("ceo", "ceo/analyst", "task", 10, title="Analyse", budget=2, box="read")
    text = doc_text(w.details.agent_detail("ceo").overview)
    assert 'Delegated, outstanding (1)\n"Analyse" -> ceo/analyst  [working on 1 task(s)]  budget 2' in text


def test_the_overview_of_root_has_what_needs_it_and_its_requests(w: DashWorld) -> None:
    team(w)
    w.obs.waiting.entries.append(("m1", "Needs you: note from ceo"))
    task = w.obs.send("root", "ceo", "task", 10, title="Ship it", budget=3, trace="self")
    w.facts.states[task.id] = ("waiting on ceo", "")
    text = doc_text(w.details.agent_detail(ROOT).overview)
    assert "You (root)\n4 agent(s); 0 running, 1 queued\nscheduler stopped" in text and "Needs you (1)\nNeeds you: note from ceo" in text
    assert 'Requests\n"Ship it" -> ceo: waiting on ceo. runs 0 of 0' in text


def test_root_has_no_runs_and_its_charter_is_the_rules(w: DashWorld) -> None:
    detail = w.details.agent_detail(ROOT)
    assert detail.runlog.note == "root is the human: no runs" and detail.charter.startswith("root is the human: no charter.\n\nORG.md rules:")
    assert "mission: test" in detail.charter


def test_the_messages_of_an_agent_come_newest_first_from_every_box(w: DashWorld) -> None:
    team(w)
    w.obs.send("root", "ceo", "task", 10, title="First", budget=1, box="read")
    w.obs.send("root", "ceo", "note", 20, title="Second")
    w.obs.send("ceo", "ops", "note", 30, title="Third")
    detail = w.details.agent_detail("ceo")
    assert [(m.title, m.box, m.direction) for m in detail.messages] == [("Third", "sent", "out"), ("Second", "inbox", "in"), ("First", "read", "in")]
    assert detail.messages[0].id > detail.messages[-1].id and detail.messages[-1].sender == ROOT and detail.messages[-1].when == stamp(10)


def test_a_message_is_shown_whole(w: DashWorld) -> None:
    team(w)
    w.obs.send("root", "ceo", "note", 10, title="Scope", body="Please also cover the Asian market.")
    row = next(m for m in w.details.agent_detail("ceo").messages if m.title == "Scope")
    assert "Please also cover the Asian market." in w.details.message_text(row)


def test_a_message_that_is_gone_or_cannot_be_read_is_told(w: DashWorld) -> None:
    team(w)
    w.obs.send("root", "ceo", "note", 10, title="Scope")
    row = next(m for m in w.details.agent_detail("ceo").messages if m.title == "Scope")
    assert row.path is not None
    row.path.unlink()
    assert "gone" in w.details.message_text(row) or "cannot read" in w.details.message_text(row)


def test_memory_and_charter_are_the_files_or_a_note(w: DashWorld) -> None:
    team(w)
    detail = w.details.agent_detail("ceo")
    assert detail.memory == "(no memory yet)" and "role: Worker" in detail.charter
    (w.root / "ceo" / "MEMORY.md").write_text("Remember \x1b[31mthis\x1b[0m.\n", encoding="utf-8")
    detail = w.details.agent_detail("ceo")
    assert detail.memory == "Remember this.\n" and "role: Worker" in detail.charter


def test_an_agent_that_has_not_run_has_no_run_log(w: DashWorld) -> None:
    team(w)
    assert w.details.agent_detail("ceo").runlog.note == "this agent has not run yet"
    assert w.details.run_log("ceo", False).note == "this agent has not run yet"


def test_the_run_log_of_a_finished_run_shows_its_exit_line(w: DashWorld) -> None:
    team(w)
    stem = w.obs.run_log("ops", 20, "# exit 1 after 10s\n", end=30)
    log = w.details.run_log("ops", False)
    assert not log.running and log.rel == f"ops/runs/{stem}.log" and log.header[0] == "started 2026-10-18 10:00:20Z"
    assert log.header[-1] == "exit 1 after 10s"


def test_the_run_log_of_a_running_agent_follows_the_registry(w: DashWorld) -> None:
    team(w)
    running_scheduler(w)
    w.obs.send("root", "ops", "task", 10, title="Busy", budget=1)
    w.obs.begin_run("ops")
    stem = w.obs.run_log("ops", 20)
    w.obs.running("ops", stem)
    detail = w.details.agent_detail("ops")
    assert detail.runlog.running and detail.runlog.header[-1] == "still running" and detail.row is not None and detail.row.kind == "running"


def test_the_events_of_an_agent_are_listed_and_told_as_lines(w: DashWorld) -> None:
    team(w)
    w.obs.tool(100, "ceo", "inbox")
    w.obs.tool(110, "ops", "inbox")
    w.obs.tool(120, "ceo", "delegate", ok=False, error="not enough budget")
    w.snapshots.snapshot()
    detail = w.details.agent_detail("ceo")
    assert [(e["kind"], e.get("tool")) for e in detail.events] == [("tool.call", "inbox"), ("tool.call", "delegate")]
    assert [x.text for x in detail.activity] == ["10:01:40 inbox ok 5ms", "10:02:00 delegate REFUSED: not enough budget"]
    assert [x.error for x in detail.activity] == [False, True]
    assert w.details.agent_detail("ceo", raw=True).activity[0].text.startswith("10:01:40 mcp ceo tool.call inbox")


def test_the_message_of_a_batch_is_told_by_its_title(w: DashWorld) -> None:
    team(w)
    note = w.obs.send("root", "ceo", "note", 10, title="Scope change")
    assert w.details.message_lookup("ceo", note.id) == ("note", "Scope change", "root")
    assert w.details.message_lookup("ceo", "nope") is None and w.details.message_lookup("ghost", note.id) is None
    ev: dict[str, object] = {"ts": "2026-10-18T10:05:27.000000Z", "kind": "run.start", "agent": "ceo", "batch": [note.id]}
    assert [x.text for x in w.details.event_lines([ev])] == ['10:05:27 run started (batch: note "Scope change" from root)']


def test_a_snapshot_is_made_when_none_is_given_or_remembered(w: DashWorld) -> None:
    team(w)
    assert w.state.snap is None
    assert w.details.agent_detail("ceo").row is not None and w.state.snap is not None
