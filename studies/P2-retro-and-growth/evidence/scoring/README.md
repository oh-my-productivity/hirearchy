# P2 step 12 (`score-and-report`, stage 1 only): what this step ran

Workflow `wf_8ee5197e04b8ee7c`, 2026-10-29, 15:21Z-15:55Z. `EV` = `/Volumes/workspace/hirearchy/studies/P2-retro-and-growth/evidence`. No stream, org
run or test suite was run. No frozen file changed: the md5 gate (`harness/arm.sh` `md5gate_ok`, 80 `MD5SUMS` lines, `protocol.md`, the
standing rules and both amendment-1 files) passed before scoring and after it, and both freezes held.

## The frozen readers (protocol 11 and 12.5), with absolute paths
1. `zsh EV/harness/skill_move.sh recover`: `no unrestored move; global skill: in place, md5 443e1bc4911aa4d6aaa6457e78f673c1`.
2. Written by this step from the raw files: `R1/measures/judged.json`, `C1/measures/judged.json` (both keys, with the files read), and
   `R1/measures/validity.json`, `C1/measures/validity.json` (the six keys of protocol 8). R1's earlier `validity.json`, written by the stream
   step with an `engine_error_turns` key that `aggregate.py` refuses, is kept byte for byte as `R1/measures/validity.stream-step.json`.
3. `zsh EV/harness/score_stream.sh R1` and `C1` (they take `EV` from `arm.sh`, an absolute path): 0 failed commands each
   (`R1/score-steps.txt`, `C1/score-steps.txt`, the runs started 15:34:56Z and 15:34:58Z). Every reader ran under `python3 -B` with
   `PYTHONDONTWRITEBYTECODE=1`.
4. `python3 -B EV/harness/aggregate.py /Volumes/workspace/hirearchy/studies/P2-retro-and-growth/evidence` -> `EV/aggregate.md`, exit 0.

**Against the gate's run (14:46Z):** `p2/verdicts.txt` is byte-identical in both streams (copies at the gate: `R1-verdicts-at-gate.txt`,
`C1-verdicts-at-gate.txt`). In `p2/gate_p1.json` only the three judged lines moved, from `NOT DETERMINED (judged ...)` to PASS: `G1(d)`,
`injected lessons` and `deliveries by copy`, in both streams.

## The labelled sensitivity (REPORTED, NOT ADOPTED)
Computed under `/tmp/hirearchy-p2-score/`, never in `EV/harness/` and never in `EV/<label>/`:
- `h-frozen/` is a byte copy of `EV/harness/` (80 of 80 `MD5SUMS` lines match). `h-5a/`, `h-62/`, `h-63/` and `h-all/` are copies of it with
  one exact replacement each (`patch.py`; the diffs are `harness-patches.diff`).
- `sensitivity.py` copies `EV/R1` and `EV/C1` into `/tmp/hirearchy-p2-score/copy/<variant>/` and runs the readers there. A control run of
  `h-frozen` on the copies gives `p2/verdicts.txt` and `p2/gate_p1.json` equal to `EV`'s in both streams.
- 5(b) is computed by rebuilding `memos/versions/` from each stream's `org-git.bundle`, with the seat taken only from an agent whose
  `AGENT.md` has `kind: verifier` (none). Variant `5b-seat-names` also reads R1's own file names (`<date>-memo.md`) as P1's scorer's
  `memo-<date>.md`.
- The outputs are `sensitivity.json`. A `find EV -newer` check after the run listed no file.
- `effort_cost.py` (read-only) gives `effort-cost.json`: each effort stop's run, its seconds until the relaunch, and its user turn.

`SCORER-MD5SUMS.txt` holds the md5 of every file in this folder except itself and this README.
