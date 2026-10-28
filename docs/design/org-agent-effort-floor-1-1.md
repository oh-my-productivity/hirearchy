# Batch 1.1: the effort floor that kiro-cli does not always apply, and two load flakes

Brief: `docs/research/org-growth/phase-1/1-1-brief.md` (binding). Base: `main` at `5bbf295f`. Branch: `fix/org-agent-effort-floor`.
Paths are relative to the worktree; `EV` is `studies/P1-itemized-playbook/evidence`, `G0` is `studies/G0-noise-baseline/evidence`, `RES` is
`/Volumes/workspace/hirearchy/docs/research/org-growth` (untracked research of the main checkout).

## 0. Overview

The owner's floor (D-E4-9) is claude-sonnet-5.5 at effort `high` or better on every seat. The product passes `--effort high` on every org
run, but kiro-cli sometimes reports on its stderr that it could not apply it, and the run then goes on silently. The kept evidence shows
that this report is written during the engine's start, before the run's first tool line and before its first model response ends, in 73
of 73 runs that logged it. The launcher cannot see it today, because kiro's stderr goes straight to the run log. This design makes the
launcher read kiro's stderr, forward it to the log unchanged, and stop the whole run the moment that line appears. The scheduler then
gives the stopped run back with a run credit and starts it again, exactly as it already does for a throttled run (D-E4-6). That is the
manager's option (a). Items 2 and 3 are test-only hardenings of three tests that depend on scheduling; neither needs a product change.

The manager approved (a) as written on 2026-10-28 (`.agents/tasks/manager-decision-item1.md`): texts A-D and G, the cost, the declared
limits, and the bound of D-E4-6 (max_failures + 1 stopped launches in a row). The manager added three binding conditions. Section 2.14
maps each one to the design and its tests, and the plan must carry them:
1. the warning is matched by its stable prefix `failed to set effort`, whatever reason follows it;
2. kiro's stderr is drained for the whole run and forwarded to the run log byte for byte, in order;
3. the throttle credit, the refused start, the silence deadline and `max_failures` keep their behaviour and texts, and their existing
   tests stay unchanged.
Items 2 and 3 were approved as proposed.

This is iteration 2. It resolves the ten findings of the design review (`.agents/tasks/design-review.md`); section 9 answers each one.
Three of the fixes change what the manager approved: text E is reworded, declared limit 6 (a stop faked by an agent with `shell`) is
new, and the run log now places kiro's stderr lines where the launcher reads them. The manager approved all three before this design
was committed (section 9.3). The manager then closed the design loop after review 2 and made its ten findings binding amendments E1-E10;
section 10 lists each one and where it landed.

The technology stack is locked as it is: Python 3 standard library in the launcher (`os`, `select`, `subprocess`, `signal`, `re`), the
existing packages `kiro`, `scheduler`, `budget` and `kernel`, pytest. No new dependency.

## 1. Item 1: the investigation (kept evidence only, no live run)

### 1.1 Method

For each of the 429 org runs of P1 (`EV/<F1|I1|I2|F2|F3|I3>/run-logs/`) and the 241 of G0 (`G0/m{0,1}-s{1,2,3}/run-logs/`), I took the run
log, found its kiro session through the stream's `run-session-map.txt` (amendment 1 A3.2: `run <addr>@<stem> ... -> session <id>`), and
read `org-kiro-sessions/<hash>/<id>/session.json` and `messages.jsonl`. In the log I located, after `# ---- output ----`: the launcher's
`# kiro: run started` line, the warning, the first `[tool ...]` line (the launcher's rendering of the first tool event) and the first
`[INFO] [KRS] <-- GenerateAssistantResponseCommand done` line (kiro's own line when a model response has ended). In the session I took
the timestamps of `createdAt`, the `user` message, `turn_start` and the first `tool_call`, and `effortLevel`. The script was a throwaway
read-only reader in `/tmp`; nothing of it is committed.

### 1.2 Counts

| | P1 (6 streams) | G0 (6 streams) |
|---|---|---|
| org runs (logs = sessions) | 429 | 241 |
| logs with `[warn] failed to set effort 'high': model 'claude-sonnet-5.5' offers no effort levels` | 32 (F1 8, I1 7, I2 6, F2 4, F3 4, I3 3) | 41 |
| any other `failed to set effort` text in an org run | 0 | 0 |
| warned sessions that record an `effortLevel` | 0 of 32 | 0 of 41 |
| unwarned sessions that record `effortLevel: high` | 396 of 397 | 199 of 200 |
| unwarned sessions with no `effortLevel` | 1: I3 `lead@20261028T040906023860` (`EV/I3/run-session-map.txt:52`) | 1: m1-s1 `lead/reviewer@20261026T060718792191` (`G0/m1-s1/run-session-map.txt:44`) |

The warning is therefore an exact signal in this data: no unwarned run lacks it while missing `effortLevel`, except the two silent runs
above, and no run that recorded `high` logged it (0 of 595). The P1 figures match the gate (`EV/stage-1-gate.md:128-135`) and F-P1-13
(`studies/P1-itemized-playbook/STUDY.md:442-445`).

The assistant (root's own kiro session) logged the other wording once: `EV/F1/turn-23.stderr.txt:11`,
`[warn] failed to set effort 'high': the engine did not load its model list in time`. Its session records `effortLevel: high`
(`EV/stage-1-gate.md:131-132`).

### 1.3 When the warning appears

An example: `EV/F1/run-logs/lead-writer/20261027T193307448475.log`. Line 4 is the `# cmd:` line with `--model claude-sonnet-5.5 --effort
high`; line 146 is `# kiro: run started (engine v3)`; lines 147-157 are kiro's start lines on stderr, ending with
`fs.workflow.recipeCatalog.refreshShared.ok {"trigger":"startup"}`; line 158 is the warning; line 159 is the first tool line
(`[tool ok] Tool Load`); line 161 is the first `[KRS] ... done`. Its session `sess_92005d14-...` has no `effortLevel`; the run before it,
`lead@20261027T193227059734` (`EV/F1/run-session-map.txt:7`), has `effortLevel: high` and the same start lines without line 158.

Across all 73 warned runs (P1 and G0):
- the warning comes after `# kiro: run started` (73 of 73), as the line right after `recipeCatalog.refreshShared.ok` (73 of 73);
- it comes before the first `[tool ...]` line (73 of 73) and before the first `[KRS] ... done` line (73 of 73);
- it is the only extra line: the start of a warned log has 13-14 lines between `run started` and the first tool line, an unwarned one 12-13.

The first tool line of every kept run is read-only: 670 of 670 logs: 666 are `[tool ok] Tool Load` (642 of them
`{"tool_ids":["hirearchy::*"]}`, 24 a list of named hirearchy tools), 2 are `[tool] Read File` and 2 are `[tool] List Directory` (E2). So a
stop at the warning comes before any tool effect in every kept run.

The session timestamps time the turn, not the warning. The `user` message is stored a median 0.67-0.69 s after the session is created,
the turn starts about 0.01 s later, and the first tool call comes at least 1.46 s after the turn start in P1 (1.57 s in G0, 1.73 s in P1's
warned runs). kiro's stderr lines carry no time, so these figures say nothing about how long before the first tool call the warning was
written. Only the log order is known.

What the kept evidence cannot settle: whether the run's first model request had already been sent when kiro wrote the warning. The org
runs' raw stream-json was not kept (the launcher keeps only its rendering), and nothing records effort per request. The assistant's wording
("did not load its model list in time") says kiro-cli waits for the model list during session setup and then gives up, so the warning is
written at setup, before or as the prompt goes out. This design therefore counts a stopped launch as having spent at most its first model
request (2.11).

### 1.4 Whether the session then records an `effortLevel`

No: 0 of 73 warned sessions record one (1.2). A clean session records `effortLevel: high` next to `modelId` in `session.json`. The two
silent sessions also lack it, with no warning in their logs (`EV/I3/run-logs/lead/20261028T040906023860.log` and
`G0/m1-s1/run-logs/lead-reviewer/20261026T060718792191.log` both go from `recipeCatalog.refreshShared.ok` straight to the first `[KRS]`
line).

### 1.5 Whether the transcript or events show any effect

None can be seen:
- every warned run ended `[run finished] success (end_turn)` with exit 0, and kiro's `usage_summary` says `success` (73 of 73);
- every warned session has reasoning from `qdev::claude-sonnet-5.5` (73 of 73), and the median tool calls are 7 in both groups;
- the run events record nothing about effort (no `effort` key in `EV/F1/events/` or `EV/I1/events/`), and every `run.end` of F1 is `ok`;
- the size differences do not agree between the studies: P1 warned runs median 1.03 credits and 50.5 s against 0.91 and 36 s unwarned;
  G0 warned 0.94 credits and 38 s against 0.97 and 36 s.

One hint fits the race explanation without proving it: in G0, 2 of 41 warned runs waited 19.4 s and 27.5 s between the `user` message
and the turn start (`m1-s3` `lead/reviewer@20261026T083824738689`, `lead@20261026T090259980205`); no unwarned G0 run waited more than
0.78 s. The engine was busy at start in those two.

Which effort the model actually used in a warned run is recorded nowhere. The floor can only be held on what kiro-cli reports.

### 1.6 Repeats

The samples are too small to show clustering: in P1, 4 of the 30 warned runs that had a next org run in their stream were followed by
another warned run (13 %, base rate 7.5 %); in G0, 2 of 41 (5 %, base rate 17 %). A relaunch sets the effort in about 83-93 % of cases if
launches are independent, and in 87 % at P1's observed repeat rate.

### 1.7 What the launcher can observe, and when

- **At build** (`src/hirearchy/kiro/_runner.py:52-64`): `RunCommandBuilder.build` reads the org's effort, refuses one below the floor
  (`effort_floor_problem`, :53) and puts `--model <id> --effort <effort>` on the command (:63). The engine does not exist yet, so nothing
  here can know whether it will apply the effort.
- **Before the run starts** (`src/hirearchy/kiro/_launch.py:253-276`, `_wait_for_start`): the launcher reads kiro's stdout until the first
  JSON event, at most `START_DEADLINE` = 60 s (`kiro/api.py:44`), and checks that it is `runStarted` with `engine: v3` (`_decide`).
- **While it runs** (`_stream`, `_launch.py:279-306`): it renders stdout: tool calls, agent text, `runFinished`, `runError`. Every other
  session update, `config_option_update` among them, renders nothing (`_session_update`, :123-146).
- **kiro's stderr is not read.** `Popen(kiro, stdout=subprocess.PIPE)` at `_launch.py:364` lets kiro inherit the launcher's stderr, which
  is the run log. The warning reaches the log at once, and the launcher never sees it.
- **kiro-cli behaves the same with its stderr on a pipe.** The kiro-v3 probes ran the real kiro-cli 2.33.0 with
  `subprocess.run(..., capture_output=True)` (`RES/kiro-v3/research-raw/scripts/probe.py:31`), so its stdout and its stderr were both
  pipes. The H3 probe exited 0 (`RES/kiro-v3/research-raw/engine/probes/H3-upgrade-v3-require-mcp-streamjson.txt:3`) and wrote the same
  start lines as a run log, from `kas.server.starting` through `recipeCatalog.refreshShared.ok` to the first `[KRS] ... done` (same file,
  :85-96).
- **The stream may carry the effort.** Two kept V3 recordings with claude-sonnet-5.5 show `config_option_update` events with `effortLevel:
  high` after the model is set and before the first tool event (`RES/kiro-v3/research-raw/engine/probes/H3-upgrade-v3-require-mcp-streamjson.txt`
  lines 13 and 20, first tool event line 27; `.../K-v3native-perms.txt` lines 41 and 48, first event line 55). No warned run's raw stream
  was kept, so how the stream looks when the set fails is unknown.
- **After the run** the scheduler sees the launcher's exit code and the log (`RunSettlement.settle`, `scheduler/_reaper.py:64`).

### 1.8 Whether a pre-launch readiness step (c) could work

The evidence says no. Every run starts its own engine: `kas.server.starting` opens 670 of 670 kept run logs. A step run before the launch
is another kiro-cli process with its own engine, so it cannot load the model list of the run's engine. The readiness calls (`--version`,
`chat --help`, `whoami`, `kiro/_readiness.py:73-101`) start no chat engine. Nothing kept shows a command that loads or caches the model
list.

## 2. The choice for item 1: (a), stop at the warning and relaunch

### 2.1 Why (a)

- (a) is possible. The warning comes before the first tool line in 73 of 73 warned runs (its own time is not recorded, 1.3), and the first
  tool call of every kept run is read-only (670 of 670: 666 Tool Load, 4 reads), so a stop at the warning comes before any tool effect in
  every kept run. A launcher that reads kiro's stderr sees the line as soon as it is written, because `select` returns as soon as a pipe
  has data.
- (a) holds the floor. No run that kiro-cli reports below the floor does tool work after the report, and the relaunch starts a fresh
  engine, which sets the effort in about 83-93 % of cases (1.6).
- (b) would let a run below the floor finish and then need a new "valid seat" notion in status, observe and the event. The manager ranks
  it after (a), and (a) is possible.
- (c) has no support in the evidence (1.8).

Rejected ways to do (a):
- **Detect on the stream** (no `config_option_update` with a floor effort before the first agent event). It cannot be checked against a
  warned run (1.7). If clean runs differed from the two recordings, it would stop every run.
- **Merge kiro's stderr into its stdout pipe.** One pipe would make the order exact, but node writes larger than `PIPE_BUF` (512 bytes on
  macOS) are not atomic, so a stderr line could split a JSON event and corrupt the effect count of the throttle credit.
- **Stop kiro and keep the launcher alive** to return an exit code of its own, which no agent could forge (as exit 75 is for the
  throttle). The launcher shares its process group with kiro, kiro's engine and the MCP server, so it cannot kill that group without
  dying itself. A launcher that leads its group cannot move out of it (`setpgid` refuses a session leader). Killing kiro alone with
  SIGKILL can leave the engine running, and SIGTERM depends on how kiro-cli and its MCP server handle it, which nothing kept shows. Moving
  kiro into a group of its own would put it out of reach of the scheduler's timeout, retirement and shutdown kills, which signal the
  launcher's group (`processes/_spawn.py:38-45`, `scheduler/_reaper.py:42,48,100,106`). The stop therefore reuses the path that already
  ends a refused or silent run: the launcher kills its whole group, itself included (`_end_run`, `_launch.py:309-319`), and the scheduler
  sees exit -9. The cost of that choice is declared limit 6.

### 2.2 The launcher (`src/hirearchy/kiro/_launch.py`, standard library only)

New constants:
- `EFFORT_PREFIX = "failed to set effort"`: the stable start of kiro-cli's warning when it did not apply `--effort`, whatever reason
  follows it (manager's condition 1). The two kept reasons (kiro-cli 2.33.0 / KAS 0.66.48) are `'high': model '<id>' offers no effort
  levels` and `'high': the engine did not load its model list in time`. Any other reason is detected the same way.
- `EFFORT_LINE = re.compile(r"(?:\[[A-Za-z]{1,10}\] )?(" + re.escape(EFFORT_PREFIX) + r"\b.*)")`: a stderr line that starts with the prefix,
  either at once or after one level tag such as `[warn] `. It is used with `match`, so the prefix must stand at the start of the line.
- `EFFORT_MARK = "# kiro: effort not set, run stopped (kiro-cli: "`. The whole mark is `EFFORT_MARK + warning + "); tool effects: " +
  ("none" | n)`, where `warning` is kiro's line as it came, from the prefix on (group 1 of `EFFORT_LINE`).
- `CUT_WARNING = 300`, the longest `warning` kept (the two known lines are 78 and 75 characters from the prefix on);
  `ERR_LINE_LIMIT = 65536`, the longest stderr line scanned; `DRAIN_READS = 16`, the most stderr or stdout reads of one drain.

New pure function, exported: `effort_warning(line: str) -> str` returns kiro's warning as the mark quotes it, or `""` when `line` is not an
effort warning. It strips trailing whitespace, applies `EFFORT_LINE.match`, and returns group 1 with every `\r` removed, cut at
`CUT_WARNING`. Nothing else is changed, so the quote is kiro's text as it came. Both the launcher's scan and `effort_stop` (2.3) use it, so
the two can never disagree.

New data: `@dataclass class ErrPipe: fd: int; open: bool = True; partial: bytes = b""; warning: str = ""; skipping: bool = False` (`skipping`:
E5, the rest of an over-long line is not scanned).

**The drain rule (manager's condition 2).** From the `Popen` to the end of `_supervise`, every place where the launcher waits also reads
kiro's stderr while that pipe is open: the start wait, the stream, the exit wait, the stop and the reads before a closing `# kiro:` line.
Every byte read is written to fd 2 before anything else is done with it. Kiro therefore never blocks on a full stderr pipe, and the run
log gets kiro's stderr byte for byte, in the order kiro wrote it. Bytes can be lost in four cases only:
- kiro writes them after the launcher's last read and before its kill, on a refused, silent or stopped run;
- a background child writes them more than 2 s after kiro's exit;
- fd 2 refuses them (`OSError`: the log itself cannot be written);
- the launcher fails: `main`'s `except` path kills at once, and what is still in the pipe is not read.

**Order across the two pipes.** Kiro's stdout and stderr are two pipes with no common order, so the launcher logs kiro's stderr where it
reads it. Two rules place it:
- **Before the start** (`_wait_for_start`), stdout is handled first in each `select` pass, and a decision returns at once. So
  `# kiro: run started` comes before every stderr line that kiro writes after `runStarted`, such as the engine's start lines
  (`EV/F1/run-logs/lead-writer/20261027T193307448475.log:146-157`).
- **From the start on** (`_stream`), stdout bytes are rendered only after stderr has been drained, and the drain comes after those bytes
  were read: once before `rest` (the stdout read together with `runStarted`) is rendered, and after every stdout read. The drain is
  `_drain_err`: `select` with timeout 0, then `_read_err`, until the pipe is not readable, at most `DRAIN_READS` reads.

So a stderr line that kiro wrote before a stdout line is always logged before that line's rendering. This holds for a writer whose writes
reach the pipes in program order. It is what `test_each_launcher_line_comes_before_the_next_line_of_kiros_stderr` pins (E1 before Hello,
E2 before `[run finished]`), and that test stays unchanged. The test still depends on its own 0.5-s pauses for Hello before E2, as it
does today, and on nothing more.

The rule does not order the other direction. A stderr line that kiro wrote after a stdout line may be logged before that line's
rendering. A stderr line written before `runStarted` would be logged after `# kiro: run started`; none of the 670 kept logs has one. No
reader depends on either order:
- `throttled_without_effect` and `effort_stop` read only the order of the launcher's own lines and of kiro's warning. `_read_err`
  forwards the warning before the launcher writes the mark, by construction.
- Nothing in `src/` or `tests/` reads the position of `# kiro: run started` or of kiro's start lines, except the `in` checks of
  `tests/integration/test_real_kiro.py:220,244`.

The drain comes after the stdout read, not before it. A drain before the read leaves a window: stdout bytes that arrive between the drain
and the read can follow a stderr line written after the drain. E2 could then be logged after `[run finished]` when kiro writes the two
back to back. A drain after the read has no such window. Every stderr byte that kiro wrote before a stdout byte that was read is already
in the stderr pipe when the drain runs. A stderr line longer than one pipe buffer does not break this either: kiro cannot write the stdout
byte until the whole line is in the pipe, and what is left of it there fits in the drain's first read.

New functions:
- `_forward(data: bytes) -> None` writes `data` to fd 2 at once, all of it, ignoring `OSError` (as `emit` does for fd 1). In a run fd 1 and
  fd 2 are one open file (`processes/_spawn.py:54-56`: `stderr=subprocess.STDOUT`). So the launcher's lines and kiro's forwarded bytes
  land in the log in the order the launcher writes them.
- `_read_err(err: ErrPipe) -> None` reads up to 64 KB from `err.fd`. Empty means end of file: the remaining `partial` is scanned as a
  line and `err.open = False`. Otherwise it forwards the bytes, appends them to `partial`, splits off the complete lines and scans each. A
  `partial` longer than `ERR_LINE_LIMIT` is dropped from the scan (it was already forwarded): `partial = b""` and `skipping = True`. While
  `skipping`, the bytes up to and including the next `\n` are dropped from the scan, then `skipping = False`, so the tail of an over-long line
  is never scanned as a line of its own. Forwarding is unchanged (E5).
- Scanning a line: decode UTF-8 with replacement. If `err.warning` is empty, set `err.warning = effort_warning(line)`. Only the first
  warning counts; the scan never changes what was forwarded.
- `_drain_err(err: ErrPipe) -> None`: while `err.open` and `select([err.fd], [], [], 0)` says readable, `_read_err(err)`, at most
  `DRAIN_READS` times. Errors propagate, as a stdout read error does today.
- `_forward_ready(err: ErrPipe | None) -> None`: `_drain_err(err)` when `err` is given, ignoring `OSError` and `ValueError`, because it
  runs just before a closing line or a kill.
- `_last_output(fd: int, err: ErrPipe, state: RenderState, buffer: bytes) -> None`: the stop's last look at stdout. While
  `select([fd], [], [], 0)` says readable, at most `DRAIN_READS` times, it reads up to 64 KB, calls `_forward_ready(err)` and renders the
  complete lines. End of file ends it, and so do `OSError` and `ValueError`; the stop goes on. Every tool update that kiro wrote to
  stdout before its warning is in the pipe by then, so the mark counts it.

Changes to existing functions:
- `main`: `subprocess.Popen(kiro, stdout=subprocess.PIPE, stderr=subprocess.PIPE)`; `err = ErrPipe(proc.stderr.fileno())`; pass `err` to
  `_supervise`. The comment on the `Popen` line becomes "stdin (the prompt) is inherited; stderr is read and forwarded to fd 2 (the run
  log); same process group". The `except Exception` path still calls `_end_run(proc)` without `err`, so nothing on that path can raise
  again before the kill.
- `_wait_for_start(fd, err, limit)`: each `select` also watches `err.fd` while it is open. In a pass, stdout is handled first, as today,
  and a decision read from it (`started`, `refused`, `ended`) returns at once. Then, when stderr is readable, `_read_err(err)`; when
  `err.warning` is then set, it copies the buffered non-JSON output as the deadline path does and returns `Start("effort")`. The deadline,
  `COPY_LIMIT` (stdout only) and every text are unchanged.
- `_stream(proc, fd, err, rest) -> tuple[RenderState, bool, float | None]` returns the state, whether the run was stopped, and
  `exited_at`:
  0. `_drain_err(err)` once, before `rest` is rendered;
  1. render every complete stdout line in the buffer (as today);
  2. if `err.warning` is set and `proc.poll() is None`: `_last_output(...)`, then return `(state, True, None)` without calling `finish`;
  3. `exited_at` is `time.monotonic()` when `proc.poll()` is first seen not `None`; the loop stops `DRAIN_SECONDS` (2 s) after it, as today;
  4. the loop stops when both stdout and stderr have reached end of file;
  5. `select` on stdout (while open) and stderr (while open), `SLICE_SECONDS`. When stdout is readable: read up to 64 KB, then
     `_drain_err(err)`, then add the bytes to the buffer (step 1 renders them). Stdout's end of file marks it closed instead of ending the
     loop, so kiro's last stderr lines are still forwarded. When only stderr is readable: `_read_err(err)`.
  After the loop it renders the rest and the `finish` lines as today, and returns `(state, False, exited_at)`.
- `_exit_code(proc, err, exited_at: float | None = None)`: while stderr is open, it sets `exited_at` when `proc.poll()` is first seen not
  `None` (if `_stream` did not), stops `DRAIN_SECONDS` after `exited_at`, and otherwise waits on stderr with `select` (at most
  `SLICE_SECONDS`, and no later than the end of that window) and calls `_read_err`. Then `proc.wait()` and today's mapping. The rule: the
  launcher reads kiro's output for at most 2 s after it sees kiro exit, in total across `_stream` and `_exit_code`. Without this loop, a
  kiro that fills the 64 KB stderr pipe while the launcher waits for it would block forever.
- `_end_run(proc, err=None)`: `_forward_ready(err)` first, then today's kill.
- `_supervise(proc, limit, err)`:
  - `Start("effort")`: `return _stop(proc, err, None)`;
  - `refused` and `gave_up`: `_forward_ready(err)`, then today's line, then `_end_run(proc, err)`. So kiro's stderr read so far comes
    before the launcher's closing line, as it does today;
  - `ended`: `code = _exit_code(proc, err)`, then as today;
  - after `run started`: `state, stopped, exited_at = _stream(...)`. If `stopped`, `return _stop(proc, err, state)`. Otherwise it closes
    stdout, takes `code = _exit_code(proc, err, exited_at)`, and goes on as today.
- New `_stop(proc, err, state) -> int`: `_forward_ready(err)`; emit the `_flush(state)` lines (an unfinished agent line); emit the mark with
  `state.effects` (`none` when 0 or when there is no state); return `_end_run(proc, err)`.

In the scheduler's runs the launcher leads its process group (`processes/_spawn.py:56`, `start_new_session=True`). The stop therefore
kills kiro, its MCP server and the launcher together, and the scheduler sees exit -9, as for a refused or silent run today. When the
launcher does not lead its group (only in tests), `_end_run` kills kiro alone and returns 1.

### 2.3 The verdict and its second check (`_launch.py`, exported by `kiro/api.py`)

The verdict is **exit -9 that the scheduler did not cause** (`not run.killed`). Unlike exit 75, it is not exclusive to the launcher: any
SIGKILL of the launcher gives it, including one sent by the agent's own `shell` tool. The mark is its second check. Together they hold
against everything except an agent with `shell` that fakes both (declared limit 6). Exit 75 stays the throttle's verdict, which no agent
can produce (0a.2 design 9.1, DR-44). The effort stop cannot have such a verdict, because the stop must kill the launcher's own process
group (2.1).

```python
@dataclass(frozen=True)
class EffortStop:
    warning: str  # kiro's warning from the prefix on, as the mark quotes it
    effects: int  # tool effects before the stop; 0 = none

def effort_stop(tail: str) -> EffortStop | None: ...
```

`effort_stop` takes the lines before the last line that starts with `# exit ` (all lines when there is none). The last line starting with
`# kiro:` must start with `EFFORT_MARK` and end with `); tool effects: none` or `); tool effects: <digits>` (`re.compile(r"\); tool
effects: (none|[0-9]+)$")`). Some line before it must give a non-empty `effort_warning(line)` (any reason after the prefix). Then the
result is `EffortStop(warning=<text between EFFORT_MARK and the match>, effects=0 for "none", else the number)`; otherwise `None`. It never
raises. `kiro/api.py` imports `EFFORT_PREFIX`, `EffortStop`, `effort_stop` and `effort_warning` from `._launch` and adds them to
`__all__`; `kiro/__init__.py` re-exports them (R1).

### 2.4 The scheduler (`src/hirearchy/scheduler/`)

New private port in `_ports.py`:

```python
class EffortStops(Protocol):
    def stop_of(self, run: RunRecord) -> EffortStop | None:
        """The launcher's stop of a run whose kiro-cli did not set its effort, as the end of its log records it; None when it records none
        or cannot be read (never raises)."""
    def credit(self, run: RunRecord, stop: EffortStop) -> str:
        """Give back a stopped run that had no tool effect: "free" (the relaunch is no failure), "counted" (the run before it was credited
        too: not charged, but a failure) or "" (no credit: charged as today; never raises)."""
```

New `_effort.py`:
- `TAIL_BYTES, TAIL_LINES = 4096, 80`, as for the throttle. The warning is forwarded just before the mark, so normally both lie in the
  tail; when they do not, the run is charged (2.9).
- `OUTCOMES = {"free": "not charged, relaunched", "counted": "not charged, counted as a failure", "": "charged as a failed run"}`.
- `effort_text(stop, kind) -> str` returns `f"effort not set: run stopped, {OUTCOMES[kind]} (kiro-cli: {stop.warning}; tool effects:
  {'none' if stop.effects == 0 else stop.effects})"`. The outcome comes first because observe cuts a run's error at 120 characters
  (`observability/_render.py:55`).
- `class CreditingEffortStops(EffortStops)` with `(logs: RunLogReader, mail: MailboxReader, delivery: MessageDelivery, console: Console)`:
  - `stop_of(run)` returns `effort_stop(self._logs.tail(run.log, TAIL_BYTES, TAIL_LINES)[0])`. On `OSError` or `OrgError` it says
    `{addr}: run log not read for the effort check: {error}` and returns `None`.
  - `credit(run, stop)` returns `""` when `stop.effects > 0`. Otherwise it returns `return_run(run, self._logs, self._mail, self._delivery,
    effort_credit(run.addr, run.log.stem))`. On `OSError` or `OrgError` it says `{addr}: effort credit not given: {error}` and returns
    `""`.

New `_credit.py` with `return_run(run, logs, mail, delivery, note) -> str`. These are steps 2-4 of the throttle credit (0a.2 design 9.2),
moved out of `CreditingThrottles._credit` (`_throttle.py:38-45`) so both credits share them:
- `""` when a message in `mail.sent(run.addr)` has an id whose first 21 characters are at or after the stem's;
- otherwise `"counted"` when the log just before `run.log` in `logs.files(addr)` is in `credited_stems(mail.received(addr))`, else `"free"`;
- the note is delivered last, so `""` always means no credit exists.

`CreditingThrottles._credit` keeps its tail check and then returns `return_run(..., run_credit(run.addr, stem))`. This is a pure move in the
REFACTOR step of its commit: the throttle's console texts, its note, its `free`/`counted`/`""` results and its order of reads stay as they
are, and `scheduler/tests/test_throttle.py` and `scheduler/tests/test_loop_throttle.py` stay unchanged and green (manager's condition 3).

`_reaper.py:RunSettlement` takes a ninth collaborator, `efforts: EffortStops`. In `settle`, after the retired-agent branch and after
`self._batches.end(addr, ok)`:

```python
stop = self._efforts.stop_of(run) if code == -signal.SIGKILL and not run.killed else None
if stop is None:
    ...  # today's lines: events.ended(run, code, exit.why), then cleared / _failed (the throttle path is untouched)
else:
    kind = self._efforts.credit(run, stop)
    self._events.ended(run, code, effort_text(stop, kind))
    self._console.say(f"{addr}: run stopped because kiro-cli did not set its effort: {OUTCOMES[kind]}")
    if kind != "free":
        self._failures.failed(addr, run.log, run.traces)
# the snapshot commit, as today
```

The credit is delivered before the `run.end` event, so the event can state the outcome. The throttle keeps its order. `_assembly.py:90`
passes `CreditingEffortStops(p.log_reader, p.mail, p.delivery, console)`. `scheduler/testing.py` gains `ScriptedEffortStops(stop=None,
kind="")`, which records the runs it was asked about and the ones it credited.

Every path other than a recognised effort stop is today's code, line for line: exit 0, the retired agent, a timeout or retirement kill
(`run.killed`), exit 75 and its throttle credit, any other failure, and -9 without the mark (a refused or silent start, a launcher error).
The one edit that condition 3's tests see is a construction detail. The shared helper `settlement(w, throttles=None)` in
`scheduler/tests/test_reaper_parts.py:76-78` gains the keyword `efforts: EffortStops | None = None` and passes `efforts or
ScriptedEffortStops()`, which recognises no stop. No existing test function and no assertion in that file changes.

### 2.5 The note (`src/hirearchy/budget/_credit.py`, exported by `budget/api.py`)

`effort_credit(addr, stem) -> Message` has the same fields and title as `run_credit` (`sender=RUNTIME, type="note", budget=1, wake=False,
title=run_credit_title(addr, stem)`) and its own body (2.10, text C). The title makes it a credit for `kernel.credited_stems` and
`is_run_credit`, so nothing else changes:
- the case run counts leave the stopped run out (`reflection/_runs.py:28`), and so do the progress counts (`progress/_counts.py:26`);
- `check`'s budget equation counts it as credited;
- observability still counts the run, because it ran.

### 2.6 Error handling

| Operation | Failure | Recoverable | What the caller gets | Logged |
|---|---|---|---|---|
| Launcher: read kiro's stderr in the start wait, the stream or the exit wait | `OSError` | no: it propagates to `main`'s `except Exception`, as a stdout read error does today | `# kiro: launcher error: ...`, the run is killed (exit -9) | that line, in the run log |
| Launcher: forward to fd 2 | `OSError` | yes, ignored (as `emit`) | nothing | no |
| Launcher: the reads of a stop and before a closing `# kiro:` line (`_forward_ready`, `_last_output`) | `OSError`, `ValueError` | yes, ignored | the stop or the closing line goes on | no |
| Launcher: the kill | `OSError` of `killpg` | yes, today's fallback `proc.kill()` | exit -9 (leader) or 1 | the mark is already written |
| Scheduler: read the tail | `OSError`, `OrgError` | yes: no stop is recognised and the run takes today's failure path (charged) | `None` | console `{addr}: run log not read for the effort check: {error}` |
| Scheduler: mail reads, log listing | `OSError`, `OrgError` | yes: no credit, charged | `""` | console `{addr}: effort credit not given: {error}` |
| Scheduler: deliver the note | `OSError`, `OrgError` | yes: no note was written (the delivery writes last), charged | `""` | the same console line |
| Count the failure, pause at `max_failures` | as today | as today | as today | as today |

### 2.7 Validation of external input

- **kiro's stderr** (untrusted bytes): every byte is forwarded to the log whatever it is, before any scan. For the scan, a line is decoded
  as UTF-8 with replacement, and only a line of at most 64 KB is scanned. It counts when `effort_warning` finds the prefix
  `failed to set effort` (case-sensitive, followed by a word boundary) at the start of the line, either at once or after one level tag of
  1-10 letters in brackets and a space (`[warn] `). Any reason after the prefix counts. The quote is kiro's text from the prefix on, without
  trailing whitespace and `\r`, cut at 300 characters. Only the first such line acts.
- **The run log's tail** (written by the launcher, kiro and, through agent text or an agent's shell, the agent): `effort_stop`'s rules
  (2.3). Anything else is `None`, and the run is charged as today.
- **The effort value**: checked at build by the existing floor (`_runner.py:53`). Detection does not depend on it.

### 2.8 Invariants and who enforces them

- **A run that kiro-cli reports below the floor does no tool work after the report.** Owner: the launcher. It is the only process that
  sees kiro's stderr while the run goes on, and the only one that can end the run before the agent acts.
- **A launch is credited only on the launcher's verdict and its mark.** Owner: `RunSettlement` and `CreditingEffortStops`. They require
  exit -9 that the scheduler did not cause, the mark as the last `# kiro:` line with `tool effects: none` and kiro's warning before it,
  and no message sent by the run. Fail safe: when in doubt, the run is charged. An agent with `shell` can fake both the exit and the mark
  (limit 6), so the invariant holds for agents without `shell`.
- **A credited launch is not charged anywhere.** Owner: `kernel.credited_stems`, the single definition that budget, reflection, progress
  and the conservation check already read.
- **Relaunches are bounded.** Owner: the existing failure counter (`CountingFailures` and `max_failures`), so this design adds no
  setting.

### 2.9 Edge and zero cases

| Case | What happens |
|---|---|
| The relaunch gets the warning again | It is stopped again. Its credit is `counted`, so it is not charged but it is a failure. Every later stop in a row is also `counted`. With `max_failures` = 3 (the default) a streak is at most 4 stopped launches (1 free, 3 counted); then the agent is paused and its parent and root get the existing "keeps failing" notice. With `max_failures` = 0 the first counted stop pauses it (the existing rule). At G0's rate (17 %), 4 in a row is about 0.08 %. Its note C still says 'the run is started again', as the throttle note does. The agent runs again once it is resumed (E9). |
| The warning comes before `runStarted` | The same stop, `tool effects: none`, and no `# kiro: run started` line (never seen: 0 of 73). |
| The warning comes after a tool effect that kiro reported | The run is stopped anyway, because the floor beats the work. The mark says `tool effects: <n>`, there is no credit, and the run is charged and counted like any failed run; its messages go back to the inbox and the existing failure rule retries it. Never seen: 0 of 73. |
| A tool effect that kiro reports only after its warning | Possible only if the tool ran but kiro wrote its completed update after the warning. An update that kiro writes after the launcher's last stdout read, or does not write before the kill, is not counted, and the run is credited. Every update written before the warning is counted (`_last_output`), and so is one written after it that reaches the pipe before that last read (E4). In the kept runs the warning always came before the first tool line, and that call was read-only (1.3). A hirearchy effect that sends mail is caught by the mail check. |
| The warning is read after kiro exited, or in `_exit_code` | It is not acted on, because nothing is left to stop. The line stays in the log, and the run ends by today's rules. Never seen. |
| A stderr line contains the prefix but does not start with it (after an optional level tag) | No stop. |
| The prefix is followed by a reason never seen before | The same stop; the mark and the event quote the new reason as it came. |
| kiro writes more than a pipe buffer (64 KiB) to stderr, at any point of the run | It is read as it comes (the drain rule, 2.2), so kiro never blocks on it, and the log gets every byte in kiro's order. |
| kiro writes more than 4 KB or 80 lines between its warning and the end of the run | The stop is not recognised, because `effort_stop` needs the warning and the mark in the last 4 KB / 80 lines. The run is charged and counted as today. Never seen: kiro writes about 12 start lines in all, and the warning comes last. |
| No warning, no `effortLevel` (2 of 670 kept runs) | Not detected: declared limit 2.12. |
| A later kiro-cli drops or rewords the prefix `failed to set effort` | Not detected: the run goes on as today. Declared limit 2.12. |
| The run sent a message before the stop (race) | No credit, charged, counted: the existing belt-and-braces check. |
| An agent with `shell` fakes the warning and the mark and SIGKILLs its own launcher | Credited if it sent no mail: declared limit 6. |
| The scheduler's `--max-runs` cap is reached by the stopped launch | The messages wait in the inbox for the next scheduler, as for a throttled run. |
| The scheduler dies after the stop and before it settles the run | The next scheduler redelivers its batch (`run.orphan`, `redelivered`, `scheduler/_orphans.py:61-63`). No credit is given and the run is charged, as for a throttled run (E8). |
| The agent is retired during the run | Today's retired branch runs first; no credit is given. |
| A timeout, retirement or shutdown kill | `run.killed`: not an effort stop. |
| A refused or silent start, or a launcher error (also exit -9) | The tail holds no effort mark, so the run takes today's path. If its log cannot be read, line E (`run log not read for the effort check`) is said and the run takes today's path. |
| The launcher does not lead its group (tests only) | Exit 1: not read as an effort stop, charged as today. |
| A background process keeps kiro's stderr open after kiro exits | The launcher stops reading 2 s after it sees kiro exit, counted once across `_stream` and `_exit_code`, as for stdout today. Later writes get `EPIPE` instead of reaching the log. |
| kiro writes a stderr line just after a stdout line | The stderr line may be logged before that stdout line's rendering (the order rule, 2.2). Nothing reads that order. |
| The assistant's own session | Out of scope (2.12). |

### 2.10 User-visible texts (exact)

| Id | Where | Text |
|---|---|---|
| A | run log, the launcher's mark | `# kiro: effort not set, run stopped (kiro-cli: failed to set effort 'high': model 'claude-sonnet-5.5' offers no effort levels); tool effects: none` (or `...; tool effects: 2`). The text after `kiro-cli: ` is kiro's line as it came, from the prefix on; with the other known reason it reads `(kiro-cli: failed to set effort 'high': the engine did not load its model list in time)`. It follows kiro's own warning line, which the log already shows today. The run log then closes with `# exit -9 after <n>s`. |
| B1 | `run.end` event `error` (observe's traces and events, the dashboard) | `effort not set: run stopped, not charged, relaunched (kiro-cli: failed to set effort 'high': model 'claude-sonnet-5.5' offers no effort levels; tool effects: none)`; the quote is the same as in A |
| B2 | same, a repeat in a row | `effort not set: run stopped, not charged, counted as a failure (kiro-cli: ...; tool effects: none)` |
| B3 | same, no credit | `effort not set: run stopped, charged as a failed run (kiro-cli: ...; tool effects: <none or n>)` |
| C | the credit note to the agent, title `run credit <addr>@<stem>` | `Your run <addr>@<stem> was stopped before any tool effect because kiro-cli did not set the effort this organization asks for, so it is not charged: this note returns its run. Your messages are back in your inbox; the run is started again.` |
| D | scheduler output (`scheduler.log`) | `<addr>: run stopped because kiro-cli did not set its effort: not charged, relaunched` (B1), `...: not charged, counted as a failure` (B2), `...: charged as a failed run` (B3) |
| E | scheduler output, errors | `<addr>: run log not read for the effort check: <error>` (asked for every exit -9 that the scheduler did not cause, so it can also name a refused or silent start), `<addr>: effort credit not given: <error>` |
| F | existing, unchanged | for B2 and B3: `<addr>: run failed (<n> in a row), log: <path>` and the `agent.failure` event; at `max_failures`, the pause and the "keeps failing" notices |
| G | README, "Agent runs (the scheduler)" paragraph (after the throttle sentence, `README.md:633-634`) | `When kiro-cli says on its stderr that it could not set the run's effort (a line beginning "failed to set effort", such as "[warn] failed to set effort 'high': ..."), the launcher stops the whole run at once and writes "# kiro: effort not set, run stopped (kiro-cli: ...); tool effects: none"; the scheduler gives a run stopped before any tool effect back with a run credit and starts it again, like a throttled run.` |

`status`, `progress`, `whoami`, ROOT_INSTRUCTIONS and SKILL.md show nothing new. The `run.end` event's fields and the event schema are
unchanged; only its `error` string is new.

### 2.11 Cost effects

- **Budget (runs):** a stopped launch with no tool effect costs nothing. Its credit note returns the run, and the case totals, the
  overspend warning and `runs n of m` leave it out. A stop after a tool effect is charged one run, like any failed run. Observability's run
  counts and failure rates include stopped launches, because they ran. `health` counts a stopped launch as a failed run: its `(+M failed)`
  count includes it, and its efficiency flags leave it out, as for a credited throttle (`health/_render.py:37`, `health/_analyzer.py:59-62`;
  E7).
- **The user's Kiro credits:** each stopped launch pays for an engine start (no model credits) and at most one model request cut off at its
  start. P1 averaged 0.21 credits per request (430.38 credits over 2,053 requests) and G0 0.22 (252.12 over 1,131). Whether Kiro bills a
  request cut off this way is not recorded. The relaunch costs what the original run would have cost anyway. Upper bound at the kept rates:
  P1's 32 stops would have added at most about 6.7 credits to its 430 (1.6 %), G0's 41 at most about 9.1 to its 252 (3.6 %).
- **Time:** each stop wastes about one engine start (a median 10.8 s from the launcher's start to the session in P1), plus the wait for the
  next scheduler pass.
- **Rate:** 7.5 % (P1) to 17 % (G0) of org launches, judging by the kept studies.
- **A faked stop (limit 6):** none in the kept evidence. The run budget of an agent with `shell` that fakes stops on purpose is bounded as
  limit 6 says; its Kiro credits are spent either way.

### 2.12 Declared limits

1. **The assistant's own chat session is out of scope.** The user's kiro starts it and the product does not launch it (F1 turn 23's
   warning). Nothing in this batch reads or stops it.
2. **A silent miss is not detected.** A run whose session records no `effortLevel` and whose kiro-cli wrote no warning (2 of 670 kept
   runs) gives the launcher nothing to act on. Backlog: compare the session store's `effortLevel` after the run.
3. **Detection rests on one prefix.** It needs a kiro-cli stderr line that begins with `failed to set effort` (after an optional level tag
   such as `[warn] `), as kiro-cli 2.33.0 / KAS 0.66.48 writes it. The reason after the prefix may be anything. A kiro-cli that drops or
   rewords the prefix turns detection off without a sign.
4. **The effort the model used is not recorded** by kiro. The floor is held on what kiro-cli reports.
5. **The price of a cut-off request is unknown** (2.11).
6. **An agent with `shell` can fake an effort stop.** The verdict is exit -9, and any SIGKILL of the launcher gives it. An agent whose
   charter grants `shell` (`kiro/api.py:42`) can put a forged warning and mark in its run log and then SIGKILL its own launcher, for
   example with `kill -9 0`. It can print the two lines as agent text, which the launcher renders verbatim (`render_line`), or write them
   into the log from its shell (`ORG_ROOT` and `ORG_AGENT` are in its environment, `kiro/_runner.py:67`). Such a run is credited if it
   sent no mail.
   - In a row, the first such run is free and each repeat is counted, so a streak ends in the existing pause after max_failures + 1
     uncharged runs.
   - Between normal runs, which clear the count, such an agent can leave up to max_failures of every max_failures + 1 runs uncharged
     (3 of 4 at the default).
   - A run that sent mail is still charged.
   - An agent without `shell` has no tool that sends a signal, so it cannot produce the verdict.

   This gives an agent with `shell` no new power. Today it can already write a credit note into its own mailbox, because a mailbox is
   plain files under the org root, and `_credited_stem` trusts fields that a file carries (`kernel/_message.py:236-240`). Closing the path
   needs a verdict the agent cannot reach, and a stop that kills the launcher's own group cannot give one (2.1). Backlog, together with
   the forged credit note.

### 2.13 Files

`src/hirearchy/kiro/_launch.py`, `kiro/api.py`, `kiro/__init__.py`; `src/hirearchy/scheduler/_ports.py`, `_effort.py` (new), `_credit.py`
(new), `_throttle.py`, `_reaper.py`, `_assembly.py`, `testing.py`; `src/hirearchy/budget/_credit.py`, `budget/api.py`,
`budget/__init__.py`; `tests/testkit/fake_agent.py` (`FAKE_EFFORT_STOP_RUNS`, 5); `README.md` (text G); `ARCHITECTURE.md`, in the docs
commit (E6), with three edits:
- `:1292`: the new exports `EFFORT_PREFIX`, `EffortStop`, `effort_stop` and `effort_warning`;
- `:1293-1294`: the launcher reads kiro's stderr, forwards it to fd 2 and stops the run at the warning (mark A, exit -9);
- `:1361`: `EffortStops` (`CreditingEffortStops(logs, mail, delivery, console)`), asked by `RunSettlement` on exit -9 of a run that was
  not killed, with `return_run` shared with the throttle credit.

No golden is expected to change:
the stub kiro-cli and the fake agent write nothing to stderr unless a test asks, and no golden holds a `run.end` error. Any golden diff is
a finding, not a regeneration.

### 2.14 The manager's binding conditions, and where each is held

| Condition (`.agents/tasks/manager-decision-item1.md`) | Held by | Tests (5) |
|---|---|---|
| 1. Match the stable prefix `failed to set effort` for any reason, including `the engine did not load its model list in time`. A and B quote kiro-cli's line as it came. The wording limit names the prefix only. | `EFFORT_PREFIX`, `EFFORT_LINE` and `effort_warning` (2.2), used by both the launcher's scan and `effort_stop` (2.3). The quote is group 1, kiro's text from the prefix on. Limit 3 of 2.12 names the prefix only. | the prefix pin; `effort_warning` with both known reasons, an unknown reason, no tag and another tag; the launcher stops a run on each of the two known reasons; `effort_stop` with both reasons |
| 2. Drain stderr until the process ends, so a full pipe never stalls kiro; forward every byte to the run log, in order. | The drain rule (2.2): `_wait_for_start`, `_stream`, `_exit_code`, `_last_output` and `_forward_ready` all read stderr while it is open, and `_read_err` forwards before it scans. Kiro's bytes keep kiro's order; their place among the launcher's lines follows the order rule of 2.2. | more than 64 KiB of stderr before and after `runStarted`, with the run completing and the log byte-complete and in order; the same before an early end; kiro's stderr forwarded byte for byte (a last line without a newline included); a background child holding stderr |
| 3. The throttle credit, the refused start, the silence deadline and `max_failures` keep their behaviour and texts; their existing tests stay unchanged. | The launcher's `refused`, `gave_up`, `ended` and throttle branches keep their texts and exit codes, and only gain the stderr reads. `RunSettlement` runs today's code for every exit that is not a recognised effort stop (2.4). `return_run` is a pure move (2.4). The failure counter and `PausingEscalation` are untouched. | listed in 5, "Existing tests that stay unchanged" |

Two edits touch files of condition 3's tests, and neither changes what they check:
- The shared construction helper of `scheduler/tests/test_reaper_parts.py` gains one keyword (2.4).
- Item 2, which the brief orders and the manager approved, changes how the silence and spinner tests find the killed process (3). Their
  checks on the exit code, the `# kiro: gave up after 1s: ...` text, the output lines and "nothing of the run is left alive" stay.

## 3. Item 2: `test_silence_gives_up_and_kills_the_run[group-leader]`

**The failure.** Phase 1's full check (`RES/phase-1/build/check-final.log:252-281`): `read_pid` raised "the fake kiro did not write its
pid" (`src/hirearchy/kiro/tests/test_launch.py:296`, called at :320). The test passed 5 of 5 alone
(`RES/phase-1/build/manager-decision-fv1-flake.md`). The suite runs in one process (no xdist in `pyproject.toml`), so "load" here means
the machine's.

**The cause.** The fake is `#!/bin/sh`, `cd "$(dirname "$0")"`, `echo $$ > pid`, `exec sleep 30` (`fake`, :249-253; the test, :315-320).
With `deadline=1` the launcher gives up after 1 s and, as the group leader, SIGKILLs its whole group (`_end_run`, `_launch.py:309-319`).
When the shell has not yet written its pid by then (its first line forks `dirname`), it dies without writing it, and `read_pid` waits 2 s
for a file that will never exist. The assertion depends on the fake being scheduled within 1 s.

**No product race.** The launcher did what it must: no `runStarted` within the deadline, so it gave up and killed the run's group. The kill
reaches kiro whatever kiro has done by then. The race lies only in how the test finds kiro's pid. The `not-leader` parameter has the same
race and has not failed yet.

**The fix (test-only, `src/hirearchy/kiro/tests/test_launch.py`).** Check that the run's whole process group is gone, which does not need
the fake to write anything:

```python
WRAPPER = "import subprocess, sys; sys.exit(subprocess.call(sys.argv[1:]))"  # leads the group, so the launcher does not

def launch_in_group(
    tmp_path: Path, body: str, deadline: float, leader: bool, timeout: float = 20
) -> tuple[int, list[str], str, int]:
    """(exit code, the launcher's stdout lines, its stderr text, the process group of the run): the launcher in a session of its own, as its
    group's leader (as the scheduler starts it) or, with ``leader`` False, as the only child of a wrapper that leads the group."""
    argv = [sys.executable, "-I", "-S", str(LAUNCHER), "--start-deadline", f"{deadline:g}", "--", str(fake(tmp_path, body))]
    if not leader:
        argv = [sys.executable, "-I", "-S", "-c", WRAPPER, *argv]
    proc = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
    try:
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
        proc.communicate()
        raise
    return proc.returncode, out.decode().splitlines(), err.decode(), proc.pid

def group_gone(group: int, within: float = 20.0) -> bool:
    """No process is left in ``group`` (polled every 50 ms, at most ``within`` seconds)."""
    end = time.monotonic() + within
    while time.monotonic() < end:
        try:
            os.killpg(group, 0)
        except ProcessLookupError:
            return True
        except PermissionError:  # the id now names another user's group: ours has ended
            return True
        time.sleep(0.05)
    return False
```

- `test_silence_gives_up_and_kills_the_run(tmp_path, session)`: body `exec sleep 30\n`; `code, out, _, group = launch_in_group(tmp_path,
  body, deadline=1, leader=session)`. The assertions on `code` (`-9 if session else 1`) and on `out` stay as they are, and `assert
  gone(read_pid(tmp_path))` becomes `assert group_gone(group)`.
- `test_a_spinner_without_a_newline_is_given_up_on_the_same_way` has the same pid race. Its pid check gets the same change, and its body
  loses `echo $$ > pid`. Its check that the spinner text reached the log still needs the shell to print within the 1-s deadline. That
  check has never failed in a kept log and stays as it is (out of the brief's scope).
- New `test_a_kiro_killed_before_its_first_line_leaves_no_process` (group leader only) reproduces the flake on purpose: body `sleep 15\necho
  $$ > pid\nexec sleep 30\n`, deadline 1 (E3: the kill still comes at about 1 s, so the run's length does not change, and
  `launch_in_group`'s 20-s timeout still bounds a failing kill). It asserts `code == -9`, that `tmp_path / "pid"` does not exist (the kill
  came first), and `group_gone(group)`. The old `read_pid` assertion fails on this body every time; the new one passes. It is leader-only
  because in the `not-leader` case the launcher kills only its child, so the shell's `sleep 15` child would outlive it.
- `read_pid` and `gone` stay for the tests whose fake writes its pid before the event the launcher acts on (`test_engine_v2_is_refused`,
  `test_a_first_event_that_is_not_run_started_is_refused`).

A PID reused as a new group leader within the polling window would make `group_gone` wait; macOS assigns PIDs in increasing order, so this
is not expected.

## 4. Item 3: the 2.5-s `READINESS_TIMEOUT`

**The search.** I searched `RES/*/` (every phase's check logs, verification and validation files), `/Volumes/workspace/hirearchy/.agents/tasks`
and `.worktrees/*/.agents/tasks` for `did not answer within`, `kiro-cli is not ready`, `kiro-cli is not usable` and failures that name
readiness:
1. `src/hirearchy/scheduler/tests/test_exit_assistant.py::test_a_real_until_done_scheduler_process_exits_by_itself`: 1 of 5 full checks
   of the kiro-v3 branch. The child scheduler refused: `"kiro-cli --version" did not answer within 2.5 s or could not be started`
   (`RES/kiro-v3/final-check-run2-failed.log:205-249`, `RES/kiro-v3/final-check.md:38-39`, `RES/kiro-v3/final-validation.json`).
2. `src/hirearchy/app/tests/test_wire_cli.py::test_the_scheduler_runner_runs_the_loop_until_there_is_nothing_to_do`: one FAST run of
   phase 0b, the same text (`RES/phase-0b/build/verification.md:559`); the file passed when re-run alone.
3. `RES/phase-0a4/c1-reproduction.md:62` is a different failure: a live sandbox whose kiro-cli could not launch `kiro-cli-chat`. That is
   an exit with an error, not a timeout, so it is out of this item.

Both flakes call the `isolated_kiro` stub, a `/bin/sh` script (`tests/testkit/fixtures.py:22-38`, written per test at :76-80), with 2.5 s
per call, and both failed on the first call (`--version`). `KiroCli.run` returns `None` for a timeout and for a failed start alike
(`kiro/api.py`, `KiroCli`), so the evidence does not say which one happened.

**The product value is not too tight.** The design measured a real kiro-cli at 9 ms for `--version`, 85 ms for `chat --help` and 0.3-0.8 s
for `whoami` (`docs/design/kiro-runtime-v3.md:633`, [P16d], [K5]). None of the 26 kept study scheduler logs (`studies/*/evidence/*/scheduler.log`)
shows a readiness refusal. The value does not tie in with item 1: the effort race happens inside each run's own engine (1.8), and no
readiness call starts one. **No product change is proposed**, so the manager's yes is not needed.

**The fix (test-only).** Neither test is about readiness. Each now runs with kiro-cli declared ready through the existing seam, so it makes
no stub call that could time out. Each also proves that no readiness call was made (E1). Nothing else in either test calls kiro-cli:
readiness runs only in `LoopSchedulerRunner.run` (`app/wire_cli.py:228`), `--max-runs 0` starts no run, `ScrubbedLaunchEnvironment` passes
`KIRO_STUB_LOG` to the child (`daemon/_site.py:41-45`), and the stub writes each call's argv to that file (`tests/testkit/fixtures.py:23`).
- `test_wire_cli.py::test_the_scheduler_runner_runs_the_loop_until_there_is_nothing_to_do`: both `runner.run(...)` calls go inside `with
  wiring.overriding({RuntimeReadiness: FixedReadiness(None)}):`, the idiom of the file's `refuse` helper and of
  `test_a_ready_kiro_cli_starts_the_loop_and_leaves_no_marker` (:189-194). Every name of the override is already imported. After the two
  calls it asserts the stub log holds no `--version` line (the assertion below; `import os` is the file's one new import).
- `test_exit_assistant.py::test_a_real_until_done_scheduler_process_exits_by_itself` keeps a real scheduler process. Before `start`, the
  test reopens the runtime with `testkit.health_world.with_ports(org, {SchedulerCommand: FixedSchedulerCommand([sys.executable, "-c",
  READY_SCHEDULER, "--root", str(org.root), "run", "--max-runs", "0", "--until-done"])})`, the pattern of the daemon's `STAND_IN`
  (`daemon/testing.py:434-482`). `READY_SCHEDULER` is one command line, because the process inspector reads command lines line by line.
  It binds the context manager to a name for the life of the process (E1): an unbound `wiring.overriding(...).__enter__()` is freed at the
  end of its statement, Python closes its generator, and the `finally` of `wiring.overriding` (`app/wiring.py:72-86`) restores the empty
  overrides before `main` runs. Adjacent string literals keep it one line:

  ```python
  READY_SCHEDULER = (
      "import sys; from hirearchy import main; from hirearchy.app import wiring; from hirearchy.kiro import RuntimeReadiness; "
      "from hirearchy.kiro.testing import FixedReadiness; ready = wiring.overriding({RuntimeReadiness: FixedReadiness(None)}); "
      "ready.__enter__(); main(sys.argv[1:])"
  )
  ```

  The process is the real `hirearchy run --until-done` with its pidfile, exit marker and log, and `SchedulerIdentity` still recognises it
  (`run` and the org root are on its command line, `daemon/_identity.py:33-36`). New imports: `SchedulerCommand` from `hirearchy.daemon`
  (the test already imports `EXIT_FILE` from there), `FixedSchedulerCommand` from `hirearchy.daemon.testing`, `with_ports` from
  `testkit.health_world`, and `from pathlib import Path`. The existing assertions stay as they are, and after them it asserts that the child
  made no readiness call.
- The assertion, the same in both tests (E1):

  ```python
  stub_log = Path(os.environ["KIRO_STUB_LOG"])
  assert not stub_log.exists() or "--version" not in stub_log.read_text(encoding="utf-8").splitlines()  # no readiness call
  ```

  These are item 3's two REDs. In `test_exit_assistant.py` the assertion fails on today's test and with the unbound one-liner, and passes
  with the bound manager. In `test_wire_cli.py` it fails today and passes once the two calls run inside `with wiring.overriding(...)`.
  Each RED is seen to fail before its fix is applied.

**Still exposed, never recorded failing.** Other tests run the real readiness against the stub: in-process through the CLI
(`cli/tests/test_run_command.py`, `test_run_command_assistant.py`, `test_progress_command_assistant.py`, `test_announce.py`,
`test_org_announce.py`) and in child processes (`daemon/tests/test_control.py:148`, `tests/e2e/test_scheduler_detach.py`,
`tests/e2e/test_scheduler_signal.py`). They stay as they are: they are what still exercises the real readiness against the stub, and the
final validation's flake rule covers them.

## 5. Test plan (the owner's test policy, `RES/phase-0a2/test-policy.md`)

Each commit runs FAST, scoped (test-policy rule 2): the touched packages' tests, plus `tests/golden`, `tests/architecture` (deselecting
`tests/architecture/test_static_checks.py`) and `uv run python scripts/static_checks.py all`. `src/hirearchy/app/tests` joins when a
commit touches `app/`, an `api.py` Protocol or the wiring (`scheduler/_assembly.py`). Each FEAT and each fix pass runs SCOPED (test-policy
rules 3 and 4): the union of the FEAT's or pass's targets plus `tests/e2e`, `tests/golden`, `tests/architecture` (deselecting
`tests/architecture/test_static_checks.py`) and `src/hirearchy/app/tests`, then `uv run python scripts/static_checks.py all`. The full
`scripts/check.sh` runs only in final validation. No real kiro-cli and no `integration` test run. Every test seat runs on
claude-sonnet-5.5 at effort high or better.

Unit tests (pure or in-memory):
- `kiro/tests/test_launch.py`, the prefix (condition 1):
  - `test_the_effort_warning_is_matched_by_its_prefix`: `EFFORT_PREFIX == "failed to set effort"`;
  - `effort_warning` on `[warn] failed to set effort 'high': model 'claude-sonnet-5.5' offers no effort levels` and on `[warn] failed to
    set effort 'high': the engine did not load its model list in time` gives each line from the prefix on, unchanged;
  - an unknown reason (`[warn] failed to set effort 'xhigh': something new`), no tag (`failed to set effort ...`) and another tag
    (`[WARN] failed to set effort ...`) give the text from the prefix on;
  - a trailing `\r` is removed and a 400-character reason is cut at 300;
  - `note: failed to set effort 'high'` (the prefix not at the start), `[warn] failed to set efforts` and an empty line give `""`.
  - RED: `ImportError`.
- `kiro/tests/test_launch.py`, `effort_stop`:
  - a genuine tail (warning line, mark, `# exit -9 after 3s`) gives `EffortStop(warning, 0)` for each of the two known reasons, and
    `tool effects: 2` gives effects 2;
  - each of these gives `None`: the mark not as the last `# kiro:` line, no warning line before the mark, a malformed effects part, an
    empty tail, and a tail with the throttle mark only.
  - RED: `ImportError`.
- `budget/tests/test_run_credit.py`: a new test shows that `effort_credit` has the fields and title of `run_credit`, text C as its body,
  and a stem that `credited_stems` reads. RED: `ImportError`.
- `scheduler/tests/test_effort.py` (new) covers `CreditingEffortStops` over the lifecycle world's memory stores:
  - `stop_of` on a genuine tail, on a tail without a mark, and on a missing log (`None` and the console line
    `<addr>: run log not read for the effort check: ...`);
  - `credit` gives `free`, then `counted` after a credited run, `""` with effects, `""` with mail sent after the stem, and `""` plus the
    console line `<addr>: effort credit not given: ...` when the delivery raises.
  - RED: `ModuleNotFoundError`.
- `scheduler/tests/test_reaper_parts.py`: the helper gains the `efforts` keyword (2.4). New cases:
  - -9, not killed, `free`: `run.end` error B1, line D, no failure;
  - `counted`: B2 and a failure; `""`: B3 and a failure;
  - -9 with `run.killed`: `stop_of` is not asked;
  - -9 without a stop: today's path (`exit code -9`, a failure);
  - exit 75 with an effort stop scripted: the throttle path, and `stop_of` is not asked.
  - RED: `TypeError` (the constructor), then the assertion on B1.
- `progress/tests` and `reflection/tests` each get one case: a run returned by `effort_credit` is neither used nor kept. These pass on
  arrival, because the title is a credit; they pin that.

Integration tests (real processes, fake kiro, no credits):
- `kiro/tests/test_launch.py`, the launcher as a script, the stop. These use `launch_in_group` (3), which gives the launcher's stdout,
  its stderr and the group:
  - `test_an_effort_warning_stops_the_run_before_any_tool_effect[group-leader|not-leader]`: the fake prints `START`, then writes
    `[warn] failed to set effort 'high': model 'claude-sonnet-5.5' offers no effort levels` to stderr, then `exec sleep 30`. Asserts out ==
    `["# kiro: run started (engine v3)", <A with none>]`, code -9 or 1, the warning in the launcher's stderr text, and `group_gone`. RED:
    `subprocess.TimeoutExpired` (today the run sleeps).
  - The same with the other known reason, `the engine did not load its model list in time`: the mark quotes it as it came (condition 1).
  - The same with an unknown reason after the prefix: stopped, quoted.
  - The warning before `runStarted`: the fake writes the warning and then `exec sleep 30` without ever printing `START`, so the order
    cannot depend on scheduling. Asserts out == `[A]`.
  - The warning after a completed `hirearchy::write` update: the fake prints `START` and the update, then writes the warning. Asserts the
    mark says `tool effects: 1`.
  - A stderr line that holds the prefix but does not start with it: exit 0, no mark.
  - `test_the_effort_mark_is_no_closing_mark_of_the_run_log` (new; the existing closing-mark test stays unchanged).
- `kiro/tests/test_launch.py`, the drain (condition 2). The fake writes numbered stderr lines of 80 bytes in a shell loop: 2,000 lines
  (160,000 bytes, more than two 64-KiB pipe buffers) at each place named below. fd 1 and fd 2 of the launcher go to one log file, as in a
  run.
  - `test_more_than_a_pipe_buffer_of_stderr_is_drained_and_logged_in_order`: 2,000 lines before `START`, 2,000 after it, then `FINISHED`.
    Exit 0 within the 30-s timeout. The log's `err-` lines are exactly the 4,000 lines written, in order. `# kiro: run started (engine
    v3)` and `[run finished] success (end_turn)` are present.
  - The same with stdout closed after `FINISHED` (`exec 1>&-`) and 2,000 more stderr lines before kiro exits: all 6,000 lines are in the
    log, and the run completes.
  - The same with separate pipes: the launcher's stderr equals the fake's stderr byte for byte, a last line without a newline included.
  - Before an early end: the fake closes stdout (`exec 1>&-`), writes 2,000 stderr lines and exits 4. Asserts exit 4, all 2,000 lines in
    the log, and `# kiro: kiro-cli exited with code 4 before the run started` as the last line. After the pipe change and without the
    stderr loop of `_exit_code`, this test times out, because kiro blocks on the full pipe while the launcher waits for it.
  - `START`, then 2,000 stderr lines, then the warning: out is `["# kiro: run started (engine v3)", A]`, and the log holds the 2,000
    lines, the warning and A, in that order (E10). RED: `subprocess.TimeoutExpired`.
  - The tail of an over-long stderr line (E5): a 70,000-byte stderr line whose last 80 bytes are `failed to set effort ...` gives no stop.
    The unit case feeds `_read_err` through a pipe in pieces, so `partial` passes `ERR_LINE_LIMIT` before the line's last bytes arrive. RED:
    without `skipping`, the tail is scanned as a line of its own and sets `err.warning`.
  - A background child holding stderr after kiro exits (`sleep 30 >/dev/null &`): the run ends within 5 s, the twin of the stdout test.
    The launcher stops reading 2 s after it sees kiro exit, counted once across `_stream` and `_exit_code`, so the 5-s bound keeps the
    stdout twin's margin.
  - `test_kiros_stderr_keeps_its_place_when_kiro_writes_without_pause` (new, a guard of the order rule of 2.2): the fake writes `START`,
    `E1` to stderr, `Hello`, `E2` to stderr and `FINISHED` with no pause, 10 times over. In each log, `# kiro: run started (engine v3)`
    is the first line, `E1` comes before `Hello` and `E2` before `[run finished] success (end_turn)`. It asserts no order between `Hello`
    and `E2`, which the rule does not give. Before the change it fails in practice, because kiro writes `E1` into the log itself before
    the launcher has written `# kiro: run started`; that is no deterministic RED, so the commit's RED is the warning test.
  - The first three pass today, because kiro writes the log itself. They are the guard that the new reading must keep green.
- `scheduler/tests/test_loop_effort.py` (new), the real loop with the fake agent:
  - `FAKE_EFFORT_STOP_RUNS=1`: the first run prints the warning to stderr and mark A to stdout, then SIGKILLs itself. Asserts one effort
    credit, no `agent.failure`, the relaunch and the case's run count without the stopped run.
  - `FAKE_EFFORT_STOP_RUNS=9` with `max_failures` 3: paused after 4 stopped launches, 4 credits, and root has "keeps failing".
  - RED: the fake agent ignores the variable, so no credit.
- Item 2: the hardened tests and `test_a_kiro_killed_before_its_first_line_leaves_no_process` (3). There is no RED for a test-only
  hardening; the new test shows the old assertion failing on the reproduced race.
- Item 3: the two hardened tests (4), each with its RED (E1): the `KIRO_STUB_LOG` "no `--version` call" assertion fails on today's
  `test_exit_assistant.py::test_a_real_until_done_scheduler_process_exits_by_itself` and with the unbound one-liner, and passes with the
  bound `ready = wiring.overriding(...)`; the same assertion fails on today's
  `test_wire_cli.py::test_the_scheduler_runner_runs_the_loop_until_there_is_nothing_to_do` and passes once its two `runner.run` calls run
  inside `with wiring.overriding(...)`.

Existing tests that stay unchanged and green (condition 3; a reviewer checks with `git diff main -- <file>`):
- `kiro/tests/test_launch.py`: every existing test except the two that item 2 hardens. That covers the throttle section (from :425),
  `test_engine_v2_is_refused`, `test_a_first_event_that_is_not_run_started_is_refused`, both `test_an_end_before_the_start_*`,
  `test_the_text_copied_before_the_start_is_limited_to_4_kb`, `test_no_launcher_line_starts_with_a_closing_mark_of_the_run_log`,
  `test_each_launcher_line_comes_before_the_next_line_of_kiros_stderr` (held by the order rule of 2.2) and
  `test_a_background_child_holding_stdout_does_not_hold_the_run`.
- `scheduler/tests/test_throttle.py`, `test_loop_throttle.py`, `test_failures.py`, `test_lifecycle.py`, `test_robustness.py`, and every
  existing test function of `test_reaper_parts.py`.
- `budget/tests/test_run_credit.py`'s existing test, `kernel/tests/test_message.py`, the credit cases of `progress/tests` and
  `reflection/tests`, `app/tests/test_scheduler_lifecycle.py`, `app/tests/test_wire_scheduler.py`, `settings/tests/test_config.py`, and the
  golden suite.

## 6. User-visible changes

1. The run log of a run that kiro-cli reports below the floor ends early with mark A and `# exit -9 after <n>s`. kiro's own stderr lines
   are in every run log as before, byte for byte, now forwarded by the launcher. Their place among the launcher's lines now follows when
   the launcher reads them (the order rule of 2.2): a stderr line kiro wrote before a stdout line still comes before its rendering, and
   one written just after may now come before it too.
2. The `run.end` event of such a run carries error B1, B2 or B3, and observe and the dashboard show it.
3. The scheduler's output gains lines D and E.
4. The agent's next prompt holds credit note C.
5. Budget: a stopped launch without a tool effect is not charged, and case totals and `runs n of m` leave it out. An agent with `shell`
   can fake such a stop (limit 6). `health` counts a stopped launch as a failed run: its `(+M failed)` count includes it, and its
   efficiency flags leave it out, as for a credited throttle (E7).
6. README gains sentence G. ARCHITECTURE.md's kiro section and scheduler ports describe the new exports, the launcher's stderr reading and
   stop, and `EffortStops` (2.13, E6).
7. Nothing changes in `status`, `progress`, `whoami`, the plan block, ORG.md, the profiles or the MCP tools. Items 2 and 3 change no
   user-visible behaviour.

## 7. SKILL.md

No change; its md5 and its 125 lines stay, and so do 0a.4's lines 72, 92 and 100 and 0a.5's line 39. Root has nothing to do: the runtime
stops, credits and relaunches by itself. A streak reaches root through the existing "keeps failing" notice. Observe's error text states
the outcome, and the throttle credit, the precedent, has no SKILL.md line either.

## 8. Out of scope

The assistant's own session (2.12), a post-run check of the session store's `effortLevel` (backlog), a verdict an agent with `shell`
cannot fake and the forged credit note (the manager's security backlog, limit 6), the spinner test's text check (3), the other tests exposed to the readiness
timeout (4), any change of `READINESS_TIMEOUT` or `START_DEADLINE`, and any change of the throttle path beyond the shared `return_run`.

## 9. Responses to the design review and the manager's decisions

### 9.1 The manager's decision on iteration 1

The manager's decision on the draft (`.agents/tasks/manager-decision-item1.md`, 2026-10-28) approved (a), texts A-D and G, the cost, the
declared limits and the bound of max_failures + 1. The decision's binding conditions are folded in:
1. **The prefix, for any reason.** `EFFORT_PREFIX`, `EFFORT_LINE` and `effort_warning` are in 2.2, used by `effort_stop` in 2.3. The
   input rules are in 2.7, the edge rows in 2.9 and limit 3 of 2.12, which now names the prefix only. Text A gained the example of the
   second known reason. The parenthesis of text G now says "a line beginning "failed to set effort", such as "[warn] failed to set effort
   'high': ..."" instead of "a line starting "[warn] failed to set effort"", so that it matches condition 1. The rest of G is as approved.
2. **The drain.** The drain rule and the order rule are in 2.2, with edge rows in 2.9 and the drain tests in 5.
3. **No regression.** It is held as 2.4 and 2.14 describe, and 5 lists the existing tests that stay unchanged. The design names its two
   edits near those tests: the construction helper of `test_reaper_parts.py`, and item 2's own hardening.

### 9.2 The design review of iteration 1 (`.agents/tasks/design-review.md`, CHANGES_REQUESTED)

1. **HIGH, stdout first breaks `test_each_launcher_line_comes_before_the_next_line_of_kiros_stderr`.** Addressed, with one deviation from
   the review's text. Stdout first is kept only in `_wait_for_start`. From the start on, stderr is drained before any stdout bytes are
   rendered (2.2, "Order across the two pipes", and `_stream` steps 0 and 5). The review proposed draining before each stdout read. This
   design drains after the read and before the rendering, and also once before `rest`. A drain before the read leaves a window in which a
   stderr line written after the drain is followed by stdout bytes that arrive before the read; a drain after the read has none (2.2).
   The "in the order kiro wrote it ... as today" claims are gone. 6 item 1 states the new placement, and 5 adds a guard test without
   pauses.
2. **MEDIUM, the agent can produce exit -9.** Addressed. 2.3 and 2.8 now say that exit -9 is not exclusive to the launcher. Limit 6 in
   2.12 declares the path and gives its exact bound. The review's bound "max_failures + 1 uncharged runs before the pause" holds for a
   streak; between normal runs, which clear the count, the bound is max_failures of every max_failures + 1 runs, and limit 6 says so.
   2.9, 2.11, 6 and 8 name it too. I did not add the optional rule (no `[tool` line between the mark and `# exit`). It does not close the
   path: the agent can arm the kill before it prints the forged lines (`sleep 1; kill -9 0 &`), so the kill's `[tool` line comes before
   the mark, or it can write the lines into the log from its shell. An agent with `shell` can also already write a credit note into its
   own mailbox (limit 6). A partial rule would add a check, a test and a reasoning burden without moving the bound. 2.1 now gives the
   reasons why no verdict can be made unforgeable within this design.
3. **MEDIUM, the 1.46-s margin.** Addressed. 1.3 now says that the session timestamps time the turn, not the warning, and adds the
   read-only first tool line (670 of 670: 666 Tool Load, 2 Read File, 2 List Directory), which I recounted from the kept logs. 2.1 and
   the 2.9 row use those facts; the row now also says that every update kiro wrote before the warning is counted, because the stop reads
   stdout to its end (`_last_output`). The 1.46 s appears only as a turn figure.
4. **MEDIUM, `_exit_code`'s 2 s.** Addressed as the review proposes. `_stream` returns `exited_at`, `_exit_code(proc, err,
   exited_at=None)` measures one window from it, and the rule "at most 2 s after kiro exits, in total across `_stream` and `_exit_code`"
   is in 2.2, 2.9 and the drain test of 5.
5. **NIT, SCOPED.** Addressed: 5 now gives SCOPED as the review words it, with `src/hirearchy/app/tests` always in.
6. **NIT, the tail.** Addressed: 2.4 says "normally both lie in the tail", and 2.9 has the row for more than 4 KB or 80 lines between the
   warning and the end of the run (charged, never seen).
7. **NIT, piped stderr.** Addressed: 1.7 cites `probe.py:31` and the H3 probe (exit 0 at :3, start lines at :85-96).
8. **NIT, clustering.** Addressed: 1.6 uses the review's wording, and 2.1 refers to it.
9. **NIT, `launch_in_group`.** Addressed: it returns `(code, stdout lines, stderr text, group)` (3), and the effort tests of 5 use the
   stderr text.
10. **NIT, line E.** Addressed: the text is `<addr>: run log not read for the effort check: <error>` in 2.4, 2.6 and 2.10, and the 2.9 row
    for refused or silent starts names it.

Changes beyond the findings, all in 2.2: `_supervise` drains stderr before the `refused` and `gave_up` lines, so kiro's earlier stderr
still comes before them as it does today; `_last_output` names the stop's last stdout read; the drain bound is the named constant
`DRAIN_READS`; the effort test "warning before `runStarted`" never prints `START`, so its result cannot depend on scheduling; and a drain
test covers an early end with more than a pipe buffer of stderr.

### 9.3 The manager's decision on iteration 2

Put to the manager before this design was committed: the reworded text E, limit 6 with its cost bound, and the new placement of kiro's
stderr lines in the run log. All three were approved on 2026-10-28 (`.agents/tasks/manager-decision-item1.md`, last section):
1. Text E reads `<addr>: run log not read for the effort check: <error>`.
2. Declared limit 6 is accepted as written, and so is declining the optional `[tool`-line rule. A `shell` agent can already forge a
   credit note and rewrite its own run log, so no verdict read from the log is unforgeable. A run-credit verdict that a `shell` agent
   cannot forge, covering both the forged credit note and the forged effort stop, is the manager's backlog item (security, after Phase
   2's design), not this batch's.
3. Placing kiro's stderr lines by read time is approved, because a stderr line written before a stdout line still comes first and
   `test_each_launcher_line_comes_before_the_next_line_of_kiros_stderr` stays unchanged.

## 10. Manager amendments (design loop closed)

Design review 2 (`.agents/tasks/design-review.md` and `.json`, on `d363fa7a`) returned CHANGES_REQUESTED with 1 HIGH, 0 MEDIUM and 9 NIT.
The manager closed the design loop by decision, with no third pass, and made the review's ten findings binding amendments E1-E10:
`/Volumes/workspace/hirearchy/.worktrees/org-1-1-effort/.agents/tasks/manager-decision-design-loop.md` (2026-10-28). The HIGH is a
test-only defect in item 3 that the reviewer verified by running it, with an exact fix and a deterministic RED; item 1's design, texts,
cost and limits verified clean. Each fix is adopted as the review words it. Where an amendment and older text of this file differ, the
amendment wins. The plan (`.agents/tasks/plan.md`) carries E1's two REDs and E5's unit case as named test commits, and E6 in its docs
commit.

| Amendment | Finding | What binds | Where it landed |
|---|---|---|---|
| E1 | 1 (HIGH) | `READY_SCHEDULER` binds the context manager to a name (`ready = wiring.overriding(...); ready.__enter__()`), one command line through adjacent string literals. The `KIRO_STUB_LOG` "no `--version` call" assertion is added to `test_exit_assistant.py::test_a_real_until_done_scheduler_process_exits_by_itself`, and after the two `runner.run` calls of `test_wire_cli.py::test_the_scheduler_runner_runs_the_loop_until_there_is_nothing_to_do`, which then run inside `with wiring.overriding(...)`. These are item 3's two REDs; each is seen to fail on today's test (and, for the first, with the unbound one-liner) before its fix | 4 (the fix); 5 (item 3) |
| E2 | 2 | 666 first tool lines are `[tool ok] Tool Load`: 642 with `{"tool_ids":["hirearchy::*"]}`, 24 with a list of named hirearchy tools; 2 Read File, 2 List Directory. 2.1 keeps "666 Tool Load, 4 reads" | 1.3 |
| E3 | 3 | `test_a_kiro_killed_before_its_first_line_leaves_no_process` uses the body `sleep 15\necho $$ > pid\nexec sleep 30\n` | 3 |
| E4 | 4 | An update that kiro writes after the launcher's last stdout read, or does not write before the kill, is not counted, and the run is credited; every update written before the warning is counted (`_last_output`) | 2.9 |
| E5 | 5 | `ErrPipe.skipping`: after an over-long `partial` is dropped, the scan skips bytes up to and including the next `\n`; forwarding is unchanged. One unit case: a 70,000-byte stderr line whose last 80 bytes are `failed to set effort ...` gives no stop | 2.2 (`ErrPipe`, `_read_err`); 5 |
| E6 | 6 | `ARCHITECTURE.md` gets three edits in the docs commit: `:1292` the new kiro exports; `:1293-1294` the launcher reads kiro's stderr, forwards it to fd 2 and stops the run at the warning (mark A, exit -9); `:1361` `EffortStops` (`CreditingEffortStops(logs, mail, delivery, console)`), asked by `RunSettlement` on exit -9 of a run that was not killed, with `return_run` shared with the throttle credit | 2.13; 6 item 6 |
| E7 | 7 | `health` counts a stopped launch as a failed run: its `(+M failed)` count includes it, and its efficiency flags leave it out, as for a credited throttle | 2.11; 6 item 5 |
| E8 | 8 | The scheduler dies after the stop and before it settles the run: the next scheduler redelivers its batch (`run.orphan`, `redelivered`); no credit, charged, as for a throttled run | 2.9 |
| E9 | 9 | Text C is unchanged. At the stop that pauses the agent, note C still says "the run is started again", as the throttle note does; the agent runs again once it is resumed | 2.9 (the repeat row) |
| E10 | 10 | The drain test: `START`, then 2,000 stderr lines, then the warning: out is `["# kiro: run started (engine v3)", A]`, and the log holds the 2,000 lines, the warning and A, in that order | 5 |

Accepted as stated (the same decision file): review 2's unverified assumption 4, that kiro-cli also writes the warning when its stderr is a
pipe, was not seen live; if it did not, detection fails open to today's behaviour, which declared limit 3 covers, and no live run is added.
Earlier decisions stand: option (a), the bound, conditions 1-3, text E, limit 6 and stderr placed by read time
(`.agents/tasks/manager-decision-item1.md`). Unchanged by the amendments: the user-visible texts A-G, the cost, the declared limits, SKILL.md
(section 7) and `READINESS_TIMEOUT`.
