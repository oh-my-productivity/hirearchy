---
name: weekly-memo
description: One short memo (decisions, and a table of who does what) from one meeting's
  notes file
inputs:
- name: notes_file
  description: File name of the meeting notes inside the notes folder, e.g. 2026-10-05.md
  required: true
acceptance:
- Uses only the requested notes file and covers that meeting only.
- At most 400 words as counted by read.
- Has a Decisions section listing every decision made in the meeting, each in one
  line.
- Has an action table with exactly the columns Owner | Action | Due, with one row
  for every task that someone was given or said they would do (explicit ACTION lines
  and informal commitments), and no row for anything else.
- Every Due value is an ISO date (YYYY-MM-DD) or the word none when the notes give
  no date; a date stated only relatively (for example a weekday) is converted using
  the meeting date, and if it cannot be determined the value is none.
- Every statement is traceable to the notes file; where owner or date is unclear or
  missing, the memo says so briefly instead of guessing.
- 'The checker''s report shows every criterion met (criteria met: n of m with n =
  m), and the writer applied every required change.'
deliverable:
  description: One markdown memo named memo-<notes file name>, e.g. memo-2026-10-05.md
  format: markdown
  max_words: 400
  path: /private/tmp/hirearchy-e4-s1r-1792693447/deliverables
budget: 15
locked: false
version: 1
defined_by: root
defined: '2026-10-22T18:29:45.407791+00:00'
created: '2026-10-22T18:29:45.407791+00:00'
---

