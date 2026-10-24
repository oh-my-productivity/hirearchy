# E5 deterministic part (protocol 4.9), run by the preflight step

Run 2026-10-24 02:55-02:57 UTC at HEAD `6618c0d80401233675366684fc86dc566657e8db`, freeze diff empty, from `/Volumes/workspace/hirearchy`.
Scoped runs only (owner's test policy: no full suite). Raw output and exit codes are in `at-6618c0d/`.

| # | Command | Result | Exit | File |
|---|---|---|---|---|
| 1 | `uv run pytest -q -p no:cacheprovider tests/e2e/test_org_growth_0a.py tests/e2e/test_org_growth_0a2.py tests/e2e/test_no_bypass_0a2.py` | 78 passed, 0 failed (35.27 s) | 0 | `at-6618c0d/pytest-q-e2e.txt` (+ `.exit`) |
| 2 | `git -C /Volumes/workspace/hirearchy grep -l e4_replay tests` | `tests/e2e/test_org_growth_0a2.py`, `tests/meta/test_e4_replay_kit.py` | 0 | `at-6618c0d/replay-files.txt` |
| 3 | `uv run pytest -v -p no:cacheprovider tests/e2e/test_org_growth_0a2.py` | 9 passed, 0 failed, 0 skipped (3.43 s); every collected test shows PASSED | 0 | `at-6618c0d/pytest-v-replays.txt` (+ `.exit`) |
| 4 | report only: `uv run pytest -q -p no:cacheprovider tests/meta/test_e4_replay_kit.py` | 11 passed, 0 failed (0.40 s) | 0 | `at-6618c0d/pytest-q-replay-kit.txt` (+ `.exit`) |

The three replays D-E4-7 names, from `pytest-v-replays.txt`:
- `tests/e2e/test_org_growth_0a2.py::test_s1r_t5_an_amendment_before_the_verdict_is_refused PASSED [ 11%]`
- `tests/e2e/test_org_growth_0a2.py::test_s1r_t8_the_artifact_path_is_withheld_while_the_question_is_open PASSED [ 55%]`
- `tests/e2e/test_org_growth_0a2.py::test_s2r_the_wrong_rule_is_refused_and_the_human_rework_needs_a_base PASSED [ 88%]`

Required (commands 1 and 3 exit 0, all PASSED, the three replays present): **met**. Command 4 is reported, not a condition.
Note: the first attempt of command 1 was killed by the step's own 1.5 s tool timeout (a unit mistake, ms vs s) before pytest produced any output; the file was
rewritten by the rerun above. Nothing else ran in between; `git status --porcelain` showed only `docs/research/` and `studies/E5-org-growth-0a2-recheck/` untracked.
