# P1 stage-1 gate (step 6, `stage-gate`, workflow `wf_9e81d83f470f71a8`)

Written 2026-10-27, about 22:55 UTC, from the recorded evidence only. No stream and no self-check was re-run. Paths are relative to
`studies/P1-itemized-playbook/evidence/` unless absolute. "Design n" is `docs/design/org-growth-phase-1.md` at `8bf7c69b`.

**Gates of this step** (protocol 0):
- `md5 -q protocol.md` = `70237b0f3a829795a89d81c8eba7a7d6` = `protocol.md5`.
- `protocol-amendment-1.md` = `8a203c5efd7445c55096858320ef46e5` = its `.md5`.
- `harness/MD5SUMS`: 64 lines, 0 mismatches; its md5 is `d21508978d71e6d805f1760b25acb1b6`.
- **Product freeze.** HEAD = `8bf7c69bb933bf2e1ecda5dc4ddbefde41eba565` on `main`. At 22:40:58Z,
  `git -C /Volumes/workspace/hirearchy diff --stat 8bf7c69b HEAD -- src skills pyproject.toml uv.lock` printed nothing (0 lines, exit 0).
  Both streams' `setup.txt` record it empty before turn 1 and after the last turn.
- `git diff docs/design/org-growth-phase-1.md` is the one 21.6 line.

## Result

**The 18.7 stop rule passes.** Protocol 11 states it: stage 2 starts only if both stage-1 streams are valid (no H rule broken, the probe
passed, `memories.db` unchanged during and between them) and neither cost more than 185 credits. The two parts:
- **Validity.** F1 and I1 are both valid under the frozen rules and the manager's rulings (section 1).
- **Cost.** F1 cost **100.23** credits and I1 **121.49**. Both are at or below 185.00.

So stage 2 (I2, F2, F3, I3) may start on the manager's yes.

**Spend so far,** as 18.7 counts it (the preflight and the streams): **230.52 credits and 137 org runs**. That is below the stage-1 approval
of about 260-390 credits and 144-208 org runs. The figures do not include the workflow steps' own sessions.

Section 5 lists four items for the manager. None of them changes the stop rule. One of them decides whether stage 2 can give G1 (arm I) a
PASS.

## 1. Validity of F1 and I1

| Rule | F1 (arm F) | I1 (arm I) |
|---|---|---|
| H1, assistant call failures | 26 of 26 turns exit 0, each `stop end_turn status success` (`turn-times.txt`, `cost.txt`); no retry | 24 of 24, the same |
| H2, skill and server | workspace, repo and global SKILL.md `b1023863...`, 125 lines (`skill-check.txt` OK); the session loaded the workspace copy; profile `ORG_ROOT` = `S/org` | the same |
| H3, ambient context | workspace `cli.json` `05d30ccb...`; 0 `<steering-files>`, 0 "Workflow Orchestration" in the session; skills listings unchanged in all 54 ambient snapshots. **No `<memories>` block in the session start** (section 4.3) | the same in all 50 snapshots, except that the session start **has** the `<memories>` block (section 4.3). Protocol 8: a memory index, present or absent, is not H3 |
| H4, models and effort | `model_check.sh all` OK: 65 of 65 run-log `# cmd:` lines have one `--model claude-sonnet-5.5` and one `--effort high`; 26 of 26 invocations `--effort high`; session `claude-sonnet-5.5` / `high`; 57 of 57 `reasoningModelId` `qdev::claude-sonnet-5.5`. Effort warnings: section 4.4 | OK: 70 of 70 run logs, 24 of 24 invocations, session `claude-sonnet-5.5` / `high`. Effort warnings: section 4.4 |
| H5, the injection | at the end of turn 5, after memo 1's first delivery (copy at 19:52); title and note md5s match; one relayed request, `revises` = memo 1's delivered task; 5 window runs (`injection/`) | at the end of turn 4, after memo 1's first delivery (copy at 21:38); the same checks match |
| H6, collision or interference | event actors are only the scheduler, the org agents, root's MCP calls, the harness's CLI snapshots and the lock hook (with the runtime's note to the owner); no overlap (F1 19:26:33-21:21:10Z, I1 21:24:35-22:38:30Z); freeze diff empty; kiro-cli 2.33.0 before and after; `observe-check.txt` all pass | the same; `observe-check.txt` all pass |
| H7, facilitator error that changed the course | the owner-form slip at turns 13 and 15 was ruled not H7 (`manager-decision-f1-owner-form.md`; its condition is recorded true). Flagged readings are left to the scorer, and none changed the course on the record: D-SPEND was applied at turns 5 and 8, H6 was used over L-ASIS at turn 6 (protocol 4.2 "always H6"), and D-SPEND was not applied at turn 13. Turn 13 used no org run (30 runs after turn 12, 30 after turn 13), and Lena's K18 answer chose the version that cost nothing. The turn-1 display slip changed nothing (`harness-failures/turn-01-display.txt`) | the turn-1 questions were mapped by ruling (a) to K20 and K3 (`manager-decision-row-I1-t1.md`). Flagged readings: at turn 18, K36 was used alone for a redo offer that named runs, and K36 declines that redo; at turn 9, K19 was used with K14. The turn-15 prompt-file timing left the line exact |
| H8, engine or infrastructure | 65 of 65 run logs `# exit 0`, `[run finished] success (end_turn)`; no throttle and no kiro failure line | 70 of 70, the same |
| H-LOCK (arm F) | **ok**. The hook ran after turn 3. Check 1 passed (the reply names the lock), and so did check 2 (`SERVICE.md` v2 `locked: true`). Check 3 failed only on the `from:` clause (the note is `from: runtime`). The ruling `manager-decision-lock-check3.md` covers that, and `lock/check3-ruling.txt` records its four facts as yes. `h-lock-before.txt`: only root's v1 playbook. `lock-held.txt`: v2-v7 `locked: true` after every turn. `h-lock-after.txt`: ok, no owner version. The owner made 0 `revise_playbook` attempts, so PB-LOCKED was never exercised (reported) | n/a: arm I runs no hook |
| The probe (18.3 item 2) | `PROBE: PASS` at attempt 2, after amendment H-A1, before F1's first turn (`preflight.md` 10, `probe/compare.txt`). Positive control: v2 in F, v1 in I. Lock checks 3 of 3 in both F repetitions | the same probe |
| Empty-argument calls (18.3 item 3) | 0 in the session store; 0 `is not available` in stderr; 0 in the tool-call log (`empty-calls.txt`) | 0, 0, 0. Both streams of the pair have 0, so neither is "invalid for the arm contrast" |
| `memories.db` | before `f0aaf02a8a216c3a291a253d2c52d461`, after the same (`memories-md5-*.txt`, `memories-db.txt`). F1 is the first stream; the preflight end value was the same | the gate found it unchanged since F1's end; before and after are the same `f0aaf02a...`. It is still `f0aaf02a...` at this gate |
| Owner's files | `safety-diff.txt` shows only labels, directory mtimes and the new sandbox; profile created and deleted with a record; `~/.kiro/agents` holds its 7 entries | the same |

The manager also ruled on F1's turns 17-23, where the per-turn snapshots ran at the same time as the turns. The ruling keeps F1 VALID
(`manager-decision-f1-after-turn-timing.md`). Its condition table is recorded: every snapshot of turns 17-23 is a clean end-of-turn-(N-1)
reading, and turn 23 was retaken in sequence. I1 ran every `after_turn.sh` in sequence and checked it each turn.

**Verdict: F1 VALID, I1 VALID.**

## 2. Credits and org runs against 185

| Stream | User turns | Org runs (all run logs) | Assistant credits | Org-run credits | `credits.txt` | Against 185.00 |
|---|---|---|---|---|---|---|
| F1 | 26 | 65 (60 + 5 in the injection window); 65 of 65 sessions matched | 39.9254 | 60.3033 | **100.23** | not over (84.77 under) |
| I1 | 24 | 70 (65 + 5); 70 of 70 matched | 52.6583 | 68.8336 | **121.49** | not over (63.51 under) |

- Each `credits.txt` line equals `cost.txt`'s `total assistant credits` plus its `per-model credits (all runs)`, rounded:
  39.9254 + 60.3033 = 100.2287, and 52.6583 + 68.8336 = 121.4919.
- No run lacked a matched session, so neither figure is flagged.
- Org runs are 65 and 70 against 18.7's 71-103 and the run cap of 130; no `CAP:` line was printed.
- Stage-1 total: the preflight 8.80 (the two probe attempts 6.17, the other checks 2.63) + 100.23 + 121.49 = **230.52 credits**, and
  2 + 65 + 70 = **137 org runs**.
- At stage 1's per-stream cost, stage 2's four streams would cost about 400-490 credits. Its approval is 480-740.

## 3. G1 and G2 so far (the frozen `guarantees.py` outputs; mechanical, no final verdict)

| Check | F1 (arm F; G1 reported only, vacuous by 18.5) | I1 (arm I) |
|---|---|---|
| G1(a) | PASS (every item is v1 `kept`) | PASS. A = P11 went `new` to `kept`, kept at turn 17. B = P12 went `new` to `warning` (turn 17) to `retired` (turn 21) |
| G1(b) | VACUOUS (no B) | PASS, ran live. P12 was retired `by: runtime (watch)` (v5, 22:29:12.257Z) in the call that recorded R4's answer (the second scripted answer, 22:29:12.198Z, turn 21), with `restores` 0 as expected. B had been edited by its owner into [full]'s words after R3 (O8, as 18.4.1 pre-registers) |
| G1(c) | PASS (no gated op) | PASS (3 `admitted: c` versions) |
| G1(d) | NOT DETERMINED (judged reading; the keyword screen found 0 hits) | the same |
| G1(e) | VACUOUS (no B) | PASS (B `retired` at the end) |
| G1(f) | PASS: 26 snapshots, 0 mismatches | **FAIL** on 21 pinned `since` mismatches (section 4.2). The states and the other pinned keys are equal. (f2) holds: A `kept` and B `retired` by `runtime (watch)`, in the product and in the re-derivation. 0 snapshots unread; 0 services mismatches |
| G2(a) | recorded PASS, but on 0 parsed Lena turns (section 4.1). Read in memory with the frozen code: **PASS, 4 of 4** (H6 t6 -> R1, L-PLANT t11 -> R2, L-MIND t18 -> R3, L-GAP t22 -> R4) | recorded PASS on 0 parsed turns. In memory: **PASS, 4 of 4** (t5 R1, t10 R2, t16 R3, t20 R4) |
| G2(b) | PASS. Each of R1-R4 was answered by a contract version (v3, v5, v6, v7) 1-2 minutes after its note and before the next new request; memo 6 had no rejection | PASS. R1-R4 were answered by v2-v5 before the next new request |
| G2(c) | PASS. REQUEST-UNANSWERED 0, FEEDBACK-UNANSWERED 0, exception uses 0, relayed accepts while unanswered 0, one-off delegates 0 | the same, all 0 |

- **Orders in I1** (`orders.json`): O1 (a); O2 by `define_service(answers=)`, related to B; base case, not O10; O8 (a gated edit after R4);
  no extra rejection.
- **Pace in I1** (18.4.1): A kept at T17 (expected T16-T21), B retired at T21 (expected T20-T27), memo 6 accepted at T24 (expected
  T24-T32).
- **Ids in this table.** The script's R4 and R5 are the streams' R3 and R4 (`guarantees/roles.txt`; no disagreement with the stream steps'
  `roles.txt`).

## 4. Self-check and view mismatches

**The self-check** (`harness-selfcheck/SELFCHECK.md`, the H-A1 run): 17 of 17 parts, 206 tests passed, no product defect recorded. It was not
re-run here.

### 4.1 G2(a) read no Lena line in either stream
- **What protocol 4.2 requires** (`protocol.md:239`): the line form `turn <n> | rules <ids> | table rows ... | facts: ...`.
- **What both stream steps wrote:** `turn <n> | <ids> | table rows ...`, without the word `rules`.
- **How the frozen parser fails.** `harness/guarantees.py:80` matches `^turn (\d+) \| rules? ...`. It returns no turn, and `g2` then passes
  on an empty list, so `g2.json` shows `"rejections": []` in F1 and I1.
- **The in-memory reading.** I loaded the frozen module with `python3 -B`, inserted `rules ` into each line in memory and wrote no file.
  The frozen G2(a) then reads PASS in both streams, one human-tier note per scripted rejection on its memo's case.
- **This is a record-form slip.** It did not change the course and is not H7.

### 4.2 I1's G1(f) FAIL rests only on the precision of `since`
- **The values.** The re-derivation gives the watch start with microseconds (`2026-10-27T21:45:58.699651+00:00`, from the playbook
  version's `revised`). The product's `quality --json` gives whole seconds (`2026-10-27T21:45:58Z`).
- **The count.** P11 differs at turns 6-16 and P12 at turns 11-20: 21 pinned mismatches. 18 more are unpinned: `since` after each item
  left its watch, plus P12's `waiting` and `clean` after its retire.
- **The product side.** `src/hirearchy/progress/_quality_render.py:446-447, 478` renders `since` with `%Y-%m-%dT%H:%M:%SZ`, the one time
  format of the quality JSON. Design 14.4 names the key and gives no precision.
- **The harness side.** `harness/rederive_watch.py:1172-1174` normalises `since` with `d.replace(microsecond=d.microsecond)`, which does
  nothing, so the comparison is exact to the microsecond.
- **How protocol 12.1 (f1) reads it.** The scorer either traces it to the frozen harness (G1(f) NOT DETERMINED for I1) or reads it as a
  product defect (FAIL). This step gives no verdict.
- **It will recur.** Every arm-I stream on this harness will show it, because every watch start falls on a fractional second.

### 4.3 The memories block differs between F1 and I1
- **Which sessions had it.** I1's session start holds the owner's `<memories>` block (5714 characters, the same as the preflight ambient
  probe's). F1's has none, and neither do the four probe sessions.
- **The rest is equal.** With the block removed, F1's and I1's session starts are equal after masking.
- **It is not the arm.** The probe's arm-I sessions lacked the block too, so the presence varies from session to session in the engine.
  `memories.db` was unchanged throughout.
- **It is not an H rule.** Protocol 8 says a memory index, present or absent, is not H3. It also changes neither the probe's PASS (all
  four probe sessions were equal) nor the mechanical guarantees.
- **What it breaks.** Design 18.2 (lines 1439-1440) and 18.3 assume "the same owner's memories index" in both arms. So the F1/I1
  assistant-layer contrast is confounded: assistant credits 39.93 against 52.66, call counts and behaviour.

### 4.4 Effort warnings
- **Org runs.** 8 of F1's 65 and 7 of I1's 70 run logs say `[warn] failed to set effort 'high': model 'claude-sonnet-5.5' offers no
  effort levels`. Their sessions record no `effortLevel`.
- **The assistant.** F1's turn-23 call logged `[warn] failed to set effort 'high': the engine did not load its model list in time`. The
  session records `effortLevel: high`, and nothing records effort per turn.
- **Not H4 under the frozen check.** E7 4.3, adopted by protocol 2.3 (`script/e7-protocol.md:381-388`), checks the `# cmd:` line (all
  135 have `--effort high`) and the session's `effortLevel` "when the session file records one".
- **Precedent.** E6, E7 and G0 reported the same pattern (G0: 41 run logs) with their streams valid.

## 5. Items for the manager before stage 2 (none changes the stop rule)

1. **G1(f) and `since` (4.2).** Without a decision, G1 (arm I) cannot read PASS: I1 reads NOT DETERMINED or FAIL, and I2 and I3 will show
   the same mismatch. Two routes:
   - a harness amendment for the streams not yet started (protocol 0), approved and frozen before I2's first turn, that compares `since`
     at the product's whole-second precision;
   - or a ruling on how the scorer reads this mismatch in all arm-I streams.
2. **G2(a)'s line form (4.1).**
   - The stage-2 stream steps should write `turn <n> | rules <ids> | table rows ... | facts: ...` exactly.
   - The scorer must re-read F1's and I1's G2(a) with the line form, or the recorded PASS stays vacuous.
3. **The memories block (4.3).** Stage-2 pairs may differ the same way. The scorer can read the presence of the block per stream from each
   session copy. How the assistant-layer contrast treats a pair that differs is the manager's call. The frozen protocol has no rule for it.
4. **Effort (4.4).** The owner requires every seat at high. The engine says about 1 in 9 org runs could not set it. This is not an H rule
   break under the frozen check. It is reported here so the manager can decide whether it matters for this study.

## 6. What this step did
- It read the brief; design 3, 8, 18, 21.1, 24 and 25 at `8bf7c69b`; the protocol, the amendment, `preflight.md`, the manager's decisions,
  and F1's and I1's evidence.
- It ran read-only checks: md5s, greps, and the frozen `guarantees.py` in memory with `-B` (no `__pycache__` was written).
- It wrote this file. It also wrote a scratch copy of the design at `8bf7c69b` to `/tmp/p1-gate-design.md` (`git show`) and deleted it
  after use.
- It did not touch the owner's `~/.kiro` (only md5s and the agents listing were read), `/Users/aminalizadeh/organization` or
  `~/.kiro/skills/`. Nothing was staged, committed or pushed. No credential was read.
- It did not write `manager-decision-stage-2.md`. `next_stream.sh` needs that file as well as this one before I2.

**Manager's answer (2026-10-27): GO to stage 2,** `manager-decision-stage-1-gate.md` (md5 `cca3acd3159f86758058d91093ff7600`; the four items ruled there; stage-2 streams under `manager-standing-rules-streams.md`).
