# G0 stream m1-s2 run log (facts only; stream step 6 of 11, workflow `wf_c415acfac4f09f84`)

Arm M1 (the owner's ambient kiro memories as they are), stream 2 of 3. Label `m1-s2`. No scoring was done by this step; the measure scripts that
`finish_stream.sh` runs wrote their outputs to `measures/` and `rederived/` unread (the aggregation step reads and scores them).

## Gates and setup (`setup.txt`, `skill-check.txt`, `safety-before.txt`)
- Sandbox `S` = `/tmp/hirearchy-g0-m1-s2-1792997653` (epoch 1792997653). No dedicated kiro home (arm M1): the chat ran under `env -u KIRO_HOME` (`turn-NN.cmd.txt`).
  Set up 2026-10-26T06:54:14Z-06:54:30Z by `run_arm.sh m1 1 --setup`. The previous stream (m0-s2) had finished (`m0-s2/finish-steps.txt`: 0 failed steps); no process referenced any G0 sandbox.
- Gates (before the first turn): `protocol.md` md5 `08cccd6458f5f418b4d388cb93d633b5` = `protocol.md5`; `harness/MD5SUMS` 48 lines (md5 `be21347995b821185a2adaba36d8390c`), no mismatch; no amendment;
  HEAD `3c841bb9cdde666c6ea8b00bb2edfeae68c256db`; **freeze diff before: empty** (`setup.txt`); repo SKILL.md, global SKILL.md and workspace copy all `a3e46347b70a7ece5f734f70198c607f`;
  `claude-sonnet-5.5` listed; kiro-cli 2.33.0; other G0 streams running: 0.
- Profile `hirearchy-study-g0-m1-s2-assistant` created in `~/.kiro/agents` (md5 `263b4d964d1bdda45fa0022afe04e13e`, 06:54:14Z); it differs from m0-s1's profile only in `name`,
  `description` and `ORG_ROOT`; `kiro-cli agent validate` exit 0.
- After turn 1 (`ambient-context.txt`): `<memories>` block present **True** (19 global memories, 20 index titles listed incl. the spurious `TITLE`; the arm's recorded condition, not H3),
  `<steering-files>` False, "Workflow Orchestration" False; `session_start` 6 666 chars; `modelId` claude-sonnet-5.5, `effortLevel` high, `memoryConfig` read_write/reflection true.
  First `disclose_context` of the skill: turn 1, call #2, 06:55:00.212Z, uri = the workspace copy, md5 `a3e46347...` (valid). First `propose_org`: turn 2, call #9, 06:56:29Z;
  first `feedback`: turn 7, call #28, 07:13:51Z. So the skill was activated before both (stratum A by E7 4.4.1; `skill-check.txt` was written right after turn 1 and says n/a
  because no `propose_org` existed yet; the aggregation step records the stratum).

## Turns (14 user turns of the cap of 15; Lena's rule ids and facts are in `lena-lines.txt`; every `kiro-cli chat` call exit 0)
| T | UTC start-end | Lena (rule) | Assistant outcome |
|---|---|---|---|
| 1 | 06:54:44-06:55:18 | H1 | 11 elicitation items (incl. an offer to write the 19 Oct memo first) |
| 2 | 06:55:55-06:56:38 | H2 + L-INF + L-VAGUE + L-FIRST (= E7 s1 t02 bytes) | PLAN FOR YOU, Budget 12 per request, one T-WARN warning (16), T-BUDGETQ as the block's last line; the assistant adds nothing of its own |
| 3 | 06:57:14-07:02:36 | **L-BUDGET-Q + H5 (adjusted)**: "Keep it as it is. Great, approve. I'll wait." | team ran (9 runs); memo 1 drafted and reviewed, **not copied**, text not shown, two Due questions (Sam, Marta) first (D8 draft) |
| 4 | 07:03:21-07:03:43 | factual answers: "Sam's should be 2026-10-09. Marta's should be 2026-10-14." | first spend question (up to 14, 2 over 12) |
| 5 | 07:04:18-07:07:47 | L-FUND ("Yes, fund it - but please keep an eye on the cost.") | rework passes; **not copied**, one question first (a "Notes on dates" sentence); D8 draft |
| 6 | 07:08:25-07:08:48 | L-KEEP ("Keep it as it is.") | **memo 1 first delivery** (copy `deliverables/memo-2026-10-05.md`, md5 `77e20d78...`, dates = key, no Summary line) |
| inj | 07:09:39-07:12:39 | (injection, no turn) | injected task `20261026T070939625591-root-ca4f`, done, 5 of 6 runs |
| 7 | 07:13:27-07:14:00 | H6, Summary-only form (= E7 s1 t05 / s2 t06 / s3 t06 bytes) | recorded the reject; asked one contract item (C1); a rework would cost about 5 more runs (conditional, no question) |
| 8 | 07:14:36-07:18:15 | "Yes, add it." | contract v2 recorded; memo 1 rework **delivered** (copy md5 `99388d9e...`); told Lena about the unrequested rework (rejected it, 5 runs its own spend) |
| 9 | 07:19:04-07:22:30 | memo-1 accept (dropped form) + L-INJ + next memo + I'll wait (= E7 s1 t07 bytes) | memo 2 drafted, **not copied**, 5 questions first |
| 10 | 07:23:15-07:26:31 | "It's just an action, not a decision. Yes, that counts. No need for 'probably'. Sam's 2026-10-21 is right. Lee's none is right. Keep it as it is." | memo 2 reworked, **not copied**, one question first (kept "Notes on unclear items" section) |
| 11 | 07:27:10-07:27:34 | L-KEEP | **memo 2 delivered** (copy md5 `43489270...`) |
| 12 | 07:28:24-07:31:31 | memo-2 accept + L-INJ + next memo (E7 s1 t09 plus L-INJ's sentence) | memo 3 drafted, **not copied**, 4 questions first |
| 13 | 07:32:31-07:36:07 | "No, nothing for Marta to do there, leave it out. Lee's should be 2026-10-30. Yes, that counts. Sam's should be none. Keep it as it is." | **memo 3 delivered** (copy md5 `d151c38c...`) |
| 14 | 07:36:48-07:37:13 | memo-3 accept + L-INJ: "This version is right now, thanks - keep it. I don't know anything about that rework - I didn't ask for it." | recorded the accept; no question to Lena; stream ended |

(Times are `turn-times.txt`'s wall-clock start-end of each `kiro-cli chat` call, local WET = UTC.) L-BUDGET-Q used once (turn 3). Facts that decided every line are in `lena-lines.txt`.
The L-INJ sentence was added to the turn-12 and turn-14 accepts because the assistant's preceding output mentioned the unrequested rework as a statement (the same treatment as m1-s1 turns 8-9);
it is a protocol line (E7 4.10, L-INJ), not coaching. Judgment calls the aggregation step may want to see: turn 10 Q1 answer is "It's just an action, not a decision." (without a leading "No,"), because the question was "keep both, or in one place only?";
turn 13 Q3 answers "Yes, that counts. Sam's should be none." (D15: Sam, 2026-10-19 meeting: none).

## Org runs (`run-counts-by-turn.txt`, `cost.txt`)
- 44 org runs (39 counted toward the cap of 45; 5 in the injection window). 44 run logs, all `# exit 0 after`, 44 of 44 `# cmd:` lines with exactly one `--model claude-sonnet-5.5` and one `--effort high`;
  no throttle mark, no credit note, no exit 75, no `[run error]`, no `# kiro:` failure line. All 44 `# cwd:` under `~/Library/Application Support/hirearchy/kiro-cwd`.
  `model_check.sh org` OK after every turn from turn 3 and before the injection; `model_check.sh assistant` OK after every turn; `model_check.sh all` OK (`model-checks.txt`).
- Assistant credits (`cost.txt`): 24.7410 over 14 turns. Org-run credits are for the aggregation step.
- `hirearchy check` (`observe-check.txt`): all checks passed, exit 0.

## Injection (`injection/`)
- Script md5 `1c4e7824e448a3a34e24a7b759a59fcd`; run once, after the turn that delivered memo 1 (turn 6; turns 3-5 were drafts, D8), before Lena's turn 7;
  `--revises 20261026T070444333415-root-80c3` (identification in `injection/memo1-identification.txt`); window `2026-10-26T07:09:39 2026-10-26T07:12:39`
  (`window.txt`, in `S/injection/` and copied); 4 polls, 2 quick replies, settled; `source: relayed`, budget 6; no scheduler was running when it started (`scheduler.exit` `finished: no open tasks`
  after turn 6). Model checks (org, assistant) were run right before: OK.

## Schedulers and signals (`scheduler-survival.txt`)
- 8 schedulers (7 started by the assistant's server, 1 by the injection script), each ended with `scheduler.exit` `finished: no open tasks`; 0 `scheduler.signal`; 0 `run.orphan`;
  0 killed runs. No scheduler was running at the end of any assistant turn (each exited 5.3-10.5 s before the end of the turn it began in; the injection's exited between turns). **No unexplained scheduler.signal.**

## Quality view
- `quality --json` after turns 3-14 (`quality/turn-NN.json`) and at the end (`quality/end.json`): 13 calls, all exit 0, recorded in `quality/calls.txt`; turns 1-2: no org yet, not run.
  `rederive_quality.py --compare`: `compared 272 keys, 0 mismatches` (`rederived/mismatches.txt`; no F-G0-1 occurrence).

## Failed calls, harness notes
- No harness failure, no retry, no boundary failure (every `run_turn.sh` returned its last line). No usage-limit, quota or throttle text in any turn's stdout or stderr.
- `finish_stream.sh`: 0 failed steps (`finish-steps.txt`).
- The injection script's console output is Python logging noise (`INFO Processing request ...`); the injection's own log is `injection/injection-log.txt`. `text-identity.txt` and `window-runs.txt` were written by `injection_files.py` during the finish.
- Harness fact: the turn-6 and turn-8 `after_turn.sh` records are unaffected by the injection (the injection ran between turn 6's `after_turn.sh` and turn 7).

## Cleanup and safety
- Profile `hirearchy-study-g0-m1-s2-assistant` copied to `profiles/`, compared (cmp), deleted from `~/.kiro/agents` at 2026-10-26T07:37:51Z (`profiles/creations.txt`, `deletions.txt`);
  `~/.kiro/agents` holds exactly the six pre-existing files again.
- `safety-before.txt` / `safety-after.txt` / `safety-diff.txt`: the diff is the label line, two directory mtimes and the new `/tmp/hirearchy-g0-m1-s2-*` directory name only. Every
  md5 line is identical before and after: the owner's `~/.kiro/settings/*` (`cli.json` `8b4f0599...`, `cli.json.lock` `9070b152...`), `~/.kiro/agents/*`, the global SKILL.md
  (`a3e46347b70a7ece5f734f70198c607f`) and `memories.db` (`d7581238189dcb31ef2f6c70a1fb525a`, 114 688 bytes, mtime 04:18Z unchanged). `/Users/aminalizadeh/organization` unchanged in the snapshot.
- Ambient snapshots (`ambient/`): skills listings and `memories.db` md5 identical in all snapshots (setup, 14 before/after pairs, end). One difference: the memories directory listing md5
  changed once (`ff482552...` -> `92db35d9...`, during turn 1, the directory mtime moved: kiro's own session start in the owner's home, as in m1-s1 and the preflight probe); the file `memories.db` did not change. Recorded, not attributed.
- **Freeze after: `git diff --stat 3c841bb9 HEAD -- src skills pyproject.toml uv.lock` is empty** (`setup.txt`, "AFTER the last turn", 07:37:51Z); HEAD unchanged; md5 gates held
  (`protocol.md` and 48 harness lines, 0 mismatches); `docs/research/` and `studies/G0-noise-baseline/` untracked, nothing staged, committed or pushed. kiro-cli 2.33.0 throughout.
  No process references the sandbox.
- The sandbox `/tmp/hirearchy-g0-m1-s2-1792997653` is left in place for the aggregation and teardown steps.

## Validity against design 20.1 / protocol 8 (E7 11 H1-H8)
H1 no assistant call failed (14 of 14 exit 0). H2 skill md5 `a3e46347...` on disclosure, the rule holds in M1 (global = workspace = repo), server bound to `S/org`.
H3 workspace settings md5 `05d30ccbfd35530747c8a542eb67985c`, no steering block, no "Workflow Orchestration"; the memory index is present, the arm's recorded condition.
H4 every seat claude-sonnet-5.5 / high (44 run logs, 14 assistant invocations with `--effort high`, session `modelId`/`effortLevel`, `reasoningModelId` `qdev::claude-sonnet-5.5`).
H5 injection as specified (md5, once, after the delivery turn, correct `revises`; text identity checked in `injection/text-identity.txt`). H6 no unknown actor (events: the assistant's servers, the schedulers, the injection server,
root `cli` reads of the harness); empty freeze diff; one kiro-cli version (2.33.0). H7 only protocol lines (L-BUDGET-Q once, turn 3). H8 no run failed or was throttled; no usage-limit or quota error.
**Verdict: m1-s2 is VALID** (judged against section 20.1 only; not scored).
