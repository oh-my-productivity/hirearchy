# P1 protocol amendment 1 (H-A1): the preflight probe's definition call (a harness item)

Written by the `preflight` step (workflow `wf_9e81d83f470f71a8`) on 2026-10-27, after the manager's approval recorded in `manager-decision-probe-define.md`, before F1's first turn
(protocol section 0: before F1's first turn any item may change by amendment; this one is a harness item and changes no measure, no Lena line, no reading, no validity rule).

- **Change.** `harness/probe.sh`, the first definition of the probe service (lines 42-43): `--deliverable 'A memo of at most 400 words in the reply'` is added to the
  `define-service lead probe-memo` call. Nothing else in `probe.sh` changes; the arm-F lock line is byte for byte as it was.
- **Reason.** The product requires `--deliverable` for a first definition. Attempt 1 of the preflight probe (`probe-attempt-1/`, `preflight.md` section 10) ended `PROBE: STOP` because no probe org had a
  service, so the positive control and the lock checks could not run. A harness defect, not an arm difference and not a product defect.
- **Whole-harness check.** Every product CLI call in the harness was checked against `hirearchy <subcommand> --help`; the list with OK/MISMATCH per call is in `harness/CHANGES.md`, "Amendment H-A1". No other mismatch.
- **Effect on the freeze.** `harness/probe.sh` md5 `6d33606b1972fb55e8c02343624abe52` -> `6e18b2826cb9bb942c63c5cce36c3f58`; `harness/CHANGES.md` `9c7c7cbff8ea428de76c0696bf72b9b4` -> the md5 in `harness/MD5SUMS`;
  `harness/MD5SUMS` `524b857e9b75f6f104f22d11860145e2` -> the md5 in `freeze.txt`'s amendment block. `protocol.md` and `protocol.md5` are unchanged (`70237b0f3a829795a89d81c8eba7a7d6`).
- **Probe rule.** The probe is re-run once with the frozen pass criteria unchanged (protocol 8.3); a second failure stops the study (no third attempt without the manager).
