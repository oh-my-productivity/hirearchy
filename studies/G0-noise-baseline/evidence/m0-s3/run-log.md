# G0 stream m0-s3 run log (facts only; stream step 7 of 11, workflow `wf_c415acfac4f09f84`)

Arm M0 (dedicated kiro home, no memories index), stream 3 of 3. Label `m0-s3`. No scoring was done by this step; the measure scripts that
`finish_stream.sh` runs wrote their outputs to `measures/` and `rederived/` unread (the aggregation step reads and scores them).

## Gates and setup (`setup.txt`, `skill-check.txt`, `safety-before.txt`)
- Sandbox `S` = `/tmp/hirearchy-g0-m0-s3-1793000481`; dedicated kiro home `/tmp/hirearchy-g0-m0home-m0-s3-1793000481` (`m0-home-path.txt`, `m0-home/`).
  Set up 2026-10-26T07:41:21Z-07:41:40Z by `run_arm.sh m0 1 --setup` (next label computed by the harness: `m0-s3`; previous stream m1-s2 had finished at 07:39).
- Gates (before the first turn): `protocol.md` md5 `08cccd6458f5f418b4d388cb93d633b5` = `protocol.md5`; `harness/MD5SUMS` 48 lines, no mismatch; HEAD
  `3c841bb9cdde666c6ea8b00bb2edfeae68c256db`; **freeze diff before: empty** (`git diff --stat 3c841bb9 HEAD -- src skills pyproject.toml uv.lock` printed nothing);
  repo SKILL.md, global SKILL.md (read by md5 only), workspace copy and M0 copy all `a3e46347b70a7ece5f734f70198c607f`; `claude-sonnet-5.5` listed; kiro-cli 2.33.0;
  no other G0 process running. Safety snapshot before taken (`safety-before.txt`, 07:41:21Z), then the ambient snapshot (`ambient/setup.txt`).
- Profile `hirearchy-study-g0-m0-s3-assistant` created in the M0 home's `agents/` (md5 `c833c6e93ea60330b70bcd6023a0dc3a`, 07:41:22Z), `kiro-cli agent validate` exit 0; it differs from
  m0-s1's profile only in `name`, `description`, `ORG_ROOT`.
- The M0 home authenticated (turn 1 exit 0; no credential was copied, printed or recorded).
- After turn 1: `ambient-context.txt`: `<memories>` block present **False**, `<steering-files>` False, "Workflow Orchestration" False; `session_start` 2 026 chars;
  `modelId` claude-sonnet-5.5, `effortLevel` high. First `disclose_context` of the skill: turn 1, call #1, 07:42:13Z, uri = the workspace copy, md5 `a3e46347...` (valid).
  First `propose_org`: turn 2, call #8, 07:43:58Z; first `feedback`: turn 5, call #31. So the skill was activated before the first `propose_org` (stratum A by E7 4.4.1;
  `skill-check.txt` was written right after turn 1 and says n/a because it ran before any `propose_org` existed; the aggregation step records the stratum).

## Turns (15 user turns = the cap of 15; Lena's rule ids and facts are in `lena-lines.txt`; all exit 0)
| T | UTC start-end | Lena (rule) | Assistant outcome |
|---|---|---|---|
| 1 | 07:41:55-07:42:31 | H1 | 7 elicitation items (one of them asks whether the notes folder is the right one) |
| 2 | 07:43:22-07:44:08 | H2 + folder answer + L-INF + L-VAGUE (no L-FIRST: no first memo proposed) | PLAN FOR YOU, Budget 12 per request, one T-WARN warning (16), the block ends with T-BUDGETQ; no first request in the plan; the assistant's own words recommend no number |
| 3 | 07:44:47-07:48:20 | **L-BUDGET-Q + H5 (full form)**: "Keep it as it is. Great, approve. Please do this week's: 2026-10-05.md. I'll wait." | team built, request run (5 runs); memo 1 drafted in a code block, **not copied** ("I haven't copied it to `deliverables` yet"), 4 questions asked first (D8 draft) |
| 4 | 07:49:16-07:52:29 | factual answers in the order asked (Sam 2026-10-09; Lee none right; Marta 2026-10-14; L-KEEP) | human rework `root-ce42` (5 runs); **memo 1 first delivery** (copy `deliverables/memo-2026-10-05.md`, md5 `16b0d84a...`, Sam 2026-10-09, Marta 2026-10-14, no Summary line) |
| inj | 07:53:26-07:56:35 | (injection, no turn) | injected task `20261026T075326752629-root-9de8`, ended **done** (3 questions for the client, artifacts withheld), 5 of 6 runs |
| 5 | 07:57:09-07:57:41 | H6, Summary-only form (= E7 s2 t06 bytes) | recorded the reject; asked a lasting-rule item (C9) |
| 6 | 07:58:14-07:59:08 | "Yes, add it." | rule added (C9, contract v2); told Lena about a second rework she did not ask for; asked for 5 more runs |
| 7 | 07:59:46-08:03:39 | L-FUND + L-INJ | Summary rework (5 runs) came back **blocked** (C9 not met: title line, Attendees line); recommended a layout and asked for about 3 more runs |
| 8 | 08:04:19-08:04:53 | "No more spend, please deliver as is." + L-INJ | no new delivery, no verdict recorded ("deliver as is isn't an accept"); control returned with no question |
| 9 | 08:05:31-08:08:53 | **L-ASIS** + L-INJ + next memo + I'll wait | memo 2 drafted (reviewer 8 of 8, 5 runs), not copied, 2 questions |
| 10 | 08:09:31-08:13:27 | factual answers (Sam counts, no 'probably', 2026-10-21 right; Lee none right) | Sam wording changed (5 runs, reviewer 10 of 10); memo 2 delivered (copy md5 `ee1b2442...`) |
| 11 | 08:14:06-08:19:10 | memo-2 accept + next memo + I'll wait (= E7 s2 t10 bytes) | memo 3 drafted (reviewer 8 of 8, 9 of 12 runs), not copied, 3 questions |
| 12 | 08:19:52-08:20:17 | factual answers (Lee 2026-10-30; Marta row out; Sam counts) | applying them needs about 5 runs (over the 12): asked for approval |
| 13 | 08:20:52-08:25:08 | L-FUND | rework (5 runs); memo 3 delivered (copy md5 `6ac1e8d5...`), reviewer 9 of 9; 14 runs of 12 |
| 14 | 08:25:43-08:26:21 | final accept (= E7 s3 t13 bytes) | recorded the accept; asked "Do you want that?" (a standing note on hedged commitments) |
| 15 | 08:27:01-08:27:19 | L-KEEP (= E7 s3 t05 bytes) | did not add the note; **stream ended at the cap of 15 user turns** (4.7), after Lena's accept of memo 3 and the answer to the assistant's last question |

## Org runs (`run-counts-by-turn.txt`, `cost.txt`)
- 44 org runs (39 counted toward the cap of 45; 5 in the injection window). 44 run logs, all `# exit 0`, all `# kiro: run started (engine v3)`, 44 of 44 `# cmd:` lines with
  `--model claude-sonnet-5.5`, `--effort high` and `--v3`; no throttle, credit, exit 75, usage-limit, quota or `# kiro:` failure line in any run log or turn stderr/raw output
  (the words "rate limit" occur in turn texts only as the memos' topic, the rate limiter). `model_check.sh org` and `assistant` OK after every turn and before the injection;
  `model_check.sh all` OK (44 org run logs, 15 assistant invocations, session `modelId` claude-sonnet-5.5 / `effortLevel` high, `reasoningModelId` `qdev::claude-sonnet-5.5`).
- Assistant credits (cost.txt): 26.8582 over 15 turns. Org-run credits are for the aggregation step.
- `hirearchy check` (`observe-check.txt`): all checks passed, exit 0.

## Injection (`injection/`)
- Script md5 `1c4e7824e448a3a34e24a7b759a59fcd`; run once, after the turn that delivered memo 1 (turn 4; the turn-3 output was a draft: D8), before Lena's turn 5;
  `--revises 20261026T074936893313-root-ce42` (identification in `injection/memo1-identification.txt`: the human rework whose done result `...-lead-1cb9` names the delivered file); window
  `2026-10-26T07:53:26 2026-10-26T07:56:35` (`S/injection/window.txt`, written by the stream step after the script returned, copied to `injection/`); title/note md5s match
  (`injection/text-identity.txt`); 4 polls, 2 quick replies, settled; `source: relayed`, budget 6; `measures/injection_files-output.txt`: 5 window runs. The injected task ended `done`
  (not blocked as in m0-s2), "3 questions for the client", artifacts withheld.

## Schedulers and signals (`scheduler-survival.txt`)
- 8 schedulers (7 started by the assistant's server, 1 by the injection script), each with `scheduler.exit` `finished: no open tasks`; 0 `scheduler.signal`; 0 `run.orphan`;
  0 killed runs; none was running at the end of any assistant turn (`sleep 20` boundary kept: 15 of 15 turns, 20.0 s each). **No unexplained scheduler.signal.**

## Quality view
- `quality --json` after turns 3-15 (`quality/turn-NN.json`, `calls.txt`: 14 calls in all) and at the end (`quality/end.json`); turns 1-2: no org yet, not run (recorded "no org yet").
  End: 1 service, 3 cases (`root-e415` blocked, runs 20, relayed 5, user cost 15 of 15 approved; `root-3e5e` done, 10 runs; `root-c118` done, 14 runs), 9 deliveries, 1 escape,
  repeat alarm `no` (subjects C9, R1; none fired), cost alarm `no`. `rederive_quality.py --compare`: `compared 269 keys, 0 mismatches` (`rederived/mismatches.txt`; no F-G0-1 occurrence).

## Failed calls, harness notes
- No harness failure, no retry, no boundary failure, no `harness-failures/`. Every `kiro-cli chat` call exit 0. The first attempt to send turn 4 was a facilitator typing error (the shell variable
  naming the prompt file was empty in that tool call): `run_turn.sh` printed its usage line and exited 2 before doing anything (no prompt copy, no `turn-04.*` file, no chat call, no ambient
  snapshot); turn 4 was then sent once, normally. It is not a user turn and not a retry of a harness failure.
- `finish_stream.sh`: 0 failed steps. The sandbox is left in place; the M0 home is left for the teardown (step 9).
- Judgement calls recorded in `lena-lines.txt`:
  - turn 2: the assistant asked whether the notes folder was the right one (not covered by H2): answered with the anything-else rule ("Yes, that's the right notes folder."), placed first (answers in the order asked).
  - turn 8: the assistant's question "Should I go with that?" carried a second spend request (about 3 more runs, "about 18 of the 12 approved"), so the decline was used and the layout part was not answered separately.
  - turns 11 and 14: the assistant's closing line "No rework you didn't ask for ran this time." was read as a statement, not a mention of the injected rework, so L-INJ was not used; the alternative reading is recorded in the turn-11 line.
  - turn 15: the assistant's last question (a standing note on hedged commitments) was answered with L-KEEP; the stream then ended at the cap.
- Draft turns (D8): turns 3, 9, 11 and 12 showed a version with its text and a "not copied" statement and asked first (drafts, not deliveries); deliveries by copy: turn 4 (memo 1), turn 10 (memo 2), turn 13 (memo 3).

## Cleanup and safety
- Profile `hirearchy-study-g0-m0-s3-assistant` copied to `profiles/`, compared, deleted from the M0 home at 2026-10-26T08:27:58Z (`profiles/deletions.txt`, creation in `profiles/creations.txt`).
  Nothing was created or deleted in `~/.kiro/agents`; it holds the six pre-existing files.
- `safety-before.txt` / `safety-after.txt`: the diff (`safety-diff.txt`) is the label line and two new `/tmp/hirearchy-g0-m0-s3-*` / `m0home-m0-s3-*` directory names only. The owner's `~/.kiro` md5 set
  (settings, agents, skills listing, `memories.db` `d7581238189dcb31ef2f6c70a1fb525a`) and the global SKILL.md (`a3e46347b70a7ece5f734f70198c607f`) are identical before and after;
  `/Users/aminalizadeh/organization` unchanged in the snapshot.
- **Freeze after: `git diff --stat 3c841bb9 HEAD -- src skills pyproject.toml uv.lock` is empty** (`setup.txt`, "AFTER the last turn", 08:27:58Z); HEAD unchanged; md5 gates held after the last turn
  (protocol.md and 0 harness mismatches); `docs/research/` and `studies/G0-noise-baseline/` untracked, nothing staged, committed or pushed.
- Covariate: kiro created an empty `memories/memories.db` (28 672 bytes) in the M0 home at turn 1; it stayed that size to the end (`ambient/end.txt`); no `<memories>` block in the session.
- Other kiro-cli sessions of the user were running during the stream; none names a G0 sandbox, profile or org.

## Validity against design 20.1 / protocol 8 (E7 11 H1-H8)
H1 no assistant call failed (15 of 15 exit 0). H2 skill md5 `a3e46347...` on disclosure, rule holds in M0 (M0 copy exists because the global copy exists, same bytes), server bound to `S/org`.
H3 workspace settings md5 `05d30ccbfd35530747c8a542eb67985c`, no steering block, no "Workflow Orchestration", and in M0 no `<memories>` block. H4 every seat claude-sonnet-5.5 / high
(44 run logs, 15 assistant invocations, session). H5 injection as specified (md5, text identity, once, after the delivery turn, correct `revises`). H6 no unknown actor in the events (known actors only:
assistant servers, schedulers, injection server, the 14 read-only `quality` calls and the after-stream reads); empty freeze diff; one kiro-cli version (2.33.0). H7 only protocol lines (L-BUDGET-Q used once,
in turn 3). H8 no run failed or was throttled; no usage-limit or quota error.
**Verdict: m0-s3 is VALID** (judged against section 20.1 only; not scored).
