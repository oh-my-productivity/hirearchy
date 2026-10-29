#!/bin/zsh
# P2: ONE wrapper per turn (F-P1-14; protocol 3.2). Usage: turn.sh <label> <turn n> <absolute prompt file>
# Runs run_turn.sh, then after_turn.sh, in sequence, in this one call, so a stream step cannot start them together. Refuses:
#   - KIRO_HOME set in this shell; the md5 gate failing (a stream label; protocol 0); an unrestored skill move of another label;
#   - turn n when turn n-1 has no after_turn record (after-turn-NN.done) or turn n already ran (turn-NN.txt exists).
# Writes turn-NN.wrapper.txt: both parts' UTC start and end and exit codes, and the sequence check: the first snapshot of after_turn.sh
# (quality/calls.txt line `turn-NN start ...`) started after the turn's end plus the boundary (`after_turn sequential: checked`), else
# `STOP: snapshot before the boundary`. Prints run_turn's and after_turn's output; a `STOP:` line means: stop at the end of this turn.
LABEL="$1"; T="$2"; PF="$3"
H0=${0:A:h}
source $H0/arm.sh "$LABEL" || exit 2
[[ $# -eq 3 && "$T" =~ '^[1-9][0-9]*$' && -f "$PF" && "$PF" == /* ]] || { echo "usage: turn.sh <label> <turn> <absolute prompt file>" >&2; exit 2; }
[[ -z "${KIRO_HOME+set}" ]] || { echo "REFUSED: KIRO_HOME is set in this shell (protocol 1)" >&2; exit 91; }
D=$EV/$LABEL; [[ "$LABEL" == selfcheck-* && -n "$P2_EVDIR" ]] && D=$P2_EVDIR
[[ -f $D/sandbox-path.txt ]] || { echo "REFUSED: $D/sandbox-path.txt missing: run setup_stream.sh first" >&2; exit 2; }
if [[ "$LABEL" =~ $STREAM_RE ]]; then
  md5gate_ok > $D/turn-md5gate.txt 2>&1 || { cat $D/turn-md5gate.txt; echo "STOP: the md5 gate failed before turn $T (protocol 0)"; exit 3; }
fi
UNR=$(zsh $H0/skill_move.sh status 2>/dev/null | awk '$1=="UNRESTORED"{print $2}' | grep -v -x -- "$LABEL")
[[ -z "$UNR" ]] || { echo "REFUSED: an unrestored skill move of another label ($UNR): run skill_move.sh recover first (protocol 3.6)" >&2; exit 92; }
NN=$(printf '%02d' "$T"); PREV=$(printf '%02d' $((T-1)))
[[ ! -f $D/turn-$NN.txt ]] || { echo "REFUSED: turn $T ran already ($D/turn-$NN.txt)" >&2; exit 4; }
(( T == 1 )) || [[ -f $D/after-turn-$PREV.done ]] || { echo "REFUSED: turn $((T-1)) has no after_turn record ($D/after-turn-$PREV.done)" >&2; exit 4; }
S=$(cat $D/sandbox-path.txt)
W=$D/turn-$NN.wrapper.txt
echo "turn.sh $LABEL $T: run_turn start $(date -u +%FT%T.%6NZ 2>/dev/null || date -u +%FT%TZ)" > $W
P2_TURN_WRAPPER=1 zsh $H0/run_turn.sh "$S" "$LABEL" "$T" "$PF"; rc1=$?
echo "run_turn end $(date -u +%FT%TZ) exit $rc1" >> $W
P2_TURN_WRAPPER=1 zsh $H0/after_turn.sh "$LABEL" "$T" 2>&1 | tee $D/after-turn-$NN.out; rc2=${pipestatus[1]}
echo "after_turn end $(date -u +%FT%TZ) exit $rc2" >> $W
# the sequence check: the turn's end + boundary (turn-times.txt) <= the first snapshot's start (quality/calls.txt); turn_seqcheck.py parses
# ISO 8601 offsets and fails closed on an unparseable time or a missing record (protocol amendment 1 item 5 (A))
python3 -B $H0/turn_seqcheck.py "$D" "$T" >> $W 2>&1 || echo "STOP: the sequence check could not run (turn_seqcheck.py exit $?)" >> $W
tail -1 $W
(( rc2 == 0 )) && touch $D/after-turn-$NN.done
exit $rc1
