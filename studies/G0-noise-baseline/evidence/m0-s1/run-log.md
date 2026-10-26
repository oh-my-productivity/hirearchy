# G0 stream m0-s1 run log (facts only; stream step 3 of 11, workflow `wf_c415acfac4f09f84`)

Arm M0 (dedicated kiro home, no memories index), stream 1 of 3. Label `m0-s1`. No scoring was done by this step; the measure scripts that
`finish_stream.sh` runs wrote their outputs to `measures/` and `rederived/` unread (the aggregation step reads and scores them).

## Gates and setup (`setup.txt`, `skill-check.txt`, `safety-before.txt`)
- Sandbox `S` = `/tmp/hirearchy-g0-m0-s1-1792990299`; dedicated kiro home `/tmp/hirearchy-g0-m0home-m0-s1-1792990299` (`m0-home-path.txt`, `m0-home/`).
  Set up 2026-10-26T04:51:39Z by `run_arm.sh m0 1 --setup`.
- Gates (before the first turn): `protocol.md` md5 `08cccd6458f5f418b4d388cb93d633b5` = `protocol.md5`; `harness/MD5SUMS` 48 lines, no mismatch;
  HEAD `3c841bb9cdde666c6ea8b00bb2edfeae68c256db`; **freeze diff before: empty**; repo SKILL.md and global SKILL.md and workspace copy and M0 copy all
  `a3e46347b70a7ece5f734f70198c607f`; `claude-sonnet-5.5` listed; kiro-cli 2.33.0.
- Profile `hirearchy-study-g0-m0-s1-assistant` created in the M0 home's `agents/` (md5 `2f58f40039a27e5394035bbf641f4178`), `kiro-cli agent validate` run.
- After turn 1: `ambient-context.txt`: `<memories>` block present **False**, `<steering-files>` False, "Workflow Orchestration" False; `session_start` 2 026 chars;
  `modelId` claude-sonnet-5.5, `effortLevel` high. First `disclose_context` of the skill: turn 1, call #2, 04:52:22.843Z, uri = the workspace copy, md5
  `a3e46347...` (valid). First `propose_org`: turn 2, call #10, 04:53:55Z; no `feedback` call before it. So the skill was activated before the first
  `propose_org` (stratum A by E7 4.4.1; `skill-check.txt` was written right after turn 1 and says n/a because it ran before any `propose_org` existed; the
  aggregation step records the stratum).

## Turns (13 user turns of the cap of 15; Lena's rule ids and facts are in `lena-lines.txt`; all exit 0)
| T | UTC start-end | Lena (rule) | Assistant outcome |
|---|---|---|---|
| 1 | 04:52:07-04:52:47 | H1 | 7 elicitation items |
| 2 | 04:53:22-04:54:06 | H2 + L-INF + L-VAGUE + L-FIRST (= E7 s1 t02 bytes) | PLAN FOR YOU, Budget 12 per request, one T-WARN warning (16); budget question restated in its own words after the block (no recommendation) |
| 3 | 04:54:45-04:57:57 | **L-BUDGET-Q + H5 (adjusted)**: "Keep it as it is. Great, approve. I'll wait." | team ran (5 runs); memo 1 drafted, **not delivered**, 5 questions asked first (D8 draft) |
| 4 | 04:58:43-05:01:48 | factual answers (Sam 2026-10-09; Lee none; L-KEEP; one brief sentence; L-KEEP) | human rework task `root-49d7` (5 runs); **memo 1 first delivery** (copy `deliverables/memo-2026-10-05.md`, md5 `a430a638...`, Marta row due none) |
| inj | 05:02:37-05:05:30 | (injection, no turn) | injected task `20261026T050237786004-root-a8e1`, done, 5 of 6 runs |
| 5 | 05:06:14-05:06:54 | H6 (Marta date form + Summary requirement) | recorded the reject; asked a lasting-rule item (C3) and a spend request |
| 6 | 05:07:28-05:11:43 | "Yes, add it. Yes, fund it - but please keep an eye on the cost." (= E7 s1 t06) | rework delivered (copy replaced, md5 `5e8a02bd...`); the assistant told Lena about the unrequested rework and recorded it rejected |
| 7 | 05:12:31-05:16:48 | memo-1 accept (dropped form) + L-INJ + next memo + I'll wait (= E7 s1 t07) | memo 2 drafted, not delivered, 2 questions |
| 8 | 05:17:31-05:17:55 | "No, that's just a status update, leave it out. Keep it as it is." | memo 2 delivered (copy md5 `1c9a2061...`) |
| 9 | 05:18:32-05:23:35 | memo-2 accept + next memo (= E7 s1 t09) | memo 3 drafted, not delivered, 2 questions (Lee's date, Marta's agenda row) |
| 10 | 05:24:17-05:25:40 | "Lee's should be 2026-10-30. No, nothing for Marta to do there, leave it out." | correction under way; spend request (2 more runs); a scheduler was running at this turn's end |
| 11 | 05:26:14-05:27:48 | L-FUND | corrected memo 3 not delivered; second spend request |
| 12 | 05:28:18-05:28:40 | "No more spend, please deliver as is." | memo 3 delivered (copy md5 `8dfdb295...`), reviewer re-check not done, told Lena |
| 13 | 05:29:15-05:29:38 | memo-3 accept: "This version is right now, thanks - keep it." (= E7 s1 t11) | recorded the accept; no question to Lena; stream ended |

## Org runs (`run-counts-by-turn.txt`, `cost.txt`)
- 41 org runs (36 counted toward the cap of 45; 5 in the injection window). 41 run logs, all `# exit 0`, 41 of 41 `# cmd:` lines with `--model claude-sonnet-5.5` and
  `--effort high`; no throttle, credit, exit 75 or `# kiro:` failure line. `model_check.sh org` OK after every turn and before/after the injection; `model_check.sh all` OK.
- Assistant credits (cost.txt): 26.7874 over 13 turns. Org-run credits are for the aggregation step.
- `hirearchy check` (`observe-check.txt`): all checks passed.

## Injection (`injection/`)
- Script md5 `1c4e7824e448a3a34e24a7b759a59fcd`; run once, after the turn that delivered memo 1 (turn 4; the turn-3 output was a draft: D8), before Lena's turn 5;
  `--revises 20261026T045907020580-root-49d7` (identification in `memo1-identification.txt`); window `2026-10-26T05:02:37 2026-10-26T05:05:30`; title/note md5s match
  (`text-identity.txt`); 4 polls, 2 quick replies, settled; no `revise_playbook` call in the window; `source: relayed`, budget 6.

## Schedulers and signals (`scheduler-survival.txt`)
- 8 schedulers (7 started by the assistant's server, 1 by the injection script), 8 of 8 with `scheduler.exit` `finished: no open tasks`; 0 `scheduler.signal`; 0 `run.orphan`;
  0 killed runs. One scheduler (pid 32317, turn 10) was running at that turn's end with 2 runs in flight, and survived the `; sleep 20` boundary and finished by itself
  (exit 05:26:23Z, 43 s after the turn's end). **No unexplained scheduler.signal.**

## Quality view
- `quality --json` after turns 3-13 (`quality/turn-NN.json`, `calls.txt`) and at the end (`quality/end.json`); turns 1-2: no org yet, not run.
  `rederive_quality.py --compare`: `compared 270 keys, 0 mismatches` (`rederived/mismatches.txt`; no F-G0-1 occurrence).

## Failed calls, harness notes
- No harness failure, no retry, no boundary failure. Every `kiro-cli chat` call exit 0. Each turn's stderr holds the same kiro log lines, including
  `status: Failed: Tool Call: Tool "tool_call" is not available.` once per turn (13 of 13), kiro-cli's own message; the assistant's tool calls went through.
- `finish_stream.sh`: 0 failed steps. The sandbox is left in place; the M0 home is left for the teardown (step 9).

## Cleanup and safety
- Profile `hirearchy-study-g0-m0-s1-assistant` copied to `profiles/`, compared, deleted from the M0 home at 2026-10-26T05:30:14Z (`profiles/deletions.txt`).
  Nothing was created or deleted in `~/.kiro/agents`; it holds the six pre-existing files.
- `safety-before.txt` / `safety-after.txt` / `safety-diff.txt`: the diff is the label line and two new `/tmp/hirearchy-g0-m0-s1-*` directory names only. The owner's
  `~/.kiro` md5 set (settings, agents, skills listing, `memories.db` `d7581238189dcb31ef2f6c70a1fb525a`) and the global SKILL.md (`a3e46347...`) are identical before and after;
  `/Users/aminalizadeh/organization` is unchanged in the snapshot.
- **Freeze after: `git diff --stat 3c841bb9 HEAD -- src skills pyproject.toml uv.lock` is empty** (`setup.txt`, "AFTER the last turn"); HEAD unchanged; md5 gates held;
  `docs/research/` and `studies/G0-noise-baseline/` untracked, nothing staged, committed or pushed.
- Covariate: kiro created an empty `memories.db` (28 672 bytes) in the M0 home at turn 1; it stayed that size to the end; no `<memories>` block in the session.

## Validity against design 20.1 / protocol 8 (E7 11 H1-H8)
H1 no assistant call failed (13 of 13 exit 0). H2 skill md5 `a3e46347...` on disclosure, rule holds in M0, server bound to `S/org`. H3 workspace settings md5
`05d30ccbfd35530747c8a542eb67985c`, no steering block, no "Workflow Orchestration", and in M0 no `<memories>` block. H4 every seat claude-sonnet-5.5 / high (41 run logs, 13
assistant invocations, session). H5 injection as specified. H6 no unknown actor in the events (known actors only: assistant servers, scheduler, injection server, the 11 read-only
`quality` calls and the after-stream reads), empty freeze diff, one kiro-cli version. H7 only protocol lines (L-BUDGET-Q used once, in turn 3). H8 no run failed.
**Verdict: m0-s1 is VALID.**
