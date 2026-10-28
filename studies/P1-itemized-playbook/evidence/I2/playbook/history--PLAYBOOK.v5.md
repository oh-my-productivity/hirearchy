---
service: weekly-meeting-memo
version: 5
revised: '2026-10-27T23:58:44.602325+00:00'
by: lead
reason: Own words of C10, added by the contract amendment the client confirmed (yes
  to R3).
evidence:
- C10
- R3
admitted: c
item: P13
items_max: 13
rules: []
why:
  P11:
  - R1
  - C8
  P13:
  - R3
  - C10
op: add
---
## Steps
1. [P1] Read the request in your prompt: its inputs, every acceptance criterion and the deliverable. The criteria come from the contract and can only be met, never changed; copy the relevant ones verbatim into every task you delegate.
2. [P2] Delegate to `writer` (Writer) with `budget=3`: its part of the request, with the criteria it must meet.
3. [P11] The memo has a one-line 'Summary:' of the meeting directly after the title, then the Decisions section, then the Actions section; the Summary line is the only addition to what the "Decisions"/"Actions" criterion allows. (WHY R1; C8)
4. [P13] Owners are shown as full names, always: in the Actions table the Owner column holds the owner's full name as written in the notes, never initials. (WHY R3; C10)
5. [P3] When the work exists, delegate to `reviewer` (Independent Reviewer) with `budget=2` to check the final file independently against every criterion. It reports findings and required changes to you and never edits the author's file.
6. [P4] If a check fails: send the required changes, quoted verbatim, to the AUTHOR of the failing file (`delegate(to=<author>, revises=<that author's task id>, budget=1)`; for the deliverable usually `writer`), then have the checker re-check that same file (`delegate(to=<checker>, revises=<the checker's task id>)`). One rework and one re-check; if it still fails, report `blocked` with options and the checker's final line instead of starting another cycle.
7. [P5] Read the final artifact yourself and check it against EVERY criterion of the request, quoting counts from your own `read` output, and paste the checker's final coverage line verbatim.
8. [P6] Report: `done` only if every criterion is met (else `blocked` with the deviation and a recommended decision). Name the deliverable's path (the assistant copies it to /tmp/hirearchy-p1-I2-1793142034/deliverables) and pass `lessons` as an after-action review: Expected / Happened / Caught at / Cause / Prevent (the system cause, not a person), or Near miss when nothing went wrong.

## Budget plan
- [P7] Request budget: 12 runs (the contract's). Hand down no more than this up front, each with `budget=` set explicitly:
- [P8] writer: 3 runs (2 work + 1 rework or re-check)
- [P9] reviewer: 2 runs (1 work + 1 rework or re-check)
- [P10] you (lead): keep 7 runs: your own 6 (plan, process each result, final check, report, one rework cycle) and 1 of slack.
   Unspent runs return to your parent with your final report.
