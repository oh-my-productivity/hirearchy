# Manager decision: P2 pre-registration loop, after iteration 2 (2026-10-29)

- Review 1: 6 HIGH, 9 MEDIUM, 6 LOW. All 21 are resolved.
- Review 2: **0 HIGH**, 8 MEDIUM (F22, F23, F27-F31, F36) and 8 LOW (F24-F26, F32-F35, F37), in `prereg-review.md`.

**I grant ONE more iteration (budget 3), as the LAST.** The MEDIUMs are not text-only:
- F27 can turn X2 into NOT DETERMINED;
- F23 can falsely FAIL A-P;
- F22 is a fail-open check;
- F29 makes Lena approve what 17.3 says she refuses;
- F36 leaves the stage gate without inputs.

Each needs code, cases and an independent check. The study costs about 740-1200 credits, so the protocol must be right before the freeze.
The owner gave full authority (2026-10-28).

## Iteration 3, preregister (binding)
Resolve every finding F22-F37 **as the review's "Resolve" text says**. Where the review offers a choice, these are mine:
- **F24:** the reply-against-record difference is a finding, not P2-L's FAIL, because P2-L reads the ledger record as its source. Write
  this one rule in both places.
- **F25:** remove `rederive_quality.py` from 3.5, and state that no P2 check reads it.
- **F26:** **exempt the versions Lena rejected; keep the rule for every version she accepted, and for every final memo.**
  - Reason: P1 gated this measure on a team with a separate reviewer. P2's team has none by design (17.3), so a slip that Lena's scorer
    rule rejects is the contract loop working, not a regression.
  - An accepted version with a wrong date or an extra row still fails.
  - Write this into 16 with the reason.
- **F32:** do both. Open the probe's turn 1 with words that need the skill, the same in both arms. Also name the remaining stop risk in
  16, with the preflight's action: stop and ask the manager.
- **F27, F28, F29, F30, F31, F33-F37:** as the review resolves them, with every constructed case it names.

Then re-run the full self-check. Every part must pass, including the new cases. Write `prereg-revision-3.md`, with one entry per finding:
what changed, in which file and lines, and which case covers it.

Change nothing the two reviews did not ask for. If a resolution turns out to be impossible as worded, choose the closest reading, write it
with its reason, and flag it in `prereg-revision-3.md`.

## Iteration 3, prereg-review (binding)
**A scoped review, not a full re-review.** For each of F22-F37, check on the files and the self-check output that its resolution is
complete and correct. Check every changed file for a regression the change introduced, and that the self-check's recorded result belongs
to the current code (mtimes).
- Raise a new finding only when a resolution is wrong or incomplete, or a change breaks something. Do not raise one for a part neither
  review touched.
- The severity scale is the same as before.

## After iteration 3
- If it has 0 HIGH, I close the loop by decision.
- Any remaining MEDIUM or LOW is ruled by me before the freeze: applied by the freeze step if it is text-only, or by a direct opus pass if
  it is code, with the self-check re-run.
- There is no iteration 4.

# The loop is CLOSED by decision after iteration 3 (2026-10-29)

Review 3 (scoped) resolved all 16 of F22-F37 on the files, and the self-check (18 of 18) belongs to the current code. It found **0 HIGH,
1 MEDIUM (F38) and 4 LOW (F39-F42)**. The loop is closed by decision, with no iteration 4, as pre-announced. Each finding is ruled below and
applied BEFORE the freeze by one direct claude-opus-5.5 pass, which re-runs the full self-check. The freeze step starts only after it.

## Rulings (binding; each as the review's "Resolve" text says unless stated)
- **C1 (F38, MEDIUM): adopt items 1-6 of the review's Resolve.**
  - A final memo keeps the rule only when the last Lena line that judged it is ACCEPT or L-ASIS.
  - When that line is a rejection, or no line judged the memo: in a cut stream it reads NOT DETERMINED (cut); with no `end.txt` it reads
    NOT DETERMINED (FAIL-CLOSED); in a `retro-2-done` stream it reads FAIL as written.
  - A never-judged version follows the same rule.
  - `gate_p1.py` carries the cut case as information, with no fail-closed prefix.
  - Write the rule into 12.3 and 16 item 10, and add the three `score_p2.py --selfcheck` cases.
  - This is the reading my F26 decision meant: a slip that Lena rejected is the loop working, and a cut stream's unfinished memo is not a
    regression.
- **C2 (F39, LOW): adopt** the arm-C form of K33, `In the order you proposed, one at a time.`, recorded as `K33 (arm C open form)`. Name it
  in 16 item 37 and standing rule 6.
- **C3 (F40, LOW): adopt the review's recommended option.** An arm-C offer is answered by the same rows as arm R's: K40 before L0; K41 in
  L1 or L2, after which that line is the arm-C turn and L3 carries no RETRO-ASK; K41a after it.
  - Record it in `retro-offers.txt` as the arm-C assistant's own offer.
  - Mark K41 "both arms", and change 4.6's "no offer can come" to "an offer is answered as in arm R".
  - Reason, in 16 item 11: the facilitator treats both arms the same way, which keeps the pair comparable. RETRO-ASK at L3 stays the
    fallback when no offer came.
- **C4 (F41, LOW): adopt.** Use `trap 'cleanup; exit 130' INT TERM` plus `trap 'cleanup' EXIT` in `probe.sh`, and
  `trap 'cleanup; exit 4' INT TERM` in `setup_stream.sh`. Add the `selfcheck.sh` stub case for TERM.
- **C5 (F42, LOW): adopt.**
  - `score_stream.sh` takes a `selfcheck-*` evidence folder through `P2_EVDIR`.
  - `dryrun.sh` runs it in both arms in place of the four direct calls.
  - The dry run checks four `exit 0` lines in `score-steps.txt`, and in arm R the `--am-time` rule.

## Conditions on the applying pass
- **Edit only** `protocol.md`, `standing-rules-streams.md` and the files under `harness/` and `harness-selfcheck/`.
- **Independence.** Open no file under `src/hirearchy/` for the re-derivation or the scorers, and say so in `harness/CHANGES.md` under
  "Manager closing pass".
- **Write `prereg-closing-pass.md`** with one entry per C1-C5: what changed, the files and lines, and the cases.
- **Re-run the full `harness/selfcheck.sh`.** Every part must pass, the new cases included.
- **Safety.** The owner's global skill stays in place with md5 `443e1bc4911aa4d6aaa6457e78f673c1`. No stream, no freeze, no live org run,
  no product edit.

## Go-ahead to freeze (2026-10-29)
The freeze rests on this closure decision and on `prereg-closing-pass.md`. It does not rest on an APPROVED verdict.
- `prereg-review.json` stays as review 3 wrote it (CHANGES_REQUESTED). No one rewrites a review's verdict.
- `freeze.txt` records the basis: this file's last two sections, `prereg-closing-pass.md`, and the self-check re-run on the frozen files.
- The closing pass is checked by that re-run on the frozen files, and by the preflight's dry runs and probe.

## Freeze attempt 1 failed on a timing fixture: ruling (b), a harness fix and a re-freeze (2026-10-29)
- **What failed:** the self-check on the frozen files passed 18 of 19 parts. The one failure is the arm-R dry run's PF-0 timing check
  (`dryrun.sh:106-134`). It builds up to 8 throwaway orgs until both the "same second" and the "earlier second" timings appear, and all 8
  builds gave "same second". The same part passed at 09:51Z.
- **Ruling (b).** A frozen self-check part must not depend on chance, so re-running until it passes (option a) is refused. The step fixes
  the fixture and re-freezes.
  1. **Preferred:** build each timing deterministically, by aligning the throwaway org's operations to whole-second boundaries through
     the CLI or the `Org` facade, in the order protocol 12.6's corrected mechanism needs. Then check each timing.
  2. **If a timing cannot be built deterministically:**
     - every timing that IS built must be classified correctly by the frozen PF-0 signature (0 misclassified);
     - at least one PF-0 must be reproduced;
     - a timing not reached in 8 builds is recorded "not reached; covered by the constructed cases <names>", and is not a failure. Those
       constructed cases must exist and pass in `selfcheck_cases`.
  3. **Test first:** with a stubbed list of timings, show three cases: all "same second" (old: FAIL; new: PASS or not reached), a
     misclassified build (FAIL), and both timings (PASS).
  4. Change nothing else. Do not open `src/hirearchy/`, and record the change in `harness/CHANGES.md` under "Freeze fix". Update protocol
     13.3's entry for this check if it describes the old rule.
  5. Keep attempt 1's files: move them to `freeze-attempt-1/`, with `freeze.txt` noting the failure. Then re-freeze and re-run the full
     self-check on the newly frozen files. It must pass 19 of 19, or the step stops.
- PF-0's signature, its readings and its X3 rule are unchanged.
