# E6 preflight (protocol 4.14; workflow step 2 of 9, `wf_25265920a47bd720`)

Run 2026-10-24, 15:17-15:28 UTC (local WEST = UTC + 1 h), by the preflight step. Facts only. No stream, assistant session or stream sandbox was started. No product file, harness file or protocol file was changed. Nothing was staged, committed or pushed.

Raw files are under `evidence/preflight/` unless a path is given. Paths below are relative to `/Volumes/workspace/hirearchy/studies/E6-org-growth-0a3-recheck/evidence/`.

**Result: PASS**

| # | Check (protocol 4.14 item) | Result | Evidence |
|---|---|---|---|
| 1 | md5 gates (item 1) | PASS | `preflight/gates.txt` |
| 2 | Freeze (item 2) | PASS | `preflight/freeze-check.txt` |
| 3 | Safety snapshot before (item 3) | PASS | `safety-before.txt` (= `preflight-safety-before.txt`) |
| 4 | kiro-cli version and model list (item 4) | PASS | `preflight/kiro-cli.txt`, `preflight/model-checks.txt` |
| 5 | Deterministic part at `18c4ffb` (item 5) | PASS: 78 passed; 15 of 15 replays PASSED; kit 11 passed | `deterministic/SUMMARY.md`, `deterministic/at-18c4ffb/` |
| 6 | Ambient probe (item 6) | PASS | `probe/` |
| 7 | One real org-agent run through the real scheduler on claude-sonnet-5.5 / effort high (item 7) | PASS | `preflight/lead-run.log`, `preflight/org-setup.txt`, `preflight/scheduler-run.txt`, `preflight/obs-events-tool-call.txt`, `preflight/org-kiro-session/`, `preflight/model-checks.txt` |
| 8 | Injection script: poll check, dry-run, selftest (item 8) | PASS | `preflight/poll-check/`, `preflight/injection-dryrun-selftest.txt`, `preflight/test_poll_loop.txt`, `preflight/injection-text-identity.txt` |
| 9 | Deletion (item 9) | PASS | `preflight/deletions.txt`, `probe/probe-profile-deletion.txt` |
| 10 | Scheduler outlives the chat call that started it (item 10) | PASS | `preflight/detach/` |
| 11 | Safety snapshot after, and diff | PASS | `preflight-safety-after.txt`, `preflight-safety-diff.txt`, `preflight-profiles.txt` |

## 1. md5 gates: PASS
- `md5 -q protocol.md` = `31410741088523af23875aef34167bac` = `cat protocol.md5` = the freeze file's value. No `protocol-amendment-*` file exists.
- `harness/MD5SUMS`: every line checked (16), no MISMATCH. `md5 -q harness/MD5SUMS` = `d8ad3b83897114b5118a78852060d68b` (as in `freeze.txt`).
- Skill: `~/.kiro/skills/hirearchy/SKILL.md` (read-only md5), repo `skills/hirearchy/SKILL.md` and `git show 18c4ffb:skills/hirearchy/SKILL.md` are all `b2469838032374807e3608631c9fb1d2`.
- Injection script `harness/inject_root_rework.py` = `1c4e7824e448a3a34e24a7b759a59fcd` (= E5's; `cmp` against E5's copy is identical).
- Notes `903e3bbf...`, `3893bd63...`, `9976a765...` and `answer-key.md` `2fb69bbef857c2bd4862cd5dd8be9da8` match protocol 4.6.
- Protocol `md5` checked again at the end of the step: unchanged (`31410741...`).

## 2. Freeze: PASS
`git rev-parse HEAD` = `18c4ffb7d2dc0ea2a04b07c478397c9d1c89ad29`, branch `main`. `git diff --stat 18c4ffb HEAD -- src skills pyproject.toml uv.lock`: empty (before the checks, after the deterministic runs, and in both safety snapshots). `git status --porcelain`: `?? docs/research/` and `?? studies/E6-org-growth-0a3-recheck/` only.

## 3. Safety snapshot before: PASS
`zsh harness/safety-snapshot.sh preflight-before > safety-before.txt` (exit 0, 16:17:33 local / 15:17:33Z). It ran after the gates (read-only) and after the empty evidence dirs `preflight/`, `deterministic/at-18c4ffb/` and `probe/` were made, and before any sandbox, profile, session or process of the preflight existed. Global SKILL.md `b2469838...`; `memories.db` unchanged across the step.

## 4. kiro-cli: PASS
- `kiro-cli --version` = `kiro-cli 2.33.0` (the version the protocol records).
- `harness/model_check.sh listed preflight`: `RESULT: spreflight listed: OK`, exit 0; `listed: claude-sonnet-5.5: yes (claude-sonnet-5.5    1.30x credits      Claude Sonnet 5.5 model with 1M context window)`. No substitution.

## 5. Deterministic part at `18c4ffb`: PASS (details in `deterministic/SUMMARY.md`)
- Command 1 (`test_org_growth_0a.py`, `test_org_growth_0a2.py`, `test_no_bypass_0a2.py`): **78 passed**, exit 0.
- Command 2 (`git grep -l -E "e4_replay|e5_s" tests`): `tests/e2e/test_org_growth_0a2.py`, `tests/e2e/test_org_growth_0a3.py`, `tests/meta/test_e4_replay_kit.py`.
- Command 3 (`-v` on `test_org_growth_0a2.py`, `test_org_growth_0a3.py`, `test_scheduler_detach.py`): **15 passed**, 0 skipped/xfail/failed/error, exit 0. Named tests all PASSED: E5's three D-E4-7 replays; the five 0a.3 replays (`test_e5_s1_t6_*`, both parameters of `test_e5_s2_t5_*`, both `test_e5_s3_*`); `test_the_scheduler_and_its_run_finish_after_its_starter_and_every_descendant_are_killed`.
- Command 4 (report only, `tests/meta/test_e4_replay_kit.py`): **11 passed**, exit 0.
- Linux citation: `git diff --stat e417c95 18c4ffb -- <the 4.9 paths>` is empty, so 0a.3's Linux record stands for `18c4ffb`. Report only.
- No full suite was run.

## 6. Ambient probe (4.5): PASS
Probe dir `/tmp/hirearchy-e6-probe-1792855143` (left in place, per protocol). Workspace skill copy `b2469838...`, `.kiro/settings/cli.json` `05d30ccbfd35530747c8a542eb67985c`.
- Profile `~/.kiro/agents/hirearchy-study-e6-probe.json`, md5 `de96983ff61cf6f0838cc1cecb1daa11`, created 15:19:19Z, deleted 15:19:54Z after a byte comparison with `probe/hirearchy-study-e6-probe.json`. `~/.kiro/agents` afterwards holds exactly the six pre-existing files.
- Call (cwd = probe dir): `kiro-cli chat --v3 --no-interactive --trust-all-tools --effort high --agent hirearchy-study-e6-probe "List the names of the skills ..."`, exit 0. Reply listed: autoresearch, commit-work, hirearchy, reverse-engineer-anything, skill-generation, test-driven-development, workflow-suggest.
- Session (`probe/probe-session.json`): `modelId` `claude-sonnet-5.5`, `effortLevel` `high`, `agentMode` `hirearchy-study-e6-probe`. `ambient_context.py`: `<steering-files>` block present: False; "Workflow Orchestration" text present: False; `<memories>` block present: True (11 global memories; covariate); `hirearchy` listed. `~/.kiro/settings/cli.json` and `cli.json.lock` md5s unchanged (`probe/global-cli-md5-before.txt`, `-after.txt`).

## 7. One real org-agent run through the real scheduler: PASS
Sandbox `P` = `/tmp/hirearchy-e6-preflight-1792855201` (org at `P/org`); deleted at the end (item 9).
Commands (`preflight/org-setup.txt`, `preflight/scheduler-run.txt`), all with the protocol's CLI forms; no form needed adapting:
```
hirearchy init P/org --mission "E6 harness preflight (throwaway)" --model claude-sonnet-5.5     -> exit 0; ORG.md: default_model: claude-sonnet-5.5, effort: high
hirearchy --root P/org hire root lead --role Lead --charter "You are the lead of a throwaway preflight org. ..." --tools read,write --model claude-sonnet-5.5   -> hired lead
hirearchy --root P/org task lead --title "Preflight note" --goal "Use the hirearchy org_write tool to write the file lead/work/preflight.txt ... E6-PREFLIGHT-OK. Then call the hirearchy report tool with status done." --acceptance "..." --budget 2
  -> task 20261024T152002144550-root-4b92 -> lead (budget 2)
(poll check, item 8, before the scheduler started)
perl -e 'alarm shift; exec @ARGV' 900 hirearchy --root P/org run --until-done --max-runs 2
  -> lead: started run (1 message(s)) / lead: run finished in 89s / scheduler exiting: finished: no open tasks   (exit 0, 15:23:17Z-15:24:45Z)
```
Run log `preflight/lead-run.log`, `# cmd:` line:
```
# cmd: /Volumes/workspace/hirearchy/.venv/bin/python3 -I -S /Volumes/workspace/hirearchy/src/hirearchy/kiro/_launch.py --start-deadline 60 -- kiro-cli chat --no-interactive --agent hirearchy-hirearchy-e6-preflight-1-e64263-read-write-xa8d10ce9 --model claude-sonnet-5.5 --effort high --v3 --require-mcp-startup --output-format stream-json <prompt on stdin>
```
- One `--model claude-sonnet-5.5`, one `--effort high`. `# kiro: run started (engine v3)`, `[run finished] success (end_turn)`, `# exit 0 after 89s`.
- Hirearchy tool calls in the log (RL3): 5 distinct calls, each with a `[tool ok]` line: `org_write lead/work/preflight.txt`, `org_read`, `org_write lead/MEMORY.md`, `org_read`, `report status=done`. (A `Tool Load` line precedes them.)
- `hirearchy --root P/org obs events --kind tool.call`: 10 events. The 5 by `lead` (run `lead@20261024T152317077253`, 15:23:48-15:24:38Z) equal the 5 log calls and are all `ok`; the other 5 are root's `progress` events of the poll check. `preflight/obs-events-tool-call.txt`, `preflight/org-events-all.jsonl`.
- Org-run session (`preflight/org-kiro-session/session.json`): `agentMode` `hirearchy-hirearchy-e6-preflight-1-e64263-read-write-xa8d10ce9` (= the log's `--agent`), `modelId` `claude-sonnet-5.5`, `effortLevel` `high`, `workspacePaths[0]` = the log's `# cwd:` (`~/Library/Application Support/hirearchy/kiro-cwd/hirearchy-e6-preflight-1-e64263f3ed456421/lead-8cb33b27`), `createdAt` 15:23:30.66Z inside `run.start` (15:23:17.08Z) and `run.end` (15:24:45.80Z, `ok: true`).
- `zsh harness/model_check.sh org preflight P`: `RESULT: spreflight org: OK`, exit 0 (`preflight/model-checks.txt`).
- Task outcome (recorded, not the pass condition): done; `lead/work/preflight.txt` held `E6-PREFLIGHT-OK`; `scheduler.exit` = `finished: no open tasks`; `hirearchy --root P/org check`: all checks passed (`preflight/final-progress-check.txt`). The org agent's scheduler profile was in the per-org kiro home (copy: `preflight/hirearchy-hirearchy-e6-preflight-1-e64263-read-write-xa8d10ce9.json`); no assistant profile was needed.

## 8. Injection script: PASS
Script md5 `1c4e7824e448a3a34e24a7b759a59fcd` = `MD5SUMS`.
- **Live poll check** (`uv --directory /Volumes/workspace/hirearchy run python harness/inject_root_rework.py --poll-check --org P/org --task 20261024T152002144550-root-4b92 --out evidence/preflight/poll-check --max-seconds 120`, run before the scheduler started, so every reply was "Not waiting: no scheduler is running"). Exit 0, 15:20:39Z-15:22:40Z. It called only `progress(task_id, wait_seconds)`.

  | Poll | Request time (UTC) | Reply | Pause before next |
  |---|---|---|---|
  | 1 | 15:20:40 | 0.0 s | 5.0 s |
  | 2 | 15:20:45 | 0.0 s | 10.0 s |
  | 3 | 15:20:55 | 0.0 s | 20.0 s |
  | 4 | 15:21:15 | 0.0 s | 40.0 s |
  | 5 | 15:21:55 | 0.0 s | 44.9 s (to the window end) |

  Final line: `polling ended (window cap: 120 seconds passed): progress(task_id) polls 5, quick replies 5, paused 119.9s in all`. Pass rule: every poll logged; each next poll at least 5 s later; 5 polls (limit 25); the final line gives the count.
- `--dry-run --org P/org` (exit 0): `title md5 849fe21b104be883af9b3c06367d4445 ok; note len 866 md5 4cdbcb9b682f2f25dcb31c83d3743fec ok`.
- `--selftest --org P/org` (exit 0) listed root's tools: `apply_org, blueprint_example, create_org, define_service, delegate, feedback, health, hire, inbox, observe, progress, propose_org, read, reclaim, report, request, retire, send, services, start, status, stop, whoami, write` (includes `request`, `start`, `progress`, `status`, `stop`).
- Offline `python3 -B harness/test_poll_loop.py`: 7 passed, 0 failed.
- Text identity: the script is byte-identical to E5's (`cmp`), which E5 proved text-identical to E4's and E2's; `preflight/injection-text-identity.txt`.
- The full injection (`request`, `start`) was not run: no stream exists. Only `progress` was called against the preflight org.

## 9. Deletion: PASS
`preflight/deletions.txt`, each by exact path with a path-prefix guard, after the evidence was copied and with no process referencing the sandbox: `~/Library/Application Support/hirearchy/kiro-home/hirearchy-e6-preflight-1-e64263f3ed456421`, `.../kiro-cwd/hirearchy-e6-preflight-1-e64263f3ed456421`, `/tmp/hirearchy-e6-preflight-1792855201`; the probe profile earlier (`probe/probe-profile-deletion.txt`). `<state>` existed before the preflight (E4 and E5 `kiro-cwd` leftovers), so it was kept. The probe dir `/tmp/hirearchy-e6-probe-1792855143` is left in place.

## 10. Scheduler survival (the E6 brief's step 2 addition; 0a.3 design 6.1 after the fix, DR-0a3-3 and DR-0a3-4): PASS
Sandbox `SB` = `/tmp/hirearchy-e6-detach-1792855531`, outside every stream sandbox and apart from the preflight org of item 7. Every real kiro-cli call ran with `KIRO_HOME=$SB/kiro-home`; the MCP server had `HOME=$SB/home`, `HIREARCHY_STATE_DIR=$SB/kiro-state`, and a stub `kiro-cli` first on its `PATH` only (`preflight/detach/stub-kiro-cli.sh`: `chat` prints `runStarted`, sleeps 60 s, prints `runFinished`). Nothing under `~/.kiro` and nothing of the user's organization was read or written by this check. Raw record: `preflight/detach/`.

| Step | Fact | File |
|---|---|---|
| Sign-in (stop condition) | `KIRO_HOME=$SB/kiro-home kiro-cli whoami` exit 0 ("Authenticated with API key"; the email line is redacted in the copy) | `whoami.txt` |
| Org | `hirearchy init`, `hire root ceo`, `task ceo --budget 2` (task `20261024T152545475247-root-8850`) with `HIREARCHY_STATE_DIR=$SB/kiro-state`, `HIR` = `/Volumes/workspace/hirearchy/.venv/bin/hirearchy` (exit 0 each) | `org-setup.txt` |
| Profile (stop condition) | `$SB/kiro-home/agents/e6-detach-1792855531.json`, V3 shape (`tools: ["@hirearchy"]`, one rule `mcp` / `hirearchy/start` / `allow`, `includeMcpJson` and `includePowers` false, no resources, no hooks, DR-0a3-4 prompt); `KIRO_HOME=$SB/kiro-home kiro-cli agent validate --path ...` exit 0 | `profile.json`, `profile-validate.txt` |
| The call | cwd `$SB`: `KIRO_HOME=$SB/kiro-home kiro-cli chat --v3 --no-interactive --require-mcp-startup --model claude-sonnet-5.5 --effort high --agent e6-detach-1792855531 "<DR-0a3-4 prompt>"`; 15:26:08Z to 15:26:28Z, exit 0; stdout `scheduler started (pid 86761; it exits by itself when the work is done); log: .../org/.runtime/scheduler.log` | `prompt.txt`, `call.stdout.txt`, `at-return.txt` |
| Stop condition: kiro home | `find $SB/kiro-home -type f -newer $SB/.marker` listed the session record `.../kiro-home/sessions/4d20a325e69231d1/sess_904a6f25-6314-4111-888d-1ca5ca03429b/session.json` (`agentMode` `e6-detach-1792855531`, `modelId` `claude-sonnet-5.5`, `effortLevel` `high`); kiro-cli honoured `KIRO_HOME` | `five-seconds-later.txt`, `session-summary.txt`, `session-record-path.txt` |
| Stop condition: the call | `scheduler.start` of this call at 15:26:24.12Z; the MCP server's `tool.call start ok=true` at 15:26:24.14Z | `events-all.jsonl` |
| At the return (15:26:28Z) | `scheduler.pid` = **86761**: `ps` `86761 ppid 1 pgid 86761 Ss` (re-parented to launchd, own session). Run `child_pid` = **86774** (`pgid` 86774): `86774 ppid 86761 Ss`, command `.../kiro/_launch.py --start-deadline ...` | `at-return.txt` |
| 5 s later (15:26:45Z, 17 s after the return) | both still alive: `86761 1 86761 Ss`, `86774 86761 86774 Ss`. The MCP server (pid **86758**, from `mcp-86758-1792855584143.jsonl`) is gone. No `scheduler.exit` and no `run.end` event | `five-seconds-later.txt` |
| Deliberate stop (15:26:56Z) | `HIREARCHY_STATE_DIR=$SB/kiro-state .../.venv/bin/python -c 'import sys; from hirearchy.app import Org; print(Org(sys.argv[1]).runtime.scheduler_control.stop())' "$SB/org"` printed `scheduler stopped (pid 86761)`, exit 0. Events: `run.end ok=false killed=true` at 15:26:58.356Z and `scheduler.exit reason="stopped by SIGTERM"` at 15:26:58.357Z. Scheduler and run gone afterwards | `stop.txt`, `scheduler.exit` |
| Clean-up | no process names `$SB`; the learned pids (86761, 86774, 86758) all gone; `$SB` removed 15:27:10Z (path-prefix guard) | `cleanup.txt` |

Pass condition (scheduler and run alive at the return and 5 s later; the stop's two events recorded): met. Before 0a.3's fix both were gone at the return (E5 s3; 0a.3's `repro-detach.md` C0). Not kept: the session record itself was inside `$SB` and was removed with it; its path and fields are recorded.

## 11. Safety snapshot after: PASS
`zsh harness/safety-snapshot.sh preflight-after > preflight-safety-after.txt` (exit 0, 16:27:16 local). `diff preflight-safety-before.txt preflight-safety-after.txt` (`preflight-safety-diff.txt`) shows three differences, all expected:
1. label and date lines;
2. mtime of the directory `~/.kiro/memories` (16:16 to 16:19; kiro sessions of the probe can touch the directory). `memories.db` md5 is unchanged; recorded, not attributed;
3. mtime of the directory `~/.kiro/agents` (05:38 to 16:19), from the probe profile's creation and deletion (item 6).

Unchanged: all `~/.kiro/settings/*` md5s, the global SKILL.md md5, the file list and md5s of `~/.kiro/agents/*`, `/Users/aminalizadeh/organization` (file count, newest mtime, stat digest), repo `git status`, HEAD, freeze diff, `protocol.md` md5, `/Volumes/workspace/orgs`. `preflight-profiles.txt` lists the profile the step created and deleted.

## Harness facts noticed (recorded; nothing changed, nothing blocks a stream)
- `model_check.sh` labels its output `spreflight` (it prefixes `s` to its `<N>` argument). Cosmetic, as in E5; the md5-frozen script is untouched.
- `ambient_context.py` lists a spurious memory title `TITLE` (12 titles listed, 11 memories shown). Cosmetic, as in E5.
- The org run produced no `.runtime/scheduler.log` file in the preflight org; `scheduler.exit` and the console output carry the scheduler's lines (as in E5).
- The preflight org's run took 89 s (E5's took 24 s); no throttle line, exit 0.
- The assistant profile template and `run_turn.sh` were not exercised (no assistant stream session was started); the probe used the template JSON with the probe name.

## Files and state left behind
- Evidence: `evidence/preflight/`, `evidence/probe/`, `evidence/deterministic/`, `evidence/safety-before.txt`, `evidence/preflight-safety-{before,after,diff}.txt`, `evidence/preflight-profiles.txt`, this file.
- Still present: `/tmp/hirearchy-e6-probe-1792855143` (probe dir). Removed: the preflight sandbox, its kiro home and scratch cwd, the detach sandbox. No `hirearchy-study-e6-*` profile is in `~/.kiro/agents`. No E4 or E5 file was changed. No `/tmp/hirearchy-e6-*` process is running.

Result: PASS
