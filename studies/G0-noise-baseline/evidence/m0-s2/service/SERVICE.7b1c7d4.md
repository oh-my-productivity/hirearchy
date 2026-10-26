---
name: weekly-meeting-memo
description: One markdown memo with the decisions and the action-item table for one
  weekly meeting
inputs:
- name: notes_file
  description: File name of the meeting notes inside the notes folder, for example
    2026-10-05.md
  required: true
acceptance:
- Covers only the meeting in the requested notes file and nothing else.
- At most 400 words as counted by read.
- Has a section titled Decisions that lists every decision the notes record as made
  (decided or agreed), one line each, and no item that is not a decision.
- Has a section titled Actions with a markdown table whose columns are exactly Owner
  | Action | Due.
- The table has one row for every commitment in the notes, including informal ones
  stated in prose (for example someone saying they will look into something), not
  only items labelled ACTION.
- Due is an ISO date (YYYY-MM-DD) when the notes give a date, or a deadline that resolves
  to one from the meeting date (a named weekday means that weekday of the meeting's
  week; the next meeting means the date the notes give for it). Due is 'none' when
  the notes give no date, say no hard date, or give only a loose period such as 'this
  week'.
- Every decision and every table row is traceable to the notes file; no owner, action
  or date is invented.
- 'The reviewer''s report shows every criterion met (criteria met: n of m with n =
  m), and the writer applied every required change.'
- Starts with a one-line 'Summary:' of the meeting, then the Decisions section, then
  the Actions table, in that order.
deliverable:
  description: One markdown memo named memo-<meeting date>.md
  format: markdown
  max_words: 400
  path: /tmp/hirearchy-g0-m0-s2-1792995184/deliverables
budget: 12
locked: false
version: 2
defined_by: root
defined: '2026-10-26T06:28:55.338235+00:00'
created: '2026-10-26T06:16:39.838295+00:00'
answers: 20261026T062806052336-root-02c4
about: C3
words: Yes, add it.
---

