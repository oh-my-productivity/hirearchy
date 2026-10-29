# P2 preflight (protocol section 9; step 3 of workflow `wf_8ee5197e04b8ee7c`)

Run 2026-10-29, 10:13Z-10:35Z, by the `preflight` step. Facts only. No stream, stream sandbox or stream profile was started.
No product file, `protocol.md`, standing rule or harness file was changed. Nothing was staged, committed or pushed (the study's one commit is step 13's).
`/Users/aminalizadeh/organization`, `~/.kiro/skills/` (apart from the recorded arm-C probe moves of `~/.kiro/skills/hirearchy/`), `~/.kiro/memories/`
(md5 and `ls` only) and the owner's files in `~/.kiro/agents` were not touched. No credential was read. `KIRO_HOME` was unset throughout.
`zsh harness/skill_move.sh recover` ran first (`preflight/recover.txt`): `no unrestored move`, global skill in place with md5 `443e1bc4...`. No `RECOVERED` line.

Paths below are relative to `/Volumes/workspace/hirearchy/studies/P2-retro-and-growth/evidence/` (`EV`).

**Result: PASS**, with one freeze gap repaired (check 1) and two of my own harness-free check attempts re-run (checks 9 and 10), all disclosed below.

| # | Check | Result | Evidence |
|---|---|---|---|
| 1 | md5 gate (protocol, standing rules, 76 `MD5SUMS` lines) | PASS after repairing a freeze gap (see 1) | `preflight/gates.txt`, `preflight/freeze-gap-standing-rules-md5.md`, `preflight/gates-end.txt` |
| 2 | Freezes, start and end (arm R `3d6b28aa`, empty product diff; arm C `aac6af1b`, clean) | PASS | `preflight/gates.txt`, `preflight/gates-end.txt`, `deterministic/freeze-before-R.txt` |
| 3 | kiro-cli 2.33.0, claude-sonnet-5.5 listed | PASS | `preflight/kiro-cli.txt`, `preflight/model-listed.txt`, `preflight/model-checks.txt` |
| 4 | Safety snapshots, owner's `~/.kiro` md5s, `memories.db` | PASS (unchanged) | `safety-before.txt`, `preflight-safety-after.txt`, `preflight-safety-diff.txt` |
| 5 | One real org-agent run at `--effort high`, each arm | PASS | `preflight/preflight-R/`, `preflight/preflight-C/`, `preflight/model-checks.txt` |
| 6 | Injection: `--dry-run`, `--selftest`, offline poll tests, live poll check, each arm | PASS | `preflight/injection-dryrun-selftest.txt`, `preflight/poll-check/` |
| 7 | Scheduler check, each arm | PASS | `preflight/scheduler-check/` |
| 8 | `setup_stream.sh R1 --dry-run`, `C1 --dry-run` | PASS | `preflight/setup-dry-run.txt` |
| 9 | Probe (`probe.sh`), both arms, 2 reps, 2 turns | **PROBE: PASS**; skill PROVED in all four sessions | `probe/`, `preflight/probe-run.txt` |
| 10 | Deterministic part | PASS: arm R 39 passed; arm C 29 passed | `deterministic/` |

## 1. Gates and freeze
- `md5 -q protocol.md` = `31bc856c...` = `protocol.md5` line 1; `standing-rules-streams.md` = `909fbb79...`; `harness/MD5SUMS` md5 `a1ff86dd09d4ec766d8f2fb3701a3045` (= `freeze.txt`), 76 lines, all match
  (`md5sum -c` 76 OK, and `arm.sh`'s `md5gate_ok`). Unchanged at the end (`preflight/gates-end.txt`).
- **Freeze gap, repaired (a finding for the report, not a stop).** Step 2 recorded the standing rules' md5 only as line 2 of `protocol.md5`. It did not write the
  separate `standing-rules-streams.md5` that protocol 0 names and that `arm.sh`'s `md5gate_ok` reads. My first gate run printed `md5 gate: standing-rules-streams.md5 missing (not frozen)`.
  Left alone, `setup_stream.sh`, `next_stream.sh` and `turn.sh` would have refused every stream. I wrote `standing-rules-streams.md5` with the one line already in `protocol.md5` and `freeze.txt`
  (`909fbb79c838b69a2d620089545c3ae6  standing-rules-streams.md`), verified equal to the file's md5. It is a new record of a value frozen earlier; no frozen file changed.
  The manager may want to confirm it (`preflight/freeze-gap-standing-rules-md5.md`).
- `git -C /Volumes/workspace/hirearchy rev-parse HEAD` = `3d6b28aa17a70a3f95854c73c2f479b6361a71de`; `git diff --stat 3d6b28aa HEAD -- src skills pyproject.toml uv.lock` empty at the start, after the
  deterministic runs and at the end. Arm C: `rev-parse HEAD` = `aac6af1b47b721515106f03f1dd6eb6758da6e55`, `status --porcelain` empty at the start, after its tests and at the end.
  Main checkout `git status --porcelain`: ` M docs/design/org-growth-phase-2.md` (the 18.6 line, step 1a), `?? docs/research/`, `?? studies/P2-retro-and-growth/` (no tracked file modified by me).
- Skills: arm R `443e1bc4911aa4d6aaa6457e78f673c1`, arm C `b10238639f48ab351fa44a06aed03ffb`, global copy `443e1bc4911aa4d6aaa6457e78f673c1`.

## 2. Safety snapshots and `memories.db`: PASS
- `safety-before.txt` (10:13:50Z) and `preflight-safety-after.txt` (10:34:25Z); `preflight-safety-diff.txt` shows only: the label and date lines, the mtimes of the directories `~/.kiro/memories`
  and `~/.kiro/agents` (the latter changed by the recorded creation and deletion of the four probe profiles; its file list and every file md5 are identical), and the new `/tmp/hirearchy-p2/` sandbox names.
  All `~/.kiro/settings/*` md5s, the global `SKILL.md`, the md5s of the files in `~/.kiro/agents`, `/Users/aminalizadeh/organization` (file count, newest mtime, tree digest) and `/Volumes/workspace/orgs` are identical.
- **`memories.db` md5, before: `ba97f447639184d1fb7da9eccf2b2e8c`; after: `ba97f447639184d1fb7da9eccf2b2e8c`** (`preflight/memories-md5-start.txt`, `preflight/memories-md5-end.txt`). Unchanged.
  Only the `~/.kiro/memories` directory's mtime moved (10:13 to 10:31, `preflight/memories-ls-{start,end}.txt`), as P1 saw; the file's size and mtime are identical.
- `~/.kiro/agents` holds its seven pre-existing entries; no `hirearchy-study-p2-*` profile remains (`probe/profiles-creations.txt`, `probe/profiles-deletions.txt`: four created, four deleted).

## 3. kiro-cli: PASS
`kiro-cli 2.33.0`. `model_check.sh listed preflight`: `listed: claude-sonnet-5.5: yes (... 1.30x credits ... 1M context window)`, `RESULT: preflight listed: OK`.

## 4. One real org-agent run per arm, `--effort high`: PASS (`harness/preflight_run.sh R|C`)
- Arm R (`preflight/preflight-R/run.txt`): init, hire, task exit 0; `lead: run finished in 22s`; `scheduler exiting: finished: no open tasks`; run exit 0. Run log `# cmd:` has `--model claude-sonnet-5.5 --effort high --v3` and `/Volumes/workspace/hirearchy/src/...`. `RESULT: preflight-R org: OK`.
- Arm C (`preflight/preflight-C/run.txt`): same, with `/Volumes/workspace/hirearchy/.worktrees/p2-arm-c/...` in every `# cmd:` (no arm-C call reached the main checkout). **One effort stop:** `lead: run stopped because kiro-cli did not set its effort: not charged, relaunched`;
  the run log says `# kiro: effort not set, run stopped (kiro-cli: failed to set effort 'high': model 'claude-sonnet-5.5' offers no effort levels); tool effects: none` (`preflight/preflight-C/org-evidence/20261029T101458299812.log` line 110).
  The relaunch finished in 28s with `--effort high`. `RESULT: preflight-C org: OK` (2 logs, both `--model claude-sonnet-5.5 --effort high`). **Effort stops in the preflight: arm R 0, arm C 1** (reported; the product's 1.1 stop worked as designed, uncharged). Streams must count these per stream.

## 5. Injection: PASS
`harness/injection.sh preflight-R|preflight-C ...` (arm R: `inject_root_rework.py` md5 `1c4e7824...`; arm C: `inject_root_rework_armc.py`):
- `--dry-run`: `title md5 849fe21b... ok; note len 866 md5 4cdbcb9b... ok` in both arms.
- `--selftest`: root's 27 tools in arm R (with `retro`), 26 in arm C (no `retro`); includes `request`, `start`, `progress`, `status`, `stop`, `quality`, `services`.
- `test_poll_loop.py`: `7 passed, 0 failed`.
- **Live poll check** (`preflight/poll-check/`, both arms in parallel against an open task and no scheduler, `--max-seconds 120`): exit 0 in both; 5 polls each, each reply 0.0 s ("Not waiting: no scheduler is running"), pauses 5, 10, 20, 40, 45 s;
  final line `polling ended (window cap: 120 seconds passed): progress(task_id) polls 5, quick replies 5, paused 120.0s in all` (the same as P1's pass). Two earlier attempts are kept and were not the check: `preflight/poll-check-attempt-0-bad-task-id/`
  (my shell grep took the word `exit` for the task id; the tool answered `no task`, exit 1) and `preflight/poll-check-attempt-1-settled-task/` (a finished task settles on poll 1, which proves nothing about the loop).
  The full injection (`request`, `start`) was not run.

## 6. Scheduler check: PASS (`preflight/scheduler-check/`)
The protocol's section 9 names "the scheduler check" without a procedure, and the frozen P2 harness has no copy of P1's `c1-tools` form. I used a no-assistant form that tests the same thing the streams depend on: the arm's own MCP server
(`harness/mcp_call.py`, root's seat, a throwaway org under `/tmp/hirearchy-p2/`), `start` with `until_done=false`, the client process exits, and the scheduler must survive it. Script: `preflight/scheduler-check/scheduler-check.sh`.
| Condition | Arm R (`R/log.txt`) | Arm C (`C/log.txt`) |
|---|---|---|
| scheduler pid | 94649 | 94853 |
| alive, ppid 1, `Ss` at +5 s and +25 s after the client's exit | yes, yes | yes, yes |
| run ends by itself, `ok: true`, `killed: false`, exit 0 | `duration_ms` 24104 | `duration_ms` 20093 |
| `stop` records `scheduler.signal` (SIGTERM, `action: stop`, `ppid: 1`) then `scheduler.exit` (`stopped by SIGTERM`) | yes | yes |
| no process names the sandbox afterwards | yes | yes |
| `model_check.sh org` | OK | OK |
The first run of the script (`preflight/scheduler-check-attempt-0-zsh-wordsplit-bug/`) failed at once: my script put the command in a string that zsh does not word-split (exit 127, no scheduler started, no run). The second run is the check above.
No scheduler or MCP process of the study remains (`ps` finds none naming `/tmp/hirearchy-p2/`).

## 7. `setup_stream.sh R1 --dry-run` and `C1 --dry-run`: PASS (`preflight/setup-dry-run.txt`)
Every gate OK (md5 gate, both freezes, `KIRO_HOME` unset, both products' skill md5s, global skill in place, no unrestored move); `claude-sonnet-5.5 listed` is not checked in `--dry-run` (check 3 did). The memories gate saw no previous stream.
Nothing was created or moved.

## 8. The probe (`harness/probe.sh`, protocol 8.3): PROBE: PASS
Order C-1, R-1, R-2, C-2, 10:27:05Z-10:33Z (`preflight/probe-start-utc.txt`, `preflight/probe-end-utc.txt`, console `preflight/probe-run.txt`). Two turns each, all eight chat calls exit 0
(`probe/*/turn-times.txt`), `env -u KIRO_HOME kiro-cli chat --v3 ... --effort high --agent hirearchy-study-p2-probe-<C1|R1|R2|C2>-assistant`; each session `modelId` claude-sonnet-5.5, `effortLevel` high (`probe/*/session.json`).
Each probe org: `init`, `hire root lead`, `define-service lead probe-memo` through the arm's CLI, all exit 0 (`probe/*/org-setup.txt`). Final line of `probe/compare.txt` (verbatim):
```
note: memories block lengths: probe-C1=6982, probe-R1=6982, probe-R2=6982, probe-C2=6982
note: arm R: loaded tools whose hash equals the catalog's: 0 of 2 (reported)
note: arm C: loaded tools whose hash equals the catalog's: 0 of 2 (reported)
note: catalogs: R 27 tools, C 26; differing entries: ['apply_org', 'blueprint_example', 'define_service', 'hire', 'propose_org', 'retro']
PROBE: PASS
```
- `session_start` (the `<memories>` block cut out; block length 6982 in all four) equal in all four sessions; non-`[tool]` stderr equal; within an arm, every tool loaded in both repetitions has the same hash; across arms, the two loaded tools (`whoami`, `services`) have the same hash,
  as the products' catalog entries for them agree. **No difference the arm setup does not explain.** The only differences are the two products' catalogs (R 27 tools, C 26): `retro` exists only in R; `apply_org`, `blueprint_example`, `define_service`, `hire` and `propose_org` have
  different descriptions or schemas (2a's brief, extension and provenance changes). The catalogs are `probe/catalog-R.json` and `probe/catalog-C.json`.
- **Failed empty-argument calls: 0 in all four sessions.** Positive control: arm R's catalog holds `retro`, arm C's does not; root's turn-2 `services` reply names `probe-memo` in all four.
- Note on the comparator: its "loaded tools whose hash equals the catalog's" line reads 0 of 2 in both arms because the loaded-tool hash and the catalog hash are built in different forms. The line is only reported, not a stop condition, and the cross-arm equality
  of the loaded `whoami`/`services` hashes plus the within-arm equality are what the comparison rests on. I did not alter the comparator.
- **Skill proof (`skill_proof.py`, `probe/<s>/skill-proof.json`):**
  | Session | Arm | `disclose_context` results | arm's whole `SKILL.md` an exact substring | other arm's | R's distinct lines 113 / 119 | verdict |
  |---|---|---|---|---|---|---|
  | probe-C1 | C | 1 | yes | no | absent / absent | PROVED |
  | probe-R1 | R | 1 | yes | no | present / present | PROVED |
  | probe-R2 | R | 1 | yes | no | present / present | PROVED |
  | probe-C2 | C | 1 | yes | no | absent / absent | PROVED |
  Checked again by hand with `grep -c` over each session's messages: `A retro: when a reply says one is due` and `needs.elicitation` appear once in each arm-R session and zero times in each arm-C session.
  Arm R's session loaded the text of md5 `443e1bc4...` (the repo copy, equal to the global one); arm C's loaded `b10238639f48ab351fa44a06aed03ffb`, with the global copy aside.
- **Global-skill moves for arm C** (`skill-moves.txt`, `probe/probe-C*/skill-aside.txt`, `skill-restore.txt`), md5 `443e1bc4911aa4d6aaa6457e78f673c1` checked before and after each move:
  - probe-C1: ASIDE-PENDING and ASIDE 10:27:07Z to `studies/P2-retro-and-growth/skill-aside/probe-C1-1793269627/hirearchy`; RESTORE 10:28:32Z, md5 ok.
  - probe-C2: ASIDE 10:31:25Z to `.../probe-C2-1793269885/hirearchy`; RESTORE 10:32:47Z, md5 ok.
  - After the probe and at the end: `skill_move.sh status` = `global skill: in place, md5 443e1bc4911aa4d6aaa6457e78f673c1`, `no unrestored move`. During the arm-R runs the global copy stayed in place.

## 9. Deterministic part: PASS (output verbatim in `deterministic/`)
```
arm R, from /Volumes/workspace/hirearchy (3d6b28aa):
UV_LINK_MODE=copy uv run pytest -q tests/e2e/test_org_growth_2.py tests/e2e/test_org_growth_1.py
.......................................                                  [100%]
39 passed in 20.62s                                      (deterministic/pytest-output-arm-R.txt, exit 0)

arm C, from /Volumes/workspace/hirearchy/.worktrees/p2-arm-c (aac6af1b):
UV_LINK_MODE=copy uv run pytest -q tests/e2e/test_org_growth_1.py
.............................                                            [100%]
29 passed in 6.78s                                       (deterministic/pytest-output-arm-C.txt, exit 0)
```
Both freezes held after the runs; the arm-C worktree stayed clean.

## 10. Cost of the preflight
Credits are the sums of `usage` over `usage_summary` records (`running_credits.py`'s rule: the assistant's session messages, and each org run's kiro session).
| Item | Credits | Org runs |
|---|---|---|
| org-agent run, arm R (check 4) | 0.2008 | 1 |
| org-agent run, arm C (check 4; the uncharged effort-stopped run is not counted) | 0.2162 | 1 charged (+1 stopped, uncharged) |
| scheduler check, arm R | 0.2132 | 1 |
| scheduler check, arm C | 0.2018 | 1 |
| probe, 4 assistant sessions (C1 1.6695 + R1 1.4837 + R2 1.5629 + C2 1.5761) | 6.2922 | 0 |
| injection, dry runs, poll checks, `setup --dry-run`, tests | 0.0000 (no model call) | 0 |
| **total** | **7.12** | **4 charged (+1 uncharged effort stop)** |
This is far below the preflight's share of stage 1 (260-420 with the first pair, about 20 for the preflight).

## 11. What is left behind
- Throwaway sandboxes under `/tmp/hirearchy-p2/` for the teardown to delete: `preflight-R-1793268869`, `preflight-C-1793268897`, `preflight-sched-{R,C}-*` (two of each; the first pair, from the failed script run, never started a scheduler), `probe-{C1-1793269625,R1-1793269712,R2-1793269796,C2-1793269884}`,
  and the product's org state for the org runs under `~/Library/Application Support/hirearchy/{kiro-home,kiro-cwd}/preflight-*` (outside `~/.kiro`; the run logs and `ORG.md` of checks 4 are copied to `preflight/preflight-{R,C}/org-evidence/`). Nothing was deleted, because deletion is the teardown's.
- Evidence kept: `preflight/`, `probe/`, `deterministic/`, `skill-moves.txt`, `standing-rules-streams.md5`, `safety-before.txt`, `preflight-safety-{after,diff}.txt`, this file.
- Files I added to the frozen set's neighbourhood: `standing-rules-streams.md5` (see 1). No harness file changed; `harness/MD5SUMS` md5 is unchanged.

Result: PASS
