#!/bin/zsh
# facilitator helper (E6 s2): usage after_turn.sh <turn n>   -- no MCP/CLI call against the org (file reads and ps only)
N=2; T="$1"
EV=/Volumes/workspace/hirearchy/studies/E6-org-growth-0a3-recheck/evidence
D=$EV/s$N; S=$(cat $D/sandbox-path.txt)
python3 $EV/harness/org_state.py $S "after turn $T" >> $D/run-counts-by-turn.txt 2>&1
python3 - "$S" "$D" <<'PY'
import json,glob,os,sys,shutil
S,D=sys.argv[1:3]; real=os.path.realpath(S)
best=None
for p in glob.glob(os.path.expanduser('~/.kiro/sessions/*/sess_*/session.json')):
    try: j=json.load(open(p))
    except Exception: continue
    if j.get('agentMode')=='hirearchy-study-e6-s2-assistant' and (j.get('workspacePaths') or [''])[0] in (real,S):
        best=p
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
  echo "processes referencing the sandbox name:"; ps -axo pid,ppid,stat,etime,command | grep hirearchy-e6-s2 | grep -v grep || echo "(none)"
} >> $D/run-counts-by-turn.txt 2>&1
zsh $EV/harness/model_check.sh org $N $S | tail -3
zsh $EV/harness/model_check.sh assistant $N $S | tail -8
# throttle marks / exit 75 among run logs
echo "--- throttle/exit-75 scan after turn $T" >> $D/run-counts-by-turn.txt
{ [[ -d $S/org ]] && find $S/org -path '*/runs/*.log' -not -path '*/.git/*' -exec grep -lE '^# kiro: throttled by the model service|^# exit 75 ' {} + ; } >> $D/run-counts-by-turn.txt 2>/dev/null; echo "(end of scan)" >> $D/run-counts-by-turn.txt
tail -45 $D/run-counts-by-turn.txt
