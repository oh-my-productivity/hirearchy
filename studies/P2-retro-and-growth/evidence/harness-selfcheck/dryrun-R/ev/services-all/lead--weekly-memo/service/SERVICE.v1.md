---
name: weekly-memo
description: One memo of decisions and action items from one meeting's notes file.
inputs:
- name: notes_file
  description: the notes file name, e.g. 2026-10-05.md
  required: true
acceptance:
- One memo per notes file, at most 400 words.
- The memo lists every decision and every commitment in the notes, informal ones included.
- The action items are a table Owner | Action | Due, with ISO dates and 'none' if
  there's no date.
- Decisions and actions use the notes' own words.
deliverable:
  description: one markdown memo
  format: markdown
  path: /private/tmp/hirearchy-p2/selfcheck-R-1793275673/deliverables
budget: 12
locked: false
version: 1
defined_by: root
defined: '2026-10-29T12:07:57.602501+00:00'
created: '2026-10-29T12:07:57.602501+00:00'
approved_in: plan 384896a34959
sources:
- default: true
- default: true
- from: with the action items as a table with columns Owner | Action | Due (ISO dates,
    'none' if there's no date)
- from: Use the words from the notes.
  asked: 'Owners: initials or full names?'
elicitation: 'Thanks! The file name each time is fine. Format: a markdown memo, at
  most 400 words, with the action items as a table with columns Owner | Action | Due
  (ISO dates, ''none'' if there''s no date). The rest of your defaults are fine, the
  deliverables folder too. Please keep it cheap, but I need it right - about 12 runs
  per memo. No separate reviewer: the lead checks. Use the words from the notes.'
---

