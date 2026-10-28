---
name: weekly-memo
description: One memo of decisions and action items from one weekly meeting notes
  file
inputs:
- name: notes_file
  description: File name of the meeting notes inside the notes folder, e.g. 2026-10-05.md
  required: true
acceptance:
- At most 400 words as counted by read, table included.
- Every decision in the notes file appears under 'Decisions', including decisions
  stated informally in prose, and no decision that is not in the notes appears.
- Every commitment in the notes file appears as one row of the action items table,
  including commitments made informally in prose (for example 'X said he would ...'),
  and no row is invented.
- The action items are a markdown table with exactly the columns Owner | Action |
  Due, and each row has exactly one owner, named as in the notes.
- Due is an ISO date (YYYY-MM-DD) when the notes give a date or make it clear from
  the meeting date (for example 'by Friday' becomes the date of that Friday); otherwise
  Due is 'none', and 'none' is also used when the notes say no date was set.
- Every statement in the memo is traceable to the named notes file and to no other
  file.
- 'The reviewer''s report shows every criterion met (criteria met: n of m with n =
  m), and the writer applied every required change.'
- When an action is for a dated event, Due is the date of that event (for example,
  a room booked for the training on the 14th has Due 2026-10-14).
- The memo is markdown with a one-line title containing the meeting date, then one
  line starting with 'Summary:' that summarises the meeting in one line, then a section
  titled 'Decisions', then a section titled 'Action items', in that order, and nothing
  else.
deliverable:
  description: One markdown memo named memo-<meeting date>.md
  format: markdown
  max_words: 400
  path: /tmp/hirearchy-p1-F1-1793129193/deliverables
budget: 12
locked: true
version: 4
defined_by: root
defined: '2026-10-27T20:04:08.083060+00:00'
created: '2026-10-27T19:32:21.244683+00:00'
initiated: user
words: always start the memo with a one-line 'Summary:' of the meeting, then the decisions,
  then the action items.
---

