# Manager decision: memories.db changed between R1 v1 and the restarted R1 (2026-10-29)

## Facts
- R1 v1's after-value was `ba97f447639184d1fb7da9eccf2b2e8c` (11:03Z). The value now is `78502051db9553346ff820af169bd21a`.
- The file's mtime is 11:46Z, and its size went from 151552 to 155648 bytes.
- No stream ran in between. The change falls inside the amendment-1 work: the manager's direct claude-opus-5.5 passes ran in sessions
  with memory `read_write` and reflection on. They are the likely writer.
- `setup_stream.sh`'s memories gate compared nothing, because `R1-v1` is outside its label order. The stream step found the change by hand,
  and nothing was restored or edited.

## Decision: GO, with `78502051db9553346ff820af169bd21a` as R1's before-value
- **The protocol's rule is met.** The change was found before the next stream's first turn, a warning was sent, and the manager ruled.
- **The pairing holds.** R1 and C1 both run after the change. P1's rule already records the `<memories>` block per stream, and the
  assistant-layer contrast is read only for pairs whose blocks match.
- **A contamination check, added for R1 and every later stream.** The change came from sessions that worked on this study, so the owner's
  memories may now hold facts about it. After turn 1, before Lena's turn-2 line, the stream step reads the `<memories>` block that reached
  the assistant session.
  - It STOPS with a warning if the block mentions any of: P2, the study, Lena, the facilitator, the decision table, a row id (`K<n>`), the
    answer key, the harness, the trap, ACT-REQ, retro 1 or retro 2, amendment 1, or the arms R and C.
  - It records the check's result in `R1/memories-block-check.txt` (the block's md5, its length, and the matched words, or "none").
  - An unrelated change in the owner's memories is not a stop; it is recorded.
- **What may run during the streams.** No direct subagent pass and no other workflow runs while a stream is in progress. That is how P1
  kept `memories.db` unchanged. This rule now binds the manager's own direct passes too.
- **A harness gap, recorded and not fixed now.** The memories gate cannot see a change between a withdrawn stream and its restart. Later
  streams follow the label order (C1 after R1, and so on), so the gate works for them. Report it in STUDY.md.

## Correction (2026-10-29, after R1's turn 8)
The 11:46Z change was written by the owner's own Kiro session `sess_ce38cb49-9ca4-48b3-a97e-af15d9e4b9c5` ("Mobile roguelite game
build"), which wrote a `memoryExtractionWatermark` at 11:46:06Z. It was not written by the manager's amendment passes, as this file first
said. The ruling (GO, with the turn-1 contamination check) stands. The standing ruling for later changes is in
`manager-decision-row-R1-t9.md`, section 2.
