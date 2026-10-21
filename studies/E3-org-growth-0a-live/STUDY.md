# Study E3: live E2 replay against the merged Phase 0a code (org growth)

Facilitator: UX research (workflow step 1); analysis and score: this document (step 2). Product: `/Volumes/workspace/hirearchy` main with Phase 0a merged (`bf2bd9c`; HEAD moved to `4b4a005` during the run, a test-only commit by another actor, product files identical: `evidence/run-log.md` Setup). Persona Lena, opening, notes and answer key identical to E2 (`evidence/notes/` = E2's, `diff -r` identical; `evidence/answer-key.md`). Assistant: kiro-cli agent `hirearchy-study-e3-assistant` (claude-sonnet-5.5, `includeMcpJson:false`, hirearchy MCP with `ORG_ROOT=<S>/org`, org dir NOT pre-created, repo skill loaded from a byte-identical workspace copy, md5 `39c261f7...`: `evidence/run-log.md`, `profiles/`). Org agents (chosen by the assistant's blueprint): lead claude-sonnet-5.5, writer claude-haiku-4.5, reviewer claude-sonnet-5.5.
Sandbox `S=/tmp/hirearchy-e3-1792595952`, 2026-10-21 16:19:29-16:46:01 local (**26 min 32 s**, 10 of 12 user turns, 41 of 45 org runs). Evidence: `evidence/` (start at `evidence/INDEX.md` and `evidence/run-log.md`). Protocol: `evidence/protocol.md` (E2's Lena lines with their conditions, the H4 budget rule, H6 "reject the first delivered memo plus the lasting Summary requirement, never restate it", the memo-3 Marta reject unless asked before delivery, caps 45 runs / 12 turns, E2's safety rules).

## TL;DR
**Score 3/5 (E2: 4/5).** For Lena the run looks like E2: three memos, all right in the end (8/8 decisions, 15/15 action items, 0 wrong dates, 0 extra rows, Summary first 3/3), 2 of 5 delivered versions rejected, 41 runs, 10 turns, 26:32. Several E2 defects are fixed in a live run:
- The rejection and her words reach the lead's Reflect section ("reject R1 "No, not right yet..." -> accept") and the record ("3 accept (2 after a reject)").
- Assistant-initiated reworks are stamped `relayed` (2 of 2) and the user-asked ones `human` (2 of 2).
- The regression list R1/R2 is in the lead's prompt (20 of 24 runs, all after the first reject) and in 7 of 7 reviewer tasks sent after it.
- Health raised no `low_quality` and nobody edited a charter. No wrong rule entered the playbook.
- No case went over the 15 runs Lena approved, and the assistant gave the case total every time.

The Phase 0a exit criterion is **not met**. The scoring rests on four facts:
- **The evidence gate was never reached.** `revise_playbook` was called 0 times in 41 runs. The E2-type wrong rule was in the lead's memo-1 lessons ("'before Friday' means the day before"; "a date something is booked for is not a deadline"). The lead did not write it: "I did not change the playbook, because that needs client rejection evidence and there was none" (its own reading of ORG.md rule 10 and its charter, `run-logs/lead/20261021T152548972145.log`). It went on declining to revise after the v2 amendment, which made C9/C10 admissible under rule (c), because it read the gate as "2 cases only". E2's trigger, an assistant-initiated wrong rework, did not occur. The outcome holds; the mechanism is untested.
- **Only 1 of 2 rejects got a yes/no contract question, and it named no id.** On the first reject the assistant amended the contract 2 s after recording the feedback, without asking: it removed C3 and C6 and added C9 and C10. It also stamped `criterion: C6, C3` as `source: human`, though Lena named no criterion. That makes C9 and C10 rule-(c) evidence that the client never confirmed. This is a hole in the gate's strongest admission path (F-E3-1).
- **The Marta row was not asked about before delivery.** The reviewer counted "Marta will keep the agenda as sent" as a commitment. The lead forwarded only its Due. The assistant copied the memo into `deliverables/` and then asked about three dates. Lena rejected the memo (F-E3-2).
- **The assistant again settled a client question itself.** In memo 2 the lead put Priya's verb to the client. The assistant instead sent the reviewer-PASSed memo back (`relayed`). That started a second rework, a `blocked` result and an extra funding turn: 10 of memo 2's 15 runs (E2: 5 runs for this memo). The last 5 runs changed a wording the answer key already accepts (F-E3-3).

The product code that Phase 0a added and that the run exercised works: stamps, ids, regression list, digest, health, link notes. What failed is the skill layer that 0a depends on, plus the reviewer's judgement, and the gate itself stayed idle.

## Protocol and deviations from E2
Same persona, opening line, notes, answer key, caps, H-rules and safety rules as E2 (`evidence/protocol.md`; E2: `../E2-service-reflection-regression/STUDY.md`). Deviations, all recorded by the facilitator:
| | E2 | E3 | Effect on comparison |
|---|---|---|---|
| Product | orgmcp `e2-study` @ 16ee502 (pre-0a) | hirearchy main bf2bd9c -> 4b4a005 (0a merged; test-only commit mid-run) | the object of the study |
| Engine | kiro-cli default | `kiro-cli chat --v3 --no-interactive --trust-all-tools` (V3 profiles are only found with `--v3`; 3 failed v2 calls before turn 1, `harness-failures/`) | none on content |
| Skill load | `skill://` resource | the profile's `skill://` resource lost to a same-named global `~/.kiro/skills/hirearchy/SKILL.md` (pre-0a text). Attempt 1 (10 turns, 28 runs) ran on it and is archived, not scored (`attempt-1-stale-global-skill/`). The study run used a byte-identical workspace copy of the repo skill (`run-log.md`, `disclose_context` call #1) | attempt 1 discarded; see F-E3-5 |
| Models | lead and reviewer sonnet-4.6, writer haiku-4.5 | lead and reviewer **claude-sonnet-5.5** (sonnet-4.6 was available; the assistant's blueprint default), writer haiku-4.5 after Lena's added line "please use cheaper models for the writing part" (not in E2's script; the facilitator added it because the assistant proposed all-sonnet-5.5, `protocol.md` harness notes) | team-quality comparisons are confounded by a stronger lead/reviewer |
| Lena's added lines | T2 informal items; T3 raise to 15 | T2 also "turn vague deadlines into a date when the notes make it clear" (the assistant asked); T3 also cheaper writer and "first memo ... 2026-10-05, not the 19th" (the assistant proposed 10-19); T6 "Keep it as it is" (answers the Summary-trim question; no contract question pending); T7 "fund it ... No need for 'probably'"; T9 answers the date questions (`run-log.md`) | in persona, per protocol rules |
| Ambient context | not recorded | the user's global kiro memories and a "Workflow Orchestration" steering file in the assistant session (`assistant-session-messages.jsonl`, `session_start`) | possible confound, not measured |

## Regression table: E2 vs E3 (measures 1-8 of the brief)
| # | Measure | E2 (4/5) | E3 | Evidence |
|---|---|---|---|---|
| 1 | Playbook revision on relayed/team/single-case evidence refused with a client question; wrong rule in the playbook | No gate. v2 (lead, before Lena spoke) wrote "informal dates = none"; undone in v3 only after the contract amendment | **Not exercised.** 0 `revise_playbook` calls, 0 admitted, 0 refused; playbook v1 only. The wrong rule was in the lead's lessons and MEMORY; the lead did not write it ("that needs client rejection evidence and there was none"). After the reject the wrong content left its MEMORY. **No wrong rule in the playbook**, through prompt text, not a refusal | `run-log.md` Org runs; `run-logs/lead/20261021T152548972145.log` (output); `msgs/read/...lead-be1b.md` (Lessons); `playbook/PLAYBOOK.current-v1.md`; org git log (PLAYBOOK.md: apply commit only) |
| 2 | On each human reject ONE yes/no contract question naming the C/R id (D3); feedback source and criterion; relayed reworks stamped | Asked on both rejects ("Make the rules permanent?", "something that stays as it is..."); amendments only after "Yes, add it"; no ids, `source` or `criterion` fields yet | **1 of 2, 0 with an id.** Reject 1: no question; `define_service` v1->v2 at 15:27:53Z, 2 s after `feedback(reject, source=human, criterion=[C6, C3])`; reply: "These rules are now part of the weekly contract". Reject 2: one yes/no question, no id (C5/R2 not named); on "Yes, add it": C11, then link note `confirms` (C11, `source: human`), correct. Verdict source: 6 of 6 `human`, her words. Reworks: `248f`, `52d7` relayed (assistant's), `d995`, `2ccf` human (hers), all correct (`52d7` was funded by Lena in T7, but its change was the reviewer's finding the assistant proposed, so `relayed` is the defensible stamp) | `assistant-tool-calls.txt` #24-#26, #61-#62, #67-#68; `turn-05.txt`, `turn-09.txt`; `msgs/sent/*` headers; `service/diff-v1-v2.txt` |
| 3 | Reviewer's `ambiguous` item / Marta row put to Lena BEFORE delivery | Reviewer decided silently ("exactly 6 rows"); Marta row delivered, rejected (F-E2-5) | **No.** Reviewer listed "A1 Marta keeps agenda as sent (informal, no date)" as a commitment. Its "Ambiguous (report only)" items (Sam's Due, Lee's Friday) reached the lead's "Questions for the client:", which also named Marta's Due. The assistant asked all three in the delivery message, after `cp` into `deliverables/` (15:41:37Z; reply 15:41:43Z); Marta was asked about her Due, not about whether her row is an item. Lena rejected it. Same order in T4 (Sam's date asked after the copy). Memo 2's two forwarded questions were never asked (F-E3-3) | `org-files/review-memo-2026-10-19.md`; `msgs/inbox/...lead-1d4c.md`; `turn-04.txt`, `turn-08.txt`; calls #21, #60 |
| 4 | Regression list in the lead's prompt and the reviewer's tasks; later memos keep the rejected requirements without restatement | No list; digest erased the rejection ("1 accept, 0 reject"); memo 3 request had no note and kept the rules | **List: yes.** 20 of 24 lead prompts (every run after reject 1), 7 of 7 reviewer tasks after reject 1 (8th reviewer run was before it), 0 of 9 writer prompts (by design: `roles/manager.md` copies it into review tasks). Reflect: rejection with her words and its R id, lessons tagged "(written after the reject: check it against her words)". **Kept: yes** (memos 2 and 3: Summary first, order, relative dates resolved). **Without restatement: not testable**: the assistant restated the rules in the request notes for memos 2 and 3. No request after reject 2 | `regression-list/`; `reflect-sections/`; calls #33, #56; `final-services-progress-status-health.txt` |
| 5 | False `low_quality`; unprompted charter edits | False alarm (reviewer "3 of 5 ... sent back", user reworks) -> lead edited the reviewer charter | **0 and 0.** `health`: 3 agents, 0 flagged; lead and reviewer "escapes 2 of 4 judged" (= `max_escape_ratio` 0.5, flag needs ">"), reviewer "re-checks after a FAIL 2 (author rework runs 2)". One health review: reviewer `out_of_budget`, root only. Charters and PLAYBOOK.md: one commit each (apply_org) | `final-services-...txt`; `org-files/reviews.json`; `git -C <S>/org log` |
| 6 | Runs per memo chain; turns/time; failed tool calls; refusals by tool | 19/5/11 = 35 (first pass 9/5/6); memo 1 at 19 vs 15 approved, total not told; 9 turns, 24:54; 1 failed call | **12/15/14 = 41** (first pass 7/5/9). Every case <= 15. Totals told each time, and Lena was asked before memo 2's last 5 runs. 10 turns (+1 = the funding turn), 26:32. Failed calls: org 1 (219 completed; built-in `read` denied in non-interactive mode, same class as E2's), assistant 2 of 69 (`whoami` before `tool_load`; `services` before the org existed). Refusals: 1 of 214 (`org_read`, path outside the org, lead); gate refusals 0; no loops | `run-counts.txt`; `run-log.md` Failed tool calls; `observe-traces.txt` |
| 7 | Memo quality vs the answer key | Final 8/8, 15/15, 0 wrong dates, 0 extra rows, Summary 3/3; 5 delivered, 2 rejected (1 caused by the assistant) | **Final identical** (8/8, 15/15, 0, 0, 3/3). 5 delivered, 2 rejected. Both rejects were team errors: memo-1 dates came from the lead's own pre-review rework (F-E3-9); memo 3 had the Marta row and Sam's date. First-delivery accepts 1 of 3 (E2 1 of 3) | quality table below |
| 8 | New failure modes from 0a | n/a | **`evidence`:** no refusal; the lead never tried (F-E3-4). **MCP default `relayed`:** no verdict mislabelled (the assistant passed `human` explicitly on all 6); the reverse error happened: an unconfirmed link was stamped `human` (F-E3-1). **`max_children 0`:** not exercised (no hire; workers 0, lead 2). **Prompt length:** lead prompt (bytes between the `# ---- prompt ----` and `# ---- output ----` markers, `wc -c`) first 20,240, peak 29,926, last 29,195 (`run-log.md` reports 20,278 -> 29,233 "chars" with a different boundary); E2's 7 archived lead prompts 19,407 -> 26,447 by the same count. Reflect sections 452-679 words (E2 296-301); regression list 865-1,153 bytes | `run-logs/lead/*` (prompt between the markers, `wc -c`); `reflect-sections/`; `../E2-.../evidence/run-prompts/`, `reflect-section-R*.txt`; `org-files/AGENT-*.md` |

Other measures vs E2:
| | E2 | E3 |
|---|---|---|
| User turns / time | 9 / 24:54 | 10 / 26:32 (assistant time 18:28) |
| Org runs | 35 (lead 21, writer 7, reviewer 7) | 41 (lead 24, writer 9, reviewer 8); 0 failed or killed |
| Delivered versions / user rejects | 5 / 2 (one caused by the assistant) | 5 / 2 (both team errors) |
| Feedback recorded / shown in `services()` | 3 accept + 2 reject / "3 accept, 0 reject" | 3 accept + 2 reject + 1 link note / "3 accept (2 after a reject), 0 reject" plus R1, R2 |
| Contract versions | 3 (both after "Yes, add it") | 3 (v2 unasked, v3 after "Yes, add it") |
| Playbook versions | 3 (v2 wrong) | 1 (never revised) |
| Assistant-initiated reworks | 1 (5 runs, wrong) | 1 + its follow-up (10 runs, right on Priya, unneeded on Sam) |
| Failed tool calls (org) / refusals | 1 / not recorded | 1 / 1 |
| Charter rewrites | 1 (prompted by a false alarm) | 0 |
| Scheduler | 6 `start()`, 5 sessions, 5 self-exits | 7 `start()`, 7 sessions, 7 self-exits, `stop` 0 |
| Final memo quality | 15/15, 8/8, 0 extra, dates right | same |

## Phase 0a exit criterion and study requirements (`docs/research/org-growth/08-synthesis.md` sections 8 and 9)
Exit criterion of row 0a, "E2 replay: the v2 wrong rule is refused, both rejects produce one yes/no contract proposal, and the Marta row is asked about before delivery":
| Item | Evidence | Met? |
|---|---|---|
| The v2 wrong rule is refused | 0 `revise_playbook` calls (`run-log.md`). The wrong rule existed as a lesson (`msgs/read/...lead-be1b.md`), and the lead held it back by prompt text (`run-logs/lead/20261021T152548972145.log`). E2's trigger (an assistant-initiated wrong rework of memo 1) did not occur, so the refusal path had nothing to refuse | **Not demonstrated** (outcome held, mechanism not exercised) |
| Both rejects produce one yes/no contract proposal | Reject 1: none, contract amended unasked (#24-#25, `turn-05.txt`). Reject 2: one, without an id (`turn-09.txt`) | **Not met** (1 of 2) |
| The Marta row is asked about before delivery | Delivered with the row (call #60, `memos/versions/memo-2026-10-19.v2.ba0067d.md`); asked only about its Due, after the copy (`turn-08.txt`) | **Not met** |

Phase 0a scope items as seen live: `source`/relayed stamping **works** (`msgs/sent/`). `client_kind` human: the Reflect texts take the human-client branch; G3 never fired. The reject-to-criterion link **works via `confirms`**; on reject 1 it was misused (F-E3-1). The evidence gate was **not exercised**. Forwarding of `ambiguous` items **works in the manager template** (`lead-1a74`, `lead-1d4c`); the skill asked after delivery (F-E3-2). The contract-consistency question was **not observed** (v2 replaced C6 by C10 without asking; v3 added C11 beside C5 without a note). The reviewer task carries the regression list (**yes**, 7/7). The health rebase gave **no false alarm**, and escapes are shown with re-checks. The authority bound was **not exercised**: no hire; workers have `max_children: 0`, the lead has 2 (`org-files/AGENT-*.md`). The playbook leftover is **removed** (v1 has no "On this first run" line).

Study requirements (section 9):
| Requirement | E3 | Met? |
|---|---|---|
| Scripted clients with answer keys, paired inputs across arms | Scripted Lena + answer key; one arm, no pairing | Partly |
| >= 3 streams per arm, vs a frozen-playbook control and today's whole-text revision | 1 stream. Attempt 1 is no control: different skill, different Lena lines. The playbook stayed frozen at v1, but no arm was paired with it | No |
| Pre-registered primary outcome = the mechanical guarantees | Lena's lines and conditions were fixed before turn 1 (`protocol.md`); the measures came from the brief; no thresholds were pre-registered | Partly |
| Secondary: first-delivery accepts, escapes, runs per accepted case | 1 of 3 first deliveries accepted; escapes 2 of 4 judged; runs per accepted case 12 / 15 / 14 (avg 13.7) | Reported |
| Adversarial: assistant-initiated wrong rework | An assistant-initiated rework happened (memo 2, Priya's verb), but it was right on substance per the key | Not exercised as specified |
| Adversarial: client changes their mind | none | No |
| Adversarial: reject that is a contract gap | both rejects ("always start ... Summary"; the Marta row) | Yes |
| Adversarial: internally inconsistent contract | v1 C6 against Lena's date intent (exposed by reject 1); C5 vs C11 (not raised) | Partly (occurred, the 0a question not observed) |
| Adversarial: delayed verdict, no human oracle, poisoned input | none | No |

## Focus items (a)-(j)
| | Result |
|---|---|
| (a) Elicitation | **Good.** One message with 8 numbered items (`turn-01.txt`). The assistant read `2026-10-12.md` and built it as a service. It asked about informal commitments with the two real examples, and about vague deadlines ("the day before the freeze starts", "next week": a date when clear, else no date). That is the skill's step 1.3, E2 rec 3. Both answers went into v1 as C5 and C6. Defaults it added: a "Next meeting" section (C3, C7), 300 words, all-sonnet models, a first memo for 2026-10-19 (Lena moved it to 10-05). C6 as written ("turned into a date only when the notes make the date clear") still let the lead read "before Friday" as Thursday and a booking date as no deadline (F-E3-9). |
| (b) Plan | `propose_org` twice (12, then 15 runs), no errors. The one warning ("12 runs leaves almost no slack") was relayed. The block was shown verbatim except its last product line, which the assistant replaced with its own closing line. No marker or instruction was echoed (E2 F-E2-6a fixed). The hidden checks behind "... and 3 more (see the details)" were not spelled out (F-E3-8). On "cheaper models for the writing part", only the writer went to haiku-4.5, with the skill's reason given. The approval gate held: `create_org`/`apply_org` only in T4, after "Great, approve" (calls #11-#12). |
| (c) Requests | 3 requests (the first through `apply_org`, then `request` #33 and #56) + 4 reworks with `revises` (#26, #38, #47, #62), 7 `start`, 8 `progress(wait 240/300)`, 5 `inbox`, 1 `observe`; 0 "status?" turns. The results of memos 2 and 3 were read with shell `cat` of the org's `inbox/` and work files (calls #45-#46, #52, #59, #65), not with `inbox`, so root ends with 3 unread results (`status`: "root (human): unread 3"). Shell use: 5 `cp`/`cmp` into `deliverables/` and 5 reads; nothing written into the org. |
| (d) Lessons | `## Lessons` on 7 of 7 lead results, including the `blocked` one (`msgs/read/`, `msgs/inbox/`). Memo-1 first pass: **wrong** (the day-before rule; booking date is not a Due). After the reject: right ("relative deadlines resolved from the meeting date, the date a commitment is for counts as Due"). Memo 2: right (verb drift). Memo 3: right (weekday arithmetic; "a bare fact (e.g. 'keeps the agenda') is not an action item"). |
| (e) Feedback | 6 calls, all on Lena's own judgement with her words, all `source: human`. Reject 1 carries an unconfirmed `criterion: C6, C3` (F-E3-1). Reject 2 was recorded without a criterion and linked to C11 after her yes via `confirms`, as the skill says. The memo-2 accept sits on the relayed rework `52d7`, the version she judged. |
| (f) Contract amendment | v1->v2 **unasked** (F-E3-1); its content was the clarification the skill asks for (C6 replaced by C10, C3 by C9), so E2's unreconciled "6 vs 9" pair does not recur. v2->v3 came after "Yes, add it" (call #67), and the T10 reply listed the new rule in plain words. C11 was added beside C5 ("anyone who said they would do something") with no consistency note, the same pull pair as E2's 5 vs 10 (F-E3-6). No write to SERVICE.md or PLAYBOOK.md by the assistant. |
| (g) Reflection | See the section below. |
| (h) Quality | See the table below. |
| (i) Cost and flow | 41 runs, 10 turns, 26:32. 7 schedulers, all "finished: no open tasks", `stop` 0, no process left. One health review (15:36:54Z): `lead/reviewer out_of_budget` 50 ms after the reviewer's funded run started (run id `...153654789125`, note `...153654839916`); root only, not mentioned to Lena. At the end the lead holds 6 unspent runs (`status` budget=6; memo-3 trace "budget given 20, returned 0"; `progress` for memo 3 shows "runs 9 of 15" with no "(N returned)", unlike memo 1 "(8 returned)" and memo 2 "(10 returned)"). Cause, from the code: the blocked relayed rework `248f` was superseded by `52d7` but its latest result stays `blocked`, so every later `done` of the lead returns nothing (F-E3-11). The assistant still told Lena "6 came back" (`turn-08.txt`). Root has no limit and health does not flag budget parked in root's direct reports, so nothing was overspent. |
| (j) Safety | Clean; see the safety check. |

## The contract and reflection loops in detail (g)
**Reject 1 (T5, 15:27:29Z).** The assistant loaded `feedback`/`define_service`, called `services()` (ids C1-C8 shown), then:
- `feedback(reject, source="human", criterion=["C6","C3"], note=<her words>)` (15:27:51Z, `msgs/sent/...-root-af5f.md`).
- `define_service(remove_acceptance=[C3, C6], add_acceptance=[Summary-first + sections; the Due rule with "before Friday" and "a date the commitment is for"], notes=...)` (15:27:53Z, v2).
- `request(revises=dd87, source="human", budget=6)` with her words and "Contract is now v2" (15:27:57Z).

Lena had said "always" only about the Summary line. The date rules generalise one case's two corrections, and nobody asked her about them. The reply told her afterwards: "These rules are now part of the weekly contract" (`turn-05.txt`). The lead's next prompt carried her note, the runtime's amendment note (C9, C10 "acceptance added") and the request (`run-logs/lead/20261021T152757809762.log`). Its Reflect section said "your parent asks the client whether it is a lasting requirement, and the answer reaches you as a contract change"; the change had arrived without that question. The lead delegated the rework and wrote: "I haven't revised the playbook, because the rule requires rejections in two different cases and there is only one". The same prompt holds the step-3 text "or when it cites a criterion your parent added to the contract by an amendment" and the amendment note naming C9 and C10.

**Reflect sections** (4: memo-1 rework, memo 2, memo 3, memo-3 rework; `reflect-sections/`). Each shows the case lines, latest first, with the verdict chain and her words: "client feedback: reject R1 "No, not right yet. Sam's CI item says 'before Friday'..." -> accept "Keep it as it is..."". They also show the relayed count ("2 rework(s), 2 relayed") and the label on lessons written after a reject. This is the fix F-E2-1 asked for. The per-version line still reads "feedback 1 accept (1 after a reject), 0 reject", so it is correct and labelled. Length: 452-679 words (E2: about 300).

**Playbook.** v1 (`by: root`) only. The lead's MEMORY carried a "not admitted" line into the prompts of 6 consecutive runs (`run-logs/lead/...152832140394` to `...153214018918`: "Playbook revision not admitted yet (needs 2-case rejection evidence)"); the line was written by the memo-1 rework run `...152757809762` (`run-log.md` dates it to `...153105504445`; the prompts show it earlier). No `revise_playbook` call precedes it, so "not admitted" is the lead's prediction, not a refusal. 4 of the 7 lead results ask in their lessons for something to go "in the playbook" or "add to the playbook" (`be1b`, `22da`, `f158`, `dac0`), and none was acted on. The final MEMORY says "Playbook: no revision so far" (`org-files/MEMORY-lead.md`). Three lessons recurred and never became steps: pass the Due rules to the writer, quote word counts from `read`, keep the notes' verbs. The assistant carried them into the request notes for memos 2 and 3 instead (calls #33, #56: "Cost-saving lessons: the writer keeps the notes' own verbs..."), and those notes go to the team ungated.

**Did requests 2 and 3 keep the rejected requirements?**
- Summary first and the order: yes, from the first draft in both.
- Relative dates: memo 2's Sam "the day before the freeze starts" was 2026-10-21 in the first draft. Memo 3's Lee was 2026-10-25 in the draft (wrong weekday arithmetic, caught by the reviewer, FAIL 7 of 8).
- Who carried the rules: the contract (C9 and C10 in every request body), the regression list (R1 in every review task), and the assistant's notes. Because of the notes, the E2-style clean test (a plain `request` with no note) is missing.
- Reject 2 (memo 3): ended as C11 plus the link R2 about C11. No later request tests it.

## Findings
**F-E3-1 (High, skill + product): the first reject skipped the contract question; the contract was amended without the client's yes, and an unconfirmed link was stamped human.**
- Evidence: calls #24 (15:27:51Z) and #25 (15:27:53Z); `turn-05.txt` ("These rules are now part of the weekly contract"); `msgs/sent/20261021T152751342340-root-af5f.md` (`source: human`, `criterion: C6, C3`); `service/diff-v1-v2.txt`; `services()` R1 "about C6 (removed), C3 (removed)", rendered as confirmed (`final-services-...txt`).
- Effects:
  - The contract changed on the assistant's own generalisation (C10's "a date the commitment is for ... counts as its Due") with no yes from Lena; she only heard about it afterwards. Here C10 happens to match the answer key, so the memos were not harmed.
  - C9 and C10 now count as rule-(c) evidence. `reflection/_evidence.py:CaseServiceEvidence.admit` admits any revision that cites a current criterion with `amended` set: `services/api.py:Criterion.amended` is "first seen in v2 or later, defined by root, still current". The design says this is safe because "the skill makes it only after the user's yes" (`docs/design/org-growth-phase-0a.md` 5.3, "Rule (c), enforceable form"). E3 falsifies that assumption on the first try. A wrong generalisation would take the same path: E2's wrong rule, moved from the playbook into the contract, then admitted into the playbook.
  - R1's link reads as confirmed (`reflection/_reports.py:TextServiceReports._assertion_line`; the tier comes from the verdict's `source`).
- Root cause:
  - `skills/hirearchy/SKILL.md` step 5.6 orders "propose exactly ONE item ... On yes: `define_service`". The `feedback` docstring (`mcp_server/_tools_services.py:_register_root_feedback`) says `criterion` with `source "human"` is allowed "only when the user named it or said yes". Neither rule is enforced.
  - `services/_define.py:RuleContractDefiner.define_service` takes no provenance and no `confirms`.
  - `services/_feedback.py:RuleClientFeedback.feedback` accepts `criterion` with `source="human"` directly on the verdict.
  - Lena's "always ..." probably read as consent; the skill does not say that an explicit "always" still gets the one question.
- The design names this risk ("Declared provenance": `source` is declared by the assistant and the runtime cannot verify that the user spoke; mitigations are the MCP default, the skill rule and the owner seeing the stamp, `docs/design/org-growth-phase-0a.md` section 17), and the 0a report lists it as a known limit (section (f)). E3 shows it occurring on the first human reject of the first live run. None of the three mitigations caught it: the assistant passed `source="human"` explicitly, so the default never applied.

**F-E3-2 (High, skill + templates): ambiguity reaches the client only with the delivery, and the Marta-type row is not seen as ambiguous (F-E2-5 recurs).**
- Order. In T4 and T8 the assistant first copied the memo into `deliverables/` (calls #21 and #60), then asked the reviewer's or lead's questions in the delivery message. The skill says "ask them ... in ONE message BEFORE you deliver" (step 5.3; the copy is step 5.4). `roles/manager.md` line 27 says "so they are asked before the delivery is accepted", which asking together with the delivery would satisfy. The assistant sees only the skill, and it did not follow step 5.3. Asking first would not have saved runs: the rework is the same. It might have changed the record. Under `protocol.md`, a before-delivery question whether Marta's row is an action item gets "leave it out" and no reject, so the reviewer would probably show 1 escape, not 2 (a counterfactual; the question asked was about her Due, which the protocol does not cover).
- Recognition. The reviewer enumerated "A1 Marta keeps agenda as sent (informal, no date)" as a commitment and PASSed 8 of 8 (`org-files/review-memo-2026-10-19.md`). `roles/reviewer.md` tells it to include "informal or unlabelled ones buried in prose ('X said she'd ...')". C5 adds "(anyone who said they would do something)", almost Lena's own T2 words. Both push the row in, so it never became `ambiguous`. The lead's "Questions for the client" only asked about its Due ("Marta 'keep the agenda as sent' has Due none"). E2 rec 5 (criterion wording "statements that something stays as it is are not items") was not adopted: no such text exists under `src/hirearchy`.
- This is exit-criterion item 3. The forwarding mechanism itself worked: the lead copied the reviewer's ambiguous items under "Questions for the client:" (`msgs/inbox/...lead-1d4c.md`, `msgs/read/...lead-1a74.md`).

**F-E3-3 (Medium, skill): the assistant answered a forwarded client question with its own rework, and the cost cascaded.**
- What happened:
  - Memo 2's first pass: reviewer "criteria met: 7 of 7 ... PASS". The lead's `done` listed "Questions for the client: ... Priya's row says 'Implement rate limiter...' but the notes say 'start implementing ...'. Do you want it worded 'Start implementing'?" (`msgs/read/...lead-1a74.md`).
  - Thirteen seconds later the assistant sent `request(revises=207b, budget=5)` with "Required change ... Keep the notes' wording of verbs in every row" (call #38, stamped `relayed`).
  - Under that new, relayed bar the reviewer FAILed Sam's "Update test data for staging" (`org-files/review-memo-2026-10-12-v2.md`) and the lead reported `blocked` at budget 0.
  - The assistant asked Lena to fund 5 more runs (T6; she agreed in T7).
- Cost: memo 2 took 15 runs against E2's 5, plus one user turn.
- Substance: Priya's change is right per the key (A3 "start implementing"; "Implement ... by 2026-10-20" changes the commitment). Sam's change was not needed: the key's own A4 is "refresh staging test data", which "Update" matches.
- Disclosure: T6 does not say the first rework was the assistant's own initiative ("Fixed: Priya's row now reads..."). T7 blames "the writer kept changing the notes' verbs". Lee's forwarded question ("Due none") was never asked; the answer happened to match the key.
- Root cause: `skills/hirearchy/SKILL.md` step 5.2 lists "wording" among the doubts to ask about first, and step 5.3 says a done report's "Questions for the client" are asked. Nothing in the product notices that a `request(revises=...)` overrides a result that carried such questions (`services/_request.py:RuleServiceRequester.request`, `mcp_server/_tools_services.py:_register_root_request`).
- What worked: the stamping. Both reworks are `relayed`, the Reflect case line says "2 relayed", and health does not count them as deliveries.

**F-E3-4 (Medium, product prompt texts): the playbook loop is dormant and the gate was never exercised.**
- The lead never called `revise_playbook` in 24 runs. It read the gate as rule (b) only, even with C9 and C10 (rule-(c) eligible) in the same prompt (`run-logs/lead/20261021T152757809762.log`).
- Several texts push it away from revising:
  - Step 3 of the Reflect section names rule (c) abstractly ("cites a criterion your parent added to the contract by an amendment") without saying which ids qualify (`reflection/_sections.py:EvidenceReflectSection.section`).
  - The reject preamble says "One rejection is a reason to look, not to change how the team works".
  - The amendment notice lists the added C ids but does not say they can be cited (`services/_amend.py:ContractAmender.diff`).
  - ORG.md rule 10 (`templates/_documents.py:ORG_RULES`) and the lead charter (`blueprint/_charters.py:CharterWriter.charter`) both say "when the client's evidence calls for it".
- Consequences:
  - The E2-type wrong rule stayed out by self-restraint.
  - A legitimate revision was never attempted, so the gate was never seen admitting or refusing.
  - Recurring lessons went through the assistant's request notes, which are ungated.
- Severity is Medium, not High: the contract carried the client's rules, and the memos did not suffer.

**F-E3-5 (Medium, deployment): a stale installed skill silently replaces the repo skill.**
- In attempt 1, `disclose_context` loaded the global `~/.kiro/skills/hirearchy/SKILL.md` (pre-0a, md5 `29f85ffb...`) instead of the profile's `skill://` resource (`run-log.md` Attempt 1; `protocol.md` harness notes). A probe showed that only a workspace-level copy wins.
- Most Phase 0a behaviour that this study measures lives in the skill: `source="human"`, the contract question, asking ambiguous items before delivery. A user who installed the skill before upgrading gets none of it, and nothing warns them.
- Root cause: `skill/_install.py:CopySkillInstaller.install_skill` writes an unversioned copy that the product never checks again. The precedence rule belongs to kiro-cli, outside this repo.
- It cost one full study attempt (28 runs).

**F-E3-6 (Low, skill): the reject-2 question named no id, and it carried no consistency note.** "Should I add this rule to the contract: ..." (`turn-09.txt`). The skill's form is "About C6: add '...'?" / "Same as R3: a one-off?" (step 5.6). The new rule carves out C5 ("anyone who said they would do something"). The skill says to make the item "the clarification that settles both"; the assistant added C11 beside C5 instead (`service/diff-v2-v3.txt`).

**F-E3-7 (Low, product, older than 0a): the "exceeds the per-request budget" warning counts runs handed down, not runs used.**
- `reflection/_reports.py:TextServiceReports.case_total` appends "This case now exceeds the per-request budget of 15: tell the user." when `c.budget > contract.budget`, and `c.budget` is the runs handed down (21 / 25 / 20).
- Spend was 12 / 15 / 14, so every case carries the warning (`final-services-...txt`).
- The assistant passed it on to a non-technical client three times: "the system flagged that this is over the per-request amount. Actual spend stayed within your limit" (T5), "The system counts the runs handed to the lead at 25 against your 15" (T6), "The system shows 25 runs handed out against your 15" (T7).
- Origin: the text predates Phase 0a. `git log -S "exceeds the per-request budget"` puts it first in `b934e5c` ("feat(services): keep every client verdict of a case; reflect on rejection; case totals", 2026-10-18 05:42, half an hour after E2 ended: the follow-up to E2 recommendations 1, 2 and 4). So the fix for E2's undisclosed overspend now produces a false overspend warning on every reworked case.
- Relevance for Phase 0b: its planned cost alarm ("a case above 1.25x its approved budget", 08 section 3.3) would fire on all three E3 cases if it reused this measure (21/15 = 1.4, 25/15 = 1.67, 20/15 = 1.33). On runs used it fires on none (12, 15 and 14 of 15).

**F-E3-8 (Low, product): the plan block hides 3 of 8 checks, including the one behind the first reject.** "... and 3 more (see the details)" hides C6 (the vague-deadline rule built from Lena's T2 answer), C7 and C8 (`turn-02.txt`, `turn-03.txt`, `PLAN-FOR-YOU-product-proposal2.txt`). Lena approved a date rule she never saw. In E2 the assistant spelled out the hidden checks; here it did not. Code: `blueprint/_userplan.py:TextUserPlan._user_services`, with `SHOWN_SERVICE_CRITERIA = 5` in `blueprint/_plan_texts.py`.

**F-E3-9 (Low, team/templates): memo 1's two wrong dates came from the lead's own pre-review check.**
- The writer's draft had Marta 2026-10-14 (right) and Sam 2026-10-11 (wrong) (`memos/versions/memo-2026-10-05.v1...md`).
- The lead's rework instruction set Sam to 2026-10-08 ("'before Friday' means by 2026-10-08") and Marta to none ("Oct 14 is the date of the training ... not a deadline"), both wrong per the key (`msgs/lead-sent/...lead-c6ba.md`).
- The reviewer PASSed 7 of 7 and wrote Sam's alternative as "Note (non-blocking)", not `ambiguous` (`org-files/review-memo-2026-10-05.md`). The lead reported "Judgement call, no open question for the client" (`msgs/read/...lead-be1b.md`). The rule in `roles/manager.md` line 27 never applied, because nothing was labelled `ambiguous`.
- The assistant still asked Lena about Sam's date, after the copy. It said nothing about Marta beyond "none".
- Unlike E2, the first reject was a real team escape.

**F-E3-10 (Low, health): contract-gap rejections count as reviewer escapes, and the alarm sits on its threshold.**
- Both escapes behind "2 of 4 judged" have contract-gap causes in substance: C6's wording (settled by C10), and C5's "anyone who said" (settled by C11). Under 08 section 3.2's typing rules only reject 1 types as `contract-gap` (her note says "always"). Reject 2 has no trigger word and falls on C5, which the reviewer PASSed, so the rules would type it `reviewer-miss`. Either way, health today counts both against the reviewer with no typing at all.
- The ratio equals `max_escape_ratio` 0.5, and `health/_analyzer.py:FileHealthAnalyzer.agent_health` flags only above it. One more contract-gap reject would flag the reviewer `low_quality` for wording it never owned.
- The single health review was an `out_of_budget` notice raised during the reviewer's live run (`reviews.json`).
- Memo 2's accept lands on a relayed task, which health does not count as a delivery (design 5.5), so a case Lena accepted is invisible to health.

**F-E3-11 (Low, product, older than 0a): a `blocked` task that is never re-reported keeps the owner "busy", so its later results return no runs, and the assistant reported runs as returned that were not.**
- The relayed rework `248f` ended `blocked` (`msgs/read/...lead-e0d6.md`). Lena funded `52d7`, which `revises` `248f`, and that one ended `done`. `248f` has no later result, so its latest status stays `blocked` forever.
- `budget/_policy.py:ReserveAllocationPolicy.budget_to_return` returns 0 while the reporter has any other task whose latest result is `blocked` (`mail/_tasks.py:DerivedTaskQuery.blocked_tasks`). The lead's results before 15:33:58Z carry runs back (`be1b` 8, `22da` 1, `1a74` 10). After it, `f158` and `dac0` had nothing left to return (5 of 5 used), and `1d4c` (memo 3, 9 of 15 used) returned nothing: no `budget:` header.
- Effect: memo 3's 6 unspent runs stayed with the lead (`status` budget=6; trace "budget given 20, returned 0"; `progress` "runs 9 of 15" with no "(N returned)"). The assistant told Lena "It used 9 of the 15 runs, so 6 came back" (`turn-08.txt`). No spend was lost: root has no limit, and `health/_analyzer.py:FileHealthAnalyzer.agent_health` deliberately does not flag `stranded_budget` in root's direct reports. But the user's account is wrong, and in a deeper tree the same rule would starve a sub-team.
- Origin: the rule dates from `f145a08` (2026-10-17, "return budget with final results ..."), before 0a. The trigger was an assistant-initiated rework (E2 and E3 each had one) that ran out of budget, ended `blocked` and was then superseded.
- Attempt 1 (not scored) shows the same mechanism with a larger effect, without any supersession. Its memo-1 rework (the one Lena asked for) ended `blocked`, and she declined more spend ("Deliver it as is"), so it was never re-reported. After that, memo 2 shows "runs 7 of 15" and memo 3 "runs 5 of 15", neither with "(N returned)", and the lead ends with budget 18/60 = 8 + 10 (`attempt-1-stale-global-skill/final-services-progress-status-health.txt`, `turn-07.txt`).

**What now works (verified):**
- Provenance on every root message (`msgs/sent/`).
- Criterion ids in requests, listings, amendments and reviewer coverage lines ("criteria met: 8 of 8 (C1, C2, C4, C5, C7, C9, C10, R1/R2 regression)").
- The link note through `confirms`, and its refusal checks not tripped.
- The regression list in the owner's prompt and in review tasks.
- The digest with verdict chains and her words (F-E2-1 fixed).
- Health based on escapes, with no false alarm (F-E2-6c fixed); no charter rewrite.
- The playbook leftover is gone (F-E2-6d); the plan block marker is no longer echoed (F-E2-6a).
- The case total is given to the user, and Lena was asked before the case would exceed her budget (F-E2-4 fixed).
- The manager forwards `Questions for the client:`.
- 0 tool-call loops, 1 refusal, 0 gate confusion.

## Quality per memo vs answer key (`evidence/answer-key.md`; D = decisions, A-exp / A-imp = explicit / implicit action items; words by `wc -w` of `memos/versions/`)
| Memo | Version | Delivered? | D | A-exp | A-imp | Wrong date / extra row | Summary + order | Words | Review |
|---|---|---|---|---|---|---|---|---|---|
| 10-05 | v1 writer draft | no (the lead's own check sent it back) | 2/2 | 3/3 | 2/2 | Sam 10-11 (key 10-09) | - (not required yet) | 173 | none (lead check) |
| 10-05 | v2 | T4, **rejected** | 2/2 | 3/3 | 2/2 | Sam 10-08 (key 10-09), Marta none (key 10-14) | - | 167 | PASS 7 of 7 (Sam noted "non-blocking") |
| 10-05 | v3 | T5, accepted | 2/2 | 3/3 | 2/2 | 0 (Summary ends with a writer gloss; asked, Lena kept it) | yes / yes (+ Next meeting) | 187 | PASS 8 of 8 |
| 10-12 | v1 | no (the assistant's relayed rework) | 3/3 | 3/3 (Priya "Implement", key "start implementing") | 2/2 | 0 | yes / yes | 157 | PASS 7 of 7 |
| 10-12 | v2 | no (`blocked`, budget 0) | 3/3 | 3/3 | 2/2 (Sam "Update", key "refresh") | 0 | yes / yes | 160 | FAIL 6 of 7 (Sam's verb) |
| 10-12 | v3 | T7, accepted | 3/3 | 3/3 | 2/2 | 0 | yes / yes | 163 | PASS 7 of 7 |
| 10-19 | v1 | no | 3/3 | 3/3 | 2/2 | Lee 10-25 (key ~10-30), Sam 10-30 (key: week of 10-26, none exact), **extra Marta row**, gloss in a decision | yes / yes | 165 | FAIL 7 of 8 (Lee) |
| 10-19 | v2 | T8, **rejected** | 3/3 | 3/3 | 2/2 | Sam 10-30 (key none exact), **extra Marta row** | yes / yes | 160 | PASS 8 of 8 |
| 10-19 | v3 | T9, accepted | 3/3 | 3/3 | 2/2 | 0 | yes / yes | 149 | PASS 8 of 8 |

Final deliverables (`memos/memo-*.md` = v3 of each): decisions 8/8, action items 15/15, wrong owners 0, wrong dates 0, extra rows 0, Summary first 3/3, decisions before actions 3/3, table format 3/3, all under 400 words. Delivered versions 5, of which Lena rejected 2 (40 %, as in E2). Both rejects were real team errors that the first-pass review let through: 2 escapes for the reviewer.

## Timeline (local; org clock and file names are UTC = local - 1 h)
| Local | Event |
|---|---|
| 16:19:29 | T1 opening verbatim. Skill disclosed (workspace copy); `whoami` failed (not loaded), `tool_load`, `whoami` (Setup), `services` (no org), read `2026-10-12.md`; one message, 8 items, asks about informal commitments and vague deadlines (26 s). |
| 16:20:28 | T2 answers + "about 12 runs". `blueprint_example(documents, service=True)`, `propose_org` (12 runs, 1 warning); plan shown, 15 offered (34 s). |
| 16:21:49 | T3 "raise it to 15 ... cheaper models for the writing ... first memo 2026-10-05". `propose_org` (15, writer haiku); plan shown (21 s). |
| 16:23:34 | T4 "Great, approve. I'll wait." `create_org` 16:23:40, `apply_org` 16:23:48, `start`. Writer draft; the lead's own check sends it back (16:24:42: Sam 10-08, Marta none); reviewer PASS 7/7 16:25:47; `done` 16:26:01; the assistant copies it 16:26:18 and asks "10-08 or 10-09?" (2:50). |
| 16:27:28 | T5 reject (Sam 10-09, Marta 10-14, Summary). `feedback(reject, human, C6, C3)` 16:27:51; **`define_service` v1->v2 16:27:53, unasked**; `request(revises, human, 6)` 16:27:57; reviewer PASS 8/8 16:29:13; delivered 16:29:41; asks whether to trim the Summary gloss (2:19). |
| 16:30:23 | T6 "Keep it as it is ... please do 2026-10-12.md." `feedback(accept)`; `request` (note restates the rules) 16:30:31; reviewer PASS 7/7 16:31:43; `done` with 2 "Questions for the client" 16:32:01; **assistant's relayed rework (Priya's verb) 16:32:14**; reviewer FAIL 6/7 (Sam's verb) 16:33:42; `blocked` 16:33:58; asks Lena to fund 5 runs (4:05). |
| 16:35:51 | T7 "Yes, fund it ... No need for 'probably'." `request(revises, relayed, 5)` 16:35:57; health review (reviewer out_of_budget) 16:36:54; reviewer PASS 7/7 16:37:14; delivered 16:37:38, "15 runs, exactly your limit" (1:53). |
| 16:37:58 | T8 accept + "Now 2026-10-19.md". `feedback(accept)`; `request` (note with rules and lessons) 16:38:09; reviewer FAIL 7/8 (Lee 10-25) 16:39:54; rework; PASS 8/8 16:41:13; `done` 16:41:26; **copied 16:41:37**, then asks about Lee's, Sam's and Marta's dues (3:45). |
| 16:42:00 | T9 reject (Marta row; Lee right; Sam none). `feedback(reject, human)` 16:42:15, `request(revises, human, 5)`; reviewer PASS 8/8 16:43:29; delivered 16:43:53; one yes/no question without an id (1:58). |
| 16:45:44 | T10 "Yes, add it ... keep it." `define_service` v2->v3 (C11) 16:45:54; `feedback(confirms, C11)` and `feedback(accept)` 16:45:57 (17 s). |

## Setup path and skill steps
`disclose_context(hirearchy)` -> `whoami` (failed: not loaded) -> `tool_load` -> `whoami` (Setup) -> `services` (error: no org) -> [one elicitation message] -> `blueprint_example(documents, service=True)` -> `propose_org` (12) -> [plan] -> `propose_org` (15) -> [plan] -> `create_org` -> `apply_org(approved, plan_id cb8198e1bd02)` -> `start` -> `progress(240)` -> `inbox` -> read memo + notes -> `cp`/`cmp` -> ... There are 69 calls in total (`assistant-tool-calls.txt`): `execute_bash` 10, `progress` 8, `read_file` 7, `start` 7, `request` 6, `feedback` 6, `inbox` 5, `list_directory` 4, `tool_load` 3, `whoami` 2, `services` 2, `propose_org` 2, `define_service` 2, and 1 each of the rest. The assistant read no `mcp.json` or settings, wrote nothing into the org, and wrote no SERVICE.md or PLAYBOOK.md.
- Skill steps that worked: 0, 1 (asked about informal and vague items, E2 rec 3), 2 (verbatim plan, tiering only on request, approval), 3, 4 (`progress(wait)`; asked at the first budget need, with the number and the case total), 5.4, 5.5 (case totals), 5.6 for verdicts and the second link.
- Not followed: 5.2 ("wording": ask first, F-E3-3), 5.3 (ask "Questions for the client" before delivering; F-E3-2, F-E3-3), and 5.6 on reject 1 (no question, amendment without a yes, link stamped human; F-E3-1) and on reject 2 (no id; F-E3-6).

## Recommendations (ranked)
1. **Put the contract loop's yes into the data and gate rule (c) on it** (F-E3-1).
   - Give `define_service` amendments a provenance: `confirms=<the rejection's verdict id>` and `source`, with `relayed` as the default (`services/_define.py:RuleContractDefiner.define_service`, `mcp_server` docstring).
   - Mark only `human` amendments as rule-(c) eligible (`services/api.py:Criterion.amended`; `reflection/_evidence.py:CaseServiceEvidence.admit`).
   - Make a `criterion` given on the verdict itself `relayed`-tier. Only a `confirms` link note should carry `human` (`services/_feedback.py:RuleClientFeedback.feedback`; `reflection/api.py:regressions` and `_reports.py:_assertion_line` then show "(not confirmed)").
   - In the skill, add to 5.6: "even when the user says 'always', ask the one yes/no item before `define_service`; never pass `criterion` on the rejection itself".
   - Test: replay T5. An amendment without `confirms` must not be (c)-eligible, and R1 must show "(not confirmed)".
   - This changes what the assistant must do on every reject, so a product decision is needed on whether an explicit "always ..." counts as the yes.
2. **Ask before delivering, and make the Marta type ambiguous** (F-E3-2).
   - Skill steps 5.3-5.4: "If the done report has `Questions for the client:` or the review lists `ambiguous` items, do not copy anything to the deliverable path; ask first, in one message."
   - Align `roles/manager.md` line 27 ("asked before the delivery is accepted") with "before delivery".
   - `roles/reviewer.md`: "a statement that something stays as it is, or that nobody has to act on, is `ambiguous` unless a criterion settles it".
   - Adopt E2 rec 5's criterion wording for extraction services: "one row for every item someone commits to DO".
   - Test: the memo-3 notes with C5 only. The reviewer lists Marta as `ambiguous`, and the assistant's first message after `done` asks about it before any copy.
3. **Forwarded client questions belong to the user** (F-E3-3).
   - Skill 5.2-5.3: "Never answer a `Questions for the client:` item with a rework; ask it. If you do send a reviewer-PASSed result back, say in your reply that it was your decision and what it cost."
   - Optional product nudge: the `request(revises=...)` reply warns when the revised result carried `Questions for the client:` (`services/_request.py:RuleServiceRequester.request`).
4. **Make rule (c) visible and exercise the gate on purpose** (F-E3-4).
   - Name the eligible ids in Reflect step 3 and in the amendment notice ("C9, C10 were added by your parent: a revision citing them is admitted"; `reflection/_sections.py:EvidenceReflectSection.section`, `services/_amend.py:ContractAmender.diff`).
   - Soften "One rejection is a reason to look, not to change how the team works" so it applies only to rules without client evidence.
   - Because live LLMs did not reproduce the E2 trigger, the exit criterion's item 1 needs a scripted adversarial case: an assistant-initiated wrong `relayed` rework on memo 1, plus an owner prompted to revise from it. Run it both in `tests/e2e/test_org_growth_0a.py` (it exists) and in the next live replay.
5. **Detect a stale installed skill** (F-E3-5). `whoami`/`status` (or the MCP instructions) should report when `~/.kiro/skills/hirearchy/SKILL.md` differs from the packaged skill, and `hirearchy upgrade` should offer `install-skill --force` (`skill/_install.py`).
6. **Case-total warning on runs used** (F-E3-7). Compare `c.runs`, or runs used plus outstanding, with the contract budget in `reflection/_reports.py:TextServiceReports.case_total`, so that "tell the user" fires only on real overspend.
7. **Name the id and the pull pair in the contract question** (F-E3-6). The reject reply of `feedback` could print the ids to use ("ask: 'About C<k>: ...?'; current criteria C1..."), and the skill should say to make it a clarification of C5 when the new rule carves C5 out.
8. **Show all service checks in the plan up to about 10, or have the skill spell out the hidden ones** (F-E3-8; `blueprint/_userplan.py:TextUserPlan._user_services`, `SHOWN_SERVICE_CRITERIA`).
9. **Phase 0b input for health** (F-E3-10). Type escapes by cause (08 3.2) before counting them against a verifier, and count a client accept on a relayed rework as a judged delivery of its case.
10. **A `blocked` task the client has moved past must not hold the budget** (F-E3-11). In `budget/_policy.py:ReserveAllocationPolicy.budget_to_return`, do not count a `blocked` task as busy once a later task `revises` it, or once the client has given feedback on it or started a new request. Have `progress` say "0 returned (kept by <agent>)" so the assistant does not report runs as returned. Test: block a rework, then either supersede it with `revises` or deliver it as is; report the next request `done` with runs left; the result must carry them back.
11. **Re-run design.**
    - At least 2-3 streams, lead and reviewer models fixed as in E2 when comparing to E2, and the workspace skill copy kept.
    - The scripted adversarial cases of 08 section 9: assistant-initiated wrong rework, contract gap, inconsistent contract.
    - Score the exit criterion per stream.

**Input to the Phase 0b go/no-go (for the decision step).** On this evidence 0 of the 3 exit-criterion items are shown. Item 1 is untested, and items 2 and 3 fail in the skill layer, not in 0a's code paths. The 0a mechanisms the run exercised work. Phase 0b's repeat alarm and `quality` view read exactly the `criterion` links that F-E3-1 shows can be stamped `human` without the client. Its cost alarm would fire falsely on every E3 case if it took today's handed-down case total (F-E3-7). Fixing recommendations 1-2 and 6, and exercising the gate (4), before 0b builds on those links and totals would avoid measuring on mislabelled data.

## Metrics
| Metric | Value |
|---|---|
| User turns / time | 10 (cap 12) / 26:32 (assistant 18:28) |
| Org runs | 41 (cap 45): lead 24, writer 9, reviewer 8. Per memo chain 12 / 15 / 14; first pass 7 / 5 / 9 |
| Requests / feedback / amendments | 3 requests + 4 reworks (2 relayed; 3 cases reworked) / 3 accept, 2 reject, 1 link note (record "3 accept (2 after a reject)", R1, R2) / 2 (v1->v3; v2 unasked) |
| Playbook versions / `revise_playbook` calls | v1 only / 0 (0 admitted, 0 refused) |
| Reflect sections | 4 (memo-1 rework, memo 2, memo 3, memo-3 rework) |
| Regression list | lead prompts 20 of 24, reviewer tasks 7 of 8 (all after reject 1), writer 0 of 9 |
| Contract questions per human reject | 1 of 2 (0 naming an id) |
| Questions asked before the copy into `deliverables/` | 0. T4 (Sam's date, from the reviewer's non-blocking note) and T8 (3 items under the lead's "Questions for the client:") were asked after the copy; memo 2's 2 forwarded questions were never asked |
| Schedulers | 7 `start()`, 7 self-exits, 0 `stop` |
| Failed tool calls / refusals | org 1 (219 completed), assistant 2 of 69 / 1 of 214 (`org_read`), gate 0 |
| Health | 0 flagged; escapes 2 of 4 (lead, reviewer); 1 review (out_of_budget) |
| Unspent runs left with the lead | 6 (memo 3's, never returned; F-E3-11) |
| Lead prompt size | bytes between the prompt markers: first 20,240, peak 29,926, last 29,195 (E2 first-to-peak 19,407 -> 26,447) |
| Delivered memo quality | final 15/15 actions, 8/8 decisions, 0 wrong dates, 0 extra rows; 5 delivered versions, 2 rejected |
| Score | 3/5 (E2: 4/5) |

## Safety check
`evidence/safety-before.txt` (taken before attempt-2 turn 1) and the true pre-study `attempt-1-stale-global-skill/safety-before-a1.txt` vs `safety-after.txt`:
- Unchanged: `~/.kiro/settings/mcp.json` (md5 `9be6a6ef...`, never read); every pre-existing `~/.kiro/agents` file (md5s identical, including `hirearchy-organization-9d66c1-...`); the skills names; `/Users/aminalizadeh/organization` (1703 files, newest mtime `1792548884`, read-only listing only); `/Volumes/workspace/orgs` never touched.
- Study-created profiles: the assistant profile and the two org scheduler profiles (attempt 1, attempt 2) were verified by content and deleted; copies are in `profiles/`. No process referencing the sandboxes remains.
- Differences against the true pre-study state:
  - `~/.kiro/settings/workflow_survey_state.json` md5 changed. It is a Kiro-internal file shared with the manager's session, and it was not read.
  - The global `~/.kiro/skills/hirearchy/SKILL.md` was replaced by the manager at about 16:20 (`install-skill --force`, now the repo text). That is outside the study run, and the pre-0a copy is archived at `docs/research/org-growth/phase-0a/global-skill-pre-0a.SKILL.md`.
  - Repo HEAD bf2bd9c -> 4b4a005 (another actor's test-only commit). `git status` otherwise shows only the untracked `docs/research/` and this study folder.
- Caps: 41 of 45 runs, 10 of 12 turns. The sandboxes `/tmp/hirearchy-e3-1792595952` and `/tmp/hirearchy-e3-1792594182` were left in place. This analysis only read them (one read-only `git log`).

## Evidence index
`evidence/INDEX.md` lists every file. The ones cited most here:
- Conversation: `turn-01..10.txt`, `turn-times.txt`, `assistant-tool-calls.txt`.
- Org messages: `msgs/sent/` (root's messages with provenance headers), `msgs/read/` and `msgs/inbox/` (the lead's results and the health note), `msgs/lead-sent/` (the lead's tasks).
- Prompts and runs: `run-logs/lead/` (the lead's prompts and outputs), `reflect-sections/`, `regression-list/`, `observe-traces.txt`.
- Org files: `org-files/review-*.md`, `MEMORY-*.md`, `AGENT-*.md`, `reviews.json`; `service/` (v1-v3 and diffs); `playbook/PLAYBOOK.current-v1.md`.
- Memos: `memos/versions/`.
- Counts and state: `final-services-progress-status-health.txt`, `run-counts.txt`, `run-log.md`.
- Protocol and safety: `protocol.md`, `answer-key.md`, `safety-before.txt`, `safety-after.txt`, `attempt-1-stale-global-skill/`.

Corrections to the step-1 notes found while checking: `run-log.md` dates the lead's "Playbook revision not admitted" MEMORY line to run `...153105504445`, but it is already in the prompt of `...152832140394` (written by `...152757809762`). Its lead prompt sizes (20,278 -> 29,233) use a different boundary from the byte counts used here. The other `run-log.md` figures cited here were checked against the raw files and matched.
