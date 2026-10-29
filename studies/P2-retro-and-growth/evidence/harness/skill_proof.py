#!/usr/bin/env python3
"""P2 skill proof (the brief: "the probe must prove, in both arms, which SKILL.md the session loaded"; protocol 1, 8 H2, 8.3).

    python3 -B skill_proof.py <session messages.jsonl> --arm R|C [--out FILE]      exit 0 proved, 1 not proved (H2), 2 unreadable
    python3 -B skill_proof.py --selfcheck --out DIR                                    constructed sessions and P1's kept I2 session

Reads the session store (kiro's messages.jsonl). For every `disclose_context` tool call of the hirearchy skill (args.name == hirearchy, or a
disclosed uri ending /hirearchy/SKILL.md) it takes the text of its tool_result and of every `skill` record. The loaded text is kiro's header
line(s) ("Skill directory: ...") plus the SKILL.md body without its frontmatter (as P1's kept sessions show). The proof, per disclosed text:
  * the arm's SKILL.md body (after its `---` frontmatter, stripped) is an exact substring;
  * the other arm's body is not;
  * the distinctive lines: arm R holds line 113 `8. A retro: when a reply says one is due` and line 119's `Put the user's answers, verbatim,
    in \\`needs.elicitation\\``; arm C holds neither.
PROVED when the session has at least one disclosed hirearchy text and every one passes; NOT PROVED otherwise (with the reason). The md5 of
each disclosed text and of the body found in it is printed. Standard library only; reads the two products' SKILL.md files, never writes them.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

SKILLS = {"R": "/Volumes/workspace/hirearchy/skills/hirearchy/SKILL.md",
          "C": "/Volumes/workspace/hirearchy/.worktrees/p2-arm-c/skills/hirearchy/SKILL.md"}
MD5 = {"R": "443e1bc4911aa4d6aaa6457e78f673c1", "C": "b10238639f48ab351fa44a06aed03ffb"}
DISTINCT_R = ["8. A retro: when a reply says one is due", "Put the user's answers, verbatim, in `needs.elicitation`"]
P1_I2 = "/Volumes/workspace/hirearchy/studies/P1-itemized-playbook/evidence/I2/assistant-session-messages.jsonl"


def body(text: str) -> str:
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            text = text[end + 4:]
    return text.strip()


def payload(d: dict) -> dict:
    p = d.get("payload")
    return json.loads(p) if isinstance(p, str) else (p or {})


def texts(o):
    if isinstance(o, str):
        yield o
    elif isinstance(o, dict):
        for v in o.values():
            yield from texts(v)
    elif isinstance(o, list):
        for v in o:
            yield from texts(v)


def disclosed(path: Path) -> list[str]:
    calls, out = set(), []
    for line in path.read_text(errors="replace").splitlines():
        if not line.strip():
            continue
        p = payload(json.loads(line))
        t = p.get("type")
        if t == "tool_call" and p.get("toolName") == "disclose_context":
            uri = (((p.get("_meta") or {}).get("kiro") or {}).get("disclosedContext") or {}).get("uri") or ""
            if (p.get("args") or {}).get("name") == "hirearchy" or uri.endswith("/hirearchy/SKILL.md"):
                calls.add(p.get("toolCallId"))
        elif t == "tool_result" and p.get("toolCallId") in calls:
            out.append("\n".join(texts(p.get("content"))))
        elif t == "skill" and "hirearchy" in json.dumps(p)[:2000]:
            out.extend(x for x in texts(p) if len(x) > 1000)
    return out


def prove(session: Path, arm: str) -> dict:
    other = "C" if arm == "R" else "R"
    mine, theirs = body(Path(SKILLS[arm]).read_text()), body(Path(SKILLS[other]).read_text())
    files_ok = all(hashlib.md5(Path(SKILLS[a]).read_bytes()).hexdigest() == MD5[a] for a in "RC")
    found = disclosed(session)
    rows, reasons = [], []
    if not files_ok:
        reasons.append("a product's SKILL.md does not have its pinned md5")
    if not found:
        reasons.append("no disclosed hirearchy skill text in the session")
    for i, t in enumerate(found, 1):
        has_mine, has_theirs = mine in t, theirs in t
        lines = [d in t for d in DISTINCT_R]
        ok = has_mine and not has_theirs and (all(lines) if arm == "R" else not any(lines))
        rows.append({"n": i, "md5": hashlib.md5(t.encode()).hexdigest(), "arm_body": has_mine, "other_body": has_theirs,
                     "distinct_R_lines": lines, "ok": ok})
        if not ok:
            reasons.append(f"disclosed text {i} is not arm {arm}'s skill (arm body {has_mine}, other body {has_theirs}, R lines {lines})")
    return {"arm": arm, "session": str(session), "disclosed": len(found), "rows": rows,
            "verdict": "PROVED" if not reasons else "NOT PROVED", "reasons": reasons,
            "body_md5": {a: hashlib.md5(body(Path(SKILLS[a]).read_text()).encode()).hexdigest() for a in "RC"}}


def selfcheck(out: Path) -> int:
    out.mkdir(parents=True, exist_ok=True)
    checks = []
    def session_with(text: str) -> Path:
        p = out / f"constructed-{len(checks)}.jsonl"
        recs = [{"payload": {"type": "tool_call", "toolCallId": "t1", "toolName": "disclose_context", "args": {"name": "hirearchy"}}},
                {"payload": {"type": "tool_result", "toolCallId": "t1", "content": "Skill directory: /tmp/x/.kiro/skills/hirearchy\n\n" + text}}]
        p.write_text("\n".join(json.dumps(r) for r in recs) + "\n")
        return p
    rb, cb = body(Path(SKILLS["R"]).read_text()), body(Path(SKILLS["C"]).read_text())
    for name, text, arm, want in (("R text, arm R", rb, "R", "PROVED"), ("R text, arm C", rb, "C", "NOT PROVED"),
                                  ("C text, arm C", cb, "C", "PROVED"), ("C text, arm R", cb, "R", "NOT PROVED"),
                                  ("both texts, arm R", rb + "\n" + cb, "R", "NOT PROVED")):
        got = prove(session_with(text), arm)["verdict"]
        checks.append((name, want, got))
    empty = out / "constructed-empty.jsonl"
    empty.write_text(json.dumps({"payload": {"type": "user"}}) + "\n")
    checks.append(("no disclosure, arm C", "NOT PROVED", prove(empty, "C")["verdict"]))
    if Path(P1_I2).is_file():  # P1 ran on 8bf7c69b, whose SKILL.md is b1023863 = arm C's: the kept session must prove C and not R
        checks.append(("P1 I2's kept session, arm C", "PROVED", prove(Path(P1_I2), "C")["verdict"]))
        checks.append(("P1 I2's kept session, arm R", "NOT PROVED", prove(Path(P1_I2), "R")["verdict"]))
    lines = [f"{'ok' if w == g else 'MISMATCH'}  {n}: expected {w}, got {g}" for n, w, g in checks]
    bad = sum(1 for _, w, g in checks if w != g)
    lines.append(f"skill_proof selfcheck: {len(checks) - bad} of {len(checks)} ok")
    (out / "skill_proof.out").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("session", nargs="?")
    ap.add_argument("--arm", choices=["R", "C"])
    ap.add_argument("--out")
    ap.add_argument("--selfcheck", action="store_true")
    a = ap.parse_args()
    if a.selfcheck:
        return selfcheck(Path(a.out))
    if not a.session or not a.arm or not Path(a.session).is_file():
        print("usage: skill_proof.py <messages.jsonl> --arm R|C [--out FILE]", file=sys.stderr)
        return 2
    r = prove(Path(a.session), a.arm)
    text = json.dumps(r, indent=1)
    if a.out:
        Path(a.out).write_text(text + "\n")
    print(f"skill proof (arm {a.arm}): {r['verdict']}" + (f": {'; '.join(r['reasons'])}" if r["reasons"] else f" ({r['disclosed']} disclosed text(s))"))
    return 0 if r["verdict"] == "PROVED" else 1


if __name__ == "__main__":
    sys.exit(main())
