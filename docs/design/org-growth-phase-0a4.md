# Org growth, Phase 0a.4: the batch after the E6 FAIL (technical design)

Status: design, revision 2 (design loop pass 2; resolves the 21 findings of `.agents/tasks/design-review.md`, one by one in Appendix A). Branch `feat/org-growth-phase-0a4` off `main` `fe0c9fd` (the E6 study commit;
product code identical to `18c4ffb`); worktree `/Volumes/workspace/hirearchy/.worktrees/org-growth-0a4`. Baseline at `fe0c9fd`:
`skills/hirearchy/SKILL.md` 125 lines; `ROOT_INSTRUCTIONS` is not edited by this batch (2 642 characters at the reference path at 0a.3, cap 2 700).

Sources of truth (read in full for this design):
- `docs/research/org-growth/phase-0a3/0a4-brief.md` ("the brief") and `docs/research/org-growth/phase-0a3/e6-decision.md` ("the decision"; binding:
  D-E6-1, D-E6-2, D-E6-3, D-E6-5).
- `docs/research/org-growth/phase-0a3/e6-gate.md` ("the gate"), sections 1.3, 1.4, 1.6 and 3.
- `studies/E6-org-growth-0a3-recheck/STUDY.md` (F-E6-1 to F-E6-8) and its `evidence/` (s1, s2, s3; committed in `fe0c9fd`, so the replays read
  them from the repository, read-only); `studies/E5-org-growth-0a2-recheck/evidence/s3/` (the E5 kill).
- `docs/design/org-growth-phase-0a3.md` ("0a.3", sections 4.3-4.5, 6 incl. 6.1, 9-17), `org-growth-phase-0a2.md` (P3, 7.6, D19),
  `org-agent-model-floor.md`; `ARCHITECTURE.md` (R1-R13) and `docs/refactor-principles.md`; `docs/research/org-growth/phase-0a2/test-policy.md`.
- `docs/research/` is untracked and absent from the worktree: it is read at `/Volumes/workspace/hirearchy/docs/research/`.

Abbreviations: `SRC` = `src/hirearchy`, `TESTS` = `tests`, `EV6` = `studies/E6-org-growth-0a3-recheck/evidence`, `EV5` =
`studies/E5-org-growth-0a2-recheck/evidence`, all in the worktree. Every function named below was read in the worktree at `fe0c9fd`. Ids are
shortened to their last 4 characters where the stream is clear (`8613` = `20261024T160846733258-lead-8613`).

## 1. Overview

E6 failed clause 3 in s1 on two flagged items that were noise (a reviewer's "harmless" style note and a heading's tail), failed "no regression"
in 3 of 3 streams on turns and spend (not content), got two top-up replies whose premise was false (s3 #19 and #36), and saw 0a.3's detach fail in its one live test
(s3's scheduler 9756 and run 10491 died at the call's return with no `scheduler.exit` and no `run.end`). The decision builds A1 and A2, B in
full, C redone and bounded, and the small items of D-E6-5. Everything stays derived: no ledger, no stored state, no new message field; the one
new event kind is `scheduler.signal`.

| Item | Decision in this design | Where |
|---|---|---|
| A1 (D-E6-1) | **Ship.** The marker line's tail is no item when list items follow it (the line is a heading), or when it is wrapped in parentheses; both rules apply only to a tail that names no criterion id (a tail that names one is always an item, so A1 never hides a `C<k>` question). An inline question with no list after it stays an item. | 4.2 |
| A2 (D-E6-1) | **Ship.** One function, `kernel.client_items(body)`, splits the parsed items: those naming `\bC[0-9]+\b` are questions (they flag the result, withhold the path, enter the relayed rework's reply); the others are notes, shown in `progress` as `k notes for the client (no criterion): <items>` and never withheld. Every reader calls it. | 4.3 |
| B (D-E6-2) | **Ship.** A relayed result's return beyond what its relayed task still had goes back to the user's side, in every user figure (`user_spend`, `user_committed`, the approval ceiling). While the revised task is open, the top-up counts the user's runs the team still holds, and the reply says `The team still holds N of the user's runs for <task>; the rework can use them.` in place of `TOPUP`. The default hand-down is unchanged. | 5 |
| C1 (D-E6-3 step 1) | **First build item, no commit.** A zero-cost sign-in preflight, then a reproduction under the streams' conditions (sandbox `KIRO_HOME`, real org run in flight, `uv --directory ... run hirearchy mcp`, all-tools profile, `--trust-all-tools`, `--resume`), sampled every 0.1 s, one condition varied at a time in a fixed order under a bound of 30 chat calls, recorded in `.agents/tasks/c1-reproduction.md`. | 6.1 |
| C2 (D-E6-3 step 2) | **Ship, always.** The scheduler's SIGTERM and SIGHUP handlers write `scheduler.signal` at once, before any grace period. The event writer becomes safe to call from a signal handler. | 6.2 |
| C3 (D-E6-3 step 3) | **Conditional on C1's evidence**, by the decision table of 6.3: SIGHUP ignored (M5), the call's marker variables dropped from the scheduler's environment (M2), or the macOS service manager (M1). Each ships only with an integration test that fails in at least 2 of 3 valid runs at `18c4ffb` and passes 3 of 3 with the fix. If C1 does not reproduce the death, or its evidence fits no row, **C3 is not shipped** and C2 ships alone. | 6.3 |
| F-E6-6 (D-E6-5) | **Ship.** SKILL.md line 100: the keep-as-is accept is recorded only when the user keeps a delivered version after seeing it; a "keep it" about one part, or before they saw it, is no accept. | 7.1, 8 |
| F-E6-7 (D-E6-5) | **Ship (today's behaviour is not correct by design).** An agent's delegation without `revises` inherits the tier of the work it does, found through the trace of its open received work (the stamper's own rules), test-first. | 7.2 |
| SKILL.md spend ask (D-E6-5) | **Ship by replacing text in line 72**: the spend is asked "in the same message as the question or yes/no item that needs the rework". No line has to be freed; no tested needle is lost. | 7.3, 8 |

Not in this batch (the brief): A3 and D (rejected), Phase 0b, the E7 study, a credit for runs the product lost.

## 2. Technology stack (locked)

Python 3.11, the existing packages only (`mcp`/FastMCP, PyYAML; Textual untouched), the standard library (`re`, `dataclasses`, `signal`, `os`,
`threading`, `subprocess`, `tempfile`), `git` (already required), uv, pytest, `mypy==2.4.0 --strict`, `import-linter==2.15`, `scripts/static_checks.py`,
`scripts/check.sh`. No new runtime dependency, no new package, no new dependency edge between packages, no new file kind in an organization (M1's
transient files live in a private temporary directory outside it, 6.3), no new message field. One new event kind (`scheduler.signal`). Strict TDD
(R11) under the owner's test policy (section 14). Tools used by hand only, never by the default test suite: kiro-cli 2.33.0 (C1, and the C3
integration test, which is marked `integration`); `launchctl` only if C3 takes branch M1 (macOS, part of the OS).

## 3. Shared definitions (each defined once)

| Name | Home | Definition |
|---|---|---|
| client item | `kernel._text.client_questions` | One item of the first `Questions for the client:` block of a message body, by the parser's rules (4.2). |
| criterion id | `kernel._text._CRITERION_ID` | A match of `\bC[0-9]+\b` (case-sensitive) anywhere in an item's text. No contract is consulted. |
| question for the client | `kernel.client_items(body).questions` | A client item that names a criterion id. |
| note for the client | `kernel.client_items(body).notes` | A client item that names no criterion id. |
| open client items | `reflection.open_client_items` | The client items of a `done` or `blocked` result that nothing has settled: not rated (`reflection.rated`) and not revised by a root task with `source == "human"` (0a.1 DR-17, 0a.2 6.1; unchanged rule). Questions and notes are settled together. |
| user task, interval, grant, hand-down, ceiling | `reflection._cases` | As 0a.3 section 3, unchanged. |
| what a relayed task still had | `reflection._cases._spend` | For a relayed task `t` (the k-th of the chain): `max(0, t.budget + <the client's grants in t's interval> - <charged runs in t's interval>)`. |
| relayed return to the user | `reflection._cases._spend` | For a relayed task `t` whose latest result `r` came before `t`'s successor was sent (or `t` is the chain's last task): `max(0, r.budget - <what t still had>)`. 0 otherwise, and 0 for an agent client. Summed per case as `Case.relayed_to_user`. |
| open task (of a case) | `reflection._cases` | A task of the chain whose latest result is missing or `blocked`. `Case.open_tasks` lists their ids, oldest first. |
| held runs | `reflection.user_held` | For a rework root just sent that revises an open task of its case: `max(0, user_committed(case) - (case.runs - case.relayed_runs) - rework.budget)`. 0 otherwise. |
| work tier | `services._rework.ServiceReworkContext.work_tier` | For an agent: the `source` of its newest open received task in the trace the stamper gives its next message (the one trace of its open received tasks, else the one trace of its run batch); None for root and when there is no such trace or task. |

## 4. D-E6-1: A1 and A2, the question block holds only what the client must decide

### 4.1 Decision

A1 and A2 as decided, with one narrowing of A1 (Deviation 1): neither A1 rule drops a tail that names a criterion id, so A1 never drops a
criterion-tagged question. A3 stays rejected:
`roles/manager.md` line 27 and its goldens are not touched. The split is decided in exactly one place, `kernel.client_items`, which calls the
parser `kernel.client_questions`; no product module outside `kernel` calls `client_questions` (pinned by an architecture test, 4.7). A2 never
hides a criterion-tagged question: the split is exhaustive and disjoint, every item that names an id is a question, and every reader that
counts, flags, withholds or repeats questions reads `client_items(...).questions`. Together with A1's narrowing, every criterion-tagged text of
the block (a list item or the marker line's tail) reaches `.questions`.

### 4.2 A1: the marker line's tail (`SRC/kernel/_text.py:client_questions`)

Today (lines 26-50) the text after the phrase on the marker line is one item unless it is empty or starts with a "none" word, and the list
lines that follow (after blank lines) are items. 762f's line `Questions for the client: (reviewer flags; I did not settle them, and they touch
your answers)` therefore gave a fourth item.

New rule. With `inline` the tail as today (stripped of `:*_ `), `names_id` whether `inline` names a criterion id (`\bC[0-9]+\b`), and `listed`
the list lines that follow the marker after any blank lines (the same `_LIST_LINE` loop as today, which ends at the first blank, heading or
non-list line):
1. **a tail that names a criterion id is one item**, whatever its shape and whatever follows (`Questions for the client: C4: should
   non-actions be excluded?` before a list; `(C3: keep Marta's row?)`; `(C4-C6)` before a list). A1 never drops a `C<k>` question (Deviation 1);
2. **heading:** otherwise, when `listed` holds at least one item (a list line that is not only a none word), the tail is no item;
3. **remark:** otherwise, when the tail is wrapped in parentheses (`_wrapped`: all of it is one parenthesized group, its first `(` closed by
   its last `)`, one final `.` allowed), it is no item. `(reviewer flags; I did not settle them, and they touch your answers)` and the same with a
   final `.` are remarks; `(a) keep Sam's row? (b) drop Lee's line (style)` is not wrapped (its first `(` closes at the third character), so it
   stays one item;
4. otherwise the tail is one item unless it is empty or its first word is a none word (today's rule). So an inline question with no list after it
   stays an item.

The list items are unchanged. The docstring states the four rules. Code (the shape the implementation follows):

```python
_CRITERION_ID = re.compile(r"\bC[0-9]+\b")  # a criterion id: what makes a client item a question for the client (D-E6-1)


def _wrapped(text: str) -> bool:
    """Is all of ``text`` one parenthesized group: its first "(" closed by its last ")", one final "." allowed (A1's remark)?"""
    text = text.removesuffix(".")
    if not (text.startswith("(") and text.endswith(")")):
        return False
    depth = 0
    for i, ch in enumerate(text):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return i == len(text) - 1  # the first "(" closes here: wrapped only if this is the last character
    return False


def client_questions(body: str) -> list[str]:
    lines = body.splitlines()
    for start, line in enumerate(lines):
        text = _LIST_PREFIX.sub("", line.strip(), count=1).lstrip("#*_ ")
        if not text.lower().startswith(_QUESTIONS_MARKER):
            continue
        inline = text[len(_QUESTIONS_MARKER):].strip(":*_ ")
        listed: list[str] = []
        for ln in itertools.dropwhile(lambda x: not x.strip(), lines[start + 1:]):  # blank lines right after the marker are skipped
            m = _LIST_LINE.fullmatch(ln)
            if m is None:
                break
            item = m.group(1).strip()
            if item and not _is_none_word(item):
                listed.append(item)
        first_word = next(iter(inline.replace(";", " ").replace(",", " ").split()), "")
        names_id = _CRITERION_ID.search(inline) is not None  # such a tail is always an item: A1 never hides a C<k> question (Deviation 1)
        heading = bool(listed) and not names_id  # list items follow: the marker line is a heading (A1)
        remark = _wrapped(inline) and not names_id  # "(reviewer flags; I did not settle them, ...)" (A1)
        own = [inline] if first_word and not _is_none_word(first_word) and not heading and not remark else []
        return own + listed
    return []
```

`str.removesuffix` strips at most one `.` (a tail ending `..` is not wrapped). The loop's `depth` never goes below 0 before the first `(`
closes, because the text starts with `(`.

### 4.3 A2: one function for the split, and its readers

`SRC/kernel/_text.py` (exported from `kernel/api.py` and its `__all__`):

```python
@dataclass(frozen=True)
class ClientItems:
    """The items of a result's "Questions for the client:" block, split (D-E6-1): ``questions`` name a criterion id (``C<k>``): the client
    decides them, they flag the result and withhold its artifact path; ``notes`` name none: they are shown and never withheld. Each keeps the
    block's order; together they are every item of the block, each once."""

    questions: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()


def client_items(body: str) -> ClientItems:
    """``client_questions(body)`` split by whether an item names a criterion id (``\\bC[0-9]+\\b``): the one place that decides what is a
    question for the client (pure)."""
    items = client_questions(body)
    return ClientItems(tuple(i for i in items if _CRITERION_ID.search(i)), tuple(i for i in items if not _CRITERION_ID.search(i)))
```

`SRC/reflection/api.py` (exported):
- `open_client_items(task, result, case, root_sent) -> ClientItems`: the body of today's `questions_open` (lines 208-220) with the count
  replaced by the split: `ClientItems()` for a status other than `done`/`blocked`, for a result without items, when `task.service and
  rated(case, task)`, or when `root_sent` holds a `task` with `revises == task.id` and `source == "human"`; else `client_items(result.body)`.
- `questions_open(task, result, case, root_sent) -> int` stays (the deliverable checks call it for `withheld`):
  `len(open_client_items(task, result, case, root_sent).questions)`. Its docstring says it counts the questions that name a criterion id.
- `items_listing(items: Sequence[str]) -> str` (pure): moved from `_steps.rework_step` byte for byte: each item `clip_line(item, ITEM_CHARS)`,
  at most `ITEMS_SHOWN` of them joined with `; `, then `; and {k} more` when more remain; `ITEM_CHARS = 160` and `ITEMS_SHOWN = 5` move from
  `_steps.py` (`QUESTION_CHARS`, `QUESTIONS_SHOWN`; no test imports them).

Readers (found with `git grep -n "questions for the client"` and `git grep -n "client_questions"` at `fe0c9fd`; these are all of them):
1. `SRC/progress/_lines.py:CaseTaskLines.line` and `_questions_open` (lines 45-65): `_questions_open` becomes `_open_items(task, result, case)
   -> ClientItems`, which returns `ClientItems()` when `result is None` or `client_items(result.body)` has neither questions nor notes (the sent
   box is still read only then), else `open_client_items(task, result, case, self._mail.sent(ROOT))`. `asked = len(items.questions)` drives the
   artifacts part and the questions part exactly as today; then, when `items.notes`, the notes part (4.4) is appended, before `no feedback yet`.
2. `SRC/reflection/_steps.py:TextServiceSteps.rework_step` (lines 107-121), the relayed branch: `questions = client_items(revised.body).questions
   if revised is not None else ()`; `""` when there are none (also when the result has only notes); else `REWORK.format(revised=...,
   questions=items_listing(questions))`. `REWORK`'s text is unchanged. The notes never enter it ("only they enter clause-3-relevant replies").
3. `SRC/reflection/_deliverable_checks.py:179`: unchanged code; `withheld` now follows the questions only, through `questions_open`.
4. `SRC/reflection/api.py:questions_open`: above.
5. No other product reader exists: `status`, `whoami`, the dashboard and `observe` show these texts only through `progress` lines and the
   deliverable note. `SRC/progress/api.py:ProgressReporter.progress`'s docstring sentence becomes: "A done or blocked result whose ``Questions for
   the client:`` block holds a question that names a criterion id (``C<k>``) is flagged "ask the user before you copy or deliver", and its path
   withheld, until the user's own rework or the client's verdict answers it (a rework root relayed does not); the block's other items are listed
   as notes for the client, never withheld."

SKILL.md step 5 item 3 says which items need an answer before the copy (section 8, line 92), so the assistant's instructions agree with the
product's: notes are passed on with the delivery, questions are asked first.

### 4.4 Texts

- Questions part (unchanged): `{n} question(s) for the client: ask the user before you copy or deliver` (singular `1 question for the client`).
- **Notes part (new):** `{n} note{s} for the client (no criterion): {listing}`, with `s` = `s` when `n != 1`, `listing = items_listing(notes)`,
  and the part's trailing `.` stripped (as `case_total`'s part is), because the line joins its parts with `. `.
  E6 s1 #56 (8613) becomes:
  `... artifacts withheld (ask first). 2 questions for the client: ask the user before you copy or deliver. 1 note for the client (no criterion): Style: 'himself' in Sam's table row (reviewer: harmless). no feedback yet. case total: ...`
  E6 s3 after 6c63 (A2's cost) becomes, for task 9a5b:
  `... artifacts: lead/writer/work/memo-2026-10-05.md, lead/reviewer/work/review-memo-2026-10-05-summary-line.md. 1 note for the client (no criterion): Keep or delete the '## Open, not decided' section (one line: no decision recorded on flaky CI, Sam investigating)? It was in the version you judged, so I kept…. no feedback yet. ...`
  (the item cut to 160 characters by `clip_line`, which ends it with `…`; the part's trailing-`.` strip does not touch it).
- `REWORK` (unchanged): `{revised}'s result asked the client: {questions}. Ask the user these questions, unless the user asked for this
  change: a rework does not answer them.`, with `{questions}` the criterion-tagged items only.
- The deliverable note's `path withheld: ask first` (unchanged text) follows the questions only.

### 4.5 Code sites

`SRC/kernel/_text.py` (`_CRITERION_ID`, the A1 rules, `ClientItems`, `client_items`), `SRC/kernel/api.py` (exports); `SRC/reflection/api.py`
(`open_client_items`, `questions_open`, `items_listing`, `ITEM_CHARS`, `ITEMS_SHOWN`, `__all__`); `SRC/reflection/_steps.py` (the relayed branch;
the two constants removed); `SRC/progress/_lines.py` (`_open_items`, the notes part, `NOTES_PART`); `SRC/progress/api.py` (docstring);
`skills/hirearchy/SKILL.md` line 92 (section 8); `TESTS/architecture/test_client_items_single_reader.py` (new).

### 4.6 Zero and empty cases

| Case | Result |
|---|---|
| no block, or a block that says none | `ClientItems((), ())`: no questions part, no notes part, the artifacts as today |
| a block with only notes | the notes part; the artifacts shown (`artifacts: ...` or `no artifacts`); no flag; the relayed rework's reply is `""`; the deliverable check does not withhold |
| a block with only questions | today's line, byte for byte |
| questions and notes | today's questions part and the path withheld, then the notes part |
| an inline tail and no list | one item (a question if it names an id, else a note) |
| a parenthesized tail without an id and no list (`(...)` or `(...).`) | no item |
| a tail of several parenthesized parts without an id (`(a) ... (b) ... (style)`) and no list | one item (a note): it is not wrapped |
| a parenthesized tail with an id and no list | one question |
| a tail without an id before a list (a heading) | the list items only |
| a tail with an id before a list, parenthesized or not | the tail is one question, then the list items (declared limit 1) |
| a tail with an id before a list of notes only | 1 question: the result is flagged and its path withheld (never hidden) |
| a tail followed only by a `- none` list line | the tail stays an item (no list item follows) |
| more than 5 notes | 5 listed, then `; and {k} more` |
| a settled result (rated, or revised by a human rework) | neither part |
| a `failed` result, or no result | neither part (today's status rule) |
| a relayed rework of the task | both parts stay (DR-17) |
| `client_items("")` | `ClientItems((), ())` |

### 4.7 Tests to write first (each RED before its code)

- `SRC/kernel/tests/test_client_questions.py`: a parenthesized tail without an id, with and without a list after it, gives no item (762f's
  exact line, and the same line with a final `.`); a tail without an id followed by list items is a heading (with and without blank lines
  between); a tail that names an id followed by list items is an item before them (`Questions for the client: C4: should non-actions be
  excluded?` then `- Style: 'himself' (reviewer: harmless).` gives both, the tail first), parenthesized or not (`(C3: keep Marta's row?)` then a
  list); a tail followed only by a `- none` list line stays an item; an inline question with no list stays one (today's tests kept); a
  parenthesized tail that names an id with no list is one item; a tail that only starts with `(` (`(C3) Keep Marta's row?`) is one item; a tail
  of two parenthesized parts and a third (`(a) keep Sam's row? (b) drop Lee's line (style)`) is one item; a nested wrapped tail (`(see (b))`) is
  no item. The existing tests pass unchanged. `_wrapped` is private: its shapes are pinned through `client_questions` only.
- `SRC/kernel/tests/test_client_items.py` (new): the split by `\bC[0-9]+\b` (`C3/C4:`, `(C5;`, `AMB1 (C5)`, `Criterion: C4.`, `C12` are ids;
  `CI`, `c5`, `C2C`, `ABC1` are not); order kept; `questions + notes` is every item of `client_questions(body)`, each once (a property over
  the E3 bodies of the existing tests and the E6 bodies of 4.8); the id-tagged tail before a notes-only list gives 1 question and the notes; the
  empty body.
- `SRC/reflection/tests/test_pure_functions.py`: `open_client_items` (each settling rule for both parts; a relayed rework keeps both; `failed`
  gives none); `questions_open` counts only criterion-tagged items; `items_listing` (5 shown, `and 1 more`, clipping).
- `SRC/reflection/tests/test_steps.py`: the relayed rework of a result with only notes gets `""`; with both, `REWORK` lists only the
  questions.
- `SRC/reflection/tests/test_deliverable_checks.py`: a file that differs from a result with only notes is `differs` with its path (not
  withheld); with a criterion question it is withheld (today).
- `SRC/progress/tests/test_lines.py`: the notes part (singular and plural, its place before `no feedback yet`, the stripped final `.`, the
  `and k more` form); only notes: path shown and no flag; both: flag, withheld path and notes; an id-tagged marker tail before a notes-only
  list: `1 question for the client`, the path withheld and the notes listed; settled: neither.
- `TESTS/architecture/test_client_items_single_reader.py` (new, a source scan like `test_policy_free_primitives.py`): no module of
  `SRC` outside `SRC/kernel/` and outside `tests/` directories contains `client_questions(`.
- Replays, `TESTS/e2e/test_org_growth_0a4.py` (new, over the E6 kit of 17.1): section 17, items A-1 to A-5.

### 4.8 What A changes on E6's files (computed on `EV6` at `fe0c9fd` with the rules above)

Over the 19 results root received with a `Questions for the client:` block in s1-s3: 50 items today; 49 after A1 (762f's tail); 47 questions
and 2 notes after A2 (8613's `Style: 'himself' ...` and 6c63's `Keep or delete the '## Open, not decided' section ...`). Per result: 8613 gives
2 questions and 1 note (the path stays withheld: its two other items name C6 and C3); 762f gives 3 questions; 6c63 gives 1 note and its path is
shown (A2's cost: Lena was asked it anyway in T8); d80f gives 2 questions (unchanged). Both items that decided s1's clause 3 FAIL are no longer
flagged; no turn count changes (gate 3 A). No marker line that root received in E5 or E6 has a tail naming an id before a list (the review's
survey of every marker line), so the narrowing of Deviation 1 changes none of these numbers.

## 5. D-E6-2: B, the top-up counts the user's runs the team holds or got back

### 5.1 Decision

B in full, in two parts, both inside `reflection`, both derived:
1. **The return attribution.** A relayed result's return beyond what its relayed task still had (its budget and the client's grants in its
   interval, less the charged runs in its interval) is the user's runs coming back. It counts as returned on the user's side in `user_spend`,
   `user_committed` and the approval ceiling (`user_approved`), one helper for all three, so they stay consistent (0b reuses `user_spend` and
   `user_approved`). The decision's words "beyond its own task's budget" are read as "beyond what its own task still had of its budget"
   (Deviation 2: the literal reading leaves s3 #36's false top-up in place, 5.5).
2. **The runs the team still holds.** While the revised task is open (no result, or a `blocked` one), the top-up adds the user's runs the team
   still holds for the case (`user_held`) to what the rework can draw on, and the reply says so. `TOPUP` is replaced by the `HELD` sentence when
   the held runs cover the round, and carries it in its `{left}` part when they cover only some of it.

**The default hand-down is unchanged** (`services._request._default_budget`, `min(left, contract)`, 1 when nothing is left; `CaseAllowance.left`
= `user_approved - user_committed`). Held runs are already handed down: handing them down again would give the team the same runs twice and raise
the approval by them, against 0a.3 I4's rule, under which the default hands down at most what the user approved and has not committed (0a.3's
limit 1 aside: Deviation 3). `left` changes
only through part 1 (the user's returned runs are no longer read as held), which is what gives s3's 9a5b its runs.

### 5.2 The return attribution (`SRC/reflection/_cases.py:_spend`, `SRC/reflection/api.py`)

`_Spend` gains `relayed_to_user: int`. In `_spend`, after `bounds`, `relayed`, `in_relayed` and `handed_down` (lines 40-46):

```python
    def back_to_user(k: int, t: Message) -> int:
        """What the latest result of the relayed task ``t`` (the k-th of the chain) carried back beyond what ``t`` still had: its budget and the
        client's grants in its interval, less the charged runs in its interval. Those were the user's runs the team held. 0 for an agent client, a
        task that is not relayed, no result, and a result that came after ``t``'s successor was sent (its interval then misses some of its runs)."""
        r = results.get(t.id)
        if not human or t.source != "relayed" or r is None or (k + 1 < len(tasks) and r.id >= tasks[k + 1].id):
            return 0
        funds = t.budget + sum(n.budget for n in handed_down if _within(n.id[:21], bounds[k]))
        ran = sum(1 for s in charged if _within(s, bounds[k]))
        return max(0, r.budget - max(0, funds - ran))

    to_user = {t.id: back_to_user(k, t) for k, t in enumerate(tasks)}
```

The ceiling loop (line 53) adds the same amounts for the relayed results answered before the hand-down `h`:

```python
        back = sum(min(r.budget, t.budget) for t in users if t.id < h.id and (r := results.get(t.id)) is not None and r.id < h.id)
        back += sum(to_user[t.id] for t in tasks if t.id < h.id and (r := results.get(t.id)) is not None and r.id < h.id)
```

and `_Spend(..., relayed_to_user=sum(to_user.values()))`. `Case` gains `relayed_to_user: int = 0` ("the user's runs that results of relayed tasks
carried back beyond what each relayed task still had (D-E6-2); 0 for an agent client and without a relayed task") and
`open_tasks: tuple[str, ...] = ()` ("the chain's tasks whose latest result is missing or blocked, oldest first"), filled in
`DerivedCaseHistory.cases` (`open_tasks=tuple(t.id for t in tasks if (r := results.get(t.id)) is None or r.status not in ("done", "failed"))`).
Both default so every hand-built `Case` keeps today's meaning. `Case.returned`, `Case.relayed_returned` and `case_spend` are unchanged
(`case_spend` and the agent client's text stay byte-identical).

`SRC/reflection/api.py`:

```python
def _user_back(case: Case) -> int:
    """What came back of the user's runs: their own results' returns (each at most its task's budget) and the user's runs that relayed results
    carried back (``relayed_to_user``). The one helper of ``user_spend`` and ``user_committed``."""
    return case.returned - case.relayed_returned + case.relayed_to_user
```

`user_spend` (line 162) and `user_committed` (line 175) replace `(case.returned - case.relayed_returned)` by `_user_back(case)`. Their
docstrings say so. `user_approved` is unchanged in code; it moves with the ceiling, which reads the same amounts.

**Why it cannot over-credit the user.** `user_committed` is at least the user's charged runs (its `max(0, ...)` term), so `left = approved -
committed` never exceeds what the user approved and has not used. A share that holds another case's runs (the lead's whole pool came back) can
only lower `committed` to the user's runs, not below. And since the ceiling at a hand-down reads the same returns as `user_committed`, a
default hand-down of `left` sets a ceiling equal to the approval: the approval does not grow (5.5, the #36 numbers).

### 5.3 The runs the team still holds (`SRC/reflection/api.py`, `SRC/reflection/_steps.py`)

```python
def user_held(case: Case, rework: Message) -> int:
    """The user's runs the team still holds for the case when ``rework`` (a task of the case root just sent) revises a task that is still open:
    what the user's requests and grants handed down, less the user's charged runs and what came back to the user, less the rework's own budget,
    at least 0 (pure). 0 when the revised task has a done or failed result, or is not a task of the case. Read when the rework is sent: its own
    runs are not counted then."""
    if not rework.revises or rework.revises not in case.open_tasks:
        return 0
    return max(0, user_committed(case) - (case.runs - case.relayed_runs) - rework.budget)
```

`TextServiceSteps._top_up` (lines 124-141) becomes:

```python
        need = client_round(self._agents, task.to)
        if task.budget >= need:
            return ""
        approved = user_approved(case, contract.budget)
        spare = max(0, approved - user_committed(case))  # the case now holds this rework's budget too
        if need - task.budget - spare <= 0:
            return ""  # what is approved and unused covers the round: root may grant it without asking (unchanged)
        held = user_held(case, task)
        ask = need - task.budget - spare - held
        still = HELD.format(held=held, revised=task.revises) if held else ""
        if ask <= 0:
            return still  # the team holds the rest of the round: nothing to ask the user (D-E6-2)
        left = (SOME_LEFT.format(spare=spare, approved=approved) if spare else NOTHING_LEFT)
        return TOPUP.format(budget=task.budget, need=need, owner=task.to, left=f"{still} {left}" if still else left, ask=ask,
                            grant=need - task.budget - held)
```

The grant leaves out the held runs (the team has them), so a grant after the user's yes raises the ceiling by exactly `ask`, as in 0a.3.
`ServiceSteps.rework_step`'s docstring (`api.py`) adds: "... and, while the revised task is still open, the user's runs the team still holds for
the case count toward the round; when they cover it, the step says so instead of asking". `CaseAllowanceOf` (`_allowance.py`) is unchanged in
code; its docstring adds that the user's runs a relayed result carried back count as back.

### 5.4 Texts

- **`HELD` (new, `SRC/reflection/_steps.py`):** `The team still holds {held} of the user's runs for {revised}; the rework can use them.`
- `TOPUP`, `NOTHING_LEFT`, `SOME_LEFT`: unchanged templates. With held runs that cover only part of the round, `{left}` is `HELD` + ` ` +
  (`SOME_LEFT` or `NOTHING_LEFT`) and `{grant}` is `need - budget - held`. Example (round 5, a 1-run rework, nothing spare, 2 held):
  `This rework has 1 run(s), and a rework of this team needs about 5 (1, plus 2 for each agent below lead). The team still holds 2 of the user's runs for <id>; the rework can use them. Nothing else is left of the runs the user approved for this case. Ask the user now for 2 more run(s), with that number; on yes, grant 2: send(to="lead", budget=2, body=<why>) (CLI: hirearchy send lead "<why>" --budget 2).`
- No MCP tool docstring changes (so no MCP surface golden changes): root's `request` docstring already says the reply "names the top-up to ask
  for when a rework the user asked for gets less than a round of the team needs".

### 5.5 E6's numbers (`EV6/s3`, verified against the recorded replies)

Chain of memo 1: 4a3e (16, user), bc02 (1, human), 5d4a (6, relayed, injected), 9a5b (1, human). Charged runs: 5 in 4a3e's interval, 6 in
bc02's (the killed run 10491 included), 5 in 5d4a's. Results: 11cc (4a3e, `blocked`), 009a (bc02, done, no return), 74fa (4a3e, done, no return,
after bc02), 406b (5d4a, done, `budget: 7`, before 9a5b). Round of `lead`'s team: 1 + 2 x 2 = 5.

| Moment | Today (`fe0c9fd`) | After B |
|---|---|---|
| #19, bc02 just sent (cut `20261024T171425096624`) | committed 5 + (17 - 5) = 17, approved 17 (ceilings 16, 17), spare 0, `TOPUP` "Nothing else is left ... Ask the user now for 4 more run(s)" | 4a3e open (11cc blocked): held = 17 - 5 - 1 = **11**; ask = 5 - 1 - 0 - 11 < 0: the reply's step is `The team still holds 11 of the user's runs for 20261024T170957358424-root-4a3e; the rework can use them.` |
| just before bc02 (cut `...171425096623`) | `left` = 16 - 16 = 0: bc02 handed 1 | unchanged: `left` 0, bc02 handed 1 (the held runs are not handed down again; the approval becomes 17, 0a.3 limit 1) |
| just before 9a5b (cut `20261024T172453163610`) | user returned 0; committed 11 + (17 - 11 - 0) = 17; `left` 0: 9a5b handed 1 | 5d4a still had 6 - 5 = 1, so 406b's 7 carry **6** back to the user (`relayed_to_user` 6); committed 11 + (17 - 11 - 6) = 11; `left` = 17 - 11 = **6**: 9a5b would be handed 6, ceiling 11 + 0 + 6 = 17 (no growth) |
| #36, 9a5b as recorded (budget 1; cut `20261024T172453163611`) | committed 18, approved 18, spare 0, `TOPUP` "Ask the user now for 4 more run(s)" | committed 11 + (18 - 11 - 6) = 12; approved 17; spare **5**; 5 - 1 - 5 < 0: no step (`""`); `user_spend` 12, no overspend sentence |

The literal reading ("beyond its own task's budget": 7 - 6 = 1 back) gives committed 17 at #36, spare 0 and the same `TOPUP` asking for 4: it
removes neither false top-up, which is why Deviation 2 reads it by what the task still had. The gate's "6 of them the user's" and "9a5b: 5 left"
are this design's figures.

E5's replays (`TESTS/e2e/test_org_growth_0a3.py`) stay byte-identical under B1, by the same rule (computed on `EV5` for this revision): s1's
relayed 963a had `budget: 6` and 5 charged runs, and its result 592f returned `budget: 1`, at most the 1 it still had, so its share is 0 and
s1 T6's `user_spend == 10` and `user_approved == 17` hold; s2's relayed tasks f3df and a9cb were sent after both of s2's cuts
(`034308207974`, `034512547000`), so s2 T5's figures do not read them; s3's replays pin tiers only.

### 5.6 Code sites

`SRC/reflection/_cases.py` (`_Spend.relayed_to_user`, `back_to_user`, the ceiling's `back`, `open_tasks`); `SRC/reflection/api.py` (`Case` fields,
`_user_back`, `user_spend`, `user_committed`, `user_held` exported, docstrings of `rework_step` and `case_total` unchanged in meaning);
`SRC/reflection/_steps.py` (`HELD`, `_top_up`); `SRC/reflection/_allowance.py` (docstring). `SRC/services/_request.py` is not changed.

### 5.7 Zero and empty cases

| Case | Result |
|---|---|
| no relayed task | `relayed_to_user` 0: every user figure as today (`user_spend == case_spend` still holds without a relayed task) |
| a relayed task without a result, with a result of `budget` 0, or whose return is at most what it still had | its share 0 |
| a relayed result after its successor was sent | share 0 (conservative: the user's committed stays higher) |
| an agent client | `relayed_to_user` 0, `user_held` not consulted (`_top_up` returns `""`), today's text |
| a hand-built `Case` | `relayed_to_user` 0 and `open_tasks` (): today's values |
| the revised task closed (done or failed) | `user_held` 0: today's `TOPUP` or `""` |
| the revised task open, the team holds none | `user_held` 0: today's `TOPUP` |
| held runs cover the round | the `HELD` sentence alone |
| held runs cover part of it | `TOPUP` with `HELD` in `{left}`, `ask` and `grant` reduced by `held` |
| spare runs alone cover the round | `""` (today) |
| `revises` names a task outside the case, or the case cannot be found | `""` (today) |
| an owner with no agent below (`need` 1) | `""` (today: every task carries at least 1 run) |

### 5.8 Tests to write first

- `SRC/reflection/tests/test_cases.py` (fs world with run logs and results): `relayed_to_user` of the 406b shape (relayed 6, 5 runs in its
  interval, result returns 7: 6), of a relayed result returning at most what it had (0), of a grant in the relayed interval (counted in what it
  had), of a relayed result after its successor (0), of an agent client (0); `open_tasks` (no result, blocked, done, failed); the ceiling after
  a relayed return (a default hand-down of `left` raises no ceiling: the approval stays).
- `SRC/reflection/tests/test_pure_functions.py`: `user_spend` and `user_committed` read `relayed_to_user` and agree (one helper); `user_spend ==
  case_spend` without a relayed task (the existing property kept); `user_committed >= runs - relayed_runs` for any `relayed_to_user`;
  `user_held` (open, closed, not in the case, never below 0).
- `SRC/reflection/tests/test_steps.py` and `test_contract_service_steps.py`: `HELD` alone (the exact text); `TOPUP` with `HELD` in `{left}` and the
  reduced ask and grant, in both `{left}` wordings; a closed revised task keeps today's `TOPUP` (the existing pins, unchanged).
- `SRC/mcp_server/tests/test_service_tools.py` and `SRC/cli/tests/test_service_commands.py`: a human rework of a request whose result is
  `blocked` with runs unspent: the reply (and the CLI's line after the request line) is the `HELD` sentence, nothing asked.
- `SRC/app/tests/test_wire_cli.py::test_the_request_command_prints_the_step_of_the_runtime` (changed deliberately, 13 Rule B): it already
  revises an open task (no result), so after B2 its expected step is the `HELD` sentence with 4 held.
- Replays (`TESTS/e2e/test_org_growth_0a4.py`): section 17, items B-1 and B-2.

## 6. D-E6-3: C, redone and bounded

C1 runs first, before any product change of this batch. C2 is built next and always ships. C3 is built only as C1's evidence selects (6.3).

### 6.1 C1: the reproduction (the first build item; manual; no commit; real kiro-cli 2.33.0 on macOS)

**What it must answer.** In E5's s3 and E6's s3 the scheduler and its run were gone within about a second of the assistant's call returning,
with no `scheduler.exit` and no `run.end` (an uncatchable kill, or TERM then KILL before the shutdown finished). 0a.3's reproduction never
showed that signature (gate discrepancy 1). C1 shows what dies, when, by which signal when it can be seen, and which condition matters.

**Safety (every step).**
- `SB=/tmp/hirearchy-0a4-c1-$(date +%s)`; `WT=/Volumes/workspace/hirearchy/.worktrees/org-growth-0a4`; every kiro-cli call runs with
  `KIRO_HOME=$SB/kiro-home`; every hirearchy command and the MCP server with `HIREARCHY_STATE_DIR=$SB/kiro-state` and the org at `$SB/org`; every
  call's cwd is `$SB`. The org runs get their per-org kiro home under `$SB/kiro-state` (`kiro/_env.py:run_environment`).
- The C1 shell is the build step's own shell. Like the E6 streams' harness, it runs inside a kiro session and inherits that session's variables,
  `KIRO_API_KEY` among them: the streams' kiro-cli signed in by it (`EV6/s3/turn-05.stderr.txt` line 2, `Auth: KIRO_API_KEY env var`), and
  `run_environment` keeps it for every org run (its docstring). The record lists the shell's `KIRO_*` variable names once (names only).
- Nothing under `~/.kiro`, `/Users/aminalizadeh/organization` or `.worktrees/org-growth-0b` is listed, opened, hashed or written. The MCP server
  (and so the scheduler and the org's runs) gets `HOME=$SB/home` and `UV_CACHE_DIR=<the output of uv cache dir>` (uv then runs from the existing
  cache), so the product's stale-skill check reads `$SB/home/.kiro/skills`, never the user's. The org's runs sign in under that `HOME` through the
  inherited `KIRO_API_KEY` (Setup 0 checks it before any model call). The assistant's own kiro-cli keeps the user's `HOME` with the sandbox
  `KIRO_HOME`, as 0a.3's C0 and the streams did. After each call its session record (under `$SB/kiro-home`) is read: a tool call other than
  `tool_load` and the `hirearchy::*` tools stops C1 (warning).
- Environment variables are recorded by **name only**, never by value. The account `whoami` names is never recorded.
- Clean-up after each attempt: kill only the pids C1 learned (the scheduler's pid file, each `run.start`'s `child_pid`/`pgid`, the chat's pid
  and the descendants the sampler saw) and processes whose command line names `$SB`; remove `$SB` after its record is written.
- **Bounds, each a stop condition:** C1 (V0, D-ENV, D-OUT, V1-V5, every attempt and repeat) at most **30** kiro-cli chat calls; C1b at most **6**;
  the C3 step's integration-test runs at most **12** (6.3). Setup 0's `whoami` makes no model call and is not counted. A bound reached before
  V0, D-ENV and (when D-ENV died) D-OUT are decided stops C1; reached later, it only skips the informational variants, which is recorded.
- **Stop conditions (send `warning`, ship C2 only, record the conditions tried):** Setup 0 fails (the owner chooses, below); the profile does
  not validate; no session record under `$SB/kiro-home` (kiro-cli ignored `KIRO_HOME`: never repeat the call); turn 2's `start` starts no
  scheduler (in every run but D-OUT, where the shell starts it); the org's first run never reaches `# kiro: run started` in its run log in 2 V0
  attempts (the org's runs cannot sign in: Setup 5 records whether `KIRO_API_KEY` reached the server); a forbidden tool call; a bound, as above.

**Setup 0, the sign-in preflight (once, before any chat call; no model call).**

```sh
mkdir -p $SB/home $SB/kiro-probe
(cd $SB && HOME=$SB/home KIRO_HOME=$SB/kiro-probe kiro-cli whoami </dev/null)   # must exit 0
rm -rf $SB/kiro-probe
```

The record keeps the exit code and the first output line only if it starts with `Authenticated` (a line that names the account is never written).
At design time (this revision) the probe exited 0 in the workflow's own shell with `Authenticated with API key`, so the default above is
expected to hold. On a non-zero exit, the step sends `warning` before any chat call, with the owner's choice:
- (a) `KIRO_API_KEY` in the MCP server's `env` block (named only in the record; the value is the owner's and is never written), keeping
  `HOME=$SB/home`; or
- (b) the MCP server keeps the user's `HOME`, as the streams and `tests/integration` do. The prompts never name `whoami` or `status`, and a root
  `hirearchy::whoami` or `hirearchy::status` call in a session record becomes a stop condition: those two tools are the only readers of
  `<HOME>/.kiro/skills/hirearchy/SKILL.md` (read-only; `mcp_server/_tools_identity.py` and `_tools_status.py`, through
  `app/wire_mcp_server.py:PackagedInstalledSkill`), and with `HIREARCHY_STATE_DIR` set nothing else these calls run reads `HOME`
  (`kiro/_places.py`). Under (b), declared limit 8 drops "the user's HOME for root's MCP server", and the profile's `env` has no `HOME` key.

The integration test of 6.3 uses the same probe as its skip condition, under the same choice.

**Setup (once per attempt).**
1. `h() { HIREARCHY_STATE_DIR=$SB/kiro-state $WT/.venv/bin/hirearchy "$@"; }`; `h init $SB/org --mission "0a.4 C1 reproduction (throwaway)"
   --model claude-sonnet-5.5`; `h --root $SB/org hire root ceo --role CEO --charter "Throwaway reproduction agent."`;
   `h --root $SB/org task ceo --title "Reproduction" --goal "Write a 300-word note about rivers into ceo/MEMORY.md with the write tool, then
   report done." --acceptance "the note exists" --budget 2`. The org's runs are real kiro-cli runs (claude-sonnet-5.5 at high effort, the floor).
2. The profile `$SB/kiro-home/agents/c1-<epoch>.json`, s3's assistant profile (`EV6/s3/profiles/hirearchy-study-e6-s3-assistant.json`) with
   the paths substituted, every value written out: `mcpServers.hirearchy = {"command": "uv", "args": ["--directory", "<WT>", "run", "hirearchy",
   "mcp"], "env": {"ORG_ROOT": "<SB>/org", "HIREARCHY_STATE_DIR": "<SB>/kiro-state", "HOME": "<SB>/home", "UV_CACHE_DIR": "<uv cache dir>"}}`,
   `"tools": ["*"]`, `"permissions": {"rules":
   [{"capability": "all", "effect": "allow"}]}`, `"resources": ["skill://<WT>/skills/hirearchy/SKILL.md", "skill://.kiro/skills/*/SKILL.md"]`
   (the second is relative to the cwd `$SB` and matches nothing), `"hooks": []`, `"includeMcpJson": false`, `"model": "claude-sonnet-5.5"`.
   `kiro-cli agent validate --path <file>` must accept it.
3. The two calls of the streams' shape (`EV6/s3/turn-05.cmd.txt`):
   - turn 1: `KIRO_HOME=$SB/kiro-home kiro-cli chat --v3 --no-interactive --trust-all-tools --effort high --agent c1-<epoch> "Load the hirearchy
     tools with tool_load, call hirearchy::progress once with its defaults, and reply with its result only."`;
   - turn 2: the same with `--resume` and `"Call hirearchy::progress once with its defaults, then hirearchy::start once with its defaults, then
     reply with the result of start only."`. The call returns seconds after `start`, while the scheduler's first real run is in its start phase
     (s3: 2.25 s after `run.start`). The `progress` call first gives D-OUT a point inside the call to start the scheduler from, with the call's
     shape unchanged.
4. The sampler (a throwaway script under `$SB`, not committed), from turn 2's start until 15 s after its return, every 0.1 s: a UTC-stamped
   `ps -o pid,ppid,pgid,sess,stat,lstart,command` of exactly these processes: the turn-2 chat process and its descendants (re-walked by parent
   pid at each sample), the scheduler (its pid file) and its descendants, and each run (`child_pid` of its `run.start` event). Nothing else of
   the process table is recorded (other processes' command lines can hold the user's prompts). It also follows the org's event files (for
   D-OUT's trigger and the verdicts).
5. Per attempt, `.agents/tasks/c1-reproduction.md` records:
   - the commands; the call's start and return (UTC, ms), exit code, stdout and stderr (stderr carries kiro-cli's own `[INFO]` lines, as
     `EV6/s3/turn-05.stderr.txt` does); the samples; the org's events (`scheduler.start`/`exit`/`signal`, `run.start`/`end`, `tool.call`); the
     session record's path;
   - kiro-cli's own log of the call: the files newer than the call's start under `$SB/kiro-home`, with their shutdown, signal and kill lines
     (such as `kas.server.signal_shutdown`). The record states whether such a file was found; when none was, the log is recorded as missing. It
     is never searched for under `~/.kiro` or elsewhere in the user's `HOME`;
   - **the changed names**: the names whose value in the MCP server's or the scheduler's environment is absent from, or differs from, the C1
     shell's (the sampler reads `ps -E -ww -o command= -p <pid>` of those two processes once, compares the values in memory and writes names
     only; a name inside a value may be listed too, which only makes D-ENV unset one harmless name more). They are split into: the keys of the
     profile's `env` block; `VIRTUAL_ENV` and names starting `UV_`; the M2 refusal list of section 10; and the rest, **D-ENV's names**. Every
     group is recorded, and whether `KIRO_API_KEY` is in the server's environment (yes/no). A name present in the shell with another value (an
     inner `KIRO_SESSION_ID`, for one) is a changed name: comparing names alone would miss it, because the C1 shell already carries its own
     session's `KIRO_*` names;
   - the verdict, by the first class that matches, in this order:
     - **no-run** (invalid: repeated, counted in the bound): no org `run.start` before the return, or the run ended before it;
     - **finished** (invalid: repeated, counted): the scheduler exited with a reason starting `finished`;
     - **died**: the scheduler's pid gone within 5 s of the return;
     - **run-only**: the scheduler alive 5 s after the return and the run gone without a `run.end` with `ok: true`: a signature of its own,
       recorded; it counts as not reproduced in 6.3's first row, and the final message names it;
     - **survived**: the scheduler and the run alive 5 s after the return;
   - for a death: the last sample alive, the first sample gone, the STAT and parent pid just before, and whether `scheduler.exit`,
     `scheduler.signal` (C1b) and `run.end` exist.

   A variant whose attempts are invalid 3 times running is recorded as "could not be set up": for V0 that is "not reproduced" with that reason;
   for D-ENV or D-OUT no row of 6.3 can match on it.

**The runs, one condition varied at a time, in this order.**

| Order | Run | Change from V0 | Valid attempts | Purpose |
|---|---|---|---|---|
| 1 | V0 | none: the streams' conditions (sandbox `KIRO_HOME`, uv-started server, all-tools profile, `--trust-all-tools`, turn 2 with `--resume`, a real org run in its start phase at the return) | up to 3 | **reproduced** when it dies in at least 2 of 3; **not reproduced** when it survives (or is run-only) in 3 of 3, or dies in only 1 of 3 |
| 2 | D-ENV | the server's `"command"` is `/usr/bin/env`, its `"args"` one `-u NAME` per D-ENV name (Setup 5, from V0's attempts) and then `uv --directory <WT> run hirearchy mcp`, so the server and the scheduler lack exactly those names | up to 2; then at most 2 narrowing attempts, one each (half of the names, then half of the half that survived) | mechanism: an inherited marker |
| 3 | D-OUT (only when D-ENV died) | the scheduler is started by the C1 shell, not by the call: as soon as the sampler sees turn 2's server write its `tool.call` line for `progress`, the shell runs `HOME=$SB/home h --root $SB/org start &` (the product's own detached start; the shell's environment lacks D-ENV's names, which D-ENV showed do not matter). Turn 2 still calls `start` once; its reply is the existing `a scheduler is already running for this org (pid N, since ...); call stop() first to restart it` (no new refusal). The attempt is valid only when the pid file names the scheduler the shell's `start` reported and its `run.start`-to-return time is within 3 s of V0's median; otherwise it is repeated (counted) | up to 2 | mechanism: ancestry inside the call's tree |
| 4 | V3 | one call: turn 1 calls `progress`, then `start` (no `--resume`) | up to 2 | informational |
| 5 | V2 | profile `"tools": ["@hirearchy"]` with a permission rule allowing `hirearchy/progress` and `hirearchy/start` only; no `--trust-all-tools` | up to 2 | informational |
| 6 | V1 | the server `"command": "<WT>/.venv/bin/hirearchy", "args": ["mcp"]` (no uv) | up to 2 | informational |
| 7 | V5 | turn 2 calls `progress`, `start`, then `progress(wait_seconds=60)`, then replies (an older scheduler, a run past its start phase) | up to 2 | informational |
| 8 | V4 | the org runs through a stub kiro-cli (`runStarted`, `sleep 60`, `runFinished`) on the server's `PATH` only | up to 2 | informational |
| C3 step | C1b | V0 on the C2 commit (6.2) | up to 3, stopping at the first death | which signal reached the scheduler (`scheduler.signal`), if any |

Orders 2-8 run only when V0 reproduced. A variant "survives" when it survives 2 valid attempts; one death decides "dies". V1-V5 never select a
row of 6.3; one skipped because the bound was reached is recorded as skipped, not a stop. C1b runs as the first act of the C3 step, on the C2
commit; if its 3 attempts all survive, that is recorded and the M5 row cannot match. Every attempt spends real model calls; the bounds are above.

**Outcome.** C1's record ends with one of the rows of 6.3's table and the evidence that selects it. When V0 is not reproduced (or is run-only,
or could not be set up), C1 records the conditions tried (and the ones the sandbox could not give: declared limit 8 of section 16) and the batch
ships C2 alone; the final message says so (D-E6-3: "E7's preflight then checks survival under the streams' conditions").

### 6.2 C2: the `scheduler.signal` event (always shipped)

**The handler** (`SRC/scheduler/_loop.py:HeartbeatLoop.serve`, lines 60-89). Today a SIGTERM only sets a flag; the loop ends after its pass and
its pause, and `release()` then terminates the runs (SIGTERM, 10 s of grace each, SIGKILL; `_reaper.py:93-106`) before it writes
`scheduler.exit`. A KILL inside that grace leaves no record. New:

```python
STOP_SIGNALS = (signal.SIGTERM, signal.SIGHUP)  # recorded at once (scheduler.signal); each ends the loop cleanly, unless SIGHUP came ignored


    def serve(self, until_idle: bool = False, max_runs: int | None = None, until_done: bool = False) -> None:
        s = self._state
        s.mode = "until_done" if until_done else "until_idle" if until_idle else "daemon"
        s.max_runs = max_runs
        self.acquire()
        stopped_by: str | None = None
        ignored = {signal.SIGHUP} if signal.getsignal(signal.SIGHUP) == signal.SIG_IGN else set()  # the scheduler was started with it ignored

        def on_signal(signum: int, _frame: object) -> None:
            nonlocal stopped_by
            name = signal.Signals(signum).name
            action = "ignored" if signum in ignored else "stop"
            try:
                self._session.signalled(name, action, s.runs)  # written now, before any grace: a KILL that follows still leaves this record
            except Exception:  # noqa: BLE001 - the record must never change what the interrupted code does
                pass
            if action == "stop" and stopped_by is None:
                stopped_by = name

        previous = {sig: signal.signal(sig, on_signal) for sig in STOP_SIGNALS}
        try:
            while stopped_by is None:
                ...  # the pass, the exit policy and the pause, unchanged
            else:
                s.exit_reason = f"stopped by {stopped_by}"
        except KeyboardInterrupt:
            ...  # unchanged
        finally:
            try:
                self.release()
            finally:
                for sig, handler in previous.items():
                    signal.signal(sig, handler if handler is not None else signal.SIG_DFL)  # as found (the tests' process, too); None: not set from Python
```

`run_once` installs no handler (unchanged). A second signal is recorded too; the first one names the exit reason.

**The ports** (private, `SRC/scheduler/_ports.py`):
- `SessionEvents.signalled(self, name: str, action: str, running: Sequence[str]) -> None`: "``scheduler.signal``: the scheduler got ``name``
  (``SIGTERM`` or ``SIGHUP``) and does ``action`` (``stop`` or ``ignored``); ``running`` are the runs in flight. Called from the signal handler,
  before any grace period."
- `SchedulerSession.signalled(self, name: str, action: str, runs: RunTable) -> None`. `ClaimedSession.signalled` calls
  `self._events.signalled(name, action, sorted(r.run_id for r in tuple(runs.values())))`.
- `SessionAnnouncer.signalled` (`SRC/scheduler/_events.py`): `self._events.emit("scheduler.signal", signal=name, action=action,
  ppid=os.getppid(), running=list(running))`.
- Fakes (`SRC/scheduler/testing.py`): `RecordingSession.signalled` and `RecordingSessionEvents.signalled` append `"signal"` to the journal and
  record `(name, action, run ids)`; `RecordingSession.fail_signal: Exception | None` makes it raise (to test the guard).

**The event schema** (one line, written by the scheduler process; envelope as every line):

| Key | Type | Value |
|---|---|---|
| `v`, `ts`, `seq`, `proc`, `pid`, `kind`, `actor`, `run`, `trace` | envelope | `proc` `scheduler`, `kind` `scheduler.signal`, `actor` `runtime`, `run` null, `trace` null; `ts` is the time of the signal (the handler writes the line at once) |
| `signal` | str | `SIGTERM` or `SIGHUP` |
| `action` | str | `stop` (the loop ends cleanly after its pass: `scheduler.exit` reason `stopped by SIGTERM` or `stopped by SIGHUP`, if no KILL comes first) or `ignored` (a SIGHUP the scheduler was started with ignored: it goes on) |
| `ppid` | int | the scheduler's parent pid at that moment (1 when re-parented to launchd or init) |
| `running` | list[str] | the run ids in flight (`<agent>@<stamp>`), sorted; `[]` for none |

It is not an error kind (`observability._pure.is_error` is unchanged): a deliberate `hirearchy stop` sends SIGTERM too, and every stop now leaves
this line. `obs events`, `observe`, the trace view and the dashboard show it with their generic line (`scheduler.signal signal=SIGTERM action=stop
ppid=1 running=[...]`); no view changes. The schema is documented in README's event table (exact row in 14, E1) and pinned by the e2e test of
6.5 (keys in order and their types); the golden `events/line_shapes.txt` is not regenerated (its scenario sends no signal).

**SIGHUP.** Today SIGHUP has no handler, so its default action ends the scheduler at once with no record and leaves its runs orphaned. With C2 a
SIGHUP is recorded and ends the loop cleanly like SIGTERM (`stopped by SIGHUP`), unless the scheduler was started with SIGHUP ignored, in which
case it stays ignored and is recorded with `action: ignored` (Deviation 6). C3's branch M5 changes this only if C1's evidence selects it.

**The writer becomes safe to call from a signal handler** (`SRC/telemetry/_pool.py`, `SRC/telemetry/_writer.py`; Deviation 7). The handler
emits on the main thread between two bytecodes, possibly while that thread is inside `FileLineWriter.append` holding the pool's lock. That lock is
a `threading.Lock`: the handler would block on it forever (a hung scheduler). And a re-entrant write in the middle of another line could give
the file's lines out of `seq` order, which `check`'s invariant (e) reports. So:
- `EventWriterPool._lock = threading.RLock()` (the same lock is still shared by the pool and its writers; one thread re-enters, other threads
  still wait);
- `FileLineWriter` keeps a queue and a flag; today's `append` body becomes `_write(...)`:

```python
    def append(self, record: JsonObject, day: str, clock: Clock, retry_after: float, on_fresh: Callable[[], None]) -> None:
        with self._lock:  # re-entrant: a signal handler of the thread that holds it gets in
            self._queue.append((record, day, clock, retry_after, on_fresh))  # one C call: a handler cannot split it
            if self._writing:
                return  # a handler that interrupted a line of this writer: that line's loop writes this one right after it
            while True:
                try:
                    item = self._queue.pop(0)
                except IndexError:
                    return  # nothing left (a handler that came in between may have written the rest itself)
                self._writing = True
                try:
                    self._write(*item)  # numbering, opening and writing, as today
                finally:
                    self._writing = False
```

  A handler that runs while a line is being written queues its line, which follows that line with the next `seq`; a handler that runs between
  two lines writes its own and the queue's. Lines are never interleaved inside one `write()`, `seq` follows the file's order, and nothing waits
  on itself. An `OSError` while writing a queued line propagates to the emit that was writing (counted once as dropped, as today); lines still
  queued are written by the next append.

### 6.3 C3: the detach by the mechanism C1 shows (conditional)

C3's mechanism is chosen **only** by C1's recorded evidence, by the first row that matches; a row whose evidence is not in
`c1-reproduction.md` is not built. `TESTS/e2e/test_scheduler_detach.py` is kept unchanged in every row.

| C1 shows | C3 | Shipped? |
|---|---|---|
| V0 not reproduced (survives or is run-only in 3 of 3, dies in only 1 of 3, or could not be set up) | none | **C3 not shipped; C2 ships alone**; the report and the final message list the conditions tried |
| V0 reproduced, and C1b shows `scheduler.signal` with `signal: SIGHUP` as the first signal the scheduler got, followed by its own `scheduler.exit` `stopped by SIGHUP` (no KILL) | **M5**: SIGHUP is recorded and always ignored | yes, if the integration test passes (its RED and GREEN rule below) |
| V0 reproduced, D-ENV survives | **M2**: the scheduler's environment drops the variables C1 named | yes, if none of those variables is needed by the org's runs (D-ENV's own org run must have completed) and the integration test passes; else not shipped (warning) |
| V0 reproduced, D-ENV dies, D-OUT survives | **M1** (macOS): the scheduler is started through launchd, never a descendant of the call | yes, if the integration test passes |
| V0 reproduced, and none of the rows above | none | **not shipped**: `warning` with the evidence; the design must be redone (0a.3 6.1's stop condition) |

**M5 (SIGHUP).** `SRC/scheduler/_loop.py`: `ignored = {signal.SIGHUP}` always. `scheduler.signal` then says `action: ignored`; SIGTERM keeps
today's clean stop (`hirearchy stop` is unchanged). The M5 commit changes, deliberately, the C2 tests that expect a SIGHUP stop (the
`test_loop.py` stop case under `sighup_default` and the second test of `TESTS/e2e/test_scheduler_signal.py`) to expect `action: ignored` and no
stop, their docstrings naming C1b's evidence.

**M2 (an inherited marker).** `SRC/daemon/_site.py:ScrubbedLaunchEnvironment.variables` (line 41) also pops the names in a new constant
`CALL_MARKERS = (<the names C1 recorded>,)` (names only, from the evidence: D-ENV's names, or the narrowed half that survived alone), as it pops
`ORG_AGENT` and `ORG_REQUIRE_AGENT` today. Test: `SRC/daemon/tests/test_launch_site.py`: the scheduler's environment lacks each name and keeps
every other variable.

**M1 (macOS launchd).** A new private class `SRC/processes/_launchd.py:LaunchdDetachedSpawner(ProcessSpawner)` wraps a `PopenProcessSpawner`
(the fallback): `spawn` delegates; `spawn_detached(argv, cwd, env, log)`:
1. `label = "com.hirearchy.scheduler." + sha256(str(cwd)).hexdigest()[:16]` (one per organization, derived; no stored state);
2. `launchctl remove <label>` (its failure, "no such job", is ignored: `start` already refused while a live scheduler holds the pid file), then
   wait until `launchctl list <label>` exits non-zero, polling every 0.1 s for at most 2 s, because `remove` returns before the job has stopped
   (`man launchctl`). Still listed after 2 s: fall back (step 6) with the reason `an earlier job <label> is still loaded`;
3. `d = tempfile.mkdtemp(prefix="hirearchy-detach-")` (mode `0700`, in the system's temporary directory, outside the organization; removed with
   `shutil.rmtree(d, ignore_errors=True)` in a `finally` of `spawn_detached`). The environment is written as JSON to `d/env.json` (`O_CREAT |
   O_EXCL`, mode `0600`) and is never put on a command line;
4. `launchctl submit -l <label> -o <log> -e <log> -- <sys.executable> -I <processes/_detach.py> --env d/env.json --cwd <cwd> --pid d/pid <log>
   -- <argv...>`. launchd starts the intermediate. With `--env`, the intermediate exits 0 at once when the env file is missing (a launchd
   respawn: `submit` keeps a job alive after a failure, `man launchctl`); otherwise it reads and deletes the file, changes to `cwd`, starts
   `argv` in a session of its own (today's `_detach.py` body), and writes `<pid>\n` to `d/pid`, or `error: <reason>\n` when `argv` cannot be
   started. It exits 0 in each case, so launchd has no failure to restart;
5. wait up to 10 s for a complete line in `d/pid`. A pid: `launchctl remove <label>` (the intermediate has exited; the scheduler is in a session
   of its own), and return the pid. That `remove` runs inside `start`, before the call returns, so the integration test's check 5 s after the
   return also shows that removing the job left the scheduler alive (unverified until then: `man launchctl` does not say);
6. fall back, in every other case: `launchctl` missing, `submit` exiting non-zero, the earlier job still loaded (step 2), `error: <reason>` in
   `d/pid`, or no line within 10 s. Then `launchctl remove <label>` (when a job was submitted), the scheduler log gets the line
   `# --- started without launchd: <reason>` (`launchctl not found`, `launchctl submit exited <code>`, `an earlier job <label> is still loaded`,
   the intermediate's `<reason>`, or `no pid within 10 seconds`), and the fallback's `spawn_detached(argv, cwd, env, log)` runs: today's detach,
   whose own failure raises today's `OSError` text. So M1 adds no new failure of `start` and no refusal: at worst `start` behaves as today. A
   scheduler that a late intermediate starts after the fallback has started one is refused by its own claim (`daemon/_lock.py`, today's `a
   scheduler is already running for this org (pid N)`) and exits, as two concurrent starts do today.
`_detach.py` gains the optional `--env FILE --cwd DIR --pid FILE` arguments before `<log> -- <argv>`; without `--env` it is today's (exit 2 on a
malformed command line). `SRC/app/wire_processes.py` builds `LaunchdDetachedSpawner` when `sys.platform == "darwin"`, else today's spawner.
Linux keeps today's detach: C1 runs on macOS only, so no Linux mechanism rests on evidence (Deviation 9, declared limit 9). The C3 step records
`launchctl list <label>` once, right after a `submit`, in `c1-reproduction.md`. Unit tests (`SRC/processes/tests/test_launchd_spawner.py`, over
a fake `launchctl` script on `PATH` and a fake fallback): each fallback reason and its log line; the wait for `list` to fail before `submit`;
the env file's mode and its absence from every command line; `d` removed in every case; and `_detach.py` with `--env` exits 0 when the file is
missing and writes `error: ...` for an `argv` that cannot start.

**The integration test (every shipped row).** `TESTS/integration/test_scheduler_survives_the_call.py::test_the_scheduler_and_its_run_outlive_the_kiro_cli_call_that_started_them`,
marked `integration` (its directory marks it; `--run-integration` runs it). It is skipped, with a named reason, when `shutil.which("kiro-cli")`
is None or Setup 0's probe (6.1) fails with the server `HOME` the test uses (the module constant `SERVER_HOME = "sandbox"`, `<tmp>/home`; set
to `"user"` only if the owner chose (b) in C1). It runs V0 (6.1 Setup 1-3) in the test's tmp dir, with `KIRO_HOME` and `HIREARCHY_STATE_DIR`
under it and the safety rules of 6.1. Its MCP server is `uv --directory <the checkout the test file is in> run hirearchy mcp`, so a copy of the
file runs that checkout's product. It imports only the standard library and pytest, so it runs unchanged on `18c4ffb`. It does not use the
`real_kiro` fixture (Deviation 13). First the validity checks: no org `run.start` before the return, the run ended before it, or the scheduler
`finished` before the 5 s check gives `pytest.fail("INVALID: <which>")`, which counts as neither RED nor GREEN. Then it asserts: 5 s after
turn 2 returns, the scheduler (pid file) and the run (`child_pid`) are alive (`ps -o stat=`, not empty and not `Z`); within the run's timeout
the run ends with `run.end` `ok: true` and `killed: false`, the task's result is `done`, and `scheduler.exit` says `finished: no open tasks`.
`finally`: kill only the pids it learned.

**Its RED and GREEN proof (the C3 step, by hand; one run is one pytest invocation of the test with `--run-integration`, 2 chat calls; at most 12
runs, invalid ones included):**
- **RED at `18c4ffb`:** `git -C /Volumes/workspace/hirearchy worktree add --detach /tmp/hirearchy-0a4-red-<epoch> 18c4ffb`, `uv sync` there,
  the new test file copied into its `tests/integration/`; 3 valid runs, of which at least 2 fail on the survival assertion (V0's criterion);
  then `git -C /Volumes/workspace/hirearchy worktree remove --force /tmp/hirearchy-0a4-red-<epoch>` (this step's own throwaway checkout,
  outside `.worktrees/`; nothing in it is committed).
- **GREEN:** 3 of 3 valid runs pass on the C3 change in this worktree, before it is committed.
- **Otherwise** (not RED by that rule, not GREEN 3 of 3, or the 12 runs used first): no C3 commit (the C3 changes are discarded with
  `git restore` and its new files deleted), `c1-reproduction.md` records every run, and the step sends `warning` (0a.3 6.1's stop condition:
  the design must be redone). C2 has already shipped.

### 6.4 Zero and empty cases (C2)

| Case | Result |
|---|---|
| no signal | no `scheduler.signal`; exit reasons as today |
| SIGTERM | one record (`action: stop`), the loop ends after its pass, `scheduler.exit` `stopped by SIGTERM` unless a KILL comes first |
| SIGHUP, inherited default | one record (`stop`), `stopped by SIGHUP` |
| SIGHUP, inherited ignored | one record (`ignored`); the loop goes on |
| a second signal | a second record; the reason stays the first signal's |
| no run in flight | `running: []` |
| `run_once` | no handler (unchanged) |
| a signal before `serve` installs its handlers (during the claim, the orphan settling, the recovery) | the default action, no record (declared limit 7) |
| SIGKILL | no record (uncatchable; C2's point is that a TERM before it is recorded) |
| events off (`events: false`) | no record (the switch, as for every event) |
| an unwritable events directory | the record is dropped and counted, as every event |
| the record raises (a bug) | swallowed in the handler; the stop flag is still set |

### 6.5 Tests to write first (C2)

- `SRC/telemetry/tests/test_file_line_writer.py`:
  - `test_a_line_appended_while_another_is_written_follows_it`: on the first append into a new events directory, `on_fresh` (called while the
    day's file is opened, inside the append) appends a second record; the file holds both lines, first then second, `seq` 1 and 2. The outer
    append runs in a daemon thread joined with a 5 s timeout and the test asserts the thread ended: RED today (the second append blocks on the
    lock forever), never a hung suite.
  - `test_a_signal_handler_can_emit_while_the_line_it_interrupted_is_written`: a `SIGUSR1` handler that appends through the same writer; the
    signal is raised from `on_fresh` with `os.kill(os.getpid(), signal.SIGUSR1)`; a `signal.setitimer(signal.ITIMER_REAL, 2.0)` guard whose
    `SIGALRM` handler raises `TimeoutError` breaks a deadlock (a lock acquire is interrupted by a signal on POSIX), so the RED run fails instead
    of hanging; both handlers and the timer are restored in `finally`. After the fix: two lines, in order, `seq` 1 and 2.
- `SRC/telemetry/tests/test_event_writer_pool.py`: the pool's lock lets the thread that holds it in again (a writer created inside a held lock).
- `SRC/scheduler/tests/test_loop.py` (over `RecordingSession`, `signal.raise_signal` from a phase or the pacing, as `test_sigterm_ends_the_loop_
  cleanly_after_the_pass_it_arrives_in` does today):
  - SIGTERM raised in phase `a` is recorded before phase `b` runs (`journal == ["open", "a", "signal", "b", "pause", "close"]`), reason
    `stopped by SIGTERM`, the record `("SIGTERM", "stop", [])`;
  - SIGHUP stops the loop the same way (`stopped by SIGHUP`);
  - with SIGHUP set to `SIG_IGN` before `serve`, a SIGHUP is recorded `ignored` and the loop ends by its exit policy;
  - the SIGHUP disposition is set by a fixture, never inherited from the runner: `sighup_default` sets `signal.signal(signal.SIGHUP,
    signal.SIG_DFL)` for the stop cases, `sighup_ignored` sets `SIG_IGN` for the ignored case, and each restores the disposition it found in
    its teardown (a runner under `nohup`, or a background `check.sh`, starts with SIGHUP ignored; `SIG_IGN` survives `fork` and `exec`);
  - two signals give two records and the first one's reason;
  - a run in the table is named in `running`;
  - `serve` leaves the SIGTERM and SIGHUP handlers it found;
  - a record that raises (`fail_signal`) changes nothing: the loop still stops.
- `SRC/scheduler/tests/test_session.py`: `ClaimedSession.signalled` forwards the run ids, sorted.
- `SRC/scheduler/tests/test_events.py`: `SessionAnnouncer.signalled` emits `scheduler.signal` with `signal`, `action`, `ppid ==
  os.getppid()` and `running`, `proc` `scheduler`, `actor` `runtime`.
- `TESTS/e2e/test_scheduler_signal.py` (new; not `integration`: no real kiro; about 5 s; the structure of `test_scheduler_detach.py`): a real
  scheduler process (`Org(...).runtime.scheduler_control.start(None, True)` from a parent process) whose stub run ignores SIGTERM (`trap ''
  TERM` in the stub, `sleep 30`); once `run.start` is in the events: SIGTERM to the scheduler, 0.2 s later SIGKILL to it (E5 s3's escalation,
  inside the run's 10 s grace). Asserts: a `scheduler.signal` line exists with the keys `v, ts, seq, proc, pid, kind, actor, run, trace, signal,
  action, ppid, running` in that order and types `int, str, int, str, int, str, str, NoneType, NoneType, str, str, int, list`, `signal ==
  "SIGTERM"`, `action == "stop"`, `running == [<the run id>]`, its `ts` before the KILL; and no `scheduler.exit`. A second test sends SIGHUP
  alone to a scheduler whose stub run dies on TERM: `scheduler.signal` (`SIGHUP`, `stop`), then `scheduler.exit` `stopped by SIGHUP`. A third
  test starts the scheduler with SIGHUP ignored, sends SIGHUP, and expects `scheduler.signal` with `action: ignored`, the scheduler still alive
  1 s later and no `scheduler.exit` until the test's SIGTERM (`stopped by SIGTERM`). The starter script (the parent process that calls
  `scheduler_control.start`) sets `signal.signal(signal.SIGHUP, signal.SIG_DFL)` before the call for the first two tests and `SIG_IGN` for the
  third, so the scheduler's disposition never depends on the runner's (it is inherited through `_detach.py`).
  `finally`: kill the run's group and the scheduler (only pids it learned). RED today (no such event).

## 7. D-E6-5: the small items

### 7.1 F-E6-6: the keep-as-is accept needs a delivered version the user saw

SKILL.md line 100, by replacing text (exact line in section 8). In s3 the assistant recorded Lena's "Keep it as it is." (an answer to a question
about one section, #45 and #53) as her accept on the whole version, in the turn that copied it, before she had seen it. The line now records the
accept only when the user keeps a delivered version as it is after seeing it, and says that a "keep it" about one part of it, or one given
before they saw it, is no accept. L-ASIS (s2) is still recorded: Lena had the memo and kept it as it was. 0b counts these as human verdicts (gate
4 item 2), so its counts move with this line. Test first: the new needles in `SRC/skill/tests/test_skill_org_growth.py` (section 13, rule S).

### 7.2 F-E6-7: delegations without `revises` inherit the tier

**Investigation.** The tier (`source`) travels into rework delegations only: `dispatch/_sender.py:38` returns `inherited` for an agent's task
only when it `revises`, and `RuleTaskAssigner.delegate` (`dispatch/_assigner.py:81`) asks `ReworkContext.fields_for` only for a rework. The
record of why: e4-decision D-E4-4 says "The tier travels into rework delegations", and 0a.2 D1 restates it ("only rework delegations carry it, as
decided"). Neither gives a reason for fresh delegations to carry no tier: E4's failure was in reworks, so the decision named reworks. The tier's
purpose (0a.2 7.6) is "the tier of the work the agent is doing in that case", shown in the receiving agent's message header (`source: human` /
`source: relayed`, `kernel/_message.py:194`) and read by every later count of delegation tiers (0b; gate 4 item 2, "The tier (F-E6-7)"). A
writer task the lead sends while working on root's human rework (s1 b5b1, s2 40f3, s3 9a5b's `...-lead-395b`) or root's relayed rework (s1's
window writer task `...-lead-dd34`) is the same work. **Today's behaviour is therefore a gap, not a design choice, and it is fixed.**

**The change.**
- `SRC/dispatch/api.py:ReworkContext` gains `work_tier(self, actor: str) -> str | None`: "The tier (``source``) of the work ``actor`` does now,
  for a task it sends without ``revises``: the ``source`` of its newest open received task in the trace its next message is stamped with (the
  one trace of its open received tasks, else the one trace of its run batch). None for root, without such a trace or task, and for a task
  without a tier."
- `SRC/services/_rework.py:ServiceReworkContext.work_tier`: `None` for `ROOT`; else `trace = self._open_trace(actor) or self._batch_trace(actor)`
  and `self._tier(actor, trace) if trace else None`. `_open_trace(actor)` mirrors `traces/_lookup.py:MailboxTraceLookup.open_task_traces` and
  its `open-task` rule (the traces of the received tasks with no result or a `blocked` latest result; their one trace when they have exactly one
  and none is missing; else None). `traces` is not a dependency of `services`, so the rule is mirrored, as 0a.3 7.3 mirrored the batch rule
  (Deviation 10). `fields_for` is unchanged.
- `SRC/dispatch/_assigner.py:RuleTaskAssigner.delegate`: `inherited = _tier_of(fields) if revises else (self._work_tier(actor) if actor !=
  ROOT else None)`, where `_work_tier` calls `self._rework.work_tier(actor)` and gives None on `OrgError` or `OSError` (the delegation is sent
  as today; the tier is advice, and a fresh delegation that worked before must not fail on it).
- `SRC/dispatch/_sender.py:provenance_source`: line 38 drops `revises` from the condition: `if source is None and actor != ROOT and type ==
  "task" and inherited in SOURCES: return inherited`. `inherited` still comes only from `delegate`, never from a tool argument; an agent's own
  `source` is still refused (S1). The docstring says "a task of an agent carries ``inherited``".
- Fakes (`SRC/dispatch/testing.py`): `NoReworkContext.work_tier` returns None; `FixedReworkContext(fields, tiers: Mapping[str, str] | None =
  None)` answers `(tiers or {}).get(actor)`.

**Zero cases.** Root: never a tier. An agent with no open received task: None. Open tasks of two traces: the batch's one trace, else None. An
open task without a tier: None. A rework (`revises`): unchanged (0a.2, 0a.3). A read error: no tier.

**Tests first.** `SRC/dispatch/tests/test_contract_rework_context.py`: `work_tier` is None for root, is None or `human`/`relayed`, and is the
same every time (every implementation). `SRC/services/tests/test_service_rework_context.py`: the lead holding root's open human rework in one
trace gives `human`; a relayed one `relayed`; two open traces and a batch of one gives the batch's; two and none gives None; a closed task gives
None. `SRC/dispatch/tests/test_rule_task_assigner.py`: an agent's fresh delegation passes `inherited=<work_tier>`; root's passes None; a raising
context passes None. `SRC/dispatch/tests/test_rule_message_sender.py`: an agent's fresh task with `inherited="human"` carries it (rule T, 13).
Replays: section 17, items F-1 and F-2.

### 7.3 The SKILL.md spend ask

SKILL.md line 72, by replacing text (section 8): "before a rework that would take the case past the approved per-request budget, ask the user,
with the number, in the same message as the question or yes/no item that needs the rework (never a turn later)". s2 lost 2 turns asking the spend
a turn after the question (T4/T5) and after the item (T7/T8); s1 did both in one message (T6), which clause 2 accepts (a spend question is no item,
D2). No line is freed and every tested needle stays, so the item ships. Test first: the new needle in `SRC/skill/tests/test_skill_org_growth.py`.

## 8. SKILL.md and ROOT_INSTRUCTIONS

Three lines change, each by replacing text inside the line, so the file stays at **125 lines**. `ROOT_INSTRUCTIONS`
(`SRC/mcp_server/_instructions.py`) is not edited: its length at the reference path is unchanged and under the 2 700 cap.

**Line 72** (section 4, the spend ask; 7.3). Today:

```
  the approved per-request budget, ask the user, with the number. A rework needs about 2 runs per delegation it requires + 1. The
```

New:

```
  the approved per-request budget, ask the user, with the number, in the same message as the question or yes/no item that needs the rework (never a turn later). A rework needs about 2 runs per delegation it requires + 1. The
```

**Line 92** (section 5, item 3; A2's notes, 4.3). Today:

```
3. A done or blocked report's "Questions for the client:" (ambiguous items; `progress` flags them and withholds the path): ask them in plain words, with any question from item 2, in ONE
```

New:

```
3. A done or blocked report's "Questions for the client:" (ambiguous items; `progress` flags them and withholds the path; the ones it lists as notes, with no criterion, you only pass on with the delivery): ask the others in plain words, with any question from item 2, in ONE
```

**Line 100** (section 5, item 6; F-E6-6, 7.1). Today:

```
   ("keep it" / "what's wrong"); when they keep the version they have as it is ("I'll take it as it is"), record that accept on its task, `source="human"`, with their words, also after a reject; "deliver as is" or "I'll read it myself" is not an accept: ask, or record nothing yet. A known unmet
```

New:

```
   ("keep it" / "what's wrong"); when they keep a delivered version as it is after seeing it ("I'll take it as it is"), record that accept on its task, `source="human"`, with their words, also after a reject; a "keep it" about one part of it, or before they saw it, is no accept; "deliver as is" or "I'll read it myself" is not an accept: ask, or record nothing yet. A known unmet
```

Needles (matched on the flattened, lower-cased text, so line breaks do not matter):
- kept (each checked against the new text): `per-request budget, ask the user, with the number` (`test_round_g_assistant.py`), `a rework needs
  about 2 runs per delegation it requires + 1`, `ask the user once, with that number` (`test_round_f_guidance.py`), `ask at the first budget
  request`, `never wait until the reserve` (`test_finish_rules.py`), `"questions for the client:"`, `with any question from item 2, in one
  message before you deliver`, `` `progress` flags them ``, `withholds the path`, `copy nothing until they are answered`, `"keep it" / "what's
  wrong"`, `with their words, also after a reject`, `"deliver as is" or "i'll read it myself" is not an accept: ask, or record nothing yet`, and
  the order needle `record\n   `feedback(` of `test_skill_services.py` (lines 98-99, untouched);
- replaced, deliberately: `when they keep the version they have as it is ("i'll take it as it is"), record that accept on its task`
  (`test_skill_org_growth.py::test_the_skill_records_the_users_keep_as_is_as_their_accept_on_its_task`) becomes `when they keep a delivered
  version as it is after seeing it ("i'll take it as it is"), record that accept on its task`; the test's docstring names F-E6-6;
- new: `a "keep it" about one part of it, or before they saw it, is no accept`, `in the same message as the question or yes/no item that needs
  the rework`, `the ones it lists as notes, with no criterion, you only pass on with the delivery): ask the others in plain words`. Line 92's
  "ask them" becomes "ask the others" (the questions, not the notes the new parenthetical just named); no tested needle contains `ask them` or
  `in plain words` (`grep -rn` over `src/hirearchy/*/tests` and `tests` at `fe0c9fd`).

The installed copy under `~/.kiro/skills/` is never touched by this batch; `whoami`/`status` will show the stale-skill note to a user whose
installed copy is older, as for every SKILL.md change (E7's harness installs the skill it pins).

## 9. Error handling

| Operation | Failure | Recoverable? | Caller receives | Logged |
|---|---|---|---|---|
| `client_questions`, `client_items` | none (any text is parsed) | n/a | the items (possibly none) | none |
| `progress` line, `open_client_items` | root's sent box or a mailbox cannot be read | as today | the error propagates as today (unchanged code path) | as today |
| relayed `rework_step` | the revised result cannot be read | yes | `""` through the MCP `_step` and the CLI `_step` (`OrgError`/`OSError`), as today | none |
| human `rework_step` (`_top_up`, `user_held`) | the case, the contract or a run log directory cannot be read | yes | `""` (the request is already sent and committed), as today | the `tool.call`/`cli.command` event as today |
| `CaseAllowance.left` (unchanged) | as today | yes | the contract's budget (0a.3) | none |
| the signal handler's record | the event sink fails (directory unwritable, disk full) | yes | the line is dropped and counted (`FsEventSink` never raises) | stderr, once per process (today's drop warning) |
| the signal handler's record | a bug raises in `signalled` | yes | swallowed in the handler; the stop flag is still set; the interrupted code goes on | none |
| a line queued by a handler | `OSError` when the writer writes it | yes | counted as dropped by the emit that was writing; lines still queued are written by the next append | stderr, once per process |
| `delegate` (agent, no `revises`) | `work_tier` cannot read a mailbox | yes | the delegation is sent without a tier (as today) | none |
| C1 (manual) | Setup 0's probe fails | n/a | the step sends `warning` before any chat call, with the owner's choice (a) or (b) of 6.1 | `.agents/tasks/c1-reproduction.md` (exit code only) |
| C1 (manual) | another stop condition of 6.1, or a bound reached before the mechanism-selecting variants are decided | n/a | the step sends `warning` and ships C2 only | `.agents/tasks/c1-reproduction.md` |
| C1 (manual) | an invalid attempt (no-run, finished) | yes | the attempt is repeated, counted in the bound; 3 running: "could not be set up" | `.agents/tasks/c1-reproduction.md` |
| C3 M1 `spawn_detached` | `launchctl` missing, `submit` exits non-zero, the earlier job still loaded after 2 s, the intermediate reports `error: <reason>`, or no pid within 10 s | yes | today's detach (`PopenProcessSpawner.spawn_detached`) runs; only its own failure raises today's `OSError` | the line `# --- started without launchd: <reason>` in `scheduler.log` |
| C3 M1 intermediate | its `--env` file is missing (a launchd respawn) | yes | exits 0, starts nothing | none |
| C3 M2 | a name C1 recorded is one the org's runs need | n/a (build time) | M2 is not built; the C3 step sends `warning` | `c1-reproduction.md` |
| C3's integration test (the C3 step) | not RED at `18c4ffb` (fewer than 2 of 3 valid runs fail), not GREEN 3 of 3, or 12 runs used | n/a (build time) | no C3 commit (changes discarded); `warning`: the design must be redone; C2 stays shipped | `c1-reproduction.md`, every run |
| the integration test | no kiro-cli, or Setup 0's probe fails | n/a | skipped with the reason | test output |
| the integration test | no run in flight at the return, or the scheduler finished first | n/a | `pytest.fail("INVALID: ...")`: neither RED nor GREEN | test output |
| the replays | an evidence file is missing | fatal for the test | `pytest.fail` naming it (never a skip) | test output |

## 10. Validation of external inputs

- **Result bodies** (written by the lead, untrusted): any text. The parser's rules decide the items; an item is shown only through `clip_line`
  (one line, at most 160 characters), at most 5 of them, the rest counted; nothing in an item is executed or used as a path. The criterion id is
  matched as text (`\bC[0-9]+\b`, case-sensitive) and never looked up in the contract: a lead that tags a note with an id makes it a question
  (stricter, never hidden); a lead that leaves an id out makes a real question a note (A2's cost, declared limit 2).
- **Signals:** only SIGTERM and SIGHUP get the handler; the action is derived from the disposition the scheduler was started with.
- **`user_held`, `relayed_to_user`, `open_tasks`:** derived per call from the mailboxes and run logs; no input is stored.
- **`work_tier`:** derived from the agent's own boxes (received, sent, inflight); never from a tool argument; an agent's own `source` is still
  refused (S1).
- **C1:** environment variables are recorded by name only; the profile's values are written out (no shell expansion inside the file); the
  prompts are fixed texts.
- **M2's names:** each must match `[A-Z_][A-Z0-9_]*` and must not be one of `PATH`, `HOME`, `KIRO_API_KEY`, `KIRO_HOME`, `ORG_ROOT`,
  `HIREARCHY_STATE_DIR`, `PYTHONUNBUFFERED` (the C3 step does not build M2 otherwise).
- **M1's files:** they live in a private `tempfile.mkdtemp` directory (mode `0700`, outside the organization, removed in a `finally`); the env
  file is created with `O_CREAT | O_EXCL` and mode `0600`, read and deleted by the intermediate before it starts the scheduler; `_detach.py`'s
  `--env`, `--cwd` and `--pid` are validated (exit 2 on a malformed command line without `--env`, as today; with `--env`, every outcome exits 0
  and is reported in the pid file).
- **D-ENV's names (C1):** the changed names of 6.1 Setup 5 less the profile's `env` keys, `VIRTUAL_ENV`, names starting `UV_` and the M2 refusal
  list above; each must match `[A-Z_][A-Z0-9_]*` (anything else is dropped and recorded as dropped).
- **The E6 kit:** `cut` must be a 21-character stamp; a missing evidence file fails the test.

## 11. Invariants and their owners

| # | Invariant | Owner | Why there |
|---|---|---|---|
| I1 | One parser and one split decide what is a question for the client: `kernel.client_items`; no product module outside `kernel` calls `client_questions` | `kernel`; pinned by `TESTS/architecture/test_client_items_single_reader.py` | the brief: "one function, used everywhere" |
| I2 | Every criterion-tagged text of the block is a question: A1 drops no tail that names an id, and the split is exhaustive and disjoint (A1 and A2 never hide a criterion-tagged question) | `kernel.client_questions` and `kernel.client_items`; the tests of 4.7 and a property test | clause 3's guarantee rests on it |
| I3 | Only questions flag a result and withhold a path, in `progress` and in the deliverable checks | `reflection.open_client_items`, `questions_open` | one settlement rule for both readers |
| I4 | Questions and notes are settled by the same rule | `reflection.open_client_items` | a settled result shows neither |
| I5 | `user_spend`, `user_committed` and the approval ceiling read the same user returns | `reflection` (`_user_back`; `_spend`'s `to_user`) | 0b reuses `user_spend` and `user_approved` |
| I6 | A default hand-down of `left` (`left >= 1`) never includes runs the team holds and never raises the approval; with nothing left, the 1-run floor raises it by 1 | `services._request` (unchanged) with `reflection` | 0a.3 I4 and limit 1; limit 6 here |
| I7 | `user_committed` is at least the user's charged runs, whatever the attribution | `reflection.api` | no run is credited to the user that they did not have |
| I8 | `case_spend` and an agent client's case total are unchanged | `reflection` | 0a.3 I1 and I6 |
| I9 | `scheduler.signal` is written before `release()` terminates the runs | `scheduler._loop.HeartbeatLoop` | C2's purpose: a TERM then KILL leaves a record |
| I10 | An event emitted from a signal handler never waits on itself and keeps `seq` in file order | `telemetry._writer`, `telemetry._pool` | `check` invariant (e); a hung scheduler |
| I11 | A delegation's tier comes from the runtime's mailboxes, never from the agent | `services._rework` (facts), `dispatch.provenance_source` (stamp) | 0a.2 7.6, 0a.3 I11 |
| I12 | C3's mechanism is the one C1's recorded evidence selects | the plan's C3 step; checked by the final validator against `c1-reproduction.md` | D-E6-3 |
| I13 | No new refusal, and no new failure of an existing call (M1 falls back to today's detach in every case it cannot finish) | every surface | the brief; the review's check 2 |

## 12. Golden impact

Expected regenerations: **0**. No golden pins a client-question text, a top-up text or SKILL.md; no MCP tool docstring changes; the events golden's
scenario sends no signal; the message shapes keep `source: NoneType` (the golden org's `ceo` works on root's fresh task, which carries no tier, so
its delegation inherits none). Must stay byte-identical (a commit stops until a diff is explained, and a regeneration is deliberate:
`HIREARCHY_UPDATE_GOLDEN=1 uv run pytest tests/golden -k <test>`, the diff reviewed, the file and the count named in the commit body):
everything under `TESTS/golden/expected/` (`events/line_shapes.txt`, `mcp/surface_*.txt`, `cli/*`, `plans/*`, `prompts/*`, `messages/*`,
`kiro/*`, `charters/*`, `files/*`), the colocated expected files (`SRC/progress/tests/expected/`, `SRC/reflection/tests/expected/`,
`SRC/blueprint/tests/golden/`, `SRC/observability/tests/expected/`) and `TESTS/testkit/expected_dash/`.

## 13. Test-site rules (existing tests the changes touch)

- **Rule A (A2).** Sites: `grep -rn "Questions for the client" src/hirearchy/*/tests tests/e2e tests/meta tests/testkit` and `grep -rn
  "questions_open\|client_questions" src/hirearchy/*/tests`. A fixture whose items name no criterion id, in a test that asserts the question path
  (the count, the flag, the withheld path, the `REWORK` listing, `questions_open`), gets ids on its items (`C1: Keep Marta's row?`, `C2: Which
  Friday?`) so that it keeps testing the question path; its docstring names D-E6-1. All of these fixtures change in commit A2 (the commit that
  makes `questions_open` count only id-naming items), `SRC/progress/tests/test_lines.py` included, so no commit leaves a red suite; A2's TARGETS
  include `src/hirearchy/progress/tests`. The notes path is tested by the new tests of 4.7. Sites at
  `fe0c9fd`: `SRC/progress/tests/test_lines.py` (`QUESTIONS` and the inline one-question body), `SRC/reflection/tests/test_steps.py` (the
  `deliver_asking` callers), `SRC/reflection/tests/test_pure_functions.py` (`ASKED` and the inline body), `SRC/reflection/tests/
  test_deliverable_checks.py` (the callers of its `questions` helper argument). Not affected: `TESTS/e2e/test_org_growth_0a.py`
  (`AMBIGUOUS_MARTA` names C5), `TESTS/e2e/test_org_growth_0a2.py` (E4's fa63 and 96e9 name C4), `TESTS/meta/test_e4_replay_kit.py` (the block's
  presence only), `SRC/mcp_server/tests/test_tools_services.py` (a fake step's text), `SRC/kernel/tests/test_client_questions.py` (A1 adds tests,
  none changes).
- **Rule B (B).** The existing `TOPUP` pins (`grep -rn "Ask the user now\|Nothing else is left" src tests` at `fe0c9fd`):
  - `SRC/reflection/tests/test_steps.py` (the top-up tests), `SRC/mcp_server/tests/test_service_tools.py` (the two top-up tests) and
    `SRC/cli/tests/test_service_commands.py` (the CLI top-up test) revise a task with a `done` result (`_support.deliver` and
    `testkit/services_world.deliver` report `done`), so `user_held` is 0 and they stay byte-identical; `SRC/cli/tests/test_commands_services.py`
    pins a fake step's text and is not affected.
  - `SRC/app/tests/test_wire_cli.py::test_the_request_command_prints_the_step_of_the_runtime` revises an **open** task (`first` has no result;
    its comment: "4 runs handed down, none used yet: all still held"). After B2: committed 5, approved 5, spare 0, `user_held` = 5 - 0 - 1 = 4,
    ask = 5 - 1 - 0 - 4 = 0, so the step is the `HELD` sentence alone. Its two assertions after the CLI call change, deliberately, to
    `assert "budget 1)" in out and f"The team still holds 4 of the user's runs for {first.id}; the rework can use them." in out` and
    `assert "This rework has" not in out and "Ask the user now" not in out`,
    and its docstring names D-E6-2: "the CLI's end-to-end case of B's second part: the team still holds the 4 runs of the open request". It is in
    B2's TARGETS.
  - The coder re-runs the grep at B2 and states the result in the commit body; any other pin whose revised task is open is changed the same
    way.
- **Rule T (F-E6-7).** `SRC/dispatch/tests/test_rule_message_sender.py::test_inherited_outside_a_rework_task_is_ignored`: its first parameter
  (`{"type": "task"}`, a fresh task) moves to a new test `test_an_agents_fresh_task_carries_the_inherited_tier`; the four others (a note, a
  result, `"garbage"`, None) stay, and the test is renamed `test_inherited_outside_a_task_is_ignored`. `test_rule_task_assigner.py`'s root
  delegation (`"inherited": None`) and its rework cases stay. Test-local `ReworkContext`s subclass the fakes (`Spy(FixedReworkContext)` in
  `test_contract_task_assigner.py`) and inherit `work_tier`; the dispatch worlds' default context (`NoReworkContext`) answers None, so every
  existing fresh delegation in those worlds stays unstamped.
- **Rule S (SKILL.md).** The one replaced needle of section 8; no other needle changes.
- No assertion is weakened; each changed expectation names the decision it follows in its docstring.

## 14. Commit plan and test policy

Conventional commits, one logical change each, a failing test first (R11), `count.txt` raised where tests are added. Per commit, FAST under
`test-policy.md` rule 2 (`cd /Volumes/workspace/hirearchy/.worktrees/org-growth-0a4 && UV_LINK_MODE=copy uv run pytest -q <TARGETS> tests/golden
tests/architecture --deselect tests/architecture/test_static_checks.py`, plus `src/hirearchy/app/tests` when the commit touches `app/`, a
Protocol in an `api.py` or the wiring, then `UV_LINK_MODE=copy uv run python scripts/static_checks.py all`). At each FEAT's end, ONE SCOPED run:
the union of its TARGETS plus `tests/e2e tests/golden tests/architecture src/hirearchy/app/tests`. At each fix pass of the code-review loop: ONE
SCOPED union run of the touched commits' TARGETS plus `tests/e2e` (and `tests/golden tests/architecture`), then `static_checks.py all`. No full
pytest and no `scripts/check.sh` during development; `UV_LINK_MODE=copy bash scripts/check.sh` runs once, in the final validation, after the
rebase onto `main`. A known flaky test (`given_queries-narrow-2-workflows`, the 2.5 s `READINESS_TIMEOUT`) is retried once, file only, and
noted. The integration test of C3 is never in these runs (it is skipped without `--run-integration`); the C3 step runs it by hand, RED at
`18c4ffb` (3 valid runs, at least 2 failing) and GREEN on the C3 change (3 of 3), and records every run (6.3).

| # | Commit | TARGETS |
|---|---|---|
| C1 | the reproduction of 6.1 (no commit; `.agents/tasks/c1-reproduction.md`), **first** | - |
| T0 | `test(testkit): the E6 replay kit` (`tests/testkit/e6_replay.py`, `e5_replay.materialize`'s keyword-only `evidence` and `service`, `tests/meta/test_e6_replay_kit.py`; 17.1). Test-only, before A1, so B's and F's replays do not depend on A's commits (the owner may override A2) | `tests/meta/test_e6_replay_kit.py tests/meta/test_e5_replay_kit.py tests/e2e/test_org_growth_0a3.py` |
| A1 | `fix(kernel): a heading's tail, or a parenthesized remark, is no question for the client unless it names a criterion id` | `src/hirearchy/kernel/tests` |
| A2 | `feat(kernel,reflection): only items that name a criterion id are questions for the client; the others are notes` (`ClientItems`, `client_items`, `open_client_items`, `questions_open`, `items_listing`, the relayed rework step; every Rule A fixture, 13) | `src/hirearchy/kernel/tests src/hirearchy/reflection/tests src/hirearchy/progress/tests src/hirearchy/mcp_server/tests` |
| A3 | `feat(progress): the task line lists the notes for the client and withholds nothing for them` (+ the architecture test, replays A-1 to A-5) | `src/hirearchy/progress/tests src/hirearchy/reflection/tests tests/architecture tests/e2e/test_org_growth_0a4.py` |
| A4 | `docs(skill): notes for the client are passed on with the delivery` (line 92) | `src/hirearchy/skill/tests src/hirearchy/blueprint/tests/test_round_f_guidance.py src/hirearchy/blueprint/tests/test_round_g_assistant.py` |
| B1 | `fix(reflection): a relayed result's return beyond what its task still had goes back to the user's side` (+ replay B-2) | `src/hirearchy/reflection/tests src/hirearchy/progress/tests tests/e2e/test_org_growth_0a4.py tests/e2e/test_org_growth_0a3.py` |
| B2 | `fix(reflection): a rework of a request that is still open counts the runs the team holds for it` (+ replay B-1; the `test_wire_cli.py` pin, 13 Rule B) | `src/hirearchy/reflection/tests src/hirearchy/mcp_server/tests src/hirearchy/cli/tests src/hirearchy/app/tests/test_wire_cli.py tests/e2e/test_org_growth_0a4.py` |
| C2a | `fix(telemetry): an event a signal handler emits while a line is written follows that line` | `src/hirearchy/telemetry/tests` |
| C2b | `feat(scheduler): SIGTERM and SIGHUP are recorded at once as scheduler.signal` | `src/hirearchy/scheduler/tests tests/e2e/test_scheduler_signal.py tests/e2e/test_scheduler_detach.py` |
| C1b | V0 on C2b (no commit; `c1-reproduction.md`) | - |
| C3 | conditional (6.3): M5 `fix(scheduler): the scheduler ignores SIGHUP and records it`; M2 `fix(daemon): the scheduler's environment drops the call's marker variables`; M1 `fix(processes,app): on macOS the scheduler is started through launchd`; each with the integration test; or no commit | M5 `src/hirearchy/scheduler/tests`; M2 `src/hirearchy/daemon/tests` (`test_launch_site.py` among them); M1 `src/hirearchy/processes/tests src/hirearchy/daemon/tests src/hirearchy/app/tests`; each plus `tests/e2e/test_scheduler_detach.py tests/e2e/test_scheduler_signal.py` |
| D1 | `fix(dispatch,services): an agent's delegation without revises inherits the tier of its work` (+ replays F-1, F-2) | `src/hirearchy/dispatch/tests src/hirearchy/services/tests src/hirearchy/app/tests tests/e2e/test_org_growth_0a4.py` |
| D2 | `docs(skill): a keep-as-is accept needs a delivered version the user saw` (line 100) | `src/hirearchy/skill/tests src/hirearchy/blueprint/tests/test_round_f_guidance.py` |
| D3 | `docs(skill): a rework's spend is asked with the question or item that needs it` (line 72) | `src/hirearchy/skill/tests src/hirearchy/blueprint/tests/test_round_f_guidance.py src/hirearchy/blueprint/tests/test_round_g_assistant.py` |
| E1 | `docs: README and ARCHITECTURE for phase 0a.4` | `src/hirearchy/skill/tests tests/architecture src/hirearchy/blueprint/tests/test_round_g_assistant.py src/hirearchy/blueprint/tests/test_round_f_guidance.py tests/e2e/test_round7.py` |

FEATs: C1 (alone, first); A (T0, A1-A4); B (B1-B2); C (C2a, C2b, C1b, C3); D (D1-D3, E1). E1 adds nothing to README's `## Services and
reflection` (97 lines today, under `test_round_g_assistant.py`'s cap of fewer than 98). E1's README gains `## Org growth: phase 0a.4` after the
0a.3 section, and the event table row (under `## Observability`) after `scheduler.start` / `scheduler.exit`:

```
| `scheduler.signal` | the scheduler got SIGTERM or SIGHUP, written by its handler at once, before the runs' grace period, so a TERM that a KILL follows still leaves it: `signal`, `action` (`stop`; `ignored` for a SIGHUP the scheduler was started with ignored), `ppid` (its parent pid then), `running` (run ids) |
```

ARCHITECTURE gains the facts of this batch where the 0a.3 ones are: 3.1 (`client_items`, `ClientItems`), 3.20 (`ReworkContext.work_tier`;
`provenance_source` for every agent task), 3.22 (`open_client_items`, `user_held`, `items_listing`, `Case.relayed_to_user`, `Case.open_tasks`),
3.7 (the re-entrant writer) and the scheduler paragraph (`SessionEvents`/`SchedulerSession.signalled`; `scheduler.signal`).

Sizes (production lines, estimates): A about 75, B about 50, C2 about 70, C3 5 (M5), 10 (M2) or about 150 (M1), D about 40. Testability: unit
(the parser and the split, the pure functions, the share and the held runs over fs worlds with run logs and results, the steps, the loop over
`RecordingSession` with `signal.raise_signal`, the writer with a re-entrant `on_fresh` and a real `SIGUSR1`, the tier over the memory world);
contract suites (`ReworkContext`, `ServiceSteps`, the telemetry writer's); end to end (the E6 replays, the scheduler's TERM-then-KILL record, the
tree-kill test kept); manual and `integration` only (C1, the C3 test with real kiro-cli).

## 15. Deviations from e6-decision.md, e6-gate.md and the brief, with reasons

1. **A1's two rules apply only to a tail that names no criterion id.** The decision drops a parenthesized tail, and a tail before a list,
   without condition. A tail that names an id (`(C3: keep Marta's row?)` with no list; `C4: should non-actions be excluded?` before a list of
   notes) would then be dropped, and with A2 nothing would flag the result: a criterion-tagged question hidden (the brief's check 3). So a tail
   that names an id is always an item. The cost is stricter, never hidden: a scope label such as `(C4-C6)` before a list counts as one more
   question (declared limit 1). E5 and E6 had no marker tail naming an id before a list, and 762f's tail names no id, so E6's effect is unchanged
   (4.8). The decision's own cases (a heading, a parenthesized remark) are applied as decided.
2. **"Beyond its own task's budget" is read as "beyond what its own task still had of its budget"** (its budget and the client's grants in its
   interval, less its charged runs). With the literal reading, s3's 406b gives 1 run back to the user, #36 still reads committed 17 and spare 0,
   and the reply still asks for 4 (5.5): the false top-up the decision removes stays. The gate's own accounting ("7 runs back to root, 6 of them
   the user's"; "9a5b: 5 left") is this reading.
3. **`left` of the default hand-down does not count the held runs**; they count in the top-up and the reply. The held runs are already in the
   team; handing them down again would give the team twice as many and raise the approval by them (0a.3 I4). The decision's effect ("no top-up
   question while their approved runs are unspent") is reached through the reply.
4. **A2's notes are settled with the questions** (shown only while the result is unsettled). The decision says notes are shown, not for how long;
   a settled result's notes would otherwise stay on every later line of the task.
5. **A2 changes SKILL.md line 92**, which the brief does not list. Without it, step 5 item 3 tells root to copy nothing until every item of the
   block is answered, which would hold the copy for the notes the product no longer withholds and bring back the noise A2 removes.
6. **SIGHUP ends the scheduler cleanly and is recorded** (an inherited ignore stays ignored). Today SIGHUP's default action ends it at once with
   no record and orphans its runs. A clean stop writes `run.end` and `scheduler.exit`, as SIGTERM does; re-raising the default would need the
   scheduler to kill itself and leave no `scheduler.exit`. Whether SIGHUP should be ignored outright is C3's M5, on evidence only.
7. **C2 changes `telemetry`** (the pool's lock becomes re-entrant; the writer queues a line a handler emits mid-line), beyond the brief's sites.
   Without it a SIGTERM that lands while the scheduler writes an event line hangs the scheduler on its own lock.
8. **`scheduler.signal` carries `ppid` and `running`** besides the signal and the time (the envelope's `ts`): no stream ever recorded the
   scheduler's parent or the runs in flight at a kill (gate 3 C, "not recorded").
9. **C3's M1 is macOS only.** C1 runs on macOS; no Linux mechanism (such as `systemd-run --user`) rests on evidence, so Linux keeps 0a.3's detach.
10. **F-E6-7 mirrors the stamper's open-task rule in `services`** (as 0a.3 7.3 mirrored the batch rule): `traces` is not a dependency of
    `services`, and the stamp rule serves every message.
11. **The E6 replay kit reuses the E5 kit.** `TESTS/testkit/e5_replay.materialize` gains the keyword-only `evidence: Path = EV5` and
    `service: str = SERVICE_NAME` (defaults: today's behaviour); `TESTS/testkit/e6_replay.py` passes `EV6` and `weekly-memo` (17.1).
12. **The `HELD` text is a sentence of its own** (`The team still holds ...`), the brief's words with a capital letter, because it replaces
    `TOPUP` as the reply's last line.
13. **C3's integration test does not use the `real_kiro` fixture**, against `tests/testkit/fixtures.py:isolated_kiro`'s rule that integration
    tests must. That fixture's fence hashes `~/.kiro/agents/` and `~/.kiro/settings/mcp.json` (`tests/testkit/kiro_sandbox.py`), which the brief
    forbids touching. This test sets `KIRO_HOME` to its tmp dir for every kiro-cli call, so no profile lands under `~/.kiro`, and it reads
    nothing there; its own checks (the session record under its `KIRO_HOME`, only `tool_load` and `hirearchy::*` calls) take the fence's place.
14. **C1's verdicts add three classes the brief does not name** (no-run and finished are invalid and repeated; run-only is its own signature,
    not reproduced), and C1's turn 2 calls `progress` before `start`, so D-OUT can start the scheduler at the same point of the call without
    changing its shape. Both keep "vary one condition at a time" exact; neither changes what C1 must record.

## 16. Declared limits, out of scope, backlog and risks

Out of scope (the brief): A3 and D (rejected, D-E6-1 and D-E6-4), Phase 0b, the E7 study and its protocol (D-E6-6's turn cap, D-E6-7's harness),
a credit for runs the product lost (deferred).

Declared limits (each pinned by a test where one can show it):
1. A1 keeps every marker tail that names a criterion id as a question, even one that only introduces the list (`Questions for the client
   (C4-C6):` and a list): stricter, never hidden (Deviation 1). E5 and E6 had 0 such tails. E7 counts them (17.3, item 1).
2. A2's cost: a real question with no criterion id is a note and holds nothing (E6: 1 of 49, 6c63, asked anyway in T8).
3. A2 trusts the lead's ids: the id is matched as text, not checked against the contract; a note tagged with an id becomes a question (stricter).
4. 8613's two items that restate Lena's answers name C6 and C3, so its path stays withheld after A2; only A3 (rejected) would have moved them.
5. B's held runs are the case's user-held runs by its own accounting, not split per task; another case's runs that fall inside the case's
   window lower them (conservative); with the revised task closed nothing is held (0a.3's conservative reading stays for that case).
6. B gives nothing back to the user from a relayed result that came after its successor was sent (conservative); 0a.3's limits 1-3 stand, so a
   1-run default with nothing left still raises the approval by 1 (bc02 still does).
7. C2 does not record a signal that arrives before `serve` installs its handlers (the claim, the orphan settling, the recovery), nor SIGKILL;
   a Python handler cannot see who sent the signal.
8. C1 runs under a sandbox `KIRO_HOME` (the brief), so four conditions of the streams are not reproducible: the user's kiro home, the state
   directory under it, the user's global skills, and the user's `HOME` for root's MCP server (C1 gives it `$SB/home`, where the org's runs sign
   in through the inherited `KIRO_API_KEY`, so that the product never reads the user's installed skill; under the owner's choice (b) of 6.1 this
   last one is reproduced and drops from the list); and it runs on macOS only. C1's `ps -E` reading of the changed names is best-effort (a value
   holding ` NAME=` adds a name), which can only make D-ENV unset a name more.
9. C3's M1 is macOS only (Deviation 9).
10. F-E6-7 covers `delegate`: an agent client's service request (`request` without `revises`) still carries no tier.

Backlog: A3, if E7 counts paths withheld only by restated answers (D-E5-4's reopen condition, the owner's call); the tier of an agent client's
service requests (limit 10); a Linux reproduction (limits 8 and 9); a dedicated dashboard line for `scheduler.signal`; the 1-run default's
growth of the approval (0a.3 limit 1).

Risks: the notes are shown, not held, so a user sees them only if the assistant passes them on (SKILL.md line 92; LLM behaviour, E7 item 1);
C1 spends real model calls (bounded: 30 chat calls for C1, 6 for C1b, 12 integration-test runs for C3); M1 is the largest C3 branch and depends
on a legacy `launchctl` subcommand, so it ships only if its integration test is RED at `18c4ffb` and GREEN 3 of 3, and every case it cannot
finish falls back to today's detach; the re-entrant writer is shared by every process (covered by the telemetry contract
suites and the new tests).

## 17. What E7 must check

The changed texts are pinned by the exact strings of 4.4, 5.4, 6.2 and 8; E7's protocol amendment cites them.

### 17.1 The E6 replay kit

`TESTS/testkit/e6_replay.py` (test-only): `EV6 = REPO / "studies" / "E6-org-growth-0a3-recheck" / "evidence"`, `SERVICE_NAME = "weekly-memo"`,
`materialize(stream, cut, dest, inflight=None)` = `e5_replay.materialize(stream, cut, dest, inflight, evidence=EV6, service=SERVICE_NAME)`: the
organization `EV6/<stream>` had at the 21-character stamp `cut` (inclusive), the contract `service/history--SERVICE.v1.md` (budget 16) at
`lead/services/weekly-memo/SERVICE.md`. `TESTS/meta/test_e6_replay_kit.py`: s3 at bc02's cut holds 4a3e and bc02 in root's `sent/`, 11cc in
root's `read/`, the 5 run logs of 4a3e's interval and the contract with `budget: 16`; a missing evidence file fails the test. If `progress`
needs a file the kit does not write, the kit writes it (test-only), and the commit whose replay needs it says so.

### 17.2 Deterministic, at the merged sha (`TESTS/e2e/test_org_growth_0a4.py` unless named)

- **A-1, 8613 (s1 #56; cut `20261024T160847113000`, task `20261024T160535424081-root-b0fe`):** `client_items` of 8613 gives the C6 and C3 items
  as questions and `Style: 'himself' in Sam's table row (reviewer: harmless).` as the one note; `progress(task_id=b0fe)` contains `artifacts
  withheld (ask first). 2 questions for the client: ask the user before you copy or deliver. 1 note for the client (no criterion): Style:
  'himself' in Sam's table row (reviewer: harmless). no feedback yet.`
- **A-2, 762f (s1 #70; cut `20261024T161928019000`, task `20261024T161442312966-root-d675`):** the three list items are the questions, there is
  no note, the tail is no item; the line contains `3 questions for the client` and no `note for the client`.
- **A-3, 6c63, A2's cost (s3 #42; cut `20261024T172839677000`, task `20261024T172453163611-root-9a5b`):** the line contains `artifacts:
  lead/writer/work/memo-2026-10-05.md, lead/reviewer/work/review-memo-2026-10-05-summary-line.md` and `1 note for the client (no criterion):
  Keep or delete the '## Open, not decided' section`, and neither `questions for the client` nor `withheld`.
- **A-4, d80f (s1 #23; cut `20261024T154519419000`, task `20261024T154227019921-root-f06d`):** 2 questions, no note, unchanged.
- **A-5, every recorded result:** over the 19 results with a block that root received in s1-s3: 49 items, 47 questions, 2 notes (8613's and
  6c63's).
- **B-1, bc02 (s3 #19):** at cut `20261024T171425096624`, `service_steps.rework_step(bc02)` equals `The team still holds 11 of the user's runs
  for 20261024T170957358424-root-4a3e; the rework can use them.` (no `Ask the user`); at cut `20261024T171425096623`,
  `case_allowance.left("lead", "weekly-memo", 4a3e) == 0` (the default stays 1 run); after bc02 `user_approved(case, 16) == 17`.
- **B-2, 9a5b (s3 #36):** at cut `20261024T172453163611`, `case.relayed_to_user == 6`, `user_approved(case, 16) - user_committed(case) == 5`,
  `user_spend(case) == 12`, and `rework_step(9a5b)` (budget 1, as recorded) is `""`; at cut `20261024T172453163610`,
  `case_allowance.left("lead", "weekly-memo", bc02) == 6`.
- **C-1:** `TESTS/e2e/test_scheduler_signal.py` (a TERM then a KILL 0.2 s later leaves `scheduler.signal` and no `scheduler.exit`; a SIGHUP alone
  gives `stopped by SIGHUP`, or `action: ignored` if M5 shipped; a SIGHUP the scheduler was started with ignored gives `action: ignored`), on
  macOS, in the final validation's `check.sh`. Linux is not run in this batch: nothing is pushed, and the merge does not re-run `check.sh`. E7's
  deterministic part records the CI result of the merged sha once the owner pushes `main`, or cites a no-change `git diff --stat` of the
  `scheduler`, `processes` and `telemetry` packages as E6 did (`deterministic/SUMMARY.md`, Linux).
- **C-2:** `TESTS/e2e/test_scheduler_detach.py`, kept, passes.
- **C-3, the C1 reproduction:** if C3 shipped, `TESTS/integration/test_scheduler_survives_the_call.py` passes with `--run-integration` under a
  sandbox kiro home (E7 cites the C3 step's record: RED in at least 2 of 3 valid runs at `18c4ffb`, GREEN 3 of 3), and E7's preflight repeats
  C1's V0 (6.1, Setup 0 first) under the streams' conditions whether or not C3 shipped (D-E6-7), recording its `scheduler.signal` lines. If C1
  did not reproduce (or was run-only), E7 replays no kill and says so, citing `c1-reproduction.md`'s conditions tried.
- **F-1, dd34 (s1; cut `20261024T154745377872`):** `rework_context.work_tier("lead") == "relayed"` (root's relayed 3a54 is the lead's open task).
- **F-2, 395b and d13d (s3; cuts `20261024T172627799242` and `20261024T172724489270`):** `work_tier("lead") == "human"` (9a5b is open).
- **S-1:** SKILL.md has at most 125 lines and the needles of section 8.

### 17.3 Per stream, live

1. **A:** per result with a block: its questions and notes; copies made while `artifacts withheld (ask first)` showed (E6: 8 of 9) and the
   questions asked before each; notes passed on with the delivery; questions without an id (A2's cost) and whether they were asked; marker tails
   that named an id before a list and so counted as questions (declared limit 1; E6 had 0).
2. **B:** every human rework: its budget, `left`, `user_held` and `spare` at that moment, from the files; each `HELD` and `TOPUP` reply and
   whether its premise held (the runs really held, or really spare); top-ups the assistant asked for, and grants after a yes.
3. **C:** every `scheduler.signal` (signal, action, ppid, running, and what followed: `scheduler.exit` or nothing); schedulers alive at a turn's
   end and whether they survived it (E5 0 of 1, E6 0 of 1); `scheduler.start` lines with a `scheduler.exit` by the stream's end (E6 19 of 20);
   `run.orphan` events.
4. **F-E6-6:** human-tier accepts recorded before the user saw the version (E6 s3: 2; target 0); keep-as-is answers about a version the user
   saw, recorded as accepts (E6 1 of 1).
5. **F-E6-7:** delegations without `revises` made under a root task with a tier that carry it (E6: none of the writer tasks under b5b1, 40f3
   and 9a5b, nor dd34; target all).
6. **The spend ask:** spend asked a turn after the question or item that needed it (E6 s2: 2; target 0).
7. **Unchanged guarantees:** clauses 1 and 2, P1-P4 and 0a.3's measures as in E6 (10.5, 10.8), so 0a.4 shows no regression in what E6 found
   working.
8. **Models:** every seat on claude-sonnet-5.5 at high effort.

## Appendix A. Review resolutions

Revision 1 (`46273df`) had no review. Revision 2 answers the design review of pass 1 (`.agents/tasks/design-review.md`, CHANGES_REQUESTED: 1
HIGH, 10 MEDIUM, 10 NIT). Every finding is addressed; none is backlogged or ignored, and none changes the product behaviour e6-decision.md
decides (finding 6 narrows A1 in a case E5 and E6 never had; Deviation 1).

| # | Sev. | Finding | Resolution | Where |
|---|---|---|---|---|
| 1 | HIGH | C1 and the C3 test give the org's runs `HOME=$SB/home`, where they may not sign in | Addressed. Setup 0, a zero-cost `HOME=$SB/home KIRO_HOME=$SB/kiro-probe kiro-cli whoami` preflight, before any chat call; on failure `warning` with the owner's choice (a) `KIRO_API_KEY` in the server's `env`, or (b) the user's `HOME` with `whoami`/`status` calls as a stop condition (verified: the only readers of the installed skill). The integration test uses the same probe as its skip condition. Run once at design time: it exited 0 (`Authenticated with API key`, through the `KIRO_API_KEY` the shell inherits; the E6 streams signed in the same way, `EV6/s3/turn-05.stderr.txt`; `run_environment` keeps the key for runs) | 6.1 Safety, Setup 0; 6.3; limit 8 |
| 2 | MED | The 30-call bound can run out before D-ENV/D-OUT | Addressed. Fixed order V0, D-ENV (+2 narrowing), D-OUT, then V3, V2, V1, V5, V4; separate bounds C1 <= 30 chat calls, C1b <= 6, C3 integration runs <= 12; a bound before the mechanism variants are decided stops C1, later it only skips (recorded) | 6.1 Safety, runs table |
| 3 | MED | D-ENV's names, D-OUT's three changes, missing verdicts, C1b once | Addressed. (a) D-ENV's names: the changed names (value absent or different, so an inner `KIRO_SESSION_ID` is caught although the C1 shell carries its own session's `KIRO_*` names) less the profile's `env` keys, `VIRTUAL_ENV`, `UV_*` and the M2 refusal list. (b) D-OUT: the shell starts the scheduler when turn 2's `progress` `tool.call` appears; turn 2 still calls `start` (V0's turn 2 also calls `progress` first, so the shape is the same); validity and run-age checks. (c) Verdicts no-run, finished (invalid, repeated) and run-only (not reproduced). (d) C1b up to 3 attempts | 6.1 Setup 3, 5, runs table; Deviation 14 |
| 4 | MED | RED on C2b, one RED/GREEN run, M2 row, no outcome when GREEN fails | Addressed. RED on a throwaway detached checkout of `18c4ffb` (the brief's sha; no deviation), 3 valid runs with at least 2 failing; GREEN 3 of 3 on the C3 change; the M2 row requires the test; otherwise no C3 commit, every run recorded, `warning` | 6.3; 9; 14 |
| 5 | MED | M1's new failure of `start`, launchd respawn, non-blocking `remove` | Addressed. Every case M1 cannot finish falls back to today's detach with a log line; the intermediate exits 0 in every case (and at once when its env file is missing); `submit` waits until `launchctl list <label>` fails (at most 2 s); `launchctl list` recorded after a `submit`; the 5-s survival check follows the `remove` | 6.3 M1; 9; I13 |
| 6 | MED | A1's heading rule drops a criterion-tagged tail before a list | Addressed, more strictly than the review's code: a tail that names an id is always an item (the review's `wrapped or not names_id` would still drop `(C3: keep Marta's row?)` before a list of notes). Cost: a scope label like `(C4-C6)` before a list is one more question (limit 1). E5/E6 effect unchanged | 4.2, 4.6, 4.7, 4.8; Deviation 1; limit 1; I2 |
| 7 | MED | I6 contradicts limit 6, B-1 and 0a.3 limit 1 | Addressed with the review's wording; 5.1's parenthetical attributes the rule to 0a.3 I4 | 11 I6; 5.1 |
| 8 | MED | A2 leaves the `progress` tests red | Addressed. A2 updates every Rule A fixture, `progress/tests/test_lines.py` included; A2's TARGETS add `src/hirearchy/progress/tests` | 13 Rule A; 14 |
| 9 | MED | `test_wire_cli.py` revises an open task and gets `HELD` | Addressed. Rule B names the pin, its computed `HELD` text (4 held) and its new assertions; B2's TARGETS add it; 5.8 lists it | 13 Rule B; 14; 5.8 |
| 10 | MED | SIGHUP tests depend on the runner's disposition | Addressed. `sighup_default`/`sighup_ignored` fixtures restore what they found; the e2e starter sets the disposition before `start`; a third e2e case expects `action: ignored`; M5 changes the stop cases deliberately | 6.5; 6.3 M5 |
| 11 | MED | C-1 claims a Linux CI run | Addressed with the review's wording: macOS only in this batch; E7 records CI after the owner pushes, or a no-change diff | 17.2 C-1 |
| 12 | NIT | The parentheses test is too loose and too tight | Addressed. `_wrapped` (balanced, one final `.`), with tests for both shapes and a nested one | 4.2; 4.7 |
| 13 | NIT | The fix-pass rule is missing | Addressed | 14 |
| 14 | NIT | TARGETS miss direct readers | Addressed. E1 adds `test_round_g_assistant.py`, `test_round_f_guidance.py`, `tests/e2e/test_round7.py` (and E1 adds nothing to `## Services and reflection`); B1 adds `src/hirearchy/progress/tests` | 14 |
| 15 | NIT | M1's files under `.runtime/` | Addressed. A private `tempfile.mkdtemp` directory (0700) outside the organization, removed in a `finally` | 6.3 M1; 2; 10 |
| 16 | NIT | Restoring a `None` handler raises | Addressed: `handler if handler is not None else signal.SIG_DFL` | 6.2 |
| 17 | NIT | kiro-cli's log only looked for under `$SB/kiro-home` | Addressed. The record states whether a log was found there and records it missing otherwise; never searched under `~/.kiro`; stderr (kiro-cli's `[INFO]` lines) is kept per call | 6.1 Setup 5 |
| 18 | NIT | Wrong test file name | Addressed: `src/hirearchy/daemon/tests/test_launch_site.py` | 6.3 M2; 14 |
| 19 | NIT | "ask them" is ambiguous | Addressed: "ask the others in plain words"; no needle holds `ask them` or `in plain words` | 8 |
| 20 | NIT | The integration test departs from the `real_kiro` rule silently | Addressed: Deviation 13 with the reason | 15; 6.3 |
| 21 | NIT | The E6 kit lands in A3 | Addressed: commit T0, `test(testkit): the E6 replay kit`, before A1 | 14; 17.1 |

The review's unverified point on B1 and the E5 replays is now verified (5.5: 963a's share is 0; s2's relayed tasks come after both cuts).

