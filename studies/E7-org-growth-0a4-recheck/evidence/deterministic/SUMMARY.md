# E7 deterministic part at `18a4531` (protocol 4.9; E7 brief step 1 item 6)

Run 2026-10-25, 06:54-06:56 UTC, by the preflight step, from `/Volumes/workspace/hirearchy`, after the preflight's other checks. HEAD `18a4531662060ddf0b78923edee8d61909bc9d6d`, freeze diff empty before and after (`at-18a4531/freeze-before.txt`, `freeze-after.txt`). Scoped runs only; no full suite. No test file, product file or E4/E5/E6 evidence file was written.

**Result: PASS. Every test collected PASSED: 78 of 78, 29 of 29, 26 of 26. No SKIPPED, XFAIL, XPASS, FAILED or ERROR line in any output.**

| Cmd | Command (`uv run pytest ... -p no:cacheprovider`) | Exit | Result | Output |
|---|---|---|---|---|
| 1 | `-q tests/e2e/test_org_growth_0a.py tests/e2e/test_org_growth_0a2.py tests/e2e/test_no_bypass_0a2.py` (E5's and E6's command 1) | 0 | 78 passed in 35.52 s | `at-18a4531/pytest-q-e2e.txt`, `.exit` |
| 2 | `git grep -l -E "e4_replay\|e5_s\|e5_replay\|e6_replay" tests` | 0 | 7 files (below) | `at-18a4531/replay-files.txt` |
| 3 | `-v tests/e2e/test_org_growth_0a2.py tests/e2e/test_org_growth_0a3.py tests/e2e/test_org_growth_0a4.py tests/e2e/test_scheduler_signal.py tests/e2e/test_scheduler_detach.py` | 0 | 29 passed in 11.81 s | `at-18a4531/pytest-v-replays.txt`, `.exit` |
| 4 | `-v tests/meta/test_e4_replay_kit.py tests/meta/test_e5_replay_kit.py tests/meta/test_e6_replay_kit.py` | 0 | 26 passed in 0.70 s | `at-18a4531/pytest-v-replay-kits.txt`, `.exit` |

Command 2 lists, as at pre-registration: `tests/e2e/test_org_growth_0a2.py`, `tests/e2e/test_org_growth_0a3.py`, `tests/e2e/test_org_growth_0a4.py`, `tests/meta/test_e4_replay_kit.py`, `tests/meta/test_e5_replay_kit.py`, `tests/meta/test_e6_replay_kit.py` and `tests/testkit/e6_replay.py`. The last holds no test (the E6 replay kit the replays import); it is listed and not run on its own (protocol 4.9, item 5). `tests/e2e/test_org_growth_0a2.py` is in commands 1 and 3, so the 133 passes of the three runs count its tests twice.

## Named tests (each `PASSED` in the output named)
Command 3 (`pytest-v-replays.txt`; the lines are also in `at-18a4531/replays-passed-lines.txt`):
- E5's D-E4-7 replays (`test_org_growth_0a2.py`): `test_s1r_t5_an_amendment_before_the_verdict_is_refused`, `test_s1r_t8_the_artifact_path_is_withheld_while_the_question_is_open`, `test_s2r_the_wrong_rule_is_refused_and_the_human_rework_needs_a_base`.
- 0a.3 design 16 item 1 replays (`test_org_growth_0a3.py`): `test_e5_s1_t6_the_case_reads_ten_user_runs_and_five_relayed_without_exceeds`; `test_e5_s2_t5_the_rework_lena_funded_does_not_exceed` with both parameters (`#21`, `#23`); `test_e5_s3_the_rework_delegation_of_memo_2_inherits_the_human_tier`; `test_e5_s3_the_re_check_delegation_of_memo_2_inherits_the_human_tier`.
- 0a.4 design 17.2 replays (`test_org_growth_0a4.py`): A-1 `test_a1_8613_...`, A-2 `test_a2_762f_...`, A-3 `test_a3_6c63_...`, A-4 `test_a4_d80f_...`, A-5 `test_a5_every_recorded_result_holds_49_items_47_questions_and_2_notes`, B-1 `test_b1_bc02_...`, B-2 `test_b2_9a5b_...` and `test_b2_just_before_9a5b_...`, F-1 `test_f1_dd34_...`, F-2 `test_f2_395b_and_d13d_...` with both parameters (`395b`, `d13d`).
- C-1 (`test_scheduler_signal.py`): `test_a_term_then_a_kill_leaves_the_scheduler_signal_line_and_no_scheduler_exit`, `test_a_sighup_alone_is_recorded_and_stops_the_scheduler_cleanly`, `test_a_scheduler_started_with_sighup_ignored_records_it_ignored_and_goes_on`.
- C-2 (`test_scheduler_detach.py`): `test_the_scheduler_and_its_run_finish_after_its_starter_and_every_descendant_are_killed`.

Command 4 (`pytest-v-replay-kits.txt`): 26 passed, of which 6 are `tests/meta/test_e6_replay_kit.py` (0a.4 design 17.1) and the rest the E4 and E5 kits.

## What the scoped set does not run (protocol 4.9)
- **C-3.** C3 was not built (the manager's decision on C1, `manager-decision-c1.md`), so `tests/integration/test_scheduler_survives_the_call.py` does not exist at `18a4531`. The reproduced kill (D-E6-9's "C") has no deterministic replay. C-1 is its deterministic stand-in; the live stand-in is the preflight's check (b) (`preflight.md`, item 10).
- **S-1.** SKILL.md at most 125 lines with 0a.4 design 8's needles: the repo file at `18a4531` has md5 `fd89a7fda55b8f342cf0306173c363fb` and 125 lines (`preflight/gates.txt`). The needle tests in `src/hirearchy/skill/tests/` are not in the scoped set; report only.

## Linux (report only; not a condition)
`git diff --stat 18c4ffb 18a4531 -- src/hirearchy/scheduler src/hirearchy/processes src/hirearchy/telemetry` (`at-18a4531/linux-diff.txt`) is **not empty**: 14 files changed, 281 insertions and 39 deletions (`scheduler/_events.py`, `_loop.py`, `_ports.py`, `_session.py`, `testing.py`, scheduler tests, `telemetry/_pool.py`, `_writer.py` and telemetry tests). `processes/` is unchanged. So E6's citation of 0a.3's Linux record does not stand for `18a4531`: **Linux not shown at `18a4531`.** 0a.4 ran no Linux test and this study never pushes.
