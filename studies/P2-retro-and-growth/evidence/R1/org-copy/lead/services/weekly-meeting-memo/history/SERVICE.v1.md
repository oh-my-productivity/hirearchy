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
deliverable:
  description: One memo per request, named <meeting-date>-memo.md after the notes
    file (for example 2026-10-05-memo.md).
  format: markdown
  max_words: 400
  path: /private/tmp/hirearchy-p2/R1-1793275867/deliverables
budget: 12
locked: false
version: 1
defined_by: root
defined: '2026-10-29T12:16:30.343437+00:00'
created: '2026-10-29T12:16:30.343437+00:00'
approved_in: plan ed1e802e67ee
sources:
- from: a markdown memo, at most 400 words
  asked: Format and length?
- from: what we decided
  asked: Memo contents?
- from: the action items as a table with columns Owner | Action | Due
  asked: Format and length?
- from: if someone said they'd do something, it counts
  asked: Do informal or unlabelled commitments count?
- from: turn vague deadlines into a date when the notes make it clear
  asked: How to treat relative or vague dates?
- from: 'For the Owner column: Use the words from the notes.'
  asked: How should the Owner column read?
- default: true
- from: 'No separate reviewer: the lead checks.'
  asked: Review by another agent?
elicitation: 'First answer: "Thanks! Yes, if someone said they''d do something, it
  counts. Yes, turn vague deadlines into a date when the notes make it clear. The
  file name each time is fine. Format: a markdown memo, at most 400 words, with the
  action items as a table with columns Owner | Action | Due (ISO dates, ''none'' if
  there''s no date). The rest of your defaults are fine, the deliverables folder too.
  Please keep it cheap, but I need it right - about 12 runs per memo. No separate
  reviewer: the lead checks. No, keep it as it is. For the Owner column: Use the words
  from the notes. No, the first memo should be this week''s: 2026-10-05.md, not 2026-11-09.md."

  Original request: "After each of our weekly team meetings I want a short memo from
  my notes: what we decided and who does what. My notes are in /tmp/hirearchy-p2/R1-1793275867/notes
  (one file per meeting)."'
---

