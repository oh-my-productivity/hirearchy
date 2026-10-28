# P1 pre-registration review (step 1b, iteration 3)

Reviewer: `prereg-review` of workflow `wf_9e81d83f470f71a8`. Reviewed fresh against the brief (`docs/research/org-growth/phase-1/p1-study-brief.md`),
the design at `main` = `8bf7c69b` (sections 3, 8, 18.2-18.7 incl. 18.4.1, 21.1, 24, 25, read with `git show 8bf7c69b:`), the manager's binding
directives `evidence/manager-decision-prereg-loop.md` (pass 3), the iteration-2 review, G0 (`STUDY.md` "What Phase 1 must know", the band
table, A1/A2), E7 (protocol 4.7, 4.10, 10.4) and the 0a design 3.4.

Reviewed: `protocol.md` (iteration 3, incl. 17.2), `answer-key-p1.md`, `notes/`, `harness/` (`CHANGES.md`, `rederive_watch.py`, `guarantees.py`,
`aggregate.py`, `cost_total.py`, `memories_gate.py`, `setup_stream.sh`, `next_stream.sh`, `after_turn.sh`, `finish_stream.sh`,
`quality_snapshot.sh`, `services_snapshot.sh`, `run_turn.sh`, `probe.sh`, `profile-template.json`, `score_memos.py:p1_no_regression`,
`p1-judged-template.json`, `spend-ledger-template.json`, `selfcheck.sh`), `harness-selfcheck/` (`SELFCHECK.md` and every `*.out`), and the design
diff. I did not re-run the self-check and ran no product command; one doubt (does `services` exit 0 on an org with no service, or would the
unread rule mark early turns unread?) was settled by the golden `tests/golden/expected/cli/fresh_services.txt` (`[exit 0]`). I did not open
`src/hirearchy/`. Nothing was modified but this file and `prereg-review.json`.

## Verdict: CHANGES_REQUESTED (0 HIGH, 3 MEDIUM, 5 LOW)

Every manager directive is implemented, and every iteration-2 finding (7 MEDIUM, 9 LOW) is resolved (tables below). The re-derivation stays
independent, the self-check passes 17 of 17 parts on the files as they stand, and the safety, the treatment and the cost figures are right.

Three new gaps remain, each on an event the script can produce:
- **P3-M1.** A stream ended by ruling (b), the protocol's own way out of a missing table row, is scored as product FAILs of exit lines.
- **P3-M2.** Memo 3's late verdict leaves the facilitator a choice between M3-VERDICT's three outcomes and L-ASIS.
- **P3-M3.** G2(a) counts one rejection note per Lena turn, so a second rejection in the same line can go unrecorded and G2(a) still passes.

The manager has said this pass closes the loop by decision. The verdict above is still the mechanical one: three MEDIUM findings.

## The manager's directives (checked first)

| Directive | Done? | Evidence |
|---|---|---|
| P2-M1: the reviewer's `g1_a` code; `retired\|restored -> kept` only with an exempt client-written restore between the snapshots; `warning -> kept` only with a corrected link; flows (2 pass, 1 fail) | yes | `guarantees.py:g1_a` and `client_restores_between`; protocol 12.1 G1(a)(ii); `g1_cases.out` lines 268-287 (2 pass, 2 fail). The new flow found a harness bug in `k_time`, fixed to section 3's `K` (13.4 item 12; `watch_cases.out` 2 rows) |
| P2-M2: the unread rule; a traceback through the product is a defect and G1(f) FAILs; other unread snapshots are NOT DETERMINED for G1(a) and G1(f); G1(e) NOT DETERMINED when `end.json` is unread; two cases | yes | `rederive_watch.py:unread_snapshots` (exit, missing, empty, invalid JSON, no `calls.txt` line; `TRACEBACK` + `PRODUCT_FRAME`); `guarantees.py` (`load_stream`, `g1_a`, `g1_e`/`end_unread`, `g1_f`, `state_at_end` reads `end` only); snapshot scripts record `bytes` and `json`; `g1_cases.out` 288-314 (empty `turn-05.json`, empty `end.json`, a product traceback, the rule on constructed `calls.txt`) |
| P2-M3: case entries at the memo's first request; `missing_cases`/`extra_cases` from the mail; a missing case is NOT DETERMINED; an `aggregate_check` scenario | yes | protocol 6.3; `rederive_watch.py:run_spend(..., stream)`; `aggregate.py:d14`; template `_about`; `kept_mail.out` (G0 m1-s1..s3 completeness); `aggregate_check.out` (ledger missing a case; completeness not checked) |
| P2-M4: both sentences | yes | protocol 4.2 ("The owner form of `Also:`", "L-LATER against M3-VERDICT", the two table rows); 16 items 2-3 |
| P2-M5: K35, K36; the post-F1 rule (a)/(b); the warning quotes the question verbatim and names the 2-3 closest rows | yes | protocol 5 (K35, K36, the facilitator rule); 0; 15; 16 item 22. (The scoring of a (b) end is P3-M1.) |
| P2-M6: the gate before anything is created, exit 4 unless `manager-decision-memories-before-<label>.md`; the check case | yes | `memories_gate.py`; `setup_stream.sh` (after the gates and refusals, before `mkdir $STREAM`); `next_stream_check.out` (7 gate cases and its place: gate line 103, exit 106, folder 135, sandbox 146, profile 151) |
| LOWs L2-L9 as written | yes | L2 4.1; L3 `pinned()` and 12.1 G1(f); L4 `RACE_LOWER`, `lower_times`; L5 `results_between`; L6 `load_contracts` raises above v1; L7 16 item 8; L8 `finish_stream.sh` reads `lead=` (which `after_turn.sh` writes into `lock/hook.txt`), `product_watch` matches the owner; L9 13.4 item 11 |
| L1, the conservative option | yes | `cost_total.py:figures` (N x the mean per matched run, flagged; no figure with no matched run); protocol 11; `cost_total.out` 13 of 13 |
| M7 decided: no regression is the pass rule in arm I; arm F reported with each regression line's cause; the gate-able parts only, each other part cited to its G0 line; L7's consequence; 16, 12.3, 12.4 and `aggregate.py` agree; the exit on four lines | yes | protocol 12.3 (G0 item 2 for the gate-able parts; item 1, the band rows "Summary of 3 \| 2-3" and "Cases within D14 \| 2-3 of 3", and item 4 for the reported ones, all checked against G0 `STUDY.md` lines 464, 473, 589, 592, 616), 12.4, 12.5, 16 items 18-19; `score_memos.py:p1_no_regression`; `aggregate.py` (`EXIT_LINES`, `SHARED`, `causes_of`); `p1-judged-template.json` `regression_causes` |
| Re-run `selfcheck.sh` and every check-case script; summary lines in `SELFCHECK.md` | yes | `SELFCHECK.md` (17 of 17 parts, 206 tests); every `*.out` ends OK; the run (UTC 16:33:32-16:33:48) is after the last harness code change (`selfcheck.sh`, 16:25:03; `find harness -newer` the outputs gives nothing) |
| 17.2's resolution table; `CHANGES.md` "Iteration 3" independence; the design diff stays one line; nothing frozen, committed or created | yes | protocol 17.2; `CHANGES.md` lines 9-33 and 112; `git diff` below; no `/tmp/hirearchy-p1-*`, no P1 profile in `~/.kiro/agents`, no `protocol.md5`, `MD5SUMS` or `freeze.txt` |

## Iteration 2's findings: each resolved

| Finding | Resolved? | Where (checked) |
|---|---|---|
| P2-M1 G1(a) failed legal steps into `kept` | yes | as the directive row above |
| P2-M2 unread snapshots | yes | as above |
| P2-M3 the D14 ledger's completeness | yes | as above; D14 is now a reported part (M7) and reads NOT DETERMINED, never PASS, on a missing case |
| P2-M4 Lena's two choices | yes | 4.2 |
| P2-M5 missing rows; no legal resolution after F1 | yes | 5, 0 (a new gap in how a (b) end is scored: P3-M1) |
| P2-M6 `memories.db` between streams | yes | 8, `memories_gate.py`, `setup_stream.sh` |
| P2-M7 no regression's arm | yes | the manager's decision, implemented in 12.3, 12.4, 16 item 18 and `aggregate.py` |
| L1-L9 | yes | as the directive rows above |

## The seven mandatory checks

| # | Check | Result | Findings |
|---|---|---|---|
| 1 | The protocol implements 18 and 21.1 completely; every pass rule and reported measure has a mechanical procedure over named files | **Partly met** | P3-M1, P3-M3; LOW P3-L3, P3-L4 |
| 2 | Memos 4-6 and Lena's lines make 18.4's events happen whatever the team writes; the keys agree with the criteria in force | **Partly met** | P3-M2; LOW P3-L2 |
| 3 | The L-KEEP table covers every question the key settles; no improvisation (F-G0-5) | **Met, with one gap in scoring** | P3-M1; LOW P3-L1, P3-L5 |
| 4 | The re-derivation is independent of the product's source; it follows 3, 8 and B1-B4; its self-check covers 18.6 and O1-O10 and passes | **Met** | none |
| 5 | The arms differ only by the lock; `KIRO_HOME` unset in both; profiles byte-identical but for labels; the probe compares what 18.3 says | **Met** | none |
| 6 | Safety: nothing writes `~/.kiro` (memories included), the user's org or `~/.kiro/skills/`; no credential read or copied | **Met** | none |
| 7 | The stage gate and stop rules are exact; every cost figure traces to 18.7; every open choice is decided with a reason | **Met but for P3-M1's unstated choice** | P3-M1 |
| - | The design diff is exactly the one 21.6 line | **Met** | none |

**Check 1.**
- 12.1-12.5 give each pass rule of 21.1 items 1-3 and each reported measure a procedure over named files, with a verdict line. 21.1's
  reported list maps one to one onto 12.5's rows, the warned-at-end items, the orders O1-O10 and H-LOCK included.
- 12.1.1's table is `guarantees.py:expected`, and `aggregate.py` is not fail-open on any missing file, key or value. Verified in the code:
  `judged()`, `combine()`, `d14()`, `verdict()`.
- Gaps:
  - a (b) end turns the protocol's gap into exit-line FAILs (P3-M1);
  - G2(a) checks one note per turn (P3-M3);
  - two smaller text issues (P3-L3, P3-L4).

**Check 2.**
- **Memo 2's planted rule.** L-PLANT goes on the first delivered version, whatever it contains.
- **Memo 3's late verdict.** L-LATER always comes first, and M3-VERDICT is the first line after it in which `requests-by-turn.txt` says
  `memo 4's request (2026-10-26.md) sent: yes`. `after_turn.sh` writes exactly that string.
- **Memo 4's change of mind.** L-MIND is the design's words.
- **Memo 5.** The notes carry the poisoned line verbatim and `ACTION: JD to send the deck to the customer by Nov 5.`, initials only. L-GAP
  is the design's sentence with "Not right yet." in front (16 item 15).
- **The keys against the notes and the criteria in force.** I re-read every row of memos 4-6:
  - dates and weekdays: 10-26, 11-02 and 11-09 are Mondays, so "by Friday" is 10-30 and 11-13, and "on Wednesday" is 11-04;
  - `none` wherever the notes give no date;
  - implicit commitments are rows; status lines (the SSO renewal signed, Jo's onboarding done, the deck sent) are no rows;
  - D3 of memo 6 is a decision, not an action;
  - the owner forms N, I, N, N+J; under N, JD has no right form (the contract gap).
- **The new `Also:` rule** is deterministic: the form the fixed line sets, and no VR-OWNER sentence.
- Gaps: M3-VERDICT against L-ASIS (P3-M2), and the sentence forms inside `Also:` (P3-L2).

**Check 3.**
- K1-K36 cover every question the key settles for memos 1-6:
  - actions, decisions and non-items: K14-K14d, K15-K17b;
  - Dues: K12, K13;
  - owners by form, and JD before and after L-GAP: K20-K24;
  - extra parts: K25;
  - the scripted items in `question_for`'s form, with `Yes, add it.`: K26;
  - the O10 note: K27;
  - another id named: K28, recorded;
  - the acknowledgement row: K31;
  - the lock: K35;
  - redoing accepted memos: K36.
- L-KEEP is reachable only through K32 and K35 (and K6 for L-BUDGET-Q). E7's "anything else" is not adopted (2.3).
- The facilitator rule leaves no improvisation:
  - every answering line is looked up and its row recorded;
  - a miss stops the step with the question quoted and the closest rows named;
  - after F1's first turn, only a ruling to an existing row or the end of the stream follows, and no line is ever added.
- Gaps:
  - how a (b) end is scored (P3-M1);
  - one foreseeable arm-I question has no row (P3-L1);
  - section 0's wording (P3-L5).

**Check 4.**
- `CHANGES.md` ("Independence", "Iteration 3") states that `src/hirearchy/` was not opened in any iteration, and lists what was read instead.
  Iteration 3 read no product file at all.
- `rederive_watch.py`, `guarantees.py`, `memories_gate.py`, `cost_total.py` and the check scripts import only the stdlib, PyYAML and the
  harness's own modules (checked by `grep` over the imports).
- The two re-derivation changes of iteration 3 follow the design's text:
  - `k_time` now tests every record from `D` on, which is section 3's `K` read literally. A warned item fails the kept test at each record,
    so B1's "never defined for a warned item" holds; only a corrected link that unrelates the related rejection reaches `kept` (8.1's one
    exception; 13.4 item 12).
  - `load_contracts` stops on a version above 1 without `defined` (B3). G0's kept v2 carries `defined`
    (`G0 m1-s1/service/SERVICE.5828ac9.md`), and `kept_mail` passes with the stop in place.
- The recorded self-check covers every 18.6 case (`watch_cases.out`: rows v-viii, xii-xviii, xx-xxv, B3's equal microsecond, the held grant
  on `6c7a`, 8.4's k values, 8.7's zero cases) and every order O1-O10 with its variants, and it passes:
  - `watch_cases` 83 of 83;
  - `g1_cases` 329 of 329;
  - `kept_mail` 135 of 135;
  - `p1_scoring` 22;
  - `aggregate_check` 150;
  - `cost_total` 13;
  - `next_stream` 23;
  - `empty_calls` 6;
  - `probe_check` 6;
  - G0's seven module counts, exact;
  - `g0_replay` 24;
  - 206 tests.
- No product defect is recorded.

**Check 5.**
- `run_turn.sh` and `probe.sh` run every chat as `env -u KIRO_HOME kiro-cli chat --v3 ... --effort high` and take the exit code before
  `; sleep 20`. `setup_stream.sh` (gate 7) and `probe.sh` refuse when `KIRO_HOME` is set.
- `profile-template.json` varies only in `name`, `description` and `ORG_ROOT` (the label and the epoch). `setup.txt` shows the raw diff and
  the masked one.
- Arm F's only difference is the hook. It runs the design's command once, as root, with checks 1-3 (check 2 at the version before + 1);
  `lock-held.txt` is written after every turn and `h-lock-after.txt` at the end.
- The probe compares what 18.3 lists, in the order F-1, I-1, I-2, F-2: the whole `session_start`, `tool_load` per tool by md5, non-`[tool]`
  stderr with digits masked, the session-store empty-call count, and the positive control (`contract v2` against `contract v1`).
- Both arms share the owner's memories index, now gated before every stream (`memories_gate.py`).

**Check 6.**
- The harness's only writes into `~/.kiro` are the study's own `hirearchy-study-p1-*` profiles, each created, compared with `cmp` and
  deleted, with a record.
- `memories.db` is read by `md5 -q` only, before and after every stream and in the new gate.
- The global `SKILL.md` is read by `md5 -q` only. `/Users/aminalizadeh/organization` is read by `ls`, `find` and `stat` in
  `safety-snapshot.sh`.
- No script reads a credential file (a `grep` for credential, keychain, `.aws`, api key and `auth.json` finds nothing).
- kiro-cli's own session and memory writes under the M1 treatment are the design's binding condition (18.2), detected per stream by the
  md5s. No P1 sandbox, profile or freeze file exists.

**Check 7.**
- Protocol 11 states 18.7's figures exactly:
  - stage 1: 20 + 2 x 120-185 = 260-390 credits and 144-208 org runs;
  - stage 2: 4 x 120-185 = 480-740 credits and 284-412 runs;
  - total: 740-1130 credits (central about 920) and 430-620 org runs;
  - per stream: 71-103 runs and 120-185 credits;
  - the probe: about 20 credits and 2 runs.
- **The stop rule is verbatim:** stage 2 only if both stage-1 streams are valid and neither cost more than 185 credits; in stage 2, a stream
  over 185 credits pauses the study. Iteration 3 adds "`memories.db` unchanged during and between them".
- **The mechanics.**
  - "Over 185" is `> 185.00` on `credits.txt`, whose figure gives G0's published 62.98-71.99, and the unmatched runs are added upward.
  - `next_stream.sh` refuses:
    - I2 without `stage-1-gate.md` and `manager-decision-stage-2.md`;
    - a stage-2 stream over 185 without `manager-decision-cost-<label>.md`;
    - any done stream without a credits line;
    - a stream after a change during a stream without the manager's decision;
    - two replacements in one arm.
  - The memories gate refuses a change between streams.
- Replacements are outside 18.7's figures and need the owner's OK.
- Section 16 decides 25 open choices with reasons. The one consequential choice still without a reason is how a (b) end is scored (P3-M1).

## Findings

### P3-M1 (MEDIUM, checks 1, 3 and 7; error handling): a stream ended by ruling (b) is scored as product FAILs of exit lines
- **Where.**
  - `protocol.md`:
    - section 5, (b): "the stream ends at that turn, valid as at a cap (4.2), its open moments read by 12.1.1's 'not reached' rows **and
      12.3's rule for a memo never delivered**";
    - 12.2 G2(b): the last request's rejections must be answered "at the stream's end";
    - 12.3 part 1: "A memo never delivered within the caps fails for that memo".
  - `harness/score_memos.py:p1_no_regression` (`no final memo` -> `pass: False` -> `mechanical_pass: False`).
  - `harness/guarantees.py:g2` (`no answer at the stream's end (the last request, L10)` -> G2(b) FAIL).
  - `harness/aggregate.py` (no notion of a ruling end).
- **Problem.**
  - Ruling (b) ends a stream because the L-KEEP table did not hold a question. That is a gap on the protocol's side, not the product's.
    - The step stops "before Lena's next line", which is typically the moment a scripted rejection's item question is open.
    - It cuts every memo not yet requested or delivered.
  - As written, a (b) end FAILs two exit lines:
    - the memos not yet delivered FAIL no regression's mechanical part (`no regression (arm I)` is an exit line);
    - the rejection whose answer was Lena's withheld line FAILs G2(b), an exit line in both arms.
  - So one missing row can turn Phase 1's exit to FAIL.
  - Neither source supports that:
    - E7 10.4 names "a cap, L-WAIT, or the assistant" as the causes that fail a missing memo. All three are on the product's side.
    - Design 18.4.1's "G2(b)'s end-of-stream check reads its open rejections" is about the cap.
  - The manager's directive fixes the stream's validity ("valid as at a cap"). It does not say the cut parts are product failures.
    - The iteration-2 fix read the open moments by 12.1.1's "not reached" rows only.
    - "12.3's rule for a memo never delivered" is this iteration's addition, and no reason is given (check 7).
  - The asymmetry also pushes every ruling toward (a), even when no row fits. A forced mapping is exactly F-G0-5's failure.
- **Fix.** This keeps the directive's "valid as at a cap"; it only defines how the cut parts are scored. If the manager meant "scored
  exactly as a cap" as well, this finding is a disagreement with the directive, to be ruled on.
  - Replace "and 12.3's rule for a memo never delivered" in section 5 (b) with:

    > The parts the end cut are not scored. A memo with no delivered version by that turn reads NOT DETERMINED (ended by ruling at turn
    > `<n>`) for no regression. A human rejection created in the stopped turn's window, whose answer was the withheld Lena line, reads
    > NOT DETERMINED for G2(b)'s end-of-stream part. A FAIL on what was delivered or recorded before stands. Reason: the end is the
    > protocol's, not the product's; E7 10.4's causes for a missing memo are a cap, L-WAIT and the assistant.

  - Record the ruling in `measures/validity.json` as `"ended_by_ruling": {"turn": n, "file": "manager-decision-row-<label>-t<n>.md"}`.
  - Make `aggregate.py` read it:
    - `no regression` is NOT DETERMINED when `mechanical_pass` is false only through `per_memo[...].final is None` for memos after the
      ruling;
    - G2 is NOT DETERMINED when `g2.json` (b) fails only on `no answer at the stream's end` lines for rejections created at or after that
      turn's start.
  - Add one `aggregate_check.py` scenario: an arm-I stream ended by ruling at memo 5, with memos 5-6 undelivered and R5 unanswered. It must
    read no regression ND, G2 ND and the exit ND, never FAIL.

### P3-M2 (MEDIUM, check 2): memo 3's late verdict leaves a choice between M3-VERDICT's three outcomes and L-ASIS, and does not say which version it judges
- **Where.** `protocol.md` 4.2:
  - the M3-VERDICT row ("recorded with one of three ids: M3-ACCEPT ..., M3-MARTA ..., VR-REJECT ...");
  - the L-ASIS paragraph ("stays, with the same conditions ... nothing after memo 3, whose next request L-LATER already made");
  - the verdict-rule paragraph;
  - K34.
- **Problem.**
  1. **L-ASIS against M3-VERDICT.**
     - E7 4.10's L-ASIS replaces the verdict-rule rejection of memo m when Lena has said "No more spend, please deliver as is." for memo m
       and the assistant returns control with memo m's version delivered, or with no delivery and no question. The protocol keeps it
       "with the same conditions" and already writes its next-memo request for memo 3, so L-ASIS on memo 3 is contemplated.
     - G0 recorded 0-2 memo-3 spend requests per stream ("What Phase 1 must know" item 1), so a declined memo-3 spend before the verdict
       is plausible.
     - At M3-VERDICT's turn, both rows can then hold, and they lead to different scripts:
       - **L-ASIS** is an accept: memo 3 is judged accepted, and A's third candidate is clean.
       - **M3-MARTA or VR-REJECT** is a human rejection: an extra rejection in A's and B's windows (12.1.1 rows A3/B4), an answer due
         before memo 5's request, and a rework the user just declined to fund.
     - This is F-G0-5's class: the facilitator choosing between readings.
  2. **Which version.** "memo 3's version" is not defined when the team delivered another version of memo 3 between L-LATER and
     M3-VERDICT, for example a rework root started on the reviewer's finding.
- **Fix.** Add to 4.2, under "L-LATER against M3-VERDICT":

  > M3-VERDICT judges the latest version of memo 3 delivered (D8) before that Lena line. When Lena said "No more spend, please deliver as
  > is." for memo 3 before that line and that version differs from the key, M3-VERDICT is `About the 2026-10-19 memo: ` + L-ASIS (its
  > sentences, no next-memo request), recorded `M3-VERDICT + L-ASIS` (an accept, not a rejection). Otherwise it is M3-ACCEPT, M3-MARTA or
  > VR-REJECT, as now. Reason: E7 4.10's exception holds for every memo's verdict, and a rework she declined to fund would add an unscripted
  > rejection.

  Deciding the opposite (L-ASIS never at M3-VERDICT) is also acceptable, with its reason. What matters is one rule, in 4.2 and 16 item 3.

### P3-M3 (MEDIUM, check 1): G2(a) checks one rejection note per Lena turn, so a second rejection in the same line can go unrecorded and G2(a) still passes
- **Where.**
  - `protocol.md` 12.2 G2(a): "for every Lena turn whose rules hold one of them, a human-tier reject note ... with its `R<k>`".
  - `harness/guarantees.py:g2`: one row per turn, if `cands` is non-empty. The note's case is not checked.
  - `guarantees.py:lena_turns`: `rules` is a set, so two VR-REJECTs collapse into one.
- **Problem.**
  - E7's composition rule puts "the verdict sentence(s)" first in one Lena line, and P1's script makes two-rejection lines reachable:
    - M3-VERDICT (M3-MARTA or VR-REJECT) together with L-MIND, when memo 4's first version is delivered in the turn after L-LATER;
    - memo 4's rework (VR-REJECT) together with L-GAP, since O6 lets memo 5's request go out after R4's answer, before memo 4's rework is
      accepted;
    - memo 5's rework together with memo 6's first version.
  - If root records only one of the two, `g2` finds one note in the window and passes G2(a). 21.1 G2(a) requires that "every Lena rejection
    line is recorded as a human-tier rejection with an `R<k>`".
  - G2(b) cannot catch it either, because it reads only rejections that were recorded. This is a fail-open in a pass rule of both arms.
- **Fix.**
  - In 12.2 G2(a), write:

    > For every rejection in a Lena turn (each of H6, L-PLANT, L-MIND, L-GAP, M3-MARTA, and each VR-REJECT with the memo it judges), a
    > distinct human-tier reject note on that memo's case (the head task's `notes_file`), created after the turn's start and before the
    > next rejection turn's start.

  - In `lena-lines.txt`, write each VR-REJECT with its memo (`VR-REJECT@<memo date>`), and parse the rules as a list.
  - In `g2`, map H6, L-PLANT, M3-MARTA, L-MIND and L-GAP to memos 1, 2, 3, 4 and 5. Then require, for each (rule, memo) pair, one note `v`
    with `mail.case_of(v.task) == memo_case[memo]`, each note used once.
  - Add two constructed cases:
    - a turn `M3-VERDICT + M3-MARTA + L-MIND` with one note: G2(a) FAIL;
    - the same turn with two notes on the two cases: G2(a) PASS.

### P3-L1 (LOW, check 3): one foreseeable arm-I question has no row: whether the team should retire the warned rule
- **Where.** `protocol.md` 5. K31 covers an acknowledgement for an item that covers a criterion still in the contract. K32 and K35 give
  `Keep it as it is.`
- **Problem.**
  - After R4's answer, root's reply carries the watch's sentence: "Rejection R4 is related to playbook item P<k> ...: P<k> is in warning
    now ...; one more related rejection retires it". Root may then ask Lena whether the team should drop that initials rule now.
  - B has no coverage by then, so K31 does not apply. A ruling under (a) could only map the question to "Keep it as it is." That steers the
    owner's choice, which 18.4 wants reported, not scripted (O9).
- **Fix.** Add K37, before the freeze: "whether the team should retire, keep or change one of its playbook items, outside an
  acknowledgement (K31)" -> `That's up to the team.` (16: 18.4 reports the owner's choice; the user takes no side.)

### P3-L2 (LOW, check 2): the sentence forms inside `Also:` are not defined
- **Where.** `protocol.md` 4.2: "`[ Also: ...]` carries the verdict-rule sentences for anything else wrong in that version".
- **Problem.**
  - E7's verdict-rule sentences include "Not right yet, something is missing." and Marta's "Almost, but not right yet: ...".
  - Inside `Also:`, it is open whether they keep the "Not right yet" part. The two choices give different verbatim lines.
- **Fix.** State that the `Also:` sentences are L-ASIS's forms (E7 4.10: "without 'Not right yet'"): `something is missing.`,
  `<Owner>'s due should be <value>.`, `'Marta keeps the agenda as sent' isn't an action item.`, `'<Action>' isn't an action item.`,
  `it should start with the one-line Summary, then the decisions, then the action items.`, in table order.

### P3-L3 (LOW, check 1): 12.3 restates E7's rule as "a memo not delivered and judged fails", but its procedure fails only a memo never delivered
- **Where.** `protocol.md` 12.3, first paragraph, against part 1 and `score_memos.py:p1_no_regression` ("no final memo").
- **Problem.**
  - The two texts disagree on a memo delivered but not judged: the case of memo 6 when the cap cuts its accept, design 18.4.1's slowest pace.
  - The procedure's narrowing matches 18.4.1's "costs only that memo's descriptive accept count", but no reason is written.
- **Fix.** In 12.3 write:

  > A memo delivered but not judged when a cap ends the stream is scored on its final memo (D16), not failed (design 18.4.1: the cap's cut
  > of memo 6's accept "costs only that memo's descriptive accept count"); E7 10.4's "delivered and judged" is narrowed to "delivered" for
  > that reason.

  Add the same sentence to 16.

### P3-L4 (LOW, check 1): `validity.json`'s `before_failure` keys are not named
- **Where.** `protocol.md` 8 (`"before_failure": {rule: "FAIL"}`); `aggregate.py:verdict` reads exactly `G1`, `G2` and `no_regression`.
- **Problem.** A scorer who writes `no regression` or `G1(b)` is silently ignored, and a FAIL before an invalidating failure is then lost.
- **Fix.** In 8, write `"before_failure": {"G1"|"G2"|"no_regression": "FAIL"}`. Have `aggregate.py` reject any other key with an error.

### P3-L5 (LOW, check 3): section 0 says a missing row is resolved "never by a new line", while section 5 allows one by amendment before F1's first turn
- **Where.** `protocol.md` 0 (the last sentence of "Amendments"); 5 ("Before F1's first turn the manager's ruling may add a line by
  amendment").
- **Fix.** In 0, write "after F1's first turn, never by a new line".

## Verified assumptions
- **The design diff.** `git diff docs/design/org-growth-phase-1.md` is exactly one added line under 21.6, the brief's text byte for byte.
  HEAD is `8bf7c69b`, and the product-freeze diff is empty.
- **The pins** (recomputed):
  - E7's protocol `0acc2b41...` = E7's `protocol.md5` = the copy;
  - G0's protocol `08cccd64...`;
  - G0's `MD5SUMS` `be213479...`;
  - `inject_root_rework.py` `1c4e7824...`;
  - `answer-key.md` `2fb69bbe...`;
  - E7's notes `903e3bbf`, `3893bd63` and `9976a765`;
  - P1's notes `78cd76ed`, `93240174` and `f9f8b424`;
  - `answer-key-p1.md` `d340ff63`;
  - `script/e7-turn-files/s1` equals E7's `s1/prompts`.
- **The self-check's timing.** The recorded run (16:33:32-16:33:48 UTC) postdates every harness code file; only `CHANGES.md` is newer.
- **The G0 citations in 12.3 and 16 items 8 and 19:**
  - item 2's "final memos 8/8 decisions, 15/15 actions, 0 wrong dates, 0 extra rows";
  - item 1's "Summary-first: 2-3 of 3 (whether L-ASIS was used)";
  - the band rows "Summary of 3 | 2-3" and "Cases within D14 | 2-3 of 3";
  - item 4's "That reading decided D14 in two streams (F-G0-8)".
- **`R<k>`** is the k-th human-tier rejection (0a 3.4), as `Mail.rid` builds it.
- **`hirearchy services` exits 0 on an org with no service** (golden `cli/fresh_services.txt`), so the unread rule does not mark the turns
  before `apply_org` unread.
- **The lock record.** `after_turn.sh` writes `lead=<lead>` into `lock/hook.txt`, which `finish_stream.sh`'s L8 fix reads.
- **The memories gate** compares with the latest stream before the label in F1, I1, I2, F2, F3, I3, with approved replacements in place. It
  runs after the gates and refusals and before `mkdir $STREAM`. `next_stream.sh` greps `CHANGED` for the during-stream case, which only
  `finish_stream.sh` writes.
- **The stream credits.** `cost_total.py` sums `total runs` lines that G0's `cost.txt` has once per window, so the mean per matched run is
  not diluted.
- **`aggregate.py`** decides the exit on `G1 (arm I)`, `G2 (arm F)`, `G2 (arm I)` and `no regression (arm I)`. Every missing input reads
  NOT DETERMINED.
- **Nothing exists yet:** no sandbox, profile, `protocol.md5`, `MD5SUMS` or `freeze.txt`, and no `src/` file is newer than the brief.

## Unverified or wrong assumptions
- **Wrong:** that ending a stream by ruling (b) is neutral for the verdict. As written it FAILs no regression for undelivered memos and
  G2(b) for a rejection Lena had not yet answered (P3-M1).
- **Wrong:** that G2(a) checks "every Lena rejection line". It checks one note per turn (P3-M3).
- **Unverified:** the product's `watch` keys and root's `services` suffix in a live Phase 1 org. The kept mail predates Phase 1, so only the
  streams (G1(f)) show them. That includes the product's state after a corrected link that unrelates a warned item's only related
  rejection, which iteration 3's `k_time` reads as `kept` at the link (13.4 item 12). The script has no corrected link, so this is unlikely
  to arise.
- **Unverified:** that the owner's quiet note from the lock lands under `<lead>/inbox|read/`, and that the lock's v2 carries `defined` at
  `8bf7c69b`. G0's product wrote it on v2. Without it, `load_contracts` stops, and `guarantees.py` with it, so arm F's `g2.json` would be
  missing (G2 (arm F) NOT DETERMINED). Recommendation for the preflight: check `defined:` on the probe's arm-F `SERVICE.md` v2 beside the
  hook's three checks.
- **Unverified (by design):** the author's statement that `src/hirearchy/` was not opened. The code shows no product import and no product
  rule text, which is all that can be checked from outside.
