# orgmcp QA report

Scope: `git diff 5207608..5a81dcb` plus the base modules it touches. Baseline: 89 tests pass.
Reproductions were written as `tests/test_qa_findings.py`: 20 tests, all `xfail(strict=True)`, one or two per finding. Their fixes landed long ago and the tests now live next to the code they test, as plain passing tests in the `test_qa_findings.py` of `src/orgmcp/{budget,cli,dispatch,health,hierarchy,orgfiles,prompts,review,scheduler}/tests/`. The component column names the code as it was when this report was written (`core`, `scheduler`, ... were modules; they are packages now, see ARCHITECTURE.md section 5 for where each function went).
Each asserts the *correct* behavior, so it flips to XPASS (a strict failure) once the bug is fixed.
Each was also run with `--runxfail` to confirm it fails for the stated reason.
No product code was changed.

## Findings

Severity is by impact on a live org. The test column gives the test name in the `test_qa_findings.py` files listed above.

| id | sev | component | description | repro / evidence | suggested fix |
|---|---|---|---|---|---|
| QA-1 | critical (macOS/Windows) | core `resolve_write` | The guard compares first path components case-sensitively. On a case-insensitive FS, `write("ceo/agent.md")` overwrites the agent's own charter (`tools: [shell]`, `can_hire`, `max_children: 99`). `write("ceo/Inbox/<id>.md")` forges inbox mail, and a forged `budget: 1000` mints budget because budget is derived from files. `memory.md` skips the MEMORY cap. Confirmed on this Mac. | `test_qa1_case_variants_of_protected_names_are_refused` (FS-independent), `test_qa1_case_variant_cannot_rewrite_own_charter_or_mint_budget` (skips on case-sensitive FS) | Compare `first.lower()` against the lowercased reserved set. Also reject any write whose real directory entry differs from the requested case. |
| QA-2 | high | core `write` | `write(<me>/<new>/AGENT.md)` creates an agent without `hire()` checks. A leaf with `can_hire: false` can mint a report with `can_hire: true, max_children: 99`, bypassing `can_hire`, `max_children` and `max_depth`. Only tools and workspace are checked. | `test_qa2_write_cannot_create_agents_around_hire_rules` | In `resolve_write`, refuse creating `AGENT.md` in a directory that is not already an agent. Create agents only through `hire`. |
| QA-3 | high | scheduler `_reap` / core `end_run` | If an agent is retired while its run is in flight (parents run in parallel with their reports), `end_run` does `target.mkdir()` without `parents=True`. That raises `FileNotFoundError` out of `tick()`, the scheduler dies and `release()` SIGTERMs every other agent's in-flight run (each already booked as a used run). With `parents=True` it would instead leave a ghost `ceo/read/` dir that blocks re-hiring the name. | `test_qa3_retiring_a_running_agent_does_not_crash_the_scheduler` | In `end_run`, return early if the agent dir is gone. In `_reap`, skip `end_run`, `clear_failures` and commit for vanished agents. Optionally refuse to retire a running agent. |
| QA-4 | high | scheduler `kiro_runner` | The whole prompt (rules, charter, memory, **every message of the batch**) is one argv string. Message and result bodies have no size cap. A ~3 MB note gives `E2BIG` at `Popen`. Each attempt is booked as a failed run and burns budget, and after 3 the agent is paused. The poison message is never skipped, so one long result permanently wedges a manager. Run logs also embed the full prompt. | `test_qa4_oversized_message_does_not_wedge_the_agent` | Pass the prompt via stdin or a file. Cap message and summary size in `send` and `report`. Truncate the batch in the prompt with a pointer to the files. |
| QA-17 | high | templates / `run_prompt` | **Live-confirmed.** The run prompt lists an open task by id and title only, never its goal or acceptance criteria. A manager woken by a worker's *result* judges it against its own paraphrase in MEMORY.md. In smoke A3 root asked for exactly 33 words and a P-L-A-N-T acrostic. The CEO invented a new criterion ("word count 35 (≤40)"), accepted 35 words, and reported "all 6 criteria met" to root. The CEO had also re-typed the criteria lossily when delegating. | `test_qa17_prompt_shows_acceptance_criteria_of_open_tasks`; live excerpt below | In `state_summary`/`run_prompt`, render the full body of each open task, and the original acceptance criteria of the delegated task a result answers. |
| QA-6 | high | core `retire` | Budget handed to a report vanishes when it is retired (`budget = received − given − runs` and the dir is moved away). **Live-confirmed in B:** the CEO retired `writer` (17 left) and `reviewer` (4 left). 21 unspent runs were destroyed and the CEO was left with 1 run, so the org cannot take new work without the human regranting budget. | `test_qa6_retire_returns_unspent_budget_to_the_parent` | On retire, deliver a note (budget = remaining) from the retired agent to its parent, or credit it in the retire result. |
| QA-5 | medium | scheduler `tick` / health | No fault isolation: `_check_stalls` and `_check_review` are best-effort features but their exceptions kill `serve()`. Valid-JSON-but-wrong-shape `.runtime/nudges.json` (e.g. `[]`) gives `AttributeError`. A non-numeric `health:` threshold in hand-edited ORG.md (`idle_after_seconds: 1h`) gives `TypeError` when the first review is due, up to 24h after start. A half-written ORG.md has the same effect. | `test_qa5_corrupt_nudge_ledger_does_not_crash_tick`, `test_qa5_bad_health_threshold_does_not_crash_tick` | Wrap each tick phase in try/except and log. Validate and coerce config and ledger shapes. Treat bad ledgers as empty. |
| QA-7 | medium | review cadence | `total_runs` sums only *live* agents, so retiring agents makes the counter go down. With ledger `runs=5`, retiring the agent that held them and then doing 3 new runs with `review_every_runs=2` gives no review. Cadence falls back to the 24h timer, often right after the busy period in which agents were retired. | `test_qa7_retiring_agents_does_not_postpone_the_next_review` | Count runs including `.retired/*/runs`, or store a monotonic run counter in the ledger. |
| QA-8 | medium | review | Review notes ignore the reserve rule. A manager with budget 1 and one outstanding delegation still gets a note. Its run consumes the run reserved for the report's result, so the result arrives to an out-of-budget, paused manager. | `test_qa8_review_does_not_spend_the_reserve_of_a_manager` | Skip managers with `budget <= len(outstanding)`, and list them under "not notified". |
| QA-13 | medium | scheduler perf | Every tick (2s) parses every message file ever received or sent by every agent (`open_tasks` → `received`+`sent` for each agent in `_check_stalls`, again in `_launch`/`budget`). The cost is linear in history and unbounded. Measured ~0.07s per tick for 300 messages (~0.23 ms per file, pure-Python YAML), so ~2s/tick at ~10k messages. | `test_qa13_idle_tick_cost_does_not_grow_with_history` | Derive open tasks from inbox/inflight plus a cached index (keyed by mtime), and use `yaml.CSafeLoader`. Only run stall checks for agents with tasks in `inflight/read` that lack a result. |
| QA-14 | medium | health `wasteful` | An "empty" run is any run that sent no message. That counts crashed runs (kiro down, E2BIG, auth) and runs that merely handle a runtime note (review, reminder). **Live:** after the review note, the CEO acted correctly (two `retire` calls) and was booked `empty 1`. A broken kiro makes every agent `wasteful`, and the suggested action ("fix the charter") is wrong. | `test_qa14_failed_runs_are_not_blamed_as_wasteful` | Exclude runs whose log ends in a failure, and runs whose batch was runtime-only, from the empty ratio. |
| QA-18 | medium | `delegate` UX | `budget` defaults to `default_budget` (10) and fails if the manager holds less. The docstring does not state the default. **Live (A1):** the CEO's reviewer delegation failed ("insufficient budget"), so it skipped the mandatory reviewer step and reported done anyway. The same happened in A3. | `test_qa18_delegate_without_budget_adapts_to_what_the_manager_can_afford` | Default to `min(default_budget, affordable)`. State the default in the tool docstring. Add to the protocol: "if you cannot satisfy an acceptance step, report blocked". |
| QA-9 | low | core `retire` | `retire` takes a short name and rejects the full address (`ceo/eng` → "no such agent: ceo/ceo/eng"), but review notes and every other tool use full addresses. (In the live B run the CEO still got it right.) | `test_qa9_retire_accepts_the_full_address_of_a_direct_report` | Accept both forms. |
| QA-10 | low | cli `resume` | `orgmcp resume ceo/` (tab completion) resumes the agent, but `clear_failures` uses the raw arg. The count stays at 3, so the next single failure re-pauses it. | `test_qa10_resume_with_trailing_slash_clears_failures` | Use `org.require()`'s normalized address. |
| QA-11 | low | core `hire` | `NAME_RE` ends with `$`, which matches before a trailing newline. `hire(name="ops\n")` creates an unaddressable dir that `children()` lists. | `test_qa11_hire_rejects_name_with_trailing_newline` | Use `fullmatch`. |
| QA-12 | low | core `deliver` | The recipient copy is written before the sender's `sent/` copy. A failure between them (disk full, crash) delivers a budget grant that the sender is never charged for, which mints budget. A redelivered `report` would also duplicate the result. | `test_qa12_failed_send_does_not_mint_budget` | Write `sent/` first, then the inbox, or make both idempotent by id. |
| QA-15 | low | core `report` | Artifacts outside the org are accepted and annotated, e.g. `/etc/hosts` (word count and mtime). That is an info leak and a bogus "artifact". | `test_qa15_report_refuses_artifacts_outside_the_org` | Refuse paths that resolve outside the org root. Prefer the reporter's own directory. |
| QA-16 | low | scheduler | The timeout and shutdown paths kill only the top process, not its process group. Tool subprocesses that kiro spawned outlive a timed-out run, which has already been redelivered. | `test_qa16_timeout_kills_the_whole_process_group` | `Popen(start_new_session=True)` and `os.killpg`. |

Observations without a test (design or ambiguity, not defects):
- `read` and `report` word counts include markdown markers (`#`, `-`). A 5-bullet blurb is "46 words" for 38 real words. Managers had to compensate for this.
- `ensure_kiro_profile` rewrites the shared `~/.kiro/agents/orgmcp*.json` non-atomically, and it points at whichever checkout ran last. Before my live test, `orgmcp.json` pointed at the QA worktree venv (I did not determine which process wrote it). After it, the profile pointed at the main venv, as intended. Concurrent org runs from different checkouts will ping-pong it.
- The ledgers (`failures`, `reviews`, `nudges`) are read-modify-write with no lock, and the CLI (`resume`, `review`) can race the scheduler. A lost update re-sends a review item or restores a failure count.
- `acquire()` trusts `kill(pid, 0)`: a recycled pid blocks startup forever, and `PermissionError` is not handled.
- `notice_failures` text ("A human must inspect it and run `orgmcp resume`") is also sent to the LLM parent, who cannot act on it and wastes a run.
- Security notes in the README hold. Symlink and `..` escapes in `write`/`read` and the `health` and `revises` permission checks held in my probes (`revises` must name an earlier task sent to the same report).

## Live smoke test (claude-haiku-4.5, main checkout venv, throwaway `/tmp/orgmcp-qa-*`, since deleted)

Kiro runs used: **14 of 25** (A: 13, B: 1). No kiro-cli errors, auth issues or timeouts occurred. Every run exited 0. (Per-tool errors are not visible in the run logs, only "status: Completed".)

**Scenario A**

Root → `ceo` (examples/ceo.md charter, `--can-hire --max-children 3`). `ceo` hired `writer` and `reviewer`. I ran three tasks of increasing strictness.

| task | runs | outcome |
|---|---|---|
| A1: 1 H1, 5 bullets of ≤12 words, ≤70 words | 3 | Correct result and artifact reached root (`ceo/writer/work/blurb.md`, 46 words). The reviewer was never used: the CEO's `delegate` to it failed on budget and it wrote "I have insufficient budget… I'll report the work as done" despite criterion 5. |
| A2: 3-word H1, 6 bullets × 7 words, exactly 52 words, distinct initials | 5 | Passed first time. The CEO delegated to the reviewer with `budget=5`. Good flow. No rework. |
| A3: 2-word H1, bullets of 3/4/5/6/7 words, P-L-A-N-T initials, exactly 33 words | 5 | The writer's first draft failed. **`revises` was used:** the CEO sent `delegate(..., revises=<A3 task id>)`, and `health` showed `writer … rework 1` and `branch … rework 1`. The final file was nevertheless wrong (35 words, bullet 1 five words). The CEO had mis-paraphrased the acrostic criterion when delegating, the writer relaxed the contract and reported `done`, and the CEO again skipped the reviewer on budget. It reported "all 6 criteria met" to root. Root's result is false. |

Excerpt (CEO run prompt, `# Your state`, final A3 run), showing the missing acceptance criteria (QA-17):
```
- Open tasks assigned to you:
  - 20261017T151841584548-root-fa47 "Strict blurb 3" from root
```
The same run's output:
```
5. ✓ Word count: 35 words (≤40)      # root asked: exactly 33
All criteria met. Now delegating to reviewer for final quality check.
[tool] Running: @orgmcp/delegate
I'm out of budget to delegate further. I'll send the verified artifact directly to root ...
```

**Scenario B**

I set `health: {idle_after_seconds: 0}`. `review --dry-run` printed 2 notes (`ceo`: reviewer and writer idle; `root`: 3 of 3 flagged) and wrote nothing. `review` sent the same two notes. One CEO run followed (the only one; the org then went idle).

- The CEO read the note and called `retire` on **both** reports at once, "to preserve budget", and rewrote MEMORY.md, recording the retirement under "Current State". The file still carries the stale "(≤40)" criterion from A3 and "Budget: 0 runs remaining" (actually 1).
- Not a platform defect on its own (the 0-second threshold forced it), but it shows the QA-6 impact: 21 unspent runs were destroyed.
- The root summary also suggested "retire `ceo`" for the only remaining manager.
- Run time: the CEO's run was 14s; the whole scenario took about 1 minute.

Prompts and tools: agents understood paths (`ceo/writer/work/...`), `whoami`, `read`, `write`, `report` and `retire` without a single wrong-path or refused call. The failure modes were semantic: lost acceptance criteria, budget errors turned into skipped steps, and "done" reported when a criterion could not be met.

## Top 3 improvements

1. **Make the contract visible and enforceable (QA-17, QA-18).** Show the full body of open tasks, and the original acceptance criteria for the task a result answers, in every run prompt. Make `delegate`'s default budget affordable. Add a protocol rule: "if you cannot satisfy an acceptance step, report `blocked`, never `done`". Today root receives false "done"s.
2. **Close the write and lifecycle holes (QA-1, QA-2, QA-3, QA-6).** Make the write guard case-insensitive and forbid `AGENT.md` creation outside `hire`. Make `end_run` and `_reap` safe for retired agents. Refund unspent budget on retire.
3. **Harden the scheduler loop (QA-4, QA-5, QA-13).** Isolate each tick phase so a bad ledger or config cannot kill the daemon. Pass the prompt by stdin or file, and cap message size. Stop re-parsing the full message history on every tick.
