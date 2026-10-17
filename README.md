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
- Guards: hop limit (loops), max depth/children, consecutive-failure pause, out-of-budget pause with a parent notice, stall nudges then escalation, per-run timeout, one scheduler per org, and a git commit after every run.

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

MCP tools: `whoami`, `inbox`, `delegate`, `report`, `send`, `hire`, `retire`, `read`, `write`, `status`.

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
