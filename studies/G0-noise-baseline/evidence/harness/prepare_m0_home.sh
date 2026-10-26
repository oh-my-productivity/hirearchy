#!/bin/zsh
# G0 arm M0: prepare the dedicated kiro home of one stream (design 20.1: "M0: the assistant runs in a dedicated HOME ... whose kiro settings are
# copies without the memories index"). Usage: prepare_m0_home.sh <label> <M0H> [--dry-run]
#   <label>  an M0 stream label (m0-s<n>, replacements m0-s<n>r, m0-s<n>r2), or 'preflight' (protocol 11: the preflight's M0 check,
#            evidence in $EV/preflight/m0-home/)
#   <M0H>    the target, /tmp/hirearchy-g0-m0home-<label>-<epoch> (the setup step computes the epoch). The script refuses any target that
#            does not start with /tmp/hirearchy-g0-m0home- and any target that exists already.
# It makes $M0H/.kiro/ with
#   settings/  byte copies (cp -p) of every regular file of ~/.kiro/settings/ EXCEPT the names starting mcp.json (the assistant profile has
#              includeMcpJson false; those files may hold credentials and are never copied, never opened, and their names are not printed);
#   agents/    empty (the setup step writes the stream's profile there);
#   skills/    a real directory. skills/hirearchy/SKILL.md is a copy of the REPO's SKILL.md, made only when ~/.kiro/skills/hirearchy/SKILL.md
#              exists and its md5 (md5 -q; the file is only digested) equals the repo file's (design 20.1: M0 holds a copy of the same bytes at
#              the same relative path exactly when M1's HOME has one). Every OTHER top-level entry name of ~/.kiro/skills/ (names only, from a
#              listing; no content is read) becomes a symlink skills/<name> -> $HOME/.kiro/skills/<name>, so the skill catalog is the owner's.
#   NOTHING else: no memories/, sessions/, secrets.json, steering/ ...
# Authentication is not copied: the chat runs under `env KIRO_HOME=$M0H/.kiro` with the inherited environment (run_turn.sh).
# Writes $EV/<label>/m0-home/setup.txt (the path, each settings copy with its md5, the skills listing with link targets, the SKILL.md md5s,
# ls -la of $M0H/.kiro) and $EV/<label>/m0-home-path.txt. --dry-run prints every action ("DRY-RUN: ...") and creates and writes nothing.
# Never writes anywhere in the owner's ~/.kiro.
REPO=/Volumes/workspace/hirearchy
ST=$REPO/studies/G0-noise-baseline
EV=$ST/evidence
M0_PREFIX=/tmp/hirearchy-g0-m0home-

LABEL="$1"; M0H="$2"; DRY=0
[[ "$3" == "--dry-run" ]] && DRY=1
[[ $# -eq 2 || ( $# -eq 3 && $DRY -eq 1 ) ]] || { echo "usage: prepare_m0_home.sh <label> <M0H> [--dry-run]" >&2; exit 2; }
[[ "$LABEL" =~ '^(m0-s[1-9][0-9]*(r[0-9]*)?|preflight)$' ]] || { echo "REFUSED: '$LABEL' is not an arm m0 stream label (m0-s<n>, m0-s<n>r, m0-s<n>r2) or 'preflight'" >&2; exit 2; }
case "$M0H" in
  ${M0_PREFIX}?*) ;;
  *) echo "REFUSED: target '$M0H' does not match ${M0_PREFIX}*" >&2; exit 3 ;;
esac
[[ "$M0H" == */../* || "$M0H" == */.. || "${M0H#$M0_PREFIX}" == */* || "$M0H" == *[[:space:]]* ]] && { echo "REFUSED: target '$M0H' is not a single path component under ${M0_PREFIX}*" >&2; exit 3; }
[[ -e "$M0H" || -L "$M0H" ]] && { echo "REFUSED: target '$M0H' exists already" >&2; exit 3; }

OWN=$HOME/.kiro
K=$M0H/.kiro
STREAM=$EV/$LABEL
REPO_SKILL=$REPO/skills/hirearchy/SKILL.md
GLOBAL_SKILL=$OWN/skills/hirearchy/SKILL.md
repo_md5=$(md5 -q "$REPO_SKILL") || { echo "REFUSED: cannot read $REPO_SKILL" >&2; exit 3; }
global_md5=""; [[ -f "$GLOBAL_SKILL" ]] && global_md5=$(md5 -q "$GLOBAL_SKILL")

settings=("$OWN"/settings/*(.ND))
copies=(); excluded=0
for f in $settings; do
  case "${f:t}" in mcp.json*) excluded=$((excluded+1)) ;; *) copies+=("$f") ;; esac
done
skill_names=("$OWN"/skills/*(ND))
links=(); for f in $skill_names; do [[ "${f:t}" == hirearchy ]] || links+=("${f:t}"); done

if [[ $DRY -eq 1 ]]; then
  echo "DRY-RUN prepare_m0_home.sh $LABEL -> $M0H (nothing is created or written)"
  echo "DRY-RUN: mkdir $K/settings $K/agents $K/skills (mode 700 on $M0H and $K)"
  for f in $copies; do echo "DRY-RUN: cp -p $f $K/settings/${f:t}"; done
  echo "DRY-RUN: $excluded file(s) matching mcp.json* in $OWN/settings are NOT copied (profile has includeMcpJson false)"
  if [[ -z "$global_md5" ]]; then
    echo "DRY-RUN: skills/hirearchy/SKILL.md: the owner has none ($GLOBAL_SKILL absent), so M0 gets none"
  elif [[ "$global_md5" == "$repo_md5" ]]; then
    echo "DRY-RUN: cp -p $REPO_SKILL $K/skills/hirearchy/SKILL.md (md5 $repo_md5; the global file has the same md5, so M0 holds the same bytes)"
  else
    echo "DRY-RUN: skills/hirearchy/SKILL.md: NOT copied; the global file's md5 $global_md5 differs from the repo's $repo_md5 (the stream is invalid, H2)"
  fi
  for n in $links; do echo "DRY-RUN: symlink $K/skills/$n -> $OWN/skills/$n"; done
  echo "DRY-RUN: NOT created: memories/, sessions/, secrets.json, steering/ or anything else under $K"
  echo "DRY-RUN: write $STREAM/m0-home/setup.txt and $STREAM/m0-home-path.txt"
  exit 0
fi

mkdir -p "$K/settings" "$K/agents" "$K/skills" || { echo "FAILED: cannot create $K" >&2; exit 4; }
chmod 700 "$M0H" "$K"
for f in $copies; do cp -p "$f" "$K/settings/${f:t}" || { echo "FAILED: cp $f" >&2; exit 4; }; done
skill_note=""
if [[ -z "$global_md5" ]]; then
  skill_note="absent: the owner has no $GLOBAL_SKILL, so M0 has none"
elif [[ "$global_md5" == "$repo_md5" ]]; then
  mkdir -p "$K/skills/hirearchy" && cp -p "$REPO_SKILL" "$K/skills/hirearchy/SKILL.md" || { echo "FAILED: cp skill" >&2; exit 4; }
  skill_note="copied: the global file's md5 equals the repo's ($repo_md5)"
else
  skill_note="differs: the global file's md5 $global_md5 is not the repo's $repo_md5; no copy is made (the stream is invalid, H2)"
  echo "WARNING: $skill_note" >&2
fi
for n in $links; do ln -s "$OWN/skills/$n" "$K/skills/$n" || { echo "FAILED: ln -s $n" >&2; exit 4; }; done

mkdir -p "$STREAM/m0-home"
echo "$M0H" > "$STREAM/m0-home-path.txt"
{
  echo "# $LABEL arm M0 home (prepare_m0_home.sh), created $(date -u +%FT%TZ)"
  echo "M0H: $M0H"
  echo "kiro home for the chat (KIRO_HOME): $K"
  echo "== settings: byte copies (cp -p) of the owner's regular files except mcp.json* ($excluded file(s) matching mcp.json* not copied)"
  for f in $copies; do echo "$(md5 -q "$K/settings/${f:t}")  $K/settings/${f:t}  (source md5 $(md5 -q "$f"))"; done
  echo "== skills: the owner's top-level entries by name, links to $OWN/skills/<name>; hirearchy is not linked"
  for n in $links; do echo "$K/skills/$n -> $(readlink "$K/skills/$n")"; done
  echo "== SKILL.md md5s (the global file is only digested)"
  echo "repo ($REPO_SKILL): $repo_md5"
  echo "global ($GLOBAL_SKILL): ${global_md5:-absent}"
  if [[ -f "$K/skills/hirearchy/SKILL.md" ]]; then echo "M0 copy ($K/skills/hirearchy/SKILL.md): $(md5 -q "$K/skills/hirearchy/SKILL.md")"; else echo "M0 copy: absent"; fi
  echo "M0 skill rule: $skill_note"
  echo "== ls -la $K"
  ls -la "$K"
  echo "== ls -la $K/skills"
  ls -la "$K/skills"
} > "$STREAM/m0-home/setup.txt" 2>&1
echo "prepared $M0H (see $STREAM/m0-home/setup.txt)"
