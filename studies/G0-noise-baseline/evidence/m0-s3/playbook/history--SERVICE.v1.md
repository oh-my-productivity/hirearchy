---
name: weekly-meeting-memo
description: One markdown memo with the decisions and the action items of one weekly
  meeting, from its notes file.
inputs:
- name: notes_file
  description: File name of the meeting notes in the notes folder, for example 2026-10-19.md
  required: true
acceptance:
- Covers only the meeting in the requested notes file and nothing else.
- At most 400 words as counted by read.
- A section titled "Decisions" lists every decision recorded in the notes file, and
  no decision that is not in it.
- A section titled "Action items" holds a markdown table with exactly the columns
  Owner | Action | Due.
- The table has one row for every commitment in the notes file, including informal
  ones stated in prose rather than labelled as an action, and no row for something
  nobody committed to.
- Each Due value is an ISO date (YYYY-MM-DD) or the word none. A deadline given relative
  to the meeting (for example "before Friday") is converted to an ISO date computed
  from the meeting date when the notes make the day clear; if no deadline is given,
  or it does not point to a single day, the value is none.
- Every statement is traceable to the requested notes file; nothing is added from
  outside it.
- 'The reviewer''s report shows every criterion met (criteria met: n of m with n =
  m), and the writer applied every required change.'
deliverable:
  description: One markdown memo named memo-<meeting date>.md (the date of the requested
    notes file)
  format: markdown
  max_words: 400
  path: /tmp/hirearchy-g0-m0-s3-1793000481/deliverables
budget: 12
locked: false
version: 1
defined_by: root
defined: '2026-10-26T07:45:15.733600+00:00'
created: '2026-10-26T07:45:15.733600+00:00'
---

