#!/bin/zsh
# Preflight scheduler check (no LLM at the assistant level): the arm's own MCP server `start` (until_done=false) on a throwaway org; the client
# process exits; the scheduler must survive it (ppid 1, alive 5 s and 25 s after the client's exit), the run must end ok, and `stop` must record
# scheduler.signal then scheduler.exit. Usage: scheduler-check.sh <R|C>
H=/Volumes/workspace/hirearchy/studies/P2-retro-and-growth/evidence/harness; source $H/arm.sh preflight-$1 || exit 2
D=$EV/preflight/scheduler-check/$1; mkdir -p $D; S=$P/preflight-sched-$1-$(date +%s); mkdir -p $S; echo $S > $D/sandbox-path.txt
"${HIR[@]}" init $S/org --mission "Scheduler check."  > $D/setup.txt 2>&1
"${HIR[@]}" --root $S/org hire root lead --role "Writer" --charter "Answers one question per task in one line." >> $D/setup.txt 2>&1
"${HIR[@]}" --root $S/org task lead --title "Say hello" --goal "Reply with the word hello." --acceptance "The reply is hello." --budget 2 >> $D/setup.txt 2>&1
MC="env -u KIRO_HOME uv --directory $REPO_A run python $H/mcp_call.py --repo $REPO_A --org $S/org"
echo "start call $(date -u +%FT%TZ)" > $D/log.txt
$MC --tool start --args '{"until_done": false}' >> $D/log.txt 2>&1; echo "start exit $? at $(date -u +%FT%TZ) (client exited)" >> $D/log.txt
sleep 1
PID=$(grep -h '"kind":"scheduler.start"' $S/org/.runtime/events/*/scheduler-*.jsonl | head -1 | python3 -c "import sys,json;print(json.loads(sys.stdin.readline())['pid'])")
echo "scheduler pid $PID" >> $D/log.txt
for t in 5 25; do sleep $(( t == 5 ? 4 : 20 )); echo "+${t}s: $(date -u +%FT%TZ) $(ps -o pid=,ppid=,stat=,command= -p $PID 2>&1 | cut -c1-110)" >> $D/log.txt; done
ps -o pid=,ppid=,stat=,command= -p $PID > $D/ps-before-stop.txt 2>&1
for i in {1..40}; do grep -q '"kind":"run.end"' $S/org/.runtime/events/*/scheduler-*.jsonl 2>/dev/null && break; sleep 3; done
grep -h '"kind":"run.end"' $S/org/.runtime/events/*/scheduler-*.jsonl >> $D/log.txt
$MC --tool stop --args '{}' >> $D/log.txt 2>&1; echo "stop exit $? at $(date -u +%FT%TZ)" >> $D/log.txt
sleep 3
grep -h '"kind":"scheduler\.\(signal\|exit\|start\)"' $S/org/.runtime/events/*/scheduler-*.jsonl | cut -c1-260 >> $D/log.txt
echo "process after stop: $(ps -o pid=,stat= -p $PID 2>&1)" >> $D/log.txt
ps aux | grep -F "$S" | grep -v grep >> $D/log.txt
zsh $H/model_check.sh org preflight-$1-sched $S | tail -2 >> $D/log.txt
