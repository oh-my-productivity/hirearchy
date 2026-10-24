# Org growth, Phase 0b: Measure (technical design)

Status: design, revision 1 (no design review exists yet). Branch `feat/org-growth-phase-0b`, worktree
`/Volumes/workspace/hirearchy/.worktrees/org-growth-0b`, based on `main` `6618c0d` (0a.2 merged; the floor batch merged before it).
Design only: no production code is written in this run. The build starts after study E5's live streams finish, and 0b merges only if E5
passes (`e4-gate.md` section 3 "After the decision"; `e4-decision.md` D-E4-7).

Sources of truth, read in full:
- `docs/research/org-growth/08-synthesis.md` ("08"): sections 2, 3.1-3.3, 6, 7, 8 (row 0b is the scope).
- `docs/research/org-growth/phase-0a/go-no-go-0b.md` ("go/no-go"): section 4 items 2-8 and the section 3 ride-alongs (binding).
- `docs/research/org-growth/phase-0a1/e4-gate.md` ("the gate"): section 4 items 1-8 (binding).
- `docs/research/org-growth/phase-0a1/e4-decision.md`: D-E4-5 (reviewer ambiguity recall is a measure), D-E4-8 and D-E4-9 (every seat
  claude-sonnet-5.5 at effort high).
- `docs/research/org-growth/phase-0a/followups.md` item 3 (the flaky golden screen test).
- `docs/design/org-growth-phase-0a.md`, `-0a1.md`, `-0a2.md` (sections 20-22) and `org-agent-model-floor.md`; the 0a.2 report sections 6-8.
- `ARCHITECTURE.md` (R1-R13, 2.2, 2.3), `docs/refactor-principles.md`, and the code at `6618c0d` that writes every record read below.
- The replay corpora under `studies/` (E, E2, A5, E3, E4 s1r/s2r/s3), all tracked in git (checked with `git ls-files`: 110, 121, 43, 371
  and 1634 files). E5 (`studies/E5-org-growth-0a2-recheck/`) and its gate (`phase-0a2/e5-gate.md`) do not exist yet (checked); section 27
  says how they are adopted by amendment.

Abbreviations: `SRC` = `src/hirearchy`, `TESTS` = `tests` (in the worktree); `ST` = `studies`. Ids such as `...-root-dd87` abbreviate full
message ids (`20261021T152347923195-root-dd87`); the design states the full id wherever a test pins it.

## 1. Overview

0b makes the record of what the org did for the human readable as counts, without storing anything new. It builds the four items of 08
row 0b: **cases for one-off tasks** (root's verdicts on them are root notes), the **`quality` view** (`hirearchy quality [service]` and the
root-only MCP tool `quality()`), the **timeline of bar changes**, and a **repeat-run noise study**. Everything the view shows is derived
on each call from files that exist today: root's and the agents' mailboxes, the run logs, the services' `SERVICE.md`/`PLAYBOOK.md` and their
`history/` versions, the deliverable folders (through 0a.2's P3 checks), the agents' derived budgets and the org's git history. The core is
domain-agnostic: it speaks of cases, deliveries, verdict tiers, client kind, the case unit, the 7 core failure classes and five rule-typed
causes, never of memos or code.

The binding definitions are settled against what 0a.2 built:
- the **repeat alarm** counts only human-tier links (a `confirms` link note or 0a.2's product link), and shows the unconfirmed ones apart;
- the **cost alarm** reads `reflection.case_spend`, the function `case_total` already uses; it shows user top-ups, the runs of relayed
  reworks and the runs credited as throttled apart from the approved budget, never folded in;
- every **escape** gets a cause typed by rule (`relayed-error`, `relayed-carry-over`, `contract-gap`, `reviewer-miss`, `untyped`), with the
  rule that typed it, and health's `low_quality` reuses that typing;
- **deliveries without a verdict** are counted and never read as accepts; a delivery whose file the assistant edited by hand counts as
  neither pass nor escape;
- a **blocked task moved past without a verdict** is shown with the runs its assignee holds;
- the **timeline** marks contract amendments confirmed, unconfirmed or user-initiated, playbook versions with what their changed lines rest on
  (never as an improvement), charter edits, model changes and top-ups.

The exit criterion is "noise baseline measured; alarms checked on replayed E/E2/A5 files". 0b checks the alarms deterministically on the
files E, E2, A5, E3 and E4 (s1r, s2r, s3) kept (section 19), with expectations pre-registered here, and specifies the noise study (study
G0, section 20): the same script repeated k >= 3 times per arm, every seat claude-sonnet-5.5 at effort high, on the V3 runtime, stratified by
memory presence (controlled) and skill activation (observed), measuring the team, the assistant layer and the product's own counts.

## 2. Technology stack (locked)

Python 3.11; the existing packages only (FastMCP `mcp`, PyYAML; Textual is touched only by the flaky-test fix); `git` (already required by
`snapshots`); uv, pytest, `mypy==2.4.0 --strict`, `import-linter==2.15`, `scripts/check.sh`. No new runtime dependency, no new package, no new
dependency edge between packages (every cross-package need below is a consumer-owned port implemented in `app`, the pattern of
`app/_checked_versions.py`), no ledger, no new file kind in an organization, no event field. Strict TDD (R11) under the owner's scoped test
policy (section 18.3).

## 3. Shared definitions (each defined once)

| Name | Home | Definition |
|---|---|---|
| case | `reflection` (`Case`) | The head of a `revises` chain sent by one sender to one assignee, plus that chain (08 3.2). A **service case**: the client (`parent(owner)`) sent tasks with `service == name` (today's `DerivedCaseHistory.cases`). A **one-off case** (new): root sent tasks without `service`; the chain follows `revises` among root's one-off tasks to the same assignee. Agents' own delegations are not cases (no client verdict exists for them). Unit: `case` (08 3.1; `period` is Phase 3). |
| delivery | `reflection` (`Delivery`, new) | A task of a case whose latest result (`kernel.latest_results`) is `done`. |
| verdict, tier | `reflection` (`Verdict`), `kernel.verdict_tier` | A note with `feedback` that replies to a task of the case; its tier is `human`, `relayed` or `agent` (a root note without `source`, written before 0a, is `human`: 0a 3.1). Only `human` counts anywhere in 0b. |
| counted verdict | `reflection` (`Delivery.counted`) | The latest human-tier verdict on a delivery's task recorded after its result, unless a hand edit voids it (4.3). |
| judged | `reflection` | A delivery is judged when it has a counted verdict. A case is judged when any of its tasks has a human-tier verdict that no hand edit voids (also a verdict on a blocked or failed result). |
| escape | `reflection` | A judged delivery whose counted verdict is a `reject`: the team reported `done`, then the human client rejected it. |
| signer | `reflection.signer_of` (moved from `health/_escapes.py`) | The sender of the latest `done` result the owner received from a direct report, answering a task the owner sent after the delivered task and received before the delivery; the owner itself when none (0a 5.5, unchanged). |
| cause | `reflection.cause_of` (new, pure) | Section 5. |
| `case_spend` | `reflection.api` (0a.1 6.1, unchanged) | Runs used, plus, while the case is open or blocked, the runs handed down that were neither used nor returned. `case_total` and the cost alarm both call it. |
| approved budget | `reflection` | A service case: the contract's per-request `budget`. A one-off case: the head task's `budget` (the plan's or root's). |
| top-ups | `reflection` (`Case.top_ups`, new) | The budgets of the chain's later tasks, by their `source` (`human`, `relayed`, or not recorded), plus the budget of every note the client sent to an agent of the team inside the case window (progress's grant rule, `LogRunCounts._window`). |
| run window | `reflection._cases` (unchanged) | From the head task's id to the final result of the latest task, ending early at the client's next task to the same owner outside the chain. A window that ended early is `cut` (new flag). |
| charged run, credited run | `kernel.credited_stems` | A run log whose stem a run credit names (`run credit <addr>@<stem>`, `kernel.RUN_CREDIT_TITLE`) is credited: not charged, not counted in `runs` (0a.2 9.2, already so in `LogRunCounter`). |
| moved past (budget sense) | `mail.moved_past` (0a.1, unchanged) | A later task from the same sender revises the blocked task (or what it revised), or the sender gave a verdict on its chain after the block: its budget is released. |
| left blocked (new) | `progress._quality` | A task whose latest result is `blocked`, that `mail.moved_past` does not release, and whose sender has since sent the assignee another task outside its chain: "moved past without a verdict" (the gate's words). |
| hand edit | `reflection.DeliverableChecks` (0a.2 P3) | A `differs` finding: a file of a contract's deliverable folder that is not the team's checked version of the artifact of the delivery the finding names (`DeliverableFinding.task`). |
| `LASTING_WORDS` | `reflection.api` (new) | `("always", "never", "from now on")`, matched case-insensitively on word boundaries (`\b(always|never|from now on)\b`). |
| `CAUSES` | `reflection.api` (new) | `("relayed-error", "relayed-carry-over", "contract-gap", "reviewer-miss", "untyped")`. |
| `FAILURE_CLASSES` | `reflection.api` (new) | `("wrong", "missing", "off_spec", "unusable", "out_of_authority", "process_skipped", "wasteful")` (08 3.2), the closed core vocabulary packs map onto (Phase 3). |
| `QUALITY_DEFAULTS` | `reflection.api` (new) | `{"min_judged": 3, "repeat_window": 3, "repeat_failures": 2, "cost_ratio": 1.25}`, tunable defaults (section 6). |
| `ratio(k, n)` | `progress._quality_render` (new, pure) | `"{k} of {n}"`; `"n/a (0 of 0)"` when `n == 0`. Every rate in the view goes through it. |

## 4. Data model of every derived count

All counts are derived per call. The table names, for each, its definition, the exact files it is read from, and the function that
derives it. "Root's boxes" are `<org>/{inbox,inflight,read,sent}/*.md`; an agent's are `<org>/<addr>/{inbox,inflight,read,sent}/*.md`
(single writer `mail`). Contracts: `<owner>/services/<name>/SERVICE.md` and `history/SERVICE.v<n>.md`; playbooks: `PLAYBOOK.md` and
`history/PLAYBOOK.v<n>.md` (single writer `services`). Run logs: `<addr>/runs/<stem>.log` (single writer `runs`).

### 4.1 Cases

| Count | Definition | Files | Function |
|---|---|---|---|
| cases | Service cases of a service; one-off cases of root | client's `sent/` (tasks), contract `created` from `SERVICE.md` | `CaseHistory.cases` (unchanged), `CaseHistory.one_off_cases` (new) |
| state | `done`, `failed`, `blocked` from the latest task's latest result, else `open` | client's received boxes (results) | unchanged |
| stalled | an `open` case whose latest task `progress`'s `TaskStates.state_of` calls `stalled` now | the team's boxes, pause flags, run registry | `progress` (current state only, no history) |
| reworks, relayed reworks | tasks after the head; those with `source: relayed` | client's `sent/` | `Case.reworks`, `Case.relayed_reworks` (unchanged) |
| cut | the window ended at the client's next task to the owner before the final result | client's `sent/`, received boxes | `Case.cut` (new) |

One-off cases (`DerivedCaseHistory.one_off_cases()`, new): root's sent tasks with no `service`, grouped by `revises` exactly as service
chains are (`head()` follows `revises` within root's one-off tasks to the same `to`; a rework to another assignee heads its own case). `Case`
for a one-off: `service = ""`, `owner = head.to`, `playbook = used = 0`, `client_kind = "human"`; verdicts are root's notes with `feedback`
that reply to a task of the chain (section 8); runs use the same window rule over `agents.subtree(head.to)` (an assignee that no longer
exists has an empty team: 0 runs, said in the view). `case_of(task)` stays service-only, so `progress`, P3 and P4 behave as today.

### 4.2 Runs, spend, top-ups

| Count | Definition | Files | Function |
|---|---|---|---|
| runs | charged run logs of the owner's subtree in the window | `<addr>/runs/*.log` names; credits in each agent's received boxes | `Case.runs` (unchanged) |
| credited | credited run logs in the window | same | `Case.credited` (new) |
| relayed runs | charged runs whose stamp `s` satisfies `t.id[:21] <= s < next.id[:21]` for a relayed task `t` of the chain (`next` its successor in the chain; the last task's interval ends at the window's end, inclusive) | same | `Case.relayed_runs` (new) |
| spend | `case_spend(case)` | as above plus result `budget` headers | unchanged |
| ratio | `spend / approved budget`, two decimals; `n/a (budget 0)` when the budget is 0 | contract `budget`, head task `budget` | `progress` renderer |
| top-ups | `{"human": h, "relayed": r, "unrecorded": u, "granted": g}`: budgets of `tasks[1:]` by `source` (`None` = unrecorded, a legacy rework), and `g` = the budget of the client's notes (`type == "note"`, `budget > 0`, `to` in the team) with an id inside the window | client's `sent/` | `Case.top_ups` (new) |

`RunCounter` gains `stamps(team, start, end) -> list[tuple[str, bool]]`: the 21-character stamps of the team's run logs in the inclusive window,
each with whether a run credit names its stem. `runs_between` becomes the count of the uncredited stamps (no caller changes). `Case.runs`,
`credited` and `relayed_runs` are computed in `DerivedCaseHistory` from one `stamps` call per case.

### 4.3 Deliveries, verdicts, coverage, hand edits

| Count | Definition | Files | Function |
|---|---|---|---|
| deliveries | per case, its tasks whose latest result is `done` | received boxes of the client | `deliveries_of` (new, pure) |
| first delivery | the head task's delivery; its counted verdict (`accepted`/`rejected`) or `none` | as above | `Delivery.step == 0` |
| superseded | a delivery with no human-tier verdict whose case sent its next task before any verdict on it | client's `sent/` | `Delivery.superseded` (the next task's id) |
| judged | deliveries with a counted verdict | client's `sent/` (notes) | `Delivery.counted` |
| without a verdict | cases whose latest task is delivered and has no counted verdict at or after it (`rated` restricted to the human tier); `relayed only` = those with a relayed verdict | client's `sent/` | `unjudged_cases` (new, pure) |
| verdicts on non-deliveries | human-tier verdicts on a task whose latest result is `blocked` or `failed` | client's `sent/` and received boxes | `Case.verdicts` filtered |
| hand-edited | deliveries a `differs` finding names, settled or not | deliverable folders, org git history (P3) | `DeliverableChecks.findings(ROOT, service, settled=True)` |
| legacy verdicts | human-tier verdicts without `source` | client's `sent/` | `Verdict.message.source is None` |

**Hand edits void a verdict only when the edit came first.** `DeliverableFinding` gains `written: int` (the file's mtime in microseconds,
which P3 already reads as `FolderFile.mtime_us`) and `settled: bool`. `DeliverableChecks.findings` gains the keyword `settled: bool = False`:
with `True`, findings P3 would leave out as settled are returned with `settled=True` (P3's own notes keep calling it with the default, so
`progress`, `status` and `whoami` are unchanged). For a delivery `d` that a finding names, `d.edited_at = finding.written`; its counted verdict
is the latest human-tier verdict recorded before `edited_at` (it judged the team's file). A human-tier verdict at or after `edited_at`
judged the hand-edited file: it is voided (`Delivery.voided`), and the delivery counts as neither pass nor escape. A hand-edited delivery
without a verdict is counted both as "without a verdict" and as "hand-edited". Only the file as it is now is known: section 26.

### 4.4 Escapes, signers, verifiers

| Count | Definition | Files | Function |
|---|---|---|---|
| escapes | judged deliveries whose counted verdict is `reject` | client's `sent/` | `Delivery.escape` |
| signer | section 3 | owner's `sent/` (tasks) and received boxes (reports' results) | `signer_of` (moved from health, unchanged rule) |
| PASS precision | per signer other than the owner: accepted / judged deliveries it signed off | as above | `progress` renderer |
| verifier FAILs | per signer: `rechecks` and `rework_runs` of `health.MailEscapeCounter` (0a 5.5, unchanged) | the signer's boxes, authors' run logs | `FailCounts` (progress port, app adapter over health) |
| assertion | `R<k>`: the k-th human-tier rejection of the service | client's `sent/` | `regressions` (unchanged) |
| cause | section 5 | as section 5 | `cause_of` |
| failure class | `off_spec` for an escape typed `reviewer-miss`; `wasteful` for a case above the cost threshold; no other class is derived in 0b (`null`) | derived | `failure_class` (new, pure) |

### 4.5 Blocks moved past without a verdict, held runs

| Count | Definition | Files | Function |
|---|---|---|---|
| left blocked | for every agent `A` and every `t` in `TaskQuery.blocked_tasks(A)`: `not moved_past(t, latest[t.id], received(A))` and `received(A)` holds a task from `t.sender` with an id above the blocked result's id that is outside `t`'s chain | `A`'s boxes | `progress._quality.left_blocked` (new, pure over mail reads) |
| held | `BudgetQuery.budget(A)` when `A` has a left-blocked task and the value is above 0 | everything `budget` derives from | `progress` |

The held figure is the assignee's whole derived budget: while a task stays blocked and is not moved past, `budget.ReserveAllocationPolicy.
budget_to_return` treats the agent as busy and its later results return nothing (0a.1 item 5). The view names that mechanism; it does not
split the budget per task (section 24, D19).

### 4.6 The core concepts in the data

- **Source tiers** (08 3.1): only `human` counts in a count of client evidence; `relayed` and `agent` verdicts are counted apart and named.
  `external`, `client-check` and `runtime-check` tiers are Phase 3; the JSON carries `tier` per verdict so they slot in.
- **`client_kind`**: `human` when the client is root, else `agent` (`Case.client_kind`, 0a). A service with an agent client has only
  agent-tier verdicts: its block is one line of counts, never quoted words, never an alarm (section 9.2).
- **Unit**: every record says `unit: case`.
- **Failure classes**: the vocabulary is fixed now; 0b derives a class only where a rule can (4.4); every other escape is `unclassed`.
- **Rule-typed causes**: section 5.

## 5. Rule-typed causes

### 5.1 The rules, in order

`cause_of(delivery, case, assertion, carried, results) -> Cause` (pure; `reflection/_causes.py`, exported from `reflection.api`) types an
escape. `v` is the counted verdict; `assertion` is its `R<k>` (`regressions`); `carried` is the set of `C<k>` ids current in the contract
version the rejected task carried (`task.contract`; a legacy task without it uses the version in force at the task's time; a one-off has
none); `results` maps each task of the case to its latest result. The rules are tried in this order; the first that matches is the type,
and every later rule that also matches is listed in `also` (a disputed cause, retro material):

1. **`relayed-error`**: the rejected delivery answers a relayed task (`delivery.task.source == "relayed"`). The team did what the assistant
   asked on its own reading.
2. **`relayed-carry-over`** (the gate's item 3): the rejected task `T` is not relayed, and there is a relayed task `R` of the chain with
   `J < R.id < T.id`, where `J` is the result id of the latest delivery of the case whose counted verdict was recorded before `T` was sent
   (the head task's id when there is none), such that
   - `R`'s latest result is `done` and lists an artifact (`kernel.artifact_paths`) that `T`'s delivery also lists, and
   - `T`'s body does not carry `services.BASE_DELIVERED_HEADING` (`"## Base: the version the client judged"`, 0a.2 7.3): the lead was not
     told to restore the judged version. A body with `BASE_LATEST_HEADING` (`"## Base: the current version"`) or with no base section
     qualifies. After 0a.2, P4 adds no base section only when no relayed rework changed the judged artifact, so a relayed rework that
     touched other files does not match the shared-artifact clause in practice, and a legacy chain is judged by the artifact lists (the P4
     no-history rule, 0a.2 D11).
3. **`contract-gap`, by answer**: a human-tier answer to this rejection names a criterion that `carried` lacks: a `C<k>` in
   `v.confirmed` (the human-tier link notes of the verdict, including 0a.2's product link), or in `assertion.about` when
   `assertion.link == "confirmed"` (a "same as R<j>" link resolved). The client said yes to a lasting rule the task's contract did not have.
4. **`reviewer-miss`**: a human-tier answer names a criterion that `carried` has. The team reported `done`, which asserts every criterion met
   (`services.FEEDBACK_HEADER`: "report `done` only if every criterion is met"), so its sign-off passed a criterion the client says failed.
5. **`contract-gap`, by words**: the client's words (`v.note`) contain a word of `LASTING_WORDS` (08 3.2's rule).
6. **`untyped`**: nothing matched; when the human-tier link is `none`, the detail says "the user said it is no lasting rule".

`Cause` (frozen dataclass): `type` (one of `CAUSES`), `rule` (`"relayed task"`, `"carry-over"`, `"answer"`, `"link"`, `"words"`, `"none"`),
`detail` (the ids the rule read: the relayed task, the shared artifact, the link note and criterion, or the matched word), `also` (the types
of the later rules that match), `before_verdict` (the id of a relayed task of the case whose `done` result lies between the rejected delivery
and the verdict: "the user may have judged that version"; `""` otherwise).

### 5.2 Why this order

The structural relayed rules come first because they name a cause outside the team that the data shows directly, and they must win over the
answer that followed: in E4 s2r the Marta escape was introduced by the injected relayed rework, inherited by Lena's rework, and then answered
with a new criterion C10; the gate pre-registers it as relayed carry-over (rule 2 before rule 3). The recorded answer comes before the reviewer
rule because the same link that names a criterion says whether the task's contract had it; rules 3 and 4 partition the human-linked rejections.
The words rule is the weakest evidence (a phrase in a note) and comes after the link rules, so a reject that names a criterion the reviewer
passed is a reviewer miss even if the note says "always" (it is listed in `also`). Section 24 D1-D3 records the departures from 08's list.

### 5.3 The texts (the view; `progress/_quality_render.py`)

| Type (rule) | Text after `R<k> case <id>, signed off by <signer>: ` |
|---|---|
| relayed-error | `relayed-error (the rejected delivery is your relayed rework {task})` |
| relayed-carry-over | `relayed-carry-over (your relayed rework {R} changed {path} after the delivery the user judged, and this rework started from it)` |
| contract-gap (answer) | `contract-gap (the user's answer, link {link}, names {C}, which contract v{n} of the task did not have)` |
| reviewer-miss | `reviewer-miss (the user's confirmed link {link} names {C}, which contract v{n} of the task had; the team reported done)` |
| contract-gap (words) | `contract-gap (the user's words say "{word}")` |
| untyped | `untyped (no rule matched)` or `untyped (the user said it is no lasting rule)` |

Then, when present: `; also {types}` and `; your relayed rework {id} delivered after it and before the verdict: the user may have judged
that version`. `{path}` is the org-relative artifact path, rendered with `reflection.shown_name` (an artifact path is agent-written text).

## 6. Alarms (thresholds are tunable defaults)

| Threshold | Default | Meaning |
|---|---|---|
| `min_judged` | 3 | an alarm is evaluated only once the record has this many judged cases (08 3.3); before that it reads `n/a ({k} of 3 judged cases)` |
| `repeat_window` | 3 | the repeat alarm looks at this many most recent judged cases |
| `repeat_failures` | 2 | ... and fires when one subject failed in at least this many of them |
| `cost_ratio` | 1.25 | the cost alarm fires for a case whose `case_spend` is above this times its approved budget |

They are read from an optional `quality:` mapping in ORG.md's frontmatter (the pattern of `health:`), through the app adapter
`ReadableOrgConfig` over `settings.readable_config`. Validation (section 14): integers for the first three (`min_judged >= 1`,
`repeat_window >= 1`, `1 <= repeat_failures <= repeat_window`), a finite number `> 0` for `cost_ratio`; a value that fails keeps its default
and adds the note `quality.{key} in ORG.md is not {what}: the default {d} is used.`; a `quality:` that is not a mapping is ignored with
`quality in ORG.md is not a mapping: the defaults are used.`; an ORG.md whose settings block does not parse gives the defaults and the note
`ORG.md cannot be read (its settings block does not parse): the default thresholds are used.` The view's header always says which applied.

**Repeat** (`repeat_alarm(record, t)`, pure). The judged cases, ordered by the id of their latest human-tier verdict; the last
`repeat_window` of them. The subjects of a case are: the `R<k>` of each of its human-tier rejections, every `C<k>` and `R<j>` its human-tier
link names (`Verdict.links` when `links_tier == "human"`, `none` excluded), and the criteria each such `R<j>` is about
(`Assertion.about`). A subject in at least `repeat_failures` of the window's cases fires the alarm. A criterion that only a relayed reading
names (the rejection's own `criterion`, or a relayed link) is never a subject; such links are listed as `not counted`. States: `fires`, `no`,
`n/a ({k} of {min_judged} judged cases)`, and for root's one-off tasks `does not apply (one-off tasks name no criterion ids)`.

**Cost** (`cost_alarm(record, t)`, pure). Evaluated once the record has `min_judged` judged cases; fires for every case of the record (any
state) with `case_spend(case) > cost_ratio * approved`. A case whose approved budget is 0 is skipped and named. The alarm compares with the
approved budget only: top-ups (human reworks, relayed reworks, unrecorded reworks, grants), relayed runs and credited runs are shown beside it
(go/no-go item 3, the gate's item 5). Each case line shows its ratio whatever the alarm says, and `case_total` keeps warning at 1.0x on any
case, so the user is told of an overspend before three cases are judged.

Both alarms ignore epochs: no count is split by contract or playbook version (08 3.3).

## 7. The timeline of bar changes

`ServiceRecord.timeline` (newest last; the view shows the 15 newest, then `and {k} earlier`). The marks are facts; no count is partitioned by
them and no mark says "improved".

| Kind | Source files | Fields | Text |
|---|---|---|---|
| contract | every stored `SERVICE` version (`ServiceStore.versions(owner, name, "SERVICE")`, read through a reflection port `ContractVersions`) | version, `defined`, `defined_by`, added and removed ids (`number_criteria` over the stored versions), basis | see below |
| playbook | `ServiceCatalog.playbook_versions` | version, `revised`, `by`, `admitted`, cited ids, changed-line counts | see below |
| charter | git history of `<addr>/AGENT.md` | addr, commit, when | `{addr}: charter edited (commit {12 hex})` |
| model | git history of `<addr>/AGENT.md` and `ORG.md` | addr or `ORG.md`, key (`model`, `effort`), before, after, commit | `{addr}: model {before} -> {after}` / `ORG.md: default model ...` / `ORG.md: effort ...` |
| top-up | the cases (4.2) | case, task or note id, amount, kind | `top-up +{n} run(s) to case {case}: {human rework {id} | your relayed rework {id} (your own spend) | rework {id} (tier not recorded) | your grant {id}}` |

**Contract marks.** v1: `contract v1 ({ids})`. A later version: `contract v{n} ({by}): adds {ids}; removes {ids}` (each part only when
non-empty; `criteria unchanged` when neither), then its basis:
- `answers` set (0a.2 P2): `: the user's answer to {R} (link {id}): {ids} confirmed`;
- `initiated: user`: `: asked for by the user on their own: {ids} user-initiated (never admit a playbook revision)`;
- a root version without either (written before 0a.2): per added id, `confirmed (link {id})` when `confirmed_criteria` names it (0a.1's rule),
  else `not confirmed`; the mark ends `: not confirmed` when none is;
- `defined_by` an agent: `: by {agent}, an agent client (its verdicts are hypotheses)`.

**Playbook marks.** `playbook v{n} ({by})`, then:
- `admitted: c`: `: admitted (c) on {cited ids}: {k} changed line(s): {w} a criterion's own words, {b} beyond them`;
- `admitted: b`: `: admitted (b) on {cited ids}: {k} changed line(s): {t} tagged with an id, {u} untagged`;
- `first`, `restore`: `: first version` / `: restores v{m}`;
- no `admitted`, written by the client (`by` is the owner's parent: root for a top-level owner): `: written by the client (no admission
  needed)` (0a 3.5: a version the client wrote has none);
- no `admitted`, written by the owner (legacy, before 0a): `: no admission recorded (written before the evidence gate)`;
then `; {r} line(s) removed` when any. The counts are recomputed for every version from the stored bodies:
`changed_lines(previous.body, body)` (services.api, 0a.2); a line is "a criterion's own words" when its `line_key` equals
`line_key(c.id) + line_key(c.text)` or `line_key(c.text) + line_key(c.id)` for any criterion of the service (P1's rule, `_words_of`, moved to
`services.api` as `criterion_words(line, criteria)` so both read one rule); "tagged" when it carries a `C<k>` or `R<k>` token. The gate's item 2
("on C9; content not checked against it, with its diff beside the cited criterion") is met by recomputation: a version admitted before P1
shows its lines beyond the cited criterion (E4 s2r v2), and one admitted after P1 shows 0 beyond by construction. Cited ids are shown only when
they match `C\d+`, `R\d+` or a message id (`\d{8}T\d{12}-[a-z0-9./-]+`); others are counted (`and {k} other id(s)`), because evidence ids are
agent-written. The playbook's `reason` is never shown (agent-written text).

**Charter and model marks** come from a reflection port `BarHistory` (`reflection/_ports.py`), implemented in `app/_bar_history.py` by
`GitBarHistory(history: OrgHistory, clock: Clock)`:
1. `history.changes([f"{a}/AGENT.md" for a in addrs] + ["ORG.md"], limit=40)` (new `OrgHistory` method, 12.6): `(commit, committed time,
   path)` per changed path, newest first, at most 40 commits; `None` without a repository or git.
2. For each path, consecutive listed versions (newer, older): `history.text(commit, path, 65536)` of each (memoized per pair). AGENT.md:
   bodies differ (after `kernel.split_frontmatter`) -> a charter mark; frontmatter `model` differs -> a model mark. ORG.md: `model` or
   `effort` differs -> a model mark. The oldest listed version of a path has no predecessor in the list: no mark (its creation, or beyond the
   bound; `truncated=True` when the list was full).
3. A bound of 5 s of git time per call (`Clock.monotonic`, read before each read) and 2 s per git subprocess; past it the rest is not read and
   `truncated=True`.
The result is `BarChanges(known: bool, marks, truncated: bool)`. `known=False` renders `charter edits and model changes: unknown (no org
history: the organization is not a git repository, or git is missing)`; `truncated` adds `(the newest 40 commits were read)`. Charter and
model marks are listed in the block of every service whose owner subtree contains the addr, and in the one-off block for the assignees'
subtrees. A retired agent's AGENT.md moved under `.retired/` is not followed (section 26).

## 8. One-off cases as root notes: the provenance rules

### 8.1 The write path: root's `feedback` accepts a one-off task

08 3.1 stores one-off verdicts as root notes on the task, written by the assistant, with no agent tool change. Root's existing `feedback`
(MCP root `feedback`, CLI `hirearchy feedback`, `Org.feedback`), all through `services.RuleClientFeedback.feedback`, gains a branch for
`actor == ROOT` and a task without `service`:
1. The task is one of root's sent tasks. With a `service`, today's service path runs unchanged; without one, the one-off path below; when no
   task root sent has that id, ONE-OFF-UNKNOWN (8.3).
2. `criterion` or `confirms` given: ONE-OFF-NO-LINK. A one-off has no contract, so a rejection names no criterion and answers no rejection.
3. `verdict` in `VERDICTS`; a `reject` needs a note; the note is at most `FEEDBACK_MAX` (1000) characters (the existing checks and texts).
4. The task has a result in root's received boxes (existing text).
5. The assignee still exists (`agents.exists(task.to)`); otherwise ONE-OFF-GONE: a quiet note needs a recipient.
6. The note is written exactly as a service verdict is: `sender.send(ROOT, task.to, FEEDBACK_HEADER + "\n\n" + (note or "accepted"),
   type="note", title=f'feedback on "{task.title}": {verdict}', reply_to=task.id, feedback=verdict, source=source, wake=False)`.

Agents' `feedback` is unchanged: an agent's non-service task is refused with today's text. No agent tool changes.

**The provenance rules from day one** (go/no-go item 6):
- `source` defaults to `relayed`: MCP root `feedback` already defaults to `source="relayed"`, and `dispatch.provenance_source` stamps a root
  verdict note without `source` as `relayed` (unchanged).
- The user's words are verbatim: the docstring and the skill say so; the product cannot check it (declared provenance, section 26).
- The reply names the next step (8.2). Because a one-off has no contract to fall back on, a relayed one-off verdict counts as no verdict in
  `quality`, and the reply says so.

### 8.2 The reply's next step (`reflection/_steps.py:TextServiceSteps.feedback_step`)

`feedback_step(note)` returns, for a verdict note on a one-off task (the reply already starts with today's receipt line
`feedback {verdict} recorded on {task_id} for {to} (message {id}, source {source}); it does not wake {to}`):
- relayed (accept or reject): `\nRecorded as relayed (your own reading): quality counts it as no verdict of the user. If the user said it,
  record their words, verbatim, with source="human".`
- human reject: `\nNext: if the user wants it redone, send it back with delegate(to="{to}", title=..., goal=<their corrections, in their
  words>, acceptance=<the criteria, verbatim>, revises="{task}", source="human"). A one-off task has no contract: no criterion changes.`
- human accept: `""`.

### 8.3 Refusal texts (constants in `SRC/services/_feedback.py`)

- **ONE-OFF-UNKNOWN** (root only; replaces today's text for root): `` refused: {task_id} is not a task you sent: feedback records the user's
  verdict on one of your service requests or one-off tasks that has a result. Your newest: {up to 10 ids, newest first, or "none"}. Nothing
  was recorded. `` Agents keep today's text.
- **ONE-OFF-NO-LINK**: `refused: {task_id} is a one-off task: it has no contract, so its verdict names no criterion and answers no rejection.
  Leave out criterion and confirms (CLI: --criterion, --confirms). Nothing was recorded.`
- **ONE-OFF-GONE**: `refused: {to}, who did {task_id}, was retired, so the verdict has no one to tell. Nothing was recorded.`

### 8.4 Docstring, help and skill

- Root `feedback` docstring: the first sentence becomes `Record the user's verdict on a delivered task: one of your service requests (or a
  rework) or one of your one-off tasks: verdict "accept" or "reject".`, and after the `source:` sentence: `A one-off task takes no criterion
  or confirms (it has no contract).` (re-wrapped at today's column; `test_service_tools.py` pins other phrases, which stay).
- CLI `feedback` help: `task` becomes `the service request, rework or one-off task the verdict is on`.
- SKILL.md step 5.6 (net 0 lines, section 11.3): one-off tasks are rated the same way, only on a verdict the user states, with no extra question.

### 8.5 What one-off cases do not change

`questions_open` keeps settling a one-off result's client questions only by the user's own rework (unchanged); P3 keeps never settling a
one-off hand-edit note by a verdict (unchanged; backlog, section 23); `delivered_unrated` and the P2 gate are service-only (unchanged).

## 9. The quality view

### 9.1 Surfaces

| Surface | Signature | Who | Where |
|---|---|---|---|
| MCP | `quality(service: str \| None = None) -> str` | root only (a `root_only` group, registered after `progress`; agents never get it: 08 2.6) | `SRC/mcp_server/_tools_quality.py:QualityTools(setup: SetupMode, report: Provider[QualityReport])`; runs in a worker thread (`anyio.to_thread.run_sync`), like `progress` |
| CLI | `hirearchy quality [service] [--json]` | the terminal (the user's seat) | `SRC/cli/_commands_views.py:QualityCommand(session, report: Provider[QualityReport], out)` |
| Python | `progress.QualityReport.quality_text(service=None) -> str`, `.quality_data(service=None) -> JsonObject` | app, tests | `SRC/progress/_quality.py:DerivedQualityReport` |

The MCP text and the CLI text are the same string. `--json` prints `quality_data` with `json.dumps(indent=2, sort_keys=True)`; it exists
for the study harness (section 20) and scripts. In setup mode (no org bound) the MCP tool returns `SetupMode.state()`, like `progress`.

MCP docstring (`quality`):
```
How the work you asked for has gone, from the files: per service, and for your one-off tasks, the cases; the user's verdicts on first
deliveries, in their words; escapes (the team reported done, then the user rejected it) with the verifier that signed them off and the
cause a rule typed; deliveries without a verdict (never counted as accepts) and hand-edited ones; runs per case against the approved
budget, with top-ups, your own relayed reworks and runs not charged shown apart; blocked tasks moved past without a verdict and the runs
held behind them; two alarms (repeat, cost; tunable defaults) and the timeline of bar changes. Read-only, root only: agents never see it,
and you never pass these counts to an agent. service: one service's block (default: everything). Use it when the user asks how a service
or the org is doing, and say what it shows in plain words.
```
CLI help: `quality`: `how the work root asked for has gone: verdicts, escapes and their causes, runs per case, alarms, bar changes`;
`service`: `only this service`; `--json`: `the same data as JSON`.

ROOT_INSTRUCTIONS line 7 (`SRC/mcp_server/_instructions.py`) gains `, `quality` (how they went)` after `` `define_service` ``: 27 characters,
so 2 669 at the reference path (< 2 700), 2 592 raw (< 2 800) and 2 809 at a 200-character path (< 2 900), measured from 0a.2's 2 642 /
2 565 / 2 782 (report section 5); the budget test pins it.

### 9.2 The text (`SRC/progress/_quality_render.py`, pure)

Order: header, notes, one block per service root requests (top-level agents' services, by owner then name), the one-off block, the line for
nested services, the moved-past section. With `service`, only that service's blocks (every owner offering that name) and no one-off block.

```
Quality of the work you asked for (derived from the files, nothing stored; for you and the user, never for agents).
Thresholds: {the defaults | from ORG.md quality:} (tunable): alarms need {min_judged} judged cases; repeat: one id failing in {repeat_failures} of the last {repeat_window} judged cases; cost: a case above {cost_ratio}x its approved budget.
{each note of 6 and 16, one per line}

{service} (offered by {owner}; client: you, human; unit: case; contract v{c}, playbook v{p}; approved {budget} runs per request)
  cases: {n} (done {d}, failed {f}, blocked {b}, open {o}, stalled {s}){; {m} blocked and moved past without a verdict}
  first deliveries: {a} accepted, {r} rejected, {w} without a verdict{ ({x} superseded by a rework before a verdict)}{; {y} never delivered}
    {case id}: {accepted | rejected}: "{the user's words}" | {case id}: accepted (no words) | {case id}: no verdict{ (superseded by {human rework | your relayed rework | rework} {id}{ (tier not recorded)})} | {case id}: never delivered ({blocked | failed | open})
  judged by the user: {ratio(judged, deliveries)} deliveries; without a verdict: {u} case(s){ ({ids}): never counted as accepted}{ ({q} with only your own relayed verdict)}; hand-edited: {h}{ ({ids})}
  {legacy verdicts (no source, counted as the user's, the 0a rule): {g}; }{verdicts on blocked or failed results: {z}}
  escapes (the team reported done, then the user rejected it): {e | none ({ratio} judged deliveries)}
    {R} case {case id}, signed off by {signer}: {cause text of 5.3}
  verifiers: {signer}: PASS precision {ratio(accepted, judged)}; escapes {e}{ ({k} {type}, ...)}; its FAILs before delivery: {r} re-check(s), {w} author rework run(s) | verifiers: none (every delivery was signed off by {owner} itself)
  runs per case (spend = runs used, plus runs still out while a case is open or blocked; approved {budget}):
    {case id} "{title}": {spend} ({x.xx}x){, {k} in your relayed reworks}{, {c} not charged (model-service throttle)}; top-ups: {none | +{n} human rework {id}, +{n} your relayed rework {id}, +{n} rework {id} (tier not recorded), +{n} your grant {id}}{; window cut by a later request}
  alarms:
    repeat: {FIRES: {id} failed in {k} of the last {w} judged cases ({R} case {id}, ...) | no ({w} judged cases; counted: {ids or "none"}) | n/a ({k} of {min} judged cases)}{; not counted: {R}'s reading {ids} (not confirmed), ...}
    cost: {FIRES: case {id} {spend} of {budget} ({x.xx}x){, {k} in your relayed reworks}, ... | no (0 of {n} cases above {cost_ratio}x) | n/a ({k} of {min} judged cases)}
  timeline (bar changes, UTC; marked, never used to split the counts):
    {YYYY-MM-DD HH:MM} {mark of section 7}
    {charter edits and model changes: unknown (...) | none}
  run attribution is by time window (08 3.3): {k} case(s) had their window cut by a later request; their later runs count for that request.
```
Limits: the 10 newest cases per block (`and {k} earlier case(s), counted above`), the 10 newest escapes, the 15 newest timeline marks, the 10
newest ids per list (`and {k} more`). Titles are root's own (`clip_line(title, 80)`); the user's words are quoted only for counted
human-tier verdicts, in the first-delivery lines (`clip_line(words, 160)`, the words `FeedbackWords.feedback_text` returns without the fixed
header; the escape lines show the cause, which names what the rule read); agent-written text (lessons, playbook reasons, result bodies, agents' task titles, file names) never appears, and artifact paths
and model names go through `shown_name` (section 15, I8).

The one-off block has the heading `One-off tasks you gave (client: you, human; unit: case; approved budget: each task's own)`, shows the
assignee after each case title (`"{title}" ({assignee})`), and its repeat line reads `repeat: does not apply (one-off tasks name no criterion
ids)`. Nested services are one line each under `Services your agents request (the client is an agent: its verdicts are hypotheses, never
counted):` as `- {service} (offered by {owner}; client {client}): {n} case(s), {d} delivered, {v} agent verdict(s)`. The moved-past section:
```
Blocked tasks moved past without a verdict (while one stays open, its assignee's later results return no runs):
  {addr} holds {n} run(s): {task {id} from you ("{title}") | {k} task(s) from {sender} ({ids})}, blocked since {YYYY-MM-DD HH:MM}; {sender} has sent {addr} {j} task(s) since.
```
or `Blocked tasks moved past without a verdict: none.` An org with no case at all: `No cases yet: you have requested no service and given no
task.` followed by the moved-past section.

### 9.3 Sample outputs (exact)

**E3's files** (the replay of section 19; MCP and CLI print the same text):
```
Quality of the work you asked for (derived from the files, nothing stored; for you and the user, never for agents).
Thresholds: the defaults (tunable): alarms need 3 judged cases; repeat: one id failing in 2 of the last 3 judged cases; cost: a case above 1.25x its approved budget.

weekly-meeting-memo (offered by lead; client: you, human; unit: case; contract v3, playbook v1; approved 15 runs per request)
  cases: 3 (done 3, failed 0, blocked 0, open 0, stalled 0)
  first deliveries: 0 accepted, 2 rejected, 1 without a verdict (1 superseded by a rework before a verdict)
    20261021T152347923195-root-dd87: rejected: "No, not right yet. Sam's CI item says 'before Friday', so that has a date, 2026-10-09. And Marta's room is for the training on the 14th, so I want 2026-10-14 t…"
    20261021T153031017749-root-207b: no verdict (superseded by your relayed rework 20261021T153213891373-root-248f)
    20261021T153809201054-root-ab46: rejected: "Almost, but not right yet: 'Marta keeps the agenda as sent' isn't an action item, nobody has to do anything there. Take that row out. Lee's Friday is right, an…"
  judged by the user: 5 of 6 deliveries; without a verdict: 0 case(s); hand-edited: 0
  escapes (the team reported done, then the user rejected it): 2
    R1 case 20261021T152347923195-root-dd87, signed off by lead/reviewer: contract-gap (the user's words say "always")
    R2 case 20261021T153809201054-root-ab46, signed off by lead/reviewer: contract-gap (the user's answer, link 20261021T154557001479-root-8ca0, names C11, which contract v2 of the task did not have)
  verifiers: lead/reviewer: PASS precision 3 of 5; escapes 2 (2 contract-gap); its FAILs before delivery: 2 re-check(s), 2 author rework run(s)
  runs per case (spend = runs used, plus runs still out while a case is open or blocked; approved 15):
    20261021T152347923195-root-dd87 "Memo for the meeting of 2026-10-05": 12 (0.80x); top-ups: +6 human rework 20261021T152757534448-root-d995
    20261021T153031017749-root-207b "Memo for the meeting of 2026-10-12": 15 (1.00x), 10 in your relayed reworks; top-ups: +5 your relayed rework 20261021T153213891373-root-248f, +5 your relayed rework 20261021T153557949152-root-52d7
    20261021T153809201054-root-ab46 "Memo for the meeting of 2026-10-19": 14 (0.93x); top-ups: +5 human rework 20261021T154215162562-root-2ccf
  alarms:
    repeat: no (3 judged cases; counted: R1, R2, C11); not counted: R1's reading C6, C3 (not confirmed)
    cost: no (0 of 3 cases above 1.25x)
  timeline (bar changes, UTC; marked, never used to split the counts):
    2026-10-21 15:23 contract v1 (C1, C2, C3, C4, C5, C6, C7, C8)
    2026-10-21 15:23 playbook v1 (root): written by the client (no admission needed)
    2026-10-21 15:27 contract v2 (root): adds C9, C10; removes C3, C6: not confirmed
    2026-10-21 15:27 top-up +6 run(s) to case 20261021T152347923195-root-dd87: human rework 20261021T152757534448-root-d995
    2026-10-21 15:32 top-up +5 run(s) to case 20261021T153031017749-root-207b: your relayed rework 20261021T153213891373-root-248f (your own spend)
    2026-10-21 15:35 top-up +5 run(s) to case 20261021T153031017749-root-207b: your relayed rework 20261021T153557949152-root-52d7 (your own spend)
    2026-10-21 15:42 top-up +5 run(s) to case 20261021T153809201054-root-ab46: human rework 20261021T154215162562-root-2ccf
    2026-10-21 15:45 contract v3 (root): adds C11: C11 confirmed (link 20261021T154557001479-root-8ca0)
    charter edits and model changes: unknown (no org history: the organization is not a git repository, or git is missing)
  run attribution is by time window (08 3.3): 0 case(s) had their window cut by a later request; their later runs count for that request.

One-off tasks you gave: none.

Blocked tasks moved past without a verdict: none.
```
Every figure above is read from E3's kept files (the replay pins them): the runs (12, 15, 14) equal the case totals 0a.1 6.1 states for E3;
the 10 relayed runs are the charged logs of `run-logs/` with stamps from `...-root-248f` to the end of the window; the FAIL counts are E3's
health line (`re-checks after a FAIL 2 (author rework runs 2)`).

**E4 s1r's files, excerpt** (values in angle brackets are pinned by the replay, not restated here):
```
weekly-memo (offered by lead; client: you, human; unit: case; contract v5, playbook v2; approved 15 runs per request)
  cases: 3 (done 2, failed 0, blocked 1, open 0, stalled 0); 1 blocked and moved past without a verdict
  first deliveries: 0 accepted, 1 rejected, 2 without a verdict
    20261022T182945409755-root-ed94: rejected: "<the user's words>"
    20261022T191407596413-root-114d: no verdict
    20261022T192724706946-root-2efa: no verdict
  judged by the user: 1 of 3 deliveries; without a verdict: 2 case(s) (20261022T191407596413-root-114d, 20261022T192724706946-root-2efa): never counted as accepted; hand-edited: 3 (20261022T182945409755-root-ed94, 20261022T191407596413-root-114d, 20261022T192724706946-root-2efa)
  escapes (the team reported done, then the user rejected it): 1
    R1 case 20261022T182945409755-root-ed94, signed off by lead/checker: contract-gap (the user's answer, link 20261022T190014222948-root-1753, names C9, which contract v1 of the task did not have)
  runs per case (spend = runs used, plus runs still out while a case is open or blocked; approved 15):
    20261022T182945409755-root-ed94 "<title>": 25 (1.67x), 5 in your relayed reworks; top-ups: +6 your relayed rework 20261022T184712524029-root-9ce9, +6 human rework 20261022T190015448581-root-3559
    20261022T191407596413-root-114d "<title>": 7 (0.47x); top-ups: none
    20261022T192724706946-root-2efa "<title>": 9 (0.60x); top-ups: none
  alarms:
    repeat: n/a (1 of 3 judged cases)
    cost: n/a (1 of 3 judged cases)
  timeline (bar changes, UTC; marked, never used to split the counts):
    2026-10-22 18:58 contract v2 (root): adds C8, C9: C9 confirmed (link 20261022T190014222948-root-1753), C8 not confirmed
    2026-10-22 19:03 playbook v2 (lead): admitted (c) on <ids>: <k> changed line(s): <w> a criterion's own words, <b> beyond them
    ... <v3, v4 (removes C9, adds C11), v5: every added criterion not confirmed>

Blocked tasks moved past without a verdict (while one stays open, its assignee's later results return no runs):
  lead holds 12 run(s): task 20261022T190015448581-root-3559 from you ("<title>"), blocked since 2026-10-22 19:11; you have sent lead 2 task(s) since.
  lead/writer holds 4 run(s): 3 task(s) from lead (<ids>), blocked since <time>; lead has sent lead/writer <j> task(s) since.
```

**A5's files, the one-off block** (A5 kept no run log, so its runs read 0: section 19):
```
One-off tasks you gave (client: you, human; unit: case; approved budget: each task's own)
  cases: 1 (done 1, failed 0, blocked 0, open 0, stalled 0)
  first deliveries: 0 accepted, 0 rejected, 1 without a verdict (1 superseded by a rework before a verdict)
    20261017T214038108044-root-f768: no verdict (superseded by rework 20261017T215111184137-root-00cd (tier not recorded))
  judged by the user: 0 of 3 deliveries; without a verdict: 1 case(s) (20261017T214038108044-root-f768): never counted as accepted; hand-edited: 0
  escapes (the team reported done, then the user rejected it): none (0 of 3 judged deliveries)
  verifiers: none (every delivery was signed off by lead itself)
  runs per case (spend = runs used, plus runs still out while a case is open or blocked; approved: each task's own):
    20261017T214038108044-root-f768 "Competitor analysis of self-hosted note-taking apps" (lead): 0 (0.00x of 22); top-ups: +4 rework 20261017T215111184137-root-00cd (tier not recorded), +4 rework 20261017T215450859628-root-dfe0 (tier not recorded), +3 your grant 20261017T215533405230-root-7620
  alarms:
    repeat: does not apply (one-off tasks name no criterion ids)
    cost: n/a (0 of 3 judged cases)
```

**An empty organization; an ORG.md that does not parse; no git** (lines of the header and the timeline):
```
Quality of the work you asked for (derived from the files, nothing stored; for you and the user, never for agents).
Thresholds: the defaults (tunable): alarms need 3 judged cases; repeat: one id failing in 2 of the last 3 judged cases; cost: a case above 1.25x its approved budget.
ORG.md cannot be read (its settings block does not parse): the default thresholds are used.
No cases yet: you have requested no service and given no task.

Blocked tasks moved past without a verdict: none.
```

**`--json`, abbreviated (E3)**:
```json
{
  "thresholds": {"cost_ratio": 1.25, "min_judged": 3, "repeat_failures": 2, "repeat_window": 3, "source": "defaults"},
  "notes": [],
  "services": [{
    "owner": "lead", "service": "weekly-meeting-memo", "client": "root", "client_kind": "human", "unit": "case",
    "contract": 3, "playbook": 1, "budget": 15,
    "cases": [{"id": "20261021T152347923195-root-dd87", "state": "done", "stalled": false, "tasks": 2, "runs": 12, "spend": 12, "ratio": 0.8,
               "relayed_runs": 0, "credited": 0, "cut": false,
               "top_ups": {"granted": 0, "human": 6, "relayed": 0, "unrecorded": 0},
               "first": {"verdict": "reject", "tier": "human", "superseded_by": null}}],
    "deliveries": {"total": 6, "judged": 5, "superseded": 1, "without_verdict": [], "relayed_only": [], "hand_edited": [], "legacy_verdicts": 0},
    "escapes": [{"assertion": "R1", "case": "20261021T152347923195-root-dd87", "task": "20261021T152347923195-root-dd87", "signer": "lead/reviewer",
                 "cause": "contract-gap", "rule": "words", "detail": ["always"], "also": [], "before_verdict": "", "class": null}],
    "verifiers": [{"addr": "lead/reviewer", "judged": 5, "accepted": 3, "escapes": {"contract-gap": 2}, "rechecks": 2, "rework_runs": 2}],
    "alarms": {"repeat": {"state": "no", "judged": 3, "subjects": {"C11": 1, "R1": 1, "R2": 1}, "not_counted": {"R1": ["C6", "C3"]}},
               "cost": {"state": "no", "judged": 3, "cases": []}},
    "timeline": [{"kind": "contract", "when": "2026-10-21T15:27:53Z", "version": 2, "by": "root", "adds": ["C9", "C10"], "removes": ["C3", "C6"],
                  "basis": "legacy", "confirmed": []}],
    "history": {"known": false, "truncated": false}
  }],
  "one_off": null,
  "nested": [],
  "moved_past": []
}
```
`state` values: `fires`, `no`, `n/a`, `does not apply`. `ratio` is `null` when the approved budget is 0. `one_off` is `null` when root gave no
one-off task.

## 10. Health rebased on typed escapes (go/no-go section 3, F-E3-10)

The cause typing is built once, in `reflection`, and health reuses it through a consumer-owned port; health still may not import
`reflection` (graph 2.2), so the conversion lives in `app`.

- `SRC/health/_ports.py`: `class SignedDelivery(NamedTuple): signer: str; judged: bool; cause: str` (`""` unless an escape) and
  `class SignedDeliveries(Protocol): def deliveries(self, owner: str) -> Sequence[SignedDelivery]`. `EscapeCounts` gains
  `not_its: tuple[tuple[str, int], ...] = ()`.
- `SRC/app/_signed_deliveries.py:CaseSignedDeliveries(records: CaseRecords)` returns, for `owner`, every delivery of `records.deliveries(owner)`
  (the owner's services' cases and root's one-off cases assigned to it) as `SignedDelivery(d.signer, d.counted is not None, cause)`.
  `records.deliveries` computes deliveries and causes without reading deliverable folders (hand edits are a quality-view input only: 10, D7).
- `SRC/health/_escapes.py:MailEscapeCounter` gets `deliveries: SignedDeliveries` as its 5th collaborator and loses `_deliveries`; `counts(addr)`
  keeps today's composition (the owner's deliveries, plus the parent's deliveries `addr` signed off when the parent is not root) and:
  - `judged` = deliveries with `judged`, including relayed reworks' deliveries the client judged (F-E3-10: a client accept on a relayed rework
    counts as a judged delivery of its case) and one-off deliveries (0a's "until Phase 0b gives one-off tasks verdicts");
  - `escapes` = judged deliveries whose cause is `reviewer-miss` or `untyped` (the verifier's possible misses);
  - `not_its` = the others by cause: `contract-gap`, `relayed-error`, `relayed-carry-over`;
  - `rechecks`, `rework_runs`: unchanged.
- `SRC/health/api.py:AgentHealth` gains `not_its: dict[str, int] = field(default_factory=dict)`; `to_dict` carries it.
- Texts (`_analyzer.py`, `_render.py`): the `low_quality` reason and the report segment append, only when `not_its` is non-empty,
  ` (+{k} not its: {n} contract-gap, {m} relayed-error, {p} relayed-carry-over)` (zero parts left out) after `{escapes} of {judged} judged`.
  `max_escape_ratio` and `min_judged_for_quality` are unchanged. E3's reviewer reads `escapes 0 of 5 judged (+2 not its: 2 contract-gap)`
  where it read `escapes 2 of 4 judged`.
- Behaviour changes, named: escapes typed `contract-gap`, `relayed-error` or `relayed-carry-over` no longer count against a verifier; accepted
  relayed reworks and one-off deliveries now count as judged; deliveries of a retired service drop out (cases need a live contract, as in
  `services`), while a continued service keeps them (0a.2 5.10).

## 11. Ride-alongs (go/no-go section 3, followups item 3)

The go/no-go's stale-installed-skill item is already done (0a.1; `followups.md` "Status after 0a.1"), so it is not repeated here.

### 11.1 Show all plan checks up to 10 (F-E3-8)

`SRC/blueprint/_plan_texts.py:SHOWN_SERVICE_CRITERIA` goes from 5 to 10; `TextUserPlan._user_services` is unchanged (`... and {k} more (see the
details)` remains for more than 10). Goldens: the plan blocks with 6-10 criteria (about 9, go/no-go's estimate).

### 11.2 Health on typed escapes (F-E3-10)

Section 10.

### 11.3 Root reads results with `inbox`; one-off verdicts (SKILL.md, net 0 lines)

`skills/hirearchy/SKILL.md` stays at 125 lines (the cap is asserted in `skill/tests/test_finish_rules.py`, `test_observe_skill.py`,
`test_skill_org_growth.py`, `test_skill_services.py` and `TESTS/e2e/test_round7.py`):
- line 88 (step 5.1): `1. Read the final deliverable and check it yourself ...` becomes `1. Read the result with `inbox` (never with shell
  reads of the org's boxes), then the final deliverable, and check it yourself ...`, re-wrapped within lines 88-89;
- line 98 (step 5.6): `6. A service request: after the delivery ask ONE short question` becomes `6. A service request (a one-off task:
  record only a verdict the user states, no question, no criterion): after the delivery ask ONE short question`, re-wrapped within
  lines 98-100 by shortening `"keep it" / "what's wrong"` to `"keep it"/"what's wrong"` and joining one short line.
The planner measures both lines against the line-length rule the skill tests apply and records the result.

### 11.4 Owner prompt growth

Measured in the noise study from the run logs (section 20.4: lead prompt bytes and Reflect words per run). The 600-word Reflect cap stays in
Phase 1. No product change.

### 11.5 The flaky golden screen test (followups item 3; a plan item)

`SRC/dashboard/tests/test_golden_screens.py::test_a_screen_is_what_its_golden_says[given_queries-narrow-2-workflows]` failed once
under a full `check.sh` and passed alone and on a rerun. The plan item, done first in its FEAT and test-first:
1. Reproduce: run the module's capture of `narrow-2-workflows` (`_screens.demo_screens`) in a loop of at least 200 captures under CPU load (a
   second process spinning), and record every differing capture with its diff against the golden.
2. Find the source of the difference in the capture path (`_screens.py`, `_worlds.py`, `DashApp(queries, interval)`): a timer or a refresh that
   can land between mount and capture, a clock read, an unordered collection, or a worker that finishes after the snapshot.
3. Make the capture deterministic at that source: wait for the specific condition (the workers idle, the refresh done) before the screen is
   read, inject the fixed clock, or sort the collection. No retry, no `flaky` marker, no sleep, no regenerated golden.
4. Prove it: the loop of step 1 shows 0 differences, and a new test pins the waited-for condition. If no source is found after the loop, the
   item stops and reports to the manager with the evidence (it is not closed by a retry).

## 12. Packages, ports, wiring and files

No package is added and no dependency edge changes (`tests/architecture/graph.py` is untouched). ARCHITECTURE.md 2.2 row 31's sentence
becomes `Derives the history of the client's requests, with statistics, from the files.` (one-off tasks are not service requests; no "and"),
and its "reads" column gains the org's git history of `*/AGENT.md` and `ORG.md` through `BarHistory`.

### 12.1 `reflection`

- `api.py`: `Case` gains `credited: int = 0`, `relayed_runs: int = 0`, `top_ups: TopUps = TopUps()`, `cut: bool = False` (all defaulted);
  new frozen dataclasses `TopUps`, `Delivery`, `Cause`, `ContractMark`, `PlaybookMark`, `CharterMark`, `ModelMark`, `TopUpMark`, `ServiceRecord`,
  `RepeatAlarm`, `CostAlarm`, `QualityThresholds`; constants `CAUSES`, `FAILURE_CLASSES`, `LASTING_WORDS`, `QUALITY_DEFAULTS`; pure functions
  `signer_of`, `deliveries_of`, `unjudged_cases`, `judged_cases`, `cause_of`, `failure_class`, `repeat_alarm`, `cost_alarm`,
  `quality_thresholds(config) -> tuple[QualityThresholds, tuple[str, ...]]`; `CaseHistory.one_off_cases()` (3 -> 4 methods); the
  `DeliverableFinding` fields `written: int = 0`, `settled: bool = False`; `DeliverableChecks.findings(actor, service=None, *, settled=False)`.
- New Protocol `CaseRecords` (2 methods):
  ```python
  @runtime_checkable
  class CaseRecords(Protocol):
      def records(self, service: str | None = None) -> list[ServiceRecord]:
          """Root's view of the record: one per service of every agent (top-level first, then nested, each by owner and name; only those named
          ``service`` when given) and, without ``service``, one for root's one-off tasks (``service == ""``), with cases, deliveries (hand edits
          read from the deliverable folders), assertions, typed escapes and the timeline. ``OrgError`` for a ``service`` no agent offers."""
      def deliveries(self, owner: str) -> list[Delivery]:
          """Every delivery of ``owner``'s services' cases and of root's one-off cases assigned to ``owner``, with signer and cause, without reading
          any deliverable folder (health's input)."""
  ```
- `ServiceRecord` (frozen): `owner, service, client, client_kind, unit = "case", contract: int, playbook: int, budget: int, cases:
  tuple[Case, ...], deliveries: tuple[Delivery, ...], assertions: tuple[Assertion, ...], escapes: tuple[tuple[Delivery, Cause], ...], timeline:
  tuple[Mark, ...], history: BarChanges`.
- `Delivery` (frozen): `case: str, task: Message, result: Message, step: int, signer: str, verdicts: tuple[Verdict, ...]` (every tier, after the
  result, oldest first), `superseded: str = ""`, `edited_at: int = 0`; properties `counted: Verdict | None`, `voided: bool`, `escape: bool`.
- `_cases.py`: one private chain builder serves `cases` and `one_off_cases`; it fills the new fields from one `RunCounter.stamps` call per case.
- `_runs.py`: `LogRunCounter.stamps` (4.2); `runs_between` counts the uncredited stamps.
- `_ports.py`: `RunCounter.stamps`; `ContractVersions` (`versions(owner, name, kind)`, satisfied by `services.ServiceStore`); `BarHistory`
  (`changes(addrs) -> BarChanges`) and `BarChanges`.
- New modules: `_records.py` (`DerivedCaseRecords(history, catalog, agents, mail, versions, bars, deliverables)`), `_causes.py`,
  `_quality_rules.py` (deliveries, signers, unjudged, alarms, thresholds), `_marks.py` (contract and playbook marks).
- `_steps.py`: `feedback_step` for one-off verdict notes (8.2). `_deliverable_checks.py`: `settled`, `written`. `_evidence.py`: `_words_of`
  becomes `services.criterion_words` (no behaviour change).
- `testing.py`: `FixedCaseRecords`, `NoBarHistory`, `FixedBarHistory`; `IMPLEMENTATIONS[CaseRecords]`.

### 12.2 `services`

- `api.py`: `BASE_DELIVERED_HEADING = "## Base: the version the client judged"`, `BASE_LATEST_HEADING = "## Base: the current version"`
  (the literals of `_request.py`/`_texts.py` move here, byte-identical; `BASE_HEADING` stays); `criterion_words(line, criteria) -> str | None`;
  the `ServiceCommands.feedback` docstring (one-off tasks).
- `_feedback.py`: the one-off branch and the three refusals (8.1, 8.3).

### 12.3 `snapshots`

- `api.py`: `OrgHistory.changes(paths: Sequence[str], limit: int) -> list[Change] | None` (4 -> 5 methods) with
  `class Change(NamedTuple): commit: str; when: datetime; path: str`; `GitClient.log(root, paths, limit) -> bytes | None` (7 -> 8 methods,
  R7's maximum).
- `_git.py`: `log` runs `git --literal-pathspecs log -n {limit} --format=%x00%H%x09%cI --name-only -- <paths>` with `cwd=root`, the 2 s
  timeout and `None` on a non-zero exit, a timeout or `OSError`; paths that fail `is_history_path` are dropped before the call, and an empty
  list answers `[]` without running git. `GitOrgHistory.changes` parses each record (a 40- or 64-hex commit, an ISO time, the paths of the
  record that are among the asked ones); a record that does not parse is skipped.
- `testing.py`: the fakes gain `changes`.

### 12.4 `health`, `progress`, `mcp_server`, `cli`, `blueprint`

- `health`: section 10.
- `progress/api.py`: `QualityReport` Protocol (`quality_text`, `quality_data`). `_ports.py`: `FailCounts` (`fails(addr) -> tuple[int, int]`) and
  `ConfigSource` (`config() -> JsonObject`). New `_quality.py` (`DerivedQualityReport(records: CaseRecords, states: TaskStates, teams: TaskTeams,
  tasks: TaskQuery, mail: MailboxReader, budgets: BudgetQuery, agents: AgentDirectory, fails: FailCounts, config: ConfigSource)` and the pure
  `left_blocked`) and `_quality_render.py` (the text and the JSON; `ratio`). `testing.py`: `FixedQualityReport`.
- `mcp_server`: `_tools_quality.py` (new), the root `feedback` docstring (`_tools_services.py`), ROOT_INSTRUCTIONS line 7.
- `cli`: `QualityCommand` in `_commands_views.py`; the `feedback` help (`_commands_services.py`).
- `blueprint`: 11.1.

### 12.5 `app`

- Fields: `case_records: CaseRecords` (`fields_reflection.py`), `quality_report: QualityReport` (`fields_progress.py`); ARCHITECTURE section 3
  lists both Protocols, so `app/tests/test_runtime_fields.py` requires them.
- Adapters (new): `_bar_history.py:GitBarHistory(history: OrgHistory, clock: Clock)`; `_signed_deliveries.py:CaseSignedDeliveries(records)`;
  `_fail_counts.py:HealthFailCounts(counter: EscapeCounter)` (`fails(addr)` = `(counts.rechecks, counts.rework_runs)`);
  `_readable_config.py:ReadableOrgConfig(settings: OrgSettings)` (`config()` = `settings.readable_config(settings)`, which raises
  `OrgError(UNREADABLE)` for an ORG.md that does not parse).
- Wiring: `wire_reflection.py` (`DerivedCaseRecords`), `wire_health.py` (the 5th collaborator), `wire_progress.py` (`DerivedQualityReport`),
  `wire_mcp_server.py` (`QualityTools` in `root_only` after `ProgressTools`), `wire_cli.py` (`QualityCommand`).

### 12.6 Single writer and stored state

Nothing in 0b writes a file of an organization except the one-off verdict note, which `mail` stores through `dispatch.RuleMessageSender`
like every verdict note (2.3 unchanged). `quality`, `health` and the timeline only read. `tests/architecture/ownership.py` is unchanged.

## 13. Error handling (per operation)

| Operation | Failure | Recoverable? | Caller receives | Logged |
|---|---|---|---|---|
| `quality` (MCP) in setup mode | no org bound | yes | `SetupMode.state()` text | tool call recorded (`ToolRecorder`), no extra log |
| `quality(service=x)` | no agent offers `x` | yes | `OrgError`: `no service named `{x}`: the services are {names or "none"}. Call quality() without a service for everything.` | tool call event with the error, as for every tool |
| `quality(service=x)` | `x` longer than 80 characters or not a string | yes | `OrgError`: `service is a service name (at most 80 characters): {clipped}` | same |
| reading a service's record | `OrgError`/`OSError` from the catalog, the store or a mailbox | yes (other services render) | that block becomes `{service} (offered by {owner}): cannot be read ({error}).`; the rest renders | no extra log |
| reading root's one-off record | same | yes | `One-off tasks you gave: cannot be read ({error}).` | no |
| thresholds | ORG.md does not parse (`OrgError(UNREADABLE)` from `ReadableOrgConfig`) | yes | defaults and the note of section 6 | no |
| thresholds | a `quality:` value fails validation | yes | its default and the note | no |
| stalled states, held runs, FAIL counts | `OrgError`/`OSError` from `TaskStates`, `BudgetQuery`, `FailCounts` | yes | the part reads `unknown ({error})` (`stalled unknown`, `holds an unknown number of runs`, `its FAILs before delivery: unknown`) | no |
| hand edits | the deliverable checks never raise for a folder, file or history (0a.2 6.3); a catalog or mailbox error | yes | `hand-edited: unknown ({error})` | no |
| timeline git reads | no repository, no git, a timeout, the bound | yes | `known=False` (the unknown line) or `truncated` | no (git errors are never raised: `OrgHistory`'s rule) |
| CLI `quality` | as above; no organization found | yes | the text, or the CLI's existing "no organization" error and exit code | the CLI's own handling |
| one-off `feedback` | 8.3's refusals, the existing validation | yes | `OrgError` with the text; nothing written | tool call event |
| one-off `feedback` | the note's delivery fails (`OSError`) | yes (retry) | the error; the pipeline writes the file last and atomically, so nothing half-written | as today |
| health `counts` | `CaseRecords.deliveries` raises `OrgError`/`OSError` | as today (health already raises on an unreadable mailbox) | the error propagates to the health caller | as today |
| `OrgHistory.changes` | anything | n/a | `None` or `[]`, never raises | no |

Errors are never swallowed silently: each one becomes visible text in the part it affects, with the error's words (`clip_line(str(exc), 200)`).

## 14. Validation of external inputs

| Input | Required | Type and limits | On failure |
|---|---|---|---|
| MCP `quality.service` | optional | `str`, stripped, 1-80 characters; empty means none | `OrgError` (13) |
| CLI `quality [service]` | optional | as MCP | the same text, exit code as other CLI errors |
| CLI `--json` | optional | flag | argparse |
| ORG.md `quality:` | optional | mapping | not a mapping: ignored, note |
| `quality.min_judged` | optional | integer >= 1 (an integral float or numeric string counts, booleans do not) | default 3, note |
| `quality.repeat_window` | optional | integer >= 1 | default 3, note |
| `quality.repeat_failures` | optional | integer, 1 <= value <= `repeat_window` (after `repeat_window` is settled) | default 2 (clamped to the window when the window is smaller), note |
| `quality.cost_ratio` | optional | finite number > 0 | default 1.25, note |
| `feedback(task_id)` for a one-off | required | root's sent task without `service`, with a result | ONE-OFF-UNKNOWN / today's "no result yet" |
| `feedback(verdict, note)` | required / required for reject | `accept`/`reject`; note at most 1000 characters | today's texts |
| `feedback(criterion, confirms)` on a one-off | must be absent | - | ONE-OFF-NO-LINK |
| `feedback(source)` | optional | `human` or `relayed` (`provenance_source`, S2) | today's text |
| message files, contract and playbook versions | read only | the existing parsers; an unreadable message is left out by the index (unchanged) | - |
| git output | read only | records that do not parse are skipped; paths are validated before the call (`is_history_path`) | - |

## 15. Invariants and their owners

| # | Invariant | Owner | Why that layer |
|---|---|---|---|
| I1 | No count reads team-written or relayed text as client evidence | `reflection`'s pure rules (`deliveries_of`, `cause_of`, `repeat_alarm`, `judged_cases`) filter on `verdict_tier(m) == "human"` and human-tier links | one place derives every case for `quality`, health and `services`; `progress` and health only render or compose |
| I2 | No new stored state | the architecture tests (`ownership.py` unchanged) and a test that runs `quality` and `health` over an fs world and asserts the org tree byte-identical before and after | storage rules are enforced where every writer is listed |
| I3 | A zero denominator is never a pass | `progress._quality_render.ratio` and the alarm states (`n/a`) | the renderer is the only place rates become text |
| I4 | One spend function | `reflection.case_spend`, called by `case_total` and `cost_alarm` (a test asserts equal spend on the same case) | 0a.1 put it in reflection for this purpose |
| I5 | One cause typing | `reflection.cause_of`, read by `quality` directly and by health through `CaseSignedDeliveries` (a test compares health's `not_its` with the record's causes on one world) | health may not import reflection; the adapter only converts |
| I6 | One-off verdicts default to `relayed` | `dispatch.provenance_source` (existing) and MCP root `feedback`'s default | the sender is the single layer every write passes |
| I7 | `quality` is root's only | `mcp_server` (`root_only` group) and the surface goldens | the factory decides each identity's tools |
| I8 | Agent-written text never enters root's view verbatim | `progress._quality_render` (only root's titles and human-tier words are quoted; paths and model names through `shown_name`; evidence ids filtered) | the renderer is the boundary between files and root's prompt |
| I9 | The core is domain-agnostic | `reflection.api` vocabularies; a needle test over the new modules forbids domain words (`memo`, `meeting`, `code`, `test`, `pull request`, `ticket`, `research`) outside tests | the vocabularies are the extension points packs replace |

## 16. Zero denominators, empty cases, ORG.md and git

- **Rates**: judged coverage, PASS precision and every `k of n` use `ratio`; with `n == 0` they read `n/a (0 of 0)`. A ratio of spend to a 0
  budget reads `n/a (budget 0)` and the case is named in the cost line.
- **Alarms** below `min_judged` judged cases read `n/a ({k} of {min} judged cases)`, never `no`; `no` needs the evaluation to have run.
- **A service with no request**: `cases: 0 (...)`; every line after it reads `none` or `n/a (0 of 0)`; alarms `n/a (0 of 3 judged cases)`.
- **No service and no one-off task**: the empty sample of 9.3; root's one-off block is left out when root gave none (`One-off tasks you gave:
  none.` when a service exists).
- **An assignee that no longer exists**: its one-off cases count 0 runs and say `(assignee retired: runs not counted)`.
- **ORG.md that does not parse**: section 6's defaults and note; every other count still renders (none reads ORG.md, and the auxiliary parts
  degrade per section 13).
- **No git history** (no repository, git missing): the timeline's contract, playbook and top-up marks still render (they come from
  `history/` files and mailboxes); charter and model marks read `unknown (...)`; hand edits are compared with the team's current files, which
  is 0a.2 P3's no-history rule, and the view adds `hand edits compared with the team's current files (no org history)`.

## 17. The four review checks, and how each passes

1. **Zero denominators and empty cases.** Every rate goes through `ratio` (`n/a (0 of 0)`); alarms below the minimum read `n/a (k of 3
   judged cases)` and never `no`; a 0 budget reads `n/a (budget 0)`; an empty service, an empty org and a corpus without run logs each have a
   defined text (16, 9.3). Tests: a parametrized renderer test over every rate with `n == 0`; alarm tests at 0, 1 and 2 judged cases; the empty
   sample as a golden.
2. **No count reads team-written or relayed text as client evidence.** Section 4 lists each count with its tier filter: verdicts count only at
   `human` tier; links count only from human-tier link notes (`Verdict.confirmed`, `links_tier == "human"`); the rejection's own `criterion`
   (root's reading) is relayed and only listed as `not counted`; lessons, playbook text, review reports and results are never read for a
   count, except the artifact lists (`## Artifacts`), which the carry-over rule reads only to compare two of the team's own deliveries, never
   as client evidence; agent-client verdicts are counted apart and never alarm. Tests: for each count, a world with the same events stamped
   `relayed` and `agent` gives 0 human-tier counts; a lesson that says "the client wants X" changes nothing.
3. **Every count is derivable from existing files, with no new stored state.** Section 4 names the files of every count; 12.6 and I2: no
   writer is added and the org tree is byte-identical before and after `quality` and `health` (test). The only new write is the one-off verdict
   note, an existing file kind through the existing writer.
4. **Domain-agnostic core.** The vocabulary is cases, deliveries, tiers, client kind, unit, failure classes and causes (4.6, 5); the rules read
   message fields, contract versions, artifact lists and base headings, all generic; `LASTING_WORDS` are English words, not domain terms (a pack
   may add others in Phase 3). I9's needle test fails on a domain word in the new modules. The samples' memo titles are data.

## 18. Testability and the test plan

### 18.1 Unit tests (pure functions and fakes)

- `reflection`: `deliveries_of` (superseded, voided by an edit before and after the verdict, verdicts on blocked results), `signer_of` (moved
  tests from health), `unjudged_cases`, `judged_cases`, `cause_of` (one test per rule, every precedence pair, `also`, `before_verdict`, legacy
  reworks, a `none` link, a "same as R<j>" link resolved), `failure_class`, `repeat_alarm` (window, subjects, unconfirmed links, one-off),
  `cost_alarm` (threshold edge `==`, 0 budget, open and blocked spend), `quality_thresholds` (each validation rule), the playbook mark counts
  (P1's own replays as fixtures), the one-off chain builder, `RunCounter.stamps` (credited stems, boundaries of the relayed interval).
- `progress`: `ratio`; the renderer over `FixedCaseRecords` (every line, limits, `shown_name` on paths); `left_blocked` (mail.moved_past
  released, superseded, verdict after the block, a later task inside the chain).
- `services`: the one-off branch and its three refusals; `criterion_words` (P1's tests keep passing).
- `snapshots`: `GitOrgHistory.changes` parsing (sha1 and sha256 ids, a malformed record, invalid paths dropped, no repository).
- `health`: `MailEscapeCounter` over a fake `SignedDeliveries` (counted and not counted causes, F-E3-10's relayed accept, one-off deliveries).

### 18.2 Contract, integration and e2e tests

- Contract suites (R8): `test_contract_case_records.py` (reflection; `DerivedCaseRecords` over the fs world and `FixedCaseRecords`),
  `test_contract_quality_report.py` (progress), the `OrgHistory` suite extended with `changes`, the `DeliverableChecks` suite extended with
  `settled`.
- Integration (fs world, in-process MCP and CLI): one-off `feedback` through MCP root, CLI and `Org.feedback` (relayed default, human, the
  refusals, the reply steps); `quality` through MCP root (absent for agents: the surface goldens) and the CLI (`--json` keys); health's text
  and JSON with `not_its`; ORG.md that does not parse; an org that is a git repository with a charter edit and a model change (the timeline
  marks), and the same org without `.git`.
- e2e: the replays of section 19 (`TESTS/e2e/test_org_growth_0b_replays.py`) and the published-count cost checks
  (`TESTS/e2e/test_org_growth_0b_costs.py`).
- What stays manual: nothing in the product; the noise study (section 20) is a study.

### 18.3 Test policy (the owner's, binding from the first commit)

The owner's rule ("scope tests to verify changes and run all of them only in the end after everything is integrated") applies as written in
`docs/research/org-growth/phase-0a2/test-policy.md`: per commit a FAST scoped run (the commit's targets, `tests/golden`,
`tests/architecture` without the static-checks test, `src/hirearchy/app/tests` only when the commit touches `app/`, an `api.py` Protocol or
the wiring, and `scripts/static_checks.py all`); per FEAT one SCOPED run (the union of the FEAT's targets plus `tests/e2e`, `tests/golden`,
`tests/architecture`, `src/hirearchy/app/tests`); no full suite during development; one `scripts/check.sh` on the integrated, rebased branch in
the final validation. A flake in a scoped run is re-run once as one file and noted; the flaky golden screen test is fixed, not retried (11.5).

## 19. Exit-check replays (deterministic; "alarms checked on replayed E/E2/A5 files", plus E3 and E4)

### 19.1 The replay kit (`TESTS/testkit/org_replay.py`, test-only)

`materialize(corpus, root) -> Path` builds an organization directory from a corpus's kept files, read-only from the repository
(`testkit.REPO / "studies" / ...`):
- ORG.md: the corpus's kept ORG.md.
- Messages: every kept message file is parsed with `kernel.split_frontmatter` and written byte-identical to its sender's `sent/<id>.md` and its
  recipient's `read/<id>.md` (root's boxes at the org root). The same id kept twice must be byte-identical, else the test fails.
- Charters: the kept AGENT.md for an address when the corpus has one, else a minimal charter (frontmatter `name` only) for every address the
  messages name; no count reads a charter.
- Contract and playbook versions: placed by their frontmatter `version` into `history/` and the current file. The contract's
  `deliverable.path` is rewritten to the replay's deliverable folder when the corpus kept deliverables (E4), else to a missing folder under the
  replay root (P3 then finds nothing). This edit of the materialized copy is the only change to a kept record, and the kit's docstring says so.
- Run logs (E3, E4): `run-logs/<folder>/<stem>.log` into `<addr>/runs/` (`lead-checker` -> `lead/checker`, `lead-writer` -> `lead/writer`, ...).
- Deliverables (E4): `memos/<name>.md` into the deliverable folder, with the mtime of its last write in `deliverables-log.txt`; the team's files:
  for each path in `memos/versions/INDEX.txt`, the newest version's bytes at that org path.
- No git repository: every replay runs on the no-history path.
A listed file that is missing, or a message that does not parse, fails the test (never a skip). `TESTS/meta/test_org_replay_kit.py` tests the
kit (address mapping, duplicate check, deliverable rewrite, mtimes).

### 19.2 What each corpus kept, and what is computable from it

| Corpus (`ST/<name>/evidence/`) | Kept | Not kept |
|---|---|---|
| E (`E-service-reflection`) | the sent boxes `msgs/{root,lead,writer,reviewer}-sent/`; `service/SERVICE.v1.md`, `v2`, `v3-current`; `playbook/PLAYBOOK.v1.md`, `v2`, `v3-current`; `org-files/ORG.md`, `lead-AGENT.md`, `reviewer-AGENT-final.md`; `run-counts.txt` (totals per agent) | run logs, received boxes (rebuilt from the sent copies), the writer's charter, the deliverable folder, git |
| E2 (`E2-service-reflection-regression`) | the same layout; `run-counts.txt` with the per-chain counts | run logs, the deliverable folder, git |
| A5 (`A5-research-final3`) | `msgs/sent__*.md` (root's 4), `msgs/lead_sent__*.md` (the lead's 14), `charters/`, `ORG.md`, `run-counts.txt` (per agent) | the reports' boxes, run logs, git |
| E3 (`E3-org-growth-0a-live`) | every box of root, lead, lead/reviewer, lead/writer under `msgs/`; `run-logs/` (41); `service/SERVICE.v1.md`, `v2`, `current`; `playbook/PLAYBOOK.current-v1.md`; `org-files/` (ORG.md, charters) | git (`observe-traces.txt` and logs only), the deliverable folder as such |
| E4 s1r, s2r, s3 (`E4-org-growth-0a1-recheck/<s>/`) | every box under `msgs/`; `run-logs/`; `service/` and `playbook/` (`history--*`, `current-*`); `org-files/`; `memos/`, `memos/versions/` (with `INDEX.txt`), `deliverables-log.txt` | git (`org-git-log.txt` is a text log), run credits (they did not exist yet) |

| Count | E | E2 | A5 | E3 | E4 |
|---|---|---|---|---|---|
| cases, deliveries, first deliveries, judged, without a verdict | yes | yes | yes (one-off) | yes | yes |
| tiers | all legacy (no `source`: human, 0a 3.1) | all legacy | no verdicts | yes | yes |
| signers | yes | yes | the lead only (no report's box kept) | yes | yes |
| causes | the relayed rules cannot fire (reworks' `source` never recorded) | same | none to type | yes | yes |
| runs, spend, relayed runs | no (no logs: the view reads 0) | no | no | yes | yes (credits: none existed) |
| cost alarm | by published counts (19.4) | by published counts | by published counts | yes | yes |
| repeat alarm | yes | yes | does not apply | yes | yes |
| top-ups | yes | yes | yes | yes | yes |
| contract and playbook marks | yes | yes | n/a | yes | yes |
| charter and model marks | no (no git) | no | no | no | no |
| hand edits | no (no folder) | no | no | no | yes (current-file rule) |
| moved past, held runs | moved past yes; held no (budget needs the logs) | same | same | yes | yes |

### 19.3 Pre-registered expectations (one test per id)

**E**
- E-1: one record `weekly-memo` (lead; client root, human); 3 cases; 3 deliveries; judged 2 of 3; first deliveries 1 accepted
  (`...-root-b495`), 0 rejected, 1 without a verdict (`...-root-c686`, superseded by rework `...-root-5bae`, tier not recorded), 1 never delivered
  (`...-root-2c75`, blocked); 1 verdict on a blocked result (`...-root-86de`); 0 cases without a verdict; 0 escapes; 3 legacy verdicts.
- E-2: repeat `no` (3 judged cases, nothing counted); cost `no` in the view with 0 runs in every case (no run log kept), asserted together
  with the corpus note in the test's docstring.
- E-3: top-ups of `...-root-c686`: +5 rework `...-root-5bae` (tier not recorded), +3 and +1 grants (`...-root-c1c5`, `...-root-f2a7`).
- E-4: timeline: contract v2 and v3 `not confirmed`; playbook v2 and v3 `no admission recorded (written before the evidence gate)`; charter
  and model marks unknown.
- E-5: no block moved past (`...-root-2c75`'s block was followed by the user's accept: `mail.moved_past`).

**E2**
- E2-1: one record `meeting-memo`; 3 cases; 6 deliveries; judged 5 of 6; first deliveries 1 accepted (`...-root-55ff`), 1 rejected
  (`...-root-e29b`), 1 without a verdict (`...-root-d22b`, superseded by rework `...-root-d90e`, tier not recorded); 0 without a verdict;
  5 legacy verdicts.
- E2-2: 2 escapes, both `untyped`: R1 on `...-root-d90e` (the assistant's own rework, whose `source` was never recorded, so `relayed-error`
  cannot fire on these files) and R2 on `...-root-e29b` (the Marta row); no link exists and no lasting word occurs.
- E2-3: repeat `no` (3 judged cases, nothing confirmed).
- E2-4: health on these files: lead/reviewer judged 5, escapes 2 (untyped, counted), not flagged (0.4 is not above 0.5), as 0a 5.5 predicted.
- E2-5: timeline: contract v2 and v3 not confirmed; playbook v2 (lead) and v3 with no admission recorded.

**A5**
- A5-1: no service record; the one-off record has 1 case (`...-root-f768`, tasks `...-00cd` and `...-dfe0`, both reworks with the tier not
  recorded); 3 deliveries; judged 0 of 3; 1 case without a verdict (`...-root-f768`), never counted as accepted; escapes `none`.
- A5-2: repeat `does not apply`; cost `n/a (0 of 3 judged cases)`; top-ups +4, +4 (tier not recorded) and +3 (grant `...-root-7620`); runs 0
  (no log kept).
- A5-3: every delivery is signed off by `lead` (the reports' boxes were not kept).

**E3** (go/no-go item 8)
- E3-1: 0 cost alarms: spends 12, 15 and 14 of 15; cost `no (0 of 3 cases above 1.25x)`.
- E3-2: R1's unconfirmed link (C6, C3, the rejection's own `criterion`) is not counted by the repeat alarm and is listed as `not counted`.
- E3-3: the superseded `...-root-248f` is not counted as a block moved past; the section is `none`.
- E3-4: contract-gap rejects are not shown as verifier escapes: R1 `contract-gap` (words, "always"), R2 `contract-gap` (answer, link
  `...-root-8ca0` names C11, not in contract v2); health: lead/reviewer `escapes 0 of 5 judged (+2 not its: 2 contract-gap)`, not flagged.
- E3-5: the text of 9.3's E3 sample equals the output byte for byte (a golden of the replay).
- E3-6: case `...-root-207b` has 10 runs in relayed reworks.

**E4** (the gate's item 8, then 0b's own)
- S2R-1: s2r's playbook v2 is shown with content beyond C9: its mark reads `admitted (c) on R1, C9` with at least 2 lines beyond a criterion's
  own words (the two vague-deadline lines the gate quotes).
- S1R-1: s1r's four unconfirmed amendments are not counted as client evidence: every criterion v2-v5 added except C9 is marked `not
  confirmed`; none is a repeat subject or a contract-gap answer; C9 is confirmed by link `...-root-1753` (0a.1's rule for a version without
  `answers`).
- S1R-2: s1r's unrecorded rejects 2 and 3 are shown as missing verdicts: cases `...-root-114d` and `...-root-2efa` are without a verdict and
  never counted as accepted; judged 1 of 3.
- S2R-2: s2r's Marta escape is typed as a relayed carry-over: R2 (`...-root-f6dc` on `...-root-342a`) is `relayed-carry-over` through
  `...-root-43b8` and `lead/writer/work/2026-10-05-memo.md`, `also contract-gap`.
- S1R-3: s1r's 16 runs are shown as held behind blocks the conversation moved past: lead holds 12 (task `...-root-3559`), lead/writer holds 4
  (three tasks from lead).
- S1R-4: the three final memos are hand-edited (they differ from the team's current files); R1 (recorded 18:59:00) predates the last write of
  `memo-2026-10-05.md` (19:12:45) and stays an escape; the deliveries of `...-114d` and `...-2efa` count as neither pass nor escape.
- S1R-5: R1 is `contract-gap` (answer: link `...-root-1753` names C9, not in contract v1), signed off by lead/checker; case `...-root-ed94`
  spends 25 of 15 (1.67x), 5 of its 23 runs in relayed rework `...-root-9ce9`; repeat and cost `n/a (1 of 3 judged cases)`.
- S2R-3: R1 (`...-root-a9fd`) is `contract-gap` (answer, C9) with `before_verdict` `...-root-43b8`; case `...-root-f230` spends 19 of 15
  (1.27x), 5 in relayed rework; alarms `n/a (1 of 3)`; hand-edited 0; health: lead/reviewer escapes 0 (+1 contract-gap, +1
  relayed-carry-over).
- S3-1: the cost alarm fires on case `...-root-88b2` only: 21 of 15 (1.40x), 5 in relayed rework `...-root-fe20`; `...-root-cdef` spends 10
  (0.67x, 5 relayed), `...-root-6947` 15 (1.00x).
- S3-2: R1 (`...-root-ac19` on `...-root-4510`) is `contract-gap` (answer: link `...-root-1fb7` names C8, not in contract v1), with
  `before_verdict` `...-root-fe20`; repeat `no` (3 judged cases; C8 once).
- S3-3: first deliveries 0 accepted, 0 rejected, 3 without a verdict, all superseded (`...-88b2` by human rework `...-4510`, `...-cdef` by relayed
  rework `...-116b`, `...-6947` by human rework `...-3286`); hand-edited 0.
- S3-4: the user's accept on relayed rework `...-root-116b` counts as a judged delivery (F-E3-10); lead/reviewer has no escape counted
  against it (+1 contract-gap).
- E4-all: no charter or model mark (no git): the unknown line in every block.

### 19.4 The cost alarm on corpora without run logs (`TESTS/e2e/test_org_growth_0b_costs.py`)

E, E2 and A5 kept no run log, so their spend is checked with `cost_alarm` over `Case` values that carry the published run counts (their
docstrings cite the source lines):
- E (`STUDY.md` focus item (c): "R1 8 of 12; R2 17 (12 + 5 rework + 3 + 1 granted = 21 handed out); R3 10 of 12"): fires on R2 only (17 >
  15, 1.42x); R3 (blocked, 10 used, 2 still out) spends 12.
- E2 (`evidence/run-counts.txt`: "R1 first pass 9, rework1 5, rework2 5 = 19; R2 5; R3 first pass 6, rework 5 = 11"): fires on R1 only (19 >
  18.75, 1.27x).
- A5 (`evidence/run-counts.txt`: lead 13, researcher 1, writer 4, factcheck 4 = 22, approved 22): does not fire (1.00x); and with 0 judged
  cases the alarm is `n/a`.

### 19.5 E5, by amendment (a plan item)

When `ST/E5-org-growth-0a2-recheck/` exists, its streams join the replays: the planner adds E5's manifest to the kit and, before any E5 replay
test is written, an amendment to this section pre-registers E5's expectations from its gate document and evidence (at least: every
`answers` amendment marked confirmed with its link, the base sections' effect on the carry-over rule, the P3 notes against the hand-edit
counts, and the `run credit` notes against the credited counts). No E5 expectation is invented before its evidence exists.

## 20. The noise study (study G0): protocol and harness

### 20.1 Purpose and design

G0 measures how much the same input varies across repeated runs, so later studies can tell a change from noise (go/no-go item 7; the gate's
item 7). It repeats E5's pre-registered script unchanged (Lena's lines, the three memos, the facilitator's injected relayed rework of memo 1,
the answer key), because that is the newest validated script and E5's results are then the first point inside or outside the band. It has
no pass rule: it reports values and their spread.

- **Runtime**: the V3 runtime for every seat (the assistant with `kiro-cli chat --v3`; org runs through the product's V3 launcher), with
  amendment 1's A3 patterns for every transcript and event extraction (`ST/E4-org-growth-0a1-recheck/evidence/protocol-amendment-1.md`).
- **Models**: every seat claude-sonnet-5.5 at `--effort high` (D-E4-8, D-E4-9): the assistant set by the harness, the org agents by the
  product's floor (ORG.md effort `high`). The harness checks `--model` and `--effort` in every run log and in the assistant's invocation; a
  seat outside the set invalidates the stream; no substitution; if claude-sonnet-5.5 is not listed when a stream starts, it does not start and
  the manager is told.
- **Arms (controlled)**: memory presence. M0: the assistant runs in a dedicated HOME prepared by the setup step whose kiro settings are copies
  without the memories index; M1: the owner's ambient kiro memories as they are, recorded by md5 and index listing. The owner's real
  `~/.kiro` is never modified (md5 before and after); if a dedicated HOME cannot authenticate, the study stops and asks the manager.
- **Stratifier (observed)**: skill activation: whether the assistant called `disclose_context` for the hirearchy skill before its first
  `propose_org` or `feedback` (the product steers it through ROOT_INSTRUCTIONS; forcing it would test another product).
- **Repeats**: k >= 3 valid streams per arm, so at least 6 streams. k = 3 is a floor that gives a range, not a rate (the gate's item 7).
  Every cell of arm x skill stratum with fewer than 3 streams reports its values and `n/a (k of 3)` for its spread.
- **Validity**: E4's H8 rule and 0a.2's throttle rule (a credited run is not charged and is retried once) as in E5; an invalid stream is
  replaced once per arm with the manager's approval, recorded before it starts.

### 20.2 What the product provides, what the harness provides

| Need | Product (0b and before) | Study harness (`ST/G0-noise-baseline/evidence/harness/`) |
|---|---|---|
| the org, tools, scheduler, run logs with prompts (`# ---- prompt ----`), events | yes | - |
| per-stream counts: cases, deliveries, verdicts, escapes and causes, without a verdict, hand edits, moved-past blocks, relayed and credited runs, alarms, timeline | `hirearchy quality --json` at the end of each stream (and after each turn, for the turn table) | records it; re-derives the same counts from the raw files independently and reports every mismatch as a product defect |
| deliverable notes, `progress` flags, refusals | yes (0a.2) | counts them from turn files |
| repeats, arms, HOME preparation, model and effort checks, Lena's turn driver, injection | - | `run_arm.sh <arm> <k>` over E5's `run_turn.sh`, `inject_root_rework.py` (with F-E4-9's fixed polling loop), `model_check.sh`, `ambient_context.py` |
| assistant-layer measures | - | `extract_mechanical.py` (E5's, with A3 patterns) extended for 20.4 B |
| answer-key scoring, reviewer ambiguity recall, prompt growth | - | `score_memos.py`, `ambiguity_recall.py`, `prompt_sizes.py` |
| the baseline table | - | `aggregate.py` -> `baseline.md` |

The harness is study code, built by the study's setup step from E5's harness (copied with md5s recorded), not product code. Before the first
stream it must re-derive E5's published counts from E5's raw evidence (a self-check); a mismatch stops the study.

### 20.3 Procedure per stream

Setup as E5 (sandbox, workspace skill copy with md5, settings md5, safety snapshot before), the arm's HOME, then E5's turns verbatim, the
injection as E5's protocol places it, `quality --json` after each turn and at the end, the copy of the org evidence, safety snapshot after.
The streams of the two arms are interleaved (M0, M1, M0, ...) so that time-of-day and service load do not line up with an arm.

### 20.4 Measures (per stream; then per arm and per skill stratum: every value, min, median, max; binary ones as `k of n`)

A. **Team layer**: per delivered memo version the answer-key score (decisions n/8, action items n/15, wrong dates, extra rows, Summary
   first); reviewer verdicts (PASS/FAIL, `criteria met n of m`); **reviewer ambiguity recall** (D-E4-5, verbatim from E5's definition): over
   every reviewed version that contains an answer-key item that fits a criterion's words but not its purpose (the Marta row of memo 3 and every
   item the key marks so), the number the reviewer listed as `ambiguous` on its first review of that version, `k of n` per stream and pooled,
   `n/a (0 of 0)` when none was reviewed, plus whether the lead forwarded it and whether `progress` flagged it; runs per case;
   `revise_playbook` attempts, refusals and admissions; **owner prompt growth**: the lead's prompt bytes per run (first, max, last, and last
   minus first) and the words of each Reflect section (max), with E3's 20.2 KB -> 29.9 KB and 452-679 words as the reference.
B. **Assistant layer**: skill activation; per human reject, exactly one yes/no item naming an id before any `define_service`; every flagged
   item asked before delivery (D-E4-5's restated clause 3); relayed reworks sent and how many the user asked for; hand edits and whether a
   human-tier verdict followed; verdict recording (delivered versions the user saw against verdicts recorded); results read with `inbox`
   against shell reads, and root's unread count at the end; P2 and P4 refusals met.
C. **Product layer**: every count of `quality --json`, and the harness's re-derivation; the alarms that fired, each checked against the raw
   files.

### 20.5 Output and use

`baseline.md`: one table per layer, rows = measures, columns = streams grouped by arm and stratum, then min/median/max (or `k of n`); a zero
denominator is `n/a (0 of 0)`. A later study on the same script reads a value inside the band as indistinguishable from noise at this k; no
test of significance is made. The baseline is the "noise baseline measured" half of the exit criterion; the replays of section 19 are the
other half.

### 20.6 Cost

About 40-50 org runs and 12 user turns per stream (E4 s1r: 39 org runs, 12 turns), so about 300 org runs plus the assistant sessions for 6
streams. The number of streams is an open question for the owner (Q3).

## 21. What the 0b study must check (pre-registration input)

- **Deterministic part**: at the study's commit, `TESTS/e2e/test_org_growth_0b_replays.py` and `test_org_growth_0b_costs.py` pass, every
  expectation of 19.3 and 19.4 included; the output is kept verbatim.
- **Model set and effort**: every seat claude-sonnet-5.5 at effort high, checked per run log and for the assistant; a seat outside the set
  invalidates the stream (20.1).
- **Runtime**: V3 everywhere; A3 patterns; every org run's `# cwd:` and model lines checked.
- **Arms and strata**: k >= 3 valid streams per memory arm; skill activation recorded per stream before any score is read; cells under 3
  streams reported as such.
- **The view is right on live files**: for every stream, every count of `quality --json` equals the harness's re-derivation from the raw files;
  each mismatch is listed with the files that show it.
- **Alarms live**: every alarm that fired is listed with its cases and checked by hand against the raw files; every repeat subject is a
  human-tier link (no relayed reading among them); every cost alarm's spend equals the case's charged runs plus the runs still out.
- **Causes live**: every escape's cause is re-typed by hand from the raw files by the rules of section 5, and disagreements are reported.
- **Reviewer ambiguity recall** and **owner prompt growth**: as 20.4, per stream and pooled.
- **Assistant layer**: as 20.4 B, per stream.
- **One-off verdicts**: E5's script has no one-off task; if a stream contains one, report its verdicts' tiers and whether the words were the
  user's (turn files). Otherwise the one-off path is covered deterministically only (A5 and section 18).
- **Throttle**: credited runs (`run credit <addr>@<stem>` notes, `kernel.RUN_CREDIT_TITLE`; the brief's and E5's "`Run not charged:`" wording is
  the 0a.2 design draft's, A.6) equal the quality view's `credited` per case.
- **Safety**: snapshots before and after; the owner's `~/.kiro` and the dedicated HOME's md5s; no org outside the sandbox touched.
- Every rate is `k of n`; a zero denominator is `n/a (0 of 0)`, never a pass. The study has no pass rule.

## 22. Golden impact (estimate; every regenerated file is named with its line count in its commit)

| Area | Files (estimate) | Why |
|---|---|---|
| MCP surfaces | `tests/golden/expected/mcp/surface_root.txt`, `surface_root_unbound.txt`, `surface_root_setup_mode.txt` (3) | the `quality` tool, the root `feedback` docstring, ROOT_INSTRUCTIONS line 7 |
| CLI help | the top-level help, `help_quality.txt` (new), `help_feedback.txt` (both copies) (about 4) | new command, feedback help |
| plan blocks | about 9 | 11.1 |
| health | text and JSON goldens of scenarios with judged deliveries (about 5-15); every health JSON golden gains `not_its` | section 10 |
| dashdata / dashboard | 0 expected (the dashboard does not render `not_its`); any dashdata snapshot that embeds `AgentHealth` JSON changes (checked by the planner) | `to_dict` |
| replays | new goldens for 9.3's samples (E3 full, the empty org) | 19.3 E3-5 |
| prompts, ORG.md, charters | 0 | agents see nothing new |
Total: about 20-35 regenerated, plus the new ones. Each diff is reviewed and counted in the phase report (08 D1).

## 23. Plan items for the planner, and the backlog

Plan items (in this order of FEATs; each FEAT ends with its SCOPED run):
1. **FEAT-1 reflection and snapshots**: `RunCounter.stamps`, the new `Case` fields, one-off cases, `Delivery`/`signer_of` (moved from health with
   its tests), `cause_of`, alarms, thresholds, marks, `ContractVersions`, `OrgHistory.changes` + `GitClient.log`, `BarHistory` +
   `GitBarHistory`, `CaseRecords` + `DerivedCaseRecords`, `DeliverableChecks(settled=...)`, `services.criterion_words` and the base heading
   constants (byte-identical moves first, each its own commit).
2. **FEAT-2 one-off verdicts**: the `feedback` branch, refusals, `feedback_step`, docstrings and help, the skill's line 98.
3. **FEAT-3 the view**: `QualityReport`, `left_blocked`, the renderer, `FailCounts` + `HealthFailCounts`, `ReadableOrgConfig`, `QualityTools`,
   `QualityCommand`, ROOT_INSTRUCTIONS, README section "Quality (phase 0b)" within the README line caps.
4. **FEAT-4 health rebase**: section 10.
5. **FEAT-5 ride-alongs**: 11.1, the skill's line 88, 11.5 (the flaky golden screen test: find the nondeterminism, make the capture
   deterministic, no retry).
6. **FEAT-6 replays**: the kit, its meta tests, 19.3 and 19.4.
7. **FEAT-7 docs**: ARCHITECTURE (2.2 row 31, section 3's Protocol lists for reflection, progress, snapshots, health's port, the entry points),
   README, and amendments to this design for anything the build changed.
8. **E5 adoption** (19.5, section 27): when E5's evidence and gate exist, an amendment to this design before any E5 replay test.

Backlog (out of scope, with the reason):
- A one-off verdict settling P3 hand-edit notes and one-off client questions (8.5): consistent, but changes 0a.2 behaviour the row does not ask
  for.
- Semantic failure classes beyond `off_spec` and `wasteful` (packs, Phase 3); `period` units and the `external` tier (Phase 3).
- A full git replay of E4's history (its log text cannot rebuild the repository).
- Health reading hand edits (it runs per agent and in the review cycle; 10).
- Refusal counts in the view (the retro brief, Phase 2; `observe` shows them now).
- An org-level criteria library from one-off verdicts (08 section 6: reopens after 0b shows recurring one-off shapes).

## 24. Deviations from 08, go/no-go and the gate (with reasons)

- **D1 (08 3.2) A contract-gap rule by answer.** 08 types contract-gap by trigger words only. 0b adds: the client's human-tier answer names a
  criterion the rejected task's contract lacked. Reason: it is the client's recorded yes, stronger than a phrase; without it E3's reject 2
  (C11), and E4's s1r/s2r/s3 first rejects, type as untyped or by an "always" that happens to be there.
- **D2 (08 3.2) A fixed order of the rules, with `also`.** 08 gives the rules as a list. The order of 5.1 makes the type deterministic and keeps
  the gate's pre-registered s2r carry-over; the other matching rules stay visible as disputed causes.
- **D3 (08 3.2) "The reviewer PASSed" read from `done` and the task's contract version.** Parsing review reports would be domain- and
  template-specific; a `done` result asserts every criterion met (`FEEDBACK_HEADER`), so a confirmed link to a carried criterion is a sign-off
  the client contradicts.
- **D4 (08 3.3) Escapes are rejections of `done` deliveries only.** A rejection of a blocked or failed result is counted as a verdict on a
  non-delivery: the team did not claim it was done.
- **D5 (08 3.3) Stalled is the current state; no event horizon.** `progress`'s `stalled` state is used instead of stall events, so the 30-day
  horizon does not apply; refusals are not in the view (backlog).
- **D6 (go/no-go item 3) Spend for open and blocked cases.** Go/no-go says "runs used"; the shared function `case_spend` (binding: one function
  with `case_total`) adds the runs still out while a case is open or blocked. For finished cases the two are equal.
- **D7 (go/no-go section 3, F-E3-10) Health excludes contract-gap and relayed causes, keeps untyped, and reads no deliverable folder.** Untyped
  escapes stay counted so unknown causes are not hidden; hand edits are left to the quality view because health runs per agent and in the
  review cycle (cost). Retired services' deliveries drop out of health (cases need a live contract).
- **D8 (08 3.2) One-off cases are root's tasks only.** 08's "one sender" is applied where a client verdict can exist; agents' delegations are
  not cases.
- **D9 (08 3.2) Failure classes: vocabulary now, two derived classes.** Only `off_spec` (reviewer-miss) and `wasteful` (above the cost threshold)
  are derived; the rest are `unclassed`, because a class assigned by the assistant would be relayed text.
- **D10 (08 3.3) Model changes include ORG.md's default model and effort.** A change there changes every agent's runs as much as a charter's
  `model:`.
- **D11 (the gate's item 2) The playbook content check is recomputed for every version**, not only for versions before P1, so a hand-written or
  legacy version is caught the same way.
- **D12 (the brief, the gate, E5's checks) The run credit's title.** They say "`Run not charged:` notes"; the code writes
  `run credit <addr>@<stem>` (0a.2 A.6). 0b reads credits only through `kernel.credited_stems`; E5 and G0 should count the `run credit` notes.
- **D13 (go/no-go item 7) The harness is not built first nor E4 re-run on it.** E4 and E5 ran with their own harnesses; G0 reuses E5's and must
  re-derive E5's counts before its first stream.
- **D14 (the gate's item 7) Memory presence is a controlled arm, skill activation an observed stratifier.** Forcing activation would measure a
  different product.
- **D15 (08 row 0b exit) Cost on E, E2 and A5 is checked from their published counts**, because they kept no run log (19.4).
- **D16 (08 3.3) `quality` is root-only and has a `--json` form on the CLI.** 08 says humans see counts; the JSON is for the study harness.
- **D17 (08 3.1) One-off verdicts go through root's existing `feedback`**, not a new tool, and take no `criterion` or `confirms`.
- **D18 (the gate's item 4) "Deliveries without a verdict" is read per case** (the latest delivery, as 0a.2 D4's `delivered_unrated`), at the
  human tier; deliveries superseded before a verdict are counted apart.
- **D19 (the gate's item 6) Held runs are the assignee's whole derived budget**, with the mechanism named (`budget_to_return` treats a blocked task
  not moved past as busy), not a per-task split.
- **D20 (08 3.3) Hand edits void only verdicts recorded after the edit**, and only the file as it is now is known.
- **D21 (0a 3.1, kept) Legacy verdicts count as the user's** (`verdict_tier`), and the view marks them as legacy.

## 25. User-visible changes beyond 08 row 0b (named)

Row 0b builds the quality view, one-off cases, the timeline and the noise study. These changes go beyond the row's words; each is either a
binding ride-along or required to build the row:
1. Root's `feedback` accepts one-off tasks (its docstring, its CLI help and a new refusal text for root): required by "cases for one-off tasks
   (root notes)".
2. The skill: step 5.1 reads results with `inbox` (go/no-go section 3, binding); step 5.6 records a one-off verdict the user states, with no
   extra question.
3. ROOT_INSTRUCTIONS names `quality` (27 characters).
4. Health: `low_quality` and the health text count typed escapes (`+k not its: ...`), relayed accepts and one-off deliveries; retired services'
   deliveries drop out (go/no-go section 3, binding).
5. The plan block shows up to 10 service checks (F-E3-8, binding).
6. An optional `quality:` mapping in ORG.md for the thresholds (08: "tunable defaults").
7. The CLI's `quality --json`.
None changes what an agent sees.

## 26. Declared limits

- **Declared provenance.** `source="human"` and the recorded words are the assistant's declaration; the product cannot see the conversation.
  A one-off verdict has no contract to fall back on.
- **Hand edits** are known only for the file as it is now, for the newest delivery listing that file name, in a folder a service contract
  names (one-off deliverables elsewhere are not checked), within P3's bounds; a file edited, judged, then rewritten later keeps the verdict.
- **Run attribution** is window-based (08 3.3): a case cut by a later request gives its later runs to that request; the view counts the cut
  cases. Relayed runs are counted by the relayed task's interval, so a relayed rework running in parallel with another task shares runs.
- **reviewer-miss** is inferred from `done` and the contract version, not from what the reviewer wrote; a team that reports `done` without a
  check is typed the same way.
- **The words rule** is English and lexical; "never" in "never mind" matches.
- **Cases** exist only for live services (and continued ones); a retired service's history leaves the view and health.
- **Charter and model marks** need git; a retired agent's charter is not followed; at most 40 commits and 5 s of git time per call.
- **The noise study** at k = 3 gives a range, not a rate.
- **Agent-client services** never alarm; their counts are hypotheses.
- **Stalled** is a current state, not a history.
- **E, E2, A5** kept no run logs; their spends are not derivable from their files.
- **A one-off verdict on a retired assignee's task** cannot be recorded (ONE-OFF-GONE); the view counts it as without a verdict.
- **Cost of a call**: `quality` runs the P3 checks once (at most about 11 s of git) and the bar history (at most 5 s).

## 27. E5: adoption by amendment, and the definitions most likely to move

E5's gate is not written yet. 0b's build may start after E5's live streams finish, and 0b merges only if E5 passes. When E5 reports, the
manager amends this design before the plan freezes, or by a design amendment during the build, for each finding that touches:
1. **The carry-over rule (5.1 rule 2)**: E5 is the first live data with P4's base sections; if a `base="delivered"` rework still carries a
   relayed change, the base clause moves.
2. **Contract-gap by answer (rule 3)** and **reviewer-miss (rule 4)**: E5's `answers` amendments and product links are their first live input.
3. **Hand-edit voiding (4.3)**: E5 counts P3 notes and hand edits; their timing decides whether "edited before the verdict" is the right cut.
4. **Without a verdict (4.3)**: P2-UNRATED makes root record verdicts; E5's counts of 0a.2 D4's friction may move the per-case reading.
5. **Credited and relayed runs (4.2)**: E5's throttle credits are the first live credits.
6. **Reviewer ambiguity recall (20.4 A)**: G0 copies E5's definition verbatim; a change there changes G0.
7. **Moved past without a verdict (4.5)**: P2's retire gate and continuations may change which blocks stay open.
8. **The replays (19.5)**: E5's streams join them with expectations pre-registered by amendment.

## 28. Open questions for the owner

- **Q1. Ask after a one-off delivery?** The design records a one-off verdict only when the user states one (no extra question, within 08's D3
  friction). Asking "Keep it, or what should change?" after every one-off delivery, as for services, would make one-off cases measurable at the
  cost of one question per one-off task.
- **Q2. Untyped escapes in health.** The design keeps them counted against the verifier (unknown causes stay visible). Excluding them would
  remove more false alarms and hide real misses.
- **Q3. The size of G0.** 2 arms x k = 3 is about 300 org runs plus 6 assistant sessions. More streams per arm (k = 5) narrow the band; adding
  streams to fill thin skill strata is possible only after the fact.
- **Q4. The cost alarm and the assistant's own spend.** The design fires on total spend and shows the relayed runs apart (the user pays both).
  Excluding relayed runs from the comparison would make the alarm about the team only.
- **Q5. The 3-judged-case minimum for the cost alarm.** It follows 08; `case_total` already warns per case at 1.0x. A per-case cost alarm
  without the minimum would repeat that warning.
