# G0 protocol: the noise baseline of Phase 0b (pre-registered)

Pre-registered on 2026-10-26 (UTC) by the pre-registration step (step 1 of 11) of workflow `wf_c415acfac4f09f84`, before any G0 sandbox,
profile, dedicated kiro home, session or stream existed. The freeze time, HEAD and the freeze diff are in `freeze.txt`.
- **Product under test.** Repo `/Volumes/workspace/hirearchy`, branch `main` = `3c841bb9cdde666c6ea8b00bb2edfeae68c256db` (short `3c841bb9`):
  Phase 0a through 0a.5, plus 0b (the quality view, `hirearchy quality --json`, the replays of design 19). Nothing is pushed. No worktree.
- **What G0 is** (design 20.1). G0 runs E7's committed script many times on the merged product and measures how much the results vary, so a
  later study can tell a change from noise. **It has no pass rule: it reports values and their spread.** Its report, with 0b's deterministic
  replays (design 19, checked by section 21's deterministic part), closes Phase 0b (exit criterion: "Noise baseline measured; alarms checked on
  replayed E/E2/A5 files").
- **Approval.** The owner approved the cost on 2026-10-25 ("I agree with both decision.", D-E7-6 in
  `docs/research/org-growth/phase-0a4/e7-decision.md`): about 230 org runs and about 355 credits, 6 streams, k = 3 per arm, every seat on
  claude-sonnet-5.5 at effort high. A design that needs materially more goes back to the manager first.
- **Terms.** "Design n" is section n of `docs/design/org-growth-phase-0b.md` (sections 20 and 21 bind this protocol). "E7" is study
  `studies/E7-org-growth-0a4-recheck/`; "E7 protocol" is its `evidence/protocol.md` and "E7 n" its section n (pinned in section 2); "E7
  STUDY" is its `STUDY.md`. "The brief" is `docs/research/org-growth/phase-0b/g0-brief.md`. "`EV`" is
  `/Volumes/workspace/hirearchy/studies/G0-noise-baseline/evidence`, "`H`" is `EV/harness`, a "label" is a stream's name (`m0-s1` ...), and
  "`<label>/`" is `EV/<label>/`. Every path in this document is absolute or relative to `EV`.

Sources read in full for this protocol: the brief; design 20 and 21, with 3-9, 19 (the E7 block of 19.3 and 19.5) and 26 for what the
re-derivation and the self-check need; E7's `STUDY.md` and `evidence/` (`protocol.md`, `harness/` with its `MD5SUMS`, `CHANGES.md`, the answer
key, `notes/`, `preflight.md`, `teardown.md`, the streams `s1`-`s3` for procedure facts and as the self-check's raw input);
`docs/research/org-growth/phase-0a4/e7-gate.md` (section 2, section 4 with F-E7-11, section 5 item 11) and `e7-decision.md`; E5's protocol
(`studies/E5-org-growth-0a2-recheck/evidence/protocol.md`, md5 `afd437c103407ec5899e4993b465cf25`) 4.4, 4.5, 4.11 and D21; E4's
amendment 1 (`studies/E4-org-growth-0a1-recheck/evidence/protocol-amendment-1.md`, md5 `1ec9e658e3bd59ab9d9f785986a26c19`) A3; and, read-only,
the product texts this protocol pins (section 3.3).

## 0. Freeze rule

- **This file is frozen at pre-registration.** `protocol.md5` holds its `md5 -q`; `harness/MD5SUMS` holds every harness file's md5;
  `freeze.txt` holds the UTC freeze time, `git rev-parse HEAD`, the empty freeze diff, the md5 of `harness/MD5SUMS`, the md5s of section 2's
  copies, the self-check outcome, and the state at freeze (no G0 sandbox, profile, dedicated kiro home or stream). Nobody edits these files
  afterwards.
- **The md5 gate.** Every later step checks `md5 -q EV/protocol.md` against `protocol.md5`, and every line of `harness/MD5SUMS`
  (`cd EV/harness; while read h f; do [ "$(md5 -q "$f")" = "$h" ] || echo "MISMATCH $f"; done < MD5SUMS` prints nothing), before it acts:
  the preflight, every stream step before its first turn and after its last, the teardown, the aggregation and the commit. On a mismatch the
  step does nothing else and sends `send_message` severity `warning`.
- **Amendments** follow E7 0 unchanged: a separate `protocol-amendment-N.md` with its `.md5`, written only after the manager's approval is
  recorded in `EV/manager-decision-<topic>.md`, frozen before the next stream's first turn. After the first stream's first turn, an amendment
  may change only harness or infrastructure items (commands, paths, evidence sources, search patterns) for streams not yet started.
- **Nothing that defines a measure changes after the first stream's first turn**: Lena's lines (section 4), the injection (E7 5), the
  readings of section 3, the definitions and methods (sections 9-10 of the pinned E7 protocol as section 2 adopts them, and section 12 here),
  the validity rules (section 8) and the aggregation (section 13).
- Facts found during a run go into `<label>/run-log.md` ("Harness notes") or `preflight.md`, never here. The stream steps produce facts only;
  the aggregation step scores and aggregates by sections 12 and 13.

## 1. Design and place in the sequence (design 20.1)

- **Sequence** (D-E5-7, D-E6-8, D-E7-1, D-E7-7): 0a.3, 0a.4 and 0a.5 merged; 0b built on them, reviewed and validated; 0b merged to `main`
  (`3c841bb9`); G0 starts after the merge with the owner's OK on its cost. G0's report closes Phase 0b.
- **Arms (controlled): memory presence.** **M0**: the assistant runs with a dedicated kiro home prepared by the setup, whose kiro settings are
  copies without the memories index (section 6). **M1**: the owner's ambient kiro memories as they are, recorded by md5 and index listing (E5
  4.5's method, `ambient_context.py`). The owner's real `~/.kiro` is never modified (its md5 set before and after, section 9).
- **Stratifier (observed): skill activation**, E7 4.4.1's strata A, B, N, n/a. Activation is never forced.
- **Repeats.** k = 3 valid streams per arm, 6 streams (Q3). k = 3 gives a range, not a rate. The streams are interleaved
  **`m0-s1`, `m1-s1`, `m0-s2`, `m1-s2`, `m0-s3`, `m1-s3`**, one at a time, never in parallel, so time of day and service load do not line up
  with an arm. `run_arm.sh <arm> <k>` names the arm's next streams (one more than the arm's highest stream number), so streams can be added
  to an arm later by the owner's decision. Every cell of arm x skill stratum with fewer than 3 streams reports its values and `n/a (k of 3)`
  for its spread.
- **No other workflow runs during G0's streams** (the manager guarantees it). A model-service usage-limit or quota error stops the step with a
  `warning`; no step continues on a degraded service, and nothing is retried in a loop.

## 2. The script pin and the copies (design 20.1 "Script pin")

**E7's protocol is pinned, not rewritten.** `studies/E7-org-growth-0a4-recheck/evidence/protocol.md`: 2 609 lines, 260 399 bytes, md5
**`0acc2b4191b8cbfa5f4bb6197b877de1`** (= E7's `protocol.md5` and `freeze.txt`). A byte-identical copy is `EV/script/e7-protocol.md` (same
md5), so this folder holds every text G0 runs on. **Adopted** from it, as written, with section 2.1's substitutions and only the changes this
protocol states: E7 3 (E3's Lena lines, reproduced in full), 4.2 and 4.2.1 (engine, profile, the tool-call boundary), 4.3 (models, M5, no
substitution, L-SONNET), 4.4 and 4.4.1 (skill, strata), 4.5 and 4.5.1 (ambient context, per-turn snapshots), 4.6 (notes, the private answer
key, AMB-1 and AMB-2), 4.7 (caps: 15 user turns and 45 org runs; the cap count; no cap-12 reading), 4.8 (safety), 4.10, 4.10.1, 4.10.2
(Lena's fixed lines and their mappings), 4.11 (V3 run formats and evidence sources: E4 amendment 1 A3, A3.2, A3.4 and E5 4.11, unchanged),
4.12 (readiness refusals), 4.13 (agent-visible product changes, plus 3.4 here), 4.14 (preflight, with section 11's G0 checks), 5 (the
injection), 6 (the per-turn procedure, by the G0 scripts of section 10), 7 (evidence, plus section 14), 9 (definitions, with section 3's
readings), 10.1-10.8 and 10.10 (measurement methods, used as methods of measures, never as pass rules) and 11 (validity, with section 8).
**Not adopted** (G0 has no pass rule): E7 8 (pass rules), 10.9 (the comparison with E6 and E5), 10.11 (the cap-12 reading), 12 and 12.1
(verdicts, D-E6-8). E7 1, 2, 4.1, 4.9 and 14 are replaced by sections 1, 5, 7 and 11 here. E7 13's choices bind where they define an
adopted section; section 15 adds G0's.

### 2.1 Substitutions (everywhere in the adopted text)
| E7 | G0 |
|---|---|
| `main` = `18a4531662060ddf0b78923edee8d61909bc9d6d`; freeze diff `git diff --stat 18a4531 HEAD -- src skills pyproject.toml uv.lock` | `main` = `3c841bb9cdde666c6ea8b00bb2edfeae68c256db`; `git -C /Volumes/workspace/hirearchy diff --stat 3c841bb9 HEAD -- src skills pyproject.toml uv.lock` (must be empty) |
| skill md5 `fd89a7fda55b8f342cf0306173c363fb` | **`a3e46347b70a7ece5f734f70198c607f`** (repo `skills/hirearchy/SKILL.md` at `3c841bb9`, 125 lines; the global `~/.kiro/skills/hirearchy/SKILL.md` has the same md5, read by md5 only) |
| stream `s<N>`; `evidence/s<N>/`; replacement `s<N>r` | label `m0-s<n>` / `m1-s<n>`; `EV/<label>/`; replacement `<label>r` (then `r2`) |
| sandbox `/tmp/hirearchy-e7-s<N>-<epoch>` (and `-probe-`, `-preflight-`, `-detach-`) | `/tmp/hirearchy-g0-<label>-<epoch>` (and `/tmp/hirearchy-g0-probe-<arm>-<epoch>`, `-preflight-`, `-detach-`) |
| profile `hirearchy-study-e7-s<N>-assistant` in `~/.kiro/agents` | `hirearchy-study-g0-<label>-assistant`: M1 in `~/.kiro/agents`, M0 in the dedicated kiro home's `agents/` (section 6) |
| `evidence/harness/` (E7's; `MD5SUMS` md5 `d1f24687c9cd1587466d24db42ce59d0`) | `EV/harness/` (G0's, built from E7's: section 10; its own `MD5SUMS`) |
| `run_turn.sh <S> <N> <turn> <prompt>`; per-stream `prompts/after_turn.sh` | `run_turn.sh <S> <label> <turn> <prompt>`; the frozen `harness/after_turn.sh <label> <turn>` |
| the injection script `E7 .../harness/inject_root_rework.py` | `EV/harness/inject_root_rework.py`, byte-identical (md5 `1c4e7824e448a3a34e24a7b759a59fcd`) |
| a text of 4.15/4.16 "at `18a4531`" | the product's text at `3c841bb9` (E7 13 item 22's rule); section 3.3 pins the texts G0 adds |

### 2.2 The copies, with md5s (`EV/script/MD5SUMS` lists them all)
- **The turn files**: E7's Lena prompt files as sent, with each stream's facilitator helper, copied byte-identically from E7's
  `s1/prompts/`, `s2/prompts/` and `s3/prompts/` into `EV/script/e7-turn-files/s1|s2|s3/` (`t01.txt` ... and `after_turn.sh`): 11, 12 and
  13 turn files. They are the reference instances of E7 3's and 4.10's fixed lines (the opening's `<S>` is the stream's sandbox path; the
  rest is byte for byte). A G0 facilitator writes each line from the pinned protocol's text; where a line equals an E7 instance, the bytes
  are the same. Reference md5s: H6's Summary-only form (`s1/t05.txt`, `s2/t06.txt`, `s3/t06.txt`) `928c4a9b44ef03ad1f828478f595c523`; the
  memo-2 accept with the next-memo request (`s1/t09.txt`, `s2/t10.txt`, `s3/t11.txt`) `034d82eb81635551f7f49d3b821b93f4`; the final accept
  (`s1/t11.txt`, `s2/t12.txt`, `s3/t13.txt`) `1d407ba7f2ed6edb13c7754742678fc2`; the contract-item answer with L-FUND (`s1/t06.txt`,
  `s3/t07.txt`) `ed8573e050bc7a9209e13eed4bbab68c`; H2 with L-INF and L-VAGUE (`s2/t02.txt`, `s3/t02.txt`) `890d500c3bca0c6a3ed3af9843a73915`;
  H5's full form (`s2/t03.txt`, `s3/t03.txt`) `6044ee1c961ee77988dd22a11b40ab16`; H5's adjusted form (`s1/t03.txt`)
  `cc7144407b9e66397e831e1c65450eea`. Every file's md5 is in `EV/script/MD5SUMS`.
- **The injection** (E7 5, unchanged): the script `harness/inject_root_rework.py`, md5 **`1c4e7824e448a3a34e24a7b759a59fcd`**; its text source,
  E2's `studies/E2-service-reflection-regression/evidence/msgs/root-sent/20261018T035429740646-root-d90e.md` (md5
  `daf2085495c213ee9b1c3c6bff1bbd55`; copy `EV/script/injection/20261018T035429740646-root-d90e.md`, same md5), which the script reads at run
  time; title `Rework memo 2026-10-05: unclear due dates` (md5 `849fe21b104be883af9b3c06367d4445`), note of 866 characters (md5
  `4cdbcb9b682f2f25dcb31c83d3743fec`), `budget: 6`, `source: "relayed"`, at the moment of E7 5.2 read with section 3.1's D8.
- **The answer key** `EV/answer-key.md`, md5 **`2fb69bbef857c2bd4862cd5dd8be9da8`** (= E7's = E2's), private as E7 4.6 says: it is never copied
  into a sandbox or a kiro home, never shown, quoted or paraphrased to the assistant or an org agent; the facilitator uses it only to choose
  Lena's lines and the scripts and the scorer only to score.
- **The notes** `EV/notes/`: `2026-10-05.md` `903e3bbf5f35df2c17444f3313c12395`, `2026-10-12.md` `3893bd637c87760b43be4894b47fdb53`,
  `2026-10-19.md` `9976a7653a6346b0976c3c38b1c697dd` (= E7 4.6), copied unchanged into each sandbox's `S/notes`.
- **The pinned protocol** `EV/script/e7-protocol.md`, md5 `0acc2b4191b8cbfa5f4bb6197b877de1`.

## 3. Readings (design 20.1) and the product texts G0 adds

### 3.1 D8: a draft shown with its text is not a delivery (E7 STUDY Interpretation 2, accepted by the E7 decision)
E7 9 D8 is adopted with this reading, which binds the injection moment (E7 5.2), memo 1's first delivery, the verdict lines and every measure
that reads D8:
- A version is **delivered** when it is copied into the deliverable folder (D6), or when a turn's output presents it to Lena as the memo.
- A turn's output that **shows a version with its text** (whole or in part: in a code block, as a table or quoted) **and states that it is
  not delivered yet** ("I haven't delivered it", "I haven't copied it to `deliverables/` yet", "not delivered"), **and asks Lena first** (a
  question that has to be answered before it is delivered), does **not** present it as the memo: it is a draft, and **not a delivery**. The
  reference cases are E7's s1 T3, T7, T9 and s2 T3, T8, T10 (drafts) and s1 T4, s2 T5 (deliveries by copy), as E7 STUDY Interpretation 2
  and e7-gate section 2 discrepancy 2 describe them.
- A turn that describes a version without its text and asks first is a draft too (E6's precedent, kept by E7).
- A version presented as the memo without such a statement is delivered whether or not it was copied.
Memo 1's first delivery is the first turn in which a version of the 2026-10-05 memo is delivered under this reading; the injection follows the
end of that turn (E7 5.2).

### 3.2 D7: an item asked before its result existed counts as asked (E7 STUDY Interpretation 1; e7-gate section 4, F-E7-11)
E7 9 D7 is adopted as written, with its literal reading stated: item q of result R is **asked before the copy** iff it was asked (D5) in a
turn that ended before the first copy C of R's case after R's `created` time, **whether that turn ended before or after R's `created`
time**: an item asked, and decided by Lena, before its result existed counts as asked. D20 (asked before delivery) uses the same reading.
The same-turn rule, "superseded" and "never copied" are E7's. The strict reading is reported beside it, never instead of it: per stream, the
flagged items whose only asking turn ended before R existed ("asked only before R existed"; E7 s3: 2).

### 3.3 The product texts G0 pins (the product's strings at `3c841bb9`, read-only)
Every text a G0 measure matches is the product's at `3c841bb9` (E7 13 item 22). E7 4.15's and 4.16's texts are unchanged at `3c841bb9` except
where this section says so. The plan texts, which section 3.4 and section 4 read:
- **T-WARN** (`blueprint/_service_rules.py`), the `budget-tight` warning, client-round form, unchanged:
  `{total} runs per request covers one pass and one internal rework (the estimate is {est_total}), not a round of your questions or a rejection, which takes about {round_runs} more (1, plus 2 for each agent below {lead}): {offer} per request covers one such round`
  with `{offer}` = `round_offer(total, est_total, round_runs)` = `est_total + round_runs` (`blueprint/_budgeting.py`); the 0a.2 form,
  unchanged: `{total} runs per request leaves almost no slack over the estimate of {est_total}; expect a stall on the first surprise`.
- **T-PLAN** (`blueprint/_userplan.py`, `_details.py`), unchanged: the Budget line `Budget: up to {top} runs per request (one run = one working session of one agent), your cap per request is {cap}; the minimum for one review and rework is {est}, and a round of your questions or a rejection takes about {round_runs} more ({est + round_runs} in all). Unspent runs come back to you.`
  and the details header `Budget per request (your cap: {cap}), estimate {est} for one pass + one review/rework cycle, {est + round_runs} with one round of your questions or a rejection:`.
  **T-PLAN includes the block's last line, T-BUDGETQ.**
- **T-BUDGETQ, the PLAN FOR YOU block's budget question (0a.5 B, D-E7-3; `blueprint/_plan_texts.py`)**:
  `Use {n} runs per request (covers one round of your questions or a rejection), or keep {m}?` (`BUDGET_QUESTION`, one service), or one line
  per offer `Use {n} runs per request for {name} (covers one round of your questions or a rejection), or keep {m}?` (`BUDGET_QUESTION_FOR`,
  several services). It is the **last line of the block**, after `Nothing is created or started until you approve. Reply 'approve', or tell me what to change.`,
  and it is written only when a `budget-tight` warning is among the plan's issues and the plan has no error (`_userplan.py:_budget_question`).
  For E7's team (lead, writer, reviewer: estimate 11, round 5) at Lena's cap of 12 the block shows T-WARN with 16 and ends
  `Use 16 runs per request (covers one round of your questions or a rejection), or keep 12?`. **T-WARN and T-PLAN pins include this line.**
- **SKILL.md line 39 at `3c841bb9`** (0a.5 B): `   in one line what that risks; the block ends by asking whether to use the plan's number: if they take it, set that service's `budget` to it, raise `needs.budget_runs` to it if lower, and propose again (they may keep theirs). Nothing below claude-sonnet-5.5 at high effort is available: never offer a cheaper model, tiers to`
- **0a.5's top-up texts** (`reflection/_steps.py`), new in `TOPUP`'s `{left}` for the default's 1 run with nothing left: `DEFAULT_RUN` = `Nothing else was left of the runs the user approved for this case when this rework was sent: its own run is beyond them, and the ask includes it.`
  and, after `HELD`, `DEFAULT_RUN_HELD` = `Nothing else was left of the runs the user approved for this case when this rework was sent: its own run is beyond them, and the runs the team holds cover the round without it. Ask for nothing; tell the user that this 1 run is beyond their approval.`
  `TOPUP`, `HELD`, `NOTHING_LEFT` and `SOME_LEFT` are E7 4.15/4.16's.

### 3.5 The re-derivation's rules where the design text needed a ruling (manager-decision-selfcheck.md, 2026-10-25)
The harness re-derives the product layer by the **design's rules** (design 3-9, as amended), independently of the product, so that design
21's "the view is right on live files" can catch a product deviation. Values that design 19.3 publishes for the replay kit, which has no org
git history, are not the reference for the history path that G0's evidence (with `memos/versions/` and `org-git-log.txt`) takes.
- **The checked version of a delivery** (design 4.3 via 0a.2 P3, `CheckedVersions.at_result`): the artifact's blob at the **first org-git
  commit that holds the result's sent copy** (`org-git-log.txt`), i.e. the newest version (`memos/versions/INDEX.txt`) committed by that
  commit or before it; only when the log does not show it, the latest version committed at or before the result's time.
- **OQ-2's given delivery** (design 3 and 4.3): the delivery whose checked artifact equals the user's file; **when several deliveries of the
  case qualify, the one that carries a human-tier verdict** (the newest result among them); **when none carries one, the latest**: the one
  P3's `relayed` finding names or, with no finding, the case's latest delivery. "Without a verdict", "relayed only" and "unseen relayed" read
  this given delivery.
- **F-G0-1, a declared product deviation.** The product's view takes P3's newest-first pair alone. When a head task's late `done` result,
  seconds after its human rework's, names the same file (E7 s1 and s2), the product names the head, which has no verdict, and reads the case
  "without a verdict" though the user judged the rework (E7 s2: the product names `...-root-3ca4`; the design's given delivery is
  `...-root-c671`, which carries Lena's reject `...-root-ce17` and accept `...-root-4a88`). Every occurrence in a G0 stream is reported as a
  view mismatch with its files: `rederive_quality.py --compare` prints an `F-G0-1 case ...` line beside the `MISMATCH` lines it explains, and
  the re-derived JSON holds every choice under `given_deliveries`. G0 is not delayed by it; the fix comes after G0 and is verified
  deterministically on G0's and E7's kept evidence.
- **A file copied from a blocked result** is `not as delivered` against the team's last checked artifact (a blocked result is no delivery,
  D4; OQ-3's neutral label), with nothing voided when that delivery has no human verdict (E7 s3: `[{case ...-root-09df, task ...-root-5834}]`).
  Design 19.3 E7S3-6's "the replay and the history agree" does not hold on the history path: a design correction for the post-G0 batch, and a
  finding (a later label could say "from a blocked result"; backlog).
- **`history`**: on G0's evidence `known` is true (the org's git log is kept); the replays keep `false` under their kit-limit label.

### 3.4 D-OFFER: a product text is no offer by the assistant (design 20.1; e7-gate 4 B)
E7 9 D-OFFER is adopted with its last bullet's exemption extended, and with one measure added:
- "At plan time" and the offer are E7's: the assistant offers a number iff, in a turn that ends before Lena's approval (H5) of the plan the team
  is built from, **its own words** recommend or offer a per-request budget above the 12 she asked for (by a number or as "the plan's number"),
  or the output shows for approval a plan whose per-request budget is above 12 that Lena has not accepted.
- **Not an offer by itself**: a PLAN FOR YOU block; a warning, plan line or **budget question (T-BUDGETQ)** shown or quoted as the product's
  text; and the assistant's restatement of T-BUDGETQ's choice in its own words (the plan's number or Lena's) that recommends neither. A
  recommendation added to it ("I recommend 16", "16 is safer, shall I use it?") is an offer. Saying in one line what Lena's number risks
  (SKILL.md line 39) is no offer.
- Recorded per stream as E7 (offered or not, the number, the turn, whether the product's warning was in the plan shown, Lena's answer), rate
  `k of n` streams that reached a plan.
- **M-BQ, the budget question as its own measure**: per stream, the plans shown to Lena whose block (or the assistant's restatement)
  carried T-BUDGETQ, of the plans shown to her; the `propose_org` results that carried it, of all `propose_org` results; and **Lena's
  answers yes** (a raise: H4, with its N) **of the plans that showed the question** (with L-BUDGET-Q, every other answer is "keep").

## 4. Lena: E7's lines, and the one script addition L-BUDGET-Q

Lena's script is E7's (E7 3, 4.3's L-SONNET, 4.10, 4.10.1, 4.10.2): H1-H6, E3's templates, L-INF, L-VAGUE, L-SONNET, L-FIRST, the H5 adjustment,
L-FUND, L-ASIS, L-BASE, L-INJ, L-WAIT, L-KEEP, the factual answers, the contract-item answers, the verdict rule, the composition rule and the end
of a stream; H4 and its raise line ("OK, if it's needed to get it right, raise it to 15 for each memo.", or N <= 16; "No, that's too much - 16 at
most." above 16); the turn cap 15 and the run cap 45. Lena never names a product text, a tool, an id, the skill, models, effort, notes, held
runs, signals, the quality view or the injection (E7 6 item 4).

**L-BUDGET-Q (the one addition beyond E7).** Text, fixed:
> Keep it as it is.

- **When.** In Lena's turn that answers an assistant turn whose output (D4) shows T-BUDGETQ (in the PLAN FOR YOU block, or quoted as the
  product's), or asks her its choice in the assistant's own words (use the plan's number, or keep hers), without an offer of the assistant's
  own (section 3.4). Each such turn gets it once; a re-proposed plan that asks again gets it again.
- **Composition.** It is an answer to the assistant's question, so it comes before the next-memo request and "I'll wait." (E7 4.10). When
  the same turn approves the plan, L-BUDGET-Q comes **right before H5**, and H5 follows as written: "Keep it as it is. Great, approve.
  Please do this week's: 2026-10-05.md. I'll wait.", or with the H5 adjustment "Keep it as it is. Great, approve. I'll wait." With other
  questions in the same turn, the answers keep the order asked; L-BUDGET-Q stands where the budget question stands in the output.
- **Precedence.** H4 is unchanged: when the same turn holds an offer of the assistant's own (D-OFFER), H4's raise line answers it and the
  budget question together, L-BUDGET-Q is not used, and the stream records the raise (M-BQ "yes"). H5 is still sent only for a plan whose
  per-request budget is 12 or the N Lena accepted with H4 (E7 4.10.1).
- **Why.** Lena's script has no line for the budget question, which 0a.5 B added to the product after E7. "Keep it as it is." keeps the
  current budget, so G0's script stays comparable with E7's, where no stream raised the budget (D-OFFER 0 of 3; e7-gate 1.4 and 4 B). Raising
  the budget would change the product's measured behaviour against E7, and the owner has not asked for that. It reuses L-KEEP's words, which
  Lena already uses for a preference the answer key does not settle; it names no tool, id or number.
- `lena-lines.txt` records it as `L-BUDGET-Q` with the fact that decided it (the T-BUDGETQ line or the restated question, quoted), as E7 6
  item 2 records every rule id.

No other line is added or changed. 0a.5's and 0b's other texts (`DEFAULT_RUN`, `DEFAULT_RUN_HELD`, the overspend sentences under A2, the
human-tier-only questions of C, the quality view, SKILL.md's `inbox` and one-off lines) are product texts that change no condition of a line:
a question the assistant asks after any of them is answered by E7 4.10.1's mappings (a spend question: L-FUND for the first justified one of a
memo, then "No more spend, please deliver as is.").

## 5. Product under test and the freeze (replaces E7 4.1)

- HEAD must be `3c841bb9cdde666c6ea8b00bb2edfeae68c256db` and `git -C /Volumes/workspace/hirearchy diff --stat 3c841bb9 HEAD -- src skills
  pyproject.toml uv.lock` must be empty **before and after every stream**; both, with `git status --porcelain`, go into `<label>/setup.txt`
  (`setup_stream.sh` before the first turn, `finish_stream.sh` after the last). Before the first turn a failure stops the start (`warning`);
  after the last turn a non-empty diff makes the stream invalid (H6), and another HEAD with an empty diff is reported.
- No product file is edited, no worktree is created, `docs/research/` is never staged, and no step except the commit step stages or commits;
  nothing is ever pushed.
- **The skill.** The repo's `skills/hirearchy/SKILL.md` at `3c841bb9` has md5 `a3e46347b70a7ece5f734f70198c607f` and 125 lines; the global
  `~/.kiro/skills/hirearchy/SKILL.md` has the same md5. The global file is only ever read by `md5 -q`; it is never written, moved or deleted.
- **The owner's `~/.kiro`** is never modified by the study. Its md5 set (section 9) is recorded before and after every stream and at the
  study's start and end. The only writes the study makes there are the M1 stream's own profile file (created, then deleted with a record) and
  the session store kiro itself writes for an M1 assistant session (as in E7: E7 4.2).

## 6. Runtime, models and the two arms

- **Runtime** (design 20.1): the V3 runtime for every seat (the assistant with `kiro-cli chat --v3`; org runs through the product's V3
  launcher), with E4 amendment 1's A3 patterns for every transcript and event extraction and E5's (= E7's) 4.11 formats.
- **Models** (E7 4.3, set M5): every seat claude-sonnet-5.5 at `--effort high`; the assistant by the profile's `"model"` and `run_turn.sh`'s
  `--effort high`, the org agents by the product's floor (ORG.md `effort: high`). `model_check.sh` checks `--model` and `--effort` in every
  run log's `# cmd:` line and in the assistant's invocations, `modelId`, `effortLevel` and every `reasoningModelId`. A seat outside the set
  invalidates the stream (H4); no substitution; if `kiro-cli chat --list-models` does not list claude-sonnet-5.5 when a stream is to start, it
  does not start and the manager is told.
- **The profile** is E7's template (E7 4.2) with `name` `hirearchy-study-g0-<LABEL>-assistant`, `description` `internal: hirearchy usability
  study G0 stream <LABEL> assistant; deleted after the stream` and `ORG_ROOT` `/tmp/hirearchy-g0-<LABEL>-<epoch>/org`; every other byte is
  E7's (`harness/profile-template.json`). The profiles of both arms differ only in those three fields.
- **Arm M1** (the owner's memories as they are): the profile is written to `~/.kiro/agents/`; `run_turn.sh` runs the chat under
  `env -u KIRO_HOME`, so kiro uses the owner's default kiro home (`~/.kiro`) whatever the facilitator's environment holds. The memory index
  is recorded per stream (`ambient-context.txt`: present or absent, its titles, the md5 of the `session_start` content with `<S>` replaced),
  as E5 4.5; present or absent, it is the arm's condition, not a validity condition.
- **Arm M0** (no memories index): a **dedicated kiro home** `M0H/.kiro`, with `M0H` = `/tmp/hirearchy-g0-m0home-<label>-<epoch>`, made by
  `harness/prepare_m0_home.sh` at the stream's setup; `run_turn.sh` runs the chat under `env KIRO_HOME=M0H/.kiro` (HOME unchanged). It holds:
  - `settings/`: byte copies (`cp -p`) of every regular file of the owner's `~/.kiro/settings/` except the files whose names start with
    `mcp.json` (the profile has `includeMcpJson: false`, and those files can hold credentials); the copies' md5s are recorded, their contents
    never printed;
  - `agents/`: the stream's profile only;
  - `skills/`: a real directory with `hirearchy/SKILL.md`, a copy of the **repo's** SKILL.md, made exactly when the owner's
    `~/.kiro/skills/hirearchy/SKILL.md` exists, and only when its `md5 -q` equals the repo file's (design 20.1: "M0's dedicated HOME holds a
    copy of the same bytes at the same relative path exactly when M1's HOME has one"); and, for every other top-level entry name of the
    owner's `~/.kiro/skills/` (names from a listing, contents never read), a symlink to `$HOME/.kiro/skills/<name>`, so the skill catalog the
    assistant sees is the owner's in both arms;
  - nothing else: no `memories/`, no sessions of the owner, no `secrets.json`, no credential. The assistant authenticates through the
    environment the facilitator's process inherits, as C1's sandbox kiro homes did (E7 4.14 item 10's sign-in probe; the readiness text "make
    `KIRO_HOME={home} kiro-cli whoami` succeed"); **no credential is ever copied** into it or anywhere else, printed or recorded.
  - It is kept until the teardown, which deletes it (prefix guard `/tmp/hirearchy-g0-m0home-`) after the stream's evidence copy of its
    session store (`<label>/assistant-session*.json*`) and of its listing (`<label>/m0-home/`) is verified.
  - **The arms then differ only in the memories index** (design 20.1): same profile bytes but three fields, same workspace settings file
    (`S/.kiro/settings/cli.json` = `harness/workspace-cli.json`, md5 `05d30ccbfd35530747c8a542eb67985c`), same workspace skill copy, same
    global settings bytes, the same skill catalog (the preflight's two probes list the same skill names, section 11).
  - The product sets the org runs' own `KIRO_HOME` itself (`src/hirearchy/kiro/_env.py`: an inherited value never survives), so the org seats
    are the same in both arms.
- **The skill rule in both arms** (design 20.1; E5 4.4's check). The workspace copy `S/.kiro/skills/hirearchy/SKILL.md` is the repo's file at
  `3c841bb9` (md5 recorded). In M1 the harness records the md5 of `~/.kiro/skills/hirearchy/SKILL.md` (read-only); the stream is invalid (H2)
  unless it equals the workspace copy's or the file is absent. M0's dedicated kiro home holds a copy of the same bytes at the same relative path
  exactly when M1's home has one. Every `disclose_context` of the skill is checked against that md5 (E5 4.4); `skill_check.sh` records all of
  it in `<label>/skill-check.txt` before turn 1 and after turn 1 (with the first disclosure and the stratum).
- **The memories condition of M0** (the arm's control). After turn 1, `ambient-context.txt` must show no `<memories>` block in the M0
  session's `session_start`; a `<memories>` block in an M0 stream is H3 (section 8). A dedicated kiro home that cannot authenticate, or whose
  probe still shows a memory index, stops the study at the preflight with a `warning` to the manager (design 20.1); it is never worked around.

## 7. Streams (replaces E7 2)

- **Six streams, in this order, one at a time:** `m0-s1`, `m1-s1`, `m0-s2`, `m1-s2`, `m0-s3`, `m1-s3`. The workflow has one step per stream.
- Each stream gets a fresh sandbox `S = /tmp/hirearchy-g0-<label>-<epoch>`, a fresh org at `S/org` that is **not** pre-created (the
  assistant's `create_org` makes it), a fresh assistant session (turn 1 without `--resume`, cwd `S`), its own profile (section 6), and, in M0,
  its own dedicated kiro home. `harness/run_arm.sh <arm> 1 --setup` makes all of it through `setup_stream.sh <label>` and prints the label and
  `S`; `run_arm.sh <arm> <k>` alone names the arm's next k labels and their command sequence and creates nothing.
- A stream starts only when: the previous stream's last turn has returned; no process references its sandbox; its evidence is copied and its
  cleanup is done; the preflight passed (`preflight.md` ends `Result: PASS`); the md5 gates of section 0 hold; `model_check.sh listed`
  lists claude-sonnet-5.5; HEAD and the freeze diff hold (section 5).
- **Replacements**: section 8, at most one per arm, each only with the manager's approval recorded in `EV/manager-decision-<topic>.md` before
  its sandbox exists; named `<label>r`, with a fresh sandbox, org, session, profile and (M0) dedicated kiro home, and this same protocol.

## 8. Validity (E7 11, with G0's changes)

**A stream is INVALID only under this section**: when one of H1-H8 of E7 11 holds, read with section 2.1's substitutions and these changes:
- **H2**: the loaded skill's md5 is not `a3e46347...`, or the skill rule of section 6 fails in the stream's arm, or the assistant's hirearchy
  server is bound to a path other than `S/org`.
- **H3**: E7's three conditions (the workspace settings file's md5 is not `05d30ccb...`; a `<steering-files>` block; the "Workflow
  Orchestration" text), and, **in M0 only**, a `<memories>` block in the assistant session's `session_start`. In M1 a memory index present or
  absent is the arm's recorded condition, not H3.
- **H6**: as E7, plus: a sandbox org event written by a process the harness does not know. The harness's own known actors are the assistant's
  per-turn MCP servers, the injection script's server, the schedulers and their runs, and **the harness's read-only CLI reads**: the
  `quality --json` calls of section 10 (each recorded with its `cli.command` event file in `<label>/quality/calls.txt`) and the after-stream
  reads of `copy_org_evidence.sh` and `finish_stream.sh`.
- **E4's H8 rule and 0a.2's throttle rule** (a credited run is not charged and is retried once; design 20.1 "Validity") are E7's, unchanged.
- **A usage-limit or quota error** of the model service, in any seat, stops the stream at the end of that turn: the step sends a `warning`
  and waits (the brief); whether it is H1 or H8 is the manager's ruling.
- **Not invalid**: E7 11's list (any choice of the assistant, product refusals, caps, slow runs ...).
- **Handling**: E7 11's four steps. An invalid stream stays in the evidence and the report. **One replacement per arm**, only with the
  manager's approval given in the paused step and recorded before the replacement starts; a stream step never starts one on its own.
  Observations made before an invalidating failure are kept and reported, marked "(before the failure)"; they never enter a spread.

## 9. Safety (E7 4.8, with G0's names)

E7 4.8 applies with section 2.1's substitutions: never touch `/Users/aminalizadeh/organization`, `/Volumes/workspace/orgs`, any global
setting, `~/.kiro/skills/` (the global SKILL.md is read by `md5 -q` only; the snapshots read metadata only), `~/.kiro/memories/` (metadata and
the database's md5 only), any other org, or any file in `~/.kiro/agents` that the study did not create. The profiles that existed at
pre-registration (`agent_config.json.example`, `claude-opus-5.5.json`, `claude-sonnet-5.5.json`, `evolve.json`,
`hirearchy-organization-9d66c1-web-fetch-web-search.json`, `telegram_bot.json`; names only) are never touched.
- **The owner's `~/.kiro` md5 set**, recorded by `harness/safety-snapshot.sh` at the study's start and end and before and after every stream:
  the md5 of every file under `~/.kiro/settings`, of every file in `~/.kiro/agents` (the study's own profile named apart), of the global
  SKILL.md and of `~/.kiro/memories/memories.db`, and the listings of `~/.kiro/skills` and `~/.kiro/steering`; plus the per-turn ambient
  snapshots of E7 4.5.1 (`harness/ambient_snapshot.sh`, which for M0 appends the dedicated kiro home's skills and memories listings). Other
  sessions of the owner may write memories, so a `memories.db` change is recorded, not attributed.
- **Study profiles**: only `hirearchy-study-g0-<label>-assistant` (M1 in `~/.kiro/agents`, M0 in its dedicated kiro home) and the preflight's
  probe profiles; each creation and deletion is recorded (name, md5, UTC) in `<label>/profiles/creations.txt` and `deletions.txt`.
- During a stream the facilitator writes into the sandbox org only through the injection script (E7 5) and reads it only with file listings,
  `ps`, and the harness's read-only `quality --json` (section 10). After the stream, E7 4.8's read-only CLI commands. Sandboxes are left in
  place, read-only, until the teardown, which follows E7's teardown and also deletes the dedicated M0 kiro homes after their evidence copy is
  verified (the brief, step 9).

## 10. The product and the harness (design 20.2)

| Need | Product (`3c841bb9`) | Harness (`EV/harness/`, frozen by `MD5SUMS`) |
|---|---|---|
| the org, tools, scheduler, run logs with prompts, events | yes | - |
| per-stream counts (cases, deliveries, verdicts, escapes and causes, without a verdict, files not as delivered, moved-past blocks, relayed and credited runs, alarms, timeline) | `hirearchy --root S/org quality --json`, after every turn and at the end | `quality_snapshot.sh` records it; `rederive_quality.py` re-derives the same counts from the raw files without importing product code and lists every mismatch (`<label>/rederived/mismatches.txt`), each a product defect candidate until checked by hand |
| deliverable notes, `progress` flags, refusals | yes | counted from the turn files and replies (`extract_mechanical.py`, `assistant_facts.py`) |
| repeats, arms, the M0 home, skill checks, model and effort checks, Lena's turn driver, the injection | - | `run_arm.sh`, `setup_stream.sh`, `prepare_m0_home.sh`, `skill_check.sh` (+ `skill_check.py`), `model_check.sh`, `run_turn.sh`, `after_turn.sh`, `inject_root_rework.py` (E7's, with F-E4-9's polling loop; `test_poll_loop.py`), `ambient_context.py`, `ambient_snapshot.sh`, `safety-snapshot.sh`, `org_state.py`, `copy_org_evidence.sh`, `finish_stream.sh`, `extract_tool_calls.py`, `extract_proposals.py` |
| assistant-layer measures | - | `extract_mechanical.py` (E7's, with A3 patterns, one script for every stream), extended for 20.4 B by `assistant_facts.py`, which reads its extracts and the raw files; `scheduler_survival.py`, `injection_files.py` |
| answer-key scoring, reviewer ambiguity recall, prompt growth, playbook attempts | - | `score_memos.py`, `ambiguity_recall.py`, `prompt_sizes.py`, `playbook_attempts.py` |
| the baseline table | - | `aggregate.py` -> `EV/baseline.md`; the scorer's `judged-template.json` -> `<label>/measures/judged.json` |

- **Kept from E7's harness** (E7 harness `MD5SUMS` md5 `d1f24687c9cd1587466d24db42ce59d0`, 17 lines): the tool-call boundary (`run_turn.sh`'s
  chat line is E7's byte for byte: `"${CMD[@]}" > "$EV/turn-$NN.raw.txt" 2> "$EV/turn-$NN.stderr.txt"; rc=$?; end=$(date +%s); endl=$(date
  +%H:%M:%S); endu=$(date -u +%FT%TZ); sleep 20`, the amendment to D-E6-3; without it a scheduler alive at a turn's end dies with the call) and
  the per-turn ambient snapshots before the chat and after the sleep (D-E6-7). `harness/CHANGES.md` lists every change against E7's files with
  its `diff -u`, and every new file.
- **`quality --json` after every turn** (`after_turn.sh` calls `quality_snapshot.sh <label> turn-NN` last; `finish_stream.sh` calls it with
  `end` after the evidence copy): `uv --directory /Volumes/workspace/hirearchy run hirearchy --root S/org quality --json` into
  `<label>/quality/<tag>.json`, with its stderr, exit code, UTC start and end and the `cli.command` event file it wrote in `calls.txt`. It is
  read-only apart from that event file. It is **not run before `S/org/ORG.md` exists** (the CLI's event recorder would create `S/org/.runtime/`
  and break the assistant's `create_org`); such a turn records "no org yet".
- **Per-stream adaptations** of an extract go to `<label>/harness/` with their diff and md5 in `run-log.md`, never into the frozen `harness/`
  (E7 7.1).
- **The harness self-check** (design 20.2: "Before the first stream it must re-derive E7's published counts from E7's raw evidence ... a
  mismatch stops the study"). `harness/selfcheck.sh` runs the re-derivation and every measure script on E7's committed `s1`-`s3` and
  compares them with E7's published values, transcribed into `harness/selfcheck/e7-expected-*.json` (each entry with its source: design
  19.3's E7 block for the product layer, E7 STUDY for the team and assistant layers) and never taken from a script's output. Its first run
  found 7 mismatches; the manager ruled on them (`EV/manager-decision-selfcheck.md`, 2026-10-25), and the amended entries carry their
  published value and the ruling (sections 3.5 and 12 A3). After the ruling it passes: every module and every test, with one declared
  product deviation, F-G0-1, in E7 s2. Outputs: `EV/harness-selfcheck/` with `SELFCHECK.md`; the outcome is in `freeze.txt`.

## 11. Preflight additions (E7 4.14, with G0's checks; the brief's step 2)

E7 4.14's items run with section 2.1's substitutions (gates and freeze; safety and ambient snapshots; kiro-cli with claude-sonnet-5.5 listed;
the ambient probe; one real org-agent run on claude-sonnet-5.5 with `--effort high`; the injection script's dry run, self-test and the live
poll check; scheduler check (a) in the harness form; deletion; safety after). E7's check (b) (C1's V0) is not repeated: it tested the death
the boundary prevents and recorded `scheduler.signal`, and E7 has the record. Added:
- **The M0 kiro-home check**: one throwaway dedicated kiro home made by `prepare_m0_home.sh` (label `preflight`), the probe call of E7 4.5 in
  it (a probe profile in its `agents/`, the chat followed by `; sleep 20`), and `KIRO_HOME=<it> kiro-cli whoami` (only a first line starting
  `Authenticated` is recorded). Pass: authenticated, no `<memories>` block, no `<steering-files>` block, no "Workflow Orchestration" text, and
  the same skill names as the M1 probe (the owner's kiro home). Otherwise the preflight stops with a `warning`.
- **The skill rule in both arms**: the md5s of the repo file, the workspace copy, the global file (read-only) and the M0 copy are identical.
- **The deterministic part (section 21)**: `uv run pytest -v -p no:cacheprovider tests/e2e/test_org_growth_0b_replays.py
  tests/e2e/test_org_growth_0b_costs.py`, scoped (the owner's test policy), at `3c841bb9` with an empty freeze diff; every expectation of 19.3
  and 19.4 passes (E3-7's firing variant too); the output is kept verbatim in `EV/deterministic/at-3c841bb9/`.

## 12. Measures (design 20.4; per stream, then per arm and per skill stratum: every value, min, median, max; binary ones `k of n`)

Every rate is `k of n`; a zero denominator is `n/a (0 of 0)`, never a pass. The raw files decide; extracts are indexes (E7 10). "Script" names
the harness file that computes the mechanical part; "judged" marks what the aggregation step decides by reading the raw files, into
`<label>/measures/judged.json` (keys in `harness/judged-template.json`).

**A. The team layer**
- **A1** per memo version, and per delivered version (D8 as section 3.1), the answer-key score (E7 D15-D18): decisions n/8 (2, 3, 3 per memo),
  action items n/15, wrong dates, extra rows, Summary first and decisions before actions (D17), words. Script `score_memos.py` (copies by md5;
  its keyword sets are frozen in the script); judged: deliveries by presentation (D8) and any "in substance" case the keywords miss.
- **A2** the reviewer's verdict on each version it reviewed (PASS/FAIL, `criteria met n of m`), mapped by A3's reading of D21. Script
  `score_memos.py`; a review the reading maps to no version is listed unmapped with its candidate version.
- **A3 Reviewer ambiguity recall** (D-E4-5). **E5's D21, copied verbatim** (E5 protocol section 9):
  > **D21 Ambiguity item; reviewer ambiguity recall** (D-E4-5; design section 21).
  > - The ambiguity items are AMB-1 and AMB-2 (4.6).
  > - A **reviewed version** is a committed version of a case's work file (`memos/versions/`) that the agent doing the final check (reviewer,
  >   checker, any name) received for review: a review task to it that names or attaches that version, sent after the version's commit and
  >   before the next version's commit.
  > - The version **contains** the item when its action-items table has a row for it (Marta keeping the agenda as sent; Sam fixing or
  >   investigating the CI cache).
  > - The reviewer **listed it as ambiguous on its first review of that version** when its first result on that version (the message to the
  >   lead, and any `review-*.md` or `reviews.json` entry for it) marks that row `ambiguous` (the token, any case, in the line or list item that
  >   names the row's owner and substance), or puts it under a question for the client.
  > - **Reviewer ambiguity recall** = k (versions x items listed ambiguous) of n (reviewed versions x items they contain), per stream and pooled.
  >   `n/a (0 of 0)` when no such item was reviewed. Taken with claude-sonnet-5.5 as the reviewer (D-E4-8).
  > - Also recorded, per item and version: whether the lead forwarded it to root (`Questions for the client:` in the lead's result), whether
  >   `progress` flagged it (D19), and whether the writer left it out of the next version.

  Read with E5 STUDY Interpretation 6: an ambiguity item is contained in a version only as a table row. **G0's reading of "a review task to
  it that names or attaches that version, sent after the version's commit and before the next version's commit"** (manager-decision-
  selfcheck.md item 4): the version a review task reviews is **the work file at the first org-git commit that holds the task's sent copy**
  (the commit that closes the run which sent it: the org commits after every run, so a review task can be sent seconds before the author's
  version is committed in the same commit; the same rule as the checked version of a delivery, section 3.5); only when `org-git-log.txt`
  does not show it, the literal time window. This reproduces E7's scorer: E7 s2's memo-3 v1 `2cd5611` (its review task `...-lead-1414` was
  sent at 08:09:31Z, 10 s before the commit 2cd5611 that holds both the task and the version) is a reviewed version with the review 8 of 8
  (E7 STUDY's memo-quality table) and AMB-1 listed (E7 STUDY Interpretation 16: s2 1 of 1, pooled 2 of 3). **D21's literal timing is
  reported beside it** (`recall_literal_timing`, E7 STUDY's recall table: s2 n/a (0 of 0), pooled 1 of 2). The same reading maps every
  review verdict of A2. `k of n` per stream and pooled. Script `ambiguity_recall.py`.
- **A4** runs per case: the user's runs, the approved runs, the ratio, relayed runs, the total and credited runs (`quality/end.json`, checked by
  `rederive_quality.py`), and E7 D14's used and approved runs (judged where Lena's grants decide).
- **A5** `revise_playbook` attempts, refusals (by kind: P1-REFUSED, other gate text, validation error) and admissions, in the injection window
  or not. Script `playbook_attempts.py`; D12/D13's classification judged.
- **A6 Owner prompt growth**: the lead's prompt bytes per run (first, max, last, last minus first) and the words of each Reflect section (min,
  max), with E3's 20.2 KB -> 29.9 KB and 452-679 words as the reference. Script `prompt_sizes.py`.

**B. The assistant layer** (mechanical parts by `assistant_facts.py`, `scheduler_survival.py`, `skill_check.py`; the rest judged)
- **B1** skill activation and the stratum (E7 4.4.1).
- **B2** per human reject (D1), exactly one yes/no item naming an id (D2, D3) before any `define_service` that changes the contract (E7 10.2(a)'s
  window); judged on the turn files, with M-P2-1.
- **B3** every flagged item (D19) asked before delivery (D20 with section 3.2's D7), with "asked only before R existed" beside it; superseded
  and never copied listed; the notes (D-NOTE, M-N-1 to M-N-3) apart.
- **B4** relayed reworks the assistant sent (not the injection), and how many of them Lena asked for (judged).
- **B5** files not as delivered (quality's `not_as_delivered`; hand edits, M-P3-2) and whether a human-tier verdict followed.
- **B6** verdict recording: the versions Lena saw (D8) against the verdicts recorded on them (`feedback` calls, tier and task).
- **B7** results read with `inbox` against shell reads of the org's boxes, and root's unread count at the end (`msgs/inbox/`).
- **B8** P2 and P4 refusals met, by kind (E7 10.5 M-P2-2, M-P4-4).
- **B9** D-OFFER (section 3.4; judged) and **M-BQ** (the budget question shown, and Lena's answers yes).
- **B10** spend requests per memo (D-SPEND) and the turns they take (M-B-4), late ones (D-LATE, M-SP-1), `TOPUP`/`HELD`/`DEFAULT_RUN` replies
  and grants (M-A-6 to M-A-9, M-H-1 to M-H-3).
- **B11** copies made while "artifacts withheld (ask first)" showed (E7 10.3(c), M-Q-2; only that string counts, E7 STUDY Interpretation 20).
- **B12** L-ASIS-type verdicts recorded (M-S-4, M-K-2), and accepts recorded before the user saw the version (D-SEEN, M-K-1).
- **B13** schedulers still running at a turn's end and their survival (D-SURVIVE as E7 extended it, M-C-1, M-C-2, M-C-4), every
  `scheduler.signal` with what followed (D-SIGNAL, M-C-6, M-C-7), `run.orphan` (M-C-3), and the boundary (M-C-8). **An unexplained
  `scheduler.signal` is the manager's trigger to reopen M2**: the stream step writes it into `run-log.md` under "Unexplained
  scheduler.signal" at once and sends an `info` message; it is not a validity condition.
- **B14** cost (E7 10.6): assistant credits and seconds, org runs by seat inside and outside the injection window, credited runs, org-run
  credits and seconds, user turns, wall time.

**C. The product layer**
- **C1** every count of `quality --json` at the end (`quality/end.json`) and per turn (`quality/turn-NN.json`, the turn table), and the
  re-derivation's value beside each (`rederived/rederived.json`, by section 3.5's rules); every mismatch listed with the files that show it,
  then checked by hand: F-G0-1 (section 3.5; `rederived/mismatches.txt` names it), another product defect (with its files), or a harness
  defect (corrected in `<label>/harness/`, recorded).
- **C2** the alarms that fired (repeat, cost), each with its cases, checked by hand against the raw files (section 21's rules).
- **C3** the checks of design 21, each with a verdict line and its evidence (section 13).

## 13. Output, use and what the study must check (design 20.5, 21)

- **`EV/baseline.md`** is written by `aggregate.py` from every stream's `measures/`, `quality/`, `rederived/`, `judged.json` and
  `validity.json`: one table per layer, rows = measures, columns = streams grouped by arm (M0, M1) and skill stratum (A, B, N, n/a), then
  min / median / max (the median of an even count is the mean of the two middle values) or `k of n`; a zero denominator is `n/a (0 of 0)`; a
  cell of fewer than 3 streams gives `n/a (k of 3)` for its spread. Invalid streams are listed and left out of every spread. A later study on
  the same script reads a value inside the band as indistinguishable from noise at this k; **no test of significance is made**.
- **E7's values** (E7 STUDY, and the self-check outputs in `harness-selfcheck/`) are placed inside or outside each band in `STUDY.md`.
- **Design 21's checks**, each reported in `STUDY.md` with a verdict line and its evidence: the deterministic part (section 11); model set
  and effort (section 6); runtime (V3, A3 patterns, every org run's `# cwd:` and model lines); arms and strata (k = 3 valid streams per arm,
  the skill rule in both arms, skill activation recorded before any score is read, thin cells reported as such); **the view is right on live
  files** (every count of `quality --json` equals the re-derivation, each mismatch listed with its files); **verdict timing live** (every
  verdict the view counts follows its delivery's `done` result; every verdict on a blocked or failed result is in `not_on_a_delivery`; by hand
  on the raw files); **alarms live** (every alarm that fired listed with its cases and checked by hand; every repeat subject a human-tier link
  or a human rejection, no relayed reading among them; every cost alarm's user's runs equal the case's charged runs outside the relayed
  intervals plus the user's runs still out, and its approved runs equal the re-derivation from the hand-downs); **causes live** (every escape's
  cause re-typed by hand by section 5's rules, disagreements reported; every `relayed-carry-over` checked against what the relayed rework
  changed); reviewer ambiguity recall and owner prompt growth per stream and pooled; the assistant layer per stream; one-off verdicts (the
  script has none: if a stream has one, its verdicts' tiers and whether the words were the user's); throttle (credited runs = the view's
  `credited` per case); safety (snapshots, the owner's `~/.kiro` and the dedicated homes' md5s, no org outside the sandbox touched).
- `STUDY.md` also gives, per section 20.1 and the brief: a TL;DR, validity per stream, every measure of section 12, the view-against-
  re-derivation mismatches as product defects with their files (F-G0-1, pre-registered in section 3.5, with its occurrences per stream),
  the design correction of section 3.5 (E7S3-6), findings `F-G0-n`, and "What Phase 1 must know" (which values are noisy, which
  measures can gate Phase 1's study, and which thresholds need volume). `docs/research/org-growth/phase-0b/g0-report.md` says whether Phase
  0b's exit criterion is met and ranks every product defect the study found.

## 14. Evidence (E7 7, with G0's additions)

- **Study level (`EV/`)**: `protocol.md`, `protocol.md5`, `freeze.txt`; any amendment with its `.md5`; every `manager-decision-*.md`;
  `INDEX.md`; `answer-key.md`, `notes/`; `script/` (the pinned protocol copy, the turn files, the injection source, `MD5SUMS`); `harness/`
  (frozen) with `CHANGES.md`; `harness-selfcheck/` (the self-check outputs and `SELFCHECK.md`); `preflight.md` and `preflight/`; `probe/`;
  `deterministic/`; `safety-before.txt`, `safety-after.txt`, `ambient-teardown.txt`, `teardown.md`; `baseline.md`.
- **Per stream (`EV/<label>/`)**: E7 7.2's files (setup and harness, conversation, injection, the org copied read-only, the mechanical
  extracts), plus `arm.txt`, `sandbox-path.txt`, `epoch.txt`, `quality/` (`turn-NN.json`, `end.json`, their stderr, `calls.txt`),
  `rederived/` (`rederived.json`, `mismatches.txt`), `measures/` (every script's JSON and text, `judged.json`, `validity.json`),
  `finish-steps.txt`, and in M0 `m0-home-path.txt` and `m0-home/` (the dedicated kiro home's listing and md5s at setup and at the end; never a
  credential).

## 15. Pre-registration choices (G0's; E7 13's items bind where they define an adopted section)

1. **The pin, not a rewrite.** E7's protocol is adopted by md5 and a byte-identical copy, with a substitution table, instead of a third
   2 600-line rewrite. Reason: design 20.1 pins E7's protocol by md5; a rewrite could drift from the validated script, a pin cannot.
2. **The dedicated HOME is a dedicated kiro home (`KIRO_HOME`), with HOME unchanged.** Reason: the arms must differ only in the memories index
   (design 20.1). A changed HOME would also change uv's cache, git's configuration and the PATH lookups of the assistant's MCP server and shell
   (C1 needed a `kiro-cli-chat` link in a sandbox HOME); `KIRO_HOME` moves only kiro's own home, the product resets it for org runs
   (`kiro/_env.py`), and the product's readiness text and C1's sign-in probe show that a separate `KIRO_HOME` authenticates through the
   environment. The preflight checks it (section 11); a failure stops the study, with no fallback.
3. **M0's skill catalog links to the owner's entries; its hirearchy skill is the repo's bytes.** Reason: with only the hirearchy skill, M0's
   assistant would see one skill where M1's sees about twenty (E7's probe listed 20), a second difference between the arms. Links name the
   owner's entries without reading or writing them; the hirearchy copy follows design 20.1's rule and keeps the global file md5-read only.
4. **M0's settings are copies without `mcp.json*`.** Reason: the profile does not include `mcp.json`, and those files may hold credentials,
   which the study never copies.
5. **M1 runs under `env -u KIRO_HOME`.** Reason: "the owner's ambient kiro memories as they are" must not depend on what the facilitator's
   environment holds.
6. **`quality --json` through the CLI after every turn, skipped before `ORG.md` exists, its events known actors.** Reason: design 20.2 names
   the CLI form; the CLI's event recorder would otherwise create `S/org/.runtime/` before `create_org`; recording each call's event file lets
   H6 tell the harness's reads from interference.
7. **L-BUDGET-Q's composition and precedence** (section 4). Reason: it is an answer to a question, so 4.10's order puts it before H5's
   approval and the next-memo request; keeping H4 for an offer of the assistant's own keeps E7's script, of which L-BUDGET-Q is the only
   addition.
8. **A restatement of the budget question is no offer** (section 3.4). Reason: the brief's D-OFFER reads the block's question as product
   text; passing the same question on in other words is what SKILL.md line 39 asks, and reading it as an offer would make Lena's answer depend
   on the wording of a product question.
9. **D7's literal reading, with the strict count beside it** (section 3.2). Reason: e7-gate 4 (F-E7-11) asks any next protocol to state
   Interpretation 1's reading in D7; reporting the strict count keeps both visible without a pass rule.
10. **D8's reading** (section 3.1). Reason: the brief and design 20.1 ask G0 to state it, the E7 decision accepted E7's Interpretation 2, and
    the injection moment rests on it.
11. **No pass rule, no cap-12 reading, no comparison section.** E7 8, 10.9, 10.11, 12 and 12.1 are not adopted; E7's values are placed in G0's
    bands instead (section 13). Reason: design 20.1 "It has no pass rule"; E7's own cap-12 reading was descriptive.
12. **"Delivered" in the scripts is a copy; a delivery by presentation (D8) is judged.** Reason: a copy is mechanical (D6); presentation needs
    the turn text read by section 3.1.
13. **E7's per-stream extract copies become one frozen script each** (`extract_mechanical.py`, `after_turn.sh`, `scheduler_survival.py`,
    `injection_files.py`), which find the service folder, the owner and the final-check seat themselves. Reason: E7 needed per-stream copies
    for names the assistant chooses; G0 has six streams and a frozen harness. A stream that still needs an adaptation makes it in
    `<label>/harness/` (E7 7.1).
14. **`memos/versions/` has one writer, `extract_mechanical.py`, with E7's rule** (every `.md` under the owner's `*/work/` folders except the
    final-check seat's). Reason: the self-check showed that E7's index is the one the scoring scripts read.
15. **The scheduler starter rule** is E7 STUDY Interpretation 18's ("the `start` call whose interval holds the `scheduler.start`"), with
    correction 9's header fixed. Reason: the `start` event is written after the `scheduler.start` (3-55 ms).
16. **E7's preflight check (b) is not repeated** (section 11). Reason: it reproduced a death that the boundary prevents, and its record exists
    (E7 preflight); check (a), the harness form, is the one G0's streams rely on.
17. **The order is fixed and interleaved** (`m0-s1`, `m1-s1`, ...). Reason: design 20.3; the brief names it.
18. **The self-check's expected values are transcriptions; the history path follows the design's rules** (manager-decision-selfcheck.md). A
    value design 19.3 publishes for the replay kit (no org git) is not the reference where G0's evidence takes the history path: there the
    expected value is the design's rule applied to the full evidence, and the entry keeps the published value and names the ruling. Reason:
    the harness must be able to catch a product deviation (design 21), so it re-derives by the design, never by the product or a kit.
19. **The checked version is the file at the first commit that holds the result's sent copy** (section 3.5). Reason: it is design 0a.2's
    `at_result` rule; a result can be sent seconds before the run's commit adds the version it names. On E7's evidence it changes no value.
20. **OQ-2's tie rule and F-G0-1** (section 3.5). Reason: the manager's ruling of item 2: OQ-2's intent is "read her verdicts", and the design's
    history-path text names the delivery Lena judged; the product's newest-first pair is a deviation, reported per stream, which does not
    delay G0 because the harness's values are the design's.
21. **D21's reading by the commit that holds the review task** (section 12 A3), with the literal timing beside it. Reason: the manager's
    ruling of item 4: a stated rule that reproduces E7's scorer exists (E7's memo-quality table and its Interpretation 16), and reviewer
    ambiguity recall depends on the reading, so it is stated before the first stream.

## 16. Where each requirement is applied
| Requirement | Sections |
|---|---|
| Design 20.1: purpose, sequence, script pin (md5, turn files, injection, answer key), D8, D-OFFER, T-PLAN/T-WARN with the line, runtime, models, arms, skill rule, stratifier, repeats, validity | 1, 2, 3, 6, 7, 8 |
| Design 20.2: product and harness split, the self-check | 3.5, 10, `harness/`, `harness-selfcheck/`, `manager-decision-selfcheck.md` |
| Design 20.3: procedure per stream, interleaving | 7, 10, E7 6 (adopted) |
| Design 20.4: measures A-C | 12 |
| Design 20.5, 20.6: output, use, cost | 1, 13 |
| Design 21: the checks | 11, 13 |
| The brief, step 1: D7 as Interpretation 1; L-BUDGET-Q with its reason; the harness from E7's; `; sleep 20` and the snapshots kept; the freeze before any sandbox | 3.2, 4, 10, 0, `freeze.txt` |
