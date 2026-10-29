# P2 stage-1 gate (protocol 11; design 17.6's stop rule; step 6 `stage-gate` of workflow `wf_8ee5197e04b8ee7c`)

Written 2026-10-29, 14:46Z-15:10Z. Facts and mechanical readings only; no final verdict (that is step 12's). Paths are relative to
`studies/P2-retro-and-growth/evidence/` (`EV`). No stream, test suite or product call was run. No frozen file changed.

**Result: `STAGE-1 STOP RULE: STOP AND REPORT`** (`stage-1-gate-inputs.json`). Only item 3 holds: four `FAIL-CLOSED` readings, all
from two harness reader defects that show in both streams (section 5). Items 1, 2 and 4 do not hold. Separately, P2-X1 already reads
FAIL in R1 (section 8).

## 1. What this step ran, in protocol 11's order
1. `zsh harness/skill_move.sh recover`: `no unrestored move; global skill: in place, md5 443e1bc4911aa4d6aaa6457e78f673c1`. No `RECOVERED` line.
2. The md5 gate (`arm.sh` `md5gate_ok`: `protocol.md` `31bc856c...`, the standing rules, both amendment-1 files, 80 `MD5SUMS` lines): OK at the
   start and again at the end. Both freezes: REPO_R HEAD `3d6b28aa...`, empty product diff; REPO_C HEAD `aac6af1b...`, clean.
3. `zsh harness/score_stream.sh R1`, then `C1`: 0 failed commands each (`R1/score-steps.txt`, `C1/score-steps.txt`). They wrote `p2/<check>.json`,
   `p2/verdicts.txt`, `p2/gate_p1.json`, `rederived/p2/`, `watch-views/`, `watch/` and `measures/score_p2*` and `measures/p1/` in each stream.
4. `python3 -B harness/stage_gate.py EV` -> `stage-1-gate-inputs.json`.
   - My first run passed `.` as EV. That relative path empties the 7.2 window (section 6.3).
   - I re-ran it with the absolute EV that protocol 11 and `arm.sh` give. The kept `stage-1-gate-inputs.json` and
     `R1/rederived/p2/gate-retro1/` come from the absolute run. Item 2 reads the same in both runs.
5. Spot checks were in-memory calls of the frozen readers (`rederive_p2`, `rederive_watch`, `lena_lines`, `extract_mechanical.detect`).
   - One import without `-B` wrote `harness/__pycache__/extract_mechanical.cpython-311.pyc`. I deleted it.
   - `MD5SUMS` lists no cache file, and the md5 gate still passes.

## 2. The stop rule, item by item
| Item | Reading | Holds? |
|---|---|---|
| 1. a stream over 250.00 credits | R1 116.82, C1 102.76 | no |
| 2. R1's retro 1 lacks `service` while `service_due`, or lacks `checker-add` while `checker_due` | B1 holds `service`; `checker_due` false (section 4) | no |
| 3. a harness check fails closed | 4 lines: `empty-argument calls` and `delivered versions (P2's form)`, each in R1 and in C1 | **yes** |
| 4. a stream is invalid | none invalid on the record (section 3) | no |

## 3. Validity of R1 and C1 (protocol 8; the final `validity.json` is step 12's)
**R1: valid on the record.** `R1/measures/validity.json` (the stream step's record) reads `valid: true` with `engine_error_turns: [9]`.
- Turn 9 ended in `ClientNetworkError` (`manager-decision-row-R1-t9.md`). That ruling pre-registered three H8 conditions. None holds:
  1. The ACT-REQ@2026-10-12 window holds one task, `root-cabf` (`R1/p2/oneoffs.json`).
  2. Memo 2's task `root-a9da` has one human verdict note, `root-4934` accept (`R1/msgs/sent/`).
  3. The 2026-10-12 list was copied in turn 10, at 12:45Z, before turn 11's LIST-KEEP (`R1/deliverables-log.txt` lines 49-56).
- H2: the skill proof is `PROVED` (`R1/skill-proof.json`), and the global copy was in place after 28 of 28 turns (`R1/skill-check-turns.txt`).
- H3: the workspace settings md5 is `05d30ccb...`. H4: `R1 all: OK`, and 0 commands lack `--effort high`.
- H5: the injection ran after memo 1's first delivered version, with window `12:19:13-12:20:07` (`R1/injection-call.txt`).
- H7: the written CONDITION (turn 18) equals the computed one (`stage_gate` facts: none).
- The facilitator flagged a reading choice: memo 6's WEEK-LIST was held back behind retro 1 and sent at turn 24 (`R1/run-log.md`). This is for step 12.

**C1: valid on the record.** It has no `validity.json` yet and no `stopped.txt`. It ended `retro-2-done` at turn 27.
- The facilitator slip at turn 22 (RETRO-ASK sent one line late, at turn 23) was ruled not H7 (`manager-decision-row-C1-t22.md`).
  `retro_places` flags turn 23 as misplaced, which that ruling explains.
- `memories.db` changed during C1. It is recorded under the standing ruling (`C1/harness-failures/memories-db-change-during-C1.md`).
- H2: `PROVED`, and the global copy was aside after 27 of 27 turns. H3: `05d30ccb...`. H4: `C1 all: OK`. H5: injection window `13:41:37-13:43:01`.
- H7: CONDITION written = computed = turn 19.

**Facts the manager should weigh (none is an H rule on the record):**
- **Another workflow ran during C1.** Workflow step `sess_ab0fe2e0` (wf-coder, created 13:41Z) was active through C1
  (`C1/harness-failures/memories-db-change-during-C1.md`). The brief's guarantee ("no other workflow runs during the streams") did not
  hold for C1. No record shows it touched C1's sandbox or org (H6).
- **The owner's own sessions changed state during both streams.** `memories.db` changed at 12:31Z in R1 and 14:37Z in C1. `~/.kiro/settings/cli.json`
  and `mcp.json` changed at 12:35:19Z and 12:38:08Z (section 7).
- **The pair's `<memories>` blocks differ.** R1's has 6903 chars (md5 `2a977c30...`); C1's has 7117 (`ce74d506...`).
  `manager-decision-memories-before-R1.md` reads the assistant-layer contrast only for pairs whose blocks match, so it is not read for this pair.
- **Effort stops** (uncharged relaunches, counted): R1 10 of 59 run logs, C1 4 of 52, R1-v1 1 of 13, preflight 1 (arm C).

## 4. Credits and org runs, against 250 and the approval
| | Credits (`credits.txt`) | Org runs | Turns | 17.6 / 17.3 per stream |
|---|---|---|---|---|
| R1 | **116.82** (assistant 74.15 + org 40.50 + 3 unmatched runs x 0.72 = 2.17, FLAGGED) | 59 (3 injection) | 28 | R: 78-112 runs, 125-200 credits, 38-46 turns |
| C1 | **102.76** (assistant 61.69 + org 41.08) | 52 (3 injection) | 27 | C: 75-105 runs, 115-190 credits |
| R1-v1 (withdrawn) | 26.66 (`R1-v1/credits-running.txt`; its `credits.txt` holds a traceback, see `R1-v1/finish-failures.txt`) | 13 | 7 | |
| preflight | 7.12 | 4 charged (+1 uncharged) | | |
| **stage 1** | **253.36** | **128** | | approval 260-420 credits; estimate 153-217 runs |

Neither stream is near 250.00. Stage 1 spent slightly less than the low end of the approval. At stage 1's per-stream cost, stage 2's four
streams would cost about 440 credits (2 x 116.82 + 2 x 102.76), under 17.6's 480-780.

## 5. Item 3: the four fail-closed readings (harness defects, both streams)
Both defects are in the harness, not the product. The kept evidence holds the data each reader missed.

**(a) `empty-argument calls: NOT DETERMINED (FAIL-CLOSED: no total in empty-calls.txt)`**, in R1 and in C1.
- The writer and the reader use different forms. `harness/finish_stream.sh:68` writes
  `total: session-store empty-argument failed calls: 23 (tool_call 22, tool_load 1)`. `harness/gate_p1.py:339` reads only `^total: (\d+)`.
- The self-check never saw the real form: `harness/gate_p1_cases.py:64,164` construct `total: 0` and `total: 2`.
- On record: R1 23 and C1 35 (`R1/empty-calls.txt:29`, `C1/empty-calls.txt:28`). The stderr grep gives the same 23 and 35.
- Under 12.3 as written, the measure reads FAIL (23) in R1 and FAIL (35) in C1.
- Correction: make `gate_p1.py` read the number after `failed calls: `, add a case with `finish_stream.sh`'s real line, then re-freeze.

**(b) `delivered versions (P2's form): NOT DETERMINED (FAIL-CLOSED: no delivered version was scored (0 of 0))`**, in R1 and in C1.
- `score_p2.py` scored 0 versions because `memos/versions/` holds no memo.
- P1's `extract_mechanical.py:522-527` leaves out every file under the team's "final-check seat".
  - `detect()` (`extract_mechanical.py:82-123`, its charter rule at 104-113) picks `lead-writer` as that seat from its charter, which mentions checking
    (`R1/org-files/lead-writer-AGENT.md:36`).
  - P2's script has no reviewer, and the writer writes every memo under `lead/writer/work/`, so every memo is left out.
- R1's index holds only `lead/work/2026-10-12-check.md`. C1's `INDEX.txt` is empty.
- The versions are in the org history: `R1/org-git-log.txt` shows commits of `lead/writer/work/2026-10-05-memo.md` through `2026-11-09-memo.md`.
  `org-git.bundle` is kept in both streams.
- The pre-freeze dry runs showed the same two lines (`harness-selfcheck/dryrun-{R,C}/gate_p1.txt:14-15`). On a throwaway org with no
  deliveries they could not be told apart from a correct fail-closed reading.
- Correction: in `extract_mechanical_p2.py`, take the seat only from an agent with `kind: verifier` (none in this script). Rebuild
  `memos/versions/` from the kept bundles, add a dry-run case for a writer-only team, then re-freeze.

Until both are fixed, these two gate-able measures fail closed in every P2 stream, stage 2 included.

## 6. Self-check, view and other mismatches (information under protocol 11 item 3, not stop conditions)
1. **Self-check:** `harness-selfcheck/selfcheck-summary.txt` reads 20 of 20 parts PASS (12:07:33Z, the frozen files). `SELFCHECK.md` carries
   PF-0 and PF-1 as product findings. Neither shows in a stage-1 stream: P2-E counts PF-0 0 and PF-1 0 in R1.
2. **View mismatches (G1(f)):**
   - `R1/watch/lead--weekly-meeting-memo` has 41 lines and `C1/watch/lead--weekly-meeting-memo` has 38. All are `since` values that differ
     only in microseconds and are equal at whole seconds, so P1's stage-1 ruling 1 counts 0 of them. C1's G1(f) reads PASS.
   - `R1/watch/lead--ops-action-list` has 181 `MISMATCH` and 28 `SERVICES-MISMATCH` lines, and R1's G1(f) reads FAIL. The cause is the
     harness, not the product:
     - `watch_views.sh:11` runs P1's `rederive_watch.py` on each service's view without naming the service.
     - `rederive_watch.load_world` (`rederive_watch.py:1081-1083`) then takes the stream's most frequent service, `weekly-meeting-memo`.
       That view's `watch-rederived.json` records `service: weekly-meeting-memo`.
     - So the view compares the product's `weekly-meeting-memo` watch list with a re-derivation over `ops-action-list`'s playbook.
     - P1's streams had one service, so this never arose there.
   - Correction: build each view's world for its own service, with a dry-run case of two services. Until then, G1(f) reads FAIL in every
     arm-R stream that defines the service.
3. **A relative EV empties the 7.2 window.**
   - `rederive_p2.Org.view` (`rederive_p2.py:100-103`) links `msgs` to `self.ev / "msgs"`. With a relative EV the link points nowhere, the
     mail is empty, and every checker window is empty.
   - This fails open: `checker_due` reads false. In memory: relative `R1`, window 0; absolute, window 6.
   - `score_stream.sh` passes absolute paths, so the `p2/` checks are unaffected. Steps 7-12 must pass the absolute EV.
     Correction: link `self.ev.resolve() / "msgs"`.
4. **P2-E: `MISMATCH (5 finding(s): PF-0 0, PF-1 0, new 5)`**, all D7 (`R1/p2/P2-E.json`):
   - B1 `contract v2 (C9)`: the product reads `not recurred` in 8 cases. The harness reads `recurred` at R3 (A-M's rejection, which replaced C9).
   - B1 `P9 (v3)` `not recurred` and B1 `P8 (v4)` `INCONCLUSIVE`: product lines with no harness line.
   - B2 `contract v4 (C11)` `INCONCLUSIVE` and B2 `P8 (v4)` `INCONCLUSIVE`: product lines with no harness line.
   - Under 12.2 these are product findings for step 12 to rank. Some may turn out to be harness gaps in the playbook D7 lines.
5. **P2-S:** PASS, T12 SAME. **P2-L:** no reply-against-record or D13 difference. Product and harness both read B1.1 `lapsed`.

## 7. The empty-argument calls (the four points `manager-decision-row-C1-t22.md` section 2 binds)
**1. Timeline.**
- **R1:** 0 in turns 1-9 (12:12:42Z-12:39:29Z). New failures per turn from turn 10:
  t10 2, t11 3, t12 0, t13 1, t14 1, t15 3, t16 0, t17 4, t18 2, t19 2, t20 0, t21 1, t22 1, t23 1, t24 0, t25 1, t26 0, t27 1, t28 0;
  23 in all (`R1/empty-calls.txt`, `R1/turn-times.txt`).
- **C1:** from turn 2 (13:33:18Z), 35 in all. The per-turn table is in `C1/harness-failures/empty-calls-and-settings-change.md`.
- **Baselines with 0:** the preflight probe (10:27-10:33Z, four sessions), R1-v1 (10:37-11:03Z, 7 turns), and P1's six streams.
- **Settings mtimes** (`stat`, UTC): `cli.json` 12:35:19Z and `mcp.json` 12:38:08Z.
  - Both fall inside R1's turn 9 call (12:34:30Z-12:39:29Z), the turn that ended in `ClientNetworkError`.
  - Turn 10 is the first turn that started after both changes.
- **Safety snapshots** (md5 `cli.json` / `mcp.json`):
  - `8d759079` / `767d7d34` in `safety-before.txt` (10:13Z), `preflight-safety-after.txt` (10:34Z) and `R1/safety-before.txt` (12:11Z);
  - `f2192412` / `9ca5275e` in `R1/safety-after.txt` (13:27Z), `C1/safety-before.txt` (13:30Z), `C1/safety-after.txt` (14:41Z), and now (15:06Z).
  - The per-turn `ambient/` snapshots record `~/.kiro/skills` and `~/.kiro/memories` only, so the two mtimes are the only finer record.
- This is a correlation, not a proven cause. F-G0-7 classified the same signature (`Tool "tool_call" is not available.`) as harness or
  environment, not product.

**2. Cost.**
- In R1, every one of the 23 failures was followed at once by a completed meta-tool call (21 `tool_call`, 2 `tool_load`). This is
  F-G0-7's retry pattern.
- In C1, 21 of 35 were followed directly by a completed meta-tool call. The rest were followed by another tool's call.
- No turn errored or was repeated because of one: R1's only `exit 1` is turn 9, which had 0 empty calls, and C1 has 27 of 27 `exit 0`.
- No org run is started by one. Their tokens are inside the assistant's credits, and no separate figure exists.
- Every scripted event a pass rule reads is on record: in R1 three one-offs, B1, the apply, the week list through the new service and
  B2; in C1 four one-offs. No record ties an empty call to a change in any of them.

**3. H8** ("engine or infrastructure failures that changed the course"): the records show no changed course, so H8 does not apply on the
record. Protocol 8's own empty-call rule makes a stream "invalid for the arm contrast" only when its pair has 0. Both streams have calls,
so that label does not apply either.

**4. The gate-able reading as frozen.** It reads `NOT DETERMINED (FAIL-CLOSED)` because of defect 5(a). With the recorded totals it reads
FAIL (23) in R1 and FAIL (35) in C1.
- Under 12.5 this gate-able measure then cannot read PASS over both arms while R1 and C1 count as valid, whatever stage 2 shows.
- The settings still hold the changed md5s, and C1 had failures from turn 2. Stage-2 streams in this environment should be expected to have them too.

## 8. A quick mechanical reading of the pass rules so far (R1 is 1 of the 3 valid arm-R streams needed; no final verdict)
| Rule | R1 (`R1/p2/verdicts.txt`) |
|---|---|
| P2-X1 | **FAIL (step 8: B2 shows B1.1 `lapsed`)**. Steps 1-7 held (see below). |
| P2-X2 | NOT REACHED: the team passed the trap in all of memos 2-5 (C1 likewise) |
| P2-X3 | PASS (harness 0, product 0 unprompted charter edits; 0 root charter writes; 0 hand writes) |
| P2-L | PASS (2 records) |
| P2-B | PASS (1 change after T0, `from your change fa962d655366`; A-P led to nothing; 0 unnominated extensions, 1 EXT-NO line) |
| P2-W | PASS ((0)-(c) PASS; (d) `[]`; (e) HELD BACK (B1)/PASS) |
| P2-E / P2-S | MISMATCH (5 new) / PASS, T12 SAME |

**P2-X1 steps 1-7.** Three judged one-offs: `root-c1b8`, `root-cabf` and `root-4a85`, the third judged at 13:01:01Z. B1.1 is a `service`
item with those three as evidence. Lena said yes, and `apply_org` of `fa962d655366` used the preceding `propose_org`'s `plan_id`.
`lead--ops-action-list` v1 reads `approved_in: change fa962d655366`.

**Why step 8 fails.**
- B1.1's effect is `service lead/one-page-ops` (`R1/org-files/retros.json`).
- The applied extension (`R1/blueprint-proposal4.yaml`) defined `lead/ops-action-list`, with input `notes_file`. The assistant (root)
  rewrote the item's pre-filled criteria for any meeting. Those criteria named one meeting's people and dates ("Dev 2026-10-08, Priya 2026-10-09 ...",
  "traceable to 2026-10-05.md"), copied from the first one-off.
- Design 4.5's effect test (design lines 323-324) needs the item's name, or a renamed service whose criteria key equals the shape's. Neither holds.
- So the product (B2 D13: `B1.1 service: lapsed: no change`) and the re-derivation (`R1/rederived/p2/ledger.json` `rules.pairs`) both read
  `lapsed`. Because they agree, this is no P2-E mismatch.
- The product follows the design here. The cause lies in the item's instance-specific pre-filled criteria and the effect test, a finding
  for step 12. It is likely to recur in any arm-R stream whose root generalizes the criteria.

**Gate-able measures (`p2/gate_p1.json`; the judged keys wait for step 12):**
- Both streams: G1(a) NOT DETERMINED (P8 `kept` -> `new` is off 8.1's paths, unexplained); G1(b) VACUOUS; G1(c) and G1(e) PASS;
  G2(a)-(c) PASS; escapes PASS (3); relayed reworks PASS (0 besides the injection); hand edits PASS (0 of 13 copies).
- G1(d), injected lessons and deliveries by copy: NOT DETERMINED (judged keys).
- G1(f): R1 FAIL (harness view defect, 6.2), C1 PASS.
- Empty-argument calls and delivered versions: FAIL-CLOSED (section 5).

**What 12.5 does with these readings (mechanics, not a verdict):**
- A FAIL in one valid stream is arm R's reading for that rule. P2-X1 therefore reads `FAIL (in R1)` unless R1's validity changes, and
  stage 2 cannot change it.
- The empty-argument measure is in the same position for R1 and C1.
- If stage 2 also leaves X2 not reached, P2-X2 reads NOT DETERMINED for arm R.

**Arm C, reported only:** 0 structural changes and 0 charter edits after T0. The week list was a fourth one-off (`root-44d7`). There was no
structural proposal at turns 23 or 27, and A-P's line was not acted on.

## 9. For the manager's decision
- `next_stream.sh` refuses R2 without this file and `EV/manager-decision-stage-2.md`, which is the manager's to write.
- Stage 2 under the frozen harness would repeat both 5(a) and 5(b) and the G1(f) view defect (6.2) in every stream. The corrections
  named above would need an amendment, a re-freeze and a self-check run.
- P2-X1 already reads FAIL in a stream valid on the record. The empty-argument environment change is still in place.
- `memories.db` is `ff69d3d5...`, unchanged since C1's end.
