#!/bin/zsh
# P2 the measures' inputs of one finished stream, in a fixed order (protocol 11 "The gate's inputs" and 12.5; F36 of review 2).
# Usage: score_stream.sh <label>          (a selfcheck-* label reads and writes the evidence folder $P2_EVDIR, as copy_org_evidence.sh does;
#                                          the dry run runs it so, in both arms: C5 of the closing decision, on F42 of review 3)
# Run by the stage gate (step 6) for R1 and C1 before `stage_gate.py EV`, and by the scoring step (step 12) for every stream before
# `aggregate.py`, after step 12 has filled <label>/measures/judged.json (at the gate it does not exist yet, so the judged keys read NOT
# DETERMINED without the FAIL-CLOSED prefix: information, not a stop). Each command's argv and exit code go into <label>/score-steps.txt;
# a failed command is listed and the next one still runs; exit 1 if any failed.
#  1. python3 -B extract_p2.py EV/<label> --checks      -> p2/<check>.json, p2/verdicts.txt (arm C: the reported measures only)
#  2. zsh watch_views.sh EV/<label>                      -> watch-views/<owner>--<name>/, watch/<owner>--<name>/ (P1's rederive_watch.py)
#  3. python3 -B score_p2.py EV/<label> --out EV/<label>/measures [--am-time <the A-M line's turn start>]   -> measures/score_p2.json
#  4. python3 -B gate_p1.py EV/<label>                   -> p2/gate_p1.json (P1's gate-able measures, 12.3)
LABEL="$1"; H0=${0:A:h}
[[ -n "$LABEL" ]] || { echo "usage: score_stream.sh <label>" >&2; exit 2; }
source $H0/arm.sh "$LABEL" > /dev/null || exit 2
D=$EV/$LABEL; [[ "$LABEL" == selfcheck-* && -n "$P2_EVDIR" ]] && D=${P2_EVDIR:A}; [[ -f $D/sandbox-path.txt ]] || { echo "score_stream.sh: $D is not a stream's evidence folder" >&2; exit 2; }
LOGF=$D/score-steps.txt; nfail=0
echo "# score_stream.sh $LABEL started $(date -u +%FT%TZ)" >> $LOGF
run() { local out="$1"; shift; "$@" > "$out" 2>&1; local rc=$?; echo "exit $rc: $* -> ${out#$D/}" >> $LOGF
  if (( rc != 0 )); then nfail=$((nfail+1)); echo "FAILED: $*"; else echo "ok: ${out#$D/}"; fi; }
# the A-M line's turn start (protocol 4.2: memo 6's versions after it are judged by the new order), read from lena-lines.txt and turn-times.txt
AMT=$(python3 -B - "$D" <<'PY'
import re, sys
from pathlib import Path
d = Path(sys.argv[1])
lines = (d / "lena-lines.txt").read_text().splitlines() if (d / "lena-lines.txt").is_file() else []
t = next((int(m.group(1)) for ln in lines for m in [re.match(r"^turn (\d+) \| rules (.*?) \|", ln)] if m and "A-M@2026-11-09" in m.group(2).split(" + ")), None)
tt = (d / "turn-times.txt").read_text().splitlines() if (d / "turn-times.txt").is_file() else []
print(next((m.group(2) for ln in tt for m in [re.match(r"^turn (\d+): .*utc (\S+) - ", ln)] if m and int(m.group(1)) == t), "") if t else "")
PY
)
mkdir -p $D/measures
run $D/score-extract_p2-checks.txt python3 -B $H0/extract_p2.py $D --checks
run $D/score-watch_views.txt zsh $H0/watch_views.sh $D
if [[ -n "$AMT" ]]; then run $D/measures/score_p2-output.txt python3 -B $H0/score_p2.py $D --out $D/measures --am-time "$AMT"
else run $D/measures/score_p2-output.txt python3 -B $H0/score_p2.py $D --out $D/measures; fi
run $D/score-gate_p1.txt python3 -B $H0/gate_p1.py $D
echo "# score_stream.sh $LABEL ended $(date -u +%FT%TZ); failed: $nfail" >> $LOGF
echo "score_stream $LABEL: $nfail failed command(s)"
(( nfail == 0 ))
