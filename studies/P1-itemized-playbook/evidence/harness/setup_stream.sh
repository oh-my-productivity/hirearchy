#!/bin/zsh
# P1 stream setup (G0's setup_stream.sh, M1 treatment only; protocol 7). Usage: setup_stream.sh <label> [--dry-run]
#   <label>  F1 F2 F3 I1 I2 I3 (a replacement, only after the manager's recorded approval: F1r ...); the arm is the first letter
# Gates, checked before anything is created (any failure prints "GATE FAILED: ..." and exits 3):
#   1. md5 -q of $EV/protocol.md equals $EV/protocol.md5;
#   2. every line of $H/MD5SUMS ("<md5>  <name>"): the md5 of $H/<name> equals it;
#   3. git HEAD of the repo is the full sha of 8bf7c69b;
#   4. `git diff --stat 8bf7c69b HEAD -- src skills pyproject.toml uv.lock` is empty;
#   5. (not in --dry-run) `kiro-cli chat --list-models` lists claude-sonnet-5.5 (no substitution; the stream does not start otherwise);
#   6. the skill rule of design 20.1: the repo SKILL.md has the required md5 and the owner's global copy equals it or is absent;
#   7. KIRO_HOME is not set in the facilitator's shell (protocol 1: unset in both arms; the injection script's scheduler and its org runs
#      inherit this shell, so it is gated here, not only removed by run_turn.sh's `env -u KIRO_HOME`).
# The memories gate (protocol 3 and 8; design 18.2), after the gates and refusals and before anything is created: memories_gate.py compares
# the md5 of ~/.kiro/memories/memories.db now with the previous stream's memories-md5-after.txt; a change prints its `STOP:` line and exits
# 4 (nothing is created) unless $EV/manager-decision-memories-before-<label>.md exists (the stream step sends a warning and waits).
# Then it creates: the stream folder $EV/<label>/ (sandbox-path.txt, epoch.txt, arm.txt, stream-start-utc.txt), safety-before.txt, the owner's
# memories.db md5 (memories-md5-before.txt: the value the memories gate checked; the gate's line in memories-db.txt), ambient/setup.txt, the sandbox S=/tmp/hirearchy-p1-<label>-
# <epoch> (S/notes = $EV/notes/*; S/.kiro/skills/hirearchy/SKILL.md = the repo copy; S/.kiro/settings/cli.json = $H/workspace-cli.json; S/org is NOT
# created), the stream's profile from profile-template.json (both arms: ~/.kiro/agents/; a copy in profiles/ and a line in
# profiles/creations.txt), model_check.sh listed, setup.txt and skill_check.sh <label> setup.
# --dry-run prints the plan (and the gate results, which it only reports) and creates and writes nothing. It never runs a turn, a chat, the
# hirearchy CLI, an MCP server or the scheduler.
# Exit: 0 ok; 2 usage / bad label; 3 gate failed; 4 refused (the stream folder or the profile exists already; memories.db changed since the
# previous stream without the manager's decision) or a creation step failed;
# 5 the skill check of the finished setup says invalid (H2).
REPO=/Volumes/workspace/hirearchy
ST=$REPO/studies/P1-itemized-playbook
EV=$ST/evidence
H=$EV/harness
SHA_REF=8bf7c69b
REQUIRED_SKILL_MD5=b10238639f48ab351fa44a06aed03ffb

LABEL="$1"; DRY=0
[[ "$2" == "--dry-run" ]] && DRY=1
[[ $# -eq 1 || ( $# -eq 2 && $DRY -eq 1 ) ]] || { echo "usage: setup_stream.sh <label> [--dry-run]" >&2; exit 2; }
[[ "$LABEL" =~ '^[FI][1-3](r[0-9]*)?$' ]] || { echo "setup_stream.sh: '$LABEL' is not a P1 stream label (F1..F3, I1..I3, replacements ...r)" >&2; exit 2; }
ARM=${LABEL[1,1]}
STREAM=$EV/$LABEL
PNAME=hirearchy-study-p1-$LABEL-assistant

fails=()
gate() {  # gate <name> <ok 0/1> <detail>
  if [[ "$2" == 1 ]]; then echo "gate: $1: OK${3:+ ($3)}"; else echo "gate: $1: FAILED${3:+ ($3)}"; fails+=("$1: $3"); fi
}
# 1. protocol.md vs protocol.md5
if [[ -f $EV/protocol.md && -f $EV/protocol.md5 ]]; then
  pm=$(md5 -q $EV/protocol.md); pr=$(awk '{print $1; exit}' $EV/protocol.md5)
  [[ -n "$pm" && "$pm" == "$pr" ]] && gate "protocol.md md5 = protocol.md5" 1 "$pm" || gate "protocol.md md5 = protocol.md5" 0 "protocol.md $pm, protocol.md5 $pr"
else
  gate "protocol.md md5 = protocol.md5" 0 "$EV/protocol.md or protocol.md5 is missing"
fi
# 2. harness/MD5SUMS
if [[ -f $H/MD5SUMS ]]; then
  nlines=0; bad=()
  while read -r sum name; do
    [[ -z "$sum" ]] && continue
    nlines=$((nlines+1))
    [[ -f "$H/$name" && "$(md5 -q "$H/$name")" == "$sum" ]] || bad+=("$name")
  done < $H/MD5SUMS
  (( ${#bad} == 0 && nlines > 0 )) && gate "MD5SUMS lines" 1 "$nlines lines, no mismatch" || gate "MD5SUMS lines" 0 "${#bad} mismatch/missing of $nlines: ${bad[*]}"
else
  gate "MD5SUMS lines" 0 "$H/MD5SUMS is missing"
fi
# 3. HEAD, 4. freeze diff
FULL=$(git -C $REPO rev-parse $SHA_REF 2>/dev/null); HEADSHA=$(git -C $REPO rev-parse HEAD 2>/dev/null)
[[ -n "$FULL" && "$HEADSHA" == "$FULL" ]] && gate "HEAD = $SHA_REF" 1 "$HEADSHA" || gate "HEAD = $SHA_REF" 0 "HEAD $HEADSHA, $SHA_REF is '$FULL'"
FZ=$(git -C $REPO diff --stat $SHA_REF HEAD -- src skills pyproject.toml uv.lock 2>&1)
[[ -z "$FZ" ]] && gate "freeze diff empty" 1 "git diff --stat $SHA_REF HEAD -- src skills pyproject.toml uv.lock" || gate "freeze diff empty" 0 "non-empty: $(print -r -- "$FZ" | tail -1)"
# 6. skill rule (before anything is created)
REPO_SKILL_MD5=$(md5 -q $REPO/skills/hirearchy/SKILL.md 2>/dev/null)
GLOBAL_SKILL=$HOME/.kiro/skills/hirearchy/SKILL.md
GLOBAL_SKILL_MD5=""; [[ -f $GLOBAL_SKILL ]] && GLOBAL_SKILL_MD5=$(md5 -q $GLOBAL_SKILL)
[[ "$REPO_SKILL_MD5" == "$REQUIRED_SKILL_MD5" ]] && gate "repo SKILL.md md5" 1 "$REPO_SKILL_MD5" || gate "repo SKILL.md md5" 0 "$REPO_SKILL_MD5, required $REQUIRED_SKILL_MD5"
[[ -z "$GLOBAL_SKILL_MD5" || "$GLOBAL_SKILL_MD5" == "$REPO_SKILL_MD5" ]] && gate "global SKILL.md absent or = repo" 1 "${GLOBAL_SKILL_MD5:-absent}" || gate "global SKILL.md absent or = repo" 0 "global $GLOBAL_SKILL_MD5, repo $REPO_SKILL_MD5 (H2)"
# 7. KIRO_HOME unset (protocol 1)
[[ -z "${KIRO_HOME+set}" ]] && gate "KIRO_HOME unset in this shell" 1 || gate "KIRO_HOME unset in this shell" 0 "KIRO_HOME is set: unset it before the stream (protocol 1)"
# 5. model listed
if [[ $DRY -eq 0 ]]; then
  LISTING="$(kiro-cli chat --list-models 2>&1)"
  print -r -- "$LISTING" | grep -Eq '(^|[[:space:]*])claude-sonnet-5\.5[[:space:]]' && gate "claude-sonnet-5.5 listed" 1 || gate "claude-sonnet-5.5 listed" 0 "claude-sonnet-5.5 is not listed: the stream does not start, tell the manager"
else
  echo "gate: claude-sonnet-5.5 listed: (not checked in --dry-run: would run kiro-cli chat --list-models)"
fi
# refusals (not gates): nothing is overwritten
[[ -e $STREAM/sandbox-path.txt ]] && { echo "REFUSED: $STREAM/sandbox-path.txt exists: this label was set up already" >&2; exit 4; }
PDIR=$HOME/.kiro/agents
[[ -e $PDIR/$PNAME.json ]] && { echo "REFUSED: $PDIR/$PNAME.json exists already" >&2; exit 4; }
[[ "$LABEL" == *r* && ! -e $EV/manager-decision-replacement-${LABEL%r*}.md ]] && { echo "REFUSED: replacement $LABEL needs the manager's recorded approval $EV/manager-decision-replacement-${LABEL%r*}.md (protocol 8)" >&2; exit 4; }
[[ "$LABEL" =~ '^[FI][1-3]r[0-9]*$' && "$LABEL" != ?[1-3]r ]] && { echo "REFUSED: a replacement is <label>r, one per stream (protocol 8)" >&2; exit 4; }
if [[ "$LABEL" == *r ]]; then
  other=($EV/${ARM}[1-3]r(N/)); other=(${other:#$STREAM})
  (( ${#other} )) && { echo "REFUSED: arm $ARM has a replacement stream already (${other:t}): at most one per arm (protocol 8)" >&2; exit 4; }
fi

if (( ${#fails} )); then
  for f in $fails; do echo "GATE FAILED: $f"; done
  if [[ $DRY -eq 0 ]]; then exit 3; fi
fi
# the memories gate (protocol 8): a change of memories.db since the previous stream's end stops the study before this stream, as a change
# during a stream does; checked before any folder, sandbox or profile exists (md5 only, never the store)
MDB=$HOME/.kiro/memories/memories.db
MDB_NOW=$( [[ -f $MDB ]] && md5 -q $MDB || echo absent )
MGATE=$(python3 -B $H/memories_gate.py --ev $EV --label $LABEL --current "$MDB_NOW"); MGRC=$?
echo "$MGATE"
if (( MGRC != 0 )); then
  if [[ $DRY -eq 0 ]]; then exit 4; fi
  echo "DRY-RUN: without --dry-run this would exit 4 (nothing created)"
fi

EPOCH=$(date +%s)
S=/tmp/hirearchy-p1-$LABEL-$EPOCH
PROFILE_DIR=$HOME/.kiro/agents
KH_ARG=""

if [[ $DRY -eq 1 ]]; then
  echo "DRY-RUN setup_stream.sh $LABEL (nothing is created or written)"
  (( ${#fails} )) && echo "DRY-RUN: ${#fails} gate(s) failed above; without --dry-run this would print GATE FAILED and exit 3"
  echo "arm: $ARM"
  echo "S=$S   (epoch $EPOCH; S/org is NOT created)"
  echo "DRY-RUN: mkdir $STREAM; write sandbox-path.txt, epoch.txt, arm.txt, stream-start-utc.txt"
  echo "DRY-RUN: safety-snapshot.sh \"$LABEL before\" > $STREAM/safety-before.txt"
  echo "DRY-RUN: write the memories gate's md5 ($MDB_NOW) to $STREAM/memories-md5-before.txt and its line to memories-db.txt"
  echo "DRY-RUN: ambient_snapshot.sh \"$LABEL setup\" $KH_ARG > $STREAM/ambient/setup.txt"
  echo "DRY-RUN: mkdir $S/notes $S/.kiro/skills/hirearchy $S/.kiro/settings"
  echo "DRY-RUN: cp -p $EV/notes/* $S/notes/"
  echo "DRY-RUN: cp -p $REPO/skills/hirearchy/SKILL.md $S/.kiro/skills/hirearchy/SKILL.md   (md5 $REPO_SKILL_MD5)"
  echo "DRY-RUN: cp -p $H/workspace-cli.json $S/.kiro/settings/cli.json"
  echo "DRY-RUN: profile $PROFILE_DIR/$PNAME.json from $H/profile-template.json (<LABEL> -> $LABEL, <epoch> -> $EPOCH; ORG_ROOT $S/org)"
  echo "DRY-RUN: copy the profile to $STREAM/profiles/; append name, md5, UTC to $STREAM/profiles/creations.txt"
  echo "DRY-RUN: model_check.sh listed $LABEL; write $STREAM/setup.txt; zsh $H/skill_check.sh $LABEL setup (writes $STREAM/skill-check.txt)"
  exit 0
fi

# ------------------------------------------------------------------ creation
mkdir -p $STREAM/ambient $STREAM/profiles || { echo "FAILED: cannot create $STREAM" >&2; exit 4; }
STARTU=$(date -u +%FT%TZ)
echo $EPOCH > $STREAM/epoch.txt
echo $S > $STREAM/sandbox-path.txt
echo $ARM > $STREAM/arm.txt
echo $STARTU > $STREAM/stream-start-utc.txt
zsh $H/safety-snapshot.sh "$LABEL before" > $STREAM/safety-before.txt 2>&1
# the owner's memories.db before this stream (design 18.2): the md5 the memories gate checked, never the store itself
echo $MDB_NOW > $STREAM/memories-md5-before.txt
echo "before $LABEL ($(date -u +%FT%TZ)): $MGATE" >> $STREAM/memories-db.txt
zsh $H/ambient_snapshot.sh "$LABEL setup" $KH_ARG > $STREAM/ambient/setup.txt 2>&1
mkdir -p $S/notes $S/.kiro/skills/hirearchy $S/.kiro/settings || { echo "FAILED: cannot create the sandbox $S" >&2; exit 4; }
cp -p $EV/notes/*(.N) $S/notes/ || { echo "FAILED: notes" >&2; exit 4; }
cp -p $REPO/skills/hirearchy/SKILL.md $S/.kiro/skills/hirearchy/SKILL.md || { echo "FAILED: skill copy" >&2; exit 4; }
cp -p $H/workspace-cli.json $S/.kiro/settings/cli.json || { echo "FAILED: workspace settings" >&2; exit 4; }
mkdir -p $PROFILE_DIR
sed -e "s/<LABEL>/$LABEL/g" -e "s/<epoch>/$EPOCH/g" $H/profile-template.json > $PROFILE_DIR/$PNAME.json || { echo "FAILED: profile" >&2; exit 4; }
PMD5=$(md5 -q $PROFILE_DIR/$PNAME.json)
cp -p $PROFILE_DIR/$PNAME.json $STREAM/profiles/$PNAME.json
echo "profile created $(date -u +%FT%TZ): $PROFILE_DIR/$PNAME.json md5 $PMD5" >> $STREAM/profiles/creations.txt
kiro-cli agent validate --path $PROFILE_DIR/$PNAME.json > $STREAM/profiles/validate.txt 2>&1; VRC=$?
zsh $H/model_check.sh listed $LABEL > /dev/null 2>&1; MCRC=$?
# the study's first profile copy: the earliest other stream with a profiles/ copy
REF=""; REFSTART=""
for d in $EV/[FI][1-3]*(/N); do
  [[ "$d" == "$STREAM" ]] && continue
  rf=($d/profiles/hirearchy-study-p1-*-assistant.json(N)); [[ -n "${rf[1]}" && -f $d/stream-start-utc.txt ]] || continue
  st=$(cat $d/stream-start-utc.txt)
  if [[ -z "$REFSTART" || "$st" < "$REFSTART" ]]; then REF=${rf[1]}; REFSTART=$st; fi
done
{
  echo "# P1 $LABEL setup (recorded before turn 1)"
  echo "date: $(date); utc: $(date -u +%FT%TZ)"
  echo "arm: $ARM"
  echo "kiro home for the chat: the owner's ~/.kiro (run_turn.sh: env -u KIRO_HOME, both arms); KIRO_HOME set in this shell? $( [[ -n "${KIRO_HOME+set}" ]] && echo yes || echo no )"
  echo "memories.db md5 before this stream: $(cat $STREAM/memories-md5-before.txt)"
  echo "== protocol.md vs protocol.md5"
  echo "md5 -q protocol.md: $(md5 -q $EV/protocol.md)"
  echo "protocol.md5: $(awk '{print $1; exit}' $EV/protocol.md5)"
  echo "== amendments:"
  am=($EV/protocol-amendment-*(N)); (( ${#am} )) && for f in $am; do echo "$f md5 $(md5 -q $f)"; done || echo none
  echo "== manager-decision files:"
  md=($EV/manager-decision-*(N)); (( ${#md} )) && for f in $md; do echo "$f"; done || echo none
  echo "== harness/MD5SUMS check (prints MISMATCH lines only)"
  n=0; while read -r sum name; do [[ -z "$sum" ]] && continue; n=$((n+1)); [[ "$(md5 -q $H/$name 2>/dev/null)" == "$sum" ]] || echo "MISMATCH $name"; done < $H/MD5SUMS; echo "(done, $n lines)"
  echo "MD5SUMS md5: $(md5 -q $H/MD5SUMS)"
  echo "global SKILL.md md5: ${GLOBAL_SKILL_MD5:-absent} (required $REQUIRED_SKILL_MD5)"
  echo "repo SKILL.md md5: $REPO_SKILL_MD5"
  echo "injection script md5: $(md5 -q $H/inject_root_rework.py)"
  echo "== HIREARCHY_STATE_DIR set? $( [[ -n "${HIREARCHY_STATE_DIR+set}" ]] && echo yes || echo no )"
  echo "== processes referencing any P1 sandbox"
  PSG=$(ps -axo pid,etime,command | grep -F hirearchy-p1- | grep -v grep | cut -c1-200); [[ -n "$PSG" ]] && print -r -- "$PSG" || echo "(none)"
  echo "== ~/.kiro/agents"
  ls $HOME/.kiro/agents
  echo "== repo checks (4.1) BEFORE turn 1"
  echo "git rev-parse HEAD: $(git -C $REPO rev-parse HEAD)"
  echo "git status --porcelain:"; git -C $REPO status --porcelain
  echo "git diff --stat $SHA_REF HEAD -- src skills pyproject.toml uv.lock: [$(git -C $REPO diff --stat $SHA_REF HEAD -- src skills pyproject.toml uv.lock)]"
  echo "== kiro-cli --version: $(kiro-cli --version)"
  echo "== S: $S  epoch: $EPOCH (sandbox created at epoch $EPOCH)"
  echo "== model_check.sh listed $LABEL: $(tail -1 $STREAM/model-checks.txt) (exit $MCRC)"
  echo "== assistant profile ($PROFILE_DIR/$PNAME.json; copy in profiles/)"
  md5 $PROFILE_DIR/$PNAME.json
  echo "kiro-cli agent validate --path: exit $VRC (output in profiles/validate.txt)"
  if [[ -n "$REF" ]]; then
    RL=${${REF:t}#hirearchy-study-p1-}; RL=${RL%-assistant.json}; RE=$(cat ${REF:h:h}/epoch.txt 2>/dev/null)
    echo "(diff against the study's first profile copy $REF, raw: the label and the sandbox epoch only)"; diff $REF $PROFILE_DIR/$PNAME.json; echo "(diff exit $?)"
    echo "(the same diff with the label and the epoch masked in both: empty means byte-identical but for them, protocol 1)"
    diff <(sed -e "s/$RL/<LABEL>/g" -e "s/$RE/<epoch>/g" $REF) <(sed -e "s/$LABEL/<LABEL>/g" -e "s/$EPOCH/<epoch>/g" $PROFILE_DIR/$PNAME.json); echo "(masked diff exit $?)"
  else echo "(diff against the study's first profile copy: this is the first stream, no reference)"; fi
  echo "== workspace settings"
  md5 $S/.kiro/settings/cli.json
  cat $S/.kiro/settings/cli.json; md5 $H/workspace-cli.json
  echo "== skill copies"
  md5 $REPO/skills/hirearchy/SKILL.md
  md5 $S/.kiro/skills/hirearchy/SKILL.md
  [[ -f $GLOBAL_SKILL ]] && echo "global: md5 $GLOBAL_SKILL_MD5 ($GLOBAL_SKILL)" || echo "global: absent"
  wc -l $REPO/skills/hirearchy/SKILL.md $S/.kiro/skills/hirearchy/SKILL.md
  echo "== notes"
  md5 $S/notes/*
  echo "== org dir exists before turn 1? $( [[ -e $S/org ]] && echo YES || echo no )"
  echo "== ps: processes referencing the sandbox"
  PSS=$(ps -axo pid,etime,command | grep -F "$S" | grep -v grep); [[ -n "$PSS" ]] && print -r -- "$PSS" || echo "(none)"
  echo "== other P1 streams running: $(ps -axo command | grep -F hirearchy-p1- | grep -v grep | grep -vF "$S" | wc -l | tr -d ' ') processes"
  echo "== safety-before.txt taken: $(grep -m1 '^date_utc' $STREAM/safety-before.txt); ambient/setup.txt taken"
} > $STREAM/setup.txt 2>&1
zsh $H/skill_check.sh $LABEL setup > /dev/null 2>&1; SRC=$?
echo "set up $LABEL: S=$S arm=$ARM"
echo "profile: $PROFILE_DIR/$PNAME.json (md5 $PMD5)"
if [[ $SRC -ne 0 ]]; then echo "SKILL CHECK: INVALID (H2), see $STREAM/skill-check.txt: do not start this stream" >&2; exit 5; fi
exit 0
