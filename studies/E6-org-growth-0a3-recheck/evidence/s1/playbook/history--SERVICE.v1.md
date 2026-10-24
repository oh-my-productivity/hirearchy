---
name: weekly-memo
description: One memo with the decisions and the action items of one weekly meeting,
  from its notes file.
inputs:
- name: notes_file
  description: File name of the meeting notes inside the notes folder, e.g. 2026-10-19.md
  required: true
acceptance:
- The memo is based only on the named notes file and covers only that meeting.
- At most 400 words as counted by read.
- Every decision taken in the meeting is listed in a section titled "Decisions", and
  nothing that was not decided is listed there.
- Every action item is in one markdown table with exactly the columns Owner | Action
  | Due. This includes every commitment, also informal ones said in prose (someone
  said they would do something), not only items marked ACTION.
- The Due column holds only an ISO date (YYYY-MM-DD) or the word none. A date is given
  only when the notes or the meeting date fix exactly one calendar day (for example,
  a relative date such as "by end of next week" is turned into a date only if it fixes
  one day); otherwise Due is none.
- Every Owner is a person named in the notes, and every Action and Due value matches
  the notes.
- 'The reviewer''s report shows every criterion met (criteria met: n of m with n =
  m), and the writer applied every required change.'
deliverable:
  description: One markdown memo for the meeting, named memo-<meeting date>.md
  format: markdown
  max_words: 400
  path: /tmp/hirearchy-e6-s1-1792855848/deliverables
budget: 16
locked: false
version: 1
defined_by: root
defined: '2026-10-24T15:36:06.393173+00:00'
created: '2026-10-24T15:36:06.393173+00:00'
---

