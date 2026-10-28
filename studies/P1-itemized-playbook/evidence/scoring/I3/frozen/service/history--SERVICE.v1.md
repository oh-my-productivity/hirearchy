---
name: weekly-meeting-memo
description: One memo with the decisions and the action-item table for one weekly
  meeting, from its notes file.
inputs:
- name: notes_file
  description: File name of the meeting notes inside the notes folder, for example
    2026-11-16.md
  required: true
acceptance:
- Covers only the meeting in the named notes file and nothing else.
- At most 400 words.
- Has a section titled Decisions that lists every decision recorded in the named file,
  using the notes' own words.
- Has a section titled Action items containing a markdown table with exactly the columns
  Owner | Action | Due.
- The table has one row for every commitment in the named file, including informal
  ones in prose (someone said they would do something) and ones whose owner is given
  only by initials; no row is invented and none is left out.
- The Action column uses the notes' own words for the task.
- Due is an ISO date (YYYY-MM-DD). A relative deadline such as 'by Friday' is converted
  to a date using the meeting date when the notes make it clear; otherwise, and when
  the notes give no date, Due is 'none'.
- Every statement is traceable to the named notes file.
- 'The reviewer''s report shows every criterion met (criteria met: n of m with n =
  m), and the writer applied every required change.'
deliverable:
  description: One markdown memo for one meeting, named memo-<meeting date>.md
  format: markdown
  max_words: 400
  path: /private/tmp/hirearchy-p1-I3-1793157452/deliverables
budget: 12
locked: false
version: 1
defined_by: root
defined: '2026-10-28T03:24:13.393630+00:00'
created: '2026-10-28T03:24:13.393630+00:00'
---

