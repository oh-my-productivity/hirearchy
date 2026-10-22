# E4 deterministic part at 7d86c31 (protocol 4.9, as amended by protocol-amendment-1.md A1): facts only

Run 2026-10-22 19:06-19:07 local (WEST; 18:06-18:07 UTC) by the amendment-1 decision step, before s1r exists.

- Repo `/Volumes/workspace/hirearchy`, branch `main`, HEAD `7d86c31f1b0d52e7ea9467ce72c8d9322e71a71c`.
- `git status --porcelain`, before and after: `?? docs/research/`, `?? studies/E4-org-growth-0a1-recheck/`.
- `git diff --stat 7d86c31 HEAD -- src skills pyproject.toml uv.lock`: empty.
- `tests/e2e/test_org_growth_0a.py` has the same git blob at `d85cc13`, at `7d86c31` and in the working tree:
  `ad4b28e7f250bd28647fa0f9a2b3f2680cfb43fb`. `git diff d85cc13 7d86c31` of the file is empty.
- `protocol.md` names no other deterministic test (4.9; section 1: "the e2e cases of 0a.1 items 1, 2 and 4", all in this file).
  `tests/e2e/` has no other org-growth file.
- No product file was changed. No test was changed, skipped or deselected.

| # | Command (cwd = repo) | Exit code | Result | Raw output |
|---|---|---|---|---|
| 1 | `uv run pytest -q tests/e2e/test_org_growth_0a.py` (the brief's form) | 0 | **12 passed, 0 failed** in 22.72 s | `pytest-q-e2e-org-growth.txt` |
| 2 | `uv run pytest -p no:cacheprovider -v tests/e2e/test_org_growth_0a.py` (protocol 4.9, verbatim) | 0 | **12 passed, 0 failed** in 22.63 s | `pytest-e2e-org-growth.txt` |

The cases 4.9 requires all PASSED in run 2:

| Case | Result |
|---|---|
| `test_3_the_e2_rule_is_refused_at_zero_run_cost` (relayed wrong rework, then a revision citing it: refused) | PASSED |
| `test_7_an_amendment_admits_a_revision_only_once_the_client_confirmed_it` (confirmed amendment: admitted) | PASSED |
| `test_11_e3_turn_5_an_unasked_amendment_is_not_the_clients_yes` (E3 T5 replay: unconfirmed amendment refused) | PASSED |
| `test_12_a_reviewers_ambiguous_item_reaches_roots_progress_before_delivery` (reviewer's ambiguous item flagged in root's `progress`) | PASSED |

The other 8 cases also passed: `test_1`, `test_2`, `test_4`, `test_5`, `test_6`, `test_8`, `test_9` and `test_10`.

Failures: none. The 4.9 rule "on failure, record and escalate before s1r" does not apply.

For comparison, the s1 step's run at `d85cc13` (`../pytest-e2e-org-growth.txt`, unchanged) had 12 passed in 24.67 s.
