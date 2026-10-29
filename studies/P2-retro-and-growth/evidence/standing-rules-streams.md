# Standing rules for every P2 stream step: R1, C1, R2, C2, R3, C3 (and a replacement)

Read this file before the stream's first turn and follow it for every turn, together with the frozen `protocol.md`. **Before anything
else, run `zsh EV/harness/skill_move.sh recover`** (protocol 3.6): it restores the owner's global skill if an earlier step was cut off with
it aside; name any `RECOVERED <label>` line in your first record and in your `send_message`, and stop with a warning on a `STOP:` line. These are P1's 16
standing rules (`studies/P1-itemized-playbook/evidence/manager-standing-rules-streams.md`), carried over and adapted to P2: the two arms, P2's
lines and rows, the one wrapper per turn, and the global-skill move of arm C. Each rule changes how the step works, not what any measure is.
Where a P1 rule was a ruling about a P1 line that P2 does not use, the P2 form says so. `H` = `evidence/harness`, `EV` = `evidence`.

1. **One wrapper per turn** (P1 rule 1; F-P1-14). Send every turn with ONE call: `zsh H/turn.sh <label> <n> <absolute prompt file>`. Never
   call `run_turn.sh` or `after_turn.sh` yourself (both refuse). After each turn, read `turn-NN.wrapper.txt`: its last line must be
   `after_turn sequential: checked`; a `STOP: snapshot before the boundary` stops the step. Record `after_turn sequential: checked` in the
   turn's facts.
2. **Absolute prompt-file paths** for every turn (P1 rule 2): write Lena's line to `EV/<label>/lines/turn-NN.txt` and pass that path.
3. **The owner form** (P1 rule 3, P2 form): N for the whole stream (names as the notes give them; JD as `JD`). Before sending a line, check
   that no key owner appears as bare initials; record `owner form N: checked`.
4. **The `lena-lines.txt` line form**, exactly: `turn <n> | rules <ids> | table rows <rows> | facts: ...` (protocol 4.8), with P2's rule
   ids; each TRAP, VR-REJECT, ACCEPT, L-ASIS, ACT-REQ and NEXT rule carries its memo date (`TRAP-N@2026-10-19`). After writing each line,
   check it with the frozen parser, read-only: `python3 -B -c "import sys; sys.path.insert(0,'EV/harness'); import lena_lines as L;
   print(L.parse_line(open('EV/<label>/lena-lines.txt').read().splitlines()[-1]))"`; it must return the turn and its rules with
   `unknown_rules` empty. Fix an unread line before the next turn.
5. **Arm C, the global skill** (replaces P1 rule 5, arm F's lock check). Arm C's setup moves `~/.kiro/skills/hirearchy/` aside to
   `ST/skill-aside/` (`skill_move.sh`); every `after_turn.sh` checks it is still aside. On ANY stop of an arm-C stream, end it with
   `zsh H/stop_stream.sh <label> "<reason>"` (it finishes the stream and restores the skill), and read its last line: the global skill must
   be `in place, md5 443e1bc4911aa4d6aaa6457e78f673c1` before you send the warning. If the restore prints `STOP: skill restore impossible`,
   change nothing and say so in the warning. In arm R the global skill stays in place; a `STOP: H2` line about it stops the step. Keep each
   turn of your own session moderate, so the step is not cut off with the skill aside; if it is, the next step's `recover` restores it
   (an `ASIDE-PENDING` record, written before the move, counts as open too: F33 of review 2).
6. **Questions mapped by P1's turn-1 rulings, and the yes/no form** (P1 rule 6, P2 form; protocol 5). A yes/no question always gets a line
   that starts with yes or no: a row whose line does not (K3's later form, K6, K12, K13, K18, K20, K32, K43, K54, K55, K56 ...) takes its
   yes/no form, `Yes, ` or `No, ` + the line, by whether the proposition says what the line says; K33 is `Yes.`; A-W, H2 and `approve` keep
   their exact text. Record `K<n> (yes/no form)`. An either/or or open question about the order of a brief's items or plans is K33's open
   form `In the brief's order, one at a time.`; in arm C, the same question about the order of the changes she said yes to (K51, K52) is
   `K33 (arm C open form)` `In the order you proposed, one at a time.` (rule `ANSWER`; C2 of the closing decision); an open "what would you like to look at?" is K53's open form `Nothing in particular; keep the
   team as it is.`; in arm C an open question about the new service's name gets `Call it the action list.` and about its criteria `The same
   as the lists: each action with its owner and due date; at most one page.` (K43a); its budget, inputs or description asked openly: stop
   and quote (F30 of review 2). at elicitation, "who may be named" and every other owners question is
   K39 (A-W `Use the words from the notes.`); English or an "open items" section is K3 with no added text; asked again after H2: K3's
   `The rest of your defaults are fine, the deliverables folder too.`; a third time: stop with a warning. **Any other question the table
   does not hold:** stop before the next Lena line with a warning that quotes the question verbatim and names the two or three closest rows.
   Never improvise.
7. **Memories** (P1 rule 7): the `memories.db` md5 before and after the stream, as frozen; a change stops the study before the next stream.
   At the stream's end record whether `session_start` holds a `<memories>` block, and its length, in `<label>/memories-block.txt`.
8. **Credits** (P1 rule 8, P2 form): stage 1 (R1, C1): `credits-running.txt` prints `CREDITS:` over 250; finish the stream (the gate reads
   it). Stage 2: a `STOP-CREDITS:` line (over 260) ends the stream with `stop_stream.sh <label> "credits"` and a warning.
9. **Report every slip** (P1 rule 9): report a facilitator slip as soon as you find it, with a file under `<label>/harness-failures/`, and wait
   for a ruling only when it could have changed the course. Never edit, retry or delete evidence.
10. **The memo input's name and value** (P1 rules 10 and 14): the team names its input and may give a path; read every memo request from
    root's sent mail (`requests-by-turn.txt` lists the notes date of each service request, read from its `## Request` block); record
    `memo <n> request read from sent mail: <message id> (<input name>: <value>)` where a line depends on it.
11. **A self-referential criterion** (P1 rule 11): whether to count, waive or treat as met a criterion about the reviewer's or the checker's
    own report is K29a `Yes.`, every time; a contract item on it is K30 (reword to exclude itself and keep the check: `Yes, add it.`; remove
    the check: `No.`; anything else: stop and quote).
12. **"One bullet or two?"** for a key decision kept as one bullet (P1 rule 12): K14c `Yes, that's a decision.`; a split key decision asked
    about: stop and quote.
13. **An extra-part question before memo 1's H6 answer** (P1 rule 13): K25a (K32 `Keep it as it is.`; with a v1 criterion that limits the
    parts: stop and quote). From H6's answer on: K25. From A-M's answer on: K25's A-M form.
14. **The trap** (new; replaces P1's owner-form rules 15-16 for P2): apply the trap rule (protocol 4.2) to every delivered version of memos
    2-5 before you write the verdict, and record `trap: fails (<owner>'s due <value>, key <date>)` or `trap: passes` in the facts. The first
    failing version of the stream is TRAP-1 (with the lasting sentence), every later one TRAP-N, which opens `Not right yet, the same
    problem as before:`. Root's question for a TRAP-N rejection: "Same as R<j>: a one-off?" with R<j> a trap rejection: K29 `Yes.`; "About
    <id>: add ...?" with `<id>` in [trap-crit]'s lineage class (`roles.txt`, the latest contract) and an agreeing proposition: K30 `Yes, add
    it.`; anything else: K30c `No: it is the same as R<j>.` with R<j> the TRAP-1 rejection. A-M's add-only item: K28 `Yes, add it - it
    replaces the old order.`
15. **The retros and the items** (new; F27 and F28 of review 2): write `CONDITION` into the rules of L0, the line that makes retro 1's
    waiting condition hold (protocol 4.6): **the line that answers root's one question for the third trap rejection** (the third TRAP rule
    for a third memo; its row K29, K30, K30c or K47a, and in its facts `answers <that TRAP rule>`, for example `answers TRAP-N@2026-10-26`),
    or, if root asks no question for it before its next delivery, the first later line that judges a delivered version; or the first
    verdict on memo 5 when that comes first and is not the third TRAP line. Every line that answers a trap rejection's question carries its
    `answers <rule>` fact. An offer in any reply before L0 gets RETRO-NOT-NOW (L0's own line included, K40); in L1 or L2 an offer gets
    RETRO-YES; when neither reply offered, L3 carries RETRO-ASK even if the reply before L3 offers (arm C: the same rows, counted from the same
    L0; an arm-C offer, of a retro or a review, is answered as in arm R: K40 before L0, K41 in L1 or L2, which line is then the arm-C turn
    with no RETRO-ASK at L3, K41a after it; record it in `retro-offers.txt` as the arm-C assistant's own offer; C3 of the closing decision).
    After retro 1's brief (arm C: after the arm-C turn), an offer before retro 2's place gets RETRO-NOT-NOW (K41a); a proposal to run the brief again while a retro's
    items are being answered gets K61's `No.`. Retro 2's place: the week list's LIST-KEEP line with RETRO-YES when the reply delivering the
    week list offers, else the next line. Record each turn's offer reading in `retro-offers.txt`. Answer the brief's items with their rows (K42-K47, `answer` items K47a, `cause` items K47b),
    one line, in the brief's order; each plan with PLAN-APPROVE, a nominated plan with changed details too (K44, recorded as facts); every
    unnominated extension (protocol 6.6) with EXT-NO. The line with RETRO-YES or RETRO-ASK carries no next-memo request.
16. **End every stream with its reason** (new; protocol 3.7): `zsh H/finish_stream.sh <label> --end retro-2-done|cap-turns|cap-runs|
    two-L-WAIT|ruling`, or `stop_stream.sh` (which passes `credits` or `stopped`). The measures read `end.txt`; without it every step
    whose event did not happen reads NOT DETERMINED. **Never run `retro` on the stream's org yourself**: the per-turn retro snapshot runs on a scratch copy (protocol 3.3); a
    `STOP: the retro snapshot changed the stream's ledger` line stops the step (H6). The facilitator never calls a product CLI on the
    stream's org except through the harness scripts and the injection.

Rulings this carries over (P1): `manager-decision-probe-define.md` (H-A1: the dry run of every CLI call), `manager-decision-lock-check3.md`
(one function per check), `manager-decision-f1-owner-form.md`, `manager-decision-f1-after-turn-timing.md` and `manager-decision-f2-after-turn-
t4.md` (the one wrapper), `manager-decision-row-I1-t1.md`, `manager-decision-row-I2-t7-revised.md`, `manager-decision-row-I2-t12.md`,
`manager-decision-row-F2-t4.md`, `manager-decision-row-F2-t10.md`, `manager-decision-row-I3-t1.md`, `manager-decision-memo-input-name.md`,
`manager-decision-stage-1-gate.md` (the `since` precision, the line form, the memories block, the effort warnings).
