#!/bin/zsh
# P1 harness self-check (design 18.6; protocol 13.4). Usage: selfcheck.sh [<out dir>]   (default: EV/harness-selfcheck)
# Read-only on every input (G0's and E7's kept evidence); writes only under <out dir>; never touches ~/.kiro, a sandbox or an org. Parts:
#   watch_cases      every constructed case of 18.6 (8.1 rows i-xxv, the repair migration's row xii and B3's equal stamp included) and every
#                    order O1-O10 of 18.4.1, each against its pre-registered state (watch_cases.py)
#   g1_cases         guarantees.py's G1 (a)-(f) on 18.4.1's flows: every order O1-O10, 12.1's variants (O2's, memo 5's, O5's, O7 late, O9 four
#                    ways, an unscripted related rejection) and negative cases, against 12.1's table; the legal 8.1 steps into `kept` (an
#                    exempt restore, a corrected link), the unread-snapshot rule, the bounded `could not retire` reply, the pinned keys and
#                    the race rule's lower margin; iteration 3b: G2(a), one reject note per rejection on its memo's case (rules a list,
#                    VR-REJECT@<memo date>), M3-VERDICT + L-ASIS, G2(b)'s late_detail (g1_cases.py)
#   kept_mail        the kept G0 (m1-s1..s3) and E7 (s1..s3) mail with a constructed item A (and A'), against selfcheck/p1-kept-mail-expected.json;
#                    the D14 ledger's completeness against the kept G0 mail (protocol 6.3)
#   p1_scoring       score_memos.py's P1 mode on constructed memos 1-6, no regression's gate-able and reported parts, and the two private
#                    keys against the frozen tables
#   aggregate_check  aggregate.py on constructed stream folders: judged values true, false, missing; validity; D14 (reported, a missing case);
#                    D8; arm F's regressions reported with their causes; the exit on the four lines (12.4); iteration 3b: a stream ended
#                    by ruling (b) (the cut parts NOT DETERMINED, the FAILs before it standing) and validity.json's keys refused (C1, C7)
#   cost_total       the stream credits of protocol 11 on G0's six cost.txt against G0's published totals, runs without a matched session,
#                    and the > 185.00 edges
#   next_stream      next_stream.sh on constructed evidence trees: the order, the stage gate, the 185-credit pause, memories, replacements;
#                    the memories gate between two streams (memories_gate.py) and its place in setup_stream.sh
#   empty_calls      the session-store empty-argument count of f-g0-7 section 1 on G0's six streams (15/19/16, 0/0/0)
#   probe_check      probe_compare.py on constructed probe sessions (18.3 item 2)
#   g0_e7_<module>   G0's seven module self-checks on E7's raw evidence, unchanged (selfcheck/e7-expected-*.json, G0's, never edited)
#   g0_replay        G0's published per-stream outputs of its M1 streams reproduced by the P1 copies (and G2 = PASS on them)
#   tests            G0's module tests (harness/tests/, the driver and aggregate tests left out with the M0 drivers)
# Prints one line per part and a final line `selfcheck: <parts OK> of <parts> parts OK; tests exit <rc>`; exits 0 iff every part passes.
REPO=/Volumes/workspace/hirearchy
H=$REPO/studies/P1-itemized-playbook/evidence/harness
E7EV=$REPO/studies/E7-org-growth-0a4-recheck/evidence
OUT="${1:-$REPO/studies/P1-itemized-playbook/evidence/harness-selfcheck}"
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
check watch_cases               python3 -B watch_cases.py         --out "$OUT"
check g1_cases                  python3 -B g1_cases.py            --out "$OUT"
check kept_mail                 python3 -B kept_mail.py           --out "$OUT"
check p1_scoring                python3 -B p1_scoring_check.py    --out "$OUT"
check aggregate_check           python3 -B aggregate_check.py     --out "$OUT"
check cost_total                python3 -B cost_total.py          --selfcheck --out "$OUT"
check next_stream               python3 -B next_stream_check.py   --out "$OUT"
check empty_calls               python3 -B empty_calls.py         --selfcheck --out "$OUT"
check probe_check               python3 -B probe_check.py         --out "$OUT"
check g0_e7_rederive            python3 -B rederive_quality.py    --selfcheck "$E7EV" --out "$OUT/g0-e7"
check g0_e7_score_memos         python3 -B score_memos.py         --selfcheck "$E7EV" --out "$OUT/g0-e7"
check g0_e7_ambiguity_recall    python3 -B ambiguity_recall.py    --selfcheck "$E7EV" --out "$OUT/g0-e7"
check g0_e7_prompt_sizes        python3 -B prompt_sizes.py        --selfcheck "$E7EV" --out "$OUT/g0-e7"
check g0_e7_playbook_attempts   python3 -B playbook_attempts.py   --selfcheck "$E7EV" --out "$OUT/g0-e7"
check g0_e7_assistant_facts     python3 -B assistant_facts.py     --selfcheck "$E7EV" --out "$OUT/g0-e7"
check g0_e7_skill_check         python3 -B skill_check.py         --selfcheck "$E7EV" --out "$OUT/g0-e7"
check g0_replay                 python3 -B g0_replay.py           --out "$OUT"
$REPO/.venv/bin/python -m pytest -q -p no:cacheprovider tests > "$OUT/tests.out" 2>&1; trc=$?
print -r -- "tests: exit $trc: $(tail -1 "$OUT/tests.out")"
find "$H" "$OUT" -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null
print -r -- "selfcheck: $ok of $all parts OK; tests exit $trc"
[[ $ok -eq $all && $trc -eq 0 ]]
