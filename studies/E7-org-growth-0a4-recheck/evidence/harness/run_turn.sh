#!/bin/zsh
# E7 per-turn driver. Usage: run_turn.sh <S> <stream N> <turn number> <prompt file>
# Sends the prompt file's text verbatim as Lena's line. Turn 1 = new session; turns >= 2 add --resume. cwd = S.
# Every call carries --effort high (protocol 4.2, 4.3). The exact argv is written to turn-NN.cmd.txt (model_check.sh reads it).
# Writes into <evidence>/s<N>/: turn-NN.prompt.txt (copy), turn-NN.cmd.txt (argv), turn-NN.txt (header + prompt + stdout, ANSI
# stripped), turn-NN.raw.txt (raw stdout), turn-NN.stderr.txt, and appends a line to turn-times.txt. No MCP/CLI call against the org.
# E7 (protocol 4.2.1, E7 item 4, D-E6-7; C1's D-HARN form): the kiro-cli chat command is never the last command of its tool call: the
# exit code and the end times are taken, then `; sleep 20` follows in the same command list, so the call stays open 20 s after the return.
# E7 (protocol 4.5.1): ambient_snapshot.sh is taken right before the chat (ambient/turn-NN-before.txt) and after the sleep
# (ambient/turn-NN-after.txt). turn-times.txt keeps E6's format and appends the time the sleep ended.
S="$1"; N="$2"; T="$3"; PF="$4"
EV=/Volumes/workspace/hirearchy/studies/E7-org-growth-0a4-recheck/evidence/s$N
H=/Volumes/workspace/hirearchy/studies/E7-org-growth-0a4-recheck/evidence/harness
NN=$(printf '%02d' "$T")
mkdir -p "$EV"
cp "$PF" "$EV/turn-$NN.prompt.txt"
PROMPT="$(cat "$PF")"
RESUME=""
[[ "$T" -ge 2 ]] && RESUME="--resume"
cd "$S" || exit 90
CMD=(kiro-cli chat --v3 --no-interactive --trust-all-tools $RESUME --effort high --agent hirearchy-study-e7-s$N-assistant "$PROMPT")
print -r -- "${(q-)CMD[@]}" > "$EV/turn-$NN.cmd.txt"
mkdir -p "$EV/ambient"
zsh "$H/ambient_snapshot.sh" "s$N before turn $T" > "$EV/ambient/turn-$NN-before.txt" 2>&1
start=$(date +%s); startl=$(date +%H:%M:%S); startu=$(date -u +%FT%TZ)
"${CMD[@]}" > "$EV/turn-$NN.raw.txt" 2> "$EV/turn-$NN.stderr.txt"; rc=$?; end=$(date +%s); endl=$(date +%H:%M:%S); endu=$(date -u +%FT%TZ); sleep 20
slept=$(date -u +%FT%TZ)
zsh "$H/ambient_snapshot.sh" "s$N after turn $T" > "$EV/ambient/turn-$NN-after.txt" 2>&1
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
