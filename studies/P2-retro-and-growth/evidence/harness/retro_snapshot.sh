#!/bin/zsh
# P2 retro snapshot, arm R only (protocol 3.3). Usage: retro_snapshot.sh <label> <tag> [--since-apply <ISO datetime with offset>]
# `hirearchy retro` without --since RECORDS a brief when a verdict of the user arrived since the last one (design 4.2), so this script never
# runs `retro` on the stream's org. It:
#   1. copies <S>/org/.runtime/retros.json byte for byte to <label>/ledger/<tag>.json (or writes <tag>.absent), with its md5;
#   2. copies <S>/org (git history included) to P/retro-scratch/<label>/<tag>/org and runs on the COPY only:
#      `hirearchy --root <copy> retro --json`                          -> <label>/retro/<tag>.json         (a brief called now)
#      `hirearchy --root <copy> retro --since <org start> --json`      -> <label>/retro/<tag>.lookback.json (recorded nowhere)
#      with --since-apply T0 also `... retro --since <T0> --json`      -> <label>/retro/<tag>.since-apply.json (P2-X3's window)
#      the organization's start = `since` of the copy's first ledger record (after the first call it has one);
#   3. checks that the stream org's ledger md5 is the same before and after (else `STOP: the retro snapshot changed the stream's ledger`),
#      and deletes the scratch copy. Every call's UTC start and end, exit code, bytes and JSON check go to <label>/retro/calls.txt.
# With no <S>/org/ORG.md: `no org yet`, nothing run (the CLI would create <S>/org/.runtime/ before create_org).
LABEL="$1"; TAG="$2"; shift 2
SINCE_APPLY=""; [[ "$1" == --since-apply ]] && SINCE_APPLY="$2"
H0=${0:A:h}
source $H0/arm.sh "$LABEL" || exit 2
[[ $ARM == R ]] || { echo "retro_snapshot.sh: arm $ARM has no retro (protocol 3.3)" >&2; exit 2; }
[[ "$TAG" =~ '^(turn-[0-9][0-9]+|end)$' ]] || { echo "usage: retro_snapshot.sh <label> turn-NN|end [--since-apply T0]" >&2; exit 2; }
D=$EV/$LABEL; [[ "$LABEL" == selfcheck-* && -n "$P2_EVDIR" ]] && D=$P2_EVDIR
S=$(cat $D/sandbox-path.txt)
mkdir -p $D/ledger $D/retro
L=$S/org/.runtime/retros.json
if [[ ! -e "$S/org/ORG.md" ]]; then echo "$TAG $(date -u +%FT%TZ): no org yet, retro not run" >> $D/retro/calls.txt; echo "retro $TAG: no org yet"; exit 0; fi
utcus() { python3 -c 'import datetime;print(datetime.datetime.now(datetime.timezone.utc).isoformat())'; }
lmd5() { [[ -f $L ]] && md5 -q $L || echo absent; }
B=$(lmd5)
if [[ -f $L ]]; then cp -p $L $D/ledger/$TAG.json; else : > $D/ledger/$TAG.absent; fi
echo "$TAG $(utcus) ledger md5 $B" >> $D/ledger/calls.txt
SCR=$P/retro-scratch/$LABEL/$TAG
[[ "$SCR" == $P/retro-scratch/* ]] || exit 2
rm -rf $SCR; mkdir -p $SCR
cp -pR $S/org $SCR/org || { echo "NOTE: retro $TAG: the scratch copy failed"; echo "$TAG copy FAILED" >> $D/retro/calls.txt; exit 0; }
run() {  # run <out file> <args...>: the arm's CLI on the copy
  local out="$1"; shift
  local s=$(utcus)
  "${HIR[@]}" --root $SCR/org retro "$@" > $out 2> ${out%.json}.stderr.txt; local rc=$?
  local e=$(utcus); local by=$(wc -c < $out | tr -d ' ')
  local ok=$(python3 -c 'import json,sys; json.load(open(sys.argv[1]))' $out > /dev/null 2>&1 && echo ok || echo invalid)
  echo "$TAG ${out:t} start $s end $e exit $rc bytes $by json $ok args $*" >> $D/retro/calls.txt
  [[ $rc -ne 0 || $ok != ok ]] && echo "NOTE: retro $TAG ${out:t} is unread (exit $rc, json $ok)"
}
run $D/retro/$TAG.json --json
START=$(python3 -c '
import json,sys
try:
    r=json.load(open(sys.argv[1]))["briefs"]
    print(r[0]["since"] if r else "")
except Exception:
    print("")' $SCR/org/.runtime/retros.json)
if [[ -n "$START" ]]; then run $D/retro/$TAG.lookback.json --since "$START" --json; else echo "$TAG lookback: no organization start known (no record in the copy)" >> $D/retro/calls.txt; fi
[[ -n "$SINCE_APPLY" ]] && run $D/retro/$TAG.since-apply.json --since "$SINCE_APPLY" --json
A=$(lmd5)
echo "$TAG $(utcus) stream ledger md5 before $B after $A" >> $D/retro/calls.txt
[[ "$A" == "$B" ]] || echo "STOP: the retro snapshot changed the stream's ledger ($B -> $A; protocol 3.3, H6)"
rm -rf $SCR
echo "retro $TAG: done (ledger $A)"
exit 0
