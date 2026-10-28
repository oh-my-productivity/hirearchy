---
id: 20261028T020955701882-runtime-1063
from: runtime
to: lead
type: note
title: contract of service weekly-meeting-memo changed to v2
created: '2026-10-28T02:09:55+00:00'
hops: 0
wake: false
---
root changed the contract of service `weekly-meeting-memo` (v1 -> v2). Read it, and follow the new criteria from the next request on:
locked: false -> true (you may no longer revise the playbook)
Acceptance criteria now:
C1: The memo covers only the meeting in the named notes file.
C2: The memo is markdown and has at most 400 words as counted by read.
C3: The memo has a Decisions section listing every decision recorded in the notes file, one line each.
C4: The memo has the action items as a markdown table with exactly the columns Owner | Action | Due.
C5: The table contains every commitment in the notes file, including informal ones stated in prose (for example 'X said they would do Y'), whether or not it is labelled ACTION.
C6: Every Due value is an ISO date (YYYY-MM-DD) or the word none. A vague deadline (for example 'by Friday') becomes a date, worked out from the meeting date, when the notes make it clear; if no date is given, Due is none.
C7: Every decision and action item is stated in the named notes file; nothing is invented.
C8: The reviewer's report shows every criterion met (criteria met: n of m with n = m), and the writer applied every required change.
Contract: lead/services/weekly-meeting-memo/SERVICE.md
