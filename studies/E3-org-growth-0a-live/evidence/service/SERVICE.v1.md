---
name: weekly-meeting-memo
description: One memo (decisions and action items) from the notes file of one weekly
  meeting
inputs:
- name: notes_file
  description: File name of the meeting notes inside the notes folder, for example
    2026-10-19.md
  required: true
acceptance:
- The memo is based only on the requested notes file and contains nothing that is
  not in it.
- At most 400 words as counted by read.
- 'The memo has exactly these sections, in this order: Decisions, Action items, Next
  meeting.'
- Decisions lists every decision recorded in the notes file.
- Action items is a markdown table with the columns Owner | Action | Due, and has
  one row for every commitment in the notes file, including informal ones stated only
  in prose (anyone who said they would do something).
- Every Due value is an ISO date (YYYY-MM-DD); a relative or vague deadline is turned
  into a date only when the notes make the date clear, otherwise Due is none; a commitment
  with no deadline has Due none.
- Next meeting gives the date of the next meeting as stated in the notes file.
- 'The reviewer''s report shows every criterion met (criteria met: n of m with n =
  m), and the writer applied every required change.'
deliverable:
  description: One markdown memo per request, saved as memo-<meeting date>.md
  format: markdown
  max_words: 400
  path: /tmp/hirearchy-e3-1792595952/deliverables
budget: 15
locked: false
version: 1
defined_by: root
defined: '2026-10-21T15:23:47.921302+00:00'
created: '2026-10-21T15:23:47.921302+00:00'
---

