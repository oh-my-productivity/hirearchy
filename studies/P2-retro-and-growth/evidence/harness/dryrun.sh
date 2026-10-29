#!/bin/zsh
# P2 dry run before the freeze (protocol 13.3; 17.5, F-P1-9, H-A1), on a throwaway org in EACH arm under /tmp/hirearchy-p2/.
# Usage: dryrun.sh <R|C> <out dir>      (selfcheck.sh calls it; the out dir is under EV/harness-selfcheck/)
# 1. `--help` of every CLI subcommand the harness calls, with each flag it passes checked in that help (help-check.txt);
# 2. dryrun_build.py --phase setup: the team and the memo service, memos 1-4 with P1-sized reworks (three trap rejections: a new criterion,
#    then two "same as" links), the relayed rework of memo 1, three judged one-offs of one shape;
# 3. the snapshot scripts as after_turn.sh runs them (quality, services; arm R: the retro snapshot on a scratch copy, the ledger unchanged);
# 4. arm R: `hirearchy retro` (text) records B1 on the throwaway org (its reply as an MCP reply would read: the same render, design 4.7) and
#    `retro --json` shows it again; the brief must hold `service` and `checker-add` with 17.3's numbers; the two items' extension files
#    (their blueprints, the deliverable filled with ITEM-DELIVERABLE's answer) are `plan`ned and `apply`ed one at a time; phase after (memo
#    5, a request of the new service, a hand edit of a charter: an `outside the tools` change, so X3's count must read 1 in both); B2;
# 5. the injection script in its arm's form: --dry-run and --selftest;
# 6. copy_org_evidence.sh, the facts the session would give (constructed from the CLI replies: applies, plans, retro replies, one-offs,
#    Lena's lines), rederive_p2.py, and score_stream.sh (C5: extract_p2.py --checks, watch_views.sh, score_p2.py, gate_p1.py, as the gate runs them);
#    the expected verdicts are written below before the run.
ARM_IN="$1"; OUT="$2"
H0=${0:A:h}; export H0   # the constructed-facts and label blocks import the harness modules from $H0
LABEL=selfcheck-$ARM_IN
source $H0/arm.sh $LABEL || exit 2
rm -rf $OUT; mkdir -p $OUT; OUT=${OUT:A}   # a fresh folder: an earlier run's evidence copy would mix two orgs
E=$(date +%s); S=$P/$LABEL-$E; mkdir -p $S
export P2_EVDIR=$OUT/ev; mkdir -p $P2_EVDIR; echo $S > $P2_EVDIR/sandbox-path.txt; echo $ARM > $P2_EVDIR/arm.txt
LOG=$OUT/dryrun.txt; : > $LOG
say() { print -r -- "$*" | tee -a $LOG; }
fails=0; expect() { if [[ "$2" == "$3" ]]; then say "ok  $1 ($3)"; else say "MISMATCH  $1: expected $2, got $3"; fails=$((fails+1)); fi; }
say "# dry run, arm $ARM, product $REPO_A, org $S/org, $(date -u +%FT%TZ)"
# 1. --help of every subcommand and flag the harness passes
HC=$OUT/help-check.txt; : > $HC
helpchk() {  # helpchk <subcommand words...> -- <flags...>
  local sub=() flags=() seen=0
  for a in "$@"; do [[ "$a" == -- ]] && { seen=1; continue; }; (( seen )) && flags+=("$a") || sub+=("$a"); done
  local h=$("${HIR[@]}" $sub --help 2>&1); local rc=$?
  for f in $flags; do print -r -- "$h" | grep -q -- "$f" && echo "OK $sub $f" >> $HC || { echo "MISMATCH $sub $f (exit $rc)" >> $HC; fails=$((fails+1)); }; done
  (( ${#flags} == 0 )) && { (( rc == 0 )) && echo "OK $sub (help exit 0)" >> $HC || { echo "MISMATCH $sub: help exit $rc" >> $HC; fails=$((fails+1)); }; }
}
helpchk init -- --mission; helpchk quality -- --json; helpchk services; helpchk check; helpchk progress; helpchk status; helpchk health
helpchk obs trace; helpchk hire -- --role --charter; helpchk define-service -- --description --input --acceptance --deliverable --path --budget
helpchk task -- --title --goal --acceptance --budget; helpchk run -- --until-done --max-runs; helpchk plan -- --allow-root; helpchk apply -- --allow-root; helpchk --root -- --root
[[ $ARM == R ]] && helpchk retro -- --since --json
say "help checks: $(grep -c '^OK' $HC) OK, $(grep -c '^MISMATCH' $HC) MISMATCH (help-check.txt)"
# 2. the throwaway org
env -u KIRO_HOME HIREARCHY_WORKSPACE_ROOTS=$S uv --directory $REPO_A run python $H0/dryrun_build.py --arm $ARM --org /private$S/org --repo $REPO_A --phase setup > $OUT/build-setup.txt 2>&1
expect "dryrun_build setup exit" 0 $?
# the MCP server's catalog of this arm (dryrun_build.py made one read-only whoami call over MCP before the plan, as a stream's assistant does)
env -u KIRO_HOME uv --directory $REPO_A run python $H0/mcp_catalog.py --repo $REPO_A --org $S/org --out $OUT/catalog-$ARM.json > $OUT/catalog.txt 2>&1
expect "mcp_catalog (list_tools over MCP)" 0 $?
if [[ $ARM == R ]]; then
  # F7 (c): the TRAP-N rejection recorded through root's MCP feedback in each form, on scratch copies of the org after memos 1-4; the
  # product's reply (its question for the rejection) kept; each form answered by its pre-registered row (K29, K30, K30c); memo 5's case
  # must then lie in [trap-crit]'s class (the re-derivation's firing class holds 4 cases with memo 5's)
  for form in a b c; do
    C7=$S/f7-$form; mkdir -p $C7; cp -pR $S/org $C7/org
    env -u KIRO_HOME HIREARCHY_WORKSPACE_ROOTS=$S uv --directory $REPO_A run python $H0/dryrun_build.py --arm R --org /private$C7/org --repo $REPO_A --phase f7 --form $form > $OUT/f7-$form-build.txt 2>&1
    expect "F7 form $form: the rejection recorded over MCP and answered by its row" 0 $?
    cp -p $C7/f7-$form.json $OUT/f7-$form.json 2>/dev/null
    E7=$C7/ev; mkdir -p $E7; echo $C7 > $E7/sandbox-path.txt; echo R > $E7/arm.txt
    P2_EVDIR=$E7 zsh $H0/copy_org_evidence.sh $C7 $LABEL > $OUT/f7-$form-copy.txt 2>&1
    python3 -B $H0/rederive_p2.py $E7 --out $E7/rd > /dev/null 2>&1
    expect "F7 form $form: memo 5's case lies in [trap-crit]'s firing class (4 cases)" yes "$(python3 - $E7/rd/signals.json $OUT/f7-$form.json <<'PY'
import json,sys
sig=json.load(open(sys.argv[1])); f=json.load(open(sys.argv[2]))
ok=any(c["fires"] and "C6" in c["class"] and f["memo5"] in c["evidence"] and len(c["evidence"])==4 for s in sig["checker"] for c in s["candidates"])
print("yes" if ok else "no")
PY
)"
    python3 -c "import json;f=json.load(open('$OUT/f7-$form.json'));print('form $form question:', [l for l in f['reply'].splitlines() if 'yes/no question' in l][0][:400])" >> $LOG 2>&1
  done
  # label coverage for P2-E on copy a: by lead (a parent's MCP write), by root outside a plan (terminal hires), from your change (an
  # extension's retire), a service defined and retired at the terminal; the product's look-back D8 against the re-derivation's
  C7=$S/f7-a
  env -u KIRO_HOME HIREARCHY_WORKSPACE_ROOTS=$S uv --directory $REPO_A run python $H0/dryrun_build.py --arm R --org /private$C7/org --repo $REPO_A --phase labels > $OUT/labels-build.txt 2>&1
  expect "label coverage: the changes made" 0 $?
  "${HIR[@]}" --root $C7/org retro --since 2026-10-01 --json > $OUT/labels-lookback.json 2>$OUT/labels-lookback.stderr.txt
  rm -rf $C7/ev; E7=$C7/ev; mkdir -p $E7; echo $C7 > $E7/sandbox-path.txt; echo R > $E7/arm.txt
  P2_EVDIR=$E7 zsh $H0/copy_org_evidence.sh $C7 $LABEL > $OUT/labels-copy.txt 2>&1
  python3 -B $H0/rederive_p2.py $E7 --out $E7/rd --since 2026-10-01T00:00:00+00:00 > /dev/null 2>&1
  H0=$H0 python3 - $E7/rd/d8.json $OUT/labels-lookback.json > $OUT/labels-compare.txt <<'PY'
import json,os,sys
sys.path.insert(0,os.environ["H0"])
import rederive_p2 as R
h=json.load(open(sys.argv[1])); p=R.parse_product_d8(json.load(open(sys.argv[2]))["sections"]["d8"]["details"])
k=lambda x:(x["kind"],x["subject"],x["label"],x["id"],x["item"])
H,P=set(map(k,h)),set(map(k,p))
print("both:", sorted(H&P)); print("harness only:", sorted(H-P)); print("product only:", sorted(P-H))
PY
  cat $OUT/labels-compare.txt >> $LOG
  expect "label coverage: every product D8 line equals the re-derivation's (by lead, from your change, by root outside a plan, retires)" "product only: []" "$(grep '^product only' $OUT/labels-compare.txt)"
  expect "label coverage: the re-derivation's only extra lines are the creations of the retired agent and service (SELFCHECK.md: product finding PF-1)" \
    "harness only: [('agent added', 'ops-helper', 'by root, outside a plan', None, None), ('service added', 'lead/extra-svc', 'by root, outside a plan', None, None)]" \
    "$(grep '^harness only' $OUT/labels-compare.txt)"
  # protocol 12.6 (3): P2-E's classifier over the product's own output. PF-1 on the label-coverage org; PF-0 on a terminal-only org
  pfclass() {  # pfclass <evidence dir> <re-derived d8.json> <product retro --json> <out>
    H0=$H0 python3 - "$@" <<'PY2'
import json,os,sys
from collections import Counter
from pathlib import Path
sys.path.insert(0,os.environ["H0"])
import rederive_p2 as R, extract_p2 as X
E,h,p,o=Path(sys.argv[1]),json.load(open(sys.argv[2])),R.parse_product_d8(json.load(open(sys.argv[3]))["sections"]["d8"]["details"]),sys.argv[4]
f=X.classify_d8(p,h,R.events_of(E)); c=Counter(x["class"] for x in f)
open(o,"w").write("\n".join([X.finding_line("look-back","D8",x) for x in f]+[f"PF-0 {c['PF-0']} PF-1 {c['PF-1']} new {c['new']}"])+"\n")
PY2
    tail -1 $4; }
  expect "12.6: the classifier over the label-coverage org reads PF-1 for both missing creations, nothing new" "PF-0 0 PF-1 2 new 0" \
    "$(pfclass $E7 $E7/rd/d8.json $OUT/labels-lookback.json $OUT/labels-classify.txt)"
  # PF-0 on the product's own output (12.6). The product's label depends on the sub-second timing of the build (iteration 3's self-check:
  # it gives the horizon label exactly when the event log's earliest record falls in the same whole second as the older commit, after it
  # in microseconds). Freeze fix (manager ruling (b)): each timing is built by construction, not by chance: `--align same` starts the build
  # just after a whole-second boundary, `--align earlier` waits for the next boundary after `apply` before the commit. A build is kept
  # whatever second it fell in; each try is recorded in pf0-timing.txt (at most 8 per timing, `same` retried only when a slow machine
  # pushed the build over a second). Each timing reached is checked; pf0_timing.py decides: every build classified correctly (0
  # misclassified), a PF-0 reproduced, and a timing not reached recorded as `not reached; covered by the constructed cases ...`
  : > $OUT/pf0-timing.txt; SAME=""; EARLIER=""
  for WANT in same earlier; do
    for i in 1 2 3 4 5 6 7 8; do
      P0=$S/pf0-$WANT-$i; mkdir -p $P0
      env -u KIRO_HOME HIREARCHY_WORKSPACE_ROOTS=$S uv --directory $REPO_A run python $H0/dryrun_build.py --arm R --org /private$P0/org --repo $REPO_A --phase pf0 --align $WANT > $OUT/pf0-build-$WANT-$i.txt 2>&1 || { echo "try $WANT $i: build failed" >> $OUT/pf0-timing.txt; continue; }
      "${HIR[@]}" --root $P0/org retro --since 2026-10-01 --json > $P0/lookback.json 2>$P0/lookback.stderr.txt
      T=$(python3 - $P0/org $P0/lookback.json <<'PY3'
import json, subprocess, sys
from datetime import datetime
from pathlib import Path
org, lb = Path(sys.argv[1]), sys.argv[2]
ts = [json.loads(l)["ts"] for f in sorted((org / ".runtime" / "events").glob("*/*.jsonl")) for l in f.read_text().splitlines() if l.strip()]
fe = datetime.fromisoformat(min(ts))
t1 = datetime.fromisoformat(subprocess.run(["git", "-C", str(org), "log", "--reverse", "--format=%cI", "--", "lead/writer/AGENT.md"], capture_output=True, text=True).stdout.split()[0].replace("Z", "+00:00"))
lab = [l for l in json.load(open(lb))["sections"]["d8"]["details"] if l.startswith("- charter of lead/writer changed")]
kind = "same" if fe.replace(microsecond=0) == t1 and fe > t1 else ("earlier" if fe < t1 else "other")
print(f"{kind}|first record {fe.isoformat()} | older commit t1 {t1.isoformat()} | product: {lab[0] if lab else 'none'}")
PY3
)
      echo "try $WANT $i (built as ${T%%|*}): ${T#*|}" >> $OUT/pf0-timing.txt
      case "${T%%|*}" in same) [[ -z $SAME ]] && SAME=$P0;; earlier) [[ -z $EARLIER ]] && EARLIER=$P0;; esac
      [[ "${T%%|*}" == $WANT ]] && break
    done
  done
  cat $OUT/pf0-timing.txt >> $LOG
  : > $OUT/pf0-builds.txt
  for KIND in same earlier; do
    P0=${(P)${KIND:u}}; [[ -n $P0 ]] || continue
    SFX=$([[ $KIND == same ]] && echo "" || echo "-earlier")
    cp -p $P0/lookback.json $OUT/pf0$SFX-lookback.json; cp -p $P0/lookback.stderr.txt $OUT/pf0$SFX-lookback.stderr.txt
    E0=$P0/ev; mkdir -p $E0; echo $P0 > $E0/sandbox-path.txt; echo R > $E0/arm.txt
    P2_EVDIR=$E0 zsh $H0/copy_org_evidence.sh $P0 $LABEL > $OUT/pf0$SFX-copy.txt 2>&1
    python3 -B $H0/rederive_p2.py $E0 --out $E0/rd --since 2026-10-01T00:00:00+00:00 > /dev/null 2>&1
    python3 -c "import json;print('\n'.join(json.load(open('$OUT/pf0$SFX-lookback.json'))['sections']['d8']['details']))" > $OUT/pf0$SFX-d8.txt 2>&1
    cat $OUT/pf0$SFX-d8.txt >> $LOG
    if [[ $KIND == same ]]; then
      expect "PF-0 (same second): the product gives the horizon label" yes "$(grep -q 'charter of lead/writer changed: body .*: by lead, or outside the tools (the event log does not reach back)' $OUT/pf0-d8.txt && echo yes || echo no)"
      CL=$(pfclass $E0 $E0/rd/d8.json $OUT/pf0-lookback.json $OUT/pf0-classify.txt)
      expect "12.6: the classifier over the same-second terminal-only org reads the product's horizon label as PF-0, nothing new" "PF-0 1 PF-1 0 new 0" "$CL"
    else
      expect "PF-0 (an earlier second): the product gives the design's label" yes "$(grep -q 'charter of lead/writer changed: body .*: outside the tools (a hand edit or the terminal)' $OUT/pf0-earlier-d8.txt && echo yes || echo no)"
      CL=$(pfclass $E0 $E0/rd/d8.json $OUT/pf0-earlier-lookback.json $OUT/pf0-earlier-classify.txt)
      expect "12.6: the classifier over the earlier-second org finds no difference" "PF-0 0 PF-1 0 new 0" "$CL"
    fi
    echo "$KIND|$CL" >> $OUT/pf0-builds.txt
  done
  python3 - $OUT/pf0-builds.txt $OUT/pf0-builds.json <<'PY4'
import json, sys
print(json.dumps([{"kind": k, "classified": c} for k, c in (l.rstrip("\n").split("|", 1) for l in open(sys.argv[1]) if "|" in l)]), file=open(sys.argv[2], "w"))
PY4
  PFV=$(python3 -B $H0/pf0_timing.py $OUT/pf0-builds.json); echo "pf0 timing verdict: $PFV" | tee $OUT/pf0-verdict.txt >> $LOG
  expect "PF-0: every timing reached is classified correctly, a PF-0 is reproduced, a timing not reached is recorded" PASS "${PFV%%:*}"
fi
# 3. the snapshots as after_turn.sh runs them
zsh $H0/quality_snapshot.sh $LABEL turn-01 >> $LOG; zsh $H0/services_snapshot.sh $LABEL turn-01 >> $LOG
expect "quality turn-01 read" "exit 0 json ok" "$(grep -o 'exit [0-9]* bytes [0-9]* json [a-z]*' $P2_EVDIR/quality/calls.txt | head -1 | sed 's/ bytes [0-9]*//')"
expect "services turn-01 read" 0 "$(grep -o '^turn-01 start .* exit [0-9]*' $P2_EVDIR/services/calls.txt | awk '{print $NF}')"
if [[ $ARM == R ]]; then
  zsh $H0/retro_snapshot.sh $LABEL turn-01 >> $LOG
  expect "the retro snapshot left the stream ledger as it was (absent)" "absent absent" "$(grep -o 'before [a-z0-9]* after [a-z0-9]*' $P2_EVDIR/retro/calls.txt | head -1 | awk '{print $2, $4}')"
  python3 - $P2_EVDIR/retro/turn-01.json > $OUT/retro-turn-01-items.txt <<'PY'
import json,sys
j=json.load(open(sys.argv[1])); its={i["kind"]:i for i in j["items"]}
print("kinds", sorted(its))
c=its.get("checker-add",{}); print("question", c.get("question","")); print("notes", c.get("notes"))
PY
  cat $OUT/retro-turn-01-items.txt >> $LOG
  expect "the scratch brief holds service and checker-add" "yes" "$(grep -q "kinds.*'checker-add'.*'service'" $OUT/retro-turn-01-items.txt && echo yes || echo no)"
  expect "17.3's numbers: net -2.0 = 0.8 x 3 - 2 - 0.8 x 3, from 3 of 4 cases" yes "$(grep -q 'net -2.0 = 0.8 × 3 − 2 − 0.8 × 3, from 3 of 4 cases' $OUT/retro-turn-01-items.txt && echo yes || echo no)"
  expect "the question's words" yes "$(grep -q 'about 2.0 more runs per request than the rework it saves' $OUT/retro-turn-01-items.txt && echo yes || echo no)"
  # 4. B1 recorded (text reply), the two items applied at the terminal, then B2
  "${HIR[@]}" --root $S/org retro > $OUT/B1.txt 2>&1
  "${HIR[@]}" --root $S/org retro --json > $OUT/B1.json 2>&1
  expect "a second call shows B1 again" "B1 True" "$(python3 -c "import json;j=json.load(open('$OUT/B1.json'));print(j['id'],bool(j['shown_again']))")"
  sleep 1.2
  python3 - $OUT/B1.json $S $OUT <<'PY'
import json,sys
j=json.load(open(sys.argv[1])); S,O=sys.argv[2],sys.argv[3]
for it in j["items"]:
    if not it["blueprint"]: continue
    bp=json.loads(it["blueprint"])
    for s in bp["extend"].get("add_services",[]):
        s["deliverable"]={"description":"One action list per request","format":"markdown","path":S+"/deliverables"}
    open(f"{O}/ext-{it['n']}-{it['kind']}.json","w").write(json.dumps(bp,indent=1))
PY
  for f in $OUT/ext-1-service.json $OUT/ext-2-checker-add.json; do
    "${HIR[@]}" --root $S/org plan $f --allow-root $S > ${f%.json}.plan.txt 2>&1; expect "plan ${f:t}" 0 $?
    "${HIR[@]}" --root $S/org apply $f --allow-root $S > ${f%.json}.apply.txt 2>&1; expect "apply ${f:t}" 0 $?
  done
  SVC=$(python3 -c "import json;print(json.load(open('$OUT/ext-1-service.json'))['extend']['add_services'][0]['name'])")
  env -u KIRO_HOME HIREARCHY_WORKSPACE_ROOTS=$S uv --directory $REPO_A run python $H0/dryrun_build.py --arm R --org /private$S/org --repo $REPO_A --phase after --service $SVC > $OUT/build-after.txt 2>&1
  expect "dryrun_build after exit" 0 $?
  "${HIR[@]}" --root $S/org retro > $OUT/B2.txt 2>&1
  expect "B2 shows both items taken" 2 "$(grep -cE '^- B1\.[12] (service|checker-add): taken' $OUT/B2.txt)"
fi
[[ $ARM == C ]] && { env -u KIRO_HOME HIREARCHY_WORKSPACE_ROOTS=$S uv --directory $REPO_A run python - $S <<'PY' > $OUT/build-after.txt 2>&1
import subprocess,sys
from pathlib import Path
org=Path(sys.argv[1])/"org"; c=org/"lead"/"writer"/"AGENT.md"; c.write_text(c.read_text()+"\nA line the human typed by hand.\n")
subprocess.run(["git","-C",str(org),"add","-A"],check=True); subprocess.run(["git","-C",str(org),"commit","-q","-m","hand edit (study self-check)"],check=True)
print("hand edit committed")
PY
}
# 5. the injection script, the arm's form
M1=$(python3 -c "import json;print(json.load(open('$S/dryrun-facts.json'))['memos']['1'][0])")
zsh $H0/injection.sh $LABEL $M1 --dry-run > $OUT/injection-dry-run.txt 2>&1; expect "injection --dry-run" 0 $?
zsh $H0/injection.sh $LABEL --selftest > $OUT/injection-selftest.txt 2>&1; expect "injection --selftest" 0 $?
# 6. the evidence copy and every reader over it
zsh $H0/quality_snapshot.sh $LABEL end >> $LOG; zsh $H0/services_snapshot.sh $LABEL end >> $LOG
zsh $H0/copy_org_evidence.sh $S $LABEL > $OUT/copy.txt 2>&1; expect "copy_org_evidence" 0 $?
python3 - $P2_EVDIR $S $OUT $ARM <<'PY'
# the facts the assistant's session would give, constructed from the CLI replies (the terminal's replies have the same render)
import json,re,sys,glob,os
from pathlib import Path
E,S,O,ARM=map(Path,sys.argv[1:4])+[sys.argv[4]] if False else (Path(sys.argv[1]),Path(sys.argv[2]),Path(sys.argv[3]),sys.argv[4])
(E/"p2"/"retro-replies").mkdir(parents=True,exist_ok=True)
facts=json.loads((S/"dryrun-facts.json").read_text())
bp=json.loads((S/"blueprint.json").read_text())
applies=[]; plans=[]
mt=lambda p: __import__("datetime").datetime.fromtimestamp(os.path.getmtime(p),__import__("datetime").timezone.utc).isoformat()
first=json.loads(open(E/"org-files"/"retros.json").read()).get("briefs",[{}])[0].get("since") if (E/"org-files"/"retros.json").exists() else None
created=(re.search(r"^created: '?([^'\n]+)",(E/"org-copy"/"lead"/"AGENT.md").read_text(),re.M) or [None,None])[1]
plan_text=(S/"dryrun-plan.txt").read_text()
applies.append({"t":created,"ok":True,"change":None,"plan_id":"terminal","approved":True,"blueprint":bp,"extend":False,"proposal":plan_text,"result":(S/"dryrun-apply.txt").read_text()})
for n,k in ((1,"service"),(2,"checker-add")):
    f=O/f"ext-{n}-{k}.json"
    if not f.exists(): continue
    res=(O/f"ext-{n}-{k}.apply.txt").read_text(); m=re.search(r"applied the change (\w+)",res)
    applies.append({"t":mt(O/f"ext-{n}-{k}.apply.txt"),"ok":bool(m),"change":m.group(1) if m else None,"plan_id":m.group(1) if m else None,"approved":True,
                    "blueprint":json.loads(f.read_text()),"extend":True,"proposal":(O/f"ext-{n}-{k}.plan.txt").read_text(),"result":res})
(E/"p2"/"applies.json").write_text(json.dumps(applies,indent=1)); (E/"p2"/"plans.json").write_text("[]")
(E/"p2"/"t0.txt").write_text((created or "")+"\n")
reps=[]
for b in ("B1","B2"):
    if (O/f"{b}.txt").exists():
        (E/"p2"/"retro-replies"/f"{b}.txt").write_text((O/f"{b}.txt").read_text()); reps.append({"id":b,"shown_again":False,"t":mt(O/f"{b}.txt")})
(E/"p2"/"retro-replies.json").write_text(json.dumps(reps,indent=1))
(E/"end.txt").write_text("end retro-2-done at turn 9 (the dry run's constructed end)\n")
# Lena's lines and turn times that the script would give: the three lists after ACT-REQ lines, the items said yes after B1
recs=json.loads((E/"org-files"/"retros.json").read_text())["briefs"] if (E/"org-files"/"retros.json").exists() else []
oo=facts["one_offs"]; rj=facts["rejections"]; tr=facts["trap_rejections"]
from datetime import datetime,timedelta,timezone
def st(mid): return datetime.strptime(mid[:21],"%Y%m%dT%H%M%S%f").replace(tzinfo=timezone.utc)
ms=lambda n: timedelta(milliseconds=n)
# the Lena lines the script would give, in the order of the build's events, each turn starting 1 ms before its event (protocol 4.3, 4.6)
ev=[("H6",rj[0]),("ACCEPT@2026-10-05 + ACT-REQ@2026-10-05",oo[0]),("TRAP-1@2026-10-12",tr[0]),("ACCEPT@2026-10-12 + ACT-REQ@2026-10-12",oo[1]),
    ("TRAP-N@2026-10-19",tr[1]),("ACCEPT@2026-10-19 + ACT-REQ@2026-10-19",oo[2]),("TRAP-N@2026-10-26",tr[2])]
lines,times=[],[]
for n,(rules,mid) in enumerate(ev,1):
    lines.append(f"turn {n} | rules {rules} | table rows none | facts: the dry run's event {mid}"); times.append((n,st(mid)-ms(1)))
# L0 (protocol 4.6; F27 of review 2): the line that answers the third trap rejection's question, 1 ms after that rejection
lines.append("turn 8 | rules ANSWER + CONDITION | table rows K29 | facts: answers TRAP-N@2026-10-26; Same as R<j>: a one-off? Yes."); times.append((8,st(tr[2])+ms(1)))
if recs and len(applies)>1:
    b1=datetime.fromisoformat(recs[0]["at"]); lines.append("turn 9 | rules RETRO-YES + ITEM-SERVICE + ITEM-CHECKER | table rows K41, K42, K45 | facts: x"); times.append((9,b1+ms(1)))
    lines.append("turn 10 | rules PLAN-APPROVE | table rows K44 | facts: x"); times.append((10,b1+ms(2)))
times.append((11,datetime(2100,1,1,tzinfo=timezone.utc)))
(E/"lena-lines.txt").write_text("\n".join(lines)+"\n")
# the dry run's relayed rework (A-R) is made through the Org facade, not E7's script: its injection record is constructed from the task
# (request-args.json's revises and title, E7 5), so gate_p1 identifies it as it identifies the injection in a stream
if facts.get("relayed"):
    t=next((p for p in (E/"msgs").glob("*/"+facts["relayed"][0]+".md")),None)
    if t:
        import yaml; m=yaml.safe_load(t.read_text().split("---",2)[1])
        (E/"injection").mkdir(exist_ok=True); (E/"injection"/"request-args.json").write_text(json.dumps({"revises":m.get("revises"),"title":m.get("title"),"source":"relayed"}))
(E/"turn-times.txt").write_text("\n".join(f"turn {n}: 00:00:00 - 00:00:00  0-0=0s  utc {t.isoformat()} - {t.isoformat()}  exit 0  sleep 20 ended utc {t.isoformat()}" for n,t in times)+"\n")
sys.path.insert(0,os.environ["H0"])
import extract_p2 as X, lena_lines as LL
lena=LL.counts(str(E/"lena-lines.txt")); (E/"p2"/"lena.json").write_text(json.dumps(lena))
(E/"p2"/"oneoffs.json").write_text(json.dumps(X.oneoffs(E,lena)))
print("constructed facts:", len(applies), "applies;", len(lines), "Lena lines")
PY
[[ $ARM == R ]] && { zsh $H0/retro_snapshot.sh $LABEL end --since-apply "$(cat $P2_EVDIR/p2/t0.txt | tr -d '\n')" >> $LOG; }
# C5 (F42 of review 3): the measures' inputs through score_stream.sh, the driver the stage gate and step 12 run (its four steps:
# extract_p2.py --checks, watch_views.sh, score_p2.py, gate_p1.py), in place of the four direct calls; the selfcheck label's evidence
# folder comes from P2_EVDIR, as in copy_org_evidence.sh
zsh $H0/score_stream.sh $LABEL > $OUT/score_stream.txt 2>&1; expect "score_stream.sh exit" 0 $?
SS=$P2_EVDIR/score-steps.txt; cp -p $SS $OUT/score-steps.txt 2>/dev/null
expect "score_stream.sh: score-steps.txt lists four steps, each exit 0" "4 of 4" "$(grep -c '^exit 0: ' $SS 2>/dev/null) of $(grep -c '^exit ' $SS 2>/dev/null)"
if [[ $ARM == R ]]; then  # the --am-time rule: passed when lena-lines.txt holds an A-M line, else left out
  if grep -qE '^turn [0-9]+ \| rules ([^|]* \+ )?A-M@2026-11-09( \+ [^|]*)? \|' $P2_EVDIR/lena-lines.txt; then
    expect "score_stream.sh: --am-time passed to score_p2.py (the constructed lena-lines.txt holds an A-M line)" yes "$(grep -E '^exit 0: .*score_p2\.py' $SS | grep -q -- '--am-time 20' && echo yes || echo no)"
  else
    expect "score_stream.sh: --am-time left out (the constructed lena-lines.txt holds no A-M line)" "left out" "$(grep -E '^exit [0-9]+: .*score_p2\.py' $SS | grep -q -- '--am-time' && echo passed || { grep -qE '^exit [0-9]+: .*score_p2\.py' $SS && echo 'left out' || echo 'no score_p2 step'; })"
  fi
  # the other branch, on a scratch copy of the evidence with an A-M line added (the closing pass found score_stream.sh passing the line's
  # turn number instead of its turn start): --am-time must be that turn's start in turn-times.txt
  AE=$S/am-ev; rm -rf $AE; cp -pR $P2_EVDIR $AE; : > $AE/score-steps.txt
  AMN=$(awk -F'[ :|]+' '/^turn /{n=$2} END{print n}' $AE/lena-lines.txt)
  echo "turn $AMN | rules ACCEPT@2026-11-02 + A-M@2026-11-09 | table rows none | facts: constructed for the --am-time check" >> $AE/lena-lines.txt
  AMS=$(grep -E "^turn $AMN: " $AE/turn-times.txt | head -1 | sed -E 's/^.*utc ([^ ]+) - .*$/\1/')
  P2_EVDIR=$AE zsh $H0/score_stream.sh $LABEL > $OUT/score_stream-am.txt 2>&1
  cp -p $AE/score-steps.txt $OUT/score-steps-am.txt 2>/dev/null
  expect "score_stream.sh: --am-time passed as the A-M line's turn start (scratch copy with an A-M line)" "--am-time $AMS" "$(grep -E '^exit 0: .*score_p2\.py' $AE/score-steps.txt | grep -oE -- '--am-time [^ ]+')"
fi
cp -p $P2_EVDIR/score-extract_p2-checks.txt $OUT/checks.txt 2>/dev/null
cat $P2_EVDIR/p2/verdicts.txt >> $LOG 2>/dev/null
python3 -B $H0/rederive_p2.py $P2_EVDIR --out $P2_EVDIR/rederived/end > $OUT/rederive-end.txt 2>&1
if [[ $ARM == R ]]; then
  expect "P2-X1 on the dry run" PASS "$(grep -o '^P2-X1: [A-Z ]*' $P2_EVDIR/p2/verdicts.txt | sed 's/^P2-X1: //;s/ *$//')"
  expect "P2-X2 on the dry run" PASS "$(grep -o '^P2-X2: [A-Z ]*' $P2_EVDIR/p2/verdicts.txt | sed 's/^P2-X2: //;s/ *$//')"
  expect "P2-X3 on the dry run (one hand edit: harness 1, product 1)" FAIL "$(grep -o '^P2-X3: [A-Z]*' $P2_EVDIR/p2/verdicts.txt | sed 's/^P2-X3: //')"
  expect "the harness's and the product's counts agree" yes "$(grep -q 'harness 1 \[.lead/writer/AGENT.md.\], product 1' $P2_EVDIR/p2/verdicts.txt && echo yes || echo no)"
  expect "P2-E on the dry run (B1 and B2 against the re-derivation)" PASS "$(grep -o '^P2-E: [A-Z]*' $P2_EVDIR/p2/verdicts.txt | sed 's/^P2-E: //')"
  expect "P2-S on the dry run" PASS "$(grep -o '^P2-S: [A-Z]*' $P2_EVDIR/p2/verdicts.txt | sed 's/^P2-S: //')"
  expect "P2-B on the dry run (every change labelled; no fact-checker)" PASS "$(grep -o '^P2-B: [A-Z]*' $P2_EVDIR/p2/verdicts.txt | sed 's/^P2-B: //')"
  expect "P2-L on the dry run (B1 then B2: taken and lapsed lines)" PASS "$(grep -o '^P2-L: [A-Z]*' $P2_EVDIR/p2/verdicts.txt | sed 's/^P2-L: //')"
  expect "P2-W(c) on the dry run (the full plan's source lines)" PASS "$(grep -o '^P2-W(c): [A-Z]*' $P2_EVDIR/p2/verdicts.txt | sed 's/^P2-W(c): //')"
else
  expect "arm C: the harness counts the hand edit" 1 "$(python3 -c "import json;print(json.load(open('$P2_EVDIR/rederived/end/edits.json'))['count'])")"
fi
# the outputs of score_stream.sh's steps 2-4 (C5): watch_views, score_p2, gate_p1
cp -p $P2_EVDIR/score-watch_views.txt $OUT/watch.txt 2>/dev/null; cat $OUT/watch.txt >> $LOG
cp -p $P2_EVDIR/measures/score_p2-output.txt $OUT/score_p2.txt 2>/dev/null
cp -p $P2_EVDIR/score-gate_p1.txt $OUT/gate_p1.txt 2>/dev/null; cat $OUT/gate_p1.txt >> $LOG
# the gate-able measures the construction determines, on the product's real output (the rest fail closed by construction: no session,
# no snapshot per constructed turn, no judged.json; listed in SELFCHECK.md)
gv() { grep -F "$1: " $OUT/gate_p1.txt | head -1 | sed "s/^$1: //" | awk '{print $1}'; }
for m in "G1(a)" "G1(c)" "G1(e)" "G2(a)" "G2(b)" "escapes typed by the user's answer" "relayed reworks sent by the assistant (the injection excepted)"; do
  expect "gate_p1 on the dry run: $m" PASS "$(gv "$m")"
done
expect "gate_p1 on the dry run: G1(b) (no item reached retire due)" VACUOUS "$(gv "G1(b)")"
expect "gate_p1 on the dry run: hand edits fail closed without a session" NOT "$(gv "hand edits")"
# F31 of review 2: the finish runs P1's extract_mechanical.py with --product-src $REPO_A/src; rendered for this arm it names the arm's
# product (arm C: REPO_C), and the import it makes with that path first on sys.path (extract_mechanical.py lines 396-398) is that product's
EMA=$(D=EV/$LABEL S=S zsh -c 'H0='$H0'; REPO_A='$REPO_A'; D=EV; S=S; '"$(grep '^EM_ARGV=' $H0/finish_stream.sh)"'; print -r -- "${EM_ARGV[*]}"')
expect "F31: the finish's extract_mechanical argv passes the arm's product (--product-src $REPO_A/src)" yes "$([[ "$EMA" == *"--product-src $REPO_A/src" && "$EMA" != *"--product-src $REPO_OTHER/src"* ]] && echo yes || echo no)"
EMI=$(python3 -B -c "import sys; sys.dont_write_bytecode=True; sys.path.insert(0, '$REPO_A/src'); from hirearchy.kernel._text import client_questions; import hirearchy.kernel._text as m; print(m.__file__)" 2>&1)
expect "F31: client_questions imported from the arm's product" "$REPO_A/src/hirearchy/kernel/_text.py" "$EMI"
[[ $ARM == C ]] && expect "F31: arm C's product is the worktree" "$REPO_C" "$REPO_A"
say "dry run arm $ARM: $fails mismatch(es)"
echo "$S" > $OUT/sandbox.txt
exit $(( fails > 0 ))
