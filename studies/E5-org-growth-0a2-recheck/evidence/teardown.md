# E5 teardown (after s1, s2, s3)

Facts only. No product code changed, nothing staged, committed or pushed. Snapshot: `teardown-safety-after.txt` (harness/safety-snapshot.sh, label teardown-after, 2026-10-24T04:41:59Z).

## 1. Study profiles in ~/.kiro/agents
At teardown start no study profile was present. Cross-check:
- `preflight-profiles.txt`: `hirearchy-study-e5-probe.json` created and deleted by the preflight (copy in `probe/`).
- `s1/profiles/deletions.txt`: `hirearchy-study-e5-s1-assistant` deleted 2026-10-24T03:30:30Z.
- `s2/profiles/deletions.txt`: `hirearchy-study-e5-s2-assistant` deleted 2026-10-24T04:01:52Z.
- `s3/profiles/deletions.txt`: `hirearchy-study-e5-s3-assistant` deleted 2026-10-24T04:38:53Z.
Deleted in this step: none.

Remaining ~/.kiro/agents (all user-owned, untouched):
agent_config.json.example, claude-opus-5.5.json, claude-sonnet-5.5.json, evolve.json, hirearchy-organization-9d66c1-web-fetch-web-search.json, telegram_bot.json

## 2. Org kiro homes deleted (under ~/Library/Application Support/hirearchy/kiro-home/)
- hirearchy-e5-s1-17928110-79a97641d74dd37d
- hirearchy-e5-s2-17928128-86c02ffe84a33875
- hirearchy-e5-s3-17928147-3afa64a909202d97
kiro-home is now empty. No probe org kiro home existed.
Left, recorded (not deleted): the matching dirs in ~/Library/Application Support/hirearchy/kiro-cwd/ (same three names). The four E4 dirs in kiro-cwd were not touched.

## 3. Safety snapshot after vs before
Compared with `preflight-safety-before.txt` and `s1/s2/s3/safety-before.txt`. The only differences in every comparison:
- the label/date/date_utc/epoch lines (header);
- the mtime of `~/.kiro/memories` (listing line 20): now Oct 24 05:41. `memories.db` md5 3f53a1d90a590b253fc33aaa1c11342c, size and mtime (Oct 21 05:43) are identical, so only the directory entry time changed, with no file change;
- the mtime of `~/.kiro/agents` (listing line 25): now Oct 24 05:38, from the creation and deletion of the study profiles. The file list and every md5 in it are identical.
Identical: all ~/.kiro/settings md5s, the global skill md5, agents file list, ~/.kiro/skills and steering listings, the repo `git status --porcelain` (`?? docs/research/`, same as before).
/Users/aminalizadeh/organization: file count 1703, newest mtime 1792548884, tree digest 9d722080be9d80d2771cdda6d072227f, all unchanged. Not touched.
Skill `/Users/aminalizadeh/.kiro/skills/hirearchy/SKILL.md` md5: b7187d6ef749505893e9aef99276ef7c (unchanged).
No unexplained change.

## 4. Freeze
HEAD of /Volumes/workspace/hirearchy is 6618c0d. `git diff --stat 6618c0d HEAD -- src skills pyproject.toml uv.lock` is empty.

## 5. Sandboxes left in /tmp (kept for the scorer)
- /tmp/hirearchy-e5-probe-1792810812
- /tmp/hirearchy-e5-s1-1792811051
- /tmp/hirearchy-e5-s2-1792812864
- /tmp/hirearchy-e5-s3-1792814736
