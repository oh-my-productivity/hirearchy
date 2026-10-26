---
name: weekly-memo
description: One short memo (decisions and action items) from one meeting's notes
  file
inputs:
- name: notes_file
  description: File name of the meeting notes in the notes folder, for example 2026-10-05.md
  required: true
acceptance:
- Covers only the meeting in the requested notes file and nothing else.
- At most 400 words as counted by read.
- Besides a title line with the meeting date, the memo has exactly two sections, titled
  "Decisions" and "Action items".
- Decisions lists every decision recorded in the notes file, and no decision that
  is not in it.
- Action items is a markdown table with the columns Owner | Action | Due, with one
  row for every commitment in the notes, including informal ones made in prose (someone
  said they would do something), not only lines labelled ACTION.
- Every row has a named person as Owner.
- Due is an ISO date (YYYY-MM-DD). A vague deadline ('before Friday', 'next week')
  becomes an ISO date only when the notes make the date clear, and the original wording
  is kept in the Action cell; otherwise Due is 'none'. No date is ever invented.
- Every statement is traceable to the notes file.
- 'The reviewer''s report shows every criterion met (criteria met: n of m with n =
  m), and the writer applied every required change.'
deliverable:
  description: One markdown memo named memo-<meeting date>.md
  format: markdown
  max_words: 400
  path: /tmp/hirearchy-g0-m1-s1-1792992820/deliverables
budget: 12
locked: false
version: 1
defined_by: root
defined: '2026-10-26T05:37:17.244687+00:00'
created: '2026-10-26T05:37:17.244687+00:00'
---

