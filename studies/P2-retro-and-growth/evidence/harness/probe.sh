#!/bin/zsh
# P2 preflight probe (protocol 8.3; F-G0-7 section 4 item 2; the skill proof in both arms). Usage: probe.sh [--dry-run] [--setup-only]
# Order C-1, R-1, R-2, C-2; each a 2-turn session on its own throwaway org under /tmp/hirearchy-p2/, with that arm's setup: the profile from
# profile-template.json (<PRODUCT> = the arm's product), the workspace copy of the arm's SKILL.md, and in arm C the global skill moved aside
# (skill_move.sh, restored by a trap after the run, whatever happens). The org (the arm's CLI, the same commands in both arms): init, hire
# root lead, define-service lead probe-memo with --deliverable and --path (H-A1). Before the sessions, mcp_catalog.py lists each product's
# tool catalog into probe/catalog-<arm>.json. Each turn runs through run_turn.sh (KIRO_HOME unset, --effort high, the 20-s boundary); the
# session is copied after turn 2. Then probe_compare.py writes probe/compare.txt and prints `PROBE: PASS` or `PROBE: STOP: ...`.
# --setup-only builds the four orgs and catalogs and stops before any chat (the self-check's dry run uses it with HOME untouched: it moves
# nothing in --setup-only). Each probe profile is deleted after its run, with a record.
H0=${0:A:h}
source $H0/arm.sh probe-R1 || exit 2
DRY=0; SETUP_ONLY=0; [[ "$1" == --dry-run ]] && DRY=1; [[ "$1" == --setup-only ]] && SETUP_ONLY=1
PR=$EV/probe; [[ -n "$P2_PROBE_DIR" && $SETUP_ONLY == 1 ]] && PR=$P2_PROBE_DIR
# F32 of review 2: turn 1 opens with words that need the skill (the same in both arms), so the session loads it and the skill proof has a
# disclose_context result to read
T1="Please load your hirearchy skill first, then run the hirearchy whoami tool and show me its reply."
T2="Now run the hirearchy services tool and show me its reply."
[[ -n "${ORG_AGENT+x}" || -n "${ORG_REQUIRE_AGENT+x}" ]] && { echo "REFUSED: ORG_AGENT or ORG_REQUIRE_AGENT is set" >&2; exit 3; }
[[ -n "${KIRO_HOME+x}" ]] && { echo "REFUSED: KIRO_HOME is set in this shell (protocol 1)" >&2; exit 3; }
zsh $H0/skill_move.sh status > /dev/null || { echo "REFUSED: a skill move has no restore" >&2; exit 3; }
mkdir -p $PR
for SES in C1 R1 R2 C2; do
  LBL=probe-$SES; source $H0/arm.sh $LBL
  EPOCH=$(date +%s); S=$P/$LBL-$EPOCH; D=$PR/$LBL
  if (( DRY )); then echo "DRY-RUN $LBL: arm $ARM product $REPO_A S=$S profile $PNAME; arm C moves the global skill aside"; continue; fi
  [[ -e $HOME/.kiro/agents/$PNAME.json || -e $D/sandbox-path.txt ]] && { echo "REFUSED: $PNAME or $D exists" >&2; exit 4; }
  mkdir -p $D $S/.kiro/skills/hirearchy $S/.kiro/settings $S/deliverables
  cp -p $REPO_A/skills/hirearchy/SKILL.md $S/.kiro/skills/hirearchy/SKILL.md
  cp -p $H0/workspace-cli.json $S/.kiro/settings/cli.json
  echo $S > $D/sandbox-path.txt; echo $ARM > $D/arm.txt
  {
    "${HIR[@]}" init $S/org --mission "Probe."; echo "init exit $?"
    "${HIR[@]}" --root $S/org hire root lead --role "Memo lead" --charter "Writes one short memo per request."; echo "hire exit $?"
    "${HIR[@]}" --root $S/org define-service lead probe-memo --description "One short memo from one notes file" \
      --input 'notes_file*:the notes file' --acceptance 'At most 400 words.' --deliverable 'A memo of at most 400 words' --path $S/deliverables --budget 12
    echo "define-service exit $?"
  } > $D/org-setup.txt 2>&1
  [[ -f $PR/catalog-$ARM.json ]] || env -u KIRO_HOME uv --directory $REPO_A run python $H0/mcp_catalog.py --repo $REPO_A --org $S/org --out $PR/catalog-$ARM.json > $D/catalog-output.txt 2>&1
  (( SETUP_ONLY )) && { echo "setup-only $LBL: $(grep exit $D/org-setup.txt | tr '\n' ' ')"; continue; }
  MOVED=0; CREATED=0
  # F34 of review 2: on any exit, the profile this run created is deleted with a record, and the skill is restored
  cleanup() {
    if (( CREATED )) && [[ -f $HOME/.kiro/agents/$PNAME.json ]]; then
      rm -f $HOME/.kiro/agents/$PNAME.json && echo "profile deleted $(date -u +%FT%TZ) (by the exit trap: the run stopped early): $PNAME" >> $PR/profiles-deletions.txt
    fi
    CREATED=0
    (( MOVED )) && zsh $H0/skill_move.sh restore $LBL >> $D/skill-restore.txt 2>&1; MOVED=0; }
  # C4 (F41 of review 3): a trapped INT or TERM runs the cleanup and then stops the probe (zsh resumes a script after a trap without exit)
  trap 'cleanup' EXIT
  trap 'cleanup; exit 130' INT TERM
  if [[ $ARM == C ]]; then zsh $H0/skill_move.sh aside $LBL > $D/skill-aside.txt 2>&1 || { cat $D/skill-aside.txt; exit 4; }; MOVED=1; fi
  CREATED=1; sed -e "s/<LABEL>/$LBL/g" -e "s/<epoch>/$EPOCH/g" -e "s#<PRODUCT>#$REPO_A#g" $H0/profile-template.json > $HOME/.kiro/agents/$PNAME.json
  cp -p $HOME/.kiro/agents/$PNAME.json $D/
  echo "profile created $(date -u +%FT%TZ): $PNAME md5 $(md5 -q $HOME/.kiro/agents/$PNAME.json)" >> $PR/profiles-creations.txt
  print -r -- "$T1" > $D/t1.txt; print -r -- "$T2" > $D/t2.txt
  P2_TURN_WRAPPER=1 zsh $H0/run_turn.sh $S $LBL 1 $D/t1.txt
  P2_TURN_WRAPPER=1 zsh $H0/run_turn.sh $S $LBL 2 $D/t2.txt
  python3 - "$S" "$D" "$HOME/.kiro" "$PNAME" <<'PY'
import json,glob,os,sys,shutil
S,D,KH,PROFILE=sys.argv[1:5]; real=os.path.realpath(S); best=None; bt=0
for p in glob.glob(os.path.join(KH,'sessions/*/sess_*/session.json')):
    try: j=json.load(open(p))
    except Exception: continue
    if j.get('agentMode')==PROFILE and (j.get('workspacePaths') or [''])[0] in (real,S):
        m=os.path.getmtime(p)
        if m>=bt: best,bt=p,m
if best:
    shutil.copy2(best,D+'/session.json'); shutil.copy2(os.path.dirname(best)+'/messages.jsonl',D+'/session-messages.jsonl'); print('session copied')
else: print('NO SESSION FOUND')
PY
  python3 -B $H0/skill_proof.py $D/session-messages.jsonl --arm $ARM --out $D/skill-proof.json | tee $D/skill-proof.txt
  rm -f $HOME/.kiro/agents/$PNAME.json && echo "profile deleted $(date -u +%FT%TZ): $PNAME" >> $PR/profiles-deletions.txt && CREATED=0
  cleanup; trap - EXIT INT TERM
  [[ $ARM == C ]] && echo "after $LBL: $(zsh $H0/skill_move.sh status | head -1)" | tee -a $D/skill-restore.txt
done
(( DRY || SETUP_ONLY )) && exit 0
python3 -B $H0/probe_compare.py $PR | tee $PR/compare.txt | tail -1
