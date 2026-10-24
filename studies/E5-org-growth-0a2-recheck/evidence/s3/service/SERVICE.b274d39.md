---
name: weekly-meeting-memo
description: One short memo with the decisions and the action items of one weekly
  meeting, from its notes file.
inputs:
- name: notes_file
  description: The file name of the meeting notes inside the notes folder, for example
    2026-10-05.md
  required: true
acceptance:
- The memo is based only on the named notes file and covers only that meeting.
- At most 400 words as counted by read.
- The memo is markdown with a Decisions section (a list) and an Action items section
  (a table with exactly the columns Owner | Action | Due), and no other section.
- Every decision made in the meeting is listed, including logistics decisions and
  decisions to keep things as they are.
- Every commitment in the notes is a row in the table with its owner, including informal
  ones where someone said they would do something, not only items labelled ACTION.
- Due is an ISO date (YYYY-MM-DD). A relative or vague deadline (for example 'before
  Friday') becomes a date only when the notes make the date clear, using the meeting
  date as the reference; otherwise Due is 'none'. No date is invented.
- Nothing in the memo is missing from or contradicts the notes file.
- 'The reviewer''s report shows every criterion met (criteria met: n of m with n =
  m), and the writer applied every required change.'
- The memo starts with a one-line 'Summary:' of the meeting, then the Decisions list,
  then the Action items table, in that order; the Summary line is not counted as a
  section.
deliverable:
  description: One markdown memo for one meeting.
  format: markdown
  max_words: 400
  path: /tmp/hirearchy-e5-s3-1792814736/deliverables
budget: 12
locked: false
version: 2
defined_by: root
defined: '2026-10-24T04:25:15.109656+00:00'
created: '2026-10-24T04:08:52.853946+00:00'
answers: 20261024T042421215723-root-a6fe
about: C3
words: Yes, add it.
---

