---
service: weekly-meeting-memo
version: 1
revised: '2026-10-29T10:42:27.030452+00:00'
by: root
reason: initial playbook
items_max: 7
rules: []
why: {}
op: first
---
## Steps
1. [P1] Read the request in your prompt: its inputs, every acceptance criterion and the deliverable. The criteria come from the contract and can only be met, never changed; copy the relevant ones verbatim into every task you delegate.
2. [P2] Delegate to `writer` (Writer) with `budget=3`: its part of the request, with the criteria it must meet.
3. [P3] Read the final artifact yourself and check it against EVERY criterion of the request, quoting counts from your own `read` output.
4. [P4] Report: `done` only if every criterion is met (else `blocked` with the deviation and a recommended decision). Name the deliverable's path (the assistant copies it to /private/tmp/hirearchy-p2/R1-1793270268/deliverables) and pass `lessons` as an after-action review: Expected / Happened / Caught at / Cause / Prevent (the system cause, not a person), or Near miss when nothing went wrong.

## Budget plan
- [P5] Request budget: 12 runs (the contract's). Hand down no more than this up front, each with `budget=` set explicitly:
- [P6] writer: 3 runs (2 work + 1 rework or re-check)
- [P7] you (lead): keep 9 runs: your own 5 (plan, process each result, final check, report, one rework cycle) and 4 of slack.
   Unspent runs return to your parent with your final report.
