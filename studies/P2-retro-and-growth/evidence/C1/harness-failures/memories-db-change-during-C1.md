# memories.db changed during C1 (facts; finish_stream.sh printed its STOP line)

- md5 before C1 (setup, 13:30Z): 6e6d7471ecc08b81a051d7862de7f64f. After (finish, 14:41Z): ff69d3d53dd6b465b0f44c52ecc6db37. File size unchanged (159744), mtime 2026-10-29T14:37:03Z (during turn 26).
- Not restored or edited.
- The writer, by manager-decision-row-R1-t9.md section 2: (a) exactly one session outside the study wrote a `memoryExtractionWatermark` within 10 s of the new mtime:
  `sess_ffcc477a-1c2f-4c4e-a7c5-18226c9b7129` ("Create Minimal Projects With Jenkinsfiles And Containers", sessions folder c180816ccebda8ac, a rewind fork of sess_e1ee9b77),
  watermark 14:37:12.267Z, 9.3 s after the mtime. The other session touched near that time, `sess_ab0fe2e0` ("game-vertex-mobile-roguelite m2-code #2", folder d2f5611b58a479bd,
  last written 14:41:55Z), holds no watermark record.
  (b) `sess_ffcc477a` has no `wf_8ee5197e04b8ee7c` meta and is not a study session or under the sandbox.
- (c) The `<memories>` block that reached C1's assistant was read once at session start (7117 chars, md5 ce74d506...), before the change, and checked clean after turn 1 (`memories-block-check.txt`). C1 is not affected.
- Reading: a change recorded under the standing ruling, not a stop. The next stream's turn-1 contamination check (c) still applies. `manager-decision-memories-before-R2.md` is not written by this step (R2 depends on the stage gate and the manager's go).
- Note for the manager: another workflow's step (`sess_ab0fe2e0`, wf-coder, created 13:41Z, active through C1) ran while C1 ran. It did not write memories.db by the watermark test.
