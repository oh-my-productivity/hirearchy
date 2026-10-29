#!/usr/bin/env python3
"""Facilitator's own read-only check (not a harness file): the turn's end + its 20 s boundary <= the start of the first snapshot
(quality/calls.txt `turn-NN start`). Needed because turn.sh's python check cannot parse the snapshot's '+00:00' timestamp (see
harness-failures/turn-sh-sequence-check-vacuous.md). Usage: seqcheck.py <R1 dir> <turn>"""
import re, sys
from datetime import datetime, timedelta, timezone
D, T = sys.argv[1], int(sys.argv[2])
def p(s):
    s = s.replace("+00:00", "").rstrip("Z")
    for f in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S"):
        try: return datetime.strptime(s, f).replace(tzinfo=timezone.utc)
        except ValueError: pass
end = slept = first = None
for ln in open(f"{D}/turn-times.txt"):
    m = re.match(rf"^turn {T}: .*utc (\S+) - (\S+)\s+exit \S+\s+sleep (\d+) ended utc (\S+)", ln)
    if m: end, slept = p(m.group(2)), p(m.group(4))
for ln in open(f"{D}/quality/calls.txt"):
    m = re.match(rf"^turn-{T:02d} start (\S+)", ln)
    if m: first = p(m.group(1)); break
if end is None or first is None: print(f"seqcheck turn {T}: NOT READ (end {end}, first snapshot {first})"); sys.exit(1)
ok = first >= end + timedelta(seconds=20)
print(f"seqcheck turn {T}: turn end {end.time()} + 20 s = {(end+timedelta(seconds=20)).time()} <= first snapshot {first.time()}: {'checked' if ok else 'STOP: snapshot before the boundary'}")
sys.exit(0 if ok else 1)
