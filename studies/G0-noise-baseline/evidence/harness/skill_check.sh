#!/bin/zsh
# G0 skill check (design 20.1 "Identical skill bytes in both arms"; E7 protocol 4.4, 4.4.1). Usage: skill_check.sh <label> setup|turn1
# Writes (rewrites) $EV/<label>/skill-check.txt and prints it. Exit 0: the md5 rule holds; 1: the stream is invalid (H2); 2: usage / missing input.
#   setup  the md5 of the repo's SKILL.md, the sandbox's workspace copy, the owner's global copy (md5 -q only; "absent" if there is none) and,
#          for arm m0, the dedicated home's copy ("absent" if none). The rule: the repo file has the required md5; the workspace copy equals
#          it; the global copy equals the workspace copy or is absent; arm m0: the M0 copy exists exactly when the global copy exists, with
#          the same md5. Anything else: "verdict: INVALID (H2)".
#   turn1  the setup block, then skill_check.py's report (first disclose_context of the skill: call number, turn, UTC, uri, md5 of the
#          SKILL.md at that path, which must be the required md5; the stratum of E7 protocol 4.4.1; the "Note: the installed skill at" counts).
# The global file is never modified, moved or deleted, and no other file under ~/.kiro/skills is read.
REPO=/Volumes/workspace/hirearchy
ST=$REPO/studies/G0-noise-baseline
EV=$ST/evidence
H=$EV/harness
REQUIRED=a3e46347b70a7ece5f734f70198c607f   # skills/hirearchy/SKILL.md at 3c841bb9, 125 lines

LABEL="$1"; MODE="$2"
[[ "$LABEL" =~ '^(m0|m1)-s[1-9][0-9]*(r[0-9]*)?$' && ( "$MODE" == setup || "$MODE" == turn1 ) && $# -eq 2 ]] || { echo "usage: skill_check.sh <label> setup|turn1" >&2; exit 2; }
ARM=${LABEL%%-*}
STREAM=$EV/$LABEL
[[ -f "$STREAM/sandbox-path.txt" ]] || { echo "skill_check.sh: $STREAM/sandbox-path.txt is missing" >&2; exit 2; }
S=$(cat "$STREAM/sandbox-path.txt")
REPO_SKILL=$REPO/skills/hirearchy/SKILL.md
WS_SKILL=$S/.kiro/skills/hirearchy/SKILL.md
GLOBAL_SKILL=$HOME/.kiro/skills/hirearchy/SKILL.md
M0_SKILL=""
if [[ "$ARM" == m0 ]]; then
  [[ -f "$STREAM/m0-home-path.txt" ]] || { echo "skill_check.sh: $STREAM/m0-home-path.txt is missing" >&2; exit 2; }
  M0_SKILL=$(cat "$STREAM/m0-home-path.txt")/.kiro/skills/hirearchy/SKILL.md
fi

md5_of() { [[ -f "$1" ]] && md5 -q "$1" || echo ""; }
lines_of() { wc -l < "$1" | tr -d ' '; }
repo_md5=$(md5_of "$REPO_SKILL"); ws_md5=$(md5_of "$WS_SKILL"); global_md5=$(md5_of "$GLOBAL_SKILL")
m0_md5=""; [[ -n "$M0_SKILL" ]] && m0_md5=$(md5_of "$M0_SKILL")

reasons=()
[[ "$repo_md5" == "$REQUIRED" ]] || reasons+=("the repo SKILL.md md5 is '${repo_md5:-absent}', not the required $REQUIRED")
[[ -n "$ws_md5" && "$ws_md5" == "$repo_md5" ]] || reasons+=("the workspace copy md5 is '${ws_md5:-absent}', not the repo's")
if [[ -n "$global_md5" && "$global_md5" != "$ws_md5" ]]; then reasons+=("the global copy md5 $global_md5 differs from the workspace copy's"); fi
if [[ "$ARM" == m0 ]]; then
  if [[ -n "$global_md5" && -z "$m0_md5" ]]; then reasons+=("the global copy exists but M0's home has none")
  elif [[ -z "$global_md5" && -n "$m0_md5" ]]; then reasons+=("the global copy is absent but M0's home has one")
  elif [[ -n "$global_md5" && "$m0_md5" != "$global_md5" ]]; then reasons+=("M0's copy md5 $m0_md5 differs from the global copy's $global_md5"); fi
fi

TURN1_TEXT=""; TURN1_RC=0
if [[ "$MODE" == turn1 ]]; then
  [[ -f "$STREAM/assistant-session-messages.jsonl" ]] || { echo "skill_check.sh: $STREAM/assistant-session-messages.jsonl is missing (copy the session first)" >&2; exit 2; }
  TURN1_TEXT=$(python3 -B "$H/skill_check.py" "$STREAM" --required-md5 "$REQUIRED" --json-out "$STREAM/skill-check.json"); TURN1_RC=$?
  [[ $TURN1_RC -eq 2 ]] && { echo "skill_check.sh: skill_check.py failed" >&2; exit 2; }
  [[ $TURN1_RC -eq 1 ]] && reasons+=("the SKILL.md the assistant loaded does not have the required md5 (see below)")
fi

{
  echo "# $LABEL skill check (design 20.1; protocol 4.4) mode $MODE at $(date -u +%FT%TZ)"
  echo "arm: $ARM"
  echo "repo skill:      ${repo_md5:-absent}  lines $( [[ -f "$REPO_SKILL" ]] && lines_of "$REPO_SKILL" || echo 0)  ($REPO_SKILL)"
  echo "workspace copy:  ${ws_md5:-absent}  lines $( [[ -f "$WS_SKILL" ]] && lines_of "$WS_SKILL" || echo 0)  ($WS_SKILL)"
  echo "global (md5 only): ${global_md5:-absent}"
  if [[ "$ARM" == m0 ]]; then
    echo "M0 copy:         ${m0_md5:-absent}  lines $( [[ -f "$M0_SKILL" ]] && lines_of "$M0_SKILL" || echo 0)  ($M0_SKILL)"
  else
    echo "M0 copy:         n/a (arm m1)"
  fi
  echo "required: $REQUIRED"
  echo "rule: the workspace copy = the repo file = required; the global copy = the workspace copy or absent; arm m0: M0's copy exists exactly when the global copy exists, same md5"
  if [[ "$MODE" == turn1 ]]; then
    echo
    print -r -- "$TURN1_TEXT"
  fi
  echo
  if (( ${#reasons} == 0 )); then echo "verdict: OK"; else echo "verdict: INVALID (H2): ${(j:; :)reasons}"; fi
} > "$STREAM/skill-check.txt"
cat "$STREAM/skill-check.txt"
(( ${#reasons} == 0 )) && exit 0
exit 1
