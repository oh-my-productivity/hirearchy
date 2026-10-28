# P1 harness: changes against G0's harness (protocol 10)

Built from G0's frozen harness (`studies/G0-noise-baseline/evidence/harness/`, `MD5SUMS` md5 `be21347995b821185a2adaba36d8390c`, pinned in
protocol 2.1) with **the M1 treatment only**: no dedicated kiro home, no `prepare_m0_home.sh`, `env -u KIRO_HOME` in both arms. The full
`diff -u` of every changed file against G0's is at the end of this file (regenerated in iteration 3). Iteration 2 of the pre-registration:
revised against `../prereg-review.md` (section "Iteration 2" below; protocol section 17.1). Iteration 3: revised against the iteration-2
review under the manager's binding directives `../manager-decision-prereg-loop.md` (section "Iteration 3" below; protocol section 17.2).
Iteration 3b: the manager's amendments C1-C8, applied before the freeze (section "Iteration 3b (manager amendments)" below; protocol 17.3).

## Independence of the re-derivation (F-G0-4; design 18.6; the brief)
**The author of `rederive_watch.py` (and of `watch_cases.py`, `g1_cases.py` and `kept_mail.py`, which construct its inputs, and of
`guarantees.py`, which reads it) did not open `src/hirearchy/` while writing it, nor at any other time in iteration 1, iteration 2,
iteration 3 or iteration 3b (the manager's amendments) of this step.** (Iteration 3 changed `rederive_watch.py`'s `k_time`, `pinned`, `compare_window`, `compare_services`,
`load_contracts`, `product_watch`, `run_stream` and `run_spend`, and added `unread_snapshots` and `lower_times`, from the design's text and
the review's findings only; see "Iteration 3".) What was read instead:
- the design texts: `docs/design/org-growth-phase-1.md` sections 1, 3, 4.1-4.2, 4.4 (the repair migration and its carried watches), 8 (8.1's
  table and rows, 8.5's settler and its reply sentences), 13, 14.3-14.4, 18, 21.1, 24, 25; `org-growth-phase-0a.md` 3.1-3.4 (`source`, its
  legacy and unknown readings, `Assertion`, criterion ids `C<k>`, `R<k>`), `org-growth-phase-0a2.md` (the contract version's
  `answers`/`about`/`words`, the product's link, `answer_ids`), `org-growth-phase-0b.md` section 3 (case, delivery, verdict on a delivery,
  counted, judged, superseded, `case_spend`, user's runs, user's approved runs) and `org-growth-phase-0b1.md` 3 (F-G0-2's `case_spend` and
  `user_spend`, `user_committed`); `phase-0b1/f-g0-7.md` section 1 (the empty-argument record);
- the file formats, from the kept G0 and E7 evidence (message frontmatter of root's `sent/` and received `read/`; `SERVICE.md` versions, the
  v1 criteria of G0 m1-s1..s3 and E7 s1; the session store's `tool_call`/`tool_result` records and the `tool_load` reply's `loaded` list;
  `cost.txt`) and from the design (the item-format `PLAYBOOK.md` of 4.1-4.2; the `services` watch suffix of 14.3);
- the product CLI's `--help` output (`hirearchy --help`, `define-service --help`, `services --help`, `init --help`, `hire --help`), for the
  command forms of the lock hook and the probe (iteration 1);
- **one product output file**, declared (iteration 1): the `watch` list of `tests/golden/expected/quality/e3.json` (a golden output, not
  source), read only for the JSON key names and value shapes the comparison needs (`r` a 2-list, `since` null for an item never watched). No
  rule was taken from it. Iteration 2 read no product file at all. Iteration 3 read no product file either: the design's section 3 rows of
  `K`, text tokens and `strip_markers`, 8.1 (its table, the monotonicity property and its one exception), 21.1 and 25.2 item 14; E7's
  protocol 10.4 and D18; G0's `STUDY.md` ("What Phase 1 must know", the band table, A1/A2); and, for formats, G0's kept `cost.txt` (the
  `runs without a matched session` and `total runs` lines) and the key names of a kept `quality/end.json` service entry (`service`, `owner`).
`rederive_watch.py` imports no product module (stdlib and PyYAML only). The G0 modules copied unchanged keep their one stated product import
(`extract_mechanical.py`: the client-questions parser, G0's), which the re-derivation does not use.

## Files
| File | Status | What changed and why |
|---|---|---|
| `run_turn.sh` | rewritten from G0's | labels F1-I3; `env -u KIRO_HOME` in both arms (no M0 branch); profile `hirearchy-study-p1-<label>-assistant`; refuses turn 31 (the cap, protocol 4.2); the chat line and `; sleep 20` byte for byte as G0's/E7's |
| `after_turn.sh` | rewritten from G0's | M1 only; the empty-argument call counter (the session-store count of f-g0-7 section 1 via `empty_calls.py`, the stderr grep beside it); the org-run cap (`CAP:` at 130 runs, every run counted); root's new requests by notes file (`requests-by-turn.txt`, M3-VERDICT's trigger); **arm F's lock hook** with its three checks (check 2: `locked: true` at the version before + 1), H-LOCK, and the lock-held check after every turn (`lock/lock-held.txt`) (design 18.2; protocol 1.1); `services_snapshot.sh` after `quality_snapshot.sh` |
| `services_snapshot.sh` | new | root's `services` after every turn and at the end, `quality_snapshot.sh`'s twin; start and end to the microsecond; iteration 3: the output's size on the `calls.txt` line and a `NOTE:` when unread (protocol 12.1) |
| `setup_stream.sh` | edited | labels; M0 branches removed; the owner's `memories.db` md5 before the stream (and against the previous stream's after value); a replacement needs the manager's recorded approval, is `<label>r`, and one per arm; the `KIRO_HOME` gate; `setup.txt` shows the profile diff raw and with the label and the epoch masked; iteration 3: **the memories gate** (`memories_gate.py`) after the gates and refusals and before anything is created, exit 4 on a change since the previous stream without `manager-decision-memories-before-<label>.md` (P2-M6) |
| `finish_stream.sh` | edited | M0 removed; the end `services` snapshot; `extract_mechanical.py --p1`; `score_memos.py --memos 6`; `memories.db` after (a change prints `STOP:`); empty-call totals (the session-store count decides); `credits.txt` (`cost_total.py`); arm F's H-LOCK re-check with the lock-held check over the copied versions; iteration 3: the lead read from `lock/hook.txt`, a missing record is H-LOCK (L8) |
| `copy_org_evidence.sh` | edited | also copies every archived contract and playbook version (`services/*/history/`) and the current files, so a run that wrote two versions loses none |
| `quality_snapshot.sh` | edited | paths, labels; start and end to the microsecond (the race rule of protocol 12.1 G1(f)); iteration 3: the output's size and whether it is valid JSON on the `calls.txt` line, and a `NOTE:` when unread (protocol 12.1, P2-M2) |
| `safety-snapshot.sh`, `skill_check.sh`, `model_check.sh` | edited | paths, labels, sha `8bf7c69b`, skill md5 `b1023863...`; the M0 parts removed (one kiro home) |
| `profile-template.json` | edited | `name`, `description`, `ORG_ROOT` with P1's names; every other byte G0's (= E7's): the arms' profiles differ only in the label and the sandbox epoch |
| `extract_mechanical.py` | extended | `--p1` runs `rederive_watch.py` and `guarantees.py` after G0's extracts; the sandbox-name pattern also exempts `hirearchy-p1` (as it did `e7`, `g0`); `cost.txt` stays G0's byte for byte (G0's tests compare it) |
| `guarantees.py` | new (rewritten in iteration 2) | the mechanical procedures of G1 (a)-(f) and G2 (a)-(c) on a `Stream` object (so `g1_cases.py` runs them on constructed flows), the roles (A and B by any gated change, B's carrier, [sections-crit] and [owner-crit] by text), the orders O1-O10 with O6 and the extra rejections, protocol 12.1.1's expected states and G1(b)'s reading; iteration 3: the legal steps into `kept` (P2-M1), the unread rule (P2-M2), the bounded `could not retire` reply (L5); iteration 3b: G2(a) one note per rejection on its memo's case, the rules a list (C3), (b)'s `late_detail` (C1) |
| `score_memos.py` | extended | memos 4-6 (`KEY_P1`, pre-registered keyword sets), the owner forms N/I/N+J, `p1_no_regression` (12.3 part 1; iteration 3: `mechanical_pass` holds G0's gate-able parts only, the Summary, the order and the owner form go to `reported`, the manager's M7 decision); `--memos 3` (the default) is G0's scoring byte for byte (`g0_replay.py`); the default key path is P1's copy (same md5) |
| `aggregate.py` | rewritten (again in iterations 2 and 3) | P1's pass rules per stream and per arm and the exit verdict (12.4): judged keys read as `.value`, missing = NOT DETERMINED; G1(d) from the judged reading with every hit decided; iteration 3: no regression = G0's gate-able memo parts + the judged D8 deliveries; the exit on `G1 (arm I)`, `G2 (arm F)`, `G2 (arm I)`, `no regression (arm I)`; reported: `no regression (arm F)` with every regression line's judged cause (a shared mechanism is a product finding), the Summary/order/owner-form parts and D14 (NOT DETERMINED on a missing case); iteration 3b: a stream ended by ruling (b) (C1) and `before_failure`'s keys (C7) |
| `rederive_watch.py` | new (edited in iteration 2) | the independent re-derivation of the watch and of the spend figures (13); iteration 2: the race rule over each snapshot's record times, pinned and unpinned keys, root's `services` suffix compared, and section 3's four readings (tiers, `about` current, carried watch (ii) by text key, B3 in `K`); iteration 3: `K` after a corrected link (the search no longer stops at the first warned record), the unread rule, the pinned keys of 25.2 item 14, the race rule's 5-s lower margin, `defined` required above v1, `--spend --stream` with `missing_cases`/`extra_cases`, the owner matched in `product_watch` |
| `cost_total.py`, `empty_calls.py` | new | the stream's credits (protocol 11) and the session-store empty-call count (f-g0-7 section 1), each with its `--selfcheck` on G0's evidence; iteration 3: runs without a matched session added at the mean per matched run and flagged (L1) |
| `memories_gate.py` | new (iteration 3) | the memories gate between two streams (protocol 8, P2-M6), called by `setup_stream.sh` before anything is created |
| `watch_cases.py`, `g1_cases.py`, `kept_mail.py`, `p1_scoring_check.py`, `aggregate_check.py`, `next_stream_check.py`, `probe_check.py`, `g0_replay.py`, `selfcheck.sh`, `selfcheck/p1-kept-mail-expected.json` | new / rewritten | the self-check (13.3); iteration 2 adds `g1_cases.py`, `aggregate_check.py`, `next_stream_check.py`, `probe_check.py` and the `cost_total`/`empty_calls` parts, and to `watch_cases.py` 8.1 row xii and B3's equal stamp (its `flow` also returns every memo's head and takes the variants and the settler `g1_cases.py` needs; its builder writes `admitted: c` for a gated change citing one R and a C); iteration 3 adds to `watch_cases.py` 8.1's exception the other way (a corrected link unrelating the only related rejection, after and before `D`), to `g1_cases.py` the P2-M1 flows, the P2-M2 cases and the rule on constructed `calls.txt` files, the L5 cases and the L3/L4 comparisons, to `kept_mail.py` the D14 ledger's completeness on G0's mail, to `p1_scoring_check.py` no regression's gate-able and reported parts, to `aggregate_check.py` the M7 exit and the reported lines (15 scenarios), to `next_stream_check.py` the memories gate and its place in `setup_stream.sh` |
| `probe.sh`, `probe_compare.py` | new (edited in iteration 2) | the preflight probe (18.3 item 2): `tool_load` compared per loaded tool; the session-store empty-call count; the `KIRO_HOME` refusal; check 2 at the version before + 1 |
| `next_stream.sh` | new (replaces `run_arm.sh`; rewritten in iteration 2) | the pre-registered order with replacements, the stage gate, the 185.00-credit pause on `credits.txt`, the memories refusal (a change during a stream; between streams: the memories gate), one replacement per arm (`P1_NEXT_STREAM_EV` is `next_stream_check.py`'s only override) |
| `spend-ledger-template.json`, `p1-judged-template.json` | new | the D14 ledger and P1's judged keys (iteration 2: `g1_d_judged` with `hits_decided`, `d8_presented_deliveries`, `harness_trace`; the keys that became mechanical removed; iteration 3: when a case entry is made (P2-M3), and `regression_causes` (M7)) |
| `prepare_m0_home.sh`, `run_arm.sh`, `tests/test_drivers.py`, `tests/test_aggregate.py` | not carried | the M0 home is not built (F-G0-7 section 4, binding); `run_arm.sh`'s arms are G0's; the two tests test those drivers and G0's aggregate |
| `MD5SUMS`, `CHANGES.md` (G0's) | not carried | P1's `MD5SUMS` is written by the freeze step; this file is P1's |
| every other file (`inject_root_rework.py`, `injection_files.py`, `test_poll_loop.py`, `ambient_*`, `org_state.py`, `extract_tool_calls.py`, `extract_proposals.py`, `assistant_facts.py`, `scheduler_survival.py`, `ambiguity_recall.py`, `prompt_sizes.py`, `playbook_attempts.py`, `rederive_quality.py`, `skill_check.py`, `judged-template.json`, `workspace-cli.json`, `selfcheck/e7-expected-*.json`, `tests/test_*.py` but the two above) | byte-identical to G0's | the M1-treatment parts, unchanged; `g0_replay.py`, G0's module self-checks and G0's module tests show it (13.3); `selfcheck/e7-expected-drivers.json` is kept as G0 had it and is not read |

## Iteration 2: how each finding of `prereg-review.md` was resolved (harness side; the protocol side is protocol section 17)
- **H1**: `cost_total.py` (new) computes a stream's credits as protocol 11 defines them (`total assistant credits` + every org run's credits,
  decimals, half-up to 2 places) into `credits.txt` (`finish_stream.sh`); `next_stream.sh` reads only that line and compares `> 185.00`
  (Decimal), refusing a stream without it. An appended line in `cost.txt` was tried first and broke 7 of G0's byte-for-byte tests, so the
  figure lives in its own file (first-run item 7). Self-check: G0's six streams give G0's published totals (62.98-71.99); 185.00 not over,
  185.01 over, a missing line refused (`cost_total`, `next_stream` parts).
- **H2**: `aggregate.py` reads `judged.json[key].value`; a missing file, key or null value makes the part NOT DETERMINED, never a pass;
  `aggregate_check.py` checks 11 scenarios (66 lines: true, false, missing, undecided hits, invalid streams, `before_failure`, D14, D8, a missing
  `validity.json`, a mechanical fail).
- **H3**: `guarantees.py` rewritten: O9's carry is an add, gated edit or restore into B's text key (or a restore of B's id) after an owner
  retire at any time before R5's answer; memo 5's and memo 4's unrelated answers are read by section 3's relation; O5's variant expects A
  `warning`; B's carrier is set from the re-derivation's carried watch; protocol 12.1.1's table is `expected()`. `g1_cases.py` runs every
  order and variant through `g1()` against the table (30 flows, 7 of them negative cases).
- **M1**: G1(a) (i) reads the re-derivation too; (ii) a step out of `kept`/`restored`/`retired` needs a gated change between the snapshots;
  (iii) `kept -> warning` / `warning -> new` need a corrected link between them; G1(b) (2) timing and (3) `restores` are verdict parts, and
  (4) a spurious runtime retire and (5) a missing expected retire fail.
- **M2**: the keyword screen only lists hits; G1(d) is `NOT DETERMINED (judged reading)` in `g1.json`, decided by `aggregate.py` from
  `g1_d_judged` with every hit in `hits_decided`; a counter-rule case in `g1_cases.py` and in `aggregate_check.py`.
- **M3**: `find_roles` takes A and B from any gated change (add, gated edit, gated restore), with version and op in `g1.json` and
  `guarantees/roles.txt`.
- **M4**: the snapshot scripts record start and end with microseconds; `rederive_watch.py` compares each key against the re-derivation at the
  start, every record time inside and the end; mismatch lines say `pinned` or `unpinned`; root's `services` suffix (14.3) is parsed and
  compared (`SERVICES-MISMATCH`, `SERVICES-UNREAD`); `guarantees.py` fails G1(f) on pinned, missing and services mismatches only, is NOT
  DETERMINED on an unread line, and `aggregate.py` makes G1(f) NOT DETERMINED on a `harness_trace`. `g1_cases.py`'s comparison checks.
- **M5**: `orders.json` `extra_rejections` with what each relates to; an extra related rejection makes that item's expectation the
  re-derivation's (rows A3, B4); `g1_cases.py` "an unscripted rejection relates to B early".
- **M6**: [sections-crit] and [owner-crit] by text from v1 (checked against the four kept v1s: G0 m1-s1 C3/C6, E7 s1 C2/C5, G0 m1-s2 and
  m1-s3 none/none); O10 = the ids memo 4's version re-added (`Criteria.readded`), and whether [owner-crit] is among them; O6 classified.
- **M7**: `after_turn.sh` writes root's new requests by notes file (`requests-by-turn.txt`), the trigger of M3-VERDICT; `REJECT_RULES` holds
  M3-MARTA and VR-REJECT (the protocol defines the composed ids).
- **M8**: protocol only (the table).
- **M9**: `after_turn.sh` writes `lock/lock-version.txt` and, after every later turn, `lock/lock-held.txt` (`STOP: H-LOCK` on a version from
  the lock on without `locked: true`); `finish_stream.sh` checks the same over the copied `service/` versions.
- **M10**: `probe_compare.py` compares a map tool id -> md5 of its `loaded` entry (a tool loaded in some sessions only is reported); the
  empty-call count is `empty_calls.py`'s session-store count (f-g0-7 section 1), in the probe and in the streams; `probe_check.py` (6 cases)
  and `empty_calls.py --selfcheck` (G0's 15/19/16 and 0/0/0).
- **M11**: no regression's D14 part reads `measures/spend-rederived.json`'s `d14_within`; only `d8_presented_deliveries` is judged.
- **M12**: `rederive_watch.py`: (i) the repair migration's carry by text key against the rendered line (`rendered_key`, the watch's `alias`
  for the rejections before the repair, `Change.earlier` for W1's token history); (ii) `about_before` keeps the criteria current at the
  live-from (`Criteria.current_at`); (iii) `k_time` tests a contract version's time first in B3's order (`World.as_of_b3`); (iv) `tier_of`
  reads a missing `source` as human and any value but `human` as relayed. `watch_cases.py` adds 8.1 row xii and B3's equal stamp; the kept
  G0 and E7 mail still give 132 of 132.
- **M13**: `next_stream.sh` walks each label then its approved replacement, applies every refusal to replacements, and refuses two
  replacement approvals in one arm; `setup_stream.sh` refuses a second replacement folder in an arm; `after_turn.sh` counts every run log for
  the cap. `next_stream_check.py` (15 cases).
- **N2**: the first-run counts below and in `SELFCHECK.md` agree. **N3**: `after_turn.sh` cites protocol 1.1, `run_turn.sh` 4.2. **N4**:
  `setup.txt`'s masked diff. **N5**: `setup_stream.sh` gate 7 and `probe.sh` refuse with `KIRO_HOME` set. **N6**: `unrated_at` takes the
  latest task of the case created before the accept. **N7**: `after_turn.sh` and `probe.sh` check `locked: true` at the version before + 1.
  **N1**, **N8**, **N9**: protocol only.

## Iteration 3: how each finding of the iteration-2 `prereg-review.md` was resolved (harness side; the protocol side is protocol 17.2)
Under the manager's binding directives (`../manager-decision-prereg-loop.md`). `src/hirearchy/` was not opened (Independence, above).
- **P2-M1** (adopt as written): `guarantees.py:g1_a` explains `retired|restored -> kept` by an exempt restore of a client-written text of
  that id between the snapshots (`client_restores_between`) and `warning -> kept` by a corrected link between them (reported), the reviewer's
  code. `g1_cases.py`: "retired -> kept: an exempt restore ..." (PASS), "NEGATIVE retired -> kept with no restore ..." (FAIL), "warning ->
  kept: a corrected link ..." (PASS), "NEGATIVE warning -> kept with no corrected link" (FAIL). **Harness bug found by the new flow:**
  `rederive_watch.py:Derivation.k_time` stopped its search at the first record from `D` on at which the item had a related rejection, so a
  corrected link that unrelated the only related rejection left the item `new` for good, where section 3 defines `K` as the earliest record
  at or after `D` whose files derive `kept` (the link itself). Fixed: every record from `D` on is tested (a warned item fails the kept test at
  each, so B1's "never defined for a warned item" still holds); `watch_cases.py` gains the two rows (after `D`: warning, warning, kept at
  the link with `K` = the link; before `D`: warning, new, kept at `D`). No other case changed its result (`SELFCHECK.md` item 12).
- **P2-M2** (adopt as written): `rederive_watch.py:unread_snapshots` (exit not 0; output missing or empty; quality not valid JSON; a turn of
  `turn-times.txt`, or the end, with no `calls.txt` line; `traceback` when the stderr file has `Traceback (most recent call last):` and a
  frame under `src/hirearchy/` or `site-packages/hirearchy/`); `run_stream` compares no unread snapshot and writes `UNREAD` lines;
  `guarantees.py` (`Stream.unread`, `load_stream`) gives an unread snapshot no product view, lists `unread_snapshots` in `g1.json`, makes
  G1(a) and G1(f) NOT DETERMINED (G1(f) FAIL with `product_defects_unread` on a product traceback), G1(e) NOT DETERMINED when the end view
  is unread or does not list B, and `state_at_end` reads the `end` view only; G1(f2) compares the product side only when the end view is
  read. `quality_snapshot.sh` and `services_snapshot.sh` add the size (and the JSON check) to the `calls.txt` line and print a `NOTE:`.
  `g1_cases.py`: an empty `turn-05.json`, an empty `end.json`, a product traceback, and `unread_snapshots` on constructed `calls.txt` files.
- **P2-M3** (adopt as written; D14 is a reported part under the M7 decision): `rederive_watch.py --spend ... --stream <dir>` reads the
  service's cases from the mail and writes `missing_cases` and `extra_cases` (the template's placeholder entry is skipped);
  `aggregate.py:d14` is NOT DETERMINED on a missing case or when the completeness was not checked; `spend-ledger-template.json` says when the
  stream step creates an entry. `aggregate_check.py` (two scenarios), `kept_mail.py` (the completeness on G0 m1-s1..s3: 3 cases each).
- **P2-M4, P2-M5**: protocol only (4.2; 5).
- **P2-M6** (adopt as written): `memories_gate.py` (new) compares the current md5 with the previous stream's `memories-md5-after.txt` in the
  order (replacements included) and exits 4 with a `STOP:` line unless `manager-decision-memories-before-<label>.md` exists;
  `setup_stream.sh` calls it after its gates and refusals and before the stream folder, the sandbox and the profile (dry-run reports it),
  and writes the gated md5 to `memories-md5-before.txt` and the gate's line to `memories-db.txt` (iteration 2's after-the-fact
  `memories.db changed since ...` line, which stopped nothing, is gone). `next_stream_check.py`: seven gate cases and the gate's place.
- **P2-M7** (the manager's decision): `score_memos.py:p1_no_regression` keeps G0's gate-able parts in `mechanical_pass` (decisions, actions,
  wrong dates, extra rows of each final memo; every copied version's wrong dates and extra rows; a memo never delivered) and moves the
  Summary/order and the owner form to `reported`; `aggregate.py` decides the exit on four lines, reports `no regression (arm F; reported,
  not a pass rule)` and the per-arm reported lines, and lists every regression line with its `judged.json` `regression_causes` entry (a
  mechanism in `SHARED` makes it a product finding; a line without an entry prints `cause NOT DETERMINED`); `p1-judged-template.json` gains
  `regression_causes`. `p1_scoring_check.py` (5 checks), `aggregate_check.py` (15 scenarios, 150 checks).
- **L1** (the conservative option): `cost_total.py` adds N x the mean credits per matched run (the per-model sum over the `total runs`
  lines less N) and flags the line; no figure with N > 0 and no matched run. Self-check: 2 of 42 unmatched, 42 of 42, none, a flagged line
  over 185.
- **L3**: `rederive_watch.py:pinned(key, state, never_watched)` (k, r, since of a never-watched item pinned; related of a restored item
  not); `compare_window` reads "never watched" as `since` None in every candidate. **L4**: `RACE_LOWER` = 5 s, `lower_times`, `RACE-LOWER`
  lines in `compare_window` and `compare_services`, counted apart. **L5**: `guarantees.py:results_between` (the `RESULT [<utc>]` blocks of
  `assistant-tool-calls.txt` between the second answer and the retire). **L6**: `load_contracts` raises on a version above 1 without
  `defined`, naming its file (`_version_files(..., with_path=True)`). **L8**: `finish_stream.sh` reads the lead from `lock/hook.txt` (no
  record: H-LOCK); `product_watch` matches the owner when the entry names one. **L9**: `_MARKER` declared (protocol 13.4 item 11 and the
  docstring). **L2, L7**: protocol only.

## Iteration 3b (manager amendments): C1-C8 of `../manager-decision-prereg-loop.md` (harness side; the protocol side is protocol 17.3)
Applied before the freeze by the separate manager-ordered step, after the loop was closed by decision ("The loop is closed by decision after
pass 3"), each as the decision and the iteration-3 review's fix text (`../prereg-review.md`, P3-M1 to P3-L5) say.
**Independence (F-G0-4):** no file under `src/hirearchy/` was opened in this step, and no product file at all (no golden output either).
`rederive_watch.py` was not changed by the amendments; the files changed are `guarantees.py`, `aggregate.py`, `g1_cases.py`,
`aggregate_check.py` and `selfcheck.sh`'s part comments. What was read: the decision, the iteration-3 review, `protocol.md`, this file,
the harness files above with `watch_cases.py`'s builder, `rederive_watch.py`'s `Mail`/`iso` (harness code), `setup_stream.sh`, E7's
protocol 4.10 (L-ASIS's sentences, `script/e7-protocol.md`) and G0's kept `lena-lines.txt` and `turn-times.txt` (formats).
- **C1 (P3-M1)**: `aggregate.py` reads `validity.json` `ended_by_ruling` (`check_validity`: `{"turn": n, "file":
  "manager-decision-row-<label>-t<n>.md"}`, the file in `EV/`, else a `ScoringError`). For such a stream, no regression's mechanical part
  is NOT DETERMINED when it fails only through memos whose `per_memo[m].final` is null and `delivered_bad` is empty (`ruling_cut_memos`),
  and its reported Summary/order/owner-form part likewise (12.3 part 1: "for this part and for the reported parts"); G2 (b), and (c) with
  it, is NOT DETERMINED when (b) fails only on `end` lines of rejections created at or after the ruling turn's start (`turn-times.txt`,
  `turn_start`; `g2_ruling_cut`). Every other FAIL stands. `guarantees.py:g2` writes `late_detail` beside `late_or_missing` (each line's
  kind `end`, `next_request` or `accept`, the R id, the note and its time). `aggregate_check.py`: the decision's scenario (I3 ended by
  ruling at turn 22, memos 5-6 undelivered, R5 unanswered: no regression ND, G2 ND, exit ND), a variant with memo 5's rejected version
  delivered, the same files without the ruling (FAIL), and four FAILs that stand (a delivered version's wrong date, memo 4's final memo
  wrong, R4 unanswered before memo 5's request, R5 created before the ruling turn); `g1_cases.py` checks `late_detail` on constructed mail.
  One reading, stated: the decision's scenario says "memos 5-6 undelivered" with "R5 unanswered"; R5 is the rejection of memo 5's first
  delivered version, so the scenario's files give memos 5-6 no final memo (as the decision says) and the variant gives memo 5 its rejected
  final memo; both must read NOT DETERMINED, and do.
- **C2 (P3-M2)**: protocol only for the rule; the harness reads `lena-lines.txt`, so `g1_cases.py` adds `M3-VERDICT + L-ASIS`: no
  rejection is read in it (G2(a) PASS with no note).
- **C3 (P3-M3)**: `guarantees.py`: `lena_line` (the parser, `lena_turns` uses it) reads the rules as a list in order (`RULE_TOKEN` also
  reads `VR-REJECT@<memo date>`); `rejections_of` maps H6, L-PLANT, M3-MARTA, L-MIND and L-GAP to memos 1-5 (`RULE_MEMO`) and a VR-REJECT to
  its `@` memo; `g2` (a) requires, for each (rule, memo) pair, one human-tier reject note in the turn's window with `mail.case_of(v.task) ==
  memo_case[memo]`, each note used once; a VR-REJECT naming no memo makes (a) NOT DETERMINED unless it FAILs. `g1_cases.py`: the
  decision's two cases (`M3-VERDICT + M3-MARTA + L-MIND`, one note: FAIL; two notes on the two cases: PASS), two notes on one case (FAIL),
  `VR-REJECT@2026-10-19` with L-MIND (PASS, the list parsed), two VR-REJECTs with one note (FAIL, the case a set collapsed) and with two
  (PASS), a bare VR-REJECT (NOT DETERMINED). G0's kept lines (`g0_replay`) still give G2 = PASS.
- **C4, C5, C6, C8**: protocol only (K37; `Also:`'s forms; 12.3 and 16 item 8; section 0).
- **C7 (P3-L4)**: `aggregate.py`: `BEFORE_FAILURE_KEYS` = `G1`, `G2`, `no_regression`; any other key, or a value other than `"FAIL"`, is a
  `ScoringError` (`main` prints it and exits 2). `aggregate_check.py`: `no regression`, `G1(b)` and `fail` refused, a malformed or
  unfiled `ended_by_ruling` refused (three cases), and an invalid stream with `no_regression` FAIL before the failure FAILs the arm.
- **Self-check**: every check added here passed on its first run (`SELFCHECK.md`, iteration 3b); no expectation was moved.

## The self-check's first runs (before any freeze): what was wrong and what changed
Recorded in `../harness-selfcheck/SELFCHECK.md` ("First runs"). Iteration 1: six mismatches, four of them errors in the self-check's own
cases or expectations (items 1, 2, 3, 5) and two harness bugs (items 4 and 6, the latter in two parts). Iteration 2: five, three of them errors
in the new checks' own cases (items 8, 10, 11) and two harness bugs (items 7 and 9). Each was fixed in the harness or in a case whose
construction contradicted the design; no expectation was moved to match an output (item 9's expectation was corrected to 8.5's text, with the
code). Iteration 3: one, a harness bug (item 12, `k_time` after a corrected link), found while constructing
P2-M1's `warning -> kept` flow, before its expectations were run; every other new check passed on its first run.

## diff -u against G0's harness (generated)

```diff
--- G0-noise-baseline/evidence/harness/after_turn.sh
+++ P1-itemized-playbook/evidence/harness/after_turn.sh
@@ -1,22 +1,31 @@
 #!/bin/zsh
-# G0 facilitator helper (protocol 6 item 3), frozen with the harness: usage after_turn.sh <label> <turn n>
-# -- no MCP/CLI call against the org (file reads, ps and the read-only quality snapshot at the very end).
-# E7's s<N>/prompts/after_turn.sh (E6 s1's helper, with the signal record fixed to read events/<date>/*.jsonl), generalized from a per-stream
-# copy to any G0 label. The assistant's session store is searched in the ARM's kiro home: M1 ~/.kiro, M0 <M0H>/.kiro (<label>/m0-home-path.txt).
-# Steps, in order: org state; the assistant session copy; the scheduler record (D-SURVIVE); the signal record (D-SIGNAL); model_check org and
-# assistant; the throttle scan; the ambient comparison (the md5 lines of the previous after-snapshot or setup, and this turn's before and
-# after: the owner's four lines and, for M0, the dedicated home's three); then quality_snapshot.sh <label> turn-NN LAST (it reads the org
-# through the product's CLI only when ORG.md exists).
+# P1 facilitator helper, frozen with the harness: usage after_turn.sh <label> <turn n>      (label F1..F3, I1..I3, replacements F1r ...)
+# G0's after_turn.sh (E7's per-stream helper generalized), M1 treatment only: the assistant's session store is searched in the owner's kiro home
+# (~/.kiro) in both arms; no dedicated kiro home exists. Steps, in order:
+#   1. org state; the assistant session copy; the scheduler record (D-SURVIVE); the signal record (D-SIGNAL); model_check org and assistant;
+#      the throttle scan; the ambient comparison (G0's, unchanged);
+#   2. the empty-argument call counter (design 18.3 item 3; f-g0-7 section 1): the session-store count (empty_calls.py on the copied session)
+#      and `grep -c 'is not available' turn-NN.stderr.txt` beside it, into empty-calls.txt; the org-run cap (protocol 4.2: 130 org runs, every
+#      run of the stream, the injection window included; a `CAP:` line ends the stream at the end of this turn, which stays valid); the
+#      memo requests root has sent (S/org/sent/, protocol 4.2's M3-VERDICT trigger), into requests-by-turn.txt;
+#   3. ARM F ONLY, the lock hook (design 18.2; protocol 1.1), once: after the turn in which the study service's SERVICE.md first exists (apply_org
+#      defined it), as root: `ORG_ROOT=<S>/org uv --directory /Volumes/workspace/hirearchy run hirearchy define-service <lead> <service> --locked`;
+#      then its three checks (the reply, SERVICE.md's frontmatter `locked: true` at the version before the hook + 1, the owner's quiet note
+#      `locked: false -> true (you may no longer revise the playbook)`) and H-LOCK (an owner's playbook version written before the lock); all of
+#      it into <label>/lock/; after the lock, every turn: lock/lock-held.txt lists `locked:` of every contract version after the lock version, and
+#      one that is not `true` prints `STOP:` (H-LOCK: the arm was not held, protocol 8);
+#   4. quality_snapshot.sh <label> turn-NN and services_snapshot.sh <label> turn-NN, LAST (each reads the org through the product's CLI only when
+#      ORG.md exists; each records its cli.command event file, a known harness actor for H6).
+# Lines starting `STOP:` mean the stream step stops at the end of this turn with a `warning` (protocol 8).
 LABEL="$1"; T="$2"
 REPO=/Volumes/workspace/hirearchy
-ST=$REPO/studies/G0-noise-baseline
+ST=$REPO/studies/P1-itemized-playbook
 EV=$ST/evidence
-[[ "$LABEL" =~ '^(m0|m1)-s[1-9][0-9]*(r[0-9]*)?$' && "$T" =~ '^[1-9][0-9]*$' && $# -eq 2 ]] || { echo "usage: after_turn.sh <label> <turn n>" >&2; exit 2; }
+[[ "$LABEL" =~ '^[FI][1-3](r[0-9]*)?$' && "$T" =~ '^[1-9][0-9]*$' && $# -eq 2 ]] || { echo "usage: after_turn.sh <label F1..I3> <turn n>" >&2; exit 2; }
 D=$EV/$LABEL; S=$(cat $D/sandbox-path.txt); SN=${S:t}
-ARM=${LABEL%%-*}
+ARM=${LABEL[1,1]}
 KH=$HOME/.kiro
-[[ "$ARM" == m0 ]] && KH="$(cat $D/m0-home-path.txt)/.kiro"
-PROFILE=hirearchy-study-g0-$LABEL-assistant
+PROFILE=hirearchy-study-p1-$LABEL-assistant
 NN=$(printf '%02d' "$T")
 python3 $EV/harness/org_state.py $S "after turn $T" >> $D/run-counts-by-turn.txt 2>&1
 python3 - "$S" "$D" "$KH" "$PROFILE" <<'PY'
@@ -33,7 +42,6 @@
 shutil.copy2(best,D+'/assistant-session.json'); shutil.copy2(os.path.dirname(best)+'/messages.jsonl',D+'/assistant-session-messages.jsonl')
 print('session copied from',best)
 PY
-# scheduler record for D-SURVIVE (protocol 6): UTC time, scheduler.pid content, ps line
 {
   echo "--- scheduler record after turn $T at $(date -u +%FT%TZ)"
   if [[ -f $S/org/.runtime/scheduler.pid ]]; then
@@ -47,7 +55,6 @@
   echo "scheduler.exit: $( [[ -f $S/org/.runtime/scheduler.exit ]] && cat $S/org/.runtime/scheduler.exit | head -3 | tr '\n' ' ' || echo '(none)')"
   echo "processes referencing the sandbox name:"; ps -axo pid,ppid,stat,etime,command | grep -F "$SN" | grep -v grep || echo "(none)"
 } >> $D/run-counts-by-turn.txt 2>&1
-# signal record (E7 item 5; D-SIGNAL): every scheduler.signal line in events/ (file reading only)
 {
   echo "--- signal record after turn $T at $(date -u +%FT%TZ): every scheduler.signal line now in S/org/.runtime/events/ (cumulative)"
   if [[ -d $S/org/.runtime/events ]]; then
@@ -60,12 +67,131 @@
 } >> $D/run-counts-by-turn.txt 2>&1
 zsh $EV/harness/model_check.sh org $LABEL $S | tail -3
 zsh $EV/harness/model_check.sh assistant $LABEL $S | tail -8
-# throttle marks / exit 75 among run logs
 echo "--- throttle/exit-75 scan after turn $T" >> $D/run-counts-by-turn.txt
 { [[ -d $S/org ]] && find $S/org -path '*/runs/*.log' -not -path '*/.git/*' -exec grep -lE '^# kiro: throttled by the model service|^# exit 75 ' {} + ; } >> $D/run-counts-by-turn.txt 2>/dev/null; echo "(end of scan)" >> $D/run-counts-by-turn.txt
-# ambient comparison (4.5.1): the md5 lines of this turn's before/after and the previous after (or setup)
 PREV=$D/ambient/setup.txt; [[ "$T" -ge 2 ]] && PREV=$D/ambient/turn-$(printf '%02d' $((T-1)))-after.txt
 echo "--- ambient comparison turn $T (md5 lines)"
 for f in $PREV $D/ambient/turn-$NN-before.txt $D/ambient/turn-$NN-after.txt; do echo "## $(basename $f)"; grep -E 'listing md5|memories\.db' $f; done
 tail -45 $D/run-counts-by-turn.txt
+# 2. the empty-argument call counter (18.3 item 3; f-g0-7 section 1): the session-store count decides, the stderr grep is reported beside it
+EC=$(grep -c 'is not available' $D/turn-$NN.stderr.txt 2>/dev/null); EC=${EC:-0}
+SC=$(python3 -B $EV/harness/empty_calls.py $D/assistant-session-messages.jsonl)
+echo "turn $NN: $SC so far (the session store); 'is not available' in turn-$NN.stderr.txt: $EC" >> $D/empty-calls.txt
+echo "empty-argument calls after turn $T: $SC; stderr grep this turn: $EC"
+# the org-run cap (protocol 4.2): every org run of the stream, the injection window included
+NRUNS=$( { [[ -d $S/org ]] && find $S/org -path '*/runs/*.log' -not -path '*/.git/*' 2>/dev/null; } | wc -l | tr -d ' ')
+echo "org runs after turn $T: $NRUNS (cap 130, the injection window included)"
+(( NRUNS >= 130 )) && echo "CAP: $NRUNS org runs after turn $T (cap 130, protocol 4.2): the stream ends at the end of this turn; it stays valid"
+# root's memo requests so far (M3-VERDICT's trigger: memo 4's request, 2026-10-26.md, exists in S/org/sent/; protocol 4.2)
+REQS=$(python3 - "$S/org/sent" <<'PY'
+import re,sys,glob,os
+out=[]
+for f in sorted(glob.glob(os.path.join(sys.argv[1],'*.md'))):
+    t=open(f,errors='replace').read(); m=re.match(r'^---\n(.*?)\n---\n?(.*)$',t,re.S)
+    if not m: continue
+    fm,body=m.groups()
+    if re.search(r'^type:\s*task\s*$',fm,re.M) and not re.search(r'^revises:\s*\S',fm,re.M):
+        n=re.search(r'notes_file:\s*(\d{4}-\d{2}-\d{2})',body)
+        if n: out.append(n.group(1))
+print(' '.join(dict.fromkeys(out)) or '(none)')
+PY
+)
+echo "turn $NN: root's new requests by notes file: $REQS; memo 4's request (2026-10-26.md) sent: $([[ $REQS == *2026-10-26* ]] && echo yes || echo no)" >> $D/requests-by-turn.txt
+tail -1 $D/requests-by-turn.txt
+# 3. arm F: the lock hook (once)
+if [[ "$ARM" == F ]]; then
+  L=$D/lock
+  if [[ ! -f $L/hook.txt ]]; then
+    SVC=("${(@f)$(find $S/org -path "$S/org/.git" -prune -o -path '*/services/*/SERVICE.md' -print 2>/dev/null | sort)}")
+    if [[ -n "${SVC[1]}" ]]; then
+      mkdir -p $L
+      if (( ${#SVC} != 1 )); then
+        echo "STOP: lock hook: ${#SVC} services exist after turn $T (${SVC[*]}): the study has one service; the hook does not guess" | tee $L/hook.txt
+      elif [[ -n "${ORG_AGENT+x}" || -n "${ORG_REQUIRE_AGENT+x}" ]]; then
+        echo "STOP: lock hook: ORG_AGENT or ORG_REQUIRE_AGENT is set in the facilitator's environment; the hook runs as root only" | tee $L/hook.txt
+      else
+        SF=${SVC[1]}; SDIR=${SF:h}; SERVICE=${SDIR:t}; LEAD=${${SDIR#$S/org/}%/services/*}
+        # H-LOCK first: an owner's playbook version (by the owner) written before the lock
+        python3 - "$SDIR" "$LEAD" > $L/h-lock-before.txt <<'PY'
+import os,re,sys,glob
+sdir,lead=sys.argv[1:3]
+files=sorted(glob.glob(os.path.join(sdir,'history','PLAYBOOK.v*.md')))+[os.path.join(sdir,'PLAYBOOK.md')]
+owner_versions=[]
+for f in files:
+    if not os.path.exists(f): continue
+    t=open(f,errors='replace').read()
+    m=re.match(r'^---\n(.*?)\n---',t,re.S)
+    fm=m.group(1) if m else ''
+    by=re.search(r'^by:\s*(.+)$',fm,re.M); op=re.search(r'^op:\s*(.+)$',fm,re.M); v=re.search(r'^version:\s*(\d+)',fm,re.M)
+    by=(by.group(1).strip().strip("'\"") if by else ''); op=(op.group(1).strip() if op else '')
+    print(f"{os.path.basename(f)} version {v.group(1) if v else '?'} by {by!r} op {op!r}")
+    if by==lead: owner_versions.append(os.path.basename(f))
+print('H-LOCK: INVALID: the owner wrote '+', '.join(owner_versions)+' before the lock' if owner_versions else 'H-LOCK: ok (no version by the owner before the lock)')
+PY
+        {
+          echo "lock hook after turn $T at $(date -u +%FT%TZ): lead=$LEAD service=$SERVICE SERVICE.md=$SF"
+          echo "SERVICE.md before: $(md5 -q $SF), $(grep -E '^(version|locked):' $SF | tr '\n' ' ')"
+          echo "command: ORG_ROOT=$S/org uv --directory $REPO run hirearchy define-service $LEAD $SERVICE --locked"
+        } > $L/hook.txt
+        VBEFORE=$(grep -E '^version:' $SF | head -1 | grep -oE '[0-9]+'); VWANT=$(( ${VBEFORE:-0} + 1 ))
+        list_cli() { [[ -d "$S/org/.runtime/events" ]] && find "$S/org/.runtime/events" -type f -name 'cli-*.jsonl' 2>/dev/null | sort; true; }
+        before="$(list_cli)"
+        startu=$(date -u +%FT%TZ)
+        ORG_ROOT=$S/org uv --directory $REPO run hirearchy define-service $LEAD $SERVICE --locked > $L/reply.txt 2> $L/stderr.txt; rc=$?
+        endu=$(date -u +%FT%TZ)
+        after="$(list_cli)"
+        new=("${(@f)$(comm -13 <(print -r -- "$before") <(print -r -- "$after"))}")
+        {
+          echo "start $startu end $endu exit $rc"
+          echo "reply (verbatim, reply.txt):"; cat $L/reply.txt
+          echo "new cli-*.jsonl during the call (known harness actor, H6): ${new[*]:-(none)}"
+          C1=no; [[ $rc -eq 0 ]] && grep -qi 'locked' $L/reply.txt && C1=yes
+          C2=no; grep -qE '^locked: true$' $SF && grep -qE "^version: $VWANT\$" $SF && C2=yes
+          NOTE=$(grep -rlF 'locked: false -> true (you may no longer revise the playbook)' $S/org/$LEAD/inbox $S/org/$LEAD/read 2>/dev/null | head -1)
+          C3=no; [[ -n "$NOTE" ]] && grep -qE '^from: root$' $NOTE && grep -qE '^wake: false$' $NOTE && C3=yes
+          echo "check 1, the reply (exit 0 and it names the lock): $C1"
+          echo "check 2, SERVICE.md frontmatter locked: true at version $VWANT (the version before the hook, $VBEFORE, + 1): $C2 ($(grep -E '^(version|locked):' $SF | tr '\n' ' '))"
+          echo "check 3, the owner's quiet note from root (wake: false) 'locked: false -> true (you may no longer revise the playbook)': $C3 (${NOTE:-none})"
+          cat $L/h-lock-before.txt
+          if [[ $C1 == yes && $C2 == yes && $C3 == yes ]] && grep -q '^H-LOCK: ok' $L/h-lock-before.txt; then
+            echo "LOCK OK after turn $T"
+          else
+            echo "STOP: LOCK FAILED after turn $T (check 1 $C1, check 2 $C2, check 3 $C3; $(tail -1 $L/h-lock-before.txt)): arm F is invalid (H-LOCK, protocol 8)"
+          fi
+        } >> $L/hook.txt
+        [[ -n "$NOTE" ]] && cp -p $NOTE $L/owner-note.md
+        cp -p $SF $L/SERVICE.after-lock.md
+        echo "$VWANT $SF" > $L/lock-version.txt
+        tail -6 $L/hook.txt
+      fi
+    else
+      echo "lock hook: no SERVICE.md yet after turn $T (arm F; the hook runs after the turn in which apply_org defines it)"
+    fi
+  else
+    echo "lock hook: done ($(grep -E '^(LOCK OK|STOP)' $L/hook.txt | head -1))"
+  fi
+  # the lock held (protocol 1.1, 8): every contract version after the lock keeps `locked: true`
+  if [[ -f $L/lock-version.txt ]]; then
+    read LV SF < $L/lock-version.txt
+    python3 - "$SF" "$LV" "$T" >> $L/lock-held.txt <<'PY'
+import os,re,sys,glob
+sf,lv,t=sys.argv[1],int(sys.argv[2]),sys.argv[3]
+files=sorted(glob.glob(os.path.join(os.path.dirname(sf),'history','SERVICE.v*.md')))+[sf]
+seen,bad={},[]
+for f in files:
+    if not os.path.exists(f): continue
+    m=re.match(r'^---\n(.*?)\n---',open(f,errors='replace').read(),re.S); fm=m.group(1) if m else ''
+    v=re.search(r'^version:\s*(\d+)',fm,re.M); lk=re.search(r'^locked:\s*(\S+)',fm,re.M)
+    if not v or int(v.group(1))<lv: continue
+    seen[int(v.group(1))]=lk.group(1) if lk else '(absent)'
+for v,lk in sorted(seen.items()):
+    if lk!='true': bad.append(f'v{v} locked: {lk}')
+print(f"after turn {t}: contract versions from the lock (v{lv}) on: "+', '.join(f'v{v} locked: {lk}' for v,lk in sorted(seen.items())))
+print(f"STOP: H-LOCK after turn {t}: {', '.join(bad)} after the lock: the arm was not held (protocol 8)" if bad else f"lock held after turn {t}")
+PY
+    tail -1 $L/lock-held.txt
+  fi
+fi
+# 4. the snapshots, last
 zsh $EV/harness/quality_snapshot.sh $LABEL turn-$NN
+zsh $EV/harness/services_snapshot.sh $LABEL turn-$NN
--- G0-noise-baseline/evidence/harness/copy_org_evidence.sh
+++ P1-itemized-playbook/evidence/harness/copy_org_evidence.sh
@@ -1,9 +1,10 @@
 #!/bin/zsh
-# G0: read-only copy of a stream's org into the evidence folder (protocol 7.2 "The org"), after the stream ended (E7's, plus memos/versions/).
+# P1 (G0's, plus every archived contract and playbook version): read-only copy of a stream's org into the evidence folder (protocol 14),
+# after the stream ended (E7's, plus memos/versions/).
 # Usage: copy_org_evidence.sh <S> <label>
 # Uses only file copies and the read-only CLI commands of protocol 4.8 (services | progress | status | health, obs trace).
 S="$1"; N="$2"
-EV=/Volumes/workspace/hirearchy/studies/G0-noise-baseline/evidence/$N
+EV=/Volumes/workspace/hirearchy/studies/P1-itemized-playbook/evidence/$N
 ORG="$S/org"
 HIR="uv --directory /Volumes/workspace/hirearchy run hirearchy"
 mkdir -p $EV/msgs $EV/run-logs $EV/events $EV/org-files $EV/service $EV/playbook
@@ -32,6 +33,12 @@
 # every committed version of SERVICE.md / PLAYBOOK.md
 git -C $ORG log --reverse --format='%h %cI' -- '*SERVICE.md' | while read h t; do f=$(git -C $ORG ls-files -- '*SERVICE.md' | head -1); git -C $ORG show $h:$f > $EV/service/SERVICE.$h.md 2>/dev/null; echo "$h $t" >> $EV/service/versions.txt; done
 git -C $ORG log --reverse --format='%h %cI' -- '*PLAYBOOK.md' | while read h t; do f=$(git -C $ORG ls-files -- '*PLAYBOOK.md' | head -1); git -C $ORG show $h:$f > $EV/playbook/PLAYBOOK.$h.md 2>/dev/null; echo "$h $t" >> $EV/playbook/versions.txt; done
+# P1: every archived version of the study service's contract and playbook (the product's history/, design 4.3), byte for byte, so that
+# rederive_watch.py reads every version even when one run wrote two (git holds only the committed ones)
+find $ORG -path "$ORG/.git" -prune -o -path '*/services/*/history/SERVICE.v*.md' -print | while read f; do cp -p $f $EV/service/history--${f:t}; done
+find $ORG -path "$ORG/.git" -prune -o -path '*/services/*/history/PLAYBOOK.v*.md' -print | while read f; do cp -p $f $EV/playbook/history--${f:t}; done
+find $ORG -path "$ORG/.git" -prune -o -path '*/services/*/SERVICE.md' -print | head -1 | while read f; do cp -p $f $EV/service/current-SERVICE.md; done
+find $ORG -path "$ORG/.git" -prune -o -path '*/services/*/PLAYBOOK.md' -print | head -1 | while read f; do cp -p $f $EV/playbook/current-PLAYBOOK.md; done
 # deliverables
 [[ -d $S/deliverables ]] && { mkdir -p $EV/memos; cp -p $S/deliverables/* $EV/memos/ 2>/dev/null; }
 # memos/versions/ is NOT written here: extract_mechanical.py writes it (E7's rule: every .md under the owner's */work/ folders except the
--- G0-noise-baseline/evidence/harness/extract_mechanical.py
+++ P1-itemized-playbook/evidence/harness/extract_mechanical.py
@@ -11,7 +11,8 @@
   * the sandbox-name patterns: from the stream's own `sandbox-path.txt` (and the generic `/tmp/hirearchy-<...>-<epoch>/org/` form).
 
 Usage:
-    python3 -B extract_mechanical.py <streamdir> <sandbox S or "-"> [--out DIR] [--product-src DIR]
+    python3 -B extract_mechanical.py <streamdir> <sandbox S or "-"> [--out DIR] [--product-src DIR] [--p1]
+  --p1         (P1, protocol 12) then also run rederive_watch.py (<out>/watch/) and guarantees.py (<out>/guarantees/: G1 and G2)
   <streamdir>  the stream's evidence dir (E7's layout: `s1/`, or G0's `m0-s1/`); never written unless it is also --out.
   S            the sandbox path (E7's second input) or "-": with "-" (or when S is gone) every input comes from the stream dir only:
                the org git history from `memos/versions/INDEX.txt`, `playbook/versions.txt` and `org-git-log.txt`; the org-run sessions from
@@ -142,7 +143,7 @@
         flags.append("writes into the deliverable folder")
     if ORG in cmd or ORG.replace("/tmp/", "/private/tmp/", 1) in cmd or re.search(r"\borg/", cmd):
         flags.append("touches S/org")
-    if re.search(r"\bhirearchy\b(?!-(?:e7|g0)\b)", cmd.replace(S, "").replace("/Volumes/workspace/hirearchy", "")):
+    if re.search(r"\bhirearchy\b(?!-(?:e7|g0|p1)\b)", cmd.replace(S, "").replace("/Volumes/workspace/hirearchy", "")):
         flags.append("mentions hirearchy")
     if re.search(r"(^|[;&|]\s*)(uv run )?hirearchy\s", cmd):
         flags.append("runs hirearchy CLI")
@@ -630,6 +631,9 @@
 def main(argv):
     args = list(argv)
     out = product_src = None
+    p1 = "--p1" in args  # P1 protocol 12: also the watch re-derivation and the G1/G2 procedures (rederive_watch.py, guarantees.py)
+    if p1:
+        args.remove("--p1")
     for flag in ("--out", "--product-src"):
         if flag in args:
             i = args.index(flag)
@@ -649,6 +653,13 @@
     res = run_extract(D, S, Path(out) if out else D, product_src or PRODUCT_SRC)
     print(f"runs {res['runs']}, sessions {res['sessions']}, matched {res['matched']}, unmatched runs {res['unmatched']}, "
           f"revise_playbook events {res['revise_playbook']}, flags {res['flags']}, calls {res['calls']}")
+    if p1:
+        sys.path.insert(0, str(Path(__file__).resolve().parent))
+        import guarantees
+        import rederive_watch
+        base = Path(out) if out else D
+        rederive_watch.run_stream(D, base / "watch")
+        guarantees.main([str(D), "--out", str(base / "guarantees"), "--watch", str(base / "watch")])
     return 0
 
 
--- G0-noise-baseline/evidence/harness/finish_stream.sh
+++ P1-itemized-playbook/evidence/harness/finish_stream.sh
@@ -1,38 +1,40 @@
 #!/bin/zsh
-# G0 stream finish (protocol 6 item 5 for G0; design 20.3). Usage: finish_stream.sh <label>      (after the last turn)
+# P1 stream finish (G0's finish_stream.sh, M1 treatment only; protocol 7). Usage: finish_stream.sh <label>      (after the last turn)
 # In this order, never stopping on one failure (every step's exit code is recorded in $EV/<label>/finish-steps.txt; failures are also listed
 # in finish-failures.txt; the exit code of this script is 1 if any step failed, else 0):
 #   1.  the injection script's --stop, only if a scheduler still runs (scheduler.pid + ps) -> scheduler-stop.txt
 #   2.  copy_org_evidence.sh <S> <label> (+ the sandbox's injection/ folder copied into the stream dir: injection_files.py reads it there)
 #   3.  `hirearchy --root S/org check` -> observe-check.txt with its exit code
-#   4.  quality_snapshot.sh <label> end
+#   4.  quality_snapshot.sh <label> end and services_snapshot.sh <label> end
 #   5.  the extracts and measures, each into its file: extract_tool_calls.py (assistant-tool-calls.txt, session-turn-times-utc.txt),
 #       extract_proposals.py, extract_mechanical.py <dir> <S>, scheduler_survival.py, injection_files.py, assistant_facts.py, score_memos.py,
 #       ambiguity_recall.py, prompt_sizes.py, playbook_attempts.py (outputs into measures/), rederive_quality.py --compare quality/end.json
-#       (outputs into rederived/). Each script's CLI is in its own docstring (protocol section 11 lists them).
+#       (outputs into rederived/); score_memos.py runs with --memos 6 (and --owner-forms owner-forms.json when the stream step wrote it);
+#       extract_mechanical.py runs with --p1 (rederive_watch.py into watch/, guarantees.py into guarantees/: G1, G2, the orders).
+#       Each script's CLI is in its own docstring (protocol section 10 lists them).
 #   6.  model_check.sh all <label> <S>
-#   7.  the profile cleanup: the profile is copied into profiles/, compared (cmp) and deleted from its kiro home (arm m1 ~/.kiro/agents;
-#       arm m0 <M0H>/.kiro/agents); name, md5 and UTC go to profiles/deletions.txt. Nothing else in any kiro home is touched.
-#   8.  safety-after.txt (+ safety-diff.txt), ambient/end.txt, and the 4.1 checks again appended to setup.txt ("AFTER the last turn").
-# The M0 home (/tmp/hirearchy-g0-m0home-*) is NOT deleted here: the teardown step does it. The sandbox is left in place, read-only.
+#   7.  the profile cleanup: the profile is copied into profiles/, compared (cmp) and deleted from ~/.kiro/agents (both arms); name, md5 and
+#       UTC go to profiles/deletions.txt. Nothing else in any kiro home is touched.
+#   8.  safety-after.txt (+ safety-diff.txt), ambient/end.txt, the owner's memories.db md5 after the stream (memories-md5-after.txt; a change
+#       against memories-md5-before.txt is written to memories-db.txt and printed as `STOP:`), the empty-argument call total (empty-calls.txt:
+#       the session-store count, the greps beside it), the stream's credits (credits.txt, cost_total.py: protocol 11), arm F's H-LOCK
+#       re-check over the copied evidence (lock/h-lock-after.txt: no owner version before the lock, every contract version from the lock on
+#       `locked: true`), and the freeze checks again appended to setup.txt.
+# The sandbox is left in place, read-only, until the teardown.
 LABEL="$1"
 REPO=/Volumes/workspace/hirearchy
-ST=$REPO/studies/G0-noise-baseline
+ST=$REPO/studies/P1-itemized-playbook
 EV=$ST/evidence
 H=$EV/harness
-SHA_REF=3c841bb9
-[[ "$LABEL" =~ '^(m0|m1)-s[1-9][0-9]*(r[0-9]*)?$' && $# -eq 1 ]] || { echo "usage: finish_stream.sh <label>" >&2; exit 2; }
+SHA_REF=8bf7c69b
+[[ "$LABEL" =~ '^[FI][1-3](r[0-9]*)?$' && $# -eq 1 ]] || { echo "usage: finish_stream.sh <label>" >&2; exit 2; }
 D=$EV/$LABEL
 [[ -f $D/sandbox-path.txt ]] || { echo "finish_stream.sh: $D/sandbox-path.txt is missing" >&2; exit 2; }
 S=$(cat $D/sandbox-path.txt)
-ARM=${LABEL%%-*}
-PNAME=hirearchy-study-g0-$LABEL-assistant
+ARM=${LABEL[1,1]}
+PNAME=hirearchy-study-p1-$LABEL-assistant
 KH_ARG=""; PDIR=$HOME/.kiro/agents
-if [[ $ARM == m0 ]]; then
-  M0H=$(cat $D/m0-home-path.txt 2>/dev/null)
-  [[ -n "$M0H" ]] && { KH_ARG=$M0H/.kiro; PDIR=$M0H/.kiro/agents; }
-fi
-mkdir -p $D/measures $D/rederived $D/profiles $D/quality $D/ambient
+mkdir -p $D/measures $D/rederived $D/profiles $D/quality $D/services $D/ambient
 STEPS=$D/finish-steps.txt; FAILS=$D/finish-failures.txt
 echo "# finish_stream.sh $LABEL started $(date -u +%FT%TZ)" >> $STEPS
 nfail=0
@@ -71,16 +73,18 @@
 
 # 4. quality at the end
 step "quality_snapshot end" $D/quality/end-snapshot-output.txt zsh $H/quality_snapshot.sh $LABEL end
+step "services_snapshot end" $D/services/end-snapshot-output.txt zsh $H/services_snapshot.sh $LABEL end
 
 # 5. extracts and measures
 step extract_tool_calls $D/extract_tool_calls-output.txt python3 -B $H/extract_tool_calls.py $D/assistant-session-messages.jsonl $D/assistant-tool-calls.txt $D/session-turn-times-utc.txt
 step extract_proposals $D/measures/extract_proposals-output.txt python3 -B $H/extract_proposals.py $D
-step extract_mechanical $D/extract_mechanical-output.txt python3 -B $H/extract_mechanical.py $D $S
+step extract_mechanical $D/extract_mechanical-output.txt python3 -B $H/extract_mechanical.py $D $S --p1
 step scheduler_survival $D/measures/scheduler_survival-output.txt python3 -B $H/scheduler_survival.py $D
 step "scheduler_survival (measures/)" $D/measures/scheduler_survival-measures-output.txt python3 -B $H/scheduler_survival.py $D --out $D/measures
 step injection_files $D/measures/injection_files-output.txt python3 -B $H/injection_files.py $D $S
 step assistant_facts $D/measures/assistant_facts-output.txt python3 -B $H/assistant_facts.py $D --out $D/measures
-step score_memos $D/measures/score_memos-output.txt python3 -B $H/score_memos.py $D --out $D/measures
+OF=(); [[ -f $D/owner-forms.json ]] && OF=(--owner-forms $D/owner-forms.json)
+step score_memos $D/measures/score_memos-output.txt python3 -B $H/score_memos.py $D --out $D/measures --memos 6 $OF
 step ambiguity_recall $D/measures/ambiguity_recall-output.txt python3 -B $H/ambiguity_recall.py $D --out $D/measures
 step prompt_sizes $D/measures/prompt_sizes-output.txt python3 -B $H/prompt_sizes.py $D --out $D/measures
 step playbook_attempts $D/measures/playbook_attempts-output.txt python3 -B $H/playbook_attempts.py $D --out $D/measures
@@ -120,8 +124,64 @@
 # 8. safety, ambient, the 4.1 checks again
 zsh $H/safety-snapshot.sh "$LABEL after" > $D/safety-after.txt 2>&1
 diff <(grep -v '^date' $D/safety-before.txt) <(grep -v '^date' $D/safety-after.txt) > $D/safety-diff.txt 2>&1
-zsh $H/ambient_snapshot.sh "$LABEL end" $KH_ARG > $D/ambient/end.txt 2>&1
+zsh $H/ambient_snapshot.sh "$LABEL end" > $D/ambient/end.txt 2>&1
+# the owner's memories.db after this stream (design 18.2): md5 only
+MDB=$HOME/.kiro/memories/memories.db
+{ [[ -f $MDB ]] && md5 -q $MDB || echo absent; } > $D/memories-md5-after.txt
+if [[ "$(cat $D/memories-md5-after.txt)" != "$(cat $D/memories-md5-before.txt 2>/dev/null)" ]]; then
+  echo "memories.db CHANGED during $LABEL: $(cat $D/memories-md5-before.txt 2>/dev/null) -> $(cat $D/memories-md5-after.txt)" >> $D/memories-db.txt
+  echo "STOP: memories.db changed during $LABEL: send a warning before the next stream and wait (the stream stays valid; never restore or edit the store)"
+else
+  echo "memories.db unchanged during $LABEL: $(cat $D/memories-md5-after.txt)" >> $D/memories-db.txt
+fi
+# the empty-argument calls (18.3 item 3; f-g0-7 section 1): the session-store count decides (empty_calls.py), the greps are reported beside it
 {
+  echo "total: $(python3 -B $H/empty_calls.py $D/assistant-session-messages.jsonl) (decides the validity label, protocol 8)"
+  echo "total 'is not available' in turn-*.stderr.txt: $(cat $D/turn-*.stderr.txt(N) 2>/dev/null | grep -c 'is not available') (reported)"
+  echo "total 'is not available' in assistant-tool-calls.txt: $(grep -c 'is not available' $D/assistant-tool-calls.txt 2>/dev/null || echo 0) (reported)"
+} >> $D/empty-calls.txt
+# the stream's credits (protocol 11): assistant + every org run, the injection window included, one line read by next_stream.sh and the gate
+python3 -B $H/cost_total.py $D/cost.txt > $D/credits.txt; echo "credits: $(cat $D/credits.txt)"
+# arm F: H-LOCK again (no owner version after the lock either: PB-LOCKED refuses every owner op; one would be a product defect)
+if [[ $ARM == F ]]; then
+  python3 - "$D" > $D/lock/h-lock-after.txt 2>&1 <<'PY'
+import sys,re,glob,os
+D=sys.argv[1]
+fm=lambda t:(re.match(r'^---\n(.*?)\n---',t,re.S) or [None,''])[1]
+# the lead (the service's owner) as the lock hook recorded it (lock/hook.txt `lead=...`), never guessed from the mail
+hook=os.path.join(D,'lock','hook.txt')
+m=re.search(r'\blead=(\S+)',open(hook,errors='replace').read()) if os.path.exists(hook) else None
+lead=m.group(1) if m else None
+print('lead (lock/hook.txt):',lead or 'MISSING')
+lock=None
+for f in glob.glob(os.path.join(D,'service','*.md')):
+    t=fm(open(f,errors='replace').read())
+    if re.search(r'^locked:\s*true$',t,re.M):
+        d=re.search(r"^defined:\s*'?([^'\n]+)",t,re.M); v=re.search(r'^version:\s*(\d+)',t,re.M)
+        if d and (lock is None or d.group(1)<lock[0]): lock=(d.group(1),v.group(1) if v else '?')
+print('lock version:',lock)
+bad=[]
+for f in sorted(glob.glob(os.path.join(D,'playbook','*.md'))):
+    t=fm(open(f,errors='replace').read())
+    by=re.search(r'^by:\s*(.+)$',t,re.M); rv=re.search(r"^revised:\s*'?([^'\n]+)",t,re.M); op=re.search(r'^op:\s*(\S+)',t,re.M)
+    if by and lead and by.group(1).strip().strip("'\"")==lead:
+        bad.append(f"{os.path.basename(f)} op {op.group(1) if op else '?'} revised {rv.group(1) if rv else '?'}")
+print('owner versions:', bad or 'none')
+held=[]
+for f in sorted(glob.glob(os.path.join(D,'service','*.md'))):
+    t=fm(open(f,errors='replace').read()); v=re.search(r'^version:\s*(\d+)',t,re.M); lk=re.search(r'^locked:\s*(\S+)',t,re.M)
+    if lock and v and lock[1]!='?' and int(v.group(1))>=int(lock[1]): held.append((int(v.group(1)),lk.group(1) if lk else '(absent)'))
+held=sorted(set(held)); unheld=[f'v{v} locked: {lk}' for v,lk in held if lk!='true']
+print('contract versions from the lock on:', ', '.join(f'v{v} locked: {lk}' for v,lk in held) or 'none')
+before=bool(bad and lock and any(b.split('revised ')[-1] < lock[0] for b in bad))
+if before or unheld or not lock or not lead:
+    print('H-LOCK: INVALID: '+('; '.join((['an owner version before the lock'] if before else [])+([', '.join(unheld)+' after the lock (the arm was not held)'] if unheld else [])+(['no locked contract version'] if not lock else [])+(['no lock hook record (lock/hook.txt)'] if not lead else []))))
+else:
+    print('H-LOCK: ok' if not bad else 'H-LOCK: ok before the lock; owner versions after it: a product defect to record')
+PY
+  echo "H-LOCK after the stream: $(tail -1 $D/lock/h-lock-after.txt)"
+fi
+{
   echo
   echo "== AFTER the last turn ($(date -u +%FT%TZ)) (protocol 4.1, 6 item 5)"
   echo "git rev-parse HEAD: $(git -C $REPO rev-parse HEAD)"
@@ -133,7 +193,6 @@
   echo "global SKILL.md md5: $(md5 -q $HOME/.kiro/skills/hirearchy/SKILL.md 2>/dev/null || echo absent)"
   echo "processes referencing the sandbox: $(ps -axo command | grep -F "${S:t}" | grep -v grep | wc -l | tr -d ' ')"
   echo "~/.kiro/agents: $(ls $HOME/.kiro/agents | tr '\n' ' ')"
-  [[ $ARM == m0 && -n "$M0H" ]] && echo "$M0H/.kiro/agents: $(ls $M0H/.kiro/agents 2>&1 | tr '\n' ' ') (the M0 home is left for the teardown)"
 } >> $D/setup.txt 2>&1
 echo "# finish_stream.sh $LABEL ended $(date -u +%FT%TZ); failed steps: $nfail" >> $STEPS
 echo "finished $LABEL: $nfail failed step(s); see $STEPS$( (( nfail > 0 )) && echo " and $FAILS")"
--- G0-noise-baseline/evidence/harness/model_check.sh
+++ P1-itemized-playbook/evidence/harness/model_check.sh
@@ -1,5 +1,5 @@
 #!/bin/zsh
-# G0 model and effort check (E7's; protocol 4.3, 11 H4). Read-only: it lists, reads and greps; it writes only model-checks.txt.
+# P1 model and effort check (G0's = E7's; protocol 6, 8 H4). Read-only: it lists, reads and greps; it writes only model-checks.txt.
 # The set is one seat value: claude-sonnet-5.5 at effort high, for the assistant and for every org agent (D-E4-8, D-E4-9).
 # Usage:
 #   model_check.sh listed    <label>       "kiro-cli chat --list-models" lists claude-sonnet-5.5 (stream start; there is no substitution)
@@ -10,16 +10,16 @@
 #                                      <label>/assistant-session.json has modelId claude-sonnet-5.5 and effortLevel high (or none recorded);
 #                                      every reasoningModelId in <label>/assistant-session-messages.jsonl is [qdev::]claude-sonnet-5.5
 #   model_check.sh all       <label> <S>   org, then assistant
-# <label> is the G0 stream label (m0-s1, m1-s2, m0-s1r, ...), or "preflight" for a scratch org (output in evidence/preflight/). Appends a block
-# to evidence/<label>/model-checks.txt and prints its RESULT line. The assistant's profile is looked for in ~/.kiro/agents, in the arm M0's
-# dedicated home (<label>/m0-home-path.txt) and in <label>/profiles/.
+# <label> is the P1 stream label (F1 ... I3, F1r ...), "probe-<arm>-<rep>" or "preflight" for a scratch org (output in evidence/preflight/).
+# Appends a block to evidence/<label>/model-checks.txt and prints its RESULT line. The assistant's profile is looked for in ~/.kiro/agents
+# and in <label>/profiles/.
 # Exit 0: every seat checked is in the set (or, for listed, the model is listed). Exit 1: a seat outside the set (stream-invalidating,
 # H4), or claude-sonnet-5.5 not listed (the stream does not start). Exit 2: usage error, or nothing to check yet (never a pass).
 MODE="$1"; N="$2"; S="$3"
 [[ -n "$MODE" && -n "$N" ]] || { echo "usage: model_check.sh listed|org|assistant|all <label> [<S>]" >&2; exit 2; }
 [[ "$MODE" == listed || -n "$S" ]] || { echo "usage: model_check.sh $MODE <label> <S>" >&2; exit 2; }
-EV=/Volumes/workspace/hirearchy/studies/G0-noise-baseline/evidence/$N
-[[ "$N" == preflight ]] && EV=/Volumes/workspace/hirearchy/studies/G0-noise-baseline/evidence/preflight
+EV=/Volumes/workspace/hirearchy/studies/P1-itemized-playbook/evidence/$N
+[[ "$N" == preflight ]] && EV=/Volumes/workspace/hirearchy/studies/P1-itemized-playbook/evidence/preflight
 mkdir -p "$EV"
 OUT="$EV/model-checks.txt"
 LISTING=""
@@ -81,11 +81,8 @@
 
 
 def assistant():
-    name = f"hirearchy-study-g0-{n}-assistant"
+    name = f"hirearchy-study-p1-{n}-assistant"
     cands = [os.path.expanduser(f"~/.kiro/agents/{name}.json")]
-    m0p = os.path.join(ev, "m0-home-path.txt")
-    if os.path.isfile(m0p):  # arm M0: the profile lives in the dedicated home
-        cands.append(os.path.join(open(m0p).read().strip(), ".kiro", "agents", f"{name}.json"))
     cands.append(os.path.join(ev, "profiles", f"{name}.json"))
     prof = [p for p in cands if os.path.isfile(p)]
     if prof:
@@ -94,7 +91,7 @@
         if m != MODEL:
             bad.append(f"assistant profile model {m!r}")
     else:
-        nothing.append(f"profile {name}.json not found in ~/.kiro/agents, the M0 home or {n}/profiles")
+        nothing.append(f"profile {name}.json not found in ~/.kiro/agents or {n}/profiles")
     cmds = sorted(glob.glob(os.path.join(ev, "turn-*.cmd.txt")))
     if not cmds:
         nothing.append("no turn-NN.cmd.txt yet")
--- G0-noise-baseline/evidence/harness/profile-template.json
+++ P1-itemized-playbook/evidence/harness/profile-template.json
@@ -1,11 +1,11 @@
 {
-  "name": "hirearchy-study-g0-<LABEL>-assistant",
-  "description": "internal: hirearchy usability study G0 stream <LABEL> assistant; deleted after the stream",
+  "name": "hirearchy-study-p1-<LABEL>-assistant",
+  "description": "internal: hirearchy usability study P1 stream <LABEL> assistant; deleted after the stream",
   "mcpServers": {
     "hirearchy": {
       "command": "uv",
       "args": ["--directory", "/Volumes/workspace/hirearchy", "run", "hirearchy", "mcp"],
-      "env": { "ORG_ROOT": "/tmp/hirearchy-g0-<LABEL>-<epoch>/org" }
+      "env": { "ORG_ROOT": "/tmp/hirearchy-p1-<LABEL>-<epoch>/org" }
     }
   },
   "tools": ["*"],
--- G0-noise-baseline/evidence/harness/quality_snapshot.sh
+++ P1-itemized-playbook/evidence/harness/quality_snapshot.sh
@@ -1,17 +1,19 @@
 #!/bin/zsh
-# G0 quality snapshot (design 20.3: `hirearchy quality --json` after each turn and at the end). Usage: quality_snapshot.sh <label> <tag>
+# P1 quality snapshot (G0's; protocol 10: `hirearchy quality --json` after each turn and at the end). Usage: quality_snapshot.sh <label> <tag>
 #   <tag>  turn-NN (after_turn.sh) or end (finish_stream.sh)
 # If <S>/org/ORG.md does not exist: appends "<tag> <utc>: no org yet, quality not run" to $EV/<label>/quality/calls.txt and exits 0. The CLI's
 # `cli.command` recorder would create <S>/org/.runtime/ and break the assistant's create_org, so the CLI is not run before the org exists.
 # Otherwise: runs `uv --directory $REPO run hirearchy --root <S>/org quality --json` into $EV/<label>/quality/<tag>.json (stderr:
-# <tag>.stderr.txt) and appends to calls.txt the tag, the UTC start and end, the exit code, and the name and `command` field of every
+# <tag>.stderr.txt) and appends to calls.txt the tag, the UTC start and end (ISO with microseconds: the re-derivation compares the product with
+# every record time inside the call, protocol 12.1 G1(f)), the exit code, the output's size in bytes and whether it is valid JSON (the
+# unread rule of protocol 12.1), and the name and `command` field of every
 # <S>/org/.runtime/events/**/cli-*.jsonl that appeared during the call (the listing before and after). Read-only otherwise: the product's
 # CLI records its own cli.command event, and that is all it writes.
 LABEL="$1"; TAG="$2"
 REPO=/Volumes/workspace/hirearchy
-ST=$REPO/studies/G0-noise-baseline
+ST=$REPO/studies/P1-itemized-playbook
 EV=$ST/evidence
-[[ "$LABEL" =~ '^(m0|m1)-s[1-9][0-9]*(r[0-9]*)?$' && "$TAG" =~ '^(turn-[0-9][0-9]+|end)$' && $# -eq 2 ]] || { echo "usage: quality_snapshot.sh <label> turn-NN|end" >&2; exit 2; }
+[[ "$LABEL" =~ '^[FI][1-3](r[0-9]*)?$' && "$TAG" =~ '^(turn-[0-9][0-9]+|end)$' && $# -eq 2 ]] || { echo "usage: quality_snapshot.sh <label> turn-NN|end" >&2; exit 2; }
 D=$EV/$LABEL
 [[ -f $D/sandbox-path.txt ]] || { echo "quality_snapshot.sh: $D/sandbox-path.txt is missing" >&2; exit 2; }
 S=$(cat $D/sandbox-path.txt)
@@ -24,13 +26,16 @@
 fi
 list_cli() { [[ -d "$S/org/.runtime/events" ]] && find "$S/org/.runtime/events" -type f -name 'cli-*.jsonl' 2>/dev/null | sort; true; }
 before="$(list_cli)"
-startu=$(date -u +%FT%TZ)
+startu=$(python3 -c 'import datetime;print(datetime.datetime.now(datetime.timezone.utc).isoformat())')
 uv --directory "$REPO" run hirearchy --root "$S/org" quality --json > "$Q/$TAG.json" 2> "$Q/$TAG.stderr.txt"; rc=$?
-endu=$(date -u +%FT%TZ)
+endu=$(python3 -c 'import datetime;print(datetime.datetime.now(datetime.timezone.utc).isoformat())')
 after="$(list_cli)"
 new=("${(@f)$(comm -13 <(print -r -- "$before") <(print -r -- "$after"))}")
+# protocol 12.1's unread rule (exit not 0, an empty output, or invalid JSON): recorded on the line, and noted (never a STOP: the scoring decides)
+bytes=$(wc -c < "$Q/$TAG.json" | tr -d ' ')
+jsonok=$(python3 -c 'import json,sys; json.load(open(sys.argv[1]))' "$Q/$TAG.json" > /dev/null 2>&1 && echo ok || echo invalid)
 {
-  echo "$TAG start $startu end $endu exit $rc"
+  echo "$TAG start $startu end $endu exit $rc bytes $bytes json $jsonok"
   if [[ -z "${new[1]}" ]]; then
     echo "  new cli-*.jsonl during the call: (none)"
   else
@@ -40,4 +45,5 @@
   fi
 } >> "$Q/calls.txt"
 echo "quality $TAG: exit $rc ($Q/$TAG.json)"
+[[ $rc -ne 0 || $bytes -eq 0 || $jsonok != ok ]] && echo "NOTE: quality $TAG is unread (exit $rc, $bytes bytes, JSON $jsonok; protocol 12.1): see $Q/$TAG.stderr.txt"
 exit 0
--- G0-noise-baseline/evidence/harness/run_turn.sh
+++ P1-itemized-playbook/evidence/harness/run_turn.sh
@@ -1,36 +1,24 @@
 #!/bin/zsh
-# G0 per-turn driver (E7's). Usage: run_turn.sh <S> <label> <turn number> <prompt file>      (label = m0-s1, m1-s2, m0-s1r, ...)
-# Sends the prompt file's text verbatim as Lena's line. Turn 1 = new session; turns >= 2 add --resume. cwd = S.
-# Every call carries --effort high (protocol 4.2, 4.3). The exact argv is written to turn-NN.cmd.txt (model_check.sh reads it).
-# Writes into <evidence>/<label>/: turn-NN.prompt.txt (copy), turn-NN.cmd.txt (argv), turn-NN.txt (header + prompt + stdout, ANSI
-# stripped), turn-NN.raw.txt (raw stdout), turn-NN.stderr.txt, and appends a line to turn-times.txt. No MCP/CLI call against the org.
-# E7 (protocol 4.2.1, E7 item 4, D-E6-7; C1's D-HARN form): the kiro-cli chat command is never the last command of its tool call: the
-# exit code and the end times are taken, then `; sleep 20` follows in the same command list, so the call stays open 20 s after the return.
-# E7 (protocol 4.5.1): ambient_snapshot.sh is taken right before the chat (ambient/turn-NN-before.txt) and after the sleep
-# (ambient/turn-NN-after.txt). turn-times.txt keeps E6's format and appends the time the sleep ended.
-# G0 (design 20.1, arms): the chat runs under the arm's kiro home. Arm M1 (the owner's ambient memories): `env -u KIRO_HOME`, so an inherited
-# KIRO_HOME cannot redirect it, and kiro uses the owner's default home. Arm M0 (no memories index): `env KIRO_HOME=<M0H>/.kiro`, <M0H> read from
-# <evidence>/<label>/m0-home-path.txt (the run is refused if that file is missing); HOME is unchanged and authentication comes from the
-# inherited environment. The env prefix is the first part of the CMD array, so turn-NN.cmd.txt shows it. For arm M0 the ambient snapshots
-# also list the dedicated home's skills and memories (ambient_snapshot.sh's second argument).
-# The variable EV below is the STREAM's evidence folder, as in E7 (EVROOT is the study's evidence root).
+# P1 per-turn driver (G0's run_turn.sh, M1 treatment only; E7's chat line and boundary). Usage: run_turn.sh <S> <label> <turn number> <prompt file>
+#   label = F1 F2 F3 I1 I2 I3 (a replacement: F1r ...). Arm = the label's first letter (F frozen-playbook control, I itemized).
+# Sends the prompt file's text verbatim as Lena's line. Turn 1 = new session; turns >= 2 add --resume. cwd = S. Every call carries --effort high.
+# The exact argv is written to turn-NN.cmd.txt (model_check.sh reads it). Writes into <evidence>/<label>/: turn-NN.prompt.txt (copy),
+# turn-NN.cmd.txt (argv), turn-NN.txt (header + prompt + stdout, ANSI stripped), turn-NN.raw.txt (raw stdout), turn-NN.stderr.txt, and a line
+# in turn-times.txt. No MCP/CLI call against the org.
+# Boundary (E7 4.2.1; D-E6-7; C1's D-HARN form): the kiro-cli chat command is never the last command of its tool call: the exit code and the end
+# times are taken, then `; sleep 20` follows in the same command list. Ambient snapshots right before the chat and after the sleep (E7 4.5.1).
+# Kiro home (design 18.2, 18.3 item 1; F-G0-7 section 4 item 1): BOTH arms run `env -u KIRO_HOME`, so kiro uses the owner's default home and an
+# inherited KIRO_HOME can never redirect it. No dedicated kiro home exists in P1. The env prefix is the first part of the CMD array, so
+# turn-NN.cmd.txt shows it in every turn of both arms.
 S="$1"; LABEL="$2"; T="$3"; PF="$4"
 REPO=/Volumes/workspace/hirearchy
-ST=$REPO/studies/G0-noise-baseline
+ST=$REPO/studies/P1-itemized-playbook
 EVROOT=$ST/evidence
 H=$EVROOT/harness
 EV=$EVROOT/$LABEL
-[[ "$LABEL" =~ '^(m0|m1)-s[1-9][0-9]*(r[0-9]*)?$' && -n "$S" && "$T" =~ '^[1-9][0-9]*$' && -f "$PF" ]] || { echo "usage: run_turn.sh <S> <label> <turn> <prompt file>" >&2; exit 2; }
-ARM=${LABEL%%-*}
+[[ "$LABEL" =~ '^[FI][1-3](r[0-9]*)?$' && -n "$S" && "$T" =~ '^[1-9][0-9]*$' && -f "$PF" ]] || { echo "usage: run_turn.sh <S> <label F1..I3> <turn> <prompt file>" >&2; exit 2; }
+[[ "$T" -le 30 ]] || { echo "REFUSED: turn $T is beyond the cap of 30 user turns (protocol 4.2)" >&2; exit 92; }
 KIRO_ENV=(env -u KIRO_HOME)
-KH=""
-if [[ "$ARM" == m0 ]]; then
-  [[ -s "$EV/m0-home-path.txt" ]] || { echo "REFUSED: $EV/m0-home-path.txt is missing: arm m0 needs its dedicated kiro home (prepare_m0_home.sh)" >&2; exit 91; }
-  M0H="$(cat "$EV/m0-home-path.txt")"
-  [[ -d "$M0H/.kiro" ]] || { echo "REFUSED: $M0H/.kiro does not exist" >&2; exit 91; }
-  KH="$M0H/.kiro"
-  KIRO_ENV=(env KIRO_HOME="$KH")
-fi
 NN=$(printf '%02d' "$T")
 mkdir -p "$EV"
 cp "$PF" "$EV/turn-$NN.prompt.txt"
@@ -38,14 +26,14 @@
 RESUME=""
 [[ "$T" -ge 2 ]] && RESUME="--resume"
 cd "$S" || exit 90
-CMD=(${KIRO_ENV[@]} kiro-cli chat --v3 --no-interactive --trust-all-tools $RESUME --effort high --agent hirearchy-study-g0-$LABEL-assistant "$PROMPT")
+CMD=(${KIRO_ENV[@]} kiro-cli chat --v3 --no-interactive --trust-all-tools $RESUME --effort high --agent hirearchy-study-p1-$LABEL-assistant "$PROMPT")
 print -r -- "${(q-)CMD[@]}" > "$EV/turn-$NN.cmd.txt"
 mkdir -p "$EV/ambient"
-zsh "$H/ambient_snapshot.sh" "$LABEL before turn $T" $KH > "$EV/ambient/turn-$NN-before.txt" 2>&1
+zsh "$H/ambient_snapshot.sh" "$LABEL before turn $T" > "$EV/ambient/turn-$NN-before.txt" 2>&1
 start=$(date +%s); startl=$(date +%H:%M:%S); startu=$(date -u +%FT%TZ)
 "${CMD[@]}" > "$EV/turn-$NN.raw.txt" 2> "$EV/turn-$NN.stderr.txt"; rc=$?; end=$(date +%s); endl=$(date +%H:%M:%S); endu=$(date -u +%FT%TZ); sleep 20
 slept=$(date -u +%FT%TZ)
-zsh "$H/ambient_snapshot.sh" "$LABEL after turn $T" $KH > "$EV/ambient/turn-$NN-after.txt" 2>&1
+zsh "$H/ambient_snapshot.sh" "$LABEL after turn $T" > "$EV/ambient/turn-$NN-after.txt" 2>&1
 {
   echo "######## TURN $T  start $startl  end $endl  elapsed $((end-start))s  (local, $(date +%F); UTC wall-clock start $startu end $endu; exit code $rc)"
   echo "######## LENA (prompt sent verbatim):"
--- G0-noise-baseline/evidence/harness/safety-snapshot.sh
+++ P1-itemized-playbook/evidence/harness/safety-snapshot.sh
@@ -1,9 +1,9 @@
 #!/bin/zsh
-# G0 safety snapshot (E7's; read-only). Usage: safety-snapshot.sh <label>   -> prints to stdout
-# Content per protocol.md 4.8 (E3's snapshot + E4 additions; G0: the product sha 3c841bb9, G0's protocol path, the /tmp/hirearchy-g0-* listing). Never modifies anything it lists.
+# P1 safety snapshot (G0's = E7's; read-only). Usage: safety-snapshot.sh <label>   -> prints to stdout
+# Content per protocol.md 4.8 (E3's snapshot + E4 additions; P1: the product sha 8bf7c69b, P1's protocol path, the /tmp/hirearchy-p1-* listing). Never modifies anything it lists.
 label="${1:-snapshot}"
 REPO=/Volumes/workspace/hirearchy
-PROTO=$REPO/studies/G0-noise-baseline/evidence/protocol.md
+PROTO=$REPO/studies/P1-itemized-playbook/evidence/protocol.md
 echo "label: $label"
 echo "date: $(date)"
 echo "date_utc: $(date -u +%Y-%m-%dT%H:%M:%SZ)  epoch: $(date +%s)"
@@ -19,7 +19,7 @@
 ls -la ~/.kiro/agents
 echo "== md5 ~/.kiro/agents/*"
 for f in ~/.kiro/agents/*(.N); do md5 "$f"; done
-echo "== hirearchy-* profiles in ~/.kiro/agents (pre-existing vs generated by G0: hirearchy-study-g0-*)"
+echo "== hirearchy-* profiles in ~/.kiro/agents (pre-existing vs generated by P1: hirearchy-study-p1-*)"
 ls -1 ~/.kiro/agents | grep '^hirearchy-' || echo "(none)"
 echo "== ls ~/.kiro/skills"
 ls ~/.kiro/skills
@@ -36,13 +36,13 @@
 git -C $REPO status --porcelain
 echo "== git HEAD"
 git -C $REPO rev-parse HEAD
-echo "== git diff --stat 3c841bb9 HEAD -- src skills pyproject.toml uv.lock"
-git -C $REPO diff --stat 3c841bb9 HEAD -- src skills pyproject.toml uv.lock
+echo "== git diff --stat 8bf7c69b HEAD -- src skills pyproject.toml uv.lock"
+git -C $REPO diff --stat 8bf7c69b HEAD -- src skills pyproject.toml uv.lock
 echo "== md5 protocol.md"
 md5 $PROTO
 echo "== other orgs"
 ls -d /Volumes/workspace/orgs
 ls -la /Volumes/workspace/orgs
-echo "== /tmp/hirearchy-g0-* (sandboxes and dedicated kiro homes; names only)"
-g0dirs=(/tmp/hirearchy-g0-*(N))
+echo "== /tmp/hirearchy-p1-* (sandboxes and dedicated kiro homes; names only)"
+g0dirs=(/tmp/hirearchy-p1-*(N))
 if (( ${#g0dirs} )); then print -rl -- ${g0dirs:t}; else echo "(none)"; fi
--- G0-noise-baseline/evidence/harness/score_memos.py
+++ P1-itemized-playbook/evidence/harness/score_memos.py
@@ -23,7 +23,8 @@
 from datetime import datetime, timezone
 from pathlib import Path
 
-DEFAULT_ANSWER_KEY = "/Volumes/workspace/hirearchy/studies/G0-noise-baseline/evidence/answer-key.md"
+DEFAULT_ANSWER_KEY = "/Volumes/workspace/hirearchy/studies/P1-itemized-playbook/evidence/answer-key.md"  # = E7's and G0's (md5 2fb69bbe...)
+DEFAULT_ANSWER_KEY_P1 = "/Volumes/workspace/hirearchy/studies/P1-itemized-playbook/evidence/answer-key-p1.md"  # memos 4-6
 DEFAULT_EXPECTED = str(Path(__file__).resolve().parent / "selfcheck" / "e7-expected-team.json")
 
 # ---------------------------------------------------------------------------------------------------------------------------
@@ -74,6 +75,55 @@
         ],
     },
 }
+# P1 (protocol section 4): memos 4-6, pre-registered with their notes before any P1 stream; the same "in substance" rule.
+_GW = ["gateway"]
+KEY_P1 = {
+    "2026-10-26": {
+        "decisions": [
+            {"id": "D1", "all": [_GW, ["cut over", "cutover", "cut-over", "switch"], ["28"]]},
+            {"id": "D2", "all": [_RL, ["large-plan", "large plan"]]},
+            {"id": "D3", "all": [["renovate"], ["all repo", "every repo", "all the repo", "november"]]},
+        ],
+        "actions": [
+            {"id": "A1", "owner": "Dev", "due": "2026-10-28", "all": [_GW, ["cutover", "cut over", "cut-over"]]},
+            {"id": "A2", "owner": "Priya", "due": "2026-10-30", "all": [_RL + ["flag"], ["large-plan", "large plan", "enable"]]},
+            {"id": "A3", "owner": "Marta", "due": "2026-10-27", "all": [["feedback"], ["summary", "send", "product"]]},
+            {"id": "A4", "owner": "Sam", "due": "2026-10-30", "all": [["onboarding"], ["=ci", "pipeline", "notes"]]},
+            {"id": "A5", "owner": "Lee", "due": "none", "all": [["runbook", "sso"]]},
+        ],
+    },
+    "2026-11-02": {
+        "decisions": [
+            {"id": "D1", "all": [["old gateway"], ["13"]]},
+            {"id": "D2", "all": [_RL, ["all plans", "every plan", "all customers"], ["16"]]},
+            {"id": "D3", "all": [["deck"], ["customer", "this week", "send"]]},
+        ],
+        "actions": [
+            {"id": "A1", "owner": "Dev", "due": "2026-11-13", "all": [["old gateway", "gateway"], ["switch off", "shut", "turn off", "decommission", "switch-off"]]},
+            {"id": "A2", "owner": "Priya", "due": "2026-11-06", "all": [["rollout", "roll-out", "roll out"], ["plan"]]},
+            {"id": "A3", "owner": "JD", "due": "2026-11-05", "all": [["deck"]]},
+            {"id": "A4", "owner": "Marta", "due": "none", "all": [["quarterly review", "review meeting"]]},
+            {"id": "A5", "owner": "Lee", "due": "2026-11-04", "all": [["invoice"]]},
+        ],
+    },
+    "2026-11-09": {
+        "decisions": [
+            {"id": "D1", "all": [["switch-off", "switch off", "old gateway"], ["20"]]},
+            {"id": "D2", "all": [["rollout plan", "roll-out plan", "rollout"], ["approv", "accept", "as written"]]},
+            {"id": "D3", "all": [["=jo"], ["on-call", "on call", "rotation"]]},
+        ],
+        "actions": [
+            {"id": "A1", "owner": "Marta", "due": "2026-11-11", "all": [["quarterly review", "review notes"]]},
+            {"id": "A2", "owner": "Dev", "due": "2026-11-20", "all": [["old gateway", "gateway"], ["switch off", "shut", "turn off", "decommission", "switch-off"]]},
+            {"id": "A3", "owner": "Priya", "due": "2026-11-16", "all": [_RL + ["rollout", "roll out"], ["all plans", "start", "rollout", "roll out"]]},
+            {"id": "A4", "owner": "Sam", "due": "2026-11-13", "all": [["=jo"], ["on-call", "on call", "rotation"]]},
+            {"id": "A5", "owner": "Lee", "due": "none", "all": [["audit log", "service account"]]},
+        ],
+    },
+}
+KEY3 = dict(KEY)  # E7's three meetings (G0's KEY, unchanged)
+P1 = {"on": False, "forms": [("", "N")]}  # set by --memos 6 / --owner-forms (P1 protocol 12.3); off = G0's scoring, byte for byte
+
 N_DECISIONS = sum(len(m["decisions"]) for m in KEY.values())  # 8
 N_ACTIONS = sum(len(m["actions"]) for m in KEY.values())  # 15
 
@@ -270,17 +320,50 @@
     return c.lower()
 
 
-def score_memo(text, meeting):
+_INITIALS = re.compile(r"(?:[A-Z]\.?){1,3}")
+
+
+def owner_is(cell, owner):
+    """The row's Owner cell denotes the key's owner: G0's equality; in P1 mode also its initials (or, for JD, a cell naming JD)."""
+    c = strip_marks(cell).strip()
+    if c.lower() == owner.lower():
+        return True
+    if not P1["on"]:
+        return False
+    if owner == "JD":
+        return re.search(r"\bJD\b", c) is not None
+    return bool(_INITIALS.fullmatch(c)) and c[0] == owner[0].upper()
+
+
+def owner_form_ok(cell, owner, form):
+    """P1 answer-key-p1.md 'Owner form': N names, I initials, N+J names and '<initials> (full name not in the notes)'."""
+    c = strip_marks(cell).strip()
+    if owner == "JD":
+        return form == "N+J" and "JD" in c and "(full name not in the notes)" in c.lower().replace("\u2019", "'")
+    if form == "I":
+        return bool(_INITIALS.fullmatch(c)) and c[0] == owner[0].upper()
+    return c.lower() == owner.lower()
+
+
+def form_at(t):
+    form = "N"
+    for since, f in P1["forms"]:
+        if t is None or since <= (t or ""):
+            form = f
+    return form
+
+
+def score_memo(text, meeting, form="N"):
     """Score one memo's text against the key of `meeting` (KeyError for an unknown meeting)."""
     key = KEY[meeting]
     dec_items = decision_items(text)
     found_d = [d["id"] for d in key["decisions"] if any(groups_match(d["all"], it) for it in dec_items)]
     rows = action_rows(text)
-    consumed, found_a, wrong, extra = set(), [], [], []
+    consumed, found_a, wrong, extra, owner_form = set(), [], [], [], []
     for r in rows:
         hit = None
         for a in key["actions"]:
-            if a["owner"].lower() == strip_marks(r["owner"]).lower() and groups_match(a["all"], r["action"]):
+            if owner_is(r["owner"], a["owner"]) and groups_match(a["all"], r["action"]):
                 hit = a
                 break
         if hit is None or hit["id"] in consumed:
@@ -288,6 +371,8 @@
             continue
         consumed.add(hit["id"])
         found_a.append(hit["id"])
+        if P1["on"] and not owner_form_ok(r["owner"], hit["owner"], form):
+            owner_form.append({"owner": hit["owner"], "cell": strip_marks(r["owner"]).strip(), "form": form, "action": hit["id"]})
         if due_value(r["due"]) != hit["due"]:
             wrong.append({"owner": hit["owner"], "due": r["due"], "expected": hit["due"], "action": hit["id"]})
     return {
@@ -296,6 +381,7 @@
         "wrong_dates": wrong, "extra_rows": extra,
         "summary_first": summary_first(text), "decisions_before_actions": decisions_before_actions(text),
         "words": words(text),
+        **({"owner_form_errors": owner_form, "owner_form": form} if P1["on"] else {}),
     }
 
 
@@ -682,7 +768,8 @@
         if m:
             parsed[meeting]["actions"].append((m.group(2), _key_due(m.group(4))))
     meetings = {}
-    for mt, k in KEY.items():
+    keys = KEY if not P1["on"] else {mt: k for mt, k in KEY.items() if (mt in KEY_P1) == (Path(path).name == Path(DEFAULT_ANSWER_KEY_P1).name)}
+    for mt, k in keys.items():
         got = parsed.get(mt)
         if got is None:
             meetings[mt] = None
@@ -693,13 +780,50 @@
     ok = all(m is not None and m["decisions"] == len(KEY[mt]["decisions"]) and m["actions"] == len(KEY[mt]["actions"])
              and m["owners_match"] and m["dues_match"] for mt, m in meetings.items())
     return {"md5": md5_bytes(raw), "meetings": meetings, "ok": ok}
+
+
+def p1_no_regression(versions, finals):
+    """P1 protocol 12.3 (design 21.1 item 3): E7's rule per memo with G0's gate-able outcome measures (G0 STUDY.md "What Phase 1 must
+    know" item 2, the team's outcome: every key decision, every key action, 0 wrong dates, 0 extra rows) on the final memos, and every
+    delivered (copied, D6) version with 0 wrong dates and 0 extra rows: `mechanical_pass`. The parts of E7's rule that G0 did not name as
+    gate-able are `reported`, never a pass rule: the Summary line first and the order (G0 item 1, "Summary-first: 2-3 of 3"), and the owner
+    form (P1's script; G0 had no owner-form measure; the action count is D18's, the right person and the substance). The D8 deliveries by
+    presentation are judged (judged.json); D14 is reported (spend-rederived.json)."""
+    per_memo, reported = {}, {}
+    for mt in KEY:
+        f = next((x for x in finals if x.get("memo") == mt and "error" not in x), None)
+        if f is None:
+            per_memo[mt] = {"final": None, "pass": False, "why": "no final memo (E7 10.4: a memo not delivered fails)"}
+            reported[mt] = {"final": None, "ok": False, "why": "no final memo"}
+            continue
+        reasons, rep = [], []
+        if f["decisions"]["k"] != f["decisions"]["n"]:
+            reasons.append(f"decisions {f['decisions']['k']}/{f['decisions']['n']}")
+        if f["actions"]["k"] != f["actions"]["n"]:
+            reasons.append(f"actions {f['actions']['k']}/{f['actions']['n']}")
+        if f["wrong_dates"]:
+            reasons.append(f"{len(f['wrong_dates'])} wrong dates")
+        if f["extra_rows"]:
+            reasons.append(f"{len(f['extra_rows'])} extra rows")
+        if f.get("owner_form_errors"):
+            rep.append(f"{len(f['owner_form_errors'])} owner-form errors")
+        if not (f["summary_first"] and f["decisions_before_actions"]):
+            rep.append("Summary first / order")
+        per_memo[mt] = {"final": f["file"], "pass": not reasons, "why": "; ".join(reasons) or "ok"}
+        reported[mt] = {"final": f["file"], "ok": not rep, "why": "; ".join(rep) or "ok"}
+    delivered = [v for v in versions if v.get("copied") and "error" not in v]
+    bad = [f"{v['memo']} v{v['version']} {v['sha']}: {len(v['wrong_dates'])} wrong dates, {len(v['extra_rows'])} extra rows"
+           for v in delivered if v["wrong_dates"] or v["extra_rows"]]
+    return {"per_memo": per_memo, "delivered_versions": len(delivered), "delivered_bad": bad,
+            "mechanical_pass": all(x["pass"] for x in per_memo.values()) and not bad,
+            "reported": reported, "reported_ok": all(x["ok"] for x in reported.values())}
 
 
 # ---------------------------------------------------------------------------------------------------------------------------
 # scoring a stream
 # ---------------------------------------------------------------------------------------------------------------------------
-def _score_fields(b, meeting):
-    r = score_memo(b.decode("utf-8", errors="replace"), meeting)
+def _score_fields(b, meeting, form="N"):
+    r = score_memo(b.decode("utf-8", errors="replace"), meeting, form)
     r["words"] = words(b)
     r["n_wrong_dates"] = len(r["wrong_dates"])
     r["wrong_date_text"] = [f"{w['owner']} {w['due']}" for w in r["wrong_dates"]]
@@ -712,7 +836,11 @@
     rd = Reader(stream)
     versions = load_versions(stream, rd)
     for v in versions:
-        v.update(_score_fields(v.pop("_bytes"), v["memo"]))
+        if v["memo"] not in KEY:
+            v.pop("_bytes")
+            v.update({"error": "not a meeting of the key"})
+            continue
+        v.update(_score_fields(v.pop("_bytes"), v["memo"], form_at(v.get("commit_time"))))
     copies = load_copies(stream, rd)
     finals_md5 = final_md5s(stream, rd)
     versions = mark_copied(versions, copies, load_log_md5s(stream, rd), finals_md5)
@@ -728,9 +856,9 @@
         if memo not in KEY:
             finals.append({"memo": memo, "file": rd.rel(p), "md5": md5_bytes(b), "error": "not a meeting of the key"})
             continue
-        f = _score_fields(b, memo)
+        match = next((v for v in versions if v["memo"] == memo and v["md5"] == md5_bytes(b)), None)
+        f = _score_fields(b, memo, form_at(match.get("commit_time") if match else None))
         f.update({"memo": memo, "file": rd.rel(p), "md5": md5_bytes(b)})
-        match = next((v for v in versions if v["memo"] == memo and v["md5"] == f["md5"]), None)
         f["is_version"] = {"version": match["version"], "sha": match["sha"]} if match else None
         finals.append(f)
         tot["d"] += f["decisions"]["k"]
@@ -759,10 +887,14 @@
             f"review task {u['task']} ({u['task_created']}, memo {u['memo']}) maps to no version"
             + (f" (it was sent {u['seconds_before_candidate_commit']} s before the commit of v{u['candidate_version']})"
                if u["candidate_version"] else ""))
+    if P1["on"]:
+        out["p1_no_regression"] = p1_no_regression(versions, finals)
     if answer_key:
         out["answer_key"] = {"path": str(answer_key), **key_check(answer_key)}
         if Path(answer_key).exists():
             rd.note(answer_key)
+        if P1["on"]:
+            out["answer_key_p1"] = {"path": DEFAULT_ANSWER_KEY_P1, **key_check(DEFAULT_ANSWER_KEY_P1)}
     out["source_files"] = rd.source_files()
     return out
 
@@ -896,7 +1028,17 @@
     ap.add_argument("--answer-key", default=DEFAULT_ANSWER_KEY)
     ap.add_argument("--selfcheck", metavar="E7EV")
     ap.add_argument("--expected", default=DEFAULT_EXPECTED)
+    ap.add_argument("--memos", type=int, default=3, help="3: G0's scoring (E7's key); 6: P1's (memos 4-6 and the owner forms)")
+    ap.add_argument("--owner-forms", help="P1: JSON list of [utc, form] from the stream's lena-lines (protocol 12.3)")
     a = ap.parse_args(argv)
+    if a.memos == 6:
+        global KEY, N_DECISIONS, N_ACTIONS
+        KEY = {**KEY3, **KEY_P1}
+        N_DECISIONS = sum(len(m["decisions"]) for m in KEY.values())
+        N_ACTIONS = sum(len(m["actions"]) for m in KEY.values())
+        P1["on"] = True
+        if a.owner_forms:
+            P1["forms"] = [("", "N")] + [tuple(x) for x in json.loads(Path(a.owner_forms).read_text())]
     if a.selfcheck:
         return run_selfcheck("score_memos", a.selfcheck, a.out, a.expected, lambda sd: score_stream(sd, a.answer_key), "score_memos", render_txt)
     if not a.streamdir:
--- G0-noise-baseline/evidence/harness/setup_stream.sh
+++ P1-itemized-playbook/evidence/harness/setup_stream.sh
@@ -1,36 +1,42 @@
 #!/bin/zsh
-# G0 stream setup (protocol 6 item 1 for G0; E7 6 item 1 + design 20.1/20.3). Usage: setup_stream.sh <label> [--dry-run]
-#   <label>  m0-s<n> or m1-s<n> (replacements m0-s<n>r, m0-s<n>r2, ...)
+# P1 stream setup (G0's setup_stream.sh, M1 treatment only; protocol 7). Usage: setup_stream.sh <label> [--dry-run]
+#   <label>  F1 F2 F3 I1 I2 I3 (a replacement, only after the manager's recorded approval: F1r ...); the arm is the first letter
 # Gates, checked before anything is created (any failure prints "GATE FAILED: ..." and exits 3):
 #   1. md5 -q of $EV/protocol.md equals $EV/protocol.md5;
 #   2. every line of $H/MD5SUMS ("<md5>  <name>"): the md5 of $H/<name> equals it;
-#   3. git HEAD of the repo is the full sha of 3c841bb9;
-#   4. `git diff --stat 3c841bb9 HEAD -- src skills pyproject.toml uv.lock` is empty;
+#   3. git HEAD of the repo is the full sha of 8bf7c69b;
+#   4. `git diff --stat 8bf7c69b HEAD -- src skills pyproject.toml uv.lock` is empty;
 #   5. (not in --dry-run) `kiro-cli chat --list-models` lists claude-sonnet-5.5 (no substitution; the stream does not start otherwise);
-#   6. the skill rule of design 20.1: the repo SKILL.md has the required md5 and the owner's global copy equals it or is absent.
-# Then it creates: the stream folder $EV/<label>/ (sandbox-path.txt, epoch.txt, arm.txt, stream-start-utc.txt), safety-before.txt, for arm m0 the
-# dedicated kiro home (prepare_m0_home.sh), ambient/setup.txt (arm m0: also the dedicated home's listings), the sandbox S=/tmp/hirearchy-g0-<label>-
+#   6. the skill rule of design 20.1: the repo SKILL.md has the required md5 and the owner's global copy equals it or is absent;
+#   7. KIRO_HOME is not set in the facilitator's shell (protocol 1: unset in both arms; the injection script's scheduler and its org runs
+#      inherit this shell, so it is gated here, not only removed by run_turn.sh's `env -u KIRO_HOME`).
+# The memories gate (protocol 3 and 8; design 18.2), after the gates and refusals and before anything is created: memories_gate.py compares
+# the md5 of ~/.kiro/memories/memories.db now with the previous stream's memories-md5-after.txt; a change prints its `STOP:` line and exits
+# 4 (nothing is created) unless $EV/manager-decision-memories-before-<label>.md exists (the stream step sends a warning and waits).
+# Then it creates: the stream folder $EV/<label>/ (sandbox-path.txt, epoch.txt, arm.txt, stream-start-utc.txt), safety-before.txt, the owner's
+# memories.db md5 (memories-md5-before.txt: the value the memories gate checked; the gate's line in memories-db.txt), ambient/setup.txt, the sandbox S=/tmp/hirearchy-p1-<label>-
 # <epoch> (S/notes = $EV/notes/*; S/.kiro/skills/hirearchy/SKILL.md = the repo copy; S/.kiro/settings/cli.json = $H/workspace-cli.json; S/org is NOT
-# created), the stream's profile from profile-template.json (arm m1: ~/.kiro/agents/; arm m0: <M0H>/.kiro/agents/; a copy in profiles/ and a line in
+# created), the stream's profile from profile-template.json (both arms: ~/.kiro/agents/; a copy in profiles/ and a line in
 # profiles/creations.txt), model_check.sh listed, setup.txt and skill_check.sh <label> setup.
 # --dry-run prints the plan (and the gate results, which it only reports) and creates and writes nothing. It never runs a turn, a chat, the
 # hirearchy CLI, an MCP server or the scheduler.
-# Exit: 0 ok; 2 usage / bad label; 3 gate failed; 4 refused (the stream folder or the profile exists already) or a creation step failed;
+# Exit: 0 ok; 2 usage / bad label; 3 gate failed; 4 refused (the stream folder or the profile exists already; memories.db changed since the
+# previous stream without the manager's decision) or a creation step failed;
 # 5 the skill check of the finished setup says invalid (H2).
 REPO=/Volumes/workspace/hirearchy
-ST=$REPO/studies/G0-noise-baseline
+ST=$REPO/studies/P1-itemized-playbook
 EV=$ST/evidence
 H=$EV/harness
-SHA_REF=3c841bb9
-REQUIRED_SKILL_MD5=a3e46347b70a7ece5f734f70198c607f
+SHA_REF=8bf7c69b
+REQUIRED_SKILL_MD5=b10238639f48ab351fa44a06aed03ffb
 
 LABEL="$1"; DRY=0
 [[ "$2" == "--dry-run" ]] && DRY=1
 [[ $# -eq 1 || ( $# -eq 2 && $DRY -eq 1 ) ]] || { echo "usage: setup_stream.sh <label> [--dry-run]" >&2; exit 2; }
-[[ "$LABEL" =~ '^(m0|m1)-s[1-9][0-9]*(r[0-9]*)?$' ]] || { echo "setup_stream.sh: '$LABEL' is not a G0 stream label (m0-s<n> | m1-s<n>, replacements ...r, ...r2)" >&2; exit 2; }
-ARM=${LABEL%%-*}
+[[ "$LABEL" =~ '^[FI][1-3](r[0-9]*)?$' ]] || { echo "setup_stream.sh: '$LABEL' is not a P1 stream label (F1..F3, I1..I3, replacements ...r)" >&2; exit 2; }
+ARM=${LABEL[1,1]}
 STREAM=$EV/$LABEL
-PNAME=hirearchy-study-g0-$LABEL-assistant
+PNAME=hirearchy-study-p1-$LABEL-assistant
 
 fails=()
 gate() {  # gate <name> <ok 0/1> <detail>
@@ -66,6 +72,8 @@
 GLOBAL_SKILL_MD5=""; [[ -f $GLOBAL_SKILL ]] && GLOBAL_SKILL_MD5=$(md5 -q $GLOBAL_SKILL)
 [[ "$REPO_SKILL_MD5" == "$REQUIRED_SKILL_MD5" ]] && gate "repo SKILL.md md5" 1 "$REPO_SKILL_MD5" || gate "repo SKILL.md md5" 0 "$REPO_SKILL_MD5, required $REQUIRED_SKILL_MD5"
 [[ -z "$GLOBAL_SKILL_MD5" || "$GLOBAL_SKILL_MD5" == "$REPO_SKILL_MD5" ]] && gate "global SKILL.md absent or = repo" 1 "${GLOBAL_SKILL_MD5:-absent}" || gate "global SKILL.md absent or = repo" 0 "global $GLOBAL_SKILL_MD5, repo $REPO_SKILL_MD5 (H2)"
+# 7. KIRO_HOME unset (protocol 1)
+[[ -z "${KIRO_HOME+set}" ]] && gate "KIRO_HOME unset in this shell" 1 || gate "KIRO_HOME unset in this shell" 0 "KIRO_HOME is set: unset it before the stream (protocol 1)"
 # 5. model listed
 if [[ $DRY -eq 0 ]]; then
   LISTING="$(kiro-cli chat --list-models 2>&1)"
@@ -75,31 +83,43 @@
 fi
 # refusals (not gates): nothing is overwritten
 [[ -e $STREAM/sandbox-path.txt ]] && { echo "REFUSED: $STREAM/sandbox-path.txt exists: this label was set up already" >&2; exit 4; }
-if [[ $ARM == m1 ]]; then PDIR=$HOME/.kiro/agents; else PDIR="<M0H>/.kiro/agents"; fi
-[[ $ARM == m1 && -e $PDIR/$PNAME.json ]] && { echo "REFUSED: $PDIR/$PNAME.json exists already" >&2; exit 4; }
+PDIR=$HOME/.kiro/agents
+[[ -e $PDIR/$PNAME.json ]] && { echo "REFUSED: $PDIR/$PNAME.json exists already" >&2; exit 4; }
+[[ "$LABEL" == *r* && ! -e $EV/manager-decision-replacement-${LABEL%r*}.md ]] && { echo "REFUSED: replacement $LABEL needs the manager's recorded approval $EV/manager-decision-replacement-${LABEL%r*}.md (protocol 8)" >&2; exit 4; }
+[[ "$LABEL" =~ '^[FI][1-3]r[0-9]*$' && "$LABEL" != ?[1-3]r ]] && { echo "REFUSED: a replacement is <label>r, one per stream (protocol 8)" >&2; exit 4; }
+if [[ "$LABEL" == *r ]]; then
+  other=($EV/${ARM}[1-3]r(N/)); other=(${other:#$STREAM})
+  (( ${#other} )) && { echo "REFUSED: arm $ARM has a replacement stream already (${other:t}): at most one per arm (protocol 8)" >&2; exit 4; }
+fi
 
 if (( ${#fails} )); then
   for f in $fails; do echo "GATE FAILED: $f"; done
   if [[ $DRY -eq 0 ]]; then exit 3; fi
 fi
+# the memories gate (protocol 8): a change of memories.db since the previous stream's end stops the study before this stream, as a change
+# during a stream does; checked before any folder, sandbox or profile exists (md5 only, never the store)
+MDB=$HOME/.kiro/memories/memories.db
+MDB_NOW=$( [[ -f $MDB ]] && md5 -q $MDB || echo absent )
+MGATE=$(python3 -B $H/memories_gate.py --ev $EV --label $LABEL --current "$MDB_NOW"); MGRC=$?
+echo "$MGATE"
+if (( MGRC != 0 )); then
+  if [[ $DRY -eq 0 ]]; then exit 4; fi
+  echo "DRY-RUN: without --dry-run this would exit 4 (nothing created)"
+fi
 
 EPOCH=$(date +%s)
-S=/tmp/hirearchy-g0-$LABEL-$EPOCH
-M0H=""; [[ $ARM == m0 ]] && M0H=/tmp/hirearchy-g0-m0home-$LABEL-$EPOCH
-PROFILE_DIR=$HOME/.kiro/agents; [[ $ARM == m0 ]] && PROFILE_DIR=$M0H/.kiro/agents
-KH_ARG=""; [[ $ARM == m0 ]] && KH_ARG=$M0H/.kiro
+S=/tmp/hirearchy-p1-$LABEL-$EPOCH
+PROFILE_DIR=$HOME/.kiro/agents
+KH_ARG=""
 
 if [[ $DRY -eq 1 ]]; then
   echo "DRY-RUN setup_stream.sh $LABEL (nothing is created or written)"
   (( ${#fails} )) && echo "DRY-RUN: ${#fails} gate(s) failed above; without --dry-run this would print GATE FAILED and exit 3"
   echo "arm: $ARM"
   echo "S=$S   (epoch $EPOCH; S/org is NOT created)"
-  [[ $ARM == m0 ]] && echo "M0H=$M0H"
   echo "DRY-RUN: mkdir $STREAM; write sandbox-path.txt, epoch.txt, arm.txt, stream-start-utc.txt"
   echo "DRY-RUN: safety-snapshot.sh \"$LABEL before\" > $STREAM/safety-before.txt"
-  if [[ $ARM == m0 ]]; then
-    zsh $H/prepare_m0_home.sh $LABEL $M0H --dry-run | sed 's/^/  /'
-  fi
+  echo "DRY-RUN: write the memories gate's md5 ($MDB_NOW) to $STREAM/memories-md5-before.txt and its line to memories-db.txt"
   echo "DRY-RUN: ambient_snapshot.sh \"$LABEL setup\" $KH_ARG > $STREAM/ambient/setup.txt"
   echo "DRY-RUN: mkdir $S/notes $S/.kiro/skills/hirearchy $S/.kiro/settings"
   echo "DRY-RUN: cp -p $EV/notes/* $S/notes/"
@@ -119,9 +139,9 @@
 echo $ARM > $STREAM/arm.txt
 echo $STARTU > $STREAM/stream-start-utc.txt
 zsh $H/safety-snapshot.sh "$LABEL before" > $STREAM/safety-before.txt 2>&1
-if [[ $ARM == m0 ]]; then
-  zsh $H/prepare_m0_home.sh $LABEL $M0H || { echo "FAILED: prepare_m0_home.sh" >&2; exit 4; }
-fi
+# the owner's memories.db before this stream (design 18.2): the md5 the memories gate checked, never the store itself
+echo $MDB_NOW > $STREAM/memories-md5-before.txt
+echo "before $LABEL ($(date -u +%FT%TZ)): $MGATE" >> $STREAM/memories-db.txt
 zsh $H/ambient_snapshot.sh "$LABEL setup" $KH_ARG > $STREAM/ambient/setup.txt 2>&1
 mkdir -p $S/notes $S/.kiro/skills/hirearchy $S/.kiro/settings || { echo "FAILED: cannot create the sandbox $S" >&2; exit 4; }
 cp -p $EV/notes/*(.N) $S/notes/ || { echo "FAILED: notes" >&2; exit 4; }
@@ -136,17 +156,18 @@
 zsh $H/model_check.sh listed $LABEL > /dev/null 2>&1; MCRC=$?
 # the study's first profile copy: the earliest other stream with a profiles/ copy
 REF=""; REFSTART=""
-for d in $EV/(m0|m1)-s*(/N); do
+for d in $EV/[FI][1-3]*(/N); do
   [[ "$d" == "$STREAM" ]] && continue
-  rf=($d/profiles/hirearchy-study-g0-*-assistant.json(N)); [[ -n "${rf[1]}" && -f $d/stream-start-utc.txt ]] || continue
+  rf=($d/profiles/hirearchy-study-p1-*-assistant.json(N)); [[ -n "${rf[1]}" && -f $d/stream-start-utc.txt ]] || continue
   st=$(cat $d/stream-start-utc.txt)
   if [[ -z "$REFSTART" || "$st" < "$REFSTART" ]]; then REF=${rf[1]}; REFSTART=$st; fi
 done
 {
-  echo "# G0 $LABEL setup (recorded before turn 1)"
+  echo "# P1 $LABEL setup (recorded before turn 1)"
   echo "date: $(date); utc: $(date -u +%FT%TZ)"
   echo "arm: $ARM"
-  [[ $ARM == m0 ]] && echo "M0 home: $M0H (kiro home for the chat: $M0H/.kiro; $STREAM/m0-home/setup.txt)"
+  echo "kiro home for the chat: the owner's ~/.kiro (run_turn.sh: env -u KIRO_HOME, both arms); KIRO_HOME set in this shell? $( [[ -n "${KIRO_HOME+set}" ]] && echo yes || echo no )"
+  echo "memories.db md5 before this stream: $(cat $STREAM/memories-md5-before.txt)"
   echo "== protocol.md vs protocol.md5"
   echo "md5 -q protocol.md: $(md5 -q $EV/protocol.md)"
   echo "protocol.md5: $(awk '{print $1; exit}' $EV/protocol.md5)"
@@ -161,11 +182,10 @@
   echo "repo SKILL.md md5: $REPO_SKILL_MD5"
   echo "injection script md5: $(md5 -q $H/inject_root_rework.py)"
   echo "== HIREARCHY_STATE_DIR set? $( [[ -n "${HIREARCHY_STATE_DIR+set}" ]] && echo yes || echo no )"
-  echo "== processes referencing any G0 sandbox"
-  PSG=$(ps -axo pid,etime,command | grep -F hirearchy-g0- | grep -v grep | cut -c1-200); [[ -n "$PSG" ]] && print -r -- "$PSG" || echo "(none)"
+  echo "== processes referencing any P1 sandbox"
+  PSG=$(ps -axo pid,etime,command | grep -F hirearchy-p1- | grep -v grep | cut -c1-200); [[ -n "$PSG" ]] && print -r -- "$PSG" || echo "(none)"
   echo "== ~/.kiro/agents"
   ls $HOME/.kiro/agents
-  [[ $ARM == m0 ]] && { echo "== $M0H/.kiro/agents"; ls $M0H/.kiro/agents; }
   echo "== repo checks (4.1) BEFORE turn 1"
   echo "git rev-parse HEAD: $(git -C $REPO rev-parse HEAD)"
   echo "git status --porcelain:"; git -C $REPO status --porcelain
@@ -176,7 +196,12 @@
   echo "== assistant profile ($PROFILE_DIR/$PNAME.json; copy in profiles/)"
   md5 $PROFILE_DIR/$PNAME.json
   echo "kiro-cli agent validate --path: exit $VRC (output in profiles/validate.txt)"
-  if [[ -n "$REF" ]]; then echo "(diff against the study's first profile copy $REF:)"; diff $REF $PROFILE_DIR/$PNAME.json; echo "(diff exit $?)"; else echo "(diff against the study's first profile copy: this is the first stream, no reference)"; fi
+  if [[ -n "$REF" ]]; then
+    RL=${${REF:t}#hirearchy-study-p1-}; RL=${RL%-assistant.json}; RE=$(cat ${REF:h:h}/epoch.txt 2>/dev/null)
+    echo "(diff against the study's first profile copy $REF, raw: the label and the sandbox epoch only)"; diff $REF $PROFILE_DIR/$PNAME.json; echo "(diff exit $?)"
+    echo "(the same diff with the label and the epoch masked in both: empty means byte-identical but for them, protocol 1)"
+    diff <(sed -e "s/$RL/<LABEL>/g" -e "s/$RE/<epoch>/g" $REF) <(sed -e "s/$LABEL/<LABEL>/g" -e "s/$EPOCH/<epoch>/g" $PROFILE_DIR/$PNAME.json); echo "(masked diff exit $?)"
+  else echo "(diff against the study's first profile copy: this is the first stream, no reference)"; fi
   echo "== workspace settings"
   md5 $S/.kiro/settings/cli.json
   cat $S/.kiro/settings/cli.json; md5 $H/workspace-cli.json
@@ -184,19 +209,17 @@
   md5 $REPO/skills/hirearchy/SKILL.md
   md5 $S/.kiro/skills/hirearchy/SKILL.md
   [[ -f $GLOBAL_SKILL ]] && echo "global: md5 $GLOBAL_SKILL_MD5 ($GLOBAL_SKILL)" || echo "global: absent"
-  [[ $ARM == m0 ]] && { [[ -f $M0H/.kiro/skills/hirearchy/SKILL.md ]] && md5 $M0H/.kiro/skills/hirearchy/SKILL.md || echo "M0 copy: absent"; }
   wc -l $REPO/skills/hirearchy/SKILL.md $S/.kiro/skills/hirearchy/SKILL.md
   echo "== notes"
   md5 $S/notes/*
   echo "== org dir exists before turn 1? $( [[ -e $S/org ]] && echo YES || echo no )"
   echo "== ps: processes referencing the sandbox"
   PSS=$(ps -axo pid,etime,command | grep -F "$S" | grep -v grep); [[ -n "$PSS" ]] && print -r -- "$PSS" || echo "(none)"
-  echo "== other G0 streams running: $(ps -axo command | grep -F hirearchy-g0- | grep -v grep | grep -vF "$S" | wc -l | tr -d ' ') processes"
+  echo "== other P1 streams running: $(ps -axo command | grep -F hirearchy-p1- | grep -v grep | grep -vF "$S" | wc -l | tr -d ' ') processes"
   echo "== safety-before.txt taken: $(grep -m1 '^date_utc' $STREAM/safety-before.txt); ambient/setup.txt taken"
 } > $STREAM/setup.txt 2>&1
 zsh $H/skill_check.sh $LABEL setup > /dev/null 2>&1; SRC=$?
 echo "set up $LABEL: S=$S arm=$ARM"
-[[ $ARM == m0 ]] && echo "M0H=$M0H"
 echo "profile: $PROFILE_DIR/$PNAME.json (md5 $PMD5)"
 if [[ $SRC -ne 0 ]]; then echo "SKILL CHECK: INVALID (H2), see $STREAM/skill-check.txt: do not start this stream" >&2; exit 5; fi
 exit 0
--- G0-noise-baseline/evidence/harness/skill_check.sh
+++ P1-itemized-playbook/evidence/harness/skill_check.sh
@@ -1,48 +1,37 @@
 #!/bin/zsh
-# G0 skill check (design 20.1 "Identical skill bytes in both arms"; E7 protocol 4.4, 4.4.1). Usage: skill_check.sh <label> setup|turn1
+# P1 skill check (G0's, M1 only; design 18.2 "the same workspace skill copy (md5 checked)"; E7 protocol 4.4, 4.4.1). Usage: skill_check.sh <label> setup|turn1
 # Writes (rewrites) $EV/<label>/skill-check.txt and prints it. Exit 0: the md5 rule holds; 1: the stream is invalid (H2); 2: usage / missing input.
 #   setup  the md5 of the repo's SKILL.md, the sandbox's workspace copy, the owner's global copy (md5 -q only; "absent" if there is none) and,
-#          for arm m0, the dedicated home's copy ("absent" if none). The rule: the repo file has the required md5; the workspace copy equals
-#          it; the global copy equals the workspace copy or is absent; arm m0: the M0 copy exists exactly when the global copy exists, with
+#          (P1: both arms use the owner's kiro home, so there is no third copy). The rule: the repo file has the required md5; the workspace
+#          copy equals it; the global copy equals the workspace copy or is absent; the same rule in both arms, with
 #          the same md5. Anything else: "verdict: INVALID (H2)".
 #   turn1  the setup block, then skill_check.py's report (first disclose_context of the skill: call number, turn, UTC, uri, md5 of the
 #          SKILL.md at that path, which must be the required md5; the stratum of E7 protocol 4.4.1; the "Note: the installed skill at" counts).
 # The global file is never modified, moved or deleted, and no other file under ~/.kiro/skills is read.
 REPO=/Volumes/workspace/hirearchy
-ST=$REPO/studies/G0-noise-baseline
+ST=$REPO/studies/P1-itemized-playbook
 EV=$ST/evidence
 H=$EV/harness
-REQUIRED=a3e46347b70a7ece5f734f70198c607f   # skills/hirearchy/SKILL.md at 3c841bb9, 125 lines
+REQUIRED=b10238639f48ab351fa44a06aed03ffb   # skills/hirearchy/SKILL.md at 8bf7c69b, 125 lines
 
 LABEL="$1"; MODE="$2"
-[[ "$LABEL" =~ '^(m0|m1)-s[1-9][0-9]*(r[0-9]*)?$' && ( "$MODE" == setup || "$MODE" == turn1 ) && $# -eq 2 ]] || { echo "usage: skill_check.sh <label> setup|turn1" >&2; exit 2; }
-ARM=${LABEL%%-*}
+[[ "$LABEL" =~ '^[FI][1-3](r[0-9]*)?$' && ( "$MODE" == setup || "$MODE" == turn1 ) && $# -eq 2 ]] || { echo "usage: skill_check.sh <label> setup|turn1" >&2; exit 2; }
+ARM=${LABEL[1,1]}
 STREAM=$EV/$LABEL
 [[ -f "$STREAM/sandbox-path.txt" ]] || { echo "skill_check.sh: $STREAM/sandbox-path.txt is missing" >&2; exit 2; }
 S=$(cat "$STREAM/sandbox-path.txt")
 REPO_SKILL=$REPO/skills/hirearchy/SKILL.md
 WS_SKILL=$S/.kiro/skills/hirearchy/SKILL.md
 GLOBAL_SKILL=$HOME/.kiro/skills/hirearchy/SKILL.md
-M0_SKILL=""
-if [[ "$ARM" == m0 ]]; then
-  [[ -f "$STREAM/m0-home-path.txt" ]] || { echo "skill_check.sh: $STREAM/m0-home-path.txt is missing" >&2; exit 2; }
-  M0_SKILL=$(cat "$STREAM/m0-home-path.txt")/.kiro/skills/hirearchy/SKILL.md
-fi
 
 md5_of() { [[ -f "$1" ]] && md5 -q "$1" || echo ""; }
 lines_of() { wc -l < "$1" | tr -d ' '; }
 repo_md5=$(md5_of "$REPO_SKILL"); ws_md5=$(md5_of "$WS_SKILL"); global_md5=$(md5_of "$GLOBAL_SKILL")
-m0_md5=""; [[ -n "$M0_SKILL" ]] && m0_md5=$(md5_of "$M0_SKILL")
 
 reasons=()
 [[ "$repo_md5" == "$REQUIRED" ]] || reasons+=("the repo SKILL.md md5 is '${repo_md5:-absent}', not the required $REQUIRED")
 [[ -n "$ws_md5" && "$ws_md5" == "$repo_md5" ]] || reasons+=("the workspace copy md5 is '${ws_md5:-absent}', not the repo's")
 if [[ -n "$global_md5" && "$global_md5" != "$ws_md5" ]]; then reasons+=("the global copy md5 $global_md5 differs from the workspace copy's"); fi
-if [[ "$ARM" == m0 ]]; then
-  if [[ -n "$global_md5" && -z "$m0_md5" ]]; then reasons+=("the global copy exists but M0's home has none")
-  elif [[ -z "$global_md5" && -n "$m0_md5" ]]; then reasons+=("the global copy is absent but M0's home has one")
-  elif [[ -n "$global_md5" && "$m0_md5" != "$global_md5" ]]; then reasons+=("M0's copy md5 $m0_md5 differs from the global copy's $global_md5"); fi
-fi
 
 TURN1_TEXT=""; TURN1_RC=0
 if [[ "$MODE" == turn1 ]]; then
@@ -58,13 +47,8 @@
   echo "repo skill:      ${repo_md5:-absent}  lines $( [[ -f "$REPO_SKILL" ]] && lines_of "$REPO_SKILL" || echo 0)  ($REPO_SKILL)"
   echo "workspace copy:  ${ws_md5:-absent}  lines $( [[ -f "$WS_SKILL" ]] && lines_of "$WS_SKILL" || echo 0)  ($WS_SKILL)"
   echo "global (md5 only): ${global_md5:-absent}"
-  if [[ "$ARM" == m0 ]]; then
-    echo "M0 copy:         ${m0_md5:-absent}  lines $( [[ -f "$M0_SKILL" ]] && lines_of "$M0_SKILL" || echo 0)  ($M0_SKILL)"
-  else
-    echo "M0 copy:         n/a (arm m1)"
-  fi
   echo "required: $REQUIRED"
-  echo "rule: the workspace copy = the repo file = required; the global copy = the workspace copy or absent; arm m0: M0's copy exists exactly when the global copy exists, same md5"
+  echo "rule: the workspace copy = the repo file = required; the global copy = the workspace copy or absent; the same in both arms (one kiro home)"
   if [[ "$MODE" == turn1 ]]; then
     echo
     print -r -- "$TURN1_TEXT"
```

(aggregate.py and selfcheck.sh are rewritten: their G0 versions are not P1's; see the files.)

## Amendment H-A1 (probe.sh; the manager's ruling `manager-decision-probe-define.md`, 2026-10-27; made by the preflight step before F1's first turn)
**What.** `probe.sh`'s first definition of the probe service (the `define-service lead probe-memo ...` call, lines 42-43) omitted `--deliverable`, which the product requires
for a first definition. Preflight attempt 1 (`probe-attempt-1/`) ended `PROBE: STOP` because of it (no service existed in any probe org, so the positive control and the lock checks
could not run). The fix adds `--deliverable 'A memo of at most 400 words in the reply'` to that call and changes nothing else in `probe.sh` (the arm-F lock line, `ORG_ROOT=$P/org uv
--directory $REPO run hirearchy define-service lead probe-memo --locked`, is byte for byte as it was; it has the form of `after_turn.sh` line 140). `--path` is not required: the call, with
`--deliverable` and the other flags as before, was run once on a throwaway org (`/tmp/hirearchy-p1-hA1check-*`, deleted; record in `preflight/deletions.txt`): `define-service` exit 0 (contract v1), then the
`--locked` line exit 0 (contract v2, `locked: true`, the owner's quiet note `locked: false -> true (you may no longer revise the playbook)` in `lead/inbox`).
The values come from attempt 1's refusal text (`a first definition of `probe-memo` needs deliverable`) and `hirearchy define-service --help` (`--deliverable DELIVERABLE`, `--path PATH` = an absolute folder for the deliverable, optional).

**Whole-harness check of every product CLI call** (read-only; each call's subcommand and flags against `hirearchy <subcommand> --help`, 2026-10-27; the harness files that call the CLI are the ones below):
| File:line | Call | Result |
|---|---|---|
| `probe.sh:40` | `hirearchy init <path>` | OK (`init [--mission] [--model] [path]`) |
| `probe.sh:41` | `hirearchy --root <org> hire root lead --role ... --charter ...` | OK (`hire --role --charter parent name`; `--root` is the top-level option) |
| `probe.sh:42-43` | `hirearchy --root <org> define-service lead probe-memo --description --input --acceptance --deliverable --budget` | OK after this amendment (before it: MISMATCH, missing the required `--deliverable`) |
| `probe.sh:48` | `ORG_ROOT=<org> uv --directory <repo> run hirearchy define-service lead probe-memo --locked` | OK (`--locked`; on an existing service only what changes is passed; run on the throwaway org: exit 0) |
| `after_turn.sh:134,140` | `ORG_ROOT=<S>/org uv --directory <repo> run hirearchy define-service <lead> <service> --locked` | OK (same form as `probe.sh:48`) |
| `finish_stream.sh:71` | `hirearchy --root <S>/org check` | OK (`check [--json]`) |
| `quality_snapshot.sh:30` | `hirearchy --root <S>/org quality --json` | OK (`quality [--json] [service]`) |
| `services_snapshot.sh:25` | `hirearchy --root <S>/org services` | OK (`services`) |
| `copy_org_evidence.sh:49` | `hirearchy --root <org> services` / `progress` / `status` / `health` | OK (each takes no required argument; `progress [--wait] [task_id]`, `health [--agent] [--json]`) |
| `copy_org_evidence.sh:52` | `hirearchy --root <org> obs trace <task id>` | OK (`obs trace [--json] task_id`) |
| `inject_root_rework.py:128`, `profile-template.json` | `uv --directory <repo> run hirearchy mcp` (MCP server) | OK (`mcp`; exercised by the preflight's self-test, poll check and probe sessions) |
No other product CLI call exists in the harness (`grep -nE 'HIR\b|run hirearchy|hirearchy --root|obs (trace|events)' harness/*`; the python modules call `git`, `ps` and `ls`, and the injection script and the scheduler stop use the MCP server and `Org(...)` API). No other MISMATCH.

**Re-freeze.** `probe.sh` md5 `6e18b2826cb9bb942c63c5cce36c3f58` -> `6e18b2826cb9bb942c63c5cce36c3f58`. `CHANGES.md` and `MD5SUMS` change with it. `protocol.md` is unchanged (md5 `70237b0f3a829795a89d81c8eba7a7d6`, `protocol.md5` unchanged). The amendment is recorded in `protocol-amendment-1.md` (+ `.md5`), as protocol section 0 prescribes.

**Lesson (the manager's, for the backlog).** `probe_check.py` tested the comparison on constructed sessions and never the probe's own product calls; a harness self-check must dry-run every product CLI call the harness makes against a throwaway org before the freeze.
