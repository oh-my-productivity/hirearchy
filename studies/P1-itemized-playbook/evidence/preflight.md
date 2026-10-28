# P1 preflight (protocol section 9; step 3 of workflow `wf_9e81d83f470f71a8`)

Run 2026-10-27, 17:23-19:22 UTC (local WET = UTC), by the preflight step (resumed after the manager's amendment H-A1). Facts only. No stream, stream sandbox or stream profile was started.
No product file or `protocol.md` was changed; the harness changed only by amendment H-A1 (`probe.sh`, `CHANGES.md`, `MD5SUMS`; section 10.2). Nothing was staged, committed or pushed. `/Users/aminalizadeh/organization`, `~/.kiro/skills/`
(read by `md5 -q` only), `~/.kiro/memories/` (md5 and metadata only) and the user's files in `~/.kiro/agents` were not touched. No credential was
read, copied, printed or recorded (the sign-in check keeps only the line `Authenticated with API key`). `KIRO_HOME` was unset throughout; no
dedicated kiro home was built.

Paths below are relative to `/Volumes/workspace/hirearchy/studies/P1-itemized-playbook/evidence/` (`EV`).

**Result: PASS**, after one amendment. Attempt 1 of the probe ended `PROBE: STOP` because the frozen `probe.sh` omitted `--deliverable` from its first definition (a harness defect, not an arm
difference); the manager approved amendment H-A1 (`manager-decision-probe-define.md`, `protocol-amendment-1.md`); attempt 2, on the amended `probe.sh`, ended `PROBE: PASS`. Both attempts are recorded in
section 10. Everything else passed on the first run.

| # | Check | Result | Evidence |
|---|---|---|---|
| 1 | md5 gates (protocol, `MD5SUMS`, pins) | PASS | `preflight/gates.txt` |
| 2 | Freeze (HEAD = 8bf7c69b, empty product diff) | PASS | `preflight/gates.txt`, `deterministic/at-8bf7c69b/freeze-{before,after}.txt`, `preflight-safety-after.txt` |
| 3 | Safety snapshot before / after, owner's `~/.kiro` md5s, `memories.db` | PASS (unchanged) | `safety-before.txt`, `preflight-safety-after.txt`, `preflight-safety-diff.txt` |
| 4 | kiro-cli 2.33.0, claude-sonnet-5.5 listed | PASS | `preflight/kiro-cli.txt`, `preflight/model-checks.txt` |
| 5 | Skill md5 `b1023863...` in both arms' setups | PASS | `preflight/setup-dry-run.txt` (F1, I1), `probe/*` workspace copies (section 4) |
| 6 | Deterministic part at 8bf7c69b | PASS: 32 passed; 116 passed | `deterministic/at-8bf7c69b/` |
| 7 | Ambient probe (owner's kiro home, `KIRO_HOME` unset) | PASS | `preflight/ambient-probe/` |
| 8 | One real org-agent run, claude-sonnet-5.5, `--effort high` | PASS | `preflight/lead-run.log`, `preflight/org-*` |
| 9 | Injection: dry run, self-test, offline test, live poll check | PASS | `preflight/injection-dryrun-selftest.txt`, `preflight/poll-check/` |
| 10 | Scheduler check (a), harness form, M1 form | PASS (attempt A2; A1 invalid, infrastructure) | `preflight/detach/` |
| 11 | F-G0-7 probe (`probe.sh`), both arms, 2 reps, 2 turns | attempt 1: STOP (harness defect); **attempt 2: PASS** | `probe-attempt-1/`, `probe/`, `preflight/probe-run*.txt` |
| 11a | Amendment H-A1: whole-harness CLI check, re-freeze, self-check | PASS: 17 of 17 parts, 206 tests | `harness/CHANGES.md`, `protocol-amendment-1.md`, `freeze.txt`, `harness-selfcheck/h-a1-run*` |
| 12 | Deletions | PASS (profiles and org sandboxes of items 7, 8, 10; probe profiles; attempt 1's four sandboxes) | `preflight/deletions.txt`, `preflight/ambient-probe/probe-profile-deletion.txt`, `preflight/detach/profile-deletions.txt`, `probe/profiles-deletions.txt` |

## 1. Gates and freeze: PASS (`preflight/gates.txt`)
- `md5 -q protocol.md` = `70237b0f3a829795a89d81c8eba7a7d6` = `protocol.md5` = `freeze.txt`. No `protocol-amendment-*`. Unchanged at the end.
- `harness/MD5SUMS` (64 lines): md5 `524b857e9b75f6f104f22d11860145e2` at the start (no MISMATCH); after amendment H-A1 `d21508978d71e6d805f1760b25acb1b6` (probe.sh and CHANGES.md updated; no MISMATCH at the end). `preflight/gates.txt` is the pre-amendment gate run.
- All pins of protocol 2.1 equal (notes, both answer keys, E7/G0 protocol copies, the injection script `1c4e7824...`, its text source, `workspace-cli.json`).
- `git rev-parse HEAD` = `8bf7c69bb933bf2e1ecda5dc4ddbefde41eba565`, branch `main`; `git diff --stat 8bf7c69b HEAD -- src skills pyproject.toml uv.lock` empty
  at the start, after the deterministic run and at the end. `git status --porcelain`: ` M docs/design/org-growth-phase-1.md` (the 21.6 line, from step 1a),
  `?? docs/research/`, `?? studies/P1-itemized-playbook/`. The installed `hirearchy` tool resolves to `/Volumes/workspace/hirearchy/src/hirearchy/__init__.py`.
- Skill: repo, `git show 8bf7c69b:skills/hirearchy/SKILL.md` and `~/.kiro/skills/hirearchy/SKILL.md` (md5 only) all `b10238639f48ab351fa44a06aed03ffb`, 125 lines.

## 2. Safety snapshots and `memories.db`: PASS
- `safety-before.txt` (17:23:27Z, before anything was created) and `preflight-safety-after.txt` (19:21:40Z, after attempt 2; the attempt-1 snapshot and diff, 19:06:37Z, are kept as `preflight-safety-{after,diff}-attempt-1.txt`). `preflight-safety-diff.txt` shows only: the label and
  date lines, the mtimes of the directories `~/.kiro/memories` and `~/.kiro/agents`, and the `/tmp/hirearchy-p1-*` listing (the ambient probe dir and the four attempt-2 probe
  sandboxes, left in place for the teardown). All `~/.kiro/settings/*` md5s, the global SKILL.md, the md5s of the files in `~/.kiro/agents`, `/Users/aminalizadeh/organization`
  (file count, newest mtime, tree digest) and `/Volumes/workspace/orgs` are identical.
- **`memories.db` md5, before: `f0aaf02a8a216c3a291a253d2c52d461`; after: `f0aaf02a8a216c3a291a253d2c52d461`** (126 976 bytes, mtime Oct 27 07:41, unchanged;
  also unchanged after the ambient probe, the org run, the scheduler check and both probe attempts: `preflight/memories-md5-start.txt`, `preflight/memories-md5-end.txt`).
  The ambient snapshots (start 17:23Z, end 19:21Z) differ only in the `~/.kiro/memories` directory mtime (17:21:02Z to 17:30:53Z) and the listing md5 that follows from it.
- `~/.kiro/agents` afterwards holds exactly the seven pre-existing entries; no `hirearchy-study-p1-*` profile remains.

## 3. kiro-cli: PASS
`kiro-cli 2.33.0`. `harness/model_check.sh listed preflight`: `listed: claude-sonnet-5.5: yes`, `RESULT: preflight listed: OK` (`preflight/model-checks.txt`).

## 4. Skill md5 in both arms' setups: PASS
`zsh harness/setup_stream.sh F1 --dry-run` and `... I1 --dry-run` (`preflight/setup-dry-run.txt`): every gate OK (protocol md5, 64 MD5SUMS lines, HEAD, empty freeze
diff, repo SKILL.md `b1023863...`, global SKILL.md equal, `KIRO_HOME` unset); both would copy the repo SKILL.md (md5 `b10238639f48ab351fa44a06aed03ffb`) and
`workspace-cli.json` (`05d30ccb...`); the memories gate saw no previous stream. The four probe sandboxes (arms F and I; attempt 1's checked from `probe-attempt-1/*/sandbox-copy/` before their deletion, attempt 2's in place) hold SKILL.md `b10238639f48ab351fa44a06aed03ffb`
and `.kiro/settings/cli.json` `05d30ccbfd35530747c8a542eb67985c` each.

## 5. Deterministic part, scoped at 8bf7c69b: PASS (`deterministic/at-8bf7c69b/`)
Freeze diff empty before and after. Commands, from `/Volumes/workspace/hirearchy`, exit 0 each, stderr empty, output verbatim in the files:
```
UV_LINK_MODE=copy uv run pytest -q tests/e2e/test_org_growth_1.py tests/e2e/test_org_growth_0b1.py
  -> 32 passed in 6.45s              (pytest-output-1-and-0b1.txt)
UV_LINK_MODE=copy uv run pytest -q tests/e2e/test_org_growth_0b_replays.py tests/e2e/test_org_growth_0b_costs.py
  -> 116 passed in 2.70s             (pytest-output-0b-replays-costs.txt)
```

## 6. Ambient probe (owner's kiro home): PASS (`preflight/ambient-probe/`)
Probe dir `/tmp/hirearchy-p1-ambient-1793121877` (left in place), workspace SKILL.md `b10238639f...`, `cli.json` `05d30ccb...`. Profile `hirearchy-study-p1-ambient-probe`
(from the harness template; md5 `8b7e4dcb57d75a0cf33acdccf352a342`), created 17:24:37Z, deleted 17:25:38Z after a byte comparison. Call (cwd = probe dir):
`env -u KIRO_HOME kiro-cli chat --v3 --no-interactive --trust-all-tools --effort high --agent hirearchy-study-p1-ambient-probe "List the names of the skills you can activate, one per line. ..."; sleep 20`,
exit 0; the reply lists 23 skill names, `hirearchy` among them. Session: `modelId` claude-sonnet-5.5, `effortLevel` high. `ambient_context.py`: `<steering-files>` block
False; "Workflow Orchestration" text False; `<memories>` block True (24 global memories; G0 saw 19; the arms' shared covariate). Global `cli.json` and `cli.json.lock`
md5s unchanged. Credits 0.2920.

## 7. One real org-agent run through the real scheduler: PASS
Sandbox `/tmp/hirearchy-p1-preflight-1793121965` (deleted). `hirearchy init ... --model claude-sonnet-5.5` (ORG.md: `default_model: claude-sonnet-5.5`, `effort: high`), `hire root lead`,
`task lead ... --budget 2` (all as G0's commands, no CLI form needed adapting: `preflight/org-setup.txt`); `perl -e 'alarm shift; exec @ARGV' 900 hirearchy --root P/org run --until-done --max-runs 2`
-> `lead: started run`, `lead: run finished in 30s`, `scheduler exiting: finished: no open tasks`, exit 0. Run log `# cmd:` has one `--model claude-sonnet-5.5`, one `--effort high`, `--v3`;
`# kiro: run started (engine v3)`, `[run finished] success (end_turn)`, `# exit 0 after 30s`. Lead's tool calls (all `[tool ok]`): `org_write`, `org_read` x2, `org_write` (MEMORY.md),
`report status=done`; `lead/work/preflight.txt` holds `P1-PREFLIGHT-OK`. `model_check.sh org preflight`: `RESULT: preflight org: OK`. Org-run session: `modelId` claude-sonnet-5.5,
`effortLevel` high, `reasoningModelId` `qdev::claude-sonnet-5.5`. `run.start` 17:28:21Z, `run.end` 17:28:52Z (`ok: true`, `killed: false`). `hirearchy check`: all checks passed.
Credits 0.6162; org runs 1. Files: `preflight/lead-run.log`, `org-events-all.jsonl`, `org-kiro-session/`, `org-run-session-facts.txt`, `obs-events-tool-call.txt`.

## 8. Injection script: PASS
`--dry-run`: `title md5 849fe21b... ok; note len 866 md5 4cdbcb9b... ok`. `--selftest`: root's tools include `request`, `start`, `progress`, `status`, `stop`, `quality`, `services`
(26 tools, new `acknowledge_playbook`). `python3 -B harness/test_poll_loop.py`: 7 passed, 0 failed. **Live poll check** (before the scheduler started; `preflight/poll-check/poll-check-log.txt`): exit 0,
5 polls at 17:26:17, :22, :32, :52, 17:27:32Z, each reply 0.0 s ("Not waiting: no scheduler is running"), pauses 5, 10, 20, 40, 44.9 s; final line
`polling ended (window cap: 120 seconds passed): progress(task_id) polls 5, quick replies 5, paused 119.9s in all`. Pass rule met (every poll logged, each next poll at least 5 s
later, at most 25 polls, final line gives the count). The full injection (`request`, `start`) was not run.

## 9. Scheduler check (a), harness form, M1 form: PASS (attempt A2; `preflight/detach/`)
**M1 form.** G0's check used C1's tools with a sandbox kiro home (`KIRO_HOME=$SB/kiro-home`). The brief forbids a dedicated kiro home, so the copies in `preflight/c1-tools/`
(changes and `diff -u` in `c1-tools/CHANGES.txt`; `allowed.py`, `logfilter.py`, `summary.py`, `timeline.py`, `verdict.py` byte-identical to C1's) differ as follows: WT = the merged repo; sandbox prefix
`/tmp/hirearchy-p1-detach-`; the profile is the study's own `~/.kiro/agents/hirearchy-study-p1-detach-<epoch>.json` (created and deleted with a record), with a copy in `SB/profile/`
(the sampler reads its env key names there); every chat call is `env -u KIRO_HOME kiro-cli chat ...` with cwd `$SB`, `KIRO_CHAT_LOG_FILE=$SB/logs/<ID>-turn<k>.log`; `$SB` holds the streams' workspace
bytes (`.kiro/settings/cli.json` `05d30ccb...`, SKILL.md); `after.sh` copies the attempt's own session out of the owner's `~/.kiro/sessions` (read only, matched by `agentMode` and workspace path)
and runs `allowed.py` on that copy. The MCP server's `HOME`, `HIREARCHY_STATE_DIR` and `UV_CACHE_DIR` stay sandboxed as in C1's V0 (the org runs' kiro home is the product's, under `SB/kiro-state`).
Setup 0, sign-in probe (no model call; `HOME=$SB0/home env -u KIRO_HOME kiro-cli whoami`): exit 0, `Authenticated with API key` (`detach/whoami.txt`).

- **A1 (sandbox `/tmp/hirearchy-p1-detach-1793122219`): invalid, repeated.** Turn 1 exited 1 after 30 s with `Error: Internal error (code -32603): {"details":"read EADDRNOTAVAIL"}`
  (a local network error; no model output; session credits 0.0000; `detach/a1-invalid/`). Not a quota or usage-limit error: `kiro-cli chat --list-models` and an HTTPS request worked right
  after. The protocol (E7 4.14 item 10) repeats an invalid attempt, at most 3. Profile and sandbox deleted (`detach/profile-deletions.txt`).
- **A2 (sandbox `/tmp/hirearchy-p1-detach-1793127126`, profile `hirearchy-study-p1-detach-1793127126`): valid, the first valid attempt decides.** Turn 1 (new session) and turn 2 (`--resume`:
  `progress` then `start` with `until_done=false`), each chat command followed by `; echo $? > ...; sleep 20`; sampler window 25 s. Chat calls used: 2 of 12 (A1 turn 1 included: 3).

| Condition (E7 4.14 item 10 (a)) | Fact | Result |
|---|---|---|
| 1. scheduler and run alive 5 s after the return and at the sleep's end; no `scheduler.signal`/`scheduler.exit` by then | `verdict survived`, `valid True`; return 18:54:56.914Z; `scheduler_alive_at_plus_5s True`, `run_alive_at_plus_5s True`; last sample with both alive 18:55:21.992Z (25.1 s after the return, past the sleep's end); scheduler pid 82714, `Ss`, ppid 1; run `child_pid` 82729; `run.start` 18:54:49.3Z, 7.6 s before the return | met |
| 2. the run ends by itself, `ok: true`, `killed: false` | `run.end` 18:55:53.581Z, `ok: true`, `killed: false`, `exit_code 0`, `duration_ms 64258`; ceo `tool.call`s `write`, `report`, both ok | met |
| 3. deliberate stop records `scheduler.signal` (SIGTERM, stop), then `scheduler.exit` | scheduler alive before the stop (ppid 1, `detach/a2-before-stop-ps.txt`); stop printed `scheduler stopped (pid 82714)`, exit 0, 18:56:10Z; `scheduler.signal` 18:56:10.800Z `SIGTERM`, `action: stop`, `ppid: 1`, `running: []`; `scheduler.exit` 18:56:11.741Z `reason: stopped by SIGTERM`, `runs_started: 1`; no process names the sandbox afterwards | met |
| 4. `allowed.py` prints ALLOWED | `ALLOWED` (`detach/a/allowed.txt`): disclose_context hirearchy, tool_load progress/start, tool_call progress, progress, start `{"until_done": false}` | met |

Models: assistant session `modelId` claude-sonnet-5.5, `effortLevel` high; org-run session claude-sonnet-5.5, high. Credits A2: assistant 1.0037 + org run 0.7226 = 1.7263; org runs 1.
Record: `detach/a/` (out, logs, events, scheduler.log, session copies, verdict, allowed, profile), `detach/samples/A2/`, `detach/a2-setup.txt`, `a2-before-stop-ps.txt`, `a2-stop.txt`.
Scheduler check (b) (C1's V0) is not repeated, as G0's protocol 11 says.

## 10. The F-G0-7 probe (`harness/probe.sh`, protocol 8.3): attempt 1 STOP, amendment H-A1, attempt 2 PASS
Both attempts: order F1, I1, I2, F2 (probe names = arm and repetition), two turns each, `env -u KIRO_HOME kiro-cli chat --v3 --no-interactive --trust-all-tools [--resume] --effort high --agent <profile> "<line>"; sleep 20`,
cwd = the throwaway sandbox; probe profiles `hirearchy-study-p1-probe-<F1|I1|I2|F2>-assistant` created and deleted with a record (`profiles-creations.txt`, `profiles-deletions.txt` in each probe folder). All 16 chat calls exit 0
(`*/turn-times.txt`); all eight sessions `modelId` claude-sonnet-5.5, `effortLevel` high.

### 10.1 Attempt 1 (`probe-attempt-1/`, 18:57:08Z-19:05:49Z, `preflight/probe-run-attempt-1.txt`): `PROBE: STOP`
`probe-attempt-1/compare.txt`: `session_start`, `tool_load` (reply text and per tool), non-`[tool]` stderr equal in all four sessions; failed empty-argument calls 0 in all four; positive control NO in all four
(root's `services`: `No services yet.`); lock checks of F1 and F2 failed. Cause: the frozen `probe.sh` called `define-service lead probe-memo` without `--deliverable` (`probe-attempt-1/F1/org-setup.txt`: `error: a first definition of `probe-memo`
needs deliverable ...`, exit 1), so no probe org had a service, and the arm-F lock command failed on a missing service (`probe-attempt-1/F1/lock-reply.txt`). A harness defect, not an arm difference and not a product defect.
The step sent a `warning` and waited. Attempt 1's evidence is kept unchanged in `probe-attempt-1/` (each arm/rep folder also holds `sandbox-copy/` = the sandbox's `org/` tree, SKILL.md and `cli.json`, copied before the sandbox was deleted).

### 10.2 Amendment H-A1 (manager ruling `manager-decision-probe-define.md`; before F1's first turn)
Done in the ruling's order:
1. **Fix:** `probe.sh` lines 42-43 only: `--deliverable 'A memo of at most 400 words in the reply'` added (`--path` is optional and not needed: checked on a throwaway org, `define-service` exit 0, then the unchanged `--locked` line exit 0, contract v1 -> v2, `locked: true`,
   the owner's quiet note present; org deleted). The `--locked` line is byte for byte as it was.
2. **Whole-harness CLI check:** every product CLI call of the harness checked against `hirearchy <subcommand> --help`: all OK after the fix, no other MISMATCH (list in `harness/CHANGES.md`, "Amendment H-A1").
3. **Attempt 1 kept:** `probe/` moved to `probe-attempt-1/`; the four sandboxes' evidence copied in; the four sandboxes deleted (section 12); no probe profile was left in `~/.kiro/agents`.
4. **Re-freeze:** `probe.sh` `6d33606b1972fb55e8c02343624abe52` -> `6e18b2826cb9bb942c63c5cce36c3f58`; `CHANGES.md` `9c7c7cbff8ea428de76c0696bf72b9b4` -> `88a4a0f5f25bf56196f1700b7c38f96a`; `MD5SUMS`
   `524b857e9b75f6f104f22d11860145e2` -> `d21508978d71e6d805f1760b25acb1b6`; `protocol.md` and `protocol.md5` unchanged (`70237b0f...`); `protocol-amendment-1.md` (md5 `8a203c5efd7445c55096858320ef46e5`, in `protocol-amendment-1.md5`)
   records H-A1 as section 0 prescribes; `freeze.txt` has the appended block. Self-check on the re-frozen files (`harness-selfcheck/h-a1-run/`, console `harness-selfcheck/h-a1-run-console.txt`, an earlier run with a relative output
   path failed at once for lack of the output folder and was overwritten): `selfcheck: 17 of 17 parts OK; tests exit 0`, `206 passed in 9.76s`.

### 10.3 Attempt 2 (`probe/`, 19:12:49Z-19:21:03Z, `preflight/probe-run.txt`): `PROBE: PASS`
`probe/compare.txt` (verbatim):
```
session_start: equal in all four sessions
tool_load (the reply's other text): equal in all four sessions
tool_load hirearchy::services: equal in all four sessions
tool_load hirearchy::whoami: equal in all four sessions
non-[tool] stderr lines (digits masked): equal
failed empty-argument calls F1: 0 (session store, f-g0-7 section 1); 'is not available' in stderr: 0 (reported)
failed empty-argument calls F2: 0 (session store, f-g0-7 section 1); 'is not available' in stderr: 0 (reported)
failed empty-argument calls I1: 0 (session store, f-g0-7 section 1); 'is not available' in stderr: 0 (reported)
failed empty-argument calls I2: 0 (session store, f-g0-7 section 1); 'is not available' in stderr: 0 (reported)
positive control F1: root's services names probe-memo with contract v2: yes
positive control F2: root's services names probe-memo with contract v2: yes
positive control I1: root's services names probe-memo with contract v1: yes
positive control I2: root's services names probe-memo with contract v1: yes
lock checks F1: 3 of 3 yes
lock checks F2: 3 of 3 yes
PROBE: PASS
```
| Probe result, attempt 2 | Arm F, rep 1 (`F1`) | Arm F, rep 2 (`F2`) | Arm I, rep 1 (`I1`) | Arm I, rep 2 (`I2`) |
|---|---|---|---|---|
| sandbox | `/tmp/hirearchy-p1-probe-F1-1793128368` | `...-F2-1793128740` | `...-I1-1793128490` | `...-I2-1793128614` |
| service definition (`org-setup.txt`) | init, hire, define-service all exit 0 | same | same | same |
| `session_start` (memories block included), `tool_load` hashes per tool, non-`[tool]` stderr | equal in all four | equal | equal | equal |
| failed empty-argument calls (session store) / `is not available` in stderr | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| root's turn-2 `services` line | `- probe-memo (offered by lead; contract v2, playbook v0)` | `contract v2` | `contract v1` | `contract v1` |
| positive control (v2 in F, v1 in I) | yes | yes | yes | yes |
| lock checks (arm F): reply names the lock, exit 0; `SERVICE.md` `locked: true` at version before + 1 = 2; owner's quiet note `locked: false -> true (you may no longer revise the playbook)` in `lead/inbox` | 3 of 3 yes | 3 of 3 yes | n/a | n/a |
| credits | 0.7661 | 0.7907 | 0.7679 | 0.7682 |

**Verdict per arm: arm F PASS (both repetitions), arm I PASS (both repetitions).** The only difference between the arms is the contract version in root's `services` reply (`contract v2` in F, `contract v1` in I), which the arm setup (the lock) explains and the
positive control expects. No unexplained difference; no failed empty-argument call in either arm; `memories.db` unchanged (`f0aaf02a8a216c3a291a253d2c52d461` before the probe and after it). The arm-F lock command has the same form as the stream hook's (`after_turn.sh` line 140).

## 11. Cost of the preflight
| Item | Credits | Org runs |
|---|---|---|
| ambient probe | 0.2920 | 0 |
| org-agent run (item 7) | 0.6162 | 1 |
| scheduler check A1 (invalid) | 0.0000 | 0 |
| scheduler check A2 (assistant 1.0037 + org run 0.7226) | 1.7263 | 1 |
| **probe attempt 1** (4 sessions: 0.7602 + 0.7775 + 0.7775 + 0.7581) | **3.0734** | 0 |
| **probe attempt 2** (4 sessions: 0.7661 + 0.7679 + 0.7682 + 0.7907) | **3.0928** | 0 |
| H-A1 self-check, CLI form check on a throwaway org (no model call) | 0.0000 | 0 |
| **total preflight** | **8.8007** | **2** |
The probe's two attempts together cost 6.1662 credits (the sum counts against the probe's line in the approval, about 20 credits; the rest of that line, the ambient probe, the org-agent run and the scheduler check, is 2.6345 more).
Credits are the sums of `usage_summary.promptTurnSummaries[].usage` per kiro session (`preflight/session_credits.py`, as `extract_mechanical.py`). Stage 1's figure for the preflight, 8.80 credits, is far below the "about 20" estimated.

## 12. Deletions and what is left behind
Records: `preflight/deletions.txt`, `preflight/ambient-probe/probe-profile-deletion.txt`, `preflight/detach/profile-deletions.txt`, `probe-attempt-1/profiles-deletions.txt`, `probe/profiles-deletions.txt`.
- Deleted by exact path with a prefix guard: the item-7 sandbox `/tmp/hirearchy-p1-preflight-1793121965` and its org kiro home and scratch cwd under `~/Library/Application Support/hirearchy/{kiro-home,kiro-cwd}/hirearchy-p1-preflight-1-222a188946652ef9`;
  the scheduler-check sandboxes A1 and A2; the **four attempt-1 probe sandboxes** `/tmp/hirearchy-p1-probe-{F1-1793127427,I1-1793127561,I2-1793127688,F2-1793127813}` (19:11:06Z, no process named them; their evidence is in `probe-attempt-1/*/sandbox-copy/`);
  the H-A1 CLI-form check org `/tmp/hirearchy-p1-hA1check-1793128181`; the ambient-probe profile; the A1 and A2 detach profiles; the eight probe profiles (four per attempt). No `hirearchy-study-p1-*` profile remains in `~/.kiro/agents`, which holds exactly its seven pre-existing entries.
- Still present, for the teardown: `/tmp/hirearchy-p1-ambient-1793121877` and the four attempt-2 probe sandboxes `/tmp/hirearchy-p1-probe-{F1-1793128368,I1-1793128490,I2-1793128614,F2-1793128740}`. No process names any P1 sandbox.
- Evidence kept: `preflight/`, `probe/`, `probe-attempt-1/`, `deterministic/at-8bf7c69b/`, `safety-before.txt`, `preflight-safety-{after,diff}.txt` (and the `-attempt-1` pair), `protocol-amendment-1.md(.md5)`, `harness-selfcheck/h-a1-run*`, this file.
- Files changed in the frozen set by the amendment: `harness/probe.sh`, `harness/CHANGES.md`, `harness/MD5SUMS` (and the new `protocol-amendment-1.md`, `protocol-amendment-1.md5`, an appended block of `freeze.txt`). No product file changed; the product freeze diff is empty. Nothing was staged or committed.
- `memories.db` md5: before the preflight `f0aaf02a8a216c3a291a253d2c52d461`; after `f0aaf02a8a216c3a291a253d2c52d461` (`preflight/memories-md5-start.txt`, `preflight/memories-md5-end.txt`).

Result: PASS
