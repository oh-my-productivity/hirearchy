#!/usr/bin/env python3
"""G0 skill-activation check (design 20.1; E7 protocol 4.4 and 4.4.1). Read-only, standard library only.

Usage:
  skill_check.py <streamdir> [--required-md5 MD5] [--json-out FILE] [--text-out FILE]
  skill_check.py --selfcheck <E7 evidence dir> --out <dir> [--expected FILE]

Reads <streamdir>/assistant-session-messages.jsonl (and <streamdir>/assistant-tool-calls.txt when present) and reports:
- the first `disclose_context` call for the hirearchy skill whose result is not an error: its call number (the order of the session's
  `tool_call` rows, the numbering of assistant-tool-calls.txt), user turn, UTC time, status, disclosed uri, and the md5 of the SKILL.md at
  that path (null when the file is absent), compared with --required-md5 when given (`valid`: true / false / null);
- the first `hirearchy::propose_org` and the first `hirearchy::feedback` call (through the `tool_call` executor's args.tool_id or as a tool
  of their own);
- the stratum of E7 protocol 4.4.1: A (activated before the first propose_org and before the first feedback), B (activated, but only after
  one of them), N (never activated), n/a (the session has neither a propose_org nor a feedback call; checked first);
- the number of disclose_context calls in the session, the number of them for the skill, and the occurrences of the text
  "Note: the installed skill at" in the two transcripts.
Exit code: 0; 1 when --required-md5 is given and the disclosed file's md5 is another (stream-invalidating, H2); 2 on an unreadable input.
The JSON follows the common conventions (sorted keys, indent 2, `source_files`, `script` = name + md5).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse

NOTE_TEXT = "Note: the installed skill at"
E7_REQUIRED_MD5 = "fd89a7fda55b8f342cf0306173c363fb"  # E7's skills/hirearchy/SKILL.md (E7 protocol 4.4); used only by --selfcheck
SCRIPT = Path(__file__).resolve()


def payload(d: dict) -> dict:
    p = d.get("payload")
    return json.loads(p) if isinstance(p, str) else (p or {})


def tool_names(p: dict) -> set[str]:
    names = {p.get("toolName") or ""}
    args = p.get("args")
    if isinstance(args, dict) and isinstance(args.get("tool_id"), str):
        names.add(args["tool_id"])
    kiro = (p.get("_meta") or {}).get("kiro") or {}
    if isinstance(kiro.get("toolId"), str):
        names.add(kiro["toolId"])
    return {n for n in names if n}


def is_hirearchy_tool(names: set[str], tool: str) -> bool:
    return any("hirearchy" in n and n.split("::")[-1].split("/")[-1] == tool for n in names)


def result_is_error(p: dict) -> bool:
    content = p.get("content")
    if not isinstance(content, str):
        content = json.dumps(content, ensure_ascii=False)
    status = str(p.get("status") or "").lower()
    return bool(p.get("isError")) or status in ("failed", "error") or content.startswith(("Error", 'Tool "', "MCP tool error"))


def md5_of(path: str) -> str | None:
    f = Path(path)
    return hashlib.md5(f.read_bytes()).hexdigest() if f.is_file() else None


def uri_to_path(uri: str) -> str | None:
    if not uri:
        return None
    u = urlparse(uri)
    if u.scheme not in ("", "file"):
        return None
    return unquote(u.path)


def analyse(streamdir: Path, required_md5: str | None = None) -> dict:
    msgs = streamdir / "assistant-session-messages.jsonl"
    sources = ["assistant-session-messages.jsonl"]
    calls: dict[str, dict] = {}
    order: list[dict] = []
    turn = 0
    n_calls = 0
    n_disclose_all = 0
    note_msgs = 0
    with open(msgs) as fh:
        for line in fh:
            if not line.strip():
                continue
            note_msgs += line.count(NOTE_TEXT)
            d = json.loads(line)
            p = payload(d)
            t = p.get("type")
            ts = d.get("timestamp", "")
            if t == "user":
                turn += 1
            elif t == "tool_call":
                n_calls += 1
                names = tool_names(p)
                kiro = (p.get("_meta") or {}).get("kiro") or {}
                uri = ((kiro.get("disclosedContext") or {}).get("uri")) or ""
                args = p.get("args") if isinstance(p.get("args"), dict) else {}
                rec = {"call": n_calls, "turn": turn, "utc": ts, "status": p.get("status"), "uri": uri,
                       "kind": None, "error": False, "id": p.get("toolCallId")}
                if p.get("toolName") == "disclose_context":
                    n_disclose_all += 1
                    if args.get("name") == "hirearchy" or uri.endswith("/hirearchy/SKILL.md"):
                        rec["kind"] = "skill"
                elif is_hirearchy_tool(names, "propose_org"):
                    rec["kind"] = "propose_org"
                elif is_hirearchy_tool(names, "feedback"):
                    rec["kind"] = "feedback"
                calls[p.get("toolCallId")] = rec
                order.append(rec)
            elif t == "tool_result":
                rec = calls.get(p.get("toolCallId"))
                if rec is not None and result_is_error(p):
                    rec["error"] = True
    note_tc = None
    tc = streamdir / "assistant-tool-calls.txt"
    if tc.is_file():
        note_tc = tc.read_text(errors="replace").count(NOTE_TEXT)
        sources.append("assistant-tool-calls.txt")
    skill_calls = [r for r in order if r["kind"] == "skill"]
    ok_skill = [r for r in skill_calls if not r["error"] and str(r["status"] or "").lower() not in ("failed", "error")]
    first_dis = ok_skill[0] if ok_skill else None
    first_prop = next((r for r in order if r["kind"] == "propose_org"), None)
    first_fb = next((r for r in order if r["kind"] == "feedback"), None)

    def brief(r: dict | None) -> dict | None:
        return None if r is None else {"call": r["call"], "turn": r["turn"], "utc": r["utc"]}

    dis_out = None
    if first_dis is not None:
        path = uri_to_path(first_dis["uri"])
        fm = md5_of(path) if path else None
        valid = None
        if required_md5 is not None and fm is not None:
            valid = fm == required_md5
        dis_out = {"call": first_dis["call"], "turn": first_dis["turn"], "utc": first_dis["utc"], "status": first_dis["status"],
                   "uri": first_dis["uri"], "path": path, "skill_file_md5": fm, "valid": valid}
    later = [r["call"] for r in (first_prop, first_fb) if r is not None]
    if not later:
        stratum = "n/a"
    elif first_dis is None:
        stratum = "N"
    elif first_dis["call"] < min(later):
        stratum = "A"
    else:
        stratum = "B"
    return {
        "script": {"name": SCRIPT.name, "md5": hashlib.md5(SCRIPT.read_bytes()).hexdigest()},
        "source_files": sources,
        "streamdir": str(streamdir),
        "required_md5": required_md5,
        "first_disclose": dis_out,
        "first_propose_org": brief(first_prop),
        "first_feedback": brief(first_fb),
        "stratum": stratum,
        "disclose_calls": n_disclose_all,
        "skill_disclose_calls": len(skill_calls),
        "note_count": {"messages": note_msgs, "tool_calls": note_tc},
    }


def render(j: dict) -> str:
    out = []
    d = j["first_disclose"]
    if d is None:
        out.append("first disclose_context call for the skill: none (the skill was never activated with a result that is not an error)")
    else:
        out.append(f"first disclose_context call for the skill: CALL #{d['call']}, turn {d['turn']}, {d['utc']}, status {d['status']} (not an error),")
        out.append(f"  disclosed uri: {d['uri']}")
        if d["skill_file_md5"] is None:
            out.append(f"  md5 of the SKILL.md at that path: (file absent at {d['path']}; not checkable)")
        elif d["valid"] is None:
            out.append(f"  md5 of the SKILL.md at that path: {d['skill_file_md5']} (no required md5 given)")
        else:
            out.append(f"  md5 of the SKILL.md at that path: {d['skill_file_md5']} (valid: {'= ' + j['required_md5'] if d['valid'] else 'NOT = ' + j['required_md5'] + ': INVALID (H2)'})")
    out.append("")

    def one(r: dict | None) -> str:
        return "none" if r is None else f"CALL #{r['call']}, turn {r['turn']}, {r['utc']}"

    out.append(f"skill-activation stratum (4.4.1): first propose_org call = {one(j['first_propose_org'])}; first feedback call = {one(j['first_feedback'])}.")
    if j["stratum"] == "A":
        out.append(f"  disclose_context (turn {d['turn']}, {d['utc'][11:19]}Z) is earlier than both -> stratum A (activated before the first propose_org and before the first feedback).")
    elif j["stratum"] == "B":
        out.append(f"  disclose_context (turn {d['turn']}, {d['utc'][11:19]}Z) came after one of them -> stratum B.")
    elif j["stratum"] == "N":
        out.append("  the skill was never activated -> stratum N.")
    else:
        out.append("  the session has neither a propose_org nor a feedback call -> stratum n/a.")
    out.append(f"stratum: {j['stratum']}")
    out.append("")
    nc = j["note_count"]
    tcs = "(file absent)" if nc["tool_calls"] is None else str(nc["tool_calls"])
    out.append(f"occurrences of '{NOTE_TEXT}' in the whole transcript: {nc['messages']} (assistant-session-messages.jsonl); {tcs} (assistant-tool-calls.txt)")
    out.append(f"disclose_context calls in the session: {j['disclose_calls']} ({j['skill_disclose_calls']} for the hirearchy skill)")
    return "\n".join(out) + "\n"


def get_path(j: dict, dotted: str):
    cur = j
    for k in dotted.split("."):
        if not isinstance(cur, dict) or k not in cur:
            return None
        cur = cur[k]
    return cur


def selfcheck(e7ev: Path, outdir: Path, expected_file: Path) -> int:
    exp = json.loads(expected_file.read_text())
    results: dict[str, dict] = {}
    for s in sorted({e["stream"] for e in exp}):
        j = analyse(e7ev / s, required_md5=E7_REQUIRED_MD5)  # shown in the report; not an expected value (the E7 sandboxes may be gone)
        d = outdir / f"e7-{s}"
        d.mkdir(parents=True, exist_ok=True)
        (d / "skill_check.json").write_text(json.dumps(j, sort_keys=True, indent=2) + "\n")
        (d / "skill_check.txt").write_text(render(j))
        results[s] = j
    ok = 0
    for e in exp:
        got = get_path(results[e["stream"]], e["key"])
        if got == e["expected"]:
            ok += 1
            print(f"OK {e['stream']} {e['key']} = {got!r}  [{e['source']}]")
        else:
            print(f"MISMATCH {e['stream']} {e['key']}: expected {e['expected']!r} ({e['source']}), got {got!r}")
    print(f"selfcheck skill_check: {ok} of {len(exp)} OK")
    return 0 if ok == len(exp) else 1


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("streamdir", nargs="?")
    ap.add_argument("--required-md5")
    ap.add_argument("--json-out")
    ap.add_argument("--text-out")
    ap.add_argument("--selfcheck", metavar="E7EV")
    ap.add_argument("--out")
    ap.add_argument("--expected")
    a = ap.parse_args(argv)
    try:
        if a.selfcheck:
            if not a.out:
                print("--selfcheck needs --out", file=sys.stderr)
                return 2
            exp = Path(a.expected) if a.expected else SCRIPT.parent / "selfcheck" / "e7-expected-drivers.json"
            return selfcheck(Path(a.selfcheck), Path(a.out), exp)
        if not a.streamdir:
            ap.error("streamdir is required")
        j = analyse(Path(a.streamdir), a.required_md5)
    except (OSError, ValueError) as e:  # unreadable input
        print(f"skill_check.py: {e}", file=sys.stderr)
        return 2
    text = render(j)
    sys.stdout.write(text)
    if a.json_out:
        Path(a.json_out).write_text(json.dumps(j, sort_keys=True, indent=2) + "\n")
    if a.text_out:
        Path(a.text_out).write_text(text)
    d = j["first_disclose"]
    return 1 if (d is not None and d["valid"] is False) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
