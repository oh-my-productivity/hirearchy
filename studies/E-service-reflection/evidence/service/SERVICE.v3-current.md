---
name: weekly-memo
description: One short memo (decisions and action items) from one meeting notes file.
inputs:
- name: notes_file
  description: File name of the meeting notes inside the notes folder, for example
    2026-10-19.md
  required: true
acceptance:
- Uses only the notes file named in the request and nothing else.
- The memo is markdown with at most 400 words as counted by read.
- It has a section titled "Decisions" that lists every decision stated in the notes
  file and no decision that is not in it.
- It has a section titled "Action items" containing a markdown table with exactly
  the columns Owner | Action | Due, with one row for every action item in the notes
  file and no row that is not in it.
- Every Due cell is an ISO date (YYYY-MM-DD) or the word none; a relative date in
  the notes is converted to ISO using the meeting date in the file name.
- Where the notes name no owner, the Owner cell says "owner not stated".
- 'The reviewer''s report shows every criterion met (criteria met: n of m with n =
  m), checked against the notes file, and the writer applied every required change.'
- In the memo, the "Decisions" section comes before the "Action items" section.
- Every commitment someone makes in the notes counts as an action item, whether or
  not it is labelled ACTION, including ones buried in a paragraph; the reviewer re-reads
  the whole notes file for such commitments and confirms each one has a row.
deliverable:
  description: One markdown memo named memo-<meeting date>.md
  format: markdown
  max_words: 400
  path: /tmp/orgmcp-e-1792289694/deliverables
budget: 12
locked: false
version: 3
defined_by: root
defined: '2026-10-18T02:42:20.124460+00:00'
created: '2026-10-18T02:16:43.197036+00:00'
---

