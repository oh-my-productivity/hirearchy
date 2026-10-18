##### ceo/services/weekly-brief/SERVICE.md
---
name: weekly-brief
description: A one-page brief on the past week's news about a topic.
inputs:
- name: topic
  description: what the brief is about
  required: true
- name: week
  description: ISO week; default the current one
  required: false
acceptance:
- At most 600 words
- Every factual claim has a source URL
deliverable:
  description: one markdown file
  format: markdown
  max_words: 600
budget: 10
locked: false
version: 1
defined_by: root
defined: '2026-01-15T09:04:00.000000+00:00'
created: '2026-01-15T09:04:00.000000+00:00'
---
Mind the sources.

##### ceo/services/weekly-brief/PLAYBOOK.md
---
service: weekly-brief
version: 2
revised: '2026-01-15T09:10:00.000000+00:00'
by: ceo
reason: 'Client rejected: too long.'
---
# Weekly brief

1. Ask the researcher for sources on the topic.
2. Have the writer draft at most 600 words.
3. Have the fact-checker verify every claim before you report.
4. Cut to 600 words before reporting.

##### ceo/services/plain-brief/SERVICE.md
---
name: plain-brief
description: A one-page brief on the past week's news about a topic.
inputs:
- name: topic
  description: what the brief is about
  required: true
- name: week
  description: ISO week; default the current one
  required: false
acceptance:
- At most 600 words
- Every factual claim has a source URL
deliverable:
  description: one markdown file
  format: markdown
  max_words: 600
budget: 4
locked: false
version: 1
defined_by: root
defined: '2026-01-15T09:05:00.000000+00:00'
created: '2026-01-15T09:05:00.000000+00:00'
---


##### ceo/services/plain-brief/PLAYBOOK.md
(missing)
