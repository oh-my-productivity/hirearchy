"""Contract of ``StallLadder``: the ladder over an organization on disk and over the in-memory ports climbs the same steps, with the same notes,
events, operator lines and ledger bytes."""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest

from orgmcp.stalls import StallLadder
from orgmcp.stalls.testing import IMPLEMENTATIONS, STALL_AFTER, StallsWorld
from orgmcp.templates.testing import static_notices

from ._support import RED, make_world, quiet_task, stall, titles

NOTICES = static_notices()


@pytest.fixture(params=IMPLEMENTATIONS[StallLadder], ids=lambda factory: factory.__name__)
def w(request: pytest.FixtureRequest, tmp_path: Path) -> StallsWorld:
    made = make_world(request, tmp_path)
    assert isinstance(made.ladder, StallLadder)
    made.hire("ceo")
    return made


def ledger(w: StallsWorld) -> dict[str, dict[str, float]]:
    text = w.ledger_text()
    assert text is not None
    return cast(dict[str, dict[str, float]], json.loads(text))


# ------------------------------------------------------------------------------ the first step: the reminder


@RED
def test_nothing_is_stalled_before_stall_after(w: StallsWorld) -> None:
    quiet_task(w)
    w.clock.advance(STALL_AFTER - 1)
    assert w.ladder.check() == [] and titles(w, "ceo") == [] and w.ledger_text() is None and w.events.events == []


@RED
def test_the_assignee_is_reminded_after_stall_after(w: StallsWorld) -> None:
    task = quiet_task(w)
    assert stall(w) == [f"ceo: reminded about open task {task.id}"]
    (note,) = w.notes("ceo")
    assert note.title == "reminder: T" and note.body == NOTICES.nudge(task.id, "T") and note.sender == "runtime" and note.wake is True
    assert note.trace == task.trace


@RED
def test_the_ledger_remembers_the_step_and_when(w: StallsWorld) -> None:
    task = quiet_task(w)
    stall(w)
    assert ledger(w) == {task.id: {"step": 0, "at": w.clock.time()}}
    assert w.ledger_text() == json.dumps({task.id: {"step": 0, "at": w.clock.time()}}, indent=2) + "\n"


@RED
def test_the_step_is_an_event_of_the_scheduler(w: StallsWorld) -> None:
    task = quiet_task(w)
    stall(w)
    (event,) = w.events.events
    assert (event.kind, event.actor, event.proc, event.trace) == ("stall.nudge", "runtime", "scheduler", task.trace)
    assert event.fields == {"task": task.id, "to": "ceo", "step": 0}


@RED
def test_a_pass_that_does_nothing_changes_nothing(w: StallsWorld) -> None:
    quiet_task(w)
    stall(w)
    before = (w.ledger_text(), len(w.events.events), len(w.notes("ceo")))
    assert w.ladder.check() == []
    assert (w.ledger_text(), len(w.events.events), len(w.notes("ceo"))) == before


# ------------------------------------------------------------------------------ the next steps


@RED
def test_the_assigner_hears_about_it_after_another_stall_after(w: StallsWorld) -> None:
    task = quiet_task(w)
    stall(w)
    w.read("ceo")  # the reminder was read and nothing came of it
    assert stall(w) == [f"ceo: stalled on {task.id}, told root"]
    (note,) = w.notes("root")
    assert note.title == "stalled: T" and note.body == NOTICES.stalled("ceo", task.id, "T", ["ceo"]) and note.trace == task.trace
    assert ledger(w) == {task.id: {"step": 1, "at": w.clock.time()}}
    assert w.events.events[-1].fields == {"task": task.id, "to": "root", "step": 1}


@RED
def test_the_ladder_stops_when_root_has_been_told(w: StallsWorld) -> None:
    quiet_task(w)
    stall(w)
    w.read("ceo")
    stall(w)
    for _ in range(3):
        w.read("ceo")
        assert stall(w) == []
    assert titles(w, "ceo") == ["reminder: T"] and titles(w, "root") == ["stalled: T"] and len(w.events.events) == 2


@RED
def test_the_ladder_climbs_each_ancestor_to_root(w: StallsWorld) -> None:
    for addr in ("ceo/eng", "ceo/eng/dev", "ops"):  # (ops is not on the chain)
        w.hire(addr)
    w.delegate("root", "ceo", "Ship")
    w.read("ceo")
    w.delegate("ceo", "ceo/eng", "Plan")
    w.read("ceo/eng")
    task = w.delegate("ceo/eng", "ceo/eng/dev", "Build")
    w.read("ceo/eng/dev")
    assert stall(w) == [f"ceo/eng/dev: reminded about open task {task.id}"]
    w.read("ceo/eng/dev")
    assert stall(w) == [f"ceo/eng/dev: stalled on {task.id}, told ceo/eng"]
    assert stall(w) == [f"ceo/eng/dev: stalled on {task.id}, told ceo"]
    assert stall(w) == [f"ceo/eng/dev: stalled on {task.id}, told root"]
    assert stall(w) == []
    assert [e.fields["to"] for e in w.events.events] == ["ceo/eng/dev", "ceo/eng", "ceo", "root"]
    assert [e.fields["step"] for e in w.events.events] == [0, 1, 2, 3]
    assert titles(w, "ceo/eng") == ["stalled: Build"] and titles(w, "ceo") == ["stalled: Build"] and titles(w, "root") == ["stalled: Build"]
    assert titles(w, "ops") == []


@RED
def test_an_assigner_that_delegated_the_work_is_not_itself_stalled(w: StallsWorld) -> None:
    w.hire("ceo/eng")
    root_task = w.delegate("root", "ceo", "Ship")
    w.read("ceo")
    w.delegate("ceo", "ceo/eng", "Build")
    w.read("ceo/eng")
    stall(w)
    stall(w)
    assert root_task.id not in ledger(w) and titles(w, "ceo").count("reminder: Ship") == 0


# ------------------------------------------------------------------------------ when the clock restarts


@RED
def test_a_step_waits_a_whole_stall_after_from_the_previous_one(w: StallsWorld) -> None:
    quiet_task(w)
    stall(w)
    w.read("ceo")
    w.clock.advance(STALL_AFTER - 1)
    assert w.ladder.check() == [] and titles(w, "root") == []
    w.clock.advance(1)
    assert len(w.ladder.check()) == 1 and titles(w, "root") == ["stalled: T"]


@RED
def test_the_end_of_a_run_of_the_assignee_restarts_the_wait(w: StallsWorld) -> None:
    quiet_task(w)
    w.clock.advance(STALL_AFTER - 10)
    w.log_run("ceo", w.clock.time())  # the assignee ran (and did not finish the task)
    w.clock.advance(20)
    assert w.ladder.check() == [] and titles(w, "ceo") == []
    w.clock.advance(STALL_AFTER)
    assert len(w.ladder.check()) == 1 and titles(w, "ceo") == ["reminder: T"]


@RED
def test_a_run_before_the_task_does_not_delay_it(w: StallsWorld) -> None:
    w.log_run("ceo", w.clock.time() - 10_000)
    quiet_task(w)
    assert len(stall(w)) == 1


@RED
def test_stall_after_is_read_from_the_settings_of_the_organization(w: StallsWorld) -> None:
    quiet_task(w)
    w.configure("---\nmission: m\nstall_after: 60\n---\nrules\n")
    w.clock.advance(59)
    assert w.ladder.check() == []
    w.clock.advance(1)
    assert len(w.ladder.check()) == 1


@RED
@pytest.mark.parametrize("bad", ["soon", "null", "[]", "true", ".nan"])
def test_a_malformed_stall_after_means_the_default(w: StallsWorld, bad: str) -> None:
    quiet_task(w)
    w.configure(f"---\nmission: m\nstall_after: {bad}\n---\nrules\n")
    w.clock.advance(STALL_AFTER - 1)
    assert w.ladder.check() == []
    w.clock.advance(1)
    assert len(w.ladder.check()) == 1


# ------------------------------------------------------------------------------ who is stalled


@RED
def test_an_agent_with_unread_mail_is_not_stalled(w: StallsWorld) -> None:
    w.delegate("root", "ceo", "T")  # unread: the next run will see it
    assert stall(w) == [] and w.ledger_text() is None


@RED
def test_an_agent_that_is_running_is_not_stalled(w: StallsWorld) -> None:
    quiet_task(w)
    w.delegate("root", "ceo", "Other")
    w.start_run("ceo")
    assert stall(w) == [] and titles(w, "ceo") == []


@RED
def test_a_paused_agent_is_not_stalled(w: StallsWorld) -> None:
    quiet_task(w)
    w.pause("ceo", "too many failures")
    assert stall(w) == [] and titles(w, "ceo") == []


@RED
def test_an_agent_waiting_on_delegated_work_is_not_stalled(w: StallsWorld) -> None:
    w.hire("ceo/eng")
    w.delegate("root", "ceo", "Ship")
    w.read("ceo")
    w.delegate("ceo", "ceo/eng", "Build")
    assert stall(w) == [] and titles(w, "ceo") == []


@RED
def test_the_stall_of_one_agent_does_not_depend_on_another_one_running(w: StallsWorld) -> None:
    w.hire("dev")
    quiet_task(w)
    w.delegate("root", "dev", "Other")
    w.start_run("dev")
    assert len(stall(w)) == 1 and titles(w, "ceo") == ["reminder: T"] and titles(w, "dev") == []


@RED
def test_every_open_task_of_a_stalled_agent_is_climbed_in_order(w: StallsWorld) -> None:
    first = w.delegate("root", "ceo", "First")
    second = w.delegate("root", "ceo", "Second")
    w.read("ceo")
    assert stall(w) == [f"ceo: reminded about open task {first.id}", f"ceo: reminded about open task {second.id}"]
    assert titles(w, "ceo") == ["reminder: First", "reminder: Second"]
    assert [e.fields["task"] for e in w.events.events] == [first.id, second.id]


@RED
def test_the_agents_are_taken_in_the_order_of_the_directory(w: StallsWorld) -> None:
    w.hire("alpha")
    a, c = quiet_task(w, "alpha"), quiet_task(w, "ceo")
    assert stall(w) == [f"alpha: reminded about open task {a.id}", f"ceo: reminded about open task {c.id}"]


# ------------------------------------------------------------------------------ the ledger follows the open tasks


@RED
def test_a_task_that_was_answered_leaves_the_ledger(w: StallsWorld) -> None:
    task = quiet_task(w)
    other = w.delegate("root", "ceo", "Other")
    w.read("ceo")
    stall(w)
    assert set(ledger(w)) == {task.id, other.id}
    w.report(task)
    w.ladder.check()
    assert set(ledger(w)) == {other.id}


@RED
def test_the_ledger_is_empty_once_no_task_is_open(w: StallsWorld) -> None:
    task = quiet_task(w)
    stall(w)
    w.report(task)
    w.ladder.check()
    assert w.ledger_text() == "{}\n"


@RED
def test_the_entry_of_a_task_stays_while_its_agent_is_busy(w: StallsWorld) -> None:
    task = quiet_task(w)
    stall(w)
    w.delegate("root", "ceo", "More")  # unread mail: not stalled now
    w.clock.advance(STALL_AFTER)
    w.ladder.check()
    assert task.id in ledger(w)


# ------------------------------------------------------------------------------ the ledger of earlier versions


@RED
def test_a_nudged_task_of_the_legacy_ledger_goes_on_with_the_assigner(w: StallsWorld) -> None:
    task = quiet_task(w)
    w.put_ledger_text(json.dumps({task.id: "nudged"}))
    assert stall(w) == [f"ceo: stalled on {task.id}, told root"]
    assert ledger(w) == {task.id: {"step": 1, "at": w.clock.time()}}


@RED
def test_an_escalated_task_of_the_legacy_ledger_gets_no_further_step(w: StallsWorld) -> None:
    task = quiet_task(w)
    w.put_ledger_text(json.dumps({task.id: "escalated"}))
    assert stall(w) == []
    assert ledger(w) == {task.id: {"step": 1, "at": 0}}  # (and the legacy form is replaced by the current one)


@RED
@pytest.mark.parametrize("junk", ["[]", "42", '"x"', "null", "{ broken", '{"a": []}', '{"a": {"step": "x"}}'])
def test_a_malformed_ledger_never_stops_the_ladder(w: StallsWorld, junk: str) -> None:
    quiet_task(w)
    w.put_ledger_text(junk)
    assert len(stall(w)) == 1 and titles(w, "ceo") == ["reminder: T"]


@RED
@pytest.mark.parametrize("junk", ["[]", "42", '"x"', "null"])
def test_a_ledger_that_is_not_an_object_is_replaced(w: StallsWorld, junk: str) -> None:
    w.put_ledger_text(junk)
    assert w.ladder.check() == [] and w.ledger_text() == "{}\n"


@RED
def test_a_ledger_that_cannot_be_parsed_is_left_alone_when_nothing_is_open(w: StallsWorld) -> None:
    w.put_ledger_text("{ broken")
    assert w.ladder.check() == [] and w.ledger_text() == "{ broken"


# ------------------------------------------------------------------------------ the cost of an idle pass


@RED
def test_an_idle_pass_computes_the_task_views_only_for_what_changed(w: StallsWorld) -> None:
    w.hire("dev")
    quiet_task(w)
    w.ladder.check()
    first = list(w.tasks.computed)
    assert {addr for _, addr in first} == {"ceo", "dev"} and ("open_tasks", "ceo") in first
    for _ in range(3):
        w.ladder.check()
    assert w.tasks.computed == first  # the message files did not change: nothing is recomputed
    w.delegate("root", "dev", "Now")  # dev gets a message; ceo's mailbox is as before
    w.ladder.check()
    assert w.tasks.computed[len(first):] == [("open_tasks", "dev")]


@RED
def test_a_run_that_only_moves_the_inbox_does_not_recompute(w: StallsWorld) -> None:
    quiet_task(w)
    w.ladder.check()
    computed = list(w.tasks.computed)
    w.delegate("root", "ceo", "Next")  # recomputed once: a new file
    w.ladder.check()
    after_new_file = list(w.tasks.computed)
    assert len(after_new_file) > len(computed)
    w.start_run("ceo")  # inbox -> inflight: the same message files
    w.ladder.check()
    assert w.tasks.computed == after_new_file


@RED
def test_a_result_recomputes_the_views_of_the_agent_that_sent_it(w: StallsWorld) -> None:
    task = quiet_task(w)
    w.ladder.check()
    before = len(w.tasks.computed)
    w.report(task)
    w.ladder.check()
    assert ("open_tasks", "ceo") in w.tasks.computed[before:]
