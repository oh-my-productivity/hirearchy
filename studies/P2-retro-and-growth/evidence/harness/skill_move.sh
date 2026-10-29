#!/bin/zsh
# P2 global-skill move for arm C (protocol 1, 3.6; the brief, "The skill, one per arm"). Usage:
#   skill_move.sh aside <label>     move ~/.kiro/skills/hirearchy/ to $ST/skill-aside/<label>-<epoch>/hirearchy/ (one mv)
#   skill_move.sh restore <label>   move it back; idempotent (with nothing to restore and the copy in place it only checks)
#   skill_move.sh status [<label>]  print the global copy's state and every move without a restore; exit 1 if one exists
#   skill_move.sh recover           FIRST in every step from the preflight on (protocol 3.6; F18 of the review): restore every move that
#                                   has no restore (a step cut off mid-stream), record it, and print `RECOVERED <label>`; exit 0 when
#                                   nothing was open or every restore held, 3 when one failed (the step stops with a warning)
# An aside is recorded as `ASIDE-PENDING` before its mv and `ASIDE` after its check (F33 of review 2); both are open moves for status,
# restore and recover until a `RESTORE` line follows.
# Checks, every time: the directory holds exactly SKILL.md, whose md5 is 443e1bc4911aa4d6aaa6457e78f673c1 (arm R's = the owner's copy),
# before and after each move. Records every move in $EV/skill-moves.txt (`ASIDE ...`, `RESTORE ...`), and the label's
# <label>/skill-restore.txt. It touches no other skill, never copies, never writes SKILL.md, never invents a restore: a missing or changed
# aside copy prints `STOP: skill restore impossible ...` and changes nothing (the manager restores; protocol 3.6).
# Self-check form: when $HOME is not the owner's home (/Users/aminalizadeh), the run is the self-check's on a constructed home under
# /tmp/hirearchy-p2/, and the record goes to $P/selfcheck-skill-moves.txt; any other $HOME is refused.
MODE="$1"; LABEL="$2"
H0=${0:A:h}
source $H0/arm.sh probe-C0 >/dev/null 2>&1 || true   # paths only (REPO_*, EV, P, SKILL_R_MD5); the label is not used for the arm
WANT=443e1bc4911aa4d6aaa6457e78f673c1
OWNER_HOME=/Users/aminalizadeh
# The aside directory (F18 of the review): for the owner's home, under the study's folder ($ST/skill-aside/), outside /tmp, so a reboot or
# macOS's periodic /tmp cleanup cannot lose the owner's copy while a cut-off step waits for its recover; the move then crosses volumes (a
# copy and a delete by mv), and dir_ok checks both sides. For the self-check's constructed home, under $P/skill-aside/.
if [[ "$HOME" == "$OWNER_HOME" ]]; then
  REC=$EV/skill-moves.txt; ASIDE=$ST/skill-aside
elif [[ "$HOME" == /tmp/hirearchy-p2/* || "$HOME" == /private/tmp/hirearchy-p2/* ]]; then
  REC=$P/selfcheck-skill-moves.txt; ASIDE=${P2_SELFCHECK_ASIDE:-$P/skill-aside}   # the self-check may point it at the study folder (a cross-volume move)
else
  echo "skill_move.sh: refused: HOME=$HOME is neither the owner's home nor a self-check home under /tmp/hirearchy-p2/" >&2; exit 2
fi
SRC=$HOME/.kiro/skills/hirearchy
now() { date -u +%Y-%m-%dT%H:%M:%SZ; }
dir_ok() {  # dir_ok <dir>: exactly SKILL.md, with the wanted md5
  local d="$1"
  [[ -d "$d" && ! -L "$d" ]] || return 1
  local entries=("${(@f)$(ls -A "$d" 2>/dev/null)}")
  [[ ${#entries} -eq 1 && "${entries[1]}" == SKILL.md ]] || return 1
  [[ "$(md5 -q "$d/SKILL.md" 2>/dev/null)" == $WANT ]] || return 1
  return 0
}
unrestored() {  # the labels with an ASIDE line and no later RESTORE line
  [[ -f $REC ]] || return 0
  awk '$1=="ASIDE" || $1=="ASIDE-PENDING"{open[$2]=$0} $1=="RESTORE"{delete open[$2]} END{for (l in open) print l}' $REC
}
case "$MODE" in
  aside)
    [[ -n "$LABEL" ]] || { echo "usage: skill_move.sh aside <label>" >&2; exit 2; }
    u=$(unrestored); [[ -z "$u" ]] || { echo "STOP: skill aside refused: an earlier move has no restore: $u" | tr '\n' ' '; echo; exit 3; }
    dir_ok $SRC || { echo "STOP: skill aside refused: $SRC is not a directory holding only SKILL.md with md5 $WANT ($(ls -A $SRC 2>&1 | tr '\n' ' '); md5 $(md5 -q $SRC/SKILL.md 2>&1))"; exit 3; }
    DEST=$ASIDE/$LABEL-$(date +%s)/hirearchy
    mkdir -p ${DEST:h} || { echo "STOP: skill aside: cannot create ${DEST:h}"; exit 3; }
    # F33 of review 2: the record comes BEFORE the move, so a step cut between the two (the move crosses volumes) leaves an open move
    # that `status` shows and `recover` restores
    echo "ASIDE-PENDING $LABEL $(now) from $SRC to $DEST" >> $REC
    mv $SRC $DEST || { echo "STOP: skill aside: mv failed"; exit 3; }
    if [[ ! -e $SRC ]] && dir_ok $DEST; then
      echo "ASIDE $LABEL $(now) from $SRC to $DEST md5 $WANT ok" >> $REC
      echo "skill aside: $SRC -> $DEST (md5 $WANT before and after; recorded in $REC)"
      exit 0
    fi
    echo "STOP: skill aside: the check after the move failed (src exists: $([[ -e $SRC ]] && echo yes || echo no); dest md5 $(md5 -q $DEST/SKILL.md 2>&1))"
    echo "ASIDE $LABEL $(now) from $SRC to $DEST CHECK-FAILED" >> $REC
    exit 3 ;;
  restore)
    [[ -n "$LABEL" ]] || { echo "usage: skill_move.sh restore <label>" >&2; exit 2; }
    LINE=$( [[ -f $REC ]] && awk -v l="$LABEL" '($1=="ASIDE" || $1=="ASIDE-PENDING") && $2==l {a=$0} $1=="RESTORE" && $2==l {a=""} END{print a}' $REC )
    if [[ -z "$LINE" ]]; then
      if dir_ok $SRC; then echo "skill restore: nothing to restore for $LABEL; $SRC in place with md5 $WANT"; exit 0; fi
      echo "STOP: skill restore impossible: no move of $LABEL is recorded and $SRC is not in place with md5 $WANT"; exit 3
    fi
    DEST=$(print -r -- "$LINE" | awk '{for(i=1;i<=NF;i++) if($i=="to") print $(i+1)}')
    if [[ "$LINE" == ASIDE-PENDING* && ! -e $DEST ]] && dir_ok $SRC; then   # the step was cut before its mv ran: nothing moved
      echo "RESTORE $LABEL $(now) nothing to move back: the pending aside to $DEST never ran; $SRC in place md5 $WANT ok" >> $REC
      [[ -d $EV/$LABEL ]] && echo "restored $(now): nothing moved (pending aside never ran); $SRC md5 $WANT ok" >> $EV/$LABEL/skill-restore.txt
      echo "skill restore: the pending aside of $LABEL never ran; $SRC in place with md5 $WANT (recorded)"
      exit 0
    fi
    if [[ -e $SRC ]]; then echo "STOP: skill restore impossible: $SRC exists already (aside copy at $DEST): nothing changed"; exit 3; fi
    dir_ok $DEST || { echo "STOP: skill restore impossible: the aside copy $DEST is missing or changed (md5 $(md5 -q $DEST/SKILL.md 2>&1)): nothing changed"; exit 3; }
    mv $DEST $SRC || { echo "STOP: skill restore: mv failed"; exit 3; }
    if dir_ok $SRC && [[ ! -e $DEST ]]; then
      rmdir ${DEST:h} 2>/dev/null
      echo "RESTORE $LABEL $(now) from $DEST to $SRC md5 $WANT ok" >> $REC
      [[ -d $EV/$LABEL ]] && echo "restored $(now): $DEST -> $SRC md5 $WANT ok" >> $EV/$LABEL/skill-restore.txt
      echo "skill restore: $DEST -> $SRC (md5 $WANT; recorded)"
      exit 0
    fi
    echo "STOP: skill restore: the check after the move failed (md5 $(md5 -q $SRC/SKILL.md 2>&1))"; exit 3 ;;
  status)
    u=$(unrestored)
    echo "global skill: $( dir_ok $SRC && echo "in place, md5 $WANT" || echo "NOT in place ($( [[ -e $SRC ]] && md5 -q $SRC/SKILL.md 2>&1 || echo absent))")"
    if [[ -n "$u" ]]; then for l in ${(f)u}; do echo "UNRESTORED $l"; done; exit 1; fi
    echo "no unrestored move"; exit 0 ;;
  recover)
    u=$(unrestored); rc=0
    if [[ -z "$u" ]]; then echo "skill recover: no unrestored move; global skill: $( dir_ok $SRC && echo "in place, md5 $WANT" || echo NOT in place)"; exit 0; fi
    for l in ${(f)u}; do
      if zsh ${0:A} restore $l; then echo "RECOVERED $l $(now)" | tee -a $REC; else echo "STOP: skill recover of $l failed"; rc=3; fi
    done
    exit $rc ;;
  *) echo "usage: skill_move.sh aside|restore|status|recover <label>" >&2; exit 2 ;;
esac
