# G0 stream m1-s1 run log (facts only; stream step 4 of 11, workflow `wf_c415acfac4f09f84`)

Arm M1 (the owner's ambient kiro memories as they are), stream 1 of 3. Label `m1-s1`. No scoring was done by this step; the measure scripts that
`finish_stream.sh` runs wrote their outputs to `measures/` and `rederived/` unread (the aggregation step reads and scores them).

## Gates and setup (`setup.txt`, `skill-check.txt`, `safety-before.txt`)
- Sandbox `S` = `/tmp/hirearchy-g0-m1-s1-1792992820` (epoch 1792992820). No dedicated kiro home (arm M1): the chat ran under `env -u KIRO_HOME` (`turn-NN.cmd.txt`).
  Set up 2026-10-26T05:33:58Z by `run_arm.sh m1 1 --setup`.
- Gates (before the first turn): `protocol.md` md5 `08cccd6458f5f418b4d388cb93d633b5` = `protocol.md5`; `harness/MD5SUMS` 48 lines, no mismatch;
  HEAD `3c841bb9cdde666c6ea8b00bb2edfeae68c256db`; **freeze diff before: empty**; repo SKILL.md, global SKILL.md and workspace copy all
  `a3e46347b70a7ece5f734f70198c607f`; `claude-sonnet-5.5` listed; kiro-cli 2.33.0; no G0 process referenced the sandbox; other G0 streams running: 0.
- Profile `hirearchy-study-g0-m1-s1-assistant` created in `~/.kiro/agents` (md5 `70dc85d3b33e7b351e00468b4b44a353`, 05:33:40Z); it differs from m0-s1's profile only in
  `name`, `description` and `ORG_ROOT`; `kiro-cli agent validate` exit 0.
- After turn 1 (`ambient-context.txt`): `<memories>` block present **True** (19 global memories, 20 index titles listed incl. the spurious `TITLE`; the arm's recorded condition, not H3),
  `<steering-files>` False, "Workflow Orchestration" False; `session_start` 6 666 chars; `modelId` claude-sonnet-5.5, `effortLevel` high, `memoryConfig` read_write/reflection true.
  First `disclose_context` of the skill: turn 1, call #2, 05:34:24.065Z, uri = the workspace copy, md5 `a3e46347...` (valid). First `propose_org`: turn 2, call #10, 05:35:58Z;
  first `feedback`: turn 6, call #24, 05:51:14Z. So the skill was activated before both (stratum A by E7 4.4.1; `skill-check.txt` was written right after turn 1 and says n/a
  because no `propose_org` existed yet; the aggregation step records the stratum).

## Turns (13 user turns of the cap of 15; Lena's rule ids and facts are in `lena-lines.txt`; every `kiro-cli chat` call exit 0)
| T | UTC start-end | Lena (rule) | Assistant outcome |
|---|---|---|---|
| 1 | 05:34:11-05:34:43 | H1 | 8 elicitation items, plus an offer to make the first request on 19 Oct |
| 2 | 05:35:25-05:36:08 | H2 + L-INF + L-VAGUE + L-FIRST (= E7 s1 t02 bytes) | PLAN FOR YOU, Budget 12 per request, one T-WARN warning (16), T-BUDGETQ as the block's last line; the assistant adds "I'll keep 12 unless you say otherwise ... or \"16\"" (choice restated, no recommendation) |
| 3 | 05:36:43-05:41:53 | **L-BUDGET-Q + H5 (adjusted)**: "Keep it as it is. Great, approve. I'll wait." | team ran (9 runs); memo 1 written and reviewed, **not copied**, 4 questions first (D8 draft) |
| 4 | 05:42:34-05:42:56 | factual answers (Sam 2026-10-09; Marta 2026-10-14; Lee none is right; "just an action, not a decision") | human rework task `root-245b` planned; first spend question (budget 5, 2 over 12) |
| 5 | 05:43:28-05:47:00 | L-FUND ("Yes, fund it - but please keep an eye on the cost.") | **memo 1 first delivery** (copy `deliverables/memo-2026-10-05.md`, md5 `72931fe5...`, dates = key, no Summary line); 14 runs |
| inj | 05:47:52-05:50:24 | (injection, no turn) | injected task `20261026T054752706554-root-5079`, done, 5 of 6 runs |
| 6 | 05:50:52-05:51:23 | H6, Summary-only form (= E7 s1 t05 / s2 t06 / s3 t06 bytes) | recorded the reject; asked one contract item (C3) and said a rework would cost about 5 more runs (conditional, no question) |
| 7 | 05:52:06-05:55:42 | "Yes, add it." | contract change recorded (C10); rework made, **not copied** (Summary line quoted, one question first); told Lena about the unrequested rework (rejected it, 5 runs its own spend) |
| 8 | 05:56:19-05:56:46 | L-KEEP + L-INJ: "Keep it as it is. I don't know anything about that rework - I didn't ask for it." | rework delivered (copy replaced, md5 `41c11ea0...`); apologised for the unrequested rework |
| 9 | 05:57:24-06:00:24 | memo-1 accept (dropped form) + L-INJ + next memo + I'll wait (= E7 s1 t07 bytes) | accept recorded; memo 2 written, **not copied**, 4 questions first |
| 10 | 06:01:05-06:01:26 | "No need for 'probably'. Sam's 2026-10-21 is right. Lee's none is right. No, it's just an action, not a decision. Keep it as it is." | **memo 2 delivered** (copy md5 `893b0535...`) |
| 11 | 06:02:02-06:04:54 | memo-2 accept + next memo (= E7 s1 t09 bytes) | accept recorded; memo 3 written, **not copied**, 3 questions first |
| 12 | 06:05:28-06:08:31 | "No, nothing for Marta to do there, leave it out. Yes, that counts. Lee's should be 2026-10-30." | **memo 3 delivered** (copy md5 `b3b4da71...`) |
| 13 | 06:09:07-06:09:27 | memo-3 accept: "This version is right now, thanks - keep it." (= E7 s1 t11 bytes) | recorded the accept; no question to Lena; stream ended |

(Times are `turn-times.txt`'s wall-clock start-end of each `kiro-cli chat` call.)

## Org runs (`run-counts-by-turn.txt`, `cost.txt`)
- 39 org runs (34 counted toward the cap of 45; 5 in the injection window). 39 run logs, all `# exit 0 after`, 39 of 39 `# cmd:` lines with `--model claude-sonnet-5.5` and `--effort high`;
  no throttle mark, no credit note, no exit 75, no `[run error]`, no `# kiro:` failure line. All 39 `# cwd:` under `~/Library/Application Support/hirearchy/kiro-cwd`.
  `model_check.sh org` OK after every turn from turn 3 and before/after the injection; `model_check.sh assistant` OK after every turn; `model_check.sh all` OK.
- Assistant credits (`cost.txt`): 21.9189 over 13 turns. Org-run credits are for the aggregation step.
- `hirearchy check` (`observe-check.txt`): all checks passed, exit 0.

## Injection (`injection/`)
- Script md5 `1c4e7824e448a3a34e24a7b759a59fcd`; run once, after the turn that delivered memo 1 (turn 5; the turn-3 output was a draft, D8), before Lena's turn 6;
  `--revises 20261026T054345276316-root-245b` (identification in `injection/memo1-identification.txt`); window `2026-10-26T05:47:52 2026-10-26T05:50:24`
  (`window.txt`); title/note md5s match (`text-identity.txt`); 3 polls, 1 quick reply, settled; `source: relayed`, budget 6; no `revise_playbook` call in the window
  (`window-runs.txt`: 0). No scheduler was running when it started.

## Schedulers and signals (`scheduler-survival.txt`)
- 6 schedulers (5 started by the assistant's server, 1 by the injection script), 6 of 6 with `scheduler.exit` `finished: no open tasks`; 0 `scheduler.signal`; 0 `run.orphan`;
  0 killed runs. No scheduler was running at the end of any assistant turn (each exited 2.4-58.5 s before the turn's end or between turns). **No unexplained scheduler.signal.**

## Quality view
- `quality --json` after turns 3-13 (`quality/turn-NN.json`) and at the end (`quality/end.json`); 26 calls recorded in `quality/calls.txt` (13 turn snapshots + end, each with its
  `cli.command` event file as known harness actors); turns 1-2: no org yet, not run. `rederive_quality.py --compare`: `compared 262 keys, 0 mismatches` (`rederived/mismatches.txt`;
  no F-G0-1 occurrence).

## Failed calls, harness notes
- No harness failure, no retry, no boundary failure (every `run_turn.sh` returned its last line). Each turn's stderr holds kiro's own log lines (as in m0-s1).
- The assistant's tool calls: 66 in all; the file's total line says 3 unsuccessful, and 4 calls show `status=failed` (turn 1 `hirearchy::services`; turn 7 `hirearchy::define_service`, `hirearchy::observe` and an `execute_bash` diff; see `assistant-tool-calls.txt`); product behaviour, not harness failures.
- `finish_stream.sh`: 0 failed steps.

## Cleanup and safety
- Profile `hirearchy-study-g0-m1-s1-assistant` copied to `profiles/`, compared (cmp), deleted from `~/.kiro/agents` at 2026-10-26T06:10:02Z (`profiles/creations.txt`, `deletions.txt`);
  `~/.kiro/agents` holds exactly the six pre-existing files again.
- `safety-before.txt` / `safety-after.txt` / `safety-diff.txt`: the diff is the label line, two directory mtimes and the new `/tmp/hirearchy-g0-m1-s1-*` directory name only. Every
  md5 line is identical before and after: the owner's `~/.kiro/settings/*` (`cli.json` `8b4f0599...`, `cli.json.lock` `9070b152...`), `~/.kiro/agents/*`, the global SKILL.md
  (`a3e46347b70a7ece5f734f70198c607f`) and `memories.db` (`d7581238189dcb31ef2f6c70a1fb525a`, 114 688 bytes). `/Users/aminalizadeh/organization` unchanged in the snapshot.
- Ambient snapshots (`ambient/`): the skills listings and `memories.db` md5 are identical in all snapshots (setup, 13 before/after pairs, end). One difference: the mtime of the directory
  `~/.kiro/memories` moved 05:32:23Z -> 05:34:18Z during turn 1 (between `turn-01-before` and `turn-01-after`), so the "memories listing md5" changed once
  (`aab92862...` -> `9eecd867...`); the file `memories.db` itself (md5 and mtime 04:18:59Z) did not change. kiro's own session start in the owner's home, as in the preflight probe. Recorded, not attributed.
- **Freeze after: `git diff --stat 3c841bb9 HEAD -- src skills pyproject.toml uv.lock` is empty** (`setup.txt`, "AFTER the last turn"); HEAD unchanged; md5 gates held
  (`protocol.md` and 48 harness lines); `docs/research/` and `studies/G0-noise-baseline/` untracked, nothing staged, committed or pushed. No process references the sandbox.
- The sandbox `/tmp/hirearchy-g0-m1-s1-1792992820` is left in place for the aggregation and teardown steps.

## Validity against design 20.1 / protocol 8 (E7 11 H1-H8)
H1 no assistant call failed (13 of 13 exit 0). H2 skill md5 `a3e46347...` on disclosure, the rule holds in M1 (global = workspace = repo), server bound to `S/org`.
H3 workspace settings md5 `05d30ccbfd35530747c8a542eb67985c`, no steering block, no "Workflow Orchestration"; the memory index is present, the arm's recorded condition.
H4 every seat claude-sonnet-5.5 / high (39 run logs, 13 assistant invocations with `--effort high`, session `modelId`/`effortLevel`, `reasoningModelId` `qdev::claude-sonnet-5.5`).
H5 injection as specified (md5, text identity, once, after the delivery turn). H6 no unknown actor (known actors only: the assistant's servers, the schedulers, the injection server,
the 26 read-only `quality` calls and the after-stream reads); empty freeze diff; one kiro-cli version (2.33.0). H7 only protocol lines (L-BUDGET-Q used once, turn 3).
H8 no run failed or was throttled; no usage-limit or quota error. **Verdict: m1-s1 is VALID** (judged against section 20.1 only; not scored).
