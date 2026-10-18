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
  config/credential file. If there is no org yet (`whoami` says "Setup"), `create_org(mission=...)` creates one at the bound
  path (pass `path=<absolute path>` only if the tool says none is bound).

## 0b. The org already exists: look for a service first
Before building anything, call `services()`. If one fits the ask, never build a new org or team: `request(service, inputs)` (tell the
user the inputs and the per-request budget in one line; their asking for it within the approved per-request budget is the approval),
then `start()`, monitor and finish as below.

## 1. Elicit (one message, then wait)
Once, or repeatedly? Recurring work ("every week", "whenever I...", "for each new ...") is a **service**, not a one-off: also ask which
inputs change per request and what stays fixed (criteria, format, place), and use `blueprint_example(kind, service=True)` in step 2.
Skip anything the request already answers. Send ONE message in plain words (the user may not be technical), each item with a
proposed default where a generic default exists, and say "reply 'defaults' to accept the proposed ones":
1. Scope: what is in and out. **If it is a list (apps, competitors, features, topics, files), ask for it. Never invent a default
   list.** Offer defaults only for things with a sensible generic default (format, length, review, budget).
2. Deliverable: format, length limit, where it goes. Default place: a new `deliverables/` folder in the user's current
   directory (use the absolute path, e.g. `<cwd>/deliverables/<name>.md`) and say so plainly: "I'll put it in a new folder
   called deliverables here". Default: markdown, <= 1500 words.
3. Acceptance criteria: the exact checks that decide done (counts, sections, numbers). Default: derived from 1-2, you list them.
   For extraction or summary work ("what was decided, who does what", "list the risks") ask whether informal or unlabelled items
   count, and write the answer into the criteria from the first version ("every commitment, including informal ones in prose").
4. Sources: web with a URL per claim (`research`), or only the user's own files (`documents`: ask which folder; it goes into
   `needs.inputs` as an absolute path of a folder that exists). Default: web for factual work.
5. Code only: workspace (one new project directory), tests, packaging, commits. Default: tests per criterion, uv/pytest for
   Python, local commits, never push.
6. Budget in runs (each agent wake-up is one run) and models. Default: the estimate + 25%; cheap model drafts, strong reviews. A service's per-request
   budget is the plan's estimate + 25% (the lead wakes once per result: about 2 runs per delegation + 1); if the user's cap is lower, say
   in one line what that risks. If they ask for cheap models, keep the lead (manager) and
   the final verifier on the strong model and say why in one line: "the lead decides how every other run is spent".
7. Review by an agent that did not write it (default yes); when they want to approve (default: the plan, before anything
   starts, and spend beyond budget); progress (default: one line when they ask).

## 2. Plan (never build before approval)
1. `blueprint_example(kind)` with kind `research`, `documents`, `code` or `analysis` (data from the user's files: read-only data, a checked script) returns a YAML template with every field explained. Edit
   it (replace every <PLACEHOLDER>, keep only what the user said) and call `propose_org(blueprint=<the YAML text>)`. It validates,
   writes nothing and returns the PLAN FOR YOU block, Details and a `plan_id`.
2. Show the PLAN FOR YOU block to the user **exactly as written** (one plain-words intro line before it is fine). Do not
   summarize or reword it: it is what they approve (team, models, budget, checks, delivery place, warnings).
   A services-only plan says "Nothing runs until you ask for a request": after approval tell the user they can ask any time.
3. Errors: fix the blueprint and propose again; never ask the user to approve a plan with errors. Revise on feedback and propose
   again (each change gives a new `plan_id`).
4. Warnings in the block (for example no model policy, built-in `write` on a non-code goal): settle them with the user BEFORE you
   ask for approval (ask which models, then propose again) or state each one plainly in your intro line. Never leave one silent.
   The Budget lines say what happens if the check still fails after one rework: you will come back to the user first.
5. Wait for an explicit "approve" (or equivalent). Your own judgment that the plan is good is not approval.

## 3. Build and run
1. `create_org(mission=...)` if the org does not exist yet.
2. `apply_org(blueprint=<the approved YAML, unchanged>, approved=True, plan_id=<from propose_org>)`: creates the agents and gives
   the first task. It refuses a missing or different `plan_id`, so you cannot apply something the user did not see.
3. `start()` (skip it if `apply_org` says a scheduler is already running or that nothing runs yet). It ends by itself when the work is done.
Tell the user it is running and how many runs were planned (a ceiling: runs the team does not spend come back automatically).

## 4. Monitor
- "status?": call `progress()` (or `progress(task_id=...)`) and answer in one or two lines (done / working / blocked, runs used of
  planned, what needs the user). Do not answer from memory or guesses.
- You cannot notify the user later: a turn ends when you reply. Never say "I'll tell you when it's done". If they want to be told
  when it finishes, say you will wait now and call `progress(wait_seconds=240)`; repeat while they are willing to wait (it returns
  early on done/failed/blocked/stalled or when something needs them). Otherwise tell them to ask "status?".
- If a result comes back `blocked`, or `inbox` shows an escalation or budget request: tell the user what happened and give a
  recommended decision (grant N runs with `send(to=<agent>, body=<why>, budget=N)`, rework, change criteria). Spend beyond the
  approved budget needs the user's OK. A rework needs about 2 runs per delegation it requires + 1. The `send(budget=N)` reply says what
  the recipient can hand down: read it; if it cannot delegate, grant enough in one go (ask the user once, with that number). Ask at the FIRST budget request, with your recommendation; never wait until the reserve
  is spent. Before asking for more, look for stranded runs (`status`/`progress`/`health`: an idle team holding unspent runs):
  `reclaim(report=<agent>)` pulls them back from your direct reports (a lead does the same with `reclaim` on its own team: ask
  it by note), and only the shortfall goes to the user.
- `progress(wait_seconds=N)` also waits on a `blocked` task while its lead can still run (after a grant + `start()`); never poll
  with `sleep` in a shell. Every unread note, budget request and escalation is listed under "Needs you" with its message id.
- `progress` / `start` saying "waiting on you" means nothing can move without the user (an agent is out of runs or keeps failing,
  or a task is stalled). Give the options it lists: grant runs, then `start()`; or accept what exists. The scheduler exits by
  itself a few minutes after that, and `start()` refuses until something changes.
- Never edit the org's artifacts to "fix" them. Send the work back with `delegate(to=<top agent>, title=..., goal=<required changes>,
  acceptance=<the criteria, verbatim>, revises=<task id>)`, or ask the user. If `progress` says the scheduler is stopped
  ("finished") and you sent more work, call `start()` again.

## 5. Finish
1. Read the final deliverable and check it yourself against EVERY acceptance criterion (counts, sections, URLs, tests run).
2. If something is unmet, send it back with `revises` (do not patch it yourself) and say what you did.
3. Copy the deliverable to the requested path (the plan lists this step) and check it exists and matches.
4. Reply briefly, and shorter still when the user asks for a short answer: the deliverable path, then one line per criterion
   (met / unmet), then runs used of planned. Nothing else.
5. A service request: after the delivery ask ONE short question ("Keep it, or what should change?") and record
   `feedback(task_id, accept|reject, note)` only on the user's own judgement of the delivered result ("keep it" / "what's wrong"); "deliver as
   is" or "I'll read it myself" is not an accept: ask, or record nothing yet. A known unmet criterion stays unmet: say so; feedback never
   waives it; reject needs the user's reason in their words. If the reason is a lasting requirement
   ("always", "never", "from now on"), propose adding it to the contract as a checkable criterion; on yes call
   `define_service(owner, name, add_acceptance=[<the new criterion>])` (an amendment: nothing else is retyped; the playbook stays),
   then tell the user the resulting criteria from its reply. Never edit SERVICE.md or PLAYBOOK.md yourself.
6. The scheduler exits on its own when nothing is left (`progress` shows "scheduler: stopped (finished: no open tasks)").
   Call `stop()` only if the user cancels, declines more budget, you hand over an unverified or partial result (say the task
   stays open/blocked, not done), or you started it with `until_done=False`.

## Blueprint rules
Templates: manager, researcher, writer, reviewer, fact-checker, engineer, tester, code-reviewer, analyst, data-checker (or give `charter:` text).
The validator enforces: exact acceptance criteria and a deliverable; web tools for web needs; write+shell only with a workspace;
a reviewer separate from the author who never edits others' files; budget within the user's cap and above the estimate; tiered
models when asked. Criteria must be checkable ("at most 1500 words"), never "good quality". Example criteria: "Covers exactly the
items the user listed", "The fact-checker's coverage report shows every factual claim verified (n of m, n = m)". The fact-checker and reviewer check everything, not a sample, so never ask for "at least N" checks.

## Files and access
- `needs.inputs`: the user's folders. Agents may read them and can never change them (kiro enforces it per agent). `needs.workspace`:
  the one folder agents may write in, for code.
- Non-code goals: never give an agent the built-in `write` tool unless the goal needs it. Agents write in their own folders and
  you copy the deliverable to the requested path (step 5). The plan lists each agent's access; if it shows "NOT confined", that
  is `shell`: only code goals get it, and they are told to stay in the workspace.
