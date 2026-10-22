---
name: weekly-meeting-memo
description: One short memo (decisions and who does what) from one weekly meeting
  notes file
inputs:
- name: notes_file
  description: File name of the meeting notes in the notes folder, for example 2026-10-26.md
  required: true
acceptance:
- Covers only the meeting in the named notes file and nothing else.
- At most 400 words as counted by read.
- The memo has a Decisions section and an Action items table with exactly the columns
  Owner | Action | Due.
- Every decision stated in the notes appears in the Decisions section.
- Every commitment in the notes, including informal ones in prose and ones without
  an ACTION label, is a row in the table with its owner.
- Every Due value is an ISO date (YYYY-MM-DD), converted from a vague deadline only
  when the notes make the date clear, otherwise none.
- Nothing in the memo is missing from or contradicts the notes.
- 'The reviewer''s report shows every criterion met (criteria met: n of m with n =
  m), and the writer applied every required change.'
- The memo starts with a one-line summary of the meeting that begins with 'Summary:'
  (after the title), then the Decisions section, then the Action items table, in that
  order.
- When the notes say a task is for a date (for example 'book the room for Oct 14'),
  that date is the task's Due.
deliverable:
  description: One markdown memo for the meeting
  format: markdown
  max_words: 400
  path: /tmp/hirearchy-e4-s2r-1792702135/deliverables
budget: 15
locked: false
version: 3
defined_by: root
defined: '2026-10-22T21:31:18.234372+00:00'
created: '2026-10-22T20:55:26.192347+00:00'
---

