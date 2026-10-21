##### ceo/AGENT.md
---
role: Chief executive
tools: []
can_hire: true
max_children: 2
hired_by: root
created: '2026-01-15T09:01:00+00:00'
---
# Role: Chief executive

Run the company.

##### ceo/eng/AGENT.md
---
role: Engineer
tools: []
can_hire: false
max_children: 0
hired_by: ceo
created: '2026-01-15T09:02:00+00:00'
---
# Role: Engineer

Build things.

##### dev/AGENT.md
---
role: Developer
model: claude-sonnet-5.5
tools:
- read
- shell
- write
can_hire: true
max_children: 3
workspace: <WS>
inputs:
- <INPUTS>
hired_by: root
created: '2026-01-15T09:04:00+00:00'
---
# Role: Developer

Write code in the workspace.

##### analyst/AGENT.md
---
role: Analyst
tools:
- read
can_hire: false
max_children: 0
inputs:
- <INPUTS>
hired_by: root
created: '2026-01-15T09:05:00+00:00'
---
# Analyst charter

Own heading wins.
