---
name: weekly-meeting-memo
description: One short markdown memo of the decisions and action items from one weekly
  meeting's notes file.
inputs:
- name: notes_file
  description: The notes file for the meeting, inside the notes folder (for example
    2026-10-19.md)
  required: true
acceptance:
- Built only from the named notes file.
- At most 400 words as counted by read.
- A markdown memo with a Decisions section that lists every decision in the notes,
  including ones stated in prose without a label.
- An action items section that is a markdown table with exactly the columns Owner
  | Action | Due.
- The table lists every commitment in the notes, including informal ones in prose
  and ones not labelled ACTION, each with the person who made it as Owner.
- Every Due value is an ISO date (YYYY-MM-DD) or none. A vague or relative deadline
  becomes a date only when the notes make the date clear; otherwise Due is none.
- 'The reviewer''s report shows every criterion met (criteria met: n of m with n =
  m), and the writer applied every required change.'
deliverable:
  description: One memo named memo-<meeting date>.md
  format: markdown
  max_words: 400
  path: /tmp/hirearchy-e5-s1-1792811051/deliverables
budget: 12
locked: false
version: 1
defined_by: root
defined: '2026-10-24T03:06:42.305850+00:00'
created: '2026-10-24T03:06:42.305850+00:00'
---

