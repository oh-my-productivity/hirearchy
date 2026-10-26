#!/usr/bin/env python3
"""Prints only the samples at which the tracked set (pid, stat) changes, from a samples .jsonl: timeline.py FILE [FROM_HH:MM:SS]."""
import json, sys
prev = None
for line in open(sys.argv[1]):
    d = json.loads(line)
    if len(sys.argv) > 2 and d["t"][11:19] < sys.argv[2]:
        continue
    cur = tuple((p["pid"], p["stat"][:1]) for p in d["procs"])
    if cur != prev:
        print(d["t"][11:23], " ".join(f"{p['role'][:5]}:{p['pid']}/{p['ppid']}/{p['pgid']}/{p['stat']}" for p in d["procs"]) or "(none tracked)")
        prev = cur
