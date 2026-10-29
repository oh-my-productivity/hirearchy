#!/bin/zsh
# P2 stream finish (P1's finish_stream.sh with the arm parameter; protocol 3.5). Usage: finish_stream.sh <label> --end <reason>
#  <reason> (protocol 3.7): retro-2-done (the script's own end), cap-turns, cap-runs, two-L-WAIT, ruling, credits or stopped; written first
#  as <label>/end.txt `end <reason> at turn <n>` (n = the last turn), unless end.txt exists. Without --end no end.txt is written, and every
#  check whose event did not happen reads NOT DETERMINED (FAIL-CLOSED: the stream's end is not recorded).
# In order, never stopping on one failure (exit codes in finish-steps.txt; failures in finish-failures.txt; exit 1 if any failed):
#  1. the injection script's --stop if a scheduler still runs; 2. copy_org_evidence.sh; 3. `hirearchy check`; 4. the end snapshots (quality,
#  services; arm R: the retro snapshot `end` with --since-apply T0, T0 from extract_p2.py --facts); 5. P1's extracts (unchanged) and P2's
#  extract_p2.py --facts; 6. model_check.sh all; skill_check.sh end; 7. the profile deleted with a record; 8. safety-after.txt,
#  memories-md5-after.txt (a change prints STOP:), the empty-call total, the effort-stop total, credits.txt (cost_total.py), both freezes
#  again in setup.txt; 9. ARM C: skill_move.sh restore <label>, LAST. Scoring is step 12's (extract_p2.py --checks, gate_p1.py, aggregate.py).
LABEL="$1"; ENDR=""; [[ "$2" == "--end" ]] && ENDR="$3"
H0=${0:A:h}
source $H0/arm.sh "$LABEL" || exit 2
D=$EV/$LABEL; [[ -f $D/sandbox-path.txt ]] || { echo "finish_stream.sh: $D/sandbox-path.txt missing" >&2; exit 2; }
if [[ -n "$ENDR" ]]; then
  [[ "$ENDR" =~ '^(retro-2-done|cap-turns|cap-runs|two-L-WAIT|ruling|credits|stopped)$' ]] || { echo "finish_stream.sh: --end takes retro-2-done, cap-turns, cap-runs, two-L-WAIT, ruling, credits or stopped" >&2; exit 2; }
  [[ -f $D/end.txt ]] || echo "end $ENDR at turn $(grep -c '^turn ' $D/turn-times.txt 2>/dev/null || echo 0) ($(date -u +%FT%TZ))" > $D/end.txt
fi
S=$(cat $D/sandbox-path.txt)
mkdir -p $D/measures $D/rederived $D/profiles $D/quality $D/services
STEPS=$D/finish-steps.txt; FAILS=$D/finish-failures.txt; nfail=0
echo "# finish_stream.sh $LABEL started $(date -u +%FT%TZ)" >> $STEPS
step() { local name="$1" out="$2"; shift 2; "$@" > "$out" 2>&1; local rc=$?; echo "$name exit $rc -> ${out#$D/} (argv: $*)" >> $STEPS
  (( rc != 0 )) && { nfail=$((nfail+1)); echo "$name exit $rc: $*" >> $FAILS; echo "STEP FAILED: $name"; } || echo "ok: $name"; }
if [[ -f $S/org/.runtime/scheduler.pid ]] && ps -p $(tr -dc '0-9' < $S/org/.runtime/scheduler.pid) > /dev/null 2>&1; then
  step "injection --stop" $D/scheduler-stop.txt zsh $H0/injection.sh $LABEL --stop
fi
step copy_org_evidence $D/copy_org_evidence-output.txt zsh $H0/copy_org_evidence.sh $S $LABEL
[[ -d $S/injection ]] && { mkdir -p $D/injection; cp -pR $S/injection/. $D/injection/; }
{ "${HIR[@]}" --root $S/org check; echo "exit code: $?"; } > $D/observe-check.txt 2>&1
step "quality end" $D/quality/end-output.txt zsh $H0/quality_snapshot.sh $LABEL end
step "services end" $D/services/end-output.txt zsh $H0/services_snapshot.sh $LABEL end
step extract_tool_calls $D/extract_tool_calls-output.txt python3 -B $H0/extract_tool_calls.py $D/assistant-session-messages.jsonl $D/assistant-tool-calls.txt $D/session-turn-times-utc.txt
step extract_p2_facts $D/extract_p2-facts-output.txt python3 -B $H0/extract_p2.py $D --facts
T0=$(cat $D/p2/t0.txt 2>/dev/null | tr -d '\n')
if [[ $ARM == R ]]; then
  if [[ -n "$T0" ]]; then step "retro end" $D/retro/end-output.txt zsh $H0/retro_snapshot.sh $LABEL end --since-apply "$T0"
  else step "retro end" $D/retro/end-output.txt zsh $H0/retro_snapshot.sh $LABEL end; fi
fi
step extract_proposals $D/measures/extract_proposals-output.txt python3 -B $H0/extract_proposals.py $D
# F31 of review 2: P1's extract imports the product's client_questions from --product-src; it is the arm's product (REPO_A), so no arm-C
# call reaches REPO_R (P1's default path is REPO_R's src). Protocol amendment 1 item 5 (B): P1's extract_mechanical.py (unchanged, pinned)
# runs through extract_mechanical_p2.py, which reads an effort-stopped run's session folder without messages.jsonl as empty, counts the
# stop in cost.txt, and fails closed on any other such folder
EM_ARGV=(python3 -B $H0/extract_mechanical_p2.py $D $S --product-src $REPO_A/src)
step extract_mechanical $D/extract_mechanical-output.txt "${EM_ARGV[@]}"
step scheduler_survival $D/measures/scheduler_survival-output.txt python3 -B $H0/scheduler_survival.py $D --out $D/measures
step injection_files $D/measures/injection_files-output.txt python3 -B $H0/injection_files.py $D $S
step assistant_facts $D/measures/assistant_facts-output.txt python3 -B $H0/assistant_facts.py $D --out $D/measures
step prompt_sizes $D/measures/prompt_sizes-output.txt python3 -B $H0/prompt_sizes.py $D --out $D/measures
step playbook_attempts $D/measures/playbook_attempts-output.txt python3 -B $H0/playbook_attempts.py $D --out $D/measures
zsh $H0/model_check.sh all $LABEL $S > $D/measures/model_check-all-output.txt 2>&1 || { nfail=$((nfail+1)); echo "model_check all failed" >> $FAILS; }
step "skill_check end" $D/skill-check-end-output.txt zsh $H0/skill_check.sh $LABEL end
PF=$HOME/.kiro/agents/$PNAME.json
if [[ -f $PF ]]; then
  PMD5=$(md5 -q $PF); cmp -s $PF $D/profiles/$PNAME.json || { cp -p $D/profiles/$PNAME.json $D/profiles/$PNAME.created.json; echo "NOTE: the profile changed during the stream" >> $FAILS; }
  cp -p $PF $D/profiles/$PNAME.json && cmp -s $PF $D/profiles/$PNAME.json && rm -f $PF
  [[ ! -e $PF ]] && echo "profile deleted $(date -u +%FT%TZ): $PF md5 $PMD5" >> $D/profiles/deletions.txt || { echo "profile NOT deleted: $PF" >> $FAILS; nfail=$((nfail+1)); }
else echo "no profile at $PF (deleted already?)" >> $D/profiles/deletions.txt; fi
zsh $H0/safety-snapshot.sh "$LABEL after" > $D/safety-after.txt 2>&1
diff <(grep -v '^date' $D/safety-before.txt) <(grep -v '^date' $D/safety-after.txt) > $D/safety-diff.txt 2>&1
MDB=$HOME/.kiro/memories/memories.db; { [[ -f $MDB ]] && md5 -q $MDB || echo absent; } > $D/memories-md5-after.txt
if [[ "$(cat $D/memories-md5-after.txt)" != "$(cat $D/memories-md5-before.txt 2>/dev/null)" ]]; then
  echo "memories.db CHANGED during $LABEL: $(cat $D/memories-md5-before.txt) -> $(cat $D/memories-md5-after.txt)" >> $D/memories-db.txt
  echo "STOP: memories.db changed during $LABEL: send a warning before the next stream and wait (never restore or edit the store)"
else echo "memories.db unchanged during $LABEL: $(cat $D/memories-md5-after.txt)" >> $D/memories-db.txt; fi
{ echo "total: $(python3 -B $H0/empty_calls.py $D/assistant-session-messages.jsonl 2>/dev/null)"; echo "total 'is not available' in turn stderr: $(cat $D/turn-*.stderr.txt(N) 2>/dev/null | grep -c 'is not available')"; } >> $D/empty-calls.txt
python3 -B $H0/effort_stops.py $S/org >> $D/effort-stops.txt 2>&1
python3 -B $H0/cost_total.py $D/cost.txt > $D/credits.txt 2>&1; echo "credits: $(cat $D/credits.txt)"
{ echo; echo "== AFTER the last turn"; freeze_lines; echo "md5 gate:"; md5gate_ok; echo "~/.kiro/agents: $(ls $HOME/.kiro/agents | tr '\n' ' ')"; } >> $D/setup.txt 2>&1
if [[ $ARM == C ]]; then zsh $H0/skill_move.sh restore $LABEL | tee -a $D/skill-restore.txt; fi
echo "# finish_stream.sh $LABEL ended $(date -u +%FT%TZ); failed steps: $nfail" >> $STEPS
echo "finished $LABEL: $nfail failed step(s); global skill: $(zsh $H0/skill_move.sh status | head -1)"
(( nfail > 0 )) && exit 1
exit 0
