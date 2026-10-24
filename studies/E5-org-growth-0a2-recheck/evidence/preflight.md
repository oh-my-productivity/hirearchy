# E5 preflight (protocol 4.14; workflow step 2 of 9)

Run 2026-10-24, 02:54-03:02 UTC (local WEST = UTC + 1 h), by the preflight step. Facts only. No stream, assistant session or stream sandbox was started. No product file, harness file or protocol file was changed. Nothing was staged, committed or pushed.

Raw files are under `evidence/preflight/` unless a path is given. Paths below are relative to `/Volumes/workspace/hirearchy/studies/E5-org-growth-0a2-recheck/evidence/`.

**Result: PASS**

| # | Check | Result | Evidence |
|---|---|---|---|
| 1 | md5 gates | PASS | `preflight/gates.txt`, `preflight/final-gates.txt` |
| 2 | Freeze | PASS | `preflight/freeze-check.txt` |
| 3 | kiro-cli version and model list | PASS | `preflight/kiro-cli.txt`, `preflight/model-checks.txt` |
| 4 | Safety snapshot before | PASS | `preflight-safety-before.txt` |
| 5 | One real org-agent run through the real scheduler | PASS | `preflight/lead-run.log`, `preflight/org-setup.txt`, `preflight/scheduler-run.txt`, `preflight/tool-call-events.jsonl`, `preflight/org-kiro-session/`, `preflight/model-checks.txt` |
| 6 | Fixed injection script (polling loop, text identity) | PASS | `preflight/poll-check/poll-check-log.txt`, `preflight/injection-text-identity.txt`, `preflight/injection-dryrun-selftest.txt`, `preflight/test_poll_loop.txt` |
| 7 | Deterministic part at `6618c0d` | PASS | `deterministic/SUMMARY.md`, `deterministic/at-6618c0d/` |
| 8 | Safety snapshot after, and diff | PASS | `preflight-safety-after.txt`, `preflight-safety-diff.txt` |
| 9 | Ambient probe check (protocol 4.14 item 6; not in the manager's list, run because the protocol's preflight includes it) | PASS | `probe/` |

## 1. md5 gates: PASS
- `md5 -q protocol.md` = `afd437c103407ec5899e4993b465cf25`; `cat protocol.md5` = `afd437c103407ec5899e4993b465cf25`. Match. No `protocol-amendment-*` file exists.
- `cd harness; while read h f; do [ "$(md5 -q "$f")" = "$h" ] || echo "MISMATCH $f"; done < MD5SUMS` printed nothing (16 lines checked). `md5 -q harness/MD5SUMS` = `5d22bf230cefe21f3477cb1f6dc1aaa6` (as recorded in `freeze.txt`).
- `md5 -q /Users/aminalizadeh/.kiro/skills/hirearchy/SKILL.md` = `b7187d6ef749505893e9aef99276ef7c`; `md5 -q /Volumes/workspace/hirearchy/skills/hirearchy/SKILL.md` = `b7187d6ef749505893e9aef99276ef7c`; `git show 6618c0d:skills/hirearchy/SKILL.md | md5 -q` = `b7187d6ef749505893e9aef99276ef7c`. All equal the required value.
- Notes (`903e3bbf...`, `3893bd63...`, `9976a765...`) and `answer-key.md` (`2fb69bbef857c2bd4862cd5dd8be9da8`) match protocol 4.6.
- The gates were run again at the end (`preflight/final-gates.txt`): all still hold.

## 2. Freeze: PASS
- `git -C /Volumes/workspace/hirearchy rev-parse HEAD` = `6618c0d80401233675366684fc86dc566657e8db` (short `6618c0d`), branch `main`.
- `git -C /Volumes/workspace/hirearchy diff --stat 6618c0d HEAD -- src skills pyproject.toml uv.lock`: empty output, exit 0.
- `git status --porcelain`: `?? docs/research/` and `?? studies/E5-org-growth-0a2-recheck/` only (before and after).

## 3. kiro-cli: PASS
- `kiro-cli --version` = `kiro-cli 2.33.0` (KAS 0.66.48 in the kiro logs).
- `kiro-cli chat --list-models` (exit 0) line: `  claude-sonnet-5.5    1.30x credits      Claude Sonnet 5.5 model with 1M context window`.
- `harness/model_check.sh listed preflight`: `RESULT: spreflight listed: OK` (exit 0), `listed: claude-sonnet-5.5: yes`. No substitution was needed.

## 4. Safety snapshot before: PASS
`zsh harness/safety-snapshot.sh preflight-before > preflight-safety-before.txt` (exit 0, 87 lines, taken 02:54:51Z, before anything was created). Global SKILL.md `b7187d6e...`; `~/.kiro/settings/cli.json` `05c63a68e44a5d7f907e7e505eba8927`; `memories.db` `3f53a1d90a590b253fc33aaa1c11342c`; HEAD `6618c0d`; freeze diff empty.

## 5. One real org-agent run through the real scheduler: PASS
Sandbox `P` = **`/tmp/hirearchy-e5-preflight-1792810596`** (epoch `1792810596`). Org at `P/org`. It was deleted at the end of the step (protocol 4.14 item 9) after its evidence was copied; the path no longer exists.

Commands (from `preflight/org-setup.txt` and `preflight/scheduler-run.txt`):
```
hirearchy init P/org --mission "E5 harness preflight (throwaway)" --model claude-sonnet-5.5      -> exit 0; P/org/ORG.md: default_model: claude-sonnet-5.5, effort: high
hirearchy --root P/org hire root lead --role Lead --charter "You are the lead of a throwaway preflight org. ..." --tools read,write --model claude-sonnet-5.5   -> hired lead
hirearchy --root P/org task lead --title "Preflight note" --goal "Use the hirearchy org_write tool to write the file lead/work/preflight.txt ... E5-PREFLIGHT-OK. Then call the hirearchy report tool with status done." --acceptance "..." --budget 2
  -> task 20261024T025636794645-root-0325 -> lead (budget 2)
(live poll check, check 6, before the scheduler started)
perl -e 'alarm shift; exec @ARGV' 900 hirearchy --root P/org run --until-done --max-runs 2
  -> lead: started run (1 message(s)) / lead: run finished in 24s / scheduler exiting: finished: no open tasks   (exit 0, 02:58:53Z-02:59:17Z)
```
The product's CLI forms matched the protocol's; no form was adapted.

Run log (`preflight/lead-run.log`, from `P/org/lead/runs/20261024T025853383721.log`), `# cmd:` line:
```
# cmd: /Users/aminalizadeh/.local/share/uv/tools/hirearchy/bin/python -I -S /Volumes/workspace/hirearchy/src/hirearchy/kiro/_launch.py --start-deadline 60 -- kiro-cli chat --no-interactive --agent hirearchy-hirearchy-e5-preflight-1-cfccbe-read-write-xec4c1da7 --model claude-sonnet-5.5 --effort high --v3 --require-mcp-startup --output-format stream-json <prompt on stdin>
```
- One `# cmd:` line, one `--model claude-sonnet-5.5`, one `--effort high`. `# kiro: run started (engine v3)`, `[run finished] success (end_turn)`, `# exit 0 after 24s`.
- Hirearchy tool calls in the log (`^\[tool\] @hirearchy/[A-Za-z_]+`, RL3): 4: `org_write lead/work/preflight.txt`, `org_read`, `report status=done`, `org_write lead/MEMORY.md`. Each has a `[tool ok]` line.
- `hirearchy --root P/org obs events --kind tool.call`: 9 events. The 4 by `lead` (run `lead@20261024T025853383721`, 02:59:08-02:59:12Z) equal the 4 log lines; the other 5 are root `progress` events from the poll check (check 6). All `ok`. `preflight/tool-call-events.jsonl`, `preflight/obs-events-tool-call.txt`.
- Org-run session (`preflight/org-kiro-session/session.json`): `agentMode` `hirearchy-hirearchy-e5-preflight-1-cfccbe-read-write-xec4c1da7`, `modelId` `claude-sonnet-5.5`, `effortLevel` `high`, `workspacePaths[0]` equals the log's `# cwd:`, `createdAt` 02:59:03.98Z inside the `run.start` (02:58:53.39Z) and `run.end` (02:59:17.59Z) events. The session's `messages.jsonl` carries no model-id fields.
- `zsh harness/model_check.sh org preflight /tmp/hirearchy-e5-preflight-1792810596`: `org run logs checked: 1`, `--model ['claude-sonnet-5.5'] --effort ['high']`, `RESULT: spreflight org: OK`, exit 0 (`preflight/model-checks.txt`).
- Task outcome (recorded, not the pass condition): `done`, `lead/work/preflight.txt` holds `E5-PREFLIGHT-OK`, runs 1 of 2 (1 returned), `scheduler: stopped (finished: no open tasks)`. `hirearchy --root P/org check`: all 6 checks PASS (`preflight/final-progress-check.txt`). The scheduler log file did not exist under `.runtime/`; `scheduler.exit` = `finished: no open tasks`.
- No prep assistant profile was needed for this run: the org agent's scheduler profile lives in the per-org kiro home, not in `~/.kiro/agents`.
- Kiro state dir `~/Library/Application Support/hirearchy` existed before the preflight (it holds E4's `kiro-cwd/hirearchy-e4-*` leftovers), so only the preflight's own kiro home and scratch cwd were deleted (`preflight/deletions.txt`): `.../kiro-home/hirearchy-e5-preflight-1-cfccbe52ec29dae5`, `.../kiro-cwd/hirearchy-e5-preflight-1-cfccbe52ec29dae5`, `/tmp/hirearchy-e5-preflight-1792810596`. Each was guarded by a path-prefix check. No process referenced the sandbox before deletion.

## 6. Fixed injection script: PASS
Script md5 `1c4e7824e448a3a34e24a7b759a59fcd` = `MD5SUMS`.
- **Live poll check** (`uv --directory /Volumes/workspace/hirearchy run python harness/inject_root_rework.py --poll-check --org P/org --task 20261024T025636794645-root-0325 --out evidence/preflight/poll-check --max-seconds 120`, run before the scheduler started: the F-E4-9 condition, every reply "Not waiting: no scheduler is running"). Exit 0, 02:56:47Z-02:58:47Z. It called only `progress(task_id, wait_seconds)`.

  | Poll | Request time (UTC) | Reply | Pause before next |
  |---|---|---|---|
  | 1 | 02:56:47 | 0.0 s | 5.0 s |
  | 2 | 02:56:52 | 0.0 s | 10.0 s |
  | 3 | 02:57:02 | 0.0 s | 20.0 s |
  | 4 | 02:57:22 | 0.0 s | 40.0 s |
  | 5 | 02:58:02 | 0.0 s | 44.9 s (to the window end) |

  Final line: `polling ended (window cap: 120 seconds passed): progress(task_id) polls 5, quick replies 5, paused 119.9s in all`. Pass rule: every poll logged; each next poll started at least 5 s later; 5 polls (limit 25); the final line gives the count. E4's loop made 36,513 / about 700 / about 490 polls in the same condition.
- **Text identity with E4** (`preflight/injection-text-identity.txt`; E4's script `c80e25d65fe58cdb97d7faa758d59484`, loaded with bytecode writing off): all ten constants equal (`TITLE_MD5` `849fe21b104be883af9b3c06367d4445`, `NOTE_MD5` `4cdbcb9b682f2f25dcb31c83d3743fec`, `NOTE_LEN` 866, `BUDGET` 6, `SOURCE` relayed, `NOTE_HEADING`, `E2_FILE`, `WAIT_STEP` 300, `WINDOW_MAX` 1200); `injected_text()` title and note are equal as strings and as UTF-8 bytes; `inspect.getsource` of `md5`, `frontmatter_and_body`, `note_of`, `injected_text`, `revised_task`, `find_task_file`, `server_params`, `text_of` and `call` is identical in both; both `--dry-run`s print `title md5 849fe21b... ok; note len 866 md5 4cdbcb9b... ok`.
- `--selftest --org P/org` (exit 0) listed root's tools: `apply_org, blueprint_example, create_org, define_service, delegate, feedback, health, hire, inbox, observe, progress, propose_org, read, reclaim, report, request, retire, send, services, start, status, stop, whoami, write` (includes `request`, `start`, `progress`, `status`, `stop`).
- Offline `python3 -B harness/test_poll_loop.py`: 7 passed, 0 failed.
- The full injection (`request`, `start`) was not run: no stream exists. Only `progress` was called against the preflight org.

## 7. Deterministic part at 6618c0d: PASS
HEAD `6618c0d`, freeze diff empty. Details: `deterministic/SUMMARY.md`.
- `uv run pytest -q -p no:cacheprovider tests/e2e/test_org_growth_0a.py tests/e2e/test_org_growth_0a2.py tests/e2e/test_no_bypass_0a2.py`: **78 passed**, 0 failed, 35.27 s, **exit 0**.
- `git -C /Volumes/workspace/hirearchy grep -l e4_replay tests`: `tests/e2e/test_org_growth_0a2.py` and `tests/meta/test_e4_replay_kit.py` (exit 0).
- `uv run pytest -v -p no:cacheprovider tests/e2e/test_org_growth_0a2.py`: **9 passed**, 0 failed, 0 skipped, **exit 0**. The three named replays PASSED: `test_s1r_t5_an_amendment_before_the_verdict_is_refused`, `test_s1r_t8_the_artifact_path_is_withheld_while_the_question_is_open`, `test_s2r_the_wrong_rule_is_refused_and_the_human_rework_needs_a_base`.
- Report only: `uv run pytest -q -p no:cacheprovider tests/meta/test_e4_replay_kit.py`: **11 passed**, 0 failed, **exit 0** (not a condition).
- A first attempt at command 1 was killed by the step's own tool timeout (1.5 s, a ms/s mix-up) before pytest printed anything; the output file was rewritten by the rerun. No pytest process was left.

## 8. Safety snapshot after: PASS
`zsh harness/safety-snapshot.sh preflight-after > preflight-safety-after.txt` (exit 0, 04:01:25 local). `diff preflight-safety-before.txt preflight-safety-after.txt` (`preflight-safety-diff.txt`) shows three differences, all expected:
1. label and date lines;
2. mtime of the directory `~/.kiro/memories` (03:53 to 04:00). `memories.db` md5 is unchanged (`3f53a1d90a590b253fc33aaa1c11342c`); kiro sessions run in this window can touch the directory, so this is recorded, not attributed;
3. mtime of the directory `~/.kiro/agents` (04:00), from the probe profile's creation and deletion (check 9).

Unchanged: all `~/.kiro/settings/*` md5s, the global SKILL.md md5, the file list and md5s of `~/.kiro/agents/*`, `/Users/aminalizadeh/organization` (file count, newest mtime, stat digest), repo `git status`, HEAD, freeze diff, `protocol.md` md5, `/Volumes/workspace/orgs`.

## 9. Ambient probe check (protocol 4.5 / 4.14 item 6): PASS
Probe dir `/tmp/hirearchy-e5-probe-1792810812` (left in place per protocol). Workspace skill copy `b7187d6ef749505893e9aef99276ef7c`, `.kiro/settings/cli.json` `05d30ccbfd35530747c8a542eb67985c`.
- Profile `~/.kiro/agents/hirearchy-study-e5-probe.json`, md5 `041d7f457c454d4df9541a40c1c37e95`, created 03:00:12Z, deleted 03:00:55Z after a byte comparison with the copy in `probe/` (`probe/probe-profile-creation.txt`, `probe/probe-profile-deletion.txt`, `preflight-profiles.txt`). `~/.kiro/agents` afterwards holds exactly the six pre-existing files.
- Call (cwd = probe dir): `kiro-cli chat --v3 --no-interactive --trust-all-tools --effort high --agent hirearchy-study-e5-probe "List the names of the skills ..."`, exit 0. Reply listed: autoresearch, commit-work, hirearchy, reverse-engineer-anything, skill-generation, test-driven-development, workflow-suggest.
- Session: `modelId` `claude-sonnet-5.5`, `effortLevel` `high`, `agentMode` `hirearchy-study-e5-probe`. `ambient_context.py`: `<steering-files>` block present: False; "Workflow Orchestration" text present: False; `<memories>` block present: True (11 global memories shown; covariate, valid either way); `hirearchy` listed. `~/.kiro/settings/cli.json` and `cli.json.lock` md5s unchanged (`probe/global-cli-md5-before.txt`, `-after.txt`).

## Harness facts noticed (recorded; nothing changed, nothing blocks a stream)
- `model_check.sh` labels its output `spreflight` (it prefixes `s` to its `<N>` argument) in the `RESULT:` lines. Cosmetic; the md5-frozen script is untouched.
- `ambient_context.py` lists a spurious memory title `TITLE` (12 titles listed, 11 memories shown). Cosmetic; the script is untouched.
- The org run produced no `.runtime/scheduler.log` file; `scheduler.exit` and the console output carry the scheduler's lines.
- The assistant profile template and `run_turn.sh` were not exercised here (no assistant stream session was started); the probe used the template JSON with the probe name.

## Files and state left behind
- Evidence: `evidence/preflight/`, `evidence/probe/`, `evidence/deterministic/`, `evidence/preflight-safety-{before,after,diff}.txt`, `evidence/preflight-profiles.txt`, this file.
- Still present: `/tmp/hirearchy-e5-probe-1792810812` (probe dir). Removed: `/tmp/hirearchy-e5-preflight-1792810596` and its kiro home and scratch cwd. No `hirearchy-study-e5-*` profile is in `~/.kiro/agents`. No E4 file was changed (`git status --porcelain --ignored -- studies/E4-org-growth-0a1-recheck` is empty).

Result: PASS
