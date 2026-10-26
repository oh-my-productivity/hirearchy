---
name: weekly-meeting-memo
description: One short markdown memo (decisions and action items) from one weekly
  meeting notes file
inputs:
- name: notes_file
  description: File name of the meeting notes inside the notes folder, e.g. 2026-10-05.md
  required: true
acceptance:
- Covers only the meeting in the requested notes file, and nothing that is not in
  that file.
- At most 400 words.
- Has a section listing the decisions taken in the meeting, and every decision in
  the notes is listed.
- Has the action items as a markdown table with exactly the columns Owner | Action
  | Due.
- Every commitment in the notes is a row in the table, including informal ones that
  someone only mentioned in prose (not only lines labelled ACTION), each with the
  right owner.
- Every Due value is an ISO date (YYYY-MM-DD). A vague deadline (such as before Friday,
  end of next week, the next meeting) is turned into a date counted from the meeting
  date when the notes make it clear; otherwise Due is none.
- 'The reviewer''s report shows every criterion met (criteria met: n of m with n =
  m), and the writer applied every required change.'
deliverable:
  description: One markdown memo named memo-<meeting date>.md
  format: markdown
  max_words: 400
  path: /tmp/hirearchy-g0-m1-s3-1793003475/deliverables
budget: 12
locked: false
version: 1
defined_by: root
defined: '2026-10-26T08:34:54.529628+00:00'
created: '2026-10-26T08:34:54.529628+00:00'
---

