#!/usr/bin/env python3
"""G0 harness, helper M: score every memo version and final memo against the answer key (E7 protocol D15-D18) and
map the reviewer's first result to the version it reviewed (D21's time window).

    python3 -B score_memos.py <streamdir> --out <dir> [--answer-key PATH]
    python3 -B score_memos.py --selfcheck <E7EV> --out <selfcheck dir> [--expected PATH]

Standard library only (Python 3.11). Never imports hirearchy product code. Reads the stream directory read-only. The private
answer key is read from its one place (default below) and is never copied: only its md5 and a consistency check against the
pre-registered tables in this file are written.

PRE-REGISTERED KEYWORD SETS (frozen; tuned only on E7's 24 versions + 9 finals, never on a G0 stream).
  A key decision / key action is present "in substance" when EVERY group of its "all" list has AT LEAST ONE alternative that occurs
  in the item text (case-insensitive, markdown marks and runs of blanks removed). An alternative is a substring, except that an
  alternative starting with "=" is a whole word. A key action also needs the right owner (the Owner cell, markdown removed,
  equals the key's owner, case-insensitive). Decisions are searched in the items of the decisions section only; actions in the
  rows of the table of the action-items section only.
"""
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_ANSWER_KEY = "/Volumes/workspace/hirearchy/studies/G0-noise-baseline/evidence/answer-key.md"
DEFAULT_EXPECTED = str(Path(__file__).resolve().parent / "selfcheck" / "e7-expected-team.json")

# ---------------------------------------------------------------------------------------------------------------------------
# The pre-registered key (E7 protocol D15 for the Dues; D18 for "in substance").
# ---------------------------------------------------------------------------------------------------------------------------
_RL = ["rate limiter", "rate-limiter", "rate limit"]
KEY = {
    "2026-10-05": {
        "decisions": [
            {"id": "D1", "all": [["gateway"], ["26 oct", "october 26", "26th"]]},
            {"id": "D2", "all": [["renovate"], ["weekly", "monday", "dependency"]]},
        ],
        "actions": [
            {"id": "A1", "owner": "Priya", "due": "2026-10-09", "all": [["rfc"], _RL]},
            {"id": "A2", "owner": "Dev", "due": "2026-10-08", "all": [["renovate"]]},
            {"id": "A3", "owner": "Marta", "due": "2026-10-14", "all": [["room"], ["book", "reserve"]]},
            {"id": "A4", "owner": "Sam", "due": "2026-10-09", "all": [["=ci", "flaky", "build cache"]]},
            {"id": "A5", "owner": "Lee", "due": "none", "all": [["vendor", "sso", "certificate"]]},
        ],
    },
    "2026-10-12": {
        "decisions": [
            {"id": "D1", "all": [["rfc"], ["token bucket"], ["approv", "go ahead", "accepted", "agreed", "adopt"]]},
            {"id": "D2", "all": [["postmortem", "post-mortem"], ["blameless"]]},
            {"id": "D3", "all": [["freeze"], ["22"], ["23"]]},
        ],
        "actions": [
            {"id": "A1", "owner": "Dev", "due": "2026-10-14", "all": [["postmortem", "post-mortem"]]},
            {"id": "A2", "owner": "Marta", "due": "2026-10-16", "all": [["agenda"], ["send", "customer"]]},
            {"id": "A3", "owner": "Priya", "due": "2026-10-20", "all": [_RL, ["implement", "build", "start", "feature flag"]]},
            {"id": "A4", "owner": "Sam", "due": "2026-10-21", "all": [["staging"], ["data", "test"]]},
            {"id": "A5", "owner": "Lee", "due": "none", "all": [["pager", "on-call", "shift", "swap"]]},
        ],
    },
    "2026-10-19": {
        "decisions": [
            {"id": "D1", "all": [["demo"], _RL, ["without", "left out", "leaving", "leave out", "excluding", "exclude", "omit",
                                                  "not include", "out of", "minus"]]},
            {"id": "D2", "all": [["sso"], ["renew"], ["twelve", "12"]]},
            {"id": "D3", "all": [["10:00"], ["14:00", "2 pm", "2pm", "2:00 pm", "14.00"], ["26 oct", "october 26", "26th", "2026-10-26"]]},
        ],
        "actions": [
            {"id": "A1", "owner": "Marta", "due": "2026-10-23", "all": [["feedback"]]},
            {"id": "A2", "owner": "Dev", "due": "2026-10-24", "all": [["freeze"]]},
            {"id": "A3", "owner": "Priya", "due": "2026-10-26", "all": [["benchmark"]]},
            {"id": "A4", "owner": "Lee", "due": "2026-10-30", "all": [["sso", "renewal", "legal"], ["sign"]]},
            {"id": "A5", "owner": "Sam", "due": "none", "all": [["=jo"]]},
        ],
    },
}
N_DECISIONS = sum(len(m["decisions"]) for m in KEY.values())  # 8
N_ACTIONS = sum(len(m["actions"]) for m in KEY.values())  # 15

ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
_BULLET = re.compile(r"^(\s*)(?:[-*+]|\d+[.)])\s+(.*)$")
_HEADING = re.compile(r"^\s{0,3}(#{1,6})\s+(.*?)\s*#*\s*$")
_BOLD_HEADING = re.compile(r"^\s*(?:\*\*|__)([^*_].*?)(?:\*\*|__)\s*:?\s*$")
_SEPARATOR_CELL = re.compile(r"^:?-{1,}:?$")


# ---------------------------------------------------------------------------------------------------------------------------
# small utilities shared with the other team-layer scripts
# ---------------------------------------------------------------------------------------------------------------------------
def md5_bytes(b):
    return hashlib.md5(b).hexdigest()


def rate(k, n):
    return {"k": int(k), "n": int(n)}


def rate_text(r):
    return f"{r['k']} of {r['n']}" if r["n"] else "n/a (0 of 0)"


def words(b):
    """`wc -w`: whitespace-separated tokens of the file's bytes."""
    if isinstance(b, str):
        b = b.encode()
    return len(b.split())


def strip_marks(s):
    return re.sub(r"[*_`]", "", s).strip()


def norm(s):
    return re.sub(r"\s+", " ", strip_marks(s).lower()).strip()


def alt_matches(alt, text):
    if alt.startswith("="):
        return re.search(r"(?<![a-z0-9])" + re.escape(alt[1:]) + r"(?![a-z0-9])", text) is not None
    return alt in text


def groups_match(groups, text):
    t = norm(text)
    return all(any(alt_matches(a, t) for a in g) for g in groups)


def utc_iso(dt):
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_time(s):
    """ISO-ish timestamp -> aware UTC datetime (a missing zone means UTC)."""
    s = s.strip().strip("'\"")
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


# ---------------------------------------------------------------------------------------------------------------------------
# memo structure
# ---------------------------------------------------------------------------------------------------------------------------
def _heading_of(line):
    m = _HEADING.match(line)
    if m:
        return len(m.group(1)), m.group(2)
    m = _BOLD_HEADING.match(line)
    if m:
        return 7, m.group(1).strip().rstrip(":")
    return None


def _headings(lines):
    return [(i, h[0], h[1]) for i, ln in enumerate(lines) if (h := _heading_of(ln))]


def _section_index(lines, word):
    for i, _lvl, text in _headings(lines):
        if word in text.lower():
            return i
    return None


def _section_body(lines, word):
    i = _section_index(lines, word)
    if i is None:
        return None
    hs = [h[0] for h in _headings(lines) if h[0] > i]
    return lines[i + 1:(hs[0] if hs else len(lines))]


def summary_first(text):
    """D17: the first content line after at most one title heading is a single line starting `Summary:`."""
    lines = text.splitlines()
    i = 0
    while i < len(lines) and not lines[i].strip():
        i += 1
    if i < len(lines) and _HEADING.match(lines[i]):
        i += 1
        while i < len(lines) and not lines[i].strip():
            i += 1
    if i >= len(lines) or not lines[i].startswith("Summary:"):
        return False
    nxt = lines[i + 1] if i + 1 < len(lines) else ""
    return not nxt.strip() or _heading_of(nxt) is not None


def decisions_before_actions(text):
    """D17: the decisions section comes before the action-items section (both must exist)."""
    lines = text.splitlines()
    d, a = _section_index(lines, "decision"), _section_index(lines, "action")
    return d is not None and a is not None and d < a


def decision_items(text):
    body = _section_body(text.splitlines(), "decision") or []
    items, cur = [], None
    for ln in body:
        if not ln.strip():
            cur = None
            continue
        m = _BULLET.match(ln)
        if m:
            items.append(m.group(2).strip())
            cur = len(items) - 1
        elif ln.lstrip().startswith("|"):
            cells = split_row(ln)
            if cells and not all(_SEPARATOR_CELL.match(c) for c in cells if c):
                items.append(" ".join(cells))
            cur = None
        elif cur is not None and ln[:1].isspace():
            items[cur] += " " + ln.strip()
        else:
            items.append(ln.strip())
            cur = len(items) - 1
    return items


def split_row(line):
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|") and not s.endswith("\\|"):
        s = s[:-1]
    return [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", s)]


def action_rows(text):
    """Rows of the first table of the action-items section (header and separator removed): dicts owner/action/due/cells."""
    lines = text.splitlines()
    body = _section_body(lines, "action")
    if body is None:
        return []
    rows, header = [], None
    for ln in body:
        if not ln.lstrip().startswith("|"):
            if rows or header:
                break  # the first table only
            continue
        cells = split_row(ln)
        if all(_SEPARATOR_CELL.match(c) for c in cells if c) and any(cells):
            continue
        if header is None:
            low = [strip_marks(c).lower() for c in cells]
            if "owner" in low or "due" in low:
                header = low
                continue
            header = ["owner", "action", "due"]
        idx = {k: (header.index(k) if k in header else d) for k, d in (("owner", 0), ("action", 1), ("due", 2))}
        if "action" not in header:
            for alt in ("task", "item", "action item"):
                if alt in header:
                    idx["action"] = header.index(alt)
        get = lambda k: cells[idx[k]] if idx[k] < len(cells) else ""  # noqa: E731
        rows.append({"owner": strip_marks(get("owner")), "action": get("action"), "due": strip_marks(get("due")),
                     "cells": [strip_marks(c) for c in cells]})
    return rows


def due_value(cell):
    c = strip_marks(cell).strip()
    m = ISO_DATE.match(c)
    if m:
        return m.group(0)
    if c.lower().startswith("none"):
        return "none"
    return c.lower()


def score_memo(text, meeting):
    """Score one memo's text against the key of `meeting` (KeyError for an unknown meeting)."""
    key = KEY[meeting]
    dec_items = decision_items(text)
    found_d = [d["id"] for d in key["decisions"] if any(groups_match(d["all"], it) for it in dec_items)]
    rows = action_rows(text)
    consumed, found_a, wrong, extra = set(), [], [], []
    for r in rows:
        hit = None
        for a in key["actions"]:
            if a["owner"].lower() == strip_marks(r["owner"]).lower() and groups_match(a["all"], r["action"]):
                hit = a
                break
        if hit is None or hit["id"] in consumed:
            extra.append(" | ".join(r["cells"]))
            continue
        consumed.add(hit["id"])
        found_a.append(hit["id"])
        if due_value(r["due"]) != hit["due"]:
            wrong.append({"owner": hit["owner"], "due": r["due"], "expected": hit["due"], "action": hit["id"]})
    return {
        "decisions": rate(len(found_d), len(key["decisions"])), "decisions_found": found_d,
        "actions": rate(len(found_a), len(key["actions"])), "actions_found": found_a,
        "wrong_dates": wrong, "extra_rows": extra,
        "summary_first": summary_first(text), "decisions_before_actions": decisions_before_actions(text),
        "words": words(text),
    }


# ---------------------------------------------------------------------------------------------------------------------------
# reading a stream directory
# ---------------------------------------------------------------------------------------------------------------------------
class Reader:
    """Remembers which files of the stream were actually used (the JSON's `source_files`)."""

    def __init__(self, stream):
        self.stream = Path(stream)
        self.files = set()

    def rel(self, p):
        try:
            return str(Path(p).relative_to(self.stream))
        except ValueError:
            return str(p)

    def note(self, p):
        self.files.add(self.rel(p))

    def read_bytes(self, p):
        self.note(p)
        return Path(p).read_bytes()

    def read_text(self, p):
        return self.read_bytes(p).decode("utf-8", errors="replace")

    def source_files(self):
        return sorted(self.files)


def script_info(path):
    p = Path(path).resolve()
    return {"name": p.name, "md5": md5_bytes(p.read_bytes())}


def parse_msg_text(raw):
    """Front matter (`key: value` lines between two `---` lines) and body of a message file."""
    h, body = {}, raw
    if raw.startswith("---\n"):
        end = raw.find("\n---", 4)
        if end != -1:
            for ln in raw[4:end].splitlines():
                if ":" in ln and not ln.startswith(" "):
                    k, v = ln.split(":", 1)
                    h[k.strip()] = v.strip().strip("'\"")
            body = raw[end + 4:].lstrip("\n")
    return h, body


def read_msgs(stream):
    """Every message file under msgs/ (deduplicated by id): {id: {"h": headers, "body": text, "path": absolute Path}}."""
    out = {}
    root = Path(stream) / "msgs"
    if not root.is_dir():
        return out
    for p in sorted(root.glob("*/*.md")):
        raw = p.read_text(encoding="utf-8", errors="replace")
        h, body = parse_msg_text(raw)
        mid = h.get("id") or p.stem
        out.setdefault(mid, {"h": h, "body": body, "path": p, "raw": raw})
    return out


# ---------------------------------------------------------------------------------------------------------------------------
# versions, copies
# ---------------------------------------------------------------------------------------------------------------------------
_VERSION_FILE = re.compile(r"^memo-(\d{4}-\d{2}-\d{2})\.v(\d+)\.([0-9a-f]+)\.md$")
_INDEX_LINE = re.compile(r"^(\S*memo-(\d{4}-\d{2}-\d{2})\.md) v(\d+) ([0-9a-f]+) (\S+) md5 ([0-9a-f]{32})\s*$")


def load_versions(stream, rd=None):
    rd = rd or Reader(stream)
    vdir = Path(stream) / "memos" / "versions"
    index = {}
    ip = vdir / "INDEX.txt"
    if ip.exists():
        for ln in rd.read_text(ip).splitlines():
            m = _INDEX_LINE.match(ln)
            if m:
                index[(m.group(2), int(m.group(3)))] = {"sha": m.group(4), "time": m.group(5), "md5": m.group(6)}
    out = []
    for p in sorted(vdir.glob("memo-*.md")) if vdir.is_dir() else []:
        m = _VERSION_FILE.match(p.name)
        if not m:
            continue
        memo, ver, sha = m.group(1), int(m.group(2)), m.group(3)
        ix = index.get((memo, ver))
        b = rd.read_bytes(p)
        out.append({"memo": memo, "version": ver, "sha": sha, "commit_time": ix["time"] if ix else None, "file": rd.rel(p),
                    "md5": md5_bytes(b), "index_md5": ix["md5"] if ix else None, "_bytes": b})
    out.sort(key=lambda v: (v["memo"], v["version"]))
    return out


_COPY_HEADER = re.compile(r"^\[(\S+Z)\] call #(\d+) turn (\d+) (\S+)")
_COPY_SOURCE = re.compile(r"(\S*memo-(\d{4}-\d{2}-\d{2})\.md) -> org-git commit at that time: ([0-9a-f]+) (\S+?)['\"\],]*(?=\s|$|'|\")")


def load_copies(stream, rd=None):
    """One entry per copy recorded in deliverables-log.txt: the call, the turn, the time and the commit it copied."""
    rd = rd or Reader(stream)
    p = Path(stream) / "deliverables-log.txt"
    if not p.exists():
        return []
    blocks, cur = [], None
    for ln in rd.read_text(p).splitlines():
        m = _COPY_HEADER.match(ln)
        if m:
            cur = {"call": int(m.group(2)), "turn": int(m.group(3)), "time": m.group(1), "tool": m.group(4), "lines": []}
            blocks.append(cur)
        elif cur is not None:
            cur["lines"].append(ln)
    out = []
    for b in blocks:
        seen = set()
        for ln in b["lines"]:
            if not ln.startswith("source file(s):"):
                continue
            for m in _COPY_SOURCE.finditer(ln):
                key = (m.group(2), m.group(3))
                if key in seen:
                    continue
                seen.add(key)
                out.append({"call": b["call"], "turn": b["turn"], "time": b["time"], "tool": b["tool"], "memo": m.group(2),
                            "commit": m.group(3), "commit_time": m.group(4)})
    return out


def load_log_md5s(stream, rd=None):
    rd = rd or Reader(stream)
    p = Path(stream) / "deliverables-log.txt"
    return set(re.findall(r"\b[0-9a-f]{32}\b", rd.read_text(p))) if p.exists() else set()


def final_files(stream):
    d = Path(stream) / "memos"
    return sorted(p for p in d.glob("memo-*.md") if p.is_file()) if d.is_dir() else []


def final_md5s(stream, rd=None):
    rd = rd or Reader(stream)
    return {md5_bytes(rd.read_bytes(p)) for p in final_files(stream)}


def mark_copied(versions, copies, log_md5s, finals_md5s):
    """A version is copied when a copy entry names its commit, or its md5 is a file written into the deliverable folder
    (an md5 in deliverables-log.txt or a final file in memos/). Returns new dicts."""
    out = []
    for v in versions:
        v = dict(v)
        cps = [c for c in copies if c["memo"] == v["memo"] and (v["sha"].startswith(c["commit"]) or c["commit"].startswith(v["sha"]))]
        by = []
        if cps:
            by.append("log-commit")
        if v["md5"] in log_md5s:
            by.append("log-md5")
        if v["md5"] in finals_md5s:
            by.append("final-md5")
        v["copies"] = cps
        v["copied_by"] = by
        v["copied"] = bool(by)
        out.append(v)
    return out


# ---------------------------------------------------------------------------------------------------------------------------
# the agents; the reviewer's results
# ---------------------------------------------------------------------------------------------------------------------------
_REVIEW_ROLE = re.compile(r"review|check|verif|audit|\bqa\b|assur|critic", re.I)


def find_roles(stream, rd=None):
    """owner = the agent the root tasks go to; reviewer = the owner's child whose charter role says review/check, else the one
    whose results carry `criteria met` / PASS."""
    rd = rd or Reader(stream)
    msgs = read_msgs(stream)
    tos = {}
    for m in msgs.values():
        h = m["h"]
        if h.get("from") == "root" and h.get("type") == "task" and h.get("service"):
            tos[h.get("to")] = tos.get(h.get("to"), 0) + 1
    owner = max(tos, key=lambda k: (tos[k], k)) if tos else None
    if owner is None:
        logs = Path(stream) / "run-logs"
        names = sorted(d.name for d in logs.iterdir() if d.is_dir() and "-" not in d.name) if logs.is_dir() else []
        owner = names[0] if names else "lead"
    stem = owner.replace("/", "-") + "-"
    children = {}
    for m in msgs.values():
        h = m["h"]
        f = h.get("from", "")
        if h.get("type") == "result" and f.startswith(owner + "/") and f.count("/") == owner.count("/") + 1:
            children.setdefault(f, {"results": 0, "scored": 0})
            children[f]["results"] += 1
            if re.search(r"criteria\s+met|\bPASS\b", m["raw"], re.I):
                children[f]["scored"] += 1
    ofiles = Path(stream) / "org-files"
    roles = {}
    if ofiles.is_dir():
        for p in sorted(ofiles.glob(stem + "*-AGENT.md")):
            child = p.name[len(stem):-len("-AGENT.md")]
            if "-" in child:
                continue
            addr = owner + "/" + child
            h, _ = parse_msg_text(rd.read_text(p))
            roles[addr] = h.get("role", "")
            children.setdefault(addr, {"results": 0, "scored": 0})
    by_charter = sorted(a for a in children if _REVIEW_ROLE.search(roles.get(a, "")))
    detected, reviewer = None, None
    if by_charter:
        reviewer = max(by_charter, key=lambda a: (children[a]["scored"], a))
        detected = "charter"
    else:
        cands = sorted(a for a in children if children[a]["scored"])
        if cands:
            reviewer = max(cands, key=lambda a: (children[a]["scored"], a))
            detected = "results"
    return {"owner": owner, "reviewer": reviewer, "reviewer_dir": reviewer.replace("/", "-") if reviewer else None,
            "detected_by": detected, "roles": roles, "children": sorted(children)}


_MET = re.compile(r"criteria\s+met:?\s*(\d+)\s+of\s+(\d+)", re.I)
_VERDICT = re.compile(r"verdict:?\s*\**\s*(not pass|pass|fail)", re.I)


def parse_review(text):
    m = _MET.search(text)
    v = _VERDICT.search(text)
    met, of = (int(m.group(1)), int(m.group(2))) if m else (None, None)
    return {"met": met, "of": of, "all_met": (met == of) if m else None, "verdict": v.group(1).upper() if v else None,
            "ambiguous_token": "ambiguous" in text.lower()}


def task_memo(h, body, known):
    """The memo date a review task is about: an ISO date of the title, else the `memo-<date>` path in the body, else the first
    known meeting date in the body."""
    for m in ISO_DATE.finditer(h.get("title", "")):
        if m.group(0) in known:
            return m.group(0)
    for m in re.finditer(r"memo-(\d{4}-\d{2}-\d{2})", body):
        if m.group(1) in known:
            return m.group(1)
    for m in ISO_DATE.finditer(body):
        if m.group(0) in known:
            return m.group(0)
    return None


_SENT_COPY = re.compile(r"(?:^|/)sent/([^/{}=> ]+)\.md$")


def load_git(stream, rd=None):
    """``(shas, sent_pos)`` from org-git-log.txt (``git log --stat``, newest first): the commits' full shas in log order, and for each message id
    the position of the first (oldest) commit whose stat lists its sent copy (``<sender>/sent/<id>.md``, ``sent/<id>.md`` or git's
    ``.../sent/<id>.md``). Both empty without the file."""
    p = Path(stream) / "org-git-log.txt"
    if not p.exists():
        return [], {}
    text = (rd or Reader(stream)).read_text(p)
    shas, paths = [], []
    for ln in text.splitlines():
        if ln.startswith("commit "):
            shas.append(ln.split()[1])
            paths.append([])
        elif shas and ln.startswith(" ") and " | " in ln:
            paths[-1].append(ln.split(" | ")[0].strip())
    sent_pos = {}
    for pos in range(len(shas) - 1, -1, -1):
        for path in paths[pos]:
            m = _SENT_COPY.search(path)
            if m:
                sent_pos.setdefault(m.group(1), pos)
    return shas, sent_pos


def map_reviews(stream, versions, roles, rd=None, rule="commit"):
    """Map each review task (to the reviewer) to the version it reviewed (D21, read as protocol 12 A3 states it).

    ``rule="commit"`` (G0's reading; manager-decision-selfcheck.md item 4): the version of the memo at the first org-git commit that holds the
    task's sent copy (the commit that closes the run which sent it, as design 0a.2's ``at_result`` reads a result's artifact): the newest version
    committed by that commit or before it. A task the log does not show (or a memo whose versions the log does not hold) falls back to the time
    window. ``rule="time"``: D21's literal timing, sent at or after the version's commit and before the next version's commit of the same memo.
    The version's review is the first result (by id) to its first mapped task; ``sent_before_commit_s`` is how long before the version's commit
    that task was sent (0 when after it)."""
    rd = rd or Reader(stream)
    shas, sent_pos = load_git(stream, rd) if rule == "commit" else ([], {})

    def pos_of(short):
        return next((i for i, full in enumerate(shas) if short and full.startswith(short)), None)
    msgs = read_msgs(stream)
    reviewer = roles.get("reviewer")
    known = {v["memo"] for v in versions} | set(KEY)
    tasks = sorted((m for m in msgs.values() if reviewer and m["h"].get("type") == "task" and m["h"].get("to") == reviewer),
                   key=lambda m: m["h"].get("id", ""))
    results = {}
    for m in msgs.values():
        if reviewer and m["h"].get("type") == "result" and m["h"].get("from") == reviewer:
            results.setdefault(m["h"].get("reply_to"), []).append(m)
    for k in results:
        results[k].sort(key=lambda m: m["h"].get("id", ""))
    by_memo = {}
    for v in versions:
        by_memo.setdefault(v["memo"], []).append(v)
    by_version, unmapped = {}, []
    for t in tasks:
        h = t["h"]
        created = parse_time(h["created"])
        memo = task_memo(h, t["body"], known)
        vs = [v for v in by_memo.get(memo, []) if v["commit_time"]]
        hit, by = None, "time"
        pos = sent_pos.get(h.get("id"))
        in_log = [(vp, v) for v in vs if (vp := pos_of(v["sha"])) is not None]
        if pos is not None and in_log:
            at = [(vp, v) for vp, v in in_log if vp >= pos]
            hit, by = (min(at, key=lambda x: x[0])[1] if at else None), "commit"
        else:
            for i, v in enumerate(vs):
                lo = parse_time(v["commit_time"])
                hi = parse_time(vs[i + 1]["commit_time"]) if i + 1 < len(vs) else None
                if lo <= created and (hi is None or created < hi):
                    hit = v
        if hit is None:
            cand = next((v for v in vs if parse_time(v["commit_time"]) > created), None)
            fr = results[h.get("id")][0] if results.get(h.get("id")) else None
            pr = parse_review(fr["body"]) if fr else {"met": None, "of": None, "verdict": None}
            unmapped.append({"task": h.get("id"), "task_created": utc_iso(created), "memo": memo,
                             "candidate_version": cand["version"] if cand else None,
                             "seconds_before_candidate_commit": int((parse_time(cand["commit_time"]) - created).total_seconds()) if cand else None,
                             "first_result": fr["h"].get("id") if fr else None,
                             "first_result_met": pr["met"], "first_result_of": pr["of"], "first_result_verdict": pr["verdict"]})
            continue
        key = (hit["memo"], hit["version"])
        ent = by_version.setdefault(key, {"tasks": []})
        ent["tasks"].append(h.get("id"))
        if "task" in ent:
            continue
        rs = results.get(h.get("id"), [])
        rd.note(t["path"])
        ent.update({"task": h.get("id"), "task_created": utc_iso(created), "result": None, "result_created": None, "status": None,
                    "met": None, "of": None, "all_met": None, "verdict": None, "ambiguous_token": None, "mapped_by": by,
                    "sent_before_commit_s": max(0, int((parse_time(hit["commit_time"]) - created).total_seconds()))})
        if rs:
            r = rs[0]
            rd.note(r["path"])
            ent.update(parse_review(r["body"]))
            ent.update({"result": r["h"].get("id"), "result_created": utc_iso(parse_time(r["h"]["created"])), "status": r["h"].get("status")})
    return {"by_version": by_version, "unmapped": unmapped, "n_tasks": len(tasks)}


# ---------------------------------------------------------------------------------------------------------------------------
# the answer key (private): only a consistency check is written, never its text
# ---------------------------------------------------------------------------------------------------------------------------
_KEY_ACTION = re.compile(r"^- A(\d+) \((?:explicit|IMPLICIT)\) (\S+) \| (.*) \| (.*?)\s*$", re.I)


def _key_due(text):
    t = text.strip()
    if t.lower().startswith("none") or re.search(r"\(none\b", t, re.I):
        return "none"
    m = ISO_DATE.search(t)
    return m.group(0) if m else t.lower()


def key_check(path):
    p = Path(path)
    if not p.exists():
        return {"status": "missing"}
    raw = p.read_bytes()
    parsed, meeting = {}, None
    for ln in raw.decode("utf-8", errors="replace").splitlines():
        m = re.match(r"^## (\d{4}-\d{2}-\d{2})\s*$", ln)
        if m:
            meeting = m.group(1)
            parsed[meeting] = {"decisions": 0, "actions": []}
            continue
        if meeting is None:
            continue
        if re.match(r"^- D\d+\b", ln):
            parsed[meeting]["decisions"] += 1
        m = _KEY_ACTION.match(ln)
        if m:
            parsed[meeting]["actions"].append((m.group(2), _key_due(m.group(4))))
    meetings = {}
    for mt, k in KEY.items():
        got = parsed.get(mt)
        if got is None:
            meetings[mt] = None
            continue
        meetings[mt] = {"decisions": got["decisions"], "actions": len(got["actions"]),
                        "owners_match": [o for o, _ in got["actions"]] == [a["owner"] for a in k["actions"]],
                        "dues_match": [d for _, d in got["actions"]] == [a["due"] for a in k["actions"]]}
    ok = all(m is not None and m["decisions"] == len(KEY[mt]["decisions"]) and m["actions"] == len(KEY[mt]["actions"])
             and m["owners_match"] and m["dues_match"] for mt, m in meetings.items())
    return {"md5": md5_bytes(raw), "meetings": meetings, "ok": ok}


# ---------------------------------------------------------------------------------------------------------------------------
# scoring a stream
# ---------------------------------------------------------------------------------------------------------------------------
def _score_fields(b, meeting):
    r = score_memo(b.decode("utf-8", errors="replace"), meeting)
    r["words"] = words(b)
    r["n_wrong_dates"] = len(r["wrong_dates"])
    r["wrong_date_text"] = [f"{w['owner']} {w['due']}" for w in r["wrong_dates"]]
    r["n_extra_rows"] = len(r["extra_rows"])
    return r


def score_stream(stream, answer_key=DEFAULT_ANSWER_KEY):
    stream = Path(stream)
    rd = Reader(stream)
    versions = load_versions(stream, rd)
    for v in versions:
        v.update(_score_fields(v.pop("_bytes"), v["memo"]))
    copies = load_copies(stream, rd)
    finals_md5 = final_md5s(stream, rd)
    versions = mark_copied(versions, copies, load_log_md5s(stream, rd), finals_md5)
    roles = find_roles(stream, rd)
    rv = map_reviews(stream, versions, roles, rd)
    for v in versions:
        v["review"] = rv["by_version"].get((v["memo"], v["version"]))
        v["final"] = v["md5"] in finals_md5
    finals, tot = [], {"d": 0, "a": 0, "w": 0, "x": 0, "s": 0}
    for p in final_files(stream):
        memo = p.stem[len("memo-"):]
        b = rd.read_bytes(p)
        if memo not in KEY:
            finals.append({"memo": memo, "file": rd.rel(p), "md5": md5_bytes(b), "error": "not a meeting of the key"})
            continue
        f = _score_fields(b, memo)
        f.update({"memo": memo, "file": rd.rel(p), "md5": md5_bytes(b)})
        match = next((v for v in versions if v["memo"] == memo and v["md5"] == f["md5"]), None)
        f["is_version"] = {"version": match["version"], "sha": match["sha"]} if match else None
        finals.append(f)
        tot["d"] += f["decisions"]["k"]
        tot["a"] += f["actions"]["k"]
        tot["w"] += len(f["wrong_dates"])
        tot["x"] += len(f["extra_rows"])
        tot["s"] += 1 if (f["summary_first"] and f["decisions_before_actions"]) else 0
    out = {
        "label": stream.name, "script": script_info(__file__), "roles": roles,
        "versions": [{k: v for k, v in x.items() if k != "index_md5" or v} for x in versions],
        "finals": finals,
        "final_totals": {"decisions": rate(tot["d"], N_DECISIONS), "actions": rate(tot["a"], N_ACTIONS), "wrong_dates": tot["w"],
                         "extra_rows": tot["x"], "summary": rate(tot["s"], len(KEY)), "memos": len([f for f in finals if "error" not in f])},
        "delivered": rate(sum(1 for v in versions if v["copied"]), len(versions)),
        "copies": copies,
        "review_unmapped": rv["unmapped"], "review_tasks": rv["n_tasks"],
        "could_not_derive": [],
    }
    for v in versions:
        if v["review"] is None:
            out["could_not_derive"].append(f"review of {v['memo']} v{v['version']} {v['sha']}: no review task sent in its window")
        elif v["review"]["met"] is None:
            out["could_not_derive"].append(f"review of {v['memo']} v{v['version']} {v['sha']}: no 'criteria met n of m' in the first result")
    for u in rv["unmapped"]:
        out["could_not_derive"].append(
            f"review task {u['task']} ({u['task_created']}, memo {u['memo']}) maps to no version"
            + (f" (it was sent {u['seconds_before_candidate_commit']} s before the commit of v{u['candidate_version']})"
               if u["candidate_version"] else ""))
    if answer_key:
        out["answer_key"] = {"path": str(answer_key), **key_check(answer_key)}
        if Path(answer_key).exists():
            rd.note(answer_key)
    out["source_files"] = rd.source_files()
    return out


def render_txt(d):
    L = [f"score_memos {d['label']}: {len(d['versions'])} versions, {len(d['finals'])} final memos; reviewer {d['roles']['reviewer']} "
         f"(owner {d['roles']['owner']})", ""]
    L.append("memo       ver sha      D    A    wrong  extra  Summary order words copied  review")
    for v in d["versions"]:
        r = v["review"]
        rv = "-" if not r else (f"{r['met']} of {r['of']}" if r["met"] is not None else "?") + (f" {r['verdict']}" if r.get("verdict") else "") + (
            f" ({r['status']})" if r.get("status") else "")
        L.append(f"{v['memo']} v{v['version']}  {v['sha']:8s} {v['decisions']['k']}/{v['decisions']['n']}  {v['actions']['k']}/{v['actions']['n']}  "
                 f"{len(v['wrong_dates']):5d}  {len(v['extra_rows']):5d}  {'yes' if v['summary_first'] else 'no ':7s} "
                 f"{'yes' if v['decisions_before_actions'] else 'no ':5s} {v['words']:5d} {'yes' if v['copied'] else 'no ':6s}  {rv}")
        for w in v["wrong_dates"]:
            L.append(f"    wrong date: {w['owner']} due {w['due']} (expected {w['expected']})")
        for x in v["extra_rows"]:
            L.append(f"    extra row: {x}")
    L.append("")
    t = d["final_totals"]
    L.append(f"final memos: decisions {rate_text(t['decisions'])}, actions {rate_text(t['actions'])}, wrong dates {t['wrong_dates']}, "
             f"extra rows {t['extra_rows']}, Summary {rate_text(t['summary'])}")
    for f in d["finals"]:
        L.append(f"  {f['memo']} md5 {f['md5']}" + (f" = v{f['is_version']['version']} {f['is_version']['sha']}" if f.get("is_version") else ""))
    L.append(f"delivered (copied) versions: {rate_text(d['delivered'])}")
    if d["could_not_derive"]:
        L.append("")
        L.append("could not derive:")
        L += [f"  {x}" for x in d["could_not_derive"]]
    return "\n".join(L) + "\n"


# ---------------------------------------------------------------------------------------------------------------------------
# JSON output and the self-check machinery (shared by the four team-layer scripts)
# ---------------------------------------------------------------------------------------------------------------------------
def dumps(d):
    return json.dumps(d, sort_keys=True, indent=2, ensure_ascii=False) + "\n"


def write_outputs(out, name, data, txt):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{name}.json").write_text(dumps(data))
    (out / f"{name}.txt").write_text(txt)


_SEG = re.compile(r"^([^\[\]]+)(?:\[([^=\]]+)=([^\]]*)\])?$")


def _split_path(path):
    parts, depth, cur = [], 0, ""
    for ch in path:
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
        if ch == "." and depth == 0:
            parts.append(cur)
            cur = ""
        else:
            cur += ch
    parts.append(cur)
    return parts


def resolve(d, path):
    """Dotted path into a JSON value; a segment `name[field=value]` selects the element of the list `name` whose `field` equals value.
    Returns (found, value)."""
    cur = d
    for seg in _split_path(path):
        m = _SEG.match(seg)
        if not m or not isinstance(cur, dict) or m.group(1) not in cur:
            return False, None
        cur = cur[m.group(1)]
        if m.group(2) is not None:
            if not isinstance(cur, list):
                return False, None
            hit = [e for e in cur if isinstance(e, dict) and str(e.get(m.group(2))) == m.group(3)]
            if not hit:
                return False, None
            cur = hit[0]
    return True, cur


def compare(actual, expected, op="eq"):
    if op == "eq":
        return actual == expected
    if not isinstance(actual, str) or not isinstance(expected, str):
        return False
    return actual.startswith(expected) if op == "startswith" else actual.endswith(expected) if op == "endswith" else False


def run_selfcheck(module, e7ev, out, expected_path, produce, name, render, label_prefix="e7-", post=None):
    """Run `produce(streamdir)` on E7EV/s1..s3, write <out>/e7-sN/<name>.json|txt, compare every expected entry of `module`.
    `post(results)` may return extra pseudo-streams {"pooled": (data, file base name, txt)}, written to <out>/e7-<name>/ and resolvable
    as stream "<name>" in the expected file. Prints OK / MISMATCH lines and `selfcheck <module>: k of n OK`.
    Returns the exit code (0 iff all OK)."""
    exp = [e for e in json.loads(Path(expected_path).read_text()) if e.get("module") == module]
    results = {}
    for s in sorted({e["stream"] for e in exp if e["stream"].startswith("s")} | {"s1", "s2", "s3"}):
        sd = Path(e7ev) / s
        if not sd.is_dir():
            continue
        results[s] = produce(sd)
        write_outputs(Path(out) / f"{label_prefix}{s}", name, results[s], render(results[s]))
    if post:
        for pname, (pdata, pbase, ptxt) in post(dict(results)).items():
            results[pname] = pdata
            write_outputs(Path(out) / f"{label_prefix}{pname}", pbase, pdata, ptxt)
    ok = 0
    for e in exp:
        found, actual = resolve(results.get(e["stream"], {}), e["key"])
        good = found and compare(actual, e["expected"], e.get("op", "eq"))
        shown = json.dumps(actual, sort_keys=True, ensure_ascii=False) if found else "NOT FOUND"
        if good:
            ok += 1
            print(f"OK {e['stream']} {e['key']} = {json.dumps(e['expected'], ensure_ascii=False)}")
        else:
            print(f"MISMATCH {e['stream']} {e['key']} expected={json.dumps(e['expected'], ensure_ascii=False)}"
                  f"{' (' + e['op'] + ')' if e.get('op') else ''} actual={shown} source={e.get('source', '')}")
    print(f"selfcheck {module}: {ok} of {len(exp)} OK")
    return 0 if ok == len(exp) else 1


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="Score memo versions and final memos against the answer key (G0 harness, helper M)")
    ap.add_argument("streamdir", nargs="?")
    ap.add_argument("--out", required=True)
    ap.add_argument("--answer-key", default=DEFAULT_ANSWER_KEY)
    ap.add_argument("--selfcheck", metavar="E7EV")
    ap.add_argument("--expected", default=DEFAULT_EXPECTED)
    a = ap.parse_args(argv)
    if a.selfcheck:
        return run_selfcheck("score_memos", a.selfcheck, a.out, a.expected, lambda sd: score_stream(sd, a.answer_key), "score_memos", render_txt)
    if not a.streamdir:
        ap.error("streamdir is required (or --selfcheck E7EV)")
    d = score_stream(a.streamdir, a.answer_key)
    write_outputs(a.out, "score_memos", d, render_txt(d))
    return 0


if __name__ == "__main__":
    sys.exit(main())
