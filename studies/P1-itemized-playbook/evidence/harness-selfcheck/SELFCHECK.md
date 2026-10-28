# P1 harness self-check (design 18.6; protocol 13.3)

Run on 2026-10-27 (iteration 3b, the manager's amendments C1-C8; last run UTC 17:15:18-17:15:35, on the files as they stand, after the last
harness change), before any freeze, sandbox, profile or stream: `zsh /Volumes/workspace/hirearchy/studies/P1-itemized-playbook/evidence/harness/selfcheck.sh` (exit 0).
Inputs, read-only: the constructed cases of `harness/watch_cases.py`, `g1_cases.py`, `aggregate_check.py`, `next_stream_check.py` and
`probe_check.py` (their throwaway folders under `aggregate-cases/`, `next-stream-cases/` and `probe-cases/` here; `g1_cases.py` and
`kept_mail.py` use temporary folders under `/tmp` and delete them), G0's kept `m0-s1`-`m1-s3` and E7's kept `s1`-`s3`. Full outputs: the
`*.out` files and folders here. The check-case scripts the manager named (`g1_cases.py`, `aggregate_check.py`, the setup and next-stream
checks of `next_stream_check.py`) are parts of this run. Also run, creating nothing: `zsh harness/setup_stream.sh F1 --dry-run` (the gates
reported, the two freeze gates failing as expected before the freeze; `memories gate: no previous stream before F1: nothing to compare`;
no folder, sandbox or profile made, checked by listing `evidence/`, `~/.kiro/agents` and `/tmp/hirearchy-p1-*` before and after; in
iteration 3b: exit 0, the listings of `evidence/` and `~/.kiro/agents` unchanged, no `/tmp/hirearchy-p1-*` before or after).

**The summary lines of iteration 3b's run** (exact):
```
watch_cases: exit 0: watch_cases: 83 of 83 checks OK
g1_cases: exit 0: g1_cases: 342 of 342 checks OK
kept_mail: exit 0: kept_mail: 135 of 135 checks OK
p1_scoring: exit 0: p1_scoring_check: 22 of 22 OK
aggregate_check: exit 0: aggregate_check: 236 of 236 checks OK
cost_total: exit 0: cost_total: 13 of 13 checks OK
next_stream: exit 0: next_stream_check: 23 of 23 checks OK
empty_calls: exit 0: empty_calls: 6 of 6 checks OK
probe_check: exit 0: probe_check: 6 of 6 checks OK
g0_e7_rederive: exit 0: selfcheck rederive: 372 of 372 OK
g0_e7_score_memos: exit 0: selfcheck score_memos: 334 of 334 OK
g0_e7_ambiguity_recall: exit 0: selfcheck ambiguity_recall: 59 of 59 OK
g0_e7_prompt_sizes: exit 0: selfcheck prompt_sizes: 15 of 15 OK
g0_e7_playbook_attempts: exit 0: selfcheck playbook_attempts: 34 of 34 OK
g0_e7_assistant_facts: exit 0: selfcheck assistant: 281 of 281 OK
g0_e7_skill_check: exit 0: selfcheck skill_check: 21 of 21 OK
g0_replay: exit 0: g0_replay: 24 of 24 OK
tests: exit 0: 206 passed in 9.59s
selfcheck: 17 of 17 parts OK; tests exit 0
```
`setup_stream.sh F1 --dry-run`: exit 0, `DRY-RUN setup_stream.sh F1 (nothing is created or written)`, with `GATE FAILED` on the two freeze
gates only (`protocol.md5` and `harness/MD5SUMS` do not exist before the freeze) and `memories gate: no previous stream before F1: nothing
to compare`.

## Outcome: PASSED, 17 of 17 parts; tests 206 passed; no product defect recorded
| Part | What it checks | Result |
|---|---|---|
| `watch_cases` | every constructed case of 18.6 (two related rejections; pending then unrelated; a corrected link; a delayed verdict both ways; a related rejection after `E`; a link and an answering version (B3) on an old rejection after the watch start, r and k unchanged; B1 in three orders; B2; B4's re-added v1 criterion, the subjects fixed at the answer and the cycle; B3's equal microsecond; the superseded rows v-viii; review 3's rows xiii-xv; rows xvi-xviii; W1 and W2 rows ix-xi; the repair migration's row xii (carried watch (ii)); the k values of 8.4; 8.7's zero cases; the held grant on a blocked case, m0-s1 `6c7a`, 14 of 14) and every order O1-O10 of 18.4.1 (O1 a/b/c with A's `K`, O2, O3, O4, O5 at its two moments, O6 both ways, O7 in three places, O8, O9 four ways, O10 with C6's lineage) against the pre-registered state; iteration 3: 8.1's exception the other way, a corrected link unrelating the only related rejection after `D` (warning -> kept, `K` = the link) and before it (warning -> new -> kept at `D`) | 83 of 83 |
| `g1_cases` | `guarantees.py`'s G1 (a)-(f) on 18.4.1's flows with the product's settler played (30 flows in iteration 2, 36 in iteration 3, and two standalone G1(a) flows): every order O1-O10, protocol 12.1.1's variants (O7 late, O9 re-add / restore / A edited into B's text / nothing / an unrelated add / before R4, memo 5's unrelated answer, O2's variant, O5's variant, an unscripted related rejection) and 7 negative cases (no runtime retire, a retire outside the call with and without the `could not retire` reply, a wrong `restores`, a spurious retire, a `kept` shown with a related rejection, a counter-rule matching the keyword screen); and the per-snapshot comparison (the race rule, pinned and unpinned keys, root's `services` suffix, an unread line); iteration 3: the legal steps into `kept` (retired -> kept by an exempt restore of a client-written text, warning -> kept by a corrected link) and their two negatives, the unread rule (an empty `turn-05.json`, an empty `end.json`, a product traceback, and `unread_snapshots` on constructed `calls.txt` files: exit, empty, invalid JSON, a missing line, the traceback), the `could not retire` reply inside and before its bound, the pinned keys of a never-watched item and of a restored item, and the race rule's 5-s lower margin; iteration 3b (C3, C2, C1): G2(a) on constructed Lena lines (`M3-VERDICT + M3-MARTA + L-MIND` with one note FAIL, with two notes on the two cases PASS, with two notes on one case FAIL; `VR-REJECT@2026-10-19` with L-MIND PASS; two VR-REJECTs with one note FAIL and two PASS; a bare VR-REJECT NOT DETERMINED; `M3-VERDICT + L-ASIS` an accept, PASS with no note; the rules parsed as a list) and G2(b)'s `late_detail` | 342 of 342 |
| `kept_mail` | G0 m1-s1..s3 and E7 s1..s3 with a constructed item A (`WHY R1; C`) and A' (`WHY C`): state, k, clean, waiting, related, pending, `judged(c)` per candidate, superseded deliveries before it, `E`, `D`, `K`, against `harness/selfcheck/p1-kept-mail-expected.json` (written by hand from section 3 before the first run; unchanged in iterations 2 and 3); iteration 3: the D14 ledger's completeness on G0 m1-s1..s3 (3 cases each; a ledger without one lists it in `missing_cases`, a bogus entry in `extra_cases`) | 135 of 135 |
| `p1_scoring` | `score_memos.py --memos 6`: the keys written as memos score perfect in each owner form; the negative cases (full names under initials, JD without the marker, JD under N, a wrong Due, an extra row); both private keys match the frozen tables; iteration 3: no regression's parts (the keys pass; no Summary under L-ASIS and an owner form are reported, not a FAIL; a wrong Due in a final memo, one wrong-date delivered version and a memo never delivered fail) | 22 of 22 |
| `aggregate_check` | `aggregate.py` on 15 constructed six-stream scenarios (23 in iteration 3b): all pass; a judged value false; `judged.json` missing; a keyword hit undecided and decided; an invalid stream with and without `before_failure`; D14 over (reported); a D8 wrong date in arm F (reported, not the exit); `validity.json` missing; the mechanical memo check failing; the ledger missing a case and its completeness never checked (NOT DETERMINED); an arm-F regression caused in a shared mechanism (a product finding); a Summary kept out under L-ASIS (reported): the four exit lines, the exit line, four reported lines and the causes list; iteration 3b (C1, C7): 8 more scenarios, a stream ended by ruling (b) at turn 22 with memos 5-6 undelivered and R5 unanswered (no regression ND, G2 ND, exit ND), its variant with memo 5's rejected version delivered (ND), the same files without the ruling (FAIL), four FAILs that stand after a ruling (a delivered version's wrong date, memo 4's final memo, R4 before memo 5's request, R5 created before the ruling turn), an invalid stream with `no_regression` FAIL before the failure; and 6 refusals (`before_failure` keys `no regression` and `G1(b)`, the value `fail`, an `ended_by_ruling` with no file, a non-numeric turn, another stream's file) | 236 of 236 |
| `cost_total` | protocol 11's stream credits on G0's six `cost.txt`: 71.99, 63.69, 71.41, 62.98, 71.45, 63.49 = G0's published totals (G0 `STUDY.md`); runs without a matched session (2 of 42 estimated and flagged, 42 of 42 no figure, none unchanged); `> 185.00`: 185.00 not over, 185.01 over (a flagged line too), a missing line refused | 13 of 13 |
| `next_stream` | `next_stream.sh` on 15 constructed evidence trees: the order, stage 2 refused without the gate and the manager's yes, a stage-1 stream over 185 left to the gate, 185.00 and 185.01 in stage 2, the cost decision, a missing `credits.txt`, `memories.db` changed with and without the manager's decision, a replacement's place, a stage-2 replacement over 185, two replacements in one arm; iteration 3: the memories gate between streams (`memories_gate.py`: the first stream, unchanged, changed: exit 4, changed with the decision, a replacement against the stream it replaces, the stream after a replacement, the latest stream before) and its place in `setup_stream.sh` (after the gates, before the stream folder, the sandbox and the profile) | 23 of 23 |
| `empty_calls` | the session-store empty-argument count (f-g0-7 section 1) on G0's six streams: 15, 19, 16, 0, 0, 0 | 6 of 6 |
| `probe_check` | `probe_compare.py` on constructed probe sessions: another load order or split, an extra tool loaded (PASS); a different description, a failed empty call, a failed positive control, a different non-`[tool]` stderr line (STOP) | 6 of 6 |
| `g0_e7_*` (7) | G0's module self-checks on E7, with G0's unchanged expectation files: rederive 372, score_memos 334, ambiguity_recall 59, prompt_sizes 15, playbook_attempts 34, assistant 281, skill_check 21: **G0's published counts exactly** (G0 `SELFCHECK.md`) | 7 of 7 modules |
| `g0_replay` | G0's published per-stream outputs of its M1 streams (`measures/*.json`, `rederived/rederived.json`) reproduced by the P1 copies (score_memos in its G0 mode), and G2 = PASS on each | 24 of 24 |
| `tests` | G0's module tests (`harness/tests/`, the driver and aggregate tests left out with G0's M0 drivers and aggregate) | 206 passed |
Final line: `selfcheck: 17 of 17 parts OK; tests exit 0`.

**What it shows.** The re-derivation follows sections 3 and 8 and B1-B4 on every case 18.6 names and on every order of 18.4.1; its `judged(c)`, `D`
and `K` behave on the flows the study will see (superseded first deliveries, a blocked rework, an L-ASIS accept); the mechanical layer that
turns the files into verdicts (G1's table, the aggregation, the stream credits, the stop rule's walk, the probe's comparison, the empty-call
count) gives the pre-registered verdicts on constructed inputs, including the vacuous branches and the negative cases; the M1-treatment parts
of the harness are G0's, unchanged in effect. **What it cannot show:** a product defect of the watch. The kept mail predates Phase 1 (its
`quality --json` has no `watch`), so the product's `watch` keys and root's `services` suffix are compared with the re-derivation only in the
streams (G1(f), after every turn). The `services` parser is written from design 14.3's wording; a line it cannot read is reported
(`SERVICES-UNREAD`), never guessed (protocol 12.1 G1(f)).

**Product defects recorded: none.** No mismatch of the self-check, in any iteration, was a product defect against the design.

## First runs (before any freeze): each mismatch, its cause and the fix
Every expectation was written from the design before the code ran. No mismatch was a product defect, and no expectation was moved to match an
output.

**Iteration 1: six mismatches, four errors in the self-check's own cases or expectations (1, 2, 3, 5) and two harness bugs (4; 6 in two parts).**
1. `watch_cases` B4 (row xxiii): the case first answered with the initials text, which therefore got the next free id C10, while the case's
   checks named C11. Case-construction error (ids are by role, protocol 4.1): the case now takes the id from the contract versions.
2. `watch_cases` row x: the restored client-written text cited nothing, so no rejection could relate to it (refs, section 3); the row presumes a
   text with refs. Case-construction error: v1's text now cites C6 and the rejections are linked to C6.
3. `watch_cases` row xxv: the expectation gave C6 no lineage after the third answer; section 3's lineage as of t takes the latest version that
   added C6's text (the second answer), which removed the initials id. Transcription error of the expectation, corrected to the definition (each
   lineage is finite, each id once, which is what row xxv asks).
4. `kept_mail`: the constructed A's live-from took the first human rework of any case after R1's answer; 18.4.1's A is live from **memo 1's**
   rework run. Harness bug, fixed (the rework is memo 1's case's).
5. `p1_scoring`: memo 5 under form N was listed among the "perfect" memos, against the key ("under N no form of JD's cell is right": the contract
   gap); removed from that list (the explicit contract-gap check stays).
6. `g0_replay`: (a) `score_memos`' `source_files` names the answer key's path, P1's copy (the same bytes, md5 `2fb69bbe...`): normalized in the
   comparison; (b) `guarantees.py` read rule ids inside the parentheses of G0's free-form `lena-lines.txt` (m1-s3 turn 7 mentions "her own H6
   words"), so it saw a second rejection turn: harness bug, fixed (ids are read outside parentheses and quotes; P1's lines carry bare ids).

**Iteration 2 (after `prereg-review.md`): five mismatches, three errors in the new checks' own cases (8, 10, 11) and two harness bugs (7, 9).**

7. `tests`: 7 of G0's `test_extract_mechanical.py` tests failed when the stream-credits line (H1) was appended to `cost.txt`: they compare
   `cost.txt` with E7's byte for byte. Harness bug (the change broke a G0 invariant): `cost.txt` is G0's again and the figure goes to its own
   `credits.txt` (`cost_total.py`, protocol 11).
8. `g1_cases`: G1(c) FAILed on O8, O9 restore and O9 "A edited into B's text": `watch_cases.py`'s builder wrote `admitted: b` for a gated edit
   or restore citing one R and one C id, which 6.2 admits as (c). Case-construction error, fixed in the builder (`b` only with two R ids).
9. `g1_cases`: O9 "A edited into B's text": both `guarantees.expected` and the check expected the carrier `retired`; 8.5's retire puts back the
   text the item had before its watch, so A, which had its own kept text, ends `restored`. Harness bug, with the check's expectation transcribed
   wrong the same way: both corrected to 8.5 (protocol 12.1.1 row B2).
10. `aggregate_check`: three scenarios named "I2: ..." shared one folder, so a later scenario read an earlier one's `judged.json`.
    Case-construction error: one folder per scenario.
11. `g1_cases` comparisons: the "another state in the `services` listing" check used `new`, the state the item had at the snapshot's start,
    which the race rule rightly matched. Case-construction error: the check now names a related id no candidate time has, and the race match
    is a check of its own.

**Iteration 3 (after the iteration-2 `prereg-review.md`, under `manager-decision-prereg-loop.md`): one mismatch, a harness bug (12).**

12. `g1_cases`, while constructing P2-M1's `warning -> kept` flow (a scratch run of the flow, before its checks were written and run): after a
    corrected link unrelated the only related rejection after `D`, the re-derivation gave the item `new` with `K` undefined for good, where
    section 3 defines `K` as "the earliest record ... at or after `D` such that the files created up to and including it derive `kept`" (the
    link itself) and 8.1's exception allows `warning -> new` or `-> kept`. Harness bug in `rederive_watch.py:Derivation.k_time`: its search
    stopped at the first record from `D` on at which the item had a related rejection. Fixed to section 3's text (every record from `D` on is
    tested; a warned item fails the kept test at each, so B1's "never defined for a warned item" still holds); `watch_cases.py` gains the two
    rows, written from 8.1 and section 3 (after `D`: warning, warning, kept at the link, `K` = the link; before `D`: warning, new, kept at
    `D`), and every earlier case gives the result it gave before (83 of 83; the kept mail 135 of 135; G0's module counts exact). Every other
    check added in iteration 3 passed on its first run.

**Iteration 3b (the manager's amendments C1-C8, `manager-decision-prereg-loop.md`): no mismatch.** Every check added for C1 (8 aggregate
scenarios and `late_detail`), C3 and C2 (the G2(a) cases on constructed Lena lines) and C7 (the refusals) was written from the decision and
the iteration-3 review's fix text before the code ran, and passed on its first run; every earlier check gives the result it gave before
(`g0_replay`: G2 = PASS on G0's kept lines under the new G2(a)). No product defect: no check of this iteration reads the product.
