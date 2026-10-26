# G0 deterministic part (design 21; protocol 11) at 3c841bb9

Run 2026-10-26T04:38:46Z-04:38:49Z, repo `/Volumes/workspace/hirearchy`, HEAD `3c841bb9cdde666c6ea8b00bb2edfeae68c256db`, branch `main`.
Freeze diff (`git diff --stat 3c841bb9 HEAD -- src skills pyproject.toml uv.lock`) empty before (`freeze-before.txt`) and after (`freeze-after.txt`).

Command (scoped; no full suite), from `/Volumes/workspace/hirearchy`:
```
uv run pytest -v -p no:cacheprovider tests/e2e/test_org_growth_0b_replays.py tests/e2e/test_org_growth_0b_costs.py
```
- Exit code: `0` (`pytest-exit.txt`). Output kept verbatim: `pytest-output.txt` (stdout), `pytest-stderr.txt` (empty).
- Result line: `116 passed in 2.77s`. 113 tests in `test_org_growth_0b_replays.py`, 3 in `test_org_growth_0b_costs.py`; 116 `PASSED`; no SKIPPED, XFAIL, XPASS, FAILED or ERROR.
- Design 19.3 and 19.4 expectations: all replay tests (E, E2, A5, E3 and E7 kits) and the three published-count tests of the costs file
  (`test_e_published_counts`, `test_e2_published_counts`, `test_a5_published_counts`) are `PASSED`. E3-7: `test_e3_7 PASSED`; it is the firing variant itself (the
  constructed variant `r2-links-r1`, asserting `repeat: FIRES: R1 failed in 2 of the last 3 judged cases`). E3-9's constructed variant
  (`N=12 fires at 1.30x` and `N=11 is exactly 1.25x and reads no`) `PASSED` too. E7 replays: `test_e7s3_1` to `test_e7s3_7` and
  `test_e7_all[E7-s1|s2|s3]` `PASSED`.
