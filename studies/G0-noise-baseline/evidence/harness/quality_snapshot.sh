#!/bin/zsh
# G0 quality snapshot (design 20.3: `hirearchy quality --json` after each turn and at the end). Usage: quality_snapshot.sh <label> <tag>
#   <tag>  turn-NN (after_turn.sh) or end (finish_stream.sh)
# If <S>/org/ORG.md does not exist: appends "<tag> <utc>: no org yet, quality not run" to $EV/<label>/quality/calls.txt and exits 0. The CLI's
# `cli.command` recorder would create <S>/org/.runtime/ and break the assistant's create_org, so the CLI is not run before the org exists.
# Otherwise: runs `uv --directory $REPO run hirearchy --root <S>/org quality --json` into $EV/<label>/quality/<tag>.json (stderr:
# <tag>.stderr.txt) and appends to calls.txt the tag, the UTC start and end, the exit code, and the name and `command` field of every
# <S>/org/.runtime/events/**/cli-*.jsonl that appeared during the call (the listing before and after). Read-only otherwise: the product's
# CLI records its own cli.command event, and that is all it writes.
LABEL="$1"; TAG="$2"
REPO=/Volumes/workspace/hirearchy
ST=$REPO/studies/G0-noise-baseline
EV=$ST/evidence
[[ "$LABEL" =~ '^(m0|m1)-s[1-9][0-9]*(r[0-9]*)?$' && "$TAG" =~ '^(turn-[0-9][0-9]+|end)$' && $# -eq 2 ]] || { echo "usage: quality_snapshot.sh <label> turn-NN|end" >&2; exit 2; }
D=$EV/$LABEL
[[ -f $D/sandbox-path.txt ]] || { echo "quality_snapshot.sh: $D/sandbox-path.txt is missing" >&2; exit 2; }
S=$(cat $D/sandbox-path.txt)
Q=$D/quality
mkdir -p "$Q"
if [[ ! -e "$S/org/ORG.md" ]]; then
  echo "$TAG $(date -u +%FT%TZ): no org yet, quality not run" >> "$Q/calls.txt"
  echo "quality $TAG: no org yet, not run"
  exit 0
fi
list_cli() { [[ -d "$S/org/.runtime/events" ]] && find "$S/org/.runtime/events" -type f -name 'cli-*.jsonl' 2>/dev/null | sort; true; }
before="$(list_cli)"
startu=$(date -u +%FT%TZ)
uv --directory "$REPO" run hirearchy --root "$S/org" quality --json > "$Q/$TAG.json" 2> "$Q/$TAG.stderr.txt"; rc=$?
endu=$(date -u +%FT%TZ)
after="$(list_cli)"
new=("${(@f)$(comm -13 <(print -r -- "$before") <(print -r -- "$after"))}")
{
  echo "$TAG start $startu end $endu exit $rc"
  if [[ -z "${new[1]}" ]]; then
    echo "  new cli-*.jsonl during the call: (none)"
  else
    for f in $new; do
      echo "  new cli-*.jsonl: ${f#$S/org/.runtime/events/}  command: $(sed -n 's/.*"command":"\([^"]*\)".*/\1/p' "$f" | tr '\n' ' ')"
    done
  fi
} >> "$Q/calls.txt"
echo "quality $TAG: exit $rc ($Q/$TAG.json)"
exit 0
