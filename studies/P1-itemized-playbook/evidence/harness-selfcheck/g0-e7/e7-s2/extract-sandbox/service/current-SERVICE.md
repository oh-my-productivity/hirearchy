---
name: weekly-meeting-memo
description: One short markdown memo (decisions and action items) from one meeting-notes
  file.
inputs:
- name: notes_file
  description: File name of the meeting notes in the notes folder, e.g. 2026-10-19.md
  required: true
acceptance:
- The memo covers only the meeting in the named notes file.
- Every decision stated in the notes file appears in the memo's Decisions section,
  and no decision appears that the notes do not state.
- Every commitment in the notes file appears as a row in the Actions table, including
  informal ones said in passing without an ACTION label (anything a person said they
  would do), each with the person who committed to it as Owner.
- Actions are a markdown table with exactly the columns Owner | Action | Due.
- Due is an ISO date (YYYY-MM-DD) when the notes state a date or give a deadline that
  can be resolved from the meeting date (for example 'before Friday'); otherwise Due
  is 'none'.
- At most 400 words.
- 'The reviewer''s report shows every criterion met (criteria met: n of m with n =
  m), and the writer applied every required change.'
- The memo starts with a one-line 'Summary:' of the meeting, followed by the Decisions
  section, then the Actions (action items) table, in that order.
deliverable:
  description: One markdown memo with a Decisions section (bulleted list) and an Actions
    section (table Owner | Action | Due).
  format: markdown
  max_words: 400
  path: /tmp/hirearchy-e7-s2-1792914064/deliverables
budget: 12
locked: false
version: 2
defined_by: root
defined: '2026-10-25T08:00:29.727776+00:00'
created: '2026-10-25T07:44:49.503484+00:00'
answers: 20261025T075910994217-root-ce17
about: C4
words: Yes, add it. No more spend, please deliver as is.
---

