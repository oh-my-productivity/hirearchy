---
name: weekly-meeting-memo
description: One markdown memo (decisions and action-item table) from one weekly meeting
  notes file
inputs:
- name: notes_file
  description: Absolute path of the meeting notes file in the notes folder, e.g. /tmp/hirearchy-p1-F2-1793146944/notes/2026-11-16.md
  required: true
acceptance:
- The memo is markdown and has at most 400 words as counted by read.
- It covers only the meeting in the given notes file.
- A Decisions section lists every decision stated in the notes file, and no statement
  that is not in the file.
- The action items are a markdown table with exactly the columns Owner | Action |
  Due.
- Every commitment in the notes file is a row of that table, including informal ones
  in prose (for example 'said he would ...') and ones marked ACTION.
- Each Due value is an ISO date (YYYY-MM-DD) or 'none'. A relative deadline (for example
  'by Friday') becomes a date only when the notes make the date clear; if no date
  is given the value is 'none'.
- 'The reviewer''s report shows every criterion met (criteria met: n of m with n =
  m), and the writer applied every required change.'
deliverable:
  description: One markdown memo per meeting, named after the notes file with -memo
    (for example 2026-11-09-memo.md)
  format: markdown
  max_words: 400
  path: /tmp/hirearchy-p1-F2-1793146944/deliverables
budget: 12
locked: true
version: 2
defined_by: root
defined: '2026-10-28T00:29:43.549315+00:00'
created: '2026-10-28T00:26:26.527585+00:00'
---

