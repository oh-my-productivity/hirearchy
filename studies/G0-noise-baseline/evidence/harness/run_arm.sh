#!/bin/zsh
# G0 arm driver (design 20.1 "Repeats": `run_arm.sh <arm> <k>` starts at the arm's next stream number). Usage:
#   run_arm.sh <arm> <k>            print the next k stream labels of the arm and, per label, the command sequence of protocol 6
#   run_arm.sh <arm> 1 --setup      run setup_stream.sh for the next label; print the label and its sandbox path S
# <arm> is m0 or m1. The next stream number is one more than the highest <arm>-s<n> evidence directory (a replacement directory <arm>-s<n>r,
# <arm>-s<n>r2 does not count; neither does a plain file); with none, 1. It NEVER runs a turn: the turns are the facilitator's, one tool call
# each (protocol 4.2.1). The evidence root is $EV; the environment variable G0_RUN_ARM_EV overrides it for the label computation ONLY (tests).
# Exit 2: usage (bad arm, k not a positive integer, --setup with k other than 1, unknown option).
REPO=/Volumes/workspace/hirearchy
ST=$REPO/studies/G0-noise-baseline
EV=$ST/evidence
H=$EV/harness

ARM="$1"; K="$2"; OPT="$3"
usage() { echo "usage: run_arm.sh <m0|m1> <k> [--setup]   (--setup needs k = 1)" >&2; exit 2; }
[[ $# -eq 2 || $# -eq 3 ]] || usage
[[ "$ARM" == m0 || "$ARM" == m1 ]] || usage
[[ "$K" =~ '^[1-9][0-9]*$' ]] || usage
SETUP=0
if [[ -n "$OPT" ]]; then
  [[ "$OPT" == "--setup" ]] || usage
  [[ "$K" == 1 ]] || { echo "run_arm.sh: --setup needs k = 1 (one stream at a time)" >&2; usage; }
  SETUP=1
fi

LEV=${G0_RUN_ARM_EV:-$EV}
HIGH=0
for d in "$LEV"/${ARM}-s*(/N); do
  n=${d:t}
  [[ "$n" =~ "^${ARM}-s([0-9]+)\$" ]] || continue
  (( match[1] > HIGH )) && HIGH=${match[1]}
done
LABELS=()
for ((i = 1; i <= K; i++)); do LABELS+=("${ARM}-s$((HIGH + i))"); done

if [[ $SETUP -eq 1 ]]; then
  LABEL=${LABELS[1]}
  zsh "$H/setup_stream.sh" "$LABEL" || { rc=$?; echo "run_arm.sh: setup_stream.sh $LABEL failed (exit $rc)" >&2; exit $rc; }
  echo "label: $LABEL"
  echo "S: $(cat "$EV/$LABEL/sandbox-path.txt")"
  exit 0
fi

echo "next labels: ${LABELS[*]}"
echo "(arm $ARM; replacement streams are named <arm>-s<n>r, then r2, and are set up with setup_stream.sh <label> directly; the arms are interleaved M0, M1, M0, ... per design 20.3)"
for LABEL in $LABELS; do
  D=$EV/$LABEL
  cat <<EOF

== $LABEL
S = the path in $D/sandbox-path.txt after the setup (/tmp/hirearchy-g0-$LABEL-<epoch>). Every command below is its own tool call, foreground.
1. setup (gates, sandbox, profile, safety-before, ambient/setup, skill check):
     zsh $H/run_arm.sh $ARM 1 --setup        # = zsh $H/setup_stream.sh $LABEL for this label
2. for each turn T = 1.. (cap 15 user turns; Lena's line by the protocol, rule ids and facts in $D/lena-lines.txt):
     write the line to $D/prompts/tNN.txt (absolute path)
     zsh $H/run_turn.sh <S> $LABEL <T> $D/prompts/tNN.txt     # alone, timeout 1800000 ms; keeps the '; sleep 20' boundary
     zsh $H/after_turn.sh $LABEL <T>                          # org state, session copy, scheduler/signal records, model checks, ambient, quality
3. after turn 1:
     python3 -B $H/ambient_context.py $D/assistant-session-messages.jsonl $D/assistant-session.json <S> > $D/ambient-context.txt
     zsh $H/skill_check.sh $LABEL turn1
4. injection, once, when the turn of memo 1's first delivery has ended and before Lena's next turn:
     zsh $H/model_check.sh org $LABEL <S>; zsh $H/model_check.sh assistant $LABEL <S>
     uv --directory $REPO run python $H/inject_root_rework.py --org <S>/org --revises <memo-1 task id> --out <S>/injection
     write <S>/injection/window.txt ("YYYY-MM-DDTHH:MM:SS YYYY-MM-DDTHH:MM:SS", UTC, request time and final progress time) and
     $D/injection/memo1-identification.txt
5. after the last turn (and after the facilitator saw no scheduler running, or this stops it):
     zsh $H/finish_stream.sh $LABEL
EOF
done
