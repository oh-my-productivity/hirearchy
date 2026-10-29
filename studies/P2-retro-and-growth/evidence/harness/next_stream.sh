#!/bin/zsh
# P2 next stream in the pre-registered order R1, C1 | R2, C2, R3, C3 (protocol 1, 8, 11). Usage: next_stream.sh   -> prints the label, or REFUSED
# Refuses (exit 4) when: the md5 gate fails; a skill move has no restore; the last finished stream has no `stream total credits:` line;
# memories.db changed during the last stream without EV/manager-decision-memories-before-<next label>.md (the one name memories_gate.py and
# protocol 3.1 and 8 use; F37 of review 2); stage 2 is next without EV/stage-1-gate.md and
# EV/manager-decision-stage-2.md; the last stage-2 stream is over 260.00 credits without EV/manager-decision-cost-<label>.md; a stream of the
# order is set up but not finished. A replacement <label>r comes right after <label> when EV/manager-decision-replacement-<label>.md exists.
H0=${0:A:h}
source $H0/arm.sh R1 >/dev/null || exit 2
md5gate_ok > /dev/null 2>&1 || { echo "REFUSED: the md5 gate fails (protocol 0)"; exit 4; }
zsh $H0/skill_move.sh status > /dev/null 2>&1 || { echo "REFUSED: a skill move has no restore: $(zsh $H0/skill_move.sh status | grep UNRESTORED)"; exit 4; }
SEQ=(); for l in $ORDER; do SEQ+=($l); [[ -f $EV/manager-decision-replacement-$l.md ]] && SEQ+=(${l}r); done
prev=""
for l in $SEQ; do
  D=$EV/$l
  if [[ ! -f $D/sandbox-path.txt ]]; then
    if [[ -n "$prev" ]]; then
      PD=$EV/$prev
      grep -q '^stream total credits:' $PD/credits.txt 2>/dev/null || { echo "REFUSED: $prev has no credits line"; exit 4; }
      if grep -q CHANGED $PD/memories-db.txt 2>/dev/null && [[ ! -f $EV/manager-decision-memories-before-$l.md ]]; then
        echo "REFUSED: memories.db changed during $prev: $l needs $EV/manager-decision-memories-before-$l.md"; exit 4; fi
      if [[ "$prev" == R[23]* || "$prev" == C[23]* ]] && python3 -B $H0/cost_total.py --over 260 $PD/credits.txt > /dev/null 2>&1 && [[ ! -f $EV/manager-decision-cost-$prev.md ]]; then
        echo "REFUSED: $prev is over 260 credits (stage 2): it needs $EV/manager-decision-cost-$prev.md"; exit 4; fi
    fi
    if [[ "$l" == R2 || "$l" == C2 || "$l" == R3 || "$l" == C3 ]]; then
      [[ -f $EV/stage-1-gate.md && -f $EV/manager-decision-stage-2.md ]] || { echo "REFUSED: stage 2 needs $EV/stage-1-gate.md and $EV/manager-decision-stage-2.md (protocol 11)"; exit 4; }
    fi
    echo "$l"; exit 0
  fi
  grep -q '^# finish_stream.sh .* ended' $D/finish-steps.txt 2>/dev/null || { echo "REFUSED: $l is set up but not finished"; exit 4; }
  prev=$l
done
echo "DONE: every stream of the order has run"; exit 0
