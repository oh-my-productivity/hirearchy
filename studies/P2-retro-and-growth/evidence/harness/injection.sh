#!/bin/zsh
# P2 injection (A-R; protocol 3.4; E7 5 unchanged). Usage: injection.sh <label> <memo-1 task id> [--dry-run|--selftest|--stop|--poll-check ...]
# Arm R: `uv --directory REPO_R run python H/inject_root_rework.py --org S/org --revises <id> --out S/injection` (E7's file, md5 pinned).
# Arm C: the same with REPO_C and H/inject_root_rework_armc.py (E7's file with line 36 only changed), so its MCP server and its text source
# are the worktree's. KIRO_HOME is unset; the output goes to <label>/injection-call.txt. After the injection itself (no mode flag but
# --force) it writes S/injection/window.txt from the log with injection_window.py (protocol amendment 1 item 5 (C)).
LABEL="$1"; shift
H0=${0:A:h}
source $H0/arm.sh "$LABEL" || exit 2
D=$EV/$LABEL; [[ "$LABEL" == selfcheck-* && -n "$P2_EVDIR" ]] && D=$P2_EVDIR; [[ "$LABEL" == preflight-* ]] && D=$EV/preflight/$LABEL
S=$(cat $D/sandbox-path.txt)
SCRIPT=$H0/inject_root_rework.py; [[ $ARM == C ]] && SCRIPT=$H0/inject_root_rework_armc.py
REV=(); [[ -n "$1" && "$1" != --* ]] && { REV=(--revises "$1"); shift; }
mkdir -p $D
echo "injection $(date -u +%FT%TZ): arm $ARM script ${SCRIPT:t} md5 $(md5 -q $SCRIPT) product $REPO_A args $REV $*" >> $D/injection-call.txt
env -u KIRO_HOME uv --directory $REPO_A run python $SCRIPT --org $S/org $REV --out $S/injection "$@" 2>&1 | tee -a $D/injection-call.txt
rc=${pipestatus[1]}
# protocol amendment 1 item 5 (C): after the injection itself (no mode flag), write S/injection/window.txt from the log (E7 5.3's last
# bullet), so no facilitator step is needed; a log without a window end, or an existing different window.txt, prints a NOTE or STOP line
if [[ $# -eq 0 && ${#REV} -gt 0 ]] || [[ $# -eq 1 && "$1" == --force && ${#REV} -gt 0 ]]; then
  python3 -B $H0/injection_window.py $S/injection 2>&1 | tee -a $D/injection-call.txt
fi
exit $rc
