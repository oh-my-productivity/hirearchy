# Org growth, Phase 0b: Measure (technical design)

Status: design, revision 2 (answers the design review of revision 1, 25 findings; resolutions in Appendix A). Branch `feat/org-growth-phase-0b`,
worktree `/Volumes/workspace/hirearchy/.worktrees/org-growth-0b`, based on `main` `6618c0d` (0a.2 merged; the floor batch merged before it).
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
  and 1634 files).
- E5: `studies/E5-org-growth-0a2-recheck/` exists in the main checkout, untracked and in progress (stream `s1`, `evidence/protocol.md` of
  1 527 lines, md5 `afd437c103407ec5899e4993b465cf25` as its `protocol.md5` records). Its gate (`phase-0a2/e5-gate.md`) does not exist yet
  (checked). Section 27 says how both are adopted by amendment.

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
- a **verdict counts only for the delivery it follows**: a human-tier verdict recorded after a task's `done` result; a verdict given on a
  blocked or failed result, or before the done result, is counted apart and is never read as the verdict on a later delivery;
- the **repeat alarm** counts only human-tier links (a `confirms` link note or 0a.2's product link), and shows the unconfirmed ones apart;
- the **cost alarm** reads `reflection.case_spend`, the function `case_total` already uses, and compares it exactly with the current
  contract's budget; it shows user top-ups, the runs of relayed reworks and the runs credited as throttled apart, never folded in;
- every **escape** gets a cause typed by rule (`relayed-error`, `relayed-carry-over`, `contract-gap`, `reviewer-miss`, `untyped`), with the
  rule that typed it; one attribution rule decides which causes count against the verifier, and both the view and health's `low_quality`
  use it;
- **deliveries without a verdict** are counted and never read as accepts; a delivery whose file the assistant edited by hand before the user
  judged it counts as neither pass nor escape;
- a **blocked task moved past without a verdict** is shown with the runs its assignee holds and every task those runs are held behind;
- the **timeline** marks contract amendments confirmed, unconfirmed or user-initiated, playbook versions with what their changed lines rest on
  (never as an improvement), charter edits, model changes and top-ups.

The exit criterion is "noise baseline measured; alarms checked on replayed E/E2/A5 files". 0b checks the alarms deterministically on the
files E, E2, A5, E3 and E4 (s1r, s2r, s3) kept (section 19), with expectations pre-registered here, and specifies the noise study (study
G0, section 20): the same script repeated k >= 3 times per arm, every seat claude-sonnet-5.5 at effort high, on the V3 runtime, stratified by
memory presence (controlled) and skill activation (observed), measuring the team, the assistant layer and the product's own counts. G0 runs
after E5 passes and 0b merges, and Phase 0b closes with G0's report (20.1).

## 2. Technology stack (locked)

Python 3.11; the existing packages only (FastMCP `mcp`, PyYAML; Textual is touched only by the flaky-test fix); the standard library's
`fractions` and `decimal` for exact threshold comparisons and rounding; `git` (already required by `snapshots`); uv, pytest,
`mypy==2.4.0 --strict`, `import-linter==2.15`, `scripts/check.sh`. No new runtime dependency, no new package, no new dependency edge between
packages (every cross-package need below is a consumer-owned port implemented in `app`, the pattern of `app/_checked_versions.py`), no ledger,
no new file kind in an organization, no event field. Strict TDD (R11) under the owner's scoped test policy (section 18.3).

## 3. Shared definitions (each defined once)

| Name | Home | Definition |
|---|---|---|
| case | `reflection` (`Case`) | The head of a `revises` chain sent by one sender to one assignee, plus that chain (08 3.2). A **service case**: the client (`parent(owner)`) sent tasks with `service == name` (today's `DerivedCaseHistory.cases`). A **one-off case** (new): root sent tasks without `service`; the chain follows `revises` among root's one-off tasks to the same assignee. Agents' own delegations are not cases (no client verdict exists for them). Unit: `case` (08 3.1; `period` is Phase 3). |
| delivery | `reflection` (`Delivery`, new) | A task of a case whose latest result (`kernel.latest_results` over the client's received boxes) is `done`. That result is the delivery's result. |
| verdict, tier | `reflection` (`Verdict`), `kernel.verdict_tier` | A note with `feedback` that replies to a task of the case; its tier is `human`, `relayed` or `agent` (a root note without `source`, written before 0a, is `human`: 0a 3.1). Only `human` counts anywhere in 0b. |
| verdict on a delivery | `reflection` (`Delivery.verdicts`) | A verdict on the delivery's task whose id is greater than the delivery's result id: it was given after the team reported `done`. |
| verdict not on a delivery | `reflection` | A human-tier verdict on a task of the case that is no verdict on a delivery: given on a blocked or failed result, or on the task before its done result arrived. Counted apart; never read as the verdict on a later delivery. |
| counted verdicts | `reflection` (`Delivery.counted`) | The human-tier verdicts on a delivery recorded before its hand edit (4.3); all of them when the delivery's file was not hand-edited. |
| judged | `reflection` | A delivery is judged when it has a counted verdict. A **judged case** is a case with at least one judged delivery. |
| escape | `reflection` (`Delivery.escape`) | A judged delivery with at least one `reject` among its counted verdicts: the team reported `done`, then the human client rejected it. A reject followed by an accept on the same delivery stays an escape (health's rule today, `health/_escapes.py`). |
| decisive verdict | `reflection` (`Delivery.decisive`) | The latest counted reject of an escape; otherwise the latest counted verdict. Its words are the ones quoted; its `R<k>` is the escape's assertion. |
| superseded | `reflection` (`Delivery.superseded`) | A delivery with no human-tier verdict (counted or voided) whose case holds a later task sent after the delivery's result: the id of the first such task. |
| signer | `reflection.signer_of` (moved from `health/_escapes.py`) | The sender of the latest `done` result the owner received from a direct report, answering a task the owner sent after the delivered task and received before the delivery; the owner itself when none (0a 5.5, unchanged). |
| cause | `reflection.cause_of` (new, pure) | Section 5. |
| attribution | `reflection.attribution` (new, pure) | `counted` for the causes `reviewer-miss` and `untyped` (the verifier's possible misses); `not its` for `contract-gap`, `relayed-error` and `relayed-carry-over`. The view's verifier line and health's `low_quality` both call it (I5). |
| `case_spend` | `reflection.api` (0a.1 6.1, unchanged) | Runs used, plus, while the case is open or blocked, the runs handed down that were neither used nor returned. `case_total` and the cost alarm both call it. |
| approved budget | `reflection` | A service case: the `budget` of the service's current contract (the value `case_total` compares with). A one-off case: the head task's `budget`. |
| top-ups | `reflection` (`Case.top_ups`, new) | The budgets of the chain's later tasks, by their `source` (`human`, `relayed`, or not recorded), plus the budget of every note the client sent to an agent of the team inside the case window (progress's grant rule, `LogRunCounts._window`). |
| run window | `reflection._cases` (unchanged) | From the head task's id to the final result of the latest task, ending early at the client's next task to the same owner outside the chain. A window that ended early is `cut` (new flag). |
| charged run, credited run | `kernel.credited_stems` | A run log whose stem a run credit names (`run credit <addr>@<stem>`, `kernel.RUN_CREDIT_TITLE = "run credit"`) is credited: not charged, not counted in `runs` (0a.2 9.2, already so in `LogRunCounter`). |
| moved past (budget sense) | `mail.moved_past` (0a.1, unchanged) | A later task from the same sender revises the blocked task (or what it revised), or the sender gave a verdict on its chain after the block: its budget is released. |
| held task (new) | `progress._quality` | A task in `TaskQuery.blocked_tasks(A)` that `mail.moved_past` does not release: `budget.ReserveAllocationPolicy.budget_to_return` treats `A` as busy while one exists. |
| left blocked (new) | `progress._quality` | A held task whose sender has since sent the assignee another task outside its chain: "moved past without a verdict" (the gate's words). |
| hand edit | `reflection.DeliverableChecks` (0a.2 P3) | A `differs` finding: a file of a contract's deliverable folder that is not the team's checked version of the artifact of the delivery whose task the finding names (`DeliverableFinding.task`). |
| `LASTING_WORDS` | `reflection.api` (new) | `("always", "never", "from now on")`, matched case-insensitively on word boundaries; the default of `cause_of`'s `lasting` argument (a pack passes its own in Phase 3). |
| `CAUSES` | `reflection.api` (new) | `("relayed-error", "relayed-carry-over", "contract-gap", "reviewer-miss", "untyped")`. |
| `FAILURE_CLASSES` | `reflection.api` (new) | `("wrong", "missing", "off_spec", "unusable", "out_of_authority", "process_skipped", "wasteful")` (08 3.2), the closed core vocabulary packs map onto (Phase 3). |
| `QUALITY_DEFAULTS` | `reflection.api` (new) | `{"min_judged": 3, "repeat_window": 3, "repeat_failures": 2, "cost_ratio": "1.25"}`, tunable defaults (section 6); `cost_ratio` is held as `Fraction("1.25")`. |
| `Mark` | `reflection.api` (new type alias) | `ContractMark \| PlaybookMark \| CharterMark \| ModelMark \| TopUpMark`, the items of `ServiceRecord.timeline`. |
| `ratio(k, n)` | `progress._quality_render` (new, pure) | `"{k} of {n}"`; `"n/a (0 of 0)"` when `n == 0`. Every rate in the view goes through it. |

## 4. Data model of every derived count

All counts are derived per call. The tables name, for each, its definition, the exact files it is read from, and the function that
derives it. "Root's boxes" are `<org>/{inbox,inflight,read,sent}/*.md`; an agent's are `<org>/<addr>/{inbox,inflight,read,sent}/*.md`
(single writer `mail`). Contracts: `<owner>/services/<name>/SERVICE.md` and `history/SERVICE.v<n>.md`; playbooks: `PLAYBOOK.md` and
`history/PLAYBOOK.v<n>.md` (single writer `services`). Run logs: `<addr>/runs/<stem>.log` (single writer `runs`). Charters:
`<addr>/AGENT.md` (single writer `orgfiles`).

### 4.1 Cases

| Count | Definition | Files | Function |
|---|---|---|---|
| cases | Service cases of a service; one-off cases of root | client's `sent/` (tasks), contract `created` from `SERVICE.md` | `CaseHistory.cases` (unchanged), `CaseHistory.one_off_cases` (new) |
| state | `done`, `failed`, `blocked` from the latest task's latest result, else `open` | client's received boxes (results) | unchanged |
| stalled | an `open` case whose latest task `progress`'s `TaskStates.state_of` calls stalled now (its `state` starts with `stalled (`) | the team's boxes, pause flags, run registry | `progress` (current state only, no history) |
| reworks, relayed reworks | tasks after the head; those with `source: relayed` | client's `sent/` | `Case.reworks`, `Case.relayed_reworks` (unchanged) |
| cut | the window ended at the client's next task to the owner before the final result | client's `sent/`, received boxes | `Case.cut` (new) |
| runs not counted | the case's team cannot be read for runs: the one-off assignee no longer exists (`assignee retired`), or the head task is older than the owner's (or assignee's) charter `created` (`sent before {owner} was hired again: the retired team's run logs are not read`; 0a.2 section 22, a continued service's old cases) | `<addr>/AGENT.md` frontmatter `created` (`agents.CharterReader`); a charter without `created`, or one that cannot be read (`OSError`), gives no mark | `Case.runs_unknown: str` (new, `""` when counted) |

One-off cases (`DerivedCaseHistory.one_off_cases()`, new): root's sent tasks with no `service`, grouped by `revises` exactly as service
chains are (`head()` follows `revises` within root's one-off tasks to the same `to`; a rework to another assignee heads its own case). `Case`
for a one-off: `service = ""`, `owner = head.to`, `playbook = used = 0`, `client_kind = "human"`; verdicts are root's notes with `feedback`
that reply to a task of the chain (section 8); runs use the same window rule over `agents.subtree(head.to)`. `case_of(task)` stays
service-only, so `progress`, P3 and P4 behave as today. One private chain builder serves `cases` and `one_off_cases`; it takes the floor
(`since: datetime | None`) and whether to count runs, so health's reads (section 10) need neither a contract nor the run logs.

### 4.2 Runs, spend, top-ups

| Count | Definition | Files | Function |
|---|---|---|---|
| runs | charged run logs of the owner's subtree in the window | `<addr>/runs/*.log` names; credits in each agent's received boxes | `Case.runs` (unchanged) |
| credited | credited run logs in the window | same | `Case.credited` (new) |
| relayed runs | charged runs whose stamp `s` satisfies `t.id[:21] <= s < next.id[:21]` for a relayed task `t` of the chain (`next` its successor in the chain; the last task's interval ends at the window's end, inclusive) | same | `Case.relayed_runs` (new) |
| spend | `case_spend(case)` | as above plus result `budget` headers | unchanged |
| ratio | `Fraction(spend, approved)`, shown with two decimals rounded half up (`Decimal.quantize(Decimal("0.01"), ROUND_HALF_UP)`); `n/a (budget 0)` when the approved budget is 0 or below | current `SERVICE.md` `budget`, head task `budget` | `progress` renderer |
| top-ups | `{"human": h, "relayed": r, "unrecorded": u, "granted": g}`: budgets of `tasks[1:]` by `source` (`None` = unrecorded, a legacy rework), and `g` = the budget of the client's notes (`type == "note"`, `budget > 0`, `to` in the team) with an id inside the window | client's `sent/` | `Case.top_ups` (new) |

`RunCounter` gains `stamps(team, start, end) -> list[tuple[str, bool]]`: the 21-character stamps of the team's run logs in the inclusive window,
each with whether a run credit names its stem. `runs_between` becomes the count of the uncredited stamps (no caller changes). `Case.runs`,
`credited` and `relayed_runs` are computed in `DerivedCaseHistory` from one `stamps` call per case.

### 4.3 Deliveries, verdicts, coverage, hand edits

For each task `t` of a case, `r` is its latest result in the client's received boxes. `t` is a delivery when `r.status == "done"`.

| Count | Definition | Files | Function |
|---|---|---|---|
| deliveries | per case, its tasks whose latest result is `done` | received boxes of the client | `deliveries_of` (new, pure) |
| verdicts on a delivery | notes with `feedback` that reply to `t` with an id above `r.id`, every tier, oldest first | client's `sent/` | `Delivery.verdicts` |
| counted, voided | counted: the human-tier ones of `Delivery.verdicts` whose time (`msg_time`, in microseconds) is below `edited_at`, all of them when `edited_at == 0`; voided: the human-tier ones at or after `edited_at` (`edited_at > 0` only) | as above, plus the deliverable folder | `Delivery.counted`, `Delivery.voided` |
| outcome | `rejected` when a counted verdict is a reject (an escape); `accepted` when judged and not an escape; `neither` when nothing is counted and something is voided (judged after a hand edit); `none` otherwise | derived | `Delivery.outcome` |
| first delivery | the head task's delivery and its outcome | as above | `Delivery.step == 0` |
| superseded | section 3 | client's `sent/` | `Delivery.superseded` (the later task's id) |
| judged | deliveries with a counted verdict | client's `sent/` (notes) | `Delivery.judged` |
| without a verdict | cases in state `done` whose latest delivery has no human-tier verdict on it (neither counted nor voided); `relayed only` = those of them with a relayed- or agent-tier verdict on it | client's `sent/` | `unjudged_cases` (new, pure; defined by `Delivery` only, never by `reflection.rated`) |
| verdicts not on a delivery | section 3 | client's `sent/` and received boxes | `not_on_a_delivery` (new, pure) |
| hand-edited | deliveries a `differs` finding names, settled or not | deliverable folders, org git history (P3) | one `DeliverableChecks.findings(ROOT, None, settled=True)` call per `records()` call |
| legacy verdicts | human-tier verdicts without `source`, counted or not | client's `sent/` | `Verdict.message.source is None` |

**Hand edits void a verdict only when the edit came first.** `DeliverableFinding` gains `written: int` (the file's mtime in microseconds,
which P3 already reads as `FolderFile.mtime_us`) and `settled: bool`. `DeliverableChecks.findings` gains the keyword `settled: bool = False`:
with `True`, findings P3 would leave out as settled are returned with `settled=True` (P3's own notes keep calling it with the default, so
`progress`, `status` and `whoami` are unchanged).

`DerivedCaseRecords.records()` calls `findings(ROOT, None, settled=True)` **once** (one P3 bound of 40 git pairs and 5 s per call, 0a.2
DR-33) and attributes each `differs` finding to the delivery, service or one-off, whose task id equals `finding.task`; that delivery gets
`edited_at = finding.written`. A finding with `written == 0` (the time is not known; only fakes produce it) marks the delivery hand-edited
and voids nothing. `unknown`, `link`, `large`, `limit` and `unreadable` findings name no delivery: they are not counted as hand edits and the
view does not show them (`progress`, `status` and `whoami` already show them as P3 notes). A finding that names a task of no record (a task
of a service whose contract is no longer requestable) is dropped.

Pass or escape is decided by the counted verdicts alone. So a hand-edited delivery whose user's verdicts all came after the edit is
`neither`; one judged before the edit keeps that verdict (it judged the team's file) and voids the later ones; one without any verdict is
counted both as "without a verdict" and as "hand-edited". Only the file as it is now is known (section 26). Section 24 D20 records this as
a deviation from the gate's item 4.

### 4.4 Escapes, signers, verifiers

| Count | Definition | Files | Function |
|---|---|---|---|
| escapes | judged deliveries with a counted reject | client's `sent/` | `Delivery.escape` |
| signer | section 3 | owner's `sent/` (tasks) and received boxes (reports' results) | `signer_of` (moved from health, unchanged rule) |
| per verifier | for each signer other than the owner: `judged` (its judged deliveries), `counted` (its escapes whose attribution is `counted`, by cause), `not its` (its escapes attributed `not its`, by cause) | as above | `progress` renderer over `ServiceRecord`, through `attribution` |
| PASS precision | per verifier: `ratio(judged - counted, judged)`: the judged deliveries it signed off that no counted escape contradicts | as above | `progress` renderer |
| verifier FAILs | per signer: `rechecks` and `rework_runs` of `health.MailEscapeCounter` (0a 5.5, unchanged) | the signer's boxes, authors' run logs | `FailCounts` (progress port, app adapter over health) |
| assertion | `R<k>`: the k-th human-tier rejection of the service (any rejection, also one not on a delivery) | client's `sent/` | `regressions` (unchanged) |
| cause | section 5 | as section 5 | `cause_of` |
| failure class | `off_spec` for an escape typed `reviewer-miss`; `wasteful` for a case above the cost threshold; no other class is derived in 0b (`null`) | derived | `failure_class` (new, pure) |

### 4.5 Blocks moved past without a verdict, held runs

| Count | Definition | Files | Function |
|---|---|---|---|
| held tasks | for every agent `A`: every `t` in `TaskQuery.blocked_tasks(A)` with `not moved_past(t, latest[t.id], received(A))` (the tasks `budget_to_return` holds on) | `A`'s boxes | `progress._quality.held_tasks` (new, pure over mail reads) |
| left blocked | a held task `t` such that `received(A)` holds a task from `t.sender` with an id above the blocked result's id that is outside `t`'s chain (the chain of `mail.moved_past`) | `A`'s boxes | `progress._quality.left_blocked` (new, pure) |
| held | `BudgetQuery.budget(A)` for an agent with at least one left-blocked task | everything `budget` derives from | `progress` |

The section lists every agent with at least one left-blocked task, with **every** held task of that agent (left blocked or not), because the
held figure is the agent's whole derived budget: while any held task exists, `budget_to_return` treats the agent as busy and its later results
return nothing (0a.1 item 5). The view names that mechanism and the tasks; it does not split the budget per task (section 24, D19). A held
budget of 0 or below reads `holds no run (budget {b})`. The service block counts its cases whose latest task is left blocked.

### 4.6 The core concepts in the data

- **Source tiers** (08 3.1): only `human` counts in a count of client evidence; `relayed` and `agent` verdicts are counted apart and named.
  `external`, `client-check` and `runtime-check` tiers are Phase 3; the JSON carries `tier` per verdict so they slot in.
- **Timing** (08 3.1, delayed oracles): Phase 3. A pack with a delayed oracle splits "without a verdict" into "awaiting (inside the oracle's
  delay)" and "without a verdict"; 0b's verdicts are immediate, so every delivery without a verdict is counted as such.
- **`client_kind`**: `human` when the client is root, else `agent` (`Case.client_kind`, 0a). A service with an agent client has only
  agent-tier verdicts: its block is one line of counts, never quoted words, never an alarm (section 9.2).
- **Unit**: every record says `unit: case`.
- **Failure classes**: the vocabulary is fixed now; 0b derives a class only where a rule can (4.4); every other escape is `unclassed`.
- **Rule-typed causes**: section 5.

## 5. Rule-typed causes

### 5.1 The rules, in order

`cause_of(delivery, case, assertion, carried, results, lasting=LASTING_WORDS) -> Cause` (pure; `reflection/_causes.py`, exported from
`reflection.api`) types an escape. `v` is the delivery's decisive verdict; `assertion` is its `R<k>` (`regressions`); `carried` is the set of
`C<k>` ids current in the contract version the rejected task carried (`task.contract`; a legacy task without it uses the version in force at
the task's time; a one-off has none); `results` maps each task of the case to its latest result; `lasting` is the words rule's vocabulary
(a pack passes its own in Phase 3, so no core edit is needed). The rules are tried in this order; the first that matches gives the type and
the rule:

1. **`relayed-error`**: the rejected delivery answers a relayed task (`delivery.task.source == "relayed"`). The team did what the assistant
   asked on its own reading.
2. **`relayed-carry-over`** (the gate's item 3): the rejected task `T` is not relayed, and there is a relayed task `R` of the chain with
   `J < R.id < T.id`, where `J` is the result id of the latest delivery of the case whose first counted verdict was recorded before `T` was
   sent (the head task's id when there is none), such that
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
5. **`contract-gap`, by words**: the client's words (`v.note`) contain a word of `lasting` (08 3.2's rule).
6. **`untyped`**: nothing matched; when the human-tier link is `none`, the detail says "the user said it is no lasting rule".

`Cause` (frozen dataclass): `type` (one of `CAUSES`), `rule` (`"relayed task"`, `"carry-over"`, `"answer"`, `"link"`, `"words"`, `"none"`,
or `"unreadable"` for 10's fallback), `detail` (the ids the rule read: the relayed task, the shared artifact, the link note and criterion, or
the matched word), `rules` (every rule that matches, in order, the winner first), `also` (the **distinct types, other than the winning
type,** of the later rules that match: a disputed cause, retro material), `before_verdict` (the id of a relayed task of the case whose `done`
result lies between the rejected delivery's result and the decisive verdict: "the user may have judged that version"; `""` otherwise).
A later rule of the same type as the winner is visible in `rules` (the JSON), not in `also` (the text). Rules 3 and 4 never match a
one-off rejection: a one-off verdict takes no link (8.1).

### 5.2 Why this order

The structural relayed rules come first because they name a cause outside the team that the data shows directly, and they must win over the
answer that followed: in E4 s2r the Marta escape was introduced by the injected relayed rework, inherited by Lena's rework, and then answered
with a new criterion C10; the gate pre-registers it as relayed carry-over (rule 2 before rule 3). The recorded answer comes before the reviewer
rule because the same link that names a criterion says whether the task's contract had it; rules 3 and 4 partition the human-linked rejections.
The words rule is the weakest evidence (a phrase in a note) and comes after the link rules, so a reject that names a criterion the reviewer
passed is a reviewer miss even if the note says "always" (`contract-gap` is then listed in `also`). Section 24 D1-D3 records the departures
from 08's list.

### 5.3 The texts (the view; `progress/_quality_render.py`)

| Type (rule) | Text after the escape's head (9.2) |
|---|---|
| relayed-error | `relayed-error (the rejected delivery is your relayed rework {task})` |
| relayed-carry-over | `relayed-carry-over (your relayed rework {R} changed {path} after the delivery the user judged, and this rework started from it)` |
| contract-gap (answer) | `contract-gap (the user's answer, link {link}, names {C}, which contract v{n} of the task did not have)` |
| reviewer-miss | `reviewer-miss (the user's confirmed link {link} names {C}, which contract v{n} of the task had; the team reported done)` |
| contract-gap (words) | `contract-gap (the user's words say "{word}")` |
| untyped | `untyped (no rule matched)`, `untyped (the user said it is no lasting rule)` or, for 10's fallback, `untyped (the contract could not be read: {error})` |

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
`ReadableOrgConfig` over `settings.readable_config`, by `quality_thresholds(config) -> tuple[QualityThresholds, tuple[str, ...]]` (pure,
`reflection._quality_rules`). Validation (section 14):
- `min_judged`, `repeat_window`: an `int` (not a `bool`), an integral `float`, or a string of digits; at least 1.
- `repeat_failures`: the same type, with `1 <= value <= repeat_window` (after `repeat_window` is settled). When `repeat_window` is below the
  default 2 and `repeat_failures` is not given, the default is clamped to the window and the note
  `quality.repeat_failures: the default 2 is above repeat_window {w}, so {w} is used.` is added.
- `cost_ratio`: an `int` or `float` (not a `bool`, finite) or a decimal string (`^\d+(\.\d+)?$`), above 0; held as `Fraction(str(value))`
  and shown as written.
- A value that fails keeps its default and adds `quality.{key} in ORG.md is not {what}: the default {d} is used.`; an unknown key adds
  `quality.{key} in ORG.md is not a threshold: ignored (the thresholds are min_judged, repeat_window, repeat_failures, cost_ratio).`;
  a `quality:` that is not a mapping is ignored with `quality in ORG.md is not a mapping: the defaults are used.`; an ORG.md whose settings
  block does not parse gives the defaults and `ORG.md cannot be read (its settings block does not parse): the default thresholds are used.`
The view's header always says which applied.

**Judged cases** (`judged_cases(record)`, pure): the cases with at least one judged delivery, ordered by the id of their latest counted verdict.

**Repeat** (`repeat_alarm(record, t)`, pure). The last `repeat_window` judged cases. The subjects of a case are, for each counted human-tier
reject `v` of its deliveries with assertion `a`: `a.id`, every `C<k>` of `v.confirmed`, every id of `a.about`, and the `R<j>` ids of `v.links`
when `v.links_tier == "human"` (`none` excluded). A subject in at least `repeat_failures` of the window's cases fires the alarm. A criterion
that only a relayed reading names (the rejection's own `criterion`, or a relayed link) is never a subject; such links are listed as `not
counted`. A rejection not on a delivery gives no subject. States: `fires`, `no`, `n/a ({k} of {min_judged} judged cases)`, and for root's
one-off tasks `does not apply (one-off tasks name no criterion ids)`.

**Cost** (`cost_alarm(record, t)`, pure). Evaluated once the record has `min_judged` judged cases; fires for every case of the record (any
state) with `Fraction(case_spend(case)) > t.cost_ratio * approved` (exact, no division: 0a.1 section 13). A case whose approved budget is 0
or below, or whose runs are not counted (4.1), is skipped and named. The alarm compares with the approved budget only: top-ups (human
reworks, relayed reworks, unrecorded reworks, grants), relayed runs and credited runs are shown beside it (go/no-go item 3, the gate's item 5).
Each case line shows its ratio whatever the alarm says, and `case_total` keeps warning at 1.0x on any case, so the user is told of an
overspend before three cases are judged. `over_cost(case, approved, ratio) -> bool` is the per-case predicate the alarm applies; 19.4 tests it
on published counts.

Both alarms ignore epochs: no count is split by contract or playbook version (08 3.3).

## 7. The timeline of bar changes

`ServiceRecord.timeline` (newest last; the view shows the 15 newest, then `and {k} earlier`). The marks are facts; no count is partitioned by
them and no mark says "improved".

| Kind | Source files | Fields | Text |
|---|---|---|---|
| contract | every stored `SERVICE` version (`ServiceStore.versions(owner, name, "SERVICE")`, read through a reflection port `ContractVersions`) | version, `defined`, `defined_by`, added and removed ids (`number_criteria` over the stored versions), basis | see below |
| playbook | `ServiceCatalog.playbook_versions` | version, `revised`, `by`, `admitted`, cited ids, changed-line counts | see below |
| charter | git history of `<addr>/AGENT.md` | addr, commit, when | `{addr}: charter edited (commit {12 hex})` |
| model | git history of `<addr>/AGENT.md` (frontmatter `model`) and `ORG.md` (frontmatter `default_model` and `effort`) | addr or `ORG.md`, key, before, after, commit | `{addr}: model {before} -> {after}` / `ORG.md: default model {before} -> {after}` / `ORG.md: effort {before} -> {after}` |
| top-up | the cases (4.2) | case, task or note id, amount, kind | `top-up +{n} run(s) to case {case}: {human rework {id} \| your relayed rework {id} (your own spend) \| rework {id} (tier not recorded) \| your grant {id}}` |

**Contract marks.** v1: `contract v1 ({ids})`. A later version: `contract v{n} ({by}): adds {ids}; removes {ids}` (each part only when
non-empty; `criteria unchanged` when neither), then its basis:
- `answers` set (0a.2 P2): `: the user's answer to {R}`, then per added id `{id} confirmed (link {link})` when `confirmed_criteria(cases,
  criteria)` names it (for an answered version only the human link on that rejection counts: 0a.2's rule), else `{id} not confirmed (the link
  was not recorded)` (0a.2 DR-30: the product's link write can fail after the contract);
- `initiated: user`: `: asked for by the user on their own: {ids} user-initiated (never admit a playbook revision)`;
- a root version without either (written before 0a.2): per added id, `confirmed (link {id})` when `confirmed_criteria` names it (0a.1's rule),
  else `not confirmed`; the mark ends `: not confirmed` when none is;
- `defined_by` an agent: `: by {agent}, an agent client (its verdicts are hypotheses)`.

**Playbook marks.** `playbook v{n} ({by})`, then:
- `admitted: c`: `: admitted (c) on {cited ids}: {k} changed line(s): {w} the cited criteria's own words, {b} beyond them`;
- `admitted: b`: `: admitted (b) on {cited ids}: {k} changed line(s): {t} tagged with an id, {u} untagged`;
- `first`, `restore`: `: first version` / `: restores v{m}`;
- no `admitted`, written by the client (`by` is the owner's parent: root for a top-level owner): `: written by the client (no admission
  needed)` (0a 3.5: a version the client wrote has none);
- no `admitted`, written by the owner (legacy, before 0a): `: no admission recorded (written before the evidence gate)`;
then `; {r} line(s) removed` when any. The counts are recomputed for every version from the stored bodies:
`changed_lines(previous.body, body)` (services.api, 0a.2). The **cited criteria** of a version are the `C<k>` ids among its evidence and the
criteria of the link notes it cites (P1: a link note id counts as its criterion), looked up in the service's criteria. A line is "the cited
criteria's own words" when `criterion_words(line, cited)` names one (P1's rule `_words_of`, moved to `services.api` as
`criterion_words(line, criteria)` so both read one rule, and applied to the same set P1 applies it to); "tagged" when it carries a `C<k>` or
`R<k>` token. A version admitted before P1 shows its lines beyond the cited criterion (E4 s2r v2); one admitted after P1 shows 0 beyond by
construction. Cited ids are shown only when they match `C\d+`, `R\d+` or a message id (`\d{8}T\d{12}-[a-z0-9./-]+`); others are counted
(`and {k} other id(s)`), because evidence ids are agent-written. The playbook's `reason` and its lines are never in the text.

**The changed lines themselves** (the gate's item 2: "with its diff beside the cited criterion's text") are in `quality --json` only: each
playbook mark carries `cited` (`[{"id", "text"}]`: the criteria's texts, the client's own) and `lines` (at most 10 changed lines, each
`{"text": clip_line(line, 600), "own_words": bool}`, plus `lines_more`), marked `"agent_written": true`. The MCP text and the CLI text never
carry them (I8; section 24 D22 records the deviation). A user who wants the diff at the terminal reads `quality --json`; root's surface is the
MCP text.

**Charter and model marks** come from a reflection port `BarHistory` (`reflection/_ports.py`), implemented in `app/_bar_history.py` by
`GitBarHistory(history: OrgHistory, clock: Clock)`:
1. `history.changes([f"{a}/AGENT.md" for a in addrs] + ["ORG.md"], limit=40)` (new `OrgHistory` method, 12.3): `(commit, committed time,
   path)` per changed path, newest first, at most 40 commits; `None` without a repository or git.
2. For each path, consecutive listed versions (newer, older): `history.text(commit, path, 65536)` of each (memoized per pair). AGENT.md:
   bodies differ (after `kernel.split_frontmatter`) -> a charter mark; frontmatter `model` differs (stripped, `""` shown as `the org
   default`) -> a model mark. ORG.md: `settings.config_default_model(meta)` or `settings.config_effort(meta)` differs (the same readers the
   runtime uses, so `null`, empty and missing compare as the default) -> a model mark. A `text` that returns `None` (the file is above 64 KiB at
   that commit, or cannot be read) gives no mark for that pair and counts in `skipped`. The oldest listed version of a path has no predecessor
   in the list: no mark (its creation, or beyond the bound; `truncated=True` when the list was full).
3. A bound of 5 s of git time per call (`Clock.monotonic`, read before each read) and 2 s per git subprocess; past it the rest is not read and
   `truncated=True`.
The result is `BarChanges(known: bool, marks, truncated: bool, skipped: int)`. `known=False` renders `charter edits and model changes:
unknown (no org history: the organization is not a git repository, or git is missing)`; `truncated` adds `(the newest 40 commits were
read)`; `skipped` adds `({k} version(s) not compared: larger than 64 KiB or unreadable)`. Charter and model marks are listed in the block of
every service whose owner subtree contains the addr (ORG.md marks in every block), and in the one-off block for the assignees' subtrees. A
retired agent's AGENT.md moved under `.retired/` is not followed (section 26).

## 8. One-off cases as root notes: the provenance rules

### 8.1 The write path: root's `feedback` accepts a one-off task

08 3.1 stores one-off verdicts as root notes on the task, written by the assistant, with no agent tool change. Root's existing `feedback`
(MCP root `feedback`, CLI `hirearchy feedback`, `Org.feedback`), all through `services.RuleClientFeedback.feedback`, gains a branch for
`actor == ROOT` and a task without `service`:
1. The task is one of root's sent tasks. With a `service`, today's service path runs unchanged; without one, the one-off path below; when no
   task root sent has that id, ONE-OFF-UNKNOWN (8.3).
2. `criterion` or `confirms` given: ONE-OFF-NO-LINK. A one-off has no contract, so a rejection names no criterion and answers no rejection.
3. `verdict` in `VERDICTS`; a `reject` needs a note; the note is at most `FEEDBACK_MAX` (1000) characters (the existing checks and texts).
4. The task has a result in root's received boxes (existing text). A verdict on a blocked or failed one-off result is accepted, as for
   services, and counted as a verdict not on a delivery.
5. The assignee still exists (`agents.exists(task.to)`); otherwise ONE-OFF-GONE: a quiet note needs a recipient.
6. The note is written exactly as a service verdict is: `sender.send(ROOT, task.to, FEEDBACK_HEADER + "\n\n" + (note or "accepted"),
   type="note", title=f'feedback on "{task.title}": {verdict}', reply_to=task.id, feedback=verdict, source=source, wake=False)`.

Agents' `feedback` is unchanged: an agent's non-service task is refused with today's text. No agent tool changes.

**The provenance rules from day one** (go/no-go item 6):
- `source` defaults to `relayed` on root's MCP `feedback` (its signature already says `source="relayed"`) and on `Org.feedback` (its
  `source=None` is stamped `relayed` by `dispatch.provenance_source`, unchanged). The CLI keeps its default `--source human`
  (`cli/_commands_services.py:143`), because the terminal is the user's own seat.
- The user's words are verbatim: the docstring and the skill say so; the product cannot check it (declared provenance, section 26).
- The reply names the next step (8.2). Because a one-off has no contract to fall back on, a relayed one-off verdict counts as no verdict in
  `quality`, and the reply says so.

### 8.2 The reply's next step (`reflection/_steps.py:TextServiceSteps.feedback_step`)

`feedback_step(note)` returns, for a verdict note on a one-off task, one of these texts, with no leading newline (MCP's `_step` adds the
newline after today's receipt line `feedback {verdict} recorded on {task_id} for {to} (message {id}, source {source}); it does not wake {to}`):
- relayed (accept or reject): `Recorded as relayed (your own reading): quality counts it as no verdict of the user. If the user said it,
  record their words, verbatim, with source="human".`
- human reject: `Next: if the user wants it redone, send it back with delegate(to="{to}", title=..., goal=<their corrections, in their
  words>, acceptance=<the criteria, verbatim>, revises="{task}", source="human"). A one-off task has no contract: no criterion changes.`
- human accept: `""`.
The CLI prints the same step after its own receipt line, as it does for service verdicts.

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
for the study harness (section 20), scripts, and the user who wants a playbook version's changed lines (section 7). In setup mode (no org
bound) the MCP tool returns `SetupMode.state()`, like `progress`.

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
`service`: `only this service`; `--json`: `the same data as JSON (with each playbook version's changed lines)`.

ROOT_INSTRUCTIONS (`SRC/mcp_server/_instructions.py`) gains one line, inserted after the line that reads
``  On a reject: `feedback` first, then ONE yes/no question naming an id, then the change (`define_service(answers=...)`).`` (the second line
of the "Services" bullet; the bullet's first line, `` - Services: `services` (check it before building a new org), `request`, `feedback`
(rate a delivery), `define_service`. ``, is 119 characters and stays as it is):
```
  `quality`: how the work went.
```
31 characters plus its newline: 32 characters more, so 2 597 raw (< 2 700 and < 2 800), 2 674 at the reference path (< 2 700) and 2 814 at a
200-character path (< 2 900), measured from today's 2 565 / 2 642 / 2 782. No line exceeds today's maximum of 120 characters. The budget
tests pin the totals, and a needle test pins the line.

### 9.2 The text (`SRC/progress/_quality_render.py`, pure)

Order: header, notes, one block per service root requests (top-level agents' services, by owner then name), the one-off block, the line for
nested services, the moved-past section. With `service`, only that service's blocks (every owner offering that name) and no one-off block.
In the template, `{...}` parts in braces are shown only when non-empty or non-zero; `|` separates alternatives.

```
Quality of the work you asked for (derived from the files, nothing stored; for you and the user, never for agents).
Thresholds: {the defaults | from ORG.md quality:} (tunable): alarms need {min_judged} judged cases; repeat: one id failing in {repeat_failures} of the last {repeat_window} judged cases; cost: a case above {cost_ratio}x its approved budget.
{each note of 6 and 16, one per line}

{service} (offered by {owner}; client: you, human; unit: case; contract v{c}, playbook v{p}; approved {budget} runs per request)
  cases: {n} (done {d}, failed {f}, blocked {b}, open {o}, stalled {s}){; {m} blocked and moved past without a verdict}
  first deliveries: {a} accepted, {r} rejected, {w} without a verdict{ ({x} superseded by a rework before a verdict)}{, {v} judged after a hand edit (neither)}{; {y} never delivered}
    {first-delivery line, one per case}
  judged by the user: {ratio(judged, deliveries)} deliveries; without a verdict: {u} case(s){ ({ids}): never counted as accepted}{ ({q} with only your own relayed verdict)}; hand-edited: {h}{ ({ids})}{; {k} judged after the edit: neither pass nor escape ({ids})}{ (compared with the team's current files: no org history)}
  {legacy verdicts (no source, counted as the user's, the 0a rule): {g}}{; }{verdicts not on a delivery (on a blocked or failed result, or before the done result): {z} ({ids})}
  escapes (the team reported done, then the user rejected it): {e | none (judged: {ratio(judged, deliveries)})}
    {R} case {case id}, signed off by {signer}: {cause text of 5.3}
  verifiers: none (every delivery was signed off by {owner} itself) | verifiers:
    {signer}: escapes {e} of {j} judged{ ({m} reviewer-miss, {u} untyped)}{; not its: {cg} contract-gap, {re} relayed-error, {co} relayed-carry-over}; PASS precision {ratio(j - e, j)}; its FAILs before delivery: {rc} re-check(s), {rw} author rework run(s)
  runs per case (spend = runs used, plus runs still out while a case is open or blocked; approved {budget}):
    {case id} "{title}": {spend} ({x.xx}x){, {k} in your relayed reworks}{, {c} not charged (model-service throttle)}; top-ups: {none | +{n} human rework {id}, +{n} your relayed rework {id}, +{n} rework {id} (tier not recorded), +{n} your grant {id}}{; window cut by a later request}
    {case id} "{title}": runs not counted ({reason of 4.1}); top-ups: ...
  alarms:
    repeat: {FIRES: {id} failed in {k} of the last {w} judged cases (cases {ids}) | no ({w} judged cases; counted: {ids or "none"}) | n/a ({k} of {min} judged cases)}{; not counted: {R}'s reading {ids} (not confirmed), ...}
    cost: {FIRES: case {id} {spend} of {budget} ({x.xx}x){, {k} in your relayed reworks}, ... | no (0 of {n} cases above {cost_ratio}x) | n/a ({k} of {min} judged cases)}{; skipped: {ids} ({budget 0 | runs not counted})}
  timeline (bar changes, UTC; marked, never used to split the counts):
    {YYYY-MM-DD HH:MM} {mark of section 7}
    {charter edits and model changes: unknown (...) | none}
  run attribution is by time window (08 3.3): {k} case(s) had their window cut by a later request{; their later runs count for that request}.
```
- **First-delivery lines**: `{case id}: rejected: "{words}"`, `{case id}: accepted: "{words}"`, `{case id}: accepted (no words)`, `{case id}:
  no verdict{ (superseded by {human rework | your relayed rework | rework} {id}{ (tier not recorded)})}`, `{case id}: judged after a hand edit
  (neither): the user's verdict came after the file was changed`, `{case id}: never delivered ({blocked | failed | open})`. The words are the
  decisive verdict's.
- **The legacy and not-on-a-delivery line** is shown when either count is above 0; its two parts are joined by `; `.
- **The no-history remark** on the `hand-edited` segment is shown when `h > 0` and the org has no history (`BarChanges.known` is false): P3
  then compared with the team's current files (0a.2 P3's no-history rule).
- **Charter and model line**: `unknown (...)` without history; `none` with history and no mark; absent when marks are listed.
- **Limits**: the 10 newest cases per block (`and {k} earlier case(s), counted above`), the 10 newest escapes, the 15 newest timeline marks,
  the 10 newest ids per list (`and {k} more`). Titles are root's own (`clip_line(title, 80)`); the user's words are quoted only for counted
  human-tier verdicts, in the first-delivery lines (`clip_line(words, 160)`, the words `FeedbackWords.feedback_text` returns without the fixed
  header; the escape lines show the cause, which names what the rule read). Agent-written text (lessons, playbook reasons and lines, result
  bodies, agents' task titles, file names) never appears, and artifact paths and model names go through `shown_name` (section 15, I8).

**The one-off block** has the heading `One-off tasks you gave (client: you, human; unit: case; approved budget: each task's own)` and the
same lines as a service block, with these variants: the runs header reads `runs per case (spend = runs used, plus runs still out while a
case is open or blocked; approved: each task's own budget):` and each case line reads `{case id} "{title}" ({assignee}): {spend} of
{approved} ({x.xx}x)...`; an escape line reads `rejected case {case id} ({assignee}), signed off by {signer}: {cause}` (a one-off rejection is
no `R<k>`); the repeat line reads `repeat: does not apply (one-off tasks name no criterion ids)`; the timeline has top-up marks and the
assignees' charter and model marks (no contract or playbook mark). Without any one-off task the block is `One-off tasks you gave: none.` when
a service exists, and absent otherwise.

**Nested services** are one line each under `Services your agents request (the client is an agent: its verdicts are hypotheses, never
counted):` as `- {service} (offered by {owner}; client {client}): {n} case(s), {d} delivered, {v} agent verdict(s)`.

**The moved-past section**:
```
Blocked tasks moved past without a verdict (while one stays blocked, its assignee's later results return no runs):
  {addr} {holds {n} run(s) | holds no run (budget {b}) | holds an unknown number of runs ({error})}:
    task {id} from {you ("{title}") | {sender}}, blocked {YYYY-MM-DD HH:MM}: {moved past: {you have | {sender} has} sent {addr} {j} task(s) since | not moved past (nothing sent since)}
```
one agent line per agent with a left-blocked task, then one line per held task of that agent, oldest block first; or `Blocked tasks moved
past without a verdict: none.` An org with no case at all: `No cases yet: you have requested no service and given no task.` followed by the
moved-past section.

**A record that cannot be read** (13): `{service} (offered by {owner}): cannot be read ({error}).` or `One-off tasks you gave: cannot be read
({error}).`; the other blocks render.

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
  verifiers:
    lead/reviewer: escapes 0 of 5 judged; not its: 2 contract-gap; PASS precision 5 of 5; its FAILs before delivery: 2 re-check(s), 2 author rework run(s)
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
  run attribution is by time window (08 3.3): 0 case(s) had their window cut by a later request.

One-off tasks you gave: none.

Blocked tasks moved past without a verdict: none.
```
Every figure above is read from E3's kept files (the replay pins them): the runs (12, 15, 14) equal the case totals 0a.1 6.1 states for E3;
the 10 relayed runs are the charged logs of `run-logs/` with stamps from `...-root-248f` to the end of the window; the FAIL counts are E3's
health line (`re-checks after a FAIL 2 (author rework runs 2)`). Every one of the six deliveries was signed off by lead/reviewer; 207b's
first delivery has no verdict, so 5 are judged; both escapes are attributed `not its`, so PASS precision is 5 of 5 and health reads
`escapes 0 of 5 judged` (section 10). The hand-edited count has no no-history remark because it is 0 (E3's deliverable folder is rewritten
to a missing one: 19.1).

**E4 s1r's files, excerpt** (values in angle brackets are pinned by the replay, not restated here):
```
weekly-memo (offered by lead; client: you, human; unit: case; contract v5, playbook v2; approved 15 runs per request)
  cases: 3 (done 2, failed 0, blocked 1, open 0, stalled 0); 1 blocked and moved past without a verdict
  first deliveries: 0 accepted, 1 rejected, 2 without a verdict
    20261022T182945409755-root-ed94: rejected: "<the user's words>"
    20261022T191407596413-root-114d: no verdict
    20261022T192724706946-root-2efa: no verdict
  judged by the user: 1 of 3 deliveries; without a verdict: 2 case(s) (20261022T191407596413-root-114d, 20261022T192724706946-root-2efa): never counted as accepted; hand-edited: 3 (20261022T182945409755-root-ed94, 20261022T191407596413-root-114d, 20261022T192724706946-root-2efa) (compared with the team's current files: no org history)
  escapes (the team reported done, then the user rejected it): 1
    R1 case 20261022T182945409755-root-ed94, signed off by lead/checker: contract-gap (the user's answer, link 20261022T190014222948-root-1753, names C9, which contract v1 of the task did not have)
  verifiers:
    lead/checker: escapes 0 of 1 judged; not its: 1 contract-gap; PASS precision 1 of 1; its FAILs before delivery: 1 re-check(s), 1 author rework run(s)
  runs per case (spend = runs used, plus runs still out while a case is open or blocked; approved 15):
    20261022T182945409755-root-ed94 "<title>": 25 (1.67x), 5 in your relayed reworks; top-ups: +6 your relayed rework 20261022T184712524029-root-9ce9, +6 human rework 20261022T190015448581-root-3559; window cut by a later request
    20261022T191407596413-root-114d "<title>": 7 (0.47x); top-ups: none
    20261022T192724706946-root-2efa "<title>": 9 (0.60x); top-ups: none
  alarms:
    repeat: n/a (1 of 3 judged cases)
    cost: n/a (1 of 3 judged cases)
  timeline (bar changes, UTC; marked, never used to split the counts):
    2026-10-22 18:58 contract v2 (root): adds C8, C9: C9 confirmed (link 20261022T190014222948-root-1753), C8 not confirmed
    2026-10-22 19:03 playbook v2 (lead): admitted (c) on <ids>: <k> changed line(s): <w> the cited criteria's own words, <b> beyond them
    ... <v3, v4 (removes C9, adds C11), v5: every added criterion not confirmed>
    charter edits and model changes: unknown (no org history: the organization is not a git repository, or git is missing)
  run attribution is by time window (08 3.3): 1 case(s) had their window cut by a later request; their later runs count for that request.

Blocked tasks moved past without a verdict (while one stays blocked, its assignee's later results return no runs):
  lead holds 12 run(s):
    task 20261022T190015448581-root-3559 from you ("Rework memo 2026-10-05: Summary line first, Sam's CI due date"), blocked 2026-10-22 19:11: moved past: you have sent lead 2 task(s) since
  lead/writer holds 4 run(s):
    task 20261022T191728726797-lead-e679 from lead, blocked 2026-10-22 19:18: moved past: lead has sent lead/writer 1 task(s) since
    task 20261022T193406984560-lead-808c from lead, blocked 2026-10-22 19:35: not moved past (nothing sent since)
```
Case ed94's window is cut: its latest task (3559) is blocked, so the window runs to the next request, 114d. The writer's third blocked task,
`...-lead-0d54`, is not listed: `...-lead-cc98` revises it, so `mail.moved_past` released it. The held figures 12 and 4 are s1r's own final
`status` (`final-services-progress-status-health.txt` lines 31 and 34), and the FAIL counts its final health line for the checker (line 41).

**A5's files, the one-off block** (A5 kept no run log, so its runs read 0: section 19):
```
One-off tasks you gave (client: you, human; unit: case; approved budget: each task's own)
  cases: 1 (done 1, failed 0, blocked 0, open 0, stalled 0)
  first deliveries: 0 accepted, 0 rejected, 1 without a verdict (1 superseded by a rework before a verdict)
    20261017T214038108044-root-f768: no verdict (superseded by rework 20261017T215450859628-root-dfe0 (tier not recorded))
  judged by the user: 0 of 3 deliveries; without a verdict: 1 case(s) (20261017T214038108044-root-f768): never counted as accepted; hand-edited: 0
  escapes (the team reported done, then the user rejected it): none (judged: 0 of 3)
  verifiers: none (every delivery was signed off by lead itself)
  runs per case (spend = runs used, plus runs still out while a case is open or blocked; approved: each task's own budget):
    20261017T214038108044-root-f768 "Competitor analysis of self-hosted note-taking apps" (lead): 0 of 22 (0.00x); top-ups: +4 rework 20261017T215111184137-root-00cd (tier not recorded), +4 rework 20261017T215450859628-root-dfe0 (tier not recorded), +3 your grant 20261017T215533405230-root-7620
  alarms:
    repeat: does not apply (one-off tasks name no criterion ids)
    cost: n/a (0 of 3 judged cases)
  timeline (bar changes, UTC; marked, never used to split the counts):
    2026-10-17 21:51 top-up +4 run(s) to case 20261017T214038108044-root-f768: rework 20261017T215111184137-root-00cd (tier not recorded)
    2026-10-17 21:54 top-up +4 run(s) to case 20261017T214038108044-root-f768: rework 20261017T215450859628-root-dfe0 (tier not recorded)
    2026-10-17 21:55 top-up +3 run(s) to case 20261017T214038108044-root-f768: your grant 20261017T215533405230-root-7620
    charter edits and model changes: unknown (no org history: the organization is not a git repository, or git is missing)
  run attribution is by time window (08 3.3): 0 case(s) had their window cut by a later request.
```
f768's first delivery (`...-lead-463e`, 21:54:32) came after the rework `...-root-00cd` (21:51:11, sent while f768 was blocked), so the task
that superseded it is `...-root-dfe0` (21:54:50), the first task sent after it. Both reworks revise f768, so the chain is f768, 00cd, dfe0.

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
  "thresholds": {"cost_ratio": "1.25", "min_judged": 3, "repeat_failures": 2, "repeat_window": 3, "source": "defaults"},
  "notes": [],
  "services": [{
    "owner": "lead", "service": "weekly-meeting-memo", "client": "root", "client_kind": "human", "unit": "case", "error": "",
    "contract": 3, "playbook": 1, "budget": 15,
    "cases": [{"id": "20261021T152347923195-root-dd87", "state": "done", "stalled": false, "tasks": 2, "runs": 12, "spend": 12, "ratio": 0.8,
               "relayed_runs": 0, "credited": 0, "cut": false, "runs_unknown": "",
               "top_ups": {"granted": 0, "human": 6, "relayed": 0, "unrecorded": 0},
               "first": {"outcome": "rejected", "tier": "human", "superseded_by": null}}],
    "deliveries": {"total": 6, "judged": 5, "superseded": 1, "without_verdict": [], "relayed_only": [], "hand_edited": [], "voided": [],
                   "legacy_verdicts": 0, "not_on_a_delivery": []},
    "escapes": [{"assertion": "R1", "case": "20261021T152347923195-root-dd87", "task": "20261021T152347923195-root-dd87", "signer": "lead/reviewer",
                 "cause": "contract-gap", "rule": "words", "rules": ["words"], "detail": ["always"], "also": [], "before_verdict": "",
                 "attribution": "not its", "class": null}],
    "verifiers": [{"addr": "lead/reviewer", "judged": 5, "escapes": {"counted": {}, "not_its": {"contract-gap": 2}},
                   "pass_precision": [5, 5], "rechecks": 2, "rework_runs": 2}],
    "alarms": {"repeat": {"state": "no", "judged": 3, "subjects": {"C11": 1, "R1": 1, "R2": 1}, "not_counted": {"R1": ["C6", "C3"]}},
               "cost": {"state": "no", "judged": 3, "cases": [], "skipped": []}},
    "timeline": [{"kind": "contract", "when": "2026-10-21T15:27:53Z", "version": 2, "by": "root", "adds": ["C9", "C10"], "removes": ["C3", "C6"],
                  "basis": "legacy", "confirmed": []}],
    "history": {"known": false, "truncated": false, "skipped": 0}
  }],
  "one_off": null,
  "nested": [],
  "moved_past": []
}
```
`state` values: `fires`, `no`, `n/a`, `does not apply`. `ratio` is `null` when the approved budget is 0 or the runs are not counted.
`one_off` is `null` when root gave no one-off task. A playbook mark carries `cited`, `lines`, `lines_more` and `agent_written` (section 7).
`cost_ratio` is the decimal as written (a string), so the JSON is exact.

## 10. Health rebased on typed escapes (go/no-go section 3, F-E3-10)

The cause typing and the attribution are built once, in `reflection`, and health reuses them through a consumer-owned port; health still may
not import `reflection` (graph 2.2), so the conversion lives in `app`.

- `SRC/health/_ports.py`: `class SignedDelivery(NamedTuple): signer: str; judged: bool; escape: bool; counted: bool; cause: str` (`cause`
  is `""` unless an escape; `counted` is the attribution: true for `reviewer-miss` and `untyped`), `class Signed(NamedTuple): items:
  tuple[SignedDelivery, ...]; unknown: str` and `class SignedDeliveries(Protocol): def deliveries(self, owner: str) -> Signed`.
  `EscapeCounts` gains `not_its: tuple[tuple[str, int], ...] = ()` and `unknown: str = ""`.
- `SRC/app/_signed_deliveries.py:CaseSignedDeliveries(records: CaseRecords)` converts `records.deliveries(owner)` (an `OwnerDeliveries`: the
  deliveries of the owner's services' cases and of root's one-off cases assigned to it, and `unknown`) into `Signed`, calling
  `reflection.attribution(cause)` for each escape.
- `CaseRecords.deliveries(owner)` reads no deliverable folder and counts no runs (hand edits are a quality-view input only: D7). Per service of
  the owner it builds the cases and the carried criteria sets; when the contract or its stored versions cannot be read (`OrgError`/`OSError`
  from `ServiceCatalog.read_contract` or `ContractVersions.versions`), it builds that service's cases from the mailboxes alone (the chain
  builder with `since=None`), types every escape `Cause("untyped", "unreadable", (clip_line(error, 200),))` (counted: the conservative side,
  so no escape disappears from a verifier's count) and adds `{service}: {error}` to `OwnerDeliveries.unknown`. A mailbox that cannot be read
  raises, as health does today.
- `SRC/health/_escapes.py:MailEscapeCounter` gets `deliveries: SignedDeliveries` as its 5th collaborator and loses `_deliveries`; `counts(addr)`
  keeps today's composition (the owner's deliveries, plus the parent's deliveries `addr` signed off when the parent is not root) and:
  - `judged` = deliveries with `judged`: a human-tier verdict after the delivery's `done` result (today's timing rule), now including relayed
    reworks' deliveries the client judged (F-E3-10: a client accept on a relayed rework counts as a judged delivery of its case) and one-off
    deliveries (0a's "until Phase 0b gives one-off tasks verdicts");
  - `escapes` = judged deliveries with `escape` and `counted`: any human-tier reject after `done` (today's rule, so a reject followed by an
    accept on the same delivery stays an escape) whose cause is attributed `counted`;
  - `not_its` = the other escapes by cause: `contract-gap`, `relayed-error`, `relayed-carry-over`;
  - `unknown` = `Signed.unknown` of the owners read;
  - `rechecks`, `rework_runs`: unchanged.
- `SRC/health/api.py:AgentHealth` gains `not_its: dict[str, int] = field(default_factory=dict)` and `causes_unknown: str = ""`; `to_dict`
  carries both.
- **Texts, root only.** `HealthRenderer.render_text(health, *, causes: bool = False)` (the keyword is new; `TextHealthRenderer` and the fakes
  implement it). With `causes=True` the report segment becomes `escapes {e} of {judged} judged (+{k} not its: {n} contract-gap, {m}
  relayed-error, {p} relayed-carry-over){; causes unknown ({unknown})}, re-checks after a FAIL ...` (zero parts and empty parentheses left
  out). MCP `health` passes `causes=(me == ROOT)` (`mcp_server/_tools_status.py`); the CLI `health` passes `causes=True`. Agents' health text
  and every `low_quality` reason (built in `_analyzer.py`, read by agents in MCP `health` and by managers in the review cycle's notes,
  `review/_planner.py:68`) keep today's wording; only their numbers change. `max_escape_ratio` and `min_judged_for_quality` are unchanged.
  E3's reviewer reads `escapes 0 of 5 judged (+2 not its: 2 contract-gap)` for root, `escapes 0 of 5 judged` for an agent, where both read
  `escapes 2 of 4 judged` before.
- **Behaviour changes, named:** escapes typed `contract-gap`, `relayed-error` or `relayed-carry-over` no longer count against a verifier;
  accepted relayed reworks and one-off deliveries now count as judged; deliveries of a retired service drop out (cases need a live contract,
  as in `services`), while a continued service keeps them (0a.2 5.10); a reject followed by an accept stays an escape (unchanged). Health
  counts a verdict the quality view voids for a hand edit (it reads no folder: D7), so the two can differ by the deliveries the view lists as
  `judged after the edit`.

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

- `api.py`: `Case` gains `credited: int = 0`, `relayed_runs: int = 0`, `top_ups: TopUps = TopUps()`, `cut: bool = False`, `runs_unknown: str =
  ""` (all defaulted); new frozen dataclasses `TopUps`, `Delivery`, `Cause`, `ContractMark`, `PlaybookMark`, `CharterMark`, `ModelMark`,
  `TopUpMark`, `ServiceRecord`, `OwnerDeliveries`, `RepeatAlarm`, `CostAlarm`, `QualityThresholds`; the type alias `Mark`; constants `CAUSES`,
  `FAILURE_CLASSES`, `LASTING_WORDS`, `QUALITY_DEFAULTS`; pure functions `signer_of`, `deliveries_of`, `unjudged_cases`, `not_on_a_delivery`,
  `judged_cases`, `cause_of`, `attribution`, `failure_class`, `repeat_alarm`, `cost_alarm`, `over_cost`, `quality_thresholds`;
  `CaseHistory.one_off_cases()` (3 -> 4 methods); the `DeliverableFinding` fields `written: int = 0`, `settled: bool = False`;
  `DeliverableChecks.findings(actor, service=None, *, settled=False)`. `shown_name` (already imported into `api.py` from `_deliverables`) is
  added to `__all__`, so `reflection/__init__.py` re-exports it (R1) and `progress._quality_render` can use it.
- New Protocol `CaseRecords` (2 methods):
  ```python
  @runtime_checkable
  class CaseRecords(Protocol):
      def records(self, service: str | None = None) -> list[ServiceRecord]:
          """Root's view of the record: one per service of every agent (top-level first, then nested, each by owner and name; only those named
          ``service`` when given) and, without ``service``, one for root's one-off tasks (``service == ""``), with cases, deliveries (hand edits
          read from the deliverable folders by one P3 call), assertions, typed escapes and the timeline. A record that cannot be read carries
          ``error`` and nothing else. ``OrgError`` for a ``service`` no agent offers; ``OrgError``/``OSError`` when the agents cannot be
          listed."""
      def deliveries(self, owner: str) -> OwnerDeliveries:
          """Every delivery of ``owner``'s services' cases and of root's one-off cases assigned to ``owner``, with signer and cause, without
          reading any deliverable folder or run log (health's input); a service whose contract cannot be read is typed ``untyped`` and named
          in ``unknown``. ``OrgError``/``OSError`` when a mailbox cannot be read."""
  ```
- `ServiceRecord` (frozen): `owner, service, client, client_kind, unit = "case", error: str = "", contract: int = 0, playbook: int = 0, budget:
  int = 0, cases: tuple[Case, ...] = (), deliveries: tuple[Delivery, ...] = (), assertions: tuple[Assertion, ...] = (), escapes:
  tuple[tuple[Delivery, Cause], ...] = (), timeline: tuple[Mark, ...] = (), history: BarChanges = BarChanges(), hand_edits: str = ""` (`""`,
  or the error text when the P3 call failed).
- `Delivery` (frozen): `case: str, task: Message, result: Message, step: int, signer: str, verdicts: tuple[Verdict, ...]` (every tier, on the
  delivery, oldest first), `superseded: str = ""`, `edited_at: int = 0`, `edited: bool = False`; properties `counted: tuple[Verdict, ...]`,
  `voided: tuple[Verdict, ...]`, `judged: bool`, `escape: bool`, `decisive: Verdict | None`, `outcome: str`.
- `OwnerDeliveries` (frozen): `deliveries: tuple[Delivery, ...]`, `causes: tuple[Cause | None, ...]` (parallel), `unknown: str`.
- `_cases.py`: one private chain builder serves `cases` and `one_off_cases` (`since`, `count_runs`); it fills the new fields from one
  `RunCounter.stamps` call per case, and `runs_unknown` from `agents.exists` and `CharterReader.charter(addr)[0].get("created")`.
- `_runs.py`: `LogRunCounter.stamps` (4.2); `runs_between` counts the uncredited stamps.
- `_ports.py`: `RunCounter.stamps`; `ContractVersions` (`versions(owner, name, kind)`, satisfied by `services.ServiceStore`); `BarHistory`
  (`changes(addrs) -> BarChanges`) and `BarChanges`.
- New modules: `_records.py` (`DerivedCaseRecords(history, catalog, agents, charters, mail, versions, bars, deliverables)`), `_causes.py`,
  `_quality_rules.py` (deliveries, signers, unjudged, alarms, thresholds), `_marks.py` (contract and playbook marks).
- `_steps.py`: `feedback_step` for one-off verdict notes (8.2). `_deliverable_checks.py`: `settled`, `written`. `_evidence.py`: `_words_of`
  becomes `services.criterion_words` (no behaviour change).
- `testing.py`: `FixedCaseRecords`, `NoBarHistory`, `FixedBarHistory`; `IMPLEMENTATIONS[CaseRecords]`.

### 12.2 `services`

- `api.py`: `BASE_DELIVERED_HEADING = "## Base: the version the client judged"`, `BASE_LATEST_HEADING = "## Base: the current version"`
  (the literals of `_request.py` lines 50 and 68 move here, byte-identical, and `_request.py` uses the constants; `BASE_HEADING` stays);
  `criterion_words(line, criteria) -> str | None`; the `ServiceCommands.feedback` docstring (one-off tasks).
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

- `health`: section 10 (`_ports.py`, `_escapes.py`, `api.py`, `_render.py`, `testing.py`).
- `progress/api.py`: `QualityReport` Protocol (`quality_text`, `quality_data`). `_ports.py`: `FailCounts` (`fails(addr) -> tuple[int, int]`) and
  `ConfigSource` (`config() -> JsonObject`). New `_quality.py` (`DerivedQualityReport(records: CaseRecords, states: TaskStates, teams: TaskTeams,
  tasks: TaskQuery, mail: MailboxReader, budgets: BudgetQuery, agents: AgentDirectory, fails: FailCounts, config: ConfigSource)` and the pure
  `held_tasks` and `left_blocked`) and `_quality_render.py` (the text and the JSON; `ratio`). `testing.py`: `FixedQualityReport`.
- `mcp_server`: `_tools_quality.py` (new), the root `feedback` docstring (`_tools_services.py`), the ROOT_INSTRUCTIONS line (9.1), and
  `_tools_status.py` passing `causes=(me == ROOT)` to the health renderer; `testing.py`'s renderer fake takes the keyword.
- `cli`: `QualityCommand` in `_commands_views.py`; `HealthCommand` passes `causes=True`; the `feedback` help (`_commands_services.py`).
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
| `quality(service=x)` | no agent offers `x` | yes | `OrgError`: ``no service named `{x}`: the services are {names or "none"}. Call quality() without a service for everything.`` | tool call event with the error, as for every tool |
| `quality(service=x)` | `x` longer than 80 characters or not a string | yes | `OrgError`: `service is a service name (at most 80 characters): {clipped}` | same |
| `records()` | the agents cannot be listed | yes (retry) | the `OrgError`/`OSError` propagates: no record can be built | tool call event with the error |
| one service's record | `OrgError`/`OSError` from the catalog, the store or a mailbox while building it | yes (other records build) | `ServiceRecord(error=...)`; the block becomes `{service} (offered by {owner}): cannot be read ({error}).` | no extra log |
| root's one-off record | same | yes | `One-off tasks you gave: cannot be read ({error}).` | no |
| the P3 call | the deliverable checks never raise for a folder, file or history (0a.2 6.3); a catalog or mailbox error raises | yes | every record gets `hand_edits = error`; the segment reads `hand-edited: unknown ({error})` and no verdict is voided | no |
| thresholds | ORG.md does not parse (`OrgError(UNREADABLE)` from `ReadableOrgConfig`) | yes | defaults and the note of section 6 | no |
| thresholds | a `quality:` value fails validation, or a key is unknown | yes | its default (or nothing) and the note | no |
| stalled states, held runs, FAIL counts | `OrgError`/`OSError` from `TaskStates`, `BudgetQuery`, `FailCounts` | yes | the part reads `unknown ({error})` (`stalled unknown`, `holds an unknown number of runs ({error})`, `its FAILs before delivery: unknown`) | no |
| moved-past section | a mailbox of an agent cannot be read | yes | that agent's line reads `{addr}: blocked tasks cannot be read ({error})` | no |
| timeline git reads | no repository, no git, a timeout, the bound, a version above 64 KiB | yes | `known=False` (the unknown line), `truncated` or `skipped` | no (git errors are never raised: `OrgHistory`'s rule) |
| CLI `quality` | as above; no organization found | yes | the text, or the CLI's existing "no organization" error and exit code | the CLI's own handling |
| one-off `feedback` | 8.3's refusals, the existing validation | yes | `OrgError` with the text; nothing written | tool call event |
| one-off `feedback` | the note's delivery fails (`OSError`) | yes (retry) | the error; the pipeline writes the file last and atomically, so nothing half-written | as today |
| one-off `feedback` reply step | `feedback_step` raises `OrgError`/`OSError` | yes | no step (MCP `_step`'s rule, unchanged) | no |
| health `counts` | a mailbox cannot be read | as today | the error propagates to the health caller (MCP tool error, CLI error, the review cycle as today) | as today |
| health `counts` | a service's contract or stored versions cannot be read | yes | that service's escapes are `untyped` (counted); root's text adds `causes unknown ({service}: {error})` | no |
| `OrgHistory.changes` | anything | n/a | `None` or `[]`, never raises | no |

Errors are never swallowed silently: each one becomes visible text in the part it affects, with the error's words (`clip_line(str(exc), 200)`).

## 14. Validation of external inputs

| Input | Required | Type and limits | On failure |
|---|---|---|---|
| MCP `quality.service` | optional | `str`, stripped, 1-80 characters; empty means none | `OrgError` (13) |
| CLI `quality [service]` | optional | as MCP | the same text, exit code as other CLI errors |
| CLI `--json` | optional | flag | argparse |
| ORG.md `quality:` | optional | mapping | not a mapping: ignored, note |
| `quality.<unknown key>` | - | - | ignored, note |
| `quality.min_judged` | optional | `int` (not `bool`), integral `float`, or digit string; >= 1 | default 3, note |
| `quality.repeat_window` | optional | as above; >= 1 | default 3, note |
| `quality.repeat_failures` | optional | as above; 1 <= value <= `repeat_window` (after `repeat_window` is settled) | default 2 (clamped to the window, with its note, when the window is smaller), note |
| `quality.cost_ratio` | optional | `int`/`float` (not `bool`, finite) or decimal string `^\d+(\.\d+)?$`; > 0; held as `Fraction(str(value))` | default 1.25, note |
| `feedback(task_id)` for a one-off | required | root's sent task without `service`, with a result | ONE-OFF-UNKNOWN / today's "no result yet" |
| `feedback(verdict, note)` | required / required for reject | `accept`/`reject`; note at most 1000 characters | today's texts |
| `feedback(criterion, confirms)` on a one-off | must be absent | - | ONE-OFF-NO-LINK |
| `feedback(source)` | optional | `human` or `relayed` (`provenance_source`, S2); default `relayed` on MCP and `Org`, `human` on the CLI | today's text |
| message files, contract and playbook versions | read only | the existing parsers; an unreadable message is left out by the index (unchanged) | - |
| git output | read only | records that do not parse are skipped; paths are validated before the call (`is_history_path`) | - |

## 15. Invariants and their owners

| # | Invariant | Owner | Why that layer |
|---|---|---|---|
| I1 | No count reads team-written or relayed text as client evidence | `reflection`'s pure rules (`deliveries_of`, `cause_of`, `repeat_alarm`, `judged_cases`) filter on `verdict_tier(m) == "human"`, human-tier links and the verdict-after-the-result rule | one place derives every case for `quality`, health and `services`; `progress` and health only render or compose |
| I2 | No new stored state | the architecture tests (`ownership.py` unchanged) and a test that calls `DerivedQualityReport.quality_text`/`quality_data` and `HealthAnalyzer.org_health` with `TextHealthRenderer.render_text` directly over an fs world (no MCP or CLI layer, so no tool-call event is written) and asserts every file's path, bytes and mtime unchanged | storage rules are enforced where every writer is listed |
| I3 | A zero denominator is never a pass | `progress._quality_render.ratio` and the alarm states (`n/a`) | the renderer is the only place rates become text |
| I4 | One spend function | `reflection.case_spend`, called by `case_total` and `cost_alarm` (a test asserts equal spend on the same case) | 0a.1 put it in reflection for this purpose |
| I5 | One cause typing and one attribution | `reflection.cause_of` and `reflection.attribution`, read by the view's verifier line directly and by health through `CaseSignedDeliveries` (a test on one world compares, per verifier, the view's counted and `not its` escapes with health's `escapes` and `not_its`; hand-edited deliveries are left out of that world, D7) | health may not import reflection; the adapter only converts |
| I6 | One-off verdicts default to `relayed` on root's MCP tool and `Org` | `dispatch.provenance_source` (existing) and MCP root `feedback`'s default; the CLI's `human` default is the user's own seat | the sender is the single layer every write passes |
| I7 | `quality` is root's only, and so is health's `not its` split | `mcp_server` (`root_only` group; `causes=(me == ROOT)`) and the surface goldens | the factory decides each identity's tools and texts |
| I8 | Agent-written text never enters root's view verbatim | `progress._quality_render` (only root's titles and human-tier words are quoted; paths and model names through `shown_name`; evidence ids filtered; playbook lines only in `--json`, marked `agent_written`) | the renderer is the boundary between files and root's prompt |
| I9 | The core is domain-agnostic | `reflection.api` vocabularies; a needle test over the new production modules matches the words `memo`, `meeting`, `code`, `test`, `pull request`, `ticket`, `research` case-insensitively as whole words (`\b...\b`, identifiers split on `_` and case changes) in identifiers and string literals | the vocabularies are the extension points packs replace |

## 16. Zero denominators, empty cases, ORG.md and git

- **Rates**: judged coverage, PASS precision and every `k of n` use `ratio`; with `n == 0` they read `n/a (0 of 0)`. A ratio of spend to a
  budget of 0 or below reads `n/a (budget 0)`, and the case is named among the cost alarm's skipped cases.
- **Alarms** below `min_judged` judged cases read `n/a ({k} of {min} judged cases)`, never `no`; `no` needs the evaluation to have run.
- **A service with no request**: `cases: 0 (...)`; every line after it reads `none` or `n/a (0 of 0)`; alarms `n/a (0 of 3 judged cases)`.
- **No service and no one-off task**: the empty sample of 9.3; root's one-off block is left out when root gave none (`One-off tasks you gave:
  none.` when a service exists).
- **A team whose runs cannot be counted** (4.1): the case line reads `runs not counted ({reason})`, its ratio is `null`, and the cost alarm
  skips it by name.
- **ORG.md that does not parse**: section 6's defaults and note; every other count still renders (none reads ORG.md, and the auxiliary parts
  degrade per section 13).
- **No git history** (no repository, git missing): the timeline's contract, playbook and top-up marks still render (they come from
  `history/` files and mailboxes); charter and model marks read `unknown (...)`; hand edits are compared with the team's current files, which
  is 0a.2 P3's no-history rule, and the `hand-edited` segment adds `(compared with the team's current files: no org history)` whenever it
  counts at least one (9.2).

## 17. The four review checks, and how each passes

1. **Zero denominators and empty cases.** Every rate goes through `ratio` (`n/a (0 of 0)`); alarms below the minimum read `n/a (k of 3
   judged cases)` and never `no`; a 0 budget reads `n/a (budget 0)`; an empty service, an empty org, a corpus without run logs and a team whose
   runs cannot be counted each have a defined text (16, 9.3). Tests: a parametrized renderer test over every rate with `n == 0`; alarm tests at
   0, 1 and 2 judged cases; the empty sample as a golden.
2. **No count reads team-written or relayed text as client evidence.** Section 4 lists each count with its tier filter: verdicts count only at
   `human` tier and only on the delivery they follow (a verdict on a blocked result is never the accept of a later delivery); links count
   only from human-tier link notes (`Verdict.confirmed`, `links_tier == "human"`); the rejection's own `criterion` (root's reading) is relayed
   and only listed as `not counted`; lessons, playbook text, review reports and results are never read for a count, except the artifact
   lists (`## Artifacts`), which the carry-over rule reads only to compare two of the team's own deliveries, never as client evidence (its
   limit is declared in section 26); agent-client verdicts are counted apart and never alarm. Tests: for each count, a world with the same
   events stamped `relayed` and `agent` gives 0 human-tier counts; a lesson that says "the client wants X" changes nothing; a human accept on a
   blocked result followed by a done result leaves that delivery without a verdict (E's 550c, 19.3 E-1).
3. **Every count is derivable from existing files, with no new stored state.** Section 4 names the files of every count; 12.6 and I2: no
   writer is added and the org tree is byte-identical before and after `quality` and `health` (test). The only new write is the one-off verdict
   note, an existing file kind through the existing writer.
4. **Domain-agnostic core.** The vocabulary is cases, deliveries, tiers, client kind, unit, failure classes and causes (4.6, 5); the rules read
   message fields, contract versions, artifact lists and base headings, all generic; `LASTING_WORDS` are English words, not domain terms, and
   `cause_of` takes them as an argument so a pack passes its own in Phase 3. I9's needle test fails on a domain word in the new modules. The
   samples' memo titles are data.

## 18. Testability and the test plan

### 18.1 Unit tests (pure functions and fakes)

- `reflection`: `deliveries_of` (the verdict-after-the-result rule: a verdict on a blocked result that later turns done; superseded only by a
  task sent after the result; counted and voided around an edit with verdicts before and after it; `written == 0`), `not_on_a_delivery`,
  `signer_of` (moved tests from health), `unjudged_cases`, `judged_cases`, `cause_of` (one test per rule, every precedence pair, `also` with a
  same-type later rule (empty) and a different-type one, `rules`, `before_verdict`, legacy reworks, a `none` link, a "same as R<j>" link
  resolved, a custom `lasting`), `attribution`, `failure_class`, `repeat_alarm` (window, subjects from `confirmed`, `about` and R links,
  unconfirmed links, a reject not on a delivery, one-off), `cost_alarm` and `over_cost` (exact equality at 1.25 x 20 = 25, 0 budget, runs not
  counted, open and blocked spend), `quality_thresholds` (each validation rule, unknown keys, numeric strings, the clamp note), the playbook
  mark counts against the cited criteria (P1's own replays as fixtures), the one-off chain builder, `runs_unknown` (assignee retired; a
  charter `created` after the head task), `RunCounter.stamps` (credited stems, boundaries of the relayed interval).
- `progress`: `ratio`; the renderer over `FixedCaseRecords` (every line and variant of 9.2, limits, `shown_name` on paths, the no-history
  remark, a record with `error`); `held_tasks` and `left_blocked` (mail.moved_past released, superseded, verdict after the block, a later task
  inside the chain, a held task with nothing sent since, budget 0).
- `services`: the one-off branch and its three refusals; `criterion_words` (P1's tests keep passing).
- `snapshots`: `GitOrgHistory.changes` parsing (sha1 and sha256 ids, a malformed record, invalid paths dropped, no repository).
- `health`: `MailEscapeCounter` over a fake `SignedDeliveries` (counted and `not its` causes, F-E3-10's relayed accept, one-off deliveries,
  reject then accept, `unknown`); `TextHealthRenderer` with `causes` true and false.

### 18.2 Contract, integration and e2e tests

- Contract suites (R8): `test_contract_case_records.py` (reflection; `DerivedCaseRecords` over the fs world and `FixedCaseRecords`, including
  one P3 call per `records()`, a record with `error`, and `deliveries()` with an unreadable stored version), `test_contract_quality_report.py`
  (progress), the `OrgHistory` suite extended with `changes`, the `DeliverableChecks` suite extended with `settled` and `written`.
- Integration (fs world, in-process MCP and CLI): one-off `feedback` through MCP root, CLI and `Org.feedback` (relayed default on MCP and
  `Org`, human default on the CLI, the refusals, the reply steps without a doubled newline); `quality` through MCP root (absent for agents:
  the surface goldens) and the CLI (`--json` keys, playbook lines only there); health's text for root (with `not its`) and for an agent
  (without), and its JSON with `not_its` and `causes_unknown`; ORG.md that does not parse; an org that is a git repository with a charter
  edit, a `default_model` change and an `effort` change written through the product's `DEFAULT_CONFIG` (the timeline marks), and the same org
  without `.git`.
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

### 19.1 The replay kit (`TESTS/testkit/org_replay.py` and `TESTS/testkit/org_replay_manifest.py`, test-only)

`materialize(corpus, root, variant=None) -> Path` builds an organization directory from a corpus's kept files, read-only from the repository
(`testkit.REPO / "studies" / ...`), following the corpus's **manifest** (`org_replay_manifest.MANIFESTS[corpus]`, plain data, one entry per
corpus E, E2, A5, E3, E4-s1r, E4-s2r, E4-s3). A manifest pins:
- `evidence`: the evidence directory;
- `boxes`: each kept message folder with the address and box it holds. E and E2: `msgs/root-sent` (root, sent), `msgs/lead-sent` (lead,
  sent), `msgs/writer-sent` (lead/writer, sent), `msgs/reviewer-sent` (lead/reviewer, sent). A5: `msgs/sent__*.md` (root, sent),
  `msgs/lead_sent__*.md` (lead, sent). E3 and E4: root's `msgs/{inbox,read,sent}` and `msgs/<prefix>-{inbox,read,sent}` with the prefix
  mapped to an address (`lead` -> `lead`, `lead-reviewer` -> `lead/reviewer`, `lead-writer` -> `lead/writer`, `lead-checker` ->
  `lead/checker`, `lead-reader` -> `lead/reader`). Files that are not messages (E's `msgs/timeline.txt`) are not listed;
- `received_from_sent`: true for E, E2 and A5 (they kept sent boxes only): the recipient's copy of each message is written to its `read/`;
- `contracts` and `playbooks`: each kept version file with its version (E: `service/SERVICE.v1.md`, `v2`, `v3-current`; E4:
  `service/history--SERVICE.v<k>.md` and `current-SERVICE.md`; ...); `diff-*.txt`, `versions.txt` and the `<hash>.md` copies are not read;
- `run_logs` (E3, E4): each `run-logs/<folder>/` with its address (`lead-checker` -> `lead/checker`, ...);
- `deliverables` (E4): each delivered file with the UTC time of its last write and the log line that shows it (below);
- `team_files` (E4): for each path of `memos/versions/INDEX.txt`, the newest listed version file, written at that org path;
- `charters`: the kept AGENT.md per address (E3 `org-files/`, A5 `charters/`, ...), else a minimal charter (frontmatter `name` only) for every
  address the messages name, except `root` (the org root) and `runtime` (a sender of notes, never an agent);
- `org_md`: the kept ORG.md.

Rules of materialization:
- Messages are parsed with `kernel.split_frontmatter` and written byte-identical, each to the box it was kept in. A `runtime` message is
  written only to its recipient's box (the runtime has no sent box). The same id kept twice must be byte-identical, else the test fails.
- Contract and playbook versions go into `history/` and the current file. The contract's `deliverable.path` is rewritten to the replay's
  deliverable folder when the corpus kept deliverables (E4), else to a missing folder under the replay root (P3 then finds nothing). This edit
  of the materialized copy is the only change to a kept record, and the kit's docstring says so.
- **Times** are converted to UTC microseconds: message ids are UTC already; `memos/versions/INDEX.txt` and `org-git-log.txt` are `+01:00`;
  the deliverables log is `Z`.
- **Deliverable mtimes** come from the manifest, which pins each file's last write (each is the start time of the last logged command that
  writes the file):
  - s1r: `memo-2026-10-05.md` 2026-10-22T19:12:45.031Z (`deliverables-log.txt` line 16, call #31, a Python heredoc writing
    `deliverables/memo-2026-10-05.md`); `memo-2026-10-12.md` 19:25:33.820Z (line 48, call #42, `sed -i` in `deliverables/`);
    `memo-2026-10-19.md` 19:41:21.761Z (line 82, call #52, a heredoc writing `memo-2026-10-19.md` with cwd `deliverables`);
  - s2r: `2026-10-05-memo.md` 2026-10-22T21:29:46.486Z (line 13, call #38, `cp`);
  - s3: `memo-2026-10-05.md` 2026-10-22T22:03:58.863Z (line 17, call #54); `memo-2026-10-12.md` 22:15:20.879Z (line 28, call #72);
    `memo-2026-10-19.md` 22:33:02.155Z (line 39, call #87).
- `variant` (E3 only, `"r2-links-r1"`, 19.3 E3-7): one more root note, a copy of `...-root-8ca0`'s frontmatter with `id:
  20261021T154600000000-root-0b01`, `created: '2026-10-21T15:46:00+00:00'`, `criterion: R1`, title `criterion link on "Memo for the meeting
  of 2026-10-19": R1`, replying to `...-root-5c11`, `source: human`: a human-tier "same as R1" link on R2, written to root's `sent/` and
  lead's `read/`.
- No git repository: every replay runs on the no-history path.

A listed file that is missing, or a message that does not parse, fails the test (never a skip). `TESTS/meta/test_org_replay_kit.py` tests the
kit: the address mapping, the duplicate check, the deliverable rewrite, the UTC conversion, and, for every pinned deliverable, that the log
line exists, starts with `[<the pinned time>] call #<n>` and names the file. The 0a.2 kit `TESTS/testkit/e4_replay.py` reads the same
corpora for another purpose: it drives a real organization (real git, new ids) with the calls the recorded assistant made. 0b's counts are
read-only derivations of the files, so 0b's kit materializes the kept files with their recorded ids instead; it reuses `e4_replay`'s `EV`,
`EV3` and `evidence()` for the E3 and E4 files and adds the E, E2 and A5 roots beside them.

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
| cases, deliveries, first deliveries, judged, without a verdict, not on a delivery | yes | yes | yes (one-off) | yes | yes |
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
| moved past, held tasks | yes | yes | yes (root's and the lead's boxes only) | yes | yes |
| held figure | no: the derived budget needs the run logs; the view prints a figure that ignores the runs not kept, and no replay asserts it | no | no | yes | yes (s1r: pinned to its final `status`) |

### 19.3 Pre-registered expectations (one test per id)

**E**
- E-1: one record `weekly-memo` (lead; client root, human); 3 cases (`20261018T021644679563-root-b495`, `20261018T022344643603-root-c686`,
  `20261018T024234965290-root-2c75`); 3 deliveries (b495 by `...-lead-e6b8`, c686 by `...-lead-52d5`, rework
  `20261018T022845034488-root-5bae` by `20261018T024337814874-lead-e73a`); judged 1 of 3 (b495, accept `...-root-f538`); first deliveries
  1 accepted (b495), 0 rejected, 1 without a verdict (c686, superseded by rework 5bae, tier not recorded), 1 never delivered (2c75,
  blocked); 1 case without a verdict (c686: its latest delivery e73a, 02:43:37, has no verdict after it; the accept
  `20261018T024152961586-root-550c`, 02:41:52, was given on 5bae's blocked result `...-lead-4b37` and is not read as the accept of e73a);
  2 verdicts not on a delivery (550c, and `20261018T025414374460-root-86de` on 2c75's blocked result); 0 escapes; 3 legacy verdicts;
  c686's window is cut by 2c75 (1 cut case).
- E-2: repeat `n/a (1 of 3 judged cases)`; cost `n/a (1 of 3 judged cases)`; 0 runs in every case (no run log kept), asserted together with
  the corpus note in the test's docstring.
- E-3: top-ups of c686: +5 rework 5bae (tier not recorded), +3 and +1 grants (`...-root-c1c5`, `...-root-f2a7`).
- E-4: timeline: contract v2 and v3 `not confirmed`; playbook v2 and v3 `no admission recorded (written before the evidence gate)`; charter
  and model marks unknown.
- E-5: moved past: `lead/writer` with one task, `20261018T023352181048-lead-a489` from lead, blocked 2026-10-18 02:34 (`...-lead.writer-f27d`),
  `moved past: lead has sent lead/writer 3 task(s) since` (5875, 50f8, b6a7); no other held task of the writer; root's 2c75 is released by
  the verdict 86de (`mail.moved_past`) and not listed; the held figure is not asserted (19.2).

**E2**
- E2-1: one record `meeting-memo`; 3 cases; 6 deliveries; judged 5 of 6; first deliveries 1 accepted (`...-root-55ff`), 1 rejected
  (`...-root-e29b`), 1 without a verdict (`...-root-d22b`, superseded by rework `...-root-d90e`, tier not recorded); 0 cases without a verdict;
  0 verdicts not on a delivery; 5 legacy verdicts; 0 cut cases.
- E2-2: 2 escapes, both `untyped` (no rule matched): R1 on `...-root-d90e` (the assistant's own rework, whose `source` was never recorded, so
  `relayed-error` cannot fire on these files) and R2 on `...-root-e29b` (the Marta row); no link exists and no lasting word occurs. The
  view's verifier line: `lead/reviewer: escapes 2 of 5 judged (2 untyped); PASS precision 3 of 5; ...`.
- E2-3: repeat `no (3 judged cases; counted: R1, R2)`.
- E2-4: health on these files: lead/reviewer judged 5, escapes 2 (untyped, counted), not flagged (0.4 is not above 0.5), as 0a 5.5 predicted;
  root's text has no `not its` part.
- E2-5: timeline: contract v2 and v3 not confirmed; playbook v2 (lead) and v3 with no admission recorded.
- E2-6: moved past: none.

**A5**
- A5-1: no service record; the one-off record has 1 case (`20261017T214038108044-root-f768`, tasks f768, `...-root-00cd` and `...-root-dfe0`,
  both reworks revising f768 with the tier not recorded); 3 deliveries (`...-lead-463e`, `...-lead-82b3`, `...-lead-26db`); judged 0 of 3;
  the first delivery without a verdict, superseded by dfe0 (the first task sent after 463e); 1 case without a verdict (f768), never counted as
  accepted; escapes `none (judged: 0 of 3)`; 0 verdicts not on a delivery.
- A5-2: repeat `does not apply`; cost `n/a (0 of 3 judged cases)`; top-ups +4, +4 (tier not recorded) and +3 (grant `...-root-7620`); runs 0
  (no log kept).
- A5-3: every delivery is signed off by `lead` (the reports' boxes were not kept).
- A5-4: the one-off block of 9.3's A5 sample equals the output's block byte for byte; moved past: none.

**E3** (go/no-go item 8)
- E3-1: 0 cost alarms: spends 12, 15 and 14 of 15; cost `no (0 of 3 cases above 1.25x)`.
- E3-2: R1's unconfirmed link (C6, C3, the rejection's own `criterion`) is not counted by the repeat alarm and is listed as `not counted`.
- E3-3: the superseded `...-root-248f` is not counted as a block moved past; the section is `none`.
- E3-4: contract-gap rejects are not shown as verifier escapes: R1 `contract-gap` (words, "always"), R2 `contract-gap` (answer, link
  `...-root-8ca0` names C11, not in contract v2), both attributed `not its`; the view's verifier line is `lead/reviewer: escapes 0 of 5
  judged; not its: 2 contract-gap; PASS precision 5 of 5; its FAILs before delivery: 2 re-check(s), 2 author rework run(s)`; health for root
  `escapes 0 of 5 judged (+2 not its: 2 contract-gap)`, for an agent `escapes 0 of 5 judged`; not flagged.
- E3-5: the text of 9.3's E3 sample equals the output byte for byte (a golden of the replay).
- E3-6: case `...-root-207b` has 10 runs in relayed reworks.
- E3-7 (the variant `r2-links-r1` of 19.1, so that a replay on real files shows the repeat alarm firing): `repeat: FIRES: R1 failed in 2 of
  the last 3 judged cases (cases 20261021T152347923195-root-dd87, 20261021T153809201054-root-ab46)`; R2's cause is unchanged (contract-gap by
  answer: C11 stays in R2's `confirmed`); the cost line is unchanged.

**E4** (the gate's item 8, then 0b's own)
- S2R-1: s2r's playbook v2 is shown with content beyond C9: its mark reads `admitted (c) on R1, C9: 7 changed line(s): 0 the cited criteria's
  own words, 7 beyond them`, and its `--json` `lines` carry the two vague-deadline lines the gate quotes, next to C9's text in `cited`.
- S1R-1: s1r's four unconfirmed amendments are not counted as client evidence: every criterion v2-v5 added except C9 is marked `not
  confirmed`; none is a repeat subject or a contract-gap answer; C9 is confirmed by link `...-root-1753` (0a.1's rule for a version without
  `answers`).
- S1R-2: s1r's unrecorded rejects 2 and 3 are shown as missing verdicts: cases `...-root-114d` and `...-root-2efa` are without a verdict and
  never counted as accepted; judged 1 of 3.
- S2R-2: s2r's Marta escape is typed as a relayed carry-over: R2 (`...-root-f6dc` on `...-root-342a`) is `relayed-carry-over` through
  `...-root-43b8` and `lead/writer/work/2026-10-05-memo.md`, `also contract-gap` (the link `...-root-d23a` names C10, which contract v1 of
  342a lacks); `rules` starts `["carry-over", "answer"]`.
- S1R-3: s1r's 16 runs are shown as held behind blocks the conversation moved past: `lead holds 12 run(s)` with task `...-root-3559`
  (moved past: 2 tasks since), and `lead/writer holds 4 run(s)` with `...-lead-e679` (moved past: 1 task since) and `...-lead-808c` (not
  moved past); `...-lead-0d54` is not listed (`...-lead-cc98` revises it). The replay derives 12 and 4 from the materialized files; they must
  equal s1r's final `status` (lines 31 and 34 of `final-services-progress-status-health.txt`), and a difference fails the test (the
  expectation is not adjusted).
- S1R-4: the three final memos are hand-edited (they differ from the team's current files), with the no-history remark; R1 (recorded
  18:59:00) predates the last write of `memo-2026-10-05.md` (19:12:45.031, pinned in the manifest), so it is counted and stays an escape (D20);
  the deliveries of `...-114d` and `...-2efa` have no verdict, so they count as neither pass nor escape; 0 deliveries judged after an edit.
- S1R-5: R1 is `contract-gap` (answer: link `...-root-1753` names C9, not in contract v1), signed off by lead/checker, with no `also` (rule 5
  matches "always" too, the same type; `rules` = `["answer", "words"]`); case `...-root-ed94` spends 25 of 15 (1.67x), 5 of its 23 runs in
  relayed rework `...-root-9ce9`, and its window is cut; repeat and cost `n/a (1 of 3 judged cases)`.
- S1R-6: every line of 9.3's s1r excerpt that has no angle brackets equals the output's line byte for byte.
- S2R-3: R1 (`...-root-a9fd`) is `contract-gap` (answer: link `...-root-b255` names C9), with no `also`, and `before_verdict`
  `...-root-43b8`; case `...-root-f230` spends 19 of 15 (1.27x), 5 in relayed rework 43b8; judged 2 of 3 deliveries (43b8's delivery is
  superseded by human rework 342a); alarms `n/a (1 of 3 judged cases)`; hand-edited 0; the view's verifier line `lead/reviewer: escapes 0
  of 2 judged; not its: 1 contract-gap, 1 relayed-carry-over; PASS precision 2 of 2; ...`; health for root `escapes 0 of 2 judged (+2 not its:
  1 contract-gap, 1 relayed-carry-over)`; moved past: none.
- S3-1: the cost alarm fires on case `...-root-88b2` only: 21 of 15 (1.40x), 5 in relayed rework `...-root-fe20`; `...-root-cdef` spends 10
  (0.67x, 5 relayed), `...-root-6947` 15 (1.00x).
- S3-2: R1 (`...-root-ac19` on `...-root-4510`) is `contract-gap` (answer: link `...-root-1fb7` names C8, not in contract v1), with no
  `also`, and `before_verdict` `...-root-fe20`; repeat `no (3 judged cases; counted: R1, C8)`.
- S3-3: first deliveries 0 accepted, 0 rejected, 3 without a verdict, all superseded (`...-88b2` by human rework `...-4510`, `...-cdef` by
  relayed rework `...-116b`, `...-6947` by human rework `...-3286`); judged 4 of 8 deliveries; hand-edited 0.
- S3-4: the user's accept on relayed rework `...-root-116b` counts as a judged delivery (F-E3-10); the view's verifier line `lead/reviewer:
  escapes 0 of 4 judged; not its: 1 contract-gap; PASS precision 4 of 4; ...`; health for root `escapes 0 of 4 judged (+1 not its: 1
  contract-gap)`.
- S3-5: moved past: none (the reviewer's blocked `...-lead-2133` is released by `...-lead-00e8`, which revises it).
- E4-all: no charter or model mark (no git): the unknown line in every block.

### 19.4 The cost comparison on corpora without run logs (`TESTS/e2e/test_org_growth_0b_costs.py`)

E, E2 and A5 kept no run log, so their spend is checked with `over_cost(case, approved, ratio)`, the per-case predicate `cost_alarm` applies,
over `Case` values that carry the published run counts (their docstrings cite the source lines). The alarm's state on the files themselves is
the one 19.3 states (E: `n/a (1 of 3 judged cases)`, E2: `no` on 0 runs, A5: `n/a (0 of 3 judged cases)`).
- E (`STUDY.md` focus item (c): "R1 8 of 12; R2 17 (12 + 5 rework + 3 + 1 granted = 21 handed out); R3 10 of 12"; approved 12, the current
  contract's budget): over on R2 only (17 > 15, 1.42x); R3 (blocked, 10 used, 2 still out) spends 12.
- E2 (`evidence/run-counts.txt`: "R1 first pass 9, rework1 5, rework2 5 = 19; R2 5; R3 first pass 6, rework 5 = 11"; approved 15): over on R1
  only (19 > 18.75, 1.27x).
- A5 (`evidence/run-counts.txt`: lead 13, researcher 1, writer 4, factcheck 4 = 22, approved 22): not over (1.00x).

### 19.5 E5, by amendment (a plan item)

E5's evidence exists in the main checkout but is untracked and in progress, and its gate is not written. When E5's evidence is committed and
its gate exists, its streams join the replays: the planner adds each E5 stream's manifest to the kit (19.1) and, before any E5 replay test is
written, an amendment to this section pre-registers E5's expectations from its gate document and evidence (at least: every `answers`
amendment marked confirmed with its link, or `not confirmed (the link was not recorded)`; the base sections' effect on the carry-over rule;
the P3 notes against the hand-edit counts; the `run credit <addr>@<stem>` notes against the credited counts). No E5 expectation is invented
before its evidence is committed.

## 20. The noise study (study G0): protocol and harness

### 20.1 Purpose, place in the sequence, and design

G0 measures how much the same input varies across repeated runs, so later studies can tell a change from noise (go/no-go item 7; the gate's
item 7). It repeats E5's pre-registered script unchanged (Lena's lines, the three memos, the facilitator's injected relayed rework of memo 1,
the answer key), because that is the newest validated script and E5's results are then the first point inside or outside the band. It has
no pass rule: it reports values and their spread.

- **Sequence.** (1) E5's live streams finish; (2) 0b is built and passes its final validation; (3) E5's gate passes; (4) 0b merges to `main`;
  (5) the manager starts G0 as a study workflow on the merged `main` sha (G0 needs `quality --json`); (6) G0's report closes Phase 0b (the
  exit criterion's "noise baseline measured"; the replays of section 19 are its other half). If E5 fails, 0b does not merge (D-E4-7) and G0
  does not start: the product under study would change, and the manager decides what follows.
- **Script pin.** G0 pins E5's committed `evidence/protocol.md` md5 (today's `protocol.md5` reads `afd437c103407ec5899e4993b465cf25`; the
  committed value is the one pinned) and copies E5's turn files, injection and answer key with their md5s.
- **Runtime**: the V3 runtime for every seat (the assistant with `kiro-cli chat --v3`; org runs through the product's V3 launcher), with
  amendment 1's A3 patterns for every transcript and event extraction (`ST/E4-org-growth-0a1-recheck/evidence/protocol-amendment-1.md`) and
  E5's 4.11 formats.
- **Models**: every seat claude-sonnet-5.5 at `--effort high` (D-E4-8, D-E4-9): the assistant set by the harness, the org agents by the
  product's floor (ORG.md effort `high`). The harness checks `--model` and `--effort` in every run log and in the assistant's invocation; a
  seat outside the set invalidates the stream; no substitution; if claude-sonnet-5.5 is not listed when a stream starts, it does not start and
  the manager is told.
- **Arms (controlled)**: memory presence. M0: the assistant runs in a dedicated HOME prepared by the setup step whose kiro settings are copies
  without the memories index; M1: the owner's ambient kiro memories as they are, recorded by md5 and index listing (E5 4.5's method). The
  owner's real `~/.kiro` is never modified (md5 before and after); if a dedicated HOME cannot authenticate, the study stops and asks the
  manager.
- **Identical skill bytes in both arms.** A global `~/.kiro/skills/hirearchy/SKILL.md` can shadow the profile's `skill://` resource
  (followups item 2). So: the workspace copy is the repo's SKILL.md at the G0 sha (md5 recorded); in M1 the harness records the md5 of
  `~/.kiro/skills/hirearchy/SKILL.md` (read-only, E5 4.4's check) and the stream is invalid unless it equals the workspace copy's or the file
  is absent; M0's dedicated HOME holds a copy of the same bytes at the same relative path exactly when M1's HOME has one. Every
  `disclose_context` of the skill is checked against that md5 (E5 4.4). The arms then differ only in the memories index.
- **Stratifier (observed)**: skill activation, E5 4.4.1's strata A (activated before the first `propose_org` and the first `feedback`), B
  (activated only after one of them), N (never), n/a (neither call). Forcing activation would test another product.
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
| repeats, arms, HOME preparation, skill md5 checks, model and effort checks, Lena's turn driver, injection | - | `run_arm.sh <arm> <k>` over E5's `run_turn.sh`, `inject_root_rework.py` (with F-E4-9's fixed polling loop), `model_check.sh`, `ambient_context.py`, `skill_check.sh` |
| assistant-layer measures | - | `extract_mechanical.py` (E5's, with A3 patterns) extended for 20.4 B |
| answer-key scoring, reviewer ambiguity recall, prompt growth | - | `score_memos.py`, `ambiguity_recall.py`, `prompt_sizes.py` |
| the baseline table | - | `aggregate.py` -> `baseline.md` |

The harness is study code, built by the study's setup step from E5's harness (copied with md5s recorded), not product code. Before the first
stream it must re-derive E5's published counts from E5's raw evidence (a self-check); a mismatch stops the study.

### 20.3 Procedure per stream

Setup as E5 (sandbox, workspace skill copy with md5, settings md5, safety snapshot before), the arm's HOME (20.1's skill rule), then E5's
turns verbatim, the injection as E5's protocol places it, `quality --json` after each turn and at the end, the copy of the org evidence,
safety snapshot after. The streams of the two arms are interleaved (M0, M1, M0, ...) so that time-of-day and service load do not line up with
an arm.

### 20.4 Measures (per stream; then per arm and per skill stratum: every value, min, median, max; binary ones as `k of n`)

A. **Team layer**: per delivered memo version the answer-key score (decisions n/8, action items n/15, wrong dates, extra rows, Summary
   first); reviewer verdicts (PASS/FAIL, `criteria met n of m`); **reviewer ambiguity recall** (D-E4-5; E5 protocol's D21 copied verbatim:
   k = reviewed versions x ambiguity items the reviewer listed as `ambiguous` on its first review of that version, n = reviewed versions x the
   items they contain), `k of n` per stream and pooled, `n/a (0 of 0)` when none was reviewed, plus per item and version whether the lead
   forwarded it, whether `progress` flagged it and whether the writer left it out of the next version; runs per case; `revise_playbook`
   attempts, refusals and admissions; **owner prompt growth**: the lead's prompt bytes per run (first, max, last, and last minus first) and
   the words of each Reflect section (max), with E3's 20.2 KB -> 29.9 KB and 452-679 words as the reference.
B. **Assistant layer**: skill activation (stratum); per human reject, exactly one yes/no item naming an id before any `define_service`; every
   flagged item asked before delivery (D-E4-5's restated clause 3); relayed reworks sent and how many the user asked for; hand edits and
   whether a human-tier verdict followed; verdict recording (delivered versions the user saw against verdicts recorded); results read with
   `inbox` against shell reads, and root's unread count at the end; P2 and P4 refusals met.
C. **Product layer**: every count of `quality --json`, and the harness's re-derivation; the alarms that fired, each checked against the raw
   files.

### 20.5 Output and use

`baseline.md`: one table per layer, rows = measures, columns = streams grouped by arm and stratum, then min/median/max (or `k of n`); a zero
denominator is `n/a (0 of 0)`. A later study on the same script reads a value inside the band as indistinguishable from noise at this k; no
test of significance is made.

### 20.6 Cost

About 40-50 org runs and 12 user turns per stream (E4 s1r: 39 org runs, 12 turns), so about 300 org runs plus the assistant sessions for 6
streams. The number of streams is an open question for the owner (Q3).

## 21. What the 0b study must check (pre-registration input)

- **Deterministic part**: at the study's commit, `TESTS/e2e/test_org_growth_0b_replays.py` and `test_org_growth_0b_costs.py` pass, every
  expectation of 19.3 and 19.4 included (E3-7's firing variant too); the output is kept verbatim.
- **Model set and effort**: every seat claude-sonnet-5.5 at effort high, checked per run log and for the assistant; a seat outside the set
  invalidates the stream (20.1).
- **Runtime**: V3 everywhere; A3 patterns; every org run's `# cwd:` and model lines checked.
- **Arms and strata**: k >= 3 valid streams per memory arm; the skill md5 rule of 20.1 in both arms; skill activation recorded per stream
  before any score is read; cells under 3 streams reported as such.
- **The view is right on live files**: for every stream, every count of `quality --json` equals the harness's re-derivation from the raw files;
  each mismatch is listed with the files that show it.
- **Verdict timing live**: every verdict the view counts follows its delivery's `done` result; every verdict on a blocked or failed result is
  in `not_on_a_delivery`; checked by hand on the raw files.
- **Alarms live**: every alarm that fired is listed with its cases and checked by hand against the raw files; every repeat subject is a
  human-tier link or a human rejection (no relayed reading among them); every cost alarm's spend equals the case's charged runs plus the runs
  still out.
- **Causes live**: every escape's cause is re-typed by hand from the raw files by the rules of section 5, and disagreements are reported;
  every `relayed-carry-over` is checked against what the relayed rework actually changed (section 26's over-attribution limit).
- **Reviewer ambiguity recall** and **owner prompt growth**: as 20.4, per stream and pooled.
- **Assistant layer**: as 20.4 B, per stream.
- **One-off verdicts**: E5's script has no one-off task; if a stream contains one, report its verdicts' tiers and whether the words were the
  user's (turn files). Otherwise the one-off path is covered deterministically only (A5 and section 18).
- **Throttle**: credited runs (`run credit <addr>@<stem>` runtime notes, `kernel.RUN_CREDIT_TITLE`, as E5's protocol 4.11 and its item 22
  already match them) equal the quality view's `credited` per case.
- **Safety**: snapshots before and after; the owner's `~/.kiro` and the dedicated HOME's md5s; no org outside the sandbox touched.
- Every rate is `k of n`; a zero denominator is `n/a (0 of 0)`, never a pass. The study has no pass rule.

## 22. Golden impact (estimate; every regenerated file is named with its line count in its commit)

| Area | Files (estimate) | Why |
|---|---|---|
| MCP surfaces | `tests/golden/expected/mcp/surface_root.txt`, `surface_root_unbound.txt`, `surface_root_setup_mode.txt` (3) | the `quality` tool, the root `feedback` docstring, the ROOT_INSTRUCTIONS line |
| CLI help | the top-level help, `help_quality.txt` (new), `help_feedback.txt` (both copies) (about 4) | new command, feedback help |
| plan blocks | about 9 | 11.1 |
| health, root's text | text goldens of root's MCP and CLI health with escapes typed `not its` (about 5-10) | section 10 (the `not its` split) |
| health, agents' text and review notes | goldens of agent health and of review notes whose judged deliveries or escapes change (relayed accepts, one-offs, typed escapes) (about 2-6); the wording is unchanged | section 10 (the numbers) |
| health JSON | every health JSON golden gains `not_its` and `causes_unknown` | `to_dict` |
| dashdata / dashboard | 0 expected (the dashboard shows flags, which keep their wording); any dashdata snapshot that embeds `AgentHealth` JSON changes (checked by the planner) | `to_dict` |
| replays | new goldens for 9.3's samples (E3 full, A5's one-off block, the empty org) | 19.3 E3-5, A5-4 |
| prompts, ORG.md, charters | 0 | agents' prompts are unchanged |
Total: about 25-40 regenerated, plus the new ones. Each diff is reviewed and counted in the phase report (08 D1).

## 23. Plan items for the planner, and the backlog

Plan items (in this order of FEATs; each FEAT ends with its SCOPED run):
1. **FEAT-1 reflection and snapshots**: `RunCounter.stamps`, the new `Case` fields (`runs_unknown` included), one-off cases and the chain
   builder's `since`/`count_runs`, `Delivery`/`signer_of` (moved from health with its tests), `not_on_a_delivery`, `cause_of` with `lasting`,
   `attribution`, alarms (exact `Fraction` comparison) and thresholds, marks, `ContractVersions`, `OrgHistory.changes` + `GitClient.log`,
   `BarHistory` + `GitBarHistory`, `CaseRecords` + `DerivedCaseRecords` (one P3 call, per-record `error`, `deliveries()` with its fallback),
   `DeliverableChecks(settled=...)` and `written`, `shown_name` in `__all__`, `services.criterion_words` and the base heading constants
   (byte-identical moves first, each its own commit).
2. **FEAT-2 one-off verdicts**: the `feedback` branch, refusals, `feedback_step` (no leading newline), docstrings and help, the skill's
   line 98.
3. **FEAT-3 the view**: `QualityReport`, `held_tasks`, `left_blocked`, the renderer (every variant of 9.2), `FailCounts` + `HealthFailCounts`,
   `ReadableOrgConfig`, `QualityTools`, `QualityCommand`, the ROOT_INSTRUCTIONS line, README section "Quality (phase 0b)" within the README
   line caps.
4. **FEAT-4 health rebase**: section 10 (the port, the 5th collaborator, `render_text(causes=...)`, root-only split).
5. **FEAT-5 ride-alongs**: 11.1, the skill's line 88, 11.5 (the flaky golden screen test: find the nondeterminism, make the capture
   deterministic, no retry).
6. **FEAT-6 replays**: the kit, its manifest, its meta tests, 19.3 (with E3-7's variant) and 19.4.
7. **FEAT-7 docs**: ARCHITECTURE (2.2 row 31, section 3's Protocol lists for reflection, progress, snapshots, health's port, the entry points),
   README, and amendments to this design for anything the build changed.
8. **E5 adoption** (19.5, section 27): once E5's evidence is committed and its gate exists, E5's manifests in the kit and an amendment to this
   design that pre-registers E5's expectations, before any E5 replay test; G0 pins E5's committed protocol md5.

Backlog (out of scope, with the reason):
- A one-off verdict settling P3 hand-edit notes and one-off client questions (8.5): consistent, but changes 0a.2 behaviour the row does not ask
  for.
- Semantic failure classes beyond `off_spec` and `wasteful` (packs, Phase 3); `period` units, the `external` tier and `timing` (delayed
  oracles) (Phase 3, 4.6).
- A full git replay of E4's history (its log text cannot rebuild the repository).
- Health reading hand edits (it runs per agent and in the review cycle; 10).
- Reading a retired team's run logs for a continued service's old cases (0a.2 section 22; 4.1 marks them instead).
- Refusal counts in the view (the retro brief, Phase 2; `observe` shows them now).
- An org-level criteria library from one-off verdicts (08 section 6: reopens after 0b shows recurring one-off shapes).

## 24. Deviations from 08, go/no-go and the gate (with reasons)

- **D1 (08 3.2; go/no-go item 4's caveat) A contract-gap rule by answer.** 08 types contract-gap by trigger words only, and go/no-go expected
  E3's reject 2 to type as `reviewer-miss`. 0b adds: the client's human-tier answer names a criterion the rejected task's contract lacked.
  Reason: it is the client's recorded yes, stronger than a phrase; without it E3's reject 2 (C11), and E4's s1r/s2r/s3 first rejects, type as
  a reviewer miss or by an "always" that happens to be there.
- **D2 (08 3.2) A fixed order of the rules, with `also` and `rules`.** 08 gives the rules as a list. The order of 5.1 makes the type
  deterministic and keeps the gate's pre-registered s2r carry-over; the other matching rules stay visible as disputed causes.
- **D3 (08 3.2) "The reviewer PASSed" read from `done` and the task's contract version.** Parsing review reports would be domain- and
  template-specific; a `done` result asserts every criterion met (`FEEDBACK_HEADER`), so a confirmed link to a carried criterion is a sign-off
  the client contradicts.
- **D4 (08 3.3) Escapes are rejections of `done` deliveries only, recorded after the delivery.** A rejection of a blocked or failed result,
  or one given before the done result, is counted as a verdict not on a delivery: the team did not claim it was done when the user judged.
- **D5 (08 3.3) Stalled is the current state; no event horizon.** `progress`'s stalled state is used instead of stall events, so the 30-day
  horizon does not apply; refusals are not in the view (backlog).
- **D6 (go/no-go item 3) Spend for open and blocked cases.** Go/no-go says "runs used"; the shared function `case_spend` (binding: one function
  with `case_total`) adds the runs still out while a case is open or blocked. For finished cases the two are equal.
- **D7 (go/no-go section 3, F-E3-10) Health excludes contract-gap and relayed causes, keeps untyped, and reads no deliverable folder.** Untyped
  escapes stay counted so unknown causes are not hidden; hand edits are left to the quality view because health runs per agent and in the
  review cycle (cost), so health also counts verdicts the view voids. Retired services' deliveries drop out of health (cases need a live
  contract). The `not its` split is shown to root only (I7), because 08 principle 6 has agents see facts, not targets.
- **D8 (08 3.2) One-off cases are root's tasks only.** 08's "one sender" is applied where a client verdict can exist; agents' delegations are
  not cases.
- **D9 (08 3.2) Failure classes: vocabulary now, two derived classes.** Only `off_spec` (reviewer-miss) and `wasteful` (above the cost threshold)
  are derived; the rest are `unclassed`, because a class assigned by the assistant would be relayed text.
- **D10 (08 3.3) Model changes include ORG.md's `default_model` and `effort`.** A change there changes every agent's runs as much as a
  charter's `model:`.
- **D11 (the gate's item 2) The playbook content check is recomputed for every version**, not only for versions before P1, so a hand-written or
  legacy version is caught the same way.
- **D12 (the brief; 0a.2 Appendix A.1 DR-11 and report section 8) The run credit's title.** Those texts say "`Run not charged:` notes"; the
  code writes `run credit <addr>@<stem>` (`kernel.RUN_CREDIT_TITLE`). 0b reads credits only through `kernel.credited_stems`. E5's protocol
  already matches `run credit` (its 4.11 and item 22), and G0 does the same.
- **D13 (go/no-go item 7) The harness is not built first nor E4 re-run on it.** E4 and E5 ran with their own harnesses; G0 reuses E5's and must
  re-derive E5's counts before its first stream.
- **D14 (the gate's item 7) Memory presence is a controlled arm, skill activation an observed stratifier.** Forcing activation would measure a
  different product.
- **D15 (08 row 0b exit) Cost on E, E2 and A5 is checked from their published counts** through the alarm's per-case predicate, because they
  kept no run log (19.4).
- **D16 (08 3.3) `quality` is root-only and has a `--json` form on the CLI.** 08 says humans see counts; the JSON is for the study harness,
  scripts and the playbook lines (D22).
- **D17 (08 3.1) One-off verdicts go through root's existing `feedback`**, not a new tool, and take no `criterion` or `confirms`.
- **D18 (the gate's item 4) "Deliveries without a verdict" is read per case** (the latest delivery, as 0a.2 D4's `delivered_unrated`), at the
  human tier and with the verdict-after-the-result rule; deliveries superseded before a verdict are counted apart.
- **D19 (the gate's item 6) Held runs are the assignee's whole derived budget**, with the mechanism named (`budget_to_return` treats a blocked
  task not moved past as busy), not a per-task split.
- **D20 (the gate's item 4) A hand-edited delivery keeps a verdict given before the edit.** The gate says a delivered file that differs from the
  team's artifact "counts as neither the team's pass nor its escape". 0b applies that to every verdict given at or after the file's last write,
  and keeps a verdict given before it, because that verdict judged the team's file: in s1r, R1 (18:59:00) judged the memo copied from the
  team's file at 18:46:13, and the hand edit came at 19:12:45. So s1r's R1 stays an escape (S1R-4). Only the file as it is now is known.
- **D21 (0a 3.1, kept) Legacy verdicts count as the user's** (`verdict_tier`), and the view marks them as legacy.
- **D22 (the gate's item 2) The playbook diff is in `--json`, not in the text.** The gate asks to show a (c) admission "with its diff beside the
  cited criterion's text". Playbook lines are written by an agent, and I8 keeps agent-written text out of root's prompt, so the MCP and CLI
  text show counts against the cited criteria and the CLI's `--json` carries the changed lines beside the cited criteria's texts. Root can
  already read PLAYBOOK.md through its shell, so the JSON opens no new channel.
- **D23 (the gate's item 6) The writer's held tasks are the two the budget holds on.** The gate says the writer holds 4 runs "behind three
  `blocked` results". One of the three (`...-lead-0d54`) was revised by `...-lead-cc98`, so `mail.moved_past` released it and it holds no run;
  the view lists e679 (moved past) and 808c (not moved past). The gate's total of 16 held runs is unchanged.

## 25. User-visible changes beyond 08 row 0b (named)

Row 0b builds the quality view, one-off cases, the timeline and the noise study. These changes go beyond the row's words; each is either a
binding ride-along or required to build the row:
1. Root's `feedback` accepts one-off tasks (its docstring, its CLI help and a new refusal text for root): required by "cases for one-off tasks
   (root notes)".
2. The skill: step 5.1 reads results with `inbox` (go/no-go section 3, binding); step 5.6 records a one-off verdict the user states, with no
   extra question.
3. ROOT_INSTRUCTIONS gains the line `` `quality`: how the work went. `` (32 characters).
4. Health for root (MCP `health` called by root, CLI `health`): the escapes segment shows `(+k not its: ...)` and `causes unknown (...)`
   (go/no-go section 3, binding); the JSON gains `not_its` and `causes_unknown`.
5. **Agent-visible:** the numbers in agents' health text and in the review cycle's `low_quality` notes change, because health counts typed
   escapes, relayed accepts and one-off deliveries and drops retired services' deliveries (go/no-go section 3, binding). Their wording is
   unchanged; agents never see the `not its` split. Agents' prompts, tools and charters are unchanged.
6. The plan block shows up to 10 service checks (F-E3-8, binding).
7. An optional `quality:` mapping in ORG.md for the thresholds (08: "tunable defaults").
8. The CLI's `quality --json`, which carries each playbook version's changed lines (D22).

## 26. Declared limits

- **Declared provenance.** `source="human"` and the recorded words are the assistant's declaration; the product cannot see the conversation.
  A one-off verdict has no contract to fall back on.
- **Hand edits** are known only for the file as it is now, for the newest delivery listing that file name, in a folder a service contract
  names (one-off deliverables elsewhere are not checked), within P3's bounds; a file edited, judged, then rewritten later keeps the verdict.
  Without git, P3 compares with the team's current files, so a rework in progress that changes the team's file in place makes the delivered
  copy show `differs` (0a.2 section 22), and the view then voids the user's verdicts given after the copy's last write; the no-history remark
  says which comparison was made.
- **The carry-over rule over-attributes.** Rule 2 types any rejected non-relayed rework as `relayed-carry-over` once a relayed rework in its
  chain touched an artifact both list, whatever the rejection is about; a one-file deliverable always shares its artifact. The escape then
  leaves health's count (D7). The shared-artifact test reads the team's own `## Artifacts` lists, so a team that lists a file it did not
  change moves blame onto the assistant. The rules that also matched stay in `also` (a `reviewer-miss` stays visible there), G0 re-types every
  carry-over by hand (21), and Q2 asks the owner whether health should keep counting them.
- **Run attribution** is window-based (08 3.3): a case cut by a later request gives its later runs to that request; the view counts the cut
  cases. Relayed runs are counted by the relayed task's interval, so a relayed rework running in parallel with another task shares runs.
- **A continued service's old cases** (0a.2 5.10) count no runs when their team was retired, because their logs stay in the retired tree; the
  view marks them `runs not counted (...)` by the charter's `created`, and the cost alarm skips them. A charter without `created` gives no
  mark, so such a case reads 0 runs.
- **reviewer-miss** is inferred from `done` and the contract version, not from what the reviewer wrote; a team that reports `done` without a
  check is typed the same way.
- **The words rule** is English and lexical; "never" in "never mind" matches.
- **Cases** exist only for live services (and continued ones); a retired service's history leaves the view and health.
- **Charter and model marks** need git; a retired agent's charter is not followed; at most 40 commits and 5 s of git time per call; a version
  above 64 KiB is not compared.
- **The noise study** at k = 3 gives a range, not a rate.
- **Agent-client services** never alarm; their counts are hypotheses.
- **Stalled** is a current state, not a history.
- **E, E2, A5** kept no run logs; their spends are not derivable from their files, and the held figure is not asserted on them.
- **A one-off verdict on a retired assignee's task** cannot be recorded (ONE-OFF-GONE); the view counts it as without a verdict.
- **Cost of a call**: `quality` runs the P3 checks once (one call: at most 40 git pairs and 5 s of git, about 11 s worst case with its
  subprocess bounds, 0a.2 DR-33/DR-43) and the bar history once (at most 5 s).

## 27. E5: adoption by amendment, and the definitions most likely to move

E5's evidence is in progress (untracked) and its gate is not written. 0b's build may start after E5's live streams finish, and 0b merges only
if E5 passes. When E5 reports, the manager amends this design before the plan freezes, or by a design amendment during the build, for each
finding that touches:
1. **The carry-over rule (5.1 rule 2)**: E5 is the first live data with P4's base sections; if a `base="delivered"` rework still carries a
   relayed change, the base clause moves.
2. **Contract-gap by answer (rule 3)** and **reviewer-miss (rule 4)**: E5's `answers` amendments and product links are their first live input.
3. **Hand-edit voiding (4.3, D20)**: E5 counts P3 notes and hand edits; their timing decides whether "edited before the verdict" is the right cut.
4. **Without a verdict and the verdict-after-the-result rule (4.3)**: P2-UNRATED makes root record verdicts; E5's counts of 0a.2 D4's friction,
   and any verdict recorded on a blocked result, may move the per-case reading.
5. **Credited and relayed runs (4.2)**: E5's throttle credits are the first live credits.
6. **Reviewer ambiguity recall (20.4 A)**: G0 copies E5's D21 verbatim; a change there changes G0.
7. **Moved past without a verdict and held tasks (4.5)**: P2's retire gate and continuations may change which blocks stay open.
8. **Continued services' run marks (4.1)**: E5 counts retire/define pairs; their cases test the `created` rule.
9. **The replays (19.5)**: E5's streams join them with expectations pre-registered by amendment.

## 28. Open questions for the owner

- **Q1. Ask after a one-off delivery?** The design records a one-off verdict only when the user states one (no extra question, within 08's D3
  friction). Asking "Keep it, or what should change?" after every one-off delivery, as for services, would make one-off cases measurable at the
  cost of one question per one-off task.
- **Q2. Which escapes health counts against a verifier.** The design keeps untyped escapes counted (unknown causes stay visible) and drops
  `relayed-carry-over` ones, although rule 2 can over-attribute (section 26). Excluding untyped escapes too would remove more false alarms and
  hide real misses; counting carry-overs again would keep misses visible and blame the reviewer for the assistant's own reworks.
- **Q3. The size of G0.** 2 arms x k = 3 is about 300 org runs plus 6 assistant sessions. More streams per arm (k = 5) narrow the band; adding
  streams to fill thin skill strata is possible only after the fact.
- **Q4. The cost alarm and the assistant's own spend.** The design fires on total spend and shows the relayed runs apart (the user pays both).
  Excluding relayed runs from the comparison would make the alarm about the team only.
- **Q5. The 3-judged-case minimum for the cost alarm.** It follows 08; `case_total` already warns per case at 1.0x. A per-case cost alarm
  without the minimum would repeat that warning.

## Appendix A. Review resolutions

### A.1 Design review of revision 1 (25 findings: 3 HIGH, 12 MEDIUM, 10 LOW)

Every finding is addressed in this revision; none is backlogged or declined. No resolution changes what the user sees or how the system
behaves beyond 08 row 0b and the binding gate items: where a finding offered a choice, the behaviour-preserving option was taken (DR-11,
DR-12).

| Id | Sev. | Resolution | Where |
|---|---|---|---|
| DR-1 | HIGH | One rule: a verdict counts for a delivery only when recorded after that delivery's `done` result (health's rule today). A verdict on a blocked or failed result, or before the done result, is a "verdict not on a delivery", counted apart. "Without a verdict" is defined by `Delivery` only (the `rated` wording is gone). A judged case is a case with a judged delivery. E-1 restated: judged 1 of 3, 1 case without a verdict (c686: 550c came before e73a), 2 verdicts not on a delivery; E-2 becomes `n/a (1 of 3 judged cases)` for both alarms. "Superseded" uses the same timing (A5's first delivery is superseded by dfe0, not 00cd). | 3, 4.3, 6, 9.2, 9.3 (A5), 17, 19.3 (E-1, E-2, A5-1), 19.4, 24 D4 |
| DR-2 | HIGH | Option (b): for an agent with at least one left-blocked task, the section lists every task `budget_to_return` holds on, each marked moved past (with the tasks sent since) or not. S1R-3: lead (3559) and lead/writer (e679 moved past, 808c not; 0d54 released, not listed); E-5: lead/writer's a489 moved past, 3 tasks since. 19.2 states that the held figure is not asserted on corpora without run logs; s1r's 12 and 4 are pinned to its final `status`. The gate's "three blocked results" is recorded as D23. | 3, 4.5, 9.2, 9.3, 19.2, 19.3 (E-5, E2-6, A5-4, S1R-3, S2R-3, S3-5), 24 D23 |
| DR-3 | HIGH | One attribution (`reflection.attribution`: `reviewer-miss` and `untyped` counted, the other causes `not its`) for the view's verifier line and for health (I5 extended). Verifier line: `escapes {e} of {j} judged (...); not its: ...; PASS precision {ratio(j - e, j)}; ...`. E3's sample reads `escapes 0 of 5 judged; not its: 2 contract-gap; PASS precision 5 of 5`; the JSON splits `counted` and `not_its`; E3-4, S2R-3 and S3-4 assert the view's line beside health's. | 3, 4.4, 9.2, 9.3, 10, 15 I5, 19.3 |
| DR-4 | MEDIUM | The no-history remark is a segment of the `hand-edited` line, shown when it counts at least one (s1r has it, E3 does not). The s1r excerpt shows ed94's `window cut by a later request` and `1 case(s)` cut. The one-off variants are in 9.2 (runs `{spend} of {approved} ({x.xx}x)`, escape `rejected case {id} ({assignee}), ...`, timeline and run-attribution lines), and the A5 sample is complete. | 9.2, 9.3, 16 |
| DR-5 | MEDIUM | `also` lists the distinct types, other than the winning type, of the later rules that match; `rules` (every matching rule, in order) is in the JSON. The s1r, s2r and s3 first rejects show no `also`; S2R-2 keeps `also contract-gap`. | 5.1, 9.3 (JSON), 19.3 (S1R-5, S2R-2, S2R-3, S3-2) |
| DR-6 | MEDIUM | `counted` = human-tier verdicts on the delivery before `edited_at`; `voided` = those at or after it; pass or escape by `counted` alone; nothing counted and something voided = `neither`; `written == 0` voids nothing. D20 is rewritten as a deviation from the gate's item 4, with the s1r times as its reason. | 3, 4.3, 24 D20 |
| DR-7 | MEDIUM | "Own words" is counted against the cited criteria (the set P1 applies `_words_of` to). The changed lines and the cited criteria's texts are in `quality --json` (marked `agent_written`); the text shows counts. Recorded as D22 (I8). | 7, 9.1, 15 I8, 19.3 S2R-1, 24 D22, 25 |
| DR-8 | MEDIUM | ORG.md marks compare `settings.config_default_model` and `settings.config_effort` of each version (`default_model`, `effort`); the integration test writes ORG.md through `DEFAULT_CONFIG`. | 7, 18.2, 24 D10 |
| DR-9 | MEDIUM | One `findings(ROOT, None, settled=True)` call per `records()`; each `differs` finding is attributed by `finding.task` to the service or one-off delivery with that task id; other kinds are not counted. Section 26's cost figure is restated for one call. | 4.3, 12.1, 26 |
| DR-10 | MEDIUM | `ServiceRecord.error` (and `hand_edits`); `records()` raises only for an unknown `service` or unlistable agents. `CaseRecords.deliveries` returns `OwnerDeliveries` with `unknown`: an unreadable contract or version makes that service's escapes `untyped` (counted) from the mailboxes alone, and root's health adds `causes unknown (...)`; mailbox errors propagate as today. `deliveries()` counts no runs and reads no folder. | 10, 12.1, 13 |
| DR-11 | MEDIUM | Root only: `render_text(health, causes=...)`, with MCP passing `me == ROOT` and the CLI `True`; agents' health text and the `low_quality` reason keep their wording. Section 25 names the remaining agent-visible change (the numbers), and 22 lists its goldens. | 10, 12.4, 15 I7, 22, 25 |
| DR-12 | MEDIUM | Kept today's rule for both views: an escape is any human-tier reject among the delivery's counted verdicts, so reject-then-accept stays an escape (named in 10 as unchanged). | 3, 4.3, 10 |
| DR-13 | MEDIUM | A per-corpus manifest pins boxes, addresses, version files, run-log folders, deliverables with their last-write UTC times and log lines (s1r #31/#42/#52, s2r #38, s3 #54/#72/#87) and team files; `root` and `runtime` get no charter, and runtime messages go to the recipient only; all times are UTC microseconds; the relation to `e4_replay.py` is stated and its readers are reused. | 19.1 |
| DR-14 | MEDIUM | Section 26 declares rule 2's over-attribution and its reliance on team-written `## Artifacts` (with `also`, G0's hand re-typing and Q2), continued services' old cases (marked `runs not counted` by the charter's `created`, skipped by the cost alarm), and the no-git in-place rework that can void verdicts. | 4.1, 9.2, 21, 26, 28 Q2 |
| DR-15 | MEDIUM | 20.1 states the sequence (E5 finishes, 0b validated, E5 PASS, merge, G0 on merged `main`, G0's report closes 0b; no G0 if E5 fails) and requires identical SKILL.md bytes in both arms (the M1 global copy equal to the workspace copy or absent; M0 mirrors it). | 1, 20.1, 20.3, 21 |
| DR-16 | LOW | The line is named by its text and added as its own line (`` `quality`: how the work went. ``, 31 characters), since the `define_service` line is 119 characters; totals 2 597 / 2 674 / 2 814. | 9.1, 25 |
| DR-17 | LOW | `feedback_step` texts have no leading newline; MCP's `_step` adds it. | 8.2 |
| DR-18 | LOW | `shown_name` is added to `reflection.api.__all__`. | 12.1 |
| DR-19 | LOW | The header, 19.5, 21, 27 and D12 say E5 exists (untracked, in progress) and already matches `run credit`; G0 pins E5's committed protocol md5. | header, 19.5, 20.1, 21, 24 D12, 27 |
| DR-20 | LOW | The relayed default is MCP's and `Org`'s; the CLI keeps `--source human`. | 8.1, 14, 15 I6 |
| DR-21 | LOW | `Fraction(case_spend) > Fraction(str(cost_ratio)) * approved`; the approved budget of a service case is the current contract's, as `case_total` uses. | 3, 4.2, 6, 14 |
| DR-22 | LOW | I9 matches whole words, case-insensitively, in identifiers (split) and string literals; I2 calls `DerivedQualityReport` and `HealthAnalyzer`/`TextHealthRenderer` directly. | 15 |
| DR-23 | LOW | `Mark` is defined; the held line for budget <= 0 and per-task block times are specified; unknown `quality:` keys get a note; numeric strings are accepted by rule; the clamp has a note; `history.text` returning `None` counts in `skipped`; an `answers` version without its link reads `not confirmed (the link was not recorded)`; base literals are only in `_request.py`; stalled is matched by the prefix `stalled (`. | 3, 4.1, 4.5, 6, 7, 9.2, 12.2, 14 |
| DR-24 | LOW | E3-7: a replay variant on E3's files with one human-tier "same as R1" link on R2 pins `repeat: FIRES: R1 failed in 2 of the last 3 judged cases`. | 19.1, 19.3 |
| DR-25 | LOW | `cause_of(..., lasting=LASTING_WORDS)`; 08 3.1's `timing` (delayed oracles) is named as the Phase-3 extension of "without a verdict". | 3, 4.6, 5.1, 17, 23 |
