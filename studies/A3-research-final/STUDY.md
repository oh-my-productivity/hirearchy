# Study A3: research org, final regression WITH the skill

Facilitator: UX research. Product: orgmcp main @ 68b44c5 (worktree `final-a`, branch `study/final-research`). Persona Maya (same 7 hidden needs as A / A2). Assistant: kiro-cli `assistant` profile (claude-sonnet-5.5, `tools:["*"]`, orgmcp MCP with `ORG_ROOT=<S>/org`, org dir NOT pre-created, skill loaded via `skill:///.../SKILL.md`).
Sandbox `S=/tmp/orgmcp-a3-1792266280`, 2026-10-17 20:45:11-21:18:35 local (33 min 24 s, 5 user turns). Evidence: `evidence/`.
Comparison: `studies/A2-research-skill/STUDY.md` (score 4/5).

## TL;DR
The process is clearly better than A2; the result is worse. PLAN FOR YOU was shown (almost) verbatim and `apply_org` used `approved=True, plan_id=bc1ec8d8c673`; "tell me when done" worked through `progress(wait_seconds)` (8 waits of 2-5 min, zero "status?" turns); the fact-checker produced a real claim ledger (88 rows, "n of m" coverage, 91 claims in the final pass vs 10 in A2); no permission denials from the new confinement profiles; the assistant again refused to accept the lead's "done" and sent the draft back with `delegate(revises=)`. But the acceptance criterion "n of m verified with n = m" could not be met (the writer's 10-section "Where we can win" is mostly opinion with decorative citations, 21 claims "not checkable"), so the org burned 24 of 25 runs in two fix cycles and ended with a **FAIL** verdict from its own checker (52 verified, 5 wrong, 13 unsupported, 21 not checkable). Maya chose to stop at 24 and take the draft unverified; the assistant delivered it honestly labelled. The scheduler did not exit on its own at the end (open, budget-stalled rework task); I had to SIGTERM it.
**Score 3/5** (A2 4/5): structure, process and honesty are 5-level, the factual deliverable and the "facts checked" need are not met.

## Focus items (a)-(e)
| | Result |
|---|---|
| (a) PLAN FOR YOU verbatim + `plan_id` | **Yes.** Turn 2 shows the whole block from `PLAN FOR YOU` to `END OF PLAN FOR YOU` word for word (only the product's instruction line "(show this to the user exactly as written)" and the `Target organization` line were left out), then two short notes. `blueprint_example(research)` -> `propose_org` -> after "approve": `create_org` -> `apply_org(approved=True, plan_id="bc1ec8d8c673")` (same id as in the propose output) -> `start`. Plan at 0:32 after the opening message, approval at 0:38, org running at ~1:00 (A2: 1:23 / 1:31 / 1:48). One blemish in the product output itself: `Goal: ... Focus on pricing, license and...` is cut with a literal "..." (evidence/propose_org-result.txt). |
| (b) fact-check depth | **Much deeper, still not reliable.** `lead/factcheck/work/ledger.md`: 88 rows `ID / claim quoted / location / cited source / verdict / evidence`; verdict counts 54 verified, 3 partial, 11 unsupported, 5 wrong, 15 not-checkable; `final_verification.md` reports "91 claims examined ... verified 52, wrong 5, unsupported 13, not-checkable 21, Total 91" (the template's n-of-m coverage, an explicit **FAIL**). A2: 10 hand-picked claims, 0 errors. The org caught real errors (AnyType EUR20 cited to the wrong page, Logseq claims, Obsidian "defaults to cloud", a 404 Joplin link). **My spot-check of 5 claims (with web access): 2 errors and 1 misleading claim not or only partly caught (below)** vs A2's 2 of 3 misleading. The checker still verified by plausibility in places (C15 "Free desktop/mobile ... universally known and not contradicted by the cited source"), and its rework pass flagged the broken `github.com/joplin/server` URL but not that the claim itself is false. |
| (c) "tell me when done" | **Worked.** After I accepted the assistant's offer ("I can wait here ... I'll reply as soon as it finishes"), turn 3 stayed alive 28 min 46 s and the assistant called `progress(wait_seconds=240/240/300 ...)`; each return was either "Waited 4m: no task finished ... Call progress(wait_seconds=...) again" or "Changed after waiting 3m: ... working -> done". 8 waits in total across turns 3-4; **0 "status?" turns and no sleep/poll loop**. It then checked the result itself and kept working in the same turn. (A2: 5 "status?" turns.) |
| (d) scheduler exit | **Partly.** First scheduler (pid 25941) exited by itself: `scheduler exiting: finished: no open tasks` right after the first task reported `done`. After the assistant's `delegate(revises)` it correctly called `start` again (pid 28857). That second scheduler never exited: the rework task stayed open ("stalled (lead is paused: budget). runs 13 of 16") because the lead had 0 budget, so `until_done` kept an idle daemon alive for 23 min (from 20:58 until my SIGTERM at 21:22). The assistant never called `stop` and never closed the task after deciding to deliver unverified. `progress`/`health` said `scheduler: running` and `!out_of_budget`. |
| (e) permission denials | **None.** grep of all 24 run logs for `denied`, `not supported in non-interactive`, `permission`: only hits are charter text. Two `[tool] status: Failed` lines are real HTTP 404 fetches (`github.com/joplin/server`). Profiles (evidence/orgmcp-orgmcp-a3-...json): lead/researcher/factcheck `tools=@orgmcp,web_fetch,web_search` (`...-web-fetch-web-search`), writer `tools=@orgmcp`; `ORG_REQUIRE_AGENT=1`; every run started and wrote its `work/` and `MEMORY.md` files through the orgmcp tools. The new confinement profiles ran end to end without a single refusal. |

## Timeline
| Time | Turn | Event |
|---|---|---|
| 20:45:11 | 1 | Opening message (verbatim). Assistant loads the skill (`[tool] Reading SKILL.md`), `whoami`, then ONE 7-item checklist with defaults. **Scope: it asked** ("I won't pick them for you") - fixes A2's G6. |
| 20:45:20 | 2 | Maya answers every item (5 apps; pricing/license/sync + "Where we can win"; path and 1500 words; URLs that state the claim; independent checker; <= ~25 runs, cheap draft / strong final review; show plan first; told when done). Plan at 20:45:43. Assistant also offers to wait. |
| 20:45:49 | 3 | "approve. Yes, wait here and tell me when it's done." `create_org`, `apply_org`, `start` at 20:46:05. Waits 3x -> first task `done` at 20:57:51 (12:40 after the opening; 11 of 22 runs). Assistant opens the draft, `wc -w`, reads factcheck's ledger, finds 3 criteria unmet (heading "Where We Can Win" not exact; many claims in "Where we can win"/Summary with no URL; ledger not n = m) although the lead's `done` report says "complete and fact-checked ... Every factual claim has a source URL", and sends it back: `delegate(to=lead, revises=..., budget=10)`, `start`. More waits; grants 2 runs (`send budget=2`) for a full re-verification. Turn ends at 21:14:35 with a decision request: 21 runs spent, factcheck FAIL with 4 problems, "grant 4 runs? ends at exactly 25". |
| 21:14:45 | 4 | Maya: "Yes, grant the 4 runs, but not beyond 25." `send budget=4`, waits, reads files. Ends 21:18:09: 24 of 25 used, lead out of budget, last fix applied but unchecked; options: grant 3 more (27, over the cap) / deliver unverified / deliver nothing. |
| 21:18:17 | 5 | Maya: "Not going over 25. Option 2 ... short answer please." `cp` + `cmp` to `<S>/deliverables/competitors.md` (1284 words). Reply: draft at the path, "not fully fact-checked", lists the unverified claims from the last pass (~25 lines, not short). Does not call `stop`. |

## Setup path and skill use
`read SKILL.md` (visible in transcript) -> `whoami` -> [checklist, no tool] -> `blueprint_example` -> `propose_org` -> [plan] -> `create_org` -> `apply_org(approved,plan_id)` -> `start` -> `progress(wait)` x8 -> `read`/`inbox`/shell reads -> `delegate(revises)` -> `start` -> `send(budget)` x2 -> `cp`. No orgmcp errors. No read of `mcp.json`/settings (grep of transcripts, session tool calls and all run logs: none). The skill visibly shaped: the single checklist, no invented scope, verbatim plan, approval gate, `plan_id`, waiting via `progress`, rework by `revises` instead of patching, refusing to exceed the cap, honest final caveat.

## Org as built
```
root (human)
└─ lead        Manager, haiku-4.5, web_fetch+web_search, budget 22 (own 7 + rework 3 + slack 5 = keeps 15), +10 rework, +2, +4 granted
   ├─ researcher  haiku-4.5, web_fetch+web_search, budget 3  (1 run, then "out of budget, paused" after 1)
   ├─ writer      haiku-4.5, @orgmcp only,           budget 2  (5 runs)
   └─ factcheck   sonnet-4.6, web_fetch+web_search, budget 2  (4 runs)
```
Same shape as A2 (the blueprint template did not change the shape). Acceptance criteria (6): exact 5 apps; <= 1500 words; table with 5 rows and pricing/license/sync columns; heading exactly "Where we can win"; every claim has a URL that states it; **factcheck's coverage report shows n of m claims verified with n = m, none wrong, none unsupported, and the writer applied every required change**. Review step present and independent (factcheck cannot edit the writer's file). No workspace.

## Execution
Runs: lead 14, writer 5, factcheck 4, researcher 1 = **24 of 25** (plan: 22 ceiling, "minimum for one review and rework is 17"). Manager overhead 14/24 = 58% (A2: 50%). First pass 11 runs; the two fix cycles after the assistant's rework request used 13 more (the last fix by the writer was never re-checked). Budget travelled back with `done` reports ("11 returned") and the assistant used `send(budget=)` for the extras, each time asking Maya before exceeding the plan. Stalls: lead, researcher paused on budget (by design); no refusals/escalation loops/write-guard conflicts. Cheap models drafted, sonnet-4.6 only on factcheck, as requested.
Progress answers (verbatim from `progress(wait)`): "Waited 4m: no task finished, got blocked or stalled, and nothing new needs you. Call progress(wait_seconds=...) again to keep waiting. ... running: lead/writer. runs 4 of 22." and "Changed after waiting 3m: ... working -> done ... runs 11 of 22 (11 returned)." The assistant never reported these to Maya mid-turn (single-turn reply), only the final decision requests.

## Needs coverage
| # | Need | Elicited | In plan/blueprint | Met by result |
|---|---|---|---|---|
| 1 | Scope: 5 apps | **Asked**, no invented default | Yes (criterion 1, "exactly") | **Yes**: exactly the 5 in table and text |
| 2 | URL per claim that states it; web access | Asked (item 4) | Yes: web tools, criterion 5 | **Partly**: 5/5 table rows cited, every bullet has a URL, but URLs are often pages that do not state the claim (e.g. "Obsidian: proprietary cloud creates trust concerns" -> license page; "Logseq: small ecosystem" -> LICENSE.md) |
| 3 | <= ~25 runs, cheap draft, strong final review | Asked (item 6) | Yes: cap 25, planned 22 | **Yes** but tight: 24 of 25 (plan: 22 ceiling, 17 minimum); two budget decisions pushed to Maya |
| 4 | Approve plan first | Asked (item 7) | Yes | **Yes** (nothing created before "approve") |
| 5 | Path, <= 1500 words, table, "Where we can win" | Asked (item 3) | Yes | **Yes**: file at path, 1284 words (`wc -w`), 5-row table, section headed exactly "Where we can win" (fixed on rework) |
| 6 | Told when done without digging | Asked (item 7 wording) + assistant offered to wait | Yes ("One line when I ask") + wait offer | **Yes**: waited in conversation via `progress(wait_seconds)`, Maya never typed "status?" and read no file. Caveat: "done" came with a decision request, and the final reply was long |
| 7 | Facts checked by someone other than the writer | Asked (item 5) | Yes, 'n of m, n = m' | **Partly / No**: checked by an independent agent twice with a real ledger, but the final file is unverified after the last fix and its last verdict was FAIL (5 wrong, 13 unsupported); delivered with an honest list |

Elicited 7 of 7, met fully 4, partly 2, not met 1 (A2: 4/3/0 but with a passing, if shallow, check).

## Deliverable check (done by me, with web access)
Mechanical: file at the path, identical to the writer's file (`cmp`), 1284 words, exactly 5 apps, 5-row table, heading "Where we can win". Spot-check of 5 claims against their cited URLs:
1. **Joplin "Joplin Server: free to self-host under AGPL-3.0" (cited github.com/laurent22/joplin repo root): WRONG.** `packages/server/LICENSE.md` is the *Joplin Server Personal Use License*: personal non-commercial use only; installing it on a server to give others access for a fee or for commercial purposes is forbidden. The draft before the rework said "free personal non-commercial" (right, but cited to a forum post, so the checker called it unsupported); the writer "fixed" it by replacing it with a false claim cited to a page that does not state it, and the checker's last pass flagged only the dead URL. Material for a company building a competing self-hosted app. (A2's spot-check found the same trap.)
2. **Logseq "Plaintext sync with any file service ... custom sync server URLs supported" (cited blog.logseq.com/how-to-setup-and-use-logseq-sync): UNSUPPORTED** by the cited page (it describes only the 2022 Open Collective-gated Sync beta; the "$5+/mo sponsorship" half of the cell is confirmed there, but is a 2022 beta page for a feature that has since changed). The checker marked the custom-URL part verified against a different URL and the plaintext part unsupported, and the final file still has it.
3. **Obsidian "Cloud-only via Obsidian Sync ... no official self-hosted server" (cited obsidian.md/pricing, /sync): MISLEADING.** The pricing page confirms AES-256 E2E for Sync and that notes are stored locally, but not "cloud-only"; Obsidian vaults are plain local folders that people sync with any file-sync tool, which matters for a self-hosting comparison. The checker verified it (C06/C07). Also the "$50/user/year" Commercial price is not in the fetched page text (the FAQ confirms the license is optional).
4. **AnyType "EUR20/editor/mo"; "self-hosted business EUR300/mo flat (coming soon)"; "50% student/educator discount" (business.anytype.io, doc.anytype.io memberships): CONFIRMED** (all three, page texts quoted in the pages).
5. **Trilium "Built-in self-hosted sync server; 3rd-party hosting; free and open source" (TriliumNext README): CONFIRMED.** (Also Joplin Server Business 2.50 EUR/user/month at 51+ users: confirmed on joplinapp.org/plans, arithmetic EUR250 for 100 users OK.)
Result: 2 clear errors + 1 misleading out of 5; the org's own last ledger flagged #2 only, and left #1 and #3 as verified/unnoticed. A2: 1 of 3 confirmed, 2 misleading, 0 caught by the org. So: depth of ledger far up, error rate in the delivered claims about the same, and the org's honest FAIL means Maya was told it is unverified (A2 told her "all criteria met" with a smaller caveat).
Quality of content: the 10-point "Where we can win" is generic (MIT licence, plugin revenue share, mobile-first, "HIPAA, GDPR, SOC 2") and half of it is assertion attached to a URL ("Joplin: weaker ecosystem despite extensibility" -> plans page). Table is the useful part.
**Score 3 / 5.** Right place, length, scope, sections; best process so far; honest outcome. Not higher: the checked-facts need was not met, the deliverable has a material licensing error, and 24 of 25 runs were spent on a fix loop the criterion made unwinnable. (4 would need either a passing check or a checker that catches the Joplin and Obsidian misreadings.)

## Comparison with A2
| | A2 | A3 |
|---|---|---|
| Plan shown | paraphrased | verbatim block, `plan_id` used |
| Scope elicited | invented default 8 apps | asked, no invention |
| "Told when done" | 5 "status?" turns, 2 died on throttling | 0 polls, assistant waited with `progress(wait_seconds)` (8 waits) |
| User turns / commands / files read | 9 (7 answered) / 0 / 0 | 5 / 0 / 0 |
| Time: plan / org running / first result / end | 1:23 / 1:48 / 11:40 / 27:45 | 0:32 / ~1:00 / 12:40 / 33:24 |
| Fact-check | 10 claims, 0 errors, no n of m | 88-row ledger, 91 claims, n of m, honest FAIL |
| Runs | 14 of 25 | 24 of 25 |
| Result checked? | "all criteria met" (shallow) | admitted unverified, listed claims |
| Scheduler | idle daemon until assistant `stop` | first exit by itself; second never exited (stalled open task); assistant never `stop` |
| Permission denials | none (profiles older) | none with confinement profiles |
| Score | 4 | 3 |
Improved: plan display, scope, waiting, ledger depth, honesty, no throttling noise. Worse: cost (24 runs), delivered check status, 2 decisions pushed to Maya in one waiting turn, and the unwinnable criterion is new (A2's was ">= 8 claims", which was too weak; "n = m over everything" is too strong when the file has opinion).

## Friction log (ranked)
| # | Sev | Friction | Evidence | Component |
|---|---|---|---|---|
| H1 | **High** | Acceptance criterion "n of m verified with n = m, none unsupported" is unreachable when the writer fills "Where we can win" with opinion + citations: 21 of 91 claims "not checkable", 13 unsupported. Each rework fixed some claims and introduced others (the final pass found 3 new claims and 2 new errors from the writer's edits), so the org spent 13 runs after the first `done` and still ended FAIL. Nothing told the writer to separate facts from judgement or the lead to cut claims instead of re-sourcing | final_verification.md; scheduler.log | Blueprint `research` template + writer/fact-checker role templates |
| H2 | **High** | Checker still verifies "a URL exists/page is on topic", not "page states it": Joplin Server licence (claim now false, cited to a repo root), Obsidian "cloud-only", C15 "universally known". Rework of a flagged claim is not re-derived from the source, so a fix can introduce a wrong claim (Joplin) | spot-check 1, 3; ledger C15 | `fact-checker` template (claim types: licence/pricing need the licence/pricing page quote) + `writer` template ("when a claim is unsupported, delete or quote the source, never rewrite from memory") |
| M1 | Medium | Manager's `done` report was false against its own criteria ("fact-checked ... every claim has a URL", "8 of 8 verified" = changes, not claims). The assistant caught it only because it re-read the file and the ledger | inbox result 20261017T195751 | `manager` template (only report `done` with the checker's n of m pasted) |
| M2 | Medium | Scheduler stays up when the only open task is budget-stalled and the user decides to stop; `until_done` waits for work that cannot move. Assistant did not call `stop` or close the task | scheduler.log (second block has no exit line), `progress`: "stalled (lead is paused: budget)", pid 28857 alive 23 min | Product (`until_done` should exit when everything open is blocked on the user/budget) + skill step "if you deliver unverified or abandon, `stop`" |
| M3 | Medium | Budget cap collision: planned 22 / "minimum 17", real 24, and a second cycle would have been 27. The plan did not say what happens if the check fails (here: the user is asked twice, in the middle of a waiting turn) | turns 3-5 | Plan wording; maybe plan a reserve for a second fix cycle or state "if the check fails twice I'll stop" up front |
| M4 | Medium | Manager overhead 58% (14/24 runs); a 4-agent org where the lead consumes more than half the runs | run counts | Blueprint (flat team / lead `run per event` cost) |
| L1 | Low | "Goal:" line of PLAN FOR YOU truncated with a literal "..." mid-sentence | propose_org-result.txt line 4 | Product (render) |
| L2 | Low | Final reply to "short answer please" was ~25 lines with 3 groups of bullets | turn-5.txt | Skill (brief final) |
| L3 | Low | Turn 3 and 4 each end with a decision while Maya "waited"; because `progress(wait)` returns on "something needs you" this is correct, but the first decision request came after 21 runs had already been spent | turn 3 | Skill/plan (ask earlier, at the lead's first budget request) |
| L4 | Low | Env noise `Dynamic registration failed ... lessthan.ai` at the top of every transcript | turn-1.txt | Environment |
What worked: setup mode + create_org, one checklist, no invented scope, verbatim plan + `plan_id`, `progress(wait_seconds)`, `delegate(revises)`, refusal to spend beyond the cap without OK, honest delivery, confinement profiles with web tools, restart of the scheduler after new work, auto-exit of the first scheduler.

## Recommendations (ranked)
1. **Role templates + research blueprint: separate facts from judgement (H1).** Writer: every sentence with a number, name, licence, price or date is a *claim* with a URL whose page states it; analysis/"where we can win" sentences carry no citation and are labelled as our judgement, or reference table cells. Fact-checker ledger: count `judgement` separately, criterion becomes "n of m *factual* claims verified, n = m". Add to the manager: if the first check fails, cut unverifiable claims rather than re-source them.
2. **`fact-checker` template: quote the sentence from the page (H2).** For licence/pricing/sync-model claims require the verbatim quote from the cited URL, plus "also look for an exception" for licences (sub-package licences like Joplin Server's). A verified row without a quote is rejected by the manager.
3. **`manager` template: paste the checker's n of m into every `done` (M1)** and never describe re-checked *changes* as claim coverage.
4. **Product: `until_done` exit when all open tasks are budget-stalled or waiting on the user (M2)** and `progress` hint "stop() or close the task if you will not grant budget"; skill: call `stop` after delivering an unverified or abandoned org.
5. **Plan/skill: state the failure policy and reserve up front (M3)**, e.g. in the PLAN FOR YOU "Budget" line: "if the check still fails after one rework I will ask before spending the reserve", and ask the user at the first budget request rather than after 21 runs. Fix the truncated "Goal:" line (L1).

## Metrics
| Metric | Value |
|---|---|
| User turns / answered | 5 / 5 (A2: 9 / 7) |
| Commands run / files read by user | 0 / 0 |
| Questions before building | 1 message, 7 items |
| Needs elicited / full / partial / not met | 7 / 4 / 2 / 1 |
| Org agent runs | 24 (cap 25): lead 14, writer 5, factcheck 4, researcher 1 |
| Permission denials | 0 (2 HTTP 404 fetch failures) |
| `progress(wait_seconds)` calls | 8; "status?" turns: 0 |
| Fact-check ledger | 88 rows; final pass 91 claims: 52 verified / 5 wrong / 13 unsupported / 21 not checkable |
| My spot-check (5 claims) | 3 confirmed (AnyType x3 sub-claims, Trilium, Joplin Business price), 1 wrong, 1 unsupported, 1 misleading |
| Time to plan / approval / org running / first result / delivery | 0:32 / 0:38 / ~1:00 / 12:40 / 33:24 |
| Scheduler | 1st exited itself; 2nd left running, SIGTERMed by me |
| Score | 3/5 |

## Safety check
Before (20:44:40) vs after (21:23): `~/.kiro/settings/mcp.json` md5 `3eacba4e4479ae692c3dae8761b14b73` unchanged; the five existing `~/.kiro/agents/orgmcp*.json` md5 unchanged; only new files were the two per-org profiles `orgmcp-orgmcp-a3-1792266280-org-1cbc08{,-web-fetch-web-search}.json` (reference `$S/org`; deleted at cleanup); main checkout `git status --short` empty before and after; live org HEAD `5b94a6b` before and after, no mention of this scenario. No `mcp.json`/settings reads in transcripts, session tool calls or run logs. Assistant and org wrote only under `$S` (the assistant's shell calls: `wc`, `ls`, `grep`, `cp`, `cmp`). Caps: 24 of 25 runs, 5 user turns, 33 min of org time (study ~40 min). The scheduler (pid 28857) was still running at the end; I sent SIGTERM; no process referencing `$S` remained.
