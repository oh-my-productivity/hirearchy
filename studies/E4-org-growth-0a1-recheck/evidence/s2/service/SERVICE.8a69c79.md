---
name: weekly-meeting-memo
description: One short memo (decisions and action items) from one weekly meeting-notes
  file
inputs:
- name: notes_file
  description: File name of the meeting notes inside the notes folder, e.g. 2026-10-19.md
  required: true
acceptance:
- Uses only the notes file named in the request.
- At most 400 words as counted by read.
- A markdown memo with a section titled Decisions (a list) and a section titled Action
  items (a table).
- Decisions lists every decision recorded in the notes, including small ones such
  as meeting logistics.
- The Action items table has exactly the columns Owner | Action | Due, with one row
  for every commitment in the notes, including informal ones written in prose and
  not labelled ACTION (anyone who said they would do something).
- Due is an ISO date (YYYY-MM-DD). A vague or relative deadline (for example 'next
  week', 'by Friday') is turned into a date computed from the meeting date only when
  it identifies one exact calendar day; otherwise Due is 'none'. A commitment with
  no deadline has Due 'none'.
- Every decision, owner, action and date is traceable to the notes file; nothing is
  invented.
- 'The reviewer''s report shows every criterion met (criteria met: n of m with n =
  m), and the writer applied every required change.'
deliverable:
  description: One memo for the meeting, named memo-<meeting date>.md
  format: markdown
  max_words: 400
  path: /tmp/hirearchy-e4-s2-1792698851/deliverables
budget: 15
locked: false
version: 1
defined_by: root
defined: '2026-10-22T19:59:19.458154+00:00'
created: '2026-10-22T19:59:19.458154+00:00'
---

