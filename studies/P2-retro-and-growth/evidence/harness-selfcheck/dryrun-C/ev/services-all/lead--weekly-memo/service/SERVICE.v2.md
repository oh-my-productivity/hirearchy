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
- The memo starts with a one-line 'Summary:', then the decisions, then the action
  items.
deliverable:
  description: one markdown memo
  format: markdown
  path: /private/tmp/hirearchy-p2/selfcheck-C-1793275756/deliverables
budget: 12
locked: false
version: 2
defined_by: root
defined: '2026-10-29T12:09:21.090964+00:00'
created: '2026-10-29T12:09:20.901962+00:00'
answers: 20261029T120921089978-root-1ddc
about: C1
words: Yes, add it.
---

