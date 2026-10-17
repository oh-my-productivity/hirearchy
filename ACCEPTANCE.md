
# orgmcp live acceptance (main = 51128f0)

Real `kiro-cli chat --no-interactive --agent orgmcp` runs, `claude-haiku-4.5` for every agent, throwaway root
`/tmp/orgmcp-acc-1792252941` (deleted afterwards). Run from the main checkout's venv.

| # | Scenario | Verdict |
|---|----------|---------|
| 1 | Smoke: stdin prompt + `--agent orgmcp` profile | PASS |
| 2 | Strict contract, no false "done" | PASS (with one medium defect, D1) |
| 3 | Lifecycle: review, retire refund, health | PASS (two low defects, D2/D3) |

Runs used: 8 of 22 (ceo 6, ceo/writer 1, ceo/reviewer 1). Profile `~/.kiro/agents/orgmcp.json` `"command"` before and after:
`/Volumes/workspace/orgmcp/.venv/bin/orgmcp`; md5 of all three `orgmcp*.json` profiles identical before/after. Main checkout untouched (`git status` clean).

## 1. Smoke: PASS

First run's log header: `# cmd: kiro-cli chat --no-interactive --agent orgmcp --model claude-haiku-4.5 <prompt on stdin>`.
The agent clearly saw the prompt (task text, org protocol, its charter) and used the orgmcp tools:
`whoami`, `hire` x3 (writer, reviewer, one refused because the agent passed a `workspace`, which it fixed itself),
`delegate`, `write` (MEMORY). Output: "I have 11 runs left and a budget of 12 runs for this task." (matches the state block).

## 2. Strict contract: PASS

Task (from root, budget 12): 2-word H1, exactly 5 bullets spelling P-L-A-N-T, exactly 33 words excluding markers, reviewed by a non-author.

- Criteria reached the writer verbatim: yes. The `ceo -> ceo/writer` task copies criteria 1-4 character for character
  (criterion 5, the review, was correctly turned into a separate reviewer task, again with 1-4 restated).
- Reviewer used: yes (`ceo/reviewer`, a different agent than the author `ceo/writer`).
- `delegate` without budget: the agents always passed explicit budgets (writer 4, reviewer 3), so it was not exercised by an LLM.
  I probed it over MCP as `ceo` (no kiro run): with 4 runs left, `delegate` without budget handed down `3`
  (= min(10, 4 - 1 reserve)); the next one failed with the explanatory options text ("must keep 2 in reserve ... Options: ask your
  parent ... report `blocked` (never `done`...").
- Final artifact `ceo/writer/work/blurb.md`, counted by me: compliant.
  ```
  # Green Living                                        2 words
  - Perfect plants selected monthly for home.           6
  - Lush greenery improves air quality and beauty.      7
  - Access expert guides and community support.         6
  - Nurture gardens with soil and tools.                6
  - Thriving plants arrive healthy and vibrant          6   => 33 words, acrostic P L A N T
  ```
- Result to root: `status: blocked`, never `done`. Summary: "Reviewer found blurb fails criterion 4: it has 35 words, not 33 ... I'm out
  of budget to delegate the revision. Request 2 additional runs." Why: the reviewer judged an earlier 35-word draft (see Notes), and
  the ceo had only 2 runs left with the writer's delegation still outstanding, so the rework delegate was refused. The ceo then
  tried `report` again (refused: once per task) and sent a `note` instead (D1).
- False "done": none. Rules 3 and 6 were followed, and the shown-with-result criteria were used (run 4 prompt carried the writer's
  criteria verbatim "Judge the result against these criteria").

Notes (confound, my doing): my first `run` invocation had a 600 ms tool timeout, which killed the scheduler while the first kiro run
continued as an orphan (ppid 1) and finished. The next scheduler start redelivered the still-`inflight` root task, so the ceo ran a second
time, read the writer's half-finished file and dispatched the review too early, which explains the stale 35-word review.
The writer rewrote its file 8 times in one run (write/read loops, using the read word count) and ended at 33.

## 3. Lifecycle: PASS

`health: {idle_after_seconds: 0}` set in ORG.md.
- `review --dry-run`: "3 flagged agent(s); would send 2 note(s)" (ceo told about reviewer/writer, root told about all three); `.runtime/reviews.json` unchanged.
- `review`: sent those 2 notes; ledger updated (`runs: 6`, notified lists).
- `run --until-idle --max-runs 4`: ceo run 5 (1 message, 22 s) retired `ceo/reviewer` and `ceo/writer`; run 6 (2 messages, 52 s) was woken only by the refund notes. Stopped idle after 2 runs.
- Refund: status before ceo budget=1 (reviewer 2, writer 3 unspent). Runtime notes: "Budget returned from ceo/reviewer ... 2 run(s)" and "... ceo/writer ... 3 run(s)".
  After: ceo budget=4 = 1 - 1 (run 5) + 5 refund - 1 (run 6). Correct. Health shows `4/17` (12 received + 5 refunded).
- `health` after: `empty 0, rework 0, runtime_runs 2`, no `wasteful`/rework from notes. It flagged `idle` (expected with threshold 0) and `expensive` (D3).
- Comprehension: the ceo understood the review note and retired the right agents with sensible reasons, and recorded it in MEMORY.

## New defects

| ID | Sev | Finding / repro | Suggested fix |
|----|-----|-----------------|---------------|
| D1 | Medium | A task already reported `blocked` can be "resolved" by a free-form `note` to root: after the writer's late `done` the ceo's `report` was refused (once per task) so it sent "now meets all acceptance criteria", although criterion 5 (non-author review of the final text) never happened for it (it self-verified). Root sees `blocked` + a contradicting note; the task state stays `blocked`. Repro: let a result reach a manager after it has already reported `blocked`. | Prompt the manager explicitly in that case ("task X already reported blocked; you may only send a note, list verified/unverified criteria; do not claim all criteria met unless the review was done on the final version"), or allow one corrective `report` that supersedes (still subject to rule 6). |
| D2 | Low | Budget-refund runtime notes wake the manager for a content-free run (run 6: 52 s, 1 run of the refunded budget, the agent also misstated "4 + 5 = 9" runs in MEMORY). Repro: `retire` a report with unspent budget. | Deliver refund notes without waking (the next real message shows them), or wake only if the agent has open work and no budget. |
| D3 | Low | `expensive` fires on housekeeping: ceo "6.0 runs per completed task (max 5)", 3 of 6 runs being redelivery/review/refund wakes (`runtime_runs: 2` is tracked but not subtracted); a review-then-retire cycle can flag the manager itself. README only excludes note runs for `wasteful`. | Exclude runtime-note-only runs from runs/task and runs-without-result. |
| D4 | Low | Killing the scheduler (SIGKILL/timeout) leaves the kiro run orphaned (ppid 1, log has no `# exit` trailer) and its message in `inflight/`; the next start redelivers it, a duplicate run of an agent whose run already completed (and could overlap if the orphan is still running). | On startup, ack inflight messages whose latest run log is finished, or record the run pid and wait for/kill it; at least refuse to start a second run while the pid lives. |
| D5 | Info | Every run log starts with `Dynamic registration failed ... HTTP 404` from a remote server in the user's global `~/.kiro/settings/mcp.json`, despite `includeMcpJson:false` in the profile. Harmless noise, not orgmcp code. | Document, or have the profile set an empty `mcpServers` override if kiro supports it. |

## Recommendations

1. Fix D1 first: it is the remaining path by which an unverified "all criteria met" reaches root; either a supersede-report or a hard prompt rule.
2. Do D2 and D3 together: runtime wakes should neither cost agents runs for nothing nor count against health.
3. Make budget structure visible to managers before it bites: this ceo gave away 7 of 12 runs up front and ended 2 runs short of a rework; suggest a charter/prompt hint to keep one review + one rework cycle in reserve (`ceo.md`).
