---
name: weekly-meeting-memo
description: One short markdown memo (decisions, and who does what) from one meeting's
  notes file.
inputs:
- name: notes_file
  description: File name of the meeting notes in the notes folder, for example 2026-10-19.md
  required: true
acceptance:
- Covers only the meeting in the named notes file.
- At most 400 words as counted by read.
- A markdown memo with a section titled 'Decisions' that lists every decision in the
  notes, including decisions stated only in prose.
- A section titled 'Action items' that is a markdown table with exactly the columns
  Owner | Action | Due.
- The table has one row for every commitment in the notes, including informal ones
  stated in prose (for example someone offering or saying they would do something),
  and none that are not in the notes.
- Due is an ISO date (YYYY-MM-DD). A vague deadline (for example 'next week', 'at
  the next meeting', 'end of next week') is turned into a date only when the notes
  make it clear, otherwise Due is 'none'; a commitment with no date has Due 'none'.
- Where the notes name no owner for an item, Owner says 'not stated'; no owner or
  date is guessed.
- Every statement is traceable to the notes file.
- 'The reviewer''s report shows every criterion met (criteria met: n of m with n =
  m), and the writer applied every required change.'
deliverable:
  description: One markdown memo for the meeting, named after the notes file.
  format: markdown
  max_words: 400
  path: /tmp/hirearchy-e4-s1-1792640562/deliverables
budget: 15
locked: false
version: 1
defined_by: root
defined: '2026-10-22T03:46:27.356748+00:00'
created: '2026-10-22T03:46:27.356748+00:00'
---

