---
service: weekly-memo
version: 2
revised: '2026-10-22T19:03:16.509889+00:00'
by: lead
reason: 'C9 confirmed by client (R1, case 20261022T182945409755-root-ed94): ''before
  Friday'' = Friday itself. Adds C9 date-conversion pitfall and C8 structure reminder
  to prevent the same errors on future requests.'
evidence:
- C9
- R1
- 20261022T182945409755-root-ed94
admitted: c
---
## Steps
1. Read the request in your prompt: its inputs, every acceptance criterion and the deliverable. The criteria come from the contract and can only be met, never changed; copy the relevant ones verbatim into every task you delegate.
2. Delegate to `reader` (Reader of the meeting notes) with `budget=3`: its part of the request, with the criteria it must meet.
3. When the previous result is in, read its artifact yourself, then delegate to `writer` (Writer) with `budget=3`, naming the artifact it builds on. Never delegate a step before its inputs exist, and send no status messages: results wake you.
4. When the work exists, delegate to `checker` (Independent Reviewer) with `budget=2` to check the final file independently against every criterion. It reports findings and required changes to you and never edits the author's file.
5. If a check fails: send the required changes, quoted verbatim, to the AUTHOR of the failing file (`delegate(to=<author>, revises=<that author's task id>, budget=1)`; for the deliverable usually `writer`), then have the checker re-check that same file (`delegate(to=<checker>, revises=<the checker's task id>)`). One rework and one re-check; if it still fails, report `blocked` with options and the checker's final line instead of starting another cycle.
6. Read the final artifact yourself and check it against EVERY criterion of the request, quoting counts from your own `read` output, and paste the checker's final coverage line verbatim.
7. Report: `done` only if every criterion is met (else `blocked` with the deviation and a recommended decision). Name the deliverable's path (the assistant copies it to /private/tmp/hirearchy-e4-s1r-1792693447/deliverables) and pass `lessons`: 1-3 lines for the next request - what worked, what to change in this playbook, and the evidence (runs used, rework, review findings).

## Budget plan
Request budget: 15 runs (the contract's). Hand down no more than this up front, each with `budget=` set explicitly:
- reader: 3 runs (2 work + 1 rework or re-check)
- writer: 3 runs (2 work + 1 rework or re-check)
- checker: 2 runs (1 work + 1 rework or re-check)
- you (lead): keep 7 runs: your own 7 (plan, process each result, final check, report, one rework cycle).
Unspent runs return to your parent with your final report.

## Pitfalls
- **C9 – Relative deadlines**: "before Friday", "by Thursday", "next week" and similar wording ARE dates (C9); convert using the meeting date. "before/by [weekday]" means that weekday's ISO date (e.g. "before Friday" for a Mon 5 Oct meeting = 2026-10-09, NOT the day before Friday). Use `none` only when the notes contain no deadline wording at all.
- **C8 – Structure**: The memo's very first line must be a single `Summary:` line (one sentence). No title heading before it. Order: Summary line, then `## Decisions`, then the action table.
- **Calendar arithmetic**: Writer must verify any weekday-to-date conversion explicitly (weekday name → ISO date → double-check day of week) before writing it. Off-by-one date errors in explanatory prose have caused rework.
