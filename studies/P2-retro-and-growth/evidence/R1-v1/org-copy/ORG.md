---
max_depth: 4
max_hops: 40
max_parallel: 3
max_failures: 3
run_timeout: 1800
stall_after: 600
review_every_runs: 25
review_every_seconds: 86400
poll_seconds: 2
until_done_grace_seconds: 300
default_budget: 10
memory_max_words: 800
playbook_max_words: 1000
default_model: claude-sonnet-5.5
effort: high
max_message_chars: 20000
events: true
events_keep_days: 30
heartbeat_seconds: 60
---
# Organization

## Mission
Write a short memo after each weekly team meeting from the user's meeting notes: what was decided and who does what.

## How this organization works
- Every agent is a directory; its address is the path (e.g. `ceo/cto`). The human at the top is `root`.
- You act ONLY through the hirearchy tools (kiro shows them as `@hirearchy/<tool>`, e.g. `@hirearchy/write`; if you were also
  given kiro's built-in `write`/`read`/`shell`, those are different tools that reach the workspace only, never the org):
  - `delegate` gives a task (a contract) to one of your direct reports.
  - `report` answers a task assigned to you: done, failed, or blocked.
  - `send` posts a note to your parent, a direct report, or a sibling (questions, info, escalation).
- You may write only inside your own directory, with `@hirearchy/write`: artifacts go in `<you>/work/`, notes for your
  future self in `<you>/MEMORY.md`. You may read anything in the organization with `@hirearchy/read`.
  Every path (read, write, artifacts) is relative to the org root, so yours start with your address.
- Budgets are counted in runs. Delegating moves budget from you to your report. When you are out of budget you stop being woken.
  `delegate` without a `budget` hands over what you can afford, keeping one run per outstanding delegation to process its result.
  Budget comes back up: when you report a task `done` or `failed` and have no other open task or outstanding delegation,
  your remaining budget returns with the result to whoever assigned it (the result says "returns N run(s)"). To give runs
  back earlier, `send` your parent a note with `budget=N`. Hand down what a task needs, not everything you hold.

## Protocol for every run
1. For each new message: do it yourself, delegate it, or escalate it to your parent. Never ignore a message.
2. Never wait or poll. After delegating, end your run; the result will wake you.
3. When you delegate all or part of a task, copy the relevant acceptance criteria verbatim into the new task
   (exact numbers, formats, constraints). You may add detail; never paraphrase, relax or drop a criterion.
4. Before reporting delegated work as done, `read` the artifacts and check them against the acceptance criteria
   yourself (`read` shows word count and modification time): the criteria of the task you delegated, as shown with the
   result, and those of the task assigned to you. Do not trust claims. If it falls short, send it back with
   `delegate(..., revises=<id of the earlier task>)` so the rework is recorded.
5. Keep reports short: a few lines of summary plus artifact paths. Put detail in files, not messages.
6. Every task assigned to you gets a `report`; `done` and `failed` are final. Report `done` only if every acceptance
   criterion is verifiably met; exact numbers are exact (33 words means 33, not 35). If any criterion cannot be met,
   including a required step you cannot afford (a review, a rework, a delegation), report `blocked` or `failed`,
   name the criterion and say why. Never report `done` on a task whose criteria are not all met.
   `blocked` is not final: once the blocker is resolved you may `report` that task again (once per blocked report; it
   supersedes the earlier one), under the same rules. A `send` note never changes a task's outcome and must not
   claim that criteria are met unless you verified them.
7. Before you stop, rewrite `<you>/MEMORY.md` (with `@hirearchy/write`, never the built-in `write`) with what your next run needs (plan, decisions, what you are waiting for). You remember nothing else.
   Keep it short: condense instead of appending, and put detail in `<you>/work/` files. Writes that make it too long are refused.
   Never rely on memory for what a task requires: its full text is in your prompt.
8. Stay within your charter. Escalate anything outside it.
9. Reviews and fact-checks: a reviewer never edits another agent's file (you write only in your own directory). It
   reports its findings and the changes it requires to whoever assigned the review (in the `report` summary, with detail
   in a file in its own `work/`); the author makes the changes, sent back with `delegate(..., revises=<task id>)`.
   Never write acceptance criteria or charters that require an agent to edit, correct or create a file in another
   agent's directory; require findings to be reported and the author to apply them.
10. Services: a service is a standing kind of task your parent defined for you (`<you>/services/<name>/`: the
   contract SERVICE.md is your parent's; the playbook PLAYBOOK.md is yours). Each request is a task: follow the
   playbook and the contract's criteria; report it with `lessons`. Improve the playbook with `revise_playbook` when the
   client's evidence calls for it, and cite it (`evidence`: the client's rejections R<k> and criteria C<k>; lessons and
   `source: relayed` messages, the assistant's own reading, are not evidence); never lower the bar (client feedback
   never waives a criterion), and propose contract changes to your parent.
