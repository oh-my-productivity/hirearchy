# G0 harness self-check on E7's raw evidence (protocol section 10; design 20.2)

Run: `zsh /Volumes/workspace/hirearchy/studies/G0-noise-baseline/evidence/harness/selfcheck.sh`. Inputs: E7's committed
`studies/E7-org-growth-0a4-recheck/evidence/s1`-`s3`, read-only. Expected values: `harness/selfcheck/e7-expected-*.json`, transcribed from
design 19.3's E7 block (product layer) and E7 STUDY (team and assistant layers), never from a script's output. Full outputs: `*.out` and
`e7-s1/`, `e7-s2/`, `e7-s3/`, `e7-pooled/` in this folder.

## Outcome: PASSED (after the manager's ruling); one declared product deviation, F-G0-1

| Module | Result |
|---|---|
| `rederive_quality.py` (the independent re-derivation of `quality --json`) | 372 of 372 OK; 1 `DECLARED` line (F-G0-1, s2) |
| `score_memos.py` (answer key, reviewer verdicts per version) | 334 of 334 OK |
| `ambiguity_recall.py` | 59 of 59 OK |
| `prompt_sizes.py` | 15 of 15 OK |
| `playbook_attempts.py` | 34 of 34 OK |
| `assistant_facts.py` (with `extract_mechanical.py`, `scheduler_survival.py`, `injection_files.py`) | 281 of 281 OK |
| `skill_check.py` | 21 of 21 OK |
| unit and integration tests (`harness/tests/`) | 299 passed |

Final line of `selfcheck.sh`: `selfcheck: 7 of 7 modules OK; tests exit 0`. Cross-check (report only): the re-derived case totals equal the
recorded `case total: N runs used` of all 8 cases that have one. `extract_mechanical.py` reproduces E7's committed extracts byte for byte
with E7's sandboxes; without them only the sandbox-dependent lines differ, each with a stated reason (`e7-s*/extract-diff.txt`).

## The first run and the ruling
The first run (before any freeze) found 7 mismatches in 2 modules; the step stopped and asked the manager. The ruling is
`EV/manager-decision-selfcheck.md` (2026-10-25). Principle: the harness re-derives by the design's rules, independently of the product;
values published for the replay kit (no org git) are not the reference for the history path. Every remaining difference from a published
value is listed here, and each amended entry in the expected files keeps its published value (`published`) and names the ruling.

| # | Mismatch (first run) | Ruling | Now |
|---|---|---|---|
| 1 | `history` s1-s3: published `known: false` (19.3 E7-all), re-derived `true` | amend: `true` on E7's evidence (43, 36, 42 commits in `org-git-log.txt`); the replays keep `false` under their kit-limit label | amended expectation, OK |
| 2 | s2 `unjudged_cases`: expected `[]`, re-derived `[...-root-3ca4]` | product defect **F-G0-1**: OQ-2's given delivery is the delivery whose checked artifact equals the file; of several, the one with a human-tier verdict; with none, the latest. The harness implements it (protocol 3.5) | expectation `[]` unchanged and now met; the product's choice is a declared deviation (below) |
| 3 | s3 `not_as_delivered`: published `[]` (E7S3-6), re-derived `[09df/5834]` | amend, correct by definition (a blocked result is no delivery, D4; OQ-3's neutral label) | amended expectation, OK; design correction and finding (below) |
| 4 | s2 memo-3 v1 `2cd5611` review: published 8 of 8 (E7 STUDY memo-quality table), not found | state D21's reading and match E7's scorer if a stated rule can | rule found and pre-registered (protocol 12 A3); the review maps, 8 of 8, OK |

### F-G0-1 (declared product deviation; G0 is not delayed)
- **Files:** `s2/msgs/read/20261025T075346466192-lead-64cb.md` (c671's `done` result, 07:53:46) and `...075348334986-lead-a112.md` (the head
  3ca4's late `done` result, 07:53:48, `supersedes` the blocked d5c7) both list `lead/writer/work/memo-2026-10-05.md`, whose checked version is
  v3 `9ce1e39` (`s2/memos/versions/INDEX.txt`, `s2/org-git-log.txt`) = `s2/memos/memo-2026-10-05.md` (md5 `7bbd2abb...`); the relayed rework
  37b7's result `...075723074733-lead-d91e.md` lists v4. Lena's reject `...-root-ce17` and her accept `...-root-4a88` are on c671.
- **The design's given delivery:** c671 (human verdict) -> s2 memo 1 has a verdict: `unjudged_cases []`, `relayed_only []`, `unseen_relayed [3ca4]`.
- **The product's:** P3's newest-first pair names the head 3ca4, which has no verdict -> `unjudged_cases [3ca4]` (by the product's rule,
  `reflection/_deliverable_checks.py:_folder_rule`, read-only; the E7 replays cannot show it, having no org history).
- **Self-check line:** `DECLARED s2: F-G0-1 case 20261025T074451197103-root-3ca4: memo-2026-10-05.md equals the checked artifact of the
  deliveries ...-root-3ca4, ...-root-c671; the design's given delivery is ...-root-c671 (human verdict), P3's newest-first pair names
  ...-root-3ca4 ...` (`rederive.out`, `e7-s2/rederive-selfcheck.txt`).
- **In G0:** the same pattern (a head task's late `done` result seconds after its human rework's, with the same file) occurred in E7 s1 and
  s2 and will most likely recur. `rederive_quality.py --compare` prints an `F-G0-1 case ...` line with the files wherever the choice differs,
  and the `MISMATCH` lines it explains; each occurrence is reported per stream. The fix comes after G0, verified deterministically on G0's
  and E7's kept evidence.

### Design correction and finding from item 3
- **Design correction (post-G0 batch):** design 19.3 E7S3-6's "the replay and the history agree" (not_as_delivered `[]`) does not hold on the
  history path: s3's file is v4 `b5f1411`, d9bc's work, whose result `...-lead-da3c` is `blocked`; the newest delivery is the relayed 5834
  (`...-lead-f639`, checked v3 `1c5b8a5`), so P3 gives `differs` naming 5834. Files: `s3/memos/versions/INDEX.txt`,
  `s3/memos/memo-2026-10-05.md`, `s3/org-git-log.txt`, `s3/msgs/read/20261025T083532641493-lead-f639.md`, `...083038053571-lead-c2f9.md`,
  `...084045856175-lead-da3c.md`.
- **Finding:** a file copied from a blocked result reads "not as delivered" (neutral label; nothing is voided when that delivery has no human
  verdict). A later label could say "from a blocked result" (backlog).

### Item 4: D21's reading
- **The rule:** a review task reviews the work file at the first org-git commit that holds the task's sent copy (the commit that closes the
  run which sent it), the same rule as the checked version of a delivery. `s2/org-git-log.txt`: commit `2cd5611` (08:09:41Z, lead run
  `20261025T080910919322`) holds both `lead/sent/20261025T080931167519-lead-1414.md` (sent 08:09:31Z) and `lead/writer/work/memo-2026-10-19.md`.
- **What it reproduces:** E7 STUDY's memo-quality table (review 8 of 8 on `2cd5611`) and its Interpretation 16 (s2 recall 1 of 1, pooled 2
  of 3). E7 STUDY's recall table applied D21's literal timing (s2 n/a (0 of 0), pooled 1 of 2): that is reported beside it as
  `recall_literal_timing` and checked too. The rule maps no other E7 review task differently.

### A harness correction found while implementing the ruling
The first version read a delivery's checked version as "the latest version committed at or before the result's time". Design 0a.2's rule
(`CheckedVersions.at_result`) is the blob at the first commit that holds the result's sent copy; the harness now uses it (protocol 3.5). On
E7's evidence it changes no re-derived value (checked by running both rules on s1-s3; every result and review task is in the log).
