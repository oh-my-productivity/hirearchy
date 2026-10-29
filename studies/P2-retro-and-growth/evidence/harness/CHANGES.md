# P2 harness: where each file comes from (protocol 10, 13)

Built by step 1a (`preregister`, iteration 1) of workflow `wf_8ee5197e04b8ee7c` from P1's frozen harness
(`studies/P1-itemized-playbook/evidence/harness/`, `MD5SUMS` md5 `d21508978d71e6d805f1760b25acb1b6`). Nothing here is frozen yet; step 2
writes `MD5SUMS`.

## Independence of the re-derivation (F-G0-4; the brief, step 1a)
- **The author did not open `src/hirearchy/` (of `/Volumes/workspace/hirearchy` or of the arm-C worktree) while writing any file of this
  harness**, and opened no product source file at all during this step. `rederive_p2.py`, `p2lib.py`, `extract_p2.py`, `score_p2.py`,
  `lena_lines.py`, `gate_p1.py` and `selfcheck_cases.py` were written from the design's text: `docs/design/org-growth-phase-2.md` sections 3,
  4 (4.2, 4.4, 4.5, 4.5a, 4.9), 7 (7.1, 7.2, 7.5), 10.1, 21 and 22, and the Phase 1 design's section 3 (`text_tokens`'s regular expression
  and `plain`, verbatim; lineage; the subjects of a rejection), the 0a.2 design (`line_key`) and the 0a/0b texts (tiers, cases).
- They reuse P1's own independent re-derivation `rederive_watch.py` (unchanged, md5 `894f0085eaebecdd0549b1a6be23c2a3` = P1's line), whose
  `Mail` and `Criteria` give cases, deliveries, rejection ids, subjects, lineage and criterion numbering; P1's author did not open
  `src/hirearchy/` either (P1's `CHANGES.md`).
- **File formats** were read, as the brief allows, from kept evidence (P1's `I2/` session store, run logs, contract and playbook versions) and
  from the self-check's throwaway orgs' output: `hirearchy retro --json` and `hirearchy retro` (the brief's JSON keys, its rendered D7, D8 and
  D13 lines, the ledger `.runtime/retros.json`), `quality --json` (the escapes' `assertion` and `verdict`), the PLAN FOR YOU text of `plan`,
  the `apply` replies, AGENT.md and SERVICE.md frontmatter, the message files, and `git log`. Three renderings were taken from that output
  and are stated where they are used: the added-words list joined by `, ` with `+{k} more` as its last part (`p2lib.listed_added_words`);
  the clarify key's text part `line_key(text)[:40]`; the D7/D8 line forms parsed by `rederive_p2.parse_product_d7/d8`.
- To drive the throwaway orgs, `dryrun_build.py` calls the public `hirearchy.core.Org` facade (its signatures read at run time with
  `inspect.signature`, no source opened) and the arm's CLI; its call shapes were read from `tests/e2e/test_org_growth_2.py` and
  `tests/testkit/services_world.py` (test files, not `src/hirearchy/`). `mcp_catalog.py` uses the `mcp` client as E7's injection script does.

## Unchanged from P1 (byte copies; each md5 equals P1's `MD5SUMS` line)
`ambient_context.py`, `ambient_snapshot.sh`, `ambiguity_recall.py`, `assistant_facts.py`, `cost_total.py`, `empty_calls.py`,
`extract_mechanical.py`, `extract_proposals.py`, `extract_tool_calls.py`, `inject_root_rework.py` (E7's, `1c4e7824...`), `injection_files.py`,
`judged-template.json`, `org_state.py`, `playbook_attempts.py`, `prompt_sizes.py`, `rederive_quality.py`, `rederive_watch.py`,
`scheduler_survival.py`, `score_memos.py`, `skill_check.py`, `test_poll_loop.py`, `workspace-cli.json` (`05d30ccb...`); P1's fixtures under
`selfcheck/p1/`.

## Adapted from P1 (what changed)
- `run_turn.sh`: P2 labels and profile name; the 50-turn cap; refuses unless called by `turn.sh`; the fake chat and short boundary only for a
  `selfcheck-*` label (the self-check of the wrapper); `env -u KIRO_HOME`, `--effort high`, `; sleep 20` unchanged.
- `after_turn.sh`: no lock hook (no arm F); P2's counters (effort stops, running credits, requests and one-offs, the 140-run cap); the skill
  and product checks (H2); the snapshots last, with the arm's CLI and, in arm R, the retro snapshot; refuses unless called by `turn.sh`.
- `quality_snapshot.sh`, `services_snapshot.sh`: one function, `snapshot_cli.sh`, with the arm's CLI (`arm.sh`).
- `setup_stream.sh`: the arm parameter, both freezes, the skill rule per arm, the arm-C skill move with a restore on failure, the profile's
  product path, the masked diff over label, epoch and product path.
- `finish_stream.sh`: the arm's CLI; P2's extracts (`extract_p2.py --facts`) and the retro snapshot `end` with T0; the arm-C skill restore
  last; scoring left to step 12.
- `next_stream.sh`: P2's order and gates (the stage gate, the 260-credit decision in stage 2, an unrestored skill move).
- `copy_org_evidence.sh`: the arm's CLI; every service under `services-all/`, the study service also under P1's names; `org-copy/`, the
  ledger, the charter history and its commit list, the git bundle.
- `model_check.sh`: P2's evidence path, labels and profile name only. `memories_gate.py`: P2's order only. `safety-snapshot.sh`: P2's
  products, protocol path and sandbox root. `skill_check.sh`: the rule per arm, plus `skill_proof.py`. `profile-template.json`: `<PRODUCT>`
  in the server's `--directory` and in the skill resource; P2's names and sandbox root. `probe.sh`, `probe_compare.py`: P2's order, the
  skill move, the catalogs per product, the skill proof. `aggregate.py`, `selfcheck.sh`: P2's rules and parts.

## New in P2
`arm.sh` (the one label -> product map), `turn.sh` (one wrapper per turn), `skill_move.sh`, `retro_snapshot.sh`, `snapshot_cli.sh`,
`stop_stream.sh`, `injection.sh`, `inject_root_rework_armc.py` (E7's file with line 36 only changed: `REPO` is the arm-C worktree, so its MCP
server and its text source are arm C's), `effort_stops.py`, `running_credits.py`, `requests_by_turn.py`, `skill_proof.py`, `mcp_catalog.py`,
`p2lib.py`, `rederive_p2.py`, `extract_p2.py`, `score_p2.py`, `lena_lines.py`, `gate_p1.py`, `stage_gate.py`, `watch_views.sh`,
`preflight_run.sh`, `dryrun.sh`, `dryrun_build.py`, `selfcheck_cases.py`, `keys/answer-key-p2.md` (private).

## Fixes found by the self-check (iteration 1; `harness-selfcheck/SELFCHECK.md`)
1. `rederive_p2.estimate`: `r` counted runs up to the next case's head (5 against the product's 3); now up to the case's last result
   (protocol 13.2 reading 9).
2. `rederive_p2.signal_checker`: two lineage classes with the same three cases gave two candidates; now one per evidence set (reading 8).
3. `rederive_p2`: D7 had no rows for structural changes and charter edits; `d7_structural` added (4.4's rows).
4. `p2lib.listed_added_words`: the overflow part is joined by `, ` as the product renders it.
5. `dryrun.sh`: the constructed facts parsed message stamps with one character too many; the three trap rejections were missing from the
   constructed Lena lines.
6. `dryrun_build.py`: a service request's `done` needs `lessons` in the after-action form; one read-only MCP call (`whoami`) now precedes the
   plan, as a stream's assistant makes calls before its first `apply_org` (SELFCHECK.md item 3).
7. `selfcheck.sh`: P1's `empty_calls.py --selfcheck` needs `--out`.
8. `extract_p2.b_check`: the first plan's own creations (`from the plan you approved`) were read as unlabelled; a full plan the user
   approved is an approved label (protocol 12.1 P2-B step 1 now says so).

## Iteration 2 (the revision for `prereg-review.md`; each finding's resolution in `../prereg-revision-2.md`)
**Independence, again:** in iteration 2 the author did not open `src/hirearchy/` of either product, nor any other product source file. The
review quotes `src/hirearchy/reflection/_steps.py:99-106`; that file was not opened. The product's question texts for a rejection were
read from the product's own MCP replies on throwaway orgs (`mcp_call.py`, `harness-selfcheck/dryrun-R/f7-*.json`), its tool argument names
from the MCP server's `list_tools` schemas, the label forms from `hirearchy retro --since ... --json` on a scratch org, and the CLI's
arguments from `--help`, as the brief allows. Every new definition in `rederive_p2.py` is written from the design's text (sections 3, 4.2,
4.4, 4.5, 4.5a, 7.1, 7.2, 7.5) and cited in its docstring.

Changed files and why:
- `rederive_p2.py`: the signals as pure functions over P1's `Mail` (`service_from`, `checker_from_mail`, `clarify_from`,
  `amendment_outcomes`, `d7_outcome`), so the constructed cases drive them (F12); 7.2's classes as design 3 defines them, `C<k>` and its
  lineage as of the derivation's time, and (b)'s escapes per verifier -> `checker-fix` (protocol 13.2 reading 12); 7.5's once-per-key part
  (`fires` and `fires_rule`); the ledger's effect test, lapse, suppression, cause after two lapses, the `lapsed` counts, the cap and the
  order (`effect_facts`, `effect_seen`, `ledger_rules`; F13); D8 with every label of 4.5: charter pairs read from the evidence copy's git
  bundle and compared by frontmatter and body (`charter_pair_label`: `by <parent>` from the event log's `write` events, the horizon
  label, `outside the tools`), retires and service retires from `RETIRED.md`, `taken back`, the creations of retired agents and services
  (reading 13), and the product's D8 parser for every label form (F12, P2-E); `edits.json` also carries the re-derived D8's unprompted
  labels (X3's second count); retired service folders kept apart from live services.
- `extract_p2.py`: rewritten checks. The cut rule and the `FAIL-CLOSED:` prefix (`end_of`, `absent`; F2); the one-off window to the line
  that judges the list (F5); D-UNNOMINATED by an item's id or kind, written to `p2/unnominated.json` (F6); X1 and X2 step 3's
  `approved=True` and the proposal's `plan_id` as a FAIL of their own; X2 step 1's split report (F7); X3's CHARTER-PLAN and CHARTER-ADDED
  counts, its second harness count, and the assistant's hand writes into the org from the session store by write target (F3); P2-L's
  reply-items finding, the re-derived D13 comparison, the shown-again id and the ledger snapshots' bytes, the title or first body line
  (F3, F13); P2-B's A-P ledger items, the unnominated count, `taken back` of an applied plan_id (F3); P2-W(c) per criterion's source line,
  W(0)'s `from_tasks` exemption stated (F3); P2-E through per-record re-derivations; P2-S per record with suppression, the ledger's order,
  cap and lapse counts, and T12 against the product's D5 group (F3, F13).
- `lena_lines.py`: "passed the trap" only for judged memos, `trap_unreached` (F2); the list bounds of 4.5 (F5); the rule ids `ITEM-CAUSE`
  and `L-NOTHANKS`; the rows per turn (K30c, F7).
- `gate_p1.py`: rewritten (F4): G1(b) per `retire due` item with P1 12.1's (1), (2) and (4); G1(c) by tier against P1's world of the
  service; G1(a) over the product's views and the re-derivation's states; G1(d) and the presented deliveries from `judged.json`; G2(b) and
  (c) as P1 12.2 words them (the next request, the case's human accept and 13.2's exception, the end, a cut); the injection's task by
  `injection/request-args.json`, every other relayed rework counted; hand edits from `assistant_facts.json` (M-P3-2); fail-closed
  readings for unread inputs and for zero scored versions. New `gate_p1_cases.py` (its 23 constructed cases) and `p2-judged-template.json`.
- `aggregate.py`: the gate-able measures over every valid stream of both arms gate the exit (F1); constructed cases for it.
- `stage_gate.py`: item 3 reads only `FAIL-CLOSED:` reasons (mismatches are information), item 2 reads the re-derivation alone and reports
  "X2 not reached" beside it, a CONDITION disagreement is an H7 fact (F20); its constructed cases (`--selfcheck`).
- `probe_compare.py`: one hash per loaded tool from the `tool_load` result's `loaded` entries (the form P1's kept sessions show), and
  constructed probe folders for every stop and the PASS (F12).
- `skill_move.sh`: `recover` (F18); the owner's aside directory under the study folder, outside `/tmp` (F18; a cross-volume move, checked
  in the self-check); the self-check's aside may point there too (`P2_SELFCHECK_ASIDE`).
- `turn.sh`: refuses while a skill move of another label is open (exit 92), as its header said (F17).
- `after_turn.sh`: the other-product check reads the scheduler by its pid file and every process naming the sandbox, by product directory
  (F17).
- `setup_stream.sh`: a failed setup deletes the profile it created, with a record (F19).
- `finish_stream.sh`, `stop_stream.sh`: `--end <reason>` writes `end.txt` (protocol 3.7; F2).
- `dryrun.sh`, `dryrun_build.py`: a fresh output folder per run (an earlier run's copy mixed two orgs); `H0` exported; F7's three question
  forms through root's MCP `feedback` on scratch copies (`--phase f7`); label coverage on a scratch copy (`--phase labels`: a parent's MCP
  write, terminal hires, an extension's retire, a service defined and retired); the constructed Lena lines in the build's event order with
  turn starts before each event; an injection record for the build's relayed rework; expectations for the gate-able measures the
  construction determines. New `mcp_call.py` (one MCP tool call, throwaway orgs under `/tmp/hirearchy-p2/` only).
- `selfcheck.sh`: the parts of protocol 13.3 line for line (stage_gate, gate_p1, probe_compare's cases; skill_move's recover and
  cross-volume cases; turn.sh's refusal). `selfcheck_cases.py`: rewritten, 131 cases (F12).

Harness bugs the iteration-2 self-check found, and their fixes (`../harness-selfcheck/SELFCHECK.md`):
1. `gate_p1.py` and `rederive_p2.py` read a link note's rejection from `confirms`; the evidence's link notes carry it in `reply_to`
   (`criterion: C5`, `reply_to: <rejection>`), and `criterion` may be a scalar. Both now read `reply_to` and a scalar or list.
2. `extract_p2.org_hand_writes` matched `2>/dev/null` as a write into the org; it now reads each command's write targets.
3. `probe_compare.py` hashed a whole `tool_load` result for every tool it named, so two tools of one load had one hash; now one per tool.
4. `dryrun.sh` did not export `H0`, so its constructed-facts block failed and P2-X1 and P2-X2 read FAIL on the dry run.
5. `dryrun.sh` reused its output folder, so the evidence copy held two orgs' messages (P2-S read the wrong repeats).
6. `gate_p1.py` read zero scored versions as FAIL; it now fails closed (NOT DETERMINED).

## After the manager's decision on PF-0 and PF-1 (`../manager-decision-prereg-pf.md`; protocol 12.6)
- `extract_p2.py`: `pf0_signature`, `classify_d8` (each D8 difference PF-0, PF-1 or new; D7 differences new), `finding_line`; `e_check`
  writes one finding line per difference with its class and `counts` {PF-0, PF-1, new}; `x3` takes a PF-0 line on a change the
  re-derivation does not count out of the product's count and step 5 (reported under P2-E), and fails as written on a counted one;
  `verdicts.txt` adds `P2-E product findings: ...`.
- `rederive_p2.py`: each charter pair of D8 carries `t1` and `t2` (its commit times); each parsed product line keeps its text (`raw`);
  the event log's horizon compared at whole seconds (a harness bug the PF-0 test found: SELFCHECK.md item 4).
- `aggregate.py`: the PF-0, PF-1 and new counts per stream, with a constructed case.
- `dryrun.sh`, `dryrun_build.py` (`--phase pf0`): the classifier over the product's own output, PF-1 on the label-coverage org and PF-0 on a
  terminal-only org. `selfcheck_cases.py`: 14 cases (PF-0, PF-1, their near misses, the X3 reading, P2-E's counts, the whole-second horizon).
- Independence unchanged: no product source file was opened; the PF-0 reproduction reads the product's own `retro --json` output.

## Iteration 3 (the revision for the second `prereg-review.md`, F22-F37; the manager's decision `../manager-decision-prereg-loop.md`; each finding's resolution in `../prereg-revision-3.md`)
**Independence, again:** in iteration 3 the author did not open `src/hirearchy/` of either product, nor any other product source file. The
new readings come from the design's text (3 "quiet note", 4.5's structural words, 4.6, 7.2, 17.3, 18.1) and from kept evidence: the
`wake:` headers of runtime notes in P1's kept streams and in the dry-run orgs, the PLAN FOR YOU and blueprint files of the dry run, P1's
`INDEX.txt` and `turn-times.txt` time formats. The one product import the harness checks in F31 (`hirearchy.kernel._text`) is P1's
`extract_mechanical.py`'s, unchanged; the dry run only resolves its file path.

Changed files and why:
- `extract_p2.py`: P2-L step 4 reads every runtime note to root that is not `wake: false` and fails only on WAKE_WORDS (`runtime_wakers`;
  F22); P2-B step 2's pattern `fact[\s_-]*check` over the reason and the added agents' name, template, role, charter and charter_extra,
  agents' addresses and roles, ledger keys and effects (`FACT_RE`, `blueprint_agents`, `names_fact_checker`; F23); D-UNNOMINATED with open
  items (`item_states`, `item_open`, `nominated(bp, items, t, m5)`, `memo5_request`, `unnominated(..., applies)`; F29); X2 step 1's residual
  case (`retro1_before_answer`; F27).
- `lena_lines.py`: `condition_turn` reads L0 as the line answering the third trap rejection's question (`third_trap`, `ANSWER_ROWS`, the
  `answers <rule>` fact), with the judging-line fallback and memo 5's exception (F27); `retro_places` (F28); `verdict_after` (F26); new
  constructed cases.
- `score_p2.py`: each version's Lena verdict (`turn_of_time`, `verdict_after`); `delivered_check` exempts rejected versions and checks
  final memos (F26); cases.
- `gate_p1.py`: a presented version Lena rejected is exempt (F26); `gate_p1_cases.py`: its case.
- `p2-judged-template.json`: the presented entry's `turn` and the exemption (F26).
- `stage_gate.py`: item 3 reads `p2/gate_p1.json`'s `FAIL-CLOSED:` values and an unread `gate_p1.json`; judged NOT DETERMINED is information;
  the constructed L0 is the answer line (F36, F27); cases.
- `score_stream.sh` (new): the measures' inputs of one stream in a fixed order, for the gate and step 12 (F36).
- `finish_stream.sh`: `extract_mechanical.py ... --product-src $REPO_A/src` (`EM_ARGV`), every step's argv in `finish-steps.txt` (F31).
- `dryrun.sh`: the F31 checks in each arm; the constructed L0 answer line (F27).
- `skill_move.sh`: `ASIDE-PENDING` before the `mv`, open for `status`, `restore` and `recover`; a pending move that never ran is closed
  with the copy in place (F33). `selfcheck.sh`: two cases for it (18 skill-move cases).
- `probe.sh`: turn 1 asks to load the hirearchy skill first (F32); the exit trap deletes the profile its run created, with a record (F34).
- `next_stream.sh`: `manager-decision-memories-before-<next label>.md`, the one name (F37).
- `selfcheck_cases.py`: cases for F22, F23, F27 and F29.
- `dryrun.sh` (a test bug the first full run of iteration 3 found; `../harness-selfcheck/SELFCHECK.md`, "Iteration 3"): the PF-0 check over
  the terminal-only org assumed the product reproduces PF-0 on every build, but its label depends on sub-second timing; the build is now
  repeated (at most 8 times) until both timings exist, each try recorded in `pf0-timing.txt`, and each timing is checked. The PF-0
  signature in `extract_p2.py` is unchanged (the manager's decision).

## Manager closing pass (the rulings C1-C5 on F38-F42 of review 3; `../manager-decision-prereg-loop.md`, "The loop is CLOSED by decision after iteration 3"; each ruling's entry in `../prereg-closing-pass.md`)
**Independence:** in the closing pass I opened no product source file: no file under `src/hirearchy/` of arm R
(`/Volumes/workspace/hirearchy/src/hirearchy/`) or of arm C (`/Volumes/workspace/hirearchy/.worktrees/p2-arm-c/src/`). The changes rest on
the protocol's text, the review's Resolve texts and the harness's own files and constructed cases. No new product import was added; the
new imports are harness modules (`score_p2.py` and `gate_p1.py` import `extract_p2.end_of`).

Changed files and why:
- `score_p2.py` (C1): `last_verdict` (the verdict of the last Lena line that judged a memo, `lena_lines.verdict_after` over that line);
  `delivered_check(versions, finals, lines, end)`: a final memo keeps the rule only when that line is ACCEPT or L-ASIS; a rejected or
  never-judged final, and a never-judged version, read NOT DETERMINED (cut) in a cut stream, NOT DETERMINED (FAIL-CLOSED) with no
  `end.txt`, and are held to the rule as written in a `retro-2-done` stream; `score()` passes `extract_p2.end_of(stream)`;
  `score_p2.json` `p2_delivered_versions` gains `not_determined`, `verdict` and `end`. Cases: three new (the review's) and the no-`end.txt`
  form; the F26 cases now pass a `retro-2-done` end.
- `gate_p1.py` (C1): carries `score_p2.json`'s NOT DETERMINED into `delivered versions (P2's form)` as it reads (the cut form with no
  `FAIL-CLOSED:` prefix); a presented version no later line judged follows the same rule (`extract_p2.end_of`); a FAIL stands over either.
  `gate_p1_cases.py`: three cases.
- `lena_lines.py` (C3): `retro1_expected(lines, offers)`, one rule for both arms (K40 at or before L0, K41 in L1 or L2, else RETRO-ASK at
  L3); `retro_places` accepts retro 1's RETRO-YES only in L1 or L2 and its RETRO-ASK only at L3. Cases: three for C3 and one for C2's row
  record (no row table exists in the module, so C2 needed no code).
- `probe.sh` (C4): `trap 'cleanup' EXIT` and `trap 'cleanup; exit 130' INT TERM`. `setup_stream.sh` (C4): `trap 'cleanup; exit 4' INT TERM`.
- `selfcheck.sh` (C4): part 5c, `trap_case`: a stub zsh script per driver with that driver's own trap lines is sent TERM and must run its
  cleanup and exit (130, 4) without its next command.
- `score_stream.sh` (C5): a `selfcheck-*` label reads its folder from `P2_EVDIR`, as `copy_org_evidence.sh` does. **A harness bug the C5
  check found:** the A-M time extraction printed the A-M line's turn number (`m.group(1)`) instead of that turn's start time
  (`m.group(2)`), so `--am-time 10` would have reached `score_p2.py`; fixed.
- `dryrun.sh` (C5): `score_stream.sh $LABEL` in both arms in place of the four direct calls (`extract_p2.py --checks`, `watch_views.sh`,
  `score_p2.py`, `gate_p1.py`); checks that `score-steps.txt` lists four `exit 0` lines, and in arm R the `--am-time` rule (left out with no
  A-M line; and, on a scratch copy with an A-M line added, passed as that line's turn start: the case for the bug above).

## Freeze fix (freeze attempt 1 failed; `../manager-decision-prereg-loop.md`, "Freeze attempt 1 failed on a timing fixture: ruling (b)")
**Independence:** I opened no file under `src/hirearchy/` (arm R or arm C). The fix rests on the dry run's own files and output.

Attempt 1's self-check on the frozen files read 18 of 19: the arm-R dry run's PF-0 expectation ("both timings built") failed because all 8
builds fell in the same second. A frozen self-check part must not depend on chance, so the fixture is built by construction.
- `dryrun_build.py`: `--align same|earlier` for `--phase pf0` (`to_second_boundary`). `same` starts the build 0.02 s after a whole-second
  boundary, so the first event record (`init`'s) and the charters' first commit (made by `apply`) share a second (the build takes well
  under a second). `earlier` waits until 0.05 s after the next boundary after `init`, before `apply`, so that commit is always in a later
  second than the first record. (A first attempt waited before the snapshot commit; the dry run showed the charters' first commit is
  `apply`'s own, so that wait changed nothing: 8 of 8 builds stayed `same`.)
- `pf0_timing.py` (new): `decide(builds)` and its command line. Every build reached must read as expected (`same` -> `PF-0 1 PF-1 0 new 0`,
  `earlier` -> `PF-0 0 PF-1 0 new 0`): 0 misclassified. At least one `same` build must exist (a PF-0 reproduced); none, or an empty list, is a
  FAIL. An `earlier` timing not reached is recorded `not reached; covered by the constructed cases <names>` and is no failure.
- `dryrun.sh`: one loop per timing (`same`, then `earlier`, at most 8 tries each, each recorded in `pf0-timing.txt` with the timing it
  was built as), the classifier's reading of each timing kept in `pf0-builds.txt`/`.json`, and one expectation on `pf0_timing.py`'s verdict
  (`pf0-verdict.txt`) in place of "both timings built". The per-timing checks are unchanged.
- `selfcheck_cases.py`: 10 new cases (166 of 166): all builds `same` (the old rule reads FAIL, the new PASS with the earlier timing `not
  reached` and the named cases), a misclassified `same` build FAIL, a misclassified `earlier` build FAIL, both timings PASS, only `earlier`
  FAIL, an empty list FAIL, a misclassified build over a reproduced PF-0 FAIL, the constructed `earlier second` case (the product gives
  the design's label; the classifier finds no difference), and that the named cases exist in the file. RED before `pf0_timing.py`
  existed: `ModuleNotFoundError: No module named 'pf0_timing'`. GREEN after: `selfcheck_cases: 166 of 166 ok`.
- `protocol.md` 13.3: the entry for this check describes the construction and the verdict. PF-0's signature, its readings and X3's rule
  are unchanged.


## Amendment 1 (`../manager-decision-row-R1-t7.md`; `../protocol-amendment-1.md` item 5; `../standing-rules-streams-amendment-1.md`)
**Independence:** in this pass I opened no file under `/Volumes/workspace/hirearchy/src/hirearchy/` (arm R) or
`/Volumes/workspace/hirearchy/.worktrees/p2-arm-c/src/` (arm C). I opened no other product source file either. The fixes rest on the
harness's own files, R1 v1's evidence (read only), P1's kept `injection-log.txt` and `window.txt` files (read only) and P1's synthetic-stream
test (`P1/evidence/harness/tests/test_extract_mechanical.py`, read only, as the model for the constructed stream). The self-check's (B)
cases run P1's `extract_mechanical.py`. That file imports the product's `client_questions` from `--product-src` (P1's one stated product
import, unchanged); no source file is opened for it.

**The pin.** `extract_mechanical.py` is unchanged. Its md5 is `73b27e25bd18ea9ec17ad5e64c7f6d1c`, equal to P1's `MD5SUMS` line and to P2's
frozen `MD5SUMS` line, and `amend1_cases.py` checks it. The wrapper below reads it as a module and edits nothing in it.

Test-first: the cases came first and were run on the frozen code (RED), then the fixes were written (GREEN).
- **(A) `turn.sh`'s sequence check was vacuous.**
  - Cause: its inline `strptime` forms rejected `+00:00`, and any unparsed time read as "no snapshot". The finding is in
    `../R1/harness-failures/turn-sh-sequence-check-vacuous.md`.
  - Fix: new `turn_seqcheck.py` (ISO 8601 with `Z`, `+HH:MM`/`-HH:MM` or none, at most 6 fraction digits). It prints `STOP:` on an
    unparseable time, a missing `quality/calls.txt`, or no record of the turn's snapshot. `turn.sh` calls it where the inline check was,
    and the line forms are unchanged.
  - RED: `MISMATCH (A) turn.sh: a first snapshot at 2020-01-01T00:00:00.000000+00:00, before the turn's end + boundary: STOP`, which got
    `after_turn sequential: checked (no snapshot taken: no org yet)`.
  - GREEN: all 10 (A) cases `ok`.
- **(B) The finish's extract crashed on an effort-stopped run's session without `messages.jsonl`.** The finding is
  `../R1/harness-failures/finish-r1-v1-findings.md` item 2.
  - Fix: new `extract_mechanical_p2.py`, and `finish_stream.sh`'s `EM_ARGV` now runs it with the same arguments.
  - It binds `open` in P1's module only, so a missing `messages.jsonl` beside an existing `session.json` reads as empty. That is what P1's
    own credit loop already does.
  - It checks each such folder against `run-session-map.txt` and the run log's `# kiro: effort not set` line. It appends `effort stops read
    as empty sessions (...): <k> (<run> -> <session>, ...)` to `cost.txt`, or fails closed: `cost.txt.unverified` with a `FAIL-CLOSED:`
    line, and exit 1.
  - RED: `MISMATCH (B) an effort-stopped run's session with no messages.jsonl: the finish's extract exits 0 and writes cost.txt`, which got
    `exit 1; FileNotFoundError: [Errno 2] No such file or directory: '/tmp/hirearchy-p2/selfcheck-amend1/B/stop/org-kiro-sessions/h0/sess_boss-scribe/messages.jsonl'`.
  - GREEN: all 7 (B) cases `ok` (cost.txt written, `1 (... -> sess_boss-scribe)` counted, `stream total credits: 3.50 (assistant 1.00 +
    org runs 2.50)`, fail closed without the mark, the pin).
  - On R1 v1 (read only, `--out /tmp/hirearchy-p2/amend1-r1v1-check`): `stream total credits: 26.66 (assistant 15.48 + org runs 11.19)`,
    with the stop `lead@20261029T104930658411 -> sess_f04502e1-4ad1-4466-87b6-479021f78e8b` counted.
- **(C) `window.txt` was left to the facilitator.** The finding is `../R1/harness-failures/finish-r1-v1-findings.md` item 1.
  - Fix: new `injection_window.py`, which `injection.sh` runs after the injection itself (a task id, with or without `--force`; never for
    `--dry-run`, `--selftest`, `--stop` or `--poll-check`).
  - It writes `S/injection/window.txt` as `<start> <end>` from the log's `window start (request):` and `window end (final progress):`
    lines, without their `Z`. On every P1 stream's log (F1-F3, I1-I3) it reproduces the kept `window.txt` byte for byte.
  - A log with no end gives a `NOTE:` line and no file. An existing different file is kept, with a `STOP:` line.
  - RED: `MISMATCH (C) injection.sh writes S/injection/window.txt from the log, with no facilitator step: ...`, which got `exit 0;
    window.txt None`.
  - GREEN: all 4 (C) cases `ok`. A stand-in `uv` on `PATH` writes E7's log lines, so no product call is made.
- **The rows and the composition rule (protocol amendment 1 items 2-3).** `lena_lines.py` gains `ext_no_not_first(lines)`, which lists
  every line whose rows hold K48 after another row (in `counts()` as `ext_no_not_first`), and 13 constructed cases:
  - each new row's record (`K62` ... `K66 (yes/no form)`);
  - the composed line of R1 v1's turn-7 mapping (read, EXT-NO counted once, no one-off window bounded);
  - `ext_no_not_first` both ways;
  - K62-K66 not moving L0.
  RED: `lena_lines selfcheck: 36 of 37 ok` (`MISMATCH amendment 1 item 3: ext_no_not_first (KeyError: 'ext_no_not_first')`). GREEN:
  `lena_lines selfcheck: 37 of 37 ok`. The module still holds no row table: rows are read as recorded.
- `selfcheck_cases.py`: one case. The ACT-REQ window runs across the composed EXT-NO + L-INJ + K62-K66 line to the LIST-KEEP, with its
  bounds read by `lena_lines.counts` from written lines, and holds one task. It passes on the frozen code too: a guard, not a fix,
  `selfcheck_cases: 167 of 167 ok`.
- `selfcheck.sh`: part 5d, `amendment 1: sequence check, effort-stop cost, window.txt` (`amend1_cases.py --scratch $P/selfcheck-amend1`).
  The parts are now 20. RED of the new part: `amend1_cases: 4 of 21 ok`. GREEN: `amend1_cases: 21 of 21 ok`.
- **Not changed:** `arm.sh`'s `md5gate_ok` does not read amendment files, as P1's did not. The stream step checks them by the standing
  rules amendment's rule A, and the gate's coverage is left to the review (`../protocol-amendment-1.md` section 9). `after_turn.sh` is not
  changed: the injection wrapper writes `window.txt`.
- New files: `amend1_cases.py`, `turn_seqcheck.py`, `extract_mechanical_p2.py`, `injection_window.py`. Changed: `turn.sh`,
  `injection.sh`, `finish_stream.sh`, `selfcheck.sh`, `lena_lines.py`, `selfcheck_cases.py`, this file. `MD5SUMS` is not rewritten here:
  the re-freeze comes after the independent review.


## Amendment 1, review rulings (`../manager-decision-row-R1-t7.md`, "Amendment 1's review: rulings"; `../amendment-1-review.md`)
**Independence:** in this pass I opened no file under `/Volumes/workspace/hirearchy/src/hirearchy/` or
`/Volumes/workspace/hirearchy/.worktrees/p2-arm-c/src/`. No `.md5`, `MD5SUMS` or `freeze.txt` was written, and `../R1/` was neither moved
nor edited. The pre-pass copies of the changed files are in `/tmp/hirearchy-p2/rulings-orig/`.

Test-first: each case was written and run before the code it tests (RED), then the code (GREEN).
- **D1: `arm.sh`'s `md5gate_ok` gates the amendment files.** It now also checks every `$EV/protocol-amendment-*.md` and
  `$EV/standing-rules-streams-amendment-*.md` (zsh globs with `(N)`, so none is no error) against `<name>.md5` beside it, first field. A
  missing `.md5` prints `md5 gate: <name>.md5 missing (<name>.md not frozen)`, a different one `md5 gate: <name>.md differs from
  <name>.md5`, and either fails the gate. The callers are unchanged: `setup_stream.sh:21`, `turn.sh:17` (stream labels only),
  `next_stream.sh:10`, `finish_stream.sh:71`. The self-check's wrapper part and both dry runs use `selfcheck-R`/`selfcheck-C` labels and
  never call the gate, so they are unaffected (the full self-check below passed with the real amendment `.md5` files absent).
  - The cases: `amend1_cases.py` part (D), 7 cases. Each builds a constructed EV copy under `--scratch` (protocol.md, the standing rules,
    `harness/MD5SUMS` with one line, and the amendment files as the case needs), then calls `md5gate_ok` in isolation (`source arm.sh
    selfcheck-R`, then `EV` and `H` pointed at the copy). No amendment file passes; both with matching `.md5` pass; `protocol-amendment-1.md`
    without its `.md5` fails; `standing-rules-streams-amendment-1.md` with a different `.md5` fails, and without one fails; a later
    `protocol-amendment-2.md` without its `.md5` fails; an amendment edited after its `.md5` fails.
  - RED (frozen-review `arm.sh`; output kept in `../harness-selfcheck/amendment-1-red/rulings-amend1.out`): `amend1_cases: 23 of 28 ok`,
    the five fail cases `MISMATCH`, each with `got: rc 0;`, for example `MISMATCH  (D) D1: protocol-amendment-1.md without its .md5: the
    gate fails, naming it`.
  - GREEN: `amend1_cases: 28 of 28 ok`.
  - On the real EV (read only) the gate now reads, among its lines, `md5 gate: protocol-amendment-1.md5 missing (protocol-amendment-1.md
    not frozen)` and the same for the standing-rules amendment, then the stale `MD5SUMS` lines. So no stream can set up before the
    re-freeze writes both `.md5` files, as D1 (f) intends.
- **`lena_lines.py`: 6 cases for the rulings** (43 of 43): the records `K67`, `K68`, `K68 (yes/no form)` and `K65 (either/or of existing
  agents)` each read as one row with rule `ANSWER`; A1's composition records `K48, K65 (open form)` and `K48, K64 (open form)` read with
  EXT-NO first, and K48 after an open line is listed by `ext_no_not_first`; a K48 + K67 + K68 line bounds no ACT-REQ window, counts EXT-NO
  once, and K67/K68 move no L0. **No parser code changed:** rows are read as recorded, so the new rows need no rule-id or row parsing.
  These cases passed on first run against the unchanged parser functions; they are guards, not RED-GREEN fixes. `lena_lines` reads no
  line text, so A9's numbering has no case here.
- **`selfcheck_cases.py`: 1 case for D2 (e)** (168 of 168): WEEK-LIST at turn 20, a `K58, K55 (yes/no form), K63, K64, K66` answer line at
  turn 21, the task in turn 21's reply, LIST-KEEP at turn 22; the week window, from `lena_lines.counts` over the written lines, runs to turn
  22 and holds the task as a one-off. It passed on first run (the window code needs no change; a guard). A negative control, run once
  outside the file with the answer line forced into the bounds, gave `to_turn` 21 and no task, so the case discriminates.
- **Full self-check** (`zsh selfcheck.sh`, started 2026-10-29T11:59:11Z, after the last harness code edit; exit 0): `SELFCHECK: 20 of 20
  parts passed`. Part 5d `amend1_cases: 28 of 28 ok`; `lena_lines selfcheck: 43 of 43 ok`; `selfcheck_cases: 168 of 168 ok`; both dry runs
  0 mismatches. This file was edited after the run (text only).
- **Superseded:** the "Not changed" bullet of the "Amendment 1" section above (`md5gate_ok` does not read amendment files) no longer
  holds: D1 changed it.
- Changed in this pass: `arm.sh`, `amend1_cases.py`, `lena_lines.py`, `selfcheck_cases.py`, this file. The re-freeze adds `arm.sh` to
  `MD5SUMS`'s changed files (D1 (e)); the other three were already on its list.
