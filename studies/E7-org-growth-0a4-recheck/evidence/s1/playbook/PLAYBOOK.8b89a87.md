---
service: weekly-meeting-memo
version: 2
revised: '2026-10-25T07:17:58.506636+00:00'
by: lead
reason: Client confirmed C9 (link note 20261025T071714388062-root-6096) after rejecting
  case 20261025T070423629042-root-5efc (R1). Adds C9's words only.
evidence:
- C9
- R1
- 20261025T071714388062-root-6096
admitted: c
---
## Steps
1. Read the request in your prompt: its inputs, every acceptance criterion and the deliverable. The criteria come from the contract and can only be met, never changed; copy the relevant ones verbatim into every task you delegate.
2. Delegate to `writer` (Writer) with `budget=3`: its part of the request, with the criteria it must meet.
3. When the work exists, delegate to `reviewer` (Independent Reviewer) with `budget=2` to check the final file independently against every criterion. It reports findings and required changes to you and never edits the author's file.
4. If a check fails: send the required changes, quoted verbatim, to the AUTHOR of the failing file (`delegate(to=<author>, revises=<that author's task id>, budget=1)`; for the deliverable usually `writer`), then have the checker re-check that same file (`delegate(to=<checker>, revises=<the checker's task id>)`). One rework and one re-check; if it still fails, report `blocked` with options and the checker's final line instead of starting another cycle.
5. Read the final artifact yourself and check it against EVERY criterion of the request, quoting counts from your own `read` output, and paste the checker's final coverage line verbatim.
6. Report: `done` only if every criterion is met (else `blocked` with the deviation and a recommended decision). Name the deliverable's path (the assistant copies it to /tmp/hirearchy-e7-s1-1792911600/deliverables) and pass `lessons`: 1-3 lines for the next request - what worked, what to change in this playbook, and the evidence (runs used, rework, review findings).

## Budget plan
Request budget: 12 runs (the contract's). Hand down no more than this up front, each with `budget=` set explicitly:
- writer: 3 runs (2 work + 1 rework or re-check)
- reviewer: 2 runs (1 work + 1 rework or re-check)
- you (lead): keep 7 runs: your own 6 (plan, process each result, final check, report, one rework cycle) and 1 of slack.
Unspent runs return to your parent with your final report.

## Pitfalls
none yet: add them from lessons and feedback
- C9: The memo has a title line with the meeting date, then a one-line 'Summary:' of the meeting, then a Decisions section, then an Actions section, and nothing else (no attendee list, no discussion recap).
