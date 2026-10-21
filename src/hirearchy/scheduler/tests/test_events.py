"""``run.start`` and ``run.end`` carry the fields the event log has always carried, in the scheduler's name; durations use the run clock."""

from __future__ import annotations

from hirearchy.access.testing import StaticAccess
from hirearchy.budget.testing import FixedBudget
from hirearchy.kernel.testing import FakeClock, ListEventSink
from hirearchy.mail.testing import memory_mailbox
from hirearchy.processes.testing import FakeProcessTable
from hirearchy.scheduler._events import ERROR_MAX, LifecycleEvents, SchedulerEvents

from ._support import ROOT_DIR, a_run, message, prepared


def test_the_events_of_the_scheduler_say_who_emits() -> None:
    sink = ListEventSink()
    SchedulerEvents(sink).emit("scheduler.start", mode="daemon", max_runs=None)
    (event,) = sink.events
    assert (event.kind, event.proc, event.actor, event.fields) == ("scheduler.start", "scheduler", "runtime", {"mode": "daemon", "max_runs": None})


def test_what_the_caller_says_wins() -> None:
    sink = ListEventSink()
    SchedulerEvents(sink).emit("x", actor="ceo", proc="cli", run="r", trace="t", a=1)
    (event,) = sink.events
    assert (event.actor, event.proc, event.run, event.trace, event.fields) == ("ceo", "cli", "r", "t", {"a": 1})


class World:
    def __init__(self) -> None:
        self.clock, self.sink = FakeClock(), ListEventSink()
        self.access = StaticAccess(ROOT_DIR)
        self.access.put_agent("ceo", {"model": "claude-x"})
        self.budgets = FixedBudget(memory_mailbox(ROOT_DIR).tasks, self.access.agents, self.access.agents)
        self.budgets.held["ceo"] = 2
        self.events = LifecycleEvents(SchedulerEvents(self.sink), self.access, self.budgets, self.access.agents, self.clock)
        self.table = FakeProcessTable(self.clock)


def test_run_start_has_the_fields_of_the_golden_event() -> None:
    w = World()
    batch = [message("20260101T000000000000-root-aaaa", trace="t1"), message("20260101T000001000000-root-bbbb", trace="t1")]
    w.events.started(prepared("ceo", batch, traces=("t1",), budget=3), 77)
    (event,) = w.sink.events
    assert (event.kind, event.proc, event.actor, event.run, event.trace) == ("run.start", "scheduler", "runtime", "ceo@20260101T000000000000", "t1")
    assert event.fields == {"agent": "ceo", "batch": [m.id for m in batch], "traces": ["t1"], "child_pid": 77, "pgid": 77, "model": "claude-x", "budget_before": 3}


def test_run_end_of_a_successful_run() -> None:
    w = World()
    run = a_run(w.table, w.clock, traces=("t1",))
    w.clock.advance(12.3456)
    w.events.ended(run, 0)
    (event,) = w.sink.events
    assert (event.kind, event.trace, event.run) == ("run.end", "t1", run.run_id)
    assert event.fields == {"agent": "ceo", "ok": True, "exit_code": 0, "duration_ms": 12345, "timed_out": False, "killed": False, "budget_after": 2, "error": None}


def test_run_end_of_a_failed_run_says_the_exit_code_and_a_killed_run_is_never_ok() -> None:
    w = World()
    run = a_run(w.table, w.clock)
    w.events.ended(run, 3)
    run.killed = run.timed_out = True
    w.events.ended(run, 0, "timed out: killed after 5s")
    first, second = (e.fields for e in w.sink.events)
    assert (first["ok"], first["error"]) == (False, "exit code 3")
    assert (second["ok"], second["timed_out"], second["killed"], second["error"]) == (False, True, True, "timed out: killed after 5s")


def test_run_end_of_a_retired_agent_has_no_budget_after_and_errors_are_clipped() -> None:
    w = World()
    run = a_run(w.table, w.clock, addr="gone")
    w.events.ended(run, 1, "x" * 900)
    (event,) = w.sink.events
    assert event.fields["budget_after"] is None and len(str(event.fields["error"])) <= ERROR_MAX


def test_a_run_that_never_started_has_a_start_and_an_end_without_trace_or_duration() -> None:
    w = World()
    w.events.not_started(prepared("ceo", traces=("t1",)), FileNotFoundError("kiro-cli"))
    start, end = w.sink.events
    assert (start.kind, start.fields["child_pid"], start.fields["pgid"]) == ("run.start", None, None)
    assert (end.kind, end.trace, end.run) == ("run.end", None, "ceo@20260101T000000000000")
    assert end.fields == {"agent": "ceo", "ok": False, "exit_code": None, "duration_ms": 0, "timed_out": False, "killed": False, "budget_after": 2,
                          "error": "failed to start: kiro-cli"}
