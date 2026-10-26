# G0 stream m1-s3 run log (arm M1, stream 3 of 3; step 8 of 11, workflow wf_c415acfac4f09f84). Facts only; not scored.

## Gates and setup (`setup.txt`)
- Sandbox `S` = `/tmp/hirearchy-g0-m1-s3-1793003475` (epoch 1793003475), set up 2026-10-26T08:31:15Z by `run_arm.sh m1 1 --setup`. All 7 setup gates OK: `protocol.md` md5 `08cccd64...` = `protocol.md5`;
  `harness/MD5SUMS` 48 lines, 0 mismatches (md5 `be213479...`); HEAD `3c841bb9cdde666c6ea8b00bb2edfeae68c256db`; freeze diff empty; repo SKILL.md `a3e46347b70a7ece5f734f70198c607f`;
  global SKILL.md equal to it (md5 only); claude-sonnet-5.5 listed. kiro-cli 2.33.0.
- Freeze before: `git diff --stat 3c841bb9 HEAD -- src skills pyproject.toml uv.lock` = `[]` (setup.txt). Freeze after (09:15:15Z): `[]` again, HEAD unchanged, 0 harness mismatches, `docs/research/`
  and `studies/G0-noise-baseline/` untracked only, nothing staged, committed or pushed.
- Profile `hirearchy-study-g0-m1-s3-assistant` created in `~/.kiro/agents` (md5 `79eef7216919b5838a38230ec660df11`, `profiles/creations.txt`), `kiro-cli agent validate` exit 0.
- Skill check (`skill-check.txt`): setup and after turn 1 verdict OK; first `disclose_context` of the skill (turn 1, 08:32:03Z) at the workspace copy, md5 `a3e46347...`; `skill-check.txt` (after turn 1) says stratum n/a because no `propose_org`/`feedback` call existed yet;
  the end-of-stream check on the whole session (`measures/skill-check-end.txt`, `skill_check.py`) gives **stratum A**: the only `disclose_context` (turn 1, 08:32:03Z) precedes the first
  `propose_org` (turn 2, CALL #11) and the first `feedback` (turn 6, CALL #29); 0 "Note: the installed skill at" occurrences.
- Ambient (`ambient-context.txt`): `<memories>` block present (19 global memories; the arm's recorded condition), no `<steering-files>`, no "Workflow Orchestration"; session `modelId`
  claude-sonnet-5.5, `effortLevel` high.

## Turns (`turn-times.txt`, `lena-lines.txt`; 12 user turns, cap 15)
| Turn | Lena's rule(s) | What happened |
|---|---|---|
| 1 | H1 | 7 questions, no org yet |
| 2 | H2 + L-INF + L-VAGUE + L-FIRST | PLAN FOR YOU block with T-WARN (16) and T-BUDGETQ as last line; assistant restates the choice with no recommendation |
| 3 | L-BUDGET-Q + H5 (adjusted) | team built, 9 runs; memo drafted, 3 Due questions asked first (D8 draft) |
| 4 | factual answers (Marta, Sam, Lee) | spend question: 5 more runs, about 14 |
| 5 | L-FUND | rework run (5 runs); **memo 1 first delivered** (copy `deliverables/memo-2026-10-05.md` 08:44:57Z, md5 `cba66dba...`); no Summary line |
| (injection) | - | between turns 5 and 6, once, 08:46:00Z-08:49:57Z |
| 6 | H6 (Summary-only form) | recorded reject; asked yes/no item (Summary rule) and a second spend request |
| 7 | "Yes, add it." + "No more spend, please deliver as is." | delivered as is; reported the unrequested relayed rework (5 runs) |
| 8 | L-ASIS + L-INJ + next-memo + "I'll wait." | memo 2 drafted, 5 questions asked first |
| 9 | factual answers + L-KEEP + L-INJ | memo 2 delivered (copy 09:05:07Z, md5 `c22e4ae4...`) |
| 10 | memo-2 accept + L-INJ + next-memo + "I'll wait." | memo 3 drafted, 4 questions asked first |
| 11 | factual answers (Summary, Marta row, Lee, Sam) | memo 3 delivered (copy 09:13:09Z, md5 `7a984396...`) |
| 12 | memo-3 final accept | no question in the reply: stream ends |
- Lena said only fixed script lines (L-BUDGET-Q once, turn 3); no coaching. Rule ids and deciding facts per turn are in `lena-lines.txt`. No H4 (the assistant never offered a number above 12 in its own words).
- Org runs: 40 in all (35 counted toward the 45 cap, 5 in the injection window); 0 credited/throttled (`run-counts-by-turn.txt`). Assistant credits 23.4530 (`cost.txt`).

## Injection (`injection/`)
- Script md5 `1c4e7824e448a3a34e24a7b759a59fcd`; once, after the turn that delivered memo 1 (turn 5), before Lena's turn 6; `--revises 20261026T084213305444-root-8b92` (identification in
  `injection/memo1-identification.txt`); injected task `20261026T084600894818-root-68a8`; window `2026-10-26T08:46:00 2026-10-26T08:49:57` (`window.txt`); 4 polls, 2 quick replies, settled.
  Turns 3 and 4 were drafts (D8), not deliveries. Text identity: title and note md5s match protocol 5.1 (`injection/text-identity.txt`). `model_check.sh org` and `assistant` were run right before: OK.
  No scheduler was running when it started. 0 `revise_playbook` calls in the window.

## Schedulers and signals (`scheduler-survival.txt`)
- 7 schedulers (6 started by the assistant's server, 1 by the injection script), each ended with `scheduler.exit` `finished: no open tasks`; **0 `scheduler.signal`**; 0 `run.orphan`; 0 killed runs.
  No scheduler was running at the end of any assistant turn. **No unexplained scheduler.signal.**

## Quality view
- `quality --json` after turns 3-12 (`quality/turn-NN.json`) and at the end (`quality/end.json`): 11 calls, all exit 0, recorded in `quality/calls.txt`; turns 1-2: no org yet, not run.
  `rederive_quality.py --compare`: `compared 246 keys, 0 mismatches` (`rederived/mismatches.txt`; no F-G0-1 occurrence). End view: alarms repeat `no`, cost `no`; case total 19 runs (14 user, 5 relayed).

## Failed calls, harness notes
- No harness failure, no retry, no boundary failure (every `run_turn.sh` returned its last line; 12 of 12 exit 0). No usage-limit, quota or throttle text in any turn's stdout or stderr.
- `finish_stream.sh`: 0 failed steps (`finish-steps.txt`). The injection console output is in `injection/injection-console.txt`.
- Harness fact: `skill-check.txt` is written after turn 1 only (frozen `skill_check.sh` has no end mode), so its stratum line is the turn-1 state; the final stratum is in `measures/skill-check-end.*`.

## Cleanup and safety
- Profile copied to `profiles/`, compared (cmp), deleted from `~/.kiro/agents` at 2026-10-26T09:15:15Z (`profiles/creations.txt`, `deletions.txt`); `~/.kiro/agents` holds exactly the six pre-existing files again.
- `safety-before.txt` / `safety-after.txt` / `safety-diff.txt`: the diff is the label line, two directory mtimes and the new `/tmp/hirearchy-g0-m1-s3-*` directory name only; every md5 line is identical
  before and after (owner's `~/.kiro/settings/*`, `~/.kiro/agents/*`, global SKILL.md `a3e46347b70a7ece5f734f70198c607f`, `memories.db` `d7581238189dcb31ef2f6c70a1fb525a`).
- Ambient snapshots (`ambient/`, 26 files): skills listings and `memories.db` md5 identical in all; the memories directory listing md5 changed once (`6183f6be...` -> `db7edae0...`, during turn 1: kiro's own
  session start in the owner's home, as in m1-s1 and m1-s2); the file did not change. Recorded, not attributed.
- The sandbox is left in place for the aggregation and teardown steps.

## Validity against design 20.1 / protocol 8 (E7 11 H1-H8)
H1 no assistant call failed (12 of 12 exit 0). H2 skill md5 `a3e46347...` on disclosure, the rule holds in M1 (global = workspace = repo), server bound to `S/org`. H3 workspace settings md5
`05d30ccbfd35530747c8a542eb67985c`, no steering block, no "Workflow Orchestration"; the memory index is present, the arm's recorded condition. H4 every seat claude-sonnet-5.5 / high (org run logs,
12 assistant invocations with `--effort high`, session `modelId`/`effortLevel`, `reasoningModelId` `qdev::claude-sonnet-5.5`; `model_check.sh all`: OK). H5 injection as specified (md5, once, after the
delivery turn, correct `revises`, text identity). H6 no unknown actor; empty freeze diff; one kiro-cli version. H7 only protocol lines. H8 no run failed or was throttled; no usage-limit or quota error.
**Verdict: m1-s3 is VALID** (judged against section 20.1 only; not scored).
