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
deliverable:
  description: One markdown memo per meeting, named memo-<notes file date>.md
  format: markdown
  max_words: 400
  path: /private/tmp/hirearchy-p2/R1-1793270268/deliverables
budget: 12
locked: false
version: 1
defined_by: root
defined: '2026-10-29T10:42:27.028618+00:00'
created: '2026-10-29T10:42:27.028618+00:00'
approved_in: plan 23d677cd0174
sources:
- from: what we decided and who does what
  asked: What should the memo cover?
- from: at most 400 words
  asked: Format and length?
- default: true
- from: if someone said they'd do something, it counts
  asked: Do informal or unlabelled commitments count?
- from: the action items as a table with columns Owner | Action | Due
  asked: Format and length?
- from: 'For the Owner column: Use the words from the notes'
  asked: Owner column wording?
- from: turn vague deadlines into a date when the notes make it clear
  asked: How to treat relative or vague dates?
- from: 'No separate reviewer: the lead checks'
  asked: Review by another agent?
elicitation: 'User, first message: After each of our weekly team meetings I want a
  short memo from my notes: what we decided and who does what. My notes are in /tmp/hirearchy-p2/R1-1793270268/notes
  (one file per meeting). Can you set up a team that does this for me every week?

  User, answers: Yes, if someone said they''d do something, it counts. Yes, turn vague
  deadlines into a date when the notes make it clear. The file name each time is fine.
  Format: a markdown memo, at most 400 words, with the action items as a table with
  columns Owner | Action | Due (ISO dates, ''none'' if there''s no date). The rest
  of your defaults are fine, the deliverables folder too. Please keep it cheap, but
  I need it right - about 12 runs per memo. No separate reviewer: the lead checks.
  For the Owner column: Use the words from the notes. No, the first memo should be
  this week''s: 2026-10-05.md, not 2026-11-09.md.'
---

