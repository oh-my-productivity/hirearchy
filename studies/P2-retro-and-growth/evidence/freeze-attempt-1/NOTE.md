# Freeze attempt 1 (2026-10-29, 09:59:30Z) failed

The self-check on the frozen files read `SELFCHECK: 18 of 19 parts passed`. The failing part was the arm-R dry run:
`MISMATCH PF-0: terminal-only orgs with a hand edit of a nested charter, both timings built: expected yes, got no` (`dryrun-R.out` here is that
run's output). All 8 builds fell in the same second as the older commit, so the 'earlier second' timing was never built. A fixture depending on
sub-second timing is not allowed in a frozen self-check (manager ruling (b), `../manager-decision-prereg-loop.md`, last section).

Kept here: `freeze.txt`, `protocol.md5` and `harness/MD5SUMS` of attempt 1. They describe files that no longer exist as they were: attempt 2
changed `harness/dryrun.sh`, `harness/dryrun_build.py`, `harness/selfcheck_cases.py`, `harness/CHANGES.md`, a new `harness/pf0_timing.py`, and
`protocol.md` (13.3 only). `standing-rules-streams.md` is unchanged. No stream ran under attempt 1.
