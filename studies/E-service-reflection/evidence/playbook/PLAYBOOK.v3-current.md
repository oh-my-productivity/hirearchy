---
service: weekly-memo
version: 3
revised: '2026-10-18T02:43:32.749556+00:00'
by: lead
reason: 'v3 contract (case 20261018T022344643603) added implicit-commitments criterion;
  rework in that case traced to missing Sam/Lee implicit items. Added: lead pre-reads
  notes and passes commitment list to writer; explicit instructions to both writer
  and reviewer to find all implicit commitments in the full file.'
---
## Steps
1. Read the request in your prompt: its inputs, every acceptance criterion and the deliverable. The criteria come from the contract and can only be met, never changed; copy the relevant ones verbatim into every task you delegate.
2. Read the notes file yourself (kiro `read` by absolute path) before delegating. Identify all explicit AND implicit commitments (any agreement by someone to do something, with or without a label). Pass this analysis inline to the writer so nothing is missed.
3. Delegate to `writer` (Memo writer) with `budget=3`: its part of the request, with ALL acceptance criteria verbatim. Explicitly tell the writer: (a) implicit commitments buried in paragraphs count as action items — they must read the whole notes file for these; (b) "Decisions" section comes before "Action items" section; (c) relative dates must be converted to ISO (YYYY-MM-DD) using the meeting date in the file name.
4. When the work exists, delegate to `reviewer` (Independent Reviewer) with `budget=2` to check the final file independently against every criterion. Pass the memo text inline to the reviewer (as the reviewer cannot read the writer's folder directly). Explicitly tell the reviewer: (a) they must re-read the whole notes file to find every implicit commitment (any agreement by someone to do something, with or without a label) and confirm each has a row; (b) they must report "criteria met: n of m" where n must equal m for acceptance.
5. If a check fails: send the required changes, quoted verbatim, to the AUTHOR of the failing file (`delegate(to=<author>, revises=<that author's task id>, budget=1)`; for the deliverable usually `writer`), then have the checker re-check that same file (`delegate(to=<checker>, revises=<the checker's task id>)`). One rework and one re-check; if it still fails, report `blocked` with options and the checker's final line instead of starting another cycle.
6. Read the final artifact yourself and check it against EVERY criterion of the request, quoting counts from your own `read` output, and paste the checker's final coverage line verbatim.
7. Report: `done` only if every criterion is met (else `blocked` with the deviation and a recommended decision). Name the deliverable's path (the assistant copies it to /tmp/orgmcp-e-1792289694/deliverables) and pass `lessons`: 1-3 lines for the next request - what worked, what to change in this playbook, and the evidence (runs used, rework, review findings).

## Budget plan
Request budget: 12 runs (the contract's). Hand down no more than this up front, each with `budget=` set explicitly:
- writer: 3 runs (2 work + 1 rework)
- reviewer: 2 runs (1 work + 1 re-check)
- you (lead): keep 7 runs: your own 6 (plan, process each result, final check, report, one rework cycle) and 1 of slack.
Unspent runs return to your parent with your final report.

## Pitfalls
- Reviewer cannot read the writer's work folder (lead/writer/work/) via kiro read. Always pass the memo text inline to the reviewer task — do not rely on the reviewer reading the file path directly.
- The deliverable path in the contract (/tmp/orgmcp-e-1792289694/deliverables) is unreachable by @orgmcp/write; put the deliverable in lead/work/ and report that path. The assistant copies it.
- The "Decisions" section must always come before the "Action items" section (standing client requirement, contract v2+). Always state this explicitly in the writer's task.
- Relative dates in the notes must be converted to ISO format (YYYY-MM-DD) using the meeting date in the file name.
- Implicit commitments (contract v3): any agreement by someone to do something counts as an action item even if not labelled ACTION. Pre-read the notes yourself and pass the full list of commitments found to the writer. Instruct the reviewer to re-read the whole notes file and confirm every implicit commitment has a row.
