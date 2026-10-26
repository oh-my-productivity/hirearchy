# G0 teardown (after m0-s1, m1-s1, m0-s2, m1-s2, m0-s3, m1-s3; step 9 of 11, workflow `wf_c415acfac4f09f84`)

Facts only. No product code changed; nothing staged, committed or pushed. Run 2026-10-26 ~09:17-09:20 UTC. Procedure: E7's teardown (`E7.../evidence/teardown.md`) plus protocol sections 6 and 9 (delete the dedicated M0 kiro homes after their evidence copy is verified). No replacement stream was approved or run; the six streams are the only ones. Snapshots: `safety-after.txt` (harness/safety-snapshot.sh, label teardown-after, 09:18:18Z), `ambient-teardown.txt` (harness/ambient_snapshot.sh, label teardown). Deletion record: `teardown-deletions.txt`. No credential was printed or recorded.

## 1. Evidence copy of the dedicated M0 HOMEs: verified, then deleted
For each of m0-s1, m0-s2, m0-s3 (homes `/tmp/hirearchy-g0-m0home-m0-s<N>-<epoch>`, each 44 files, 20 skill symlinks):
- `<stream>/assistant-session.json` and `<stream>/assistant-session-messages.jsonl` are **byte-identical** (`cmp`) to the home's `.kiro/sessions/<id>/sess_*/session.json` and `messages.jsonl` (messages 386 811, 422 596, 395 570 bytes).
- `<stream>/m0-home/setup.txt` (listing, settings md5s, skill symlinks) exists (7 025 bytes each), written at preparation.
- `<stream>/profiles/{creations,deletions}.txt` and the profile copies exist; each study assistant profile was deleted inside the home at stream end (`deletions.txt`); the home's `.kiro/agents` was empty at teardown.
- Memories covariate: each home held only kiro's own empty `memories/memories.db` (28 672 bytes, md5 `7517fcd420c7146f75db0d27f278b636` in all three, mtime = creation time): no memory was written in any M0 stream.
- **No credentials in the evidence copy.** The homes held no secrets, token, auth or mcp file (settings: `cli.json`, `cli.json.lock`, `session-response-indexing.json`, `survey_state.json`, `workflow_survey_state.json`). A fixed-string scan of the whole `evidence/` tree for the value of the inherited API key (value not printed) found no file; a pattern scan for `ksk_...`, `Bearer ...` and `accessToken/refreshToken` found no file.
- Nothing was incomplete, so no pause was needed. Approved replacements: none (none existed).

Deleted (exact paths, prefix guard `/tmp/hirearchy-g0-m0home-m0-s?-`, no process naming them): `/tmp/hirearchy-g0-m0home-m0-s1-1792990299`, `-m0-s2-1792995184`, `-m0-s3-1793000481`; each `exists_after=no` (`teardown-deletions.txt`).

## 2. Org kiro homes deleted (under `~/Library/Application Support/hirearchy/kiro-home/`)
Their session copies are in `<stream>/org-kiro-sessions/` (3 session dirs each) and the scheduler profiles in `<stream>/profiles/`. Deleted: `hirearchy-g0-m0-s1-17929-33e62c5799a5c0c7`, `-m0-s2-17929-5efce31e3a09a8e9`, `-m0-s3-17930-ec05daf2f4c4e5e1`, `-m1-s1-17929-9eefc3fd042dbc94`, `-m1-s2-17929-f6c7232ac7f305ec`, `-m1-s3-17930-56715956f09491c4`. `kiro-home` is now empty. Left, recorded, not deleted (as E7): the six matching dirs in `.../hirearchy/kiro-cwd/` (and the E4-E7 ones).

## 3. Study profiles in `~/.kiro/agents`
None present at teardown start. Cross-check: `m1-s1`, `m1-s2`, `m1-s3` `profiles/deletions.txt` record `hirearchy-study-g0-m1-s<N>-assistant.json` deleted (06:10:02Z, 07:37:51Z, 09:15:15Z); the M0 profiles lived in the M0 homes (deleted per stream, section 1); the preflight probe profile was deleted at preflight. Deleted in this step: none. `~/.kiro/agents` holds exactly the six pre-existing user files (agent_config.json.example, claude-opus-5.5.json, claude-sonnet-5.5.json, evolve.json, hirearchy-organization-9d66c1-web-fetch-web-search.json, telegram_bot.json), md5s identical to `safety-before.txt`. `ls ~/.kiro/agents | grep study` = 0.

## 4. Processes
No process references a `hirearchy-g0` path or a `/tmp` org root. Killed in this step: none.

## 5. Sandboxes kept (read-only use by the scorer)
`/tmp/hirearchy-g0-m0-s1-1792990299`, `-m0-s2-1792995184`, `-m0-s3-1793000481`, `-m1-s1-1792992820`, `-m1-s2-1792997653`, `-m1-s3-1793003475`, and the probe dirs `/tmp/hirearchy-g0-probe-m0-1792989651`, `/tmp/hirearchy-g0-probe-m1-1792989560`. All stopped.

## 6. Safety snapshot after vs before (`diff safety-before.txt safety-after.txt`)
Differences only: the label/date lines; the mtime of `~/.kiro/memories` (Oct 26 04:37 to 09:17, directory only) and of `~/.kiro/agents` (profile creation/deletion; file list and md5s identical); the `/tmp/hirearchy-g0-*` listing (now the kept sandboxes and probe dirs). Identical: every `~/.kiro/settings` md5, the global SKILL.md, `~/.kiro/memories/memories.db` (md5 `d7581238189dcb31ef2f6c70a1fb525a`), `~/.kiro/agents` files and md5s, `/Users/aminalizadeh/organization` (file count, newest mtime, digest), repo `git status`, HEAD, the empty freeze diff, the protocol md5, `/Volumes/workspace/orgs`.
Ambient: `preflight/ambient-start.txt` vs `ambient-teardown.txt` differ only in labels/date and the `~/.kiro/memories` directory mtime (1792989435 to 1793006225) with the memories listing md5 that follows from it (`d25ecb78...` to `e86a98af...`); skills listings (find -P, find -L) identical: no skill added, removed or changed. Recorded, not attributed (as E7): the owner's own sessions may write that directory; the study never touches it.

## 7. Final freeze check and gates
- `git -C /Volumes/workspace/hirearchy diff --stat 3c841bb9 HEAD -- src skills pyproject.toml uv.lock`: **empty** (0 bytes). HEAD `3c841bb9cdde666c6ea8b00bb2edfeae68c256db`, branch main. `git status --porcelain`: `?? docs/research/` and `?? studies/G0-noise-baseline/` only; nothing staged.
- Owner's `~/.kiro` md5s equal preflight (section 6); `~/.kiro/skills/hirearchy/SKILL.md` md5 `a3e46347b70a7ece5f734f70198c607f` (read with `md5 -q` only), as expected and as preflight.
- `md5 protocol.md` = `08cccd6458f5f418b4d388cb93d633b5` = `protocol.md5`; `harness/MD5SUMS` md5 `be21347995b821185a2adaba36d8390c` as in `freeze.txt`, every listed file matches (no MISMATCH).

Result: PASS. No safety check differs from preflight beyond the recorded directory mtimes.
