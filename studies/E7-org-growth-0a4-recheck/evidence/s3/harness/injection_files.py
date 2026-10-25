#!/usr/bin/env python3
# E7 s3 facilitator helper (read-only on the org): writes injection/text-identity.txt and injection/window-runs.txt (protocol 5.4).
import glob, json, os, re, subprocess, sys, hashlib
S = sys.argv[1]; INJ = sys.argv[2]; MEMO1 = sys.argv[3]; WIN = open(S + "/injection/window.txt").read().split()
org = S + "/org"
w0, w1 = WIN[0] + "Z", WIN[1] + "Z"
# text identity
f = glob.glob(f"{org}/sent/{INJ}.md")[0]; txt = open(f).read()
hdr = {}
head, _, body = txt.partition("\n---\n")
for line in head.splitlines()[1:]:
    if ": " in line: k, v = line.split(": ", 1); hdr[k] = v.strip("'")
title = hdr["title"]
m = re.search(r"## Note from the requester\n(.*?)(\n## |\Z)", txt, re.S); note = m.group(1).rstrip("\n")
t_md5 = hashlib.md5(title.encode()).hexdigest(); n_md5 = hashlib.md5(note.encode()).hexdigest()
with open(S + "/injection/text-identity.txt", "w") as o:
    o.write(f"title as stored: {title!r} md5 {t_md5} (protocol 5.1: 849fe21b104be883af9b3c06367d4445) match={t_md5=='849fe21b104be883af9b3c06367d4445'}\n")
    o.write(f"note as stored: {len(note)} chars md5 {n_md5} (protocol 5.1: 866 chars, 4cdbcb9b682f2f25dcb31c83d3743fec) match={n_md5=='4cdbcb9b682f2f25dcb31c83d3743fec' and len(note)==866}\n")
    o.write("stored headers: " + json.dumps(hdr) + "\n")
# events
ev = []
for p in glob.glob(org + "/.runtime/events/*/*.jsonl"):
    for l in open(p):
        try: ev.append(json.loads(l))
        except Exception: pass
starts = [e for e in ev if e.get("kind") == "run.start"]
ends = {e.get("run"): e for e in ev if e.get("kind") == "run.end"}
def iso(t): return t.replace("+00:00", "Z")
runs = []
for e in starts:
    ts = e["ts"]
    if w0 <= iso(ts)[:19] + "Z" <= w1.replace("Z", "Z") or (iso(ts)[:19] >= WIN[0] and iso(ts)[:19] <= WIN[1]):
        runs.append(e)
runs.sort(key=lambda e: e["ts"])
out = [f"# window runs (protocol 5.4): runs that started in the injection window {w0} .. {w1}; injected task {INJ}; revised (memo 1) task {MEMO1}\n"]
msgs = []
for p in glob.glob(org + "/**/*.md", recursive=True):
    if "/.git/" in p: continue
    try: t = open(p).read()
    except Exception: continue
    mm = re.match(r"---\n(.*?)\n---\n", t, re.S)
    if not mm: continue
    h = {}
    for line in mm.group(1).splitlines():
        if ": " in line: k, v = line.split(": ", 1); h[k] = v.strip("'")
    if h.get("from") and h.get("type") in ("task", "result", "note"): msgs.append((p, h, t))
for e in runs:
    run = e.get("run"); en = ends.get(run, {})
    agent = (e.get("run") or "").split("@")[0]
    logs = glob.glob(f"{org}/**/runs/{run.split('@')[-1]}.log", recursive=True) if run else []
    model = ""
    if logs:
        c = [l for l in open(logs[0]) if l.startswith("# cmd:")]
        mo = re.search(r"--model (\S+)", c[0]) if c else None; model = mo.group(1) if mo else ""
    rp = [x for x in ev if x.get("kind") == "tool.call" and x.get("run") == run and x.get("args", {}) is not None and "revise_playbook" in json.dumps(x.get("tool", ""))]
    out.append(f"## run {run} agent={agent} model={model} start={e['ts']} end={en.get('ts')} ok={en.get('ok')} killed={en.get('killed')}")
    out.append(f"revise_playbook calls in this run (events): {len(rp)}")
    if logs:
        t = open(logs[0]).read(); out_part = t.split("# ---- output ----")[-1]
        rl1 = len(re.findall(r"^\[tool\] @hirearchy/revise_playbook(?= |$)", out_part, re.M)); rl3 = len(re.findall(r"^\[tool\] @hirearchy/\w+", out_part, re.M))
        out.append("run-log RL1 lines: %d; RL3 lines: %d" % (rl1, rl3))
    t0 = e["ts"]; t1 = en.get("ts") or "9999"
    for p, h, t in msgs:
        c = h.get("created", "")
        if h.get("from") == agent:
            if t0[:19] <= c[:19] <= t1[:19]:
                out.append(f"  {agent} message {h.get('id')} to={h.get('to')} type={h.get('type')} status={h.get('status')} source={h.get('source')} revises={h.get('revises')} created={c}")
                lm = re.search(r"## Lessons\n(.*?)(\n## |\Z)", t, re.S)
                if h.get("type") == "result": out.append("  ## Lessons: " + (lm.group(1).strip() if lm else "(none)"))
    if logs:
        rel = os.path.relpath(logs[0], org)
        r = subprocess.run(["git", "-C", org, "log", "-1", "--format=%h", "--", rel], capture_output=True, text=True)
        out.append(f"  org-git: last commit touching {rel}: {r.stdout.strip()}")
        cm = subprocess.run(["git", "-C", org, "log", "--format=%h", "--grep", os.path.basename(logs[0])], capture_output=True, text=True).stdout.split()
        if cm and os.path.dirname(logs[0]).endswith("lead/runs"):
            d = subprocess.run(["git", "-C", org, "show", "--format=    commit %H%n    Date:   %cd%n    %s", cm[0], "--", "lead/MEMORY.md"], capture_output=True, text=True).stdout
            out.append("  org-git commit MEMORY.md diff:"); out.extend("    " + l for l in d.splitlines())
    out.append("")
open(S + "/injection/window-runs.txt", "w").write("\n".join(out) + "\n")
print("written", len(runs), "window runs")
