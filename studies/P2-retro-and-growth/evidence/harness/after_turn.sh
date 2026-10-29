#!/bin/zsh
# P2 after-turn helper (P1's after_turn.sh without arm F's lock hook, with the arm's product; protocol 3.2). Called ONLY by turn.sh.
# Usage (through turn.sh): after_turn.sh <label> <turn n>
# Steps, in order: 1. the org state, the assistant session copy, the scheduler and signal records, model_check org and assistant, the
# throttle scan, the ambient comparison (P1's); 2. the empty-argument call counter (P1 8), the effort-stop counter (effort_stops.py), the
# org-run cap (140; a `CAP:` line), the running credits (running_credits.py; stage 2: `STOP-CREDITS:` over 260), root's requests and one-off
# tasks by turn (requests_by_turn.py), the skill and product checks (H2: arm C's global skill aside, arm R's in place; no process of the
# stream that names the other product); 3. the snapshots, LAST: quality_snapshot.sh, services_snapshot.sh, and in arm R retro_snapshot.sh.
# Lines starting `STOP:` mean the stream step stops at the end of this turn with a `warning` (protocol 8). Exit 0 unless a step of its own
# could not run (then turn.sh writes no .done record and the next turn is refused).
[[ "$P2_TURN_WRAPPER" == 1 ]] || { echo "REFUSED: after_turn.sh runs only inside turn.sh (one wrapper per turn, F-P1-14)" >&2; exit 93; }
LABEL="$1"; T="$2"
H0=${0:A:h}
source $H0/arm.sh "$LABEL" || exit 2
[[ "$T" =~ '^[1-9][0-9]*$' && $# -eq 2 ]] || { echo "usage: after_turn.sh <label> <turn n>" >&2; exit 2; }
D=$EV/$LABEL; [[ "$LABEL" == selfcheck-* && -n "$P2_EVDIR" ]] && D=$P2_EVDIR
S=$(cat $D/sandbox-path.txt); SN=${S:t}
NN=$(printf '%02d' "$T")
KH=$HOME/.kiro
# 1. P1's records
python3 -B $H0/org_state.py $S "after turn $T" >> $D/run-counts-by-turn.txt 2>&1
python3 - "$S" "$D" "$KH" "$PNAME" <<'PY'
import json,glob,os,sys,shutil
S,D,KH,PROFILE=sys.argv[1:5]; real=os.path.realpath(S)
best=None; bt=0
for p in glob.glob(os.path.join(KH,'sessions/*/sess_*/session.json')):
    try: j=json.load(open(p))
    except Exception: continue
    if j.get('agentMode')==PROFILE and (j.get('workspacePaths') or [''])[0] in (real,S):
        m=os.path.getmtime(p)
        if m>=bt: best,bt=p,m
if not best: print('NO SESSION FOUND'); sys.exit(0)
shutil.copy2(best,D+'/assistant-session.json'); shutil.copy2(os.path.dirname(best)+'/messages.jsonl',D+'/assistant-session-messages.jsonl')
print('session copied from',best)
PY
{
  echo "--- scheduler record after turn $T at $(date -u +%FT%TZ)"
  if [[ -f $S/org/.runtime/scheduler.pid ]]; then
    PID=$(cat $S/org/.runtime/scheduler.pid | tr -dc '0-9')
    echo "scheduler.pid: $(cat $S/org/.runtime/scheduler.pid | tr '\n' ' ')"
    ps -o pid=,ppid=,stat=,etime=,command= -p "$PID" 2>&1 || echo "(not running)"
  else echo "scheduler.pid: (no file)"; fi
  echo "scheduler.exit: $( [[ -f $S/org/.runtime/scheduler.exit ]] && head -3 $S/org/.runtime/scheduler.exit | tr '\n' ' ' || echo '(none)')"
  echo "processes referencing the sandbox name:"; ps -axo pid,ppid,stat,etime,command | grep -F "$SN" | grep -v grep || echo "(none)"
  echo "--- signal record after turn $T: scheduler.signal, scheduler.exit, run.orphan lines (cumulative)"
  if [[ -d $S/org/.runtime/events ]]; then
    find $S/org/.runtime/events -name '*.jsonl' 2>/dev/null | sort | while read f; do grep -H -E '"(scheduler\.signal|scheduler\.exit|run\.orphan)"' "$f" | sed "s#$S/org/.runtime/events/##" | cut -c1-600; done
  else echo "(no events dir)"; fi
} >> $D/run-counts-by-turn.txt 2>&1
zsh $H0/model_check.sh org $LABEL $S | tail -3
zsh $H0/model_check.sh assistant $LABEL $S | tail -6
{ echo "--- throttle/exit-75 scan after turn $T"; [[ -d $S/org ]] && find $S/org -path '*/runs/*.log' -not -path '*/.git/*' -exec grep -lE '^# kiro: throttled by the model service|^# exit 75 ' {} + 2>/dev/null; echo "(end of scan)"; } >> $D/run-counts-by-turn.txt
PREV=$D/ambient/setup.txt; [[ "$T" -ge 2 ]] && PREV=$D/ambient/turn-$(printf '%02d' $((T-1)))-after.txt
echo "--- ambient comparison turn $T (md5 lines)"
for f in $PREV $D/ambient/turn-$NN-before.txt $D/ambient/turn-$NN-after.txt; do echo "## ${f:t}"; grep -E 'listing md5|memories\.db' $f 2>/dev/null; done
# 2. counters, caps and checks
EC=$(grep -c 'is not available' $D/turn-$NN.stderr.txt 2>/dev/null); EC=${EC:-0}
SC=$( [[ -f $D/assistant-session-messages.jsonl ]] && python3 -B $H0/empty_calls.py $D/assistant-session-messages.jsonl || echo "0 (no session yet)")
echo "turn $NN: $SC so far (the session store); 'is not available' in turn-$NN.stderr.txt: $EC" >> $D/empty-calls.txt
echo "empty-argument calls after turn $T: $SC; stderr grep this turn: $EC"
python3 -B $H0/effort_stops.py $S/org --turn $T >> $D/effort-stops.txt 2>&1; tail -1 $D/effort-stops.txt
NRUNS=$( { [[ -d $S/org ]] && find $S/org -path '*/runs/*.log' -not -path '*/.git/*' 2>/dev/null; } | wc -l | tr -d ' ')
echo "org runs after turn $T: $NRUNS (cap 140, the injection window included)"
(( NRUNS >= 140 )) && echo "CAP: $NRUNS org runs after turn $T (cap 140, protocol 4.7): the stream ends at the end of this turn; it stays valid"
STAGE=1; [[ "$LABEL" == R[23]* || "$LABEL" == C[23]* ]] && STAGE=2
python3 -B $H0/running_credits.py $D $S --turn $T --stage $STAGE >> $D/credits-running.txt 2>&1; tail -1 $D/credits-running.txt
python3 -B $H0/requests_by_turn.py $S/org --turn $T >> $D/requests-by-turn.txt 2>&1; tail -2 $D/requests-by-turn.txt
# H2: the skill per arm, and no process of this stream from the other product
GS=$(zsh $H0/skill_move.sh status 2>&1 | head -1)
if [[ $ARM == C ]]; then
  [[ ! -e $HOME/.kiro/skills/hirearchy ]] && echo "skill (arm C) after turn $T: global copy aside: ok" >> $D/skill-check-turns.txt \
    || { echo "skill (arm C) after turn $T: global copy PRESENT ($GS)" >> $D/skill-check-turns.txt; echo "STOP: H2: the global skill is present during arm C's turn $T"; }
else
  [[ "$GS" == *"in place, md5 443e1bc4911aa4d6aaa6457e78f673c1"* ]] && echo "skill (arm R) after turn $T: global copy in place: ok" >> $D/skill-check-turns.txt \
    || { echo "skill (arm R) after turn $T: $GS" >> $D/skill-check-turns.txt; echo "STOP: H2: the global skill is not in place during arm R's turn $T"; }
fi
# the stream's processes: the scheduler (its pid file) and every process whose command names the sandbox (the injection's server, the
# org runs); each command's product directory (REPO_C's path, else REPO_R's or its /Users/aminalizadeh/workspace/hirearchy link) must be
# the arm's. The assistant's MCP server ends with each turn; its --directory is the profile copy's (setup.txt) and the probe's catalog.
SPID=$( [[ -f $S/org/.runtime/scheduler.pid ]] && tr -dc '0-9' < $S/org/.runtime/scheduler.pid )
OTHER=$( { [[ -n "$SPID" ]] && ps -o pid=,command= -p $SPID 2>/dev/null; ps -axo pid=,command= | grep -F "$SN" | grep -v grep; } | python3 -c "
import sys
R, C, A = '$REPO_R', '$REPO_C', '$REPO_A'
for ln in sys.stdin:
    d = C if C in ln else (R if (R in ln or '/Users/aminalizadeh/workspace/hirearchy' in ln) else None)
    if d and d != A: print(ln.strip()[:300])
")
[[ -z "$OTHER" ]] || { echo "STOP: H2: a process of this stream runs from the other product: $OTHER"; print -r -- "$OTHER" >> $D/harness-failures-product.txt; }
# 3. the snapshots, last
zsh $H0/quality_snapshot.sh $LABEL turn-$NN
zsh $H0/services_snapshot.sh $LABEL turn-$NN
[[ $ARM == R ]] && zsh $H0/retro_snapshot.sh $LABEL turn-$NN
exit 0
