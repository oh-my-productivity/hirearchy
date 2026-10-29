#!/bin/zsh
# P2: one P1-shaped view per service, so P1's rederive_watch.py runs unchanged on each (protocol 12.3 G1(f), 16 item 24).
# Usage: watch_views.sh <stream evidence dir>  -> <dir>/watch-views/<owner>--<name>/ (msgs, quality, services, turn-times.txt and the
# service's own service/ and playbook/), then rederive_watch.py <view> --out <dir>/watch/<owner>--<name>/ for each.
E="$1"; H0=${0:A:h}
for s in $E/services-all/*--*(/N); do
  k=${s:t}; V=$E/watch-views/$k; rm -rf $V; mkdir -p $V
  for x in msgs quality services turn-times.txt; do [[ -e $E/$x ]] && ln -s $E/$x $V/$x; done
  ln -s $s/service $V/service; ln -s $s/playbook $V/playbook
  mkdir -p $E/watch/$k
  python3 -B $H0/rederive_watch.py $V --out $E/watch/$k > $E/watch/$k/rederive_watch-output.txt 2>&1; echo "watch $k: exit $? ($(tail -1 $E/watch/$k/watch-mismatches.txt 2>/dev/null))"
done
