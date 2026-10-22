#!/bin/zsh
# E4 per-turn driver. Usage: run_turn.sh <S> <stream N> <turn number> <prompt file>
# Sends the prompt file's text verbatim as Lena's line. Turn 1 = new session; turns >= 2 add --resume. cwd = S.
# Writes into <evidence>/s<N>/: turn-NN.prompt.txt (copy), turn-NN.txt (header + prompt + stdout, ANSI stripped),
# turn-NN.raw.txt (raw stdout), turn-NN.stderr.txt, and appends a line to turn-times.txt. No MCP/CLI call against the org.
S="$1"; N="$2"; T="$3"; PF="$4"
EV=/Volumes/workspace/hirearchy/studies/E4-org-growth-0a1-recheck/evidence/s$N
NN=$(printf '%02d' "$T")
mkdir -p "$EV"
cp "$PF" "$EV/turn-$NN.prompt.txt"
PROMPT="$(cat "$PF")"
RESUME=""
[[ "$T" -ge 2 ]] && RESUME="--resume"
cd "$S" || exit 90
start=$(date +%s); startl=$(date +%H:%M:%S); startu=$(date -u +%FT%TZ)
kiro-cli chat --v3 --no-interactive --trust-all-tools $RESUME --agent hirearchy-study-e4-s$N-assistant "$PROMPT" > "$EV/turn-$NN.raw.txt" 2> "$EV/turn-$NN.stderr.txt"
rc=$?
end=$(date +%s); endl=$(date +%H:%M:%S); endu=$(date -u +%FT%TZ)
{
  echo "######## TURN $T  start $startl  end $endl  elapsed $((end-start))s  (local, $(date +%F); UTC wall-clock start $startu end $endu; exit code $rc)"
  echo "######## LENA (prompt sent verbatim):"
  cat "$PF"
  echo
  echo "######## ASSISTANT (stdout, ANSI stripped; stderr is in turn-$NN.stderr.txt):"
  python3 -c "import re,sys; sys.stdout.write(re.sub(r'\x1b\[[0-9;?]*[A-Za-z]|\x1b\][^\x07]*\x07','',open(sys.argv[1],errors='replace').read()))" "$EV/turn-$NN.raw.txt"
} > "$EV/turn-$NN.txt"
echo "turn $T: $startl - $endl  $end-$start=$((end-start))s  utc $startu - $endu  exit $rc" >> "$EV/turn-times.txt"
echo "turn $T exit $rc elapsed $((end-start))s"
exit $rc
