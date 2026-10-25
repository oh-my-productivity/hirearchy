---
name: weekly-meeting-memo
description: One memo of the decisions and the actions (owner, action, due date) from
  one weekly meeting notes file.
inputs:
- name: notes_file
  description: File name of the meeting notes in the notes folder, for example 2026-10-05.md
  required: true
acceptance:
- Built only from the requested notes file; the other notes files are not used.
- The memo has a title line with the meeting date, then exactly two sections titled
  Decisions and Actions, and nothing else (no attendee list, no discussion recap).
- Decisions lists every decision the notes state, one bullet each, and no item the
  notes do not present as decided.
- Actions is a markdown table with the columns Owner | Action | Due. It has one row
  for every commitment in the notes, including informal ones in prose (someone says
  they will do something, offers to, or agrees to), not only lines labelled ACTION.
- Every Owner is a person named in the notes.
- Every Due value is an ISO date (YYYY-MM-DD) when the notes give a date, or give
  a relative deadline that points to one clear day counted from the meeting date;
  otherwise it is the word none. No date is guessed.
- At most 400 words as counted by read.
- 'The reviewer''s report shows every criterion met (criteria met: n of m with n =
  m), and the writer applied every required change.'
deliverable:
  description: One markdown memo for one meeting, named memo-<meeting date>.md, for
    example memo-2026-10-05.md.
  format: markdown
  max_words: 400
  path: /tmp/hirearchy-e7-s1-1792911600/deliverables
budget: 12
locked: false
version: 1
defined_by: root
defined: '2026-10-25T07:04:23.626836+00:00'
created: '2026-10-25T07:04:23.626836+00:00'
---

