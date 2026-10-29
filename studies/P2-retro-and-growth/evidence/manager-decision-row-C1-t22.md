# Manager decision: C1 turn 22, the missing RETRO-ASK; and the empty-argument calls in both stage-1 streams (2026-10-29)

## 1. The facilitator slip: (a) CONTINUE, with RETRO-ASK placed at turn 23 by ruling
**Facts** (`C1/harness-failures/facilitator-slip-retro-ask-missing-at-L3-t22.md`):
- In C1, L0 = turn 19, the accept of memo 5. No TRAP rule fired in this stream: memos 2-5 all passed the trap, so X2 is "not reached",
  which reads nothing in arm C.
- L1, L2 and L3 are turns 20, 21 and 22. No reply before L1 or L2 offered a retro.
- By protocol 4.6 and standing rule 15, L3 had to carry RETRO-ASK. The facilitator sent `Yes, add it.` alone, because it had mislabelled the
  A-M line as L1.
- Nothing was sent after the slip.

**Ruling: continue.**
- Turn 23 is the line the frozen rules give for the reply to turn 22. Its verdict part is for memo 6's rework, judged under the verdict
  rule (ACCEPT `This version is right now, thanks.` if it passes). Then come the answers it needs (L-INJ if the reply mentions the rework
  again). Then **RETRO-ASK `Shall we look at how it's going?`**. The follow-on WEEK-LIST is held back, as protocol 4.4 part 6 requires.
- Record it as `RETRO-ASK (by ruling, manager-decision-row-C1-t22.md)`, and note in the facts that the arm-C turn is placed at turn 23 by
  ruling.
- No line is added: RETRO-ASK is an existing line, and this ruling moves its place by one line. Later rules read from there: the week list
  follows the arm-C turn's answers, and then retro 2's place.

**The reading, pre-registered now: C1 stays VALID; this is not H7.**
- H7 needs a facilitator error that changed the course of something a measure reads. Arm C carries no pass rule. P1's gate-able measures
  read the memos, verdicts, copies, empty calls and hand edits, and none of them depends on where the arm-C turn falls. P1's F1 owner-form
  ruling was decided the same way.
- **Step 12 reports the deviation:** C1's arm-C turn came one line late (turn 23, after memo 6's rework, not at L3 while the rework was
  pending).
  - The arm-C reported measures that read events after that turn are reported with this note: proposals at the turn, unprompted
    structural changes, and the fourth one-off.
  - `retro_places` flags turn 23 as misplaced; that flag is explained by this ruling, and it is not an H7 fact.
- **A standing facilitator check for every later stream.** The harness is unchanged. Before composing any Lena line from L0 to L3, run the
  frozen `lena_lines.condition_turn` and `retro1_expected` on the current `lena-lines.txt`, and write the computed L0-L3 and the expected
  retro-1 part into the turn's facts.

## 2. The empty-argument calls in R1 and C1: an environment change, for the stage gate
**Facts** (read by the manager from the stream records; nothing was edited):
- `Tool "tool_call" is not available.` failures:
  - R1: 0 in turns 1-9, then rising from turn 10, 23 in total;
  - C1: from turn 2 on, 24 by turn 22;
  - P1: 0 in all six streams; P2's preflight probe: 0 in four sessions.
- **The owner's global Kiro settings changed during R1.** `R1/safety-diff.txt` shows `~/.kiro/settings/cli.json` (mtime 12:35:19Z) and
  `~/.kiro/settings/mcp.json` (mtime 12:38:08Z) with new md5s. An owner session started at about 12:35Z. R1's empty calls began in turn 10,
  the first turn after these changes, and C1 ran entirely after them.
- **This is a correlation, not a proven cause.** The study profiles use `includeMcpJson: false` and the workspace `cli.json`. The study
  never writes these files, and must not.

**What it bears on:**
- "0 empty-argument calls" is one of P1's gate-able measures that P2 gates in every stream of both arms (protocol 12.3, item 8). Read as
  frozen, it is FAIL in R1 and in C1, and under 12.5 that makes Phase 2's exit FAIL, whatever the product does.
- It is not "invalid for the arm contrast" (F-G0-7 section 4 item 3), because both arms have them.

**For the stage gate (step 6), binding.** I take no position here on validity, and I will not re-read a measure because of its result. The
gate reports:
1. the per-turn timeline of empty calls in both streams against the settings files' mtimes and every safety snapshot;
2. whether the failures cost turns, runs or credits, or changed any event a pass rule reads;
3. whether H8 ("engine or infrastructure failures that changed the course") applies, under the protocol's own words;
4. the gate-able reading as frozen.

The manager then decides on stage 2. The choices include stopping before stage 2 until the environment is restored and checked by a
probe, so that the credits are not spent where the frozen gate-able measure cannot pass.
