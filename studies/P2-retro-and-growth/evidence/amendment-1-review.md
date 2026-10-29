# Review of P2 protocol amendment 1 (independent claude-opus-5.5 pass, 2026-10-29)

**Verdict: CHANGES_REQUESTED.** Five MEDIUM findings (A1-A5), and no HIGH ones. The harness fixes (A), (B) and (C) are correct and fail
closed, and I reproduced them. The self-check I ran reads `SELFCHECK: 20 of 20 parts passed`. The new rows map R1 v1's turn-7 reply
correctly. Their weak point is what comes next: some realistic follow-up questions at ACT-REQ still stop the stream, and the precedence
leaves some row pairs unresolved. Either can end a stream again, which is how R1 v1 was lost.

`EV` = `studies/P2-retro-and-growth/evidence`, `H` = `EV/harness`, `AM` = `EV/protocol-amendment-1.md`, `SR-A` =
`EV/standing-rules-streams-amendment-1.md`.

## What I ran (all read-only on EV except the self-check's own output and these two files)
- `md5 -q` on every file under H, compared with `H/MD5SUMS`.
  - Changed: `CHANGES.md`, `finish_stream.sh`, `injection.sh`, `lena_lines.py`, `selfcheck.sh`, `selfcheck_cases.py`, `turn.sh`.
  - New: `amend1_cases.py`, `extract_mechanical_p2.py`, `injection_window.py`, `turn_seqcheck.py`.
  - Every other line matches, including `extract_mechanical.py` at `73b27e25bd18ea9ec17ad5e64c7f6d1c`, which equals P1's
    `MD5SUMS` line 12.
  - `protocol.md` is `31bc856c...`, which matches `protocol.md5`. `standing-rules-streams.md` is `909fbb79...`, which matches its `.md5`.
- I diffed the changed files against `/tmp/hirearchy-p2/amend1-orig/`, whose md5s equal the frozen MD5SUMS lines.
- `python3 -B H/amend1_cases.py --scratch /tmp/hirearchy-p2/review-a1/amend1 --product-src <repo>/src` gave `amend1_cases: 21 of 21 ok`.
- `H/turn_seqcheck.py R1 <t>` for turns 1-7 of R1 v1:
  - turns 1-2 read `checked (no snapshot taken: no org yet)`, from calls.txt's own `no org yet` records;
  - turns 3-7 read `checked (turn end ... + 20 s <= first snapshot ...)`, the same times as `EV/R1/seqcheck.txt`;
  - parser probes: `.9+00:00`, `.12345Z`, `-05:00` and no offset parse; `+0000`, a space separator and 7 fraction digits give None,
    which fails closed (Python 3.11.9).
- `extract_mechanical_p2.py R1 - --product-src <repo>/src --out /tmp/hirearchy-p2/review-a1/r1v1-extract`:
  - exit 0;
  - `effort stops ...: 1 (lead@20261029T104930658411 -> sess_f04502e1-...)`;
  - `cost_total.line_of` gives `stream total credits: 26.66 (assistant 15.48 + org runs 11.19)`;
  - `EV/R1` was byte-identical before and after (md5 of every file).
- `injection_window.py` on copies of every earlier study's `injection-log.txt` reproduced all 26 `window.txt` files byte for byte:
  P1 F1-F3 and I1-I3, P1's scoring copy, G0's six, and E4-E7.
  - On R1 v1's sandbox log, the lines give `2026-10-29T10:48:27` and `2026-10-29T10:50:27`.
- `zsh H/selfcheck.sh`, run by me at 2026-10-29T11:43:22Z, exit 0: `SELFCHECK: 20 of 20 parts passed`.
  - Part 5d: `amend1_cases: 21 of 21 ok`; lena_lines: 37 of 37; selfcheck_cases: 167 of 167.
  - Every harness file's mtime (the latest is `CHANGES.md`, 11:24:41) precedes both the author's run (11:24:47Z) and mine.
  - The harness md5s were unchanged after my run.
- Safety, before and after everything above:
  - `~/.kiro/skills/hirearchy/SKILL.md` was `443e1bc4911aa4d6aaa6457e78f673c1` both times;
  - a stat listing (mtime, size, path) of every file under `~/.kiro/skills`, `~/.kiro/agents` and `/Users/aminalizadeh/organization`
    was identical before and after;
  - no file in EV outside `harness-selfcheck/` changed;
  - I did not open `src/hirearchy/`.

## Findings

### A1 (MEDIUM): precedence 1 contradicts K65's either/or clause, and leaves a mixed either/or unanswered as asked
- **Where:** AM:60-62 ("A question that proposes such a change is never K62-K66, however it is worded"), AM:75 (K65: "an either/or
  between an existing agent and anything else" gets `Someone already on the team.`), and SR-A:38-41.
- **Problem:** An either/or with a structural option falls under both rules. Two examples:
  - "Should the memo lead make it, or shall I hire a list writer?"
  - R1 v1's own Q3 in a slightly different wording: "Just this list, or shall I set up a weekly list service?"
  - Precedence 1 says K48 alone: `No, keep the team as it is.` That line does not give the value the either/or asks for, which breaks
    protocol 5's rule and P1's C7 lesson.
  - K65's own text says the opposite: `Someone already on the team.`
  - The facilitator cannot apply both rules mechanically.
- **Resolve:** Replace precedence 1's last sentence with this rule:
  - "A question that proposes such a change is answered by K48, K51 or K52. When the question is an either/or whose other alternative is
    in a K62-K66 class, the line is EXT-NO (or the arm-C row), then that row's open line, recorded `K48, K6n (open form)`. The
    composition rule places EXT-NO first."
  - Delete "and anything else" from K65's either/or clause, or narrow it to "anything that is not a structural change".
  - Add a lena_lines case for `K48, K65 (open form)`.

### A2 (MEDIUM): the service rows are missing from the precedence; K66 collides with K43 and K43a
- **Where:** AM:57 ("K66 applies to any action list"), AM:60-70 (the precedence), and AM:76.
- **Problem:** K66's class covers several things that the service rows also answer:
  - its class includes "its file name or folder", "a budget given as a default" and "how it is checked";
  - K43 answers "what one request produces, where it goes: its deliverable or path" (`One action list per request, in the deliverables
    folder.`);
  - K43a answers a new service's budget, name or inputs (`Yes.` to a proposal);
  - K57 and K60 also overlap.
- **Where the overlap occurs:**
  - arm C, when K51 is said yes to inside an ACT-REQ window;
  - arm R, in retro 1's service item (ITEM-SERVICE, then the deliverable question), because K66 is not window-bound;
  - with D2, the week-list window, where K58 holds.
- The precedence names only K44, K48, K51 and K52 (then K9, K54 and K10-K11), so "where should each list go?" has two rows with different
  lines.
- **Resolve:** Add K42, K43, K43a, K57, K58 and K60 to precedence 1:
  - "While a new service is being defined (from a K42 or K51 yes to its PLAN FOR YOU's apply), K43, K43a, K57 and K60 come before
    K62-K66";
  - "K58 comes before K64 and K65".
  - Mirror this in SR-A D.

### A3 (MEDIUM): two foreseeable follow-ups to EXT-NO are left on purpose to stop-and-quote
- **Where:** AM:87-93 ("Outside the classes, on purpose": a request of an existing service, and the assistant writing the list itself),
  and SR-A:45-48.
- **Problem:** In R1 v1 the assistant thought the list needed a team change. Under amendment 1, Lena answers that with
  `No, keep the team as it is.`, so the next reply has to find another route. Two routes are natural, and both stop:
  - "Shall I send it to the weekly-memo service as a request? It already takes a notes file."
  - "Then shall I write it myself from the notes?"
- A stop leads to ruling (b), because a ruling (a) cannot claim a row that the amendment explicitly excludes. The stream then ends,
  costing about 125-200 credits, as R1 v1 did.
- The author's reason, "each would be new wording of hers", does not hold for the second route. Protocol 5's generic yes/no rule already
  gives `No, someone already on the team.` from K65's open line, with no new words.
- **Resolve:**
  - (i) Bring a yes/no proposal that the assistant (root) make or write the list itself into K65: `No, someone already on the team.`,
    recorded `K65 (yes/no form)`.
  - (ii) For a proposal to make it as a request of an existing service, the manager rules on one line of existing words. My suggestion
    is `No, just this list, by someone already on the team.` (K64's and K65's words). Its reason: the script needs a one-off (protocol
    4.5; P2-X1 step 1 reads a service request in the window as FAIL-CLOSED).
  - (iii) An either/or between two existing agents ("the lead or the writer?") gets `Someone already on the team.`, which does not pick
    one. Either accept that explicitly, or answer `That's up to the team.` (K37's words). Record which.

### A4 (MEDIUM): "who is the ops team?" has no line that answers it as asked, and its yes/no form stops
- **Where:** AM:73 (K63's class: "including a request for the names or a rule that defines the part").
- **Problem:** No notes file says "ops". Each is headed "Platform team weekly". ACT-REQ, though, says "for the ops team". R1 v1's Q2
  already asked for "the ops team's names".
- An open "Which team is ops?" maps to K63 only through the "names" clause. `Every action item in those notes.` does not name a team, so
  the assistant may ask again.
- The yes/no form "Is the ops team the Platform team in the notes?" fits neither of K63's propositions (every action, or a part). It
  stops.
- **Resolve:** Add to K63's class "who the ops team is, or whether it is the team in the notes". The open form stays
  `Every action item in those notes.`. The yes/no form is:
  - `Yes, every action item in those notes.` when the proposition is that it is the notes' team, or that no filter applies;
  - `No, every action item in those notes.` otherwise.
- This uses no new words, and every reading names the whole list.

### A5 (MEDIUM): in arm C, K51's "repeated action list" is not mechanical inside the ACT-REQ windows where the precedence now sends service proposals
- **Where:** AM:61-62 (precedence 1 sends arm-C service proposals to K51), AM:74 (K64 yields to it), and protocol.md:530 (K51: "a
  proposal to make the repeated action list a standing service").
- **Problem:** Before amendment 1, "Should I set this up as a recurring service?" at an ACT-REQ stopped the stream. Now it is routed, and
  in arm C the facilitator must choose between two lines:
  - K51 `Yes, make it a service.`
  - K48 `No, keep the team as it is.`
- The choice turns on whether the list is "repeated" at ACT-REQ@2026-10-05 (no list yet), @10-12 or @10-19. The table does not say.
- A yes at ACT-REQ 1 or 2 would also make the later lists service requests. Arm C's fourth one-off would be gone, and so would the count
  of one-offs it is compared on.
- **Resolve:** State a mechanical test, for example "repeated = at least one earlier ACT-REQ list has a LIST-KEEP line". Then:
  - at ACT-REQ@10-05 the proposal is K48;
  - from ACT-REQ@10-12 on it is K51.
  - Alternatively, use the manager's choice of threshold.
- Name the consequence for the arm-C one-off count in the amendment, so the pairing argument (protocol 16 item 11) stays explicit.

### A6 (LOW): R1 v1's reply showed that the assistant sees the harness's CLI calls, and a follow-up question has no row
- **Where:** AM:127 ("not a question; no row is needed").
- **Problem:** That reading is correct for turn 7. But "Did you run those `root run/quality/services` commands?" is a plausible next
  question in either arm, because both arms take CLI snapshots. K10 (L-INJ) covers only the injected rework.
- **Resolve:** The manager either records the stop risk as accepted, or rules a line now (for example L-INJ's first clause, `I don't
  know anything about that.`). This is outside decision items 1-6, so I leave it to the manager.

### A7 (LOW): item numbering and scope labels do not match the decision
- **Where:** AM:10-11, 120, 148, 245, 256, and the comments in H/turn.sh, injection.sh, finish_stream.sh and lena_lines.py that cite
  "item 5 (A)" and "items 2-4".
- **Problem:** The amendment's numbers drift from the decision's:
  - its "Item 4" (the mapping check) is part of the decision's item 2;
  - its "Item 5" (harness) is the decision's item 4;
  - the decision's item 5 (records) has no section;
  - its "Item 7" (section 9) exists in no decision.
- The decision's item 4 names only the turn.sh fix. Fixes (B) and (C) go beyond items 1-6 as written. They are sound, and this review's
  brief expects them, but the record should show who ratified them.
- AM:245 says standing rules 1, 4 and 6 are touched. SR-A also adds new rules A, E, F and G.
- **Resolve:**
  - Renumber the headings to the decision's items, or add a mapping line.
  - Add to section 1: "(B) and (C) are harness fixes the manager ratified in <file>; they change no measure."
  - Correct AM:245 to list A-G.

### A8 (LOW): the re-freeze list omits two items of decision item 5, and a precondition of the restart
- **Where:** AM:262-269.
- **Problem:**
  - The decision asks that `standing-rules-streams.md5` be written "with a check that preflight's written copy equals the frozen value"
    (see `preflight/freeze-gap-standing-rules-md5.md`). Section 9 does not list it.
  - Section 9 does not say that `EV/R1/` must move to `EV/R1-v1/` before the restarted R1's setup. `setup_stream.sh:31` refuses, with
    "REFUSED: ... was set up already", while `EV/R1/sandbox-path.txt` exists.
- **Resolve:** Add both to section 9's list, together with D1's gate change below.

### A9 (LOW): numbering applies only in lines that hold K48
- **Where:** AM:104-106 (rules 3-4 of the composition rule).
- **Problem:** The same six numbered questions get numbered answers when the reply also announces a team change. Without the
  announcement they get unnumbered answers (protocol 4.4 part 2 numbers only a brief's items). That is a small difference in stimulus
  between replies, and so between arms.
- **Resolve:** State whether rules 3-4 also apply to any line that answers a numbered list of two or more questions. I recommend yes:
  it changes no line's text.

### A10 (LOW): the record forms are inconsistent
- **Where:** AM:78, SR-A:21, AM:143.
- **Problem:** K62's, K63's, K64's and K66's open lines are recorded as bare `K6n` (the composed record uses `K62`, `K63`, `K64`,
  `K66`), but K65's open line is recorded `K65 (open form)`. The parser accepts both forms, so nothing breaks, but the record is
  ambiguous.
- **Resolve:** One sentence: "the open or either/or line is recorded `K6n`; K65's, whose row has no bare line, `K65 (open form)`."

### A11 (LOW): K66's "rules" part ratifies whatever rule the assistant proposes, even one against the key
- **Where:** AM:76 ("the rules it follows ... what counts as an action, how owners and dates are written"; the yes/no form follows the
  assistant's default).
- **Problem:** The decision binds "rules like the memo's" to K3's sentence. For R1 v1's Q5 ("same rules as the memo", default yes) that
  is consistent with the key. A default against the key, such as "only `ACTION:` lines count", would get
  `Yes, the rest of your defaults are fine ...`. That is Lena's consent to a criterion narrower than her own H2 words (L-INF, K1), and
  root may copy it into the one-off. The one-off's criteria then reach the extracted service as `from_tasks` copies (P2-W(0)).
  LIST-KEEP keeps every list, so no verdict changes.
- **Resolve:** Limit K66's "rules" to "the memo's rules, or a default that restates them". A rule default that differs from the key on
  what counts as an action takes K54's content rows (K14b, or K1's line `Yes, if someone said they'd do something, it counts.`).

### A12 (LOW, reported only): answers given only at the first ACT-REQ can split the one-off shape
- **Where:** AM:83-86.
- **Problem:** Some lines are long, notably K62's and K63's. If root copies them into the first one-off's criteria, and the second and
  third ACT-REQs raise no such question, then the shape relations differ:
  - the criteria key (ii) differs;
  - the Jaccard index (iii) can fall below 0.6 (design section 3; the digit-bearing `<date>.md` is dropped, so the date itself is
    harmless);
  - only the title relation (i) would remain to join the cases.
- This is T12's known risk (design L5), and P2-S reports it. Any answer at ACT-REQ 1 carries it, so it is no reason to change a line.
- **Resolve:** Add one sentence to AM section 4 noting the risk, so step 12 reads a `DIFFERENT` T12 with it in mind.

## Check-by-check
1. **Decision items 1-6.**
   - Item 1 (the ACT-REQ text) is exact (AM:30-31), with the deviation declared.
   - Item 2's rows hold every line the decision gives, verbatim. K66 uses K3's sentence. The mapping check is done.
   - Item 3: the composition rule is as decided.
   - Item 4: the turn.sh fix is done, and `EV/R1/seqcheck.txt` is recorded (I reproduced it).
   - Item 5: partly pending the re-freeze. A8 lists the gaps.
   - Item 6: I found no change to a measure, reading, validity rule, aggregation, cost figure or pass rule.
     - `cost_total.py`'s patterns (`^total assistant credits:`, `per-model credits (all runs):`, `runs without a matched session: N`,
       `^\s*total runs`) do not match the appended line.
     - So `credits.txt` is unchanged for any stream without effort stops (the line then reads `0 (none)`), and for R1 v1 it is 26.66.
   - Fixes (B) and (C) go beyond the decision's item 4 (A7).
   - AM section 8's table agrees with the files.
2. **K62-K66.**
   - Each class test is literal, but the precedence has gaps (A1, A2, A5).
   - Every line answers as asked, except "who is ops" (A4) and an either/or between two existing agents (A3 iii).
   - On criterion content:
     - `Every action item in those notes.` restates ACT-REQ's "Each action". Copied into a task, it says what the key already says, and
       it permits nothing the key forbids. That differs from A-W, whose words allowed any notes wording in the Owner column.
     - `Only <date>.md, ...: one list.` repeats the file ACT-REQ now names and ACT-REQ's "a one-page action list".
     - Neither line widens a criterion. The only ratification risk is K66's "rules" part (A11).
   - There is no collision with an id: the K62-K69 search came back empty in the original harness, `protocol.md` and the standing rules.
     I read protocol section 5 in full. The overlaps in meaning are with K43, K43a, K57, K58 and K60 (A2) and with K51 (A5). K32 against
     K66 on list layout was already open in v1 through K54, and K54's form clause decides it.
3. **The mapping check.**
   - Each of the six questions maps as AM's table says, and the announced change maps to K48.
   - The composed line follows protocol 4.4: no part 1 in this line; part 2 opens with EXT-NO, then L-INJ, which the reply raised before
     its list, then 1-6; part 7 is `I'll wait.`.
   - The CLI-commands sentence is correctly left without a row (but see A6).
   - The variants are in the table below.
4. **Pairing.** The rows and the composition rule are written for both arms. They differ only through K48/K51/K52, which is the products'
   difference (protocol 16 item 11), but K51's undefined "repeated" makes the arm-C reading non-mechanical (A5). A9 is a small
   asymmetry in numbering.
5. **(A) `turn_seqcheck.py`.**
   - It is correct and fails closed on: a missing turn-times line, an unparseable time on either side, a missing `calls.txt`, and a
     turn without any record.
   - It reads `no org yet` only from that exact record.
   - The line forms are unchanged.
   - `turn.sh` calls it where the inline heredoc was, with `|| echo "STOP: ..."` for a crash. `tail -1` then shows the STOP line.
   - Its cases pass: 10 of 10 (A) cases in `amend1_cases`.
6. **(B) `extract_mechanical_p2.py`.**
   - The pin holds: `73b27e25...`, equal to P1's MD5SUMS line 12.
   - `em.open = _open` binds a global in that module only. Its `open(...)` calls resolve the module global first, and every call except
     a missing `messages.jsonl` beside a `session.json` goes to `builtins.open`. The binding is removed in `finally`.
   - Other modules, including the imported product `client_questions`, and every `Path.read_text` are unaffected. Writes still use the
     builtin.
   - Matching is exact. Each recorded folder must map to exactly one run in `run-session-map.txt`, and that run's log must have a line
     starting `# kiro: effort not set`.
   - An unmatched folder, including a session without a run, fails closed: it renames `cost.txt` to `cost.txt.unverified`, writes a
     `FAIL-CLOSED:` line, and exits 1.
   - R1 v1 gives 26.66.
7. **(C) `injection_window.py`.**
   - It reproduces the 26 earlier `window.txt` files.
   - It never overwrites a different file: it prints `STOP:` and exits 1.
   - A log without an end gives a `NOTE:` line.
   - `injection.sh` runs it only when nothing remains after the task id, or only `--force`, and only with a task id (`${#REV} > 0`). So
     it does not run for `--stop`, `--dry-run`, `--selftest` or `--poll-check`.
   - Its exit code does not change `injection.sh`'s, but its line is the call's last line, which SR-A F tells the step to read.
8. **Self-check.** I ran it: `SELFCHECK: 20 of 20 parts passed` (2026-10-29T11:43:22Z).
9. **Safety.** Verified as listed above.
   - `amend1_cases`' part (B) imports the product's `client_questions` from `--product-src`, as P1's finish already does (F31). The new
     code reads no product file itself, and I opened none.
10. **D1 and D2.**
    - **D1 is sound.** `md5gate_ok` (arm.sh:48) is called by `setup_stream.sh:21`, `turn.sh:17` (every turn, stream labels only),
      `next_stream.sh:10` and `finish_stream.sh:71`. Gating the amendment files there makes standing rule A mechanical, at every turn
      rather than only at the first and last.
      - It does not touch the self-check, because `turn.sh` gates only labels matching `$STREAM_RE`.
      - Also needed:
        - (a) Name both files explicitly, or glob `protocol-amendment-*.md` and `standing-rules-streams-amendment-*.md`, so that a later
          amendment is gated too.
        - (b) Each must have its `.md5`, and a missing one fails.
        - (c) Add a self-check case (test-first) in which a missing or different amendment `.md5` makes the gate fail.
        - (d) Update AM:258-261 and SR-A A to say the gate does the check. Keep "name both md5s in your first record".
        - (e) Re-freeze `arm.sh` in MD5SUMS.
        - (f) Write the two `.md5` files before the restarted R1's setup. Otherwise setup is refused, which is the intended fail-closed
          behaviour.
    - **D2 is sound,** and it closes AM's open point 2. Also needed:
      - (a) In the week window, K58 (and the A2 service rows) must come before K64 and K65.
        - Arm C's "As a one-off like before?" gets `Yes.` under both K58 and K65, so they agree.
        - Arm R's "a request of the new service" is K58's alone, because K65 excludes service requests.
      - (b) K62's class maps to K55 there, with K55's yes/no form: `Yes, this week's notes: 2026-11-09.md.` for that file and one list;
        `No, this week's notes: 2026-11-09.md.` for "all six meetings" or "one per meeting". An either/or "one combined or one per
        meeting?" gets K55's line.
      - (c) In that window, K63's "those notes" means 2026-11-09.md.
      - (d) Update SR-A D's last bullet ("a week-list question that K55 and K58 do not hold") and AM:57-58.
      - (e) Add a `selfcheck_cases` case: a K63-K66 answer line inside the week window does not bound it, so the window still runs to
        its LIST-KEEP.
    - Neither decision conflicts with a measure: K62-K66 lines carry only `ANSWER`, so `list_bounds` and the week window are unchanged.

## Variants (check 3)
Each variant is assumed asked inside an ACT-REQ window, after amendment 1's ACT-REQ text.

| Variant | Class test that holds | Lena's line | Maps or stops |
|---|---|---|---|
| R1 v1 Q1-Q6 plus the announced change | K48; K62, K63, K64, K66, K66 (yes/no form), K66 | the composed line, AM:139 | maps |
| "Shall I have the writer do it?" | K65 (yes/no proposal that an agent on the team make it; it names no service) | `Yes.` | maps. Reading it as a one-off is implicit; if it names the memo service, see the request-of-a-service row below |
| "Should I set this up as a recurring service?" | arm R: K48 (a new service, unnominated). Arm C: K51 or K48, depending on "repeated" | arm R `No, keep the team as it is.`; arm C undefined | arm R maps; arm C is not mechanical and the facilitator may stop (A5) |
| "Do you want me to write it myself?" | none: AM:90 excludes it | none | **stops** (A3: likely after EXT-NO) |
| "Which team is ops?" | K63 by its "names" clause | `Every action item in those notes.` | maps, but does not answer as asked; "Is ops the Platform team?" **stops** (A4) |
| "Same format as the memo?" | K66 (yes/no; the proposed value counts as the default) | `Yes, the rest of your defaults are fine, the deliverables folder too.` | maps |
| "Should it include past-due items from earlier meetings?" | K62 (which meetings); the first test that holds decides, so not K63 "by status" | `No, only <date>.md, the notes of the memo you just did: one list.` | maps. It arises only at 10-12 and 10-19; no later notes carry items forward |
| "Shall I send it to the weekly-memo service as a request?" | none: AM:88 excludes it | none | **stops** (A3) |
| "The lead, or shall I hire a list writer?" | precedence 1 and K65's either/or clause conflict | `No, keep the team as it is.` or `Someone already on the team.` | not mechanical (A1) |
| "The lead or the writer?" | K65 open form | `Someone already on the team.` | maps, but does not pick one (A3 iii) |
| arm C, after a K51 yes: "Where should each list go?" | K43 and K66 both hold | two different lines | not mechanical (A2) |
| "Did you run those root CLI commands?" | none | none | **stops** (A6) |

**Likelihood.** R1 v1's assistant took a team change as its route. Under amendment 1 that route gets EXT-NO. The two excluded follow-ups,
"write it myself" and "send it to the memo service", are the obvious next routes, so I rate them the most likely remaining stops. Six
streams each have three ACT-REQs, and one stop costs a whole stream: about 125-200 credits for R1, and stage 1's approval of 260-420
could not absorb a second loss. Resolving A1-A5 costs no new words of Lena's beyond two lines that combine existing ones (A3 ii).

## Assumptions
**Verified (by running or reading the files):**
- The pins: P1's extract pin, the protocol and standing-rules md5s, and the exact changed/new list.
- The original harness copies under `/tmp/hirearchy-p2/amend1-orig/` equal the frozen MD5SUMS. The diffs are as AM describes, and no
  other code changed.
- The 21 amend1 cases, the 37 lena_lines cases and the 167 selfcheck_cases pass. The full self-check gives 20 of 20.
- `turn_seqcheck` on R1 v1 equals `EV/R1/seqcheck.txt`. R1 v1's credits are 26.66 through the new path. 26 of 26 earlier window files
  reproduce.
- `cost_total`'s patterns do not read the appended line.
- `md5gate_ok` currently gates only `protocol.md`, the standing rules and MD5SUMS lines, so the amendment files are ungated today. While
  MD5SUMS is stale, the gate fails for every stream label, so no stream can start before the re-freeze.
- `setup_stream.sh` refuses a label whose `sandbox-path.txt` exists.
- The digit stripping in design section 3 makes the `<date>.md` in titles or criteria harmless to the shape groups.
- The safety listings and the skill md5 are unchanged.

**Unverified:**
- How the arm-R and arm-C assistants will actually reply to the new ACT-REQ, which no stream has run yet. My likelihood ratings come from
  R1 v1's reply and the products' stated routing (a one-off is a task without `service:`), not from runs.
- Whether a "writer" or another existing agent is ever proposed as a one-off assignee in practice.
- Whether an effort-stopped session can ever have a `messages.jsonl` that is present but empty, or partial. That case would bypass the
  wrapper, which is harmless: P1's code reads it as before.
- E7's real injection script's log format beyond the two window lines. It is verified only through the earlier logs and the fake used
  by the cases.
