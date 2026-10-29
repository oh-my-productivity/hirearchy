#!/bin/zsh
# P2 arm parameter (protocol 1, 10): the ONE place that maps a label to its product. Sourced by every driver: `source $H/arm.sh <label>`.
#   label  R1 R2 R3 C1 C2 C3 (a replacement: R1r ...), probe-R<k> / probe-C<k>, selfcheck-R / selfcheck-C, preflight-R / preflight-C
# Sets: ARM (R|C), REPO_A (the arm's product directory), SHA_A (its pinned sha), SKILL_A (its SKILL.md md5), SKILL_OTHER (the other arm's),
# HIR (the arm's CLI argv, KIRO_HOME unset), EV, H, P (the study's sandbox root), REPO_R, REPO_C, the label patterns, PNAME (the profile).
# Exits (when sourced, returns) 2 on a label it does not know.
REPO_R=/Volumes/workspace/hirearchy
REPO_C=/Volumes/workspace/hirearchy/.worktrees/p2-arm-c
SHA_R=3d6b28aa17a70a3f95854c73c2f479b6361a71de
SHA_C=aac6af1b47b721515106f03f1dd6eb6758da6e55
SKILL_R_MD5=443e1bc4911aa4d6aaa6457e78f673c1
SKILL_C_MD5=b10238639f48ab351fa44a06aed03ffb
GLOBAL_SKILL_DIR=$HOME/.kiro/skills/hirearchy
ST=$REPO_R/studies/P2-retro-and-growth
EV=$ST/evidence
H=$EV/harness
P=/tmp/hirearchy-p2
STREAM_RE='^[RC][1-3](r)?$'
ORDER=(R1 C1 R2 C2 R3 C3)
_label="$1"
case "$_label" in
  R[1-3]|R[1-3]r|probe-R*|selfcheck-R*|preflight-R*) ARM=R ;;
  C[1-3]|C[1-3]r|probe-C*|selfcheck-C*|preflight-C*) ARM=C ;;
  *) echo "arm.sh: '$_label' is not a P2 label" >&2; return 2 2>/dev/null || exit 2 ;;
esac
if [[ $ARM == R ]]; then
  REPO_A=$REPO_R; SHA_A=$SHA_R; SKILL_A=$SKILL_R_MD5; SKILL_OTHER=$SKILL_C_MD5; REPO_OTHER=$REPO_C
else
  REPO_A=$REPO_C; SHA_A=$SHA_C; SKILL_A=$SKILL_C_MD5; SKILL_OTHER=$SKILL_R_MD5; REPO_OTHER=$REPO_R
fi
HIR=(env -u KIRO_HOME uv --directory $REPO_A run hirearchy)
PNAME=hirearchy-study-p2-$_label-assistant
# the two freezes (protocol 2.2), as one function every driver calls before and after a stream
freeze_lines() {
  echo "== freeze (protocol 2.2) at $(date -u +%FT%TZ)"
  echo "REPO_R HEAD: $(git -C $REPO_R rev-parse HEAD 2>&1) (required $SHA_R)"
  echo "REPO_R diff --stat $SHA_R HEAD -- src skills pyproject.toml uv.lock: [$(git -C $REPO_R diff --stat $SHA_R HEAD -- src skills pyproject.toml uv.lock 2>&1)]"
  echo "REPO_C HEAD: $(git -C $REPO_C rev-parse HEAD 2>&1) (required $SHA_C)"
  echo "REPO_C status --porcelain: [$(git -C $REPO_C status --porcelain 2>&1)]"
}
freeze_ok() {  # 0 when both freezes hold
  [[ "$(git -C $REPO_R rev-parse HEAD 2>/dev/null)" == $SHA_R ]] || return 1
  [[ -z "$(git -C $REPO_R diff --stat $SHA_R HEAD -- src skills pyproject.toml uv.lock 2>&1)" ]] || return 1
  [[ "$(git -C $REPO_C rev-parse HEAD 2>/dev/null)" == $SHA_C ]] || return 1
  [[ -z "$(git -C $REPO_C status --porcelain 2>&1)" ]] || return 1
  return 0
}
md5gate_ok() {  # 0 when protocol.md, the standing rules, every amendment of either and every MD5SUMS line match (protocol 0; D1 of the
  # manager's rulings on amendment 1's review): each EV/protocol-amendment-*.md and EV/standing-rules-streams-amendment-*.md must have its
  # .md5 beside it (<name>.md5), and a missing one fails; prints the failures
  local bad=0 f m
  if [[ -f $EV/protocol.md5 ]]; then
    [[ "$(md5 -q $EV/protocol.md)" == "$(awk '{print $1; exit}' $EV/protocol.md5)" ]] || { echo "md5 gate: protocol.md differs from protocol.md5"; bad=1; }
  else echo "md5 gate: protocol.md5 missing (not frozen)"; bad=1; fi
  if [[ -f $EV/standing-rules-streams.md5 ]]; then
    [[ "$(md5 -q $EV/standing-rules-streams.md)" == "$(awk '{print $1; exit}' $EV/standing-rules-streams.md5)" ]] || { echo "md5 gate: standing-rules-streams.md differs"; bad=1; }
  else echo "md5 gate: standing-rules-streams.md5 missing (not frozen)"; bad=1; fi
  for f in $EV/protocol-amendment-*.md(N) $EV/standing-rules-streams-amendment-*.md(N); do
    m=${f%.md}.md5
    if [[ -f $m ]]; then
      [[ "$(md5 -q $f)" == "$(awk '{print $1; exit}' $m)" ]] || { echo "md5 gate: ${f:t} differs from ${m:t}"; bad=1; }
    else echo "md5 gate: ${m:t} missing (${f:t} not frozen)"; bad=1; fi
  done
  if [[ -f $H/MD5SUMS ]]; then
    local n=0
    while read -r sum name; do [[ -z "$sum" ]] && continue; n=$((n+1)); [[ "$(md5 -q "$H/$name" 2>/dev/null)" == "$sum" ]] || { echo "md5 gate: MISMATCH $name"; bad=1; }; done < $H/MD5SUMS
    (( n > 0 )) || { echo "md5 gate: MD5SUMS empty"; bad=1; }
  else echo "md5 gate: harness/MD5SUMS missing (not frozen)"; bad=1; fi
  return $bad
}
