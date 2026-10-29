# P2 protocol amendment 1: ACT-REQ names its notes file, the action-list rows, the composition rule, and the harness fixes

Written 2026-10-29 by a direct claude-opus-5.5 pass, after the manager's decision was recorded. It is not frozen by this pass: an independent
claude-opus-5.5 review comes first, and then the re-freeze writes `protocol-amendment-1.md5` (section 9 of this file). `EV` =
`/Volumes/workspace/hirearchy/studies/P2-retro-and-growth/evidence`, `H` = `EV/harness`. "Protocol n" is section n of `EV/protocol.md`
(md5 `31bc856cad06efbdefc04d582142eac2`, frozen 2026-10-29T10:10:16Z, `freeze.txt`). "Design 17.3" is section 17.3 of
`docs/design/org-growth-phase-2.md`.

## 1. Basis
- **The binding decision:** `EV/manager-decision-row-R1-t7.md` (2026-10-29), "Decision: protocol amendment 1, before any further stream,
  and R1 run again", items 1-6. This file carries out items 1-4 and 6, and item 5 except the re-freeze, which comes after the review.
- **The departure from protocol 0.** Protocol 0 bars any change to Lena's lines or the decision table after R1's first turn. The manager
  departs from it under the owner's delegation (2026-10-28), for the reasons the decision gives: no pass rule's outcome has been observed
  (R1 ended at turn 7, before any one-off task, retro, brief, extension or signal); the change fixes a stimulus defect (an ambiguous
  request), not a reading of results; it applies equally to all six streams, none of which has run under it, so the pairing holds; without
  it every stream would end by ruling at its first ACT-REQ.
- **The facts it rests on:** `EV/R1/harness-failures/question-not-in-table-t7.md` (R1 v1's turn-7 reply, verbatim, and the rows examined),
  `EV/R1/harness-failures/finish-r1-v1-findings.md` and `EV/R1/harness-failures/turn-sh-sequence-check-vacuous.md` (the harness defects).
  `EV/R1/` is read only; nothing in it was moved or edited by this pass.
- **The review and its rulings.** The independent review (`EV/amendment-1-review.md`, `.json`) found A1-A12 and two needs, D1 and D2. The
  manager ruled on each in `EV/manager-decision-row-R1-t7.md`, section "Amendment 1's review: rulings" (2026-10-29). A direct
  claude-opus-5.5 pass applied the rulings to this file, to `EV/standing-rules-streams-amendment-1.md` and to the harness. Each change
  names its finding (A1-A12, D1, D2) where it stands.
- **How this file's sections map to the decision's items 1-6** (A7; the headings keep their own numbers, which the harness comments cite):

  | This file | The decision's item |
  |---|---|
  | section 3 (ACT-REQ's text) | item 1 |
  | section 4 (rows K62-K68, the precedence, K51's condition) and section 6 (the mapping check) | item 2 |
  | section 5 (the composition rule) | item 3 |
  | section 7 (A) (`turn.sh`'s sequence check) | item 4 |
  | section 7 (B), (C) | not in items 1-6: harness fixes the manager ratified (next bullet) |
  | section 7 (D) (the md5 gate, D1) | the manager's D1 |
  | section 7's cases and self-check, section 9's re-freeze list | item 5 |
  | section 8 (nothing else changes) | item 6 |
  | section 9 (how later steps read the amended texts) | none: the reading rule for the amended texts, and item 5's re-freeze |
- **(B) and (C) are harness fixes the manager ratified** in `EV/manager-decision-row-R1-t7.md` ("Amendment 1's review: rulings", A7). They
  change no measure: they make the cost of an effort stop and the injection's window mechanical.

## 2. Scope
- **It binds every stream that starts after it is frozen:** the restarted R1 (label `R1`, a fresh setup), C1, R2, C2, R3, C3, and any
  replacement. All of them run under protocol v1 as amended here, so the arms stay paired.
- **R1 v1 is withdrawn.** Its evidence moves to `EV/R1-v1/` (the manager's decision; not done by this pass). It is reported as "withdrawn
  at turn 7 under protocol v1, superseded by amendment 1", is not scored, is no valid stream of either version, and does not use arm R's
  one replacement.

## 3. Item 1: ACT-REQ names its notes file
- **New text of ACT-REQ** (protocol 4.3's row, the text column; the "When" column is unchanged):
  `Can you also make a one-page action list from these notes (<date>.md) for the ops team? Each action with its owner and due date; at most one page. I'll wait.`
  with `<date>` the date of the memo the same line accepts: `2026-10-05` after memo 1, `2026-10-12` after memo 2, `2026-10-19` after memo 3.
  The rule id stays `ACT-REQ@<date>` (protocol 4.8).
- **A declared deviation from design 17.3 item 3's exact text** (`Can you also make a one-page action list from these notes for the ops
  team?`). The only change is ` (<date>.md)` after "these notes". The reason: protocol 4.3 already defines "these notes" as the memo just
  accepted, but Lena's words did not say so. In R1 v1 the assistant read "these notes" as possibly every file in the notes folder
  (question 1 of its turn-7 reply), and no row of the table could answer it. Naming the file makes her words carry the referent the
  protocol had already fixed. 17.3's words stay, and so do its criteria lines (`Each action with its owner and due date; at most one
  page.`). They are still the same in each of the three requests, as 17.3 requires. Only the file name differs between them, as the
  referent already did.
- **The other lines that name a list's notes were checked and are unchanged:**
  - WEEK-LIST (`Make the action list for this week.`) has no "these notes". Its referent question ("which notes or week?") already has
    a row, K55 (WEEK-NOTES, `This week's notes: 2026-11-09.md.`), so it is not ambiguous the way ACT-REQ was. ACT-REQ's referent
    question had no row.
  - WEEK-NOTES already names its file. NEXT (`Now <next>.md please. I'll wait.`) names its file. LIST-KEEP and ITEM-DELIVERABLE name no
    notes.
  - K43a's arm-C open form (`The same as the lists: each action with its owner and due date; at most one page.`) quotes ACT-REQ's
    criteria words, which are unchanged.

## 4. Item 2: the action-list rows K62-K68, their precedence, and K51's condition
Added to protocol 5's table after K61. No row id is reused: the table's highest id is K61, and no harness file names K62-K69 (checked by
search before writing). K67 and K68 were added by the manager's rulings on the review (A3 (ii), A6). Every line answers the question as
asked (protocol 5's rule, P1's C7 lesson). A yes/no question gets the row's yes/no form, which starts with `Yes` or `No`. An open or
either/or question gets the row's open form. No line carries criterion content beyond ACT-REQ's own words (the A-W lesson, p1-decision;
protocol 5, "No answer at elicitation may widen into a criterion"). K67's and K68's lines combine or reuse existing words of Lena's.

**Where the rows apply (mechanical).**
- **In an ACT-REQ window.** K62-K65 and K67 apply to a question in an assistant reply inside an ACT-REQ window that is about the list that
  ACT-REQ asked for. An ACT-REQ window runs from the ACT-REQ line to the next Lena line with LIST-KEEP, ACT-REQ, NEXT or WEEK-LIST
  (protocol 4.5; `lena_lines.counts()["list_bounds"]`).
- **In the week window (D2).** The week window runs from the WEEK-LIST line to the next Lena line with LIST-KEEP (protocol 4.5). There:
  - K58, and the service rows of precedence 2 while a new service is being defined, come first, before K62-K67 (D2 (a); A2);
  - K62's class (which notes, one list or several) maps to **K55**: the open or either/or form is K55's line `This week's notes:
    2026-11-09.md.` (an either/or such as "one combined or one per meeting?" gets it too); the yes/no form is `Yes, this week's notes:
    2026-11-09.md.` when the proposition is that file and one list, and `No, this week's notes: 2026-11-09.md.` otherwise (for example
    "all six meetings" or "one per meeting") (D2 (b));
  - K63-K66 apply as in an ACT-REQ window, and K63's "those notes" means 2026-11-09.md (D2 (c));
  - the K63-K66 lines carry only rule `ANSWER`, so they do not bound the week window: it still runs to its LIST-KEEP (D2 (e); the
    self-check holds this case).
- **Anywhere.** K66 applies to any action list, as K54 does. K68 applies to any question about activity Lena did not do.
- A question about the week list that no row holds falls under protocol 5's rule, as before.

**Precedence.** These rows come first, in this order, and K62-K68 yield to them:
1. **The structural rows.** K44 (a nominated PLAN FOR YOU), K48 (an unnominated structural change: a hire, a new service, a charter or
   limit change, announced or proposed), and in arm C K51 and K52. A question that proposes such a change is answered by K44, K48, K51 or
   K52 (A1).
   - **An either/or whose alternatives include a structural change** (A1; "Should the memo lead make it, or shall I hire a list writer?",
     "Just this list, or shall I set up a weekly list service?") gets EXT-NO (or, in arm C, K51 or K52 where they apply), then the open
     line of the K62-K66 row whose class holds the other alternative. It is recorded `K48, K6n (open form)`, for example `K48, K65 (open
     form)` for `No, keep the team as it is. Someone already on the team.` and `K48, K64 (open form)` for `No, keep the team as it is.
     Just this list.` Section 5's composition rule places EXT-NO first.
   - **When K51 or K52 applies in arm C** (Lena says yes to the structural alternative), the line is K51's or K52's alone, recorded
     `K51` or `K52`. The yes picks one alternative, so it answers the either/or as asked, and the other alternative's open line (such as
     `Just this list.`) would contradict it. This is the closest reading of the ruling's "(or, in arm C, K51 or K52 where they apply),
     then the open line": taken literally, the line would be `Yes, make it a service. Just this list.`, which says both.
2. **The service rows, while a new service is being defined** (A2), from a K42 or K51 yes to its PLAN FOR YOU's apply: K43, K43a, K57 and
   K60 come before K62-K68. So, in arm C after a K51 yes, "Where should each list go?" is K43's `One action list per request, in the
   deliverables folder.`, not K66's line.
   - **K58 comes before K64 and K65** (A2), and before K67, because K67's line is built from K64's and K65's words. Without that, arm R's
     week-list question "Shall I send it as a request of the new service?" would get K67's `No, ...` where K58 gives `Yes.`.
3. **K9**, a spend request beyond an approval.
4. **K54's content rows** (K12-K16, K14a-K14d, K19), for an action, an owner, a Due or a row that the key settles; and, for a rule
   default that differs from the key on what counts as an action, K14b or K1's line (A11; K66 below).
5. **K10 and K11**, the injected rework and which version. K10 wins over K68 for the injected rework (A6).

**K51's condition, amended (A5).** Protocol 5's K51 reads "(arm C) a proposal to make the repeated action list a standing service". Its
line (`Yes, make it a service.`) is unchanged; its condition now reads:
- **"repeated" holds once at least three ACT-REQ lists have a LIST-KEEP line.** An ACT-REQ list has a LIST-KEEP line when the first
  list bound after its ACT-REQ line (`lena_lines.counts()["list_bounds"]`) carries a `LIST-KEEP@<task id>` rule. The count is read from
  `lena-lines.txt` as written before the Lena line being composed. This is design 7.1's threshold for the service signal.
- **Before that,** an arm-C proposal to make the list a service is K48 (EXT-NO), as an unnominated proposal is in arm R. **After it,** it
  is K51. A proposal in the reply that delivers the third list is still "before": its answer is the line that carries the third
  LIST-KEEP, and that LIST-KEEP is not yet written when the line is composed. A later proposal gets K51.
- **The reason** is the pairing (protocol 16 item 11). Arm R's brief can nominate the service only after three judged one-offs (retro 1
  comes after the third list), so the same threshold in arm C means neither arm can make the service earlier, and the first three
  one-offs are kept in both arms.
- **The consequence for arm C's one-off count.** Every arm-C service proposal inside an ACT-REQ window gets K48, so arm C's three ACT-REQ
  one-offs stay one-offs, as arm R's do. Under v1's unbounded "repeated", a yes at ACT-REQ 1 or 2 would have made the later lists service
  requests and removed up to two ACT-REQ one-offs and the week list's one-off. From the line after the third LIST-KEEP, a K51 yes is
  possible. If its service is applied before WEEK-LIST, arm C's week list (protocol 12.4's "arm C's fourth one-off") may be a request of
  that service instead of a fourth one-off. 12.4 reports what the week window holds, as before.
- ITEM-SERVICE's arm-C condition in protocol 4.3 ("a proposal to make the repeated action list a standing service (K51)") reads with this
  meaning of "repeated".

**Class tests (read literally from the question; the first test that holds decides):**

| Row | The question (class test) | Open or either/or form | Yes/no form |
|---|---|---|---|
| K62 | **which notes, or one list or several:** the question asks which notes file(s), meeting(s), week(s) or dates the list is made from, or whether to make one list or several (one per meeting, one combined). In the week window: K55 (above) | `Only <date>.md, the notes of the memo you just did: one list.` | `Yes, only <date>.md, the notes of the memo you just did: one list.` when the proposition is that file only, one list; `No, only <date>.md, the notes of the memo you just did: one list.` for any other file, set of files or number of lists |
| K63 | **which actions:** the question asks which action items go on the list, all of them or a part (by team, owner, kind, status or date, "only the ops team's"), including a request for the names or a rule that defines the part, and who the ops team is, or whether it is the team in the notes (A4) | `Every action item in those notes.` | `Yes, every action item in those notes.` when the proposition is every action, or that the ops team is the notes' team, or that no filter applies; `No, every action item in those notes.` otherwise (for any part) |
| K64 | **one-off or recurring:** the question asks whether she wants this one list, or a list repeatedly (each week, with each memo, a standing list), and proposes no change to the team (precedence 1 above) | `Just this list.` | `Yes, just this list.` when the proposition is this list once; `No, just this list.` when it is a repeat |
| K65 | **who makes it, or whether to send it to someone already on the team as a one-off:** the question asks which agent makes the list, or proposes that an agent already on the team make it as a one-off (a task outside any service), or proposes that the assistant (root) make or write it itself (A3 (i)) | `Someone already on the team.`, for an open question, or an either/or between an existing agent and anything that is not a structural change (A1) and not another existing agent; an either/or between two existing agents ("the lead or the writer?"): `That's up to the team.` (K37's words), recorded `K65 (either/or of existing agents)` (A3 (iii)) | a yes/no proposal that an agent already on the team make it as a one-off: `Yes.`; a yes/no proposal that the assistant (root) make or write it itself ("Then shall I write it myself from the notes?"): `No, someone already on the team.` (A3 (i)) |
| K66 | **an action list's defaults:** a question, or a heading with an offered default, about the list's format (file type, layout, columns, title, length, what "one page" means), the rules it follows, limited to the memo's rules or a default that restates them (A11), its file name or folder, how it is checked (by agents already on the team), or a budget given as a default; a value the assistant proposes counts as its default. A rule default that differs from the key on what counts as an action (for example "only `ACTION:` lines count", or one that adds items the key leaves out) is not K66's: it takes K54's content rows, K14b `No, that's not an action item - leave it out.` for an item the key does not hold, or K1's line `Yes, if someone said they'd do something, it counts.` for a default that would leave out commitments the key counts (A11) | K3's sentence `The rest of your defaults are fine, the deliverables folder too.` (K54's form line) | `Yes, the rest of your defaults are fine, the deliverables folder too.` when the proposition is the assistant's default; `No, the rest of your defaults are fine, the deliverables folder too.` when it is not (for example "or do you want a PDF?" against a markdown default) |
| K67 | **a request of an existing service** (A3 (ii)): a proposal to make the list as a request of a service that already exists ("Shall I send it to the weekly-memo service as a request? It already takes a notes file."); and (the manager's closing ruling) an either/or between such a request and a one-off ("as a request of the memo service, or a one-off?"). In the week window K58 comes first (precedence 2) | the either/or: `Just this list, by someone already on the team.` (K67's own words without its `No`), recorded `K67 (open form)` | `No, just this list, by someone already on the team.` (K64's and K65's words) |
| K68 | **activity Lena did not do** (A6): a question about the harness's CLI snapshots or other commands in the log that she did not run ("Did you run those `root run/quality/services` commands?"); the injected rework stays K10's | `I don't know anything about that.` (L-INJ's first clause) | `No, I don't know anything about that.` (its own yes/no line, so the `I` keeps its case) |

- **Recorded** under rule `ANSWER`. The record rule (A10): the open or either/or line is recorded `K6n`; K65's, whose row has no bare
  line, `K65 (open form)`. The yes/no line is recorded `K6n (yes/no form)`. The special forms are `K65 (either/or of existing agents)`
  (A3 (iii)) and, in A1's composition, `K48, K6n (open form)`, which is the ruling's own form and marks the open line given after EXT-NO.
  K67's yes/no line is recorded `K67`, and its either/or line `K67 (open form)`. Protocol 4.8's `ANSWER` ("a K12-K37, K43a, K47a or K57-K61 table answer") also covers K62-K68.
- **K66 and K3's count.** K3's "a third time: stop and quote" counts the memo's elicitation defaults (K3's class). It does not count K66
  lines. K54 in v1 already gave a list's form K3's sentence without that count, and K66 keeps that reading.
- **Why each line adds no criterion content:**
  - K62 names the file ACT-REQ now names and says "one list", which ACT-REQ's "a one-page action list" already says.
  - K63 restates ACT-REQ's "Each action". Its extension (A4) uses the same lines, and every reading names the whole list.
  - K64 and K65 say nothing about the list's content. K65's `That's up to the team.` is K37's line, and its `No, someone already on the
    team.` is its own open line in protocol 5's yes/no form.
  - K66 accepts the assistant's own defaults in K3's existing words, and only for rules that are the memo's or restate them (A11). A rule
    that differs from the key gets the key's own rows. No words of Lena's beyond ACT-REQ's enter a list task.
  - K67 combines K64's and K65's words and says nothing about content. The script needs one-offs (design 17.3 item 3, design 7.1, and
    P2-X1 step 1, which reads a service request in the window as FAIL-CLOSED), and K67 keeps the list a one-off in both arms.
  - K68 is L-INJ's first clause and says nothing about the list.
- **Outside the classes:**
  - any open question about content the key does not settle;
  This follows protocol 5's rule (stop and quote). The either/or between a request of an existing service and a one-off, which the
  rulings pass flagged, is now K67's open form (the manager's closing ruling in `EV/manager-decision-row-R1-t7.md`).
- **A note for step 12 (A12; reported only, no line changes).** Some lines are long, notably K62's and K63's. If root copies an answer
  given only at the first ACT-REQ into the first one-off's criteria, and the second and third ACT-REQs raise no such question, the shape
  relations of design section 3 differ: the criteria key (ii) differs, and the Jaccard index (iii) can fall below 0.6 (the digit-bearing
  `<date>.md` is dropped, so the date itself is harmless). Only the title relation (i) would then join the cases. This is T12's known risk
  (design L5), and P2-S reports it. Step 12 reads a `DIFFERENT` T12 with it in mind.

## 5. Item 3: the composition rule for a reply that announces an unnominated change and asks questions
- **When it applies.** A Lena line answers a reply that announces or proposes a structural change K48 answers, and that also asks one
  or more other questions (or mentions something a row answers, such as the injected rework, K10). It also applies to an either/or whose
  alternatives include a structural change (A1, section 4's precedence 1): EXT-NO, then the open line of the other alternative's row.
- **Numbering in every line (A9).** Rule 3 below applies to any Lena line that answers a numbered list of two or more questions, with or
  without K48. It changes no line's text, only adds the reply's numbers, so a numbered list gets numbered answers whether or not the reply
  also announces a team change. Rule 4 (numbering questions the reply did not number) stays within this composition rule's lines; protocol
  4.4's own numbering of a brief's items is unchanged.
- **The rule:**
  1. EXT-NO `No, keep the team as it is.` comes first among the answers, once, however many sentences announce the change.
  2. The other answers follow in the order the reply raised them.
  3. Answers to a numbered list of questions carry the reply's numbers in E7's form, `<n>: <line>` (as in K30's `1: Yes, add it. 2:
     No.`). This rule holds in every line that answers a numbered list of two or more questions (A9).
  4. When the reply asks two or more questions and numbers none of them, they are numbered 1, 2, ... in the order asked.
  5. An answer to something outside the numbered list, such as L-INJ for a mention of the rework or L-BASE, carries no number and stands
     where the reply raised it.
- **How it fits protocol 4.4's part order.** EXT-NO is a table answer (K48), so it belongs to part 2, "the answers to the assistant's
  questions". This rule only fixes its place as the first entry of part 2 and adds the numbering (in every line that answers a numbered
  list, A9). Part 1 (the verdict sentences) still
  comes before it. Parts 3-7 follow unchanged, including part 7: `I'll wait.` comes last when a memo or list she asked for is not
  delivered.
- **The record.** The rows are written in the line's order, K48 first (`table rows K48, ...`). `lena_lines.ext_no_not_first()` lists
  every line whose rows hold K48 after another row. It is an H7 check for step 12, and the self-check exercises it.
- **What it keeps working:**
  - The line carries no LIST-KEEP, ACT-REQ, NEXT or WEEK-LIST, so the ACT-REQ window runs on to the line that judges the list (protocol
    4.5, P2-X1 step 1).
  - EXT-NO is counted once (`lena_lines.counts()["ext_no"]`, P2-B step 3).
  - D-UNNOMINATED is still read per `propose_org` call (protocol 6.6, `p2/unnominated.json`) and is unaffected by an announcement that
    made no call.
  - The self-check holds a case for each of these (section 7).

## 6. Item 4: the mapping check against R1 v1's turn-7 reply
The reply is quoted in `EV/R1/harness-failures/question-not-in-table-t7.md` (`EV/R1/turn-07.txt`). Its turn-7 line was ACT-REQ v1
(`... from these notes for the ops team? ...`), and memo 2026-10-05 had just been accepted. Each part of the reply maps to a row:

| Part of the reply | Class test that holds | Row | Lena's answer |
|---|---|---|---|
| "About the extra rework: ... I didn't send it in this conversation ... I rejected its result" (the injected rework mentioned) | the injected rework mentioned (P1's precedent: L-INJ on every mention, P1 F1 turns 10-18) | K10 | L-INJ `I don't know anything about that rework - I didn't ask for it.` |
| "The log also shows some command-line `root` commands ... check who else has access to this org." | not a question; no row is needed (protocol 4.4 answers questions); the harness's own CLI snapshots are a known actor (H6). A question about them would be K68 (A6) | none | none |
| the announced change: "this needs a change to the team, so I'll propose a plan for your approval first" | a structural change announced, no brief recorded, so no item nominated it (6.6) | K48 | EXT-NO `No, keep the team as it is.` |
| 1. "Which notes? ... the 2026-10-05 notes only, or all six meetings ... one combined list or one per meeting?" | which notes, or one list or several (either/or) | K62 | `1: Only 2026-10-05.md, the notes of the memo you just did: one list.` |
| 2. "Which actions go on the list? ... every action ... or only the ones that concern the ops team? ... I need the ops team's names" | which actions (either/or, and the names of a part) | K63 | `2: Every action item in those notes.` |
| 3. "One-off or every week? Do you want just this list, or a list each week alongside the memo?" | one-off or recurring (either/or; no team change proposed) | K64 | `3: Just this list.` |
| 4. "Format and 'one page'. Default: markdown, at most 350 words ... Do you want it as markdown, or as a PDF?" | the list's format with an offered default (either/or) | K66 | `4: The rest of your defaults are fine, the deliverables folder too.` |
| 5. "Same rules as the memo? Default: yes. ..." | the rules it follows, asked yes/no, with "yes" the default | K66 (yes/no form) | `5: Yes, the rest of your defaults are fine, the deliverables folder too.` |
| 6. "Where it goes and how it's checked. Default: the same `deliverables` folder, and the lead checks it ... Budget is about 12 runs" | folder, how it is checked by agents already on the team, a budget given as a default (a heading with a default) | K66 | `6: The rest of your defaults are fine, the deliverables folder too.` |

- **Every question maps,** and the announced change maps to K48, as the decision requires. No row was added or adjusted for the check:
  K62-K66 as written in section 4 hold all six questions.
- **The composed Lena line (turn 8),** by section 5's rule (EXT-NO first; then L-INJ, which the reply raised before its numbered list;
  then 1-6 with the reply's numbers; part 7's `I'll wait.` last, because the list is not delivered):

  `No, keep the team as it is. I don't know anything about that rework - I didn't ask for it. 1: Only 2026-10-05.md, the notes of the memo you just did: one list. 2: Every action item in those notes. 3: Just this list. 4: The rest of your defaults are fine, the deliverables folder too. 5: Yes, the rest of your defaults are fine, the deliverables folder too. 6: The rest of your defaults are fine, the deliverables folder too. I'll wait.`

- **Its record:** `turn 8 | rules EXT-NO + L-INJ + ANSWER | table rows K48, K10, K62, K63, K64, K66, K66 (yes/no form), K66 | facts: ...`.
  The frozen-form parser reads it with `unknown_rules` empty. The self-check reads this record (section 7).
- **Under amendment 1, ACT-REQ itself** reads `... from these notes (2026-10-05.md) for the ops team? ...`, so question 1 may not arise.
  The check above is run against the v1 reply, which is the hardest case on record.

**The review's variants, under the amended rows** (the variants table of `EV/amendment-1-review.md`, check 3; each assumed asked inside an
ACT-REQ window after amendment 1's ACT-REQ text, `<date>` the memo just accepted; the last two A1 examples are from finding A1):

| Variant | Row under the rulings | Lena's line | Record | Maps |
|---|---|---|---|---|
| R1 v1 Q1-Q6 plus the announced change | K48; K10; K62; K63 (Q2's "ops team's names" also by A4's clause); K64; K66; K66 (yes/no form); K66 | the composed line above (numbered, A9) | `K48, K10, K62, K63, K64, K66, K66 (yes/no form), K66` | yes |
| "Shall I have the writer do it?" | K65, a yes/no proposal that an agent on the team make it as a one-off (if it names a service, K67) | `Yes.` | `K65 (yes/no form)` | yes |
| "Should I set this up as a recurring service?" | arm R: K48. Arm C: K48 inside every ACT-REQ window (A5: fewer than three ACT-REQ lists have a LIST-KEEP line); K51 only after the third LIST-KEEP | `No, keep the team as it is.` (arm C after the threshold: `Yes, make it a service.`) | `K48` (`K51`) | yes, both arms |
| "Do you want me to write it myself?" | K65's yes/no form for a proposal that root write it itself (A3 (i)) | `No, someone already on the team.` | `K65 (yes/no form)` | yes |
| "Which team is ops?" | K63, "who the ops team is" (A4) | `Every action item in those notes.` | `K63` | yes |
| "Is ops the Platform team in the notes?" | K63's yes/no form, the proposition that it is the notes' team (A4) | `Yes, every action item in those notes.` | `K63 (yes/no form)` | yes |
| "Same format as the memo?" | K66's yes/no form (the proposed value is the default) | `Yes, the rest of your defaults are fine, the deliverables folder too.` | `K66 (yes/no form)` | yes |
| "Should it include past-due items from earlier meetings?" | K62's yes/no form (which meetings; the first test that holds decides) | `No, only <date>.md, the notes of the memo you just did: one list.` | `K62 (yes/no form)` | yes |
| "Shall I send it to the weekly-memo service as a request?" | K67 (A3 (ii)); in the week window K58 comes first | `No, just this list, by someone already on the team.` | `K67` | yes |
| "The lead, or shall I hire a list writer?" | precedence 1's either/or rule (A1), then K65's open line | `No, keep the team as it is. Someone already on the team.` | `K48, K65 (open form)` | yes |
| "Just this list, or shall I set up a weekly list service?" (A1's example) | precedence 1's either/or rule (A1), then K64's open line; in arm C after the threshold, K51 alone | `No, keep the team as it is. Just this list.` | `K48, K64 (open form)` | yes |
| "The lead or the writer?" | K65, an either/or of existing agents (A3 (iii)) | `That's up to the team.` | `K65 (either/or of existing agents)` | yes |
| arm C, after a K51 yes: "Where should each list go?" | K43, before K66 while the service is being defined (A2) | `One action list per request, in the deliverables folder.` | `K43` | yes |
| "Did you run those root CLI commands?" | K68's yes/no form (A6) | `No, I don't know anything about that.` | `K68 (yes/no form)` | yes |

Every variant maps under the amended rows. Two cases rest on readings taken here and flagged in section 4, both confirmed by the manager's
closing ruling (`EV/manager-decision-row-R1-t7.md`): arm C's K51 alone in an either/or (precedence 1), and the third list's delivery reply
still being "before" K51's threshold (K51's condition). The neighbouring either/or between a request of an existing service and a one-off
maps to K67's open form, `Just this list, by someone already on the team.`, recorded `K67 (open form)` (the same closing ruling).

## 7. Item 5: the harness items (A), (B), (C) and (D)
Each was written test-first. The new cases (`H/amend1_cases.py`, self-check part 5d) were run on the harness as frozen (RED) and after the
fix (GREEN). No file under `/Volumes/workspace/hirearchy/src/hirearchy/` or `/Volumes/workspace/hirearchy/.worktrees/p2-arm-c/src/` was
opened (`H/CHANGES.md`, "Amendment 1").

**(A) turn.sh's sequence check (protocol 3.2) was vacuous.**
- **Cause.** The frozen check parsed times with `strptime` forms that reject `+00:00`, which `snapshot_cli.sh` writes. It read any
  unparsed time as "no snapshot", so from turn 3 on it printed `after_turn sequential: checked (no snapshot taken: no org yet)` and
  passed.
- **The fix.** The check moved from turn.sh's inline Python into `H/turn_seqcheck.py`, which turn.sh calls in the same place. It parses
  ISO 8601 with `Z`, `+HH:MM`/`-HH:MM` or no offset (read as UTC), with up to 6 fraction digits.
- **It now fails closed (`STOP:`)** on:
  - an unparseable time in `turn-times.txt` or `quality/calls.txt`;
  - a missing `quality/calls.txt`;
  - no record of this turn's snapshot at all.
  It reads `checked (no snapshot taken: no org yet)` only when the snapshot's own record says `no org yet`.
- **The line forms are unchanged** (`after_turn sequential: checked (...)`, `STOP: snapshot before the boundary (...)`), so standing rule
  1 reads them as before.
- **RED:** `MISMATCH (A) turn.sh: a first snapshot at 2020-01-01T00:00:00.000000+00:00, before the turn's end + boundary: STOP`, which got
  `after_turn sequential: checked (no snapshot taken: no org yet)`. The unparseable-time case and the after-the-boundary case got the
  same line.
- **GREEN:** the three turn.sh cases and seven direct cases are `ok`. One of the direct cases is R1 v1's turn-3 record form, which now
  reads `checked (turn end 2026-10-29T10:44:32+00:00 + 20 s <= first snapshot 2026-10-29T10:44:53.169316+00:00)`.
- **R1 v1's turns 3-7** were checked by the facilitator's read-only substitute `EV/R1/facilitator/seqcheck.py`. Its output is in
  `EV/R1/seqcheck.txt` (turns 3-7 all `checked`). The decision asks this to be recorded here.

**(B) extract_mechanical.py crashed on an effort-stopped run's session (protocol 3.5).**
- **Cause.** The run `lead@20261029T104930658411` (exit -9, 12 s, 0 credits) has a session folder that holds `session.json` and no
  `messages.jsonl`. P1's extract reads such a session as 0 credits where it sums credits, but its revise_playbook section opens
  `messages.jsonl` unguarded. So `cost.txt` was never written, and `credits.txt` became a traceback.
- **The pin forces no edit, so none was made.** `extract_mechanical.py` is P1's file, pinned byte-identical to P1's harness (protocol 2.1
  and 10; `H/CHANGES.md` "Unchanged from P1"). Its md5 is still `73b27e25bd18ea9ec17ad5e64c7f6d1c`, equal to P1's `MD5SUMS` line, and the
  self-check checks this.
- **New `H/extract_mechanical_p2.py`.** `finish_stream.sh`'s `EM_ARGV` now runs it, with the same arguments. How it works:
  1. It runs P1's `main()` unchanged in the same process, with one name bound in that module only (`open`). Opening a missing
     `messages.jsonl` in a folder whose `session.json` exists reads as an empty file, which is what P1's own credit loop already does for
     it, and the folder is recorded.
  2. It checks every recorded folder against the `run-session-map.txt` the extract wrote. Each folder must be matched to exactly one run
     whose log has a line starting `# kiro: effort not set`. This is batch 1.1's mark, the one `effort_stops.py` counts.
  3. If every folder passes, it appends one line to `cost.txt`: `effort stops read as empty sessions (no messages.jsonl; '# kiro: effort
     not set' in the run log; relaunched uncharged, 0 credits): <k> (<run id> -> <session id>, ...)`. The line matches none of the
     patterns `cost_total.py` reads, so the credit figure is computed as before. The stopped run stays matched with 0 credits, so it
     triggers no unmatched-run estimate. The effort stop really was uncharged.
  4. Otherwise it fails closed: `cost.txt` becomes `cost.txt.unverified` with a `FAIL-CLOSED:` line naming the folder, and the step exits
     1. The `credits` step then has no figure, and protocol 11 already reads a missing figure as never low.
- **RED:** `MISMATCH (B) an effort-stopped run's session with no messages.jsonl: the finish's extract exits 0 and writes cost.txt`, which
  got `exit 1; FileNotFoundError: [Errno 2] No such file or directory: '.../org-kiro-sessions/h0/sess_boss-scribe/messages.jsonl'`.
- **GREEN:** cost.txt is written. The stop is counted as `1 (... -> sess_boss-scribe)`. `cost_total.py` reads `stream total credits: 3.50
  (assistant 1.00 + org runs 2.50)`. The same folder without the mark fails closed. The md5 pin holds.
- **On R1 v1's evidence** (read-only, output to `/tmp/hirearchy-p2/amend1-r1v1-check/`), the wrapper wrote cost.txt with `... 1
  (lead@20261029T104930658411 -> sess_f04502e1-4ad1-4466-87b6-479021f78e8b)`. `cost_total.py` read `stream total credits: 26.66
  (assistant 15.48 + org runs 11.19)`, which equals R1 v1's running figure.

**(C) S/injection/window.txt was left to the facilitator (protocol 3.4; E7 5.3's last bullet).**
- **Cause.** In R1 v1 the facilitator did not write the file, so the finish's `injection_files` step exited 2.
- **The fix.** `H/injection.sh` now runs the new `H/injection_window.py` right after E7's script, for the injection itself (`<memo-1 task
  id>`, with or without `--force`). It does not run for `--dry-run`, `--selftest`, `--stop` or `--poll-check`.
- **How the window is read.** The script reads E7's own log lines: the last `window start (request): <UTC>Z` and the first `window end
  (final progress): <UTC>Z` after it. It writes `S/injection/window.txt` as `<start> <end>`, each without its `Z`, on one line. This is
  E7's and P1's form. On the six P1 streams' logs it reproduces their `window.txt` byte for byte.
- **The failure paths.** A log without a window end writes nothing and prints a `NOTE:` line. An existing different `window.txt` is never
  overwritten: the script prints a `STOP:` line.
- **No facilitator step remains.** `finish_stream.sh` already copies `S/injection/` into `<label>/injection/`.
- **RED:** `MISMATCH (C) injection.sh writes S/injection/window.txt from the log, with no facilitator step`, which got `exit 0; window.txt
  None`.
- **GREEN:** `2026-10-29T10:48:27 2026-10-29T10:50:27` is written. This equals R1 v1's window per its log. `--stop`, a log with no end,
  and an existing different file behave as described above.

**(D) The md5 gate did not read the amendment files (protocol 0; the manager's D1).**
- **Cause.** `arm.sh`'s `md5gate_ok` checked `protocol.md`, the standing rules and every `MD5SUMS` line, and no amendment file. So
  standing rule A's check of the amendment md5s was the stream step's own, at the first and last turn only.
- **The fix.** `md5gate_ok` now also checks every `EV/protocol-amendment-*.md` and `EV/standing-rules-streams-amendment-*.md` (globs, so
  a later amendment is gated too, D1 (a)) against the `.md5` beside it (`<name>.md5`, first field). A missing `.md5` fails, with the line
  `md5 gate: <name>.md5 missing (<name>.md not frozen)`; a different one fails with `md5 gate: <name>.md differs from <name>.md5` (D1 (b)).
  The gate runs where it ran: `setup_stream.sh` (before anything is created), `turn.sh` (every turn, stream labels only), `next_stream.sh`,
  and `finish_stream.sh` (recorded in `setup.txt` after the last turn). So the amendment md5s are now checked at every turn.
- **The self-check and the dry runs are not affected.** `turn.sh` gates only labels that match `$STREAM_RE`, and the self-check's wrapper
  cases and both dry runs use `selfcheck-R`/`selfcheck-C` labels and call no setup, next or finish script. The full self-check below passed
  with the real amendment `.md5` files still absent.
- **Until the re-freeze writes the two `.md5` files, the gate fails for every stream label,** so `setup_stream.sh` refuses the restarted
  R1. This is the intended fail-closed behaviour (D1 (f)). The gate already failed before D1, on the harness files that `MD5SUMS` does not
  yet hold.
- **RED** (D1 (c); the cases in `H/amend1_cases.py` part (D), on a constructed EV copy under `/tmp/hirearchy-p2/`, the function called in
  isolation; the real `.md5` files were never written): `amend1_cases: 23 of 28 ok`, for example `MISMATCH (D) D1: protocol-amendment-1.md
  without its .md5: the gate fails, naming it`, which got `rc 0`.
- **GREEN:** `amend1_cases: 28 of 28 ok`. No amendment file passes, as before; both with matching `.md5` files pass; a missing or different
  `.md5` of either file fails; a later `protocol-amendment-2.md` without its `.md5` fails; an amendment edited after its `.md5` fails.

**The self-check, re-run in full** (`H/selfcheck.sh`, every part). The final line, the run time and every part are in
`EV/harness-selfcheck/SELFCHECK.md` ("Amendment 1" and "Amendment 1, review rulings"):
- part 5d is new: `amendment 1: sequence check, effort-stop cost, window.txt`, 21 cases, and 7 more for D1 (28);
- `lena_lines` gains 13 cases (each new row's record, the composed line, `ext_no_not_first`, K62-K66 not moving L0), and 6 more for the
  rulings (K67, K68, `K68 (yes/no form)`, `K65 (either/or of existing agents)`, A1's `K48, K6n (open form)` records, and K67/K68 bounding
  no window and moving no L0) (43);
- `selfcheck_cases` gains 1 case (the ACT-REQ window across the composed line), and 1 more for D2 (the week window across a K58 + K55 +
  K63-K66 answer line) (168).
`lena_lines` reads no line text, so A9's numbering has no parser case: the step checks it against section 5 when it writes the line.
Protocol 13.3's list gains part 5d and these cases.

## 8. Item 6: nothing else changes
No measure, reading, validity rule, aggregation, cost rule or pass rule changes:
- the six pass rules and their procedures (12.1);
- P2-E and P2-S (12.2);
- the gate-able measures (12.3);
- the readings (6);
- validity (8);
- the stage gate and cost (11);
- the aggregation (12.5);
- the re-derivation (13.1-13.2);
- PF-0 and PF-1 (12.6);
- the caps (4.7).
Of Lena's lines only ACT-REQ's text changes. Of the table, K62-K68 are added, and every v1 row keeps its line. Every v1 row keeps its
condition except K51, whose "repeated" is now defined (A5, section 4); its line is unchanged. The rulings changed no measure, reading,
validity rule, aggregation, cost or pass rule.

**The protocol sections this amendment touches, and how:**

| Section | What changes |
|---|---|
| 0 | its text is unchanged; the manager's decision departs from its bar on changing lines and rows after R1's first turn (section 1 above); the md5 gate (`md5gate_ok`) also checks every `protocol-amendment-*.md` and `standing-rules-streams-amendment-*.md` against its `.md5`, and a missing one fails (D1; section 7 (D)) |
| 3.2 | the sequence check is `turn_seqcheck.py` (same place, same line forms); it parses offsets and fails closed |
| 3.4 | `injection.sh` writes `S/injection/window.txt` after the injection |
| 3.5 | the finish's `extract_mechanical` step runs P1's file through `extract_mechanical_p2.py`; `cost.txt` gains the effort-stop count line |
| 4.3 | ACT-REQ's text (section 3 above); ITEM-SERVICE's arm-C condition reads K51's amended "repeated" (A5) |
| 4.4 | part 2 starts with EXT-NO in a line that answers an announced or proposed unnominated change together with other questions, or an either/or with a structural alternative (A1); answers to a numbered list of two or more questions carry its numbers in every line (A9); the numbering (section 5) |
| 4.5 | its last bullet now also names K62-K68 for an ACT-REQ list's questions, and K55, K58 and K63-K66 for the week list's (D2) |
| 4.8 | `ANSWER` covers K62-K68; the record forms of section 4 (A10) |
| 5 | rows K62-K68, their precedence (with the service rows, A2) and their week-window reading (D2); K51's condition (A5) (section 4) |
| 10 | the harness table gains `turn_seqcheck.py`, `extract_mechanical_p2.py`, `injection_window.py` and `amend1_cases.py`; `arm.sh`'s `md5gate_ok` gates the amendment files (D1) |
| 13.3 | the self-check gains part 5d (with D1's cases) and the new `lena_lines` and `selfcheck_cases` cases (with the rulings' and D2's) |

`EV/standing-rules-streams-amendment-1.md` holds rules A-G (A7): B, C and D amend standing rules 1, 4 and 6; A, E, F and G are new. No
other section changes. Protocol 2.1's pins are
unchanged: P1's `extract_mechanical.py` keeps its md5, and the md5 is recorded against the pin in `H/CHANGES.md`.

## 9. Item 7: how the facilitator and every later step read the protocol
- **What to read.** `EV/protocol.md` as amended by this file, and `EV/standing-rules-streams.md` as amended by
  `EV/standing-rules-streams-amendment-1.md`. Where an amendment and the text it amends differ, the amendment wins.
- **Who reads them.** Every later step reads all four files: each stream step before its first turn, the stage gate, the teardown, the
  scoring and the commit. Any later amendment N wins over this one where they differ.
- **The md5 gate does the check (D1 (d)).** `arm.sh`'s `md5gate_ok` checks `md5 -q` of every `protocol-amendment-*.md` and
  `standing-rules-streams-amendment-*.md` against its `.md5`, as it does for `protocol.md`, and a missing `.md5` fails (section 7 (D)). It
  runs in `setup_stream.sh`, in `turn.sh` before every turn of a stream label, in `next_stream.sh` and in `finish_stream.sh`. A failure
  stops the step with a `warning`. Each stream step still names both amendment md5s in its first record.
- **What the re-freeze must do,** after the rulings are applied and checked, and outside this pass:
  - write `protocol-amendment-1.md5` and `standing-rules-streams-amendment-1.md5` before the restarted R1's setup (D1 (f)); until then
    `setup_stream.sh` refuses, which is the intended fail-closed behaviour;
  - write `standing-rules-streams.md5`, with a check that preflight's written copy equals the frozen value
    (`EV/preflight/freeze-gap-standing-rules-md5.md`; the decision's item 5; A8);
  - rewrite `harness/MD5SUMS`. New files: `amend1_cases.py`, `turn_seqcheck.py`, `extract_mechanical_p2.py`, `injection_window.py`.
    Changed files: `arm.sh` (D1 (e)), `turn.sh`, `injection.sh`, `finish_stream.sh`, `selfcheck.sh`, `lena_lines.py`, `selfcheck_cases.py`,
    `CHANGES.md`;
  - keep the attempt-2 freeze files under `freeze-attempt-2/`;
  - write `freeze.txt` naming the manager's decision as its basis.
- **Before the restarted R1's setup** (A8), the stream step moves `EV/R1/` to `EV/R1-v1/` (the decision's "status of R1 v1").
  `setup_stream.sh` refuses a label whose `sandbox-path.txt` exists ("REFUSED: ... was set up already"), so the move is a precondition of
  the restart. This pass did not move or edit `EV/R1/`.
- **The review's open points are closed** by the manager's rulings: the gate checks the amendment files (D1), and the week list gets K63-K66
  with K62's class read as K55 (D2, section 4).
