# Study A5: research org, final regression #3 WITH the skill (rounds 8-9)

Facilitator: UX research. Product: orgmcp main @ 7ff93ad (worktree `final-a5`, branch `study/a5-research`). Persona Maya (same 7 hidden needs as A2-A4). Assistant: kiro-cli `assistant` profile (claude-sonnet-5.5, `tools:["*"]`, orgmcp MCP with `ORG_ROOT=<S>/org`, org dir NOT pre-created, skill via `skill:///.../SKILL.md`).
Sandbox `S=/tmp/orgmcp-a5-1792273159`, 2026-10-17 22:39:43-22:58:02 local (**18 min 19 s**, 4 user turns). Evidence: `evidence/`. Comparison: `studies/A4-research-final2/STUDY.md` (2.5/5), `studies/A3-research-final/STUDY.md` (3/5).

## TL;DR
First run where the lead behaved as designed and the org delivered a file that passed its own checker. The lead (sonnet-4.6) delegated strictly sequentially (research -> write -> check), sent zero status messages, routed every rework to the **writer** with `revises`, and had **the same file** re-checked; after the second failed check (22 of 25) it stopped with `blocked` + options A/B/C instead of researching more. The assistant relayed the options, Maya picked A, and the final `done` pasted the coverage line verbatim: "**25 of 25 factual claims verified (25 = 25 required); 0 wrong, 0 unsupported, 0 not-checkable; 7 judgement statements, each resting on verified facts: yes**" (ledger path included). 22 of 25 runs (A4: 23, A3: 24), no stranded runs, three schedulers all exited by themselves, 0 permission denials, 0 "status?" turns, `progress(wait)` worked after every grant and listed every unread root note.
Not fixed: the verification is still not trustworthy. The lead's first `done` ("all criteria met", 25 of 25) was **false**: the "Where we can win" section still contained new prices/counts and a wrong heading, and the checker had answered "judgement ... yes". The assistant caught it by reading the file (not the checker), and it took a third rework. And the final "25 of 25" still lets through the Joplin Server licence trap (3rd study in a row), two "verified" rows that rest on absence/other pages, and a thin generic win-section (518 words).
**Score 3.5/5** (A4 2.5, A3 3, A2 4). Process, honesty, cost and speed are now first-rate; the deliverable is correct enough to use but not fact-checked as claimed.

## Focus items (a)-(h)
| | Result |
|---|---|
| (a) Lead model and behaviour | **Sonnet-4.6 lead (plan said so and the assistant flagged it as a deviation; Maya approved).** Messages the lead sent (14): 7 tasks (researcher, writer, factcheck, rework, re-check, targeted fix, re-check), 1 rework to the writer in each of the 2 fix cycles, 4 results, 1 budget note; **0 status/"waiting" messages**; one empty run (`health`: "empty 1") = waking to read root's budget grant. **Sequential**: researcher 21:40:52Z, writer only after research arrived 21:42:39Z, factcheck only after the writer reported 21:43:42Z. **Rework to the author with `revises`** (21:46:24Z `revises` the writer task, 9 required changes copied verbatim from the ledger), **re-check names the same file** (`lead/writer/work/competitors.md`, `revises` the first check). After the first failed re-check the lead reported `blocked` with options (cut/fix/accept) rather than another research cycle. |
| (b) Verdict + coverage line in `done` | **Yes, three times.** Final `done` (msg `...-lead-26db`): "Fact-checker's final coverage line (verbatim): Coverage: 25 of 25 factual claims verified (25 = 25 required); 0 wrong, 0 unsupported, 0 not-checkable; 7 judgement statements, each resting on verified facts: yes" + ledger path. Totals add up (25, F1-F24 + F16b). **But** the earlier pasted line (same 25 of 25, "10 judgement statements ... yes") accompanied a document whose win-section contained "€28-95/year", "€80.28/year per user", "three of five ... AGPL-3.0", "only Joplin and AnyType ...", "growing segment" and a heading with a suffix: criterion 5 was violated and neither checker nor lead noticed; the assistant did (evidence/assistant-tool-calls.txt: `grep` of the ledger for those strings). Pasting the line is not enough if the line is wrong. |
| (c) My spot-check (web access: yes) | **0 wrong, 1 misleading (material), 2 partly unsupported, 3 confirmed of 6** (A3: 1 wrong/1 unsupported/1 misleading of 5; A4: 2/1/1 of 6). See below. |
| (d) Runs and budget | **22 of 25**: lead 13, writer 4, factcheck 4, researcher 1 (A4: 23: lead 12/research 4/factcheck 4/writer 3). Plan: 22 planned, 3 reserve. Overhead lead 13/22 = 59%. Budget flow: root 25 -> lead 22 (researcher 4, writer 3, factcheck 3, lead keeps 12); first result returned 10; root `delegate(revises, budget=4)` (used 5 - progress said "runs 5 of 4"), then `delegate(budget=4)` + `send(budget=3)` for the third fix; **final state: every agent budget 0, no stranded runs**. `reclaim` was never needed and never used (nothing to reclaim). The assistant told Maya "23 runs against 22 planned, 3 extra"; the logs say 22 (the 22 planned): it double-counted the grant. |
| (e) `progress(wait)` | **Worked every time**, 6 waits (600 s requested): "Changed after waiting 9m: ... working -> blocked ... Needs you: blocked result from lead ..." ; after the grant+start: "Changed after waiting 3m: ... working -> done"; after `send(budget=3)`: "Changed after waiting 30s: new item for you: Needs you: note from lead 'Budget needed: 2 more runs to complete fact-check'" (the lead's note was listed immediately, A4 failed here); "Changed after waiting 2m: ... working -> done". No "Nothing to wait for" after any grant (A4: 3x), no `sleep` poll, 0 "status?" turns. "Needs you" listed both the blocked result and the unread note. Counter blemishes: "runs 5 of 4", "runs 6 of 7 (1 returned)". |
| (f) Scheduler exit | **Three schedulers, all `scheduler exiting: finished: no open tasks`, by themselves** (21:50:26Z, 21:54:29Z, 21:57:47Z). No `stop` needed or called; `progress` final: "scheduler: stopped (finished: no open tasks)". The "waiting on you" exit was not exercised (the lead `blocked` each time again). 0 processes left. |
| (g) Plan block | **Verbatim** (diff: identical except the product's own instruction suffix "(show this to the user exactly as written)"), intro lines added by the assistant, `apply_org(approved=True, plan_id='0a306cdd2064')` (same id), failure-policy line present and **honoured**: "If the check still fails after one rework, I'll come back to you with options before spending the reserve (about 5 runs)". Lead model: the blueprint used `model: strong` for the lead, so no `manager-cheap-model` warning fired; the assistant itself disclosed it ("The lead is also on the strong model") and Maya approved. Only validator warning (deliverable path outside agent write scope; assistant copies + verifies) was explained and acted on: `cp` + `cmp`, then `wc -w` 518. |
| (h) Permission denials | **None.** grep of all 22 run logs for `denied|non-interactive`: 0; `status: Failed` only the real 404 (`joplinapp.org/help/apps/sync_config/`). `ORG_REQUIRE_AGENT=1` fine. The "Dynamic registration failed ... lessthan.ai" line is environment noise. |

## Spot-check of the delivered `competitors.md` (live web, 2026-10-17; web_fetch + raw `curl` where the text extractor dropped content)
1. **Joplin licence "AGPL-3.0-or-later" next to "self-hosted €2.50-3.33/user/month" (cited github.com/laurent22/joplin/blob/dev/LICENSE): MISLEADING, material.** The cited LICENSE says "All code in this repository is licensed under the AGPL-3.0-or-later License **unless a directory contains a LICENSE or LICENSE.md file** ... packages/server contains a LICENSE.md file", and that file is the *Joplin Server Personal Use License* (personal non-commercial only; forbids installing it on your server for others for a fee). The ledger's F11 "verified" quote cuts the sentence exactly at "unless a directory contains a LICENSE ...". The researcher's notes had the carve-out; the writer dropped it; the checker saw it and did not apply the exception check the template requires. Same trap as A2/A3/A4; the cell no longer says "Joplin Server is AGPL" outright, so I class it misleading rather than wrong.
2. **Obsidian sync cell "Local only; paid Sync with E2E encryption; third-party file sync" (cited obsidian.md/sync): PARTLY UNSUPPORTED.** /sync confirms AES-256 E2E; "local only" is on /pricing and /license, not the cited page; "third-party file sync" is on none of the three pages. Ledger F6 verifies the cell with a /pricing quote (not the cited URL). Omission: the table never says there is no official self-hosted Obsidian server, the fact that matters most in a self-hosting comparison.
3. **Obsidian "Sync $4-5/month, Publish $8-10/month, Commercial $50/year" (obsidian.md/pricing): CONFIRMED.** Correction to A4: `web_fetch` returns the page without the price block, but the raw HTML contains "Sync $4 ... billed annually / $5 ... billed monthly; Publish $8 / $10; Commercial $50 USD per user per year". The checker's verbatim quote was real; A4's M3 ("quote not reproducible") was a text-extraction artefact, not a checker error.
4. **Logseq "Sync in beta requiring $5-15/month Open Collective contribution" CONFIRMED at the cited blog (a 2022-era beta page, status today unknown); "third-party file sync (free)" UNSUPPORTED.** The page only tells users *not* to keep a Sync graph in iCloud/Dropbox/OneDrive folders; the ledger's F15 verdict is "no mention of a charge" = verified by absence.
5. **Trilium "optional third-party hosting $3.50/month or $36/year; custom domain $52/year" (trilium.cc): CONFIRMED**, and now correctly labelled as third-party hosting (A4: misleading).
6. **AnyType "Business €20/editor/month or €300/month self-hosted; MIT (infrastructure); Source Available for apps; Business cloud not zero-knowledge; self-hosted coming soon": CONFIRMED** (business.anytype.io, blog.anytype.io/our-open-philosophy). Side note: "Free tier" cited to anytype.io/pricing is true (raw HTML: "Free 100 MB of remote storage") although the text extractor returns nothing; the checker verified the claim from doc.anytype.io, i.e. not the cited URL; the org's first check had flagged the true "100 MB" claim as unsupported and the lead had it removed (information lost because of a fetch limitation).
Bonus: Joplin Cloud €2.99-9.99/month and Server Business 2.50/2.92/3.33 €/user/month: CONFIRMED on joplinapp.org/plans; "Joplin sync: third-party" is on /help/apps/sync/, not the cited /plans.
Tally of the 6: 3 confirmed, 1 misleading, 2 partly unsupported, 0 wrong. Of the flawed ones the org's own ledger caught none in the final pass.
Content: table is the useful part; "Where we can win" is seven generic paragraphs (no numbers, now compliant) that do not use the concrete openings the facts offer (Joplin Server is not free for commercial self-hosting, Obsidian has no self-hosted server, Logseq Sync still a beta, AnyType self-hosting "coming soon"). Mechanical: file at `<S>/deliverables/competitors.md` (identical to the writer's file by `cmp`), 518 words by `wc -w` (484 by the org's `read`), 5-row table, heading exactly "Where we can win" with an italic "Our assessment (judgement)" line, no URLs inside it.

## Timeline
| Time | Event |
|---|---|
| 22:39:43 | Turn 1, opening verbatim. Skill read, `status`, ONE 7-item checklist with defaults: asks for the apps ("I won't pick them for you"), proposed the path (`<cwd>/deliverables/`), a "short recommendation section", "estimate the number of runs and add 25%". |
| 22:39:52 | Turn 2: Maya answers every item (5 apps; pricing/license/sync; file path + 1500 + table + "Where we can win"; URLs that state the claim + web; independent checker; cheap draft/strong review, ~25 runs; plan first; told when done). Plan at 22:40:17 (**0:34** after opening); offers to wait. |
| 22:40:23 | Turn 3: "approve. Yes, wait here and tell me when it's done." `create_org`, `apply_org(approved, plan_id)`, `start` 22:40:39 (**0:56**). Single `progress(600)` returned at 10:43 with the lead's `blocked` (22 of 25, runs 11 of 22); assistant read the message via `inbox` and ended the turn with the options (A recommended: 2 runs). |
| 22:50:53 | Turn 4: "Yes, go with A. Not beyond 25 total." `delegate(revises, budget=4)` + `start`; waits; reads the file itself and finds two violations (heading, new facts in win-section) although the lead had reported done; second `delegate(revises)`; lead asks for 2 more runs - `send(budget=3)` crossed with it; waits; reads file + ledger; `cp` + `cmp` + `wc`. Final reply 22:58:02 (**18:19**). |
Maya was never asked "deliver as is vs spend more" (it finished within 22 runs), so the "short answer please" line was not needed; the reply was a 6-bullet check list + one paragraph (~20 lines, longer than "short").

## Setup path and skill use
`read SKILL.md` -> `status` -> [checklist] -> `blueprint_example` -> `propose_org` -> [verbatim plan] -> `create_org` -> `apply_org(approved, plan_id)` -> `start` -> `progress(600)` -> `inbox` -> [decision] -> `whoami` -> `delegate(revises)` -> `start` -> `progress` -> `inbox` -> `read` -> `grep` -> `delegate(revises)` -> `start` -> `progress` -> `inbox` -> `status` -> `send(budget=3)` -> `progress` -> `inbox` -> `read` -> `grep` -> `shell cp/cmp/wc` -> `progress`. No orgmcp errors; no read of `mcp.json`/settings (grep of transcripts, session tool calls and run logs). Skill shaped: single checklist, no invented scope, verbatim plan + plan_id + approval gate, waiting via `progress`, ask-before-exceeding-plan, verifying the deliverable itself (it rejected the lead's `done`), copy-and-verify. Not seen: `stop` (not needed), `reclaim`.

## Org as built
```
root (human)
└─ lead        Manager, sonnet-4.6, web_fetch+web_search, budget 22 (+4, +4, +3 granted over three root tasks)
   ├─ researcher  haiku-4.5, web, budget 4 (1 run)
   ├─ writer      haiku-4.5, @orgmcp only, budget 3 (4 runs)
   └─ factcheck   sonnet-4.6, web, budget 3 (4 runs)
```
Same shape as A2-A4. 7 acceptance criteria incl. facts vs judgement, quoted sentence, coverage line, and "final report pastes it". Independent review present. Rework budget reserved: the lead had 12 for planning/checking/rework and did fund the writer's reworks (A4's deadlock gone).

## Needs coverage
| # | Need | Elicited | In plan | Met |
|---|---|---|---|---|
| 1 | Scope: 5 apps | Asked | Yes ("exactly") | **Yes** |
| 2 | URL per claim that states it; web | Asked | Yes | **Mostly**: per-cell links; a few cells cite a page that does not state all parts (Obsidian sync, Joplin sync, Logseq free sync) |
| 3 | <= ~25 runs, cheap draft, strong review | Asked ("add 25%" default proposed first) | Yes (22, cap 25) | **Yes**: 22 of 25 |
| 4 | Approve plan first | Asked | Yes | **Yes** |
| 5 | One file, path, <= 1500, table, "Where we can win" | Asked (path proposed, Maya gave hers) | Yes | **Yes** (518 words, generic win-section) |
| 6 | Told when done, no digging | Offered, accepted | Yes | **Yes** (0 "status?", Maya read no file; final reply long) |
| 7 | Facts checked by someone else | Asked | Yes | **Partly**: independent checker, n = m reached, but the check missed the Joplin licence carve-out, accepted absence as evidence, and passed a non-compliant win-section once |
Elicited 7/7, met fully 5, partly 2, not met 0 (A4: 4/3/0; A3: 4/2/1).

## Comparison
| | A3 | A4 | A5 |
|---|---|---|---|
| Time / user turns | 33:24 / 5 | 18:58 / 5 | **18:19 / 4** |
| Runs (cap 25) | 24 | 23 | **22** |
| Lead | haiku, 14 runs | haiku 12 runs, parallel premature delegation, status msgs | sonnet 13 runs, sequential, no status msgs |
| Rework routing | to lead, 2 cycles, last unchecked | to researcher, wrong file re-checked | **to writer, same file re-checked** |
| Final verdict | FAIL, delivered unverified | FAIL, delivered unfixed draft | **PASS 25/25 pasted in `done`** (but one false earlier "done") |
| Spot-check (wrong/unsup./misl. of n) | 1/1/1 of 5 | 2/1/1 of 6 | **0/2/1 of 6** |
| Scheduler | 1 SIGTERM | 2 self-exits | 3 self-exits |
| `progress(wait)` | 8 ok | 3 of 6 "nothing to wait for", missed note | **6 of 6 ok, note listed** |
| Denials | 0 | 0 | 0 |
| Score | 3 | 2.5 | **3.5** |

## Friction log (ranked)
| # | Sev | Friction | Evidence | Component |
|---|---|---|---|---|
| H1 | **High** | The verifier still cannot be trusted on the one check that matters for this user: the Joplin Server licence carve-out passed again (3rd study in a row) although the quoted source sentence contains "unless a directory contains a LICENSE ..."; the exception check for sub-package licences is not enforced | ledger F11 vs LICENSE text; researcher note line 69 | `fact-checker` template: when a quoted licence sentence has "unless/except", the checker must follow it (open the named file) and report the sub-licence; lead/writer: carry researcher caveats into the table |
| H2 | **High** | The lead reported `done` with 25 of 25 and "all acceptance criteria met" while criterion 5 (win-section has no new facts) and the exact heading were violated; the checker said "10 judgement statements ... yes". Only the assistant's own read caught it (and cost a third rework and 6 more runs) | `lead-...-463e` vs root `...-dfe0`; ledger | `fact-checker`: check the judgement section for digits/currency/"only/all/most" tokens mechanically and fail it; `manager`: run the same grep/read before `done` |
| M1 | Medium | "verified" rows still rest on absence or on a different page than the cited URL (Logseq "third-party sync (free)": "no mention of a charge"; Obsidian sync cell verified from /pricing; AnyType "Free tier" from doc.anytype.io); the final pass re-fetched 2 pages and carried 25 rows over "unchanged" | ledger F6, F15, F19/F20; final run log (2 fetches) | `fact-checker` template: a row is `verified` only with a quote from the cited URL fetched in this run; "no mention" = unsupported |
| M2 | Medium | Text extractor hides content (Obsidian price block, anytype.io/pricing blank), producing false "unsupported" (true "100 MB" claim deleted) and the lead acts on it | A4 M3 reproduced; raw HTML has the prices | Tool/guidance: checker may retry raw/alternative page; lead should prefer "re-check with another source" over deleting a fact |
| M3 | Medium | Root budget sizing: the assistant gave 4 runs for a writer+check cycle that needs about 6 (wake x3 + writer + checker); the lead had to ask for more (crossed with the root's own grant) and one run was spent just reading the grant note | lead note `...-0afa`, `health` "empty 1" | Skill: size a rework grant as 2 per delegation + 1 for the report |
| L1 | Low | Assistant mis-stated usage ("23 runs ... 3 extra") when the logs show 22 = plan | turn-4 vs run-counts | Skill: quote `progress`/`health` run counts verbatim |
| L2 | Low | Counters: "runs 5 of 4", "runs 6 of 7 (1 returned)" | progress outputs | Product (task budget accounting) |
| L3 | Low | Final reply ~20 lines although the user wanted it short; checklist proposed an output path and "+25%" default | turn-4, turn-1 | Skill |
| L4 | Low | "Waiting on you" scheduler exit still unexercised (lead always ends `blocked`) | scheduler.log | Test gap |
What worked: sequential delegation, no polling, author-routed rework with `revises`, same-file re-check, stop-at-FAIL with options, coverage line in `done`, three self-exiting schedulers, progress(wait) + "Needs you", verbatim plan with honoured failure policy, assistant independently verifying and rejecting a false `done`, 0 denials, no stranded budget, speed.

## Recommendations (ranked)
1. **Make the licence exception check mechanical** (H1): for any licence claim, the checker lists every `LICENSE*`/"unless/except/other than" sentence on the cited page and opens the referenced file; claims about a product with a server/sub-package carry the sub-licence in the table. This is the trap four studies in a row.
2. **Gate `done` on a mechanical judgement-section scan** (H2): digits, currency symbols, "only/all/most/three of" in the win-section fail the check; the manager runs the same scan on the file before reporting.
3. **`verified` only with a quote from the cited URL fetched in this run** (M1); "no mention of" and "found elsewhere" are `unsupported`/`partial`; re-fetch after any edit of the cited cells.
4. **Fetch fallback** (M2): when a page returns blank/thin text, try the raw page or a mirror before declaring unsupported; the lead must not delete a claim that only failed to render.
5. **Skill: grant sizing and quoting** (M3, L1): 2 runs per delegation + 1 for the report; quote run counts from `progress`; keep the final to 5 lines when the user says "short".

## Metrics
| Metric | Value |
|---|---|
| User turns / commands / files read by user | 4 / 0 / 0 |
| Time: plan / approval / org running / first result (blocked) / delivery | 0:34 / 0:40 / 0:56 / 10:43 / 18:19 |
| Org agent runs | 22 (cap 25): lead 13, writer 4, factcheck 4, researcher 1; budgets all 0 at the end |
| Fact-check passes | check 1 FAIL (9 issues), re-check 22/25 FAIL, targeted 25/25 (pass, false: win-section), full 25/25 PASS |
| Web calls (factcheck fetches per run) | 12, 18, 4, 2 (+ researcher 10 fetch/6 search); 1 failed (404) |
| Permission denials | 0 |
| `progress(wait_seconds)` | 6, all effective; "status?" turns 0 |
| Schedulers | 3 starts, 3 self-exits, 0 SIGTERM |
| Spot-check | 3 confirmed, 1 misleading, 2 partly unsupported, 0 wrong (6) |
| Deliverable | 518 words, table + judgement section, honest |
| Score | 3.5/5 |

## Safety check
Before (22:39:20) vs after (23:04:42): `~/.kiro/settings/mcp.json` md5 `3eacba4e4479ae692c3dae8761b14b73` unchanged; the five pre-existing `~/.kiro/agents/orgmcp*.json` md5 unchanged; only new files the two per-org profiles `orgmcp-orgmcp-a5-1792273159-org-27cc27{,-web-fetch-web-search}.json` (reference `$S/org`; copied to evidence, deleted at cleanup); main checkout `git status --short` empty before and after; main HEAD 7ff93ad; live org HEAD `5b94a6b` before and after, no mention of this scenario. No `mcp.json`/settings reads in transcripts, session tool calls or run logs. Caps: 22 of 25 runs, 4 of 8 turns, ~19 min. No process referencing `$S` remained; `$S` removed.
