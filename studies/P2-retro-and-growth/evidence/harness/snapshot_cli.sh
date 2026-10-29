#!/bin/zsh
# P2 per-turn CLI snapshot (P1's quality_snapshot.sh and services_snapshot.sh in one function, with the arm's CLI; protocol 3.2).
# Usage: snapshot_cli.sh <label> <tag> <kind> <cli args...>      kind: quality (JSON) or services (text)
#   <tag>  turn-NN (after_turn.sh) or end (finish_stream.sh)
# If <S>/org/ORG.md does not exist: appends "<tag> <utc>: no org yet, <kind> not run" to <label>/<kind>/calls.txt and exits 0 (the CLI's
# cli.command recorder would create <S>/org/.runtime/ and break the assistant's create_org, P1's rule). Otherwise runs the ARM's
# `hirearchy --root <S>/org <args>` (KIRO_HOME unset) into <label>/<kind>/<tag>.<json|txt> (stderr <tag>.stderr.txt) and appends to calls.txt
# the tag, the UTC start and end with microseconds, the exit code, the output's size in bytes, (quality) whether it is valid JSON, and every
# <S>/org/.runtime/events/**/cli-*.jsonl that appeared during the call (a known harness actor, H6). An unread snapshot prints a `NOTE:` line.
LABEL="$1"; TAG="$2"; KIND="$3"; shift 3
H0=${0:A:h}
source $H0/arm.sh "$LABEL" || exit 2
[[ "$TAG" =~ '^(turn-[0-9][0-9]+|end)$' && ( "$KIND" == quality || "$KIND" == services ) ]] || { echo "usage: snapshot_cli.sh <label> turn-NN|end quality|services <args>" >&2; exit 2; }
D=$EV/$LABEL; [[ "$LABEL" == selfcheck-* && -n "$P2_EVDIR" ]] && D=$P2_EVDIR
[[ -f $D/sandbox-path.txt ]] || { echo "snapshot_cli.sh: $D/sandbox-path.txt is missing" >&2; exit 2; }
S=$(cat $D/sandbox-path.txt)
Q=$D/$KIND; EXT=txt; [[ $KIND == quality ]] && EXT=json
mkdir -p "$Q"
if [[ ! -e "$S/org/ORG.md" ]]; then
  echo "$TAG $(date -u +%FT%TZ): no org yet, $KIND not run" >> "$Q/calls.txt"; echo "$KIND $TAG: no org yet, not run"; exit 0
fi
utcus() { python3 -c 'import datetime;print(datetime.datetime.now(datetime.timezone.utc).isoformat())'; }
list_cli() { [[ -d "$S/org/.runtime/events" ]] && find "$S/org/.runtime/events" -type f -name 'cli-*.jsonl' 2>/dev/null | sort; true; }
before="$(list_cli)"
startu=$(utcus)
"${HIR[@]}" --root "$S/org" "$@" > "$Q/$TAG.$EXT" 2> "$Q/$TAG.stderr.txt"; rc=$?
endu=$(utcus)
after="$(list_cli)"
new=("${(@f)$(comm -13 <(print -r -- "$before") <(print -r -- "$after"))}")
bytes=$(wc -c < "$Q/$TAG.$EXT" | tr -d ' ')
jsonok=""
[[ $KIND == quality ]] && jsonok=" json $(python3 -c 'import json,sys; json.load(open(sys.argv[1]))' "$Q/$TAG.$EXT" > /dev/null 2>&1 && echo ok || echo invalid)"
{
  echo "$TAG start $startu end $endu exit $rc bytes $bytes$jsonok product $REPO_A"
  if [[ -z "${new[1]}" ]]; then echo "  new cli-*.jsonl during the call: (none)"
  else for f in $new; do echo "  new cli-*.jsonl: ${f#$S/org/.runtime/events/}  command: $(sed -n 's/.*"command":"\([^"]*\)".*/\1/p' "$f" | tr '\n' ' ')"; done; fi
} >> "$Q/calls.txt"
echo "$KIND $TAG: exit $rc ($Q/$TAG.$EXT)"
[[ $rc -ne 0 || $bytes -eq 0 || "$jsonok" == " json invalid" ]] && echo "NOTE: $KIND $TAG is unread (exit $rc, $bytes bytes${jsonok}; protocol 12): see $Q/$TAG.stderr.txt"
exit 0
