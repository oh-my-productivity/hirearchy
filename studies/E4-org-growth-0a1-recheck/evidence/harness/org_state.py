#!/usr/bin/env python3
"""E4 read-only org state snapshot (file listings only; no MCP/CLI call against the org).
Usage: org_state.py <S> <label>   -> prints a block for run-counts-by-turn.txt
Lists every run log (agent, model, start from the file name = UTC, duration from the exit line, flagged if inside the
injection window recorded in <S>/injection/window.txt as 'start_utc end_utc'), open items (message files in inboxes and
inflight dirs), the deliverables folder with mtimes and md5, and processes that reference the sandbox."""
import hashlib
import os
import re
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

S = Path(sys.argv[1])
label = sys.argv[2] if len(sys.argv) > 2 else ""
org = S / "org"
print(f"=== {label}  snapshot {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')} (local {datetime.now().strftime('%H:%M:%S')})")
win = None
wf = S / "injection" / "window.txt"
if wf.exists():
    parts = wf.read_text().split()
    if len(parts) >= 2:
        win = (parts[0], parts[1])
        print(f"injection window (UTC, from window.txt): {parts[0]} .. {parts[1]}")
    elif len(parts) == 1:
        win = (parts[0], "9999")
        print(f"injection window start (UTC): {parts[0]}; end not yet written")
runs = []
for log in sorted(org.glob("**/runs/*.log")) if org.exists() else []:
    agent = str(log.parent.parent.relative_to(org))
    head = log.read_text(errors="replace")
    m = re.search(r"^# cmd: .*--model (\S+)", head, re.M)
    ex = re.search(r"^# exit (\S+) after (\d+)s", head, re.M)
    stamp = log.stem  # 20261021T152349661718 (UTC)
    iso = f"{stamp[0:4]}-{stamp[4:6]}-{stamp[6:8]}T{stamp[9:11]}:{stamp[11:13]}:{stamp[13:15]}Z"
    inwin = bool(win and win[0] <= iso <= win[1])
    runs.append((stamp, agent, m.group(1) if m else "?", ex.group(1) if ex else "running/none", int(ex.group(2)) if ex else None, inwin, log))
runs.sort()
print(f"org runs total: {len(runs)}  (injection-window runs: {sum(1 for r in runs if r[5])}; counted toward the 45 cap: {sum(1 for r in runs if not r[5])})")
by = Counter((r[1], r[2]) for r in runs)
for (a, m), n in sorted(by.items()):
    print(f"  {a:30s} {m:20s} {n}")
for r in runs:
    print(f"  run {r[0]} agent={r[1]} model={r[2]} exit={r[3]} secs={r[4]}{' [INJECTION WINDOW]' if r[5] else ''}")
print("open items (files in inbox/ dirs and inflight/ dirs, excluding root read/sent):")
n_open = 0
if org.exists():
    for p in sorted(org.glob("**/inbox/*")) + sorted(org.glob("**/inflight/*")):
        if ".git" in p.parts or not p.is_file():
            continue
        n_open += 1
        print(f"  {p.relative_to(org)}")
print(f"  ({n_open} item(s))")
run_json = org / ".runtime" / "running.json"
print("running.json:", run_json.read_text()[:300].replace("\n", " ") if run_json.exists() else "(none)")
sx = org / ".runtime" / "scheduler.exit"
print("scheduler.exit:", sx.read_text()[:200].replace("\n", " ") if sx.exists() else "(none)")
print("deliverables/:")
d = S / "deliverables"
if d.exists():
    for p in sorted(d.rglob("*")):
        if p.is_file():
            st = p.stat()
            print(f"  {p.relative_to(S)} mtime {datetime.fromtimestamp(st.st_mtime).strftime('%H:%M:%S')} size {st.st_size} md5 {hashlib.md5(p.read_bytes()).hexdigest()}")
else:
    print("  (none)")
ps = subprocess.run(["ps", "-axo", "pid,etime,command"], capture_output=True, text=True).stdout.splitlines()
mine = [l for l in ps if re.search(re.escape(S.name), l) and "org_state.py" not in l and "grep" not in l]
print(f"processes referencing the sandbox name ({len(mine)}):")
for l in mine:
    print("  " + l[:220])
