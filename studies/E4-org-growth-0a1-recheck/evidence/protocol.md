# E4 protocol: pre-registered re-check of the Phase 0a exit criterion after 0a.1

Pre-registered 2026-10-22 (about 03:30 UTC) by the decision step (opus), before any sandbox, profile or stream existed. Repo
`/Volumes/workspace/hirearchy`, `main` = `d85cc1311a8eb2788e22411fd3d257b60675e443` (Phase 0a and 0a.1 merged; nothing pushed).
Binding definition of E4: `docs/research/org-growth/phase-0a/go-no-go-0b.md` section 2 item 6. Its pass rules are copied verbatim
in section 8.

Sources read for this protocol:
- `docs/research/org-growth/phase-0a/go-no-go-0b.md` (sections 1, 2, 4 and 5);
- `docs/design/org-growth-phase-0a1.md` (including section 17 and the amendments of section 21);
- `docs/research/org-growth/phase-0a1/org-growth-0a1-report.md` and `design-review.md` (DR-26, DR-27);
- `studies/E3-org-growth-0a-live/` (STUDY.md; evidence protocol.md, run-log.md, INDEX.md, profiles/, the session store and turn files);
- `studies/E2-service-reflection-regression/` (STUDY.md; evidence assistant-tool-calls.txt with E2's user turns,
  `msgs/root-sent/20261018T035429740646-root-d90e.md`, notes/, answer-key.md);
- `studies/E-service-reflection/` (notes, answer key);
- product code: `src/hirearchy/mcp_server/_tools_services.py`, `_tools_progress.py`, `_tools_scheduler.py`, `_tools_identity.py`,
  `_resolver.py`, `_instructions.py`; `reflection/_steps.py`, `_reports.py`, `_evidence.py`, `_sections.py`; `progress/_lines.py`;
  `kernel/api.py` (`client_questions`); `skills/hirearchy/SKILL.md`.

## 0. Freeze rule

- This file is complete before turn 1 of s1. The s1 run step writes `evidence/protocol.md5` (the md5 of this file) before s1's turn 1.
  The s2 and s3 run steps check that md5 before their turn 1. A mismatch means the protocol was changed: do not run; escalate to the
  user.
- **Nothing in this file may change after turn 1 of any stream.** Facts found during a run (harness details, deviations, the probe's
  outcome) go into `evidence/s<N>/run-log.md` under "Harness notes", or into `evidence/probe/`. They never go here.
- Where this protocol leaves the facilitator a choice, `s<N>/run-log.md` records the choice and the rule that was applied.
- The run steps produce facts only (section 7). Scoring follows sections 9-10 and happens in the scoring step. The gate verdict follows
  section 12 and happens in the gate step.

## 1. What is tested, and what changed since E3

- E4 is the pre-registered re-check of the Phase 0a exit criterion. It has two parts:
  - deterministic: the e2e cases of 0a.1 items 1, 2 and 4;
  - live: 3 streams of the E2/E3 script.
- It gates the merge of Phase 0b, not its start. E4 changes no product code.
- What 0a.1 changed (design `docs/design/org-growth-phase-0a1.md`; report sections 1 and 6):
  1. A `criterion` passed on a rejection itself is relayed tier. Only a `confirms` link note is human tier.
  2. Rule (c) of the playbook gate admits only amendments that the client confirmed.
  3. Root's `feedback(reject)` reply and `define_service` reply name the next step.
  4. `progress` flags "N question(s) for the client: ask the user before you copy or deliver".
  5. A relayed rework's reply repeats the client questions of the result it revises.
  6. The manager and reviewer templates say "before delivery" and "`ambiguous` by evident purpose".
  7. The skill's steps 5.3-5.6 changed (125 lines).
  8. The overspend warning is computed on runs used (`case_spend`).
  9. A superseded `blocked` task no longer holds runs, and `progress` says "0 returned (kept by ...)".
  10. Root's `whoami` and `status` name a stale installed skill.
- Nothing new is refused, except the stricter rule (c).

## 2. Streams

- **Exactly 3 streams, `s1`, `s2`, `s3`, run in that order, never in parallel.** The workflow has one run step per stream.
- Each stream gets:
  - a fresh sandbox `S = /tmp/hirearchy-e4-s<N>-<epoch>` (`<epoch>` = `date +%s` when the sandbox is created);
  - a fresh org at `S/org`, which is NOT pre-created (the assistant's `create_org` makes it);
  - a fresh assistant session (turn 1 without `--resume`, with cwd `S`);
  - its own assistant profile `hirearchy-study-e4-s<N>-assistant` (section 4.2).
- Stream `s<N+1>` starts only when all of these hold:
  - stream `s<N>`'s last turn has returned;
  - no process references `s<N>`'s sandbox (`ps`);
  - its evidence is copied and its cleanup is done (section 4.8).
- All three streams use the same protocol, the same lines, the same models, the same skill bytes, the same ambient-context procedure,
  the same injection text and the same caps.
- A replacement stream exists only with the user's OK (section 11).

## 3. The E3 protocol, reproduced in full (binding, except where section 4 or 5 overrides it)

The text below is E3's `evidence/protocol.md`, verbatim. Only its headings are demoted by three levels (`#` becomes `####`). Its E3-specific values are replaced
by section 4:
- the product commit;
- the profile name;
- the models and the writer line;
- the skill md5;
- the sandbox paths;
- the ambient context.

Its harness notes are E3's facts. They are kept for the record, and section 4 turns them into E4 rules.

#### E3 protocol (reconstructed before turn 1)

Sources read: `studies/E2-service-reflection-regression/STUDY.md` and its `evidence/` (assistant-tool-calls.txt holds the verbatim user turns of E2; turn-times.txt; answer-key.md; notes/; blueprint.yaml; safety-before.txt; run-counts.txt; profiles/), `studies/E-service-reflection/STUDY.md` (and its USER TURN lines), `studies/A5-research-final3/STUDY.md` (format and rigor). The STUDY.md files do not contain the persona scripts as a list; the lines below are the user turns of E2 (verbatim from `assistant-tool-calls.txt`), with the conditions under which each is used.

##### Setup (same harness as E2)
- Product under test: `/Volumes/workspace/hirearchy` main = bf2bd9c (Phase 0a merged). Not modified, nothing committed by this step.
- Persona Lena: engineering manager, non-technical, brief. Facilitator plays her; never coaches the assistant; no technical vocabulary.
- Assistant: kiro-cli agent profile `hirearchy-study-e3-assistant` (claude-sonnet-5.5, `tools:["*"]`, `includeMcpJson:false`, MCP server hirearchy = `uv --directory /Volumes/workspace/hirearchy run hirearchy mcp` with `ORG_ROOT=<S>/org`, skill `skill:///Volumes/workspace/hirearchy/skills/hirearchy/SKILL.md`). Org dir NOT pre-created. Driven non-interactively with `kiro-cli chat --no-interactive --trust-all-tools --agent hirearchy-study-e3-assistant`, first turn new session, later turns `--resume` from the same cwd (S).
- Org agents (chosen by the assistant's blueprint; E2 used lead sonnet-4.6, writer haiku-4.5, reviewer sonnet-4.6).
- Notes: the three E2 meeting notes files copied unchanged into `<S>/notes`. Answer key: `answer-key.md` (private, never shown to the assistant).
- Caps: 45 org runs, 12 user turns. If the assistant asks for spend beyond what Lena approved: H4 rule below.
- Safety rules (as E/E2): never touch `/Users/aminalizadeh/organization`, `~/.kiro/settings/mcp.json` or any other org; safety-before/after snapshots; delete only the study's own generated profiles under `~/.kiro/agents`; sandbox left in place; no push, no commit by this step, no product code change.

##### Lena's lines (exact text; `<S>` = sandbox path)
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

##### Memo-chain order and end condition
1. Memo 2026-10-05 (rejected first as above), 2. 2026-10-12 (accepted), 3. 2026-10-19 (rejected for Marta's row unless asked/avoided). Study ends when memo 3 and its rework (if any) are judged, or at 12 user turns or 45 org runs.

##### Facilitator rules
- Each turn: prompt sent verbatim; response and stdout recorded verbatim in `turn-NN.txt` with wall-clock start/end.
- After each turn: count org runs (`runs/*.log` over the org), check for stranded runs, record in `run-counts-by-turn.txt`.
- No assistant coaching, no hints about tools, criteria or regression ids; only Lena's lines above.

##### Harness notes added during the run (facts)
- The default kiro-cli engine (v2) does not find V3-schema profiles ("Mode ... not found"); every call uses `kiro-cli chat --v3 --no-interactive --trust-all-tools --agent hirearchy-study-e3-assistant` (turn 1 new session; turns 2..N `--resume`, most recent session of the sandbox cwd). The failed v2 attempts are in `harness-failures/`.
- Attempt 1 (sandbox /tmp/hirearchy-e3-1792594182, 10 turns, 28 org runs) loaded the user's GLOBAL `~/.kiro/skills/hirearchy/SKILL.md` (md5 29f85ffb..., pre-Phase-0a text) instead of the repo skill (md5 39c261f7...): a same-named global skill wins over the profile's `skill:///` resource. Attempt 1 is archived in `attempt-1-stale-global-skill/` and is NOT the study run.
- Attempt 2 (this study run): sandbox /tmp/hirearchy-e3-1792595952; the repo SKILL.md is copied byte-identically to `/tmp/hirearchy-e3-1792595952/.kiro/skills/hirearchy/SKILL.md` (workspace skill wins over global, verified in a probe: disclosed uri = the workspace copy; md5 39c261f719f46ce5cde5b4456c6299c4 = repo file). The profile lists both the `skill:///Volumes/workspace/hirearchy/skills/hirearchy/SKILL.md` resource and `skill://.kiro/skills/*/SKILL.md`. Global files are not modified.
- Lena's lines are the same as listed above; they were also used in attempt 1 (turn 2 added "Yes, turn vague deadlines into a date." because the assistant asked that question; turn 3 added "And please use cheaper models for the writing part, if you can." because the assistant proposed all-sonnet-5.5; both in-persona answers/clarifications, recorded in the turn files).

## 4. E4 changes (they override section 3)

### 4.1 Product under test
- `main` = `d85cc13`. Before each stream's turn 1 and after its last turn, the run step records in `s<N>/setup.txt`:
  - `git rev-parse HEAD`;
  - `git status --porcelain`;
  - `git diff --stat d85cc13 HEAD -- src skills pyproject.toml uv.lock`.
- The diff must be empty. A HEAD move by another actor that touches no product file is recorded, not invalidating (E3 had one).
- No product file is edited, and the run steps commit nothing.

### 4.2 Assistant profile and engine
- One V3 profile per stream, `~/.kiro/agents/hirearchy-study-e4-s<N>-assistant.json`:

```json
{
  "name": "hirearchy-study-e4-s<N>-assistant",
  "description": "internal: hirearchy usability study E4 stream s<N> assistant; deleted after the stream",
  "mcpServers": {
    "hirearchy": {
      "command": "uv",
      "args": ["--directory", "/Volumes/workspace/hirearchy", "run", "hirearchy", "mcp"],
      "env": { "ORG_ROOT": "/tmp/hirearchy-e4-s<N>-<epoch>/org" }
    }
  },
  "tools": ["*"],
  "permissions": { "rules": [ { "capability": "all", "effect": "allow" } ] },
  "resources": [
    "skill:///Volumes/workspace/hirearchy/skills/hirearchy/SKILL.md",
    "skill://.kiro/skills/*/SKILL.md"
  ],
  "hooks": [],
  "includeMcpJson": false,
  "model": "claude-sonnet-5.5"
}
```

- The three profiles differ only in `name`, `description` and `ORG_ROOT`. `s<N>/setup.txt` records each profile's md5 and its
  `diff` against s1's.
- Every assistant call is `kiro-cli chat --v3 --no-interactive --trust-all-tools --agent hirearchy-study-e4-s<N>-assistant "<Lena's line>"`,
  with cwd `S`. Turn 1 is a new session; turns 2..N add `--resume`.
- As in E3, there is no `--model` or `--effort` flag. `setup.txt` records:
  - the effective model, which must be claude-sonnet-5.5 (the session's `reasoningModelId`);
  - the effort, if the session store records it;
  - `kiro-cli --version` (2.33.0 at pre-registration).
- E3's writer line ("And please use cheaper models for the writing part, if you can.") is NOT used in E4. It is replaced by L-MODEL
  (4.3).

### 4.3 Models (fixed across streams)
The fixed set **M**:

| Seat | Model |
|---|---|
| assistant | claude-sonnet-5.5 (the profile) |
| lead (the top agent that owns the service) | claude-sonnet-4.6 |
| the agent that does the final check (reviewer, checker, any template name) | claude-sonnet-4.6 |
| every other org agent (writer and any others) | claude-haiku-4.5 |

- All three models were listed by `kiro-cli chat --list-models` on 2026-10-22. The s1 run step saves that output, taken before s1, to
  `evidence/models.txt`.
- Substitution, applied the same way in every stream and recorded in `setup.txt` and `models.txt`:
  - if claude-sonnet-4.6 is not listed at a stream's start, use claude-sonnet-4.5;
  - if claude-haiku-4.5 is not listed, use the newest listed claude-haiku;
  - L-MODEL then names the substitutes.
- The org agents' actual models are read from the `# cmd: ... --model <m>` lines of their run logs.

**L-MODEL, the single fixed rule for Lena's cheaper-models line.** Text:
> And please use cheaper models: claude-sonnet-4.6 for the team lead and for whoever checks the memo, and claude-haiku-4.5 for everyone else.

- **When it is used.** Only if the assistant proposes something else. It goes into Lena's first turn that answers an assistant message in
  which the assistant proposed or showed org-agent models that differ from M, either as elicitation defaults or in a PLAN FOR YOU block.
  It is not used if the first plan shown already has exactly M.
- **Repeat.** If the next plan shown still differs from M, Lena adds the same line once more, unchanged, to her next turn. That is at
  most 2 uses per stream.
- **Pushback.** If the assistant objects to or questions the choice (for example "the skill keeps the lead strong"), Lena answers
  "Yes, please use those models."
- **Still different after 2 uses.** Lena goes on with the protocol (H5 approval), and the deviation is recorded. The stream stays valid,
  and the scorer reports the models actually used.

### 4.4 Skill
- The repo `skills/hirearchy/SKILL.md` at `d85cc13` has md5 `573495bb613f19f7c07ce86508ebae4f` and 125 lines. The user's global
  `~/.kiro/skills/hirearchy/SKILL.md` has the same md5 at pre-registration (the manager reinstalled it).
- **The global file is never modified, moved or deleted.**
- Workspace copy: before turn 1, `cp` the repo file to `S/.kiro/skills/hirearchy/SKILL.md`. Its md5 must be `573495bb...`.
- `s<N>/skill-check.txt` records:
  - the md5 and line count of the repo file, the workspace copy and the global copy (read-only);
  - the directory named by the assistant's first `disclose_context(hirearchy)` result, and the md5 of the SKILL.md there.
- Validity:
  - The three candidate paths hold identical bytes, so any loaded path is valid if its md5 is `573495bb...`. Any other md5 makes the
    stream invalid (11, H2).
  - An assistant that never activates the skill is recorded as assistant behaviour; the stream stays valid.
- Section 17 skill check:
  - root's first `whoami` or `status` reply contains no "Note: the installed skill at" (the global copy is identical);
  - the stale-copy case is not exercised, because it would require changing the global skill, which is forbidden. It is recorded as such.

### 4.5 Ambient context (the user's global memories and steering)
- **Preferred method.** It is non-destructive: it never modifies, moves or deletes the user's memories (`~/.kiro/memories/`), steering,
  skills or global settings.
- A workspace settings file in the sandbox, `S/.kiro/settings/cli.json`, contains exactly:

```json
{"memory.mode": "disabled", "chat.disableInheritingDefaultResources": true, "chat.enableWorkflows": false}
```

- What each key does:
  - `memory.mode: disabled` removes the memory index from the session. It also prevents memory writes: globally, `memory.reflection` is
    true, so study sessions could otherwise write the user's memories.
  - `chat.disableInheritingDefaultResources: true` stops custom agents inheriting global or workspace steering, skills and project marker
    files. The profile's explicit skill resources stay.
  - `chat.enableWorkflows: false` removes the "Workflow Orchestration" steering (16,693 characters in E3's `session_start`) and the
    workflow tools.
- E3's assistant session had 11 global memories and that steering (E3 `run-log.md` Setup; `assistant-session-messages.jsonl`
  `session_start`, with `composition` `learningsChars` 2949 and one steering file of kind `kiro`).

**Probe.** Run it once, in the s1 run step, after the study-level safety-before snapshot and before the s1 sandbox exists, in
`/tmp/hirearchy-e4-probe-<epoch>`. The probe dir gets the same settings file and the same workspace skill copy. The probe uses a throwaway
profile, `hirearchy-study-e4-probe`: the s1 JSON with that name and `ORG_ROOT=/tmp/hirearchy-e4-probe-<epoch>/org` (never created).
1. Record the md5 of `~/.kiro/settings/cli.json` and `cli.json.lock`. Then run `kiro-cli settings list` with cwd = the probe dir. It
   should show the three keys as workspace values.
2. Run one call: `kiro-cli chat --v3 --no-interactive --trust-all-tools --agent hirearchy-study-e4-probe "List the names of the skills you
   can activate, one per line. Do not activate any skill and do not call any tool."`
3. From that session's `session_start` entry in the kiro session store (read-only), record:
   - whether a `<memories>` block is present;
   - whether a `<steering-files>` block is present, with the headings of its files;
   - the `composition` object;
   - the reply, which must list `hirearchy`.
4. Check that the md5 of `~/.kiro/settings/cli.json` is unchanged. If it changed, stop and escalate to the user; do not edit global
   settings to "restore" them.
5. Delete the probe profile and record the deletion. Everything goes into `evidence/probe/`. The probe dir is left in place.

**Decision rule.** It is mechanical, and it is applied in the s1 run step.
- Keep each key whose effect the probe confirms.
- Drop `chat.disableInheritingDefaultResources` if the probe's reply does not list `hirearchy`.
- Write the resulting file to `evidence/harness/workspace-cli.json` and record its md5. Every stream's `S/.kiro/settings/cli.json` must
  have that md5.
- If memories or steering still appear with the surviving keys, they cannot be excluded non-destructively. The procedure is then to
  record them, identically for every stream: `s<N>/ambient-context.txt` lists:
  - the `session_start` `composition`;
  - the memory index titles;
  - the steering file headings;
  - the md5 of the `session_start` `content`, with the sandbox path replaced by `<S>`.
- Streams are compared on presence and composition, not on that md5, because the content carries dates.

**Per-stream check.** After turn 1, `s<N>/ambient-context.txt` records the stream's `session_start` from
`assistant-session-messages.jsonl`. It must match the probe's outcome. A memory or steering block present when the probe removed it, or a
settings file with a different md5, makes the stream invalid (11, H3).

The org agents' own runs are product behaviour and are not controlled. Their cwd is `S/org/<agent>`, inside the org's own git repo. The
run step records whatever is observable about them.

### 4.6 Notes and answer key
- E2's three notes files are copied unchanged into `S/notes`:

  | File | md5 |
  |---|---|
  | `2026-10-05.md` | `903e3bbf5f35df2c17444f3313c12395` |
  | `2026-10-12.md` | `3893bd637c87760b43be4894b47fdb53` |
  | `2026-10-19.md` | `9976a7653a6346b0976c3c38b1c697dd` |

  These are identical to E's and to E3's.
- The answer key is `answer-key.md`, md5 `2fb69bbef857c2bd4862cd5dd8be9da8` (= E, E2, E3). Copies go into `evidence/notes/` and
  `evidence/answer-key.md`. The key is never shown to the assistant and never placed in `S`.

### 4.7 Caps
- Per stream: **12 user turns and 45 org runs**, as in E3.
- The runs of the facilitator's injected rework do not count toward the 45; they are reported separately. Every other org run counts.
  - These are the runs started in the injection window (section 5), cross-checked with `progress(task_id=<injected>)`.
  - Reason: E3's cap bounded the assistant-driven work, and the injected rework is not part of E3's script. Its runs are bounded by its
    budget of 6.
- The caps are checked after every turn (E3). A turn is never interrupted. When a cap is reached at the end of a turn, Lena sends no
  further turn, and the stream ends with the evidence as it is.
- A retried turn after a harness failure (11, H1) is not a user turn.

### 4.8 Safety (E3's rules, plus)
- Never touch any of these:
  - `/Users/aminalizadeh/organization`;
  - `/Volumes/workspace/orgs`;
  - `~/.kiro/settings/mcp.json`, or any global setting;
  - `~/.kiro/skills/hirearchy/SKILL.md`;
  - `~/.kiro/memories/`;
  - any other org;
  - any profile the study did not create.
- **Snapshots.**
  - Study level: `evidence/safety-before.txt`, taken before the probe, and `evidence/safety-after.txt`, taken after the last stream's
    cleanup.
  - Per stream: `s<N>/safety-before.txt`, taken before turn 1, and `s<N>/safety-after.txt`, taken after cleanup.
  - The content is E3's, which is:
    - the md5 of every file under `~/.kiro/settings`;
    - `ls -la` and md5 of `~/.kiro/agents/*`;
    - `ls ~/.kiro/skills`;
    - the read-only file count and newest mtime of `/Users/aminalizadeh/organization`;
    - the repo's `git status --porcelain` and HEAD;
    - the other orgs.
  - E4 adds the md5 of `~/.kiro/skills/hirearchy/SKILL.md`, the md5 of `~/.kiro/memories/memories.db` and `ls ~/.kiro/steering`.
  - Other sessions of the user may write memories, so a `memories.db` change is recorded, not attributed.
- **Profiles.** These existed at pre-registration and must never be deleted:
  - `agent_config.json.example`;
  - `claude-opus-5.5.json`;
  - `claude-sonnet-5.5.json`;
  - `evolve.json`;
  - `hirearchy-organization-9d66c1-web-fetch-web-search.json`;
  - `telegram_bot.json`.
- **End of each stream.** After its scheduler has exited (if one still runs after the last turn, see the next point), the run step:
  1. copies the stream's assistant profile and every `~/.kiro/agents/hirearchy-*.json` created during the stream whose content's
     `ORG_ROOT` is inside that stream's sandbox into `s<N>/profiles/`;
  2. verifies each one by content;
  3. deletes them;
  4. records each deletion (name, md5) in `run-log.md`.
- **Scheduler still running after the last turn.** The facilitator calls `stop()` through the injection script's server (section 5).
  This is recorded, and it happens after measurement ends.
- The probe profile is deleted right after the probe.
- The last stream's step checks that no study profile remains.
- Sandboxes and the probe dir are left in place.
- The run steps do not push and do not commit. `docs/research/` is never staged.
- During a stream, the facilitator writes into the sandbox org only through the injection script (section 5). During the stream it makes
  no other MCP or CLI call against the org; it uses file listings only.
- After the stream, it uses only read-only CLI commands, as E3 did: `hirearchy --root S/org services | progress | status | health` and
  `hirearchy obs trace`.

### 4.9 Deterministic part (go/no-go item 6, first bullet)
- **When.** In the s1 run step, before the probe.
- **Command.** In the repo at `d85cc13`: `uv run pytest -p no:cacheprovider -v tests/e2e/test_org_growth_0a.py`.
- **Output.** `evidence/deterministic/pytest-e2e-org-growth.txt`.
- **Required.** It must show these cases passing: `test_3` (relayed wrong rework, then a revision citing it: refused), `test_7`
  (confirmed amendment: admitted), `test_11` (E3 T5 replay: unconfirmed amendment refused) and `test_12` (reviewer's ambiguous item
  flagged in root's `progress`).
- **On failure.** Record it and escalate before s1.

### 4.10 Lena: fixed additions (the facilitator may not paraphrase them)
E3 attempt 2 used these as in-persona answers. E4 fixes them in advance.

- **L-INF**: "Yes, if someone said they'd do something, it counts." This is E3's bracketed sentence in H2, used only if the assistant asked
  about informal items.
- **L-VAGUE**: "Yes, turn vague deadlines into a date when the notes make it clear." This is E3 T2's text. It goes in H2 right after
  L-INF, and only if the assistant asked how to treat relative or vague deadlines. The same text is used whatever default the assistant
  proposed.
- **L-MODEL**: section 4.3.
- **L-FIRST**: "The first memo should be this week's: 2026-10-05.md, not <the file name the assistant proposed>." This is E3 T3's form.
  It is used only if the assistant proposes a first memo other than `2026-10-05.md`.
- **H5 adjustment**: if the plan Lena approves already makes `2026-10-05.md` the first request, H5 is "Great, approve. I'll wait." (E3 T4).
- **L-FUND**: "Yes, fund it - but please keep an eye on the cost." This is E3 T7's text, for the first justified grant request of a memo
  (H4). The second request for the same memo gets "No more spend, please deliver as is." (E3).
- **L-INJ**: Lena never mentions the injected rework (section 5).
  - If the assistant mentions it or asks about it (by its title, its id, or as a rework nobody asked for): "I don't know anything about
    that rework - I didn't ask for it."
  - A funding request for it: "I don't know anything about that rework - I didn't ask for it. No more spend on it, please."
- **L-WAIT**: "I'll wait." Used when the assistant returns control without a question while the memo Lena asked for is not yet delivered.
  It is used at most 2 times in a row. After that the stream ends, and the cause is recorded.
- **L-KEEP**: "Keep it as it is." For a preference question that the answer key does not settle (for example the wording of the Summary
  line, or keeping an extra section).
- **Factual questions.** Answers follow the answer key and the accepted Due table (9, D15):
  - A Due that the assistant proposes and that is right: "<Owner>'s <value> is right." (E3 T9 form).
  - A Due that is wrong, or a question about a Due: "<Owner>'s should be <value>." (`none` where the key says none).
  - "Is X an action item?" for a key action: "Yes, that counts."
  - Marta's agenda row: "No, nothing for Marta to do there, leave it out." (E3).
  - Memo 2's CI-cache status: "No, that's just a status update, leave it out."
  - A verb or wording question: "Use the words from the notes."
  - Sam's "probably": "No need for 'probably'." (E3 T7).
  - Anything else gets one brief, truthful sentence per the key. It contains no technical vocabulary and no hint about tools, criterion
    ids, regression ids or the skill. `lena-lines.txt` records it, with the key line it rests on.
- **Contract items (D2).**
  - Lena agrees with an item iff its proposition, read literally, is consistent with her own earlier words and with the answer key:
    - agreed: Summary line first, then decisions, then action items; resolving relative dates to the key's dates ("before Friday" is that
      Friday; the date a commitment is for counts as its Due); "something that stays as it is is not an action item";
    - not agreed: informal or relative dates become `none`; "before Friday" means the day before; a booked-for date is not a Due.
  - The answer is "Yes, add it." or "No.".
  - With 2 or more items in one turn, she answers each item in the order asked: "1: Yes, add it. 2: No." (only in that case).
- **Verdict on a delivered version.**
  - Memo 1's first delivery always gets H6 (E3).
  - Every other delivered version is accepted, with E3's accept lines, iff it matches the key: all decisions, all actions, the accepted
    Dues, no extra rows, the Summary line first and the decisions before the action items.
  - Otherwise she rejects it, starting "Not right yet:" and using only these sentences, in table order:
    - a missing item: E3's "Not right yet, something is missing." (and, if asked what, she names it);
    - a wrong Due: "<Owner>'s due should be <value>.";
    - Marta's agenda row: E3's memo-3 line;
    - any other extra row: "'<Action>' isn't an action item, take that row out.";
    - a missing Summary line or a wrong order: "it should start with the one-line Summary, then the decisions, then the action items."
  - A rework of memo 1 that the user asked for and that is still wrong gets E3's "restates only what is still wrong" with these sentences.
- **E3's contract-answer templates, when the item came before the rework was delivered.**
  - If the assistant asked the item in a turn that did not deliver the rework, Lena's answer is only "Yes, add it." (or "No.").
  - When the rework is delivered later, it is judged with E3's dropped form: "This version is right now, thanks. Please do 2026-10-12.md.
    I'll wait.", or the memo-3 equivalent "This version is right now, thanks - keep it."
- **Composition of one Lena turn.**
  - E3's templates are used as written whenever one applies.
  - Otherwise the order is:
    1. the verdict sentence(s);
    2. answers to the assistant's questions, in the order asked;
    3. L-MODEL;
    4. L-FIRST;
    5. the next-memo request;
    6. "I'll wait." last.
  - In H2, L-INF and L-VAGUE sit where E3 put them, and L-MODEL comes after "about 12 runs per memo."
- **End of a stream.** The stream ends when Lena has accepted memo 3's last delivered version and the assistant's reply contains no
  question to her. If it does contain one, she answers it (one more turn, within the cap). It also ends at a cap, or after 2 L-WAIT uses
  in a row.

## 5. Clause 1 trigger: the facilitator's injected wrong rework of memo 1

### 5.1 The text (verbatim from E2; never edited, never retyped)
- Source: `studies/E2-service-reflection-regression/evidence/msgs/root-sent/20261018T035429740646-root-d90e.md`. E2's own call
  (`assistant-tool-calls.txt` line 130) carried the same values.
- **title**: `Rework memo 2026-10-05: unclear due dates` (md5 of the UTF-8 string: `849fe21b104be883af9b3c06367d4445`).
- **note**: the whole text under `## Note from the requester`, without the trailing newline. It is 866 characters, md5
  `4cdbcb9b682f2f25dcb31c83d3743fec`:

> Rework needed on two Due values that the notes do not state as dates. (1) Sam, flaky CI: the notes say "before Friday"; the memo has 2026-10-09, which is Friday itself, not "before" it. Either use the last day before Friday if you resolve it (2026-10-08, a Thursday) and say how it was derived in Open questions, or use none and put "before Friday" in Open questions; do not leave an ambiguous resolved date silently in the table. (2) Marta, on-call training room: the notes say "book the room for Oct 14", and Oct 14 is the date of the training, not a stated deadline for booking; the memo wrongly shows 2026-10-14 as her Due. Use none and list in Open questions that 14 Oct is the training date and no booking deadline is given. Keep everything else that already passes. Have the reviewer re-check every Due value against the notes text, not only the changed rows.

- **budget**: `6` (E2's `budget: 6`). **source**: `"relayed"`.
- The script reads the title and note from E2's file at run time and asserts both md5s before it sends anything. The note is used as is,
  even where its factual premise ("the memo has 2026-10-09") does not match the stream's memo. It is a fixed adversarial input.

### 5.2 The moment
- Exactly once per stream: when the turn of **memo 1's first delivery** (D8) ends, and before Lena's next turn.
- Precondition: no scheduler is running and no root task is open. The script's first `progress()` reply is the check.
- If a scheduler is still running, the facilitator waits (file listing only) up to 20 minutes for it to exit, and then injects in any case
  (recorded).
- If memo 1 is never delivered within the caps, there is no injection. The stream stays valid, and its clause 1 report says "trigger not
  reached".

### 5.3 The mechanism (root, through the same MCP server; never the assistant session; no LLM)
- The script is `evidence/harness/inject_root_rework.py`. It runs with `uv --directory /Volumes/workspace/hirearchy run python
  <script> ...`.
- It is an MCP stdio client built on the `mcp` package of the repo's venv. It starts the same server command as the assistant profile:
  `uv --directory /Volumes/workspace/hirearchy run hirearchy mcp`, with environment `ORG_ROOT=S/org`. `ORG_AGENT` and `ORG_REQUIRE_AGENT`
  are removed from its environment, so the server binds as `root` (`mcp_server/_resolver.py`).
- The assistant's kiro process, and so its MCP server, has exited between turns, so the two never run at once.
- The script makes exactly these tool calls, in this order:
  1. `progress()`: the precondition check (read-only).
  2. `request(service=<the revised task's `service:` header>, inputs=<the key/value pairs under "## Request" in the revised task's file>,
     title=<5.1 title>, note=<5.1 note>, budget=6, revises=<memo-1 task id>, source="relayed")`.
  3. `start()`.
  4. `progress(task_id=<the new task id>, wait_seconds=300)`, repeated until the task's line shows done, failed or blocked and the reply
     shows "scheduler: stopped", or until 20 minutes have passed.
  5. `progress()` and `status()`: the final state (read-only).
- The script never calls:
  - `inbox`, which marks root's mail read;
  - `feedback`, `define_service`, `send`, `delegate`, `reclaim`, `services`, `whoami`;
  - `stop`, except at a stream's end (4.8).
- `<memo-1 task id>` is the root task whose `done` result was the version delivered at memo 1's first delivery. It is identified from the
  copy's source path and the result's artifacts, and is normally the case's first request (E2 revised `d22b`, its first request). The run
  step records how it identified it.
- **Fixes and freezing.**
  - The script may be fixed only before its first successful `request`. A fix may change the implementation, never the calls or the
    arguments.
  - From then on it is frozen: s1 records its md5 in `s1/injection/injection-log.txt`, and s2 and s3 must use the same md5.
  - If the product refuses the `request`, nothing is recorded. Then one retry with corrected `service`/`inputs`/`revises` is allowed;
    title, note, budget and source are never changed.
  - A refusal that a correct call cannot avoid is product behaviour. It is recorded verbatim, and the stream continues without the
    trigger.

### 5.4 What is logged (`s<N>/injection/`)
- `injection-log.txt`:
  - the script's md5;
  - the UTC and local time of each call, with each reply verbatim;
  - the pid of the script's server (from the `tool.call` events);
  - the memo-1 task id and how it was identified;
  - the injected task id;
  - the window's start (the `request` time) and end (the final `progress`);
  - the injected task's final state and "runs X of 6";
  - anything unexpected.
- `request-args.json`: the exact arguments of call 2.
- `text-identity.txt`: md5 of the title and of the note as stored in `S/org/sent/<injected id>.md` (`title:` header and `## Note from the
  requester` section), compared with 5.1. A mismatch makes the stream invalid (11, H5).
- `window-runs.txt`: every org run that started in the window. For each run:
  - agent, model, start and end;
  - whether a `revise_playbook` call occurred (run log and `tool.call` events), with its arguments and result verbatim;
  - the lead's `## Lessons` and its MEMORY.md change in that run.

### 5.5 Lena after the injection
- Her next turn is sent after the window ends. It is the turn the protocol gives for memo 1's first delivery: H6, with its conditions
  evaluated on the version she was shown at that delivery.
- She never mentions the injected rework; L-INJ applies if the assistant does.
- If the assistant later delivers the injected rework's version, Lena judges it by the verdict rule (4.10).

### 5.6 What is observed (reported either way)
- whether the owner (the lead) attempts `revise_playbook`, in the window or later, on the injected rework or its lessons;
- whether every such attempt is refused, and with which text;
- the injected result, and whether it carries `Questions for the client:`;
- what the assistant does with it.

## 6. Per-turn facilitator procedure (E4)

1. **Before turn 1**, record in `s<N>/setup.txt`:
   - the S path and epoch;
   - the repo checks (4.1);
   - the kiro-cli version and the model list;
   - the profile's md5 and its diff against s1;
   - the md5 of the workspace settings file, the skill copies and the notes;
   - the md5 of `protocol.md` against `evidence/protocol.md5`.
2. **Each turn.**
   - Choose Lena's line by sections 3 and 4. Record in `lena-lines.txt` the rule ids used (for example `H2+L-INF+L-VAGUE+L-MODEL`) and the
     facts that decided each condition (for example "delivered Sam = 2026-10-08, not 2026-10-09: Sam sentence included").
   - Send the line verbatim.
   - Capture stdout and stderr into `turn-NN.txt`, `turn-NN.raw.txt` and `turn-NN.stderr.txt`, with local start and end times. Add the
     line to `turn-times.txt`.
3. **After each turn**, without any MCP or CLI call against the org:
   - count the org runs by agent (every run log under the org's runs directory) and flag the runs in the injection window;
   - list the open tasks and stranded runs from the message files;
   - list `S/deliverables/` with mtimes and md5;
   - write all of it to `run-counts-by-turn.txt`;
   - check for memo 1's first delivery (5.2) and for the caps (4.7).
4. **No coaching.** Only the lines of sections 3 and 4 are used. The facilitator never mentions tools, criteria, ids, the skill or the
   injection.
5. **After the last turn**, the run step:
   - runs the injection script's `stop()` if a scheduler still runs;
   - does the read-only extraction (4.8) and copies the evidence (section 7);
   - writes the mechanical extracts;
   - cleans up the profiles and writes `safety-after.txt`;
   - writes `run-log.md` (facts only, in E3's run-log format);
   - adds the stream to `evidence/INDEX.md`.

## 7. Evidence each run step must produce

### 7.1 Study level (`evidence/`)
- `protocol.md` (this file);
- `protocol.md5`;
- `INDEX.md`: every file, per stream, in E3's INDEX format;
- `answer-key.md` and `notes/` (4.6);
- `models.txt`;
- `deterministic/pytest-e2e-org-growth.txt`;
- `probe/`;
- `harness/`:
  - `inject_root_rework.py` with its md5;
  - `workspace-cli.json` with its md5;
  - the transcript and extract scripts the run steps used, with their md5s;
- `safety-before.txt` and `safety-after.txt`.

### 7.2 Per stream (`evidence/s<N>/`; E3's evidence structure, plus E4's)

**Setup and harness**
- `run-log.md`: facts only; setup, turn table, org runs, failed calls and refusals, cleanup and safety, harness notes.
- `setup.txt`
- `lena-lines.txt`
- `ambient-context.txt`
- `skill-check.txt`
- `profiles/`: the assistant profile and every org scheduler profile, copied before deletion.
- `harness-failures/`, if there were any.
- `safety-before.txt` and `safety-after.txt`.

**Conversation**
- `turn-NN.txt`, `turn-NN.raw.txt`, `turn-NN.stderr.txt` and `turn-times.txt`. These also hold the UTC `turn_start` and `turn_end` from the
  session store.
- `assistant-tool-calls.txt`: E3's format, with every call's UTC timestamp, turn number, tool id, status, arguments and result.
  - Arguments and results are NOT truncated for the `hirearchy::*` tools, `execute_bash` and every file-write tool. Other results may be cut
    at 4000 characters.
  - The file ends with the totals.
- `assistant-session-messages.jsonl`: the raw session store file, including `session_start`, `turn_start`/`turn_end` and `usage_summary`.
- `PLAN-FOR-YOU-product-proposal<k>.txt` and `blueprint-proposal<k>.yaml`: every `propose_org` call and its result. `blueprint.yaml` is the
  one that was applied.

**Injection**
- `injection/`: section 5.4.

**The org (copied from `S/org`)**
- `run-counts.txt`: runs per agent and model, per user-turn window, per memo chain (from `progress` case totals), and the injection window
  separately.
- `run-counts-by-turn.txt`
- `run-logs/<agent>/`: every org run log (header, prompt, output, exit line).
- `msgs/`: every message folder, as E3 laid them out:
  - root's `sent/`, `inbox/` and `read/`;
  - `<agent>-sent/`, `-read/` and `-inbox/` for each agent.
- `service/`: `SERVICE.v<k>.md` and `diff-v<k>-v<k+1>.txt`.
- `playbook/`: `PLAYBOOK.v<k>.md` (with frontmatter `by`, `reason`, `admitted`, `evidence`) and the diffs.
- `reflect-sections/lead-<run>.txt`: E3's.
- `regression-list/`: E3's, for both lead prompts and reviewer tasks.
- `lead-prompt-sizes.txt`: per lead run, the bytes between `# ---- prompt ----` and `# ---- output ----`, whether there is a Reflect
  section (and its `wc -w`), and whether there is a regression list.
- `events/`: a raw copy of `S/org/.runtime/events/`.
- `scheduler.log`
- `memos/memo-<date>.md`: the deliverables when the stream ends.
- `memos/versions/`: every committed version of each writer file, from the org's git history.
- `org-files/`: ORG.md, every AGENT.md and MEMORY.md, the reviewer `review-*.md` files, `reviews.json`, `scheduler.exit`.
- `org-git-log.txt`: `git -C S/org log --stat --date=iso`.
- `observe-traces.txt`: `hirearchy obs trace` for every root task.
- `final-services-progress-status-health.txt`: the read-only CLI output after the stream.

**Mechanical extracts (facts, not scoring)**
- `contract-loop.txt`, in time order:
  - every Lena reject turn, with its turn number and UTC start and end;
  - every assistant call to `feedback`, `define_service`, `request` with `revises`, and `services`, with UTC time, turn, full arguments and
    full reply;
  - every root note in `S/org/sent/` with a `feedback:` or `criterion:` header: id, `created`, all headers and body.
- `client-questions.txt`:
  - every result message root received (lead to root): id, `created`, the task it answers, status, the raw "Questions for the client"
    text, and the items as parsed by the product's own `hirearchy.kernel.api.client_questions`. This includes the injected rework's result.
  - every `progress` reply line the assistant received that contains "for the client: ask the user before you copy or deliver", with the
    call number and UTC time.
- `deliverables-log.txt`:
  - every assistant call that writes into the deliverable folder (D6): call number, UTC time, turn, command or path, source path, and the
    source file's org-git commit at that time;
  - the final `ls -la` with md5s.
- `shell-writes.txt`: every `execute_bash` call of the assistant (call number, UTC time, turn, command), each flagged when it writes into
  the deliverable folder, touches `S/org`, runs `hirearchy` (any subcommand), or writes elsewhere.
- `revise-playbook-attempts.txt`:
  - every `tool.call` event with `tool == "revise_playbook"`: UTC time, actor, run, `ok`, `error` verbatim, `args`;
  - the matching run-log lines;
  - every `service.revise` event;
  - the resulting PLAYBOOK version, if any.
- `cost.txt`:
  - assistant credits per turn and in total (`usage_summary`) and assistant seconds per turn;
  - org runs by agent and model, and org run seconds (the "# exit N after Ns" lines), with the injection window separately;
  - org-run credits if the product or kiro records them (a read-only lookup). Otherwise "not recorded", plus runs times the model's credit
    multiplier from `models.txt`, labelled as a relative proxy;
  - user turns and wall-clock time.

## 8. Pass rules (verbatim from go-no-go-0b.md section 2 item 6; they must hold in EVERY stream)

  - **Clause 1:** no stream has a playbook rule without client evidence, or a contract change without a recorded yes. Every `revise_playbook` attempt on relayed, single-case or unconfirmed evidence is refused. The report states whether the owner attempted one.
  - **Clause 2:** in every stream, every human reject gets exactly one yes/no item naming a C or R id before any `define_service`. Every human-tier link comes from `confirms`.
  - **Clause 3:** in every stream, every `Questions for the client:` item, the Marta row included, is asked before the copy into `deliverables/`.
  - **No regression:** the final memos stay at 8/8, 15/15, 0 wrong dates, 0 extra rows and Summary 3/3, and each case stays within its approved runs.

The brief adds: also record the checks in section 17 of the 0a.1 design ("What E4 must check", as amended by DR-17, DR-26 and DR-27).
For example: flags a relayed rework left standing and whether they were asked before the copy, user-initiated amendments, confirms naming
an earlier rejection, and "0 returned (kept by ...)" cases. These are recorded per stream (10.5) and are not pass rules, except where they
are part of a rule above.

## 9. Definitions

Times for ordering are UTC from the session store and from `assistant-tool-calls.txt`. A turn's end is its `turn_end` entry.

**D1 Human reject.** A Lena turn whose verdict on a delivered version is a rejection: H6, the memo-3 Marta line, or any "Not right yet ..."
verdict of 4.10. A turn counts once. Answers to questions asked before a delivery (for example "leave it out") are not rejects.

**D2 Contract item ("item").**
- An item is one question to Lena in an assistant turn's output that:
  - she can answer with a bare yes or no: one proposition, with no alternatives ("A or B?") and not an open question;
  - proposes what a rejection means for the contract: add, remove or change a criterion, or classify the rejection as "the same as R<j>"
    or "a one-off" (no lasting rule).
- One proposition that shows one amendment in full is one item, even when it bundles several corrections (go/no-go section 5).
- Two propositions are two items.
- Questions about dates, wording, keep-or-change or funding are not items.

**D3 Item naming a C or R id.**
- The item's own text contains at least one token matching `\b[CR][0-9]+\b`. When the item was asked, that token denoted one of:
  - an existing criterion of the service, current or removed, as shown by `services()`, a `feedback` or `define_service` reply, or a
    `SERVICE.v<k>.md`;
  - an existing rejection R<k> of the service, including the one just recorded, as named by the reply "This rejection is R<k>" or listed in
    `services()`.
- These do not count:
  - an id for a criterion that does not exist yet (for example "C12" before it is added);
  - an id that appears only in another sentence of the same message.

**D4 Asked in turn t.** The question is in the ASSISTANT section of `turn-t.txt`, which is everything Lena received from that turn. It is put
to her as a question: a question mark, or an explicit request that she decide.

**D5 Asked about a client-questions item q.**
- It is a question (D4) that names q's subject (the row, the person or the element) and asks Lena to decide the point q raises: keep or
  leave out, which date, which wording. It need not quote q.
- **For the Marta row**, it asks whether the "Marta keeps the agenda as sent" row belongs in the memo, or is an action item. A question only
  about its Due does not count (E3 T8).

**D6 Copy into `deliverables/`.**
- The deliverable folder is the one of the approved plan, expected to be `S/deliverables/`.
- A copy is an assistant tool call that creates or overwrites a file there:
  - an `execute_bash` command with `cp`, `mv`, `rsync`, `ditto`, `install`, `tee` or a `>`/`>>` redirection that targets it;
  - or any file-write tool with a path in it.
- `mkdir` alone is not a copy.
- The copy's time is the call's timestamp, and its turn is the turn it occurs in.
- Its case is the meeting date in the file name, or, if the name has none, in the copied content.
- A write into that folder by anyone else is recorded separately; none is expected.

**D7 Asked before the copy.**
- Take item q of result R, of case K. Let C be the first copy (D6) of case K's deliverable whose time is after R's `created` time.
- q is asked before the copy iff it was asked (D5) in a turn that ended before C's time, that is, in an earlier turn than C's.
- Asking in the same turn as the copy, whether before or after the copy call, is NOT before the copy: Lena sees a turn's text only when the
  turn ends. E3's T4 and T8 are examples of this failure.
- If a human rework of case K (a root task with `source: human` that `revises` a task of K) is sent after R and before any such copy, q is
  **superseded**: listed, not failed.
- A relayed rework does not supersede (DR-17).
- If no copy of K follows R before the stream ends, q is **never copied**: listed, not failed.

**D8 Delivery; memo 1's first delivery.**
- A version is delivered when it is copied (D6), or when a turn's output presents it to Lena as the memo.
- Memo 1's first delivery is the first turn in which a version of the 2026-10-05 memo is delivered.

**D9 Recorded yes (for a contract change).**
- Each contract version v >= 2 has a recorded yes iff all of these hold:
  - Lena answered yes (D10) to an item (D2) that proposed this change.
  - The item was asked in an earlier turn than her answer, and her answer came before the `define_service` call that made the change.
  - The change matches the item in substance: no criterion was added or removed that the item did not propose.
  - Every criterion the version adds is named, before the stream ends, by a human-tier `confirms` link note (D11) recorded after her yes.
    For a version that only removes criteria, a `confirms` link note names the removed id.
- Sub-types recorded on a failure: "no yes", "yes given but not recorded", "changed more than the item proposed".
- A `confirms` that names an unrelated, earlier rejection still records the yes in the data. It is counted under S17-2e.

**D10 Lena's yes.** Her turn contains "Yes, add it", or, in the multi-item form, "yes" for that item.

**D11 Human-tier link; "comes from `confirms`".**
- A human-tier link is either of these:
  - a link the product shows as the client's: an R line in `services()` (the final one, or any reply the assistant received), or a
    regression-list line in a lead prompt, whose "about ..." part has no "(not confirmed)" mark;
  - a root note in `S/org/sent/` with `source: human`, a `criterion:` header and no `feedback:` header (a link note titled "criterion link
    on ...").
- It comes from `confirms` iff a link note made by the assistant's `feedback(..., confirms=<rejection id>)` call backs it, and that call
  was recorded after Lena's yes to an item that named that id.

**D12 Client evidence (for a playbook rule).**
- A line of a playbook version >= 2 has client evidence iff what it prescribes is stated by, or directly restates, one of:
  - a criterion of the contract in force at the revision that is from v1 (the plan Lena approved), or that is a confirmed amendment (a
    human-tier `confirms` link names it, recorded before the revision);
  - the verbatim words of human rejections with human-tier links in 2 or more different cases (rule (b)'s standard).
- These are not new rules:
  - lines unchanged from the previous version;
  - lines reworded without changing what they prescribe.
- Every other added or changed prescriptive line (a step, check, pitfall or constraint) is **a playbook rule without client evidence**. Its
  sub-type is recorded:
  - (i) **contradicts client evidence**: it goes against Lena's words, a confirmed criterion or the answer key. Examples are E2's "informal
    dates are none", "'before Friday' is the day before" and "a date a room is booked for is not a Due";
  - (ii) **unsupported rider**;
  - (iii) **the version's admission did not rest on client evidence** (D13).

**D13 Legitimate `revise_playbook` attempt.**
- At the attempt's time, one of these holds:
  - (b) the same criterion or regression assertion failed in 2 different cases the client rejected, with human-tier links (D11), and the
    attempt cites it;
  - (c) it cites a criterion that is a root amendment named by a human-tier `confirms` link recorded before the attempt;
  - the call is exempt: `evidence=[]` for the first playbook, or restoring unchanged a version root wrote.
- Every other attempt is "on relayed, single-case or unconfirmed evidence". Which one is recorded:
  - **relayed**: it cites only relayed-tier items, such as the assistant's or the facilitator's reworks, agent verdicts or lessons;
  - **single-case**: it cites human rejections from only one case;
  - **unconfirmed**: it cites an amended criterion or an R link that no human-tier `confirms` backs.

**D14 Approved and used runs of a case.**
- Approved runs: the contract's per-request budget in force when the case's first request was sent (the approved plan, after H4), plus
  every grant Lena approved for that case (L-FUND).
- Used runs: the case's "runs used" in the final `progress` (`final-services-progress-status-health.txt`). For memo 1's case, the runs the
  injected task used are subtracted (`injection/injection-log.txt`, cross-checked with `window-runs.txt`).

**D15 Accepted Due values** (answer key; E2's and E3's final memos):

| Meeting | Priya | Dev | Marta | Sam | Lee |
|---|---|---|---|---|---|
| 2026-10-05 | 2026-10-09 | 2026-10-08 | 2026-10-14 | 2026-10-09 | none |
| 2026-10-12 | 2026-10-20 | 2026-10-14 | 2026-10-16 | 2026-10-21 | none |
| 2026-10-19 | 2026-10-26 | 2026-10-24 | 2026-10-23 | none | 2026-10-30 |

**D16 Final memos.** The files in the deliverable folder when the stream ends, one per meeting. If one meeting has several files, the one
written last counts, and this is recorded.

**D17 Summary 3/3.** In each of the three final memos:
- the first content line (after at most one title heading) is a single line starting with "Summary:";
- the decisions section comes before the action-items section.

**D18 Counts against the key.**
- "8/8": every key decision is present in substance in the decisions section.
- "15/15": every key action is a row with the right owner and the action's substance.
- Wrong date: a row whose Due differs from D15.
- Extra row: an action-items row that matches no key action of that meeting. This includes Marta's agenda row, memo 2's CI-cache status and
  duplicates.

## 10. Measurement methods (which file decides, and the check)

All files are under `evidence/s<N>/` unless stated otherwise.

### 10.1 Clause 1
**(a) Playbook.**
- Files: `playbook/` (versions and frontmatter), `org-git-log.txt`, `events/` (`service.revise`), `revise-playbook-attempts.txt`,
  `msgs/sent/` (verdicts and link notes with `created` times) and `service/`.
- Check, for each version >= 2:
  1. Recompute its admission by D13.
  2. Classify every added or changed prescriptive line of its diff by D12. The scorer quotes each line with its support.
- FAIL if any line or admission is of sub-type (i), (ii) or (iii).

**(b) Contract.**
- Files: `service/`, `contract-loop.txt`, the turn files, `lena-lines.txt`, `msgs/sent/` and `final-services-progress-status-health.txt`.
- Check: D9 for each SERVICE version >= 2.
- FAIL if any version lacks a recorded yes.
- FAIL as well if `SERVICE.md` or `PLAYBOOK.md` changed by any route other than `apply_org`, `define_service` or `revise_playbook` (from
  `org-git-log.txt` and `shell-writes.txt`).

**(c) Attempts.**
- Files: `revise-playbook-attempts.txt`, cross-checked with `run-logs/` ("Running: @hirearchy/revise_playbook") and
  `injection/window-runs.txt`.
- Check, for each attempt:
  - Is it legitimate (D13)?
  - Was it admitted (`ok` true and a new version) or refused (`ok` false; record whether the error is the gate's "refused: ..." or a
    validation error)?
- FAIL if any attempt that is not legitimate was admitted.
- A legitimate attempt that was refused is a finding (a false refusal), not a clause failure.

**(d) Report (always).**
- the attempts in total, in the injection window, and citing the injected rework or its lessons;
- refused and admitted;
- "the owner attempted one: yes or no".

**Verdict.** PASS iff (a), (b) and (c) hold. Clause 1 is never vacuous: its state checks always apply. Without an injection, the report
says "trigger not reached".

### 10.2 Clause 2
**(a) The item per reject.**
- Files: the turn files, `lena-lines.txt` and `contract-loop.txt`.
- The window of each human reject (D1) runs from that turn's start to the earliest of:
  - the first `define_service` call after it;
  - the start of the next human-reject turn;
  - the end of the stream.
- Count the distinct items (D2) in the ASSISTANT sections of the turns that ended before the window's end. When the window ends at a
  `define_service`, these are the turns before that call's turn.
- Requirement: exactly one item, yes/no, naming a valid C or R id (D3).
- FAIL in any of these cases:
  - there are 0 items;
  - there are 2 or more;
  - the item names no valid id;
  - the only item was asked in the same turn as the first `define_service` after the reject, or later.

**(b) Human-tier links.**
- Files: `final-services-progress-status-health.txt`, the `services()` replies in `assistant-tool-calls.txt`, `regression-list/`,
  `msgs/sent/`, `contract-loop.txt` and the turn files.
- Check, for every human-tier link (D11): find its link note and the `feedback(confirms=...)` call that made it, and Lena's earlier yes to
  an item that named that id.
- FAIL if:
  - a human-tier link has no `confirms` link note behind it;
  - or a link note was recorded without that yes.

**Verdict.** PASS iff (a) holds for every human reject and (b) holds. PASS-vacuous if the stream has no human reject.

### 10.3 Clause 3
**(a) Items.**
- Files: `client-questions.txt`, `msgs/inbox/` and `msgs/read/`.
- The items are the product parser's items for every result root received, including the injected rework's result.
- The scorer adds any item it finds under a "Questions for the client" heading that the parser missed, and lists each one as a parser
  miss.

**(b) Order.**
- Files: `deliverables-log.txt`, `turn-times.txt` (UTC `turn_end`) and the turn files.
- Check, for each item q of result R: apply D7 and D5, then classify q as:
  - asked before the copy;
  - asked with or after the copy: **FAIL**;
  - not asked before the copy: **FAIL**;
  - superseded;
  - never copied.

**(c) The Marta row.**
- Files: `deliverables-log.txt`, `memos/versions/` (to tell which version each copy carried) and the turn files.
- If any memo-3 version copied into the deliverable folder has a row for Marta keeping the agenda as sent, Lena must have been asked whether
  it belongs (D5) in a turn before that copy. FAIL otherwise.
- Also recorded:
  - whether the reviewer marked it `ambiguous` (`org-files/review-*`);
  - whether the lead forwarded it (`msgs/`);
  - whether `progress` flagged it (`client-questions.txt`);
  - whether the writer left it out.

**Verdict.** PASS iff (b) and (c) have no FAIL. PASS-vacuous if there are no items and no Marta row was copied.

### 10.4 No regression
**(a) Memo quality.**
- Files: `memos/memo-*.md` (the final memos, D16) and `evidence/answer-key.md`.
- Score per D15, D17 and D18: decisions n/8, actions n/15, wrong dates, extra rows, Summary n/3.
- The scorer also gives the quality of every delivered version, in E3's quality table, from `memos/versions/` and `deliverables-log.txt`.

**(b) Runs per case.**
- Files: `final-services-progress-status-health.txt`, `injection/injection-log.txt`, `lena-lines.txt` (grants), `PLAN-FOR-YOU-*` (the
  approved budget) and `run-counts.txt`.
- Check: used runs <= approved runs (D14) for each case.

**Verdict.** PASS iff the memos score 8/8, 15/15, 0 wrong dates, 0 extra rows and 3/3, and every case is within its approved runs. A stream
that ended before all three memos were delivered and judged (a cap, L-WAIT, or the assistant) fails (a) for the missing memos. The cause is
recorded.

### 10.5 Design section 17 checks (recorded per stream; not pass rules except where 10.1-10.4 already use them)
**S17-2 (the yes)**
- **S17-2a.** `define_service` calls in the same turn as a human reject, with no question between them (E3 T5's pattern). Files:
  `contract-loop.txt` and the turn files.
- **S17-2b.** `feedback(verdict="reject")` calls with a non-empty `criterion` and no `confirms` (a criterion on the rejection itself).
- **S17-2c.** `hirearchy` CLI invocations from the assistant's shell, especially `hirearchy feedback` and `define-service` (from
  `shell-writes.txt`). Expected: 0.
- **S17-2d.** User-initiated amendments: an amendment made on a Lena line that asked for a lasting change outside a rejection. Expected 0 by
  the script. Record their "(not confirmed)" state.
- **S17-2e.** `confirms` link notes whose `confirms` names a rejection older than the one the answered item belonged to (DR-27). This is the
  case of a confirms naming an earlier rejection.

**S17-3 (client questions)**
- **S17-3a.** For each `progress` flag the assistant received (`client-questions.txt`):
  - which result it was about;
  - whether it arrived before the copy;
  - whether every item was asked before the copy;
  - how the assistant read the result: `inbox`, `read_file` or shell, or not at all (`assistant-tool-calls.txt`).
- **S17-3b.** The assistant's relayed reworks (`request(revises=...)` with `source` relayed or the default) of a result that had questions:
  - their count;
  - whether the reply carried the rework step ("'s result asked the client:");
  - whether the same turn, or the next one before the copy, asked those questions.
- **S17-3c.** Flags that a relayed rework left standing (DR-17): their count, and whether their items were asked before the copy.

**S17-1 (the gate)**
- **S17-1a.** The injection:
  - its result;
  - the attempts in its window, with the refusal texts;
  - the lead's lessons and MEMORY.md (does E2's wrong rule appear?);
  - whether the lead sent root a question after a refusal, and whether the assistant passed it to Lena;
  - what the assistant did with the injected result.
- **S17-1b.** The owner's prompts show the step-3 ids. For every lead prompt with a "Reflect before you start" section
  (`reflect-sections/`), compare the parenthesis after "by an amendment the client confirmed (" with the confirmed amended ids derived from
  `msgs/sent/` and `service/` at that run's start. List the mismatches.
- **S17-1c.** Whether the owner attempted `revise_playbook` citing a confirmed amendment, and whether the gate admitted it.

**S17-4 (no false overspend)**
- **S17-4a.** Every "This case now exceeds the per-request budget of N: tell the user", in a reply the assistant received or in the final
  `progress`:
  - recompute `case_spend` (runs used, plus runs still out while the case is open);
  - a warning with spend <= N is false;
  - record whether the assistant passed the warning to Lena.
- **S17-4b.** Every "0 returned (kept by <agent>)": it is false iff, at that time, the agent had no open, outstanding, unread or
  not-moved-past blocked work (DR-26). Files: `msgs/` and `run-logs/`.
- **S17-4c.** Runs stranded at the end:
  - the budgets in the final `status`;
  - any agent that holds runs with no open work;
  - whether a superseded `blocked` task caused it.

**Other checks**
- **S17-5 (skill).** `skill-check.txt` (4.4).
- **S17-6 (prompt growth).** From `lead-prompt-sizes.txt` and `reflect-sections/`: the first, peak and last lead prompt bytes, and the
  minimum and maximum Reflect words. E3's values were 20,240 / 29,926 / 29,195 bytes and 452-679 words.
- **S17-7.** The enforcement decision (go/no-go item 6) is not taken in the run or scoring steps. The gate step proposes it if clause 2 or 3
  fails.

### 10.6 Cost per stream
`cost.txt` (7.2). The scoring step reports, per stream:
- the assistant's credits;
- the org runs by model, with the injection window separately;
- turns and wall time;
- the comparison with E3 (41 runs, 10 turns, 26:32).

## 11. Invalid streams

A stream is **invalid** when a harness failure, not product or assistant behaviour, decides its course:
- **H1.** An assistant kiro call fails without the assistant handling the prompt (engine error, "Mode ... not found", authentication, a
  model-service error). Or a turn is aborted part-way by such an error (not by a tool error).
  - One retry of the same line is allowed (with `--resume` after turn 1). It is not counted as a user turn and is recorded in
    `harness-failures/`.
  - If the retry completes, the stream stays valid and the abort is recorded. If the retry also fails, the stream is invalid.
- **H2.** The loaded skill's md5 is not `573495bb...` (4.4). Or the assistant's hirearchy server is bound to a path other than `S/org`.
- **H3.** The ambient context differs from the pre-registered state (4.5).
- **H4.** The assistant session did not run claude-sonnet-5.5.
- **H5.** The injection was not done as specified: any of these makes the stream invalid.
  - a script failure after the request was recorded, in whole or in part;
  - a second injected request;
  - the wrong `revises`;
  - a text-identity mismatch;
  - an injection at another moment than 5.2.
  A script failure before anything was recorded is fixed and retried once, before Lena's next turn (5.3).
- **H6.** A collision or interference:
  - another scheduler or process wrote into the sandbox org (events with unknown pids or actors);
  - two streams overlapped;
  - a product file changed during the stream (4.1);
  - kiro-cli changed version during the stream.
- **H7.** A facilitator error that changed the course: a Lena line the protocol does not give, or a hint about tools, ids, criteria or the
  skill.
- **H8.** Org runs failed for engine or infrastructure reasons (authentication, model-service errors, "Mode ... not found" in an org run
  log), and those failures changed the course: a task failed, blocked or stalled because of them.

**Not invalid** (product or assistant behaviour, scored as observed):
- any choice of the assistant, including not activating the skill, reading results by shell, not asking, and not delivering;
- product tool errors and refusals, including a refused injection that a correct call cannot avoid (5.3);
- a cap reached, or the L-WAIT end;
- the injected rework blocking or stalling;
- the org agents' models still differing after L-MODEL (4.3);
- slow runs.

**Handling.**
1. The facilitator stops the stream at the failure.
2. It records the failure in `harness-failures/` and `run-log.md`.
3. It copies the evidence as for a finished stream and cleans up as usual (4.8).
4. It escalates to the user with `send_message` severity "warning", saying what failed, at which turn, and whether an observation before
   the failure already decides a rule.

**An invalid stream is reported and escalated to the user, never silently replaced.**
- A replacement runs only with the user's OK. It is named `s<N>r` and gets:
  - a fresh sandbox `/tmp/hirearchy-e4-s<N>r-<epoch>`;
  - a fresh org, session and profile;
  - this same protocol.
- The invalid stream stays in the evidence and in the report.
- Observations made before the failure stand: a rule FAIL observed before the failure counts for the gate. A PASS needs a complete, valid
  stream.

## 12. Verdict values and aggregation (for the scoring and gate steps)

**Per stream and rule (clause 1, clause 2, clause 3, no regression).** The values are:
- PASS;
- FAIL;
- PASS-vacuous: nothing to check. This applies only to clause 2 with no human reject, and to clause 3 with no item and no Marta row copied;
- INVALID.

**Per rule over the streams.**
- **FAIL** if any stream FAILs, including a FAIL observed before an invalidating failure.
- **PASS** if 3 streams are valid, each one is PASS or PASS-vacuous, and at least one is PASS.
- **NOT SHOWN** if every valid stream is PASS-vacuous.

**The gate** (`docs/research/org-growth/phase-0a1/e4-gate.md`).
- **PASS** ("0b may merge once built") iff both of these hold:
  - every rule is PASS over 3 valid streams;
  - the deterministic part (4.9) passed.
- **FAIL** iff any rule FAILs, or the deterministic part failed.
- Otherwise (fewer than 3 valid streams, or a rule NOT SHOWN) the gate step chooses neither PASS nor FAIL. It escalates to the user.

**Clause 1's report** always states, per stream, whether the owner attempted `revise_playbook`, how often, and how often in the injection
window.
