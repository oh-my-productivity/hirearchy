#!/bin/zsh
# G0 harness self-check (protocol section 10; design 20.2: "Before the first stream it must re-derive E7's published counts from E7's raw
# evidence (a self-check); a mismatch stops the study"). Usage: selfcheck.sh [<out dir>]   (default: EV/harness-selfcheck)
# Runs, on E7's committed s1-s3 (read-only), every script's --selfcheck against selfcheck/e7-expected-*.json (transcribed from design 19.3's
# E7 block and E7 STUDY, never from a script's output), then the harness's unit tests. Prints one line per module and a final line
#   selfcheck: <modules OK> of <modules> modules OK; tests exit <rc>
# and exits 0 iff every module and the tests pass. Writes only under <out dir>; never touches E7's folder, ~/.kiro, a sandbox or an org.
REPO=/Volumes/workspace/hirearchy
H=$REPO/studies/G0-noise-baseline/evidence/harness
E7EV=$REPO/studies/E7-org-growth-0a4-recheck/evidence
OUT="${1:-$REPO/studies/G0-noise-baseline/evidence/harness-selfcheck}"
mkdir -p "$OUT"
cd "$H" || exit 2
export PYTHONDONTWRITEBYTECODE=1
ok=0; all=0
check() {  # check <name> <command...>: runs it, keeps its full output in $OUT/<name>.out, prints its last line
  local name=$1; shift
  all=$((all+1))
  "$@" > "$OUT/$name.out" 2>&1; local rc=$?
  print -r -- "$name: exit $rc: $(tail -1 "$OUT/$name.out")"
  [[ $rc -eq 0 ]] && ok=$((ok+1))
}
check rederive          python3 -B rederive_quality.py   --selfcheck "$E7EV" --out "$OUT"
check score_memos       python3 -B score_memos.py        --selfcheck "$E7EV" --out "$OUT"
check ambiguity_recall  python3 -B ambiguity_recall.py   --selfcheck "$E7EV" --out "$OUT"
check prompt_sizes      python3 -B prompt_sizes.py       --selfcheck "$E7EV" --out "$OUT"
check playbook_attempts python3 -B playbook_attempts.py  --selfcheck "$E7EV" --out "$OUT"
check assistant_facts   python3 -B assistant_facts.py    --selfcheck "$E7EV" --out "$OUT"
check skill_check       python3 -B skill_check.py        --selfcheck "$E7EV" --out "$OUT"
$REPO/.venv/bin/python -m pytest -q -p no:cacheprovider tests > "$OUT/tests.out" 2>&1; trc=$?
print -r -- "tests: exit $trc: $(tail -1 "$OUT/tests.out")"
find "$H" "$OUT" -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null
print -r -- "selfcheck: $ok of $all modules OK; tests exit $trc"
[[ $ok -eq $all && $trc -eq 0 ]]
