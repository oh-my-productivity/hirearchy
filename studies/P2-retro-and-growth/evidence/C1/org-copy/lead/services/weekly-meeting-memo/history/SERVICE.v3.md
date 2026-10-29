---
name: weekly-meeting-memo
description: One short markdown memo from one meeting's notes with the decisions and
  a table of action items.
inputs:
- name: notes_file
  description: File name of the meeting notes inside the notes folder, for example
    2026-10-05.md
  required: true
acceptance:
- Covers only the meeting in the file named in the request and nothing else.
- At most 400 words as counted by read.
- The memo has a section titled "Decisions" that lists every decision in the notes,
  worded as in the notes.
- The memo has a section titled "Actions" with a markdown table with the columns Owner
  | Action | Due, with one row for every commitment in the notes, including informal
  ones written in prose ("X said he would ..."), worded as in the notes.
- Due is an ISO date (YYYY-MM-DD). A relative deadline such as "before Friday" becomes
  a date only when the notes and the meeting date make it clear; otherwise, and when
  the notes give no date, Due is "none".
- A name that is not in the attendee list is used as written in the notes and marked
  "(not in attendee list)".
- Nothing appears in the memo that is not in the notes file.
- The lead's check against the notes shows every decision and every commitment covered
  (n of m with n = m).
- The memo starts with a one-line "Summary:" of the meeting, followed by the "Decisions"
  section, then the "Actions" section, in that order.
- The Actions table leaves out any line where nobody has to do anything, such as a
  statement that something stays as it is.
deliverable:
  description: One markdown memo for the meeting
  format: markdown
  max_words: 400
  path: /private/tmp/hirearchy-p2/C1-1793280632/deliverables
budget: 12
locked: false
version: 3
defined_by: root
defined: '2026-10-29T14:05:15.127789+00:00'
created: '2026-10-29T13:35:18.540965+00:00'
answers: 20261029T140412342725-root-28e3
about: C4
words: Yes, add it.
---

