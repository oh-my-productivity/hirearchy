---
name: weekly-meeting-memo
description: One markdown memo of the decisions and action items of one weekly meeting,
  from the notes file for that meeting.
inputs:
- name: notes_file
  description: File name of the meeting notes in the notes folder, for example 2026-10-26.md
  required: true
acceptance:
- Covers only the meeting in the requested notes file, and nothing from other files.
- At most 400 words as counted by read, tables included.
- The memo has a Decisions section, an Action items section and an Open items section.
- Every decision in the notes, including ones agreed only in conversation, is listed
  once, one line each; no decision that is not in the notes appears.
- Action items are a markdown table with the columns exactly Owner | Action | Due,
  and every commitment someone made in the notes is a row, including informal ones
  stated in prose, each with one named owner.
- Every Due value is an ISO date (YYYY-MM-DD) or the word none. A relative or vague
  deadline is converted to an ISO date, using the meeting date in the notes, when
  the notes make that date clear; otherwise Due is none.
- Nothing in the memo is missing from or contradicts the notes file; open items are
  limited to points the notes leave unresolved.
- 'The reviewer''s report shows every criterion met (criteria met: n of m with n =
  m), and the writer applied every required change.'
- The memo starts with a one-line 'Summary:' of the meeting, followed by the Decisions
  section, then the Action items section.
deliverable:
  description: One markdown memo named memo-<meeting date>.md, for example memo-2026-10-19.md
  format: markdown
  max_words: 400
  path: /tmp/hirearchy-e7-s3-1792916437/deliverables
budget: 12
locked: false
version: 2
defined_by: root
defined: '2026-10-25T08:38:00.394947+00:00'
created: '2026-10-25T08:24:32.439986+00:00'
answers: 20261025T083630462812-root-c370
about: C3
words: Yes, add it.
---

