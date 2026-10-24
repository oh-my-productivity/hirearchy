#!/usr/bin/env python3
"""s2 facilitator helper: writes s2/skill-check.txt (protocol 4.4, 4.4.1). Read-only on the session copy. Usage: skill_check.py"""
import hashlib, json, os, re, subprocess
EV = "/Volumes/workspace/hirearchy/studies/E5-org-growth-0a2-recheck/evidence/s2"
S = open(EV + "/sandbox-path.txt").read().strip()
REQ = "b7187d6ef749505893e9aef99276ef7c"


def md5(p):
    return hashlib.md5(open(p, "rb").read()).hexdigest()


def lines(p):
    return len(open(p, "rb").read().splitlines())


repo = "/Volumes/workspace/hirearchy/skills/hirearchy/SKILL.md"
ws = S + "/.kiro/skills/hirearchy/SKILL.md"
gl = "/Users/aminalizadeh/.kiro/skills/hirearchy/SKILL.md"
out = ["# s2 skill check (protocol 4.4)",
       f"{repo}: {lines(repo)} lines md5 {md5(repo)}",
       f"{ws}: md5 {md5(ws)}, {lines(ws)} lines",
       f"{gl}: md5 {md5(gl)}, {lines(gl)} lines (read-only check)",
       f"required: {REQ}"]
calls = []  # (ts, turn, tool, args, status, disclosed, errorish)
cur_turn = 0
turn_of = {}
rows = []
for line in open(EV + "/assistant-session-messages.jsonl"):
    d = json.loads(line)
    rows.append(d)
# reuse the transcript text for call numbers, turns and timestamps
txt = open(EV + "/assistant-tool-calls.txt").read()
pat = re.compile(r"^\[(\S+)\] CALL #(\d+) turn=(\d+) (\S+) \(toolId=[^)]*\) status=(\S+)(.*)$", re.M)
allc = [(m.group(1), int(m.group(2)), int(m.group(3)), m.group(4), m.group(5), m.group(6)) for m in pat.finditer(txt)]
first_skill = None
for ts, n, t, tool, st, rest in allc:
    if tool == "disclose_context" and ("hirearchy" in rest) and st not in ("failed", "error"):
        first_skill = (ts, n, t, rest)
        break
first_prop = next(((ts, n, t) for ts, n, t, tool, st, rest in allc if '"tool_id": "hirearchy::propose_org"' in rest), None)
first_fb = next(((ts, n, t) for ts, n, t, tool, st, rest in allc if '"tool_id": "hirearchy::feedback"' in rest), None)
if first_skill:
    ts, n, t, rest = first_skill
    uri = re.search(r'"uri": "([^"]+)"', rest)
    uri = uri.group(1) if uri else "(not shown)"
    path = uri.replace("file://", "").replace("/private/tmp/", "/tmp/", 1)
    pm = md5(path) if os.path.exists(path) else "(path not readable)"
    ok = "valid" if pm == REQ else "INVALID (H2)"
    which = "the workspace copy" if path.startswith(S) else ("the repo copy" if path == repo else "other")
    out.append(f"first disclose_context(hirearchy): call #{n}, turn {t}, {ts}; disclosed uri {uri} ({which}); result completed (not an error); md5 of the SKILL.md at that path: {pm} -> {ok}.")
else:
    out.append("first disclose_context(hirearchy): none so far")
stratum = "n/a"
if first_prop is None and first_fb is None:
    stratum = "n/a (no propose_org and no feedback call so far)"
elif first_skill is None:
    stratum = "N (never activated)"
else:
    later = [x for x in (first_prop, first_fb) if x]
    before_all = all(first_skill[0] < x[0] for x in later)
    stratum = "A" if before_all else "B"
    out.append("skill-activation stratum (4.4.1): %s. First hirearchy::propose_org call %s and first hirearchy::feedback call %s; activation at %s (turn %s)." % (
        stratum, f"#{first_prop[1]} (turn {first_prop[2]}, {first_prop[0]})" if first_prop else "none",
        f"#{first_fb[1]} (turn {first_fb[2]}, {first_fb[0]})" if first_fb else "none", first_skill[0], first_skill[2]))
if first_prop is None and first_fb is None:
    out.append("skill-activation stratum (4.4.1): " + stratum)
n_note = len(re.findall(r"Note: the installed skill at", txt))
out.append(f"'Note: the installed skill at' occurrences in the whole transcript: {n_note} (assistant-tool-calls.txt: {n_note})")
out.append("stale-skill case: not exercised (would require changing the global skill, which is forbidden).")
open(EV + "/skill-check.txt", "w").write("\n".join(out) + "\n")
print("\n".join(out))
