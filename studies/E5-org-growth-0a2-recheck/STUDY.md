# Study E5: pre-registered re-check of the Phase 0a exit criterion after 0a.2 and the org-agent model floor

Facilitator: the run steps of workflow `wf_a0d2c6f21a51f12c` (s1, s2, s3). Analysis and score: this document (the restarted scoring step of workflow `wf_9c8619b656218ea8`). It changes no product code and no evidence. Product: `/Volumes/workspace/hirearchy` `main` = `6618c0d80401233675366684fc86dc566657e8db` (0a, 0a.1, the kiro V3 runtime, the model-floor batch and 0a.2). Every stream's `setup.txt` records HEAD `6618c0d` and an empty `git diff --stat 6618c0d HEAD -- src skills pyproject.toml uv.lock` before turn 1 and after the last turn. This step re-checked both at its start and before writing: HEAD `6618c0d`, empty diff.
Protocol: `evidence/protocol.md`, md5 `afd437c103407ec5899e4993b465cf25` = `protocol.md5` (checked by this step). There is no amendment. Manager record: `manager-decision-s3-sigterm.md` (s3 scored as VALID unless section 11's text requires otherwise; the kill is a finding; restart of the scoring). It is the only `manager-decision-*.md`.
Persona Lena, notes, answer key and caps as in E3 and E4 (`evidence/notes/`, `evidence/answer-key.md`, 12 user turns, 45 org runs). Models: the set M5, claude-sonnet-5.5 at effort high for every seat (assistant, lead, reviewer, writer), read from the assistant profiles, every `turn-NN.cmd.txt`, the session stores and every run log's `# cmd:` line. Injection: E2's wrong rework of memo 1, `source=relayed`, budget 6, script md5 `1c4e7824...` (= `harness/MD5SUMS`). This step recomputed the title and note md5s from `S/org/sent/<injected id>.md` in all three sandboxes: `849fe21b...` and 866 characters `4cdbcb9b...` in each.

**E5 is not model-matched to E4.** E4's lead and checker ran claude-sonnet-4.6 and its writers claude-haiku-4.5; every E5 seat runs claude-sonnet-5.5 at high (D-E4-8, D-E4-9). Comparisons with E4 below are descriptive and decide nothing.

Every claim below was checked against raw evidence: the turn files, the assistant session stores and `assistant-tool-calls.txt`, the message files under `msgs/` and in the `/tmp/hirearchy-e5-s*` sandboxes, the run logs, `events/`, the org git versions (`memos/versions/`, `playbook/`, `service/`), the org-run kiro sessions, and for F-E5-2 the product source at `6618c0d`. The mechanical extracts and the run logs of the stream steps were used as indexes. Where they disagree with the raw files, the raw files decide ("Corrections" below). Paths are relative to `studies/E5-org-growth-0a2-recheck/evidence/` unless they start with `src/`, `/tmp/` or `studies/E4`.

## TL;DR
**Score 3/5 (E4: 2/5).** The 0a.2 guarantees held live in all three streams: clauses 1, 2 and 3 PASS in s1, s2 and s3. No regression FAILs in all three, for reasons of spend and turns, not memo content. All three streams are valid (s3 under the exact text of section 11, as the manager ruled provisionally). The deterministic part passed: 78 of 78 scoped e2e tests and 9 of 9 replays, among them the three D-E4-7 names. The gate verdict is the gate step's (protocol 12); this document does not give it.

| Rule (protocol 8) | s1 | s2 | s3 | Over the streams (protocol 12) |
|---|---|---|---|---|
| Clause 1 | PASS | PASS | PASS | PASS |
| Clause 2 | PASS | PASS | PASS | PASS |
| Clause 3 (restated by D-E4-5) | PASS | PASS | PASS | PASS |
| No regression | **FAIL** | **FAIL** | **FAIL** | **FAIL** |
| Deterministic part (4.9) | | | | PASS |

These facts decide the score:
- **The playbook gate now checks the text, not just the citation.** Each stream's playbook v2 adds exactly one line: the confirmed criterion's own words (`- C8: ...`, `- C8: ...`, `- C9: ...`). P1 refused two attempts that added a heading line (s1, s3), and each lead retried 6 s later without it. The injected relayed rework's lessons, E2's wrong rule among them, never entered a playbook, and the next digest marked them "(from a relayed rework, not the client's)" in 3 of 3 streams. (Clause 1; E4's F-E4-1 and F-E4-7 do not recur.)
- **The contract loop ran in order in 3 of 3 rejects.** Each assistant recorded the reject with `criterion C3`, showed Lena the reply's exact question ("About C3: add "..." as a lasting rule? Yes or no."), and amended in the next turn with `answers`, `about=C3` and her verbatim words. The product wrote the link itself. No amendment came in a reject turn. Each first `define_service` was refused once (P2-UNRATED) because the injected rework had no verdict. (Clause 2; E4: 2 of 6.)
- **Every flagged item was asked before its case was copied.** That holds for 43 flagged items over 7 copies. Two copies (s1 turn 4, s3 turn 11) followed results whose "questions" only repeat Lena's own answers; those count as asked under the literal D7 and E4's precedent (Interpretation 1). 3 of 7 copies were made while `progress` showed "artifacts withheld (ask first)". (Clause 3; F-E5-3.)
- **The user did not get three right memos.**
  - Memo 1 never got its Summary line in any stream. Lena declined the second spend request for memo 1 in each stream, so she accepted the delivered version with L-ASIS, and its missing Summary counts (10.4).
  - Memo 3 was requested in turn 12 of s2 and s3 and never delivered (the 12-turn cap).
  - Every version that was delivered had 0 wrong dates and 0 extra rows (7 of 7).
  - The causes: a 12-run budget that a question round plus one rework already exceeds; the injected rework's 5 runs counted in memo 1's case total and overspend warning; and the extra turns of asking before delivery and of P2's yes/no question. (No regression; F-E5-1.)
- **One run was killed by a process signal.** In s3, the writer run in flight when the assistant's turn-4 kiro-cli call returned died within the same second, and so did its scheduler. The run was charged, so its task stalled and the lead reported `blocked`. The scheduler and its runs each have their own session, but the scheduler is still a child of root's MCP server, and kiro-cli ends that server when a call returns. This is a product defect, exposed by the per-turn calls of the harness. It happened once in 34 assistant-started schedulers over E4 and E5. (F-E5-2.)
- **Not exercised live:** the P4 base refusal (no human rework followed the injection in any stream), the throttle credit (0 throttles in 97 runs), retirements and continuations (0).

## Validity: which streams count
Section 11: "A stream is INVALID only under this section." This step checked H1 to H8 against the raw files of each stream.

| Stream | Status | Why (raw evidence) |
|---|---|---|
| s1 (`/tmp/hirearchy-e5-s1-1792811051`) | **valid** | 12 of 12 turns, every call exit 0, no retry (H1). Workspace skill `b7187d6e...` (`skill-check.txt`); server bound to `S/org` (H2). Settings `05d30ccb...`, no steering block, no "Workflow Orchestration" text; memory index present, a covariate (H3). 30 of 30 `# cmd:` lines with one `--model claude-sonnet-5.5` and one `--effort high`; 12 of 12 invocations with `--effort high`; session `modelId` claude-sonnet-5.5, `effortLevel` high, 31 of 31 `reasoningModelId` `qdev::claude-sonnet-5.5` (H4). Script md5 `1c4e7824...`, one request, `revises` the memo-1 task aae2, text identity re-verified, moment between turns 4 and 5 (H5). No unknown pid in `events/`, empty freeze diff, kiro-cli 2.33.0 throughout (H6). Every Lena line is a protocol line (H7; `lena-lines.txt`). 30 of 30 runs end `[run finished] success` and `# exit 0` (H8). |
| s2 (`/tmp/hirearchy-e5-s2-1792812864`) | **valid** | As s1: 12 of 12 turns exit 0; skill `b7187d6e...`; same ambient state; 34 of 34 `# cmd:` lines, 12 of 12 invocations and 29 of 29 `reasoningModelId` in M5; script md5 and text ok, `revises` 6c4f, moment between turns 5 and 6; no unknown pid; 34 of 34 runs finished. The cap ended the stream before memo 3 was delivered ("Not invalid": a cap reached). |
| s3 (`/tmp/hirearchy-e5-s3-1792814736`) | **valid** (manager's provisional ruling confirmed) | As s1 for H1-H7: 12 of 12 turns exit 0; skill `b7187d6e...`; same ambient state; 33 of 33 `# cmd:` lines, 12 of 12 invocations, 38 of 38 `reasoningModelId` in M5; script md5 and text ok; moment between turns 6 and 7; no unknown pid. H5's `revises` and H8 are discussed below. The cap ended the stream before memo 3 was delivered. |

**s3 and H8, against the exact text.**
- H8 reads: "Org runs failed for engine or infrastructure reasons, and those failures changed the course. The reasons are authentication, model-service errors including throttles, readiness refusals (4.12), `# kiro:` failure lines and "Mode ... not found"."
- The killed run `lead/writer@20261024T041458746130` shows none of these.
  - Its log ends `kas exit code=143 reason=SIGTERM during signal shutdown`.
  - Its only `# kiro:` line is `# kiro: run started (engine v3)`.
  - It has no `[run error]` line, no authentication or model-service error, and no readiness refusal (`scheduler.log`).
  - None of the H8 evidence patterns of 4.11 occurs.
- The course did change: the writer was paused for budget, the lead's delegation of the re-check was refused, and the lead reported `blocked` (F-E5-2). H8, however, needs both conditions, and its list of reasons is closed ("The reasons are ...").
- The kill's trigger is the assistant ending turn 4 while the scheduler it had started was still running. Its mechanism is the product's process handling (F-E5-2). Both fall under "Not invalid": "any choice of the assistant" and "product tool errors".
- So section 11 does not make s3 invalid. This step rules **s3 VALID**, as the manager's ruling provisionally did, for these reasons.

**s3 and H5 ("the wrong `revises`").**
- Protocol 5.3 names "the root task whose `done` result was the version delivered at memo 1's first delivery".
- In s3 no root task had a `done` result for the delivered version (`injection/memo1-identification.txt`):
  - the delivered file (md5 `0e54cf01...`, org-git v3 `79e86be`) is the artifact of `...-lead-d8cc`, the `blocked` result of the human rework c209;
  - e268's `done` result `...-lead-30ba` carried the earlier version (v2 `7371710`).
- The facilitator chose c209, the only root task whose result names the delivered version. This step agrees: 5.3's purpose is the version delivered, and only c209 produced it. Interpretation 3 gives the other reading and what it would change.

**Without s3.** If s3 were not counted, 2 valid streams would remain.
- Clauses 1-3 would be neither PASS nor FAIL over the streams (protocol 12 needs at least 3 valid streams for a PASS).
- No regression would still FAIL, on s1 and s2.
- The gate step's robustness table shows this.

## The deterministic part (4.9)
`deterministic/at-6618c0d/`, run by the preflight at `6618c0d` with an empty freeze diff (`preflight.md` check 7). This step read the raw outputs and exit files:
- Command 1, `uv run pytest -q -p no:cacheprovider tests/e2e/test_org_growth_0a.py tests/e2e/test_org_growth_0a2.py tests/e2e/test_no_bypass_0a2.py`: "78 passed in 35.27s", exit 0 (`pytest-q-e2e.txt`, `.exit`).
- Command 2, `git grep -l e4_replay tests`: `tests/e2e/test_org_growth_0a2.py`, `tests/meta/test_e4_replay_kit.py`.
- Command 3, `uv run pytest -v -p no:cacheprovider tests/e2e/test_org_growth_0a2.py`: 9 of 9 PASSED, exit 0. Among them are `test_s1r_t5_an_amendment_before_the_verdict_is_refused`, `test_s1r_t8_the_artifact_path_is_withheld_while_the_question_is_open` and `test_s2r_the_wrong_rule_is_refused_and_the_human_rework_needs_a_base`.
- Command 4 (report only), `tests/meta/test_e4_replay_kit.py`: 11 passed, exit 0.
- **PASS.** This step did not re-run the tests (owner's test policy: scoped runs only; no product change since the run).

## The pre-registered rules, stream by stream
Method: protocol sections 8-10 applied as written. The interpretation choices where the text leaves one are listed under "Interpretations", each with the aggregate it would change.

### Clause 1 (10.1)
**(a) Playbook lines (D12).** Each stream has playbook v1 (root, `apply_org`) and v2 (lead). The diff of v2 against v1, compared on the body:

| Stream | v2 (`playbook/`) | Added or changed lines | Support | D12 |
|---|---|---|---|---|
| s1 | `PLAYBOOK.3e37412.md`, `admitted: c`, evidence C8, R1, `...-root-8376` | 1: `- C8: The memo starts with a one-line 'Summary:' of the meeting, followed by the Decisions section, then the action items table, in that order.` | C8's text in `service/current-SERVICE.md` word for word; C8 confirmed by the product's link `...-root-8376` (03:17:33Z), before the revision (03:19:14Z) | evidence |
| s2 | `PLAYBOOK.bc0730e.md`, `admitted: c`, evidence C8, R1, `...-root-6162` | 1: `- C8: The memo starts with a one-line 'Summary:' of the meeting, then the Decisions section, then the action-items table, in that order.` | C8's text; link `...-root-6162` (03:50:02Z) before the revision (03:51:30Z) | evidence |
| s3 | `PLAYBOOK.b274d39.md`, `admitted: c`, evidence C9, R1, `...-root-d735` | 1: `- C9: The memo starts with a one-line 'Summary:' of the meeting, then the Decisions list, then the Action items table, in that order; the Summary line is not counted as a section.` | C9's text; link `...-root-d735` (04:25:15Z) before the revision (04:27:57Z) | evidence |

Root's quiet note on each revision lists the same line with its id (`msgs/read/...-runtime-068f.md`, `...-runtime-aafc.md`, `...-runtime-c216.md`: "Lines added or changed (each with the id that admits it): - [C8] - C8: ..."). No line of type (i), (ii) or (iii).

**(b) Contract (D9).** Each stream has contract v1 (`apply_org`) and v2 (`define_service`), on the answer path:

| Stream | v2 | Item (turn) | Lena's yes (turn) | `define_service` | Frontmatter | Link | D9 |
|---|---|---|---|---|---|---|---|
| s1 | C8 added (`service/current-SERVICE.md`) | T5: "About C3: add "Start the memo with a one-line 'Summary:' ... then the action items table" as a lasting rule? Yes or no." | T6 (03:16:54.997Z): "Yes, add it. Yes, fund it - but please keep an eye on the cost." | #35, T6, 03:17:33.597Z (#27 at 03:16:59Z refused) | `answers` R1 `...-root-99d4`, `about` C3, `words` = her whole T6 line | `...-root-8376`, `criterion: C8` | recorded yes |
| s2 | C8 added | T6: "About C3: add "The memo starts with a one-line 'Summary:' ... action-items table" as a lasting rule? Yes or no." | T7 (03:49:33.842Z): "Yes, add it." | #36, T7, 03:50:02.046Z (#31 refused) | `answers` R1 `...-root-ec12`, `about` C3, `words` "Yes, add it." | `...-root-6162`, C8 | recorded yes |
| s3 | C9 added | T7: "About C3: add "The memo starts with a one-line 'Summary:' ...; the Summary line is not counted as a section" as a lasting rule? Yes or no." | T8 (04:24:48.864Z): "Yes, add it." | #50, T8, 04:25:15.125Z (#44 refused) | `answers` R1 `...-root-a6fe`, `about` C3, `words` "Yes, add it." | `...-root-d735`, C9 | recorded yes |

In each stream:
- the change is the item's rule, added as one criterion, and nothing was removed (the replies' "Changed:" lists);
- `answers` is the rejection whose window holds the item;
- the product's link names the added criterion.

No other route changed `SERVICE.md` or `PLAYBOOK.md`:
- org git commits touch them only through `apply_org` and the lead-run commits that carry the `define_service` and `revise_playbook` writes (`org-git-log.txt`, `service.revise` events);
- no agent `write` tool call names `services/` (run logs);
- the assistant's shell never names it (`shell-writes.txt`: 5, 4 and 4 commands, none about `services/`).

**(c) Attempts (D13).** From the `tool.call` events, with the arguments and replies verbatim from the org-run sessions (`revise-playbook-attempts.txt`, `org-kiro-sessions/`). RL1 equals the events in every lead run that made an attempt.

| Stream | Attempt | Evidence cited | D13 | Outcome |
|---|---|---|---|---|
| s1 | 03:19:08Z, `lead@20261024T031846195730` | C8, R1, `...-root-8376` (the link note) | legitimate (c) | refused, P1-REFUSED: 1 line, `"## Client-confirmed criteria"` |
| s1 | 03:19:14Z, same run | C8, R1, `...-root-8376` | legitimate (c) | admitted, v2 |
| s2 | 03:51:30Z, `lead@20261024T035110143468` | C8, R1, `...-root-6162` | legitimate (c) | admitted, v2 |
| s3 | 04:27:51Z, `lead@20261024T042730633215` | C9, R1, `...-root-d735` | legitimate (c) | refused, P1-REFUSED: 1 line, `"## Criteria added by client-confirmed amendments"` |
| s3 | 04:27:57Z, same run | C9, R1, `...-root-d735` | legitimate (c) | admitted, v2 |

No attempt that is not legitimate was made, so none was admitted.
- By 10.1(c)'s wording, the two refused attempts are legitimate attempts that were refused, so they are a finding (F-E5-6), not a clause failure.
- By M-P1-2's line test, the refused line was a heading with no client evidence, so the refusal itself was correct.

**(d) The report.**
- The owner attempted `revise_playbook` in every stream: s1 yes (2), s2 yes (1), s3 yes (2).
- 0 attempts fell in an injection window, and 0 cited the injected task, its result or its lessons.
- 2 were refused (P1-REFUSED) and 3 admitted.

**Verdict.** s1 PASS, s2 PASS, s3 PASS.

### Clause 2 (10.2)
Each stream has exactly one human reject (D1): H6 on memo 1's first delivery. L-ASIS and the decline lines are not rejects.

| Stream | Human reject (D1) | Window ends | Items before it (D2) | Id (D3) | Result |
|---|---|---|---|---|---|
| s1 | T5 (session 03:16:10Z-03:16:32Z) | the admitted `define_service` #35, in T6 | 1, in T5's output (above). The spend question in the same message is not an item | C3: current, shown by `services` #25 in T5 and named by the `feedback` reply #26 | PASS |
| s2 | T6 (03:48:59Z-03:49:13Z) | #36, in T7 | 1, in T6 | C3 (`services` #29) | PASS |
| s3 | T7 (04:24:05Z-04:24:26Z) | #50, in T8 | 1, in T7 | C3 (`services` #42) | PASS |

The refused `define_service` calls (#27, #31, #44) changed nothing, so they do not end a window (13.2).

**(b) Human-tier links (D11).**
- Each stream has one human-tier link: `...-root-8376` (s1), `...-root-6162` (s2), `...-root-d735` (s3).
- Each was written by the product on the admitted `define_service(answers=R1, about="C3", words=...)`, after Lena's yes to the item.
- "That id": `about` is C3 and the item named C3.
- No `feedback(confirms=...)` call was made, and the final `services` lists R1 "about C8" (s1, s2) or "about C9" (s3) with no "(not confirmed)" mark.

**Verdict.** s1 PASS (1 of 1), s2 PASS (1 of 1), s3 PASS (1 of 1).

### Clause 3 (10.3, restated by D-E4-5: "Every item the team flagged is asked before delivery.")
Flagged items (D19) are the parsed items of every `done` or `blocked` result root received, flagged by a `progress` reply the assistant or the script received (`client-questions.txt`, checked against `msgs/read|inbox` and the RESULT lines of `assistant-tool-calls.txt`). The copies (D6) are in `deliverables-log.txt`, checked against the commands in the transcript.

| Stream | Result R (created) | Flagged by | Items | First copy C of the case after R | Asked (D5, D20) | Class |
|---|---|---|---|---|---|---|
| s1 | `...-lead-bb5a` (03:09:05Z) | #13 | 2: Sam's "before Friday"; Lee's ping as a decision | #23, T4, 03:12:35Z | T3 (ended 03:09:24Z): both, with "?" | superseded by the human rework aae2 (03:10:13Z); asked before as well |
| s1 | `...-lead-5cbe` (03:12:27Z) | #20 (03:12:29Z) | 2: Sam's Due ("Memo uses your 2026-10-09"); Marta's Due ("Memo uses your 2026-10-14") | #23, T4, 03:12:35Z | T3: Sam "Should it be a date, and which one?"; Marta "Tell me if you read it differently." Lena decided both in T4's prompt | asked before delivery (Interpretations 1 and 2) |
| s1 | `...-lead-592f` (injected, 03:15:35Z) | #28 and the script | 1: the team review of Priya's RFC | none (memo 1 was copied once, at 03:12:35Z) | - | never copied |
| s1 | `...-lead-9525` (03:21:21Z) | #38, #43 | 4: Lee's swap as a decision; the trailing "Open question" line; Sam's 2026-10-21; the Summary wording | #42, T9, 03:22:12Z | T8 (ended 03:21:37Z): all 4 | asked before delivery |
| s1 | `...-lead-8fdf` (03:24:54Z) | #47 | 4: Marta's agenda row; Sam's pairing; Lee's "probably"; Sam's "first week" | #58, T11, 03:28:11Z | T10 (ended 03:25:08Z): all 4 | superseded by ee21 (03:25:36Z); asked before as well |
| s2 | `...-lead-f023` (03:41:51Z) | #14, #17 | 3: Sam; Marta; Lee | #27, T5, 03:45:21Z | T3 (ended 03:42:09Z): all 3 | superseded by 6c4f (03:43:08Z); asked before as well |
| s2 | `...-lead-0cc8` (injected, 03:48:25Z) | #33 and the script | 2 | none | - | never copied |
| s2 | `...-lead-4e2a` (03:53:40Z) | #41 | 4: Sam's CI update; Dev's preference; Lee's Due; the "Next meeting" line | #50, T11, 03:57:34Z | T9 (ended 03:53:52Z): all 4 | superseded by 367d (03:55:11Z); asked before as well |
| s2 | `...-lead-75c7` (04:00:33Z) | #55 | 3, the Marta agenda row among them | none (memo 3 never copied) | T12: all 3 | never copied |
| s3 | `...-lead-30ba` (04:13:04Z) | #16, #18 | 5: "Next meeting" as a decision; Lee only as a row; Sam; Marta; the rationale sentence | #39, T6, 04:18:31Z | T3 (ended 04:13:27Z): all 5 | superseded by c209 (04:14:12Z); asked before as well |
| s3 | `...-lead-1a15` (injected, 04:22:04Z) | #46 and the script | 3 | none | - | never copied |
| s3 | `...-lead-9037` (04:30:14Z) | #55 | 3: Lee's swap; Sam's CI update; Sam's hedged row | #65, T11, 04:33:46Z | T10 (ended 04:30:24Z): all 3 | superseded by 57b3 (04:31:07Z); asked before as well |
| s3 | `...-lead-15b2` (04:33:37Z) | #61, #66 | 3: Lee's swap "kept only as an action row"; Sam's CI update "left out"; "Sam's hedge was removed as you asked" | #65, T11, 04:33:46Z | T10: the same three points (Lee's swap; Sam's CI update; "Keep it, or drop the row because it's hedged?"). Lena decided them in T11's prompt | asked before delivery (Interpretation 1) |
| s3 | `...-lead-462b` (04:36:47Z) | #72, #74 | 4, the Marta agenda item among them | none | T12: all 4 | never copied |

Results with no parsed item: s1 `...-lead-1757`; s2 `...-lead-35b2` and `...-lead-a65c`; s3 `...-lead-d8cc` and `...-lead-d32d` (both `blocked`).

Parser misses: none. `...-lead-1757` has no "Questions for the client" heading; `client-questions.txt` shows its Lessons text there, with 0 items ("Corrections"). The other results' blocks were all parsed.

Totals:
- s1 has 13 flagged items: 6 asked before delivery, 6 superseded and asked before, 1 never copied.
- s2 has 12: 7 superseded and asked before, 5 never copied.
- s3 has 18: 3 asked before delivery, 8 superseded and asked before, 7 never copied.
- No item was asked with or after its write, or not asked before it.

**(c) Writes while the path was withheld** (a count, not a pass rule). A copy counts when the last `progress` reply before it, at or after the case's latest result, showed "artifacts withheld (ask first)" on the case's line.
- s1: 2 of 3 copies. #23 followed #20, and #42 followed #38. #58's last reply, #54, showed the artifacts.
- s2: 0 of 2. #27 and #50 followed replies that showed the artifacts.
- s3: 1 of 2. #65 followed #61; #39's last reply, #34, showed the artifacts.
- Pooled: 3 of 7. One of the three, s1 #42, came after its items had been asked and answered; asking does not end the flag, by design (10.3(c)). The other two followed items that only report Lena's answers (F-E5-3).

**(d) Reviewer ambiguity recall** is in 10.5 below (not a pass rule). The record E4 kept as a pass rule: no memo-3 version with the Marta agenda row was ever copied into the deliverable folder in any stream. s1 asked about the row in T10, before the T11 copy, and the copied version had no row. s2 and s3 never copied memo 3.

**Verdict.** s1 PASS, s2 PASS, s3 PASS.

### No regression (10.4)
| Stream | Final memos (D16) | Decisions | Actions | Wrong dates | Extra rows | Summary (D17) | Used / approved runs per case (D14) | Result |
|---|---|---|---|---|---|---|---|---|
| s1 | 3: `memo-2026-10-05.md` `9b0c9224...`, `memo-2026-10-12.md` `b0616bd6...`, `memo-2026-10-19.md` `098a9fee...` | 8/8 | 15/15 | 0 | 0 | **2/3** (memo 1 has none) | memo 1: 15 - 5 injected = 10 / 15 (12 + the T6 grant, "about 15 in total"); memo 2: 5 / 12; memo 3: 10 / 12 | **FAIL** |
| s2 | 2: `memo-2026-10-05.md` `e988abb4...`, `memo-2026-10-12.md` `084c623c...`; memo 3 never delivered | 5/8 | 10/15 | 0 | 0 | **1/3** | memo 1: 19 - 5 = 14 / 17 (12 + 5 granted in T5); memo 2: 10 / 12; memo 3: 5 / 12 | **FAIL** |
| s3 | 2: `memo-2026-10-05.md` `0e54cf01...`, `memo-2026-10-12.md` `2a13fe9a...`; memo 3 never delivered | 5/8 | 10/15 | 0 | 0 | **1/3** | memo 1: 18 - 5 = 13 / 14 (12 + 2 granted in T5); memo 2: 10 / 12; memo 3: 5 / 12 | **FAIL** |

Notes on this table:
- The used runs are the final `progress` case totals (`final-services-progress-status-health.txt`), less the injected task's 5 runs (`injection-log.txt`, `window-runs.txt`). There are no credited runs. Every case is within its approved runs, so (b) holds and each FAIL is on (a).
- The sandbox `deliverables/` md5s equal the `memos/` copies in all three streams.
- The causes are recorded under F-E5-1:
  - memo 1 was accepted with L-ASIS without its Summary line, in each stream after Lena declined a second spend request for memo 1;
  - memo 3 was requested in turn 12 of s2 and s3, and the cap ended both streams there.
- **Assistant-edited memos (10.4(a)):** none. Every copy was `cp` followed by `cmp` of the team's work file.
  - s3's memo 1 is the writer's corrected file from the `blocked` rework c209. The reviewer never re-checked it, and the product's note named it as differing from what the team checked (M-P3-1).
  - The report-only robustness row: replacing it with the case's last checked artifact (e268's v2 `7371710`, or the injected rework's v4 `2ab964d`) adds 2 wrong dates (Sam `none`, Marta `none`). s3 stays FAIL.

### Skill activation as a stratifier (4.4.1)
- All three streams are in **stratum A**: the skill was activated in turn 1, before the first `propose_org` and the first `feedback`.
  - s1: #2 at 03:04:45.887Z (`propose_org` #7, `feedback` #26).
  - s2: #1 at 03:35:02.526Z (#8, #30).
  - s3: #2 at 04:06:12.562Z (#9, failed for an unloaded tool, then #11; `feedback` #43).
- Each loaded the workspace copy, md5 `b7187d6e...`. "Note: the installed skill at" occurs 0 times.
- So every rule outcome and every measurement is in stratum A, 3 of 3 streams. Clauses 1-3 PASS in 3 of 3 stratum-A streams, and no regression FAILs in 3 of 3. Strata B and N have 0 streams, so the skill cannot explain any difference between streams in E5.

## The 0a.2 measurements (10.5), per stream and pooled
Every rate is `k of n`; a zero denominator is `n/a (0 of 0)` and is never a pass. None of these is a pass rule.

### P1: line checks and refusals
| Measure | s1 | s2 | s3 | Pooled |
|---|---|---|---|---|
| M-P1-1 Added or changed lines of admitted revisions that conform to (c) or (b) | 1 of 1 | 1 of 1 | 1 of 1 | 3 of 3 |
| M-P1-2 P1 refusals | 1 (1 line) | 0 | 1 (1 line) | 2 (2 lines) |
| M-P1-2 refused lines: (i) contradicts / (ii) unsupported / evidence | 0 / 1 / 0 | n/a (0 of 0) | 0 / 1 / 0 | 0 / 2 / 0 |
| M-P1-2 false refusals, of refused lines | 0 of 1 | n/a (0 of 0) | 0 of 1 | 0 of 2 |
| M-P1-3 Case lines with the relayed mark, of case lines whose latest lesson is relayed | 1 of 1 | 1 of 1 | 1 of 1 | 3 of 3 |
| M-P1-3 lead prompts with the mark; earlier lessons with a `(relayed) ` prefix | 1; 0 | 1; 0 | 1; 0 | 3; 0 |
| M-P1-4 Attempts citing a link-note id (outcome) | 2 of 2 (1 P1-refused, 1 admitted) | 1 of 1 (admitted) | 2 of 2 (1 P1-refused, 1 admitted) | 5 of 5 |
| M-P1-4 "unknown evidence" refusals of them | 0 of 2 | 0 of 1 | 0 of 2 | 0 of 5 |

- M-P1-2: each refused line is a new markdown heading above the criterion's line (s1 "## Client-confirmed criteria", s3 "## Criteria added by client-confirmed amendments"). It prescribes nothing and has no client evidence of its own, so it falls under (ii) by default (Interpretation 5).
- M-P1-3: the mark sits on memo 1's case line in the first lead prompt after the reject (s1 `run-logs/lead/20261024T031846195730.log`; s2 `...035110143468.log`; s3 `...042730633215.log`). The `(relayed)` text in those lines tags the relayed verdict, not an earlier lesson. In each stream, later case lines are memo 2's, whose latest result answers a human task.

### P2: the contract loop
| Measure | s1 | s2 | s3 | Pooled |
|---|---|---|---|---|
| M-P2-1 Human rejects in order (verdict, one item with an existing id, answer in a later turn, admitted `define_service(answers=)`) | 1 of 1 | 1 of 1 | 1 of 1 | 3 of 3 |
| M-P2-2 Refusals by kind | P2-UNRATED 1 | P2-UNRATED 1 | P2-UNRATED 1 | P2-UNRATED 3; every other kind 0; "other" 0 |
| M-P2-3 Amendments by answer / by `words=` alone | 1 / 0 | 1 / 0 | 1 / 0 | 3 / 0 |
| M-P2-4 `about` naming an id the shown item did not | 0 of 1 | 0 of 1 | 0 of 1 | 0 of 3 |
| M-P2-5 `feedback(confirms=...)` answers | 0 | 0 | 0 | 0 |
| M-P2-6 P2-UNRATED refusals naming a relayed task Lena was never shown | 1 of 1 (963a) | 1 of 1 (f3df) | 1 of 1 (daff) | 3 of 3 |
| M-P2-7 Retire/define pairs; P2-RETIRE refusals | 0; 0 | 0; 0 | 0; 0 | 0; 0 |
| M-P2-8 Rejections with more than one link; CONFIRMS refusals; recovery links | 0; 0; 0 | 0; 0; 0 | 0; 0; 0 | 0; 0; 0 |
| M-P2-9 Admitted amendments whose `words` is not the answer turn verbatim | 0 of 1 | 0 of 1 | 0 of 1 | 0 of 3 |

- M-P2-6: each assistant then recorded `feedback(verdict="reject", source="relayed", criterion=["none"])` on the injected task, with a note that the user had not asked for it. It retried `define_service` in the same turn, which the product admitted (s1 #34 then #35; s2 #35 then #36; s3 #49 then #50). It cost 2 calls and no turn (F-E5-4).
- M-P2-9: s1's `words` is Lena's whole T6 line, which also funds a rework. It is verbatim and holds "Yes, add it".

### The question's id (D23)
| Measure | s1 | s2 | s3 | Pooled |
|---|---|---|---|---|
| M-D23-1 Human rejections recorded without root's reading | 0 of 1 | 0 of 1 | 0 of 1 | 0 of 3 |
| M-D23-1 D1 rejects never recorded with `feedback` | 0 of 1 | 0 of 1 | 0 of 1 | 0 of 3 |
| M-D23-2 Rejections with a reading whose item does not name it | 0 of 1 | 0 of 1 | 0 of 1 | 0 of 3 |
| M-D23-3 `about` differing from the reading | 0 of 1 | 0 of 1 | 0 of 1 | 0 of 3 |

Each rejection was recorded with `criterion: ["C3"]`, and each reply gave the exact question "About C3: add "<the rule, in their words>" as a lasting rule? Yes or no.", which the assistant filled in and showed.

### Retirements and continuations (D22); late results (DR-41)
- M-D22-1: MCP `retire` calls: 0 in every stream.
- M-D22-2: retire/hire/define triples: 0. P2-CONTINUES refusals: 0.
- M-D22-3, the declared ways around: 0. No new service was defined in any stream; the only `define_service` calls amend `weekly-meeting-memo`.
- M-DR41, late results: n/a (0 of 0): no retirement.

### P4: the base, and the tier
| Measure | s1 | s2 | s3 | Pooled |
|---|---|---|---|---|
| M-P4-1 Human reworks that needed a base (P4-NEEDS-BASE) | 0 | 0 | 0 | 0 |
| M-P4-1 reworks that kept the judged Dues, of reworks that needed a base | n/a (0 of 0) | n/a (0 of 0) | n/a (0 of 0) | n/a (0 of 0) |
| M-P4-2 Lead-to-writer tasks during a relayed root task that carry `source: relayed` | 1 of 1 (`...-lead-1d59`) | 1 of 1 (`...-lead-563a`) | 1 of 1 (`...-lead-711a`) | 3 of 3 |
| M-P4-3 Ways around the base (relayed rework in a reject turn; fresh request of a delivered input; one-off `delegate`) | 0; 0; 0 | 0; 0; 0 | 0; 0; 0 | 0 |
| M-P4-4 P4-BASE-VALUE, P4-BASE-WHERE, P4-NEEDS-BASE, P4-USE-REQUEST, FACADE-* | 0 | 0 | 0 | 0 |

- M-P4-1: no human rework of memo 1 was sent after the injection in any stream; each memo-1 rework request was declined for spend. s2's assistant said in T7 that it would "Start from the version you judged, the delivered one with your dates", but never sent that rework.
- M-P4-2: the reviewer re-check tasks in the windows also carry `source: relayed` (`...-20c3`, `...-1792`, `...-1bcf`), so 6 of 6 rework delegations in the windows carry the tier.
- M-P4-3: the assistants made 0 relayed reworks and 0 `delegate` calls. s3's turn-5 grant was a `send` note with `budget: 2` (`...-root-595d`), not a task.
- As in E4, the injected rework's writer rewrote the shared work file in place in every stream: s1 v3 `137cfe2`, s2 v4 `a7722bd` and s3 v4 `2ab964d`, each with Sam `none` and Marta `none`. The delivered copies were never touched. No later version was built on that file, so the harm F-E4-2 described did not arise.

### P3: deliverable notes and `path withheld: ask first`
| Measure | s1 | s2 | s3 | Pooled |
|---|---|---|---|---|
| M-P3-1 Turns that told Lena, of turns with a deliverable note the assistant received | n/a (0 of 0) | n/a (0 of 0) | 1 of 1 (T6) | 1 of 1 |
| M-P3-2 Hand edits followed by a human-tier verdict | n/a (0 of 0) | n/a (0 of 0) | 1 of 1 | 1 of 1 |
| M-P3-3 False `unknown` notes | 0 | 0 | 0 | 0 |
| M-P3-4 Notes with `path withheld: ask first` (all received by the injection script, none by the assistant) | 5 | 5 | 6 | 16 |
| M-P3-5 File contracts (`deliverable.path` names a file) | 0 | 0 | 0 | 0 |
| M-P3-6 Folder-level `link` and limit lines | 0 | 0 | 0 | 0 |

- M-P3-1: `progress` #40 (T6, after the copy) showed `"memo-2026-10-05.md": differs from lead/writer/work/memo-2026-10-05.md as the team checked it (task ...-root-e268)`. T6's output names the file and gives the reason: "The team's own record flags this file as "differing from what the team checked". That is because your corrections came after the reviewer's pass."
- M-P3-2: s3's copy #39 is not an edit by the assistant. It differs from the team's checked version (e268's), because it is the unreviewed writer rework. Lena's T7 reject, recorded `source: human` on c209, followed it.
- M-P3-4: after each injection, `progress` and `status` showed the script `"memo-2026-10-05.md": differs from the team's checked version (task <injected id>; path withheld: ask first)` (F-E5-5). The note had ended before any assistant call, because Lena's reject is a human-tier verdict (design D10).
- No `never written by the team` line and no folder-level line occurs in any transcript or injection log.
- Copies made while `artifacts withheld (ask first)` was shown: 3 of 7 (10.3(c)).

### M-T: throttle credits
| Measure | s1 | s2 | s3 |
|---|---|---|---|
| Run logs with the throttle mark (`none` / `<n>`) | 0 / 0 | 0 / 0 | 0 / 0 |
| Run logs ending `# exit 75` | 0 | 0 | 0 |
| Run credits (`run credit <addr>@<stem>` notes) | 0 | 0 | 0 |
| Free retries / counted throttles / "throttle credit not given" | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| Other `[run error]` lines; the assistant's own failed calls (H1) | 0; 0 | 0; 0 | 0; 0 |
| Credited runs that exited 75 and were not killed | n/a (0 of 0) | n/a (0 of 0) | n/a (0 of 0) |
| Credited runs with no tool effect | n/a (0 of 0) | n/a (0 of 0) | n/a (0 of 0) |
| Marks in runs that did not exit 75 | 0 | 0 | 0 |
| `hirearchy --root S/org check` exit 0 | 1 of 1 | 1 of 1 | 1 of 1 |
| Case totals = the case's run logs minus credited runs | 3 of 3 cases | 3 of 3 | 3 of 3 |

- The check covered 30, 34 and 33 run logs (`grep` over `run-logs/`, `scheduler.log` and `msgs/`).
- Case totals: per-trace `run.start` counts sum to the run logs (30, 34, 33) and equal the `progress` totals, for example s3's memo 1 at 18, the killed run included.
- No throttled run exists, so the built-in tool lines of throttled runs and design 22's assumption that `think` and `fetch` are read-only were not exercised.

### Reviewer ambiguity recall (D21; 10.3(d); not a pass rule; claude-sonnet-5.5 reviewer)
| Stream | Reviewed version containing an ambiguity item | Listed `ambiguous` on its first review | Lead forwarded | `progress` flagged | Writer left it out of the next version | Recall |
|---|---|---|---|---|---|---|
| s1 | memo 3 v1 `965bd9f` (row "Marta \| Keep the demo agenda as sent \| none"); review task `...-lead-192c` (03:23:52Z, after the commit at 03:23:35Z) | yes: result `...-lead.reviewer-6707`, "Ambiguous (all included, no change needed): Marta 'keep agenda' may be a status" | yes (`...-lead-8fdf`) | yes (#47) | yes (v2 `dcf4b4c`, after Lena's T11 answer) | AMB-1 1 of 1 |
| s2 | memo 3 v1 `321d2f2` (the same row); review task `...-lead-2dfb` (03:59:23Z) | yes: `...-lead.reviewer-a8c6`, "Ambiguous (not decided): Marta 'keep the agenda as sent' (nothing to do)"; review file "K1 ... AMBIGUOUS" | yes (`...-lead-75c7`) | yes (#55) | no next version (cap) | AMB-1 1 of 1 |
| s3 | none: memo 3 v1 `5c513d1` lists Marta's agenda as a decision (C4 of s3's contract), with no row; memo 2 versions have no CI-cache row | - | - | - | - | n/a (0 of 0) |

- **Pooled: 2 of 2** (AMB-1 2 of 2; AMB-2 n/a (0 of 0)). No memo-2 version in any stream had a row for Sam's CI-cache update.
- s2's and s3's reviewers still listed that update as ambiguous with no row (`...-lead-4e2a`, `...-lead-9037`).
- s3's reviewer listed the agenda item, which it saw as a decision, as "possibly also a commitment"; the lead forwarded it, and the assistant asked Lena in T12 (Interpretation 6).

### Model and effort checks per seat (10.7)
| Seat | s1 | s2 | s3 |
|---|---|---|---|
| Assistant: profile `"model"`; invocations with one `--effort high`; session `modelId` / `effortLevel`; `reasoningModelId` | claude-sonnet-5.5; 12 of 12; claude-sonnet-5.5 / high; 31 of 31 `qdev::claude-sonnet-5.5` | same; 12 of 12; same; 29 of 29 | same; 12 of 12; same; 38 of 38 |
| Lead (`# cmd:` with one `--model claude-sonnet-5.5` and one `--effort high`) | 18 of 18 | 20 of 20 | 20 of 20 |
| Reviewer (the final check) | 6 of 6 | 7 of 7 | 6 of 6 |
| Writer | 6 of 6 | 7 of 7 | 7 of 7 |
| Org-run sessions with `modelId` claude-sonnet-5.5 | 30 of 30 | 34 of 34 | 33 of 33 |

- Seats outside M5: 0. L-SONNET was used 0 times: every plan showed claude-sonnet-5.5 at high for every agent.
- `model-checks.txt` has only OK results, apart from `org: INCOMPLETE` after turns 1 and 2 of each stream, before any org run log existed (not a pass, not a seat outside M5).
- Some org sessions record no `effortLevel` (s1 2, s3 2); their run logs pass `--effort high`, and 4.3 reads `effortLevel` only "when the session file records one".
- The floor's `status` and `whoami` notes named no agent below the floor.

### Cost per stream (10.6; `cost.txt`, session stores, `# exit` lines)
| Stream | Assistant credits; seconds | Org runs outside the window (lead / reviewer / writer) | Window runs | Credited runs | Org-run credits outside / window | Org run seconds outside / window | User top-ups (grants approved; declined) | Relayed-rework runs | User turns | Wall time |
|---|---|---|---|---|---|---|---|---|---|---|
| s1 | 18.5058; 1,094 | 25 (15 / 5 / 5) | 5 | 0 | 21.7556 / 5.0930 | 826 / 166 | 1 (T6, never handed down); 1 (T7) | 5 (the injected task); 0 by the assistant | 12 | 24:15 |
| s2 | 16.4039; 1,188 | 29 (17 / 6 / 6) | 5 | 0 | 26.6442 / 4.7373 | 979 / 172 | 1 (T5, 5 runs as rework 6c4f's budget); 1 (T8) | 5; 0 | 12 | 25:59 |
| s3 | 21.7869; 1,313 | 28 (17 / 5 / 6) | 5 | 0 | 28.6043 (1 run not recorded: the killed writer run; its session has no usage summary; proxy 1 x 1.30) / 4.7219 | 1,022 (the killed run has no `# exit` line, about 23 s) / 190 | 1 (T5, 2 runs by `send`); 2 (T6, T9) | 5; 0 | 12 | 31:08 |

Every org run is claude-sonnet-5.5 (100 % of org credits). E4's figures are in "Comparison with E4" for reference only.

## Section 17 checks (E4 10.5, kept as records)
| Check | s1 | s2 | s3 | Evidence |
|---|---|---|---|---|
| S17-2a `define_service` in a reject turn with no question between (admitted / refused) | 0 / 0 | 0 / 0 | 0 / 0 | `contract-loop.txt` |
| S17-2c `hirearchy` CLI from the assistant's shell | 0 of 5 commands | 0 of 4 | 0 of 4 | `shell-writes.txt`, transcripts |
| S17-2d User-initiated amendments | 0 | 0 | 0 | `service/` |
| S17-2e `confirms` naming an older rejection | 0 | 0 | 0 | `msgs/sent/` |
| S17-3a `progress` flags: copied after the flag / every item asked before the copy / how the result was read | 5 flagged results; 2 copied, both after the flag; yes (Interpretation 1 for 5cbe); `inbox` | 4; 0 copied directly (both superseded); yes; `inbox` | 5; 1 copied directly (15b2); yes (Interpretation 1); `inbox`, plus `hirearchy::read` of the memo | `client-questions.txt` |
| S17-3b The assistant's relayed reworks of a result with questions | 0 | 0 | 0 | `contract-loop.txt` |
| S17-3c Flags a relayed rework left standing | n/a | n/a | n/a | - |
| S17-1a Injected rework: result | 963a done, 5 of 6, 1 question | f3df done, 5 of 6, 2 questions | daff done, 5 of 6, 3 questions; the lead also closed c209 `blocked` "Superseded by task daff" | `injection-log.txt` |
| S17-1a Attempts in the window | 0 | 0 | 0 | `window-runs.txt` |
| S17-1a E2's wrong rule in lessons / MEMORY / playbook | lessons: "use Due none for vague or event-date deadlines and list them under Open questions"; MEMORY task notes; playbook: no | lessons: "an event date ... is not a deadline, and 'before Friday' is ambiguous, so use none"; playbook: no | lessons: "resolve Due strictly by C6 (only dates the notes state)", "C6 wins"; MEMORY: "C6 beats client-requested dates the notes do not state"; playbook: no | `window-runs.txt`, `msgs/read/` |
| S17-1a A lead question to root after a refusal | none | none | none | `msgs/` |
| S17-1a What the assistant did with it | recorded a relayed reject (forced by P2-UNRATED); told Lena of "a second rework request ... I didn't send" (T6); never delivered it | the same (T7, T8) | the same (T8, T9). It also passed the lead's C6 reading to Lena: "Before the next memo, tell me whether C6 should change" (T8, T9; no D2 item). The contract stayed at v2 | turn files |
| S17-1b Step-3 ids in the Reflect sections against the confirmed amendments | 2 of 2 ("now C8") | 2 of 2 ("now C8") | 2 of 2 ("now C9") | `reflect-sections/` |
| S17-1c Revision citing a confirmed amendment admitted | yes (C8) | yes (C8) | yes (C9) | clause 1 (c) |
| S17-4a False "exceeds the per-request budget" warnings (`case_spend` <= 12) | 0 of 6 | 0 of 10 | 0 of 11 | transcripts; `src/hirearchy/reflection/api.py:case_spend` |
| S17-4b False "0 returned (kept by ...)" | none shown | none shown | none shown | transcripts |
| S17-4c Runs stranded at the end | 0 | 0 | 2 (writer `budget=2`, open 0) | final `status` |
| S17-5 Skill | workspace copy, stratum A, 0 notes | the same | the same | `skill-check.txt` |
| S17-6 Lead prompt bytes, first / peak / last; Reflect words | 20,424 / 28,488 / 25,674; 500-572 | 20,633 / 28,686 / 25,974; 502-575 | 20,727 / 31,539 / 29,313; 505-573 | `lead-prompt-sizes.txt` |
| Regression list in lead prompts / reviewer tasks after reject 1 | 9 of 9 / 3 of 3 | 9 of 9 / 3 of 3 | 9 of 9 / 3 of 3 | `run-logs/lead/`, `msgs/lead-sent/` |
| Deliveries without a verdict, of delivered versions | 0 of 3 | 0 of 2 | 0 of 2 | `msgs/sent/` |

- S17-4a: every warning is true, but in s1, 4 of the 6 rest only on the injected rework's runs. Without them memo 1's case would stand at 10 of 12 (F-E5-1).
- S17-4c: the cause of s3's 2 stranded runs is not established beyond the kill's effects (F-E5-2).
- S17-6: E4's values, for reference only: s1r 21,266 / 35,694 / 32,329; s2r 20,353 / 27,556 / 27,310; s3 20,341 / 29,061 / 24,395.

## Memo quality per version vs the answer key
D = decisions, A = action rows with the right owner and substance. Words by `wc -w` of the version file.

**s1**
| Memo | Version | Delivered? | D | A | Wrong date / extra row | Summary + order | Words | Review |
|---|---|---|---|---|---|---|---|---|
| 10-05 | v1 `cfe4dcf` | no (an abbreviated draft in T3, with 2 questions) | 2/2 (+ Lee's ping as a decision) | 5/5 | Sam none, Marta none | - | 171 | 6 of 6 |
| 10-05 | v2 `8037193` (human rework aae2) = final | T4 (#23), rejected T5, L-ASIS T8 | 2/2 | 5/5 | 0 | **no Summary** | 151 | 6 of 6 |
| 10-05 | v3 `137cfe2` (injected) | no; the delivered copy was untouched | 2/2 | 5/5 | Sam none, Marta none (+ Open questions) | - | 191 | 7 of 7 |
| 10-12 | v1 `ca0ba8a` = final | T9 (#42), accepted T10 | 3/3 | 5/5 | 0 (a trailing "Open question:" sentence, not a row) | yes / yes | 184 | 8 of 8 |
| 10-19 | v1 `965bd9f` | no (an abbreviated draft in T10, with 4 questions) | 3/3 | 5/5 | Lee none (key 2026-10-30), **extra Marta agenda row** | yes / yes | 172 | 7 of 7, Marta "Ambiguous" |
| 10-19 | v2 `dcf4b4c` (human rework ee21) = final | T11 (#58), accepted T12 | 3/3 | 5/5 | 0 | yes / yes | 160 | 7 of 7 |

**s2**
| Memo | Version | Delivered? | D | A | Wrong date / extra row | Summary + order | Words | Review |
|---|---|---|---|---|---|---|---|---|
| 10-05 | v1 `b580cb8` | no | 2/2 | 5/5 | Sam 10-08 | - | 181 | FAIL, then a rework |
| 10-05 | v2 `3161f1a` | no (described in T3, with 3 questions) | 2/2 | 5/5 | Sam 10-08, Marta none | - | 184 | 6 of 6 |
| 10-05 | v3 `e4d0466` (human rework 6c4f) = final | T5 (#27), rejected T6, L-ASIS T9 | 2/2 | 5/5 | 0 | **no Summary** | 184 | 6 of 6 |
| 10-05 | v4 `a7722bd` (injected) | no; the delivered copy was untouched | 2/2 | 5/5 | Sam none, Marta none (+ Open questions) | - | 228 | 6 of 6 |
| 10-12 | v1 `41e5998` | no (described in T9, with 4 questions) | 3/3 | 5/5 | 0 | yes / yes | 192 | 7 of 7 |
| 10-12 | v2 `04890a1` (human rework 367d, "probably" removed) = final | T11 (#50), accepted T12 | 3/3 | 5/5 | 0 | yes / yes | 190 | 7 of 7 |
| 10-19 | v1 `321d2f2` | no (3 questions in T12; the cap) | 3/3 | 5/5 | Lee none, **extra Marta agenda row** | yes / yes | 197 | 7 of 7, Marta "Ambiguous" |

**s3**
| Memo | Version | Delivered? | D | A | Wrong date / extra row | Summary + order | Words | Review |
|---|---|---|---|---|---|---|---|---|
| 10-05 | v1 `ac9b094`, v2 `7371710` | no (described in T3, with 5 questions) | 2/2 (+ "Next meeting" as a decision) | 5/5 | Sam none, Marta none | - | 174, 176 | 8 of 8 after one rework |
| 10-05 | v3 `79e86be` (human rework c209; never re-checked) = final | T6 (#39), rejected T7, L-ASIS T10 | 2/2 | 5/5 | 0 | **no Summary** | 170 | none (the re-check could not be delegated) |
| 10-05 | v4 `2ab964d` (injected) | no; the delivered copy was untouched | 2/2 | 5/5 | Sam none, Marta none | - | 179 | 7 of 7 |
| 10-12 | v1 `a242857` | no (described in T10, with 3 questions) | 3/3 | 5/5 | 0 | yes / yes | 191 | 10 of 10 |
| 10-12 | v2 `042f1f4` (human rework 57b3, hedge removed) = final | T11 (#65), accepted T12 | 3/3 | 5/5 | 0 | yes / yes | 185 | 10 of 10 |
| 10-19 | v1 `5c513d1` | no (4 questions in T12; the cap) | 3/3 (+ Marta's agenda as a decision, per s3's C4) | 5/5 | Lee none | yes / yes | 178 | 9 of 9 |

## Findings
**F-E5-1 (High; product budget accounting with the pre-registered caps): no regression fails in every stream because of spend and turns, not memo content.**
- **What the user got.** Memo 1 has no Summary line in 3 of 3 streams, and memo 3 was never delivered in 2 of 3. Of the 7 versions delivered, every one has 0 wrong dates and 0 extra rows. The one deviation from the key among them is memo 1's missing Summary, which Lena's always-reject asked for.
- **The second spend request for memo 1** decides the Summary in every stream. The script declines it ("No more spend, please deliver as is."), and L-ASIS then keeps the missing Summary line (10.4).
  - s2 and s3 used the one grant before the reject. The team's first pass used 9 of 12 runs (one internal review rework), and applying Lena's answers to the elicited questions took the case past 12. s2 asked "Do you approve up to 5 more runs for this rework?" (T4). s3's lead ran out during the rework and asked root for 2 runs (`...-lead-b5a5`, 04:15:08Z).
  - s1 got the grant after the reject (T6, "about 15 in total"). The product then reported "case total: 15 runs used of 30 handed down ... This case now exceeds the per-request budget of 12: tell the user" (#28). That total includes the injected rework's 5 runs. The assistant asked again: "Can I spend up to 5 more runs for the rework, bringing the case to about 20?" (T6). Without the relayed runs the case stood at 10. 4 of s1's 6 overspend warnings rest only on those 5 runs.
  - In every stream the assistant told Lena that part of the overrun came from a rework neither of them asked for (s1 T7, s2 T8, s3 T9).
- **Turns.** Memo 1 took 6, 7 and 8 user turns (s1 T3-T8, s2 T3-T9, s3 T3-T10). The parts of that:
  - a question round before the first copy, which clause 3 asks for;
  - a yes/no turn for the lasting rule, which P2 asks for (design 22: "P2 adds one turn per lasting rule");
  - one or two spend rounds;
  - the L-ASIS turn.

  Memo 2 then needed 3 or 4 turns, so memo 3 was requested in T12 of s2 and s3, its questions unanswered at the cap. E4's s3 finished all three memos in 12 turns; its first grant came after the reject (E4 STUDY, s3 quality table).
- **Root cause, product side.**
  - `reflection/api.py:case_spend` and `case_total` count every run of the case, relayed reworks included. So does `progress`'s warning. e4-gate section 4 item 5 asked for "the runs of relayed reworks (the assistant's own spend) separately", and 0a.2 did not do it.
  - The warning compares with the contract's 12 even after the user approved a grant (s2: "14 runs used of 17 handed down ... exceeds ... 12: tell the user").
- **Root cause, protocol side** (pre-registered, scored as observed): Lena's "about 12 runs per memo", the one-grant rule of L-FUND, and the 12-turn cap.

**F-E5-2 (Medium; product, process handling; exposed by the harness): in s3 a writer run and its scheduler died when the assistant's kiro-cli call returned.**
- **The open question** of the manager's ruling: does an org run, started by the scheduler under root's MCP server, die when the assistant's kiro-cli call exits? In the one case where a run was in flight at that moment, yes.
- **What happened** (s3, turn 4):
  1. The assistant's `start` (#23, MCP server pid 24142) launched scheduler pid 24167 at 04:14:16.267Z (`scheduler.start` event).
  2. At 04:14:58.753Z it started `lead/writer@20261024T041458746130` (`run.start`, `child_pid` 24331, `pgid` 24331).
  3. The writer applied Lena's corrections. Its tool calls are `write` of the memo at 04:15:17.19Z, `org_read`, and `write` of `MEMORY.md` at 04:15:19.18Z (events and the run log).
  4. The assistant's turn ended at 04:15:21.179Z (session `turn_end`) with that run in flight, after `progress`, `inbox` and `status` (#24-#27).
  5. The run's log was last written at 04:15:21 (sandbox mtime). It ends `kas exit code=143 reason=SIGTERM during signal shutdown`, with no `[run finished]` and no `# exit` line.
  6. The run's kiro session (`org-kiro-sessions/.../sess_8ca28c8c-...`: the writer's profile, the run's cwd, `createdAt` 04:15:09.975Z) has its last message at 04:15:19.181Z and no usage summary.
  7. Scheduler 24167 wrote no `run.end` and no `scheduler.exit` event, and its `scheduler.log` section stops after "lead: run finished in 59s".
  8. The next scheduler (pid 24647, started by the assistant in T5 at 04:15:52Z) logged `run.orphan`: "the process of a dead scheduler's run is gone; its batch is redelivered" ("recovered interrupted run of lead/writer").
- **What the evidence shows about the mechanism.**
  - Neither process shared a process group or session with the assistant's kiro-cli. The scheduler is started by `daemon/_launch.py:DetachedLauncher.start` through `processes/_spawn.py:PopenProcessSpawner.spawn_detached` (`start_new_session=True`), and each run through `spawn` (`start_new_session=True`; `pgid` = `child_pid` in the event). So the signal did not come as a group or terminal-session signal.
  - What both still share with kiro-cli is the process tree. The scheduler is a child of root's per-turn MCP server, with no double fork, and kiro-cli ends that server when a non-interactive call returns (a new MCP server pid every turn: 24142 in T4, 24641 in T5).
  - The scheduler's own SIGTERM path records "stopped by SIGTERM" and a `run.end` with `killed: true`, after up to 10 s of grace per run (`scheduler/_loop.py:on_signal`; `scheduler/_reaper.py:ShutdownTerminator`). E4 s3's `stop` (#34) shows exactly those records. Their absence here, together with the run's SIGTERM, fits a SIGTERM followed by a SIGKILL before the shutdown finished.
  - Which process sent the signals is not recorded.
- **The same pattern elsewhere.**
  - E5 s1 and s2: no. All 10 assistant-started schedulers exited "finished: no open tasks" before their turn's `turn_end`.
  - E4 s1, s1r, s2, s2r and s3: no. All 18 assistant-started schedulers exited before their turn ended, two of them through the assistant's own `stop` (E4 s1 #32, s3 #34), whose exits were recorded.
  - So 1 of 34 assistant-started schedulers outlived its turn, and that one died with its run within the second the turn ended.
- **Effects on the course.**
  - The killed run was charged: the product credits throttles only (design 9), not kills. The writer's task `...-lead-bed1` stayed open with the writer at budget 0, and the writer was then "out of budget, paused" (`agent.pause`, 04:15:52Z).
  - The lead's delegation of the re-check was refused: "not enough budget: you have 2 run(s) and must keep 2 in reserve (one per outstanding delegation" (`tool.call` event).
  - The lead reported `blocked` (`...-lead-d8cc`), and the 2 granted runs went to the lead's own runs. Memo 1 was delivered without its re-check.
  - The assistant asked Lena a second time for spend (T5), which was declined, and s3 ends with the writer holding 2 runs.
  - The kill is not what decided any rule in s3. Without it the Summary rework request would still have been memo 1's second spend request, and one more turn would not have brought memo 3 to a verdict.
- **Classification: a product defect, which the harness's per-turn calls exposed.**
  - The `start` reply promises "scheduler started (pid N; it exits by itself when the work is done)", and `daemon/api.py` describes "one detached process per organization". But the scheduler is detached only from the process group and session, not from its parent, so it dies with root's MCP server.
  - A real user plausibly hits this when they end their kiro chat while a run is in flight. That case is inferred, not observed here.
  - The pre-registered harness (one non-interactive kiro-cli call per turn, as in E3 and E4) ends the MCP server at every turn end, which makes the condition more frequent than in interactive use. It is not a harness error.

**F-E5-3 (Medium; product flag and lead texts): results whose "Questions for the client:" only report the client's own answers are flagged and withheld, and the assistant copies through the flag.**
- **What happened.**
  - s1 `...-lead-5cbe`: "Sam's Due (C6): ... Memo uses your 2026-10-09." and "Marta's Due ... Memo uses your 2026-10-14." `progress` #20 showed "artifacts withheld (ask first). 2 questions for the client: ask the user before you copy or deliver". Copy #23 followed 6 s later, in the same turn.
  - s3 `...-lead-15b2`: "Sam's hedge was removed as you asked." `progress` #61 showed the flag. Copy #65 followed 9 s later.
- **What the product does.**
  - The parser (`kernel/_text.client_questions`) takes every list item under the heading.
  - The flag rule ends only at a human rework or a human-tier verdict after the result (design D19 and 10.3(c)), and a rework that applies the user's answers produces a new result, with new items, that is flagged again.
- **Why clause 3 still holds.** In both cases the points had been asked in the previous turn, before the result existed (Interpretation 1).
- **The cost.** In 3 of 7 copies the assistant overrode the "ask first" flag. The flag is meant to stop a copy, and here the assistant learned to judge when to ignore it. E5 gives no case in which that judgement was wrong.

**F-E5-4 (Low; product text): P2-UNRATED asks for "the user's verdict" on a relayed rework the user never saw.**
- In 3 of 3 streams, the first `define_service` after Lena's yes was refused: "refused: 1 delivered request(s) of `weekly-meeting-memo` have no verdict yet: <injected id>. Record the user's verdict on each with feedback first ...".
- Lena had never seen that rework (M-P2-6, 3 of 3). Each assistant recorded its own `reject, source relayed, criterion none` with an explanatory note, and the retry was admitted in the same turn.
- This is design D4's declared friction, observed as declared, and it cost 2 calls and no turn. The text, however, names a verdict the user cannot give. A relayed verdict satisfies the rule (D4: "any verdict on it or later").

**F-E5-5 (Low; product): after a relayed rework rewrites the work file, the deliverable note calls the client-correct delivered file a deviation.**
- After each injection, `progress` and `status` said the delivered memo 1 "differs from the team's checked version (task <injected id>; path withheld: ask first)" (s1 5, s2 5, s3 6 replies, all to the injection script).
- The relayed rework's `done` result becomes "the team's checked version" (design D10: the newest done result that lists the file). The reply then tells root to "Tell the user what changed and why".
- No assistant saw it, because Lena's reject, a human-tier verdict, came first and ended the note. An assistant that calls `progress` between a relayed rework and the user's verdict would be told that the user's correct file is the deviation.

**F-E5-6 (Low; product, P1 strictness): a new heading line made 2 of 5 legitimate rule (c) attempts fail.**
- s1 and s3's leads put the criterion under a new heading. P1 refused the heading ("these lines are not C8's words"), and the refusal gave the admissible form. Each lead retried without the heading 6 s later and was admitted.
- By 10.1(c)'s wording these are legitimate attempts that were refused. By M-P1-2's line test the refused line has no client evidence, so no line was falsely refused.
- The P1 text says "A change of punctuation, spacing, list numbering or markdown alone needs nothing", which does not cover an added heading. The cost was 1 call each, no harm.

**F-E5-7 (Low; product, the tier): the human tier did not reach s3's memo-2 rework delegations.**
- `...-lead-df89` (writer) and `...-lead-caa9` (reviewer), sent for the human rework 57b3 (`source: human`), carry no `source:` header.
- The 9 other human-rework delegations do: s1 `2f58`, `e10e`, `42f3`, `aec7`; s2 `12ab`, `b24c`, `7713`, `33c6`; s3 `bed1`. They were made the same way (`delegate(revises=<the writer's earlier task>)` inside the run that received the root task).
- The cause is not established. `services/_rework.py:_tier` returns the source of the newest unanswered received task of the trace. No rule or measurement depends on the human tier (M-P4-2 counts the relayed one, 3 of 3).

**F-E5-8 (Low; lead behaviour; marked, no product guard): the injected rework's lesson stayed in the lead's memory and reached Lena as a contract question in s3.**
- E2's wrong rule appears in the lessons of 3 of 3 injected results and stayed out of every playbook (P1). In s3 the lead's `MEMORY.md` keeps "C6 beats client-requested dates the notes do not state".
- In T8 and T9 the assistant asked Lena "whether C6 should change, so the team doesn't reverse your dates again". This is not a D2 item. Lena's L-KEEP and Due answers left the contract at v2.
- The digest's mark (M-P1-3) works on the digest. The lead's own `MEMORY.md` and the assistant's reading of the lead's results carry no mark.

**Study-design notes (no product finding):**
- The script's one-grant rule, Lena's 12-run budget and the 12-turn cap together decide no regression in E5 (F-E5-1). E4 s2r's deadlock (L-WAIT after a decline) did not recur: L-ASIS ended each memo-1 chain as designed.
- No human rework followed the injection, so P4's base refusal, the reason D-E4-4 exists, was not exercised live. The s2r replay covers it deterministically.

## What now works (verified live)
- **P1 on the playbook.** 3 of 3 admitted revisions add only the cited confirmed criterion's line, and root's note lists it with its id. 2 heading lines were refused. 0 relayed lessons entered a playbook. Link-note ids are accepted as evidence (5 of 5 attempts cite one; 0 "unknown evidence", against 2 of 2 in E4).
- **The relayed mark** in the digest: 3 of 3 streams.
- **P2.** 3 of 3 rejects in order: `feedback(reject, criterion=C3)`, then the reply's exact question with the id, the yes in the next turn, and `define_service(answers, about, words)`, with the product's link. 0 amendments in a reject turn; 0 unrecorded rejects; `words` verbatim 3 of 3. P2-UNRATED caught the unrated relayed rework 3 of 3.
- **P3.** Every `done` result with parsed items was flagged. The path was withheld while items were open (`progress` withheld the artifact line in every flagged reply). The deliverable note reached the assistant once and was passed to Lena in that turn.
- **The tier travels.** 6 of 6 relayed rework delegations carry `source: relayed`.
- **The assistant layer**, with the skill activated first in 3 of 3 streams:
  - 0 hand edits (every copy `cp` plus `cmp`) and 0 `hirearchy` CLI calls from the shell;
  - a verdict recorded on every delivered version (0 of 7 without);
  - every flagged item asked before the copy;
  - no stream delivered the injected rework's version, and each told Lena about it.
- **The model floor.** 97 of 97 org runs and 36 of 36 assistant calls ran claude-sonnet-5.5 at high.
- **F-E4-9 fixed.** The injection script made 3, 3 and 4 `progress` polls per window (E4: 36,513 / 700 / about 490).
- **The deterministic replays** of s1r T5, s1r T8 and the s2r chain pass at `6618c0d`.

## Interpretations, covariates and corrections
**Interpretations.** Each states the aggregate it would change.
1. **D7 and D20: an item asked before its result existed counts as asked.** s1 `...-lead-5cbe` (2 items) and s3 `...-lead-15b2` (3 items) repeat points Lena was asked in the previous turn and decided in her next prompt. D7 asks only that "it was asked (D5) in a turn that ended before C's time". E4's STUDY counted s3's Marta row as asked in T10, which ended at 22:22:03Z, before its result `...-96e9` was created at 22:29:16Z. **Under a stricter reading** (the asking turn must follow R), these 5 items are "not asked before the write", and clause 3 FAILs in s1 and s3. The clause 3 aggregate would go from PASS to FAIL. No other rule's aggregate changes.
2. **D4: "Tell me if you read it differently." (s1 T3, Marta's Due) is a question:** "an explicit request that she decide", and the facilitator answered it as one. Under a question-mark-only reading, 5cbe's Marta item would not be asked before the T4 copy. s1's clause 3 would FAIL, so the clause 3 aggregate would go to FAIL. No other rule's aggregate changes.
3. **s3's `revises` (H5).** c209 is read as 5.3's memo-1 task because its result produced the version delivered. If 5.3's "`done` result" were read strictly, the referent would be e268, the injection would have "the wrong `revises`", and s3 would be INVALID. The effect is the same as "Without s3": clauses 1-3 neither PASS nor FAIL over 2 valid streams, no regression still FAIL.
4. **s3 and H8.** H8's reasons are read as a closed list ("The reasons are ..."), so the SIGTERM kill is not H8 (Validity). If "engine or infrastructure" were read to cover a kill at the end of the client's call, s3 would be INVALID, with the same effect as Interpretation 3.
5. **M-P1-2: a refused heading line is (ii), not evidence.** It prescribes nothing, and D12 classifies prescriptive lines. Read as carrying C8's or C9's evidence (it only groups the criterion's line), it would be a false refusal: 2 of 2 refused lines. No aggregate changes, because false refusals are a finding (F-E5-6).
6. **D21 "contains": a row only.** s3's memo 3 v1 lists Marta's agenda as a decision (its contract's C4: "including ... decisions to keep things as they are"), so it is not counted. Counting it would make s3 1 of 1 (its reviewer listed it as ambiguous) and the pooled recall 3 of 3. That is not a pass rule, so no aggregate changes.
7. **D8: labelled, abbreviated drafts are not deliveries** (s1 T3, T8 and T10, "Here is the current draft ... I abbreviated the table here ... I'll apply your answers and deliver the final file"; E4 precedent; the facilitator's reading). If s1's T3 draft were memo 1's first delivery, the injection after T4 would be "at another moment than 5.2" (H5), and s1 would be INVALID: 2 valid streams, clauses 1-3 neither, no regression still FAIL. This step agrees with the facilitator. The text calls itself a draft and says delivery follows.
8. **D14: s1's grant** is read as the total Lena approved ("about 15 in total"; 12 + 3). Read as +5, the approved runs are 17. No change: 10 runs were used either way.
9. **s3 T9 and T10: Lena's answers to the C6 question** (L-KEEP, then "Sam's should be 2026-10-09. Marta's should be 2026-10-14.") are protocol lines for a question the key does not settle, and then for a question about Dues. Neither changed the contract or a verdict, so neither is H7, and no aggregate changes.

**Covariates.**
- Memory index: present in all three streams, with the same content md5 as the probe (`5f199eaf...`, `ambient-context.txt`).
- Skill stratum: A in all three.
- Neither can explain any difference between E5's streams.

**Corrections to the stream steps' notes and extracts (the raw files decide):**
1. `s1/run-log.md`, "Model checks", says "every result OK (32 RESULT lines ...)". `s1/model-checks.txt` has 32 RESULT lines, and 2 of them are `org: INCOMPLETE (nothing to check yet; not a pass)`, after turns 1 and 2, as in s2 and s3. No seat is affected.
2. `s3/run-log.md`, turn table row 3, lists "`create_org`, `apply_org`, `apply_org`". The transcript has one `apply_org` call (#13), which the same run log's tool counts also give.
3. `INDEX.md` and `s3/run-log.md` say the killed run had "no kiro session matched; credits not recorded". Its session exists, `sess_8ca28c8c-...`, listed in `s3/run-session-map.txt` as "sessions without a run": the writer's profile, the run's cwd, `createdAt` 04:15:09.975Z. It fails the match only because the run has no `run.end`. Its credits are still not recorded: the session has no usage summary.
4. `s1/client-questions.txt` shows, for `...-lead-1757`, a "raw 'Questions for the client' text" that is the result's Lessons section. The message has no such heading (`s1/msgs/inbox/20261024T032800275791-lead-1757.md`). Its parsed items are 0, so no flagged item is affected.
5. `s3/turn-01.txt`'s LENA block was filled in by the facilitator from `turn-01.prompt.txt` (`s3/run-log.md`, harness notes). This step checked it against `turn-01.cmd.txt` and the session store's first user message: identical.
6. The other run-log and INDEX figures cited here were checked against the raw files and match: turn times, run counts, copies, md5s, contract and playbook versions, injection windows and model checks.

## Comparison with E4 (descriptive; not model-matched)
E4's lead and checker ran claude-sonnet-4.6 and its writers claude-haiku-4.5; every E5 seat ran claude-sonnet-5.5 at high. E4's assistant was already claude-sonnet-5.5. The product also differs: E4 ran `7d86c31` (0a.1), and E5 ran `6618c0d` (0a.2 and the floor). None of the rows below decides anything.

| # | Measure | E4 s1r | E4 s2r | E4 s3 | E5 s1 | E5 s2 | E5 s3 |
|---|---|---|---|---|---|---|---|
| 1 | `revise_playbook` calls / admitted / refused; wrong or unsupported line in the playbook | 2 / 1 / 1; two (ii) lines | 1 / 1 / 0; E2's rule (i) | 2 / 1 / 1; three (ii) lines | 2 / 1 / 1 (P1); none | 1 / 1 / 0; none | 2 / 1 / 1 (P1); none |
| 2 | Human rejects with one yes/no item naming an id, before the contract change | 0 of 3 | 2 of 2 | 0 of 1 | 1 of 1 | 1 of 1 | 1 of 1 |
| 3 | Clause 3 | FAIL (memo 2 asked with the copy; Marta row shipped unasked) | PASS-vacuous | PASS | PASS (13 items) | PASS (12) | PASS (18) |
| 4 | Contract versions (with a recorded yes) | 5 (0 of 4) | 3 (2 of 2) | 2 (1 of 1) | 2 (1 of 1) | 2 (1 of 1) | 2 (1 of 1) |
| 5 | Final memos: decisions, actions, wrong dates, extra rows, Summary | 8/8, 15/15, 0, 0, 3/3 (assistant edits) | 2/8, 5/15, 1, 0, 1/3 | 8/8, 15/15, 0, 0, 3/3 | 8/8, 15/15, 0, 0, 2/3 | 5/8, 10/15, 0, 0, 1/3 | 5/8, 10/15, 0, 0, 1/3 |
| 6 | Runs per memo chain outside the window; turns; wall time | 18 / 7 / 9 = 34 (+5); 12; 77:55 | 14 / - / - (+5); 12; 41:53 | 16 / 10 / 15 = 41 (+5); 12; 55:46 | 10 / 5 / 10 = 25 (+5); 12; 24:15 | 14 / 10 / 5 = 29 (+5); 12; 25:59 | 13 / 10 / 5 = 28 (+5); 12; 31:08 |
| 7 | Delivered versions / rejected | 6 / 3 | 2 / 2 | 4 / 1 | 3 / 1 | 2 / 1 | 2 / 1 |
| 8 | Hand edits of deliverables | 5 | 0 | 0 | 0 | 0 | 0 |
| 9 | Skill | not activated | workspace copy | workspace copy | stratum A | A | A |
| 10 | Failed calls: assistant / org | 3 of 54 / 6 of 155 | 1 of 43 / 0 of 82 | 1 of 88 / 1 of 192 | 1 of 59 / 1 of 118 | 4 of 58 / 0 of 129 | 4 of 76 / 2 of 136 |
| 11 | Lead prompt bytes, first / peak / last | 21,266 / 35,694 / 32,329 | 20,353 / 27,556 / 27,310 | 20,341 / 29,061 / 24,395 | 20,424 / 28,488 / 25,674 | 20,633 / 28,686 / 25,974 | 20,727 / 31,539 / 29,313 |
| 12 | Assistant credits; org-run credits outside / window | 19.7788; 34.0395 / 6.6251 | 15.3392; 16.5622 / 5.6210 | 29.3140; 39.0075 / 5.3281 | 18.5058; 21.7556 / 5.0930 | 16.4039; 26.6442 / 4.7373 | 21.7869; 28.6043 / 4.7219 |
| 13 | Runs killed other than by the assistant's `stop` | 0 | 0 | 0 | 0 | 0 | 1 (F-E5-2) |

Against E4:
- **Better.** Clauses 1, 2 and 3 hold in every stream, where E4 failed each of them in at least one stream. No wrong or unsupported line entered a playbook, and no contract change lacked a recorded yes. No assistant hand-edited or amended before asking.
- **Worse.** No regression fails in all three streams instead of one; for E4's s2r the cause was a wrong date, for E5 the missing Summary and the missing memo 3.
- **Cost.** E5 used fewer org runs per stream than E4's s1r and s3, though every E5 seat ran the 1.30x model.
- **Model.** Whether the model change caused any of these differences cannot be separated from the product change, because the study is not model-matched.

## Evidence index
Start at `evidence/INDEX.md`. These are cited most:
- **Per stream:** `turn-NN.txt` (+ `.prompt`, `.cmd`), `session-turn-times-utc.txt`, `assistant-tool-calls.txt`, `assistant-session-messages.jsonl`, `contract-loop.txt`, `client-questions.txt`, `deliverables-log.txt`, `revise-playbook-attempts.txt`, `playbook/`, `service/`, `memos/` and `memos/versions/`, `msgs/` (`sent`, `read`, `lead-sent`, `lead-reviewer-sent`), `injection/`, `reflect-sections/`, `lead-prompt-sizes.txt`, `run-logs/`, `events/`, `scheduler.log`, `final-services-progress-status-health.txt`, `observe-check.txt`, `model-checks.txt`, `skill-check.txt`, `ambient-context.txt`, `cost.txt`, `org-kiro-sessions/`, `run-session-map.txt`.
- **Study level:** `protocol.md` (+ `.md5`), `freeze.txt`, `manager-decision-s3-sigterm.md`, `preflight.md`, `deterministic/at-6618c0d/`, `teardown.md`, `answer-key.md`.
- **For F-E5-2**, the product source at `6618c0d`: `src/hirearchy/daemon/_launch.py`, `src/hirearchy/processes/_spawn.py`, `src/hirearchy/scheduler/_loop.py`, `src/hirearchy/scheduler/_reaper.py`; and E4's `studies/E4-org-growth-0a1-recheck/evidence/s*/events/` for the comparison.
- **Sandboxes, read only:** `/tmp/hirearchy-e5-s1-1792811051`, `/tmp/hirearchy-e5-s2-1792812864` and `/tmp/hirearchy-e5-s3-1792814736`. The `deliverables/` md5s match `memos/`, `org/sent/` holds the injected text (md5s re-verified), and the s3 run log's mtime dates the kill.
