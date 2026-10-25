#!/usr/bin/env python3
"""E7 s2 facilitator extract (facts only; protocol 6, 7.2, D-SURVIVE and D-SIGNAL; E6 s1's extract with the signal listing added). Reads s2/events/*/ and s2/session-turn-times-utc.txt and
s2/injection/injection-log.txt (read-only) and writes s2/scheduler-survival.txt (E7: also every scheduler.signal). Usage: scheduler_survival.py <stream dir>"""
import glob
import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

D = Path(sys.argv[1])


def ts(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


ev = []
for p in sorted(glob.glob(str(D / "events" / "*" / "*.jsonl"))):
    name = Path(p).name
    for ln in open(p):
        try:
            d = json.loads(ln)
        except Exception:
            continue
        d["_file"] = name
        ev.append(d)
ev.sort(key=lambda d: d["ts"])

turn_end = {}
for ln in open(D / "session-turn-times-utc.txt"):
    m = re.match(r"turn (\d+): .* turn_end (\S+)", ln)
    if m:
        turn_end[int(m.group(1))] = ts(m.group(2))
turn_start = {}
for ln in open(D / "session-turn-times-utc.txt"):
    m = re.match(r"turn (\d+): .* turn_start (\S+)", ln)
    if m:
        turn_start[int(m.group(1))] = ts(m.group(2))

stops = [d for d in ev if d["kind"] == "tool.call" and d.get("tool") == "stop"]
inj = (D / "injection" / "injection-log.txt").read_text() if (D / "injection" / "injection-log.txt").exists() else ""
inj_stop = bool(re.search(r"--- stop at", inj))
mcp_files = {d["_file"]: d["pid"] for d in ev if d["_file"].startswith("mcp-")}

out = []
w = out.append
w("# E7 s2 scheduler survival (D-SURVIVE and D-SIGNAL; facts only, from events/, session-turn-times-utc.txt, injection-log.txt)")
w("Per scheduler: pid, who started it (the last `start` tool.call before its scheduler.start whose mcp file/pid is the assistant's per-turn server, or the injection script's), its start/exit,")
w("the turn it began in, whether it was running at any turn's end, runs in flight at a turn's end, and kills/stops.")
w("")
scheds = [d for d in ev if d["kind"] == "scheduler.start"]
exits = {d["pid"]: d for d in ev if d["kind"] == "scheduler.exit"}
running_pairs = []
n_ass = n_inj = 0
for s in scheds:
    pid = s["pid"]
    st = ts(s["ts"])
    # starter: the 'start' tool.call at the closest time (within 5 s) from an mcp process
    cands = [d for d in ev if d["kind"] == "tool.call" and d.get("tool") == "start" and d["_file"].startswith("mcp-")
             and abs((ts(d["ts"]) - st).total_seconds()) < 5]
    starter = cands[0] if cands else None
    who = "unknown"
    if starter:
        in_inj = f"injection script" if re.search(rf"scheduler started \(pid {pid};", inj) else "assistant's MCP server"
        who = f"{in_inj} (mcp pid {starter['pid']}, file {starter['_file']}, start tool.call at {starter['ts']})"
    turn_in = next((t for t in sorted(turn_start) if turn_start[t] <= st <= turn_end[t] + timedelta(seconds=1)), None)
    if "injection script" in who: n_inj += 1
    elif "assistant" in who: n_ass += 1
    ex = exits.get(pid)
    w(f"scheduler pid {pid}: scheduler.start {s['ts']}; starter: {who}; began in assistant turn: {turn_in if turn_in else 'none (between turns: the injection window)'}")
    if ex:
        w(f"  scheduler.exit {ex['ts']} reason={ex.get('reason')!r}")
    else:
        w("  scheduler.exit: NONE")
    runs = [d for d in ev if d["kind"] in ("run.start", "run.end") and d["pid"] == pid]
    starts = {d["run"]: d for d in runs if d["kind"] == "run.start"}
    ends = {d["run"]: d for d in runs if d["kind"] == "run.end"}
    killed = [r for r, d in ends.items() if d.get("killed")]
    w(f"  runs: {len(starts)} run.start, {len(ends)} run.end; run.end with killed=true: {len(killed)}; run.start without run.end: {[r for r in starts if r not in ends]}")
    # running at any turn end?
    pairs = []
    for t, te in sorted(turn_end.items()):
        running = st < te and (not ex or ts(ex["ts"]) >= te)
        if running:
            inflight = [r for r, d in starts.items() if ts(d["ts"]) < te and (r not in ends or ts(ends[r]["ts"]) >= te)]
            pairs.append((t, inflight))
    if pairs:
        for t, infl in pairs:
            w(f"  RUNNING at the end of turn {t} ({turn_end[t].isoformat()}); runs in flight: {infl}")
            running_pairs.append((pid, t, infl, ex))
    else:
        w("  not running at the end of any assistant turn (scheduler.exit came before the turn_end of the turn it began in, or it ran between turns)")
    nearest = [(t, (turn_end[t] - ts(ex['ts'])).total_seconds()) for t in sorted(turn_end) if ex and turn_end[t] >= ts(ex['ts'])][:1]
    if nearest:
        t, dt = nearest[0]
        w(f"  scheduler.exit to the next turn_end (turn {t}): {dt:.1f} s")
    w("")
w(f"stop tool.calls of the assistant: {len(stops)}; injection script --stop: {inj_stop}")
w(f"schedulers: {len(scheds)}; started by the assistant's server: {n_ass}; started by the injection script: {n_inj}")
w(f"(turn end, scheduler) pairs with the scheduler running: {len(running_pairs)}")
w("schedulers with a scheduler.exit: " + str(sum(1 for s in scheds if s['pid'] in exits)) + " of " + str(len(scheds)))
w("reasons: " + ", ".join(sorted({repr(exits[p].get('reason')) for p in exits})))
w("run.end with killed=true in the stream: " + str(sum(1 for d in ev if d['kind'] == 'run.end' and d.get('killed'))))
w("run.orphan events: " + str(sum(1 for d in ev if d['kind'] == 'run.orphan')))
w("")
w("Per-turn ps records (run-counts-by-turn.txt 'scheduler record after turn N'): see that file; every record shows 'scheduler.pid: (no file)' unless noted.")

# ---- E7 addition (protocol 4.11, 6, 9 D-SIGNAL): every scheduler.signal and what followed it (facts only)
w("")
w("# D-SIGNAL: every scheduler.signal line of the stream")
sigs = [d for d in ev if d["kind"] == "scheduler.signal"]
w(f"scheduler.signal lines: {len(sigs)}")
for g in sigs:
    gt = ts(g["ts"])
    before = [(t, (gt - turn_end[t]).total_seconds()) for t in sorted(turn_end) if turn_end[t] <= gt]
    after = [(t, (turn_end[t] - gt).total_seconds()) for t in sorted(turn_end) if turn_end[t] > gt]
    ex = exits.get(g["pid"])
    w(f"scheduler.signal {g['ts']} pid {g['pid']}: signal={g.get('signal')} action={g.get('action')} ppid={g.get('ppid')} running={g.get('running')}")
    w(f"  nearest turn_end before: {before[-1] if before else None}; after: {after[0] if after else None} (turn, seconds)")
    w(f"  scheduler.exit after it: " + (f"{ex['ts']} reason={ex.get('reason')!r} ({(ts(ex['ts']) - gt).total_seconds():.2f} s later)" if ex and ts(ex['ts']) >= gt else "NONE"))
    for r in (g.get("running") or []):
        e = [d for d in ev if d["kind"] == "run.end" and d.get("run") == r]
        w(f"  run in flight {r}: " + (f"run.end {e[0]['ts']} ok={e[0].get('ok')} killed={e[0].get('killed')}" if e else "no run.end"))
    stopc = [d for d in stops if 0 <= (gt - ts(d['ts'])).total_seconds() <= 30]
    w(f"  explained by a recorded stop (assistant stop tool.call within 30 s before, or injection --stop / facilitator stop per injection-log.txt and run-log.md): assistant stop tool.call: {bool(stopc)}; injection --stop: {inj_stop}")
w("")
w("# Schedulers alive at a turn's end (from the pairs above) and whether each survived (D-SURVIVE)")
if not running_pairs:
    w("(turn end, scheduler) pairs with the scheduler running: 0 -> n/a (0 of 0) for survival")
for (pid, t, infl, ex) in running_pairs:
    w(f"pid {pid} running at the end of turn {t}; runs in flight {infl}; scheduler.exit: {ex.get('reason') if ex else 'NONE'}")

(D / "scheduler-survival.txt").write_text("\n".join(out) + "\n")
print("\n".join(out))
