---
name: weekly-memo
description: One memo of decisions and action items from one weekly meeting's notes
  file
inputs:
- name: meeting_file
  description: File name of the meeting notes inside the notes folder, e.g. 2026-10-19.md
  required: true
acceptance:
- The memo covers only the meeting in the requested notes file and nothing else.
- At most 400 words as counted by read.
- The memo is markdown with a section titled "Decisions" and a section titled "Action
  items".
- Every decision recorded in the notes, including small ones such as a schedule change,
  is listed under Decisions, with its reason when the notes give one.
- Action items is a table with exactly the columns Owner | Action | Due.
- Every commitment in the notes is a row of the table, including informal ones said
  in prose without an ACTION label (anyone who said they would do something).
- Each row names the person the notes name as the owner.
- Due is an ISO date (YYYY-MM-DD). A vague deadline (for example 'end of next week'
  or 'the day before the freeze') is turned into a date only when the notes make the
  date clear from the meeting date or other dates in the notes; otherwise Due is 'none'.
  Due is 'none' when the notes give no deadline.
- 'No invented decisions, owners, dates or reasons: nothing is stated that the notes
  do not say.'
- 'The reviewer''s report shows every criterion met (criteria met: n of m with n =
  m) after checking the memo against the whole notes file, and the writer applied
  every required change.'
deliverable:
  description: One markdown memo for the requested meeting
  format: markdown
  max_words: 400
  path: /tmp/hirearchy-e6-s2-1792859296/deliverables
budget: 12
locked: false
version: 1
defined_by: root
defined: '2026-10-24T16:31:47.111122+00:00'
created: '2026-10-24T16:31:47.111122+00:00'
---

