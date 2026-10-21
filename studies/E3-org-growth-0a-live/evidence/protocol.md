# E3 protocol (reconstructed before turn 1)

Sources read: `studies/E2-service-reflection-regression/STUDY.md` and its `evidence/` (assistant-tool-calls.txt holds the verbatim user turns of E2; turn-times.txt; answer-key.md; notes/; blueprint.yaml; safety-before.txt; run-counts.txt; profiles/), `studies/E-service-reflection/STUDY.md` (and its USER TURN lines), `studies/A5-research-final3/STUDY.md` (format and rigor). The STUDY.md files do not contain the persona scripts as a list; the lines below are the user turns of E2 (verbatim from `assistant-tool-calls.txt`), with the conditions under which each is used.

## Setup (same harness as E2)
- Product under test: `/Volumes/workspace/hirearchy` main = bf2bd9c (Phase 0a merged). Not modified, nothing committed by this step.
- Persona Lena: engineering manager, non-technical, brief. Facilitator plays her; never coaches the assistant; no technical vocabulary.
- Assistant: kiro-cli agent profile `hirearchy-study-e3-assistant` (claude-sonnet-5.5, `tools:["*"]`, `includeMcpJson:false`, MCP server hirearchy = `uv --directory /Volumes/workspace/hirearchy run hirearchy mcp` with `ORG_ROOT=<S>/org`, skill `skill:///Volumes/workspace/hirearchy/skills/hirearchy/SKILL.md`). Org dir NOT pre-created. Driven non-interactively with `kiro-cli chat --no-interactive --trust-all-tools --agent hirearchy-study-e3-assistant`, first turn new session, later turns `--resume` from the same cwd (S).
- Org agents (chosen by the assistant's blueprint; E2 used lead sonnet-4.6, writer haiku-4.5, reviewer sonnet-4.6).
- Notes: the three E2 meeting notes files copied unchanged into `<S>/notes`. Answer key: `answer-key.md` (private, never shown to the assistant).
- Caps: 45 org runs, 12 user turns. If the assistant asks for spend beyond what Lena approved: H4 rule below.
- Safety rules (as E/E2): never touch `/Users/aminalizadeh/organization`, `~/.kiro/settings/mcp.json` or any other org; safety-before/after snapshots; delete only the study's own generated profiles under `~/.kiro/agents`; sandbox left in place; no push, no commit by this step, no product code change.

## Lena's lines (exact text; `<S>` = sandbox path)
H1 opening (turn 1, always):
> Hi! After each of our weekly team meetings I want a short memo from my notes: what we decided and who does what. My notes are in <S>/notes (one file per meeting). Can you set up a team that does this for me every week?

H2/H3/H4/H5 answer to the elicitation (turn 2). The sentence in [ ] is included ONLY if the assistant asked about informal / unlabelled commitments (E2: "Informal commitments" question). Informal items count only if the assistant asks; if it does not ask, the sentence is omitted and Lena never brings it up.
> Thanks! [Yes, if someone said they'd do something, it counts.] The file name each time is fine. Format: a markdown memo, at most 400 words, with the action items as a table with columns Owner | Action | Due (ISO dates, 'none' if there's no date). The rest of your defaults are fine, the deliverables folder too. Please keep it cheap, but I need it right - about 12 runs per memo.
(If the assistant did not give defaults, "The rest of your defaults are fine" is dropped; if it asks a question not covered, Lena answers briefly and truthfully per the answer key: relative dates such as "before Friday" -> a date, 2026-10-09; "for the 14th" -> 2026-10-14; Marta's agenda "kept as sent" is not an action item; a stated number of runs is H4.)

H4 budget rule: "about 12 runs per memo". If the assistant explains that 12 is too tight and proposes a raise to at most 16, Lena accepts once:
> OK, if it's needed to get it right, raise it to 15 for each memo.
(If it proposes a different number <= 16, "OK, if it's needed to get it right, raise it to N for each memo." If > 16: "No, that's too much - 16 at most.") Spend beyond the approved per-memo budget (rework grants): ask Lena -> she says yes once for a justified request, with "keep an eye on the cost"; a second request for the same memo is declined ("No more spend, please deliver as is").

H5/approval (turn 3 or the turn in which the plan is shown and the assistant asks for approval):
> Great, approve. Please do this week's: 2026-10-05.md. I'll wait.

H6 (reject the first delivered memo whatever its quality, plus the lasting requirement; never restated afterwards):
> No, not right yet. [Date corrections ONLY if the delivered memo has Sam's row due other than 2026-10-09 and/or Marta's row due other than 2026-10-14: "Sam's CI item says 'before Friday', so that has a date, 2026-10-09, not 'none'." / "And Marta's room is for the training on the 14th, so I want 2026-10-14 there."] And always start the memo with a one-line 'Summary:' of the meeting, then the decisions, then the action items.
(If the delivered memo already has no date errors, Lena's reject carries only the Summary requirement: "No, not right yet. Always start the memo with a one-line 'Summary:' of the meeting, then the decisions, then the action items.") The reject goes to the first memo as delivered; if the assistant delivers the first memo more than once before Lena has answered, her reject applies to the version she is shown.

Answer to "make the rules permanent?" / a contract-question (D3 yes/no):
> Yes, add it - and this version is right now, thanks. Once that's added, please do 2026-10-12.md. I'll wait.
(Used in the turn after the rework of memo 1 is delivered. If the assistant has not yet asked a contract question, the sentence "Yes, add it - and" is dropped: "This version is right now, thanks. Please do 2026-10-12.md. I'll wait." If the rework is still wrong, Lena restates only what is still wrong, briefly.) A yes/no contract question about a criterion Lena agrees with is answered "Yes, add it."; one she does not agree with "No."

Memo 2 accept (turn after memo 2 is delivered; the quick-check contents are right):
> That one is right, all the items are there - keep it. Now 2026-10-19.md please. I'll wait.
(If a decision or action item from the answer key is missing, Lena says only "Not right yet, something is missing." and, if asked what, names the omitted item from the key. Informal items are not volunteered otherwise.)

Memo 3 reject (the Marta row; used only if memo 3 is delivered with a row for "Marta keeps the agenda as sent"; if the assistant asks Lena BEFORE delivery whether that counts as an action item she answers "No, nothing for Marta to do there, leave it out." and does not reject afterwards):
> Almost, but not right yet: 'Marta keeps the agenda as sent' isn't an action item, nobody has to do anything there. Take that row out. The rest is fine.
(If memo 3 is delivered without that row and otherwise matches the key, Lena accepts it without the reject, and the fact is recorded.)

Final accept after the rework / contract question:
> Yes, add it. And this version is right now, thanks - keep it.
(If no contract question is pending: "This version is right now, thanks - keep it.")

Status turns: Lena never sends "status?"; when the assistant says it is waiting she says nothing until it replies (the facilitator only sends a turn when the assistant has returned control). If the assistant returns control with a question, Lena answers it using the rules above. If it returns with a plan or progress and no question, Lena says "Ok." only if the assistant asked "Shall I continue?"; otherwise the session ends when all three memos are delivered and judged.

## Memo-chain order and end condition
1. Memo 2026-10-05 (rejected first as above), 2. 2026-10-12 (accepted), 3. 2026-10-19 (rejected for Marta's row unless asked/avoided). Study ends when memo 3 and its rework (if any) are judged, or at 12 user turns or 45 org runs.

## Facilitator rules
- Each turn: prompt sent verbatim; response and stdout recorded verbatim in `turn-NN.txt` with wall-clock start/end.
- After each turn: count org runs (`runs/*.log` over the org), check for stranded runs, record in `run-counts-by-turn.txt`.
- No assistant coaching, no hints about tools, criteria or regression ids; only Lena's lines above.

## Harness notes added during the run (facts)
- The default kiro-cli engine (v2) does not find V3-schema profiles ("Mode ... not found"); every call uses `kiro-cli chat --v3 --no-interactive --trust-all-tools --agent hirearchy-study-e3-assistant` (turn 1 new session; turns 2..N `--resume`, most recent session of the sandbox cwd). The failed v2 attempts are in `harness-failures/`.
- Attempt 1 (sandbox /tmp/hirearchy-e3-1792594182, 10 turns, 28 org runs) loaded the user's GLOBAL `~/.kiro/skills/hirearchy/SKILL.md` (md5 29f85ffb..., pre-Phase-0a text) instead of the repo skill (md5 39c261f7...): a same-named global skill wins over the profile's `skill:///` resource. Attempt 1 is archived in `attempt-1-stale-global-skill/` and is NOT the study run.
- Attempt 2 (this study run): sandbox /tmp/hirearchy-e3-1792595952; the repo SKILL.md is copied byte-identically to `/tmp/hirearchy-e3-1792595952/.kiro/skills/hirearchy/SKILL.md` (workspace skill wins over global, verified in a probe: disclosed uri = the workspace copy; md5 39c261f719f46ce5cde5b4456c6299c4 = repo file). The profile lists both the `skill:///Volumes/workspace/hirearchy/skills/hirearchy/SKILL.md` resource and `skill://.kiro/skills/*/SKILL.md`. Global files are not modified.
- Lena's lines are the same as listed above; they were also used in attempt 1 (turn 2 added "Yes, turn vague deadlines into a date." because the assistant asked that question; turn 3 added "And please use cheaper models for the writing part, if you can." because the assistant proposed all-sonnet-5.5; both in-persona answers/clarifications, recorded in the turn files).
