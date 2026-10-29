---
name: weekly-meeting-memo
description: One markdown memo with the decisions and the action-item table from one
  weekly meeting-notes file.
inputs:
- name: notes_file
  description: File name of the meeting notes in the notes folder, e.g. 2026-10-05.md
  required: true
acceptance:
- The memo covers only the decisions and the action items of the requested notes file,
  with a Decisions section and an Actions section.
- The memo is at most 400 words as counted by read.
- Every decision in the notes file is listed in the Decisions section, and nothing
  is listed there that the notes do not state as decided or agreed.
- Every commitment in the notes file is a row in the Actions table, including informal
  ones in prose (for example 'Sam said he'd look into ...'), and no row is an invented
  commitment.
- The Actions section is a table with exactly the columns Owner | Action | Due.
- The Owner cell uses the words the notes use for that person or group.
- The Due cell is an ISO date (YYYY-MM-DD). A vague deadline (for example 'before
  Friday') is turned into a date, using the meeting date in the notes, only when the
  notes make that date clear; otherwise the cell is 'none'.
- The lead's check report matches every decision and every action row of the memo
  against the notes file (n of m, n = m), and every commitment in the notes file has
  a row.
- Every memo starts with a one-line 'Summary:' of the meeting, then the Decisions,
  then the Actions; the Summary line is the one thing allowed besides decisions and
  actions.
deliverable:
  description: One markdown memo per meeting, named memo-<notes file date>.md
  format: markdown
  max_words: 400
  path: /private/tmp/hirearchy-p2/R1-1793270268/deliverables
budget: 12
locked: false
version: 2
defined_by: root
defined: '2026-10-29T10:53:41.278670+00:00'
created: '2026-10-29T10:42:27.028618+00:00'
answers: 20261029T105129733247-root-9230
about: C1
words: Yes, add it.
---

