# G0 evidence index (the preflight, stream, teardown and aggregation steps add their files; facts only)

Times are UTC unless marked. Product: `main` = `3c841bb9`. Protocol `protocol.md`, md5 in `protocol.md5`.

## Study level, written by the pre-registration step (step 1 of 11, workflow `wf_c415acfac4f09f84`)
| File | What it is |
|---|---|
| `protocol.md`, `protocol.md5`, `freeze.txt` | The pre-registered protocol (E7's protocol pinned by md5, with G0's readings, L-BUDGET-Q, the arms, the measures), its md5, and the freeze record (UTC time, HEAD, the empty freeze diff, the skill, harness, script and source md5s, the self-check outcome, the state at freeze). |
| `manager-decision-selfcheck.md` | The manager's ruling on the self-check's first-run mismatches (2026-10-25). |
| `script/` (`MD5SUMS`) | E7's protocol (byte copy, md5 `0acc2b41...`), E7's turn files and facilitator helpers (`e7-turn-files/s1`-`s3`), the injection's text source (E2's `...-root-d90e.md`). |
| `notes/`, `answer-key.md` | E2's three notes files and the private answer key, byte-identical to E7's. |
| `harness/` (`MD5SUMS`, `CHANGES.md`) | The study harness, built from E7's (`CHANGES.md`: every file against E7's, with diffs), its tests, the self-check's expected values (`selfcheck/`) and `selfcheck.sh`. |
| `harness-selfcheck/` (`SELFCHECK.md`) | The self-check's outputs on E7's raw evidence and its outcome. |

## Added by the aggregation step (step 10 of 11)
| File | What it is |
|---|---|
| `manager-decision-m0-s2-validity.md` | The manager's ruling (b): m0-s2 is invalid from turn 7 (H7), with no replacement; M0 is reported at k = 2. Written by the manager. |
| `<stream>/measures/judged.json`, `judged-evidence.md` | The judged measures of `harness/judged-template.json` per stream, with the scorer's worksheet: raw-file evidence, section 21 hand checks a-j, corrections. |
| `<stream>/measures/validity.json` | The validity record `aggregate.py` reads: 5 valid, and m0-s2 invalid with its reason. |
| `baseline.md` | Written by the frozen `harness/aggregate.py`. One table per layer, columns by arm and stratum, then min / median / max or `k of n`. Its last section records the lines this step added after generation. |
| `../STUDY.md` | The study report. |
