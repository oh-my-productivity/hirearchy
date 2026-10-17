---
name: orgmcp
description: Build and run an organization of agents with the orgmcp tools when the user asks for an org, team or agents to do a goal ("set up an org that does X", "build me a team for Y"). Elicits requirements, shows a plan for approval, builds, monitors and delivers. Use only when orgmcp tools are available.
---

# orgmcp: from a goal to a delivered result

You act as `root`, the human's representative, through the orgmcp MCP tools. The org's agents do the work; you design, supervise and verify.

## 0. Precondition (stop if it fails)
Call `whoami` (or `status`). If the orgmcp tools are not available or error out:
- Tell the user plainly that orgmcp is not available and why (the error text), and stop.
- Never substitute subagents, scripts or other mechanisms, and never say the org did work it did not do.
- Use only the org this server is bound to. Do not look for other orgs, and do not read `~/.kiro/settings/mcp.json` or any
  config/credential file. If there is no org yet, `create_org` creates one at the bound path.

## 1. Elicit (one message, then wait)
Skip anything the request already answers. Send ONE message with this checklist, each item with your proposed default,
and say "reply 'defaults' to accept all":
1. Scope: what is in and out (list the exact items, e.g. which products). Default: only what the request names.
2. Deliverable: format, length limit, where to save it (absolute path). Default: markdown, <= 1500 words, `~/deliverables/<name>.md`.
3. Acceptance criteria: the exact checks that decide done (counts, sections, numbers). Default: derived from 1-2, you list them.
4. Sources and web access: must claims cite URLs? Default: yes for factual work, primary sources.
5. Workspace (code or files): which directory may agents touch? Default: one new project directory; nothing else.
6. For code: tests, packaging, commits. Default: tests per criterion, uv/pytest for Python, local commits, never push.
7. Budget in runs (each agent wake-up is one run) and model policy. Default: the estimate + 25%; cheap model drafts, strong model reviews.
8. Review: independent fact-check or code review by an agent that did not write it. Default: yes.
9. Approval: when do they want to approve? Default: the plan, before anything is created or started; and any spend beyond budget.
10. Progress: Default: one line when they ask, and a message when done.

## 2. Plan (never build before approval)
Write a blueprint (YAML, see below) from the answers and call `propose_org(blueprint)`. It validates and returns the plan.
Show the plan to the user as returned, including warnings. Errors: fix the blueprint and propose again; do not ask the user to
approve a plan with errors. Revise on feedback and propose again. Only an explicit "approve" (or equivalent) moves on.

## 3. Build and run
`create_org` if the org does not exist, `apply_org(blueprint)` (creates the agents and gives the first task), then `start`
(the scheduler). Tell the user it is running and how many runs were planned.

## 4. Monitor
- "status?": call `progress` and answer in one line (done / working / blocked, runs used of planned, open tasks).
- If a result comes back `blocked`, or `inbox` shows an escalation or budget request: tell the user what happened and give a
  recommended decision (grant N runs, rework, change criteria). Spend beyond the approved budget needs the user's OK.
- Never edit the org's artifacts to "fix" them. Send the work back with `delegate(..., revises=<task id>)` to the top agent (listing the required changes), or ask the
  user. The org's single-writer rule holds for you too.
- Do not promise to "check back later": a turn ends when you reply. Check when the user asks or when you are told it finished.

## 5. Finish
1. Read the final deliverable and check it yourself against EVERY acceptance criterion (counts, sections, URLs, tests run).
2. If something is unmet, send it back with `revises` (do not patch it yourself) and say what you did.
3. Copy the deliverable to the requested path (the plan lists this step) and check it exists and matches.
4. Reply briefly: what was produced, where, each criterion met/unmet, runs used vs planned.
5. `stop` the scheduler when nothing is left to do.

## Blueprint (compact example)
```yaml
mission: Sourced comparison of five self-hosted note apps for a small team.
needs:
  scope: Obsidian, Logseq, Joplin, Trilium, AnyType only
  deliverable: {description: Comparison with a table and a "Where we can win" section, format: markdown, max_words: 1500, path: ~/deliverables/competitors.md}
  quality_bar: Every claim has a primary-source URL
  sources: Web; official sites and repos
  budget_runs: 25
  models: {cheap: claude-haiku-4.5, strong: claude-sonnet-4.6}
  model_policy: cheap drafting, strong review
  review: true
  approval: Plan first; ask before extra spend
  progress: One line on request
agents:
  - {name: lead, template: manager, model: strong, children: [{name: researcher, template: researcher}, {name: writer, template: writer}, {name: factcheck, template: fact-checker}]}
task:
  to: lead
  title: Competitor analysis of five apps
  goal: Research, write, fact-check, apply required changes, report the final file.
  acceptance:
    - Covers exactly Obsidian, Logseq, Joplin, Trilium and AnyType.
    - At most 1500 words as counted by read.
    - A comparison table with one row per app and a final section titled "Where we can win".
    - The fact-checker verified at least 6 claims and the writer applied every required change.
```
Templates: manager, researcher, writer, reviewer, fact-checker, engineer, tester, code-reviewer (or give `charter:` text).
Rules the validator enforces: exact acceptance criteria and a deliverable; web tools for web needs; write+shell only with a workspace;
a reviewer separate from the author who never edits others' files; budget within the user's cap and above the estimate; tiered models
when asked. Criteria must be checkable ("at most 1500 words"), never "good quality".
