# Manager decision: F1's per-turn snapshots for turns 17-23 ran at the turn's start (2026-10-27)

**What happened** (`F1/harness-failures/after-turn-parallel-t17-t23.txt`). From turn 17 to turn 23 the step started `run_turn.sh` and
`after_turn.sh` in one tool block, so they ran at the same time. Each `after_turn.sh` started 1-2 s into its turn, not after the turn's 20-s
boundary. Turns 1-16 ran in sequence and are fine.

**What the measures read** (protocol 12; `finish_stream.sh`):
- **G2 (a)-(c), the pass rule in both arms, reads the mail and its times,** not the per-turn snapshots. So does no regression, which reads the
  delivered versions.
- **`finish_stream.sh` recomputes over the whole stream:** the empty-argument call total (from the session store), `model_check.sh all`, the
  tool-call extract, the credits and H-LOCK-after. So these lose nothing, provided the session copy is complete at the end.
- **G1 is a pass rule in arm I only.** In arm F it is reported.
- **The view-against-re-derivation comparison is by time, not by turn label.** The race rule uses each snapshot's own start time and the record
  times. So a snapshot taken at the start of turn N is still a valid comparison point for its own time.

**Ruling.**
1. **(a) F1 stays VALID.** The lines were chosen from the turn texts and the deliverables, and the one snapshot-based trigger (memo 4's
   request, for M3-VERDICT) came from turn 16, which ran correctly. Nothing a pass rule reads is lost.
2. **(b) Retake turn 23 now, once and in sequence, but keep the mistimed files.**
   - Before the retake, copy every per-turn file that `after_turn.sh` overwrites for turn 23 (at least `quality/turn-23.json` and
     `services/turn-23.txt`; check the script for others) into `F1/harness-failures/mistimed-turn-23/`, unchanged.
   - Then run `after_turn.sh F1 23` once, and label it `late retake of turn 23 (manager-decision-f1-after-turn-timing.md)` in
     `run-log-notes.txt`.
3. **(c) How the scorer reads turns 17-23.** A snapshot labelled turn N (N = 18..23) was taken at the start of turn N, so it is a reading of
   the **end of turn N-1**. Turn 17's is a second reading of the end of turn 16. The end of turn 23 is the retake. **No end-of-turn state is
   missing.**
   - **The condition.** After the retake (when the session copy is complete), the step writes a table to
     `F1/harness-failures/after-turn-parallel-t17-t23.txt`, under the heading "Manager's condition". For N = 17..23 it gives:
     - the quality and services snapshot start and end times (`calls.txt`);
     - the time of turn N's first assistant tool call (session store / `session-turn-times-utc.txt`).
   - A snapshot that ended before turn N's first tool call is a **clean** end-of-turn-(N-1) reading. One that did not is an **overlapped**
     reading: still valid as a time-stamped comparison point under the race rule, but not used as a per-turn state.
   - The scorer cites this file, reports the remap and the overlapped tags, and reads requests-by-turn, run counts, lock-held and the ambient
     lines for 17-23 the same way, shifted by one turn.
4. **The spend ledger.** Check now that `cases.<head task id>` exists for every memo root has requested so far (memos 1-5), each with the plan
   budget Lena approved, against root's sent mail, not `requests-by-turn.txt`. If any entry is missing, add it now and record that it was
   added late, with the time. D14 is reported only.
5. **From turn 24 on,** run `run_turn.sh` and `after_turn.sh` as separate tool calls, one after the other. Check every turn that
   `after_turn.sh`'s first snapshot starts after the turn's end, including the 20-s boundary (`turn-times.txt` against `quality/calls.txt`).
   Record `after_turn sequential: checked` in that turn's facts.

**Standing rule for every remaining stream (I1, I2, F2, F3, I3):** the same as item 5. A stream step never issues `run_turn.sh` and
`after_turn.sh` in one tool block.
