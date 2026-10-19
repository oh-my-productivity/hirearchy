"""Contract of ``NowQueries``: what is happening right now, over an organization on disk and one in memory.

The scheduler is whatever the world says it is, the budgets are numbers the world sets; the mail, the run logs, the event files and the pause flags are
the organization's. Nothing is written by asking."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import cast

import pytest

from orgmcp.daemon import SchedulerState
from orgmcp.kernel import JsonObject
from orgmcp.observability import NowQueries
from orgmcp.observability.testing import IMPLEMENTATIONS, ObservabilityWorld

from . import _support
from ._support import RED, items, stamp, table

pytestmark = RED

NOW = stamp(200)
RUNNING = SchedulerState("running", 7000, "2026-10-18 10:00:00Z")
KEYS = ["now", "scheduler", "max_parallel", "runs_in_flight", "queued", "waiting_on_you", "open_root_tasks", "paused", "errors_15m", "last_event", "events_seen"]


@pytest.fixture(params=_support.implementations(IMPLEMENTATIONS[NowQueries]))
def w(request: pytest.FixtureRequest, tmp_path: Path) -> ObservabilityWorld:
    made: ObservabilityWorld = request.param(tmp_path)
    assert isinstance(made.now, NowQueries)
    for addr in ("ceo", "ceo/eng"):
        made.agent(addr)
    return made


def queued(w: ObservabilityWorld, **extra: object) -> dict[str, str]:
    return {str(q["agent"]): str(q["reason"]) for q in items(w.now.now_view(NOW), "queued")}


def mail(w: ObservabilityWorld, to: str, budget: int = 0, when: float = 150, **kw: object) -> None:
    w.send("root", to, "task", when, title="Do", budget=budget, **kw)
    w.budgets.held[to] = budget
    w.settle()


def test_an_organization_nothing_happened_in_is_quiet(w: ObservabilityWorld) -> None:
    view = w.now.now_view(NOW)
    assert list(view) == KEYS and view["now"] == NOW.isoformat()
    assert (view["runs_in_flight"], view["queued"], view["waiting_on_you"], view["paused"]) == ([], [], [], {})
    assert (view["open_root_tasks"], view["last_event"], view["events_seen"], view["max_parallel"]) == (0, None, False, 3)
    assert view["errors_15m"] == {"count": 0, "events": []}
    assert table(view, "scheduler")["state"] == "stopped" and table(view, "scheduler")["last_exit"] is None


def test_the_default_time_is_the_clock(w: ObservabilityWorld) -> None:
    w.clock.advance(5)
    assert w.now.now_view()["now"] == w.clock.now().isoformat()


def test_the_scheduler_is_the_one_the_status_says(w: ObservabilityWorld) -> None:
    w.scheduler.current = SchedulerState("unverified", 4242, "x", "its command line is 'vim'")
    s = table(w.now.now_view(NOW), "scheduler")
    assert (s["state"], s["pid"], s["since"], s["detail"], s["mode"]) == ("unverified", 4242, "x", "its command line is 'vim'", None)


def test_a_running_scheduler_has_a_mode_an_uptime_and_a_heartbeat(w: ObservabilityWorld) -> None:
    w.scheduler.current = RUNNING
    w.emit(0, "scheduler.start", proc="scheduler", pid=7000, mode="until_done")
    w.emit(190, "scheduler.heartbeat", proc="scheduler", pid=7000, running=["ceo"])
    s = table(w.now.now_view(NOW), "scheduler")
    assert (s["mode"], s["uptime_s"], s["heartbeats"], s["last_heartbeat_age_s"], s["heartbeat_running"]) == ("until_done", 200.0, True, 10.0, ["ceo"])


def test_a_stopped_scheduler_says_how_the_last_one_exited(w: ObservabilityWorld) -> None:
    w.marker.write("stopped by hand")
    assert table(w.now.now_view(NOW), "scheduler")["last_exit"] == "stopped by hand"
    w.emit(50, "scheduler.start", proc="scheduler", pid=7000, mode="daemon")
    w.emit(60, "scheduler.exit", proc="scheduler", pid=7000, reason="finished: no open tasks")
    s = table(w.now.now_view(NOW), "scheduler")
    assert s["last_exit"] == "finished: no open tasks" and s["last_exit_ts"] == stamp(60).isoformat()


def test_mail_waits_for_a_scheduler_to_start_it(w: ObservabilityWorld) -> None:
    mail(w, "ceo", 3)
    assert queued(w) == {"ceo": "scheduler is not running"}
    w.scheduler.current = RUNNING
    assert queued(w) == {"ceo": "ready: starts on the next tick"}
    (q,) = items(w.now.now_view(NOW), "queued")
    assert q["unread"] == 1 and q["waiting_s"] is not None


def test_an_agent_with_no_budget_waits_for_runs(w: ObservabilityWorld) -> None:
    w.scheduler.current = RUNNING
    mail(w, "ceo", 0)
    assert queued(w) == {"ceo": "no budget"}


def test_a_paused_agent_waits_for_its_flag_to_go(w: ObservabilityWorld) -> None:
    w.scheduler.current = RUNNING
    mail(w, "ceo", 3)
    w.pause("ceo", "failures")
    assert queued(w) == {"ceo": "paused: failures"} and w.now.now_view(NOW)["paused"] == {"ceo": "failures"}


def test_mail_that_comes_in_during_a_run_waits_for_the_next(w: ObservabilityWorld) -> None:
    w.scheduler.current = RUNNING
    mail(w, "ceo", 3, trace="self")
    w.begin_run("ceo")
    stem = w.run_log("ceo", 160)
    w.running("ceo", stem)
    w.send("root", "ceo", "note", 170, title="More")
    assert queued(w) == {"ceo": "its current run is still going; the next run starts after it"}


def test_agents_wait_when_as_many_runs_as_may_go_are_going(w: ObservabilityWorld) -> None:
    w.scheduler.current = RUNNING
    w.configure("---\nmission: test\nmax_parallel: 1\n---\nrules\n")
    mail(w, "ceo", 3)
    w.begin_run("ceo")
    w.running("ceo", w.run_log("ceo", 160))
    mail(w, "ceo/eng", 3)
    view = w.now.now_view(NOW)
    assert view["max_parallel"] == 1 and {q["agent"]: q["reason"] for q in items(view, "queued")}["ceo/eng"] == "max_parallel (1) runs are busy"


def test_a_run_going_is_named_with_its_batch_and_its_traces(w: ObservabilityWorld) -> None:
    mail(w, "ceo", 3, trace="self")
    w.begin_run("ceo")
    stem = w.run_log("ceo", 180)
    w.running("ceo", stem)
    (run,) = items(w.now.now_view(NOW), "runs_in_flight")
    assert (run["agent"], run["run"], run["batch"]) == ("ceo", f"ceo@{stem}", ["Do"])
    assert len(cast("list[str]", run["traces"])) == 1 and run["elapsed_s"] == 200.0


def test_what_waits_for_root_is_what_the_queue_lists(w: ObservabilityWorld) -> None:
    w.waiting.entries = [("m1", "Needs you: note from ceo \"Logo\": help (message m1)")]
    assert w.now.now_view(NOW)["waiting_on_you"] == ["Needs you: note from ceo \"Logo\": help (message m1)"]


def test_root_tasks_that_are_open_are_counted(w: ObservabilityWorld) -> None:
    w.send("root", "ceo", "task", 10, title="Ship", budget=2, trace="self")
    assert w.now.now_view(NOW)["open_root_tasks"] == 1


def test_the_errors_of_the_last_fifteen_minutes_are_counted_and_the_last_five_shown(w: ObservabilityWorld) -> None:
    for i in range(7):
        w.tool(100 + i, "ceo", "send", ok=False, error=f"e{i}")
    w.tool(99, "ceo", "send")
    w.tool(-2000, "ceo", "send", ok=False, error="old")
    errors = table(w.now.now_view(NOW), "errors_15m")
    assert errors["count"] == 7 and [e["error"] for e in cast("list[JsonObject]", errors["events"])] == ["e2", "e3", "e4", "e5", "e6"]


def test_the_last_event_and_whether_any_was_seen(w: ObservabilityWorld) -> None:
    w.tool(30, "ceo", "inbox")
    w.tool(90, "ceo", "inbox")
    view = w.now.now_view(NOW)
    assert view["events_seen"] is True and view["last_event"] == stamp(90).isoformat()


def test_asking_changes_nothing(w: ObservabilityWorld, tmp_path: Path) -> None:
    mail(w, "ceo", 3)
    w.tool(30, "ceo", "inbox")

    def snapshot() -> list[tuple[str, int, int]]:
        return sorted((str(p), p.stat().st_mtime_ns, p.stat().st_size) for p in tmp_path.rglob("*") if p.is_file())

    before = snapshot()
    w.now.now_view(NOW)
    assert snapshot() == before


def test_a_time_before_the_events_is_fine(w: ObservabilityWorld) -> None:
    w.tool(300, "ceo", "inbox")
    view = w.now.now_view(datetime(2026, 10, 18, 9, 0, tzinfo=NOW.tzinfo))
    assert view["errors_15m"] == {"count": 0, "events": []}
