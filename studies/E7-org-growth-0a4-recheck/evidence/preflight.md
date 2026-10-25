# E7 preflight (protocol 4.14; workflow step 2 of 9, `wf_31a4e82c906df7ea`)

Run 2026-10-25, 06:41-06:56 UTC (local WET = UTC), by the preflight step. Facts only. No stream, assistant stream session or stream sandbox was started. No product file, harness file or protocol file was changed. Nothing was staged, committed or pushed. The user's organization, `~/.kiro/skills/`, the user's files in `~/.kiro/agents` and the 0b worktree were not touched.

Raw files are under `evidence/preflight/` unless a path is given. Paths below are relative to `/Volumes/workspace/hirearchy/studies/E7-org-growth-0a4-recheck/evidence/`.

**Result: PASS**

| # | Check (protocol 4.14 item) | Result | Evidence |
|---|---|---|---|
| 1 | md5 gates (item 1) | PASS | `preflight/gates.txt` |
| 2 | Freeze (item 2) | PASS | `preflight/gates.txt`, `deterministic/at-18a4531/freeze-before.txt`, `freeze-after.txt` |
| 3 | Safety snapshot before (item 3) | PASS | `safety-before.txt`, `preflight/ambient-start.txt` |
| 4 | kiro-cli version, claude-sonnet-5.5 listed (item 4) | PASS | `preflight/kiro-cli.txt`, `preflight/model-checks.txt` |
| 5 | Deterministic part (item 5; protocol 4.9) | PASS: 78 of 78, 29 of 29, 26 of 26 | `deterministic/SUMMARY.md`, `deterministic/at-18a4531/` |
| 6 | Ambient probe (item 6) | PASS | `probe/` |
| 7 | One real org-agent run through the real scheduler (item 7) | PASS | `preflight/lead-run.log`, `preflight/scheduler-run.txt`, `preflight/org-events-all.jsonl`, `preflight/org-kiro-session/` |
| 8 | Injection script: poll check, dry-run, selftest (item 8) | PASS | `preflight/poll-check/`, `preflight/injection-dryrun-selftest.txt` |
| 9 | Deletion (item 9) | PASS | `preflight/deletions.txt`, `probe/probe-profile-deletion.txt` |
| 10a | Scheduler check (a), the harness form (item 10) | **PASS** (attempt A1) | `preflight/detach/a/`, `preflight/detach/samples/A1/` |
| 10b | Scheduler check (b), C1's V0 repeated once (item 10) | **PASS** (attempt B1): the scheduler died and `scheduler.signal` was recorded | `preflight/detach/b/`, `preflight/detach/samples/B1/` |
| 11 | Safety snapshot after, and diff (item 11) | PASS | `preflight-safety-after.txt`, `preflight-safety-diff.txt`, `preflight/ambient-end.txt` |

The brief's order was followed (gates and freeze, kiro-cli, safety snapshots, ambient probe, org-agent run with the poll check, check (a), check (b), then the deterministic part). Protocol 4.14 puts the deterministic part before check (a); item 10 needs no result of item 5, so the order changes nothing. Item 9's deletion ran after item 8 and before item 10, as in the protocol.

## 1. md5 gates: PASS (`preflight/gates.txt`)
- `md5 -q protocol.md` = `0acc2b4191b8cbfa5f4bb6197b877de1` = `protocol.md5` = `freeze.txt`. No `protocol-amendment-*` file exists. Checked again at the end of the step: unchanged.
- `harness/MD5SUMS`: 17 lines, no MISMATCH (also at the end of the step). `md5 -q MD5SUMS` = `d1f24687c9cd1587466d24db42ce59d0` (as in `freeze.txt`).
- Injection script `1c4e7824e448a3a34e24a7b759a59fcd` (= E6's; `cmp` against E6's copy is identical). Notes `903e3bbf...`, `3893bd63...`, `9976a765...` and `answer-key.md` `2fb69bbef857c2bd4862cd5dd8be9da8`, as in protocol 4.6.
- The nine C1 tools that item 10 copies match the md5s in `freeze.txt`.
- Skill: global `~/.kiro/skills/hirearchy/SKILL.md` (read-only md5), the repo file and `git show 18a4531:skills/hirearchy/SKILL.md` are all `fd89a7fda55b8f342cf0306173c363fb`.

## 2. Freeze: PASS
`git rev-parse HEAD` = `18a4531662060ddf0b78923edee8d61909bc9d6d`, branch `main`. `git diff --stat 18a4531 HEAD -- src skills pyproject.toml uv.lock` is empty before the checks, after the deterministic runs, and in both safety snapshots. `git status --porcelain`: `?? docs/research/` and `?? studies/E7-org-growth-0a4-recheck/` only.

## 3. Safety snapshot before: PASS
`zsh harness/safety-snapshot.sh preflight-before > safety-before.txt` (exit 0, 06:42:59Z), after the read-only gates and before any sandbox, profile, session or process of the preflight existed. The ambient snapshot `preflight/ambient-start.txt` (exit 0, 408 lines) followed. Global SKILL.md `fd89a7fd...`; `memories.db` md5 `d91d954fc5ff92c41d0c285e812684c4`; `~/.kiro/agents` held exactly the six pre-existing files.

## 4. kiro-cli: PASS
`kiro-cli --version` = `kiro-cli 2.33.0` (the version the protocol records). `harness/model_check.sh listed preflight`: `RESULT: spreflight listed: OK`, exit 0; `listed: claude-sonnet-5.5: yes (claude-sonnet-5.5    1.30x credits      Claude Sonnet 5.5 model with 1M context window)`. No substitution.

## 5. Deterministic part: PASS (`deterministic/SUMMARY.md`)
- Command 1 (`test_org_growth_0a.py`, `test_org_growth_0a2.py`, `test_no_bypass_0a2.py`): **78 passed**, exit 0.
- Command 2 (`git grep`): the 7 files the protocol names.
- Command 3 (`-v`: `test_org_growth_0a2.py`, `test_org_growth_0a3.py`, `test_org_growth_0a4.py`, `test_scheduler_signal.py`, `test_scheduler_detach.py`): **29 passed**, 0 skipped/xfail/failed/error, exit 0. Every named test of protocol 4.9 is `PASSED`: E5's three D-E4-7 replays, the five 0a.3 replays (six lines with the two `#21`/`#23` parameters), the 0a.4 replays A-1 to A-5, B-1, B-2 (two tests), F-1 and F-2 (both parameters), the three C-1 tests and the C-2 test.
- Command 4 (`-v`: the E4, E5 and E6 replay kits): **26 passed** (6 in `test_e6_replay_kit.py`), exit 0.
- Not run, as the protocol says: C-3 (no such test exists; C3 was not built) and S-1 (the needle tests of `src/hirearchy/skill/tests/`).
- Linux (report only): the diff of `scheduler/`, `processes/` and `telemetry/` against `18c4ffb` is **not empty** (14 files; `processes/` unchanged). **Linux not shown at `18a4531`.**
- No full suite was run.

## 6. Ambient probe (4.5): PASS
Probe dir `/tmp/hirearchy-e7-probe-1792910605` (left in place). Workspace skill copy `fd89a7fd...`, `.kiro/settings/cli.json` `05d30ccbfd35530747c8a542eb67985c`.
- Profile `~/.kiro/agents/hirearchy-study-e7-probe.json`, md5 `603327270f6c0efa420715ccaa569124` (V3 shape; `kiro-cli agent validate` ran clean), created 06:43:25Z, deleted 06:44:40Z after a byte comparison with `probe/hirearchy-study-e7-probe.json`. `~/.kiro/agents` afterwards holds exactly the six pre-existing files.
- Call (cwd = probe dir), followed by `; sleep 20` in the same tool call: `kiro-cli chat --v3 --no-interactive --trust-all-tools --effort high --agent hirearchy-study-e7-probe "List the names of the skills ..."`, exit 0. The reply lists 20 names, `hirearchy` among them.
- Session (`probe/probe-session.json`): `modelId` `claude-sonnet-5.5`, `effortLevel` `high`, `agentMode` `hirearchy-study-e7-probe`. `ambient_context.py` (`probe/probe-ambient-context.txt`): `<steering-files>` block present: False; "Workflow Orchestration" text present: False; `<memories>` block present: True (15 global memories; covariate); `hirearchy` listed. `~/.kiro/settings/cli.json` and `cli.json.lock` md5s unchanged (`probe/global-cli-md5-before.txt`, `-after.txt`).
- **Covariate, recorded:** the reply lists 20 skill names (`agents`, `autoresearch`, `commit-work`, `dubbing`, `hirearchy`, `music`, `onboarding`, `realtime`, `reverse-engineer-anything`, `setup-api-key`, `skill-generation`, `sound-effects`, `speech-engine`, `speech-to-text`, `test-driven-development`, `text-to-speech`, `update-skills-from-changelog`, `voice-changer`, `voice-isolator`, `workflow-suggest`). E6's probe listed 7. The user's `~/.kiro/skills` changed after E6 (its directory mtime is 2026-10-24T17:25:39Z; `preflight/ambient-start.txt`). The memory index now shows 15 global memories (E6: 11). Neither is an E7 harness effect or a probe failure; the streams' per-turn snapshots (4.5.1) will show whether it moves again.

## 7. One real org-agent run through the real scheduler: PASS
Sandbox `P` = `/tmp/hirearchy-e7-preflight-1792910702` (org at `P/org`); deleted (item 9). The commands are the protocol's, with the `hirearchy` on `PATH` (a uv-tool install whose package resolves to `/Volumes/workspace/hirearchy/src/hirearchy`, checked); no form needed adapting (`preflight/org-setup.txt`, `preflight/scheduler-run.txt`):
```
hirearchy init P/org --mission "E7 harness preflight (throwaway)" --model claude-sonnet-5.5      -> exit 0; ORG.md: default_model: claude-sonnet-5.5, effort: high
hirearchy --root P/org hire root lead ... --tools read,write --model claude-sonnet-5.5          -> hired lead
hirearchy --root P/org task lead --title "Preflight note" ... --budget 2                        -> task 20261025T064503483287-root-08c9
(poll check, item 8, before the scheduler started)
perl -e 'alarm shift; exec @ARGV' 900 hirearchy --root P/org run --until-done --max-runs 2
  -> lead: started run (1 message(s)) / lead: run finished in 20s / scheduler exiting: finished: no open tasks   (exit 0, 06:47:21Z-06:47:41Z)
```
Run log `preflight/lead-run.log`, `# cmd:` line: `.../_launch.py --start-deadline 60 -- kiro-cli chat --no-interactive --agent hirearchy-hirearchy-e7-preflight-1-fe3128-read-write-x752a0b32 --model claude-sonnet-5.5 --effort high --v3 --require-mcp-startup --output-format stream-json <prompt on stdin>`.
- One `--model claude-sonnet-5.5`, one `--effort high`. `# kiro: run started (engine v3)`, `[run finished] success (end_turn)`, `# exit 0 after 20s`.
- Hirearchy tool calls (RL3): `org_write lead/work/preflight.txt`, `org_read`, `org_write lead/MEMORY.md`, `report status=done`, each with a `[tool ok]` line (a `Tool Load` line precedes them). `obs events --kind tool.call` holds 9 events: the 4 by `lead` (run `lead@20261025T064721480309`, 06:47:32-06:47:37Z) equal the log's 4 calls and are all `ok`; the other 5 are root's `progress` calls of the poll check (`preflight/obs-events-tool-call.txt`).
- Org-run session (`preflight/org-kiro-session/session.json`): `agentMode` = the log's `--agent`, `modelId` `claude-sonnet-5.5`, `effortLevel` `high`, `workspacePaths[0]` = the log's `# cwd:`, `createdAt` 06:47:28.358Z inside `run.start` (06:47:21.486Z) and `run.end` (06:47:41.668Z, `ok: true`).
- `zsh harness/model_check.sh org preflight P`: `RESULT: spreflight org: OK`, exit 0. Task outcome (recorded, not the pass condition): done; `scheduler.exit` `finished: no open tasks`; `hirearchy --root P/org check`: all checks passed (`preflight/final-progress-check.txt`).

## 8. Injection script: PASS
Script md5 `1c4e7824e448a3a34e24a7b759a59fcd` = `MD5SUMS`.
- **Live poll check** (`uv --directory /Volumes/workspace/hirearchy run python <script> --poll-check --org P/org --task 20261025T064503483287-root-08c9 --out .../evidence/preflight/poll-check --max-seconds 120`, before the scheduler started, so every reply was "Not waiting: no scheduler is running"). Exit 0, 06:45:08Z-06:47:08Z. It called only `progress(task_id, wait_seconds)`.

  | Poll | Request time (UTC) | Reply | Pause before next |
  |---|---|---|---|
  | 1 | 06:45:08 | 0.0 s | 5.0 s |
  | 2 | 06:45:13 | 0.0 s | 10.0 s |
  | 3 | 06:45:23 | 0.0 s | 20.0 s |
  | 4 | 06:45:43 | 0.0 s | 40.0 s |
  | 5 | 06:46:23 | 0.0 s | 44.9 s (to the window end) |

  Final line: `polling ended (window cap: 120 seconds passed): progress(task_id) polls 5, quick replies 5, paused 119.9s in all` (`preflight/poll-check/poll-check-log.txt`). Pass rule: every poll logged; each next poll at least 5 s later; 5 polls (limit 25); the final line gives the count. Met.
- `--dry-run` (exit 0): `title md5 849fe21b... ok; note len 866 md5 4cdbcb9b... ok`. `--selftest` (exit 0) lists root's tools, including `request`, `start`, `progress`, `status` and `stop`. `python3 -B harness/test_poll_loop.py`: 7 passed, 0 failed. Text identity: byte-identical to E6's copy (`preflight/injection-text-identity.txt`).
- The full injection (`request`, `start`) was not run: no stream exists.

## 9. Deletion: PASS (`preflight/deletions.txt`)
By exact path with a path-prefix guard, after the evidence was copied and with no process referencing the sandbox: `~/Library/Application Support/hirearchy/kiro-home/hirearchy-e7-preflight-1-fe3128d7faad4dfa`, `.../kiro-cwd/hirearchy-e7-preflight-1-fe3128d7faad4dfa` and `/tmp/hirearchy-e7-preflight-1792910702` (06:48:01Z); the probe profile earlier (`probe/probe-profile-deletion.txt`). `<state>` existed before the preflight (E4, E5 and E6 `kiro-cwd` leftovers; an empty `kiro-home`), so it was kept. The probe dir stays.

## 10. The two scheduler checks (item 10): both PASS
Sandboxes `SB` = `/tmp/hirearchy-e7-detach-<epoch>`, outside every stream sandbox and apart from P. Every kiro-cli call ran with `KIRO_HOME=$SB/kiro-home` and `KIRO_CHAT_LOG_FILE=$SB/logs/<ID>-turn<k>.log`; the sandboxed `HOME` had a `kiro-cli-chat` symlink (as C1 made it). Environment variables are recorded by name only. Nothing under `~/.kiro` was read or written by these checks, apart from the kiro-cli process itself, which uses the sandbox home.

**Tools** (`preflight/c1-tools/`, `CHANGES.txt` with each `diff -u` and the copies' md5s): the nine C1 tools, changed only as protocol item 10 lists. `WT` is the repo `/Volumes/workspace/hirearchy` in `setup.sh`, `after.sh` and `mkprofile.py`; the copy source, the `timeline.py` path and the samples archive are the E7 paths; the sandbox prefix is `/tmp/hirearchy-e7-detach-`. `allowed.py`, `logfilter.py`, `sampler.py`, `summary.py`, `timeline.py` and `verdict.py` are byte-identical to C1's. (`sampler.py` still has a `--wt` option defaulting to the removed 0a.4 worktree. It is read only by the `--d-out` branch, which neither check uses; the protocol's change list does not name it, so it was left alone.)

**Setup 0, the sign-in probe** (`preflight/detach/whoami.txt`): exit 0, first line `Authenticated with API key`; `$SB0` removed. Each attempt's setup (`a-setup.txt`, `b-setup.txt`): `init`, `hire`, `task`, `validate` and `chat-help` all exit 0.

Chat calls used: 4 of 12 (A1 turns 1-2, B1 turns 1-2). Both attempts were valid on the first try, so A2/A3 and B2/B3 were not needed. The `disclose_context` call in each turn reported that no skill was available in the sandbox `KIRO_HOME`, as the model said in its replies. The model went on to its tool calls: `disclose_context`, `tool_load` and `hirearchy::progress` in turn 1, then `disclose_context`, `tool_load`, `progress` and `start` in turn 2 (`allowed.py`: ALLOWED for both attempts; `preflight/detach/a/allowed.txt`, `b/allowed.txt`).

### (a) The harness form: PASS (attempt A1; sandbox `/tmp/hirearchy-e7-detach-1792910942`, agent `c1-1792910942`)
Each turn's tool call was the chat command followed by `; echo $? > $SB/out/A1-turn<k>.exit; sleep 20`, with the sampler (window 25 s) started before it by a background call. Turn 1 exit 0. Turn 2 (`--resume`; `hirearchy::progress` then `hirearchy::start` with `until_done=false`): start 06:50:22.3Z, chat return (process gone) 06:50:47.548Z, exit 0. Stdout: `scheduler started (pid 76914; it runs until stop()); log: .../org/.runtime/scheduler.log`.

| Condition (protocol item 10 (a)) | Fact | Result |
|---|---|---|
| 1. scheduler and run alive 5 s after the return and at the sleep's end, with no `scheduler.signal` or `scheduler.exit` by then | `verdict.py`: `verdict survived`, `valid True`; `scheduler_alive_at_plus_5s True`, `run_alive_at_plus_5s True`; last sample with both alive 06:51:12.629Z (24.9 s after the return, past the sleep's end at about 06:51:07.5Z); first gone: none. Scheduler pid 76914, `ps` state `Ss`, ppid 1, pgid 76914 (re-parented to launchd). Run `child_pid` 76944 (`Ss`, ppid 76914). `run.start` 06:50:44.426Z, 2.8 s before the return. No `scheduler.signal`, no `scheduler.exit` | met |
| 2. the run ends by itself: `run.end` `ok: true`, `killed: false` | `run.end` 06:51:26.633Z (`ok: true`, `killed: false`, `exit_code 0`, `duration_ms 42207`), 39 s after the return. The ceo agent's `tool.call` events: `write ceo/MEMORY.md` and `report status=done`, both `ok` | met |
| 3. the deliberate stop records `scheduler.signal` (`SIGTERM`, `stop`), then `scheduler.exit` `stopped by SIGTERM` | after `run.end`, the scheduler was alive (`a-before-stop-ps.txt`: pid 76914, ppid 1). The stop (`HIREARCHY_STATE_DIR=$SB/kiro-state .../.venv/bin/python -c '...scheduler_control.stop()' $SB/org`) printed `scheduler stopped (pid 76914)`, exit 0, 06:51:32-06:51:34Z. Events: `scheduler.signal` 06:51:32.930Z `signal: SIGTERM`, `action: stop`, `ppid: 1`, `running: []`; then `scheduler.exit` 06:51:34.744Z `reason: stopped by SIGTERM`, `runs_started: 1`. No process names `$SB` afterwards | met |
| 4. `allowed.py` prints ALLOWED | `ALLOWED` (`preflight/detach/a/allowed.txt`) | met |

Record (`preflight/detach/a/`): `out/` (commands' stdout, stderr, start and exit files), `logs/` (kiro-cli's own log of each call), `profile.json`, `verdict.json`, `allowed.txt`, `events-all.jsonl`, `events-selected.jsonl` (`scheduler.start`, `exit`, `signal`, `run.start`, `end`, `tool.call`), `session-record-paths.txt`, `cleanup.txt`; the sample timelines, summaries and verdicts are in `preflight/detach/samples/A1/`. The scheduler's own `scheduler.log` (a 4-line file) was not copied: the sandbox was removed before the copy; the events carry the same facts. (For B1 it was copied.)

### (b) C1's V0, repeated once: PASS (attempt B1; sandbox `/tmp/hirearchy-e7-detach-1792911121`, agent `c1-1792911121`)
C1's V0 exactly: the same setup and turn 1, turn 2 with `start`'s defaults, each chat command the LAST command of its own tool call (nothing after it; timeout 900 000 ms), sampler window 15 s, `after.sh $SB B1 2 --c1b`. Turn 1 exit 0. Turn 2 (`--resume`; `progress` then `start` with defaults): start 06:53:08.3Z, return 06:53:33.037Z, exit 0. Stdout: `Scheduler started (pid 78480). It exits by itself when the work is done. Log: ...`.

| Item | Fact |
|---|---|
| `scheduler.signal` written by turn 2's scheduler (pid 78480), after its `scheduler.start` (06:53:30.191Z) | **recorded**, 06:53:31.807Z: `signal: SIGTERM`, `action: stop`, `ppid: 1`, `running: ["ceo@20261025T065330192469"]` |
| time against the chat's return | 1.23 s before the return (06:53:33.037Z); the scheduler's last sample alive 06:53:32.192Z, first sample gone 06:53:32.301Z, 737 ms before the return; the run's last alive sample 06:53:31.760Z, first gone 06:53:31.866Z |
| what followed | `run.end` 06:53:32.214Z for the one run in `running` (`ok: false`, `killed: true`, `exit_code -15`, `duration_ms 2016`, `error: interrupted by scheduler shutdown`, `budget_after 1`); then `scheduler.exit` 06:53:32.215Z `reason: stopped by SIGTERM`, `runs_started: 1`. No `run.orphan` |
| `verdict.py` class | `died` (`valid True`); `--c1b`: `any_signal_recorded True`, `m5_signature False` |
| `allowed.py` | `ALLOWED` |

So the death C1 reproduced (V0, 2 of 2) reproduced again in 1 of 1, under 0a.4's C2, and C2 recorded the signal before the stop: this is the record that E6 lacked. The scheduler was gone 0.7 s before the chat returned, as in C1 (0.5-0.7 s). Record: `preflight/detach/b/` (as for (a), plus `scheduler.log`) and `preflight/detach/samples/B1/`. The sandbox was removed after the copy (`b/cleanup.txt`); no process named it.

**Reading, report only:** with the chat as the last command of the tool call the scheduler died and was recorded (B1); with `; sleep 20` after the chat, in the same conditions otherwise, it survived to `run.end` and to a deliberate stop (A1). That is C1's D-HARN result, repeated once each in the harness conditions E7 will use. Each is one valid attempt; neither is a rate.

## 11. Safety snapshot after: PASS
`zsh harness/safety-snapshot.sh preflight-after > preflight-safety-after.txt` (exit 0, 06:55:39Z) and `preflight/ambient-end.txt`. `diff safety-before.txt preflight-safety-after.txt` (`preflight-safety-diff.txt`) shows three differences, all expected:
1. the label and date lines;
2. the mtime of the directory `~/.kiro/memories` (06:41 to 06:44, from the probe's kiro session). `memories.db` md5 is unchanged (`d91d954f...` before and after);
3. the mtime of the directory `~/.kiro/agents` (Oct 24 18:40 to Oct 25 06:44), from the probe profile's creation and deletion.

Unchanged: all `~/.kiro/settings/*` md5s, the global SKILL.md md5, the file list and md5s of `~/.kiro/agents/*`, `/Users/aminalizadeh/organization` (file count, newest mtime and stat digest), repo `git status`, HEAD, the freeze diff, the `protocol.md` md5 and `/Volumes/workspace/orgs`. The ambient snapshots differ only in their label and date lines, the mtime of the `~/.kiro/memories` directory and the memories listing md5 that follows from it; the skills listing md5 (`6ee25f86...`) and the skills-through-links md5 (`c21852c3...`) are the same at the start and the end. The preflight created and deleted one profile (`hirearchy-study-e7-probe`, md5 `603327270f6c0efa420715ccaa569124`) and no other.

## Harness facts noticed (recorded; nothing changed, nothing blocks a stream)
- `model_check.sh` labels its output `spreflight` (it prefixes `s` to its `<N>` argument). Cosmetic, as in E5 and E6. It checks the org run log's `# cmd:` line only; the org-run session's `modelId` and `effortLevel` were read by hand (item 7).
- `ambient_context.py` lists a spurious memory title `TITLE` (16 titles listed, 15 memories shown). Cosmetic, as in E5 and E6.
- No `.runtime/scheduler.log` file existed in the preflight org (item 7), as in E5 and E6. The scheduler checks' orgs did have one.
- The preflight org's run took 20 s (E6's 89 s); no throttle line.
- The assistant profile template and `run_turn.sh` were not exercised (no assistant stream session was started); the probe used the template JSON with the probe name, and the probe's chat call used the `; sleep 20` form by hand. `harness/ambient_snapshot.sh` ran twice (start and end) without error.
- Other kiro-cli sessions of the user were running during the preflight (the user's own TUI sessions and the workflow's); none of them names an E7 sandbox, profile or org.

## Files and state left behind
- Evidence: `evidence/preflight/`, `evidence/probe/`, `evidence/deterministic/`, `evidence/safety-before.txt`, `evidence/preflight-safety-{after,diff}.txt`, this file.
- Still present: `/tmp/hirearchy-e7-probe-1792910605` (the probe dir). Removed: the preflight sandbox, its kiro home and scratch cwd, both scheduler-check sandboxes. No `hirearchy-study-e7-*` profile is in `~/.kiro/agents`. No process names an E7 sandbox.
- No E4, E5 or E6 file was changed. Nothing was staged or committed.

Result: PASS
