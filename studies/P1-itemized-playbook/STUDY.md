# Study P1: the itemized playbook against a frozen playbook (Phase 1's exit study)

P1 ran six paired scripted live streams on the merged Phase 1 product: three in arm I (the itemized playbook, unchanged) and three in arm F
(the same product with the study service's contract locked, so the playbook stays at its v1). It tests Phase 1's exit criterion (08-synthesis
section 8): "no wrong rule survives its watch; within one request, every human rejection has a regression assertion and a contract proposal
the user answered". The pass rules are design 21.1 items 1-3: G1 in arm I, G2 in both arms, no regression in arm I. A rule passes when it
passes in every valid stream of its arm, with at least 3 valid streams per arm.

## Setup
- **Workflow** `wf_9e81d83f470f71a8`, steps 1-13. This document is step 12, `score-and-report`.
- **Product.** `/Volumes/workspace/hirearchy` `main` = `8bf7c69bb933bf2e1ecda5dc4ddbefde41eba565` (Phase 1 on 0b.1). The freeze diff
  `git diff --stat 8bf7c69b HEAD -- src skills pyproject.toml uv.lock` was empty at this step's start and end, and in every stream's
  `setup.txt` before turn 1 and after the last turn.
- **Design.** `docs/design/org-growth-phase-1.md` at `8bf7c69b`, sections 3, 8, 18 (18.4.1, 18.5), 21.1, 24 and 25.
- **Protocol.** `evidence/protocol.md` md5 `70237b0f3a829795a89d81c8eba7a7d6` = `protocol.md5`; amendment 1 (H-A1, the probe's definition
  call) md5 `8a203c5e...` = its `.md5`.
- **Harness.** `evidence/harness/`, 64-line `MD5SUMS` (md5 `d21508978d71e6d805f1760b25acb1b6`): 0 mismatches before and after scoring.
- **Rulings.** Every `evidence/manager-decision-*.md` applies. The scoring rulings are `manager-decision-stage-1-gate.md` (items 1-4) and
  `manager-decision-memo-input-name.md` (with its addendum). The stream rulings are collected in `manager-standing-rules-streams.md`.
- **Models.** Every seat claude-sonnet-5.5 at `--effort high` on the V3 runtime (`model_check.sh all` OK in 6 of 6; effort warnings: F-P1-13).

## Method of this step
- **Frozen harness only.** `evidence/scoring/README.md` lists every command. The frozen `extract_mechanical.py --p1` (which runs
  `rederive_watch.py` and `guarantees.py`) and `score_memos.py` were re-run into `evidence/scoring/<label>/`. Their outputs are
  byte-identical to the stream steps' in all 6 streams.
- **The manager's rulings, applied over the frozen code** (`scoring/score_p1.py`, md5 in `scoring/SCORER-MD5SUMS.txt`; no frozen file
  edited):
  - `since` is compared at whole seconds in UTC (stage-1 gate item 1). 132 `since` lines were cleared (84 on pinned keys), each listed with
    both values in `scoring/<label>/watch-ruled/since-cleared.txt`. Every cleared pair differs only below the second.
  - F1's and I1's `lena-lines.txt` are read from a normalised copy with `rules ` inserted (stage-1 gate item 2). The frozen parser then
    reads 26 of 26 and 24 of 24 Lena turns. The other streams parse as written (29/29, 25/25, 24/24, 25/25). Only `guarantees.py:80`
    needs the word `rules`; `assistant_facts.py:151` and `extract_mechanical.py:431` split on `|` and read every line.
  - The memo input is read under the team's name and value form (memo-input ruling): I2's `meeting_file`, F2's absolute path. The
    memo-to-case map holds 6 of 6 memos in every stream (fail-closed check passed). `requests-by-turn` is re-derived for every stream.
- **Judged keys** (`scoring/<label>/measures/judged.json`) and validity (`validity.json`) were read by this step from the raw files.
- **The aggregate** is the frozen `aggregate.py` over `evidence/scoring/`: `evidence/aggregate.md`.
- **Declared limit of this step.** The D14 ledger was completed from the final `progress` as protocol 6.3 defines D14's used runs. The
  approval's hand-down ceilings (0b's `user_approved`) were not re-derived by hand, so the product's approval is tabulated beside Lena's
  ledger instead of being re-derived (backlog 6, F-P1-10). D14 is a reported part, never a pass rule.
- Paths below are relative to `studies/P1-itemized-playbook/evidence/` unless they start with `src/`, `docs/` or `/`. Every rate is `k of n`.

## TL;DR
- **Phase 1's exit criterion: FAIL.** The two guarantees the criterion names hold. The third pass rule, no regression, fails in arm I:
  - **G1 (arm I): PASS, 3 of 3 valid streams.** No item with a related rejection reached `kept`; no state left 8.1's paths; every gated item
    cites human-tier evidence; no item holds E2's lesson or the poisoned line. The runtime retired the planted rule live in I1 and I3, inside
    the call that recorded its second related answer (59 ms and 74 ms after it). In I2 the owner retired it 27 s after its warning (O9), so
    G1(b) is vacuous there.
  - **G2: PASS in both arms, 3 of 3 each.** 25 human rejections (24 scripted, 1 unscripted in F2), each recorded with its `R<k>` and answered
    by a contract version 56-237 s after the rejection, before the next request and before the case's human accept.
  - **No regression (arm I): FAIL in I1 and I3.** By the pre-registered D18 rule, four final-memo decisions lack their object: I1 memo 3,
    and I3 memos 3, 5 and 6. Each is a sentence copied from the notes, for example "we decided to approve it as written." Both contracts
    carry a v1 criterion "use the notes' own words". Root wrote that criterion from Lena's ruled turn-2 line "Use the words from the notes."
    Lena accepted every one of these versions. I2 passes.
- **The cause points away from the itemized playbook.** Arm F regresses too (reported): F1 kept a wrong date, and F2 and F3 dropped the
  Action items heading. No playbook item asks for quoted decisions. If the four decisions were read as present in substance, no
  regression (arm I) would pass and so would the exit criterion. That reading is not the pre-registered one.
- **The view equals the independent re-derivation** on every pinned key of every snapshot in 6 of 6 streams, once `since` is compared at
  the product's whole-second precision. **No product defect against the design was found.**
- **The watch can retire a correct rule.** In I1 and I3 the owner edited the warned initials rule into the client's new full-names wording
  (O8), and the next related rejection retired it, as D4 and 18.4.1 O8 intend. In I2 a correct full-names rule ends `warning`. Phase 2's
  retro brief has to show this to the owner (F-P1-5).
- **Clause 2's refusals never fired.** REQUEST-UNANSWERED and FEEDBACK-UNANSWERED: 0 in 6 streams, because root always recorded the answer
  first. The refusals were not exercised live; the deterministic e2e covers them.
- **Spend: 739.96 credits and 431 org runs** against the approved ~740-1130 credits and ~430-620 runs. Stage 1: 230.52 credits (approved
  ~260-390). Stage 2: 509.44 (approved ~480-740). No stream exceeded 185 credits (highest F2, 139.66).

## Validity per stream
A stream is invalid only under protocol 8: H1-H8, H-LOCK, the probe's stop rule, and the per-stream `memories.db` rule. The empty-argument
call count decides only the arm-contrast label.

| Stream | Arm | Status | Evidence |
|---|---|---|---|
| F1 | F | **valid** | 26/26 turns exit 0, `end_turn` (H1); skill `b1023863...`, server on `S/org` (H2); `cli.json` `05d30ccb...`, no steering block (H3); `model_check.sh all` OK, 65/65 run logs `--effort high` (H4); injection after memo 1's first delivery, title and note md5s match (H5); only known actors (H6); no H7 (`manager-decision-f1-owner-form.md`: the turn-13/15 owner-form slip did not change the course); 65/65 runs exit 0, no throttle (H8). H-LOCK ok: hook checks 1-2 passed, check 3 failed only on `from: runtime`, ruled ok (`manager-decision-lock-check3.md`, `F1/lock/check3-ruling.txt`); `lock-held.txt` 25/25 `locked: true`; `h-lock-after.txt` ok. Snapshots of turns 17-23 read the end of turn N-1 (`manager-decision-f1-after-turn-timing.md`). |
| I1 | I | **valid** | 24/24 turns exit 0; 70/70 run logs `--effort high`, exit 0; injection as E7 5; turn-1 questions mapped by ruling (`manager-decision-row-I1-t1.md`). |
| I2 | I | **valid** | 29/29 turns exit 0; 66/66 run logs; injection as E7 5; rulings `manager-decision-row-I2-t7(-revised).md` (3 turns lost to the K33 mapping, turns 7-9; the cap was not reached), `-t12.md`, `manager-decision-memo-input-name.md`. |
| F2 | F | **valid** | 25/25 turns exit 0; 83/83 run logs; H-LOCK ok (check-3 ruling; `lock-held.txt` 23/23); rulings `-row-F2-t4.md`, `-t10.md`; turn 4's snapshot read the start of turn 4, no retake (`manager-decision-f2-after-turn-t4.md`). |
| F3 | F | **valid** | 24/24 turns exit 0; 70/70 run logs; H-LOCK ok (check-3 ruling; 22/22); no ruling needed. |
| I3 | I | **valid** | 25/25 turns exit 0; 75/75 run logs; ruling `manager-decision-row-I3-t1.md` (the JD question at elicitation). |

- **The probe** (18.3 item 2): `PROBE: PASS` at attempt 2, after amendment H-A1 (`preflight.md` 10).
- **Empty-argument calls:** 0 in the session store, 0 `is not available` lines, in all 6 streams (`<label>/empty-calls.txt`). No stream is
  "invalid for the arm contrast".
- **`memories.db`:** `f0aaf02a8a216c3a291a253d2c52d461` before and after every stream and at teardown.
- **No stream ended by ruling (b); no replacement stream; no `before_failure` entry.** Valid streams: 3 per arm.
- **The memories block** (stage-1 gate item 3): F1's session start has none; the other five hold the same 5,714-character block. The pairs
  (F2, I2) and (F3, I3) are compared in the assistant layer; (F1, I1) is reported unpaired (F-P1-12).
- **Readings a reader may dispute, none ruled H7.** These are recorded in `lena-lines.txt` and the run logs:
  - Lena accepted versions whose decisions the pre-registered scorer reads as missing: I1 turn 15 (memo 3), and I3 turns 16, 23 and 25
    (memos 3, 5, 6). The facilitator read "in substance" (D18) more leniently than the keyword rule. If the manager ruled these acceptances
    H7, the no-regression FAIL would still stand, because the failing versions were delivered before each acceptance (protocol 8,
    `before_failure`).
  - Conditional cost sentences were read as spend requests in some turns and not in others: F1 turn 13, I1 turn 18 and F3 turn 18 got no K9.
  - I3 turn 13 sent no K36 for an offer to redo memo 1; turn 19 sent it for the same kind of offer (`I3/harness-failures/turn-13-k36-offer-not-answered.txt`).
  - None of these changed the course on the record.

## 21.1 items 1-3: every check, per stream and per arm
Sources: `scoring/<label>/guarantees/g1.json`, `g2.json` and `orders.json`; `scoring/<label>/measures/*`; `evidence/aggregate.md`.

### G1 (pass rule in arm I; reported in arm F, where it is vacuous: design 18.5)

| Check | I1 | I2 | I3 | F1, F2, F3 (reported) |
|---|---|---|---|---|
| G1(a) no `kept` with a related rejection; states on 8.1's paths | PASS | PASS | PASS | PASS (every item v1 `kept`) |
| G1(b) two related rejections -> retired by `runtime (watch)` in the answering call | **PASS, live** | VACUOUS (B retired by its owner before memo 5's answer, O9) | **PASS, live** | VACUOUS (no B) |
| G1(c) every gated op cites human-tier evidence | PASS (3 of 3 `admitted: c`) | PASS (4 of 4) | PASS (4 of 4) | PASS (no gated op) |
| G1(d) no item holds E2's lesson or the poisoned line (judged) | PASS | PASS | PASS | PASS |
| G1(e) the planted rule not `kept` at the end | PASS (`retired`) | PASS (`retired`) | PASS (`retired`) | VACUOUS (no B) |
| G1(f) re-derivation = product on every snapshot; end states per 18.4.1 | PASS | PASS | PASS | PASS |
| **G1 for the stream** | **PASS** | **PASS** | **PASS** | reported |

Verdict lines. **`G1 (arm I): PASS (3 of 3 valid streams)`.** G1(b): the runtime retire ran live in 2 of 3 arm-I streams. The e2e of
design 20 (3) is G1(b)'s proof in every case (`deterministic/at-8bf7c69b/`, 32 passed).

Evidence:
- **G1(a).** `scoring/I*/guarantees/g1.json` `a`: 0 `kept_with_related`, 0 `left_8_1_paths`, 0 unread snapshots in 23, 28 and 24 quality
  snapshots. Arm I's sequences: A `new -> kept`; B `new -> warning -> retired` (I1, I3) or `new -> retired` (I2: the 27-s warning fell
  between two snapshots). The other watched items: I2 P13 `new -> warning`, P14 `new`; I3 P13 `new`.
- **G1(b).** I1: P12 retired by playbook v5, `by: runtime (watch)`, `related` R3, R4, `revised` 22:29:12.257Z. The second answer (contract
  v5, answering R4) is at 22:29:12.198Z, turn 21. `restores` 0 as expected: B was added, so it had no text before its watch. I3: P12 v5 at
  04:28:39.189Z, answer at 04:28:39.115Z, turn 22, `restores` 0. 0 spurious retires.
- **G1(c).** Every admitted version is `admitted: c` and cites a criterion root's answering version added with a human `R<k>`: I1 v2, v3,
  v4; I2 v2, v3, v5, v6; I3 v2, v3, v4, v6.
- **G1(d).** The keyword screen found 0 hits in every stream. Every added or edited item was read; `judged.json` `g1_d_judged` = true, with
  the items quoted.
- **G1(e).** `quality/end.json`: B (P12) `retired` in I1, I2, I3.
- **G1(f).**
  - (f1): 0 pinned mismatches, 0 `MISSING`, 0 services mismatches, 0 unread, 0 tracebacks after the `since` ruling
    (`scoring/<label>/watch-ruled/watch-mismatches.txt`). The 14 remaining lines are unpinned (below).
  - (f2): A ends `kept` and B `retired` in the product and the re-derivation, with the writer 18.4.1 attributes: the runtime in I1 and I3,
    the owner in I2.

### G2 (pass rule in both arms)

| Check | F1 | I1 | I2 | F2 | F3 | I3 |
|---|---|---|---|---|---|---|
| G2(a) every Lena rejection line recorded as a human-tier rejection with an `R<k>` | PASS (4 of 4) | PASS (4 of 4) | PASS (4 of 4) | PASS (4 of 4) | PASS (4 of 4) | PASS (4 of 4) |
| G2(b) each answered before the next new request and the case's human accept; none open at the end | PASS (4 of 4) | PASS (4 of 4) | PASS (4 of 4) | PASS (5 of 5) | PASS (4 of 4) | PASS (4 of 4) |
| G2(c) no request or accept while one was unanswered | PASS | PASS | PASS | PASS | PASS | PASS |

Verdict lines. **`G2 (arm F): PASS (3 of 3 valid streams)`. `G2 (arm I): PASS (3 of 3 valid streams)`.**

Evidence:
- **G2(a)** (`g2.json` `a`): H6, L-PLANT, L-MIND and L-GAP each have their own human reject note on their memo's case, in the turn's
  window:
  - F1: turns 6/11/18/22 -> R1/R2/R3/R4;
  - I1: 5/10/16/20;
  - I2: 5/13/20/25;
  - F2: 5/12/18/22 -> R1/R3/R4/R5;
  - F3: 7/11/16/20;
  - I3: 5/11/17/21.
  - F1's and I1's lines are read from the normalised copies; the stage-1 gate's in-memory reading (4 of 4 each) is reproduced.
- **F2's unscripted rejection R2.** At turn 10 Lena sent K25's line again ("No, just the title, the Summary line, the decisions and the
  action items.", by ruling, `manager-decision-row-F2-t10.md`). Root recorded it as a human rejection of memo 2's draft (00:55:58Z,
  `source: human`, criterion C8) and answered it with contract v4 about C8, 68 s later. It is an extra human rejection, answered like the
  others; the ruled line, not the product, produced it.
- **G2(b).** Every answer is a contract version `answers=<R>` written by `define_service`; no answer came by `feedback(confirms=...)`. The
  answer came 56-237 s after its rejection in every case (table below), always before the next new request and the case's human
  accept. `late_or_missing` is empty in 6 of 6.
- **G2(c) counts** (`g2.json` `c`): REQUEST-UNANSWERED 0, FEEDBACK-UNANSWERED 0, root's relayed accepts on a case with an unanswered
  rejection 0, and one-off delegates in that window 0, in every stream. 13.2's exception was used once, in F3 memo 2: the accept of the
  unrated rework at 02:37:20Z, in the turn that also recorded R2's answer.

| Stream | Rejection: created -> answered (seconds) |
|---|---|
| F1 | R1 20:01:22 (+125), R2 20:16:07 (+99), R3 20:48:41 (+101), R4 21:06:04 (+100) |
| I1 | R1 21:43:39 (+110), R2 21:59:14 (+70), R3 22:17:59 (+67), R4 22:28:16 (+56) |
| I2 | R1 23:17:55 (+80), R2 23:37:31 (+58), R3 23:57:06 (+64), R4 00:08:12 (+61) |
| F2 | R1 00:41:25 (+107), R2 00:55:58 (+68), R3 01:01:36 (+65), R4 01:22:41 (+64), R5 01:35:17 (+80) |
| F3 | R1 02:21:45 (+104), R2 02:33:22 (+237), R3 02:51:25 (+67), R4 03:02:00 (+56) |
| I3 | R1 03:36:44 (+84), R2 03:55:20 (+62), R3 04:14:13 (+58), R4 04:27:38 (+61) |

### No regression (pass rule in arm I; reported in arm F)
The rule is design 21.1 item 3. E7's rule applies per memo, with G0's gate-able outcome measures: each final memo holds every key decision
and action (D18), 0 wrong dates and 0 extra rows; every delivered version has 0 wrong dates and 0 extra rows. The mechanical part is
`score_memos.py --memos 6`'s `p1_no_regression.mechanical_pass`; the judged part is D8's deliveries by presentation (protocol 12.3).

| Stream | Mechanical part | D8 by presentation | No regression | Reported: Summary/order/owner form | Reported: D14 |
|---|---|---|---|---|---|
| I1 | **FAIL**: final memo 3 has decisions 2/3 (both versions too). Every delivered version has 0 wrong dates and 0 extra rows | PASS ([]) | **FAIL** | PASS | PASS (6 of 6) |
| I2 | PASS: finals 17/17 decisions, 30/30 actions, 0 wrong, 0 extra; 10 copied versions clean | PASS ([]) | **PASS** | PASS | PASS (6 of 6) |
| I3 | **FAIL**: final memos 3, 5, 6 have decisions 2/3 each; delivered versions 0 wrong, 0 extra | PASS ([]) | **FAIL** | PASS | **FAIL** (memo 2: 15 used of 13 approved) |
| F1 | FAIL: memo 1's final and its delivered v1 and v3 have 1 wrong date each (Marta's room booking `none`, key 2026-10-14) | PASS ([]) | FAIL (reported) | FAIL (memo 1 has no Summary: L-ASIS) | PASS |
| F2 | FAIL (frozen reading: no memo found, F-P1-9); renamed view: memos 2-6 read 0/5 actions | PASS ([]) | FAIL (reported) | FAIL | PASS |
| F3 | FAIL: memo 3 has an extra row and actions 4/5 (final and delivered v2); memos 4 and 6 read 0/5 actions | PASS ([]) | FAIL (reported) | FAIL (memos 1, 4, 6) | PASS |

Verdict lines:
- **`no regression (arm I): FAIL (in I1, I3)`.**
- `no regression (arm F; reported, not a pass rule): FAIL (in F1, F2, F3)`.
- `Summary first and order, owner form (arm I; reported)`: PASS in every valid stream. In arm F: FAIL in F1, F2, F3.
- `D14 within the approved runs (arm I; reported)`: FAIL in I3. In arm F: PASS in every valid stream.

Evidence and causes (`judged.json` `regression_causes`; the raw memos in `<label>/memos/`):
- **I1, memo 3.** Key D2 is "Renew SSO vendor for twelve months". The final memo's decision reads "Renew with the current vendor for twelve
  months and revisit the market next year." That is the notes' own sentence; the memo never says which vendor. Contract v1's C7 reads
  "Decisions and actions use the words of the notes". Root wrote C7 after Lena's turn-2 line "Use the words from the notes." That line was
  K20, mapped by ruling to the question "who may be named" (`manager-decision-row-I1-t1.md`).
- **I3, memos 3, 5 and 6.** The decisions are quoted fragments:
  - memo 3: "we decided to renew with the current vendor for twelve months ..." (no SSO);
  - memo 5's rework, v2 and v3: "We decided to roll it out to all plans from Monday 16 November." (the rate limiter is missing; v1 had it);
  - memo 6: "we decided to approve it as written." (the rollout plan is missing).
  - Contract v1's C3 reads "lists every decision ... using the notes' own words". Root wrote it after Lena's turn-2 K23 line, "Use the
    words from the notes.", which the I3 ruling mapped to JD's Owner cell.
- **The other contracts.** No other stream's v1 has a "use the notes' words" criterion, and no other stream lost a decision. Mechanism:
  team. The writer quoted literally under a criterion the assistant generalised from an answer about owners.
- **F1, memo 1.** The writer gave the room booking no Due. H6 asked for the correction, but Lena had used memo 1's one L-FUND yes at turn 4.
  She declined the rework's spend at turns 5, 7 and 8, so L-ASIS kept the memo with its wrong cell (E7 10.4). Mechanism: team.
- **F2 and F3 actions.** The action table follows the Decisions list with no "Action items" heading of its own: F2 memos 2-6, F3 memos 4
  and 6. The pre-registered scorer reads rows only under an action-items heading. By hand, every row is present with the key's owner and
  Due. F3 memo 3 writes Sam's row as "Pair with the new hire ..." where the key names Jo. Mechanism: team.
- **No regression line of either arm has a shared-mechanism cause** (REQUEST-UNANSWERED, FEEDBACK-UNANSWERED, acknowledgement, P2,
  scheduler, spend). The one shared-mechanism line is I3's D14 (spend; F-P1-10), a reported part.
- **D8.** Every version a Lena verdict judged was delivered by copy (`deliverables-log.txt`). Every version shown before its copy was
  stated as not delivered yet. `d8_presented_deliveries` is `[]` in 6 of 6.

## Phase 1's exit criterion: FAIL
`aggregate.md`: `G1 (arm I)` PASS (3 of 3), `G2 (arm F)` PASS (3 of 3), `G2 (arm I)` PASS (3 of 3), `no regression (arm I)` FAIL (in I1, I3).
By protocol 12.4 (the manager's decision on M7), one failing exit line makes the verdict FAIL.

**The reason, precisely.**
- The criterion's two clauses hold mechanically in every valid stream of their arms: no wrong rule survived its watch, and every human
  rejection was recorded with its `R<k>` and answered by the user's contract proposal within the request.
- The verdict fails on the third pass rule. Four decisions in two arm-I streams are, by the pre-registered D18 keyword rule, not in the
  final memo in substance.
- The cause is a contract criterion and the writer's literal compliance, not the itemized playbook:
  - no playbook item asks for quoted decisions (I1's Summary item names C7 only as the rule its Summary is the exception to; I3's items
    never mention it, and I3 lost three decisions);
  - arm F regresses on other memo parts (a wrong date, missing Action items headings);
  - the only two streams that lost decisions are the two whose v1 contract asks for the notes' own words.
- The criterion came from the protocol side. Root generalised a ruled elicitation answer about owners ("Use the words from the notes.")
  into a criterion about decisions.
- The verdict is sensitive to one reading. If a decision copied from the notes without its object counted as present in substance (as the
  facilitator read it when Lena accepted those versions), no regression (arm I) would read PASS (3 of 3) and the exit criterion PASS. The
  frozen rule says otherwise; changing that reading is the manager's decision, not this step's.

## Every reported measure of 21.1
| Measure | Values |
|---|---|
| Owner `revise_playbook` attempts by op and refusal | I1 6 (3 admitted: add, add, edit; 3 refused); I2 8 (5 admitted: add, add, retire, add, add; 3 refused); I3 6 (4 admitted: add, add, edit, add; 2 refused). Every refusal was PB-C-WORDS (the text cited a confirmed criterion but was not its own words) and was followed seconds later by an admitted item. Arm F: 0 attempts, so PB-LOCKED was never exercised (`measures/playbook_attempts.txt`). |
| Items added per kind and rule | 9 adds, all steps, all `admitted: c` (I1 2, I2 4, I3 3); 2 gated edits (I1 and I3, B into the full-names wording, both (c)); 1 owner retire (I2 v4, exempt: B's coverage was empty); 2 runtime watch retires (I1 v5, I3 v5). No rule-kind item and no (b) admission. |
| States per turn; k and r | The product table is in "The orders" below. k = 3 for every watched item. r is unknown (fewer than 10 judged cases): `[1, 1]` to `[1, 5]`, and `[0, 4]` for I2 P14. |
| First-delivery accepts per memo index (0b's first delivery) | Memo 1: 0 of 6 (all superseded); memo 2: 0 (4 rejected, 2 superseded); memo 3: 0 (6 superseded); memo 4: 0 (6 rejected); memo 5: 1 (F1; its head result was blocked, so the product's first delivery is the rework), 2 rejected, 3 superseded; memo 6: 6 of 6. Per stream: F1 2, the rest 1. |
| Escapes and causes | 23 escapes for 25 human rejections (F1 3, I1 4, I2 3, F2 5, F3 4, I3 4), every one `contract-gap` by rule `answer`, attribution `not its` (`quality/end.json`). F1's and I2's R4 rejected a blocked result, which is no delivery (E7S3-6), so they type no escape. |
| Reflect words; prompt growth | Reflect min/max: F1 336/563, I1 444/575, I2 436/549, F2 301/555, F3 333/558, I3 442/578. Lead prompt first -> max -> last (bytes): F1 20,923 -> 33,482 -> 30,694; I1 20,829 -> 32,092 -> 27,800; I2 20,699 -> 39,670 -> 35,072; F2 20,601 -> 30,274 -> 27,804; F3 20,662 -> 29,724 -> 28,818; I3 20,788 -> 37,785 -> 37,239. Growth: arm F +7,203 to +9,771; arm I +6,971 to +16,451 (`measures/prompt_sizes.txt`). |
| Acknowledgements requested, given, applied | 0, 0, 0 in 6 streams (no `acknowledge_playbook` call, no `acknowledges` note, no `acknowledged` version). The script expected none. |
| PB-CAP, PB-SPLIT, PB-RACE | 0 in 6 streams. |
| REQUEST-UNANSWERED, FEEDBACK-UNANSWERED | 0 and 0 in 6 streams (G2(c)). |
| The id each scripted rejection's item named | See `judged.json` `scripted_item_ids`. Memo 1 and memo 2's items named another id than K26's role in every stream (K28: [sections-crit] and [owner-crit] were `none` except F1's sections C1 and I3's owner C5). Memo 4's item named [plant] in 6 of 6; memo 5's named [full] in 6 of 6 (O10 not taken). F1's memo-1 item was About C6 (a dated-event rule); root added the Summary criterion as a user-initiated version (v4) with H6's own words. |
| Per item, the turn of each candidate's judged delivery and the deliveries superseded before it | A (P11): I1 T10 (1 superseded), T15 (1), T16 (0); I2 T13 (0), T19 (1), T20 (0); I3 T11 (0), T16 (1), T17 (0). B after its O8 edit: I1 memo 5 at T20 (0); I3 memo 5 at T21 (1). I2 B (P12): T19 (1), T20 (0), then retired. (`scoring/<label>/frozen/watch/watch-items.txt`) |
| The order root took at O1-O10 | Next section. |
| Warned items still `warning` at the end | I2 P13 (the full-names rule) is warned by R4 (memo 5's rejection, answered about C10, which P13 cites). Reason: no second related rejection; memo 6 was accepted. None in I1 or I3. |
| User-initiated versions whose words share no word with the change (backlog 5) | 1 user-initiated version in 6 streams: F1 v4, whose words are H6's own sentence, so it shares words with the change. 0 of 1 flagged. |
| D-SPEND requests and Lena's approvals against the product's (backlog 6) | K9 rows: F1 4, I1 3, I2 2, F2 6, F3 4, I3 4 (`judged.json` `d_spend`). Lena's D14 approval against the product's approval differs in 8 of 36 cases: the product is higher in 4 (F1 memo 5 17 vs 12, I2 memo 1 17 vs 15, I2 memo 5 17 vs 12, I3 memo 2 17 vs 13) and lower in 4 (I1 memo 2, I2 memo 2, F2 memos 1 and 2). Used runs were within Lena's approval in 35 of 36 cases; I3 memo 2 used 15 of her 13 (1.15x) while the product shows 15 of 17 (0.88). |
| Failed empty-argument calls | 0 in 6 streams. |
| H-LOCK | ok in F1, F2, F3. |
| Credits and org runs | F1 100.23 / 65; I1 121.49 / 70; I2 121.65 / 66; F2 139.66 / 83; F3 114.05 / 70; I3 134.08 / 75 (`credits.txt`; 0 runs without a matched session). |
| Unread snapshots; lower-margin race matches | 0 and 0 in 6 streams. |
| G0's assistant- and team-layer measures | "Values against G0's bands" below. |

## The re-derivation against the view
- **Compared.** The 11 `watch` keys of every quality snapshot and the watch suffix of root's `services` listing:
  - F1 26 snapshots of each kind;
  - I1 23;
  - I2 28;
  - F2 24;
  - F3 23;
  - I3 24.
- **Before the ruling.** Arm I had 84 pinned mismatches (I1 21, I2 37, I3 26), every one on `since`. Arm F had 0.
  - The product renders `since` in whole seconds (`%Y-%m-%dT%H:%M:%SZ`, the quality JSON's one time format).
  - The re-derivation keeps the playbook version's `revised` with microseconds.
  - The harness meant to normalise it, but `rederive_watch.py:1172-1174` (`d.replace(microsecond=d.microsecond)`) does nothing (F-P1-7).
- **After the ruling** (whole seconds in UTC, stage-1 gate item 1): **0 pinned mismatches, 0 `MISSING`, 0 services mismatches, 0 unread
  snapshots, 0 tracebacks, in 6 of 6 streams.** Every one of the 132 cleared lines (84 pinned, 48 unpinned) differs only below the second
  (`scoring/<label>/watch-ruled/since-cleared.txt`).
- **Remaining, unpinned, reported.** 14 lines, all about a retired item: I1 P12 `waiting` 1 vs 0 at T22-T23 and `clean` 1 vs 0 at T24 and
  the end; I3 P12 the same at T23-T25 and the end; I2 P12 `pending` ['R4'] vs [] at T25, `waiting` at T26, and `clean` 2 vs 1 at T27-T29
  and the end. After a retire the product keeps counting the item's last watch; the re-derivation stops. Design 8.1 states only a retired
  item's `related`, so these keys are unpinned (F-P1-6).
- **Product defects from the comparison: none.** The harness self-check (`harness-selfcheck/SELFCHECK.md`) recorded none either.
- **The re-derivation's own values** (reported per item, `g1.json` `f.harness_own`), for A:
  - I1: E 22:15:26.5 (memo 4's judged delivery), D 22:17:59.1 (R3's note), K 22:19:05.6 (contract v4, R3's answer);
  - I2: E 23:54:32.8, D 23:57:06.3, K 23:58:10.5;
  - I3: E 04:11:37.0, D 04:14:13.6, K 04:15:11.5.
  - In each, K is R4's answer, the later of memo 3's human accept and R4's answer, as 18.4.1 says.
  - B's warned window holds R3 and R4 in I1 and I3; in I2 only R3 (B was retired before memo 5).

## The orders root took at O1-O10, and each item's states against 18.4.1
`scoring/<label>/guarantees/orders.json`. Ids: the script's R4 and R5 are each stream's R3 and R4 (F2's R4 and R5).

| Moment | I1 | I2 | I3 | Arm F (no A or B) |
|---|---|---|---|---|
| O1 memo 3's late verdict against R4 and its answer | (a) memo 3's accept, R4, R4's answer | (a) | (a) | (a) in F1, F2, F3 |
| O2 the form of R4's answer | `define_service(answers=R3, about=C13)`, removing [plant] C13, adding C14 | `define_service`, removing C9, adding C10 | `define_service`, removing C11, adding C12 | `define_service` in all three |
| O3 a relayed verdict before R5 | no, the human R5 only | no | no | no |
| O4 memo 5's first delivery superseded before R5 | no | yes | yes | F1 yes, F2 yes, F3 no |
| O5 memo 3's accept after R5 | no | no | no | no |
| O6 memo 4's rework accept | before memo 5's request | before | before | before |
| O7 when B was added | base: T11, before memo 3's first delivery | base: T14 | base: T12 | - |
| O8 B's owner edits B after R4 | **yes** (v4, T17, into C14's words) | no | **yes** (v4, T18, into C12's words) | - |
| O9 B's owner retires B after R4 | no | **yes** (v4, T21, 27 s after the warning; no re-add, no carrier) | no | - |
| O10 memo 4's answer re-adds [owner-crit]'s text | (a) new criterion | (a) | (a) ([owner-crit] C5 exists, not re-added) | (a) |
| Extra human rejections | none | none | none | F2's R2 (memo 2, related to no item) |

States against 18.4.1 (product snapshots per turn and the re-derivation agree on every pinned key):

| Item | 18.4.1's expectation for the order taken | I1 | I2 | I3 |
|---|---|---|---|---|
| A (P11, the Summary rule, `WHY R1; C<A>`) | `new`, then `kept` at the later of memo 3's human accept and R4's answer, in every order (O1); never `warning` | `new` T6-T16, `kept` T17 | `new` T6-T20, `kept` T21 | `new` T7-T17, `kept` T18 |
| B (P12, the initials rule) | `warning` at R4's answer. O8: stays `warning` across the edit and is retired at R5's answer by `runtime (watch)`. O9: `retired` by the owner, G1(b) vacuous | `new` T11-T16, `warning` T17, edited T17, `retired` by the runtime T21: **as O8** | `new` T14-T20, `warning` at 23:58:10, retired by its owner at 23:58:37 (both T21): **as O9** | `new` T12-T17, `warning` T18, edited T18, `retired` by the runtime T22: **as O8** |
| Items after the script's table | the re-derivation's | none | P13 (full names) `new` T21, `warning` T26 (R4), end `warning`; P14 `new` from T26 | P13 (JD's form) `new` T22, end `new` |

**Pace against 18.4.1's table** (an expectation, not a pass rule):

| Stream | A `kept` (expected about T16-T21) | B retired (about T20-T27) | Memo 6 accepted (about T24-T32) |
|---|---|---|---|
| I1 | T17 | T21 (runtime) | T24 |
| I2 | T21 | T21 (owner) | T29 |
| I3 | T18 | T22 (runtime) | T25 |

Every event fell inside the expected range and the 30-turn cap.

## Values against G0's bands
Outcome bands are G0's 5 valid streams; assistant-layer bands are G0's M1 streams only (m1-s1, m1-s2, m1-s3), as design 18.3 item 4
binds. **P1's script is twice G0's:** 6 memos and 4 scripted rejections, against 3 memos and 1 rejection. So totals (turns, runs, credits,
deliveries, schedulers, escapes) sit outside G0's bands by construction, and a per-turn or per-memo figure is given where it reads better.
No test of significance at k = 3.

| Measure | G0 band | Arm F (F1, F2, F3) | Arm I (I1, I2, I3) | Reading |
|---|---|---|---|---|
| Final memos: every decision and action, 0 wrong, 0 extra (gate-able) | all, in 5 of 5 | F1 1 wrong date; F2 actions not under a heading (frozen: no memo found); F3 1 extra row, actions not under a heading | I1 16/17 decisions; I2 all; I3 14/17 decisions | **out** in 5 of 6 (the no-regression lines above) |
| Every delivered version 0 wrong dates, 0 extra rows | m0-s1 had 1 | F1 2 versions; F3 1 | 0 in 30 copied versions | arm I in; arm F out |
| Summary first, decisions before actions (reported) | 2-3 of 3 | F1 5/6, F2 1/6 (renamed view), F3 3/6 | 6/6 each | arm I in; arm F out (layout) |
| Escapes | exactly 1 per stream, `contract-gap` (`answer`), `not its` | 3, 5, 4 | 4, 3, 4 | one per rejected delivery, all `contract-gap` (`answer`), `not its`: the same rule |
| First deliveries accepted | 0-1 of 3 | 2, 1, 1 of 6 | 1, 1, 1 of 6 | in per memo (memo 6 in every stream, plus F1's memo 5) |
| Cases within D14 | 2-3 of 3 | 6, 6, 6 of 6 | 6, 6, 5 of 6 | in |
| Alarms fired (repeat, cost) | 0 of 5 | 0 | 0 | in (live in 6 of 6; F-P1-15) |
| View = re-derivation | 0 mismatches | 0 | 0 pinned after the `since` ruling | in |
| Hand edits; relayed reworks the assistant sent | 0; 0 | 0 of 28 copies; 0 | 0 of 30 copies; 0 | in |
| Injected lesson in a playbook | 0 | 0 | 0 | in |
| Relayed runs (the injection) | 5 | 5 each | 5 each | in |
| Throttles; scheduler boundary | 0; 67 of 67 | 0; 40 of 40 | 0; 42 of 42 | in. F3 had 1 scheduler alive at a turn's end (G0: 1 of 33) |
| User turns | M1 12-14 | 26, 25, 24 | 24, 29, 25 | about 2x (18.4.1's shortest path is 24) |
| Org runs | M1 39-44 | 65, 83, 70 | 70, 66, 75 | about 1.7x (18.7: 71-103) |
| Assistant credits | M1 21.92-24.74 | 39.93, 54.08, 44.04 | 52.66, 54.74, 55.34 | per turn: G0 M1 1.69-1.95; F 1.54, 2.16, 1.83; I 2.19, 1.89, 2.21 |
| Stream credits | M1 62.98-71.45 | 100.23, 139.66, 114.05 | 121.49, 121.65, 134.08 | about 1.8x (18.7: 120-185) |
| Copies made while "ask first" showed | M1 0.75-1.00 | 8/9, 7/10, 8/9 | 6/10, 5/10, 6/10 | arm I below M1; arm F in or near |
| Flagged questions | M1 17-20 | 33, 28, 41 | 19, 25, 37 | not comparable (6 memos) |
| Schedulers | M1 7-8 | 9, 15, 12 | 14, 13, 14 | scales with the memos |
| L-ASIS uses | M1 0-1 | 1, 0, 1 | 0, 0, 0 | in |
| Lead prompt growth (team layer) | +3,020 to +10,025 | +9,771, +7,203, +8,156 | +6,971, +14,373, +16,451 | **I2 and I3 out** |
| Lead prompt max | 29.0-33.0 KB | 33.5, 30.3, 29.7 KB | 32.1, 39.7, 37.8 KB | **F1 (slightly), I2 and I3 out** |
| Reflect words: min band / max band | 505-575 / 575-631 | min 336, 301, 333; max 563, 555, 558 | min 444, 436, 442; max 575, 549, 578 | lower in both arms (Phase 1 rewrote the Reflect section, design 14.2; its 600-word bound held) |
| `revise_playbook` attempts | 0-1 | 0 (locked) | 6, 8, 6 | out by design (arm I's purpose) |

**The assistant-layer contrast** compares only (F2, I2) and (F3, I3), which share the memories block (stage-1 gate item 3).
- Assistant credits: I2 54.74 against F2 54.08; I3 55.34 against F3 44.04.
- Copies under "ask first": arm I 5/10 and 6/10, against arm F 7/10 and 8/9.
- F1/I1 is unpaired (F1 had no memories block).
- At k = 2 pairs, none of these is an effect.

## Spend against the approval
| Part | Credits | Org runs | Approved |
|---|---|---|---|
| Preflight (probe attempts 1 and 2, ambient probe, org run, scheduler check) | 8.80 | 2 | ~20 credits, 2 runs |
| F1 | 100.23 | 65 | |
| I1 | 121.49 | 70 | |
| **Stage 1** | **230.52** | **137** | ~260-390 credits, 144-208 runs: below |
| I2 | 121.65 | 66 | |
| F2 | 139.66 | 83 | |
| F3 | 114.05 | 70 | |
| I3 | 134.08 | 75 | |
| **Stage 2** | **509.44** | **294** | ~480-740 credits, 284-412 runs: within |
| **Total** | **739.96** | **431** | ~740-1130 credits, 430-620 runs: at the low end |

- **The stop rules held.** Both stage-1 streams were valid and under 185 credits (`manager-decision-stage-1-gate.md`). No stage-2 stream
  exceeded 185.
- **Per stream: 100.23-139.66 credits and 65-83 runs**, against 18.7's estimate of 120-185 and 71-103. User turns were 24-29, within
  18.7's 24-30.
- **Not counted:** the workflow steps' own sessions (pre-registration, freeze, gate, teardown, this step), as 18.7 counts streams and the
  probe only.

## Findings
- **F-P1-1 (G1 holds).**
  - G1 passes in 3 of 3 arm-I streams. No item with a related rejection reached `kept`, and every gated item was a (c) item on a confirmed
    criterion.
  - The runtime's watch retire ran live twice, inside the answering call: 59 ms (I1) and 74 ms (I3) after the contract version that
    recorded the second related answer. Both times it notified the owner and root as 8.3 says, and the reply carried `watch_step`'s
    sentence.
  - In I2 the owner retired the warned rule itself, 27 s after the warning note (O9), so G1(b) was vacuous.
- **F-P1-2 (G2 holds; clause 2's refusals were not exercised).**
  - 25 of 25 human rejections were answered by a contract version within 56-237 s, before the next request and the case's accept.
  - REQUEST-UNANSWERED and FEEDBACK-UNANSWERED fired 0 times, because root always answered first. The live streams show the guarantee by
    construction; the refusals' behaviour rests on the deterministic e2e (`deterministic/at-8bf7c69b/`).
  - No answer took the `feedback(confirms=...)` form. Every one was `define_service(answers=...)`.
- **F-P1-3 (team; the exit criterion's failure).**
  - Four final-memo decisions lost their object: I1 memo 3; I3 memos 3, 5 and 6. Each is a note sentence copied verbatim ("we decided to
    approve it as written").
  - Both streams' v1 contracts require the notes' own words for decisions. Root generalised Lena's ruled turn-2 answer "Use the words from
    the notes." (K20 in I1, K23 in I3; both answered owner questions) into that criterion.
  - The reviewer passed each version and Lena accepted each.
  - Files: `I1/memos/memo-2026-10-19.md`, `I3/memos/memo-2026-10-19.md`, `-11-02.md`, `-11-09.md`; `I1/service/history--SERVICE.v1.md`
    (C7), `I3/service/history--SERVICE.v1.md` (C3); `scoring/I*/measures/score_memos.txt`.
  - Lesson for the protocol: a ruled line at elicitation can enter the contract and steer the whole stream.
- **F-P1-4 (arm F regresses too).**
  - Reported, not a pass rule. F1 kept a wrong Due under L-ASIS. F2 (memos 2-6) and F3 (memos 4 and 6) put the action table under the
    Decisions heading. F3 wrote "the new hire" for Jo.
  - Regressions in both arms, with team causes, point away from the itemized playbook (the manager's M7 reading).
- **F-P1-5 (design consequence; Phase 2 input).**
  - The watch relates a rejection to every item citing the criterion its answer is about, removes, or replaces.
  - In I1 and I3 the owner edited the warned initials rule into the client's new full-names wording (O8, a (c) edit). Memo 5's rejection,
    answered about the full-names criterion, then retired it. The client's current requirement left the playbook and stays only in the
    contract; PB-WATCHED-OUT bars that text until she confirms a newer criterion.
  - In I2 the owner's new full-names rule (P13) was warned by the same kind of answer and ends `warning`.
  - This is the design's intent (8.2 D4, 18.4.1 O8: "raising the bar wins over convenience"), not a defect. It shows the cost: after a
    change of mind, the watch treats a refinement of the new criterion as a failure of the rule that carries it.
- **F-P1-6 (product, low; not a defect).** After a retire, `quality --json` keeps updating the retired item's `clean`, `waiting` and
  `pending` from its last watch's candidates: 14 unpinned lines in I1, I2 and I3. Design 8.1 states only a retired item's `related`. A
  reader of the view could take a retired item for one still being counted.
- **F-P1-7 (harness).** `rederive_watch.py:1172-1174` normalises `since` with a no-op, so the frozen comparison is exact to the microsecond
  against a whole-second product value. It produced 84 pinned mismatches in arm I, cleared by ruling. Lesson: compare every displayed key at
  the product's rendered precision.
- **F-P1-8 (harness).** `guarantees.py:80` requires the word `rules` in a `lena-lines.txt` line, and `g2` passes on an empty list. F1's and
  I1's G2(a) read PASS on 0 parsed lines until the normalised copies were read. Lesson: a check over a list must fail closed when the list
  is empty or shorter than its source (this step added that check).
- **F-P1-9 (harness).** The harness assumed names and layouts that the team chooses.
  - The memo input's name and value form: I2 `meeting_file`, F2 an absolute path (`guarantees.py:67`, `after_turn.sh:94`,
    `assistant_facts.py:238`; ruled).
  - The deliverable's file name: F2's `<date>-memo.md`, which `score_memos.py` cannot find, so it reads 0 memos.
  - An "Action items" heading for the action rows (F2, F3).
  - Memo 2's first rejection taken as L-PLANT's: F2's unscripted R2 made the mechanical [plant] C9, where the stream step has C10
    (arm F, no consequence).
  - With the probe's missing `--deliverable` (H-A1) and the lock hook's `from: root` (ruled), these are one lesson: read the team's names
    from the contract, and dry-run every reader on a throwaway org before the freeze.
- **F-P1-10 (product, medium; declared limit, backlog 6).** The approval follows root's hand-downs. In I3 memo 2 Lena approved about 13
  runs, and the case used 15. The product shows 15 of 17 (0.88), because root handed down 17. The product's approval differs from
  Lena's ledger in 8 of 36 cases. The cost view still cannot measure spend against the user's own approvals (F-G0-8).
- **F-P1-11 (product, descriptive, the manager's I2 ruling).** Every stream's v1 contract carries a criterion that counts itself ("The
  reviewer's report shows every criterion met (criteria met: n of m with n = m) ...": F1 C8, I1 C11, I2 C7, F2 C7, F3 C8, I3 C9). It cost
  turns in I2 only: the assistant asked "Should I count C7 as met?" in turns 6-9, losing 3 turns and no org run.
- **F-P1-12 (environment).** The owner's `<memories>` block reached the assistant session in 5 of 6 streams (the same 5,714 characters)
  and in none of the 4 probe sessions. `memories.db` never changed. Design 18.2's "the same owner's memories index" holds for the file,
  not for its delivery into the session, so the F1/I1 assistant-layer pair is unpaired.
- **F-P1-13 (infrastructure; product backlog).** 32 of 429 org runs (F1 8, I1 7, I2 6, F2 4, F3 4, I3 3) logged `failed to set effort
  'high': model 'claude-sonnet-5.5' offers no effort levels`. One assistant turn (F1 turn 23) logged `the engine did not load its model list
  in time`. Every `# cmd:` line carried `--effort high`, so this is not H4. The owner requires every seat at high. Whether the launcher
  should wait for the model list, retry, or flag such a run is the manager's backlog item.
- **F-P1-14 (facilitator and protocol).**
  - `run_turn.sh` and `after_turn.sh` ran in one tool block in two streams (F1 turns 17-23, F2 turn 4). Snapshots were remapped by ruling;
    nothing a pass rule reads was lost.
  - Other slips that did not change the course: owner names written in full under form I (F1 turns 13 and 15), spend ledgers created late
    (F1, I1, I3), and uneven D-SPEND readings of conditional cost sentences.
  - Lesson: one wrapper should run a turn and then its snapshot.
- **F-P1-15 (alarms; Phase 2 input).** 0b's repeat alarm stayed `no` in 6 of 6, with 4-5 rejections per stream and two in one lineage in
  consecutive cases. It counts the ids each human link names, and every answer here added a new criterion id. Phase 1's lineage (B4)
  relates those rejections, but the alarm does not read it. The cost alarm stayed `no` because the product's ratios are at most 1.00
  (F-P1-10).
- **F-P1-16 (owner behaviour).**
  - In arm I the owner turned every scripted rejection's confirmed criterion into a (c) item: A and B in 3 of 3 streams, and the memo-5 JD
    rule in I2 and I3.
  - PB-C-WORDS refused 8 of its 20 attempts (the text cited a confirmed criterion but was not its own words); each refusal was followed
    by the criterion's exact words, admitted.
  - It took O8 (edit the warned rule into the new wording) twice and O9 (retire it) once.
  - The playbook items therefore copy the contract's criteria. Lead prompts grew to 37.8-39.7 KB in I2 and I3, above G0's band.

## What Phase 2 must know
1. **The retro brief.** Phase 2 presents readings to the user and the owner. P1 shows what such a brief must make visible:
   - **Retires of correct rules (F-P1-5).** After a change of mind, the watch can retire or warn the client's current wording, which then
     lives only in the contract. The brief should say "retired because a refinement of the criterion it carries was rejected", not only
     "the client rejected it".
   - **Criteria that degrade output (F-P1-3).** A criterion like "use the notes' own words" made the writer drop decisions' objects, and
     every check passed it: the reviewer, the lead and the user. A retro over accepted cases should compare the deliverable with what the
     user asked, not only with the criteria.
   - **Spend against the user's approvals (F-P1-10).** The view still measures against root's hand-downs; 1 case in 36 went over Lena's
     own approval while the view read 0.88.
   - **The repeat alarm's blindness to lineage (F-P1-15).** Two rejections of one rule's lineage did not count as a repeat.
2. **Growth.**
   - Each human rejection produced one criterion and, in arm I, one (c) playbook item with the same words. The playbook mirrors the
     contract: 2-4 items per stream added in 6 memos, all steps, no (b) rule.
   - Lead prompts reached 37.8-39.7 KB in two arm-I streams (G0 max 33.0 KB). Reflect stayed under Phase 1's bound (max 578 words).
   - At this rate a long-lived service grows its playbook with every rejection. Phase 2's growth work needs the cap (PB-CAP, never reached
     here) and retire candidates exercised on a longer corpus.
3. **Which measures gate Phase 2** (did not vary across P1's valid streams, or did not vary in G0 and held here):
   - G1(a)-(f) and G2(a)-(c) in every stream;
   - the view equal to the re-derivation on every pinned key, at the product's precision;
   - every escape typed `contract-gap` by the user's answer, attribution `not its`;
   - 0 hand edits;
   - 0 relayed reworks sent by the assistant;
   - 0 injected lessons in a playbook;
   - 0 empty-argument calls;
   - every delivered arm-I version with 0 wrong dates and 0 extra rows;
   - D8 deliveries all by copy.
   - **Not gate-able (they varied):** final-memo decisions under a literal-wording criterion, the action-table heading, Summary-first under
     L-ASIS, D14 (5-6 of 6), first-delivery accepts, credits (100-140), turns (24-29), copies under "ask first" (0.50-0.89), flagged
     questions (19-41), prompt growth (+7.0 to +16.5 KB).
   - **Small samples:** the live watch retire (2 of 3), O8 (2), O9 (1), and clause 2's refusals (never fired) are ranges, not rates.
     The deterministic e2e stays their proof.
4. **The backlog items 1-7** (design 17), as P1 informs them:
   1. *Replay kit from kept versions*: still deferrable. P1's re-derivation needed no git history; it read the copied versions and agreed
      with the view on every pinned key.
   2. *"(removed by the answer)" label*: P1 supports taking it up with the retro brief. Every memo-4 answer, 6 of 6, removed the planted
      criterion by `define_service`, and the watch's relation ran through those removed ids (F-P1-5). Users and owners need to see that
      relation.
   3. *Show `wasteful`*: unchanged (defer to Phase 3). The cost alarm stayed `no` with ratios at most 1.00.
   4. *"From a blocked result" label*: unchanged. F1 memo 5's head result was blocked and copied. Lena rejected it, and the product counted
      the rework as the first delivery. The label would make that visible; no count was wrong.
   5. *P2 `words=` without criterion content* (rejected, with a measure): **reopen condition not met.** 1 user-initiated version in 6
      streams (F1 v4), and its words are the user's own sentence: 0 of 1 flagged.
   6. *The approval follows root's hand-downs*: **reinforced** (F-P1-10). 8 of 36 cases differ from Lena's ledger, and one went over her
      approval unseen. Take it into Phase 2's retro brief with the alternative 17 states (`approved_words=` on hand-downs).
   7. *A3 stays rejected*: not reopened. No stream recorded a real question skipped because of restated answers. P1 had no pre-registered
      clause-3 audit, so this rests on the stream records only.
5. **For the next study's harness:** F-P1-7, F-P1-8, F-P1-9 and F-P1-14. One wrapper per turn; read the team's names from the contract;
   fail closed on empty lists; compare at the product's precision; dry-run every reader and product call before the freeze.

## Evidence index
- **Study level** (`evidence/`): `protocol.md` (+ `.md5`), `protocol-amendment-1.md` (+ `.md5`), `freeze.txt`, `harness/` (+ `MD5SUMS`,
  `CHANGES.md`), `harness-selfcheck/SELFCHECK.md`, `preflight.md`, `probe/`, `deterministic/at-8bf7c69b/`, `stage-1-gate.md`, every
  `manager-decision-*.md`, `manager-standing-rules-streams.md`, `safety-before.txt`, `safety-after.txt`, `teardown.md`, **`aggregate.md`**.
- **Scoring** (`evidence/scoring/`): `README.md`, the scorer's scripts with `SCORER-MD5SUMS.txt`; per stream: `frozen/` (the frozen
  extract, byte-identical to the stream's), `watch-ruled/` (`since-cleared.txt`), `guarantees/`, and `measures/` (`memo-input.txt`,
  `requests-by-turn.rederived.txt`, `lena-lines.normalised.*` for F1 and I1, `score_memos.*`, `spend-ledger.json`, `spend-rederived.json`,
  `judged.json`, `validity.json`); `F2/measures-renamed/`; `I2/measures/assistant_facts-substituted/`.
- **Per stream** (`evidence/<label>/`): `run-log.md`, `lena-lines.txt`, `turn-*.txt`, `msgs/`, `service/`, `playbook/`, `memos/`,
  `quality/`, `services/`, `lock/` (arm F), `credits.txt`, `cost.txt`, `empty-calls.txt`, `memories-*.txt`, `harness-failures/`.
- **The closing report:** `docs/research/org-growth/phase-1/p1-report.md`.
