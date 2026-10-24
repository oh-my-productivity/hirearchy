#!/bin/zsh
# facilitator helper (s3): usage after_turn.sh <turn n>   -- no MCP/CLI call against the org
N=3; T="$1"
EV=/Volumes/workspace/hirearchy/studies/E5-org-growth-0a2-recheck/evidence
D=$EV/s$N; S=$(cat $D/sandbox-path.txt)
python3 $EV/harness/org_state.py $S "after turn $T" >> $D/run-counts-by-turn.txt 2>&1
python3 - "$S" "$D" <<'PY'
import json,glob,os,sys,shutil
S,D=sys.argv[1:3]; real=os.path.realpath(S)
best=None
for p in glob.glob(os.path.expanduser('~/.kiro/sessions/*/sess_*/session.json')):
    try: j=json.load(open(p))
    except Exception: continue
    if j.get('agentMode')==f'hirearchy-study-e5-s3-assistant' and (j.get('workspacePaths') or [''])[0] in (real,S):
        best=p
if not best: print('NO SESSION FOUND'); sys.exit(1)
shutil.copy2(best,D+'/assistant-session.json'); shutil.copy2(os.path.dirname(best)+'/messages.jsonl',D+'/assistant-session-messages.jsonl')
print('session copied from',best)
PY
zsh $EV/harness/model_check.sh org $N $S | tail -3
zsh $EV/harness/model_check.sh assistant $N $S | tail -8
tail -25 $D/run-counts-by-turn.txt
