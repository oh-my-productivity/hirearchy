#!/bin/zsh
# C1 per-attempt setup (design 6.1 Setup 1-2 + the sandbox kiro-cli-chat symlink). Usage: setup.sh <variant> [mkprofile.py extra args...]; prints EPOCH.
WT=/Volumes/workspace/hirearchy
VARIANT=$1; shift
EPOCH=$(date +%s); SB=/tmp/hirearchy-e7-detach-$EPOCH; echo "EPOCH=$EPOCH"
mkdir -p $SB/home/.local/bin $SB/kiro-home/agents $SB/kiro-state $SB/logs $SB/samples $SB/out
ln -s /Users/aminalizadeh/.local/bin/kiro-cli-chat $SB/home/.local/bin/kiro-cli-chat
cp /Volumes/workspace/hirearchy/studies/E7-org-growth-0a4-recheck/evidence/preflight/c1-tools/*.py $SB/
cd $SB
h() { HIREARCHY_STATE_DIR=$SB/kiro-state $WT/.venv/bin/hirearchy "$@"; }
h init $SB/org --mission "0a.4 C1 reproduction (throwaway)" --model claude-sonnet-5.5 >/dev/null 2>&1; echo init $?
h --root $SB/org hire root ceo --role CEO --charter "Throwaway reproduction agent." >/dev/null 2>&1; echo hire $?
h --root $SB/org task ceo --title "Reproduction" --goal "Write a 300-word note about rivers into ceo/MEMORY.md with the write tool, then report done." --acceptance "the note exists" --budget 2 >/dev/null 2>&1; echo task $?
$WT/.venv/bin/python -I $SB/mkprofile.py --sb $SB --epoch $EPOCH --variant $VARIANT "$@" | python3 -c "import json,sys; d=json.load(sys.stdin); s=d['mcpServers']['hirearchy']; print('server:', s['command'], s['args'], 'env keys:', sorted(s['env'])); print('tools:', d['tools'])"
KIRO_HOME=$SB/kiro-home kiro-cli agent validate --path $SB/kiro-home/agents/c1-$EPOCH.json >/dev/null 2>&1; echo "validate $?"
HOME=$SB/home kiro-cli chat --help </dev/null >/dev/null 2>&1; echo "chat-help $?"
