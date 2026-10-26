#!/usr/bin/env python3
"""C1 attempt summary (stdlib only): prints, as markdown, what the record needs of one turn: start/return (UTC ms), stdout, stderr's tool lines,
sample counts by role, the roles' first/last-seen times, the org's events of interest, the verdict, the changed names (names only).
Usage: summary.py --sb SB --attempt ID --turn K [--verdict]  (writes nothing; run allowed.py separately)."""
from __future__ import annotations

import argparse
import json
import os


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sb", required=True)
    ap.add_argument("--attempt", required=True)
    ap.add_argument("--turn", required=True)
    a = ap.parse_args()
    sb, tag = a.sb, f"{a.attempt}-turn{a.turn}"
    rd = lambda p: open(p).read() if os.path.exists(p) else ""  # noqa: E731
    meta = json.loads(rd(f"{sb}/samples/{tag}.meta.json") or "{}")
    print(f"- call start (UTC): {rd(f'{sb}/out/{tag}.start').strip()}; chat first seen {meta.get('chat_first_seen')}; chat gone (the return) {meta.get('chat_gone')}")
    print(f"- stdout: `{' '.join(rd(f'{sb}/out/{tag}.stdout').split())[:700]}`")
    tools = [line for line in rd(f"{sb}/out/{tag}.stderr").splitlines() if line.startswith("[tool]") or "ERROR" in line or "WARN" in line]
    print(f"- stderr: {len(rd(f'{sb}/out/{tag}.stderr').splitlines())} lines; tool/err lines: `{' | '.join(t[:90] for t in tools[:14])}`")
    log = f"{sb}/logs/{tag}.log"
    print(f"- KIRO_CHAT_LOG_FILE written: {'yes (' + str(os.path.getsize(log)) + ' bytes)' if os.path.exists(log) else 'NO'}")
    roles: dict[str, list[str]] = {}
    n = 0
    for line in open(f"{sb}/samples/{tag}.jsonl"):
        d = json.loads(line)
        n += 1
        for p in d["procs"]:
            r = roles.setdefault(p["role"], [d["t"], d["t"], str(p["pid"]), str(p["pgid"]), str(p["ppid"]), p["stat"]])
            r[1] = d["t"]
    print(f"- samples: {n} (file `c1-tools/samples/{a.attempt}/{tag}.jsonl`); roles (first seen, last seen, pid, pgid, first ppid, first stat):")
    for k, v in roles.items():
        print(f"  - {k}: {v[0][11:]} .. {v[1][11:]}, pid {v[2]}, pgid {v[3]}, ppid {v[4]}, {v[5]}")
    vp = f"{sb}/samples/{tag}.verdict.json"
    if os.path.exists(vp):
        v = json.loads(rd(vp))
        print("- org events of interest:")
        for e in v.get("events_of_interest", []):
            print("  - " + ", ".join(f"{k}={x}" for k, x in e.items() if x is not None))
        keep = {k: v[k] for k in v if k not in ("events_of_interest",)}
        print("- verdict json: `" + json.dumps(keep) + "`")
    for who in ("server", "scheduler"):
        g = meta.get(f"{who}_changed_names")
        if g:
            print(f"- changed names in the {who}'s environment (names only): " + "; ".join(f"{k}: {','.join(x) or '-'}" for k, x in g.items()))
    print(f"- KIRO_API_KEY in server env: {meta.get('server_has_KIRO_API_KEY')}; in scheduler env: {meta.get('scheduler_has_KIRO_API_KEY')}")
    if meta.get("d_out"):
        print("- d_out: " + json.dumps(meta["d_out"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
