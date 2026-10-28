# Batch 1.1: the effort floor that kiro-cli does not always apply, and two load flakes

Brief: `docs/research/org-growth/phase-1/1-1-brief.md` (binding). Base: `main` at `5bbf295f`. Branch: `fix/org-agent-effort-floor`.
Paths are relative to the worktree; `EV` is `studies/P1-itemized-playbook/evidence`, `G0` is `studies/G0-noise-baseline/evidence`, `RES` is
`/Volumes/workspace/hirearchy/docs/research/org-growth` (untracked research of the main checkout).

## 0. Overview

The owner's floor (D-E4-9) is claude-sonnet-5.5 at effort `high` or better on every seat. The product passes `--effort high` on every org
run, but kiro-cli sometimes reports on its stderr that it could not apply it, and the run then goes on silently. The kept evidence shows
that this report is written during the engine's start, before the run's first tool call and before its first model response ends, in 73
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

The session timestamps give the margin. The `user` message is stored a median 0.69 s after the session is created, the turn starts about
0.01 s later, and the first tool call comes at least 1.46 s after the turn start in 670 of 670 sessions (at least 1.73 s in P1's warned
runs, 1.57 s in G0's).

What the kept evidence cannot settle: whether the run's first model request had already been sent when kiro wrote the warning. kiro's
stderr lines carry no time, the org runs' raw stream-json was not kept (the launcher keeps only its rendering), and nothing records effort
per request. The assistant's wording ("did not load its model list in time") says kiro-cli waits for the model list during session setup
and then gives up, so the warning is written at setup, before or as the prompt goes out. This design therefore counts a stopped launch as
having spent at most its first model request (2.11).

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

### 1.6 Independence of repeats

In P1, 4 of the 30 warned runs that had a next org run in their stream were followed by another warned run (13 %, base rate 7.5 %); in
G0, 2 of 41 (5 %, base rate 17 %). Warnings do not cluster, so a relaunch is expected to set the effort with about the base rate's
complement (83-93 %).

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

- (a) is possible. The warning arrives before any tool call in 73 of 73 runs, at least 1.46 s before the first tool call in every kept
  session. A launcher that reads kiro's stderr sees it within milliseconds, because `select` returns as soon as a pipe has data.
- (a) holds the floor. No run that kiro-cli reports below the floor does tool work after the report, and the relaunch starts a fresh
  engine, which sets the effort with probability 0.83-0.93 (1.6).
- (b) would let a run below the floor finish and then need a new "valid seat" notion in status, observe and the event. The manager ranks
  it after (a), and (a) is possible.
- (c) has no support in the evidence (1.8).

Rejected ways to do (a):
- **Detect on the stream** (no `config_option_update` with a floor effort before the first agent event). It cannot be checked against a
  warned run (1.7). If clean runs differed from the two recordings, it would stop every run.
- **Merge kiro's stderr into its stdout pipe.** One pipe would make the order exact, but node writes larger than `PIPE_BUF` (512 bytes on
  macOS) are not atomic, so a stderr line could split a JSON event and corrupt the effect count of the throttle credit.
- **Stop kiro with SIGTERM and keep the launcher alive** to return a code of its own. That depends on how kiro-cli and its MCP server handle
  SIGTERM, which nothing kept shows, and it needs a fallback. The launcher already ends a refused or silent run by killing its process
  group, itself included (`_end_run`, `_launch.py:309-319`); the stop reuses that path unchanged.

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
  `ERR_LINE_LIMIT = 65536`, the longest stderr line scanned.

New pure function, exported: `effort_warning(line: str) -> str` returns kiro's warning as the mark quotes it, or `""` when `line` is not an
effort warning. It strips trailing whitespace, applies `EFFORT_LINE.match`, and returns group 1 with every `\r` removed, cut at
`CUT_WARNING`. Nothing else is changed, so the quote is kiro's text as it came. Both the launcher's scan and `effort_stop` (2.3) use it, so
the two can never disagree.

New data: `@dataclass class ErrPipe: fd: int; open: bool = True; partial: bytes = b""; warning: str = ""`.

**The drain rule (manager's condition 2).** From the `Popen` to the end of `main`, every place where the launcher waits also reads kiro's
stderr while that pipe is open: the start wait, the stream, the exit wait and the reads before a kill. Every byte read is written to fd 2
before anything else is done with it. kiro therefore never blocks on a full stderr pipe, and the run log gets kiro's stderr byte for byte,
in the order kiro wrote it. The launcher's own lines (fd 1) fall between kiro's lines in the order the launcher read them, as today. In
one `select` pass that finds both pipes readable, stdout is handled first and then stderr, so `# kiro: run started` still comes before the
engine's start lines (as in `EV/F1/run-logs/lead-writer/20261027T193307448475.log:146-157`). The only bytes that can be lost are those
written after the launcher's kill (kiro is dead then), those a background child writes after the 2-s drain, and those fd 2 refuses
(`OSError`: the log itself cannot be written).

New functions:
- `_forward(data: bytes) -> None` writes `data` to fd 2 at once, all of it, ignoring `OSError` (as `emit` does for fd 1). In a run fd 1 and
  fd 2 are the same log file (`processes/_spawn.py:54-56`: `stderr=subprocess.STDOUT`), so kiro's lines land in the log in arrival order,
  between the launcher's own lines, as they do today.
- `_read_err(err: ErrPipe) -> None` reads up to 64 KB from `err.fd`. Empty means end of file: the remaining `partial` is scanned as a
  line and `err.open = False`. Otherwise it forwards the bytes, appends them to `partial`, splits off the complete lines and scans each. A
  `partial` longer than `ERR_LINE_LIMIT` is dropped from the scan (it was already forwarded).
- Scanning a line: decode UTF-8 with replacement. If `err.warning` is empty, set `err.warning = effort_warning(line)`. Only the first
  warning counts; the scan never changes what was forwarded.
- `_forward_ready(err: ErrPipe | None) -> None`: while `select` with timeout 0 says the open pipe is readable, `_read_err`, at most 16
  times. Any `OSError` or `ValueError` is ignored, because this runs just before a kill.

Changes to existing functions:
- `main`: `subprocess.Popen(kiro, stdout=subprocess.PIPE, stderr=subprocess.PIPE)`; `err = ErrPipe(proc.stderr.fileno())`; pass `err` to
  `_supervise`. The comment on the `Popen` line becomes "stdin (the prompt) is inherited; stderr is read and forwarded to fd 2 (the run
  log); same process group". The `except Exception` path still calls `_end_run(proc)`, without `err`.
- `_wait_for_start(fd, err, limit)`: each `select` also watches `err.fd` while it is open. Stdout is handled first, as today; a decision
  read from it (`started`, `refused`) returns at once, and stderr bytes still in the pipe are read by the next stage. When stderr is
  readable, `_read_err(err)`; when `err.warning` is then set, copy the buffered non-JSON output as the deadline path does and return
  `Start("effort")`. The deadline, `COPY_LIMIT` (stdout only) and every text are unchanged.
- `_stream(proc, fd, err, rest) -> tuple[RenderState, bool]`:
  1. render every complete stdout line in the buffer (as today);
  2. if `err.warning` is set and `proc.poll() is None`: read what stdout holds now (`select` timeout 0, at most 16 reads of 64 KB),
     render its complete lines, and return `(state, True)` without calling `finish`;
  3. note when kiro exited, and stop the loop 2 s (`DRAIN_SECONDS`) after it, as today;
  4. stop the loop when both stdout and stderr have reached end of file;
  5. `select` on stdout (while open) and stderr (while open), `SLICE_SECONDS`; in a pass that finds both readable, stdout is read and
     rendered first, then stderr goes to `_read_err`; stdout end of file now marks stdout closed instead of ending the loop, so kiro's
     last stderr lines are still forwarded.
  After the loop, render the rest and the `finish` lines as today, and return `(state, False)`.
- `_exit_code(proc, err)`: while kiro runs and stderr is open, keep reading stderr (`select`, `SLICE_SECONDS`); after kiro exited, keep
  reading until stderr reaches end of file or 2 s have passed; then `proc.wait()` and today's mapping. Without this, a kiro that fills the
  64 KB stderr pipe while the launcher waits would block forever.
- `_end_run(proc, err=None)`: `_forward_ready(err)` first, then today's kill.
- `_supervise(proc, limit, err)`:
  - `Start("effort")`: `_stop(proc, err, None)`;
  - `refused` and `gave_up`: as today with `_end_run(proc, err)`;
  - `ended`: `code = _exit_code(proc, err)`, then as today;
  - after `run started`: `state, stopped = _stream(...)`; if `stopped`, return `_stop(proc, err, state)`; else as today with
    `_exit_code(proc, err)`.
- New `_stop(proc, err, state) -> int`: `_forward_ready(err)`; emit the `_flush(state)` lines (an unfinished agent line); emit the mark with
  `state.effects` (`none` when 0 or when there is no state); return `_end_run(proc, err)`.

In the scheduler's runs the launcher leads its process group (`processes/_spawn.py:56`, `start_new_session=True`). The stop therefore
kills kiro, its MCP server and the launcher together, and the scheduler sees exit -9, as for a refused or silent run today. When the
launcher does not lead its group (only in tests), `_end_run` kills kiro alone and returns 1.

### 2.3 The verdict and its second check (`_launch.py`, exported by `kiro/api.py`)

The verdict is **exit -9 that the scheduler did not cause** (`not run.killed`). Agent text cannot produce it, because it needs a SIGKILL of
the launcher. The mark is its second check, the same split as the throttle's exit 75 and mark (0a.2 design 9.1, DR-44).

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
- `TAIL_BYTES, TAIL_LINES = 4096, 80`, as for the throttle. The warning is forwarded just before the mark, so both lie in the tail.
- `OUTCOMES = {"free": "not charged, relaunched", "counted": "not charged, counted as a failure", "": "charged as a failed run"}`.
- `effort_text(stop, kind) -> str` returns `f"effort not set: run stopped, {OUTCOMES[kind]} (kiro-cli: {stop.warning}; tool effects:
  {'none' if stop.effects == 0 else stop.effects})"`. The outcome comes first because observe cuts a run's error at 120 characters
  (`observability/_render.py:55`).
- `class CreditingEffortStops(EffortStops)` with `(logs: RunLogReader, mail: MailboxReader, delivery: MessageDelivery, console: Console)`:
  - `stop_of(run)` returns `effort_stop(self._logs.tail(run.log, TAIL_BYTES, TAIL_LINES)[0])`. On `OSError` or `OrgError` it says
    `{addr}: effort stop not read: {error}` and returns `None`.
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
| Launcher: read kiro's stderr | `OSError` | no: it propagates to `main`'s `except Exception`, as a stdout read error does today | `# kiro: launcher error: ...`, the run is killed (exit -9) | the mark line, in the run log |
| Launcher: forward to fd 2 | `OSError` | yes, ignored (as `emit`) | nothing | no |
| Launcher: the reads before a stop | `OSError`, `ValueError` | yes, ignored | the stop goes on | no |
| Launcher: the kill | `OSError` of `killpg` | yes, today's fallback `proc.kill()` | exit -9 (leader) or 1 | the mark is already written |
| Scheduler: read the tail | `OSError`, `OrgError` | yes: no stop is recognised and the run takes today's failure path (charged) | `None` | console `{addr}: effort stop not read: {error}` |
| Scheduler: mail reads, log listing | `OSError`, `OrgError` | yes: no credit, charged | `""` | console `{addr}: effort credit not given: {error}` |
| Scheduler: deliver the note | `OSError`, `OrgError` | yes: no note was written (the delivery writes last), charged | `""` | the same console line |
| Count the failure, pause at `max_failures` | as today | as today | as today | as today |

### 2.7 Validation of external input

- **kiro's stderr** (untrusted bytes): every byte is forwarded to the log whatever it is, before any scan. For the scan, a line is decoded
  as UTF-8 with replacement, and only a line of at most 64 KB is scanned. It counts when `effort_warning` finds the prefix
  `failed to set effort` (case-sensitive, followed by a word boundary) at the start of the line, either at once or after one level tag of
  1-10 letters in brackets and a space (`[warn] `). Any reason after the prefix counts. The quote is kiro's text from the prefix on, without
  trailing whitespace and `\r`, cut at 300 characters. Only the first such line acts.
- **The run log's tail** (written by the launcher, kiro and, through agent text, the agent): `effort_stop`'s rules (2.3). Anything else is
  `None`, and the run is charged as today.
- **The effort value**: checked at build by the existing floor (`_runner.py:53`). Detection does not depend on it.

### 2.8 Invariants and who enforces them

- **A run that kiro-cli reports below the floor does no tool work after the report.** Owner: the launcher. It is the only process that
  sees kiro's stderr while the run goes on, and the only one that can end the run before the agent acts.
- **A launch is credited only on the launcher's verdict.** Owner: `RunSettlement` and `CreditingEffortStops`. They require exit -9 that
  the scheduler did not cause, the mark as the last `# kiro:` line, `tool effects: none`, and no message sent by the run. Fail safe: when
  in doubt, the run is charged.
- **A credited launch is not charged anywhere.** Owner: `kernel.credited_stems`, the single definition that budget, reflection, progress
  and the conservation check already read.
- **Relaunches are bounded.** Owner: the existing failure counter (`CountingFailures` and `max_failures`), so this design adds no
  setting.

### 2.9 Edge and zero cases

| Case | What happens |
|---|---|
| The relaunch gets the warning again | It is stopped again. Its credit is `counted`, so it is not charged but it is a failure. Every later stop in a row is also `counted`. With `max_failures` = 3 (the default) a streak is at most 4 stopped launches (1 free, 3 counted); then the agent is paused and its parent and root get the existing "keeps failing" notice. With `max_failures` = 0 the first counted stop pauses it (the existing rule). At G0's rate (17 %), 4 in a row is about 0.08 %. |
| The warning comes before `runStarted` | The same stop, `tool effects: none` (never seen: 0 of 73). |
| The warning comes after a tool effect | The run is stopped anyway, because the floor beats the work. The mark says `tool effects: <n>`, there is no credit, and the run is charged and counted like any failed run; its messages go back to the inbox and the existing failure rule retries it. Never seen: 0 of 73. |
| The warning is read after kiro exited | It is not acted on, because nothing is left to stop. The line stays in the log, and the run ends by today's rules. Never seen. |
| A stderr line contains the prefix but does not start with it (after an optional level tag) | No stop. |
| The prefix is followed by a reason never seen before | The same stop; the mark and the event quote the new reason as it came. |
| kiro writes more than a pipe buffer (64 KiB) to stderr, at any point of the run | It is read as it comes (the drain rule, 2.2), so kiro never blocks on it, and the log gets every byte in order. |
| No warning, no `effortLevel` (2 of 670 kept runs) | Not detected: declared limit 2.12. |
| A later kiro-cli drops or rewords the prefix `failed to set effort` | Not detected: the run goes on as today. Declared limit 2.12. |
| The run sent a message before the stop (race) | No credit, charged, counted: the existing belt-and-braces check. |
| The stop races a tool effect that the stdout drain did not see | Possible only within milliseconds of a tool call; every kept first tool call came at least 1.46 s into the turn. A hirearchy effect that sends mail is caught by the mail check. |
| The scheduler's `--max-runs` cap is reached by the stopped launch | The messages wait in the inbox for the next scheduler, as for a throttled run. |
| The agent is retired during the run | Today's retired branch runs first; no credit is given. |
| A timeout, retirement or shutdown kill | `run.killed`: not an effort stop. |
| A refused or silent start, or a launcher error (also exit -9) | The tail holds no effort mark, so the run takes today's path. |
| The launcher does not lead its group (tests only) | Exit 1: not read as an effort stop, charged as today. |
| A background process keeps kiro's stderr open after kiro exits | The 2-s drain ends the run, as for stdout today. Its later writes get `EPIPE` instead of reaching the log. |
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
| E | scheduler output, errors | `<addr>: effort stop not read: <error>`, `<addr>: effort credit not given: <error>` |
| F | existing, unchanged | for B2 and B3: `<addr>: run failed (<n> in a row), log: <path>` and the `agent.failure` event; at `max_failures`, the pause and the "keeps failing" notices |
| G | README, "Agent runs (the scheduler)" paragraph (after the throttle sentence, `README.md:633-634`) | `When kiro-cli says on its stderr that it could not set the run's effort (a line beginning "failed to set effort", such as "[warn] failed to set effort 'high': ..."), the launcher stops the whole run at once and writes "# kiro: effort not set, run stopped (kiro-cli: ...); tool effects: none"; the scheduler gives a run stopped before any tool effect back with a run credit and starts it again, like a throttled run.` |

`status`, `progress`, `whoami`, ROOT_INSTRUCTIONS and SKILL.md show nothing new. The `run.end` event's fields and the event schema are
unchanged; only its `error` string is new.

### 2.11 Cost effects

- **Budget (runs):** a stopped launch with no tool effect costs nothing. Its credit note returns the run, and the case totals, the
  overspend warning and `runs n of m` leave it out. A stop after a tool effect is charged one run, like any failed run. Observability's run
  counts and failure rates include stopped launches, because they ran.
- **The user's Kiro credits:** each stopped launch pays for an engine start (no model credits) and at most one model request cut off at its
  start. P1 averaged 0.21 credits per request (430.38 credits over 2,053 requests) and G0 0.22 (252.12 over 1,131). Whether Kiro bills a
  request cut off this way is not recorded. The relaunch costs what the original run would have cost anyway. Upper bound at the kept rates:
  P1's 32 stops would have added at most about 6.7 credits to its 430 (1.6 %), G0's 41 at most about 9.1 to its 252 (3.6 %).
- **Time:** each stop wastes about one engine start (a median 10.8 s from the launcher's start to the session in P1), plus the wait for the
  next scheduler pass.
- **Rate:** 7.5 % (P1) to 17 % (G0) of org launches, judging by the kept studies.

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

### 2.13 Files

`src/hirearchy/kiro/_launch.py`, `kiro/api.py`, `kiro/__init__.py`; `src/hirearchy/scheduler/_ports.py`, `_effort.py` (new), `_credit.py`
(new), `_throttle.py`, `_reaper.py`, `_assembly.py`, `testing.py`; `src/hirearchy/budget/_credit.py`, `budget/api.py`,
`budget/__init__.py`; `tests/testkit/fake_agent.py` (`FAKE_EFFORT_STOP_RUNS`, 5); `README.md` (text G). No golden is expected to change:
the stub kiro-cli and the fake agent write nothing to stderr unless a test asks, and no golden holds a `run.end` error. Any golden diff is
a finding, not a regeneration.

### 2.14 The manager's binding conditions, and where each is held

| Condition (`.agents/tasks/manager-decision-item1.md`) | Held by | Tests (5) |
|---|---|---|
| 1. Match the stable prefix `failed to set effort` for any reason, including `the engine did not load its model list in time`. A and B quote kiro-cli's line as it came. The wording limit names the prefix only. | `EFFORT_PREFIX`, `EFFORT_LINE` and `effort_warning` (2.2), used by both the launcher's scan and `effort_stop` (2.3). The quote is group 1, kiro's text from the prefix on. Limit 3 of 2.12 names the prefix only. | the prefix pin; `effort_warning` with both known reasons, an unknown reason, no tag and another tag; the launcher stops a run on each of the two known reasons; `effort_stop` with both reasons |
| 2. Drain stderr until the process ends, so a full pipe never stalls kiro; forward every byte to the run log, in order. | the drain rule (2.2): `_wait_for_start`, `_stream`, `_exit_code` and `_forward_ready` all read stderr while it is open; `_read_err` forwards before it scans | more than 64 KiB of stderr before and after `runStarted`, with the run completing and the log byte-complete and in order; kiro's stderr forwarded byte for byte (a last line without a newline included); a background child holding stderr |
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

def launch_in_group(tmp_path: Path, body: str, deadline: float, leader: bool, timeout: float = 20) -> tuple[int, list[str], int]:
    """(exit code, the launcher's stdout lines, the process group of the run): the launcher in a session of its own, as its group's leader (as
    the scheduler starts it) or, with ``leader`` False, as the only child of a wrapper that leads the group."""
    argv = [sys.executable, "-I", "-S", str(LAUNCHER), "--start-deadline", f"{deadline:g}", "--", str(fake(tmp_path, body))]
    if not leader:
        argv = [sys.executable, "-I", "-S", "-c", WRAPPER, *argv]
    proc = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
    try:
        out, _ = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
        proc.communicate()
        raise
    return proc.returncode, out.decode().splitlines(), proc.pid

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

- `test_silence_gives_up_and_kills_the_run(tmp_path, session)`: body `exec sleep 30\n`; `code, out, group = launch_in_group(tmp_path,
  body, deadline=1, leader=session)`. The assertions on `code` (`-9 if session else 1`) and on `out` stay as they are, and `assert
  gone(read_pid(tmp_path))` becomes `assert group_gone(group)`.
- `test_a_spinner_without_a_newline_is_given_up_on_the_same_way` has the same pid race. Its pid check gets the same change, and its body
  loses `echo $$ > pid`. Its check that the spinner text reached the log still needs the shell to print within the 1-s deadline. That
  check has never failed in a kept log and stays as it is (out of the brief's scope).
- New `test_a_kiro_killed_before_its_first_line_leaves_no_process` (group leader only) reproduces the flake on purpose: body `sleep 3\necho
  $$ > pid\nexec sleep 30\n`, deadline 1. It asserts `code == -9`, that `tmp_path / "pid"` does not exist (the kill came first), and
  `group_gone(group)`. The old `read_pid` assertion fails on this body every time; the new one passes. It is leader-only because in the
  `not-leader` case the launcher kills only its child, so the shell's `sleep 3` child would outlive it.
- `read_pid` and `gone` stay for the tests whose fake writes its pid before the event the launcher acts on (`test_engine_v2_is_refused`,
  `test_a_first_event_that_is_not_run_started_is_refused`, the new effort tests).

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
no stub call that could time out:
- `test_wire_cli.py::test_the_scheduler_runner_runs_the_loop_until_there_is_nothing_to_do`: both `runner.run(...)` calls go inside `with
  wiring.overriding({RuntimeReadiness: FixedReadiness(None)}):`, the idiom of the file's `refuse` helper and of
  `test_a_ready_kiro_cli_starts_the_loop_and_leaves_no_marker` (:189-194). Every name is already imported.
- `test_exit_assistant.py::test_a_real_until_done_scheduler_process_exits_by_itself` keeps a real scheduler process. Before `start`, the
  test reopens the runtime with `testkit.health_world.with_ports(org, {SchedulerCommand: FixedSchedulerCommand([sys.executable, "-c",
  READY_SCHEDULER, "--root", str(org.root), "run", "--max-runs", "0", "--until-done"])})`, the pattern of the daemon's `STAND_IN`
  (`daemon/testing.py:434-482`). `READY_SCHEDULER` is one line, because the process inspector reads command lines line by line:
  `"import sys; from hirearchy import main; from hirearchy.app import wiring; from hirearchy.kiro import RuntimeReadiness; from
  hirearchy.kiro.testing import FixedReadiness; wiring.overriding({RuntimeReadiness: FixedReadiness(None)}).__enter__(); main(sys.argv[1:])"`.
  The process is the real `hirearchy run --until-done` with its pidfile, exit marker and log, and `SchedulerIdentity` still recognises it
  (`run` and the org root are on its command line, `daemon/_identity.py:33-36`). New imports: `SchedulerCommand` from `hirearchy.daemon`
  (the test already imports `EXIT_FILE` from there), `FixedSchedulerCommand` from `hirearchy.daemon.testing`, `with_ports` from
  `testkit.health_world`. The assertions stay as they are.

**Still exposed, never recorded failing.** Other tests run the real readiness against the stub: in-process through the CLI
(`cli/tests/test_run_command.py`, `test_run_command_assistant.py`, `test_progress_command_assistant.py`, `test_announce.py`,
`test_org_announce.py`) and in child processes (`daemon/tests/test_control.py:148`, `tests/e2e/test_scheduler_detach.py`,
`tests/e2e/test_scheduler_signal.py`). They stay as they are: they are what still exercises the real readiness against the stub, and the
final validation's flake rule covers them.

## 5. Test plan (the owner's test policy, `RES/phase-0a2/test-policy.md`)

Each commit runs FAST, scoped: the touched packages' tests, plus `tests/golden`, `tests/architecture` (deselecting
`tests/architecture/test_static_checks.py`) and `uv run python scripts/static_checks.py all`. `src/hirearchy/app/tests` joins when a
commit touches `app/`, an `api.py` Protocol or the wiring (`scheduler/_assembly.py`). Each FEAT and each fix pass runs SCOPED: that union
plus `tests/e2e`. The full `scripts/check.sh` runs only in final validation. No real kiro-cli and no `integration` test run. Every test seat
runs on claude-sonnet-5.5 at effort high or better.

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
  - `stop_of` on a genuine tail, on a tail without a mark, and on a missing log (`None` and the console line E);
  - `credit` gives `free`, then `counted` after a credited run, `""` with effects, `""` with mail sent after the stem, and `""` plus line E
    when the delivery raises.
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
- `kiro/tests/test_launch.py`, the launcher as a script, the stop:
  - `test_an_effort_warning_stops_the_run_before_any_tool_effect[group-leader|not-leader]`: the fake prints `START`, then writes
    `[warn] failed to set effort 'high': model 'claude-sonnet-5.5' offers no effort levels` to stderr, then `exec sleep 30`. Asserts out ==
    `["# kiro: run started (engine v3)", <A with none>]`, code -9 or 1, the warning on the launcher's stderr and `group_gone`. RED:
    `subprocess.TimeoutExpired` (today the run sleeps).
  - The same with the other known reason, `the engine did not load its model list in time`: the mark quotes it as it came (condition 1).
  - The same with an unknown reason after the prefix: stopped, quoted.
  - The warning before `START` (out == `[A]`), and after a completed `hirearchy::write` update (`tool effects: 1`).
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
  - 2,000 stderr lines, then the warning: the run is stopped, and the log holds the 2,000 lines, the warning and mark A, in that order.
    RED: `subprocess.TimeoutExpired`.
  - A background child holding stderr after kiro exits: the run ends within 5 s (the twin of the stdout test).
  - The first three pass today, because kiro writes the log itself. They are the guard that the new reading must keep green.
- `scheduler/tests/test_loop_effort.py` (new), the real loop with the fake agent:
  - `FAKE_EFFORT_STOP_RUNS=1`: the first run prints the warning to stderr and mark A to stdout, then SIGKILLs itself. Asserts one effort
    credit, no `agent.failure`, the relaunch and the case's run count without the stopped run.
  - `FAKE_EFFORT_STOP_RUNS=9` with `max_failures` 3: paused after 4 stopped launches, 4 credits, and root has "keeps failing".
  - RED: the fake agent ignores the variable, so no credit.
- Item 2: the hardened tests and `test_a_kiro_killed_before_its_first_line_leaves_no_process` (3). There is no RED for a test-only
  hardening; the new test shows the old assertion failing on the reproduced race.
- Item 3: the two hardened tests (4). There is no RED for a test-only hardening.

Existing tests that stay unchanged and green (condition 3; a reviewer checks with `git diff main -- <file>`):
- `kiro/tests/test_launch.py`: every existing test except the two that item 2 hardens. That covers the throttle section (from :425),
  `test_engine_v2_is_refused`, `test_a_first_event_that_is_not_run_started_is_refused`, both `test_an_end_before_the_start_*`,
  `test_the_text_copied_before_the_start_is_limited_to_4_kb`, `test_no_launcher_line_starts_with_a_closing_mark_of_the_run_log`,
  `test_each_launcher_line_comes_before_the_next_line_of_kiros_stderr` and `test_a_background_child_holding_stdout_does_not_hold_the_run`.
- `scheduler/tests/test_throttle.py`, `test_loop_throttle.py`, `test_failures.py`, `test_lifecycle.py`, `test_robustness.py`, and every
  existing test function of `test_reaper_parts.py`.
- `budget/tests/test_run_credit.py`'s existing test, `kernel/tests/test_message.py`, the credit cases of `progress/tests` and
  `reflection/tests`, `app/tests/test_scheduler_lifecycle.py`, `app/tests/test_wire_scheduler.py`, `settings/tests/test_config.py`, and the
  golden suite.

## 6. User-visible changes

1. The run log of a run that kiro-cli reports below the floor ends early with mark A and `# exit -9 after <n>s`. kiro's own stderr lines
   are in every run log as before, now forwarded by the launcher.
2. The `run.end` event of such a run carries error B1, B2 or B3, and observe and the dashboard show it.
3. The scheduler's output gains lines D and E.
4. The agent's next prompt holds credit note C.
5. Budget: a stopped launch without a tool effect is not charged, and case totals and `runs n of m` leave it out.
6. README gains sentence G.
7. Nothing changes in `status`, `progress`, `whoami`, the plan block, ORG.md, the profiles or the MCP tools. Items 2 and 3 change no
   user-visible behaviour.

## 7. SKILL.md

No change; its md5 and its 125 lines stay, and so do 0a.4's lines 72, 92 and 100 and 0a.5's line 39. Root has nothing to do: the runtime
stops, credits and relaunches by itself. A streak reaches root through the existing "keeps failing" notice. Observe's error text states
the outcome, and the throttle credit, the precedent, has no SKILL.md line either.

## 8. Out of scope

The assistant's own session (2.12), a post-run check of the session store's `effortLevel` (backlog), the spinner test's text check (3),
the other tests exposed to the readiness timeout (4), any change of `READINESS_TIMEOUT` or `START_DEADLINE`, and any change of the
throttle path beyond the shared `return_run`.

## 9. Responses to the design review

No review yet (iteration 1).

The manager's decision on the draft (`.agents/tasks/manager-decision-item1.md`, 2026-10-28) approved (a), texts A-D and G, the cost, the
declared limits and the bound of max_failures + 1. The decision's binding conditions are folded in:
1. **The prefix, for any reason.** `EFFORT_PREFIX`, `EFFORT_LINE` and `effort_warning` are in 2.2, used by `effort_stop` in 2.3. The
   input rules are in 2.7, the edge rows in 2.9 and limit 3 of 2.12, which now names the prefix only. Text A gained the example of the
   second known reason. The parenthesis of text G now says "a line beginning "failed to set effort", such as "[warn] failed to set effort
   'high': ..."" instead of "a line starting "[warn] failed to set effort"", so that it matches condition 1. The rest of G is as approved.
2. **The drain.** The drain rule is in 2.2, with the stdout-first order in `_wait_for_start` and `_stream`, an edge row in 2.9 and the
   drain tests in 5.
3. **No regression.** It is held as 2.4 and 2.14 describe, and 5 lists the existing tests that stay unchanged. The design names its two
   edits near those tests: the construction helper of `test_reaper_parts.py`, and item 2's own hardening.
