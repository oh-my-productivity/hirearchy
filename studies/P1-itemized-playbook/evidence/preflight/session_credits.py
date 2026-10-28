#!/usr/bin/env python3
"""Preflight helper (read-only): credits of kiro session messages.jsonl files = sum of usage_summary.promptTurnSummaries[].usage (as extract_mechanical.py)."""
import json, sys
tot = 0.0
for path in sys.argv[1:]:
    c = 0.0
    for line in open(path):
        d = json.loads(line); p = d["payload"]; p = json.loads(p) if isinstance(p, str) else p
        if p.get("type") == "usage_summary":
            c += sum((s.get("usage", 0) or 0) for s in p.get("promptTurnSummaries") or [])
    print(f"{c:.4f} {path}"); tot += c
print(f"total {tot:.4f}")
