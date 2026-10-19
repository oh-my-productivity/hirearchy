"""The whole life of a run over the in-memory ports: from mail to a finished batch, a failed one, one that never started, one that ran out of time."""

from __future__ import annotations

import signal

from orgmcp.scheduler._run import RunTable
from orgmcp.scheduler.testing import LifecycleWorld, lifecycle_world

from ._support import red

pytestmark = red


def world(config: str = "") -> LifecycleWorld:
    w = lifecycle_world()
    if config:
        w.access.put_config(f"---\n{config}\n---\n# Organization\n")
    w.hire("ceo", 3)
    w.mail_to("ceo", trace="t1")
    return w


def test_a_run_from_mail_to_a_finished_batch() -> None:
    w = world()
    w.table.will_exit(0, after=5, output="the agent speaks\n")
    runs: RunTable = {}
    assert w.lifecycle.starter.launch(runs, set(), None) == 1
    run = runs["ceo"]
    log = w.runs_store.read_log(run.log)
    assert log is not None and log.decode().startswith("# run of ceo, 1 message(s)\n# senders: root\n# cwd: /memory/work\n# cmd: kiro-cli chat <prompt on stdin>\n")
    assert log.decode().endswith("# ---- output ----\nthe agent speaks\n")
    assert w.spawner.spawned[0].stdin == "THE PROMPT" and w.spawner.spawned[0].env["ORG_RUN_ID"] == run.run_id
    assert w.runs_store.all()["ceo"]["pgid"] == run.proc.pid and w.console.lines == ["ceo: started run (1 message(s))"]
    (start,) = w.events_of("run.start")
    assert start["run"] == run.run_id and start["child_pid"] == run.proc.pid and start["budget_before"] == 3 and start["trace"] == "t1"
    w.lifecycle.reaper.reap(runs)
    assert "ceo" in runs  # still running
    w.clock.advance(5)
    w.lifecycle.reaper.reap(runs)
    assert runs == {} and w.runs_store.all() == {} and w.box.messages("ceo", "inflight") == []
    assert (w.runs_store.read_log(run.log) or b"").decode().endswith("the agent speaks\n\n# exit 0 after 5s\n")
    (end,) = w.events_of("run.end")
    assert (end["ok"], end["exit_code"], end["timed_out"], end["killed"], end["error"]) == (True, 0, False, False, None)
    assert w.console.lines[-1] == "ceo: run finished in 5s" and w.snapshots.commits[-1].startswith("ceo: run ok, 1 message(s) [ceo/runs/")


def test_failed_runs_are_counted_and_the_agent_is_paused_at_the_limit() -> None:
    w = world("max_failures: 2")
    runs: RunTable = {}
    for attempt in (1, 2):
        w.table.will_exit(1)
        w.lifecycle.starter.launch(runs, set(), None)
        w.lifecycle.reaper.reap(runs)
        assert w.box.messages("ceo", "inbox") != [] and runs == {}
        assert w.console.lines[-1].startswith(f"ceo: run failed ({attempt} in a row)")
        w.pauses.resume("ceo", "") if attempt == 1 else None
    assert w.pauses.paused("ceo") == "failures" and [m.to for m in w.delivery.messages] == ["root"]
    assert [e["count"] for e in w.events_of("agent.failure")] == [1, 2]


def test_a_process_that_cannot_start_is_a_failed_run_with_both_events() -> None:
    w = world()
    w.spawner.fail = FileNotFoundError("kiro-cli")
    runs: RunTable = {}
    assert w.lifecycle.starter.launch(runs, set(), None) == 1
    assert runs == {} and w.count.total == 1 and w.box.messages("ceo", "inbox") != []
    assert [e["agent"] for e in w.events_of("run.start")] == ["ceo"] and w.events_of("run.end")[0]["error"] == "failed to start: kiro-cli"
    assert w.events_of("agent.failure")[0]["count"] == 1 and w.runs_store.all() == {}
    (log,) = w.runs_store.files("ceo")
    assert (w.runs_store.read_log(log.path) or b"").decode().endswith("\n# failed to start: kiro-cli\n")


def test_a_run_past_the_timeout_is_killed_by_the_run_clock_with_its_whole_group() -> None:
    w = world("run_timeout: 30")
    runs: RunTable = {}
    w.lifecycle.starter.launch(runs, set(), None)
    run = runs["ceo"]
    tool = w.table.add_member(run.proc.pid)
    w.clock.advance(31)
    w.lifecycle.reaper.reap(runs)
    assert runs == {} and not w.table.is_alive(tool) and ("group", run.proc.pid, signal.SIGKILL) in w.table.signals
    (end,) = w.events_of("run.end")
    assert (end["ok"], end["timed_out"], end["killed"], end["error"]) == (False, True, True, "timed out: killed after 30s")
    assert (w.runs_store.read_log(run.log) or b"").decode().endswith("\n# killed after 30s timeout\n\n# exit -9 after 31s\n")
    assert w.box.messages("ceo", "inbox") != []


def test_a_retired_agent_loses_its_run() -> None:
    w = world()
    runs: RunTable = {}
    w.lifecycle.starter.launch(runs, set(), None)
    child = w.table.add_member(runs["ceo"].proc.pid)
    w.retire("ceo")
    w.lifecycle.reaper.reap(runs)
    assert runs == {} and not w.table.is_alive(child) and w.runs_store.all() == {}
    assert w.events_of("run.end")[0]["error"] == "killed: the agent was retired during its run"
    assert w.snapshots.commits == ["ceo: run ended after retirement (exit -9)"]


def test_the_cap_on_runs_started_counts_a_failed_start() -> None:
    w = world()
    w.hire("ops", 2)
    w.mail_to("ops")
    w.spawner.fail = OSError("no")
    runs: RunTable = {}
    assert w.lifecycle.starter.launch(runs, set(), 1) == 1 and w.count.total == 1
    assert w.lifecycle.starter.launch(runs, set(), 1) == 0


def test_shutdown_interrupts_the_runs_in_flight() -> None:
    w = world()
    runs: RunTable = {}
    w.lifecycle.starter.launch(runs, set(), None)
    run = runs["ceo"]
    w.lifecycle.reaper.terminate_all(runs)
    assert runs == {} and w.runs_store.all() == {} and w.box.messages("ceo", "inbox") != [] and run.killed
    assert w.events_of("run.end")[0]["error"] == "interrupted by scheduler shutdown"
