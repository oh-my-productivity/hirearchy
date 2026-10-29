#!/usr/bin/env python3
"""P2 running credits after a turn (protocol 11: "in stage 2, a stream over 260 credits is stopped and reported"). Read-only.

    python3 -B running_credits.py <stream dir> <S> --turn N --stage 1|2      one line; stage 2 over 260.00 prints `STOP-CREDITS: ...`
    python3 -B running_credits.py --selfcheck

The same sources as cost.txt and cost_total.py (P1 11), read live:
  * the assistant: the sum of `usage` over every `usage_summary` record's `promptTurnSummaries` in <stream>/assistant-session-messages.jsonl
    (extract_tool_calls.py's rule);
  * every org run: its kiro session's usage summaries, the session found under <state>/kiro-home/<org id>/sessions/*/sess_*/ where the run
    log's `# cwd: <state>/kiro-cwd/<org id>/...` names <state> and <org id> (extract_mechanical.py's rule), matched to the run by the
    session's workspace path and agent mode; a run with no matched session is estimated upward: N unmatched runs times the mean credits per
    matched run (P1 11's L1 rule), and the line is FLAGGED; with unmatched runs and no matched one, the figure is `unknown` and, in stage 2,
    `STOP-CREDITS: unknown` (fail closed).
Over 260 means > 260.00, the figure rounded half-up to 2 decimals.
"""
import json
import re
import sys
import tempfile
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

LIMIT = Decimal("260.00")


def payload(d):
    p = d.get("payload")
    return json.loads(p) if isinstance(p, str) else (p or {})


def usage(msgs: Path) -> Decimal:
    tot = Decimal(0)
    if not msgs.is_file():
        return tot
    for line in msgs.read_text(errors="replace").splitlines():
        if not line.strip():
            continue
        p = payload(json.loads(line))
        if p.get("type") == "usage_summary":
            for s in p.get("promptTurnSummaries") or []:
                tot += Decimal(str(s.get("usage", 0) or 0))
    return tot


def org_runs(org: Path):
    logs = sorted(p for p in org.rglob("runs/*.log") if ".git" not in p.parts) if org.is_dir() else []
    sessions = {}
    matched, unmatched, credits = 0, 0, Decimal(0)
    for lg in logs:
        t = lg.read_text(errors="replace")
        m = re.search(r"^# cwd: (.*)/kiro-cwd/([^/]+)/(.*)$", t, re.M)
        if not m:
            unmatched += 1
            continue
        state, orgid, cwd = Path(m.group(1)), m.group(2), m.group(0)[len("# cwd: "):]
        kh = state / "kiro-home" / orgid
        if kh not in sessions:
            sessions[kh] = []
            for sj in kh.glob("sessions/*/sess_*/session.json"):
                try:
                    j = json.loads(sj.read_text())
                except Exception:
                    continue
                sessions[kh].append(((j.get("workspacePaths") or [""])[0], j.get("createdAt", ""), sj.parent, j.get("agentMode")))
        cand = [s for s in sessions[kh] if s[0] == cwd]
        # one run, one session: the session whose cwd is the run's and that no earlier run took, by creation time
        cand.sort(key=lambda s: s[1])
        took = next((s for s in cand if s[2] not in getattr(org_runs, "_used", set())), None)
        if took is None:
            unmatched += 1
            continue
        org_runs._used = getattr(org_runs, "_used", set()) | {took[2]}
        matched += 1
        credits += usage(took[2] / "messages.jsonl")
    org_runs._used = set()
    return len(logs), matched, unmatched, credits


def figure(stream: Path, S: Path):
    a = usage(stream / "assistant-session-messages.jsonl")
    n, matched, unmatched, o = org_runs(S / "org")
    if unmatched and not matched:
        return None, a, o, n, unmatched, None
    est = (o / matched * unmatched) if unmatched else Decimal(0)
    tot = (a + o + est).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return tot, a, o, n, unmatched, est


def selfcheck() -> int:
    ok = 0
    with tempfile.TemporaryDirectory(dir="/tmp") as d:
        d = Path(d)
        st, S = d / "stream", d / "S"
        st.mkdir()
        (st / "assistant-session-messages.jsonl").write_text(json.dumps({"payload": {"type": "usage_summary", "promptTurnSummaries": [{"usage": 100.5}, {"usage": 50}]}}) + "\n")
        state = d / "state"
        cwd = state / "kiro-cwd" / "org1" / "lead-x"
        (S / "org" / "lead" / "runs").mkdir(parents=True)
        for i, u in enumerate((60, 50)):
            (S / "org" / "lead" / "runs" / f"r{i}.log").write_text(f"# run\n# cwd: {cwd}\n")
            sd = state / "kiro-home" / "org1" / "sessions" / "h" / f"sess_{i}"
            sd.mkdir(parents=True)
            (sd / "session.json").write_text(json.dumps({"workspacePaths": [str(cwd)], "createdAt": f"2026-01-0{i+1}"}))
            (sd / "messages.jsonl").write_text(json.dumps({"payload": {"type": "usage_summary", "promptTurnSummaries": [{"usage": u}]}}) + "\n")
        tot = figure(st, S)[0]
        ok += tot == Decimal("260.50")
        (S / "org" / "lead" / "runs" / "r9.log").write_text("# run\n# cwd: /nowhere/else\n")
        tot2, _, o, _, un, est = figure(st, S)
        ok += un == 1 and est == Decimal(55) and tot2 == Decimal("315.50")
    print(f"running_credits selfcheck: {ok} of 2 ok")
    return 0 if ok == 2 else 1


def main() -> int:
    if sys.argv[1:2] == ["--selfcheck"]:
        return selfcheck()
    stream, S = Path(sys.argv[1]), Path(sys.argv[2])
    turn = sys.argv[sys.argv.index("--turn") + 1]
    stage = sys.argv[sys.argv.index("--stage") + 1]
    tot, a, o, n, un, est = figure(stream, S)
    if tot is None:
        print(f"turn {turn}: running credits unknown ({n} org runs, {un} without a matched session, none matched); assistant {a:.2f}")
        if stage == "2":
            print(f"STOP-CREDITS: unknown after turn {turn} (fail closed, protocol 11)")
        return 0
    flag = f" + {un} runs without a matched session estimated {est:.2f}; FLAGGED" if un else ""
    print(f"turn {turn}: running credits {tot} (assistant {a:.2f} + org runs {o:.2f}{flag}; {n} org runs)")
    if stage == "2" and tot > LIMIT:
        print(f"STOP-CREDITS: {tot} > 260.00 after turn {turn} (protocol 11): stop the stream with stop_stream.sh and report")
    elif tot > Decimal("250.00"):
        print(f"CREDITS: {tot} > 250.00 after turn {turn} (stage {stage}; the stage-1 limit is read at the gate)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
