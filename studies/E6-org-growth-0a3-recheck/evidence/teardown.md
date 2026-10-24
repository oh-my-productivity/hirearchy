# E6 teardown (after s1, s2, s3)

Facts only. No product code changed, nothing staged, committed or pushed. Snapshot: `teardown-safety-after.txt` (harness/safety-snapshot.sh, label teardown-after, 2026-10-24T17:45:41Z). Protocol md5 gate: `md5 -q protocol.md` = 31410741088523af23875aef34167bac = `protocol.md5`.

## 1. Study profiles in ~/.kiro/agents
At teardown start no study profile was present. Cross-check:
- `preflight-profiles.txt`: probe profile created and deleted by the preflight.
- `s1/profiles/deletions.txt`: `hirearchy-study-e6-s1-assistant.json` deleted 2026-10-24T16:23:52Z.
- `s2/profiles/deletions.txt`: `hirearchy-study-e6-s2-assistant.json` deleted 2026-10-24T17:01:54Z.
- `s3/profiles/deletions.txt`: `hirearchy-study-e6-s3-assistant.json` deleted 2026-10-24T17:40:21Z.
Deleted in this step: none.

Remaining ~/.kiro/agents (all user-owned, untouched): agent_config.json.example, claude-opus-5.5.json, claude-sonnet-5.5.json, evolve.json, hirearchy-organization-9d66c1-web-fetch-web-search.json, telegram_bot.json

## 2. Org kiro homes deleted in this step (under ~/Library/Application Support/hirearchy/kiro-home/)
- hirearchy-e6-s1-17928558-6a43f953dd5df144
- hirearchy-e6-s2-17928592-fa2d6cf9a0cd7209
- hirearchy-e6-s3-17928615-64110e24af48ba66
kiro-home is now empty. Left, recorded (not deleted): the matching three dirs in ~/Library/Application Support/hirearchy/kiro-cwd/ (hirearchy-e6-s1-17928558-6a43f953dd5df144, hirearchy-e6-s2-17928592-fa2d6cf9a0cd7209, hirearchy-e6-s3-17928615-64110e24af48ba66). The E4 and E5 dirs in kiro-cwd were not touched.

## 3. Processes
`ps` shows no process referencing `/tmp/hirearchy-e6-*`, no E6 scheduler and no E6 MCP server. The `hirearchy mcp` processes still running (pids 7459, 82367, 13861, 21748, with their `uv` parents) all have `ORG_ROOT=/Users/aminalizadeh/organization`: they are the user's own sessions, not started by the study, and were not touched. Killed in this step: none.

## 4. Safety snapshot after vs before
Compared with `s3/safety-before.txt` and `preflight-safety-before.txt`. Differences:
- header label/date/date_utc/epoch lines;
- `~/.kiro/memories/memories.db`: md5 now 4b45c15d0e0b9291f0137589ad35bc30 (was 3f53a1d90a590b253fc33aaa1c11342c), mtime Oct 24 18:26 (was Oct 21 05:43), size 94208 unchanged. The change falls in s3's window (s3 began 18:05 local) and the study never touches this file or the memory tool. Recorded, not attributed; cause unknown to this step. The `~/.kiro/memories` dir mtime changed with it.
- `~/.kiro/skills` listing: new symlinks `agents, dubbing, music, onboarding, realtime, setup-api-key, sound-effects, speech-engine, speech-to-text, text-to-speech, update-skills-from-changelog, voice-changer, voice-isolator`, created 2026-10-24 18:25:38-39 local (pointing to `../../.agents/skills/*`). The study created none of them (it never writes in `~/.kiro/skills/`); they look like an ElevenLabs skills install by another session of the user. Recorded, not attributed, not touched. `~/.kiro/skills/hirearchy` is unchanged.
- mtime of `~/.kiro/agents` (now Oct 24 18:40) from study profile creation and deletion; the file list and every md5 in it are identical.
- mtime of the home dir `..` line (listing, 141 to 145 entries): user activity.
Identical: all ~/.kiro/settings md5s, agents file list and md5s, steering listing, repo `git status --porcelain` for `docs/research/`.
/Users/aminalizadeh/organization: file count 31, newest mtime 1792852894, tree digest 7ba5d9206b4c800d27a2f2d195137764, identical to `s3/safety-before.txt` (and to the preflight). Not touched.
Skill `/Users/aminalizadeh/.kiro/skills/hirearchy/SKILL.md` md5: b2469838032374807e3608631c9fb1d2 (expected value; equals the repo's `skills/hirearchy/SKILL.md`).
Two changes (memories.db, ~/.kiro/skills symlinks) are unexplained by the study and are outside anything it writes.

## 5. Freeze
HEAD of /Volumes/workspace/hirearchy is 18c4ffb7d2dc0ea2a04b07c478397c9d1c89ad29. `git diff --stat 18c4ffb HEAD -- src skills pyproject.toml uv.lock` is empty (0 bytes). `git status --porcelain`: `?? docs/research/` and `?? studies/E6-org-growth-0a3-recheck/` only; nothing staged.

## 6. Sandboxes left in /tmp (kept for the scorer)
- /tmp/hirearchy-e6-probe-1792855143
- /tmp/hirearchy-e6-s1-1792855848
- /tmp/hirearchy-e6-s2-1792859296
- /tmp/hirearchy-e6-s3-1792861552
