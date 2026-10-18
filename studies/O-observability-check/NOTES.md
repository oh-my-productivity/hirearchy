# O-observability-check: observability against real kiro

Question: with the real emitter and a real `kiro-cli`, does an agent's MCP server write events tagged with the agent and
the scheduler's run id (i.e. does `ORG_RUN_ID` pass through kiro to the MCP server it spawns), and do the four views
(`trace`, `now`, `metrics`, `check`) tell the truth about it?

## Setup
- Sandbox `/tmp/orgmcp-obs-<epoch>` (removed afterwards), org built with this worktree's CLI
  (`uv --directory /Volumes/workspace/orgmcp-wt/o-integration run orgmcp ...`, branch `o-integration`).
- One top-level agent `worker` (model `claude-haiku-4.5`, no built-in tools). Task: call `whoami`, `write` one line to
  `worker/MEMORY.md`, `report` done. `orgmcp run --until-idle --max-runs 2`.
- Three tasks were run in the same org (the second and third only to sample `obs now` while a run is in flight).

## Result 1: ORG_RUN_ID passes through kiro (evidence/mcp-*.jsonl)
The file written by the MCP server kiro spawned, `.runtime/events/<day>/mcp-<pid>-<start_ms>.jsonl`, first task:

```
seq 1  proc=mcp  kind=tool.call  tool=whoami  actor=worker  run=worker@20261018T092912856677  trace=20261018T092904624658-root-a621
seq 2  proc=mcp  kind=tool.call  tool=write   actor=worker  run=worker@20261018T092912856677  args={path: worker/MEMORY.md, content_chars: 22, append: false}
seq 3  proc=mcp  kind=msg.deliver             actor=worker  run=worker@20261018T092912856677
seq 4  proc=mcp  kind=tool.call  tool=report  actor=worker  run=worker@20261018T092912856677  args={task_id: ..., status: done, summary_chars: 12}
```

`actor` is the agent (`worker`), `run` equals the scheduler's `run.start` id and the run log stem
(`worker/runs/20261018T092912856677.log`), `trace` is root's task. The same holds for the second and third runs. The
envelope `pid` is the MCP server's own (94658), the scheduler's `run.start` carries `child_pid`/`pgid` of the kiro
process. The prompt, the output and the message bodies are not in any event (only `content_chars`/`summary_chars`).

## Result 2: the views (evidence: trace.txt, now-running.txt, metrics.txt, check.txt, events-run.txt)
```
$ orgmcp obs trace 20261018T092904624658-root-a621
trace 20261018T092904624658-root-a621 "Tool check" -> worker: done
     +0s  root -> worker task "Tool check" +2 run(s)
     +8s    run 20261018T092912856677 ok, ran 14s, queued 8.2s, 3 call(s) [report×1 whoami×1 write×1]
    +20s    worker -> root result (done) "Tool check" +1 run(s)
totals: wall 20s | runs 1 (budget given 2, returned 1) | run time 14s | queue 8.2s | waiting on you 0s | tool calls 3 (0 refused)

$ orgmcp obs now            # sampled 9 s into the third run, scheduler started as `orgmcp --root <org> run --until-idle`
scheduler: running pid 5585 (until_idle, up 9.0s, last heartbeat 9.0s ago)
runs in flight 1/3:
  worker 9.0s Third check trace 20261018T093211981048-root-723b
queued, not running: none
waiting on you: nothing

$ orgmcp obs metrics --since 1h        (after task 1)
runs 1: ok 1, failed 0, timeout 0, killed 0 | duration p50 14s p95 14s max 14s (n=1) | queue p50 8.2s p95 8.2s (n=1)
tool calls 3, refused 0 (0.0%)

$ orgmcp check
(a)..(f) PASS ... all checks passed        # (f): pid 5585 is this organization's scheduler
```
`progress` agrees with the trace: `"Tool check": done. runs 1 of 2 (1 returned)`.

## Defect found and fixed
`obs now` (and `check` (f)) reported the live scheduler as `unverified` (`now-running-BEFORE-fix.txt`): the sandbox lives
under `/tmp`, which macOS resolves to `/private/tmp`; `Org.root` is the resolved path but the scheduler's command line
(`orgmcp --root /tmp/orgmcp-obs-.../org run ...`) carries the spelling the user typed, and `_looks_like_scheduler_of` compared
strings. It now also compares the resolved `--root` argument (absolute or `~` paths only; relative ones still cannot be
compared). The real check was re-run once: `scheduler: running pid 5585 ...` and `(f) PASS` (`now-running.txt`).
This also affected `status`/`start`/`stop` for any org addressed through a symlink; a unit test covers it.

## Observations
- Queue 8.2 s of task 1 is real: the task was given, then the scheduler was started a few seconds later (queue wait = run
  start minus the batch's earliest message). Task 3 (scheduler started right after) shows 105 ms.
- A failing `orgmcp check` is itself recorded as a `cli.command` error (`error="exit 1"`), so it shows up under
  "errors in the last 15 min" of `now` for a while.
- The agent called `write` on its memory in the second and third runs although the task did not ask for it: the run prompt
  tells agents to update `MEMORY.md` before stopping, and the tool-call record makes that visible.

## Safety
- md5 of every file in `~/.kiro/agents/` (12 files) and of `~/.kiro/settings/mcp.json` taken before and after
  (`evidence/kiro-agents.{before,after}.md5`, `evidence/mcp-json.{before,after}.md5`; mcp.json was never read or printed):
  identical after cleanup. During the run the scheduler wrote one per-org profile
  (`orgmcp-orgmcp-obs-<epoch>-or-eba177.json`); it was deleted only after checking that its `ORG_ROOT` was exactly the sandbox org.
- No process referencing the sandbox remained (nothing needed killing); no other org was touched. The sandbox was removed.
