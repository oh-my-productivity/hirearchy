#!/bin/zsh
# P2 read-only copy of a stream's org into its evidence folder (P1's copy_org_evidence.sh, with the arm's CLI and P2's additions; protocol 3.5).
# Usage: copy_org_evidence.sh <S> <label>          (a selfcheck-* label writes into $P2_EVDIR)
# P1's copies, unchanged in form: msgs/ (root's sent, inbox, read; each agent's as <agent>-<kind>), run-logs/, events/, org-files/ (ORG.md,
# every AGENT.md, MEMORY.md and review file, the current SERVICE.md and PLAYBOOK.md of each service), org-git-log.txt, the study service's
# contract and playbook versions under service/ and playbook/ (the names P1's rederive_watch.py reads), memos/ (the deliverables), and the
# read-only CLI listings (services, progress, status, health; obs trace of root's tasks), through the ARM's CLI.
# P2 adds: services-all/<owner>--<name>/{service,playbook}/ for EVERY service (history/ versions and the current file; retired copies under
# services-all/<owner>--.retired--<name>/); org-copy/ (the org's files without .git: AGENT.md and RETIRED.md of live and retired agents,
# .runtime/ with the ledger); org-files/retros.json; charter-history.txt (`git log -p --reverse --no-renames --format='COMMIT %H %ct %s'
# -- '*/AGENT.md'`) and charter-history-commits.txt (`git log --reverse --format=%H -- '*/AGENT.md'`, its fail-closed count); org-git.bundle
# (the whole history, `git bundle create --all`). The study service is the service the first apply defined: the SERVICE.md whose v1
# `created` is the earliest.
S="$1"; N="$2"
H0=${0:A:h}
source $H0/arm.sh "$N" || exit 2
EVD=$EV/$N; [[ "$N" == selfcheck-* && -n "$P2_EVDIR" ]] && EVD=$P2_EVDIR
ORG="$S/org"
mkdir -p $EVD/msgs $EVD/run-logs $EVD/events $EVD/org-files $EVD/service $EVD/playbook $EVD/services-all
for d in sent inbox read; do [[ -d $ORG/$d ]] && { mkdir -p $EVD/msgs/$d; cp -p $ORG/$d/* $EVD/msgs/$d/ 2>/dev/null; }; done
find $ORG -type d \( -name sent -o -name inbox -o -name read \) -not -path "$ORG/.git/*" -not -path "$ORG/sent" -not -path "$ORG/inbox" -not -path "$ORG/read" | while read d; do
  rel=${d#$ORG/}; agent=${rel%/*}; kind=${rel##*/}; dest=$EVD/msgs/${agent//\//-}-$kind
  mkdir -p $dest; cp -p $d/* $dest/ 2>/dev/null
done
find $ORG -type d -name runs -not -path "$ORG/.git/*" | while read d; do
  rel=${d#$ORG/}; agent=${rel%/runs}; dest=$EVD/run-logs/${agent//\//-}; mkdir -p $dest; cp -p $d/*.log $dest/ 2>/dev/null
done
cp -pR $ORG/.runtime/events/* $EVD/events/ 2>/dev/null
cp -p $ORG/.runtime/scheduler.log $EVD/scheduler.log 2>/dev/null
cp -p $ORG/.runtime/scheduler.exit $EVD/org-files/scheduler.exit 2>/dev/null
cp -p $ORG/.runtime/reviews.json $EVD/org-files/reviews.json 2>/dev/null
cp -p $ORG/.runtime/retros.json $EVD/org-files/retros.json 2>/dev/null
cp -p $ORG/ORG.md $EVD/org-files/ORG.md 2>/dev/null
find $ORG \( -name AGENT.md -o -name MEMORY.md -o -name RETIRED.md -o -name 'review-*.md' \) -not -path "$ORG/.git/*" | while read f; do rel=${f#$ORG/}; cp -p $f $EVD/org-files/${rel//\//-}; done
find $ORG -path "$ORG/.git" -prune -o \( -name SERVICE.md -o -name PLAYBOOK.md \) -print | while read f; do rel=${f#$ORG/}; cp -p $f $EVD/org-files/current-${rel//\//-}; done
git -C $ORG log --stat --date=iso > $EVD/org-git-log.txt 2>&1
# every service: its versions (history/ and the current file)
find $ORG -path "$ORG/.git" -prune -o -type f -name SERVICE.md -path '*/services/*' -print | while read f; do
  sdir=${f:h}; rel=${sdir#$ORG/}; owner=${rel%%/services/*}; name=${rel##*/services/}
  key=${owner//\//-}--${name//\//--}
  mkdir -p $EVD/services-all/$key/service $EVD/services-all/$key/playbook
  cp -p $sdir/history/SERVICE.v*.md(N) $EVD/services-all/$key/service/ 2>/dev/null
  cp -p $sdir/history/RETIRED*.md(N) $EVD/services-all/$key/service/ 2>/dev/null
  cp -p $sdir/SERVICE.md $EVD/services-all/$key/service/current-SERVICE.md
  cp -p $sdir/history/PLAYBOOK.v*.md(N) $EVD/services-all/$key/playbook/ 2>/dev/null
  [[ -f $sdir/PLAYBOOK.md ]] && cp -p $sdir/PLAYBOOK.md $EVD/services-all/$key/playbook/current-PLAYBOOK.md
  [[ -f $sdir/RETIRED.md ]] && cp -p $sdir/RETIRED.md $EVD/services-all/$key/service/RETIRED.md
  echo "$key $(python3 -c 'import sys,re; t=open(sys.argv[1]).read(); m=re.search(r"^created:\s*'"'"'?([^'"'"'\n]+)",t,re.M); print(m.group(1) if m else "")' $(ls $sdir/history/SERVICE.v1.md(N) $sdir/SERVICE.md | head -1))" >> $EVD/services-all/created.txt
done
# the study service (the earliest created) under P1's names, for rederive_watch.py unchanged
if [[ -f $EVD/services-all/created.txt ]]; then
  STUDY=$(sort -k2 $EVD/services-all/created.txt | head -1 | awk '{print $1}')
  echo "$STUDY" > $EVD/services-all/study-service.txt
  cp -p $EVD/services-all/$STUDY/service/*.md(N) $EVD/service/ 2>/dev/null
  cp -p $EVD/services-all/$STUDY/playbook/*.md(N) $EVD/playbook/ 2>/dev/null
fi
# the org's files without .git (charters, RETIRED.md records, the runtime), the charter history and the whole history as a bundle
mkdir -p $EVD/org-copy
rsync -a --exclude .git $ORG/ $EVD/org-copy/ 2>/dev/null || cp -pR $ORG/. $EVD/org-copy/
rm -rf $EVD/org-copy/.git
git -C $ORG log -p --reverse --no-renames --format='COMMIT %H %ct %s' -- '*/AGENT.md' 'AGENT.md' > $EVD/charter-history.txt 2>&1
git -C $ORG log --reverse --format=%H -- '*/AGENT.md' 'AGENT.md' > $EVD/charter-history-commits.txt 2>&1
git -C $ORG bundle create $EVD/org-git.bundle --all > /dev/null 2>&1 || echo "NOTE: no git bundle (no history)"
[[ -d $S/deliverables ]] && { mkdir -p $EVD/memos; cp -p $S/deliverables/* $EVD/memos/ 2>/dev/null; }
{
  for c in services progress status health; do echo "######## hirearchy --root $ORG $c ($REPO_A)"; "${HIR[@]}" --root $ORG $c 2>&1; echo; done
} > $EVD/final-services-progress-status-health.txt
{
  for f in $ORG/sent/*-root-*.md(N); do id=$(basename $f .md); echo "######## hirearchy --root $ORG obs trace $id"; "${HIR[@]}" --root $ORG obs trace $id 2>&1; echo; done
} > $EVD/observe-traces.txt
echo "copied; services $(ls $EVD/services-all 2>/dev/null | grep -- -- | tr '\n' ' '); charter commits $(wc -l < $EVD/charter-history-commits.txt | tr -d ' ')"
