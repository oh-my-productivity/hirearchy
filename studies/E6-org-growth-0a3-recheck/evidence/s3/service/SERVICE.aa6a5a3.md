---
name: weekly-memo
description: One short markdown memo (decisions and action-item table) from one meeting
  notes file
inputs:
- name: notes_file
  description: File name of the meeting notes in the notes folder, for example 2026-10-05.md
  required: true
acceptance:
- Covers only the meeting in the named notes file, and nothing from other files.
- At most 400 words as counted by read.
- Has a section titled "Decisions" that lists every firm decision made in the meeting;
  items that were discussed but left open are not listed as decisions.
- Has a section titled "Action items" that is a markdown table with exactly the columns
  Owner | Action | Due.
- The table has one row for every commitment in the notes, including informal ones
  stated in prose (for example "X offered to ..." or "X said he would ...") and those
  labelled ACTION.
- Every Due value is an ISO date (YYYY-MM-DD) or the word none. A vague or relative
  deadline (for example "next week", "by Friday") is turned into a date when the notes
  make it clear, otherwise it is none.
- Every decision and every table row is traceable to the notes file, and nothing is
  invented.
- 'The reviewer''s report shows every criterion met (criteria met: n of m with n =
  m), and the writer applied every required change.'
deliverable:
  description: One markdown memo for the requested meeting
  format: markdown
  max_words: 400
  path: /tmp/hirearchy-e6-s3-1792861552/deliverables
budget: 16
locked: false
version: 1
defined_by: root
defined: '2026-10-24T17:09:57.356205+00:00'
created: '2026-10-24T17:09:57.356205+00:00'
---

