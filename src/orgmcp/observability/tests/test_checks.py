"""One test per invariant, each on the corrupted scenario (``_scenario.corrupt``: every kind of damage a check looks for, once) and on a healthy one."""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any

import pytest

from orgmcp.kernel import ROOT
from orgmcp.observability import IntegrityChecks
from orgmcp.observability._checks import COPY_GRACE, INFLIGHT_GRACE, FileIntegrityChecks, JudgedLiveRuns
from orgmcp.observability._ports import IntegrityCheck, LiveRuns

from . import _scenario
from ._scenario import NOW, SCENARIOS, VerdictJudge, follow_ports, old, settle, stamp
from ._second import Second
from ._support import items


STOPPED = ("stopped", None, None, "")


def second(built: Any, name: str, state: tuple[str, int | None, str | None, str] | None = None, verdict: str | None = None) -> Second:
    setup, scheduler, judged = SCENARIOS[name]
    setup(built)
    settle(built.org)
    return Second(follow_ports(built.org, state or scheduler, verdict or judged))


def run(part: IntegrityCheck, second: Second, now: datetime = NOW) -> dict[str, Any]:
    result: dict[str, Any] = part.run(second.index.scan(), now.timestamp())
    return result


def test_the_six_invariants_in_order(built: Any) -> None:
    s = second(built, "story")
    assert [type(p).__name__ for p in s.parts] == ["MessagesIntact", "BudgetConserved", "InflightAccounted", "RunsAccounted", "SeqGapless", "PidfileSane"]
    assert all(isinstance(p, IntegrityCheck) for p in s.parts) and isinstance(s.checks, IntegrityChecks) and isinstance(s.live, LiveRuns)
    assert [c["id"] for c in items(s.checks.check(NOW), "checks")] == ["a", "b", "c", "d", "e", "f"]


def test_a_healthy_organization_passes_every_check(built: Any) -> None:
    result = second(built, "story").checks.check(NOW)
    assert result["ok"] is True and all(c["ok"] for c in items(result, "checks"))


def test_the_verdict_is_ok_only_when_all_are(built: Any) -> None:
    result = second(built, "corrupt").checks.check(NOW)
    assert result["ok"] is False and [c["ok"] for c in items(result, "checks")] == [False] * 6


# ------------------------------------------------------------------------------ (a) messages intact


def test_a_message_file_named_after_another_id_is_found(built: Any) -> None:
    s = second(built, "corrupt")
    result = run(s.messages, s)
    assert result["id"] == "a" and result["ok"] is False
    assert "ceo/read/renamed.md: file name differs from its id 20261018T100001000000-root-aaaa" in result["details"]


def test_a_file_that_does_not_parse_is_found(built: Any) -> None:
    s = second(built, "corrupt")
    assert "ceo/read/broken.md: no frontmatter" in run(s.messages, s)["details"]


def test_a_message_in_the_box_of_somebody_else_is_found(built: Any) -> None:
    s = second(built, "corrupt")
    assert "ceo/eng/inflight/20261018T100002000000-root-bbbb.md: in the inflight/ of ceo/eng but addressed to ceo" in run(s.messages, s)["details"]


def test_an_id_twice_among_received_copies_is_found(built: Any) -> None:
    s = second(built, "corrupt")
    assert "id 20261018T100003000000-root-cccc appears 2 times among received copies (ceo/inbox, ceo/read)" in run(s.messages, s)["details"]


def test_a_sender_copy_without_a_recipient_copy_is_found_once_it_is_older_than_the_grace(built: Any) -> None:
    s = second(built, "corrupt")
    missing = "20261018T100004000000-ceo-dddd: sent by ceo to ceo/eng but ceo/eng has no copy (recover() or a run start re-delivers it)"
    assert missing in run(s.messages, s)["details"]
    sent = next(built.org.dir("ceo").glob("sent/20261018T100004000000-ceo-dddd.md"))
    old(sent, 200 - COPY_GRACE + 1)  # written a moment before NOW: the other copy is being written
    assert missing not in run(s.messages, s)["details"]


def test_a_recipient_copy_without_a_sender_copy_is_found(built: Any) -> None:
    s = second(built, "corrupt")
    assert "20261018T100001000000-root-aaaa: in ceo/read from root but root has no sent copy" in run(s.messages, s)["details"]


def test_a_healthy_organization_counts_its_messages(built: Any) -> None:
    s = second(built, "story")
    result = run(s.messages, s)
    assert result["ok"] is True and result["details"] == [f"{len({f.id for f in s.index.scan()})} message(s) checked"]


def test_more_than_eight_problems_are_cut_with_the_count_of_the_rest(built: Any) -> None:
    s = second(built, "corrupt")
    for n in range(10):
        _scenario.write(built.org, f"ceo/read/odd-{n}.md", {"id": f"20261018T1010{n:02d}000000-root-ffff", "from": ROOT, "to": "ceo", "type": "note"})
    details = run(s.messages, s)["details"]
    assert len(details) == 9 and details[-1].startswith("... and ") and details[-1].endswith(" more")


# ------------------------------------------------------------------------------ (b) budget conserved


def test_a_budget_off_by_four_is_found_with_the_equation(built: Any) -> None:
    s = second(built, "corrupt")
    result = run(s.budget, s)
    assert result["id"] == "b" and result["ok"] is False
    assert result["details"] == ["handed down 11 = held 5 + used 5 live + 0 retired + returned 3 + dropped 0: 2 run(s) appeared from nowhere (difference -2)"]


def test_the_budget_of_retired_agents_is_counted_used_and_dropped(built: Any) -> None:
    s = second(built, "retired")
    result = run(s.budget, s)
    assert result["ok"] is True and result["details"] == ["handed down 19 = held 7 + used 4 live + 1 retired + returned 3 + dropped 4"]


def test_a_message_being_delivered_is_counted_in_delivery(built: Any) -> None:
    s = second(built, "story")
    fresh = _scenario.write(built.org, "sent/20261018T100500000000-root-eeee.md",
                            {"id": "20261018T100500000000-root-eeee", "from": ROOT, "to": "ceo", "type": "task", "budget": 3})
    old(fresh, 199)  # one second before NOW: the recipient copy is written a moment later
    result = run(s.budget, s)
    assert result["ok"] is True and result["details"][0].endswith(" + 3 in delivery")
    old(fresh, 100)  # ... but not forever
    assert run(s.budget, s)["ok"] is False


def test_a_budget_that_cannot_be_computed_says_so(built: Any) -> None:
    s = second(built, "story")
    _scenario.write(built.org, "ceo/inbox/20261018T100600000000-root-gggg.md", {"id": "20261018T100600000000-root-gggg", "from": ROOT, "to": "ceo",
                                                                                "type": "task", "budget": "lots"})
    result = run(s.budget, s)
    assert result["ok"] is False and result["details"][0].startswith("cannot compute the agents' budgets: ")


# ------------------------------------------------------------------------------ (c) inflight accounted


def test_a_batch_inflight_with_no_run_is_found_when_no_scheduler_runs(built: Any) -> None:
    s = second(built, "corrupt")
    result = run(s.inflight, s)
    assert result["id"] == "c" and result["ok"] is False
    assert result["details"] == ["ceo/eng: 2 message(s) inflight for 1m40s but no live run (no scheduler is running)"]


def test_a_batch_just_begun_under_a_running_scheduler_is_given_a_moment(built: Any) -> None:
    s = second(built, "corrupt", state=_scenario.RUNNING)
    batch = list((built.org.dir("ceo/eng") / "inflight").glob("*.md"))
    assert run(s.inflight, s)["details"] == ["ceo/eng: 2 message(s) inflight for 1m40s but no live run (the scheduler has no live process for it)"]
    for path in batch:
        old(path, 200 - INFLIGHT_GRACE + 1)
    assert run(s.inflight, s)["ok"] is True


def test_a_batch_whose_recorded_process_lives_is_accounted_for(built: Any) -> None:
    s = second(built, "busy")
    for path in (built.org.dir("ceo") / "inflight").glob("*.md"):
        old(path, -600)
    assert run(s.inflight, s)["ok"] is True


def test_a_batch_whose_recorded_process_is_gone_is_found(built: Any) -> None:
    setup, state, _ = SCENARIOS["busy"]
    setup(built)
    settle(built.org)
    s = Second(follow_ports(built.org, state, "gone"))
    for path in (built.org.dir("ceo") / "inflight").glob("*.md"):
        old(path, -600)
    assert run(s.inflight, s)["ok"] is False


def test_an_organization_without_batches_has_nothing_to_find(built: Any) -> None:
    s = second(built, "story")
    assert run(s.inflight, s) == {"id": "c", "name": "nothing inflight without a live run", "ok": True,
                                  "details": ["no agent has an unfinished batch without a run"]}


# ------------------------------------------------------------------------------ (d) runs accounted


def test_a_run_start_without_an_end_and_a_run_log_without_a_start_are_found(built: Any) -> None:
    s = second(built, "corrupt")
    result = run(s.runs, s)
    assert result["id"] == "d" and result["ok"] is False
    assert result["details"][0] == "ceo@20261018T100230000000: run.start at 2026-10-18T10:02:30+00:00 has no run.end and no live process"
    assert result["details"][1].startswith("ceo/eng@") and result["details"][1].endswith("run log without a run.start event (events began 2026-10-18T10:00:00+00:00)")


def test_a_run_that_started_and_ended_is_accounted_for(built: Any) -> None:
    s = second(built, "story")
    assert run(s.runs, s)["details"] == ["5 run.start event(s) checked"]


def test_an_organization_without_run_events_skips_the_check(bare: Any) -> None:
    s = Second(follow_ports(bare, STOPPED, "gone"))
    assert run(s.runs, s) == {"id": "d", "name": "runs accounted for: run.start has run.end or a live process; run logs have run.start", "ok": True,
                              "details": ["no run events yet (skipped)"]}


# ------------------------------------------------------------------------------ (e) seq gapless


def test_a_gap_in_the_lines_of_a_file_is_found(built: Any) -> None:
    s = second(built, "corrupt")
    result = run(s.seq, s)
    assert result["id"] == "e" and result["ok"] is False
    assert result["details"] == ["2026-10-18/mcp-4242-1792317600001.jsonl: seq jumps from 10 to 13 (2 line(s) lost)"]


def test_files_without_gaps_are_counted(built: Any) -> None:
    s = second(built, "story")
    assert run(s.seq, s)["details"] == ["5 event file(s) checked"]


# ------------------------------------------------------------------------------ (f) pid file sane


def test_a_stale_pid_file_is_found(built: Any) -> None:
    s = second(built, "corrupt")
    result = run(s.pidfile, s)
    assert result["id"] == "f" and result["ok"] is False
    assert result["details"] == [".runtime/scheduler.pid is stale: its process is gone (a scheduler start replaces it; remove it if none will start)"]


def test_a_pid_file_of_a_process_that_is_not_our_scheduler_is_not_trusted(built: Any) -> None:
    s = second(built, "corrupt_unverified")
    assert run(s.pidfile, s)["details"] == [
        ".runtime/scheduler.pid names pid 4242, alive but not verified as this org's scheduler (its command line is 'vim')"]


def test_a_pid_file_of_the_running_scheduler_passes(built: Any) -> None:
    s = second(built, "corrupt", state=_scenario.RUNNING)
    assert run(s.pidfile, s) == {"id": "f", "name": "scheduler pid file matches a live scheduler", "ok": True,
                                 "details": ["pid 7000 is this organization's scheduler"]}


def test_no_pid_file_means_no_scheduler_claims_to_run(built: Any) -> None:
    s = second(built, "story")
    assert run(s.pidfile, s)["details"] == ["no pid file: no scheduler claims to run"]


# ------------------------------------------------------------------------------ the object that runs them


def test_the_default_time_is_the_clock(built: Any) -> None:
    s = second(built, "story")
    assert s.checks.check()["ok"] is True  # the clock of the scenario is at the time of the story


def test_checks_are_run_in_the_order_they_are_given_and_a_new_one_is_a_new_class(built: Any) -> None:
    class Extra(IntegrityCheck):
        def run(self, files: Any, now: float) -> dict[str, Any]:
            return {"id": "z", "name": "extra", "ok": True, "details": [f"{len(files)} files at {now}"]}

    s = second(built, "story")
    checks = FileIntegrityChecks(s.index, [Extra(), *s.parts[:1]], built.org.runtime.clock)
    result = checks.check(NOW)
    assert [c["id"] for c in items(result, "checks")] == ["z", "a"] and result["ok"] is True
    assert str(items(result, "checks")[0]["details"]).endswith(f" files at {NOW.timestamp()}']")


def test_a_live_run_is_one_the_judge_calls_ours_or_in_doubt() -> None:
    record = {"pgid": 123, "lstart": "x"}
    assert [JudgedLiveRuns(VerdictJudge(v)).live(record) for v in ("ours", "doubt", "gone", "foreign")] == [True, True, False, False]
    assert JudgedLiveRuns(VerdictJudge("ours")).live(None) is False and JudgedLiveRuns(VerdictJudge("ours")).live({}) is False


def test_checking_changes_nothing(built: Any) -> None:
    s = second(built, "corrupt")
    org = built.org

    def snapshot() -> list[tuple[str, int, int]]:
        return sorted((str(p), p.stat().st_mtime_ns, p.stat().st_size) for p in org.root.rglob("*") if p.is_file())

    before = snapshot()
    s.checks.check(NOW)
    s.now.now_view(NOW)
    assert snapshot() == before
    assert os.path.exists(org.root / ".runtime" / "scheduler.pid") and stamp(0) < NOW
