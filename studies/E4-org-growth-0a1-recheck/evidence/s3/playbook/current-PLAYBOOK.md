---
service: weekly-memo
version: 2
revised: '2026-10-22T22:01:00.630898+00:00'
by: lead
reason: Add C8 (Summary line) to writer instructions and pitfalls after client rejection
  R1 and contract amendment confirming C8; clarify C5 date resolution. Case 20261022T214057425390-root-88b2.
evidence:
- C8
- R1
- 20261022T214057425390-root-88b2
admitted: c
---
## Steps
1. Read the request in your prompt: its inputs, every acceptance criterion and the deliverable. The criteria come from the contract and can only be met, never changed; copy the relevant ones verbatim into every task you delegate.
2. Delegate to `writer` (Writer) with `budget=3`: its part of the request, with the criteria it must meet. Explicitly instruct the writer to structure the memo in this exact order: (a) one line starting with 'Summary:' that summarises the meeting in a single line, using only information from the notes file; (b) the Decisions section; (c) the action-items table with columns Owner | Action | Due; (d) a 'Next meeting' footer if stated in the notes. No other sections (e.g. no Open questions section unless a criterion requires it).
3. When the work exists, delegate to `reviewer` (Independent Reviewer) with `budget=2` to check the final file independently against every criterion (C1–C8) and the regression list verbatim. It reports findings and required changes to you and never edits the author's file.
4. If a check fails: send the required changes, quoted verbatim, to the AUTHOR of the failing file (`delegate(to=<author>, revises=<that author's task id>, budget=1)`; for the deliverable usually `writer`), then have the checker re-check that same file (`delegate(to=<checker>, revises=<checker's task id>)`). One rework and one re-check; if it still fails, report `blocked` with options and the checker's final line instead of starting another cycle.
5. Read the final artifact yourself and check it against EVERY criterion of the request, quoting counts from your own `read` output, and paste the checker's final coverage line verbatim.
6. Report: `done` only if every criterion is met (else `blocked` with the deviation and a recommended decision). Name the deliverable's path (the assistant copies it to /tmp/hirearchy-e4-s3-1792705005/deliverables) and pass `lessons`: 1-3 lines for the next request — what worked, what to change in this playbook, and the evidence (runs used, rework, review findings).

## Budget plan
Request budget: 15 runs (the contract's). Hand down no more than this up front, each with `budget=` set explicitly:
- writer: 3 runs (2 work + 1 rework or re-check)
- reviewer: 2 runs (1 work + 1 rework or re-check)
- you (lead): keep 10 runs: your own 6 (plan, process each result, final check, report, one rework cycle) and 4 of slack.
Unspent runs return to your parent with your final report.

## Pitfalls
- C8 (Summary line first): The memo MUST start with a single line beginning with 'Summary:' before any other section, followed immediately by Decisions, then the action-items table. Omitting it or placing it elsewhere fails C8. Instruct the writer explicitly in every delegation.
- Date resolution (C5): A relative deadline becomes an ISO date only when the notes make the reference date calculable (e.g. 'before Friday' in a meeting explicitly dated Monday Oct 5 resolves to Oct 9 of that week). Do not default all relative dates to 'none'; resolve them when the notes supply the anchor. Do not invent a date that is not calculable from the notes.
