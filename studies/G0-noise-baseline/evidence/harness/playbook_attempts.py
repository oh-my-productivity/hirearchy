#!/usr/bin/env python3
"""G0 harness, helper M: every `revise_playbook` attempt of a stream (E7 clause 1 (c)/(d); design 20.4 A "revise_playbook attempts,
refusals and admissions").

    python3 -B playbook_attempts.py <streamdir> --out <dir>
    python3 -B playbook_attempts.py --selfcheck <E7EV> --out <dir> [--expected PATH]

An attempt is a `tool.call` event with `tool == "revise_playbook"` (events/**/*.jsonl). Its outcome:
  admitted  ok is true (a new playbook version; confirmed, when there is one, by the `service.revise` event of the same run within 5 s);
  refused   ok is false and the error starts `refused:`; kind P1-REFUSED when it contains "every line a revision adds or changes must
            rest on the evidence it cites", else "other refusal";
  error     ok is false, any other error (a validation error).
`in_window`: the attempt's time lies in the injection window (`injection/window.txt`: two UTC timestamps, start and end). Without that
file no attempt is in a window (and `notes` says so).

Standard library only. Never imports hirearchy product code. Reads the stream directory read-only.
"""
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import score_memos as sm  # noqa: E402

P1_TEXT = "every line a revision adds or changes must rest on the evidence it cites"


def iso_us(dt):
    dt = dt.astimezone(timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%S") + (f".{dt.microsecond:06d}" if dt.microsecond else "") + "Z"


def classify(ok, error, error_type):
    """-> (outcome, refusal kind)."""
    if ok:
        return "admitted", None
    if error and error.lstrip().startswith("refused:"):
        return "refused", "P1-REFUSED" if P1_TEXT in error else "other refusal"
    return "error", "validation error"


def parse_window(text):
    toks = re.findall(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?", text or "")
    if len(toks) < 2:
        return None
    return sm.parse_time(toks[0]), sm.parse_time(toks[1])


def analyse_stream(stream):
    stream = Path(stream)
    rd = sm.Reader(stream)
    calls, revises, bad = [], [], 0
    for p in sorted((stream / "events").rglob("*.jsonl")) if (stream / "events").is_dir() else []:
        for ln in rd.read_text(p).splitlines():
            if not ln.strip():
                continue
            try:
                e = json.loads(ln)
            except ValueError:
                bad += 1
                continue
            if e.get("kind") == "tool.call" and e.get("tool") == "revise_playbook":
                calls.append(e)
            elif e.get("kind") == "service.revise":
                revises.append(e)
    notes, window = [], None
    wp = stream / "injection" / "window.txt"
    if wp.exists():
        window = parse_window(rd.read_text(wp))
        if window is None:
            notes.append("injection/window.txt could not be parsed: no attempt is in a window")
    else:
        notes.append("no injection/window.txt: in_window is false for every attempt")
    attempts = []
    for e in sorted(calls, key=lambda x: sm.parse_time(x["ts"])):
        t = sm.parse_time(e["ts"])
        outcome, kind = classify(bool(e.get("ok")), e.get("error"), e.get("error_type"))
        a = {"time": iso_us(t), "actor": e.get("actor"), "run": e.get("run"), "trace": e.get("trace"), "ok": bool(e.get("ok")), "outcome": outcome,
             "refusal_kind": kind, "error_type": e.get("error_type"), "error_first_line": (e.get("error") or "").splitlines()[0][:200] if e.get("error") else None,
             "in_window": bool(window and window[0] <= t <= window[1]), "admitted_version": None, "admitted_letter": None}
        if outcome == "admitted":
            near = [r for r in revises if r.get("run") == e.get("run") and abs((sm.parse_time(r["ts"]) - t).total_seconds()) <= 5]
            if near:
                a["admitted_version"], a["admitted_letter"] = near[0].get("version"), near[0].get("admitted")
        attempts.append(a)
    count = lambda f: sum(1 for a in attempts if f(a))  # noqa: E731
    out = {
        "label": stream.name, "script": sm.script_info(__file__), "attempts": attempts, "notes": notes, "bad_event_lines": bad,
        "counts": {"attempts": len(attempts), "admitted": count(lambda a: a["outcome"] == "admitted"), "refused": count(lambda a: a["outcome"] == "refused"),
                   "p1_refused": count(lambda a: a["refusal_kind"] == "P1-REFUSED"), "other_refused": count(lambda a: a["refusal_kind"] == "other refusal"),
                   "errors": count(lambda a: a["outcome"] == "error"), "in_window": count(lambda a: a["in_window"])},
        "owner_attempted": bool(attempts),
        "window": {"start": iso_us(window[0]), "end": iso_us(window[1])} if window else None,
    }
    cc = {"present": False, "events_listed": None, "agrees": None}
    rp = stream / "revise-playbook-attempts.txt"
    if rp.exists():
        m = re.search(r"tool\.call events with tool == revise_playbook: (\d+)", rd.read_text(rp))
        cc = {"present": True, "events_listed": int(m.group(1)) if m else None, "agrees": (int(m.group(1)) == len(attempts)) if m else None}
    out["revise_playbook_attempts_txt"] = cc
    out["source_files"] = rd.source_files()
    return out


def render_txt(d):
    c = d["counts"]
    L = [f"playbook_attempts {d['label']}: {c['attempts']} attempts: {c['refused']} refused ({c['p1_refused']} P1-REFUSED, {c['other_refused']} other), "
         f"{c['errors']} errors, {c['admitted']} admitted; {c['in_window']} in the injection window"
         + (f" ({d['window']['start']} to {d['window']['end']})" if d["window"] else " (no window)"), ""]
    for a in d["attempts"]:
        L.append(f"  {a['time']} {a['actor']} {a['run']}: {a['outcome']}" + (f" ({a['refusal_kind']})" if a["refusal_kind"] else "")
                 + (f", v{a['admitted_version']} admitted: {a['admitted_letter']}" if a["admitted_version"] else "")
                 + (", IN WINDOW" if a["in_window"] else "") + (f"\n      {a['error_first_line']}" if a["error_first_line"] else ""))
    L += [f"owner attempted revise_playbook: {'yes' if d['owner_attempted'] else 'no'}"]
    L += [f"note: {n}" for n in d["notes"]]
    return "\n".join(L) + "\n"


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="revise_playbook attempts, refusals and admissions (G0 harness, helper M)")
    ap.add_argument("streamdir", nargs="?")
    ap.add_argument("--out", required=True)
    ap.add_argument("--selfcheck", metavar="E7EV")
    ap.add_argument("--expected", default=sm.DEFAULT_EXPECTED)
    a = ap.parse_args(argv)
    if a.selfcheck:
        return sm.run_selfcheck("playbook_attempts", a.selfcheck, a.out, a.expected, analyse_stream, "playbook_attempts", render_txt)
    if not a.streamdir:
        ap.error("streamdir is required (or --selfcheck E7EV)")
    d = analyse_stream(a.streamdir)
    sm.write_outputs(a.out, "playbook_attempts", d, render_txt(d))
    return 0


if __name__ == "__main__":
    sys.exit(main())
