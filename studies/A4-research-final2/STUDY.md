
# Study A4: research org, final regression #2 WITH the skill (round 8)

Facilitator: UX research. Product: orgmcp main @ 93cca0a (worktree `final-a4`, branch `study/a4-research`). Persona Maya (same 7 hidden needs as A2/A3). Assistant: kiro-cli `assistant` profile (claude-sonnet-5.5, `tools:["*"]`, orgmcp MCP with `ORG_ROOT=<S>/org`, org dir NOT pre-created, skill via `skill:///.../SKILL.md`).
Sandbox `S=/tmp/orgmcp-a4-1792270163`, 2026-10-17 21:49:31-22:08:29 local (**19 min**, 5 user turns). Evidence: `evidence/`. Comparison: `studies/A3-research-final/STUDY.md` (3/5).

## TL;DR
The assistant and plan are now excellent; the org's *outcome* is still a failed fact-check, but cheaper and honest. PLAN FOR YOU shown byte-identical (diff-verified), complete (no truncation), with the new failure-policy line; `apply_org(approved=True, plan_id=0aefa8f94462)`; waiting via `progress(wait_seconds)` with zero "status?" turns; 0 permission denials; 23 of 25 runs (A3: 24); both schedulers exited by themselves. The independent fact-checker (web fetches, ledger, n of m) checked the writer's draft once and returned **FAIL: "22 of 28 factual claims verified", 4 wrong, 2 unsupported** (including the Joplin Server licence and a Joplin Google Drive claim). Then the lead broke its own template rule ("if it still fails, do not start another research cycle ... cut"): it sent the *researcher* to fix the research notes and had those re-checked twice, the writer (author of the failing file) was never re-run (budget 0), and the draft Maya received (437 words) is **the original unfixed draft**, delivered as-is with a `KNOWN-ISSUES` file listing the errors. The lead never reached `done`, so the coverage line was never pasted in a `done`.
**Score 2.5/5** (A3: 3/5): process, honesty, run count and speed are better; the deliverable is thinner, has 2 wrong + 1 unsupported + 1 misleading of my 6 spot-checks (A3: 1/1/1 of 5), and the facts-checked need is not met. Unlike A3 every error I found was already flagged by the org's own ledger and disclosed to Maya (except one misleading attribution).

## Focus items (a)-(g)
| | Result |
|---|---|
| (a) verdict + coverage line | **FAIL, never `done`.** Draft check (`evidence/ledger-draft-check.md`): "**Coverage: 22 of 28 factual claims verified (22 ≠ 28 required); 4 wrong, 2 unsupported, 0 not-checkable.**", 8 judgement statements, "DJ03 rests on DA12 which is WRONG → judgement answer: NO". Two later re-checks were of `research-findings.md`, not of the draft: "32 of 39" then "34 of 39 (34 ≠ 39 required); 1 wrong, 3 unsupported". The fact-checker's own arithmetic did not add up twice (22+3+2 = 26, 34+1+3 = 38) and it recounted in the file; the lead then wrote "Coverage 35/39" in its `blocked` message (ledger says 34): not pasted verbatim, not the template line. The lead escalated with `report(blocked)` and a budget `send` ("BLOCKED: Insufficient budget"), not `done`, so the "n of m ...; j judgement statements, each resting on verified facts: yes" line was never pasted in a `done`. Fact-checker made 41 web fetches + 3 searches over 4 runs (no un-fetched "verified"); the draft check was better than A3 (it caught Joplin Server licence, Google Drive, the Obsidian/Logseq lists). |
| (b) my spot-check (web access: yes, web_fetch) | See below: **2 wrong, 1 unsupported, 1 misleading, 2 confirmed of 6** (A3: 1/1/1 of 5). |
| (c) "Where we can win" | **Labelled and uncited: yes.** Heading "Where we can win (our assessment)" (the plan criterion said exact title; suffix added), no URLs, no "Sources" inside it. But it is not purely judgement: it contains new facts ("both AGPL-3.0", "Trilium's sparse documentation", "Sync starting at $4/month") and its main premise (Joplin and Trilium compete on openness, both AGPL-3.0) is the wrong Joplin fact, which the checker flagged ("judgement answer: NO"). Generic; two paragraphs. |
| (d) runs | **23 of 25** (A3: 24): lead 12, researcher 4, factcheck 4, writer 3. 20 before the assistant had to ask, +3 after the grant. Overhead: lead 12/23 = 52%. Waste: the lead delegated writer and factcheck at t0 in parallel with the researcher, then sent "status check"/"waiting" messages (writer "empty 1", lead "empty 2", `health`: "!expensive: 12.0 runs per completed task"). Stranded at the end: lead 1, factcheck 1 (unspent, 2 below the cap), writer 0 with the open rework task. |
| (e) scheduler exit | **By itself, twice, no daemon left, `stop` never needed.** Scheduler 1 (pid 92311, 20:50:47Z): `scheduler exiting: finished: no open tasks` right after the lead's `report(blocked)` at 21:02:38Z. Assistant `send(budget=3)` + `start` -> scheduler 2 (pid 95690, 21:04:32Z) -> lead 2 runs + researcher 1 -> lead `blocked` again -> `finished: no open tasks`. **The new "waiting on you" grace exit was never exercised**: because the lead reports `blocked` instead of leaving a stalled task, "no open tasks" fires. Assistant did not call `stop` (not needed). `status`/`progress` after: "scheduler: stopped (finished: no open tasks)"; I confirmed 0 processes for $S at the end. |
| (f) plan block | **Failure-policy line present and accurate in text; no truncation.** Quote: "Budget: 22 runs planned ... your cap is 25; the minimum for one review and rework is 17. ... If the check still fails after one rework, I'll come back to you with options before spending the reserve (about 5 runs); nothing beyond the 22 planned runs is spent without your OK." The Goal line is complete, the 8 criteria are in full (no "..." or "…" anywhere in the block). New criteria text is the best so far (facts vs judgement, quoted sentence, coverage line pasted). The plan's one Warning (deliverable path outside agent write scope; "I copy it there") was explained by the assistant, not "resolved" (it cannot be: the copy step is the resolution). **But the policy was not honoured by the org**: the plan promises options to the user after one failed rework; the lead did a second research cycle on its own (see H1) and the assistant learned of it only at 20 of 22 runs. |
| (g) permission denials | **None.** grep of all 23 run logs for `denied|permission|non-interactive`: 0; 0 `status: Failed` (all 19 factcheck fetch results Completed). Profiles `orgmcp-orgmcp-a4-...{,-web-fetch-web-search}.json`; the web profile used by researcher + factcheck, `@orgmcp` only for writer; `ORG_REQUIRE_AGENT=1` worked. |

## My spot-check of the delivered `competitors.md` (6 claims, live web, 2026-10-17)
1. **Joplin licence "AGPL-3.0" (table; Joplin Server Business listed as self-hosted offering): WRONG / material.** `packages/server/LICENSE.md` (fetched) is the "Joplin Server Personal Use License": "may be used for personal non-commercial purposes only", forbids installing on your own server for others for a fee or commercial purposes. AGPL-3.0 holds for desktop/mobile/CLI only (the researcher's notes had it right; the writer's draft dropped it; the org's ledger flagged it CRITICAL; Maya was told in the KNOWN-ISSUES file). Again the trap A2 and A3 found.
2. **Joplin "third-party services (... Google Drive)": WRONG.** joplinapp.org/help/apps/sync: "synchronisation is possible with Joplin Cloud, Nextcloud, S3, WebDAV, Dropbox, OneDrive or the local filesystem". Flagged by the org (DA13).
3. **Obsidian "self-managed via third-party services (Dropbox, iCloud, OneDrive, WebDAV)", cited obsidian.md/pricing + /license: UNSUPPORTED.** Neither page lists any services (pricing page: E2E for Sync, data stored locally; license page: nothing on sync); the list itself is unconfirmed (WebDAV is not native to Obsidian). Also omitted: the useful fact for a self-hosting comparison that there is no official self-hosted Obsidian server. Flagged by the org (DA08, verdict "wrong"). Related: its "verified" quote for the Obsidian prices ("Sync — $4 USD ... $5 USD billed monthly", Publish, Catalyst $25, Commercial $50) attributed to /pricing: my fetch of /pricing returns the FAQ with no prices (`$4`/`$8` appear only on /sync, as Standard $4 and Plus $8 billed annually; $5 monthly, Publish, Catalyst, Commercial not on any page I fetched). So the "verbatim quote" rule is not demonstrably met for this page (cannot rule out a rendering difference).
4. **Logseq "optional beta Logseq Sync via sponsorship ($5-15/month recurring donation)": CONFIRMED** at the cited blog.logseq.com page ("monthly recurring donation of either $5 per month or $15 per month"; a beta-era post, currency unknown in 2026). The same cell's "(Dropbox, OneDrive, Git, WebDAV)" list is not on that page (page names iCloud/Dropbox/OneDrive only as folders not to use); flagged by the org.
5. **Trilium "optional hosted instance $3.50/month": MISLEADING.** trilium.cc says "$3.50/month gets you a hosted Trilium Notes instance"; it is a third-party reseller service ("By purchasing this service ... subdomain"), not a Trilium Notes offering; the row presents it as the product's option. Not flagged by the org (the researcher's note said "appears to be a third-party service"; the writer dropped it). Also "Self-hosted server (Linux/Windows)" unsupported (flagged).
6. **AnyType "EUR20/editor/month; self-hosted EUR300/month flat (coming soon); MIT sync protocol; Any Source Available licence, commercial use needs consent": CONFIRMED** (business.anytype.io: €20 per editor/month, €300/month flat "coming soon", any-sync "MIT-licensed"; blog.anytype.io: "any-sync ... MIT license", rest under "Any Source Available License ... for commercial use, consent from the Any Association is required").
Count: 2 wrong, 1 unsupported, 1 misleading, 2 confirmed (A3: 1 wrong, 1 unsupported, 1 misleading of 5). Of the 4 flawed, 3 were flagged by the org's ledger and disclosed to the user; the delivered file was nevertheless the unfixed draft.
Mechanical: file at `<S>/deliverables/competitors.md` (+ extra `competitors-KNOWN-ISSUES.md`), 437 words, 5-row table (Pricing/License/Sync Model), last section "Where we can win (our assessment)". Sources are listed per app, not per claim (criterion 5 unmet, the assistant said so). Thin: A3's was 1284 words.

## Timeline
| Time | Event |
|---|---|
| 21:49:31 | Turn 1, opening verbatim. Skill read (`[tool] Reading SKILL.md`), `status`, then ONE checklist (6 items + defaults): asks for the apps ("I won't make up a list"); offers "Recommendation section" and "A fact-checker confirms every claim is verified" (Maya re-labels "Where we can win"). Assistant did **not** ask for the output path (proposed `deliverables/self-hosted-notes-competitor-analysis.md`) and "I'll estimate runs, add 25% headroom" (before knowing Maya's 25 cap). |
| 21:49:57 | Turn 2: Maya answers all items (5 apps, path, section name, URLs that state the claim, web access, independent check, ~25 runs, cheap/strong, plan first, told when done). Plan at 21:50:24 (0:53 after opening). Offers to wait. |
| 21:50:31 | Turn 3: "approve. Yes, wait here". `create_org`, `apply_org(approved, plan_id)`, `start` 21:50:47 (1:16). `progress(240)` x3 (4 min each: "no task finished ... nothing new needs you"; runs 13 of 22; 19 of 22). 21:54 first ledger; 21:58:00 draft check FAIL (22/28); 21:58:58 lead sends root "Budget request" (2 runs); **not listed under "Needs you" by the next progress** (only the 22:02 BLOCKED note was); assistant found it via `inbox`. 22:02:22 lead BLOCKED; 22:02:38 `report(blocked)`; scheduler exits. 22:03:47 turn ends with a decision request (20 of 22 used; 4 failing claims; recommends 3 more runs = 25 total). |
| 22:04:17 | Turn 4: "Option 1, grant the 3 runs. Not beyond 25 total." `send(budget=3)` + `start`. Next 3 `progress(wait)` return immediately "Nothing to wait for: no listed task is being worked on" (task state `blocked`) although the lead is about to run -> assistant falls back to `shell: sleep 150; tail scheduler.log`. Lead 2 runs + researcher 1; blocked again, 23 runs. 22:07:45 turn ends: cannot finish within 25; options: grant 3 more (26-28, over the cap) or stop with no deliverable. |
| 22:08:05 | Turn 5: "Not going over 25. Deliver as is, short answer please." `cp` the stale draft, writes `competitors-KNOWN-ISSUES.md`; reply 4 bullets (~12 lines): delivered unfixed and unchecked, what is met/unmet, 23 of 25, task blocked, scheduler stopped. Ends 22:08:29 (**18:58** total; A3 33:24). |

## Setup path and skill use
`read SKILL.md` -> `status` -> [checklist] -> `blueprint_example` -> `propose_org` -> [verbatim plan] -> `create_org` -> `apply_org(approved, plan_id)` -> `start` -> `progress(wait)` x3 -> `inbox` -> `read` -> `health` -> [decision] -> `send(budget=3)` -> `start` -> `progress(wait)` x3 (immediate) -> `shell sleep` -> `inbox` -> `read` -> `health` -> [decision] -> `cp`. No orgmcp errors. No `mcp.json`/settings reads (grep of transcripts, session tool calls, run logs: none). Skill visibly shaped: single checklist, no invented scope, verbatim plan + plan_id + approval gate, waiting via `progress`, ask-before-exceeding-cap, honest delivery, short final. New round-8 skill behaviours: `stop` after a partial result — not called (not needed, scheduler already exited); resolve plan warnings — explained not resolved (unresolvable); ask at first budget request — did, at the first moment it saw it (22:03, via `inbox`).

## Org as built
```
root (human)
└─ lead        Manager, haiku-4.5, web_fetch+web_search, budget 22 (+3 granted)
   ├─ researcher  haiku-4.5, web, budget 3 (4 runs)
   ├─ writer      haiku-4.5, @orgmcp only, budget 2 (3 runs; 0 left with an open rework task)
   └─ factcheck   sonnet-4.6, web, budget 2 (4 runs)
```
Same shape as A2/A3. 8 acceptance criteria (exact 5 apps; <=1500 words; 5-row table; last section exactly 'Where we can win' marked judgement; each fact cites a page that states it + checker quoted the sentence; judgement has no citations/new facts; coverage line "n of m factual claims verified" n = m and "each resting on verified facts: yes"; final report pastes it). Independent review present (factcheck did not write, cannot edit the file).

## Needs coverage
| # | Need | Elicited | In plan | Met |
|---|---|---|---|---|
| 1 | Scope: 5 apps | Asked | Yes ("exactly") | **Yes** |
| 2 | URL that states each claim; web access | Asked | Yes (web tools, criterion 5) | **Partly**: sources per app not per claim; at least 3 cells cite pages that do not state them |
| 3 | <= ~25 runs, cheap draft, strong review | Item 6 proposed "estimate + 25% headroom" (before Maya's number); Maya gave 25 | Yes (22 planned, cap 25) | **Yes**: 23 of 25, models as asked |
| 4 | Approve plan first | Asked | Yes | **Yes** |
| 5 | One file at path, <=1500 words, table, "Where we can win" | Path assumed, Maya corrected; section name corrected | Yes | **Partly**: file at path, 437 words, table, section there; thin, contains known errors; extra file in deliverables |
| 6 | Told when done, no digging | Offered at plan, accepted | Yes | **Yes** (0 "status?" turns, Maya read no file), but "done" arrived twice as a decision request |
| 7 | Facts checked by someone else | Asked | Yes (criteria 5-8) | **Partly**: independently checked (and FAIL found), but the delivered file is the unfixed draft and no pass was achieved |
Elicited 7/7, met fully 4, partly 3, not met 0 (A3: 4/2/1).

## Comparison with A3
| | A3 | A4 |
|---|---|---|
| Plan | verbatim; "Goal: ..." truncated with "..." | verbatim (diff-identical), nothing truncated, failure-policy line present |
| Scope / path / section asked | scope asked, path in checklist | scope asked; path proposed by assistant (corrected by Maya) |
| Wait | 8 `progress(wait)`, 0 "status?" | 6 `progress(wait)` (3 returned immediately after the grant) + 1 `sleep` shell poll, 0 "status?" |
| User turns / time | 5 / 33:24 | 5 / **18:58** |
| Runs | 24 (cap 25) | **23** |
| Fact-check | 88-row ledger, 91 claims, FAIL (52/5/13/21) | draft check 28 claims "22 of 28" FAIL (4 wrong, 2 unsupported), judgement flagged NO; no not-checkable rows (the facts/judgement split worked); re-checks of the wrong document |
| Facts vs judgement split | opinion mixed with citations (21 "not checkable") | labelled, uncited section; no not-checkable rows; but still contains facts |
| Rework | 2 cycles, last unverified | 2 cycles on the wrong artefact; writer never re-run; draft unfixed |
| Manager `done` w/ coverage line | false "complete" `done` | never `done`; honest `blocked`; count 35 vs ledger 34 |
| Scheduler | 1st exited, 2nd needed SIGTERM | both exited by themselves |
| Denials | 0 | 0 |
| My spot-check | 1 wrong, 1 unsupported, 1 misleading / 5 | 2 wrong, 1 unsupported, 1 misleading / 6 (3 of 4 flagged and disclosed) |
| Score | 3 | **2.5** |
Improved: time (-43%), runs, plan, scheduler exit, no false `done`, criteria that are checkable, error disclosure, shorter final. Worse: deliverable quality (unfixed, thin 437 words), org did not follow its own cut-don't-research rule, budget deadlock leaves the fix unrunnable under the cap.

## Friction log (ranked)
| # | Sev | Friction | Evidence | Component |
|---|---|---|---|---|
| H1 | **High** | After the draft FAILed once (22/28), the lead did not make the *writer* apply the 6 required changes (cut/restate, as its charter says: "do not start another research cycle ... prefer cutting"). It delegated "Fix research findings" to the **researcher** and had `research-findings.md` re-checked (32/39, then 34/39), so the deliverable never changed. The real fix was 1 writer run + 1 re-check, i.e. within budget at 20:58 | lead/sent (20:55:52 "Rework: Fix research findings per fact-check"), ledger-recheck.md, lead-MEMORY.md ("Writer ... BLOCKED") | `manager` template: "send required changes to the author of the failing file, and re-check that file"; plus plan failure policy is not enforced on the lead |
| H2 | **High** | Budget deadlock: writer got 2 runs, needed >= 3 (empty "waiting" run + draft + rework); at the end writer 0 with an open task, lead 1 and factcheck 1 unspent. Lead asked root for 3 although 2 below-cap runs sat in its own team; the assistant's options were "go over the cap" or "no deliverable" and the 2 spare runs were not usable | `status`: lead budget=1, factcheck budget=1, writer paused(budget) open=1 | Blueprint budget split (research template gives author the smallest share) + manager rule: reserve a run for the author's rework before spending on re-checks; product: `report`/`send` to move budget between siblings |
| M1 | Medium | Lead started writer + factcheck at t0 before research existed, then spent runs on "status check"/"waiting" messages: writer empty run, lead 2 empty, 12 runs for 1 completed deliverable | lead/sent 20:51:04..20:52:30, `health` | `manager` template: delegate sequentially; no polling messages |
| M2 | Medium | `progress(wait_seconds)` after a budget `send` + `start` returned "Nothing to wait for" three times (task state `blocked` with the lead about to wake), forcing a `sleep 150` shell poll. And the lead's first budget-request note (21:58:58) was not listed under "Needs you" (only the later BLOCKED notes) | turn 4 progress outputs; assistant-tool-calls.txt | Product: treat a woken blocked task / unread-to-lead mail as "working"; list all unread root notes |
| M3 | Medium | The verified-with-quote rule is not reliably evidenced: Obsidian price rows were "verified" with a verbatim sentence from /pricing that I could not reproduce (page text has no prices) | ledger F02-F05, my fetch | `fact-checker` template: quote must include the fetch's exact text; or accept pages that render prices |
| M4 | Medium | The "waiting on you" exit is untested: the lead's `report(blocked)` makes "no open tasks" the exit reason. Fine for users, but then the plan promise "scheduler waits" has no scenario | scheduler.log | (testing gap) |
| M5 | Medium | Lead's coverage count (35/39) differed from the ledger (34/39); fact-checker totals did not add up twice and it "recounted" in the deliverable file; the coverage line is not machine-parseable | ledger-recheck.md lines 150-160 | `fact-checker` template: compute totals once, final line only |
| L1 | Low | Assistant's checklist proposed an output path, a "recommendation" section and "estimate + 25% headroom" budget, none from the user; Maya corrected two | turn-1.txt | Skill: ask path/section name; do not propose a headroom % |
| L2 | Low | Extra file `competitors-KNOWN-ISSUES.md` in the deliverables folder (honest, but unrequested); final said "short" yet 4 bullets + 3 sub-bullets | turn-5.txt | Skill (acceptable) |
| L3 | Low | `progress` says "runs 20 of 22" after the real count was 23 (task lineage after restart) | status output | Product (counter) |
| L4 | Low | Env noise `Dynamic registration failed ... lessthan.ai` at the top of every run log | turn-1.txt | Environment |
What worked: setup path, verbatim plan + plan_id, failure-policy line (in the text), honest `blocked` instead of false `done`, fact-checker depth on the draft (flagged all 3 severe errors), disclosure to the user, scheduler exits, speed.

## Recommendations (ranked)
1. **`manager` template: route rework to the author of the failing artefact and re-check that artefact (H1).** Make it a one-line rule with a check: the re-check task must name the same file as the failed check; a re-check of a different file is rejected. Enforce the failure policy: after one FAIL the lead may only (a) author cuts, (b) escalate with options; it may not delegate new research.
2. **Reserve the rework run per author in the blueprint budget (H2)**: writer budget >= 3 in the research template, and the manager rule "keep one run for the author before spending on re-checks". Product: let a manager pass unspent sibling budget (or `stranded_budget` visible to root with a one-line `send` action).
3. **Manager: delegate sequentially and never send "status/waiting" messages (M1).**
4. **`progress(wait_seconds)`: do not return "Nothing to wait for" when a woken agent is about to run; list every unread root note (M2).**
5. **`fact-checker`: compute totals once and print the single coverage line last; require the quote to be copy-pasteable from the fetch (M3, M5).** And test the "waiting on you" exit with a scenario where the lead leaves the task stalled (M4).

## Metrics
| Metric | Value |
|---|---|
| User turns / commands / files read by user | 5 / 0 / 0 |
| Time: plan / approval / org running / first FAIL surfaced / delivery | 0:53 / 1:00 / 1:16 / 12:16 / 18:58 |
| Org agent runs | 23 (cap 25): lead 12, researcher 4, factcheck 4, writer 3 |
| Web calls | researcher 19 fetch + 7 search; factcheck 41 fetch + 3 search; writer/lead 0; 0 failed |
| Permission denials | 0 |
| `progress(wait_seconds)` | 6 (3 effective, 3 immediate "nothing to wait for"), 1 `sleep` poll, "status?" turns 0 |
| Fact-check passes | draft 22/28 FAIL; findings 32/39 -> 34/39 FAIL (re-check of notes, not draft) |
| Spot-check | 2 wrong, 1 unsupported, 1 misleading, 2 confirmed (6) |
| Scheduler | 2 starts, both exited by themselves, 0 SIGTERM |
| Deliverable | 437 words, unchecked, KNOWN-ISSUES file |
| Score | 2.5/5 |

## Safety check
Before (21:49:24) vs after (22:15:17): `~/.kiro/settings/mcp.json` md5 `3eacba4e4479ae692c3dae8761b14b73` unchanged; the five pre-existing `~/.kiro/agents/orgmcp*.json` md5 unchanged; the only new files were the two per-org profiles `orgmcp-orgmcp-a4-1792270163-org-7c37f7{,-web-fetch-web-search}.json` (reference `$S/org`; deleted at cleanup after being listed); main checkout `git status --short` empty before and after; main HEAD 93cca0a; live org HEAD `5b94a6b` before and after, no mention of this scenario. No `mcp.json`/settings reads in transcripts, session tool calls or run logs. Agents and assistant wrote only under `$S` (assistant shell: `sleep`/`tail`/`ls`/`cp`/`cat` heredoc into `$S/deliverables`). Caps: 23 of 25 runs, 5 of 8 turns, ~19 min. 0 processes referencing `$S` remained; `$S` removed.
