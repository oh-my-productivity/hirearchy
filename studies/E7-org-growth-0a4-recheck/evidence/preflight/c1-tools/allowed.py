#!/usr/bin/env python3
"""C1 allowed-set check (stdlib only; DR-0a4-2). Reads the session record(s) (messages.jsonl) under SB/kiro-home.

Allowed: tool_load whose tool_ids ALL start with `hirearchy::`; tool_call whose tool_id starts with `hirearchy::`; disclose_context of the hirearchy
skill. Anything else is forbidden. Under --choice b a tool_call of hirearchy::whoami or hirearchy::status is forbidden too.
Prints the record path(s), the session id(s), every tool use, and ALLOWED or FORBIDDEN: <tool and args>. Exit 0 either way (the caller reads the line).
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--kiro-home", required=True)
    ap.add_argument("--choice", default="default", choices=["default", "a", "b"])
    a = ap.parse_args()
    records = sorted(glob.glob(os.path.join(a.kiro_home, "**", "messages.jsonl"), recursive=True))
    if not records:
        print("NO SESSION RECORD under " + a.kiro_home)
        return 0
    bad: list[str] = []
    for rec in records:
        sid = os.path.basename(os.path.dirname(rec))
        print(f"record: {rec}\nsession: {sid}")
        rows = []
        for line in open(rec):
            try:
                d = json.loads(line)
            except ValueError:
                continue
            p = d.get("payload")
            rows.append((d, json.loads(p) if isinstance(p, str) else p))
        # a call whose result says the tool "is not available" ran nothing (MCP tools connect ~2 s after the session starts): noted, not forbidden
        unavailable = {p.get("toolCallId") for _, p in rows if isinstance(p, dict) and p.get("type") == "tool_result"
                       and "is not available" in str(p.get("content"))}
        for d, p in rows:
            if not isinstance(p, dict) or p.get("type") != "tool_call":
                continue
            name = p.get("toolName")
            args = p.get("args") or {}
            if p.get("toolCallId") in unavailable:
                print(f"  {d.get('timestamp')} {name} {json.dumps(args)[:200]} [UNAVAILABLE: nothing ran]")
                continue
            print(f"  {d.get('timestamp')} {name} {json.dumps(args)[:200]}")
            if name == "tool_load" and all(str(t).startswith("hirearchy::") for t in args.get("tool_ids", [])) and args.get("tool_ids"):
                continue
            if name == "tool_call" and str(args.get("tool_id", "")).startswith("hirearchy::"):
                if a.choice == "b" and args["tool_id"] in ("hirearchy::whoami", "hirearchy::status"):
                    bad.append(f"{name} {json.dumps(args)[:200]} (forbidden under choice b)")
                continue
            if name == "disclose_context" and args.get("name") == "hirearchy":
                continue
            bad.append(f"{name} {json.dumps(args)[:200]}")
    print("ALLOWED" if not bad else "FORBIDDEN: " + "; ".join(bad))
    return 0


if __name__ == "__main__":
    sys.exit(main())
