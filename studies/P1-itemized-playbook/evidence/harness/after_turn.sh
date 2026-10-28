#!/bin/zsh
# P1 facilitator helper, frozen with the harness: usage after_turn.sh <label> <turn n>      (label F1..F3, I1..I3, replacements F1r ...)
# G0's after_turn.sh (E7's per-stream helper generalized), M1 treatment only: the assistant's session store is searched in the owner's kiro home
# (~/.kiro) in both arms; no dedicated kiro home exists. Steps, in order:
#   1. org state; the assistant session copy; the scheduler record (D-SURVIVE); the signal record (D-SIGNAL); model_check org and assistant;
#      the throttle scan; the ambient comparison (G0's, unchanged);
#   2. the empty-argument call counter (design 18.3 item 3; f-g0-7 section 1): the session-store count (empty_calls.py on the copied session)
#      and `grep -c 'is not available' turn-NN.stderr.txt` beside it, into empty-calls.txt; the org-run cap (protocol 4.2: 130 org runs, every
#      run of the stream, the injection window included; a `CAP:` line ends the stream at the end of this turn, which stays valid); the
#      memo requests root has sent (S/org/sent/, protocol 4.2's M3-VERDICT trigger), into requests-by-turn.txt;
#   3. ARM F ONLY, the lock hook (design 18.2; protocol 1.1), once: after the turn in which the study service's SERVICE.md first exists (apply_org
#      defined it), as root: `ORG_ROOT=<S>/org uv --directory /Volumes/workspace/hirearchy run hirearchy define-service <lead> <service> --locked`;
#      then its three checks (the reply, SERVICE.md's frontmatter `locked: true` at the version before the hook + 1, the owner's quiet note
#      `locked: false -> true (you may no longer revise the playbook)`) and H-LOCK (an owner's playbook version written before the lock); all of
#      it into <label>/lock/; after the lock, every turn: lock/lock-held.txt lists `locked:` of every contract version after the lock version, and
#      one that is not `true` prints `STOP:` (H-LOCK: the arm was not held, protocol 8);
#   4. quality_snapshot.sh <label> turn-NN and services_snapshot.sh <label> turn-NN, LAST (each reads the org through the product's CLI only when
#      ORG.md exists; each records its cli.command event file, a known harness actor for H6).
# Lines starting `STOP:` mean the stream step stops at the end of this turn with a `warning` (protocol 8).
LABEL="$1"; T="$2"
REPO=/Volumes/workspace/hirearchy
ST=$REPO/studies/P1-itemized-playbook
EV=$ST/evidence
[[ "$LABEL" =~ '^[FI][1-3](r[0-9]*)?$' && "$T" =~ '^[1-9][0-9]*$' && $# -eq 2 ]] || { echo "usage: after_turn.sh <label F1..I3> <turn n>" >&2; exit 2; }
D=$EV/$LABEL; S=$(cat $D/sandbox-path.txt); SN=${S:t}
ARM=${LABEL[1,1]}
KH=$HOME/.kiro
PROFILE=hirearchy-study-p1-$LABEL-assistant
NN=$(printf '%02d' "$T")
python3 $EV/harness/org_state.py $S "after turn $T" >> $D/run-counts-by-turn.txt 2>&1
python3 - "$S" "$D" "$KH" "$PROFILE" <<'PY'
import json,glob,os,sys,shutil
S,D,KH,PROFILE=sys.argv[1:5]; real=os.path.realpath(S)
best=None; bt=0
for p in glob.glob(os.path.join(KH,'sessions/*/sess_*/session.json')):
    try: j=json.load(open(p))
    except Exception: continue
    if j.get('agentMode')==PROFILE and (j.get('workspacePaths') or [''])[0] in (real,S):
        m=os.path.getmtime(p)
        if m>=bt: best,bt=p,m
if not best: print('NO SESSION FOUND'); sys.exit(1)
shutil.copy2(best,D+'/assistant-session.json'); shutil.copy2(os.path.dirname(best)+'/messages.jsonl',D+'/assistant-session-messages.jsonl')
print('session copied from',best)
PY
{
  echo "--- scheduler record after turn $T at $(date -u +%FT%TZ)"
  if [[ -f $S/org/.runtime/scheduler.pid ]]; then
    PID=$(cat $S/org/.runtime/scheduler.pid | tr -dc '0-9')
    echo "scheduler.pid: $(cat $S/org/.runtime/scheduler.pid | tr '\n' ' ')"
    echo "ps -o pid=,ppid=,stat=,etime=,command= -p $PID:"
    ps -o pid=,ppid=,stat=,etime=,command= -p "$PID" 2>&1 || echo "(not running)"
  else
    echo "scheduler.pid: (no file)"
  fi
  echo "scheduler.exit: $( [[ -f $S/org/.runtime/scheduler.exit ]] && cat $S/org/.runtime/scheduler.exit | head -3 | tr '\n' ' ' || echo '(none)')"
  echo "processes referencing the sandbox name:"; ps -axo pid,ppid,stat,etime,command | grep -F "$SN" | grep -v grep || echo "(none)"
} >> $D/run-counts-by-turn.txt 2>&1
{
  echo "--- signal record after turn $T at $(date -u +%FT%TZ): every scheduler.signal line now in S/org/.runtime/events/ (cumulative)"
  if [[ -d $S/org/.runtime/events ]]; then
    EVF=("${(@f)$(find $S/org/.runtime/events -name '*.jsonl' 2>/dev/null | sort)}")
    echo "(scheduler.signal lines):"; [[ -n "${EVF[1]}" ]] && { grep -H '"scheduler.signal"' "${EVF[@]}" | sed "s#$S/org/.runtime/events/##" | cut -c1-600; true; }
    echo "(scheduler.exit lines):"; [[ -n "${EVF[1]}" ]] && { grep -H '"scheduler.exit"' "${EVF[@]}" | sed "s#$S/org/.runtime/events/##" | cut -c1-600; true; }
    echo "(run.orphan lines):"; [[ -n "${EVF[1]}" ]] && { grep -H '"run.orphan"' "${EVF[@]}" | sed "s#$S/org/.runtime/events/##" | cut -c1-600; true; }
  else echo "(no events dir)"; fi
  echo "(turn $T end per turn-times.txt:)"; grep -E "^turn $T:" $D/turn-times.txt
} >> $D/run-counts-by-turn.txt 2>&1
zsh $EV/harness/model_check.sh org $LABEL $S | tail -3
zsh $EV/harness/model_check.sh assistant $LABEL $S | tail -8
echo "--- throttle/exit-75 scan after turn $T" >> $D/run-counts-by-turn.txt
{ [[ -d $S/org ]] && find $S/org -path '*/runs/*.log' -not -path '*/.git/*' -exec grep -lE '^# kiro: throttled by the model service|^# exit 75 ' {} + ; } >> $D/run-counts-by-turn.txt 2>/dev/null; echo "(end of scan)" >> $D/run-counts-by-turn.txt
PREV=$D/ambient/setup.txt; [[ "$T" -ge 2 ]] && PREV=$D/ambient/turn-$(printf '%02d' $((T-1)))-after.txt
echo "--- ambient comparison turn $T (md5 lines)"
for f in $PREV $D/ambient/turn-$NN-before.txt $D/ambient/turn-$NN-after.txt; do echo "## $(basename $f)"; grep -E 'listing md5|memories\.db' $f; done
tail -45 $D/run-counts-by-turn.txt
# 2. the empty-argument call counter (18.3 item 3; f-g0-7 section 1): the session-store count decides, the stderr grep is reported beside it
EC=$(grep -c 'is not available' $D/turn-$NN.stderr.txt 2>/dev/null); EC=${EC:-0}
SC=$(python3 -B $EV/harness/empty_calls.py $D/assistant-session-messages.jsonl)
echo "turn $NN: $SC so far (the session store); 'is not available' in turn-$NN.stderr.txt: $EC" >> $D/empty-calls.txt
echo "empty-argument calls after turn $T: $SC; stderr grep this turn: $EC"
# the org-run cap (protocol 4.2): every org run of the stream, the injection window included
NRUNS=$( { [[ -d $S/org ]] && find $S/org -path '*/runs/*.log' -not -path '*/.git/*' 2>/dev/null; } | wc -l | tr -d ' ')
echo "org runs after turn $T: $NRUNS (cap 130, the injection window included)"
(( NRUNS >= 130 )) && echo "CAP: $NRUNS org runs after turn $T (cap 130, protocol 4.2): the stream ends at the end of this turn; it stays valid"
# root's memo requests so far (M3-VERDICT's trigger: memo 4's request, 2026-10-26.md, exists in S/org/sent/; protocol 4.2)
REQS=$(python3 - "$S/org/sent" <<'PY'
import re,sys,glob,os
out=[]
for f in sorted(glob.glob(os.path.join(sys.argv[1],'*.md'))):
    t=open(f,errors='replace').read(); m=re.match(r'^---\n(.*?)\n---\n?(.*)$',t,re.S)
    if not m: continue
    fm,body=m.groups()
    if re.search(r'^type:\s*task\s*$',fm,re.M) and not re.search(r'^revises:\s*\S',fm,re.M):
        n=re.search(r'notes_file:\s*(\d{4}-\d{2}-\d{2})',body)
        if n: out.append(n.group(1))
print(' '.join(dict.fromkeys(out)) or '(none)')
PY
)
echo "turn $NN: root's new requests by notes file: $REQS; memo 4's request (2026-10-26.md) sent: $([[ $REQS == *2026-10-26* ]] && echo yes || echo no)" >> $D/requests-by-turn.txt
tail -1 $D/requests-by-turn.txt
# 3. arm F: the lock hook (once)
if [[ "$ARM" == F ]]; then
  L=$D/lock
  if [[ ! -f $L/hook.txt ]]; then
    SVC=("${(@f)$(find $S/org -path "$S/org/.git" -prune -o -path '*/services/*/SERVICE.md' -print 2>/dev/null | sort)}")
    if [[ -n "${SVC[1]}" ]]; then
      mkdir -p $L
      if (( ${#SVC} != 1 )); then
        echo "STOP: lock hook: ${#SVC} services exist after turn $T (${SVC[*]}): the study has one service; the hook does not guess" | tee $L/hook.txt
      elif [[ -n "${ORG_AGENT+x}" || -n "${ORG_REQUIRE_AGENT+x}" ]]; then
        echo "STOP: lock hook: ORG_AGENT or ORG_REQUIRE_AGENT is set in the facilitator's environment; the hook runs as root only" | tee $L/hook.txt
      else
        SF=${SVC[1]}; SDIR=${SF:h}; SERVICE=${SDIR:t}; LEAD=${${SDIR#$S/org/}%/services/*}
        # H-LOCK first: an owner's playbook version (by the owner) written before the lock
        python3 - "$SDIR" "$LEAD" > $L/h-lock-before.txt <<'PY'
import os,re,sys,glob
sdir,lead=sys.argv[1:3]
files=sorted(glob.glob(os.path.join(sdir,'history','PLAYBOOK.v*.md')))+[os.path.join(sdir,'PLAYBOOK.md')]
owner_versions=[]
for f in files:
    if not os.path.exists(f): continue
    t=open(f,errors='replace').read()
    m=re.match(r'^---\n(.*?)\n---',t,re.S)
    fm=m.group(1) if m else ''
    by=re.search(r'^by:\s*(.+)$',fm,re.M); op=re.search(r'^op:\s*(.+)$',fm,re.M); v=re.search(r'^version:\s*(\d+)',fm,re.M)
    by=(by.group(1).strip().strip("'\"") if by else ''); op=(op.group(1).strip() if op else '')
    print(f"{os.path.basename(f)} version {v.group(1) if v else '?'} by {by!r} op {op!r}")
    if by==lead: owner_versions.append(os.path.basename(f))
print('H-LOCK: INVALID: the owner wrote '+', '.join(owner_versions)+' before the lock' if owner_versions else 'H-LOCK: ok (no version by the owner before the lock)')
PY
        {
          echo "lock hook after turn $T at $(date -u +%FT%TZ): lead=$LEAD service=$SERVICE SERVICE.md=$SF"
          echo "SERVICE.md before: $(md5 -q $SF), $(grep -E '^(version|locked):' $SF | tr '\n' ' ')"
          echo "command: ORG_ROOT=$S/org uv --directory $REPO run hirearchy define-service $LEAD $SERVICE --locked"
        } > $L/hook.txt
        VBEFORE=$(grep -E '^version:' $SF | head -1 | grep -oE '[0-9]+'); VWANT=$(( ${VBEFORE:-0} + 1 ))
        list_cli() { [[ -d "$S/org/.runtime/events" ]] && find "$S/org/.runtime/events" -type f -name 'cli-*.jsonl' 2>/dev/null | sort; true; }
        before="$(list_cli)"
        startu=$(date -u +%FT%TZ)
        ORG_ROOT=$S/org uv --directory $REPO run hirearchy define-service $LEAD $SERVICE --locked > $L/reply.txt 2> $L/stderr.txt; rc=$?
        endu=$(date -u +%FT%TZ)
        after="$(list_cli)"
        new=("${(@f)$(comm -13 <(print -r -- "$before") <(print -r -- "$after"))}")
        {
          echo "start $startu end $endu exit $rc"
          echo "reply (verbatim, reply.txt):"; cat $L/reply.txt
          echo "new cli-*.jsonl during the call (known harness actor, H6): ${new[*]:-(none)}"
          C1=no; [[ $rc -eq 0 ]] && grep -qi 'locked' $L/reply.txt && C1=yes
          C2=no; grep -qE '^locked: true$' $SF && grep -qE "^version: $VWANT\$" $SF && C2=yes
          NOTE=$(grep -rlF 'locked: false -> true (you may no longer revise the playbook)' $S/org/$LEAD/inbox $S/org/$LEAD/read 2>/dev/null | head -1)
          C3=no; [[ -n "$NOTE" ]] && grep -qE '^from: root$' $NOTE && grep -qE '^wake: false$' $NOTE && C3=yes
          echo "check 1, the reply (exit 0 and it names the lock): $C1"
          echo "check 2, SERVICE.md frontmatter locked: true at version $VWANT (the version before the hook, $VBEFORE, + 1): $C2 ($(grep -E '^(version|locked):' $SF | tr '\n' ' '))"
          echo "check 3, the owner's quiet note from root (wake: false) 'locked: false -> true (you may no longer revise the playbook)': $C3 (${NOTE:-none})"
          cat $L/h-lock-before.txt
          if [[ $C1 == yes && $C2 == yes && $C3 == yes ]] && grep -q '^H-LOCK: ok' $L/h-lock-before.txt; then
            echo "LOCK OK after turn $T"
          else
            echo "STOP: LOCK FAILED after turn $T (check 1 $C1, check 2 $C2, check 3 $C3; $(tail -1 $L/h-lock-before.txt)): arm F is invalid (H-LOCK, protocol 8)"
          fi
        } >> $L/hook.txt
        [[ -n "$NOTE" ]] && cp -p $NOTE $L/owner-note.md
        cp -p $SF $L/SERVICE.after-lock.md
        echo "$VWANT $SF" > $L/lock-version.txt
        tail -6 $L/hook.txt
      fi
    else
      echo "lock hook: no SERVICE.md yet after turn $T (arm F; the hook runs after the turn in which apply_org defines it)"
    fi
  else
    echo "lock hook: done ($(grep -E '^(LOCK OK|STOP)' $L/hook.txt | head -1))"
  fi
  # the lock held (protocol 1.1, 8): every contract version after the lock keeps `locked: true`
  if [[ -f $L/lock-version.txt ]]; then
    read LV SF < $L/lock-version.txt
    python3 - "$SF" "$LV" "$T" >> $L/lock-held.txt <<'PY'
import os,re,sys,glob
sf,lv,t=sys.argv[1],int(sys.argv[2]),sys.argv[3]
files=sorted(glob.glob(os.path.join(os.path.dirname(sf),'history','SERVICE.v*.md')))+[sf]
seen,bad={},[]
for f in files:
    if not os.path.exists(f): continue
    m=re.match(r'^---\n(.*?)\n---',open(f,errors='replace').read(),re.S); fm=m.group(1) if m else ''
    v=re.search(r'^version:\s*(\d+)',fm,re.M); lk=re.search(r'^locked:\s*(\S+)',fm,re.M)
    if not v or int(v.group(1))<lv: continue
    seen[int(v.group(1))]=lk.group(1) if lk else '(absent)'
for v,lk in sorted(seen.items()):
    if lk!='true': bad.append(f'v{v} locked: {lk}')
print(f"after turn {t}: contract versions from the lock (v{lv}) on: "+', '.join(f'v{v} locked: {lk}' for v,lk in sorted(seen.items())))
print(f"STOP: H-LOCK after turn {t}: {', '.join(bad)} after the lock: the arm was not held (protocol 8)" if bad else f"lock held after turn {t}")
PY
    tail -1 $L/lock-held.txt
  fi
fi
# 4. the snapshots, last
zsh $EV/harness/quality_snapshot.sh $LABEL turn-$NN
zsh $EV/harness/services_snapshot.sh $LABEL turn-$NN
