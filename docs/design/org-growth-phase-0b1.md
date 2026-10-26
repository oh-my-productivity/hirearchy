# Org growth, Phase 0b.1: the batch after G0 (technical design)

Status: design, revision 2 (the 14 findings of the design review's pass 1 resolved; responses in 13). Branch `feat/org-growth-phase-0b1` off `main` `c68ae679` (the G0 study commit; product code identical to `3c841bb9`);
worktree `/Volumes/workspace/hirearchy/.worktrees/org-growth-0b1`. Baseline: `skills/hirearchy/SKILL.md` has 125 lines, md5
`a3e46347b70a7ece5f734f70198c607f`; this batch does not edit it unless F-G0-7 is the product's (9).

Sources, read in full for this design:
- **The brief:** `/Volumes/workspace/hirearchy/docs/research/org-growth/phase-0b/0b1-brief.md` (scope items 1-5, constraints, steps).
- **Binding:** `studies/G0-noise-baseline/STUDY.md` (F-G0-1 to F-G0-14, "The view against the re-derivation", "What Phase 1 must know" item 4);
  its `evidence/` (m0-s1, m0-s2, m1-s3, `harness-selfcheck/SELFCHECK.md`, `protocol.md` 3.5, `harness/rederive_quality.py`); and
  `evidence/manager-decision-selfcheck.md` ("the ruling": item 2 is the F-G0-1 rule, item 3 the E7S3-6 correction).
- **Design:** `docs/design/org-growth-phase-0b.md` ("0b": 3, 4.2-4.5, 19, 26); `org-growth-phase-0a3.md` (4.2, I1) and `org-growth-phase-0a5.md`
  (A2, 4.7) for `user_spend`, `user_committed`, `user_granted` and the approval.
- **Rules:** `ARCHITECTURE.md` (R1-R13, single writer, derived state) and `docs/refactor-principles.md`.

Abbreviations: `SRC` = `src/hirearchy`, `TESTS` = `tests`, `EVG0` = `studies/G0-noise-baseline/evidence` (tracked, read-only). Ids are shortened to
their last 4 characters where the stream is clear; a test pins the full id. Every function named below was read at `c68ae679`.

## 1. Overview

G0 found three product defects and one design error, and left one arm difference unexplained. 0b.1 fixes the defects, verifies each on G0's kept
files, corrects the design text, and investigates the arm difference. **F-G0-2:** `user_spend` and `case_spend` leave out the runs a user grant
still holds, so a blocked case reads 13 of 14 where 0b section 3 gives 14 of 14. **F-G0-1:** when a head task's late `done` result and its human
rework's result hold the same checked file, P3 names the newest (the head, unjudged), so the case reads "without a verdict" though the user judged
the rework. **F-G0-3:** `progress` raised `FileNotFoundError` on a result that `inbox` moved between the listing of root's boxes and the read.
**E7S3-6:** 0b 19.3 claims that replay and history agree for E7 s3; with history they do not. **F-G0-7:** every M0 stream had 15-19 failed
`tool_call` calls with empty arguments and no M1 stream had any; the cause is found from G0's raw evidence and fixed only if it is the product's.
Nothing new is stored: no ledger, no state, no message field, no event, no new refusal and no new runtime dependency. SKILL.md and every MCP tool
docstring are unchanged (unless F-G0-7's cause is in them). P3's notes in `progress`, `status` and `whoami` change in one way only: a `relayed`
line can name the tie rule's chosen delivery instead of the head's late result; its words are unchanged (4.4). **One pre-registered expectation moves under F-G0-2 (3.5); the manager ruled it
(R-0b1-1, 12): it is amended in the fix commit, under stated conditions.**

## 2. Technology stack (locked)

Python 3.11, the existing packages only; pytest; `git` in the e2e tests that already use it (`test_org_growth_0b_given.py` pattern: skipped when git
is not installed); uv, `mypy==2.4.0 --strict`, `import-linter==2.15`, `scripts/check.sh`. No new package, no new dependency edge
(`tests/architecture/graph.py` untouched), no new runtime dependency. Strict TDD (R11), one logical change per conventional commit, under the owner's
test policy (10).

## 3. F-G0-2: held user grants count in the user's runs and in the total

**3.1 The rule.** While a case is open or blocked, the runs of a user grant (`Case.user_granted`: root's notes with `budget` to the team inside a
user interval, 0a.3) that were neither used nor returned are runs the team still holds for the user. `user_spend` and `case_spend` count them as
`user_committed` and the approval's ceiling (`_cases._spend`) already do. A finished case (`done`, `failed`) holds nothing; its figures do not change.

**3.2 The change** (`SRC/reflection/api.py`, pure functions; their docstrings add "and the user's grants"):
```python
def case_spend(case: Case) -> int:
    still_out = 0 if case.state in ("done", "failed") else max(0, case.budget + case.user_granted - case.runs - case.returned)
    return case.runs + still_out


def user_spend(case: Case) -> int:
    if case.state in ("done", "failed"):
        return case.runs - case.relayed_runs
    return user_committed(case)  # the user's runs, plus what the user's requests and grants handed down and nobody used or got back
```
`user_cost`, `user_committed`, `user_held`, `user_approved` and `_cases._spend` are unchanged (`user_committed` is defined below `user_spend`; the
call resolves at run time). This makes the code match 0b section 3 and 4.2 as written ("the user's runs the team still holds"; "the runs handed
down that were neither used nor returned"). It supersedes, as written there: 0a.1 6.1's `case_spend` (the tasks' runs still out only); 0a.3 4.2's
"user spend" row (the tasks' budgets only) and the first clause of 0a.3's I1 ("`case_spend` is unchanged"); and 0b 3's `case_spend` row ("0a.1 6.1,
unchanged"). Those documents are not edited; the one design text this fix edits is 0a.5 4.7's row, under R-0b1-1 (12).

**3.3 Zero and empty cases.**
- No grant (`user_granted == 0`: every agent client's case, every hand-built `Case`): both functions return today's value.
- `done` or `failed`: today's value.
- A grant used up or given back: `max(0, ...)` adds 0; the figure is never below the runs used.
- A grant inside a relayed rework's interval is no user grant (0a.3): it changes neither function (declared limit, 11).
- A result that returns more than its own task's budget counts at most that budget (0a.1's `returned`), so returned grant runs above it still read
  as held: the rule `user_committed` and the ceiling already follow.
- 0a.3's I1 still holds: with no relayed task, `user_spend == user_cost == case_spend` (both sides add `user_granted`); its property test is
  extended with grants. New invariant: `user_spend == user_committed` while the case is open or blocked.

**3.4 What it changes.** The quality view's `user_cost`, `spend`, `ratio` and cost line of an open or blocked case with held grant runs; the cost
alarm's comparison and `total`; `case_total`'s overspend sentence for a human client (`user_cost` against `user_approved`). `case_total`'s head
`N runs used of M handed down` (`M` = `Case.budget`, the tasks' budgets) is **not** changed (11, backlog). In G0's kept end views exactly one case
has a held grant: m0-s1 `6c7a` (m1-s3 `b5e4`'s grant is on a `done` case).

**3.5 The replays it moves (computed for this design).** Old and new formulas were evaluated on every case of every materialization the e2e tests
make: the 16 corpora of `org_replay_manifest.MANIFESTS` at their end, and the 26 time cuts of `test_org_growth_0a3.py` (E5), `0a4.py` (E6) and
`0a5.py` (E7) (a one-off script, not kept). The 16 are the 16 keys of `MANIFESTS` (E, E2, A5, E3, E4-s1r, E4-s2r, E4-s3, E5-s1 to E7-s3). E3's two
constructed `VARIANTS` (`r2-links-r1`, `r3-overspend-<N>`) are not among them and were not computed: they add a link note without `budget` and empty
run logs of `lead` to E3, which has no grant, so `user_granted` stays 0 and 3.3's first rule leaves both figures as today. Every grant case at a corpus end is `done` (E `c686`, A5 `f768`, E4 s3 `6947`, E5 s3 `e268`, E6 s3 `4a3e`,
E7 s1 `fb17`, E7 s2 `3ca4`): 0 moves. Four time cuts move:

| Cut | Case | Old -> new (`user_spend`, `case_spend`) | What the test there asserts |
|---|---|---|---|
| E6 s3 `20261024T172627799242`, `...172724489270` | `4a3e` open, grant 4 | (12, 18) -> (16, 22); (14, 19) -> (16, 22) | `work_tier` only: no expectation |
| E7 s1 `20261025T072625893903` | `fb17` blocked, grant 3 | (9, 9) -> (11, 11) | prompt headings only: no expectation |
| **E7 s2 `20261025T075138446837`** (after the grant 68df) | `3ca4` open, grant 1 | **(13, 13) -> (14, 14)** | **`test_a2_e7_s2_the_grant_68df_approves_13`: `user_cost == 13` and no "exceeds"/"more than" in `case_total`** |

The last row is a pre-registered expectation (0a.5 4.7, row "after the grant 68df": "approval 13; `user_cost` (open) 13: no sentence"). With the
fix the user's requests hold 9 used + 3 (the head's) + 1 (c671's default run) + 1 (the grant) = 14 against the 13 approved, and `case_total`
reads `case total: 9 runs used of 13 handed down (contract: 12 per request). The user's requests now cost 14 runs, more than the 13 the user approved
for this case (contract: 12 per request, plus 1 approved beyond it): tell the user.` (`OVER_APPROVED`), the figure and sentence that #24 prints two
minutes later on the same case. 0a.5 computed 13 with the arithmetic F-G0-2 corrects. The brief says never to edit an expectation to match, so
the design stopped and asked: the manager ruled **R-0b1-1: yes** (12). The approval of 13 stays; only the cost and the sentence change.

**3.6 Tests.**
- RED, then GREEN: `TESTS/e2e/test_org_growth_0b1.py::test_f_g0_2_m0_s1_memo_3_holds_the_grant_run_14_of_14`, on the G0 kit (6) at `m0-s1`, cut
  `20261026T052934311534` (root's accept `...-root-00d1`, the last kept message; no run log after it). Case `20261026T051850834033-root-6c7a`: state
  `blocked`, `runs` 13, `relayed_runs` 0, `user_approved` 14, top-ups `+3 human ...-root-492d`, `+2 granted ...-root-7ea7`; **`user_cost` 14,
  `spend` 14, `ratio` `"1.00"`, cost line `14 of 14 approved (1.00x)`** (at `c68ae679`: 13, 13, `"0.93"`). Evidence facts asserted on the kept files in
  the same test: 9 run logs in 6c7a's interval, 3 in 492d's before the grant, 1 after it (`run-logs/`); the final `status` line `lead ... budget=1`
  and the lead's note `...-lead-5372` ("I hold 1 run besides this one"). The other cases do not move (`ece7`: `user_cost` 15 of 15, relayed 5, spend
  20; `a7ef`: 8 of 12, `"0.67"`). `case_total` of 492d stays `case total: 13 runs used of 15 handed down (contract: 12 per request)` (14 is not above 14).
- Unit (`SRC/reflection/tests/test_pure_functions.py`): `case_spend` and `user_spend` with a grant per state (open, blocked: counted; done, failed:
  unchanged); a grant used up; a relayed task beside a grant; I1 with grants (the `CHAINS` x `NUMBERS` property, `user_granted` 0 and 3);
  `user_spend == user_committed` while open or blocked.
- Integration (`SRC/reflection/tests/test_cases.py`), the 6c7a shape in the fs world: head 12, 9 runs, `done` returning 3; human rework 3, 3 runs,
  `blocked`; a grant of 2; 1 more run: `user_granted` 2, `runs` 13, `user_spend` 14, `case_spend` 14, `user_committed` 14, `user_approved(case, 12)` 14.
- The amended replay (R-0b1-1, 12): in the fix commit, `test_a2_e7_s2_the_grant_68df_approves_13` becomes
  `test_a2_e7_s2_the_grant_68df_cost_14_over_13`, asserting `user_approved(case, 12) == 13`, `user_cost(case) == 14` and `case_total(c671)` equal to
  the text of 3.5. Its docstring says the published 13 was superseded by 0b.1 F-G0-2 (R-0b1-1) and decomposes the 14 in 12's words (condition 3). It is RED at `c68ae679` (13) and GREEN with the fix.
- No existing unit test pins today's figure for an open or blocked case with a held grant (searched: `test_cases.py`, `test_pure_functions.py`,
  `test_alarms.py`, `test_steps.py`, `progress/tests`). If the build finds one, the fix commit changes it and names it with the old and new value;
  a pre-registered replay value is never such a pin (7).

## 4. F-G0-1: the given delivery when the file equals several deliveries

**4.1 The rule** (the ruling, item 2, as `protocol.md` 3.5 states it and `harness/rederive_quality.py:_attributed` implements it). OQ-2's given
delivery is the delivery whose checked artifact equals the user's file. When deliveries of the case qualify, it is the one that carries a human-tier
verdict (of several, the newest result among them). When none carries one, it is the latest: the one P3's `relayed` finding names, or, with no
finding, the case's latest delivery (`_quality_rules._given`'s fallback), as today. This supersedes, as written there: 0b 3's "given delivery"
row and 0b 4.3's "without a verdict" row (the delivery a `relayed` finding names, else the case's latest delivery), which now read with the tie rule
in front; and the `DeliverableFinding.kind` lists of 0a.3 (DR-0a3-6: the `kind` comment gains `relayed`) and 0b (B4.8: `written` is set for
`differs`, `relayed` and `unknown` only), which gain `given` (4.4; `written` is set for it too). Those documents are not edited.

**4.2 Where.** Only P3 knows checked artifacts, so the rule is applied in `SRC/reflection/_deliverable_checks.py:FolderDeliverableChecks._folder_rule`,
the site the brief names; `_records._attributed` keeps only flagging the delivery a finding names. A records-side choice was rejected: records sees
findings, not checked artifacts.

**4.3 The walk, changed at one point.** `_folder_rule` walks the pairs of the file's name, newest result first, as today. At the first pair `P` whose
checked version equals the file:
1. The rule applies only when `P.case` is not None and `P`'s version came from git: the key is in the new `_Call.from_git: set[tuple[str, str]]`,
   added by `_checked` when `CheckedVersions.at_result` answered. Otherwise today's code runs.
2. `chosen` = `P` when `P` carries a human-tier verdict; else the first later pair `Q` (newest first) with `Q.case.id == P.case.id`, the same file
   name, a git-given checked version equal to the file, and a human-tier verdict; else None. "Carries a human-tier verdict" is
   `any(v.tier == "human" and v.task_id == Q.task.id and v.message.id > Q.result.id for v in Q.case.verdicts)`: a verdict on that delivery
   (`deliveries_of`'s rule; counted or voided). One given on an earlier blocked result is on no delivery (D4).
3. A differing relayed pair was walked past (`newest is not None`): return `("relayed", chosen or P, relayed_ids)`; `relayed_ids` are today's.
4. `P` is the newest pair: when `chosen` is not None and `chosen.task.id` differs from the case's latest delivery (the new private
   `_latest_delivery(case, call.latest)`: the last task of `case.tasks` whose latest result is `done`, the delivery `_given` falls back to), return
   `("given", chosen, ())`; otherwise `("", None, ())`, as today.

The scan of step 2 runs only when `P` carries no human-tier verdict and covers pairs of the same file name and case: a few more `at_result` calls.
They count against the call's existing bound of 40 pairs and 5 s, so in a folder with many files the files walked later can reach the fallback to
the team's current file sooner than today (a declared limit, 11).

**4.4 The `given` kind, P3's notes and the fake** (new value of `DeliverableFinding.kind`; `task` names the chosen delivery; `written` and `settled`
as for `relayed`). It says the file is as delivered and names the given delivery. `_entry` returns it **only when `call.settled` is true** (the
quality view's one call: `records()` asks `findings(ROOT, None, settled=True)`), whatever its own `settled` mark; P3's notes in `progress`, `status`
and `whoami` call without `settled` and never see it. `_records._attributed` treats `given` as `relayed`: the delivery it names is the given one; it
voids nothing and is not counted. `api.py` documents the kind on `DeliverableFinding.kind` and `.task`, and documents on `DeliverableChecks.findings`
the Protocol rule "a `given` finding is returned only with `settled=True`". It is emitted only when it changes the given delivery (step 4), so a file
equal to the case's latest delivery yields no new finding.

**P3's notes and a `relayed` tie.** Step 3 applies in every call, the default one included, so that P3 names one delivery for one file in every
view. A `relayed` finding that the default call shows (one that is not settled: no human-tier verdict on its case at or after the file's last write)
can therefore name the tie rule's chosen delivery, an older equal delivery with a human-tier verdict, where today it names the head's late result.
That happens when the user's verdict on that delivery was recorded before the user's copy was written (she accepted `b`, then the assistant copied
it, then the head's late result and a relayed rework followed). The line's words (`_relayed_line`) are unchanged; only its task id differs. This is
the one change to the notes' content (1); `deliverables_note` and its texts are otherwise unchanged. Applying step 2 only when `call.settled` is true
was rejected: the notes would then name a delivery the quality view does not, for the same file.

**The fake.** `reflection/testing.py:FixedDeliverableChecks.findings` keeps the rule too: it returns `f` when `(settled or (not f.settled and
f.kind != "given")) and (service is None or service in f.services)`, and its docstring says so. Without it a test could get a `given` finding from a
default call, and `deliverables_note` would render it inside a "not what the team delivered as checked" block (R8; refactor-principles "L").
`DeliverableHarness` gains `populate_given: Callable[[], str]`, used instead of `populate`: afterwards root's `weekly-brief` has exactly one finding,
of kind `given`, not settled, naming the returned task id. `deliverable_checks_fixed` puts such a finding (`settled=False`).
`deliverable_checks_fs` builds the real class itself, `FolderDeliverableChecks(w.s.catalog, w.history, w.s.d.mail, FsDeliverableFolder(), versions,
HashBlobIds(), w.s.d.clock)` with a `FixedCheckedVersions` it holds, instead of `w.deliverables`: `_world` builds `w.deliverables` the same way with an
empty `FixedCheckedVersions`, so `populate`'s `unknown` finding is unchanged. Its `populate_given` builds the m0-s2 shape (4.8) over the fs world:
root asks (`a`); `ceo` answers `a` `blocked`; root's human rework `b` (`revises` `a`); `ceo` answers `b` `done` listing `ceo/work/memo.md`
(`at[(b's result, path)]` = V2); `ceo` answers `a` `done` listing it (`at` = V2, the head's late result); root's human accept on `a`; then the user's
`deliverables/memo.md` is written with V2 and an mtime one day after the fake clock's now, after the accept, so the finding is not settled.

**4.5 Why git-given versions only.** Without git (every replay, and every pair past P3's bound), `_checked` falls back to the team's current file, so
every delivery that lists the file name reads the same version and "ties". The rule would then choose by verdicts alone among versions nobody
checked, not by what the team checked. So no candidate is added where git did not answer; the replays without history are untouched by
construction.

**4.6 Zero and empty cases.**
- One delivery equals the file: `P` is the only candidate. With a human verdict and `P` the case's latest delivery: no finding, as today; with a
  human verdict and a later delivery that does not list the file: `given` names `P` (4.1's first sentence). In the 23 given-delivery choices the
  harness made on G0's 6 and E7's 3 streams (`given_deliveries` in each `rederived.json`) this form never differs from P3's.
- Several equal, none with a human-tier verdict: today's result (`relayed` naming `P`, or no finding and the case's latest delivery).
- Several equal, one or more with a human-tier verdict: the newest result among those with one.
- Only relayed- or agent-tier verdicts: not human; ignored.
- An equal pair of another case, or a one-off pair (`case` None): never a candidate; a one-off `P` keeps today's choice.
- No git, or the bound exhausted: no candidate beyond today's walk.
- A pair whose checked version is unknown on both sides: dropped, as in the walk.
- `_file_rule` (a contract that names one file) is unchanged (11).

**4.7 Effect on the kept evidence.** Of the harness's 23 choices (15 in G0, 8 in E7), 1 differs from P3's: E7 s2's `3ca4`, which the fix moves to `c671`. In m0-s2 the
pattern (head `6f1d`'s late `f5df` and `52e3`'s `e876`, in one commit `0491b2b`, both v2) changes no count: at T4 neither has a verdict; from T5 on
the case is blocked and Lena's reject `...-root-02c4` is on `52e3`, the case's latest delivery; from T8 the file is v4, equal to neither, and the
`differs` finding still names the newest pair (the rule is about equal files only).

**4.8 Tests.**
- Real git, `TESTS/e2e/test_org_growth_0b_given.py` (its helpers `commit`, `deliver`, `judge`, `record_of`; `deliver` gains `status="done"` and
  `commit=True`: with `commit=False` it reports without committing, so that two results can share one commit), new fixture `tie` of E7 s2's shape:
  head `a` reported `blocked`; human rework `b` (revises `a`) delivered with V2; the lead then reports `a` `done` listing the same file, unchanged
  (the head's late result); relayed rework `c` delivered with V3. Each delivery is committed as today. Each test writes the user's copy (V2) itself.
  - `test_the_head_s_late_result_ties_with_the_rework_the_user_judged_and_her_verdict_decides` (the copy, then Lena's reject and accept on `b`, the
    relayed reject on `c`): one finding, `relayed`, task `b`, relayed `(c,)` (at `c68ae679`: task `a`); `unjudged_cases []`, `relayed_only []`,
    `unseen_relayed [a]`, `not_as_delivered []`, deliveries 3, judged 1. RED first.
  - `..._with_no_human_verdict_the_newest_result_is_named` (only the relayed reject on `c`): task `a`, as today; `unjudged_cases [a]`. Guard.
  - The m0-s2 shape, fixture `tie_m0_s2` (`tie` without `c`; `b`'s and `a`'s late results reported with `commit=False`, then one `commit`; the one
    commit is cosmetic: `at_result` gives V2 either way). Three tests, each with one state of the verdicts, never cumulative:
    - no verdict: `findings(ROOT, SERVICE, settled=True) == []`, `unjudged_cases [a]`. Guard.
    - only the user's reject on `b` (the case's latest delivery): `[]`, `unjudged_cases []`. Guard.
    - only the user's accept on `a`'s late delivery, **then** the copy written (so the verdict is older than the file and the finding is not
      settled): `findings(ROOT, SERVICE, settled=True)` is one `given` finding naming `a` with `settled` False; the default call gives `[]` (here
      the `given` rule's doing, not the settled filter's); `unjudged_cases []` (at `c68ae679`: `[a]`, the given delivery being the latest, `b`,
      which has no verdict). RED first.
  - The existing three tests stay as they are (`b` carries the accept and is the walk's own pair).
- Replay of m0-s2 T4 **on a git history built from the kept files** (`test_org_growth_0b1.py::test_f_g0_1_m0_s2_t4_the_tie_without_a_verdict_is_the_latest_delivery`,
  git-guarded): the G0 kit at `m0-s2`, cut `20261026T062340000000` (G0's `quality/turn-04.json` was written at 06:23:40; no message lies between
  `...-lead-f5df`, 06:23:07, and the injection's `...-root-9279`, 06:24:13), with the deliverable pinned, the team's files and `history=True` (6).
  P3 takes the history path: both `f5df` and `e876` read v2 from git and equal the file, a tie with no verdict. Expected, equal to `turn-04.json` on
  these keys: case `20261026T061639840350-root-6f1d` `done`, 2 tasks, `runs` 10, `user_cost` 10, `user_approved` 12, `ratio` `"0.83"`, `spend` 10;
  deliveries `total` 2, `judged` 0, `unjudged_cases [6f1d]`, `relayed_only []`, `unseen_relayed []`, `not_as_delivered []`, `neither []`,
  `not_on_a_delivery []`; first delivery `6f1d` outcome `none`, not superseded; `history.known` true; and `findings(ROOT, None, settled=True) == []`.
  Evidence facts on the kept files: commit `0491b2b` (06:23:12) holds `lead/sent/...-e876.md` and `...-f5df.md` (`org-git-log.txt`); v2 `0d07ec4` was
  committed at 06:21:48 and v3 at 06:25:26, after the cut (`memos/versions/INDEX.txt`). It is GREEN at `c68ae679` too: the zero case of the rule on
  kept history, which must not move.
- Unit (`SRC/reflection/tests/test_deliverable_checks.py`, `Rig` with `FixedCheckedVersions`: `at` is git-given, `now` the fallback; the world's
  `FakeClock`, whose `monotonic` moves 1 µs per reading, so P3's 5-s bound is never reached): every case of 4.6; `relayed` names the older equal pair
  with the human verdict; several with verdicts: the newest result; a fallback-equal pair is no candidate; a `P` from the fallback keeps today's walk;
  another case's pair is no candidate; a one-off pair keeps today's choice; `given` only when the chosen delivery is not the case's latest. And two
  tests with the verdict **older than the file** (finding not settled):
  - the default call (no `settled`) on a `relayed` tie (the `tie` shape: the accept on `b`, then the copy): one `relayed` finding naming `b`,
    relayed `(c,)`, `settled` False (at `c68ae679`: `a`); `deliverables_note` of it is today's line with `b`'s id;
  - the m0-s2 shape (the accept on `a`, then the copy): `findings(ROOT, SERVICE) == []` and `findings(ROOT, SERVICE, settled=True)` is one `given`
    finding naming `a`, `settled` False.
  A test that pins P3's newest-first choice in a tie with a human verdict pins the defect: the commit changes it and names it.
- Contract (`SRC/reflection/tests/test_contract_deliverable_checks.py`, over `IMPLEMENTATIONS[DeliverableChecks]`):
  `test_a_given_finding_is_returned_only_with_settled_true`: after `populate_given` (4.4), `findings(ROOT) == [] == findings(ROOT, service)`, and
  `findings(ROOT, settled=True)` and `findings(ROOT, service, settled=True)` are the one finding, `("given", <the returned task>, False)` for
  `(kind, task, settled)`. The fake's RED is its filter of today; the real class's RED is that `given` does not exist yet.
- `SRC/reflection/tests/test_records.py`: a `given` finding flags its delivery `given` like `relayed`, voids nothing and is not counted.
- Determinism of the real-git tests. They run on the system clock, as `test_org_growth_0b_given.py` does today: P3 asks git only while its call is
  under 5 s (`clock.monotonic()`; `testkit.clocks.ClockReading` keeps the system's monotonic, and a frozen one would freeze the runtime's waits too).
  Each call here asks at most 6 pairs of a local repository. A git slower than that makes P3 compare with the team's current file (V3 for `tie`):
  the `tie` tests then fail, never pass falsely; the m0-s2 T4 replay is a zero case whose expected values the fallback gives too.

## 5. F-G0-3: a message file that moves between the listing and the read

**5.1 What happened** (m1-s3 T7, `assistant-tool-calls.txt` lines 745-763). Root's `inbox` (#33) moved the result `...-lead-3386` inbox -> inflight
-> read (`FsBatchStore.begin`, then `end`), and `progress(task_id=...-root-68a8)` (#34), 1 ms later, had listed root's `inflight/` and then failed to
open `inflight/...-3386.md`. The raise comes from `FsMailbox.messages` (`SRC/mail/_mailbox.py`), the runtime's `MailboxReader` (`app/wire_mail.py`),
which parses every listed file with no guard (`CachingMessageParser.parse_as` opens the path); every `progress` read of root's boxes goes through it.

**5.2 The rule.** A file listed in a received box (`RECEIVED_BOXES`: `inbox`, `inflight`, `read`) but gone when it is read is read from its new
place when that place is another of the received boxes the call asked for, and is otherwise left out of this call. A message is returned once per
call. Nothing else changes: the order (by id), the boxes, the `sent` box's reads, and every other error (a file that does not parse, a permission
error) still raise as today.

**5.3 The change, in the reader** (`FsMailbox.messages`). For each listed file of each asked box: parse it; on `FileNotFoundError`, when the box is one
of `RECEIVED_BOXES`, try the same file name in each other asked box of `RECEIVED_BOXES`, in that order (a second `FileNotFoundError` goes on to the
next); found nowhere, skip it. A file name already read from one received box in this call is not read again from another: the walk can meet a
moving file twice (in `inbox` before the move, in `read` after it). The `sent` box keeps today's reads: a `sent` file that is gone still raises (no
writer moves a sent copy, and the brief's defect is a result that `inbox` moved). The fix is in `mail` rather than in `progress` because the race is the reader's: a guard in
`progress` would leave `status`, `quality` and the scheduler's counts raising on the same race. `DirMtimeCachingMailbox` (the dashboard's) already
skips such a file and is unchanged; `find_anywhere` already never raises and is unchanged (11). **The single writer is unchanged:** `FsBatchStore`
stays the only writer of `inflight/` and `read/`; `inbox` still moves the file; `FsMailbox` only reads (R9).

**5.4 Zero and empty cases.** No move: today's list, byte for byte. Moved forward (inbox -> inflight -> read) into an asked box: read there, once.
Moved back (a failed run's `end(ok=False)`, inflight -> inbox) after `inbox` was listed: found by the lookup, once. Moved twice before the read: the
lookup tries every other asked received box. Moved to a box the call did not ask for (`messages(addr, "inflight")`): skipped. Removed: skipped. A
missing box directory: `[]`, as today. The same name present in two received boxes at once (an anomaly no writer makes): returned once, from the
first box listed. A `sent` file gone between the listing and the read: raises, as today (tested, 5.5).

**5.5 Tests** (deterministic: the move is injected between the listing and the read).
- `SRC/mail/testing.py` gains `MovingMessageParser(CachingMessageParser)`, beside `CountingMessageParser`: given `{source: target}` (paths), it
  overrides `parse_as`; the first parse of a path whose `Path.resolve()` equals a source's `resolve()` `os.replace`s it to its target and appends
  the source to `moved: list[Path]`, then parses the path as usual, and so raises the real `FileNotFoundError`. Resolving both sides makes the match
  independent of how `OrgLayout` spells the path (macOS's `/private/var` against `tmp_path`'s `/var`). It is the seam of the race: the listing has
  happened, the read has not. Every test that uses it asserts `moved` holds its source once, so a move that did not happen fails the test.
- `SRC/mail/tests/test_fs_mailbox.py`: each case of 5.4 with the parser; `received(ROOT)` holds the moved message once; a `sent` file moved away
  (to a path outside the boxes) still raises `FileNotFoundError` from `messages(addr, "sent")`; a file that does not parse still raises; a listing
  without a move is equal to today's.
- Replay of m1-s3 T7 (`test_org_growth_0b1.py::test_f_g0_3_m1_s3_t7_progress_reads_the_result_inbox_moved`; `from testkit.progress_world import
  describe_progress`): the G0 kit at `m1-s3`, cut
  `20261026T085214255000` (#33's time), `inflight={ROOT: ["20261026T084941501890-lead-3386"]}` (between `begin` and `end` of root's `inbox`). The
  organization is opened inside `wiring.overriding({**clock_ports(fixed), MessageParser: MovingMessageParser({<org>/inflight/...-3386.md:
  <org>/read/...-3386.md})})`: `describe_progress(org, "20261026T084600894818-root-68a8")` does not raise, names the task and its `done` state, and
  equals the text of the control (the same cut with the result in `read/`, the same fixed clock), and the parser's `moved` holds the source once.
  Root's `inflight/` is read only through `messages`
  here (`has_inflight` is asked of agents only: `progress/_states.py`, `_liveness.py`, `attention/_waiting.py`), so the two texts can be equal. If
  the RED run shows that another reader opens the file first (the text then differs from the control), the coder reports it with the reader's
  name; the comparison with the control is never loosened. At
  `c68ae679` it raises the m1-s3 error, `[Errno 2] No such file or directory: '.../inflight/20261026T084941501890-lead-3386.md'`.
- No contract-suite change: the race needs a parser seam that only the file implementation has (R8's suites are unchanged).

## 6. The G0 replay kit (`TESTS/testkit/g0_replay.py`, test-only)

`materialize(stream, cut, root, *, inflight=None, deliverables=(), team_files=False, history=False) -> Path` builds the organization `EVG0/<stream>`
had at the 21-character stamp `cut` (inclusive) at `root/org` and returns it:
- it calls `e5_replay.materialize(stream, cut, root / "org", inflight, evidence=EVG0, service="weekly-meeting-memo")`, with the key `ROOT` of
  `inflight` mapped to `""` (root's boxes are the organization directory itself). The contract is `service/history--SERVICE.v1.md`, as for E5-E7;
  every G0 contract version has `budget: 12` (`history--SERVICE.v1.md`, `current-SERVICE.md`), so no figure here depends on it;
- it rewrites the materialized contract's `deliverable.path` line to `root/deliverables` when `deliverables` are pinned, else to
  `root/no-deliverables` (never created): the only edit of a kept record, as in `org_replay`. The kept contracts name
  `/tmp/hirearchy-g0-<stream>-<epoch>/deliverables`, and G0's sandboxes are still in `/tmp`, so without it P3 would read a folder outside the test;
- each pinned deliverable is `(name, version file under memos/versions/, UTC mtime, deliverables-log line)`; the file is written with those bytes
  and that mtime. The log line is 1-based and read with `org_replay.log_block` (its convention: the line must be a header `[<time>] call #<n> ...`).
  m0-s2 T4 pins `("memo-2026-10-05.md", "memo-2026-10-05.v2.0d07ec4.md", "2026-10-26T06:23:13.513Z", 3)`: line 3 of m0-s2's `deliverables-log.txt`
  is `[2026-10-26T06:23:13.513Z] call #26 turn 4 execute_bash`, the `cp` (md5 `47d12bc382b8200461240047cb3a935c`);
- an INDEX entry `<path> v<k> <sha7> <time> md5 <md5>` (`org_replay.index_entries`, reused; the `working tree` lines are not versions) maps to its
  version file `memos/versions/<stem of path>.v<k>.<sha7>.md`, the sha taken from the entry's third column (`org_replay.newest_version`'s rule):
  `lead/writer/work/memo-2026-10-05.md v2 0d07ec4 ...` is `memo-2026-10-05.v2.0d07ec4.md`. The kit checks the file's md5 against the entry;
- with `team_files`, for each path of `memos/versions/INDEX.txt`, the newest version committed at or before `cut` (G0's INDEX times are `Z`) is
  written at its org path (m0-s2 T4: `lead/writer/work/memo-2026-10-05.md` = v2);
- with `history` (requires `team_files`), the organization becomes a git repository of **one commit** holding everything materialized (`git init
  -q`, `git add -A`, `git commit -q`, with a fixed author and committer in the environment of the call). `CheckedVersions.at_result` then answers
  every result's artifact with its version at the cut. That is faithful only when no listed file changed between a result and the cut, so the kit
  first checks: for every `done` result in root's received boxes at the cut, no INDEX version of a path it lists was committed after the result's
  stamp and at or before the cut; a violation fails the test (m0-s2 T4: none; v3 came at 06:25:26).

A missing evidence file, a bad cut, a pin whose log line is not a header with the pinned time, an INDEX entry whose version file is missing or
whose md5 differs, an unfaithful history or a failing git
call fails the test, never skips it (the tests that use `history` carry the git `skipif` of `test_org_growth_0b_given.py`). The tests set
`HIREARCHY_WORKSPACE_ROOTS` to their `tmp_path`. `TESTS/meta/test_g0_replay_kit.py` tests it: the cut (inclusive), the root `inflight` mapping, the
contract equal to `service/history--SERVICE.v1.md` except the one rewritten line (never a `/tmp/hirearchy-g0-` path), the pinned file's md5 against
INDEX and its mtime, the team file at the cut, the one commit (`git rev-list --count HEAD` is 1, it holds `lead/sent/...-e876.md`), and the
faithfulness check failing at m0-s2 `20261026T062600000000` (after v3 `b389f15`, 06:25:26, while `e876` lists the memo).

## 7. The replays and the stop rule

After each fix, the FEAT's end run (10) holds every pre-registered replay: `TESTS/e2e/test_org_growth_0b_replays.py` (E to E7, E3-7, the constructed
E3-9; the 116 tests G0 ran at `3c841bb9`, `EVG0/deterministic/at-3c841bb9/`), `test_org_growth_0b_costs.py`, `test_org_growth_0b_given.py`, and the
E5-E7 time-cut replays of `test_org_growth_0a3.py`, `0a4.py` and `0a5.py`. Expected moves: only the RED values above (m0-s1 `6c7a`: 13 -> 14; the
`tie` fixture's `relayed` task `a` -> `b` and its m0-s2 shape's accept on `a`; m1-s3 T7: raise -> text) and the one pre-registered value of 3.5,
amended as R-0b1-1 rules (12). **If any other expectation moves, the FEAT stops** and the coder sends a warning with the expectation's id, the computed value, the
expected one and the kept files that show it; an expectation, a golden or a rule is never edited to match (0b 19.3, DR2-13). Goldens: 0 are expected
to change (`tests/golden` has one quality golden with a grant, A5's `a5_one_off_block.txt`, on a `done` case); a golden that changes is the same stop.

## 8. E7S3-6: the design correction (0b 19.3)

One `docs(design)` commit edits `docs/design/org-growth-phase-0b.md`; no replay expectation changes (the replay's `[]` is the kit's, and it stays).
Facts checked on `studies/E7-org-growth-0a4-recheck/evidence/s3`: `f639` answers 5834 `done` (v3 `1c5b8a5`, 08:34:02, was the file then); `c2f9`
answers 62a5 `done`; `da3c` answers d9bc `blocked`; v4 `b5f1411` (08:39:14) is the file now; `2da1` is a relayed reject of 5834; the harness's
history-path view (`harness-selfcheck/e7-s3/rederived.json`) has `not_as_delivered [{09df, 5834}]`.
- **19.3, "What a replay of these files cannot show (kit limit)", E7 block.** Replace `in s1 and s3 the replay and the history agree (memo 1's file is
  the current one).` with: `in s1 the replay and the history agree (memo 1's file is the current one, the checked artifact of 066f's delivery). In s3
  they do not (corrected by 0b.1: F-G0-13, manager decision of 2026-10-25 item 3): memo 1's file is v4 (b5f1411), written by d9bc, whose result
  ...-lead-da3c is blocked, so no delivery checked it (D4); with history P3 compares the file with the newest delivery that lists it, the relayed
  5834 (...-lead-f639, checked v3 1c5b8a5), and reports differs naming 5834: not_as_delivered [{"case": 09df, "task": 5834}], nothing voided (5834
  carries only the relayed reject ...-root-2da1), and the judged line reads "not as delivered: 1 (...-root-5834)". The replay compares with the
  team's current file, v4, and finds nothing.` (ids and code spans formatted as the paragraph around it).
- **19.3, E7S3-6.** `the three delivered memos equal the team's current files` becomes `the three memos the user was given equal the team's current
  files` (memo 1's file came from a blocked result, which is no delivery: D4); `the checked artifact of d9bc (whose result is blocked)` becomes `the
  version d9bc's run committed (its result ...-lead-da3c is blocked, so it is no delivery's checked artifact: D4)`; the item ends with `With history
  (G0's self-check, SELFCHECK.md item 3; not a replay expectation): not_as_delivered [{"case": 09df, "task": 5834}], as the kit-limit paragraph
  says.` E6S1-6 and E7S1-6 keep their wording: their memo 1 is a delivery's checked artifact.
- **19.2:** checked; its E7 paragraph says only that the replay compares with the team's current files and never finds a `relayed` file. It makes
  no "agree" claim, so it is unchanged. The E6 block of 19.3 has a like sentence ("in s1 and s3 the replay and the history agree"); it is outside
  this correction, was not re-derived on the history path, and is backlog (11).

## 9. F-G0-7: the investigation plan (fix only if it is the product's)

**What is known.** M0 streams have 15, 19 and 16 calls of `tool_call`/`tool_load` with `args={}` failing `Tool "tool_call" is not available.`; M1
streams have 0 (counted again for this design in every `assistant-tool-calls.txt`). In m0-s1 the failed #8 (`args={}`) is followed 2 s later by #9,
a `tool_call` with full arguments that succeeds, so the meta-tool exists in M0 sessions. The M0 `session_start` is 2 026 characters against M1's
6 666. The assistant-facing product texts name neither meta-tool: SKILL.md, the MCP server's instructions (`SRC/mcp_server/_instructions.py`) and the
tool docstrings have no `tool_call`, `tool_load` or "deferred". The org agents' texts do (`SRC/kiro/_profile_document.py`, `SRC/prompts/_files.py`),
but they reach org runs only, never the assistant's session (to be confirmed in step 4).

**Evidence to read** (read-only, `EVG0` only; never `~/.kiro`, never a file named `mcp.json*`, never the `/tmp` sandboxes; no live run):
1. Every failed empty-argument call in `m0-s1`, `m0-s2` (all turns: the H7 cut does not bear on a tool failure) and `m0-s3`: turn, position, the call
   before and after it (a retry with arguments?), whether it is in a parallel batch, and its raw record in `turn-NN.raw.txt` (the event's `rawInput`:
   empty, missing or cut) and `turn-NN.stderr.txt`. The same search in `m1-s1`-`m1-s3` must give 0.
2. The session stores (`assistant-session.json`, `assistant-session-messages.jsonl`) of M0 and M1: what `session_start` holds in each (the
   `<memories>` block, the deferred-tool catalog and its instructions, the skills list, steering), the session settings that differ, and the tools
   each session was offered.
3. The assistant profiles (`profiles/hirearchy-study-g0-<stream>-assistant.json`) diffed across arms with the stream labels masked; `setup.txt`
   (kiro-cli version, `--v3`, the command line, the environment names); `m0-home/setup.txt` (what the dedicated `KIRO_HOME` held);
   `harness/prepare_m0_home.sh`, `run_turn.sh`, `profile-template.json`, `workspace-cli.json`; `preflight/` and `probe/`.
4. What the product served both arms: the skill md5 (`skill-check.txt`, equal in 6 of 6), the MCP server's instructions and tool descriptions as the
   session recorded them, the org profiles under `profiles/`.

**How to classify.** The rule decides whether product code changes, so it is applied in this order, and the first that holds decides:
1. **Product** only when (a) a product byte the assistant's session received differs between the arms (SKILL.md, the MCP server's instructions,
   a tool's description or schema, or a server error, as the session stores recorded them), and the failures follow it in the M0 sessions; or
   (b) a product text itself tells the model to make the empty-argument call: the note quotes it, with its file and line.
2. **Harness or environment** when the product bytes the sessions received are equal in both arms and the failures occur in one arm only. The
   cause is then what only the arms differ in: the dedicated `KIRO_HOME` (no `memories/`, `sessions/`, `steering/` or other kiro state; settings
   copied without `mcp.json*`), the harness's turn driver, or kiro-cli's own behaviour in a fresh home (for example its deferred-tool catalog or
   session context built differently). This holds even when a product text change could mask the failures: such a mitigation is backlog, never
   this batch.
3. **Not determined** when the evidence cannot show 1 or 2 (for example, the sessions did not record the bytes needed to compare). It is no
   product cause, and no product code changes.

**What follows.**
- The finding goes to `.agents/tasks/f-g0-7.md` (never staged): the counts per stream, the classification, the files and lines that show it, and
  whether the M0 assistant-credit gap (26.79-29.12 against 21.92-24.74) is explained by it.
- **Product:** a FEAT that fixes the cause test-first and adds no behaviour beyond the fix (a test that fails on the shipped text first). A SKILL.md
  edit keeps it at 125 lines or fewer, its 0a.4 and 0a.5 lines word for word; an MCP docstring or instructions edit regenerates its golden
  deliberately, with the count stated.
- **Harness or environment, or not determined:** no product code changes. The note states what a future study harness must do, at least: build the
  M0 home with the same kiro state as M1 except the memories index (naming the files); run a preflight probe that compares both arms'
  `session_start` and tool catalog before turn 1 and stops on any difference other than `<memories>`; count empty-argument failed tool calls per arm
  as a validity measure; and, for "not determined", the probe that would decide it (it needs the owner's OK on spend).

## 10. Error handling, validation, invariants, test policy

**Error handling.**
| Operation | Failure | Recoverable? | Caller receives | Logged |
|---|---|---|---|---|
| `user_spend`, `case_spend` | none (pure; a negative held figure is floored at 0) | n/a | an int | no |
| `_folder_rule`'s tie scan | `at_result` raises nothing (the port's contract: an unreadable history is `None`); `None` or a fallback version: no candidate | yes | today's walk result | no |
| `_entry` with `given`, a call without `settled` | not an error (the Protocol rule, 4.4) | n/a | no finding | no |
| `FsMailbox.messages`, a file listed in a received box gone | `FileNotFoundError` | yes: new place, else skipped for this call | the list without the file, or with it read at its new place | no (the normal race; the dashboard's reader does not log it either) |
| `FsMailbox.messages`, a `sent` file gone, or any other read error | `FileNotFoundError` in `sent`, parse error, `PermissionError`, ... | no (unchanged) | the exception, as today | as today |
| `g0_replay.materialize` | missing evidence, bad cut, bad pin, a version file missing or with another md5, unfaithful history, git failing | no | `pytest.fail` (never a skip) | the test report |

**Validation of external inputs.** No new external input: no tool argument, no message field, no config key. The `given` kind is internal to
`reflection`. The kit validates its own inputs (cut length 21, files exist, the pin's log line, the history's faithfulness).

**Invariants and their owners.**
| Invariant | Owner | Why there |
|---|---|---|
| `user_spend == user_committed` while open or blocked; I1 (`user_spend == user_cost == case_spend` with no relayed task) | `reflection.api` (pure functions, property tests) | the one home of the spend arithmetic |
| The delivery P3 names as equal to the file is a delivery of that case whose git-given checked version equals it; ties are broken by the human-tier verdict | `reflection._deliverable_checks` | only P3 knows checked versions; records only flags |
| A `given` finding is returned only with `settled=True` (P3's notes, `findings` without `settled`, never hold it); a `relayed` line they show can name the tie rule's chosen delivery, with today's words (4.4) | `FolderDeliverableChecks._entry`; the fake `FixedDeliverableChecks.findings` too; the contract suite tests both | the notes render no `given` kind; one rule for every implementation (R8) |
| One message per file name in a received-box read; a moved file never raises | `mail.FsMailbox` | the reader of the boxes |
| `inflight/` and `read/` have one writer | `mail.FsBatchStore` (unchanged) | R9 |

**Testability.** Pure: the spend functions (hand-built `Case`). Unit with fakes: the P3 walk (`FixedCheckedVersions`, `HashBlobIds`), the records'
attribution (fixed findings), the reader's race (`MovingMessageParser` on a real directory). Integration: the fs worlds of `reflection/tests`. E2e
on kept files: the G0 kit's three replays (one with a one-commit git history). E2e on real git: the `tie` fixtures. Contract: `given` only with `settled=True`, over both implementations. Every RED is deterministic (no LLM,
no network, the move injected) except for one bound: the real-git and one-commit-history tests run on the system's monotonic clock, under P3's
5-s git bound, as `test_org_growth_0b_given.py` does today; a slow git can make the `tie` tests fail, never pass falsely (4.8).

**Test policy (the owner's).** Per commit, FAST and scoped: the touched packages' colocated tests (`SRC/reflection/tests`, `SRC/mail/tests`), the test
files the commit adds or changes under `TESTS/e2e` or `TESTS/meta`, `tests/golden`, `tests/architecture --deselect
tests/architecture/test_static_checks.py`, then `uv run python scripts/static_checks.py all`. At each FEAT end and each fix pass: one SCOPED union run
of those, plus `tests/e2e` (which holds every replay of 7). The full `UV_LINK_MODE=copy bash scripts/check.sh` (about 15 minutes, timeout 1800000 ms)
runs once, in final validation, after the rebase onto `main`; the merge step does not rerun it after a no-op rebase.

**Suggested FEATs** (the planner sets the commits). FEAT-0: the F-G0-7 investigation (read-only; no commit; it decides whether a product FEAT
exists). FEAT-1: the G0 kit and its meta test; then F-G0-2, whose fix commit carries R-0b1-1's amendment (12). FEAT-2: F-G0-1. FEAT-3: F-G0-3. FEAT-4: the E7S3-6
correction. FEAT-5, only for a product cause: F-G0-7's fix.

## 11. Out of scope, declared limits, backlog

- **Out of scope:** Phase 1 work; the approval that follows root's hand-downs (F-E7-9, F-G0-8; it goes to the Phase 1 design); the re-derivation's
  independence (F-G0-4), the L-KEEP table (F-G0-5) and `words=` (F-G0-6), which are study or Phase 1 inputs.
- **Backlog (with reasons):**
  - `case_total`'s "N runs used of M handed down" leaves grants out of `M` (m0-s1 reads 15 where 17 were handed down). The brief's fix is the two
    spend figures; changing the head moves pre-registered texts (0a.5 4.7's `9 runs used of 13 handed down`, `14 runs used of 13 handed down`).
  - A grant in a relayed rework's interval stays out of `case_spend` while held (0a.3: no user grant). No kept corpus has one.
  - `_file_rule` (a contract that names one file) does not apply the tie rule; aligning it with OQ-2 is a separate change. G0 and E7 use folder
    contracts only.
  - `FsMailbox.find_anywhere` returns None for a file that moves between its check and its read, where the next box would hold it. No caller of
    `progress` uses it.
  - A label "from a blocked result" for a file copied from a blocked result (the ruling, item 3; F-G0-13).
  - 0b 19.3's E6 block says "in s1 and s3 the replay and the history agree", which was not re-derived on the history path (E7S3-6 corrects only
    the E7 block's sentence, 8). A re-derivation of E6 s1 and s3 with history is a separate check.
- **Declared limits** (declared here; 0b 26 is not edited):
  - the tie rule considers only versions git gave, inside P3's bounds (20 results per service, 10 paths per result, 40 git pairs, 5 s);
  - the tie scan's git questions count against the call's 40-pair and 5-s bound, so in a folder with many files the files walked later can be
    compared without git sooner than today;
  - a one-off task's tie keeps P3's newest-first choice;
  - a received-box file that moved to a box the call did not ask for is missing from that call only.

## 12. The manager's ruling R-0b1-1 (2026-10-27)

**Asked.** F-G0-2's rule moves one pre-registered expectation (3.5): 0a.5 4.7's row "after the grant 68df" and its test
`TESTS/e2e/test_org_growth_0a5.py::test_a2_e7_s2_the_grant_68df_approves_13` (E7 s2, cut `20261025T075138446837`). Published: `user_cost` 13, no
sentence in `case_total`. With the fix: `user_cost` 14 (9 used + 5 held: 3 of 3ca4's 12, c671's default run and the granted run) against the
approval 13, and `case_total` adds `OVER_APPROVED`
(text in 3.5). May the fix commit amend them?

**Ruling: yes** (`.agents/tasks/manager-decision-design-loop.md`). 0a.5 4.7's own table reads the case over at #20 (`OVER_CONTRACT`, 13 > 12; c671
is unapproved) and at #24 (`OVER_APPROVED`, 14 > 13). Only the cut after the grant read "no sentence", because the cost left out the granted run the
team still held: that is F-G0-2. The grant of 1 covered half of the 2-run ask, so 1 run is still beyond the approval. The approval of 13 stays
(it leaves out c671's unapproved run). m0-s1 6c7a (grant +2, 14 of 14, no sentence) shows the fix does not raise an alarm for a grant by itself.

**Conditions, binding on the build:**
1. Of the pre-registered expectations, the F-G0-2 fix commit changes that row and that test only.
2. The test is renamed to say what it asserts: `test_a2_e7_s2_the_grant_68df_cost_14_over_13` (3.6).
3. In `docs/design/org-growth-phase-0a5.md` 4.7, the 0a.5 cell of the row "after the grant 68df" becomes:

   > grant term: committed 9 + (13 - 9) = 13, less c671's run still out 1, plus 1: approval **13**; `user_cost` (open) **14** (9 used + 5 held:
   > 3 of 3ca4's 12, c671's default run and the granted run): `OVER_APPROVED` (published: `user_cost` (open) 13, no sentence; superseded by 0b.1
   > F-G0-2 (R-0b1-1))

   The test's docstring states the same figures in the same words ("9 used + 5 held: 3 of 3ca4's 12, c671's default run and the granted run").
   (0a.5's `user_held` at this cut is 4: it leaves out the rework c671's own run, so it is not the whole cost.)
4. The fix commit's message names R-0b1-1 and the old and new values (`user_cost` 13 -> 14; no sentence -> `OVER_APPROVED`).
5. Section 7's stop rule stands for every other expectation: if one moves, the FEAT stops and asks.

## 13. Responses to the design review, pass 1 (`.agents/tasks/design-review.md`, 0 HIGH, 5 MEDIUM, 9 NIT)

Every finding is addressed; none is backlogged or ignored.

| # | Severity | Response |
|---|---|---|
| 1 | MEDIUM | Addressed (12, condition 3 and "Asked"; 3.6). The 14 is "9 used + 5 held: 3 of 3ca4's 12, c671's default run and the granted run", in the 0a.5 cell, the test docstring and "Asked"; it agrees with 3.5. The 4 was 0a.5's `user_held`, which leaves out c671's own run (stated). |
| 2 | MEDIUM | Addressed with the review's option (a) (4.4, 1, 10's invariant row, 4.8). Step 3 applies in every call, so an unsettled `relayed` line can name the tie rule's chosen delivery; its words are unchanged. The "byte-identical" claim is withdrawn. New unit test: a default call on a `relayed` tie, verdict older than the file, names `b`. Option (b) was rejected: the notes and the quality view would name different deliveries for one file. |
| 3 | MEDIUM | Addressed (4.4, 4.8, 10). `FixedDeliverableChecks.findings` filters with `(settled or (not f.settled and f.kind != "given"))`. `DeliverableHarness` gains `populate_given`. The new contract test `test_a_given_finding_is_returned_only_with_settled_true` runs over `IMPLEMENTATIONS[DeliverableChecks]`: the real class uses the m0-s2 shape with the accept older than the file, the fake a `given` finding with `settled=False`. In the e2e m0-s2-shape test the copy is now written after the accept, so its default-call `[]` comes from the rule. |
| 4 | MEDIUM | Addressed with the recommended option (5.2, 5.3, 5.4, 5.5, 10). The `sent` skip is dropped: a `sent` file that is gone still raises, and a `test_fs_mailbox.py` test pins that. |
| 5 | MEDIUM | Addressed (9, "How to classify"). There is now an ordered rule. Product only for (a) a differing product byte the session received, or (b) a quoted product text that asks for the empty call. Equal bytes with failures in one arm only is harness or environment, even when a product change could mask it (that mitigation is backlog). Not determined means no product change. |
| 6 | NIT | Addressed (3.2, 4.1). Each superseded definition is named, and the documents that hold them are not edited: 0a.1 6.1, 0a.3 4.2 and I1, 0b 3's `case_spend` and "given delivery" rows, 0b 4.3's "without a verdict", and the `kind` lists of 0a.3 DR-0a3-6 and 0b B4.8. |
| 7 | NIT | Addressed (11): the limits are "declared here; 0b 26 is not edited". FEAT-4's commit edits 0b 19.3 only. |
| 8 | NIT | Addressed (4.3, 11): the tie scan's draw on the shared 40-pair and 5-s budget is a declared limit. |
| 9 | NIT | Addressed (5.5). `MovingMessageParser` matches by `Path.resolve()` on both sides and records `moved`, and each test asserts the move happened. The import is named: `from testkit.progress_world import describe_progress`. The review's unverified point about another reader opening the file first is handled too: it would show as a text that differs from the control, and the coder reports it. |
| 10 | NIT | Addressed (8, 11): the E6 block's sentence is backlog. |
| 11 | NIT | Addressed (4.8). `deliver` gains `commit=True`, and `commit=False` lets two results share one commit (cosmetic for `at_result`). The m0-s2-shape states are three separate tests, never cumulative: at `c68ae679`, a reject on `b` plus an accept on `a` would already read `unjudged_cases []`. |
| 12 | NIT | Addressed (3.5, 6). The log line is 1-based (`org_replay.log_block`), and line 3 is quoted. An INDEX entry maps to `<stem>.v<k>.<sha7>.md` (`index_entries` and `newest_version`, reused). `MANIFESTS` has 16 keys: the review's 17 counted E3's `VARIANTS`, which are not in `MANIFESTS` and were not computed. 3.5 says why they cannot move: E3 has no grant. |
| 13 | NIT | Addressed (8): E7S3-6 reads "the three memos the user was given". E6S1-6 and E7S1-6 keep their wording. |
| 14 | NIT | Addressed by qualifying the claim (4.8, 10). The real-git tests keep the system's monotonic clock, as today: `ClockReading` keeps it, and a frozen one would also freeze the runtime's waits. A slow git can make the `tie` tests fail, never pass falsely. The unit tests run on `FakeClock`, whose monotonic moves 1 µs per reading. |

The review also flagged one claim as unverified: "on E7 s3's replay it would flag `62a5`" (4.5). It is withdrawn. 4.5 now gives only the reason
that does not depend on it.
