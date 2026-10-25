#!/usr/bin/env python3
"""Read-only: E3-format transcript of a kiro session store (protocol 7.2 assistant-tool-calls.txt) plus cost/turn data.
Usage: extract_tool_calls.py <messages.jsonl> <out assistant-tool-calls.txt> [<turn-times-utc.txt out>]
Every user turn, assistant text, tool call and result with UTC timestamps. Arguments and results are NOT truncated for
hirearchy::* tools, execute_bash and every file-write tool; other results are cut at 4000 characters.
The file ends with the totals ('# total tool calls: N; unsuccessful: M')."""
import json
import sys
from datetime import datetime

src, out = sys.argv[1], sys.argv[2]
turns_out = sys.argv[3] if len(sys.argv) > 3 else None
FULL_TOOLS = ("execute_bash", "fs_write", "str_replace", "write", "create", "append", "edit")


def load():
    rows = []
    for line in open(src):
        d = json.loads(line)
        p = d["payload"]
        p = json.loads(p) if isinstance(p, str) else p
        rows.append((d.get("timestamp", ""), d.get("id", ""), p))
    return rows


def iso(ts):
    return ts


def is_full(tool_name, tool_id):
    s = f"{tool_name} {tool_id}".lower()
    return "hirearchy" in s or any(t == tool_name for t in FULL_TOOLS) or "write" in s or "bash" in s


rows = load()
calls = {}
lines = []
n_calls = n_fail = 0
turn_no = 0
turn_rows = []  # (turn_no, start, end, credits, elapsed_ms, status)
cur = None
pending_text = []


def flush_text():
    global pending_text
    if pending_text:
        txt = "".join(pending_text).strip()
        if txt:
            lines.append(f"    ASSISTANT TEXT: {txt}")
        pending_text = []


for ts, rid, p in rows:
    t = p.get("type")
    if t == "user":
        flush_text()
        turn_no += 1
        lines.append(f"\n######## USER TURN {turn_no} [{ts}]: {p.get('content')}")
        cur = {"n": turn_no, "user_ts": ts}
        turn_rows.append(cur)
    elif t == "turn_start" and cur is not None:
        cur["start"] = ts
    elif t == "turn_end" and cur is not None:
        flush_text()
        cur["end"] = ts
        cur["stop"] = p.get("stopReason")
    elif t == "usage_summary" and cur is not None:
        s = p.get("promptTurnSummaries") or [{}]
        cur["credits"] = sum(x.get("usage", 0) for x in s)
        cur["elapsed_ms"] = p.get("elapsedTime")
        cur["status"] = p.get("status")
    elif t == "assistant":
        kind = p.get("operationType")
        if kind == "Reasoning":
            continue
        pending_text.append(p.get("content") or "")
    elif t == "tool_call":
        flush_text()
        n_calls += 1
        kiro = (p.get("_meta") or {}).get("kiro") or {}
        tool_id = kiro.get("toolId") or p.get("toolName")
        name = p.get("toolName")
        calls[p.get("toolCallId")] = (ts, name, tool_id)
        args = json.dumps(p.get("args"), ensure_ascii=False)
        if not is_full(name, tool_id) and len(args) > 6000:
            args = args[:6000] + "...[cut]"
        extra = ""
        if kiro.get("disclosedContext"):
            extra = f" disclosed={json.dumps(kiro['disclosedContext'])}"
        lines.append(f"[{ts}] CALL #{n_calls} turn={turn_no} {name} (toolId={tool_id}) status={p.get('status')}{extra} args={args}")
    elif t == "tool_result":
        cid = p.get("toolCallId")
        cts, name, tool_id = calls.get(cid, (ts, "?", "?"))
        content = p.get("content")
        if not isinstance(content, str):
            content = json.dumps(content, ensure_ascii=False)
        status = p.get("status") or ("error" if p.get("isError") else "ok")
        bad = bool(p.get("isError")) or str(status).lower() in ("failed", "error") or content.startswith("Tool \"") or content.startswith("MCP tool error") or content.startswith("Error")
        if bad:
            n_fail += 1
        full = is_full(name, tool_id)
        if not full and len(content) > 4000:
            content = content[:4000] + "...[cut]"
        try:
            ms = int((datetime.fromisoformat(ts.replace("Z", "+00:00")) - datetime.fromisoformat(cts.replace("Z", "+00:00"))).total_seconds() * 1000)
        except Exception:  # noqa: BLE001
            ms = -1
        lines.append(f"    RESULT [{ts}] ({ms} ms){' [UNSUCCESSFUL]' if bad else ''}: {content}")
flush_text()
lines.append(f"\n# total tool calls: {n_calls}; unsuccessful: {n_fail}")
open(out, "w").write("\n".join(lines) + "\n")
if turns_out:
    tot = 0.0
    with open(turns_out, "w") as f:
        for r in turn_rows:
            tot += r.get("credits", 0) or 0
            f.write(f"turn {r['n']}: user_ts {r.get('user_ts')} turn_start {r.get('start')} turn_end {r.get('end')} stop {r.get('stop')} status {r.get('status')} elapsed_ms {r.get('elapsed_ms')} credits {r.get('credits', 0):.4f}\n")
        f.write(f"total assistant credits: {tot:.4f}\n")
print(f"calls {n_calls}, unsuccessful {n_fail}, turns {turn_no}")
