---
name: meeting-memo
description: One short memo of the decisions and the who-does-what from one weekly
  meeting's notes file
inputs:
- name: notes_file
  description: File name of the meeting notes inside the notes folder, for example
    2026-10-19.md
  required: true
acceptance:
- The memo is based only on the requested notes file and covers that meeting only.
- At most 400 words as counted by read.
- Format is markdown with a section "Decisions" and a section "Action items".
- The Decisions section lists every decision stated in the notes file, each in one
  line, and no decision that is not in the notes.
- The Action items section is a markdown table with exactly the columns Owner | Action
  | Due, with one row for every commitment in the notes file, including informal ones
  stated in prose (for example 'I'll sort it out'); no row for something nobody committed
  to.
- Every Due value is an ISO date (YYYY-MM-DD) or the word none when the notes give
  no date; a date is never invented, and an owner or date that the notes leave unclear
  is listed in a final section titled 'Open questions'.
- 'The reviewer''s report shows every criterion met (criteria met: n of m with n =
  m) and every decision and commitment in the notes file checked against the memo
  (n of m, n = m), and the writer applied every required change.'
- The memo's first content line (right after the title, if any) is a single line starting
  with 'Summary:' that summarises the meeting in one sentence; then come the Decisions
  section, then the Action items section, then Open questions (when there is anything
  to list).
- When the notes say a commitment is due 'before <weekday>', its Due is the date of
  that weekday in the meeting's week; when the notes say it is 'for <date>', its Due
  is that date; both are written as ISO dates and are not listed in Open questions.
- The Action items table has no row for something that merely stays as it is or that
  nobody has to do (for example 'keep the agenda as sent'); only things someone commits
  to do get a row.
deliverable:
  description: One markdown memo named after the meeting notes file (for example 2026-10-19.md)
  format: markdown
  max_words: 400
  path: /tmp/orgmcp-e2-1792295253/deliverables
budget: 15
locked: false
version: 3
defined_by: root
defined: '2026-10-18T04:12:36.509545+00:00'
created: '2026-10-18T03:49:53.825607+00:00'
---

