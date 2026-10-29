---
name: weekly-meeting-memo
description: One markdown memo with the decisions and the action items table for one
  meeting notes file.
inputs:
- name: notes_file
  description: File name of the meeting notes in the notes folder, for example 2026-10-05.md
  required: true
acceptance:
- The memo is markdown and has at most 400 words as counted by read.
- The memo has a Decisions section listing every decision made in the named notes
  file, and nothing from other files.
- The action items are a markdown table with exactly the columns Owner | Action |
  Due.
- Every commitment in the notes is a row of the table, both those labelled ACTION
  and those stated in prose, such as someone saying they would do something.
- Each Due value is an ISO date (YYYY-MM-DD). A relative deadline such as 'by Friday'
  is turned into a date only when the notes make the date clear; if the notes give
  no date, Due is 'none'.
- Each Owner value uses the name exactly as written in the notes.
- Every statement in the memo is traceable to the notes file, and anything unclear
  (no owner, an unconfirmed decision) is listed under a final heading 'Unclear' instead
  of being guessed.
- The lead's check report states that every decision and every table row was compared
  with the notes file, with the count verified (n of m, n = m).
- A statement that something stays as it is, where nobody has to do anything, is not
  an action item and gets no row in the table.
- The memo starts with a one-line 'Summary:' of the meeting, followed by the action
  items table, then the Decisions section.
deliverable:
  description: One memo per request, named <meeting-date>-memo.md after the notes
    file (for example 2026-10-05-memo.md).
  format: markdown
  max_words: 400
  path: /private/tmp/hirearchy-p2/R1-1793275867/deliverables
budget: 12
locked: false
version: 4
defined_by: root
defined: '2026-10-29T13:12:32.972313+00:00'
created: '2026-10-29T12:16:30.343437+00:00'
answers: 20261029T131124958232-root-b7f2
about: C9
words: Yes, add it.
---

