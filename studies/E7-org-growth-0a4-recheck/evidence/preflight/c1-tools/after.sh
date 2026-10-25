#!/bin/zsh
# C1 verdict call: after.sh <SB> <ID> <turn> [--c1b]. Waits for .done, runs verdict/summary/allowed/timeline, archives the sandbox data under c1-tools/samples/<ID>/.
SB=$1; ID=$2; T=$3; shift 3
WT=/Volumes/workspace/hirearchy; PY="$WT/.venv/bin/python -I"; A=/Volumes/workspace/hirearchy/studies/E7-org-growth-0a4-recheck/evidence/preflight/detach/samples/$ID
for i in {1..60}; do [[ -f $SB/samples/$ID-turn$T.done ]] && break; sleep 1; done
mkdir -p $A
$=PY $SB/verdict.py --sb $SB --attempt $ID --turn $T "$@" > /dev/null
$=PY $SB/summary.py --sb $SB --attempt $ID --turn $T > $A/summary-turn$T.md
$=PY $SB/allowed.py --kiro-home $SB/kiro-home > $A/allowed.txt
python3 /Volumes/workspace/hirearchy/studies/E7-org-growth-0a4-recheck/evidence/preflight/c1-tools/timeline.py $SB/samples/$ID-turn$T.jsonl > $A/timeline-turn$T.txt
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
