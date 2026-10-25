# E7 teardown (after s1, s2, s3)

Facts only. No product code changed; nothing staged, committed or pushed. Snapshots: `safety-after.txt` (harness/safety-snapshot.sh, label teardown-after, 2026-10-25T09:02:50Z) and `ambient-teardown.txt` (harness/ambient_snapshot.sh, label teardown). Protocol md5 gate: `md5 evidence/protocol.md` = 0acc2b4191b8cbfa5f4bb6197b877de1 = `protocol.md5`. Procedure: E6's teardown, with the protocol's rename of the snapshot to `safety-after.txt` and the ambient snapshot `ambient-teardown.txt` (4.5.1, 4.8).

## 1. Study profiles in ~/.kiro/agents
At teardown start no study profile was present. Cross-check with the stream records:
- `s1/profiles/deletions.txt`: `hirearchy-study-e7-s1-assistant.json` deleted 2026-10-25T07:37:37Z, md5 21c7aaaf85ffc860ff21913b446c5b01.
- `s2/profiles/deletions.txt`: `hirearchy-study-e7-s2-assistant.json` deleted 2026-10-25T08:16:36Z, md5 2370f0ca03f767a340bcdb3b7415d2f8.
- `s3/profiles/deletions.txt`: `hirearchy-study-e7-s3-assistant.json` deleted 2026-10-25T08:59:47Z, md5 3a5c38de582e9ada0d697aa23764c386.
- The preflight and probe profiles went to a sandbox `KIRO_HOME`, not `~/.kiro/agents`.
Deleted in this step: none.

Remaining ~/.kiro/agents (6 files, all user-owned, untouched, md5s identical to `safety-before.txt`): agent_config.json.example, claude-opus-5.5.json, claude-sonnet-5.5.json, evolve.json, hirearchy-organization-9d66c1-web-fetch-web-search.json, telegram_bot.json.

## 2. Org kiro homes deleted in this step (under ~/Library/Application Support/hirearchy/kiro-home/)
- hirearchy-e7-s1-17929116-8da189031b753305
- hirearchy-e7-s2-17929140-9e603a789ac06f75
- hirearchy-e7-s3-17929164-224143a5119be2e6
Each held agents, enterprise-management, logs, session-index, sessions and settings (copies of the scheduler profiles are in `s<N>/profiles/`). kiro-home is now empty. Left, recorded, not deleted: the matching three dirs in `.../hirearchy/kiro-cwd/` (hirearchy-e7-s1-17929116-8da189031b753305, hirearchy-e7-s2-17929140-9e603a789ac06f75, hirearchy-e7-s3-17929164-224143a5119be2e6). The E4, E5 and E6 dirs there were not touched.

## 3. Processes
`ps` shows no process referencing `/tmp/hirearchy-e7-*`, and no E7 scheduler or MCP server. The `hirearchy mcp` processes running (pids 4212, 8117, 21748, 33122, 56978) all have `ORG_ROOT=/Users/aminalizadeh/organization`: the user's own sessions, not started by the study, not touched. Killed in this step: none.

## 4. Sandboxes in /tmp (kept for the scorer, read-only use)
- /tmp/hirearchy-e7-probe-1792910605
- /tmp/hirearchy-e7-s1-1792911600
- /tmp/hirearchy-e7-s2-1792914064
- /tmp/hirearchy-e7-s3-1792916437
All four are stopped: no process uses them.

## 5. Safety snapshot after vs before
`diff safety-before.txt safety-after.txt` (preflight-before 06:42:59Z vs teardown-after 09:02:50Z). Differences:
- header label, date, date_utc, epoch lines;
- mtime of `~/.kiro/memories` dir: Oct 25 06:41 to 09:02. `memories.db` is unchanged: md5 d91d954fc5ff92c41d0c285e812684c4 both times, size 102400, mtime Oct 25 03:39. Only the directory mtime moved (a transient entry created and removed in it). Recorded, not attributed; the study never touches this directory or the memory tool;
- mtime of `~/.kiro/agents` dir: Oct 24 18:40 to Oct 25 08:59, from the study's profile creation and deletion; the file list and every md5 are identical;
- mtime of the home dir `..` line (listing 145 entries both times): user activity.
Identical: every `~/.kiro/settings` md5; `~/.kiro/agents` file list and md5s; `~/.kiro/skills` listing (same 21 names; the ElevenLabs symlinks were already present at preflight); steering listing; `git status --porcelain`; the other orgs.
`/Users/aminalizadeh/organization`: file count 31, newest mtime 1792852894, tree digest 7ba5d9206b4c800d27a2f2d195137764, identical to `safety-before.txt` and to each stream's before/after. Not touched.
Per-stream snapshots: `s1`, `s2`, `s3` `safety-before.txt` vs `safety-after.txt` differ only in header lines, directory mtimes of `~/.kiro/memories` and `~/.kiro/agents`, and the home dir mtime line.
Ambient snapshot: `preflight/ambient-start.txt` vs `ambient-teardown.txt` differ only in the `~/.kiro/memories` dir mtime (1792910491 to 1792918947, 09:02:27Z) and so in the memories listing md5 (43f036a9548a2c3681e081a49c062467 to 8f7b57d4c8f16e2da5362d4b35f1446d). The skills listings (find -P and find -L) and the memories.db md5 are identical: no skill added, removed or changed over the whole study.
Result: no unexpected difference in `~/.kiro/skills`, `~/.kiro/agents` user files, `memories.db` or the user's org. The one recorded item is the `~/.kiro/memories` directory mtime.

## 6. Freeze
HEAD of /Volumes/workspace/hirearchy is 18a4531662060ddf0b78923edee8d61909bc9d6d. `git diff --stat 18a4531 HEAD -- src skills pyproject.toml uv.lock` is empty (0 bytes). `~/.kiro/skills/hirearchy/SKILL.md` md5 fd89a7fda55b8f342cf0306173c363fb (read-only check). `git status --porcelain`: `?? docs/research/` and `?? studies/E7-org-growth-0a4-recheck/` only; nothing staged. `.worktrees/` holds only `org-growth-0b`, untouched.
