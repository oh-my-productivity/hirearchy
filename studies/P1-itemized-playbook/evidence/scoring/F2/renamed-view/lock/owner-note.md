---
id: 20261028T002943553558-runtime-b78b
from: runtime
to: lead
type: note
title: contract of service weekly-meeting-memo changed to v2
created: '2026-10-28T00:29:43+00:00'
hops: 0
wake: false
---
root changed the contract of service `weekly-meeting-memo` (v1 -> v2). Read it, and follow the new criteria from the next request on:
locked: false -> true (you may no longer revise the playbook)
Acceptance criteria now:
C1: The memo is markdown and has at most 400 words as counted by read.
C2: It covers only the meeting in the given notes file.
C3: A Decisions section lists every decision stated in the notes file, and no statement that is not in the file.
C4: The action items are a markdown table with exactly the columns Owner | Action | Due.
C5: Every commitment in the notes file is a row of that table, including informal ones in prose (for example 'said he would ...') and ones marked ACTION.
C6: Each Due value is an ISO date (YYYY-MM-DD) or 'none'. A relative deadline (for example 'by Friday') becomes a date only when the notes make the date clear; if no date is given the value is 'none'.
C7: The reviewer's report shows every criterion met (criteria met: n of m with n = m), and the writer applied every required change.
Contract: lead/services/weekly-meeting-memo/SERVICE.md
