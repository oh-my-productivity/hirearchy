#!/usr/bin/env python3
"""Offline check of the F-E4-9 fix in inject_root_rework.py (protocol 5.3 step 4). No server, no org, no sandbox, no model call:
progress() is a stub and the clock and the sleep are fakes, so the 20-minute window runs in milliseconds.
Usage: python3 test_poll_loop.py        (exit 0 when every scenario holds; it also runs under pytest)"""
from __future__ import annotations

import asyncio
import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("inject_root_rework", HERE / "inject_root_rework.py")
inj = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(inj)

TASK = "20261022T215128895860-root-fe20"
NOT_WAITING = "Not waiting: nothing can progress without you.\n- weekly-memo (task {t}): open, lead busy\nscheduler: stopped".format(t=TASK)
DONE_RUNNING = "- weekly-memo (task {t}): done, runs 5 of 6\nscheduler: running (pid 1)".format(t=TASK)
DONE_STOPPED = "- weekly-memo (task {t}): done, runs 5 of 6\nscheduler: stopped (finished: no open tasks)".format(t=TASK)


class Clock:
    def __init__(self) -> None:
        self.t = 1000.0

    def __call__(self) -> float:
        return self.t

    async def sleep(self, s: float) -> None:
        self.t += s


class Lines:
    def __init__(self) -> None:
        self.lines: list[str] = []

    def write(self, text: str) -> None:
        self.lines.append(text)


def run(reply_for, took_for, window=inj.WINDOW_MAX):
    """reply_for(n, clock) -> reply text of poll n (1-based); took_for(n, args) -> seconds the server took."""
    clock, log, calls = Clock(), Lines(), []

    async def progress(args, timeout):
        calls.append((clock.t, dict(args), timeout))
        n = len(calls)
        clock.t += took_for(n, args)
        return reply_for(n, clock)

    stats = asyncio.run(inj.poll_until_settled(progress, TASK, clock.t, log, window=window, clock=clock, sleep=clock.sleep))
    return stats, calls, log.lines, clock


def test_s2_state_progress_returns_at_once_and_nothing_moves():
    """E4 s2: 36,513 polls in 7 minutes. Now: paced, bounded by the 20-minute window, every poll logged."""
    stats, calls, lines, clock = run(lambda n, c: NOT_WAITING, lambda n, a: 0.01)
    assert stats["end"] == "window cap: 20 minutes passed", stats
    assert 2 <= stats["polls"] <= 30, stats
    assert stats["quick_replies"] == stats["polls"]
    assert abs((clock.t - 1000.0) - inj.WINDOW_MAX) < 1.0  # the loop used the whole window, by pausing
    gaps = [b[0] - a[0] for a, b in zip(calls, calls[1:])]
    assert all(g >= inj.PAUSE_START for g in gaps), gaps  # never two polls closer than 5 s
    assert max(gaps) <= inj.PAUSE_MAX + 1.0, gaps
    assert all(a == {"task_id": TASK, "wait_seconds": a["wait_seconds"]} for _, a, _ in calls)  # the E4 arguments, nothing else
    assert calls[0][1]["wait_seconds"] == 300 and calls[0][2] == 480  # wait_seconds = min(300, time left); timeout = wait + 180
    assert sum(1 for ln in lines if ln.startswith("poll ")) == stats["polls"]
    assert "window cap: 20 minutes passed" in lines
    assert lines[-1].startswith("polling ended (window cap: 20 minutes passed): progress(task_id) polls ")


def test_s3_state_done_while_the_scheduler_still_runs_then_stops():
    """E4 s3: about 490 polls in 7 s once the task was done and the scheduler had not yet exited. Now: a few paced polls."""
    stats, calls, lines, clock = run(lambda n, c: DONE_RUNNING if c.t < 1007.0 else DONE_STOPPED, lambda n, a: 0.01)
    assert stats["end"].startswith("settled"), stats
    assert stats["polls"] == 3, stats  # t=0 (running), pause 5; t=5 (running), pause 10; t=15 (stopped): settled
    assert lines[-2].startswith("poll 3: reply after") and lines[-2].endswith("; settled")


def test_a_server_that_waits_is_not_paused():
    stats, calls, lines, clock = run(lambda n, c: NOT_WAITING, lambda n, a: float(a["wait_seconds"]))
    assert stats == {"polls": 4, "quick_replies": 0, "paused_seconds": 0.0, "end": "window cap: 20 minutes passed"}, stats
    assert [a["wait_seconds"] for _, a, _ in calls] == [300, 300, 300, 300]


def test_settled_on_the_first_poll():
    stats, calls, lines, clock = run(lambda n, c: DONE_STOPPED, lambda n, a: 2.0)
    assert stats["polls"] == 1 and stats["end"].startswith("settled") and stats["paused_seconds"] == 0.0


def test_the_pause_resets_after_a_reply_that_waited():
    # quick, quick, waited, quick: pauses 5, 10, (reset), 5
    took = {1: 0.01, 2: 0.01, 3: 30.0, 4: 0.01, 5: 0.01}
    stats, calls, lines, clock = run(lambda n, c: DONE_STOPPED if n == 5 else NOT_WAITING, lambda n, a: took[n])
    pauses = [ln for ln in lines if "pausing" in ln]
    assert [p.split("pausing ")[1].split("s ")[0] for p in pauses] == ["5.0", "10.0", "5.0"], pauses
    assert stats["polls"] == 5 and stats["end"].startswith("settled")


def test_the_poll_cap_bounds_the_calls():
    old = inj.MAX_POLLS
    inj.MAX_POLLS = 3
    try:
        stats, calls, lines, clock = run(lambda n, c: NOT_WAITING, lambda n, a: 0.01)
    finally:
        inj.MAX_POLLS = old
    assert stats["polls"] == 3 and stats["end"] == "poll cap: 3 polls", stats


def test_the_poll_check_window():
    stats, calls, lines, clock = run(lambda n, c: NOT_WAITING, lambda n, a: 0.01, window=120.0)
    assert stats["end"] == "window cap: 120 seconds passed", stats
    assert stats["polls"] == 5, stats  # t=0, 5, 15, 35, 75 (pauses 5, 10, 20, 40, then 45 to the end of the window)
    assert calls[0][1]["wait_seconds"] == 120


def main() -> int:
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS {t.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL {t.__name__}: {e}")
    print(f"{len(tests) - failed} passed, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
