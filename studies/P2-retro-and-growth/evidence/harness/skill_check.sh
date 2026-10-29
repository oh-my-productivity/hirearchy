#!/bin/zsh
# P2 skill check, per arm (protocol 1, 8 H2). Usage: skill_check.sh <label> setup|turn1|end
# Writes (rewrites) <label>/skill-check.txt and prints it. Exit 0: the rule holds; 1: the stream is invalid (H2); 2: usage / missing input.
#   setup  the md5 of the arm's repo SKILL.md, the sandbox's workspace copy and the owner's global copy (md5 -q only). The rule: the arm's repo
#          file has its pinned md5 (R 443e1bc4..., C b1023863...); the workspace copy equals it; the global copy is in place with 443e1bc4...
#          in arm R, and ABSENT (moved aside by skill_move.sh) in arm C.
#   turn1  the setup rule, then P1's skill_check.py (the first disclose_context: its uri, the md5 of the file at that path, which must be the
#          arm's) and skill_proof.py (the loaded TEXT is the arm's SKILL.md body, not the other's; the distinctive lines).
#   end    as turn1, over the whole session (after the last turn; the global copy still aside in arm C, restored after).
LABEL="$1"; MODE="$2"
H0=${0:A:h}
source $H0/arm.sh "$LABEL" || exit 2
[[ ( "$MODE" == setup || "$MODE" == turn1 || "$MODE" == end ) && $# -eq 2 ]] || { echo "usage: skill_check.sh <label> setup|turn1|end" >&2; exit 2; }
STREAM=$EV/$LABEL; [[ "$LABEL" == probe-* ]] && STREAM=$EV/probe/$LABEL; [[ "$LABEL" == selfcheck-* && -n "$P2_EVDIR" ]] && STREAM=$P2_EVDIR
[[ -f "$STREAM/sandbox-path.txt" ]] || { echo "skill_check.sh: $STREAM/sandbox-path.txt is missing" >&2; exit 2; }
S=$(cat "$STREAM/sandbox-path.txt")
REPO_SKILL=$REPO_A/skills/hirearchy/SKILL.md; WS_SKILL=$S/.kiro/skills/hirearchy/SKILL.md; GLOBAL_SKILL=$HOME/.kiro/skills/hirearchy/SKILL.md
md5_of() { [[ -f "$1" ]] && md5 -q "$1" || echo ""; }
repo_md5=$(md5_of $REPO_SKILL); ws_md5=$(md5_of $WS_SKILL); global_md5=$(md5_of $GLOBAL_SKILL)
reasons=()
[[ "$repo_md5" == "$SKILL_A" ]] || reasons+=("the arm's repo SKILL.md md5 is '${repo_md5:-absent}', not $SKILL_A")
[[ -n "$ws_md5" && "$ws_md5" == "$repo_md5" ]] || reasons+=("the workspace copy md5 is '${ws_md5:-absent}', not the arm's")
if [[ $ARM == R ]]; then
  [[ "$global_md5" == "$SKILL_R_MD5" ]] || reasons+=("arm R: the global copy is '${global_md5:-absent}', not in place with $SKILL_R_MD5")
else
  [[ -z "$global_md5" && ! -e $HOME/.kiro/skills/hirearchy ]] || reasons+=("arm C: the global copy is present ('$global_md5'): it must be aside (skill_move.sh)")
fi
REPORT=""
if [[ "$MODE" != setup ]]; then
  [[ -f "$STREAM/assistant-session-messages.jsonl" ]] || { echo "skill_check.sh: the session copy is missing" >&2; exit 2; }
  REPORT=$(python3 -B $H0/skill_check.py "$STREAM" --required-md5 "$SKILL_A" --json-out "$STREAM/skill-check.json"); rc=$?
  (( rc == 2 )) && { echo "skill_check.sh: skill_check.py failed" >&2; exit 2; }
  (( rc == 1 )) && reasons+=("the SKILL.md file at the disclosed uri does not have the arm's md5")
  PROOF=$(python3 -B $H0/skill_proof.py "$STREAM/assistant-session-messages.jsonl" --arm $ARM --out "$STREAM/skill-proof.json"); prc=$?
  REPORT="$REPORT
$PROOF"
  (( prc != 0 )) && reasons+=("$PROOF")
fi
{
  echo "# $LABEL skill check (protocol 1, 8 H2) mode $MODE at $(date -u +%FT%TZ)"
  echo "arm: $ARM (product $REPO_A)"
  echo "repo skill:     ${repo_md5:-absent} ($REPO_SKILL)"
  echo "workspace copy: ${ws_md5:-absent} ($WS_SKILL)"
  echo "global (md5 only): ${global_md5:-absent}"
  echo "required: $SKILL_A; global rule: $( [[ $ARM == R ]] && echo "in place with $SKILL_R_MD5" || echo "aside (absent)")"
  [[ -n "$REPORT" ]] && { echo; print -r -- "$REPORT"; }
  echo
  if (( ${#reasons} == 0 )); then echo "verdict: OK"; else echo "verdict: INVALID (H2): ${(j:; :)reasons}"; fi
} > "$STREAM/skill-check.txt"
cat "$STREAM/skill-check.txt"
(( ${#reasons} == 0 )) && exit 0
exit 1
