# F2: tool names when the agent holds kiro's built-in `read` / `write`

> Repeatable form: `tests/integration/test_real_kiro.py::test_builtin_write_and_org_write_side_by_side` (opt-in, `pytest --run-integration`).

Problem (F-read-experiment, study D F1): kiro lists MCP tools by their plain names, so a built-in `read`/`write` shadows
the orgmcp tool of the same name. Round F worked around it for `read` (the built-in may read the org by absolute path).
For `write` nothing worked: an agent with built-in `write` (code orgs) could not call orgmcp `write`, so it could not
save `MEMORY.md` or org `work/` files, although every prompt said `@orgmcp/write`.

## Fix

* `Org.tool_names(addr)` (core): charter `tools` holds `write` -> orgmcp write is `org_write`; holds `read` -> orgmcp read
  is `org_read`. Otherwise (and for root) `write` / `read`, exactly as before. `shell` alone changes nothing.
* `build_server` registers `read`/`write` under those names (the shadowed plain name is not registered; descriptions say
  "called `org_write` for you").
* Prompt texts name the tool the agent has: Files section (one explicit line: "kiro's built-in `write` has the name
  `write`; the orgmcp write tool is `@orgmcp/org_write` for you: use it for MEMORY.md and org files"), the read-only
  inputs line, the stray-file notice, the run_prompt footer ("update your memory with `@orgmcp/org_write`(...)").
  ORG.md's shared rules still say `@orgmcp/write` generically; the per-agent line says to use the `org_` name wherever
  ORG.md names it. Prompts of agents without built-in `read`/`write` are byte-identical to main (test: sha256 of the
  old output vs the new one for `plain`, `shell`-only and inputs-only agents).
* README "Workspaces, inputs and confinement" updated to the code after round F (read: workspace + inputs + org, no deny;
  write: workspace only, org denied; shadowing; names; relative vs absolute paths).

## Real kiro verification (kiro-cli, `claude-haiku-4.5`, 2 runs; logs in `evidence/`)

Sandbox org with one agent `dev`, tools `[read, write, shell]`, workspace `S/ws`, profile
`...-read-shell-write-x3f904e23` (confined). Built with this worktree's CLI; run with `orgmcp run --until-idle`.

Run 1 (`evidence/run1-dev.log`): task = write `S/ws/hello.txt` with the built-in write; write `dev/work/note.md` and
`dev/MEMORY.md` with the orgmcp tool; report done.

```
  - orgmcp tools (shown as `@orgmcp/org_write`, `@orgmcp/org_read`, ...): ... (orgmcp `org_write` only).      <- prompt
Before you stop, update your memory with `@orgmcp/org_write`(path="dev/MEMORY.md", ...) ...                    <- prompt
[tool] Creating hello.txt                  <- built-in write, workspace
[tool] status: Completed
[tool] Running: @orgmcp/org_write          <- orgmcp write, twice
[tool] Running: @orgmcp/org_write
[tool] Running: @orgmcp/report
# exit 0 after 36s
```

Results: `S/ws/hello.txt` = `hello from builtin write`; `dev/work/note.md` = `note via orgmcp`; `dev/MEMORY.md` (empty before the
run) = `task done, both files written`. Nothing stray in the workspace (only `hello.txt`), no `# warning:` in the log.

Run 2 (`evidence/run2-dev.log`): read `dev/work/note.md` by relative path with the orgmcp read tool, `S/ws/hello.txt` with
the built-in read.

```
[tool] Running: @orgmcp/org_read           <- orgmcp read, relative org path
[tool] Reading hello.txt:1                 <- built-in read, workspace file
[tool] Running: @orgmcp/report
[tool] Running: @orgmcp/org_write          <- MEMORY.md update from the prompt footer
```

Both tools are callable side by side: the shadowing is gone for `write` and `read`.

## Safety

md5s of every file in `~/.kiro/agents/` and of `~/.kiro/settings/mcp.json` before and after: identical
(`evidence/safety-before.txt`, `safety-after.txt`; contents never printed). The one profile whose `ORG_ROOT` was the
sandbox org was deleted; no process referenced the sandbox afterwards; the sandbox directory was removed. No other org
was touched.

## Risks / notes

* Existing orgs: a running agent's prompt (built from the charter at run time) changes names the moment it is upgraded;
  its MEMORY.md may say "`@orgmcp/write`" from earlier runs, the per-agent Files line overrides it. The scheduler's own
  warning text (`scheduler.py`, "built-in write shadows orgmcp write?") is unchanged.
* Anything outside the prompts that calls the tools by name `write`/`read` for such an agent (own scripts, external MCP
  clients acting as that agent) must use the `org_` names.
