---
name: weekly-meeting-memo
description: One short markdown memo (decisions and action items table) from one weekly
  meeting notes file.
inputs:
- name: notes_file
  description: File name of the meeting notes inside the notes folder, for example
    2026-11-09.md
  required: true
acceptance:
- The memo covers only the meeting in the named notes file.
- The memo is markdown and has at most 400 words as counted by read.
- The memo has a Decisions section listing every decision recorded in the notes file,
  one line each.
- The memo has the action items as a markdown table with exactly the columns Owner
  | Action | Due.
- The table contains every commitment in the notes file, including informal ones stated
  in prose (for example 'X said they would do Y'), whether or not it is labelled ACTION.
- Every Due value is an ISO date (YYYY-MM-DD) or the word none. A vague deadline (for
  example 'by Friday') becomes a date, worked out from the meeting date, when the
  notes make it clear; if no date is given, Due is none.
- Every decision and action item is stated in the named notes file; nothing is invented.
- 'The reviewer''s report shows every criterion met (criteria met: n of m with n =
  m), and the writer applied every required change.'
- The memo starts with a one-line 'Summary:' of the meeting, followed by the Decisions
  section, then the action items table.
- In the action table, the Owner column shows initials only (one capital letter per
  person, for example P, S, L, M, D).
deliverable:
  description: One memo per request, named memo-<notes file name>, for example memo-2026-11-09.md
  format: markdown
  max_words: 400
  path: /tmp/hirearchy-p1-F3-1793152805/deliverables
budget: 12
locked: true
version: 4
defined_by: root
defined: '2026-10-28T02:37:20.103207+00:00'
created: '2026-10-28T02:04:45.103657+00:00'
answers: 20261028T023322666789-root-620b
about: C4
words: Yes, add it - and this version is right now, thanks.
---

