#!/bin/zsh
# E7 model and effort check (protocol 4.3, 11 H4). Read-only: it lists, reads and greps; it writes only model-checks.txt.
# The set is one seat value: claude-sonnet-5.5 at effort high, for the assistant and for every org agent (D-E4-8, D-E4-9).
# Usage:
#   model_check.sh listed    <N>       "kiro-cli chat --list-models" lists claude-sonnet-5.5 (stream start; there is no substitution)
#   model_check.sh org       <N> <S>   every org run log under S/org has one "# cmd:" line with exactly one "--model claude-sonnet-5.5"
#                                      and exactly one "--effort high"
#   model_check.sh assistant <N> <S>   the stream's profile has "model": "claude-sonnet-5.5"; every turn-NN.cmd.txt has "--effort high"
#                                      once, the stream's --agent, and no --model other than claude-sonnet-5.5; the session copy
#                                      s<N>/assistant-session.json has modelId claude-sonnet-5.5 and effortLevel high (or none recorded);
#                                      every reasoningModelId in s<N>/assistant-session-messages.jsonl is [qdev::]claude-sonnet-5.5
#   model_check.sh all       <N> <S>   org, then assistant
# <N> is the stream label (1, 2, 3, 1r, ...), or "preflight" for the preflight's scratch org (protocol 4.14; output in
# evidence/preflight/). Appends a block to evidence/s<N>/model-checks.txt and prints its RESULT line.
# Exit 0: every seat checked is in the set (or, for listed, the model is listed). Exit 1: a seat outside the set (stream-invalidating,
# H4), or claude-sonnet-5.5 not listed (the stream does not start). Exit 2: usage error, or nothing to check yet (never a pass).
MODE="$1"; N="$2"; S="$3"
[[ -n "$MODE" && -n "$N" ]] || { echo "usage: model_check.sh listed|org|assistant|all <N> [<S>]" >&2; exit 2; }
[[ "$MODE" == listed || -n "$S" ]] || { echo "usage: model_check.sh $MODE <N> <S>" >&2; exit 2; }
EV=/Volumes/workspace/hirearchy/studies/E7-org-growth-0a4-recheck/evidence/s$N
[[ "$N" == preflight ]] && EV=/Volumes/workspace/hirearchy/studies/E7-org-growth-0a4-recheck/evidence/preflight
mkdir -p "$EV"
OUT="$EV/model-checks.txt"
LISTING=""
if [[ "$MODE" == listed ]]; then
  LISTING="$(kiro-cli chat --list-models 2>&1)"; LRC=$?
  LISTING="exit $LRC
$LISTING"
fi
python3 - "$MODE" "$N" "$S" "$EV" "$LISTING" >> "$OUT" <<'EOF'
import glob, json, os, re, shlex, sys
from datetime import datetime, timezone

mode, n, S, ev, listing = sys.argv[1:6]
MODEL, EFFORT = "claude-sonnet-5.5", "high"


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def flag(tokens, name):
    return [tokens[i + 1] for i, t in enumerate(tokens[:-1]) if t == name]


print(f"## model check {mode} s{n} at {now()} (set: {MODEL} at effort {EFFORT})")
bad, nothing = [], []


def listed():
    lines = listing.splitlines()
    print("kiro-cli chat --list-models:", lines[0] if lines else "(no output)")
    print("\n".join("  " + ln for ln in lines[1:]))
    rows = [ln for ln in lines[1:] if re.search(rf"(^|[\s*]){re.escape(MODEL)}\s", ln + " ")]
    if rows:
        print(f"listed: {MODEL}: yes ({rows[0].strip()})")
    else:
        bad.append(f"{MODEL} is not listed")


def org():
    logs = [p for p in sorted(glob.glob(os.path.join(S, "org", "**", "runs", "*.log"), recursive=True)) if "/.git/" not in p]
    if not logs:
        nothing.append("no org run log yet")
    for p in logs:
        rel = os.path.relpath(p, os.path.join(S, "org"))
        txt = open(p, errors="replace").read()
        cmds = re.findall(r"^# cmd: (.*)$", txt, re.M)
        if not cmds:
            first = next((ln for ln in txt.splitlines() if ln.startswith("# ")), "(empty)")
            print(f"  {rel}: no '# cmd:' line, so no model ran ({first[:160]})")
            continue
        tokens = cmds[0].split()
        models, efforts = flag(tokens, "--model"), flag(tokens, "--effort")
        ok = len(cmds) == 1 and models == [MODEL] and efforts == [EFFORT]
        print(f"  {rel}: --model {models or '(none)'} --effort {efforts or '(none)'}{'' if ok else '   <-- OUTSIDE THE SET'}")
        if not ok:
            bad.append(f"org run {rel}: --model {models} --effort {efforts} ({len(cmds)} '# cmd:' line(s))")
    print(f"org run logs checked: {len(logs)}")


def assistant():
    name = f"hirearchy-study-e7-s{n}-assistant"
    prof = [p for p in (os.path.expanduser(f"~/.kiro/agents/{name}.json"), os.path.join(ev, "profiles", f"{name}.json")) if os.path.isfile(p)]
    if prof:
        m = json.load(open(prof[0])).get("model")
        print(f"  profile {prof[0]}: model {m!r}")
        if m != MODEL:
            bad.append(f"assistant profile model {m!r}")
    else:
        nothing.append(f"profile {name}.json not found in ~/.kiro/agents or s{n}/profiles")
    cmds = sorted(glob.glob(os.path.join(ev, "turn-*.cmd.txt")))
    if not cmds:
        nothing.append("no turn-NN.cmd.txt yet")
    for p in cmds:
        tokens = shlex.split(open(p).read())[:-1]  # the last argument is Lena's line
        efforts, models, agents = flag(tokens, "--effort"), flag(tokens, "--model"), flag(tokens, "--agent")
        ok = efforts == [EFFORT] and models in ([], [MODEL]) and agents == [name]
        print(f"  {os.path.basename(p)}: --effort {efforts} --model {models or '(the profile)'} --agent {agents}{'' if ok else '   <-- OUTSIDE THE SET'}")
        if not ok:
            bad.append(f"assistant invocation {os.path.basename(p)}: --effort {efforts} --model {models} --agent {agents}")
    sj = os.path.join(ev, "assistant-session.json")
    if os.path.isfile(sj):
        j = json.load(open(sj))
        mid, eff = j.get("modelId"), j.get("effortLevel")
        print(f"  session {j.get('id')}: modelId {mid!r} effortLevel {eff!r}{'' if eff else ' (not recorded by the session file)'}")
        if mid != MODEL:
            bad.append(f"assistant session modelId {mid!r}")
        if eff not in (None, "", EFFORT):
            bad.append(f"assistant session effortLevel {eff!r}")
    else:
        nothing.append(f"no session copy s{n}/assistant-session.json yet")
    mj = os.path.join(ev, "assistant-session-messages.jsonl")
    if os.path.isfile(mj):
        vals = {}
        for line in open(mj):
            for v in re.findall(r'"reasoningModelId"\s*:\s*"([^"]*)"', line.replace('\\"', '"')):
                vals[v] = vals.get(v, 0) + 1
        print(f"  reasoningModelId values in the session messages: {vals or '(none)'}")
        if not vals:
            nothing.append("no reasoningModelId in the session messages yet")
        for v, k in vals.items():
            if v.split("::")[-1] != MODEL:
                bad.append(f"assistant reasoningModelId {v!r} (x{k})")
    else:
        nothing.append(f"no session copy s{n}/assistant-session-messages.jsonl yet")


steps = {"listed": [listed], "org": [org], "assistant": [assistant], "all": [org, assistant]}
if mode not in steps:
    bad.append(f"unknown mode {mode!r}")
else:
    for step in steps[mode]:
        step()
for b in bad:
    print(f"OUTSIDE THE SET: {b}" if mode != "listed" else f"NOT LISTED: {b}")
for x in nothing:
    print(f"NOT CHECKED: {x}")
if bad:
    res = "NOT LISTED: the stream does not start (no substitution)" if mode == "listed" else "INVALIDATING (H4: a seat outside the set)"
elif nothing:
    res = "INCOMPLETE (nothing to check yet; not a pass)"
else:
    res = "OK"
print(f"RESULT: s{n} {mode}: {res} ({now()})")
sys.exit(1 if bad else (2 if nothing else 0))
EOF
rc=$?
tail -1 "$OUT"
exit $rc
