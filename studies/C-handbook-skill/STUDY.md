# Study C: unseen scenario, WITH the skill ("onboarding guide from a company handbook")

Facilitator: UX research. Product: orgmcp main @ 32b698a. Persona: Priya, people-ops manager at "Larkspur Labs" (hidden needs 1-7). Assistant: kiro-cli `assistant` profile (claude-sonnet-5.5, `tools:["*"]`, orgmcp MCP with `ORG_ROOT=<S>/org`, org dir NOT pre-created, **skill loaded** via `skill://.../skills/orgmcp/SKILL.md`).
Date 2026-10-17, 19:19-20:00 local (41 min). Evidence: `evidence/` (7 transcripts, charters, task/result messages, final guide, handbook, safety snapshots).
Unseen scenario: nothing in the workflow/skill examples is about writing from internal documents, a read-only source folder, or a no-web constraint (skill's example is a web research org).

## TL;DR
The skill changed the behaviour completely compared with A and B. The assistant called `whoami`, read the handbook itself, asked **one** checklist message with defaults (turn 1), took all of Priya's answers, ran `propose_org` (5 times, i.e. it iterated on validation), showed a plain-words plan and **waited for "approve"** before `create_org` -> `apply_org(approved=True)` -> `start`. The org (lead + writer + independent fact-checker, no web or shell tools) ran 14 of 15 planned runs. When the lead reported `done`, the assistant read the file, **found problems the fact-checker missed**, and sent the work back with `delegate(revises=...)` instead of patching it. It then verified the final file, checksummed the handbook, stopped the scheduler and delivered to `<S>/out/onboarding-guide.md` with a criterion-by-criterion note. All 7 hidden needs were met; remaining problems are (a) a handful of small factual/citation slips that the org's fact-check did not catch, and (b) a messy write path: agents using kiro's built-in `write` put files in `<S>/out/lead/...` (the user's deliverable folder) while orgmcp's `report` could not find them, and the lead's reports quoted three different word counts for a file it didn't have. Score **4 / 5**.

## Setup path (tools in order)
| Turn | User (Priya) | Assistant (tools) | Wall |
|---|---|---|---|
| 1 | Opening message (verbatim) | Read SKILL.md, listed `$S`, `@orgmcp/whoami` (setup mode), read all 6 handbook files. One message: 10-item checklist with a proposed default each, invites "defaults"; also spotted two handbook ambiguities (Expensify vs "expense tool"; several contacts) and asked about tone. No org created. | 1:02 (19:20:57) |
| 2 | Answered per item: out path + 800-1200 words, day-1/week-1/month-1 + Who-to-ask only, plain language + `[file.md]` refs, handbook only/no web, handbook never changed, <= ~20 runs, independent check, plan before start, note when done | `propose_org` x5, then plan in plain words (what / who / budget / privacy / "when it's done"). Ends "Reply 'approve' to start". | 1:20 (19:22:26) |
| 3 | "Yes, that sounds good, approve. Please go ahead." | `create_org`, `apply_org`, `start`. "The team is running ... ceiling of 15 runs." | 0:48 (19:23:28) |
| 4 | "status?" (19:25) | `progress` -> "Still working. The writer is drafting now, and 2 of 15 runs are used. Nothing needs your decision yet." | 0:31 |
| 5 | "status?" (19:45) | `progress` -> "Still working. The lead is running now, and 9 of 15 runs are used." | 0:10 |
| 6 | "status?" (19:47, lead already `done`) | `progress`, `inbox`, shell `wc`/`md5`, read the guide; **found defects, called `delegate(revises)`** to lead (5 runs); told Priya what was fine and what was sent back, listed 5 defects | 1:46 |
| 7 | "status?" (19:58, rework `done`) | `progress`, `inbox`, checks again, `stop`, final note (below) | 1:16 |

Skill visibly followed: yes. The transcript shows `Reading SKILL.md` as the first action, then every skill phase in order (precondition `whoami`, elicit-in-one-message with defaults, propose, wait for explicit approval, build, `progress` answers, verify against every criterion, `revises` instead of patching, `stop`). No hint of the A/B failure modes (no subagent fallback, no false "I used orgmcp", no config read: `grep mcp.json|settings` over transcripts and run logs found nothing).

Time: first question 1 min; plan shown 2.5 min; approved at 3 min (13 s after the plan); org running 3.5 min; first `done` from the lead 28 min; final (after rework) 41 min.

## Quoted plan (turn 2, abridged; the whole text is in evidence/turn-2.txt)
> Here's the plan in plain words. Nothing has been created or started yet. **What gets made:** One friendly guide ... at `/tmp/orgmcp-c-.../out/onboarding-guide.md`, 800-1200 words. It has a Day 1 checklist, a Week 1 checklist, a Month 1 checklist and a "Who to ask" table, and nothing else... **Who does what (3 agents)** lead (strong model) ... writer (cheaper model) ... factcheck (strong model, separate from the writer) checks every fact, number, deadline and contact ... and doesn't edit the guide itself. **Budget:** About 15 runs in total, with a hard ceiling of 20. Unused runs come back to you. I'll ask before going past 15. **Privacy:** The agents have only read and write tools. They have no web access and no shell ... The tools can't technically stop an agent from writing to the handbook, so the instruction not to change it is the only block. After the run I'll compare the handbook files against the checksums ... **When it's done:** I'll read the guide and check it against each of your criteria ... Reply "approve" to start, or tell me what to change.

Quality: clear and honest for a non-technical reader, covers all her stated needs, no jargon, discloses the one thing it cannot enforce (handbook write protection). Weaknesses: the skill says "show the plan as returned"; the assistant summarised it (right for Priya's "plain words" request, but then she never saw the models, per-agent budget split, acceptance criteria text or validation warnings; the tool-validated tree/budget table never reached her). It also did not say that the handbook sits outside the agents' workspace (see F2). The 5 `propose_org` calls show validation errors/warnings forced iterations; the arguments are not visible in `--no-interactive` output, so I can't quote what they were.

## Org as built
```
root (human)
└─ lead         manager, claude-sonnet-4.6, tools read+write, workspace <S>/out, can_hire   budget 15 (keeps 11)
   ├─ writer    claude-haiku-4.5,  tools read+write, workspace <S>/out   grant 2
   └─ factcheck claude-sonnet-4.6, tools read+write, workspace <S>/out   grant 2
```
- No web_fetch/web_search/shell anywhere (charters and the generated `orgmcp-...-read-write` profile: tools `@orgmcp, read, write`). Run logs contain only `@orgmcp/*` calls plus kiro read/write; no URLs, no network tools, no `~/.kiro` or `mcp.json` access, no paths outside `$S`. Need 1: met.
- Task to lead: 6 numbered acceptance criteria (path+800-1200 words; structure; bracketed refs; tone; independent check + writer applied changes; handbook unchanged). Good and checkable. Review step: author -> independent verifier -> rework via `revises`; charters follow the single-writer rule.
- Cheap draft / strong review split applied, unprompted by Priya (skill default).

## Needs coverage
| # | Hidden need | Elicited | In plan / blueprint | Met by result |
|---|---|---|---|---|
| 1 | Handbook only, no web, nothing sent anywhere | **Asked** (item 4; Priya confirmed) | Yes: no web/shell tools, scope + mission text | **Yes.** Verified from charters, profile and run logs |
| 2 | One file `<S>/out/onboarding-guide.md`, 800-1200 words, day-1/week-1/month-1 + Who to ask | **Asked** (item 2; assistant's default path was `deliverables/`, corrected) | Yes: criteria 1-2 | **Yes.** 909 words (`wc -w`), exactly those four sections (plus a title and a welcome line). File sits at the requested path |
| 3 | Plain friendly language; every policy statement traceable by bracket | Assumed tone, **asked** for bracket style via checklist (item 3) | Yes: criteria 3-4 | **Mostly.** 41 bracketed refs, every bullet and table row has one; jargon mostly gone (2FA spelled out, PTO explained). 3 citation slips (below) |
| 4 | Someone other than the writer checks every fact | **Asked** (item 8) | Yes: independent `factcheck`, criterion 5 | **Partly.** It ran twice (28 claims, then 7 fixes + 23 spot checks) but missed defects the assistant found, and "every fact" was sampling |
| 5 | Handbook not modified | **Asked** (item 5) | Yes, as text rule only; plan says so honestly | **Yes.** md5 of all 6 files identical before/after; mtimes 19:19 |
| 6 | <= ~20 runs | **Asked** (item 7; default 12, Priya said ~20) | 15 planned, ceiling 20, ask before >15 | **Yes.** 14 runs (lead 8, writer 4, factcheck 2); lead's request for +3 was declined (not needed) |
| 7 | See plan in plain words first; short note when done | **Asked** (items 9-10) | Yes; approval gate honoured | **Yes.** Plan -> "approve" -> build; final note given when Priya asked "status?" (see F9) |

## Result verification (my own, against the handbook files)
Word count 909; structure OK; refs on every list item/table row (all 6 cited names exist); handbook unchanged. Fact cross-check of every statement in the guide:

Correct and consistent with the handbook: 14:00 UTC start, 30-min welcome call with Tomas Lindqvist; 2FA list/apps/no SMS/48 h; channels; intro in #general; read handbook in Notion; communication norms and values; daily 30-min 1:1s; buddy on day 2; Friday all-hands 15:00 UTC; plan choice in 30 days; 90%/70% premiums; core hours 13:00-17:00 UTC; 25 PTO days, accrual, Bamboo request rule, sick days (10, doctor's note after 3), 24 Dec-1 Jan shutdown; parental leave 16/6 weeks, 8 weeks notice; laptop return 14 days; 30-day check-in and 90-day goals; retirement 60 days, 4% match, immediate; learning $1,200 / $300 approval; Mindwell and 6 counselling sessions; every Who-to-ask name, role and email; 1 h security reporting, phishing button/#security; emoji.

Mismatches / issues:
1. "Complete the security awareness course by the end of week 2 (45 minutes) [first-week.md]": the 45 minutes is only in security-policy.md (cite is wrong/incomplete).
2. "Submit home-office stipend receipts within 60 days. You received a one-time $600 stipend ... [tools-and-accounts.md]": wrong meaning ("received", handbook: spend, keep receipts, submit for it) and wrong cite ($600 and 60 days are from benefits.md; only "Expensify" is from tools-and-accounts.md).
3. "monthly internet stipend of $25 ... towards your home office costs": handbook says towards **internet costs**.
4. Who-to-ask row "Benefits, wellbeing, counselling -> Marguerite Osei": handbook names her only as benefits lead; the counselling line is "on the people-ops page", so assigning her counselling is an inference.
5. Omissions (not errors): the laptop shipping process (address to Tomas >= 10 days before start; chase via #it-help if not arrived 3 working days before), "sign your contract in Bamboo", "cover starts on day 1" and Dev Anand's one-working-day reply promise. The guide has no "before you start" step even though the laptop process was the example fact in the brief.
6. Month 1 contains items that are not month-1 tasks (laptop return if you leave, parental leave, retirement after 60 days, security course due in week 2). The assistant noticed this itself and offered to cut them.
7. Housekeeping: a table header cell with a trailing space; row 4 of the table packs a policy sentence into the "Question" cell.
So: no wrong numbers, names, dates or contacts; 3 content/citation slips (1-3), 1 inference (4).

Verification by the org vs by the assistant: the org's fact-checker round 1 (initially mis-estimated the word count at 640-670, then 28 claims confirmed, 2 invented) and round 2 (7/7 fixes + 23 spot checks) missed slips 1-3 and the assistant's other defects (invented "check it arrived safely and install updates" laptop advice, "data breach", missing refs in the table, jargon). The assistant caught all of these in its own pass and sent them back; **its extra check is what lifted the result**, exactly as the skill intends. It did say honestly "I did not read [factcheck-round2.md] ... so I haven't confirmed that the fact-checker covered every fact."

## Execution
- Runs 14: lead 8, writer 4, factcheck 2 (15 planned, 20 cap). Run times: writer first draft 514 s (haiku), factcheck 293 s and 133 s, lead 40-247 s.
- Progress answers (quoted above) were one-liners from `progress`: accurate, and "Nothing needs your decision". When it said "The lead is running now" at 19:45 the lead had finished at 19:47: fine.
- Budget: returned with final result; lead's mid-rework message asked for 3 more runs (it had miscounted its reserve). Assistant read it, judged not needed, declined (unspent budget in the end: 1 of 15). No stalls: the scheduler never waited on a human.
- Escalations: the lead's budget request only. No refusals or blocked reports at root level; the writer's first run took 514 s, and it made 5 failed `report` attempts first (F1).

## Friction log (ranked)
| # | Sev | Friction | Evidence | Component |
|---|---|---|---|---|
| F1 | **High** | Built-in `write` in agent runs resolves relative to the grant `workspace` (= the user's deliverable folder `<S>/out`), while orgmcp's `report(artifacts=...)` and `read` resolve relative to the org root. Agents (haiku writer, sonnet lead/factcheck) wrote into `<S>/out/lead/writer/work/...`, `<S>/out/lead/work/...` (the lead's dir, from the writer!), and `<S>/out/onboarding-guide.md`; `report` failed repeatedly ("artifact not found"), the writer retried 5 times and finally reported with no artifact. The org dir holds a **stale** 896-word draft (`org/lead/work/`, and `org/lead/writer/work/` is empty) while the true final is outside the org. The lead's results quote 957, 843 and 858 words for a file that was 896/909 | evidence/run-excerpts/writer-first-run-report-path-fight.txt, `evidence/out-tree.txt`, org result messages ("843 words, modified 18:47:09 UTC, NOT modified since...") | Product: `workspace` vs org-relative path semantics, built-in `write` granted alongside orgmcp `write` |
| F2 | **High** | Source/workspace mismatch for read-only inputs: the handbook is *outside* the agents' declared workspace (`<S>/out`), yet agents read it with the built-in `read` (worked; nothing blocked it), and the charter says "everything you read ... stays inside [the workspace]". Same unrestricted `read`+`write` means "handbook is never changed" relies on prose only. The plan disclosed the latter but not the former; neither is a way to give agents *read-only* access to a named folder | charters (workspace line vs scope line), plan text | Product (read-only input roots) / blueprint validator |
| F3 | **Medium** | Org-side fact-check is shallow: sampled ~30 claims, mis-estimated word count at first, never checked that a bracket points to the file the fact actually comes from, missed 3 slips and the assistant's 5 defects. "Check every fact" in the criteria is not enforceable; the manager marks it `done` | factcheck findings; assistant turn 6 | Role template (fact-checker should enumerate claims systematically and check citation->source) |
| F4 | **Medium** | The user's deliverable folder is polluted: `out/` now holds `lead/` with agent memory, notes, 3 copies of the guide, next to the deliverable. The assistant reported it and offered cleanup, but it exists because of F1 | `evidence/out-tree.txt` | Product (same as F1); skill could tell the assistant to deliver into a clean path |
| F5 | **Medium** | Lead's reports are unreliable on facts it could check (3 different word counts; the file named in `Artifacts` was a stale copy) and it reports `done` anyway; the assistant's independent check caught it. Same root as F1 | org result messages | Product / manager template |
| F6 | **Low** | Plan shown to the user was a re-summary, so tree, models, per-agent budget split, acceptance criteria and any warnings from `propose_org` were not visible to Priya. Acceptable here (she asked for plain words) but loses the audit trail the skill intended | turn-2 vs skill section 2 | Skill ("show as returned" vs plain-words persona): offer both, e.g. plain plan + "say 'details' for the full plan" |
| F7 | **Low** | Assistant's elicited default path was `<cwd>/deliverables/...` and word limit 1800 (skill default 1500 plus, no knowledge of the user's); harmless as Priya corrected it, but the checklist offered "Default: ... ~/deliverables" for content a non-technical user may not know where to find | turn-1 | Skill |
| F8 | **Low** | Month-1 padding: writer/lead stuffed unrelated policies into the checklist to reach 800 words; an acceptance criterion about structure and length alone does not cover relevance | final guide | Role template / criteria wording |
| F9 | **Low** | The "short note when done" only comes when the user types something (headless turn model): Priya had to ask "status?" 4 times to get it. The skill correctly says not to promise to check back, but a user who wants a note when done will still have to poll | transcripts 4-7 | Docs (known limitation) |
| F10 | **Low** | I (the facilitator) left `safety/handbook-before.md5` etc. inside the assistant's cwd; the assistant found and used `safety/t0` and the md5 file as its checksum baseline ("compare the handbook files against the checksums in safety/handbook-before.md5"). Study artefact, so the assistant's checksum check is real, but it would not have existed for a real user | turn-2 plan | Study setup |

What worked (new vs baseline): bound-org precondition handled in one `whoami`; single elicitation message; approval gate; validation iterated until clean; budget as ceiling, 1 of 15 returned; `progress` answers; independent re-check and `revises` rework without self-patching; scheduler `stop`; honest closing note including "wrong reports from the lead" and uncertainty about the fact-checker.

## Result score: **4 / 5**
All hard requirements are met: path, 909 words, four requested sections, brackets on every statement, independent check ran, handbook untouched, no web, 14 runs, plan before start and a closing note. It is a useful guide with friendly language. It loses a point for 3 small content/citation errors that the org's fact-check missed, an unsourced inference in the table, the missing laptop-shipping/pre-start steps, off-topic Month-1 items, and a polluted `out/` folder.

## Comparison with baselines (A: research, B: software)
- Setup: A/B had no tools (server refused to start), silent subagent fallback, false "I used orgmcp". C: setup mode + skill, `whoami` first, nothing improvised. Fixed.
- Requirements: A asked 0 questions and missed 5/7 needs; B ran against the live org. C asked once, all 7 needs elicited, plan approved before anything existed. Fixed.
- Budget: A stranded 16 of 28 runs and the assistant granted +4 unasked; C planned 15, used 14, declined the +3 request, budget returned. Improved.
- Review: A's reviewer hit the write-guard impossibility; C's charters use "findings -> author applies" and the assistant used `revises`. Fixed. But the org's own fact-check was again weaker than the assistant's pass (same finding as A).
- Delivery: A left the file in a private agent dir; C's final sits at the requested path, though only because agents wrote it there through the built-in `write`, and the org tree is out of sync with it (F1). New problem: relative-path semantics and polluted workspace.
- Safety: no access to the live org, config or web (A F11 config read did not recur).

## Recommendations
1. **Product (F1, F4, F5):** make built-in `write`/`read` resolve to the same root as orgmcp (or do not grant them alongside `workspace` for non-code goals); have `report` accept absolute paths under the workspace; keep agent memory out of the user's deliverable folder (e.g. run with cwd = agent dir and a separate `workspace` input/output). Add a validator warning for non-code goals that grant built-in `write`.
2. **Product (F2):** a first-class read-only inputs list in the blueprint (`inputs: [/path/handbook]`) that becomes readable without being writable (or at least a plan line stating "agents can read/write anywhere under X"). Today "never modify the handbook" is prose.
3. **Role template (F3, F8):** fact-checker template should require: list every claim with its cited file, check citation->source and arithmetic (word count via `read`), report coverage ("n of m claims"), and fail the review if the claim list is a sample. Manager template should quote counts from `read`, not from memory.
4. **Skill (F6, F7, F9):** keep "show the plan as returned", but allow a plain-words summary *plus* the full text on request; suggest delivering to an empty directory chosen with the user; add "a user who wants a note when done must ask: say so once in the plan".
5. **Docs:** note in README that the assistant's own verification step is the strongest quality gate (here it caught what two org fact-checks missed) so the skill's "check against EVERY criterion yourself" should stay mandatory.

## Safety check (before / after)
- `~/.kiro/settings/mcp.json` md5 `3eacba4e...` unchanged. Existing `~/.kiro/agents/orgmcp*.json` md5s unchanged; one new profile `orgmcp-orgmcp-c-1792261179-org-866561-read-write.json` (references only `<S>/org`), deleted at cleanup.
- Main checkout `git status --short`: empty before and after. Live org HEAD `5b94a6b` before and after; no commit mentions this scenario.
- Handbook md5s identical before/after. No process for `$S` left (scheduler `stop`ped by the assistant; checked). No `mcp.json`/settings reads in any transcript or run log.
- Agent runs: 14 (cap 25), user turns 7 (cap 8), ~41 min.

## User effort
7 turns (2 content, 1 approval, 4 "status?"), 0 commands run by the user, 0 files read by the user. All answers were short.
