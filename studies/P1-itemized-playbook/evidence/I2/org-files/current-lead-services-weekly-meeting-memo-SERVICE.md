---
name: weekly-meeting-memo
description: One memo of decisions and action items from one meeting's notes file.
inputs:
- name: meeting_file
  description: File name of the meeting notes in the notes folder, e.g. 2026-10-05.md
  required: true
acceptance:
- The memo is based on the requested notes file only.
- At most 400 words as counted by read.
- The memo has a section titled "Decisions" with one bullet for every decision stated
  in the notes, and a section titled "Actions" containing a markdown table with exactly
  the columns Owner | Action | Due; it has no other sections besides a title that
  names the meeting date.
- The Actions table has one row for every commitment in the notes, including informal
  ones said in prose (for example 'X said he'd do Y'), and no row for anything nobody
  committed to.
- Due is an ISO date (YYYY-MM-DD). A relative deadline such as 'by Friday' is converted
  to a date using the meeting date when the notes make the date clear. Due is 'none'
  when the notes give no date or say none.
- Every decision and action is traceable to the notes, and nothing is invented.
- 'The reviewer''s report shows every criterion met (criteria met: n of m with n =
  m), and the writer applied every required change.'
- The memo has a one-line 'Summary:' of the meeting directly after the title, then
  the Decisions section, then the Actions section; the Summary line is the only addition
  to what the "Decisions"/"Actions" criterion allows.
- 'Owners are shown as full names, always: in the Actions table the Owner column holds
  the owner''s full name as written in the notes, never initials.'
- For an owner the notes give only as initials, the Owner cell holds the initials
  followed by '(full name not in the notes)', for example 'JD (full name not in the
  notes)'.
deliverable:
  description: One markdown memo for the meeting, named memo-<meeting date>.md
  format: markdown
  max_words: 400
  path: /tmp/hirearchy-p1-I2-1793142034/deliverables
budget: 12
locked: false
version: 5
defined_by: root
defined: '2026-10-28T00:09:14.030320+00:00'
created: '2026-10-27T23:05:07.594743+00:00'
answers: 20261028T000812806533-root-81a8
about: C10
words: Yes, add it.
---

