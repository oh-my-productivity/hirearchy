# E4 restart teardown (after s1r, s2, s2r, s3)

Facts only. No product code changed, nothing committed. Snapshot: `teardown-safety-after.txt` (harness/safety-snapshot.sh, label teardown-after, 2026-10-22T22:40:20Z).

## 1. Study profiles in ~/.kiro/agents
At teardown start no study profile was present. Cross-check against `s*/profiles/deletions.txt`: the s1r, s2, s2r, s3 assistant profiles and the preflight prep profile `hirearchy-study-e4-prep-1792693245.json` were already deleted (copies verified in `s*/profiles/`); the older prep profile `hirearchy-study-e4-prep-1792639838.json` was already gone (template copy in harness/). Deleted in this step: none.

Remaining ~/.kiro/agents (all user-owned, untouched):
agent_config.json.example, claude-opus-5.5.json, claude-sonnet-5.5.json, evolve.json, hirearchy-organization-9d66c1-web-fetch-web-search.json, telegram_bot.json

## 2. Org kiro homes deleted (under ~/Library/Application Support/hirearchy/kiro-home/)
- hirearchy-e4-s1r-1792693-bfcddd47e6ecb16c
- hirearchy-e4-s2-17926988-212f59b7daf49c3f
- hirearchy-e4-s2r-1792702-b0c5db682e7e6ab7
- hirearchy-e4-s3-17927050-8f0c59d32ad49337
No preflight/probe org kiro home existed. kiro-home is now empty.
Left, recorded (outside the instruction's scope): the matching per-org dirs in ~/Library/Application Support/hirearchy/kiro-cwd/ (same four names).

## 3. safety-after (teardown-safety-after.txt) vs
- study-level `safety-after.txt` (22:36Z): no difference except the date lines, the memories dir mtime (22:51 -> 23:39 listing line), and the removal of the appended NOTES block. Settings md5s, skill md5, memories.db md5, agents listing identical.
- study-level `safety-before.txt` (03:38Z): differences are (a) ~/.kiro/settings cli.json, mcp.json, workflow_survey_state.json md5s (changed between 04:07Z and 18:24Z, outside any stream, already documented in safety-after.txt NOTES); (b) the prep profile removed (study-created); (c) repo HEAD d85cc131... -> 7d86c31f... (product commits made outside this study before s1r; the study's diff against 7d86c31 was empty). Skill SKILL.md md5 573495bb... and memories.db md5 3f53a1d9... unchanged. /Users/aminalizadeh/organization not touched.

## 4. Sandboxes left in /tmp
/tmp/hirearchy-e4-s1-1792640562, /tmp/hirearchy-e4-s1r-1792693447, /tmp/hirearchy-e4-s2-1792698851, /tmp/hirearchy-e4-s2r-1792702135, /tmp/hirearchy-e4-s3-1792705005 (plus any other pre-existing /tmp/hirearchy-e4-* dirs such as diag, prep-*, probe-*, preflight, untouched).
