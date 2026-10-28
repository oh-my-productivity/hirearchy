#!/bin/zsh
# P1 stream finish (G0's finish_stream.sh, M1 treatment only; protocol 7). Usage: finish_stream.sh <label>      (after the last turn)
# In this order, never stopping on one failure (every step's exit code is recorded in $EV/<label>/finish-steps.txt; failures are also listed
# in finish-failures.txt; the exit code of this script is 1 if any step failed, else 0):
#   1.  the injection script's --stop, only if a scheduler still runs (scheduler.pid + ps) -> scheduler-stop.txt
#   2.  copy_org_evidence.sh <S> <label> (+ the sandbox's injection/ folder copied into the stream dir: injection_files.py reads it there)
#   3.  `hirearchy --root S/org check` -> observe-check.txt with its exit code
#   4.  quality_snapshot.sh <label> end and services_snapshot.sh <label> end
#   5.  the extracts and measures, each into its file: extract_tool_calls.py (assistant-tool-calls.txt, session-turn-times-utc.txt),
#       extract_proposals.py, extract_mechanical.py <dir> <S>, scheduler_survival.py, injection_files.py, assistant_facts.py, score_memos.py,
#       ambiguity_recall.py, prompt_sizes.py, playbook_attempts.py (outputs into measures/), rederive_quality.py --compare quality/end.json
#       (outputs into rederived/); score_memos.py runs with --memos 6 (and --owner-forms owner-forms.json when the stream step wrote it);
#       extract_mechanical.py runs with --p1 (rederive_watch.py into watch/, guarantees.py into guarantees/: G1, G2, the orders).
#       Each script's CLI is in its own docstring (protocol section 10 lists them).
#   6.  model_check.sh all <label> <S>
#   7.  the profile cleanup: the profile is copied into profiles/, compared (cmp) and deleted from ~/.kiro/agents (both arms); name, md5 and
#       UTC go to profiles/deletions.txt. Nothing else in any kiro home is touched.
#   8.  safety-after.txt (+ safety-diff.txt), ambient/end.txt, the owner's memories.db md5 after the stream (memories-md5-after.txt; a change
#       against memories-md5-before.txt is written to memories-db.txt and printed as `STOP:`), the empty-argument call total (empty-calls.txt:
#       the session-store count, the greps beside it), the stream's credits (credits.txt, cost_total.py: protocol 11), arm F's H-LOCK
#       re-check over the copied evidence (lock/h-lock-after.txt: no owner version before the lock, every contract version from the lock on
#       `locked: true`), and the freeze checks again appended to setup.txt.
# The sandbox is left in place, read-only, until the teardown.
LABEL="$1"
REPO=/Volumes/workspace/hirearchy
ST=$REPO/studies/P1-itemized-playbook
EV=$ST/evidence
H=$EV/harness
SHA_REF=8bf7c69b
[[ "$LABEL" =~ '^[FI][1-3](r[0-9]*)?$' && $# -eq 1 ]] || { echo "usage: finish_stream.sh <label>" >&2; exit 2; }
D=$EV/$LABEL
[[ -f $D/sandbox-path.txt ]] || { echo "finish_stream.sh: $D/sandbox-path.txt is missing" >&2; exit 2; }
S=$(cat $D/sandbox-path.txt)
ARM=${LABEL[1,1]}
PNAME=hirearchy-study-p1-$LABEL-assistant
KH_ARG=""; PDIR=$HOME/.kiro/agents
mkdir -p $D/measures $D/rederived $D/profiles $D/quality $D/services $D/ambient
STEPS=$D/finish-steps.txt; FAILS=$D/finish-failures.txt
echo "# finish_stream.sh $LABEL started $(date -u +%FT%TZ)" >> $STEPS
nfail=0

step() {  # step <name> <output file or /dev/null> <command...>: run, record the exit code, never stop
  local name="$1" out="$2"; shift 2
  local t0=$(date -u +%FT%TZ)
  "$@" > "$out" 2>&1; local rc=$?
  echo "$name exit $rc  ($t0 .. $(date -u +%FT%TZ))  -> ${out#$D/}" >> $STEPS
  if (( rc != 0 )); then nfail=$((nfail+1)); echo "$name exit $rc: $*" >> $FAILS; echo "STEP FAILED: $name exit $rc (output: ${out#$D/})"; else echo "ok: $name"; fi
}

# 1. the scheduler, if one still runs
SCHED_PID=""
if [[ -f $S/org/.runtime/scheduler.pid ]]; then
  SCHED_PID=$(cat $S/org/.runtime/scheduler.pid | tr -dc '0-9')
  if [[ -n "$SCHED_PID" ]] && ps -p "$SCHED_PID" > /dev/null 2>&1; then
    echo "a scheduler still runs (pid $SCHED_PID) at $(date -u +%FT%TZ): stopping it through the injection script (protocol 4.8)" | tee -a $STEPS
    step "injection script --stop" $D/scheduler-stop.txt uv --directory $REPO run python $H/inject_root_rework.py --org $S/org --out $S/injection --stop
  else
    SCHED_PID=""
  fi
fi
[[ -z "$SCHED_PID" ]] && echo "no scheduler running at $(date -u +%FT%TZ): no --stop" >> $STEPS

# 2. the org evidence
step copy_org_evidence $D/copy_org_evidence-output.txt zsh $H/copy_org_evidence.sh $S $LABEL
if [[ -d $S/injection ]]; then
  mkdir -p $D/injection
  step "copy injection folder" /dev/null cp -pR $S/injection/. $D/injection/
fi

# 3. hirearchy check
{ uv --directory $REPO run hirearchy --root $S/org check; echo "exit code: $?"; } > $D/observe-check.txt 2>&1
echo "observe check -> observe-check.txt ($(tail -1 $D/observe-check.txt))" >> $STEPS

# 4. quality at the end
step "quality_snapshot end" $D/quality/end-snapshot-output.txt zsh $H/quality_snapshot.sh $LABEL end
step "services_snapshot end" $D/services/end-snapshot-output.txt zsh $H/services_snapshot.sh $LABEL end

# 5. extracts and measures
step extract_tool_calls $D/extract_tool_calls-output.txt python3 -B $H/extract_tool_calls.py $D/assistant-session-messages.jsonl $D/assistant-tool-calls.txt $D/session-turn-times-utc.txt
step extract_proposals $D/measures/extract_proposals-output.txt python3 -B $H/extract_proposals.py $D
step extract_mechanical $D/extract_mechanical-output.txt python3 -B $H/extract_mechanical.py $D $S --p1
step scheduler_survival $D/measures/scheduler_survival-output.txt python3 -B $H/scheduler_survival.py $D
step "scheduler_survival (measures/)" $D/measures/scheduler_survival-measures-output.txt python3 -B $H/scheduler_survival.py $D --out $D/measures
step injection_files $D/measures/injection_files-output.txt python3 -B $H/injection_files.py $D $S
step assistant_facts $D/measures/assistant_facts-output.txt python3 -B $H/assistant_facts.py $D --out $D/measures
OF=(); [[ -f $D/owner-forms.json ]] && OF=(--owner-forms $D/owner-forms.json)
step score_memos $D/measures/score_memos-output.txt python3 -B $H/score_memos.py $D --out $D/measures --memos 6 $OF
step ambiguity_recall $D/measures/ambiguity_recall-output.txt python3 -B $H/ambiguity_recall.py $D --out $D/measures
step prompt_sizes $D/measures/prompt_sizes-output.txt python3 -B $H/prompt_sizes.py $D --out $D/measures
step playbook_attempts $D/measures/playbook_attempts-output.txt python3 -B $H/playbook_attempts.py $D --out $D/measures
step rederive_quality $D/rederived/rederive_quality-output.txt python3 -B $H/rederive_quality.py $D --out $D/rederived --compare $D/quality/end.json

# 6. models
zsh $H/model_check.sh all $LABEL $S > $D/measures/model_check-all-output.txt 2>&1; mrc=$?
echo "model_check all exit $mrc -> model-checks.txt" >> $STEPS
(( mrc != 0 )) && { nfail=$((nfail+1)); echo "model_check all exit $mrc" >> $FAILS; echo "STEP FAILED: model_check all exit $mrc"; }

# 7. profile cleanup
PF=$PDIR/$PNAME.json
if [[ -f $PF ]]; then
  PMD5=$(md5 -q $PF)
  if [[ -f $D/profiles/$PNAME.json ]] && ! cmp -s $PF $D/profiles/$PNAME.json; then
    cp -p $D/profiles/$PNAME.json $D/profiles/$PNAME.created.json
    echo "NOTE: the profile at the end differs from the copy made at its creation (kept as $PNAME.created.json)" >> $FAILS
    nfail=$((nfail+1))
  fi
  cp -p $PF $D/profiles/$PNAME.json
  if cmp -s $PF $D/profiles/$PNAME.json; then
    rm -f $PF
    if [[ ! -e $PF ]]; then
      echo "profile deleted $(date -u +%FT%TZ): $PF md5 $PMD5" >> $D/profiles/deletions.txt
      echo "ok: profile $PNAME deleted"
    else
      echo "profile NOT deleted (rm failed): $PF" >> $FAILS; nfail=$((nfail+1)); echo "STEP FAILED: profile delete"
    fi
  else
    echo "profile copy does not match $PF; NOT deleted" >> $FAILS; nfail=$((nfail+1)); echo "STEP FAILED: profile copy mismatch"
  fi
else
  echo "no profile at $PF (already deleted?)" >> $D/profiles/deletions.txt
  echo "STEP NOTE: no profile at $PF"
fi

# 8. safety, ambient, the 4.1 checks again
zsh $H/safety-snapshot.sh "$LABEL after" > $D/safety-after.txt 2>&1
diff <(grep -v '^date' $D/safety-before.txt) <(grep -v '^date' $D/safety-after.txt) > $D/safety-diff.txt 2>&1
zsh $H/ambient_snapshot.sh "$LABEL end" > $D/ambient/end.txt 2>&1
# the owner's memories.db after this stream (design 18.2): md5 only
MDB=$HOME/.kiro/memories/memories.db
{ [[ -f $MDB ]] && md5 -q $MDB || echo absent; } > $D/memories-md5-after.txt
if [[ "$(cat $D/memories-md5-after.txt)" != "$(cat $D/memories-md5-before.txt 2>/dev/null)" ]]; then
  echo "memories.db CHANGED during $LABEL: $(cat $D/memories-md5-before.txt 2>/dev/null) -> $(cat $D/memories-md5-after.txt)" >> $D/memories-db.txt
  echo "STOP: memories.db changed during $LABEL: send a warning before the next stream and wait (the stream stays valid; never restore or edit the store)"
else
  echo "memories.db unchanged during $LABEL: $(cat $D/memories-md5-after.txt)" >> $D/memories-db.txt
fi
# the empty-argument calls (18.3 item 3; f-g0-7 section 1): the session-store count decides (empty_calls.py), the greps are reported beside it
{
  echo "total: $(python3 -B $H/empty_calls.py $D/assistant-session-messages.jsonl) (decides the validity label, protocol 8)"
  echo "total 'is not available' in turn-*.stderr.txt: $(cat $D/turn-*.stderr.txt(N) 2>/dev/null | grep -c 'is not available') (reported)"
  echo "total 'is not available' in assistant-tool-calls.txt: $(grep -c 'is not available' $D/assistant-tool-calls.txt 2>/dev/null || echo 0) (reported)"
} >> $D/empty-calls.txt
# the stream's credits (protocol 11): assistant + every org run, the injection window included, one line read by next_stream.sh and the gate
python3 -B $H/cost_total.py $D/cost.txt > $D/credits.txt; echo "credits: $(cat $D/credits.txt)"
# arm F: H-LOCK again (no owner version after the lock either: PB-LOCKED refuses every owner op; one would be a product defect)
if [[ $ARM == F ]]; then
  python3 - "$D" > $D/lock/h-lock-after.txt 2>&1 <<'PY'
import sys,re,glob,os
D=sys.argv[1]
fm=lambda t:(re.match(r'^---\n(.*?)\n---',t,re.S) or [None,''])[1]
# the lead (the service's owner) as the lock hook recorded it (lock/hook.txt `lead=...`), never guessed from the mail
hook=os.path.join(D,'lock','hook.txt')
m=re.search(r'\blead=(\S+)',open(hook,errors='replace').read()) if os.path.exists(hook) else None
lead=m.group(1) if m else None
print('lead (lock/hook.txt):',lead or 'MISSING')
lock=None
for f in glob.glob(os.path.join(D,'service','*.md')):
    t=fm(open(f,errors='replace').read())
    if re.search(r'^locked:\s*true$',t,re.M):
        d=re.search(r"^defined:\s*'?([^'\n]+)",t,re.M); v=re.search(r'^version:\s*(\d+)',t,re.M)
        if d and (lock is None or d.group(1)<lock[0]): lock=(d.group(1),v.group(1) if v else '?')
print('lock version:',lock)
bad=[]
for f in sorted(glob.glob(os.path.join(D,'playbook','*.md'))):
    t=fm(open(f,errors='replace').read())
    by=re.search(r'^by:\s*(.+)$',t,re.M); rv=re.search(r"^revised:\s*'?([^'\n]+)",t,re.M); op=re.search(r'^op:\s*(\S+)',t,re.M)
    if by and lead and by.group(1).strip().strip("'\"")==lead:
        bad.append(f"{os.path.basename(f)} op {op.group(1) if op else '?'} revised {rv.group(1) if rv else '?'}")
print('owner versions:', bad or 'none')
held=[]
for f in sorted(glob.glob(os.path.join(D,'service','*.md'))):
    t=fm(open(f,errors='replace').read()); v=re.search(r'^version:\s*(\d+)',t,re.M); lk=re.search(r'^locked:\s*(\S+)',t,re.M)
    if lock and v and lock[1]!='?' and int(v.group(1))>=int(lock[1]): held.append((int(v.group(1)),lk.group(1) if lk else '(absent)'))
held=sorted(set(held)); unheld=[f'v{v} locked: {lk}' for v,lk in held if lk!='true']
print('contract versions from the lock on:', ', '.join(f'v{v} locked: {lk}' for v,lk in held) or 'none')
before=bool(bad and lock and any(b.split('revised ')[-1] < lock[0] for b in bad))
if before or unheld or not lock or not lead:
    print('H-LOCK: INVALID: '+('; '.join((['an owner version before the lock'] if before else [])+([', '.join(unheld)+' after the lock (the arm was not held)'] if unheld else [])+(['no locked contract version'] if not lock else [])+(['no lock hook record (lock/hook.txt)'] if not lead else []))))
else:
    print('H-LOCK: ok' if not bad else 'H-LOCK: ok before the lock; owner versions after it: a product defect to record')
PY
  echo "H-LOCK after the stream: $(tail -1 $D/lock/h-lock-after.txt)"
fi
{
  echo
  echo "== AFTER the last turn ($(date -u +%FT%TZ)) (protocol 4.1, 6 item 5)"
  echo "git rev-parse HEAD: $(git -C $REPO rev-parse HEAD)"
  echo "git status --porcelain:"; git -C $REPO status --porcelain
  echo "git diff --stat $SHA_REF HEAD -- src skills pyproject.toml uv.lock: [$(git -C $REPO diff --stat $SHA_REF HEAD -- src skills pyproject.toml uv.lock)]"
  echo "kiro-cli --version: $(kiro-cli --version)"
  nmis=0; while read -r sum name; do [[ -z "$sum" ]] && continue; [[ "$(md5 -q $H/$name 2>/dev/null)" == "$sum" ]] || nmis=$((nmis+1)); done < $H/MD5SUMS
  echo "protocol.md md5: $(md5 -q $EV/protocol.md) (protocol.md5 $(awk '{print $1; exit}' $EV/protocol.md5)); harness/MD5SUMS mismatches: $nmis"
  echo "global SKILL.md md5: $(md5 -q $HOME/.kiro/skills/hirearchy/SKILL.md 2>/dev/null || echo absent)"
  echo "processes referencing the sandbox: $(ps -axo command | grep -F "${S:t}" | grep -v grep | wc -l | tr -d ' ')"
  echo "~/.kiro/agents: $(ls $HOME/.kiro/agents | tr '\n' ' ')"
} >> $D/setup.txt 2>&1
echo "# finish_stream.sh $LABEL ended $(date -u +%FT%TZ); failed steps: $nfail" >> $STEPS
echo "finished $LABEL: $nfail failed step(s); see $STEPS$( (( nfail > 0 )) && echo " and $FAILS")"
(( nfail > 0 )) && exit 1
exit 0
