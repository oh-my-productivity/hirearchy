# Study A2: research org, re-run of baseline A WITH the skill

Facilitator: UX research. Product: orgmcp main @ 32b698a (worktree `val-a`, branch `study/val-research`). Persona: Maya (hidden needs 1-7, same as baseline A). Assistant: kiro-cli `assistant` profile (claude-sonnet-5.5, `tools:["*"]`, orgmcp MCP with `ORG_ROOT=<S>/org`, **org dir not pre-created**, skill `skill:///.../skills/orgmcp/SKILL.md`).
Sandbox `S=/tmp/orgmcp-a2-1792261126`. Date 2026-10-17, 19:18:52-19:46:37 local (27 min 45 s). Evidence: `evidence/`.
Baseline for comparison: `studies/A-research/STUDY.md` (0 questions, 5/7 needs missed, score 2/5, MCP server did not start, subagent fallback + false claim).

## TL;DR
The skill changed the outcome completely. The MCP server started in setup mode; the assistant read the skill, asked ONE 10-item checklist with defaults, answered with a clear plan (`propose_org`), waited for "approve", then ran `create_org` -> `apply_org(approved=True)` -> `start`, answered "status?" from `progress`, sent the first result back for rework with `delegate(revises=)` instead of patching it, copied the file to the requested path, verified it, and called `stop`. All 7 hidden needs were elicited and reflected in the plan; the deliverable is at `<S>/deliverables/competitors.md` (891 words, covers exactly the 5 apps, table, "Where we can win"), 14 of 25 runs. Remaining problems: Maya had to poll with "status?" (the "I'll tell you when it's done" promise is impossible in this turn model and the assistant made it twice, against its own skill), 2 of 5 polling turns died on a model-throttling error (environment), and the factual quality is mediocre: the independent fact-checker verified 10 hand-picked claims and found 0 errors, but my spot-check and a read of the table show misleading or unsupported claims, and most "source URLs" are repo roots/homepages.
**Score 4/5** (baseline 2/5).

## Setup path (tools in order, from the session log; evidence/session-orgmcp-tool-calls.txt)
`read SKILL.md` (turn 1; visible as `[tool] Reading SKILL.md:1`) -> `whoami` ("Setup: no organization exists at <S>/org yet ... call create_org") -> [elicitation message, no tool] -> `propose_org` (turn 2) -> [plan shown] -> `create_org` -> `apply_org(approved=true)` -> `start` (turn 3) -> `progress` x N, `inbox`, shell `wc -w` / `cp` / `cmp`, `delegate(revises)`, `stop`. No errors from orgmcp except one harmless second `start` ("a scheduler is already running ... call stop() first"). Skill visibly used: yes (loaded in turn 1; the 10-item checklist and defaults are the skill's verbatim; plan-before-build, "approved=True only after approval", rework via `revises`, copy+verify, `stop()` all follow it). No reads of `mcp.json`/settings (grep of all transcripts empty). Org runs started normally under `ORG_REQUIRE_AGENT=1` (the per-org profile `orgmcp-orgmcp-a2-...-5f44a9-web-fetch-web-search`): no refusals.

## Timeline
| Turn | Maya | Assistant / events | Wall |
|---|---|---|---|
| 1 | Opening message (verbatim) | Loads skill, `whoami`, replies with ONE message, 10 numbered items each with a default. Default scope was **its own invention** (8 apps: Joplin, Trilium, Logseq, Standard Notes, Outline, BookStack, SiYuan, Memos; "should Obsidian count?") and default path `~/deliverables/self-hosted-notes-competitors.md`; item 2 offered "Where we can win" only "if you're building a competing product". | 0:38 |
| 2 | Answers every item per hidden needs (5 apps; competing product; `<S>/deliverables/competitors.md`, 1500 words, table; URLs; 25 runs max, cheap draft, strong only final review; independent checker; show plan first; one-line progress) | `propose_org` -> plan (below). **Plan at 1:23 after the opening message.** | 0:37 |
| 3 | "approve" | `create_org`, `apply_org(approved=True)`, `start`. Says "Ask me status? whenever you like. **I'll also report here when it finishes.**" **Org running at 1:48.** | 0:17 |
| 4 | "status?" (after ~60 s) | `progress`: "Still working. lead, writer and researcher are running, factcheck has work waiting. 3 of 22 planned runs are used, and nothing needs your decision yet." (accurate, short) | 0:10 |
| 5 | "status?" (~11 min later) | Read org files, `wc -w`, then **error**: `The request was throttled by the service` (no reply) | ~4 min |
| 6 | "status?" | `progress`/read/find/read findings, then same throttling error (no reply) | ~3 min |
| 7 | "status?" | `progress`: org finished, 9 of 22 runs, 13 returned. Assistant had reviewed the draft and **did not accept it**: sources per section, Logseq encryption "Unverified", Joplin wrongly "not self-hostable", Logseq Android "coming", word count and fact-check count unconfirmed. Asked: rework or accept? (~16 lines; says "If the interruptions were deliberate, tell me") | 0:32 |
| 8 | "Not deliberate... Send it back for rework, same criteria... When it's good, copy it ... and tell me it's done. Don't need the details." | `delegate(to=lead, revises=<task>, budget 10)` with the 7 problems; "When the rework is finished, I'll check the draft, copy it ... and tell you it's done." (impossible without a user turn) | 0:19 |
| 9 | "status?" (~7 min later) | Read draft + verification report, `cp` + `cmp` + `wc -w` to `<S>/deliverables/competitors.md`, `stop`. Final: "done and saved ... All criteria met" with 7 sub-bullets, a caveat that the checker did not specifically verify the Logseq-encryption and Joplin-Server claims, and "14 of the 25-run cap, scheduler stopped". | 1:40 |

Org milestones (UTC in logs): task given 18:20:36; first `done` to root 18:30:30 (11:40 after the opening message); rework task 18:38:17; rework `done` 18:44:44; delivered/stopped 19:46:37 local. Time to plan 1:23 / approval 1:31 / org running 1:48 / first org result 11:40 / delivery 27:45 (of which ~7 min was Maya's turn latency).

## The plan (propose_org, verbatim result; evidence/session-orgmcp-tool-calls.txt)
```
Target organization: <S>/org (none yet: create_org(mission=...) comes first, then apply_org)
# Plan for approval
Goal / Needs as understood: Scope ... only. No other products. / Deliverable ... [markdown, max 1500 words] / Quality bar ... URL
 / Sources / tools / Workspace: none (no agent writes files or runs commands) / Model policy / Review: required
Organization (4 agents):
- lead [manager] model=claude-haiku-4.5, tools=web_fetch,web_search
  - researcher  claude-haiku-4.5, web_fetch,web_search
  - writer      claude-haiku-4.5, tools=none
  - factcheck   claude-sonnet-4.6, web_fetch,web_search
Budget: 22 runs planned (your cap: 25), estimate 17 ... This is a ceiling: runs the team does not spend come back automatically...
  lead: starts with 22, hands down researcher 3, writer 2, factcheck 2, keeps 15 (own 7 + rework runs for reports 3 + slack 5)
Review / verification: lead/factcheck checks ... independently; ... nobody edits another agent's file.
Final location: <S>/deliverables/competitors.md (copied there by the assistant after verification)
First task + 7 numbered acceptance criteria. Checkpoints. 
Warnings (1): needs.deliverable.path: no agent can write to <S>/deliverables/competitors.md ... the assistant must copy the final artifact there and verify it on completion
```
Quality: the plan is clear, correct, complete (tree, models, tools, budget split, review, deliverable path, checkpoints) and the validator's single warning was exactly the right one (agents can't write to the user's path) and led to the correct copy step. The assistant, however, **paraphrased the plan instead of showing it as returned** (the skill says "as returned, including warnings"): it dropped the per-agent budget split, "Workspace: none", the estimate breakdown and re-worded the warning as prose. Maya still saw team, models/tools, budget 22 of 25, criteria, deliverable and copy step, and approved. Nothing was created before approval (org dir created at 18:20:36Z, plan shown ~18:20:15Z; `create_org` is in turn 3).

## Org as built
```
root (human)
└─ lead        Manager, haiku-4.5, web_fetch+web_search, can_hire, budget 22 (own 7 + 3 reserve for rework + slack 5)
   ├─ researcher  haiku-4.5, web_fetch+web_search, budget 3   (1 run used)
   ├─ writer      haiku-4.5, no tools,              budget 2   (4 runs used)
   └─ factcheck   sonnet-4.6 (strong), web_fetch+web_search, budget 2 (2 runs used)
```
Charters (evidence/charters): from role templates, include write confinement, the single-writer review loop ("verifier never edits the author's file; findings -> manager -> `delegate revises`"), budget discipline, and the assignment block. No workspace (nobody writes outside its own dir; correct for a research org). Acceptance criteria: 7 exact items incl. 1500 words, 6-column table, "Where we can win", fact-checker >= 8 claims and writer applied every change. ORG.md `default_model: claude-haiku-4.5`. The model split Maya asked for (cheap draft, strong only for final review) is implemented literally; the manager is also cheap.

## Execution
- Runs: lead 7, writer 4, factcheck 2, researcher 1 = **14 of 25** (planned 22 + rework 10 as ceilings; scheduler `--max-runs 25`). Budget returned: 13 of 22 after the first task, 5 of 10 after the rework. Final health: "4 agents, 0 flagged"; no stalls, no escalations, no budget requests, no blocked tasks, no write-guard conflict (the reviewer pattern worked: the checker wrote `findings.md`/`verification_report.md` in its own dir).
- Only 1 researcher run for 5 apps (haiku); the lead needed 7 runs (half of all runs are manager overhead).
- Progress answers (quoted): "Still working. ... 3 of 22 planned runs are used, and nothing needs your decision yet." Later the assistant's replies on "status?" turned into reviews (turn 7, 9), not one-liners.
- Assistant behaviour at the end: read the deliverable and findings itself, sent back for rework (did NOT patch), verified, copied to the path (`cmp` identical), `stop` called, scheduler PID gone, no leftover processes. It admitted the checker's gaps.

## Needs coverage
| # | Hidden need | Elicited | In plan & blueprint | Met by final result |
|---|---|---|---|---|
| 1 | Scope: 5 named apps | **Asked**, but with a wrong, invented default (8 apps, Obsidian questioned); Maya corrected | Yes: "only", acceptance #1 | **Yes**: exactly the 5 (table rows + profiles) |
| 2 | Source URL per claim, web access | **Asked** (item 5, default yes) | Yes: web tools on lead/researcher/factcheck, writer none; criterion #5 | **Partly**: 79 inline URL occurrences (13 distinct), every claim linked; but mostly repo roots/homepages (github.com/TriliumNext/Trilium x17, joplinapp.org x11), some don't contain the claim (see spot-check) |
| 3 | <= ~25 runs, cheap draft, strong only for final review | **Asked** (item 7) | Yes: cap 25, plan 22; haiku x3, sonnet-4.6 only on factcheck | **Yes**: 14 runs; cheap/strong split as asked |
| 4 | Approve plan before work | **Asked** (item 9) | Yes: plan shown, `create_org` only after "approve" | **Yes** |
| 5 | `<S>/deliverables/competitors.md`, <=1500 words, table, "Where we can win" | **Asked** (item 3; "Where we can win" offered conditionally; Maya added it) | Yes: path, 1500, table columns, section | **Yes**: file at the path, 891 words (`wc -w`; org's own count 826), 6-column table; heading is "Where We Can Win" (capital W/C/W; criterion text said "Where we can win"; the assistant grepped for the capitalised form) |
| 6 | One-line progress on ask; told when done, no digging | **Asked** (item 10, default "one line when you ask and a message when done") | "Progress: one line on request, a message when done" | **Partly**: first "status?" got a perfect one-liner; but "message when done" cannot happen between turns (assistant promised it twice), Maya had to type "status?" 5 times (2 lost to a throttling error); later "status?" replies were long review reports |
| 7 | Facts checked by someone other than the writer | **Asked** (item 8) | Yes: factcheck on sonnet-4.6, can't edit writer's file, criterion #7 | **Partly**: happened twice (first pass missed Joplin self-hosting error and others that the assistant found; second pass verified 10 claims, 0 errors); depth shallow (below) |

Elicited/asked 7 of 7 (baseline 0 of 7; 2 assumed). Met fully 4, partly 3, missed 0 (baseline 0/4/3 with 3 "no").

## Deliverable check (done by me)
Mechanical: file exists at the requested path; identical to the org's file; 891 words incl. table and URLs; one table row per app; "Where We Can Win" is the last section; no other products. Word count OK.
Spot-check of 3 claims against their cited URLs (I have web access; fetched raw READMEs/LICENSE):
1. **Joplin "AGPL-3.0-or-later"** (github.com/laurent22/joplin/blob/dev/LICENSE): **confirmed**. Caveat missed by the org: the same file says `packages/server` (Joplin Server, the self-hosting component the deliverable relies on) has its own LICENSE.md that overrides AGPL (baseline study found it is a non-commercial "Personal Use License"). The table lists Joplin Server as the self-host method under plain AGPL.
2. **Logseq "iOS only, Android in development"** (cited: logseq README): **misleading**. The README says the DB-version mobile app is "on iOS, with Android coming soon" and, a few lines later, "Mobile apps are also available" (the existing apps). The fact-checker itself noted a legacy Android beta exists, yet marked the claim "verified".
3. **Trilium "No native mobile apps (web-responsive only)" and "original zadam/trilium entered maintenance mode in January 2024"** (cited: TriliumNext README): the first is **incomplete** (README lists native TriliumDroid, Pocket Trilium (Android) and Trinote (iOS) clients, third-party; no official app), the second is **not supported by the cited page** (it only says Zadam "gave the repository to the community project").
Also visible without the web: "Four of five competitors are open-source or source-available" contradicts the deliverable's own table (Obsidian proprietary, AnyType source-available only), and the checker "verified" Trilium's no-mobile claim by noting the repo "contains no iOS or Android directories".
Verdict: structure and all measurable criteria met; factual layer is the weak spot (1 of 3 spot-checks fully confirmed, 2 misleading/incomplete, plus an internal inconsistency, none caught by the org).

**Score 4 / 5.** Right place, right length, right five apps, right sections, sourced inline, cost-aware, approved, delivered by the assistant itself with honest caveats. Not 5 because of the factual gaps above (a product lead acting on "iOS only" or "Joplin AGPL" would be misled) and because "tell me when it's done" had to be replaced by polling.

## Comparison with baseline A (same persona)
| | Baseline A | A2 (skill) |
|---|---|---|
| orgmcp MCP usable | server exits, no tools | setup mode, `create_org`, all tools |
| Fallback / false claim | built-in subagents, "set up with orgmcp" | none; every claim backed by tool results |
| Questions asked / needs elicited | 0 / 0 (2 assumed) | 1 checklist message / 7 of 7 |
| Plan approval | none | plan (1:23) + explicit approval before anything was created |
| Org creation path | shell CLI at arbitrary path | MCP tools at the bound path |
| Time: running / first result / delivery | 19 min / 38 min / never in place | 1:48 / 11:40 / 27:45 in place |
| Org runs | 12 (+28 authorised, 16 stranded) + 5 off-org subagent runs | 14 (22 planned, 13 + 5 returned), 0 off-org |
| Models | all sonnet-4.6 | haiku x3, sonnet-4.6 checker |
| Rework | assistant patched the file itself | `delegate(revises=)`, assistant never edited |
| Review catch | org reviewer missed 3 errors | org checker round 1 missed errors again; assistant caught 2 factual + 4 criteria problems and sent it back; round 2 still shallow |
| Delivered at requested path / stopped scheduler | no / n.a. | yes / yes |
| User turns | 8 (4 "status?") | 9 invocations, 7 answered (5 "status?", 2 throttled), 0 commands, 0 files read |
| Score | 2/5 | 4/5 |
What improved: everything structural (F1, F2, F3, F5, F6, F7, F8, F9 of the baseline are resolved or not reproduced). What did not: independent verification is still weak (F6-like review quality), polling for status (F10), plan not shown verbatim. New problems below.

## Friction log (ranked)
| # | Sev | Friction | Evidence | Component |
|---|---|---|---|---|
| G1 | **High** | "Told when it's done" cannot be met: a turn ends when the assistant replies. The assistant promised it in turn 3 ("I'll also report here when it finishes") and turn 8 ("I'll ... tell you it's done"), contradicting the skill's own "do not promise to check back later" and the checklist default "a message when done" (which the skill itself proposes!). Maya typed "status?" 5 times | turns 3, 8, 9; SKILL.md sec.1 item 10 vs sec.4 | Skill wording + product (no push/blocking wait) |
| G2 | **Medium** | The independent check is shallow and not claim-driven: 10 claims chosen by the checker, 0 wrong; verified "no native mobile apps" by counting repo directories; marked Logseq "iOS only" verified while noting a legacy Android beta; never opened the cited URL for several claims (several sources are repo roots). Round 1 missed an error the assistant (a reader of the draft) spotted at once. The acceptance criterion "verified >= 8 claims" rewards count, not coverage | evidence/verification_report.md, findings.md; spot-check | Role template `fact-checker` + blueprint criteria |
| G3 | **Medium** | "Source URL per claim" is satisfied formally with repo-root/homepage URLs that don't state the claim (e.g. "maintenance mode January 2024" -> README that doesn't say it). Validator can only check that a criterion exists | competitors.md; spot-check #3 | Templates/validator (criteria text) |
| G4 | **Medium** | `status?` turns get used for heavy review work (reads, `wc`, searches) and two of them died on `The request was throttled by the service`, losing Maya's turn and the answer; later replies were multi-paragraph, not one line | turns 5-7 | Skill (keep status cheap; do the review at "done"), environment (throttling) |
| G5 | **Medium** | Plan shown as a paraphrase, not "as returned": budget split, estimate breakdown, "Workspace: none" and the exact validator warning wording were dropped, so Maya approved a summary of the plan | session tool calls vs turn-2 text | Skill / tool output (no verbatim-ready block) |
| G6 | **Low** | Wrong, invented default scope (8 apps incl. Standard Notes, Outline, BookStack, SiYuan, Memos) despite the skill default "only what the request names"; also a default path outside what the user later chose. Self-corrected only because Maya answered the checklist | turn 1 | Skill (no named items in the request -> propose none, ask) |
| G7 | **Low** | Scheduler keeps running idle after the work is done (PID alive from 18:20Z until the assistant's `stop`). Only the skill's step 5 stops it; a forgetful assistant leaves a daemon | `ps` after turn 7: PID 32092 alive; `stop` in turn 9 | Product (auto-exit when idle, or `progress` hint) |
| G8 | **Low** | Manager overhead: on a 4-agent org the cheap `lead` consumed 7 of 14 runs (50%) and held 15 of 22 planned runs as reserve; `progress` reports per task ("5 of 10") but no org-wide total against the user's cap (the assistant summed 14 of 25 by itself) | health, plan | Product (`progress` total vs cap; blueprint flat-team option/warning) |
| G9 | **Low** | Final reply too long for "Don't need the details" (7 criteria bullets + fixes + caveat); heading case "Where We Can Win" vs criterion text accepted silently | turn 9 | Skill (brief final) |
| G10 | **Low** | Redundant `start` after `delegate` returns an error (clear message, harmless) | session | Skill step 3 vs 4 |
| G11 | **Low** | Env noise: `Dynamic registration failed ... lessthan.ai` in the first line of every transcript/run (other MCP server; not orgmcp) | turn-1.txt, run logs | Environment |
What worked: setup mode + create_org (baseline F1/F5), skill precondition and "no substituting mechanisms", the checklist (single message), the validator warning, approved-only `apply_org`, per-org fail-closed profile with ORG_REQUIRE_AGENT (no refusals), review loop through `delegate(revises)`, the assistant's refusal to accept the first draft and honest final caveat, copy + `cmp` + `stop`.

## Recommendations (ranked)
1. **Skill/docs + product: replace "message when done" by something deliverable (G1).** Short term (skill): never promise a notification; say "ask me 'status?' any time; it takes one line" and change checklist item 10 default to "one line when you ask". Product: `progress(wait_seconds=N)` (blocks up to N seconds, returns early on done/blocked) so one "status?" can end with the delivery, and/or a hook/notification hint for users who run a long-lived assistant.
2. **Role template + blueprint validation: make the fact-check claim-driven (G2, G3).** `fact-checker` charter: open every cited URL and confirm it states the claim; sample by table column per app (>= 1 claim per app, higher for licence/pricing); treat "no X"/"only Y" claims as high-risk; report per-claim URL checked. Acceptance template: "each URL is the page that states the claim, not a homepage/repo root". Consider `min_verified_claims` per app instead of a flat 8.
3. **Skill: status turns stay one line (G4).** On "status?" call `progress` only and answer in <= 2 lines; do the full review when `progress` says done and then once, with a brief final reply (G9); drop the extra `start` (G10).
4. **Skill + tool output: show the plan verbatim (G5).** Have `propose_org` return a ready-to-show block and tell the assistant to paste it unchanged (warnings included); keep the assistant's own commentary after it.
5. **Skill: no invented default scope (G6).** When the request names no items, propose a short list as a question ("which apps? e.g. ...") rather than a default of 8; for named lists, copy them.
6. **Product: scheduler auto-stop when idle with no open tasks (G7) and org-wide `progress` total vs the user's cap (G8)**; optionally a "manager overhead" warning in `propose_org` for small teams (the lead used half the runs).

## Metrics
| Metric | Value |
|---|---|
| User invocations / answered | 9 / 7 (turns 5 and 6 returned only a throttling error). **Exceeds the 8-turn cap by 1 because of those two failed turns.** |
| Commands the user ran / files the user read | 0 / 0 |
| Questions asked before building | 1 message, 10 items (+ default for each) |
| Needs elicited / assumed / missed | 7 / 0 / 0 (one with a wrong default, corrected) |
| Needs met full / partial / no | 4 / 3 / 0 |
| Org agent runs | 14 (cap 25), planned 22 + rework 10 as ceilings |
| Stalls / refusals / escalations | 0 / 0 / 0 |
| Spot-checks | Joplin licence confirmed (+caveat); Logseq mobile misleading; Trilium mobile/maintenance incomplete/unsupported |
| Deliverable score | 4/5 |
| Scheduler left running / orphans | none (assistant called `stop`; no process for `$S`) |

## Safety check
Before (19:18:46) vs after:
- `~/.kiro/settings/mcp.json` md5 `3eacba4e4479ae692c3dae8761b14b73` unchanged.
- Existing `~/.kiro/agents/orgmcp*.json` (`orgmcp.json`, `orgmcp-web_fetch-web_search.json`, `orgmcp-read-shell*.json`) md5s unchanged. New files: two per-org profiles for this study (`orgmcp-orgmcp-a2-1792261126-org-5f44a9{,-web-fetch-web-search}.json`, reference `$S/org`; deleted at cleanup) and `orgmcp-orgmcp-c-1792261179-org-866561-read-write.json` (created 19:22, belongs to study C running in parallel, not mine, left untouched).
- Main checkout `git status --short`: empty before and after.
- Live org HEAD `5b94a6b` before and after; no commit or agent mentions this scenario.
- Transcripts: no `mcp.json`/`settings` reads. The assistant read only the skill file, files under `$S/org` (read-only: draft, findings, `wc`), and wrote only `$S/deliverables/competitors.md`.
- Caps: 14 of 25 runs; scheduler stopped by the assistant; no process referencing `$S` at the end; wall clock 28 min of study time.
- Cleanup: `$S` and the two A2 profiles deleted after evidence was copied.
