---
name: weekly-meeting-memo
description: One short markdown memo (decisions, and an action table of who does what
  by when) from one weekly meeting note file.
inputs:
- name: notes_file
  description: File name of the meeting notes inside the notes folder, for example
    2026-10-05.md
  required: true
acceptance:
- Uses only the note file named in the request.
- At most 400 words as counted by read.
- The memo is markdown with a section titled Decisions and an action-items table with
  exactly the columns Owner | Action | Due.
- Every decision stated in the note file is in the Decisions section, and no decision
  is added that the notes do not state.
- Every commitment in the note file has one row in the action table, including informal
  ones written in prose and ones that are not labelled as actions. A commitment the
  notes state as uncertain (for example 'will probably') is marked 'tentative' in
  its Action cell.
- Every Due cell is an ISO date (YYYY-MM-DD). A vague deadline (for example 'before
  the freeze' or 'next week') is turned into a date only when the notes and the meeting
  date make that date clear; otherwise the cell is 'none'. No date is guessed.
- 'The reviewer''s report shows every criterion met (criteria met: n of m with n =
  m), and the writer applied every required change.'
- The memo starts with a one-line 'Summary:' of the meeting, then the Decisions section,
  then the action-items table, in that order.
deliverable:
  description: One markdown memo for the requested meeting
  format: markdown
  max_words: 400
  path: /tmp/hirearchy-e5-s2-1792812864/deliverables
budget: 12
locked: false
version: 2
defined_by: root
defined: '2026-10-24T03:50:02.033824+00:00'
created: '2026-10-24T03:37:32.486871+00:00'
answers: 20261024T034910526824-root-ec12
about: C3
words: Yes, add it.
---

