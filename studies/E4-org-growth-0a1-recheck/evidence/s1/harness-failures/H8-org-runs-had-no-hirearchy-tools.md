# s1: org runs ran without the hirearchy tools (protocol 11, H8 candidate); facts only

## What happened
- Turn 4 (Lena's approval + "2026-10-05.md"): the assistant called `create_org` (03:46:18Z), `apply_org` (03:46:27Z), `request` (03:46:29Z; task `20261022T034629280991-root-cb6a`, budget 15), `start` (03:46:31Z; scheduler pid 12848).
- Org run 1: `lead@20261022T034631122838`, claude-sonnet-4.6, 104 s, exit 0. Org run 2: `lead@20261022T034833740575`, claude-sonnet-4.6, 86 s, exit 0 (started after the assistant's `send` to lead at 03:48:33Z, a nudge).
- Neither lead run made a single hirearchy tool call. `grep -c "Running: @hirearchy"` over both run logs = 0. Their `[tool]` lines are only built-in `read` calls (24 `status: Completed`, 6 `status: Failed`, e.g. "[denied] tool permission approval is not supported in non-interactive mode"). In both logs the model says the hirearchy tools are not in its tool list ("I only see `read`"; "Tools beyond hirearchy: read" is the prompt's own line).
- The `.runtime/events` of the org hold no event from an agent-bound hirearchy MCP server (no `proc: mcp` file with `actor: lead`); the only mcp event file is the assistant's server (pid 12808, actor root).
- Result: task `20261022T034629280991-root-cb6a` = "stalled (lead has not reported and nothing is running)"; `progress`: "runs 2 of 15"; `status`: lead budget 13, open 1, delegated 0; writer and reviewer ran 0 times; scheduler.log: "waiting on you: ... needs a decision (lead holds it and nothing is running)". No memo exists; `deliverables/` was never created.
- The assistant reported this to Lena in turn 4 (no memo delivered), called `stop()` at 03:50:20Z, and offered two options (retry after someone checks the setup, or write the memo itself outside the team).

## Comparison facts
- The org scheduler profile `hirearchy-hirearchy-e4-s1-17926405-dcd590-read-xc7b006b8.json` (copy in `../profiles/`) differs from E3's (`E3-org-growth-0a-live/evidence/profiles/hirearchy-hirearchy-e3-1792595952-1cee14-read-x853fd920.json`) only in name, description and the sandbox path.
- The org runs use the scheduler's command `kiro-cli chat --no-interactive --agent <profile> --model <m>` (the `# cmd:` line of the run log), the same shape as in E3, kiro-cli 2.33.0 in both.
- The workspace settings file `S/.kiro/settings/cli.json` does not apply to the org agents' cwd (`S/org/lead`): `kiro-cli settings list` there shows only `chat.enableWorkflows = true (global)`.
- Global settings unchanged since E3's `safety-before.txt` (`cli.json` md5 `680bab99...`, `mcp.json` md5 `9be6a6ef...`). The env of the facilitator's shell has `KIRO_AGENT_ENGINE=kas` and `KIRO_API_KEY` (value not recorded); the org runs inherit the env of the assistant's MCP server process.

## Diagnostic calls (after the stream stopped; no call against the org)
Throwaway profile `hirearchy-study-e4-diag` (copy: `diag-profile.json`): the org-run profile shape (`tools: ["@hirearchy","read"]`, `allowedTools: ["@hirearchy"]`, `includeMcpJson: false`, `ORG_REQUIRE_AGENT=1`, `ORG_ROOT=/tmp/hirearchy-e4-diag/org` never created), with the MCP command `/bin/sh -c 'env | grep ... > /tmp/hirearchy-e4-diag/mcp-env.txt; exec .../hirearchy mcp'`. cwd `/tmp/hirearchy-e4-diag/cwd` (no `.kiro` dir).
1. `ORG_AGENT=lead kiro-cli chat --no-interactive --agent hirearchy-study-e4-diag --model claude-haiku-4.5 "List the names of all tools you can call, one per line. Do not call any tool."` -> reply `read`. `mcp-env.txt` was NOT created (the MCP command never ran). (`diag-call1.stdout.txt`)
2. Same with `--trust-all-tools` and no `--model` -> a reply that does not list tools; `mcp-env.txt` not created.
3. Same as 1 with `env -u KIRO_AGENT_ENGINE` -> reply `read`; `mcp-env.txt` not created. (`diag-call3-no-KIRO_AGENT_ENGINE.stdout.txt`)
4. Same as 1 with `env -u KIRO_API_KEY`: no output within 200 s (the call hung and was killed; process killed by `pkill -f hirearchy-study-e4-diag`).
The diag profile was deleted afterwards (`../profiles/deletions.txt`). Root cause not determined: what is established is that, in this environment on 2026-10-22, a `kiro-cli chat --no-interactive --agent <profile with a command-based MCP server>` run does not start the profile's MCP server and offers only the built-in `read`; the E3 org runs (2026-10-21) did start it.
