---
name: weekly-meeting-memo
description: One memo (decisions and action table) from one weekly meeting's notes
  file.
inputs:
- name: notes_file
  description: File name of the meeting notes in the notes folder, for example 2026-11-16.md
  required: true
acceptance:
- Covers only the meeting in the requested notes file.
- The memo is markdown and has at most 400 words as counted by read.
- Every decision stated in the notes is listed under a heading "Decisions".
- Every commitment in the notes, including informal ones stated in prose (for example
  "X said he would ..."), is one row of a table under a heading "Actions".
- The table columns are exactly Owner | Action | Due.
- Due is an ISO date (YYYY-MM-DD) or "none". A relative date such as "by Friday" is
  converted to an ISO date using the meeting date only when the notes make it clear;
  if there is no date or it is not clear, Due is "none".
- Decisions and actions use the words of the notes, and nothing appears that is not
  in the notes.
- Topics that were only discussed and not decided are not listed.
- The memo names the meeting date and the people present.
- The memo gives the next meeting date when the notes give one.
- 'The reviewer''s report shows every criterion met (criteria met: n of m with n =
  m), and the writer applied every required change.'
- The first line of the memo is one line starting "Summary:" that summarises the meeting,
  in the team's own words and using only facts from the notes (this is the one exception
  to "use the words of the notes"). After it come "Decisions", then "Actions". The
  meeting date, the people present and the next meeting date go after the Actions
  table.
- In the Actions table, the Owner column holds the owner's name as written in the
  notes (for example Priya), not an initial.
deliverable:
  description: One markdown memo per meeting, named memo-<notes file name>.md (for
    example memo-2026-11-16.md).
  format: markdown
  max_words: 400
  path: /tmp/hirearchy-p1-I1-1793136275/deliverables
budget: 12
locked: false
version: 4
defined_by: root
defined: '2026-10-27T22:19:05.621740+00:00'
created: '2026-10-27T21:30:58.639390+00:00'
answers: 20261027T221759090700-root-9a11
about: C13
words: Yes, add it.
---

