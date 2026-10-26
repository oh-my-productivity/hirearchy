# Study G0: the noise baseline of Phase 0b

G0 ran E7's committed script six times on the merged product and measures how much the results vary, so that later studies can tell a change from noise. **It has no pass rule.** It reports values and their spread, and its report closes Phase 0b together with 0b's deterministic replays.

## Setup
- **Workflow.** `wf_c415acfac4f09f84`, steps 1-11. This document is step 10, aggregate and report.
- **Product.** `/Volumes/workspace/hirearchy` `main` = `3c841bb9cdde666c6ea8b00bb2edfeae68c256db` (0a through 0a.5, plus 0b).
  - This step checked HEAD and the empty freeze diff `git diff --stat 3c841bb9 HEAD -- src skills pyproject.toml uv.lock` at its start and before writing.
  - Every stream's `setup.txt` records both before turn 1 and after its last turn.
- **Protocol.** `evidence/protocol.md`, md5 `08cccd6458f5f418b4d388cb93d633b5` = `protocol.md5`. It pins E7's protocol by md5 `0acc2b41...`.
- **Harness.** `evidence/harness/`; its 48-line `MD5SUMS` has md5 `be21347995b821185a2adaba36d8390c`. This step re-checked both the protocol and the harness against the freeze before acting: no MISMATCH.
- **Decisions.** Two manager decisions apply: `manager-decision-selfcheck.md` and `manager-decision-m0-s2-validity.md`.
- **Models.** Every seat is claude-sonnet-5.5 at effort `high`.

## Method of this step
- **The aggregation.** `evidence/baseline.md` is written by the frozen `harness/aggregate.py`. The section "Notes of the aggregation step" in that file records what was added after generation.
- **The judged measures.** These are the 31 keys of `harness/judged-template.json` plus a text note.
  - Six read-only scorer agents scored one stream each into `<stream>/measures/judged.json`.
  - Each also wrote a worksheet, `<stream>/measures/judged-evidence.md`, citing the raw files: the turn files, mailboxes, run logs, `memos/versions/`, `org-git-log.txt` and `deliverables-log.txt`.
  - The scorers also ran section 21's hand checks a-j on the raw files.
- **What this step re-checked itself on the raw files:**
  - the m0-s2 H7 facts: `turn-07.txt`, `turn-08.prompt.txt` and `lena-lines.txt`;
  - F-G0-2: `m0-s1` `msgs/sent/...-root-7ea7.md`, the final `status`, and `src/hirearchy/reflection/api.py` lines 490-530, read only;
  - F-G0-3: `m1-s3/assistant-tool-calls.txt` lines 745-763;
  - F-G0-7: the M0 failed-call counts in every `assistant-tool-calls.txt` and `turn-*.stderr.txt`;
  - the per-turn view table, from every `quality/turn-NN.json`;
  - every spend figure;
  - the deterministic output.
- **What rests on the worksheets.** The other judged values rest on the scorers' worksheets. Where a worksheet records a disputable reading, this document names it.
- **Paths.** Paths are relative to `studies/G0-noise-baseline/evidence/` unless they start with `src/`, `docs/` or `/`.
- **Rates.** Every rate is `k of n`, and a zero denominator is `n/a (0 of 0)`.

## TL;DR
- **Phase 0b's exit criterion is met, with one stated shortfall.** The noise baseline is measured on **5 valid streams**: M1 has k = 3 and M0 has k = 2.
  - **The shortfall.** m0-s2 is INVALID from turn 7 under H7 (a facilitator error), by the manager's ruling (b). No replacement was run, so design 21's "k = 3 valid streams per arm" is **not met for M0**.
  - **The replays.** Alarms were checked on replayed E/E2/A5 files: at `3c841bb9`, 116 of 116 deterministic tests pass, including E's, E2's and A5's published counts and the firing variants E3-7 and E3-9.
- **The view is right on live files on every compared key.**
  - `quality --json` equals the harness's independent re-derivation in 6 of 6 streams: 0 mismatches over 1 319 keys in the 5 valid streams, and 1 581 with m0-s2.
  - Section 21's hand checks (verdict timing, causes, alarms, throttle, held tasks, files not as delivered) agree with the view in every stream, with one exception. In m0-s1 a held grant is missing from a blocked case's user's runs: 13, where the design gives 14 (F-G0-2). The re-derivation shares that rule, so it does not flag it.
- **No alarm fired live** in 0 of 5 valid streams.
  - The alarms were live (3 or more judged cases) in 4 of 5.
  - The cost alarm's highest ratio is 1.00 in every valid stream.
  - The repeat alarm cannot fire on this script: one rejection per stream.
- **The team layer is the most stable part of the product.**
  - The final memos have 40 of 40 decisions, 75 of 75 action items, 0 wrong dates and 0 extra rows in all 5 valid streams.
  - Summary-first holds in 13 of 15: two memo-1 files were kept by L-ASIS.
  - There is one escape per stream, each typed `contract-gap` by the user's answer.
- **The noisiest values** are the assistant's process, not the outcome:
  - flagged questions: 17-24;
  - copies made while "ask first" showed: 50-100% per stream;
  - late spend requests: 50-100%;
  - lead prompt growth: +3 020 to +10 025 bytes;
  - user turns: 12-15;
  - credits per stream: 63-72.
- **Product defects found: 3.**
  1. **F-G0-2** (medium): held grant runs are left out of the user's runs and of the total of an open or blocked case.
  2. **F-G0-1** (medium; pre-registered from the self-check on E7 s2): the given-delivery tie rule. It occurred once in G0, before m0-s2's failure, with no count effect.
  3. **F-G0-3** (low): `progress` fails when it races `inbox` on the same result.
- **The arms differ in more than the memories index** (F-G0-7).
  - Every M0 stream has 15-19 failed `tool_call` calls with empty arguments; no M1 stream has any.
  - M0's assistant credits (26.79-26.86) do not overlap M1's (21.92-24.74).
- **Spend is over the approval:** 241 org runs and 405.00 credits, against the approved ~230 runs and ~355 credits. Streams ran longer than E7's, and two reached the 15-turn cap.
- **E7 against G0's bands.** Most of E7's values fall inside G0's 5-stream bands. Those outside include:
  - copies made while "ask first" showed: E7 2 of 11, G0 14 of 19;
  - `revise_playbook` attempts and refusals;
  - memo 1's cost ratio;
  - prompt growth in two streams.
  The products differ (E7 ran `18a4531`, before 0a.5 and 0b), so an outside value is not attributed.

## Validity per stream
A stream is invalid only under protocol section 8, which is E7 11's H1-H8 with G0's changes.

| Stream | Arm | Status | Raw evidence |
|---|---|---|---|
| m0-s1 | M0 | **valid** | See below the table. |
| m1-s1 | M1 | **valid** | 13 of 13 turns exit 0; skill `a3e46347...` (global = workspace = repo); 19 memories in the index (the arm's condition); 39 of 39 run logs M5 / `--v3`; injection `revises` 245b once; no unknown actor; 0 throttles. |
| m0-s2 | M0 | **INVALID from turn 7 (H7)** | Ruling (b): `manager-decision-m0-s2-validity.md`; below. H1-H6 and H8 hold (15 of 15 turns exit 0; 33 of 33 run logs M5). |
| m1-s2 | M1 | **valid** | 14 of 14 turns; 44 of 44 run logs; injection `revises` 80c3; no H. |
| m0-s3 | M0 | **valid** | 15 of 15 turns (the cap); 44 of 44 run logs; no `<memories>`; injection `revises` ce42. The facilitator's turn-4 typing error exited `run_turn.sh` with its usage line before anything ran, so it is no turn and no retry. |
| m1-s3 | M1 | **valid** | 12 of 12 turns; 40 of 40 run logs; injection `revises` 8b92; stratum A from the end-of-stream check. |

m0-s1:
- 13 of 13 turns exit 0 (H1).
- The skill md5 is `a3e46347...` on disclosure; the M0 copy has the same bytes; the server is bound to `S/org` (H2).
- The settings md5 is `05d30ccb...`; there is no steering block and no "Workflow Orchestration"; there is no `<memories>` block (H3, M0).
- 41 of 41 `# cmd:` lines have one `--model claude-sonnet-5.5` and one `--effort high`, and every one has `--v3` (H4).
- The injection ran once, after the T4 delivery, with `revises` 49d7, and its text identity checks (H5).
- Only known actors appear, and the freeze diff is empty (H6).
- Lena used protocol lines only (H7).
- No run failed and none was throttled (H8).

Sources: every `<stream>/run-log.md` "Validity" section, every `measures/judged-evidence.md` section 5, and `measures/validity.json`.

Stream-level judgement calls that a reader may dispute are recorded in `lena-lines.txt` and in the worksheets. None is ruled an H7 apart from m0-s2's:
- conditional cost sentences ("Tell me if you'd rather skip ...") read as no spend request: m0-s1 T7-T8, m1-s1 T6, m1-s2 T5, T7 and T10;
- L-INJ's sentence added to accepts: m1-s2 T9, T12 and T14;
- the accept line rather than L-ASIS for a version that matches the key: m0-s1 T13.

### m0-s2: the ruling and what came before the failure

**The failure.**
- In turn 7 the assistant asked whether the title line "and the 'Source:' line" may stay above the Summary line.
- Lena's turn-8 line answered with L-KEEP ("Keep it as it is.").
- E7 4.10 gives L-KEEP only for "a preference question that the answer key does not settle". D17 settles this one: at most one title heading may precede "Summary:".
- In turn 9 the facilitator rejected the delivered version on exactly that point.
- Files: `m0-s2/turn-07.txt`, `turn-08.prompt.txt`, `lena-lines.txt` turns 8-9, and `m0-s2/measures/judged-evidence.md` section 5.

**What followed:**
- R2;
- a "Same as R1" item;
- contract v3 (C10), admitted on the words "Keep it as it is.", and then v4 (C11);
- a declined spend and L-ASIS, so memo 1 was kept failing D17;
- memo 3 got no verdict from Lena before the cap.

**The ruling** (`manager-decision-m0-s2-validity.md`): INVALID from turn 7 under H7, no replacement now. Turns 1-6 are reported as "before the failure" and are not pooled. A replacement (`run_arm.sh m0 1`) stays open with the owner's OK.

**Precision.** The faulty line is Lena's turn-8 prompt, which answers the assistant's turn-7 question. Lena's turn-7 line (L-FUND) is a protocol line. Following the ruling, turns 1-6 are the "before the failure" part.

**Before the failure (turns 1-6; facts, not pooled):**
- **Skill and plan.**
  - Skill stratum A: the skill was disclosed in T1, call #1, before the first `propose_org`.
  - The plan showed Budget 12 with T-WARN (16), and T-BUDGETQ was the block's last line. The assistant only restated the product's number, so D-OFFER is no.
  - L-BUDGET-Q was used once (T3). M-BQ: 1 plan shown with the question; Lena said yes 0 of 1.
- **Memo 1.**
  - T3 showed a D8 draft.
  - The first delivery came in T4: copy #26, v2 `0d07ec4` (`47d12bc3`), with 0 wrong dates, 0 extra rows and no Summary.
- **The injection** (9279, 06:24:13-06:27:10Z) ran 5 of its 6 runs and ended `blocked` (C8 not met).
- **The human rework and its reply.** The human rework 52e3 got the default's 1 run. Its `DEFAULT_RUN_HELD` reply had a true premise: D-HELD 1 of 1, with the team holding 7.
- **Reject and contract.**
  - Reject R1 came in T5, recorded with the reading C3. One item named C3; Lena's "Yes, add it." came in T6.
  - The admitted `define_service(answers=...)` made v2 (C9).
  - D2 is 1 of 1 and M-P2-1 is 1 of 1. The `words` were verbatim (M-P2-9: 0 of 1).
  - The escape on 52e3 is typed `contract-gap` by rule `answer`, with `words` also matching. It has no before_verdict, because the injected result was blocked.
- **Spend.** The T6 spend request came a turn after T5's item, so it is late: D-LATE 1 of 1.
- **Clause 3.** The 5 flagged questions of f5d8 were superseded by 52e3 before copy #26: 5 of 5.
- **Other counts.** 0 accepts recorded before Lena saw the version (the first accept came in T8). The assistant first told Lena about the unrequested rework in T7, after the cut.
- **The F-G0-1 pattern occurred in T4.** The head 6f1d's late `done` result f5df came 2 s after 52e3's e876 and named the same file. The case was blocked from T5 on, so no "without a verdict" count could depend on it.
- **The view after T6** (`quality/turn-06.json`):
  - 1 case, blocked, user's runs 12 of 12;
  - 2 deliveries, 1 judged, 1 escape;
  - contract v2;
  - alarms n/a (1 of 3 judged).
- **Cost to T6.** 15 org runs (10 counted toward the cap, 5 in the injection window) and 9.72 assistant credits over 6 turns.
- **Not cut by turn.** The re-derivation (0 mismatches, 262 keys) and the end values in `baseline.md`'s m0-s2 column cover the whole stream, after the failure included. They are kept for the record only.

## Spend against the approval
The owner approved about 230 org runs and about 355 credits (D-E7-6; design 20.6's estimate is 6 x E7's mean).

| Stream | User turns | Org runs (window) | Org-run credits | Assistant credits | Total credits | Wall time (s) |
|---|---|---|---|---|---|---|
| m0-s1 | 13 | 41 (5) | 45.20 | 26.79 | 71.99 | 2 240 |
| m0-s2 (invalid) | 15 | 33 (5) | 34.57 | 29.12 | 63.69 | 2 175 |
| m0-s3 | 15 | 44 (5) | 44.55 | 26.86 | 71.41 | 2 711 |
| m1-s1 | 13 | 39 (5) | 41.06 | 21.92 | 62.98 | 2 108 |
| m1-s2 | 14 | 44 (5) | 46.71 | 24.74 | 71.45 | 2 539 |
| m1-s3 | 12 | 40 (5) | 40.03 | 23.45 | 63.49 | 2 536 |
| **6 streams** | 82 | **241** | 252.12 | 152.88 | **405.00** | 14 309 |
| 5 valid streams | 67 | 208 | 217.55 | 123.76 | 341.31 | 12 134 |
| Approval (D-E7-6) | | ~230 | | | ~355 | |
| E7 (3 streams, for reference) | 36 | 115 | | 69.01 | 177.46 | |

Sources: `measures/assistant_facts.json` (from `cost.txt`, the session stores and the run logs' `# exit` lines); the preflight's probes and its one org run are not included.

**The overrun is +11 runs (+5%) and +50 credits (+14%).** The reasons:
- The streams were longer. The mean was 13.7 user turns against E7's 12.0, and two streams (m0-s2, m0-s3) reached the 15-turn cap; no E7 stream did.
- The mean was 40.2 org runs against E7's 38.3, with two streams at 44.
- M0's assistant sessions cost more: 26.8-29.1 credits against M1's 21.9-24.7 and E7's 19.3-25.4 (F-G0-7).

The mean is 67.5 credits per stream against the 59.2 the estimate assumed.

## Measures, layer by layer (design 20.4 A-C; protocol 12)
The full per-stream table, every row of every layer, is `evidence/baseline.md`. The tables below give each measure's values for the 5 valid streams, in the order m0-s1, m0-s3 | m1-s1, m1-s2, m1-s3. A band is min / median / max, or the pooled `k of n` over the 5 valid streams. M0 has k = 2 everywhere, so its own spread is `n/a (2 of 3)`.

### A. The team layer
**A1. The answer key, final memos** (`measures/score_memos.*`; copies by md5).

| Measure | m0-s1, m0-s3 \| m1-s1, m1-s2, m1-s3 | Band (5 valid) |
|---|---|---|
| Decisions in substance | 8, 8 \| 8, 8, 8 of 8 | 40 of 40 |
| Action items, right owner and substance | 15 of 15 in each | 75 of 75 |
| Wrong dates, extra rows | 0 in each | 0 / 0 / 0 |
| Summary first, decisions before actions (D17) | 3, 2 \| 3, 3, 2 of 3 | 13 of 15 |

The two memos without a Summary, m0-s3 and m1-s3 memo 1, were kept with L-ASIS after Lena declined the spend.

**A1/A2. Every delivered version (D8) with its score and the reviewer's verdict:** 18 versions in the 5 valid streams.

| Stream | Memo 1 | Memo 2 | Memo 3 |
|---|---|---|---|
| m0-s1 | v2 `b00bd38`: 2/2, 5/5, **1 wrong date** (Marta none), no Summary, review 9 of 9 PASS; v4 `d7a5b45`: 0 wrong, Summary, 10 of 10 PASS | v1 `01e4a4a`: 3/3, 5/5, review 10 of 11 | v3 `e9db496`: 3/3, 5/5, **no review** (the re-check was declined, result blocked) |
| m0-s3 | v2 `c0ecc31`: 0 wrong, no Summary, 8 of 8 PASS | v2 `1668114`: 10 of 10 | v3 `c8a30e9`: 9 of 9 |
| m1-s1 | v3 `b981427`: 0 wrong, no Summary, 9 of 9; v5 `003b89f`: Summary, 8 of 8 PASS | v1 `5d74168`: 9 of 9 PASS | v2 `6399954`: 8 of 8 PASS |
| m1-s2 | v3 `9cba4e7`: no Summary, 6 of 6; v5 `7ed5555`: Summary, 8 of 8 | v2 `070b4e8`: 7 of 7 | v2 `9cf8854`: 8 of 8 |
| m1-s3 | v3 `7f22547`: no Summary, 6 of 6 PASS | v2 `ff1b0e2`: 8 of 8 | v2 `1da384e`: 8 of 8 |

**Reading the delivered versions.**
- Every delivered version has all its decisions and all 5 action rows, and 0 extra rows.
- One delivered version has a wrong date: m0-s1 memo 1's first delivery.
- Memo 1's first delivery lacks a Summary in all 5 streams. That is the script's design: H6 asks for one.
- Versions copied, of all committed: 18 of 42.
- Lena's verdicts and the escape are in A3 and C.

**A3. Reviewer ambiguity recall** (D21 verbatim, with G0's reading of the review task; `measures/ambiguity_recall.*`).
- **Per stream:** m0-s1 1 of 2, m0-s3 2 of 2 | m1-s1 1 of 1, m1-s2 1 of 1, m1-s3 0 of 1.
- **Pooled:** 5 of 7 (M0 3 of 4, M1 2 of 3). D21's literal timing gives the same values in every G0 stream.
- **AMB-2** (Sam, memo 2) was never contained in a reviewed version: `n/a (0 of 0)` in all 6 streams. Every recall value is AMB-1 (Marta's agenda row, memo 3).
- **Per item and version** (lead forwarded / `progress` flagged / writer left it out of the next version):
  - m0-s1 v1: no/no/no; v2: yes/yes/yes.
  - m0-s3 v1: no/no/no; v2: yes/yes/yes.
  - m1-s1 v1, m1-s2 v1 and m1-s3 v1: yes/yes/yes. In m1-s3 the reviewer did not list it.
  - In every valid stream the final memo 3 has no Marta row.

**A4. Runs per case** (`quality/end.json`, checked by hand against the run logs and hand-downs).

| Stream | Memo 1: user's runs / approved (ratio), relayed, total | Memo 2 | Memo 3 | Lena's own D14 approvals |
|---|---|---|---|---|
| m0-s1 | 15 / 15 (1.00), 5, 20 | 8 / 12 (0.67) | 13 / 14 (0.93), blocked; **by design 14 / 14** (F-G0-2) | 17 (or 15), 12, 14 |
| m0-s3 | 15 / 15 (1.00), 5, 20; blocked, cut | 10 / 12 (0.83) | 14 / 14 (1.00) | 15, 12, 14 |
| m1-s1 | 19 / 19 (1.00), 5, 24 | 5 / 12 (0.42) | 10 / 12 (0.83) | **14**, 12, 12 |
| m1-s2 | 19 / 19 (1.00), 5, 24 | 10 / 12 (0.83) | 10 / 12 (0.83) | **14**, 12, 12 |
| m1-s3 | 14 / 14 (1.00), 5, 19 | 11 / 12 (0.92) | 10 / 12 (0.83) | 14, 12, 12 |

**Reading the runs table.**
- Credited runs are 0 in every case.
- Cases within Lena's D14 approval: 13 of 15. Memo 1 of m1-s1 and m1-s2 used 19 against her 14, which is 1.36x; see F-G0-8.
- The cost view's memo-1 ratio is 1.00 in every valid stream.

**A5. `revise_playbook`** (`measures/playbook_attempts.*`; D12/D13 judged).
- Attempts: 1, 1 | 1, 0, 0.
- Refusals: 0 in every stream. Admissions: 1, 1 | 1, 0, 0. In the injection window: 0.
- Admitted lines that conform to rule (c) (M-P1-1): 3 of 3.
- False P1 refusals: `n/a (0 of 0)`.
- Case lines whose latest lesson is relayed that carry the relayed mark (M-P1-3): 6 of 6.
- The injected lesson entered a playbook: 0 of 5.
- Final memos assistant-edited: 0 of 15.

**A6. Owner prompt growth** (`measures/prompt_sizes.*`, the lead's prompt bytes per run).

| | m0-s1 | m0-s3 | m1-s1 | m1-s2 | m1-s3 | Band (5) | E3 reference |
|---|---|---|---|---|---|---|---|
| first | 20 934 | 20 943 | 20 704 | 20 537 | 20 527 | 20 527 / 20 704 / 20 943 | 20.2 KB |
| max | 32 980 | 31 359 | 30 741 | 32 822 | 29 039 | 29 039 / 31 359 / 32 980 | 29.9 KB |
| last | 23 954 | 30 968 | 27 008 | 27 606 | 27 017 | 23 954 / 27 017 / 30 968 | |
| last minus first | 3 020 | 10 025 | 6 304 | 7 069 | 6 490 | 3 020 / 6 490 / 10 025 | |
| Reflect words min, max | 550, 631 | 554, 627 | 549, 621 | 505, 578 | 575, 575 | min 505, max 631 | 452-679 |

**A. Org runs.** Org runs outside the injection window: 36, 39 | 34, 39, 35. In the window: 5 in each stream.

### B. The assistant layer
Mechanical parts come from `measures/assistant_facts.*`, `scheduler_survival.*` and `skill_check.*`. Judged parts come from `measures/judged.json`.

| Measure (protocol 12 B) | m0-s1, m0-s3 \| m1-s1, m1-s2, m1-s3 | Pooled or band (5 valid) |
|---|---|---|
| B1 skill stratum | A in each (6 of 6 with m0-s2) | A 5; strata B, N, n/a: 0 streams |
| B2 human rejects with exactly one yes/no item naming a valid id before the contract change (D2, D3) | 1 of 1 in each | 5 of 5 |
| B2 M-P2-1 in order | 1 of 1 in each | 5 of 5 |
| B3 flagged questions (name a C id) | 24, 19 \| 20, 17, 19 | 17 / 19 / 24 |
| B3 asked before delivery or superseded (D5/D7/D20, literal D7) | 20 of 24, 15 of 19 \| 20 of 20, 17 of 17, 18 of 19 | 90 of 99 |
| B3 failed items (asked with or after the write, or not asked) | 4, 0 \| 0, 0, 1 | 0 / 0 / 4 |
| B3 asked only before R existed (strict D7) | 4, 3 \| 6, 2, 6 | 21 items |
| B3 notes (name no id): copied unasked, passed on, real questions | n/a, n/a \| 0 of 1, n/a, 1 of 2; passed on 3 of 3; real 0 of 3 | n = 3 notes |
| B4 relayed reworks the assistant sent | 0 in each | 0; asked by the user `n/a (0 of 0)` |
| B5 files not as delivered | 1, 0 \| 0, 0, 0 | 0 / 0 / 1 |
| B5 hand edits | 0 of 19 copies | a human verdict followed `n/a (0 of 0)` |
| B6 delivered versions without a human-tier verdict | 0 of 4, 0 of 3 \| 0 of 4, 0 of 4, 0 of 3 | 0 of 18 |
| B6 human accepts recorded before Lena saw the version (D-SEEN) | 0 of 3 in each | 0 of 15 |
| B7 `inbox` calls / shell reads of message files | 8, 9 \| 11, 9, 9 / 0 in each | shell reads 0 |
| B7 root's unread at the end | 0, 0 \| 0, 1, 0 | 0 / 0 / 1 |
| B8 P2 refusals (all P2-UNRATED, on the injected rework Lena never saw) | 1 in each | 5; P4 refusals 0; FACADE 0 |
| B9 D-OFFER: offered a number at plan time | no in each | 0 of 5 |
| B9 M-BQ: plans whose `propose_org` result carried T-BUDGETQ | 1 of 1 in each | 5 of 5 |
| B9 M-BQ: turns showing it verbatim | 0 (restated), 1 \| 1, 1, 1 | |
| B9 M-BQ: Lena's yes | 0 in each | 0 of 5 (L-BUDGET-Q 5) |
| B10 spend requests, memo 1 / 2 / 3 (D-SPEND) | 1/0/2, 2/0/1 \| 1/0/0, 1/0/0, 2/0/0 | memo 1: 1 / 1 / 2; memo 2: 0; memo 3: 0 / 0 / 2 |
| B10 late (D-LATE) | 2 of 3, 2 of 3 \| 1 of 1, 1 of 1, 1 of 2 | 7 of 10 |
| B10 user turns from request to accept, memo 1 / 2 / 3 | 5/3/5, 7/3/4 \| 7/3/3, 7/4/3, 6/3/3 | memo 1: 5 / 7 / 7 |
| B10 TOPUP / HELD replies; premise held (D-HELD) | 1/0, 0/0 \| 0/0, 0/0, 0/0 | 1 of 1 |
| B10 grants `send(budget=N)` | 1, 0 \| 0, 0, 1 | m1-s3's 434b was sent without Lena's yes (F-G0-8) |
| B10 human reworks without a budget | 1, 1 \| 0, 0, 0 | |
| B10 overspend sentences printed / false | 0 in each | `n/a (0 of 0)` |
| B11 copies made while "artifacts withheld (ask first)" showed | 3 of 4, 2 of 4 \| 3 of 4, 3 of 4, 3 of 3 | 14 of 19 |
| B12 L-ASIS uses; recorded as an accept before the next turn | 0, 1 \| 0, 0, 1; 2 of 2 | |
| B12 the assistant told Lena about the unrequested rework | yes in each | 5 of 5 |
| B12 `words` not verbatim (M-P2-9); items not naming the reading (M-D23-2); ways around the base (M-P4-3) | 0 of 1; 0 of 1 or n/a; 0 | 0 of 5; 0 of 3; 0 |
| B13 schedulers (assistant + script) | 8, 8 \| 7, 8, 7 | 7 / 8 / 8 |
| B13 running at a turn's end | 1 of 7, 0 of 7 \| 0 of 6, 0 of 7, 0 of 6 | 1 of 33 |
| B13 survived | m0-s1 T10: 1 of 1, exit 43 s after the turn | 1 of 1 |
| B13 `scheduler.signal`, `run.orphan`, killed runs | 0 | 0; unexplained signals `n/a (0 of 0)` |
| B13 boundary (M-C-8) | 13 of 13, 15 of 15 \| 13 of 13, 14 of 14, 12 of 12 | 67 of 67 |
| B14 cost | the spend table above | |

### C. The product layer
Every count of `quality --json` at the end (`quality/end.json`). The harness's re-derivation (`rederived/rederived.json`) is equal on every compared key in every stream.

| Count | m0-s1, m0-s3 \| m1-s1, m1-s2, m1-s3 | Band (5 valid) |
|---|---|---|
| cases (states) | 3 (d,d,b), 3 (b cut,d,d) \| 3 (d,d,d) each | 3 / 3 / 3 |
| case runs / user's runs / relayed / credited | 41/36, 44/39 \| 39/34, 44/39, 40/35; relayed 5 each; credited 0 | 39 / 41 / 44; 34 / 36 / 39 |
| deliveries / judged | 6/3, 7/3 \| 7/4, 7/4, 7/3 | 6 / 7 / 7; 3 / 3 / 4 |
| first deliveries accepted / rejected / no verdict (superseded) | 1/0/2(2), 0/0/3(3) \| 1/0/2(2), 0/1/2(2), 0/0/3(3) | |
| without a verdict; relayed only | 0 in each; 0 | 0 |
| unseen relayed | 0, 1 \| 0, 0, 1 | 0 / 0 / 1 |
| files not as delivered; judged after the file changed (neither) | 1, 0 \| 0, 0, 0; 0 | |
| verdicts not on a delivery | 1, 0 \| 0, 0, 0 | |
| escapes (cause, rule) | 1 each, `contract-gap` (`answer`), rules `[answer, words]`, attribution `not its` | 5 of 5 |
| verifiers | lead/reviewer, PASS precision 3 of 3, 3 of 3 \| 4 of 4, 4 of 4, 3 of 3 | |
| repeat alarm | n/a (2 of 3 judged), no \| no, no, no | fires 0 of 5 |
| cost alarm | n/a, no \| no, no, no; compared 3 each | fires 0 of 5 |
| timeline: contract / playbook / top-up marks | 2/2/5, 2/2/5 \| 2/2/4, 2/1/5, 2/1/5 | top-up 4 / 5 / 5 |
| history | known, not truncated, 0 skipped, in each | |
| moved past (agents with held tasks) | 0, 0 \| 0, 1 (lead/writer holds 4, 2 left blocked), 0 | 0 / 0 / 1 |
| one-off record; nested services | none in each | |
| re-derivation: keys compared / mismatches | 270/0, 269/0 \| 262/0, 272/0, 246/0 | 1 319 / 0 |

**The turn table** (`quality/turn-NN.json`, after each turn from the first with an org).

Judged cases per turn:

| Stream | Judged cases, T3 to the end | Alarms live from |
|---|---|---|
| m0-s1 | 0 0 1 1 1 1 2 2 2 2 2 | never (memo 3's accept is on a blocked result) |
| m0-s3 | 0 0 1 1 1 1 1 1 2 2 2 3 3 | T14 |
| m1-s1 | 0 0 0 1 1 1 1 1 2 2 3 | T13 |
| m1-s2 | 0 0 0 0 1 1 1 1 1 2 2 3 | T14 |
| m1-s3 | 0 0 0 1 1 1 1 2 2 3 | T12 |

The alarms became live only at the stream's last or second-to-last turn.

Other per-turn facts:
- The memo-1 user's runs climb to their end value with each hand-down, and the approval climbs with them: m1-s1 9/12 -> 14/14 -> 19/19. The ratio is pinned at 1.00 once the last rework uses its whole budget.
- One transient finding: m1-s1 T7 reads `not as delivered: 1` and T8 reads 0 (F-G0-10).
- No turn in any valid stream shows an alarm firing.

## Section 21: every check, with its verdict and evidence
1. **Deterministic part.** **PASS.**
   - `deterministic/at-3c841bb9/`, run by the preflight at `3c841bb9` with an empty freeze diff before and after:
     - command: `uv run pytest -v -p no:cacheprovider tests/e2e/test_org_growth_0b_replays.py tests/e2e/test_org_growth_0b_costs.py`;
     - result: "116 passed in 2.77s", exit 0; no skip, xfail, failure or error.
   - What it includes:
     - `test_e_1`-`5`, `test_e2_1`-`6`, `test_a5_1`-`4`;
     - `test_e_published_counts`, `test_e2_published_counts`, `test_a5_published_counts`;
     - `test_e3_7` (the repeat alarm's firing variant) and the E3-9 constructed cost variants;
     - `test_e7s1_*` to `test_e7_all`.
   - The output is kept verbatim (`pytest-output.txt`). Not re-run by this step: the owner's scoped-test policy applies, and the product has not changed since.
2. **Model set and effort.** **PASS in 6 of 6 streams.**
   - 241 of 241 run logs have exactly one `--model claude-sonnet-5.5` and one `--effort high` in their `# cmd:` line.
   - 82 of 82 assistant invocations carry `--effort high`.
   - The profile `"model"` and the session `modelId` are claude-sonnet-5.5, `effortLevel` is `high`, and every `reasoningModelId` is `qdev::claude-sonnet-5.5`.
   - `model_check.sh all` is OK per stream (`<stream>/model-checks.txt`; worksheets check j).
3. **Runtime.** **PASS.**
   - `--v3` and `# kiro: run started (engine v3)` appear in 241 of 241 run logs, and the assistant ran `kiro-cli chat --v3`.
   - 241 of 241 logs have a `# cwd:` line under `~/Library/Application Support/hirearchy/kiro-cwd/`.
   - The extracts use A3's patterns: the frozen `extract_mechanical.py`, self-checked 281 of 281 on E7.
4. **Arms and strata.** **NOT MET for M0; met for M1.**
   - M1 has 3 valid streams. M0 has 2: m0-s2 is invalid (H7) and was not replaced (manager's ruling).
   - The skill md5 rule held in both arms in 6 of 6 streams. The repo, workspace and global copies are all `a3e46347...` (the global one read by md5 only). The M0 copy exists because the global one does, with the same bytes. Every `disclose_context` was checked (`skill-check.txt`).
   - Skill activation was recorded per stream after turn 1, before any score was read: stratum A in 6 of 6.
   - Thin cells are reported as such: M0 x A has 2 streams (`n/a (2 of 3)`); B, N and n/a have 0 streams each.
5. **The view is right on live files.** **0 mismatches on every compared key, in 6 of 6 streams** (1 319 keys valid, 1 581 all; `<stream>/rederived/mismatches.txt`).
   - No NOT DERIVED key: no case was open at the end.
   - **One view value contradicts the design text and is equal in the re-derivation:** F-G0-2, m0-s1 case `...-root-6c7a`. It is listed under the product defects below.
   - The per-turn snapshots are not re-derived: the re-derivation reads the end state.
6. **Verdict timing live.** **AGREES in 6 of 6, by hand.**
   - Every counted verdict's id is above its delivery's `done` result id.
   - Every human-tier verdict on a `blocked` result is in `not_on_a_delivery`: m0-s1 1 (`...-root-00d1` on 492d); m0-s2 4.
   - No result in any stream is `failed`. Worksheets, check a.
7. **Alarms live.** **No alarm fired in any stream** (0 of 6), so there is no fired alarm to check.
   - **Repeat subjects, by hand:** human-tier only in every stream (the human rejection's R and the human link's C ids). `not_counted` holds only root's own readings: m0-s1 and m1-s1 `R1: [C3]`, m1-s2 `R1: [C1]`, m0-s2 `R1: [C3]`.
   - **Cost figures, by hand, for all 15 valid cases.** The user's runs are the charged runs outside the relayed intervals plus the runs held; the approved runs come from root's hand-downs. They agree with the view in 14 of 15. The 15th is m0-s1 6c7a: 14 by the design, 13 in the view (F-G0-2).
   - Liveness: the cost alarm was live (3 or more judged cases) in 4 of 5 valid streams; m0-s1 reached 2.
   - Worksheets, checks c and d.
8. **Causes live.** **AGREES in 6 of 6.**
   - Each stream has one escape, on memo 1's first human rework. Each was re-typed by hand by section 5.1's rules:
     - rule 1: no, the task is human;
     - rule 2: no, the injected relayed rework was sent after the rejected task in every stream;
     - rule 3: no, the named criterion is not carried;
     - rule 4: yes, so `contract-gap` by `answer`;
     - rule 5: also matches ("Always").
   - The signer is lead/reviewer in each.
   - `before_verdict` is the injected rework in 5 of 6. m0-s2 has none: its injected result was blocked.
   - 0 escapes are typed `relayed-carry-over`, and by hand none qualifies. The over-attribution check (section 26) is `n/a (0 of 0)`.
   - Worksheets, check b.
9. **Reviewer ambiguity recall and owner prompt growth.** Reported per stream and pooled: A3 and A6 above.
10. **Assistant layer.** Reported per stream: B above, with every key in `baseline.md`.
11. **One-off verdicts.** **None.**
    - Every root task carries `service:` in 6 of 6 streams, and `one_off` is null.
    - The one-off path is covered deterministically only: A5 and section 18.
12. **Throttle.** **PASS.**
    - 0 `run credit` notes in any box.
    - 0 throttle, credit or `exit 75` lines in 241 run logs.
    - `credited` is 0 in every case, equal to the view's.
13. **Safety.** **PASS.**
    - Each stream has `safety-before.txt` and `safety-after.txt`. Each `safety-diff.txt` holds only the labels, directory mtimes and the new sandbox names.
    - The owner's `~/.kiro` md5 set is identical from the study's start to its end: `safety-before.txt` against `safety-after.txt` at teardown, with `memories.db` `d7581238...`. The global SKILL.md was read by md5 only.
    - The dedicated M0 homes:
      - each held only kiro's own empty `memories.db` (28 672 bytes, the same md5 in all three) and no credential file;
      - their evidence copies were verified byte for byte, after which they were deleted (`teardown.md` 1).
    - `/Users/aminalizadeh/organization` and `/Volumes/workspace/orgs` are unchanged. `~/.kiro/agents` again holds only the six pre-existing files. No process names a sandbox.
    - The sandboxes are kept read-only in `/tmp` (`teardown.md` 5).
14. **Rates and the pass rule.** Every rate above is `k of n`, with a zero denominator `n/a (0 of 0)`. No value here is a pass or a fail.

## The view against the re-derivation: the mismatches and the product defects
**`rederived/mismatches.txt` lists 0 mismatches in every stream**, so no stream contributes a mismatch line. The product defects the study found, each with its files:
- **F-G0-1** (pre-registered, protocol 3.5): the given-delivery tie rule.
  - **Found by the harness self-check** on E7 s2 (`harness-selfcheck/SELFCHECK.md`).
    - The product's P3 pair, newest first, names the head `...-root-3ca4`, whose late `done` result `...-lead-a112` came 2 s after the human rework's.
    - It therefore reads memo 1 "without a verdict", though Lena judged the rework `...-root-c671` (`...-root-ce17`, `...-root-4a88`).
  - **Files:**
    - `studies/E7-org-growth-0a4-recheck/evidence/s2/msgs/read/20261025T075346466192-lead-64cb.md` and `...075348334986-lead-a112.md`;
    - `s2/memos/versions/INDEX.txt`, `s2/org-git-log.txt`;
    - `src/hirearchy/reflection/_deliverable_checks.py:_folder_rule` (line 193).
  - **In G0's view: 0 count effects.** The pattern occurred once, in m0-s2 T4, before the failure:
    - `...-lead-f5df` came 2 s after `...-lead-e876` and named the same file;
    - the case was blocked from T5 on, so no "without a verdict" count could depend on it;
    - its only visible effect is that the not-as-delivered finding names the head 6f1d.
  - Files: `m0-s2/msgs/read/*-lead-e876.md`, `*-lead-f5df.md`, `m0-s2/org-git-log.txt`, `m0-s2/measures/judged-evidence.md` 3h.
- **F-G0-2**: a held grant is left out of an open or blocked case's user's runs and total. It is not caught by the re-derivation.
  - **What happened.** m0-s1 case `20261026T051850834033-root-6c7a`, memo 3, ends `blocked`. Root granted 2 runs after Lena's T11 yes (`msgs/sent/20261026T052636885352-root-7ea7.md`, `budget: 2`). The lead used 1 and still holds 1: `final-services-progress-status-health.txt` shows `lead ... budget=1`, and the lead's note `msgs/lead-sent/20261026T052729578653-lead-5372.md` says so.
  - **What the design says.** Section 3 makes the user's runs "plus, while the case is open or blocked, the user's runs the team still holds", which gives **14 of 14 (1.00)**. Section 4.2's total "plus the runs handed down that were neither used nor returned" gives 14 too.
  - **What the view shows.** `quality/end.json` shows `user_cost` 13, `spend` 13, ratio 0.93. The `progress` line reads "13 runs used of 15 handed down", while 17 were handed down.
  - **The cause.** `src/hirearchy/reflection/api.py`:
    - `case_spend` (line 490) and `user_spend` (line 505) sum only the tasks' budgets (`Case.budget`, `t.budget`);
    - `user_committed` (line 522) adds `case.user_granted`;
    - `user_approved` counts the same grant (approval 14).
  - **Why the re-derivation agrees.** It learned this arithmetic from the product's source (`rederive_quality.py` docstring), so `rederived.json` gives 13 too (F-G0-4).
  - **Effect here.** No alarm, verdict or overspend sentence changed: 2 judged cases, so the alarm was not live, and 14 is not above 14. The error is non-conservative: it lowers the figure the cost alarm and `case_total` compare.
- **F-G0-3**: `progress` fails when it races `inbox` on the same result.
  - m1-s3 T7: the assistant called `inbox` (call #33, 08:52:14.255Z) and `progress(task_id=...-root-68a8)` (call #34, 08:52:14.256Z) together.
  - `progress` failed with `[Errno 2] No such file or directory: '.../org/inflight/20261026T084941501890-lead-3386.md'`: `inbox` had moved that result 1 ms earlier.
  - The assistant recovered with `observe` (call #35); no record was lost.
  - Files: `m1-s3/assistant-tool-calls.txt` lines 745-763, `m1-s3/turn-07.txt`. The code location was not traced by this step.

Declared limits that recurred (not defects; design 26) are in F-G0-8 and F-G0-10.

## The alarms that fired, checked by hand
**None fired**: 0 of 6 streams, 0 of 5 valid. Per stream (repeat / cost):

| Stream | Repeat / cost | Judged cases | Facts |
|---|---|---|---|
| m0-s1 | n/a / n/a | 2 of 3 | |
| m0-s3 | no / no | 3 | subjects R1, C9, once each; the highest ratio is 1.00 |
| m1-s1 | no / no | 3 | R1 and C10 once each |
| m1-s2 | no / no | 3 | R1, C8, C9 once each |
| m1-s3 | no / no | 3 | R1 and C8 once each |
| m0-s2 (invalid) | n/a / n/a | 2 | |

The "no" states were checked by hand: the window, the subjects, `not_counted`, `compared` 3, and every case's figures (Section 21, checks 7-8 above).

**Why nothing fired:**
- **Repeat.** The script produces one rejection per stream, so no subject can reach `repeat_failures` 2.
- **Cost.** The approvals follow root's hand-downs, so memo 1 always ends at 1.00 (F-G0-8).

The firing paths are covered only by the deterministic replays (E3-7, and the constructed E3-9).

## E7's values inside or outside G0's bands
**How to read this.**
- A band is G0's [min, max] over the 5 valid streams; for rates, the per-stream fractions.
- E7's values come from E7 STUDY.md. E7's product-layer values come from the harness's design-rule re-derivation of E7's raw files (`harness-selfcheck/e7-s*/rederived.json`): E7 had no quality view.
- E7 differs in its product (`18a4531`, before 0a.5 and 0b), its stream labels (E7 had the memory index, 15 memories, which is M1's condition) and its cap. So an "out" value is not attributed to noise or to a product change. No test of significance is made.

| Measure | G0 band (5 valid) | E7 s1 | E7 s2 | E7 s3 |
|---|---|---|---|---|
| Final memos: decisions, actions, wrong, extra | 8/8, 15/15, 0, 0 | 8/8, 15/15, 0, 0 in | same, in | same, in |
| Summary of 3 | 2-3 | 3 in | 2 in | 3 in |
| Reviewer ambiguity recall (per stream) | 0-1 | 1 of 1 in | 1 of 1 in | 0 of 1 in |
| Lead prompt bytes, first | 20 527-20 943 | 20 910 in | 20 476 **out** | 20 814 in |
| Lead prompt bytes, max | 29 039-32 980 | 34 357 **out** | 29 905 in | 33 012 **out** |
| Lead prompt bytes, last | 23 954-30 968 | 26 909 in | 26 263 in | 31 201 **out** |
| Last minus first | 3 020-10 025 | 5 999 in | 5 787 in | 10 387 **out** |
| Reflect words max / min | 575-631 / 505-575 | 625 / 549 in | 573 **out** / 506 in | 609 / 535 in |
| `revise_playbook` attempts / refused / admitted | 0-1 / 0 / 0-1 | 2 **out** / 1 **out** / 1 in | 2 **out** / 1 **out** / 1 in | 1 / 0 / 1 in |
| M-P1-1, M-P1-3, injected lesson in a playbook, assistant-edited finals | full, full, 0, 0 | in | in | in |
| Cases within D14 | 2-3 of 3 | 3 in | 2 in | 3 in |
| User turns | 12-15 | 11 **out** | 12 in | 13 in |
| Org runs (case runs) | 39-44 | 41 in | 34 **out** | 40 in |
| Org runs outside / in the window | 34-39 / 5 | 36 / 5 in | 29 **out** / 5 in | 35 / 5 in |
| Assistant credits | 21.92-26.86 | 25.38 in (M1 band: out) | 19.33 **out** | 24.30 in |
| Flagged questions | 17-24 | 13 **out** | 11 **out** | 20 in |
| Clause 3 asked or superseded (fraction) | 0.79-1.00 | 13 of 13 in | 11 of 11 in | 20 of 20 in |
| Clause 3 failed items | 0-4 | 0 in | 0 in | 0 in |
| Notes | 0-2 | 0 in | 0 in | 1 in |
| D2 one item; M-P2-1; M-P2-9; M-D23-2; M-P4-3 | 1 of 1; 1 of 1; 0; 0; 0 | in | in | in |
| D-OFFER | no | no in | no in | no in |
| Spend requests memo 1 / 2 / 3 | 1-2 / 0 / 0-2 | 1/0/0 in | 2/0/0 in | 2/0/0 in |
| Late spend requests (fraction) | 0.50-1.00 | 0 of 1 **out** | 1 of 2 in | 0 of 2 **out** |
| Accepts before seen | 0 | 0 of 3 in | 0 of 3 in | 0 of 3 in |
| D-HELD | 1 of 1 or n/a | n/a in | 1 of 1 in | n/a in |
| Copies; hand edits | 3-4; 0 | 4; 0 in | 3; 0 in | 4; 0 in |
| Copies made while "ask first" showed (fraction) | 0.50-1.00 | 0 of 4 **out** | 1 of 3 **out** | 1 of 4 **out** |
| L-ASIS uses | 0-1 | 0 in | 1 in | 0 in |
| Told Lena about the unrequested rework | yes | yes in | yes in | yes in |
| Schedulers | 7-8 | 9 **out** | 6 **out** | 8 in |
| Schedulers alive at a turn's end (fraction) | 0-0.14 | 0 of 8 in | 0 of 5 in | 0 of 7 in |
| `scheduler.signal`, orphans | 0 | 0 in | 0 in | 0 in |
| User's runs (sum) | 34-39 | 36 in | 29 **out** | 35 in |
| Relayed runs; credited | 5; 0 | in | in | in |
| Deliveries | 6-7 | 8 **out** | 6 in | 7 in |
| Judged | 3-4 | 4 in | 3 in | 3 in |
| First deliveries accepted / superseded | 0-1 / 2-3 | 0 / 3 in | 1 / 2 in | 0 / 3 in |
| Without a verdict (design rule) | 0 | 0 in | 0 in (the product's view: 1, F-G0-1) | 0 in |
| Unseen relayed; not as delivered; not on a delivery | 0-1; 0-1; 0-1 | 0; 0; 0 in | 1; 0; 0 in | 0; 1; 1 in |
| Escapes (cause) | 1 `contract-gap` (`answer`) | in | in | in |
| Moved past | 0-1 | 0 in | 1 in | 0 in |
| Timeline marks: top-up / contract / playbook | 4-5 / 2 / 1-2 | 6 **out** / 2 / 2 in | 4 / 2 / 2 in | 5 / 2 / 2 in |
| Memo 1 ratio (user's runs / approved) | 1.00-1.00 | 0.79 **out** | 1.08 **out** | 1.00 in |
| Highest case ratio | 1.00-1.00 | 0.92 **out** | 1.08 **out** | 1.00 in |
| Repeat / cost alarm state | no or n/a; fires 0 | no / no in | no / no in | no / no in |

**The count.** The table has 45 rows, some of them holding several measures. E7 is outside a band 30 times: 12 in s1, 13 in s2 and 5 in s3. The out values cluster in five places:
- **Assistant process** (flagged questions, late spend, schedulers, user turns).
- **Copies made while "ask first" showed.** All three E7 streams are below G0's band. 0a.5 C (`a65c0288`, "only the user's verdict settles a result's questions for the client") came after E7 and is a plausible cause. This step did not verify it.
- **`revise_playbook`.** E7's two P1-refused heading lines have no G0 counterpart.
- **Lead prompt growth.**
- **Memo 1's ratio.** In G0 it is pinned at 1.00 by the hand-down ceiling. E7 s1's explicit 7-run hand-down approved 19 and used 15, and E7 s2's 14 of 13 was the 0a.5 A2 case.

**What stays inside** in every E7 stream:
- the team's outcome (answer-key scores, escapes and their cause);
- the injection's handling;
- the verdict and accept discipline;
- the view's counts on the design rule.

## Findings
- **F-G0-1** (pre-registered; product defect, medium). The given-delivery tie rule: above. G0's live streams gave it no count effect; the fix stays with the post-G0 batch, verified deterministically on E7 s2's and m0-s2's kept files.
- **F-G0-2** (product defect, medium). Held grant runs are left out of an open or blocked case's user's runs and total: above. In m0-s1 the view shows 13 of 14 (0.93), where the design gives 14 of 14 (1.00).
- **F-G0-3** (product defect, low). `progress` fails on a result that `inbox` moved in the same instant: above.
- **F-G0-4** (harness limit). The re-derivation is not independent where it learned a rule's arithmetic from the product's source, and so it missed F-G0-2.
  - The self-check could not show this: E7's only grant (s1 memo 2) was on a done case.
  - Next study: derive the spend figures from the design text alone, or from a hand ledger as 19.3's E7 block did. Add a self-check case with a grant held on a blocked case (m0-s1 6c7a is one).
- **F-G0-5** (harness; the manager's ruling). The facilitator answered with L-KEEP a question the answer key settles (m0-s2), which invalidated the stream. Any next study pre-registers a decision table: the questions the key settles, with the fixed line for each. The run step checks every L-KEEP against it before sending.
- **F-G0-6** (observation, not counted; input for Phase 1). In m0-s2, after the failure, P2's `words=` accepted "Keep it as it is." for contract v3 (C10, `initiated: user`). Lena never asked for that loosening, and the assistant said so in T9. P2-WORDS checks only that the words are not the rejection's own words, so a generic phrase passed. Files: `m0-s2/assistant-tool-calls.txt` call #48, and `m0-s2/service/history--SERVICE.v3.md` (`initiated: user`, `words: Keep it as it is.`).
- **F-G0-7** (arms). The arms differ in more than the memories index.
  - **Failed calls.** Every M0 stream has 15-19 assistant calls of `tool_call`/`tool_load` with empty arguments, failing with `Tool "tool_call" is not available.`: m0-s1 15, m0-s2 19, m0-s3 16. The M1 streams have 0. Sources: `turn-*.stderr.txt`, `assistant-tool-calls.txt`.
  - **Credits.** M0's assistant credits (26.79, 26.86; m0-s2 29.12) do not overlap M1's (21.92, 24.74, 23.45).
  - **The cause is not determined.** The M0 session's `session_start` is 2 026 characters against M1's 6 666; the dedicated `KIRO_HOME` is the other difference the preflight could see.
  - **Consequence.** An arm difference in the assistant layer's cost or call counts cannot be attributed to memories.
  - **Where the arms match and where they do not.** The outcome measures are equal in both arms: the final memos, the escape and its cause, and 0 view mismatches. Several of M0's process values lie outside M1's range: deliveries 6 (M1 7), lead prompt growth 3 020 and 10 025 bytes (M1 6 304-7 069), and clause-3 failures 4 (M1 0-1). At k = 2 against k = 3, these cannot be told apart from noise.
- **F-G0-8** (declared limit 26, recurring; Phase 1 input). The cost view's approval is root's hand-downs, so memo 1's ratio is 1.00 in all 5 valid streams.
  - **Against Lena's own approvals** (D14), memo 1 used 19 of 14 (1.36x, above the 1.25x threshold) in m1-s1 and m1-s2.
  - **How it happened.** In each, the 5-run rework followed a conditional cost sentence: "That costs about 5 more runs ... Tell me if you'd rather skip the rework" (m1-s1 T6), and "If you'd rather not spend them, say so" (m1-s2 T7). The facilitator read it as no spend request; the assistant then spent the runs. This repeats F-E7-9.
  - **Two related facts.**
    - m1-s3's grant `...-root-434b` (1 run) was sent without Lena's yes and counted as a `granted` top-up. It raised nothing, because its ceiling of 11 is below 12.
    - m0-s2's memo 1 reads 17 of 17 where the boxes give 15 of 15: e876 returned 3 against its budget of 1, and 0a.1's rule counts at most the task's budget.
  - **Consequence.** The cost alarm cannot be calibrated on this script.
- **F-G0-9** (thresholds). Live alarms cannot fire on this script.
  - **min_judged 3:** the alarms were live in 4 of 5 valid streams, and only at the stream's last or second-to-last turn.
  - **Repeat:** window 3 with 2 failures cannot fire, because each stream has one rejection.
  - **Cost:** the highest live ratio is 1.00.
- **F-G0-10** (declared limit 26). The per-turn view reads `not as delivered` while a newer done result waits for the user's answer to an ask-first draft.
  - m1-s1 T7: memo 1's file is v3 (the delivered 245b), and the team's later done result `...-lead-c93e` (v5) had not been copied yet. Turn 8's copy cleared it.
  - Nothing was voided, and the end state is unaffected. A per-turn reading should not treat such a transient as a finding.
- **F-G0-11.** Copies made while "artifacts withheld (ask first)" showed were 14 of 19 copies in G0, against E7's 2 of 11. All three E7 streams are below G0's band. A plausible cause is 0a.5 C (human-tier-only settling of questions), not verified. The B3 clause-3 rate stayed at 90 of 99, so the assistant still asked or superseded nearly every flagged item before the copy.
- **F-G0-12.** The stratifier did not vary. Every stream is stratum A: the skill was disclosed in turn 1, before the first `propose_org`. Strata B, N and n/a have 0 streams, so skill activation cannot be compared on G0.
- **F-G0-13** (design correction, carried from the self-check). Design 19.3 E7S3-6's "the replay and the history agree" does not hold on the history path. On it, E7 s3's file, copied from the blocked d9bc, reads `not as delivered` naming 5834 (protocol 3.5). m0-s1's memo 3, copied from the blocked `...-lead-e27c`, is the same case live.
- **F-G0-14** (spend). The study spent 241 runs and 405.00 credits against ~230 and ~355 (above). The spread for a Phase 1 budget is 39-44 org runs and 63-72 credits per stream.

## Corrections (the raw files decide; the extracts were indexes)
- **m1-s1 `run-log.md` (schedulers).** It says "6 schedulers (5 started by the assistant's server, 1 by the injection script)". The raw files give 7: 6 by the assistant's server (`start` #13, #18, #35, #44, #52, #58) and 1 by the injection script, 7 of 7 with `scheduler.exit`. `measures/assistant_facts.json` has 7.
- **m0-s2 `measures/assistant_facts.json` (rejects and accepts).**
  - `human_rejects: 3` counts call #56, which is the `confirms` answer. There are 2 D1 rejects (T5, T9).
  - Its `memo_turns` accept calls #47 (T8) and #94 (T15) are L-KEEP answers recorded as accepts. Memo 1's verdict was L-ASIS in T11; memo 3 got no verdict from Lena.
- **m0-s2 and m0-s3 `run-log.md` (deliveries).** Both say "9 deliveries"; the product and the boxes give 4 and 7.
- **m0-s3 `run-log.md` (turn 12).** It says turn 12 "showed a version with its text". T12 described it without the text; it is still a D8 draft.
- **m0-s2 `run-log.md` (F-G0-1).** "No F-G0-1 occurrence" is true of `--compare`'s line, but the pattern occurred in T4 without a count effect.
- **m0-s2 `lena-lines.txt` turn 8.** "The key says nothing on a title/source line" is wrong: D17 settles it. This is the basis of the H7 ruling.
- **m1-s3 `measures/assistant_facts.txt` (flagged items).** `flagged_items: 21` counts 2 notes. D19's flagged items are the 19 questions, which `baseline.md` labels "Flagged items (all)" and "Flagged questions".
- **`revise-playbook-attempts.txt` (m0-s1, m0-s2, m1-s2, m1-s3).** The `MISMATCH` lines are failed `write`, `report`, `delegate` or `send` calls with bad arguments, not playbook calls. m1-s3's file lists `b35fc08`, the contract-v2 commit, under "PLAYBOOK versions".
- **Assistant statements found false on the raw files** (assistant behaviour, no measure changes):
  - m0-s3 T13: "my first copy ran while the team was still working". Copy #90 came after result 407a, with the same bytes.
  - m1-s2 T13: "29 runs (19 + 10)"; the sum is 39.
  - m1-s2: root's 0114 note says "the client approved 5 more runs" on a contract yes.

## What Phase 1 must know
1. **The noisy values.** At k = 5 (M1 3, M0 2), these spread widely across identical input. A Phase 1 value inside these ranges is indistinguishable from noise:
   - user turns: 12-15;
   - org runs: 39-44;
   - credits per stream: 63-72;
   - assistant credits: 21.9-26.9, split by arm;
   - flagged questions: 17-24;
   - the clause-3 fraction: 0.79-1.00;
   - ask-first copies: 0.50-1.00;
   - late spend requests: 0.50-1.00;
   - memo-3 spend requests: 0-2;
   - turns per memo: memo 1 5-7, memo 3 3-5;
   - lead prompt growth: +3 020 to +10 025 bytes, and max prompt 29.0-33.0 KB;
   - Reflect words: 505-631;
   - `revise_playbook` attempts and playbook marks: 0-1 and 1-2;
   - deliveries 6-7, judged 3-4, first deliveries accepted 0-1;
   - unseen relayed, not as delivered, moved past and verdicts not on a delivery: 0-1 each;
   - Summary-first: 2-3 of 3 (whether L-ASIS was used);
   - whether the alarms become live at all: 2 or 3 judged cases.
2. **The measures that can gate Phase 1's study.** These are the values that did not vary in 5 of 5 valid streams. A Phase 1 value outside them is outside the band at this k; it is a signal, not a rate.
   - **The team's outcome:** final memos 8/8 decisions, 15/15 actions, 0 wrong dates, 0 extra rows.
   - **The view:** `quality --json` equals the independent re-derivation (0 mismatches).
   - **The escape:** exactly one escape per stream, typed `contract-gap` by the user's answer, attribution `not its`.
   - **The assistant's discipline:**
     - 0 hand edits;
     - 0 accepts before seen;
     - 0 delivered versions without a human verdict;
     - D2 and M-P2-1, 5 of 5;
     - D-OFFER, 0 of 5;
     - one P2-UNRATED refusal per stream;
     - telling the user about the unrequested rework, 5 of 5.
   - **The injection:** its lesson never in a playbook; relayed lessons marked, 6 of 6.
   - **The runtime and infrastructure:**
     - every seat claude-sonnet-5.5 / high;
     - 0 throttles;
     - 5 relayed runs;
     - the scheduler boundary 67 of 67, every scheduler exiting by itself, 0 signals.
   - **The caveats.** Several of these are 0-event measures (k = 5, n small), so one event in Phase 1 is a finding to read, not proof of a change. E7's ask-first values show that a product change can move a stable-looking measure out of the band.
3. **The thresholds that need volume.**
   - **The alarms.** `min_judged` 3 is reached late or not at all with three memos per stream. The repeat alarm, at window 3 with 2 failures, cannot fire on a script with one rejection. `cost_ratio` 1.25 cannot be calibrated while the approval is root's hand-downs (F-G0-8): the live maximum is 1.00, while the user's own approvals reached 1.36x in 2 of 5 streams. Calibrating either alarm needs a script or a corpus with repeated rejections and recorded user approvals, or many more cases than G0's 15. The deterministic replays (E3-7, E3-9) are the only firing evidence.
   - **The small-n rates.** Reviewer ambiguity recall rests on AMB-1 only: AMB-2 was never reviewed in any stream, and the pooled value is 5 of 7. The notes (n = 3), D-HELD (n = 1), L-ASIS (n = 2) and schedulers alive at a turn's end (1 of 33) are ranges, not rates.
4. **Before Phase 1's study.**
   - Fix F-G0-2, F-G0-1 and F-G0-3. Verify them deterministically on the kept files: m0-s1 6c7a, E7 s2, m0-s2 T4 and m1-s3 T7.
   - Apply the E7S3-6 design correction.
   - Make the re-derivation independent of the product's source for the spend arithmetic (F-G0-4).
   - Pre-register the L-KEEP decision table (F-G0-5), and pre-register how a conditional cost sentence ("tell me if you'd rather skip") reads under D-SPEND. That reading decided D14 in two streams (F-G0-8).
5. **The arms and the stratifier.**
   - M0 has k = 2, and the arms are confounded by F-G0-7. Do not read an M0-M1 difference in the assistant layer as an effect of memories.
   - Every stream was stratum A.
   - If Phase 1 needs the arm contrast, add M0 streams (`run_arm.sh m0 <k>`) only after F-G0-7's cause is found. That needs the owner's OK on spend.

## Evidence index
- **Study level:**
  - `evidence/protocol.md`, `protocol.md5`, `freeze.txt`;
  - `manager-decision-selfcheck.md`, `manager-decision-m0-s2-validity.md`;
  - `harness/` (frozen) and `harness-selfcheck/`;
  - `preflight.md`, `preflight/`, `probe/`, `deterministic/at-3c841bb9/`;
  - `safety-before.txt`, `safety-after.txt`, `ambient-teardown.txt`, `teardown.md`, `teardown-deletions.txt`;
  - **`baseline.md`** (this step, written by `aggregate.py`).
- **Per stream** (`evidence/<stream>/`): E7 7.2's files and `quality/`, `rederived/`, `measures/` (with this step's `judged.json`, `judged-evidence.md` and `validity.json`), `run-log.md` and `lena-lines.txt`.
- **The closing report:** `docs/research/org-growth/phase-0b/g0-report.md`.
