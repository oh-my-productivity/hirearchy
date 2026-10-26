---
name: weekly-meeting-memo
description: One memo from one weekly meeting notes file - what was decided and who
  does what.
inputs:
- name: notes_file
  description: File name of the meeting notes in the notes folder, for example 2026-10-05.md
  required: true
acceptance:
- Covers only the meeting in the requested notes file.
- At most 400 words as counted by read.
- 'Markdown with exactly these sections: Decisions, Action items, Open or tentative
  items.'
- Every decision recorded in the notes file appears under Decisions.
- 'Every commitment in the notes file appears as a row of the Action items table:
  the explicit ACTION lines and also anything a person said they would do, including
  informal ones said in prose.'
- The Action items table has exactly the columns Owner | Action | Due. Due is an ISO
  date (YYYY-MM-DD), or 'none' when the notes give no date.
- A vague deadline (for example 'before Friday' or 'by end of next week') is turned
  into an ISO date only when the notes make the date clear from the meeting date;
  otherwise Due is 'none'.
- A commitment the notes word as hedged (for example 'will probably') is marked '(tentative)'
  in its Action cell. Open or tentative items lists anything unresolved or unclear
  in the notes, or says 'none'.
- Nothing appears that is not in the notes file, and names are spelled as in the notes.
- 'The reviewer''s report shows every criterion met (criteria met: n of m with n =
  m), and the writer applied every required change.'
- The memo starts with a one-line 'Summary:' of the meeting, then the Decisions section,
  then the Action items section. The Summary line does not count as a section for
  the 'exactly these sections' check.
deliverable:
  description: One markdown memo named memo-<meeting date>.md (for example memo-2026-10-05.md)
  format: markdown
  max_words: 400
  path: /tmp/hirearchy-g0-m0-s1-1792990299/deliverables
budget: 12
locked: false
version: 2
defined_by: root
defined: '2026-10-26T05:08:19.637315+00:00'
created: '2026-10-26T04:55:11.614882+00:00'
answers: 20261026T050645955155-root-ea45
about: C3
words: Yes, add it. Yes, fund it - but please keep an eye on the cost.
---

