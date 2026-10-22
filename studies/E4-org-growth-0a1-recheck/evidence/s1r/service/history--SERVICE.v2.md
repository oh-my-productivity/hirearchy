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
- Every statement is traceable to the notes file; where owner or date is unclear or
  missing, the memo says so briefly instead of guessing.
- 'The checker''s report shows every criterion met (criteria met: n of m with n =
  m), and the writer applied every required change.'
- 'The memo''s very first line is a single line starting with "Summary:" that sums
  up the meeting in one sentence; it is followed by the Decisions section, and then
  the action table (in this order: Summary, Decisions, actions). No title heading
  before the Summary line.'
- 'Every Due value is an ISO date (YYYY-MM-DD) or the word none only when the notes
  give no date or deadline at all. A deadline stated relatively ("before Friday",
  "by Thursday", "next week") counts as a date: convert it using the meeting date
  to the ISO date of the day named ("before Friday" or "by Friday" means that Friday
  itself; for the 2026-10-05 meeting, Friday is 2026-10-09). Use none only if the
  notes give no deadline wording at all.'
deliverable:
  description: One markdown memo named memo-<notes file name>, e.g. memo-2026-10-05.md
  format: markdown
  max_words: 400
  path: /private/tmp/hirearchy-e4-s1r-1792693447/deliverables
budget: 15
locked: false
version: 2
defined_by: root
defined: '2026-10-22T18:58:59.927879+00:00'
created: '2026-10-22T18:29:45.407791+00:00'
---

