#!/usr/bin/env python3
"""E7 mechanical extracts (protocol 7.2 "Mechanical extracts", amendment 1 A3). Facts only; no scoring. Read-only on the sandbox,
the org and the kiro home (file copies only). Usage:
    uv --directory /Volumes/workspace/hirearchy run python extract_mechanical.py <stream, e.g. 1r>
Needs evidence/s<N>/ to hold sandbox-path.txt, assistant-session-messages.jsonl, events/, run-logs/, msgs/ (copy_org_evidence.sh).
Writes into evidence/s<N>/: org-kiro-sessions/, profiles/ (org scheduler profiles, copied), run-session-map.txt,
revise-playbook-attempts.txt, client-questions.txt, contract-loop.txt, deliverables-log.txt, shell-writes.txt,
lead-prompt-sizes.txt, reflect-sections/, regression-list/, memos/versions/, injection/ (copy + text-identity + window-runs),
cost.txt (credits parts), run-counts.txt."""
import glob
import hashlib
import json
import re
import shutil
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

EV = Path("/Volumes/workspace/hirearchy/studies/E7-org-growth-0a4-recheck/evidence")
N = sys.argv[1]
D = EV / f"s{N}"
S = Path((D / "sandbox-path.txt").read_text().strip())
ORG = S / "org"
sys.path.insert(0, "/Volumes/workspace/hirearchy/src")


def md5b(b: bytes) -> str:
    return hashlib.md5(b).hexdigest()


def parse_ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def stamp_to_dt(stamp: str) -> datetime:
    return datetime.strptime(stamp[:15], "%Y%m%dT%H%M%S").replace(tzinfo=timezone.utc)


def git(*a: str) -> str:
    return subprocess.run(["git", "-C", str(ORG), *a], capture_output=True, text=True).stdout


def payload(d):
    p = d["payload"]
    return json.loads(p) if isinstance(p, str) else p


# ---------------------------------------------------------------- assistant session -> calls
calls, turns = [], []
turn_no = 0
byid = {}
for line in open(D / "assistant-session-messages.jsonl"):
    d = json.loads(line)
    p = payload(d)
    ts = d.get("timestamp", "")
    t = p.get("type")
    if t == "user":
        turn_no += 1
        turns.append({"n": turn_no, "user_ts": ts})
    elif t == "turn_start" and turns:
        turns[-1]["start"] = ts
    elif t == "turn_end" and turns:
        turns[-1]["end"] = ts
    elif t == "tool_call":
        kiro = (p.get("_meta") or {}).get("kiro") or {}
        args = p.get("args") or {}
        name = p.get("toolName")
        tool = args.get("tool_id") if name == "tool_call" else None
        c = {"n": len(calls) + 1, "ts": ts, "turn": turn_no, "name": name, "tool": tool, "args": args,
             "status": p.get("status"), "result": None, "rts": None, "id": p.get("toolCallId")}
        calls.append(c)
        byid[c["id"]] = c
    elif t == "tool_result":
        c = byid.get(p.get("toolCallId"))
        if c:
            content = p.get("content")
            c["result"] = content if isinstance(content, str) else json.dumps(content, ensure_ascii=False)
            c["rts"] = ts
            c["rstatus"] = p.get("status")

tt = {}
for ln in open(D / "turn-times.txt"):
    m = re.match(r"turn (\d+): (\S+) - (\S+)\s+\S+\s+utc (\S+) - (\S+)\s+exit (\d+)", ln)
    if m:
        tt[int(m.group(1))] = {"utc_start": m.group(4), "utc_end": m.group(5), "exit": m.group(6)}
for tr in turns:
    tr.update(tt.get(tr["n"], {}))


def hcalls(*names):
    return [c for c in calls if c["tool"] and c["tool"].split("::")[-1] in names]


# ---------------------------------------------------------------- events
events = []
for f in sorted(glob.glob(str(D / "events" / "*" / "*.jsonl"))):
    for line in open(f):
        e = json.loads(line)
        e["_file"] = Path(f).name
        events.append(e)
events.sort(key=lambda e: e["ts"])

# ---------------------------------------------------------------- run logs
runs = []
for lg in sorted(glob.glob(str(D / "run-logs" / "*" / "*.log"))):
    txt = Path(lg).read_text(errors="replace")
    stamp = Path(lg).stem
    agent_dir = Path(lg).parent.name
    cwd = re.search(r"^# cwd: (.*)$", txt, re.M)
    cmd = re.search(r"^# cmd: .*? --agent (\S+) --model (\S+)", txt, re.M)
    ex = re.search(r"^# exit (\S+) after (\d+)s", txt, re.M)
    runs.append({"stamp": stamp, "agent_dir": agent_dir, "path": lg, "cwd": cwd.group(1) if cwd else None,
                 "agent_profile": cmd.group(1) if cmd else None, "model": cmd.group(2) if cmd else None,
                 "exit": ex.group(1) if ex else None, "secs": int(ex.group(2)) if ex else None, "text": txt,
                 "dt": stamp_to_dt(stamp)})
runs.sort(key=lambda r: r["stamp"])
for r in runs:
    r["start_ev"] = next((e for e in events if e["kind"] == "run.start" and e.get("run", "").endswith("@" + r["stamp"])), None)
    r["end_ev"] = next((e for e in events if e["kind"] == "run.end" and e.get("run", "").endswith("@" + r["stamp"])), None)
    r["run_id"] = (r["start_ev"] or {}).get("run") or ("?@" + r["stamp"])

# ---------------------------------------------------------------- org kiro home (A3.2)
first_cwd = runs[0]["cwd"]
m = re.match(r"(.*)/kiro-cwd/([^/]+)/[^/]+$", first_cwd)
STATE, ORGID = Path(m.group(1)), m.group(2)
KH = STATE / "kiro-home" / ORGID
cwds = Counter(re.match(r"(.*/kiro-cwd/[^/]+)/", r["cwd"]).group(1) for r in runs)
out = []
out.append(f"# run-session map (amendment 1 A3.2)\nstate dir: {STATE}\nfirst run log # cwd: {first_cwd}\nkiro home: {KH}")
out.append(f"every run log shows the same <state>/kiro-cwd/<org-id>/: {len(cwds) == 1} ({dict(cwds)})")
sess = []
for sj in sorted(glob.glob(str(KH / "sessions" / "*" / "sess_*" / "session.json"))):
    sd = Path(sj).parent
    j = json.load(open(sj))
    credits = 0.0
    tool_calls = Counter()
    try:
        for line in open(sd / "messages.jsonl"):
            p = payload(json.loads(line))
            if p.get("type") == "usage_summary":
                for s in p.get("promptTurnSummaries") or []:
                    credits += s.get("usage", 0) or 0
            if p.get("type") == "tool_call":
                a = p.get("args") or {}
                tool_calls[a.get("tool_id") or p.get("toolName")] += 1
    except FileNotFoundError:
        pass
    dst = D / "org-kiro-sessions" / sd.parent.name / sd.name
    dst.mkdir(parents=True, exist_ok=True)
    shutil.copy2(sj, dst / "session.json")
    if (sd / "messages.jsonl").exists():
        shutil.copy2(sd / "messages.jsonl", dst / "messages.jsonl")
    sess.append({"id": j["id"], "hash": sd.parent.name, "cwd": (j.get("workspacePaths") or [None])[0], "mode": j.get("agentMode"),
                 "model": j.get("modelId"), "created": j.get("createdAt"), "credits": credits, "dir": dst, "tools": tool_calls})
out.append(f"org kiro sessions copied: {len(sess)} (to org-kiro-sessions/<hash>/<session id>/)")
norm = lambda p: str(Path(p).resolve()) if p else p  # noqa: E731
unmatched_runs, used = [], set()
for r in runs:
    cand = []
    for s in sess:
        if s["id"] in used:
            continue
        if norm(s["cwd"]) != norm(r["cwd"]) and s["cwd"] != r["cwd"]:
            continue
        if s["mode"] != r["agent_profile"] or s["model"] != r["model"]:
            continue
        a, b = r["start_ev"], r["end_ev"]
        if a and b and not (parse_ts(a["ts"]) <= parse_ts(s["created"]) <= parse_ts(b["ts"])):
            continue
        cand.append(s)
    if len(cand) == 1:
        r["session"] = cand[0]
        used.add(cand[0]["id"])
    else:
        r["session"] = None
        unmatched_runs.append((r["stamp"], len(cand)))
    out.append(f"run {r['run_id']:40s} {r['stamp']} model={r['model']} exit={r['exit']} secs={r['secs']} -> session "
               f"{(r['session'] or {}).get('id', 'NOT MATCHED (%d candidates)' % len(cand))} credits "
               f"{('%.6f' % r['session']['credits']) if r['session'] else 'not recorded'}")
out.append(f"unmatched runs: {unmatched_runs}; sessions without a run: {[s['id'] for s in sess if s['id'] not in used]}")
(D / "run-session-map.txt").write_text("\n".join(out) + "\n")

# org scheduler profiles (copied, not deleted: A3.2)
(D / "profiles").mkdir(exist_ok=True)
for f in glob.glob(str(KH / "agents" / "hirearchy-*.json")):
    shutil.copy2(f, D / "profiles" / ("org-kiro-home--" + Path(f).name))

# ---------------------------------------------------------------- revise-playbook-attempts.txt
o = ["# revise_playbook attempts (protocol 7.2; amendment 1 A3.3 10.1(c)); facts only", ""]
rp = [e for e in events if e["kind"] == "tool.call" and e.get("tool") == "revise_playbook"]
o.append(f"tool.call events with tool == revise_playbook: {len(rp)}")
for e in rp:
    o.append(f"- {e['ts']} actor={e.get('actor')} run={e.get('run')} trace={e.get('trace')} ok={e.get('ok')} error_type={e.get('error_type')}\n  error (verbatim): {e.get('error')}\n  args: {json.dumps(e.get('args'), ensure_ascii=False)}")
o.append("")
P1 = re.compile(r"^\[tool\] @hirearchy/revise_playbook(?= |$)", re.M)
P2 = re.compile(r"^\[tool (?:ok|failed)\] @hirearchy/revise_playbook(?= |$)", re.M)
P3 = re.compile(r"^\[tool\] @hirearchy/\w+", re.M)
o.append("run-log patterns per run (after '# ---- output ----'): P1 revise_playbook call lines | P2 end lines | P3 all hirearchy call lines | tool.call events whose run is this run")
for r in runs:
    outp = r["text"].split("# ---- output ----", 1)[-1]
    ev_n = sum(1 for e in events if e["kind"] == "tool.call" and e.get("run") == r["run_id"])
    ev_rp = sum(1 for e in rp if e.get("run") == r["run_id"])
    p1, p2, p3 = len(P1.findall(outp)), len(P2.findall(outp)), len(P3.findall(outp))
    flag = "" if (p1 == ev_rp and p3 == ev_n) else "   <-- MISMATCH between run-log lines and events"
    o.append(f"  {r['run_id']:44s} P1={p1} P2={p2} P3={p3} events(all)={ev_n} events(revise_playbook)={ev_rp}{flag}")
    for ln in re.findall(r"^\[tool(?: ok| failed)?\] @hirearchy/revise_playbook.*$", outp, re.M):
        o.append(f"      {ln[:400]}")
o.append("")
o.append("full arguments and result verbatim, from the org-run session (tool_call with args.tool_id == hirearchy::revise_playbook):")
for r in runs:
    s = r.get("session")
    if not s:
        continue
    byc = {}
    for line in open(s["dir"] / "messages.jsonl"):
        p = payload(json.loads(line))
        if p.get("type") == "tool_call" and (p.get("args") or {}).get("tool_id") == "hirearchy::revise_playbook":
            byc[p["toolCallId"]] = {"args": p["args"], "res": None}
            byc[p["toolCallId"]]["ts"] = json.loads(line).get("timestamp")
        elif p.get("type") == "tool_result" and p.get("toolCallId") in byc:
            c = p.get("content")
            byc[p["toolCallId"]]["res"] = c if isinstance(c, str) else json.dumps(c, ensure_ascii=False)
    for cid, v in byc.items():
        o.append(f"--- run {r['run_id']} session {s['id']} call {cid} at {v['ts']}\nARGUMENTS: {json.dumps(v['args'], ensure_ascii=False, indent=1)}\nRESULT: {v['res']}")
o.append("")
o.append("service.revise events:")
for e in events:
    if e["kind"] == "service.revise":
        o.append(f"- {e['ts']} {json.dumps({k: v for k, v in e.items() if k not in ('v', 'seq', '_file')}, ensure_ascii=False)}")
o.append("")
o.append("PLAYBOOK versions (org git history of lead/services/weekly-memo/PLAYBOOK.md and history/):")
o.append(git("log", "--reverse", "--format=%h %cI %s", "--", "lead/services/weekly-memo/PLAYBOOK.md", "lead/services/weekly-memo/history").strip())
hist = sorted(glob.glob(str(ORG / "lead/services/weekly-memo/history/*")))
o.append("history files now: " + ", ".join(Path(h).name for h in hist))
for h in hist:
    dst = D / "playbook" / ("history--" + Path(h).name)
    shutil.copy2(h, dst)
    for sub in ("service",):
        pass
for h in glob.glob(str(ORG / "lead/services/weekly-memo/history/SERVICE.v*.md")):
    shutil.copy2(h, D / "service" / ("history--" + Path(h).name))
shutil.copy2(ORG / "lead/services/weekly-memo/SERVICE.md", D / "service" / "current-SERVICE.md")
shutil.copy2(ORG / "lead/services/weekly-memo/PLAYBOOK.md", D / "playbook" / "current-PLAYBOOK.md")
(D / "revise-playbook-attempts.txt").write_text("\n".join(o) + "\n")

# ---------------------------------------------------------------- messages (root's)
def read_msg(path):
    txt = Path(path).read_text()
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", txt, re.S)
    hdr = {}
    for ln in m.group(1).splitlines():
        if ": " in ln:
            k, v = ln.split(": ", 1)
            hdr[k.strip()] = v.strip().strip("'")
    return hdr, m.group(2), txt


# ---------------------------------------------------------------- client-questions.txt
from hirearchy.kernel._text import client_questions  # noqa: E402

o = ["# client questions (protocol 7.2); facts only", ""]
o.append("Result messages root received (lead -> root), with the product parser's items (hirearchy.kernel._text.client_questions):")
for d in ("inbox", "read"):
    for f in sorted(glob.glob(str(D / "msgs" / d / "*.md"))):
        hdr, body, raw = read_msg(f)
        if hdr.get("to") != "root" or hdr.get("type") != "result":
            continue
        raw_q = ""
        mm = re.search(r"(?im)^.*questions for the client.*$", body)
        if mm:
            raw_q = body[mm.start():]
            raw_q = raw_q.split("\n## ", 1)[0]
        items = client_questions(body)
        o.append(f"- id {hdr.get('id')} folder={d} created={hdr.get('created')} answers(reply_to)={hdr.get('reply_to')} status={hdr.get('status')} from={hdr.get('from')}\n"
                 f"  raw 'Questions for the client' text: {raw_q.strip() if raw_q else '(none)'}\n  parsed items ({len(items)}): {items}")
o.append("")
FLAG = "for the client: ask the user before you copy or deliver"
o.append(f"progress replies the assistant received that contain {FLAG!r}:")
n_flag = 0
for c in calls:
    if c["result"] and FLAG in c["result"]:
        n_flag += 1
        lines = [ln for ln in c["result"].splitlines() if FLAG in ln]
        o.append(f"- call #{c['n']} {c['ts']} turn {c['turn']} {c['tool']}: {lines}")
o.append(f"count: {n_flag}")
(D / "client-questions.txt").write_text("\n".join(o) + "\n")

# ---------------------------------------------------------------- contract-loop.txt
o = ["# contract loop (protocol 7.2); facts only, time order", ""]
o.append("Lena reject turns (D1 candidates: turns whose line starts with 'No, not right yet' / 'Not right yet' / 'Almost'):")
for tr in turns:
    pass
lena = {}
for ln in (D / "lena-lines.txt").read_text().splitlines():
    m = re.match(r"turn (\d+) \| (.*)", ln)
    if m:
        lena[int(m.group(1))] = m.group(2)
for n in sorted(lena):
    prompt = (D / f"turn-{n:02d}.prompt.txt").read_text()
    if re.match(r"(No, not right yet|Not right yet|Almost)", prompt):
        tr = turns[n - 1]
        o.append(f"- turn {n}: script UTC {tr.get('utc_start')} - {tr.get('utc_end')}; session turn_start {tr.get('start')} turn_end {tr.get('end')}; line: {prompt}")
o.append("")
o.append("assistant calls to feedback, define_service, request, services (full arguments and replies):")
for c in calls:
    if c["tool"] and c["tool"].split("::")[-1] in ("feedback", "define_service", "request", "services"):
        o.append(f"[{c['ts']}] call #{c['n']} turn {c['turn']} {c['tool']} status={c['status']}\nARGS: {json.dumps(c['args'], ensure_ascii=False)}\nREPLY ({c['rts']}): {c['result']}\n")
o.append("root notes in S/org/sent with a feedback: or criterion: header:")
for f in sorted(glob.glob(str(D / "msgs" / "sent" / "*.md"))):
    hdr, body, raw = read_msg(f)
    if "feedback" in hdr or "criterion" in hdr:
        o.append(f"--- {Path(f).name} id={hdr.get('id')} created={hdr.get('created')}\nheaders: {json.dumps(hdr, ensure_ascii=False)}\nbody:\n{body.strip()}\n")
(D / "contract-loop.txt").write_text("\n".join(o) + "\n")

# ---------------------------------------------------------------- deliverables-log.txt and shell-writes.txt
DELIV = str(S / "deliverables")
DELIV2 = DELIV.replace("/tmp/", "/private/tmp/", 1)


def writes_to(cmd: str, d_variants) -> bool:
    if not any(v in cmd for v in d_variants) and "deliverables" not in cmd:
        return False
    return bool(re.search(r"\b(cp|mv|rsync|ditto|install|tee|write_text)\b|sed -i|open\(|\.write\(|>>?\s*\S*deliverables|>\s", cmd))


o = ["# deliverables log (protocol 7.2, D6); facts only", ""]
sw = ["# shell writes (protocol 7.2): every execute_bash call of the assistant; facts only", ""]
variants = (DELIV, DELIV2)
for c in calls:
    nm = c["name"]
    if nm == "execute_bash":
        cmd = c["args"].get("command", "")
        flags = []
        if writes_to(cmd, variants):
            flags.append("writes into the deliverable folder")
        if str(ORG) in cmd or str(ORG).replace("/tmp/", "/private/tmp/", 1) in cmd or re.search(r"\borg/", cmd):
            flags.append("touches S/org")
        if re.search(r"\bhirearchy\b(?!-e7)", cmd.replace(str(S), "").replace("/Volumes/workspace/hirearchy", "")):
            flags.append("mentions hirearchy")
        if re.search(r"(^|[;&|]\s*)(uv run )?hirearchy\s", cmd):
            flags.append("runs hirearchy CLI")
        if re.search(r"\b(sed -i|>>?\s|tee |cp |mv |rm |write_text|open\([^)]*['\"]w)", cmd) and not flags:
            flags.append("writes elsewhere (possible)")
        sw.append(f"[{c['ts']}] call #{c['n']} turn {c['turn']} status={c['status']} flags={flags or ['none']}\nCOMMAND: {cmd}\nRESULT: {(c['result'] or '')[:1500]}\n")
        if "writes into the deliverable folder" in flags:
            src = re.findall(r"((?:/private)?/tmp/hirearchy-e7-s\w+-\d+/org/[\w/.\-]+\.md|org/[\w/.\-]+\.md)", cmd)
            src_info = []
            for sp in src:
                rel = sp.split("/org/", 1)[-1] if "/org/" in sp else sp[len("org/"):]
                g = git("log", f"--until={c['ts']}", "-1", "--format=%h %cI", "--", rel).strip()
                src_info.append(f"{rel} -> org-git commit at that time: {g or '(none)'}")
            o.append(f"[{c['ts']}] call #{c['n']} turn {c['turn']} execute_bash\nCOMMAND: {cmd}\nsource file(s): {src_info or 'not found in the command'}\nresult: {(c['result'] or '')[:600]}\n")
    elif nm and re.search(r"write|create|append|edit|replace", nm) and "hirearchy" not in (c.get("tool") or ""):
        path = c["args"].get("path") or c["args"].get("file_path") or ""
        if "deliverables" in str(path) or "deliverables" in json.dumps(c["args"]):
            o.append(f"[{c['ts']}] call #{c['n']} turn {c['turn']} {nm} (file-write tool) args={json.dumps(c['args'], ensure_ascii=False)[:800]}\n")
o.append("any other write into the deliverable folder (not by the assistant): none can be seen from the assistant session; the folder holds:")
for p in sorted((S / "deliverables").glob("*")):
    st = p.stat()
    o.append(f"  {p.name} size {st.st_size} mtime {datetime.fromtimestamp(st.st_mtime).strftime('%H:%M:%S')} local md5 {md5b(p.read_bytes())}")
o.append("")
o.append("final ls -la:\n" + subprocess.run(["ls", "-la", str(S / "deliverables")], capture_output=True, text=True).stdout)
(D / "deliverables-log.txt").write_text("\n".join(o) + "\n")
(D / "shell-writes.txt").write_text("\n".join(sw) + "\n")

# ---------------------------------------------------------------- lead-prompt-sizes, reflect-sections, regression-list
(D / "reflect-sections").mkdir(exist_ok=True)
(D / "regression-list").mkdir(exist_ok=True)
o = ["# lead prompt sizes (protocol 7.2): bytes between '# ---- prompt ----' and '# ---- output ----'", ""]
for r in runs:
    if r["agent_dir"] != "lead":
        continue
    txt = r["text"]
    pr = txt.split("# ---- prompt ----\n", 1)[1].split("# ---- output ----", 1)[0]
    size = len(pr.encode())
    refl = re.search(r"^# Reflect before you start:.*?(?=^# (?!Reflect)|\Z)", pr, re.M | re.S)
    reg = re.search(r"^# Regression list:.*?(?=^# (?!Regression)|\Z)", pr, re.M | re.S)
    words = len(refl.group(0).split()) if refl else 0
    o.append(f"{r['run_id']:30s} bytes={size} reflect_section={'yes' if refl else 'no'} reflect_words={words} regression_list={'yes' if reg else 'no'}")
    if refl:
        (D / "reflect-sections" / f"lead-{r['stamp']}.txt").write_text(refl.group(0))
    if reg:
        (D / "regression-list" / f"lead-{r['stamp']}.txt").write_text(reg.group(0))
# regression list inside delegated review tasks (reviewer task messages)
for f in sorted(glob.glob(str(D / "msgs" / "*reviewer*" / "*.md"))):
    hdr, body, raw = read_msg(f)
    if "Regression list" in body:
        i = body.index("Regression list")
        (D / "regression-list" / f"reviewer-task-{Path(f).name}").write_text(body[i - 2:i + 3000])
(D / "lead-prompt-sizes.txt").write_text("\n".join(o) + "\n")

# ---------------------------------------------------------------- memos/versions
(D / "memos" / "versions").mkdir(parents=True, exist_ok=True)
files = [x for x in git("ls-files", "lead/writer/work").split() if x.endswith(".md")]
vlog = []
for fpath in files:
    hs = git("log", "--reverse", "--format=%h %cI", "--", fpath).strip().splitlines()
    for i, ln in enumerate(hs, 1):
        h, t = ln.split(" ", 1)
        body = git("show", f"{h}:{fpath}")
        (D / "memos" / "versions" / f"{Path(fpath).stem}.v{i}.{h}.md").write_text(body)
        vlog.append(f"{fpath} v{i} {h} {t} md5 {md5b(body.encode())}")
    cur = ORG / fpath
    if cur.exists():
        vlog.append(f"{fpath} working tree md5 {md5b(cur.read_bytes())} (committed head: {md5b(git('show', 'HEAD:' + fpath).encode())})")
(D / "memos" / "versions" / "INDEX.txt").write_text("\n".join(vlog) + "\n")

# ---------------------------------------------------------------- injection/
inj = D / "injection"
inj.mkdir(exist_ok=True)
for f in glob.glob(str(S / "injection" / "*")):
    shutil.copy2(f, inj / Path(f).name)
log = (inj / "injection-log.txt").read_text()
iid = re.search(r"injected task id: (\S+)", log).group(1)
mid = re.search(r"revised task file: .*/(\S+)\.md", log).group(1)
hdr, body, raw = read_msg(D / "msgs" / "sent" / f"{iid}.md")
note = body.split("## Note from the requester\n", 1)[1]
note = note.split("\n## ", 1)[0].rstrip("\n")
title = hdr.get("title")
ti = [f"title as stored: {title!r} md5 {md5b(title.encode())} (protocol 5.1: 849fe21b104be883af9b3c06367d4445) match={md5b(title.encode()) == '849fe21b104be883af9b3c06367d4445'}",
      f"note as stored: {len(note)} chars md5 {md5b(note.encode())} (protocol 5.1: 866 chars, 4cdbcb9b682f2f25dcb31c83d3743fec) match={len(note) == 866 and md5b(note.encode()) == '4cdbcb9b682f2f25dcb31c83d3743fec'}",
      f"stored headers: {json.dumps(hdr, ensure_ascii=False)}"]
(inj / "text-identity.txt").write_text("\n".join(ti) + "\n")
w0, w1 = (S / "injection" / "window.txt").read_text().split()
w0d, w1d = parse_ts(w0 + "Z"), parse_ts(w1 + "Z")
o = [f"# window runs (protocol 5.4): runs that started in the injection window {w0}Z .. {w1}Z; injected task {iid}; revised (memo 1) task {mid}", ""]
for r in runs:
    if not (w0d <= r["dt"] <= w1d):
        continue
    se, ee = r["start_ev"], r["end_ev"]
    o.append(f"## run {r['run_id']} agent={r['agent_dir']} model={r['model']} start={se and se['ts']} end={ee and ee['ts']} exit={r['exit']} secs={r['secs']} session={(r.get('session') or {}).get('id')}")
    rpc = [e for e in rp if e.get("run") == r["run_id"]]
    o.append(f"revise_playbook calls in this run (events): {len(rpc)}")
    for e in rpc:
        o.append(f"  {e['ts']} ok={e.get('ok')} error={e.get('error')} args={json.dumps(e.get('args'))}")
    outp = r["text"].split("# ---- output ----", 1)[-1]
    o.append(f"run-log P1 lines: {len(P1.findall(outp))}; P3 lines: {len(P3.findall(outp))}")
    if r["agent_dir"] == "lead":
        # lead's result messages sent in this run + its MEMORY.md change in this run's commit
        t0, t1 = parse_ts(se["ts"]) if se else w0d, parse_ts(ee["ts"]) if ee else w1d
        for f in sorted(glob.glob(str(D / "msgs" / "lead-sent" / "*.md"))):
            h2, b2, _ = read_msg(f)
            try:
                cr = parse_ts(h2.get("created", ""))
            except Exception:  # noqa: BLE001
                continue
            if t0 <= cr <= t1:
                les = re.search(r"## Lessons\n(.*?)(?=\n## |\Z)", b2, re.S)
                o.append(f"  lead message {h2.get('id')} to={h2.get('to')} type={h2.get('type')} status={h2.get('status')} created={h2.get('created')}\n  ## Lessons: {les.group(1).strip() if les else '(none)'}")
        g = git("log", f"--grep={r['stamp']}", "--format=%h")
        for h in g.split():
            o.append(f"  org-git commit {h} MEMORY.md diff:\n" + "\n".join("    " + x for x in git("show", h, "--", "lead/MEMORY.md").splitlines()))
    o.append("")
(inj / "window-runs.txt").write_text("\n".join(o) + "\n")

# ---------------------------------------------------------------- run-counts.txt and cost.txt
rc = subprocess.run(["python3", str(EV / "harness" / "org_state.py"), str(S), "final"], capture_output=True, text=True).stdout
per_turn = []
for r in runs:
    per_turn.append((r["stamp"], r["agent_dir"], r["model"], r["secs"]))
o = [rc]
o.append("\nruns per user-turn window (UTC turn_start .. next turn_start / end):")
bounds = [(tr["n"], parse_ts(tr["utc_start"]) if tr.get("utc_start") else None) for tr in turns]
cnt = defaultdict(list)
for r in runs:
    k = 0
    for n, st in bounds:
        if st and r["dt"] >= st:
            k = n
    cnt[k].append(r)
for k in sorted(cnt):
    o.append(f"  during/after turn {k} start: {len(cnt[k])} runs, " + ", ".join(sorted(f"{x['agent_dir']}={x['model']}" for x in cnt[k]))[:300])
(D / "run-counts.txt").write_text("\n".join(o) + "\n")

c = ["# s%s cost; facts only" % N, ""]
tot = 0.0
for ln in (D / "session-turn-times-utc.txt").read_text().splitlines():
    c.append(ln)
c.append("")
c.append("Assistant seconds per turn (turn-times.txt wall clock):")
c.append((D / "turn-times.txt").read_text())
c.append("Org runs by agent and model; seconds from '# exit N after Ns'; injection window apart:")
by = defaultdict(lambda: [0, 0, 0.0])
byw = defaultdict(lambda: [0, 0, 0.0])
for r in runs:
    tgt = byw if (w0d <= r["dt"] <= w1d) else by
    k = (r["agent_dir"], r["model"])
    tgt[k][0] += 1
    tgt[k][1] += r["secs"] or 0
    tgt[k][2] += (r["session"]["credits"] if r.get("session") else 0.0)
for label, dct in (("outside the injection window (counted toward the 45 cap)", by), ("injection window", byw)):
    c.append(f"  {label}:")
    for k, v in sorted(dct.items()):
        c.append(f"    {k[0]:14s} {k[1]:20s} runs {v[0]:3d} secs {v[1]:5d} credits {v[2]:.4f}")
    c.append(f"    total runs {sum(v[0] for v in dct.values())} secs {sum(v[1] for v in dct.values())} credits {sum(v[2] for v in dct.values()):.4f}")
c.append(f"org-run credits are read from each run's kiro session (usage_summary); runs without a matched session: {len(unmatched_runs)}")
c.append(f"  per-model credits (all runs): " + str({m: round(sum(r['session']['credits'] for r in runs if r.get('session') and r['model'] == m), 4) for m in sorted({r['model'] for r in runs})}))
(D / "cost.txt").write_text("\n".join(c) + "\n")
print(f"runs {len(runs)}, sessions {len(sess)}, matched {len(used)}, unmatched runs {len(unmatched_runs)}, revise_playbook events {len(rp)}, flags {n_flag}, calls {len(calls)}")
