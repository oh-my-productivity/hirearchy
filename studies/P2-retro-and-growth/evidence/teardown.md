# P2 teardown (step 1 of the close, workflow `wf_8ee5197e04b8ee7c`; after R1-v1 (withdrawn), R1 and C1; stage 2 not run)

Facts only. Run 2026-10-29 15:13Z-15:20Z by the `teardown` step (the brief: `docs/research/org-growth/phase-2/p2-stage1-close-brief.md`, Step 1; procedure:
the study brief's step 11 and P1's `teardown.md`). No product code changed; nothing staged, committed or pushed; no stream and no org run; no
credential read; `memories.db` neither restored nor edited; `/Users/aminalizadeh/organization` read with `stat` and `find` only.
Files written: `safety-after.txt` (`harness/safety-snapshot.sh teardown-after`, 15:14:45Z), `teardown-safety-diff.txt` (`diff safety-before.txt
safety-after.txt`), `teardown-deletions.txt` (the directories removed, listed before removal), `teardown-verify.txt` (the read-only checks after the
deletions, 15:18:47Z), this file. Nothing under `EV/` was deleted.

## 0. Gates
| Check | Result |
|---|---|
| md5 gate (`arm.sh` `md5gate_ok`: `protocol.md`, `standing-rules-streams.md`, both amendments, every `harness/MD5SUMS` line) | **PASS**, rc 0, at the start (15:14:13Z) and again at the end (`teardown-verify.txt`) |
| `harness/skill_move.sh recover` (first action) | no unrestored move; global skill in place, md5 `443e1bc4911aa4d6aaa6457e78f673c1` |

## 1. The global skill and the skill moves
| Check | Result |
|---|---|
| `~/.kiro/skills/hirearchy/` | in place, holds exactly `SKILL.md`, md5 **`443e1bc4911aa4d6aaa6457e78f673c1`** (`safety-after.txt`, `teardown-verify.txt`) |
| `harness/skill_move.sh status` | `global skill: in place, md5 443e1bc4...` and `no unrestored move`, rc 0 |
| `skill-moves.txt` | 4 moves, each with an `ASIDE-PENDING`, an `ASIDE` and a `RESTORE` line, md5 `443e1bc4...` checked at every move: `probe-C1` (10:27:07Z-10:28:32Z), `probe-C2` (10:31:25Z-10:32:47Z), `C1` (aside 13:30:32Z, restore 14:27:30Z), `C1` second aside (14:31:29Z, restore 14:41:27Z) |
| C1's two asides | The global copy was in place between 14:27:30Z and 14:31:29Z. `C1/turn-times.txt` has no turn in that gap (turn 22 ended 14:25:58Z, turn 23 started 14:31:54Z). `C1/skill-check.txt` reads `skill proof (arm C): PROVED` and `verdict: OK`. The stream records I read give no reason for the gap; it is not a teardown failure |
| `skill-aside/` (`studies/P2-retro-and-growth/skill-aside/`) | empty |
| Other skills in `~/.kiro/skills/` | `ls` identical to `safety-before.txt` (24 entries) |

## 2. The owner's `~/.kiro` (`teardown-safety-diff.txt`: the full diff; md5 before = `safety-before.txt` 10:13:50Z, after = `safety-after.txt`)
**Unchanged:** the `~/.kiro/agents` file list and every md5 (the seven entries below); `~/.kiro/skills/` (listing and the global skill's md5); the
settings files `cli.json.lock`, `mcp.json.bak`, `mcp.json.bak-rea`, `mcp.json.bak-whatsapp`, `session-response-indexing.json`, `survey_state.json`
(md5 and mtime); the user's org; `/Volumes/workspace/orgs`; the repo's `git status --porcelain`.

**Changed, and not by the study.** Four files differ, and none of the study's harness scripts writes `~/.kiro/settings` or `~/.kiro/memories`.
The study opened no file in either. They are listed as the owner's, with the records the streams kept:

| File | Before | After | When and who |
|---|---|---|---|
| `settings/cli.json` | `8d759079...` | `f2192412...` (`f21924126253d2f829fd25ad189e4825`) | mtime 2026-10-29T12:35:19Z, inside R1's turn 9 call (12:34:30Z-12:39:29Z). The owner's change; the writer is not identified in any record. Record: `stage-1-gate.md` section 7, `C1/harness-failures/empty-calls-and-settings-change.md`, `manager-decision-stage-2.md` (reason 3) |
| `settings/mcp.json` | `767d7d34...` | `9ca5275e...` (`9ca5275ee24dfa57e57c763e717e2387`) | mtime 12:38:08Z, same turn. Same records. Both `R1/safety-after.txt` (13:27Z), `C1/safety-before.txt`, `C1/safety-after.txt` and now hold the new md5s, so no change happened after 12:38Z |
| `settings/workflow_survey_state.json` | `2079174b169f2a98397ed7871e972b03` | `f9e25c32a0322e98da5db1415bd6b839` | mtime 14:44:52Z, 1 minute after C1's finish (14:41Z) and when the `stream-c1` workflow step ended and `stage-gate` began. It is kiro's own bookkeeping (`completedWorkflowCount` 39; the file holds survey counters only). No stream or gate record mentions it; the first snapshot to show it changed is this one |
| `memories/memories.db` | `ba97f447639184d1fb7da9eccf2b2e8c` (151552 bytes, mtime Oct 29 05:13 local) | `42d6e6eb81ad82e594664cc09474e8d8` (163840 bytes, mtime 2026-10-29T15:14:34Z) | The chain below |

Directory mtimes also moved: `~/.kiro/memories` (10:13 to 15:14), `~/.kiro/agents` (Oct 28 04:39 to Oct 29 14:41: the study profiles' creation and
deletion), and the home directory (`..` of the org, line 71 of the diff).

### `memories.db`, every value on record
| md5 | Where recorded | Size, mtime (UTC) | Writer (the owner's own session; the file is never restored or edited) |
|---|---|---|---|
| `ba97f447...` | `safety-before.txt` (10:13Z), `R1-v1/memories-md5-before.txt` and `-after.txt` (unchanged during R1-v1) | 151552, Oct 29 05:13 local | (earlier) |
| `78502051...` | `R1/memories-md5-before.txt` (12:11Z) | 155648, 11:46Z | owner session `sess_ce38cb49-9ca4-48b3-a97e-af15d9e4b9c5` ("Mobile roguelite game build"), `memoryExtractionWatermark` 11:46:06Z. `manager-decision-memories-before-R1.md`, with its correction |
| `6e6d7471...` | `R1/memories-md5-after.txt`, `C1/memories-md5-before.txt` | 159744, 12:31:23Z (during R1's turn 8) | owner session `sess_e1ee9b77-aa4d-46f1-86b8-082887906d28` ("Create Minimal Projects With Jenkinsfiles And Containers"), watermark 12:31:26Z. `manager-decision-row-R1-t9.md` section 2 |
| `ff69d3d5...` | `C1/memories-md5-after.txt`, `C1/memories-db.txt` | 159744, 14:37:03Z (during C1's turn 26) | owner session `sess_ffcc477a-1c2f-4c4e-a7c5-18226c9b7129` (same title; a rewind fork of `sess_e1ee9b77`), watermark 14:37:12.267Z. `C1/harness-failures/memories-db-change-during-C1.md` |
| `42d6e6eb...` | `safety-after.txt` (15:14:45Z), `teardown-verify.txt` | 163840, **15:14:34Z** | new in this step, between C1's end and the teardown: the same owner session `sess_ffcc477a`, which wrote a `memoryExtractionWatermark` at 15:14:39.997Z, 5.4 s after the mtime. It is the only session outside this workflow with a watermark within 10 s. Its `session.json` carries no workflow meta (title "Create Minimal Projects With Jenkinsfiles And Containers", status idle). The study's own sessions wrote watermarks at 14:41:52Z-14:45:30Z (`stream-c1`, `stage-gate`) and from 15:14:54Z (this `teardown` step, `sess_e14cef0d`); none is within 10 s of 15:14:34Z |

The standing ruling of `manager-decision-row-R1-t9.md` section 2 would make this change a record and not a stop: (a) one outside session with a
watermark within 10 s, (b) not a workflow step of this run, (c) the contamination check applies to a next stream's `<memories>` block, and no stream
follows. Limits of the evidence: the file shows only its last write, so I cannot exclude an earlier write between 14:41Z (C1's end) and 15:14:34Z; the
owner session's watermark times above are the only owner activity on record in that window. `memories.db` is still the only entry in `~/.kiro/memories`. Neither R1 nor C1 is affected: each assistant read its `<memories>` block once, at session start, and checked it
clean after turn 1 (`R1/memories-block-check.txt`, `C1/memories-block-check.txt`).

### Other state the owner's sessions changed (theirs, for the report)
- **The owner's workflow during C1:** `wf_531166aa9507942e` ("game-vertex-mobile-roguelite", step `m2-code`, session `sess_ab0fe2e0`, owned by the owner's
  session `sess_ce38cb49`), per `manager-decision-stage-2.md` ("Records for step 12") and `C1/harness-failures/memories-db-change-during-C1.md`. It is
  still running at this step (its `run.beat` was written between 15:10Z and 15:20Z). No record shows it touched C1.
- **The owner's `~/.kiro/sessions/` folders** keep growing with their own sessions; the study only reads them.

## 3. `~/.kiro/agents`: back to its original entries; every study profile deleted, each with a record
`ls ~/.kiro/agents` holds exactly the seven entries of `safety-before.txt`, with identical md5s (`diff` empty; `teardown-verify.txt`):
`agent_config.json.example` `469663a5...`, `claude-opus-5.5.json` `4067177e...`, `claude-sonnet-5.5.json` `dc760943...`, `evolve.json` `064b1e0c...`,
`explainer.json` `3d471c90...`, `hirearchy-organization-9d66c1-web-fetch-web-search.json` `51adddec...`, `telegram_bot.json` `a8b6eef2...`.
`ls ~/.kiro/agents | grep -c -E 'study|p2'` = **0**. None was present at the start of this step, so this step deleted none. Each was deleted by its own step:

| Profile | Created | Deleted | Record |
|---|---|---|---|
| four probe profiles (`hirearchy-study-p2-probe-{C1,R1,C2,R2}-assistant`, first created 10:27:07Z) | preflight | preflight (first deleted 10:28:32Z; all before the 10:34Z `preflight-safety-after.txt`) | `probe/profiles-creations.txt`, `probe/profiles-deletions.txt` (four created, four deleted); `preflight.md` |
| `hirearchy-study-p2-R1-assistant.json` (R1-v1) md5 `016027a3...` | R1-v1 setup | 2026-10-29T11:03:21Z | `R1-v1/profiles/deletions.txt` |
| `hirearchy-study-p2-R1-assistant.json` (R1) md5 `0e8e3fb9dc06b8dfa1cefe4056b628ca` | 12:11:08Z | 13:27:29Z | `R1/profiles/creations.txt`, `R1/profiles/deletions.txt` |
| `hirearchy-study-p2-C1-assistant.json` md5 `d0f09b517e35a12d409fa7292b81610f` | 13:30:33Z | 14:41:25Z | `C1/profiles/creations.txt`, `C1/profiles/deletions.txt` |

The org seats' scheduler profiles are not in `~/.kiro/agents`; they live in the org kiro homes (section 6) and are copied under `<stream>/profiles/org-kiro-home--*.json`.

## 4. The user's organization `/Users/aminalizadeh/organization`: untouched
Read-only `stat`/`find` checks (`safety-snapshot.sh`; no file opened, no `git` command run in it): listing identical (same 10 entries, mtimes Oct 24 15:38);
**31 files**, newest mtime `1792852894` (`.runtime/events/2026-10-24/cli-82016-1792852894630.jsonl`), tree digest **`7ba5d9206b4c800d27a2f2d195137764`**, identical to
`safety-before.txt`, `preflight-safety-after.txt`, and `teardown-verify.txt` (15:18:47Z). Only the directory entry `..` (the home directory) has a new mtime (Oct 29 15:13).
`/Volumes/workspace/orgs`: listing identical.

## 5. The freeze and the arm-C worktree (`teardown-verify.txt`)
| Check | Result |
|---|---|
| `git -C /Volumes/workspace/hirearchy diff --stat 3d6b28aa HEAD -- src skills pyproject.toml uv.lock` | **empty** (0 bytes); HEAD `3d6b28aa17a70a3f95854c73c2f479b6361a71de`, branch `main` |
| `git -C /Volumes/workspace/hirearchy/.worktrees/p2-arm-c` HEAD | **`aac6af1b47b721515106f03f1dd6eb6758da6e55`**, `status --porcelain` empty (0 lines); `freeze_ok` rc 0 |
| `git status --porcelain` of the repo | ` M docs/design/org-growth-phase-2.md` (the one 18.6 line, for the commit step), `?? docs/research/`, `?? studies/P2-retro-and-growth/`; nothing staged |
| The arm-C worktree | **left in place** (`git worktree list`); the manager removes it |

## 6. Sandboxes removed from `/tmp/hirearchy-p2/`
Before removing, I checked what the three stream sandboxes held against the evidence (byte comparison by md5, against everything under `EV/<stream>/`):
- **R1** (`R1-1793275867`), **C1** (`C1-1793280632`), **R1-v1** (`R1-1793270268`): every file in `notes/`, `deliverables/`, `injection/` and `org/` (outside `.runtime/`)
  has a byte-identical copy in the stream's evidence, `notes/` is identical to `EV/notes/`, and the `org/.git` history is in `org-git.bundle`.
- **Not in the evidence copy:** 39 (R1), 40 (C1) and 15 (R1-v1) `org/.runtime/events/2026-10-29/cli-<pid>-<epoch>.jsonl` files. Their times are 13:27:12Z-13:27:23Z,
  14:41:12Z-14:41:24Z and 11:03:16Z-11:03:19Z, that is, after each stream's `end.txt` time (13:27:10Z, 14:41:11Z, 11:03:15Z): the event logs of the finish step's own CLI calls, written after
  `copy_org_evidence.sh` ran. Also not copied: the sandbox's `.kiro/settings/cli.json` (the harness's `workspace-cli.json`) and `.kiro/skills/hirearchy/SKILL.md`
  (md5 `443e1bc4...` in R1 and R1-v1, `b1023863...` in C1: the pinned arm skills). The readers take the sandbox only as a name pattern from `sandbox-path.txt` (or run
  in no-sandbox mode), so the score step does not need it.
- No process referred to any P2 path (`ps` count 0).

**Removed: all 142 subdirectories of `/tmp/hirearchy-p2/`** (80196 files, about 350 MB; `teardown-deletions.txt` gives the file count and size of each, listed before removal). By group:
- **Stream sandboxes (3):** `R1-1793270268` (R1-v1, withdrawn), `R1-1793275867` (R1), `C1-1793280632` (C1).
- **Preflight (6):** `preflight-C-1793268897`, `preflight-R-1793268869`, `preflight-sched-C-1793269282`, `preflight-sched-C-1793269583`, `preflight-sched-R-1793269133`, `preflight-sched-R-1793269552`.
- **Probe sandboxes (72):** `probe-C1-*` (18), `probe-C2-*` (18), `probe-R1-*` (18), `probe-R2-*` (18); the epochs run 1793251895-1793275661.
- **Self-check sandboxes (48):** `selfcheck-C-*` (19), `selfcheck-R-*` (22), and `selfcheck-amend1`, `selfcheck-gate`, `selfcheck-gate-p1`, `selfcheck-home`, `selfcheck-probe`, `selfcheck-traps`, `selfcheck-wrapper`.
- **Other study scratch directories (13):** `explore-R-1793254342`, `pf0test-1793258151`, `dbg`, `retro-scratch`, `skill-aside` (a self-check leftover, `selfcheck-C3-1793275654`), `review-a1`,
  `amend1-orig`, `amend1-r1v1-check`, `amend1-red`, `rulings-cases`, `rulings-green`, `rulings-orig`, `rulings-red`. (3 + 6 + 72 + 48 + 13 = 142.)
- The exact name, file count and size of each of the 142 directories is in `teardown-deletions.txt`. `rm -r` ran on each directory by its exact name (no symlink was followed; none of the 198 symlinks inside
  pointed outside `/tmp/hirearchy-p2/` or `EV/`). 142 removed, 0 failures.

**Left in `/tmp/hirearchy-p2/`:** the directory itself and 65 loose files. They are not sandboxes, so I did not delete them; the manager may `rm` them: `am-new.md`, `amend1-selfcheck-run*.txt`,
`dr-test.out`, `dryrun-R.out`, `explore-last.txt`, `extract_head.py`, `pf0test-last.txt`, `r1-*.console.txt` (9), `r1-t7-assistant.txt`, `r1b-*.console.txt` (30), `r1b-memblock.txt`,
`rulings-*.out`/`.md`/`.txt`, `sec12.md`, `sec126.md`, `sec13.py`, `sec16.py`, `selfcheck-run*.{out,log}`, `selfcheck-skill-moves.txt`, `sra-d.md`, `sra-new.md`, `table_edit.py`.
A byte comparison shows `extract_head.py` (empty), `r1-t7-assistant.txt`, `r1b-memblock.txt` and three `rulings-*.out` are duplicated in the evidence; the rest are working files (console logs, drafts) that are not.

**Left, recorded, not deleted (outside `/tmp/hirearchy-p2/`, so outside this step's list):** the org kiro homes under
`~/Library/Application Support/hirearchy/kiro-home/`: `c1-1793280632-org-63c63f610bbc48b8`, `r1-1793275867-org-6d44e4ecb77bfda2`, `r1-1793270268-org-89c67acfa4521081`,
`preflight-c-1793268897-o-b45b48f53c484252`, `preflight-r-1793268869-o-49bd889e729113b6`, `preflight-sched-c-179326-0f9bd689464f3a0f`, `preflight-sched-r-179326-dd6b48b14cc9049a`
(P1 deleted its own after a verified copy). The copy check for the three stream homes: every file under `sessions/` is byte-identical to `<stream>/org-kiro-sessions/` (R1-v1 27 files, R1 104, C1 102) except
two kiro `.index/.lock` files each (kiro's own lock files, as in P1). Their `agents/` profiles are copied under `<stream>/profiles/`. The matching dirs in `.../hirearchy/kiro-cwd/` are also left. Whether to delete them is the manager's call.

## 7. Result
All teardown checks pass (md5 gate, skill in place with no open move, `~/.kiro/agents` original, org untouched, freeze and arm-C worktree, sandboxes removed). The owner's `~/.kiro` shows four files changed by
the owner's own state (`cli.json`, `mcp.json`, `workflow_survey_state.json`, `memories.db`), recorded above and not attributed to the study, and not restored or edited.
No check failed, so there is no stop warning.
