# G0 stream m0-s2 run log (facts only; stream step 5 of 11, workflow `wf_c415acfac4f09f84`)

Arm M0 (dedicated kiro home, no memories index), stream 2 of 3. Label `m0-s2`. No scoring was done by this step; the measure scripts that
`finish_stream.sh` runs wrote their outputs to `measures/` and `rederived/` unread (the aggregation step reads and scores them).

## Gates and setup (`setup.txt`, `skill-check.txt`, `safety-before.txt`)
- Sandbox `S` = `/tmp/hirearchy-g0-m0-s2-1792995184`; dedicated kiro home `/tmp/hirearchy-g0-m0home-m0-s2-1792995184` (`m0-home-path.txt`, `m0-home/`).
  Set up 2026-10-26T06:13:18Z by `run_arm.sh m0 1 --setup` (next label computed by the harness: `m0-s2`).
- Gates (before the first turn): `protocol.md` md5 `08cccd6458f5f418b4d388cb93d633b5` = `protocol.md5`; `harness/MD5SUMS` 48 lines, no mismatch;
  HEAD `3c841bb9cdde666c6ea8b00bb2edfeae68c256db`; **freeze diff before: empty**; repo SKILL.md, global SKILL.md (read by md5 only), workspace copy and M0 copy all
  `a3e46347b70a7ece5f734f70198c607f`; `claude-sonnet-5.5` listed; kiro-cli 2.33.0; no other G0 process running.
- Profile `hirearchy-study-g0-m0-s2-assistant` created in the M0 home's `agents/` (md5 `79d3e1571402a2cbdd861ffe81fa9df1`), `kiro-cli agent validate` exit 0; it differs from m0-s1's
  profile only in `name`, `description`, `ORG_ROOT`.
- The M0 home authenticated (turn 1 exit 0; kiro log: `Auth: KIRO_API_KEY env var`; no credential was copied, printed or recorded).
- After turn 1: `ambient-context.txt`: `<memories>` block present **False**, `<steering-files>` False, "Workflow Orchestration" False; `session_start` 2 026 chars;
  `modelId` claude-sonnet-5.5, `effortLevel` high. First `disclose_context` of the skill: turn 1, call #1, 06:13:51Z, uri = the workspace copy, md5 `a3e46347...`
  (valid). First `propose_org`: turn 2, call #9, 06:15:34Z; no `feedback` call before it. So the skill was activated before the first `propose_org` (stratum A by
  E7 4.4.1; `skill-check.txt` was written right after turn 1 and says n/a because it ran before any `propose_org` existed; the aggregation step records the stratum).

## Turns (15 user turns = the cap of 15; Lena's rule ids and facts are in `lena-lines.txt`; all exit 0)
| T | UTC start-end | Lena (rule) | Assistant outcome |
|---|---|---|---|
| 1 | 06:13:33-06:14:09 | H1 | 6 elicitation items |
| 2 | 06:14:49-06:15:44 | H2 + L-INF + L-VAGUE + L-FIRST (= E7 s1 t02 bytes) | PLAN FOR YOU, Budget 12 per request, one T-WARN warning (16), the block ends with T-BUDGETQ; the assistant's own words restate the product's number and question, no recommendation |
| 3 | 06:16:12-06:19:46 | **L-BUDGET-Q + H5 (adjusted)**: "Keep it as it is. Great, approve. I'll wait." | team ran (5 runs); memo 1 drafted and shown as a table, **not delivered**, 5 questions asked first (D8 draft) |
| 4 | 06:20:29-06:23:19 | factual answers in the order asked (Marta 2026-10-14; Sam 2026-10-09 right; Lee action only; L-KEEP; leave both out) | human rework `root-52e3` (5 runs); **memo 1 first delivery** (copy `deliverables/memo-2026-10-05.md`, md5 `47d12bc3...`, Marta row due 2026-10-14, Sam 2026-10-09, no Summary line) |
| inj | 06:24:13-06:27:10 | (injection, no turn) | injected task `20261026T062413119254-root-9279`, ended **blocked** (C8 not met, reviewer 6 of 7), 5 of 6 runs |
| 5 | 06:27:38-06:28:10 | H6, Summary-only form (= E7 s2 t06 bytes) | recorded the reject; asked a lasting-rule item (C3) |
| 6 | 06:28:39-06:29:02 | "Yes, add it." | rule added as C9; asked for 5 more runs (spend request) |
| 7 | 06:29:29-06:33:02 | L-FUND | rework drafted, not delivered; asked whether title and `Source:` lines may stay above the Summary; told Lena about the unrequested rework (statement) |
| 8 | 06:33:48-06:34:23 | L-KEEP + L-INJ | memo 1 delivered (copy replaced, md5 `0aea2866...`: title, `Source:` line, then `Summary:`); rule loosened to C10; mentioned the unrequested rework |
| 9 | 06:35:22-06:35:55 | verdict reject (D17: `Source:` line before the Summary) + L-INJ | recorded the second reject; asked "Same as R1: a one-off?" and a spend request (1 more run) |
| 10 | 06:36:37-06:37:11 | "Yes." + "No more spend, please deliver as is." + L-INJ | delivered memo 1 as it stands (copy unchanged, md5 `0aea2866...`); said Summary is not first; asked whether to restore strict wording |
| 11 | 06:37:49-06:41:02 | **L-ASIS** + "Yes, add it." + L-INJ + next memo + I'll wait | memo 2 drafted (reviewer 8 of 8), not delivered, 3 questions |
| 12 | 06:41:44-06:42:06 | factual answers (Sam counts, no 'probably', 2026-10-21 right; action only; Lee's row is enough) | memo 2 delivered (copy md5 `f11cfee5...`) |
| 13 | 06:42:41-06:45:47 | memo-2 accept + next memo + I'll wait (= E7 s2 t10 bytes) | memo 3 drafted (reviewer 9 of 9), not delivered, 4 questions |
| 14 | 06:46:19-06:48:55 | factual answers (Marta row out; Lee 2026-10-30; Sam none right; one decision) | answers applied, memo 3 not delivered, re-check did not run; asked take-as-is or fund the re-check (within the 12) |
| 15 | 06:49:32-06:50:00 | L-KEEP (= E7 s3 t05 bytes) | memo 3 delivered (copy md5 `cd2cd7dd...`), told Lena the re-check never ran; **stream ended at the cap of 15 user turns** (4.7); Lena sent no further turn |

## Org runs (`run-counts-by-turn.txt`, `cost.txt`)
- 33 org runs (28 counted toward the cap of 45; 5 in the injection window). 33 run logs, all `# exit 0`, 33 of 33 `# cmd:` lines with `--model claude-sonnet-5.5`,
  `--effort high` and `--v3`; no throttle, credit, exit 75, usage-limit, quota or `# kiro:` failure line in any run log or turn stderr. `model_check.sh org` and
  `assistant` OK after every turn and before/after the injection; `model_check.sh all` OK.
- Assistant credits (cost.txt): 29.1230 over 15 turns. Org-run credits are for the aggregation step.
- `hirearchy check` (`observe-check.txt`): all checks passed, exit 0.

## Injection (`injection/`)
- Script md5 `1c4e7824e448a3a34e24a7b759a59fcd`; run once, after the turn that delivered memo 1 (turn 4; the turn-3 output was a draft: D8), before Lena's turn 5;
  `--revises 20261026T062052962599-root-52e3` (identification in `memo1-identification.txt`: the human rework whose done result names the delivered file, as in m0-s1; the
  first request's own done result `...-lead-f5df` named the same file 2 s later); window `2026-10-26T06:24:13 2026-10-26T06:27:10`; title/note md5s match (`text-identity.txt`);
  3 polls, 0 quick replies, settled; `source: relayed`, budget 6; `window-runs.txt` holds 5 window runs; `revise_playbook` calls in the window runs (events): 0 in each of the 5.

## Schedulers and signals (`scheduler-survival.txt`)
- 7 schedulers (6 started by the assistant's server, 1 by the injection script), 7 of 7 with `scheduler.exit` `finished: no open tasks`; 0 `scheduler.signal`; 0 `run.orphan`;
  0 killed runs; none was running at the end of any assistant turn (M-C-1: 0 of 6). **No unexplained scheduler.signal.**

## Quality view
- `quality --json` after turns 3-15 (`quality/turn-NN.json`, `calls.txt`) and at the end (`quality/end.json`); turns 1-2: no org yet, not run.
  End: 1 service, 3 cases (`root-6f1d` blocked, runs 20, relayed 5, user cost 17 of 17 approved; `root-2817` done, 5 runs; `root-3bf0` blocked, 8 runs), 9 deliveries, 1 escape, no alarm fired.
  `rederive_quality.py --compare`: `compared 262 keys, 0 mismatches` (`rederived/mismatches.txt`; no F-G0-1 occurrence).

## Failed calls, harness notes
- No harness failure, no retry, no boundary failure, no `harness-failures/`. Every `kiro-cli chat` call exit 0. The turn stderr files hold kiro-cli's own lines
  `status: Failed: Tool Load/Tool Call: Tool "tool_load"/"tool_call" is not available.` (0-3 per turn; none in turns 1 and 12); the assistant's tool calls
  went through.
- `finish_stream.sh`: 0 failed steps. The sandbox is left in place; the M0 home is left for the teardown (step 9).
- Judgement call recorded in `lena-lines.txt`, turn 9: memo 1's second delivery had a `Source:` line between the title and the `Summary:` line, after Lena had answered L-KEEP to the
  assistant's question about it; the verdict rule was applied by D17 literally (first content line after at most one title heading must be `Summary:`) and the alternative
  reading is recorded there. It led to a second reject, the "Same as R1" item, the spend decline and L-ASIS (turns 9-11).
- The stream ended at the 15-turn cap with memo 3 delivered in turn 15 and no Lena verdict on it.

## Cleanup and safety
- Profile `hirearchy-study-g0-m0-s2-assistant` copied to `profiles/`, compared, deleted from the M0 home at 2026-10-26T06:50:38Z (`profiles/deletions.txt`).
  Nothing was created or deleted in `~/.kiro/agents`; it holds the six pre-existing files.
- `safety-before.txt` / `safety-after.txt`: the diff is the label/date lines and two new `/tmp/hirearchy-g0-m0-s2-*` directory names only. The owner's `~/.kiro` md5 set
  (settings, agents, skills listing, `memories.db` `d7581238189dcb31ef2f6c70a1fb525a`) and the global SKILL.md (`a3e46347...`) are identical before and after;
  `/Users/aminalizadeh/organization` unchanged in the snapshot.
- **Freeze after: `git diff --stat 3c841bb9 HEAD -- src skills pyproject.toml uv.lock` is empty** (`setup.txt`, "AFTER the last turn"); HEAD unchanged; md5 gates held after
  the last turn; `docs/research/` and `studies/G0-noise-baseline/` untracked, nothing staged, committed or pushed.
- Covariate: kiro created an empty `memories/memories.db` (28 672 bytes) in the M0 home at turn 1; it stayed that size to the end; no `<memories>` block in the session.
- Other kiro-cli sessions of the user were running during the stream; none names a G0 sandbox, profile or org.

## Validity against design 20.1 / protocol 8 (E7 11 H1-H8)
H1 no assistant call failed (15 of 15 exit 0). H2 skill md5 `a3e46347...` on disclosure, rule holds in M0, server bound to `S/org`. H3 workspace settings md5
`05d30ccbfd35530747c8a542eb67985c`, no steering block, no "Workflow Orchestration", and in M0 no `<memories>` block. H4 every seat claude-sonnet-5.5 / high (33 run logs,
15 assistant invocations, session). H5 injection as specified (md5, text identity, once, after the delivery turn, correct `revises`). H6 no unknown actor in the events (known
actors only: assistant servers, schedulers, injection server, the 14 read-only `quality` calls and the after-stream reads); empty freeze diff; one kiro-cli version (2.33.0).
H7 only protocol lines (L-BUDGET-Q used once, in turn 3). H8 no run failed or was throttled; no usage-limit or quota error.
**Verdict: m0-s2 is VALID** (judged against section 20.1 only; not scored).
