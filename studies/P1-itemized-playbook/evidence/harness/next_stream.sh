#!/bin/zsh
# P1 order and stage gate (protocol 1, 8, 11; design 18.2, 18.7). Usage: next_stream.sh      prints the next stream label, or a refusal
# The pre-registered order is F1, I1 | I2, F2, F3, I3 (the bar is the stage gate). A replacement <label>r (at most one per arm, protocol 8) runs
# immediately after the stream it replaces, before the next label, and only when evidence/manager-decision-replacement-<label>.md exists
# (the manager's approval, with the owner's OK for its extra credits). A stream is done when its finish-steps.txt has an "ended" line.
# Refusals (each printed as `REFUSED: ...`, exit 3), checked for every done stream, replacements included:
#   - its memories-db.txt says CHANGED and evidence/manager-decision-memories-<label>.md does not exist (protocol 8: a change DURING it; a
#     change BETWEEN two streams is stopped by setup_stream.sh's memories gate, memories_gate.py, before the next stream creates anything);
#   - its credits.txt has no `stream total credits:` line (cost_total.py; protocol 11): no figure, no next stream;
#   - it is a stage-2 stream (I2, F2, F3, I3, or a replacement of one) over 185.00 credits and evidence/manager-decision-cost-<label>.md does
#     not exist (design 18.7: the study pauses for the owner);
#   - stage 2 (I2) before evidence/stage-1-gate.md AND evidence/manager-decision-stage-2.md (the manager's yes) exist;
#   - two replacement approvals in one arm.
# It creates nothing; the stream step runs setup_stream.sh <label> itself.
EV=${P1_NEXT_STREAM_EV:-/Volumes/workspace/hirearchy/studies/P1-itemized-playbook/evidence}  # the override is next_stream_check.py's only
H=/Volumes/workspace/hirearchy/studies/P1-itemized-playbook/evidence/harness
ORDER=(F1 I1 I2 F2 F3 I3)
for A in F I; do
  rep=($EV/manager-decision-replacement-${A}[1-3].md(N))
  (( ${#rep} > 1 )) && { echo "REFUSED: ${#rep} replacement approvals in arm $A (${(j:, :)${rep[@]:t}}): at most one replacement stream per arm (protocol 8)"; exit 3; }
done
SEQ=()
for L in $ORDER; do SEQ+=($L); [[ -f $EV/manager-decision-replacement-$L.md ]] && SEQ+=(${L}r); done
done_() { [[ -f $EV/$1/finish-steps.txt ]] && grep -q 'ended' $EV/$1/finish-steps.txt; }
stage2() { [[ ${1%r} == (I2|F2|F3|I3) ]]; }
for L in $SEQ; do
  if done_ $L; then
    if grep -q CHANGED $EV/$L/memories-db.txt 2>/dev/null && [[ ! -f $EV/manager-decision-memories-$L.md ]]; then
      echo "REFUSED: memories.db changed during $L: the manager decides before the next stream (protocol 8)"; exit 3; fi
    python3 -B $H/cost_total.py --over 185 $EV/$L/credits.txt; rc=$?
    if (( rc == 2 )); then
      echo "REFUSED: $L has no 'stream total credits:' line in credits.txt (protocol 11): run cost_total.py on its cost.txt first"; exit 3; fi
    if stage2 $L && (( rc == 0 )) && [[ ! -f $EV/manager-decision-cost-$L.md ]]; then
      echo "REFUSED: $L cost $(grep -o 'stream total credits: [0-9.]*' $EV/$L/credits.txt | grep -o '[0-9.]*$') credits (> 185.00): the study pauses for the owner (design 18.7)"; exit 3; fi
    continue
  fi
  if [[ $L == I2 && ! ( -f $EV/stage-1-gate.md && -f $EV/manager-decision-stage-2.md ) ]]; then
    echo "REFUSED: stage 2 needs evidence/stage-1-gate.md and the manager's yes in evidence/manager-decision-stage-2.md (design 18.7)"; exit 3; fi
  echo "$L"; exit 0
done
echo "all streams are done"; exit 0
