# P1 teardown (step 11, workflow `wf_9e81d83f470f71a8`; after I1, I2, I3, F1, F2, F3)

Facts only. No product code changed; nothing staged, committed or pushed; no stream started; no credential read, copied or printed. Run 2026-10-28 ~04:40-04:43 UTC. Procedure: G0's teardown (`../../G0-noise-baseline/evidence/teardown.md`) in its M1 form (no M0 home exists in P1). Files written: `safety-after.txt` (`harness/safety-snapshot.sh teardown-after`, 04:42:28Z), `ambient-teardown.txt` (`harness/ambient_snapshot.sh teardown`), `teardown-verify.txt` (evidence-copy check), `teardown-deletions.txt` (deletion record), `teardown-safety-diff.txt` and `teardown-ambient-diff.txt` (the raw diffs quoted below), this file.

## 1. Org kiro homes: evidence copy verified, then deleted
Each stream's org ran in its own kiro home under `~/Library/Application Support/hirearchy/kiro-home/`. Before deleting, `teardown-verify.txt` compared each home with the stream's evidence:
- Every file under `sessions/` is byte-identical (`cmp`) to `<stream>/org-kiro-sessions/` (133-169 files per stream). The only files of a home's `sessions/` not in the evidence are the three empty-or-internal `.index/.lock` files per stream (kiro's own lock files, not session content).
- Every file under `agents/` (the scheduler profiles of the org's lead and readers) is byte-identical to `<stream>/profiles/org-kiro-home--<name>.json` (F1 and F3 have the one reader profile, the other four streams two).
- The homes' `settings/cli.json(.lock)`, `logs/`, `session-index/` and `enterprise-management/` are not copied, as in G0. No file in them was opened.
- Guard: exact-prefix `hirearchy-p1-[if][123]-`; no process named any of these paths (`ps` count 0).

Deleted (all `exists_after=no`, `teardown-deletions.txt`; files before delete in brackets): `hirearchy-p1-f1-17931291-b710c83948597702` [171], `hirearchy-p1-f2-17931469-141f8d494151e346` [208], `hirearchy-p1-f3-17931528-f4b0de7112f5ea07` [181], `hirearchy-p1-i1-17931362-53c0ba0683b744d2` [182], `hirearchy-p1-i2-17931420-43a60f0d2f38c7be` [174], `hirearchy-p1-i3-17931574-331ae4382b4fa231` [192]. `kiro-home` is now empty. Left, recorded, not deleted (as G0): the matching dirs in `.../hirearchy/kiro-cwd/` (P1's six and the earlier studies' ones).

## 2. Study profiles in `~/.kiro/agents`
None present at teardown start; deleted in this step: none. Each stream deleted its own `hirearchy-study-p1-<stream>-assistant.json` at its end (`<stream>/profiles/deletions.txt`): I1 2026-10-27T22:38:29Z, I2 2026-10-28T00:19:00Z, I3 2026-10-28T04:39:07Z, F1 2026-10-27T21:21:09Z, F2 2026-10-28T01:56:41Z, F3 2026-10-28T03:12:25Z. The preflight probe profiles were deleted at preflight. `ls ~/.kiro/agents | grep -c -E 'study|p1'` = 0. The directory holds exactly the seven files of `safety-before.txt` (agent_config.json.example, claude-opus-5.5.json, claude-sonnet-5.5.json, evolve.json, explainer.json, hirearchy-organization-9d66c1-web-fetch-web-search.json, telegram_bot.json), md5s identical.

## 3. Sandboxes and scratch: kept, not deleted
As in G0 (`teardown.md` 5), the stream sandboxes stay in `/tmp`, read-only, for the scoring step: `assistant_facts.py` and `extract_mechanical.py` read each stream's `sandbox-path.txt`, and the protocol (section 7) says they "stay, read-only, until the teardown". Deleting them is irreversible and the scorer is the next step, so the call is the manager's: one `rm -r` of the paths below after scoring.
`/tmp/hirearchy-p1-I1-1793136275`, `-I2-1793142034`, `-I3-1793157452`, `-F1-1793129193`, `-F2-1793146944`, `-F3-1793152805` (6.6-8.1 MB each), `/tmp/hirearchy-p1-ambient-1793121877`, `/tmp/hirearchy-p1-probe-{I1-1793128490,I2-1793128614,F1-1793128368,F2-1793128740}`. All stopped; each sandbox's `.kiro/` holds only `settings/cli.json` and `skills/hirearchy/SKILL.md`, no study profile. Scratch outside these: none created by P1.

## 4. Processes
No process references a `hirearchy-p1` path or a P1 kiro home. Killed in this step: none. (The running `hirearchy mcp` processes are the owner's MCP servers.)

## 5. Safety, after against before (`teardown-safety-diff.txt` = `diff safety-before.txt safety-after.txt`)
| Check | Result |
|---|---|
| every `~/.kiro/settings` md5 (9 files) | unchanged |
| `~/.kiro/skills/hirearchy/SKILL.md` md5 | unchanged: `b10238639f48ab351fa44a06aed03ffb` (read with `md5` only; as expected) |
| `~/.kiro/memories/memories.db` md5 | unchanged: `f0aaf02a8a216c3a291a253d2c52d461`, size 126976, mtime Oct 27 07:41; equal to the `memories.db md5 before` of each of the six `setup.txt` and the `memories-md5-after` of each stream's `safety-after.txt` |
| `~/.kiro/memories` directory | mtime only: Oct 27 17:21 to Oct 28 04:41 (directory, not the file; listing md5 `8e7e2eb9...` to `94b63d8d...`); contents are still the single `memories.db` |
| `~/.kiro/skills/` | unchanged: `ls` identical; `find -P` and `find -L` listings identical (`teardown-ambient-diff.txt` shows no skills line) |
| `~/.kiro/agents` | file list and every md5 unchanged; only the directory mtime moved (Oct 27 03:50 to Oct 28 04:39: profile creation and deletion by the streams) |
| `/Users/aminalizadeh/organization` | unchanged: 31 files, newest mtime 1792852894, tree digest `7ba5d9206b4c800d27a2f2d195137764` |
| `/Volumes/workspace/orgs` | unchanged (listing identical; only its parent directory's mtime differs, line 101) |
| repo `git status --porcelain` | unchanged: ` M docs/design/org-growth-phase-1.md` (1 line added: 21.6, for step 13), `?? docs/research/`, `?? studies/P1-itemized-playbook/`; nothing staged |
| HEAD, protocol md5 | unchanged: `8bf7c69bb933bf2e1ecda5dc4ddbefde41eba565`; `protocol.md` = `protocol.md5` = `70237b0f3a829795a89d81c8eba7a7d6` |
| product freeze | empty (see 6) |
| `/tmp/hirearchy-p1-*` | `(none)` at preflight; now the kept sandboxes, ambient dir and probe dirs of section 3 |

Differences in the diff, all expected: the label/date lines; directory mtimes of `~/.kiro/memories`, `~/.kiro/agents`, the home directory (`..` of the user's org, line 74) and `/Volumes/workspace` parent of `orgs` (line 101); the `/tmp/hirearchy-p1-*` listing. The owner's own sessions may write the `memories` and home directories; the study did not touch them. No unexpected difference; nothing to restore or edit.

## 6. Freeze and gates
- `git -C /Volumes/workspace/hirearchy diff --stat 8bf7c69b HEAD -- src skills pyproject.toml uv.lock`: **empty** (0 bytes). HEAD `8bf7c69bb933bf2e1ecda5dc4ddbefde41eba565`, branch main.
- `harness/MD5SUMS`: md5 `d21508978d71e6d805f1760b25acb1b6` (as in every stream's `setup.txt`), 64 lines, 0 mismatches.
- `protocol.md` md5 = `protocol.md5` (above).

Result: PASS. The owner's `~/.kiro`, the user's org and `~/.kiro/skills/` are unchanged beyond the recorded directory mtimes; the study's profiles are deleted; the study's org kiro homes are deleted after a verified evidence copy; the sandboxes remain for scoring.
