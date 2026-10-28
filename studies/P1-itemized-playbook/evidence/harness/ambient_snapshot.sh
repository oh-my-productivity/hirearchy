#!/bin/zsh
# G0 ambient snapshot (read-only). Usage: ambient_snapshot.sh <label> [<kiro home>]   -> prints to stdout
# E7's snapshot (protocol 4.5.1; E7 item 4, D-E6-7), unchanged for the owner's ~/.kiro: before and after every turn, the user's global skills and
# memories database, metadata only.
# 1. every entry under ~/.kiro/skills, links not followed (find -P): mtime (epoch and UTC), type, size, path, and a symlink's target;
# 2. every entry reached through the links (find -L): mtime, type, size and path (the skill catalog's content, metadata only);
# 3. ~/.kiro/memories: each entry's mtime, type, size and name, and the md5 of memories.db.
# It never opens, parses, queries or prints the database's contents (md5 -q digests its bytes and prints the digest only), writes nothing
# but its stdout, and changes nothing it lists. Each listing is followed by its own md5, so two snapshots compare line by line.
# G0 (arm M0): with a second argument <kiro home> (the dedicated home's .kiro directory), the same three sections are appended for
# <kiro home>/skills (find -P and find -L) and <kiro home>/memories (expected absent: the listing is the single line "(absent)"), each with
# its listing md5 (lines "home skills listing md5", "home skills-through-links listing md5", "home memories listing md5").
label="${1:-snapshot}"
KH="$2"
SK=$HOME/.kiro/skills
MEM=$HOME/.kiro/memories
FMT='%m|%Sm|%HT|%z|%N|%Y'
echo "label: $label"
echo "date_utc: $(date -u +%Y-%m-%dT%H:%M:%SZ)  epoch: $(date +%s)"
P=$(TZ=UTC find -P "$SK" -exec stat -t '%Y-%m-%dT%H:%M:%SZ' -f "$FMT" {} + 2>&1 | sort -t'|' -k5,5)
L=$(TZ=UTC find -L "$SK" -exec stat -L -t '%Y-%m-%dT%H:%M:%SZ' -f '%m|%Sm|%HT|%z|%N' {} + 2>&1 | sort -t'|' -k5,5)
M=$(TZ=UTC find -P "$MEM" -maxdepth 1 -exec stat -t '%Y-%m-%dT%H:%M:%SZ' -f "$FMT" {} + 2>&1 | sort -t'|' -k5,5)
echo "== ~/.kiro/skills, links not followed (find -P): mtime_epoch|mtime_utc|type|size|path|link target ($(print -r -- "$P" | wc -l | tr -d ' ') entries)"
print -r -- "$P"
echo "skills listing md5: $(print -r -- "$P" | md5 -q)"
echo "== ~/.kiro/skills through the links (find -L): mtime_epoch|mtime_utc|type|size|path ($(print -r -- "$L" | wc -l | tr -d ' ') entries)"
print -r -- "$L"
echo "skills-through-links listing md5: $(print -r -- "$L" | md5 -q)"
echo "== ~/.kiro/memories, metadata only: mtime_epoch|mtime_utc|type|size|path|link target"
print -r -- "$M"
echo "memories listing md5: $(print -r -- "$M" | md5 -q)"
echo "memories.db md5 (a digest only; its contents are never read): $(md5 -q "$MEM/memories.db" 2>&1)"
if [[ -n "$KH" ]]; then
  HSK=$KH/skills
  HMEM=$KH/memories
  if [[ -d "$HSK" ]]; then
    HP=$(TZ=UTC find -P "$HSK" -exec stat -t '%Y-%m-%dT%H:%M:%SZ' -f "$FMT" {} + 2>&1 | sort -t'|' -k5,5)
    HL=$(TZ=UTC find -L "$HSK" -exec stat -L -t '%Y-%m-%dT%H:%M:%SZ' -f '%m|%Sm|%HT|%z|%N' {} + 2>&1 | sort -t'|' -k5,5)
  else
    HP="(absent)"; HL="(absent)"
  fi
  if [[ -d "$HMEM" ]]; then
    HM=$(TZ=UTC find -P "$HMEM" -maxdepth 1 -exec stat -t '%Y-%m-%dT%H:%M:%SZ' -f "$FMT" {} + 2>&1 | sort -t'|' -k5,5)
  else
    HM="(absent)"
  fi
  echo "== $HSK, links not followed (find -P): mtime_epoch|mtime_utc|type|size|path|link target ($(print -r -- "$HP" | wc -l | tr -d ' ') entries)"
  print -r -- "$HP"
  echo "home skills listing md5: $(print -r -- "$HP" | md5 -q)"
  echo "== $HSK through the links (find -L): mtime_epoch|mtime_utc|type|size|path ($(print -r -- "$HL" | wc -l | tr -d ' ') entries)"
  print -r -- "$HL"
  echo "home skills-through-links listing md5: $(print -r -- "$HL" | md5 -q)"
  echo "== $HMEM, metadata only (expected absent): mtime_epoch|mtime_utc|type|size|path|link target"
  print -r -- "$HM"
  echo "home memories listing md5: $(print -r -- "$HM" | md5 -q)"
fi
