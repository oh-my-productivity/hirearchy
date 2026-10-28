#!/bin/zsh
# C1 verdict call, P1 M1 form: after.sh <SB> <ID> <turn> [--c1b]. Waits for .done, copies the attempt's own session record out of the owner's ~/.kiro/sessions
# (read only, matched by agentMode = the attempt's profile and workspacePaths[0] = SB/home's cwd SB), runs verdict/summary/allowed/timeline, archives under preflight/detach/samples/<ID>/.
SB=$1; ID=$2; T=$3; shift 3
WT=/Volumes/workspace/hirearchy; PY="$WT/.venv/bin/python -I"; A=/Volumes/workspace/hirearchy/studies/P1-itemized-playbook/evidence/preflight/detach/samples/$ID
PROFILE=hirearchy-study-p1-detach-${SB##*-}
for i in {1..60}; do [[ -f $SB/samples/$ID-turn$T.done ]] && break; sleep 1; done
mkdir -p $A $SB/session-record
python3 - "$SB" "$PROFILE" <<'PYS'
import glob, json, os, shutil, sys
sb, prof = sys.argv[1:3]
real = os.path.realpath(sb)
for p in glob.glob(os.path.expanduser('~/.kiro/sessions/*/sess_*/session.json')):
    try: j = json.load(open(p))
    except Exception: continue
    if j.get('agentMode') == prof and (j.get('workspacePaths') or [''])[0] in (real, sb):
        d = os.path.join(sb, 'session-record', os.path.basename(os.path.dirname(p)))
        os.makedirs(d, exist_ok=True)
        shutil.copy2(p, d + '/session.json'); shutil.copy2(os.path.dirname(p) + '/messages.jsonl', d + '/messages.jsonl')
        print('session record copied:', p)
PYS
$=PY $SB/verdict.py --sb $SB --attempt $ID --turn $T "$@" > /dev/null
$=PY $SB/summary.py --sb $SB --attempt $ID --turn $T > $A/summary-turn$T.md
$=PY $SB/allowed.py --kiro-home $SB/session-record > $A/allowed.txt
python3 /Volumes/workspace/hirearchy/studies/P1-itemized-playbook/evidence/preflight/c1-tools/timeline.py $SB/samples/$ID-turn$T.jsonl > $A/timeline-turn$T.txt
cp $SB/samples/$ID-turn$T* $SB/out/$ID-turn$T* $SB/logs/$ID-turn$T* $A/ 2>/dev/null
tail -1 $A/allowed.txt
python3 - <<P
import json
v=json.load(open('$SB/samples/$ID-turn$T.verdict.json'))
for k in ['return','scheduler_pid','run_start_to_return_ms','scheduler_alive_at_plus_5s','run_alive_at_plus_5s','scheduler_last_sample_alive','scheduler_first_sample_gone','scheduler_gone_relative_to_return_ms','scheduler_last_alive_stat_ppid_pgid','run_last_sample_alive','run_first_sample_gone','scheduler.exit','scheduler.signal','run.end','verdict','why','valid','c1b']:
    if k in v: print(k, v[k])
P
echo "run started in run logs:"; grep -c "run started" $SB/org/*/runs/*.log 2>/dev/null | head -3
echo "--- stdout:"; head -c 300 $SB/out/$ID-turn$T.stdout; echo
