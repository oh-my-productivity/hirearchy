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
- Tasks go down (`delegate`, direct reports only), results go up (`report`: `done` and `failed` are final, a `blocked` task can be reported again and the new result `supersedes` it), and notes go to the parent, reports, siblings, or a reply.
- The task contract travels with every run: the prompt carries the full text (goal, acceptance criteria, inputs) of each open task, and next to each `result` the task you delegated that it answers. Protocol: copy criteria verbatim when delegating, report `done` only if every criterion is met, otherwise `blocked`/`failed`.
- Task state and budget are derived from the message files, never stored separately.
- Budget is counted in runs and passes down the tree: a child gets only what its parent hands it, and each delegation keeps a reserve so the parent can process the result. It comes back up in two ways, both as one message that is charged to the sender and credited to the recipient (so nothing is minted or lost): with a final result, and by hand. When an agent reports `done` or `failed` and has no other open task, no task it reported `blocked` (that may be re-reported), no outstanding delegation and no mail waiting for a run, everything it has left travels up with the result to whoever assigned it (the result shows "returns N run(s)", and its own reports have already returned theirs, so it cascades up). `blocked` returns nothing. An agent can also give runs back early with `send(to=<parent>, body, budget=N)` (the reserve for its own delegations stays). Budget still goes nowhere else: down to direct reports, up to the parent. Results written before this existed carry no budget and mean what they always did. `delegate` without a `budget` hands down `min(default_budget, remaining - reserve)` (one run reserved per outstanding delegation plus one for the new one) and fails with the options if that is below 1.
- Reviews follow the single-writer rule (rule 9 of the protocol in `ORG.md`): a reviewer or fact-checker never edits the author's file; it reports its findings and the changes it requires to whoever assigned the review, and the author applies them (`delegate(..., revises=<task id>)`). Acceptance criteria and charters must never require an agent to edit another agent's files. The protocol text is copied into `ORG.md` when an organization is created, so an existing organization keeps the text it was created with (the runtime rules above apply to it regardless). `orgmcp upgrade-rules [--dry-run]` rewrites the body of its `ORG.md` to the current text, keeping the frontmatter and the mission, and prints what changed (each agent sees the new rules from its next run).
- Authority only narrows: a parent cannot grant tools, a workspace or inputs it doesn't have.
- The write guard is the same on case-sensitive and case-insensitive filesystems (`agent.md`, `Memory.md` or a `RUNS` directory are refused, as are names that differ from an existing file only by case), and `AGENT.md` is created only by `hire`. `write` is confined to your own directory, `report` artifacts to the organization; `retire` takes a short name or full address and returns the team's unspent budget to the retired agent's parent as a runtime note (nothing when that parent is root). That note is non-waking (`wake: false`): it counts towards budget at once and lifts a budget pause, but does not start a run; it is held in the inbox, not counted as unread (scheduling, health), and delivered with the agent's next real batch.
- Guards: hop limit (loops), max depth/children, out-of-budget pause with a parent notice, per-run timeout, one scheduler per org, and a git commit after every run. Also:
  - Stall ladder: checked every tick, per open task. If the assignee is idle (not running, no unread mail, not paused, not waiting on delegations) for `stall_after` seconds (default 600), it gets a reminder; each further `stall_after` the runtime tells the assigner, then each ancestor up to root, then stops. State is in `.runtime/nudges.json`.
  - Consecutive failed runs pause the agent after `max_failures`. The count is kept in `.runtime/failures.json` (survives restarts) and cleared by a successful run or `orgmcp resume`.
  - Messages are capped at `max_message_chars` (default 20000): longer `send`/`delegate`/`report` bodies are refused (put detail in a file under `work/`). Whatever is shown to an agent (new messages, the contract of open tasks, the task a result answers, `inbox`) is cut at 8000 characters with the path to `read` the rest.
  - Word counts shown to agents (artifact notes on a `report`, `read`) ignore markdown markers (`#`, `-`, `1.`, `|`, fences); the `MEMORY.md` cap counts plain whitespace-separated words.
  - A scheduler tick isolates faults per phase (a failing phase is logged and retried next tick), runs start in their own process group so a timeout kills the tools too, and prompts go to `kiro-cli` on stdin. Agent crashes notify the human (`orgmcp resume`); an LLM parent gets a notice with its options instead.
  - Orphaned runs: each run's process group is recorded in `.runtime/running.json` (pgid, start time) while it lives. A scheduler that starts finds the records of a dead one, kills a group only if its leader is still alive with the recorded start time and leads its own session (never anything else), then redelivers the batch; a live orphan that cannot be verified or killed keeps its agent from starting a second run until it is gone.
  - `MEMORY.md` is capped at `memory_max_words` (default 800): writes and appends beyond it are refused, and an oversized memory is flagged for condensing in the next run's prompt.

## Use

```sh
uv run orgmcp init org --mission "..." --model claude-haiku-4.5
uv run orgmcp hire root ceo --role "Chief of staff" --charter @examples/ceo.md \
    --model claude-sonnet-4.6 --can-hire --max-children 3
uv run orgmcp task ceo --title "..." --goal @goal.md --acceptance @acceptance.md --budget 14
uv run orgmcp run --until-idle --max-runs 14     # or plain `run` as a daemon; `--until-done` exits when no task is open or all open ones wait on you
uv run orgmcp status
uv run orgmcp inbox
```

Other commands: `hire ... --inputs PATH` (repeatable: read-only folders for the agent), `progress [TASK_ID] [--wait SECONDS]`, `plan`/`apply` (blueprints, below), `send` (note or budget grant), `resume <agent>`, `review [--dry-run]`, `run --once`, `upgrade-rules [--dry-run]`, `install-skill [--dest DIR] [--force]`, `mcp`, `kiro-profile` (this org's internal profile).

### Progress

```sh
uv run orgmcp progress [TASK_ID]
```

What to read back to someone who asks "status?": one line per task you gave (open or blocked ones, and those that finished in the last day; with `TASK_ID`, just that task in any state): its state (`working`, `waiting on <agent>` with the reason if it is paused, `stalled`, `blocked: <reason>`, `done`, `failed`), who is running or has unread work in its team, runs used while it was open against the budget given for it, the time since the team's last activity, and for finished tasks the artifact paths and the runs returned. Then one `Needs you:` line for each unread item in your inbox that waits for a decision (blocked or failed results, notes from agents, runtime notices). It only reads; `orgmcp inbox` still shows the messages. The Python entry point is `orgmcp.progress.progress(org, task_id=None)`.

```
"Competitor report": waiting on ceo/writer. runs 2 of 12. last activity 4m ago. (task 20261017T175121-root-8218)
"Second": blocked: Need the 2025 sales figures from finance. runs 1 of 5. last activity 1m ago. (task 20261017T175135-root-fc1a)
Needs you: blocked result from ceo "Second": Need the 2025 sales figures from finance (message 20261017T175135-ceo-a9b7)
```

## Create an org from a goal

Building an org for a goal goes wrong when it is improvised: scope, deliverable, budget, models and the review step get
assumed. With orgmcp registered in your kiro assistant (see [Kiro integration](#kiro-integration)) and its skill installed
(`orgmcp install-skill`), this is the whole story:

1. **Ask.** "Build me an org that produces a competitor analysis of five note apps." The assistant replies with one message
   of the questions that matter, in plain words, with a proposed default only where a generic one exists: format, length,
   exact acceptance criteria, sources and web access, workspace and tests (for code), budget in runs, models, review,
   approval, progress. A list it was not given (apps, competitors, features, source files) it asks for; it does not invent
   one. Unless you say otherwise the result goes into a new `deliverables/` folder in your current directory.
   You answer, or say "defaults".
2. **Plan.** The assistant starts from `blueprint_example(kind)` (`research`: web sources; `documents`: write from your local
   files, no web; `code`: repo workspace with tests and commits; `analysis`: your data files, read-only, analysed by a checked script), edits it with your answers and calls `propose_org`. You get
   a block headed **PLAN FOR YOU** that the assistant must show you exactly as written (about 40 lines, plain words): goal,
   needs as understood, the team (role, model, tools, and for each agent what it may touch, worded from the same
   computation as the `Access:` line below, so the plan states what kiro will enforce), the budget and its split, the independent
   review, the deliverable and where it will be delivered, the checks that decide "done", checkpoints and warnings. Under
   the budget it states the failure policy: if the check still fails after one rework, the assistant comes back to you with
   options before spending the reserve (the planned runs above the minimum for one review and rework, e.g. "about 4 runs").
   Fields are cut only at sentence ends (the Goal line shows the whole mission up to 800 characters; success checks are
   always in full). Below it come the full details for the assistant and a `plan_id`. Errors block the plan until fixed. Nothing has been
   written yet, not even the organization.
3. **Approve.** You say "approve" or ask for changes (then it proposes again). Only after your explicit approval the
   assistant calls `create_org` (if there is no organization yet), `apply_org(blueprint, approved=True, plan_id=...)` and
   `start`. `plan_id` is a short hash of the normalized blueprint (the same blueprint always gives the same id, any change
   gives another; nothing is stored, so it survives restarts). `apply_org` refuses without `approved=True` and without
   the `plan_id` of exactly that blueprint, so the plan you saw is the plan that is applied. It hires the whole tree as root
   (parents first), gives the first task, and undoes everything if anything fails midway.
4. **It runs.** The scheduler wakes the agents. The budget in the plan is a ceiling, not a price: runs a team does not spend
   come back automatically with each agent's final report, up to you. Spending beyond the plan needs your OK. `start`
   launches it with `until_done`: it exits by itself when you have no open task and nothing is running or runnable
   (`orgmcp run --until-done` on the command line; `--until-idle` is unchanged) and logs why in `.runtime/scheduler.log`;
   `status` and `progress` then say `scheduler: stopped (finished: no open tasks)`. Give the org more work later and
   `start` again; `stop` is only for cancelling. It also exits by itself when every open task is **waiting on you**:
   nothing runs and nothing can start because the agents holding the work are out of budget or keep failing (or the task
   is stalled and the stall ladder has already told root). After `until_done_grace_seconds` (ORG.md, default 300) of that,
   it exits with `waiting on you: "<task>" needs budget (<agent> out of runs)` (or `needs you to resume <agent>`, or `needs
   a decision`). `progress` shows the reason and your options (grant runs with `send(to=..., budget=N)` and `start`, or accept
   what exists, leaving the task open), `progress(wait_seconds=...)` does not wait while it holds, and `start` refuses until
   something changes. A grant, a resume or new work restarts the count.
5. **Progress.** "Status?" is answered from `progress`: one line per task (working / waiting on an agent / stalled /
   blocked with the reason / done / failed), who is busy, runs used of the budget, time since the last activity, and what
   needs your decision. An assistant cannot message you between turns, so it never promises to. If you want to be told
   when the work is done, it says it will wait and calls `progress(wait_seconds=N)` (up to 900; `orgmcp progress --wait N`
   on the command line): the call returns as soon as a task is done, failed, blocked or stalled, or something new needs
   you, or when the time is up, with what changed; it only reads files (no locks, nothing written) and does not wait
   when no scheduler is running. Say how long you are willing to wait and it repeats the call; otherwise ask "status?".
6. **Delivery.** When the task is done the assistant reads the deliverable, checks it against every acceptance criterion
   (sending it back for rework if one is unmet, never patching it itself), copies it to the path you chose, and tells you
   which criteria are met and how many runs it cost.

The same flow works without an assistant: `orgmcp plan bp.yaml` (exit status 1 on errors), `orgmcp apply bp.yaml`,
`orgmcp run`, `orgmcp progress`.

The blueprint (YAML or JSON; `blueprint_example(kind)` returns a commented template, a longer one is in
[`examples/blueprint-research.yaml`](examples/blueprint-research.yaml)):

```yaml
mission: ...                          # what the organization is for
needs:                                # the elicited requirements (free text unless noted)
  scope: ...
  deliverable: {description: ..., format: ..., max_words: 1500, path: /abs/path/file.md}
  quality_bar: ...   sources: ...   workspace: /abs/project/dir   budget_runs: 25   # the user's cap
  inputs: [/abs/read-only/dir]        # sources agents may read but never change (kiro enforces it; see Workspaces, inputs and confinement)
  models: {cheap: <model id>, strong: <model id>}   model_policy: ...
  review: true                        # independent reviewer required
  approval: ...   progress: ...   kind: research|writing|code   code: {tests: ..., packaging: ..., commits: ...}
agents:                               # exactly one top-level agent; nested tree
  - {name: lead, template: manager, model: strong, children: [{name: w, template: writer, model: cheap}]}
        # per agent: role, template or charter, model (id, or cheap/strong), tools, workspace, inputs, can_hire, max_children, scale
task: {to: lead, title: ..., goal: ..., acceptance: [exact, checkable items], inputs: [...], budget: 22}
```

Validation encodes the lessons of the usability studies: a deliverable and exact acceptance criteria; web tools when sources
are needed; `write`/`shell` only with a workspace inside an allowed root (default: home, temp, cwd; `--allow-root DIR` or
`$ORGMCP_WORKSPACE_ROOTS`; never the org itself or `~/.kiro`); code goals need an engineer with a workspace; a reviewer distinct
from the author whose charter never has it edit others' files (rule 9 of the protocol); managers hold the tools and workspace
they hand down; budget within the user's cap and above the estimate; different models for drafting and review when asked;
depth and children within limits. Over MCP the blueprint is passed as YAML/JSON text and is never read from a file path.

**Budget estimate.** One pass plus one review/rework cycle. A worker's pass costs its template's `base_runs` times `scale`
(researcher 3, writer 2, engineer 4, fact-checker 2, reviewer 1, tester 2, code-reviewer 2, analyst 4, data-checker 2) and its rework costs 1. A manager's
pass costs 2 plus one per direct report; its rework costs 2. The planned budget is the estimate times 1.25 unless
`task.budget` is set. Managers get a written budget plan: initial grants equal the reports' pass runs and the rest stays with
the manager as reserve for rework. Unspent runs return up the tree automatically (see the budget rule above), so the
planned figure is what you authorize at most, and `progress` shows what was used and returned.

**Role templates** live in `src/orgmcp/roles/*.md`: `manager`, `researcher`, `writer`, `reviewer`, `fact-checker`, `engineer`,
`tester`, `code-reviewer`, `analyst`, `data-checker`. Each has purpose, responsibilities, decision rights, escalation, quality bar, budget discipline and a
default tool set and model tier. Reviewers report findings and required changes to their manager and never edit another
agent's file (the manager sends them back to the author with `revises`). `template:` plus a `charter:` adds your own text.

What the templates add for verification and delegation:

- Verifier templates now check exhaustively. Fact-checking separates facts from judgement: a fact is any sentence with a number, name, version, licence, price, date or no/only/all, and it needs the page that states it and a verbatim quote; opinions go in a labelled section, uncited, resting on verified facts. The `fact-checker` writes a ledger of every factual claim, opens each cited source (homepages/repo roots that don't state the claim are "unsupported") and ends with the coverage line `n of m factual claims verified (n = m required); k wrong, u unsupported, p not-checkable; j judgement statements, each resting on verified facts: yes`; the manager pastes it verbatim in every `done`, and the review fails unless n = m. The `reviewer` goes through the acceptance criteria one by one ("criteria met: n of m", pass only if n = m).
- Unverifiable claims are cut or reframed by the author, never re-sourced from memory; after one failed verification cycle the manager cuts instead of researching again, then escalates with options.
- Verifiers get the project and the authors' workspaces read-only as `inputs` unless they can already write there; explicit `inputs` that hide the reviewed work raise the warning `verifier-cannot-read`.
- `blueprint_example("analysis")`: data analysis with read-only data, a scratch workspace, an `analyst` and an independent `data-checker`. The data-checker recomputes the key figures with its own script and checks figures with their label: (label, number) pairs, not numbers alone.
- `code-reviewer` now has `read` and `shell`: it runs the test suite and the commands named in the criteria and reports each command and result; it still never edits files (charter-enforced, since shell can't be confined). It needs a workspace, like the engineer.
- `manager` verifies with its own `read` output (never memory or a report's claim), treats the verifier's coverage report as a precondition for `done`, and sends deviations back with `revises` or escalates instead of reporting `done`.
- `writer`/`researcher`/`engineer`/`tester` got small additions: relevance over length, page-level citations with retrieval date, tests run before reporting, every criterion exercised with commands.

So acceptance criteria should ask for the coverage report ("every factual claim verified, n = m"), not for "at least N" checks.

**The assistant's playbook** is `skills/orgmcp/SKILL.md`: the precondition (use orgmcp or say it is unavailable), the one-message
checklist, plan and approval, build and run, monitoring, and verification before delivery. The server's own instructions carry
a compact version of the same workflow, so an assistant without the skill still gets the order of steps. How to install the
skill: see [Kiro integration](#kiro-integration).

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

A task counts once, by its latest result: a `blocked` that was superseded by a later `done` is a `done` in the counts
(and in `low_quality` and the health reviews). A task reported `blocked` is answered, not open: it does not keep the
agent scheduled, and `whoami` lists it as re-reportable.

| Flag | Meaning | Threshold key (default) |
| --- | --- | --- |
| `stuck` | open task older than the limit, and the agent is not running, has no unread mail, and is not waiting on a delegation | `stuck_after_seconds` (1800) |
| `out_of_budget` | budget <= 0 while it has unread mail or open tasks | - |
| `paused` | paused for any reason (shown in the reason) | - |
| `low_quality` | (failed + blocked + rework) / tasks received above the ratio, once enough tasks were received | `max_problem_ratio` (0.5), `min_tasks_for_quality` (3) |
| `expensive` | runs per completed task above the limit (needs a result), or too many runs since its last result while holding an open task; runs that failed or were woken only by runtime notes (stall reminders, reviews, refunds) are not counted, but `runs` and the budget still include them | `max_runs_per_task` (5), `max_runs_without_result` (6) |
| `wasteful` | empty runs / runs used above the ratio, once enough runs were used | `max_empty_run_ratio` (0.5), `min_runs_for_waste` (4) |
| `stranded_budget` | budget left but no open tasks, no delegations, no unread mail and no activity for longer than the limit; the runs belong with the parent (not raised for root's direct reports: root has no limit). Suggested action: ask the agent to return its budget (a `send` to its parent with `budget=N`), or retire it | `stranded_after_seconds` (1800) |
| `idle` | no open tasks, no delegations, no unread mail and no activity for longer than the limit (measured from hiring if it never ran): a candidate to retire | `idle_after_seconds` (86400) |

Branch totals (the agent plus its subtree) sum runs, open tasks, results and rework, and show the worst flag, in the
order above (`stuck` is worst, `idle` mildest; `stranded_budget` sits just above `idle`). Override any threshold in the `ORG.md` frontmatter:

```yaml
health:
  stuck_after_seconds: 900
  max_runs_per_task: 8
```

### Health reviews

Measuring is not managing. Periodically the runtime turns the flags above into a short note for the manager who
can act on them, so problems get followed up, reworked, re-budgeted or retired instead of waiting for you to run
`orgmcp health`.

- **Cadence.** The scheduler runs a review when `review_every_runs` runs have been used across the organization since
  the last review (counted from the run logs, so a restart does not reset it) or `review_every_seconds` have passed,
  whichever comes first. The first scheduler tick only starts the clock. The last review (time, run count, who was
  told about what) is kept in `.runtime/reviews.json`, the only extra state.
- **Managers.** An agent with direct reports gets one note ("health review: N new problem(s)") listing the flags of
  its direct reports, each with the reason and a suggested action (follow up or reassign, grant runs, investigate a
  pause, tighten the charter or rework with `revises`, narrow the tasks, fix a wasteful charter, retire). If a
  report manages a team, the worst flag raised further down its team is mentioned too. The manager is asked to act
  within its charter and record decisions in its `MEMORY.md`.
- **Only what is new.** A (report, flag) pair already sent to that manager in the previous review is not repeated;
  if it goes away and comes back it is new again. Paused managers and managers with no budget left are skipped
  (root's summary covers them, and they hear about the problem once they can act).
- **Root.** Whenever anything is flagged, root gets one note with every flagged agent and reason, plus suggested
  actions for its own direct reports and the list of managers that were not notified. Root is free to notify.
- **Cost.** A healthy organization costs nothing: no flags means no notes, only a ledger update. Each manager note
  wakes the manager for one run of its budget.

| Config key (ORG.md) | Default | Meaning |
| --- | --- | --- |
| `review_every_runs` | 25 | runs used across the organization between reviews |
| `review_every_seconds` | 86400 | seconds between reviews |
| `max_message_chars` | 20000 | longest message body `send`/`delegate`/`report` accept |
| `default_budget` | 10 | runs a delegation gets when none is given, capped by what the delegator can afford |

Runs that failed, and runs woken only by runtime notes (budget, stall, review, budget refunds), are left out of the
`wasteful` statistics. The retired agents' runs still count towards `review_every_runs`.

```sh
uv run orgmcp review [--dry-run]
```

Runs a review immediately through the same code path and prints what was sent to whom. `--dry-run` prints what
would be sent and writes nothing (no messages, no ledger).

## Kiro integration

**Talking to the org yourself (you act as `root`).** Register the server globally; it does not need an
organization to exist yet:

```json
"orgmcp": {
  "command": "uv",
  "args": ["--directory", "/path/to/orgmcp", "run", "orgmcp", "mcp"],
  "env": { "ORG_ROOT": "/path/to/your/org" }
}
```

- The server is bound to exactly one path for its lifetime: `ORG_ROOT` (or, when it is unset, the organization found
  from the working directory). It never falls back to another organization.
- If nothing exists at that path (missing or empty directory), the server still starts in *setup mode*: `whoami` and
  `status` explain the next step, every other tool answers `no organization at <path> yet: call create_org(mission=...)
  first`, and `create_org(mission, default_model=None)` creates the organization there. From then on all tools work
  in the same session, no restart. `create_org` refuses a directory that holds anything else, and an organization that
  already exists (which is then ready to use). With `ORG_ROOT` unset and no organization in the working directory it
  needs a `path` (absolute); with `ORG_ROOT` set a different `path` is refused.
- Root-only tools: `create_org`, `start(max_runs=None)` (launch a detached scheduler for this org, output in
  `.runtime/scheduler.log`, returns its pid; refused if one runs), `stop()` (SIGTERM, only to a pid verified to be this
  org's scheduler: alive, `run` in its command line, and this org's `--root` or an `orgmcp` program with no other
  `--root`). `status` and `whoami` end with a `scheduler: running (pid, since) / stopped` line.
- Goal workflow tools (root only; see [Create an org from a goal](#create-an-org-from-a-goal)):
  - `blueprint_example(kind="research")`: a ready-to-edit YAML blueprint with a comment on every field and a schema
    summary; `kind` is `research`, `documents`, `code` or `analysis`. Paths start in the server's working directory.
  - `propose_org(blueprint)`: blueprint as YAML/JSON text in (its description carries the compact schema), out: the
    **PLAN FOR YOU** block to show the user verbatim, the full details, and `plan_id`; writes nothing; works in setup mode.
  - `apply_org(blueprint, approved=False, plan_id=None)`: refuses unless `approved=True` and `plan_id` equals the id
    of this blueprint (pass them only after the user approved the plan that `propose_org` returned), refuses in setup mode
    ("call create_org first") and on validation errors, otherwise hires the team, gives the first task and says to call
    `start`.
  - `start(max_runs=None, until_done=True)`: background scheduler that exits by itself when the work is done.
  - `progress(task_id=None, wait_seconds=0)`: the status lines described above plus the scheduler line; with
    `wait_seconds` it first waits for a change; in setup mode it explains the next step.
- Other tools: `whoami`, `inbox`, `delegate`, `report`, `send`, `hire` (with `inputs` for read-only folders), `retire`, `read`, `write`, `status`, `health`.
  Agents get these (not `create_org`, `start`, `stop`, `blueprint_example`, `propose_org`, `apply_org`, `progress`). `report` tells an agent when
  budget travelled up with its result; `send(..., budget=N)` to its parent gives runs back early.
- The server's instructions for root contain the workflow in five lines (ask once → `blueprint_example` + `propose_org` →
  show the PLAN FOR YOU block, wait for explicit approval → `create_org`/`apply_org(approved=True, plan_id)`/`start` →
  `progress` (or `progress(wait_seconds)`) → verify, copy) next to the safety
  rules: only the bound organization, no substituting other mechanisms, no claims without tool evidence.

**The assistant skill.** `orgmcp install-skill [--dest DIR] [--force]` copies the skill to `~/.kiro/skills/orgmcp/SKILL.md`
(`DIR` is the skills directory: the file goes to `DIR/orgmcp/SKILL.md`), prints the path, leaves an identical file alone and
refuses to replace a different one without `--force`. Kiro loads skills through the `resources` of an agent profile as
`skill://` entries (a path or a glob): the profiles in `~/.kiro/agents` use `"skill://.kiro/skills/*/SKILL.md"`. To use the skill from a project-local profile without installing it, give the
absolute path of the checkout's file, for example in `<project>/.kiro/agents/org-assistant.json` (the file validates with
`kiro-cli agent validate --path <file>`, which checks the shape of the entries, not that the file exists):

```json
{
  "name": "org-assistant",
  "description": "Builds and runs an orgmcp organization for a goal",
  "prompt": "You manage one orgmcp organization for the user through the orgmcp tools. Follow the orgmcp skill.",
  "mcpServers": {
    "orgmcp": {
      "command": "uv",
      "args": ["--directory", "/path/to/orgmcp", "run", "orgmcp", "mcp"],
      "env": { "ORG_ROOT": "/path/to/your/org" }
    }
  },
  "tools": ["*"],
  "resources": ["skill:///path/to/orgmcp/skills/orgmcp/SKILL.md"],
  "includeMcpJson": false
}
```

Run it with `kiro-cli chat --agent org-assistant`. This profile binds the assistant to one organization (and keeps your other
MCP servers out); `tools: ["*"]` lets it copy the finished deliverable with kiro's own file tools, so narrow it if you prefer
to copy files yourself. Use a name other than `orgmcp-...`, which the scheduler's internal profiles use.

**Agent runs (the scheduler).** Runs use `kiro-cli chat --no-interactive --agent <profile>`; the prompt is passed
on stdin. The scheduler writes one *internal* profile per organization (and per set of granted built-in tools) to
`~/.kiro/agents/`:

- name `orgmcp-<org-slug>-<6-char hash of the org path>[-<tools>]` (lowercase `[a-z0-9-]`), description "internal:
  used by the orgmcp scheduler for <org path>; not a general-purpose agent". Different orgs never share or overwrite a
  profile.
- It loads only the orgmcp server (`includeMcpJson: false`), so agents never see your other MCP servers. The server
  entry carries `ORG_ROOT=<this org>` and `ORG_REQUIRE_AGENT=1`.
- Fail closed: with `ORG_REQUIRE_AGENT=1` the server refuses to start unless `ORG_AGENT` names an agent (`root` does not
  count). If something borrows a profile as a general subagent, it gets an error instead of acting as `root`.
- `ORG_AGENT` is not baked into the profile: the scheduler sets it per run in the process environment of `kiro-cli`.
  This relies on kiro starting MCP servers with its own environment plus the profile's `env` (the same inheritance the
  scheduler always used for `ORG_AGENT`/`ORG_ROOT`). If a kiro version replaced the environment instead, runs would fail
  visibly with the message above rather than act as root.
- Older global profiles (`~/.kiro/agents/orgmcp*.json`) are no longer written or used; they are never deleted or
  rewritten, so remove them yourself when no scheduler that uses them is running.

### Workspaces, inputs and confinement

Two path worlds meet in a run: orgmcp tools (`read`, `write`, `report`, `delegate` inputs) use paths relative to the
**org root**; kiro's own tools (`read`, `write`, `shell`) start in the agent's **workspace** (its charter `workspace`, else
its org directory) and resolve relative paths there. An agent that writes `lead/writer/work/x.md` with kiro's `write`
therefore creates that tree inside the user's folder, not in the org. The charter fields and the rules below keep the
two apart.

The two kinds of tools share short names. In kiro the orgmcp ones appear as `@orgmcp/write`, `@orgmcp/read`, ...; an agent that
holds the built-in `write`/`read`/`shell` is told in its prompt's Files section (and in ORG.md's rules, for orgs created or
`upgrade-rules`d since) to use `@orgmcp/write` for org files (`<addr>/MEMORY.md`, `<addr>/work/`, reports) and the built-ins
for the workspace only; its closing "update your memory" line names `@orgmcp/write` too. The orgmcp `write` tool's description
and reply say it writes an organization file. **Stray org files:** after each run of an agent with built-in `write` and a
workspace, the scheduler looks for `<workspace>/<address>/` (new during the run) and a written `<workspace>/<address>/MEMORY.md`.
If found it logs a `# warning:` in the run log and the scheduler output and records it in `.runtime/strays.json`; the agent's
next prompt says once to move that content into its org files with `@orgmcp/write`. Nothing is moved or deleted.

Charter fields: `workspace` (read-write, as before) and `inputs: [absolute paths]` (read-only; blueprint: `needs.inputs`
for the whole project or `inputs` per agent). A report's inputs must be inside its manager's inputs or workspace (authority
only narrows), inputs are absolute and never overlap the org directory. Charters without `inputs` keep working. Set them with
`orgmcp hire ... --inputs PATH` (repeatable) or the `inputs` parameter of the `hire` tool (root, or a manager within its own
inputs/workspace); `documents`-type goals put the user's folder in `needs.inputs` (it must exist).

**Enforced by kiro** (per-agent profiles, checked against kiro-cli 2.29.1 in `--no-interactive` mode; the experiments are
in `studies/X1-confinement/EXPERIMENTS.md`). An agent with built-in `read` or `write` gets a profile
`orgmcp-<org>-<hash>-<tools>-x<access hash>` (same `ORG_ROOT`/`ORG_REQUIRE_AGENT=1`, same "internal" description; agents with
equal tools and access share it) whose `toolsSettings` say:

```json
"tools": ["@orgmcp", "read", "write"],
"allowedTools": ["@orgmcp"],
"toolsSettings": {
  "write": {"allowedPaths": ["/ws/**"], "deniedPaths": ["/org", "/org/**"]},
  "read":  {"allowedPaths": ["/ws", "/ws/**", "/inputs", "/inputs/**"], "deniedPaths": ["/org", "/org/**"]}
}
```

- `read`/`write` are deliberately **not** in `allowedTools`: a trusted tool ignores `allowedPaths`. Left out, a call on an
  allowed path runs, and any other path needs an approval, which a headless run cannot give: it is refused with "tool
  permission approval is not supported in non-interactive mode". `..` traversal is refused too.
- `write` only under the workspace (nowhere without one), so inputs are read-only and nothing is created beside them.
  `read` under workspace + inputs. Neither reaches the org directory (hard deny, also over kiro's "the working directory is
  readable" rule); the org is reached through orgmcp tools only.
- Agents without built-in `read`/`write` keep the shared per-org profile. A legacy charter with only `read`, no workspace and
  no `inputs` key keeps today's unconfined read; give it `inputs: []` (or real inputs) to confine it. A confined parent never
  hands down an unconfined `read`.

**Enforced by orgmcp:** `report(artifacts=...)` takes org paths (relative or absolute) and absolute paths inside the
reporter's **own** workspace, annotated as before (words, modified, "NOT modified since..."); anything else outside the
org is refused without probing. `read` takes relative org paths, and absolute paths inside the caller's workspace, its
inputs, and the workspace of any agent in its subtree (a manager can verify what its team made); everything else outside
the org is refused. Root's `read` is unchanged (organization only).

**Only instructed:** `shell` cannot be confined (kiro has no path rule for it; it can write anywhere its OS user can), so an
agent that holds it (engineer, tester, code-reviewer, and a manager that holds what its code team holds) is told the rule in its charter and prompt, and the plan says so (`shell-unconfined` warning, "shell NOT
confined" in its `Access:` line). The prompt's Files section (workspace, inputs, "never create org files in the workspace",
"report workspace artifacts by absolute path") is guidance on top of the enforcement above. Symlinks inside a workspace that
point out were not tested against kiro's own matching; orgmcp's `read`/`report` resolve them and refuse targets outside.

Every command that changes an organization (`init`, `hire`, `task`, `apply`, `send`, `resume`, `run`, `review`, `inbox`
without `--keep`, `upgrade-rules` without `--dry-run`, `kiro-profile`) first prints `org: <path>` to stderr. `python -m orgmcp` is the same as the `orgmcp` script.

## Security notes

- Everything is local stdio with no network listener. Identity is enforced by the process environment, not by
  authentication: anything that can run `orgmcp mcp` with `ORG_AGENT` set can act as that agent.
- The orgmcp write rules apply to the orgmcp tools. kiro's built-in `read`/`write` are confined to the agent's workspace
  and inputs by its profile (see [Workspaces, inputs and confinement](#workspaces-inputs-and-confinement)); `shell` is not:
  an agent that holds it can touch anything its OS user can. Grant it only to agents that need it, with a `workspace`.

## Test

```sh
uv run pytest -q
```

The tests use a deterministic fake agent (`tests/fake_agent.py`) in place of kiro. An autouse fixture
(`tests/conftest.py`) points `$HOME` and the profile directory at a temp dir and puts a stub `kiro-cli` first on
`PATH`, so running them never touches your real `~/.kiro`.
