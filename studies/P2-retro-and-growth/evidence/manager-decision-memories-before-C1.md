# memories.db before C1 (written by the stream-c1 step under the standing ruling, 2026-10-29)

Authority: `manager-decision-row-R1-t9.md`, section 2, "A standing ruling for the rest of the study". The stream step may write this file
when (a) and (b) hold; (c) is checked after C1's turn 1.

## Facts
- `memories.db` md5 at R1's start: `78502051db9553346ff820af169bd21a`. At R1's end (`R1/memories-md5-after.txt`): `6e6d7471ecc08b81a051d7862de7f64f`.
  The change happened during R1 (`R1/memories-db.txt`: "CHANGED during R1") and the manager has ruled on it (R1 stays valid).
- md5 now, read by `md5 -q` before C1's setup (13:3xZ): `6e6d7471ecc08b81a051d7862de7f64f`. **No change between R1's end and C1.**
  File size 159744 bytes, mtime Oct 29 12:31 (the same change).
- (a) The writer: session `sess_e1ee9b77-aa4d-46f1-86b8-082887906d28`, title "Create Minimal Projects With Jenkinsfiles And Containers"
  (sessions folder `c180816ccebda8ac`), whose `session.json` was last written at 12:31:26 and whose `messages.jsonl` holds
  `memoryExtractionWatermark` records (the manager's section 2 names the watermark at 12:31:26Z).
- (b) It is not a workflow step of `wf_8ee5197e04b8ee7c` and not a study session (different sessions folder, no sandbox path).
- Nothing was restored or edited.

## Why this file exists
`next_stream.sh` refuses C1 while `R1/memories-db.txt` records a change and no `manager-decision-memories-before-C1.md` exists. The gate
(`memories_gate.py`) itself finds no difference between R1's after-value and the current value.

## Condition (c), still open
C1's turn-1 `<memories>` contamination check (`manager-decision-memories-before-R1.md`) runs before Lena's turn-2 line; its result goes to
`C1/memories-block-check.txt`. A failed check, or any new memories.db change during C1 whose writer cannot be identified under (a) and (b),
is a stop with a warning.
