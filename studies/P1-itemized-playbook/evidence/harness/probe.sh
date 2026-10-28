#!/bin/zsh
# P1 preflight probe (design 18.3 item 2; F-G0-7 section 4 item 2), run by the preflight step before turn 1 of F1, never by this step.
# Usage: probe.sh [--dry-run]
# Four 2-turn sessions, in the order F-1, I-1, I-2, F-2 (both arms, 2 repetitions each), each on a throwaway sandbox P=/tmp/hirearchy-p1-probe-
# <arm><rep>-<epoch> with that arm's setup and the streams' workspace bytes (the repo SKILL.md copy, harness/workspace-cli.json):
#   - the org P/org made as root through the product's CLI: init; hire root lead; define-service lead probe-memo (contract v1); arm F only, the
#     lock exactly as the stream hook applies it: `ORG_ROOT=P/org uv --directory /Volumes/workspace/hirearchy run hirearchy define-service lead
#     probe-memo --locked` (contract v2), with the hook's three checks;
#   - the profile hirearchy-study-p1-probe-<arm><rep>-assistant from harness/profile-template.json (label probe-<arm><rep>), in ~/.kiro/agents,
#     created and deleted with a record in probe/profiles-creations.txt and probe/profiles-deletions.txt;
#   - turn 1: "Please run the hirearchy whoami tool and show me its reply." turn 2 (--resume): "Now run the hirearchy services tool and show me
#     its reply." Each turn: `env -u KIRO_HOME kiro-cli chat --v3 --no-interactive --trust-all-tools [--resume] --effort high --agent <profile>
#     "<line>"; sleep 20` (run_turn.sh's form), cwd P;
#   - the session store copied (the owner's ~/.kiro/sessions, read only) into probe/<arm><rep>/.
# Then probe_compare.py probe/ writes probe/compare.txt and ends `PROBE: PASS` or `PROBE: STOP: <the difference>`. Nothing else is written outside
# P and probe/; the sandboxes stay for the teardown (prefix guard /tmp/hirearchy-p1-probe-).
REPO=/Volumes/workspace/hirearchy
EV=$REPO/studies/P1-itemized-playbook/evidence
H=$EV/harness
PR=$EV/probe
HIR=(uv --directory $REPO run hirearchy)
DRY=0; [[ "$1" == "--dry-run" ]] && DRY=1
T1="Please run the hirearchy whoami tool and show me its reply."
T2="Now run the hirearchy services tool and show me its reply."
[[ -n "${ORG_AGENT+x}" || -n "${ORG_REQUIRE_AGENT+x}" ]] && { echo "REFUSED: ORG_AGENT or ORG_REQUIRE_AGENT is set; the probe acts as root only" >&2; exit 3; }
[[ -n "${KIRO_HOME+x}" ]] && { echo "REFUSED: KIRO_HOME is set in this shell; it is unset in both arms (protocol 1)" >&2; exit 3; }
for SES in F1 I1 I2 F2; do
  ARM=${SES[1,1]}; LBL=probe-$SES; PNAME=hirearchy-study-p1-$LBL-assistant
  EPOCH=$(date +%s); P=/tmp/hirearchy-p1-probe-$SES-$EPOCH; D=$PR/$SES
  if (( DRY )); then
    echo "DRY-RUN $SES: P=$P; init, hire, define-service$( [[ $ARM == F ]] && echo ', --locked (hook checks)'); profile $PNAME; 2 turns; session copy -> $D"
    continue
  fi
  [[ -e $HOME/.kiro/agents/$PNAME.json || -e $D ]] && { echo "REFUSED: $PNAME or $D exists already" >&2; exit 4; }
  mkdir -p $D $P/.kiro/skills/hirearchy $P/.kiro/settings
  cp -p $REPO/skills/hirearchy/SKILL.md $P/.kiro/skills/hirearchy/SKILL.md
  cp -p $H/workspace-cli.json $P/.kiro/settings/cli.json
  echo $P > $D/sandbox-path.txt
  {
    ${HIR[@]} init $P/org; echo "init exit $?"
    ${HIR[@]} --root $P/org hire root lead --role "Memo lead" --charter "Writes one short memo per request."; echo "hire exit $?"
    ${HIR[@]} --root $P/org define-service lead probe-memo --description "One short memo from one notes file" \
      --input 'notes_file*:the notes file' --acceptance 'At most 400 words.' --deliverable 'A memo of at most 400 words in the reply' --budget 12; echo "define-service exit $?"
  } > $D/org-setup.txt 2>&1
  if [[ $ARM == F ]]; then
    SF=$P/org/lead/services/probe-memo/SERVICE.md
    VBEFORE=$(grep -E '^version:' $SF | head -1 | grep -oE '[0-9]+'); VWANT=$(( ${VBEFORE:-0} + 1 ))
    ORG_ROOT=$P/org uv --directory $REPO run hirearchy define-service lead probe-memo --locked > $D/lock-reply.txt 2> $D/lock-stderr.txt; rc=$?
    NOTE=$(grep -rlF 'locked: false -> true (you may no longer revise the playbook)' $P/org/lead/inbox $P/org/lead/read 2>/dev/null | head -1)
    {
      echo "exit $rc"; cat $D/lock-reply.txt
      echo "check 1 (reply): $([[ $rc -eq 0 ]] && grep -qi locked $D/lock-reply.txt && echo yes || echo no)"
      echo "check 2 (locked: true, version = before + 1 = $VWANT): $(grep -qE '^locked: true$' $SF && grep -qE "^version: $VWANT\$" $SF && echo yes || echo no)"
      echo "check 3 (the owner's quiet note): $([[ -n "$NOTE" ]] && echo yes || echo no) ${NOTE:-}"
    } > $D/lock-checks.txt
  fi
  sed -e "s/<LABEL>/$LBL/g" -e "s#/tmp/hirearchy-p1-$LBL-<epoch>/org#$P/org#g" $H/profile-template.json > $HOME/.kiro/agents/$PNAME.json
  cp -p $HOME/.kiro/agents/$PNAME.json $D/$PNAME.json
  echo "profile created $(date -u +%FT%TZ): $HOME/.kiro/agents/$PNAME.json md5 $(md5 -q $HOME/.kiro/agents/$PNAME.json)" >> $PR/profiles-creations.txt
  cd $P || exit 90
  n=0
  for LINE in "$T1" "$T2"; do
    n=$((n+1)); NN=$(printf '%02d' $n); RESUME=""; [[ $n -ge 2 ]] && RESUME="--resume"
    CMD=(env -u KIRO_HOME kiro-cli chat --v3 --no-interactive --trust-all-tools $RESUME --effort high --agent $PNAME "$LINE")
    print -r -- "${(q-)CMD[@]}" > $D/turn-$NN.cmd.txt
    startu=$(date -u +%FT%TZ)
    "${CMD[@]}" > $D/turn-$NN.raw.txt 2> $D/turn-$NN.stderr.txt; rc=$?; endu=$(date -u +%FT%TZ); sleep 20
    echo "turn $n: utc $startu - $endu exit $rc" >> $D/turn-times.txt
  done
  cd $EV
  python3 - "$P" "$D" "$PNAME" <<'PY'
import json,glob,os,sys,shutil
P,D,PROFILE=sys.argv[1:4]; real=os.path.realpath(P); best=None; bt=0
for p in glob.glob(os.path.expanduser('~/.kiro/sessions/*/sess_*/session.json')):
    try: j=json.load(open(p))
    except Exception: continue
    if j.get('agentMode')==PROFILE and (j.get('workspacePaths') or [''])[0] in (real,P):
        m=os.path.getmtime(p)
        if m>=bt: best,bt=p,m
if not best: print('NO SESSION FOUND'); sys.exit(1)
shutil.copy2(best,D+'/session.json'); shutil.copy2(os.path.dirname(best)+'/messages.jsonl',D+'/session-messages.jsonl'); print('session copied from',best)
PY
  PF=$HOME/.kiro/agents/$PNAME.json
  if cmp -s $PF $D/$PNAME.json; then rm -f $PF; echo "profile deleted $(date -u +%FT%TZ): $PF md5 $(md5 -q $D/$PNAME.json)" >> $PR/profiles-deletions.txt
  else echo "profile NOT deleted (it changed): $PF" >> $PR/profiles-deletions.txt; fi
done
(( DRY )) && exit 0
python3 -B $H/probe_compare.py $PR | tee $PR/compare.txt | tail -3
grep -q '^PROBE: PASS' $PR/compare.txt
