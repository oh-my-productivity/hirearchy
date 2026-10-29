#!/bin/zsh
# P2 per-turn driver (P1's run_turn.sh with the arm's label; protocol 3.2). Called ONLY by turn.sh (F-P1-14): it refuses otherwise.
# Usage (through turn.sh): run_turn.sh <S> <label> <turn number> <absolute prompt file>
# Sends the prompt file's text verbatim as Lena's line. Turn 1 = new session; turns >= 2 add --resume. cwd = S. Every call carries
# --effort high. The argv goes to turn-NN.cmd.txt. Writes into <EV>/<label>/: turn-NN.prompt.txt, turn-NN.cmd.txt, turn-NN.txt (header +
# prompt + stdout, ANSI stripped), turn-NN.raw.txt, turn-NN.stderr.txt, and a line in turn-times.txt. No MCP or CLI call against the org.
# Boundary (E7 4.2.1): the chat command is never the last command of its call: the exit code and the end time are taken, then `; sleep 20`
# follows in the same command list. Ambient snapshots right before the chat and after the sleep.
# Kiro home (F-G0-7 section 4, binding): BOTH arms run `env -u KIRO_HOME`; the env prefix is the first part of the argv, so turn-NN.cmd.txt
# shows it in every turn of both arms.
[[ "$P2_TURN_WRAPPER" == 1 ]] || { echo "REFUSED: run_turn.sh runs only inside turn.sh (one wrapper per turn, F-P1-14)" >&2; exit 93; }
S="$1"; LABEL="$2"; T="$3"; PF="$4"
H0=${0:A:h}
source $H0/arm.sh "$LABEL" || exit 2
[[ "$LABEL" =~ $STREAM_RE || "$LABEL" == probe-* || "$LABEL" == selfcheck-* ]] || { echo "run_turn.sh: bad label $LABEL" >&2; exit 2; }
[[ -n "$S" && "$T" =~ '^[1-9][0-9]*$' && -f "$PF" && "$PF" == /* ]] || { echo "usage: run_turn.sh <S> <label> <turn> <absolute prompt file>" >&2; exit 2; }
[[ "$T" -le 50 ]] || { echo "REFUSED: turn $T is beyond the cap of 50 user turns (protocol 4.7)" >&2; exit 92; }
[[ -z "${KIRO_HOME+set}" ]] || { echo "REFUSED: KIRO_HOME is set in this shell (protocol 1)" >&2; exit 91; }
KIRO_ENV=(env -u KIRO_HOME)
# the self-check's overrides (a fake chat, a short boundary, a scratch evidence folder) hold for a selfcheck-* label only; a stream or a
# probe always runs kiro-cli with the 20-second boundary into its own evidence folder
KCLI=kiro-cli; BOUND=20
D=$EV/$LABEL; [[ "$LABEL" == probe-* ]] && D=$EV/probe/$LABEL
if [[ "$LABEL" == selfcheck-* ]]; then KCLI=${P2_KIRO_CLI:-kiro-cli}; BOUND=${P2_BOUNDARY:-20}; [[ -n "$P2_EVDIR" ]] && D=$P2_EVDIR; fi
NN=$(printf '%02d' "$T")
mkdir -p "$D"
cp "$PF" "$D/turn-$NN.prompt.txt"
PROMPT="$(cat "$PF")"
RESUME=""
[[ "$T" -ge 2 ]] && RESUME="--resume"
cd "$S" || exit 90
CMD=(${KIRO_ENV[@]} $KCLI chat --v3 --no-interactive --trust-all-tools $RESUME --effort high --agent $PNAME "$PROMPT")
print -r -- "${(q-)CMD[@]}" > "$D/turn-$NN.cmd.txt"
mkdir -p "$D/ambient"
zsh "$H0/ambient_snapshot.sh" "$LABEL before turn $T" > "$D/ambient/turn-$NN-before.txt" 2>&1
start=$(date +%s); startl=$(date +%H:%M:%S); startu=$(date -u +%FT%TZ)
"${CMD[@]}" > "$D/turn-$NN.raw.txt" 2> "$D/turn-$NN.stderr.txt"; rc=$?; end=$(date +%s); endl=$(date +%H:%M:%S); endu=$(date -u +%FT%TZ); sleep $BOUND
slept=$(date -u +%FT%TZ)
zsh "$H0/ambient_snapshot.sh" "$LABEL after turn $T" > "$D/ambient/turn-$NN-after.txt" 2>&1
{
  echo "######## TURN $T  start $startl  end $endl  elapsed $((end-start))s  (local, $(date +%F); UTC wall-clock start $startu end $endu; exit code $rc)"
  echo "######## LENA (prompt sent verbatim):"
  cat "$PF"
  echo
  echo "######## ASSISTANT (stdout, ANSI stripped; stderr is in turn-$NN.stderr.txt):"
  python3 -c "import re,sys; sys.stdout.write(re.sub(r'\x1b\[[0-9;?]*[A-Za-z]|\x1b\][^\x07]*\x07','',open(sys.argv[1],errors='replace').read()))" "$D/turn-$NN.raw.txt"
} > "$D/turn-$NN.txt"
echo "turn $T: $startl - $endl  $end-$start=$((end-start))s  utc $startu - $endu  exit $rc  sleep $BOUND ended utc $slept" >> "$D/turn-times.txt"
echo "turn $T exit $rc elapsed $((end-start))s"
exit $rc
