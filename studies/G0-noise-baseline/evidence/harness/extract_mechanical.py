#!/usr/bin/env python3
"""G0 mechanical extracts (E7 protocol 7.2 "Mechanical extracts"; facts only, no scoring).

ONE script for every stream. It is E7's `harness/extract_mechanical.py` (and E7's per-stream copies `s1|s2|s3/harness/extract_mechanical.py`
and the frozen `extract_mechanical_s2.py`/`_s3.py`, which differed from it in exactly the service folder name, the final-check seat's message
glob and prefix, and the sandbox-name patterns) with those per-stream choices detected instead of edited:
  * the owner (the agent root's tasks go to) and the service folder name: from root's sent tasks (`to`, `service`) in the stream dir;
  * the final-check seat: the agent below the owner whose name says review/check/..., else whose charter (`org-files/<agent>-AGENT.md`)
    says review/check, else whose results carry `criteria met`; the regression-list file prefix is the seat's last address part
    (`reviewer-task-<msg>.md` for E7's `lead/reviewer`);
  * the sandbox-name patterns: from the stream's own `sandbox-path.txt` (and the generic `/tmp/hirearchy-<...>-<epoch>/org/` form).

Usage:
    python3 -B extract_mechanical.py <streamdir> <sandbox S or "-"> [--out DIR] [--product-src DIR]
  <streamdir>  the stream's evidence dir (E7's layout: `s1/`, or G0's `m0-s1/`); never written unless it is also --out.
  S            the sandbox path (E7's second input) or "-": with "-" (or when S is gone) every input comes from the stream dir only:
               the org git history from `memos/versions/INDEX.txt`, `playbook/versions.txt` and `org-git-log.txt`; the org-run sessions from
               `org-kiro-sessions/`; the deliverable folder listing from `memos/`.  With a sandbox that exists the script reads it as E7's did
               (`git -C S/org`, the org's kiro home from the run logs' `# cwd:`, `S/deliverables`) and copies the org-run sessions, the org
               profiles, the playbook/service history and `memos/versions/` into --out, as E7's did.
  --out DIR    where the extracts are written (default: the stream dir, as E7's).

Writes into --out: revise-playbook-attempts.txt, client-questions.txt, contract-loop.txt, deliverables-log.txt, shell-writes.txt,
lead-prompt-sizes.txt, reflect-sections/, regression-list/, cost.txt, run-session-map.txt (and, with a sandbox: org-kiro-sessions/,
profiles/, playbook/, service/, memos/versions/). Not written (E7 wrote them in the same script): `run-counts.txt` (its `final` block is
org_state.py's time-stamped snapshot, so it cannot be reproduced) and `injection/` (injection_files.py writes it).

PRODUCT IMPORT (read-only, stated): `client-questions.txt` lists the items by the PRODUCT's parser `hirearchy.kernel._text.client_questions`,
exactly as E7's did (E7 inserted `/Volumes/workspace/hirearchy/src` into sys.path and imported it). That is the only product import in the
harness: the build was told to keep it. It is read-only: `sys.dont_write_bytecode` is set before the import (no `__pycache__` appears under
`src/`), nothing in the product is called but that pure function, and `--product-src` can point to another checkout. Every other script of
the harness is stdlib-only and independent of the product (assistant_facts.py parses the items back out of `client-questions.txt`)."""
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

sys.dont_write_bytecode = True

PRODUCT_SRC = "/Volumes/workspace/hirearchy/src"


def md5b(b: bytes) -> str:
    return hashlib.md5(b).hexdigest()


def parse_ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def stamp_to_dt(stamp: str) -> datetime:
    return datetime.strptime(stamp[:15], "%Y%m%dT%H%M%S").replace(tzinfo=timezone.utc)


def payload(d):
    p = d["payload"]
    return json.loads(p) if isinstance(p, str) else p


def read_msg(path):
    txt = Path(path).read_text()
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", txt, re.S)
    hdr = {}
    for ln in m.group(1).splitlines():
        if ": " in ln:
            k, v = ln.split(": ", 1)
            hdr[k.strip()] = v.strip().strip("'")
    return hdr, m.group(2), txt


# ---------------------------------------------------------------- detection (replaces E7's per-stream edits)
SEAT_NAME = re.compile(r"review|check|qa|verif|audit|inspect", re.I)


def detect(D: Path) -> dict:
    """Owner, service folder name and final-check seat of a stream, from the stream dir alone."""
    D = Path(D)
    owner = service = None
    for f in sorted(glob.glob(str(D / "msgs" / "sent" / "*.md"))):
        hdr, _, _ = read_msg(f)
        if hdr.get("from") == "root" and hdr.get("type") == "task" and hdr.get("service") and hdr.get("to"):
            owner, service = hdr["to"], hdr["service"]
            break
    agents = sorted(p.name for p in (D / "run-logs").iterdir() if p.is_dir()) if (D / "run-logs").is_dir() else []
    if owner is None:
        owner = min(agents, key=lambda a: (a.count("-"), a)).replace("-", "/") if agents else "lead"
    owner_dir = owner.replace("/", "-")
    if service is None:
        for f in sorted(glob.glob(str(D / "org-files" / f"current-{owner_dir}-services-*-SERVICE.md"))):
            service = Path(f).name[len(f"current-{owner_dir}-services-"):-len("-SERVICE.md")]
            break
    below = [a for a in agents if a.startswith(owner_dir + "-")]
    seat = None
    by_name = [a for a in below if SEAT_NAME.search(a[len(owner_dir) + 1:])]
    if by_name:
        seat = by_name[0]
    if seat is None:
        by_charter = []
        for a in below:
            ch = D / "org-files" / f"{a}-AGENT.md"
            if ch.exists():
                t = ch.read_text(errors="replace").lower()
                if "review" in t or "check" in t:
                    by_charter.append((0 if "review" in t else 1, a))
        if by_charter:
            seat = sorted(by_charter)[0][1]
    if seat is None:
        for a in below:
            for f in glob.glob(str(D / "msgs" / f"{a}-sent" / "*.md")):
                if re.search(r"criteria met", Path(f).read_text(errors="replace"), re.I):
                    seat = a
                    break
            if seat:
                break
    return {"owner": owner, "owner_dir": owner_dir, "service": service, "seat_dir": seat,
            "seat_short": seat[len(owner_dir) + 1:].split("-")[-1] if seat else None, "agents": agents}


def source_paths(cmd: str):
    """Sandbox-org paths (absolute under any /tmp/hirearchy-<...>-<epoch>/org/, or relative org/...) a command names."""
    return re.findall(r"((?:/private)?/tmp/hirearchy-[\w-]+?-\d+/org/[\w/.\-]+\.md|org/[\w/.\-]+\.md)", cmd)


def shell_flags(cmd: str, S, deliv_variants=None):
    """The flags of one execute_bash command (E7's, with the sandbox taken from the stream, not from a study name).
    Returns (flags, writes_into_the_deliverable_folder)."""
    S = str(S)
    ORG = S + "/org"
    DELIV = S + "/deliverables"
    variants = deliv_variants or (DELIV, DELIV.replace("/tmp/", "/private/tmp/", 1))
    flags = []
    wrote = False
    if any(v in cmd for v in variants) or "deliverables" in cmd:
        wrote = bool(re.search(r"\b(cp|mv|rsync|ditto|install|tee|write_text)\b|sed -i|open\(|\.write\(|>>?\s*\S*deliverables|>\s", cmd))
    if wrote:
        flags.append("writes into the deliverable folder")
    if ORG in cmd or ORG.replace("/tmp/", "/private/tmp/", 1) in cmd or re.search(r"\borg/", cmd):
        flags.append("touches S/org")
    if re.search(r"\bhirearchy\b(?!-(?:e7|g0)\b)", cmd.replace(S, "").replace("/Volumes/workspace/hirearchy", "")):
        flags.append("mentions hirearchy")
    if re.search(r"(^|[;&|]\s*)(uv run )?hirearchy\s", cmd):
        flags.append("runs hirearchy CLI")
    if re.search(r"\b(sed -i|>>?\s|tee |cp |mv |rm |write_text|open\([^)]*['\"]w)", cmd) and not flags:
        flags.append("writes elsewhere (possible)")
    return flags, wrote


# ---------------------------------------------------------------- the assistant session (shared with assistant_facts.py)
def load_session(D: Path):
    """(calls, turns) of the assistant session copy `assistant-session-messages.jsonl`: calls are numbered like assistant-tool-calls.txt;
    `tool` is the MCP tool id of a `tool_call` wrapper (None for built-in tools); `uri` is the disclosed context's uri (disclose_context)."""
    calls, turns = [], []
    turn_no = 0
    byid = {}
    for line in open(Path(D) / "assistant-session-messages.jsonl"):
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
            args = p.get("args") or {}
            name = p.get("toolName")
            tool = args.get("tool_id") if name == "tool_call" else None
            kiro = (p.get("_meta") or {}).get("kiro") or {}
            c = {"n": len(calls) + 1, "ts": ts, "turn": turn_no, "name": name, "tool": tool, "args": args,
                 "status": p.get("status"), "result": None, "rts": None, "id": p.get("toolCallId"),
                 "uri": (kiro.get("disclosedContext") or {}).get("uri")}
            calls.append(c)
            byid[c["id"]] = c
        elif t == "tool_result":
            c = byid.get(p.get("toolCallId"))
            if c:
                content = p.get("content")
                c["result"] = content if isinstance(content, str) else json.dumps(content, ensure_ascii=False)
                c["rts"] = ts
                c["rstatus"] = p.get("status")
    return calls, turns


def hcalls(calls, *names):
    """The assistant's MCP calls to hirearchy tools with these short names (e.g. 'feedback')."""
    return [c for c in calls if c["tool"] and c["tool"].split("::")[-1] in names]


# ---------------------------------------------------------------- the extract
def run_extract(D: Path, S_arg: str, OUT: Path, product_src: str = PRODUCT_SRC) -> dict:
    D = Path(D)
    OUT = Path(OUT)
    OUT.mkdir(parents=True, exist_ok=True)
    S = Path(S_arg if S_arg != "-" else (D / "sandbox-path.txt").read_text().strip())
    have_sandbox = S_arg != "-" and (S / "org").is_dir()
    ORG = S / "org"
    info = detect(D)
    owner, owner_dir, service, seat_dir, seat_short = info["owner"], info["owner_dir"], info["service"], info["seat_dir"], info["seat_short"]
    svc_dir = f"{owner}/services/{service}"
    N = D.name

    def git(*a: str) -> str:
        if not have_sandbox:
            return ""
        return subprocess.run(["git", "-C", str(ORG), *a], capture_output=True, text=True).stdout

    # ------------------------------------------------------------ assistant session -> calls
    calls, turns = load_session(D)

    tt = {}
    for ln in open(D / "turn-times.txt"):
        m = re.match(r"turn (\d+): (\S+) - (\S+)\s+\S+\s+utc (\S+) - (\S+)\s+exit (\d+)", ln)
        if m:
            tt[int(m.group(1))] = {"utc_start": m.group(4), "utc_end": m.group(5), "exit": m.group(6)}
    for tr in turns:
        tr.update(tt.get(tr["n"], {}))

    # ------------------------------------------------------------ events
    events = []
    for f in sorted(glob.glob(str(D / "events" / "*" / "*.jsonl"))):
        for line in open(f):
            e = json.loads(line)
            e["_file"] = Path(f).name
            events.append(e)
    events.sort(key=lambda e: e["ts"])

    # ------------------------------------------------------------ run logs
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

    # ------------------------------------------------------------ org kiro home (A3.2)
    first_cwd = runs[0]["cwd"] if runs else None
    m = re.match(r"(.*)/kiro-cwd/([^/]+)/[^/]+$", first_cwd or "")
    STATE, ORGID = (Path(m.group(1)), m.group(2)) if m else (None, None)
    KH = STATE / "kiro-home" / ORGID if STATE else None
    cwds = Counter(re.match(r"(.*/kiro-cwd/[^/]+)/", r["cwd"]).group(1) for r in runs if r["cwd"])
    out = []
    out.append(f"# run-session map (amendment 1 A3.2)\nstate dir: {STATE}\nfirst run log # cwd: {first_cwd}\nkiro home: {KH}")
    out.append(f"every run log shows the same <state>/kiro-cwd/<org-id>/: {len(cwds) == 1} ({dict(cwds)})")
    sess = []
    kh_sessions = sorted(glob.glob(str(KH / "sessions" / "*" / "sess_*" / "session.json"))) if (KH and KH.is_dir()) else []
    copied = bool(kh_sessions)
    src_sessions = kh_sessions or sorted(glob.glob(str(D / "org-kiro-sessions" / "*" / "sess_*" / "session.json")))
    for sj in src_sessions:
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
        if copied:
            dst = OUT / "org-kiro-sessions" / sd.parent.name / sd.name
            dst.mkdir(parents=True, exist_ok=True)
            shutil.copy2(sj, dst / "session.json")
            if (sd / "messages.jsonl").exists():
                shutil.copy2(sd / "messages.jsonl", dst / "messages.jsonl")
        else:
            dst = sd
        sess.append({"id": j["id"], "hash": sd.parent.name, "cwd": (j.get("workspacePaths") or [None])[0], "mode": j.get("agentMode"),
                     "model": j.get("modelId"), "created": j.get("createdAt"), "credits": credits, "dir": dst, "tools": tool_calls})
    if copied:
        out.append(f"org kiro sessions copied: {len(sess)} (to org-kiro-sessions/<hash>/<session id>/)")
    else:
        out.append(f"org kiro sessions read from the stream dir copy: {len(sess)} (org-kiro-sessions/<hash>/<session id>/)")
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
    (OUT / "run-session-map.txt").write_text("\n".join(out) + "\n")

    if have_sandbox and KH and KH.is_dir():  # org scheduler profiles (copied, not deleted: A3.2)
        (OUT / "profiles").mkdir(exist_ok=True)
        for f in glob.glob(str(KH / "agents" / "hirearchy-*.json")):
            shutil.copy2(f, OUT / "profiles" / ("org-kiro-home--" + Path(f).name))

    # ------------------------------------------------------------ revise-playbook-attempts.txt
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
    o.append(f"PLAYBOOK versions (org git history of {svc_dir}/PLAYBOOK.md and history/):")
    if have_sandbox:
        o.append(git("log", "--reverse", "--format=%h %cI %s", "--", f"{svc_dir}/PLAYBOOK.md", f"{svc_dir}/history").strip())
        hist = sorted(glob.glob(str(ORG / svc_dir / "history" / "*")))
        hist_names = [Path(h).name for h in hist]
    else:
        o.append(playbook_versions_from_evidence(D))
        hist_names = sorted(Path(h).name[len("history--"):] for h in glob.glob(str(D / "playbook" / "history--*")))
    o.append("history files now: " + ", ".join(hist_names))
    if have_sandbox:
        (OUT / "playbook").mkdir(exist_ok=True)
        (OUT / "service").mkdir(exist_ok=True)
        for h in hist:
            shutil.copy2(h, OUT / "playbook" / ("history--" + Path(h).name))
        for h in glob.glob(str(ORG / svc_dir / "history" / "SERVICE.v*.md")):
            shutil.copy2(h, OUT / "service" / ("history--" + Path(h).name))
        shutil.copy2(ORG / svc_dir / "SERVICE.md", OUT / "service" / "current-SERVICE.md")
        shutil.copy2(ORG / svc_dir / "PLAYBOOK.md", OUT / "playbook" / "current-PLAYBOOK.md")
    (OUT / "revise-playbook-attempts.txt").write_text("\n".join(o) + "\n")

    # ------------------------------------------------------------ client-questions.txt
    sys.dont_write_bytecode = True
    if product_src not in sys.path:
        sys.path.insert(0, product_src)
    from hirearchy.kernel._text import client_questions  # noqa: E402  (the one product import: read-only, stated in the docstring)

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
    (OUT / "client-questions.txt").write_text("\n".join(o) + "\n")

    # ------------------------------------------------------------ contract-loop.txt
    o = ["# contract loop (protocol 7.2); facts only, time order", ""]
    o.append("Lena reject turns (D1 candidates: turns whose line starts with 'No, not right yet' / 'Not right yet' / 'Almost'):")
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
    (OUT / "contract-loop.txt").write_text("\n".join(o) + "\n")

    # ------------------------------------------------------------ deliverables-log.txt and shell-writes.txt
    DELIV = str(S / "deliverables")
    DELIV2 = DELIV.replace("/tmp/", "/private/tmp/", 1)
    variants = (DELIV, DELIV2)
    index_rows = index_from_evidence(D)
    o = ["# deliverables log (protocol 7.2, D6); facts only", ""]
    sw = ["# shell writes (protocol 7.2): every execute_bash call of the assistant; facts only", ""]
    for c in calls:
        nm = c["name"]
        if nm == "execute_bash":
            cmd = c["args"].get("command", "")
            flags, wrote = shell_flags(cmd, S, variants)
            sw.append(f"[{c['ts']}] call #{c['n']} turn {c['turn']} status={c['status']} flags={flags or ['none']}\nCOMMAND: {cmd}\nRESULT: {(c['result'] or '')[:1500]}\n")
            if "writes into the deliverable folder" in flags:
                src = source_paths(cmd)
                src_info = []
                for sp in src:
                    rel = sp.split("/org/", 1)[-1] if "/org/" in sp else sp[len("org/"):]
                    if have_sandbox:
                        g = git("log", f"--until={c['ts']}", "-1", "--format=%h %cI", "--", rel).strip()
                    else:
                        g = commit_at(index_rows, rel, c["ts"])
                    src_info.append(f"{rel} -> org-git commit at that time: {g or '(none)'}")
                o.append(f"[{c['ts']}] call #{c['n']} turn {c['turn']} execute_bash\nCOMMAND: {cmd}\nsource file(s): {src_info or 'not found in the command'}\nresult: {(c['result'] or '')[:600]}\n")
        elif nm and re.search(r"write|create|append|edit|replace", nm) and "hirearchy" not in (c.get("tool") or ""):
            path = c["args"].get("path") or c["args"].get("file_path") or ""
            if "deliverables" in str(path) or "deliverables" in json.dumps(c["args"]):
                o.append(f"[{c['ts']}] call #{c['n']} turn {c['turn']} {nm} (file-write tool) args={json.dumps(c['args'], ensure_ascii=False)[:800]}\n")
    o.append("any other write into the deliverable folder (not by the assistant): none can be seen from the assistant session; the folder holds:")
    if have_sandbox and (S / "deliverables").is_dir():
        listing = sorted((S / "deliverables").glob("*"))
    else:
        listing = sorted((D / "memos").glob("*.md")) if (D / "memos").is_dir() else []
    for p in listing:
        st = p.stat()
        o.append(f"  {p.name} size {st.st_size} mtime {datetime.fromtimestamp(st.st_mtime).strftime('%H:%M:%S')} local md5 {md5b(p.read_bytes())}")
    o.append("")
    if have_sandbox and (S / "deliverables").is_dir():
        o.append("final ls -la:\n" + subprocess.run(["ls", "-la", str(S / "deliverables")], capture_output=True, text=True).stdout)
    else:
        o.append("final ls -la:\n(no sandbox: the listing above is of the stream dir's memos/ copy)\n")
    (OUT / "deliverables-log.txt").write_text("\n".join(o) + "\n")
    (OUT / "shell-writes.txt").write_text("\n".join(sw) + "\n")

    # ------------------------------------------------------------ lead-prompt-sizes, reflect-sections, regression-list
    (OUT / "reflect-sections").mkdir(exist_ok=True)
    (OUT / "regression-list").mkdir(exist_ok=True)
    o = ["# lead prompt sizes (protocol 7.2): bytes between '# ---- prompt ----' and '# ---- output ----'", ""]
    for r in runs:
        if r["agent_dir"] != owner_dir:
            continue
        txt = r["text"]
        pr = txt.split("# ---- prompt ----\n", 1)[1].split("# ---- output ----", 1)[0]
        size = len(pr.encode())
        refl = re.search(r"^# Reflect before you start:.*?(?=^# (?!Reflect)|\Z)", pr, re.M | re.S)
        reg = re.search(r"^# Regression list:.*?(?=^# (?!Regression)|\Z)", pr, re.M | re.S)
        words = len(refl.group(0).split()) if refl else 0
        o.append(f"{r['run_id']:30s} bytes={size} reflect_section={'yes' if refl else 'no'} reflect_words={words} regression_list={'yes' if reg else 'no'}")
        if refl:
            (OUT / "reflect-sections" / f"{owner_dir}-{r['stamp']}.txt").write_text(refl.group(0))
        if reg:
            (OUT / "regression-list" / f"{owner_dir}-{r['stamp']}.txt").write_text(reg.group(0))
    if seat_dir:
        for f in sorted(glob.glob(str(D / "msgs" / f"{seat_dir}-*" / "*.md"))):
            hdr, body, raw = read_msg(f)
            if "Regression list" in body:
                i = body.index("Regression list")
                (OUT / "regression-list" / f"{seat_short}-task-{Path(f).name}").write_text(body[i - 2:i + 3000])
    (OUT / "lead-prompt-sizes.txt").write_text("\n".join(o) + "\n")

    # ------------------------------------------------------------ memos/versions (sandbox only; copy_org_evidence.sh makes it in G0)
    if have_sandbox:
        (OUT / "memos" / "versions").mkdir(parents=True, exist_ok=True)
        seat_path = seat_dir.replace("-", "/") if seat_dir else None
        files = [x for x in git("ls-files", f"{owner}").split()
                 if x.endswith(".md") and "/work/" in x and not (seat_path and x.startswith(seat_path + "/"))]
        vlog = []
        for fpath in files:
            hs = git("log", "--reverse", "--format=%h %cI", "--", fpath).strip().splitlines()
            for i, ln in enumerate(hs, 1):
                h, t = ln.split(" ", 1)
                body = git("show", f"{h}:{fpath}")
                (OUT / "memos" / "versions" / f"{Path(fpath).stem}.v{i}.{h}.md").write_text(body)
                vlog.append(f"{fpath} v{i} {h} {t} md5 {md5b(body.encode())}")
            cur = ORG / fpath
            if cur.exists():
                vlog.append(f"{fpath} working tree md5 {md5b(cur.read_bytes())} (committed head: {md5b(git('show', 'HEAD:' + fpath).encode())})")
        (OUT / "memos" / "versions" / "INDEX.txt").write_text("\n".join(vlog) + "\n")

    # ------------------------------------------------------------ cost.txt
    w0d = w1d = None
    wf = D / "injection" / "window.txt"
    if wf.exists() and len(wf.read_text().split()) >= 2:
        w0, w1 = wf.read_text().split()[:2]
        w0d, w1d = parse_ts(w0 + "Z"), parse_ts(w1 + "Z")
    c = ["# %s cost; facts only" % N, ""]
    for ln in (D / "session-turn-times-utc.txt").read_text().splitlines():
        c.append(ln)
    c.append("")
    c.append("Assistant seconds per turn (turn-times.txt wall clock):")
    c.append((D / "turn-times.txt").read_text())
    c.append("Org runs by agent and model; seconds from '# exit N after Ns'; injection window apart:")
    by = defaultdict(lambda: [0, 0, 0.0])
    byw = defaultdict(lambda: [0, 0, 0.0])
    for r in runs:
        tgt = byw if (w0d and w0d <= r["dt"] <= w1d) else by
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
    c.append("  per-model credits (all runs): " + str({m: round(sum(r['session']['credits'] for r in runs if r.get('session') and r['model'] == m), 4) for m in sorted({r['model'] for r in runs})}))
    (OUT / "cost.txt").write_text("\n".join(c) + "\n")
    return {"runs": len(runs), "sessions": len(sess), "matched": len(used), "unmatched": len(unmatched_runs),
            "revise_playbook": len(rp), "flags": n_flag, "calls": len(calls), "sandbox": have_sandbox,
            "owner": owner, "service": service, "seat": seat_dir}


# ---------------------------------------------------------------- evidence-only replacements for the org's git
def index_from_evidence(D: Path):
    """Rows of memos/versions/INDEX.txt: (path, version, sha, time) for every committed version; [] when absent."""
    rows = []
    f = Path(D) / "memos" / "versions" / "INDEX.txt"
    if f.exists():
        for ln in f.read_text().splitlines():
            m = re.match(r"(\S+) v(\d+) (\w+) (\S+) md5 (\w+)", ln)
            if m:
                rows.append((m.group(1), int(m.group(2)), m.group(3), m.group(4)))
    return rows


def commit_at(rows, rel: str, ts: str) -> str:
    """`git log --until=<ts> -1 --format='%h %cI' -- rel` from INDEX.txt: the last version of `rel` committed at or before `ts`."""
    t = parse_ts(ts)
    best = ""
    for path, _v, sha, ctime in rows:
        if path == rel and parse_ts(ctime) <= t:
            best = f"{sha} {ctime}"
    return best


def playbook_versions_from_evidence(D: Path) -> str:
    """`git log --reverse --format='%h %cI %s'` of the playbook, from playbook/versions.txt ('<sha> <time>') and the subjects in org-git-log.txt."""
    D = Path(D)
    vf = D / "playbook" / "versions.txt"
    if not vf.exists():
        return ""
    subjects = {}
    gl = D / "org-git-log.txt"
    if gl.exists():
        cur = None
        want_subject = False
        for ln in gl.read_text(errors="replace").splitlines():
            m = re.match(r"commit (\w{40})", ln)
            if m:
                cur, want_subject = m.group(1), False
                continue
            if cur and ln.startswith("Date:"):
                want_subject = True
                continue
            if cur and want_subject and ln.strip():
                subjects[cur] = ln.strip()
                want_subject = False
    out = []
    for ln in vf.read_text().splitlines():
        parts = ln.split()
        if len(parts) < 2:
            continue
        sha, t = parts[0], parts[1]
        subj = next((s for full, s in subjects.items() if full.startswith(sha)), "")
        out.append(f"{sha} {t} {subj}".rstrip())
    return "\n".join(out)


def main(argv):
    args = list(argv)
    out = product_src = None
    for flag in ("--out", "--product-src"):
        if flag in args:
            i = args.index(flag)
            val = args[i + 1]
            del args[i:i + 2]
            if flag == "--out":
                out = val
            else:
                product_src = val
    if len(args) != 2:
        print(__doc__)
        return 2
    D, S = Path(args[0]), args[1]
    if not (D / "assistant-session-messages.jsonl").exists():
        print(f"not a stream evidence dir: {D}", file=sys.stderr)
        return 2
    res = run_extract(D, S, Path(out) if out else D, product_src or PRODUCT_SRC)
    print(f"runs {res['runs']}, sessions {res['sessions']}, matched {res['matched']}, unmatched runs {res['unmatched']}, "
          f"revise_playbook events {res['revise_playbook']}, flags {res['flags']}, calls {res['calls']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
