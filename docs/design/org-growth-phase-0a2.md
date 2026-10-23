# Org growth, Phase 0a.2: the enforcement batch after E4 (technical design)

Status: design, revision 3, amended by the manager's decision of 2026-10-23 (DR-41 to DR-46, Appendix A.3) and the planner's corrections (A.4) (revision 1 was `31bf5ab`, revision 2 `1b385a2`; the 27 findings of review pass 1 and the 13 of pass 2, DR-28 to DR-40, are resolved in Appendix A, under the manager's binding directives of 2026-10-23 for this revision). Where Appendix A.3 or A.4 conflicts with a section above, the appendix wins. Branch
`feat/org-growth-phase-0a2` off `main` `3815813`; worktree `/Volumes/workspace/hirearchy/.worktrees/org-growth-0a2`.
Baseline (`.agents/tasks/baseline.md`): 14 415 passed, 5 skipped, 3 deselected, 1 xfailed; import-linter contracts kept; `scripts/check.sh` exit 0
(734 s). `skills/hirearchy/SKILL.md`: 125 lines. Root instructions: 2 635 characters at the reference path (`/` + 59 `r`), 2 558 raw.

Sources of truth (read in full):
- `docs/research/org-growth/phase-0a1/e4-decision.md` (binding): D-E4-1 to D-E4-7; the owner's D-E4-8 (every live-study seat runs
  claude-sonnet-5.5) and D-E4-9 (claude-sonnet-5.5 is the floor at `--effort high`; built as the separate "org agent floor" batch in
  `.worktrees/org-agent-floor`, which supersedes D-E4-8's "the product needs no change"). "The decision" below. D-E4-9 is not in 0a.2's
  scope; it shapes section 8.3 (merge order) and section 21 only.
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
   (the answer to a rejection; the product writes the `confirms` link itself and refuses a second answer, by amendment or by `confirms`) or
   `words=` alone (user-initiated, never (c)-eligible). Every delivered request needs its verdict first. Root cannot retire a service to escape
   that while a verdict or an answer is missing, and retiring the owning agent does not reset the record: defining the same service of the
   same agent again continues its contract, playbook and cases (5.10). The `feedback(reject)` reply gives the exact question, with the id
   root names as its reading on the rejection.
3. **P3, partial** (D-E4-3). `progress` flags `blocked` results with client questions and withholds the artifact path ("ask first") while they
   are open; `progress`, `status` and `whoami` name the files of a contract's deliverable folder that differ from the team's last checked
   version or that the team never wrote, and tell root to tell the user. No `deliver` tool.
4. **P4, the judged version** (D-E4-4). `request(revises=X, source="human")` on a case whose artifact a relayed rework changed after the judged
   delivery needs `base="delivered"|"latest"`; `delivered` gives the lead the judged version (its org-git commit and text). Rework
   delegations inherit the tier. Root's other ways to send a rework of a service request (`delegate`, the `Org` facade's `send`) are refused.
5. **D-E4-6.** The root instructions say to activate the skill before building or rating, and give the reject order in one line. A run that
   ended on a model-service throttle with no tool effect (the launcher's own verdict, carried by its exit code) is not charged (a runtime
   credit note returns its run; the case and progress run counts leave it out) and is retried once.
6. **Deterministic replays** of s1r T5, s1r's playbook v2, s1r v3/v4, s1r T8, the s2r chain, the s3 flow and E3 T5, read from the raw
   evidence files.

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
| `strip_markers(line) -> str` | `SRC/kernel/_text.py`, exported from `kernel.api` (pure) | `line` without its leading markdown markers: `_LINE_MARKER` (`>`, `#`..`######`, `-`, `*`, `+`, `•`, `1.`/`1)` up to 3 digits, `[ ]`/`[x]`) removed repeatedly from the start, exactly the loop `word_count` runs today (`word_count` calls it; no behaviour change). |
| `line_key(line) -> str` | `SRC/services/api.py` (pure) | `"".join(ch for ch in strip_markers(line).casefold() if ch.isalnum())`: the line's letters and digits after its leading markers, case-folded. Punctuation, spacing, list numbering (`3.` -> `4.` when a step is inserted), bullets, checkboxes (`- [ ] x` and `- [x] x` are the same line) and other markdown never make two lines differ; a change of any word, or of a number inside the text, does. |
| `changed_lines(current, new) -> list[str]` | `SRC/services/api.py` (pure) | The lines of `new` (stripped, in order) whose `line_key` is not among the keys of `current`'s lines, counted as a multiset (`collections.Counter`): a line repeated in `new` more often than in `current` counts once more. Lines whose key is empty (blank, `---`, a fence, a lone `-` or `#`) are never changes. `changed_lines(new, current)` gives the removed lines. |
| `repeats_rejection(words, note) -> bool` | `SRC/services/api.py` (pure) | `A` = the words of `words`, `B` = the words of `note` (each `re.split(r"[^0-9a-z]+", text.casefold())` without empty items). True when `A == B`, or when the shorter of `A` and `B` has at least 4 words and occurs as a contiguous run in the longer (symmetric: a paste of the user's whole reject turn that contains the recorded note, or a part of the note, are both caught). Checked on the evidence: s1r T5 (`turn-05.prompt.txt`) against #22's note: True; E3 T5 against E3 #24's note: True; `"Yes, add it."` and s1r #23's `"Yes, add it. Yes, fund it - but please keep an eye on the cost."` against #22's note: False. |
| `rated(case, task) -> bool` | moved from `SRC/progress/_lines.py` to `SRC/reflection/api.py` (pure); `progress` imports it | Has the client given a verdict (any tier) on this delivery or on a later task of its chain? Unchanged semantics. |
| `questions_open(task, result, case, root_sent) -> int` | moved from `SRC/progress/_lines.py:CaseTaskLines._questions_to_ask` to `SRC/reflection/api.py` (pure) | The client questions (`kernel.client_questions`) of a `done` or `blocked` result (6.1) that nothing settled: 0 when there are none, when `task.service` and `rated(case, task)`, or when `root_sent` holds a task with `revises == task.id` and `source == "human"`; else their number. `progress` (6.1, 6.2) and the deliverable checks (6.3) read this one rule. |
| `delivered_unrated(cases) -> tuple[str, ...]` | `SRC/reflection/api.py` (pure) | The latest task id of every case whose `state == "done"` and `not rated(case, case.tasks[-1])`. |
| `artifact_paths(body) -> list[str]` | `SRC/kernel/_text.py`, exported from `kernel.api` | The paths of the `## Artifacts` section of a result body: the non-blank stripped lines of that section (`## ` heading, case-insensitive), each `lstrip("-* ")` and cut at the first `" ("`. Exactly what `progress._lines.artifacts_of` does today through `attention.section`; `artifacts_of` becomes `artifact_paths(result.body)`, so `progress` and `reflection` parse one way. |
| `blob_id(data, hexlen=40) -> str` | `SRC/snapshots/api.py` (pure) | The git object id of a blob with these bytes, as `git hash-object` computes it: `sha1(b"blob %d\0" % len(data) + data)` for `hexlen == 40`, `sha256(...)` for 64. The caller passes the length of the id it compares with, which is the repository's own object format (a checked id read from git is 40 or 64 hex digits); with no checked id read from git (no repository), both sides of a comparison are blobs the product computes itself (the folder's file and the current org file), both with 40. Any other length is a `ValueError` (a bug). |
| The judged delivery of a case | `SRC/reflection/_judged.py` | Section 7.2. |
| The basis of a contract version | `SRC/services/_parse.py:contract_of` | Section 5.4: `answers`, `about`, `words`, `initiated` in its frontmatter. |
| `answering_version(store, owner, name, note) -> int` | `SRC/services/_criteria.py` (package-private) | The first stored `SERVICE` version (`ServiceStore.versions(owner, name, "SERVICE")`, oldest first) whose frontmatter `answers` equals `note`; 0 when none. The one reader of "a contract version answers this rejection", used by the definer (P2-ANSWERED) and by `feedback` (P2-CONFIRMS-ANSWERED, P2-CONFIRMS-RECOVERY). |
| `answer_ids(store, owner, name, version) -> tuple[str, ...]` | `SRC/services/_criteria.py` (package-private) | The ids the link of an answering version names: the criteria that `version` added (present in it, absent from the stored version before it, numbered by `number_criteria` over the stored versions), in order; when it added none, the ones it removed. The definer computes the product's link ids with it (5.4) and `feedback` compares a recovery link with it (5.3), so both read one rule. |
| `RUN_CREDIT_TITLE = "Run not charged"`, `run_credit_title(addr, stem) -> str`, `is_run_credit(sender, title, budget) -> bool`, `credited_stems(received) -> frozenset[str]` | `SRC/kernel/_message.py` (pure) | The title of a credit is `f"{RUN_CREDIT_TITLE}: {addr}@{stem}"` (`addr@stem` is the run id `observability` already uses; `stem` is the run log's file stem, `\d{8}T\d{12}`). A note is a run credit when `sender == RUNTIME`, `budget > 0` and the title matches `^Run not charged: (.+)@(\d{8}T\d{12})$`. `credited_stems(messages)` = the stems of the run credits among `messages` (a received box). In `kernel` because `budget`, `agents` (retired archive), `observability`, `reflection` and `progress` all recognize it and only the kernel is below all of them. |

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
   - is a **(c) line** when `line_key(c.text)` is non-empty and `line_key(line)` equals `line_key(c.id) + line_key(c.text)` or
     `line_key(c.text) + line_key(c.id)` for some `c` in `added` (for example `- C9: <C9's text, verbatim>`, `2. C9: <C9's text>` as a
     numbered step, or `<C9's text> (C9)`; the leading markers are not part of the key); it is admitted on `c.id`. A criterion whose text has
     no letter or digit (an empty key) admits no (c) line: a bare `C9` would otherwise be its "words";
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
{c_part}{b_part}A change of punctuation, spacing, list numbering or markdown alone needs nothing. Nothing was written: revise again without these lines, or send {client} (`send`) this question once: "We would add to how we deliver {service}: {first offending line}. Is that what you want from now on? If yes, please add it to the contract as a criterion."
```
- At most 10 offending lines are listed, each `clip_line(line, 600)` (so the refusal is at most about 6 KB of quoted lines). 600 holds every
  changed line of E4's refused revisions whole: the longest, s3's step 2 in `PLAYBOOK.dd2d1da.md`, has 532 characters, and its riders
  (`(d) a 'Next meeting' footer` at characters 398-425, `No other sections` at 450-467) and step 3's `(C1–C8) and the regression list
  verbatim` (149-189 of 273) are inside the listing. More than 10: `- and {k} more`.
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
non-empty key) that contain `criterion.id` as a standalone token, or whose `line_key` contains `line_key(criterion.text)` when that key is
non-empty (the text quoted verbatim, modulo punctuation; an empty key is never "contained", or every line would quote it). `SRC/services/_amend.py:ContractAmender.diff` gains the parameter `quoting: Mapping[str, Sequence[str]]` (removed
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
`playbook` on an existing service is refused today). Two other ways could give a service new criteria with a fresh record, and both are
closed. Retiring the service (`FsServiceStore.retire` moves it under `.retired/`) is gated by the same basis (5.2a). Retiring the owning
agent with its team (`hierarchy.RuleRetirement.retire_team`: MCP root `retire`, CLI `retire`, `Org.retire`, `Org.retire_team`), hiring it
again and defining the service is not refused (the user keeps authority over the structure); instead the definition continues the retired
service's contract, playbook and cases whenever a request of that service has a result of any status (a recorded request, 5.10, DR-41), so its record is neither erased nor reset.
Every path, and the declared ways around that remain visible (another owner, another name), is listed in 5.8.

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
    question: str          # the exact question of 5.6 for it, with its ids filled in (reflection owns the QUESTION text)

@dataclass(frozen=True)
class AmendmentBasis:
    rejections: tuple[Rejection, ...]
    unrated: tuple[str, ...]  # reflection.delivered_unrated(cases)
```
`Rejection.question` is built by the same function as the `feedback(reject)` reply (`SRC/reflection/_steps.py:question_for`, 5.6), so
the definer's and the retirement's refusals quote the question byte for byte as the reply showed it, and the text lives in one place.

Order of checks, each refusal writes nothing:

0. **Continuation** (5.10). `actor == ROOT` and no current contract: `prior = self._continued.continued(owner, name)`; `OrgError`/`OSError`
   while reading it: P2-UNREADABLE (fail closed). With a `prior`, the call is a continuation: `old` is the contract of `prior`'s
   `SERVICE.md` for every rule below, the first-definition rules (the missing-fields refusal, the refusal of `add_acceptance`/`remove_acceptance`
   "does not exist yet") do not apply, and:
   - a `playbook`, or a resulting acceptance list whose set differs from `old`'s: P2-CONTINUES;
   - today's "no change" refusal does not apply (a continuation always writes the next version, which records who defined the service again
     and when).
   Without a `prior` (none, or none with a recorded request, DR-41), the call is today's first definition.
1. `actor != ROOT` and any of `answers`, `about`, `words` given: P2-ROOT-ONLY.
2. Any of them given on a first definition, or on a call that is not an acceptance amendment (a continuation never is one): P2-NOT-AN-AMENDMENT
   (after today's "no change" refusal, so an amendment that changes nothing keeps today's text).
3. Root's acceptance amendment (`answers`, `about`, `words` normalized: stripped; `about` upper-cased):
   1. `basis = self._evidence.amendment_basis(owner, name)`; `OrgError`/`OSError` while reading it: P2-UNREADABLE (fail closed: the gate guards
      the contract).
   2. `basis.unrated` non-empty: P2-UNRATED, whatever else was passed (the verdicts come first: this is the s1r T5 order, where the amendment
      came 0.46 s before the `feedback(reject)`).
   3. `words` missing or blank: P2-NEEDS-WORDS. `len(words) > FEEDBACK_MAX` (1000): P2-WORDS-LONG.
   4. exactly one of `answers` and `about` given: P2-PAIR.
   5. With `answers` (the answer to a rejection):
      - no `r` in `basis.rejections` with `r.note == answers`: P2-NOT-A-REJECTION;
      - `r.answered`, or `answering_version(store, owner, name, r.note) > 0` (section 3): P2-ANSWERED (one rejection, one answer);
      - `about` is neither a criterion current in the contract version in force when `r` was recorded nor one of `r.earlier`: P2-ABOUT.
        The version in force is the latest stored version whose `defined` is at or before the timestamp of `r.note` (read with
        `ServiceStore.versions(owner, name, "SERVICE")` and `contract_of` as `stored_versions` does; its criteria through
        `criteria_of(number_criteria(stored), that version's acceptance)`). When no stored version has a `defined` at or before it (a legacy
        file without `defined`, or a history file that is missing), the oldest stored version is used; the current version is always stored,
        so there is at least one;
      - `repeats_rejection(words, r.words)` (section 3; symmetric, so a paste of the user's whole reject turn is caught as well as a part of
        the note): P2-WORDS-ARE-THE-REJECTION (section 20, D3).
   6. Without `answers` (user-initiated): any `r` in `basis.rejections` with `not r.answered` and `answering_version(...) == 0`:
      P2-OPEN-REJECTION (the change is inside a rejection; section 20, D4).
4. Write, in this order: on a continuation, the restored copy (`ServiceRestorer.restore`, 5.10); the contract (5.4); on the answer path, the
   link note (5.4); the owner's note (the amendment note, or the continuation note of 5.10); then the reply (5.7). The link is written before
   the owner's note so that the note's marks say what is recorded. When the link cannot be written (section 12), the owner's note is still
   delivered, with the new ids marked `(not confirmed)` and the line `The link that records the client's yes to {R} could not be written; it
   follows as a criterion link.`, and only then is the error raised, so the owner learns of the new contract either way.

### 5.2a Retiring a service is gated by the same basis (`SRC/services/_retire.py:RuleServiceRetirement.retire_service`)

`RuleServiceRetirement` gets `evidence: ServiceEvidence` as its 8th collaborator (`app/wire_services.py`, `services.testing`). For
`actor == ROOT`, after today's checks (authority, the service exists, a reason) and before `self._store.retire(...)`:
1. `basis = self._evidence.amendment_basis(owner, name)`; `OrgError`/`OSError`: P2-RETIRE-UNREADABLE (fail closed).
2. `basis.unrated` non-empty: P2-RETIRE-UNRATED.
3. any `r` with `not r.answered` and `answering_version(store, owner, name, r.note) == 0`: P2-RETIRE-OPEN (the oldest is named).
Agents retiring their reports' services are not gated (as agents' amendments are not, 5.8). Root can always meet the condition: any verdict
counts as rated (a relayed `accept` when the user drops the delivery), and a rejection is answered by `feedback(confirms=...)` with "none".
After every verdict and answer the retirement is allowed; defining the service again afterwards continues it when it had a recorded request (5.10), so the record survives this path too. The gate is kept beside the continuation: it costs no structure (the agent and its team stay),
and it keeps the retired copy's record complete at the moment it is retired (section 20, D20).

### 5.3 Refusal texts (new; constants in `SRC/services/_define.py`)

Every text has the common frame: it starts with `refused: ` and says what was not done (`Nothing was written|retired|recorded|sent.`, or, in
the two "cannot be read" texts, `so the contract was not changed` / `so the service was not retired`). The texts are raised in `services`, the
one layer MCP and the CLI share, so a text that names arguments gives both forms: the MCP form in the sentence and the CLI flags in a
`(CLI: ...)` parenthesis (`--answers`, `--about`, `--words` of `define-service`; `--confirms`, `--criterion`, `--source`, `--note` of
`feedback`).

- **P2-ROOT-ONLY**: `refused: answers, about and words are root's: they record the human client's answer. An agent client amends its report's contract without them. Nothing was written.`
- **P2-NOT-AN-AMENDMENT**: `refused: answers, about and words record the user's answer to a change of the acceptance criteria; this call changes none. Pass them only with acceptance, add_acceptance or remove_acceptance on an existing service (CLI: --acceptance, --add-acceptance, --remove-acceptance). Nothing was written.`
- **P2-NEEDS-WORDS**:
  ```
  refused: a change of the acceptance criteria of `{name}` records the user's words. If it answers a rejection, pass answers=<the rejection's message id>, about=<the C or R id your one question named> and words=<the user's answer, verbatim> (CLI: --answers, --about, --words), after they answered yes to that question{open}. If the user asked for this change on their own, outside any rejection, pass words=<their request, verbatim> alone (CLI: --words): it is recorded as user-initiated and never admits a playbook revision. Nothing was written.
  ```
  `{open}` = ` (waiting for an answer: R1, message <id>)` listing every unanswered rejection, or `""`.
- **P2-WORDS-LONG** (DR-46): `refused: words (CLI: --words) is {n} characters; the limit is 1000: the user's answer, verbatim, not a summary. Nothing was written.`
- **P2-PAIR**: `refused: answers and about go together: answers=<the rejection's message id>, about=<the C or R id your question named> (CLI: --answers, --about). Nothing was written.`
- **P2-UNREADABLE**: `refused: the record of `{name}` cannot be read ({error}), so the contract was not changed. Try again; if it persists, tell the user.`
- **P2-UNRATED** (DR-46): ``refused: {n} delivered request(s) of `{name}` have no verdict yet: {task ids}. Record the user's verdict on each with feedback first, a rejection then its one question (CLI: hirearchy feedback <task id> accept|reject --note ...); the contract changes only after the verdicts. Nothing was written.``
- **P2-NOT-A-REJECTION** (DR-46): ``refused: answers (CLI: --answers) must be the message id of a rejection you recorded with feedback(..., source="human") (CLI: hirearchy feedback <task id> reject --note ...) on a request of `{name}`: {answers}. Its rejections: {"R1 (message <id>)", ... or "none yet"}. Nothing was written.``
- **P2-ANSWERED**: `refused: rejection {R} (message {id}) already has its answer ({link note <id> | contract v<n>}): one rejection gets one answer. A new lasting rule needs a new rejection and its question, or words alone (CLI: --words) when the user asks for it on their own. Nothing was written.`
- **P2-ABOUT** (DR-46): `refused: about (CLI: --about) must be the id your one question named: a criterion of contract v{v}, in force when {R} was recorded ({C ids}), or an earlier rejection ({R ids or "none"}): {about}. A criterion this change creates cannot be what the question was about. Nothing was written.`
- **P2-WORDS-ARE-THE-REJECTION** (DR-46): `refused: words (CLI: --words) repeats rejection {R}'s own note (or the note is part of it). The answer is what the user said to your one question after the rejection (e.g. "Yes, add it."); an "always ..." inside the rejection is not it. Nothing was written.`
- **P2-OPEN-REJECTION**:
  ```
  refused: rejection {R} (message {id}) on task {task} has no answer yet, so this change is not one the user asked for on their own. Ask the user the one question first ({question}). On yes: define_service(owner="{owner}", name="{name}", ..., answers="{id}", about=<the id you asked about>, words=<their answer, verbatim>) (CLI: --answers, --about, --words). On no, a one-off or "as it is": feedback(task_id="{task}", verdict="reject", confirms="{id}", criterion=["none"], ["R<j>"] or ["C<k>"], source="human", note=<their answer, verbatim>) (CLI: --confirms, --criterion, --source human, --note). Nothing was written.
  ```
  `{question}` is `Rejection.question` (5.2, 5.6). With several unanswered rejections, the oldest is named.
- **P2-CONTINUES** (5.10):
  ```
  refused: `{name}` of {owner} continues the retired service kept at {path} ({k} request(s) with a result), so defining it again keeps its contract v{n}, its playbook {v<p> | (none yet)} and its record. Leave out {what} and define it again; then change the criteria as an amendment, the user's answer to a rejection (answers=, about=, words=) or a change they asked for on their own (words= alone) (CLI: --answers, --about, --words). Nothing was written.
  ```
  `{what}`: `playbook (CLI: --playbook)` when one was given; `the change of the criteria: give no acceptance, add_acceptance or remove_acceptance, or acceptance exactly as in v{n} (CLI: --acceptance, --add-acceptance, --remove-acceptance)` when the set differs; both joined by ` and ` when both apply.

New refusals of `retire_service` (5.2a; constants in `SRC/services/_retire.py`):
- **P2-RETIRE-UNRATED** (DR-46): ``refused: {n} delivered request(s) of `{name}` have no verdict yet: {task ids}. Record the user's verdict on each with feedback first (CLI: hirearchy feedback <task id> accept|reject --note ...); a service is retired only after its verdicts, so that its record stays complete. Nothing was retired.``
- **P2-RETIRE-OPEN**:
  ```
  refused: rejection {R} (message {id}) on task {task} of `{name}` has no answer yet. Ask the user the one question first ({question}) and record the answer: define_service(..., answers="{id}", about=<the id you asked about>, words=<their answer, verbatim>) on yes (CLI: --answers, --about, --words), feedback(task_id="{task}", verdict="reject", confirms="{id}", criterion=["none"], ["R<j>"] or ["C<k>"], source="human", note=<their answer, verbatim>) otherwise (CLI: --confirms, --criterion, --source human, --note). A service is retired only after its rejections are answered. Nothing was retired.
  ```
- **P2-RETIRE-UNREADABLE**: `refused: the record of `{name}` cannot be read ({error}), so the service was not retired. Try again; if it persists, tell the user.`

New refusals of `feedback` (constants `CONFIRMS_ANSWERED` and `CONFIRMS_RECOVERY` in `SRC/services/_feedback.py`; `RuleClientFeedback`
gets `store: ServiceStore` as its 5th collaborator; section 20, D18). They are raised in `RuleClientFeedback._check_confirmation` after its
four existing checks (the rejection `confirms` exists on this task; it is a reject; the verdict is `reject`; `criterion` is given), and only
when `n = answering_version(store, task.to, task.service, confirms) > 0` (a contract version answers the rejection). Then exactly one link
is still accepted, the product's own link when its write failed (section 12): `criterion` equal as a set to `answer_ids(store, task.to,
task.service, n)` (after `normalize_links`), `source == "human"`, and no human-tier link note on `confirms` in root's sent box yet. That link
confirms the criteria (5.5: a human-tier link on the answered rejection). Every other `confirms` on that rejection is refused:
- **P2-CONFIRMS-ANSWERED** (a human-tier link on `confirms` exists; DR-46): ``refused: rejection {confirms} was answered by contract v{n} of `{service}` (define_service(..., answers="{confirms}"); CLI: define-service --answers) and its link {link id} records the user's yes: one rejection gets one answer. A different answer needs a new rejection and its question. Nothing was recorded.``
- **P2-CONFIRMS-RECOVERY** (no such link yet, but other ids or another source): `refused: rejection {confirms} was answered by contract v{n} of `{service}`, and its link is missing (its write failed). The only link it still takes is that one: feedback(task_id="{task}", verdict="reject", confirms="{confirms}", criterion=[{ids}], source="human", note=<the user's answer, verbatim>) (CLI: --confirms, --criterion, --source human, --note). Nothing was recorded.`

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
  (byte-identical note) and `RuleContractDefiner` gets it as its 14th collaborator. `ids` = `answer_ids` of the new version (section 3):
  the criteria the amendment added, in order; when it adds none, the ones it removed. The link is stamped `source: human` by the product;
  the `words` are declared by root (declared provenance). If the link cannot be written (`OSError`/`OrgError`) after the contract was: 5.2
  step 4 and section 12 (the one recovery link `feedback` still accepts, 5.3).
- **A continuation** (5.10) writes byte-identical copies of the retired copy's files (its `SERVICE.md`, `PLAYBOOK.md` and `history/`
  versions) into the live service directory, then the next version as an ordinary amendment. The copies are immutable versions written by
  the single writer (`FsServiceStore`); the retired copy itself is never changed.
- Nothing else: no new event field (`service.define` keeps `amendment: bool`, so `events/line_shapes.txt` is unchanged), no ledger.

### 5.5 Eligibility: a user-initiated amendment is never (c)-eligible

`SRC/reflection/api.py:confirmed_criteria(cases, criteria)` (the signature gains the **required** parameter `criteria: Sequence[Criterion]`,
with no default, so mypy finds every caller: `_evidence.confirmed` and `admit`, `_sections._eligible`, `_reports`, `_steps`, and any
`dashdata` reader; each passes `catalog.criteria(owner, service)`): a `C<k>` named by a human-tier link note (as today) is confirmed when
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

`SRC/reflection/_steps.py:QUESTION` becomes one of three texts, chosen by **root's reading**: the first id of the rejection's own `criterion`
that is a current `C<k>` or an earlier `R<j>` of the service (`none`, or no `criterion`, is no reading). The rejection's own `criterion` is
the one place root names what it reads the rejection as: 0a.1 already records it as relayed and "not confirmed" whatever the source, and in
0a.2 it never confirms a criterion (5.5: only a human-tier link note does), never is an assertion's `about` (`regressions` reads human-tier
links only) and never weighs in rule (b). So it is a reading, not the link; the link stays the human-tier note written after the yes, by
`define_service(answers=...)` or `feedback(confirms=...)`. `{own}` and `This rejection is {R}. ` stay as today in front of each text.

A reading `C<k>` (the question with the id, D-E4-2):
```
Next: ask the user exactly ONE yes/no question, in these words: "About C<k>: add "<the rule, in their words>" as a lasting rule? Yes or no." Change nothing in this turn: an "always ..." in the rejection is not their yes. On yes: define_service(owner="{owner}", name="{service}", add_acceptance=["<the rule>"], answers="{note}", about="C<k>", words="<their answer, verbatim>"). On no, a one-off or "as it is": feedback(task_id="{task}", verdict="reject", confirms="{note}", criterion=["none"] or ["C<k>"], source="human", note="<their answer, verbatim>").
```
A reading `R<j>` (a repeat):
```
Next: ask the user exactly ONE yes/no question, in these words: "Same as R<j>: a one-off? Yes or no." Change nothing in this turn: an "always ..." in the rejection is not their yes. On yes: feedback(task_id="{task}", verdict="reject", confirms="{note}", criterion=["R<j>"], source="human", note="<their answer, verbatim>"). On no, when their answer asks for a lasting rule: define_service(owner="{owner}", name="{service}", add_acceptance=["<the rule>"], answers="{note}", about="R<j>", words="<their answer, verbatim>"); otherwise feedback(task_id="{task}", verdict="reject", confirms="{note}", criterion=["none"], source="human", note="<their answer, verbatim>").
```
No reading (the question names the id root chooses now; section 20, D23):
```
Next: ask the user exactly ONE yes/no question that names the criterion you read the rejection as: "About <its id>: add "<the rule, in their words>" as a lasting rule? Yes or no.", with <its id> one of {C ids}; for a repeat: "Same as R<j>: a one-off? Yes or no.", with R<j> one of {R ids}. Next time, pass your reading as criterion on the rejection and this reply gives the question with its id. Change nothing in this turn: an "always ..." in the rejection is not their yes. On yes: define_service(owner="{owner}", name="{service}", add_acceptance=["<the rule>"], answers="{note}", about="<the id you asked about>", words="<their answer, verbatim>"). On no, a one-off or "as it is": feedback(task_id="{task}", verdict="reject", confirms="{note}", criterion=["none"], ["R<j>"] or ["C<k>"], source="human", note="<their answer, verbatim>").
```
- `C<k>`/`R<j>` in the first two texts are the reading itself (for example `About C3: add`); `{C ids}`: the current criteria; `{R ids}`:
  the other assertions, or `none` (then the repeat sentence is left out). `{owner}`, `{service}`: the request's. Rev 2's fallback
  `({first} is one of {C ids} ...)`, which printed `C<k> is one of ...` with no reading, is gone.
- The quoted question (the text inside the first pair of quotes, with the same substitutions) is built by
  `question_for(rejection, criteria, earlier)` in `SRC/reflection/_steps.py`, which `feedback_step` and `CaseServiceEvidence.amendment_basis`
  (for `Rejection.question`, 5.2) both call; so P2-OPEN-REJECTION and P2-RETIRE-OPEN quote the question as the reply showed it, with its id
  when root gave a reading.
- The receipt line before the step is unchanged (`..., about C3 (not confirmed)); it does not wake lead`).
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
- **Root `feedback` docstring** (two phrases pinned by `SRC/mcp_server/tests/test_service_tools.py:35-36` go on purpose, DR-46: line 35's `confirms: the user's yes. After they answered yes to your one question naming the id, call again with the same task_id, verdict "reject"` and line 36's `only this link counts as the client's`; commit B4 replaces them in that test with the new sentence's phrases, in the same commit; the rest of those assertions stays): the sentence from `confirms: the user's yes.` to `only this link counts as the client's.` becomes
  `confirms: the user's answer that changes no criterion ("no", "a one-off", "about C<k> as it is"): call again with the same task_id, verdict "reject", confirms=<the rejection's message id>, criterion ("none", "R<j>" or "C<k>"), source "human" and their answer verbatim as note; it records the link, not a new verdict. A yes that changes the contract is define_service(..., answers=<the rejection's message id>, about=<the id>, words=<their answer>), which records the link itself; after it, that rejection takes no confirms.`
  and, after `on the rejection itself it is shown as not confirmed, whatever the source.` (kept: `test_service_tools.py:36` pins it), the
  sentence `Pass your reading there (one id: what you read the rejection as), and the reply gives the exact question naming it.` is inserted
  (wrapped at today's column; 5.6, D23).

### 5.8 No bypass

| Path | Reaches | Gate applies |
|---|---|---|
| MCP root `define_service` | `ServiceCommands.define_service` | yes |
| MCP agent `define_service` (no new arguments) | same; `actor != ROOT`, not root's amendment | not gated (agent clients' amendments are never `amended`, hence never (c)-eligible) |
| CLI `define-service` | same | yes: the human at the terminal passes `--words` (or `--answers/--about/--words`) like anyone |
| `Org.define_service` | same | yes |
| `apply_org` / `hirearchy apply` | `ServiceCommands.define_service` with `playbook=` | first definitions only (an existing service with `playbook` is refused today; a name that continues a retired service with a recorded request is refused with P2-CONTINUES, 5.10) |
| root `retire_service` (MCP, CLI `retire-service`, `Org.retire_service`), all through `ServiceCommands.retire_service` -> `RuleServiceRetirement` | the basis of 5.2a | yes: P2-RETIRE-UNRATED, P2-RETIRE-OPEN, P2-RETIRE-UNREADABLE |
| retire the service, then define it again for the same owner, after every verdict and answer | a continuation when it had a recorded request (5.10); else a first definition | the continuation keeps contract, playbook and record; its defining call cannot change the criteria (P2-CONTINUES); later changes go through the gate with the whole record. A retired service none of whose requests ever got a result has no record to keep: its re-definition is a new service, as in 0a.1. |
| root retires the owning agent with its team (MCP root `retire`, CLI `retire`, `Org.retire`, `Org.retire_team`, all through `hierarchy.RuleRetirement.retire_team`), hires the same name again (MCP/CLI `hire`, `Org.hire`) and defines the service | `ServiceCommands.define_service` -> `RuleContractDefiner`, step 0 of 5.2 | the retirement is **not refused** (the user's authority over the structure); the definition continues the service whenever a request of it has a result of any status (5.10, DR-41): the same contract (next version, same `created`), playbook and cases, and P2-CONTINUES for a criteria change in that call. `retire_team` closes the team's open requests as `failed` (`hierarchy/_retirement.py:64`), so after a team retirement every request of the service is recorded; a human rejection of a `blocked` or `failed` result keeps its record across retire, hire and define, and the later amendment is refused P2-OPEN-REJECTION exactly as for a `done` result. MCP root's `retire` reply says so and names what is still open (5.10). E5 counts retire/hire/define triples (section 21). |
| after that retirement, the same service name defined for **another** top-level agent, or the criteria under **another name** (also while a rejection of the old service is unanswered or a delivery unrated) | a first definition of a new service (another owner or name) | **declared way around, visible**: `services` lists a new service (its owner or name differs, its record starts empty, its v1 criteria are never (c)-eligible); the old record stays in root's mailbox and in the retired copy. E5 counts new services defined by root while another service, live or retired, has an unanswered rejection or an unrated delivery (section 21; D22). |
| root's `delegate` without `revises` to a service's owner (a one-off task, "redo the memo") | `RuleTaskAssigner.delegate`; no case, no contract, no base | **declared way around, visible**: a one-off task in `progress`, outside every case (no P4 base, no verdict needed). E5 counts one-off root tasks to an owner while one of its cases is open or has an unrated delivery (section 21). |
| `feedback(confirms=...)` naming a `C<k>` | a link note | cannot make an amendment eligible (5.5); after `define_service(answers=X)`, `confirms=X` is refused (P2-CONFIRMS-ANSWERED), except the one recovery link when the product's link write failed (P2-CONFIRMS-RECOVERY refuses every other) |
| `send` / `write` (MCP, CLI) | notes without `feedback`, `criterion`, `service` or `revises` (neither surface has these arguments) / files outside `services/` | `criterion` is refused on a plain note by `provenance_source` (S3); `orgfiles` does not own `services/**` |
| `Org.send(ROOT, ..., type="note", feedback=... or criterion=...)` (the facade, which forwards every field) | would write a verdict or link note without `RuleClientFeedback` | refused by `dispatch.GuardedRootSender` (`check_root_send`, 7.5), which the `Org` facade's `send` delegates to (A.4 P1): FACADE-ROOT-VERDICT |
| `Org.deliver(msg)` and `Org.runtime.<port>` | the delivery pipeline and the composition root's ports, below every policy | **out of the guarantee, declared**: `Org.deliver`'s docstring already says "Low level ... Policy is checked by the callers"; both are the primitives every rule is built on (ARCHITECTURE 2.3) and no surface exposes them. Pinned by `TESTS/architecture/test_policy_free_primitives.py`: (1) no module of `SRC/mcp_server` or `SRC/cli` outside `tests/` calls `.deliver(` (a source scan, as the existing architecture checks do); (2) the MCP `send` tool (every identity) and the CLI `send` parser have none of the parameters `type`, `feedback`, `criterion`, `service`, `revises`, `source` (checked on the registered tool's input schema and the argparse actions); (3) `Org.deliver.__doc__` starts with `Low level`; (4) the guarded `Org.send` refuses the four shapes of 7.5. A new surface that calls the primitive or widens `send` fails (section 20, D19). |
| the assistant's shell writing `SERVICE.md` | outside the product | not preventable by the product (the user's machine); a hand-written version is read like any other, and a forged `answers` key with a `feedback(confirms=...)` link could make a criterion eligible. No product path writes a root acceptance amendment without a basis, so a legacy-shaped root version after 0a.2 can only come from such a write. E4 counted 0 shell writes under `services/` (STUDY "Clause 1 (b)"); E5 counts them (section 21). |

### 5.9 What P2 cannot enforce

That the question was shown, held one proposition, or that `words` are the user's. Without a reading on the rejection the reply cannot name
the id (D23); the replays pass the reading the compliant flow would (s2r and s3 add `criterion=["C3"]` to the rejection, which E4's
assistants did not pass). P2-WORDS-ARE-THE-REJECTION catches only a copy of the rejection (or a paste that contains it). That `about` names
the id the shown question named is declared, not checked (the reading is the assistant's, and the user's answer may move it); E5 counts the
mismatches. A second `feedback(confirms=X)` after a first one (two links, no contract change) is still accepted, as in 0a.1:
the latest human link decides what `X` is about (`regressions().about`), which lets the user correct an answer; E5 counts rejections with
more than one link (section 21). The visible ways around of 5.8 (another owner, another name, a one-off `delegate`) are counted, not
refused: the product cannot tell a new service the user wants from an escape.

### 5.10 Retiring the owner keeps the record: a definition continues the retired service

**The rule.** When root defines service `name` of a top-level agent `owner` and no live contract exists, the definition **continues** the
newest retired copy of that service when that copy has a recorded request (a request of it with a result of any status, DR-41); otherwise it is a first definition, as today. Agent clients'
definitions never continue (P2 binds root's amendments only). The retirement itself is never refused for this: retiring an agent with its
team is the user's structural decision, and the record survives it.

**Retired copies** (read only by `SRC/services/_continue.py:RecordedContinuations`):
- `<owner>/services/.retired/<entry>/`, where `re.fullmatch(re.escape(name) + r"-\d{8}T\d{12}", entry)` (the stamp of
  `RuleServiceRetirement`, `%Y%m%dT%H%M%S%f`; so the service `weekly` never picks `weekly-memo-<stamp>`);
- for every retired agent tree `t` in `agents.RetiredArchive.trees()` with `t.top_level` and `t.addr == owner`: `t.path/services/<name>/`,
  and `t.path/services/.retired/<entry>/` with the same `fullmatch`. `RetiredTree` (`SRC/agents/api.py`) gains the read-only property `addr`:
  its name without the `-<stamp>` suffix (`-\d{8}T\d{6}$`), `.` read as `/`. The suffix pattern moves from `agents/_retired.py` to
  `agents/api.py`, so one rule names and reads a tree.
- A copy is a directory that holds a regular `SERVICE.md`. Every candidate path is built from the layout and the archive, never from a name
  read in a file; all of them are inside the organization.
- The **newest** copy is the one with the greatest `defined` in its `SERVICE.md` (`contract_of(...).defined`; `None` sorts first); ties go to
  the greater path. A continued service carries its whole lineage (its copied history), so the newest copy is enough.
- The copy **has a recorded request** (DR-41) when root's sent box holds a task with `to == owner`, `service == name` and `msg_time(m) >= created`
  (the copy's `Contract.created`; `None`: no floor) whose latest result in root's received box (`kernel.latest_results`) has **any** status:
  `done`, `blocked` or `failed`. A verdict, a rejection, an answer and a judged delivery all rest on a result (`RuleClientFeedback` refuses a
  task that has none: "has no result yet"), so a request with a result of any status is exactly what can leave a record to keep, and a
  human rejection of a `blocked` or `failed` result keeps its record across retire, hire and define like one of a `done` result.
  `retire_team` closes the team's open requests as `failed` results (`hierarchy/_retirement.py:64`), so after a team retirement every request
  of the service is recorded. A rolled-back blueprint (`blueprint/_undo.py:RetiringRollback`, which retires what a failed `apply_org` built)
  and a service none of whose requests got a result before it was retired therefore start fresh.
  **Declared facet** (DR-41): a request still open at `retire_service`, whose result arrives only after a fresh re-definition (the copy had no
  recorded request then, so the definition was a first one with a new `created`), falls outside every case of the new service; E5 counts the
  results recorded after a fresh re-definition of a retired service (section 21).

```python
@dataclass(frozen=True)
class RetiredService:  # SRC/services/_protocols.py (package-private)
    path: str                            # the copy, org-relative
    files: tuple[tuple[str, str], ...]   # (name inside the service directory, text): SERVICE.md, PLAYBOOK.md, history/SERVICE.v<k>.md, history/PLAYBOOK.v<k>.md
    recorded: int                        # the requests of it with a result of any status (done, blocked, failed)

class ContinuedServices(Protocol):
    def continued(self, owner: str, name: str) -> RetiredService | None:
        """The retired copy a root definition of ``owner``'s ``name`` continues: the newest one, when it has a recorded request; None
        otherwise. ``OSError``/``OrgError`` when a copy cannot be read."""

class ServiceRestorer(Protocol):
    def restore(self, owner: str, name: str, retired: RetiredService) -> None:
        """Write the copy's files byte for byte into the live service directory, ``SERVICE.md`` last."""
```
`RecordedContinuations(places: ServicePlaces, archive: RetiredArchive, mail: MailboxReader)` implements `ContinuedServices` (services may
import `agents` and `mail`). `FsServiceStore` implements `ServiceRestorer` besides `ServiceStore`: it stays the single writer of
`<owner>/services/**`, and `ServiceStore` keeps its 8 methods (R7). Only the four file shapes are read and written (`SERVICE.md`,
`PLAYBOOK.md`, `history/SERVICE.v\d+.md`, `history/PLAYBOOK.v\d+.md`); anything else in a copy is ignored. `RuleContractDefiner` gets both
ports as its 15th and 16th collaborators, `continued: ContinuedServices` and `restorer: ServiceRestorer` (`app/wire_services.py`,
`services.testing`).

**The definition** (5.2 step 0). `old` is the contract of the copy's `SERVICE.md`; the stored versions are the copy's `SERVICE` files, parsed
with `merged_versions` as `FsServiceStore.versions` does, so the criteria keep their ids. Refusals: P2-CONTINUES (a `playbook`, or another
set of criteria), P2-NOT-AN-AMENDMENT (any of `answers`, `about`, `words`), P2-UNREADABLE (a copy that cannot be read: fail closed, since a
skipped copy would reset the record). The usual field rules apply. The writes: `restorer.restore(owner, name, copy)`, then
`store.write_contract(owner, name, meta, notes, archive_version=old.version)` with `version = old.version + 1` and `created = old.created`
(the amendment rule of today), `defined_by = root`, `defined = now`. The event is `service.define` with `amendment=True` (no new field).

**What it keeps.** `DerivedCaseHistory.cases` reads root's requests since the unchanged `created`, so every earlier case is a case of the
continued service again, with its verdicts, link notes, judged deliveries and relayed reworks (all in root's mailbox, which no retirement
moves). The criteria ids continue (`number_criteria` over the copied versions); `stored_basis`, `answering_version` and `answer_ids` read the
copied versions; the playbook continues at its version, so the owner's next revision is gated by P1 (no new exempt first version); P2's
gate (5.2) and P4's base (7.1) then see the whole record. What stays in the retired tree: the old team's mailboxes, run logs and work files.
So the old cases count 0 runs (the run counter reads the live team's logs), and P3 and P4 compare the old artifacts with the org history
only (the current file of a moved path is `None`: 6.3 skips the pair, 7.2 counts it as changed).

**Texts.**
- Reply (services, so MCP and the CLI show it): `defined service `{name}` for {owner} again: it continues the retired one kept at {path}
  (contract v{n} -> v{n+1}, {playbook v{p} | no playbook yet}, {k} request(s) with a result and their record). {record}`, then today's
  `Changed:` lines when other fields changed. `{record}` is read after the write from `ServiceEvidence.amendment_basis(owner, name)`:
  `Still open: rejection R1 (message <id>) has no answer; {n} delivered request(s) have no verdict: <ids>. Record them before the criteria
  change (feedback first).` (only the parts that apply), or `Every delivery has its verdict and every rejection its answer.`; `""` on
  `OrgError`/`OSError` (advisory).
- Owner's note (wake False), title `service {name} continued as contract v{n+1}`, body: `{actor} defined the service `{name}` again: it
  continues the retired one kept at {path}. Contract v{n+1} has the criteria of v{n}; playbook {v<p> | none yet}; every earlier request is a
  case of it again.`, then the changes.
- MCP root `retire` (`SRC/mcp_server/_tools_hiring.py:HiringTools`, root only, advisory). Before the retirement, when `addr` is top-level,
  the tool reads `catalog.service_names(addr)` and `evidence.amendment_basis(addr, name)` of each; after a successful retirement it appends
  `\nKept with {addr}: {services}. Defining one of them again for {addr} continues its contract, playbook and cases (when a request of it has a result).{ Still open in `{name}`: rejection R1 (message <id>) has no answer; {n} delivered request(s) without a verdict: <ids>.} Tell the
  user.` (nothing when the agent offers no service; nothing on a read error). `HiringTools` gets `catalog: Provider[ServiceCatalog]` and
  `evidence: Provider[ServiceEvidence]` (`wire_mcp_server.py`); the `retire` docstring and every surface golden stay unchanged. Agents'
  `retire` and the CLI `retire` print today's text (the terminal is the user's own seat, D15).

**Why this, and not refusing the team retirement** (the review's option (a), DR-28). The manager's directive keeps the user's authority over
the structure, and the continuation is sound on every path that could reset the record invisibly: the same owner and name is the only shape
`services` cannot tell from the old service, and it now continues; the retired copy is never changed, so nothing is lost if the continuation
is itself retired (its copy then holds the whole lineage); a copy that cannot be read refuses the definition; the continuing call cannot
change the criteria, and every later change meets the gate with the whole record. What remains are the visible shapes of 5.8 (another owner,
another name), declared and counted (D22).

## 6. P3, the partial form (D-E4-3; gate 3 P3, "A cheaper, partial alternative")

### 6.1 `progress` flags `blocked` results with client questions

`SRC/progress/_lines.py:CaseTaskLines._questions_to_ask` moves to `reflection.questions_open(task, result, case, mail.sent(ROOT))` (section 3)
and changes `if result.status != "done"` to `if result.status not in ("done", "blocked")`; the settling rules are unchanged (a human rework
of the task or the client's verdict on the delivery ends the flag; a relayed rework does not, 0a.1 DR-17). `CaseTaskLines.line` computes
`asked` for `done` and `blocked` results and appends the flag part
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
        """The files in the deliverable folders (``deliverable.path`` of the contracts) of the services ``actor`` requests (or only the folder
        of ``service``) that differ from the team's last checked version, that the team never wrote, or that could not be read; settled ones
        are left out. Never reads outside a folder; never raises for an unreadable folder, file or history."""
```

```python
@dataclass(frozen=True)
class DeliverableFinding:
    folder: str                # the folder as resolved (for a contract that names a file: that file's folder)
    services: tuple[str, ...]  # every service whose contract names this folder (or this file), sorted
    name: str                  # the file name inside it ("" for the folder itself)
    kind: str                  # "differs" | "unknown" | "link" | "large" | "limit" | "unreadable"
    artifact: str              # the team's artifact it was compared with ("" unless "differs")
    task: str                  # the task whose done result last listed that artifact ("" unless "differs")
    withheld: bool = False     # that result still has open client questions (questions_open > 0): its artifact path is not shown
    error: str = ""            # for "unreadable": the error's text
    file: bool = False         # the contract names this file itself, not a folder (DR-32)
```
and a pure renderer `deliverables_note(findings) -> str` (`""` for none). Its text, one block per folder:

```
Deliverable folder {folder} ({services}): {n} file(s) the team did not deliver as checked. Tell the user what changed and why; never patch a deliverable yourself (send it back with revises):
- {name}: differs from {artifact} as the team checked it (task {task})
- {name}: differs from the team's checked version (task {task}; path withheld: ask first)
- {name}: never written by the team
- {name}: a link, not read (hirearchy reads only files inside the folder)
- {name}: not read (larger than 4 MiB)
- {name}: not read (this check reads at most 32 MiB in all)
- {name}: cannot be read ({error})
```
`{services}` is ``service `a` `` or ``services `a`, `b` ``. The second line replaces the first when `withheld` (6.2 withholds the same path
while the questions are open). At most 10 file lines per folder, then `- and {k} more`. An unreadable folder is the single line
`Deliverable folder {folder} ({services}) cannot be read ({error}).`; a folder that is a link, or one of whose components became a link
while it was read, is the single line `Deliverable folder {folder} ({services}) is a link: not read (hirearchy reads only the folder the
contract names).` A contract that names a file (`file`) has the heading `Deliverable file {folder}/{name} ({services}): it is not what the
team delivered as checked. Tell the user what changed and why; never patch a deliverable yourself (send it back with revises):` and its one
line without the `{name}: ` prefix (for example `- differs from lead/writer/work/memo.md as the team checked it (task ...)`). `{name}` and
`{folder}` are rendered by `shown_name` ("Names" below).

**Folders.** The services are `catalog.requestable_services(actor)` (for root: the top-level agents' services), or only `service`. Each
service's path is resolved (containment steps 1-2 below). Services whose folders resolve to the same path form one **group**, shown as one
block that names them all. Whether a contract names a folder or a file is decided per contract by the walk (containment, step 3 below) **before** groups are formed (DR-45). A contract whose path names a file (an existing regular file; a name not there yet gives no findings) forms a **single-file group** keyed by the file's resolved path; when that file's folder is also a folder group, the file is checked once, as an entry of that folder group, by the **file rule** below (`differs` or no finding, never `unknown`), its services join that group's comparison basis, and the group's block names them too. The blueprint examples at `blueprint/_example_texts.py:34, 81, 179` are one-off `needs.deliverable` paths; the service examples at `:267, 279, 303` name a FOLDER. With `service` given (`progress(task_id)` of a service request), the group of its path is checked (all
its members still form the comparison basis) and only that block is shown; a one-off task gives no block.

**Comparison basis** (per group; the default `deliverables/` folder is shared by every service and every one-off goal, SKILL 1.2 and
ROOT_INSTRUCTIONS step 1, so the basis is the union):
- *Candidate results*: for every service of the group, the newest 20 tasks of its cases (by result id) whose latest result is `done`; plus
  the newest 20 of root's own one-off tasks (root's sent `task`s without `service`) whose latest result is `done`. Of each result, its first 10
  org-relative paths of `artifact_paths(result.body)` (no leading `/`, no `..` or empty segment, not a directory). Absolute (workspace)
  artifacts are not compared (no history): a file whose basename matches only such an artifact gives no finding.
- *The checked version of a pair (result R, path P)*: `CheckedVersions.at_result(R, P)`, the blob of `P` at the first org-git commit that holds
  `R`'s sent copy (`<sender>/sent/<R.id>.md`; the scheduler commits after every run, `RunSettlement.settle`, so that commit has the artifact as
  the team reported it). `None` (no repository, git missing, not committed yet, or past the git bound): `CheckedVersions.current(P, hexlen)`,
  the org file now (best effort; section 22).
- *A file `F` of the folder* (bytes `b`):
  1. **Basename match** (no git needed to find it): the candidate pairs whose `P` has `F`'s name as its basename. A pair whose checked
     version is unknown on both sides (`at_result` and `current` both `None`: the team's file was moved, as after a team retirement, or
     deleted) is dropped. If pairs remain, `F` is compared with the checked version of the **newest** of them: `blob_id(b, len(checked))`
     equal: no finding; different: `differs`, with `artifact = P`, `task = R.reply_to` and
     `withheld = questions_open(task, R, case, mail.sent(ROOT)) > 0`. If none remains, `F` goes to step 2.
  2. **No basename match** (a renamed copy, another service's or the user's file), computed lazily, only when such a file exists: equal to the
     current org file of any candidate path (`current`, no git), or to the checked version of any candidate pair that the git bound still
     allows (newest first): no finding; else `unknown` ("never written by the team").
- *A single-file group* (`file`; its one file `F` is opened as in step 5 below, through its folder's descriptor): the basename pairs of step 1
  when there are any, else every pair of the **newest** candidate result (a contract that names `memo.md` while the team writes
  `2026-10-05-memo.md`). The same rule checks a file contract that is an entry of a folder group (DR-45). Equal to the checked version of any of them: no finding; else `differs` from the first of them (the basename match,
  or that result's first artifact), with its task and `withheld`; with no candidate result at all: `unknown`. A missing file gives no
  finding (nothing was copied yet).
- *Git bound*: one `findings` call asks `at_result` for at most 40 distinct pairs and spends at most 5 s of git time (measured with
  `kernel.Clock.monotonic`, read before each pair; `FolderDeliverableChecks` gets the clock). Each git subprocess has a 2 s timeout, so a call spends at most about 11 s on git (5 s, plus the last pair's two subprocesses of 2 s each, plus 2 s for the one `head` lookup below). Basename matches are asked
  first, newest first; past either bound, the remaining pairs use `current`. `GitCheckedVersions` memoizes answers per (result id, path) for
  the life of the runtime: non-`None` answers for good (commits are immutable), `None` answers under the `HEAD` they were asked at
  (`OrgHistory.head()`, read once per `findings` call), so a pair not committed yet is asked again only after the next commit. The CLI, a fresh
  process per call, is held to the same bounds. A `progress(wait_seconds=N)` call computes the note once, in the text it returns after the
  wait (`_wait.py` renders only on return).
- *Bytes*: one `findings` call reads at most 32 MiB of deliverable files in all (`READ_TOTAL`), on top of the 4 MiB limit per file; a file
  whose `st_size` exceeds what is left is not read (`limit`). Folders are read in group order, files in name order.
- *Object format*: `hexlen` is the length of the checked id read from git (40 for sha1, 64 for sha256 repositories). When a group has no
  checked id at all (no repository), both sides of every comparison are `current` blobs and `blob_id` with 40 is used for both.
- *Settled* (only the user's own judgement settles a finding): a `differs` finding is left out once its case has a **human-tier** verdict
  (`verdict_tier(m) == "human"`) recorded at or after the file's mtime (the verdict id's timestamp in microseconds against `st_mtime_ns //
  1000`, both UTC); an `unknown` one once a case of any service of the group has such a verdict. A relayed verdict never settles one, so the
  assistant's own `feedback(task, "accept")` right after its own edit leaves the finding shown. Files whose mtime is before the earliest
  `Contract.created` of the group's services are ignored (the user's own older files); when none of them has `created` (legacy contracts),
  there is no floor.

**Path containment and reading** (`SRC/reflection/_deliverables.py:FsDeliverableFolder`, behind a private port `DeliverableFolder` in
`reflection/_ports.py`; the only code that touches a deliverable folder):
1. `raw = contract.deliverable.get("path")`; not a non-empty `str`: the service is skipped. `p = Path(raw).expanduser()`; not absolute (a
   hand-edited contract): skipped.
2. `named = Path(os.path.normpath(p))` (lexical) and `target = p.resolve(strict=False)` (normalizes `..` and follows the links of the path
   as it is now, such as macOS `/tmp` -> `/private/tmp`: the user chose that place). **A link as the last component**: `os.lstat(named)` is a
   symbolic link (`deliverables -> ~/.ssh`, which an agent with shell and an overlapping workspace could make): the folder-level `link`
   finding, nothing read. `FileNotFoundError` on `lstat`: go on with `target` (the walk below decides).
3. **The walk** (a component that becomes a link after the resolve is never followed; DR-43): `fd = os.open("/", O_RDONLY | O_DIRECTORY | O_CLOEXEC)` and `pending = ""` (the traverse-only components carried so far, each followed by `/`); then, for each component `part` of `target.parts[1:]` in turn (descriptors closed in a `finally`):
   - `os.open(pending + part, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC, dir_fd=fd)`. On success it is the new `fd` (the previous one is closed) and `pending` is reset; before the walk goes on, every carried component is `os.stat`ed again (`follow_symlinks=False`): one that is no longer the same directory (`(st_dev, st_ino)` changed, or now a link) gives the folder-level `link` finding, nothing read. `O_NOFOLLOW` guards the component just opened.
   - `ENOTDIR` or `ELOOP` (the open refused a link or a non-directory; which of the two a system reports for a link opened with `O_DIRECTORY | O_NOFOLLOW` differs): `st = os.stat(pending + part, dir_fd=fd, follow_symlinks=False)`; `S_ISLNK`: the folder-level `link` finding, nothing read; `S_ISREG` and `part` is the last component: the contract is a **single-file group**, and step 5 runs on `pending + part` with `dfd = fd`; anything else: skipped.
   - `EACCES` on a component that is **not** the last (a traverse-only parent, mode `--x`: it can be passed through but not opened for listing; measured on macOS: `os.open` of a 0o311 directory gives `EACCES`, while `os.open("p/f", ..., dir_fd=gp)` succeeds): `st = os.stat(pending + part, dir_fd=fd, follow_symlinks=False)`; `S_ISLNK`: `link`; not `S_ISDIR`: skipped; else its `(st_dev, st_ino)` is remembered, `part + "/"` is appended to `pending` and the walk goes on with the next component (`fd` unchanged). It is **not** reported as `unreadable`.
   - `EACCES` on the last component (the folder itself): the folder-level `unreadable` finding. `ENOENT` on any component: skipped, no findings (nothing there yet: no folder, or a file not copied yet). Other `OSError`: `unreadable`.
   The descriptor of the last component, `dfd`, is the folder; it is closed in a `finally`.
4. `os.scandir(dfd)` (file descriptors are supported on macOS and Linux: `os.scandir in os.supports_fd` and `os.open in os.supports_dir_fd`
   are true on the project's Python 3.11), entries sorted by name, names starting with `.` skipped (`.DS_Store`), at most 200 entries; never
   recursive.
5. Each entry (and the one file of a single-file group): `entry.is_symlink()`: `link` (never followed, never read). Not
   `entry.is_file(follow_symlinks=False)` (directory, FIFO, socket, device): skipped, never opened. Otherwise
   `fd = os.open(entry.name, O_RDONLY | O_NOFOLLOW | O_NONBLOCK | O_CLOEXEC, dir_fd=dfd)` (`O_NOFOLLOW`: the entry cannot have become a
   link; `O_NONBLOCK`: a FIFO swapped in cannot block `progress`). `os.fstat(fd)` must be a regular file (`stat.S_ISREG`, else skipped) with
   `st_size` at most 4 MiB (else `large`) and at most what is left of the 32 MiB of the call (else `limit`); then at most 4 MiB + 1 bytes are
   read with `os.read(fd, 65536)` in a loop (more than 4 MiB read: `large`); `fd` is closed in a `finally`. A hard link (`st_nlink > 1`) is
   a regular file of the folder and is read like any other (only its hash is kept). The bytes never leave the process: only their blob id
   and the entry's mtime are kept.
6. `OSError` on `scandir`: one `unreadable` finding for the folder; `OSError` on one entry: `unreadable` for it, except `ELOOP` from
   `O_NOFOLLOW`, which is `link`.

Nothing outside the named place is opened: the objects opened are the components of `target` (as directories, never through a link that
appeared after the resolve), the folder itself and its direct entries, by name relative to the folder's descriptor. What remains: a link in
an earlier component that existed **before** the resolve is followed (the user's own layout, such as `/tmp`); an agent that can replace a
parent of the user's folder by a link before `progress` runs can point the check at another folder, and then only the names and hashes of
its direct files are used, never their contents (section 22). Declared residual (DR-43): a traverse-only parent swapped for a link and swapped back between its two `stat`s is not detected; the same bound holds for it.

**Names.** File names reach root's tool output, and an org agent with a workspace can create a file whose name carries newlines or
instructions, so names are a prompt-injection channel. `shown_name(text, limit)` (`SRC/reflection/_deliverables.py`) renders every name and
folder: `json.dumps(text, ensure_ascii=False)` (one double-quoted line; quotes, backslashes and control characters escaped), then each
remaining character that is not `str.isprintable()` (for example U+2028) as `\u{ord:04x}`, then `clip_line(..., limit)` (120 for a name,
200 for a folder). The note never shows file contents.

**History reads** go through a private port `CheckedVersions` (`SRC/reflection/_ports.py`), implemented in `SRC/app` by `GitCheckedVersions`
over the new `snapshots.OrgHistory` (6.4), `snapshots.blob_id` and `kernel.OrgLayout`:

```python
class CheckedVersions(Protocol):
    def at_result(self, result: Message, path: str) -> tuple[str, str] | None:
        """(commit, blob id) of ``path`` (org-relative) at the first commit that holds ``result``'s sent copy; None when unknown."""
    def current(self, path: str, hexlen: int) -> str | None:
        """The blob id (``hexlen`` 40 or 64: the object format of the ids it is compared with) of the org file now; None when it is missing,
        not a regular file, larger than 4 MiB, or resolves outside the organization."""
    def text(self, commit: str, path: str, limit: int) -> bytes | None:
        """The bytes of ``path`` at ``commit``; None when absent or larger than ``limit`` bytes."""
```
`GitCheckedVersions` memoizes `at_result` answers per (result id, path) for the life of the runtime (non-`None` answers for good, since
commits are immutable; `None` answers under the `HEAD` they were asked at, "Git bound" above). `current` checks that the resolved path is
inside the organization root, then reads it with the same `O_NOFOLLOW | O_NONBLOCK` open and 4 MiB bound as step 5.

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
    def head(self) -> str | None:
        """The commit ``HEAD`` names now (the key under which ``None`` answers are memoized, 6.3)."""
```
`GitClient` (`SubprocessGit`) gains three read methods (4 -> 7, under R7's 8), all run as `git --literal-pathspecs ...` (so `*`, `?` and
`:(...)` in an artifact path are literal characters, not pathspec magic), with `cwd=root`, `capture_output=True`, a 2 s timeout and `None`
on a non-zero exit, a timeout or `OSError`: `added_by(root, path)` (`git log --format=%H --diff-filter=A -- <path>`, last line),
`object_id(root, spec)` (`git rev-parse --verify --quiet <spec>`; `head()` is `object_id(root, "HEAD")`), `cat(root, obj, limit)`
(`git cat-file -s <obj>` first: a size above `limit` answers `None` without reading the blob; then `git cat-file blob <obj>`). Input rules
(enforced in `GitOrgHistory`, before any call): `path` is relative, has no `..` or empty segment, does not start with `-`, contains none of
`:`, `^`, `~`, `@{` and `\` (so the `<commit>:<path>` spec can never be read as revision syntax), and is always passed after `--` (or inside
`<commit>:<path>`); `commit` matches `[0-9a-f]{40}` or `[0-9a-f]{64}`. Anything else gives `None` without running git (the caller then
compares with the current file).

### 6.5 Surfaces

- `SRC/progress/_render.py:RootTaskReport` gets a 5th collaborator `deliverables: DeliverableChecks` (after `roots`, `lines`, `queue`,
  `clock`); `render` appends `deliverables_note(findings(ROOT, service))` (split into lines) after the task lines and before
  `HumanQueue.lines()`. With `task_id`, only that task's service (no block for a one-off task); without, every service root requests.
  `SRC/progress/_function.py:progress` passes `rt.deliverable_checks`; the wiring in `SRC/app/wire_progress.py` passes the provider.
- `SRC/mcp_server/_tools_identity.py` and `_tools_status.py`: `IdentityTools` and `StatusTools` get `deliverables: Provider[DeliverableChecks]`;
  for `me == ROOT`, not in setup mode, `whoami` and `status` append `"\n\n" + note` when non-empty, before the stale-skill note
  (`with_deliverables_note(text, ...)`, the pattern of `with_stale_skill_note`). Agents never see it. With the floor batch merged, root's
  text is, in this order: the tree or summary, the scheduler line, the deliverables note, the floor note, the stale-skill note (the floor
  batch's design, section 7; 8.3).
- The CLI's `progress` shows it (same `ProgressReporter`); the CLI's `status` and `whoami` do not (the terminal is the user's own seat).
- Runtime fields: `deliverable_checks: DeliverableChecks` in `SRC/app/fields_reflection.py`, `org_history: OrgHistory` in
  `SRC/app/fields_snapshots.py`, and (section 7) `judged_versions: JudgedVersions` in `SRC/app/fields_services.py` beside `service_evidence`
  (a port of `services` that `reflection` implements; `wire_reflection` provides it). ARCHITECTURE section 3 lists the three Protocols, so
  `app/tests/test_runtime_fields.py` requires the fields.

### 6.6 What P3 partial cannot enforce

The assistant can still copy before asking (the path is in the result body) and can still patch: the patch is shown afterwards in every
`progress`, `status` and `whoami` until the user's own verdict follows it. Items nobody flagged (10.3(c)) are D-E4-5's measured rate, not a
refusal. A file beyond the git bound (40 pairs, 5 s) is compared with the current org file only, and a renamed copy of an old checked
version can be reported as `unknown` (a false "never written"; E5 counts the notes and checks each against the deliverables log). Files
beyond 32 MiB in one call are listed as not read (`limit`), not compared. A link in a parent of the deliverable folder that is there
before the check runs is followed (6.3, step 3); a traverse-only parent (mode `--x`) is walked through, not reported, and one swapped for a link and swapped back between its two `stat`s is not detected (DR-43). A contract that names a file is checked as that one file; one whose path is missing is
checked once something is there (E5 counts file-path contracts and their notes, section 21).

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
    texts: tuple[tuple[str, str], ...]  # (path, judged text) of the changed artifacts included (7.3: at most 6000 bytes of UTF-8 in all)

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
   `checked` is known and `versions.current(P, len(checked.blob)) != checked.blob`, or, without history, when a result of a task in `relayed`
   lists `P`. No changed path: `None`.
5. `texts`: in the order of `changed`, `versions.text(commit, P, JUDGED_BYTES)` (`JUDGED_BYTES = 6000`) decoded as UTF-8 (errors replaced),
   while the bytes included so far plus this one stay at most 6000; the others are listed without text (7.3). The limit is in **bytes** on
   both sides (`OrgHistory.text` and `CheckedVersions.text` limit bytes). E4's memos are 854 to 1 426 bytes
   (`EV/*/memos/versions/*`), so one judged memo is always included.

s2r: `J` = f230's result `...-lead-5314` (judged by `...-root-a9fd`), `relayed` = (`...-root-43b8`,), changed = (`lead/writer/work/2026-10-05-memo.md`,):
the human rework needs a base. s1r #24 (`...-root-3559`) and s3 #31 (`...-root-ff36`) likewise (s3's is replayed in section 10; s1r #24's is
not replayed, so it is a prediction). E4's other human reworks do not (a prediction from the memo version index, not replayed).

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
`### {path}: not included ({no org history | the judged texts here are limited to 6000 bytes}); it is in the organization's git history{ at commit <12 hex>}.`

**Placement and the prompt cut.** `TextRequestBodies.body` puts the base section **last**, after `## Note from the requester` (after
`## Deliverable` when there is no note), and adds one sentence to the `## Goal` paragraph: `The client's corrections apply to the version
they judged: see "## Base" at the end of this task.` (`base="delivered"`) or `The client's corrections apply to the current version: see
"## Base" at the end of this task.` (`base="latest"`). A task body longer than `RENDER_BODY_CHARS` (8 000 characters) is cut in the lead's
prompt by `Message.cut_body`, which appends `[... message cut: ... Read the rest with read(path="...") if you need it.]`. So the goal, the
request, the acceptance criteria, the deliverable and the requester's note (the user's corrections) are never displaced by the base
section: they come first, exactly as today, and the cut can only reach the base section's tail (the judged text), which the lead reads in
full in the task file with `read`. The judged text is not shortened to fit: at most 6000 bytes of it are in the task file (7.2 step 5).
Test (D3): a request whose criteria and note are long (the rest of the body 7 000 characters) with a 6 000-byte judged text: every criterion
and the note are inside `msg.render()`, the Goal sentence is there, and the cut pointer names the task file.

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
  refused: since the delivery the client judged (task {task}, result {result}), relayed rework {ids} (your own reading, not the client's) changed {paths}. Say which version the user's corrections apply to: base="delivered" (the lead restores the version they judged{, org-git commit <12 hex>}, then applies their corrections) or base="latest" (the relayed changes stay; tell the user) (CLI: --base delivered or --base latest). Nothing was sent.
  ```
- **P4-BASE-VALUE**: `refused: base must be "delivered" or "latest": {base}. Nothing was sent.` (the CLI's `choices` refuse other values first)
- **P4-BASE-WHERE**: `refused: base goes only with a rework the user asked for: revises=<an earlier request of this service>, source="human" (CLI: --revises <task id> --source human). Nothing was sent.`
- **P4-USE-REQUEST** (closure; section 20, D2): `refused: {revises} is a request for the service `{service}`: send it back with request(service="{service}", inputs=..., revises="{revises}", source=...) (CLI: hirearchy request {service} --revises {revises}) so the rework stays in its case under the contract (and names its base when a relayed rework changed the delivery). Nothing was sent.`

Facade refusals (constants in `SRC/dispatch/_root_send.py`, raised by `check_root_send`, 7.5; section 20, D19):
- **FACADE-ROOT-TASK**: `refused: a root task for a service, or a rework, goes through request(...) or delegate(...), which apply the case rules (the contract, the base, the verdicts). Nothing was sent.`
- **FACADE-ROOT-VERDICT**: `refused: a verdict or a link from root goes through feedback(...), which applies the rules of a case (a delivered request, one answer per rejection). Nothing was sent.`

### 7.5 No bypass

`RuleServiceRequester.request` is reached by MCP root `request`, the CLI `request` (whose `--revises` defaults `source` to `human`) and
`Org.request`. The other ways root could send a rework of a service request, and what stops each:
- `delegate(revises=...)` (MCP `delegate`, CLI `task --revises`, `Org.delegate`), all through
  `SRC/dispatch/_assigner.py:RuleTaskAssigner.delegate`: when `actor == ROOT`, `revises` is given and `fields_for` answers a `service` (the
  revised task is a service request), it raises P4-USE-REQUEST before sending.
- `Org.send(ROOT, to, body, type="task", service=..., revises=..., source="human")`: the facade forwards every field to
  `runtime.message_sender.send`, which applies only the provenance rules. `SRC/app/_facade_dispatch.py:DispatchMixin.send` now first calls
  `dispatch.check_root_send(actor, type, service, revises, feedback, criterion)` (a pure function in `SRC/dispatch/_root_send.py`, exported
  from `dispatch.api`, so the rule and its texts live in `dispatch`, not in the composition root). For `norm(actor) == ROOT` it raises
  FACADE-ROOT-TASK on `type == "task"` with `service` or `revises`, and FACADE-ROOT-VERDICT on `type == "note"` with `feedback` or
  `criterion`; every other message passes unchanged (root's plain notes, budget grants, one-off tasks: `test_dispatch_facade.py:41` and the
  budget tests). The guard is in the facade, not in `RuleMessageSender`, because `RuleServiceRequester`, `RuleTaskAssigner` and
  `RuleClientFeedback` send those very shapes through `MessageSender` after their own rules. MCP and the CLI cannot reach the shapes at all:
  their `send` has no `type`, `service`, `revises`, `feedback` or `criterion` argument (pinned, 5.8).
- `Org.deliver(msg)`: the declared policy-free primitive (5.8), out of the guarantee.
Agents' delegations are not human reworks.

### 7.6 The tier travels into rework delegations

`SRC/services/_rework.py:ServiceReworkContext.fields_for(actor, revises)` is restructured (today it returns `{}` as soon as the revised task
has no `service`, which is exactly the lead's writer task):

```python
def fields_for(self, actor: str, revises: str) -> Mapping[str, object]:
    task = next((m for m in self._mail.sent(actor) if m.id == revises and m.type == "task"), None)
    if task is None:
        return {}                                   # not one of actor's tasks: nothing is inherited
    fields: dict[str, object] = {}
    if task.service:                                # a rework of a service request keeps its case (today's fields, unchanged)
        version = self._catalog.read_playbook(task.to, task.service).version if self._agents.exists(task.to) else 0
        fields.update(service=task.service, contract=task.contract, playbook=version)
    if actor != ROOT and task.trace:                # the tier of the work actor does in that case; never for root, never without a trace
        tier = self._tier(actor, task.trace)
        if tier is not None:
            fields["source"] = tier
    return fields
```
`_tier(actor, trace)`: among `mail.received(actor)`, the **newest** message (by id) with `type == "task"`, `sender != RUNTIME`, `trace ==
trace` (non-empty; `None == None` never matches, because a revised task without a trace returns before the lookup), and no final result from
`actor` (`latest_results(mail.sent(actor))` has none for it, or a `blocked` one); its `source` when it is in `SOURCES`, else `None`. It is the
tier of the work the agent is doing in that case: a lead's writer task revises the writer's earlier task, which carries no service and no
tier, so copying from the revised task would never fire (section 20, D1). s2r: for `...-lead-608b` (revises `...-lead-7124`, trace
`...-root-f230`) the newest open received task with that trace is `...-root-43b8` (`relayed`); for `...-lead-0e90` it is `...-root-342a`
(`human`). The `ReworkContext` docstring (`dispatch/api.py`) becomes: "The fields a rework task inherits from the task ``actor`` sent with id
``revises``: ``service`` and ``contract`` of that task and the ``playbook`` version current now when it is a service request, and, for an
agent, the ``source`` of the open task it received in the same trace. Empty when the task is not one of ``actor``'s." Its contract test
(`dispatch/tests/test_contract_rework_context.py`) gains: a non-service revised task with a trace gives only `source`; a revised task without
a trace gives no `source`; root never gets `source`; a received task with a final result is skipped.

`SRC/dispatch/_sender.py:provenance_source` gains `inherited: str | None = None`: for `actor != ROOT`, `type == "task"`, `revises` set,
`source is None` and `inherited in SOURCES`, it returns `inherited`. An agent's own `source` is refused exactly as today (S1); `inherited`
comes only from `RuleTaskAssigner.delegate` (`fields.get("source")`, now passed as `inherited=` besides `_service_fields(fields)`), never from
a tool argument. `MessageSender.send` gains the keyword
`inherited: str | None = None` (`RuleMessageSender`, `dispatch.testing.RecordingSender`); its docstring's provenance paragraph adds: "A task of an
agent that revises another carries the tier its sender works under (``inherited``, from ``ReworkContext``): the runtime's copy, never the agent's
declaration." s2r: `...-lead-608b` carries `source: relayed`, `...-lead-0e90` `source: human`.

### 7.7 What P4 cannot enforce

That the lead restores the file (gate: "still LLM behaviour"); without history the judged text is not in the task. `base="latest"` relies on
root telling the user. Three ways around the base remain, because the product cannot see the conversation: a rework the user asked for sent
with `source="relayed"` (the default) needs no base; so does a fresh `request` of the same input without `revises` (a new case); and so does
root's one-off `delegate` without `revises` to the owner ("redo the memo"), which is outside every case (5.8). All three are visible
afterwards (the rework is marked relayed in the owner's digest and in `progress`; the fresh request is a second case of the same input; the
one-off task is a root task without a service in `progress`), and E5 counts all three (section 21).

## 8. D-E4-6: root instructions and SKILL.md

### 8.1 `ROOT_INSTRUCTIONS` (`SRC/mcp_server/_instructions.py`)

Two lines are added (the skill line and the reject order), step 5 names `request` beside `delegate` for a rework (a service request sent
back with `delegate` is refused, 7.5), and five parentheticals whose content SKILL.md carries are cut, so the text fits. The confinement line
"(no other paths or ORG_ROOT)" is kept: it is a safety line, and sessions that never load the skill (E4's s1r) would lose it. Unified diff
against `3815813` (`difflib.unified_diff`, no context lines; the rest is unchanged):

```
@@ -3,2 +3,2 @@
-- Never claim the organization did work unless hirearchy tools show it.
-- If a hirearchy tool fails, tell the user instead of substituting another mechanism.
+- Never claim the org did work unless hirearchy tools show it; if a tool fails, tell the user instead of substituting.
+- Before you build an org or rate a delivery, activate the hirearchy skill.
@@ -6,0 +7 @@
+  On a reject: `feedback` first, then ONE yes/no question naming an id, then the change (`define_service(answers=...)`).
@@ -9,4 +10,3 @@
-   given (scope items, source files), never invent. Default deliverable place: a new
-   `deliverables/` folder in the current directory (say so). Also ask: format, length, exact checkable criteria,
-   sources/web, workspace and tests (code), budget in runs, models (all claude-sonnet-5.5; if cheaper: keep the lead and final verifier strong;
-   the lead decides how every other run is spent), review, approval.
+   given, never invent. Default deliverable place: a new `deliverables/` folder here (say so). Also ask: format,
+   length, exact checkable criteria, sources/web, workspace and tests (code), budget in runs, models (all claude-sonnet-5.5;
+   if cheaper: keep the lead and final verifier strong; the lead decides how every other run is spent), review, approval.
@@ -19 +19 @@
-   first check `status` for stranded runs and `reclaim` them (or tell the lead to).
+   first check `status` for stranded runs and `reclaim` them.
@@ -23,4 +23,4 @@
-5. When it is done: read the deliverable and check it against EVERY acceptance criterion (send it back with
-   `delegate(..., revises=...)` if not; never patch it yourself), copy it where they want it. `start` ends by
-   itself when the work is done (start again for more work); `stop` only if the user cancels, declines
-   more budget or you hand over an unverified result (say the task stays open). Final answer: as short as asked.
+5. When it is done: read the deliverable, check it against EVERY acceptance criterion (send it back with
+   `request`/`delegate(..., revises=...)` if not; never patch it yourself), copy it where they want it. `start` ends by
+   itself when the work is done; `stop` only if the user cancels, declines more budget or you hand over an
+   unverified result (say the task stays open). Final answer: as short as asked.
```

Measured for revision 3 on an export of the worktree at `1b385a2` (`git archive` into a scratch folder, since removed), with the
worktree's Python, importing the candidate `ROOT_INSTRUCTIONS` and formatting it exactly as `InstructionText._for_root` does
(`where = "The organization is at <path>."`): raw template **2 622** characters (tests `< 2700` and `test_finish_rules.py`'s `< 2800`;
today 2 558); at the reference path (`REFERENCE_ORG_PATH = "/" + "r" * 59`, `test_skill_services.py:15`) **2 699** (test `< 2700`, today
2 635; 1 character of headroom); with a 200-character path **2 839** (test `< 2900`); 26 lines (unchanged), longest template line 124.
The claim line keeps `tell the user instead of substituting`, which `mcp_server/tests/test_binding.py:98` and
`test_goal_tools.py:63-65` (`test_root_instructions_describe_the_workflow_and_keep_safety_lines`) pin as a safety phrase; neither test is
edited. With this text and K1-K4 of 8.2 applied, the tests that read the instructions or the skill were run on the export (574 tests:
`mcp_server/tests/` whole, `skill/tests/` whole, `app/tests/test_wire_mcp_server.py`, `test_wire_skill.py`, `blueprint/tests/test_apply.py`,
`test_round_f_guidance.py`, `test_round_g_assistant.py`, `cli/tests/test_commands_ops.py`, `tests/e2e/test_round7.py`): 573 passed, and the
one failure is the needle 8.2 replaces on purpose (`test_skill_org_growth.py:50`, "never pass `criterion` on the rejection itself", B9). The surface goldens
were not run there: E1 regenerates them. Every needle pinned today was checked present, including `never look for, create or modify
another`, `` `start` ends by``, `settle its warnings (e.g. model policy) with the user`, `instead of substituting`. Where each cut lives
on: "scope items, source files" (SKILL 1.1), "in the current directory" (SKILL 1.2 and its "here"), "or tell the lead to" (SKILL 4: "a lead
does it on its own team"), "start again for more work" (SKILL 4 and 5.7), "another mechanism" (implied by "substituting"). The floor
batch's merge only shortens the text (8.3: 2 642 at the reference path). New needle test
`test_root_instructions_name_the_skill_and_the_reject_order` (`SRC/mcp_server/tests/test_instructions.py`): `activate the hirearchy skill`,
``On a reject: `feedback` first, then ONE yes/no question naming an id, then the change``, ``send it back with
   `request`/`delegate(..., revises=...)``, `(no other paths or ORG_ROOT)`.

**Root's `delegate` docstring** (`SRC/mcp_server/_tools_tasks.py:_register_root_delegate`): after `revises: when sending work back for
rework, the id of the earlier task you sent to the same report.` insert `A service request is sent back with request(..., revises=...).`
(wrapped at today's column). Agents' `delegate` docstring is unchanged (`surface_manager*.txt` keep it).

### 8.2 SKILL.md (125 lines; net 0 per replacement)

| # | Lines at `3815813` | Becomes | Lines |
|---|---|---|---|
| K1 | 83-85 (step 4, rework bullet) | `- Never edit the org's artifacts to "fix" them: send the work back with `delegate(to=<top agent>, title=..., goal=<required changes>,` / `  acceptance=<the criteria, verbatim>, revises=<task id>)` (a service request: `request(service, inputs, revises=<task id>)`), or ask the user. If `progress` says the scheduler is stopped` / `  ("finished") and you sent more work, call `start()` again. Pass source="human" only on a rework the user asked for (the default is relayed); if a relayed rework changed the file after their verdict, also base="delivered" (what they judged) or base="latest" (say so).` | 3 -> 3 |
| K2 | 92 (step 5 item 3, first line) | `3. A done or blocked report's "Questions for the client:" (ambiguous items; `progress` flags them and withholds the path): ask them in plain words, with any question from item 2, in ONE` | 1 -> 1 |
| K3 | 95 (step 5 item 4) | `4. Then copy the deliverable to the requested path (the plan lists this step) and check it exists and matches. If `progress`, `status` or `whoami` name a file there the team did not deliver as checked, tell the user what changed and why.` | 1 -> 1 |
| K4 | 104-109 (step 5 item 6, from `another, make the item`) | block below | 6 -> 6 |

K4 (the reading on the rejection, 5.6 and D23, replaces 0a.1's "never pass `criterion` on the rejection itself"; as amended by DR-46, which names the terminal path too):
```
   another, make the item the clarification that settles both. "Always ..." is not their yes: ask the item first. Name the id you
   read the reject as, with `criterion` on the rejection itself (your reading, not their yes) in MCP `feedback` (at the terminal, `--criterion` on a reject records the answer): the reply then gives the exact question.
   On yes: `define_service(owner, name, add_acceptance=[<the new criterion>])` with `answers=<the rejection's message id>`, `about=<the id
   you asked about>` and `words=<their answer, verbatim>` (and `remove_acceptance` for a clarification): it records their yes; tell the user the resulting criteria. On no, a one-off or "as it is":
   `feedback(..., source="human", confirms=<the rejection's message id>)` with criterion "none", the R id or the existing C id. A change they ask for on their own, outside a rejection: `words=` alone. An owner's note
   with a question for the client is no new question (only your one item per reject asks one): read it with `inbox`, go on, and never reply to it or mention it. Never edit SERVICE.md or PLAYBOOK.md yourself.
```

Pinned needles kept (raw or flattened, checked against the replacement text): `` `define_service(owner, name, add_acceptance=[<the new criterion>])` ``,
`the resulting criteria`, `Never edit SERVICE.md or PLAYBOOK.md yourself`, `confirms=<the rejection's message id>`, `only your one item per
reject asks one`, `an owner's note with a question for the client is no new question`, `read it with `inbox`, go on, and never reply to it or
mention it`, `make the item the clarification that settles both`, `"always ..." is not their yes: ask the item first`,
`pass source="human" only on a rework the user asked for`, `"questions for the client:"`, `` `progress` flags them ``,
`with any question from item 2, in one message before you deliver`, `copy nothing until they are answered`, `4. then copy the deliverable`, and
the order `Reply briefly` before ``record\n   `feedback(``. One pinned needle is replaced on purpose: `test_skill_org_growth.py:50`'s
``never pass `criterion` on the rejection itself`` becomes ``with `criterion` on the rejection itself (your reading, not their yes)``, and
the test's docstring says why (E3's criterion on the rejection was taken for the yes; since 0a.1 it is relayed, and since 0a.2 an amendment
in the reject turn is refused, so naming the reading only gives the reply its id). Measured on the export with K1-K4: SKILL.md stays at 125
lines, and the ten tests that assert `<= 125` lines stay green (0a.1 8.1 lists them). New needle test
`test_the_skill_records_the_answer_with_define_service_and_names_the_base` (`SRC/skill/tests/test_skill_org_growth.py`) asserts `<= 125`
lines plus the needles of the replacements that exist at each commit, each K commit adding its own (section 18): B9 creates it with K4's
`answers=<the rejection's message id>`, `words=<their answer, verbatim>`, `` `words=` alone ``, the reading needle and, from DR-46, ``at the terminal, `--criterion` on a reject records the answer``; C2 adds K2's
`withholds the path`; C5 adds K3's `did not deliver as checked`; D3 adds K1's `base="delivered"`.

### 8.3 Merge order with the floor batch (D-E4-9)

The "org agent floor" batch (D-E4-9, `.worktrees/org-agent-floor`, branch `feat/org-agent-model-floor-effort`; in progress, 8 commits on
`3815813` at `9608c8c` when this revision was written) has its own design,
`/Volumes/workspace/hirearchy/.worktrees/org-agent-floor/docs/design/org-agent-model-floor.md`, whose section 7 fixes how the two branches
merge. 0a.2 adopts it as written:
- **`ROOT_INSTRUCTIONS` step 1** (file lines 27-30): the resolved text is the floor design's, which keeps 0a.2's rewrap and replaces the
  cheaper-models clause:
  ```
     given, never invent. Default deliverable place: a new `deliverables/` folder here (say so). Also ask: format,
     length, exact checkable criteria, sources/web, workspace and tests (code), budget in runs, models (all claude-sonnet-5.5
     at high effort; nothing below is available), review, approval.
  ```
  Measured with 8.1's candidate: 2 565 raw, **2 642** at the reference path, 2 782 with a 200-character path, 26 lines. The freed
  characters are not spent by 0a.2: they become headroom.
- **`IdentityTools`/`StatusTools` constructors**, the root branch of `whoami()`/`status()`, `wire_mcp_server.py` and the tool-group tests:
  both new parameters are kept, 0a.2's `deliverables` first. Root's text is, in this order: the tree or summary, the scheduler line, the
  deliverables note (6.5), the floor note (`with_floor_note`), the stale-skill note.
- **`surface_root*.txt`**: regenerated after the rebase (method G) in a commit `test(golden): regenerate the root surface after merging
  <the other batch>` that lists the diff.
- **SKILL.md**: 0a.2 changes lines 83-85, 92, 95 and 104-109 (8.2); the floor batch lines 37, 39, 40 and 117-118 (its section 6). They do
  not overlap; the second merge re-checks the 125-line cap and every pinned needle.
- **Count files**: neither branch raises a `count.txt` beyond its own tests; they are floors (`>=`).
- **`kiro/api.py`**: both branches export new names (0a.2: `throttled_without_effect`, `READ_ONLY_TOOL_IDS`, `THROTTLE_EXIT`); the merge
  keeps both sets in `__all__`. The floor batch passes `--effort` through the launcher's argv unchanged (its section 4), and 0a.2's launcher
  change (9.1) touches only the rendering state, `finish` and the exit code, so the two changes do not meet.
Whichever batch merges second rebases onto the other. E5 waits for both merges (D-E4-9). No 0a.2 test pins the model sentence.

## 9. D-E4-6: a throttled run is not charged and is retried once (F-E4-8)

### 9.1 Detection (facts, in the launcher: `SRC/kiro/_launch.py`, standard library only)

What kiro V3 actually sends decides the design (checked in `SRC/kiro/tests/golden/kiro-streams/ws4a.jsonl`, a real V3 recording, and in the
throttled run's transcript `EV/s2/run-logs/lead-reviewer/20261022T202454859379.log`):
- a built-in tool arrives as `tool_call` (with `kind`: `read`, `search`, `edit`, `delete`, ...) and then `tool_call_update`s **without**
  `kind`;
- an MCP tool arrives as `tool_call` **without** `kind` (title `@hirearchy/<tool>`, `rawInput: {"tool_id": "hirearchy::<tool>", ...}`), then
  updates; but some MCP calls arrive as an **update only** (no `tool_call` before it): the s2 transcript's line 178
  `[tool failed] Tool Call {"tool_id":"hirearchy::write",...}` has no `[tool]` line;
- a tool load arrives as an **update only**, `status: completed`, `title: "Tool Load"`, `rawInput: {"tool_ids": [...]}` (ws4a line 174; the s2
  transcript's line 169 `[tool ok] Tool Load {"tool_ids":["hirearchy::*"]}`).
The session store (`org-kiro-sessions/.../messages.jsonl`) records every call as a `tool_call` with `kind: "other"`, so it is not a model
of the stream and no fixture is built from it.

`RenderState` gains `calls: dict[str, tuple[str, str, bool]]` (toolCallId -> (`kind`, `tool_id`, `is_load`) as recorded from the
`tool_call`), `effects: int = 0`, `throttled: bool = False`.
- `tool_call` records the triple from its own fields: `kind` (`""` when absent), `rawInput.tool_id` (`""` when absent), and `is_load` =
  `rawInput` has a `tool_ids` list and no `tool_id`. A `tool_call` that already carries `status: "completed"` (not seen in a recording, but
  allowed by ACP) is also counted as its own completed update.
- `tool_call_update` with `status == "completed"` takes each of the three facts **from the update itself when it carries it** (`kind`;
  `rawInput.tool_id`; `rawInput.tool_ids`), else from the recorded call, else unknown. It adds 1 to `effects` unless the call is read-only:
  its kind is one of `read`, `search`, `think`, `fetch`; or it is a tool load; or its tool id is one of `READ_ONLY_TOOL_IDS =
  ("hirearchy::inbox", "hirearchy::read", "hirearchy::org_read", "hirearchy::status", "hirearchy::health", "hirearchy::progress",
  "hirearchy::whoami", "hirearchy::services", "hirearchy::observe")`. A completed update with none of the facts (no recorded call, no
  `rawInput`) is an effect (fail safe: charged as today). Unknown kinds and unknown tools count as effects. A `failed` update is no effect.
- `runError` sets `throttled` when `data.retryErrorType`, `data.data.retryErrorType` or the compact message (spaces removed) carries
  `"retryErrorType":"THROTTLING"` (the s2 line 179 form: the message ends `(code -32000): {"errorType":"ModelThrottleError","retryErrorType":"THROTTLING",...}`).
- `finish(state)` emits, after any flushed partial line, `# kiro: throttled by the model service (retryErrorType THROTTLING); tool effects: none`
  (or `...; tool effects: {n}`) when `throttled`. Constant `THROTTLE_MARK`; it starts with `# kiro:` like every launcher line, never with a
  run-log closing mark. Rendered transcript lines are unchanged (V3 design 5.2 table).
- **The launcher's verdict is its exit code** (the agent cannot write it). `_stream` returns its `RenderState`; `_supervise` then returns
  `THROTTLE_EXIT = 75` (`EX_TEMPFAIL` of `sysexits.h`, "temporary failure, retry") when `state.throttled and state.effects == 0`, else
  kiro's exit code as today, except that kiro's own 75 is returned as 1 on EVERY return path of `main` and `_supervise`, the "ended" branch included (`code or 1`), so 75 always means the launcher's verdict (DR-44) (V3 design 5.1 step 4
  gains this one exception; no code of `scheduler`, `runs`, `health` or `stalls` gives 75 a meaning today: searched). The mark stays in the
  transcript for the reader and for E5.
- Why both: agent message chunks are written to the transcript line by line, verbatim (`render_line`, `state.partial.split("\n")`), so an
  agent's text can contain a line equal to the mark, and even a forged `[run error] ...THROTTLING...` line before it. The exit code is the
  launcher's alone; the transcript rule below is a second check, never the only one.
- `SRC/kiro/api.py` exports `THROTTLE_EXIT`, `READ_ONLY_TOOL_IDS` and the pure parser `throttled_without_effect(tail: str) -> bool`: true
  only when the mark `...; tool effects: none` is the **last `# kiro:` line** of the tail (the last line starting with `# kiro:` before the runtime's closing line `# exit <code> after <n>s`, `runs/_format.py`) **and** a `[run error] ` line whose compact text (spaces removed) carries `"retryErrorType":"THROTTLING"` stands somewhere before it in the tail (DR-44). Other lines (kiro's stderr, which the supervisor interleaves) may sit between the run error and the mark, or after the mark up to the closing line. A genuine run gives the run error and then the mark (`render_line` flushes any partial agent line before it writes the `[run error]` line, and `finish` writes the mark next). A later `# kiro:` line after the mark, or no THROTTLING run error before it, makes it false: charged as today (fail safe). The launcher cannot import `observability` (standard library
  only), so the equality
  `READ_ONLY_TOOL_IDS == tuple(sorted("hirearchy::" + t for t in observability READ_ONLY_TOOLS))` is pinned by
  `TESTS/architecture/test_read_only_tool_ids.py`, which may import `hirearchy.observability._trace` (the top-level `tests/architecture`
  modules already import private modules, e.g. `test_tools.py`, `facade_cases.py`; R2 binds the packages under `src/`, not them). No
  `observability.api` export is added.

S2's throttled run under this rule: the update-only tool load (read-only, from the update's `rawInput.tool_ids`), `hirearchy::org_read`
(read-only by tool id), `Read File` (kind `read` from its recorded `tool_call`), the update-only `hirearchy::write` (`failed`: no effect), then
the `runError` with THROTTLING: `tool effects: none`.

### 9.2 The decision (in the scheduler; the charge stays derived)

The run log still exists (the run happened; `RunLogReader.count`, the dashboard's per-agent `runs_used` and `Org.runs_used` keep counting
it). It is not **charged** because a runtime credit note returns its run: `budget` is derived as received - handed down - runs, and the note
is received budget. No file kind is added, and the credit is an immutable note.

- New private port `ThrottleCredits` (`SRC/scheduler/_ports.py`), implemented by `SRC/scheduler/_throttle.py:CreditingThrottles(logs:
  RunLogReader, mail: MailboxReader, delivery: MessageDelivery)`: `credit(run: RunRecord) -> str` returns `""` (not credited), `"free"` or
  `"counted"`. Every fallible read comes first and the delivery is the last fallible action, so a reply of `""` always means "no credit
  exists":
  1. `tail, _ = logs.tail(run.log, 4096, 80)`; `not throttled_without_effect(tail)`: `""`.
  2. Belt and braces from the runtime's own record: any message in `mail.sent(run.addr)` whose id starts at or after the run's stem (first 21
     characters compared) means the run had an effect: `""`.
  3. `kind = "counted"` when the agent's previous run (the log right before `run.log` in `logs.files(addr)`) was credited too (its stem is
     in `kernel.credited_stems(mail.received(addr))`), else `"free"`: also for the agent's first run, and when `run.log` is not among
     `logs.files(addr)` (a log the listing does not show yet has no previous run to look at).
  4. Deliver `budget.run_credit(run.addr, run.log.stem)`: `Message(sender=RUNTIME, to=addr, type="note", budget=1, wake=False,
     title=run_credit_title(addr, stem), body=...)`, body: `Your run {addr}@{stem} ended on a model-service throttle (retryErrorType
     THROTTLING) before any tool effect, so it is not charged: this note returns its run. Your messages are back in your inbox; the run is
     started again.`; then return `kind`.
  Any `OSError`/`OrgError` in 1-4: `""` (charged as today) and the console line `{addr}: throttle credit not given: {error}`. An error in 4
  means the note was not written (the delivery pipeline writes the file last, atomically).
- `SRC/scheduler/_reaper.py:RunSettlement` gets `throttles: ThrottleCredits`; in `settle`, for `not ok`, before the failure count, and only
  when `exit.code == THROTTLE_EXIT` and the run was not killed (`not run.killed`: a timeout or a retirement kill has no launcher verdict):
  `kind = self._throttles.credit(run)`; every other failed run takes today's path without reading anything. `"free"`: no `failures.failed`
  (the retry is not a failure), console `{addr}: run throttled by the model service before any tool effect: not charged, retried`.
  `"counted"`: console `... not charged` and `failures.failed(...)` as today. `""`: today's path. `batches.end(addr, ok=False)` already
  returns the batch to the inbox (at least once), and the reaper runs before the starter in each tick, so the credit is there before the next
  admission (`BudgetGate.admit` sees the run back).
- **Retried once** = one retry free of the failure count. A second throttle in a row is still not charged but counts as a failure; after it the
  existing rule applies (the batch is retried while failures < `max_failures`, then the agent is paused and its parent and root are told).
  A throttle storm therefore costs no budget and at most `max_failures + 1` runs before a human sees it (`max_failures` is 3 by default,
  `settings/_config.py`; it is not validated as at least 1, and with 0 the existing rule pauses at the first counted failure, so the bound
  holds for every value).
- **The case and progress counts leave credited runs out** (the user-visible totals and the overspend warning must agree with the budget the
  agent was charged). `SRC/reflection/_runs.py:LogRunCounter` gets `mail: MailboxReader` (its 2nd collaborator; `app/wire_reflection.py` and
  `reflection/testing.py` pass it) and `runs_between` skips a log whose stem is in `credited_stems(mail.received(addr))`, so `Case.runs`,
  `case_spend`, `case_total` ("exceeds the budget ... tell the user") and the digest count charged runs. `SRC/progress/_counts.py:
  LogRunCounts._window` (it already has `mail`) skips the same logs in `used`, so `runs_text` and `kept` agree with the agent's derived
  budget (a credited run is neither used nor kept). The run counts of `observability` (traces, metrics, `runs_used` in checks) keep every
  run: they report what ran, and the conservation check adds the credits (next bullet).
- **Conservation** (`SRC/observability/_checks/_budget.py:BudgetConserved`): credits enter budget from the runtime, so
  `handed down + credited == held + used + returned + dropped (+ in delivery)`. `credited` = the budget of every run credit
  (`kernel.is_run_credit` on the front matter) in a received box of a live agent, plus `RetiredArchive.credited()` (new, `SRC/agents/_retired.py`:
  the same over the retired trees' received boxes; `RetiredArchive` 3 -> 4 methods). The equation text gains ` + {c} credited` after `handed
  down {h}` only when `c > 0`, so every existing check text and golden is unchanged.

### 9.3 Tests

- `SRC/kiro/tests/test_launch.py`: a new stream `SRC/kiro/tests/golden/kiro-streams/f-e4-8-throttle.jsonl`, hand-built (documented in its
  first test's docstring) in the **event order of the s2 transcript** (`EV/s2/run-logs/lead-reviewer/20261022T202454859379.log` lines
  169-179) with the **event shapes of `ws4a.jsonl`**: `runStarted`; an update-only completed `Tool Load` with `rawInput: {"tool_ids":
  ["hirearchy::*"]}`; a `tool_call` without `kind` (title `@hirearchy/org_read`, `rawInput.tool_id: "hirearchy::org_read"`) and its
  completed update; a `tool_call` with `kind: "read"` (`Read File`, the notes path) and its completed update; an update-only failed `Tool
  Call` with `rawInput.tool_id: "hirearchy::write"`; the `runError` whose `message` is the text of line 179 after `[run error] prompt: `,
  verbatim. Expected last line: `...; tool effects: none`, and `main` returns `THROTTLE_EXIT`. Variants: the write update `completed`
  (`tool effects: 1`, kiro's code returned); an update-only tool load alone (none); an MCP `tool_call` without `kind` for `hirearchy::write`,
  completed (1); a completed update with no recorded call and no `rawInput` (1); an unknown kind (1); a `runError` without THROTTLING (no
  mark, kiro's code); a kiro that exits 75 without a throttle (the launcher returns 1); the mark never starts with a closing mark.
  `throttled_without_effect`: true on the fixture's transcript followed by `\n# exit 75 after 3s\n` (`test_true_when_kiro_stderr_lines_sit_between_the_run_error_and_the_mark` adds kiro stderr lines between the run error and the mark); false when a later `# kiro:` line follows the mark (`test_false_when_a_later_kiro_line_follows_the_mark`); false when no THROTTLING `[run error]` line precedes the mark; `test_kiros_own_75_is_returned_as_1_on_every_return_path` (`main` and `_supervise`, the "ended" branch included); and `test_a_forged_pair_in_agent_text_passes_the_transcript_rule_but_main_returns_kiros_code`: a **forged** pair, the mark and a `[run error] ...THROTTLING...` line written by the agent's text, can satisfy the transcript rule, but the launcher's exit code is kiro's own, never 75.
- `TESTS/architecture/test_read_only_tool_ids.py`: the equality of 9.1.
- `SRC/scheduler/tests/test_throttle.py` (unit, fakes): free credit; counted credit after a credited previous run; a message sent during the
  run (no credit); no mark (no credit); an unreadable log (no credit, console line); a delivery that raises (`""`, console line, and no note
  in the agent's received boxes); a run log missing from `logs.files(addr)` (`"free"`).
- `SRC/scheduler/tests/test_reaper_parts.py` (the existing file; A.4 P3): `settle` asks `ThrottleCredits` only for `exit.code == THROTTLE_EXIT` and a run that was not
  killed. **Forged mark** (`test_a_forged_mark_with_exit_1_or_a_kill_is_charged_and_counted`): a run whose transcript ends with the agent's forged `[run error] ...THROTTLING...` line and the mark, and that
  then fails another way (exit 1, or killed after the timeout), is charged and counted as a failure, and no credit note exists.
- `SRC/scheduler/tests/test_loop_throttle.py` (integration, `testkit.scheduler_loop` with the fake agent): a new switch of
  `TESTS/testkit/fake_agent.py`, `FAKE_THROTTLE_RUNS=N` (documented in its docstring), makes a run print a `[run error] ...` line carrying
  `"retryErrorType":"THROTTLING"` and then the mark, and exit `THROTTLE_EXIT`, while the agent's run-log count (its current run's log
  included) is at most `N`, then work as `FAKE_MODE` says. `N=1`: the agent's budget after the run equals the budget before it; one credit
  note; the retry ran and finished; `.runtime/failures.json` has no failure for it; root's `progress` says `runs 1 of ...` (the credited run
  left out: this assertion needs the counters of E5 and is added in the E5 commit, A.4 P5). `N=2`: two credits, one failure counted. A run that `send`s before the throttle: charged, failure counted. A run that prints the
  two lines but exits 1: charged, failure counted.
- `SRC/reflection/tests/test_run_counter.py` and `SRC/progress/tests/test_counts.py`: a credited log is not counted; a credit note for another
  agent's stem changes nothing; `case_total` of a case with one credited run does not say "exceeds".
- `SRC/observability/tests/test_checks.py`: conservation with a live credit and with a retired agent's credit.

## 10. Deterministic replays from E4's raw evidence

New file `TESTS/e2e/test_org_growth_0a2.py` with a small kit `TESTS/testkit/e4_replay.py`:
- `evidence(path) -> (meta, body)` reads a file under `EV` or `EV3` from the repository (`testkit.REPO / "studies" / ...`) with
  `kernel.split_frontmatter`; a missing file fails the test (never a skip). `tool_call(stream_dir, n) -> dict` reads call `#n`'s JSON arguments
  (the `arguments` object of the recorded `{"tool_id": ..., "arguments": {...}}`) in either recorded format: E4's `contract-loop.txt`, a line
  `[<time>] call #<n> turn <t> <tool> status=...` followed by a line `ARGS: {...}`; E3's `assistant-tool-calls.txt`, one line
  `[<time>] CALL #<n> <tool> status=... success=... args={...}` (the JSON is everything after `args=`). A call number that is absent, or
  present twice, fails the test. `lena_line(stream_dir, turn) -> str`: `turn-<NN>.prompt.txt` when it exists (E4), else the line after
  `######## LENA (prompt sent verbatim):` in `turn-<NN>.txt` (E3).
- `ReplayIds` (DR-42): maps the literal case ids of E4's evidence (a message id such as `20261022T182945409755-root-ed94`) to the ids of the
  replay's own organization, which differ; `C<k>` and `R<k>` pass through; an E4 id that is not bound fails the test (never a skip).
- `scripted_report(w, task_id, result_file, artifact_texts)`: writes each artifact (org path -> text, from `EV/<stream>/memos/versions/...`) in
  the org, reports the task through the lead's MCP `report` tool with the summary, artifacts and lessons parsed from the evidence result's
  `## ` sections, then commits through `org.runtime.snapshotter` (the `OrgSnapshotter` field) as `RunSettlement.settle` does after a run (real
  git, as the existing e2e tests use). A scripted writer reports each delegation the scripted lead makes, so no task is left open.
- Root's calls go through root's in-process MCP server; the lead's `revise_playbook` through the lead's. No scheduler, no LLM, no network; each
  test builds its own organization in `tmp_path`, with the stream's contract v1 (`acceptance`, `deliverable`, `budget`, `inputs` from the
  `SERVICE.v1` file) and playbook v1, and the deliverable path pointed at `tmp_path / "deliverables"`.

| Test | Built from (all under `EV` unless `EV3`) | Asserted outcome |
|---|---|---|
| `test_s1r_t5_an_amendment_before_the_verdict_is_refused` | `s1r/service/history--SERVICE.v1.md`; `s1r/playbook/PLAYBOOK.4435fd0.md`; `s1r/msgs/sent/20261022T182945409755-root-ed94.md`; `s1r/msgs/read/20261022T184536871337-lead-4f4d.md`; `s1r/memos/versions/memo-2026-10-05.v2.a358b76.md`; `s1r/contract-loop.txt` calls #21, #22, #23; `s1r/turn-05.prompt.txt` (Lena's T5, verbatim) | #21's arguments as made, before #22: **P2-UNRATED** naming `...-ed94`; with `words=<Lena's T5>` added: P2-UNRATED again. After #22 (`criterion=["C5"]`): the reply has `About C5: add` and `answers="{#22's id}"`; #21 + `words=<T5>`: **P2-OPEN-REJECTION**; + `answers, about="C5", words=<T5>`: **P2-WORDS-ARE-THE-REJECTION** (T5 is the #22 note with "No, not right yet." before it: the symmetric rule of section 3 catches it); `SERVICE.md` still v1 after each. The compliant path (#21 + `answers`, `about="C5"`, `words=<#23's note>`) is admitted: v2, a link from root naming `C8, C9`, `services` shows neither as "(not confirmed)". |
| `test_s1r_v3_and_v4_without_a_verdict_are_refused` | as above, plus `s1r/msgs/sent/20261022T190015448581-root-3559.md` (#24, memo 1's human rework) and its result `s1r/msgs/read/20261022T191112496455-lead-f84e.md`, `s1r/msgs/sent/20261022T191407596413-root-114d.md`, `s1r/msgs/read/20261022T192346320735-lead-fa63.md`, `s1r/memos/versions/memo-2026-10-12.v1.dfce3a4.md`, `s1r/service/history--SERVICE.v2.md` and `v3.md`, `s1r/contract-loop.txt` #24, #44, #45; `s1r/turn-09.prompt.txt` (Lena's reject of memo 2) | Setup: from v2 (the compliant T5/T6 of the first row), #24 is sent and reported with its evidence result `...-lead-f84e`, which is `status: blocked` as in E4, and **no verdict is recorded on it** (E4 recorded none): a blocked case has no delivery to rate, so it is not in `delivered_unrated`. Memo 2 (`...-114d`) is delivered (`...-lead-fa63`) and unrated. #44 (+ `words`) and #45 (+ `answers=<T5 rejection>`, `about="C9"`, `words`) are both **P2-UNRATED** naming `...-114d` only (`1 delivered request(s)`). After Lena's T9 reject of memo 2 is recorded (`source="human"`), #45 with the T5 rejection is **P2-ANSWERED** (`contract v2`), and #44 + `words` is **P2-OPEN-REJECTION** naming the T9 rejection; `SERVICE.md` stays v2 and `C9` current. |
| `test_s1r_playbook_v2_of_e4_is_refused_line_by_line` (the gate's P1 replay "of s1r") | `s1r/playbook/PLAYBOOK.4435fd0.md` (v1), `s1r/playbook/PLAYBOOK.e9bd92f.md` (E4's v2: its body verbatim as the content, its frontmatter `evidence` `[C9, R1, 20261022T182945409755-root-ed94]` as the evidence); `s1r/revise-playbook-attempts.txt` (the admitted attempt, `ok=True`); setup as the first row's compliant end state | E4's v2 replaced the line `none yet: add them from lessons and feedback` with three lines: `**C9 – Relative deadlines**: ...`, `**C8 – Structure**: ...` and `**Calendar arithmetic**: ...`. Under P1: **P1-REFUSED** listing all three (no `- and ... more` line), with `are not C8's or C9's words`, `Write it as "- C8: The memo's very first line` and `Write it as "- C9: Every Due value is an ISO date`; the playbook stays v1. C8 and C9 are both in `added` (C9 cited, C8 through R1's link: R1.about == (C8, C9), so citing R1 brings C8 into `added`, 4.1; in the replay the product's link names every added criterion, D8, where E4's link named only C9), and none of the three lines is either criterion's own words. (DR-42) Then v1 with that line replaced by `- C9: <C9's text>` and evidence `["C9"]`: admitted `c`, root's note lists `[C9] - C9: ...`. |
| `test_s1r_t8_the_artifact_path_is_withheld_while_the_question_is_open` | `s1r/msgs/sent/...-root-114d.md`; `s1r/msgs/read/...-lead-fa63.md` (its `Questions for the client:` block); `s1r/memos/versions/memo-2026-10-12.v1.dfce3a4.md`; `s1r/client-questions.txt` (progress #36); `s1r/deliverables-log.txt` (#40's `sed`) | `progress(task_id=114d)` has `artifacts withheld (ask first)` and `1 question for the client: ask the user before you copy or deliver`, and not `lead/writer/work/memo-2026-10-12.md`. After #40's edit is applied to a copy in the deliverable folder (`implemented a deploy freeze` -> `decided on a deploy freeze`), with the question still open: `progress`, `status` and `whoami` name `"memo-2026-10-12.md": differs from the team's checked version (task ...114d; path withheld: ask first)` and none of them shows `lead/writer/work/memo-2026-10-12.md`. A relayed `feedback(114d, "accept")` after the edit: the finding stays and the flag ends, so the line becomes `"memo-2026-10-12.md": differs from lead/writer/work/memo-2026-10-12.md as the team checked it (task ...114d)`. A human-tier verdict recorded after the edit: the finding is settled (no note). Separately, a human rework of 114d (instead of a verdict): `progress` shows the path again. Also `s3/msgs/read/20261022T222916707473-lead-96e9.md` (blocked, with a question): flagged. |
| `test_s2r_the_wrong_rule_is_refused_and_the_human_rework_needs_a_base` | `s2r/service/history--SERVICE.v1.md`, `history--SERVICE.v2.md`; `s2r/playbook/PLAYBOOK.2b6438a.md` (v1), `PLAYBOOK.6b06123.md` (v2); `s2r/revise-playbook-attempts.txt` (v2 arguments verbatim); `s2r/msgs/sent/` `...-root-f230`, `...-root-43b8` (and `s2r/injection/request-args.json`), `...-root-a9fd`, `...-root-342a`; `s2r/msgs/read/` `...-lead-5314`, `...-lead-c3dd`; `s2r/msgs/lead-sent/` `...-lead-608b`, `...-lead-0e90`; `s2r/memos/versions/2026-10-05-memo.v2.0aa3d3b.md` (judged, Marta 2026-10-14) and `v3.d8fd320.md` (injected, Marta none); `s2r/contract-loop.txt` (#31) | (1) the injected rework's writer delegation (a rework of the writer's task, sent while the lead works the relayed `43b8`) carries `source: relayed`; (2) the lead's service sections for the batch `[a9fd, 342a]` (`org.runtime.service_prompt_sections.prompt_sections("lead", batch)`, what the
scheduler puts in the lead's prompt) show `lessons (from a relayed rework, not the client's): "Rework needed`; (2a) `a9fd` is recorded with its note verbatim and root's reading `criterion=["C3"]` added (E4's assistant passed none; the reading is what the compliant 0a.2 flow passes, 5.6): its reply has `"About C3: add "<the rule, in their words>" as a lasting rule? Yes or no."` and `answers="<a9fd's id>", about="C3"`; recorded without the reading, the reply has `"About <its id>: add`, lists the current C ids, says `Next time, pass your reading as criterion on the rejection`, and contains no `C<k> is one of`; (3) after `a9fd`, `request(revises=f230, source="human")` without base: **P4-NEEDS-BASE** naming `...-43b8` and `lead/writer/work/2026-10-05-memo.md`; (4) with `base="delivered"`: the task body has `## Base: the version the client judged`, the commit that first holds `lead/sent/<5314>.md`, and the judged text with `| Marta |` ... `| 2026-10-14 |` and no `Open questions`: Marta's date survives; the writer delegation for it carries `source: human`; (5) #31 with `answers=a9fd`, `about="C3"`, `words="Yes, add it."`: admitted, link names `C9`; (6) the lead's `revise_playbook` with v2's exact content and `["R1", "C9"]`: **P1-REFUSED**, containing `are not C9's words` and both vague-deadline lines (`Flag any vague deadline as `none``, `Vague deadlines:`); playbook stays v1; (7) v1 with its `none yet: ...` line replaced by `- C9: <C9's text>`, evidence `["C9"]`: v2 `admitted: c`, root's note lists `[C9] - C9: ...`. |
| `test_s3_the_answered_amendment_is_admitted_and_only_its_words_enter_the_playbook` | `s3/service/history--SERVICE.v1.md`; `s3/playbook/PLAYBOOK.f6d34a7.md` (v1), `PLAYBOOK.dd2d1da.md` (v2); `s3/revise-playbook-attempts.txt`; `s3/contract-loop.txt` #12, #23, #30, #31, #37, #38; `s3/injection/request-args.json`; `s3/msgs/read/` `...-lead-de22`, `...-lead-ffba`, `...-lead-40d8`; `s3/memos/versions/memo-2026-10-05.v2.a526bb3.md`, `v3.b7f83c8.md` | #30 (the reject) recorded with its arguments and root's reading `criterion=["C3"]` added (E4's assistant passed none): its reply names `About C3: add`. #31 (human rework after the injected `fe20` changed the memo): P4-NEEDS-BASE, then admitted with `base="delivered"`; #37 with `answers=<#30's id>`, `about="C3"`, `words=<#38's note>`: **admitted** (the s3 flow), the product's link names `C8`; the lead's attempt 1 (v2 content, evidence `C8` + the product's link id + `88b2`): not "unknown evidence" (F-E4-7) but **P1-REFUSED** listing the riders (`(d) a 'Next meeting' footer`, `No other sections`, `(C1–C8) and the regression list verbatim`) and the changed step 4; v1 plus `- C8: <C8's text>`, evidence `[<the link id>]`: admitted `c` (a link-note id is evidence). |
| `test_e3_turn_5_an_amendment_in_the_reject_turn_is_refused` (replaces `test_11` of `test_org_growth_0a.py`) | `EV3/service/SERVICE.v1.md`; `EV3/assistant-tool-calls.txt` calls `CALL #24` (feedback, `criterion: ["C6", "C3"]`) and `CALL #25` (define_service), read by call number in E3's one-line format; `EV3/turn-05.txt` (the line after `######## LENA (prompt sent verbatim):`) | after #24: #25's arguments: **P2-NEEDS-WORDS**; + `words=<T5>`: **P2-OPEN-REJECTION**; + `answers=<#24's id>`, `about="C6"`, `words=<T5>`: **P2-WORDS-ARE-THE-REJECTION**; `SERVICE.md` v1; the reply of #24 names `About C6: add` (root's reading is the first id of #24's own `criterion`, `["C6", "C3"]`). |

D-E4-7 names s1r T5, s1r T8 and the s2r chain for E5; they are the first, fourth and fifth rows. The throttle replay is in 9.3.
Each replay lands in the commit that makes its last asserted text exist (section 18): s1r T5, s1r v3/v4, s1r's playbook v2 and E3 T5 in B6
(after B5, whose `QUESTION` they assert; the playbook replay's setup is the compliant T5 path, which needs B4 and B6, while its P1 text
exists since A3); s1r T8 in C5; s2r and s3 in D4 (they assert P1, P2 and P4 together).

## 11. Data model and the architecture rules

**New records (immutable)**: the product-written `confirms` link note (root -> owner; the shape `feedback(confirms=...)` writes today); the
runtime run-credit note (runtime -> agent, `budget: 1`, `wake: false`); on a continuation (5.10), byte-identical copies of a retired copy's
contract and playbook versions in the live service directory (the retired copy is never changed). **New keys on an existing immutable record**: `answers`, `about`,
`words`, `initiated` in a contract version's frontmatter (5.4); `source` on an agent's rework task (7.6, an existing `Message` field, now
copied by the runtime). **Derived, never stored**: line attribution (`Admission.lines`), confirmation and eligibility (`confirmed_criteria` with
the basis join), `AmendmentBasis`, `JudgedBase`, `DeliverableFinding`s, the throttle decision (from the launcher's exit code, the run log
and the mailbox), the continuation decision (from the retired copies and root's mailbox), root's reading (the rejection's own `criterion`,
an existing field). **Not added**:
no ledger, no `.runtime/*.json`, no file kind, no `Message` field, no event field, no frontmatter key on `PLAYBOOK.md`.

| Rule | How 0a.2 complies |
|---|---|
| R1-R2 | New public names in each `api.py` and `__all__`: `services`: `line_key`, `changed_lines`, `repeats_rejection`, `quoting_lines`, `AmendmentBasis`, `Rejection`, `JudgedBase`, `JudgedVersions`, `BASE_HEADING`, `ServiceEvidence.amendment_basis`; `reflection`: `DeliverableChecks`, `DeliverableFinding`, `deliverables_note`, `rated`, `questions_open`, `delivered_unrated`, `Verdict.link_notes`, `Case.lesson_sources`; `snapshots`: `OrgHistory`, `blob_id`; `kernel`: `strip_markers`, `artifact_paths`, `RUN_CREDIT_TITLE`, `run_credit_title`, `is_run_credit`, `credited_stems`; `dispatch`: `check_root_send`; `kiro`: `throttled_without_effect`, `READ_ONLY_TOOL_IDS`, `THROTTLE_EXIT`; `budget`: `run_credit`; `agents`: `RetiredArchive.credited`, `RetiredTree.addr` (a property); `snapshots`: also `OrgHistory.head`. Implementations stay in `_*.py` (`answering_version` and `answer_ids` are package-private in `services/_criteria.py`; `RetiredService`, `ContinuedServices` and `ServiceRestorer` in `services/_protocols.py`, `RecordedContinuations` in `services/_continue.py`); the app adapter `GitCheckedVersions` lives in `SRC/app`; the facade guard is one call to `dispatch.check_root_send`. |
| R3-R5 | No new edge: `reflection` uses `services`, `mail`, `kernel` (git through its own port, implemented in `app`); `services` uses `dispatch` (`MessageSender` for `LinkNotes`), `agents` (`RetiredArchive`) and `mail` (`MailboxReader`) for the continuation, and its own `ServiceEvidence` port (retirement); `progress` uses `reflection`; `mcp_server` uses `reflection` and `services` (root's `retire` note); `scheduler` uses `kiro`, `budget`, `mail`, `delivery`; `observability` uses `budget`, `agents`; `agents` uses `kernel`; `app` uses `dispatch` (the facade guard). All allowed in ARCHITECTURE 2.2 today (`tests/architecture/graph.py`: `services` may import kernel, agents, settings, mail, delivery, dispatch); no import-linter contract changes. The 2.2 row of `reflection` gains, in its "Reads, does not own" column, "the contracts' deliverable folders (direct files, read-only); the organization's git history (through a port implemented in `app`)", and the row of `services` gains "the retired copies of its services (`.retired`, read-only)" (commit 35). |
| R6 | Every new collaborator is typed by a Protocol: `LinkNotes`, `JudgedVersions`, `ServiceEvidence` (definer, retirement), `ContinuedServices`, `ServiceRestorer` (definer), `RetiredArchive`, `MailboxReader` (`RecordedContinuations`), `ServiceStore` (feedback), `DeliverableChecks` (progress, MCP tools), `ServiceCatalog`, `ServiceEvidence` (`HiringTools`), `CheckedVersions`, `DeliverableFolder`, `Clock`, `MailboxReader` (`LogRunCounter`) (reflection), `OrgHistory`/`GitClient` (snapshots), `ThrottleCredits`, `RunLogReader`, `MailboxReader`, `MessageDelivery` (scheduler). |
| R7 | `ServiceEvidence` 3 -> 4; `ServiceSteps` 3 -> 2; `GitClient` 4 -> 7; `OrgHistory` 4; `DeliverableChecks` 1; `JudgedVersions` 1; `ContinuedServices` 1; `ServiceRestorer` 1; `RetiredArchive` 3 -> 4; `ServiceStore` stays at 8 (`restore` is the separate `ServiceRestorer`, which `FsServiceStore` also implements); `MessageSender`, `ServiceCommands` (5), `ReworkContext` (1) keep their method counts (signatures widen). `Notices` (8, at the cap) is not touched: the credit text is `budget.run_credit`. |
| R8 | Contract suites: new `snapshots/tests/test_contract_org_history.py` (real git, memory fake), `reflection/tests/test_contract_deliverable_checks.py`, `services/tests/test_contract_judged_versions.py` (reflection implementation over the fs world, memory fake), `services/tests/test_contract_continued_services.py` (`RecordedContinuations` over the fs world and a memory fake: the newest copy, `fullmatch` of the name, a tree of another agent, no delivery, an unreadable copy; `FsServiceStore.restore` byte for byte, `SERVICE.md` last); extended `test_contract_service_evidence.py` (`amendment_basis`, `Rejection.question`, `admit(lines=)`), `test_contract_service_commands.py` (the retire gate, the continuation, `confirms` after an answer and its one recovery, `base`), `test_contract_git_client.py` (the read methods, `--literal-pathspecs`), `test_contract_message_sender.py` (`inherited`), `test_contract_rework_context.py` (the restructured `fields_for`: `source` without a service, none without a trace, none for root), `test_contract_retired_archive.py` (`credited`, `RetiredTree.addr`), `test_contract_service_steps.py` (no `amendment_step`). Fakes in the same commits: `services.testing.AdmittingServiceEvidence(basis=...)`, `NoJudgedVersions`/`FixedJudgedVersions`, `services.testing.NoContinuations`, `reflection.testing` world fields, `snapshots.testing.MemoryOrgHistory`, `mcp_server.testing.ScriptedSteps` (no `amendment`), `FixedDeliverableChecks`, `dispatch.testing.RecordingSender`, `blueprint.testing` command fakes, `cli/tests/_fakes.py`. Runtime fields: `deliverable_checks`, `judged_versions`, `org_history`. |
| R9 | No new writer and no new file kind. `SERVICE.md` keys and the continuation's copies: `services` (`FsServiceStore`, the single writer of `<owner>/services/**`); notes: `mail` through `delivery`; run logs untouched; the retired trees are read, never written. Reads outside the org: only the contract's deliverable folder (6.3, contained) and the git repository of the org (inside it). |
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
| `define_service` | the link note cannot be written after the contract was (`OrgError`/`OSError`) | recoverable | the owner's note is delivered first (5.2 step 4, the new ids marked `(not confirmed)`), then `OrgError`: `the contract of `{name}` is now v{n} (it answers rejection {id}), but the link that records the user's yes could not be written ({error}). Record it with feedback(task_id="{task}", verdict="reject", confirms="{id}", criterion=[{ids}], source="human", note=<their answer, verbatim>) (CLI: --confirms, --criterion, --source human, --note).` (`; the owner was not told either ({error})` is appended when the note's delivery failed too). That one link is still accepted by `feedback` (5.3) and makes the criteria confirmed (5.5); any other `confirms` on that rejection is P2-CONFIRMS-RECOVERY, any after it P2-CONFIRMS-ANSWERED. | `tool.call` failed; no snapshot commit by the CLI (the next commit includes the version) |
| `define_service` | the marks' `confirmed` read fails | advisory (0a.1 3.3) | the amendment as usual, every amended criterion marked | no |
| `define_service` (root, no live contract) | `ContinuedServices.continued` raises (`OSError`/`OrgError`: a retired copy or a mailbox cannot be read) | recoverable, fail closed (a skipped copy would reset the record) | P2-UNREADABLE; nothing written | `tool.call` refused |
| `define_service` (continuation) | a `playbook`, or another set of criteria | recoverable | P2-CONTINUES; nothing written | `tool.call` refused |
| `define_service` (continuation) | `restore` fails part way (`OSError`) | recoverable | the exception; the live directory may hold some copied files but no `SERVICE.md` (written last), so no service exists; a retry restores again (the same bytes) | `tool.call` failed |
| `define_service` (continuation) | `write_contract` fails after `restore` | recoverable | the exception; the live service is the retired copy restored exactly (v{n}, its `created`); a retry is an ordinary amendment of it (and a call that changes nothing gets today's "no change" text) | `tool.call` failed |
| `define_service` (continuation) | the `{record}` part of the reply cannot be read | advisory | the reply without it | no |
| MCP root `retire` | the services or their basis cannot be read before the retirement | advisory | today's reply, without the `Kept with` note; the retirement is unchanged | no |
| `retire_service` (root) | P2-RETIRE-UNRATED, P2-RETIRE-OPEN | recoverable | `OrgError` (5.3); nothing retired, no event, no note | `tool.call` refused |
| `retire_service` (root) | `amendment_basis` raises `OrgError`/`OSError` | recoverable, fail closed | P2-RETIRE-UNREADABLE | `tool.call` refused |
| `feedback(confirms=X)` | a contract version answers `X` and a human-tier link on `X` exists | recoverable | `OrgError` P2-CONFIRMS-ANSWERED; nothing recorded | `tool.call` refused |
| `feedback(confirms=X)` | a contract version answers `X`, no link on it yet, and other ids or another source than the recovery link | recoverable | `OrgError` P2-CONFIRMS-RECOVERY (it gives the one accepted call); nothing recorded | `tool.call` refused |
| `feedback(confirms=X)` | the stored versions cannot be read (`OSError`) | as today for unreadable service files | the exception (`answering_version` and `answer_ids` read the same files `criteria` reads before them) | as today |
| `request` (root) | P4 refusals | recoverable | `OrgError` (7.4); nothing sent | `tool.call` refused |
| `request` | `JudgedVersions.base`: git unavailable or slow (a git call past its 2 s timeout) | recoverable | the fallback of 7.2 step 4; the base section says `not included (no org history)` | no |
| `request` | mail or cases unreadable | as today | the exception | as today |
| `delegate` (root) | P4-USE-REQUEST | recoverable | `OrgError`; nothing sent | `tool.call` refused |
| `Org.send` (root) | FACADE-ROOT-TASK, FACADE-ROOT-VERDICT | recoverable (a programming error of the caller) | `OrgError`; nothing sent | no (the facade has no event of its own; the caller is in-process code) |
| `progress`, `status`, `whoami` | the deliverable folder or one file unreadable | recoverable | a finding of kind `unreadable` in the note | no |
| `progress`, `status`, `whoami` | the folder (or one of its components after the resolve) is a link | recoverable | the folder-level `link` line; nothing in it is read | no |
| `progress`, `status`, `whoami` | a parent component of the folder is traverse-only (mode `--x`) | recoverable | walked through; no finding (never `unreadable`, DR-43) | no |
| `progress`, `status`, `whoami` | the folder itself cannot be opened or listed | recoverable | the folder-level `unreadable` finding | no |
| `progress`, `status`, `whoami` | more than 32 MiB of deliverable files in one call | recoverable | `limit` lines for the files not read | no |
| `progress`, `status`, `whoami` | git slow or failing for the checked versions | recoverable | at most 40 pairs and 5 s of git time per call, each git call at most 2 s; a `None` answer falls back to the current org file | no |
| `progress`, `status`, `whoami` | `DeliverableChecks.findings` raises `OrgError`/`OSError` (catalog or mail) | recoverable | the text without the note (the `_step` rule of 0a.1: any other exception is a bug and propagates) | no |
| `OrgHistory` methods | no repository, git missing, timeout, non-zero exit, invalid input | recoverable | `None` | no |
| scheduler settle | `ThrottleCredits.credit` fails (`OSError`/`OrgError`) in any step | recoverable | the run is charged as today and counted as a failure; because the note's delivery is the last fallible step, a failure never leaves a credit note behind a charged report | console line `{addr}: throttle credit not given: {error}` |
| scheduler settle | a failed run whose exit code is not `THROTTLE_EXIT`, or that was killed (a forged mark in the agent's text included) | not a throttle | today's path: charged, counted; `ThrottleCredits` is not asked | as today |
| case and progress counts | the received boxes cannot be read for `credited_stems` | as today for unreadable mail | the exception, as every other mail read of `cases` | as today |
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
| `deliverable.path` of a contract (read time) | no | absolute `str`; resolved; an existing directory (a folder group) or an existing regular file (a single-file group, 6.3); the last component not a link | missing: no findings (nothing there yet); a link: the folder-level `link` line; anything else: skipped |
| files of the deliverable folder | - | direct regular files, not hidden, not links, <= 4 MiB each and 32 MiB per call (fstat and a bounded read of 4 MiB + 1 bytes), at most 200 entries, opened by name relative to the folder's descriptor (reached by a component walk with `O_NOFOLLOW`) with `O_NOFOLLOW \| O_NONBLOCK` | `link`, `large`, `limit`, `unreadable` findings; others skipped |
| file names and the folder path shown to root | - | any text | rendered by `shown_name` (one escaped, quoted line; 120 / 200 characters); never raw |
| artifact paths of results (P3, P4) | - | org-relative, no `..`, not a directory; resolved inside the org | not compared |
| git inputs (`OrgHistory`) | - | relative path without `..` or empty segment or leading `-`, without `:`, `^`, `~`, `@{` or `\`, always after `--` and under `--literal-pathspecs`; commit `[0-9a-f]{40}` or `{64}` | `None`, git not run |
| `Org.send` from root | - | `type == "task"` without `service` and `revises`; `type == "note"` without `feedback` and `criterion` | FACADE-ROOT-TASK, FACADE-ROOT-VERDICT |
| `retire_service` (root) | - | no new argument; the service's record must be complete (5.2a) | P2-RETIRE-UNRATED, P2-RETIRE-OPEN, P2-RETIRE-UNREADABLE |
| `define_service` (root) of a name with a retired copy that has a recorded request (a request with a result of any status) | - | no `playbook`; the acceptance set unchanged; no `answers`/`about`/`words` (5.10) | P2-CONTINUES, P2-NOT-AN-AMENDMENT |
| `feedback(reject, criterion=...)` on the rejection itself (root's reading) | no | the existing `criterion` rules (`normalize_links`, `ServiceEvidence.links`); the first current `C<k>` or earlier `R<j>` is the reading | as today; no reading: the reply's third form (5.6) |
| a retired copy's files (continuation) | - | only `SERVICE.md`, `PLAYBOOK.md`, `history/SERVICE.v\d+.md`, `history/PLAYBOOK.v\d+.md`, inside the organization; paths built from the layout and the archive, never from file contents | other files ignored; unreadable: P2-UNREADABLE |
| a `runError` event (launcher) | - | any JSON; THROTTLING detected in three places (9.1) | no mark |
| the launcher's exit code (scheduler) | - | `THROTTLE_EXIT` (75) only from the launcher's own verdict; kiro's own 75 becomes 1 | anything else: no credit |
| a run log tail (scheduler) | - | the last 4 096 bytes; the mark must be the last `# kiro:` line, with a THROTTLING `[run error]` line before it (DR-44) | no credit |

## 14. Invariants and their owners

| Invariant | Owner (layer) | Why there |
|---|---|---|
| A revision under rule (c) adds only the cited confirmed criterion's words; under rule (b) only lines tagged with a qualifying id | `reflection.CaseServiceEvidence.admit`, called by `services.RulePlaybookReviser` with `services.changed_lines` | the gate already owns admission; the reviser is the only writer of `PLAYBOOK.md` versions, reached by MCP and the facade |
| Lines are compared one way | `services.line_key` | the reviser, the gate and `quoting_lines` share it |
| Root changes the criteria only with a basis; one answer per rejection; verdicts before amendments | `services.RuleContractDefiner` | the only writer of `SERVICE.md`; every surface reaches it (5.8) |
| Root cannot reset a service's record by retiring the service while a verdict or an answer is missing | `services.RuleServiceRetirement` | the only path that moves a service under `.retired/`; every surface reaches it |
| Retiring the owner (or the service) never resets the record of the same owner and name: a root definition after it continues the retired copy that has a recorded request (a result of any status), and that call cannot change the criteria | `services.RuleContractDefiner` over `services.ContinuedServices` (which copy) and `ServiceRestorer` (the copy) | the definer is the only writer of `SERVICE.md` versions and every surface reaches it (5.8); the retirement itself stays the user's structural decision, unrefused |
| One rejection, one answer, in both directions (amendment after a link, link after an amendment, except the one recovery link of an answer whose link write failed) | `services._criteria.answering_version` and `answer_ids`, read by the definer and by `RuleClientFeedback` | both writers of an answer are in `services`; one reader of "a version answers it" and of "the ids its link names" |
| Root's verdicts, links and service reworks go through their rule classes | `dispatch.check_root_send`, applied by `dispatch.GuardedRootSender`, which the `Org` facade's `send` delegates to (A.4 P1; the only surface that can pass those fields) | MCP and CLI `send` cannot pass the fields (pinned); `RuleMessageSender` must keep accepting them from the rule classes |
| A user-initiated criterion is never (c)-eligible; only the product's link confirms an answered one | `reflection.confirmed_criteria` (basis join), read by the gate, step 3, the amendment note and `services` | one rule for every reader, as 0a.1's `confirmed_amendments` |
| The link that records an answer has one shape | `services.LinkNotes` | `feedback(confirms=)` and `define_service(answers=)` write it the same way |
| A human rework after relayed changes names its base | `services.RuleServiceRequester`; `dispatch.RuleTaskAssigner` refuses root's `delegate` of a service request | the requester builds every service rework; the assigner is the only other way root reworks |
| A rework delegation carries its sender's tier | `dispatch.provenance_source` (stamp), with the facts from `services.ServiceReworkContext` | provenance is dispatch's rule; the tier is service-case knowledge |
| `progress` withholds the path while questions are open | `progress.CaseTaskLines` (the line) over `reflection.questions_open` (the rule) | the line is built in one place; the rule is shared with the deliverable note, which withholds the same path |
| A deliverable finding ends only with the user's own verdict after the change | `reflection.FolderDeliverableChecks` | the one deriver of findings; nothing is stored, so the rule is re-applied on every read |
| Deliverable-folder reads stay inside the folder | `reflection.FsDeliverableFolder` | one reader; the containment is tested there |
| A throttled run with no tool effect is not charged | `kiro`'s launcher (the verdict: `THROTTLE_EXIT` and the mark), `scheduler.CreditingThrottles` (the decision, only on that exit code) and `budget.run_credit` (the note); `observability` counts credits in the conservation check | the launcher alone sees the events and writes the exit code (the agent cannot); the scheduler settles runs; budget stays derived |
| User-visible case and task run counts equal the runs charged | `reflection.LogRunCounter` and `progress.LogRunCounts`, both over `kernel.credited_stems` | the two counters every case total, overspend warning and `runs n of m` come from; one recognizer of a credit |

## 15. Zero denominators and empty cases

0a.2 adds no division and no ratio; every new number is a count. Every new count text is guarded: the P1 refusal lists n >= 1 lines,
`- and {k} more` only when k >= 1, `{k} line(s) removed` only when k >= 1, P2-UNRATED and P2-RETIRE-UNRATED have n >= 1, "none yet" covers no
rejections, the deliverable note is `""` with no findings, ` + {c} credited` only when c > 0. The empty cases:
- **No playbook yet**: the first version is exempt (no line stage). **No changed line** (removal or reorder only): today's admission.
- **No confirmed criteria**: `added` is empty; rule (c) gives no `c_part`; G1/G2 as today. **No rejections**: `AmendmentBasis.rejections == ()`;
  the answer path is P2-NOT-A-REJECTION ("none yet"); the user path is open (when every delivery is rated); retirement is open. **No cases**:
  `unrated == ()`.
- **No stored version in force when a rejection was recorded** (a legacy file without `defined`, a missing history file): P2-ABOUT uses the
  oldest stored version (5.2); the current version is always stored, so the set is never empty.
- **`words` of fewer than 4 words** (`"Yes, add it."`): only equality with the rejection's note refuses (section 3). **An empty note** cannot
  occur (a rejection needs a note today).
- **No artifact yet** (no done result): P3 compares nothing; files of the folder newer than the group's earliest `created` and unsettled are
  `unknown`; P4 has no judged delivery (`None`, no base needed). **Empty folder, missing folder, no `path`, a missing file of a file
  contract**: no findings. **A path that names a file**: the single-file check (6.3). **No `Contract.created`** on any service of a group:
  no mtime floor. **No git history**: P3 compares with the current org file; P4 uses the result-listing fallback and includes no text. **No
  one-off results**: the union basis is the services' results only. **A basename pair unknown on both sides** (`at_result` and `current`
  both `None`: the team's file moved or was deleted): the pair is dropped; with no pair left, the file is compared as in step 2. **A
  single-file group with no candidate result**: `unknown`.
- **A criterion whose text has no letter or digit** (`line_key(c.text) == ""`): it admits no (c) line, and `quoting_lines` matches it by its
  id only (4.1, 4.5), so a bare `C9` is neither its "words" nor a quote of it.
- **No reading on a rejection**: the reply's third form (5.6), which names no id and lists the candidates; **no current criterion** (`{C ids}`
  empty, a contract with no criteria cannot exist: `criteria_lines(..., required=True)`) and **no earlier rejection** (`{R ids}` = `none`:
  the repeat sentence is left out).
- **No retired copy** (continuation): a first definition, as today. **A copy with no recorded request** (no request of it has a result): a first definition. **A copy
  without `created`**: every request of the owner and name counts (no floor). **A copy without a playbook**: the continued service has none
  (`no playbook yet`), and the owner's first revision is exempt as it would have been.
- **No previous run** (first run of an agent), or a run log that `logs.files(addr)` does not list: the throttle credit is `"free"`.
  **`max_failures`** is 3 by default and not validated; any value bounds a throttle storm at `max_failures + 1` runs (9.2). **No credit
  note**: `credited_stems` is empty and every count is today's.
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
| B4 | `TESTS/golden/expected/mcp/surface_root.txt`, `surface_root_unbound.txt`, `surface_root_setup_mode.txt` | G | root `define_service` (arguments, docstring), root `feedback` docstring (5.7, including "after it, that rejection takes no confirms" and the sentence on root's reading) |
| B4 | `TESTS/golden/expected/cli/help_define-service.txt`, `SRC/cli/tests/expected/help_define-service.txt` | G, H | `--answers`, `--about`, `--words` |
| B4 | `TESTS/golden/expected/cli/help_feedback.txt`, `SRC/cli/tests/expected/help_feedback.txt` | G, H | the `--criterion` help gains `(an answer that changes no criterion)` (D16) |
| B6 | `SRC/cli/tests/expected/define_service_amend_acceptance.txt` | H | the scenario (`SRC/cli/tests/_scenario.py`) adds `--words Add-a-summary.`; the output gains the "Recorded as a change the user asked for on their own" line (scenario deliveries, if any, get their verdict first) |
| D3 | the three `surface_root*.txt` | G | root `request` gains `base` and its docstring sentence |
| D3 | `TESTS/golden/expected/cli/help_request.txt`, `SRC/cli/tests/expected/help_request.txt` | G, H | `--base` |
| D4 | the three `surface_root*.txt` | G | root `delegate` docstring: `A service request is sent back with request(..., revises=...).` (8.1) |
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
credit; checked: `BRIEF` in `TESTS/golden/scenarios.py`, `testkit/services_world.py`, `testkit/dash_fixtures.py` has no `path`), and
`cli/help_retire-service.txt` and the `retire_service` CLI outputs (the retirement gate adds no argument, and the scenarios that retire have no
delivered request: `SRC/cli/tests/_scenario.py`'s `retire_service` runs on `_team`, `test_golden_events.py:87` retires a service with no
request). The three `surface_root*.txt` are regenerated four times (B4, D3, D4, E1); each commit lists only its own diff. The merge with the
floor batch regenerates them once more (8.3). B8a (the continuation) and B8b (root's `retire` note) change no golden: no golden scenario
defines a service again after a retirement (`test_golden_events.py:85-87` retires an agent without services and a service without a
request; the CLI scenario's `retire_service` is not followed by a definition; `progress/tests/_scenario.py:159` retires an agent through
`Org.retire`, not MCP), and the `retire` docstring is unchanged. E2 changes no `kiro/*` golden: the recorded streams have no THROTTLING
`runError`, so no mark is rendered and no exit code changes.

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
- **Rule R** (P2-RETIRE-*): a test that retires a service as root after a delivered request records a verdict on it first (a relayed
  `accept` unless the test is about verdicts). Known site: `SRC/reflection/tests/test_cases.py:test_requests_from_before_a_service_was_retired_are_not_cases_of_the_new_one`
  (it delivers, then retires). The other retiring tests retire with open requests only (no `done` result), which the gate does not count:
  `test_contract_case_history.py` (lines 421, 453), `test_contract_service_reports.py:115`, `services/tests/test_contract_service_hints.py:62`,
  `services/tests/test_events.py:39`, `TESTS/golden/test_golden_events.py:87`, the CLI scenario `retire_service`.
- **Rule C** (continuation, 5.10): a test that retires a root service (or its owner) after a request that has a result and defines it again expects
  the continuation. Known site: `SRC/reflection/tests/test_cases.py:test_requests_from_before_a_service_was_retired_are_not_cases_of_the_new_one`
  becomes `test_a_service_defined_again_after_a_delivery_continues_its_cases` (deliver, rate (Rule R), retire, define again: the old case is
  a case of the defined service, and its contract is v2 with the old `created`). The 0a.1 meaning stays pinned where it still holds:
  `test_contract_case_history.py:test_requests_from_before_the_service_was_created_again_are_not_part_of_it` (line 418) asks without a
  delivery, so its re-definition is a first definition and the test is unchanged. `services/tests/test_define.py:163`
  (`retire_team` moves the service with its owner) is unchanged and gains a sibling: hire again, define, the service continues.
- **Rule K** (skill needles): `test_skill_org_growth.py:test_always_is_not_the_users_yes` replaces its needle ``never pass `criterion` on
  the rejection itself`` with ``with `criterion` on the rejection itself (your reading, not their yes)`` in B9, and its docstring says why
  (8.2). No other test pins the old needle (searched `never pass`).
- **Rule S** (facade guard): a test that sends a root task with `service`/`revises`, or a root note with `feedback`/`criterion`, through
  `Org.send` uses `request`, `delegate` or `feedback` instead. Searched: `grep -rnE '\.send\((ROOT|"root")' src tests` filtered for
  `service=|revises=|feedback=|criterion=` finds only `dispatch/tests` (they call `RuleMessageSender` directly) and the observability
  fixtures' `w.send(...)` (a file writer of the test world, not the facade): no facade call is affected. `TESTS/architecture/facade_cases.py`'s
  `send` forwarding case sends from `ceo`, so it is unaffected; the facade does not expose `inherited` (7.6), so its forwarded call is
  unchanged.

Known sites (found by `grep -rn "add_acceptance\|remove_acceptance\|add-acceptance\|remove-acceptance"` and `revise_playbook(` with non-empty
evidence; the coder applies the same rules to anything else the full suite shows, naming each site in its commit message):
`SRC/app/tests/test_services_facade.py`; `SRC/cli/tests/_scenario.py`, `test_service_commands.py` (`test_commands_services.py` uses fakes: only
the argument plumbing); `SRC/mcp_server/tests/test_service_amend_tool.py`, `test_service_tools.py`, `test_tools_services.py` (also
`test_root_define_service_reply_carries_the_amendment_step`, removed with 5.6); `SRC/reflection/tests/test_case_service_evidence.py`,
`test_prompt_sections.py`, `test_reports.py`, `test_steps.py`, `test_digest.py`, `test_contract_service_steps.py`;
`SRC/services/tests/test_amend.py`, `test_amender.py` (it pins the rule (c) note line `Rule (c): a playbook revision that cites ... is admitted; confirmed now: {ids}.` that 4.6 rewords), `test_contract_service_catalog.py`, `test_contract_service_commands.py`, `test_events.py`, `test_playbook.py`;
`SRC/skill/tests/test_skill_services.py` (needle unchanged, 8.2); `TESTS/architecture/facade_cases.py`; `TESTS/golden/test_golden_events.py`,
`test_golden_files.py`; `TESTS/testkit/services_world.py`; `TESTS/e2e/test_org_growth_0a.py`: `chain()` (block 6: `... state it [C6].`),
`test_6`, `test_7` (rewritten to Rule A: `define_service(add_acceptance=[added], answers=n2, about="C6", words="Yes, add it.")`; the
refusal-before-confirmation assertion becomes "a revision citing C7 with any other line is refused"; the admitted revision is
`PLAYBOOK_V1 + "- C7: " + added`), `test_11` (replaced by the E3 replay, section 10).

## 18. Commit plan (each green; `count.txt` raised where tests are added; conventional commits)

The labels (A1 ... E6) are the ones the golden table (section 16), the test-site rules and the replay placement (section 10) use. Each
commit is RED (its tests first, failing for the stated reason) -> GREEN -> REFACTOR, and names the existing tests it changes by rule
(section 17).

1. `docs(design): add org-growth phase 0a.2 design` (revision 1) and `docs(design): revise phase 0a.2 design per review` (this revision).
2. (A1) `feat(kernel,services): strip_markers, line_key and changed_lines compare playbook lines on their words` (pure; unit tests:
   renumbered steps are no change; `- [ ] x` equals `- [x] x`; a changed word or number is a change; `word_count` unchanged).
3. (A2) `feat(reflection): a confirms link-note id is evidence for its criterion` (`Verdict.link_notes`; F-E4-7).
4. (A3) `feat(reflection): rule (c) admits only the cited criterion's words and rule (b) only tagged lines` (`admit(lines=)`, `Admission.lines`,
   P1-REFUSED with the 600-character listing, root's note; `2. C9: <text>` is a (c) line; Rule T sites; golden `service_and_playbook_files.md`).
5. (A4) `feat(reflection): step 3, the amendment note and the revise_playbook docstring say how lines are admitted` (6 goldens).
6. (A5) `feat(reflection): the digest marks lessons from relayed reworks` (`Case.lesson_sources`).
7. (A6) `feat(services): an amendment that removes a criterion names the playbook lines that quote it` (`quoting_lines`, `diff(quoting=)`).
8. (B1) `feat(services): a contract version records its basis` (`Contract`/`Criterion` fields, `number_criteria(basis=)`, `stored_basis`;
   parse only, behaviour unchanged).
9. (B2) `feat(reflection): only the product's link confirms an answered amendment; a user-initiated one never counts`
   (`confirmed_criteria(cases, criteria)` with `criteria` required, marks).
10. (B3) `feat(reflection): amendment_basis lists the rejections and the deliveries without a verdict` (`rated` and `delivered_unrated` move
    to `reflection.api`; `ServiceEvidence.amendment_basis`; `Rejection` without `question` yet; fakes).
11. (B4) `feat(services): define_service records the user's answer and writes its link; one rejection gets one answer` (`answers/about/words`
    through services, `Org`, MCP root (split registration) and CLI; `LinkNotes` shared with `feedback`; `repeats_rejection` with the four
    evidence cases of section 3 as unit tests; `answering_version` and `answer_ids`; the refusals of the given values: P2-ROOT-ONLY,
    P2-NOT-AN-AMENDMENT, P2-PAIR, P2-WORDS-LONG, P2-UNREADABLE, P2-NOT-A-REJECTION, P2-ANSWERED, P2-ABOUT, P2-WORDS-ARE-THE-REJECTION; and
    the same invariant from the other side, P2-CONFIRMS-ANSWERED and P2-CONFIRMS-RECOVERY in `feedback` (one invariant, both writers of an
    answer, one commit); the write order of 5.2 step 4; **the link-failure recovery test**: a `LinkNotes` fake that raises once, so
    `define_service(answers=X)` raises the section 12 error, `SERVICE.md` is the new version and the owner's note was delivered with the ids
    `(not confirmed)`; then `feedback(confirms=X, criterion=<answer_ids>, source="human")` is admitted and the criteria are confirmed; a
    second `confirms=X` is P2-CONFIRMS-ANSWERED; before the recovery, `confirms=X` with other ids, or with `source="relayed"`, is
    P2-CONFIRMS-RECOVERY; the replies and docstrings of 5.7, the reading sentence of the root `feedback` docstring included; no refusal yet
    of a call without the new arguments; goldens: 3 `surface_root*`, 2 `help_define-service`, 2 `help_feedback`).
12. (B5) `feat(reflection): the rejection reply gives the exact question` (`QUESTION`'s three forms chosen by root's reading, `question_for`,
    `Rejection.question`; F-E4-6; tests: a reading `C<k>` gives `About C<k>: add` and `about="C<k>"`; a reading `R<j>` gives
    `Same as R<j>: a one-off?`; `none` or no `criterion` gives the third form, which lists the ids and contains no `C<k> is one of`). The
    reply now names `define_service(answers=...)`, which exists since B4.
13. (B6) `feat(services): root changes the acceptance criteria only as an answer or a user-initiated request` (P2-UNRATED, P2-NEEDS-WORDS,
    P2-OPEN-REJECTION; Rules W/A/V; `services_world.confirmed_amendment`; `test_7`; golden `define_service_amend_acceptance.txt`; scenario
    `test_golden_events.py`; the replay kit `TESTS/testkit/e4_replay.py` and the replays `test_s1r_t5_...`, `test_s1r_v3_and_v4_...`,
    `test_s1r_playbook_v2_of_e4_...`, `test_e3_turn_5_...`, which assert B5's question; `test_11` removed).
14. (B7) `feat(reflection,mcp_server): the amendment reply drops amendment_step and NO_YES_YET` (`ServiceSteps` 3 -> 2; root
    `define_service` appends no step; `ScriptedSteps`, `test_contract_service_steps.py`, `test_steps.py`,
    `test_root_define_service_reply_carries_the_amendment_step` removed). After B6 no root amendment can precede its answer, so the step can
    only be dead text; removing it is its own change.
15. (B8) `feat(services): root retires a service only after its verdicts and answers` (5.2a; P2-RETIRE-UNRATED, P2-RETIRE-OPEN,
    P2-RETIRE-UNREADABLE; `RuleServiceRetirement` gets `ServiceEvidence`; Rule R; tests: each refusal through MCP, the CLI `retire-service`
    and `Org.retire_service`; after a verdict and an answer the retirement is admitted).
16. (B8a) `feat(services,agents): defining a retired service again continues its record` (5.10: `RetiredTree.addr`, `RetiredService`,
    `ContinuedServices` and `RecordedContinuations`, `ServiceRestorer` on `FsServiceStore`, step 0 of 5.2, P2-CONTINUES, the reply and the
    owner's note; contract suite `test_contract_continued_services.py`; Rule C; tests on MCP, CLI and `Org`: (a) deliver, reject, retire the
    owner with `retire_team`, hire it again, define the service with other criteria: P2-CONTINUES, nothing written; (b) define it with its
    criteria: v<n+1> with the old `created`, the old case is a case again, the reply names the open rejection; (c) then
    `define_service(..., add_acceptance=..., words=...)`: P2-OPEN-REJECTION, and with the answer: admitted with the whole record; (d) the
    same after `retire_service` (with its verdicts); (e) a retired copy with no recorded request (a rolled-back blueprint): a first
    definition, as today; (f) `weekly` is not continued from `weekly-memo-<stamp>`; (g) the same name for another top-level agent: a new
    service; (h) an unreadable copy: P2-UNREADABLE; (i) a continuation retired and continued again keeps the whole lineage; (j) `apply_org`
    of a blueprint that defines a continued name: P2-CONTINUES (the playbook); (k) DR-41: a **blocked** result rejected by the human, then
    `retire_team`, `hire` and `define_service` with new criteria: the service continues (the open rejection keeps its record) and the
    amendment is refused P2-OPEN-REJECTION as for a done result; with the open request closed by `retire_team` as `failed`, the same;
    a request without a result at `retire_service` is not recorded (the declared late-result facet)).
17. (B8b) `feat(mcp_server): root's retire reply names the records its services keep` (5.10 texts; `HiringTools` gets the catalog and the
    evidence; tests: a top-level agent with an open rejection and an unrated delivery; one without services (no note); a read error (no
    note); an agent's `retire` (today's text)).
18. (B9) `docs(skill): the answer is recorded with define_service` (K4; Rule K; the new needle test with K4's needles).
19. (C1) `feat(kernel): artifact_paths reads a result's artifacts` (`progress.artifacts_of` delegates).
20. (C2) `feat(progress): blocked results with client questions are flagged and the artifact path is withheld while they are open`
    (`questions_open` moves to `reflection.api`; Rule F; K2 and its needle `withholds the path`).
21. (C3) `feat(snapshots): OrgHistory reads the organization's git history` (`GitClient` read methods under `--literal-pathspecs` with a 2 s
    timeout, `head()`, the size check before `cat-file blob`, `blob_id` for sha1 and sha256, contract suite with real git and the memory fake;
    a path with `*` and `:(` is read literally; a path with `:`, `^`, `~`, `@{` or `\` runs no git).
22. (C4) `feat(reflection): deliverable checks name the files the team did not deliver as checked` (`DeliverableChecks`, `FsDeliverableFolder`,
    `CheckedVersions` and its `app` adapter, runtime fields; folder groups and the union basis (two services and a one-off result in one
    folder give no false `unknown`); the git bounds (a fake history that counts calls: at most 40 pairs; a fake clock past 5 s stops the
    lookups; `None` answers asked again only after `head()` changes); a basename pair unknown on both sides is dropped; human-tier settling (a
    relayed accept after an edit leaves the finding); `shown_name` (a name with a newline and one with U+2028 are rendered escaped on one
    line); single-file contracts (a contract path that names a file: an edited copy gives `differs`, an equal one none, a missing one none;
    a file contract inside a folder group is checked once); containment tests: a symlink entry, a `..` in the contract path, the folder
    itself a symlink (`deliverables -> <another folder>`: the folder-level `link` line and none of that folder's names), a parent component
    swapped for a symlink **between** `resolve` and the walk (the walk called with a stale target through the `locate`/`walk` seam of A.4 P4 (no `Path.resolve` patch): the `link` line,
    nothing of the other folder read; DR-43: `ENOTDIR`/`ELOOP` classified by `os.stat(..., follow_symlinks=False)`, a last component swapped for a link,
    a traverse-only parent gives no `unreadable` and one swapped for a link gives `link`, a folder that cannot be listed is `unreadable`; DR-45: the kind is decided before
    grouping, a file contract inside a folder group uses the file rule and joins the basis, a single-file group outside any folder group), a FIFO (skipped, and a FIFO swapped in for a regular entry does not block: `O_NONBLOCK`), a 4 MiB + 1
    byte file (`large`), nine 4 MiB files (eight read, the ninth `limit`), a hard link (read), a subfolder (skipped), 201 entries (200 read)).
23. (C5) `feat(progress,mcp_server): progress, status and whoami show the deliverable note` (K3 and its needle `did not deliver as checked`;
    the withheld-path line; replay `test_s1r_t8_...`).
24. (D1) `feat(dispatch,services): rework delegations inherit the tier of their sender's work` (`fields_for` restructured as in 7.6,
    `provenance_source(inherited=)`, the `ReworkContext` docstring and contract test).
25. (D2) `feat(reflection): JudgedVersions names the judged delivery and what relayed reworks changed after it` (the port in `services.api`,
    `CaseJudgedVersions`, its contract suite over the fs world and the memory fake, the runtime field `judged_versions`; no caller yet).
26. (D3) `feat(services): a human rework after relayed changes names its base` (`base` through services, `Org`, MCP root and CLI; the base
    section last, with the Goal sentence and the 6000-byte limit, and the long-criteria test of 7.3; P4-NEEDS-BASE, P4-BASE-VALUE,
    P4-BASE-WHERE; Rule B; goldens: 3 `surface_root*`, 2 `help_request`; K1 and its needle `base="delivered"`).
27. (D4) `feat(dispatch,app): root reworks a service request only with request` (P4-USE-REQUEST in `RuleTaskAssigner`; `check_root_send`
    with FACADE-ROOT-TASK in `Org.send`; root's `delegate` docstring sentence; Rule S; golden: 3 `surface_root*`; replays `test_s2r_...`
    and `test_s3_...`, which assert P1, P2 and P4 together and so land when the last of them exists).
28. (D5) `feat(app): the Org facade sends no root verdict or link outside feedback` (FACADE-ROOT-VERDICT in `check_root_send`;
    `TESTS/architecture/test_policy_free_primitives.py`).
29. (E1) `docs(instructions): activate the skill before building or rating; the reject order in one line` (8.1; 3 goldens; needle test).
30. (E2) `feat(kiro): the launcher marks a throttled run, counts its tool effects and says so in its exit code` (the update-first facts of
    9.1; `THROTTLE_EXIT` and kiro's own 75 returned as 1 on every return path (DR-44); the new fixture stream; `throttled_without_effect` with the last-`# kiro:`-line rule and the
    forged-pair test; `READ_ONLY_TOOL_IDS` and `TESTS/architecture/test_read_only_tool_ids.py`).
31. (E3) `feat(kernel,budget): run credit vocabulary` (`RUN_CREDIT_TITLE`, `run_credit_title`, `is_run_credit`, `credited_stems`,
    `run_credit`).
32. (E4) `feat(scheduler): a throttled run with no tool effect is credited and retried once` (`ThrottleCredits` with the delivery last, asked
    only for `THROTTLE_EXIT` and a run that was not killed; unit, reaper (the forged mark) and loop tests; `FAKE_THROTTLE_RUNS`).
33. (E5) `feat(reflection,progress): case and task run counts leave credited runs out` (`LogRunCounter(logs, mail)`, `LogRunCounts`).
34. (E6) `feat(observability,agents): budget conservation counts run credits` (`RetiredArchive.credited`).
35. `docs: README and ARCHITECTURE for phase 0a.2` (README "Services and reflection" and "Kiro integration" paragraphs updated in place;
    ARCHITECTURE 2.2's `reflection` row, "Reads, does not own": the contracts' deliverable folders (direct files, read-only) and the
    organization's git history (through a port implemented in `app`), and the `services` row: the retired copies of its services; section 3
    interface blocks of `kernel`, `snapshots`, `agents`, `dispatch`, `services`, `reflection`, `kiro`, `budget`, and 3.37).

Numbering (A.4 P6): the plan numbers these items in 36 commits: 1 Z0 (this amendment of the design), 2-7 A1-A6, 8-12 B1-B5, 13 B6k (the replay kit, split out of B6), 14 B6, 15 B7, 16 B9 (before B8), 17 B8, 18 B8a, 19 B8b, 20-24 C1-C5, 25-29 D1-D5, 30-35 E1-E6, 36 docs. The paragraph below uses revision 3's numbers; read A, B, C, D, E labels.

Order: A (2-7) and C (19-23) are independent of each other; B (8-18) needs A; D (24-28) needs A and B; E (29-34) is independent, except that
29 comes after 11, 26 and 27 (the same three goldens are regenerated in each, and each commit lists its own diff) and its step 5 names the
`request` rework that 27 enforces. The full pytest runs before the plan's commits 4, 9, 14, 17, 18, 21, 27, 28, 31 and 33 (design A3, B2, B6, B8, B8a, C2, D3, D4, E2, E4); every
other commit its targeted set plus a search of `src/` and `tests/` for each text it changes; each package ends with the full
`scripts/check.sh`.

D2 and D3 were one commit in revision 1; they are split because the port and its contract suite (a new derived view, with no behaviour
visible to any caller) and the refusal that uses it are two changes. D4 and D5 are split for the same reason: D4 closes root's ways to rework
a service request (the P4 invariant), D5 closes the facade's way to write a verdict or link (the P2 and `feedback` invariants).

### 18.1 Test plan per scope item (unit = pure functions and fakes; integration = the fs world / in-process MCP; e2e = section 10)

| Item | Unit (RED first) | Integration | e2e replay |
|---|---|---|---|
| P1 lines (A1, A3) | `line_key`/`changed_lines`/`strip_markers` cases; (c) line forms (`- C9:`, `2. C9:`, `<text> (C9)`); (b) tag regex (`[C6]`, not `C60`); refusal text with 0, 1, 10, 11 offending lines | `RulePlaybookReviser` through the lead's MCP `revise_playbook`: refused writes nothing; admitted writes `Admission.lines` into root's note | s2r (6), (7); s3 attempt 1 and its compliant form |
| P1 companions (A2, A5, A6) | link-note id resolution (human, relayed); `case_line` marks; `quoting_lines` | the amendment note names the quoting lines; the digest in the owner's prompt sections | s2r (2); s3 (link id as evidence) |
| P2 answer path (B1-B5) | `repeats_rejection` (the four evidence cases); `answering_version`; `answer_ids`; `confirmed_criteria` basis join; `question_for` (the three forms: reading `C<k>`, reading `R<j>`, no reading) | every refusal of 5.3 through MCP root, CLI `define-service` and `Org.define_service` (one parametrized test per refusal and surface: no bypass); the product's link shape equals `feedback(confirms=)`'s; P2-CONFIRMS-ANSWERED and P2-CONFIRMS-RECOVERY through MCP, CLI `feedback` and `Org.feedback`; the link-failure recovery (B4) | s1r T5 (compliant path), s2r (2a), (5), s3 #30, #37 |
| P2 gate (B6, B8) | `delivered_unrated` (done, rated by any tier, a later rework; a blocked case is not unrated) | P2-UNRATED, P2-NEEDS-WORDS, P2-OPEN-REJECTION and P2-RETIRE-* on the three surfaces | s1r T5, s1r v3/v4, s1r playbook v2, E3 T5 |
| P2 continuation (B8a, B8b) | the copy selection (newest by `defined`, `fullmatch` of the name, `RetiredTree.addr`, a request with a result of any status since `created`) over a memory fake; `restore` byte for byte, `SERVICE.md` last | the eleven cases (a)-(k) of B8a through MCP, CLI and `Org` (`retire_team` + `hire` + `define_service`, and `retire_service` + `define_service`); root's `retire` note (B8b) | - (E4 has no retirement; E5 counts them, section 21) |
| P3 flag and path (C2) | `questions_open` (done, blocked, settled by a verdict or a human rework, not by a relayed one) | `progress` lines | s1r T8 (first half); s3 `...-lead-96e9` |
| P3 folder check (C3-C5) | `blob_id` against `git hash-object` (sha1; sha256 in a `--object-format=sha256` repository); `shown_name`; grouping (file contracts included); settling; the git bounds (40 pairs, 5 s by a fake clock, the `None` memo under `HEAD`); the 32 MiB total | `FsDeliverableFolder` containment cases (C4: the component walk, a final link, a swap between resolve and walk, single-file contracts); `GitOrgHistory` over real git; note in `progress`, `status`, `whoami` (root only; agents never) | s1r T8 (second half) |
| P4 tier (D1) | `provenance_source(inherited=)` | `fields_for` contract cases; a lead's writer delegation during a relayed and a human rework | s2r (1), (4) |
| P4 base and closure (D2-D5) | `JudgedBase` steps 1-5; base section texts and fence; byte limit; the placement (last, with the Goal sentence) | P4-NEEDS-BASE/VALUE/WHERE through MCP, CLI `request --base` and `Org.request`; long criteria stay inside the rendered prompt; P4-USE-REQUEST through MCP `delegate`, CLI `task --revises`, `Org.delegate`; FACADE-ROOT-TASK/VERDICT through `Org.send`; `test_policy_free_primitives.py` | s2r (3), (4); s3 #31 |
| Root instructions (E1) | the budget tests (`< 2700` at the reference path, `< 2900` with 200 characters, `< 2800` raw); needle tests, including `test_binding.py:98` and `test_goal_tools.py:63` (`instead of substituting`) unchanged | `build_server(org, ROOT).instructions` | - |
| Throttle (E2-E6) | launcher fixture and variants (9.3), the exit code (75 only from the launcher's verdict); `throttled_without_effect` (the position rule, the forged pair); `credited_stems`; `CreditingThrottles` with fakes (order: delivery last; a log missing from the listing) | the reaper asks only on `THROTTLE_EXIT` (a forged mark with exit 1 or a kill: charged); scheduler loop with `FAKE_THROTTLE_RUNS`; run counters; conservation check | - (the fixture is built from E4's s2 transcript) |

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
| 0a.1 18, "`define_service`, `request`, `feedback` and delivery refuse nothing new" | no new refusal | the refusals of 4.2, 5.3, 7.4 (D-E4-1, -2, -4); `feedback` refuses one new case, `confirms` on a rejection a contract version answered (P2-CONFIRMS-ANSWERED, D18); delivery still refuses nothing new |
| 0a 4.1 / services `retire_service` ("same authority as a definition") | root may retire any top-level service at any time | root's retirement needs the service's record complete: every delivery rated, every human rejection answered (5.2a); defining it again afterwards continues it when it had a recorded request (5.10) |
| `app/_facade_dispatch.py:DispatchMixin.send` | forwards every field to the message sender | refuses root's service tasks, reworks, verdicts and links (7.5, D19); `Org.deliver` stays the declared policy-free primitive |
| `services/_rework.py:ServiceReworkContext.fields_for` ("Empty for an ordinary task") | service fields only, `{}` for a non-service task | the restructured method of 7.6: service fields when the revised task is a service request, `source` for an agent in a traced case |
| 0a.1 21.11 (DR-27), what `confirms` may name | unchanged | unchanged |
| V3 design 5.1/5.2 | the launcher's lines; 5.1 step 4 "Return kiro's exit code" | one more `# kiro:` line (9.1); the rendered lines are unchanged; the launcher returns `THROTTLE_EXIT` (75) for a throttled run without a tool effect, and kiro's own 75 as 1 (9.1) |
| 0a.1 (and 0a) "a service defined again after its retirement is a new service" (`reflection/tests/test_cases.py:143`; the `created` filter of `DerivedCaseHistory.cases`) | requests from before a retirement are never cases of the new definition | still true for agent clients and for a retired copy none of whose requests got a result; a root definition of the same owner and name whose retired copy has a recorded request (a result of any status) continues it (5.10): same `created`, the old cases are its cases |
| `hierarchy` team retirement (`RuleRetirement.retire_team`) | retires the team; its services leave with it | unchanged and never refused; MCP root's `retire` reply names the records the services keep (5.10) |
| SKILL.md step 5 item 6 (0a.1 8.1, S-lines) | "never pass `criterion` on the rejection itself" | "Name the id you read the reject as, with `criterion` on the rejection itself (your reading, not their yes)" (8.2 K4, D23) |
| 0a.1 3.4 `QUESTION` `{own}` and the reading | the rejection's own `criterion` is shown as not confirmed | unchanged, and it is now also root's reading, which fills the question's id (5.6) |
| `runs/api.py`, "the existence of the file is what consumes one run of budget" | true | still true; a credit note returns a throttled run (9.2) |
| `reflection/_runs.py:LogRunCounter`, `progress/_counts.py:LogRunCounts` ("a run is a log file") | every log in the window counts | a log whose run has a credit note is not counted (9.2): the case and task counts are the runs charged |

## 20. Deviations from e4-gate.md and e4-decision.md, with reasons

- **D1 (P4, mechanism of "the tier travels").** The gate says `fields_for` "adds `source`". Copied from the revised task it would never fire:
  a lead's writer task revises the writer's earlier task, which carries no service and no tier (s2r `...-lead-608b` revises `...-lead-7124`,
  both without `source`). The tier is taken from the work the delegating agent is doing in that case (its latest open received task with the
  same trace, 7.6); `fields_for` is restructured so that a revised task without a service still yields `source` (it returned `{}` for one
  before), and a revised task without a trace yields none. The behaviour the decision asks for (the lead's and the writer's tasks show
  "relayed") holds; only rework delegations carry it, as decided.
- **D2 (P4, closure, a refusal the decision does not name).** Root's `delegate(revises=<a service request>)` is refused with P4-USE-REQUEST.
  Without it a human rework could bypass the base refusal through `delegate` (MCP, CLI `task`, `Org.delegate`), against the brief's "no refusal
  can be bypassed". `request(revises=...)` is the documented service rework and what every E4 assistant used.
- **D3 (P2, addition).** P2-WORDS-ARE-THE-REJECTION refuses `words` that repeat the rejection's own note: equal words, or the shorter of the
  two (at least 4 words) occurring as a contiguous run in the longer (`repeats_rejection`, section 3; symmetric, so s1r T5, which is the #22
  note with "No, not right yet." before it, is caught as well as E3 T5, which equals its note). The gate's conditions would admit both if the
  assistant pasted the reject as the answer; the check is deterministic and cheap, and it does not claim to prove the words are the user's
  (5.9).
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
- **D10 (P3, settling and scope of the folder check).** The decision gives no end to the note. It ends when the case gets a **human-tier**
  verdict after the file changed (the user judged the file as it is; the assistant's own relayed verdict does not end it); files older than
  the folder's services are ignored; the folder is read flat (no subfolders); services that share a folder are checked together against the
  union of their and root's one-off checked artifacts (a shared `deliverables/` is the default); workspace (absolute) artifacts are not
  compared; a renamed copy equal to a checked or current artifact is not reported; at most 40 history lookups per check (older history is
  compared with the current org file). The note names the "team's last checked artifact" of the decision as the newest done result that lists
  a file of that name.
- **D11 (P4, when the base is needed).** "Changed after the judged delivery" is decided by content (the judged blob against the current file),
  so a relayed rework that did not touch the file needs no base; without git history, by whether a relayed result lists the artifact. With no
  human-tier verdict the judged delivery is the latest done result of a non-relayed task.
- **D12 (D-E4-6 root instructions, condensation).** Five parentheticals or clauses were cut, and "organization" became "org" in one line, to
  fit the budget (8.1); their content is in SKILL.md. Two safety phrases are kept: the confinement line "(no other paths or ORG_ROOT)" and
  "tell the user instead of substituting" (pinned by `test_binding.py:98` and `test_goal_tools.py:63`; only "another mechanism" is cut), so
  the text has 1 character of headroom at the reference path (2 699 < 2 700), and 58 once the floor batch is merged (8.3). Step 5 names
  `request` beside `delegate`, which the decision does not ask for but P4-USE-REQUEST requires (else the always-sent text would steer root
  into a refusal).
- **D13 (D-E4-6 third bullet, F-E4-9).** The injection script's polling loop is E5's harness, not product code: not in this batch; listed for E5
  (section 21).
- **D14 (P2, removal of `amendment_step`).** The decision says the `feedback(reject)` reply settles F-E4-6; the other text of F-E4-6
  (`NO_YES_YET`) is removed rather than reworded, because no root amendment can precede its answer any more.
- **D15 (P3, surfaces).** The deliverable note is in root's MCP `progress`, `status` and `whoami` and in the CLI's `progress` (one
  `ProgressReporter`); the CLI's `status` does not show it: the terminal is the user's own seat, and "tell the user" is addressed to root.
- **D16 (P2 and 0a.1's CLI composition).** `hirearchy feedback <task> reject --criterion C<k>` (source human) still records the verdict and a
  link in one command (0a.1 3.4). That link is the rejection's answer ("about C<k>"), so a later `define-service --answers <that verdict>` is
  P2-ANSWERED. A terminal user who wants a lasting rule rejects without `--criterion` and then runs `define-service ... --answers <id> --about
  C<k> --words "..."`; the `--criterion` help gains `(an answer that changes no criterion)` (golden `help_feedback.txt`, both copies, B4). DR-46: K4 says so (`at the terminal, `--criterion` on a reject records the answer`), and the tests `test_a_terminal_reject_with_criterion_records_the_answer_so_define_service_answers_is_answered` and `test_a_terminal_reject_without_criterion_then_define_service_answers_records_the_answer` keep both paths consistent.
- **D17 (D-E4-6 throttle, what "not charged" covers).** Not charged = the agent's budget gets the run back (credit note) and the case and task
  run counts (`case_total`, the overspend warning, `progress`'s `runs n of m` and `kept`) leave the run out. The per-agent run counts of the
  dashboard, `Org.runs_used` and `observability` keep it: they report what ran, and the conservation check adds the credits.
- **D18 (P2, a refusal in `feedback`).** The gate keeps `feedback(confirms=...)` "only for no and one-off answers" and says "a second amendment
  on the same rejection is refused"; it does not say what happens to `confirms=X` after `define_service(answers=X)`. 0a.2 refuses it
  (P2-CONFIRMS-ANSWERED), so one rejection has one answer in both directions; this departs from 0a.1 18's "`feedback` refuses nothing new".
  One link is still accepted on such a rejection: the product's own link when its write failed (the same ids, `source="human"`, and no
  human-tier link yet); every other shape is P2-CONFIRMS-RECOVERY (DR-30). A second `confirms` after a first one (no contract change) stays
  accepted, as in 0a.1 (the user may correct an answer; 5.9).
- **D19 (P2 and P4, closure of the facade; refusals the decision does not name).** The `Org` facade's `send` forwards every field, so root
  could write a service rework, a verdict or a link without the rule classes. It now refuses those four shapes (FACADE-ROOT-TASK,
  FACADE-ROOT-VERDICT), against the brief's "no refusal can be bypassed through the Org facade". `Org.deliver` and `Org.runtime` are declared
  out of the guarantee: they are the pipeline primitives every rule is built on, already documented as policy-free, and no MCP or CLI surface
  reaches them (pinned, 5.8).
- **D20 (P2, closure of retire-and-redefine; a refusal the decision does not name).** Root's `retire_service` is refused while a delivery has
  no verdict or a human rejection has no answer (5.2a). Revision 2 justified it as the only thing that kept the record; since revision 3 the
  continuation (5.10, D22) keeps the record across every retirement, so the gate's remaining role is narrower: a service-level retirement has
  no structural cost (the agent and its team stay), and waiting for the verdicts keeps the retired copy complete at the moment it is
  retired. It is kept because it was reviewed and costs little; it is not what the P2 guarantee rests on any more. The alternative of
  revision 2 (a re-definition after a retirement requires `words=` and is user-initiated) stays rejected: it would leave the record erasable.
- **D21 (D-E4-9, not in 0a.2).** The model floor and `--effort` are the separate floor batch; 0a.2 changes no model or effort code. Its only
  effects here are the merge order (8.3) and E5's effort check (section 21).
- **D22 (P2, closure of retire-the-owner-and-redefine, DR-28; behaviour the decision does not name).** Root can retire the owning agent with
  its team, hire the same name again and define the service. 0a.2 does not refuse the retirement (the manager's directive: the user keeps
  authority over the structure); a root definition of the same owner and name then **continues** the retired copy that has a recorded
  request (a result of any status, DR-41; 5.10): the same `created`, the contract's next version, the playbook, every case. The defining call cannot change the criteria
  (P2-CONTINUES), so every change meets the gate with the whole record. This changes 0a.1's "a re-defined service is a new service" for
  root's services with a delivery (section 19). Declared, visible and counted, not refused: the same name defined for another top-level
  agent, or the criteria put under another name (5.8; section 21), because the product cannot tell a new service the user wants from an
  escape, and `services` shows both as new services.
- **D23 (P2, "the exact question to show, with the id", DR-31).** The product cannot know which criterion a rejection is about. The id comes
  from root's reading, the rejection's own `criterion` (5.6): with it the reply gives the exact question with its id, as D-E4-2 asks; without
  it the reply gives the exact wording and the candidate ids, and tells root to pass its reading next time. The reading never confirms
  anything (5.5) and is shown as "not confirmed" (0a.1), so allowing it reverses the skill's 0a.1 line "never pass `criterion` on the
  rejection itself" (8.2 K4, Rule K) without weakening P2: since 0a.2 an amendment in the reject turn is refused. The reading is not
  required (no new refusal in `feedback`); E5 counts the rejections recorded without one and the `about` values that differ from it. DR-46: the reading applies to MCP `feedback`; the CLI's `reject --criterion` records the answer (D16); both paths are tested.
- **D24 (D-E4-6 throttle, the verdict's channel, DR-34).** The gate and the decision describe detection from `retryErrorType: THROTTLING` and
  "no tool effect". 0a.2 carries the launcher's verdict in its exit code (`THROTTLE_EXIT` = 75, `EX_TEMPFAIL`) besides the transcript mark,
  because an agent's text is rendered into the transcript verbatim and could forge the mark and a run-error line; the exit code is the
  launcher's alone. V3 design 5.1 step 4 ("return kiro's exit code") gains this one exception, and kiro's own 75 is returned as 1.
- **D25 (P3, scope of the folder check, DR-32 and DR-33).** "The contract's deliverable folder" is read as the place `deliverable.path` names: a folder, or a single file (the one-off `needs.deliverable` examples of the blueprint name files, `_example_texts.py:34, 81, 179`; the service examples name a folder: DR-45). The check stays inside it: the path's components are walked
  with `O_NOFOLLOW`, a link as the last component is reported and not read, and a call reads at most 32 MiB and spends at most 5 s on git.
  A link in an earlier component that exists before the check runs is followed (the user's layout, such as `/tmp`), and is a declared limit
  (6.6).

## 21. What E5 must check (pre-registration input)

E5 is D-E4-7's study: E4's protocol plus D-E4-5, D-E4-8 and the new tools, at least 3 valid streams, the workspace skill copy, and the
deterministic replays of section 10 (at least s1r T5, s1r T8 and the s2r chain) passing at the E5 commit.

- **Model set and effort (D-E4-8, D-E4-9).** Every live seat runs claude-sonnet-5.5 **at `--effort high`**: the assistant, the lead, the
  reviewer or checker, the writer and every other org agent. The org agents' model floor and effort come from the floor batch (D-E4-9; E5
  starts only after both batches are merged, 8.3); the assistant's `--effort high` is set by the E5 harness. E5 checks `--model` and
  `--effort` in every run log and in the assistant's invocation, and a seat outside the set invalidates the stream. E4's L-MODEL line
  (claude-sonnet-4.6 and claude-haiku-4.5) is dropped; if the assistant proposes another model, Lena's fixed line is "Please use
  claude-sonnet-5.5 for everyone." There is no substitution: if claude-sonnet-5.5 is not listed when a stream starts, the stream does not
  start and the manager is told. **E5 is not model-matched to E4**: it is a gate on its own pre-registered rules, and its report says so;
  E4's lead- and reviewer-side failures may be partly model-caused, its assistant-side ones are not (the assistant was already
  claude-sonnet-5.5). D-E4-8's "the product needs no change" is superseded by D-E4-9: the floor batch drops the cheaper-models option from
  `ROOT_INSTRUCTIONS` and SKILL.md; 0a.2 itself changes no model text, and its step 1 rewrap is reconciled at the merge (8.3).
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
  P2-UNRATED refusals whose unrated delivery was a relayed rework the user never saw (D4's friction). Count also: retire/define pairs of the
  same service name and every P2-RETIRE refusal (D20); rejections with more than one link note, P2-CONFIRMS-ANSWERED and P2-CONFIRMS-RECOVERY
  refusals, and recovery links (D18); `words` that the P2-WORDS-ARE-THE-REJECTION rule admitted but that are not the user's answer turn
  verbatim (read from the turn files).
- **The question's id (D23):** human rejections recorded without root's reading (the reply then showed no id), as `k of n` human rejections;
  among those with a reading, the questions shown to the user that do not name it (read from the turn files), and the `about` values of the
  answering `define_service` that differ from the reading.
- **Retirements and continuations (D22):** every retirement of a top-level agent that offers a service (MCP `retire`, with the services it
  offered and their open items as the reply named them), and every retire/hire/define triple of the same owner and service name; for each,
  whether the definition continued (the reply's `continues the retired one`) and every P2-CONTINUES refusal; the declared ways around: new
  services defined by root, for another owner or under another name, while another service (live or retired) has an unanswered human
  rejection or an unrated delivery; each is reported, not excused.
- **Late results (DR-41):** the results recorded after a fresh re-definition of a retired service whose request was still open when it was
  retired (the declared facet of 5.10): each is reported with its request, the retirement and the re-definition, not excused.
- **No regression and P4:** count human reworks that needed a base, which base was chosen, what the user was told for `latest`, and whether the
  lead's writer restored the judged version (memo versions); s2r's Marta date in particular. Check that every lead writer task made during a
  relayed rework carries `source: relayed`. Count the ways around the base (7.7): reworks sent with `source="relayed"` whose turn shows a user
  rejection of that delivery, fresh `request`s (no `revises`) of an input that already has a delivered case, and root's one-off `delegate`
  tasks (no `revises`, no service) to a service's owner while one of its cases is open or has an unrated delivery; each is reported, not
  excused. Count FACADE refusals (none expected: E5's assistant has no facade).
- **P3 detection:** count deliverable notes shown and whether root told the user in the same turn; count hand edits (D6 writes that differ from
  the team's checked version) and whether a **human-tier** verdict followed them; count notes whose `never written by the team` line names a
  file the deliverables log shows as a copy of a team artifact (false `unknown`, D10), and notes shown with `path withheld: ask first`.
  Count the contracts whose `deliverable.path` names a file and the notes they gave (D25), and every folder-level `link` line and `limit`
  line (expected 0; each is reported).
- **Throttle:** count runs with the throttle mark, the runs that exited `THROTTLE_EXIT` (75), the credits given (`Run not charged:` notes),
  free retries, counted throttles; every credited run exited 75 and was not killed (checked against the run log's closing line); no run
  with a tool effect may be credited (checked against the run's transcript lines, `[tool ok]` of a non-read-only tool); marks that appear
  in a run that did not exit 75 (a forged or partial mark) are counted and must have no credit; the conservation check (`observe check`)
  stays green; every case total and `progress` count equals the run logs minus the credited ones (D17).
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
  - P3 notes repeat in every `progress`, `status` and `whoami` until the user's own (human-tier) verdict follows the change: deliberate, so a
    hand edit stays visible.
  - P2-RETIRE-* make retirement wait for the record: a user who abandons a delivery is asked for a verdict first (a relayed one counts).
  - The continuation (5.10) adds a call when root wants new criteria for a re-defined service (define it again as it was, then amend), and
    an `apply_org` that defines a continued name fails with P2-CONTINUES (it always passes a playbook); the rolled-back build's own retired
    copy never delivered, so re-applying after a failed apply is not affected. The continued service's old cases count 0 runs (their logs
    stay in the retired tree), and their old artifacts are compared with the org history only. The continuation's copies duplicate
    immutable versions (the retired copy stays the archive).
  - The deliverable check follows a link in a parent of the folder that exists before it runs (the user's layout); an agent that can
    replace such a parent can point it at another folder, of which only direct file names and hashes are used, never contents (6.3). A traverse-only
    parent swapped for a link and swapped back between its two `stat`s is not detected (DR-43).
  - A request still open when its service is retired, whose result arrives after a fresh re-definition, falls outside every case of the new
    service (DR-41, 5.10); E5 counts it.
  - The throttle detector depends on kiro's event shapes (`kind` on built-in `tool_call`s, `rawInput.tool_id`/`tool_ids` on calls and
    updates, update-only events, `runError`); a change in them degrades to "charged as today", never to a wrong credit (a completed call with
    unknown facts counts as an effect). The `kind` values of built-ins other than `read`, `search`, `edit` and `delete` (`think`, `fetch`)
    were not seen in a recording; listing them as read-only is an assumption that E5's transcripts check.
  - `GitCheckedVersions` runs git subprocesses on `progress`, `status` and `whoami`: at most 40 pairs and 5 s of git time per call (each
    subprocess at most 2 s), basename matches first, known answers memoized for the runtime's life and `None` answers until `HEAD` moves; the
    CLI (a fresh process) pays the bound each time. Real git timings on a long-lived org were not measured; the bound holds regardless.

## Appendix A. Responses to the design reviews

### A.1 Review pass 1 (revision 1, 27 findings)

Every finding is **addressed**; none is backlogged or declined. Where the review offered a choice, the choice and its reason are given.

| Id | Sev. | Resolution | Where |
|---|---|---|---|
| DR-1 | HIGH | `repeats_rejection` is symmetric: equal words, or the shorter (at least 4 words) as a contiguous run in the longer. Checked on the evidence: s1r T5 vs #22 refused, E3 T5 vs #24 refused, "Yes, add it." and s1r #23 admitted; these four are its unit tests. D3 reworded. | 3, 5.2, 5.3, 10, 18 (B4), 20 D3 |
| DR-2 | HIGH | Option (a): root's `retire_service` runs `amendment_basis` and refuses with P2-RETIRE-UNRATED, P2-RETIRE-OPEN, P2-RETIRE-UNREADABLE (fail closed). 5.8 row "retire, then define again" states what remains; tests on MCP, CLI and `Org`; E5 counts retire/define pairs. The alternative (`words=` on a re-definition) was not taken: it leaves the record erasable (D20). | 5.1, 5.2a, 5.3, 5.8, 12-14, 17 (Rule R), 18 (B8), 20 D20, 21 |
| DR-3 | HIGH | `DispatchMixin.send` calls `dispatch.check_root_send`: FACADE-ROOT-TASK (root task with `service` or `revises`) and FACADE-ROOT-VERDICT (root note with `feedback` or `criterion`). `Org.deliver` and `Org.runtime` are declared out of the guarantee, pinned by `test_policy_free_primitives.py` (no MCP/CLI module calls `.deliver(`; MCP and CLI `send` cannot pass the guarded fields). | 5.8, 7.4, 7.5, 12-14, 17 (Rule S), 18 (D4, D5), 20 D19 |
| DR-4 | HIGH | Facts are read from the update first (kind, `rawInput.tool_id`, `rawInput.tool_ids`), then the recorded call; a completed update with no facts is an effect. The fixture follows the s2 transcript's event order with ws4a's shapes (update-only tool load, MCP `tool_call` without `kind`, `read_file` with `kind: read`, update-only failed write, the line-179 `runError`); the session store is not used. Variants for an update-only load and an MCP call without `kind`. | 9.1, 9.3 |
| DR-5 | MEDIUM | `line_key` strips leading markers with the kernel's marker loop, exported as `kernel.strip_markers` (`word_count` uses it). Tests: renumbering is no change, `2. C9: <text>` is a (c) line, `- [ ] x` equals `- [x] x` (decided: a checkbox toggle is no word change). | 3, 4.1, 4.2, 18 (A1, A3) |
| DR-6 | MEDIUM | Listed lines are clipped at 600 characters (at most 10 lines). Measured: s3's longest changed line has 532 characters, so every rider of the s3 replay is listed. | 4.2, 10 |
| DR-7 | MEDIUM | `fields_for` is specified as code: `{}` only when the revised task is not `actor`'s; service fields when it has a service; `source` for an agent only when the revised task has a non-empty trace, from the newest open received task with that trace. Docstring and contract test updated. | 7.6, 20 D1 |
| DR-8 | MEDIUM | Step 5 says ``send it back with `request`/`delegate(..., revises=...)` ``; root's `delegate` docstring gains "A service request is sent back with request(..., revises=...)."; goldens in D4 and E1. Measured: 2 693 at the reference path with DR-27's restoration (below). | 8.1, 16, 18 (D4, E1) |
| DR-9 | MEDIUM | A finding is settled only by a human-tier verdict at or after the file's mtime, for `differs` and `unknown` alike; a relayed accept after an edit leaves it (test in C4, and the s1r T8 replay). | 6.3, 10, 14, 20 D10 |
| DR-10 | MEDIUM | Services are grouped by resolved folder (one block naming them all); a file is `unknown` only if it matches no candidate of any service of the group nor root's done one-off results; the mtime floor is the group's earliest `created`. Test with two services and a one-off result in one folder. | 6.3, 18 (C4), 20 D10 |
| DR-11 | MEDIUM | Option (a): `reflection.LogRunCounter` (gets `mail`) and `progress.LogRunCounts` skip logs whose run has a credit note (`kernel.credited_stems`, from the title `Run not charged: <addr>@<stem>`); per-agent and observability counts keep every run (D17). Tests in E5. | 3, 9.2, 9.3, 14, 18 (E5), 20 D17 |
| DR-12 | MEDIUM | Reordered: B5 is the new `QUESTION` (after B4's arguments exist), B6 the refusals with the replays that assert it, B7 the removal of `amendment_step`. Section 10 states each replay's commit. | 10, 18 |
| DR-13 | LOW | Section 21: every seat at `--effort high` (org agents from the floor batch, the assistant from the harness), checked in each run log and the assistant invocation; the "no product change" and "model sentence kept" statements are replaced; 8.3 gives the merge order (second merge rebases, re-measures, regenerates the three `surface_root*`). | Header, 8.3, 20 D21, 21 |
| DR-14 | LOW | The folder is opened once and read with `scandir(dfd)` and `open(name, dir_fd=dfd)`; entries open with `O_NOFOLLOW \| O_NONBLOCK \| O_CLOEXEC`; reads are bounded at 4 MiB + 1 bytes; names and the folder are rendered by `shown_name` (JSON-escaped, non-printables escaped, clipped); hard links are read like any file (hash only); git runs with `--literal-pathspecs`, and `cat` checks the size first. | 6.3, 6.4, 13, 18 (C3, C4) |
| DR-15 | LOW | `DeliverableFinding.withheld` (from `questions_open`) renders `differs from the team's checked version (task {task}; path withheld: ask first)`. | 6.3, 10 |
| DR-16 | LOW | Refused: `confirms=X` after a contract version answered `X` (P2-CONFIRMS-ANSWERED, via the shared `answering_version`; `RuleClientFeedback` gets `ServiceStore`). A second `confirms` after a first one stays accepted (0a.1; correction of an answer) and is counted in E5. | 3, 5.3, 5.7, 5.8, 5.9, 19, 20 D18, 21 |
| DR-17 | LOW | `confirmed_criteria(cases, criteria)` with `criteria` required; the callers are listed. | 5.5, 18 (B2) |
| DR-18 | LOW | `tool_call` reads both formats (E4 `call #n` + `ARGS:` line; E3 one-line `CALL #n ... args={...}`); calls are named by number; `lena_line` reads `turn-NN.prompt.txt` or the E3 `LENA` line. | 10 |
| DR-19 | LOW | P2-ABOUT falls back to the oldest stored version; no `created` means no mtime floor; the `max_failures` claim is reworded (default 3, not validated; the bound holds for any value). | 5.2, 6.3, 9.2, 15 |
| DR-20 | LOW | `credit` computes "counted" (step 3) before the delivery (step 4), which is the last fallible action; an error never leaves a credit behind a charged report. Test: a delivery that raises. | 9.2, 9.3, 12 |
| DR-21 | LOW | 7.7 lists both declared-provenance ways around the base (`source="relayed"`, a fresh `request`); E5 counts both. | 7.7, 21 |
| DR-22 | LOW | Judged texts are limited in bytes (6 000 in all, `JUDGED_BYTES`); the base section sits after `## Goal`, so it fits inside `RENDER_BODY_CHARS` and is never cut; the rest of a long body is cut with `cut_body`'s `read(path=...)` pointer, as today. | 7.2, 7.3 |
| DR-23 | LOW | The pin test is `TESTS/architecture/test_read_only_tool_ids.py` (top-level architecture tests already import private modules); no `observability.api` export. | 9.1, 9.3 |
| DR-24 | LOW | At most 40 history pairs (80 git calls) per check, basename matches first, the renamed-copy check lazy and against current files first; memo for the runtime's life; one computation per `progress` call (the wait loop renders on return). The "only basename matches" claim is replaced. | 6.3, 12, 22 |
| DR-25 | LOW | `RootTaskReport`'s 5th collaborator; `services/tests/test_amender.py` added to the known sites; ARCHITECTURE 2.2's `reflection` "Reads, does not own" column in commit 33; `CheckedVersions.current(path, hexlen)` hashes in the format of the checked id it is compared with. | 3, 6.3, 6.5, 11, 17, 18 |
| DR-26 | LOW | Commit 21 is split into D2 (the `JudgedVersions` port, implementation and contract suite) and D3 (`base` and its refusals); the facade closure is also split (D4, D5). | 18 |
| DR-27 | LOW | "(no other paths or ORG_ROOT)" is restored now, without waiting for the floor batch: "organization" became "org" in the claim line and "and check" became ", check" in step 5. Measured: 2 616 raw, 2 693 at the reference path (< 2 700), 2 833 with a 200-character path; needle test added. | 8.1, 20 D12 |

The commit numbers in A.1 are revision 2's; revision 3 inserts B8a and B8b, and the plan numbers section 18's items in 36 commits (Z0 and B6k are new; the docs commit is 36).
DR-22's placement of the base section is superseded by DR-35's, DR-24's git bound by DR-33's, and DR-27's measurement by DR-29's.

### A.2 Review pass 2 (revision 2, 13 findings, DR-28 to DR-40), under the manager's directives for revision 3

Every finding is **addressed**; none is backlogged or declined. Where the manager's directive chose among the review's options, the choice
follows the directive, and the reason is given.

| Id | Sev. | Resolution | Where |
|---|---|---|---|
| DR-28 | HIGH | The manager's preferred design, not the review's refusal of the team retirement: the retirement is never refused, and a root definition of the same owner and name **continues** the newest retired copy that has a delivered request (copies from `<owner>/services/.retired/` and from the retired agent trees, found by `RetiredTree.addr`; `RecordedContinuations`; `FsServiceStore` as `ServiceRestorer` copies the files byte for byte, the retired copy unchanged). The continued service keeps its `created` (so every earlier case is its case again, with its rejections, answers, links and judged deliveries), its criteria ids, the basis of its versions and its playbook version; the defining call cannot change the criteria or pass a playbook (P2-CONTINUES), so every later change meets the gate with the whole record. MCP root's `retire` reply names what its services keep and what is open. Soundness is argued in 5.10 ("Why this"); the review's port in `hierarchy` was not needed. 5.1's "one other way" sentence and the invariant of section 14 are corrected; the 5.8 table gains the team-retirement row and the declared, visible ways around (another owner, another name), which E5 counts. The 5.2a gate is kept, with its narrower role stated (D20). | 1, 5.1, 5.2 (step 0), 5.3 (P2-CONTINUES), 5.4, 5.8, 5.10, 11, 12, 13, 14, 15, 17 (Rule C), 18 (B8a, B8b), 19, 20 D20, D22, 21, 22 |
| DR-29 | MEDIUM | The reviewer's fix: the claim line keeps `tell the user instead of substituting` (`test_binding.py:98`, `test_goal_tools.py:63` unchanged). Re-measured on an export: 2 622 raw, 2 699 at the reference path, 2 839 with a 200-character path, 26 lines; the instruction and skill tests (574) pass except the one needle DR-31 replaces on purpose. With the floor batch's step 1: 2 642. | 8.1, 8.3, 20 D12 |
| DR-30 | MEDIUM | The reviewer's fix: on a rejection a contract version answers, `feedback(confirms=X)` still accepts exactly one link, the product's own when its write failed (ids equal to `answer_ids`, `source="human"`, no human-tier link on `X` yet); after it, P2-CONFIRMS-ANSWERED; any other shape before it, P2-CONFIRMS-RECOVERY (new text). The write order is contract, link, owner's note (the note is delivered even when the link failed, with the ids marked not confirmed), then the error. Test in B4 (a link writer that raises once, the recovery admitted and confirming, a second `confirms` refused, other ids refused). | 3 (`answer_ids`), 5.2 step 4, 5.3, 5.4, 12, 14, 18 (B4), 20 D18 |
| DR-31 | MEDIUM | The manager's preferred option: root names its reading of the rejection, the rejection's own `criterion`, which is not the link in 0a.2's sense (it never confirms, never is an assertion's `about`, never weighs in rule (b); 0a.1 already shows it as not confirmed). The reply then gives the exact question with the id (`About C3: add ...`, or `Same as R2: a one-off?`); without a reading it gives the wording and the candidate ids and no `C<k> is one of`. The link stays the human-tier note written after the yes. K4 replaces "never pass `criterion` on the rejection itself" (the pinned needle is changed on purpose, Rule K); the root `feedback` docstring gains one sentence; the s2r and s3 replays pass `criterion=["C3"]` on the reject. D23 records what is still a deviation (the id needs root's reading) and E5 counts it. | 5.6, 5.7, 5.9, 8.2, 10, 13, 15, 17 (Rule K), 18 (B4, B5, B9), 19, 20 D23, 21 |
| DR-32 | MEDIUM | The manager's preferred option: a `deliverable.path` that names a file is checked as that one file, through its folder's descriptor (the walk's `ENOTDIR` on the last component), with the folder's comparison rules (basename pairs, else the newest result's artifacts), and rendered `Deliverable file ...`; a file contract inside a folder group is checked once. Tests for both shapes in C4; E5 counts file-path contracts and their notes. | 6.3, 6.6, 13, 15, 18 (C4), 20 D25, 21 |
| DR-33 | LOW | The walk from `/` with `O_NOFOLLOW` per component replaces the single open, so a component swapped for a link after the resolve is refused (`ELOOP`), and the claim is reworded to what holds (a link that exists before the resolve is followed: a declared limit). A link as the last component is detected with `lstat` and reported, not read. A call reads at most 32 MiB (`limit` lines) and spends at most 5 s on git (each subprocess 2 s; about 9 s worst case); `None` answers are memoized under `HEAD`. The C4 test swaps the component between the resolve and the walk. | 6.3, 6.4, 6.6, 12, 13, 18 (C3, C4), 22 |
| DR-34 | LOW | The reviewer's fix (the mark counts only as the last launcher line, right after a THROTTLING `[run error]` line) plus an unforgeable channel, because a forged pair of lines followed by a kill of kiro would still pass the position rule: the launcher returns `THROTTLE_EXIT` (75) for its verdict, kiro's own 75 becomes 1, and the scheduler asks for a credit only on that exit code of a run that was not killed. Tests: a forged mark plus a non-throttle failure gives no credit; a forged pair with a later launcher line is no mark. | 9.1, 9.2, 9.3, 12, 13, 14, 18 (E2, E4), 19, 20 D24, 21 |
| DR-35 | LOW | The base section is placed last (after the requester's note), with one sentence in `## Goal` pointing to it, so the criteria and the note keep their place in the prompt; the judged text is not shortened, and `cut_body`'s pointer leads to the task file. Test: long criteria stay inside the rendered prompt. | 7.3, 18 (D3), 18.1 |
| DR-36 | LOW | Both ways are listed as declared and visible: root's one-off `delegate` without `revises` (5.8 row, 7.7) and a new service under another name (or, after DR-28, for another owner) while a rejection or a delivery is open (5.8 row, 5.9); E5 counts both. | 5.8, 5.9, 7.7, 21 |
| DR-37 | LOW | (a) New replay `test_s1r_playbook_v2_of_e4_is_refused_line_by_line` from `PLAYBOOK.4435fd0.md` -> `PLAYBOOK.e9bd92f.md` (evidence C9, R1 and the case id): P1-REFUSED lists all three changed lines (the C9 elaboration, the C8 line, Calendar arithmetic); in the replay C8 is confirmed too (D8), so it is refused as not cited. (b) The v3/v4 setup reports #24 (`...-root-3559`) with its evidence result `...-lead-f84e`, which is `blocked`, and records no verdict on it, as E4 did: a blocked case is not unrated, so P2-UNRATED names only `...-114d`. (c) Each K commit adds its own needles to the new skill test (B9: K4; C2: K2; C5: K3; D3: K1). | 8.2, 10, 18 (B6, B9, C2, C5, D3) |
| DR-38 | LOW | A basename pair unknown on both sides is dropped (the file goes to step 2 when none is left); a criterion with an empty `line_key` admits no (c) line and is quoted by its id only; a run log missing from `logs.files(addr)` gives `"free"`. | 4.1, 4.5, 6.3, 9.2, 15, 18 (E4) |
| DR-39 | LOW | 8.3 points to the floor batch's design section 7 and adopts it: its resolved step-1 text (measured: 2 642 at the reference path), the root-note order (tree or summary, scheduler line, deliverables note, floor note, stale-skill note), the constructor merge (both parameters, `deliverables` first), the regeneration of `surface_root*`, and both `kiro/api.py` export sets. Whichever batch merges second rebases onto the other. | 6.5, 8.3 |
| DR-40 | LOW | `_check_confirmation`'s four checks are named and the new refusals follow them; the ws4a tool load is line 174; P2-ROOT-ONLY, P2-NOT-AN-AMENDMENT, P2-WORDS-LONG, P2-PAIR, P4-BASE-VALUE and P4-BASE-WHERE get the `refused: ... Nothing was ...` frame; every P2 and P4 text that names arguments gives the CLI flags in a `(CLI: ...)` parenthesis (the texts are raised in `services`, the one layer both surfaces share, so one text serves both); DR-46 completes this for the texts it missed (A.3). | 5.3, 7.4, 9.1, 12 |

### A.3 The manager's closing decision (DR-41 to DR-46; binding; 2026-10-23)

Review pass 3 had 0 HIGH, 2 MEDIUM and 4 LOW findings. The design loop is closed: this design (`c0f72d1`) is approved as amended by the six items
below, which override the sections they name where they conflict. Each is an explicit TDD item of the plan and is checked by its DR id in the final validation.

| Id | Sev. | Resolution | Where | Plan commit, named tests |
|---|---|---|---|---|
| DR-41 | MEDIUM | The continuation is keyed on "a request of this service (root's sent task, `to == owner`, `service == name`, `msg_time >= created`, or no floor without `created`) with a result of ANY status (`done`, `blocked`, `failed`) in root's received box (`kernel.latest_results`)". `RetiredService.delivered` is renamed `recorded`; texts say `{k} request(s) with a result`. A human rejection of a blocked or failed result keeps the record across `retire_team` + `hire` + `define_service`, and the later amendment is refused P2-OPEN-REJECTION exactly as for a done result. Declared facet: a request still open at `retire_service`, whose result arrives after a fresh re-definition, falls outside every case (5.10, 22; E5 counts it). Consequence: `retire_team` closes the team's open requests as `failed` (`hierarchy/_retirement.py:64`), so after a team retirement every request of the service is recorded. | 5.1, 5.2 (step 0), 5.2a, 5.3, 5.8, 5.10, 13, 14, 15, 17, 18 (B8a case (k)), 20 D22, 21, 22 | 1 (design text), 18 (B8a): `test_contract_continued_services.py::test_a_copy_without_a_recorded_request_continues_nothing`, `::test_a_request_with_a_blocked_or_failed_result_is_recorded`; `test_continue.py::test_a_rejected_blocked_result_keeps_the_record_across_retire_team_hire_and_define`, `::test_retire_team_closes_open_requests_as_failed_so_they_are_recorded`, `::test_a_request_without_a_result_at_retire_service_is_not_recorded` |
| DR-42 | MEDIUM | The s1r playbook replay expects `are not C8's or C9's words`, `Write it as "- C8: The memo's very first line` and `Write it as "- C9: Every Due value is an ISO date` (R1.about == (C8, C9), so citing R1 brings C8 into `added`, 4.1). The row's explanation: C8 and C9 are both in `added` (C9 cited, C8 through R1's link), and none of the three lines is either criterion's own words. E4's literal case id maps to the replay's id through `e4_replay.ReplayIds`. | 10 (the s1r playbook row and the kit list) | 1, 13 (B6k), 14 (B6): `tests/meta/test_e4_replay_kit.py::test_replay_ids_map_e4_ids_and_pass_c_and_r_ids_through`, `::test_an_unbound_e4_id_fails`; `tests/e2e/test_org_growth_0a2.py::test_s1r_playbook_v2_of_e4_is_refused_line_by_line` |
| DR-43 | LOW | The walk classifies `ENOTDIR`/`ELOOP` from `O_DIRECTORY` + `O_NOFOLLOW` with `os.stat(part, dir_fd=fd, follow_symlinks=False)`: `S_ISLNK` -> the folder-level `link` finding (nothing read); `S_ISREG` on the last component -> the single-file group; otherwise skipped. A traverse-only parent (`EACCES` on the `O_RDONLY` open; measured on macOS: `os.open` of a 0o311 directory gives `EACCES`, `os.open("p/f", ..., dir_fd=gp)` succeeds) is walked through, never reported; only the folder itself (or the single file) that cannot be opened is `unreadable`. The git worst case is about 11 s (5 s + 2 x 2 s + 2 s for `head`). Declared residual: a traverse-only parent swapped for a link and swapped back between its two `stat`s is not detected. | 6.3 (step 3, "Git bound"), 6.6, 12, 18 (C4), 22 | 1, 23 (C4): `test_deliverable_folder.py::test_a_component_swapped_for_a_link_after_the_resolve_reports_link`, `::test_a_last_component_swapped_for_a_link_reports_link`, `::test_a_traverse_only_parent_gives_no_unreadable`, `::test_a_traverse_only_parent_swapped_for_a_link_reports_link`, `::test_a_folder_that_cannot_be_listed_is_unreadable` |
| DR-44 | LOW | The transcript mark is accepted only as the LAST `# kiro:` line before the closing `# exit <code> after <n>s` line, with a `[run error] ` line carrying `"retryErrorType":"THROTTLING"` (compact text) somewhere before it in the tail; other lines (kiro's stderr) may sit between or after. kiro's own 75 is returned as 1 on EVERY return path of `main` and `_supervise`, including the "ended" branch (`code or 1`). The credit rests on the launcher's exit code 75 of a run that was not killed. A forged mark in agent text is tested. | 9.1, 9.3, 13, 18 (E2, E4) | 1, 31 (E2), 33 (E4): `test_launch.py::test_true_when_kiro_stderr_lines_sit_between_the_run_error_and_the_mark`, `::test_false_when_a_later_kiro_line_follows_the_mark`, `::test_kiros_own_75_is_returned_as_1_on_every_return_path`, `::test_a_forged_pair_in_agent_text_passes_the_transcript_rule_but_main_returns_kiros_code`; `test_reaper_parts.py::test_a_forged_mark_with_exit_1_or_a_kill_is_charged_and_counted` |
| DR-45 | LOW | The blueprint lines `_example_texts.py:34, 81, 179` are one-off `needs.deliverable` paths (the service examples at `:267, 279, 303` name a FOLDER). The kind (folder or file) is decided per contract by the walk BEFORE groups are formed. A file contract whose folder is a folder group is checked once, as an entry of that group, by the file rule (`differs`, never `unknown`), and its services join that group's comparison basis and its block's services. | 6.3 ("Folders"), 6.6, 18 (C4), 20 D25 | 1, 23 (C4): `test_deliverable_checks.py::test_the_kind_is_decided_before_grouping`, `::test_a_file_contract_inside_a_folder_group_uses_the_file_rule_and_joins_the_basis`, `::test_a_single_file_group_outside_any_folder_group` |
| DR-46 | LOW | Every P2 refusal text that names an argument gives its CLI form: P2-NOT-A-REJECTION, P2-ABOUT, P2-WORDS-LONG, P2-WORDS-ARE-THE-REJECTION, P2-UNRATED (binding) and, for "every", P2-RETIRE-UNRATED and P2-CONFIRMS-ANSWERED (planner; texts in 5.3). The two phrases pinned by `SRC/mcp_server/tests/test_service_tools.py:35-36` that 5.7 removes are replaced on purpose in B4, in the same commit. K4 reads "in MCP `feedback` (at the terminal, `--criterion` on a reject records the answer)"; both paths are tested. | 5.3, 5.7, 8.2 (K4), 20 D16, D23, A.2 DR-40 | 1, 11 (B4), 12 (B5), 14 (B6), 16 (B9), 17 (B8), 18 (B8a): `SRC/services/tests/test_texts_cli_forms.py::test_every_p2_text_that_names_an_argument_gives_its_cli_form` (grown per commit); `SRC/cli/tests/test_service_commands.py::test_a_terminal_reject_with_criterion_records_the_answer_so_define_service_answers_is_answered`, `::test_a_terminal_reject_without_criterion_then_define_service_answers_records_the_answer`; `SRC/mcp_server/tests/test_service_tools.py::test_mcp_reject_with_a_reading_then_define_service_answers_is_admitted`; `SRC/skill/tests/test_skill_org_growth.py::test_the_skill_records_the_answer_with_define_service_and_names_the_base` |

**Also binding.** D-E4-9: every seat runs claude-sonnet-5.5 at `--effort high` (21). The floor batch (`feat/org-agent-model-floor-effort`; its design is
`docs/design/org-agent-model-floor.md` in `.worktrees/org-agent-floor`) is expected to merge to `main` before 0a.2; 0a.2's merge step rebases onto
`main` and resolves conflicts keeping both changes, the 125-line SKILL.md cap and the ROOT_INSTRUCTIONS character cap (8.3).

### A.4 The planner's corrections (no behaviour change)

- **P1. The facade guard is a port, not a statement in the facade.** `tests/architecture/facade_rules.py` requires every `_facade_*.py` method to
  be ONE `return self.runtime.<field>.<method>(<params>)` statement (no other call, no branch). A `dispatch.check_root_send(...)` call inside
  `DispatchMixin.send` (7.5) would break that rule. So D4 adds `dispatch._root_send.GuardedRootSender(MessageSender)` (constructor `inner:
  MessageSender`; `send` calls `check_root_send(actor, type, service, revises, feedback, criterion)` and then `inner.send(...)` with every
  argument unchanged), a runtime field `facade_sender: MessageSender` (`SRC/app/fields_dispatch.py`, wired in `SRC/app/wire_dispatch.py` as
  `GuardedRootSender(<the message_sender>)`), and `DispatchMixin.send` delegates to `self.runtime.facade_sender.send(...)`.
  `TESTS/architecture/facade_cases.py`'s `send` case names `facade_sender`. The rule classes keep `message_sender`. `check_root_send` stays the
  pure function in `dispatch.api` with the texts in `dispatch/_root_send.py` (the design's intent: the rule lives in dispatch).
  `GuardedRootSender` is not added to `dispatch.testing.IMPLEMENTATIONS[MessageSender]` (it is a guard over any sender; its own tests are
  `SRC/dispatch/tests/test_root_send.py`, including "every other message reaches the inner sender unchanged" with `RecordingSender`).
- **P2. `JudgedVersions` contract suite.** `services/tests` cannot import `reflection` (layers). Follow the `ServiceEvidence` pattern
  (`SRC/reflection/tests/test_case_service_evidence.py` header): `SRC/services/tests/test_contract_judged_versions.py` iterates
  `services.testing.IMPLEMENTATIONS[JudgedVersions] = [no_judged_versions, fixed_judged_versions]`, and
  `SRC/reflection/tests/test_case_judged_versions.py` runs the same suite functions against `CaseJudgedVersions` over the fs world.
- **P3. Reaper tests** go to the existing `SRC/scheduler/tests/test_reaper_parts.py` (the design's `test_reaper.py` does not exist).
- **P4. The C4 swap test uses a seam.** `SRC/reflection/_deliverables.py` splits the containment into `locate(raw: str) -> Located | None`
  (steps 1-2: type and absolute checks, `normpath`, the last-component `lstat`, `resolve`) and the module function `walk(target: Path) ->
  Opened` (step 3). The test resolves, swaps a component for a link, then calls `walk` with the stale target: no `Path.resolve` patch.
- **P5. The loop test's `runs 1 of ...` assertion** (9.3, `test_loop_throttle.py`, N=1) needs E5's counters, so it is added in E5 (plan commit
  34), not in E4.
- **P6.** B9 before B8; B6k split out of B6 (the replay kit `TESTS/testkit/e4_replay.py` with its own tests); Z0 is new (this amendment). The plan
  numbers section 18's items in 36 commits (18, above).
