---
id: 20261027T194149830288-runtime-c876
from: runtime
to: lead
type: note
title: contract of service weekly-memo changed to v2
created: '2026-10-27T19:41:49+00:00'
hops: 0
wake: false
---
root changed the contract of service `weekly-memo` (v1 -> v2). Read it, and follow the new criteria from the next request on:
locked: false -> true (you may no longer revise the playbook)
Acceptance criteria now:
C1: The memo is markdown with a one-line title containing the meeting date, then exactly two sections titled 'Decisions' and 'Action items', and nothing else.
C2: At most 400 words as counted by read, table included.
C3: Every decision in the notes file appears under 'Decisions', including decisions stated informally in prose, and no decision that is not in the notes appears.
C4: Every commitment in the notes file appears as one row of the action items table, including commitments made informally in prose (for example 'X said he would ...'), and no row is invented.
C5: The action items are a markdown table with exactly the columns Owner | Action | Due, and each row has exactly one owner, named as in the notes.
C6: Due is an ISO date (YYYY-MM-DD) when the notes give a date or make it clear from the meeting date (for example 'by Friday' becomes the date of that Friday); otherwise Due is 'none', and 'none' is also used when the notes say no date was set.
C7: Every statement in the memo is traceable to the named notes file and to no other file.
C8: The reviewer's report shows every criterion met (criteria met: n of m with n = m), and the writer applied every required change.
Contract: lead/services/weekly-memo/SERVICE.md
