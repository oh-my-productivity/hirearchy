# Manager decision: F2's turn-4 snapshot ran during the turn (2026-10-28)

**What happened** (`F2/harness-failures/after-turn-parallel-t4.txt`). At turn 4, `run_turn.sh` and `after_turn.sh` ran in the same tool block
(a slip against standing rule 1), so the `turn-04` snapshots (00:33:28Z) and the session copy read the start of turn 4. After turn 4 ended,
the injection window ran (00:37:33-00:40:23Z, exit 0). Turn 5 (H6) has not been sent yet.

**Ruling.** Turn 4 gets no retake, and F2 continues from turn 5 with strictly separate calls.
- **Why no retake.** Unlike F1's turn 23, the org has moved on since turn 4 ended: the injection's runs are in it. A retake now would record the
  state after the injection under turn 4's label. Running `after_turn.sh F2 4` again would also add a second turn-4 block to its run-count and
  lock records. The end of turn 4 before the injection cannot be taken again.
- **How the scorer reads it,** as in `manager-decision-f1-after-turn-timing.md` item 3:
  - `turn-04` is a reading of the end of turn 3, classified clean or overlapped against turn 4's first assistant tool call. The step adds that
    row to its failure file under the heading "Manager's condition".
  - The end of turn 4 has no snapshot. The scorer reports it as `not snapshotted (manager-decision-f2-after-turn-t4.md)`. G1 is only reported
    in arm F. G2 reads the mail. `finish_stream.sh` recomputes the empty-call total, the model checks, the credits and H-LOCK-after over the
    whole stream from the final session copy. Nothing a pass rule reads is lost.
- **Reported** in `STUDY.md` with F1's case. The same slip happened in two streams. Lesson for future harnesses: one wrapper script should run a
  turn and then its snapshot, so that the step cannot start them together.
