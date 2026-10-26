#!/bin/zsh
# G0: read-only copy of a stream's org into the evidence folder (protocol 7.2 "The org"), after the stream ended (E7's, plus memos/versions/).
# Usage: copy_org_evidence.sh <S> <label>
# Uses only file copies and the read-only CLI commands of protocol 4.8 (services | progress | status | health, obs trace).
S="$1"; N="$2"
EV=/Volumes/workspace/hirearchy/studies/G0-noise-baseline/evidence/$N
ORG="$S/org"
HIR="uv --directory /Volumes/workspace/hirearchy run hirearchy"
mkdir -p $EV/msgs $EV/run-logs $EV/events $EV/org-files $EV/service $EV/playbook
# messages: root's folders and each agent's
for d in sent inbox read; do [[ -d $ORG/$d ]] && { mkdir -p $EV/msgs/$d; cp -p $ORG/$d/* $EV/msgs/$d/ 2>/dev/null; }; done
find $ORG -type d \( -name sent -o -name inbox -o -name read \) -not -path "$ORG/.git/*" -not -path "$ORG/sent" -not -path "$ORG/inbox" -not -path "$ORG/read" | while read d; do
  rel=${d#$ORG/}; agent=${rel%/*}; kind=${rel##*/}; dest=$EV/msgs/${agent//\//-}-$kind
  mkdir -p $dest; cp -p $d/* $dest/ 2>/dev/null
done
# run logs
find $ORG -type d -name runs -not -path "$ORG/.git/*" | while read d; do
  rel=${d#$ORG/}; agent=${rel%/runs}; dest=$EV/run-logs/${agent//\//-}; mkdir -p $dest; cp -p $d/*.log $dest/ 2>/dev/null
done
# runtime
cp -pR $ORG/.runtime/events/* $EV/events/ 2>/dev/null
cp -p $ORG/.runtime/scheduler.log $EV/scheduler.log 2>/dev/null
cp -p $ORG/.runtime/scheduler.exit $EV/org-files/scheduler.exit 2>/dev/null
cp -p $ORG/.runtime/reviews.json $EV/org-files/reviews.json 2>/dev/null
cp -p $ORG/ORG.md $EV/org-files/ORG.md 2>/dev/null
find $ORG -name AGENT.md -not -path "$ORG/.git/*" | while read f; do rel=${f#$ORG/}; cp -p $f $EV/org-files/${rel//\//-}; done
find $ORG -name MEMORY.md -not -path "$ORG/.git/*" | while read f; do rel=${f#$ORG/}; cp -p $f $EV/org-files/${rel//\//-}; done
find $ORG -name 'review-*.md' -not -path "$ORG/.git/*" | while read f; do rel=${f#$ORG/}; cp -p $f $EV/org-files/${rel//\//-}; done
# services and playbook (current files; versions come from git history)
find $ORG -path "$ORG/.git" -prune -o -name SERVICE.md -print -o -name PLAYBOOK.md -print | while read f; do rel=${f#$ORG/}; cp -p $f $EV/org-files/current-${rel//\//-}; done
git -C $ORG log --stat --date=iso > $EV/org-git-log.txt 2>&1
# every committed version of SERVICE.md / PLAYBOOK.md
git -C $ORG log --reverse --format='%h %cI' -- '*SERVICE.md' | while read h t; do f=$(git -C $ORG ls-files -- '*SERVICE.md' | head -1); git -C $ORG show $h:$f > $EV/service/SERVICE.$h.md 2>/dev/null; echo "$h $t" >> $EV/service/versions.txt; done
git -C $ORG log --reverse --format='%h %cI' -- '*PLAYBOOK.md' | while read h t; do f=$(git -C $ORG ls-files -- '*PLAYBOOK.md' | head -1); git -C $ORG show $h:$f > $EV/playbook/PLAYBOOK.$h.md 2>/dev/null; echo "$h $t" >> $EV/playbook/versions.txt; done
# deliverables
[[ -d $S/deliverables ]] && { mkdir -p $EV/memos; cp -p $S/deliverables/* $EV/memos/ 2>/dev/null; }
# memos/versions/ is NOT written here: extract_mechanical.py writes it (E7's rule: every .md under the owner's */work/ folders except the
# final-check seat's, every committed version, and INDEX.txt), from the sandbox org's git, when finish_stream.sh runs it after this script.
# One writer only, so the index keeps E7's rule (protocol 15 item 14; a draft of this script also indexed the reviewer's work files).
# read-only CLI after the stream
{
  for c in services progress status health; do echo "######## hirearchy --root $ORG $c"; ${=HIR} --root $ORG $c 2>&1; echo; done
} > $EV/final-services-progress-status-health.txt
{
  for f in $ORG/sent/*-root-*.md(N); do id=$(basename $f .md); case "$id" in *root-*) ;; esac; echo "######## hirearchy --root $ORG obs trace $id"; ${=HIR} --root $ORG obs trace $id 2>&1; echo; done
} > $EV/observe-traces.txt
echo "copied; $(ls $EV/run-logs 2>/dev/null | tr '\n' ' ')"
