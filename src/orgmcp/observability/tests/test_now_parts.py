"""The parts ``now`` is made of, each alone: what the scheduler report reads, which batches are in flight, why mail is queued, the recent events, the desk of root."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, cast

import pytest

from orgmcp.attention.testing import ListHumanQueue
from orgmcp.daemon import SchedulerState
from orgmcp.daemon.testing import FakeSchedulerStatus, MemoryExitMarker
from orgmcp.eventlog.testing import MemoryEventLog
from orgmcp.kernel import JsonObject
from orgmcp.kernel.testing import FakeClock
from orgmcp.mail import MessageFile, MessageIndex
from orgmcp.observability._now import (
    BatchRunsInFlight,
    EventSchedulerReport,
    FileNowQueries,
    LoggedRecentEvents,
    MailInflightBatches,
    MailRootDesk,
    ReasonedQueue,
)
from orgmcp.observability._ports import BatchItem, FlightReport, InflightBatches, QueueReport, RecentEvents, RootDesk, SchedulerReport

from ._scenario import NOW, RUNNING, SCENARIOS, follow_ports, settle, stamp
from ._second import Second
from ._support import RED, items

pytestmark = RED


def put(log: MemoryEventLog, when: float, kind: str, proc: str = "scheduler", pid: int = 7000, **fields: object) -> None:
    ts = stamp(when)
    line = {"v": 1, "ts": ts.isoformat(), "seq": 1, "proc": proc, "pid": pid, "kind": kind, "actor": "runtime", **fields}
    log.append(f"{ts:%Y-%m-%d}", f"{proc}-{pid}-{1792317600000 + pid}.jsonl", (json.dumps(line) + "\n").encode())


def busy(built: Any, parallel: int = 3) -> Second:
    setup, state, verdict = SCENARIOS["busy"]
    setup(built)
    if parallel != 3:
        cfg = (built.org.root / "ORG.md").read_text().replace("max_parallel: 3", f"max_parallel: {parallel}")
        (built.org.root / "ORG.md").write_text(cfg)
    settle(built.org)
    return Second(follow_ports(built.org, state, verdict))


# ------------------------------------------------------------------------------ the scheduler


def test_a_stopped_scheduler_reports_how_the_last_one_exited_from_its_events() -> None:
    log = MemoryEventLog(FakeClock())
    put(log, 0, "scheduler.start", mode="daemon")
    put(log, 50, "scheduler.exit", reason="finished: no open tasks")
    report = EventSchedulerReport(FakeSchedulerStatus(SchedulerState("stopped")), MemoryExitMarker("older\n"), log)
    assert isinstance(report, SchedulerReport)
    info = report.info(stamp(60))
    assert info["state"] == "stopped" and info["last_exit"] == "finished: no open tasks" and info["last_exit_ts"] == stamp(50).isoformat()
    assert info["mode"] is None and info["uptime_s"] is None and info["heartbeats"] is False


def test_a_stopped_scheduler_without_events_reports_the_exit_marker() -> None:
    log = MemoryEventLog(FakeClock())
    assert EventSchedulerReport(FakeSchedulerStatus(), MemoryExitMarker("stopped by hand\n"), log).info(stamp(5))["last_exit"] == "stopped by hand"
    assert EventSchedulerReport(FakeSchedulerStatus(), MemoryExitMarker(), log).info(stamp(5))["last_exit"] is None


def test_only_the_last_three_files_are_asked_for_the_exit() -> None:
    log = MemoryEventLog(FakeClock())
    put(log, 1, "scheduler.exit", pid=1, reason="the oldest")
    for pid in (2, 3, 4):
        put(log, pid, "scheduler.start", pid=pid, mode="daemon")
    assert EventSchedulerReport(FakeSchedulerStatus(), MemoryExitMarker(), log).info(stamp(9))["last_exit"] is None


def test_a_running_scheduler_reports_its_mode_uptime_and_heartbeat() -> None:
    log = MemoryEventLog(FakeClock())
    put(log, 0, "scheduler.start", mode="until_done")
    put(log, 190, "scheduler.heartbeat", running=["ceo"])
    other = EventSchedulerReport(FakeSchedulerStatus(SchedulerState("running", 7000, "x")), MemoryExitMarker("ignored"), log)
    info = other.info(stamp(200))
    assert info["mode"] == "until_done" and info["uptime_s"] == 200.0 and info["heartbeats"] is True
    assert info["last_heartbeat_age_s"] == 10.0 and info["heartbeat_running"] == ["ceo"] and info["last_exit"] is None


def test_a_running_scheduler_that_has_written_no_events_has_only_its_state() -> None:
    info = EventSchedulerReport(FakeSchedulerStatus(SchedulerState("running", 7000, "x")), MemoryExitMarker(), MemoryEventLog(FakeClock())).info(stamp(1))
    assert (info["state"], info["pid"], info["mode"], info["uptime_s"], info["heartbeats"]) == ("running", 7000, None, None, False)


def test_an_unverified_scheduler_carries_its_detail() -> None:
    state = SchedulerState("unverified", 4242, "x", "its command line is 'vim'")
    info = EventSchedulerReport(FakeSchedulerStatus(state), MemoryExitMarker(), MemoryEventLog(FakeClock())).info(stamp(1))
    assert info["detail"] == "its command line is 'vim'" and info["since"] == "x"


# ------------------------------------------------------------------------------ the batches


def test_the_batches_in_flight_are_the_messages_of_the_agents_with_a_run_going(built: Any) -> None:
    s = busy(built)
    assert isinstance(s.batches, InflightBatches)
    got = s.batches.of_running()
    assert list(got) == ["ceo"]
    assert [b.title for b in got["ceo"]] == ["Memo", "Another"] and all(isinstance(b, BatchItem) and b.sender == "root" for b in got["ceo"])
    assert [b.trace for b in got["ceo"]] == [None, None] and got["ceo"][0].id < got["ceo"][1].id


def test_no_run_going_no_batches(built: Any) -> None:
    setup, state, verdict = SCENARIOS["story"]
    assert Second(follow_ports(built.org, state, verdict)).batches.of_running() == {}


def test_the_front_matter_of_a_batch_comes_from_the_index_one_file_at_a_time(built: Any) -> None:
    s = busy(built)
    asked: list[Path] = []

    class Spy(MessageIndex):
        def scan(self) -> list[MessageFile]:
            raise AssertionError("scan reads every file")

        def meta_of(self, path: Path) -> tuple[JsonObject | None, str | None, float]:
            asked.append(path)
            found: tuple[JsonObject | None, str | None, float] = built.org.runtime.message_index.meta_of(path)
            return found

    rt = built.org.runtime
    got = MailInflightBatches(rt.agents, rt.mailbox, rt.paths, Spy()).of_running()
    assert [p.parent.parent.name for p in asked] == ["ceo", "ceo"] and [b.title for b in got["ceo"]] == ["Memo", "Another"]


def test_hidden_and_foreign_files_and_unreadable_ones_are_not_in_the_batch(built: Any) -> None:
    s = busy(built)
    inflight = built.org.dir("ceo") / "inflight"
    (inflight / ".tmp-1.md").write_text("---\nid: hidden\nfrom: root\nto: ceo\ntype: note\n---\nx\n")
    (inflight / "notes.txt").write_text("x")
    (inflight / "zz-broken.md").write_text("no front matter\n")
    assert [b.title for b in s.batches.of_running()["ceo"]] == ["Memo", "Another"]


def test_the_title_and_trace_of_a_batch_come_from_its_front_matter(built: Any) -> None:
    s = busy(built)
    inflight = built.org.dir("ceo") / "inflight"
    (inflight / "zz-traced.md").write_text("---\nid: traced-1\nfrom: root\nto: ceo\ntype: note\ntrace: T-9\n---\nx\n")
    (inflight / "zz-plain.md").write_text("---\nfrom: root\nto: ceo\ntype: note\n---\nx\n")
    last = s.batches.of_running()["ceo"][-2:]
    assert [(b.id, b.title, b.trace) for b in last] == [("traced-1", "", "T-9"), ("zz-plain", "", None)]


# ------------------------------------------------------------------------------ the runs in flight


def test_a_run_going_is_named_after_its_log_and_has_run_for_so_long(built: Any) -> None:
    s = busy(built)
    assert isinstance(s.flight, FlightReport)
    (run,) = s.flight.runs(NOW)
    assert run["agent"] == "ceo" and run["run"] == built.busy_run and run["batch"] == ["Memo", "Another"]
    assert run["elapsed_s"] == pytest.approx(19, abs=1)
    traces = cast("list[str]", run["traces"])
    assert traces == sorted(traces) and len(traces) == 2


def test_a_run_going_with_no_record_is_named_after_its_last_log(built: Any) -> None:
    s = busy(built)
    (built.org.root / ".runtime" / "running.json").unlink()
    (run,) = s.flight.runs(NOW)
    assert run["run"] == built.busy_run and run["elapsed_s"] is not None


def test_a_batch_that_records_its_trace_is_not_derived() -> None:
    class Batches(InflightBatches):
        def of_running(self) -> dict[str, list[BatchItem]]:
            return {"ceo": [BatchItem("m1", "", "root", "T-1"), BatchItem("m2", "Two", "root", "T-1")]}

    class Registry:
        def all(self) -> dict[str, JsonObject]:
            return {"ceo": {"started": stamp(5).timestamp(), "log": "ceo/runs/20261018T100005000000.log"}}

    class Nothing:
        def messages(self) -> dict[str, Any]:
            raise AssertionError("nothing to derive")

    flight = BatchRunsInFlight(Batches(), Registry(), None, Nothing(), None)  # type: ignore[arg-type]
    (run,) = flight.runs(stamp(25))
    assert run == {"agent": "ceo", "run": "ceo@20261018T100005000000", "elapsed_s": 20.0, "batch": ["m1", "Two"], "traces": ["T-1"]}


# ------------------------------------------------------------------------------ the queue


def queue_of(s: Second, up: bool, running: int, parallel: int) -> dict[str, str]:
    return {str(q["agent"]): str(q["reason"]) for q in s.queue.queued(NOW, up, running, parallel)}


def test_every_reason_a_mail_waits(built: Any) -> None:
    s = busy(built)
    assert isinstance(s.queue, QueueReport)
    assert queue_of(s, True, 1, 3) == {
        "ceo": "its current run is still going; the next run starts after it", "ceo/eng": "paused: failures", "ops": "ready: starts on the next tick",
        "poor": "no budget",
    }
    assert queue_of(s, True, 1, 1)["ops"] == "max_parallel (1) runs are busy"
    assert queue_of(s, False, 1, 3)["ops"] == "scheduler is not running"


def test_an_agent_paused_for_its_budget_is_not_held_back_once_it_has_some(built: Any) -> None:
    s = busy(built)
    built.org.resume("ceo/eng")
    built.org.pause("ceo/eng", "budget")
    budget = built.org.budget("ceo/eng") or 0
    assert queue_of(s, True, 1, 3)["ceo/eng"] == ("ready: starts on the next tick" if budget > 0 else "paused: budget")
    built.org.send("ceo", "ceo/eng", "runs for you", budget=1, wake=False)
    assert queue_of(s, True, 1, 3)["ceo/eng"] == "ready: starts on the next tick"


def test_how_long_the_oldest_mail_has_waited_comes_from_the_names_of_the_files(built: Any) -> None:
    s = busy(built)
    waits = {q["agent"]: q["waiting_s"] for q in s.queue.queued(NOW, True, 1, 3)}
    assert waits["ops"] == pytest.approx(15, abs=1) and all(w is not None for w in waits.values())


def test_the_paused_agents_and_why(built: Any) -> None:
    assert busy(built).queue.paused() == {"ceo/eng": "failures"}


# ------------------------------------------------------------------------------ the recent events


def test_the_errors_of_the_last_fifteen_minutes_and_the_last_five_of_them() -> None:
    log = MemoryEventLog(FakeClock())
    for i in range(7):
        put(log, 100 + i, "tool.call", proc="mcp", pid=1, actor="ceo", tool="send", ok=False, error=f"e{i}")
    put(log, 99, "tool.call", proc="mcp", pid=1, actor="ceo", tool="send", ok=True)
    put(log, -1500, "tool.call", proc="mcp", pid=1, actor="ceo", tool="send", ok=False, error="old")
    recent = LoggedRecentEvents(log)
    assert isinstance(recent, RecentEvents)
    errors = recent.errors(stamp(200))
    assert errors["count"] == 7 and [e["error"] for e in items(errors, "events")] == ["e2", "e3", "e4", "e5", "e6"]


def test_the_last_event_is_found_in_the_last_files_of_the_last_days() -> None:
    log = MemoryEventLog(FakeClock())
    assert LoggedRecentEvents(log).last(stamp(100)) is None
    put(log, 10, "scheduler.start", pid=1)
    put(log, 90, "tool.call", proc="mcp", pid=2, actor="ceo", ok=True)
    assert LoggedRecentEvents(log).last(stamp(100)) == stamp(90)
    assert LoggedRecentEvents(log).last(stamp(3 * 86400)) is None  # nothing in the last two days


# ------------------------------------------------------------------------------ the desk of root


def test_the_desk_lists_what_waits_for_root_and_counts_the_tasks_it_has_out(built: Any) -> None:
    desk = MailRootDesk(ListHumanQueue([("m1", "Needs you: a"), ("m2", "Needs you: b")]), built.org.runtime.task_query)
    assert isinstance(desk, RootDesk)
    assert desk.waiting() == ["Needs you: a", "Needs you: b"] and desk.open_tasks() == len(built.org.outstanding("root"))


# ------------------------------------------------------------------------------ the view


class Spy:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[Any, ...]]] = []


def test_the_view_is_made_of_the_parts_and_the_clock_gives_its_time(built: Any) -> None:
    class Scheduler(SchedulerReport):
        def info(self, now: datetime) -> JsonObject:
            return {"state": "running", "at": now.isoformat()}

    class Flight(FlightReport):
        def runs(self, now: datetime) -> list[JsonObject]:
            return [{"agent": "a"}, {"agent": "b"}]

    class Queue(QueueReport):
        def queued(self, now: datetime, scheduler_up: bool, running: int, max_parallel: int) -> list[JsonObject]:
            return [{"up": scheduler_up, "running": running, "max": max_parallel}]

        def paused(self) -> dict[str, str]:
            return {"x": "y"}

    class Recent(RecentEvents):
        def errors(self, now: datetime) -> JsonObject:
            return {"count": 0, "events": []}

        def last(self, now: datetime) -> datetime | None:
            return None

    class Desk(RootDesk):
        def waiting(self) -> list[str]:
            return ["w"]

        def open_tasks(self) -> int:
            return 4

    clock = FakeClock()
    view = FileNowQueries(built.org.runtime.settings, Scheduler(), Flight(), Queue(), Recent(), Desk(), clock).now_view()
    assert view == {
        "now": clock.now().isoformat(), "scheduler": {"state": "running", "at": clock.now().isoformat()}, "max_parallel": 3,
        "runs_in_flight": [{"agent": "a"}, {"agent": "b"}], "queued": [{"up": True, "running": 2, "max": 3}], "waiting_on_you": ["w"],
        "open_root_tasks": 4, "paused": {"x": "y"}, "errors_15m": {"count": 0, "events": []}, "last_event": None, "events_seen": False,
    }
    assert RUNNING[0] == "running"
