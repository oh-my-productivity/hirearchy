#!/bin/zsh
# P1 skill check (G0's, M1 only; design 18.2 "the same workspace skill copy (md5 checked)"; E7 protocol 4.4, 4.4.1). Usage: skill_check.sh <label> setup|turn1
# Writes (rewrites) $EV/<label>/skill-check.txt and prints it. Exit 0: the md5 rule holds; 1: the stream is invalid (H2); 2: usage / missing input.
#   setup  the md5 of the repo's SKILL.md, the sandbox's workspace copy, the owner's global copy (md5 -q only; "absent" if there is none) and,
#          (P1: both arms use the owner's kiro home, so there is no third copy). The rule: the repo file has the required md5; the workspace
#          copy equals it; the global copy equals the workspace copy or is absent; the same rule in both arms, with
#          the same md5. Anything else: "verdict: INVALID (H2)".
#   turn1  the setup block, then skill_check.py's report (first disclose_context of the skill: call number, turn, UTC, uri, md5 of the
#          SKILL.md at that path, which must be the required md5; the stratum of E7 protocol 4.4.1; the "Note: the installed skill at" counts).
# The global file is never modified, moved or deleted, and no other file under ~/.kiro/skills is read.
REPO=/Volumes/workspace/hirearchy
ST=$REPO/studies/P1-itemized-playbook
EV=$ST/evidence
H=$EV/harness
REQUIRED=b10238639f48ab351fa44a06aed03ffb   # skills/hirearchy/SKILL.md at 8bf7c69b, 125 lines

LABEL="$1"; MODE="$2"
[[ "$LABEL" =~ '^[FI][1-3](r[0-9]*)?$' && ( "$MODE" == setup || "$MODE" == turn1 ) && $# -eq 2 ]] || { echo "usage: skill_check.sh <label> setup|turn1" >&2; exit 2; }
ARM=${LABEL[1,1]}
STREAM=$EV/$LABEL
[[ -f "$STREAM/sandbox-path.txt" ]] || { echo "skill_check.sh: $STREAM/sandbox-path.txt is missing" >&2; exit 2; }
S=$(cat "$STREAM/sandbox-path.txt")
REPO_SKILL=$REPO/skills/hirearchy/SKILL.md
WS_SKILL=$S/.kiro/skills/hirearchy/SKILL.md
GLOBAL_SKILL=$HOME/.kiro/skills/hirearchy/SKILL.md

md5_of() { [[ -f "$1" ]] && md5 -q "$1" || echo ""; }
lines_of() { wc -l < "$1" | tr -d ' '; }
repo_md5=$(md5_of "$REPO_SKILL"); ws_md5=$(md5_of "$WS_SKILL"); global_md5=$(md5_of "$GLOBAL_SKILL")

reasons=()
[[ "$repo_md5" == "$REQUIRED" ]] || reasons+=("the repo SKILL.md md5 is '${repo_md5:-absent}', not the required $REQUIRED")
[[ -n "$ws_md5" && "$ws_md5" == "$repo_md5" ]] || reasons+=("the workspace copy md5 is '${ws_md5:-absent}', not the repo's")
if [[ -n "$global_md5" && "$global_md5" != "$ws_md5" ]]; then reasons+=("the global copy md5 $global_md5 differs from the workspace copy's"); fi

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
  echo "required: $REQUIRED"
  echo "rule: the workspace copy = the repo file = required; the global copy = the workspace copy or absent; the same in both arms (one kiro home)"
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
