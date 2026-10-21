# hirearchy

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
- Budget is counted in runs and passes down the tree: a child gets only what its parent hands it, and each delegation keeps a reserve so the parent can process the result. It comes back up in two ways, both as one message that is charged to the sender and credited to the recipient (so nothing is minted or lost): with a final result, and by hand. When an agent reports `done` or `failed` and has no other open task, no task it reported `blocked` (that may be re-reported), no outstanding delegation and no mail waiting for a run, everything it has left travels up with the result to whoever assigned it (the result shows "returns N run(s)", and its own reports have already returned theirs, so it cascades up). `blocked` returns nothing. An agent can also give runs back early with `send(to=<parent>, body, budget=N)` (the reserve for its own delegations stays). A manager (or root) can also pull runs back with `reclaim(report, budget=None)`: from a DIRECT report that is idle (no open task, nothing delegated and outstanding, not running, no unread mail that would wake it), all of its unspent runs by default. It is one message too: a non-waking note titled "budget reclaimed by <actor>" from the report to the actor, written by the runtime on the report's behalf (in the report's `sent/`, so the arithmetic stays derived and the total conserved; the report is not woken). It is refused, with the reason, for a busy report, a report that is not a direct one (no cascade: a manager reclaims from its own team), nothing to reclaim or more than is available. Use it before asking for more budget when a team has stranded runs (`health` flags them as `stranded_budget`). Budget still goes nowhere else: down to direct reports, up to the parent. Results written before this existed carry no budget and mean what they always did. `delegate` without a `budget` hands down `min(default_budget, remaining - reserve)` (one run reserved per outstanding delegation plus one for the new one) and fails with the options if that is below 1.
- Reviews follow the single-writer rule (rule 9 of the protocol in `ORG.md`): a reviewer or fact-checker never edits the author's file; it reports its findings and the changes it requires to whoever assigned the review, and the author applies them (`delegate(..., revises=<task id>)`). Acceptance criteria and charters must never require an agent to edit another agent's files. The protocol text is copied into `ORG.md` when an organization is created, so an existing organization keeps the text it was created with (the runtime rules above apply to it regardless). `hirearchy upgrade-rules [--dry-run]` rewrites the body of its `ORG.md` to the current text, keeping the frontmatter and the mission, and prints what changed (each agent sees the new rules from its next run).
- Authority only narrows: a parent cannot grant tools, a workspace or inputs it doesn't have.
- The write guard is the same on case-sensitive and case-insensitive filesystems (`agent.md`, `Memory.md` or a `RUNS` directory are refused, as are names that differ from an existing file only by case), and `AGENT.md` is created only by `hire`. `write` is confined to your own directory, `report` artifacts to the organization; `retire` takes a short name or full address and returns the team's unspent budget to the retired agent's parent as a runtime note (nothing when that parent is root). That note is non-waking (`wake: false`): it counts towards budget at once and lifts a budget pause, but does not start a run; it is held in the inbox, not counted as unread (scheduling, health), and delivered with the agent's next real batch.
- Guards: hop limit (loops), max depth/children, out-of-budget pause with a parent notice, per-run timeout, one scheduler per org, and a git commit after every run. Also:
  - Stall ladder: checked every tick, per open task. If the assignee is idle (not running, no unread mail, not paused, not waiting on delegations) for `stall_after` seconds (default 600), it gets a reminder; each further `stall_after` the runtime tells the assigner, then each ancestor up to root, then stops. State is in `.runtime/nudges.json`.
  - Consecutive failed runs pause the agent after `max_failures`. The count is kept in `.runtime/failures.json` (survives restarts) and cleared by a successful run or `hirearchy resume`.
  - Messages are capped at `max_message_chars` (default 20000): longer `send`/`delegate`/`report` bodies are refused (put detail in a file under `work/`). Whatever is shown to an agent (new messages, the contract of open tasks, the task a result answers, `inbox`) is cut at 8000 characters with the path to `read` the rest.
  - Word counts shown to agents (artifact notes on a `report`, `read`) ignore markdown markers (`#`, `-`, `1.`, `|`, fences); the `MEMORY.md` cap counts plain whitespace-separated words.
  - A scheduler tick isolates faults per phase (a failing phase is logged and retried next tick), runs start in their own process group so a timeout kills the tools too, and prompts go to `kiro-cli` on stdin. Agent crashes notify the human (`hirearchy resume`); an LLM parent gets a notice with its options instead.
  - Orphaned runs: each run's process group is recorded in `.runtime/running.json` (pgid, start time) while it lives. A scheduler that starts finds the records of a dead one, kills a group only if its leader is still alive with the recorded start time and leads its own session (never anything else), then redelivers the batch; a live orphan that cannot be verified or killed keeps its agent from starting a second run until it is gone.
  - `MEMORY.md` is capped at `memory_max_words` (default 800): writes and appends beyond it are refused, and an oversized memory is flagged for condensing in the next run's prompt.

## Use

```sh
uv run hirearchy init org --mission "..."           # every agent runs on claude-sonnet-5.5; --model X sets another org default
uv run hirearchy hire root ceo --role "Chief of staff" --charter @examples/ceo.md \
    --can-hire --max-children 3                  # no --model: the org default (add --model X to pin this agent)
uv run hirearchy task ceo --title "..." --goal @goal.md --acceptance @acceptance.md --budget 14
uv run hirearchy run --until-idle --max-runs 14     # or plain `run` as a daemon; `--until-done` exits when no task is open or all open ones wait on you
uv run hirearchy status
uv run hirearchy inbox
```

Other commands: `hire ... --inputs PATH` (repeatable: read-only folders for the agent), `progress [TASK_ID] [--wait SECONDS]`, `plan`/`apply` (blueprints, below), `services`, `define-service`, `request`, `feedback`, `retire-service` ([services](#services-and-reflection)), `send` (note or budget grant), `resume <agent>`, `review [--dry-run]`, `run --once`, `upgrade-rules [--dry-run]`, `install-skill [--dest DIR] [--force]`, `mcp`, `kiro-profile` (this org's internal profile), and the read-only views of [Observability](#observability): `obs now [--watch S]`, `obs trace TASK_ID`, `obs metrics [--since 24h] [--by agent|tool|service|trace]`, `obs events [--since] [--until] [--agent] [--kind] [--trace] [--errors] [--limit N] [--follow]` (each with `--json`) and `check [--json]`.

### Models

Every agent runs on **claude-sonnet-5.5** unless it is told otherwise. The scheduler always passes `--model` to `kiro-cli`, chosen in this order:

1. the agent's charter (`model:` in its `AGENT.md`, set by `hire --model` or a blueprint),
2. the organization's `default_model` in `ORG.md` (`init --model`, `create_org(default_model=...)`),
3. `claude-sonnet-5.5` (`hirearchy.core.DEFAULT_MODEL`).

`hire` without a model leaves the charter unpinned, so the agent follows the org default. **Existing organizations** whose `ORG.md` says `default_model: null` (or has no such key) used to run on kiro's own default; they now run on claude-sonnet-5.5. A model named explicitly in a charter or in `ORG.md` is kept, and to get another model org-wide, set `default_model` in `ORG.md`. The `run.start` event records the model each run used.

Blueprints follow the same rule: without `needs.models`, or for a tier it does not map, `cheap` and `strong` both resolve to the org's default model, and the plan says `Models: claude-sonnet-5.5 for every agent`. Cheaper drafting is only used when you ask for it (`needs.models: {cheap: <id>, strong: <id>}`); then the lead and the final verifier stay on `strong`, and the plan lists which model each group of agents runs on.

### Progress

```sh
uv run hirearchy progress [TASK_ID]
```

What to read back to someone who asks "status?": one line per task you gave (open or blocked ones, and those that finished in the last day; with `TASK_ID`, just that task in any state): its state (`working`, `waiting on <agent>` with the reason if it is paused, `stalled`, `blocked: <reason>`, `done`, `failed`), who is running or has unread work in its team, runs used against the budget given for it (every run of any agent in the task's team from when it was given to its final `done`/`failed` result, or now, across scheduler restarts; the budget is the task's own plus every later grant), the time since the team's last activity, and for finished tasks the artifact paths and the runs returned. Then one `Needs you:` line, with the message id, for every unread item in your inbox that waits for a decision (blocked or failed results, notes such as budget requests and escalations, runtime notices); `done` results and quiet budget notices are not listed. With `wait_seconds`, a task counts as in progress while it is `working` or `waiting`, and also while it is `blocked` or `stalled` but an agent below it is running or can run (unread mail that wakes it and budget left), for example right after you granted the lead runs; the call returns at once only when nothing in the org can run, and ends early when the last thing that could run stops. It only reads; `hirearchy inbox` still shows the messages. The Python entry point is `hirearchy.progress.progress(org, task_id=None)`.

```
"Competitor report": waiting on ceo/writer. runs 2 of 12. last activity 4m ago. (task 20261017T175121-root-8218)
"Second": blocked: Need the 2025 sales figures from finance. runs 1 of 5. last activity 1m ago. (task 20261017T175135-root-fc1a)
Needs you: blocked result from ceo "Second": Need the 2025 sales figures from finance (message 20261017T175135-ceo-a9b7)
```

## Create an org from a goal

Building an org for a goal goes wrong when it is improvised: scope, deliverable, budget, models and the review step get
assumed. With hirearchy registered in your kiro assistant (see [Kiro integration](#kiro-integration)) and its skill installed
(`hirearchy install-skill`), this is the whole story:

1. **Ask.** "Build me an org that produces a competitor analysis of five note apps." The assistant replies with one message
   of the questions that matter, in plain words, with a proposed default only where a generic one exists: format, length,
   exact acceptance criteria, sources and web access, workspace and tests (for code), budget in runs, models, review,
   approval, progress. A list it was not given (apps, competitors, features, source files) it asks for; it does not invent
   one. Unless you say otherwise the result goes into a new `deliverables/` folder in your current directory.
   You answer, or say "defaults".
2. **Plan.** The assistant starts from `blueprint_example(kind)` (`research`: web sources; `documents`: write from your local
   files, no web; `code`: repo workspace with tests and commits; `analysis`: your data files, read-only, analysed by a checked script), edits it with your answers and calls `propose_org`. You get
   a block headed **PLAN FOR YOU** that the assistant must show you exactly as written (about 40 lines, plain words; the instruction to show it and the end-of-block marker sit outside it): goal,
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
   (`hirearchy run --until-done` on the command line; `--until-idle` is unchanged) and logs why in `.runtime/scheduler.log`;
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
   when the work is done, it says it will wait and calls `progress(wait_seconds=N)` (up to 900; `hirearchy progress --wait N`
   on the command line): the call returns as soon as a task is done, failed, blocked or stalled, or something new needs
   you, or when the time is up, with what changed; it only reads files (no locks, nothing written) and does not wait
   when no scheduler is running or nothing in the org can run. Say how long you are willing to wait and it repeats the call; otherwise ask "status?". If you ask for cheap models, the assistant keeps the lead (it decides how every other run is spent) and the final verifier on the strong model, and says so in one line; when a lead asks for more budget it first looks for stranded runs and `reclaim`s them before asking you.
6. **Delivery.** When the task is done the assistant reads the deliverable, checks it against every acceptance criterion
   (sending it back for rework if one is unmet, never patching it itself), copies it to the path you chose, and tells you
   which criteria are met and how many runs it cost.

The same flow works without an assistant: `hirearchy plan bp.yaml` (exit status 1 on errors), `hirearchy apply bp.yaml`,
`hirearchy run`, `hirearchy progress`.

The blueprint (YAML or JSON; `blueprint_example(kind)` returns a commented template, a longer one is in
[`examples/blueprint-research.yaml`](https://github.com/oh-my-productivity/hirearchy/blob/main/examples/blueprint-research.yaml)):

```yaml
mission: ...                          # what the organization is for
needs:                                # the elicited requirements (free text unless noted)
  scope: ...
  deliverable: {description: ..., format: ..., max_words: 1500, path: /abs/path/file.md}
  quality_bar: ...   sources: ...   workspace: /abs/project/dir   budget_runs: 25   # the user's cap
  inputs: [/abs/read-only/dir]        # sources agents may read but never change (kiro enforces it; see Workspaces, inputs and confinement)
  models: {cheap: <model id>, strong: <model id>}   model_policy: ...   # optional; without models every agent runs on the org default
  review: true                        # independent reviewer required
  approval: ...   progress: ...   kind: research|writing|code   code: {tests: ..., packaging: ..., commits: ...}
agents:                               # exactly one top-level agent; nested tree
  - {name: lead, template: manager, model: strong, children: [{name: w, template: writer, model: cheap}]}
        # per agent: role, template or charter, model (id, or cheap/strong), tools, workspace, inputs, can_hire, max_children, scale
task: {to: lead, title: ..., goal: ..., acceptance: [exact, checkable items], inputs: [...], budget: 22}
```

Validation encodes the lessons of the usability studies: a deliverable and exact acceptance criteria; web tools when sources
are needed; `write`/`shell` only with a workspace inside an allowed root (default: home, temp, cwd; `--allow-root DIR` or
`$HIREARCHY_WORKSPACE_ROOTS`; never the org itself or `~/.kiro`); code goals need an engineer with a workspace; a reviewer distinct
from the author whose charter never has it edit others' files (rule 9 of the protocol); managers hold the tools and workspace
they hand down; budget within the user's cap and above the estimate; different models for drafting and review when asked;
depth and children within limits. Over MCP the blueprint is passed as YAML/JSON text and is never read from a file path.

**Budget estimate.** One pass plus one review/rework cycle. A worker's pass costs its template's `base_runs` times `scale`
(researcher 3, writer 2, engineer 4, fact-checker 2, reviewer 1, tester 2, code-reviewer 2, analyst 4, data-checker 2) and its rework costs 1. A manager's
pass costs 2 plus one per direct report; its rework costs 2. The planned budget is the estimate times 1.25 unless
`task.budget` is set. Managers get a written budget plan: each report's grant is its whole subtree, pass and its one rework (author)
or re-check (verifier) run, and the lead keeps the rest (its own runs plus a reserve). For `examples/blueprint-research.yaml`
(`hirearchy plan` prints it): 22 runs, researcher 4, writer 3, fact-checker 3, lead keeps 12. Unspent runs return up the tree on each
final report (see the budget rule above; a lead can pull them back from an idle report with `reclaim`), so the planned figure is
what you authorize at most, and `progress` shows what was used and returned.

**Role templates** live in `src/hirearchy/roles/*.md`: `manager`, `researcher`, `writer`, `reviewer`, `fact-checker`, `engineer`,
`tester`, `code-reviewer`, `analyst`, `data-checker`. Each has purpose, responsibilities, decision rights, escalation, quality bar, budget discipline and a
default tool set and model tier. Reviewers report findings and required changes to their manager and never edit another
agent's file (the manager sends them back to the author with `revises`). `template:` plus a `charter:` adds your own text.

What the templates add for verification and delegation:

- Verifier templates now check exhaustively. Fact-checking separates facts from judgement: a fact is any sentence with a number, name, version, licence, price, date or no/only/all, and it needs the page that states it and a verbatim quote; opinions go in a labelled section, uncited, resting on verified facts. The `fact-checker` writes a ledger of every factual claim, opens each cited source (homepages/repo roots that don't state the claim are "unsupported") and ends with the coverage line `n of m factual claims verified (n = m required); k wrong, u unsupported, p not-checkable; j judgement statements, each resting on verified facts: yes`; the manager pastes it verbatim in every `done`, and the review fails unless n = m. The `reviewer` goes through the acceptance criteria one by one ("criteria met: n of m", pass only if n = m).
- Unverifiable claims are cut or reframed by the author, never re-sourced from memory; after one failed verification cycle the manager cuts instead of researching again, then escalates with options.
- Verifiers get the project and the authors' workspaces read-only as `inputs` unless they can already write there; explicit `inputs` that hide the reviewed work raise the warning `verifier-cannot-read`.
- `blueprint_example("analysis")`: data analysis with read-only data, a scratch workspace, an `analyst` and an independent `data-checker`. The data-checker recomputes the key figures with its own script and checks figures with their label: (label, number) pairs, not numbers alone.
- `code-reviewer` now has `read` and `shell`: it runs the test suite and the commands named in the criteria and reports each command and result; it still never edits files (charter-enforced, since shell can't be confined). It needs a workspace, like the engineer.
- The lead (`manager`) runs on the strong model, even when the drafters are cheap, because it decides how every other run is spent; the plan warns `manager-cheap-model` if it is put on a cheap one. By default there is no cheap model (see Models): every tier is claude-sonnet-5.5 and the warning cannot fire.
- The lead delegates a step only when its inputs exist (research, then write, then check) and never sends status messages; results wake it.
- A failed check goes back to the author of the failing file (`delegate(revises=...)`, required changes quoted verbatim), with one cut-or-reframe rework and one re-check of that same file. If it still fails, the lead reports `blocked` with options and the coverage line.
- `manager` verifies with its own `read` output (never memory or a report's claim), treats the verifier's coverage report as a precondition for `done`, and sends deviations back with `revises` or escalates instead of reporting `done`.
- `writer`/`researcher`/`engineer`/`tester` got small additions: relevance over length, page-level citations with retrieval date, tests run before reporting, every criterion exercised with commands.

So acceptance criteria should ask for the coverage report ("every factual claim verified, n = m"), not for "at least N" checks.

**The assistant's playbook** is `skills/hirearchy/SKILL.md`: the precondition (use hirearchy or say it is unavailable), the one-message
checklist, plan and approval, build and run, monitoring, and verification before delivery. The server's own instructions carry
a compact version of the same workflow, so an assistant without the skill still gets the order of steps. How to install the
skill: see [Kiro integration](#kiro-integration).

## Services and reflection

A one-off task teaches the org nothing. Work you want again and again is better offered as a **service**, and a team should get better at
it. Two concepts:

- A **service** is a standing task one agent (the owner, usually the lead of a team) offers. Its **contract** (`SERVICE.md`) is the
  client's: what may be asked (inputs), what is guaranteed (exact acceptance criteria, deliverable), the runs handed down with each
  request, and `locked`. Its **playbook** (`PLAYBOOK.md`) is the owner's: how the team does it (steps, budget plan, pitfalls).
- **Reflection** is the default loop that improves the playbook. After each request the owner reports with `lessons`; the client gives
  `feedback`; before the next request the owner's prompt shows the evidence since the playbook's last revision and it may
  `revise_playbook`. The owner cannot touch the contract, so "improving" can never mean "lowering the bar".

On disk, `ceo/services/weekly-brief/` holds `SERVICE.md` (the contract, written with `define_service`), `PLAYBOOK.md` (the owner's, via
`revise_playbook` only) and `history/` (every earlier version of both; restore one by revising back to it).

Cases (a request plus its rework chain), their statistics and the digest are never stored; they are derived from the message files
and run logs like all state. `services` is a reserved name; plain `write` into it is refused. Retiring the owner takes its services along.

**Tools** (workers see none of them but `report`'s `lessons`):

| who | tools |
|---|---|
| root, and an agent with reports or `can_hire` | `services`, `define_service` (contract of a direct report's service; on an existing one it is an amendment: pass only what changes, e.g. `add_acceptance=[...]` / `remove_acceptance=[...]`; the old contract is archived and the owner quietly told exactly what changed), `request(service, inputs, ...)`, `feedback(task_id, accept\|reject, note)` |
| an agent that owns a service | `services`, `revise_playbook(service, content, reason)` |
| every agent | `report(..., lessons)`: required for `done`, `failed` and `blocked` on a service request |

A request is a task built from the contract (inputs, its criteria plus any `extra_acceptance`, the deliverable, its budget), so every
rule of tasks applies: direct reports only, budget moves down, `done`/`failed` are final, rework is `revises`.

CLI (as root): `hirearchy services`; `define-service OWNER NAME --description T --input 'topic*:what it is about' --acceptance T|@file
--deliverable T [--format F --max-words N --path DIR] --budget N [--playbook @file] [--locked]`; to amend, pass only what changes: `define-service OWNER NAME --add-acceptance T [--remove-acceptance EXACT_TEXT]` (also `--no-locked`; `--acceptance` replaces all and excludes add/remove); `request SERVICE --input key=value
[--title --note --budget --revises]`; `feedback TASK_ID accept|reject [--note]`; `retire-service OWNER NAME --reason T` (the only way to
retire one: there is no MCP tool for it).

**What the owner sees.** Only an agent that owns a service gets more in its prompt (everyone else's is byte-identical): `# Your services`
(versions, requests so far, file paths) every run; `# Playbook: <service> (v<n>)` while it holds an open request for it; and, when the
batch holds a NEW request and there is evidence since the playbook's last revision, `# Reflect before you start: <service>`: the cases with
new evidence (state, runs used of budget, rework, the client's verdict and note, its own lessons), statistics per playbook version, and
the steps: revise if a change would prevent what repeats or was rejected, restore an older version if the current one did worse, else leave it
alone (`report` reply and ORG.md rule 10 carry the rest).

**Guardrails.** The contract belongs to the client; the playbook may only raise the bar (a lasting requirement from feedback goes to the
parent, who adds it to the contract with `define_service`). A playbook is capped at `playbook_max_words` (default 1000), must differ from the
current one and needs a reason naming its cases; every version is kept in `history/`. `locked: true` takes revising away (the evidence is
still shown). Playbook and contract notices to root are quiet (not under "Needs you"); feedback costs no run and wakes nobody.
`progress` tags service tasks `[service <name> v<playbook>]` and says "no feedback yet" when finished; `status` shows `services:`.

**What study E changed.** A parent's rewrite of a report's `AGENT.md` keeps every frontmatter key the new text does not set (`tools`,
`inputs`, `model`, ...), and the write reply lists the kept and changed keys. The feedback note says it is for reflection only and never
waives an acceptance criterion (ORG.md rule 10 too); the assistant records `feedback` only on the user's own judgement, not on "deliver as
is". `lessons` are required for `done`, `failed` and `blocked` service reports, and the digest shows each case's latest lessons first.
`send(budget=N)` replies with what the recipient can now hand down (size a request at the estimate + 25%, about 2 runs per delegation + 1).
Agents with the built-in `read` can also read the organization's files (read-only; the org root is in their allowedPaths), so a reviewer
opens an author's `work/` file directly. Verifiers report doubtful items as `ambiguous`.

**What study E2 changed.** Every feedback verdict of a case is kept: the digest shows `reject "<words>" -> accept "<words>"` and the statistics
count accepts that came after a reject. The Reflect section also appears when a reject arrives, telling the owner to decide then whether the
playbook must change; the client's feedback outranks the owner's own lessons. A request plus its reworks is one case: rework replies and
`progress` show the case total against the per-request budget; client-driven reworks no longer count against an agent's `low_quality` health. The skill asks the user (not the team) when a reviewer evidenced a PASS and only the reading of a criterion is in doubt, asks about
relative or vague values ("before Friday") up front, says so when it adds a criterion unasked, asks before a rework passes the budget and states the case total at delivery. The plan block starts at a bare `PLAN FOR YOU` line; the show-verbatim instruction and a marker
line sit outside it.

**In a blueprint.** `services:` next to `agents:` (any of the four kinds: `blueprint_example(kind, service=True)`; a filled research one is
[`examples/blueprint-service.yaml`](https://github.com/oh-my-productivity/hirearchy/blob/main/examples/blueprint-service.yaml)):

```yaml
services:
  - name: weekly-brief                # unique; requests name the service only
    owner: lead                       # optional; must be the top-level agent in this version
    description: A one-page, sourced brief on the past week's news about a topic.
    inputs: [{name: topic, description: what it is about, required: true}]   # what changes per request
    acceptance: [exact, checkable criteria]    # the contract: only the user changes it, through define_service
    deliverable: {description: one markdown file, format: markdown, max_words: 600, path: /abs/folder}
    budget: 22                        # runs per request; default = estimate + 25%; also optional: locked: true
    playbook: |                       # optional initial workflow; default generated from the team (steps, budget plan, pitfalls)
task: {service: weekly-brief, inputs: {topic: solid-state batteries}}   # optional: a first request; or omit and request later
```

`task` becomes optional; `needs.deliverable` and the task's acceptance are only required for a plain task, and `needs.budget_runs` is the
cap for ONE request (each service's budget must be within it and above the estimate). The PLAN FOR YOU block gains a compact Services part
(what you provide, runs per request, the first checks, where it is delivered), one line on reflection, and "nothing runs until you ask for
a request" when there is no first task. `apply` hires the team, defines each service (a given or generated playbook v1) and sends the first
request (or says the services are ready: `request(service, inputs)`, then `start()`). The skill uses `services()` before building anything
and asks "Keep it, or what should change?" after each delivery to record `feedback`.

**Limitations.** No schedules (a request is made when someone asks). Only a parent requests from its direct reports: no sibling or
cross-team requests, and a blueprint service is owned by the top-level agent. Runs of concurrent requests to one owner are attributed by
the same progress window rule as tasks, so overlapping cases can be misattributed. Statistics are counts, not scores: quality is the client's verdict.

## Health

Health is measured from the files alone (message files and `runs/*.log`); nothing extra is stored. A run starts at
the timestamp in its log file name and ends at the log's mtime; a run is *empty* if the agent sent no message during it.

```sh
uv run hirearchy health [--agent ADDR] [--json]
```

Prints a summary line (`3 agents, 1 flagged`), then one line per agent (indented by depth) with state, budget
(left/received), runs, open tasks and the age of the oldest, results by status, rework, runs per completed task,
empty runs, time since last activity, branch totals for managers, and any flags with their reasons.
`--agent` limits it to that agent and its subtree; `--json` prints the structured data.

The MCP tool `health(agent=None)` returns the same report. Root may ask about anyone; any other agent may ask
about itself or an agent in its own subtree. By default it reports your own subtree (root: the whole organization).

"Rework" counts tasks an agent received with `revises` set: a manager sends work back with
`delegate(..., revises=<earlier task id>)` (CLI: `hirearchy task ... --revises TASK_ID`). The id must be a task the
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
`hirearchy health`.

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
| `events` | true | write the event log (`.runtime/events/<day>/<proc>-<pid>-<start>.jsonl`, git-ignored); `false` = no emission |
| `events_keep_days` | 30 | the scheduler deletes event-log days older than this (at most once a day) |
| `heartbeat_seconds` | 60 | how often the scheduler writes a `scheduler.heartbeat` event |

Runs that failed, and runs woken only by runtime notes (budget, stall, review, budget refunds), are left out of the
`wasteful` statistics. The retired agents' runs still count towards `review_every_runs`.

```sh
uv run hirearchy review [--dry-run]
```

Runs a review immediately through the same code path and prints what was sent to whom. `--dry-run` prints what
would be sent and writes nothing (no messages, no ledger).

## Observability

Questions an operator can answer from the org directory alone, each with one command (or one call of the root-only MCP tool `observe`):

| Question | View |
| --- | --- |
| What is happening right now? Is the scheduler alive, what runs, what is queued and why is it not running, what waits on me, what broke in the last 15 minutes? | `obs now` |
| What exactly happened to request X, in order, and why? Every message, run, tool call and refusal, with who, when and how long. | `obs trace TASK_ID` |
| Where did time and runs go (queue wait vs run time vs waiting on me; runs and budget per agent)? | `obs trace` totals, `obs metrics` |
| Is the system healthy or degrading (error and refusal rates by tool and reason, failed or timed-out runs, stalls, pauses, scheduler faults, latency percentiles)? | `obs metrics` |
| Show me the raw record (filter by time, agent, kind, trace, errors; follow live). | `obs events` |
| Is the runtime itself consistent (budget conserved, messages intact, nothing stuck, runs accounted for)? | `check` |

Everything is derived from **one append-only event log** written by the runtime (never by agents) plus the message files and run logs that already exist. There is no metrics store, no daemon, no network and no new dependency. Orgs created before this keep working: with no events the views fall back to messages and run logs and say `[partial]`.

### The event log

- **Files.** `.runtime/events/<YYYY-MM-DD>/<proc>-<pid>-<start_epoch_ms>.jsonl`, one file per process per UTC day, written only by that process (`proc` is `scheduler`, `mcp` for an MCP server, or `cli`). Readers glob and merge by `ts`. The directory is git-ignored (`.runtime/events/` is added to `.gitignore` by the first event of an org that lacks it).
- **Envelope** (every line is one JSON object): `v` (1), `ts` (UTC, microseconds), `seq` (lines of this file, from 1 in each day's file: a gap means a lost line), `proc`, `pid` (the emitting process), `kind`, `actor` (`root`, an agent address, or `runtime`), `run` (`<agent>@<run log stem>`, null outside a run) and `trace`. The scheduler hands the run id to the kiro process as `ORG_RUN_ID`; the MCP server kiro spawns inherits it, so an agent's tool calls carry its run id.
- **Emission never breaks an operation.** A failure is swallowed, counted and reported once per process on stderr; a line is one `write()` on an append-mode file (flushed, no fsync) and at most 8 KB (longer ones are shrunk and marked `"truncated": true`).

| Kind | When (extra fields) |
| --- | --- |
| `scheduler.start` / `scheduler.exit` | `mode`, `max_runs`, `max_parallel`, `version` / `reason`, `runs_started` |
| `scheduler.heartbeat` | every `heartbeat_seconds`: `running` (run ids), `runnable`, `waiting_on_you` |
| `scheduler.error` | a tick phase raised (`phase`, `error`); the tick goes on |
| `run.start` | `agent`, `run`, `batch` (message ids), `traces`, `child_pid`/`pgid` (the kiro process; the envelope `pid` is the scheduler's), `model`, `budget_before` |
| `run.end` | `ok`, `exit_code`, `duration_ms`, `timed_out`, `killed`, `budget_after`, `error` |
| `run.orphan` | recovery at startup of a dead scheduler's run: `killed`, `redelivered` or `kept` |
| `agent.pause` / `agent.resume` / `agent.failure` | reason / failure count |
| `stall.nudge` | each step of the stall ladder (`task`, `to`, `step`) |
| `review.run`, `prune` | health review sent (`flagged`, `notes`); event-log days removed |
| `tool.call` | every hirearchy tool, agents and root: `tool`, `ok`, `ms`, `error` (the refusal text), `error_type` (`OrgError` or the exception class), `args` (a summary, below) |
| `cli.command` | `command`, `ok`, `ms`, `error` |
| `msg.deliver` | every message: `id`, `type`, `from`, `to`, `title`, `status`, `budget`, `reply_to`, `revises`, `service`, `wake`, `hops`, `chars`, `trace_rule` (+ `trace_candidates` when ambiguous) |
| `agent.hire` / `agent.retire`, `service.define` / `service.revise` / `service.retire` | who, what, returned budget |

**Never recorded:** message bodies, file contents, environment values, secrets. `tool.call` `args` keeps ids, addresses, clipped titles (80 characters), status, budget, paths, service names, verdicts and numbers; long text fields only as their length (`"summary_chars": 1234`); unset arguments are omitted. Errors are clipped to 500 characters. **Out of scope:** the provider is a black box. We observe a run's boundaries (start, end, exit, duration, batch) and every hirearchy tool call it makes, never kiro's internals (tokens, built-in tool calls, model reasoning). There are no exporters, dashboards, sampling or alerting; the field names are OTel-friendly so a file exporter can be added later as a pure function over the events.

Config (`ORG.md`): `events` (default `true`; `false` disables emission entirely), `events_keep_days` (30; the scheduler prunes older day directories at most once a day), `heartbeat_seconds` (60).

### Traces

A **trace** is one request from root. Its id is the id of root's task; a rework (`revises`) stays in the trace of the task it revises. Every message gets a `trace` frontmatter field stamped by the runtime at send time; the first matching rule wins and is recorded as `trace_rule` in the `msg.deliver` event:

1. `new`: root sends a task without `revises`: its own id.
2. `link`: the message has `reply_to` or `revises` and that message has a trace: that trace (otherwise the next rules apply).
3. `open-task`: the sender's open tasks (received, no final result; a `blocked` result is not final) all share one trace.
4. `batch`: the sender's current batch (its `inflight/` messages) has exactly one distinct trace.
5. `ambiguous`: no trace is stamped (the event lists `trace_candidates`). Root's plain notes and grants have no `reply_to`, so they may be untraced; the trace view attributes them to the request by the same window rule `progress` uses.

Runtime notices carry the trace of the task they are about when known. Messages of orgs created before traces are traced by the views (walking `reply_to`/`revises` and the same rules over the files), marked `~`. `trace` accepts a root task id, a rework of it, or any message of the request.

### Views

```sh
uv run hirearchy obs now [--watch SECONDS]
uv run hirearchy obs trace TASK_ID [--json]
uv run hirearchy obs metrics [--since 24h] [--by agent|tool|service|trace] [--json]
uv run hirearchy obs events [--since 24h] [--until T] [--agent ADDR] [--kind KIND] [--trace TASK_ID] [--errors] [--limit N] [--follow] [--json]
uv run hirearchy check [--json]        # exit 1 when an invariant fails
```

Durations are `15m`, `24h`, `7d` or an ISO timestamp. The MCP tool `observe(view="now"|"trace"|"metrics"|"events"|"check", target=None, since="24h", by=None, errors_only=False, limit=50)` is offered to root only and returns the same text. Sample output from a real kiro run (`claude-haiku-4.5`, one agent that calls `whoami`, `write` and `report`; the full record is in `studies/O-observability-check/`):

```
$ hirearchy obs trace 20261018T092904624658-root-a621
trace 20261018T092904624658-root-a621 "Tool check" -> worker: done
     +0s  root -> worker task "Tool check" +2 run(s)
     +8s    run 20261018T092912856677 ok, ran 14s, queued 8.2s, 3 call(s) [report×1 whoami×1 write×1]
    +20s    worker -> root result (done) "Tool check" +1 run(s)
totals: wall 20s | runs 1 (budget given 2, returned 1) | run time 14s | queue 8.2s | waiting on you 0s | tool calls 3 (0 refused)

$ hirearchy obs now                      # while the scheduler runs
scheduler: running pid 5585 (until_idle, up 9.0s, last heartbeat 9.0s ago)
runs in flight 1/3:
  worker 9.0s Third check trace 20261018T093211981048-root-723b
queued, not running: none
waiting on you: nothing
errors in the last 15 min: 0

$ hirearchy obs metrics --since 1h
metrics 2026-10-18T08:30:20Z .. 2026-10-18T09:30:20Z (18 event(s) in the window)
runs 1: ok 1, failed 0, timeout 0, killed 0 | duration p50 14s p95 14s max 14s (n=1) | queue p50 8.2s p95 8.2s (n=1)
budget spent 1 run(s)
tool calls 3, refused 0 (0.0%)
  report               1 calls   0 refused (0%) p50 3ms p95 3ms
...
```

A refusal and a crashed run, from the test organization (`tests/e2e/test_observability_e2e.py`: a manager and a report, real scheduler, fake agent):

```
trace 20261018T091640455395-root-5160 "Ship it" -> ceo: done
     +0s    run 20261018T091640456990 ok, ran 341ms, queued 6ms, 3 call(s) [delegate×1 whoami×1 write×1]
     +0s      run 20261018T091640766755 failed, ran 71ms, queued 29ms, 0 call(s), error: exit code 1
     +0s      * agent.failure agent=ceo/eng count=1
     +0s      run 20261018T091640875315 ok, ran 264ms, queued 137ms, 4 call(s) [report×2 whoami×1 write×1], 1 refused
                ! report: status must be one of ('done', 'failed', 'blocked')
```

`trace` lists, in time order and indented by agent depth, every message (delegations, results, notes, grants), every run (queue wait = run start minus its earliest batch message; duration; ok, failed, timeout or killed with the cause) with its tool-call counts and every refusal's text, and the totals: wall time, runs (equal to what `progress` reports for the task; a request with reworks lists each task's runs), run time, queue time, time waiting on you (from a blocked or needs-you item to your next action), tool calls, refusals, budget given and returned. Without events it works from messages and run logs and is marked `[partial]`. `obs events --errors` shows every refused call with its text, every failed or killed run and every scheduler fault.

### `check` invariants

Each is PASS or FAIL with details naming the defect: **(a)** every message file parses, ids are unique, every sender copy has a recipient copy and vice versa; **(b)** budget is conserved (everything root handed down = budgets held + runs used, live and retired, + returned to root + dropped at retirement); **(c)** nothing is in `inflight/` without a live run; **(d)** every `run.start` has a `run.end` or a live process, and every run log since events began has a `run.start`; **(e)** each event file has no `seq` gaps (it counts from 1 in each file); **(f)** the scheduler pid file matches a live scheduler of this org.

## Dashboard

`hirearchy dash` is a read-only terminal dashboard for a running org: the agent hierarchy with what every agent is doing, its run log, messages and activity, your requests with their traces, services, the live event stream and health. It never writes inside the organization and emits no event; grants, start/stop and feedback stay with the assistant and the CLI.

```sh
hirearchy --root ORG dash [--interval SECONDS]   # the interactive dashboard (default refresh: 2 s)
hirearchy --root ORG dash --once                  # a plain-text snapshot, then exit (also used without a terminal)
```

An agent is in exactly one state, with this precedence: `running 1m12s` (a run is in flight; mail that arrives meanwhile is `+N unread`); `paused: <reason>` (plus `, N unread`); `out of budget` (plus `, N unread`); `queued: <why>, N unread` - only when the agent would run and has not started yet: `scheduler is not running`, `max_parallel (N) runs are busy` or `starts on the next tick`; otherwise `waiting on N report(s)`, `working on N task(s)` or `idle`. The words are derived from the same files as `status`, `progress` and `obs now`. The header shows the org, the scheduler (running pid / uptime / last heartbeat, or stopped and why), the counts running, queued, waiting on you and errors in the last 15 minutes, and `refresh 2s` / `refresh paused` (and `refresh failed` when the last refresh did). Events are shown as one readable line each (`10:05:40 delegate → ceo/analyst REFUSED: not enough budget: ...`, `10:06:00 run ended ok after 33s`); `x` on the Activity tab and on the Events screen shows them raw, with ids, process groups, budgets and arguments. Screenshots of every screen of a demo org are in `studies/DASH-screens/` (`make_screens.py` regenerates them).

| Key | Does |
| --- | --- |
| `1` `2` `3` `4` `5` | Org · Workflows · Services · Events · Health |
| `↑` `↓` / `j` `k`, `g` `G` | move, top / bottom |
| `←` `→` / `h` `l` | fold / unfold a node, or switch pane (`h` returns to the tree) |
| `Enter` | open: agent → its details, request → its trace, service → cases, playbook and contract, message → its text |
| `Esc` / `Backspace` | back (close an overlay, leave a trace or a service) |
| `Tab` / `Shift+Tab` | cycle focus between the panes |
| `[` `]` | previous / next tab of an agent: Overview, Activity, Messages, Run log, Memory, Charter |
| `r` / `p` | refresh now / pause and resume the automatic refresh |
| `e` `/` `f` `x` | Events: errors only, filter (words matched against agent, kind, trace, tool and the text of the line), follow on/off, raw events (also on an agent's Activity tab) |
| `c` | Health: run the consistency check (`obs check`) on demand |
| `?` / `q` | all keys / quit |

Refreshes keep the selection, the scroll position and the folded nodes; the Run log tab follows a growing log (it shows the last 2000 lines). Long text wraps in the detail panes and the trace; a state in the narrow agent tree is cut with an ellipsis (the whole state is in the Overview tab). A refresh that fails is shown in a red status line above the footer and the dashboard keeps running. The traces and the check are computed when opened, not on every tick.

What `--once` prints (the demo org of `studies/DASH-screens`):

```text
hirearchy dash - acme (/path/to/acme)  2026-10-18 10:06:40Z
scheduler running pid 7000 (until_done, up 6m40s, heartbeat 3.0s ago) | running 2/2 · queued 1 · waiting on you 1 · errors 15m 2

AGENTS
★ root (you)  needs you: 1
  ○ archivist [Archivist]  idle  budget 0  claude-sonnet-5.5
  ▶ ceo [Chief executive]  running 1m12s  budget 3  claude-sonnet-5.5
    ◔ analyst [Competitor analyst]  queued: max_parallel (2) runs are busy, 1 unread  budget 4  claude-opus-5.5
    ◆ writer [Report writer]  working on 1 task(s)  budget 2  claude-sonnet-5.5
  ◇ ops [Operations lead]  waiting on 1 report(s)  budget 3  claude-sonnet-5.5
    ‖ audit [Auditor]  paused by the user: audit window closed  budget 0  claude-sonnet-5.5
    ‖ deploy [Deploy engineer]  paused: 2 consecutive failed runs, 1 unread  budget 1  claude-sonnet-5.5
  ▶ research [Research lead]  running 2m05s  budget 4  claude-sonnet-5.5
    ! crawler [Web crawler]  out of budget  budget 0  claude-sonnet-5.5

NEEDS YOU
  Needs you: note from ops "Need approval for downtime": The key rotation needs a maintenance window. May I take the API down on Saturday 02:00? (message 20261018T100200000003-ops-007b)

REQUESTS
  "Brief: heat pumps" -> research: working (running: research); runs 2 of 6, last activity 5.0s ago
  "Brief: EV chargers (shorter)" -> research: done; runs 1 of 4 (3 returned), last activity 5.0s ago
  "Brief: EV chargers" -> research: done; runs 1 of 6 (5 returned), last activity 5.0s ago
  "Rotate API keys" -> ops: waiting on ops/deploy (paused: 2 consecutive failed runs); runs 2 of 6, last activity 4m10s ago
  "Quarterly market report" -> ceo: working (running: ceo; unread work: ceo/analyst); runs 3 of 12, last activity 0s ago
  "Archive old reports" -> archivist: done; runs 1 of 3 (2 returned), last activity 6m18s ago

SERVICES
  research/market-brief  contract v1 playbook v1  2 request(s): 1 done, 0 failed, 1 open; 1 reworked; avg 2 runs; feedback 1 accept (1 after a reject), 0 reject
```

## Kiro integration

**Talking to the org yourself (you act as `root`).** Register the server globally; it does not need an
organization to exist yet:

```json
"hirearchy": {
  "command": "uv",
  "args": ["--directory", "/path/to/hirearchy", "run", "hirearchy", "mcp"],
  "env": { "ORG_ROOT": "/path/to/your/org" }
}
```

- The server is bound to exactly one path for its lifetime: `ORG_ROOT` (or, when it is unset, the organization found
  from the working directory). It never falls back to another organization.
- If nothing exists at that path (missing or empty directory), the server still starts in *setup mode*: `whoami` and
  `status` explain the next step, every other tool answers `no organization at <path> yet: call create_org(mission=...)
  first`, and `create_org(mission, default_model=None)` (None = claude-sonnet-5.5) creates the organization there. From then on all tools work
  in the same session, no restart. `create_org` refuses a directory that holds anything else, and an organization that
  already exists (which is then ready to use). With `ORG_ROOT` unset and no organization in the working directory it
  needs a `path` (absolute); with `ORG_ROOT` set a different `path` is refused.
- Root-only tools: `create_org`, `start(max_runs=None)` (launch a detached scheduler for this org, output in
  `.runtime/scheduler.log`, returns its pid; refused if one runs), `stop()` (SIGTERM, only to a pid verified to be this
  org's scheduler: alive, `run` in its command line, and this org's `--root` or a `hirearchy` program with no other
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
- Other tools: `whoami`, `inbox`, `delegate`, `report`, `send`, `hire` (with `inputs` for read-only folders), `retire`, `reclaim`, `read`, `write`, `status`, `health`.
  Agents get these (not `create_org`, `start`, `stop`, `blueprint_example`, `propose_org`, `apply_org`, `progress`). `report` tells an agent when
  budget travelled up with its result; `send(..., budget=N)` to its parent gives runs back early. `reclaim(report, budget=None)` (managers and root; direct, idle reports only) pulls unspent runs back down the other way.
- The server's instructions for root contain the workflow in five lines (ask once → `blueprint_example` + `propose_org` →
  show the PLAN FOR YOU block, wait for explicit approval → `create_org`/`apply_org(approved=True, plan_id)`/`start` →
  `progress` (or `progress(wait_seconds)`) → verify, copy) next to the safety
  rules: only the bound organization, no substituting other mechanisms, no claims without tool evidence.

**The assistant skill.** `hirearchy install-skill [--dest DIR] [--force]` copies the skill to `~/.kiro/skills/hirearchy/SKILL.md`
(`DIR` is the skills directory: the file goes to `DIR/hirearchy/SKILL.md`), prints the path, leaves an identical file alone and
refuses to replace a different one without `--force`. Kiro loads skills through the `resources` of an agent profile as
`skill://` entries (a path or a glob): the profiles in `~/.kiro/agents` use `"skill://.kiro/skills/*/SKILL.md"`. To use the skill from a project-local profile without installing it, give the
absolute path of the checkout's file, for example in `<project>/.kiro/agents/org-assistant.json` (the file validates with
`kiro-cli agent validate --path <file>`, which checks the shape of the entries, not that the file exists):

```json
{
  "name": "org-assistant",
  "description": "Builds and runs a hirearchy organization for a goal",
  "prompt": "You manage one hirearchy organization for the user through the hirearchy tools. Follow the hirearchy skill.",
  "mcpServers": {
    "hirearchy": {
      "command": "uv",
      "args": ["--directory", "/path/to/hirearchy", "run", "hirearchy", "mcp"],
      "env": { "ORG_ROOT": "/path/to/your/org" }
    }
  },
  "tools": ["*"],
  "resources": ["skill:///path/to/hirearchy/skills/hirearchy/SKILL.md"],
  "includeMcpJson": false
}
```

Run it with `kiro-cli chat --agent org-assistant`. This profile binds the assistant to one organization (and keeps your other
MCP servers out); `tools: ["*"]` lets it copy the finished deliverable with kiro's own file tools, so narrow it if you prefer
to copy files yourself. Use a name other than `hirearchy-...`, which the scheduler's internal profiles use.

**Agent runs (the scheduler).** Runs use `kiro-cli chat --no-interactive --agent <profile>`; the prompt is passed
on stdin. The scheduler writes one *internal* profile per organization (and per set of granted built-in tools) to
`~/.kiro/agents/`:

- name `hirearchy-<org-slug>-<6-char hash of the org path>[-<tools>]` (lowercase `[a-z0-9-]`), description "internal:
  used by the hirearchy scheduler for <org path>; not a general-purpose agent". Different orgs never share or overwrite a
  profile.
- It loads only the hirearchy server (`includeMcpJson: false`), so agents never see your other MCP servers. The server
  entry carries `ORG_ROOT=<this org>` and `ORG_REQUIRE_AGENT=1`.
- Fail closed: with `ORG_REQUIRE_AGENT=1` the server refuses to start unless `ORG_AGENT` names an agent (`root` does not
  count). If something borrows a profile as a general subagent, it gets an error instead of acting as `root`.
- `ORG_AGENT` is not baked into the profile: the scheduler sets it per run in the process environment of `kiro-cli`.
  This relies on kiro starting MCP servers with its own environment plus the profile's `env` (the same inheritance the
  scheduler always used for `ORG_AGENT`/`ORG_ROOT`). If a kiro version replaced the environment instead, runs would fail
  visibly with the message above rather than act as root.
- Older global profiles (`~/.kiro/agents/hirearchy*.json`) are no longer written or used; they are never deleted or
  rewritten, so remove them yourself when no scheduler that uses them is running.

### Workspaces, inputs and confinement

Two path worlds meet in a run: hirearchy tools (`read`, `write`, `report`, `delegate` inputs) use paths relative to the
**org root**; kiro's own tools (`read`, `write`, `shell`) start in the agent's **workspace** (its charter `workspace`, else
its org directory) and resolve relative paths there. An agent that writes `lead/writer/work/x.md` with kiro's `write`
therefore creates that tree inside the user's folder, not in the org. The charter fields and the rules below keep the
two apart.

The two kinds of tools share short names, and kiro lists MCP tools by their plain names, so a built-in `read` or `write`
**shadows** the hirearchy tool of the same name: an agent that holds it sees one `read` / one `write`, kiro's, and cannot call
hirearchy's (verified in `studies/F-read-experiment` and `studies/F2-tool-names`). The server therefore registers the hirearchy
tools by what the charter's `tools` hold:

- charter `tools` holds `write`: the hirearchy write tool is **`org_write`** (else `write`);
- charter `tools` holds `read`: the hirearchy read tool is **`org_read`** (else `read`).

(`shell` alone changes nothing; root and agents without built-in `read`/`write` keep `read` / `write` exactly.) In kiro the
hirearchy tools appear as `@hirearchy/org_write`, `@hirearchy/org_read`, `@hirearchy/report`, ... The agent's prompt (Files section,
"update your memory" line, stray-file notice) names the tool *it* has: `@hirearchy/org_write` for `<addr>/MEMORY.md`,
`<addr>/work/` and reports, and the built-in `write` for the workspace only. ORG.md's shared rules say `@hirearchy/write`
generically; the per-agent line says to use the `org_` name wherever it appears. `org_read` takes **relative** org paths
(and the absolute workspace/inputs paths below). The built-in `read` reaches the org too, but only by **absolute** path
`<org root>/<path>`: a relative path starts in the agent's working directory (its workspace, else its org directory).
**Stray org files:** after each run of an agent with built-in `write` and a workspace, the scheduler looks for
`<workspace>/<address>/` (new during the run) and a written `<workspace>/<address>/MEMORY.md`. If found it logs a
`# warning:` in the run log and the scheduler output and records it in `.runtime/strays.json`; the agent's next prompt says
once to move that content into its org files with its hirearchy write tool. Nothing is moved or deleted.

Charter fields: `workspace` (read-write, as before) and `inputs: [absolute paths]` (read-only; blueprint: `needs.inputs`
for the whole project or `inputs` per agent). A report's inputs must be inside its manager's inputs or workspace (authority
only narrows), inputs are absolute and never overlap the org directory. Charters without `inputs` keep working. Set them with
`hirearchy hire ... --inputs PATH` (repeatable) or the `inputs` parameter of the `hire` tool (root, or a manager within its own
inputs/workspace); `documents`-type goals put the user's folder in `needs.inputs` (it must exist).

**Enforced by kiro** (per-agent profiles, checked against kiro-cli 2.29.1 in `--no-interactive` mode; the experiments are
in `studies/X1-confinement/EXPERIMENTS.md`). An agent with built-in `read` or `write` gets a profile
`hirearchy-<org>-<hash>-<tools>-x<access hash>` (same `ORG_ROOT`/`ORG_REQUIRE_AGENT=1`, same "internal" description; agents with
equal tools and access share it) whose `toolsSettings` say:

```json
"tools": ["@hirearchy", "read", "write"],
"allowedTools": ["@hirearchy"],
"toolsSettings": {
  "write": {"allowedPaths": ["/ws/**"], "deniedPaths": ["/org", "/org/**"]},
  "read":  {"allowedPaths": ["/ws", "/ws/**", "/inputs", "/inputs/**", "/org", "/org/**"], "deniedPaths": []}
}
```

- `read`/`write` are deliberately **not** in `allowedTools`: a trusted tool ignores `allowedPaths`. Left out, a call on an
  allowed path runs, and any other path needs an approval, which a headless run cannot give: it is refused with "tool
  permission approval is not supported in non-interactive mode". `..` traversal is refused too.
- `write` only under the workspace (nowhere without one), so inputs are read-only and nothing is created beside them. The
  org directory is a hard deny for it (also over kiro's "the working directory is readable" rule): org files are written
  with the hirearchy tool (`org_write`) only.
- `read` under workspace + inputs + the organization (read-only), with **no** `deniedPaths` (a deny would beat the allow).
  Other paths, e.g. `/etc/hosts`, are refused. The built-in `read` is the only `read` such an agent sees, so this is how it
  reads a teammate's file by absolute path; `org_read` is the relative-path alternative. The deny is skipped for `write`
  too when the workspace is inside the org.
- Agents without built-in `read`/`write` keep the shared per-org profile. A legacy charter with only `read`, no workspace and
  no `inputs` key keeps today's unconfined read; give it `inputs: []` (or real inputs) to confine it. A confined parent never
  hands down an unconfined `read`.

**Enforced by hirearchy:** `report(artifacts=...)` takes org paths (relative or absolute) and absolute paths inside the
reporter's **own** workspace, annotated as before (words, modified, "NOT modified since..."); anything else outside the
org is refused without probing. `read` takes relative org paths, and absolute paths inside the caller's workspace, its
inputs, and the workspace of any agent in its subtree (a manager can verify what its team made); everything else outside
the org is refused. Root's `read` is unchanged (organization only).

**Only instructed:** `shell` cannot be confined (kiro has no path rule for it; it can write anywhere its OS user can), so an
agent that holds it (engineer, tester, code-reviewer, and a manager that holds what its code team holds) is told the rule in its charter and prompt, and the plan says so (`shell-unconfined` warning, "shell NOT
confined" in its `Access:` line). The prompt's Files section (workspace, inputs, "never create org files in the workspace",
"report workspace artifacts by absolute path") is guidance on top of the enforcement above. Symlinks inside a workspace that
point out were not tested against kiro's own matching; hirearchy's `read`/`report` resolve them and refuse targets outside.

Every command that changes an organization (`init`, `hire`, `task`, `apply`, `send`, `resume`, `run`, `review`, `inbox`
without `--keep`, `upgrade-rules` without `--dry-run`, `kiro-profile`) first prints `org: <path>` to stderr. `python -m hirearchy` is the same as the `hirearchy` script.

## Security notes

- Everything is local stdio with no network listener. Identity is enforced by the process environment, not by
  authentication: anything that can run `hirearchy mcp` with `ORG_AGENT` set can act as that agent.
- The hirearchy write rules apply to the hirearchy tools. kiro's built-in `write` is confined to the agent's workspace and its
  `read` to workspace, inputs and the organization (read-only) by its profile (see [Workspaces, inputs and confinement](#workspaces-inputs-and-confinement)); `shell` is not:
  an agent that holds it can touch anything its OS user can. Grant it only to agents that need it, with a `workspace`.

## Architecture

hirearchy is organized by feature: one package per responsibility under `src/hirearchy/`, each behind an interface, wired together in one place.

```
src/hirearchy/
  kernel/          the shared vocabulary every package may use (Message, Address, Clock, IdGenerator, OrgError, ...); imports nothing else
  <feature>/       36 feature packages (mail, budget, hierarchy, health, blueprint, ...); each has
    api.py           the only public surface: its typing.Protocol interfaces, data types and exceptions (__init__.py re-exports exactly api)
    _*.py            private implementations; every class with behaviour subclasses the Protocol it implements and gets its collaborators
                     through its constructor, typed by Protocols
    testing.py       in-memory fakes of its Protocols
    tests/           its tests, next to the code; test_contract_<protocol>.py runs one contract suite against the real implementation AND the fake
  scheduler/ mcp_server/ cli/ dashboard/    the entry points; they depend only on the api of features
  app/             the composition root: the only package that imports `_` modules and constructs concrete classes
                   (`wiring.open_runtime(root)` builds the `OrgRuntime` of ports; `wire_<pkg>.py` provides each package's ports)
  core.py          the permanent compatibility facade: `hirearchy.core.Org` (+ `DEFAULT_MODEL`, `OrgError`, ...)
```

`hirearchy.core.Org` is a thin facade, built by `hirearchy.app`, that delegates every method to the feature services; no feature imports it. It, `hirearchy.progress.progress(org, task_id=None)`
and the entry point `hirearchy.main` (the `hirearchy` script, `python -m hirearchy`) are the permanent Python surface; everything else is reached through the `api` of a feature.

The rules, and what enforces them (all run by `scripts/check.sh`):

* every class with behaviour implements a Protocol and no constructor names a concrete `hirearchy` class (`tests/architecture`: class-interface check, `test_constructors_depend_on_protocols`);
* layers entry points -> features (by level) -> kernel, no cycles, the kernel imports nothing, only a package itself and `hirearchy.app` import its `_` modules, no feature imports `Org`,
  Textual / the MCP SDK / PyYAML only at the edge (50 `import-linter` contracts, generated from the package map; `mypy --strict` on every package);
* a Protocol has at most 8 methods, has a contract suite, and one writer owns each file and ledger (`tests/architecture`);
* behaviour, text and formats are frozen by the golden suite (`tests/golden`).

[ARCHITECTURE.md](https://github.com/oh-my-productivity/hirearchy/blob/main/ARCHITECTURE.md) has the package map, every interface, the dependency graph and, at the top, what was built and how it differs from the plan.

## Test

```sh
scripts/check.sh                      # EVERYTHING, exit 0 = done: pytest (unit, contract, golden, architecture) + mypy --strict + import-linter
uv run pytest -q                      # the tests alone: no LLM, no network, never touches your ~/.kiro (also runs mypy + lint-imports)
uv run pytest -q src/hirearchy/mail      # the tests of one package (they live next to its code)
uv run pytest -q tests/golden         # only the golden (characterization) snapshots, about 15 s
uv run pytest -q tests/architecture   # the structural rules (or `-m "not architecture"` to leave them out)
uv run pytest -q tests/integration --run-integration    # + the real-kiro tests (or HIREARCHY_RUN_INTEGRATION=1)
HIREARCHY_UPDATE_GOLDEN=1 uv run pytest -q tests/golden    # regenerate the golden files, deliberately (review the git diff)
uv run python scripts/static_checks.py mypy|imports     # one static check
uv run python -m tests.architecture.lint                # import contracts only: generates .importlinter (git-ignored) and runs it + the pyproject ones
uv run python -m tests.architecture.gen_importlinter    # print the generated contracts
uv run python -m tests.architecture.collected_count --write   # record the test-count floor of each package (a floor only ever goes up)
```

**Where tests live.** A feature package keeps its tests next to its code, in `src/hirearchy/<feature>/tests/` (with an `__init__.py`, so two features may both have a
`test_api.py`; `tests/architecture/test_layout.py` checks it): unit tests of each class, `test_contract_<protocol>.py` per Protocol (the same suite for the real
implementation and the in-memory fake of `testing.py`), and behaviour tests. `tests/` holds what crosses features: `tests/architecture` (the structural rules),
`tests/golden` (byte-for-byte snapshots), `tests/e2e` (scenarios through the facade, the CLI and the MCP server), `tests/meta` (tests of the test machinery) and
`tests/integration` (the real `kiro-cli`, opt-in), and the shared helpers in `tests/testkit/` (`fake_agent.py`, `kiro_sandbox.py`, the worlds that build a team, ...;
`tests/` is on `sys.path`, so `import testkit` works everywhere). `pytest` collects both trees (`testpaths`); the wheel contains no `tests/` directory. The collected count
never drops: `tests/architecture/baseline_test_count.txt` and one `count.txt` per colocated `tests/` are floors (`test_collected_count`).

**Seams, not monkeypatching.** A test gives the code under test a fake by port, never by patching a module attribute: `open_runtime(root, {Port: fake})` for one runtime, and
`hirearchy.app.wiring.overriding({Port: fake})` for code that opens its own (a CLI command, an MCP tool, the scheduler, `Org(root)`; the explicit overrides of `open_runtime` win).
The fixtures in `tests/testkit/fixtures.py`, registered by the root `conftest.py` so colocated tests get them too, do it for the common cases: `org` (a small team),
`frozen_clock(now)`, `counter_ids()` (predictable message ids), `process_overrides({...})`, and the autouse `isolated_kiro` (`$HOME` in a temp dir, a stub `kiro-cli` first on `PATH`),
`fresh_process_resources` and `process_state_guard` (a test that leaves a process-global replaced is failed by name). A colocated test that needs what its layer may not import
(`hirearchy.core`, `hirearchy.app.wiring`, `yaml`) takes it from `testkit.reach.<module>`, an alias of the very same module that import-linter does not see.

**The `integration` marker.** Tests marked `@pytest.mark.integration` (and everything under `tests/integration/`, marked or not) call the real `kiro-cli` and a real LLM; a default run
reports them as skipped, and `tests/meta/test_integration_marker.py` proves it. `--run-integration` (or `HIREARCHY_RUN_INTEGRATION=1`) runs them.

**Golden tests (`tests/golden/`).** Byte-for-byte snapshots, in `tests/golden/expected/`, of everything a refactor must not
change: run prompts, `ORG.md`, message files, charters, `SERVICE.md`/`PLAYBOOK.md`, kiro profiles and command lines, the
`propose_org` plans for every example and template, the MCP tool surface (names, parameters, defaults, docstrings, server
instructions) for root, a manager, a worker, a service owner and agents with built-in tools, the output of the CLI
(`status`, `progress`, `services`, `health`, `inbox`, `obs ...`, `check`, `dash --once`, every `--help`) and the shape of
every event line. They use a fixed clock, counter-based ids and placeholders for tmp paths (`<ORG>`, `<TMP>`, `<HOME>`,
`<VENV_BIN>`), all in the tests (`tests/golden/golden_support.py`), never in the production code. A failing golden test
prints a unified diff. **A diff in `expected/` means observable behaviour changed**: a refactor must leave the
directory untouched; a deliberate change regenerates the files with `HIREARCHY_UPDATE_GOLDEN=1` and commits them with it.

**Class-interface check (`tests/golden/test_class_interfaces.py`).** Every class with behaviour defined in `src/hirearchy`
subclasses a `typing.Protocol` (data classes, exceptions, Protocols and Textual classes are exempt; the classifier is
`tests/architecture/class_interfaces.py`, permanent exemptions `tests/architecture/exempt_classes.py`). The allow-list
`tests/golden/interface_allowlist.txt` is empty and must stay so. Its second half, `tests/architecture/test_constructor_dependencies.py`, resolves the type hints of every such
class's constructor (dataclass fields included) and fails when an annotation, however deeply nested in `Optional`, unions, generics or `Callable`, names a concrete
`hirearchy` class instead of a Protocol (data classes, enums, exceptions and non-`hirearchy` types are fine; the fakes of the `testing` modules are not checked); a seeded package proves it can fail.

**Static checks (pinned dev dependencies `mypy==2.4.0`, `import-linter==2.15`, config in `pyproject.toml`).**
`uv run python scripts/static_checks.py` runs both; `scripts/check.sh` runs them after the tests, and
`tests/architecture/test_static_checks.py` runs them inside plain `pytest` (skipped only when a tool is not installed).

* *mypy, strict, package by package:* every package directory of `src/hirearchy/` (a directory with `__init__.py`: the kernel, a
  feature, an entry point, `app`) is checked with `strict = true` and, for its `api.py`, `disallow_any_explicit`; nothing has to be
  registered, creating the package is enough. Production code is strict; the tests that were moved into the packages carry `# mypy: ignore-errors`.
* *import-linter contracts:* two sources. The contracts of the architecture (layers feature levels -> kernel, one
  `private-modules-<pkg>` per package with `_*` modules, kernel independence, no import of the `Org` facade, testing modules, Textual /
  MCP / PyYAML only at the edge) are **generated** by `tests/architecture/gen_importlinter.py` from `tests/architecture/graph.py` (the
  package map, equal to ARCHITECTURE.md 2.2/4.3) and the packages that exist, so a new package brings its
  contracts without editing a config; `python -m tests.architecture.lint` writes `.importlinter` (git-ignored) and runs it. The
  hand-written `[[tool.importlinter.contracts]]` in `pyproject.toml` (the library and `hirearchy.core` do not import the entry points) are run with it.
  A plain `lint-imports` would read only `.importlinter`; use `lint` or `scripts/static_checks.py imports`, which run both.
* *Structural rules (`tests/architecture/`, marker `architecture`):* one test per rule of ARCHITECTURE.md 1.2 (R1 `api`/`__init__`,
  R4 imports match the graph, R6 no module-level singletons and constructors depend on Protocols, R7 Protocols have at most 8 methods, R8 contract suite per Protocol, R9
  single writer per file and per ledger, R13 no "and" in a responsibility), run on the real tree and on `tests/architecture/fixtures/bad_pkg`
  and other seeded violations, which break each rule on purpose: a checker that cannot fail proves nothing. `ownership.py` is the table 2.3 and
  `compat_surface.py` states the permanent compatibility surface (`hirearchy.core`, `hirearchy.progress.progress`, `hirearchy.main`; no flat module besides `core.py`).

**The `Org` facade (`src/hirearchy/app/`).** `hirearchy.core.Org` is assembled in `hirearchy.app` from 20 mixins (`_facade_<pkg>.py`, one per
package it delegates to; the MRO is documented in `app/facade.py`) and `hirearchy.core` re-exports it. Every method is pure delegation to a port of the runtime;
`tests/architecture/test_facade_contract.py` calls all 98 methods against a real runtime and a runtime of spy fakes and checks the delegation by AST.
`app/tests/test_facade_signatures.py` compares the facade with
`tests/architecture/org_signatures.json` (names, kinds, parameters and defaults of all 98 `Org` defs and of `Message`; regenerating it
is a deliberate change of what callers can rely on: `uv run python -m hirearchy.app.tests._signatures --write`), and
`app/tests/test_import_order.py` imports every module in a fresh interpreter in two orders.

**Unit tests (default).** They use a deterministic fake agent (`tests/testkit/fake_agent.py`) in place of kiro, and the autouse fixtures above keep them off your `$HOME`.
A default run starts zero real-LLM runs.

**Integration tests (opt-in).** `tests/integration/test_real_kiro.py` runs tiny orgs (3 tests, one agent run each,
about 45 s and 3 LLM calls in total) against the real `kiro-cli` and your kiro login: that the agent and the scheduler's
run id reach the MCP server's events (`ORG_RUN_ID`), that the built-in `read` reads the org but nothing outside it, and
that the built-in `write` and hirearchy's `org_write` work side by side. They assert on files and events, not on wording.

* Cost: real model calls, billed to your kiro account like any other run. `HIREARCHY_IT_MODEL=<model>` picks a cheaper one
  (default: the system default model, `claude-sonnet-5.5`).
* Skipped (not failed) when `kiro-cli` is not on `PATH`. Each run is killed after 300 s, the scheduler after 480 s.
* Safety (`tests/testkit/kiro_sandbox.py`): the org lives in the test's tmp dir. Before the test the md5 of every file in
  `~/.kiro/agents/` and of `~/.kiro/settings/mcp.json` is taken (hashed only, never read out or printed). After it, pass or
  fail, only the per-org profiles whose `ORG_ROOT` is inside that tmp dir are deleted, every process whose command line
  mentions the tmp dir is killed, and the test fails if any of those md5s changed. No other organization is touched.
* Possible flakiness: model behaviour (a run that does not follow the task fails the test, the run log tail is in the
  assertion message), kiro or network outages, a machine so loaded that a run exceeds its timeout.
