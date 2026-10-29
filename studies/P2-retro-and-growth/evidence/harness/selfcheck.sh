#!/bin/zsh
# P2 harness self-check (protocol 13.3). Usage: selfcheck.sh   -> EV/harness-selfcheck/ (one .out file per part, selfcheck-summary.txt)
# Parts: 1. the modules' constructed cases (skill_proof, effort_stops, running_credits, lena_lines, score_p2, aggregate, probe_compare,
# selfcheck_cases: the re-derivation and every check's fail-closed rule); 2. P1's unchanged modules' own self-checks where they run on kept
# G0/P1 data (cost_total --selfcheck, empty_calls --selfcheck); 3. the skill move on a constructed home under /tmp/hirearchy-p2/ (never the
# owner's); 4. the arm-C injection's one-line diff; the profile template's masked equality across the arms; 5. the one wrapper per turn with
# a fake chat (a selfcheck label: the fake chat and the 1-s boundary are refused for any other label); 5c. the signal traps of probe.sh and
# setup_stream.sh on stub scripts sent TERM (C4); 6. the dry run in EACH arm
# (dryrun.sh R, dryrun.sh C). The last line: `SELFCHECK: <k> of <n> parts passed`.
H0=${0:A:h}
source $H0/arm.sh selfcheck-R >/dev/null || exit 2
OUT=$EV/harness-selfcheck; mkdir -p $OUT
SUM=$OUT/selfcheck-summary.txt; echo "# P2 self-check $(date -u +%FT%TZ)" > $SUM
n=0; k=0
part() { local name="$1" out="$2"; shift 2; n=$((n+1)); "$@" > $OUT/$out 2>&1; local rc=$?
  if (( rc == 0 )); then k=$((k+1)); echo "PASS  $name ($(tail -1 $OUT/$out))" | tee -a $SUM; else echo "FAIL  $name (exit $rc; $OUT/$out)" | tee -a $SUM; fi; }
cd $H0
part "skill_proof" skill_proof.out python3 -B skill_proof.py --selfcheck --out $OUT/skill_proof
part "effort_stops" effort_stops.out python3 -B effort_stops.py --selfcheck
part "running_credits" running_credits.out python3 -B running_credits.py --selfcheck
part "lena_lines" lena_lines.out python3 -B lena_lines.py --selfcheck
part "score_p2" score_p2.out python3 -B score_p2.py --selfcheck --out $OUT/score_p2
part "aggregate" aggregate.out python3 -B aggregate.py --selfcheck $P/selfcheck-aggregate
rm -rf $P/selfcheck-probe $P/selfcheck-gate $P/selfcheck-gate-p1 $P/selfcheck-aggregate
part "probe_compare (constructed probe folders)" probe_compare.out python3 -B probe_compare.py --selfcheck $P/selfcheck-probe
part "stage_gate (17.6's stop rule on constructed folders)" stage_gate.out python3 -B stage_gate.py --selfcheck $P/selfcheck-gate
part "gate_p1 (P1's gate-able measures on constructed streams)" gate_p1.out python3 -B gate_p1.py --selfcheck $P/selfcheck-gate-p1
part "selfcheck_cases (re-derivation, checks)" selfcheck_cases.out python3 -B selfcheck_cases.py --out $OUT/cases
part "P1's cost_total (G0's six totals)" cost_total.out python3 -B cost_total.py --selfcheck --out $OUT/cost_total
part "P1's empty_calls (G0's six streams)" empty_calls.out python3 -B empty_calls.py --selfcheck --out $OUT/empty_calls
# 3. the skill move on a constructed home
skill_case() {
  local HM=$P/selfcheck-home; rm -rf $HM $P/selfcheck-skill-moves.txt $P/skill-aside/selfcheck-*; mkdir -p $HM/.kiro/skills/hirearchy $HM/.kiro/skills/other
  cp -p $REPO_R/skills/hirearchy/SKILL.md $HM/.kiro/skills/hirearchy/SKILL.md; echo other > $HM/.kiro/skills/other/SKILL.md
  local OM=$(md5 -q $HM/.kiro/skills/other/SKILL.md) bad=0
  run() { HOME=$HM zsh $H0/skill_move.sh "$@"; }
  run aside selfcheck-C1 || bad=1;           [[ ! -e $HM/.kiro/skills/hirearchy ]] || { echo "aside: still present"; bad=1; }
  run status > /dev/null && { echo "status should report UNRESTORED"; bad=1; }
  run aside selfcheck-C2 > /dev/null && { echo "a second aside must be refused"; bad=1; }
  run restore selfcheck-C1 || bad=1;         [[ "$(md5 -q $HM/.kiro/skills/hirearchy/SKILL.md)" == $SKILL_R_MD5 ]] || { echo "restore: md5"; bad=1; }
  run restore selfcheck-C1 | grep -q 'nothing to restore' || { echo "restore is idempotent"; bad=1; }
  run aside selfcheck-C4 > /dev/null; run recover | grep -q 'RECOVERED selfcheck-C4' || { echo "recover must restore an unrestored move"; bad=1; }
  [[ "$(md5 -q $HM/.kiro/skills/hirearchy/SKILL.md 2>/dev/null)" == $SKILL_R_MD5 ]] && run status > /dev/null || { echo "recover: the copy is back and nothing is open"; bad=1; }
  # the owner's form crosses volumes (/Users -> the study folder on /Volumes/workspace): the same aside and restore, with the md5 on both sides
  P2_SELFCHECK_ASIDE=$ST/selfcheck-aside run aside selfcheck-C5 > /dev/null || { echo "cross-volume aside"; bad=1; }
  [[ -f $(ls -d $ST/selfcheck-aside/selfcheck-C5-*/hirearchy 2>/dev/null | head -1)/SKILL.md && ! -e $HM/.kiro/skills/hirearchy ]] || { echo "cross-volume aside: the copy is not in the study folder"; bad=1; }
  run restore selfcheck-C5 > /dev/null && [[ "$(md5 -q $HM/.kiro/skills/hirearchy/SKILL.md)" == $SKILL_R_MD5 ]] || { echo "cross-volume restore"; bad=1; }
  rmdir $ST/selfcheck-aside 2>/dev/null
  # F33: a step cut between the ASIDE-PENDING record and the mv's check (simulated: the record, then the mv, no ASIDE line); and one cut
  # before the mv ran (the record only)
  local PD=$P/skill-aside/selfcheck-C6-1/hirearchy; mkdir -p ${PD:h}
  echo "ASIDE-PENDING selfcheck-C6 x from $HM/.kiro/skills/hirearchy to $PD" >> $P/selfcheck-skill-moves.txt; mv $HM/.kiro/skills/hirearchy $PD
  run status > /dev/null && { echo "a pending aside whose mv ran must read UNRESTORED"; bad=1; }
  run recover | grep -q 'RECOVERED selfcheck-C6' && [[ "$(md5 -q $HM/.kiro/skills/hirearchy/SKILL.md 2>/dev/null)" == $SKILL_R_MD5 ]] || { echo "recover must restore a pending aside whose mv ran"; bad=1; }
  echo "ASIDE-PENDING selfcheck-C7 x from $HM/.kiro/skills/hirearchy to $P/skill-aside/selfcheck-C7-1/hirearchy" >> $P/selfcheck-skill-moves.txt
  run status > /dev/null && { echo "a pending aside whose mv never ran must read UNRESTORED"; bad=1; }
  run recover | grep -q 'RECOVERED selfcheck-C7' && run status > /dev/null && [[ "$(md5 -q $HM/.kiro/skills/hirearchy/SKILL.md 2>/dev/null)" == $SKILL_R_MD5 ]] || { echo "recover must close a pending aside that never ran, the copy in place"; bad=1; }
  run aside selfcheck-C3 > /dev/null; D=$(awk '$1=="ASIDE" && $2=="selfcheck-C3"{for(i=1;i<=NF;i++) if($i=="to") print $(i+1)}' $P/selfcheck-skill-moves.txt)
  echo tampered >> $D/SKILL.md; run restore selfcheck-C3 | grep -q 'STOP: skill restore impossible' || { echo "a changed aside copy must stop the restore"; bad=1; }
  [[ ! -e $HM/.kiro/skills/hirearchy ]] || { echo "nothing may be restored from a changed copy"; bad=1; }
  [[ "$(md5 -q $HM/.kiro/skills/other/SKILL.md)" == $OM ]] || { echo "another skill changed"; bad=1; }
  HOME=/tmp/elsewhere zsh $H0/skill_move.sh status > /dev/null 2>&1 && { echo "a foreign HOME must be refused"; bad=1; }
  echo "skill_move cases: $( (( bad )) && echo FAILED || echo '18 of 18 ok')"; return $bad
}
part "skill_move (constructed home)" skill_move.out skill_case
# 4. the arm-C injection's one-line diff; the profile template across the arms
inj_case() {
  local d=$(diff $H0/inject_root_rework.py $H0/inject_root_rework_armc.py)
  [[ "$(md5 -q $H0/inject_root_rework.py)" == 1c4e7824e448a3a34e24a7b759a59fcd ]] || { echo "E7's script md5 differs"; return 1; }
  [[ "$(print -r -- "$d" | grep -c '^[<>]')" == 2 && "$d" == *'REPO = "/Volumes/workspace/hirearchy/.worktrees/p2-arm-c"'* && "$(print -r -- "$d" | head -1)" == 36c36 ]] || { echo "diff: $d"; return 1; }
  diff <(sed -e "s/<LABEL>/R1/g; s/<epoch>/1/g; s#<PRODUCT>#$REPO_R#g" $H0/profile-template.json | sed -e "s/R1/<LABEL>/g; s/1\/org/<e>\/org/; s#$REPO_R#<PRODUCT>#g") \
       <(sed -e "s/<LABEL>/C1/g; s/<epoch>/1/g; s#<PRODUCT>#$REPO_C#g" $H0/profile-template.json | sed -e "s/C1/<LABEL>/g; s/1\/org/<e>\/org/; s#$REPO_C#<PRODUCT>#g") || { echo "the masked profiles differ"; return 1; }
  echo "injection: E7's md5 kept, the arm-C form differs in line 36 only; profiles: equal but for label, epoch and product path"
}
part "injection diff and profile masking" injection_profile.out inj_case
# 5. the one wrapper per turn, with a fake chat
wrap_case() {
  local W=$P/selfcheck-wrapper; rm -rf $W; mkdir -p $W/bin $W/ev $W/S
  printf '#!/bin/zsh\necho "fake reply to: ${@[-1]}"\n' > $W/bin/kiro-cli; chmod +x $W/bin/kiro-cli
  echo $W/S > $W/ev/sandbox-path.txt; print -r -- "Hello." > $W/prompt.txt
  local bad=0
  P2_EVDIR=$W/ev P2_KIRO_CLI=$W/bin/kiro-cli P2_BOUNDARY=1 zsh $H0/turn.sh selfcheck-R 1 $W/prompt.txt > $W/t1.out 2>&1
  grep -q 'after_turn sequential: checked' $W/ev/turn-01.wrapper.txt || { echo "no sequence line"; bad=1; }
  [[ -f $W/ev/after-turn-01.done ]] || { echo "no after_turn record"; bad=1; }
  grep -q -- 'env -u KIRO_HOME' $W/ev/turn-01.cmd.txt && grep -q -- '--effort high' $W/ev/turn-01.cmd.txt || { echo "argv lacks env -u KIRO_HOME or --effort high"; bad=1; }
  P2_EVDIR=$W/ev P2_KIRO_CLI=$W/bin/kiro-cli zsh $H0/turn.sh selfcheck-R 1 $W/prompt.txt > /dev/null 2>&1 && { echo "turn 1 twice must be refused"; bad=1; }
  P2_EVDIR=$W/ev P2_KIRO_CLI=$W/bin/kiro-cli zsh $H0/turn.sh selfcheck-R 3 $W/prompt.txt > /dev/null 2>&1 && { echo "turn 3 without turn 2 must be refused"; bad=1; }
  zsh $H0/run_turn.sh $W/S selfcheck-R 2 $W/prompt.txt > /dev/null 2>&1; [[ $? == 93 ]] || { echo "run_turn.sh alone must be refused (93)"; bad=1; }
  P2_TURN_WRAPPER=1 P2_KIRO_CLI=$W/bin/kiro-cli zsh $H0/run_turn.sh $W/S R9 2 $W/prompt.txt > /dev/null 2>&1; [[ $? == 2 ]] || { echo "a stream label must not take the fake chat"; bad=1; }
  grep -q 'sleep 1 ended' $W/ev/turn-times.txt || { echo "the boundary"; bad=1; }
  # turn.sh refuses while a skill move of another label has no restore (a constructed home and record)
  local HM=$P/selfcheck-home; mkdir -p $HM/.kiro/skills; rm -rf $HM/.kiro/skills/hirearchy; mkdir -p $HM/.kiro/skills/hirearchy
  cp -p $REPO_R/skills/hirearchy/SKILL.md $HM/.kiro/skills/hirearchy/SKILL.md; rm -f $P/selfcheck-skill-moves.txt
  HOME=$HM zsh $H0/skill_move.sh aside selfcheck-C9 > /dev/null
  HOME=$HM P2_EVDIR=$W/ev P2_KIRO_CLI=$W/bin/kiro-cli P2_BOUNDARY=1 zsh $H0/turn.sh selfcheck-R 2 $W/prompt.txt > /dev/null 2>&1; [[ $? == 92 ]] || { echo "turn.sh must refuse another label's unrestored move (92)"; bad=1; }
  HOME=$HM zsh $H0/skill_move.sh restore selfcheck-C9 > /dev/null
  echo "wrapper cases: $( (( bad )) && echo FAILED || echo '9 of 9 ok')"; return $bad
}
part "one wrapper per turn (fake chat)" wrapper.out wrap_case
# 5b. the probe's own product calls (H-A1's lesson): its four throwaway orgs and both catalogs, no chat and no skill move (--setup-only)
probe_setup_case() {
  local PD=$OUT/probe-setup; rm -rf $PD; mkdir -p $PD
  P2_PROBE_DIR=$PD zsh $H0/probe.sh --setup-only || return 1
  local bad=0
  for s in probe-C1 probe-R1 probe-R2 probe-C2; do grep -q 'define-service exit 0' $PD/$s/org-setup.txt && grep -q 'hire exit 0' $PD/$s/org-setup.txt || { echo "$s: org setup failed"; bad=1; }; done
  python3 -c "import json,sys; r=json.load(open('$PD/catalog-R.json'))['tools']; c=json.load(open('$PD/catalog-C.json'))['tools']; sys.exit(0 if 'retro' in r and 'retro' not in c else 1)" || { echo "positive control"; bad=1; }
  echo "probe setup: $( (( bad )) && echo FAILED || echo 'four orgs and two catalogs ok; retro in R only')"; return $bad
}
part "the probe's product calls (--setup-only)" probe_setup.out probe_setup_case
# 5c. C4 (F41 of review 3): a trapped INT or TERM must stop the script. A stub zsh script per driver carries that driver's own trap lines
# (read from probe.sh and setup_stream.sh, the `trap -` resets left out), is sent TERM while it runs, and must run its cleanup and exit
# with the driver's code (probe.sh 130, setup_stream.sh 4) without running its next command
trap_case() {
  local W=$P/selfcheck-traps; rm -rf $W; mkdir -p $W; local bad=0 f want tl st pid rc i
  for f want in probe.sh 130 setup_stream.sh 4; do
    tl=$(grep -E "^[[:space:]]*trap '" $H0/$f)
    [[ -n "$tl" ]] || { echo "$f: no trap line"; bad=1; continue; }
    st=$W/${f%.sh}-stub.zsh
    { echo '#!/bin/zsh'; echo "cleanup() { echo cleanup-ran >> $W/${f%.sh}.log; }"; print -r -- "$tl"; echo ": > $W/${f%.sh}.ready"; echo 'sleep 2'
      echo "echo next-command-ran >> $W/${f%.sh}.log"; echo 'exit 0'; } > $st
    zsh $st & pid=$!
    for i in {1..50}; do [[ -e $W/${f%.sh}.ready ]] && break; sleep 0.1; done
    kill -TERM $pid; wait $pid; rc=$?
    local log=$(cat $W/${f%.sh}.log 2>/dev/null | tr '\n' ' ')
    echo "$f: trap lines [$(print -r -- "$tl" | sed 's/^ *//' | tr '\n' ';')] TERM -> exit $rc, log [$log]"
    [[ $rc == $want && "$log" == *cleanup-ran* && "$log" != *next-command-ran* ]] || { echo "$f: expected exit $want, the cleanup and no next command"; bad=1; }
  done
  echo "trap cases: $( (( bad )) && echo FAILED || echo '2 of 2 ok')"; return $bad
}
part "signal traps stop the drivers (C4)" traps.out trap_case
# 5d. protocol amendment 1's harness items (A) turn.sh's sequence check, (B) the finish's cost path on an effort-stopped session, (C) the
# injection wrapper's window.txt; constructed under $P/selfcheck-amend1/, no product call but (B)'s stated client_questions import
rm -rf $P/selfcheck-amend1
part "amendment 1: sequence check, effort-stop cost, window.txt" amend1.out python3 -B amend1_cases.py --scratch $P/selfcheck-amend1 --product-src $REPO_R/src
# 6. the dry run in each arm
part "dry run, arm R (throwaway org, every CLI call and reader)" dryrun-R.out zsh $H0/dryrun.sh R $OUT/dryrun-R
part "dry run, arm C (throwaway org, every CLI call and reader)" dryrun-C.out zsh $H0/dryrun.sh C $OUT/dryrun-C
echo "SELFCHECK: $k of $n parts passed" | tee -a $SUM
(( k == n ))
