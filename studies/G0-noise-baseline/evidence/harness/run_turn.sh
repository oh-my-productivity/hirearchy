#!/bin/zsh
# G0 per-turn driver (E7's). Usage: run_turn.sh <S> <label> <turn number> <prompt file>      (label = m0-s1, m1-s2, m0-s1r, ...)
# Sends the prompt file's text verbatim as Lena's line. Turn 1 = new session; turns >= 2 add --resume. cwd = S.
# Every call carries --effort high (protocol 4.2, 4.3). The exact argv is written to turn-NN.cmd.txt (model_check.sh reads it).
# Writes into <evidence>/<label>/: turn-NN.prompt.txt (copy), turn-NN.cmd.txt (argv), turn-NN.txt (header + prompt + stdout, ANSI
# stripped), turn-NN.raw.txt (raw stdout), turn-NN.stderr.txt, and appends a line to turn-times.txt. No MCP/CLI call against the org.
# E7 (protocol 4.2.1, E7 item 4, D-E6-7; C1's D-HARN form): the kiro-cli chat command is never the last command of its tool call: the
# exit code and the end times are taken, then `; sleep 20` follows in the same command list, so the call stays open 20 s after the return.
# E7 (protocol 4.5.1): ambient_snapshot.sh is taken right before the chat (ambient/turn-NN-before.txt) and after the sleep
# (ambient/turn-NN-after.txt). turn-times.txt keeps E6's format and appends the time the sleep ended.
# G0 (design 20.1, arms): the chat runs under the arm's kiro home. Arm M1 (the owner's ambient memories): `env -u KIRO_HOME`, so an inherited
# KIRO_HOME cannot redirect it, and kiro uses the owner's default home. Arm M0 (no memories index): `env KIRO_HOME=<M0H>/.kiro`, <M0H> read from
# <evidence>/<label>/m0-home-path.txt (the run is refused if that file is missing); HOME is unchanged and authentication comes from the
# inherited environment. The env prefix is the first part of the CMD array, so turn-NN.cmd.txt shows it. For arm M0 the ambient snapshots
# also list the dedicated home's skills and memories (ambient_snapshot.sh's second argument).
# The variable EV below is the STREAM's evidence folder, as in E7 (EVROOT is the study's evidence root).
S="$1"; LABEL="$2"; T="$3"; PF="$4"
REPO=/Volumes/workspace/hirearchy
ST=$REPO/studies/G0-noise-baseline
EVROOT=$ST/evidence
H=$EVROOT/harness
EV=$EVROOT/$LABEL
[[ "$LABEL" =~ '^(m0|m1)-s[1-9][0-9]*(r[0-9]*)?$' && -n "$S" && "$T" =~ '^[1-9][0-9]*$' && -f "$PF" ]] || { echo "usage: run_turn.sh <S> <label> <turn> <prompt file>" >&2; exit 2; }
ARM=${LABEL%%-*}
KIRO_ENV=(env -u KIRO_HOME)
KH=""
if [[ "$ARM" == m0 ]]; then
  [[ -s "$EV/m0-home-path.txt" ]] || { echo "REFUSED: $EV/m0-home-path.txt is missing: arm m0 needs its dedicated kiro home (prepare_m0_home.sh)" >&2; exit 91; }
  M0H="$(cat "$EV/m0-home-path.txt")"
  [[ -d "$M0H/.kiro" ]] || { echo "REFUSED: $M0H/.kiro does not exist" >&2; exit 91; }
  KH="$M0H/.kiro"
  KIRO_ENV=(env KIRO_HOME="$KH")
fi
NN=$(printf '%02d' "$T")
mkdir -p "$EV"
cp "$PF" "$EV/turn-$NN.prompt.txt"
PROMPT="$(cat "$PF")"
RESUME=""
[[ "$T" -ge 2 ]] && RESUME="--resume"
cd "$S" || exit 90
CMD=(${KIRO_ENV[@]} kiro-cli chat --v3 --no-interactive --trust-all-tools $RESUME --effort high --agent hirearchy-study-g0-$LABEL-assistant "$PROMPT")
print -r -- "${(q-)CMD[@]}" > "$EV/turn-$NN.cmd.txt"
mkdir -p "$EV/ambient"
zsh "$H/ambient_snapshot.sh" "$LABEL before turn $T" $KH > "$EV/ambient/turn-$NN-before.txt" 2>&1
start=$(date +%s); startl=$(date +%H:%M:%S); startu=$(date -u +%FT%TZ)
"${CMD[@]}" > "$EV/turn-$NN.raw.txt" 2> "$EV/turn-$NN.stderr.txt"; rc=$?; end=$(date +%s); endl=$(date +%H:%M:%S); endu=$(date -u +%FT%TZ); sleep 20
slept=$(date -u +%FT%TZ)
zsh "$H/ambient_snapshot.sh" "$LABEL after turn $T" $KH > "$EV/ambient/turn-$NN-after.txt" 2>&1
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
