#!/usr/bin/env python3
"""C1 verdict (stdlib only; design 6.1 Setup 5, DR-0a4-5). Run by a LATER call, after SB/samples/<ID>-turn<K>.done exists.

Reads SB/samples/<ID>-turn<K>.{jsonl,meta.json} and the org's events; prints and writes SB/samples/<ID>-turn<K>.verdict.json.
Class, first match: no-run / finished / run-ended-ok (invalid), died, run-only, survived. --c1b adds the first scheduler.signal and the M5 signature.
"""
from __future__ import annotations

import argparse
import datetime
import glob
import json
import os
import sys


def epoch(ts: str) -> float:
    return datetime.datetime.fromisoformat(ts).timestamp()


def iso(t: float) -> str:
    return datetime.datetime.fromtimestamp(t, datetime.timezone.utc).isoformat(timespec="milliseconds")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sb", required=True)
    ap.add_argument("--attempt", required=True)
    ap.add_argument("--turn", required=True)
    ap.add_argument("--c1b", action="store_true")
    a = ap.parse_args()
    base = os.path.join(a.sb, "samples", f"{a.attempt}-turn{a.turn}")
    meta = json.load(open(base + ".meta.json"))
    samples = [json.loads(line) for line in open(base + ".jsonl") if line.strip()]
    events: list[dict] = []
    for f in sorted(glob.glob(os.path.join(a.sb, "org", ".runtime", "events", "*", "*.jsonl"))):
        for line in open(f):
            try:
                events.append(json.loads(line))
            except ValueError:
                pass
    events.sort(key=lambda e: (e.get("ts", ""), e.get("seq", 0)))
    kinds = ("scheduler.start", "scheduler.exit", "scheduler.signal", "run.start", "run.end")
    interest = [e for e in events if e.get("kind") in kinds or (e.get("kind") == "tool.call" and e.get("proc") == "mcp")]
    v: dict = {"attempt": a.attempt, "turn": a.turn, "events_of_interest": [
        {k: e.get(k) for k in ("ts", "proc", "pid", "kind", "tool", "ok", "reason", "signal", "action", "ppid", "running", "child_pid", "pgid",
                               "killed", "timed_out", "duration_ms", "agent") if k in e} for e in interest]}
    ret = meta.get("chat_gone_epoch")
    if ret is None or not samples:
        v.update(verdict="invalid", why="no chat return or no samples were recorded")
        return finish(base, v)
    v["return"] = iso(ret)
    starts = [e for e in events if e.get("kind") == "scheduler.start"]
    exits = [e for e in events if e.get("kind") == "scheduler.exit"]
    signals = [e for e in events if e.get("kind") == "scheduler.signal"]
    runstarts = [e for e in events if e.get("kind") == "run.start"]
    runends = [e for e in events if e.get("kind") == "run.end"]
    sched = starts[-1]["pid"] if starts else meta.get("scheduler_pid")
    v["scheduler_pid"] = sched
    v["start_to_return_ms"] = None
    if not runstarts:
        v.update(verdict="no-run", why="no run.start event at all", valid=False)
        return finish(base, v)
    run = runstarts[0]
    runpid = run.get("child_pid")
    v["run_pid"] = runpid
    v["run_start_to_return_ms"] = round((ret - epoch(run["ts"])) * 1000)
    if epoch(run["ts"]) > ret:
        v.update(verdict="no-run", why="the first run.start is after the return", valid=False)
        return finish(base, v)
    ended_before = [e for e in runends if e.get("run") == run.get("run") and epoch(e["ts"]) < ret]
    # A run the scheduler itself stopped because a signal reached the scheduler (run.end killed:true and scheduler.exit "stopped by SIG...")
    # before the return is the death seen early with its signal visible, not a run that ended by itself (amendment found in DENn2).
    stopped_by_signal = any(str(e.get("reason", "")).startswith("stopped by SIG") and epoch(e["ts"]) < ret for e in exits)
    run_killed_by_stop = bool(ended_before) and all(e.get("killed") is True and e.get("timed_out") is not True for e in ended_before)
    if ended_before and not (stopped_by_signal and run_killed_by_stop):
        v.update(verdict="no-run", why="the run ended before the return", valid=False)
        return finish(base, v)
    if ended_before:
        v["run_ended_before_return_by_scheduler_stop"] = True
    fin = [e for e in exits if str(e.get("reason", "")).startswith("finished")]
    if fin and epoch(fin[0]["ts"]) < ret + 5:
        v.update(verdict="finished", why=f"scheduler.exit reason {fin[0].get('reason')!r}", valid=False)
        return finish(base, v)

    def alive(s: dict, pid: int | None) -> bool:
        return any(p["pid"] == pid and not p["stat"].startswith("Z") for p in s["procs"]) if pid else False

    at5 = next((s for s in samples if s["epoch"] >= ret + 5.0), samples[-1])
    v["at_plus_5s_sample"] = at5["t"]
    s_alive, r_alive = alive(at5, sched), alive(at5, runpid)
    v["scheduler_alive_at_plus_5s"], v["run_alive_at_plus_5s"] = s_alive, r_alive
    ok_end = [e for e in runends if e.get("ok") is True]
    # the scheduler's life over the samples
    seen = [s for s in samples if alive(s, sched)]
    v["scheduler_first_sample_alive"] = seen[0]["t"] if seen else None
    if seen:
        last = seen[-1]
        gone = next((s for s in samples if s["epoch"] > last["epoch"]), None)
        v["scheduler_last_sample_alive"] = last["t"]
        row = next(p for p in last["procs"] if p["pid"] == sched)
        v["scheduler_last_alive_stat_ppid_pgid"] = [row["stat"], row["ppid"], row["pgid"]]
        v["scheduler_first_sample_gone"] = gone["t"] if gone else None
        v["scheduler_gone_relative_to_return_ms"] = round((gone["epoch"] - ret) * 1000) if gone else None
        v["scheduler_alive_at_end_of_samples"] = alive(samples[-1], sched)
    rseen = [s for s in samples if alive(s, runpid)]
    if rseen:
        rl = rseen[-1]
        rgone = next((s for s in samples if s["epoch"] > rl["epoch"]), None)
        v["run_last_sample_alive"] = rl["t"]
        v["run_first_sample_gone"] = rgone["t"] if rgone else None
        row = next(p for p in rl["procs"] if p["pid"] == runpid)
        v["run_last_alive_stat_ppid_pgid"] = [row["stat"], row["ppid"], row["pgid"]]
    v["scheduler.exit"] = [{"ts": e["ts"], "reason": e.get("reason")} for e in exits]
    v["scheduler.signal"] = [{k: e.get(k) for k in ("ts", "signal", "action", "ppid", "running")} for e in signals]
    v["run.end"] = [{k: e.get(k) for k in ("ts", "ok", "killed", "timed_out", "duration_ms")} for e in runends]
    if not s_alive:
        v.update(verdict="died", valid=True)
    elif not r_alive and not ok_end:
        v.update(verdict="run-only", valid=True)
    elif not r_alive:
        v.update(verdict="run-ended-ok", why="the run ended with run.end ok:true within 5 s of the return", valid=False)
    else:
        v.update(verdict="survived", valid=True)
    if a.c1b:
        sig = sorted(signals, key=lambda e: (e["ts"], e.get("seq", 0)))
        first = sig[0] if sig else None
        ex = exits[0] if exits else None
        v["c1b"] = {"first_signal": {k: first.get(k) for k in ("ts", "signal", "action", "ppid", "running")} if first else None,
                    "exit_reason": ex.get("reason") if ex else None,
                    "m5_signature": bool(first and first.get("signal") == "SIGHUP" and first.get("action") == "stop"
                                         and ex and ex.get("reason") == "stopped by SIGHUP"),
                    "any_signal_recorded": bool(sig)}
    return finish(base, v)


def finish(base: str, v: dict) -> int:
    with open(base + ".verdict.json", "w") as fh:
        json.dump(v, fh, indent=1)
    print(json.dumps(v, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
