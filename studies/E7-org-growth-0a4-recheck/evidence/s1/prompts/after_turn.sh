#!/bin/zsh
# facilitator helper (E7 s1, protocol 6 item 3): usage after_turn.sh <turn n>   -- no MCP/CLI call against the org (file reads and ps only)
# Adapted from E6 s1's prompts/after_turn.sh: paths and names E7's; adds the signal record (D-SIGNAL) and the ambient comparison (4.5.1).
N=1; T="$1"
EV=/Volumes/workspace/hirearchy/studies/E7-org-growth-0a4-recheck/evidence
D=$EV/s$N; S=$(cat $D/sandbox-path.txt)
NN=$(printf '%02d' "$T")
python3 $EV/harness/org_state.py $S "after turn $T" >> $D/run-counts-by-turn.txt 2>&1
python3 - "$S" "$D" <<'PY'
import json,glob,os,sys,shutil
S,D=sys.argv[1:3]; real=os.path.realpath(S)
best=None; bt=0
for p in glob.glob(os.path.expanduser('~/.kiro/sessions/*/sess_*/session.json')):
    try: j=json.load(open(p))
    except Exception: continue
    if j.get('agentMode')=='hirearchy-study-e7-s1-assistant' and (j.get('workspacePaths') or [''])[0] in (real,S):
        m=os.path.getmtime(p)
        if m>=bt: best,bt=p,m
if not best: print('NO SESSION FOUND'); sys.exit(1)
shutil.copy2(best,D+'/assistant-session.json'); shutil.copy2(os.path.dirname(best)+'/messages.jsonl',D+'/assistant-session-messages.jsonl')
print('session copied from',best)
PY
# scheduler record for D-SURVIVE (protocol 6): UTC time, scheduler.pid content, ps line
{
  echo "--- scheduler record after turn $T at $(date -u +%FT%TZ)"
  if [[ -f $S/org/.runtime/scheduler.pid ]]; then
    PID=$(cat $S/org/.runtime/scheduler.pid | tr -dc '0-9')
    echo "scheduler.pid: $(cat $S/org/.runtime/scheduler.pid | tr '\n' ' ')"
    echo "ps -o pid=,ppid=,stat=,etime=,command= -p $PID:"
    ps -o pid=,ppid=,stat=,etime=,command= -p "$PID" 2>&1 || echo "(not running)"
  else
    echo "scheduler.pid: (no file)"
  fi
  echo "scheduler.exit: $( [[ -f $S/org/.runtime/scheduler.exit ]] && cat $S/org/.runtime/scheduler.exit | head -3 | tr '\n' ' ' || echo '(none)')"
  echo "processes referencing the sandbox name:"; ps -axo pid,ppid,stat,etime,command | grep hirearchy-e7-s1 | grep -v grep || echo "(none)"
} >> $D/run-counts-by-turn.txt 2>&1
# signal record (E7 item 5; D-SIGNAL): every scheduler.signal line in events/ (file reading only)
{
  echo "--- signal record after turn $T at $(date -u +%FT%TZ): every scheduler.signal line now in S/org/.runtime/events/ (cumulative)"
  if [[ -d $S/org/.runtime/events ]]; then
    EVF=("${(@f)$(find $S/org/.runtime/events -name '*.jsonl' 2>/dev/null | sort)}")
    echo "(scheduler.signal lines):"; [[ -n "${EVF[1]}" ]] && { grep -H '"scheduler.signal"' "${EVF[@]}" | sed "s#$S/org/.runtime/events/##" | cut -c1-600; true; }
    echo "(scheduler.exit lines):"; [[ -n "${EVF[1]}" ]] && { grep -H '"scheduler.exit"' "${EVF[@]}" | sed "s#$S/org/.runtime/events/##" | cut -c1-600; true; }
    echo "(run.orphan lines):"; [[ -n "${EVF[1]}" ]] && { grep -H '"run.orphan"' "${EVF[@]}" | sed "s#$S/org/.runtime/events/##" | cut -c1-600; true; }
  else echo "(no events dir)"; fi
  echo "(turn $T end per turn-times.txt:)"; grep -E "^turn $T:" $D/turn-times.txt
} >> $D/run-counts-by-turn.txt 2>&1
zsh $EV/harness/model_check.sh org $N $S | tail -3
zsh $EV/harness/model_check.sh assistant $N $S | tail -8
# throttle marks / exit 75 among run logs
echo "--- throttle/exit-75 scan after turn $T" >> $D/run-counts-by-turn.txt
{ [[ -d $S/org ]] && find $S/org -path '*/runs/*.log' -not -path '*/.git/*' -exec grep -lE '^# kiro: throttled by the model service|^# exit 75 ' {} + ; } >> $D/run-counts-by-turn.txt 2>/dev/null; echo "(end of scan)" >> $D/run-counts-by-turn.txt
# ambient comparison (4.5.1): the md5 lines of this turn's before/after and the previous after (or setup)
PREV=$D/ambient/setup.txt; [[ "$T" -ge 2 ]] && PREV=$D/ambient/turn-$(printf '%02d' $((T-1)))-after.txt
echo "--- ambient comparison turn $T (md5 lines)"
for f in $PREV $D/ambient/turn-$NN-before.txt $D/ambient/turn-$NN-after.txt; do echo "## $(basename $f)"; grep -E 'listing md5|memories\.db' $f; done
tail -45 $D/run-counts-by-turn.txt
