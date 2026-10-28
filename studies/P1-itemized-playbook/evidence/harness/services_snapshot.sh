#!/bin/zsh
# P1 services snapshot (protocol 10: root's `services` after every turn and at the end). Usage: services_snapshot.sh <label> <tag>
#   <tag>  turn-NN (after_turn.sh) or end (finish_stream.sh)
# quality_snapshot.sh's twin: not run before <S>/org/ORG.md exists (the CLI's event recorder would create .runtime/ before create_org); otherwise
# `uv --directory $REPO run hirearchy --root <S>/org services` into $EV/<label>/services/<tag>.txt (stderr <tag>.stderr.txt), and calls.txt gets the
# tag, the UTC start and end (ISO with microseconds), the exit code, the output's size in bytes (protocol 12.1's unread rule) and every cli-*.jsonl event file that appeared during the call (a known harness actor, H6).
# Read-only otherwise: root's listing shows `- {name} (offered by {owner}; contract v{n}, playbook v{m})` and the watch suffix of 14.3.
LABEL="$1"; TAG="$2"
REPO=/Volumes/workspace/hirearchy
EV=$REPO/studies/P1-itemized-playbook/evidence
[[ "$LABEL" =~ '^[FI][1-3](r[0-9]*)?$' && "$TAG" =~ '^(turn-[0-9][0-9]+|end)$' && $# -eq 2 ]] || { echo "usage: services_snapshot.sh <label> turn-NN|end" >&2; exit 2; }
D=$EV/$LABEL
[[ -f $D/sandbox-path.txt ]] || { echo "services_snapshot.sh: $D/sandbox-path.txt is missing" >&2; exit 2; }
S=$(cat $D/sandbox-path.txt)
Q=$D/services
mkdir -p "$Q"
if [[ ! -e "$S/org/ORG.md" ]]; then
  echo "$TAG $(date -u +%FT%TZ): no org yet, services not run" >> "$Q/calls.txt"
  echo "services $TAG: no org yet, not run"
  exit 0
fi
list_cli() { [[ -d "$S/org/.runtime/events" ]] && find "$S/org/.runtime/events" -type f -name 'cli-*.jsonl' 2>/dev/null | sort; true; }
before="$(list_cli)"
startu=$(python3 -c 'import datetime;print(datetime.datetime.now(datetime.timezone.utc).isoformat())')
uv --directory "$REPO" run hirearchy --root "$S/org" services > "$Q/$TAG.txt" 2> "$Q/$TAG.stderr.txt"; rc=$?
endu=$(python3 -c 'import datetime;print(datetime.datetime.now(datetime.timezone.utc).isoformat())')
after="$(list_cli)"
new=("${(@f)$(comm -13 <(print -r -- "$before") <(print -r -- "$after"))}")
bytes=$(wc -c < "$Q/$TAG.txt" | tr -d ' ')  # protocol 12.1's unread rule: exit not 0 or an empty output
{
  echo "$TAG start $startu end $endu exit $rc bytes $bytes"
  if [[ -z "${new[1]}" ]]; then echo "  new cli-*.jsonl during the call: (none)"
  else for f in $new; do echo "  new cli-*.jsonl: ${f#$S/org/.runtime/events/}"; done; fi
} >> "$Q/calls.txt"
echo "services $TAG: exit $rc ($Q/$TAG.txt)"
[[ $rc -ne 0 || $bytes -eq 0 ]] && echo "NOTE: services $TAG is unread (exit $rc, $bytes bytes; protocol 12.1): see $Q/$TAG.stderr.txt"
exit 0
