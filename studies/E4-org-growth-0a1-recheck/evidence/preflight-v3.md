# E4 harness preflight (V3), manager-decision-restart.md item 3

**Result: PASS.** Run 2026-10-22, 18:17-18:22 UTC (local WEST = UTC + 1 h). No stream, sandbox `S`, probe or injection was started. No product file was changed, nothing was committed or staged.

Gate checks before anything: `md5 -q evidence/protocol.md` = `584b6cc71e3d073d10d45c1c2e64325e` (matches). `md5 -q evidence/protocol-amendment-1.md` = `1ec9e658e3bd59ab9d9f785986a26c19` = content of `protocol-amendment-1.md5` (matches). Neither file was edited.

## Environment
- Repo `main` = `7d86c31f1b0d52e7ea9467ce72c8d9322e71a71c`; `git status --porcelain` = `?? docs/research/` and `?? studies/E4-org-growth-0a1-recheck/` only.
- `kiro-cli --version` = `kiro-cli 2.33.0` (KAS 0.66.48 in the kiro logs).
- `hirearchy` on PATH = `~/.local/bin/hirearchy` -> uv tool install, editable, `file:///Volumes/workspace/hirearchy` (imports `/Volumes/workspace/hirearchy/src/hirearchy/kiro/_launch.py`, i.e. 7d86c31).
- `KIRO_API_KEY` set in the environment (value never read or printed). `HIREARCHY_STATE_DIR` unset, so the state dir is the default `~/Library/Application Support/hirearchy` (it did not exist before this step).

## 1-2. Scratch org and real scheduler run
Scratch dir: `/tmp/hirearchy-e4-preflight-1792693126` (outside any `/tmp/hirearchy-e4-s1r-*`, `-s2-*`, `-s3-*`). Lead model: **claude-sonnet-4.6** (protocol 4.3 lead seat; org default also set to it).

```
hirearchy init /tmp/hirearchy-e4-preflight-1792693126 --mission "E4 harness preflight (throwaway)" --model claude-sonnet-4.6
hirearchy --root /tmp/hirearchy-e4-preflight-1792693126 hire root lead --role Lead --charter "You are the lead of a throwaway preflight org. Do exactly the task you are given, using your hirearchy tools, then report it done." --tools read,write --model claude-sonnet-4.6
hirearchy --root /tmp/hirearchy-e4-preflight-1792693126 task lead --title "Preflight note" --goal "Use the hirearchy org_write tool to write the file notes/preflight.txt in the organization with the single line: E4-PREFLIGHT-OK. Then call the hirearchy report tool with status done." --acceptance "notes/preflight.txt holds E4-PREFLIGHT-OK; reported done." --budget 2
  -> task 20261022T181846737551-root-80a1 -> lead (budget 2)
perl -e 'alarm shift; exec @ARGV' 900 hirearchy --root /tmp/hirearchy-e4-preflight-1792693126 run --until-done --max-runs 2
  -> lead: started run (1 message(s)) / lead: run finished in 83s / scheduler exiting: finished: no open tasks   (exit 0, 18:18:51Z-18:20:14Z)
```

Run log header (`preflight-v3/lead-run.log`): `# cmd: .../python -I -S /Volumes/workspace/hirearchy/src/hirearchy/kiro/_launch.py --start-deadline 60 -- kiro-cli chat --no-interactive --agent hirearchy-hirearchy-e4-preflight-1-1406d8-read-write-x48ac051a --model claude-sonnet-4.6 --v3 --require-mcp-startup --output-format stream-json <prompt on stdin>`; `# kiro: run started (engine v3)`; `[run finished] success (end_turn)`; `# exit 0 after 83s`. cwd was the scratch dir under the state dir, `.../kiro-cwd/hirearchy-e4-preflight-1-1406d810aa50fd41/lead-8cb33b27`. Org kiro session: `modelId` claude-sonnet-4.6.

## 3. Tool-call evidence (hirearchy tool.call events by the lead, real scheduler run)
`hirearchy --root <scratch> obs events --kind tool.call` -> "4 of 4 matching event(s), oldest first":

```
18:19:26.737 mcp lead tool.call org_write REFUSED 1ms error="you may only write inside your own directory. Paths are relative to the org root, so yours start with `lead/`: e.g. `lead/MEMORY.md` or `lead/work/notes.md` (got `notes/preflight.txt`)" error_type=OrgError args=path=notes/preflight.txt,co…
18:19:41.331 mcp lead tool.call org_read ok 1ms args=path=. run=lead@20261022T181852089488 trace=20261022T181846737551-root-80a1
18:20:00.678 mcp lead tool.call org_write ok 2ms args=path=lead/MEMORY.md,content_chars=158,append=False run=lead@20261022T181852089488 trace=20261022T181846737551-root-80a1
18:20:06.179 mcp lead tool.call report ok 4ms args=task_id=20261022T181846737551-root-80a1,status=failed,summary_chars=340 run=lead@20261022T181852089488 trace=20261022T181846737551-root-80a1
```

Raw event lines (`.runtime/events/2026-10-22/mcp-25128-1792693166736.jsonl`, copy in `preflight-v3/mcp-events.jsonl`):

```
{"v":1,"ts":"2026-10-22T18:19:26.737055+00:00","seq":1,"proc":"mcp","pid":25128,"kind":"tool.call","actor":"lead","run":"lead@20261022T181852089488","trace":"20261022T181846737551-root-80a1","tool":"org_write","ok":false,"ms":1.03,"error":"you may only write inside your own directory. Paths are relative to the org root, so yours start with `lead/`: e.g. `lead/MEMORY.md` or `lead/work/notes.md` (got `notes/preflight.txt`)","error_type":"OrgError","args":{"path":"notes/preflight.txt","content_chars":15,"append":false}}
{"v":1,"ts":"2026-10-22T18:19:41.331684+00:00","seq":2,"proc":"mcp","pid":25128,"kind":"tool.call","actor":"lead","run":"lead@20261022T181852089488","trace":"20261022T181846737551-root-80a1","tool":"org_read","ok":true,"ms":0.83,"error":null,"error_type":null,"args":{"path":"."}}
{"v":1,"ts":"2026-10-22T18:20:00.678039+00:00","seq":3,"proc":"mcp","pid":25128,"kind":"tool.call","actor":"lead","run":"lead@20261022T181852089488","trace":"20261022T181846737551-root-80a1","tool":"org_write","ok":true,"ms":1.8,"error":null,"error_type":null,"args":{"path":"lead/MEMORY.md","content_chars":158,"append":false}}
{"v":1,"ts":"2026-10-22T18:20:06.179735+00:00","seq":5,"proc":"mcp","pid":25128,"kind":"tool.call","actor":"lead","run":"lead@20261022T181852089488","trace":"20261022T181846737551-root-80a1","tool":"report","ok":true,"ms":4.28,"error":null,"error_type":null,"args":{"task_id":"20261022T181846737551-root-80a1","status":"failed","summary_chars":340}}
```

Run log call lines (P3 pattern `^\[tool\] @hirearchy/\w+`): 4 lines (`org_write`, `org_read`, `org_write`, `report`) = 4 `tool.call` events. Example: `[tool] @hirearchy/org_write {"tool_id":"hirearchy::org_write","arguments":{"path":"notes/preflight.txt","content":"E4-PREFLIGHT-OK"}}`, then `[tool failed] @hirearchy/org_write ...`.

Reading: the preflight criterion (a hirearchy `tool.call` by the lead through the real scheduler, visible in `obs events` and the org's event files) is met. No readiness refusal, no `# kiro:` failure line, `scheduler.exit` = `finished: no open tasks`.
Note (facts, not a failure of the preflight): the task itself ended `failed`. My preflight task text asked for `notes/preflight.txt`, outside the lead's own directory, and the product's `org_write` refused it by design (first event above). The lead then wrote `lead/MEMORY.md` and reported `failed` with that reason. This was a mistake in my throwaway task wording, not a harness fault; the harness question (do org agents get and use hirearchy tools under V3?) is answered by the four events. The preflight org was not rerun.

Files kept (small copies, taken before deletion): `preflight-v3/lead-run.log`, `mcp-events.jsonl`, `obs-events-tool-call.txt`, `obs-events-tool-call.jsonl`, `load-check.stdout.txt`, `load-check.stderr.txt`.

## 4. Deletion of the scratch org
Deleted (exact paths, with `rm -rf`; each guarded by a path-prefix check):
- kiro home of the scratch org: `/Users/aminalizadeh/Library/Application Support/hirearchy/kiro-home/hirearchy-e4-preflight-1-1406d810aa50fd41` (held `agents/hirearchy-hirearchy-e4-preflight-1-1406d8-read-write-x48ac051a.json`, md5 `1fbf9eb3fc05c832f0525a5075ef1811`, `ORG_ROOT` `/private/tmp/hirearchy-e4-preflight-1792693126`, plus `sessions/`, `session-index/`, `logs/`, `settings/`);
- scratch cwd of the same org: `/Users/aminalizadeh/Library/Application Support/hirearchy/kiro-cwd/hirearchy-e4-preflight-1-1406d810aa50fd41`;
- the scratch org dir: `/tmp/hirearchy-e4-preflight-1792693126`;
- then `rmdir` of the now-empty `.../hirearchy/kiro-home`, `.../hirearchy/kiro-cwd` and `.../Library/Application Support/hirearchy` (the state dir did not exist before this step; it is absent again).

Checked afterwards: `ls -d /tmp/hirearchy-e4-preflight-*` finds nothing; `pgrep -fl hirearchy-e4-preflight` finds nothing. Nothing was written to `~/.kiro/agents` by the scratch org (V3 puts the org's scheduler profile in its own kiro home). No other path was removed. Pre-existing `/tmp/hirearchy-e4-*` dirs (`diag`, `prep-1792639838`, `probe-1792640374`, `s1-1792640562`) were not touched.

## 5. Fresh prep profile and V3 load check
- Profile created: **`~/.kiro/agents/hirearchy-study-e4-prep-1792693245.json`** (name `hirearchy-study-e4-prep-1792693245`), md5 `0a0ee9e3557a0a86e2fe995a296e5e47`. Content = protocol 4.2 JSON (V3 shape: `permissions.rules` `[{capability: all, effect: allow}]`, `hooks: []`, `tools: ["*"]`, `includeMcpJson: false`, model `claude-sonnet-5.5`, hirearchy MCP server `uv --directory /Volumes/workspace/hirearchy run hirearchy mcp`, both skill resources), `ORG_ROOT` = `/tmp/hirearchy-e4-prep-1792693245/org` (never created). Same recipe as the earlier `hirearchy-study-e4-prep-1792639838` (a template copy is in `harness/hirearchy-study-e4-prep-1792639838.json.deleted-by-manager`); that earlier profile is no longer in `~/.kiro/agents` and was not touched.
- Prep sandbox: `/tmp/hirearchy-e4-prep-1792693245/` with `.kiro/skills/hirearchy/SKILL.md` (md5 `573495bb613f19f7c07ce86508ebae4f`) and `.kiro/settings/cli.json` (the probe's `harness/workspace-cli.json`: `{"chat.disableInheritingDefaultResources": true, "chat.enableWorkflows": false}`). Left in place, like the earlier prep sandbox.
- Load check (18:20:45Z), cwd `/tmp/hirearchy-e4-prep-1792693245`:
  `kiro-cli chat --v3 --no-interactive --trust-all-tools --agent hirearchy-study-e4-prep-1792693245 "List the names of the skills you can activate, one per line. Do not activate any skill and do not call any tool."`
  - **Result: loaded, exit 0.** Reply listed: autoresearch, commit-work, hirearchy, reverse-engineer-anything, skill-generation, test-driven-development, workflow-suggest.
  - Session `sess_30a86dd0-ab96-422f-b568-f3912c6040fa`: `agentMode` `hirearchy-study-e4-prep-1792693245`, `modelId` claude-sonnet-5.5, `effortLevel` high, `workspacePaths` `/private/tmp/hirearchy-e4-prep-1792693245`. No tool call; `/tmp/hirearchy-e4-prep-1792693245/org` does not exist.
- Safety fence: `md5` of `~/.kiro/agents/*`, `~/.kiro/settings/*` and `~/.kiro/skills/hirearchy/SKILL.md` before vs after: the only difference is the new prep profile above. `/Users/aminalizadeh/organization` was not touched. The prep profile is a study-created profile; the last stream's cleanup deletes it.

## Verdict
PASS: the lead (claude-sonnet-4.6) made hirearchy `tool.call`s through the real scheduler under kiro-cli 2.33.0 at 7d86c31; no readiness refusal; the assistant profile shape loads under `--v3`. s1r may start once the manager releases it.
