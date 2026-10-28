---
service: weekly-meeting-memo
version: 3
revised: '2026-10-27T22:00:49.926438+00:00'
by: lead
reason: Client confirmed C13 (R2).
evidence:
- C13
admitted: c
item: P12
items_max: 12
rules: []
why:
  P11:
  - R1
  - C12
  P12:
  - R2
  - C13
op: add
---
## Steps
1. [P1] Read the request in your prompt: its inputs, every acceptance criterion and the deliverable. The criteria come from the contract and can only be met, never changed; copy the relevant ones verbatim into every task you delegate.
2. [P2] Delegate to `writer` (Writer) with `budget=3`: its part of the request, with the criteria it must meet.
3. [P11] The first line of the memo is one line starting "Summary:" that summarises the meeting, in the team's own words and using only facts from the notes (this is the one exception to "use the words of the notes"). After it come "Decisions", then "Actions". The meeting date, the people present and the next meeting date go after the Actions table. (WHY R1; C12)
4. [P12] In the Actions table, the Owner column holds the owner's initials only (the first letter of the first name, for example P for Priya; if two people share a letter, the first two letters for both), and names stay as they are everywhere else in the memo (the Present line and the action text). (WHY R2; C13)
5. [P3] When the work exists, delegate to `reviewer` (Independent Reviewer) with `budget=2` to check the final file independently against every criterion. It reports findings and required changes to you and never edits the author's file.
6. [P4] If a check fails: send the required changes, quoted verbatim, to the AUTHOR of the failing file (`delegate(to=<author>, revises=<that author's task id>, budget=1)`; for the deliverable usually `writer`), then have the checker re-check that same file (`delegate(to=<checker>, revises=<the checker's task id>)`). One rework and one re-check; if it still fails, report `blocked` with options and the checker's final line instead of starting another cycle.
7. [P5] Read the final artifact yourself and check it against EVERY criterion of the request, quoting counts from your own `read` output, and paste the checker's final coverage line verbatim.
8. [P6] Report: `done` only if every criterion is met (else `blocked` with the deviation and a recommended decision). Name the deliverable's path (the assistant copies it to /tmp/hirearchy-p1-I1-1793136275/deliverables) and pass `lessons` as an after-action review: Expected / Happened / Caught at / Cause / Prevent (the system cause, not a person), or Near miss when nothing went wrong.

## Budget plan
- [P7] Request budget: 12 runs (the contract's). Hand down no more than this up front, each with `budget=` set explicitly:
- [P8] writer: 3 runs (2 work + 1 rework or re-check)
- [P9] reviewer: 2 runs (1 work + 1 rework or re-check)
- [P10] you (lead): keep 7 runs: your own 6 (plan, process each result, final check, report, one rework cycle) and 1 of slack.
   Unspent runs return to your parent with your final report.
