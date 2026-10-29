# turn.sh's sequence check is vacuous (harness defect, found at turn 3; no facilitator slip, no effect on the course)
`turn.sh` (frozen, md5 in harness/MD5SUMS) ends each wrapper with `after_turn sequential: checked (no snapshot taken: no org yet)` from turn 3 on, although the snapshots exist.
Cause: its python check parses `quality/calls.txt`'s `turn-NN start 2026-10-29T10:44:53.169316+00:00` with strptime formats that do not accept `+00:00`, so `first` is None and the
"no org yet" branch prints. The check therefore never compares the snapshot with the boundary. The frozen harness was not changed.
Structural guarantee: turn.sh runs run_turn.sh (with its `; sleep 20`) and then after_turn.sh in one call in sequence, so the snapshots cannot start before the boundary.
Facilitator's read-only substitute: `R1/facilitator/seqcheck.py` compares the turn's end + 20 s with the first snapshot's start from `turn-times.txt` and `quality/calls.txt`; its output is in `R1/seqcheck.txt`
(turns 3-5 checked after the fact; every later turn right after its wrapper). A `STOP:` there would stop the step.
