# P2 pre-registration: the manager's closing pass (the rulings C1-C5 on F38-F42 of review 3)

The binding rulings are in `manager-decision-prereg-loop.md`, in the section "The loop is CLOSED by decision after iteration 3". This pass
applies C1-C5 as they are worded and makes no other change. Where an entry says a reading was needed, the reading is flagged. Nothing is
frozen: no `protocol.md5`, no `MD5SUMS`, no `freeze.txt`. No stream, no probe with a kiro-cli session and no live org run took place. No
product file was edited. I opened no product source file (`harness/CHANGES.md`, "Manager closing pass").

`EV` = `studies/P2-retro-and-growth/evidence/`, `H` = `EV/harness/`. Line numbers are 1-based, in the files as they stand after this pass.
Test-first: for each code change I added or adjusted the case first, ran it and saw it fail (RED), then made the change and ran it again
(GREEN). Each RED and GREEN line below is quoted from the output of a run.

**Self-check:** `SELFCHECK: 19 of 19 parts passed` (`EV/harness-selfcheck/selfcheck-summary.txt`, run started 2026-10-29T09:51:20Z,
after the last code edit). It has one more part than before: 5c, C4's trap case.
**The owner's global skill** `~/.kiro/skills/hirearchy/SKILL.md`: md5 `443e1bc4911aa4d6aaa6457e78f673c1` before the pass, before the
self-check, after the self-check and at the end. `~/.kiro/agents` held 7 entries before and after the self-check.

## C1 (F38, MEDIUM): final memos and unjudged versions under the cut rule. Done.
**What changed**
- `H/score_p2.py:125-130`: new `last_verdict(lines, memo)`. It runs `lena_lines.verdict_after` over the last Lena line that judges the
  memo.
- `H/score_p2.py:132-181`: `delivered_check(versions, finals, lines, end)`.
  - A final memo keeps the rule only when its last judging line is ACCEPT or L-ASIS. The rule is 0 extra rows and 0 wrong dates, with
    the trap row included unless the memo was accepted under L-ASIS.
  - When that line is a rejection, or no line judged the memo, and for a copied version that no later line judged:
    - in a cut stream: `NOT DETERMINED (cut at turn <n>: the memo's last version was rejected or not judged: ...)`;
    - with no `end.txt`: `NOT DETERMINED (FAIL-CLOSED: the stream's end is not recorded: ...)`;
    - in a `retro-2-done` stream: held to the rule as written, so it reads FAIL when it breaks the rule.
  - A FAIL anywhere stands over a NOT DETERMINED.
  - The function returns `not_determined` and `verdict` as well.
- `H/score_p2.py:213-220`: `score()` passes `extract_p2.end_of(stream)`, the one end reader the checks use. `score_p2.json`
  `p2_delivered_versions` gains `not_determined`, `verdict` and `end`. The docstring's item 4 is updated (`:14-15`).
- `H/gate_p1.py:342-379`: carries score_p2's NOT DETERMINED into `delivered versions (P2's form)` as it reads, so the cut form has no
  `FAIL-CLOSED:` prefix. The stage gate (`stage_gate.py:58-62`, unchanged) lists such a value as information. A presented version that no
  later line judged follows the same rule, through `extract_p2.end_of`.
- `EV/protocol.md`: 12.3 (`:982-992`) states the rule. 16 item 10 (`:1360-1373`) states the rule and its reason: a slip Lena rejected is
  the contract loop working, and a cut stream's unfinished memo is not a regression. 13.3 items 4 and 8 (`:1201-1203`, `:1219-1221`) list
  the new cases.

**Cases**
- `score_p2.py --selfcheck` (`H/score_p2.py:258-289`):
  - "C1: a cut stream whose memo-4 final is the TRAP-N-rejected version: NOT DETERMINED (cut), not FAIL";
  - "C1: a cut stream whose last version was never judged and has a slip: NOT DETERMINED (cut), not FAIL";
  - "C1: a retro-2-done stream whose accepted final has an extra row: FAIL";
  - "C1: the same TRAP-N-rejected final with no end.txt: NOT DETERMINED (FAIL-CLOSED: the stream's end is not recorded)".
  - The three F26 cases now pass a `retro-2-done` end, since they describe a finished stream.
  - RED: `score_p2 selfcheck: 6 of 13 ok`. The new four-argument call did not exist.
  - The old code on the same inputs: `{'ok': False, 'bad': ['final 2026-10-26: wrong 1, extra 0'], ...}` and `{'ok': False, 'bad':
    ['2026-11-09 v3 (not judged): wrong 1, extra 0'], ...}`. Both are F38's FAIL.
  - GREEN: `score_p2 selfcheck: 13 of 13 ok`.
- `gate_p1.py --selfcheck` (`H/gate_p1_cases.py:175-195`):
  - "C1: a cut stream whose memo-4 final was rejected: score_p2's NOT DETERMINED (cut) is carried, with no FAIL-CLOSED prefix";
  - "C1: the same with no end.txt: NOT DETERMINED (FAIL-CLOSED: ...)";
  - "C1: a version presented in the cut turn with a slip and never judged: NOT DETERMINED (cut), not FAIL".
  - RED: `gate_p1 selfcheck: 24 of 27 ok` (got `PASS`, `PASS` and `FAIL`). GREEN: `gate_p1 selfcheck: 27 of 27 ok`.

**Readings (flagged)**
- **"in a `retro-2-done` stream it reads FAIL as written".** I read "as written" as section 12's convention ("the step reads FAIL, as
  written below"). The final memo is held to 12.3's rule as written and reads FAIL when it breaks the rule. A clean final there passes.
  This also matches Resolve item 3's "otherwise it keeps the rule".
- **A never-judged version with no `end.txt`.** Resolve item 3 says "otherwise it keeps the rule". The manager's ruling says "A
  never-judged version follows the same rule" as finals, and the ruling binds. So such a version reads NOT DETERMINED (FAIL-CLOSED) when the
  end is not recorded, and keeps the rule only in a `retro-2-done` stream.
- **Presented versions.** 12.3 has one rule for versions delivered by copy and by presentation. So `gate_p1.py` applies item 3 to a
  presented version that no line judged, as well as carrying score_p2's result.
- **A fourth score_p2 case** (no `end.txt`) beyond the three the ruling names. It covers the second branch of Resolve item 2.
- The NOT DETERMINED is applied whatever the item's content, as the ruling words it. A clean rejected or unjudged final in a cut stream
  also reads NOT DETERMINED (cut).

## C2 (F39, LOW): the arm-C open form of K33. Done.
**What changed**
- `EV/protocol.md:509` (row K33): adds the arm-C form. In arm C, an either/or or open question about the order of the changes she said yes
  to (K51, K52) gets `In the order you proposed, one at a time.`, recorded `K33 (arm C open form)`, rule `ANSWER`.
- 16 item 37 (`:1485-1489`) names it, with the reason: without it the question has no row, and after R1's first turn it would end the C
  stream by ruling (b).
- Standing rule 6 (`EV/standing-rules-streams.md:33-34`) names it.

**Cases.** `lena_lines.py` has no table of row ids: rows are free text, and only rule ids are checked against `RULE`. So no row had to be
added and no code changed. I added one confirming case, "C2: the row record `K33 (arm C open form)` reads as one row, K33, with rule ANSWER
known" (`H/lena_lines.py:281-283`). It passed on the unchanged parser. It is a check, not a RED/GREEN pair.

## C3 (F40, LOW): an arm-C offer is answered as in arm R. Done.
**What changed**
- `EV/protocol.md`, the table rows:
  - K40 (`:516`) is marked both arms;
  - K41 (`:517`) is marked **both arms**: in arm C that line is then the arm-C turn, and L3 carries no RETRO-ASK;
  - K41a (`:518`) is marked both arms, "arm C: after the arm-C turn".
- `EV/protocol.md`, 4.6:
  - the arm-C bullet (`:391-396`) changes "no offer can come" to "an offer is answered as in arm R": K40 before L0; K41 in L1 or L2,
    which is then the arm-C turn with no RETRO-ASK at L3; K41a after it. Each offer is recorded in `retro-offers.txt` as the arm-C
    assistant's own offer. RETRO-ASK at L3 is the fallback when no offer came.
  - "Between the retros" (`:403-407`) now reads both arms.
- `EV/protocol.md`, 16 item 11 (`:1374-1382`) gives the reason. One facilitator rule for both arms keeps the pair comparable, and the
  facilitator never has to choose between K41 and the L3 rule. RETRO-ASK at L3 stays the fallback when no offer came.
- `EV/standing-rules-streams.md`, rule 15 (`:70-74`): "arm C: always L3" is replaced by the same rule.
- `H/lena_lines.py:147-158`: new `retro1_expected(lines, offers)`, one rule for both arms. An offer answered at or before L0 gets
  RETRO-NOT-NOW. An offer before L1 or L2 gets RETRO-YES in the first such line, which is retro 1 (the arm-C turn) with no RETRO-ASK. With
  no such offer, L3 gets RETRO-ASK.
- `H/lena_lines.py:120-131` (`retro_places`): retro 1's RETRO-YES is accepted only in L1 or L2, and its RETRO-ASK only at L3. Before, the
  first RETRO-YES or RETRO-ASK anywhere in L1-L3 was accepted.
- 13.3 item 3 (`:1196-1198`) lists the cases.

**Cases** (`H/lena_lines.py:262-280`):
- "C3: an arm-C offer before L1 gets RETRO-YES at L1 (the arm-C turn) and no RETRO-ASK at L3; a RETRO-ASK there is misplaced";
- "C3: no offer: RETRO-ASK at L3 (turn 13), and a RETRO-ASK at L1 is misplaced";
- "C3: an arm-C offer before L0 gets RETRO-NOT-NOW (K40), and retro 1 then falls back to RETRO-ASK at L3".
- RED 1: `MISMATCH  C3: retro1_expected (name 'retro1_expected' is not defined)`, `lena_lines selfcheck: 21 of 22 ok`.
- RED 2, after adding `retro1_expected` and before tightening `retro_places`: `MISMATCH  C3: no offer: RETRO-ASK at L3 (turn 13), and a
  RETRO-ASK at L1 is misplaced`, `lena_lines selfcheck: 23 of 24 ok`.
- GREEN: `lena_lines selfcheck: 24 of 24 ok`. Every earlier case is unchanged and passes, and so do the dry runs' L1 RETRO-YES lines.

**Readings (flagged)**
- **K40, K41a, "Between the retros" and standing rule 15.** The ruling names only K41's mark, 4.6's sentence and 16 item 11. But "the
  same rows as arm R's: K40 before L0 ... K41a after it" cannot hold while K40 and K41a read "arm R". So those rows, 4.6's "Between the
  retros" ("the pairing with arm C, which gets no line there") and standing rule 15 ("arm C: always L3") were changed to the same rule.
- **`offers`.** `retro-offers.txt` has no machine-readable format pre-registered, so I added no parser. `retro1_expected` takes the turns
  of the Lena lines that answer an offering reply. The table rows record the answers (K40, K41, K41a).

## C4 (F41, LOW): the signal traps stop the drivers. Done.
**What changed**
- `H/probe.sh:49-51`: `trap 'cleanup' EXIT` plus `trap 'cleanup; exit 130' INT TERM`. The reset at `:74` (`trap - EXIT INT TERM`) is
  unchanged. `cleanup` is idempotent (it clears `CREATED` and `MOVED`), so a second run from the EXIT trap does nothing.
- `H/setup_stream.sh:62-63`: `trap 'cleanup; exit 4' INT TERM`.
- `H/selfcheck.sh:110-130`: new part 5c, `trap_case`, with the header updated (`:7-8`). For each driver, it builds a stub zsh script from
  that driver's own `trap '...'` lines, read from the file. The stub is sent TERM from outside while it runs, and must run its cleanup and
  exit 130 (probe) or 4 (setup) without running its next command.
- 13.3 item 14 (`EV/protocol.md:1262-1264`) lists the case.

**Case** "signal traps stop the drivers (C4)" (`EV/harness-selfcheck/traps.out`):
- RED (the function run alone on the old drivers):
  - `probe.sh: trap lines [trap 'cleanup' EXIT INT TERM;] TERM -> exit 0, log [cleanup-ran next-command-ran cleanup-ran ]`;
  - `setup_stream.sh: trap lines [trap 'cleanup' INT TERM;] TERM -> exit 0, log [cleanup-ran next-command-ran ]`;
  - `trap cases: FAILED`.
- GREEN:
  - `probe.sh: trap lines [trap 'cleanup' EXIT;trap 'cleanup; exit 130' INT TERM;] TERM -> exit 130, log [cleanup-ran cleanup-ran ]`;
  - `setup_stream.sh: trap lines [trap 'cleanup; exit 4' INT TERM;] TERM -> exit 4, log [cleanup-ran ]`;
  - `trap cases: 2 of 2 ok`, and in the full self-check `PASS  signal traps stop the drivers (C4) (trap cases: 2 of 2 ok)`.
- `zsh -n` passes on both drivers.

## C5 (F42, LOW): `score_stream.sh` runs in the dry run. Done, with a harness bug found and fixed.
**What changed**
- `H/score_stream.sh:3-4, 16`: a `selfcheck-*` label takes its evidence folder from `P2_EVDIR`, as `copy_org_evidence.sh:17` does.
  Stream labels are unchanged.
- `H/dryrun.sh:274-295` runs `zsh $H0/score_stream.sh $LABEL` in both arms in place of the four direct calls: `extract_p2.py --checks`,
  `watch_views.sh`, `score_p2.py` and `gate_p1.py`. The old calls at the former `:274-290` are removed. `:312-315` copy the steps'
  outputs where the later checks read them, and the header (`:14`) is updated. The checks:
  - `score-steps.txt` lists four `exit 0` lines (`:279`);
  - in arm R, `--am-time` is passed when the constructed `lena-lines.txt` holds an A-M line, or left out when none exists (`:280-285`).
- 13.3 items 15 and 16 (`:1289-1291`) list the checks.
- **Harness bug found and fixed.** The constructed dry-run lines hold no A-M line, so only the "left out" branch runs. I also ran the other
  branch on a scratch copy and found that `score_stream.sh` passed the A-M line's turn number, not its turn start.
  - RED: `exit 0: python3 -B .../score_p2.py ... --am-time 10 ...`.
  - The fix (`H/score_stream.sh:29`): `m.group(2)`, the time, in place of `m.group(1)`, the turn.
  - Arm R's dry run now keeps this branch as a case (`H/dryrun.sh:286-294`). It runs `score_stream.sh` on a scratch copy with an A-M
    line added and checks `--am-time` equals that turn's start in `turn-times.txt`.
  - This case goes beyond the ruling's words. I added it because the fix needed a case.

**Cases**
- `score_stream.sh` on a copy of the last dry run's arm-R evidence, before the `P2_EVDIR` change. RED: `score_stream.sh:
  .../evidence/selfcheck-R is not a stream's evidence folder`, exit 2, no `score-steps.txt` (the dry run's check would read ` of `).
  GREEN: four `exit 0:` lines, `check: 4 of 4`.
- The A-M branch case on the scratch copy:
  - RED (`m.group(1)`): `MISMATCH ... expected --am-time 2026-10-29T08:38:08.098095+00:00, got --am-time 10`;
  - GREEN: `ok ... (--am-time 2026-10-29T08:38:08.098095+00:00)`.
- In the full self-check:
  - `dryrun-R/dryrun.txt:65-68`: `ok  score_stream.sh exit (0)`, `ok  score_stream.sh: score-steps.txt lists four steps, each exit 0 (4
    of 4)`, `ok  score_stream.sh: --am-time left out (the constructed lena-lines.txt holds no A-M line) (left out)`, `ok
    score_stream.sh: --am-time passed as the A-M line's turn start (scratch copy with an A-M line) (--am-time
    2026-10-29T09:52:39.169155+00:00)`;
  - `dryrun-C/dryrun.txt:14-15`: `ok  score_stream.sh exit (0)` and `(4 of 4)`;
  - both dry runs: `0 mismatch(es)`.

## Other records
- `H/CHANGES.md`: the section "Manager closing pass", with the independence statement.
- `EV/harness-selfcheck/SELFCHECK.md`: the section "The manager's closing pass".
- `EV/protocol.md` 17: one paragraph naming this pass.
- **Not a product defect, and not new.** In both dry runs, `delivered versions (P2's form)` reads `NOT DETERMINED (FAIL-CLOSED: no delivered
  version was scored (0 of 0))`, because the construction copies no memo version. The old `score_p2.py` and `gate_p1.py`, run on the new
  dry-run evidence, give the same line. The dry run does not check this measure.
- **Files changed:** `EV/protocol.md`, `EV/standing-rules-streams.md`, `H/score_p2.py`, `H/gate_p1.py`, `H/gate_p1_cases.py`,
  `H/lena_lines.py`, `H/probe.sh`, `H/setup_stream.sh`, `H/selfcheck.sh`, `H/score_stream.sh`, `H/dryrun.sh`, `H/CHANGES.md`,
  `EV/harness-selfcheck/SELFCHECK.md`, and the self-check outputs under `EV/harness-selfcheck/`. This file is new.

**Final:** `SELFCHECK: 19 of 19 parts passed`. Skill md5 before `443e1bc4911aa4d6aaa6457e78f673c1`, after
`443e1bc4911aa4d6aaa6457e78f673c1`.
