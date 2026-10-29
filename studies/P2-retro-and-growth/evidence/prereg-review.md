# P2 pre-registration review (step 1b, `prereg-review`, iteration 3: the scoped review)

**Verdict: CHANGES_REQUESTED** (0 HIGH, 1 MEDIUM, 4 LOW).

**Scope.** This is the scoped review that `manager-decision-prereg-loop.md` binds for iteration 3. For each of F22-F37 I checked, on the
files and the self-check output, that its resolution is complete and correct. I checked every changed file for a regression the change
introduced, and checked that the recorded self-check result belongs to the current code. New findings are raised only where a resolution
is wrong or incomplete or a change breaks something. They continue the numbering from F38.

**Read:** the brief in full; design 17 and 18.1 again at `3d6b28aa` (the other bound sections as in iterations 1 and 2);
`manager-decision-prereg-loop.md`, `manager-decision-prereg-pf.md` (with its iteration-3 addendum) and `prereg-revision-3.md`. Under
`EV` = `studies/P2-retro-and-growth/evidence/`: `protocol.md` (1467 lines; sections 1, 3, 4.2-4.8, 5, 6.6, 8, 11, 12, 16 and 17 in full),
`standing-rules-streams.md` and `products.txt`. In `harness/`: `CHANGES.md` and the changed code (`extract_p2.py`, `lena_lines.py`,
`score_p2.py`, `gate_p1.py`'s delivered-versions part, `stage_gate.py`, the new `score_stream.sh`, `finish_stream.sh`, `skill_move.sh`,
`probe.sh`, `setup_stream.sh`'s cleanup, `next_stream.sh`, `dryrun.sh`'s F31 part, `p2lib.py`, `arm.sh`, `watch_views.sh`). In
`harness-selfcheck/`: `SELFCHECK.md`, `selfcheck-summary.txt`, the new cases in every `.out` file, the dry-run orgs' runtime notes and the
checker-add plan.

**Spot-checks run** (read-only, or in my own scratch folder under `/tmp`):
- every harness file's mtime against the self-check's run time;
- the `wake:` headers and titles of runtime notes to root in P1's kept streams and in the dry-run orgs;
- the product's one-question forms (`grep 'Yes or no' src/hirearchy`);
- a grep of the P2 harness for product imports;
- the memories decision file's name in every file;
- `zsh -n` on `score_stream.sh` and `probe.sh`;
- a 5-line zsh script testing what a script does after a trapped TERM.

No self-check, test suite, product call or stream ran. Nothing in the pre-registration was edited.

**The design line.** `git -C /Volumes/workspace/hirearchy diff -- docs/design/org-growth-phase-2.md` is exactly one added line under the
18.6 heading, the brief's text word for word. **Pass.**

**Severity scale** (as in iterations 1 and 2):
- **HIGH:** a wrong or undeterminable exit verdict in ordinary streams, a safety gap, or a missing required part.
- **MEDIUM:** a gap or contradiction a stream would hit with ordinary assistant behaviour, a check not implemented as written, or a
  breach of a binding rule.
- **LOW:** wording, hygiene, or a record to add.

Line numbers are 1-based, in the files as they stand now.

## Review 2's findings, one by one
| Id | Sev. | Resolution on the files | Case that covers it | Result |
|---|---|---|---|---|
| F22 | MEDIUM | `extract_p2.py:748` `WAKE_WORDS`, `:752` `runtime_wakers` (waking unless `wake: false`; every waking note listed; `budget`, `team`, `limit` alone no longer fail); `protocol.md:868` | `selfcheck_cases.out:140-141` | Resolved. P1's kept notes to root bear it out: `health review` and `lead is out of budget` carry no `wake:` key, and every playbook note carries `wake: false`. |
| F23 | MEDIUM | `FACT_RE` `fact[\s_-]*check` at `extract_p2.py:196`, `names_fact_checker` `:214`, used by `b_check`; `protocol.md:885` | `selfcheck_cases.out:138-139` | Resolved |
| F24 | LOW | One rule at `protocol.md:758` and P2-L step 1 | existing case | Resolved |
| F25 | LOW | `rederive_quality.py` out of 3.5, with the sentence that no P2 check reads it | text | Resolved |
| F26 | LOW | `lena_lines.verdict_after`, `score_p2.delivered_check`, `gate_p1.py:356`; `protocol.md:972`, 16 item 10 (`:1336`) | `score_p2.out:7-9`, `lena_lines.out:19`, `gate_p1.out:22` | Resolved as the manager chose, but the new final-memo check ignores the cut rule: **F38** |
| F27 | MEDIUM | `lena_lines.third_trap`, `condition_turn`; `extract_p2.retro1_before_answer`, called in `x2`; `stage_gate.py`'s constructed L0; `protocol.md:375`, `:572`, `:811`, 16 item 34 (`:1431`); standing rule 15 | `lena_lines.out:4-9`, `selfcheck_cases.out:142`, `stage_gate.out:1` | Resolved. Flags (a) and (b) are sound: (a) puts L0 later, so the answer exists before it; (b) keeps 17.3's memo-5 branch except where it would bring back F27's case. |
| F28 | MEDIUM | K41a, K40 and K41 narrowed, K61 scoped (`protocol.md:511-513`, `:535`), 4.6 "Between the retros" (`:399`), `lena_lines.retro_places`; standing rule 15 | `lena_lines.out:10-12` | Resolved for arm R. K41's arm is unstated: **F40** (LOW) |
| F29 | MEDIUM | `item_open`, `nominated(bp, items, t, m5)`, `item_states`, `memo5_request` (`extract_p2.py:226-325`); 6.6 (`:558`), K44 (`:517`), 16 item 30 | `selfcheck_cases.out:132-137` | Resolved |
| F30 | MEDIUM | K33 open form (`:504`), arm-C K43a lines (`:516`), K53 open form (`:527`), 16 item 37; standing rule 6 | table text | Resolved for the rows named. K33's new open form names the brief, which arm C does not have: **F39** (LOW) |
| F31 | MEDIUM | `finish_stream.sh` `EM_ARGV` with `--product-src $REPO_A/src`; each argv in `finish-steps.txt` | `dryrun-C.out:25-27`, `dryrun-R.out:59-60` | Resolved |
| F32 | LOW | `probe.sh:17` turn 1 asks for the skill; 16 item 36 names the stop risk and the preflight's action | `probe_setup.out` | Resolved |
| F33 | LOW | `skill_move.sh` `ASIDE-PENDING` before the `mv`, open in `unrestored`, closed in `restore` when nothing moved | `skill_move.out` (18 of 18) | Resolved |
| F34 | LOW | `probe.sh:43-49` cleanup in the trap, with a deletion record | `zsh -n` only | Resolved as asked, but a trapped INT or TERM does not stop the script: **F41** (LOW) |
| F35 | LOW | 16 item 23 (`:1384`) states the reading and why | text | Resolved |
| F36 | MEDIUM | New `score_stream.sh`; section 11's ordered gate inputs; item 3 reads `gate_p1.json`'s `FAIL-CLOSED:` values (`stage_gate.py:52-66`); 12.5 uses the same script | `stage_gate.out:11-13` | Resolved. `score_stream.sh` itself never ran in the self-check: **F42** (LOW) |
| F37 | LOW | One name, `manager-decision-memories-before-<label>.md`, in every file (grep: 8 hits, one form) | grep | Resolved |

**The self-check's recorded result belongs to the current code.** The run started at 2026-10-29T08:36:57Z
(`selfcheck-summary.txt`). The newest harness code files predate it: `dryrun.sh` at 08:34:58, and `probe.sh`, `next_stream.sh` and
`p2-judged-template.json` between 08:22 and 08:23. Only text changed after it: `protocol.md` (08:37:13), `harness/CHANGES.md`
(08:41:18), `SELFCHECK.md` and `prereg-revision-3.md` (08:42). The result is `SELFCHECK: 18 of 18 parts passed`, with 156 of 156
constructed cases, 20 of 20 in `lena_lines`, 9 of 9 in `score_p2`, 14 of 14 in `stage_gate`, 24 of 24 in `gate_p1`, 18 of 18 in the skill
move, and 0 mismatches in both dry runs. The first full run's 17 of 18 (the PF-0 timing) is explained in `SELFCHECK.md` "Iteration 3" and
decided by the manager (the addendum to `manager-decision-prereg-pf.md`).

---

## Check 1. The protocol implements 17 and 18.1 completely; every pass rule and check has a mechanical procedure over named files, which fails closed

F22, F23, F24 and F25 are resolved (table above). P2-L step 4 now reads every waking runtime note to root and lists it. Its words follow
design 18.1 ("a brief, a team change or a schedule"), and constructed cases cover both directions. P2-B step 2 matches only the fact-check
pattern, with near-miss cases. One regression comes from F26's new code.

### F38 (MEDIUM). The new final-memo check fails a cut stream on a version Lena rejected, against the cut rule
- **Where:** `harness/score_p2.py:125-146` (`delivered_check`: the loop over `finals`, and the never-judged versions); `protocol.md:972-980`
  (12.3, "Every final memo has 0 extra rows and 0 wrong dates, its trap row included unless the memo was accepted under L-ASIS"; "never
  judged keeps the rule"); `protocol.md:1336` (16 item 10); against `protocol.md:765` (12, Cuts) and `:1006` (12.5: "the parts its end cut
  read NOT DETERMINED").
- **Problem:** Iteration 3 makes `score_p2.py` check final memos, which the code had not done before. A final memo is the file
  `memos/memo-<date>.md` at the end. In a stream ended by the script (`retro-2-done`), every memo's final file is a version Lena accepted, so
  the rule works as the manager meant it. In a **cut** stream it does not:
  - The pre-registered cut paths are a cap, a ruling that ends the stream, the stage-2 credits stop, and a stop. A cut can leave the memo in
    progress with its last delivered version rejected. For example, a stream cut by `cap-runs` during the rework after a TRAP-N rejection,
    or ended by ruling (b) on root's question for that rejection, keeps the rejected version as the memo's final file.
  - `delivered_check` then counts that file's wrong Dues with the trap row included, because the memo was not taken under L-ASIS. A
    TRAP-rejected final therefore always fails. That wrong Due is the event the script plants.
  - A version delivered in the cut turn and never judged also keeps the rule (`lena` is None), so a slip in it fails as well.
  - `gate_p1.py` then reads `delivered versions (P2's form)` as `FAIL`. Under 12.5 one gate-able FAIL in a valid stream makes Phase 2's
    exit **FAIL**. Without this check, such a stream's exit would read NOT DETERMINED: its later X1 and X2 steps wait for retro 2.
  - This contradicts 12's cut rule, which binds gate-able measures too (12.5; G2(b) applies it explicitly). It also contradicts the
    manager's reason for F26: "a slip that Lena's scorer rule rejects is the contract loop working, not a regression".
  - Before iteration 3, a TRAP-rejected final in a cut stream passed, because the trap row was excluded and finals were not checked. The
    change has turned it into a FAIL.
- **Resolve** (code plus cases, with the self-check re-run):
  1. A final memo keeps the rule when the last Lena line that judges that memo is ACCEPT or L-ASIS (`lena_lines.verdict_after` over the
     memo's last judging line).
  2. When that last line is a rejection (H6, VR-REJECT, TRAP-1, TRAP-N, A-M), or no line judged the memo:
     - in a cut stream (`extract_p2.end_of(...)["cut"]`), the final memo reads `NOT DETERMINED (cut at turn <n>: the memo's last version
       was rejected or not judged)`;
     - with no `end.txt`, it reads `NOT DETERMINED (FAIL-CLOSED: the stream's end is not recorded)`;
     - in a `retro-2-done` stream, where this cannot happen by the script, it reads FAIL as written.
  3. Apply the same rule to a version that was never judged: NOT DETERMINED (cut) when the end cut its verdict, otherwise it keeps the
     rule.
  4. Have `gate_p1.py` carry that NOT DETERMINED into `delivered versions (P2's form)`, with no fail-closed prefix in the cut case, so the
     stage gate lists it as information.
  5. Write the rule into 12.3 and 16 item 10.
  6. Add `score_p2.py --selfcheck` cases:
     - a cut stream whose memo-4 final is the TRAP-N-rejected version (NOT DETERMINED (cut));
     - a cut stream whose last version was never judged and has a slip (NOT DETERMINED (cut));
     - a `retro-2-done` stream whose accepted final has an extra row (FAIL).

---

## Check 2. The script makes its events happen whatever the team writes; the keys are consistent with every criterion in force

F27 is resolved. I traced `lena_lines.condition_turn` against the protocol's text:
- **What L0 now is.** L0 is the first line after the third distinct trap memo's TRAP rule whose rows hold K29, K30, K30c or K47a and whose
  facts carry `answers <that rule>`.
- **The fallback.** When root asks no question first, L0 is the first later line that judges a delivered version. That line comes after
  any answer, so the third case is recorded before L1.
- **Memo 5's branch.** It stays, except when memo 5's first verdict is itself the third TRAP line (`b = None` when the turn equals T3).
- **Why the answer is in place before L1.** Root records the answer in L0's own turn. So the reply to L0, which can offer the retro that
  L1 answers with RETRO-YES, comes after the class reaches three.
- **The residual case.** When root records the brief before the answer even so, P2-X2 step 1 reads NOT DETERMINED and names the calls
  (`retro1_before_answer`, case `selfcheck_cases.out:142`).
- **The other rows.** K30b is not in `ANSWER_ROWS`, but the product asks only `About {id}: add ... as a lasting rule? Yes or no.` and
  `Same as {id}: a one-off? Yes or no.` (`src/hirearchy/reflection/_steps.py:14-16`, read for this check only). So the rows that can answer
  a trap rejection are all listed.
- **Arm C.** Arm C's L3 is counted from the same L0, and standing rule 15 says so.

The F26, F28, F29 and F30 changes leave every other event and key as iteration 2 had them (three ACT-REQ lines before the earliest L0;
A-W, A-P, A-R and A-M; the trap's Dues; the A-M both-orders case). No finding.

---

## Check 3. The decision table covers every question the brief, the extension and the plan can ask, with no improvisation, and every yes/no question gets a yes or no line

F28, F29 and F30 are resolved for the cases they named:
- K41a covers offers between the retros, and K61 is narrowed so the two do not overlap.
- Retro 2's place includes the week list's delivering reply, and `retro_places` flags misplaced retro lines.
- K44 approves only a plan for an item that is still open, and K48 refuses the rest.
- K33, K43a and K53 now answer open questions with a value line.

Two edges of these changes are left.

### F39 (LOW). K33's new open form names "the brief's order", which arm C does not have
- **Where:** `protocol.md:504` (K33: "an either/or or open question about that order or pace" -> `In the brief's order, one at a time.`),
  `protocol.md:1451` (16 item 37), `standing-rules-streams.md:32` (rule 6).
- **Problem:** K33 is scoped to "a brief's items or plans". In arm C, Lena says yes to both proposals (K51, K52) at the arm-C turn. A
  question such as "Which shall I do first, the service or the checker?" then has no row. The new line would not answer it either, because
  arm C has no brief. This is the same kind of gap F30 fixed for K43a. After R1's first turn no line can be added (section 0), so such a
  question would end the C stream by ruling (b).
- **Resolve:** Add an arm-C form to K33: an either/or or open question about the order of the changes she said yes to (K51, K52) gets
  `In the order you proposed, one at a time.`, recorded `K33 (arm C open form)`, rule `ANSWER`. Name it in 16 item 37 and standing rule 6.
  This is a text-only change.

### F40 (LOW). The retro-offer rows leave arm C's offers unstated
- **Where:** `protocol.md:511-513` (K40 and K41a read "arm R"; K41 names no arm), `protocol.md:391` (4.6: "Arm C ... no offer can come; L3
  carries RETRO-ASK"), `protocol.md:552` (D-RETRO-OFFER includes "a review").
- **Problem:** F28 narrowed K40, K41 and K41a and marked K40 and K41a as arm R. K41 names no arm, so it applies to arm C as written. An
  arm-C assistant can offer "a review" before L3, which D-RETRO-OFFER counts as an offer. Before L0 no row answers it. In L1 or L2, K41
  gives RETRO-YES, while 4.6 and 16 item 11 put RETRO-ASK at L3 "always". The facilitator would have to choose between them.
- **Resolve:** Write arm C's rule. Recommended: an arm-C offer is answered by the same rows as arm R's (K40 before L0; K41 in L1 or L2,
  and that line is then the arm-C turn, so L3 carries no RETRO-ASK; K41a after it). Record it in `retro-offers.txt` as the arm-C
  assistant's own offer. Mark K41 "both arms", and change 4.6's "no offer can come" to "an offer is answered as in arm R". The other
  choice: every arm-C offer before L3 gets RETRO-NOT-NOW and L3 keeps RETRO-ASK. Either is a text-only change. Write the choice and its
  reason in 16 item 11.

---

## Check 4. The re-derivation is independent of the product's source, and its self-check passes

**Passes.**
- **Independence.** `harness/CHANGES.md` ("Iteration 3") states that the author opened no product source file in iteration 3. The new
  readings cite the design's text and kept evidence (runtime-note headers, dry-run files). A grep of the harness finds no new product import.
  The only ones are `dryrun_build.py`'s `Org` facade, used to drive throwaway orgs, and P1's `extract_mechanical.py` `client_questions`,
  now taken from the arm's own product (F31).
- **PF-0.** The corrected mechanism is a product finding, recorded and decided by the manager (`manager-decision-prereg-pf.md`, addendum).
  It is not imitated in the harness: the signature is unchanged, and the re-derivation keeps the design's labels.
- **The self-check.** It passes on the current code (see "Review 2's findings").

No finding.

---

## Check 5. The arms differ only by the product and its skill

F31 is resolved: the finish's `extract_mechanical.py` call names `--product-src $REPO_A/src`, and the arm-C dry run proves it resolves to
the worktree (`dryrun-C.out:25-27`). `KIRO_HOME` is unset in every chat and product call, as before. One template still gives both arms'
profiles, masked as in 16 item 25. The probe's new turn 1 is the same text in both arms (`probe.sh:17`), and the skill proof is unchanged.
`score_stream.sh` sources `arm.sh` but makes no product call; its four steps are harness modules that read only evidence. No finding.

---

## Check 6. Safety

F33, F34 and F35 are resolved as asked:
- `ASIDE-PENDING` is written before the `mv`, and `status`, `restore` and `recover` treat it as open.
- A pending move whose `mv` never ran is closed only when the copy is in place with its md5.
- A partly copied aside, with the source still present, stops with `skill restore impossible` and changes nothing.

Nothing new writes the owner's `~/.kiro`, the user's org or another skill, and nothing reads a credential.

### F41 (LOW). A trapped INT or TERM runs the cleanup, and then the probe goes on
- **Where:** `harness/probe.sh:43-49` (`cleanup`; `trap 'cleanup' EXIT INT TERM`); the same pattern in `harness/setup_stream.sh:62`
  (`trap 'cleanup' INT TERM`, F19 of review 1).
- **Problem:** In zsh, a string trap on INT or TERM runs its command and then resumes the script. My scratch test showed this: a script
  with `trap 'cleanup' EXIT INT TERM` that received TERM printed the cleanup line and then "continued-after-sleep", exit 0.
  - **In `probe.sh`.** After F34, an interrupted arm-C probe run deletes its profile and restores the skill, as F34 asked. Then it carries
    on: it runs turn 2 against a profile that no longer exists (kiro-cli fails on an unknown agent), and goes on to the later sessions.
    Those move the skill aside again and spend credits, after someone tried to stop the probe. The result reads `PROBE: STOP` (NOT
    PROVED), so nothing unsafe follows, and the skill is back after each run.
  - **In `setup_stream.sh`.** An interrupted arm-C setup restores the skill and then completes the setup with the global skill in place.
    Turn 1's `after_turn.sh` then stops the stream as H2, which wastes a stream.
- **Resolve:** End each signal trap with an exit: `trap 'cleanup; exit 130' INT TERM` together with `trap 'cleanup' EXIT` in `probe.sh`,
  and `trap 'cleanup; exit 4' INT TERM` in `setup_stream.sh`. Add a `selfcheck.sh` case: a stub script with the same trap lines receives
  TERM, and the case checks that the stub ran its cleanup and exited without running its next command.

---

## Check 7. The stage gate and the stop rules are exact, and every cost figure traces to 17.6

**The figures and the stop rule** in section 11 are unchanged from iteration 2, and still trace to 17.6:
- per stream, 78-112 and 75-105 runs, 125-200 and 115-190 credits;
- stage 1, 240-390 credits, 260-420 with the preflight, 153-217 runs;
- stage 2, 480-780 credits;
- in total, 740-1200 credits and 463-659 runs;
- the cap of 140 runs (1.25 x 112), the stage-1 `> 250.00` and the stage-2 `STOP-CREDITS:` at 260.

**F36 is resolved.** Section 11 now gives the gate's inputs in order: `score_stream.sh R1`, `score_stream.sh C1`, then `stage_gate.py
EV`. Item 3 reads both `p2/verdicts.txt` and `p2/gate_p1.json` for the `FAIL-CLOSED:` prefix, and a judged key's NOT DETERMINED is
information. The three new cases pass. A failed `extract_p2.py --checks` leaves no `verdicts.txt`, which item 3 reads as unread, so the gate
fails closed. F37 is resolved.

### F42 (LOW). `score_stream.sh` never ran before the freeze
- **Where:** `harness/score_stream.sh` (new in iteration 3); `harness/selfcheck.sh` and `harness/dryrun.sh` (neither calls it: `dryrun.sh:274-290`
  runs the four commands directly).
- **Problem:** The gate's and step 12's inputs now depend on a driver no run has executed. That driver holds the A-M time extraction (an
  inline Python heredoc inside `$(...)`), the `run` wrapper and its `score-steps.txt` record, and the `sandbox-path.txt` gate. It passes
  `zsh -n`. Its label must be a stream label, because `D=$EV/$LABEL` is fixed by `arm.sh`, so it cannot run on the dry run's folder as
  written. A bug would show only at step 6, after R1 and C1 have been spent. It fails closed there (item 3) and the gate always asks the
  manager, so it costs a loop-back, not a wrong verdict. Design 17.5 binds a dry run of "every reader" before the freeze.
- **Resolve:** Let `score_stream.sh` accept the evidence folder of a `selfcheck-*` label from `P2_EVDIR`, as `copy_org_evidence.sh`
  does. Run it in `dryrun.sh` in both arms in place of the four direct calls. Check that `score-steps.txt` lists four `exit 0` lines, and in
  arm R that `--am-time` was passed when the constructed `lena-lines.txt` holds an A-M line (or that it was left out when none exists).

---

## Verified assumptions
- The design diff is exactly the one 18.6 line, with the brief's text.
- `products.txt`: arm R `3d6b28aa...` on `main`; arm C `aac6af1b...`, a clean detached worktree; the skills `443e1bc4...` (R, equal to
  the owner's global copy) and `b1023863...` (C).
- The self-check's recorded result (18 of 18 parts) belongs to the current code: every code file predates the 08:36:57Z run.
- The product writes no `wake:` key on a waking runtime note and `wake: false` on a quiet one. Seen in P1's kept notes to root (health
  review and out of budget: no key; 14 playbook and watch notes: `wake: false`) and in the dry-run orgs (`A checker joined your team`: no key).
- The product's one-question forms for a rejection are `About {id}: add ... as a lasting rule? Yes or no.` and `Same as {id}: a one-off?
  Yes or no.` (`src/hirearchy/reflection/_steps.py:14-16`), so `ANSWER_ROWS` (K29, K30, K30c, K47a) covers every answer to a trap
  rejection's question.
- The dry run's checker-add plan (`dryrun-R/ext-2-checker-add.json`) uses template `reviewer` and a C6 `charter_extra` with no
  fact-check words. So the product's own path does not trip F23's pattern.
- In arm C, `finish_stream.sh`'s `extract_mechanical.py` imports `client_questions` from the worktree (`dryrun-C.out:26`).
- `score_stream.sh` and `probe.sh` pass `zsh -n`. The memories decision file has one name everywhere.
- In `extract_p2.checks`, a failed `rederive_p2.py` raises, leaves no `verdicts.txt`, and the gate's item 3 reads that as unread
  (FAIL-CLOSED).
- The cost figures and the stop rule trace to 17.6 (check 7).

## Unverified or wrong assumptions
- **Wrong:** that "every final memo" is always a version Lena accepted. In a cut stream it can be a rejected or unjudged version (F38).
- **Wrong:** that a trapped INT or TERM stops `probe.sh` or `setup_stream.sh`. zsh resumes the script after the trap (F41).
- **Unverified:** that `score_stream.sh` runs correctly. It never ran (F42).
- **Unverified:** that the arm-C assistant never offers a retro or a review before L3. 4.6 assumes it, and K41's arm is unstated (F40).
- **Unverified (carried from iterations 1 and 2, reported, not a finding):** that the assistant delegates each action list as a one-off
  rather than writing it itself (X1 then reads NOT DETERMINED), and that the probe's new turn 1 makes kiro load the skill (16 item 36 names
  the stop risk and the preflight's action).

## Findings at a glance
| Id | Sev. | Check | Where | In one line |
|---|---|---|---|---|
| F38 | MEDIUM | 1 | `score_p2.py:125-146`; `protocol.md:972-980`, `:1336`, `:765`, `:1006` | The new final-memo check fails a cut stream on its rejected or unjudged last version (a TRAP-rejected final always), making the exit FAIL against the cut rule |
| F39 | LOW | 3 | `protocol.md:504`, `:1451`; standing rule 6 | K33's open form names "the brief's order"; arm C's order question after K51 and K52 has no row |
| F40 | LOW | 3 | `protocol.md:511-513`, `:391`, `:552` | K41 names no arm; an arm-C offer before L3 has no row, or K41's RETRO-YES conflicts with 4.6's L3 rule |
| F41 | LOW | 6 | `probe.sh:43-49`; `setup_stream.sh:62` | A trapped INT or TERM runs the cleanup and then the script goes on (turn 2 without a profile; a setup with the skill restored) |
| F42 | LOW | 7 | `score_stream.sh`; `dryrun.sh:274-290` | The gate's new input driver never ran in the self-check |

**The count:** 0 HIGH, 1 MEDIUM (F38), 4 LOW. The verdict is mechanical: **CHANGES_REQUESTED**. By the manager's decision there is no
iteration 4. F38 is code (`score_p2.py`, `gate_p1.py`, with cases and the self-check re-run). F39 and F40 are text-only. F41 and F42 are
small code changes with one case each.
