---
name: weekly-meeting-memo
description: One memo of the decisions and the action items (who does what) from one
  weekly meeting's notes file.
inputs:
- name: notes_file
  description: File name of the meeting notes inside the notes folder, for example
    2026-10-05.md
  required: true
acceptance:
- Covers only the meeting in the named notes file, and only its decisions and who
  does what.
- At most 400 words as counted by read.
- A section titled "Decisions" lists every decision made in the meeting, including
  decisions that have no owner.
- A markdown table with exactly the columns Owner | Action | Due lists every commitment
  in the meeting, one row each, including informal ones where someone said in prose
  that they would do something.
- Due is an ISO date (YYYY-MM-DD). A vague deadline is turned into a date only when
  the notes make it clear; otherwise Due is none, and Due is none when the notes give
  no date.
- Every decision and every row is traceable to the named notes file; nothing is invented.
- 'The reviewer''s report shows every criterion met (criteria met: n of m with n =
  m), and the writer applied every required change.'
deliverable:
  description: One markdown memo per meeting, named memo-<meeting date>.md
  format: markdown
  max_words: 400
  path: /tmp/hirearchy-g0-m1-s2-1792997653/deliverables
budget: 12
locked: false
version: 1
defined_by: root
defined: '2026-10-26T06:57:36.664165+00:00'
created: '2026-10-26T06:57:36.664165+00:00'
---

