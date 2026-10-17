# orgmcp

A file-based organization of agents, run over MCP. Directories are agents, nesting is the hierarchy,
immutable message files are the only channel, and a small scheduler wakes an agent (a fresh
`kiro-cli` run) whenever its inbox has mail.

```
org/                      # root = you, the human
├── ORG.md                # mission, protocol, limits (YAML frontmatter)
├── inbox/ read/ sent/    # your mailbox
└── ceo/
    ├── AGENT.md          # charter (written by the parent)
    ├── MEMORY.md         # the agent's notes to its future self
    ├── inbox/ inflight/ read/ sent/
    ├── work/             # artifacts
    ├── runs/             # one log per run (also the budget ledger)
    └── writer/ ...       # direct reports
```

## Rules the runtime enforces

- Address = path (`ceo/writer`). Every path in tools is relative to the org root.
- An agent writes only inside its own directory. The exception is a direct report's `AGENT.md`, which the parent owns.
- Tasks go down (`delegate`, direct reports only), results go up (`report`, once per task), and notes go to the parent, reports, siblings, or a reply.
- Task state and budget are derived from the message files, never stored separately.
- Budget is counted in runs and passes down the tree: a child gets only what its parent hands it, and each delegation keeps a reserve so the parent can process the result.
- Authority only narrows: a parent cannot grant tools or a workspace it doesn't have.
- Guards: hop limit (loops), max depth/children, out-of-budget pause with a parent notice, per-run timeout, one scheduler per org, and a git commit after every run. Also:
  - Stall ladder: checked every tick, per open task. If the assignee is idle (not running, no unread mail, not paused, not waiting on delegations) for `stall_after` seconds (default 600), it gets a reminder; each further `stall_after` the runtime tells the assigner, then each ancestor up to root, then stops. State is in `.runtime/nudges.json`.
  - Consecutive failed runs pause the agent after `max_failures`. The count is kept in `.runtime/failures.json` (survives restarts) and cleared by a successful run or `orgmcp resume`.
  - `MEMORY.md` is capped at `memory_max_words` (default 800): writes and appends beyond it are refused, and an oversized memory is flagged for condensing in the next run's prompt.

## Use

```sh
uv run orgmcp init org --mission "..." --model claude-haiku-4.5
uv run orgmcp hire root ceo --role "Chief of staff" --charter @examples/ceo.md \
    --model claude-sonnet-4.6 --can-hire --max-children 3
uv run orgmcp task ceo --title "..." --goal @goal.md --acceptance @acceptance.md --budget 14
uv run orgmcp run --until-idle --max-runs 14     # or plain `run` as a daemon
uv run orgmcp status
uv run orgmcp inbox
```

Other commands: `send` (note or budget grant), `resume <agent>`, `run --once`, `mcp`, `kiro-profile`.

## Health

Health is measured from the files alone (message files and `runs/*.log`); nothing extra is stored. A run starts at
the timestamp in its log file name and ends at the log's mtime; a run is *empty* if the agent sent no message during it.

```sh
uv run orgmcp health [--agent ADDR] [--json]
```

Prints a summary line (`3 agents, 1 flagged`), then one line per agent (indented by depth) with state, budget
(left/received), runs, open tasks and the age of the oldest, results by status, rework, runs per completed task,
empty runs, time since last activity, branch totals for managers, and any flags with their reasons.
`--agent` limits it to that agent and its subtree; `--json` prints the structured data.

The MCP tool `health(agent=None)` returns the same report. Root may ask about anyone; any other agent may ask
about itself or an agent in its own subtree. By default it reports your own subtree (root: the whole organization).

"Rework" counts tasks an agent received with `revises` set: a manager sends work back with
`delegate(..., revises=<earlier task id>)` (CLI: `orgmcp task ... --revises TASK_ID`). The id must be a task the
delegator earlier sent to the same assignee.

| Flag | Meaning | Threshold key (default) |
| --- | --- | --- |
| `stuck` | open task older than the limit, and the agent is not running, has no unread mail, and is not waiting on a delegation | `stuck_after_seconds` (1800) |
| `out_of_budget` | budget <= 0 while it has unread mail or open tasks | - |
| `paused` | paused for any reason (shown in the reason) | - |
| `low_quality` | (failed + blocked + rework) / tasks received above the ratio, once enough tasks were received | `max_problem_ratio` (0.5), `min_tasks_for_quality` (3) |
| `expensive` | runs per completed task above the limit (needs a result), or too many runs since its last result while holding an open task | `max_runs_per_task` (5), `max_runs_without_result` (6) |
| `wasteful` | empty runs / runs used above the ratio, once enough runs were used | `max_empty_run_ratio` (0.5), `min_runs_for_waste` (4) |
| `idle` | no open tasks, no delegations, no unread mail and no activity for longer than the limit (measured from hiring if it never ran): a candidate to retire | `idle_after_seconds` (86400) |

Branch totals (the agent plus its subtree) sum runs, open tasks, results and rework, and show the worst flag, in the
order above (`stuck` is worst, `idle` mildest). Override any threshold in the `ORG.md` frontmatter:

```yaml
health:
  stuck_after_seconds: 900
  max_runs_per_task: 8
```

## Kiro integration

- Agent runs use `kiro-cli chat --no-interactive --agent orgmcp[-tools]`. The scheduler writes these profiles to
  `~/.kiro/agents/`. They load only the orgmcp server (`includeMcpJson: false`), so agents never see your
  other MCP servers. Identity comes from `ORG_AGENT`, which the scheduler sets per run.
- To talk to the org yourself from any kiro session, register the server globally (you act as `root`):

```json
"orgmcp": {
  "command": "uv",
  "args": ["--directory", "/Users/aminalizadeh/workspace/orgmcp", "run", "orgmcp", "mcp"],
  "env": { "ORG_ROOT": "/Users/aminalizadeh/workspace/orgmcp/org" }
}
```

MCP tools: `whoami`, `inbox`, `delegate`, `report`, `send`, `hire`, `retire`, `read`, `write`, `status`, `health`.

## Security notes

- Everything is local stdio with no network listener. Identity is enforced by the process environment, not by
  authentication: anything that can run `orgmcp mcp` with `ORG_AGENT` set can act as that agent.
- The write rules apply to the orgmcp tools only. If a charter grants kiro built-ins (`write`, `shell`), that agent
  can touch anything its OS user can. Grant them together with a `workspace` and only to agents that need them.

## Test

```sh
uv run pytest -q
```

The tests use a deterministic fake agent (`tests/fake_agent.py`) in place of kiro.
