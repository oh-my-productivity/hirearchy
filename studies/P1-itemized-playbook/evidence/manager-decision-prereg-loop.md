# Manager decision: the P1 pre-registration loop, pass 3 (2026-10-27)

**The record so far:**
- Iteration 1: CHANGES_REQUESTED, with 3 HIGH, 13 MEDIUM and 9 NIT.
- Iteration 2: CHANGES_REQUESTED, with 0 HIGH, 7 MEDIUM and 9 LOW. Every iteration-1 finding is resolved (`prereg-review.md`).

**Why a third pass.** The 7 MEDIUMs are not polish. They decide whether a stream can be scored at all:
- a pass rule could fail on a legal sequence (M1);
- a fail-open could pass a check on missing data (M2, M3);
- the facilitator could still face a choice, which is F-G0-5 again (M4, M5);
- a brief rule could be left unenforced (M6);
- a choice that can decide the exit verdict had no reason (M7).

They must be fixed and reviewed before the freeze: nothing that defines a measure may change after F1's first turn. So I grant **one more
pass, the last.** After its review I close the loop by decision, whatever MEDIUM and LOW findings remain.

The directives below are binding on the author (`preregister`, iteration 3) and on the reviewer (`prereg-review`, iteration 3). A finding that
disagrees with a directive is reported as a disagreement with the manager, not as a blocker.

## Adopt the reviewer's fix as written
- **P2-M1.** The three legal transitions:
  - `retired|restored -> kept` only with an exempt client-written restore between the two snapshots;
  - `warning -> kept` only with a corrected link between them, reported.
  - Add the `g1_a` code and the three `g1_cases.py` flows: two that pass and one that must fail.
- **P2-M2.** The "unread snapshot" rule in 12.1 and in code:
  - a Python traceback through `hirearchy` is a product defect, and G1(f) FAILs;
  - any other unread snapshot reads NOT DETERMINED for G1(a) and G1(f);
  - G1(e) is NOT DETERMINED when `end.json` is unread, never PASS.
  - Add the two constructed cases.
- **P2-M3.**
  - Case entries are created when root's first request of a memo exists.
  - `missing_cases` and `extra_cases` are derived from the mail.
  - A missing case reads NOT DETERMINED.
  - Add the `aggregate_check.py` scenario.
- **P2-M4.** Both sentences:
  - `Also:` is judged under the owner form that the fixed line itself sets, with no VR-OWNER sentence;
  - L-LATER is always the first line after memo 3's first delivered version, and M3-VERDICT is the first line after it.
- **P2-M5.**
  - Add rows K35 (the lock: `Keep it as it is.`) and K36 (redo an accepted memo: `No, keep the earlier memos as they are.`).
  - Replace section 5's last clause with the reviewer's rule. After F1's first turn, a missing row is resolved only by (a) a ruling that maps
    it to an existing row, recorded `K<n> (by ruling)`, or (b) ending the stream at that turn, valid as at a cap.
  - No line is ever added after F1's first turn.
  - **Also:** the stream step's warning on a missing row must quote the question verbatim and name the two or three closest rows, so that I
    can rule (a) quickly.
- **P2-M6.** A `memories.db` change between streams stops the study before the next stream, as a change during a stream does.
  - The check comes before any folder, sandbox or profile is made: exit 4, unless
    `EV/manager-decision-memories-before-<label>.md` exists.
  - Add the check case.
- **The LOWs L2-L9:** adopt as written.
- **L1:** take the conservative option. Add N x the stream's mean credits per matched run, flagged in `credits.txt`, so the 185-credit
  comparison is never low. Say so in protocol 11.

## I decide M7: "no regression" is the pass rule in arm I; arm F is reported and compared

**Reasons:**
- Phase 1's exit criterion is about what Phase 1 ships. That is arm I: the default product, unchanged.
- Arm F is a configuration the harness imposes as a control: a locked contract, applied by the harness through the product's CLI. It is the
  same reason G1 is read in arm I only (design 18.5).
- What arm F is for here is the contrast. A regression in both arms points away from the itemized playbook. A regression in arm I only points
  at it.

**What is reported in arm F, with a cause:** every regression line, classified by its cause.
- A regression whose cause is in a mechanism both arms share is a **product finding** `F-P1-n`, ranked by severity in `p1-report.md`, even
  though it does not decide the exit verdict. The shared mechanisms are: REQUEST-UNANSWERED, FEEDBACK-UNANSWERED, the acknowledgement path, P2,
  the scheduler, and spend.

**The rule itself stays the design's 21.1 item 3,** word for word:
- E7's rule per memo, with G0's gate-able outcome measures: every delivered version has 0 wrong dates and 0 extra rows.
- Any part of E7's per-memo rule that G0's "What Phase 1 must know" did NOT name as gate-able is reported, not a pass rule. For example, a memo
  kept without a Summary under L-ASIS. Cite the G0 line for each.
- The L7 fix applies: state the consequence ("one wrong-date delivered version fails the stream") as the design's own text.

Make section 16, 12.3, 12.4 and `aggregate.py` agree with this. The exit needs the G1 and G2 lines plus `no regression (arm I)`.

## Also required in pass 3
- Re-run `selfcheck.sh`, and every check-case script (`g1_cases.py`, `aggregate_check.py`, the setup and next-stream checks). All must pass.
  Record the summary lines in `SELFCHECK.md`.
- Add a resolution table for the iteration-2 findings to `protocol.md` section 17, finding by finding, naming the directive used.
- Keep `rederive_watch.py` independent: do not open `src/hirearchy/` while changing it, and say so in `CHANGES.md`'s "Iteration 3".
- The design diff stays the one 21.6 line. Nothing is frozen. Nothing is committed. No sandbox, profile or stream is created.

**For the reviewer:** check every directive above first, then the seven mandatory checks again. Report only what is wrong or missing.

## The loop is closed by decision after pass 3 (2026-10-27)

Pass 3: CHANGES_REQUESTED, with **0 HIGH**, 3 MEDIUM and 5 LOW. Every directive above and every iteration-2 finding is resolved
(`prereg-review.md`, iteration 3).
- **The loop is closed. The pre-registration is approved with the amendments C1-C8 below.**
- They are applied before the freeze, by a separate manager-ordered step, which then runs `selfcheck.sh` and every check-case script. Only
  then is the loop closed and the freeze step run.
- Nothing that defines a measure may change after the freeze.

**The author's judgment call, "D14 is reported, not a pass rule": CONFIRMED.**
- This is what M7's directive requires. G0's "measures that can gate" are the values that did not vary in 5 of 5 valid streams (G0 `STUDY.md`
  "What Phase 1 must know" item 2).
- D14 varied (G0's band row "Cases within D14 | 2-3 of 3"; F-G0-8, memo 1 of m1-s1 and m1-s2 at 1.36x). So it is reported, NOT DETERMINED on
  an incomplete ledger, and never a pass rule.

### Amendments
- **C1 (P3-M1): adopt the reviewer's fix as written.** This is not a disagreement with my directive: "valid as at a cap" was about validity.
  An end by ruling (b) is on the protocol's side, so the parts it cut are NOT DETERMINED, never FAIL:
  - for no regression: a memo with no delivered version by that turn;
  - for G2(b)'s end-of-stream part: a rejection whose answer was the withheld line.

  A FAIL on what was delivered or recorded before stands. Add `ended_by_ruling` to `validity.json`, the matching reads in `aggregate.py`, and
  the `aggregate_check.py` scenario (memos 5-6 undelivered, R5 unanswered: no regression ND, G2 ND, exit ND).
- **C2 (P3-M2): adopt the reviewer's fix as written** (L-ASIS can apply at M3-VERDICT):
  - M3-VERDICT judges the latest version of memo 3 delivered (D8) before that line.
  - If Lena has declined memo 3's spend ("No more spend, please deliver as is.") and that version differs from the key, M3-VERDICT is
    `About the 2026-10-19 memo: ` + L-ASIS, recorded `M3-VERDICT + L-ASIS`, an accept.
  - Reason: E7 4.10's exception holds for every memo's verdict. A rework she declined to fund would add an unscripted rejection.
  - Write it in 4.2 and 16 item 3, and add a constructed `lena-lines` case if the harness reads it.
- **C3 (P3-M3): adopt the reviewer's fix as written.**
  - Each rejection in a Lena turn needs its own human-tier reject note on that memo's case.
  - Write `VR-REJECT@<memo date>` in `lena-lines.txt`, and parse the rules as a list.
  - Add the memo map and the one-note-per-rejection matching to `guarantees.py:g2`.
  - Add the two constructed cases: one note for two rejections FAILs; two notes PASS.
- **C4 (P3-L1): add row K37:** "whether the team should retire, keep or change one of its playbook items, outside an acknowledgement (K31)"
  -> `That's up to the team.` Reason (16): 18.4 reports the owner's choice, and the user takes no side. This is allowed: it is added before
  F1's first turn, by amendment.
- **C5-C8 (P3-L2 to L5): adopt as written:**
  - C5: the sentence forms inside `Also:` are L-ASIS's forms, in table order;
  - C6: the 12.3 sentence and the 16 sentence on a delivered memo whose judgment the cap cut;
  - C7: the `before_failure` keys `G1`, `G2` and `no_regression` only, and `aggregate.py` rejects any other key;
  - C8: section 0 says "after F1's first turn, never by a new line".

**Also:**
- Add a resolution table for the iteration-3 findings and C1-C8 to `protocol.md` as section 17.3.
- Add `CHANGES.md` "Iteration 3b (manager amendments)". Keep `rederive_watch.py` independent: do not open `src/hirearchy/`.
- Re-run `selfcheck.sh` and every check-case script, and record the summary lines in `SELFCHECK.md`.
- The design diff stays the one 21.6 line. Nothing is frozen, committed or created.
