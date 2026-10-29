#!/bin/zsh
# Facilitator's driver (not a harness file; it only calls the frozen turn.sh once per turn). Usage: go.sh <n>
T=$1; NN=$(printf '%02d' $T); E=/Volumes/workspace/hirearchy/studies/P2-retro-and-growth/evidence; D=$E/R1
[[ -f $D/lines/turn-$NN.txt && -f $D/lines/turn-$NN.rec ]] || { echo "missing lines/turn-$NN.txt or .rec"; exit 2; }
grep -q "^turn $T |" $D/lena-lines.txt 2>/dev/null || cat $D/lines/turn-$NN.rec >> $D/lena-lines.txt
python3 -B -c "import sys; sys.path.insert(0,'$E/harness'); import lena_lines as L; r=L.parse_line(open('$D/lena-lines.txt').read().splitlines()[-1]); print('parsed turn', r['turn'], r['rules'], 'rows', r['rows'], 'unknown:', r['unknown_rules'])"
env -u KIRO_HOME zsh $E/harness/turn.sh R1 $T $D/lines/turn-$NN.txt > /tmp/hirearchy-p2/r1b-turn-$NN.console.txt 2>&1; echo "turn.sh exit $?"
grep -n "STOP\|CAP:\|CREDITS\|effort stops\|empty-arg\|org runs after\|sequential\|running credits\|NOTE" /tmp/hirearchy-p2/r1b-turn-$NN.console.txt | cut -c1-260
sed -n '/ASSISTANT/,$p' $D/turn-$NN.txt | cut -c1-${CUT:-1800} | head -${LINES_MAX:-80}
