# E4 protocol amendment 1: product 7d86c31, replacement stream s1r, section 10 under the V3 run formats

Pre-registered 2026-10-22 (about 18:10 UTC) by the decision step (opus), before the replacement stream exists: no `evidence/s1r/`, no s1r
sandbox, profile or session. Authority: `manager-decision-restart.md`, decision 2, which lists what this amendment may change. It changes
nothing else.

- `protocol.md` (md5 `584b6cc71e3d073d10d45c1c2e64325e`, `protocol.md5`) is not edited. It stays binding wherever this file does not
  override it.
- **Freeze.** This file is frozen before turn 1 of s1r. Its md5 is in `protocol-amendment-1.md5`, and it is never edited afterwards.
  `protocol.md` section 0 applies to it as to `protocol.md`: the s1r, s2 and s3 run steps check both md5 files before their turn 1. A
  mismatch means: do not run; escalate to the user.
- The harness preflight of decision 3 of `manager-decision-restart.md` is a precondition for s1r's turn 1. It is defined there, not here.

Sources read for this amendment:
- `protocol.md`, `manager-decision-restart.md`, `setup.md`, `INDEX.md`, `harness/*`, and `evidence/s1/` (read only);
- `docs/research/org-growth/kiro-v3/kiro-v3-report.md` and `live-verification.md`;
- the real V3 run logs, events, kiro home and evidence under `/tmp/kirov3-live`;
- README sections "Kiro integration" and "Workspaces, inputs and confinement";
- `docs/design/org-growth-phase-0a1.md` section 17 and `go-no-go-0b.md` section 2 item 6;
- at `7d86c31`: `src/hirearchy/kiro/{_launch,_readiness,_runner,_places,_env}.py`, `app/wire_cli.py`, `daemon/{api,_status}.py`,
  `mcp_server/{_tools_scheduler,_tools_services,_tools_files}.py`, `telemetry/_summarize.py`, `prompts/_files.py` (diff), and the recorded
  kiro streams `src/hirearchy/kiro/tests/golden/kiro-streams/{k5b,p15b}.jsonl`.

## A1. Product under test

- **`main` = `7d86c31f1b0d52e7ea9467ce72c8d9322e71a71c`.** That is 0a and 0a.1 (`d85cc13`) plus the 13 commits of `fix/kiro-runtime-v3`
  (fast-forward, not pushed). Wherever `protocol.md` names `d85cc13` as the product under test, it reads `7d86c31`: the header, 4.1 and 4.9.
- **4.1 diff check.** Before each stream's turn 1 and after its last turn, `s<N>/setup.txt` records:
  - `git rev-parse HEAD`;
  - `git status --porcelain`;
  - `git diff --stat 7d86c31 HEAD -- src skills pyproject.toml uv.lock`, which must be empty.

  The rest of 4.1 is unchanged. `harness/safety-snapshot.sh` still prints `git diff --stat d85cc13 HEAD -- ...`. That output now lists
  the kiro-runtime-v3 files. It is informational, and the 4.1 check is the `7d86c31` diff above.
- **Skill (4.4).** `skills/hirearchy/SKILL.md` at `7d86c31` has md5 **`573495bb613f19f7c07ce86508ebae4f`** and 125 lines. This step
  verified it on the git blob at `7d86c31`, on the git blob at `d85cc13` and on the working tree. `git diff d85cc13 7d86c31 -- skills/` is
  empty, and no commit in `d85cc13..7d86c31` touches `skills/`. The staged copy `harness/staging/.kiro/skills/hirearchy/SKILL.md` has the
  same md5. All of 4.4 applies unchanged, with this value.
- **Deterministic part (4.9).** It runs at `7d86c31`, before s1r's turn 1. The step that writes this amendment runs it:
  - the 4.9 command verbatim: `uv run pytest -p no:cacheprovider -v tests/e2e/test_org_growth_0a.py`;
  - the brief's form: `uv run pytest -q tests/e2e/test_org_growth_0a.py`.

  The output goes to `evidence/deterministic/at-7d86c31/` (a `SUMMARY.md` plus the raw outputs). The required cases, the failure rule
  (record, then escalate before s1r) and section 12's use of the result are those of 4.9. The `d85cc13` output from the s1 step,
  `deterministic/pytest-e2e-org-growth.txt`, stays unchanged as the record of that run. Section 12's "the deterministic part (4.9)
  passed" is read on the `7d86c31` run.
- kiro-cli is `2.33.0` at this step (`kiro-cli --version`), the same version as s1 and the live verification. 4.2 and H6 are unchanged.

## A2. Streams: s1 INVALID, replacement s1r, then s2 and s3

- **s1 is INVALID (section 11, H8).** Org runs had no hirearchy tools (`s1/harness-failures/`). `evidence/s1/` stays unchanged and in the
  report as INVALID. Section 11 applies: observations made before the failure stand, and the scoring step scores them.
- **s1r is the replacement stream** approved under section 11 (`manager-decision-restart.md`, decision 1). It gets:
  - a fresh sandbox `/tmp/hirearchy-e4-s1r-<epoch>`;
  - a fresh org at `S/org`, not pre-created;
  - a fresh assistant session;
  - the profile `hirearchy-study-e4-s1r-assistant`: the 4.2 JSON with `s<N>` = `s1r`;
  - the evidence folder `evidence/s1r/`, with the structure of 7.2.

  It runs under `protocol.md` plus this amendment.
- **Order.** s1r, then s2, then s3, never in parallel. Section 2's start conditions apply with s1r in place of s1.
- **The study needs 3 valid streams: s1r, s2 and s3.** Section 12's "3 valid streams" means these three. s1 is not one of them.
- **Where `protocol.md` uses s1 as the first stream, s1r takes that role:**
  - 4.2: s1r's profile is the reference for the profile `diff` of s2 and s3;
  - 5.3: the injection script is still unfrozen. s1 never injected, and the script md5 is `c80e25d65fe58cdb97d7faa758d59484`. It is
    frozen at s1r's first successful `request`. s1r records its md5 in `s1r/injection/injection-log.txt`, and s2 and s3 must use the same
    md5.
- **Study-level steps of the s1 step are not repeated:**
  - `protocol.md5`;
  - the probe and `harness/workspace-cli.json` (md5 `05d30ccbfd35530747c8a542eb67985c`; 4.5 runs the probe once);
  - `models.txt` (4.3's substitution check still runs at each stream's start);
  - `answer-key.md` and `notes/`;
  - the study-level `safety-before.txt`.

  The deterministic part is re-run at `7d86c31` (A1).

## A3. Section 10 under the V3 run-log and event formats

Each method below still measures what section 10 says. Only the evidence source or the pattern changed where noted. No pass rule, no
definition of section 9 and no verdict rule of section 12 changes.

### A3.1 What moved, with real examples

| Item | At `d85cc13` (E3, s1) | At `7d86c31` (V3) | Real example |
|---|---|---|---|
| Run command (`# cmd:`) | `kiro-cli chat --no-interactive --agent P --model M <prompt on stdin>` | the launcher, then the same kiro command plus `--v3 --require-mcp-startup --output-format stream-json`: `<python> -I -S .../kiro/_launch.py --start-deadline 60 -- kiro-cli chat --no-interactive --agent P --model M --v3 --require-mcp-startup --output-format stream-json <prompt on stdin>` | `/tmp/kirov3-live/org/lead/worker/runs/20261022T160101282202.log` line 4 (`--model claude-haiku-4.5 --v3 ...`) |
| Run cwd (`# cwd:`) | `S/org/<agent>` | an emptied scratch dir `<state>/kiro-cwd/<org-id>/<agent-key>` | E3 `# cwd: /private/tmp/hirearchy-e3-1792595952/org/lead`; V3 `# cwd: /private/tmp/kirov3-live/state/kiro-cwd/kirov3-live-org-54c47d7d69341c23/lead-8cb33b27` (`lead/runs/20261022T160045143176.log` line 3) |
| Start marker | none | `# kiro: run started (engine v3)` after the prompt section | the same log; in every run log of the live verification |
| A hirearchy tool call | `[tool] Running: @hirearchy/<tool>`, then separate `[tool] status: Completed` lines | the renderer's `[tool] @hirearchy/<tool> <input as compact JSON, cut at 200 characters>`, then `[tool ok] @hirearchy/<tool> <input>` or `[tool failed] @hirearchy/<tool> <input>[: <kiro denial text>]` | `[tool] @hirearchy/delegate {"tool_id":"hirearchy::delegate","arguments":{"to":"lead/worker",...` and `[tool ok] @hirearchy/delegate ...` (`lead/runs/20261022T160045143176.log`); E3: `[tool] Running: @hirearchy/delegate` (`studies/E3-org-growth-0a-live/evidence/run-logs/lead/20261021T152349661718.log` line 200) |
| Tool results in the run log | kiro's text output; E3's logs show `[tool] status: Completed` lines and no results | never (README "Agent runs (the scheduler)"; `_launch.py` copies only kiro's "Tool call denied" text) | `[tool failed] Read File /tmp/kirov3-live/ws sp 1 (x)/c.txt: Tool call denied by user's permissions. Rule: deny fs_read matching "/**" Source: agent-profile.` (`odd/runs/20261022T160628867519.log` line 138) |
| End of the model's run | no marker: the text ends, then `# exit` | `[run finished] <status> (<stopReason>)` or `[run error] <stage>: <message>` | `[run finished] success (end_turn)` (worker log line 149) |
| Prompt markers | `# ---- prompt ----` / `# ---- output ----` | unchanged | `lead/runs/20261022T160045143176.log` lines 5 and 105 |
| Exit line | `# exit N after Ns` | unchanged (written by the scheduler; `scheduler/` and `runs/` unchanged) | `# exit 0 after 30s` (worker log line 151) |
| Kiro state of org runs | the user's `~/.kiro` | the per-org kiro home under the hirearchy state dir (A3.2) | `[INFO] agent.userConfigDir.resolved {"name":"kirov3-live-org-54c47d7d69341c23","source":"env"}` (`lead/runs/20261022T160045143176.log` line 112) |
| Org scheduler profiles | `~/.kiro/agents/hirearchy-*.json` | `<kiro home>/agents/hirearchy-*.json`; none is written to `~/.kiro/agents` | live-verification step 8b and 8c |
| Org-run sessions and credits | not used; credits "not recorded by the product or by the run logs" (`s1/cost.txt`) | kiro's session store in the per-org kiro home: `sessions/<hash>/sess_*/messages.jsonl` (`tool_call` with full `args`, `tool_result` with full `content`, `usage_summary` with credits) and `session.json` | the `rev` run `rev@20261022T160811713490`: session `sess_7f802e17-...`, `tool_call` `{"tool_id": "hirearchy::report", "arguments": {...}}`, its result "reported done on 20261022T160811451884-root-6751 to root; returned 1 unspent run(s) of budget to root", `usage_summary` credits 0.18298508298507465 |
| `.runtime/events/` (`tool.call`, `run.start`, `run.end`, `service.revise`, `msg.deliver`, `cli.command`) | schema v1 | **unchanged**. `telemetry/`, `observability/`, `scheduler/`, `services/`, `reflection/`, `mail/` and `dispatch/` have 0 non-test files changed since `d85cc13` | `{"v":1,...,"proc":"mcp","pid":52633,"kind":"tool.call","actor":"lead","run":"lead@20261022T160045143176",...,"tool":"delegate","ok":true,...,"error":null,"error_type":null,"args":{...}}` has the same schema as s1's `mcp-12808-*.jsonl` lines at `d85cc13` |
| `tool.call` `args` | a summary: ids, paths, titles, numbers; other text only as `<name>_chars`; other lists as `<name>_n` | unchanged. For `revise_playbook` that means `service`, `content_chars`, `reason_chars`, `evidence_n` and `evidence_chars`, not the ids | `"args":{"path":"lead/MEMORY.md","content_chars":331,"append":false}` (`mcp-52633`) |

Two rules for every run-log pattern:
- **One call line per hirearchy call.** A `[tool] @hirearchy/<tool>` line is written once per hirearchy call. In every lead and
  lead/worker run of `/tmp/kirov3-live`, the count of such lines equals the count of that run's `tool.call` events: 2, 2, 3, 3 and 3 for
  the five lead runs, and 2 and 2 for the two worker runs (all 10 runs: A3.3, P3). `Tool Load` lines (kiro's `tool_load`) do not match.
- **The events decide.** Events decide whether a call succeeded, as before. `[tool ok]` / `[tool failed]` are never used to decide
  whether a hirearchy call was admitted or refused. How kiro marks a hirearchy tool that returns an error was not observed live: no run
  in `/tmp/kirov3-live` has `[tool failed] @hirearchy/`.

### A3.2 Where a stream's kiro state lives, and what is copied

- **`<state>`.** It is `$HIREARCHY_STATE_DIR` when that is set in the environment of the process that starts the scheduler, else
  `~/Library/Application Support/hirearchy` (macOS; `src/hirearchy/kiro/_places.py`). The scheduler is started by root's MCP server: the
  assistant's, or the injection script's. Both normally inherit the facilitator's environment. The assistant's server inherits it through
  kiro-cli, which starts MCP servers with its own environment plus the profile's `env` (README "Profiles"; kiro-v3 report section 7(d)).
- **The per-org kiro home** is `<state>/kiro-home/<org-id>/`, mode `0700`. It holds `agents/`, `sessions/`, `session-index/`, `logs/` and
  `settings/`.
- **The scratch cwds** are `<state>/kiro-cwd/<org-id>/<agent-key>/`. Each one is emptied before every run, so it holds no evidence.
- **Finding them.** The run step reads `<state>/kiro-cwd/<org-id>/` from the `# cwd:` line of the stream's first run log. It records in
  `run-log.md` the kiro home that follows from it, and whether every run log of the stream shows the same `<state>/kiro-cwd/<org-id>/`. A
  different one is recorded as a fact. Example: `# cwd: /private/tmp/kirov3-live/state/kiro-cwd/kirov3-live-org-54c47d7d69341c23/lead-8cb33b27`
  means the kiro home is `/private/tmp/kirov3-live/state/kiro-home/kirov3-live-org-54c47d7d69341c23/`.
- **What is copied.** After the stream, with the read-only extraction of 4.8 and section 7, these are copied read-only:
  - `<kiro home>/agents/hirearchy-*.json` goes to `s<N>/profiles/`. These are 7.2's "every org scheduler profile". They are not deleted:
    4.8's deletion covers `~/.kiro/agents` and is unchanged. Under V3 that deletion finds only the stream's assistant profile.
  - `<kiro home>/sessions/*/sess_*/session.json` and `messages.jsonl` go to `s<N>/org-kiro-sessions/<hash>/<session id>/`. Each org run
    has one session.

  Nothing else in the kiro home or the scratch dirs is read. The kiro home is left in place, as the sandbox is.
- **Matching a run to its session.** A run and a session match when all of these hold:
  - `session.json` `workspacePaths[0]` equals the run log's `# cwd:`;
  - `agentMode` equals the `--agent` of its `# cmd:`;
  - `modelId` equals its `--model`;
  - `createdAt` lies between the run's `run.start` and `run.end` events.

  Example: `rev/runs/20261022T160811713490.log` has `# cwd: .../kiro-cwd/kirov3-live-org-54c47d7d69341c23/rev-03e404fd`, and
  `run.start` and `run.end` are at 16:08:11.718Z and 16:08:50.252Z. Session `sess_7f802e17-02f2-4015-8c7c-290188f49036` has
  `workspacePaths` `[".../rev-03e404fd"]`, `agentMode` `hirearchy-kirov3-live-org-54c47d-read-shell-xbbb1b99e`, `modelId`
  `claude-haiku-4.5`, and `createdAt` 16:08:21.734Z.

### A3.3 Method by method

"Not moved" means: same files, same sources, same check as in `protocol.md`.

| Method | Moved? | Under V3 |
|---|---|---|
| 10.1(a) playbook | Not moved, except the `revise-playbook-attempts.txt` input (10.1(c)) | `playbook/`, `org-git-log.txt`, `events/` (`service.revise`), `msgs/sent/` and `service/` come from the org's git, its message files and `.runtime/events/`, all unchanged (A3.1). |
| 10.1(b) contract | Not moved | `service/`, `contract-loop.txt`, turn files, `lena-lines.txt`, `msgs/sent/`, `final-services-progress-status-health.txt`, `org-git-log.txt`, `shell-writes.txt`. The assistant's session store is the user's `~/.kiro` under `kiro-cli chat --v3`, as in s1 and E3. |
| 10.1(c) attempts | **Moved: the run-log pattern and the source of verbatim arguments and replies** | `revise-playbook-attempts.txt` lists every `tool.call` event with `tool == "revise_playbook"` (unchanged; it decides). The cross-check with `run-logs/` uses patterns P1 and P2 below instead of `Running: @hirearchy/revise_playbook`. Per run, the P1 lines must equal the events; a mismatch is recorded, and the events decide. Admitted or refused: from the event's `ok` and `error` (verbatim), and for admitted, a new PLAYBOOK version, as before. The cited `evidence` ids, the full arguments and the reply verbatim come from the run's session (A3.2): the `tool_call` entry whose `args.tool_id` is `hirearchy::revise_playbook`, and its `tool_result`. The events carry only `evidence_n`. The same sources fill 5.4's `window-runs.txt` ("its arguments and result verbatim"). Example: A3.1 rows "A hirearchy tool call" and "Org-run sessions" (`delegate`, `report`). No live run called `revise_playbook`; the renderer writes every hirearchy call in the same form. |
| 10.1(d) report | Follows 10.1(c) | Counts from `revise-playbook-attempts.txt`. |
| 10.2(a) item per reject | Not moved | Turn files, `lena-lines.txt`, `contract-loop.txt` (assistant session). |
| 10.2(b) human-tier links | Not moved | `regression-list/` is cut from lead prompts between `# ---- prompt ----` and `# ---- output ----`, which are unchanged (A3.1). `reflection/` and `prompts/` are unchanged except the Files lines (A5). |
| 10.3(a)-(c) clause 3 | Not moved | `client-questions.txt` (result files in `S/org/inbox` and `read`, the product parser), `deliverables-log.txt` and the turn files (assistant), `memos/versions/` (org git), `org-files/review-*`. |
| 10.4(a) memo quality | Not moved | `memos/`, `memos/versions/`, `answer-key.md`. |
| 10.4(b) runs per case | Not moved | `run-counts.txt` patterns still match: model `^# cmd: .*--model (\S+)` gives `claude-haiku-4.5` on the V3 line of A3.1; start from the log's file name (UTC), equal to the `run` id of the events (`lead/runs/20261022T160045143176.log` matches `run":"lead@20261022T160045143176"`); seconds from `^# exit (\S+) after (\d+)s`. A run log with a `# kiro:` failure line (A3.4) is still a run log, and every run counts as 4.7 says. |
| 10.5 S17-2a to S17-2e | Not moved | Assistant data and `msgs/`. |
| 10.5 S17-3a to S17-3c | Not moved | `client-questions.txt`, `assistant-tool-calls.txt`. |
| 10.5 S17-1a injection | Partly moved, as 10.1(c) | Attempts and refusal texts: as 10.1(c). The lead's lessons (result messages), MEMORY.md (org git), and its question to root (`msgs/`): not moved. |
| 10.5 S17-1b step-3 ids | Not moved | `reflect-sections/` from the lead prompts (markers unchanged). |
| 10.5 S17-1c | As 10.1(c) | |
| 10.5 S17-4a to S17-4c | Not moved | `progress` replies, `msgs/`, `run-logs/` (timing only), final `status`. |
| 10.5 S17-5 skill | Not moved | `skill-check.txt` (assistant). |
| 10.5 S17-6 prompt growth | Method not moved | Bytes between the unchanged markers. The lead prompts at `7d86c31` carry the longer V3 Files lines (A5, item 2). The comparison with E3's 20,240 / 29,926 / 29,195 bytes is reported as measured, with that difference named. |
| 10.6 cost | **Moved: the source of org-run credits** | 7.2's "org-run credits if the product or kiro records them (a read-only lookup)": kiro records them per run in the per-org kiro home, in `usage_summary.promptTurnSummaries[].usage` of the run's `messages.jsonl` (A3.2), summed per run and by model, with the injection window apart. Example: the `rev` run, 0.18298508298507465 credits, `elapsedTime` 26638 ms. If a run's session cannot be matched, that run is "not recorded", with the relative proxy of 7.2. Org run seconds (`# exit` lines) and assistant credits are not moved. |
| s1's tool-availability check (`s1/harness-failures/`, used to detect H8) | Moved | It was `Running: @hirearchy` lines per run. It is now P3 lines per run, plus `tool.call` events whose `actor` is the agent. |

Run-log patterns (Python `re`, multiline, on the run log's lines after `# ---- output ----`):
- **P1**, a `revise_playbook` call: `^\[tool\] @hirearchy/revise_playbook(?= |$)`
- **P2**, the end of that call: the next line matching `^\[tool (?:ok|failed)\] @hirearchy/revise_playbook(?= |$)`
- **P3**, any hirearchy call: `^\[tool\] @hirearchy/\w+`

On all 10 run logs of `/tmp/kirov3-live/org`, the P3 count per run equals that run's `tool.call` events (10 of 10, checked during this
step). P1 and P2 differ from P3 only by the tool name; on the same logs, P1 and P2 with `delegate` in place of `revise_playbook` find the
one `delegate` call and its `[tool ok]` line.

### A3.4 H8 evidence in V3 run logs (patterns only; H8 is unchanged)

H8's example "Mode ... not found" in an org run log is not expected at `7d86c31`: every run passes `--v3`, and the launcher refuses a run
whose first event is not a V3 `runStarted`.
The failure kinds H8 lists (engine, authentication, model service) show up as these lines. They come from `src/hirearchy/kiro/_launch.py`
at `7d86c31`.

- `# kiro: refused: the first event of kiro-cli was "<kind>", not "runStarted"`, or `# kiro: refused: kiro-cli started engine "<e>";
  hirearchy needs "v3"` (the engine);
- `# kiro: gave up after 60s: kiro-cli did not start the run (no "runStarted" event); without KIRO_API_KEY it may be waiting for a browser
  sign-in ...` (authentication hang);
- `# kiro: kiro-cli exited with code <N> before the run started` (the spike reads exit 3 as a failed `--require-mcp-startup` and exit 4 as
  an unloadable profile), `# kiro: cannot start <bin>: ...` or `# kiro: launcher error: ...`;
- `[run error] <stage>: <message>`. Two recorded real kiro streams (kiro-v3 report section 5: trimmed and secret-scanned) were rendered
  with the `7d86c31` renderer during this step:
  - `k5b.jsonl` (invalid key) gives `[run error] prompt: Access denied. Please check your authentication. ...`;
  - `p15b.jsonl` (MCP server failed) gives `[run error] init: these servers failed to start: hirearchy: Connection closed
    (--require-mcp-startup enabled)`.

  That last line is the V3 form of s1's failure: a run without its hirearchy server now stops instead of running without the tools.

No run log in `/tmp/kirov3-live` contains any of these lines: all 10 have exactly one `# kiro:` line, `# kiro: run started (engine v3)`.
Whether such a failure "changed the course" is decided by H8 as written.

## A4. Readiness refusals

**The rule.** A scheduler start in a stream that the readiness gate refuses because kiro-cli is unreachable or not usable, or not signed
in, is an **H8-type infrastructure failure**. This covers a start by the assistant's `start` call, by the assistant's shell, or by the
injection script's `start()`. Section 11's H8 applies to it as an "engine or infrastructure" failure. H8's condition ("those failures
changed the course: a task failed, blocked or stalled because of them") and section 11's handling are unchanged.

The covered reasons are the gate's own texts (`src/hirearchy/kiro/_readiness.py` at `7d86c31`):
- `kiro-cli is not usable: "<command>" did not answer within 2.5 s or could not be started (...: try again)`;
- `kiro-cli is not usable: "<command>" exited <code>: ...`;
- `kiro-cli cannot be checked: ...`;
- `... does not offer --v3, ... in "chat --help": ... upgrade kiro-cli`;
- `kiro-cli is not signed in for this organization's kiro home (...): set KIRO_API_KEY ...`.

Any other refusal reason is not classified by this amendment. Section 11 applies to it as written, and its text is recorded verbatim.
Examples of other reasons: a workspace, input or the organization placed against hirearchy's state dirs; configuration planted in the kiro
home; a relative `HIREARCHY_STATE_DIR`.

**How it shows.** The `start` tool does not run the gate. Its reply is still `scheduler started (pid N ...)`, and the started scheduler
then refuses before any run (`app/wire_cli.py` `LoopSchedulerRunner.run`). Then:
- `.runtime/scheduler.log`, after the `# --- scheduler started <UTC>Z: ...` header: `error: kiro-cli is not ready, no run was started:
  <reason>`. The scheduler's stdout and stderr go to that file.
- `.runtime/scheduler.exit`: `refused to start: kiro-cli is not ready: <reason>`.
- `status`, `progress` and root's `whoami` end with `scheduler: stopped (refused to start: kiro-cli is not ready: <reason>)`. `progress`
  adds `- open tasks do not move until it is started`. This stays until a scheduler starts.
- A `cli.command` event with `command` `run`, `ok` false and `error` `kiro-cli is not ready, no run was started: <reason>`.
- No run log, no `run.start` event.

Real example: live-verification step 6.
- `/tmp/kirov3-live/evidence/step6a.out`: `error: kiro-cli is not ready, no run was started: kiro-cli is not signed in for this
  organization's kiro home (/private/tmp/kirov3-live/state/kiro-home/kirov3-live-org-54c47d7d69341c23): set KIRO_API_KEY ...`.
- Event `cli-54583-1792685350754.jsonl`: `"kind":"cli.command","command":"run","ok":false,"error":"kiro-cli is not ready, no run was
  started: kiro-cli is not signed in ..."`.
- Run logs 9 before and 9 after.
- `status` and `progress` ended with the `refused to start` line.

That example is a shell `hirearchy run --once`. Through the `start` tool the same scheduler output goes to `.runtime/scheduler.log`. That
path was not observed live.

**The assistant's own reaction is product behaviour.** This covers a retried `start`, its `status`, `progress` or `whoami` calls, what it
tells Lena, or any workaround.
- It is recorded: call number, UTC time, arguments and reply verbatim.
- It is scored as observed. It is never itself an H1 or H8 failure.
- A retry that the gate refuses again is another readiness refusal under this rule.
- The facilitator never retries a start for the assistant (4.8).

Each refusal is recorded in `s<N>/harness-failures/readiness-<k>.txt` and in `run-log.md`:
- who started the scheduler, with the call and the time;
- the reason, verbatim;
- the `scheduler.log` lines, `scheduler.exit` and the `cli.command` event;
- the next `status` or `progress` reply the assistant received;
- the facilitator's H8 decision and the fact it rests on.

## A5. Agent-visible changes since `d85cc13`: context, not confounds

These three are part of the product under test at `7d86c31`. No harness step removes them, works around them or adjusts for them.
Observations are scored as observed, and the scorer may cite these changes where they explain a fact.

1. **Org agents run from an empty scratch cwd.** The cwd is `<state>/kiro-cwd/<org-id>/<agent-key>`, emptied before every run, and the
   run uses the org's own kiro home (A3.2). The cwd is no longer `S/org/<agent>`.
   - Agents are told to give kiro's tools absolute paths. They are told that `grep_search` and `file_search` cannot search the workspace.
   - 4.5's sentence "Their cwd is `S/org/<agent>`, inside the org's own git repo" describes `d85cc13`.
   - 4.5's rule is unchanged: org runs are product behaviour, they are not controlled, and the run step records what is observable.
   - Example: A3.1 row "Run cwd".
2. **The V3 built-in tool names in the Files guide.** Commit `c93e9b7`: `prompts/_files.py` and the `org_read`/`org_write` descriptions in
   `mcp_server/_tools_files.py`.
   - The Files lines of an agent's prompt name kiro's V3 ids: `read_file`, `list_directory`, `fs_write`, `str_replace`, `fs_append` and
     `delete_file`.
   - They name hirearchy's tools as `tool_load` / `tool_call` with `hirearchy::<name>` (`hirearchy::org_write`, `hirearchy::org_read`).
   - They name the scratch directory and the protected folders.
   - Example: the "Files:" block of `/tmp/kirov3-live/org/lead/runs/20261022T160045143176.log` (prompt lines 74 and after).
   - Root's tool surface, which the assistant sees, does not change: root keeps `read`/`write`.
3. **The stricter workspace protections.** Kiro's file tools now refuse:
   - writes to `.kiro/`, `.git/`, `.vscode/` and `AGENTS.md` anywhere in a workspace (rule 7);
   - writes outside the workspace (rule 6);
   - writes into the organization, unless the workspace is inside it (rule 4);
   - reads outside workspace, inputs and organization (rule 5).

   A charter with `read` but no `inputs` and no workspace reads only the organization. Unknown tool names and paths that cannot be
   confined fail the run closed. Example: live-verification step 4: 11 denials by rules 5, 5, 6, 4 and 7 (seven times), and the allowed
   writes `ok.txt` and `.gitignore`.

## A6. Unchanged

These are exactly as in `protocol.md`:
- the pass rules (section 8);
- the definitions (section 9) and the verdict values and aggregation (section 12), except that 12 now counts the streams of A2 and the
  deterministic run of A1;
- the models and L-MODEL (4.3);
- the assistant profile and its call (4.2, with the s1r name);
- the injection: text, md5s, budget, source, moment, mechanism, freezing (section 5; the freeze moves to s1r, A2);
- the caps (4.7);
- Lena's lines and their rules (sections 3 and 4.10);
- the ambient-context rules (4.5);
- the safety rules (4.8), including the list of profiles never to be deleted;
- the evidence list of section 7, plus the A3.2 copies;
- the invalidity rules H1 to H8 and their handling (section 11), plus the readiness rule of A4.
