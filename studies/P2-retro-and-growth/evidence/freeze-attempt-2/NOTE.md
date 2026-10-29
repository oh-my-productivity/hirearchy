# Freeze attempt 2 (2026-10-29, 10:10:16Z), archived when attempt 3 was written

Attempt 2 froze at 2026-10-29T10:10:16Z (`freeze.txt` here: the self-check read 19 of 19). Stream R1 v1 ran under it and stopped at turn 7:
the arm-R assistant's reply to ACT-REQ@2026-10-05 asked six questions that no row of the action-list table held
(`../manager-decision-row-R1-t7.md`, section 'The question'). The manager decided on protocol amendment 1 before any further stream, with R1
run again (same file, section 'Decision: protocol amendment 1, before any further stream, and R1 run again'; the amendment's review and the
rulings on it are in the file's later sections and in `../amendment-1-review.md`). R1 v1 is withdrawn, not scored.

Kept here, unchanged (byte-identical copies made before any attempt-3 file was written):
- `protocol.md5` (two lines: protocol.md and standing-rules-streams.md);
- `standing-rules-streams.md5` (the file the preflight wrote; see `../preflight/freeze-gap-standing-rules-md5.md`);
- `harness/MD5SUMS` (76 files; md5 a1ff86dd09d4ec766d8f2fb3701a3045);
- `freeze.txt`.

They describe harness files that no longer exist as they were. Attempt 3 changed `arm.sh`, `turn.sh`, `injection.sh`, `finish_stream.sh`,
`selfcheck.sh`, `lena_lines.py`, `selfcheck_cases.py` and `CHANGES.md`, and added `amend1_cases.py`, `turn_seqcheck.py`,
`extract_mechanical_p2.py` and `injection_window.py`. `protocol.md` and `standing-rules-streams.md` are not changed (md5s
31bc856cad06efbdefc04d582142eac2 and 909fbb79c838b69a2d620089545c3ae6); amendment 1 sits beside them in two separate files.
Stream R1 v1 is the only stream that ran under attempt 2.
