"""Contract of ``IntegrityChecks``: the six invariants of the runtime, over an organization on disk and one in memory.

Each invariant is shown holding and then broken, the way a live system breaks it: a message copy lost, an id twice, a budget that does not add up, a
batch with no run, a run that never ended, a gap in the lines of an event file, a pid file nobody keeps."""

from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest

from orgmcp.daemon import SchedulerState
from orgmcp.kernel import JsonObject
from orgmcp.observability import IntegrityChecks
from orgmcp.observability.testing import IMPLEMENTATIONS, ObservabilityWorld

from . import _support
from ._support import items, stamp


NOW = stamp(500)
RUNNING = SchedulerState("running", 7000, "2026-10-18 10:00:00Z")


@pytest.fixture(params=_support.implementations(IMPLEMENTATIONS[IntegrityChecks]))
def w(request: pytest.FixtureRequest, tmp_path: Path) -> ObservabilityWorld:
    made: ObservabilityWorld = request.param(tmp_path)
    assert isinstance(made.checks, IntegrityChecks)
    for addr in ("ceo", "ceo/eng"):
        made.agent(addr)
    return made


def verdicts(w: ObservabilityWorld) -> dict[str, JsonObject]:
    w.settle()
    return {str(c["id"]): c for c in items(w.checks.check(NOW), "checks")}


def details(w: ObservabilityWorld, cid: str) -> list[str]:
    return cast("list[str]", verdicts(w)[cid]["details"])


def grant(w: ObservabilityWorld, runs: int = 3) -> str:
    """Root hands ``runs`` to ceo, which holds them."""
    msg = w.send("root", "ceo", "task", 10, title="Ship", budget=runs, trace="self")
    w.budgets.held["ceo"] = runs
    return msg.id


def test_an_organization_nothing_happened_in_passes(w: ObservabilityWorld) -> None:
    result = w.checks.check(NOW)
    assert result["ok"] is True and [c["id"] for c in items(result, "checks")] == ["a", "b", "c", "d", "e", "f"]
    assert all(c["ok"] for c in items(result, "checks")) and set(items(result, "checks")[0]) == {"id", "name", "ok", "details"}


def test_the_default_time_is_the_clock(w: ObservabilityWorld) -> None:
    w.clock.advance(500)
    w.settle()
    assert w.checks.check()["ok"] is True


def test_the_verdict_is_the_conjunction_of_the_checks(w: ObservabilityWorld) -> None:
    grant(w)
    w.budgets.held["ceo"] = 1
    result = w.checks.check(NOW)
    assert result["ok"] is False and [c["ok"] for c in items(result, "checks")] == [True, False, True, True, True, True]


def test_the_names_of_the_checks(w: ObservabilityWorld) -> None:
    assert [c["name"] for c in items(w.checks.check(NOW), "checks")] == [
        "messages intact: files parse, ids unique, sender and recipient copies match",
        "budget conserved: handed down = held + used + returned (+ dropped at retirement)",
        "nothing inflight without a live run",
        "runs accounted for: run.start has run.end or a live process; run logs have run.start",
        "event files have no seq gaps",
        "scheduler pid file matches a live scheduler",
    ]


# ------------------------------------------------------------------------------ (a) messages intact


def test_messages_with_both_copies_are_intact(w: ObservabilityWorld) -> None:
    grant(w)
    assert details(w, "a") == ["1 message(s) checked"] and verdicts(w)["a"]["ok"] is True


def test_a_recipient_copy_that_is_lost_is_found(w: ObservabilityWorld) -> None:
    mid = grant(w)
    w.remove(f"ceo/inbox/{mid}.md")
    v = verdicts(w)["a"]
    assert v["ok"] is False and details(w, "a") == [f"{mid}: sent by root to ceo but ceo has no copy (recover() or a run start re-delivers it)"]


def test_a_sender_copy_that_is_lost_is_found(w: ObservabilityWorld) -> None:
    mid = grant(w)
    w.remove(f"sent/{mid}.md")
    assert details(w, "a") == [f"{mid}: in ceo/inbox from root but root has no sent copy"]


def test_an_id_among_the_received_copies_twice_is_found(w: ObservabilityWorld) -> None:
    mid = grant(w)
    w.put(f"ceo/read/{mid}.md", w.read(f"ceo/inbox/{mid}.md") or "")
    assert details(w, "a") == [f"id {mid} appears 2 times among received copies (ceo/inbox, ceo/read)"]


def test_a_file_that_does_not_parse_is_found(w: ObservabilityWorld) -> None:
    w.put("ceo/read/broken.md", "no front matter at all\n")
    assert details(w, "a") == ["ceo/read/broken.md: no frontmatter"]


def test_a_file_in_the_box_of_somebody_else_is_found(w: ObservabilityWorld) -> None:
    mid = grant(w)
    w.put(f"ceo/eng/inbox/{mid}.md", w.read(f"ceo/inbox/{mid}.md") or "")
    assert any(d == f"ceo/eng/inbox/{mid}.md: in the inbox/ of ceo/eng but addressed to ceo" for d in details(w, "a"))


# ------------------------------------------------------------------------------ (b) budget conserved


def test_what_root_handed_down_is_held_or_used(w: ObservabilityWorld) -> None:
    grant(w)
    assert verdicts(w)["b"]["ok"] is True
    assert details(w, "b") == ["handed down 3 = held 3 + used 0 live + 0 retired + returned 0 + dropped 0"]


def test_runs_that_were_used_count(w: ObservabilityWorld) -> None:
    grant(w)
    w.run_log("ceo", 20)
    w.budgets.held["ceo"] = 2
    assert details(w, "b") == ["handed down 3 = held 2 + used 1 live + 0 retired + returned 0 + dropped 0"]


def test_runs_that_vanished_are_found_with_the_difference(w: ObservabilityWorld) -> None:
    grant(w)
    w.budgets.held["ceo"] = 1
    assert verdicts(w)["b"]["ok"] is False
    assert details(w, "b") == ["handed down 3 = held 1 + used 0 live + 0 retired + returned 0 + dropped 0: 2 run(s) vanished (difference +2)"]


def test_runs_that_appeared_from_nowhere_are_found(w: ObservabilityWorld) -> None:
    grant(w)
    w.budgets.held["ceo"] = 5
    assert details(w, "b")[0].endswith(": 2 run(s) appeared from nowhere (difference -2)")


def test_runs_returned_to_root_count(w: ObservabilityWorld) -> None:
    grant(w)
    w.send("ceo", "root", "result", 30, title="Ship", budget=2, status="done", box="read")
    w.budgets.held["ceo"] = 1
    assert verdicts(w)["b"]["ok"] is True and "returned 2" in details(w, "b")[0]


# ------------------------------------------------------------------------------ (c) nothing inflight without a live run


def test_a_batch_whose_run_is_recorded_alive_is_accounted_for(w: ObservabilityWorld) -> None:
    grant(w)
    w.begin_run("ceo")
    w.running("ceo", w.run_log("ceo", 20))
    w.judge.verdict = "ours"
    assert verdicts(w)["c"]["ok"] is True


def test_a_batch_whose_process_is_gone_is_found(w: ObservabilityWorld) -> None:
    grant(w)
    w.begin_run("ceo")
    w.running("ceo", w.run_log("ceo", 20))
    w.judge.verdict = "gone"
    assert details(w, "c")[0].startswith("ceo: 1 message(s) inflight for ") and details(w, "c")[0].endswith("but no live run (no scheduler is running)")


def test_a_batch_with_no_record_is_found_and_the_scheduler_is_named(w: ObservabilityWorld) -> None:
    grant(w)
    w.begin_run("ceo")
    w.scheduler.current = RUNNING
    assert details(w, "c")[0].endswith("but no live run (the scheduler has no live process for it)")


def test_a_process_in_doubt_is_given_the_benefit_of_it(w: ObservabilityWorld) -> None:
    grant(w)
    w.begin_run("ceo")
    w.running("ceo", w.run_log("ceo", 20))
    w.judge.verdict = "doubt"
    assert verdicts(w)["c"]["ok"] is True


# ------------------------------------------------------------------------------ (d) runs accounted for


def test_a_run_that_started_and_ended_is_accounted_for(w: ObservabilityWorld) -> None:
    stem = w.run_log("ceo", 20)
    w.run_events("ceo", stem, 20, 10, [], [])
    assert verdicts(w)["d"]["ok"] is True and details(w, "d") == ["1 run.start event(s) checked"]


def test_a_run_that_never_ended_is_found(w: ObservabilityWorld) -> None:
    stem = w.run_log("ceo", 20)
    w.emit(20, "run.start", proc="scheduler", pid=7000, run=f"ceo@{stem}", agent="ceo", batch=[], traces=[], pgid=1)
    assert details(w, "d") == [f"ceo@{stem}: run.start at {stamp(20).isoformat()} has no run.end and no live process"]


def test_a_run_that_never_ended_but_lives_is_accounted_for(w: ObservabilityWorld) -> None:
    stem = w.run_log("ceo", 20)
    w.emit(20, "run.start", proc="scheduler", pid=7000, run=f"ceo@{stem}", agent="ceo", batch=[], traces=[], pgid=1)
    w.running("ceo", stem)
    w.judge.verdict = "ours"
    assert verdicts(w)["d"]["ok"] is True


def test_a_run_log_without_a_start_is_found_once_events_began(w: ObservabilityWorld) -> None:
    w.emit(0, "scheduler.start", proc="scheduler", pid=7000, mode="daemon")
    stem = w.run_log("ceo", 20)
    assert details(w, "d") == [f"ceo@{stem}: run log without a run.start event (events began {stamp(0).isoformat(timespec='seconds')})"]


def test_without_run_events_the_check_is_skipped(w: ObservabilityWorld) -> None:
    w.run_log("ceo", 20)
    assert details(w, "d") == ["no run events yet (skipped)"] and verdicts(w)["d"]["ok"] is True


# ------------------------------------------------------------------------------ (e) seq gapless


def test_lines_numbered_from_one_without_gaps_are_fine(w: ObservabilityWorld) -> None:
    for i in range(3):
        w.tool(10 + i, "ceo", "inbox")
    assert verdicts(w)["e"]["ok"] is True and details(w, "e") == ["1 event file(s) checked"]


def test_a_gap_is_found_with_the_lines_lost(w: ObservabilityWorld) -> None:
    for i in range(2):
        w.tool(10 + i, "ceo", "inbox")
    w.emit(20, "tool.call", actor="ceo", tool="inbox", ok=True, ms=1, seq=5)
    (line,) = details(w, "e")
    assert line.endswith("seq jumps from 2 to 5 (2 line(s) lost)")


def test_a_file_that_starts_late_is_found(w: ObservabilityWorld) -> None:
    w.emit(20, "tool.call", actor="ceo", tool="inbox", ok=True, ms=1, seq=4)
    assert details(w, "e")[0].endswith("first seq is 4, expected 1")


# ------------------------------------------------------------------------------ (f) pid file


def test_with_no_pid_file_no_scheduler_claims_to_run(w: ObservabilityWorld) -> None:
    assert details(w, "f") == ["no pid file: no scheduler claims to run"]


def test_a_pid_file_of_the_running_scheduler_is_fine(w: ObservabilityWorld) -> None:
    w.pidfile("7000")
    w.scheduler.current = RUNNING
    assert verdicts(w)["f"]["ok"] is True and details(w, "f") == ["pid 7000 is this organization's scheduler"]


def test_a_pid_file_nobody_keeps_is_stale(w: ObservabilityWorld) -> None:
    w.pidfile("999999")
    assert verdicts(w)["f"]["ok"] is False
    assert details(w, "f") == [".runtime/scheduler.pid is stale: its process is gone (a scheduler start replaces it; remove it if none will start)"]


def test_a_pid_file_of_a_process_that_is_not_our_scheduler_is_not_trusted(w: ObservabilityWorld) -> None:
    w.pidfile("4242")
    w.scheduler.current = SchedulerState("unverified", 4242, "x", "its command line is 'vim'")
    assert details(w, "f") == [".runtime/scheduler.pid names pid 4242, alive but not verified as this org's scheduler (its command line is 'vim')"]


def test_asking_changes_nothing(w: ObservabilityWorld, tmp_path: Path) -> None:
    grant(w)
    w.pidfile("999999")
    w.settle()

    def snapshot() -> list[tuple[str, int, int]]:
        return sorted((str(p), p.stat().st_mtime_ns, p.stat().st_size) for p in tmp_path.rglob("*") if p.is_file())

    before = snapshot()
    w.checks.check(NOW)
    assert snapshot() == before
