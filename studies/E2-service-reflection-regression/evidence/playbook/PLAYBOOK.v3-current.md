---
service: meeting-memo
version: 3
revised: '2026-10-18T04:01:47.731192+00:00'
by: lead
reason: 'Contract updated to v2: "before &lt;weekday&gt;" must resolve to the date
  of that weekday in the meeting''s week, and "for &lt;date&gt;" must resolve to that
  date — both as ISO dates, not none. Previous pitfall said the opposite. Case: contract-v2
  note 20261018T040115445402-runtime-788d and task 20261018T040120119761-root-55ff.'
---
## Steps
1. Read the request in your prompt: its inputs, every acceptance criterion and the deliverable. The criteria come from the contract and can only be met, never changed; copy the relevant ones verbatim into every task you delegate.
2. Delegate to `writer` (Writer) with `budget=3`: its part of the request, with the criteria it must meet. On this first run delegate only the steps that need nothing from a teammate.
3. When the work exists, delegate to `reviewer` (Independent Reviewer) with `budget=2` to check the final file independently against every criterion. It reports findings and required changes to you and never edits the author's file.
4. If a check fails: send the required changes, quoted verbatim, to the AUTHOR of the failing file (`delegate(to=<author>, revises=<that author's task id>, budget=1)`; for the deliverable usually `writer`), then have the checker re-check that same file (`delegate(to=<checker>, revises=<the checker's task id>)`). One rework and one re-check; if it still fails, report `blocked` with options and the checker's final line instead of starting another cycle.
5. Read the final artifact yourself and check it against EVERY criterion of the request, quoting counts from your own `read` output, and paste the checker's final coverage line verbatim.
6. Report: `done` only if every criterion is met (else `blocked` with the deviation and a recommended decision). Name the deliverable's path (the assistant copies it to /tmp/orgmcp-e2-1792295253/deliverables) and pass `lessons`: 1-3 lines for the next request - what worked, what to change in this playbook, and the evidence (runs used, rework, review findings).

## Budget plan
Request budget: 15 runs (the contract's). Hand down no more than this up front, each with `budget=` set explicitly:
- writer: 3 runs (2 work + 1 rework or re-check)
- reviewer: 2 runs (1 work + 1 rework or re-check)
- you (lead): keep 10 runs: your own 6 (plan, process each result, final check, report, one rework cycle) and 4 of slack.
Unspent runs return to your parent with your final report.

## Pitfalls
- **Date resolution rules (contract v2):**
  - "before <weekday>" → resolve to the ISO date of that weekday in the meeting's week (e.g. meeting is Monday Oct 12; "before Friday" → Oct 16, i.e. 2026-10-16). Write it as an ISO date; do NOT use `none`.
  - "for <date>" → resolve to that date as an ISO date (e.g. "for Oct 14" → 2026-10-14). Write it as an ISO date; do NOT use `none`.
  - "by <date>" → that date as an ISO date (e.g. "by Oct 14" → 2026-10-14).
  - Only use `none` when the notes give absolutely no date indicator whatsoever for that commitment.
  - Neither "before <weekday>" nor "for <date>" entries belong in Open questions — they have resolved ISO dates.
- **Informal commitments count.** Phrases like "I'll sort it out", "he'll swap shifts", "will probably sort it out himself" are action items. Include them in the Action items table.
- **Summary line is required.** The memo's first content line after the title must be `Summary: <one sentence>`. Then Decisions, then Action items, then Open questions (if any).
- **Open questions only for genuinely unclear items.** An owner or date the notes leave truly unclear belongs in Open questions. A resolved ISO date does not.
