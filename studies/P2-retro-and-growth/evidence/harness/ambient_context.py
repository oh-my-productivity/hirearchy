#!/usr/bin/env python3
"""Read-only: summarise the session_start entry of a kiro session store (protocol 4.5 probe / per-stream ambient-context check).
Usage: ambient_context.py <messages.jsonl> <session.json> <sandbox path S>   -> prints the report to stdout"""
import hashlib
import json
import re
import sys

msgs, sess, S = sys.argv[1:4]
start = None
for line in open(msgs):
    d = json.loads(line)
    p = d["payload"]
    p = json.loads(p) if isinstance(p, str) else p
    if p.get("type") == "session_start":
        start = (d, p)
        break
sj = json.load(open(sess))
d, p = start
content = p.get("content", "")
print(f"session id: {sj['id']}  agentMode: {sj.get('agentMode')}  modelId: {sj.get('modelId')}  effortLevel: {sj.get('effortLevel')}")
print(f"workspacePaths: {sj.get('workspacePaths')}  workflowsEnabled: {sj.get('workflowsEnabled')}  memoryConfig: {sj.get('memoryConfig')}")
print(f"session_start id: {d['id']}  timestamp: {d['timestamp']}  agentType: {p.get('agentType')}")
print("session_start composition:", json.dumps(p.get("composition")))
print(f"session_start content length: {len(content)} chars")
print("<memories> block present:", "<memories>" in content)
titles = re.findall(r'- \[[A-Z_]+\] title: "([^"]+)"', content)
print(f"memory index titles ({len(titles)}):", ", ".join(titles))
for m in re.finditer(r"^.*(Global|repo:[^\n]*)\(?.*$", content, re.M):
    pass
scopes = [ln.strip() for ln in content.splitlines() if re.search(r"(shown|total)", ln) and ("Global" in ln or "repo:" in ln or "scope" in ln.lower())]
print("scope lines:", scopes[:10])
print("<steering-files> block present:", "<steering-files>" in content)
if "<steering-files>" in content:
    blk = content.split("<steering-files>", 1)[1].split("</steering-files>", 1)[0]
    print("steering headings:", re.findall(r"^#+ .*$", blk, re.M))
print("'Workflow Orchestration' text present:", "Workflow Orchestration" in content)
norm = content.replace(S, "<S>").replace(S.replace("/tmp/", "/private/tmp/"), "<S>")
print("md5 of content with sandbox path replaced by <S>:", hashlib.md5(norm.encode()).hexdigest())
print("other top-level tags in content:", sorted(set(re.findall(r"<([a-z][a-z-]+)>", content))))
