# G0 preflight (protocol section 11 with E7 4.14; step 2 of 11, workflow `wf_c415acfac4f09f84`)

Run 2026-10-26, 04:37-04:49 UTC (local WET = UTC), by the preflight step. Facts only. No stream, assistant stream session or stream sandbox was
started. No product file, harness file or protocol file was changed. Nothing was staged, committed or pushed. `/Users/aminalizadeh/organization`,
`~/.kiro/skills/` (the global SKILL.md was read by `md5 -q` only), the user's files in `~/.kiro/agents` and `/Volumes/workspace/orgs` were not touched.
No credential was copied, printed or recorded (the sign-in checks keep only the first line `Authenticated with API key`; environment variables are named, never valued).

Raw files are under `preflight/` unless a path is given. Paths below are relative to `/Volumes/workspace/hirearchy/studies/G0-noise-baseline/evidence/`.

**Result: PASS**

| # | Check | Result | Evidence |
|---|---|---|---|
| 1 | md5 gates (protocol 0) | PASS | `preflight/gates.txt` |
| 2 | Freeze (HEAD, empty diff) | PASS | `preflight/gates.txt`, `deterministic/at-3c841bb9/freeze-{before,after}.txt`, both safety snapshots |
| 3 | Safety snapshot before, ambient start | PASS | `safety-before.txt`, `preflight/ambient-start.txt` |
| 4 | kiro-cli version, claude-sonnet-5.5 listed | PASS | `preflight/kiro-cli.txt`, `preflight/model-checks.txt` |
| 5 | Deterministic part (design 21) at 3c841bb9 | PASS: 116 passed (113 replays + 3 costs) | `deterministic/at-3c841bb9/` |
| 6 | Ambient probe, arm M1 (owner's kiro home) | PASS | `probe/m1/` |
| 7 | M0 dedicated kiro home: prepare, sign-in, probe | PASS (authenticated; no memories index) | `preflight/m0-home/`, `probe/m0/` |
| 8 | Skill rule in both arms | PASS (all md5s identical) | `preflight/skill-rule.txt` |
| 9 | One real org-agent run (claude-sonnet-5.5, `--effort high`) through the real scheduler | PASS | `preflight/lead-run.log`, `preflight/scheduler-run.txt`, `preflight/org-events-all.jsonl`, `preflight/org-kiro-session/` |
| 10 | Injection script: live poll check, dry-run, selftest, offline test | PASS | `preflight/poll-check/`, `preflight/injection-dryrun-selftest.txt` |
| 11 | Deletion | PASS | `preflight/deletions.txt`, `probe/m1/probe-profile-deletion.txt`, `probe/m0/probe-profile-deletion.txt` |
| 12 | Scheduler check (a), the harness form | **PASS** (attempt A1, first try) | `preflight/detach/a/`, `preflight/detach/samples/A1/` |
| 13 | Safety snapshot after, and diff | PASS | `preflight-safety-after.txt`, `preflight-safety-diff.txt`, `preflight/ambient-end.txt` |

Scheduler check (b) (C1's V0) was **not repeated**, as protocol section 11 and 15 item 16 say (E7 has its record). The brief's order was followed
for items 1-4; the deterministic part ran right after item 4 (it needs no result of the later items and no model call).

## 1. md5 gates: PASS (`preflight/gates.txt`)
- `md5 -q protocol.md` = `08cccd6458f5f418b4d388cb93d633b5` = `protocol.md5` = `freeze.txt`. No `protocol-amendment-*` file exists. Unchanged again at the end of the step.
- `harness/MD5SUMS` (48 lines, md5 `be21347995b821185a2adaba36d8390c`, as in `freeze.txt`): no MISMATCH, checked at the start and at the end. `script/MD5SUMS` (md5 `d92eff5043ad1f3d0856a78cbccda796`): no MISMATCH.
- E7 pin: `script/e7-protocol.md` and E7's `protocol.md` both `0acc2b4191b8cbfa5f4bb6197b877de1`; E7's `harness/MD5SUMS` md5 `d1f24687c9cd1587466d24db42ce59d0`, 17 lines.
- Injection script `1c4e7824e448a3a34e24a7b759a59fcd` (= E7's, `cmp` identical); text source `daf2085495c213ee9b1c3c6bff1bbd55` (= E2's). Notes `903e3bbf...`, `3893bd63...`, `9976a765...`; answer key `2fb69bbef857c2bd4862cd5dd8be9da8`: all as in the protocol.
- The C1 tools the scheduler check copies (`docs/research/org-growth/phase-0a4/c1-tools/`): the six unchanged tools equal E7's copies byte for byte (`preflight/c1-tools/CHANGES.txt`).

## 2. Freeze: PASS
`git rev-parse HEAD` = `3c841bb9cdde666c6ea8b00bb2edfeae68c256db`, branch `main`. `git diff --stat 3c841bb9 HEAD -- src skills pyproject.toml uv.lock` is **empty** before the checks, before and after the deterministic run, in both safety snapshots and at the end. `git status --porcelain`: `?? docs/research/` and `?? studies/G0-noise-baseline/` only. The installed `hirearchy` package resolves to `/Volumes/workspace/hirearchy/src/hirearchy/__init__.py` (`preflight/hirearchy-package-path.txt`).

## 3. Safety snapshot before: PASS
`zsh harness/safety-snapshot.sh preflight-before > safety-before.txt` (exit 0, 04:38:28Z), before any sandbox, profile, session or process of the preflight existed; then `harness/ambient_snapshot.sh preflight-start` (exit 0, 408 lines). Global SKILL.md `a3e46347...`; `memories.db` md5 `d7581238189dcb31ef2f6c70a1fb525a`; `~/.kiro/agents` held exactly the six pre-existing files; `~/.kiro/settings` md5s recorded in the file (`cli.json` `8b4f0599...`); no `/tmp/hirearchy-g0-*` directory existed.

## 4. kiro-cli: PASS
`kiro-cli --version` = `kiro-cli 2.33.0` (the version E7 recorded). `harness/model_check.sh listed preflight`: `RESULT: preflight listed: OK`, exit 0; `listed: claude-sonnet-5.5: yes (claude-sonnet-5.5    1.30x credits      Claude Sonnet 5.5 model with 1M context window)`. No substitution.

## 5. Deterministic part (design 21): PASS (`deterministic/at-3c841bb9/SUMMARY.md`)
At `3c841bb9`, empty freeze diff before and after, scoped (no full suite), from `/Volumes/workspace/hirearchy`:
```
uv run pytest -v -p no:cacheprovider tests/e2e/test_org_growth_0b_replays.py tests/e2e/test_org_growth_0b_costs.py
```
Exit 0; **`116 passed in 2.77s`** (113 in the replays file, 3 in the costs file); no skipped, xfail, failed or error. `test_e3_7` (the repeat alarm's firing variant, `r2-links-r1`) and the E3-9 constructed variants pass; `test_e7s3_1` to `test_e7s3_7` and `test_e7_all` for E7 s1, s2, s3 pass; `test_e_published_counts`, `test_e2_published_counts`, `test_a5_published_counts` pass. Output kept verbatim in `pytest-output.txt` (stderr empty).

## 6. Ambient probe, arm M1: PASS (`probe/m1/`)
Probe dir `/tmp/hirearchy-g0-probe-m1-1792989560` (left in place). Workspace skill copy `a3e46347...`, `.kiro/settings/cli.json` `05d30ccbfd35530747c8a542eb67985c` (= `harness/workspace-cli.json`). Throwaway profile `~/.kiro/agents/hirearchy-study-g0-probe-m1.json` (the harness template with `name`, `description`, `ORG_ROOT` changed), md5 `33670628ac52d1a2d194a78e497db267`, created 04:39:20Z, deleted 04:48:17Z after a byte comparison with `probe/m1/hirearchy-study-g0-probe-m1.json`.
- Call (cwd = probe dir, `env -u KIRO_HOME`, as `run_turn.sh` runs M1), followed by `; sleep 20`: `kiro-cli chat --v3 --no-interactive --trust-all-tools --effort high --agent hirearchy-study-g0-probe-m1 "List the names of the skills you can activate, one per line. ..."`, exit 0. The reply lists 20 skill names, `hirearchy` among them.
- Session (`probe/m1/probe-session.json`): `modelId` `claude-sonnet-5.5`, `effortLevel` `high`, `agentMode` the probe profile. `ambient_context.py` (`probe/m1/probe-ambient-context.txt`): `<steering-files>` block present: False; "Workflow Orchestration" text present: False; `<memories>` block present: True (**19** global memories; E7 saw 15; covariate); `hirearchy` listed.
- `~/.kiro/settings/cli.json` and `cli.json.lock` md5s unchanged (`probe/m1/global-cli-md5-before.txt`, `-after.txt`).

## 7. M0 dedicated kiro home: PASS (`preflight/m0-home/`, `probe/m0/`)
- **Prepared** by `zsh harness/prepare_m0_home.sh preflight /tmp/hirearchy-g0-m0home-preflight-1792989639` (exit 0; a dry run came first). `preflight/m0-home/setup.txt`: 5 settings files copied byte for byte with md5s recorded (`cli.json`, `cli.json.lock`, `session-response-indexing.json`, `survey_state.json`, `workflow_survey_state.json`; their contents were not printed); the 4 `mcp.json*` files were **not copied**; `skills/hirearchy/SKILL.md` copied (md5 `a3e46347...`, because the global file has the same md5); the other 20 top-level skill entries of the owner are symlinks to `$HOME/.kiro/skills/<name>`. No `memories/`, `sessions/`, `secrets.json`, `steering/` or credential file was made by the script.
- **Authentication, no credential copied.** `KIRO_HOME=<M0H>/.kiro kiro-cli whoami </dev/null`: exit 0, first line `Authenticated with API key` (`probe/m0/whoami.txt`). The chat authenticates through the environment the facilitator's process inherits (kiro's own log line names the mechanism, `KIRO_API_KEY env var`; the value was never printed or written). A scan of the evidence folder for the key's value found no file containing it (the value itself was not printed), and `preflight/m0-home/listing-final.txt` shows no secrets, token, auth or mcp file in the M0 home.
- **Probe in it** (`probe/m0/`): probe dir `/tmp/hirearchy-g0-probe-m0-1792989651` (left in place), profile `hirearchy-study-g0-probe-m0.json` in `<M0H>/.kiro/agents/` (md5 `8f79cc7cbbbf1ca39155427470603173`), the chat under `env KIRO_HOME=<M0H>/.kiro` followed by `; sleep 20`, exit 0, 20 skill names, `hirearchy` among them. Session: `modelId` `claude-sonnet-5.5`, `effortLevel` `high`. `ambient_context.py`: **`<memories>` block present: False** (memory index titles: 0; `session_start` content 2 029 chars against M1's 6 669); `<steering-files>` block present: False; "Workflow Orchestration" text present: False.
- **Same skill names as the M1 probe: yes** (the two replies sorted are identical; `skill-rule.txt`).
- Global `cli.json` / `cli.json.lock` md5s unchanged by the M0 probe (`probe/m0/global-cli-md5-{before,after}.txt`).
- **Covariate, recorded:** kiro itself created an empty `memories/memories.db` (28 672 bytes) in the M0 home during the probe call (`preflight/m0-home/listing-final.txt`); the session showed no index. Because the session's `memoryConfig` is `read_write` with `reflection: true` in both arms, a stream's assistant could write memories into the M0 home's own database during a stream; the protocol checks the M0 condition after turn 1 (section 6), and the per-turn ambient snapshots list the M0 home's `memories` entry. Nothing here needs action before the streams.
- **Deleted**: the preflight M0 home `/tmp/hirearchy-g0-m0home-preflight-1792989639` (prefix guard `/tmp/hirearchy-g0-m0home-`) after its evidence copy (`probe/m0/probe-session.json`, `probe-session-messages.jsonl`, `preflight/m0-home/setup.txt`, `listing-final.txt`) was verified (`preflight/deletions.txt`).

## 8. The skill rule in both arms: PASS (`preflight/skill-rule.txt`)
All of these are `a3e46347b70a7ece5f734f70198c607f`: the repo file, `git show 3c841bb9:skills/hirearchy/SKILL.md`, the workspace copy in the M1 probe dir, the workspace copy in the M0 probe dir, the global `~/.kiro/skills/hirearchy/SKILL.md` (read with `md5 -q` only, before and after), and the M0 home's copy. Both probe profiles name the repo file as their `skill://` resource. `skill_check.sh`'s per-stream checks (before and after turn 1) are for the streams and were not run here (they need a stream sandbox).

## 9. One real org-agent run through the real scheduler: PASS
Sandbox `P` = `/tmp/hirearchy-g0-preflight-1792989703` (org at `P/org`), outside every stream sandbox; deleted at item 11. The commands are E7's (`hirearchy` is the uv-tool install whose package resolves to the repo's `src/`); no CLI form needed adapting (`preflight/org-setup.txt`, `preflight/scheduler-run.txt`):
```
hirearchy init P/org --mission "G0 harness preflight (throwaway)" --model claude-sonnet-5.5       -> exit 0; ORG.md: default_model: claude-sonnet-5.5, effort: high
hirearchy --root P/org hire root lead ... --tools read,write --model claude-sonnet-5.5               -> hired lead
hirearchy --root P/org task lead --title "Preflight note" ... --budget 2                              -> task 20261026T044144236971-root-8142
(poll check, item 10, before the scheduler started)
perl -e 'alarm shift; exec @ARGV' 900 hirearchy --root P/org run --until-done --max-runs 2
  -> lead: started run (1 message(s)) / lead: run finished in 24s / scheduler exiting: finished: no open tasks   (exit 0, 04:44:05Z-04:44:30Z)
```
- Run log `preflight/lead-run.log`, `# cmd:` line: `.../_launch.py --start-deadline 60 -- kiro-cli chat --no-interactive --agent hirearchy-hirearchy-g0-preflight-1-ec7753-read-write-x92c7d35c --model claude-sonnet-5.5 --effort high --v3 --require-mcp-startup --output-format stream-json <prompt on stdin>`: one `--model claude-sonnet-5.5`, one `--effort high`, `--v3`. `# kiro: run started (engine v3)`, `[run finished] success (end_turn)`, `# exit 0 after 24s`. No throttle or credit line.
- Hirearchy tool calls (all `[tool ok]`): `org_write lead/work/preflight.txt`, `org_write lead/MEMORY.md`, `org_read` (twice), `report status=done`. `obs events --kind tool.call` holds 10 events: the 5 by `lead` (run `lead@20261026T044405599852`) equal the log's calls; the other 5 are root's `progress` calls of the poll check (`preflight/obs-events-tool-call.txt`).
- Org-run session (`preflight/org-kiro-session/session.json`): `agentMode` = the log's `--agent`, `modelId` `claude-sonnet-5.5`, `effortLevel` `high`, `workspacePaths[0]` = the log's `# cwd:` (`.../kiro-cwd/hirearchy-g0-preflight-1-ec7753e74d43fc47/lead-8cb33b27`), `createdAt` 04:44:14.045Z inside `run.start` (04:44:05.6Z) and `run.end` (04:44:29.8Z, `ok: true`, `killed: false`); the one `reasoningModelId` is `qdev::claude-sonnet-5.5`.
- `zsh harness/model_check.sh org preflight P`: `RESULT: preflight org: OK`, exit 0. Task outcome (recorded, not the pass condition): done, `lead/work/preflight.txt` holds `G0-PREFLIGHT-OK`; `scheduler.exit` `finished: no open tasks`; `hirearchy --root P/org check`: all checks passed (`preflight/final-progress-check.txt`).

## 10. Injection script: PASS
Script md5 `1c4e7824e448a3a34e24a7b759a59fcd` = `MD5SUMS` (and E7's).
- **Live poll check** (`uv --directory /Volumes/workspace/hirearchy run python harness/inject_root_rework.py --poll-check --org P/org --task 20261026T044144236971-root-8142 --out preflight/poll-check --max-seconds 120`, before the scheduler started, so every reply was "Not waiting: no scheduler is running"). Exit 0, 04:41:53Z-04:43:08Z. It called only `progress(task_id, wait_seconds)`:

  | Poll | Request time (UTC) | Reply | Pause before next |
  |---|---|---|---|
  | 1 | 04:41:53 | 0.0 s | 5.0 s |
  | 2 | 04:41:58 | 0.0 s | 10.0 s |
  | 3 | 04:42:08 | 0.0 s | 20.0 s |
  | 4 | 04:42:28 | 0.0 s | 40.0 s |
  | 5 | 04:43:08 | 0.0 s | 44.9 s (to the window end) |

  Final line: `polling ended (window cap: 120 seconds passed): progress(task_id) polls 5, quick replies 5, paused 119.9s in all` (`preflight/poll-check/poll-check-log.txt`). Pass rule (every poll logged; each next poll at least 5 s later; at most 25 polls; the final line gives the count): met.
- `--dry-run` (exit 0): `title md5 849fe21b104be883af9b3c06367d4445 ok; note len 866 md5 4cdbcb9b682f2f25dcb31c83d3743fec ok`. `--selftest` (exit 0) lists root's tools: `apply_org, blueprint_example, create_org, define_service, delegate, feedback, health, hire, inbox, observe, progress, propose_org, quality, read, reclaim, report, request, retire, send, services, start, status, stop, whoami, write` (`request`, `start`, `progress`, `status`, `stop` included; `quality` is available for the harness's reads). `python3 -B harness/test_poll_loop.py`: 7 passed, 0 failed. The text source is byte-identical to E2's and the script to E7's (`preflight/injection-dryrun-selftest.txt`).
- The full injection (`request`, `start`) was not run: no stream exists.

## 11. Deletion: PASS (`preflight/deletions.txt`)
By exact path with a path-prefix guard, after the evidence was copied and with no process naming any of them: the preflight M0 home (section 7), `/tmp/hirearchy-g0-preflight-1792989703`, `~/Library/Application Support/hirearchy/kiro-home/hirearchy-g0-preflight-1-ec7753e74d43fc47` and `.../kiro-cwd/hirearchy-g0-preflight-1-ec7753e74d43fc47`, the check (a) sandbox `/tmp/hirearchy-g0-detach-1792989925`, and the M1 probe profile `~/.kiro/agents/hirearchy-study-g0-probe-m1.json` (04:48:17Z; the M0 probe profile went with the M0 home). `<state>` (`~/Library/Application Support/hirearchy`) existed before the preflight (E4-E7 `kiro-cwd` leftovers), so it was kept. `~/.kiro/agents` afterwards holds exactly the six pre-existing files; no `hirearchy-study-g0-*` profile remains. The two probe dirs (`/tmp/hirearchy-g0-probe-m1-1792989560`, `/tmp/hirearchy-g0-probe-m0-1792989651`) stay.

## 12. Scheduler check (a), the harness form: PASS (attempt A1, sandbox `/tmp/hirearchy-g0-detach-1792989925`, agent `c1-1792989925`)
Tools: C1's nine tools copied from `docs/research/org-growth/phase-0a4/c1-tools/` into `preflight/c1-tools/` and changed only as E7's item 10 lists, with G0's names (`WT` = the repo in `setup.sh`, `after.sh`, `mkprofile.py`; the copy and `timeline.py` paths; the samples archive `preflight/detach/samples/`; sandbox prefix `/tmp/hirearchy-g0-detach-`); `preflight/c1-tools/CHANGES.txt` has each `diff -u` and the copies' md5s. **Setup 0, the sign-in probe** (`preflight/detach/whoami.txt`): exit 0, first line `Authenticated with API key`; its sandbox was removed. Setup (`preflight/detach/a-setup.txt`): `init`, `hire`, `task`, `validate`, `chat-help` all exit 0. Every kiro-cli call ran with `KIRO_HOME=$SB/kiro-home` and `KIRO_CHAT_LOG_FILE=$SB/logs/A1-turn<k>.log`; nothing under `~/.kiro` was read or written by this check. Chat calls used: 2 of 12. The attempt was valid on the first try.

Each turn's tool call was the chat command followed by `; echo $? > $SB/out/A1-turn<k>.exit; sleep 20`; the sampler (window 25 s) was started before it by a background call. Turn 1 exit 0 (the `disclose_context` call reported the skill not available in the sandbox kiro home, as in E7, and the model went on to `tool_load` and `progress`). Turn 2 (`--resume`; `progress` then `start` with `until_done=false`): start 04:46:35Z, chat return (process gone) 04:47:01.273Z, exit 0. Stdout: `scheduler started (pid 21150; it runs until stop()); log: .../org/.runtime/scheduler.log`.

| Condition (E7 4.14 item 10 (a)) | Fact | Result |
|---|---|---|
| 1. scheduler and run alive 5 s after the return and at the sleep's end, no `scheduler.signal` or `scheduler.exit` by then | `verdict survived`, `valid True`; `scheduler_alive_at_plus_5s True`, `run_alive_at_plus_5s True`; last sample with both alive 04:47:26.323Z (25.0 s after the return, past the sleep's end at about 04:47:21Z); first gone: none. Scheduler pid 21150, `ps` state `Ss`, ppid 1, pgid 21150 (re-parented to launchd). Run `child_pid` 21165. `run.start` 04:46:58.46Z, 2.8 s before the return. No `scheduler.signal`, no `scheduler.exit` | met |
| 2. the run ends by itself: `run.end` `ok: true`, `killed: false` | `run.end` 04:47:36.662Z (`ok: true`, `killed: false`, `exit_code 0`, `duration_ms 38198`), 35 s after the return. The ceo agent's `tool.call` events: `write` and `report`, both `ok` | met |
| 3. the deliberate stop records `scheduler.signal` (`SIGTERM`, `stop`), then `scheduler.exit` `stopped by SIGTERM` | after `run.end` the scheduler was alive (`detach/a-before-stop-ps.txt`: pid 21150, ppid 1). The stop (`HIREARCHY_STATE_DIR=$SB/kiro-state /Volumes/workspace/hirearchy/.venv/bin/python -c '...scheduler_control.stop()' $SB/org`) printed `scheduler stopped (pid 21150)`, exit 0, 04:47:42Z. Events: `scheduler.signal` 04:47:42.306Z `signal: SIGTERM`, `action: stop`, `ppid: 1`, `running: []`; then `scheduler.exit` 04:47:42.782Z `reason: stopped by SIGTERM`, `runs_started: 1`. No process named `$SB` afterwards | met |
| 4. `allowed.py` prints ALLOWED | `ALLOWED` (`preflight/detach/a/allowed.txt`) | met |

Record (`preflight/detach/a/`): `out/`, `logs/`, `profile.json`, `verdict.json`, `allowed.txt`, `events-all.jsonl`, `events-selected.jsonl`, `scheduler.log`, `session-record-paths.txt`, `cleanup.txt`; the sample timelines, summaries and verdicts are in `preflight/detach/samples/A1/`; `detach/a-setup.txt`, `a-before-stop-ps.txt`, `a-stop.txt`. The sandbox was removed after the copy (`a/cleanup.txt`).

## 13. Safety snapshot after: PASS
`zsh harness/safety-snapshot.sh preflight-after > preflight-safety-after.txt` (exit 0, 04:48:28Z) and `preflight/ambient-end.txt`. `diff safety-before.txt preflight-safety-after.txt` (`preflight-safety-diff.txt`) shows only expected differences:
1. the label and date lines;
2. the mtime of the directory `~/.kiro/memories` (04:37 to 04:39, from the M1 probe's kiro session) and of the directory `~/.kiro/agents` (probe profile created and deleted); the file lists and md5s are unchanged;
3. the `/tmp/hirearchy-g0-*` listing, which now names the two probe dirs left in place.

**The owner's `~/.kiro`, md5 before and after: unchanged.** All `~/.kiro/settings/*` md5s (including `cli.json` `8b4f0599...` and `cli.json.lock` `9070b152...`), the global SKILL.md (`a3e46347...`), `memories.db` (`d7581238189dcb31ef2f6c70a1fb525a`, 114 688 bytes), the file list and md5s of `~/.kiro/agents/*`, `/Users/aminalizadeh/organization` (file count, newest mtime, stat digest), repo `git status`, HEAD, the empty freeze diff, the `protocol.md` md5 and `/Volumes/workspace/orgs`. The two ambient snapshots differ only in their label and date lines, the mtime of the `~/.kiro/memories` directory and the memories listing md5 that follows from it; the skills listings and skills-through-links listings (and their md5s) are the same at start and end. The preflight created and deleted one profile in `~/.kiro/agents` (`hirearchy-study-g0-probe-m1`, md5 `33670628ac52d1a2d194a78e497db267`), one in the M0 home (`hirearchy-study-g0-probe-m0`, md5 `8f79cc7cbbbf1ca39155427470603173`), and no other.

## Harness facts noticed (recorded; nothing changed, nothing blocks a stream)
- `model_check.sh` for `preflight` prints `preflight` (not E7's `spreflight`), and checks the org run log's `# cmd:` line only; the org-run session's `modelId` and `effortLevel` were read by hand (section 9).
- `ambient_context.py` lists a spurious memory title `TITLE` (20 titles listed, 19 memories shown). Cosmetic, as in E5-E7.
- No `.runtime/scheduler.log` existed in the item-9 org (as in E5-E7); the check (a) org had one.
- The Global memory count the M1 probe shows has risen over the studies (E6 11, E7 15, G0 19); the user's `~/.kiro/skills` listing and the 20 skill names are the same as E7's. It is the M1 arm's recorded condition, not a validity condition.
- `hirearchy status` was run once on the throwaway item-9 org (to see the task) and wrote a `cli.command` event there; nothing else read the org during the check.
- The assistant profile template and `run_turn.sh`, `setup_stream.sh`, `after_turn.sh`, `skill_check.sh` and `quality_snapshot.sh` were not exercised (they need a stream); the probes used the template JSON with the probe names, and `prepare_m0_home.sh` ran for real (once, after a dry run). `ambient_snapshot.sh` ran twice (start and end) without error.
- Other kiro-cli sessions of the user and the workflow were running during the preflight; none names a G0 sandbox, profile or org.

## Files and state left behind
- Evidence: `preflight/`, `probe/m1/`, `probe/m0/`, `deterministic/at-3c841bb9/`, `safety-before.txt`, `preflight-safety-{after,diff}.txt`, this file.
- Still present: the two probe dirs `/tmp/hirearchy-g0-probe-m1-1792989560` and `/tmp/hirearchy-g0-probe-m0-1792989651`. Removed: the item-9 sandbox, its kiro home and scratch cwd, the check (a) sandbox, the preflight M0 home, the M1 probe profile. No `hirearchy-study-g0-*` profile is in `~/.kiro/agents`; no process names a G0 sandbox.
- No E7, E5 or E4 file was changed. Nothing was staged or committed. The frozen protocol and harness are unchanged (md5s re-checked at the end).

Result: PASS
