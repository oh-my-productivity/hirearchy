# E5 harness: changes against E4

Written by the E5 pre-registration step on 2026-10-24, before any E5 sandbox, profile, session or stream existed. Source: the E4 study's
`studies/E4-org-growth-0a1-recheck/evidence/harness/` (committed in `3815813`; `git status` shows no change there, and this step edited no E4
file). Every file below was copied with `cp -p` and then changed only as listed. The md5 of every file in this folder is in `MD5SUMS`
(this file included, `MD5SUMS` itself excluded). `protocol.md` section 7.1 binds these md5s.

## Files

| E4 file | E4 md5 | E5 file | E5 md5 | |
|---|---|---|---|---|
| `run_turn.sh` | `ea99077dd1b58e192bbdcd4ca5734e87` | `run_turn.sh` | `8df3e434558e1bcdb5fecef344e4e45a` | changed |
| `inject_root_rework.py` | `c80e25d65fe58cdb97d7faa758d59484` | `inject_root_rework.py` | `1c4e7824e448a3a34e24a7b759a59fcd` | changed |
| `ambient_context.py` | `c40d05929771b0fcbc7f0491df79d195` | `ambient_context.py` | `c40d05929771b0fcbc7f0491df79d195` | identical |
| `model_check.sh` | `07ffec85c836e77735fd43050de25858` | `model_check.sh` | `c403fd661cf19c28776264cd2a0ab14e` | changed |
| `extract_mechanical.py` | `ec2d7db51fd06233f182c0153ecd6957` | `extract_mechanical.py` | `9b1187b2152da68436170ed0d4a2ec9b` | changed |
| `extract_mechanical_s2.py` | `bbb2d83520f3a7537f447c0f817ff3e2` | `extract_mechanical_s2.py` | `6a1f0a6e98111a682ba07d5fbf6556d1` | changed |
| `extract_mechanical_s3.py` | `b88031528b72cc6915228ad9302ce309` | `extract_mechanical_s3.py` | `13e07bfd8f60d10ece309b11d86efafb` | changed |
| `extract_proposals.py` | `41f317d85f10cd0da284dc10398dd138` | `extract_proposals.py` | `41f317d85f10cd0da284dc10398dd138` | identical |
| `extract_tool_calls.py` | `da57d91e9beea0f1947ffb126ea92c88` | `extract_tool_calls.py` | `da57d91e9beea0f1947ffb126ea92c88` | identical |
| `copy_org_evidence.sh` | `be61b6ad98f15776af6e76b9342083a4` | `copy_org_evidence.sh` | `6b5db4255cce0f457728d92ae0c17248` | changed |
| `safety-snapshot.sh` | `b1b27416553adf746912108ac6829f35` | `safety-snapshot.sh` | `dbaae0f538fc807cb94cd3241da8cfcf` | changed |
| `org_state.py` | `11668031afb4ae29725affd2447de260` | `org_state.py` | `84dda2e11d1b16a93fe5cb853517aba3` | changed |
| `workspace-cli.json` | `05d30ccbfd35530747c8a542eb67985c` | `workspace-cli.json` | `05d30ccbfd35530747c8a542eb67985c` | identical |
| `hirearchy-study-e4-prep-1792639838.json.deleted-by-manager` | `0f711c96814a3d67a51609f02f111605` | `profile-template.json` | `13871b86430cf636feb1b56021b7cd14` | changed |
| (new) | | `test_poll_loop.py` | `0b269d00bcd8ce4e7c4498e270960c30` | new: offline check of change (a) |

Not copied:
- `staging/`: E4's pre-probe candidate settings file (three keys) and a copy of the old skill (md5 `573495bb...`). E5's settings file is
  `workspace-cli.json` (unchanged, the probe's outcome in E4), and each stream copies the skill from the repo at `6618c0d` (md5
  `b7187d6ef749505893e9aef99276ef7c`).
- `workspace-cli.json.md5`: `MD5SUMS` covers `workspace-cli.json` (`05d30ccbfd35530747c8a542eb67985c`, as in E4).
- E4's `hirearchy-study-e4-prep-1792639838.json.deleted-by-manager` is copied as `profile-template.json` (change c).

## (a) F-E4-9: the injection script waits between polls (`inject_root_rework.py`)

What was wrong (E4 STUDY F-E4-9, manager ruling `manager-decision-s2-and-h3.md` F-E4-harness-1): step 4 of protocol 5.3 called
`progress(task_id, wait_seconds=300)` in a loop with no pause. When the server returns at once ("Not waiting: nothing can progress without
you", or a done task while the scheduler is still exiting), the loop re-polled without delay: 36,513 calls in s2, about 700 in s2r and
about 490 in s3.

The fix:
- The loop is now the function `poll_until_settled(progress, task_id, window_start, log, window, clock, sleep)`. Its calls are those of
  E4: `progress({"task_id": <id>, "wait_seconds": min(300, time left)})` with a read timeout of `wait + 180` s. The end condition is
  E4's, moved into `settled()` unchanged: the task's line shows done, failed or blocked, and the reply shows `scheduler: stopped`.
- A reply that came back in less than `QUICK_REPLY` = 5 s did not wait. The loop then pauses before the next poll: 5 s after the first
  quick reply, doubling for each further quick reply in a row up to 60 s, never past the window. A reply that waited resets the pause.
- Bounds: the window is still 20 minutes from the request (`WINDOW_MAX`), plus a hard cap of `MAX_POLLS` = 300 polls. With the pauses, a
  20-minute window allows at most 241 polls; the s2 state now gives 23.
- Every poll is logged (`poll k: reply after X s ...`), and the end is logged with the poll count:
  `polling ended (<why>): progress(task_id) polls N, quick replies Q, paused P s in all`. E4's line `window cap: 20 minutes passed` is kept.
- New mode `--poll-check --task <id> [--max-seconds N]` (default 120) for the preflight (protocol 4.14). It starts the same root-bound
  server and runs only the polling loop, so it calls `progress(task_id=..., wait_seconds=...)` and nothing else, and it logs to
  `<out>/poll-check-log.txt`. It never calls `request` or `start` and writes nothing into the org.
- `Log` takes an optional file name (default `injection-log.txt`, as in E4) for that mode.
- Unchanged: the modes `--dry-run`, `--selftest`, `--stop` and the injection itself; the call order `progress()`, `request(...)`,
  `start()`, the polling loop, `progress()`, `status()`; the arguments; the precondition and `--force`; the marker; the exit codes; the
  never-called tools.

**The injected text is byte-for-byte E2's/E4's (E4 protocol 5.1).** The script still reads the title and the note from E2's file at run
time and asserts their md5s before it sends anything. Proof, run by this step:

1. Diff of the text constants and the text functions (`REPO`, `E2_FILE`, `TITLE_MD5`, `NOTE_MD5`, `NOTE_LEN`, `BUDGET`, `SOURCE`,
   `NOTE_HEADING`, and `md5`, `frontmatter_and_body`, `note_of`, `injected_text`), extracted from both scripts: **no difference** (31
   lines each).
2. Values, from importing both scripts:

| Constant | E4 | E5 | |
|---|---|---|---|
| `REPO` | `/Volumes/workspace/hirearchy` | `/Volumes/workspace/hirearchy` | same |
| `E2_FILE` | `/Volumes/workspace/hirearchy/studies/E2-service-reflection-regression/evidence/msgs/root-sent/20261018T035429740646-root-d90e.md` | `/Volumes/workspace/hirearchy/studies/E2-service-reflection-regression/evidence/msgs/root-sent/20261018T035429740646-root-d90e.md` | same |
| `TITLE_MD5` | `849fe21b104be883af9b3c06367d4445` | `849fe21b104be883af9b3c06367d4445` | same |
| `NOTE_MD5` | `4cdbcb9b682f2f25dcb31c83d3743fec` | `4cdbcb9b682f2f25dcb31c83d3743fec` | same |
| `NOTE_LEN` | `866` | `866` | same |
| `BUDGET` | `6` | `6` | same |
| `SOURCE` | `relayed` | `relayed` | same |
| `NOTE_HEADING` | `## Note from the requester` | `## Note from the requester` | same |
| `WAIT_STEP` | `300` | `300` | same |
| `WINDOW_MAX` | `1200` | `1200` | same |

   Source of these functions identical in both scripts: `md5` yes, `frontmatter_and_body` yes, `note_of` yes, `injected_text` yes, `revised_task` yes, `find_task_file` yes, `server_params` yes, `text_of` yes, `call` yes.
3. `injected_text()` of both scripts, compared byte for byte: title identical **True**, note identical **True**. Title md5
   `849fe21b104be883af9b3c06367d4445`, note 866 characters, md5 `4cdbcb9b682f2f25dcb31c83d3743fec` (E4 protocol 5.1:
   `849fe21b104be883af9b3c06367d4445`; 866 characters, `4cdbcb9b682f2f25dcb31c83d3743fec`).
4. `--dry-run` of both scripts (no server, no org): both print
   `title md5 849fe21b104be883af9b3c06367d4445 ok; note len 866 md5 4cdbcb9b682f2f25dcb31c83d3743fec ok`.

**Offline exercise of the fixed loop** (`test_poll_loop.py`; no server, no org, no sandbox, no model call: `progress` is a stub, and the
clock and the sleep are fakes): `python3 -B test_poll_loop.py`:

```
PASS test_a_server_that_waits_is_not_paused
PASS test_s2_state_progress_returns_at_once_and_nothing_moves
PASS test_s3_state_done_while_the_scheduler_still_runs_then_stops
PASS test_settled_on_the_first_poll
PASS test_the_pause_resets_after_a_reply_that_waited
PASS test_the_poll_cap_bounds_the_calls
PASS test_the_poll_check_window
7 passed, 0 failed
```

- The s2 state (every reply at once, nothing moves): 23 polls in the 20-minute window, gaps 5, 10, 20, 40, then 60 s; E4 made 36,513.
- The s3 state (task done, scheduler exits 7 s later): 3 polls; E4 made about 490.
- A server that waits: 4 polls of 300 s, no pause.
- The live check against a real server is left to the preflight (protocol 4.14, `--poll-check`), because it needs an org and this step
  creates none.

## (b) `run_turn.sh`: `--effort high` on every assistant call, and the invocation is recorded

- Every assistant call is now `kiro-cli chat --v3 --no-interactive --trust-all-tools [--resume] --effort high --agent
  hirearchy-study-e5-s<N>-assistant "<Lena's line>"` (D-E4-9: the harness sets the assistant's effort). The model comes from the profile
  (change c); there is no `--model` flag, as in E4.
- The argv is built as a zsh array and run as `"${CMD[@]}"`; an empty `$RESUME` drops out, as in E4. The exact argv (shell-quoted,
  `${(q-)CMD[@]}`) is written to `turn-NN.cmd.txt` before the call, so `model_check.sh assistant` can check the invocation.
  `turn-NN.txt`, `turn-NN.raw.txt`, `turn-NN.stderr.txt`, `turn-NN.prompt.txt` and `turn-times.txt` keep E4's format exactly.
- Checked offline: the argv has 10 words without `--resume` and 11 with it, and Lena's line, with quotes in it, survives the quoting
  round trip. `kiro-cli` was not run.

## (c) `profile-template.json`: the assistant's study profile, `"model": "claude-sonnet-5.5"`

- Made from E4's profile template (the prep profile copy). It holds E4 protocol 4.2's JSON with E5's names: `name`
  `hirearchy-study-e5-s<N>-assistant`, its description, and `ORG_ROOT` `/tmp/hirearchy-e5-s<N>-<epoch>/org`. `"model": "claude-sonnet-5.5"`
  is kept (it was already E4's value). The MCP server, `tools`, `permissions`, both skill resources, `hooks` and `includeMcpJson` are
  unchanged.
- Substitution: `<N>` = the stream label (`1`, `2`, `3`, `1r`, ...), `<epoch>` = the sandbox's epoch. The probe profile of protocol 4.5
  is the same JSON with `name` `hirearchy-study-e5-probe`, description `internal: hirearchy usability study E5 probe; deleted after the
  probe` and `ORG_ROOT` `/tmp/hirearchy-e5-probe-<epoch>/org`. The JSON parses, before and after substitution.

## (d) `model_check.sh`: a check of the seats, not a ping

- E4's `model_check.sh` (md5 `07ffec85...`, written for E4 s3) pinged claude-sonnet-4.6 and claude-haiku-4.5 through a prep profile with
  retries. E5 replaces its body. The file keeps its name and its role: the stream's model record, `s<N>/model-checks.txt`.
- Modes (all read-only; each appends a block to `s<N>/model-checks.txt` and prints its `RESULT:` line):
  - `listed <N>`: `kiro-cli chat --list-models` lists `claude-sonnet-5.5` (protocol 4.3: no substitution; exit 1 means the stream does
    not start).
  - `org <N> <S>`: every org run log under `S/org` has exactly one `# cmd:` line, with exactly one `--model claude-sonnet-5.5` and exactly
    one `--effort high`. A log with no `# cmd:` line (a run that never started a model) is listed and is not a seat.
  - `assistant <N> <S>`: the stream's profile (in `~/.kiro/agents`, else the copy in `s<N>/profiles/`) has `"model": "claude-sonnet-5.5"`;
    every `turn-NN.cmd.txt` has `--effort high` once, the stream's `--agent`, and no `--model` other than claude-sonnet-5.5; the session
    copy `s<N>/assistant-session.json` has `modelId` claude-sonnet-5.5 and `effortLevel` high, or none recorded; every `reasoningModelId`
    in `s<N>/assistant-session-messages.jsonl` is `claude-sonnet-5.5` (E4's store writes `qdev::claude-sonnet-5.5`).
  - `all <N> <S>`: org, then assistant.
  - `<N>` = `preflight` writes to `evidence/preflight/model-checks.txt` instead of `s<N>/` (protocol 4.14, the preflight's scratch org).
- Exit 0: every seat checked is in the set. Exit 1: a seat outside the set, reported as `OUTSIDE THE SET: ...` and `RESULT: ...
  INVALIDATING (H4: a seat outside the set)`; for `listed`, `NOT LISTED`. Exit 2: usage error, or nothing to check yet (`INCOMPLETE`,
  never a pass).
- Exercised offline by this step in a scratch folder `evidence/sprereg-selftest/`, deleted afterwards. A stub `kiro-cli` printed E4's
  `models.txt`, and the org check read E4's s3 sandbox (read only):
  - `listed`: OK (claude-sonnet-5.5 is listed).
  - `org` on `/tmp/hirearchy-e4-s3-1792705005`: 46 logs checked, every one `OUTSIDE THE SET` (claude-sonnet-4.6 or claude-haiku-4.5, no
    `--effort`), so the result is INVALIDATING, as expected for E4.
  - `assistant` with E4 s3's session copy and two made-up command files: the one with `--effort high` passed, the one without it was
    flagged; `modelId` claude-sonnet-5.5, `effortLevel` not recorded, `reasoningModelId` `qdev::claude-sonnet-5.5` x30 passed.
  - `org` with no org: INCOMPLETE, exit 2. Missing `<S>`: usage, exit 2.

## (e) E4 paths and labels renamed, nothing else

- `run_turn.sh`: the evidence path `E4-org-growth-0a1-recheck` becomes `E5-org-growth-0a2-recheck`, the profile `hirearchy-study-e4-s$N-assistant`
  becomes `hirearchy-study-e5-s$N-assistant`, and the header label (with change b).
- `copy_org_evidence.sh`: label and evidence path.
- `safety-snapshot.sh`: label; `PROTO` = E5's `protocol.md`; "generated by E5"; the informational diff `d85cc13` (E4's product commit)
  becomes `6618c0d` (E5's).
- `org_state.py`: label only.
- `extract_mechanical.py`, `extract_mechanical_s2.py`, `extract_mechanical_s3.py`: label; `EV`; the regex `(?!-e4)` becomes `(?!-e5)`; the
  sandbox regex `/tmp/hirearchy-e4-s\w+-\d+/org/` becomes `/tmp/hirearchy-e5-s\w+-\d+/org/`. Not changed, and to be adapted per stream
  under protocol 7.1: the service folder (`weekly-memo` in `extract_mechanical.py`, `weekly-meeting-memo` in `_s2`/`_s3`) and the
  final-check seat's message glob (`*checker*` in `extract_mechanical.py`, `*reviewer*` in `_s2`/`_s3`). E4 made the same per-stream
  copies.
- Unchanged: `ambient_context.py`, `extract_proposals.py`, `extract_tool_calls.py` and `workspace-cli.json` (byte-identical to E4).

## Syntax checks (this step)

| File | `bash -n` | `zsh -n` | `python3 -m py_compile` |
|---|---|---|---|
| `run_turn.sh` | ok | ok | |
| `model_check.sh` | ok | ok | |
| `copy_org_evidence.sh` | syntax error at line 42, `(N)` | ok | |
| `safety-snapshot.sh` | syntax error at line 12, `(.N)` | ok | |
| every `.py` file (9) | | | ok |
| `workspace-cli.json`, `profile-template.json` | | | parse as JSON: ok |

`copy_org_evidence.sh` and `safety-snapshot.sh` are zsh scripts (`#!/bin/zsh`) that use zsh glob qualifiers, which bash cannot parse.
E4's originals give the same `bash -n` errors at the same lines, and the E5 changes to them are comment and path edits only. `zsh -n`
is the check for their interpreter, and it passes. The `__pycache__/` made by `py_compile` was deleted.

## Side effects of this step's checks (recorded, all undone)

- Importing E4's `inject_root_rework.py` for the text-identity proof made Python write
  `studies/E4-org-growth-0a1-recheck/evidence/harness/__pycache__/inject_root_rework.cpython-311.pyc` (git-ignored) at 03:16 local. This step
  deleted that file and the folder. No E4 file was changed (`git status --porcelain --ignored -- studies/E4-org-growth-0a1-recheck` is
  empty), and E4's harness md5s in the table above are E4's recorded values (`c80e25d6...`, `07ffec85...`, `ec2d7db5...`, `05d30ccb...`).
- The constants diff of the proof used two scratch text files, `/tmp/e5-prereg-text-e4.txt` and `/tmp/e5-prereg-text-e5.txt`. They were
  deleted in the same command. They were not sandboxes, and no org, profile or session was made.
- The `model_check.sh` exercise used `evidence/sprereg-selftest/` and a stub `harness/.stub-bin/kiro-cli`. Both were deleted.

## Diffs (E4 -> E5, `diff -u`)

### `run_turn.sh`

```diff
--- E4-org-growth-0a1-recheck/evidence/harness/run_turn.sh	2026-10-22 04:42:07
+++ E5-org-growth-0a2-recheck/evidence/harness/run_turn.sh	2026-10-24 03:16:16
@@ -1,10 +1,11 @@
 #!/bin/zsh
-# E4 per-turn driver. Usage: run_turn.sh <S> <stream N> <turn number> <prompt file>
+# E5 per-turn driver. Usage: run_turn.sh <S> <stream N> <turn number> <prompt file>
 # Sends the prompt file's text verbatim as Lena's line. Turn 1 = new session; turns >= 2 add --resume. cwd = S.
-# Writes into <evidence>/s<N>/: turn-NN.prompt.txt (copy), turn-NN.txt (header + prompt + stdout, ANSI stripped),
-# turn-NN.raw.txt (raw stdout), turn-NN.stderr.txt, and appends a line to turn-times.txt. No MCP/CLI call against the org.
+# Every call carries --effort high (protocol 4.2, 4.3). The exact argv is written to turn-NN.cmd.txt (model_check.sh reads it).
+# Writes into <evidence>/s<N>/: turn-NN.prompt.txt (copy), turn-NN.cmd.txt (argv), turn-NN.txt (header + prompt + stdout, ANSI
+# stripped), turn-NN.raw.txt (raw stdout), turn-NN.stderr.txt, and appends a line to turn-times.txt. No MCP/CLI call against the org.
 S="$1"; N="$2"; T="$3"; PF="$4"
-EV=/Volumes/workspace/hirearchy/studies/E4-org-growth-0a1-recheck/evidence/s$N
+EV=/Volumes/workspace/hirearchy/studies/E5-org-growth-0a2-recheck/evidence/s$N
 NN=$(printf '%02d' "$T")
 mkdir -p "$EV"
 cp "$PF" "$EV/turn-$NN.prompt.txt"
@@ -12,8 +13,10 @@
 RESUME=""
 [[ "$T" -ge 2 ]] && RESUME="--resume"
 cd "$S" || exit 90
+CMD=(kiro-cli chat --v3 --no-interactive --trust-all-tools $RESUME --effort high --agent hirearchy-study-e5-s$N-assistant "$PROMPT")
+print -r -- "${(q-)CMD[@]}" > "$EV/turn-$NN.cmd.txt"
 start=$(date +%s); startl=$(date +%H:%M:%S); startu=$(date -u +%FT%TZ)
-kiro-cli chat --v3 --no-interactive --trust-all-tools $RESUME --agent hirearchy-study-e4-s$N-assistant "$PROMPT" > "$EV/turn-$NN.raw.txt" 2> "$EV/turn-$NN.stderr.txt"
+"${CMD[@]}" > "$EV/turn-$NN.raw.txt" 2> "$EV/turn-$NN.stderr.txt"
 rc=$?
 end=$(date +%s); endl=$(date +%H:%M:%S); endu=$(date -u +%FT%TZ)
 {
```

### `inject_root_rework.py`

```diff
--- E4-org-growth-0a1-recheck/evidence/harness/inject_root_rework.py	2026-10-22 04:34:11
+++ E5-org-growth-0a2-recheck/evidence/harness/inject_root_rework.py	2026-10-24 03:15:00
@@ -1,17 +1,23 @@
 #!/usr/bin/env python3
-"""E4 clause-1 trigger: the facilitator's injected wrong rework of memo 1 (protocol.md section 5).
+"""E5 clause-1 trigger: the facilitator's injected wrong rework of memo 1 (protocol.md section 5).
 
 Run with:  uv --directory /Volumes/workspace/hirearchy run python <this file> --org S/org --revises <memo-1 task id> --out S/injection
 Other modes:
   --dry-run    verify the text md5s, parse the revised task, print the request arguments; no server, no org write
   --selftest   start the server (root binding), initialize and list tools only; makes no tool call
   --stop       stream end only (protocol 4.8): call stop() once; nothing else
+  --poll-check preflight only (protocol 4.14): run the step-4 polling loop alone, progress(task_id=--task, wait_seconds) and nothing
+               else, for at most --max-seconds; log to <out>/poll-check-log.txt; no request, no start, no org write
 
 It is an MCP stdio client of the SAME server command the assistant profile uses (`uv --directory <repo> run hirearchy mcp`,
 ORG_ROOT=<org>; ORG_AGENT and ORG_REQUIRE_AGENT removed, so the server binds as root). No LLM is involved.
 Exactly these calls, in this order: progress(); request(...); start(); progress(task_id, wait_seconds=300) repeated; progress(); status().
 It never calls inbox, feedback, define_service, send, delegate, reclaim, services, whoami (stop only with --stop).
 The title and note are read at run time from E2's sent file and their md5s are asserted before anything is sent.
+F-E4-9 fix (E5): progress(task_id, wait_seconds) returns at once when nothing can progress ("Not waiting: ..."), and E4's loop then
+re-polled without delay (36,513 calls in s2). The loop now pauses after every reply that came back without waiting (5 s, doubling up
+to 60 s; reset after a reply that waited), stops at 20 minutes from the request as before or after MAX_POLLS polls, and logs every
+poll and the poll count. The calls, their arguments and the end condition are unchanged.
 Exit codes: 0 done; 2 text/identity assertion or argument error (nothing sent); 3 precondition not met (scheduler running; nothing sent,
 rerun with --force after the facilitator's wait); 4 refused or failed request (nothing recorded); 5 failure after the request was sent.
 """
@@ -37,6 +43,11 @@
 NOTE_HEADING = "## Note from the requester"
 WAIT_STEP = 300          # seconds per progress() wait
 WINDOW_MAX = 20 * 60     # seconds from the request
+# F-E4-9 fix (E5): pacing of the step-4 loop when progress(wait_seconds) does not wait.
+QUICK_REPLY = 5.0        # a progress reply faster than this (seconds) did not wait
+PAUSE_START = 5.0        # the pause after the first quick reply (seconds)
+PAUSE_MAX = 60.0         # the pause doubles after each further quick reply in a row, up to this
+MAX_POLLS = 300          # hard bound on progress(task_id) polls per window (with the pauses, 20 minutes allow at most 241)
 
 
 def md5(text: str) -> str:
@@ -94,9 +105,9 @@
 
 
 class Log:
-    def __init__(self, out: Path) -> None:
+    def __init__(self, out: Path, name: str = "injection-log.txt") -> None:
         out.mkdir(parents=True, exist_ok=True)
-        self.path = out / "injection-log.txt"
+        self.path = out / name
 
     def write(self, text: str) -> None:
         with self.path.open("a", encoding="utf-8") as f:
@@ -131,6 +142,61 @@
     return reply
 
 
+def settled(reply: str, task_id: str) -> bool:
+    """The end condition of protocol 5.3 step 4 (unchanged from E4): the task's line shows done, failed or blocked, and the reply
+    shows the scheduler stopped."""
+    line = next((ln for ln in reply.splitlines() if f"(task {task_id})" in ln), "")
+    return bool(re.search(r"\]?: (done|failed|blocked)\b", line)) and "scheduler: stopped" in reply
+
+
+async def poll_until_settled(progress, task_id: str, window_start: float, log: Log, window: float = WINDOW_MAX,
+                             clock=time.monotonic, sleep=None) -> dict:
+    """Protocol 5.3 step 4: progress(task_id=..., wait_seconds=min(300, time left)) repeated until settled(), until `window` seconds
+    after `window_start`, or MAX_POLLS polls. `progress(args, timeout)` makes and logs one call and returns its reply.
+    F-E4-9: a reply that came back in less than QUICK_REPLY seconds did not wait, so the loop pauses before the next poll
+    (PAUSE_START, doubling per quick reply in a row up to PAUSE_MAX, never past the window); a reply that waited resets the pause.
+    `clock` and `sleep` are injectable so the loop can be exercised offline with a stub (harness/test_poll_loop.py)."""
+    if sleep is None:
+        import anyio
+        sleep = anyio.sleep
+    polls = quick = 0
+    paused = 0.0
+    pause = PAUSE_START
+    end = "window cap: 20 minutes passed" if window == WINDOW_MAX else f"window cap: {window:.0f} seconds passed"
+    while True:
+        left = window - (clock() - window_start)
+        if left <= 0:
+            log.write(end)
+            break
+        if polls >= MAX_POLLS:
+            end = f"poll cap: {MAX_POLLS} polls"
+            log.write(end)
+            break
+        wait = int(min(WAIT_STEP, left))
+        t0 = clock()
+        reply = await progress({"task_id": task_id, "wait_seconds": wait}, wait + 180)
+        polls += 1
+        took = clock() - t0
+        if settled(reply, task_id):
+            end = "settled: the task's line shows done, failed or blocked, and the scheduler has stopped"
+            log.write(f"poll {polls}: reply after {took:.1f}s; settled")
+            break
+        if took < QUICK_REPLY:
+            quick += 1
+            nap = max(0.0, min(pause, window - (clock() - window_start)))
+            log.write(f"poll {polls}: reply after {took:.1f}s (did not wait); pausing {nap:.1f}s before the next poll")
+            if nap > 0:
+                await sleep(nap)
+                paused += nap
+            pause = min(pause * 2, PAUSE_MAX)
+        else:
+            log.write(f"poll {polls}: reply after {took:.1f}s (waited); not settled")
+            pause = PAUSE_START
+    stats = {"polls": polls, "quick_replies": quick, "paused_seconds": round(paused, 1), "end": end}
+    log.write(f"polling ended ({end}): progress(task_id) polls {polls}, quick replies {quick}, paused {paused:.1f}s in all")
+    return stats
+
+
 async def run(args: argparse.Namespace) -> int:
     from mcp import ClientSession
     from mcp.client.stdio import stdio_client
@@ -148,6 +214,17 @@
             await call(s, log, "stop", {})
         return 0
 
+    if args.poll_check:
+        plog = Log(out, "poll-check-log.txt")
+        plog.write(f"## POLL CHECK (protocol 4.14; progress(task_id) only), script md5 {script_md5}, org {org}, task {args.task}, "
+                   f"max {args.max_seconds}s, {plog.stamp()}")
+        async with stdio_client(server_params(org)) as (r, w), ClientSession(r, w) as s:
+            await s.initialize()
+            stats = await poll_until_settled(lambda a, t: call(s, plog, "progress", a, timeout=t), args.task, time.monotonic(), plog,
+                                             window=float(args.max_seconds))
+        print(json.dumps(stats))
+        return 0
+
     if args.selftest:
         async with stdio_client(server_params(org)) as (r, w), ClientSession(r, w) as s:
             await s.initialize()
@@ -193,17 +270,8 @@
         try:
             # 3. start
             await call(session, log, "start", {})
-            # 4. wait until the injected task is done/failed/blocked and the scheduler has stopped, or 20 minutes
-            while True:
-                left = WINDOW_MAX - (time.monotonic() - window_start)
-                if left <= 0:
-                    log.write("window cap: 20 minutes passed")
-                    break
-                wait = int(min(WAIT_STEP, left))
-                reply = await call(session, log, "progress", {"task_id": new_id, "wait_seconds": wait}, timeout=wait + 180)
-                line = next((ln for ln in reply.splitlines() if f"(task {new_id})" in ln), "")
-                if re.search(r"\]?: (done|failed|blocked)\b", line) and "scheduler: stopped" in reply:
-                    break
+            # 4. wait until the injected task is done/failed/blocked and the scheduler has stopped, or 20 minutes (F-E4-9: paced)
+            await poll_until_settled(lambda a, t: call(session, log, "progress", a, timeout=t), new_id, window_start, log)
             # 5. final state (read-only)
             await call(session, log, "progress", {})
             await call(session, log, "status", {})
@@ -223,6 +291,9 @@
     ap.add_argument("--dry-run", action="store_true")
     ap.add_argument("--selftest", action="store_true")
     ap.add_argument("--stop", action="store_true")
+    ap.add_argument("--poll-check", action="store_true", help="preflight only: the step-4 polling loop alone (progress only)")
+    ap.add_argument("--task", help="--poll-check: the task id to poll")
+    ap.add_argument("--max-seconds", type=int, default=120, help="--poll-check: the window in seconds (default 120)")
     a = ap.parse_args()
     try:
         if a.dry_run:
@@ -236,7 +307,9 @@
             return 0
         if not a.out and not a.selftest:
             ap.error("--out is required")
-        if not (a.selftest or a.stop) and not a.revises:
+        if a.poll_check and not a.task:
+            ap.error("--poll-check needs --task")
+        if not (a.selftest or a.stop or a.poll_check) and not a.revises:
             ap.error("--revises is required")
         import anyio
         a.out = a.out or "/tmp"
```

### `model_check.sh`

```diff
--- E4-org-growth-0a1-recheck/evidence/harness/model_check.sh	2026-10-22 23:39:32
+++ E5-org-growth-0a2-recheck/evidence/harness/model_check.sh	2026-10-24 03:21:50
@@ -1,20 +1,150 @@
 #!/bin/zsh
-# usage: modelcheck.sh "<label>"   appends to s3/model-checks.txt; exit 0 if both models OK
-LABEL="$1"; OUT=/Volumes/workspace/hirearchy/studies/E4-org-growth-0a1-recheck/evidence/s3/model-checks.txt
-PREP=hirearchy-study-e4-prep-1792693245
-echo "## model check: $LABEL (started $(date -u +%FT%TZ))" >> $OUT
-cd /tmp/hirearchy-e4-prep-1792693245 || exit 90
-for m in claude-sonnet-4.6 claude-haiku-4.5; do
-  ok=0
-  for a in 1 2 3 4 5 6 7; do
-    ts=$(date -u +%FT%TZ)
-    rep=$(kiro-cli chat --v3 --no-interactive --trust-all-tools --agent $PREP --model $m "Reply with OK." 2>/tmp/e4-s3-mc.err); rc=$?
-    err=$(tr '\n' ' ' < /tmp/e4-s3-mc.err | cut -c1-300)
-    echo "[$ts] $LABEL model=$m attempt=$a exit=$rc reply=<<$(echo $rep | tr '\n' ' ')>> stderr=<<$err>>" >> $OUT
-    if [[ $rc -eq 0 && "$rep" == *OK* ]]; then echo "  -> success" >> $OUT; ok=1; break; fi
-    echo "  -> failed; waiting 600s" >> $OUT
-    [[ $a -lt 7 ]] && sleep 600
-  done
-  [[ $ok -eq 1 ]] || { echo "RESULT: $LABEL FAILED for $m after 7 attempts ($(date -u +%FT%TZ))" >> $OUT; exit 1; }
-done
-echo "RESULT: $LABEL both models OK ($(date -u +%FT%TZ))" >> $OUT
+# E5 model and effort check (protocol 4.3, 11 H4). Read-only: it lists, reads and greps; it writes only model-checks.txt.
+# The set is one seat value: claude-sonnet-5.5 at effort high, for the assistant and for every org agent (D-E4-8, D-E4-9).
+# Usage:
+#   model_check.sh listed    <N>       "kiro-cli chat --list-models" lists claude-sonnet-5.5 (stream start; there is no substitution)
+#   model_check.sh org       <N> <S>   every org run log under S/org has one "# cmd:" line with exactly one "--model claude-sonnet-5.5"
+#                                      and exactly one "--effort high"
+#   model_check.sh assistant <N> <S>   the stream's profile has "model": "claude-sonnet-5.5"; every turn-NN.cmd.txt has "--effort high"
+#                                      once, the stream's --agent, and no --model other than claude-sonnet-5.5; the session copy
+#                                      s<N>/assistant-session.json has modelId claude-sonnet-5.5 and effortLevel high (or none recorded);
+#                                      every reasoningModelId in s<N>/assistant-session-messages.jsonl is [qdev::]claude-sonnet-5.5
+#   model_check.sh all       <N> <S>   org, then assistant
+# <N> is the stream label (1, 2, 3, 1r, ...), or "preflight" for the preflight's scratch org (protocol 4.14; output in
+# evidence/preflight/). Appends a block to evidence/s<N>/model-checks.txt and prints its RESULT line.
+# Exit 0: every seat checked is in the set (or, for listed, the model is listed). Exit 1: a seat outside the set (stream-invalidating,
+# H4), or claude-sonnet-5.5 not listed (the stream does not start). Exit 2: usage error, or nothing to check yet (never a pass).
+MODE="$1"; N="$2"; S="$3"
+[[ -n "$MODE" && -n "$N" ]] || { echo "usage: model_check.sh listed|org|assistant|all <N> [<S>]" >&2; exit 2; }
+[[ "$MODE" == listed || -n "$S" ]] || { echo "usage: model_check.sh $MODE <N> <S>" >&2; exit 2; }
+EV=/Volumes/workspace/hirearchy/studies/E5-org-growth-0a2-recheck/evidence/s$N
+[[ "$N" == preflight ]] && EV=/Volumes/workspace/hirearchy/studies/E5-org-growth-0a2-recheck/evidence/preflight
+mkdir -p "$EV"
+OUT="$EV/model-checks.txt"
+LISTING=""
+if [[ "$MODE" == listed ]]; then
+  LISTING="$(kiro-cli chat --list-models 2>&1)"; LRC=$?
+  LISTING="exit $LRC
+$LISTING"
+fi
+python3 - "$MODE" "$N" "$S" "$EV" "$LISTING" >> "$OUT" <<'EOF'
+import glob, json, os, re, shlex, sys
+from datetime import datetime, timezone
+
+mode, n, S, ev, listing = sys.argv[1:6]
+MODEL, EFFORT = "claude-sonnet-5.5", "high"
+
+
+def now():
+    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
+
+
+def flag(tokens, name):
+    return [tokens[i + 1] for i, t in enumerate(tokens[:-1]) if t == name]
+
+
+print(f"## model check {mode} s{n} at {now()} (set: {MODEL} at effort {EFFORT})")
+bad, nothing = [], []
+
+
+def listed():
+    lines = listing.splitlines()
+    print("kiro-cli chat --list-models:", lines[0] if lines else "(no output)")
+    print("\n".join("  " + ln for ln in lines[1:]))
+    rows = [ln for ln in lines[1:] if re.search(rf"(^|[\s*]){re.escape(MODEL)}\s", ln + " ")]
+    if rows:
+        print(f"listed: {MODEL}: yes ({rows[0].strip()})")
+    else:
+        bad.append(f"{MODEL} is not listed")
+
+
+def org():
+    logs = [p for p in sorted(glob.glob(os.path.join(S, "org", "**", "runs", "*.log"), recursive=True)) if "/.git/" not in p]
+    if not logs:
+        nothing.append("no org run log yet")
+    for p in logs:
+        rel = os.path.relpath(p, os.path.join(S, "org"))
+        txt = open(p, errors="replace").read()
+        cmds = re.findall(r"^# cmd: (.*)$", txt, re.M)
+        if not cmds:
+            first = next((ln for ln in txt.splitlines() if ln.startswith("# ")), "(empty)")
+            print(f"  {rel}: no '# cmd:' line, so no model ran ({first[:160]})")
+            continue
+        tokens = cmds[0].split()
+        models, efforts = flag(tokens, "--model"), flag(tokens, "--effort")
+        ok = len(cmds) == 1 and models == [MODEL] and efforts == [EFFORT]
+        print(f"  {rel}: --model {models or '(none)'} --effort {efforts or '(none)'}{'' if ok else '   <-- OUTSIDE THE SET'}")
+        if not ok:
+            bad.append(f"org run {rel}: --model {models} --effort {efforts} ({len(cmds)} '# cmd:' line(s))")
+    print(f"org run logs checked: {len(logs)}")
+
+
+def assistant():
+    name = f"hirearchy-study-e5-s{n}-assistant"
+    prof = [p for p in (os.path.expanduser(f"~/.kiro/agents/{name}.json"), os.path.join(ev, "profiles", f"{name}.json")) if os.path.isfile(p)]
+    if prof:
+        m = json.load(open(prof[0])).get("model")
+        print(f"  profile {prof[0]}: model {m!r}")
+        if m != MODEL:
+            bad.append(f"assistant profile model {m!r}")
+    else:
+        nothing.append(f"profile {name}.json not found in ~/.kiro/agents or s{n}/profiles")
+    cmds = sorted(glob.glob(os.path.join(ev, "turn-*.cmd.txt")))
+    if not cmds:
+        nothing.append("no turn-NN.cmd.txt yet")
+    for p in cmds:
+        tokens = shlex.split(open(p).read())[:-1]  # the last argument is Lena's line
+        efforts, models, agents = flag(tokens, "--effort"), flag(tokens, "--model"), flag(tokens, "--agent")
+        ok = efforts == [EFFORT] and models in ([], [MODEL]) and agents == [name]
+        print(f"  {os.path.basename(p)}: --effort {efforts} --model {models or '(the profile)'} --agent {agents}{'' if ok else '   <-- OUTSIDE THE SET'}")
+        if not ok:
+            bad.append(f"assistant invocation {os.path.basename(p)}: --effort {efforts} --model {models} --agent {agents}")
+    sj = os.path.join(ev, "assistant-session.json")
+    if os.path.isfile(sj):
+        j = json.load(open(sj))
+        mid, eff = j.get("modelId"), j.get("effortLevel")
+        print(f"  session {j.get('id')}: modelId {mid!r} effortLevel {eff!r}{'' if eff else ' (not recorded by the session file)'}")
+        if mid != MODEL:
+            bad.append(f"assistant session modelId {mid!r}")
+        if eff not in (None, "", EFFORT):
+            bad.append(f"assistant session effortLevel {eff!r}")
+    else:
+        nothing.append(f"no session copy s{n}/assistant-session.json yet")
+    mj = os.path.join(ev, "assistant-session-messages.jsonl")
+    if os.path.isfile(mj):
+        vals = {}
+        for line in open(mj):
+            for v in re.findall(r'"reasoningModelId"\s*:\s*"([^"]*)"', line.replace('\\"', '"')):
+                vals[v] = vals.get(v, 0) + 1
+        print(f"  reasoningModelId values in the session messages: {vals or '(none)'}")
+        if not vals:
+            nothing.append("no reasoningModelId in the session messages yet")
+        for v, k in vals.items():
+            if v.split("::")[-1] != MODEL:
+                bad.append(f"assistant reasoningModelId {v!r} (x{k})")
+    else:
+        nothing.append(f"no session copy s{n}/assistant-session-messages.jsonl yet")
+
+
+steps = {"listed": [listed], "org": [org], "assistant": [assistant], "all": [org, assistant]}
+if mode not in steps:
+    bad.append(f"unknown mode {mode!r}")
+else:
+    for step in steps[mode]:
+        step()
+for b in bad:
+    print(f"OUTSIDE THE SET: {b}" if mode != "listed" else f"NOT LISTED: {b}")
+for x in nothing:
+    print(f"NOT CHECKED: {x}")
+if bad:
+    res = "NOT LISTED: the stream does not start (no substitution)" if mode == "listed" else "INVALIDATING (H4: a seat outside the set)"
+elif nothing:
+    res = "INCOMPLETE (nothing to check yet; not a pass)"
+else:
+    res = "OK"
+print(f"RESULT: s{n} {mode}: {res} ({now()})")
+sys.exit(1 if bad else (2 if nothing else 0))
+EOF
+rc=$?
+tail -1 "$OUT"
+exit $rc
```

### `extract_mechanical.py`

```diff
--- E4-org-growth-0a1-recheck/evidence/harness/extract_mechanical.py	2026-10-22 20:47:54
+++ E5-org-growth-0a2-recheck/evidence/harness/extract_mechanical.py	2026-10-24 03:18:54
@@ -1,5 +1,5 @@
 #!/usr/bin/env python3
-"""E4 mechanical extracts (protocol 7.2 "Mechanical extracts", amendment 1 A3). Facts only; no scoring. Read-only on the sandbox,
+"""E5 mechanical extracts (protocol 7.2 "Mechanical extracts", amendment 1 A3). Facts only; no scoring. Read-only on the sandbox,
 the org and the kiro home (file copies only). Usage:
     uv --directory /Volumes/workspace/hirearchy run python extract_mechanical.py <stream, e.g. 1r>
 Needs evidence/s<N>/ to hold sandbox-path.txt, assistant-session-messages.jsonl, events/, run-logs/, msgs/ (copy_org_evidence.sh).
@@ -18,7 +18,7 @@
 from datetime import datetime, timezone
 from pathlib import Path
 
-EV = Path("/Volumes/workspace/hirearchy/studies/E4-org-growth-0a1-recheck/evidence")
+EV = Path("/Volumes/workspace/hirearchy/studies/E5-org-growth-0a2-recheck/evidence")
 N = sys.argv[1]
 D = EV / f"s{N}"
 S = Path((D / "sandbox-path.txt").read_text().strip())
@@ -337,7 +337,7 @@
             flags.append("writes into the deliverable folder")
         if str(ORG) in cmd or str(ORG).replace("/tmp/", "/private/tmp/", 1) in cmd or re.search(r"\borg/", cmd):
             flags.append("touches S/org")
-        if re.search(r"\bhirearchy\b(?!-e4)", cmd.replace(str(S), "").replace("/Volumes/workspace/hirearchy", "")):
+        if re.search(r"\bhirearchy\b(?!-e5)", cmd.replace(str(S), "").replace("/Volumes/workspace/hirearchy", "")):
             flags.append("mentions hirearchy")
         if re.search(r"(^|[;&|]\s*)(uv run )?hirearchy\s", cmd):
             flags.append("runs hirearchy CLI")
@@ -345,7 +345,7 @@
             flags.append("writes elsewhere (possible)")
         sw.append(f"[{c['ts']}] call #{c['n']} turn {c['turn']} status={c['status']} flags={flags or ['none']}\nCOMMAND: {cmd}\nRESULT: {(c['result'] or '')[:1500]}\n")
         if "writes into the deliverable folder" in flags:
-            src = re.findall(r"((?:/private)?/tmp/hirearchy-e4-s\w+-\d+/org/[\w/.\-]+\.md|org/[\w/.\-]+\.md)", cmd)
+            src = re.findall(r"((?:/private)?/tmp/hirearchy-e5-s\w+-\d+/org/[\w/.\-]+\.md|org/[\w/.\-]+\.md)", cmd)
             src_info = []
             for sp in src:
                 rel = sp.split("/org/", 1)[-1] if "/org/" in sp else sp[len("org/"):]
```

### `extract_mechanical_s2.py`

```diff
--- E4-org-growth-0a1-recheck/evidence/harness/extract_mechanical_s2.py	2026-10-22 21:43:17
+++ E5-org-growth-0a2-recheck/evidence/harness/extract_mechanical_s2.py	2026-10-24 03:18:54
@@ -1,5 +1,5 @@
 #!/usr/bin/env python3
-"""E4 mechanical extracts (protocol 7.2 "Mechanical extracts", amendment 1 A3). Facts only; no scoring. Read-only on the sandbox,
+"""E5 mechanical extracts (protocol 7.2 "Mechanical extracts", amendment 1 A3). Facts only; no scoring. Read-only on the sandbox,
 the org and the kiro home (file copies only). Usage:
     uv --directory /Volumes/workspace/hirearchy run python extract_mechanical.py <stream, e.g. 1r>
 Needs evidence/s<N>/ to hold sandbox-path.txt, assistant-session-messages.jsonl, events/, run-logs/, msgs/ (copy_org_evidence.sh).
@@ -18,7 +18,7 @@
 from datetime import datetime, timezone
 from pathlib import Path
 
-EV = Path("/Volumes/workspace/hirearchy/studies/E4-org-growth-0a1-recheck/evidence")
+EV = Path("/Volumes/workspace/hirearchy/studies/E5-org-growth-0a2-recheck/evidence")
 N = sys.argv[1]
 D = EV / f"s{N}"
 S = Path((D / "sandbox-path.txt").read_text().strip())
@@ -337,7 +337,7 @@
             flags.append("writes into the deliverable folder")
         if str(ORG) in cmd or str(ORG).replace("/tmp/", "/private/tmp/", 1) in cmd or re.search(r"\borg/", cmd):
             flags.append("touches S/org")
-        if re.search(r"\bhirearchy\b(?!-e4)", cmd.replace(str(S), "").replace("/Volumes/workspace/hirearchy", "")):
+        if re.search(r"\bhirearchy\b(?!-e5)", cmd.replace(str(S), "").replace("/Volumes/workspace/hirearchy", "")):
             flags.append("mentions hirearchy")
         if re.search(r"(^|[;&|]\s*)(uv run )?hirearchy\s", cmd):
             flags.append("runs hirearchy CLI")
@@ -345,7 +345,7 @@
             flags.append("writes elsewhere (possible)")
         sw.append(f"[{c['ts']}] call #{c['n']} turn {c['turn']} status={c['status']} flags={flags or ['none']}\nCOMMAND: {cmd}\nRESULT: {(c['result'] or '')[:1500]}\n")
         if "writes into the deliverable folder" in flags:
-            src = re.findall(r"((?:/private)?/tmp/hirearchy-e4-s\w+-\d+/org/[\w/.\-]+\.md|org/[\w/.\-]+\.md)", cmd)
+            src = re.findall(r"((?:/private)?/tmp/hirearchy-e5-s\w+-\d+/org/[\w/.\-]+\.md|org/[\w/.\-]+\.md)", cmd)
             src_info = []
             for sp in src:
                 rel = sp.split("/org/", 1)[-1] if "/org/" in sp else sp[len("org/"):]
```

### `extract_mechanical_s3.py`

```diff
--- E4-org-growth-0a1-recheck/evidence/harness/extract_mechanical_s3.py	2026-10-22 23:34:45
+++ E5-org-growth-0a2-recheck/evidence/harness/extract_mechanical_s3.py	2026-10-24 03:18:54
@@ -1,5 +1,5 @@
 #!/usr/bin/env python3
-"""E4 mechanical extracts (protocol 7.2 "Mechanical extracts", amendment 1 A3). Facts only; no scoring. Read-only on the sandbox,
+"""E5 mechanical extracts (protocol 7.2 "Mechanical extracts", amendment 1 A3). Facts only; no scoring. Read-only on the sandbox,
 the org and the kiro home (file copies only). Usage:
     uv --directory /Volumes/workspace/hirearchy run python extract_mechanical.py <stream, e.g. 1r>
 Needs evidence/s<N>/ to hold sandbox-path.txt, assistant-session-messages.jsonl, events/, run-logs/, msgs/ (copy_org_evidence.sh).
@@ -18,7 +18,7 @@
 from datetime import datetime, timezone
 from pathlib import Path
 
-EV = Path("/Volumes/workspace/hirearchy/studies/E4-org-growth-0a1-recheck/evidence")
+EV = Path("/Volumes/workspace/hirearchy/studies/E5-org-growth-0a2-recheck/evidence")
 N = sys.argv[1]
 D = EV / f"s{N}"
 S = Path((D / "sandbox-path.txt").read_text().strip())
@@ -337,7 +337,7 @@
             flags.append("writes into the deliverable folder")
         if str(ORG) in cmd or str(ORG).replace("/tmp/", "/private/tmp/", 1) in cmd or re.search(r"\borg/", cmd):
             flags.append("touches S/org")
-        if re.search(r"\bhirearchy\b(?!-e4)", cmd.replace(str(S), "").replace("/Volumes/workspace/hirearchy", "")):
+        if re.search(r"\bhirearchy\b(?!-e5)", cmd.replace(str(S), "").replace("/Volumes/workspace/hirearchy", "")):
             flags.append("mentions hirearchy")
         if re.search(r"(^|[;&|]\s*)(uv run )?hirearchy\s", cmd):
             flags.append("runs hirearchy CLI")
@@ -345,7 +345,7 @@
             flags.append("writes elsewhere (possible)")
         sw.append(f"[{c['ts']}] call #{c['n']} turn {c['turn']} status={c['status']} flags={flags or ['none']}\nCOMMAND: {cmd}\nRESULT: {(c['result'] or '')[:1500]}\n")
         if "writes into the deliverable folder" in flags:
-            src = re.findall(r"((?:/private)?/tmp/hirearchy-e4-s\w+-\d+/org/[\w/.\-]+\.md|org/[\w/.\-]+\.md)", cmd)
+            src = re.findall(r"((?:/private)?/tmp/hirearchy-e5-s\w+-\d+/org/[\w/.\-]+\.md|org/[\w/.\-]+\.md)", cmd)
             src_info = []
             for sp in src:
                 rel = sp.split("/org/", 1)[-1] if "/org/" in sp else sp[len("org/"):]
```

### `copy_org_evidence.sh`

```diff
--- E4-org-growth-0a1-recheck/evidence/harness/copy_org_evidence.sh	2026-10-22 04:59:23
+++ E5-org-growth-0a2-recheck/evidence/harness/copy_org_evidence.sh	2026-10-24 03:18:54
@@ -1,9 +1,9 @@
 #!/bin/zsh
-# E4: read-only copy of a stream's org into the evidence folder (protocol 7.2 "The org"), after the stream ended.
+# E5: read-only copy of a stream's org into the evidence folder (protocol 7.2 "The org"), after the stream ended.
 # Usage: copy_org_evidence.sh <S> <stream N>
 # Uses only file copies and the read-only CLI commands of protocol 4.8 (services | progress | status | health, obs trace).
 S="$1"; N="$2"
-EV=/Volumes/workspace/hirearchy/studies/E4-org-growth-0a1-recheck/evidence/s$N
+EV=/Volumes/workspace/hirearchy/studies/E5-org-growth-0a2-recheck/evidence/s$N
 ORG="$S/org"
 HIR="uv --directory /Volumes/workspace/hirearchy run hirearchy"
 mkdir -p $EV/msgs $EV/run-logs $EV/events $EV/org-files $EV/service $EV/playbook
```

### `safety-snapshot.sh`

```diff
--- E4-org-growth-0a1-recheck/evidence/harness/safety-snapshot.sh	2026-10-22 04:30:21
+++ E5-org-growth-0a2-recheck/evidence/harness/safety-snapshot.sh	2026-10-24 03:18:54
@@ -1,9 +1,9 @@
 #!/bin/zsh
-# E4 safety snapshot (read-only). Usage: safety-snapshot.sh <label>   -> prints to stdout
+# E5 safety snapshot (read-only). Usage: safety-snapshot.sh <label>   -> prints to stdout
 # Content per protocol.md 4.8 (E3's snapshot + E4 additions). Never modifies anything it lists.
 label="${1:-snapshot}"
 REPO=/Volumes/workspace/hirearchy
-PROTO=$REPO/studies/E4-org-growth-0a1-recheck/evidence/protocol.md
+PROTO=$REPO/studies/E5-org-growth-0a2-recheck/evidence/protocol.md
 echo "label: $label"
 echo "date: $(date)"
 echo "date_utc: $(date -u +%Y-%m-%dT%H:%M:%SZ)  epoch: $(date +%s)"
@@ -19,7 +19,7 @@
 ls -la ~/.kiro/agents
 echo "== md5 ~/.kiro/agents/*"
 for f in ~/.kiro/agents/*(.N); do md5 "$f"; done
-echo "== hirearchy-* profiles in ~/.kiro/agents (pre-existing vs generated by E4)"
+echo "== hirearchy-* profiles in ~/.kiro/agents (pre-existing vs generated by E5)"
 ls -1 ~/.kiro/agents | grep '^hirearchy-' || echo "(none)"
 echo "== ls ~/.kiro/skills"
 ls ~/.kiro/skills
@@ -36,8 +36,8 @@
 git -C $REPO status --porcelain
 echo "== git HEAD"
 git -C $REPO rev-parse HEAD
-echo "== git diff --stat d85cc13 HEAD -- src skills pyproject.toml uv.lock"
-git -C $REPO diff --stat d85cc13 HEAD -- src skills pyproject.toml uv.lock
+echo "== git diff --stat 6618c0d HEAD -- src skills pyproject.toml uv.lock"
+git -C $REPO diff --stat 6618c0d HEAD -- src skills pyproject.toml uv.lock
 echo "== md5 protocol.md"
 md5 $PROTO
 echo "== other orgs"
```

### `org_state.py`

```diff
--- E4-org-growth-0a1-recheck/evidence/harness/org_state.py	2026-10-22 04:42:35
+++ E5-org-growth-0a2-recheck/evidence/harness/org_state.py	2026-10-24 03:18:54
@@ -1,5 +1,5 @@
 #!/usr/bin/env python3
-"""E4 read-only org state snapshot (file listings only; no MCP/CLI call against the org).
+"""E5 read-only org state snapshot (file listings only; no MCP/CLI call against the org).
 Usage: org_state.py <S> <label>   -> prints a block for run-counts-by-turn.txt
 Lists every run log (agent, model, start from the file name = UTC, duration from the exit line, flagged if inside the
 injection window recorded in <S>/injection/window.txt as 'start_utc end_utc'), open items (message files in inboxes and
```

### `profile-template.json`

```diff
--- E4-org-growth-0a1-recheck/evidence/harness/hirearchy-study-e4-prep-1792639838.json.deleted-by-manager	2026-10-22 04:30:47
+++ E5-org-growth-0a2-recheck/evidence/harness/profile-template.json	2026-10-24 03:18:27
@@ -1,11 +1,11 @@
 {
-  "name": "hirearchy-study-e4-prep-1792639838",
-  "description": "internal: hirearchy usability study E4 harness-preparation profile (pre-flight only, no org); deleted at the end of the study",
+  "name": "hirearchy-study-e5-s<N>-assistant",
+  "description": "internal: hirearchy usability study E5 stream s<N> assistant; deleted after the stream",
   "mcpServers": {
     "hirearchy": {
       "command": "uv",
       "args": ["--directory", "/Volumes/workspace/hirearchy", "run", "hirearchy", "mcp"],
-      "env": { "ORG_ROOT": "/tmp/hirearchy-e4-prep-1792639838/org" }
+      "env": { "ORG_ROOT": "/tmp/hirearchy-e5-s<N>-<epoch>/org" }
     }
   },
   "tools": ["*"],
```

### `test_poll_loop.py` (new)

See the file; md5 in `MD5SUMS`.
