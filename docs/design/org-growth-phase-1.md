# Org growth, Phase 1: the itemized playbook (technical design)

Status: design, revision 4 (the third and last fix pass, after design review 3 of the relaunch `wf_7425beced1ec8bb4`, under the manager's
binding directives of passes 3 and 4; the first run `wf_b5e00b63cdb0f479` wrote nothing; how each finding of review 1 (30), review 2 (25) and
review 3 (11) was resolved is in section 23), **approved with the manager's binding amendments B1-B10** after design review 4 (0 HIGH, 4
MEDIUM, 5 LOW), when the manager closed the design loop by decision; section 24 lists each amendment and where it landed, and where an
amendment and older text of this file differ, the amendment wins; section 25 records the design **as built** (the planner's corrections PC-1 to PC-12 and the build's deviations) and wins over older text in turn. Branch
`feat/org-growth-phase-1`, worktree `/Volumes/workspace/hirearchy/.worktrees/org-growth-p1`, base `main` = `05cfc2bf` (0a to 0a.5, 0b and 0b.1).
Every function named below was read at `05cfc2bf` in the worktree. `SRC` is `src/hirearchy/`, `RESEARCH` is
`/Volumes/workspace/hirearchy/docs/research/org-growth/`. Binding briefs: `RESEARCH/phase-1-resume-brief.md` (wins) and `RESEARCH/phase-1-brief.md`.

Where the brief's 14 required items are (brief item -> section): 1 -> 4, 2 -> 5, 3 -> 6, 4 -> 7, 5 -> 8, 6 -> 9, 7 -> 10, 8 -> 11, 9 -> 12,
10 -> 14, 11 -> 15 (with 13, clause 2's refusals, and 16, no bypass), 12 -> 17, 13 -> 18, 14 -> 21. The six mandatory review checks are audited in 22;
the review resolutions are in 23; the manager's amendments B1-B10 are in 24.

## 1. Overview

Phase 1 turns the playbook of a service from one free text that the owner rewrites whole into a list of **items** with stable ids (`P<k>`), of two
kinds: a **step** (ordered procedure) and a **rule** (`WHEN <condition> THEN <action> WHY <R ids>; <C ids>`). `PLAYBOOK.md` stays the one file,
rendered from the items and capped at 1000 words; it is also the item file, so nothing new is stored beside it. The owner changes it one item at a
time with `revise_playbook(op=add|edit|retire|restore|move)`, and every change is judged by today's evidence gate, applied to that one item: rule
(b) (two different cases the human client rejected on the same criterion or assertion) or rule (c) (the item is the own words of a criterion the
client confirmed); rule (a) has no data path yet and admits nothing. 0a.2's line-level admission (P1) is folded into this: the item is the unit, its
`WHY` is written by the runtime from the admission, and P1's whole-text form goes. An admitted item enters as `new` and is **watched**: derived from
the files on every read, it stays `new` until k (3, or more when the failure's recurrence rate is known) later cases, each judged by the human
client on whichever of its deliveries the client judged first, pass without a related rejection (one recorded before the k-th of those verdicts
counts, whatever delivery it is on, and once the item is `kept` its watch is over); the first related rejection makes it `warning`
and tells the owner; the second (read over every later delivery while the warned text is live: the warned window, B1) makes the runtime,
as the `services` single writer, retire it and restore its previous text, and tell the owner
and the parent. Retiring, weakening or restoring an item that covers a criterion or an assertion needs the parent's acknowledgement; the cap
offers retire candidates; a change of more than about 30% of the words is refused with "split it". Lessons take an after-action-review shape and
stay the owner's view. Clause 2 of the exit criterion gets two refusals of its own: root's next new request of a service waits until every human
rejection since the previous request has the user's recorded answer, and root's human accept of a case waits while an earlier human rejection of
that case has none (unless the answer itself waits for that accept, 13.2). The skill changes in one line; ROOT_INSTRUCTIONS does not change.

**The binding design principle** (go-no-go-0b 4; E3 to E7): every guarantee of the exit criterion is built on a tool's refusal, a value the
runtime writes, or a check derived from the files. Text (skill, prompts, docstrings) only says what the refusals already enforce, and every place
that still rests on text is listed with its reason (section 15).

**Exit criterion (08 section 8, row 1), as this design reads it.** On paired scripted streams these pre-registered mechanical guarantees hold:
- **G1, no wrong rule survives its watch:** no item with a related human rejection in its watch reaches `kept`; every item with two is retired by
  the runtime and its previous text restored; no gated item enters without human-tier evidence (sections 8, 15).
- **G2, within one request every human reject has a regression assertion and a contract proposal the user answered:** the assertion `R<k>` is
  derived from the human rejection; the answer (an answering contract version or a human link) is recorded before the service's next new request,
  which is refused until it is (13.1), and before root's human accept of the same case (13.2). The last request of a service has no next request:
  there the accept refusal narrows the gap, and the rest is a derived check at the stream's end, not a refusal (declared limit L10, 21.1 G2(b)).
First-delivery accepts are the secondary outcome.

**What this phase builds on (0b.1 is the current product).** 0b.1 (`05cfc2bf`) changed what Phase 1 reads:
- **F-G0-2** (`5c9638b3`): `user_spend` and `case_spend` count a user grant's held runs while a case is open or blocked (`reflection/api.py`,
  `user_committed`). Ruling R-0b1-1 moved one pre-registered value: E7 s2 "after the grant 68df" reads 14, over the 13 approved, with `OVER_APPROVED`.
  `case_total`'s head "N runs used of M handed down" is unchanged (0b.1 11, backlog). Phase 1 changes no spend figure; the study's spend ledger
  re-derives these figures from the 0b and 0b.1 design texts (section 18.6, F-G0-4).
- **F-G0-1** (`dc36817a`, `cf818259`): when several deliveries equal the file, the given delivery is the one with a human-tier verdict, else the latest.
  The watch does not read the given delivery: it reads every delivery of a case and the verdicts on each, and counts the case through the
  delivery the client judged first (`judged(c)`, section 3), so it is unaffected.
- **F-G0-3** (`05cfc2bf`): `FsMailbox` reads a message that moved between the listing and the read at its new place. The watch and the new refusals
  read mail through `MailboxReader` and inherit it.
- **E7S3-6** (`38d32f09`): a blocked result is no delivery. The watch follows it: a clean case needs a judged delivery (a `done` result), while a
  related rejection counts on any result (8.2), so a file copied from a blocked result can warn a rule but never keep one.

## 2. Technology stack (locked)

Python 3.11; the existing packages only (FastMCP `mcp`, PyYAML); the standard library's `math`, `hashlib`, `fractions`, and `fcntl` and `os` for
the playbook write's lock and exclusive archive (4.3; POSIX, as the product's `os.O_NOFOLLOW` reads already are). `uv`, `pytest`,
`mypy==2.4.0 --strict`, `import-linter==2.15`, `scripts/check.sh`. No new runtime dependency, no new package, no new dependency edge between
packages: `services` (L7) keeps not importing `reflection` (L8); the derived facts `services` needs (the item gate, the watch) come through its own
port `ServiceEvidence`, implemented in `reflection/_evidence.py` and wired in `app`, as today. No ledger, no new file kind: the item file is
`PLAYBOOK.md` and its `history/` versions; the acknowledgement is a note with one new header field (section 9). The one new file is the
playbook's lock, `services/<name>/.tmp-playbook.lock`: empty, git-ignored, never read, holding no state (4.3). Strict TDD under the owner's test
policy: FAST scoped tests per commit, SCOPED tests per FEAT and per fix pass, one full `scripts/check.sh` in final validation after a rebase onto
`main`, no rerun after a no-op rebase.

## 3. Shared definitions (each defined once; homes are new unless marked)

| Name | Home | Definition |
|---|---|---|
| item | `services.api.PlaybookItem` | One entry of an item-format playbook: `id` (`P<k>`), `kind` (`step` or `rule`), `section` (the heading line it sits under, `""` for the text before the first heading), `text` (a step's words, or a rule's `THEN`), `when` (a rule's condition; `"always"` when none), `why` (the R and C ids the runtime wrote, the frontmatter `why` entry of 4.2; `()` for an item never gated). |
| item-format playbook | `services.api` | A `PLAYBOOK.md` whose frontmatter has `items_max`. Any other playbook is **legacy** (every playbook written before Phase 1). |
| item id | `services.api` | `P<k>`, k >= 1; the next id is `items_max + 1`; an id is never reused, not even after a retire. Ids are compared upper-case. |
| content words | `services.api.content_words` | The words (`str.split`) of every live item's `text` and `when` (a `when` of `"always"` counts 0) and of the section headings. Item markers, the `WHEN`/`THEN`/`WHY` keywords and the ids after `WHY` are not counted. For a legacy body: `len(body.split())`, today's count. |
| text key | `services.api.line_key` (exists) | The letters and digits of a text, case-folded, after its leading markdown markers, joined into one string. Used, unchanged, for the legacy marks of the timeline, the migration's loss check (4.4), the lenient text comparisons of 8.6 and the carried watches (below); never to decide that an edit is formatting only. The text key of an **item** is the key of its `text` field: a step's text, a rule's `then` (its `when` is not part of it), so a rule re-added as a step with the same words has the same text key (B2). (The acknowledgement's **text hash**, 9.2, is a different value.) |
| text tokens | `services.api.text_tokens` (new, pure) | ``[tok for i, line in enumerate(t.splitlines()) for tok in TOKEN.findall(plain(strip_markers(line) if i else line).casefold())]`` with ``TOKEN = re.compile(r"\d+(?:[.,:/-]\d+)*\|[^\W\d_]+\|[^\w\s.,;:!?'\"()\[\]*_`]")`` and ``plain(line) = re.sub(r"^\s*#+", "", line.replace("~~", ""))`` (B9): the numbers with their inner separators kept (`3.5`, `3,5`, `35`, `1`, `2`, `2024-05-01` are five different tokens or token lists), the runs of letters (any script), and **every other symbol as a token of its own** (`<`, `>`, `=`, `≠`, `%`, `$`, `€`, `+`, `-`, `✓`, `\|`, ...). Only whitespace, sentence punctuation (`. , ; : ! ? ' " ( ) [ ]`), the markdown emphasis and code markers (`*`, `_`, the backtick), the strikethrough pair `~~` and the `#` run at the start of a line are dropped (a single `~`, as in `~5`, and a `#` inside a line, as in `#3`, are tokens: B9), and, **on continuation lines only** (the second and later lines, which only migrated items have, 4.4), the leading list and heading markers (`strip_markers`). An item's first line is the owner's or the migration's words without any list marker (the runtime renders the marker), so a leading `>`, `+ `, `- `, `• `, `N. ` or `[x]` there is the owner's own symbol and stays a token. Two texts with equal tokens differ only in spacing, case, markdown and sentence punctuation (and, on a continuation line, its own list marker: L13). |
| gated change | `services._ops` | An add, an edit whose text tokens (of `text`, and of `when` for a rule) differ from the old ones, or an owner's restore of a text no client-written version had: it needs evidence (section 6). |
| exempt change | `services._ops` | A move, an edit whose text tokens are unchanged (a formatting fix), the first version, the migration (and the repair migration), the runtime's watch retire, a restore of a client-written text. |
| live | `services.api` | An item is live in a version when that version's body holds it. Its **live-from** is the `revised` time of the version that gave it its current text. |
| watched change | `reflection._watch` | While the item is in its watch (section 8): its latest change that restarts the watch, which is its latest gated change, or a later exempt restore of a client-written text (8.1, rule W2). Its **watched text** is the text that change gave it; a formatting edit, a move or a repair migration keeps the watched change and makes the item's new text its watched text (rule W1). The watched change's **live-from** is the `revised` time of the version that wrote it (a W1 change does not move it); "the live-from" below means this one. Its **watch start** is the live-from of the first gated change since the item last was not watched, or the watch start of a watch carried to it (below). |
| carried watch | `reflection._watch` | Derived, no stored link. (i) An owner's `restore` of an item that its owner retired while it was in `warning`, or an owner's `add` or **gated `edit`** (of any live item) whose new text key equals the text key of such a retired text, continues that watch: same watch start, its related rejections counted (carried as they are; its own window, from its own live-from, adds the later ones). An edited item that carries a watch also keeps its own related rejections: its related set is the union of both, derived, as D4 does for a restart (B2). (ii) An item of a repair migration (4.4) whose text key equals the text key of an item that was live and in its watch in the last parseable version before the repair, rendered with its marker but without its list marker, continues that item's watch (8.1). |
| refs | `reflection._watch` | Of an item text: its `why` entry (gated items), else the `C<k>` and `R<k>` tokens of its text (`quoting_lines`' token rule; legacy, v1 and migrated items), plus, for every `R<k>` among them, the `C<k>` ids that assertion was about when the text went live (`Assertion.about` over the links created before the text's live-from), so the refs of a text never change. The watch reads the refs of the text at the watch start (8.4) and of the text live when a rejected result was created (related rejection). |
| coverage | `reflection._watch` | Of an item: `{C in refs : C is a current criterion} ∪ {R in refs : R.link == "confirmed" and (R.about holds a current criterion, or R.about holds no criterion at all)}`. A removed criterion is no coverage, an assertion marked "no lasting rule" (`link == "none"`) is none, and neither is a confirmed assertion that is only about removed criteria: the client lowered that bar herself. |
| subjects of a rejection | `reflection._watch` | Of a human-tier rejection `R<k>`: `R<k>` itself; the ids its effective human link names (`Assertion.about`, and the `R<j>` a "same as" link names); the `about` id of its answering contract version, the ids that version's link names or would name (`services._criteria.answer_ids`, so a failed link write changes nothing) and the ids it removes (`Cause.removes`' rule, `services._criteria.amendment_ids`); and the **lineage as of t** of every `C<k>` among them, where t is the time of the rejection's answer (the created time of its first human link, or the `defined` time of its answering version, whichever is earlier; for a corrected link, that link's time), so a later re-add of a criterion's text cannot change the subjects of a rejection already answered (B4). A rejection is **pending** while it has no human link and no answering version, or while its human link names an earlier rejection that is pending ("same as R<j>": `Assertion.about` resolves through R<j>'s links, so its subjects are not known until R<j> is answered); a pending rejection has subjects `{R<k>}`. (This is the watch's notion; clause 2's `unanswered`, 13, counts a "same as" link as the user's answer, and R<j>'s own answer is due by the same rule.) Once a rejection is not pending its subjects are fixed: P2's one-answer rule refuses a second answer (`ANSWERED`, `CONFIRMS_ANSWERED`), and the one record that can still change them is a corrected link (a second human link, 0a.2 5.9; 8.2). |
| lineage of a criterion as of a time t | `reflection._watch` | The criteria it replaced, as the contract stood at t (B4): the criteria removed by the **latest** stored contract version whose `defined` is at or before t and that added `C<k>`'s text (the text is present in that version and absent from the version before it; `number_criteria` gives a text that comes back its first id, so a re-added text is found by this test, not by a new id), and their lineage as of t in turn, each id visited once (so a cycle, C6 -> C10 -> C6, ends). An answer to one question is one change (D3), so what it removed is what it replaced. A criterion with no such version at or before t (a v1 criterion never removed and re-added, or a user-initiated one) has none as of t. So a rejection about the new wording of a criterion relates to the rules that cited the old one, and a v1 text that one answer removed and a later answer re-added has, after the re-add, the lineage of what the re-adding answer removed. |
| candidate case | `reflection._watch` | Of a watched change: a case (0b 3) other than the cases of the change's `why` assertions, with a `done` result created after the watched change's live-from. Candidates are ordered by the `created` time of their first such `done` result. A new candidate's first done time is always later than an existing one's, so the first k candidates are fixed once k exist. |
| judged delivery `judged(c)`, `J(c)` | `reflection._watch` | Of a candidate c: the delivery of c whose `done` result was created after the watched change's live-from and that carries c's first counted verdict, the human-tier verdict with the lowest note id among the verdicts on those deliveries (0b's `Delivery.verdicts`, `counted` = human tier, L4). Verdict notes are only appended, with growing ids, so `judged(c)` never changes once it exists; a verdict recorded later on an earlier, superseded delivery has a higher id and changes nothing. A delivery superseded without a verdict holds nothing. `J(c)` is the `created` time of `judged(c)`'s `done` result. |
| last judged delivery `E` | `reflection._watch` | `max(J(c))` over the first k candidates. Undefined until each of them has `judged(c)`. Once defined it never moves (the first k candidates and their `J(c)` are fixed), so a late verdict never pulls it back. |
| closing time `D` | `reflection._watch` | The created time of the latest of the first k candidates' judging verdicts (the verdict note that makes `judged(c)`). Defined exactly when `E` is and, like `E`, fixed once defined (verdict notes are only appended). "Recorded before `D`" compares message ids, which begin with the creation stamp, so two notes never tie. |
| window | `reflection._watch` | Of a watched change: a human-tier rejection is **in the window** when its rejected result was created at or after the watch start, and either that result was created at or before `E` or the rejection note was created before `D`. Open-ended while `E` is undefined (every human rejection on a result created at or after the watch start). The rejected result is the rejected task's latest result created before the rejection note (done or blocked). A watch whose watched change was restarted (8.1 W2) has the union of its watched changes' windows: the first from the watch start, each later one with its own `E` and `D` and from its own live-from in place of the watch start, so a restart keeps every rejection found so far and pulls in none that was outside. The window decides `new -> kept` and the first related rejection; an item already in `warning` reads its second over the **warned window** (next row). |
| warned window | `reflection._watch` | Of an item in `warning` (B1): every human-tier rejection on a result created at or after the start of the watch in which the item was warned, recorded while the item is live in that watch's watched text (live with the watched text's tokens under its id or the carried id, W1). It has no `E`, `D` or `K` bound, so it only grows; a restart (W2) and a carried watch carry it as they carry the window (D4, section 3's union). A warned item's related rejections are those of its window plus those of its warned window; the second retires it whatever order root recorded the k-th verdict and a later delivery's rejection in. |
| end of the watch `K` | `reflection._watch` | The created time of the earliest record (a verdict note, a link note or an answering contract version of the service) at or after `D` such that the files created up to and including it derive `kept` (8.1). Undefined while the item has not reached `kept`; fixed once defined (a later record cannot change what the files up to `K` derive). From `K` on the watch is over: the window is read only for rejections recorded at or before `K`, so nothing recorded later joins it (8.1, the monotonicity property). `watch_states` finds `K` by testing the `kept` condition at each such record's time in order, from `D` on; every record carries its creation time (message ids, the contract version's `defined`, `Contract.defined`, written once per version, and the playbook version's `revised`; never the contract's `created`, which every version carries from v1, `services/_define.py`), compared as aware datetimes (`stamp_of(message id)` against `parse_time(defined)` and `parse_time(revised)`); at an equal microsecond a contract version comes before the link note `define_service` writes after it (B3). Never defined for a warned item (B1). |
| related rejection | `reflection._watch` | Of an item in its watch: a human-tier rejection in the window (for an item already in `warning`, in the window or its warned window, B1) that is not pending, whose rejected result was created while text T of the item was live, and whose subjects meet T's refs. Derived, with no `applied` ids (08 4.2). |
| judged case, delivery, counted verdict | `reflection` (0b 3, exists) | As 0b defines them; the watch reads them from mail only (8.2). |
| clean case | `reflection._watch` | Of an item's watched change: a candidate c that has `judged(c)` and none of whose human rejections in the window is related or pending. |
| k, r | `reflection._watch` | Section 8.4. |
| states | `reflection._watch` | `new`, `warning`, `retired`, `restored`, and `kept` (section 8.1). |

## 4. The item data model, rendered and stored (brief item 1)

### 4.1 The file is the items

`<owner>/services/<name>/PLAYBOOK.md` keeps its path, its frontmatter and its `history/PLAYBOOK.v<n>.md` archive. In item format the body is
canonical markdown that the runtime renders and parses:

```
## Steps
1. [P1] Read the request in your prompt: its inputs, every acceptance criterion and the deliverable. ...
2. [P2] Delegate to `writer` (Writer) with `budget=5`: its part of the request, with the criteria it must meet.
3. [P12] Before the review, compare every Due cell with the notes' own words. (WHY R2, R3; C6)

## Budget plan
- [P8] Request budget: 12 runs (the contract's). ...

## Rules
- [P9] WHEN always THEN The memo starts with a one-line 'Summary:' of the meeting, then the Decisions section. WHY R1; C9
- [P13] WHEN a Due cell in the notes is relative ('next week') THEN convert it from the meeting date and say so in the review task. WHY R2, R3; C6
```
(The example's words are a memo's; the format is not.)

Rendering rules (`services._items.render_items`, pure):
- **Sections** in their stored order. Every section renders its heading line, verbatim, whether or not it holds a live item (a heading with
  nothing under it is part of the text, so a legacy title, two consecutive headings or a trailing heading survive the migration, and a restored
  item finds its section again). The section `""` (text before the first heading of a legacy body) renders no heading line. One blank line
  precedes every heading line except at the start of the body. **Two exceptions, both the product's own sections:** the rules section, always the
  last one and headed `## Rules`, renders only while a rule is live; and a `## Steps` section the runtime creates for an add (the placement rule
  below) is an ordinary section from then on.
- **A step** in a section whose first item was numbered renders `<n>. [P<k>] <first line>`, else `- [P<k>] <first line>`; a gated step's last
  line ends with ` (WHY <ids>)`. Every further line of the item (only legacy and migrated items have one) renders as exactly 3 spaces followed by
  the line verbatim; a blank line inside an item renders empty.
- **A rule** renders `- [P<k>] WHEN <when> THEN <text> WHY <R ids>; <C ids>` on one line (ids sorted by number, `; ` between the two groups, a
  group that is empty is left out).
- **`WHY`** is rendered from the frontmatter `why` entry (4.2), which the runtime writes from the admission (6.3), never from the owner's input.
  The body's `WHY` is rendering only; the frontmatter entry is canonical.

Parsing (`services._items.parse_items(body, meta)`, pure) reads only item-format bodies, line by line, with this grammar:
- a **heading** is a column-0 line matching `^#{1,6}(\s|$)`: it starts a section;
- an **item** starts at a column-0 line matching `^(\d+\. |- )\[P(\d+)\] `; its kind is `rule` when its id is in the frontmatter `rules`, else
  `step` (the kind is never guessed from the words);
- a **continuation** is a line that starts with exactly 3 spaces (the 3 are stripped; the rest is the item's next line, verbatim) or a blank line
  followed, before the next item or heading, by such a line; other blank lines are separators and belong to no item;
- **any other line** (a column-0 line that is neither, a line before the first item of a section that is not blank) is a parse error.

A rule's `when`/`text` are split at the first ` THEN ` after the leading `WHEN `, and its trailing ` WHY <ids>` is stripped only when it equals the
rendering of the item's frontmatter `why` entry; a step's trailing ` (WHY <ids>)` likewise. An item without a `why` entry keeps whatever its words
end with, so a migrated text that ends in `(WHY C6)` stays words, and a suffix that differs from the canonical entry is a parse error, never a
second source of `WHY`. Input validation forbids a capitalised `THEN` inside a rule's `when` (19.2), the one place where it would be read as the
separator; a `WHEN`, `THEN` or `WHY` anywhere else in an owner's words stays words, because the parser splits a rule only at the first ` THEN `
after its leading `WHEN ` and strips only a suffix equal to the canonical `WHY`. When the
frontmatter's `rules` is not empty, the last section must be headed `## Rules` and hold exactly the live rule items, in order; a rule id anywhere
else, or a step in that section, is a parse error. So a legacy section that happens to be headed `## Rules` (any level) is an ordinary step
section, and the product's rules section, when there is one, always comes after it. A body that does not parse (a hand edit of a file `services/`
owns) gives `ItemsParse.error` (`"line {n}: {why}"`) instead of items, never an exception; 19.1 and 4.4 say what each reader and writer does with
it. The round trip is an invariant: `parse_items(render_items(x)) == x` for every item list `x` (unit-tested over 4.4's corpus and over seeded
random item lists, 20), and `RuleItemReviser` and the watch settler assert `parse_items(render_items(items), meta) == items` on the items they are
about to write, before every write (an `AssertionError`, never a user path, like the migration's loss check: a body the parser would reject is
never written).

**Placement** (`services._items`, pure; used by `add` and `restore`):
- a step `add` without `after` goes after the last item of the first section headed `## Steps`; else after the last item of the first section whose
  first item is numbered; else into a new `## Steps` section placed first (after the `""` section, if any). With `after`, which must be a live
  **step** (a rule id is PB-ARGS `after={x} is a rule: a step goes after a step (or leave after out)`, 5.3), right after that step, in its
  section, so a step can never land in the product's `## Rules` section;
- a rule `add` goes to the end of the rules section (created as the last section when no rule is live), or right after `after` (a live rule);
- a restored item goes back to the section it was in when it was last live (sections are never deleted, renamed or reordered by any op, so the
  section is found again by its heading line and its occurrence among headings with the same line), right after the nearest item that preceded
  it there in that version and is still live in that section, else first in that section. A restored rule goes to the rules section by the rule
  `add`'s rule, after the nearest preceding rule that is still live.
- Two normal-form rules keep the round trip exact: the `""` section is in the body only while it holds a live item (a restore into it recreates
  it first), and a section's numbering is read from its first item, so a section emptied by retires renders its next item numbered only when its
  heading is `## Steps` (a bullet otherwise). Neither changes a word.

### 4.2 Frontmatter of a version (the only stored state, all in the item file)

Kept as today: `service`, `version`, `revised`, `by`, `reason`, `evidence`, `admitted`, `restores`. New, written by the runtime on every
item-format version:

| Key | Value | Written by |
|---|---|---|
| `items_max` | the highest item number ever used (monotonic; the next id is `P<items_max + 1>`) | every item-format write |
| `rules` | the ids of the live rule items, in body order | every item-format write |
| `why` | a map from every live gated item's id to its sorted `WHY` ids (`{P12: [R2, R3, C6], P13: [R2, R3, C6]}`); `{}` when none. The canonical `WHY`: the body's rendering is checked against it (4.1) | every item-format write |
| `op` | `first`, `migrate`, `add`, `edit`, `retire`, `restore`, `move`, `watch` | every item-format write |
| `item` | the id the op changed (absent for `first` and `migrate`) | ops on one item |
| `admitted` | `b`, `c`, `first`, `migrate`, `exempt`, `restore`, `watch` (values `b`, `c`, `first`, `restore` keep today's meaning) | every write |
| `related` | the `R<k>` ids the watch retire rests on | `op: watch` only |
| `acknowledged` | the id of the parent's acknowledgement note | guarded retire, edit or restore only (section 9) |
| `restores` | the version whose text of `item` came back | `restore`, and `watch` when a previous text exists |

`by` is the owner's address, `root` for a client-written version, `runtime (watch)` for the watch retire and `runtime (migration)` for the migration
(both contain a space and a parenthesis, so no agent address can be equal to them: `kernel.NAME_RE`). `by` is a label, not an address: the
`service.revise` event of a runtime write has `actor` = `kernel.RUNTIME` (`"runtime"`, an address every observability filter knows) and carries
the label in its `by` field; an owner's or root's write keeps `actor` = `by`, as today.

Nothing else is stored: the states `new`, `warning` and `kept`, every count, every related rejection and k are derived on each read (section 8).
`retired` and `restored` are facts of the item file (an op wrote them).

`services.api.Playbook` gains `items: tuple[PlaybookItem, ...] | None` (None for a legacy body), `sections` (heading lines in order, with whether
each is numbered), `items_max`, `rules`, `why`, `op`, `item`, `related`, `acknowledged` and `parse_error` (`""`, or why an item-format body did
not parse). They are filled where every `PLAYBOOK.md` is read today, `services/_parse.py:playbook_of(meta, body, path)`, which calls
`parse_items(body, meta)` when `items_max` is in `meta`. `ServiceCatalog.read_playbook` never raises for a body that does not parse: it fills
`parse_error`, and each reader acts on it (19.1).

### 4.3 Single writer and history

Every write goes through `services._store.FsServiceStore.write_playbook` (archive the current file to `history/PLAYBOOK.v<n>.md`, then write the
next atomically) via `services._texts.EventedPlaybookWriter`, which emits `service.revise` (fields unchanged; `actor` is `by` for an owner's
or root's write and `kernel.RUNTIME` for the runtime's, 4.2). The only
writers are `services` commands: `define_service` (v1 from the client), `revise_playbook` (the owner's ops and the migration), and the watch
settler that `feedback(confirms=...)` and `define_service(answers=...)` call (8.5). `orgfiles` keeps `services/**` closed to the `write`
tool (unchanged). The history of an item is derived from the stored versions (`ServiceStore.versions(owner, name, "PLAYBOOK")`), oldest first;
git (a commit after every run) holds the same files and is not read.

**Two processes, one writer module: a compare-and-swap under a lock.** Before Phase 1 the owner was a playbook's only writer after v1, so its writes
never raced. The watch settler adds a second process: it runs in root's MCP or CLI process (inside `feedback` and `define_service`) while the
owner's `revise_playbook` runs in the agent's MCP process. Rule R9 (single writer per file) still holds, because `services` stays the only package
that writes `PLAYBOOK.md`; what is new is that two processes run that package's code on one file, and the lock serialises them. The change is
inside `write_playbook`, whose signature does not change (`ServiceStore` already has R7's 8 methods, so no method is added):
1. Take an exclusive `fcntl.flock` on `services/<name>/.tmp-playbook.lock` (created if missing, never deleted). The `.tmp-` prefix is one an
   organization's `.gitignore` has ignored since `Org.init` (`INITIAL_IGNORE_LINES`, for the atomic writer's temp files), so `git add -A` does not
   commit it; `FILE_SHAPE` and `visible()` ignore it, so no reader, continuation or listing sees it.
2. Read the current file's frontmatter `version`. It must equal `archive_version`, the version the caller judged (no file at all when
   `archive_version` is None). Otherwise raise `services.api.PlaybookRace(current)` (an `OrgError` subclass carrying the current version) and
   write nothing.
3. Archive the current bytes to `history/PLAYBOOK.v<archive_version>.md` by an exclusive create (`O_CREAT|O_EXCL` semantics, done atomically:
   the bytes go to a temp file, which is hard-linked to the history name, a link that fails with `FileExistsError` when the name exists; then the
   temp file is removed). A history file is never overwritten. An existing history file whose bytes equal the current file's is the leftover of
   an interrupted write (archived, then the main write failed) and is accepted; any other existing file raises `PlaybookRace`.
4. Write the new file atomically (today's writer), then release the lock.
`MemoryServiceStore` (`services/testing.py`) makes the same check without a lock: the current `version` must equal `archive_version`, and a history
key that exists with other text raises `PlaybookRace`. `write_contract` is unchanged (one writer per contract: the parent). On `PlaybookRace`,
`RuleItemReviser` refuses with PB-RACE (5.3) and the settler records the item as `failed` (8.5); neither retries in the same call.

### 4.4 Migration of today's free-text playbooks (no data loss)

**When.** A legacy playbook is never rewritten by a read. The first `revise_playbook` call on a legacy playbook that passes the argument checks of
5.1 (whatever its op, and even one that is then refused by the gate) first writes the migration as the next version (`op: migrate`,
`admitted: migrate`, `by: runtime (migration)`, reason `the free-text v<n> as <m> items (no change of words)`), then judges the op against it. A
refused op leaves the migration written: it changes no word and every later read sees the same ids. `define_service(playbook=...)` writes v1 in
item format directly (`op: first`), and so does the blueprint's `apply_org` through it.

**Its record.** The migration is a playbook version like any other: `EventedPlaybookWriter` emits `service.revise` for it (`actor` `runtime`,
`by` `runtime (migration)`, `admitted` `migrate`). The client gets one quiet note per call, never two: when the op that triggered the migration
is written, the op's note (5.2) starts `Playbook v{n-1} is the free text of v{n-2} as {m} items (P1-P{m}), no change of words.`; when that op is
refused, the migration gets its own quiet note, title `playbook of {service}: v{n} (items)`, body `The free text of v{n-1} as {m} items
(P1-P{m}), no change of words. Nothing else changed.` So every playbook version still has its note to the client.

**How (`services._items.migrate_body`, pure).** The legacy body is split into blocks, every non-blank line in exactly one block:
- a heading line (`#` to `######` at column 0) starts a section with its heading line verbatim (level kept: a `###` stays `###`), whether or not
  any block follows it before the next heading or the end;
- a top-level list item (`-`, `*`, `+`, `<n>.`, `<n>)`, a checkbox) with every following line that is indented or a lazy continuation, and the
  blank lines between them;
- a fenced code block (with its inner blank lines), a table (consecutive lines starting with `|`), or a paragraph (consecutive non-blank lines that
  are none of the above).
Each block becomes one `step` item, ids `P1..Pm` in file order: its first line is the block's first line without its list marker, and every
further line is kept verbatim (its own indentation included), rendered after 3 more spaces (4.1), so a nested `- [P1] x` or a `## ` line inside a
fence can never be read as an item or a heading. The section remembers whether its first item was numbered. No block becomes a rule and no item
gets a `why` entry (a legacy text has no runtime-written `WHY`, so it is never treated as gated, and a text that ends in `(WHY C6)` stays
words). `items_max` is `m`. A legacy body may contain `[P1]` as plain words: legacy bodies are recognized by the missing `items_max`, never by
markers, so such words stay words.

**Loss check (an invariant at write time and in the unit corpus).** For every legacy body B: the multiset of the **non-empty** `line_key`
values of B's lines equals the multiset of the non-empty `line_key` values of the migrated rendering's lines, each with its item marker
(`<n>. [P<k>] ` or `- [P<k>] `) removed first (empty keys, from blank lines, `---`, fences or lone markers, are skipped, as `changed_lines`
skips them). List numbering, bullet style, indentation and blank lines are the only differences, all invisible to the check. **Fallbacks, so the
migration cannot fail:** when the per-block split does not pass the check (a body the splitter mishandles), `migrate_body` makes each section one
multi-line step (its lines verbatim); when that does not pass either, the whole body is the single step `P1` (every line after the first is a
continuation). The last form passes by construction: every line of B appears once, prefixed only by a marker or by spaces, and `line_key`
ignores both. A fallback is never silent: the migration's reason ends `; one item per section: the per-block split did not keep every line` or
`; one item: neither split kept every line`, and the reply and the client's note carry the reason. The write-time check stays as an assertion of
that fact, not as a user path (19.1). **The corpus assertion is stronger than the invariant:** on every kept file and every generated v1 below,
`migrate_body` must pass with the per-block split and **no fallback**, so a splitter that pushed ordinary owner-written bodies into the fallbacks
(one or a few giant items) fails the unit corpus, and a kept file that needs a fallback is a splitter bug to fix, not an expectation to change.
The corpus: every `PLAYBOOK*.md` under `studies/` (the kept study evidence: E, E2, E3, E4 s1/s1r/s2/s2r/s3,
E5-E7 s1-s3, G0's six streams; 42 files, none with an empty section; B5), every generated v1 of the plan goldens, and constructed bodies: a table, a
fence (with a `## ` line and a `- [P1] x` line inside), nested lists, two headings with the same text, text before the first heading, an H1 title
directly before a `##` heading, two consecutive headings, a body that ends with a heading, a body of headings only, a paragraph ending in
`(WHY C6)`, list items separated by blank lines, CRLF, trailing spaces, a literal `[P1]`, and an empty body (the constructed bodies may take a
fallback only where the test says so). The legacy file itself is archived byte for byte as
`history/PLAYBOOK.v<n>.md` by the migration's write, so even a quirk of rendering loses nothing.

**An item-format file that no longer parses** (a hand edit of `services/**`, 16) is treated like a legacy body at the next owner op, or at the
watch settler's next due retire (8.5), whichever comes first: it first writes a repair migration of its current body (`op: migrate`, `by: runtime
(migration)`, the same split and fallbacks, new ids from `items_max + 1` so no id is reused, no `why` entry and no rule), with reason `v<n> was
changed outside revise_playbook and is not in item form ({reason}); its text as <m> items P<a>-P<b> (no change of words)`, and the reply says so
(5.2). The ids of the old file are then no longer live, so they read `retired`; the new items are `kept` (but for the carried watches below) and
their refs come from their own
`C<k>`/`R<k>` tokens, so an item whose words cite a current criterion still needs the parent's acknowledgement to be retired. **Watches are
carried, by text key (derived, nothing stored):** a repaired item whose text key equals the text key of an item that was live and in its watch
(or `warning`, or `retire due`) in the last version before the repair whose body parses, that item's line rendered with its `[P<k>]` marker but
without its list marker (a rule's `WHEN ... THEN ... WHY ...` line is exactly what the split keeps as the repaired step's words), continues that
item's watch: the same watch start, k, refs and related rejections, and its repaired text becomes the watched text (rule W1, 8.1), so a hand
edit does not clear a warning or a due retire. Two shapes cannot be carried and are declared (L6): an item whose words the hand edit changed (no
equal key), and an item whose watched text was written by the very version that was then edited by hand (its runtime-written body is lost, so
no parseable version holds it); both read `retired` under their old id and come back as `kept` items. A carried rule becomes a step (the repair
writes no rule), so its watch retire removes it and restores no previous text (a rule's text has no place in a step's slot; it stays in
`history/`). Readers show 19.1's line until the repair. Declared limit L6 (a hand-written file that does parse is read like the runtime's) is
unchanged.

**What existing orgs see.** Until the first change: nothing changes in the file; the owner's prompt shows the playbook as it would migrate, with
its future ids and the line "ids are assigned when you first change an item" (14.1); root's `services` reads `free text` (14.3). At the first
change root's `services` shows the playbook's version one higher with no word changed, and the client's note says why. Migrated items are `kept`
(never watched: they predate the watch) and their refs come from their own `C<k>`/`R<k>` tokens, so a 0a.2-era line `- C9: <C9's words>` covers C9
and its retire needs the parent's acknowledgement like any other.

**Continuations and retired copies.** `services._continue` copies a retired service's files byte for byte (unchanged); a legacy copy migrates at
its first change like any other.

## 5. Each operation (brief item 2)

### 5.1 The tool

`revise_playbook` keeps its name (every text that says "improve the playbook with `revise_playbook`" stays true), is still the owner's only, and
changes one item per call. MCP signature (`SRC/mcp_server/_tools_services.py:_register_owner_tools`):

```
revise_playbook(service: str, reason: str, op: str | None = None, evidence: list[str] = [], item: str | None = None,
                kind: str | None = None, text: str | None = None, when: str | None = None, then: str | None = None,
                after: str | None = None, version: int | None = None, acknowledged: str | None = None,
                content: str | None = None) -> str
```
`ServiceCommands.revise_playbook(actor, service, op, reason, evidence, *, item, kind, text, when, then, after, version, acknowledged) ->
PlaybookChange` follows (`services/api.py`), implemented by `services._ops.RuleItemReviser` (replaces `RulePlaybookReviser`; the
`PlaybookRevisions` Protocol follows), and `Org.revise_playbook` delegates to it unchanged in form (`app/_facade_services.py`). `op` is optional in
the MCP schema and `content` is accepted there only so that an old-form call, `revise_playbook(service, content, reason, evidence)`, passes
FastMCP's schema validation and reaches PB-FORM instead of a schema error ("op: field required"): an org agent whose session holds the old
docstring will call it so. PB-FORM is the first check, raised when `content is not None or op is None`. There is no CLI form:
`revise_playbook` is an org agent's tool and the CLI acts as root; the human's path to a lasting change is the contract (21.2, D3).

`PlaybookChange` (frozen dataclass, `services/api.py`): `version: int` (the version the op wrote), `op: str`, `item: str` (`""` for `first`),
`kind: str` (`""` for `first`), `admission: Admission` (6.3; `rule` is `exempt`, `first` or `restore` for exempt ops), `migrated: int | None` (the
version of a migration written first in this call, 4.4), `items: int` (the number of live items after the op), `restored_from: int | None` (the
version whose text came back), `acknowledged: str` (`""` when none), `ack_ignored: str` (an `acknowledged` id the change did not need, 5.1;
`""` when none), `formatting: bool` (an exempt edit), `related: tuple[str, ...]` (the related rejections the written item's watch holds: those
that stay after a gated edit of a warned item, 8.2, or that a carried watch brings, section 3), `carried: str` (the id whose watch the written item
continues, `""` when none; 5.2) and `client: str`. The MCP reply (5.2) is built from it alone.

| op | Arguments | What it does | Gate |
|---|---|---|---|
| `first` | `text` (markdown, the whole first version) | v1 when there is none: migrated into step items (4.4). Allowed only while the service has no playbook version (else PB-FIRST-EXISTS), no verdict (any tier) and no task with `revises` (else PB-FIRST-LATE): the procedure of the first request, before any evidence exists | exempt |
| `add` | `kind` (`step` or `rule`); a step: `text`, optional `after`; a rule: `then`, optional `when`, optional `after` (a rule id) | a new item `P<items_max+1>`, placed by 4.1's placement rule. On a service with no playbook (version 0) it writes v1 in item format (`op: add`, `admitted: b` or `c`, `items_max: 1`), in `## Steps` or `## Rules` | gated |
| `edit` | `item`; a step: `text`; a rule: `then` and/or `when`; optional `acknowledged` | the item's new text; its id, kind and place stay | exempt if the text tokens are unchanged, else gated; guarded if weakening (section 9) |
| `retire` | `item`; optional `acknowledged` | the item leaves the body (its texts stay in `history/`). The last live item may be retired: the body is then its heading lines, or empty, and `read_playbook` gives `items=()` (14.1 says what the prompt shows). `CappedPlaybookTexts.body`'s refusal of an empty body applies to `first`'s input only, never to a rendered item body | exempt; guarded if the item has coverage (section 9) |
| `restore` | `item`; optional `version`; optional `acknowledged` | brings back the item's text of `version` (default: its latest text before its current one; for a retired item, its last live text), placed by 4.1's rule. A live item that has had one text only and no `version`: PB-ARGS (`{id} has no earlier text`); a `version` that does not hold the item: PB-ARGS; a `version` whose text equals the current one: PB-SAME | exempt for a text a client-written version had; else gated; refused for a text the watch retired (8.6); guarded if it replaces the live text of an item with coverage and is weakening (9.1), exempt restores included |
| `move` | `item`, `after` (an item id of the same section, or `start`) | reorders within the item's section; `after` equal to the item itself, or to the item it already follows (`start` when it is already first): PB-SAME | exempt |

Every op: `reason` 1-400 characters (today's `REASON_MAX`); `evidence` at most 20 ids (today's `normalize_evidence`), ignored by exempt ops.
`acknowledged` goes with `edit`, `retire` and `restore` only (with any other op: PB-ARGS); on one of those three whose change needs no
acknowledgement (no coverage, or not weakening) it is ignored, not checked and not recorded, and the reply says so (5.2).
Order of checks in `RuleItemReviser.revise_playbook`:
1. PB-FORM; the owner check (today's `_owned`); PB-LOCKED (today's text); `reason`; PB-OP; the argument shape and the texts (which arguments go
   with the op, `kind`, PB-TEXT with its exemption for a criterion's own words, which reads the current criteria; 19.2); for `first`,
   PB-FIRST-EXISTS and PB-FIRST-LATE. All of these are pure or read-only and write nothing.
2. The migration (4.4) of a legacy or unparseable body (the repair migration carries the watches, 4.4).
3. The watch settler (8.5): a due watch retire is written, on the migrated body when step 2 wrote one, so a hand-broken file cannot hold a due
   retire back. When that retire removed the item the op names, step 4's PB-ITEM starts with the sentence of B7 (5.3).
4. The item (PB-ITEM), the item-dependent PB-ARGS (the item's kind, `after`, `version`, a restore without an earlier text; they need the ids,
   which a legacy body gets only at step 2) and no-change (PB-SAME).
5. For a gated change: the gate (section 6), the 30% rule (section 7; not for a (c) admission), the cap (section 10), then PB-WATCHED-OUT (8.6,
   `add`, gated `edit` and `restore`, B2: its exception needs the admission). For `edit` and `restore`, the guard (section 9) runs last, on the new text's coverage
   (for a gated change, computed from `admission.why`; for an exempt restore, from the restored text's `why` entry when it was live, else its
   tokens); a formatting edit keeps its `why` and is never weakening. For `retire`, only the guard. For `move`, nothing more. An exempt
   `restore` of a client-written text takes the 30% rule, the cap and the guard.
6. The round-trip assertion (4.1), the write (a compare-and-swap, 4.3: on `PlaybookRace`, PB-RACE), then the client's quiet note.

A refusal writes nothing, except a migration written before it (4.4) and a watch retire that was due (8.5). A guard refusal after an admitted gate
writes nothing either: the acknowledged call is judged again from step 1.

### 5.2 Replies (MCP; the owner reads them)

- add: `playbook of {service} is now v{n}: added {id} ({kind}), admitted ({rule}) on {ids}. {It starts new and is watched: a related client
  rejection warns it, a second retires it. | It continues the watch of {old id}: warning ({R ids}); one more related rejection retires it.}
  {client} was told without being woken.` (the second form for a carried add, section 3 carried watch (i))
- edit, gated: `... edited {id}, admitted ({rule}) on {ids}. Its watch starts again{; its warning stays (R4): one more related rejection retires
  it}{; it continues the watch of {old id}: warning ({R ids}), one more related rejection retires it}. ...` (the last clause for an edit into a
  text its owner retired in `warning`, section 3 carried watch (i), B2); formatting only: `... fixed the formatting of {id} (no evidence needed; its state is unchanged). ...`
- retire: `... retired {id}{ (acknowledged by {parent}, note {ack})}. ...`; restore: `... restored {id} to the text of v{k}, admitted ({rule}) on
  {ids}{ | (written by {client}: no evidence needed)}{ (acknowledged by {parent}, note {ack})}{; it continues the watch of {old id}: warning
  ({R ids}), one more related rejection retires it}. ...`; move: `... moved {id} after {after} (no evidence needed). ...`; first: `... wrote
  playbook v1: {m} items ({sections}). ...`
- The carried clause comes from the derivation after the write: `RuleItemReviser` reads `evidence.watch(owner, service)` once more and takes the
  written item's `ItemWatch.carried` and `related` into `PlaybookChange.carried` and `PlaybookChange.related` (one definition of a carried watch,
  `reflection._watch`). When that read fails (`OrgError`, `OSError`) after the write succeeded, the change stands and the reply's watch sentence is
  `Its watch state is in your prompt's playbook section.` (the states line of 14.1 shows it at the next run).
- An `acknowledged` the change did not need (5.1) adds ` (acknowledged={id} was not needed for this change and is not recorded.)` before the
  client sentence.
- When a migration ran first (`PlaybookChange.migrated`), the reply starts `playbook v{n-1} is the free-text v{n-2} as {m} items (P1-P{m}, no
  change of words). `; for a repair migration (4.4), `playbook v{n-1} is v{n-2}, which was changed outside revise_playbook, as {m} new items
  (P{a}-P{b}, no change of words). `.
- A retire of the last live item ends `The playbook has no items now: add one (op="add") when the evidence calls for it.`

The client's quiet note (`delivery.notify(client, ...)`, today's place) names the op, the item, its kind, the admission, the evidence ids, the
owner's reason (as today's note) and the file path. **New rule: no item text in root's note.** Today's note carries the admitted lines' text to
the client, root included (`services/_playbook.py:93-96`, "Lines added or changed"). From Phase 1 the note to a human client (root) carries ids
only; an agent client's note keeps the item's text. The reason: an item is an instruction written for the team (the study's poisoned line is
one), every change is now one item and one note, and root's context is the assistant's, where 0b already keeps agent text out of its views
(the views name ids; the text is one `read` of `PLAYBOOK.md` away). The reason line stays, as today and as root's `services` listing already
shows it (14.3), because it is the owner's sentence to its client about the change.

### 5.3 Refusal texts (constants in `SRC/services/_ops.py` unless marked; owner-facing, no CLI form)

```
PB-FORM: refused: revise_playbook changes one item of the playbook per call; it no longer takes the whole text (`content`). Use op="add" (kind
"step" with text and after, or kind "rule" with when and then), "edit" (item and the new text), "retire" (item), "restore" (item, version) or
"move" (item, after). Your playbook's items and their ids are in your prompt under "# Playbook". Nothing was written.
PB-OP: refused: op is one of first, add, edit, retire, restore, move: {op}. Nothing was written.
PB-ARGS: refused: op="{op}" takes {needed}; {wrong}. Nothing was written.
PB-FIRST-EXISTS: refused: `{service}` already has playbook v{n}: op="first" writes only the first version. Change it one item at a time
(op="add", "edit", "retire", "restore" or "move"). Nothing was written.
PB-FIRST-LATE: refused: `{service}` already has evidence ({what}), so its playbook is built one item at a time: op="add" with evidence (your
Reflect section says what is admitted). The first version is only for the procedure of the first request. Nothing was written.
PB-ITEM: refused: {The watch retired {id} in v{n} (rejections {R4}, {R6}). }`{service}` has no live item {id}. Its items: {ids, "none yet"}{; retired:
{ids} (op="restore" brings one back)}. Nothing was written.
(B7: the lead sentence only when step 3 of this call wrote the watch retire of {id}; in the retired list, an id the watch retired reads
`P12 (retired by the watch in v{n}: it comes back only as a confirmed criterion's own words)`.)
PB-SAME: refused: no change: {id} {already reads so | already comes after {after} | is already first in its section}. Change an item only when the
evidence calls for a different way of working. Nothing was written.
PB-TEXT: refused: {field} {rule}. Nothing was written.
PB-RACE: refused: the playbook of `{service}` changed while this call ran (now v{n}), so this change was not written: call again.
PB-SPLIT: section 7.   PB-CAP: section 10.   PB-ACK, PB-ACK-BAD: section 9.   PB-WATCHED-OUT: 8.6.
PB-C-WORDS (SRC/reflection/_evidence.py): 6.2.
PB-LOCKED, the agent-client refusal and the unknown-evidence refusal: today's texts, unchanged.
G1 (_no_client_evidence): today's text with "A revision is admitted only when" -> "An item is admitted only when" and "(c) it cites a criterion
{client} added to the contract by an amendment the client confirmed" -> "(c) it is the own words of a criterion {client} added to the contract by
an amendment the client confirmed"; the client question is unchanged.
G2 (_one_case): today's text with "Revise when the answer is in the contract (cite its new criterion), or when a second case shows the same
criterion failing." -> "Add the item when the answer is in the contract (its new criterion's own words, citing it), or when a second case
shows the same criterion failing."
```

The placeholders of PB-ARGS, PB-TEXT, PB-SAME, PB-FIRST-LATE and the `first` reply take exactly these strings (constants beside the texts; `{x}` is the value found):

| Placeholder | op or field | String |
|---|---|---|
| `{needed}` | `first` | `text (the whole first version, in markdown)` |
| | `add` | `kind ("step" with text, or "rule" with then), and optionally when (a rule) and after (an item id)` |
| | `edit` | `item and the new text (a step: text; a rule: then and/or when), and optionally acknowledged` |
| | `retire` | `item, and optionally acknowledged` |
| | `restore` | `item, and optionally version and acknowledged` |
| | `move` | `item and after (an item id of its section, or "start")` |
| `{wrong}` | an argument that does not go with the op | `{arg} does not go with op="{op}"` (one clause per argument, joined by `; `) |
| | a missing argument | `{arg} is missing` |
| | `kind` | `kind is "{x}", not "step" or "rule"` |
| | the item's kind | `{id} is a {step \| rule}: pass {text \| then and/or when}` |
| | `after` | `after={x} is not an item of {id}'s section` (move), `after={x} is not a live item` (add of a step), `after={x} is a rule: a step goes after a step (or leave after out)` (add of a step after a live rule), `after={x} is not a live rule` (add of a rule) |
| | `version` | `version={x} does not hold {id}` |
| | restore without an earlier text | `{id} has no earlier text: it has read so since v{k}, so there is nothing to restore` |
| `{what}` | PB-FIRST-LATE | `a verdict on {task}` or `a rework {task}`, for the oldest such record (B8) |
| `{sections}` | the `first` reply (5.2) | the heading lines without their `#` run, joined by `, `; `none` for a body without headings (B8) |
| `{field} {rule}` | any text field | `{field} is empty`; `{field} has more than one line ({x} lines)`; for a text that is not a current criterion's own words (19.2): `{field} has more than {limit} characters ({x})`, `text and then have more than 150 words with when ({x})`, `{field} has an item id in brackets ({x}): ids are the runtime's`, `text starts with "#": a heading is no item` |
| | `when` | `when has the word "THEN" in capitals: it would split the rule there; write the condition without it` |
| | `first`'s text | `text is empty`; `text has {x} words; the limit is {cap} (playbook_max_words)` |
| | `acknowledged` | `acknowledged is not a message id ({x})` |

### 5.4 Relation to 0a.2's line-level admission: folded in

P1 (0a.2 4) admitted a whole-text revision line by line. Phase 1 keeps every rule P1 enforced and moves it to the item:
- **(c) lines** ("the cited confirmed criterion's own words") become (c) items: the item's text (a step's `text`, a rule's `then` with `when` left
  out) must be the criterion's own words (6.2). The comparison is a new pure function, `services.api.item_words(words: str, criteria:
  Sequence[Criterion]) -> str | None`: the id of the first `c` with a non-empty `line_key(c.text)` such that `line_key(words)` is one of
  `line_key(c.text)`, `line_key(c.id) + line_key(c.text)` or `line_key(c.text) + line_key(c.id)`, else None. An item may be the criterion's words
  with or without its id, because the item's `WHY` names the id anyway. P1's `criterion_words` (which deliberately refuses the words without the
  id, `services/tests/test_line_keys.py`) and its use for the legacy `own_words` mark (`reflection/_marks.py`) stay unchanged.
- **(b) lines** ("carries the id it rests on, `[C6]`") become (b) items whose `WHY` the runtime writes from the admission (6.3): the tag can no
  longer be missing or wrong, because the owner does not write it.
- **Unchanged lines need nothing; formatting changes need nothing** (P1's "punctuation, spacing, list numbering or markdown alone"): the exempt edit
  and the move.
- **P1-REFUSED** (`LINES_REFUSED`) is replaced by PB-C-WORDS; G1, G2, the agent-client refusal and the unknown-evidence refusal stay.
- **P1's companions stay:** relayed lessons marked in the digest (0a.2 4.4); a `confirms` link-note id is evidence for its criterion (4.3); a
  removed criterion's note names the items that quote it (4.5), now by id for an item-format playbook (`still cites it in 2 item(s): P7, P12`,
  14.9) and by `quoting_lines` for legacy bodies.
- **What goes:** the whole-text `content` argument, `changed_lines` as the gate's input (it stays for the legacy marks of the timeline, 14.4),
  and the whole-version restore of 0a's Reflect step 5 (an item-level restore replaces it).

## 6. The evidence gate, item by item (brief item 3)

### 6.1 What is gated

Every **gated change** (section 3) is judged; exempt changes are not. Gated: every `add` (a rule or a step), every `edit` whose text tokens change,
every owner `restore` of a text no client-written version had. Exempt: `move`, a formatting-only `edit`, `retire` (it removes words; the
raise-the-bar guard of section 9 is its check), `first`, the migration, the watch retire, and a restore of a client-written text (0a's
exemption, kept). 08 4.2 exempts "reordering steps and fixing their wording"; the runtime cannot tell a wording fix from a changed check, so a
wording fix is exempt only when its text tokens (section 3) are unchanged (deviation D1, 21.2): only spacing, case, markdown markers and sentence
punctuation may change. A change of a word, a letter, a number or a symbol is gated, at the start of a text too, so a step that changes a check,
an output value or the handling of a criterion, whether the value sits in words, digits or symbols, can never pass as a wording fix, which is
M3's point (11-final-verification); the one exception is the list marker of a migrated item's continuation line (L13). The pattern, exactly
(`services.api`):
```python
TOKEN = re.compile(r"\d+(?:[.,:/-]\d+)*|[^\W\d_]+|[^\w\s.,;:!?'\"()\[\]*_`]")
LEADING_HASHES = re.compile(r"^\s*#+")

def plain(line: str) -> str:  # B9: `~` is dropped only as the pair `~~`, `#` only at the start of a line
    return LEADING_HASHES.sub("", line.replace("~~", ""))

def text_tokens(t: str) -> list[str]:
    lines = t.splitlines()
    return [tok for i, line in enumerate(lines) for tok in TOKEN.findall(plain(strip_markers(line) if i else line).casefold())]
```
Text tokens, not the text key, decide it: the key joins all letters and digits and drops every symbol, so `within 3.5 days` -> `within 35 days`,
`steps 1, 2` -> `steps 12` or `value > 100` -> `value < 100` would keep the key and pass as formatting; their tokens differ. `strip_markers` runs
on continuation lines only: an item's first line never carries a list marker (the runtime renders it; the migration removed it; an owner's `text`,
`when` and `then` are one line of words), so a leading symbol there is the owner's. Unit rows, each gated: `within 3.5 days` -> `within 35 days`;
`steps 1, 2` -> `steps 12`; `3,5` -> `3.5`; `é` -> `e`; `value > 100` -> `value < 100`; `x = 5` -> `x ≠ 5`; `at most 5%` -> `at most 5`; `$5` ->
`€5`; `UTC+2` -> `UTC-2`; `-3 days` -> `3 days`; `✓` -> `✗`; and at the start of a text, `>5 rows` -> `5 rows`, `> 5 action items` -> `5 action
items`, `+ 2 days to each due date` -> `2 days to each due date`, `[x] reviewed` -> `[ ] reviewed`; and (B9) `within ~5 days` -> `within 5 days`,
`see #3` -> `see 3`. Formatting (equal tokens): `**Due:**  ISO` ->
`Due: iso`; `Check the date.` -> `check the date`; a migrated item whose second line changes from `   - sub` to `   1. sub` (a continuation
line's own list marker, L13); and (B9) `~~old~~ new` -> `old new`, a continuation line `   ## Sub` -> `   Sub`. (A scratch run of this rule, with the product's `strip_markers`, on every pair above gave exactly these results, the B9 rows included
(re-run with B9's `plain` when the amendments were applied);
`- step` -> `1. step` on a first line is now gated, as it should be: the owner's own leading `-` and `1.` are tokens. The build's unit test is
the check.)

### 6.2 Rules (a), (b) and (c) for one item

`ServiceEvidence.admit_item(owner, service, evidence, reason, *, kind, text, when) -> Admission` (new method of the `services` port; implemented in
`SRC/reflection/_evidence.py:CaseServiceEvidence`). It keeps today's evidence stage of `admit` unchanged: resolve every cited id (criterion,
assertion, verdict, case, result, link note), refuse unknown ids, refuse for an agent client, collect `subjects`, `added` (the cited confirmed
amendments, `confirmed_amendments`) and `qualifying` (subjects that failed in at least 2 different cases the human client rejected: case heads
differ, `cases_of`). Then the **item stage** replaces P1's line stage. It first narrows `added` to the criteria a rejection of the client's own
confirms: `added_h = [c for c in added if any(c.id in a.verdict.confirmed for a in found)]` (`found` holds human-tier rejections only, and
`Verdict.confirmed` the ids a human link on that verdict names). A criterion in `added` but not in `added_h` was confirmed only by a human link on a
relayed (or agent) rejection: `feedback(confirms=...)` does not check the rejected note's tier (`services/_feedback.py:_check_confirmation`), and
`confirmed_criteria` counts such a link for a criterion with an empty `answers` (pre-0a.2 amendments). It gets the note `{id} was confirmed only
by a link on a relayed rejection (the assistant's own reading): rule (c) needs a rejection of the client's own` and admits nothing.
1. **(c)** when some `c` in `added_h` has a non-empty text key and the item's words are `c`'s own words: `item_words(words, added_h) == c.id`
   (5.4), where `words` is a step's `text` or a rule's `then`, and a rule's `when` is absent or `always`. Admitted as `c` on `c.id`.
2. **(b)** else when `qualifying` is non-empty: admitted as `b`; the item's text is the owner's (as P1's tagged lines were), and the runtime writes
   its `WHY` from the admission's `why` (6.3): the qualifying ids and the rejections that make them qualify.
3. Else, when `added_h` is non-empty: **PB-C-WORDS** (below). When both are empty: today's G2 (one case) or G1 (no client evidence), as today,
   with the note above among G1's notes when it applies.
The narrowing refuses no flow of E7 or G0 (the two corpora replayed): in each of their streams the (c) admissions rest on a criterion that
`define_service(answers=...)` added to answer the stream's human rejection, and the product's human link on that rejection names it (the replay of
13.2 lists every human rejection of E7 and G0 with its human answer link). E3-E6 were not replayed for it.

**(a)** "a deterministic client-check or runtime-check result shows the defect" has no data path in the product (no check result is recorded
anywhere: no `client-check` or `runtime-check` record exists; checked by `grep` over `SRC`). Rule (a) therefore admits nothing in Phase 1, and no
refusal offers it (declared limit L1, 21.3). It becomes live with the oracle tiers of Phase 3.

**Independent cases** (11 section 2, "undefined"): two cases are independent when their case heads differ (0b 3's case), the definition `cases_of`
already uses. A rework of the same case is never a second case.

```
PB-C-WORDS: refused: {ids} {is|are} confirmed by the client, so an item citing {it|them} may be only {its|their} own words: this item is not.
{one sentence per id, in id order: Write it as a step with text "{Ck's full text}" (or a rule with then "{Ck's full text}" and no when) to
add Ck. | for a text over 300 characters: Write it as a step whose text is Ck's words exactly as `services` lists them (or a rule with those words
as then and no when) to add Ck.} A different way of doing it needs a second case the client rejected on the same criterion (rule (b)). Nothing
was written: change it again with those words, or send {client} (`send`) this question once: "We would add to how we deliver {service}: {first
160 characters of the item}. Is that what you want from now on? If yes, please add it to the contract as a criterion."
```
The words PB-C-WORDS prescribes always pass PB-TEXT: a text that is a current criterion's own words is exempt from its keyword, bracket and length
rules (19.2), so every confirmed criterion, whatever its length or wording (a Given/When/Then criterion included), can become an item.

### 6.3 The admission and `WHY`

`Admission` (services/api.py) keeps `rule`, `evidence`, `detail` and gains `why: tuple[str, ...]`, computed in `admit_item` from the names of
today's `admit` (`found` = the regression assertions, `qualifying`, `added`):
```
(b): why = sorted(set(qualifying) | {a.id for a in found if a.id in qualifying or set(a.about) & set(qualifying)})
(c): why = sorted({c.id} | {a.id for a in found if c.id in a.verdict.confirmed or a.verdict.message.id == c.answers})
```
So a (b) item's `WHY` always holds the `R<k>` of every rejection that makes a qualifying id qualify (at least two, `cases_of`), whether the owner
cited criteria, assertions, verdicts or cases; and a (c) item's `WHY` holds its criterion and the rejection(s) whose human link confirmed it or that
its answering version answers, even when `Criterion.answers` is empty (a criterion whose answer predates `answers`). Every gated item's `WHY`
therefore holds at least one `R<k>`, by construction: (b) needs two human rejections, and (c) admits only through `added_h` (6.2), whose criterion
some human rejection's `verdict.confirmed` names, so that rejection's `R<k>` is in `why`. So the motivating case of every gated item is a `why`
case and is never one of its candidates (8.2), and the cap's candidate list of section 10 is empty by construction (D9; the repaired items that
carry a watch, which have no `why` entry, are excluded from it, and so is a text restored during a watch: section 10 reads the `why` of the
change that started the watch). `RuleItemReviser` writes the frontmatter `why` entry from `admission.why` only and renders the body's `WHY` from it; the version
records `evidence` (as cited) and `admitted` (`b`/`c`). **A gated edit's `WHY` is the new admission's `why`: it replaces the old entry, never merges
with it** (the new text rests on its own evidence). A formatting edit, a move and a retire keep the entry as it is; a restore writes the entry the
restored text had when it was live (its admission then), or, when the restore is itself gated, its new admission's. The owner never writes the
canonical `WHY`: it is the frontmatter entry, and a `WHY` in the owner's words stays words (4.1: the parser strips only a suffix equal to the
canonical rendering, so a copied suffix is kept as text and renders before the canonical one).

### 6.4 What the gate cannot enforce

That a (b) item follows from the two rejections (the team's words, backed by two human rejections; as 0a.2 4.7); that a (c) item sits in the right
place. Both are what the watch exists for.

## 7. The 30% rule (brief item 4)

`services._ops.split_check(current, new) -> None` (pure), applied to `add`, a gated `edit` and an owner `restore`; not to a (c) admission (its
words are a confirmed criterion's, which the contract already holds and which cannot be split), `retire`, `move`, a formatting fix, `first`, the
migration or the watch retire. Words are the content words of section 3 as text tokens (section 3).
`changed` = |multiset difference new minus current| + |current minus new| over the two bodies' content words; `base` = the current content words.
Refused when `changed > max(ceil(0.3 x base), 50)`:

```
PB-SPLIT: refused: this change touches {changed} of the playbook's {base} words, more than about 30% ({limit}): make it as smaller changes (one
item, or part of an item, per call), each with its own reason and evidence, so each one is judged and watched on its own. Nothing was written.
```
The floor of 50 words lets a small playbook take one ordinary rule (an item is at most 150 words, 19.2); "about 30%" is 08's figure, the floor is
this design's labelled default (not configurable). Zero case: with base 0 (no playbook, a migrated empty body, or every item retired) the limit is
the 50-word floor, so the first item of an empty playbook is an ordinary `add` within it; `first` is exempt from the rule.

## 8. The watch (brief item 5)

### 8.1 The states

Derived per call by `reflection._watch.watch_states(versions, cases, results, criteria, contract_versions) -> tuple[ItemWatch, ...]` (pure).
Inputs: every stored playbook version (frontmatter and parsed items); the service's cases built from mail alone (`CaseHistory.chains(owner,
service, since=created, runs=False)`); `results: Mapping[str, tuple[Message, ...]]`, every result of every task the client sent, oldest first,
from one `mail.received(client)` read (a `Case` carries only the latest result of its latest task, and the watch needs each task's deliveries and
the result a rejection was on); the criteria (`ServiceCatalog.criteria`); and the contract versions (`ContractVersions.versions(..., "SERVICE")`,
for the answering versions). Its one caller is `CaseServiceEvidence.watch(owner, service)` (`reflection/_evidence.py`), which reads those inputs
once per call; every reader of a watch state goes through that one method (8.2, 20.1). `ItemWatch(id, kind, state, text_version, watch_start, k,
r, clean, waiting, related, pending, restores, coverage, retire_due, carried)`, frozen (`services/api.py`, because `ServiceEvidence.watch` returns
it to `services`); `waiting` is the number of the first k candidates without `judged(c)`, `carried` the id whose watch the item continues (`""`
when none; section 3, carried watch). A retired item's `ItemWatch` keeps the `related` of its last watch (the carried watch reads it).

| State | Derived when | Live? |
|---|---|---|
| `new` | the item is live, in its watch, with 0 related rejections | yes |
| `warning` | the item is live, in its watch, with exactly 1 related rejection; or with 2 or more and `retire due` set, until the runtime's retire is written (8.5) | yes |
| `retired` | the item is not in the current body (an owner's `retire`, or `op: watch` without a previous text) | no |
| `restored` | live with a text the watch brought back (`op: watch` with `restores`), and no gated change since | yes |
| `kept` | live and not in its watch: its watch ended at `K` (k clean cases, every rejection in its window answered and unrelated), or it was never watched (v1, migrated, exempt-only history) | yes |

An item is **in its watch** from its watch start until it reaches `kept` (at `K`) or leaves the body. It reaches `kept` when `E` is defined (each
of its first k candidates has its judged delivery, section 3) and every human rejection in the window (section 3: on a result created at or after
the watch start, and created at or before `E` or recorded before `D`; for a restarted watch, the union of its windows), of any case, is answered and unrelated; all k candidates are then clean.
A candidate with no verdict yet on any of its deliveries after the live-from, or a rejection in the window that is pending, holds the item `new`
(showing `waiting for the client's verdict on {n} case(s)` or `waiting for the user's answer to {R}`), so no case can slip past the end without
its verdict. A delivery that a later task of its case superseded before any verdict (0b's `Delivery.superseded`, the common case in G0 and E7: 2-3
of every 3 first deliveries) holds nothing: the case counts through the delivery the client did judge. A gated change of a `kept` or `restored`
item starts a new watch. A warned item never reaches `kept` in that watch (its related rejection stays in the window, below): it stays `warning`
until a second related rejection retires it, read over its warned window (section 3, B1: every human rejection on a result created at or
after the watch start, recorded while the item is live in its watched text, whatever `E`, `D` and `K` are), or until its owner retires it
(D4). Two related rejections never
leave an item live for long: the runtime retires it (8.5); until that write succeeds, the derived state is `warning` with `retire due` set, and
every reader says so (14.1).

**Why the window closes at `D`, and the watch at `K`.** `E` bounds the window by delivery time, `D` by recording time. Without `D`, a rejection
recorded before the k-th candidate's verdict on a result delivered after `E` (a later case, rejected and answered while the k-th verdict was
still due) would be related while `E` was undefined and unrelated once the k-th verdict defined `E`: a late verdict, or root recording the
user's verdict after a relayed one, would turn a warned rule `kept` (review 3, R3-F1). With `D` every rejection recorded before the window closed
stays in it. `K` makes the existing rule "in its watch until it reaches `kept`" exact: a rejection recorded after `K`, even on a delivery
made before `E` (a second verdict on a judged delivery, a late verdict on a superseded one, or the first verdict on another case delivered
before `E`), is after the watch, like a rejection of a later delivery, and cannot move a `kept` item back.

**The monotonicity property** (8.7 and 20 test it). Within one watch (one watched change, rules W1-W3 below), as records are appended, the
derived state moves only along `new -> kept` or `new -> warning -> retired` (through `retire due`), and a warned item stays `warning` only while
no second related rejection has come (B1: whatever the order root records verdicts and answers in, the second one retires it). A verdict, a link
or an answering version recorded later never moves `warning` back to `new` or to `kept`, and never moves `kept` back to `new` or to `warning`.
**The one exception is a corrected link** (a second human link on a rejection, which 0a.2 5.9 lets decide, 8.2): it changes that rejection's
subjects, so it can unrelate it (`warning -> new` before `K`, or clear a `retire due` that is not written yet) or relate it (`kept -> warning`,
and a second such link the retire). A written watch retire stays (8.6, L9). *Proof.*
1. Fixed once they exist: k and r (8.4), the first k candidates (a new candidate's first done time is later than every existing one's),
   `judged(c)` and `J(c)` (verdict notes are only appended, with growing ids), `E`, `D` and `K` (each is a function of records that later records
   do not change; every record's time is its own creation time, a contract version's being its `defined`, B3); the refs of every text
   (section 3: taken as of its live-from); and the subjects of a rejection once it is not pending (P2's one-answer rule; its lineage is taken as
   of the time of its answer, B4, so a later re-add of a criterion's text does not change them; only a corrected link changes them).
2. Before `K` the window only grows. While `E` is undefined it holds every rejection on a result created at or after the watch start. `E`
   becomes defined at the moment `D`, so every rejection recorded before then has a note created before `D` and stays; the judging verdict
   recorded at `D` is on `judged(c)`, whose result was created at or before `E`, and stays; later membership is a fixed test of fixed times.
3. Answers are only appended, so a rejection never becomes pending again, and by 1 an answered rejection's relation to a text never changes.
   With 2, the set of related rejections only grows: the count goes `0 -> 1 -> 2`, never back. One related rejection makes `kept` impossible
   (it needs none in the window), so `warning` never returns to `new` or reaches `kept`; two make the retire due, and the runtime writes it.
   For a warned item the second is read over its warned window (B1): every human rejection on a result created at or after the watch start,
   recorded while the item is live in its watched text. That window has no `E`, `D` or `K` bound, so it only grows, and the related count only
   grows; a warned item never reaches `kept`, so `K` is never defined for it, and whether the k-th verdict or a later delivery's rejection is
   recorded first cannot decide between `retired` and `warning`.
4. `kept` is first derived at `K`, when every rejection in the window is answered and unrelated. From `K` on only the rejections recorded at or
   before `K` are read, each answered, with fixed subjects and fixed refs (1), so nothing but a corrected link can change their relation, and the
   state stays `kept`. ∎

A W2 change (below) is an owner's change, not a record of the kinds above: it starts a new watched change and adds its window to the watch's
(section 3: from its own live-from, open-ended until its own `E`), so the related rejections found so far stay (D4) and no rejection that was
outside the window is pulled in; the owner's op therefore makes no rejection related (8.5).

**Changes during a watch** (three rules; 8.7 has their rows):
- **W1, a change that keeps the watch.** A move, a formatting edit (equal text tokens) and a repair migration of a carried item keep the watched
  change, its candidates and its counts. The item's text after it is the watched text from then on: "still live in the watched text" (8.5) means
  live with the same text tokens as the watched text (the same id, or the carried id), so the settler's retire removes the current text, wherever
  it now sits.
- **W2, a change that restarts the watch.** A gated change restarts it (an edit restarts the count of clean cases, 09 40). So does an owner's
  exempt `restore` of a client-written text made while the item is in its watch: it is a change of the text like any other, so the restored text
  becomes the watched text, the candidates are counted again from its live-from, and the related rejections found so far stay (D4: a warning
  survives every change). The settler compares against that new watched text. (Outside a watch, the same restore leaves a `kept` item `kept`: a
  client-written text, like v1's, is never watched.)
- **W3, a change that ends the watch.** Only a retire: the owner's (the item reads `retired`; its related rejections stay in the history and carry
  over to a restore or a re-add of the same text, section 3) or the runtime's (8.5).

Computation (`watch_states`, per item, from the versions, the service's cases and every result of their tasks): (1) the watched change and its
live-from, by rules W1-W3; (2) the candidates, in first-done-time order; (3) for each candidate, `judged(c)` and `J(c)` from the human-tier
verdicts on its deliveries whose `done` result came after the live-from; (4) `E = max J(c)` and `D` once each of the first k has `judged(c)`;
(5) the window (section 3; the union of the watched changes' windows after a restart): every human rejection on a result created at or after the watch start, and, once `E` is defined, on a result created
at or before `E` or recorded before `D`; each tested for relation against the text that was live when its result was created, and pending while
it (or the earlier rejection its link names as the same) has no answer; (6) `K`: from `D` on, the first record time at which the files up to it
derive `kept`; from `K` on, only the window's rejections recorded at or before `K` are read; (7) for an item with one related rejection, its
warned window (section 3, B1), in which a second related rejection retires it whatever `E`, `D` and `K` are. The state follows from the counts, and moves only
as the monotonicity property above says. Unit rows: (i) a candidate delivered before the k-th and judged after it, related: `warning`, never
`kept`; (ii) the same candidate unjudged: `new`, waiting, until its verdict; (iii) a related rejection on a result created after `E` and recorded
after `D`, of an item whose k candidates are clean: outside the window (`kept`); (iv) a related rejection on a blocked result created before `E`:
related; (v) a first delivery superseded by a human rework whose delivery the user accepts: the case is clean (`judged(c)` is the rework);
(vi) the same with a relayed rework whose delivery the user rejects about the item's refs: related; (vii) the k-th candidate's first delivery
superseded, its rework rejected about the item: related, inside the window (`E` is the rework's done time, `D` that rejection's note), never
outside it; (viii) a late verdict recorded on the superseded first delivery after the rework's verdict: `judged(c)`, `E` and `D` unchanged; as a
rejection about the item it is related when recorded before `K` (its result was created before `E`) and after the watch when recorded after `K`;
(ix) a move, then a formatting edit, of a warned item, then its second related rejection: the settler retires the moved, reformatted text (W1);
(x) an exempt restore of a client-written text while warned: `warning`, the clean count restarted, the next related rejection retires the
restored text (W2); (xi) an owner's retire in `warning`, then a restore of the same id, and separately an add of a text with the same text key:
each starts in `warning` with the carried rejection (section 3); (xii) a repair migration of a hand-broken file holding a warned rule whose line
was not touched: the repaired item is `warning` (carried), and one more related rejection retires it. **The rows of review 3 (R3-F1)**, with k = 3,
candidates c1 and c2 accepted, c3 delivered: (xiii) c4, delivered after c3's delivery, rejected about the item and linked
(`feedback(confirms=...)`) before c3's verdict is recorded: `warning`, and still `warning` after c3's verdict (the rejection was recorded before
`D`); (xiv) the same rejection recorded after c3's verdict: outside the window (its result after `E`, its note after `D`), and the item is
`kept`; (xv) root records a relayed verdict on c3 before c4's link and the user's verdict on c3 after it: `warning`, and it stays (a relayed
verdict makes no `judged(c)`, so `D` is the human verdict's note). **Rows of the property's edges:** (xvi) after `K`, a human rejection of a
delivery made before `E` (a second verdict on c2's judged delivery, or the first verdict on a case delivered before `E`), answered as related:
`kept` stays (after the watch); (xvii) at `D` a rejection in the window is pending, and before it is answered another rejection, on a result
created before `E`, is recorded and answered as related: `warning` (it is in the window, and `K` is not reached); (xviii) a rejection linked "same
as R<j>" while R<j> is unanswered is pending; the call that answers R<j> settles both, and when both relate, the count goes from 0 to 2 in that
call (8.3); (xix) after `K`, a corrected link that makes a rejection of the window related: `warning` (the exception), and a second such link the
retire. **Rows of the manager's amendments (section 24):** (xx) B1, k = 3: the item is warned by a related rejection in its window, `D` is
defined, and then a related rejection of a delivery made after `E` is recorded after `D`: it is the second related rejection (warned window),
so the retire is due, in every order of the k-th verdict, the first rejection's answer and that rejection; (xxi) B2: the owner retires P12 in
`warning`, then a gated edit of the live P13 into P12's text: P13 is `warning` (carried from P12), with P13's own related rejections as well
(the union); (xxii) B3: an old rejection answered by a contract version whose `defined` is after the watch start leaves `r` and k unchanged
(the link-note row of 8.4 has its version twin); (xxiii) B4: a v1 criterion C6 that one answer removed (adding C10) and a later answer re-added
by its exact text (removing C10): C6's lineage as of the later answer holds C10, and C10's lineage as of that time holds C6, each visited once,
so a rejection answered about C6 after the re-add relates to a rule that cited C10; (xxiv) B4: a rejection answered before the re-add keeps the
subjects it had at its answer (C6 had no lineage then); (xxv) B4, a cycle C6 -> C10 -> C6 -> C10 (three answers): the lineage ends, each id once.

### 8.2 What counts: deliveries, clean cases, related and pending rejections

All from mail and the item file, never from team text:
- **Deliveries and verdicts** are 0b's (`reflection._quality_rules.deliveries_of`, counted verdicts = human tier), built from the client's mail
  only. The watch does not read the deliverable folders, so 0b's voiding of a verdict recorded after a hand edit is not applied (declared limit L4;
  G0 counted 0 hand edits in 19 copies). This keeps the watch one definition for its three readers: the write path (8.5), the owner's prompt
  and root's views.
- **A clean case** for a watched change: section 3. Cases of the change's `why` assertions are no candidates (6.3 puts the `R<k>` of every
  motivating rejection in `why`, so a rework of a motivating case delivered after the item went live is not counted either), so "later" means
  fresh cases. Each case counts once: it enters the candidates at its first delivery after the live-from and is judged through its judged
  delivery, the one of its deliveries after the live-from that got the client's first verdict (section 3). This is 0b's judged case ("a case
  with at least one judged delivery", `judged_cases`), read from the live-from on: the team's questions, an ask-first draft and a human or
  relayed rework before the verdict (G0's and E7's usual flow) move the judged delivery, not the case out of the count.
- **A related rejection**: section 3. It counts on any rejected result, `done` or `blocked` (E7S3-6: a blocked result is no delivery, but a user who
  rejects a file copied from it still rejects the rule's effect), and on any case, the cited ones included, when it is in the window (section 3:
  bounded by `E` on its result and by `D` on its note; closed at `K`), or, for an item already in `warning`, in its warned window (section 3,
  B1: every later delivery while the warned text is live, with no `E`, `D` or `K` bound). The text it is held against is the text that was live when the rejected
  result was created, so a rejection of an older text cannot warn a newer one.
- **A pending rejection** (no human link and no answering version yet, or a "same as R<j>" link while R<j> is pending, section 3) makes its case
  not clean and is not related yet; when the answer is recorded, it becomes related or not. Section 13 makes every rejection's answer due before the service's next new request and before root's
  human accept of its case, so pending cases clear within one request.
- **"No lasting rule"** (a human link `none`) makes a rejection unrelated; its case is then clean for the item (it is judged and has no related
  rejection).
- **Relayed and agent verdicts weigh nothing**: they are no counted verdict, no assertion and no link (0a's tiers, unchanged).

**Across edits.** An edit restarts the watch's count of clean cases (09 40; 04 7.1): the clean cases of a watch are those after the live-from of
its watched change (8.1, W2). Related rejections accumulate over the whole watch period, across every change, until the item reaches `kept` or
leaves the body (the watch's window is the union of its watched changes' windows, section 3, so a restart keeps every rejection found so far
and adds those on results after its own live-from), and they carry over to a restore of the same id or a re-add of the same text after an owner's retire in `warning` (section 3,
carried watch), or to a gated edit of another live item into its text (B2; the edited item keeps its own related rejections too): an owner
cannot clear a warning by editing, restoring, retiring and re-adding the rule, or editing another item into its text (section 22, check 2).
This holds for a
(c) edit too (D4): an owner who edits a warned item into the own words of a criterion the client confirmed after the warning keeps the warning,
so one more related rejection retires the client's words, and PB-WATCHED-OUT then bars them until the client confirms another criterion; raising
the bar wins over convenience, and the owner can add the words again after that confirmation. Several items may reference one criterion: one
related rejection then warns each of them (11 section 2, "09-40").

**Order and late answers.** The states are recomputed from all data on every read, and the order in which root records the user's verdicts, its
own relayed verdicts and the answers moves them only as 8.1's monotonicity property allows; a warned item's second related rejection retires
it whatever that order (B1, the warned window). A late answer settles a pending rejection: before
`K` it can only turn `new` into `warning` (related) or let the item reach `kept` (unrelated); it cannot reach a `kept` item, whose window holds no
pending rejection. A user's corrected link (a second `feedback(confirms=...)`, which 0a.2 5.9 lets decide) is the one exception: it can turn a
related rejection unrelated, or an unrelated one related, so a `kept` item one of whose window's rejections turns related is `warning` again
(`E`, `D` and `K` do not move: section 3). A watch retire, once written, is a fact of the file and stays (8.6 says when the item may come back).

### 8.3 Notifications

All are quiet notes (`MessageDelivery.notify(..., wake=False)`), written by the watch settler (8.5) in the call that recorded the answer:
- **to the owner, on the first related rejection:** title `playbook item {id} of {service}: warning`, body `Rejection {R} (case {case}) is about
  {subjects}, which {id} cites. One more related rejection retires {id}{ and restores the text of v{k}}. Follow the contract where they differ.`
- **to the owner and to the parent, on the watch retire:** title `playbook of {service}: the watch retired {id}`, body `Rejections {R4} and {R6}
  are about {ids}, which {id} cited, so the runtime retired it{ and restored the text of v{k}} (playbook v{n}). The client's verdicts decide
  this; no acknowledgement is needed.` The note to a human client (root) names ids only, never the item's words (5.2's rule).
Nothing is sent when nothing changed (before and after are both derived in the same call, 8.5), so no flag is stored to avoid repeats. When one
call takes an item's related count from 0 to 2 or more (possible: the call that answers `R<j>` also settles a later rejection linked "same as
R<j>", which was pending until then, 8.1 row xviii), the retire's note is sent and no warning note.

### 8.4 k and r

`k = 3` unless the recurrence rate `r` is known. `r` = (judged cases of the service whose first `done` result came before the watch start and
that have a human rejection whose subjects meet the item's refs, the refs of the text at the watch start, as k is fixed then) / (judged cases of
the service with a `done` result before the watch start). An edit within the watch does not change `r` or k. It
is computed from the data as it stood at the watch start: only cases with a result created before it, and only the verdicts, link notes and
answering contract versions whose `defined` is before it (message ids carry their creation stamp, a contract version its `defined`, never the
contract's `created`, which every version carries from v1; compared as aware datetimes, B3), so an answer recorded later never changes `r`,
and k is fixed for the whole watch. Unit rows: a link note on an old rejection recorded after the watch start leaves `r` and k unchanged; so
does an answering contract version of an old rejection whose `defined` is after the watch start (B3). `r` is
**known** when that denominator is at least 10 and the numerator at least 1 (06 section 6: a failure seen once in 12 can
never be shown fixed within 20; below 10 judged cases the rate is noise). Then `k = max(3, ceil(ln 0.1 / ln(1 - r)))`, with `r = 1` giving 3.
Values (unit-tested): r = 0.5 -> 4, 0.3 -> 7, 0.2 -> 11, 0.1 -> 22. `k` is never capped and is shown with `r` (root's views; 14.3, 14.4). The
minimum of 10 is a labelled default of this design, not an ORG.md setting.

### 8.5 The automatic retire and restore: the runtime, as the `services` single writer

`services._watch.RuleWatchSettler` (implements the new package-private Protocol `WatchSettlement`): `settle(owner, service, before) -> SettleReport`
(`SettleReport(retired: tuple[str, ...], warned: tuple[str, ...], failed: tuple[tuple[str, str], ...])`, the ids it retired, the ids it warned and
the `(id, error)` of each retire it could not write).
- **Who calls it.** `RuleClientFeedback.feedback` after it writes a human link (`confirms=`), and `RuleContractDefiner.define_service` after it
  writes the answering version and attempts its link (`answers=`), each with `before` = `evidence.watch(owner, service)` read before its own write;
  and `RuleItemReviser.revise_playbook` at step 3 of 5.1, after a migration and before the op (with `before` equal to `after`: it only writes a
  due retire). These are the only moments a relation can appear (a rejection becomes related only through a human link or an answering version)
  or a due write can be retried. On a locked contract the owner's op is refused at step 1, before the settler, so there a failed retire is retried
  at the next recorded answer only (L11).
  On the `define_service(answers=...)` path the settler runs after the contract version is written and the link is attempted, and before
  `LINK_FAILED` is raised when the link could not be written: the answering version alone already relates the rejection (its `about`, its answer
  ids and the ids it removes are subjects, section 3), so the retire does not wait for the link. `LINK_FAILED`'s text is unchanged; the retire it may have
  written shows in `services` and in the notes.
- **What it does.** `after = evidence.watch(owner, service)` (`ServiceEvidence.watch`, new port method, implemented with `watch_states`). For every
  item with 2 or more related rejections that is still live in the watched text (8.1 W1: live, under its id or the carried id, with the same text
  tokens as the watched text, so a move or a formatting edit during the watch changes nothing here): re-read the current playbook, write the next
  version with that item's current text removed and, when the item had a text before its watch (a `kept` or `restored` text, of the same kind)
  whose text tokens differ from the watched text's, that text back in its place (`op: watch`, `admitted: watch`, `by: runtime (watch)`, `related`,
  `restores`, the restored text's `why` entry back, reason `the client rejected {R4} and {R6}, which are about {ids}`; the `service.revise` event
  has `actor` `runtime`, 4.2). When the text before the watch has the watched text's tokens (a W2 restore brought exactly it back), putting it
  back would write an unchanged body, so the watch retire removes the item and restores nothing (`op: watch` without `restores`; the item reads
  `retired`; unit row). Items are handled one
  per version, in id order, each write a compare-and-swap on the version just read (4.3). When the current body does not parse (a hand edit), the
  settler first writes the repair migration of 4.4, which carries the watches, and then the retire on the repaired body. An item whose current
  text no longer has the watched text's tokens (a gated change the owner wrote meanwhile restarted its watch, W2) is left to the next derivation.
  Then the notes of 8.3, for each item whose related count went from 0 (in `before`) to exactly 1, and for each retire.
- **Exempt from the guard** (section 9): the client's verdicts are the authority (11 M4). **Locked contracts too:** the lock stops the owner's ops,
  not the client's verdicts, so a contract locked after items were admitted still has its watched items retired.
- **What root reads.** `feedback` keeps returning the link `Message` and `define_service` its `str` (so none of their callers change); the watch's
  outcome reaches root's reply through a derived step, as `feedback_step` does today: the new `ServiceSteps.watch_step(rejection: str) -> str`
  (`reflection`, 14.5) derives from the files, for the rejection the call answered, the items it warned, the `op: watch` versions whose `related`
  holds it, and the items with `retire due`, and returns their sentences (`""` when none):
  - `Rejection {R} is related to playbook item {id} of {service}: {id} is in warning now ({owner} was told); one more related rejection retires it.`
  - `The watch retired {id} of {service} (playbook v{n}) because rejections {R4} and {R6} are related to it{, and restored the text of v{k}};
    {owner} was told.`
  - `The watch could not retire {id} of {service} yet (retire due: {R4} and {R6} are related); it retries at {the owner's next change of the
    playbook or }the next recorded answer.` (the braced part is left out when the contract is locked)
  - `The watch could not be checked ({error}); it is checked again at the next change.` (when `watch_step`'s own read fails; the only error text a
    reply carries)

  The MCP replies of `feedback(confirms=...)` and `define_service(answers=...)`, and the CLI's `feedback --confirms`, the CLI's automatic link of
  a human reject with `--criterion` (`cli/_commands_services.py`) and `define-service --answers`, append it (the CLI prints each sentence as a line
  after today's line). One builder, so the MCP, the CLI and the derived states can never disagree.
- **Failure.** The link or the answering version is the user's record and stays written. On the `feedback` and `define_service` paths a failed
  playbook write (`OSError`, `OrgError`, `PlaybookRace`) is caught and recorded in `SettleReport.failed`; the derived `retire due` (8.1) is what
  the reply's third sentence and every later read show until a write succeeds. The error text itself is not carried into the reply (it is no fact
  of the files): the same write is retried at the next owner op (unless the contract is locked) or the next recorded answer, where a persistent
  `OSError` propagates as any write failure of `revise_playbook` does (the recorder's `tool.call ok: false` names it). No new event kind. On the
  `revise_playbook` path a `PlaybookRace` of the settler's write refuses the op with PB-RACE, any other write failure propagates the same way, and
  nothing else is written by that call.
- **Concurrency.** Two processes run this code: root's (the `feedback` and `define_service` paths) and the owner's agent (`revise_playbook`).
  Every playbook write is a compare-and-swap under the per-service lock (4.3), so of two writers that read the same version one writes and the
  other gets `PlaybookRace`: the owner's op is refused with PB-RACE and the owner calls again; the settler records `failed`, `retire due` shows,
  and the retire is written at the next trigger, re-derived from the files. A second settler that finds the item already gone writes nothing.
  Integration test with two writers (20).

### 8.6 Coming back after a watch retire

An owner's `add`, gated `edit` (of any live item, B2) or `restore` whose new text key equals a text the watch retired (any `op: watch`
version's removed text of any item; a rule's text key is that of its `then`, section 3, so a rule re-added as a step is caught; the lenient
key on purpose, so a re-add with other punctuation is caught), or a text its owner retired while its watch retire was due (2 related, the write
not yet done), is refused while at least 2 of that retire's related rejections are still related
(a user's corrected link can undo the relation), unless it is admitted under (c) by a criterion confirmed after that retire (the client then made
it the contract):
```
PB-WATCHED-OUT: refused: this text is {id}'s text that {the watch retired | you retired while the watch's retire of it was due} in v{n}, because
the client rejected {R4} and {R6} on what it cited
({ids}). It comes back only as the own words of a criterion the client confirms after that (rule (c)). Nothing was written. If you think the
client wants it, send {client} (`send`) this question once: "Your rejections {R4} and {R6} retired this from how we deliver {service}: {first
160 characters of the text}. Do you want it back from now on? If yes, please add it to the contract as a criterion."
```

### 8.7 Zero and empty cases

| Case | Result |
|---|---|
| a service with no playbook, or no item ever gated | every item `kept` or none; `watch_states` returns the items with state `kept`, `()` for no playbook |
| a legacy playbook | its virtual items (4.4), all `kept` |
| a watched item with 0 deliveries since its watch start | `new`, clean 0 of k |
| a judged case whose only rejection is pending | not clean, not related; listed in `pending` |
| a rejection linked `none` | unrelated; its case is clean |
| the user never answers a rejection | its case stays pending; the item cannot reach `kept` through it; section 13 refuses the next new request, and root's human accept of that case unless the accept is what the answer waits for (13.2) |
| r's denominator below 10, or numerator 0 | k = 3, r shown as `unknown (n judged cases)` |
| an agent client | no human-tier verdicts: no gated item can enter (the gate refuses), so nothing is watched |
| a contract with no criteria | refs of (b) items are `R<k>` ids only; coverage is the confirmed assertions; the watch works on R subjects |
| a removed criterion | still a subject of the rejections whose answers removed it, and in the lineage of the criterion that replaced it, so the rule that cited it stays related to rejections about either; it is no coverage, and neither is a confirmed assertion that is only about removed criteria (section 9) |
| every item retired (an empty item list) | `watch_states` returns the retired items only; the owner's prompt reads `Playbook v{n} has no items: add one (op="add").` (14.1); the 30% rule's base is 0 (section 7) |
| a candidate case none of whose deliveries after the live-from ever gets a verdict | the item stays `new` (`waiting for the client's verdict on 1 case`): it cannot reach `kept` while one of its k candidates has no judged delivery (L12) |
| a candidate whose first delivery is superseded (a human or relayed rework, an ask-first draft) before any verdict | holds nothing: the case is judged through the delivery the client judged (`judged(c)`); clean or related by that verdict and its answer (8.1 rows v-vii) |
| a late verdict on a superseded delivery, after a later delivery of the case was judged | changes nothing for `judged(c)`, `J(c)`, `E` and `D` (8.1 row viii); a rejection among such verdicts is in the window when recorded before `K` (its result was created before `E`), after the watch when recorded after `K` |
| a later case rejected about the item, and its rejection answered, before the k-th candidate's verdict is recorded (a delayed verdict, or root recording a relayed verdict first) | the rejection was recorded before `D`, so it stays in the window: `warning`, and still `warning` once the k-th verdict is recorded (8.1 rows xiii, xv) |
| the same rejection recorded after the k-th candidate's verdict, on a result created after `E` | outside the window: the item can reach `kept` (8.1 row xiv) |
| a rejection recorded after `K`, of any delivery (one made before `E` included) | after the watch: a `kept` item stays `kept` (8.1 row xvi); only a corrected link of a rejection in the window reopens it (8.1 row xix) |
| a warned item whose window has closed (`D` defined) | retired at the second related rejection, whatever the order (B1): the second is read over the warned window, every human rejection on a result created at or after the watch start while the warned text is live, so a related rejection of a later delivery retires it, recorded before or after `D`; it stays `warning` only while no second related rejection has come, or until its owner retires it (8.1 row xx) |
| a rejection linked "same as R<j>" while R<j> has no answer | pending until R<j> is answered (its subjects are not known); then both settle in one call (8.1 row xviii) |
| a move or a formatting edit of an item in its watch | the watch continues; the moved or reformatted text is the watched text (W1); a due retire removes it |
| an exempt restore of a client-written text of an item in its watch | the watch restarts on the restored text, related rejections kept (W2); the settler compares against the restored text |
| a gated change of a warned item (an edit, or a gated restore) | the watch restarts its clean count; the warning stays (D4); the settler retires the new text at the next related rejection |
| a blocked result in the watch that is never rejected | holds nothing (a blocked result is no delivery and needs no verdict); rejected, it can relate (8.2) |
| an item retired by its owner during its watch | `retired`; its related rejections stay in the history and carry over to a restore of the id, an add of a text with the same text key, or a gated edit of another live item into that text (section 3, carried watch (i); B2; 8.1 row xxi); PB-WATCHED-OUT applies only to the watch's own retires and to an owner's retire made while the watch retire was due (8.6) |
| a gated edit of a live item into a text the watch retired (B2) | PB-WATCHED-OUT, as for an add or a restore of that text (8.6), unless (c) admits it by a criterion confirmed after that retire |
| an unparseable (hand-edited) body with a due retire | the settler (or the owner's next op) writes the repair migration first, which carries the watches by text key, then the retire (4.4, 8.5); an item whose line the hand edit changed loses its watch (L6) |
| one call takes an item's related count from 0 to 2 or more (the call that answers `R<j>` also settles a later rejection linked "same as R<j>") | the settler retires the item in that call; the retire's note is sent and no warning note (8.3) |
| the watch retire of an item whose text before the watch has the watched text's tokens (a W2 restore brought exactly it back) | the retire removes the item and restores nothing (8.5): no version with an unchanged body is written |
| two writers of one playbook at once (the settler in root's process, `revise_playbook` in the owner's) | one compare-and-swap wins; the other gets `PlaybookRace`: PB-RACE for the owner, `failed` and `retire due` for the settler (4.3, 8.5) |

## 9. The raise-the-bar acknowledgement (brief item 6)

### 9.1 When it is needed

An owner's `retire` of an item with **coverage** (section 3: a current criterion, or a confirmed assertion that is not only about removed criteria),
and an owner's **weakening** `edit` or `restore` of such an item, need the parent's acknowledgement. An edit or a restore replaces the item's live
text with a new one, and is weakening when (i) the new text's coverage lacks an id of the old text's coverage, or (ii) the new text's content
words are a strict sub-multiset of the old text's (it only deletes words). The new text's coverage:
- for a gated edit or a gated restore, computed from the new admission's `why` (6.3), which is why the guard runs after the gate (5.1);
- for an exempt restore (a client-written text, 0a's exemption), from the restored text's `why` entry when that text was live, else from its own
  `C<k>`/`R<k>` tokens (refs, section 3). So an owner cannot lower the bar by restoring an older, uncovered text, even one root wrote: example, v1
  step P4 (root's words) edited by the owner, under (c), into C9's own words (covered by C9), then restored to v1's words: weakening by (i), PB-ACK;
- a formatting fix keeps its `why` and is never weakening.
A restore of a retired item replaces no live text and is never weakening. The runtime's watch retire is exempt (8.5). An item whose refs are only
removed criteria, "no lasting rule" assertions or confirmed assertions about removed criteria only has no coverage, so its retire needs nothing:
the client already lowered that bar. Example (the study's planted rule B, 18.4): B is a (c) item with `WHY R2; C10`; when the client's answer to
a later rejection removes C10, B's coverage is empty (C10 is removed, and R2 is about C10 only), so the owner may retire B without asking. A
semantic weakening that keeps the ids and adds words is not caught by (i) or (ii); it is a gated change, so it needs fresh evidence and is watched
(declared limit L5).

### 9.2 The acknowledgement

**The parent's tool.** New `acknowledge_playbook(owner, service, item, op, text_hash=None, words=None)` for the owner's parent: root (MCP and CLI)
and a manager (MCP, in its runs). Implemented by `services._acknowledge.RuleAcknowledger(agents, catalog, owners, evidence, sender)` (Protocol
`PlaybookAcknowledgements` in `services/_protocols.py`, beside `PlaybookRevisions` and `ClientFeedback`; `ServiceCommands` gains `acknowledge_playbook(actor, owner, service, item, op, *, text_hash=None,
words=None) -> Message`, the note it wrote, and `Org.acknowledge_playbook` delegates to it). Coverage comes from `evidence.watch` (`ItemWatch.coverage`).
- Checks, in order: `owner` is the actor's direct report (ACK-NOT-YOURS, today's `define_service` rule); `service` is one `owner` offers
  (ACK-NO-SERVICE); `item` is live (ACK-NO-ITEM); `op` is `retire` or `edit` (ACK-OP; a restore is acknowledged as the `edit` to the restored
  text); `text_hash` is given for `edit` (ACK-HASH: missing, or not 12 lower-case hex digits) and not given for `retire` (ACK-ARGS); the item has
  coverage (else ACK-NOT-NEEDED); root passes `words`, the user's yes verbatim, 1 to `FEEDBACK_MAX` (1000) characters (ACK-WORDS, with the
  length when it is over) and an agent parent passes none (ACK-AGENT-WORDS).
- **The text hash** of an edit is the first 12 hex digits of the SHA-256 of the new text, UTF-8, as stored: a step, its `text` stripped; a rule,
  `when + "\n" + then`, each stripped, with `when` normalised as the runtime stores it (absent, `""` or `always` in any case is `always`). So an
  acknowledgement is for exactly one new text, and a restore's is the restored text's hash. PB-ACK names it. (It is not the text key of section 3.)
- Writes one quiet note parent -> owner through the message sender: title `playbook acknowledgement: {op} {item} of {service}`, the new header field
  `acknowledges: "{service} {op} {item}[ {text_hash}]"`, `source: human` for root, body the words (an agent parent's body: `Acknowledged.`).
  `dispatch.MessageSender.send` gains `acknowledges: str | None = None`, accepted only on a `note` without `feedback` and without `criterion`
  (else `OrgError("acknowledges goes only on a plain note")`); the kernel `Message` gains the optional field, read and written by its
  frontmatter codec like `criterion` and shown in its header (`acknowledges: ...`), so `inbox` and `read` show it. No surface's `send` takes it
  (the architecture test's `GUARDED` gains it, 16), and the `msg.deliver` event does not gain a key (the note's title already names the op and the
  item), so `events/line_shapes.txt` is unchanged. Reply (MCP): `Acknowledged {op} of {item} ({service}): note {id}. {owner} applies it at its
  next run by making the refused change again with acknowledged="{id}".` (the same words for an edit and for a restore, which is acknowledged as
  the edit to the restored text).
- CLI: `hirearchy acknowledge-playbook <owner> <service> <item> retire|edit [--text-hash H] --words "<the user's yes>"`. Output line:
  `acknowledged {op} of {item} ({service}) for {owner}: note {id}`, then the snapshot commit `root: acknowledge {id} -> {owner}` as every mutating
  command.

**The owner's side.** A guarded op without `acknowledged`:
```
PB-ACK: refused: {id} covers {ids} (what the client required or rejected), so {retiring it | this edit, which {drops C6 | only deletes words}, |
restoring it to the text of v{k}, which {drops C6 | only deletes words},} lowers the bar: it needs {parent}'s acknowledgement. Nothing was written.
Send {parent} (`send`) this once: "May we {retire | change | restore to v{k}} {id} of {service} ({ids}) because {reason, clip 200}? If yes:
acknowledge_playbook(owner="{owner}", service="{service}", item="{id}", op="{retire | edit}"{, text_hash="{hash}"}{, words=<the user's yes,
verbatim>})." When the acknowledgement arrives (a note "playbook acknowledgement"), call this again with acknowledged=<its id>.
```
With `acknowledged`: the note must be in the owner's received mail, sent by its parent, its `acknowledges` equal to this op (`edit` with the new
text's hash for an edit or a restore), created after the item's current text went live, not cited by any stored version's `acknowledged`, and
for root `source: human`. Otherwise PB-ACK-BAD naming the failed condition. The version records `acknowledged`. An `acknowledged` passed on a
change that needs none is ignored (5.1, 5.2).

ACK texts (constants in `SRC/services/_acknowledge.py`; root and manager; the CLI form in parentheses):
```
ACK-NOT-YOURS: refused: {owner} is not your direct report: only its parent acknowledges a change of its playbook. Nothing was written.
ACK-NO-SERVICE: refused: {owner} offers no service `{service}`. Its services: {names, or "none"}. Nothing was written.
ACK-NO-ITEM: refused: `{service}` of {owner} has no live item {item}. Its items: {ids, or "none"}. Nothing was written.
ACK-OP: refused: op is retire or edit (CLI: retire|edit; a restore is acknowledged as edit): {op}. Nothing was written.
ACK-ARGS: refused: text_hash goes with op="edit" only (CLI: --text-hash): a retire is acknowledged for the item, whatever its text. Nothing was
written.
ACK-HASH: refused: an edit is acknowledged for one new text: pass text_hash="<the 12 hex digits {owner}'s request named>" (CLI: --text-hash).
Nothing was written.
ACK-NOT-NEEDED: refused: {item} covers no current criterion or confirmed assertion, so {owner} needs no acknowledgement to {op} it. Nothing
was written.
ACK-WORDS: refused: an acknowledgement from root records the user's yes: pass words=<their answer, verbatim> (CLI: --words), after they answered
yes to {owner}'s request{; words has {n} characters, the limit is 1000}. Nothing was written.
ACK-AGENT-WORDS: refused: words= records the user's own yes, so only root passes it; acknowledge without it. Nothing was written.
```
`PB-ACK-BAD: refused: acknowledged={id} is not {parent}'s acknowledgement of this change ({the failed condition: not found in your mail | not
from {parent} | for {other op or item} | for another text (hash {h}) | older than the current text of {item} | already used by v{k} | not the
user's (no source human)}). Nothing was written.`

**Why a note and not a stored request.** The acknowledgement is a message, an existing file kind, and the guard is derived from it at the owner's
call; the owner's request is a free `send`. No pending state is stored. The guard is not part of the exit criterion; its friction is one parent
call (for root: one yes/no question to the user) per lowering of the bar, which 03 3.5 and 02 R9 ask for. That the owner then applies the
acknowledgement (calls again with `acknowledged=`) rests on PB-ACK's text (section 15, item 9).

## 10. Cap handling (brief item 7)

The cap is today's `playbook_max_words` (default 1000, ORG.md), counted in content words (section 3) for an item-format playbook, so the
migration's markers never push a playbook over. `add`, gated `edit` and `restore` are refused when the new content words exceed the cap:
```
PB-CAP: refused: the playbook would have {n} words; the limit is {cap} (playbook_max_words). Retire an item first. Candidates, oldest first (new
items whose watch rests on no regression assertion): {P7 (since v4; cites C9: retiring it needs {parent}'s acknowledgement), ...}. Or shorten an item
(op="edit"). Nothing was written.
```
Candidates are the live `new` items whose watch rests on no `R<k>`: the `why` entry of the gated change that started the item's watch (for a
carried watch, the change that started the watch it continues) cites no `R<k>` (09 50; 10 F2). So the repaired items that carry a watch are
excluded (they have no `why` entry of their own, but they have their own watch, which the cap must not cut short), and so is an item whose owner
restored a client-written text during its watch (W2: that text has no `why` entry, but its watch started on evidence). Candidates are ordered by
live-from, at most 5, each marked when the guard applies (it does for every candidate that covers a current criterion: the cap then needs the
parent, which is 09 50's "human prompt when the cap is reached"). In Phase 1 this list is empty by construction: every gated item's `WHY` holds
at least one `R<k>` (6.3: a (b) item's holds the rejections that make its subjects qualify, a (c) item's the human rejection whose human link
confirmed its criterion, which 6.2's `added_h` requires), every watch starts at a gated change, and the items 08 had in mind
(rule (a)'s check results, pack seeds) do not exist yet (D9). The list stays in the design so that it fills when those arrive. So the
refusal adds a second list: the oldest live items with no coverage (v1, migrated and other ungated items; their retire needs no acknowledgement),
at most 5, as `Items that cover no criterion or assertion (no acknowledgement needed): P4 (since v1), ...`. Zero case, both lists empty: `Every
item covers a criterion or an assertion: retire one yourself (it needs {parent}'s acknowledgement), or shorten one.` A legacy playbook is migrated first (its content
words are its words), and a playbook over the cap (a legacy file or a lowered `playbook_max_words`) can still take retires, moves and formatting
fixes.

## 11. Lessons as after-action reviews (brief item 8)

**Shape.** `report(..., lessons=...)` stays required on a service request (1-800 characters, `dispatch/_lessons.py`, unchanged checks). Its
docstring (`SRC/mcp_server/_tools_tasks.py`), the refusal texts of `check_lessons` and the last step of the generated v1 (14.8) ask for an
after-action review in five labelled parts, domain-agnostic:
`Expected: <the criterion id or step it concerns>. Happened: <what the work did>. Caught at: <where it should have been caught>. Cause: <the system
cause: a step, a check, a hand-off, an input; not a person>. Prevent: <what would have prevented it>.` and, when nothing went wrong,
`Near miss: <what almost went wrong, or none>.`

**Parsing and display** (`reflection._digest.aar_parts(text) -> AarParts | None`, pure). The labels are matched case-insensitively at the start of
the text or after a sentence end (`.`, `;`, a newline); each part runs to the next label. In the digest (`case_line`), after the client's
verdicts, a case's latest lesson renders as `owner's view: Expected C6 | Happened ... | Caught at ... | Cause ... | Prevent ...` (each part clipped
to 60 characters, the whole to today's `CLIP_LESSON` 220), or `owner's view: "<the text>"` when no label is found. For a case whose final verdict is
an accept, the line shows `owner's view: near miss: <its Near miss part, or "none recorded">` (08 4.2: "an accepted case adds a near-miss line";
it costs no run, the team wrote it when it reported). The relayed and "written after the reject" marks of 0a.2 4.4 stay, inside the tag:
`owner's view (from a relayed rework, not the client's): ...`.

**Never evidence.** The gate never reads lesson text: a result id cited as evidence is refused with "its lessons are your team's view" (today's
note), and the watch reads no lesson. The `report` reply's existing hint (`services/_hints.py:ServiceReportHints.report_hint`, which the MCP
`report` tool appends) names the AAR form on every report of a service request whose service has a playbook (its new wording is in 14.9).
The hint sees the task and the status, not the lessons text, so it states the form every time instead of a nudge when no label was found; nothing
is refused (the shape gates nothing; section 15 lists it).

## 12. The Reflect cap (brief item 9)

`EvidenceReflectSection.section` returns at most 600 words (`REFLECT_WORDS = 600`, a labelled default; G0's Reflect sections ran 505-631 words),
counted with `str.split` over the whole section. Its **fixed text** (heading, intro, the warning line of 14.2, lead and numbered steps) is bounded
by `REFLECT_FIXED_WORDS = 400` in every variant, asserted by a unit test over locked/unlocked, human/agent client, human/relayed/agent
rejection and new request, with and without a warning line, and with every id list of the fixed text at its longest. To make that bound hold,
every id list in the fixed text (the warning line's items, the `{eligible}` groups) shows at most 5 ids, then `+{n} more`. Measured on 14.2's
text as written here: 335 words in the variant G0 ran (human client, unlocked, after a human rejection, `{eligible}` = `none yet`, no warning),
278 for a new request, 393 at the longest (three `{eligible}` groups of 5 ids plus `+n more`, a warning line of 5 items plus `+n more`); the
unit test asserts the bound on the implemented strings, and a text change that breaks it fails there. The digest gets the rest:
`DigestBuilder` gains `reflection_digest(owner, service, words=None)`, and `section` passes `words = REFLECT_WORDS - words(fixed text)` (at least
200); with `words`, the builder drops the oldest shown case lines first (keeping at least one) and then clips the remaining line, ending it with
`… (more: services)`, so the whole section is at most 600 words in every case. Only the Reflect section is capped; the playbook section and the
regression list keep their own limits (`RENDER_BODY_CHARS`, `REGRESSION_LINES`).

## 13. Clause 2's refusals: every human rejection is answered within one request

**What counts as answered** (one rule, one helper). A human rejection has a recorded answer when it has a human link note (`Rejection.answered`,
derived by `ServiceEvidence.amendment_basis`, `reflection/_evidence.py`) or a contract version that answers it
(`services._criteria.answering_version(store, owner, name, note) > 0`, read from the `services` store: `amendment_basis` does not derive it, which is
why `RuleServiceRetirement._check_record` calls it with its own store today, `_retire.py:73`). A new pure-ish helper in `services/_criteria.py`
states that rule once: `unanswered(basis: AmendmentBasis, store: ServiceStore, owner: str, name: str) -> list[Rejection]`, the rejections of
`basis` with neither, oldest first. `RuleServiceRetirement._check_record`, `RuleContractDefiner` (its two copies of the rule in `_record` and
`_check_answer`), `RuleServiceRequester` (13.1) and `RuleClientFeedback` (13.2) all use it, so a rejection whose answering version exists but
whose link write failed (`LINK_FAILED`) is answered for every one of them, and no refusal offers a call that is itself refused.
`services.api.Rejection` gains `case: str` (the id of the rejection's case, `Assertion.case`), filled by `amendment_basis`.

### 13.1 The next new request waits for the answers

**The rule** (`SRC/services/_request.py:RuleServiceRequester.request`). Root's `request` of a service without `revises` (a new request, not a
rework) is refused while a human-tier rejection of that service, recorded after the service's previous new request was sent (its note id is
greater than that task's id: message ids begin with their creation stamp), is in `unanswered(...)`. "Since the previous new request" makes the
window exactly one request (11 M8) and leaves an existing org's older backlog alone. Reworks (`revises=`) are never held: the user's corrections
can start at once (P2's reasoning).

```
REQUEST-UNANSWERED: refused: rejection {R} (message {note}) on task {task} of `{service}` has no recorded answer yet, so the next request of
`{service}` waits: every rejection gets the user's answer within one request. Ask the user the one question first: {question}. On yes:
define_service(owner="{owner}", name="{service}", ..., answers="{note}", about=<the id you asked about>, words=<their answer, verbatim>)
(CLI: hirearchy define-service ... --answers, --about, --words). On no, a one-off or "as it is": feedback(task_id="{task}", verdict="reject",
confirms="{note}", criterion=["none"], ["R<j>"] or ["C<k>"], source="human", note=<their answer, verbatim>) (CLI: hirearchy feedback <task>
reject --confirms ... --criterion ... --source human --note ...). A rework of that case (revises=) is not held. Nothing was sent.
```
`{question}` is `reflection._steps.question_for` (today's one wording). Several unanswered: the oldest is named, then `and {k} more: {R ids}`.

**Zero case.** No earlier new request of the service, or no human rejection since it: nothing is due and nothing is refused.

**Who it applies to.** Root's MCP `request`, the CLI `hirearchy request`, and `Org.request` (one class). An agent client's rejections are agent tier:
no assertion, no refusal. Root's one-off tasks have no service and are not refused (a declared way around, section 16). `RuleServiceRequester`
gains two constructor dependencies, `evidence: ServiceEvidence` and `store: ServiceStore` (for `unanswered`), wired in `app` like the other
consumers (20.1). A record that cannot be read refuses with a request variant of today's `UNREADABLE` (`services/_define.py`), a new constant in
`services/_request.py`:
```
REQUEST-UNREADABLE: refused: the record of `{name}` cannot be read ({error}), so the request was not sent. Try again; if it persists, tell the user.
```

### 13.2 Root's accept of a case waits for the answers of that case

**The rule** (`SRC/services/_feedback.py:RuleClientFeedback.feedback`, after today's `_checked` and before the note is written). Root's accept
whose effective source is human (`verdict="accept"`, `source == "human"`) on a task of a service is refused while a human rejection of **the
same case** (an earlier one: every recorded rejection is) is in `unanswered(...)`, **unless the accepted task is in `basis.unrated`** (a delivered
case whose latest task has no verdict yet). The MCP `feedback` tool's default `source="relayed"` (`mcp_server/_tools_services.py`), and a facade
or service call without `source` (`Org.feedback`'s default `None`, which `dispatch._sender.provenance_source` stamps `relayed` on root's verdict
note), are relayed and never held; the CLI's `hirearchy feedback <task> accept` defaults to `--source human` and is held. The case of the accepted
task is the first task of its `revises` chain in root's sent mail, followed only through tasks of the same service sent to the same assignee (the
head `CaseHistory` uses, `reflection/_cases.py:_build`), compared with `Rejection.case`. Relayed and agent accepts, rejections and one-off tasks
are never held by it. Unit rows: `Org.feedback(ROOT, t, "accept")` (no `source`) on a case with an unanswered rejection is recorded, as relayed;
the same with `source="human"` is FEEDBACK-UNANSWERED; a task whose `revises` names a task to another assignee starts its own case.

**Why the exception.** `define_service(answers=...)` is itself refused by P2-UNRATED (`services/_define.py:388`) while any delivered case's latest
task has no verdict. When a rework of the case was delivered before the user's answer, and that answer is a new criterion, refusing the rework's
accept would leave root no order that works: the answer waits for the verdict and the verdict for the answer. A task in `basis.unrated` is
exactly the delivery that P2-UNRATED holds the answer for, so its accept is recorded and the answer follows. Every other accept on a case with an
unanswered rejection waits: the accept of a delivery that already has a verdict (the "as it is" accept after a rejection of the same delivery,
L-ASIS, which E7 s2, G0 m0-s3 and m1-s3 used), an accept on a blocked result (a blocked case is never in `unrated`), and an accept of an earlier
delivery of the case. No order deadlocks: a task in `unrated` can always get its verdict (its accept is exempt, and a rejection or a relayed
verdict is never held), after which P2-UNRATED lets the answer through, after which every accept passes.

```
FEEDBACK-UNANSWERED: refused: rejection {R} (message {note}) on task {rejected task} of this case of `{service}` has no recorded answer yet, so
the user's accept waits: a case is closed only after its rejections have the user's answers. Record the answer first, then this accept again.
Ask the user the one question first if you have not: {question}. On yes: define_service(owner="{owner}", name="{service}", ...,
answers="{note}", about=<the id you asked about>, words=<their answer, verbatim>) (CLI: hirearchy define-service ... --answers, --about,
--words). On no, a one-off or "as it is": feedback(task_id="{rejected task}", verdict="reject", confirms="{note}", criterion=["none"], ["R<j>"]
or ["C<k>"], source="human", note=<their answer, verbatim>) (CLI: hirearchy feedback <task> reject --confirms ... --criterion ... --source human
--note ...). Nothing was recorded.
FEEDBACK-UNREADABLE: refused: the record of `{service}` cannot be read ({error}), so the verdict was not recorded. Try again; if it persists, tell
the user.
```
Several unanswered: the oldest is named, then `and {k} more: {R ids}`. It applies to root's MCP `feedback` with `source="human"`, the CLI
`hirearchy feedback <task> accept` (human by default) and `Org.feedback` with `source="human"` (one class). `RuleClientFeedback` already has
`evidence` and `store`; it gains `settler: WatchSettlement` (8.5).

**Replayed against E7 and G0** (the owner's received mail of E7 s1-s3 and of G0's six streams, m0-s2 included; a scratch script, facts only, not
a test: `.agents/tasks/replay_accept_refusal.py` in the worktree): 9 cases had a human rejection and ended with a human accept, and in every one the rejection's human answer link was written
before the accept, including the three L-ASIS endings. The refusal would have refused **0** calls, and no flow these studies needed waits on
it. Their P2-UNRATED flows (root's relayed verdict on the injected relayed rework, which in all 9 streams was sent before the human rejection)
are unchanged.

**The last request.** The service's last request (of a stream, or of a service that is then left alone) has no next new request. 13.2 narrows the
gap: its case cannot be closed with an accept of an already judged delivery, of a blocked result or of an earlier delivery while a rejection of it
is unanswered. What remains is an accept of the case's latest, unrated rework while the rejection waits, and a case that ends with no accept;
there only `retire_service` refuses until every rejection has its answer (today). That remainder is declared (L10) and measured: the study's
G2(b) adds a derived end-of-stream check (21.1). The owner may close the remainder by narrowing P2-UNRATED for an answer (21.6, question 2).

**What the user sees.** When they ask for the next request, or accept a version of a case, before answering the one question about a rejection,
the assistant asks the question first; their answer may be "no lasting rule" or "a one-off", so the cost is one answer they were already to be
asked (D3), and one reordering of root's calls.

## 14. What changes in the prompts, the skill, ROOT_INSTRUCTIONS and root's views (brief item 10)

### 14.1 The owner's playbook section (`reflection/_sections.py:QuotedPlaybookSection`)

```
# Playbook: {service} (v{n}, yours to improve one item at a time; {w} of {cap} words)
> ## Steps
> 1. [P1] ...
> ...
> ## Rules
> - [P9] WHEN always THEN ... WHY R1; C9
Item states: P9 rule, new since v5 (watched: a related client rejection warns it, a second retires it); P12 step, warning: rejection R4 (case
{case}) is related; one more retires it and restores the text of v3. All other items: kept.
```
The body stays quoted (`> `), so agent text never mixes with the prompt's headings. The states line is the product's and names only ids, states,
versions and rejection ids; it shows no counts of clean cases (08 P6: agents see facts, not targets; root and the human see the counts, 14.3).
`retire due` reads `P12: retire due (R4, R6 are related): the runtime retires it at the next change; follow the contract`, and on a locked
contract (where the owner's ops are refused before the settler runs, L11) `P12: retire due (R4, R6 are related): the runtime retires it at the
client's next answer; follow the contract` (B6). A watch held open by a
missing verdict reads `P9 rule, new since v5 (waiting for the client's verdict on 1 case)`, the number of its first k candidates with no judged
delivery yet (`ItemWatch.waiting`; a superseded delivery is not counted, only a case none of whose deliveries since the live-from has a verdict),
and one held by an unanswered rejection `P9 rule, new since v5 (waiting for the user's answer to R4)`. A carried watch (section 3) shows its old
id: `P15 step, warning (carried from P9): rejection R4 is related; one more retires it`. A legacy playbook is shown as it would migrate,
with `Items get these ids when you first change one.` before the states line. An item-format playbook with no items (every item retired): the
quoted body is its heading lines (or nothing), and the states line is `Playbook v{n} has no items: add one (op="add").` A playbook that does not
parse: the raw body quoted, and the line `Playbook v{n} is not in item form ({reason}): your next change first turns its text into new items (no
change of words).` No playbook (version 0; the locked text is today's): the two texts become, while reflecting, `No playbook yet: write v1 now
from how the team works with revise_playbook(op="first", text=...) (Reflect before you start shows the evidence; rules from lessons or relayed
verdicts are not steps), then follow it. The first version needs no evidence and is allowed only until the client's first verdict or rework;
after that, add items one at a time (op="add") with the client's evidence.`, and otherwise `No playbook yet: plan as usual; when you report this
request, write v1 with revise_playbook(op="first", text=...): the steps your team followed, nothing more (no evidence needed, and only until the
client's first verdict or rework; after that, op="add" with the client's evidence).` One text covers both sides of PB-FIRST-LATE, so the section
needs no reading of verdicts for it.

**Where the states come from.** `QuotedPlaybookSection(catalog, paths, evidence: ServiceEvidence)` reads `evidence.watch(addr, service)` once
per section (the one derivation, 8.1) and builds the states line from the `ItemWatch` values; `EvidenceReflectSection` gains the same
dependency for its warning line (14.2). When that read fails (`OrgError`, `OSError`), the section quotes the body and replaces the states line by
`Item states could not be read ({error}); follow the contract where an item differs from it.` (nothing else of the prompt changes). The owner's
`# Your services` listing (`OwnedServicesListing`) shows no states: the playbook section is where the owner reads them, and its goldens stay
as they are.

### 14.2 The Reflect section (`EvidenceReflectSection.section`)

Human client, unlocked (the variant G0 measured; the others change the same way). Today's text is shortened so that the fixed text fits section
12's bound:
```
# Reflect before you start: {service}
Your playbook is how your team delivers this service; you own it and change it one item at a time. Evidence since v{n}:
{digest, capped (12)}
{warning line, when an item is in warning: "Warning: P12 (R4), P13 (R5) each have one related rejection; a second retires it." (at most 5 items, then "+{n} more")}
{lead}
1. Look for what repeats, and for anything the client rejected (the regression list). A rejection or a failure is enough to look into on its own;
   a single slow case is not.
2. When a lesson of yours conflicts with the client's own feedback (not a relayed verdict), the client is right: apply the feedback in this {what}.
3. If a change to how the team works would prevent it, change one item with `revise_playbook` (its description gives the ops). A rule, or a step
   that changes a check, an output or how a criterion is handled, needs evidence in `evidence`: the same criterion or assertion failed in 2
   different cases the client rejected, or the item is the own words of a criterion the client confirmed ({eligible}). Lessons and relayed
   verdicts are not evidence. An admitted item is watched: a related client rejection warns it, a second retires it. Retiring or weakening an
   item that covers a criterion needs your parent's acknowledgement. If a change is refused, nothing is written: send your parent its question
   once and go on.
4. The playbook may raise the bar, never lower it: the acceptance criteria come from the contract and travel with every request. Your parent asks
   the client whether a rejection is a lasting requirement: send nothing about it yourself beyond a refused change's question (step 3).
5. If nothing needs to change, change nothing. Then handle the {what} following the playbook.
```
The human-rejection lead becomes: `The client rejected a delivery: check it against their words, the regression list and the contract before you
plan the {what}. Without the client's evidence (step 3) a rejection is a reason to look, not to change an item: your parent asks the client
whether it is a lasting requirement, and the answer reaches you as a contract change or a criterion link.` The relayed and agent leads are
today's with "cannot change the playbook" kept and "revise" read as "change an item". `{eligible}` is today's `_eligible` reworded and clipped
(section 12): `now C9, C10 (an item may be the own words of one); C12 not confirmed yet; C14 user-initiated (never rule (c))`, or `none yet`. Today's
step 5 (the whole-version restore, "read history/PLAYBOOK.v<k>.md: revise_playbook with its text unchanged") goes: `op="restore"` is per item.
Locked: today's locked text, with "revise" read as "change". Agent client: today's text, with "nothing can admit a change (only the first
version)".

### 14.3 Root's `services` listing (`reflection/_reports.py:_block`)

The `playbook` line of an offered or requestable service (today `  playbook v{n} ({date}): "{reason}"`) gains a suffix with the items and the
watch, ids and counts only (no agent text): `  playbook v5 (2026-01-15): "..."; 11 items (2 rules); watched: P9 new (1 of 3 clean cases, k 3;
waiting for the client's verdict on 1 case), P12 warning (R4; the next related rejection retires it)`; `; 11 items (2 rules), none watched` when nothing is watched; `; free text (items when the
owner first changes one)` for a legacy playbook; `; not in item form ({reason}): it becomes items at the owner's next change` for a file that does
not parse; `; no items` for an empty item list. The CLI `services` command prints the same lines (one builder). The regression list's assertion
lines add `(rules citing it: P12)` when an item's `why` cites them. The builder is `TextServiceReports(agents, catalog, history, paths, evidence:
ServiceEvidence)`, which reads `evidence.watch(owner, name)` once per listed service; when that read fails, the suffix reads `; watch not read
({error})` and the listing goes on.

### 14.4 The quality view and the timeline (`reflection/_marks.py`, `progress/_quality_render.py`)

- `PlaybookMark` gains `op`, `item`, `item_kind` (`""` for legacy versions). **The quality JSON's playbook marks gain them too**
  (`progress/_quality_render.py:_mark_data`: keys `op`, `item`, `item_kind`, always present, `""` for a legacy version; `item_kind` because the
  mark's own `kind` key already reads `"playbook"`), and `basis` takes the new values below. The goldens and pins that move with that: the one
  quality golden with a playbook mark, `tests/golden/expected/quality/e3.json` (one mark; it moves anyway for `watch`), and the schema helper
  `tests/testkit/quality_schema.py` (`PLAYBOOK_MARK`: the three keys and the `basis` choices; the service record's `watch`). The 0b replay kit
  (`tests/e2e/test_org_growth_0b_replays.py`) reads named keys of the marks (`basis`, `by`, `evidence`, `changed`, ...) and compares tuples of
  them, never whole marks, so no replay expectation moves. A legacy version's mark is computed exactly as today (`changed_lines`, `own_words`,
  `tagged`), so every published replay count of E to G0 stays. An item version's text: `playbook v5 (lead): add P9 (rule), admitted
  (c) on C9, R1`; `playbook v6 (runtime (watch)): retires P12 after R4, R6 and restores the text of v3`; `playbook v4 (runtime (migration)): the
  free text as 11 items (no change of words)`; `playbook v7 (lead): retires P3, acknowledged by root (note {id})`; `basis` takes the new values
  `migrate`, `exempt`, `watch`.
- Each service record gains a `watch` list (JSON: `[{"item", "kind", "state", "k", "r", "clean", "waiting", "related", "pending", "since",
  "carried"}]`, `[]` when none;
  every key always present, schema 1 extended), filled by `DerivedCaseRecords(..., evidence: ServiceEvidence)` from `evidence.watch(owner, name)`
  inside its `_read` guard (a failure reads as the record's `error`, `the playbook watch: {words}`, like every other read of a record), so the
  quality view, the prompt sections, root's listing and the write path read one derivation (8.1). The text view prints one line `playbook watch: ...` (14.3's wording) only when the list holds an
  item that is not `kept`, so a corpus with no item-format playbook prints as today.

### 14.5 Tool descriptions

`revise_playbook` (rewritten for the ops; under today's length), `acknowledge_playbook` (new; root and manager surfaces), `report`'s `lessons` (11),
`request` (one sentence: `A new request waits until every rejection since the previous one has the user's answer; the refusal gives the
question.`), `feedback` (two additions: in `verdict`, `An accept waits while an earlier rejection of the same case has no answer from the
user; the refusal gives the question.`; in `confirms`, `An answer may retire a watched playbook rule; the reply says so.`) and `define_service`
(in `answers`, the same clause: `An answer may retire a watched playbook rule; the reply says so.`). The new reflection port method `ServiceSteps.watch_step(rejection)` (8.5) is no tool; its sentences are the reply text
of 8.5.

### 14.6 SKILL.md (125 lines, net 0; lines 39, 72, 92 and 100 word for word)

One edit, inside line 109 (not one of the protected lines). Today its tail reads:
```
   ... read it with `inbox`, go on, and never reply to it or mention it. Never edit SERVICE.md or PLAYBOOK.md yourself.
```
and becomes:
```
   ... read it with `inbox`, go on, and never reply to it or mention it; an owner's request to acknowledge a playbook change is not such a
   note: ask the user its yes/no, then `acknowledge_playbook(..., words=<their yes>)`. Never edit SERVICE.md or PLAYBOOK.md yourself.
```
(one physical line in the file; wrapped here). The line count stays 125; md5 changes from `a3e46347...`. Why: line 109 tells root to ignore an owner's note with a client
question, and an acknowledgement request is such a note in form; without the edit the guard's path would be blocked by the skill itself. Every
other guarantee of this phase reaches root through tool replies (the `request` refusal, the `feedback` and `define_service` replies, the watch's
notes), so no other line changes. Tests: the line-count and needle tests (`skill/tests/test_finish_rules.py`, `test_observe_skill.py`,
`test_skill_org_growth.py`, `test_skill_services.py`, `tests/e2e/test_round7.py`) keep passing unchanged; one new needle test pins the clause and
re-asserts lines 39, 72, 92 and 100 byte for byte.

### 14.7 ROOT_INSTRUCTIONS

Unchanged (`SRC/mcp_server/_instructions.py`, under 2700 characters). The reject order it states ("`feedback` first, then ONE yes/no question
naming an id, then the change") is the one section 13 enforces, and its two refusals (13.1, 13.2) reach root through tool replies.

### 14.8 Role templates and the generated v1

`roles/manager.md`: unchanged. `blueprint/_playbooks.py:StepsPlaybookWriter.default_playbook`: the last step's lessons clause becomes the AAR form
(11), and the trailing `## Pitfalls\nnone yet: add them from lessons and feedback` goes (it invited rules from lessons, which the gate refuses; rules
now get their own section when the first one is admitted). The plan's Details label becomes `playbook v1: generated from the team (steps, budget
plan):`. `templates/_documents.py`'s service paragraph ("Improve the playbook with `revise_playbook`") stays true and unchanged.

### 14.9 Owner-facing texts of `services` that name the playbook

Each changes because it names the whole-text revision; the new wording, word for word:
- **The `report` hint** (`services/_hints.py:ServiceReportHints.report_hint`, appended by the MCP `report` tool to the reply of a done or failed
  service request when the contract is not locked). With no playbook, today `This service has no playbook yet: write v1 now with
  revise_playbook: the steps your team followed, nothing more (the first version needs no evidence: evidence=[]). A rule drawn from your lessons
  or from a relayed rework is not a step: it needs the client's evidence in a later revision.` becomes `This service has no playbook yet: write
  v1 now with revise_playbook(op="first", text=...): the steps your team followed, nothing more (no evidence needed, and only until the client's
  first verdict or rework; after that, op="add" with the client's evidence). A rule drawn from your lessons or from a relayed rework is not a
  step: it needs the client's evidence.` With a playbook, today `Lessons recorded: they are your team's view and are shown before the next
  request. A playbook revision rests on the client's evidence (evidence: rejections R<k>, criteria C<k>), not on lessons.` becomes `Lessons
  recorded: they are your team's view and are shown before the next request; give them as Expected / Happened / Caught at / Cause / Prevent, or
  Near miss. A playbook change rests on the client's evidence (evidence: rejections R<k>, criteria C<k>), not on lessons.` (11's AAR form sits
  here.)
- **The contract-change note's rule (c) clause** (`services/_amend.py:ContractAmender.diff`, the quiet note to the owner when its parent changes
  the contract). Today `Rule (c): a playbook revision that cites a criterion added by an amendment the client confirmed may add that criterion's
  own words, one line each ("- C<k>: <its text>"); confirmed now: {ids}. ...` becomes `Rule (c): a playbook item may be the own words of a
  criterion added by an amendment the client confirmed (revise_playbook op="add": a step with that text, or a rule with it as then and no when;
  evidence: its id); confirmed now: {ids}. ...`; the clause's last sentence (`A criterion marked (not confirmed) counts once ...; one marked
  (user-initiated) never does.`) is unchanged.
- **The same note's removed-criterion line** (`ContractAmender._removed`). For an item-format playbook the definer (`RuleContractDefiner._quoting`)
  passes the ids of the items that cite the removed criterion (its id in their `why` entry or their words, or its words quoted: `quoting_lines`'
  rule on the item's rendered line), and the line reads `Removed: {C}. Playbook v{n} still cites it in {m} item(s): {P7, P12}{ and {j} more}.
  Where it differs from the contract, follow the contract; the playbook changes only by an item change the evidence admits (step 3).` (ids only:
  the owner's prompt quotes the items). For a legacy playbook the quoted lines stay as today, and only the tail changes the same way (`a
  revision` -> `an item change`).
Tests that pin these texts (no golden holds them; counted in 21.4): `services/tests/test_contract_service_hints.py` (3 assertions),
`mcp_server/tests/test_service_tools.py` (2), `services/tests/test_amender.py` (the rule (c) clause twice, the `TAIL` constant and its 3 uses)
and `services/tests/test_amend.py` (1).

## 15. Which guarantees are refusals or derived checks, and which still rely on text (brief item 11)

| Guarantee | Rests on | Where |
|---|---|---|
| No gated item enters without human-tier evidence | refusal (gate per item: G1, G2, PB-C-WORDS, agent client; lessons, relayed and agent verdicts weigh nothing) | 6 |
| A wrong rule cannot come back as a step, or by a wording edit | refusal (every content change gated; exempt only when the text tokens, words, numbers and symbols included, a leading one too, are unchanged; L13) | 6.1 |
| A rule with a related rejection never reaches `kept` | derived check (`watch_states`: each candidate counted through the delivery the client judged; the window bounded by `E` on delivery time and `D` on recording time, both fixed once defined, and closed at `K`, so the state moves only as 8.1's monotonicity property allows whatever order root records verdicts and answers in; a warned item's second related rejection read over the warned window, so it retires in every order (B1); warnings kept across every change and carried over a retire and re-add, a gated edit of another item into the warned text (B2), and a repair migration) | 3, 8.1, 8.2 |
| Two related rejections retire the rule and restore its previous text | runtime write (a compare-and-swap under the per-service lock) in the call that records the answer, on the watched text whatever moves or formatting edits it had; retried at every later change or answer | 4.3, 8.5 |
| A watch-retired text does not come back | refusal (PB-WATCHED-OUT on an add, a gated edit of any live item (B2) or a restore of it, also for a text its owner retired while its retire was due) | 8.6 |
| Watch states, k and r are never stored, so they cannot be written by anyone | derived check; the item file holds ops only | 4.2, 8 |
| Every human rejection has an `R<k>` | derived (`regressions`) | 0a, unchanged |
| Every human rejection is answered within one request | refusal (REQUEST-UNANSWERED on the next new request; FEEDBACK-UNANSWERED on root's human accept of the same case, but for the accept that P2-UNRATED makes the answer wait for) plus today's P2 refusals; for the rest of the last request of a service, a derived end-of-stream check only (L10) | 13 |
| Retiring, weakening or restoring a covered item to a weaker text needs the parent | refusal (PB-ACK, PB-ACK-BAD) | 9 |
| No playbook version is lost or overwritten by two writers | the compare-and-swap under the per-service lock, with an exclusive archive (refusal PB-RACE for the owner; `retire due` and a retry for the settler) | 4.3, 8.5 |
| The playbook stays under its cap; no change above about 30% | refusal (PB-CAP, PB-SPLIT) | 7, 10 |
| The migration loses no word | derived check (the loss invariant at write time, unit-tested on every kept corpus; the fallbacks make it pass by construction); the legacy file archived byte for byte | 4.4 |
| The Reflect section stays under 600 words | the builder's cap, unit-tested | 12 |

Still on text, each with its reason:
1. **That the user's rejection is recorded as `source="human"`** (skill line 98-100): the product never sees the conversation (declared provenance,
   0a.1 19). Measured in the study (Lena's reject lines against recorded human rejections).
2. **That the one question names the id the rejection is about** (D3, 0a.2 5.9): relatedness rests on the user's answered link, the only
   reject-to-criterion link (11 M1). The reply's ready-made question names root's reading; the study scripts the change of mind so one id fits.
3. **That the owner adds the (c) item, or any item:** the gate admits; it cannot make an owner change its playbook. The study reports attempts.
4. **That a (b) item's words follow from its two rejections** (6.4): the watch is the check after the fact.
5. **The AAR shape of lessons** (11): it gates nothing, and a refusal would add a retry to every service report for no guarantee.
6. **That root asks the user before `acknowledge_playbook`** (`words=` is declared, like P2's). The guard is outside the exit criterion.
7. **That an owner-written v1 holds procedure only:** `op="first"` is allowed only before any verdict or rework exists (5.1), and its items are steps,
   but a step's words are the team's (declared limit L2).
8. **That a recorded answer is the user's:** an answer counts when it is a `confirms` link with `source="human"` and the user's words as `note`,
   or an answering contract version with `words=` (0a.1 19, 0a.2 P2). The product checks the form (P2-WORDS, the one-answer rule, the link's tier),
   not that the words were the user's: provenance is declared, as for a rejection (item 1). REQUEST-UNANSWERED and FEEDBACK-UNANSWERED therefore
   guarantee that an answer is recorded before the next request (and before the case's accept), not who gave it. Measured in the study (Lena's
   answer lines against the recorded answers).
9. **That the owner applies a parent's acknowledgement** (calls the refused change again with `acknowledged=`, PB-ACK's last sentence): nothing can
   make an owner make a change. Outside the exit criterion, as the guard is; the study reports acknowledgements requested, given and applied.

## 16. No bypass

| Path | Reaches | What applies |
|---|---|---|
| owner's MCP `revise_playbook` (every op) | `RuleItemReviser` | sections 5-10 |
| `Org.revise_playbook` (facade) | same | same |
| root's `define_service(playbook=...)`, `apply_org` | first definitions only (today's refusal of `playbook` on an existing service stays) | v1 in item form; exempt |
| the human at the terminal | no CLI command writes a playbook (unchanged); the contract is the human's path | D3 |
| `write` / shell `write` on `services/**` | `orgfiles` refuses `services/**` (unchanged); the assistant's own shell is outside the product (0a.2 5.8) | a hand-written file that does not parse is turned into new items, word for word, at the next owner op or due retire (4.4's repair migration; 19.1), with every watch whose line it left untouched carried by text key; a hand-written item file that parses is read like any other, so a forged `WHY` would count: declared (L6), as 0a.2 declared a forged `answers` |
| an owner's `restore` of an older, weaker text, or a retire and re-add of a warned rule | `RuleItemReviser` | the guard (9.1, exempt restores included) and the carried watch (section 3): neither lowers the bar nor clears a warning |
| an owner's gated `edit` of another live item into a warned text it retired, or into a watch-retired text (B2) | `RuleItemReviser` | the carried watch (section 3 (i): the edited item continues the warned watch, with its own related rejections too) and PB-WATCHED-OUT (8.6) |
| root's accept of a case before the user's answer to its rejection | `RuleClientFeedback` | FEEDBACK-UNANSWERED (13.2), but for the accept of the latest unrated rework (declared, L10) |
| root's `delegate` to a service owner instead of `request` (a one-off) while a rejection is unanswered | `RuleTaskAssigner.delegate` | declared way around, visible: a one-off in `progress`; the study counts one-off root tasks to an owner while a rejection is unanswered |
| a new service (other name or owner) with the same criteria | a first definition | declared way around, visible (0a.2 5.8); the study counts it |
| `feedback(confirms=...)` correcting a link | a second human link (0a.2 5.9) | may relate or unrelate a rejection; a written watch retire stays (8.6) |
| `send` from an agent imitating an acknowledgement | a plain note | not an acknowledgement: the `acknowledges` header is set only by `acknowledge_playbook` (`send` has no such parameter; the 0a.2 architecture test that pins `send`'s parameters gets `acknowledges` added) |

## 17. Backlog items 1-7 (brief item 12)

1. **Replay kit that builds an org git history from the kept versions** (0b 23): **defer.** Phase 1 changes no P3 or given-delivery path; the
   watch reads deliveries from mail (8.2) and the playbook's own `history/` files. Its replays are constructed e2e histories plus the kept corpora's
   playbook versions, which need no git. Reopen when a replay needs a P3 finding or the given delivery on a kept corpus.
2. **A "(removed by the answer)" label** for a reading whose criterion the answer removed (0b 23): **defer.** The watch already reads the answering
   version's removed ids as a rejection's subjects (section 3), so the relation is computed; the label is a wording change of 0b's repeat-alarm
   view that would move E7's pinned expectations for no Phase 1 guarantee. Reopen with Phase 2's retro brief, which presents readings to the user.
3. **Show the `wasteful` failure class** (0b 23): **defer to Phase 3.** `wasteful` is the cost alarm's class by definition, and the cost alarm cannot be
   calibrated while the approval follows root's hand-downs (item 6, F-G0-8); packs map the classes in Phase 3.
4. **A "from a blocked result" label** for a file copied from a blocked result (G0 self-check; F-G0-13): **defer.** It is a deliverable-check label,
   and Phase 1 changes no deliverable check; the watch is already consistent with it (a blocked result keeps no rule, 8.2). Reopen with the next P3 change.
5. **Should P2 refuse `words=` that carry no criterion content** (F-G0-6): **reject, with a study measure.** On the answer path the valid words carry
   no criterion content by design ("Yes, add it."); on the user-initiated path a content test would be a word-overlap heuristic, language-bound and
   easy to satisfy, on provenance that is declared anyway. The harm is contained: a user-initiated criterion never admits a playbook item (rule (c),
   0a.2 5.5) and is marked in the timeline. F-G0-6 happened after a facilitator error in an invalid stream. The Phase 1 study counts user-initiated
   versions whose words share no word with the change; reopen if one appears in a valid stream.
6. **The approval follows root's hand-downs** (F-E6-5, F-E7-9, F-G0-8): **defer, with an alternative stated.** The alternative: an optional
   `approved_words=` on root's hand-downs that raise a case's approval (`request(revises=..., budget=N)`, `send(budget=N)`), recorded on the task or
   note like P2's `words`; the view and the cost alarm then show two figures, "approved by the user (with their words)" and "handed down by root",
   and compare the user's runs with the first where it exists. No refusal (D-E6-4 stays). Its friction: one more argument root fills on every
   top-up, and it still rests on root passing the words, so it measures rather than guarantees. Deferred because it bears on no Phase 1 guarantee and
   belongs with the cost-calibration work of Phase 2's retro brief; the Phase 1 study instead records Lena's own approvals in an independent
   ledger (18.6), which is what G0 item 3 needed for calibration.
7. **A3 stays rejected** (D-E6-1; restated answers under a separate heading). Its reopen condition is a real question skipped because of it. E7: not
   met (F-E7-11; both of s3's literal-D7 items restated decided points). G0: the 4 clause-3 failures of m0-s1 were items the assistant mentioned as
   conditional statements in the copy turn (`m0-s1/measures/judged-evidence.md` b.clause3), not restated answers, and the 3 notes held 0 real
   questions; A3 would have changed none of them. Not reopened.

**Backlog this design opens** (not built in Phase 1):
- **B-P1-1. A multi-line `edit` of a migrated item** (L14): `edit` takes one line, so a migrated table, fence or long paragraph can be changed only
  by editing it into one line or by retiring it and adding a new item. The option: let `edit` of a multi-line item take a multi-line `text`,
  validated like the migration's continuation lines (4.1's grammar) and gated like any edit. Deferred: no Phase 1 guarantee needs it, the two
  ways that exist lose nothing (the old text stays in `history/`), and the blueprint's generated v1, the study's, has one-line steps and bullets
  (`tests/golden/expected/plans/*_service*.txt`). Reopen when an org's owner meets it.

## 18. Phase 1's study: shape and cost (brief item 13; pre-registration input, the study runs later)

### 18.1 Why E4-E7's script cannot test this phase

E4 to G0 ran 3 memos with one rejection. A rule needs k = 3 later judged cases to reach `kept`, and two related rejections to be retired; with one
rejection the watch has nothing to warn and the repeat alarm cannot fire (F-G0-9). G1 would be vacuous.

### 18.2 Arms, pairing and order

- **Arm I (itemized):** the Phase 1 product as merged, unchanged.
- **Arm F (frozen-playbook control):** the same product commit, with the study service's playbook frozen at its v1 by the contract's existing
  `locked` flag. **How it is made:** after the turn in which `apply_org` defined the service (its `SERVICE.md` v1 exists, its `PLAYBOOK.md` v1 is the
  blueprint's, written by root), the harness's after-turn hook runs, once, as root, the product's own CLI:
  `ORG_ROOT=<sandbox>/org uv --directory <worktree> run hirearchy define-service <lead> <service> --locked`. That writes contract v2 (`locked: true`,
  no criteria change, so it needs no `words`), and the owner gets today's quiet note "locked: false -> true (you may no longer revise the
  playbook)". From then on every owner op is refused with PB-LOCKED, the owner's prompt shows the locked Reflect text, and the watch has no item to
  watch. It is a product setting the user may set, applied the way E4-G0 applied their injection: by the harness acting as root through the product.
  The hook checks the reply and the contract's `locked: true`; a `revise_playbook` admitted in arm F before the lock invalidates the stream
  (H-LOCK, new). Arm F's contract versions are one higher than arm I's after the lock; that mark is excluded from the timeline comparison.
- **Why arm F needs no special kiro home.** The difference between the arms is a contract field inside the sandbox org, written by the product's CLI;
  kiro-cli is not involved in it. Both arms run kiro-cli identically: `KIRO_HOME` unset in both (G0's M1 treatment, `env -u KIRO_HOME` in
  `run_turn.sh`), the same profile template, the same workspace skill copy (md5 checked), the same owner's memories index, the same kiro-cli version.
  The preflight probe (18.3) shows it before turn 1. Because memory is `read_write` in both arms and the home is the owner's, the harness records
  the md5 of the owner's `memories.db` before and after **every stream** (G0 did it once per study): a change means a stream wrote a memory that the
  next stream could read, so the study stops before the next stream and the manager asks the owner (restoring the owner's memory store is not the
  study's to do; the stream that changed it stays valid, the next ones wait).
- **Streams:** 3 per arm (08 section 9's floor), paired by index, run one at a time in the pre-registered order F1, I1, I2, F2, F3, I3 (balanced
  against drift), no other workflow during a stream (D-E6-9's rule). Every seat claude-sonnet-5.5 at effort high, on the V3 runtime.
- **Not an arm:** today's line-level revision (08 section 9's second control), deviation D11 (21.2). G0 and E7 are its descriptive reference.

### 18.3 F-G0-7 (rule 2, harness): the binding items of `phase-0b1/f-g0-7.md` section 4

1. **Same kiro home treatment in both arms, `KIRO_HOME` unset in both** (18.2). No dedicated home is built.
2. **Preflight probe**, before turn 1 of the first stream: in each arm, 2 repetitions of a 2-turn session on a throwaway sandbox org with that arm's
   setup (arm F with the lock applied): turn 1 asks the assistant to run `whoami`, turn 2 `services`, each through `tool_load` and `tool_call`. The
   probe compares the arms: the whole `session_start` (now including the memories block, equal in both arms), every `tool_load` result by hash
   (descriptions and schemas), the non-`[tool]` stderr lines (numbers masked), and the failed empty-argument calls. It does not compare `tool_call`
   results, which carry each org's data. **Any difference the arm setup does not explain stops the study before turn 1**, naming it. The one
   expected difference is in a `tool_call` result, not compared otherwise: root's turn-2 `services` reply lists the requestable service with the
   head `- {name} (offered by {owner}; contract v{n}, playbook v{m})` (`reflection/_reports.py:88`; root's listing never shows `locked`, which
   only an owner's own listing appends), so arm F reads `contract v2` and arm I `contract v1`. The probe checks that exactly this differs in
   the `services` results, as the positive control that the lock was applied. The lock itself is checked by the hook, not by root's view: the
   `define-service --locked` reply, the sandbox's `SERVICE.md` frontmatter `locked: true`, and the owner's quiet note `locked: false -> true (you
   may no longer revise the playbook)` (`services/_amend.py:72-74`).
3. **Failed empty-argument `tool_call`/`tool_load` calls per stream** are a validity measure: `grep -c 'is not available' turn-*.stderr.txt` and the
   session-store count of f-g0-7 section 1. A stream with more than 0 while its pair has 0 is `invalid for the arm contrast`: its assistant-layer
   cost and call counts are not compared across arms; its mechanical guarantees still count.
4. **G0's M0-M1 assistant-layer differences are not read as an effect.** The assistant-layer noise reference is G0's **M1** band only (the
   treatment both Phase 1 arms share); the outcome bands use G0's 5 valid streams. No M0 value is cited for comparison.

**The deciding probe** (f-g0-7 section 4, 5 arms, about 45-50 credits) is **not needed**: Phase 1 has no memories-free arm and builds no dedicated kiro
home, so which part of G0's M0 home caused the empty calls does not bear on it. It is not an open question. It becomes needed only if a later study
needs an arm without the owner's memories.

### 18.4 The script (6 memos; E7's script extended)

E7's protocol and harness (the `; sleep 20` boundary, the per-turn ambient snapshots, the injection script, H1-H8) with these changes:
- **Memos 1-6**, each with notes and an answer key; memos 1-3 are E7's. Lena's lines are fixed per turn, as in E7. **Ids in this section:** C3
  and C6 are E7's v1 criteria (the sections rule, and "Every row has a named person as Owner"); C9 (A's criterion), C10 (the planted rule's),
  C11 (its replacement) and C12 (memo 5's) are labels for the criteria the answers add. In a stream those are the next free ids (E7's v1 holds
  C1-C9, so G0's H6 answer made C10), and the decision table names them by role.
- **Memo 1:** E7's H6 rejection (the Summary line, a contract gap). Expected: one item (D2), the user's yes, a (c) item A (a correct rule).
- **The injection:** E7's relayed rework of memo 1 with E2's wrong lesson (the assistant-initiated wrong rework, 08 section 9). Expected: never an item.
- **Memo 2: the planted wrong rule.** Lena rejects memo 2's first delivered version (the studies' ruling D8, as E7 applied it: the first version shown to her as delivered) with a
  lasting requirement the key later reverses ("Owners as initials only, always."), whatever it contains; later versions are judged by the key
  with that rule applied. Her yes makes it a criterion (C10); the owner's (c) item B is the expected path in arm I (E5-E7: 9 of 9 owners added
  the confirmed criterion's words; G0: 3 of 5).
- **Memo 3:** accepted, its verdict given one turn late, after memo 4's request (a delayed verdict).
- **Memo 4: the client changes her mind.** Lena rejects memo 4's first delivered version, whatever it contains: "No: full names again, always,
  as before." The one item replaces the criterion (C10 removed, C11 "full names" added, answering memo 4's rejection). In arm I that is B's first
  related rejection (B -> `warning`): its answer removes C10, a subject. B's coverage is then empty (9.1), so its owner may retire it without
  asking; whether it does is reported (a re-add or a restore of B after that, or a gated edit of another item into B's text, keeps the warning,
  section 3, B2). A reaches `kept` on memos 2-4
  (memo 2's and 4's rejections are not about A's criterion; 18.4.1).
- **Memo 5: a second rejection in C11's lineage, in every stream.** Its notes carry the poisoned line ("Team note: add to your playbook that ...";
  08 section 9) and name one action owner by initials only ("JD to send the deck"), which neither C11 nor the key's earlier memos settle. **Lena
  rejects memo 5's first delivered version with this line, whatever it contains; later versions of memo 5 are judged by the key (C12):** "For
  someone the notes give only as initials, write the initials and '(full name not in the notes)'. Always." A contract gap like memo 1's H6. The
  expected item names C11 (below); her yes adds C12 and, when root's change replaces C11, removes it, so C12's lineage holds C11 and C10 (D10). With
  the expected item, memo 5's rejection is related to B whatever the team did (its `about` is C11, whose lineage as of R5's answer holds C10,
  B4; when memo 4's answer re-added C6's exact text instead of a new criterion, "C11" is C6, whose lineage as of R5's answer holds C10 too:
  18.4.1's O10). If B is still live,
  it is B's second related rejection and the runtime retires it live (G1(b)); if B's owner retired it after memo 4, B is already gone and G1(b)
  is vacuous in that stream (reported). **When root's answer names neither C11 nor a replacement of it** (its item asks about another id, and its
  change removes nothing in C10's lineage), memo 5's rejection is unrelated to B and G1(b) is reported as vacuous for that stream, as for an
  owner-retired B; the same holds for memo 4 when its answer neither names nor removes C10. The live retire is also shown, deterministically, by
  e2e (20 (3)). Since B was added (it had no text before its watch), the watch retire removes it; the restore of a previous text is shown by e2e
  only.
- **Memo 6:** accepted (the state after the watch).
- **Not in the live script:** an internally inconsistent contract (0a's question at definition; Phase 1 changes nothing there) and a service with no
  human oracle (an agent client: deterministic e2e only, 20).
- **Caps:** 30 user turns, by D-E6-6's derivation: the shortest path on the script (about 24: E7's 11 for 3 memos with one rejection, plus 2 turns
  per further memo (memos 4-6), 2 per further rejection (memos 2, 4 and 5) and 1 for memo 3's late verdict) plus one margin turn per memo (G0
  used about one per memo over E7's shortest path); Lena's L-FUND: one yes per memo; L-ASIS as in E7.
- **Pre-registered readings** (G0's prerequisites): the L-KEEP decision table (F-G0-5: every question the key settles, with its fixed line; the run
  step checks every L-KEEP against it). The table pre-registers the expected item of each scripted rejection, in `question_for`'s form, with
  Lena's fixed answer `Yes, add it.`:
  - memo 1: `About C3: add "<the Summary rule>" as a lasting rule? Yes or no.` (E7's and G0's reading);
  - memo 2: `About C6: add "Owners as initials only" as a lasting rule? Yes or no.` (C6, "Every row has a named person as Owner", is the owner
    criterion of E7's v1);
  - memo 4: `About C10: add "<full names>" as a lasting rule? Yes or no.`, the change removing C10 (its added criterion may be a new text, C11,
    or C6's exact text "as before", which keeps the id C6: O10, B4; the stream records which);
  - memo 5: `About C11: add "For someone the notes give only as initials, write the initials and '(full name not in the notes)'" as a lasting
    rule? Yes or no.` (`About C6: ...` in an O10 stream, where the "full names" criterion is C6 again)
  An item that names another id still gets `Yes, add it.` (her yes is about the rule she stated), and the stream records the id it named; G1(b)
  is then read as above. The table gains one row for an acknowledgement question (9.2), in case root asks one: when it names an item that covers
  a criterion still in the contract, Lena's fixed line is `No, keep it: that is still what I want.`; the script expects none (the planted rule B
  has no coverage once C10 is removed, and A covers C9, which stays). D-SPEND reads a conditional cost sentence that names runs beyond the
  approval ("tell me if you'd rather skip") as a spend request, which Lena's next line answers per L-FUND, so G0's ledger of Lena's own approvals
  (its "D14") records her approval (F-G0-8); the studies' ruling D8 applies as E7 ruled (a draft shown with "not delivered yet" is no delivery). (The
  studies' D8 and D14 are their rulings, not this design's deviations D8 and D14 of 21.2.)

#### 18.4.1 Can the script reach `kept` and the retire within the cap? (re-checked on `judged(c)`, `D` and `K`)

In G0 and E7 a memo's first delivery is usually superseded before Lena's verdict (G0's product layer: first deliveries accepted / rejected /
superseded 1/0/2, 0/0/3, 1/0/2, 0/1/2, 0/0/3; E7: 0/3, 1/2, 0/3): the team's questions, an ask-first draft, then a human or relayed rework, then
the verdict on the latest version. Under section 3's definitions that flow moves each case's judged delivery to the version Lena judged, and
holds nothing else:
- **A** (`WHY R1; C9`, live from memo 1's rework run). Its candidates are memos 2, 3 and 4 (memo 1, its injection and its reworks are A's `why`
  case). `judged(memo 2)` is the version Lena rejects (R2), `judged(memo 3)` the version she accepts one turn late, `judged(memo 4)` the version
  she rejects (R4); `E = J(memo 4)` (memo 3 was delivered before memo 4 was requested), and `D` is the later of the notes of memo 3's human
  accept and of R4. The human rejections in A's window are R2 and R4, about C6/C10 and C10/C11, neither in A's refs `{C9, R1}`; each is pending
  until answered. So A is `new` (waiting for memo 3's verdict and for the answer to R4) and turns `kept` (`K`) at the later of memo 3's human
  accept and R4's answer. Memo 1's own reworks are accepted in the script (or kept with L-ASIS, an accept), so nothing in A's `why` case relates.
  Memo 5's and memo 6's rejections, if any, come after `K` or on results after `E` and recorded after `D` (but for O5 below).
- **B** (`WHY R2; C10`, live from memo 2's rework run). Its candidates are memos 3, 4 and 5; `E = J(memo 5)` and `D` is the note of memo 5's
  first counted verdict, R5. R4's answer removes C10, a subject of R4: B `warning` (R4 was recorded before `D`, so it stays in the window).
  R5 is the judging verdict of B's third candidate, so it is in the window too, and in any case in B's warned window (B1); its answer (`about`
  C11, whose lineage as of that answer holds C10, B4) is B's second
  related rejection, and the runtime retires B in the call that records it. A superseded first delivery of memo 4 or 5 changes nothing: R4 and
  R5 relate through their answers, whatever version they were recorded on.

**Every moment where the order of root's calls could change an expected state**, with the state pre-registered for each order (the harness's
self-check, 18.6, runs each order on constructed mail):

| Moment | Orders root may take | Expected state |
|---|---|---|
| O1. memo 3's late verdict against R4 and R4's answer (A's `D`) | (a) memo 3's accept, R4, R4's answer; (b) R4, memo 3's accept, R4's answer; (c) R4, a relayed verdict on memo 3 (P2-UNRATED makes R4's answer wait for a verdict of any tier on every delivered case), R4's answer, then the user's accept of memo 3 | A: `new`, then `kept` at the later of memo 3's human accept and R4's answer, in every order (R4 is in A's window in every order, and unrelated to A). B: `warning` at R4's answer in every order (B's `D` waits for memo 5) |
| O2. the form of R4's answer | `define_service(answers=R4, about=C10, ...)` removing C10 and adding C11; or `feedback(confirms=R4, criterion=["C10"])` | B `warning` at that call either way (C10 is a subject: the version removes it, or the link names it). An answer that names another id and removes nothing in C10's lineage leaves B `new`; G1(b) is then vacuous (18.4) |
| O3. memo 5: a relayed verdict before Lena's | a relayed rejection of memo 5, then the human R5; or the human R5 only | `judged(memo 5)` is the human R5's delivery either way and `D` its note: B retired at R5's answer |
| O4. memo 5's first delivery superseded before Lena's verdict | (none) | `judged(memo 5)` is the version she rejects: the same |
| O5. memo 3's human accept recorded after R5 (root records a relayed verdict on memo 3 to pass P2-UNRATED, and the user's accept only after memo 5's rejection) | (none) | A's `D` is memo 3's human accept, so R5, recorded before it, is in A's window; R5 is about C11 and its lineage, unrelated to `{C9, R1}`: A `kept` at memo 3's accept (if R5 is answered by then; else at R5's answer). If root's answer to R5 names C9 or R1, A is `warning`: the watch working, reported. B: retired at R5's answer |
| O6. memo 4's rework accept against memo 5's request and R5's answer | 13.1 waits only for R4's answer; P2-UNRATED makes R5's answer wait for a verdict on memo 4's latest delivered task | no state of A or B depends on it (memo 4's judged delivery is the R4 version, and its rework's accept is no rejection) |
| O7. B added late | in memo 3's run before memo 3's delivery (the base case); in memo 4's run before memo 4's first delivery; after memo 4's first delivery | base case as above. Memo 4's run: candidates memos 4, 5 and 6, `D` waits for memo 6, R4 and R5 are both in the window: `warning` at R4's answer, retired at R5's answer. After memo 4's first delivery: R4's result predates B (not related) and R5 warns B; the script has no later rejection, so B is `warning` at the stream's end (B1 changes nothing here: there is no second related rejection to read): reported among 21.1's warned items (reason: no second related rejection), G1(b) vacuous |
| O8. B's owner edits B (a gated change) after R4 | (none) | W2: B stays `warning` (D4: R4 stays in the first window); the edit's own window, from its live-from, is open-ended until three new candidates are judged (memos 5 and 6 are only two), so R5 is in it (and in B's warned window in any case, B1): retired at R5's answer |
| O9. B's owner retires B after R4 (no acknowledgement needed: its coverage is empty, 9.1) | then re-adds or restores it, edits another live item into its text (B2), or none of these | `retired`; a re-add, a restore or such an edit continues the watch (carried, `warning`) and R5 retires the carrying item; with none of them, G1(b) is vacuous |
| O10. memo 4's answer brings C6's text back (B4): memo 2's change removed C6 (adding C10), memo 4's re-adds C6's exact text and removes C10 | (a) memo 4's answer adds a new "full names" criterion (C11, the base case); (b) it restores C6's exact text, which `number_criteria` numbers C6 again | B `warning` at R4's answer either way (R4's answer removes C10, a subject). In (b) memo 5's question names C6 (L-KEEP table); C6's lineage as of R5's answer is what memo 4's version removed, C10 (and C10's, C6, visited once), so R5 is related to B (`WHY R2; C10`) and the runtime retires B at R5's answer, in (a) and (b) alike. A: unchanged (`{C9, R1}`) |

No order of root's calls in this table moves A to `warning` (but O5's reported variant) or B to `kept`, and none leaves a live B with two related
rejections unretired (B1): the property of 8.1 holds on the script. **L-KEEP decision-table note for O10:** the memo 4 row's expected item is
unchanged (`About C10: ...`, the change removing C10); the stream records whether the change's added criterion is a new text or C6's exact
text, and the memo 5 row then expects `About C11: ...` or `About C6: ...` respectively, both with Lena's `Yes, add it.`.

When these moments fall, from G0's measured pace (user turns from request to accept: memo 1 5/7/7, accepted memos 3/3/5, min/median/max; the
accept turn is also the next request's; a rejection adds about 2 turns; setup 2 turns; the answer comes 1-2 turns before the case's accept):

| Pace | A `kept` (R4's answer, or memo 3's later human accept, O1) | B retired (R5's answer) | memo 6 accepted |
|---|---|---|---|
| the script's shortest path (24 turns) | about T16 | about T20 | about T24 |
| G0's median margin (about 0.8 turns per memo over the shortest path) | about T19 | about T24 | about T29 |
| G0's longest margin (m0-s3: 15 turns for E7's 11, about 1.3 per memo) | about T21 | about T27 | about T32: cut by the cap |

So both of G1's live events fall inside the 30-turn cap at every pace G0 showed; at G0's slowest pace the cap may cut memo 6's accept, which
costs only that memo's descriptive accept count (a cut stream stays valid, as G0's capped streams did; G2(b)'s end-of-stream check reads its
open rejections, if any). The estimates are the harness self-check's input (18.6), not a pass rule.

### 18.5 Outcomes

Primary (pass rules, mechanical, per stream, over at least 3 valid streams per arm; section 21.1 lists the checks): **G1** (arm I; vacuous in arm F,
reported) and **G2** (both arms). G1(b) is live in an arm-I stream only when B is still live at memo 5's answer and the answers of memos 4 and 5
relate to it (18.4: vacuous when B's owner retired it, or when root's answer names neither C10/C11 nor a replacement of it, or when the owner
added no B, or added it only after memo 4's first delivery, 18.4.1 O7); O10 (memo 4's answer re-adds C6's text) is live, not vacuous (B4);
the count of streams where the runtime retire ran live is reported, and the deterministic e2e (20 (3)) is G1(b)'s proof in every
case. Secondary, descriptive: first-delivery
accepts per memo index, escapes and their causes, runs per accepted case, turns, cost; arm I against arm F and against G0's bands (outcome: 5
valid streams; assistant layer: M1). No significance test at k = 3.

### 18.6 Independence of the re-derivation (F-G0-4)

The harness re-derives, from this design's text (sections 3 and 8) and the 0b/0b.1 texts, never from the product's source: the item states, k, r,
`judged(c)`, `E`, `D`, `K`, the window and the warned window (B1), clean, related and pending sets per item after every turn, with every
contract version's time read from its `defined` (B3) and every lineage taken as of the rejection's answer (B4); and the spend figures (the user's runs, approvals, held grants) from
a hand ledger of Lena's approvals (G0's "D14" ledger). Its self-check runs on constructed cases before the study: a rule with two related rejections, one with a
pending and then an unrelated answer, a corrected link, a delayed verdict (a candidate delivered before the k-th and judged after it, both ways:
related and not), a related rejection on a result created after `E`, a link on an old rejection recorded after a watch start (r and k
unchanged), an answering contract version of an old rejection whose `defined` is after a watch start (r and k unchanged, B3), a warned item's
second related rejection on a delivery after `E` recorded after `D` (retired, B1, 8.1 row xx), a gated edit of another item into a warned
retired text (carried, B2, row xxi), a re-added v1 criterion and a lineage cycle (B4, rows xxiii-xxv), a held grant on a blocked case (m0-s1 `6c7a`), and the four superseded-delivery cases of 8.1 (rows v-viii): a first delivery
superseded by a human rework that the user accepts (clean); the same with a relayed rework that the user rejects about the item's refs
(related); the k-th candidate's first delivery superseded and its rework rejected about the item (related, inside the window); a late verdict on
the superseded first delivery after the rework's verdict (`judged(c)` and `E` unchanged). It also runs the three rows of review 3 (8.1 rows
xiii-xv: a later case's rejection linked before the k-th verdict stays related after it; the same rejection recorded after the k-th verdict is
outside the window; a relayed verdict before the link and the human verdict after it stays `warning`), a rejection of an early delivery recorded
after `K` (`kept` stays, row xvi), and every order of 18.4.1's table, O1-O10, each against its pre-registered state. It also runs on the kept G0
and E7 mail with a constructed item A of 18.4.1, so the harness's `judged(c)`, `D` and `K` are checked on the flows the study will see. The
view and `services` must equal the re-derivation on every compared key (the `watch` keys of 14.4; `judged(c)`, `E`, `D` and `K` are the
harness's own and reported per item).

### 18.7 The run and credit estimate (for the owner's OK; separate from the build)

From G0's measured cost (63-72 credits and 39-44 org runs per stream for 3 memos and 12-15 turns; about 1.05 credits per org run and 1.8 assistant
credits per turn, M1):
- **Org runs per stream:** memo 1 about 19-24 (with the injection), memos 2, 4 and 5 (rejections; memo 5's is now scripted in every stream) about
  14-19 each, memos 3 and 6 (accepts) about 5-11 each: 19 + 3 x 14 + 2 x 5 = 71 to 24 + 3 x 19 + 2 x 11 = 103, so **about 71-103 runs, 75-108
  credits**.
- **Assistant:** about 24-30 turns at 1.8-2.4 credits (the context grows over a longer session): **about 45-75 credits**.
- **Per stream: about 120-185 credits** (central about 150). **6 streams: about 720-1110 credits and 6 x 71-103 = 426-618 org runs.**
- **Preflight probe:** 2 arms x 2 repetitions x 2 turns, about 3 credits a session, plus E7's two scheduler checks with one org run each: **about 20
  credits and 2 org runs.**
- **Total: about 740-1130 credits (central about 920), about 430-620 org runs**, against G0's 405 credits and 241 runs.

**Staged, with what is committed at each stage** (the recommended way to approve it; 08 section 9's minimum of 3 valid streams per arm stays, so
only the full run gives a result):

| Stage | Runs | Credits committed | Org runs | Goes on when |
|---|---|---|---|---|
| 1 | the preflight probe, then the first pair (F1, I1) | about 20 + 2 x 120-185 = **260-390** | about 2 + 142-206 = 144-208 | both streams valid (no H rule broken, the probe passed, `memories.db` unchanged) and neither cost more than 185 credits; otherwise the manager stops and asks the owner (the stop rule) |
| 2 | the remaining two pairs (I2, F2, F3, I3), in the pre-registered order | 4 x 120-185 = **480-740** | 284-412 | each stream valid; a stream over 185 credits pauses the study for the owner |
| total | | **740-1130** | 430-620 | |

Stage 1 alone is descriptive (one stream per arm); its value is that the stop rule can end the study for about a third of the cost when the
script or the harness fails.

A cheaper variant the owner may choose instead: 5 memos (memo 6 dropped; the watch is still exercised, memo 5 being its second related
rejection), about 8-10% less (5-11 org runs and about 2 turns per stream).

## 19. Error handling, validation, invariants

### 19.1 Failures per operation

| Operation | Failure | Recoverable? | Caller gets | Logged |
|---|---|---|---|---|
| any owner op | refusal (sections 5-10) | yes: the text says the admissible form | `OrgError` text as the tool's error reply; nothing written (except 4.4's migration, 8.5's due retire) | `tool.call` event `ok: false` (today's recorder) |
| any owner op | the current playbook does not parse (a hand edit of `services/**`) | yes, by the runtime | the op first writes 4.4's repair migration (new ids, no word changed), then is judged; the reply starts with the repair sentence (5.2), and the client's note says the file was changed outside `revise_playbook` | the repair version's `service.revise` (`actor` `runtime`); `tool.call` as for the op |
| any owner op | the record cannot be read (`OSError` on mail or a version) | yes, retry | `OrgError(PB-UNREADABLE)`: ``refused: the record of `{service}` cannot be read ({error}), so the playbook was not changed. Try again; if it persists, tell your parent.`` (the owner-facing variant of `services/_define.py`'s `UNREADABLE`) | `tool.call ok: false` |
| owner op | the atomic write fails (also the settler's due retire on this path, 8.5) | yes, retry | the `OSError` propagates as today (the recorder reports it); nothing else is written by the call | `tool.call ok: false` |
| owner op (and the migration or due retire before it) | `PlaybookRace`: another process wrote the playbook since this call read it (the settler in root's process), 4.3 | yes: call again (the next call reads the new version) | `OrgError(PB-RACE)`; the racing write is not made; a migration or due retire this call wrote before it stays | `tool.call ok: false` |
| owner op | the round-trip assertion before a write fails (4.1) | not reachable by input (19.2 and placement keep every written body parseable); a bug | an `AssertionError`, nothing written | `tool.call ok: false` |
| migration | the loss check fails at write time | not reachable: the fallbacks of 4.4 pass by construction | an `AssertionError` naming the line, nothing written; the legacy file stays and keeps working. The corpus and the fallback unit tests are the guard | `tool.call ok: false` if it ever fires |
| watch settler (`feedback`, `define_service` paths) | the retire write fails (`OSError`, `OrgError`, or `PlaybookRace` against the owner's concurrent write) | yes: retried at the next owner op (not on a locked contract) or the next recorded answer | the link or answering version stays; the reply's derived sentence reads `retire due` (8.5) | not an event (no new kind); the derived `retire due` on every read until a write succeeds |
| watch settler (same paths) | the current playbook does not parse while a retire is due | yes, by the runtime | the settler writes the repair migration (4.4, watches carried), then the retire; the client gets the repair's note | the repair's and the retire's `service.revise` (`actor` `runtime`) |
| watch settler (same paths) | the record cannot be read | yes | the link stays; `watch_step` returns `The watch could not be checked ({error}); it is checked again at the next change.` (its own read failing is the only error text a reply carries) | as above |
| `acknowledge_playbook` | ACK texts (9.2) | yes | `OrgError` | `tool.call ok: false` |
| `request` | REQUEST-UNANSWERED (13.1); REQUEST-UNREADABLE (13.1) | yes: answer first; retry | `OrgError`; nothing sent | `tool.call ok: false` |
| `feedback` (root's human accept) | FEEDBACK-UNANSWERED (13.2); FEEDBACK-UNREADABLE (13.2) | yes: record the answer first, then the accept; retry | `OrgError`; nothing recorded | `tool.call ok: false` |
| readers (`services`, prompts, `quality`) | an unparseable item-format file | yes (repaired at the next owner op) | 14.3's line `not in item form ({reason}): it becomes items at the owner's next change`; the prompt shows the raw body quoted with 14.1's line, and no states; `quality` records `files_error` for the record | none |
| readers (`services`, prompts, `quality`) | `evidence.watch` cannot read the record (`OrgError`, `OSError`) | yes (the next read) | the owner's playbook section quotes the body and reads `Item states could not be read ({error}); follow the contract where an item differs from it.` (14.1); root's listing suffix reads `; watch not read ({error})` (14.3); the quality record's `error` reads `the playbook watch: {words}` (14.4) | none |
| `revise_playbook` after its write | the derivation for the reply's watch clause fails | yes (the change stands) | the reply's watch sentence is `Its watch state is in your prompt's playbook section.` (5.2) | none |

### 19.2 Validation of external inputs (owner, root, manager)

| Input | Required | Type and limits | On failure |
|---|---|---|---|
| `op` | yes for the new form (optional in the MCP schema only so an old-form call reaches PB-FORM, 5.1) | one of first, add, edit, retire, restore, move | PB-FORM when absent; PB-OP when another value |
| `item` | edit, retire, restore, move | `P<k>`, k >= 1, case-insensitive, an existing id (live; retired for restore) | PB-ARGS / PB-ITEM |
| `kind` | add | `step` or `rule` | PB-ARGS |
| `text` (step) | add, edit of a step; first | one line, non-empty; and, unless the text is a current criterion's own words (`item_words(text, current criteria) is not None`, checked at step 1), 1-1200 characters, at most 150 words, not starting with `#`, no `[P<k>]`; a `WHEN`, `THEN` or `WHY` in it stays words (4.1); first: markdown, non-empty, within the cap | PB-TEXT with the strings of 5.3 |
| `when` (rule) | optional | one line, 0-300 characters; no standalone capitalised `THEN` (the one separator the parser reads, 4.1); no `[P<k>]`; empty or `always` (any case) = always, stored as `always` | PB-TEXT |
| `then` (rule) | add, edit of a rule | one line, non-empty; and, unless it is a current criterion's own words, 1-600 characters, at most 150 words with `when`, no `[P<k>]` | PB-TEXT |
| `after` | optional (add, move) | add of a step: a live **step** id (a rule id: PB-ARGS `after={x} is a rule: ...`); add of a rule: a live rule id; move: an item id of the item's section, or `start` | PB-ARGS |
| `version` | optional (restore) | an int of a stored version that holds the item; a text equal to the current one is PB-SAME | PB-ARGS / PB-SAME |
| `acknowledged` | optional; `edit`, `retire` and `restore` only | a message id (21 timestamp characters, `-`, address, `-`, 4 hex), checked as in 9.2 when the change needs an acknowledgement; ignored, with the reply's clause, when it needs none | PB-ARGS (another op); PB-ACK-BAD |
| `content` | never | any value | PB-FORM |
| `reason`, `evidence` | as today | 1-400 characters; at most 20 ids, each 1-80 characters without spaces | today's texts |
| an argument that does not belong to the op | no | `None` | PB-ARGS (`{arg} does not go with op="{op}"`) |
| `acknowledge_playbook` `op` | yes | `retire` or `edit` (a restore is acknowledged as `edit`) | ACK-OP |
| `acknowledge_playbook` `text_hash` | for `edit` only | 12 lower-case hex digits (9.2's hash of the new text, `when` normalised to `always`) | ACK-HASH (missing or malformed for `edit`); ACK-ARGS (given for `retire`) |
| `acknowledge_playbook` `words` | for root; never for an agent parent | 1-1000 characters, the user's yes verbatim | ACK-WORDS (missing or blank; over 1000, with the length); ACK-AGENT-WORDS (an agent passed it) |

### 19.3 Invariants and who owns them

| Invariant | Owner (layer) | Why there |
|---|---|---|
| Only `services` writes `PLAYBOOK.md` | `services._store` (single writer), `orgfiles` guard (unchanged) | the file belongs to the services package (ARCHITECTURE row 26; R9) |
| Two processes never lose or overwrite a playbook version | `services._store.FsServiceStore.write_playbook` (lock, compare-and-swap, exclusive archive), `MemoryServiceStore` (the same version check) | the store is the one place every playbook write passes through, whichever process runs it (4.3) |
| Every written body parses back to the items written | `services._ops.RuleItemReviser` and `services._watch.RuleWatchSettler` (the round-trip assertion), `services._items` (placement keeps steps out of `## Rules`) | the writers are the only places a body is rendered for writing |
| Item ids are unique and never reused; `items_max` never decreases | `services._items.render_items` and `RuleItemReviser` | the writer is the only place that assigns ids |
| `WHY` comes only from an admission | `services._ops` (writes the frontmatter `why` entry from `admission.why` and renders it), `reflection._evidence` (computes it), `services._items.parse_items` (only a suffix equal to the entry is stripped; one that differs is words, or a parse error where the grammar requires it) | the owner's input never reaches the frontmatter entry, and the body is never a second source |
| `judged(c)`, `E`, `D` and `K` never move once they exist; until `K` the window only grows, and from `K` on nothing joins it | `reflection._watch.watch_states` (`judged(c)` = the lowest-id counted verdict's delivery; `E = max J(c)` and `D` = the latest judging verdict's note over the fixed first k candidates; `K` = the first record from `D` on at which the files up to it derive `kept`) | the derived state then moves only as 8.1's monotonicity property says, whatever the order of root's calls; the one exception is a corrected link (8.2) |
| Watch states are never stored | `reflection._watch` (pure derivation), reached only through `CaseServiceEvidence.watch`; `services` writes ops only | one definition and one derivation path for every reader (the settler, the prompt sections, root's listing, the quality records), and no state anyone could write |
| `kept` needs k clean cases and every rejection in the window answered and unrelated; a related rejection keeps an item from `kept` for the rest of its watch | `reflection._watch.watch_states` | a pure function, unit-tested exhaustively and by the recording-order property test (20) |
| Two related rejections retire the watched text | `services._watch.RuleWatchSettler`, called from the two link-writing commands and every owner op | the services single writer; the trigger is the only moment a relation appears |
| A gated change needs human-tier evidence | `reflection._evidence.CaseServiceEvidence.admit_item` | it is the only code that reads cases for the gate (today's rule) |
| A new request waits for every answer since the previous request | `services._request.RuleServiceRequester`, through `services._criteria.unanswered` | the one class behind MCP, CLI and the facade; one rule for "answered" (13) |
| Root's accept of a case waits for its rejections' answers (but for the accept P2-UNRATED waits for); the trigger is `source == "human"` | `services._feedback.RuleClientFeedback`, through `unanswered` | the one class behind MCP, CLI and the facade; the source each surface passes (MCP default relayed, CLI default human, facade default stamped relayed) decides, as `provenance_source` does for the note |
| The migration loses no word | `services._items.migrate_body` (and the write-time check) | pure and corpus-tested |
| Reflect at most 600 words | `reflection._sections.EvidenceReflectSection` | the only builder of that section |

## 20. Testability

- **Unit (pure, no files):** `parse_items`, `render_items`, `migrate_body` and its two fallbacks, and the loss invariant over the corpus of 4.4
  (including the heading-only cases); the round trip `parse_items(render_items(x)) == x` over the corpus and over seeded random item lists
  (`random.Random(seed)`, no new dependency: sections with and without items, multi-line steps with blank lines and 3-space-looking content,
  rules, `why` entries); placement (add, restore after a retired or moved neighbour, a restore into an emptied section and into the `""` section);
  `content_words`; `text_tokens` (the rows of 6.1, the four start-of-text rows, the continuation-line row and B9's `~`, `#` and `~~` rows included); `item_words` (with and without the id, against `criterion_words` unchanged); `split_check`
  (base 0 included); weakening and coverage (the removed-criterion rows of 9.1); `Admission.why` for (b) cited by case, verdict and criterion ids,
  and for (c) with an empty `Criterion.answers`, and the (c) refusal of a criterion confirmed only by a link on a relayed rejection (6.2's
  `added_h`); `watch_states` over constructed versions and cases (every row of 8.7, the across-edits rule, late and corrected links, rows i-xxv
  of 8.1, among them the four superseded-delivery rows, the W1/W2 rows, the carried watches, review 3's three rows xiii-xv, the property's
  edges xvi-xix and the amendments' rows xx-xxv (B1 to B4), the two r rows of 8.4 (a link note and, B3, an answering version), k for r = 0.5,
  0.3, 0.2, 0.1, unknown); PB-WATCHED-OUT on a gated edit of another live item into a watch-retired text (B2), and on a rule re-added as a step
  with its `then`'s words; the settler's retire when the text before the watch has the watched
  text's tokens (the item is removed, no `restores`, 8.5); the cap's candidates excluding a carried watch and a W2-restored text (10); the accept
  refusal's trigger (13.2: `Org.feedback(ROOT, t, "accept")` without `source` on a case with an unanswered rejection is recorded, as relayed; with
  `source="human"` it is FEEDBACK-UNANSWERED; a `revises` to another assignee starts its own case); the restore guard (9.1: an exempt restore of a client-written text that drops a covered id is PB-ACK; a restore of a retired item is
  never weakening); placement refusing a step after a rule; PB-TEXT's exemption for a criterion's own words (a Given/WHEN/THEN criterion, one over
  1200 characters, one with `[P3]`) and its `THEN`-in-`when` rule; the acknowledgement hash (a rule with `when` absent, `""` and `always` hashes
  alike); `unanswered` (a rejection answered by a version whose link write failed is answered); `aar_parts`; the Reflect word cap and the
  fixed-text bound over every variant at its longest (section 12).
- **Corpus (pure, over kept files):** `migrate_body` on the 42 kept `PLAYBOOK*.md` files (every one under `studies/`, B5) and every generated v1 passes the loss check with the
  per-block split and **no fallback** (4.4); the constructed bodies pass, each with the form its test names.
- **Contract suites:** `ServiceEvidence` (`admit_item`, `watch`) run against the real implementation and the fake in `services/testing.py`, so
  consumers' fakes stay trustworthy (refactor principles, L).
- **Integration (fs world, in-process MCP and CLI):** every op and refusal through MCP, including an old-form call (`content`, no `op`) reaching
  PB-FORM through FastMCP's schema; `acknowledge_playbook` through MCP and CLI; the settler inside `feedback(confirms=)` and
  `define_service(answers=)`, with `watch_step`'s sentences in the MCP and CLI replies (and before `LINK_FAILED`); REQUEST-UNANSWERED and
  REQUEST-UNREADABLE through MCP, CLI and the facade; FEEDBACK-UNANSWERED through MCP, CLI and the facade, with its exception (the accept of the
  case's unrated rework passes, then `define_service(answers=)` passes P2-UNRATED); the item file's frontmatter after each op; the migration of a
  real legacy file; the repair migration of a hand-broken item file, with a warned rule's watch carried, and the settler repairing before a due
  retire; **two writers** (`FsServiceStore` on a real directory: two processes, `multiprocessing` from the standard library, each reading v5 and
  writing v6, the owner's op and the settler's retire; exactly one writes v6, the other gets `PlaybookRace`; `history/PLAYBOOK.v5.md` holds v5's
  bytes; no version is lost; and the leftover-archive case of 4.3 step 3 is accepted); the lock file is ignored by `git add -A` in an org made by
  `Org.init`.
- **e2e (deterministic, fake agents):** (1) E4 s2r's vague-deadline rule as an add citing C9: refused PB-C-WORDS; (2) E5-E7's legitimate (c) line as a
  (c) item: admitted; (3) the planted-wrong-rule chain of 18.4 end to end: warning on the first related answer, the runtime retire on the second
  (written in the answering call, with the watch sentence in root's reply and the notes to owner and parent), PB-WATCHED-OUT on re-adding it and
  on editing another live item into its text (B2); a second related rejection of a later delivery recorded after the k-th verdict retires it (B1); the
  same chain on an edited rule, whose previous text the retire restores; and a failed retire write (`retire due`, then the retry at the owner's
  next op); (4) a correct rule reaching `kept` after 3 clean cases, and back to `warning` on a corrected link; (5) an agent
  client's service: every gated op refused, nothing watched; (6) a legacy org (E7 s1's files) taking its first op: the migration, then the op;
  (7) REQUEST-UNANSWERED on E7's flow when the next memo is requested before the answer, and FEEDBACK-UNANSWERED on an L-ASIS accept recorded
  before its answer; (8) the 0b replays and published counts unchanged; (9) G0 m1-s1's flow (memo 1's first delivery superseded by the
  injection and a human rework) with a constructed item A live from its rework: A's case counts through the delivery Lena judged.
- **Property test, the recording order** (`reflection/tests/test_watch_order.py`, pure, standard library only: `random.Random(seed)` and
  `itertools.permutations`, no new dependency). For each of a fixed set of seeds, a generated watch: k = 3, three to five cases with first and
  superseded deliveries (done and blocked), the item live from before the first, and a set of records to append: the human verdicts of the first
  k candidates, root's relayed verdicts on them, the human rejections of other cases (delivered before and after `E`) and second verdicts on
  judged deliveries, and the answers to the rejections (links, some related, some "none", some "same as R<j>", and answering versions), at most 7
  records a seed. For every order of those records that keeps each answer after its rejection and each verdict after its delivery (at most 5040
  orders a seed), the
  records are stamped in that order and `watch_states` is derived after each one. Asserted: (1) the state sequence moves only along 8.1's
  paths (`new -> kept`, `new -> warning -> retire due`, `warning` held), never `warning -> new | kept` and never `kept -> new | warning`; (2) the
  final state equals `watch_states` on the final files, derived from scratch; (3) with one corrected link inserted, the only move outside (1) is at
  that record; (4) (B1) the generated records include, for some seeds, a second related rejection on a delivery made after `E` and recorded after
  `D` of an item that a first related rejection warned: in every order the item ends `retire due` (retired by the settler), never `warning` with
  two related rejections. The constructed rows of 8.1 xiii-xxv and 18.4.1's O1-O10 are fixed cases of the same test.
- **One derivation path** (integration, fs world): for a service with a watched item, `ServiceEvidence.watch`, the `quality` record's `watch`,
  the owner's playbook section's states line and root's `services` suffix name the same states (every reader calls `CaseServiceEvidence.watch`;
  the test pins the wiring of 20.1).
- **Goldens:** 21.4.

### 20.1 Files and integration points (for the planner)

| Package | File | Change |
|---|---|---|
| kernel | `kernel` `Message` and its frontmatter codec | one optional field and header `acknowledges` (read and written like `criterion`, shown in the message header) |
| dispatch | `api.py` (`MessageSender.send`), `_sender.py` (`RuleMessageSender`, `provenance_source`), `testing.py` | `send(..., acknowledges: str \| None = None)`, accepted only on a plain note (9.2); the fake follows |
| services | `api.py` | `PlaybookItem`, `ItemWatch` (with `coverage`, `waiting`, `carried`), `PlaybookChange`, `PlaybookRace`, `content_words`, `text_tokens`, `item_words`; `Playbook`'s new fields (4.2); `Admission.why`; `Rejection.case`; `ServiceCommands.revise_playbook` (new signature, returns `PlaybookChange`) and `acknowledge_playbook` (returns `Message`; 6 methods, R7's limit is 8); `ServiceEvidence.admit_item` (replaces `admit`, whose only caller is the reviser) and `watch` (5 methods). `feedback` and `define_service` keep their signatures and return types |
| services | `_items.py` (new) | `parse_items`, `render_items`, `migrate_body` (with its fallbacks), placement, the loss check |
| services | `_ops.py` (new; replaces `_playbook.py`) | `RuleItemReviser(agents, catalog, texts, playbooks, delivery, evidence, settler: WatchSettlement, mail: MailboxReader)` (the acknowledgement note is read from the owner's received mail), `split_check`, weakening, the round-trip assertion, the PB-* texts (PB-RACE among them) |
| services | `_watch.py` (new), `_acknowledge.py` (new) | `RuleWatchSettler(catalog, evidence, playbooks, delivery)`, `SettleReport`, the Protocol `WatchSettlement` (`_protocols.py`); `RuleAcknowledger(agents, catalog, owners, evidence, sender)` and the ACK texts |
| services | `_feedback.py` | `RuleClientFeedback(agents, mail, sender, evidence, store, settler: WatchSettlement)`: the settler after the human link; FEEDBACK-UNANSWERED, FEEDBACK-UNREADABLE (13.2) |
| services | `_define.py` | `RuleContractDefiner(..., settler: WatchSettlement)`: the settler after the answering version (before `LINK_FAILED`); `_record` and `_check_answer` use `unanswered` |
| services | `_request.py` | REQUEST-UNANSWERED, REQUEST-UNREADABLE; `RuleServiceRequester(agents, catalog, mail, bodies, sender, judged, allowance, evidence: ServiceEvidence, store: ServiceStore)` |
| services | `_criteria.py`, `_retire.py` | `unanswered(basis, store, owner, name)` (13); `RuleServiceRetirement._check_record` uses it (no text change) |
| services | `_hints.py`, `_amend.py`, `_define.py` (`_quoting`) | the `report` hint's two texts, the contract-change note's rule (c) clause and removed-criterion line, and the item ids `_quoting` passes for an item-format playbook (14.9) |
| services | `_store.py`, `testing.py` | `FsServiceStore.write_playbook`: the lock, the compare-and-swap and the exclusive archive (4.3); `MemoryServiceStore.write_playbook`: the same version check; both raise `PlaybookRace` |
| services | `_parse.py` (`playbook_of`, where `read_playbook` parses), `_protocols.py`, `_texts.py`, `testing.py` | parsing on read and the new `Playbook` fields; the Protocols (`PlaybookRevisions`, `PlaybookAcknowledgements`, `WatchSettlement`); v1 in item form; `service.revise` with `actor` `runtime` for runtime writes; fakes |
| reflection | `_watch.py` (new) | `watch_states(versions, cases, results, criteria, contract_versions)`: candidates, `judged(c)`, `E`, `D`, the window, `K`, W1-W3, carried watches, k and r |
| reflection | `_evidence.py` | `CaseServiceEvidence(history, catalog, versions: ContractVersions, mail: MailboxReader)` (`ContractVersions` is reflection's existing port, `_ports.py`, implemented by the services store: the playbook and contract versions; `mail` gives `watch` every result of every task, one `mail.received(client)` read per call); `admit_item` (with `why` and `added_h`), `watch`, `amendment_basis` filling `Rejection.case`; PB-C-WORDS; G1 and G2 wording |
| reflection | `api.py`, `_steps.py` | `ServiceSteps.watch_step(rejection)` (8.5; 3 methods); `TextServiceSteps(agents, catalog, history, mail, evidence: ServiceEvidence)` |
| reflection | `_sections.py`, `_digest.py` | 14.1, 14.2, 11, 12; `QuotedPlaybookSection(catalog, paths, evidence: ServiceEvidence)` and `EvidenceReflectSection(catalog, config, paths, history, evidence: ServiceEvidence)`; `OwnedServicesListing` unchanged (no states, 14.1) |
| reflection | `api.py`, `_marks.py`, `_records.py`, `_reports.py` | `PlaybookMark` fields, `ServiceRecord.watch`, the listing (14.3, 14.4); `DerivedCaseRecords(history, catalog, agents, mail, versions, bars, deliverables, evidence: ServiceEvidence)` and `TextServiceReports(agents, catalog, history, paths, evidence: ServiceEvidence)`, each reading `evidence.watch` (one derivation path, 8.1) |
| progress | `_quality_render.py` | the watch line and JSON key; the marks' `op`, `item`, `item_kind` keys (14.4) |
| mcp_server | `_tools_services.py`, `_tools_tasks.py` | the tools and docstrings of 14.5; `watch_step` appended to the `feedback(confirms=)` and `define_service(answers=)` replies; `revise_playbook`'s reply from `PlaybookChange` |
| cli | `_commands_services.py`, the command registry | `acknowledge-playbook` (and its `--help`); `watch_step` lines after `feedback --confirms`, the automatic link, and `define-service --answers` |
| dispatch | `_lessons.py` | the AAR form in `check_lessons`' refusal texts (11; the reply's AAR sentence is the `report` hint's, 14.9) |
| blueprint | `_playbooks.py`, `_details.py` | 14.8 |
| app | `wire_services.py`, `wire_reflection.py`, `_facade_services.py` | new classes wired and every constructor change above. `wire_reflection.py`: `CaseServiceEvidence(b.get(CaseHistory), b.get(ServiceCatalog), b.get(ServiceStore), b.get(MailboxReader))`; `TextServiceSteps(..., b.get(MailboxReader), b.get(ServiceEvidence))`; `TextServiceReports(..., OrgServicePaths(...), b.get(ServiceEvidence))`; `DerivedCaseRecords(..., b.get(DeliverableChecks), b.get(ServiceEvidence))`; in `_sections`, `QuotedPlaybookSection(catalog, paths, b.get(ServiceEvidence))` and `EvidenceReflectSection(catalog, b.get(OrgSettings), paths, history, b.get(ServiceEvidence))`. `wire_services.py`: `RuleWatchSettler(catalog, b.get(ServiceEvidence), playbooks, delivery)` passed to `RuleItemReviser(agents, catalog, texts, playbooks, delivery, b.get(ServiceEvidence), settler, mail)`, `RuleClientFeedback(agents, mail, sender, b.get(ServiceEvidence), store, settler)` and `RuleContractDefiner(..., settler)`; `RuleServiceRequester(..., b.get(CaseAllowance), b.get(ServiceEvidence), store)`; `RuleAcknowledger(agents, catalog, owners, b.get(ServiceEvidence), sender)`. No provider cycle: `ServiceEvidence` is built from `CaseHistory`, `ServiceCatalog`, `ServiceStore` and `MailboxReader`, none of which needs `CaseRecords`, `ServiceReports`, `ServiceSteps` or `ServicePromptSections`. No R-rule moves: `reflection` (L8) already imports `services` (L7) (R4), every new parameter is a Protocol (R6), `ServiceEvidence` has 5 methods (R7). `Org.revise_playbook` and `Org.acknowledge_playbook` |
| skill | `skills/hirearchy/SKILL.md` | line 109 (14.6) |
| tests | `tests/architecture/test_policy_free_primitives.py` | `acknowledges` among the parameters `send` must not have (`GUARDED`) |
| tests | `tests/architecture/org_signatures.json`, `facade_cases.py` | `Org.revise_playbook`'s new signature and return type, `Org.acknowledge_playbook`, `MessageSender.send`'s new parameter |
| tests | `tests/architecture/constructor_dependencies.py`, `test_constructor_dependencies.py` | no edit: `constructor_dependencies.py` is R6's engine and holds no list of classes; `test_constructor_dependencies.py` runs it over `hirearchy` and so checks every constructor of this table (each new parameter is a Protocol: `ServiceEvidence`, `MailboxReader`, `ContractVersions`, `WatchSettlement`, `ServiceStore`) |
| tests | `tests/testkit/quality_schema.py` | `PLAYBOOK_MARK`'s `op`, `item`, `item_kind` and new `basis` values; the record's `watch` |

## 21. What the Phase 1 study must check; deviations; declared limits; golden impact; user-visible changes; open questions (brief item 14)

### 21.1 What the Phase 1 study must check (pre-registration input)

Pass rules (per stream; a rule passes over the streams when it passes in every valid stream of its arm, at least 3):
1. **G1 (arm I):** (a) no item with a related human rejection in its window (section 3: bounded by `E` and `D`, closed at `K`) is `kept` at any
   turn's end, and no item's per-turn state sequence leaves 8.1's paths (`warning` never back to `new` or `kept`, `kept` never back, but at a
   corrected link, which is reported); (b) every item with two related rejections is
   retired by `runtime (watch)` in the call that recorded the second answer (or the next change, after a `retire due` reply), with its previous
   text restored when it had one; vacuous in a stream where the planted rule B was retired by its owner before memo 5's answer, where the owner
   added no B, where B was added after memo 4's first delivery (O7), or where root's answers to memos 4 and 5 name neither C10/C11 nor a
   replacement of them (18.4, 18.4.1; the count of streams where the retire ran live is reported; the e2e of 20 (3) shows it in every build); (c) every gated op admitted cites a human-tier
   assertion or a confirmed criterion (no team-only or relayed evidence); (d) the injected relayed lesson and the poisoned line are in no item;
   (e) the planted wrong rule, if admitted, is not `kept` at the end; (f) the re-derivation (18.6) equals the product's states and `watch` keys
   (14.4) after every turn, and its `judged(c)`, `E`, `D`, `K` and warned window (B1) give each item the state 18.4.1 pre-registered for the
   order root took (O1-O10).
2. **G2 (both arms):** (a) every Lena rejection line is recorded as a human-tier rejection with an `R<k>`; (b) each has a recorded answer before the
   service's next new request and before the human accept of its case (but for the accept of the case's unrated rework, 13.2), and, for the
   stream's last request (memo 6, and any rejection after it), at the stream's end: `amendment_basis` lists no human rejection without an answer
   (a derived check: no refusal holds the rest of the last request, L10); (c) no new request of the service was sent, and no human accept of a
   case was recorded outside 13.2's exception, while one was unanswered (by construction; the study counts REQUEST-UNANSWERED and
   FEEDBACK-UNANSWERED refusals, the exception's uses, root's accepts recorded as relayed on a case with an unanswered rejection (not held,
   `source == "human"` only), and one-off delegates to the owner in that window).
3. **No regression** as E7's rule, per memo, with G0's gate-able outcome measures (every delivered version: 0 wrong dates, 0 extra rows).

Reported, not pass rules: owner `revise_playbook` attempts by op and refusal; items added per kind and rule; states per turn; k and r; first-delivery
accepts per memo index; escapes and causes; Reflect words; prompt growth; acknowledgements requested, given and applied; PB-CAP, PB-SPLIT and
PB-RACE refusals; REQUEST-UNANSWERED and FEEDBACK-UNANSWERED refusals; the id each scripted rejection's item named (18.4); per item, the turn
each candidate got its judged delivery and how many of its deliveries were superseded before it (18.4.1); the order root took at each of
18.4.1's moments O1-O10 (for O10, whether memo 4's change re-added C6's exact text); the warned items still `warning` at the stream's end, each
with its reason (no second related rejection, or an owner action: a retire, a gated change that restarted its watch) (B1); user-initiated versions whose words share no word with the change (backlog 5); D-SPEND spend requests and Lena's
approvals against the product's (backlog 6); failed empty-argument calls per stream (18.3); H-LOCK.

### 21.2 Deviations (from 08 4.2 and the brief), with reasons

- **D1. A wording fix is exempt only when its text tokens are unchanged** (08 4.2: "fixing their wording"): only spacing, case, markdown markers
  and sentence punctuation may change; every word, letter, number and other symbol (`<`, `=`, `%`, a currency or a sign), a leading one
  included, is a token (section 3, 6.1); only a migrated item's continuation lines drop their own list markers (L13). The runtime cannot tell a
  reworded step from a changed check; the strict reading is what keeps a wrong rule from coming back as a step (11 M3).
- **D2. A fifth state, `kept`,** for a live item outside its watch (the brief lists `new`, `warning`, `retired`, `restored`). A rule that passed its
  watch, and every v1 or migrated item, must have a state; `restored` is kept for the text the watch brought back.
- **D3. No root CLI override of the playbook** (08 4.2's "human edits come from ... a root CLI override", 09 13). Any root write path is reachable by
  the assistant's shell and would be a relayed channel around the gate, against check 2. The human's lasting wishes go into the contract, which
  rule (c) turns into items; the first version still comes from `define_service(playbook=...)`. Reopen if a user needs a playbook edit that is not a
  contract matter.
- **D4. A warning survives every change** (08 4.2: "an edit restarts the watch"). An edit, a gated restore and an exempt restore of a
  client-written text (8.1 W2) restart the count of clean cases; related rejections accumulate over the watch, and carry over to a restore of
  the same id, a re-add of the same text or a gated edit of another item into it (B2) after an owner's retire in `warning`, and across a repair
  migration (section 3, carried watch), so an owner cannot clear a warning by editing, restoring, retiring and re-adding, editing another item
  into the text, or a hand edit (check 2); the second related rejection is read over the warned window and retires in every order (B1). This includes a (c) edit of a warned
  item into the own words of a criterion the client confirmed after the warning: the client's words then inherit the warning, one more related
  rejection retires them, and PB-WATCHED-OUT bars them until the client confirms another criterion. Raising the bar wins over convenience; the
  owner can add the words again after that confirmation.
- **D5. Related rejections count on blocked results too, and on the cited cases; clean cases do not** (asymmetric on purpose: toward warning, never
  toward keeping).
- **D6. The owner's `first` version is allowed only before any verdict or rework exists** (0a: "after its first request"). It keeps the first version
  free of anything the evidence could have suggested.
- **D7. Rule (a) admits nothing** until a check-result record exists (Phase 3).
- **D8. Clause 2 gets two refusals** (the exit criterion's guarantee needs them, section 13): on root's next new request of the service
  (REQUEST-UNANSWERED), and on root's human accept of a case while an earlier human rejection of that case is unanswered (FEEDBACK-UNANSWERED).
  The second has one exception: the accept of a task in `basis.unrated`, because P2-UNRATED makes the answer wait for exactly that verdict
  (13.2); without it a rework delivered before the answer would deadlock the case.
- **D9. The cap's candidates as 08 defines them are empty in Phase 1** (a candidate is a `new` item whose watch rests on no `R<k>`, and every
  watch starts at a gated change whose `WHY` holds an `R<k>` by construction, 6.2's `added_h` and 6.3); the refusal adds the uncovered items as
  a second list (section 10).
- **D10. A rejection's subjects include the lineage of its criteria, as of the rejection's answer** (section 3, B4): without it, a rejection about the new wording of a replaced
  criterion could never be the second related rejection of the rule that cited the old wording (the client-changes-her-mind case, 18.4).
- **D11. The study has no line-level-revision arm** (08 section 9 names today's whole-text revision as a second control). Phase 1 removes that
  form (5.4), so an arm would need a third product build that ships nowhere, and E7 and G0 already measured it under the same script head (memos
  1-3) with the same model, harness and kiro-home treatment; they are its descriptive reference (18.2). A third arm would also add 3 streams,
  about 360-555 credits (18.7's per-stream figure), for a contrast the exit criterion does not ask for.
- **D12. No item text in root's quiet note** (5.2): today's client note carries the admitted lines' text to root; from Phase 1 a human client's
  note names ids, the op, the admission and the reason only. Every change is now one item and one note, an item is an instruction written for the
  team, and root's context is the assistant's (0b keeps agent text out of root's views for the same reason); the text is one `read` away.
- **D13. Rule (c) needs a rejection of the client's own** (6.2's `added_h`): a criterion confirmed only by a human link on a relayed rejection
  admits no item. 0a.2 never checked the rejected note's tier on a link; this narrows (c) to what its text says ("an amendment the client
  confirmed" on her own rejection) and refuses no flow of E7 or G0.
- **D14. The raise-the-bar guard covers what still binds** (the brief: "an item that references a criterion or regression assertion"). 9.1 reads
  "references" as **coverage**: a current criterion, or a confirmed assertion that is not only about removed criteria. An item whose references
  are only removed criteria, assertions marked "no lasting rule", or confirmed assertions about removed criteria only, needs no acknowledgement to
  be retired or weakened: the client already lowered that bar herself (her answer removed the criterion, or said "no lasting rule"), and asking
  the parent to confirm it again would put a question to the user that her own answer settled. The study's planted rule B is the case (9.1, O9).

### 21.3 Declared limits

- **L1.** Rule (a) has no data path (6.2).
- **L2.** An owner-written v1 is the team's words and unwatched (D6 narrows when it can be written).
- **L3.** Relatedness rests on the id the user's answered question named (15 item 2).
- **L4.** The watch reads verdicts from mail and does not void a verdict recorded after a hand edit (8.2).
- **L5.** A weakening edit that keeps every covered id and adds words is not caught by the guard; it is gated and watched (9.1).
- **L6.** A hand-written item file that parses, with a forged `WHY`, is read like the runtime's (16); one that does not parse is turned into new
  items at the next owner op or due retire (4.4), which keeps every word but drops its rule kinds and `WHY` entries. Watches are carried into
  the repaired items by text key, except in two shapes: an item whose line the hand edit changed, and an item whose watched text the hand-edited
  version itself had written (that version's runtime body is gone, so no parseable version holds it). Those read `retired` under their old id
  and come back as `kept` items; a hand edit of `services/**` is outside the product's tools (`orgfiles` refuses it), so only the assistant's
  own shell can make one (0a.2 5.8).
- **L7.** A one-off `delegate` to the owner, or a new service, goes around REQUEST-UNANSWERED, visibly (16).
- **L8.** The watch's minimum of 10 judged cases for a known rate, the 50-word floor of the 30% rule, the 600-word Reflect cap and its 400-word
  bound on the fixed text are this design's labelled defaults, not settings.
- **L9.** A written watch retire stays when a later corrected link removes the relation; the owner may bring the text back as an ordinary gated
  restore once fewer than 2 of its related rejections still hold (8.6).
- **L10.** The last request of a service has no next new request. FEEDBACK-UNANSWERED narrows the gap (its case cannot be closed with an
  accept of an already judged delivery, of a blocked result or of an earlier delivery while a rejection of it waits), but two shapes remain: the
  accept of the case's latest, unrated rework (13.2's exception) and a case that ends with no accept. There nothing refuses while the rejection
  waits for its answer (only `retire_service` does, today), and clause 2 holds only as the study's derived end-of-stream check (21.1 G2(b)). The
  owner may close the first shape by narrowing P2-UNRATED (21.6, question 2).
- **L11.** A failed watch-retire write's error text is not in the `feedback` or `define_service` reply (the reply is derived from the files and
  says `retire due`); it surfaces at the retry, the owner's next op, if the failure persists (8.5). On a locked contract the owner's ops are
  refused before the settler runs, so there the retry comes at the next recorded answer only.
- **L12.** A candidate case none of whose deliveries after the live-from ever gets a verdict (or whose rejection is never answered) keeps its
  item `new` (8.1, 8.7): the watch errs toward not keeping. A delivery superseded before any verdict holds nothing (the case counts through the
  delivery the client judged), so this is a case the client never judged at all, not the usual rework flow.
- **L13.** A migrated item's continuation lines (its second and later lines, 4.4) drop their own leading list and heading markers before the
  token comparison, so a change of such a marker there (`   - sub` -> `   1. sub`, or `   [x] done` -> `   [ ] done`) is a formatting fix. An
  item's first line, and every line an owner writes (`text`, `when` and `then` are one line), keep every symbol (6.1).
- **L14.** `edit` takes one line, so a multi-line migrated item (a table, a fence, a long paragraph) can be changed only by editing it into one
  line of at most 150 words, or by retiring it and adding a new item; its old text stays in `history/`. Multi-line `edit` is in the backlog
  (B-P1-1, section 17), not built in Phase 1.
- **L15.** Deleted by the manager's amendment B1 (section 24): a warned item's second related rejection is read over the warned window
  (section 3), so it is retired in every recording order, and no warned item stays `warning` because its window closed. The number is kept so
  that L1-L14 keep their references.

### 21.4 Golden impact (predicted; each regenerated file named with its line count in its commit; D1 of 08 section 10)

| Area | Files (about) | Why |
|---|---|---|
| MCP surfaces `tests/golden/expected/mcp/*` | 10 | `report`'s lessons text (every identity); `revise_playbook` (manager); `acknowledge_playbook` (root, manager); `request`'s sentence, `feedback`'s two (the accept's wait, the watch clause), `define_service`'s watch clause (root) |
| plans `tests/golden/expected/plans/*_service*.txt` | 10 | the generated v1 (AAR step, no Pitfalls placeholder, the label) |
| `charters/apply_service_example.md`, `blueprint/tests/golden/second_half.json` | 2 | the generated v1 |
| prompts `tests/golden/expected/prompts/service_owner_*.txt` | 2-3 | the playbook section and Reflect |
| `reflection/tests/expected/sections_*.txt` | 6 | the same |
| `services/services_text_root.txt`, `service_and_playbook_files.md` | 2 | the listing's playbook line; v1 in item form |
| `cli/services.txt` (and `fresh_services.txt` if its fixture has a playbook; today it has none) | 1-2 | the listing's playbook line |
| `cli/help.txt` and a new `cli/help_acknowledge-playbook.txt` (the help pages of `feedback` and `define-service` keep their text) | 2 | the new command in `hirearchy --help` and its own help page |
| `quality/e3.json` (the `watch` key, and the `op`, `item`, `item_kind` keys of its one playbook mark), `cli/tests/expected/quality.txt` | 2 | the `watch` list; the marks' new keys (14.4). No other quality golden holds a playbook mark (`a5_one_off_block.txt`, `e3.txt`, `empty_org.txt` and `empty_service.txt` are text views whose legacy mark lines are unchanged) |
| `tests/architecture/org_signatures.json`, `facade_cases.py` | 2 | `Org.revise_playbook`'s signature and return type, `Org.acknowledge_playbook`, `MessageSender.send(acknowledges=)` |
| `events/line_shapes.txt` | 0 | unchanged: `msg.deliver` gains no key (9.2) and `service.revise` keeps its fields (`actor` stays a string) |
| **Total** | **about 46 (44 changed, 2 new) by the plan's section 5; 49 as built (47 changed, 2 new), see 25.3** | none of the E-G0 replay expectations moves (legacy marks unchanged, 14.4) |

Test sites that change (not goldens): every test that calls `revise_playbook(content=...)`, among them `tests/e2e/test_org_growth_0a.py`,
`test_org_growth_0a2.py`, `test_no_bypass_0a2.py` and the services and reflection unit tests of P1's line stage. Each keeps its outcome under the
item form (the E4 s2r replay stays refused, the E5 (c) line stays admitted); none is weakened. E2e scenarios that send a new request while a human
rejection is unanswered now meet REQUEST-UNANSWERED, and those that record a human accept of a case before its rejection's answer (other than of
the unrated rework) meet FEEDBACK-UNANSWERED: each is read, and one that tests something else answers first (named in its commit). The contract
suite of `ServiceEvidence` moves from `admit` to `admit_item`; `tests/testkit/quality_schema.py` follows the new keys (a test helper, not a
golden). The 0b replay kit compares named keys of marks, so none of its expectations moves (14.4). SKILL.md: line 109 only (14.6).
The owner-facing texts of 14.9 are pinned by tests, not goldens (none of `tests/golden` or the packages' `tests/expected` holds them):
`services/tests/test_contract_service_hints.py` (3 assertions), `mcp_server/tests/test_service_tools.py` (2), `services/tests/test_amender.py`
(the rule (c) clause twice, and the `TAIL` constant behind 3 assertions) and `services/tests/test_amend.py` (1): 4 test files, 9 assertions,
each updated to the new wording in the commit that changes it. The no-playbook texts of 14.1 move `tests/golden/expected/prompts/
service_owner_no_playbook.txt` and the two `reflection/tests/expected/sections_*` files that show the unlocked text (the locked text is
unchanged), already among the prompt and section goldens counted above. The new constructor parameters (20.1) move the tests that build those classes directly (their fakes gain a
`ServiceEvidence`, from `services/testing.py`); no golden moves for them, and the owner's `# Your services` listing is unchanged (14.1).
**The manager's amendments (section 24) move no golden:** the strings they add or change (the locked `retire due` line, B6; PB-ITEM's lead
sentence and watch-retired marking, B7; the carried clause of a gated edit's reply, B2; the `{what}` and `{sections}` strings, B8) appear in no
golden fixture (none of the prompt or section goldens has a watched item, a refused op or a `first` reply), and are pinned by the unit and
integration tests that name them; B1, B3, B4 and B9 change derivations only.

### 21.5 Every user-visible change, by name

For the user (through root):
- **REQUEST-UNANSWERED**: the next request waits for the one answer (MCP `request`, CLI `hirearchy request`); **REQUEST-UNREADABLE**.
- **FEEDBACK-UNANSWERED**: root's human accept of a case (`source="human"`, the CLI's default; the MCP default `relayed` and a facade call
  without `source` are relayed and never wait) waits while an earlier human rejection of that case has no answer, except the accept of
  the case's unrated rework (MCP `feedback`, CLI `hirearchy feedback <task> accept`); **FEEDBACK-UNREADABLE**.
- **The acknowledgement question** when the team wants to retire, weaken or restore to a weaker text an item that covers a criterion: the new
  tool **`acknowledge_playbook`** (MCP; arguments `owner`, `service`, `item`, `op`, `text_hash`, `words`), the new CLI command **`hirearchy
  acknowledge-playbook <owner> <service> <item> retire|edit [--text-hash H] --words ...`** and its output line, listed in **`hirearchy --help`**
  with its own help page, with its refusals ACK-NOT-YOURS, ACK-NO-SERVICE, ACK-NO-ITEM, ACK-OP, ACK-ARGS, ACK-HASH, ACK-NOT-NEEDED, ACK-WORDS,
  ACK-AGENT-WORDS; and the note it writes, whose new header **`acknowledges: "{service} {op} {item}[ {hash}]"`** shows in `inbox` and `read`
  (the owner's, and root's sent copy).
- **The watch sentences in root's replies** (`ServiceSteps.watch_step`, 8.5): appended to the MCP replies of `feedback(confirms=...)` and
  `define_service(answers=...)` and printed as lines by the CLI's `feedback --confirms`, the CLI's automatic link of a human reject with
  `--criterion`, and `define-service --answers` (warned, retired, `retire due`, "could not be checked").
- **The docstring clauses** of `request` (the wait), `feedback` (the accept's wait, and "An answer may retire a watched playbook rule; the reply
  says so.") and `define_service` (the same clause), and the new docstrings of `revise_playbook` and `acknowledge_playbook` (14.5).
- **The watch notes** to root when the runtime retires a rule (8.3).
- **The `services` playbook line** (MCP `services` and CLI `hirearchy services`, one builder): the items, rules and watch suffix (with `waiting
  for the client's verdict on n case(s)`), `free text`, `not in item form`, `no items` (14.3); the regression list's **`(rules citing it: P12)`**;
  and, when an owner first changes a legacy playbook, **a playbook version one higher with no word changed** (the migration, with the client's
  note saying so, and the fallback's reason when one was used, 4.4), and **`; watch not read ({error})`** when the watch cannot be read (14.3).
- **The `quality` view**: the text line `playbook watch: ...` (MCP `quality` and CLI `hirearchy quality`), the `watch` JSON key (with `waiting`
  and `carried`), the playbook marks' new JSON keys **`op`, `item`, `item_kind`** and `basis` values, the item marks of the timeline, and a
  record's `error` **`the playbook watch: {words}`** when the watch cannot be read (14.4).
- **The plan's Details: the generated v1** (no Pitfalls placeholder, the AAR lessons step, the label; the PLAN FOR YOU block the user approves is
  unchanged).
- **SKILL.md line 109** (14.6).

For root, also: **the client's quiet note on each playbook change** (names the op, the item, the admission, the evidence and the reason, and
**no longer the text**, D12), including the migration's and the repair's notes (4.4). For owners and teams (in prompts and tool replies):
**`revise_playbook`'s ops** (with `acknowledged` on `restore`) and its replies (5.2, among them the "was not needed" clause, the carried-watch
clause of a carried add, restore or gated edit (B2), and `Its watch state is in your prompt's playbook section.`) and refusals
(PB-FORM, PB-OP, PB-ARGS, PB-FIRST-EXISTS, PB-FIRST-LATE (with B8's `{what}`), PB-ITEM (with B7's lead sentence `The watch retired {id} in v{n}
(rejections ...).` and its watch-retired marking), PB-SAME, PB-TEXT, PB-RACE, PB-SPLIT, PB-CAP, PB-ACK with its restore
variant, PB-ACK-BAD, PB-WATCHED-OUT (also on a gated edit into a watch-retired text, B2), PB-C-WORDS, PB-UNREADABLE, and the reworded G1, with its relayed-rejection note, and G2), **the item form of
`PLAYBOOK.md`** and the migration and repair versions, **the playbook section's states line** (with the waiting and carried forms, the locked `retire due` form of B6, and `Item
states could not be read ({error}); ...` when the watch cannot be read) and its empty, legacy, unparseable and **no-playbook** variants (the two
no-playbook texts reworded for `op="first"`, 14.1), **the Reflect section's shortened text and 600-word cap**, with **today's step
5 (the whole-version restore) removed** (14.2), **the AAR form of `lessons`** in `check_lessons`' refusals and **the `report` hint's two
reworded texts** (14.9), **the contract-change note's reworded rule (c) clause and removed-criterion line** (item ids for an item-format
playbook, 14.9), **the warning and retire notes**, and the effect of
**D6: an owner can no longer write a free v1 once a verdict or a rework exists** (it adds items with evidence instead, PB-FIRST-LATE).

### 21.6 Open questions for the owner

The deviations D1-D14 (21.2) and the backlog decisions (17) are decided in this design; the owner may override any of them before the plan.
**The questions stay open with the owner; the plan assumes the recommended answers (B10):** Q1, both refusals approved; Q2, P2-UNRATED kept as it
is; Q4, root's acknowledgement path approved. Q3 (the study's cost) does not affect the build. Each FEAT of the plan whose commits carry a Q1,
Q2 or Q4 behaviour names the question, so that an owner override changes known commits only.

1. **The two refusals of clause 2 (section 13, D8), both user-visible.** REQUEST-UNANSWERED makes root's next new request of a service wait for
   the user's answer to every rejection since the previous one; FEEDBACK-UNANSWERED makes root's human accept of a case wait while an earlier
   rejection of that case has no answer (except the accept of the case's unrated rework, which the answer itself waits for). What the user sees:
   if they ask for the next request, or accept a version, before answering the one question about a rejection, the assistant asks it first and
   records the answer, then the request or the accept. Replayed on E7 and G0: 0 refusals of FEEDBACK-UNANSWERED (13.2). Recommendation: approve
   both.
2. **Narrow P2-UNRATED for an answer's own case?** (13.2, L10). Today `define_service(answers=R)` is refused while any delivered case's latest task
   has no verdict, including the rework of R's own case that the user is about to judge. That is why FEEDBACK-UNANSWERED needs its exception, and
   the exception is the one way a last request can still close with its rejection unanswered. The option: P2-UNRATED would not count the
   unrated latest task of the answered rejection's own case when it was sent after the rejection; FEEDBACK-UNANSWERED would then lose its
   exception (the order becomes: answer, then accept). What changes for the user: in that one flow the answer is recorded before the accept,
   instead of after. It changes a 0a.2 refusal (P2-UNRATED, whose text and order 0a.3 fixed), so this design does not do it without the owner's
   word. Recommendation: keep today's P2-UNRATED in Phase 1 and measure the exception's uses in the study (21.1 G2(c)); narrow it later if the
   study shows that shape.
3. **The study's run and cost (18.7), separate from the build.** About 740-1130 credits (central about 920) and 430-620 org runs for 6 streams of
   6 memos, preflight probe included (about 20 credits and 2 org runs; G0's 63-72 credits per stream is the base). Recommended staging: stage 1,
   the probe and the first pair, about 260-390 credits; stage 2, the other two pairs, about 480-740 credits, only when stage 1's two streams are
   valid and within 185 credits each (the stop rule). Or the 5-memo variant at about 8-10% less. Recommendation: approve the 6-memo design in two
   stages. The optional 5-arm deciding probe of F-G0-7 (about 45-50 credits) is not needed (18.3) and is not asked for.
4. **The acknowledgement path for root** (section 9): root asks the user one yes/no and records their words before acknowledging. What the user
   sees: one question each time the team wants to lower the bar of a covered item (a retire, a weakening edit or restore, at the cap included).
   Recommendation: approve (the guard is the brief's; the user question is how root's acknowledgement stays the user's).

## 22. The six mandatory review checks, audited (re-run for revision 4, against review 3's failures; revision 3's audit of review 2's kept)

1. **Zero and empty cases.** Tables 8.7 (watch, including every item retired, a case never judged, a superseded first delivery, a late verdict on
   a superseded delivery, an unrejected blocked result, a move or formatting edit during a watch, an exempt restore during a watch, two writers,
   and a call that takes a related count from 0 to 2), 10 (no cap candidate), 13 (no answer due; the last request, L10), 19.1 (unparseable,
   unreadable, a race), 4.4 (empty, heading-only and legacy bodies); 5.1's table (`add` on version 0, `first` on an existing playbook:
   PB-FIRST-EXISTS, retiring the last item, `restore` without an earlier text, a no-op `move`); section 7's base 0; `ratio`-style `k of n` with
   `n/a (0 of 0)` in every view count (0b's `ratio`). **Review 2's failures:** (a) the superseded first delivery, G0's and E7's usual case, no
   longer holds an item `new`: a candidate counts through `judged(c)`, the delivery that carries its first counted verdict, and only a case
   never judged at all holds it (section 3, 8.1 rows v-viii, L12; R2-F1); (b) the 0-to-2 case is stated, with its notes (8.3, 8.7; R2-F13).
   **Review 3's additions:** the window's zero cases, a window still open (`E` undefined: every rejection since the watch start), a closed
   window (`D` defined) with a pending rejection, a rejection recorded after `K`, a warned item whose window has closed (then L15; under B1 its second related rejection retires it), a "same as" link
   to an unanswered rejection, and a watch retire with nothing to restore (8.1 rows xiii-xix, 8.7, 8.5; R3-F1, R3-F8). **The amendments
   (section 24):** the closed-window row of 8.7 now reads "retired at the second related rejection, whatever the order" (B1, row xx); an answering
   version whose `defined` is after the watch start changes neither `r` nor k (B3, row xxii); a criterion with no adding version at
   or before t has no lineage as of t (B4). **PASS.**
2. **No team-written or relayed text activates or keeps a rule.** Activation: gated changes need human-tier evidence (6), and rule (c) needs a
   rejection of the client's own (`added_h`, 6.2; R2-F12); an exempt edit cannot change a word, a number or a symbol (6.1's tokens: `>` -> `<`,
   `5%` -> `5`, `UTC+2` -> `UTC-2` are gated; R2-F2); the owner's v1 only before any evidence (D6); lessons are never read (11); `WHY` is the
   runtime's, canonical in the frontmatter (4.1, 6.3). Keeping: `kept` derives only from human-tier verdicts on the deliveries the client judged
   (8.1, 8.2), and no item reaches it while one of its first k candidates has none; a relayed rework moves `judged(c)` to the delivery the user
   then judges, so it cannot move the user's judgement out of the window (`E = max J(c)`, R2-F1); relayed and agent verdicts are no verdict
   there; a move or a formatting edit keeps the watch and the settler retires the current text (W1, R2-F4); an exempt restore restarts the watch
   with the warning kept (W2); no edit, restore, retire-and-re-add or hand edit clears a warning (D4, carried watches; R2-F15, F16, F17, with the
   two hand-edit shapes declared in L6); a restore to a weaker text needs the parent (9.1, R2-F3); an agent's `send` cannot be an acknowledgement
   (16). **Review 3's two failures, re-checked:** (a) *the order of root's calls* (R3-F1). The window is bounded by `E` on delivery time and by
   `D` on recording time, both fixed once defined, and closed at `K`; 8.1 states and proves that the derived state then moves only along `new ->
   kept`, `new -> warning -> retired` or stays `warning`, whatever order root records the user's verdicts, its own relayed verdicts and the
   answers in. So no relayed act (a relayed verdict recorded first, a human verdict recorded late, a link before a verdict) can move a related
   rejection out of the window or turn a warned rule `kept`; the one record that can move a state back is the user's own corrected link
   (a human link, 0a.2 5.9). 18.4.1 pre-registers every order of the script (O1-O10) and the recording-order property test (20) checks every
   order of a generated watch; a warned item's second related rejection is read over the warned window, so it retires the item in every order
   (B1, review 4's R4-F1). (b) *a leading symbol as formatting* (R3-F4): `strip_markers` now runs on continuation lines only, so `>5 rows`
   -> `5 rows`, `+ 2 days` -> `2 days` and `[x]` -> `[ ]` at the start of a text are gated changes (6.1's rows); what remains is a migrated item's
   continuation-line marker (L13), which no owner writes (an owner's text is one line). **Review 4's failure, re-checked (R4-F2, B2):** a gated
   `edit` of another live item into a warned text its owner retired continues that warned watch (carried watch (i), with the edited item's own
   related rejections too), and one into a watch-retired text is PB-WATCHED-OUT, as an `add` or a `restore` of it is; a rule's text key is that
   of its `then`, so a rule re-added as a step is caught (section 3, 8.6, 16; 8.1 row xxi; 20). B9 makes `~5` and `#3` tokens, so neither
   passes as a formatting fix. **PASS.**
3. **Every watch state is derivable from existing files, with no new stored state other than the item file.** `new`, `warning`, `kept`, k, r, all
   counts, `judged(c)`, `J(c)`, `E`, W1-W3 and the carried watches (matched by text key over the stored versions) are derived per call from the
   playbook versions, mail and contract versions (8.1), read through `ContractVersions` and `CaseHistory` (R2-F6's wiring); `retired` and
   `restored` are ops in the item file's own frontmatter, and the new `why`, `rules` and `items_max` keys are the item file's too (4.2). The lock
   file `.tmp-playbook.lock` holds no state (an empty file the lock is taken on; git-ignored, never read). The acknowledgement note is mail and
   holds no watch state; `SettleReport` and `PlaybookRace` are values, never written. Revision 4 adds `D`, the window and `K`, each derived
   from the creation times the files already carry (message ids, the contract version's `defined`, B3, never its `created`, which every version
   carries from v1, and the playbook version's `revised`), and gives
   the derivation its missing input, every result of every task, read from the client's mail (R3-F3). **PASS.**
4. **Domain-agnostic.** The core speaks of items, steps, rules, criteria, assertions, cases and deliveries; section headings are the user's v1; the
   only product headings are `Rules` (and `Steps` for an add to a playbook that has no steps section); the AAR labels name no domain. A
   criterion of any wording or length can become an item: PB-TEXT exempts a criterion's own words, and only a capitalised `THEN` in `when` is
   refused (19.2; R2-F8). Memo words appear only in the study and in one labelled illustration (4.1). **PASS.**
5. **The migration loses nothing.** The per-block split is checked at write time on the non-empty `line_key` values; when it fails, the
   per-section and the single-item fallbacks follow, named in the reason, and the last passes by construction (4.4), so the migration can neither
   lose a word nor refuse; the corpus requires the per-block split with no fallback on all 42 kept files (every `PLAYBOOK*.md` under `studies/`,
   now named in full, B5) and every generated v1 (R2-F11). Every
   heading renders whether or not it holds an item (4.1), the round trip is unit-tested and asserted before every write, so no op can write a body
   the parser rejects (R2-F7), the legacy file is archived byte for byte, a hand-broken item file is repaired word for word at the next op or due
   retire with its watches carried (4.4), an old-form call reaches PB-FORM, and no version can be lost or overwritten by two writers (4.3;
   R2-F5). Existing orgs keep working: nothing is rewritten by a read. Revision 4 declares the one usability limit review 3 found: a multi-line
   migrated item can be changed only into one line, or by a retire and an add, with its old text kept in `history/` (L14; multi-line `edit` in
   the backlog, B-P1-1). **PASS.**
6. **Every guarantee in the exit criterion rests on a refusal or a derived check.** G1: the gate's refusals, the derived states (now over the
   judged delivery of every candidate, R2-F1, and the watched text by tokens, R2-F4), the runtime's compare-and-swap write and PB-WATCHED-OUT. G2:
   the derived `R<k>`, REQUEST-UNANSWERED and FEEDBACK-UNANSWERED over one `unanswered` rule that counts an answering version whose link failed
   (R2-F6, R2-F21), and P2's refusals; for the remainder of the last request of a service (13.2's exception and a case ending with no accept) the
   derived end-of-stream check (L10, declared and narrowed). What still rests on text is listed in section 15 with its reason, the provenance of a
   recorded answer and the owner's applying of an acknowledgement included (items 8 and 9), and measured by the study (21.1). **Review 3's
   failures, re-checked:** (a) G1's derived check was order-dependent and had two fixed points (R3-F1): `E` no longer depends on relatedness,
   `D` and `K` close the window, and the state is a function of the files that moves only as 8.1's proven property allows, so "no wrong rule
   survives its watch" is decided by the files alone; (b) the derivation now has its input (R3-F3): `CaseServiceEvidence(history, catalog,
   versions, mail)` passes every result of every task to `watch_states`, and every reader (the settler, `QuotedPlaybookSection`,
   `EvidenceReflectSection`, `TextServiceReports`, `DerivedCaseRecords`, `TextServiceSteps`) calls that one `watch`, with each constructor in
   20.1; (c) G2's accept refusal has one trigger, `source == "human"` (R3-F2), matching how the product stamps an accept without a source.
   **The amendments:** G1's "two related rejections retire the rule" no longer depends on root's recording order (B1), and the proof's premises
   hold in the edge cases review 4 found: k and r read each contract version's `defined` (B3), and a rejection's subjects are fixed at its answer
   (B4). **PASS.**

## 23. Review resolutions

### 23.1 Design review 1

Each finding of design review 1 (1 HIGH, 17 MEDIUM, 12 LOW) and how revision 2 resolved it (kept as written; revision 3 changes some of
these answers, and 23.2 says which). None changes the goal, the
exit criterion, the binding design principle or the owner's test policy, and none adds a user-visible change beyond what the briefs ask.

| Finding | Resolution |
|---|---|
| F1 (HIGH) heading-only sections lost | Addressed. Every heading renders, only the product's `## Rules` is conditional (4.1); the corpus gains the H1-title, consecutive-heading, trailing-heading and headings-only bodies; `migrate_body` has the per-section and whole-body fallbacks, the last lossless by construction, and the loss check is an assertion, not a user path (4.4, 19.1, 22.5). |
| F2 old-form call fails schema validation | Addressed as proposed: `op: str \| None = None`, PB-FORM first when `content is not None or op is None` (5.1, 19.2); an integration test calls the old form through FastMCP (20). |
| F3 a (b) `WHY` without `R<k>` | Addressed with the proposed formulas (6.3), including (c) with an empty `Criterion.answers`; D9 now holds (10). Clean cases exclude every motivating case (8.2). |
| F4 rule (c) is not `criterion_words` | Addressed: new pure `services.api.item_words`; `criterion_words` and the legacy `own_words` mark unchanged (5.4, 6.2). |
| F5 formatting edits can change numbers | Addressed with a stricter token rule than the one proposed: `text_tokens` keeps each number with its inner separators and matches letters of any script (the proposed `[0-9a-z]+` would have ignored a change of an accented letter and taken `1, 5` and `1.5` as equal). `line_key` stays for the legacy marks, the loss check and PB-WATCHED-OUT (3, 6.1); unit rows added. |
| F6 the watch end and `r` underspecified | Addressed, with one change to the proposal: `E` is the done time of the k-th **candidate** (not of the k-th clean case), so it depends only on delivery times and a late verdict can never move it (with the proposed definition, a late accept of an earlier delivery would pull `E` back and could turn a `warning` into `kept`). `kept` needs all k candidates clean; an unjudged or pending candidate holds the item `new`; related rejections count on results in [start, `E`], open-ended for a warned item; `r` uses only the data before the watch start (3, 8.1, 8.4). Unit rows for each and the re-derivation's self-check cases (18.6). |
| F7 the guard needs the new `WHY` | Addressed: a gated edit's `WHY` replaces the old one (6.3); for `edit` the order is the gate, the 30% rule, the cap, then the guard on `admission.why`; a guard refusal writes nothing and the acknowledged call is judged again (5.1, 9.1). |
| F8 coverage through an assertion about a removed criterion | Addressed with a slightly wider formula than proposed: a confirmed `R` covers when its `about` holds a current criterion or no criterion at all (a confirmed "same as R<j>" repeat about nothing still raises the bar); one only about removed criteria does not (3, 9.1). Lena's acknowledgement line is in the L-KEEP table (18.4). |
| F9 no signatures for the new replies | Addressed: `revise_playbook -> PlaybookChange` (5.1); `acknowledge_playbook -> Message`; `MessageSender.send(acknowledges=)` on plain notes only; `msg.deliver` gains no key (9.2); the CLI output lines (8.5, 9.2). Instead of a `Recorded` return for `feedback`, the watch sentences come from a derived step, `ServiceSteps.watch_step` (8.5), the reviewer's "or an equivalent": `feedback` keeps returning `Message` (about 65 call sites in `src` and the tests assign its result, and the `Org` facade is pure delegation, so a new return type would move every one of them), and a derived reply cannot disagree with the files. The one loss, a failed write's error text, is declared (L11). `dispatch`, `org_signatures.json`, `facade_cases.py` and `constructor_dependencies.py` are in 20.1 and 21.4. |
| F10 refusal texts missing | Addressed: PB-WATCHED-OUT in full (8.6), PB-FIRST-EXISTS (5.3), ACK-NO-SERVICE and ACK-AGENT-WORDS (9.2), every `{needed}`, `{wrong}` and PB-TEXT string (5.3), REQUEST-UNREADABLE (13) and PB-UNREADABLE (19.1) word for word. |
| F11 zero and empty cases | Addressed: base 0 uses the 50-word floor (7); `add` on version 0, PB-FIRST-EXISTS, retiring the last item (`items=()`, the "has no items" prompt line, `CappedPlaybookTexts.body` only for `first`), `restore` without an earlier text (PB-ARGS), a no-op `move` (PB-SAME) (5.1, 14.1, 8.7). |
| F12 clause 2 for the last request | Addressed: L10 declared; G2(b) gains the derived end-of-stream check; section 15 item 8 lists the provenance of a recorded answer (1, 13, 15, 21.1, 22.6). |
| F13 grammar not round-trip safe | Addressed: column-0 headings and items, exactly 3 added and stripped spaces for continuations, any other line a parse error, the canonical `WHY` in a frontmatter `why` map with the body suffix checked against it, and the `parse(render(x)) == x` property test with seeded random lists (no new dependency) (4.1, 4.2, 4.4, 20). |
| F14 placement of restore and add | Addressed: placement rules for a step add, a rule add and a restore, and how a legacy section headed `## Rules` coexists with the product's (4.1). |
| F15 an unparseable item file is a dead end | Addressed as proposed: the next owner op writes a repair migration (new ids from `items_max + 1`, loss-checked, with the fallbacks) and says so; L6 restated (4.4, 14.1, 14.3, 16, 19.1, 21.3). |
| F16 the 330-word bound is infeasible | Addressed both ways: 14.2's text is shortened, id lists are clipped at 5, the bound is 400 words (measured on this text: 335 in G0's variant, 393 at the longest), and the digest's budget is `600 - words(fixed text)`, at least 200 (12, 14.2). |
| F17 user-visible changes not all named | Addressed: 21.5 now names the watch sentences in the MCP and CLI replies, the docstring clauses, `(rules citing it: ...)`, the migration's version bump, `hirearchy --help`, the CLI `services` and `quality` lines, D6's owner effect and the removed whole-version restore step, and every new refusal by name. |
| F18 the runtime retire may never run live | Addressed with option (a) and the honest part of (b): memo 5's rejection is now a scripted contract gap in C11's lineage in every stream, so it relates to B whatever the team did; because B's coverage is empty after memo 4 (F8), its owner may still retire it first, so G1(b) can be vacuous in a stream: that is reported, and the e2e of 20 (3) is G1(b)'s proof (18.4, 18.5, 21.1). The cost estimate follows (18.7). |
| F19 the probe's expected difference | Addressed: the probe compares `tool_load` results, not `tool_call` results, and checks arm F's `services` result shows the lock as a positive control (18.3). |
| F20 goldens missed | Addressed: `org_signatures.json`, `facade_cases.py`, `cli/help.txt` and the new help page, `cli/services.txt`; `events/line_shapes.txt` named as unchanged, with why (21.4). |
| F21 `_parse.py` and the requester's dependency | Addressed: `services/_parse.py:playbook_of` (4.2, 20.1); `RuleServiceRequester` gains `evidence: ServiceEvidence` (13, 20.1). |
| F22 `actor` of runtime writes | Addressed as proposed: `actor` = `kernel.RUNTIME`, the label in `by` (4.2, 4.3, 8.5). |
| F23 the migration's note and event | Addressed: it emits `service.revise`; one quiet note per call, its own when the triggering op is refused (4.4). |
| F24 the dropped second control | Addressed: D11 (21.2), referenced from 18.2. |
| F25 the settler and `LINK_FAILED` | Addressed: the settler runs before `LINK_FAILED` is raised (8.5). |
| F26 "a locked playbook gets no watched items" | Addressed: the sentence is replaced by the lock-after-admission case (8.5). |
| F27 the org-run total | Addressed: recomputed for the revised script, 6 x 71-103 = 426-618 plus 2 probe runs, about 430-620 (18.7, 21.6). |
| F28 "no item enters" | Addressed: "no gated item enters" (1, 15). |
| F29 memories across streams | Addressed: the owner's `memories.db` md5 is recorded before and after every stream; a change stops the study before the next stream (18.2). |
| F30 PB-C-WORDS with several ids | Addressed: one "Write it as" sentence per id (6.2). |

**Revision 3 changes these revision-2 answers:** F5 (the tokens now keep every symbol, R2-F2), F6 (`E` is now `max J(c)` over the judged
deliveries of the first k candidates, not the k-th candidate's first done time, R2-F1; it still never moves once defined), F13 (a step `add`
after a rule is refused and every write asserts the round trip, R2-F7), F15 (the repair migration now carries watches, R2-F17), F18 (memo 5's
line now rejects the first delivered version only, R2-F10), F19 (the positive control now reads `contract v2` against `contract v1`, R2-F9) and
F21 (the requester also gets the store, R2-F6).

### 23.2 Design review 2

Each finding of design review 2 (1 HIGH, 10 MEDIUM, 14 LOW) and how revision 3 resolves it (kept as written; revision 4 changes R2-F1's
window, which now closes at `D` and `K`, R2-F2's tokens, which keep a leading symbol, R2-F6's wiring, now through `CaseServiceEvidence(...,
mail)` and every reader, and R2-F16's carried window, no longer open-ended; 23.3 says how), under the manager's pass-3 directives
(`.agents/tasks/manager-decision-design-loop.md`). None changes the goal, the exit criterion, the binding design principle, SKILL.md's
constraints or the owner's test policy. The user-visible additions (FEEDBACK-UNANSWERED, PB-RACE, the restore variant of PB-ACK, ACK-ARGS,
the `acknowledges:` header, no item text in root's note, the marks' JSON keys) are each one a directive or a review fix names; they are listed in
21.5 and the two that change root's order of calls are open question 1 of 21.6.

| Finding | Directive | Resolution |
|---|---|---|
| R2-F1 (HIGH) the watch reads only first deliveries | adopt as written; re-check 18.4 | `judged(c)`, `J(c)`, `E = max J(c)` over the first k candidates (undefined until each has one, fixed once defined) and `clean` exactly as the review defines them (section 3); a superseded delivery without a verdict holds nothing. Updated 8.1 (rows v-viii: human rework accepted, relayed rework rejected, the k-th candidate rejected on its rework, a late verdict on the superseded delivery), 8.2, 8.7, 14.1's waiting line (cases with no judged delivery, `ItemWatch.waiting`), 18.4, 18.6 (the four self-check cases, and a run on the kept G0 and E7 mail), L12 and 19.3. 18.4.1 re-checks the script on the new definitions against G0's and E7's flows: A reaches `kept` at R4's answer (about T16-T21) and B is retired at R5's answer (about T20-T27), inside the 30-turn cap at every pace G0 showed; only memo 6's accept may be cut at G0's slowest pace. |
| R2-F2 symbols pass as formatting | adopt as written | The review's `TOKEN` pattern, verbatim, in section 3 and 6.1; unit rows for `<`/`>`, `=`/`≠`, `%`, `$`/`€`, `UTC+2`/`UTC-2`, `-3`/`3`, `✓`/`✗` (gated) and `**Due:**  ISO` -> `Due: iso` (formatting); a scratch run of the pattern on these pairs gave exactly these results. D1, 6.1 and 22.2 restated ("only spacing, case, markdown markers and sentence punctuation may change"). |
| R2-F3 restore bypasses the guard | adopt as written | 9.1: an owner's `restore` replacing the live text of a covered item is weakening on tests (i) and (ii); the restored text's coverage is its `why` entry when it was live, else its tokens; exempt restores included. 5.1 step 5 runs the guard last for `restore`; `restore` takes `acknowledged`; PB-ACK's `restoring it to the text of v{k}` variant; the parent acknowledges with `op="edit"` and the restored text's hash. |
| R2-F4 the settler after an exempt change | rule 1 as written; rule 2: an exempt restore restarts the watch, with D4's carryover | 8.1 W1 (a move or formatting edit keeps the watch; "still live in the watched text" = live with equal text tokens; the retire removes the current text), W2 (an exempt restore of a client-written text restarts the watch on the restored text, related rejections kept; the settler compares against it), W3; 8.5's settler reads them; three 8.7 rows (move or formatting edit, exempt restore, gated change of a warned item) and unit rows ix-x. |
| R2-F5 two unsynchronised writers | adopt; lock in `FsServiceStore`; R9 named; two-writer test | 4.3: `fcntl.flock` on `services/<name>/.tmp-playbook.lock` (the `.tmp-` prefix every org's `.gitignore` already ignores, so `git add -A` never commits it; hidden from `FILE_SHAPE` and `visible()`), the version check, the archive by exclusive create (`O_CREAT|O_EXCL` semantics through a hard link), then the atomic write; `MemoryServiceStore` makes the same version check; `PlaybookRace`; PB-RACE for the owner (5.3), `failed`/`retire due` and a retry for the settler (8.5). R9 holds (one writer package; the lock serialises its processes); `write_playbook`'s signature is unchanged, so `ServiceStore` stays at R7's 8 methods. 19.1 row; the two-writer integration test (20). |
| R2-F6 "answered" derivation and dependencies | adopt as written | `services._criteria.unanswered(basis, store, owner, name)` with `_retire.py:73`'s rule, used by retirement, the definer, the requester and the new accept refusal (13); 13's wrong sentence corrected. Constructor changes in 20.1: `RuleServiceRequester(+evidence, +store)`, `CaseServiceEvidence(+versions: ContractVersions)`, `TextServiceSteps(+evidence)`, `RuleClientFeedback` and `RuleContractDefiner(+settler)`, `RuleAcknowledger(agents, catalog, owners, evidence, sender)`, plus `RuleItemReviser` and `RuleWatchSettler` in full. |
| R2-F7 a step after a rule | adopt as written | 4.1 placement and 5.3: `after={x} is a rule: a step goes after a step (or leave after out)` (PB-ARGS); `RuleItemReviser` and the settler assert `parse_items(render_items(items), meta) == items` before every write (an `AssertionError`, 19.1). |
| R2-F8 PB-TEXT refuses a criterion's words | adopt as written | 4.1 and 19.2: the capitalised-`THEN` ban applies to `when` only; a text for which `item_words(text, current criteria)` is not None is exempt from the keyword, bracket and length rules; PB-C-WORDS quotes the full text, or "its words exactly as `services` lists them" over 300 characters (6.2). |
| R2-F9 the probe's positive control | adopt as written | 18.3: root's `services` shows `contract v2` (arm F) against `contract v1` (arm I), nothing else; the lock is checked by the hook (`define-service --locked`'s reply, `SERVICE.md` `locked: true`, the owner's quiet note). |
| R2-F10 memo 5's line | adopt as written | 18.4: Lena rejects memo 5's first delivered version only; later versions are judged by the key (C12); the same wording for memos 2 and 4. The decision table pre-registers each scripted rejection's expected item (memo 5: `About C11: ...`); when root's answer names neither C11 nor a replacement, G1(b) is reported vacuous for that stream (18.4, 18.5, 21.1). |
| R2-F11 the loss check's empty keys | adopt as written | 4.4: the multiset of the non-empty `line_key` values (as `changed_lines`); the corpus requires the per-block split, no fallback, on all 42 kept files and every generated v1; a fallback names itself in the migration's reason. |
| R2-F12 a (c) `WHY` without `R<k>` | the refusal route | 6.2: `added_h` keeps only criteria some human rejection's `verdict.confirmed` names (`c.id in a.verdict.confirmed`); a criterion confirmed only by a link on a relayed rejection admits nothing, with a note in G1's text (the refusal that applies); so every gated `WHY` holds an `R<k>` by construction (6.3, 10, D9, D13). It refuses no flow of E7 or G0 (their (c) criteria answer the stream's human rejection and the product's link on it names them). |
| R2-F13 0-to-2 in one call | adopt as written | 8.3 and 8.7: the two cases stated; the retire's note is sent and no warning note. |
| R2-F14 the rejected task's latest result | adopt as written | Section 3: "the latest result of the rejected task created before the rejection note". |
| R2-F15 a (c) edit inherits the warning | keep D4, say so | D4 and 8.2 say it: the client's words inherit the warning, one more related rejection retires them, PB-WATCHED-OUT bars them until another confirmation; raising the bar wins over convenience. |
| R2-F16 retire and restore or re-add clears a warning | carry the related rejections over | Section 3 "carried watch" (i): a restore of the same id, or an add with the same text key, after an owner's retire in `warning`, continues that watch (same start, related rejections, open-ended window); derived, no new state. 8.2, 8.7, unit row xi, 22.2. 8.6 extends PB-WATCHED-OUT to a text its owner retired while its watch retire was due. |
| R2-F17 a hand edit clears every watch | carry watches by text key | Section 3 "carried watch" (ii) and 4.4: a repaired item whose text key equals that of an item in its watch in the last parseable version continues its watch; the settler repairs before a due retire (5.1's new order: migration, then settler; 8.5); the two shapes that cannot be carried are declared in L6. Unit row xii; integration test (20). |
| R2-F18 the client note's text | adopt as written | 5.2 names "no item text in root's note" as a new rule with its reason; D12; 21.5. |
| R2-F19 the quality JSON's marks | adopt as written | 14.4: the marks gain `op`, `item` and `item_kind` (the mark's `kind` key is already `"playbook"`); the one quality golden with a playbook mark (`e3.json`, already moving for `watch`) and `tests/testkit/quality_schema.py` move; the replay kit compares named keys, so no replay expectation moves (21.4). |
| R2-F20 which refs `r` uses | adopt as written | 8.4 and section 3: the refs of the text at the watch start; an edit within the watch changes neither `r` nor k. |
| R2-F21 the last-request window | adopt the refusal | 13.2 FEEDBACK-UNANSWERED, with its exact text and CLI forms, FEEDBACK-UNREADABLE, 15, 16, 19.1, 19.3, 21.1, 21.5, 21.6 (question 1, next to REQUEST-UNANSWERED); L10 narrowed. Replayed against the owner's mail of E7 s1-s3 and G0's six streams: 0 refusals (every accept of a case with a human rejection came after that rejection's human answer, L-ASIS endings included). One exception, found while checking it: the accept of a task in `basis.unrated` is not held, because P2-UNRATED makes the answer wait for exactly that verdict, so a rework delivered before the answer would otherwise deadlock the case (13.2, D8); the option to remove the exception by narrowing P2-UNRATED is open question 2, since it changes a 0a.2 refusal. |
| R2-F22 four `acknowledge_playbook` details | the suggested choices | ACK-ARGS for a hash passed with `op="retire"`; ACK-WORDS with the length over 1000 characters; `acknowledged=` on a change that needs none is ignored with a reply clause; the hash is of the stored text, `when` normalised to `always` (9.2, 19.2, 5.1, 5.2). The argument is named `text_hash` (CLI `--text-hash`; ACK-KEY is now ACK-HASH), because revision 3's section 3 uses "text key" for `line_key`, the value the directives of R2-F16 and R2-F17 match on; one name for two values would have been ambiguous. |
| R2-F23 applying the acknowledgement is text | adopt as written | Section 15 item 9, outside the exit criterion; the study reports acknowledgements applied. |
| R2-F24 PB-SPLIT's remedy | adopt as written | "make it as smaller changes (one item, or part of an item, per call)" (7). |
| R2-F25 the locked retry and the header | adopt as written | 8.5, 19.1 and L11: on a locked contract the retry comes at the next recorded answer only, and the reply's sentence leaves out the owner's change; 21.5 names the `acknowledges:` header shown in `inbox` and `read`. |
| Also required: study cost staged | directive | 18.7: stage 1 (probe and first pair) about 260-390 credits, stage 2 (two pairs) about 480-740, total 740-1130; 3 valid streams per arm stay the minimum; 21.6 question 3. |
| Also required: the audit | directive | Section 22 re-run check by check against review 2's failures (checks 1, 2 and 6, and the risks noted under 3 and 5). |

### 23.3 Design review 3

Each finding of design review 3 (1 HIGH, 3 MEDIUM, 7 LOW) and how revision 4 resolves it, under the manager's pass-4 directives
(`.agents/tasks/manager-decision-design-loop.md`, "Pass 4 granted"). None changes the goal, the exit criterion, the binding design principle,
SKILL.md's constraints or the owner's test policy, and 21.6's four questions are unchanged. The user-visible additions are wording that the
findings name (the `report` hint, the contract-change note, the no-playbook prompt texts, the carried-watch reply clause, three read-failure
sentences) and are listed in 21.5.

| Finding | Directive | Resolution |
|---|---|---|
| R3-F1 (HIGH) the window closes at the k-th verdict, so the order of root's calls can turn a warned rule `kept` | adopt as written; (a) state and prove the monotonicity property; (b) the recording-order property test; (c) re-check 18.4.1 under `D`, with the expected state for each order | Section 3: `D` and the window exactly as the review's block gives them (the rejected result created at or after the watch start, and created at or before `E` or the rejection note created before `D`; open-ended while `E` is undefined); "and for an item with a related rejection" deleted from `E`, which is renamed "last judged delivery" because it is no longer the watch's end; related, pending, clean and kept read over the window in 3, 8.1 (computation step 5), 8.2, 8.7, 18.6, 19.3 and 21.1. The three unit and self-check rows are 8.1 xiii-xv and 18.6. (a) 8.1 states the property and proves it in four steps. **One addition, flagged for the manager:** under the window alone a rejection recorded after `D` on a result created before `E` (a second verdict on a judged delivery, a late verdict on a superseded one, or the first verdict on another case delivered before `E`) joins the window after the item reached `kept`, and moves it to `new` (pending) and then `warning`, which the property forbids. `K`, the end of the watch, makes exact the rule the design already had ("in its watch until it reaches `kept`"): from `K` on nothing recorded later joins the window. Before `K` the window is the review's, word for word. Step 1 of the proof needed three small refinements, each derived: a text's refs are taken as of its live-from, a "same as R<j>" rejection is pending while R<j> is (its `about` resolves through R<j>'s links), and an answering version's answer ids are subjects (so a recovered link adds none). With the open-ended clause gone, a warned item whose window has closed can stay `warning` for good (the directive's third path): declared as L15, reported in 21.1, and 8.7 has its row; carried watch (i) loses its own open-ended clause (its related rejections are carried, and its own window adds the later ones), and a restarted watch's window is the union of its watched changes' windows (section 3), so a restart keeps every rejection found so far, pulls in none that was outside, and the owner's op makes no rejection related (8.5's claim holds). (b) Section 20's recording-order property test: every order of a generated watch's records, asserted against the property and against the from-scratch derivation, with one corrected link as the only exception. (c) 18.4.1 re-derives A and B on `D` and `K` and pre-registers the expected state for every moment where root's order matters (O1-O9); 18.6 runs each order; 21.1 G1(a) and (f) read them. No order moves A to `warning` (but a reported variant of O5) or B to `kept`. |
| R3-F2 FEEDBACK-UNANSWERED's trigger counts an absent source as human | adopt | 13.2: the trigger is `source == "human"`; the MCP default `relayed` and a facade call without `source` (stamped `relayed` by `provenance_source`) are never held, the CLI's default `human` is; unit rows (20); 19.3, 21.1 G2(c), 21.5. |
| R3-F3 the watch's input and its readers' dependencies | `DerivedCaseRecords` gains `evidence` (one derivation path); `OwnedServicesListing` shows no states | `CaseServiceEvidence(history, catalog, versions, mail)` passes every result of every task to `watch_states(versions, cases, results, criteria, contract_versions)` (8.1). `QuotedPlaybookSection`, `EvidenceReflectSection`, `TextServiceReports` and `DerivedCaseRecords` each gain `evidence: ServiceEvidence` and call `evidence.watch` (14.1, 14.3, 14.4, 20.1). No R-rule forbids it (R4: `reflection` already imports `services`; R6: every new parameter is a Protocol; R7: `ServiceEvidence` keeps 5 methods) and the providers form no cycle, so the fallback was not needed; an integration test pins that every reader names the same states (20). `OwnedServicesListing` is unchanged. Every constructor is in 20.1's app row; `constructor_dependencies.py` is R6's engine and holds no list of classes, so it needs no edit, and `test_constructor_dependencies.py` checks every new parameter. Each reader's read failure has its text (19.1). |
| R3-F4 a leading symbol passes as formatting | adopt | `text_tokens` strips markers on continuation lines only (3, 6.1's code); gated rows `>5 rows`, `> 5 action items`, `+ 2 days ...`, `[x] reviewed`; the formatting example `- step` -> `1. step` (now gated on a first line) is replaced by a continuation-line example; L13 declares the continuation lines; D1, 15 and 22.2 restated. A scratch run with the product's `strip_markers` gave all 19 pairs of 6.1 as stated. |
| R3-F5 owner-facing texts not named | adopt; give each text's new wording; count its tests and goldens | 14.9 gives the new wording, word for word, of the `report` hint's two texts (where 11's AAR form now sits: the hint does not see the lessons text, so it names the form on every report instead of a conditional nudge, 11) and of the contract-change note's rule (c) clause and removed-criterion line (item ids for an item-format playbook, passed by `RuleContractDefiner._quoting`); 14.1 gives the two no-playbook texts; 21.4 counts 4 test files and 9 assertions (no golden holds these texts) and the no-playbook prompt goldens already counted; 20.1 and 21.5 name them. |
| R3-F6 the cap's candidates are not empty by construction | exclude the carried items | 10: a candidate is a `new` item whose watch rests on no `R<k>` (the `why` of the gated change that started its watch), which excludes the repaired items carrying a watch and, for the same reason (the cap must not cut a watch short), an item whose owner restored a client-written text during its watch (W2); 6.3 and D9's "empty by construction" now hold. |
| R3-F7 the reply to a carried add or restore | adopt | 5.2: the add and restore replies carry `It continues the watch of {old id}: warning ({R ids}); one more related rejection retires it`; `PlaybookChange.carried`; filled from the derivation after the write, with a fixed sentence when that read fails (19.1). |
| R3-F8 the settler's retire can write an unchanged body | adopt | 8.5: when the text before the watch has the watched text's tokens, the watch retire removes the item and restores nothing; 8.7 row; unit row (20). |
| R3-F9 a multi-line migrated item edits into one line | a declared limit; multi-line `edit` in the backlog | L14 (21.3); B-P1-1 (17); 22.5. Not built in Phase 1. |
| R3-F10 the narrowed guard is no deviation | adopt | D14 (21.2). The studies' rulings D8 and D14 cited in 18.4 and 18.6 are now named as theirs, so the labels cannot be read as this design's deviations. |
| R3-F11 the case rule omits the assignee | adopt | 13.2: the `revises` chain is followed only through tasks of the same service sent to the same assignee (`_cases.py:_build`'s head); unit row (20). |
| Also required: the audit | directive | Section 22 re-run against review 3's failures: checks 2 and 6 (R3-F1, R3-F2, R3-F3, R3-F4), with the additions under 1, 3 and 5. |
| Also required: 21.6 | keep as it is | Unchanged. |

**Flagged for the manager (readings of the pass-4 directives, none a brief-fixed item):** (1) `K`, the end of the watch, is added to the
review's window because the directive's property ("`kept` never back to `new`") is false under the window alone (a rejection recorded after `D`
on a result created before `E`); before `K` the window is the review's word for word. (2) A restarted watch reads the union of its watched
changes' windows, so an owner's gated change can neither clear a warning (D4) nor pull in a rejection that was outside, and 8.5's "only an
answer makes a rejection related" holds. (3) Without the open-ended clause a warned item can stay `warning` for good (L15; superseded by the
manager's B1, section 24), the directive's
third path; the study reports such items. None changes what the user sees.

## 24. Manager amendments (design loop closed)

Design review 4 (`.agents/tasks/design-review.md` and `.json`) returned CHANGES_REQUESTED with 0 HIGH, 4 MEDIUM and 5 LOW. The manager closed
the design loop by decision and approved this design with the binding amendments B1-B10:
`/Volumes/workspace/hirearchy/.worktrees/org-growth-p1/.agents/tasks/manager-decision-design-loop.md`, section "Design loop closed by decision
after pass 4" (published with the run's task files to `RESEARCH/phase-1/manager-decision-design-loop.md`). Its earlier sections, the pass-3 and
pass-4 directives, stay binding. The designer's three flagged readings of 23.3: (1) `K`, approved; (2) the union of a restarted watch's windows,
approved; (3) L15, superseded by B1. Where an amendment and older text of this file differ, the amendment wins.

| Amendment | Finding | What binds | Where it landed |
|---|---|---|---|
| B1 | R4-F1 (the reviewer's alternative) | A warned item's second related rejection is read over an open window, the **warned window**: every human rejection on a result created at or after the start of the watch in which the item was warned, recorded while the item is live in that watched text (token-equal, W1); a restart carries it under D4 and reading (2). The window, `E`, `D` and `K` are unchanged for `new -> kept` and for the first related rejection. The warned window only grows and the related count only grows; a warned item never reaches `kept`, and `K` is never defined for it. L15 is deleted, the open-form warning texts (8.3, 8.5, 14.1-14.3: "one more related rejection retires it") are true as written, and no closed form or D15 is added. 21.1 reports the warned items still warned at the end, each with its reason | 1; 3 (window, warned window, `K` and related rejection rows); 8.1 (states text, the property, proof step 3, computation step 7, row xx); 8.2; 8.7 (the closed-window row); 15; 18.4.1 (B's analysis, O7, O8); 18.6; 20 (the property test's assertion 4); 21.1; 21.2 D4; 21.3 L15; 22 (checks 1, 2, 6) |
| B2 | R4-F2 (check 2) | PB-WATCHED-OUT and carried watch (i) also cover an owner's gated `edit` (of any live item) whose new text key equals that text; the edited item keeps its own related rejections too (the union). A rule's text key is the key of its `then` (its `text` field), so a rule re-added as a step with the same words is caught. Two unit rows and a row in 16 | 3 (text key and carried watch rows); 5.1 step 5; 5.2 (the gated edit's carried clause); 8.1 row xxi; 8.2; 8.6; 8.7 (two rows); 15; 16; 18.4.1 O9; 20; 21.2 D4; 21.5; 22 check 2 |
| B3 | R4-F3 | A contract version's time is `Contract.defined` (written once per version), never the contract's `created` (carried from v1). Times are compared as aware datetimes (`stamp_of` against `parse_time`); at an equal microsecond a contract version comes before the link note written after it. A unit row: an old rejection answered by a contract version whose `defined` is after the watch start leaves `r` and k unchanged | 3 (the `K` row); 8.1 (proof step 1, row xxii); 8.4; 18.6; 20; 22 (checks 1, 3, 6) |
| B4 | R4-F4 (the reviewer's main fix) | Lineage is taken as of a time t: the criteria removed by the latest stored contract version whose `defined` is at or before t and that added `C<k>`'s text (present in it, absent from the version before), and their lineage as of t, each id visited once. A rejection's subjects are taken at the time of its answer, so they are fixed once it is not pending. Unit rows for a re-added v1 text and a cycle; moment O10 with its pre-registered state (B relates to R5 through C6's re-add: retired at R5's answer) and its L-KEEP decision-table note | 3 (subjects and lineage rows); 8.1 (proof step 1, rows xxiii-xxv); 18.4 (memo 4 and 5, the L-KEEP rows); 18.4.1 (O10 and its note); 18.5; 18.6; 20; 21.1; 21.2 D10; 22 (checks 1, 6) |
| B5 | R4-F5 | The corpus is every `PLAYBOOK*.md` under `studies/`: E, E2, E3, E4 s1/s1r/s2/s2r/s3, E5-E7 s1-s3, G0's six; 42 files | 4.4; 20; 22 check 5 |
| B6 | R4-F6 | The locked form of the `retire due` states line: `P12: retire due (R4, R6 are related): the runtime retires it at the client's next answer; follow the contract` | 14.1; 21.4; 21.5 |
| B7 | R4-F7 | PB-ITEM marks a watch-retired id `P12 (retired by the watch in v{n}: it comes back only as a confirmed criterion's own words)`, and, when step 3 of the same call wrote that retire, starts with `The watch retired {id} in v{n} (rejections {R4}, {R6}). ` | 5.1 step 3; 5.3 (PB-ITEM); 21.4; 21.5 |
| B8 | R4-F8 | `{what}` = `a verdict on {task}` or `a rework {task}` (the oldest); `{sections}` = the heading lines without `#`, joined by `, ` (`none` for a body without headings) | 5.3 (the placeholder table); 21.5 |
| B9 | R4-F9 (refines the R2-F2 directive) | `~` is dropped only as the pair `~~`, and `#` only as the run at the start of a line, so `within ~5 days` -> `within 5 days` and `see #3` -> `see 3` are gated; unit rows. A scratch run with the product's `strip_markers` on 6.1's pairs and the new rows gave the stated results | 3 (text tokens row); 6.1 (the code and the rows); 20; 22 check 2 |
| B10 | 21.6 | The owner questions stay open with the owner; the plan assumes the recommended answers (Q1 both refusals approved, Q2 P2-UNRATED kept as it is, Q4 root's acknowledgement path approved); Q3 does not affect the build; every FEAT whose commits carry a Q1, Q2 or Q4 behaviour names the question | 21.6; the plan (`.agents/tasks/plan.md`) |

Unchanged by the amendments: the goal, the exit criterion, the binding design principle, SKILL.md's constraints (14.6), the owner's test policy
(section 2), the study's shape and cost (18.7), and the rule that this run commits only this file.

## 25. As built

This section is written after the build (FEAT-001 to FEAT-010, commits 1-45 of the plan, on `feat/org-growth-phase-1`) and records what the code at that
point does where it differs from the text above, or where the text left a reading open. Where it and older text of this file differ, this section wins
(like section 24). Every claim here was taken from the build's evidence note (`.agents/tasks/verification.md`, one section per FEAT) and from the code at
the build's HEAD. The design's behaviour (sections 4 to 16, B1-B10) is built as written; no pre-registered expectation moved (every E-G0 replay and
published count in `tests/e2e` and `tests/meta` passed unchanged in every FEAT's scoped run), and no FEAT recorded a stop to ask the manager. The owner questions
of 21.6 stay open: the build used the recommended answers (B10), Q1 (both refusals, commits 3 and 4), Q2 (P2-UNRATED kept, commit 4) and Q4 (the
acknowledgement path, commits 30-33 and 36's sentence).

### 25.1 The planner's corrections PC-1 to PC-12, as built

| Id | Correction | As built | Commit(s) |
|---|---|---|---|
| PC-1 | The golden estimate is about 46 files (44 changed, 2 new), not 39-41 (21.4). `reflection/tests/expected` moves 13 files (7 `sections_*`, 4 `digest_*`, the 2 `services_{root,ceo}_three_playbook_versions.txt` listings); the colocated CLI help copies move; `cli/tests/expected/quality.txt` and the four `plans/template_*_service.yaml` do not | Held. The count as built is in 25.3: 49 files (47 changed, 2 new), 46 from the plan's list and 3 outside it | 3-41 |
| PC-2 | An `op: first` version keeps today's quality-mark text. Root's v1 from `define_service(playbook=...)` and `apply_org` stores no `admitted` key, so its basis stays `client` | Held. Root's v1 is in item form (`op: first`, no `admitted`) and its mark reads "written by the client (no admission needed)"; the owner's `op="first"` reads "first version". `quality/empty_service.txt` is byte-identical. Guards: `reflection/tests/test_marks.py::test_roots_item_form_v1_keeps_written_by_the_client`, `::test_a_first_version_keeps_todays_text` | 20, 41 |
| PC-3 | The `Org` facade cannot write an acknowledgement: `check_root_send` refuses `acknowledges` from any actor and `Org.send` gains no parameter | Held. The refusal text is `FACADE_ACKNOWLEDGES`; `MessageSender.send` gains `acknowledges`, accepted only on a plain note (`check_acknowledges`, applied by every sender and by the recording fake); `acknowledges` is among the guarded fields of `tests/architecture/test_policy_free_primitives.py` | 29 |
| PC-4 | `ServiceEvidence.admit` stays beside `admit_item` from commit 18 until commit 21 switches the reviser, then `admit` and P1's line stage go | Held. `ServiceEvidence` ends at 5 methods (`links`, `admit_item`, `confirmed`, `amendment_basis`, `watch`); `Admission.lines`, `LINES_REFUSED`, `_admitted`, `_tag_of` and `_lines_refused` are gone | 18, 21 |
| PC-5 | The CLI prints `watch_step`'s lines: `FeedbackCommand` and `DefineServiceCommand` gain `steps: Provider[ServiceSteps]` | Held, wired in `app/wire_cli.py`; one line per sentence after `feedback --confirms`, the automatic link and `define-service --answers` | 28 |
| PC-6 | The generated-v1 half of 4.4's corpus assertion lives in `tests/meta/test_playbook_migration_corpus.py` | Held: 42 kept files and every generated v1 migrate with the per-block split and no fallback | 7 |
| PC-7 | The reflection stories write playbooks through the new ops | Held: `reflection/tests/_support.py:revise` is replaced by `first_playbook` and `add_step` (and `legacy_playbook` for a v1 that must be free text) | 21 |
| PC-8 | `acknowledge_playbook` has one MCP signature for root and managers | Held: `owner, service, item, op, text_hash=None, words=None` for both; a manager that passes `words` meets ACK-AGENT-WORDS | 31 |
| PC-9 | `Rejection.case` has the default `""` | Held; `amendment_basis` fills it | 2 |
| PC-10 | The lock file's git-ignore test lives in `tests/e2e/test_org_growth_1.py`; the two-writer test (`multiprocessing`, a real directory) lives in `services/tests/test_store_race.py` with no `integration` marker | Held (`test_the_playbook_lock_file_is_never_committed`; the race test uses the `spawn` context) | 10 |
| PC-11 | FEAT-010's end-to-end tests are acceptance guards, GREEN when written | Held: all 13 test functions (the E5-E7 one in nine streams) were green when written; no fix commit was needed | 42-45 |
| PC-12 | The merge step runs claude-sonnet-5.5 at effort high | Binds the merge step; nothing in the code. Every agent seat of the build ran claude-sonnet-5.5 at effort high or better, and no test configures a lower model or effort | merge |

### 25.2 Deviations and readings, by FEAT

Each entry is a place where the text left a gap and the build chose a reading, or where the build differs from the plan's or the design's wording. None
changes a guarantee of sections 15 and 16 or a user-visible change of 21.5.

**FEAT-001 (clause 2, commits 1-4).**
1. Where 13.1 and 13.2 leave a gap: several unanswered rejections read ` (and {k} more: {R ids})` right after "has no recorded answer yet", and the question's trailing full stop is dropped once (`removesuffix(".")`) so the refusal does not read "no.. On yes". The template constants are the design's, word for word.
2. Six test sites that send a new request after an unanswered rejection (reflection `test_cases`, `test_digest`, `test_prompt_sections`, `test_reports`, the second request of `tests/golden`'s `test_service_and_playbook_files`, the dashboard demo organization) use a test-only seam (`services.testing.unheld_requests` / `unheld_request`, `testkit.services_world.request_unheld`), because a recorded answer would add a message, shift message ids, move 11 dashboard screen goldens and a case id in `services_text_root.txt`. Production code has no switch.
3. Services tests that need rejections to stay unanswered use a rework (never held) instead of a fresh request; mcp_server, health and the 0b and 0b_given e2e files record the user's answer first, with their assertions unchanged.

**FEAT-002 (the item model, commits 5-9).**
4. `services.api.PlaybookSection(heading, numbered, ids)` is new: two sections can have the same heading line, so a section also carries its item ids in order, and the round trip is exact. No stored key changes.
5. `content_words(items, headings, *, body="")` counts a heading's `str.split` words verbatim (the `#` run included); `items=None` is the legacy form (`len(body.split())`).
6. The parser accepts `- [P<k>]` at the end of a line without its trailing space (an empty first line may lose it to a strip). A rule must be one line (a continuation is a parse error). When the frontmatter has a `why` entry for an item, the body must end with exactly its canonical suffix. A section without items is numbered only for `## Steps`.
7. Placement errors are `PlacementError(ValueError)` carrying the PB-ARGS clause; a restore whose old section is gone is placed like an add; a restored rule with no live predecessor goes first in the rules section.
8. `migrate_body(body, *, splitters=...)` is a seam so the two fallbacks of 4.4 are tested with a lossy splitter; the per-section fallback keeps each section's lines verbatim with `numbered=False`. The corpus is 42 files, 493 items, all migrated by the per-block split.

**FEAT-003 (the lock, commits 10-11).**
9. A playbook that states no version counts as version 0 (`playbook_version`): a missing file and a versionless hand-made file both compare equal to `archive_version or 0`, so such a file is written over without an archive, as before. Every versioned file is compared strictly.
10. The archive's temp file is written through the store's `AtomicWriter` (`history/.tmp-archive-PLAYBOOK.v<n>.md`, a fixed name because the lock allows one writer), hard-linked to `history/PLAYBOOK.v<n>.md` and removed; the `.tmp-` prefix keeps it out of `FILE_SHAPE`, the history glob and git.
11. `PlaybookRace`'s message is the store's ("the playbook was changed by another writer while this call ran: it is at v{current} now, so this write was not made"); PB-RACE (5.3) is the reviser's text, built from `.current`.
12. The runtime-write tests live in `services/tests/test_events.py`; the two-writer test runs one race in a module fixture and its tests read the outcome.

**FEAT-004 (the watch, commits 12-17 and two more).**
13. `migrate_body` is exported by `services.api` (a late re-export) so the watch reads a legacy playbook as it would migrate (8.7: virtual items, all `kept`). `Playbook.restores` is a new field read by `playbook_of`.
14. `ItemWatch` readings: `r` is `(failed, judged)` (the views print `unknown (n judged cases)` or the fraction); an item never watched has `k` 0, `r` `(0, 0)` and `watch_start` None; `text_version` is the version that wrote the watched change while the item is in a watch, else the version of its current (or last) text; `coverage` lists `R` ids first, then `C` ids.
15. Relayed and agent links are left out of the watch's records (they weigh nothing). `Records` is a data-only dataclass with module functions (R6). A user-initiated criterion has no lineage as of t: a `user` version that is the latest to add the text gives none, it does not fall back.
16. "After the live-from" is strict for a candidate's `done` result and for `judged(c)`; the window's results are "at or after the watch start". `K` is searched over every verdict note, every human link note and every answering contract version at or after `D`, re-reading the files up to each (0.29 s for a warned item over 120 judged cases). The warned window of a restarted watch is read per watched change, and a carried watch is evaluated again over the files, so a corrected link on an old rejection reaches the carrying item.
17. O9's "edit" variant: the edit cites the evidence B rested on (`WHY R2; C10`), the only evidence that could admit B's words, so R4 relates to the carrying item through its own refs.
18. Repair carry (ii) compares the keys of the old item's re-rendered line with the repaired item's text, because `render_items` is private to `services`; unparseable versions are skipped when versions are read.
19. `CaseServiceEvidence.watch` reads playbook versions through the catalog and contract versions through `ContractVersions`; the cases are `chains(..., since=contract.created, runs=False)`; it returns `()` for no contract, no playbook or an owner with no client. The "equal to the derivation from scratch" property is read as: the same files with cases, results and contract versions listed in reverse order give the state the last record left. An agent client's verdict is a verdict note whose sender is not root.
20. Two commits beyond the plan, neither adding a test function or changing behaviour: `cb74062a` (the corrected-link seeds of the order test each hold a corrected link) and `74bca5e0` (a docstring). Test helpers `reflection/tests/_watch_kit.py` and `_watch_stream.py` were added.

**FEAT-005 (the operations, commits 18-25).**
21. `RuleItemReviser(agents, catalog, texts, playbooks, delivery, evidence, mail, settler, *, splitters=SPLITTERS)` takes `mail` from commit 21 (PB-FIRST-LATE needs the oldest verdict or rework of any tier from the client's sent mail, and `ServiceEvidence` has no data path for it), not at commit 32; `splitters` is the 4.4 seam. The settler is the last positional parameter, after `mail` (20.1 listed it before).
22. `revise_playbook(actor, service, op: str | None, reason, evidence, *, item, kind, text, when, then, after, version, acknowledged, content)`: `content` and a nullable `op` are kept so that PB-FORM is the reviser's first check (5.1).
23. `PlaybookChange` carries more than 5.1 lists: `after`, `sections`, `migration` (the ready-made migration sentence), `watch_unread` (19.1's fixed sentence) and `carried_related`; `services._reply.playbook_reply` builds 5.2's reply from it alone. `Admission.confirmed` (new, `""` by default) is the id of the user's link that confirmed the criterion a (c) item is the words of (8.6 needs its time).
24. `{ids}` in "admitted ({rule}) on {ids}" is the admission's `why` (R ids, then C ids), not the cited evidence ids. PB-TEXT uses `text and then have more than 150 words with when ({x})` literally, for a step's text too. PB-ARGS joins its clauses in the order of the arguments; an edit with none of text, then and when says `text is missing`.
25. The 30% rule counts text tokens on both sides; the cap counts `content_words` (`## Steps` is two words); the refusal says "words" for both. 8.6's "owner retired while its retire was due" is judged by the watch as it is now (`related` of at least 2). `restore`'s default source is the latest version that holds a text different from the current one.
26. E4 replays (s1r, s2r, s3): E4's whole-text v2 is offered line by line, each changed line as one `add` of a step; every line is refused by PB-C-WORDS (the same criteria named), and the criterion's own words are admitted as an `edit` of the "none yet" item (rule (c)). Refusals quote the first 160 characters of an item (the old refusal quoted 600).
27. Tests that changed because the design changes the flow, outcomes kept: `services/tests/test_continue.py` (D6: a v1 after a verdict or rework is PB-FIRST-LATE), `app/tests/test_services_facade.py` (the first revision before the first report), `reflection/tests/test_cases.py` and `test_prompt_sections.py` (a v1 after a verdict is written straight into the store with `legacy_playbook`), `services/tests/test_amend.py` and `test_contract_service_prompt_sections.py` (item markers add 7 characters per line). New test helpers: `legacy_playbook`, `first_playbook`, `add_step`, `services/testing.py:_world(playbook_writer=...)`.
28. Between commits 20 and 21 six e2e tests of `test_org_growth_0a.py` and `test_org_growth_0a2.py` are red (named in commit 20's body): the whole-text revisions that commit 21 replaces by the op form. The README still names `revise_playbook(service, content, reason, evidence)` (the plan keeps the README unchanged). PB-ITEM had no B7 forms until commit 27.
29. Commit-message slip (history is not amended): commit 20's body gives golden changes as "15", "7" and "5 lines"; the real counts are 18+/14-, 3+/4- and 3+/4-.

**FEAT-006 (the settler, commits 26-28).**
30. `WatchSettlement.settle(owner, service, before, *, strict=False)`: `before` may be None (no warning note is sent); `strict=True` is the owner's op (a failed write raises, `PlaybookRace` becomes PB-RACE); the default records `SettleReport.failed` and never raises. `SettleReport` lives in `services/_protocols.py` and is re-exported by `_watch.py`.
31. A read that fails never refuses a call on the settler's path, the owner's included: the report records `("", error)` and nothing is written. The reviser's own reads still raise PB-UNREADABLE (19.1). A note that cannot be delivered is recorded in `failed` on the feedback and define paths and raised when strict.
32. The warning note's `{subjects}` is the ids the item cites (its `why` entry, else the `C` and `R` ids in its words, else `nothing`); `{case}` is `Rejection.case` (the task id when empty, `unknown` when unreadable). The text before the watch is the item's text in the last parseable version revised before `watch_start`, of the same kind and with other text tokens; an item not live in that version has no text to restore. The warning note fires for an item whose state is `warning` with exactly one related rejection that `before` did not have; after a repair `before` is dropped.
33. `define_service(answers=)`: `before` is read before the contract is written and the settler runs in a `finally`, also when the owner's note fails (its error still propagates) and before `LINK_FAILED`. `feedback(confirms=)`: the settler runs only when the link written has the human tier.
34. `watch_step` names every item whose retire is due (not only those related to the rejection answered), and each `op: watch` version whose `related` holds the rejection, oldest first; sentences are joined by newlines (the MCP reply appends them after a newline, the CLI prints one line each).
35. Refactor inside commit 26: `repair_of`, `and_ids` and `without` moved from `_ops.py` to `_items.py` so the settler shares them; no text changed. `RuleContractDefiner(..., restorer, settler)` and `RuleClientFeedback(..., store, settler)` take the settler last.
36. Commit-message slip: commit 27's body says `services/tests` 1400 -> 1415; the file went to 1419.

**FEAT-007 (the acknowledgement, commits 29-33).**
37. `services.api.acknowledge_reply(op, item, service, owner, note)` (a late re-export) is the MCP reply of 9.2; the tool normalises `op` (lower case) and `item` (upper case); the CLI prints its line from the note's `acknowledges` header. `text_hash(kind, text, when)` is `services._acknowledge.text_hash`. ACK-HASH accepts the 12 lower-case hex digits with surrounding blanks stripped. ACK-WORDS counts the stripped words (limit 1000 = `FEEDBACK_MAX`).
38. The facade's refusal text is `FACADE_ACKNOWLEDGES` ("refused: an acknowledgement of a playbook change is written by acknowledge_playbook(...), which checks that its writer is the owner's parent. Nothing was sent."). `check_acknowledges` in `dispatch/_sender.py` is applied by `RuleMessageSender` and by `RecordingSender`.
39. `Message.acknowledges` is declared after `trace` and written after it in the frontmatter (`test_message_provenance.py` pins `feedback, source, criterion, trace` as adjacent); the header shows it right after `criterion`.
40. CLI: `op` is a positional `retire|edit` metavar (not argparse `choices`) and `--words` is optional in argparse, so ACK-OP and ACK-WORDS are what the user reads; `--words` reads like define-service's (`@file` works). The command is exempt from `test_the_scenarios_cover_every_command` (its output is pinned by `test_service_commands.py`).
41. Sites forced by the new names: the `Org` surface is 99 methods (`test_core_surface.py`, `test_facade_signatures.py`, `test_facade_contract.py` pinned 98); the tool lists and command lists of the MCP and CLI tests; `cli/tests/expected/no_command.txt` and `unknown_command.txt` (see 25.3).
42. The guard's "new text's coverage" is membership of the old coverage's ids in the new text's ids (the admission's `why`, or the restored text's own `why` entry or `C`/`R` tokens); the one inexact case (a covered `C` reached only through the `about` of an `R` in the `why`) makes it ask the parent once more than needed, never less. A watch that cannot be read refuses a guarded op with PB-UNREADABLE; an op that needs no guard does not read the watch for it.
43. The reply clause `(acknowledged by {parent}, note {id})` is in the retire and restore replies only. "Older than the current text" compares the note's id time with the `revised` time of the first version of the unbroken run that holds exactly the item's current `(text, when)`. PB-ACK-BAD's `{other op or item}` reads `for {op} {item} of {service}` from the note's header (`for no change: it is not an acknowledgement` for a plain note). A malformed `acknowledged` is a PB-ARGS clause only when the change needs an acknowledgement; otherwise it is ignored with the reply clause.
44. Commit-message slip: commit 33's body says `skill/tests` 150 -> 152; the real numbers are 133 -> 135. A flake: `app/tests/test_wire_cli.py::test_the_scheduler_runner_runs_the_loop_until_there_is_nothing_to_do` failed once in commit 29's FAST and passed on a re-run of the file.

**FEAT-008 (the owner's texts, commits 34-39 and one more).**
45. `QuotedPlaybookSection(catalog, config, paths, evidence)` takes a `ConfigSource` as a fourth parameter (the head shows `{w} of {cap} words` and the cap is a setting). `services.api` also exports `render_items` and the new pure `watch_restores(versions, watch) -> int` (the version whose text a watch retire would bring back, 0 for none).
46. `ReflectSection.section(...)` takes `digest: Callable[[int], str]` (the digest within N words) so the section asks for `REFLECT_WORDS` less the fixed text, at least 200 words; `ReflectionDigest.reflection_digest(owner, service, words=None)` drops the oldest case line first (one stays), then clips the remaining case line ending `… (more: services)`. The digest is therefore derived twice in a reflecting prompt.
47. The head of a locked playbook stays today's (`# Playbook: {service} (v{n}, locked by your parent)`): the owner cannot change items, so the 14.1 head would say something untrue.
48. States line readings: `restored` reads `P2 step, restored (the watch put back the text of v1)`; waiting and pending join with `; ` in one parenthesis; a legacy playbook ends `Items get these ids when you first change one.` then `Item states: all items kept.`; `All other items: kept.` is left out when every live item is listed; a carried warning follows the design's example literally, a non-carried one carries `(case {case})` and the restores clause when `watch_restores` finds a version.
49. AAR parsing: a label needs its colon; a repeated label keeps its first part; a part ends at the next label and loses a trailing `.`/`;`. For a case whose final verdict is an accept the owner's view is its near miss only (`near miss: <part, clipped to 60>` or `none recorded`).
50. Step 3 for an agent client reads "Your client is an agent, so nothing can admit a change (only the first version): ..."; a locked contract keeps its four steps with "change" for "revise". `{eligible}` reads `now C9 (an item may be the own words of it)`, `C12 not confirmed yet`, `C14 user-initiated (never rule (c))`, at most 5 ids then `+n more`; `eligible_clause` and `warning_line` are public pure functions of `_sections.py`. The warning line is left out when the watch cannot be read, and an item with two related rejections (retire due) is not in it.
51. The removed-criterion line names at most 5 item ids, then `and {j} more` (`CITING_IDS = 5`); `RuleContractDefiner._quoting` returns a third value (item form) and `ContractAmendment.diff` gains `by_item: bool = False`. Report-hint, refusal and docstring texts are module constants (`dispatch/_lessons.py:AAR_FORM`, `LESSONS_MISSING`, `LESSONS_TOO_LONG`; `services/_hints.py`; `services/_amend.py`).
52. The generated v1's last step reads "... and pass `lessons` as an after-action review: Expected / Happened / Caught at / Cause / Prevent (the system cause, not a person), or Near miss when nothing went wrong." Text left alone on purpose: README lines 204 and 280, `_example_texts.py:247` and the four `plans/template_*_service.yaml` goldens still say "(steps, budget plan, pitfalls)".
53. Reflect word counts (heading line included, `str.split`): the longest variant of the fixed text is 398 words (bound 400); with `none yet` and no warning, 340 and 283 (the design's 335/278/393 count the same text without the heading line's 5 extra words); the whole section with 8 delivered cases is 580 words (bound 600). The fix-up commit `efe3f5ad` changed only the test that counted the section without its heading line. E-G0 sites touched, text only: `tests/e2e/test_org_growth_0a2.py:407` and `test_org_growth_0a.py:217` and `:268`; no replay expectation moved.

**FEAT-009 (root's views, commits 40-41).**
54. `quality/e3.json` carries `watch` for e3's legacy playbook: the 11 virtual items P1-P11, all `kept` (8.7: a legacy playbook's virtual items), not `[]` as the plan's table predicted; the record is filled from `ServiceEvidence.watch` alone. The text view is unaffected (it prints a watch line only for an item that is not `kept`).
55. `PlaybookMark` has five fields more than the plan names (`related`, `acknowledged`, `acknowledged_by`, `items`, besides `op`, `item`, `item_kind`); only the last three are JSON keys. `reflection` re-exports `ItemWatch` and `watch_entry` because `progress` may not import `services`; `reflection/_watch_text.py` (new, pure) holds the entry words.
56. The watch is read for the listing only for an item-format playbook with items; a legacy, unparseable or empty playbook has no item to watch (suffixes `free text ...`, `not in item form (...)`, `no items`). A failed read replaces the counts: `; watch not read ({error})` alone, the error clipped to 160 characters.
57. Wording where 14.3 and 14.4 give one example: `watched:` lists the items in a watch (`new`, `warning`, retire due as `warning (R4, R6; retire due)`), not `restored`; the quality line `playbook watch: ...` lists every item that is not `kept` (also `restored` and `retired`); the regression list's suffix reads `(rules citing it: P12)` when every citing item is a rule and `(items citing it: P4)` when one is a step (`services_text_root.txt` moved by 3 lines, not 1). The record's `watch` JSON has the eleven keys of 14.4 and no `retire_due`. Mark words for ops the design does not give: `edit P1 (step), admitted (b) on R1, R2`, `restores P2 (step) to the text of v2`, `move P2 (step)`, `retires P2`, each followed by `, acknowledged by root (note {id})` when the file names a note.

**FEAT-010 (end to end, commits 42-45).**
58. All four commits are acceptance guards (PC-11) and only `tests/e2e/test_org_growth_1.py` changed. `define_service(playbook=...)` writes v1 in item form, so the legacy-file migration is shown by writing the kept free-text v1 into the store with `legacy_playbook`. `testkit.g0_replay` puts every G0 contract at `lead/services/weekly-meeting-memo/` while G0's messages name `weekly-memo`: the c45 test moves the directory in the materialized copy. It freezes the runtime clock at 05:53:41Z (memo 1's rework run) so item A is live from the rework as 18.4.1 says, and its history is the kept free-text v1 plus one real `revise_playbook` add of C10's words. The parent of `ceo` is root, who is also the client, so one note each reaches `ceo` and root. The four commit bodies say "Owner questions: none carried" although c42's G2 test asserts REQUEST-UNANSWERED (Q1's behaviour): recorded here instead.

**Across the build.**
59. Counts: every `count.txt` raised only for the directories that gained tests; `collected_count --write` also raised `access`, `bootstrap`, `hierarchy`, `orgfiles` and `settings` each time (environment-dependent parametrization) and those were restored, never staged. Tests replaced (same directory, no floor dropped): P1's line-stage tests, `test_playbook.py`'s nine (by `test_ops.py`), eight collected whole-version restore tests, the exempt-admit and `lines` contract tests, and several tests renamed with their new text (FEAT-008).
60. `src/hirearchy/services/testing.py` gained `RecordingSettler`, `unheld_requests` and `unheld_request`; `tests/testkit/services_world.py` gained `legacy_playbook` and `request_unheld`.
61. `tests/architecture/org_signatures.json` was regenerated hunk by hunk: `_signatures --write` also rewrites 10 to 13 informational `annotated` strings of other methods (the committed pin is stale on them), which were not applied.

### 25.3 Goldens as built

Section 5 of the plan predicted about 46 files (44 changed, 2 new); 21.4 estimated 39-41. **As built: 49 files, 47 changed and 2 new**, counted with
`git diff --name-status main...HEAD` over `tests/golden/expected`, `src/hirearchy/*/tests/expected`, `src/hirearchy/*/tests/golden`,
`src/hirearchy/app/tests/snapshots`, `tests/testkit/expected_dash` and `tests/architecture/org_signatures.json` (the 2 new files are both
`help_acknowledge-playbook.txt`, in `tests/golden/expected/cli` and `src/hirearchy/cli/tests/expected`):

| Area | Files | Why |
|---|---|---|
| `tests/golden/expected/mcp/surface_*.txt` | 10 | `request`, `feedback`, `define_service`, `report` and `revise_playbook` texts; the new tool |
| `tests/golden/expected/plans/*service*.txt` | 10 | the generated v1 (AAR step, no Pitfalls placeholder, the label) |
| `charters/apply_service_example.md`, `blueprint/tests/golden/second_half.json` | 2 | the generated v1 and v1 in item form |
| `tests/golden/expected/services/` (`services_text_root.txt`, `service_and_playbook_files.md`) | 2 | the listing's playbook line; v1 in item form |
| `tests/golden/expected/prompts/` (`service_owner_no_playbook.txt`, `service_owner_reflect.txt`) | 2 | the playbook section and Reflect |
| `src/hirearchy/reflection/tests/expected/` | 13 | 7 `sections_*`, 4 `digest_*`, 2 `services_*_three_playbook_versions` |
| `tests/golden/expected/cli/` (`help.txt`, `services.txt`, new `help_acknowledge-playbook.txt`) | 3 | the new command; the listing's playbook line |
| `src/hirearchy/cli/tests/expected/` (`help.txt`, new `help_acknowledge-playbook.txt`) | 2 | the colocated copies |
| `tests/golden/expected/quality/e3.json` | 1 | the marks' `op`, `item`, `item_kind`; the record's `watch` |
| `tests/architecture/org_signatures.json` | 1 | `Org.revise_playbook`, `Org.acknowledge_playbook`, `Message.acknowledges` |
| **In section 5's list** | **46** | |
| `src/hirearchy/dashboard/tests/golden/wide-3-services-detail.txt` | 1 | the demo organization's v1 is in item form and the service screen prints the file (commit 21; found by a dashboard run outside commit 20's targets) |
| `src/hirearchy/cli/tests/expected/no_command.txt`, `unknown_command.txt` | 2 | argparse's usage and "choose from" lists name every command, `acknowledge-playbook` among them (commit 31) |
| **Outside section 5's list** | **3** | |
| **Total as built** | **49** | |

Byte-identical, as required: `tests/golden/expected/events/line_shapes.txt`, `messages/*`, `kiro/*`, `files/*`, every other prompt and charter, the four
`plans/template_*_service.yaml`, `quality/e3.txt`, `empty_org.txt`, `empty_service.txt` (PC-2), `a5_one_off_block.txt`, `cli/tests/expected/quality.txt`,
`src/hirearchy/app/tests/snapshots/**`, `tests/testkit/expected_dash/**`. Not goldens but pins that moved: `tests/architecture/facade_cases.py` and
`tests/testkit/quality_schema.py`. `pyproject.toml` and `uv.lock` are unchanged (no new dependency), `skills/hirearchy/SKILL.md` changed only at line 109
(still 125 lines; lines 39, 72, 92 and 100 byte for byte) and `ROOT_INSTRUCTIONS` measures the same before and after (`2597 2674 2814 27 120`).

### 25.4 Commits beyond the plan's list

Three commits are not in plan section 8: `cb74062a` and `74bca5e0` (FEAT-004, a test seed fix and a docstring) and `efe3f5ad` (FEAT-008, the 600-word test
counts the section's heading line). None changes a guarantee. Commit 21 carries the dashboard golden and commit 31 the two argparse goldens named in
25.3 (not amended into earlier commits).
