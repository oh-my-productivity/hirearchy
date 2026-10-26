#!/usr/bin/env python3
"""G0 assistant-layer facts (design 20.4 B): the MECHANICAL part of each assistant-layer measure of one stream, and the candidates the scorer
must judge. Every judged decision (D5 "asked", D-OFFER, D-SPEND, D-LATE, D-SEEN, the user's request for a rework ...) goes into
`measures/judged.json`, never into this code. Standard library only; it imports no product module.

Reads (read-only) in the stream dir <D>: assistant-session-messages.jsonl, session-turn-times-utc.txt, turn-times.txt, turn-NN.txt,
turn-NN.prompt.txt, lena-lines.txt, msgs/ (root's sent / read / inbox boxes), injection/ (injection-log.txt, window.txt),
memos/versions/INDEX.txt, run-logs/, events/, skill-check.txt, sandbox-path.txt, arm.txt; and, from the extracts directory (default: the
stream dir; `--extracts DIR` to use freshly regenerated ones): client-questions.txt, run-session-map.txt.
Writes <D>/measures/assistant_facts.json (or --out DIR/assistant_facts.json): sorted keys, `source_files`, `script` {name, md5}, and a flat
`measures` dict that aggregate.py reads.

Usage:
    python3 -B assistant_facts.py <streamdir> [--out DIR] [--extracts DIR]
    python3 -B assistant_facts.py --selfcheck <E7EV> --out <harness-selfcheck dir>     (runs the whole E7 chain on s1-s3 and compares
        `selfcheck/e7-expected-assistant.json`; prints OK / MISMATCH lines and `selfcheck assistant: k of n OK`; exit 0 iff all OK)

Definitions used (E7 protocol): skill stratum 4.4.1; flagged item D19 (an item naming `\\bC[0-9]+\\b`; notes apart, D-NOTE); copy D6 (the
`execute_bash` writes that extract_mechanical.py's shell flags call "writes into the deliverable folder", plus file-write tools naming the
deliverable folder); superseded / never copied D7 (a `source: human` root task that `revises` a task of the case, created after the result
and before the first copy after it; a rework is checked first, so a result with a rework and no copy is `superseded`); ask-first copies
10.3(c) with Interpretation 20 (only the string `artifacts withheld (ask first)` on the line of the task the case's latest result replies to,
in the last `progress` reply between that result and the copy); hand edit M-P3-2 (the copied version's md5 differs from the md5 of the artifact
of the case's latest result at that result's time, by memos/versions/INDEX.txt); refusal kinds M-P2-2 / M-P4-4; D-SURVIVE / D-SIGNAL / M-C-8
through scheduler_survival.py."""
import ast
import glob
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import extract_mechanical as em  # noqa: E402  (pure helpers; its product import happens only inside run_extract)
import scheduler_survival as ss  # noqa: E402

FLAG_RE = re.compile(r"\b\d+ questions? for the client: ask the user before you copy or deliver")
ASK_FIRST = "artifacts withheld (ask first)"
TOPUP_TEXT = "and a rework of this team needs about"
HELD_TEXT = "The team still holds"
BUDGET_RE = re.compile(r"^Use \d+ runs per request( for \S.*?)? \(covers one round of your questions or a rejection\), or keep \d+\?$", re.M)
MONTHS = {m: i for i, m in enumerate(["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"], 1)}
D1_RE = re.compile(r"(No, not right yet|Not right yet|Almost)")
REFUSALS = [  # (kind, regex) in the order of E7 protocol 10.5 M-P2-2 / M-P4-4; first match wins
    ("P2-ROOT-ONLY", r"answers, about and words are root's"),
    ("P2-NOT-AN-AMENDMENT", r"this call changes none\. Pass them only with acceptance"),
    ("P2-NEEDS-WORDS", r"records the user's words\. If it answers a rejection"),
    ("P2-WORDS-LONG", r"refused: words \(CLI: --words\) is .*? characters; the limit is"),
    ("P2-PAIR", r"answers and about go together"),
    ("P2-UNREADABLE", r"cannot be read \(.*so the contract was not changed"),
    ("P2-UNRATED", r"have no verdict yet:.*The contract changes only after the verdicts"),
    ("P2-NOT-A-REJECTION", r"answers \(CLI: --answers\) must be the message id of a rejection"),
    ("P2-ANSWERED", r"already has its answer \("),
    ("P2-ABOUT", r"about \(CLI: --about\) must be the id your one question named"),
    ("P2-WORDS-ARE-THE-REJECTION", r"repeats rejection.*own note"),
    ("P2-OPEN-REJECTION", r"has no answer yet, so this change is not one the user asked for on their own"),
    ("P2-CONTINUES", r"continues the retired service kept at"),
    ("P2-RETIRE-UNRATED", r"a service is retired only after its verdicts"),
    ("P2-RETIRE-OPEN", r"A service is retired only after its rejections are answered"),
    ("P2-RETIRE-UNREADABLE", r"so the service was not retired"),
    ("P2-CONFIRMS-ANSWERED", r"records the user's yes: one rejection gets one answer"),
    ("P2-CONFIRMS-RECOVERY", r"and its link is missing \(its write failed\)"),
    ("P4-BASE-VALUE", r'base must be "delivered" or "latest"'),
    ("P4-BASE-WHERE", r"base goes only with a rework the user asked for"),
    ("P4-NEEDS-BASE", r"since the delivery the client judged"),
    ("P4-USE-REQUEST", r"is a request for the service.*send it back with request\("),
    ("FACADE-ROOT-TASK", r"a root task for a service, or a rework, goes through request\("),
    ("FACADE-ROOT-VERDICT", r"a verdict or a link from root goes through feedback\("),
]
REFUSAL_RES = [(k, re.compile(r, re.S | (re.I if k == "P2-UNRATED" else 0))) for k, r in REFUSALS]


# ---------------------------------------------------------------- small pure helpers
def rate(k, n):
    return {"k": k, "n": n}


def show(r):
    return "n/a (0 of 0)" if r["n"] == 0 else f"{r['k']} of {r['n']}"


def date_in(text):
    """The meeting date (YYYY-MM-DD) a file name or title names: an ISO date, or 'D Month YYYY'."""
    m = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", text or "")
    if m:
        return m.group(1)
    m = re.search(r"\b(\d{1,2}) (" + "|".join(MONTHS) + r") (\d{4})\b", text or "")
    if m:
        return f"{m.group(3)}-{MONTHS[m.group(2)]:02d}-{int(m.group(1)):02d}"
    return None


def ts(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def skill_md5(text):
    m = re.search(r"md5 of the SKILL\.md at that path: (\w{32})", text or "")
    return m.group(1) if m else None


def _brief(c):
    return {"call": c["n"], "turn": c["turn"], "ts": c["ts"], "uri": c.get("uri")} if c else None


def skill_facts(calls, whole_text):
    """Skill activation (E7 protocol 4.4.1): the first non-error disclose_context naming hirearchy against the first propose_org / feedback."""
    dis = [c for c in calls if c["name"] == "disclose_context" and c["status"] != "failed"
           and (str((c["args"] or {}).get("name", "")).lower() == "hirearchy" or (c.get("uri") or "").endswith("/hirearchy/SKILL.md"))
           and not re.match(r"(?i)\s*(error|failed)", c["result"] or "")]
    prop = em.hcalls(calls, "propose_org")
    fb = em.hcalls(calls, "feedback")
    first_d = min(dis, key=lambda c: ts(c["ts"])) if dis else None
    first_p = prop[0] if prop else None
    first_f = fb[0] if fb else None
    if not prop and not fb:
        stratum = "n/a"
    elif not first_d:
        stratum = "N"
    else:
        later = [x for x in (first_p, first_f) if x]
        stratum = "A" if all(ts(first_d["ts"]) < ts(x["ts"]) for x in later) else "B"
    return {"stratum": stratum, "first_disclose": _brief(first_d), "first_propose_org": _brief(first_p), "first_feedback": _brief(first_f),
            "disclose_calls": len(dis), "installed_skill_notes": len(re.findall(r"Note: the installed skill at", whole_text or "")), "skill_md5": None}


def classify_refusal(text):
    """The refusal kind of a tool reply ('P2-UNRATED', 'P4-NEEDS-BASE', 'FACADE-ROOT-TASK', ..., 'other'), or None if the reply is no refusal."""
    t = (text or "").strip()
    m = re.match(r"(?:MCP tool error: Error executing tool \w+: )?(refused:.*)", t, re.S)
    if not m:
        return None
    body = m.group(1)
    for kind, rx in REFUSAL_RES:
        if rx.search(body):
            return kind
    return "other"


def budget_lines(text):
    """The product's budget question lines of a PLAN FOR YOU text (BUDGET_QUESTION and BUDGET_QUESTION_FOR of src/hirearchy/blueprint/_plan_texts.py)."""
    return [m.group(0) for m in BUDGET_RE.finditer(text or "")]


def lena_rules(line):
    """The rule ids (H<n>, L-...) USED in a lena-lines.txt line: those in the rule field (the text between its first and second '|') with
    parentheses removed, except a token the field names only to say it was not used (the 30 characters before it, up to the last '+' or ';',
    hold 'instead of', 'not', 'no', 'never' or 'rather than')."""
    parts = line.split("|")
    field = parts[1] if len(parts) > 1 else ""
    while True:
        new = re.sub(r"\([^()]*\)", "", field)
        if new == field:
            break
        field = new
    out = set()
    for m in re.finditer(r"\b(H\d+|L-[A-Z0-9][A-Z0-9-]*)\b", field):
        before = re.split(r"[+;]", field[max(0, m.start() - 30):m.start()])[-1].lower()
        if re.search(r"(instead of|rather than|\bnot\b|\bno\b|\bnever\b)", before):
            continue
        out.add(m.group(1))
    return out


def copy_cases(cmd):
    """The meeting dates a copy command writes: dates in the deliverable-folder paths it names, else in its org source paths."""
    dest = [t for t in re.findall(r"\S+", cmd) if "deliverables" in t]
    dates = []
    for t in dest:
        d = date_in(os.path.basename(t.rstrip("/'\";&|)")))
        if d and d not in dates:
            dates.append(d)
    if not dates:
        for sp in em.source_paths(cmd):
            d = date_in(os.path.basename(sp))
            if d and d not in dates:
                dates.append(d)
    return dates


# ---------------------------------------------------------------- the stream
def read_text(p):
    try:
        return Path(p).read_text(errors="replace")
    except FileNotFoundError:
        return ""


def index_rows(D):
    rows = []
    for ln in read_text(Path(D) / "memos" / "versions" / "INDEX.txt").splitlines():
        m = re.match(r"(\S+) v(\d+) (\w+) (\S+) md5 (\w+)", ln)
        if m:
            rows.append({"path": m.group(1), "version": int(m.group(2)), "sha": m.group(3), "time": m.group(4), "md5": m.group(5)})
    return rows


def version_at(rows, rel, t):
    best = None
    for r in rows:
        if r["path"] == rel and ts(r["time"]) <= t:
            best = r
    return {"sha": best["sha"], "time": best["time"], "md5": best["md5"], "path": rel} if best else None


def load_msgs(D):
    msgs = {}
    for box in ("sent", "read", "inbox"):
        for f in sorted(glob.glob(str(Path(D) / "msgs" / box / "*.md"))):
            hdr, body, _ = em.read_msg(f)
            hdr = dict(hdr)
            msgs[hdr.get("id", Path(f).stem)] = {"hdr": hdr, "body": body, "box": box, "file": f}
    return msgs


def parse_created(h):
    try:
        return ts(h.get("created", ""))
    except ValueError:
        return None


class Case:
    """case-of-message resolution (the meeting date a task, result or note belongs to)."""

    def __init__(self, msgs, seat_path):
        self.msgs, self.seat_path = msgs, seat_path

    def task(self, tid, depth=0):
        m = self.msgs.get(tid)
        if not m or depth > 8:
            return None
        nf = re.search(r"^- notes_file: (\S+)", m["body"], re.M)
        d = (date_in(nf.group(1)) if nf else None) or date_in(m["hdr"].get("title", ""))
        if d:
            return d
        for k in ("revises", "reply_to"):
            if m["hdr"].get(k):
                d = self.task(m["hdr"][k], depth + 1)
                if d:
                    return d
        return None

    def artifacts(self, body):
        out, inside = [], False
        for line in body.splitlines():
            if line.startswith("## "):
                inside = line[3:].strip().lower() == "artifacts"
            elif inside and line.strip():
                out.append(line.strip().lstrip("-* ").split(" (", 1)[0])
        return out

    def result(self, m):
        for a in self.artifacts(m["body"]):
            if self.seat_path and a.startswith(self.seat_path + "/"):
                continue
            d = date_in(os.path.basename(a))
            if d:
                return d
        return self.task(m["hdr"].get("reply_to"))

    def artifact_of(self, m, case):
        for a in self.artifacts(m["body"]):
            if self.seat_path and a.startswith(self.seat_path + "/"):
                continue
            if case in os.path.basename(a):
                return a
        return None


def parse_client_questions(text):
    """[{id, folder, created, reply_to, status, frm, items}] from client-questions.txt."""
    out, cur = [], None
    for ln in text.splitlines():
        m = re.match(r"- id (\S+) folder=(\S+) created=(\S+) answers\(reply_to\)=(\S+) status=(\S+) from=(\S+)", ln)
        if m:
            cur = {"id": m.group(1), "folder": m.group(2), "created": m.group(3), "reply_to": m.group(4), "status": m.group(5), "from": m.group(6), "items": []}
            out.append(cur)
            continue
        m = re.match(r"  parsed items \((\d+)\): (\[.*\])$", ln)
        if m and cur is not None:
            cur["items"] = ast.literal_eval(m.group(2))
            cur = None
    return out


def injection_flags(log):
    """[(ts, task id)] for every progress-reply line of injection-log.txt that carries the question flag."""
    out, cur = [], None
    for ln in log.splitlines():
        m = re.match(r"--- (\w+) at (\S+)", ln)
        if m:
            cur = m.group(2)
            continue
        if FLAG_RE.search(ln):
            t = re.search(r"\(task (\S+?)\)\s*$", ln)
            out.append((cur, t.group(1) if t else None))
    return out


def analyse(D, extracts=None):
    D = Path(D)
    E = Path(extracts) if extracts else D
    sources = ["assistant-session-messages.jsonl"]
    calls, turns = em.load_session(D)
    info = em.detect(D)
    seat_path = info["seat_dir"].replace("-", "/") if info["seat_dir"] else None
    S = read_text(D / "sandbox-path.txt").strip()
    label = D.name
    arm = read_text(D / "arm.txt").strip() or (label.split("-")[0] if re.match(r"m[01]-", label) else "e7")
    msgs = load_msgs(D)
    sources.append("msgs/")
    case = Case(msgs, seat_path)
    inj_log = read_text(D / "injection" / "injection-log.txt")
    m = re.search(r"injected task id: (\S+)", inj_log)
    injected = m.group(1) if m else None
    rows = index_rows(D)
    sources.append("memos/versions/INDEX.txt")
    whole = read_text(D / "assistant-session-messages.jsonl")

    # ---- results root received, tasks root sent
    results = []
    for mid, m in msgs.items():
        h = m["hdr"]
        if m["box"] in ("read", "inbox") and h.get("to") == "root" and h.get("type") == "result":
            results.append({"id": mid, "created": parse_created(h), "created_raw": h.get("created"), "status": h.get("status"), "reply_to": h.get("reply_to"),
                            "case": case.result(m), "msg": m})
    results.sort(key=lambda r: (r["created"], r["id"]))
    sent_tasks = [m for m in msgs.values() if m["box"] == "sent" and m["hdr"].get("type") == "task" and m["hdr"].get("from") == "root"]
    human_reworks = [m for m in sent_tasks if m["hdr"].get("source") == "human" and m["hdr"].get("revises")]

    # ---- skill
    sk = skill_facts(calls, whole)
    sc = read_text(D / "skill-check.txt")
    if sc:
        sources.append("skill-check.txt")
    sk["skill_md5"] = skill_md5(sc)

    # ---- copies (D6)
    copies = []
    for c in calls:
        nm = c["name"]
        if nm == "execute_bash":
            cmd = c["args"].get("command", "")
            flags, wrote = em.shell_flags(cmd, S)
            if not wrote:
                continue
            srcs = em.source_paths(cmd)
            for cs in copy_cases(cmd) or [None]:
                src = next((sp for sp in srcs if cs and cs in os.path.basename(sp)), srcs[0] if srcs else None)
                rel = (src.split("/org/", 1)[-1] if "/org/" in src else src[len("org/"):]) if src else None
                copies.append({"call": c["n"], "turn": c["turn"], "ts": c["ts"], "case": cs, "tool": "execute_bash", "command": cmd[:400],
                               "source_path": rel})
        elif nm and re.search(r"write|create|append|edit|replace", nm) and "hirearchy" not in (c.get("tool") or ""):
            path = c["args"].get("path") or c["args"].get("file_path") or ""
            if "deliverables" in str(path) or "deliverables" in json.dumps(c["args"]):
                copies.append({"call": c["n"], "turn": c["turn"], "ts": c["ts"], "case": date_in(os.path.basename(str(path))), "tool": nm,
                               "command": json.dumps(c["args"], ensure_ascii=False)[:400], "source_path": None})
    progress_like = [c for c in calls if c["result"] and FLAG_RE.search(c["result"]) is not None or (c["tool"] and c["tool"].split("::")[-1] in ("progress", "status", "whoami"))]
    feedbacks = em.hcalls(calls, "feedback")

    def human_fb_after(cs, t0):
        out = []
        for f in feedbacks:
            a = f["args"].get("arguments") or {}
            if a.get("source") != "human" or ts(f["ts"]) <= t0:
                continue
            tc = case.task(a.get("task_id"))
            if tc == cs:
                out.append({"call": f["n"], "turn": f["turn"], "verdict": a.get("verdict"), "task": a.get("task_id")})
        return out

    for cp in copies:
        t = ts(cp["ts"])
        cp["source_version"] = version_at(rows, cp["source_path"], t) if cp["source_path"] else None
        latest = None
        for r in results:
            if r["case"] == cp["case"] and r["created"] and r["created"] <= t:
                latest = r
        cp["latest_result"] = {"id": latest["id"], "created": latest["created_raw"], "status": latest["status"], "reply_to": latest["reply_to"]} if latest else None
        art = case.artifact_of(latest["msg"], cp["case"]) if latest else None
        cp["checked_version"] = version_at(rows, art, latest["created"]) if (latest and art) else None
        if cp["source_version"] and cp["checked_version"]:
            cp["hand_edit"] = cp["source_version"]["md5"] != cp["checked_version"]["md5"]
        else:
            cp["hand_edit"] = None
        # ask-first shown (10.3(c), Interpretation 20)
        cp["ask_first_shown"], cp["progress_call"] = False, None
        if latest:
            pcs = [c for c in em.hcalls(calls, "progress") if latest["created"] <= ts(c["ts"]) < t]
            if pcs:
                last = pcs[-1]
                cp["progress_call"] = last["n"]
                for ln in (last["result"] or "").splitlines():
                    if latest["reply_to"] and f"(task {latest['reply_to']})" in ln and ASK_FIRST in ln:
                        cp["ask_first_shown"] = True
        cp["human_feedback_after"] = human_fb_after(cp["case"], t)
    n_hand = sum(1 for c in copies if c["hand_edit"])

    # ---- flagged items (D19 / D7 / D-NOTE)
    cq = parse_client_questions(read_text(E / "client-questions.txt"))
    sources.append("client-questions.txt")
    inj_flags = injection_flags(inj_log)
    items, by_result = [], {}
    for r in cq:
        if not r["items"]:
            continue
        res = next((x for x in results if x["id"] == r["id"]), None)
        cs = res["case"] if res else case.task(r["reply_to"])
        t_r = res["created"] if res else ts(r["created"])
        later_copies = [c for c in copies if c["case"] == cs and ts(c["ts"]) > t_r]
        first_copy = min(later_copies, key=lambda c: ts(c["ts"])) if later_copies else None
        reworks = []
        for w in human_reworks:
            wt = parse_created(w["hdr"])
            if wt and wt >= t_r and (first_copy is None or wt < ts(first_copy["ts"])) and case.task(w["hdr"]["id"]) == cs:
                reworks.append(w["hdr"]["id"])
        flagged_by = []
        for c in calls:
            if c["result"] and ts(c["ts"]) >= t_r:
                for ln in c["result"].splitlines():
                    if FLAG_RE.search(ln) and r["reply_to"] and f"(task {r['reply_to']})" in ln:
                        flagged_by.append({"source": "assistant", "call": c["n"], "turn": c["turn"], "ts": c["ts"]})
                        break
        for (t0, tid) in inj_flags:
            if tid == r["reply_to"] and t0 and ts(t0) >= t_r:
                flagged_by.append({"source": "injection-log", "ts": t0})
        cls = lambda: ("superseded" if reworks else "never copied" if first_copy is None else "needs D5 judgement (copy at T)")  # noqa: E731
        br = by_result.setdefault(r["id"], {"created": r["created"], "status": r["status"], "case": cs, "reply_to": r["reply_to"], "questions": 0, "notes": 0,
                                           "superseded": 0, "never_copied": 0, "needs_d5": 0,
                                           "first_flag_call": min([f["call"] for f in flagged_by if f["source"] == "assistant"], default=None)})
        for text in r["items"]:
            kind = "question" if re.search(r"\bC[0-9]+\b", text) else "note"
            klass = cls()
            items.append({"result": r["id"], "created": r["created"], "case": cs, "kind": kind, "text": text, "class": klass,
                          "copy": ({"call": first_copy["call"], "turn": first_copy["turn"], "ts": first_copy["ts"]} if first_copy else None),
                          "reworks_between": reworks, "flagged_by": flagged_by})
            if kind == "question":
                br["questions"] += 1
                key = {"superseded": "superseded", "never copied": "never_copied"}.get(klass, "needs_d5")
                br[key] += 1
            else:
                br["notes"] += 1
    q_items = [i for i in items if i["kind"] == "question"]
    counts = {"results_with_items": len(by_result), "items": len(items), "questions": len(q_items), "notes": len(items) - len(q_items),
              "superseded": sum(1 for i in q_items if i["class"] == "superseded"),
              "never_copied": sum(1 for i in q_items if i["class"] == "never copied"),
              "needs_d5": sum(1 for i in q_items if i["class"].startswith("needs D5"))}

    # ---- rejects (per human reject: the defines after it, the window and its turn files)
    humans = [f for f in feedbacks if (f["args"].get("arguments") or {}).get("verdict") == "reject" and (f["args"].get("arguments") or {}).get("source") == "human"]
    defines = em.hcalls(calls, "define_service")
    last_turn = turns[-1]["n"] if turns else 0
    rej = []
    for i, f in enumerate(humans):
        a = f["args"].get("arguments") or {}
        nxt = humans[i + 1] if i + 1 < len(humans) else None
        after = [d for d in defines if ts(d["ts"]) > ts(f["ts"]) and (nxt is None or ts(d["ts"]) < ts(nxt["ts"]))]
        dl, first_ok = [], None
        for d in after:
            kind = classify_refusal(d["result"])
            ok = kind is None and d["status"] != "failed" and (d["result"] or "").startswith("redefined")
            dl.append({"call": d["n"], "turn": d["turn"], "ts": d["ts"], "status": "admitted" if ok else ("refused" if kind else "failed"), "refusal": kind,
                       "answers": (d["args"].get("arguments") or {}).get("answers"), "about": (d["args"].get("arguments") or {}).get("about")})
            if ok and first_ok is None:
                first_ok = d
        if first_ok:
            end = {"kind": "define_service", "turn": first_ok["turn"], "call": first_ok["n"]}
            until = first_ok["turn"] - 1
        elif nxt:
            end = {"kind": "next_reject", "turn": nxt["turn"]}
            until = nxt["turn"] - 1
        else:
            end = {"kind": "stream_end", "turn": last_turn}
            until = last_turn
        rej.append({"call": f["n"], "turn": f["turn"], "ts": f["ts"], "task": a.get("task_id"), "criterion": a.get("criterion"),
                    "defines_after": dl, "window_end": end, "turn_files_between": [f"turn-{n:02d}.txt" for n in range(f["turn"], until + 1)]})
    lena = {}
    for ln in read_text(D / "lena-lines.txt").splitlines():
        mm = re.match(r"turn (\d+) \|", ln)
        if mm:
            lena[int(mm.group(1))] = ln
    sources.append("lena-lines.txt")
    d1 = []
    for n in sorted(lena):
        pr = read_text(D / f"turn-{n:02d}.prompt.txt")
        if D1_RE.match(pr):
            d1.append(n)
    d1_unrec = [n for n in d1 if not any(h["turn"] == n for h in humans)]
    no_reading = [h for h in humans if not any(re.fullmatch(r"[CR][0-9]+", str(x)) for x in ((h["args"].get("arguments") or {}).get("criterion") or []))]
    about_diff = 0
    about_n = 0
    for r in rej:
        for dd in r["defines_after"]:
            if dd["status"] == "admitted" and dd["answers"] and dd["about"]:
                note = msgs.get(dd["answers"])
                reading = set(re.findall(r"[CR][0-9]+", (note["hdr"].get("criterion", "") if note else "")))
                if reading:
                    about_n += 1
                    about_diff += 0 if dd["about"] in reading else 1

    # ---- relayed reworks through the assistant's server
    relayed = [{"id": m["hdr"]["id"], "created": m["hdr"].get("created"), "revises": m["hdr"].get("revises"), "budget": m["hdr"].get("budget"), "title": m["hdr"].get("title")}
               for m in sent_tasks if m["hdr"].get("source") == "relayed" and m["hdr"]["id"] != injected]

    # ---- reads
    orgs = [S + "/org", ("/private" + S + "/org") if S.startswith("/tmp/") else S + "/org"]
    shell_reads = 0
    for c in calls:
        txt = c["args"].get("command", "") if c["name"] == "execute_bash" else (c["args"].get("path", "") if c["name"] == "read_file" else "")
        if txt and any(o in txt for o in orgs) and re.search(r"/(inbox|read|sent)/", txt):
            shell_reads += 1
    unread = sum(1 for m in msgs.values() if m["box"] == "inbox" and m["hdr"].get("to") == "root" and m["hdr"].get("type") in ("result", "note"))
    reads = {"inbox_calls": len(em.hcalls(calls, "inbox")), "read_calls": len(em.hcalls(calls, "read")), "shell_reads": shell_reads, "root_unread_at_end": unread}

    # ---- refusals
    ref_list, by_kind = [], {}
    for c in calls:
        if not c["tool"]:
            continue
        k = classify_refusal(c["result"])
        if k:
            by_kind[k] = by_kind.get(k, 0) + 1
            ref_list.append({"call": c["n"], "turn": c["turn"], "tool": c["tool"].split("::")[-1], "kind": k, "text": (c["result"] or "")[:300]})
    refusals = {"by_kind": by_kind, "list": ref_list, "p2_total": sum(v for k, v in by_kind.items() if k.startswith("P2-")),
                "p4_total": sum(v for k, v in by_kind.items() if k.startswith("P4-")), "facade_total": sum(v for k, v in by_kind.items() if k.startswith("FACADE-")),
                "other_total": by_kind.get("other", 0)}

    # ---- plan
    plans = []
    for c in em.hcalls(calls, "propose_org"):
        txt = c["result"] or ""
        if "PLAN FOR YOU" not in txt:
            continue
        lines = budget_lines(txt)
        sec = (read_text(D / f"turn-{c['turn']:02d}.txt").split("######## ASSISTANT", 1) + [""])[1]
        shown = bool(lines) and all(" ".join(l.split()) in " ".join(sec.split()) for l in lines)
        plans.append({"call": c["n"], "turn": c["turn"], "has_budget_line": bool(lines), "lines": lines, "shown_verbatim_in_turn": shown})
    rules_by_turn = {n: lena_rules(l) for n, l in lena.items()}
    plan = {"plans": len(plans), "list": plans, "plans_with_budget_line": rate(sum(1 for p in plans if p["has_budget_line"]), len(plans)),
            "turns_showing_line": len({p["turn"] for p in plans if p["shown_verbatim_in_turn"]}),
            "lena_yes_h4": sum(1 for r in rules_by_turn.values() if "H4" in r), "lena_keep_l_budget_q": sum(1 for r in rules_by_turn.values() if "L-BUDGET-Q" in r)}

    # ---- topup / held / grants / human reworks
    topup = [{"call": c["n"], "turn": c["turn"], "tool": c["tool"].split("::")[-1]} for c in calls if c["tool"] and TOPUP_TEXT in (c["result"] or "")]
    held = [{"call": c["n"], "turn": c["turn"], "tool": c["tool"].split("::")[-1]} for c in calls if c["tool"] and HELD_TEXT in (c["result"] or "")]
    grants = []
    for c in em.hcalls(calls, "send"):
        a = c["args"].get("arguments") or {}
        if a.get("budget") is not None:
            grants.append({"call": c["n"], "turn": c["turn"], "to": a.get("to"), "budget": a.get("budget")})
    hr = []
    for c in em.hcalls(calls, "request"):
        a = c["args"].get("arguments") or {}
        if a.get("source") == "human" and a.get("revises"):
            mm = re.search(r"budget (\d+)", c["result"] or "")
            hr.append({"call": c["n"], "turn": c["turn"], "budget_arg": a.get("budget"), "reply_budget": int(mm.group(1)) if mm else None,
                       "topup": TOPUP_TEXT in (c["result"] or ""), "held": HELD_TEXT in (c["result"] or "")})
    human_rw = {"count": len(hr), "without_budget": sum(1 for h in hr if h["budget_arg"] is None), "list": hr}

    # ---- L-ASIS
    lasis_turns = [n for n, r in rules_by_turn.items() if "L-ASIS" in r]
    accepted = [n for n in lasis_turns if any((f["args"].get("arguments") or {}).get("verdict") == "accept" and (f["args"].get("arguments") or {}).get("source") == "human" and f["turn"] == n for f in feedbacks)]
    lasis = {"turns": lasis_turns, "accepted_turns": accepted, "uses": len(lasis_turns), "accepted": rate(len(accepted), len(lasis_turns))}

    # ---- verdict recording
    versions = {}
    for cp in copies:
        key = (cp["case"], (cp["source_version"] or {}).get("sha") or f"call{cp['call']}")
        versions.setdefault(key, cp)
    no_verdict = [k for k, cp in versions.items() if not cp["human_feedback_after"]]
    verdicts = {"delivered_versions": len(versions), "delivered_without_verdict": rate(len(no_verdict), len(versions))}

    # ---- memo turns: from the turn that created the case's first root task to the turn of the first human accept on a task of the case
    def turn_of(t):
        for tr in turns:
            if tr.get("user_ts") and tr.get("end") and ts(tr["user_ts"]) - timedelta(seconds=1) <= t <= ts(tr["end"]) + timedelta(seconds=1):
                return tr["n"]
        return None

    memo = []
    cases_seen = sorted({cp["case"] for cp in copies if cp["case"]} | {case.task(m["hdr"]["id"]) for m in sent_tasks if case.task(m["hdr"]["id"])})
    for cs in cases_seen:
        first = None
        for m in sorted(sent_tasks, key=lambda x: parse_created(x["hdr"]) or ts("2999-01-01T00:00:00Z")):
            if case.task(m["hdr"]["id"]) == cs and not m["hdr"].get("revises") and m["hdr"].get("source") != "relayed":
                first = m
                break
        rq_turn = turn_of(parse_created(first["hdr"])) if first else None
        rq_call = next((c["n"] for c in calls if first and c["tool"] and first["hdr"]["id"] in (c["result"] or "")), None)
        ac = next((f for f in feedbacks if (f["args"].get("arguments") or {}).get("verdict") == "accept" and (f["args"].get("arguments") or {}).get("source") == "human"
                   and case.task((f["args"].get("arguments") or {}).get("task_id")) == cs), None)
        memo.append({"case": cs, "request_call": rq_call, "request_turn": rq_turn, "accept_call": ac["n"] if ac else None, "accept_turn": ac["turn"] if ac else None,
                     "turns": (ac["turn"] - rq_turn + 1) if (rq_turn and ac) else None, "copies": [cp["turn"] for cp in copies if cp["case"] == cs]})

    # ---- schedulers
    sa = ss.analyse(D)
    sources.extend(["events/", "session-turn-times-utc.txt", "turn-times.txt"])
    sched = {"total": sa["counts"]["schedulers"], "assistant_started": sa["counts"]["assistant_started"], "script_started": sa["counts"]["script_started"],
             "unknown_starter": sa["counts"]["unknown_starter"], "reasons": sa["counts"]["reasons"], "m_c_1": sa["m_c_1"], "m_c_2_pairs": sa["m_c_2_pairs"],
             "m_c_2_runs": sa["m_c_2_runs"], "m_c_4": sa["m_c_4"], "m_c_6": sa["m_c_6"], "m_c_7": sa["m_c_7"], "m_c_8": {"k": sa["m_c_8"]["k"], "n": sa["m_c_8"]["n"]},
             "sleep_entries": sa["sleep_entries"], "boundary_failure_files": sa["m_c_8"]["boundary_failure_files"],
             "signals": sa["signals"], "run_orphan": sa["counts"]["run_orphan"], "run_end_killed": sa["counts"]["run_end_killed"], "stop_calls": sa["counts"]["stop_calls"],
             "per_scheduler": [{"pid": s["pid"], "starter": s["starter"]["kind"], "began_in_turn": s["began_in_turn"], "exit_reason": (s["exit"] or {}).get("reason"),
                                "classes": [p["class"] for p in s["running_at_turn_ends"]]} for s in sa["schedulers"]]}

    # ---- cost
    cost = cost_facts(D, E, turns)
    sources.append("session-turn-times-utc.txt")

    deliverable_notes = len([c for c in calls if c["tool"] and "did not deliver as checked" in (c["result"] or "")])
    shell_commands = len([c for c in calls if c["name"] == "execute_bash"])
    measures = {
        "skill_stratum": sk["stratum"],
        "schedulers_total": sched["total"], "schedulers_assistant": sched["assistant_started"], "schedulers_script": sched["script_started"],
        "schedulers_running_at_turn_end": sched["m_c_1"], "survival_pairs": sched["m_c_2_pairs"], "schedulers_with_exit": sched["m_c_4"],
        "run_orphan": sched["run_orphan"], "run_end_killed": sched["run_end_killed"], "scheduler_signals": len(sched["signals"]),
        "unexplained_signals": sched["m_c_7"], "m_c_8": sched["m_c_8"], "sleep_entries": sched["sleep_entries"], "boundary_failure_files": len(sched["boundary_failure_files"]),
        "copies": len(copies), "hand_edits": rate(n_hand, len(copies)), "ask_first_copies": rate(sum(1 for c in copies if c["ask_first_shown"]), len(copies)),
        "delivered_without_verdict": verdicts["delivered_without_verdict"],
        "flagged_results": counts["results_with_items"], "flagged_items": counts["items"], "flagged_questions": counts["questions"], "flagged_notes": counts["notes"],
        "flagged_superseded": counts["superseded"], "flagged_never_copied": counts["never_copied"], "flagged_needs_d5": counts["needs_d5"],
        "shell_commands": shell_commands, "inbox_calls": reads["inbox_calls"], "shell_reads": reads["shell_reads"], "root_unread_at_end": reads["root_unread_at_end"],
        "p2_refusals": refusals["p2_total"], "p2_unrated": by_kind.get("P2-UNRATED", 0), "p4_refusals": refusals["p4_total"], "facade_refusals": refusals["facade_total"],
        "other_refusals": refusals["other_total"],
        "human_rejects": len(humans), "d23_without_reading": rate(len(no_reading), len(humans)), "d1_never_recorded": rate(len(d1_unrec), len(d1)),
        "d23_about_differs": rate(about_diff, about_n),
        "plans": plan["plans"], "plans_with_budget_line": plan["plans_with_budget_line"], "turns_showing_budget_line": plan["turns_showing_line"],
        "lena_yes_h4": plan["lena_yes_h4"], "lena_keep_l_budget_q": plan["lena_keep_l_budget_q"],
        "topup_replies": len(topup), "held_replies": len(held), "grants": len(grants), "human_reworks": human_rw["count"], "human_reworks_without_budget": human_rw["without_budget"],
        "relayed_reworks_by_assistant": len(relayed), "lasis_uses": lasis["uses"], "lasis_accepted": lasis["accepted"], "deliverable_notes": deliverable_notes,
        "user_turns": cost["user_turns"], "assistant_credits": cost["assistant_credits"], "assistant_seconds": cost["assistant_seconds"], "wall_time": cost["wall_time"],
        "wall_seconds": cost["wall_seconds"],
        "org_runs_outside": cost["org_runs"]["outside"], "org_runs_window": cost["org_runs"]["window"], "org_credits_outside": cost["org_credits"]["outside"],
        "org_credits_window": cost["org_credits"]["window"], "org_seconds_outside": cost["org_seconds"]["outside"], "org_seconds_window": cost["org_seconds"]["window"],
    }
    for i in range(3):
        measures[f"memo{i + 1}_turns"] = memo[i]["turns"] if i < len(memo) else None
    return {"stream": label, "arm": arm, "owner": info["owner"], "service": info["service"], "seat": info["seat_dir"], "injected_task": injected,
            "skill": sk, "rejects": {"human_rejects": rej, "d1_candidate_turns": d1, "d1_never_recorded": d1_unrec, "without_reading": rate(len(no_reading), len(humans)),
                                     "about_differs_from_reading": rate(about_diff, about_n)},
            "flagged": {"items": items, "by_result": by_result, "counts": counts},
            "relayed_reworks": {"sent": relayed, "injected": injected},
            "copies": {"list": copies, "count": len(copies), "hand_edits": rate(n_hand, len(copies)),
                       "ask_first": rate(sum(1 for c in copies if c["ask_first_shown"]), len(copies))},
            "verdicts": verdicts, "reads": reads, "refusals": refusals, "plan": plan, "topup_held": {"topup": topup, "held": held}, "grants": grants,
            "human_reworks": human_rw, "lasis": lasis, "memo_turns": memo, "schedulers": sched, "cost": cost, "measures": measures,
            "source_files": sorted(set(sources))}


def cost_facts(D, E, turns):
    """Assistant credits / seconds / turns / wall time (the session's own `usage_summary` entries, whose sum equals the session store's total:
    summing the per-turn rounded lines of session-turn-times-utc.txt is 0.0001-0.0002 lower, E7 STUDY Correction 18) and org runs by seat
    (run-logs/, injection/window.txt, credits from run-session-map.txt)."""
    cr = sec = 0.0
    for line in open(Path(D) / "assistant-session-messages.jsonl"):
        p = em.payload(json.loads(line))
        if p.get("type") == "usage_summary":
            sec += (p.get("elapsedTime") or 0) / 1000
            for t in p.get("promptTurnSummaries") or []:
                cr += t.get("usage", 0) or 0
    starts = [ts(t["start"]) for t in turns if t.get("start")]
    ends = [ts(t["end"]) for t in turns if t.get("end")]
    wall = (max(ends) - min(starts)).total_seconds() if (starts and ends) else None
    wall_s = int(wall + 0.5) if wall is not None else None
    credits = {}
    for ln in read_text(Path(E) / "run-session-map.txt").splitlines():
        m = re.match(r"^run (\S+)\s+(\d{8}T\d+) model=\S+ exit=\S+ secs=\S+ -> session \S+ credits ([\d.]+)", ln)
        if m:
            credits[m.group(2)] = float(m.group(3))
    win = None
    wf = Path(D) / "injection" / "window.txt"
    if wf.exists() and len(wf.read_text().split()) >= 2:
        w0, w1 = wf.read_text().split()[:2]
        win = (ts(w0 + "Z"), ts(w1 + "Z"))
    runs = {"outside": 0, "window": 0}
    secs = {"outside": 0, "window": 0}
    cred = {"outside": 0.0, "window": 0.0}
    by_seat, win_seat = {}, {}
    for lg in sorted(glob.glob(str(Path(D) / "run-logs" / "*" / "*.log"))):
        stamp, agent = Path(lg).stem, Path(lg).parent.name
        txt = read_text(lg)
        ex = re.search(r"^# exit (\S+) after (\d+)s", txt, re.M)
        w = bool(win and win[0] <= em.stamp_to_dt(stamp) <= win[1])
        k = "window" if w else "outside"
        runs[k] += 1
        secs[k] += int(ex.group(2)) if ex else 0
        cred[k] += credits.get(stamp, 0.0)
        (win_seat if w else by_seat)[agent] = (win_seat if w else by_seat).get(agent, 0) + 1
    return {"user_turns": len(turns), "assistant_credits": round(cr, 4), "assistant_seconds": int(sec + 0.5), "wall_seconds": wall_s,
            "wall_time": f"{wall_s // 60}:{wall_s % 60:02d}" if wall_s is not None else None,
            "org_runs": {"total": runs["outside"] + runs["window"], "outside": runs["outside"], "window": runs["window"], "outside_by_seat": by_seat, "window_by_seat": win_seat},
            "org_credits": {k: round(v, 4) for k, v in cred.items()}, "org_seconds": secs}


def render_txt(a):
    m = a["measures"]
    out = [f"# assistant facts: {a['stream']} (arm {a['arm']}; facts only, judged measures are not here)", ""]
    for k in sorted(m):
        v = m[k]
        out.append(f"{k}: {show(v) if isinstance(v, dict) and set(v) == {'k', 'n'} else v}")
    out.append("")
    out.append("flagged items (class by D7; the D5 judgement is the scorer's):")
    for i in a["flagged"]["items"]:
        out.append(f"- {i['result']} [{i['kind']}] case {i['case']}: {i['class']}" + (f" (copy #{i['copy']['call']} turn {i['copy']['turn']})" if i["copy"] else "") + f": {i['text'][:120]}")
    return out


def write_outputs(a, out, name="assistant_facts"):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    j = dict(a)
    j["script"] = {"name": Path(__file__).name, "md5": hashlib.md5(Path(__file__).read_bytes()).hexdigest()}
    (out / f"{name}.json").write_text(json.dumps(j, sort_keys=True, indent=2, default=str) + "\n")
    (out / f"{name}.txt").write_text("\n".join(render_txt(a)) + "\n")


# ---------------------------------------------------------------- the E7 self-check
LAST_EXTRACT_ROWS = []
EXTRACT_FILES = ["revise-playbook-attempts.txt", "client-questions.txt", "contract-loop.txt", "deliverables-log.txt", "shell-writes.txt",
                 "lead-prompt-sizes.txt", "cost.txt", "run-session-map.txt"]


def _diff_rows(stream, label, mine_root, theirs_root, prefix=""):
    import difflib
    rows, chunks = [], []
    for f in EXTRACT_FILES + ["injection/text-identity.txt", "injection/window-runs.txt"]:
        a_p = Path(mine_root) / f if not f.startswith("injection/") else Path(mine_root).parent / f
        b_p = Path(theirs_root) / f
        a = read_text(a_p).splitlines()
        b = read_text(b_p).splitlines()
        d = list(difflib.unified_diff(b, a, f"E7 committed {f}", f"regenerated {f}", lineterm="", n=0))
        rem = sum(1 for l in d if l.startswith("-") and not l.startswith("---"))
        add = sum(1 for l in d if l.startswith("+") and not l.startswith("+++"))
        rows.append({"stream": stream, "file": prefix + f, "identical": not d, "differing_lines": max(rem, add)})
        if d:
            chunks.append(f"##### {label} {prefix}{f}\n" + "\n".join(d))
    for sub in ("reflect-sections", "regression-list"):
        mine = {p.name: read_text(p) for p in sorted((Path(mine_root) / sub).glob("*"))}
        theirs = {p.name: read_text(p) for p in sorted((Path(theirs_root) / sub).glob("*"))}
        same_ = mine == theirs
        rows.append({"stream": stream, "file": f"{prefix}{sub}/", "identical": same_, "differing_lines": 0 if same_ else len(set(mine) ^ set(theirs)) + sum(1 for k in mine if k in theirs and mine[k] != theirs[k]),
                     "files": len(theirs)})
        if not same_:
            chunks.append(f"##### {label} {prefix}{sub}/: files only in one side: {sorted(set(mine) ^ set(theirs))}; changed: {[k for k in mine if k in theirs and mine[k] != theirs[k]]}")
    return rows, chunks


def extract_diffs(E7EV, out):
    """Regenerate E7's extracts from the stream dirs with extract_mechanical.py (no sandbox) and injection_files.py, and diff them against
    E7's committed ones. When E7's sandbox still exists the extracts are also regenerated from it and compared (rows named `sandbox:<file>`).
    Writes out/e7-sN/extract-diff.txt (unified diffs of every file that differs). Returns [{stream, file, identical, differing_lines}]."""
    import injection_files as inj
    E7EV, out = Path(E7EV), Path(out)
    allrows = []
    for st in ("s1", "s2", "s3"):
        d = E7EV / st
        o = out / f"e7-{st}"
        em.run_extract(d, "-", o / "extract")
        inj.run_injection_files(d, "-", o / "injection", smap=o / "extract" / "run-session-map.txt")
        rows, chunks = _diff_rows(st, st, o / "extract", d)
        sandbox = Path(read_text(d / "sandbox-path.txt").strip())
        if (sandbox / "org" / ".git").exists():
            em.run_extract(d, str(sandbox), o / "extract-sandbox")
            inj.run_injection_files(d, str(sandbox), o / "injection-sandbox", smap=o / "extract-sandbox" / "run-session-map.txt")
            r2, c2 = _diff_rows(st, st, o / "extract-sandbox", d, prefix="sandbox:")
            # the injection files of the sandbox run live in injection-sandbox/
            for r in r2:
                if r["file"].startswith("sandbox:injection/"):
                    f = r["file"][len("sandbox:"):]
                    import difflib
                    a = read_text(o / "injection-sandbox" / f.split("/", 1)[1]).splitlines()
                    b = read_text(d / f).splitlines()
                    dd = list(difflib.unified_diff(b, a, lineterm="", n=0))
                    r["identical"] = not dd
                    r["differing_lines"] = max(sum(1 for l in dd if l.startswith("-") and not l.startswith("---")), sum(1 for l in dd if l.startswith("+") and not l.startswith("+++")))
            rows += r2
            chunks += [c for c in c2 if "injection/" not in c]
        (o / "extract-diff.txt").write_text(("\n\n".join(chunks) if chunks else "no differences") + "\n")
        allrows += rows
    return allrows


def resolve(obj, path):
    cur = obj
    for part in path.split("."):
        if cur is None:
            return None
        if isinstance(cur, list):
            try:
                cur = cur[int(part)]
            except (ValueError, IndexError):
                return None
        elif isinstance(cur, dict):
            cur = cur.get(part)
        else:
            return None
    return cur


def same(expected, actual):
    if isinstance(expected, float) or isinstance(actual, float):
        try:
            return abs(float(expected) - float(actual)) <= 6e-5
        except (TypeError, ValueError):
            return False
    return expected == actual


def selfcheck(E7EV, out, expected_path):
    """Run the whole chain on E7's s1-s3 (extract_mechanical in no-sandbox mode, scheduler_survival, injection_files, assistant_facts), write the
    outputs under `out/e7-sN/`, and compare every expected entry. Returns [{stream, key, expected, actual, ok, source}]."""
    import injection_files as inj
    E7EV, out = Path(E7EV), Path(out)
    facts = {}
    LAST_EXTRACT_ROWS[:] = extract_diffs(E7EV, out)  # regenerates out/e7-sN/extract and injection, writes extract-diff.txt
    for s in ("s1", "s2", "s3"):
        d = E7EV / s
        o = out / f"e7-{s}"
        ss_a = ss.analyse(d)
        o.mkdir(parents=True, exist_ok=True)
        (o / "scheduler-survival.txt").write_text("\n".join(ss.render(ss_a, s)) + "\n")
        (o / "scheduler_survival.json").write_text(json.dumps(ss_a, sort_keys=True, indent=2) + "\n")
        a = analyse(d, extracts=o / "extract")
        write_outputs(a, o)
        facts[s] = a
    results = []
    for e in json.loads(Path(expected_path).read_text()):
        st, key = e["stream"], e["key"]
        if st == "all":
            op, path = key.split(":", 1)
            vals = [resolve(facts[s], path) for s in ("s1", "s2", "s3")]
            if op == "sum":
                actual = sum(vals)
            else:
                actual = {"k": sum(v["k"] for v in vals), "n": sum(v["n"] for v in vals)}
        else:
            actual = resolve(facts[st], key)
        results.append({"stream": st, "key": key, "expected": e["expected"], "actual": actual, "ok": same(e["expected"], actual), "source": e["source"]})
    return results


def main(argv):
    args = list(argv)
    opts = {}
    for flag in ("--out", "--extracts", "--selfcheck"):
        if flag in args:
            i = args.index(flag)
            opts[flag] = args[i + 1]
            del args[i:i + 2]
    if "--selfcheck" in opts:
        out = Path(opts.get("--out") or ".")
        res = selfcheck(opts["--selfcheck"], out, Path(__file__).resolve().parent / "selfcheck" / "e7-expected-assistant.json")
        lines = []
        for r in res:
            tag = "OK" if r["ok"] else "MISMATCH"
            lines.append(f"{tag} {r['stream']} {r['key']}: expected {r['expected']!r} actual {r['actual']!r} [{r['source']}]")
        k = sum(1 for r in res if r["ok"])
        diff_lines = [f"{'EXTRACT-SAME' if r['identical'] else 'EXTRACT-DIFF'} {r['stream']} {r['file']}" + ("" if r["identical"] else f": {r['differing_lines']} line(s) differ from E7's committed file (see e7-{r['stream']}/extract-diff.txt)")
                      for r in LAST_EXTRACT_ROWS]
        final = f"selfcheck assistant: {k} of {len(res)} OK"
        print("\n".join(lines + diff_lines + [final]))
        for s in ("s1", "s2", "s3"):
            (out / f"e7-{s}").mkdir(parents=True, exist_ok=True)
            (out / f"e7-{s}" / "assistant-selfcheck.txt").write_text(
                "\n".join([l for l in lines if f" {s} " in l or " all " in l] + [l for l in diff_lines if f" {s} " in l] + [final]) + "\n")
        return 0 if k == len(res) else 1
    if len(args) != 1:
        print(__doc__)
        return 2
    D = Path(args[0])
    if not (D / "assistant-session-messages.jsonl").exists():
        print(f"not a stream evidence dir: {D}", file=sys.stderr)
        return 2
    a = analyse(D, extracts=opts.get("--extracts"))
    write_outputs(a, Path(opts["--out"]) if "--out" in opts else D / "measures")
    print(f"assistant facts for {a['stream']} written")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
