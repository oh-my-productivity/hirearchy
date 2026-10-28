#!/bin/zsh
# C1 per-attempt setup, P1 M1 form (design 6.1 Setup 1-2 + the sandbox kiro-cli-chat symlink). Usage: setup.sh <variant> [mkprofile.py extra args...]; prints EPOCH.
# P1 changes from C1's: WT = the merged repo; sandbox prefix /tmp/hirearchy-p1-detach-; NO dedicated kiro home (no SB/kiro-home, no KIRO_HOME):
# the profile is the study's own ~/.kiro/agents/hirearchy-study-p1-detach-<epoch>.json (mkprofile.py), validated with the owner's kiro home.
WT=/Volumes/workspace/hirearchy
TOOLS=/Volumes/workspace/hirearchy/studies/P1-itemized-playbook/evidence/preflight/c1-tools
VARIANT=$1; shift
EPOCH=$(date +%s); SB=/tmp/hirearchy-p1-detach-$EPOCH; echo "EPOCH=$EPOCH"
mkdir -p $SB/home/.local/bin $SB/profile $SB/kiro-state $SB/logs $SB/samples $SB/out
ln -s /Users/aminalizadeh/.local/bin/kiro-cli-chat $SB/home/.local/bin/kiro-cli-chat
cp $TOOLS/*.py $SB/
# the streams' workspace bytes (protocol 3): the settings file, so that the check runs under the same chat settings as a stream
mkdir -p $SB/.kiro/settings $SB/.kiro/skills/hirearchy
cp -p /Volumes/workspace/hirearchy/studies/P1-itemized-playbook/evidence/harness/workspace-cli.json $SB/.kiro/settings/cli.json
cp -p $WT/skills/hirearchy/SKILL.md $SB/.kiro/skills/hirearchy/SKILL.md
cd $SB
h() { HIREARCHY_STATE_DIR=$SB/kiro-state $WT/.venv/bin/hirearchy "$@"; }
h init $SB/org --mission "P1 preflight scheduler check (throwaway)" --model claude-sonnet-5.5 >/dev/null 2>&1; echo init $?
h --root $SB/org hire root ceo --role CEO --charter "Throwaway reproduction agent." >/dev/null 2>&1; echo hire $?
h --root $SB/org task ceo --title "Reproduction" --goal "Write a 300-word note about rivers into ceo/MEMORY.md with the write tool, then report done." --acceptance "the note exists" --budget 2 >/dev/null 2>&1; echo task $?
$WT/.venv/bin/python -I $SB/mkprofile.py --sb $SB --epoch $EPOCH --variant $VARIANT "$@" | python3 -c "import json,sys; d=json.load(sys.stdin); s=d['mcpServers']['hirearchy']; print('server:', s['command'], s['args'], 'env keys:', sorted(s['env'])); print('tools:', d['tools'])"
env -u KIRO_HOME kiro-cli agent validate --path $HOME/.kiro/agents/hirearchy-study-p1-detach-$EPOCH.json >/dev/null 2>&1; echo "validate $?"
HOME=$SB/home env -u KIRO_HOME kiro-cli chat --help </dev/null >/dev/null 2>&1; echo "chat-help $?"
