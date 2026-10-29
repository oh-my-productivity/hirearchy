#!/bin/zsh
# Facilitator's driver (not a harness file; it only calls the frozen turn.sh once per turn). Usage: go.sh <n>
# Reads lines/turn-NN.txt (Lena's line, verbatim) and lines/turn-NN.rec (the lena-lines.txt record), appends the record, checks it with
# the frozen parser, sends the turn with ONE turn.sh call, prints the gating lines, runs seqcheck.py and shows the assistant's reply (cut).
T=$1; NN=$(printf '%02d' $T); E=/Volumes/workspace/hirearchy/studies/P2-retro-and-growth/evidence; D=$E/R1
[[ -f $D/lines/turn-$NN.txt && -f $D/lines/turn-$NN.rec ]] || { echo "missing lines/turn-$NN.txt or .rec"; exit 2; }
grep -q "^turn $T |" $D/lena-lines.txt || cat $D/lines/turn-$NN.rec >> $D/lena-lines.txt
python3 -B -c "import sys; sys.path.insert(0,'$E/harness'); import lena_lines as L; r=L.parse_line(open('$D/lena-lines.txt').read().splitlines()[-1]); print('parsed turn', r['turn'], r['rules'], 'unknown:', r['unknown_rules'])"
env -u KIRO_HOME zsh $E/harness/turn.sh R1 $T $D/lines/turn-$NN.txt > /tmp/hirearchy-p2/r1-turn-$NN.console.txt 2>&1; echo "turn.sh exit $?"
grep -n "STOP\|CAP:\|CREDITS\|effort stops\|empty-arg\|org runs after\|sequential\|running credits\|NOTE" /tmp/hirearchy-p2/r1-turn-$NN.console.txt | cut -c1-260
python3 $D/facilitator/seqcheck.py $D $T | tee -a $D/seqcheck.txt
sed -n '/ASSISTANT/,$p' $D/turn-$NN.txt | cut -c1-${CUT:-1500} | head -${LINES_MAX:-70}
