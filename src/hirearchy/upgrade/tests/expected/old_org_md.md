---
max_depth: 4
max_hops: 40
max_parallel: 3
max_failures: 3
run_timeout: 1800
stall_after: 600
review_every_runs: 25
review_every_seconds: 86400
# my comment
poll_seconds: 0.05
until_done_grace_seconds: 300
default_budget: 10
memory_max_words: 800
playbook_max_words: 1000
default_model: m1
max_message_chars: 20000
events: true
events_keep_days: 30
heartbeat_seconds: 60
---
# Organization

## Mission
Study octopuses.

## Findings so far
They have three hearts.

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
