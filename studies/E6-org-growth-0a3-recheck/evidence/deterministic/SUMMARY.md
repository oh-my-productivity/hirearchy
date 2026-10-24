# E6 deterministic part at `18c4ffb` (protocol 4.9; preflight step 2 of 9, workflow `wf_25265920a47bd720`)

Run 2026-10-24 15:17-15:19 UTC from `/Volumes/workspace/hirearchy` (HEAD `18c4ffb`, freeze diff empty before and after; `git status --porcelain`: only `?? docs/research/` and `?? studies/E6-org-growth-0a3-recheck/`). Scoped runs only (owner's test policy): no full suite. Files are in `at-18c4ffb/`.

**Result: PASS** (commands 1 and 3 exit 0; all 15 tests of command 3 PASSED; no SKIPPED, XFAIL, FAILED or ERROR).

| # | Command | Exit | Result | File |
|---|---|---|---|---|
| 1 | `uv run pytest -q -p no:cacheprovider tests/e2e/test_org_growth_0a.py tests/e2e/test_org_growth_0a2.py tests/e2e/test_no_bypass_0a2.py` | 0 | **78 passed** in 37.62 s | `pytest-q-e2e.txt`, `.exit` |
| 2 | `git grep -l -E "e4_replay\|e5_s" tests` | 0 | `tests/e2e/test_org_growth_0a2.py`, `tests/e2e/test_org_growth_0a3.py`, `tests/meta/test_e4_replay_kit.py` (as at pre-registration) | `replay-files.txt` |
| 3 | `uv run pytest -v -p no:cacheprovider tests/e2e/test_org_growth_0a2.py tests/e2e/test_org_growth_0a3.py tests/e2e/test_scheduler_detach.py` | 0 | **15 passed** in 8.46 s (15 PASSED lines) | `pytest-v-replays.txt`, `.exit` |
| 4 | report only: `uv run pytest -q -p no:cacheprovider tests/meta/test_e4_replay_kit.py` | 0 | **11 passed** in 0.43 s | `pytest-q-replay-kit.txt`, `.exit` |

## Named tests in command 3 (all PASSED)
- E5's D-E4-7 replays (`tests/e2e/test_org_growth_0a2.py`): `test_s1r_t5_an_amendment_before_the_verdict_is_refused`, `test_s1r_t8_the_artifact_path_is_withheld_while_the_question_is_open`, `test_s2r_the_wrong_rule_is_refused_and_the_human_rework_needs_a_base`. The other six tests of that file also PASSED (9 in all).
- 0a.3 design 16 item 1 (`tests/e2e/test_org_growth_0a3.py`, 5 tests):
  - `test_e5_s1_t6_the_case_reads_ten_user_runs_and_five_relayed_without_exceeds`
  - `test_e5_s2_t5_the_rework_lena_funded_does_not_exceed[#21: the user's rework just sent]`
  - `test_e5_s2_t5_the_rework_lena_funded_does_not_exceed[#23: the rework delivered]`
  - `test_e5_s3_the_rework_delegation_of_memo_2_inherits_the_human_tier`
  - `test_e5_s3_the_re_check_delegation_of_memo_2_inherits_the_human_tier`
- Detach (`tests/e2e/test_scheduler_detach.py`): `test_the_scheduler_and_its_run_finish_after_its_starter_and_every_descendant_are_killed` PASSED.

## Linux (report only; protocol 4.9, 13 item 25)
`git -C /Volumes/workspace/hirearchy diff --stat e417c95 18c4ffb -- src/hirearchy/processes src/hirearchy/daemon src/hirearchy/scheduler src/hirearchy/app/wire_daemon.py src/hirearchy/kiro tests/e2e/test_scheduler_detach.py tests/testkit/fixtures.py tests/testkit/fake_agent.py tests/testkit/__init__.py` printed nothing (exit 0). The citation of 0a.3's Linux run (`verification.md` C2, `1 passed in 3.48s` at `e417c95`) therefore stands for `18c4ffb`. Not a condition; this step did not repeat the Linux run.
