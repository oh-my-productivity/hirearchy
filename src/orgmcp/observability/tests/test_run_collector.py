"""``RunCollector``: every run is one run log (the file truth: one log = one run = one run of budget), completed with the events of the run.

Over the in-memory run logs, registry, mailboxes, agents and event log; ``run_events`` and ``run_dict`` are its pure parts."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import cast

import pytest

from orgmcp.eventlog.testing import memory_event_log
from orgmcp.kernel import JsonObject
from orgmcp.mail.testing import MemoryMailbox, memory_mailbox
from orgmcp.observability._ports import RunCollection
from orgmcp.observability._runs import RunCollector, RunRec, run_dict, run_events
from orgmcp.runs.testing import RunsHarness, memory_runs

from ._support import stamp


Events = dict[str, dict[str, JsonObject]]


@dataclass
class Place:
    collector: RunCollection
    runs: RunsHarness
    put: Callable[[str, str], None]  # a file of the organization (a message in a box)

    def log(self, addr: str, start: float, footer: str = "") -> str:
        name = f"{stamp(start):%Y%m%dT%H%M%S%f}"
        path = self.runs.put_log(addr, f"{name}.log", footer)
        self.runs.set_mtime(path, stamp(start + 1).timestamp())
        return name


@pytest.fixture
def place(tmp_path: Path) -> Place:
    mail, runs, log = memory_mailbox(tmp_path), memory_runs(tmp_path), memory_event_log(tmp_path)
    agents = cast(MemoryMailbox, mail.reader).agents
    for addr in ("ceo", "ceo/eng"):
        mail.agent(addr)
        runs.add_agent(addr)
    return Place(RunCollector(runs.reader, runs.registry, agents, mail.reader, log.reader), runs, mail.put)


def ev(kind: str, ts: float, **fields: object) -> JsonObject:
    return {"kind": kind, "ts": stamp(ts).isoformat(), **fields}


def only(runs: list[RunRec]) -> RunRec:
    (run,) = runs
    return run


# ------------------------------------------------------------------------------ the pure parts


def test_the_events_of_a_run_are_gathered_by_run_id_from_events_or_timed_events() -> None:
    start, end, orphan = ev("run.start", 1, run="a@1"), ev("run.end", 9, run="a@1"), ev("run.orphan", 5, run="b@2")
    noise = [ev("tool.call", 2, run="a@1"), ev("run.start", 3), ev("run.end", 3, run="")]
    assert run_events([start, end, orphan, *noise]) == {"a@1": {"start": start, "end": end}, "b@2": {"orphan": orphan}}
    assert run_events([(stamp(1), start), (stamp(9), end)]) == {"a@1": {"start": start, "end": end}}
    assert run_events([]) == {}


def test_a_run_as_a_dict_has_iso_times_and_leaves_the_log_out() -> None:
    run = RunRec(agent="ceo", run="ceo@1", start=stamp(3), outcome="ok", ok=True, end=stamp(45), duration_ms=42000.0, exit_code=0, batch=["m1"],
                 traces=["t1"], queue_ms=3000.0, source="events", log=Path("/x/y.log"), pid=123)
    assert run_dict(run) == {
        "agent": "ceo", "run": "ceo@1", "start": stamp(3).isoformat(), "outcome": "ok", "ok": True, "end": stamp(45).isoformat(),
        "duration_ms": 42000.0, "exit_code": 0, "error": None, "batch": ["m1"], "traces": ["t1"], "queue_ms": 3000.0, "source": "events", "pid": 123,
    }


# ------------------------------------------------------------------------------ one run


def test_a_run_log_is_a_run_with_the_outcome_its_closing_lines_give(place: Place) -> None:
    ok, bad, timeout, killed, failed_start, open_ = (place.log("ceo", n, f) for n, f in (
        (10, "# exit 0 after 5s\n"), (20, "# exit 1 after 6s\n"), (30, "# killed after 600s timeout\n"), (40, "# killed: by hand\n"),
        (50, "# failed to start: no kiro\n"), (60, "")))
    runs = {r.run: r for r in place.collector.collect(None, None, {}, ["ceo"])}
    assert [(runs[f"ceo@{s}"].outcome, runs[f"ceo@{s}"].ok) for s in (ok, bad, timeout, killed, failed_start, open_)] == [
        ("ok", True), ("failed", False), ("timeout", False), ("killed", False), ("failed", False), ("unknown", None)]
    first = runs[f"ceo@{ok}"]
    assert (first.exit_code, first.duration_ms, first.source, first.batch, first.traces, first.queue_ms, first.end) == (0, 5000.0, "log", None, None, None, None)
    assert first.start == stamp(10) and first.log is not None and first.log.name == f"{ok}.log"
    assert runs[f"ceo@{bad}"].exit_code == 1 and runs[f"ceo@{timeout}"].exit_code is None


def test_the_events_of_a_run_complete_it_and_win_over_the_log(place: Place) -> None:
    stem = place.log("ceo", 10, "# exit 0 after 5s\n")
    rid = f"ceo@{stem}"
    events: Events = {rid: {
        "start": ev("run.start", 10.5, batch=["20261018T100000000000-root-ab12", "x"], traces=["T1"], child_pid=4321, pgid=77),
        "end": ev("run.end", 15, ok=False, exit_code=3, duration_ms=5200, timed_out=False, killed=False, error="boom " * 200)}}
    run = only(place.collector.collect(None, None, events, ["ceo"]))
    assert (run.source, run.ok, run.outcome, run.exit_code, run.duration_ms, run.end) == ("events", False, "failed", 3, 5200.0, stamp(15))
    assert (run.batch, run.traces, run.pid) == (["20261018T100000000000-root-ab12", "x"], ["T1"], 4321)
    assert run.queue_ms == pytest.approx(10500.0) and run.error is not None and len(run.error) == 500 and run.error.endswith("…")


def test_the_outcome_of_an_end_event(place: Place) -> None:
    stems = [place.log("ceo", n) for n in (10, 20, 30, 40)]
    ends = [dict(ok=True), dict(ok=True, timed_out=True), dict(ok=True, killed=True), dict(ok=False, killed=True, timed_out=True)]
    events: Events = {f"ceo@{s}": {"end": ev("run.end", 11, **e)} for s, e in zip(stems, ends)}
    got = [r.outcome for r in place.collector.collect(None, None, events, ["ceo"])]
    assert got == ["ok", "timeout", "killed", "timeout"]


def test_the_pid_is_the_childs_else_the_process_group_and_never_a_bool(place: Place) -> None:
    stems = [place.log("ceo", n) for n in (10, 20, 30, 40)]
    starts: list[dict[str, object]] = [dict(child_pid=1, pgid=2), dict(pgid=2), dict(child_pid="x", pgid=True), dict()]
    events: Events = {f"ceo@{s}": {"start": ev("run.start", 11, batch=[], traces=[], **p)} for s, p in zip(stems, starts)}
    assert [r.pid for r in place.collector.collect(None, None, events, ["ceo"])] == [1, 2, None, None]


def test_the_wait_in_the_queue_is_from_the_oldest_message_of_the_batch_to_the_start_of_the_run(place: Place) -> None:
    stem = place.log("ceo", 100)
    ids = [f"{stamp(40):%Y%m%dT%H%M%S%f}-root-0001", f"{stamp(70):%Y%m%dT%H%M%S%f}-root-0002", "not-an-id"]
    events: Events = {f"ceo@{stem}": {"start": ev("run.start", 100.25, batch=ids, traces=[])}}
    assert only(place.collector.collect(None, None, events, ["ceo"])).queue_ms == 60250.0
    events = {f"ceo@{stem}": {"start": ev("run.start", 100, batch=["not-an-id"], traces=[])}}
    assert only(place.collector.collect(None, None, events, ["ceo"])).queue_ms is None
    events = {f"ceo@{stem}": {"start": ev("run.start", 1, batch=ids[:1], traces=[])}}  # the event before the messages: never negative
    assert only(place.collector.collect(None, None, events, ["ceo"])).queue_ms == 0.0


def test_an_orphaned_run_was_killed(place: Place) -> None:
    stem = place.log("ceo", 10)
    events: Events = {f"ceo@{stem}": {"orphan": ev("run.orphan", 12, action="killed", detail="no process")}}
    run = only(place.collector.collect(None, None, events, ["ceo"]))
    assert (run.outcome, run.ok, run.error, run.source) == ("killed", False, "orphan: killed no process", "log")


def test_the_run_in_flight_is_running_only_when_the_agent_has_a_batch_and_the_registry_says_so(place: Place) -> None:
    older = place.log("ceo", 10)
    place.log("ceo", 20)
    assert [r.outcome for r in place.collector.collect(None, None, {}, ["ceo"])] == ["unknown", "unknown"]
    place.put(f"ceo/inflight/{stamp(5):%Y%m%dT%H%M%S%f}-root-0001.md", "---\nfrom: root\nto: ceo\ntype: task\n---\nx\n")
    # a batch in flight and no record of the run: the latest log is the run
    assert [r.outcome for r in place.collector.collect(None, None, {}, ["ceo"])] == ["unknown", "running"]
    place.runs.registry.record("ceo", {"log": f"ceo/runs/{older}.log"})  # the registry names the run: that one
    assert [r.outcome for r in place.collector.collect(None, None, {}, ["ceo"])] == ["running", "unknown"]


# ------------------------------------------------------------------------------ many runs


def test_runs_are_the_logs_that_started_in_the_window_oldest_first(place: Place) -> None:
    for addr, n in (("ceo", 50), ("ceo/eng", 10), ("ceo", 30), ("ceo/eng", 90)):
        place.log(addr, n)
    assert [r.start for r in place.collector.collect(None, None, {})] == [stamp(10), stamp(30), stamp(50), stamp(90)]
    assert [r.start for r in place.collector.collect(stamp(30), stamp(50), {})] == [stamp(30), stamp(50)]
    assert [r.agent for r in place.collector.collect(None, None, {}, ["ceo/eng"])] == ["ceo/eng", "ceo/eng"]


def test_a_log_whose_name_is_not_a_time_is_no_run(place: Place) -> None:
    place.runs.put_log("ceo", "notes.log", "")
    place.log("ceo", 10)
    assert len(place.collector.collect(None, None, {})) == 1


def test_a_run_that_only_the_events_know_belongs_to_an_agent_that_is_gone(place: Place) -> None:
    gone, exists = "gone/agent@20261018T100100000000", "ceo/eng@20261018T100200000000"
    events: Events = {
        gone: {"start": ev("run.start", 60, batch=[], traces=[]), "end": ev("run.end", 72, ok=True, duration_ms=12000)},
        exists: {"start": ev("run.start", 120, batch=[], traces=[])},  # its agent exists but has no such log: not counted
        "ceo@nothing": {"end": ev("run.end", 5, ok=True)},  # no start event
        "broken": {"start": ev("run.start", 5)},  # no agent in the id
    }
    run = only(place.collector.collect(None, None, events))
    assert (run.run, run.agent, run.source, run.outcome, run.log, run.start) == (gone, "gone/agent", "events", "ok", None, stamp(60))
    assert place.collector.collect(None, None, events, ["ceo"]) == []  # named agents only: the retired are not asked about
    assert place.collector.collect(stamp(61), None, events) == []


def test_without_events_given_the_collector_reads_them_from_the_window(tmp_path: Path) -> None:
    mail, runs, log = memory_mailbox(tmp_path), memory_runs(tmp_path), memory_event_log(tmp_path)
    mail.agent("ceo")
    runs.add_agent("ceo")
    collector = RunCollector(runs.reader, runs.registry, cast(MemoryMailbox, mail.reader).agents, mail.reader, log.reader)
    name = f"{stamp(10):%Y%m%dT%H%M%S%f}"
    runs.put_log("ceo", f"{name}.log", "# exit 0 after 5s\n")
    log.log.emit(stamp(10.5), "run.start", proc="scheduler", pid=1, run=f"ceo@{name}", agent="ceo", batch=[], traces=["T1"])
    log.log.emit(stamp(16), "run.end", proc="scheduler", pid=1, run=f"ceo@{name}", agent="ceo", ok=False, exit_code=2, duration_ms=5500)
    run = only(collector.collect(stamp(0) - timedelta(seconds=1), None))
    assert (run.outcome, run.exit_code, run.traces, run.duration_ms) == ("failed", 2, ["T1"], 5500.0)


# ------------------------------------------------------------------------------ the runs of a team


def test_the_runs_of_a_team_are_its_logs_inside_the_windows(place: Place) -> None:
    for addr, n in (("ceo", 10), ("ceo/eng", 20), ("ceo", 30), ("ceo", 90)):
        place.log(addr, n)
    inside = [f"{stamp(n):%Y%m%dT%H%M%S%f}" for n in (10, 20, 30)]
    got = place.collector.team_runs(["ceo", "ceo/eng"], lambda stem: stem in inside, {})
    assert [(r.agent, r.start) for r in got] == [("ceo", stamp(10)), ("ceo/eng", stamp(20)), ("ceo", stamp(30))]
    assert place.collector.team_runs(["ceo/eng"], lambda stem: True, {})[0].agent == "ceo/eng"
    assert place.collector.team_runs([], lambda stem: True, {}) == []


def test_the_runs_of_a_team_are_completed_with_their_events_and_ignore_the_retired(place: Place) -> None:
    stem = place.log("ceo", 10)
    events: Events = {f"ceo@{stem}": {"start": ev("run.start", 10.1, batch=[], traces=["T"]), "end": ev("run.end", 20, ok=True, duration_ms=9900)},
                      "gone@20261018T100000000000": {"start": ev("run.start", 1, batch=[], traces=[])}}
    run = only(place.collector.team_runs(["ceo"], lambda s: True, events))
    assert (run.source, run.traces, run.duration_ms) == ("events", ["T"], 9900.0)
