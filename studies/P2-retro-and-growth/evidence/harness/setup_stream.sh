#!/bin/zsh
# P2 stream setup (P1's setup_stream.sh with the arm parameter and the skill move; protocol 3.1). Usage: setup_stream.sh <label> [--dry-run]
#   <label>  R1 C1 R2 C2 R3 C3 (a replacement, only after the manager's recorded approval: R1r ...)
# Gates, before anything is created (a failure prints "GATE FAILED: ..." and exits 3): 1. the md5 gate (protocol 0); 2. both freezes
# (protocol 2.2); 3. (not in --dry-run) claude-sonnet-5.5 listed; 4. KIRO_HOME unset; 5. the skill rule: both products' SKILL.md have their
# pinned md5s and the global copy is in place with 443e1bc4...; 6. no unrestored skill move. Then the memories gate (exit 4 on a change,
# unless EV/manager-decision-memories-before-<label>.md exists). Then: the stream folder, safety-before.txt, memories-md5-before.txt; ARM C:
# skill_move.sh aside <label> (a trap restores it if a later step of this script fails); the sandbox S=/tmp/hirearchy-p2/<label>-<epoch>
# (S/notes = EV/notes/*.md; S/.kiro/skills/hirearchy/SKILL.md = the ARM's SKILL.md; S/.kiro/settings/cli.json = H/workspace-cli.json;
# S/deliverables/; S/org not created); the profile from profile-template.json (<LABEL>, <epoch>, <PRODUCT> = the arm's product directory);
# setup.txt (both freezes, the skill md5s, the profile's raw and masked diffs against the study's first profile); skill_check.sh setup.
# --dry-run prints the plan and the gate results and creates nothing (it never moves the skill).
# Exit: 0 ok; 2 usage; 3 gate failed; 4 refused or a creation step failed (the skill restored); 5 the skill check says invalid (H2).
LABEL="$1"; DRY=0; [[ "$2" == "--dry-run" ]] && DRY=1
H0=${0:A:h}
source $H0/arm.sh "$LABEL" || exit 2
[[ "$LABEL" =~ $STREAM_RE && ( $# -eq 1 || $DRY -eq 1 ) ]] || { echo "usage: setup_stream.sh <R1..C3[r]> [--dry-run]" >&2; exit 2; }
STREAM=$EV/$LABEL
fails=()
gate() { if [[ "$2" == 1 ]]; then echo "gate: $1: OK${3:+ ($3)}"; else echo "gate: $1: FAILED${3:+ ($3)}"; fails+=("$1: $3"); fi; }
MG=$(md5gate_ok 2>&1); [[ $? -eq 0 ]] && gate "md5 gate (protocol 0)" 1 || gate "md5 gate (protocol 0)" 0 "$(print -r -- $MG | tr '\n' ';')"
freeze_ok && gate "both freezes (protocol 2.2)" 1 "R $SHA_R, C $SHA_C clean" || gate "both freezes (protocol 2.2)" 0 "$(freeze_lines | tr '\n' ';')"
[[ -z "${KIRO_HOME+set}" ]] && gate "KIRO_HOME unset" 1 || gate "KIRO_HOME unset" 0 "set: unset it (protocol 1)"
[[ "$(md5 -q $REPO_R/skills/hirearchy/SKILL.md)" == $SKILL_R_MD5 && "$(md5 -q $REPO_C/skills/hirearchy/SKILL.md)" == $SKILL_C_MD5 ]] && gate "product skills" 1 || gate "product skills" 0 "a product SKILL.md md5 differs"
ST=$(zsh $H0/skill_move.sh status); SRC=$?
[[ "$ST" == *"in place, md5 $SKILL_R_MD5"* ]] && gate "global skill in place" 1 || gate "global skill in place" 0 "$(print -r -- $ST | head -1)"
(( SRC == 0 )) && gate "no unrestored skill move" 1 || gate "no unrestored skill move" 0 "$(print -r -- $ST | tr '\n' ' ')"
if (( DRY == 0 )); then
  kiro-cli chat --list-models 2>&1 | grep -Eq '(^|[[:space:]*])claude-sonnet-5\.5[[:space:]]' && gate "claude-sonnet-5.5 listed" 1 || gate "claude-sonnet-5.5 listed" 0 "not listed"
else echo "gate: claude-sonnet-5.5 listed: (not checked in --dry-run)"; fi
[[ -e $STREAM/sandbox-path.txt ]] && { echo "REFUSED: $STREAM was set up already" >&2; exit 4; }
[[ -e $HOME/.kiro/agents/$PNAME.json ]] && { echo "REFUSED: $HOME/.kiro/agents/$PNAME.json exists" >&2; exit 4; }
if [[ "$LABEL" == *r ]]; then
  [[ -e $EV/manager-decision-replacement-${LABEL%r}.md ]] || { echo "REFUSED: $LABEL needs $EV/manager-decision-replacement-${LABEL%r}.md (protocol 8)" >&2; exit 4; }
  other=($EV/${ARM}[1-3]r(N/)); other=(${other:#$STREAM}); (( ${#other} )) && { echo "REFUSED: arm $ARM has a replacement already" >&2; exit 4; }
fi
if (( ${#fails} )); then for f in $fails; do echo "GATE FAILED: $f"; done; (( DRY == 0 )) && exit 3; fi
MDB=$HOME/.kiro/memories/memories.db; MDB_NOW=$( [[ -f $MDB ]] && md5 -q $MDB || echo absent )
MGATE=$(python3 -B $H0/memories_gate.py --ev $EV --label $LABEL --current "$MDB_NOW"); MGRC=$?; echo "$MGATE"
(( MGRC != 0 && DRY == 0 )) && exit 4
EPOCH=$(date +%s); S=$P/$LABEL-$EPOCH
if (( DRY == 1 )); then
  echo "DRY-RUN setup_stream.sh $LABEL: arm $ARM, product $REPO_A, S=$S, profile $PNAME; arm C would move the global skill aside first"
  exit 0
fi
mkdir -p $STREAM/ambient $STREAM/profiles $P || { echo "FAILED: cannot create $STREAM" >&2; exit 4; }
echo $EPOCH > $STREAM/epoch.txt; echo $S > $STREAM/sandbox-path.txt; echo $ARM > $STREAM/arm.txt; echo $REPO_A > $STREAM/product.txt
date -u +%FT%TZ > $STREAM/stream-start-utc.txt
zsh $H0/safety-snapshot.sh "$LABEL before" > $STREAM/safety-before.txt 2>&1
echo $MDB_NOW > $STREAM/memories-md5-before.txt; echo "before $LABEL ($(date -u +%FT%TZ)): $MGATE" >> $STREAM/memories-db.txt
MOVED=0; MADE=0
cleanup() {
  if (( MADE )) && [[ -f $HOME/.kiro/agents/$PNAME.json ]]; then
    rm -f $HOME/.kiro/agents/$PNAME.json && echo "profile deleted $(date -u +%FT%TZ) by the failed setup's cleanup: $HOME/.kiro/agents/$PNAME.json" >> $STREAM/profiles/deletions.txt
  fi
  (( MOVED )) && zsh $H0/skill_move.sh restore $LABEL; }
fail() { echo "FAILED: $1" >&2; cleanup; exit 4; }
if [[ $ARM == C ]]; then
  zsh $H0/skill_move.sh aside $LABEL > $STREAM/skill-aside.txt 2>&1 || { cat $STREAM/skill-aside.txt; exit 4; }
  MOVED=1; cat $STREAM/skill-aside.txt
fi
# C4 (F41 of review 3): a trapped INT or TERM runs the cleanup and then stops the setup (exit 4, as a failed setup)
trap 'cleanup; exit 4' INT TERM
zsh $H0/ambient_snapshot.sh "$LABEL setup" > $STREAM/ambient/setup.txt 2>&1
mkdir -p $S/notes $S/.kiro/skills/hirearchy $S/.kiro/settings $S/deliverables || fail "the sandbox"
cp -p $EV/notes/*.md $S/notes/ || fail "notes"
cp -p $REPO_A/skills/hirearchy/SKILL.md $S/.kiro/skills/hirearchy/SKILL.md || fail "skill copy"
cp -p $H0/workspace-cli.json $S/.kiro/settings/cli.json || fail "workspace settings"
MADE=1; sed -e "s/<LABEL>/$LABEL/g" -e "s/<epoch>/$EPOCH/g" -e "s#<PRODUCT>#$REPO_A#g" $H0/profile-template.json > $HOME/.kiro/agents/$PNAME.json || fail "profile"
MADE=1; PMD5=$(md5 -q $HOME/.kiro/agents/$PNAME.json); cp -p $HOME/.kiro/agents/$PNAME.json $STREAM/profiles/
echo "profile created $(date -u +%FT%TZ): $HOME/.kiro/agents/$PNAME.json md5 $PMD5" >> $STREAM/profiles/creations.txt
kiro-cli agent validate --path $HOME/.kiro/agents/$PNAME.json > $STREAM/profiles/validate.txt 2>&1; VRC=$?
REF=""; for l in $ORDER; do [[ $l == $LABEL ]] && break; f=$EV/$l/profiles/hirearchy-study-p2-$l-assistant.json; [[ -f $f && -z "$REF" ]] && REF=$f; done
{
  echo "# P2 $LABEL setup (recorded before turn 1) $(date -u +%FT%TZ)"
  echo "arm: $ARM; product: $REPO_A ($SHA_A); skill required $SKILL_A"
  echo "kiro home: the owner's ~/.kiro (env -u KIRO_HOME in every chat and product call); KIRO_HOME set here? $( [[ -n "${KIRO_HOME+set}" ]] && echo yes || echo no)"
  echo "memories.db md5 before: $MDB_NOW"
  freeze_lines
  echo "== md5 gate"; print -r -- "$MG"
  echo "== the global skill: $(zsh $H0/skill_move.sh status | head -1)"; [[ $ARM == C ]] && cat $STREAM/skill-aside.txt
  echo "== skills: REPO_R $(md5 -q $REPO_R/skills/hirearchy/SKILL.md), REPO_C $(md5 -q $REPO_C/skills/hirearchy/SKILL.md), workspace copy $(md5 -q $S/.kiro/skills/hirearchy/SKILL.md)"
  echo "== workspace settings $(md5 -q $S/.kiro/settings/cli.json)"; echo "== notes"; md5 $S/notes/*
  echo "== profile $PNAME md5 $PMD5; validate exit $VRC"
  if [[ -n "$REF" ]]; then
    RL=${${REF:t}#hirearchy-study-p2-}; RL=${RL%-assistant.json}; RE=$(cat ${REF:h:h}/epoch.txt); RP=$(cat ${REF:h:h}/product.txt)
    echo "(raw diff against the study's first profile $REF)"; diff $REF $HOME/.kiro/agents/$PNAME.json; echo "(diff exit $?)"
    echo "(masked diff: label, epoch and product path masked in both; empty = byte-identical but for them, protocol 1)"
    diff <(sed -e "s/$RL/<LABEL>/g" -e "s/$RE/<epoch>/g" -e "s#$RP#<PRODUCT>#g" $REF) <(sed -e "s/$LABEL/<LABEL>/g" -e "s/$EPOCH/<epoch>/g" -e "s#$REPO_A#<PRODUCT>#g" $HOME/.kiro/agents/$PNAME.json); echo "(masked diff exit $?)"
  else echo "(the first stream: no reference profile)"; fi
  echo "== org dir before turn 1? $( [[ -e $S/org ]] && echo YES || echo no)"
  echo "== ~/.kiro/agents"; ls $HOME/.kiro/agents
} > $STREAM/setup.txt 2>&1
trap - INT TERM
zsh $H0/skill_check.sh $LABEL setup > /dev/null 2>&1 || { echo "SKILL CHECK: INVALID (H2): see $STREAM/skill-check.txt" >&2; cleanup; exit 5; }
echo "set up $LABEL: S=$S arm $ARM product $REPO_A profile $PNAME"
exit 0
