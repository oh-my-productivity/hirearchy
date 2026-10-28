#!/usr/bin/env python3
"""P1 self-check part: G0's published per-stream counts replayed with the P1 harness (the brief: "to show the M1-treatment parts are unchanged").

For each of G0's valid M1 streams (m1-s1, m1-s2, m1-s3; read-only), the P1 copies of G0's measure scripts run on the kept stream evidence
into <out>/g0-<label>/, and each JSON output is compared with the one G0 published in that stream (`measures/*.json`, `rederived/rederived.json`),
ignoring only the keys that name the script or a path (`script`, `path`, `answer_key.path`). score_memos.py runs in its G0 mode (3 memos).
Also guarantees.py's G2 on the same streams, whose expected verdict is PASS in each (G0 STUDY: one human rejection per stream, answered
before the next request and before the case's accept; design 13.2's replay: 0 refusals).

    python3 -B g0_replay.py --out DIR   ->  one line per comparison, `g0_replay: <ok> of <n> OK`; exit 0 iff all OK
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

H = Path(__file__).resolve().parent
G0 = Path("/Volumes/workspace/hirearchy/studies/G0-noise-baseline/evidence")
LABELS = ["m1-s1", "m1-s2", "m1-s3"]
MODULES = [("score_memos", "measures/score_memos.json"), ("ambiguity_recall", "measures/ambiguity_recall.json"),
           ("prompt_sizes", "measures/prompt_sizes.json"), ("playbook_attempts", "measures/playbook_attempts.json"),
           ("assistant_facts", "measures/assistant_facts.json"), ("scheduler_survival", "measures/scheduler_survival.json")]
IGNORE = {"script", "path", "scripts"}


P1_KEY = "/Volumes/workspace/hirearchy/studies/P1-itemized-playbook/evidence/answer-key.md"
G0_KEY = "/Volumes/workspace/hirearchy/studies/G0-noise-baseline/evidence/answer-key.md"  # the same bytes (md5 2fb69bbe...)


def strip(o):
    if isinstance(o, str):
        return o.replace(P1_KEY, G0_KEY)
    if isinstance(o, dict):
        return {k: strip(v) for k, v in o.items() if k not in IGNORE}
    if isinstance(o, list):
        return [strip(x) for x in o]
    return o


def diff(a, b, path="") -> list[str]:
    if type(a) is not type(b):
        return [f"{path}: {a!r} != {b!r}"[:300]]
    if isinstance(a, dict):
        out = []
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b:
                out.append(f"{path}.{k}: only in {'P1' if k in a else 'G0'}")
            else:
                out += diff(a[k], b[k], f"{path}.{k}")
        return out
    if isinstance(a, list):
        if len(a) != len(b):
            return [f"{path}: length {len(a)} != {len(b)}"]
        out = []
        for i, (x, y) in enumerate(zip(a, b)):
            out += diff(x, y, f"{path}[{i}]")
        return out
    return [] if a == b else [f"{path}: {a!r} != {b!r}"[:300]]


def main(argv):
    out = Path(argv[argv.index("--out") + 1])
    lines, ok, n = [], 0, 0
    for lab in LABELS:
        sd = G0 / lab
        od = out / f"g0-{lab}"
        od.mkdir(parents=True, exist_ok=True)
        for mod, kept in MODULES:
            n += 1
            r = subprocess.run([sys.executable, "-B", str(H / f"{mod}.py"), str(sd), "--out", str(od)], capture_output=True, text=True)
            (od / f"{mod}-output.txt").write_text(r.stdout + r.stderr)
            mine = od / Path(kept).name
            if r.returncode != 0 or not mine.exists():
                lines.append(f"FAIL {lab} {mod}: exit {r.returncode}")
                continue
            d = diff(strip(json.loads(mine.read_text())), strip(json.loads((sd / kept).read_text())))
            ok += not d
            lines.append(f"{'OK  ' if not d else 'FAIL'} {lab} {mod}: {'= G0 published' if not d else str(len(d)) + ' differences: ' + '; '.join(d[:4])}")
        n += 1
        rd = od / "rederived"
        r = subprocess.run([sys.executable, "-B", str(H / "rederive_quality.py"), str(sd), "--out", str(rd), "--compare",
                            str(sd / "quality" / "end.json")], capture_output=True, text=True)
        (od / "rederive_quality-output.txt").write_text(r.stdout + r.stderr)
        mine, theirs = rd / "rederived.json", sd / "rederived" / "rederived.json"
        d = diff(strip(json.loads(mine.read_text())), strip(json.loads(theirs.read_text()))) if mine.exists() else ["no output"]
        mm = (rd / "mismatches.txt").read_text().strip().splitlines()[-1] if (rd / "mismatches.txt").exists() else "?"
        good = not d and r.returncode == 0
        ok += good
        lines.append(f"{'OK  ' if good else 'FAIL'} {lab} rederive_quality: {'= G0 published' if not d else '; '.join(d[:4])} ({mm})")
        n += 1
        r = subprocess.run([sys.executable, "-B", str(H / "guarantees.py"), str(sd), "--out", str(od / "guarantees")], capture_output=True, text=True)
        g2 = json.loads((od / "guarantees" / "g2.json").read_text()) if (od / "guarantees" / "g2.json").exists() else {}
        verd = [g2.get(k, {}).get("verdict", "?") for k in "abc"]
        good = r.returncode == 0 and all(str(v).startswith("PASS") for v in verd)
        ok += good
        lines.append(f"{'OK  ' if good else 'FAIL'} {lab} guarantees G2 (a, b, c): {verd}")
    lines.append(f"g0_replay: {ok} of {n} OK")
    text = "\n".join(lines)
    print(text)
    (out / "g0_replay.out").write_text(text + "\n")
    return 0 if ok == n else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
