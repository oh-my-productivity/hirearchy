#!/bin/zsh
# P1 per-turn driver (G0's run_turn.sh, M1 treatment only; E7's chat line and boundary). Usage: run_turn.sh <S> <label> <turn number> <prompt file>
#   label = F1 F2 F3 I1 I2 I3 (a replacement: F1r ...). Arm = the label's first letter (F frozen-playbook control, I itemized).
# Sends the prompt file's text verbatim as Lena's line. Turn 1 = new session; turns >= 2 add --resume. cwd = S. Every call carries --effort high.
# The exact argv is written to turn-NN.cmd.txt (model_check.sh reads it). Writes into <evidence>/<label>/: turn-NN.prompt.txt (copy),
# turn-NN.cmd.txt (argv), turn-NN.txt (header + prompt + stdout, ANSI stripped), turn-NN.raw.txt (raw stdout), turn-NN.stderr.txt, and a line
# in turn-times.txt. No MCP/CLI call against the org.
# Boundary (E7 4.2.1; D-E6-7; C1's D-HARN form): the kiro-cli chat command is never the last command of its tool call: the exit code and the end
# times are taken, then `; sleep 20` follows in the same command list. Ambient snapshots right before the chat and after the sleep (E7 4.5.1).
# Kiro home (design 18.2, 18.3 item 1; F-G0-7 section 4 item 1): BOTH arms run `env -u KIRO_HOME`, so kiro uses the owner's default home and an
# inherited KIRO_HOME can never redirect it. No dedicated kiro home exists in P1. The env prefix is the first part of the CMD array, so
# turn-NN.cmd.txt shows it in every turn of both arms.
S="$1"; LABEL="$2"; T="$3"; PF="$4"
REPO=/Volumes/workspace/hirearchy
ST=$REPO/studies/P1-itemized-playbook
EVROOT=$ST/evidence
H=$EVROOT/harness
EV=$EVROOT/$LABEL
[[ "$LABEL" =~ '^[FI][1-3](r[0-9]*)?$' && -n "$S" && "$T" =~ '^[1-9][0-9]*$' && -f "$PF" ]] || { echo "usage: run_turn.sh <S> <label F1..I3> <turn> <prompt file>" >&2; exit 2; }
[[ "$T" -le 30 ]] || { echo "REFUSED: turn $T is beyond the cap of 30 user turns (protocol 4.2)" >&2; exit 92; }
KIRO_ENV=(env -u KIRO_HOME)
NN=$(printf '%02d' "$T")
mkdir -p "$EV"
cp "$PF" "$EV/turn-$NN.prompt.txt"
PROMPT="$(cat "$PF")"
RESUME=""
[[ "$T" -ge 2 ]] && RESUME="--resume"
cd "$S" || exit 90
CMD=(${KIRO_ENV[@]} kiro-cli chat --v3 --no-interactive --trust-all-tools $RESUME --effort high --agent hirearchy-study-p1-$LABEL-assistant "$PROMPT")
print -r -- "${(q-)CMD[@]}" > "$EV/turn-$NN.cmd.txt"
mkdir -p "$EV/ambient"
zsh "$H/ambient_snapshot.sh" "$LABEL before turn $T" > "$EV/ambient/turn-$NN-before.txt" 2>&1
start=$(date +%s); startl=$(date +%H:%M:%S); startu=$(date -u +%FT%TZ)
"${CMD[@]}" > "$EV/turn-$NN.raw.txt" 2> "$EV/turn-$NN.stderr.txt"; rc=$?; end=$(date +%s); endl=$(date +%H:%M:%S); endu=$(date -u +%FT%TZ); sleep 20
slept=$(date -u +%FT%TZ)
zsh "$H/ambient_snapshot.sh" "$LABEL after turn $T" > "$EV/ambient/turn-$NN-after.txt" 2>&1
{
  echo "######## TURN $T  start $startl  end $endl  elapsed $((end-start))s  (local, $(date +%F); UTC wall-clock start $startu end $endu; exit code $rc)"
  echo "######## LENA (prompt sent verbatim):"
  cat "$PF"
  echo
  echo "######## ASSISTANT (stdout, ANSI stripped; stderr is in turn-$NN.stderr.txt):"
  python3 -c "import re,sys; sys.stdout.write(re.sub(r'\x1b\[[0-9;?]*[A-Za-z]|\x1b\][^\x07]*\x07','',open(sys.argv[1],errors='replace').read()))" "$EV/turn-$NN.raw.txt"
} > "$EV/turn-$NN.txt"
echo "turn $T: $startl - $endl  $end-$start=$((end-start))s  utc $startu - $endu  exit $rc  sleep 20 ended utc $slept" >> "$EV/turn-times.txt"
echo "turn $T exit $rc elapsed $((end-start))s"
exit $rc
