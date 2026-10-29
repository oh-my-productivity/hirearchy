# P2 harness self-check (protocol 13.3; step 1a, iteration 3)

Command: `env -u KIRO_HOME zsh evidence/harness/selfcheck.sh` (2026-10-29T08:36:57Z, before any freeze, after every harness code change of
iteration 3; `../prereg-revision-3.md`). Summary: `selfcheck-summary.txt`.
**Result: `SELFCHECK: 18 of 18 parts passed`.** (Iteration 3's first full run read 17 of 18: the arm-R dry run's PF-0 expectation;
see "Iteration 3" below. The harness's `__pycache__/`, written by the product interpreter's imports during the dry run, was removed after
the run; it is no harness file.) Every throwaway org lived under `/tmp/hirearchy-p2/`; no profile was created in
`~/.kiro/agents`; the owner's global skill was never moved (the skill-move cases ran on a constructed home under
`/tmp/hirearchy-p2/selfcheck-home`, one of them with its aside copy in the study folder to exercise the cross-volume move); after the run
`~/.kiro/skills/hirearchy/SKILL.md` is in place with md5 `443e1bc4911aa4d6aaa6457e78f673c1`. No live chat and no org-agent run ran (the
wrapper part used a fake chat under a `selfcheck-*` label; the throwaway orgs were driven through the `Org` facade, the CLI and, for F7
and the label coverage, one MCP tool call at a time through `mcp_call.py`).

## The parts (protocol 13.3's list, line for line)
| # | Part | Result | File |
|---|---|---|---|
| 1 | `skill_proof.py`: constructed sessions against each arm, and P1's kept I2 session (P1's skill = arm C's: PROVED for C, NOT PROVED for R) | 8 of 8 | `skill_proof.out` |
| 2 | `effort_stops.py`, `running_credits.py` (the 260.00 line, the unmatched-run estimate) | 1 of 1, 2 of 2 | `effort_stops.out`, `running_credits.out` |
| 3 | `lena_lines.py`: the line form, unread lines, unknown and new rule ids, the TRAP memos, "passed the trap" only for judged memos and `trap_unreached` (F2), "X2 not reached", the CONDITION, the list bounds (F5); iteration 3: L0 as the answer line (F27, 6 cases), the retro places (F28, 3 cases), `verdict_after` (F26) | 20 of 20 | `lena_lines.out` |
| 4 | `score_p2.py`: the trap rule, no trap in memo 1, the A-M order, JD under form N; iteration 3: rejected versions exempt, accepted versions and final memos keep the rule (F26) | 9 of 9 | `score_p2.out` |
| 5 | `aggregate.py`: the exit with the gate-able measures (F1): all PASS with G1(b) VACUOUS; one FAIL; X2 not reached; two valid streams; a gate-able FAIL in arm C; a judged key missing; VACUOUS outside G1(b); no `gate_p1.json`; the PF-0, PF-1 and new counts per stream (12.6 (4)); a bad `before_failure` key | 10 of 10 | `aggregate.out` |
| 6 | `probe_compare.py` on constructed probe folders: PASS when alike; STOP on no sessions, a `session_start` difference, a failed empty-argument call, an unproved skill, two hashes in one arm, a cross-arm load difference the catalogs do not explain, a failed positive control | 8 of 8 | `probe_compare.out` |
| 7 | `stage_gate.py` on constructed folders (17.6's four items, F20; item 2 reads the brief's offered items, held-back keys reported beside it); iteration 3: `gate_p1.json` FAIL-CLOSED, a judged NOT DETERMINED, an unread `gate_p1.json` (F36), the answer line as L0 (F27) | 14 of 14 | `stage_gate.out` |
| 8 | `gate_p1.py` on constructed streams (`gate_p1_cases.py`; F4); iteration 3: a presented version Lena rejected, exempt (F26) | 24 of 24 | `gate_p1.out` |
| 9 | `selfcheck_cases.py`: tokens and added words; the shapes; 7.1, 7.2, 7.5; D7; the ledger's rules; the charter-edit count; every D8 label (and the whole-second horizon); the product's parsers; every `extract_p2.py` check, its FAIL paths, cuts and fail-closed readings; D-UNNOMINATED (F3, F5, F6, F12, F13); **12.6: PF-0, PF-1, their near misses (each classified new), the X3 reading both ways and without the signature, P2-E's classes and counts**; iteration 3: F22's runtime notes, F23's near misses and a `Fact Checker` role, F27's residual case, F29's open items (6 cases) | 156 of 156 | `selfcheck_cases.out` |
| 10 | P1's `cost_total.py` and `empty_calls.py` on G0's six streams (unchanged modules) | 13 of 13, 6 of 6 | `cost_total.out`, `empty_calls.out` |
| 11 | `skill_move.sh` on a constructed home: aside, UNRESTORED, a second aside refused, restore with md5, idempotent restore, `recover` (F18), a cross-volume aside and restore into the study folder (F18), a changed aside copy stops the restore, another skill untouched, a foreign `HOME` refused; iteration 3: `ASIDE-PENDING` with and without its `mv` (F33) | 18 of 18 | `skill_move.out` |
| 12 | the arm-C injection differs from E7's file in line 36 only (E7's md5 `1c4e7824...` kept); the profiles equal with the label, the epoch and the product path masked | ok | `injection_profile.out` |
| 13 | one wrapper per turn with a fake chat, and `turn.sh` refusing another label's unrestored move (exit 92, F17) | 9 of 9 | `wrapper.out` |
| 14 | the probe's own product calls (`probe.sh --setup-only`): four throwaway orgs, both catalogs, `retro` in arm R's only | ok | `probe_setup.out`, `probe-setup/` |
| 15 | **the dry run, arm R** (below) | 57 checks, 0 mismatches | `dryrun-R.out`, `dryrun-R/` |
| 16 | **the dry run, arm C** (below) | 24 checks, 0 mismatches | `dryrun-C.out`, `dryrun-C/` |

## The dry run before the freeze (17.5, F-P1-9, H-A1)
- **Every product CLI call the harness makes, checked against `--help`** (`dryrun-<arm>/help-check.txt`): arm R 27 OK, arm C 25 OK, 0
  MISMATCH (`init --mission`; `quality --json`; `services`; `check`; `progress`; `status`; `health`; `obs trace`; `hire --role --charter`;
  `define-service --description --input --acceptance --deliverable --path --budget`; `task --title --goal --acceptance --budget`; `run
  --until-done --max-runs`; `plan --allow-root`; `apply --allow-root`; `--root`; arm R also `retro --since --json`).
- **The throwaway orgs** (`dryrun_build.py`, P1-sized reworks; each rework 3 runs): a memo service owned by a lead with a writer and no
  reviewer (arm R: a full blueprint with sourced criteria and `needs.elicitation`, A-W's widened criterion among them; arm C: string
  criteria); memo 1 rejected by H6 and answered with a new criterion; the relayed rework of memo 1 (A-R); memos 2-4 each failing the trap
  (the first answered with a new criterion, the next two by "same as" links); three judged one-off action lists of one shape. Arm R then:
  B1 recorded, both items applied at the terminal, memo 5, a request of the new service, a hand edit of the writer's charter; B2.
- **Arm R, `hirearchy retro --json` on P1-sized reworks** (on the scratch copy, as the per-turn snapshot runs it; the stream ledger was
  unchanged): items `service`, `checker-add` and `clarify`; the `checker-add` question ends `It costs about 2 more runs per request; about
  2.0 more runs per request than the rework it saves.` and its Details note reads `net -2.0 = 0.8 × 3 − 2 − 0.8 × 3, from 3 of 4 cases`:
  design 17.3's numbers (c = 2, f = 3, r = 3, p = 3 of 4, net −2.0), p at one decimal. A second `retro` showed B1 again. Both extension
  files `plan` and `apply`; B2's D13 shows both items `taken`.
- **F7: the TRAP-N question forms, through root's MCP `feedback`** (scratch copies of the org after memos 1-4; memo 5 delivered and
  rejected with TRAP-N's line `Not right yet, the same problem as before: Lee's due should be 2026-11-04.`; `dryrun-R/f7-{a,b,c}.json`):
  - (a) without `criterion`, the product replies `ask the user exactly ONE yes/no question that names the criterion you read the
    rejection as: "About <its id>: add ...? Yes or no.", with <its id> one of C1, ..., C6; for a repeat: "Same as R<j>: a one-off? Yes or
    no."`: root may name any id. Answered by K29 (`Yes.` to "Same as R2"): the link names R2;
  - (b) with `criterion=["C6"]` ([trap-crit]): `ask ... in these words: "About C6: add ...? Yes or no."`. Answered by K30 (`Yes, add it.`):
    an answering version `about C6`;
  - (c) with `criterion=["C2"]` (outside the class): `"About C2: add ...? Yes or no."`. Answered by K30c (`No: it is the same as R2.`):
    the no-branch link names C6;
  in each form the re-derivation's firing class holds [trap-crit] and four cases, memo 5's among them.
- **Label coverage for P2-E** (scratch copy of form a; `dryrun-R/labels-compare.txt`): a parent's MCP `write` of its report's charter,
  committed as the reaper commits (`by lead`); two terminal hires (`by root, outside a plan`); an extension that retires one of them
  (`from your change 44cd...`); a service defined and retired at the terminal (`by root, outside a plan`). Every product D8 line of
  `retro --since ... --json` equals the re-derivation's; the re-derivation's only extra lines are the creations of the retired agent and
  the retired service (PF-1 below).
- **12.6's classifier on the product's own output** (the manager's decision): over the label-coverage org (`dryrun-R/labels-classify.txt`)
  it reads `PF-0 0 PF-1 2 new 0` (the creations of `ops-helper` and `lead/extra-svc`, both retired in the window, missing from D8, their
  retire lines present); over a terminal-only org (`dryrun_build.py --phase pf0`: `init` and `apply` at the terminal, no MCP call, the first
  versions committed, then a hand edit of `lead/writer/AGENT.md` committed; `dryrun-R/pf0-lookback.json`, `pf0-d8.txt`,
  `pf0-classify.txt`) the product's `- charter of lead/writer changed: body (2026-10-29): by lead, or outside the tools (the event log does
  not reach back)` against the re-derivation's `outside the tools` reads `PF-0 1 PF-1 0 new 0`: PF-0 reproduced on the arm-R product.
- **Every reader over the output:** the snapshot scripts, `copy_org_evidence.sh`, the facts as the session would give them (constructed
  from the CLI replies, the same render, with Lena's lines in the build's event order), `rederive_p2.py`, `extract_p2.py --checks`,
  P1's `rederive_watch.py` per service, `score_p2.py`, `gate_p1.py`. On arm R's org: **P2-X1 PASS, P2-X2 PASS, P2-L PASS, P2-B PASS,
  P2-W(0)-(c) PASS, P2-E PASS (B1 and B2), P2-S PASS**, and **P2-X3 FAIL as constructed** (the hand edit: harness 1, product 1, one
  `outside the tools` label). The gate-able measures the construction determines: G1(a), G1(c), G1(e), G2(a), G2(b), escapes typed, relayed
  reworks (the build's relayed rework excepted by its injection record) PASS; G1(b) VACUOUS. Those that fail closed by construction (no
  session store, no snapshot per constructed turn, no `judged.json`): hand edits, empty calls, G1(d), G1(f), delivered versions, deliveries
  by copy. Arm C: the harness counts the same hand edit (1); its readers run and read the same.
- The injection's arm form: `--dry-run` and `--selftest` exit 0 in both arms.

## Mismatches found, and what each was
1. **Harness bugs, fixed** (each in `harness/CHANGES.md`, "Iteration 2"): a link note's rejection is in `reply_to`, not `confirms` (G2(b)
   and the ledger's effect test read the wrong key); the hand-write reader took `2>/dev/null` for a write; `probe_compare.py` gave every
   tool of one load the same hash; `dryrun.sh` did not export `H0` (its constructed facts failed, so X1 and X2 read FAIL on the dry run);
   `dryrun.sh` reused its folder (two orgs' messages mixed, P2-S read the wrong repeats); zero scored versions read FAIL instead of failing
   closed. Two constructed expectations were corrected for their own construction (a 7.5 case built words with digits, which the token
   rule splits, `w0` into `w` and `0`; a D8 case whose reworded line kept its tag: reading 11), each recorded in `selfcheck_cases.py`.
2. **Iteration 1's fixes stand** (iteration 1's list in `harness/CHANGES.md`).
3. **Product findings** (against the design's text; recorded here, never "fixed" in the harness; the warning is sent at the end of step 1a):
   - **PF-0 (LOW; iteration 1's item 3, F15 of the review).** Files: iteration 1's first arm-R build (the blueprint applied at the terminal
     before any MCP call), its B2 D8 line for `lead/writer/AGENT.md`. The product labelled a hand edit `by lead, or outside the tools (the
     event log does not reach back)` while events were on and `cli.command` events covered the window; design 4.5 gives that label for "a
     nested charter's change whose window is beyond the event log's horizon, or with events off", and `outside the tools (a hand edit or
     the terminal)` "while the event log covers the window". The product reads the horizon from MCP-path events. Iteration 1's dry run
     then made one read-only MCP call (`whoami`) first, so the case no longer arises there; that changed the dry run's input, not the
     harness, and the harness keeps the design's label. In a stream root's MCP calls precede every change, and both labels count as an
     unprompted charter edit, so no pass rule depends on it. Iteration 1 sent no warning for it; this iteration records it as a product
     finding for step 12 and includes it in the warning.
   - **PF-1 (LOW).** Files: `dryrun-R/labels-lookback.json`, `dryrun-R/labels-compare.txt`, the scratch org under the dry run's sandbox
     (`f7-a/org/.retired/ops-helper-*/`, `f7-a/org/lead/services/.retired/extra-svc-*/`). The product's D8 lists `agent ops-helper retired`
     and `service lead/extra-svc retired` but not their creations in the same window (`agent ops-helper added`, `service lead/extra-svc
     added`), while the live agent hired in the same way (`ops-keeper`) is listed. Design 4.3 D8 lists "every structural change since
     `since`" and 4.5's `taken back` row says "the creation it takes back carries the same label", so the creation of an agent retired
     later is listed. P2-E reports a MISMATCH in any stream where an agent or a service is created and retired within one brief's window;
     no pass rule depends on it. The harness keeps the design's reading (protocol 13.2 reading 13).

4. **Found while writing 12.6's PF-0 test (a harness bug, fixed):** the re-derivation compared the event log's horizon (microseconds)
   with a commit time (whole seconds), so a log whose first record falls in the same second as the older commit read as not covering the
   window, and the harness gave the horizon label itself on the terminal-only org. Both the D8 label and PF-0's signature now compare at
   whole seconds (protocol 13.2 reading 1), with a constructed case.

## The manager's decision on PF-0 and PF-1 (`../manager-decision-prereg-pf.md`)
Both carried to step 12 as product findings, neither fixed in the harness. Protocol 12.6 pre-registers, for each, every rule and check
that reads the affected output and whether it can change its verdict in this script (no pass rule can; P2-E can show PF-1, and PF-0 cannot
arise in a stream because every `AGENT.md` version follows root's first `propose_org`), the X3 reading (the re-derivation's count decides;
a PF-0 label on an uncounted change is reported under P2-E, on a counted one X3 fails), the signatures as mechanical tests over named
files, and the counts per stream (`p2/P2-E.json` `counts`, `aggregate.md`).

## Design-silence notes (carried to step 12)
- **Reading 8** (protocol 13.2): one checker candidate per evidence set, named by its newest current criterion. Adopted in iteration 1
  after the dry run showed the product offering one candidate where the harness first offered two (`harness/CHANGES.md` iteration 1 fix
  2). The design gives one candidate per class that fires and does not say how two classes with one evidence set are offered.
- **Reading 11**: a reworded added-section line that keeps an applied tag reads `from your change` by 4.5's content test read literally;
  CHARTER-ADDED refuses such a rewrite through the tools.

## Iteration 3 (`../prereg-revision-3.md`)
- **New checks in the dry run:** F31 in each arm (the finish's `extract_mechanical.py` argv names `--product-src REPO_A/src`, never the
  other product's; `client_questions` resolves to the arm's product file; in arm C `REPO_A` is the worktree); the constructed L0 answer
  line (F27). On arm R's org every pass rule reads as before (X1, X2, L, B, W(0)-(c), E, S PASS; X3 FAIL as constructed); P2-L now lists
  every waking runtime note to root (F22) and still passes.
- **A test bug the first run found, fixed (harness side).** The first full run read 17 of 18: over the terminal-only org the product gave
  the design's `outside the tools (a hand edit or the terminal)` and the classifier read `PF-0 0`, where iteration 2's run reproduced PF-0.
  Six further throwaway builds (`/tmp/hirearchy-p2/pf0-probe-1..6`, deleted afterwards) gave, for the writer's charter pair:

  | Try | The log's earliest record (CLI only) | The older commit `t1` | The product's label |
  |---|---|---|---|
  | 1 | 08:33:55.896817 | 08:33:56 | `outside the tools (a hand edit or the terminal)` |
  | 2 | 08:33:58.380824 | 08:33:58 | `by lead, or outside the tools (the event log does not reach back)` |
  | 3 | 08:34:00.857254 | 08:34:01 | `outside the tools ...` |
  | 4 | 08:34:03.317709 | 08:34:03 | `by lead, or outside the tools (...)` |
  | 5 | 08:34:05.787404 | 08:34:06 | `outside the tools ...` |
  | 6 | 08:34:08.226757 | 08:34:08 | `by lead, or outside the tools (...)` |

  The dry run's expectation assumed the product reproduces PF-0 on every build: a harness test bug. `dryrun.sh` now builds until both
  timings exist (at most 8), records each try in `dryrun-R/pf0-timing.txt`, and checks each: same second -> the horizon label, classified
  `PF-0 1 PF-1 0 new 0`; an earlier second -> the design's label, `PF-0 0 PF-1 0 new 0`. The final run's two tries are in that file.
- **PF-0's mechanism, corrected (product side; recorded, not fixed).** The product gives the horizon label exactly when the event log's
  earliest record falls in the same whole second as the pair's older commit and after it in microseconds, CLI records included. That is the
  comparison the harness itself got wrong in iteration 2 (item 4 above, fixed by protocol 13.2 reading 1), not iteration 1's reading "the
  horizon from MCP-path records only". Protocol 12.6 now states the observed mechanism. The pre-registered signature, which the manager
  decided (`../manager-decision-prereg-pf.md`), is unchanged. It matches every PF-0 these builds produce (they hold no MCP-path record).
  In a stream PF-0 cannot arise in either form, because root's MCP calls precede every `AGENT.md` version by more than the commit's second.
  A same-second PF-0 after an MCP-path record would be classified `new` and reported. No pass rule can change. A `warning` was sent with the
  question whether to keep the signature or rewrite its condition (iii). The manager answered: keep it as pre-registered (an addendum to
  `../manager-decision-prereg-pf.md`); the product fix, comparing the horizon at whole seconds, goes on the 2b backlog.

## The manager's closing pass (`../prereg-closing-pass.md`)
- **Result:** `SELFCHECK: 19 of 19 parts passed` (`selfcheck-summary.txt`, run started 2026-10-29T09:51:20Z, after the last harness code
  edit). The new part is 5c, `signal traps stop the drivers (C4)` (`traps.out`). New cases: `lena_lines` 24 of 24 (C2, C3), `score_p2` 13 of
  13 (C1), `gate_p1` 27 of 27 (C1); both dry runs run `score_stream.sh` (C5) with 0 mismatches.
- **A harness bug the C5 check found, fixed:** `score_stream.sh` passed the A-M line's turn number as `--am-time` instead of that turn's
  start time. The dry run's constructed lines hold no A-M line, so arm R also runs `score_stream.sh` on a scratch copy with one added, and
  checks the value (`dryrun-R/score-steps-am.txt`).
- **No product defect** was found. The dry runs' `delivered versions (P2's form)` reads `NOT DETERMINED (FAIL-CLOSED: no delivered version
  was scored (0 of 0))` in both arms, as before this pass (the construction copies no memo version; the old `score_p2.py` and `gate_p1.py`
  give the same line on the new dry-run evidence); it is not among the measures the dry run checks.

## Amendment 1 (`../manager-decision-row-R1-t7.md`; `../protocol-amendment-1.md` item 5; `../harness/CHANGES.md` "Amendment 1")
- **Result:** `SELFCHECK: 20 of 20 parts passed` (`selfcheck-summary.txt`, run started 2026-10-29T11:24:47Z, after the last harness code
  edit). The new part is 5d, `amendment 1: sequence check, effort-stop cost, window.txt` (`amend1.out`, `amend1_cases: 21 of 21 ok`).
  Other counts: `lena_lines` 37 of 37 (13 new) and `selfcheck_cases` 167 of 167 (1 new). Every other part reads as at the freeze. Both
  dry runs have 0 mismatches.
- **RED, on the frozen harness.** The new cases were written first. Their outputs are kept in `amendment-1-red/`:
  - `amend1_cases: 4 of 21 ok`. The four that passed are the ones the fixes do not change: the finish names its extract command, the
    stopped run is matched in `run-session-map.txt`, `extract_mechanical.py`'s md5 is pinned, and `--stop` writes no window.txt.
  - `lena_lines selfcheck: 36 of 37 ok`.
  - (A) `MISMATCH (A) turn.sh: a first snapshot at 2020-01-01T00:00:00.000000+00:00, before the turn's end + boundary: STOP`, which got
    `after_turn sequential: checked (no snapshot taken: no org yet)`. The unparseable-time case and the after-the-boundary case got the
    same vacuous line. The seven direct cases had no `turn_seqcheck.py` to run.
  - (B) `MISMATCH (B) an effort-stopped run's session with no messages.jsonl: the finish's extract exits 0 and writes cost.txt`, which got
    `exit 1; FileNotFoundError: [Errno 2] No such file or directory: '/tmp/hirearchy-p2/selfcheck-amend1/B/stop/org-kiro-sessions/h0/sess_boss-scribe/messages.jsonl'`.
    This is R1 v1's crash on a constructed stream.
  - (C) `MISMATCH (C) injection.sh writes S/injection/window.txt from the log, with no facilitator step: ...`, which got `exit 0;
    window.txt None`.
  - The composition rule: `MISMATCH amendment 1 item 3: ext_no_not_first (KeyError: 'ext_no_not_first')`.
- **GREEN, after the fixes:** `amend1_cases: 21 of 21 ok`, `lena_lines selfcheck: 37 of 37 ok`.
- **Checks on kept evidence (read only, outside the self-check; output under `/tmp/hirearchy-p2/amend1-r1v1-check/`):**
  - `extract_mechanical_p2.py` on R1 v1 counts its one effort stop (`lead@20261029T104930658411 -> sess_f04502e1-...`), and
    `cost_total.py` reads `stream total credits: 26.66 (assistant 15.48 + org runs 11.19)`. This equals `R1/credits-running.txt`'s turn-7
    line.
  - `injection_window.py` on R1 v1's log gives `2026-10-29T10:48:27 2026-10-29T10:50:27`.
  - On P1's F1, F2, F3, I1, I2 and I3 logs it reproduces each kept `window.txt` byte for byte.
  - No file of `EV/R1/` was written: the count of files newer than `end.txt` was 84 before and after.
- **No product defect** was found. The global skill's md5 was `443e1bc4911aa4d6aaa6457e78f673c1` before and after each run.

## Amendment 1, review rulings (`../manager-decision-row-R1-t7.md`, "Amendment 1's review: rulings"; `../harness/CHANGES.md`, same title)
- **Result:** `SELFCHECK: 20 of 20 parts passed` (`selfcheck-summary.txt`, run started 2026-10-29T11:59:11Z, exit 0, after the last harness
  code edit). Part 5d reads `amend1_cases: 28 of 28 ok` (7 new D1 cases); `lena_lines selfcheck: 43 of 43 ok` (6 new);
  `selfcheck_cases: 168 of 168 ok` (1 new, D2). Every other part reads as at the "Amendment 1" run. Both dry runs have 0 mismatches.
- **D1, RED then GREEN.** The cases (`amend1_cases.py` part (D)) call `arm.sh`'s `md5gate_ok` in isolation on a constructed EV copy under
  `/tmp/hirearchy-p2/`; the real amendment `.md5` files were never written.
  - RED, on `arm.sh` as reviewed (kept in `amendment-1-red/rulings-amend1.out`): `amend1_cases: 23 of 28 ok`, with five `MISMATCH` lines,
    each `got: rc 0;`, among them `MISMATCH  (D) D1: protocol-amendment-1.md without its .md5: the gate fails, naming it` and `MISMATCH
    (D) D1: standing-rules-streams-amendment-1.md with a different .md5: the gate fails, naming it`.
  - GREEN, after the fix: `amend1_cases: 28 of 28 ok`.
- **The parser and window cases** (K67, K68, `K65 (either/or of existing agents)`, A1's `K48, K6n (open form)`, and D2's week window)
  passed on first run against unchanged code: they are guards, and no parser or window code was changed. A negative control for the D2
  case (the answer line forced into the bounds) gave `to_turn` 21 and no task.
- **The gate on the real EV is unaffected by the self-check** (it uses `selfcheck-*` labels only), and on the real EV it now fails with
  `md5 gate: protocol-amendment-1.md5 missing (protocol-amendment-1.md not frozen)` and the standing-rules amendment's line until the
  re-freeze, as D1 (f) intends.
- **Safety.** The global skill's md5 was `443e1bc4911aa4d6aaa6457e78f673c1` before the run and after it. No stream, live kiro-cli session or
  live org run was started; `../R1/` was not moved or edited.
