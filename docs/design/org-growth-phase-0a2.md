# Org growth, Phase 0a.2: the enforcement batch after E4 (technical design)

Status: design, revision 1. Branch `feat/org-growth-phase-0a2` off `main` `3815813`; worktree `/Volumes/workspace/hirearchy/.worktrees/org-growth-0a2`.
Baseline (`.agents/tasks/baseline.md`): 14 415 passed, 5 skipped, 3 deselected, 1 xfailed; import-linter contracts kept; `scripts/check.sh` exit 0
(734 s). `skills/hirearchy/SKILL.md`: 125 lines. Root instructions: 2 635 characters at the reference path (`/` + 59 `r`), 2 558 raw.

Sources of truth (read in full):
- `docs/research/org-growth/phase-0a1/e4-decision.md` (binding): D-E4-1 to D-E4-7, and the owner's D-E4-8 (every live-study seat runs
  claude-sonnet-5.5; it needs no product change and shapes section 21 only). "The decision" below.
- `docs/research/org-growth/phase-0a1/e4-gate.md` section 3: proposals P1 to P4 and the non-enforcement items. "The gate" below.
- `studies/E4-org-growth-0a1-recheck/STUDY.md`: findings F-E4-1 to F-E4-10.
- `docs/design/org-growth-phase-0a.md` ("0a design") and `org-growth-phase-0a1.md` ("0a.1 design", sections 17-21); `docs/design/kiro-runtime-v3.md`
  ("V3 design", sections 5.1, 5.2, 10).
- README.md, ARCHITECTURE.md (2.2, 2.3, R1-R13), `docs/refactor-principles.md`, `skills/hirearchy/SKILL.md`, the instructions budget test
  `src/hirearchy/skill/tests/test_skill_services.py`.

Abbreviations: `SRC` = `src/hirearchy`, `TESTS` = `tests` (both in the worktree). `EV` = `studies/E4-org-growth-0a1-recheck/evidence` and `EV3` =
`studies/E3-org-growth-0a-live/evidence`; both are tracked in git (checked: `git ls-files` lists them), so the replays read them from the
repository, read-only. Every function named below was read in the worktree at `3815813`.

## 1. Overview

E4 failed every rule over three valid streams. Its deterministic mechanisms held; what failed was what still rested on the assistant or the
lead following text: the playbook gate admitted a whole text on one citation (s2r v2 carries E2's wrong rule as `admitted: c`), contracts were
amended in the reject turn, a flagged question was asked with the copy, the assistant patched every delivered memo by hand, and a relayed
rework's edits reached a delivered memo through the shared work file. 0a.2 moves those guarantees into refusals at the single layer every
caller goes through, and makes the rest visible:

1. **P1, line-level admission** (D-E4-1). `revise_playbook` diffs the new body against the current one line by line. Rule (c) admits only
   lines that are the cited confirmed criterion's own words with its id; rule (b) only lines that carry their qualifying id. The refusal
   lists the offending lines; the admission carries the admitted lines and root's note lists them. Companions: the digest marks lessons of
   relayed reworks; a `confirms` link-note id is evidence for its criterion (F-E4-7); an amendment that removes a criterion names the
   playbook lines that quote it.
2. **P2, the contract changes only as the recorded answer** (D-E4-2). Root's acceptance amendments carry `answers=`, `about=` and `words=`
   (the answer to a rejection; the product writes the `confirms` link itself and refuses a second answer) or `words=` alone (user-initiated,
   never (c)-eligible). Every delivered request needs its verdict first. The `feedback(reject)` reply gives the exact question.
3. **P3, partial** (D-E4-3). `progress` flags `blocked` results with client questions and withholds the artifact path ("ask first") while they
   are open; `progress`, `status` and `whoami` name the files of a contract's deliverable folder that differ from the team's last checked
   version or that the team never wrote, and tell root to tell the user. No `deliver` tool.
4. **P4, the judged version** (D-E4-4). `request(revises=X, source="human")` on a case whose artifact a relayed rework changed after the judged
   delivery needs `base="delivered"|"latest"`; `delivered` gives the lead the judged version (its org-git commit and text). Rework
   delegations inherit the tier.
5. **D-E4-6.** The root instructions say to activate the skill before building or rating, and give the reject order in one line. A run that
   ended on a model-service throttle with no tool effect is not charged (a runtime credit note returns its run) and is retried once.
6. **Deterministic replays** of s1r T5, s1r v3/v4, s1r T8, the s2r chain, the s3 flow and E3 T5, read from the raw evidence files.

What the product still cannot enforce (gate section 3, "A limit common to all of them"): that a question was asked, how it was worded, or that
recorded words are the user's. Every enforcement below makes the compliant path the only path to a change, or makes a bypass visible.

## 2. Technology stack (locked)

Python 3.11, the existing packages only (`mcp`/FastMCP, PyYAML, Textual untouched), `git` (already required by `snapshots`), uv, pytest,
`mypy==2.4.0 --strict`, `import-linter==2.15`, `scripts/check.sh`. No new runtime dependency, no new package, no new dependency edge between
packages (section 11), no new ledger, no new file kind in an organization. Strict TDD (R11): one logical change per commit, the suite green
after each (section 18). The kiro launcher stays standard-library only (V3 design 5.1).

## 3. Shared definitions (each defined once)

| Name | Home | Definition |
|---|---|---|
| `line_key(line) -> str` | `SRC/services/api.py` (pure) | `"".join(ch for ch in line.casefold() if ch.isalnum())`: letters and digits, case-folded. Punctuation, spacing and markdown alone never make two lines differ; a change of any word does. |
| `changed_lines(current, new) -> list[str]` | `SRC/services/api.py` (pure) | The lines of `new` (stripped, in order) whose `line_key` is not among the keys of `current`'s lines, counted as a multiset (`collections.Counter`): a line repeated in `new` more often than in `current` counts once more. Lines whose key is empty (blank, `---`, a fence, a lone `-` or `#`) are never changes. `changed_lines(new, current)` gives the removed lines. |
| `rated(case, task) -> bool` | moved from `SRC/progress/_lines.py` to `SRC/reflection/api.py` (pure); `progress` imports it | Has the client given a verdict (any tier) on this delivery or on a later task of its chain? Unchanged semantics. |
| `delivered_unrated(cases) -> tuple[str, ...]` | `SRC/reflection/api.py` (pure) | The latest task id of every case whose `state == "done"` and `not rated(case, case.tasks[-1])`. |
| `artifact_paths(body) -> list[str]` | `SRC/kernel/_text.py`, exported from `kernel.api` | The paths of the `## Artifacts` section of a result body: the non-blank stripped lines of that section (`## ` heading, case-insensitive), each `lstrip("-* ")` and cut at the first `" ("`. Exactly what `progress._lines.artifacts_of` does today through `attention.section`; `artifacts_of` becomes `artifact_paths(result.body)`, so `progress` and `reflection` parse one way. |
| `blob_id(data, hexlen=40) -> str` | `SRC/snapshots/api.py` (pure) | The git object id of a blob with these bytes, as `git hash-object` computes it: `sha1(b"blob %d\0" % len(data) + data)` for `hexlen == 40`, `sha256(...)` for 64. The caller passes the length of the id it compares with (the repository's own object format); any other length is a `ValueError` (a bug). |
| The judged delivery of a case | `SRC/reflection/_judged.py` | Section 7.2. |
| The basis of a contract version | `SRC/services/_parse.py:contract_of` | Section 5.4: `answers`, `about`, `words`, `initiated` in its frontmatter. |
| `RUN_CREDIT_TITLE = "Run not charged"` and `is_run_credit(sender, title, budget) -> bool` | `SRC/kernel/_message.py` (pure) | A note is a run credit when `sender == RUNTIME`, `budget > 0` and `title.startswith(RUN_CREDIT_TITLE + ": ")`. In `kernel` because `budget`, `agents` (retired archive) and `observability` all recognize it and only the kernel is below all three. |

## 4. P1: line-level admission (D-E4-1; gate 3 P1)

### 4.1 Behaviour

`SRC/services/_playbook.py:RulePlaybookReviser.revise_playbook` computes, after the "no change" refusal and before the gate,
`lines = changed_lines(current.body, body)` (`[]` when there is no current playbook) and `removed = changed_lines(body, current.body)`, and
passes `lines` to the gate: `self._evidence.admit(actor, service, ids, reason, exempt=exempt, lines=lines)`.

`SRC/services/api.py:ServiceEvidence.admit` gains the keyword `lines: Sequence[str] = ()` and `Admission` gains
`lines: tuple[tuple[str, str], ...] = ()` (each admitted line with the id that admits it). `SRC/reflection/_evidence.py:CaseServiceEvidence.admit`
keeps every step it has today (resolve the ids, unknown ids, exemptions, agent client, then rules (c) and (b) at the level of the evidence,
then G2/G1) and adds a **line stage** after the evidence stage has found an admitting rule:

1. Exempt revisions (`first`, `restore` of a version the client wrote) return as today; `lines` is ignored.
2. `added` = the cited criteria rule (c) admits (today's `added`); `qualifying` = every subject `x` with `len(cases_of(x)) >= 2` (today's (b)
   loop, collected instead of returning the first); `tags` = `qualifying` plus every cited assertion id whose `about` meets `qualifying`.
   When both are empty, G2/G1 are raised exactly as today.
3. Each line of `lines`:
   - is a **(c) line** when `line_key(line)` equals `line_key(c.id) + line_key(c.text)` or `line_key(c.text) + line_key(c.id)` for some
     `c` in `added` (for example `- C9: <C9's text, verbatim>` or `<C9's text> (C9)`); it is admitted on `c.id`;
   - else is a **(b) line** when it contains an id of `tags` as a standalone token (regex `(?<![A-Za-z0-9])<id>(?![0-9])`, case-insensitive),
     for example `[C6]`; it is admitted on that id (the first in `tags` order);
   - else it is **offending**.
4. Any offending line: refused with P1-REFUSED (4.2). Nothing is written.
5. Otherwise `Admission(rule, ids, detail, lines=admitted)`: `rule` is `"b"` when any admitted line is a (b) line, else `"c"` when `added` is
   non-empty, else `"b"`; `detail` is today's (c) or (b) detail for that rule. With `lines == ()` (a revision that only removes or reorders
   lines) the admission is today's.

Root's quiet note (`RulePlaybookReviser.revise_playbook`, `delivery.notify(client, ...)`) gains, after `admitted: ...`:

```
Lines added or changed (each with the id that admits it):
- [C9] - C9: The memo starts with a one-line summary ...
{k} line(s) removed.
```
The first two lines only when `admission.lines` is non-empty (each line clipped to 200 characters with `clip_line`); the last only when
`removed` is non-empty. The playbook frontmatter is unchanged (`evidence`, `admitted`, `restores`): the lines are derivable from the archived
versions and recorded in the note.

### 4.2 Refusal text (P1-REFUSED, new; constant `LINES_REFUSED` in `SRC/reflection/_evidence.py`)

```
refused: every line a revision adds or changes must rest on the evidence it cites, and {n} line(s) do not:
- "{line}"
{c_part}{b_part}A change of punctuation, spacing or markdown alone needs nothing. Nothing was written: revise again without these lines, or send {client} (`send`) this question once: "We would add to how we deliver {service}: {first offending line}. Is that what you want from now on? If yes, please add it to the contract as a criterion."
```
- At most 10 offending lines are listed (each `clip_line(line, 160)`), then `- and {k} more`.
- `{c_part}` when `added` is non-empty: `Rule (c) admits only the cited confirmed criterion's own words, one line each with its id: these lines are not {C9's | C8's or C9's} words. Write it as "- C9: {C9's text, clip_line 300}". ` (one `Write it as` sentence per criterion of `added`).
- `{b_part}` when `tags` is non-empty: `Rule (b) admits a line that carries the id it rests on ({"[C6]", "[R2]"}): these lines carry none. `
- The first offending line in the question is clipped to 160 characters.

The unknown-evidence refusal, G1, G2 and the agent-client refusal are unchanged.

### 4.3 A `confirms` link-note id is evidence (F-E4-7)

`SRC/reflection/api.py:Verdict` gains `link_notes: tuple[Message, ...] = ()`: the link notes that reply to it (every tier), in id order.
`SRC/reflection/_cases.py:DerivedCaseHistory._verdict` fills it from the `links` list it already receives. In `admit`, a cited id that is the
id of a link note is resolved before the "unknown" branch:
- a human-tier link note (`verdict_tier(m) == "human"`): `count(assertion of its verdict)` when the verdict is an assertion, and every
  `C<k>` it names that is a current criterion is added to `subjects` (as if cited);
- a relayed link note: the note `link {id} is relayed (the assistant's own reading)` (it weighs nothing, like a relayed verdict).
s1r's `...-root-1753` and s3's `...-root-1fb7` are then resolved, not "unknown evidence".

### 4.4 The digest marks lessons of relayed reworks

`Case` gains `lesson_sources: list[str] = field(default_factory=list)`, parallel to `lessons`: the `source` of the task each lesson's result
answers (`"relayed"`, `"human"` or `""`), filled in `DerivedCaseHistory.cases` from the same comprehension as `lesson_ids`.
`SRC/reflection/_digest.py:case_line`:
- the latest lesson from a relayed task reads `; lessons (from a relayed rework, not the client's): "..."`; when the "written after the
  reject" mark also applies, both marks are joined: `lessons (from a relayed rework, not the client's; written after the reject: check it against
  her words)`;
- each earlier lesson from a relayed task is prefixed `(relayed) ` inside the `earlier:` part.
The comment "The latest result is the final word on the case" becomes "The latest result is the team's final word on the case; a relayed
rework's lessons are marked: they are not the client's."

### 4.5 A removed criterion names the playbook lines that quote it

New pure function in `SRC/services/api.py`: `quoting_lines(body: str, criterion: Criterion) -> list[str]`: the lines of `body` (stripped,
non-empty key) that contain `criterion.id` as a standalone token, or whose `line_key` contains `line_key(criterion.text)` (the text quoted
verbatim, modulo punctuation). `SRC/services/_amend.py:ContractAmender.diff` gains the parameter `quoting: Mapping[str, Sequence[str]]` (removed
criterion id -> lines; the package-private `ContractAmendment` Protocol follows); `RuleContractDefiner` computes it from
`self._catalog.read_playbook(owner, name)` for every criterion the amendment removes. The note gets, after the criteria list and before the
rule (c) line, one line per removed criterion with quoting lines:

```
Removed: C9. Playbook v2 still quotes it in 1 line(s): "- **C9 – Relative deadlines**: ...". Where it differs from the contract, follow the contract; the playbook changes only by a revision the evidence admits (step 3).
```
(each line clipped to 160 characters, at most 3, then `and {k} more`). Advisory only: nothing is refused and no new admission rule is added
(section 20, D9).

### 4.6 Texts the owner sees

- **Reflect step 3** (`SRC/reflection/_sections.py:EvidenceReflectSection.section`, human client, unlocked): the sentence from `It is admitted
  only when` to `are not evidence.` becomes:
  `It is admitted only when the same criterion or assertion failed in 2 different cases the client rejected (then every line it adds or
  changes carries that id, e.g. "[C6]"), or when it cites a criterion your parent added to the contract by an amendment the client confirmed
  ({eligible}): then it may add only that criterion's own words, one line each, "- C<k>: <its text>". A link note id counts as its criterion.
  Your lessons and relayed verdicts (the assistant's own reading) are not evidence.`
- `_eligible`: one id `now {id}: a revision citing it may add its words`; several `now {ids}: a revision citing one of them may add its words`;
  `none yet` otherwise; unconfirmed amended ids append `; {ids} {is|are} not confirmed yet`; user-initiated ones (5.5) append
  `; {ids} {is|are} user-initiated (rule (c) never admits {it|them})`.
- **`revise_playbook` docstring** (`SRC/mcp_server/_tools_services.py:_register_owner_tools`): after `(your Reflect section and the amendment
  note name them);` insert `line by line: under the first rule every line you add or change carries the id it rests on ("[C6]"), under the
  second it is only that criterion's words ("- C<k>: <its text>"); a link note id counts as its criterion;`, re-wrapped at today's column.
- **Amendment note, rule (c) line** (`ContractAmender.diff`): `... is admitted; confirmed now: {ids}.` becomes `... may add that criterion's own
  words, one line each ("- C<k>: <its text>"); confirmed now: {ids}.` and the last sentence becomes `A criterion marked (not confirmed) counts
  once the client's yes is recorded (it reaches you as a criterion link); one marked (user-initiated) never does.`

### 4.7 What P1 cannot enforce

That a (c) line is the right place for the rule, or that a (b)-tagged line follows from the two rejections: a tagged elaboration is admitted
on the tag (rule (b) rests on two client rejections, as today). The services listing does not show the added lines (section 20, D6).

## 5. P2: the contract changes only as the recorded answer (D-E4-2; gate 3 P2)

### 5.1 Arguments and surfaces

| Layer | Change |
|---|---|
| `SRC/services/api.py:ServiceCommands.define_service` (and package-private `ContractDefinitions`, `RuleServiceCommands`) | keywords `answers: str \| None = None`, `about: str \| None = None`, `words: str \| None = None` |
| `SRC/app/_facade_services.py:ServicesMixin.define_service` (the `Org` facade) | the same three keywords, passed through; `TESTS/architecture/org_signatures.json` and `facade_cases.py` updated |
| MCP, root (`SRC/mcp_server/_tools_services.py`) | `_register_client_tools` registers `define_service` per identity: `_register_root_define` (root: the 12 arguments of today plus `answers: str \| None = None, about: str \| None = None, words: str \| None = None`, docstring 5.7) and `_register_agent_define` (agents: today's signature and docstring, byte-identical, so `mcp/surface_manager*.txt` keep it). The `amendment_step` tail is removed (5.6). |
| CLI (`SRC/cli/_commands_services.py:DefineServiceCommand`) | `--answers VERDICT_ID`, `--about ID`, `--words TEXT\|@FILE` (read with `TextSource.read`); help: `amendment of the criteria: the rejection the user's answer is about (its message id)`, `the C or R id your question named`, `the user's words, verbatim (their answer; alone: a change they asked for on their own)` |

The refusal is enforced in `SRC/services/_define.py:RuleContractDefiner.define_service`, the only writer of `SERVICE.md`
(`FsServiceStore.write_contract` has no other caller). MCP (root and agents), the CLI, the `Org` facade and `blueprint` apply all reach it
through `ServiceCommands.define_service` -> `RuleServiceCommands` -> `RuleContractDefiner`; `blueprint` only ever makes first definitions (a
`playbook` on an existing service is refused today). No other path changes a contract: section 5.8.

### 5.2 The gate (in `RuleContractDefiner.define_service`)

Definitions: an **acceptance amendment** is a call on an existing service whose resulting acceptance list adds or removes at least one
criterion (`set(new.acceptance) != set(old.acceptance)`; a pure reordering is not one). **Root's** = `actor == ROOT`.

Facts come from a new `ServiceEvidence` method (implemented in `reflection`, the 0a pattern; services cannot import reflection):

```python
def amendment_basis(self, owner: str, service: str) -> AmendmentBasis:
    """What a root amendment of the acceptance criteria may answer: every human-tier rejection of the service (oldest first) with whether it
    has its answer, and the latest task of every case whose done delivery has no verdict yet."""
```

```python
@dataclass(frozen=True)
class Rejection:  # SRC/services/api.py
    note: str              # the rejection's message id (its first 21 characters are when it was recorded)
    assertion: str         # its R<k> (service-wide numbering, as `services` shows it)
    task: str              # the request (or rework) it judged
    title: str             # that task's title (the link note's title names it)
    earlier: tuple[str, ...]  # the R ids recorded before it
    words: str             # the client's words in the rejection (Verdict.note)
    answered: str          # the id of the first human-tier link note that replies to it; "" while it has none

@dataclass(frozen=True)
class AmendmentBasis:
    rejections: tuple[Rejection, ...]
    unrated: tuple[str, ...]  # reflection.delivered_unrated(cases)
```

Order of checks, each refusal writes nothing:

1. `actor != ROOT` and any of `answers`, `about`, `words` given: P2-ROOT-ONLY.
2. Any of them given on a first definition, or on a call that is not an acceptance amendment: P2-NOT-AN-AMENDMENT (after today's "no change"
   refusal, so an amendment that changes nothing keeps today's text).
3. Root's acceptance amendment (`answers`, `about`, `words` normalized: stripped; `about` upper-cased):
   1. `basis = self._evidence.amendment_basis(owner, name)`; `OrgError`/`OSError` while reading it: P2-UNREADABLE (fail closed: the gate guards
      the contract).
   2. `basis.unrated` non-empty: P2-UNRATED, whatever else was passed (the verdicts come first: this is the s1r T5 order, where the amendment
      came 0.46 s before the `feedback(reject)`).
   3. `words` missing or blank: P2-NEEDS-WORDS. `len(words) > FEEDBACK_MAX` (1000): P2-WORDS-LONG.
   4. exactly one of `answers` and `about` given: P2-PAIR.
   5. With `answers` (the answer to a rejection):
      - no `r` in `basis.rejections` with `r.note == answers`: P2-NOT-A-REJECTION;
      - `r.answered`, or a stored contract version whose `answers == r.note`: P2-ANSWERED (one rejection, one answer);
      - `about` is neither a criterion current in the contract version in force when `r` was recorded (the latest stored version whose
        `defined` is at or before the timestamp of `r.note`, read with `ServiceStore.versions(owner, name, "SERVICE")` and `contract_of` as
        `stored_versions` does; its criteria through `criteria_of(number_criteria(stored), that version's acceptance)`) nor one of
        `r.earlier`: P2-ABOUT;
      - the words of `words` (lower-cased, split on non-alphanumerics) equal those of `r.words`, or number at least 4 and appear in
        `r.words` in order and contiguous: P2-WORDS-ARE-THE-REJECTION (section 20, D3).
   6. Without `answers` (user-initiated): any `r` in `basis.rejections` with `not r.answered` and no stored version answering it:
      P2-OPEN-REJECTION (the change is inside a rejection; section 20, D4).
4. Write the contract (5.4), then, on the answer path, the link note (5.4), then the owner's amendment note, then the reply (5.7).

### 5.3 Refusal texts (new; constants in `SRC/services/_define.py`)

- **P2-ROOT-ONLY**: `answers, about and words are root's: they record the human client's answer. An agent client amends its report's contract without them.`
- **P2-NOT-AN-AMENDMENT**: `answers, about and words record the user's answer to a change of the acceptance criteria; this call changes none. Pass them only with acceptance, add_acceptance or remove_acceptance on an existing service.`
- **P2-NEEDS-WORDS**:
  ```
  refused: a change of the acceptance criteria of `{name}` records the user's words. If it answers a rejection, pass answers=<the rejection's message id>, about=<the C or R id your one question named> and words=<the user's answer, verbatim>, after they answered yes to that question{open}. If the user asked for this change on their own, outside any rejection, pass words=<their request, verbatim> alone: it is recorded as user-initiated and never admits a playbook revision. Nothing was written.
  ```
  `{open}` = ` (waiting for an answer: R1, message <id>)` listing every unanswered rejection, or `""`.
- **P2-WORDS-LONG**: `words is {n} characters; the limit is 1000: the user's answer, verbatim, not a summary.`
- **P2-PAIR**: `answers and about go together: answers=<the rejection's message id>, about=<the C or R id your question named>. Nothing was written.`
- **P2-UNREADABLE**: `refused: the record of `{name}` cannot be read ({error}), so the contract was not changed. Try again; if it persists, tell the user.`
- **P2-UNRATED**: `refused: {n} delivered request(s) of `{name}` have no verdict yet: {task ids}. Record the user's verdict on each with feedback first (a rejection, then its one question); the contract changes only after the verdicts. Nothing was written.`
- **P2-NOT-A-REJECTION**: `refused: answers must be the message id of a rejection you recorded with feedback(..., source="human") on a request of `{name}`: {answers}. Its rejections: {"R1 (message <id>)", ... or "none yet"}. Nothing was written.`
- **P2-ANSWERED**: `refused: rejection {R} (message {id}) already has its answer ({link note <id> | contract v<n>}): one rejection gets one answer. A new lasting rule needs a new rejection and its question, or words alone when the user asks for it on their own. Nothing was written.`
- **P2-ABOUT**: `refused: about must be the id your one question named: a criterion of contract v{v}, in force when {R} was recorded ({C ids}), or an earlier rejection ({R ids or "none"}): {about}. A criterion this change creates cannot be what the question was about. Nothing was written.`
- **P2-WORDS-ARE-THE-REJECTION**: `refused: words repeats rejection {R}'s own note. The answer is what the user said to your one question after the rejection (e.g. "Yes, add it."); an "always ..." inside the rejection is not it. Nothing was written.`
- **P2-OPEN-REJECTION**:
  ```
  refused: rejection {R} (message {id}) on task {task} has no answer yet, so this change is not one the user asked for on their own. Ask the user the one question first ({QUESTION_FORM}). On yes: define_service(owner="{owner}", name="{name}", ..., answers="{id}", about=<the id you asked about>, words=<their answer, verbatim>). On no, a one-off or "as it is": feedback(task_id="{task}", verdict="reject", confirms="{id}", criterion=["none"], ["R<j>"] or ["C<k>"], source="human", note=<their answer, verbatim>). Nothing was written.
  ```
  `{QUESTION_FORM}` is the question form of 5.6 for that rejection. With several unanswered rejections, the oldest is named.

### 5.4 What is recorded (immutable versions and notes, nothing derived is stored)

- **Contract version frontmatter** (`SERVICE.md`, written by `FsServiceStore`, the single writer of `<owner>/services/**`). After `created`:
  answer path `answers: <rejection id>`, `about: <C|R id>`, `words: <verbatim>`; user path `initiated: user`, `words: <verbatim>`. The keys
  belong to the version that carries them: the next version's `meta` is built from scratch (as today) and never copies them; the archived
  `history/SERVICE.v<n>.md` keeps them immutable. `Contract` (`SRC/services/api.py`) gains `answers`, `about`, `words`, `initiated: str = ""`,
  parsed by `contract_of`. Versions written before 0a.2 carry none (legacy).
- **Criterion basis.** `Criterion` gains `answers: str = ""` and `user: bool = False`: the basis of the latest version that added the text
  (present in that version, absent from the one before; v1's texts have none). `number_criteria(versions, basis=None)` takes
  `basis: Mapping[int, tuple[str, bool]]` (version -> (answers, user)); `SRC/services/_criteria.py:stored_versions` keeps its shape and a new
  `stored_basis(store, owner, name)` reads the map; `ContractServiceCatalog.criteria` and the definer's in-memory numbering pass it.
- **The `confirms` link the product writes** (answer path only), after the contract write: the same note `feedback(confirms=...)` writes today,
  through one shared writer. A new package-private Protocol in `SRC/services/_protocols.py`:
  ```python
  class LinkNotes(Protocol):
      def write(self, actor: str, owner: str, title: str, rejection: str, ids: Sequence[str], words: str) -> Message:
          """The link note on ``rejection``: from ``actor`` (root) to ``owner``, LINK_HEADER + the user's words, criterion = ``ids``,
          source human, wake False, title 'criterion link on "<title>": <ids>'."""
  ```
  `SenderLinkNotes(sender: MessageSender)` in `SRC/services/_feedback.py` implements it; `RuleClientFeedback` uses it for `confirms`
  (byte-identical note) and `RuleContractDefiner` gets it as its 14th collaborator. `ids` = the criteria the amendment added, in order; when it
  adds none, the ones it removed. The link is stamped `source: human` by the product; the `words` are declared by root (declared provenance).
  If the link cannot be written (`OSError`/`OrgError`) after the contract was: section 12.
- Nothing else: no new event field (`service.define` keeps `amendment: bool`, so `events/line_shapes.txt` is unchanged), no ledger.

### 5.5 Eligibility: a user-initiated amendment is never (c)-eligible

`SRC/reflection/api.py:confirmed_criteria(cases, criteria=())` (signature gains `criteria`; every caller passes the service's criteria): a
`C<k>` named by a human-tier link note (as today) is confirmed when
- its criterion has `answers`: only if a human-tier link note **on that rejection** names it (the product's own link);
- its criterion has `user`: never;
- otherwise (v1, an agent's version, a legacy version): as in 0a.1 (any human-tier link names it).
`confirmed_amendments(criteria, confirmed)` is unchanged (`amended and in confirmed`), so the gate, step 3, the amendment note and the listing
all read one rule. Consequence: after 0a.2 a `feedback(confirms=X, criterion=["C<k>"])` can no longer make an amendment (c)-eligible unless
the version that added `C<k>` answers `X`, which only the gate writes.

Marks: `services` (`SRC/reflection/_reports.py:TextServiceReports._block`): a current amended user-initiated criterion reads
`    C11: <text> (amendment, user-initiated: never admits a playbook revision)`; the amendment note marks it ` (user-initiated)`; step 3 as in 4.6.
Unconfirmed legacy amendments keep `(amendment, not confirmed)`.

### 5.6 The `feedback(reject)` reply gives the exact question (settles F-E4-6)

`SRC/reflection/_steps.py:QUESTION` becomes (`{own}` and `This rejection is {R}. ` as today):

```
Next: ask the user exactly ONE yes/no question that names an existing id: "About {first}: add "<the rule, in their words>" as a lasting rule? Yes or no." ({first} is one of {C ids}; for a repeat: "Same as R<j>: a one-off? Yes or no.", R<j> one of {R ids}). Change nothing in this turn: an "always ..." in the rejection is not their yes. On yes: define_service(owner="{owner}", name="{service}", add_acceptance=["<the rule>"], answers="{note}", about="<the id you asked about>", words="<their answer, verbatim>"). On no, a one-off or "as it is": feedback(task_id="{task}", verdict="reject", confirms="{note}", criterion=["none"], ["R<j>"] or ["C<k>"], source="human", note="<their answer, verbatim>").
```
- `{first}`: the first `C<k>` of the rejection's own `criterion` when it names one (the assistant's reading, which the user then confirms or
  not), else the literal `C<k>`. `{C ids}`: current criteria; `{R ids}`: the other assertions, or `none`. `{owner}`, `{service}`: the
  request's. The `QUESTION_FORM` of P2-OPEN-REJECTION is the quoted question with the same substitutions.
- **`amendment_step` and `NO_YES_YET` are removed** (`ServiceSteps` keeps `feedback_step` and `rework_step`): an amendment can no longer precede
  the yes, and the one text that named the new id (F-E4-6) is gone. MCP root `define_service` appends no step; `ScriptedSteps`
  (`SRC/mcp_server/testing.py`), the contract suite `test_contract_service_steps.py` and `test_steps.py` drop it.

### 5.7 Replies and docstrings

- **`define_service` reply** (services, so MCP and the CLI show it), after today's reply:
  - answer path: `Recorded as the user's answer to {R} (rejection {id}; your question named {about}): link {link id} names {ids}. {ids} {is|are} client-confirmed: a playbook revision citing {it|them} may add {its|their} words (rule (c)).`
  - user path: `Recorded as a change the user asked for on their own: "{clip_line(words, 160)}".` plus, when it added criteria, ` {ids} {is|are} user-initiated: {it travels|they travel} with every request but never admit{s} a playbook revision (rule (c)).`
- **Owner's amendment note**: one line after the changes: `The client's yes to {R} (about {about}) is recorded: {ids} {is|are} client-confirmed.` or `The client asked for this change on their own ("{words, 160}"): {ids} {is|are} user-initiated.`; the marks use `confirmed` read after the link write (`confirmed | set(ids)` on the answer path).
- **Root `define_service` docstring** = today's plus, after `An amendment that changes nothing is refused.`:
  `CHANGING THE CRITERIA (you, root): only as the user's answer after a rejection: answers=<the rejection's message id>, about=<the C or R id your one question named>, words=<their answer, verbatim> (it records their yes as the link itself); or, for a change the user asks for on their own outside any rejection, words=<their request, verbatim> alone (never admits a playbook revision). Every delivered request of the service needs its verdict first.` (wrapped at today's column).
- **Root `feedback` docstring**: the sentence from `confirms: the user's yes.` to `only this link counts as the client's.` becomes
  `confirms: the user's answer that changes no criterion ("no", "a one-off", "about C<k> as it is"): call again with the same task_id, verdict "reject", confirms=<the rejection's message id>, criterion ("none", "R<j>" or "C<k>"), source "human" and their answer verbatim as note; it records the link, not a new verdict. A yes that changes the contract is define_service(..., answers=<the rejection's message id>, about=<the id>, words=<their answer>), which records the link itself.`

### 5.8 No bypass

| Path | Reaches | Gate applies |
|---|---|---|
| MCP root `define_service` | `ServiceCommands.define_service` | yes |
| MCP agent `define_service` (no new arguments) | same; `actor != ROOT`, not root's amendment | not gated (agent clients' amendments are never `amended`, hence never (c)-eligible) |
| CLI `define-service` | same | yes: the human at the terminal passes `--words` (or `--answers/--about/--words`) like anyone |
| `Org.define_service` | same | yes |
| `apply_org` / `hirearchy apply` | `ServiceCommands.define_service` with `playbook=` | first definitions only (an existing service with `playbook` is refused today) |
| `feedback(confirms=...)` naming a `C<k>` | a link note | cannot make an amendment eligible (5.5) |
| `send` / `write` | messages without `criterion` / files outside `services/` | `criterion` is refused on `send` (S3); `orgfiles` does not own `services/**` |
| the assistant's shell writing `SERVICE.md` | outside the product | not preventable by the product (the user's machine); a hand-written version is read like any other, and a forged `answers` key with a `feedback(confirms=...)` link could make a criterion eligible. No product path writes a root acceptance amendment without a basis, so a legacy-shaped root version after 0a.2 can only come from such a write. E4 counted 0 shell writes under `services/` (STUDY "Clause 1 (b)"); E5 counts them (section 21). |

### 5.9 What P2 cannot enforce

That the question was shown, held one proposition, or that `words` are the user's. s3's question had no id; the replay passes `about="C3"`
as the assistant could have (gate 3 P2, "What it cannot enforce"). P2-WORDS-ARE-THE-REJECTION catches only a copy of the rejection.

## 6. P3, the partial form (D-E4-3; gate 3 P3, "A cheaper, partial alternative")

### 6.1 `progress` flags `blocked` results with client questions

`SRC/progress/_lines.py:CaseTaskLines._questions_to_ask`: `if result.status != "done"` becomes `if result.status not in ("done", "blocked")`;
the settling rules are unchanged (a human rework of the task or the client's verdict on the delivery ends the flag; a relayed rework does not,
0a.1 DR-17). `CaseTaskLines.line` computes `asked` for `done` and `blocked` results and appends the flag part
(`{n} question(s) for the client: ask the user before you copy or deliver`, unchanged text) for both. F-E4-4's `...-lead-96e9` is flagged.

### 6.2 The artifact path is withheld while questions are open

In `CaseTaskLines.line`, for a `done` or `failed` result: when `asked > 0` the part `artifacts: <paths>` is replaced by
`artifacts withheld (ask first)`; otherwise it is today's `artifacts: ...` / `no artifacts`. A `blocked` result has no artifact part, as today.
The path still appears in the result body (`inbox`, the message file): the partial form adds no `deliver` tool (D-E4-3).

### 6.3 Files of the deliverable folder the team did not deliver as checked

New Protocol in `SRC/reflection/api.py` (implemented by `SRC/reflection/_deliverables.py:FolderDeliverableChecks`):

```python
@runtime_checkable
class DeliverableChecks(Protocol):
    def findings(self, actor: str, service: str | None = None) -> list[DeliverableFinding]:
        """The files in the deliverable folder (``deliverable.path`` of the contract) of every service ``actor`` requests (or of ``service`` only)
        that differ from the team's last checked version, that the team never wrote, or that could not be read; settled ones are left out.
        Never reads outside the folder; never raises for an unreadable folder, file or history."""
```

```python
@dataclass(frozen=True)
class DeliverableFinding:
    service: str
    folder: str     # the folder as resolved
    name: str       # the file name inside it ("" for the folder itself)
    kind: str       # "differs" | "unknown" | "link" | "large" | "unreadable"
    artifact: str   # the team's artifact it was compared with ("" unless "differs")
    task: str       # the task whose done result last listed that artifact ("" unless "differs")
```
and a pure renderer `deliverables_note(findings) -> str` (`""` for none). Its text, one block per service:

```
Deliverable folder of `{service}` ({folder}): {n} file(s) the team did not deliver as checked. Tell the user what changed and why; never patch a deliverable yourself (send it back with revises):
- {name}: differs from {artifact} as the team checked it (task {task})
- {name}: never written by the team
- {name}: a link, not read (hirearchy reads only files inside the folder)
- {name}: not read (larger than 4 MiB)
- {name}: cannot be read ({error})
```
(at most 10 file lines, then `- and {k} more`); an unreadable folder is the single line
`Deliverable folder of `{service}` ({folder}) cannot be read ({error}).`

**Comparison basis.**
- *Checked versions*: for every case of the service, every task of the chain whose latest result is `done`, every org-relative path `P` of
  `artifact_paths(result.body)` (no leading `/`, no `..` segment, not a directory): the blob of `P` at the first org-git commit that holds the
  sender's sent copy of that result (the scheduler commits after every run, `RunSettlement.settle`, so that commit has the artifact as the
  team reported it). Without that commit (no repository, git missing, not committed yet): the current blob of the org file (best effort;
  section 22).
- *A file `F` of the folder* (bytes `b`, blob `blob_id(b, len(<the checked id>))`):
  - when some artifact has the basename of `F`: compare with the **last** checked version of that artifact (the latest done result that lists
    a path with that basename). Equal: no finding. Different: `differs`;
  - otherwise: equal to any checked version of any artifact of the service (a renamed copy): no finding; else `unknown` ("never written by
    the team").
  - Absolute (workspace) artifacts are not compared (no history): a file whose basename matches only such an artifact gives no finding.
- *Settled*: a `differs` finding is left out once its case has a verdict (any tier) recorded at or after the file's mtime (the timestamp in
  the verdict's message id, microseconds); an `unknown` one once the service has such a verdict. Files whose mtime is before the service was
  first defined (`Contract.created`) are ignored (the user's own older files).

**Path containment (`SRC/reflection/_deliverables.py:FsDeliverableFolder`, a private port `DeliverableFolder` in `reflection/_ports.py`).**
1. `raw = contract.deliverable.get("path")`; not a non-empty `str`: the service is skipped. `p = Path(raw).expanduser()`; not absolute (a
   hand-edited contract): skipped.
2. `folder = p.resolve(strict=False)` (normalizes `..`, follows a symlinked folder such as macOS `/tmp` -> `/private/tmp`); not an existing
   directory: skipped (no findings).
3. `os.scandir(folder)`, entries sorted by name, names starting with `.` skipped (`.DS_Store`), at most 200 entries; never recursive.
4. Each entry: `entry.is_symlink()` -> `link` (never followed, never read). Not `entry.is_file(follow_symlinks=False)` (directory, FIFO,
   socket, device) -> skipped, never opened. Otherwise `fd = os.open(entry.path, os.O_RDONLY | os.O_NOFOLLOW)` (closes the window in which the
   entry could be swapped for a link), `os.fstat(fd)` must be a regular file (`stat.S_ISREG`) and its size at most 4 MiB (else `large`), then
   read and close. The bytes never leave the process: only their blob id and the entry's mtime are kept.
5. `OSError` on `scandir` -> one `unreadable` finding for the folder; `OSError` on one entry -> `unreadable` for it (`ELOOP` from
   `O_NOFOLLOW` -> `link`).
Nothing outside `folder` is opened: the only paths read are `folder` itself and `folder/<name>` for names `scandir` returned.

**History reads** go through a private port `CheckedVersions` (`SRC/reflection/_ports.py`) implemented in `SRC/app` by `GitCheckedVersions`
over the new `snapshots.OrgHistory` (6.4) and `kernel.OrgLayout`:

```python
class CheckedVersions(Protocol):
    def at_result(self, result: Message, path: str) -> tuple[str, str] | None:
        """(commit, blob id) of ``path`` (org-relative) at the first commit that holds ``result``'s sent copy; None when unknown."""
    def current(self, path: str) -> str | None:
        """The blob id of the org file now; None when it is missing, not a regular file, or resolves outside the organization."""
    def text(self, commit: str, path: str, limit: int) -> str | None:
        """The text of ``path`` at ``commit`` (UTF-8, errors replaced); None when absent or longer than ``limit`` bytes."""
```
`GitCheckedVersions` memoizes `at_result` answers that are not `None` per (result id, path) for the life of the runtime (commits are immutable).

### 6.4 `snapshots.OrgHistory` (read-only)

New Protocol in `SRC/snapshots/api.py`, implemented by `SRC/snapshots/_git.py:GitOrgHistory(paths: OrgLayout, git: GitClient)`:

```python
@runtime_checkable
class OrgHistory(Protocol):
    """Read-only questions to the organization's git history. Every method answers None when there is no repository, no git, or no answer;
    none raises and none writes."""
    def first_commit_with(self, path: str) -> str | None:
        """The id of the oldest commit that added ``path`` (org-relative, ``/``-separated)."""
    def blob(self, commit: str, path: str) -> str | None:
        """The object id of ``path`` at ``commit``; None when it is no file there."""
    def text(self, commit: str, path: str, limit: int) -> bytes | None:
        """The bytes of ``path`` at ``commit``; None when absent or larger than ``limit``."""
```
`GitClient` (`SubprocessGit`) gains three read methods, all with `cwd=root`, `capture_output=True`, a 10 s timeout and `None` on a non-zero
exit, a timeout or `OSError`: `added_by(root, path)` (`git log --format=%H --diff-filter=A -- <path>`, last line), `object_id(root, spec)`
(`git rev-parse --verify --quiet <spec>`), `cat(root, obj, limit)` (`git cat-file -s <obj>` then `git cat-file blob <obj>`). Input rules
(enforced in `GitOrgHistory`, before any call): `path` is relative, has no `..` segment, does not start with `-`, and is always passed after
`--` (or inside `<commit>:<path>`); `commit` matches `[0-9a-f]{40}` or `[0-9a-f]{64}`. Anything else gives `None` without running git.

### 6.5 Surfaces

- `SRC/progress/_render.py:RootTaskReport` gets a 4th collaborator `deliverables: DeliverableChecks`; `render` appends
  `deliverables_note(findings(ROOT, service))` (split into lines) after the task lines and before `HumanQueue.lines()`. With `task_id`, only that
  task's service (none for a one-off task); without, every service root requests. `SRC/progress/_function.py:progress` passes
  `rt.deliverable_checks`; the wiring in `SRC/app/wire_progress.py` passes the provider.
- `SRC/mcp_server/_tools_identity.py` and `_tools_status.py`: `IdentityTools` and `StatusTools` get `deliverables: Provider[DeliverableChecks]`;
  for `me == ROOT`, not in setup mode, `whoami` and `status` append `"\n\n" + note` when non-empty, before the stale-skill note
  (`with_deliverables_note(text, ...)`, the pattern of `with_stale_skill_note`). Agents never see it.
- The CLI's `progress` shows it (same `ProgressReporter`); the CLI's `status` and `whoami` do not (the terminal is the user's own seat).
- Runtime fields: `deliverable_checks: DeliverableChecks` in `SRC/app/fields_reflection.py`, `org_history: OrgHistory` in
  `SRC/app/fields_snapshots.py`, and (section 7) `judged_versions: JudgedVersions` in `SRC/app/fields_services.py` beside `service_evidence`
  (a port of `services` that `reflection` implements; `wire_reflection` provides it). ARCHITECTURE section 3 lists the three Protocols, so
  `app/tests/test_runtime_fields.py` requires the fields.

### 6.6 What P3 partial cannot enforce

The assistant can still copy before asking (the path is in the result body) and can still patch: the patch is shown afterwards in every
`progress`, `status` and `whoami` until a verdict follows it. Items nobody flagged (10.3(c)) are D-E4-5's measured rate, not a refusal.

## 7. P4: a human rework starts from the version the client judged (D-E4-4; gate 3 P4)

### 7.1 The rule

`SRC/services/_request.py:RuleServiceRequester.request` gains `base: str | None = None` (`ServiceCommands.request`, `ServiceRequests`,
`RuleServiceCommands`, `Org.request`, MCP root `request` and CLI `request --base {delivered,latest}` pass it). After the `revises` check:

1. `base` given and not in `("delivered", "latest")`: P4-BASE-VALUE.
2. `base` given and not (`actor == ROOT`, `revises` given, `source == "human"`): P4-BASE-WHERE.
3. `actor == ROOT`, `revises`, `source == "human"`: `judged = self._judged.base(contract.owner, service, revises)` (a new port, 7.2).
   `judged is not None` and `base is None`: P4-NEEDS-BASE. `judged is None`: `base` is accepted and changes nothing (no section; the MCP reply
   says so).
4. The body gets the base section of 7.3 (`TextRequestBodies.body(..., base=(base, judged))`; the package-private `RequestBodies` Protocol
   follows).

### 7.2 The judged delivery and what relayed reworks changed after it

New Protocol in `SRC/services/api.py` (implemented in `SRC/reflection/_judged.py:CaseJudgedVersions(history, mail, versions: CheckedVersions)`):

```python
@dataclass(frozen=True)
class JudgedBase:
    task: str                     # the task whose delivery the client judged
    result: str                   # that delivery (a result id)
    commit: str                   # the org-git commit that holds it; "" without history
    relayed: tuple[str, ...]      # the relayed reworks of the case sent after it
    changed: tuple[str, ...]      # its artifacts (org paths) that differ now
    texts: tuple[tuple[str, str], ...]  # (path, judged text) of each changed artifact that could be read, at most 20 000 characters each

@runtime_checkable
class JudgedVersions(Protocol):
    def base(self, owner: str, service: str, revises: str) -> JudgedBase | None:
        """For a rework of ``revises``: the delivery the client judged and what relayed reworks changed after it; None when nothing needs a base."""
```

`CaseJudgedVersions.base`:
1. The case: `history.case_of(<the task revises>)`; none: `None`.
2. The judged delivery `J`: the task `t` of the case's latest human-tier verdict (by message id), and `t`'s latest result with an id lower than
   the verdict's; with no human-tier verdict, the latest `done` result of a task of the chain whose `source` is not `"relayed"` (the request or
   a human rework). None: `None`.
3. `relayed` = the tasks of the chain with `source == "relayed"` and an id greater than `J`'s. Empty: `None`.
4. For each org-relative artifact `P` of `J` (`artifact_paths`): `checked = versions.at_result(J, P)`. `P` is **changed** when
   `checked` is known and `versions.current(P) != checked.blob`, or, without history, when a result of a task in `relayed` lists `P`.
   No changed path: `None`.
5. `texts`: `versions.text(commit, P, 20_000)` for each changed `P` with a commit.

s2r: `J` = f230's result `...-lead-5314` (judged by `...-root-a9fd`), `relayed` = (`...-root-43b8`,), changed = (`lead/writer/work/2026-10-05-memo.md`,):
the human rework needs a base. s1r #24 (`...-root-3559`) and s3 #31 (`...-root-ff36`) likewise. E4's other human reworks do not.

### 7.3 The base section of the task body (texts)

`base="delivered"`:
```
## Base: the version the client judged
The client's corrections apply to the version they judged: the delivery of task {task} (result {result}{, org-git commit <12 hex>}). Relayed rework {ids} (the assistant's own reading, not the client's) changed {paths} after it. Start from that version: restore each file below to it, then make only the changes this request asks for.

### {path}, as the client judged it
{fence}
{text}
{fence}
```
`{fence}` is a run of backticks one longer than the longest run in `{text}` (at least 3). A changed path without text reads
`### {path}: not included ({no org history | longer than 20000 characters}); it is in the organization's git history{ at commit <12 hex>}.`

`base="latest"`:
```
## Base: the current version
The client's corrections apply to the current version, which keeps the changes relayed rework {ids} (the assistant's own reading, not the client's) made to {paths} after the delivery they judged (task {task}). Keep those changes unless this request says otherwise.
```

MCP root `request` reply (`_requested`), after the case total: `base delivered: the lead starts from the version the user judged.`,
`base latest: the changes of your own relayed rework stay in it: tell the user so.`, or, when a base was given but none was needed,
`base: not needed (no relayed rework changed the delivery the user judged).` (detected by the absence of the `## Base: ` heading,
`services.BASE_HEADING`, in `msg.body`). CLI: `request {id} -> {to} (service {s}, budget {b}, base {base})` when given.

### 7.4 Refusal texts (new; constants in `SRC/services/_request.py` and `SRC/dispatch/_assigner.py`)

- **P4-NEEDS-BASE**:
  ```
  refused: since the delivery the client judged (task {task}, result {result}), relayed rework {ids} (your own reading, not the client's) changed {paths}. Say which version the user's corrections apply to: base="delivered" (the lead restores the version they judged{, org-git commit <12 hex>}, then applies their corrections) or base="latest" (the relayed changes stay; tell the user). Nothing was sent.
  ```
- **P4-BASE-VALUE**: `base must be "delivered" or "latest": {base}`
- **P4-BASE-WHERE**: `base goes only with a rework the user asked for: revises=<an earlier request of this service>, source="human".`
- **P4-USE-REQUEST** (closure; section 20, D2): `{revises} is a request for the service `{service}`: send it back with request(service="{service}", inputs=..., revises="{revises}", source=...) so the rework stays in its case under the contract (and names its base when a relayed rework changed the delivery). Nothing was sent.`

### 7.5 No bypass

`RuleServiceRequester.request` is reached by MCP root `request`, the CLI `request` (whose `--revises` defaults `source` to `human`) and
`Org.request`. The other way root reworks a task is `delegate(revises=...)` (MCP `delegate`, CLI `task --revises`, `Org.delegate`), all through
`SRC/dispatch/_assigner.py:RuleTaskAssigner.delegate`: when `actor == ROOT`, `revises` is given and `fields_for` answers a `service`
(the revised task is a service request), it raises P4-USE-REQUEST before sending. Agents' delegations are not human reworks.

### 7.6 The tier travels into rework delegations

`SRC/services/_rework.py:ServiceReworkContext.fields_for(actor, revises)` keeps the service fields and, for `actor != ROOT`, adds
`"source": <tier>`: the `source` of the latest task `actor` received (`type == "task"`, not from `runtime`) whose `trace` equals the revised
task's `trace` and that has no final result from `actor` (`latest_results(mail.sent(actor))`: none or `blocked`), when it is `"human"` or
`"relayed"`. It is the tier of the work the agent is doing in that case (a lead's writer task revises the writer's earlier task, which carries
no service and no tier, so copying from the revised task would never fire: section 20, D1).

`SRC/dispatch/_sender.py:provenance_source` gains `inherited: str | None = None`: for `actor != ROOT`, `type == "task"`, `revises` set,
`source is None` and `inherited in SOURCES`, it returns `inherited`. An agent's own `source` is refused exactly as today (S1); `inherited`
comes only from `RuleTaskAssigner.delegate` (`fields.get("source")`), never from a tool argument. `MessageSender.send` gains the keyword
`inherited: str | None = None` (`RuleMessageSender`, `dispatch.testing.RecordingSender`); its docstring's provenance paragraph adds: "A task of an
agent that revises another carries the tier its sender works under (``inherited``, from ``ReworkContext``): the runtime's copy, never the agent's
declaration." s2r: `...-lead-608b` carries `source: relayed`, `...-lead-0e90` `source: human`.

### 7.7 What P4 cannot enforce

That the lead restores the file (gate: "still LLM behaviour"); without history the judged text is not in the task. `base="latest"` relies on
root telling the user.

## 8. D-E4-6: root instructions and SKILL.md

### 8.1 `ROOT_INSTRUCTIONS` (`SRC/mcp_server/_instructions.py`)

Two lines are added (the skill line and the reject order) and six parentheticals whose content SKILL.md carries are cut, so the text fits.
Unified diff against `3815813` (the rest is unchanged):

```
-- Use only this organization: never look for, create or modify another (no other paths or ORG_ROOT).
-- Never claim the organization did work unless hirearchy tools show it.
-- If a hirearchy tool fails, tell the user instead of substituting another mechanism.
+- Use only this organization: never look for, create or modify another.
+- Never claim the organization did work unless hirearchy tools show it; if a tool fails, tell the user, never substitute.
+- Before you build an org or rate a delivery, activate the hirearchy skill.
 - `whoami` and `status` show the state; ...
 - Services: `services` (check it before building a new org), `request`, `feedback` (rate a delivery), `define_service`.
+  On a reject: `feedback` first, then ONE yes/no question naming an id, then the change (`define_service(answers=...)`).
 When the user asks for an org, team or agents for a goal:
 1. Ask what you need in ONE message. Propose defaults only where a generic one exists; ASK for any list not
-   given (scope items, source files), never invent. Default deliverable place: a new
-   `deliverables/` folder in the current directory (say so). Also ask: format, length, exact checkable criteria,
-   sources/web, workspace and tests (code), budget in runs, models (all claude-sonnet-5.5; if cheaper: keep the lead and final verifier strong;
-   the lead decides how every other run is spent), review, approval.
+   given, never invent. Default deliverable place: a new `deliverables/` folder here (say so). Also ask: format,
+   length, exact checkable criteria, sources/web, workspace and tests (code), budget in runs, models (all claude-sonnet-5.5;
+   if cheaper: keep the lead and final verifier strong; the lead decides how every other run is spent), review, approval.
 ...
-   first check `status` for stranded runs and `reclaim` them (or tell the lead to).
+   first check `status` for stranded runs and `reclaim` them.
 ...
-   itself when the work is done (start again for more work); `stop` only if the user cancels, declines
-   more budget or you hand over an unverified result (say the task stays open). Final answer: as short as asked.
+   itself when the work is done; `stop` only if the user cancels, declines more budget or you hand over an
+   unverified result (say the task stays open). Final answer: as short as asked.
```

Measured with the worktree's Python on the exact candidate text: raw template **2 589** characters (test `< 2700`, today 2 558); at the
reference path (`"/" + "r" * 59`) **2 666** (test `< 2700`, today 2 635; 34 characters of headroom); with a 200-character path **2 807** (test
`< 2900`); 26 lines (unchanged), longest line 124. Every needle pinned today (`test_instructions.py`, `test_finish_rules.py`,
`test_reclaim_tool.py`, `test_blueprint_tools.py`, `test_round7.py`, `test_skill_services.py`) was checked present. Where each cut lives on:
"no other paths or ORG_ROOT" (SKILL 0), "scope items, source files" (SKILL 1.1), "in the current directory" (SKILL 1.2 and its "here"), "or
tell the lead to" (SKILL 4: "a lead does it on its own team"), "start again for more work" (SKILL 4 and 5.7). New needle test
`test_root_instructions_name_the_skill_and_the_reject_order` (`SRC/mcp_server/tests/test_instructions.py`): `activate the hirearchy skill`,
``On a reject: `feedback` first, then ONE yes/no question naming an id, then the change``.

### 8.2 SKILL.md (125 lines; net 0 per replacement)

| # | Lines at `3815813` | Becomes | Lines |
|---|---|---|---|
| K1 | 83-85 (step 4, rework bullet) | `- Never edit the org's artifacts to "fix" them: send the work back with `delegate(to=<top agent>, title=..., goal=<required changes>,` / `  acceptance=<the criteria, verbatim>, revises=<task id>)` (a service request: `request(service, inputs, revises=<task id>)`), or ask the user. If `progress` says the scheduler is stopped` / `  ("finished") and you sent more work, call `start()` again. Pass source="human" only on a rework the user asked for (the default is relayed); if a relayed rework changed the file after their verdict, also base="delivered" (what they judged) or base="latest" (say so).` | 3 -> 3 |
| K2 | 92 (step 5 item 3, first line) | `3. A done or blocked report's "Questions for the client:" (ambiguous items; `progress` flags them and withholds the path): ask them in plain words, with any question from item 2, in ONE` | 1 -> 1 |
| K3 | 95 (step 5 item 4) | `4. Then copy the deliverable to the requested path (the plan lists this step) and check it exists and matches. If `progress`, `status` or `whoami` name a file there the team did not deliver as checked, tell the user what changed and why.` | 1 -> 1 |
| K4 | 104-109 (step 5 item 6, from `another, make the item`) | block below | 6 -> 6 |

K4:
```
   another, make the item the clarification that settles both. "Always ..." is not their yes: ask the item first, and never pass `criterion`
   on the rejection itself. On yes: `define_service(owner, name, add_acceptance=[<the new criterion>])` with `answers=<the rejection's message id>`,
   `about=<the id you asked about>` and `words=<their answer, verbatim>` (and `remove_acceptance` for a clarification): it records their yes; tell
   the user the resulting criteria. On no, a one-off or "as it is": `feedback(..., source="human", confirms=<the rejection's message id>)` with criterion
   "none", the R id or the existing C id. A change they ask for on their own, outside a rejection: `words=` alone. An owner's note with a question for the client is no new question (only your one item per
   reject asks one): read it with `inbox`, go on, and never reply to it or mention it. Never edit SERVICE.md or PLAYBOOK.md yourself.
```

Pinned needles kept (raw or flattened, checked against the replacement text): `` `define_service(owner, name, add_acceptance=[<the new criterion>])` ``,
`the resulting criteria`, `Never edit SERVICE.md or PLAYBOOK.md yourself`, `confirms=<the rejection's message id>`, `only your one item per
reject asks one`, `an owner's note with a question for the client is no new question`, `read it with `inbox`, go on, and never reply to it or
mention it`, `make the item the clarification that settles both`, `"always ..." is not their yes: ask the item first`, ``never pass `criterion`
on the rejection itself``, `pass source="human" only on a rework the user asked for`, `"questions for the client:"`, `` `progress` flags them ``,
`with any question from item 2, in one message before you deliver`, `copy nothing until they are answered`, `4. then copy the deliverable`, and
the order `Reply briefly` before ``record\n   `feedback(``. The ten tests that assert `<= 125` lines stay green (0a.1 8.1 lists them).
New needle test `test_the_skill_records_the_answer_with_define_service_and_names_the_base` (`SRC/skill/tests/test_skill_org_growth.py`):
`answers=<the rejection's message id>`, `words=<their answer, verbatim>`, `` `words=` alone ``, `base="delivered"`, `withholds the path`,
`did not deliver as checked`, plus `<= 125` lines. Each replacement lands with the commit of its behaviour (section 18).

## 9. D-E4-6: a throttled run is not charged and is retried once (F-E4-8)

### 9.1 Detection (facts, in the launcher: `SRC/kiro/_launch.py`, standard library only)

`RenderState` gains `calls: dict[str, tuple[str, str, bool]]` (toolCallId -> (ACP `kind`, `rawInput.tool_id` or `""`, whether `rawInput` is a
tool load: a `tool_ids` list and no `tool_id`)), `effects: int = 0`, `throttled: bool = False`.
- `tool_call` records the triple; `tool_call_update` with `status == "completed"` adds 1 to `effects` unless the call is read-only: its kind
  (from the update, else the recorded one) is one of `read`, `search`, `think`, `fetch`; or it is a tool load; or its tool id is one of
  `READ_ONLY_TOOL_IDS = ("hirearchy::inbox", "hirearchy::read", "hirearchy::org_read", "hirearchy::status", "hirearchy::health",
  "hirearchy::progress", "hirearchy::whoami", "hirearchy::services", "hirearchy::observe")`. Unknown kinds and unknown tools count as effects
  (fail safe: charged as today). A failed call is no effect.
- `runError` sets `throttled` when `data.retryErrorType`, `data.data.retryErrorType` or the compact message (spaces removed) carries
  `"retryErrorType":"THROTTLING"` (the s2 line 179 form: the message ends `(code -32000): {"errorType":"ModelThrottleError","retryErrorType":"THROTTLING",...}`).
- `finish(state)` emits, after any flushed partial line, `# kiro: throttled by the model service (retryErrorType THROTTLING); tool effects: none`
  (or `...; tool effects: {n}`) when `throttled`. Constant `THROTTLE_MARK`; it starts with `# kiro:` like every launcher line, never with a
  run-log closing mark. Rendered transcript lines are unchanged (V3 design 5.2 table).
- `SRC/kiro/api.py` exports the pure parser `throttled_without_effect(tail: str) -> bool` (the exact `...tool effects: none` line on a line of its
  own); `READ_ONLY_TOOL_IDS` equals `observability._trace.READ_ONLY_TOOLS` prefixed `hirearchy::`, pinned by a test (the launcher may not import
  it).

### 9.2 The decision (in the scheduler; the charge stays derived)

The run log still exists, so `RunLogReader.count` and every reader of runs count the run (it happened). It is not **charged** because a runtime
credit note returns its run: `budget` is derived as received - handed down - runs, and the note is received budget. No reader of run logs
changes, no file kind is added, and the credit is an immutable note.

- New private port `ThrottleCredits` (`SRC/scheduler/_ports.py`), implemented by `SRC/scheduler/_throttle.py:CreditingThrottles(logs:
  RunLogReader, mail: MailboxReader, delivery: MessageDelivery)`: `credit(run: RunRecord) -> str` returns `""` (not credited), `"free"` or
  `"counted"`:
  1. `tail, _ = logs.tail(run.log, 4096, 80)`; `not throttled_without_effect(tail)`: `""`.
  2. Belt and braces from the runtime's own record: any message in `mail.sent(run.addr)` whose id starts at or after the run's stem (first 21
     characters compared) means the run had an effect: `""`.
  3. Deliver `budget.run_credit(run.addr, run_id)`: `Message(sender=RUNTIME, to=addr, type="note", budget=1, wake=False, title=f"{RUN_CREDIT_TITLE}: {run_id}", body=...)`,
     body: `Your run {run_id} ended on a model-service throttle (retryErrorType THROTTLING) before any tool effect, so it is not charged: this note returns its run. Your messages are back in your inbox; the run is started again.`
  4. `"counted"` when the agent's previous run (the log before `run.log` in `logs.files(addr)`) was credited too (a received runtime note titled
     `f"{RUN_CREDIT_TITLE}: {addr}@{previous stem}"`), else `"free"`.
  Any `OSError`/`OrgError` in 1-4: `""` (charged as today) and the console line `{addr}: throttle credit not given: {error}`.
- `SRC/scheduler/_reaper.py:RunSettlement` gets `throttles: ThrottleCredits`; in `settle`, for `not ok`, before the failure count:
  `kind = self._throttles.credit(run)`. `"free"`: no `failures.failed` (the retry is not a failure), console
  `{addr}: run throttled by the model service before any tool effect: not charged, retried`. `"counted"`: console `... not charged` and
  `failures.failed(...)` as today. `""`: today's path. `batches.end(addr, ok=False)` already returns the batch to the inbox (at least once), and
  the reaper runs before the starter in each tick, so the credit is there before the next admission (`BudgetGate.admit` sees the run back).
- **Retried once** = one retry free of the failure count. A second throttle in a row is still not charged but counts as a failure; after it the
  existing rule applies (the batch is retried while failures < `max_failures`, then the agent is paused and its parent and root are told).
  A throttle storm therefore costs no budget and at most `max_failures + 1` runs before a human sees it.
- **Conservation** (`SRC/observability/_checks/_budget.py:BudgetConserved`): credits enter budget from the runtime, so
  `handed down + credited == held + used + returned + dropped (+ in delivery)`. `credited` = the budget of every run credit
  (`kernel.is_run_credit` on the front matter) in a received box of a live agent, plus `RetiredArchive.credited()` (new, `SRC/agents/_retired.py`:
  the same over the retired trees' received boxes; `RetiredArchive` 3 -> 4 methods). The equation text gains ` + {c} credited` after `handed
  down {h}` only when `c > 0`, so every existing check text and golden is unchanged.

### 9.3 Tests

- `SRC/kiro/tests/test_launch.py`: a new recorded stream `SRC/kiro/tests/golden/kiro-streams/f-e4-8-throttle.jsonl`, built from
  `EV/s2/org-kiro-sessions/68b8df2b7d941cfd/sess_c6fe5695-efac-4329-bb67-552425b7dc61/messages.jsonl` (the four tool calls with their kinds,
  `rawInput` and statuses: tool load completed, `hirearchy::org_read` completed, `read_file` kind `read` completed, `hirearchy::write` failed) and
  `EV/s2/run-logs/lead-reviewer/20261022T202454859379.log` line 179 (the `runError` message, verbatim): the last line is
  `...; tool effects: none`. Variants: the write completed (`tool effects: 1`); an unknown kind (counted); a `runError` without THROTTLING (no
  mark); the mark never starts with a closing mark; `throttled_without_effect` on each.
- `SRC/scheduler/tests/test_throttle.py` (unit, fakes): free credit; counted credit after a credited previous run; a message sent during the run
  (no credit); no mark (no credit); an unreadable log (no credit, console line).
- `SRC/scheduler/tests/test_loop_throttle.py` (integration, `testkit.scheduler_loop` with the fake agent): `FAKE_THROTTLE_RUNS=1` makes the first
  run print the mark and exit 1, then work normally: the agent's budget after the run equals the budget before it; one credit note; the retry ran
  and finished; `.runtime/failures.json` has no failure for it. `FAKE_THROTTLE_RUNS=2`: two credits, one failure counted. A run that `send`s
  before the throttle: charged, failure counted.
- `SRC/observability/tests/test_checks.py`: conservation with a live credit and with a retired agent's credit.

## 10. Deterministic replays from E4's raw evidence

New file `TESTS/e2e/test_org_growth_0a2.py` with a small kit `TESTS/testkit/e4_replay.py`:
- `evidence(path) -> (meta, body)` reads a file under `EV` or `EV3` from the repository (`testkit.REPO / "studies" / ...`) with
  `kernel.split_frontmatter`; a missing file fails the test (never a skip). `tool_call(stream, n)` reads call `#n`'s JSON arguments from a
  stream's `contract-loop.txt` or `assistant-tool-calls.txt` line `ARGS: {...}`.
- `scripted_report(w, task_id, result_file, artifact_texts)`: writes each artifact (org path -> text, from `EV/<stream>/memos/versions/...`) in
  the org, reports the task through the lead's MCP `report` tool with the summary, artifacts and lessons parsed from the evidence result's
  `## ` sections, then commits through `org.runtime.snapshotter` (the `OrgSnapshotter` field) as `RunSettlement.settle` does after a run (real
  git, as the existing e2e tests use). A scripted writer reports each delegation the scripted lead makes, so no task is left open.
- Root's calls go through root's in-process MCP server; the lead's `revise_playbook` through the lead's. No scheduler, no LLM, no network; each
  test builds its own organization in `tmp_path`, with the stream's contract v1 (`acceptance`, `deliverable`, `budget`, `inputs` from the
  `SERVICE.v1` file) and playbook v1, and the deliverable path pointed at `tmp_path / "deliverables"`.

| Test | Built from (all under `EV` unless `EV3`) | Asserted outcome |
|---|---|---|
| `test_s1r_t5_an_amendment_before_the_verdict_is_refused` | `s1r/service/history--SERVICE.v1.md`; `s1r/playbook/PLAYBOOK.4435fd0.md`; `s1r/msgs/sent/20261022T182945409755-root-ed94.md`; `s1r/msgs/read/20261022T184536871337-lead-4f4d.md`; `s1r/memos/versions/memo-2026-10-05.v2.a358b76.md`; `s1r/contract-loop.txt` calls #21, #22, #23; `s1r/turn-05.txt` | #21's arguments as made, before #22: **P2-UNRATED** naming `...-ed94`; with `words=<Lena's T5>` added: P2-UNRATED again. After #22 (`criterion=["C5"]`): the reply has `About C5: add` and `answers="{#22's id}"`; #21 + `words=<T5>`: **P2-OPEN-REJECTION**; + `answers, about="C5", words=<T5>`: **P2-WORDS-ARE-THE-REJECTION**; `SERVICE.md` still v1 after each. The compliant path (#21 + `answers`, `about="C5"`, `words=<#23's note>`) is admitted: v2, a link from root naming `C8, C9`, `services` shows neither as "(not confirmed)". |
| `test_s1r_v3_and_v4_without_a_verdict_are_refused` | as above, plus `s1r/msgs/sent/20261022T191407596413-root-114d.md`, `s1r/msgs/read/20261022T192346320735-lead-fa63.md`, `s1r/memos/versions/memo-2026-10-12.v1.dfce3a4.md`, `s1r/service/history--SERVICE.v2.md` and `v3.md`, `s1r/contract-loop.txt` #44, #45 | from v2 (compliant T5/T6) with memo 2 delivered and unrated: #44 (+ `words`) and #45 (+ `answers=<T5 rejection>`, `about="C9"`, `words`) both **P2-UNRATED** naming `...-114d`; after a recorded reject of memo 2, #45 with the T5 rejection is **P2-ANSWERED**; `SERVICE.md` stays v2 and `C9` current. |
| `test_s1r_t8_the_artifact_path_is_withheld_while_the_question_is_open` | `s1r/msgs/sent/...-root-114d.md`; `s1r/msgs/read/...-lead-fa63.md` (its `Questions for the client:` block); `s1r/memos/versions/memo-2026-10-12.v1.dfce3a4.md`; `s1r/client-questions.txt` (progress #36); `s1r/deliverables-log.txt` (#40's `sed`) | `progress(task_id=114d)` has `artifacts withheld (ask first)` and `1 question for the client: ask the user before you copy or deliver`, and not `lead/writer/work/memo-2026-10-12.md`. After #40's edit is applied to a copy in the deliverable folder (`implemented a deploy freeze` -> `decided on a deploy freeze`): `progress`, `status` and `whoami` name `memo-2026-10-12.md: differs from lead/writer/work/memo-2026-10-12.md as the team checked it (task ...114d)`. After a human rework (or the client's verdict): the path is shown again; after a verdict recorded after the edit, the finding is settled. Also `s3/msgs/read/20261022T222916707473-lead-96e9.md` (blocked, with a question): flagged. |
| `test_s2r_the_wrong_rule_is_refused_and_the_human_rework_needs_a_base` | `s2r/service/history--SERVICE.v1.md`, `history--SERVICE.v2.md`; `s2r/playbook/PLAYBOOK.2b6438a.md` (v1), `PLAYBOOK.6b06123.md` (v2); `s2r/revise-playbook-attempts.txt` (v2 arguments verbatim); `s2r/msgs/sent/` `...-root-f230`, `...-root-43b8` (and `s2r/injection/request-args.json`), `...-root-a9fd`, `...-root-342a`; `s2r/msgs/read/` `...-lead-5314`, `...-lead-c3dd`; `s2r/msgs/lead-sent/` `...-lead-608b`, `...-lead-0e90`; `s2r/memos/versions/2026-10-05-memo.v2.0aa3d3b.md` (judged, Marta 2026-10-14) and `v3.d8fd320.md` (injected, Marta none); `s2r/contract-loop.txt` (#31) | (1) the injected rework's writer delegation (a rework of the writer's task, sent while the lead works the relayed `43b8`) carries `source: relayed`; (2) the lead's service sections for the batch `[a9fd, 342a]` (`org.runtime.service_prompt_sections.prompt_sections("lead", batch)`, what the
scheduler puts in the lead's prompt) show `lessons (from a relayed rework, not the client's): "Rework needed`; (3) after `a9fd`, `request(revises=f230, source="human")` without base: **P4-NEEDS-BASE** naming `...-43b8` and `lead/writer/work/2026-10-05-memo.md`; (4) with `base="delivered"`: the task body has `## Base: the version the client judged`, the commit that first holds `lead/sent/<5314>.md`, and the judged text with `| Marta |` ... `| 2026-10-14 |` and no `Open questions`: Marta's date survives; the writer delegation for it carries `source: human`; (5) #31 with `answers=a9fd`, `about="C3"`, `words="Yes, add it."`: admitted, link names `C9`; (6) the lead's `revise_playbook` with v2's exact content and `["R1", "C9"]`: **P1-REFUSED**, containing `are not C9's words` and both vague-deadline lines (`Flag any vague deadline as `none``, `Vague deadlines:`); playbook stays v1; (7) v1 with its `none yet: ...` line replaced by `- C9: <C9's text>`, evidence `["C9"]`: v2 `admitted: c`, root's note lists `[C9] - C9: ...`. |
| `test_s3_the_answered_amendment_is_admitted_and_only_its_words_enter_the_playbook` | `s3/service/history--SERVICE.v1.md`; `s3/playbook/PLAYBOOK.f6d34a7.md` (v1), `PLAYBOOK.dd2d1da.md` (v2); `s3/revise-playbook-attempts.txt`; `s3/contract-loop.txt` #12, #23, #30, #31, #37, #38; `s3/injection/request-args.json`; `s3/msgs/read/` `...-lead-de22`, `...-lead-ffba`, `...-lead-40d8`; `s3/memos/versions/memo-2026-10-05.v2.a526bb3.md`, `v3.b7f83c8.md` | #31 (human rework after the injected `fe20` changed the memo): P4-NEEDS-BASE, then admitted with `base="delivered"`; #37 with `answers=<#30's id>`, `about="C3"`, `words=<#38's note>`: **admitted** (the s3 flow), the product's link names `C8`; the lead's attempt 1 (v2 content, evidence `C8` + the product's link id + `88b2`): not "unknown evidence" (F-E4-7) but **P1-REFUSED** listing the riders (`(d) a 'Next meeting' footer`, `No other sections`, `(C1–C8) and the regression list verbatim`) and the changed step 4; v1 plus `- C8: <C8's text>`, evidence `[<the link id>]`: admitted `c` (a link-note id is evidence). |
| `test_e3_turn_5_an_amendment_in_the_reject_turn_is_refused` (replaces `test_11` of `test_org_growth_0a.py`) | `EV3/service/SERVICE.v1.md`; `EV3/assistant-tool-calls.txt` calls #24 (feedback, `criterion: ["C6", "C3"]`) and #25 (define_service, lines 668-670); `EV3/turn-05.txt` | after #24: #25's arguments: **P2-NEEDS-WORDS**; + `words=<T5>`: **P2-OPEN-REJECTION**; + `answers=<#24's id>`, `about="C6"`, `words=<T5>`: **P2-WORDS-ARE-THE-REJECTION**; `SERVICE.md` v1; the reply of #24 names `About C6: add`. |

D-E4-7 names s1r T5, s1r T8 and the s2r chain for E5; they are the first, third and fourth rows. The throttle replay is in 9.3.

## 11. Data model and the architecture rules

**New records (immutable)**: the product-written `confirms` link note (root -> owner; the shape `feedback(confirms=...)` writes today); the
runtime run-credit note (runtime -> agent, `budget: 1`, `wake: false`). **New keys on an existing immutable record**: `answers`, `about`,
`words`, `initiated` in a contract version's frontmatter (5.4); `source` on an agent's rework task (7.6, an existing `Message` field, now
copied by the runtime). **Derived, never stored**: line attribution (`Admission.lines`), confirmation and eligibility (`confirmed_criteria` with
the basis join), `AmendmentBasis`, `JudgedBase`, `DeliverableFinding`s, the throttle decision (from the run log and the mailbox). **Not added**:
no ledger, no `.runtime/*.json`, no file kind, no `Message` field, no event field, no frontmatter key on `PLAYBOOK.md`.

| Rule | How 0a.2 complies |
|---|---|
| R1-R2 | New public names in each `api.py` and `__all__`: `services`: `line_key`, `changed_lines`, `quoting_lines`, `AmendmentBasis`, `Rejection`, `JudgedBase`, `JudgedVersions`, `BASE_HEADING`, `ServiceEvidence.amendment_basis`; `reflection`: `DeliverableChecks`, `DeliverableFinding`, `deliverables_note`, `rated`, `delivered_unrated`, `Verdict.link_notes`, `Case.lesson_sources`; `snapshots`: `OrgHistory`, `blob_id`; `kernel`: `artifact_paths`, `RUN_CREDIT_TITLE`, `is_run_credit`; `kiro`: `throttled_without_effect`; `budget`: `run_credit`; `agents`: `RetiredArchive.credited`. Implementations stay in `_*.py`; the app adapter `GitCheckedVersions` lives in `SRC/app`. |
| R3-R5 | No new edge: `reflection` uses `services`, `mail`, `kernel` (git through its own port, implemented in `app`); `services` uses `dispatch` (`MessageSender` for `LinkNotes`); `progress` uses `reflection`; `mcp_server` uses `reflection`; `scheduler` uses `kiro`, `budget`, `mail`, `delivery`; `observability` uses `budget`, `agents`; `agents` uses `kernel`. All allowed in ARCHITECTURE 2.2 today; no contract or row changes. |
| R6 | Every new collaborator is typed by a Protocol: `LinkNotes`, `JudgedVersions`, `ServiceEvidence` (definer), `DeliverableChecks` (progress, MCP tools), `CheckedVersions`, `DeliverableFolder` (reflection), `OrgHistory`/`GitClient` (snapshots), `ThrottleCredits`, `RunLogReader`, `MailboxReader`, `MessageDelivery` (scheduler). |
| R7 | `ServiceEvidence` 3 -> 4; `ServiceSteps` 3 -> 2; `GitClient` 4 -> 7; `OrgHistory` 3; `DeliverableChecks` 1; `JudgedVersions` 1; `RetiredArchive` 3 -> 4; `MessageSender`, `ServiceCommands` (5), `ReworkContext` (1) keep their method counts (signatures widen). `Notices` (8, at the cap) is not touched: the credit text is `budget.run_credit`. |
| R8 | Contract suites: new `snapshots/tests/test_contract_org_history.py` (real git, memory fake), `reflection/tests/test_contract_deliverable_checks.py`, `services/tests/test_contract_judged_versions.py` (reflection implementation over the fs world, memory fake); extended `test_contract_service_evidence.py` (`amendment_basis`, `admit(lines=)`), `test_contract_git_client.py`, `test_contract_message_sender.py` (`inherited`), `test_contract_rework_context.py` (`source`), `test_contract_retired_archive.py` (`credited`), `test_contract_service_steps.py` (no `amendment_step`). Fakes in the same commits: `services.testing.AdmittingServiceEvidence(basis=...)`, `NoJudgedVersions`/`FixedJudgedVersions`, `reflection.testing` world fields, `snapshots.testing.MemoryOrgHistory`, `mcp_server.testing.ScriptedSteps` (no `amendment`), `FixedDeliverableChecks`, `dispatch.testing.RecordingSender`, `blueprint.testing` command fakes, `cli/tests/_fakes.py`. Runtime fields: `deliverable_checks`, `judged_versions`, `org_history`. |
| R9 | No new writer and no new file. `SERVICE.md` keys: `services` (`FsServiceStore`); notes: `mail` through `delivery`; run logs untouched. Reads outside the org: only the contract's deliverable folder (6.3, contained) and the git repository of the org (inside it). |
| R10-R11 | mypy strict; RED -> GREEN -> REFACTOR per commit (section 18). |
| R12 | Not applicable (refactor-principles D1); goldens are regenerated deliberately (section 16). |
| R13 | Responsibilities unchanged: `reflection` "derives the history of service requests ... from the files" (judged versions and deliverable checks are that history); `snapshots` "snapshots the organization directory in git" (reading its history is part of it); `scheduler`, `kiro`, `budget` unchanged. |

## 12. Error handling

| Operation | Failure | Kind | Caller receives | Logged |
|---|---|---|---|---|
| `revise_playbook` | offending lines (P1) | recoverable | `OrgError` P1-REFUSED; nothing written | `tool.call` refused event, as every refusal |
| `revise_playbook` | the cases cannot be read | as today | the exception | as today |
| `define_service` (root) | any P2 refusal | recoverable | `OrgError` with the text of 5.3; nothing written | `tool.call` refused |
| `define_service` | `amendment_basis` raises `OrgError`/`OSError` | recoverable, fail closed | P2-UNREADABLE | `tool.call` refused |
| `define_service` | the link note cannot be written after the contract was (`OrgError`/`OSError`) | recoverable | `OrgError`: `the contract of `{name}` is now v{n} (it answers rejection {id}), but the link that records the user's yes could not be written ({error}). Record it with feedback(task_id="{task}", verdict="reject", confirms="{id}", criterion=[{ids}], source="human", note=<their answer, verbatim>).` That link makes the criteria confirmed (the version answers that rejection, 5.5). | `tool.call` failed; no snapshot commit by the CLI (the next commit includes the version) |
| `define_service` | the marks' `confirmed` read fails | advisory (0a.1 3.3) | the amendment as usual, every amended criterion marked | no |
| `request` (root) | P4 refusals | recoverable | `OrgError` (7.4); nothing sent | `tool.call` refused |
| `request` | `JudgedVersions.base`: git unavailable or slow (> 10 s per call) | recoverable | the fallback of 7.2 step 4; the base section says `not included (no org history)` | no |
| `request` | mail or cases unreadable | as today | the exception | as today |
| `delegate` (root) | P4-USE-REQUEST | recoverable | `OrgError`; nothing sent | `tool.call` refused |
| `progress`, `status`, `whoami` | the deliverable folder or one file unreadable | recoverable | a finding of kind `unreadable` in the note | no |
| `progress`, `status`, `whoami` | `DeliverableChecks.findings` raises `OrgError`/`OSError` (catalog or mail) | recoverable | the text without the note (the `_step` rule of 0a.1: any other exception is a bug and propagates) | no |
| `OrgHistory` methods | no repository, git missing, timeout, non-zero exit, invalid input | recoverable | `None` | no |
| scheduler settle | `ThrottleCredits.credit` fails (`OSError`/`OrgError`) | recoverable | the run is charged as today and counted as a failure | console line `{addr}: throttle credit not given: {error}` |
| kiro launcher | an unknown event shape | never raises (V3 design 5.2) | no mark, or effects counted (fail safe) | the transcript |

## 13. Validation of external inputs

| Input | Required | Type and limits | On failure |
|---|---|---|---|
| `define_service(answers=)` (root) | with `about`; only on root's acceptance amendment | `str`, stripped, 1-80 characters, no whitespace; a human-tier rejection of this service recorded by root | P2-PAIR, P2-NOT-AN-AMENDMENT, P2-NOT-A-REJECTION, P2-ANSWERED |
| `define_service(about=)` | with `answers` | one id `C<k>` or `R<k>` (case-insensitive, upper-cased); `none` is not an answer that changes the contract | P2-PAIR, P2-ABOUT |
| `define_service(words=)` | on every root acceptance amendment | `str`, stripped, 1-1000 characters (`FEEDBACK_MAX`), verbatim; not the rejection's own words | P2-NEEDS-WORDS, P2-WORDS-LONG, P2-WORDS-ARE-THE-REJECTION |
| any of the three from an agent | never | - | P2-ROOT-ONLY |
| CLI `--answers/--about/--words` | as above | `--words` accepts `@FILE` (read with `TextSource.read`, as `--notes`) | the same refusals; exit 1, `error: ...` on stderr |
| `request(base=)` | when `JudgedVersions.base` is not `None` for a human rework | `"delivered"` or `"latest"` | P4-NEEDS-BASE, P4-BASE-VALUE, P4-BASE-WHERE |
| CLI `--base` | as above | `choices=("delivered", "latest")` (argparse refuses others) | argparse usage error, exit 2 |
| a revision's content lines (P1) | - | any text; compared by `line_key` | P1-REFUSED |
| `deliverable.path` of a contract (read time) | no | absolute `str`; resolved; must be an existing directory | skipped (no findings) |
| files of the deliverable folder | - | direct regular files, not hidden, not links, <= 4 MiB, at most 200 entries | `link`, `large`, `unreadable` findings; others skipped |
| artifact paths of results (P3, P4) | - | org-relative, no `..`, not a directory; resolved inside the org | not compared |
| git inputs (`OrgHistory`) | - | relative path without `..` or leading `-`; commit `[0-9a-f]{40}` or `{64}` | `None`, git not run |
| a `runError` event (launcher) | - | any JSON; THROTTLING detected in three places (9.1) | no mark |
| a run log tail (scheduler) | - | the last 4 096 bytes | no credit |

## 14. Invariants and their owners

| Invariant | Owner (layer) | Why there |
|---|---|---|
| A revision under rule (c) adds only the cited confirmed criterion's words; under rule (b) only lines tagged with a qualifying id | `reflection.CaseServiceEvidence.admit`, called by `services.RulePlaybookReviser` with `services.changed_lines` | the gate already owns admission; the reviser is the only writer of `PLAYBOOK.md` versions, reached by MCP and the facade |
| Lines are compared one way | `services.line_key` | the reviser, the gate and `quoting_lines` share it |
| Root changes the criteria only with a basis; one answer per rejection; verdicts before amendments | `services.RuleContractDefiner` | the only writer of `SERVICE.md`; every surface reaches it (5.8) |
| A user-initiated criterion is never (c)-eligible; only the product's link confirms an answered one | `reflection.confirmed_criteria` (basis join), read by the gate, step 3, the amendment note and `services` | one rule for every reader, as 0a.1's `confirmed_amendments` |
| The link that records an answer has one shape | `services.LinkNotes` | `feedback(confirms=)` and `define_service(answers=)` write it the same way |
| A human rework after relayed changes names its base | `services.RuleServiceRequester`; `dispatch.RuleTaskAssigner` refuses root's `delegate` of a service request | the requester builds every service rework; the assigner is the only other way root reworks |
| A rework delegation carries its sender's tier | `dispatch.provenance_source` (stamp), with the facts from `services.ServiceReworkContext` | provenance is dispatch's rule; the tier is service-case knowledge |
| `progress` withholds the path while questions are open | `progress.CaseTaskLines` | the one place the line is built |
| Deliverable-folder reads stay inside the folder | `reflection.FsDeliverableFolder` | one reader; the containment is tested there |
| A throttled run with no tool effect is not charged | `scheduler.CreditingThrottles` (decision) over `kiro`'s mark (facts) and `budget.run_credit` (the note); `observability` counts credits in the conservation check | the scheduler settles runs; budget stays derived |

## 15. Zero denominators and empty cases

0a.2 adds no division and no ratio; every new number is a count. The empty cases:
- **No playbook yet**: the first version is exempt (no line stage). **No changed line** (removal or reorder only): today's admission.
- **No confirmed criteria**: `added` is empty; rule (c) gives no `c_part`; G1/G2 as today. **No rejections**: `AmendmentBasis.rejections == ()`;
  the answer path is P2-NOT-A-REJECTION ("none yet"); the user path is open (when every delivery is rated). **No cases**: `unrated == ()`.
- **No artifact yet** (no done result): P3 compares nothing; files of the folder newer than the service and unsettled are `unknown`;
  P4 has no judged delivery (`None`, no base needed). **Empty folder, missing folder, no `path`**: no findings. **No git history**: P3 compares
  with the current org file; P4 uses the result-listing fallback and includes no text.
- **No previous run** (first run of an agent): the throttle credit is `"free"`. **`max_failures`** >= 1 (settings), so the counted path pauses.
- For E5's measures (section 21) every rate is reported as `k of n`, and `n = 0` is reported as `n/a (0 of 0)`, never as 0 % or 100 %.

## 16. Golden impact (predicted; each regenerated file is named with its line count in its commit)

Methods (0a.1 section 14): **G** `HIREARCHY_UPDATE_GOLDEN=1 uv run pytest tests/golden -k <test>` then review `git diff`; **H** a hand edit of the
changed sentence only (colocated files have no switch; placeholders kept).

| Commit | File | Method | Why |
|---|---|---|---|
| A3 | `TESTS/golden/expected/services/service_and_playbook_files.md` | G | the scenario's rule (b) revision line `4. Cut to 600 words before reporting.` becomes `... reporting [C1].` (1 line in the PLAYBOOK v2 section) |
| A4 | `TESTS/golden/expected/prompts/service_owner_reflect.txt` | G | step 3 (4.6) |
| A4 | `SRC/reflection/tests/expected/sections_history_then_new_request.txt`, `sections_playbook_and_rejection.txt`, `sections_rejection_and_rework.txt`, `sections_second_playbook_and_new_request.txt` | H | step 3 (1 line each) |
| A4 | `TESTS/golden/expected/mcp/surface_manager.txt` | G | the `revise_playbook` docstring |
| B4 | `TESTS/golden/expected/mcp/surface_root.txt`, `surface_root_unbound.txt`, `surface_root_setup_mode.txt` | G | root `define_service` (arguments, docstring), root `feedback` docstring |
| B4 | `TESTS/golden/expected/cli/help_define-service.txt`, `SRC/cli/tests/expected/help_define-service.txt` | G, H | `--answers`, `--about`, `--words` |
| B4 | `TESTS/golden/expected/cli/help_feedback.txt`, `SRC/cli/tests/expected/help_feedback.txt` | G, H | the `--criterion` help gains `(an answer that changes no criterion)` (D16) |
| B5 | `SRC/cli/tests/expected/define_service_amend_acceptance.txt` | H | the scenario (`SRC/cli/tests/_scenario.py`) adds `--words Add-a-summary.`; the output gains the "Recorded as a change the user asked for on their own" line (scenario deliveries, if any, get their verdict first) |
| D3 | the three `surface_root*.txt` | G | root `request` gains `base` and its docstring sentence |
| D3 | `TESTS/golden/expected/cli/help_request.txt`, `SRC/cli/tests/expected/help_request.txt` | G, H | `--base` |
| E1 | the three `surface_root*.txt` | G | `ROOT_INSTRUCTIONS` (8.1) |
| - | `TESTS/architecture/org_signatures.json` | by hand (registry) | `define_service` (`answers`, `about`, `words`), `request` (`base`) |
| E2 | `SRC/kiro/tests/golden/kiro-streams/f-e4-8-throttle.jsonl` | **new** fixture (not a regeneration) | 9.3 |

Distinct regenerated files: 17 (`surface_root.txt`, `surface_root_unbound.txt`, `surface_root_setup_mode.txt`, `surface_manager.txt`,
`service_owner_reflect.txt`, 4 `sections_*`, `service_and_playbook_files.md`, 2 `help_define-service.txt`, 2 `help_feedback.txt`,
2 `help_request.txt`, `define_service_amend_acceptance.txt`), plus the signature registry and one new fixture. Scenario changes made so their goldens stay
byte-identical: `TESTS/golden/test_golden_events.py:80` gains `words="Keep it to 300 words."` (`events/line_shapes.txt` unchanged: no event field
is added). Must stay byte-identical (the commit stops until a diff is explained): `surface_manager_without_service.txt`, `surface_worker.txt`,
`surface_builtin_*`, every `progress`, `cli/progress*`, `cli/status*`, `cli/services*`, `cli/feedback*`, `messages/*`, `events/*`, `kiro/*`,
`plans/*`, `files/*`, `charters/*`, `services/services_text_root.txt`, the reflection `services_*`, `totals_*` and `digest_*`, the
observability and dashboard goldens (no scenario has a deliverable `path`, a blocked result with questions, a relayed lesson, a throttle or a
credit; checked: `BRIEF` in `TESTS/golden/scenarios.py`, `testkit/services_world.py`, `testkit/dash_fixtures.py` has no `path`).

## 17. Test-site rules (existing tests the refusals touch)

- **Rule W** (P2, a test only needs *an* amendment): pass `words="<a short request>"` (user-initiated). **Rule A** (the test needs a
  (c)-eligible amendment): reject a delivery, then `define_service(..., answers=<the rejection id>, about=<a current id>, words="Yes, add it.")`.
  `TESTS/testkit/services_world.py:confirmed_amendment` becomes exactly Rule A (it no longer calls `feedback(confirms=...)`).
- **Rule V** (P2-UNRATED): a test that amends after an unrated delivery records the verdict first.
- **Rule T** (P1): a revision under rule (b) tags each added line with its id (`[C6]`); under rule (c) its added lines are `- C<k>: <text>`.
  `admit(...)` unit calls without `lines` are unchanged.
- **Rule B** (P4): a human rework after a relayed rework that changed the artifact passes `base`; a root `delegate(revises=<service request>)`
  becomes `request(service, inputs, revises=..., source=...)`.
- **Rule F** (P3): `progress` assertions on a result with open questions expect `artifacts withheld (ask first)`;
  `progress/tests/test_lines.py:test_a_blocked_result_is_not_flagged` (0a.1) is inverted to `test_a_blocked_result_with_questions_is_flagged`.

Known sites (found by `grep -rn "add_acceptance\|remove_acceptance\|add-acceptance\|remove-acceptance"` and `revise_playbook(` with non-empty
evidence; the coder applies the same rules to anything else the full suite shows, naming each site in its commit message):
`SRC/app/tests/test_services_facade.py`; `SRC/cli/tests/_scenario.py`, `test_service_commands.py` (`test_commands_services.py` uses fakes: only
the argument plumbing); `SRC/mcp_server/tests/test_service_amend_tool.py`, `test_service_tools.py`, `test_tools_services.py` (also
`test_root_define_service_reply_carries_the_amendment_step`, removed with 5.6); `SRC/reflection/tests/test_case_service_evidence.py`,
`test_prompt_sections.py`, `test_reports.py`, `test_steps.py`, `test_digest.py`, `test_contract_service_steps.py`;
`SRC/services/tests/test_amend.py`, `test_contract_service_catalog.py`, `test_contract_service_commands.py`, `test_events.py`, `test_playbook.py`;
`SRC/skill/tests/test_skill_services.py` (needle unchanged, 8.2); `TESTS/architecture/facade_cases.py`; `TESTS/golden/test_golden_events.py`,
`test_golden_files.py`; `TESTS/testkit/services_world.py`; `TESTS/e2e/test_org_growth_0a.py`: `chain()` (block 6: `... state it [C6].`),
`test_6`, `test_7` (rewritten to Rule A: `define_service(add_acceptance=[added], answers=n2, about="C6", words="Yes, add it.")`; the
refusal-before-confirmation assertion becomes "a revision citing C7 with any other line is refused"; the admitted revision is
`PLAYBOOK_V1 + "- C7: " + added`), `test_11` (replaced by the E3 replay, section 10).

## 18. Commit plan (each green; `count.txt` raised where tests are added; conventional commits)

The labels (A1 ... E5) are the ones the golden table (section 16) and the test-site rules use.

1. `docs(design): add org-growth phase 0a.2 design` (this file).
2. (A1) `feat(services): line_key and changed_lines compare playbook lines on their words` (pure; unit tests).
3. (A2) `feat(reflection): a confirms link-note id is evidence for its criterion` (`Verdict.link_notes`; F-E4-7).
4. (A3) `feat(reflection): rule (c) admits only the cited criterion's words and rule (b) only tagged lines` (`admit(lines=)`, `Admission.lines`,
   P1-REFUSED, root's note; Rule T sites; golden `service_and_playbook_files.md`).
5. (A4) `feat(reflection): step 3, the amendment note and the revise_playbook docstring say how lines are admitted` (6 goldens).
6. (A5) `feat(reflection): the digest marks lessons from relayed reworks` (`Case.lesson_sources`).
7. (A6) `feat(services): an amendment that removes a criterion names the playbook lines that quote it` (`quoting_lines`, `diff(quoting=)`).
8. (B1) `feat(services): a contract version records its basis` (`Contract`/`Criterion` fields, `number_criteria(basis=)`, `stored_basis`; parse
   only, behaviour unchanged).
9. (B2) `feat(reflection): only the product's link confirms an answered amendment; a user-initiated one never counts`
   (`confirmed_criteria(cases, criteria)`, marks).
10. (B3) `feat(reflection): amendment_basis lists the rejections and the deliveries without a verdict` (`rated` and `delivered_unrated` move to
    `reflection.api`; `ServiceEvidence.amendment_basis`; fakes).
11. (B4) `feat(services): define_service records the user's answer and writes its link` (`answers/about/words` through services, `Org`, MCP root
    (split registration) and CLI; `LinkNotes` shared with `feedback`; the replies and docstrings of 5.7; validation of the given values only,
    no new refusal of a call without them; goldens: 3 `surface_root*`, 2 `help_define-service`, 2 `help_feedback`).
12. (B5) `feat(services): root changes the acceptance criteria only as an answer or a user-initiated request` (the refusals of 5.3; Rules W/A/V;
    `services_world.confirmed_amendment`; `test_7`; golden `define_service_amend_acceptance.txt`; scenario `test_golden_events.py`; the replay
    kit `TESTS/testkit/e4_replay.py` and the replays `test_s1r_t5_...`, `test_s1r_v3_and_v4_...`, `test_e3_turn_5_...`; `test_11` removed).
13. (B6) `feat(reflection): the rejection reply gives the exact question; amendment_step is gone` (`QUESTION`, `ServiceSteps` 3 -> 2; F-E4-6).
14. (B7) `docs(skill): the answer is recorded with define_service` (K4; needle test).
15. (C1) `feat(kernel): artifact_paths reads a result's artifacts` (`progress.artifacts_of` delegates).
16. (C2) `feat(progress): blocked results with client questions are flagged and the artifact path is withheld while they are open` (Rule F; K2).
17. (C3) `feat(snapshots): OrgHistory reads the organization's git history` (`GitClient` read methods, `blob_id`, contract suite).
18. (C4) `feat(reflection): deliverable checks name the files the team did not deliver as checked` (`DeliverableChecks`, `FsDeliverableFolder`,
    `CheckedVersions` and its `app` adapter, runtime fields).
19. (C5) `feat(progress,mcp_server): progress, status and whoami show the deliverable note` (K3; replay `test_s1r_t8_...`).
20. (D1) `feat(dispatch,services): rework delegations inherit the tier of their sender's work` (`fields_for` source, `provenance_source(inherited=)`).
21. (D3) `feat(services): a human rework after relayed changes names its base` (includes D2, `JudgedVersions` in reflection; `base` through
    services, `Org`, MCP root and CLI; the base section; P4-NEEDS-BASE, P4-BASE-VALUE, P4-BASE-WHERE; Rule B; goldens: 3 `surface_root*`,
    2 `help_request`; K1).
22. (D4) `feat(dispatch): root reworks a service request with request` (P4-USE-REQUEST; Rule B for `delegate`; replays `test_s2r_...` and
    `test_s3_...`, which assert P1, P2 and P4 together and so land when the last of them exists).
23. (E1) `docs(instructions): activate the skill before building or rating; the reject order in one line` (3 goldens; needle test).
24. (E2) `feat(kiro): the launcher marks a throttled run and counts its tool effects` (new fixture stream).
25. (E3) `feat(kernel,budget): run credit vocabulary` (`RUN_CREDIT_TITLE`, `is_run_credit`, `run_credit`).
26. (E4) `feat(scheduler): a throttled run with no tool effect is credited and retried once` (`ThrottleCredits`; unit and loop tests).
27. (E5) `feat(observability,agents): budget conservation counts run credits` (`RetiredArchive.credited`).
28. `docs: README and ARCHITECTURE for phase 0a.2` (README "Services and reflection" and "Kiro integration" paragraphs updated in place;
    ARCHITECTURE section 3 interface blocks of `kernel`, `snapshots`, `agents`, `dispatch`, `services`, `reflection`, `kiro`, `budget`, and 3.37).

Order: A (2-7) and C (15-19) are independent of each other; B (8-14) needs A; D (20-22) needs A and B; E (23-27) is independent, except that 23
comes after 11 and 21 (the same three goldens are regenerated in each, and each commit lists its own diff). Commits 4, 9, 12, 16, 21 and 26 run
the full pytest before they are made; every other commit its targeted set plus a search of `src/` and `tests/` for each text it changes; each
package ends with the full `scripts/check.sh`.

## 19. Amendments to the 0a and 0a.1 designs (what is superseded)

| Design, section | Was | Becomes |
|---|---|---|
| 0a 5.3, rule (c) / rule (b) | a revision citing an eligible id is admitted whole | admitted line by line (4.1); lines are compared by `line_key` |
| 0a 5.1, S1 ("every message of an agent stays unstamped") | agents' messages carry no `source` | an agent's rework task carries the inherited tier (7.6); an agent still cannot declare one |
| 0a 4.1/4.2, the MCP and CLI surfaces | `define_service`, `request` without the new arguments | `answers`, `about`, `words`; `base`; root's `delegate` of a service request is refused |
| 0a.1 3.1, "`define_service` gets no `source` path" | user-initiated amendments impossible to mark | the user path with `words=` (D-E4-2; the 0a.1 section 18 backlog item, with the user's verbatim words as it asked) |
| 0a.1 3.1, `confirmed_criteria(cases)` | any human-tier link confirms | the basis join of 5.5 |
| 0a.1 3.4, `amendment_step`, `NO_YES_YET` and the `define_service` reply step | after an amendment, what records the yes | removed (5.6); the definer's reply says what was recorded |
| 0a.1 3.4, `QUESTION` | "before define_service ... then record the answer: feedback(confirms=...)" | the exact question; yes -> `define_service(answers=...)`; no/one-off -> `feedback(confirms=...)` |
| 0a.1 3.4, CLI `feedback --criterion` composing a link | the user's yes | unchanged; it no longer makes an amendment (c)-eligible unless that amendment answers the same rejection |
| 0a.1 4.1, step 3 and the rule (c) note line | "a revision citing it is admitted" | "may add its words", one line each (4.6) |
| 0a.1 5.2, the progress flag | `done` results only | `done` and `blocked`; the path is withheld while open (6.1, 6.2) |
| 0a.1 18, "`define_service`, `request`, `feedback` and delivery refuse nothing new" | no new refusal | the refusals of 4.2, 5.3, 7.4 (D-E4-1, -2, -4); `feedback` and delivery still refuse nothing new |
| 0a.1 21.11 (DR-27), what `confirms` may name | unchanged | unchanged |
| V3 design 5.1/5.2 | the launcher's lines | one more `# kiro:` line (9.1); the rendered lines are unchanged |
| `runs/api.py`, "the existence of the file is what consumes one run of budget" | true | still true; a credit note returns a throttled run (9.2) |

## 20. Deviations from e4-gate.md and e4-decision.md, with reasons

- **D1 (P4, mechanism of "the tier travels").** The gate says `fields_for` "adds `source`". Copied from the revised task it would never fire:
  a lead's writer task revises the writer's earlier task, which carries no service and no tier (s2r `...-lead-608b` revises `...-lead-7124`,
  both without `source`). The tier is taken from the work the delegating agent is doing in that case (its latest open received task with the
  same trace, 7.6). The behaviour the decision asks for (the lead's and the writer's tasks show "relayed") holds; only rework delegations
  carry it, as decided.
- **D2 (P4, closure, a refusal the decision does not name).** Root's `delegate(revises=<a service request>)` is refused with P4-USE-REQUEST.
  Without it a human rework could bypass the base refusal through `delegate` (MCP, CLI `task`, `Org.delegate`), against the brief's "no refusal
  can be bypassed". `request(revises=...)` is the documented service rework and what every E4 assistant used.
- **D3 (P2, addition).** P2-WORDS-ARE-THE-REJECTION refuses `words` that repeat the rejection's own note (or 4+ of its words in a row). The
  gate's conditions would admit E3 T5 and s1r T5 if the assistant pasted the reject as the answer; the check is deterministic and cheap, and it
  does not claim to prove the words are the user's (5.9).
- **D4 (P2, definitions the gate leaves open).** "Every delivered request of the service has a verdict" is read per case: the latest task of a
  case whose result is `done` must be rated (any verdict on it or later). A per-task reading would refuse s2r's and s3's legitimate flows (their
  first deliveries and the injected reworks were never rated). It applies to the user-initiated path too, and the user path is refused while a
  human rejection awaits its answer: otherwise s1r T5 (#21, before #22) and #44/#45/#54 would pass as "user-initiated". The decision admits
  user-initiated amendments "outside a rejection"; an unanswered rejection is read as "inside".
- **D5 (D-E4-6 throttle, mechanism and "once").** "Not charged" is a runtime credit note that returns the run (budget stays derived; the run
  log stays the record of the run), not an exclusion of the log from the count. "Retried once" is one retry free of the failure count; a
  second throttle in a row is credited but counted, and the existing `max_failures` rule bounds the rest. "No tool effect" is decided by the
  launcher from kiro's own tool events (read-only kinds and read-only hirearchy tools; anything unknown counts) plus the runtime's record (no
  message sent during the run).
- **D6 (P1, "what the user sees").** The gate says `services` and root's note show the added lines. Root's note does; `services` does not (it
  would change the listing goldens of every scenario that revises a playbook, and it is not in D-E4-1's scope list). 0b's timeline shows version diffs (gate section 4 item 2).
- **D7 (P1, comparison).** Lines are compared case-insensitively (`casefold`) besides letters and digits: a capitalization fix is not a word
  change. A changed heading or step counts as a changed line (strict, as the gate's "a change of any word counts").
- **D8 (P2, the link's ids).** The product's link names every criterion the amendment added (s1r's T5 answer would confirm C8 and C9; E4's
  link named only C9), or the removed ones when it adds none. `about` is kept in the contract version, not in the link's `criterion`.
- **D9 (P1, removed criterion).** The note names the quoting lines; no admission rule lets the owner remove them on the removal's strength.
  Backlogged (section 22).
- **D10 (P3, settling and scope of the folder check).** The decision gives no end to the note. It ends when the case gets a verdict after the
  file changed (the user judged the file as it is); files older than the service are ignored; the folder is read flat (no subfolders);
  workspace (absolute) artifacts are not compared; a file equal to an older checked version of a renamed artifact is not reported.
- **D11 (P4, when the base is needed).** "Changed after the judged delivery" is decided by content (the judged blob against the current file),
  so a relayed rework that did not touch the file needs no base; without git history, by whether a relayed result lists the artifact. With no
  human-tier verdict the judged delivery is the latest done result of a non-relayed task.
- **D12 (D-E4-6 root instructions, condensation).** Six parentheticals were cut to fit the budget (8.1); their content is in SKILL.md.
- **D13 (D-E4-6 third bullet, F-E4-9).** The injection script's polling loop is E5's harness, not product code: not in this batch; listed for E5
  (section 21).
- **D14 (P2, removal of `amendment_step`).** The decision says the `feedback(reject)` reply settles F-E4-6; the other text of F-E4-6
  (`NO_YES_YET`) is removed rather than reworded, because no root amendment can precede its answer any more.
- **D15 (P3, surfaces).** The deliverable note is in root's MCP `progress`, `status` and `whoami` and in the CLI's `progress` (one
  `ProgressReporter`); the CLI's `status` does not show it: the terminal is the user's own seat, and "tell the user" is addressed to root.
- **D16 (P2 and 0a.1's CLI composition).** `hirearchy feedback <task> reject --criterion C<k>` (source human) still records the verdict and a
  link in one command (0a.1 3.4). That link is the rejection's answer ("about C<k>"), so a later `define-service --answers <that verdict>` is
  P2-ANSWERED. A terminal user who wants a lasting rule rejects without `--criterion` and then runs `define-service ... --answers <id> --about
  C<k> --words "..."`; the `--criterion` help gains `(an answer that changes no criterion)` (golden `help_feedback.txt`, both copies, B4).

## 21. What E5 must check (pre-registration input)

E5 is D-E4-7's study: E4's protocol plus D-E4-5, D-E4-8 and the new tools, at least 3 valid streams, the workspace skill copy, and the
deterministic replays of section 10 (at least s1r T5, s1r T8 and the s2r chain) passing at the E5 commit.

- **Model set (D-E4-8).** Every live seat runs claude-sonnet-5.5: the assistant, the lead, the reviewer or checker, the writer and every other
  org agent. E4's L-MODEL line (claude-sonnet-4.6 and claude-haiku-4.5) is dropped; if the assistant proposes another model, Lena's fixed line is
  "Please use claude-sonnet-5.5 for everyone." There is no substitution: if claude-sonnet-5.5 is not listed when a stream starts, the stream does
  not start and the manager is told. Each run log's `--model` is checked against the set, as in E4. **E5 is not model-matched to E4**: it is a
  gate on its own pre-registered rules, and its report says so; E4's lead- and reviewer-side failures may be partly model-caused, its
  assistant-side ones are not (the assistant was already claude-sonnet-5.5). No product change follows: the product already defaults every
  agent to claude-sonnet-5.5 and uses tiers only when the user asks (SKILL.md step 1 item 6, `mcp_server/_instructions.py`,
  `blueprint/_example_texts.py`); 0a.2 changes none of them (8.1 keeps the model sentence of step 1 word for word).
- **Throttling** is more likely with one model for every seat: the not-charged, retry-once rule of section 9 and E4's H8 validity rule apply as
  before, and E5 reports the throttle counts below per stream.

Specific to 0a.2:

- **Clause 3, restated by D-E4-5 (pre-register this wording):** "Every item the team flagged is asked before delivery." A flagged item is an
  item of a `Questions for the client:` block of a `done` or `blocked` result that `progress` flagged; it is asked before delivery when the turn
  that asked it ends before the first write of that case's deliverable into the contract's deliverable folder after the result (D6 of the
  protocol, with amendment 1's in-place and Python writes). Count also the copies made while `progress` showed `artifacts withheld (ask first)`.
- **Reviewer ambiguity recall (D-E4-5: a measured rate, not a pass rule; taken with claude-sonnet-5.5 as the reviewer, D-E4-8):** over every
  reviewed version that contains an answer-key item that
  fits a criterion's words but not its purpose (the Marta row of memo 3 and every item the key marks so), the number the reviewer listed as
  `ambiguous` on its first review of that version, reported as `k of n` per stream and pooled, and `n/a (0 of 0)` when no such item was
  reviewed. Also report whether the lead forwarded it and whether `progress` flagged it. Not part of the gate.
- **Clause 1 (P1):** for every admitted revision, every added or changed line is the cited criterion's words (c) or carries a qualifying id
  (b), checked from the version diff; count P1 refusals and classify each refused line by D12 ((i) contradicts, (ii) unsupported, evidence);
  a refused (evidence) line is a false refusal and is reported. Count digests that showed `(from a relayed rework, not the client's)`, and
  revisions that cited a link-note id (no "unknown evidence").
- **Clause 2 (P2):** per human reject, whether the turn order was verdict -> one item naming an existing id -> answer -> `define_service(answers=...)`;
  count every P2 refusal by kind (5.3), the amendments admitted by answer and by `words=` alone, and every `about` that names an id the shown
  item did not (declared provenance; read from the turn files); count `feedback(confirms=...)` answers ("no", one-off, "as it is"); count the
  P2-UNRATED refusals whose unrated delivery was a relayed rework the user never saw (D4's friction).
- **No regression and P4:** count human reworks that needed a base, which base was chosen, what the user was told for `latest`, and whether the
  lead's writer restored the judged version (memo versions); s2r's Marta date in particular. Check that every lead writer task made during a
  relayed rework carries `source: relayed`.
- **P3 detection:** count deliverable notes shown and whether root told the user in the same turn; count hand edits (D6 writes that differ from
  the team's checked version) and whether a verdict followed them.
- **Throttle:** count runs with the throttle mark, the credits given (`Run not charged:` notes), free retries, counted throttles; no run with a
  tool effect may be credited; the conservation check (`observe check`) stays green.
- **Skill activation (D-E4-6):** whether the assistant called `disclose_context` for the skill before its first `propose_org` or `feedback`, as a
  stratifier (E4's s1r did not).
- **Harness (F-E4-9):** the injection script's polling loop is fixed and its md5 recorded before the first stream.
- Every rate is `k of n`; a zero denominator is `n/a`, never a pass.

## 22. Out of scope, backlog and risks

- **Out of scope** (decision and brief): the full `deliver` tool; Phase 0b (quality view, alarms, cause typing, the timeline); item-level
  playbook operations; the retro brief; F-E4-10 (blocked results keep their runs); the injection script (E5's harness).
- **Backlog:** an admission rule for removing playbook lines that quote a criterion an answered amendment removed (D9); the added lines in
  `services` (D6); a `read` of an org file at a commit for leads without shell (P4 gives the text in the task instead); recursing into
  subfolders of the deliverable folder.
- **Risks and known limits:**
  - Declared provenance remains (5.9, 7.7): the product cannot see the conversation.
  - P1 is strict: a lead's correct elaboration of a confirmed rule is refused until rule (b) or a contract change; E5 counts false refusals.
  - P2 adds one turn per lasting rule (the decision accepts it) and refuses amendments while a delivery is unrated; a relayed rework that came
    back `done` as a case's latest task must be rated before the contract changes (D4).
  - P3 compares against the org-git commit after the reporting run; between the report and that commit (during the lead's run) the current file
    is used. Without git the comparison is with the current file, so an in-place rework in progress can show `differs`.
  - P3 notes repeat in every `progress`, `status` and `whoami` until a verdict follows the change: deliberate, so a hand edit stays visible.
  - The throttle detector depends on kiro's event shapes (`kind`, `rawInput.tool_id`, `runError`); a change in them degrades to "charged as
    today", never to a wrong credit (unknown kinds count as effects).
  - `GitCheckedVersions` runs git subprocesses on `progress`; it memoizes known answers and only asks for artifacts whose basename is in the
    folder.
