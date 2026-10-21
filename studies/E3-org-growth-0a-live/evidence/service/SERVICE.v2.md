---
name: weekly-meeting-memo
description: One memo (decisions and action items) from the notes file of one weekly
  meeting
inputs:
- name: notes_file
  description: File name of the meeting notes inside the notes folder, for example
    2026-10-19.md
  required: true
acceptance:
- The memo is based only on the requested notes file and contains nothing that is
  not in it.
- At most 400 words as counted by read.
- Decisions lists every decision recorded in the notes file.
- Action items is a markdown table with the columns Owner | Action | Due, and has
  one row for every commitment in the notes file, including informal ones stated only
  in prose (anyone who said they would do something).
- Next meeting gives the date of the next meeting as stated in the notes file.
- 'The reviewer''s report shows every criterion met (criteria met: n of m with n =
  m), and the writer applied every required change.'
- 'The memo starts with one line that begins with ''Summary:'' and sums up the meeting
  in that single line, followed by exactly these sections, in this order: Decisions,
  Action items, Next meeting.'
- Every Due value is an ISO date (YYYY-MM-DD) or none. A deadline in the notes, including
  a relative one such as 'before Friday' (the date of that Friday, resolved from the
  meeting date), is turned into its ISO date; a date the commitment is for, such as
  the date a room is booked for, also counts as its Due. Due is none only when the
  notes give no such date or say there is no hard date.
deliverable:
  description: One markdown memo per request, saved as memo-<meeting date>.md
  format: markdown
  max_words: 400
  path: /tmp/hirearchy-e3-1792595952/deliverables
budget: 15
locked: false
version: 2
defined_by: root
defined: '2026-10-21T15:27:53.056427+00:00'
created: '2026-10-21T15:23:47.921302+00:00'
---
Client feedback on the first memo (2026-10-05): 'before Friday' means the date of that Friday (Sam: 2026-10-09). The date a booking is for counts as the Due (Marta's room for the training: 2026-10-14). The memo starts with a one-line 'Summary:'. Playbook: tell the writer these rules.
