---
name: weekly-memo
description: One short memo (decisions and action items) from one meeting's notes
  file
inputs:
- name: notes_file
  description: File name of the meeting notes in the notes folder, for example 2026-10-19.md
  required: true
acceptance:
- The memo is markdown and has at most 400 words as counted by read.
- It covers only the meeting in the given notes file.
- It has a Decisions section that lists every decision recorded in the notes file
  and no decision that is not in the notes.
- It has an action-items table with exactly the columns Owner | Action | Due, with
  one row for every commitment in the notes, including informal ones where a person
  said in prose that they would do something, and no row that is not in the notes.
- Every Due value is an ISO date (YYYY-MM-DD) or none. A relative deadline (for example
  next week, next meeting) becomes a date only when the notes make the date clear;
  otherwise Due is none. No date is guessed.
- Every owner name matches the person named in the notes.
- 'The reviewer''s report shows every criterion met (criteria met: n of m with n =
  m), and the writer applied every required change.'
- The memo starts with a one-line summary of the meeting that begins with 'Summary:',
  followed by the Decisions section, followed by the action-items table, in that order.
deliverable:
  description: One markdown memo named memo-<meeting date>.md
  format: markdown
  max_words: 400
  path: /tmp/hirearchy-e4-s3-1792705005/deliverables
budget: 15
locked: false
version: 2
defined_by: root
defined: '2026-10-22T21:58:34.263247+00:00'
created: '2026-10-22T21:40:54.842744+00:00'
---

