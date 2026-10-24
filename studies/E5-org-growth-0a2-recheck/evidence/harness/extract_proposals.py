#!/usr/bin/env python3
"""Read-only: write PLAN-FOR-YOU-product-proposal<k>.txt, blueprint-proposal<k>.yaml, blueprint.yaml and apply_org-result.txt
from an assistant session store (protocol 7.2). Usage: extract_proposals.py <stream dir, e.g. .../evidence/s3>
Reads <dir>/assistant-session-messages.jsonl; writes into <dir>. Facts only."""
import json
import sys
from pathlib import Path

D = Path(sys.argv[1])
rows = []
for line in open(D / "assistant-session-messages.jsonl"):
    d = json.loads(line)
    p = d["payload"]
    p = json.loads(p) if isinstance(p, str) else p
    rows.append((d.get("timestamp", ""), p))
calls = {}
k = 0
last_bp = None
for ts, p in rows:
    t = p.get("type")
    if t == "tool_call":
        args = p.get("args") or {}
        tid = args.get("tool_id") if isinstance(args, dict) else None
        calls[p.get("toolCallId")] = (ts, tid, args)
    elif t == "tool_result":
        cts, tid, args = calls.get(p.get("toolCallId"), (ts, None, {}))
        content = p.get("content")
        if not isinstance(content, str):
            content = json.dumps(content, ensure_ascii=False)
        a = args.get("arguments", {}) if isinstance(args, dict) else {}
        if tid == "hirearchy::propose_org":
            ok = not (p.get("isError") or content.startswith("MCP tool error") or content.startswith("Error"))
            if not ok:
                (D / f"propose_org-failed-at-{cts}.txt").write_text(f"# propose_org at {cts}; result at {ts}\n\n{content}\n")
                continue
            k += 1
            (D / f"PLAN-FOR-YOU-product-proposal{k}.txt").write_text(f"# propose_org call {k} at {cts}; result at {ts}\n\n{content}\n")
            (D / f"blueprint-proposal{k}.yaml").write_text(a.get("blueprint", ""))
            last_bp = a.get("blueprint", "")
        elif tid == "hirearchy::apply_org":
            (D / "apply_org-result.txt").write_text(f"# apply_org at {cts}; args: {json.dumps({x: y for x, y in a.items() if x != 'blueprint'})}\n\n{content}\n")
            (D / "blueprint.yaml").write_text(a.get("blueprint", last_bp or ""))
print("successful propose_org calls:", k)
