#!/usr/bin/env python3
"""G0 scheduler survival: D-SURVIVE, D-SIGNAL and M-C-8 of one stream (E7 protocol 9 and 10.10; facts only).
Generalized from E7's `s1|s2|s3/harness/scheduler_survival.py` (the three copies differ only in the stream number in two header lines).

What changed against E7's script (and why):
  * the starter of a scheduler is the `start` tool.call event, in an `mcp-<pid>-*.jsonl` file, whose INTERVAL [ts - ms/1000, ts] holds the
    `scheduler.start` (E7 STUDY Interpretation 18). E7's extract picked the first `start` call within 5 s either side; the event is written
    3-55 ms after the `scheduler.start`, so the rule "the last start call before it" that E7's header stated would credit the previous call.
    The header now says what the rule is (E7 STUDY Correction 9). "injection script" when injection-log.txt says `scheduler started (pid <pid>;`.
  * D-SURVIVE as E7's protocol extends it (E7 item 5): a scheduler counts as running at a turn's end also when a `stopped by SIGTERM`/`SIGHUP`
    exit or an unexplained `scheduler.signal` falls within 5 s before that `turn_end`; every (turn end, scheduler) pair is classed
    `survived` / `died with the call` / `died later` / `error`; M-C-1, M-C-2, M-C-4, M-C-6, M-C-7 are computed; M-C-8 is computed from
    turn-times.txt (`sleep 20 ended` at least 20 s after the chat's end) and `harness-failures/boundary-turn-*.txt`.
  * a label in the header instead of a fixed stream name; the stream dir is the only input; `--out` for the outputs.

Usage:  python3 -B scheduler_survival.py <streamdir> [--out DIR]
Reads (read-only): events/*/*.jsonl, session-turn-times-utc.txt, turn-times.txt, injection/injection-log.txt, harness-failures/.
Writes: <out>/scheduler-survival.txt (the E7 text, default out = the stream dir) and <out>/scheduler_survival.json (sorted keys, with
source_files and script name+md5)."""
import glob
import hashlib
import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.dont_write_bytecode = True

SELF_EXIT_BAD = ("stopped by SIGTERM", "stopped by SIGHUP", "interrupted (KeyboardInterrupt)")


def ts(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def rate(r):
    return "n/a (0 of 0)" if r["n"] == 0 else f"{r['k']} of {r['n']}"


def _is_stop_reason(reason):
    return bool(reason) and (reason.startswith("stopped by SIG") or reason.startswith("interrupted"))


def analyse(D: Path) -> dict:
    D = Path(D)
    sources = []
    ev = []
    for p in sorted(glob.glob(str(D / "events" / "*" / "*.jsonl"))):
        name = Path(p).name
        sources.append(str(Path(p).relative_to(D)))
        for ln in open(p):
            try:
                d = json.loads(ln)
            except Exception:  # noqa: BLE001
                continue
            d["_file"] = name
            ev.append(d)
    ev.sort(key=lambda d: d["ts"])

    sources.append("session-turn-times-utc.txt")
    turn_end, turn_start = {}, {}
    for ln in open(D / "session-turn-times-utc.txt"):
        m = re.match(r"turn (\d+): .* turn_end (\S+)", ln)
        if m:
            turn_end[int(m.group(1))] = ts(m.group(2))
        m = re.match(r"turn (\d+): .* turn_start (\S+)", ln)
        if m:
            turn_start[int(m.group(1))] = ts(m.group(2))

    stops = [d for d in ev if d["kind"] == "tool.call" and d.get("tool") == "stop"]
    inj_f = D / "injection" / "injection-log.txt"
    inj = inj_f.read_text() if inj_f.exists() else ""
    if inj_f.exists():
        sources.append("injection/injection-log.txt")
    inj_stop = bool(re.search(r"--- stop at", inj))
    inj_stop_times = []
    for m in re.finditer(r"--- stop at (\S+)", inj):
        try:
            inj_stop_times.append(ts(m.group(1)))
        except ValueError:
            pass

    def stop_before(t, window=30):
        """A recorded stop at most `window` s before time t: an assistant `stop` tool.call, or the injection script's --stop."""
        if any(0 <= (t - ts(d["ts"])).total_seconds() <= window for d in stops):
            return True
        if any(0 <= (t - x).total_seconds() <= window for x in inj_stop_times):
            return True
        return inj_stop and not inj_stop_times  # a --stop line without a parsable time: E7's reading (any --stop explains)

    scheds_ev = [d for d in ev if d["kind"] == "scheduler.start"]
    exits = {d["pid"]: d for d in ev if d["kind"] == "scheduler.exit"}
    sigs = [d for d in ev if d["kind"] == "scheduler.signal"]
    schedulers = []
    n_ass = n_inj = 0
    for s in scheds_ev:
        pid = s["pid"]
        st = ts(s["ts"])
        # starter: the `start` tool.call (mcp file) whose interval [ts - ms, ts] holds the scheduler.start (E7 STUDY Interpretation 18)
        cands = []
        for d in ev:
            if d["kind"] == "tool.call" and d.get("tool") == "start" and d["_file"].startswith("mcp-"):
                end = ts(d["ts"])
                begin = end - timedelta(milliseconds=float(d.get("ms") or 0))
                if begin <= st <= end:
                    cands.append((end - st, d))
        starter = min(cands, key=lambda x: x[0])[1] if cands else None
        if starter:
            kind = "script" if re.search(rf"scheduler started \(pid {pid};", inj) else "assistant"
            starter_d = {"kind": kind, "mcp_pid": starter["pid"], "file": starter["_file"], "tool_call_ts": starter["ts"]}
        else:
            starter_d = {"kind": "unknown", "mcp_pid": None, "file": None, "tool_call_ts": None}
        turn_in = next((t for t in sorted(turn_start) if t in turn_end and turn_start[t] <= st <= turn_end[t] + timedelta(seconds=1)), None)
        if starter_d["kind"] == "script":
            n_inj += 1
        elif starter_d["kind"] == "assistant":
            n_ass += 1
        ex = exits.get(pid)
        runs = [d for d in ev if d["kind"] in ("run.start", "run.end") and d["pid"] == pid]
        starts = {d["run"]: d for d in runs if d["kind"] == "run.start"}
        ends = {d["run"]: d for d in runs if d["kind"] == "run.end"}
        killed = [r for r, d in ends.items() if d.get("killed")]
        my_sigs = [g for g in sigs if g["pid"] == pid]
        pairs = []
        for t, te in sorted(turn_end.items()):
            exit_t = ts(ex["ts"]) if ex else None
            running = st < te and (not ex or exit_t >= te)
            ext = False
            if not running and ex and st < te and _is_stop_reason(ex.get("reason")) and 0 < (te - exit_t).total_seconds() <= 5 \
                    and not stop_before(exit_t):
                running = ext = True  # D-SURVIVE signal extension (1): a TERM/HUP exit in the last 5 s before the turn's end
            if not running and st < te:
                for g in my_sigs:
                    if 0 < (te - ts(g["ts"])).total_seconds() <= 5 and not stop_before(ts(g["ts"])):
                        running = ext = True
                        break
            if not running:
                continue
            inflight = [r for r, d in starts.items() if ts(d["ts"]) < te and (r not in ends or ts(ends[r]["ts"]) >= te)]
            pairs.append({"turn": t, "turn_end": te.isoformat(), "in_flight": inflight, "extension": ext,
                          "scheduler_exit_reason": ex.get("reason") if ex else None, "survived": None, "class": None, "runs": []})
        for pr in pairs:
            te = turn_end[pr["turn"]]
            cls = _classify(ex, pr, te, ends, my_sigs, stop_before)
            pr["class"] = cls
            pr["survived"] = cls == "survived"
            for r in pr["in_flight"]:
                e = ends.get(r)
                pr["runs"].append({"run": r, "run_end": e["ts"] if e else None, "ok": e.get("ok") if e else None,
                                   "killed": bool(e.get("killed")) if e else None,
                                   "kill_ok": bool(e) and not e.get("killed") or bool(e and e.get("killed") and stop_before(ts(e["ts"])))})
        nearest = [(t, (turn_end[t] - ts(ex['ts'])).total_seconds()) for t in sorted(turn_end) if ex and turn_end[t] >= ts(ex['ts'])][:1]
        schedulers.append({
            "pid": pid, "start_ts": s["ts"], "starter": starter_d, "began_in_turn": turn_in,
            "exit": {"ts": ex["ts"], "reason": ex.get("reason")} if ex else None,
            "runs": {"run_start": len(starts), "run_end": len(ends), "run_end_killed": len(killed),
                     "start_without_end": [r for r in starts if r not in ends]},
            "running_at_turn_ends": pairs,
            "exit_to_next_turn_end": list(nearest[0]) if nearest else None,
        })

    # ---- signals (D-SIGNAL)
    signals = []
    for g in sigs:
        gt = ts(g["ts"])
        before = [(t, (gt - turn_end[t]).total_seconds()) for t in sorted(turn_end) if turn_end[t] <= gt]
        after = [(t, (turn_end[t] - gt).total_seconds()) for t in sorted(turn_end) if turn_end[t] > gt]
        ex = exits.get(g["pid"])
        stopc = [d for d in stops if 0 <= (gt - ts(d['ts'])).total_seconds() <= 30]
        runs = []
        for r in (g.get("running") or []):
            e = [d for d in ev if d["kind"] == "run.end" and d.get("run") == r]
            runs.append({"run": r, "run_end": e[0]["ts"] if e else None, "ok": e[0].get("ok") if e else None, "killed": e[0].get("killed") if e else None})
        signals.append({
            "ts": g["ts"], "pid": g["pid"], "signal": g.get("signal"), "action": g.get("action"), "ppid": g.get("ppid"), "running": g.get("running"),
            "nearest_before": list(before[-1]) if before else None, "nearest_after": list(after[0]) if after else None,
            "exit_after": ({"ts": ex["ts"], "reason": ex.get("reason"), "delay_s": (ts(ex["ts"]) - gt).total_seconds()} if ex and ts(ex["ts"]) >= gt else None),
            "runs": runs, "assistant_stop_call": bool(stopc), "injection_stop": inj_stop,
            "explained": stop_before(gt),
        })

    # ---- rates
    ass = [s for s in schedulers if s["starter"]["kind"] == "assistant"]
    all_pairs = [(s, p) for s in schedulers for p in s["running_at_turn_ends"]]
    in_flight = [r for _, p in all_pairs for r in p["runs"]]
    m_c_1 = {"k": sum(1 for s in ass if s["running_at_turn_ends"]), "n": len(ass)}
    m_c_2_pairs = {"k": sum(1 for _, p in all_pairs if p["survived"]), "n": len(all_pairs)}
    m_c_2_runs = {"k": sum(1 for r in in_flight if r["kill_ok"]), "n": len(in_flight)}
    m_c_4 = {"k": sum(1 for s in schedulers if s["exit"]), "n": len(schedulers)}
    m_c_6 = {"k": sum(1 for g in signals if g["exit_after"]), "n": len(signals)}
    m_c_7 = {"k": sum(1 for g in signals if not g["explained"]), "n": len(signals)}

    # ---- M-C-8: the boundary (turn-times.txt)
    turns8, sleep_entries = [], 0
    tt = D / "turn-times.txt"
    if tt.exists():
        sources.append("turn-times.txt")
        for ln in tt.read_text().splitlines():
            m = re.match(r"turn (\d+): .*?utc (\S+) - (\S+)\s+exit (\d+)(?:\s+sleep 20 ended utc (\S+))?", ln)
            if not m:
                continue
            slept = m.group(5)
            if slept:
                sleep_entries += 1
            secs = (ts(slept) - ts(m.group(3))).total_seconds() if slept else None
            turns8.append({"turn": int(m.group(1)), "chat_end": m.group(3), "sleep_end": slept, "seconds": secs, "ok": bool(secs is not None and secs >= 20)})
    bf = sorted(Path(p).name for p in glob.glob(str(D / "harness-failures" / "boundary-turn-*.txt")))
    m_c_8 = {"k": sum(1 for t in turns8 if t["ok"]), "n": len(turns8), "turns": turns8, "boundary_failure_files": bf}

    return {
        "stream": D.name,
        "schedulers": schedulers,
        "counts": {"schedulers": len(schedulers), "assistant_started": n_ass, "script_started": n_inj, "unknown_starter": len(schedulers) - n_ass - n_inj,
                   "pairs": len(all_pairs), "with_exit": m_c_4["k"], "reasons": sorted({exits[p].get("reason") for p in exits}),
                   "stop_calls": len(stops), "injection_stop": inj_stop,
                   "run_end_killed": sum(1 for d in ev if d["kind"] == "run.end" and d.get("killed")),
                   "run_orphan": sum(1 for d in ev if d["kind"] == "run.orphan"), "scheduler_signals": len(signals)},
        "m_c_1": m_c_1, "m_c_2_pairs": m_c_2_pairs, "m_c_2_runs": m_c_2_runs, "m_c_4": m_c_4, "m_c_6": m_c_6, "m_c_7": m_c_7, "m_c_8": m_c_8,
        "sleep_entries": sleep_entries,
        "signals": signals,
        "source_files": sources,
    }


def _classify(ex, pr, te, ends, my_sigs, stop_before):
    """D-SURVIVE's classes for one (turn end, scheduler) pair."""
    if ex is None:
        # no scheduler.exit by the stream's end: died with the call, except that an unexplained signal further than 5 s from every turn end is "died later"
        unexplained = [g for g in my_sigs if not stop_before(ts(g["ts"]))]
        if unexplained and all(abs((ts(g["ts"]) - te).total_seconds()) > 5 for g in unexplained):
            return "died later"
        return "died with the call"
    reason = ex.get("reason") or ""
    exit_t = ts(ex["ts"])
    if reason.startswith("error"):
        return "error"
    if reason.startswith("interrupted"):
        return "error"
    stopped = reason in ("stopped by SIGTERM", "stopped by SIGHUP")
    if stopped and not stop_before(exit_t):
        return "died with the call" if abs((exit_t - te).total_seconds()) <= 5 else "died later"
    for r in pr["in_flight"]:
        e = ends.get(r)
        if e is None:
            return "died with the call"
        if e.get("killed") and not stop_before(ts(e["ts"])):
            return "died with the call"
    return "survived"


def render(a: dict, label: str) -> list:
    """The text of scheduler-survival.txt: E7's lines (header corrected), then the D-SURVIVE classes, the M-C rates and M-C-8."""
    out = []
    w = out.append
    w(f"# {label} scheduler survival (D-SURVIVE and D-SIGNAL; facts only, from events/, session-turn-times-utc.txt, injection-log.txt)")
    w("Per scheduler: pid, who started it (the `start` tool.call, in an mcp-<pid> event file, whose interval [ts - ms, ts] holds the scheduler.start: the assistant's per-turn server, or the injection script's server when injection-log.txt names the scheduler's pid), its start/exit,")
    w("the turn it began in, whether it was running at any turn's end, runs in flight at a turn's end, and kills/stops.")
    w("")
    for s in a["schedulers"]:
        st = s["starter"]
        if st["kind"] == "unknown":
            who = "unknown"
        else:
            who = f"{'injection script' if st['kind'] == 'script' else chr(97) + 'ssistant' + chr(39) + 's MCP server'} (mcp pid {st['mcp_pid']}, file {st['file']}, start tool.call at {st['tool_call_ts']})"
        w(f"scheduler pid {s['pid']}: scheduler.start {s['start_ts']}; starter: {who}; began in assistant turn: "
          f"{s['began_in_turn'] if s['began_in_turn'] else 'none (between turns: the injection window)'}")
        if s["exit"]:
            w(f"  scheduler.exit {s['exit']['ts']} reason={s['exit']['reason']!r}")
        else:
            w("  scheduler.exit: NONE")
        r = s["runs"]
        w(f"  runs: {r['run_start']} run.start, {r['run_end']} run.end; run.end with killed=true: {r['run_end_killed']}; run.start without run.end: {r['start_without_end']}")
        if s["running_at_turn_ends"]:
            for p in s["running_at_turn_ends"]:
                w(f"  RUNNING at the end of turn {p['turn']} ({p['turn_end']}); runs in flight: {p['in_flight']}")
        else:
            w("  not running at the end of any assistant turn (scheduler.exit came before the turn_end of the turn it began in, or it ran between turns)")
        if s["exit_to_next_turn_end"]:
            t, dt = s["exit_to_next_turn_end"]
            w(f"  scheduler.exit to the next turn_end (turn {t}): {dt:.1f} s")
        w("")
    c = a["counts"]
    w(f"stop tool.calls of the assistant: {c['stop_calls']}; injection script --stop: {c['injection_stop']}")
    w(f"schedulers: {c['schedulers']}; started by the assistant's server: {c['assistant_started']}; started by the injection script: {c['script_started']}")
    w(f"(turn end, scheduler) pairs with the scheduler running: {c['pairs']}")
    w("schedulers with a scheduler.exit: " + str(c["with_exit"]) + " of " + str(c["schedulers"]))
    w("reasons: " + ", ".join(repr(x) for x in c["reasons"]))
    w("run.end with killed=true in the stream: " + str(c["run_end_killed"]))
    w("run.orphan events: " + str(c["run_orphan"]))
    w("")
    w("Per-turn ps records (run-counts-by-turn.txt 'scheduler record after turn N'): see that file; every record shows 'scheduler.pid: (no file)' unless noted.")
    w("")
    w("# D-SIGNAL: every scheduler.signal line of the stream")
    w(f"scheduler.signal lines: {len(a['signals'])}")
    for g in a["signals"]:
        bf = tuple(g["nearest_before"]) if g["nearest_before"] else None
        af = tuple(g["nearest_after"]) if g["nearest_after"] else None
        w(f"scheduler.signal {g['ts']} pid {g['pid']}: signal={g['signal']} action={g['action']} ppid={g['ppid']} running={g['running']}")
        w(f"  nearest turn_end before: {bf}; after: {af} (turn, seconds)")
        ex = g["exit_after"]
        w("  scheduler.exit after it: " + (f"{ex['ts']} reason={ex['reason']!r} ({ex['delay_s']:.2f} s later)" if ex else "NONE"))
        for r in g["runs"]:
            w(f"  run in flight {r['run']}: " + (f"run.end {r['run_end']} ok={r['ok']} killed={r['killed']}" if r["run_end"] else "no run.end"))
        w(f"  explained by a recorded stop (assistant stop tool.call within 30 s before, or injection --stop / facilitator stop per injection-log.txt and run-log.md): assistant stop tool.call: {g['assistant_stop_call']}; injection --stop: {g['injection_stop']}")
    w("")
    w("# Schedulers alive at a turn's end (from the pairs above) and whether each survived (D-SURVIVE)")
    if c["pairs"] == 0:
        w("(turn end, scheduler) pairs with the scheduler running: 0 -> n/a (0 of 0) for survival")
    for s in a["schedulers"]:
        for p in s["running_at_turn_ends"]:
            w(f"pid {s['pid']} running at the end of turn {p['turn']}; runs in flight {p['in_flight']}; scheduler.exit: {p['scheduler_exit_reason'] if s['exit'] else 'NONE'}")
    w("")
    w("# D-SURVIVE classes, M-C rates and M-C-8 (computed here; the text above is E7's)")
    for s in a["schedulers"]:
        for p in s["running_at_turn_ends"]:
            w(f"pid {s['pid']} turn {p['turn']}: {p['class']}" + (" (running by the signal extension: a TERM/HUP exit or unexplained signal within 5 s before the turn end)" if p["extension"] else ""))
    w(f"M-C-1 assistant-started schedulers running at the end of at least one turn: {rate(a['m_c_1'])}")
    w(f"M-C-2 (turn end, scheduler) pairs that survived: {rate(a['m_c_2_pairs'])}; runs in flight whose run.end is not a kill: {rate(a['m_c_2_runs'])}")
    w(f"M-C-3 run.orphan events: {c['run_orphan']}")
    w(f"M-C-4 scheduler.start with a scheduler.exit by the stream's end: {rate(a['m_c_4'])}")
    w(f"M-C-6 scheduler.signal lines followed by a scheduler.exit of the same scheduler: {rate(a['m_c_6'])}")
    w(f"M-C-7 unexplained scheduler.signal lines, of all: {rate(a['m_c_7'])} (explained = a recorded stop within 30 s before: an assistant stop tool.call or the injection script's --stop; a facilitator stop recorded only in run-log.md is not read here)")
    m8 = a["m_c_8"]
    w(f"M-C-8 turns whose sleep ended at least 20 s after the chat's end: {rate(m8)}; 'sleep 20 ended' entries: {a['sleep_entries']}; harness-failures/boundary-turn-*.txt: {len(m8['boundary_failure_files'])}")
    for t in m8["turns"]:
        w(f"  turn {t['turn']}: chat end {t['chat_end']}, sleep end {t['sleep_end']}, {t['seconds']} s, {'ok' if t['ok'] else 'NOT ok'}")
    return out


def main(argv):
    args = list(argv)
    out = None
    if "--out" in args:
        i = args.index("--out")
        out = Path(args[i + 1])
        del args[i:i + 2]
    if len(args) != 1:
        print(__doc__)
        return 2
    D = Path(args[0])
    if not (D / "session-turn-times-utc.txt").exists():
        print(f"no session-turn-times-utc.txt in {D}", file=sys.stderr)
        return 2
    out = out or D
    out.mkdir(parents=True, exist_ok=True)
    a = analyse(D)
    text = render(a, D.name)
    (out / "scheduler-survival.txt").write_text("\n".join(text) + "\n")
    a["script"] = {"name": Path(__file__).name, "md5": hashlib.md5(Path(__file__).read_bytes()).hexdigest()}
    (out / "scheduler_survival.json").write_text(json.dumps(a, sort_keys=True, indent=2) + "\n")
    print("\n".join(text))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
