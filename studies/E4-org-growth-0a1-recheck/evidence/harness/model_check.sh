#!/bin/zsh
# usage: modelcheck.sh "<label>"   appends to s3/model-checks.txt; exit 0 if both models OK
LABEL="$1"; OUT=/Volumes/workspace/hirearchy/studies/E4-org-growth-0a1-recheck/evidence/s3/model-checks.txt
PREP=hirearchy-study-e4-prep-1792693245
echo "## model check: $LABEL (started $(date -u +%FT%TZ))" >> $OUT
cd /tmp/hirearchy-e4-prep-1792693245 || exit 90
for m in claude-sonnet-4.6 claude-haiku-4.5; do
  ok=0
  for a in 1 2 3 4 5 6 7; do
    ts=$(date -u +%FT%TZ)
    rep=$(kiro-cli chat --v3 --no-interactive --trust-all-tools --agent $PREP --model $m "Reply with OK." 2>/tmp/e4-s3-mc.err); rc=$?
    err=$(tr '\n' ' ' < /tmp/e4-s3-mc.err | cut -c1-300)
    echo "[$ts] $LABEL model=$m attempt=$a exit=$rc reply=<<$(echo $rep | tr '\n' ' ')>> stderr=<<$err>>" >> $OUT
    if [[ $rc -eq 0 && "$rep" == *OK* ]]; then echo "  -> success" >> $OUT; ok=1; break; fi
    echo "  -> failed; waiting 600s" >> $OUT
    [[ $a -lt 7 ]] && sleep 600
  done
  [[ $ok -eq 1 ]] || { echo "RESULT: $LABEL FAILED for $m after 7 attempts ($(date -u +%FT%TZ))" >> $OUT; exit 1; }
done
echo "RESULT: $LABEL both models OK ($(date -u +%FT%TZ))" >> $OUT
