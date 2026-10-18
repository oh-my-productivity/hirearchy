---
service: weekly-memo
version: 2
revised: '2026-10-18T02:24:09.070806+00:00'
by: lead
reason: 'case 20261018T022310913851-root-f538: client feedback "Wants decisions always
  before action items" and contract v2 now requires it. Also codifying the known workaround
  for reviewer file access and the deliverable path constraint from prior case lessons.'
---
## Steps
1. Read the request in your prompt: its inputs, every acceptance criterion and the deliverable. The criteria come from the contract and can only be met, never changed; copy the relevant ones verbatim into every task you delegate.
2. Delegate to `writer` (Memo writer) with `budget=3`: its part of the request, with the criteria it must meet. On this first run delegate only the steps that need nothing from a teammate. Remind the writer that the "Decisions" section MUST come before the "Action items" section.
3. When the work exists, delegate to `reviewer` (Independent Reviewer) with `budget=2` to check the final file independently against every criterion. Pass the memo text inline to the reviewer (as the reviewer cannot read the writer's folder directly). It reports findings and required changes to you and never edits the author's file.
4. If a check fails: send the required changes, quoted verbatim, to the AUTHOR of the failing file (`delegate(to=<author>, revises=<that author's task id>, budget=1)`; for the deliverable usually `writer`), then have the checker re-check that same file (`delegate(to=<checker>, revises=<the checker's task id>)`). One rework and one re-check; if it still fails, report `blocked` with options and the checker's final line instead of starting another cycle.
5. Read the final artifact yourself and check it against EVERY criterion of the request, quoting counts from your own `read` output, and paste the checker's final coverage line verbatim.
6. Report: `done` only if every criterion is met (else `blocked` with the deviation and a recommended decision). Name the deliverable's path (the assistant copies it to /tmp/orgmcp-e-1792289694/deliverables) and pass `lessons`: 1-3 lines for the next request - what worked, what to change in this playbook, and the evidence (runs used, rework, review findings).

## Budget plan
Request budget: 12 runs (the contract's). Hand down no more than this up front, each with `budget=` set explicitly:
- writer: 3 runs (2 work + 1 rework or re-check)
- reviewer: 2 runs (1 work + 1 rework or re-check)
- you (lead): keep 7 runs: your own 6 (plan, process each result, final check, report, one rework cycle) and 1 of slack.
Unspent runs return to your parent with your final report.

## Pitfalls
- Reviewer cannot read the writer's work folder (lead/writer/work/) via kiro read. Always pass the memo text inline to the reviewer task — do not rely on the reviewer reading the file path directly.
- The deliverable path in the contract (/tmp/orgmcp-e-1792289694/deliverables) is unreachable by @orgmcp/write; put the deliverable in lead/work/ and report that path. The assistant copies it.
- The "Decisions" section must always come before the "Action items" section (standing client requirement, contract v2). Always state this explicitly in the writer's task.
- Relative dates in the notes must be converted to ISO format (YYYY-MM-DD) using the meeting date in the file name.
