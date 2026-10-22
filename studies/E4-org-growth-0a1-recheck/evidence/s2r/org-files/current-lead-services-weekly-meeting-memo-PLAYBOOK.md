---
service: weekly-meeting-memo
version: 2
revised: '2026-10-22T21:24:08.889499+00:00'
by: lead
reason: R1 was about C9 (client rejected missing Summary line; criterion link 20261022T212136687899-root-b255
  confirmed it). Add C9 requirement explicitly to writer step and pitfalls.
evidence:
- R1
- C9
admitted: c
---
## Steps
1. Read the request in your prompt: its inputs, every acceptance criterion and the deliverable. The criteria come from the contract and can only be met, never changed; copy the relevant ones verbatim into every task you delegate.
2. Delegate to `writer` (Writer) with `budget=3`: its part of the request, with the criteria it must meet. Explicitly require the writer to:
   - Begin the memo with a one-line `Summary:` of the meeting (after the title, before the Decisions section) — C9. This must be the very first content after the title.
   - Flag any vague deadline as `none` and add an Open questions item for it, rather than converting it to a date.
3. When the work exists, delegate to `reviewer` (Independent Reviewer) with `budget=2` to check the final file independently against every criterion and the regression list (copy it verbatim into the task). It reports findings and required changes to you and never edits the author's file.
4. If a check fails: send the required changes, quoted verbatim, to the AUTHOR of the failing file (`delegate(to=<author>, revises=<that author's task id>, budget=1)`; for the deliverable usually `writer`), then have the checker re-check that same file (`delegate(to=<checker>, revises=<checker's task id>)`). One rework and one re-check; if it still fails, report `blocked` with options and the checker's final line instead of starting another cycle.
5. Read the final artifact yourself and check it against EVERY criterion of the request, quoting counts from your own `read` output, and paste the checker's final coverage line verbatim.
6. Report: `done` only if every criterion is met (else `blocked` with the deviation and a recommended decision). Name the deliverable's path (the assistant copies it to /tmp/hirearchy-e4-s2r-1792702135/deliverables) and pass `lessons`: 1-3 lines for the next request — what worked, what to change in this playbook, and the evidence (runs used, rework, review findings).

## Budget plan
Request budget: 15 runs (the contract's). Hand down no more than this up front, each with `budget=` set explicitly:
- writer: 3 runs (2 work + 1 rework or re-check)
- reviewer: 2 runs (1 work + 1 rework or re-check)
- you (lead): keep 10 runs: your own 6 (plan, process each result, final check, report, one rework cycle) and 4 of slack.
Unspent runs return to your parent with your final report.

## Pitfalls
- C9 / R1: The memo must start with a one-line `Summary:` (after the title, before the Decisions section). The client rejected a memo that omitted it (R1). Require it from the writer explicitly on every request; the reviewer must check it.
- Vague deadlines: Any Due converted to a date without explicit notes support will be flagged. Require the writer to leave vague deadlines as `none` and add an Open questions item, unless the requester confirms a specific date.
