#!/bin/zsh
# E7 ambient snapshot (read-only). Usage: ambient_snapshot.sh <label>   -> prints to stdout
# Protocol 4.5.1 (E7 item 4, D-E6-7): before and after every turn, the user's global skills and memories database, metadata only.
# 1. every entry under ~/.kiro/skills, links not followed (find -P): mtime (epoch and UTC), type, size, path, and a symlink's target;
# 2. every entry reached through the links (find -L): mtime, type, size and path (the skill catalog's content, metadata only);
# 3. ~/.kiro/memories: each entry's mtime, type, size and name, and the md5 of memories.db.
# It never opens, parses, queries or prints the database's contents (md5 -q digests its bytes and prints the digest only), writes nothing
# but its stdout, and changes nothing it lists. Each listing is followed by its own md5, so two snapshots compare line by line.
label="${1:-snapshot}"
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
