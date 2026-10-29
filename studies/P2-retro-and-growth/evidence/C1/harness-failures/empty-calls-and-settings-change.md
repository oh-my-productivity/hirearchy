# C1: empty-argument calls and the owner's settings files (facts only; written at the finish, 2026-10-29)

Requested by `manager-decision-row-C1-t22.md` section 2. Stat and md5 only: `~/.kiro/settings/cli.json` and `mcp.json` were never opened or edited.

## C1 totals (`C1/empty-calls.txt`, `C1/turn-NN.stderr.txt`)
- Session-store empty-argument failed calls: **35** (tool_call 34, tool_load 1). The stderr grep ('is not available') adds up to the same 35 over the 27 turns.
- First failed call in turn 2 (13:33Z); 0 in turn 1. P1: 0 in all six streams. P2's preflight probe: 0 in four sessions.
- Cost: each failed call is a no-op tool call inside the assistant session. In the records: no turn had to be repeated because of one, no org run was started or lost by one,
  and the assistant mentioned one itself only in turn 5 ('Calling with proper arguments this time'). The credits of the assistant session include the extra tokens (no separate figure).

## Per-turn counts (C1), by the turn's UTC start
| Turn | Start (UTC) | New | Cumulative | tool_call | tool_load | stderr 'is not available' (this turn) |
|---|---|---|---|---|---|---|
| 1 | 13:31:11 | 0 | 0 | 0 | 0 | 0 |
| 2 | 13:33:18 | 1 | 1 | 1 | 0 | 1 |
| 3 | 13:34:50 | 1 | 2 | 2 | 0 | 1 |
| 4 | 13:38:20 | 0 | 2 | 2 | 0 | 0 |
| 5 | 13:43:36 | 2 | 4 | 3 | 1 | 2 |
| 6 | 13:44:41 | 1 | 5 | 4 | 1 | 1 |
| 7 | 13:47:56 | 1 | 6 | 5 | 1 | 1 |
| 8 | 13:49:29 | 1 | 7 | 6 | 1 | 1 |
| 9 | 13:52:25 | 0 | 7 | 6 | 1 | 0 |
| 10 | 13:55:28 | 0 | 7 | 6 | 1 | 0 |
| 11 | 13:58:05 | 3 | 10 | 9 | 1 | 3 |
| 12 | 14:00:57 | 2 | 12 | 11 | 1 | 2 |
| 13 | 14:03:50 | 0 | 12 | 11 | 1 | 0 |
| 14 | 14:04:54 | 1 | 13 | 12 | 1 | 1 |
| 15 | 14:08:02 | 0 | 13 | 12 | 1 | 0 |
| 16 | 14:10:46 | 0 | 13 | 12 | 1 | 0 |
| 17 | 14:13:17 | 3 | 16 | 15 | 1 | 3 |
| 18 | 14:16:28 | 0 | 16 | 15 | 1 | 0 |
| 19 | 14:18:07 | 6 | 22 | 21 | 1 | 6 |
| 20 | 14:21:20 | 0 | 22 | 21 | 1 | 0 |
| 21 | 14:22:26 | 1 | 23 | 22 | 1 | 1 |
| 22 | 14:23:24 | 1 | 24 | 23 | 1 | 1 |
| 23 | 14:31:54 | 4 | 28 | 27 | 1 | 4 |
| 24 | 14:34:04 | 0 | 28 | 27 | 1 | 0 |
| 25 | 14:35:07 | 4 | 32 | 31 | 1 | 4 |
| 26 | 14:38:46 | 1 | 33 | 32 | 1 | 1 |
| 27 | 14:39:48 | 2 | 35 | 34 | 1 | 2 |

## The owner's settings files, from every safety snapshot (md5 as printed by `safety-snapshot.sh`; mtimes by `stat` now, 14:4xZ)
| Snapshot (file) | cli.json md5 | mcp.json md5 |
|---|---|---|
| `safety-before.txt` (preflight-before, 10:13Z) | 8d75907973b5f3720d5bd4de5eaff7d8 | 767d7d34ab140172ef643ffcc7ca39e1 |
| `preflight-safety-after.txt` (10:34Z) | 8d75907973b5f3720d5bd4de5eaff7d8 | 767d7d34ab140172ef643ffcc7ca39e1 |
| `R1/safety-before.txt` (R1 setup, about 12:11Z) | 8d75907973b5f3720d5bd4de5eaff7d8 | 767d7d34ab140172ef643ffcc7ca39e1 |
| `R1/safety-after.txt` (R1 finish, about 13:27Z) | f21924126253d2f829fd25ad189e4825 | 9ca5275ee24dfa57e57c763e717e2387 |
| `C1/safety-before.txt` (C1 setup, 13:30Z) | f21924126253d2f829fd25ad189e4825 | 9ca5275ee24dfa57e57c763e717e2387 |
| `C1/safety-after.txt` (C1 finish, 14:41Z) | f21924126253d2f829fd25ad189e4825 | 9ca5275ee24dfa57e57c763e717e2387 |
- mtimes now: `cli.json` 2026-10-29T12:35:19Z, `mcp.json` 2026-10-29T12:38:08Z (as the manager read in `R1/safety-diff.txt`). The snapshots print md5s, not file mtimes, so the mtime of
  each earlier snapshot is not on record; the md5 pairs bracket the change between R1's setup (about 12:11Z) and R1's finish.
- Both files are identical in C1's before and after snapshots: **they did not change during C1**; C1 ran entirely after the 12:35Z and 12:38Z changes (C1 turn 1 started 13:31Z).
- `C1/safety-diff.txt` differs only in: the label, `memories.db` (see below), the directory mtimes of `~/.kiro/memories`, the study's folders, `~/.kiro/skills/hirearchy` absent in the
  after-snapshot because `finish_stream.sh` takes it before the restore (restored 14:41:27Z, md5 443e1bc4..., checked), and the new sandbox name under `/tmp/hirearchy-p2`.

## R1 for comparison (`R1/empty-calls.txt`): 0 in turns 1-9 (12:12-12:34Z), first failures in turn 10 (12:44Z; 2), 23 in total (tool_call 22, tool_load 1). R1's turn 9 ended at about 12:39Z, after both changes.
C1's failures start at turn 2, i.e. 2 minutes into a stream that began 55 minutes after the changes.
This file states the timeline; it takes no position on cause or on validity (the manager's section 2 reserves that for the stage gate).
