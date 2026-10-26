# Org growth, Phase 0b: Measure (technical design)

Status: design, revision 3, amended by review pass 3's LOW findings (A.3), the planner's corrections (A.4), the manager's decisions after the
E5 FAIL (D-E5-6 and `e5-gate.md` section 4), the E6 FAIL (D-E6-8, D-E6-9) and the E7 FAIL (D-E7-1 to D-E7-7, `e7-gate.md` section 5; all in A.3). **As built (plan commit 49):** Appendix A.5 records the commit numbering, the golden
list and counts, and every deviation of the build; where A.5 differs from an earlier section, A.5 wins, as A.3 and A.4 do.
Revision 3 answers the design review of revision 2 (14 findings, `DR2-1` to `DR2-14`) and the manager's binding decision of 2026-10-24 on that
review (owner questions Q1-Q5, section 28); resolutions in Appendix A.2, revision 1's in A.1. Branch `feat/org-growth-phase-0b`, worktree
`/Volumes/workspace/hirearchy/.worktrees/org-growth-0b`. Revision 3 was written on `main` `6618c0d` (0a.2 merged); the branch is rebased onto
`main` `b252d77c`, which holds 0a.3 (`18c4ffb`), 0a.4 (`18a4531`) and 0a.5 (`b252d77c`) and the study commits E5 (`3cd28b3`), E6 (`fe0c9fd`) and
E7 (`3a0bf49`). Every figure below that depends on the user's runs or approvals is computed under `b252d77c`'s rules. **Sequence (D-E5-7,
D-E6-8, D-E7-1, D-E7-7):** 0a.3, 0a.4 and 0a.5 merged before this build; 0b is built on top of them, reuses their `Case.relayed_runs`,
`user_spend`, `user_cost`, `user_approved` and `case_total`, and merges after its fail-closed final validation on the current `main` **if
`e7-gate.md` section 3 ("D-E6-8: may 0b merge?") answers YES** (it does). It does not wait for a study to PASS. G0 starts after the merge and only
with the owner's OK on its cost (section 20.6).

Sources of truth, read in full. `docs/research/` is untracked in the main checkout and absent from the worktree, so its files are named by
absolute path (`RESEARCH` = `/Volumes/workspace/hirearchy/docs/research/org-growth`):
- `RESEARCH/08-synthesis.md` ("08"): sections 2, 3.1-3.3, 6, 7, 8 (row 0b is the scope).
- `RESEARCH/phase-0a/go-no-go-0b.md` ("go/no-go"): section 4 items 2-8 and the section 3 ride-alongs (binding).
- `RESEARCH/phase-0a1/e4-gate.md` ("the gate"): section 4 items 1-8 (binding).
- `RESEARCH/phase-0a1/e4-decision.md`: D-E4-5 (reviewer ambiguity recall is a measure), D-E4-8 and D-E4-9 (every seat claude-sonnet-5.5 at
  effort high).
- `RESEARCH/phase-0a/followups.md` item 3 (the flaky golden screen test).
- `RESEARCH/phase-0a2/test-policy.md` (the owner's scoped test policy, 18.3) and `RESEARCH/phase-0a2/org-growth-0a2-report.md` sections 6-8.
- In the worktree: `docs/design/org-growth-phase-0a.md`, `-0a1.md`, `-0a2.md` (sections 20-22) and `org-agent-model-floor.md`;
  `ARCHITECTURE.md` (R1-R13, 2.2, 2.3), `docs/refactor-principles.md`, and the code at `b252d77c` that writes every record read below.
- The replay corpora under `studies/` (E, E2, A5, E3, E4 s1r/s2r/s3), all tracked in git and present in the worktree (checked with
  `git ls-files`: 110, 121, 43, 371 and 1634 files).
- E5, E6, E7 (all FAILED their gates, which is how they are used here; the verdicts do not stop this build):
  - E5: gate `RESEARCH/phase-0a2/e5-gate.md` (section 4 is the input for the E5 amendment), decision `RESEARCH/phase-0a2/e5-decision.md`
    (D-E5-1 to D-E5-7). Its evidence is committed at `3cd28b3` under `studies/E5-org-growth-0a2-recheck/evidence/` (streams `s1`-`s3`).
  - E6: gate `RESEARCH/phase-0a3/e6-gate.md` (section 4), decision `RESEARCH/phase-0a3/e6-decision.md` (D-E6-1 to D-E6-9). Evidence committed
    at `fe0c9fd`.
  - E7: gate `RESEARCH/phase-0a4/e7-gate.md` (section 3 answers D-E6-8 YES; section 5 is adopted in full), decision
    `RESEARCH/phase-0a4/e7-decision.md` (D-E7-1 to D-E7-7). Evidence committed at `3a0bf49`, under `studies/E7-org-growth-0a4-recheck/evidence/`.
  - Section 19.5 and 27 say how their streams join the replays; the study corpora of 19.2 are the older ones.
- `RESEARCH/phase-0a2/test-policy.md`, `docs/design/org-growth-phase-0a5.md` section 18 ("What 0b and G0 must know") and
  `RESEARCH/phase-0b/manager-decision-design-loop.md` (published copy of `.agents/tasks/manager-decision-design-loop.md`).

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
- the **cost alarm** compares the user's runs (`reflection.user_cost`, the figure `case_total` prints) exactly with the user's approved runs
  (`reflection.user_approved`), both 0a.3's, so the warning and the alarm are one rule (D-E5-6); the assistant's relayed runs and the total
  (`case_spend`) are shown on their own line, and the runs credited as throttled apart, never folded in;
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
G0, section 20): the same script repeated k = 3 times per arm (the gate's floor; Q3, decided), every seat claude-sonnet-5.5 at effort high, on the V3 runtime, stratified by
memory presence (controlled) and skill activation (observed), measuring the team, the assistant layer and the product's own counts. G0 runs
after 0b merges, with the owner's OK on its cost, and Phase 0b closes with G0's report (20.1).

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
| counted verdicts | `reflection` (`Delivery.counted`) | The human-tier verdicts on a delivery recorded before the delivery's file changed (4.3); all of them when the file is as delivered. |
| judged | `reflection` | A delivery is judged when it has a counted verdict. A **judged case** is a case with at least one judged delivery. |
| escape | `reflection` (`Delivery.escape`) | A judged delivery with at least one `reject` among its counted verdicts: the team reported `done`, then the human client rejected it. A reject followed by an accept on the same delivery stays an escape (health's rule today, `health/_escapes.py`). |
| decisive verdict | `reflection` (`Delivery.decisive`) | The latest counted reject of an escape; otherwise the latest counted verdict. Its words are the ones quoted; its `R<k>` is the escape's assertion. |
| superseded | `reflection` (`Delivery.superseded`) | A delivery with no human-tier verdict (counted or voided) whose case holds a later task sent after the delivery's result: the id of the first such task. |
| signer | `reflection.signer_of` (moved from `health/_escapes.py`) | The sender of the latest `done` result the owner received from a direct report, answering a task the owner sent after the delivered task and received before the delivery; the owner itself when none (0a 5.5, unchanged). |
| cause | `reflection.cause_of` (new, pure) | Section 5. |
| attribution | `reflection.attribution` (new, pure) | `counted` for the causes `reviewer-miss` and `untyped` (the verifier's possible misses); `not its` for `contract-gap`, `relayed-error` and `relayed-carry-over`. The view's verifier line and health's `low_quality` both call it (I5). |
| `case_spend` | `reflection.api` (0a.1 6.1, unchanged) | Runs used, plus, while the case is open or blocked, the runs handed down that were neither used nor returned. It is the case's **total**, the user's requests and root's relayed reworks together. |
| user's runs | `reflection.user_cost` (0a.3) | `user_spend(case)` less `case.relayed_overlap`: the charged runs of the case outside the intervals of relayed tasks (4.2), less the user's runs that a relayed result carried back, plus, while the case is open or blocked, the user's runs the team still holds; `relayed_overlap` is the most of an unanswered relayed task's runs that can lie in a later request of the user's (0 in every kept corpus but E4 s1r's `...-root-ed94`, where it is 1). It is the figure `case_total` prints and the one its docstring names for this alarm (D-E5-6, decided D1 of the build). `user_spend` is the same without the `relayed_overlap` deduction. |
| user's approved runs | `reflection.user_approved(case, budget)` (0a.3, amended by 0a.5 A2) | `max(budget, case.user_ceiling)`: the per-request `budget` of the service's current contract (a one-off case: the head task's `budget`), raised to the highest ceiling root set for the user's requests; the ceiling at a hand-down is the runs the user's requests used, plus what the team still held for them, plus the hand-down's own budget, at that moment. The default's 1-run hand-down with nothing left is no approval (`Case.unapproved_reworks`); a grant root sends after the user's yes is. For an agent client the contract's budget. It is **not** "the budget plus the top-ups": a top-up asked for while earlier runs came back raises nothing (E3 dd87: +6, approved 15). |
| top-ups | `reflection` (`Case.top_ups`, new) | The budgets of the chain's later tasks, by their `source` (`human`, `relayed`, or not recorded), plus the budget of every note the client sent to an agent of the team inside the case window (progress's grant rule, `LogRunCounts._window`). |
| run window | `reflection._cases` (unchanged) | From the head task's id to the final result of the latest task, ending early at the client's next task to the same owner outside the chain. A window that ended early is `cut` (new flag). |
| charged run, credited run | `kernel.credited_stems` | A run log whose stem a run credit names (`run credit <addr>@<stem>`, `kernel.RUN_CREDIT_TITLE = "run credit"`) is credited: not charged, not counted in `runs` (0a.2 9.2, already so in `LogRunCounter`). |
| moved past, released (budget sense) | `mail.moved_past` (0a.1, unchanged) | A later task from the same sender revises the blocked task (or what it revised), or the sender gave a verdict on its chain after the block: its budget is released. This design says **released** for this sense, so "moved past" in the view always has the gate's sense (left blocked, below). |
| held task (new) | `progress._quality` | A task in `TaskQuery.blocked_tasks(A)` that `mail.moved_past` does not release: `budget.ReserveAllocationPolicy.budget_to_return` treats `A` as busy while one exists. |
| left blocked (new) | `progress._quality` | A held task whose sender has since sent the assignee another task outside its chain: "moved past without a verdict" (the gate's words). |
| not as delivered | `reflection.DeliverableChecks` (0a.2 P3, 0a.3 F-E5-5) | A `differs` finding: a file of a contract's deliverable folder that is not the team's checked version of the artifact of the delivery whose task the finding names (`DeliverableFinding.task`). The label is P3's own words (OQ-3, decided): the files do not show who changed it, so the view does not say "hand-edited". A `relayed` finding (the file equals the checked artifact of an earlier delivery that root's relayed reworks changed afterwards; its `task` is that delivery, its `relayed` the reworks' ids) is **not** a delivery that is not as delivered: it names the delivery the user was given (4.3). |
| given delivery | `reflection` | Of a case: the delivery a `relayed` finding names when one names a delivery of the case (the user's file is that delivery's checked artifact), else the case's latest delivery (OQ-2, decided). |
| `LASTING_WORDS` | `reflection.api` (new) | `("always", "never", "from now on")`, matched case-insensitively on word boundaries; the default of `cause_of`'s `lasting` argument (tests pass other words). No port carries a pack's own words in 0b: that hook is Phase-3 work (backlog, 23). |
| `CAUSES` | `reflection.api` (new) | `("relayed-error", "relayed-carry-over", "contract-gap", "reviewer-miss", "untyped")`. |
| `FAILURE_CLASSES` | `reflection.api` (new) | `("wrong", "missing", "off_spec", "unusable", "out_of_authority", "process_skipped", "wasteful")` (08 3.2), the closed core vocabulary packs map onto (Phase 3). |
| `QUALITY_DEFAULTS` | `reflection.api` (new) | `{"min_judged": 3, "repeat_window": 3, "repeat_failures": 2, "cost_ratio": "1.25"}`, tunable defaults (section 6); `cost_ratio` is held as `Fraction("1.25")`. |
| `Mark` | `reflection.api` (new type alias) | `ContractMark \| PlaybookMark \| CharterMark \| ModelMark \| TopUpMark`, the items of `ServiceRecord.timeline`. |
| `ratio(k, n)` | `progress._quality_render` (new, pure) | `"{k} of {n}"`; `"n/a (0 of 0)"` when `n == 0`. Every rate in the view goes through it. |
| carried criteria | `reflection._causes` | The `C<k>` ids of the contract version the rejected task carried (`task.contract`; a legacy task without it uses the version in force at the task's time, `services`' `in_force` rule; a one-off has none). **Unknown** (`None`) when that version is not among the stored versions. |
| answering version | `reflection._marks` | Of a rejection: the oldest stored contract version whose frontmatter `answers` is the rejection's id (the rule of `services._criteria.answering_version`, applied to the contract marks of section 7); none for a version written before 0a.2. Its **removed ids** are its mark's `removes` (the rule of `services._criteria.amendment_ids`). |

## 4. Data model of every derived count

All counts are derived per call. The tables name, for each, its definition, the exact files it is read from, and the function that
derives it. "Root's boxes" are `<org>/{inbox,inflight,read,sent}/*.md`; an agent's are `<org>/<addr>/{inbox,inflight,read,sent}/*.md`
(single writer `mail`). Contracts: `<owner>/services/<name>/SERVICE.md` and `history/SERVICE.v<n>.md`; playbooks: `PLAYBOOK.md` and
`history/PLAYBOOK.v<n>.md` (single writer `services`). Run logs: `<addr>/runs/<stem>.log` (single writer `runs`). Charters:
`<addr>/AGENT.md` (single writer `orgfiles`).

### 4.1 Cases

| Count | Definition | Files | Function |
|---|---|---|---|
| cases | Service cases of a service; one-off cases of root | client's `sent/` (tasks), contract `created` from `SERVICE.md` | `CaseHistory.cases` (unchanged), `CaseHistory.chains` and `CaseHistory.one_off_cases` (new) |
| state | `done`, `failed`, `blocked` from the latest task's latest result, else `open` | client's received boxes (results) | unchanged |
| stalled | an `open` case whose latest task `progress`'s `TaskStates.state_of` calls stalled now (its `state` starts with `stalled (`) | the team's boxes, pause flags, run registry | `progress` (current state only, no history) |
| reworks, relayed reworks | tasks after the head; those with `source: relayed` | client's `sent/` | `Case.reworks`, `Case.relayed_reworks` (unchanged) |
| cut | the window ended at the client's next task to the owner before the final result | client's `sent/`, received boxes | `Case.cut` (new) |
| runs not counted | the case's runs cannot be read, for the first of these reasons that applies: (1) the one-off assignee no longer exists (`assignee retired`); (2) the head task is older than the owner's (or assignee's) charter `created` (`sent before {owner} was hired again: the retired team's run logs are not read`; 0a.2 section 22, a continued service's old cases); (3) the case is `done` or `failed`, its window is not `cut`, and the window holds no run log of the team, charged or credited (`no run log in its window`): live, the run that wrote the result started inside the window, so a case without one is a corpus that kept no run log or a run that began before the task arrived (26). Evaluated only when runs are counted (`runs=True`) | `<addr>/AGENT.md` frontmatter `created` (`agents.CharterReader`); the run log names (4.2). A charter without `created`, with a `created` that `parse_time` rejects, or one whose read raises (`OSError`, text that is not UTF-8, frontmatter that does not parse) gives no mark for reason (2) | `Case.runs_unknown: str` (new, `""` when counted) |

One-off cases (`CaseHistory.one_off_cases(*, runs=True)`, new): root's sent tasks with no `service`, grouped by `revises` exactly as service
chains are (`head()` follows `revises` within root's one-off tasks to the same `to`; a rework to another assignee heads its own case). `Case`
for a one-off: `service = ""`, `owner = head.to`, `playbook = used = 0`, `client_kind = "human"`; verdicts are root's notes with `feedback`
that reply to a task of the chain (section 8); runs use the same window rule over `agents.subtree(head.to)`. `case_of(task)` stays
service-only, so `progress`, P3 and P4 behave as today.

Service chains get a public method too, so that `DerivedCaseRecords`, typed against the `CaseHistory` Protocol (R6), can ask for chains
without a contract and without runs: `CaseHistory.chains(owner, service, *, since: datetime | None, runs: bool) -> list[Case]` (new) builds
the service's cases from the client's mailboxes alone, keeping requests at or after `since` (`None`: every request), and reads no contract.
`cases(owner, service)` becomes `chains(owner, service, since=contract.created, runs=True)` after the contract read (`[]` without a contract,
unchanged). With `runs=False` the builder reads the mailboxes only (no run log, charter or playbook file): `runs`, `credited`,
`relayed_runs` and `used` are 0 and `runs_unknown` is `""`; the other fields (`returned`, `cut`, `top_ups`, and 0a.3's `relayed_returned`, `relayed_to_user`, `user_granted`, `unapproved_reworks`,
`open_tasks`) are mail-only and always filled. `user_ceiling` is filled too, but the runs before each hand-down are then read as 0 (no run log
is read), so it is a lower bound: the figure of the corpora that kept no run log (19.4).
One private builder in `_cases.py` serves `chains` and `one_off_cases`. Health's reads (section 10) use `runs=False`.

### 4.2 Runs, spend, top-ups

| Count | Definition | Files | Function |
|---|---|---|---|
| runs | charged run logs of the owner's subtree in the window | `<addr>/runs/*.log` names; credits in each agent's received boxes | `Case.runs` (unchanged) |
| credited | credited run logs in the window | same | `Case.credited` (new) |
| relayed runs | charged runs whose stamp `s` satisfies `t.id[:21] <= s < next.id[:21]` for a relayed task `t` of the chain (`next` its successor in the chain; the last task's interval ends at the window's end, inclusive) | same | `Case.relayed_runs` (0a.3, built in this form) |
| total | `case_spend(case)` | as above plus result `budget` headers | unchanged |
| user's runs | `user_cost(case)` (section 3) | as above | 0a.3's, read by `case_total` and by the cost alarm |
| user's approved runs | `user_approved(case, budget)` (section 3); `budget` = the current `SERVICE.md` `budget`, or the head task's `budget` for a one-off case | contract, client's `sent/`, result `budget` headers, run logs | 0a.3's, amended by 0a.5 A2 |
| ratio | `Fraction(user_cost, user_approved)`, shown with two decimals rounded half up (`Decimal.quantize(Decimal("0.01"), ROUND_HALF_UP)`); `n/a (budget 0)` when the user's approved runs are 0 or below; not shown when the runs are not counted. The JSON carries the same two-decimal string (`"0.93"`) or `null` | as above | `progress` renderer |
| top-ups | `TopUps(items: tuple[TopUp, ...])`, one `TopUp(id, kind, amount)` per budget added after the head task, in id order: each of `tasks[1:]` with its budget and its `source` as kind (`human`, `relayed`, or `unrecorded` for `None`, a legacy rework), and each client note (`type == "note"`, `budget > 0`, `to` in the team) with an id inside the window, kind `granted`; properties `human`, `relayed`, `unrecorded`, `granted` sum the amounts | client's `sent/` | `Case.top_ups` (new) |

`RunCounter.stamps(team, start, end) -> list[tuple[str, bool]]` (the 21-character stamps of the team's run logs in the inclusive window, each
with whether a run credit names its stem) and `LogRunCounter.stamps` were built by 0a.3, and `runs_between` counts the uncredited stamps: 0b
reuses them. `Case.runs` and `relayed_runs` are computed in `DerivedCaseHistory` from one `stamps` call per case (0a.3); 0b adds `credited` from
the same call.

**The user's runs and the total.** For a case whose client is root, the case line shows the user's runs against the user's approved runs; the
assistant's relayed runs and the total are one line below it, never folded in (D-E5-6). For a finished case the user's runs are the total less
the relayed runs; for an open or blocked case they add the runs the team still holds for the user (E4 s1r's `...-root-ed94`: 23 runs, 5
relayed, user's runs 18 with the one run that may lie in a later request left out, total 25).

### 4.3 Deliveries, verdicts, coverage, files not as delivered

For each task `t` of a case, `r` is its latest result in the client's received boxes. `t` is a delivery when `r.status == "done"`.

| Count | Definition | Files | Function |
|---|---|---|---|
| deliveries | per case, its tasks whose latest result is `done` | received boxes of the client | `deliveries_of` (new, pure) |
| verdicts on a delivery | notes with `feedback` that reply to `t` with an id above `r.id`, every tier, oldest first | client's `sent/` | `Delivery.verdicts` |
| counted, voided | counted: the human-tier ones of `Delivery.verdicts` whose time (`msg_time`, in microseconds) is below `edited_at`, all of them when `edited_at == 0`; voided: the human-tier ones at or after `edited_at` (`edited_at > 0` only) | as above, plus the deliverable folder | `Delivery.counted`, `Delivery.voided` |
| outcome | `rejected` when a counted verdict is a reject (an escape); `accepted` when judged and not an escape; `neither` when nothing is counted and something is voided (judged after the file changed); `none` otherwise | derived | `Delivery.outcome` |
| first delivery | the case's delivery with the lowest `step` (the head task's when it was delivered; else the first rework that was), and its outcome; none when no task of the case was delivered, and the line then reads `never delivered ({case state})` | as above | `Delivery.step`, minimum per case |
| superseded | section 3 | client's `sent/` | `Delivery.superseded` (the later task's id) |
| judged | deliveries with a counted verdict | client's `sent/` (notes) | `Delivery.judged` |
| without a verdict | cases in state `done` whose **given delivery** (section 3: OQ-2) has no human-tier verdict on it (neither counted nor voided); `relayed only` = those of them with a relayed- or agent-tier verdict on it; `unseen relayed` = cases with a later delivery than the given one, a relayed rework's, that the user was not given (shown apart, never counted as the user's). Where no `relayed` finding names a delivery of the case, the given delivery is the latest one and the rule is D18 as before | client's `sent/`, deliverable folders (P3) | `unjudged_cases` (new, pure; defined by `Delivery` only, never by `reflection.rated`, which counts any tier: e7-gate 5 item 12) |
| verdicts not on a delivery | section 3 | client's `sent/` and received boxes | `not_on_a_delivery` (new, pure) |
| not as delivered | deliveries a `differs` finding names, settled or not | deliverable folders, org git history (P3) | one `DeliverableChecks.findings(ROOT, None, settled=True)` call per `records()` call |
| legacy verdicts | human-tier verdicts without `source`, counted or not | client's `sent/` | `Verdict.message.source is None` |

**A file that is not as delivered voids a verdict only when it changed first.** `DeliverableFinding` gains `written: int` (the file's mtime in
microseconds, which P3 already reads as `FolderFile.mtime_us`) and `settled: bool`. `DeliverableChecks.findings` gains the keyword `settled:
bool = False`: with `True`, findings P3 would leave out as settled are returned with `settled=True` (P3's own notes keep calling it with the
default, so `progress`, `status` and `whoami` are unchanged). 0a.3's `DeliverableFinding` already has the kind `relayed` and the field `relayed`
(F-E5-5), which 0b reads.

`DerivedCaseRecords.records()` calls `findings(ROOT, None, settled=True)` **once** (one P3 bound of 40 git pairs and 5 s per call, 0a.2
DR-33) and attributes each finding to the delivery, service or one-off, whose task id equals `finding.task`:
- a `differs` finding: that delivery gets `edited_at = finding.written` and is counted as not as delivered. A finding with `written == 0` (the
  time is not known; only fakes produce it) marks the delivery not as delivered and voids nothing;
- a `relayed` finding (0a.3, F-E5-5): the file equals the checked artifact of that delivery, which root's relayed reworks changed afterwards. It
  names the **given delivery** of the case (section 3, OQ-2) and is **not** a delivery that is not as delivered: it voids nothing and is not
  counted (the user's correct file is no deviation);
- `unknown`, `link`, `large`, `limit` and `unreadable` findings name no delivery: they are not counted and the view does not show them
  (`progress`, `status` and `whoami` already show them as P3 notes). A finding that names a task of no record (a task of a service whose
  contract is no longer requestable) is dropped.

Pass or escape is decided by the counted verdicts alone. So a delivery whose file changed after all the user's verdicts is `neither`; one judged
before the change keeps that verdict (it judged the team's file) and voids the later ones; one without any verdict is counted both as "without a
verdict" and as "not as delivered". Only the file as it is now is known (section 26). Section 24 D20 records this as a deviation from the gate's
item 4. A file the team itself left unchecked (E5 s3: a `cp` of the writer's unreviewed rework) is labelled by the same words, `not as delivered`
(OQ-3, decided): the label says what P3 found and asserts no cause.

**A verdict on a result that is not `done`** (e5-gate 4 item 3; e7-gate 5 items 6 and 14): D4 stays. A human-tier verdict on a `blocked` or
`failed` result, or before the `done` result, is a verdict not on a delivery, also when the user was given that result's file (E5 s3's R1 on
`...-c209`; E7 s3's accept on the `blocked` `...-d9bc`): the team did not report `done`. Such a case is not a judged case, and the view shows
the verdict under `verdicts not on a delivery`. 0a.5 makes `mail.still_open` false after the user's accept of a `blocked` rework (F-E7-7); the
view does **not** read `still_open` as "the user accepted it", since the broader `moved_past` rule also closes a task on its sender's relayed
verdict on another task of its chain (0a.5 section 18 item 7). Only a human-tier verdict replying to the task says so, and it is counted apart.

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
| failure class | `off_spec` for an escape typed `reviewer-miss`; no other class is derived in 0b (`null`). `wasteful` is the failure class of a case the cost alarm counts, by definition: 0b neither stores nor shows it as a field (the cost line and `cost.cases` carry no class, 9.4); Phase 3's packs map onto it, and showing it is backlog (design correction, manager decision of 2026-10-25) | derived | `failure_class` (new, pure) |

### 4.5 Blocks moved past without a verdict, held runs

| Count | Definition | Files | Function |
|---|---|---|---|
| held tasks | for every agent `A`: every `t` in `TaskQuery.blocked_tasks(A)` with `not moved_past(t, latest[t.id], received(A))`, i.e. not released (the tasks `budget_to_return` holds on) | `A`'s boxes | `progress._quality.held_tasks` (new, pure over mail reads) |
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

`cause_of(delivery, case, assertion, carried, answer_removes, results, lasting=LASTING_WORDS) -> Cause` (pure; `reflection/_causes.py`,
exported from `reflection.api`) types an escape. `v` is the delivery's decisive verdict; `assertion` is its `R<k>` (`regressions`);
`carried: frozenset[str] | None` is the task's carried criteria (section 3; `None` when the version is not stored); `answer_removes:
tuple[str, ...]` is the removed ids of the rejection's answering version (section 3; `()` when no version answers it); `results` maps each
task of the case to its latest result; `lasting` is the words rule's vocabulary (tests pass other words; 0b has no port through which a
pack supplies its own, which is Phase-3 work: backlog, 23). The **named criteria** of the escape are the `C<k>` ids of the human-tier answer,
in order and each once: those of `v.confirmed` (the human-tier link notes of the verdict, including 0a.2's product link), then those of
`assertion.about` when `assertion.link == "confirmed"` (a "same as R<j>" link resolved). The rules are tried in this order; the first that
matches gives the type and the rule:

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
3. **`reviewer-miss`** (rule `link`): a named criterion is in `carried` and not in `answer_removes`. The team reported `done`, which asserts
   every criterion met (`services.FEEDBACK_HEADER`: "report `done` only if every criterion is met"), so its sign-off passed a criterion the
   client says failed and keeps.
4. **`contract-gap`, by answer** (rule `answer`): a named criterion is not in `carried` (the client said yes to a lasting rule the task's
   contract did not have), or is in `answer_removes` (the client answered the rejection by taking the criterion out of the contract: 0a.2
   writes the product link of an answering version that adds nothing with the ids it removed, `services._criteria.answer_ids`, 0a.2 D8; a
   "drop C6" answer names C6, and C6 was carried).
5. **`contract-gap`, by words**: the client's words (`v.note`) contain a word of `lasting` (08 3.2's rule).
6. **`untyped`**: nothing matched; when the human-tier link is `none`, the detail says "the user said it is no lasting rule".

**A stored version is missing.** When the escape has named criteria and `carried` is `None` (the task's contract version is not among the
stored versions), rules 3 and 4 cannot be decided: after rules 1 and 2, the escape is typed `Cause("untyped", "unreadable", ("contract v{n}
is not stored",))`, the fallback of section 10, so it stays counted against the verifier and visible. Without named criteria, rules 5 and 6
run as usual (they need no contract).

**Mixed links.** A link that names a carried, kept criterion and a missing or removed one matches rules 3 and 4: `reviewer-miss` wins and
`contract-gap` is listed in `also`, so a possible miss of the verifier is never hidden behind the gap.

`Cause` (frozen dataclass): `type` (one of `CAUSES`), `rule` (`"relayed task"`, `"carry-over"`, `"link"`, `"answer"`, `"words"`, `"none"`,
or `"unreadable"` for the fallbacks), `detail` (the ids the rule read, as strings: the relayed task; the shared artifact's org-relative path;
the link note's id followed by the criteria of that rule in named order; or the matched word), `rules` (every rule that matches, in order, the
winner first), `also` (the **distinct types, other than the winning type,** of the later rules that match: a disputed cause, retro material),
`before_verdict` (the id of a relayed task of the case whose `done` result lies between the rejected delivery's result and the decisive
verdict: "the user may have judged that version"; `""` otherwise). A later rule of the same type as the winner is visible in `rules` (the
JSON), not in `also` (the text). Rules 3 and 4 never match a one-off rejection: a one-off verdict takes no link (8.1). `{link}` in the texts
below is the latest human-tier link note that names the rule's first criterion.

### 5.2 Why this order

The structural relayed rules come first because they name a cause outside the team that the data shows directly, and they must win over the
answer that followed: in E4 s2r the Marta escape was introduced by the injected relayed rework, inherited by Lena's rework, and then answered
with a new criterion C10; the gate pre-registers it as relayed carry-over (rule 2 before rule 4). The two link rules come next because the
client's recorded answer is the strongest evidence after the structure. They do not partition the human-linked rejections: a link can name
both a criterion the task carried and kept and one it lacked, or one the answer removed. The reviewer rule goes first so that such a mixed
link is typed `reviewer-miss` with `contract-gap` in `also`: the alternative (the gap first) would hide a possible miss of the verifier
behind a contract change, and health counts a miss but not a gap (D7). A criterion the answering version removed is a contract defect the
client named, never a miss: the client did not say the criterion failed, it said the criterion should not be there. The words rule is the
weakest evidence (a phrase in a note) and comes after the link rules, so a reject that names a criterion the reviewer passed is a reviewer
miss even if the note says "always" (`contract-gap` is then listed in `also`). Section 24 D1-D3 records the departures from 08's list.

### 5.3 The texts (the view; `progress/_quality_render.py`)

| Type (rule) | Text after the escape's head (9.2) |
|---|---|
| relayed-error | `relayed-error (the rejected delivery is your relayed rework {task})` |
| relayed-carry-over | `relayed-carry-over (your relayed rework {R} delivered {path} after the delivery the user judged, and the rejected delivery lists it too)` |
| reviewer-miss (link) | `reviewer-miss (the user's confirmed link {link} names {C}, which contract v{n} of the task had; the team reported done)` |
| contract-gap (answer) | `contract-gap (the user's answer, link {link}, names {C}, which contract v{n} of the task did not have)`; for ids the answering version removed, `contract-gap (the user's answer, link {link}, names {C}, which the answering contract v{m} removes)`; when both kinds occur, the second clause is joined to the first: `... did not have, and {C'}, which the answering contract v{m} removes)` |
| contract-gap (words) | `contract-gap (the user's words say "{word}")` |
| untyped | `untyped (no rule matched)`, `untyped (the user said it is no lasting rule)` or, for the fallbacks, `untyped (the contract could not be read: {error})` (section 10) and `untyped (the contract could not be read: contract v{n} is not stored)` (5.1) |

`{C}` lists the rule's criteria, comma-joined in named order. An id in `answer_removes` is listed only in the `removes` clause; the `did not
have` clause lists the other named ids that are not in `carried`.

Then, when present: `; also {types}` and `; your relayed rework {id} delivered after it and before the verdict: the user may have judged
that version`. `{path}` is the org-relative artifact path, rendered with `reflection.shown_name` (an artifact path is agent-written text).

## 6. Alarms (thresholds are tunable defaults)

| Threshold | Default | Meaning |
|---|---|---|
| `min_judged` | 3 | an alarm is evaluated only once the record has this many judged cases (08 3.3); before that it reads `n/a ({k} of 3 judged cases)` |
| `repeat_window` | 3 | the repeat alarm looks at this many most recent judged cases |
| `repeat_failures` | 2 | ... and fires when one subject failed in at least this many of them |
| `cost_ratio` | 1.25 | the cost alarm fires for a case whose user's runs (`user_cost`) are above this times the user's approved runs (`user_approved`) |

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
when `v.links_tier == "human"` (`none` excluded). A subject in at least `repeat_failures` of the window's cases fires the alarm; when several
fire, each is listed. Fired subjects, and the `counted` list of the `no` state, are ordered `R` ids first, then `C` ids, each by number (E3:
`R1, R2, C11`). A criterion that only a relayed reading names (the rejection's own
`criterion`, or a relayed link) is never a subject; such links are listed as `not counted`, under every state (also `n/a`), so the user
always sees which readings the alarm ignored: those of the window's cases, and below `min_judged` those of every judged case. A rejection not on a delivery gives no subject. States: `fires`, `no`, `n/a ({k} of
{min_judged} judged cases)`, and for root's one-off tasks `does not apply (one-off tasks name no criterion ids)`.

**Cost** (`cost_alarm(record, t)`, pure). A case of the record (any state) is **skipped**, and named with its reason, when the user's approved
runs are 0 or below (`budget 0`) or its runs are not counted (`runs not counted`, 4.1); every other case is **compared**. `n` is the number of
compared cases. The alarm is evaluated once the record has `min_judged` judged cases; it then fires for every compared case with
`Fraction(user_cost(case)) > t.cost_ratio * user_approved(case, budget)` (exact, no division: 0a.1 section 13; `budget` as in section 3),
reads `no (0 of {n} cases above {cost_ratio}x)` when none does, and reads `n/a (0 of 0 cases compared)` when `n == 0` (JSON `state: "n/a"`,
`compared: 0`): nothing was compared, so it is never `no`. A continued service whose old cases all predate the re-hire (0a.2 section 22) and
E2's files (19.3) are such records. The skipped cases are listed under every state. **The alarm compares the user's runs with the user's
approved runs, the same two figures `case_total` compares** (D-E5-6, which reverses Q4: the assistant's relayed runs are its own spend, and
folding them in led the assistant to ask the user to pay for them: E5 s1). The relayed runs and the total (`case_spend`) are shown on their own
line, the top-ups (human reworks, relayed reworks, unrecorded reworks, grants) and the credited runs beside it (go/no-go item 3, the gate's item
5). Each case line shows its ratio whatever the alarm says, and `case_total` warns at 1.0x on any case, so the user is told of an overspend
before three cases are judged. `over_cost(case, approved, ratio) -> bool` is the per-case predicate the alarm applies (`approved` is the user's
approved runs; the case carries the user's runs); 19.4 tests it on published counts. **A case of an agent client never alarms** (4.6).

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
non-empty, `adds` first; `criteria unchanged` when neither; the added ids in the order of the version's acceptance list and the removed ids in
the order of the version before it, as `services._criteria.amendment_ids` gives them), then its basis, whose per-id parts follow the order
of the added ids:
- `answers` set (0a.2 P2): `: the user's answer to {R}`, then, per id of `answer_ids` (the added ids, else the removed ids, in
  `amendment_ids` order), `: ` and the parts joined by `, `: `{id} confirmed (link {link})` when `confirmed_criteria(cases, criteria)` names
  it (for an answered version only the human link on that rejection counts: 0a.2's rule), else `{id} not confirmed (the link was not recorded)`
  (0a.2 DR-30: the product's link write can fail after the contract). So a removal-only answering version reads `contract v4 (root): removes C6:
  the user's answer to R1: C6 confirmed (link {id})` or `...: C6 not confirmed (the link was not recorded)`;
- `initiated: user`: `: asked for by the user on their own: {ids} user-initiated (never admit a playbook revision)`;
- a root version without either (written before 0a.2): per added id, `{id} confirmed (link {link})` when `confirmed_criteria` names it (0a.1's
  rule), else `{id} not confirmed`; the mark ends `: not confirmed` instead when none is;
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
2. For each path, consecutive listed versions (newer, older): `history.text(commit, path, 65536)` of each (memoized per version), decoded
   strictly as UTF-8 and split with `kernel.split_frontmatter` (the parser `settings` applies to ORG.md). AGENT.md: bodies differ -> a
   charter mark; frontmatter `model` differs (stripped, `""` shown as `the org default`) -> a model mark. ORG.md: `settings.config_default_model(meta)`
   or `settings.config_effort(meta)` differs (the same readers the runtime uses, so `null`, empty and missing compare as the default) -> a
   model mark. A version is **not compared** when `text` returns `None` (the file is above 64 KiB at that commit, or cannot be read), when its
   bytes are not UTF-8, or when its frontmatter does not parse (PyYAML may be imported only by `kernel` and `blueprint`, import-linter
   contract `yaml-only-where-needed`, so the adapter follows the repository's pattern for YAML errors, `except Exception:  # noqa: BLE001 -
   not UTF-8, or YAML that does not parse`, around the decode and the split only, as `agents/_budget.py` and `mail/_index.py` do). Such a
   version gives no mark for either pair it belongs to and counts once in `skipped`. The oldest listed version of a path has no predecessor
   in the list: no mark (its creation, or beyond the bound; `truncated=True` when the list was full).
3. A bound of 5 s of git time per call (`Clock.monotonic`, read before each read) and 2 s per git subprocess; past it the rest is not read and
   `truncated=True`.
The result is `BarChanges(known: bool, marks, truncated: bool, skipped: int)`. `known=False` renders `charter edits and model changes:
unknown (no org history: the organization is not a git repository, or git is missing)`; `truncated` adds `(the newest 40 commits were
read)`; `skipped` adds `({k} version(s) not compared: larger than 64 KiB, unreadable or not parseable)`. Charter and model marks are listed in the block of
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
  (`cli/_commands_services.py:143`), because the terminal is the user's own seat; this departs from go/no-go item 6 (D24).
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
The CLI prints no step after its receipt line: `FeedbackCommand` prints none for service verdicts either (A.4 PC-5; as built).

### 8.3 Refusal texts (constants in `SRC/services/_feedback.py`)

- **ONE-OFF-UNKNOWN** (root only; replaces today's text for root): `` refused: {task_id} is not a task you sent: feedback records the user's
  verdict on one of your service requests or one-off tasks that has a result. Your newest: {up to 10 ids, newest first, or "none"}. Nothing
  was recorded. `` The ids are root's sent tasks that have a result in root's received boxes, service requests (and reworks) and one-off tasks
  alike, by id, newest first. Agents keep today's text.
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

`questions_open` keeps settling a one-off result's client questions only by the user's own rework (`source: human`; a relayed rework settles
none, 0a.5 C; unchanged for one-off tasks); P3 keeps never settling a
one-off not-as-delivered note by a verdict (unchanged; backlog, section 23); `delivered_unrated` and the P2 gate are service-only (unchanged).

## 9. The quality view

### 9.1 Surfaces

| Surface | Signature | Who | Where |
|---|---|---|---|
| MCP | `quality(service: str \| None = None) -> str` | root only (a `root_only` group, registered after `progress`; agents never get it: 08 2.6) | `SRC/mcp_server/_tools_quality.py:QualityTools(setup: SetupMode, report: Provider[QualityReport])`; runs in a worker thread (`anyio.to_thread.run_sync`), like `progress` |
| CLI | `hirearchy quality [service] [--json]` | the terminal (the user's seat) | `SRC/cli/_commands_views.py:QualityCommand(session, report: Provider[QualityReport], out)` |
| Python | `progress.QualityReport.quality_text(service=None) -> str`, `.quality_data(service=None) -> JsonObject` | app, tests | `SRC/progress/_quality.py:DerivedQualityReport` |

The MCP text and the CLI text are the same string. `--json` prints `quality_data` with `json.dumps(data, indent=2, sort_keys=True)` and a
newline (ASCII output: a non-ASCII character is a `\uXXXX` escape, as in the CLI's other `--json` views); its schema is 9.4. It exists
for the study harness (section 20), scripts, and the user who wants a playbook version's changed lines (section 7). In setup mode (no org
bound) the MCP tool returns `SetupMode.state()`, like `progress`.

MCP docstring (`quality`):
```
How the work you asked for has gone, from the files: per service, and for your one-off tasks, the cases; the user's verdicts on first
deliveries, in their words; escapes (the team reported done, then the user rejected it) with the verifier that signed them off and the
cause a rule typed; deliveries without a verdict (never counted as accepts) and files not as delivered; runs per case, the user's against
the runs you approved, with top-ups, your own relayed reworks (your own spend) and runs not charged shown apart; blocked tasks moved past without a verdict and the runs
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

Order: the header block (the title line, the `Thresholds:` line, then each note of 6 and 16, one per line), one block per service root
requests (top-level agents' services, by owner then name), the one-off block, the nested-services section, the moved-past section.
**Layout**: exactly one blank line between two blocks or sections, none inside a block (the header block included), and no blank line at
the start or the end of the text. In the template, `|` separates alternatives. A group with `|` always shows one of its alternatives, with its
numbers even when 0. A group without `|` is shown only when it is non-empty or non-zero. Inside a shown group, a `{n} word` part with `n == 0`
is left out, and a group whose parts are all left out is not shown. A `not counted` reading lists its ids in the rejection's recorded order.

**Which blocks appear.**
- `No cases yet: you have requested no service and given no task.` replaces the service blocks, the one-off block and the nested section
  exactly when no agent offers a service (top-level or nested) and root gave no one-off task; the moved-past section follows it. A service
  defined with no request yet renders its full block (9.3, the empty-service sample).
- The one-off block reads `One-off tasks you gave: none.` when root gave no one-off task and some service exists.
- The nested section is absent when no nested service exists.
- With `service=x`: the header block, then every top-level block of a service named `x` (every owner offering that name), then, when a
  nested service is named `x`, the nested heading with its one line or lines; no one-off block, no `No cases yet`; the moved-past section is
  shown in full, because a held task blocks every service of its assignee. A name no agent offers is the error of section 13, which lists
  the distinct service names, top-level ones in the view's order first, then nested ones in theirs.

```
Quality of the work you asked for (derived from the files, nothing stored; for you and the user, never for agents).
Thresholds: {the defaults | from ORG.md quality:} (tunable): alarms need {min_judged} judged cases; repeat: one id failing in {repeat_failures} of the last {repeat_window} judged cases; cost: a case above {cost_ratio}x its approved runs.
{each note of 6 and 16, one per line}

{service} (offered by {owner}; client: you, human; unit: case; contract v{c}, {playbook v{p} | no playbook}; approved {budget} runs per request)
  cases: {n} (done {d}, failed {f}, blocked {b}, open {o} ({stalled {s} | stalled: unknown ({error})})){; {m} blocked and moved past without a verdict}
  first deliveries: {a} accepted, {r} rejected, {w} without a verdict{ ({x} superseded by a rework before a verdict)}{, {v} judged after the file changed (neither)}{; {y} never delivered}
    {first-delivery line, one per case}
  judged by the user: {ratio(judged, deliveries)} deliveries; without a verdict: {u} case(s){ ({ids}): never counted as accepted}{ ({q} with only your own relayed verdict)}{; {n} later relayed delivery(ies) the user was not given ({ids})}; not as delivered: {h}{ ({ids})}{; {k} judged after the file changed: neither pass nor escape ({ids})}{ (compared with the team's current files: no org history)}
  {legacy verdicts (no source: read as the user's, the 0a rule): {g}}{; }{verdicts not on a delivery (on a blocked or failed result, or before the done result): {z} ({ids})}
  escapes (the team reported done, then the user rejected it): {e | none (judged: {ratio(judged, deliveries)})}
    {R} case {case id}, signed off by {signer}: {cause text of 5.3}
  verifiers: none (no delivery yet) | verifiers: none (every delivery was signed off by {owner} itself) | verifiers:
    {signer}: escapes {ratio(e, j)} judged{ ({m} reviewer-miss, {u} untyped)}{; not its: {cg} contract-gap, {re} relayed-error, {co} relayed-carry-over}; PASS precision {ratio(j - e, j)}; its FAILs before delivery: {rc} re-check(s), {rw} author rework run(s)
  runs per case (the user's runs: runs used outside your relayed reworks, plus runs still out while a case is open or blocked; approved: the contract's {budget} per request, or more where your hand-downs raised it (runs used + held + new, at that moment)):{ none}
    {case id} "{title}": {u} of {a} approved ({x.xx}x){, {c} not charged (model-service throttle)}; top-ups: {none | +{n} human rework {id}, +{n} your relayed rework {id}, +{n} rework {id} (tier not recorded), +{n} your grant {id}}{; window cut by a later request}
      {your relayed reworks: {k} run(s), your own spend; total {t}}
    {case id} "{title}": runs not counted ({reason of 4.1}); top-ups: ...
  alarms:
    repeat: {FIRES: {id} failed in {k} of the last {w} judged cases (cases {ids}){; {id} failed in ...} | no ({w} judged cases; counted: {ids or "none"}) | n/a ({k} of {min} judged cases)}{; not counted: {R}'s reading {ids} (not confirmed), ...}
    cost: {FIRES: case {id} {u} of {a} approved ({x.xx}x){; your relayed reworks {k}, total {t}}, ... | no (0 of {n} cases above {cost_ratio}x) | n/a (0 of 0 cases compared) | n/a ({k} of {min} judged cases)}{; skipped: {ids} (runs not counted){, {ids} (budget 0)}}
  timeline (bar changes, UTC; marked, never used to split the counts):
    {YYYY-MM-DD HH:MM} {mark of section 7}
    {charter edits and model changes: unknown (...) | none}
  run attribution is by time window (08 3.3): {k} case(s) had their window cut by a later request{; their later runs count for that request}.
```
- **Counts of states**: `done`, `failed`, `blocked` and `open` partition the cases; `stalled` counts the open cases that are stalled now, so
  it is written inside `open`'s parentheses.
- **The verifiers line**: `none (no delivery yet)` when the record has no delivery; `none (every delivery was signed off by {owner}
  itself)` when it has deliveries and no signer other than the owner (in the one-off block `{owner}` is the assignees, comma-joined in case
  order); otherwise one line per signer other than the owner, by address. A signer with no judged delivery reads `escapes n/a (0 of 0)
  judged` and `PASS precision n/a (0 of 0)`.
- **The runs header** ends `: none` when the record has no case; otherwise it is followed by one line per case. In a case line `{u}` is the
  user's runs (`user_cost`) and `{a}` the user's approved runs (`user_approved`, section 3); the indented line under it is shown only when the
  case has relayed runs (`k > 0`), `k` is `Case.relayed_runs` and `t` is `case_spend` (the total, including the runs still out). The one-off
  variant is `({assignee})` after the title. `n/a (budget 0)` replaces `({x.xx}x)` when `{a}` is 0 or below.
- **First-delivery lines**: `{case id}: rejected: "{words}"`, `{case id}: accepted: "{words}"`, `{case id}: accepted (no words)`, `{case id}:
  no verdict{ (superseded by {human rework | your relayed rework | rework} {id}{ (tier not recorded)})}`, `{case id}: judged after the file changed
  (neither): the user's verdict came after the file was changed`, `{case id}: never delivered ({case state})`. The line is the first
  delivery's (4.3: the case's delivery with the lowest step), so a case whose head was blocked and whose rework was done shows the rework's
  outcome; `never delivered` appears only for a case none of whose tasks was delivered, with the case's state (`blocked`, `failed` or
  `open`). The words are the decisive verdict's.
- **The legacy and not-on-a-delivery line** is shown when either count is above 0; its two parts are joined by `; `.
- **The no-history remark** on the `not as delivered` segment is shown when `h > 0` and the org has no history (`BarChanges.known` is false): P3
  then compared with the team's current files (0a.2 P3's no-history rule).
- **Charter and model line**: `unknown (...)` without history; `none` with history and no mark; absent when marks are listed.
- **Limits**: the 10 newest cases per block (`and {k} earlier case(s), counted above`), the 10 newest escapes, the 15 newest timeline marks,
  the 10 newest ids per list (`and {k} more`). Titles are root's own (`clip_line(title, 80)`); the user's words are quoted only for counted
  human-tier verdicts, in the first-delivery lines (`clip_line(words, 160)`, the words `FeedbackWords.feedback_text` returns without the fixed
  header; the escape lines show the cause, which names what the rule read). Agent-written text (lessons, playbook reasons and lines, result
  bodies, agents' task titles, file names) never appears, and artifact paths and model names go through `shown_name` (section 15, I8).

**The one-off block** has the heading `One-off tasks you gave (client: you, human; unit: case; approved budget: each task's own)` and the
same lines as a service block, with these variants: the runs header reads `runs per case (the user's runs: runs used outside your relayed
reworks, plus runs still out while a case is open or blocked; approved: each task's own budget, or more where your hand-downs raised it (runs used + held + new, at that moment)):` and each case line reads
`{case id} "{title}" ({assignee}): {u} of {a} approved ({x.xx}x)...` or `{case id} "{title}" ({assignee}): runs not counted ({reason}); top-ups: ...`; an escape line reads `rejected case {case id} ({assignee}), signed off by {signer}: {cause}` (a one-off rejection is
no `R<k>`); the repeat line reads `repeat: does not apply (one-off tasks name no criterion ids)`; the timeline has top-up marks and the
assignees' charter and model marks (no contract or playbook mark). Which of `One-off tasks you gave: none.`, the block or nothing appears is
decided by the rules above ("Which blocks appear").

**Nested services** are one line each under `Services your agents request (the client is an agent: its verdicts are hypotheses, never
counted):` as `- {service} (offered by {owner}; client {client}): {n} case(s), {d} delivered, {v} agent verdict(s)`, by owner then name.

**The moved-past section**:
```
Blocked tasks moved past without a verdict (while one stays blocked, its assignee's later results return no runs):
  {addr} {holds {n} run(s) | holds no run (budget {b}) | holds an unknown number of runs ({error})}:
    task {id} from {you ("{title}") | {sender}}, blocked {YYYY-MM-DD HH:MM}: {left blocked: {you have | {sender} has} sent {addr} {j} task(s) since | blocked, nothing sent since}
```
one agent line per agent with a left-blocked task, then one line per held task of that agent, oldest block first; or `Blocked tasks moved
past without a verdict: none.` The heading keeps the gate's words; each task line says `left blocked` (moved past in the gate's sense) or
`blocked, nothing sent since` (held, not yet moved past). A released task (`mail.moved_past`) is never listed, so the view uses "moved past"
in one sense only.

**A record that cannot be read** (13): `{service} (offered by {owner}): cannot be read ({error}).` or `One-off tasks you gave: cannot be read
({error}).`; the other blocks render.

### 9.3 Sample outputs (exact)

**E3's files** (the replay of section 19; MCP and CLI print the same text):
```
Quality of the work you asked for (derived from the files, nothing stored; for you and the user, never for agents).
Thresholds: the defaults (tunable): alarms need 3 judged cases; repeat: one id failing in 2 of the last 3 judged cases; cost: a case above 1.25x its approved runs.

weekly-meeting-memo (offered by lead; client: you, human; unit: case; contract v3, playbook v1; approved 15 runs per request)
  cases: 3 (done 3, failed 0, blocked 0, open 0 (stalled 0))
  first deliveries: 0 accepted, 2 rejected, 1 without a verdict (1 superseded by a rework before a verdict)
    20261021T152347923195-root-dd87: rejected: "No, not right yet. Sam's CI item says 'before Friday', so that has a date, 2026-10-09. And Marta's room is for the training on the 14th, so I want 2026-10-14 t…"
    20261021T153031017749-root-207b: no verdict (superseded by your relayed rework 20261021T153213891373-root-248f)
    20261021T153809201054-root-ab46: rejected: "Almost, but not right yet: 'Marta keeps the agenda as sent' isn't an action item, nobody has to do anything there. Take that row out. Lee's Friday is right, an…"
  judged by the user: 5 of 6 deliveries; without a verdict: 0 case(s); not as delivered: 0
  escapes (the team reported done, then the user rejected it): 2
    R1 case 20261021T152347923195-root-dd87, signed off by lead/reviewer: contract-gap (the user's words say "always")
    R2 case 20261021T153809201054-root-ab46, signed off by lead/reviewer: contract-gap (the user's answer, link 20261021T154557001479-root-8ca0, names C11, which contract v2 of the task did not have)
  verifiers:
    lead/reviewer: escapes 0 of 5 judged; not its: 2 contract-gap; PASS precision 5 of 5; its FAILs before delivery: 2 re-check(s), 2 author rework run(s)
  runs per case (the user's runs: runs used outside your relayed reworks, plus runs still out while a case is open or blocked; approved: the contract's 15 per request, or more where your hand-downs raised it (runs used + held + new, at that moment)):
    20261021T152347923195-root-dd87 "Memo for the meeting of 2026-10-05": 12 of 15 approved (0.80x); top-ups: +6 human rework 20261021T152757534448-root-d995
    20261021T153031017749-root-207b "Memo for the meeting of 2026-10-12": 5 of 15 approved (0.33x); top-ups: +5 your relayed rework 20261021T153213891373-root-248f, +5 your relayed rework 20261021T153557949152-root-52d7
      your relayed reworks: 10 run(s), your own spend; total 15
    20261021T153809201054-root-ab46 "Memo for the meeting of 2026-10-19": 14 of 20 approved (0.70x); top-ups: +5 human rework 20261021T154215162562-root-2ccf
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
Every figure above is read from E3's kept files (the replay pins them): the totals (12, 15, 14) equal the case totals 0a.1 6.1 states for E3;
the 10 relayed runs are the charged logs of `run-logs/` with stamps from `...-root-248f` to the end of the window, so 207b's user's runs are 15
- 10 = 5; the approved runs are the contract's 15, raised only where the hand-downs reached more: at dd87's rework (`...-d995`) the user's
requests had used 4 runs and the team held 2 of the 15 (9 had come back), so 4 + 2 + 6 = 12, below 15; at ab46's rework (`...-2ccf`) they had
used 9 and the team held 6 (nothing came back), so 9 + 6 + 5 = 20; the FAIL counts are E3's
health line (`re-checks after a FAIL 2 (author rework runs 2)`). Every one of the six deliveries was signed off by lead/reviewer; 207b's
first delivery has no verdict, so 5 are judged; both escapes are attributed `not its`, so PASS precision is 5 of 5 and health reads
`escapes 0 of 5 judged` (section 10). The not-as-delivered count has no no-history remark because it is 0 (E3's deliverable folder is rewritten
to a missing one: 19.1).

**E4 s1r's files, excerpt** (values in angle brackets are pinned by the replay, not restated here):
```
weekly-memo (offered by lead; client: you, human; unit: case; contract v5, playbook v2; approved 15 runs per request)
  cases: 3 (done 2, failed 0, blocked 1, open 0 (stalled 0)); 1 blocked and moved past without a verdict
  first deliveries: 0 accepted, 1 rejected, 2 without a verdict
    20261022T182945409755-root-ed94: rejected: "<the user's words>"
    20261022T191407596413-root-114d: no verdict
    20261022T192724706946-root-2efa: no verdict
  judged by the user: 1 of 3 deliveries; without a verdict: 2 case(s) (20261022T191407596413-root-114d, 20261022T192724706946-root-2efa): never counted as accepted; not as delivered: 3 (20261022T182945409755-root-ed94, 20261022T191407596413-root-114d, 20261022T192724706946-root-2efa) (compared with the team's current files: no org history)
  escapes (the team reported done, then the user rejected it): 1
    R1 case 20261022T182945409755-root-ed94, signed off by lead/checker: contract-gap (the user's answer, link 20261022T190014222948-root-1753, names C9, which contract v1 of the task did not have)
  verifiers:
    lead/checker: escapes 0 of 1 judged; not its: 1 contract-gap; PASS precision 1 of 1; its FAILs before delivery: 1 re-check(s), 1 author rework run(s)
  runs per case (the user's runs: runs used outside your relayed reworks, plus runs still out while a case is open or blocked; approved: the contract's 15 per request, or more where your hand-downs raised it (runs used + held + new, at that moment)):
    20261022T182945409755-root-ed94 "<title>": 18 of 19 approved (0.95x); top-ups: +6 your relayed rework 20261022T184712524029-root-9ce9, +6 human rework 20261022T190015448581-root-3559; window cut by a later request
      your relayed reworks: 5 run(s), your own spend; total 25
    20261022T191407596413-root-114d "<title>": 7 of 15 approved (0.47x); top-ups: none
    20261022T192724706946-root-2efa "<title>": 9 of 15 approved (0.60x); top-ups: none
  alarms:
    repeat: n/a (1 of 3 judged cases); not counted: R1's reading C5 (not confirmed)
    cost: n/a (1 of 3 judged cases)
  timeline (bar changes, UTC; marked, never used to split the counts):
    <the earlier marks: contract v1, playbook v1, the top-up of 9ce9>
    2026-10-22 18:58 contract v2 (root): adds C8, C9; removes C5: C8 not confirmed, C9 confirmed (link 20261022T190014222948-root-1753)
    <the marks in between: the top-up of 3559>
    2026-10-22 19:03 playbook v2 (lead): admitted (c) on <ids>: <k> changed line(s): <w> the cited criteria's own words, <b> beyond them
    <v3 (adds C10), v4 (adds C11; removes C9), v5 (adds C12, C13; removes C10): every added criterion not confirmed>
    charter edits and model changes: unknown (no org history: the organization is not a git repository, or git is missing)
  run attribution is by time window (08 3.3): 1 case(s) had their window cut by a later request; their later runs count for that request.

Blocked tasks moved past without a verdict (while one stays blocked, its assignee's later results return no runs):
  lead holds 12 run(s):
    task 20261022T190015448581-root-3559 from you ("Rework memo 2026-10-05: Summary line first, Sam's CI due date"), blocked 2026-10-22 19:11: left blocked: you have sent lead 2 task(s) since
  lead/writer holds 4 run(s):
    task 20261022T191728726797-lead-e679 from lead, blocked 2026-10-22 19:18: left blocked: lead has sent lead/writer 1 task(s) since
    task 20261022T193406984560-lead-808c from lead, blocked 2026-10-22 19:35: blocked, nothing sent since
```
Case ed94's window is cut: its latest task (3559) is blocked, so the window runs to the next request, 114d. The writer's third blocked task,
`...-lead-0d54`, is not listed: `...-lead-cc98` revises it, so `mail.moved_past` released it. The held figures 12 and 4 are s1r's own final
`status` (`final-services-progress-status-health.txt` lines 31 and 34), and the FAIL counts its final health line for the checker (line 41).

**A5's files, the one-off block** (A5 kept no run log, so its done, uncut case reads `runs not counted (no run log in its window)`: 4.1
reason 3, section 19):
```
One-off tasks you gave (client: you, human; unit: case; approved budget: each task's own)
  cases: 1 (done 1, failed 0, blocked 0, open 0 (stalled 0))
  first deliveries: 0 accepted, 0 rejected, 1 without a verdict (1 superseded by a rework before a verdict)
    20261017T214038108044-root-f768: no verdict (superseded by rework 20261017T215450859628-root-dfe0 (tier not recorded))
  judged by the user: 0 of 3 deliveries; without a verdict: 1 case(s) (20261017T214038108044-root-f768): never counted as accepted; not as delivered: 0
  escapes (the team reported done, then the user rejected it): none (judged: 0 of 3)
  verifiers: none (every delivery was signed off by lead itself)
  runs per case (the user's runs: runs used outside your relayed reworks, plus runs still out while a case is open or blocked; approved: each task's own budget, or more where your hand-downs raised it (runs used + held + new, at that moment)):
    20261017T214038108044-root-f768 "Competitor analysis of self-hosted note-taking apps" (lead): runs not counted (no run log in its window); top-ups: +4 rework 20261017T215111184137-root-00cd (tier not recorded), +4 rework 20261017T215450859628-root-dfe0 (tier not recorded), +3 your grant 20261017T215533405230-root-7620
  alarms:
    repeat: does not apply (one-off tasks name no criterion ids)
    cost: n/a (0 of 3 judged cases); skipped: 20261017T214038108044-root-f768 (runs not counted)
  timeline (bar changes, UTC; marked, never used to split the counts):
    2026-10-17 21:51 top-up +4 run(s) to case 20261017T214038108044-root-f768: rework 20261017T215111184137-root-00cd (tier not recorded)
    2026-10-17 21:54 top-up +4 run(s) to case 20261017T214038108044-root-f768: rework 20261017T215450859628-root-dfe0 (tier not recorded)
    2026-10-17 21:55 top-up +3 run(s) to case 20261017T214038108044-root-f768: your grant 20261017T215533405230-root-7620
    charter edits and model changes: unknown (no org history: the organization is not a git repository, or git is missing)
  run attribution is by time window (08 3.3): 0 case(s) had their window cut by a later request.
```
f768's first delivery (`...-lead-463e`, 21:54:32) came after the rework `...-root-00cd` (21:51:11, sent while f768 was blocked), so the task
that superseded it is `...-root-dfe0` (21:54:50), the first task sent after it. Both reworks revise f768, so the chain is f768, 00cd, dfe0.

**An empty organization; an ORG.md that does not parse; no git** (the whole text):
```
Quality of the work you asked for (derived from the files, nothing stored; for you and the user, never for agents).
Thresholds: the defaults (tunable): alarms need 3 judged cases; repeat: one id failing in 2 of the last 3 judged cases; cost: a case above 1.25x its approved runs.
ORG.md cannot be read (its settings block does not parse): the default thresholds are used.

No cases yet: you have requested no service and given no task.

Blocked tasks moved past without a verdict: none.
```

**A service defined with no request yet** (the whole text). The fixture is an fs world at the golden clock's start (`golden_support.START`,
2026-01-15 09:00 UTC) with one top-level agent `lead` offering `weekly-report`: contract v1 defined by root at that time with two acceptance
criteria and budget 10, playbook v1 written by root with it (no `admitted`), no task of root at all, no git:
```
Quality of the work you asked for (derived from the files, nothing stored; for you and the user, never for agents).
Thresholds: the defaults (tunable): alarms need 3 judged cases; repeat: one id failing in 2 of the last 3 judged cases; cost: a case above 1.25x its approved runs.

weekly-report (offered by lead; client: you, human; unit: case; contract v1, playbook v1; approved 10 runs per request)
  cases: 0 (done 0, failed 0, blocked 0, open 0 (stalled 0))
  first deliveries: 0 accepted, 0 rejected, 0 without a verdict
  judged by the user: n/a (0 of 0) deliveries; without a verdict: 0 case(s); not as delivered: 0
  escapes (the team reported done, then the user rejected it): none (judged: n/a (0 of 0))
  verifiers: none (no delivery yet)
  runs per case (the user's runs: runs used outside your relayed reworks, plus runs still out while a case is open or blocked; approved: the contract's 10 per request, or more where your hand-downs raised it (runs used + held + new, at that moment)): none
  alarms:
    repeat: n/a (0 of 3 judged cases)
    cost: n/a (0 of 3 judged cases)
  timeline (bar changes, UTC; marked, never used to split the counts):
    2026-01-15 09:00 contract v1 (C1, C2)
    2026-01-15 09:00 playbook v1 (root): written by the client (no admission needed)
    charter edits and model changes: unknown (no org history: the organization is not a git repository, or git is missing)
  run attribution is by time window (08 3.3): 0 case(s) had their window cut by a later request.

One-off tasks you gave: none.

Blocked tasks moved past without a verdict: none.
```
The block is the service's own: a defined service with no request is never `No cases yet` (9.2, "Which blocks appear"). Both empty samples
are goldens (22) and are among the cases of I3's parametrized renderer test (17 item 1).

**`--json` (E3)**: the full output on E3's files is the replay golden `tests/golden/expected/quality/e3.json` (19.3 E3-8), with the schema of
9.4. Each count in it equals the figure of the E3 text above that 9.4's source column names, and its ids and times are those of E3's files;
its bytes are `json.dumps(data, indent=2, sort_keys=True)` of that content.

### 9.4 The JSON schema (`quality_data`, `quality --json`)

Every key is always present (a record with `error` keeps its heading keys, `owner` to `unit`, and has every other key at its empty value: `0`,
`""`, `[]`, `{}` or `null` as the table says; an error record has `budget: null`, `alarms: {}` and `history: null`). The JSON carries every case, escape, mark and id: the text's limits (9.2 "Limits") do not apply.
Times are UTC strings, `YYYY-MM-DDTHH:MM:SSZ` (type `time` below). Ids are full message ids. `ratio` values are the two-decimal string the
text shows (`"0.93"`), never a float. Free text an agent wrote appears only in the playbook lines (`agent_written: true`); artifact paths
(`escape.detail` of a carry-over) and model names, which an agent may have written, appear as stored, unclipped; titles are the stored
strings too (the text, not the JSON, goes through `shown_name` and `clip_line`, I8). A change of shape raises `schema`.

| Object | Key | Type | Empty or null rule | Source (text of 9.2) |
|---|---|---|---|---|
| top level | `schema` | int | always `1` | - |
| | `thresholds` | `{min_judged: int, repeat_window: int, repeat_failures: int, cost_ratio: str, source: "defaults" \| "ORG.md"}` | - | `Thresholds:` line (`cost_ratio` as written) |
| | `notes` | `[str]` | `[]` | the notes of the header block, in order |
| | `services` | `[record]` | `[]` | the top-level service blocks, in the view's order; with `service=x` those named `x` |
| | `one_off` | `record \| null` | `null` when root gave no one-off task, and always with `service` | the one-off block |
| | `nested` | `[{owner: str, service: str, client: str, cases: int, delivered: int, agent_verdicts: int, error: str}]` | `[]` | the nested lines; with `service=x` those named `x` |
| | `moved_past` | `[{addr: str, held: int \| null, held_error: str, error: str, tasks: [held task]}]` | `[]`; `held` null when `held_error` (or `error`) is set | the moved-past section, one object per agent line |
| held task | `id`, `sender` | str | - | the task line |
| | `title` | `str \| null` | `null` unless the sender is root (root's own title, I8) | `you ("{title}")` |
| | `blocked` | time | - | `blocked {time}` (the blocked result's) |
| | `left_blocked`, `sent_since` | bool, int | `sent_since` 0 when not left blocked | `left blocked: ... {j} task(s) since` / `blocked, nothing sent since` |
| record | `owner`, `service` | str | `""` for the one-off record | the block's heading |
| | `client`, `client_kind`, `unit` | str | `client` `"root"`, `client_kind` `"human"`, `unit` `"case"` | heading |
| | `error`, `files_error`, `stalled_error` | str | `""` unless the part cannot be read (13) | `cannot be read ({error})`, `not as delivered: unknown ({error})`, `stalled: unknown ({error})` |
| | `contract`, `playbook` | int | `0` for the one-off record; `playbook` `0` when there is none | `contract v{c}, playbook v{p}` / `no playbook` |
| | `budget` | `int \| null` | `null` for the one-off record (each task's own) and for an error record | `approved {budget} runs per request` |
| | `cases` | `[case]` | `[]` | `cases:` line and the runs lines, oldest first |
| | `first_deliveries` | `{accepted: int, rejected: int, no_verdict: int, superseded: int, neither: int, never_delivered: int}` | zeros | `first deliveries:` line |
| | `deliveries` | `{total: int, judged: int, unjudged_cases: [id], relayed_only: [id], unseen_relayed: [id], not_as_delivered: [{case, task}], neither: [{case, task}], legacy_verdicts: int, not_on_a_delivery: [id]}` | zeros and `[]` | `judged by the user:` and the legacy line (`unjudged_cases`, `relayed_only`, `unseen_relayed`: case ids; `not_on_a_delivery`: verdict note ids) |
| | `escapes` | `[escape]` | `[]` | the escape lines, oldest first |
| | `verifiers` | `[verifier]` | `[]` (both `none (...)` texts; `deliveries.total` tells which) | `verifiers:` lines, by address |
| | `alarms` | `{repeat: repeat, cost: cost}` | `{}` for an error record | `alarms:` |
| | `timeline` | `[mark]` | `[]` | the timeline lines, oldest first, all of them |
| | `history` | `{known: bool, truncated: bool, skipped: int}` | `null` for an error record | the charter and model line and its remarks |
| case | `id`, `title`, `assignee` | str | `assignee` is the owner for a service case | the case line |
| | `state` | `"done" \| "failed" \| "blocked" \| "open"` | - | `cases:` counts |
| | `stalled` | `bool \| null` | `null` when the record's `stalled_error` is set | `stalled {s}` |
| | `tasks`, `budget` | int | `budget` is the contract's per-request budget (a one-off case: the head task's budget) | `budget` is the number `user_approved` starts from; it is not shown on the case line |
| | `user_approved` | int | - | the case line (`of {a} approved`) |
| | `runs`, `credited`, `relayed_runs`, `spend`, `user_cost` | `int \| null` | `null` when `runs_unknown` is set | the case line (`{u}` is `user_cost`; the relayed line's `{k}` is `relayed_runs` and `{t}` is `spend`, the total; `{c} not charged`) |
| | `ratio` | `str \| null` | `null` when `user_approved` is 0 or below, or `runs_unknown` is set | `({x.xx}x)` = `user_cost / user_approved` |
| | `cut` | bool | - | `window cut by a later request` |
| | `runs_unknown` | str | `""` when counted | `runs not counted ({reason})` |
| | `top_ups` | `[{id: str, source: "human" \| "relayed" \| "unrecorded" \| "granted", amount: int}]` | `[]` | `top-ups:` (id order) |
| | `first` | `{task: str, outcome: "accepted" \| "rejected" \| "neither" \| "none", superseded_by: str \| null, superseded_source: "human" \| "relayed" \| "unrecorded" \| null} \| null` | `null` when the case was never delivered | the first-delivery line (4.3: the lowest-step delivery) |
| escape | `assertion` | `str \| null` | `null` in the one-off record | `R<k>` |
| | `case`, `task`, `verdict`, `signer` | str | - | the escape line (`task`: the rejected delivery's task; `verdict`: the decisive verdict's note id) |
| | `cause`, `rule` | str | one of `CAUSES`; a rule of `Cause.rule` | the cause text of 5.3 |
| | `rules`, `detail`, `also` | `[str]` | `[]` | `Cause.rules`, `Cause.detail` (strings, 5.1), `Cause.also` |
| | `before_verdict` | str | `""` | `; your relayed rework {id} delivered after it ...` |
| | `attribution` | `"counted" \| "not its"` | - | the verifier line |
| | `class` | `"off_spec" \| null` | `null` unless `reviewer-miss` | `failure_class` (4.4) |
| verifier | `addr`, `judged` | str, int | - | `{signer}: escapes {ratio(e, j)} judged` |
| | `escapes` | `{counted: {cause: int}, not_its: {cause: int}}` | `{}` per part | `({m} reviewer-miss, {u} untyped)`, `not its: ...` |
| | `pass_precision` | `[int, int]` | `[0, 0]` when `judged` is 0 | `PASS precision {ratio}` |
| | `rechecks`, `rework_runs` | `int \| null` | `null` when `fails_error` is set | `its FAILs before delivery:` |
| | `fails_error` | str | `""` | `its FAILs before delivery: unknown` |
| repeat | `state` | `"fires" \| "no" \| "n/a" \| "does not apply"` | - | `repeat:` |
| | `judged` | int | judged cases of the record | `n/a ({k} of {min} judged cases)` |
| | `window` | `[id]` | `[]` below `min_judged` | the last `repeat_window` judged cases |
| | `subjects` | `{id: int}` | `{}` | cases per subject in the window |
| | `fired` | `[id]` | `[]` | `FIRES: ...` (6's order) |
| | `not_counted` | `{R: [C ids]}` | `{}`; present under every state | `not counted: {R}'s reading ...` |
| cost | `state` | `"fires" \| "no" \| "n/a"` | - | `cost:` |
| | `judged`, `compared` | int | `compared` is 6's `n`, the cases not skipped, under every state | `n/a ({k} of {min} judged cases)`, `n/a (0 of 0 cases compared)`, `no (0 of {n} ...)` |
| | `cases` | `[{case: str, user_cost: int, user_approved: int, ratio: str, relayed_runs: int, total: int}]` | `[]` | `FIRES: case ...` (`total` is `case_spend`) |
| | `skipped` | `[{case: str, reason: "budget 0" \| "runs not counted"}]` | `[]`; present under every state | `; skipped: ...` |
| contract mark | `kind`, `when`, `version`, `by` | `"contract"`, time, int, str | - | `contract v{n} ({by})` |
| | `adds`, `removes` | `[id]` | v1: every id in `adds` | `adds ...; removes ...` |
| | `basis` | `"first" \| "answers" \| "user" \| "legacy" \| "agent"` | - | the basis of section 7 |
| | `answers` | `str \| null` | `null` unless `basis` is `answers` | `the user's answer to {R}` (the `R<k>`) |
| | `confirmed`, `not_confirmed` | `[{id, link}]`, `[id]` | `[]` | per id of `answer_ids` (the added ids, else the removed ids, in `amendment_ids` order) |
| playbook mark | `kind`, `when`, `version`, `by` | `"playbook"`, time, int, str | - | `playbook v{n} ({by})` |
| | `basis`, `restores` | `"c" \| "b" \| "first" \| "restore" \| "client" \| "legacy"`, `int \| null` | `restores` null unless `restore` | the basis of section 7 |
| | `evidence`, `evidence_other` | `[id]`, int | `[]`, 0 | `on {cited ids}` and `and {k} other id(s)` |
| | `changed`, `removed` | int | - | `{k} changed line(s)`, `{r} line(s) removed` |
| | `own_words`, `beyond`, `tagged`, `untagged` | `int \| null` | the first two for `c`, the last two for `b`, else `null` | the counts of section 7 |
| | `cited` | `[{id: str, text: str}]` | `[]` | the cited criteria's texts (the client's own) |
| | `lines`, `lines_more`, `agent_written` | `[{text: str, own_words: bool}]`, int, `true` | `[]`, 0 | agent-written, JSON only (section 7, D22) |
| charter mark | `kind`, `when`, `addr`, `commit` | `"charter"`, time, str, str | - | `{addr}: charter edited (commit ...)` |
| model mark | `kind`, `when`, `addr`, `key`, `before`, `after`, `commit` | `"model"`, time, str (`"ORG.md"` for ORG.md), `"model" \| "default_model" \| "effort"`, str, str, str | `before`/`after` `""` = the org default | `{addr}: model ...`, `ORG.md: ...` |
| top-up mark | `kind`, `when`, `case`, `id`, `source`, `amount` | `"top-up"`, time, str, str, as in `top_ups`, int | - | `top-up +{n} run(s) to case ...` |

`stalled_error`, `fails_error`, `held_error` and `files_error` are new beside 13's texts so a script can tell "0" from "unknown". A test checks every replay
corpus's `quality_data` against this table (keys, types, null rules, and one error record) and, for E3, every count against its text figure (19.3 E3-8).

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
- `CaseRecords.deliveries(owner)` reads no deliverable folder and counts no runs (files not as delivered are a quality-view input only: D7). Per service of
  the owner it reads the contract and its stored versions (12.1's read rule), builds the cases with `CaseHistory.chains(owner, service,
  since=contract.created, runs=False)` and the carried criteria sets; root's one-off cases assigned to the owner come from
  `CaseHistory.one_off_cases(runs=False)`. When the contract or its stored versions cannot be read (`OrgError`/`OSError` from
  `ServiceCatalog.read_contract` or `ContractVersions.versions`, or a file among them that does not parse), it builds that service's cases from
  the mailboxes alone (`CaseHistory.chains(owner, service, since=None, runs=False)`), types every escape `Cause("untyped", "unreadable",
  (clip_line(error, 200),))` (counted: the conservative side, so no escape disappears from a verifier's count) and adds `{service}: {error}`
  to `OwnerDeliveries.unknown`. A mailbox that cannot be read raises, as health does today.
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
  counts a verdict the quality view voids because the file changed after it (it reads no folder: D7), so the two can differ by the deliveries
  the view lists as `judged after the file changed`.

## 11. Ride-alongs (go/no-go section 3, followups item 3)

The go/no-go's stale-installed-skill item is already done (0a.1; `RESEARCH/phase-0a/followups.md`, that is
`/Volumes/workspace/hirearchy/docs/research/org-growth/phase-0a/followups.md`, "Status after 0a.1"), so it is not repeated here.

### 11.1 Show all plan checks up to 10 (F-E3-8)

`SRC/blueprint/_plan_texts.py:SHOWN_SERVICE_CRITERIA` goes from 5 to 10; `TextUserPlan._user_services` is unchanged (`... and {k} more (see the
details)` remains for more than 10). Goldens: the plan blocks with 6-10 criteria (about 9, go/no-go's estimate).

### 11.2 Health on typed escapes (F-E3-10)

Section 10.

### 11.3 Root reads results with `inbox`; one-off verdicts (SKILL.md, net 0 lines)

`skills/hirearchy/SKILL.md` stays at 125 lines (the cap is asserted in `skill/tests/test_finish_rules.py`, `test_observe_skill.py`,
`test_skill_org_growth.py`, `test_skill_services.py` and `TESTS/e2e/test_round7.py`):
- line 88 (step 5.1): `1. Read the final deliverable and check it yourself ...` becomes `1. Read the result with `inbox` (never with shell
  reads of the org's boxes), then the final deliverable, and check it yourself ...` (as built: inside the one line, 125 lines before and after);
- line 98 (step 5.6): `6. A service request: after the delivery ask ONE short question` becomes `6. A service request (a one-off task:
  record only a verdict the user states, no question, no criterion): after the delivery ask ONE short question` (as built: the first line of the step
  is longer and lines 99-100 are untouched, so 0a.4's line 100 stays word for word; the re-wrap this design planned is not done, A.5.3 B5.3).
No line-length rule applies to SKILL.md: the skill tests cap only the file, at 125 lines (its longest line has 317 characters today). The
planner checks the 125-line cap after both edits and records the line count.

### 11.4 Owner prompt growth

Measured in the noise study from the run logs (section 20.4: lead prompt bytes and Reflect words per run). The 600-word Reflect cap stays in
Phase 1. No product change.

### 11.5 The flaky golden screen test (followups item 3; a plan item)

Source: item 3 of `/Volumes/workspace/hirearchy/docs/research/org-growth/phase-0a/followups.md` (untracked, in the main checkout only).
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

As built (plan commit 37): the source was in the table widget, not in the capture path, and the fix is in `SRC/dashboard/_widgets.py` (A.5.3 B8.1).

## 12. Packages, ports, wiring and files

No package is added and no dependency edge changes (`tests/architecture/graph.py` is untouched). ARCHITECTURE.md 2.2 row 31's sentence
becomes `Derives the history of the client's requests, with statistics, from the files.` (one-off tasks are not service requests; no "and"),
and its "reads" column gains the org's git history of `*/AGENT.md` and `ORG.md` through `BarHistory`.

### 12.1 `reflection`

- `api.py`: `Case` already has 0a.3's `relayed_runs`, `relayed_returned`, `relayed_to_user`, `relayed_overlap`, `unsplit_runs`,
  `user_granted`, `user_ceiling`, `unapproved_reworks` and `open_tasks`, and `user_spend`, `user_cost`, `user_committed`, `user_held`,
  `user_approved`, `case_spend` are in `__all__`; 0b reuses them as they are. `Case` gains `credited: int = 0`, `top_ups: TopUps = TopUps()`, `cut: bool = False`, `runs_unknown: str =
  ""` (all defaulted); new frozen dataclasses `TopUps`, `Delivery`, `Cause`, `ContractMark`, `PlaybookMark`, `CharterMark`, `ModelMark`,
  `TopUpMark`, `ServiceRecord`, `OwnerDeliveries`, `RepeatAlarm`, `CostAlarm`, `QualityThresholds`; the type alias `Mark`; constants `CAUSES`,
  `FAILURE_CLASSES`, `LASTING_WORDS`, `QUALITY_DEFAULTS`; pure functions `signer_of`, `deliveries_of`, `unjudged_cases`, `not_on_a_delivery`,
  `judged_cases`, `cause_of`, `attribution`, `failure_class`, `repeat_alarm`, `cost_alarm`, `over_cost`, `quality_thresholds`;
  `CaseHistory.chains(owner, service, *, since, runs)` and `CaseHistory.one_off_cases(*, runs=True)` (4.1; 3 -> 5 methods, within R7's 8);
  the `DeliverableFinding` fields `written: int = 0`, `settled: bool = False`;
  `DeliverableChecks.findings(actor, service=None, *, settled=False)`. `shown_name` (already imported into `api.py` from `_deliverables`) is
  added to `__all__`, so `reflection/__init__.py` re-exports it (R1) and `progress._quality_render` can use it.
- New Protocol `CaseRecords` (2 methods):
  ```python
  @runtime_checkable
  class CaseRecords(Protocol):
      def records(self, service: str | None = None) -> list[ServiceRecord]:
          """Root's view of the record: one per service of every agent (top-level first, then nested, each by owner and name; only those named
          ``service`` when given) and, without ``service``, one for root's one-off tasks (``service == ""``), with cases, deliveries (files not as
          delivered read from the deliverable folders by one P3 call), assertions, typed escapes and the timeline. A record that cannot be read carries
          ``error`` and nothing else. ``OrgError`` for a ``service`` no agent offers; ``OrgError``/``OSError`` when the agents cannot be
          listed."""
      def deliveries(self, owner: str) -> OwnerDeliveries:
          """Every delivery of ``owner``'s services' cases and of root's one-off cases assigned to ``owner``, with signer and cause, without
          reading any deliverable folder or run log (health's input); a service whose contract cannot be read is typed ``untyped`` and named
          in ``unknown``. ``OrgError``/``OSError`` when a mailbox cannot be read."""
  ```
- `ServiceRecord` (frozen): `owner, service, client, client_kind, unit = "case", error: str = "", contract: int = 0, playbook: int = 0, budget:
  int = 0, cases: tuple[Case, ...] = (), deliveries: tuple[Delivery, ...] = (), assertions: tuple[Assertion, ...] = (), escapes:
  tuple[tuple[Delivery, Cause], ...] = (), timeline: tuple[Mark, ...] = (), history: BarChanges = BarChanges(), files_error: str = ""` (`""`,
  or the error text when the P3 call failed).
- `Delivery` (frozen): `case: str, task: Message, result: Message, step: int, signer: str, verdicts: tuple[Verdict, ...]` (every tier, on the
  delivery, oldest first), `superseded: str = ""`, `edited_at: int = 0`, `edited: bool = False`, `given: bool = False` (set on the case's given delivery, section 3); properties `counted: tuple[Verdict, ...]`,
  `voided: tuple[Verdict, ...]`, `judged: bool`, `escape: bool`, `decisive: Verdict | None`, `outcome: str`.
- `OwnerDeliveries` (frozen): `deliveries: tuple[Delivery, ...]`, `causes: tuple[Cause | None, ...]` (parallel), `unknown: str`.
- `_cases.py`: `DerivedCaseHistory(catalog, agents, mail, words, timelines, counter, charters: CharterReader)`: the 7th collaborator is
  `agents.CharterReader` (reflection already depends on `agents`, so no edge is added). One private chain builder serves `chains` (and
  `cases` through it) and `one_off_cases`; it fills the new fields from one `RunCounter.stamps` call per case, and `runs_unknown` from
  `agents.exists`, `CharterReader.charter(addr)[0].get("created")` and the stamps (4.1's three reasons).
- **Reads that may not parse** (DR2-2). A file of the org whose frontmatter does not parse raises `yaml.YAMLError` out of
  `kernel.split_frontmatter`, and one that is not UTF-8 raises `UnicodeDecodeError`; the readers `quality` calls do not catch either
  (`agents.FsCharterReader.charter`, `services` `ServiceStore.versions` and `read_contract`, which `ServiceCatalog.read_contract`, `criteria`,
  `playbook_versions` and `requestable_services` use). PyYAML may be imported only by `kernel` and `blueprint` (import-linter contract
  `yaml-only-where-needed`), so the error cannot be named here. `quality` therefore treats a parse failure like `OSError` at each read it
  makes, with the repository's pattern `except Exception as exc:  # noqa: BLE001 - yaml errors of any kind, text that is not UTF-8` (as
  `agents/_budget.py`, `mail/_index.py` and `settings/_readable.py` do) around each collaborator call that reads files, never around the
  rules that compute from what was read:
  - `_records.py` makes each of its reads through one private helper that turns `OrgError`, `OSError` or any other exception of that call
    into the record's `error`, with the text `{label}: {words}`: the label names the read (`SERVICE.md`, `the stored contract versions`,
    `the criteria`, `the playbook versions`, `the cases`), and the words are `clip_line(str(exc), 200)` for `OrgError`/`OSError`; for any other
    exception, classified without importing PyYAML: `does not parse ({type})` when `type(exc).__module__` starts with `yaml`, `is not UTF-8`
    for `UnicodeDecodeError`, otherwise `cannot be read ({type}: {clip_line(str(exc), 200)})` (so a programming error is not worded as a file
    that does not parse). Only `_records.py`'s texts follow this; `_cases.py` and `_bar_history.py` show no exception text.
    `records()` lists each agent's services with `catalog.service_names(addr)` (names only, no file parsed). The reads are the contract (`catalog.read_contract`), the criteria (`catalog.criteria`), the stored
    versions (`versions.versions(owner, name, "SERVICE")`), the playbook versions (`catalog.playbook_versions`) and the cases
    (`history.cases(owner, service)`, which reads the playbook timeline and builds the chain with the contract's budget (B2.2), and `history.one_off_cases()`;
    their mailbox reads raise only `OrgError`/`OSError`, because the mail index already leaves a message that does not parse out).
    `deliveries(owner)` uses the same helper for 10's fallback; its `chains(..., runs=False)` reads mail only (4.1).
  - `_records.py` makes the P3 call through the same helper (P3's `requestable_services(ROOT)` reads every contract): a failure sets every
    record's `files_error` to the error (13).
  - `_cases.py` reads a charter's `created` with the same pattern around `charters.charter(addr)`: a charter that cannot be read or does not
    parse gives no mark for reason (2) of 4.1, and the case's runs are counted.
  - `app/_bar_history.py` skips a git version that is not UTF-8 or does not parse (section 7) and counts it in `skipped`.
  - ORG.md's thresholds already come through `settings.readable_config`, which turns any failure into `OrgError(UNREADABLE)` (section 6).
  So `quality` never raises on a file that does not parse, current or committed: the floor batch's rule that a bad ORG.md does not break a
  read-only view, applied to every file the view reads. 18.1 and 18.2 test each read.
- `_runs.py`: nothing: `LogRunCounter.stamps` and the uncredited count of `runs_between` are 0a.3's (4.2).
- `_ports.py`: `ContractVersions` (`versions(owner, name, kind)`, satisfied by `services.ServiceStore`); `BarHistory`
  (`changes(addrs) -> BarChanges`) and `BarChanges`.
- New modules: `_records.py` (`DerivedCaseRecords(history: CaseHistory, catalog, agents, mail, versions, bars, deliverables)`, 7
  collaborators: it reads no charter, `DerivedCaseHistory` does), `_causes.py`, `_quality_rules.py` (deliveries, signers, unjudged, alarms,
  thresholds), `_marks.py` (contract and playbook marks).
- `_steps.py`: `feedback_step` for one-off verdict notes (8.2). `_deliverable_checks.py`: `settled`, `written`. `_evidence.py`: `_words_of`
  becomes `services.criterion_words` (no behaviour change).
- `testing.py`: `FixedCaseRecords`, `NoBarHistory`, `FixedBarHistory`; `IMPLEMENTATIONS[CaseRecords]`; the package's `CaseHistory` fakes
  gain `chains` and `one_off_cases`.

### 12.2 `services`

- `api.py`: `contract_of` (from `_parse.py`) and `amendment_ids` (from `_criteria.py`) are re-exported, and `version_in_force(contracts, when)
  -> Contract | None` is extracted from `_criteria.in_force` (which calls it), so reflection reads the stored versions through one parse rule and
  one in-force rule without importing a private module (A.4 PC-1). The re-exports are imported at the end of `api.py`, after every type they
  need, under the comment `# Pure rules re-exported from their modules; they import the types above, so these imports come last.`
  `BASE_DELIVERED_HEADING = "## Base: the version the client judged"`, `BASE_LATEST_HEADING = "## Base: the current version"`
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
- Wiring: `wire_reflection.py` (`DerivedCaseRecords`, and `DerivedCaseHistory`'s new `CharterReader` collaborator), `wire_health.py` (the 5th
  collaborator), `wire_progress.py` (`DerivedQualityReport`),
  `wire_mcp_server.py` (`QualityTools` in `root_only` after `ProgressTools`), `wire_cli.py` (`QualityCommand`).

### 12.6 Single writer and stored state

Nothing in 0b writes a file of an organization except the one-off verdict note, which `mail` stores through `dispatch.RuleMessageSender`
like every verdict note (2.3 unchanged). `quality`, `health` and the timeline only read. `tests/architecture/ownership.py` is unchanged.

## 13. Error handling (per operation)

| Operation | Failure | Recoverable? | Caller receives | Logged |
|---|---|---|---|---|
| `quality` (MCP) in setup mode | no org bound | yes | `SetupMode.state()` text | tool call recorded (`ToolRecorder`), no extra log |
| `quality(service=x)` | no agent offers `x` | yes | `OrgError`: ``no service named `{x}`: the services are {names or "none"}. Call quality() without a service for everything.`` (the distinct names, top-level ones first, then nested ones, each in the view's order: 9.2) | tool call event with the error, as for every tool |
| `quality(service=x)` | `x` longer than 80 characters or not a string | yes | `OrgError`: `service is a service name (at most 80 characters): {clipped}` | same |
| `records()` | the agents cannot be listed | yes (retry) | the `OrgError`/`OSError` propagates: no record can be built | tool call event with the error |
| one service's record | `OrgError`/`OSError` from the catalog, the store or a mailbox while building it, or a contract or playbook file (current or stored) that does not parse (12.1's read rule) | yes (other records build) | `ServiceRecord(error=...)`; the block becomes `{service} (offered by {owner}): cannot be read ({error}).` (e.g. `SERVICE.md: does not parse (ScannerError)`) | no extra log |
| root's one-off record | same | yes | `One-off tasks you gave: cannot be read ({error}).` | no |
| `runs_unknown`'s charter read | the charter cannot be read, is not UTF-8 or its frontmatter does not parse | yes | no mark for reason (2) of 4.1; the case's runs are counted | no |
| the P3 call | the deliverable checks never raise for a folder, file or history (0a.2 6.3); a catalog or mailbox error, or a contract that does not parse, raises | yes | every record gets `files_error = error`; the segment reads `not as delivered: unknown ({error})` and no verdict is voided | no |
| thresholds | ORG.md does not parse (`OrgError(UNREADABLE)` from `ReadableOrgConfig`) | yes | defaults and the note of section 6 | no |
| thresholds | a `quality:` value fails validation, or a key is unknown | yes | its default (or nothing) and the note | no |
| stalled states, held runs, FAIL counts | `OrgError`/`OSError` from `TaskStates`, `BudgetQuery`, `FailCounts` | yes | the part reads `unknown ({error})` (`stalled unknown`, `holds an unknown number of runs ({error})`, `its FAILs before delivery: unknown`) | no |
| moved-past section | a mailbox of an agent cannot be read | yes | that agent's line reads `{addr}: blocked tasks cannot be read ({error})` | no |
| timeline git reads | no repository, no git, a timeout, the bound, a version above 64 KiB, a version that is not UTF-8 or whose frontmatter does not parse | yes | `known=False` (the unknown line), `truncated` or `skipped` | no (git errors are never raised: `OrgHistory`'s rule) |
| CLI `quality` | as above; no organization found | yes | the text, or the CLI's existing "no organization" error and exit code | the CLI's own handling |
| one-off `feedback` | 8.3's refusals, the existing validation | yes | `OrgError` with the text; nothing written | tool call event |
| one-off `feedback` | the note's delivery fails (`OSError`) | yes (retry) | the error; the pipeline writes the file last and atomically, so nothing half-written | as today |
| one-off `feedback` reply step | `feedback_step` raises `OrgError`/`OSError` | yes | no step (MCP `_step`'s rule, unchanged) | no |
| health `counts` | a mailbox cannot be read | as today | the error propagates to the health caller (MCP tool error, CLI error, the review cycle as today) | as today |
| health `counts` | a service's contract or stored versions cannot be read or do not parse | yes | that service's escapes are `untyped` (counted); root's text adds `causes unknown ({service}: {error})` | no |
| `OrgHistory.changes` | anything | n/a | `None` or `[]`, never raises | no |

Errors are never swallowed silently: each one becomes visible text in the part it affects, with the error's words (`clip_line(str(exc), 200)`),
or `does not parse ({exception type})` for a file that does not parse. `quality` never raises on a file that does not parse (12.1).

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
| I3 | A zero denominator is never a pass, and nothing compared is never `no` | `progress._quality_render.ratio` and the alarm states (`n/a ({k} of {min} judged cases)`, `n/a (0 of 0 cases compared)`) | the renderer is the only place rates become text |
| I4 | One user's-runs function and one approved-runs function | `reflection.user_cost` and `reflection.user_approved`, 0a.3's, read by `case_total` and `cost_alarm` (a test asserts equal figures on the same case); `case_spend` is the total, shown on its own line | 0a.3 put them in reflection for the warning, and D-E5-6 has the alarm read the same pair |
| I5 | One cause typing and one attribution | `reflection.cause_of` and `reflection.attribution`, read by the view's verifier line directly and by health through `CaseSignedDeliveries` (a test on one world compares, per verifier, the view's counted and `not its` escapes with health's `escapes` and `not_its`; deliveries not as delivered are left out of that world, D7) | health may not import reflection; the adapter only converts |
| I6 | One-off verdicts default to `relayed` on root's MCP tool and `Org` | `dispatch.provenance_source` (existing) and MCP root `feedback`'s default; the CLI's `human` default is the user's own seat | the sender is the single layer every write passes |
| I7 | `quality` is root's only, and so is health's `not its` split | `mcp_server` (`root_only` group; `causes=(me == ROOT)`) and the surface goldens | the factory decides each identity's tools and texts |
| I8 | Agent-written text never enters root's view verbatim | `progress._quality_render` (only root's titles and human-tier words are quoted; paths and model names through `shown_name`; evidence ids filtered; playbook lines only in `--json`, marked `agent_written`) | the renderer is the boundary between files and root's prompt |
| I9 | The core is domain-agnostic | `reflection.api` vocabularies; a needle test over the new production modules matches the words `memo`, `meeting`, `code`, `test`, `pull request`, `ticket`, `research` case-insensitively as whole words (`\b...\b`, identifiers split on `_` and case changes) in identifiers and string literals | the vocabularies are named constants of one module, so the pack port of Phase 3 (backlog, 23) has one place to replace them |

## 16. Zero denominators, empty cases, ORG.md and git

- **Rates**: judged coverage, PASS precision, a verifier's escapes and every `k of n` use `ratio`; with `n == 0` they read `n/a (0 of 0)`
  (a verifier with no judged delivery: `escapes n/a (0 of 0) judged`, `PASS precision n/a (0 of 0)`). A ratio of the user's runs to user's approved runs of 0 or
  below reads `n/a (budget 0)`, and the case is named among the cost alarm's skipped cases.
- **Alarms** below `min_judged` judged cases read `n/a ({k} of {min} judged cases)`, never `no`; `no` needs the evaluation to have run. A cost
  alarm whose every case is skipped (`n == 0` compared cases, for example a continued service whose old cases all predate the re-hire) reads
  `n/a (0 of 0 cases compared)`, never `no` (6).
- **A service with no request**: its full block, the exact sample of 9.3 (`cases: 0 (...)`, `verifiers: none (no delivery yet)`, the runs
  header ending `: none`, alarms `n/a (0 of 3 judged cases)`, its contract and playbook marks).
- **No service and no one-off task**: `No cases yet` exactly when no agent offers a service, top-level or nested, and root gave no one-off
  task (9.2 "Which blocks appear"; the empty sample of 9.3). Root's one-off block reads `One-off tasks you gave: none.` when a service exists
  and root gave none.
- **A team whose runs cannot be counted** (4.1, its three reasons, including a done or failed, uncut case with no run log in its window): the
  case line reads `runs not counted ({reason})`, its ratio is `null`, and the cost alarm skips it by name.
- **ORG.md that does not parse**: section 6's defaults and note; every other count still renders (none reads ORG.md, and the auxiliary parts
  degrade per section 13). A committed ORG.md or AGENT.md version that does not parse or is not UTF-8 is not compared and counts in the
  timeline's `skipped`; a charter, contract or playbook file that does not parse degrades its part (12.1's read rule, 13). No file that does
  not parse makes `quality` raise.
- **No git history** (no repository, git missing): the timeline's contract, playbook and top-up marks still render (they come from
  `history/` files and mailboxes); charter and model marks read `unknown (...)`; files are compared with the team's current files, which
  is 0a.2 P3's no-history rule, and the `not as delivered` segment adds `(compared with the team's current files: no org history)` whenever it
  counts at least one (9.2).

## 17. The four review checks, and how each passes

1. **Zero denominators and empty cases.** Every rate goes through `ratio` (`n/a (0 of 0)`), a verifier's escapes included; alarms below the
   minimum read `n/a (k of 3 judged cases)` and never `no`; a cost alarm with no compared case reads `n/a (0 of 0 cases compared)`; a 0 budget
   reads `n/a (budget 0)`; an empty service, an empty org, a record with no delivery (`verifiers: none (no delivery yet)`), a corpus without
   run logs and a team whose runs cannot be counted each have a defined text (16, 9.3). Tests: a parametrized renderer test (I3) over every
   rate with `n == 0`, both empty samples of 9.3 and the no-delivery verifier line; alarm tests at 0, 1 and 2 judged cases, and a cost alarm
   over 3 judged cases whose runs are all not counted; the empty samples as goldens.
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
   `cause_of` takes them as an argument (tests pass other words). 0b adds no port through which a pack supplies its own words or its mapping
   onto the failure classes; that port is Phase-3 work (backlog, 23). I9's needle test fails on a domain word in the new modules. The
   samples' memo titles are data.

## 18. Testability and the test plan

### 18.1 Unit tests (pure functions and fakes)

- `reflection`: `deliveries_of` (the verdict-after-the-result rule: a verdict on a blocked result that later turns done; superseded only by a
  task sent after the result; counted and voided around an edit with verdicts before and after it; `written == 0`), `not_on_a_delivery`,
  `signer_of` (moved tests from health), `unjudged_cases`, `judged_cases`, `cause_of` (one test per rule, every precedence pair, `also` with a
  same-type later rule (empty) and a different-type one, `rules`, `before_verdict`, legacy reworks, a `none` link, a "same as R<j>" link
  resolved, a custom `lasting`; a removal-only answer: the answering version removes C6 and its product link names C6, a carried criterion,
  so the escape is `contract-gap` by rule `answer` with the "removes" text, never `reviewer-miss`; a mixed link naming a carried, kept
  criterion and a missing one: `reviewer-miss` with `contract-gap` in `also`; named criteria with `carried=None`: `untyped`, rule
  `unreadable`, `contract v{n} is not stored`), `attribution`, `failure_class`, `repeat_alarm` (window, subjects from `confirmed`, `about`
  and R links, unconfirmed links, a reject not on a delivery, one-off, two subjects firing in 6's order, `not counted` under `n/a`),
  `cost_alarm` and `over_cost` (exact equality at 1.25 x 20 = 25 on the user's runs and the user's approved runs, a user's approved runs of 0, runs
  not counted, open and blocked cases; a case with relayed runs compares only the user's runs; `case_total` and `cost_alarm` read equal figures
  on one case: I4; 3 judged cases whose
  runs are all not counted read `n/a (0 of 0 cases compared)` with JSON `compared: 0`; the skipped list under `n/a` by `min_judged`),
  `quality_thresholds` (each validation rule, unknown keys, numeric strings, the clamp note), the first delivery (4.3: a head blocked and its
  rework done gives the rework's delivery and outcome; no delivery at all gives `never delivered ({case state})`), the playbook
  mark counts against the cited criteria (P1's own replays as fixtures), the one-off chain builder, `chains` (`since=None` keeps every
  request; `runs=False` reads no run log, charter or playbook file), `runs_unknown` (assignee retired; a charter `created` after the head
  task; a charter that cannot be read, is not UTF-8 or does not parse gives no mark; a done or failed, uncut case with no stamp in its window
  gets `no run log in its window`, while a cut, blocked or open one does not), `RunCounter.stamps` (credited stems, boundaries of the
  relayed interval); `DerivedCaseRecords` over fakes whose `SERVICE.md` read, stored versions, playbook versions or P3 call raise a
  non-`OSError` exception (fakes whose `criteria`, `chains` and `one_off_cases` raise one too: labels `the criteria` and `the cases`): the record's
  `error` (or `files_error`) is set, the other records build, and `deliveries()` types the escapes
  `untyped` with the service in `unknown`.
- `progress`: `ratio`; the renderer over `FixedCaseRecords` (every line and variant of 9.2, limits, `shown_name` on paths, the no-history
  remark, a record with `error`, the blank-line layout, `No cases yet` against a defined service with no request, `verifiers: none (no
  delivery yet)`, a signer with no judged delivery, a nested service named by `service=`); `quality_data` against 9.4 (keys, types, null
  rules); `held_tasks` and `left_blocked` (mail.moved_past released, superseded, verdict after the block, a later task
  inside the chain, a held task with nothing sent since, budget 0).
- `app`: `GitBarHistory` over a fake `OrgHistory` (a version that is not UTF-8 and one whose frontmatter does not parse are not compared,
  give no mark for either pair they belong to, and count once each in `skipped`; the bound and `truncated`).
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
  without `.git`; **files that do not parse** (DR2-2), in one git org: snapshot 1 commits a good ORG.md and AGENT.md, snapshot 2 an AGENT.md
  whose frontmatter does not parse, snapshot 3 that AGENT.md repaired with an edited body, snapshot 4 an ORG.md that does not parse (also the
  working file); `quality` renders the thresholds' defaults and their note, every count of the service block, no charter mark (both pairs of
  the bad AGENT.md version are not compared) and `(2 version(s) not compared: larger than 64 KiB, unreadable or not parseable)`, and raises
  nothing; in the same org, a working AGENT.md that does not parse leaves its cases' runs counted, and a stored `SERVICE.v1.md` that does not
  parse turns that service's block into `{service} (offered by {owner}): cannot be read ({label}: does not parse (...)).` while the one-off
  block and the moved-past section render.
- e2e: the replays of section 19 (`TESTS/e2e/test_org_growth_0b_replays.py`) and the published-count cost checks
  (`TESTS/e2e/test_org_growth_0b_costs.py`).
- What stays manual: nothing in the product; the noise study (section 20) is a study.

### 18.3 Test policy (the owner's, binding from the first commit)

The owner's rule ("scope tests to verify changes and run all of them only in the end after everything is integrated") applies as written in
`/Volumes/workspace/hirearchy/docs/research/org-growth/phase-0a2/test-policy.md` (untracked, in the main checkout only): per commit a FAST scoped run (the commit's targets, `tests/golden`,
`tests/architecture` without the static-checks test, `src/hirearchy/app/tests` only when the commit touches `app/`, an `api.py` Protocol or
the wiring, and `scripts/static_checks.py all`); per FEAT one SCOPED run (the union of the FEAT's targets plus `tests/e2e`, `tests/golden`,
`tests/architecture`, `src/hirearchy/app/tests`); no full suite during development; one `scripts/check.sh` on the integrated, rebased branch in
the final validation. A flake in a scoped run is re-run once as one file and noted; the flaky golden screen test is fixed, not retried (11.5).

## 19. Exit-check replays (deterministic; "alarms checked on replayed E/E2/A5 files", plus E3 and E4)

### 19.1 The replay kit (`TESTS/testkit/org_replay.py` and `TESTS/testkit/org_replay_manifest.py`, test-only)

`materialize(corpus, root, variant=None) -> Path` builds an organization directory from a corpus's kept files, read-only from the repository
(`testkit.REPO / "studies" / ...`), following the corpus's **manifest** (`org_replay_manifest.MANIFESTS[corpus]`, plain data, one entry per
corpus E, E2, A5, E3, E4-s1r, E4-s2r, E4-s3 and, by the amendment of 19.5, E5-s1, E5-s2, E5-s3, E6-s1, E6-s2, E6-s3). A manifest pins:
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
    `memo-2026-10-19.md` 22:33:02.155Z (line 39, call #87);
  - E5 (the assistant's `cp` of the team's file, `deliverables-log.txt`): s1 `memo-2026-10-05.md` 2026-10-24T03:12:35.854Z (line 3, call #23),
    `memo-2026-10-12.md` 03:22:12.233Z (line 12, call #42), `memo-2026-10-19.md` 03:28:11.906Z (line 27, call #58); s2 `memo-2026-10-05.md`
    03:45:21.122Z (line 3, call #27), `memo-2026-10-12.md` 03:57:34.246Z (line 12, call #50); s3 `memo-2026-10-05.md` 04:18:31.904Z (line 3, call
    #39), `memo-2026-10-12.md` 04:33:46.819Z (line 14, call #65). The final `memos/` files equal the sandboxes' `deliverables/` copies by md5
    (e5-gate 1.4);
  - E6 (the assistant's `cp` of the team's file, `deliverables-log.txt`; memo 1 was copied twice in s1 and s3, and the pin is the last write): s1
    `memo-2026-10-05.md` 2026-10-24T15:59:09.266Z (line 12, call #45), `memo-2026-10-12.md` 16:09:25.486Z (line 24, call #61), `memo-2026-10-19.md`
    16:20:53.664Z (line 35, call #73); s2 `memo-2026-10-05.md` 16:45:22.100Z (line 3, call #31), `memo-2026-10-12.md` 16:59:33.715Z (line 13, call #53);
    s3 `memo-2026-10-05.md` 17:29:19.322Z (line 12, call #44), `memo-2026-10-12.md` 17:33:53.245Z (line 23, call #52). The final `memos/` files equal the
    sandboxes' `deliverables/` copies by md5 (e6-gate 1.4: 7 of 7).
- E5's and E6's three streams each keep E4's layout: `msgs/` (E5: no `inbox` folder in s2 and s3; E6: the eight non-empty boxes `read`, `sent` and
  `lead-`, `lead-reviewer-`, `lead-writer-` `read`/`sent`, no `inbox` folder), `run-logs/{lead,lead-reviewer,lead-writer}`, `service/` and
  `playbook/` (`history--*.md` and `current-*.md`; the `SERVICE.<hash>.md` copies are not read), `org-files/`, and `memos/` with
  `versions/INDEX.txt`.
- `variant` (E3 only, `"r2-links-r1"`, 19.3 E3-7): one more root note, a copy of `...-root-8ca0`'s frontmatter with `id:
  20261021T154600000000-root-0b01`, `created: '2026-10-21T15:46:00+00:00'`, `criterion: R1`, title `criterion link on "Memo for the meeting
  of 2026-10-19": R1`, replying to `...-root-5c11`, `source: human`: a human-tier "same as R1" link on R2, written to root's `sent/` and
  lead's `read/`.
- `variant` `"r3-overspend-{N}"` (E3 only, N = 12 or 11, 19.3 E3-9) is **a constructed variant, not an observation**: the kit adds N empty run
  logs of `lead` named `20261021T1543000000{01..N}.log` (21-character stamps inside case ab46's window, which runs from 15:38:09.201054 to
  its last result at 15:43:42.518435). No study corpus fires the cost alarm under D-E5-6's rule (19.3, 19.4), so this variant is the only
  replay in which it fires; the kit's docstring, the test's name and docstring and the manifest entry all say "constructed".
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
| runs, spend, relayed runs | no (no logs: done or failed, uncut cases read `runs not counted (no run log in its window)`, 4.1 reason 3; the others read 0) | no (same) | no (same) | yes | yes (credits: none existed) |
| cost alarm | by published counts (19.4) | by published counts | by published counts | yes | yes |
| repeat alarm | yes | yes | does not apply | yes | yes |
| top-ups | yes | yes | yes | yes | yes |
| contract and playbook marks | yes | yes | n/a | yes | yes |
| charter and model marks | no (no git) | no | no | no | no |
| not as delivered | no (no folder) | no | no | no | yes (current-file rule) |
| moved past, held tasks | yes | yes | yes (root's and the lead's boxes only) | yes | yes |
| held figure | no: the derived budget needs the run logs; the view prints a figure that ignores the runs not kept, and no replay asserts it | no | no | yes | yes (s1r: pinned to its final `status`) |

**E5 s1-s3** (`E5-org-growth-0a2-recheck/evidence/<s>/`; kept as E4 kept: every box under `msgs/`, `run-logs/`, `service/` and `playbook/`,
`org-files/`, `memos/` with `versions/INDEX.txt`, `deliverables-log.txt`; no git, `org-git-log.txt` is a text log) take the E4 column of the table,
with two differences. No run credit exists (0 throttles in 97 runs: `credited` is 0 in every case), and the held figure is not asserted: s3's writer
holds 2 runs behind a blocked task that nothing was sent after, which 4.5 does not list (OQ-4 decided: no), so the replay has no figure to compare
with the recorded `status`. Because the organization has no git history, P3 compares each deliverable with the team's current file and never finds
a `relayed` file (19.3 E5).

**E6 s1-s3** (`E6-org-growth-0a3-recheck/evidence/<s>/`; kept as E5 kept, service `weekly-memo`; no git, `org-git-log.txt` is a text log) take the E4
column of the table, with two differences from E5. No run credit exists (0 throttles in 105 runs: `credited` is 0 in every case). The held figure is
asserted in s2 and s3, where the lead's writer holds a blocked task that the lead moved past by sending it another task (4.5 lists it): 2 and 4
runs, equal to the recorded `status` (`budget=2`, `budget=4`); s1 has no held task. Because the organization has no git history, P3 compares each
deliverable with the team's current file and never finds a `relayed` file (19.3 E6).

### 19.3 Pre-registered expectations (one test per id)

**When an expectation fails** (DR2-13). Each expectation below is written before its test runs. If a replay computes another value, the
coder does not edit the expectation, the golden or the rule to make them agree: the FEAT stops, and the coder sends the manager a warning
with the expectation's id, the computed value, the expected one and the kept files that show it. The expectation changes only by an
amendment to this design that the manager approves; the same holds for 19.4 and for the goldens of 9.3.

**E**
- E-1: one record `weekly-memo` (lead; client root, human); 3 cases (`20261018T021644679563-root-b495`, `20261018T022344643603-root-c686`,
  `20261018T024234965290-root-2c75`); 3 deliveries (b495 by `...-lead-e6b8`, c686 by `...-lead-52d5`, rework
  `20261018T022845034488-root-5bae` by `20261018T024337814874-lead-e73a`); judged 1 of 3 (b495, accept `...-root-f538`); first deliveries
  1 accepted (b495), 0 rejected, 1 without a verdict (c686, superseded by rework 5bae, tier not recorded), 1 never delivered (2c75,
  blocked); 1 case without a verdict (c686: its latest delivery e73a, 02:43:37, has no verdict after it; the accept
  `20261018T024152961586-root-550c`, 02:41:52, was given on 5bae's blocked result `...-lead-4b37` and is not read as the accept of e73a);
  2 verdicts not on a delivery (550c, and `20261018T025414374460-root-86de` on 2c75's blocked result); 0 escapes; 3 legacy verdicts;
  c686's window is cut by 2c75 (1 cut case).
- E-2: repeat `n/a (1 of 3 judged cases)`; cost `n/a (1 of 3 judged cases); skipped: 20261018T021644679563-root-b495 (runs not counted)`;
  b495 (done, its window not cut, no run log kept) reads `runs not counted (no run log in its window)`; c686 (its window cut) and 2c75
  (blocked) read 0 runs; asserted together with the corpus note (no run log kept) in the test's docstring.
- E-3: top-ups of c686: +5 rework 5bae (tier not recorded), +3 and +1 grants (`...-root-c1c5`, `...-root-f2a7`).
- E-4: timeline: contract v2 and v3 `not confirmed`; playbook v2 and v3 `no admission recorded (written before the evidence gate)`; charter
  and model marks unknown.
- E-5: moved past: `lead/writer` with one task, `20261018T023352181048-lead-a489` from lead, blocked 2026-10-18 02:34 (`...-lead.writer-f27d`),
  `left blocked: lead has sent lead/writer 3 task(s) since` (5875, 50f8, b6a7); no other held task of the writer; root's 2c75 is released by
  the verdict 86de (`mail.moved_past`) and not listed; the held figure is not asserted (19.2).

**E2**
- E2-1: one record `meeting-memo`; 3 cases; 6 deliveries; judged 5 of 6; first deliveries 1 accepted (`...-root-55ff`), 1 rejected
  (`...-root-e29b`), 1 without a verdict (`...-root-d22b`, superseded by rework `...-root-d90e`, tier not recorded); 0 cases without a verdict;
  0 verdicts not on a delivery; 5 legacy verdicts; 0 cut cases.
- E2-2: 2 escapes, both `untyped` (no rule matched): R1 on `...-root-d90e` (the assistant's own rework, whose `source` was never recorded, so
  `relayed-error` cannot fire on these files) and R2 on `...-root-e29b` (the Marta row); no link exists and no lasting word occurs. The
  view's verifier line: `lead/reviewer: escapes 2 of 5 judged (2 untyped); PASS precision 3 of 5; ...`.
- E2-3: repeat `no (3 judged cases; counted: R1, R2)`; cost `n/a (0 of 0 cases compared); skipped:
  20261018T034955412135-root-d22b, 20261018T040120119761-root-55ff, 20261018T040509774983-root-e29b (runs not counted)`: the three cases are
  done, no window is cut and no run log was kept, so each case line reads `runs not counted (no run log in its window)` (4.1 reason 3) and
  nothing is compared (6).
- E2-4: health on these files: lead/reviewer judged 5, escapes 2 (untyped, counted), not flagged (0.4 is not above 0.5), as 0a 5.5 predicted;
  root's text has no `not its` part.
- E2-5: timeline: contract v2 and v3 not confirmed; playbook v2 (lead) and v3 with no admission recorded.
- E2-6: moved past: none.

**A5**
- A5-1: no service record; the one-off record has 1 case (`20261017T214038108044-root-f768`, tasks f768, `...-root-00cd` and `...-root-dfe0`,
  both reworks revising f768 with the tier not recorded); 3 deliveries (`...-lead-463e`, `...-lead-82b3`, `...-lead-26db`); judged 0 of 3;
  the first delivery without a verdict, superseded by dfe0 (the first task sent after 463e); 1 case without a verdict (f768), never counted as
  accepted; escapes `none (judged: 0 of 3)`; 0 verdicts not on a delivery.
- A5-2: repeat `does not apply`; cost `n/a (0 of 3 judged cases); skipped: 20261017T214038108044-root-f768 (runs not counted)`; top-ups +4,
  +4 (tier not recorded) and +3 (grant `...-root-7620`); the case reads `runs not counted (no run log in its window)` (done, uncut, no log
  kept; the lead's charter `created`, 21:40:38, is not after the head task, 21:40:38.108044, so reason 2 does not apply).
- A5-3: every delivery is signed off by `lead` (the reports' boxes were not kept).
- A5-4: the one-off block of 9.3's A5 sample equals the output's block byte for byte; moved past: none.

**E3** (go/no-go item 8)
- E3-1: 0 cost alarms: the user's runs 12, 5 and 14 against 15, 15 and 20 approved (0.80x, 0.33x, 0.70x; totals 12, 15, 14); cost `no (0 of
  3 cases above 1.25x)`. The approved runs are the contract's 15, raised only at ab46's rework (`...-2ccf`: 9 used + 6 held + 5 = 20); at dd87's
  rework (`...-d995`: 4 used + 2 held + 6 = 12) nothing is raised.
- E3-2: R1's unconfirmed link (C6, C3, the rejection's own `criterion`) is not counted by the repeat alarm and is listed as `not counted`.
- E3-3: the superseded `...-root-248f` is not counted as a block moved past; the section is `none`.
- E3-4: contract-gap rejects are not shown as verifier escapes: R1 `contract-gap` (words, "always"), R2 `contract-gap` (answer, link
  `...-root-8ca0` names C11, not in contract v2), both attributed `not its`; the view's verifier line is `lead/reviewer: escapes 0 of 5
  judged; not its: 2 contract-gap; PASS precision 5 of 5; its FAILs before delivery: 2 re-check(s), 2 author rework run(s)`; health for root
  `escapes 0 of 5 judged (+2 not its: 2 contract-gap)`, for an agent `escapes 0 of 5 judged`; not flagged.
- E3-5: the text of 9.3's E3 sample equals the output byte for byte (a golden of the replay).
- E3-6: case `...-root-207b` has 10 runs in relayed reworks; its user's runs are 5 (total 15), and its relayed line reads `your relayed
  reworks: 10 run(s), your own spend; total 15`.
- E3-7 (the variant `r2-links-r1` of 19.1, so that a replay on real files shows the repeat alarm firing): `repeat: FIRES: R1 failed in 2 of
  the last 3 judged cases (cases 20261021T152347923195-root-dd87, 20261021T153809201054-root-ab46)`; R2's cause is unchanged (contract-gap by
  answer: C11 stays in R2's `confirmed`); the cost line is unchanged.
- E3-8 (DR2-7): `quality --json` on E3's files conforms to 9.4 (keys, types, null rules) and equals the golden
  `tests/golden/expected/quality/e3.json`; every count in it equals the figure of the E3 text sample (9.3) that 9.4's source column names
  (for example `deliveries.total` 6 and `judged` 5, `cases[*].user_cost` 12, 5, 14, `user_approved` 15, 15, 20, `relayed_runs` 0, 10, 0,
  `spend` (the total) 12, 15, 14 and `ratio` `"0.80"`, `"0.33"`, `"0.70"`,
  `alarms.cost.compared` 3, `alarms.repeat.not_counted` `{"R1": ["C6", "C3"]}`, `verifiers[0].pass_precision` `[5, 5]`). The golden is
  written once, deliberately (`HIREARCHY_UPDATE_GOLDEN=1`), in FEAT-9 and reviewed key by key against 9.4 and the text sample. The
  conformance test also checks one error record (DR3-3).
- E3-9 (D-E5-6; **a constructed variant, not an observation**, 19.1): with `r3-overspend-12`, case `...-root-ab46` has 26 charged runs, the
  user's runs 26 against 20 approved (1.30x), and the alarm reads `cost: FIRES: case 20261021T153809201054-root-ab46 26 of 20 approved (1.30x)`;
  with `r3-overspend-11` the user's runs are 25, exactly 1.25 x 20, and the alarm reads `cost: no (0 of 3
  cases above 1.25x)`. The two replays pin the boundary of `Fraction(user_cost) > cost_ratio * user_approved` on files. **No study corpus fires
  the cost alarm under this rule** (E3, E4's three streams: 19.3; E, E2, A5: 19.4), which is why the variant exists.

**E4** (the gate's item 8, then 0b's own)
- S2R-1: s2r's playbook v2 is shown with content beyond C9: its mark reads `admitted (c) on R1, C9: 7 changed line(s): 0 the cited criteria's
  own words, 7 beyond them; 4 line(s) removed`, and its `--json` `lines` carry the two vague-deadline lines the gate quotes, next to C9's text in `cited`.
- S1R-1: s1r's four unconfirmed amendments are not counted as client evidence: every criterion v2-v5 added except C9 is marked `not
  confirmed`; none is a repeat subject or a contract-gap answer; C9 is confirmed by link `...-root-1753` (0a.1's rule for a version without
  `answers`).
- S1R-2: s1r's unrecorded rejects 2 and 3 are shown as missing verdicts: cases `...-root-114d` and `...-root-2efa` are without a verdict and
  never counted as accepted; judged 1 of 3.
- S2R-2: s2r's Marta escape is typed as a relayed carry-over: R2 (`...-root-f6dc` on `...-root-342a`) is `relayed-carry-over` through
  `...-root-43b8` and `lead/writer/work/2026-10-05-memo.md`, `also contract-gap` (the link `...-root-d23a` names C10, which contract v1 of
  342a lacks); `rules` starts `["carry-over", "answer"]`.
- S1R-3: s1r's 16 runs are shown as held behind blocks the conversation moved past: `lead holds 12 run(s)` with task `...-root-3559`
  (`left blocked: you have sent lead 2 task(s) since`), and `lead/writer holds 4 run(s)` with `...-lead-e679` (`left blocked: lead has sent
  lead/writer 1 task(s) since`) and `...-lead-808c` (`blocked, nothing sent since`); `...-lead-0d54` is not listed (`...-lead-cc98` revises
  it, so it is released). The replay derives 12 and 4 from the materialized files; they must equal s1r's final `status` (lines 31 and 34 of
  `final-services-progress-status-health.txt`), and a difference fails the test and stops the FEAT (the rule above: the expectation is not
  adjusted).
- S1R-4: the three final memos are not as delivered (they differ from the team's current files; no `relayed` finding exists, since the corpus
  predates 0a.3), with the no-history remark; R1 (recorded
  18:59:00) predates the last write of `memo-2026-10-05.md` (19:12:45.031, pinned in the manifest), so it is counted and stays an escape (D20);
  the deliveries of `...-114d` and `...-2efa` have no verdict, so they count as neither pass nor escape; 0 deliveries judged after an edit.
- S1R-5: R1 is `contract-gap` (answer: link `...-root-1753` names C9, not in contract v1), signed off by lead/checker, with no `also` (rule 5
  matches "always" too, the same type; `rules` = `["answer", "words"]`); case `...-root-ed94`: the user's runs 18 of 19 approved (0.95x) (`user_spend` is 19; one relayed run may lie in a later request, so `user_cost`
  leaves it out), 5 of its 23 runs in
  relayed rework `...-root-9ce9`, and its window is cut; repeat and cost `n/a (1 of 3 judged cases)`.
- S1R-6: every line of 9.3's s1r excerpt that has no angle brackets equals the output's line byte for byte.
- S2R-3: R1 (`...-root-a9fd`) is `contract-gap` (answer: link `...-root-b255` names C9), with no `also`, and `before_verdict`
  `...-root-43b8`; case `...-root-f230`: the user's runs 14 of 24 approved (0.58x), 5 in relayed rework 43b8, total 19; judged 2 of 3 deliveries (43b8's delivery is
  superseded by human rework 342a); alarms `n/a (1 of 3 judged cases)`; not as delivered 0; the view's verifier line `lead/reviewer: escapes 0
  of 2 judged; not its: 1 contract-gap, 1 relayed-carry-over; PASS precision 2 of 2; ...`; health for root `escapes 0 of 2 judged (+2 not its:
  1 contract-gap, 1 relayed-carry-over)`; moved past: none.
- S3-1: no cost alarm fires (this was a firing expectation before D-E5-6): `...-root-88b2` the user's runs 16 of 25 approved (0.64x), 5 in
  relayed rework `...-root-fe20`, total 21; `...-root-cdef` 5 of 15 (0.33x), 5 relayed, total 10; `...-root-6947` 15 of 18 (0.83x); the alarm reads
  `no (0 of 3 cases above 1.25x)`.
- S3-2: R1 (`...-root-ac19` on `...-root-4510`) is `contract-gap` (answer: link `...-root-1fb7` names C8, not in contract v1), with no
  `also`, and `before_verdict` `...-root-fe20`; repeat `no (3 judged cases; counted: R1, C8)`.
- S3-3: first deliveries 0 accepted, 0 rejected, 3 without a verdict, all superseded (`...-88b2` by human rework `...-4510`, `...-cdef` by
  relayed rework `...-116b`, `...-6947` by human rework `...-3286`); judged 4 of 8 deliveries; not as delivered 0.
- S3-4: the user's accept on relayed rework `...-root-116b` counts as a judged delivery (F-E3-10); the view's verifier line `lead/reviewer:
  escapes 0 of 4 judged; not its: 1 contract-gap; PASS precision 4 of 4; ...`; health for root `escapes 0 of 4 judged (+1 not its: 1
  contract-gap)`.
- S3-5: moved past: none (the reviewer's blocked `...-lead-2133` is released by `...-lead-00e8`, which revises it).
- E4-all: no charter or model mark (no git): the unknown line in every block.

**E5** (amendment of 19.5, written for plan commit 45 from `RESEARCH/phase-0a2/e5-gate.md` section 4 items 2-8 and the committed evidence
`studies/E5-org-growth-0a2-recheck/evidence/s1` to `s3`, never from the product's output). Every stream is one service `weekly-meeting-memo`
(offered by `lead`, client root, human; contract v1 with a per-request budget of 12, v2 after the user's answer; playbook v1, v2 after the
lead's revision) with three cases, one per memo; memo 1's chain holds the facilitator's injected relayed rework (5 runs). The run figures come
from a throwaway ledger that reads the kept files and the published counts and imports no product code (commit 1's, extended to E5), under
`b252d77c`'s rules; the structural facts (cases, deliveries, verdicts, links, signers) are read from the message files, the FAIL counts from the
recorded `final-services-progress-status-health.txt` of each stream. Short ids below are the suffixes of full ids: `...-root-f07a` is
`20261024T030644000395-root-f07a`.

**What a replay of these files cannot show (kit limit).** The replay has no org git history, so OQ-2's given-delivery path and P3's `relayed`
finding cannot run; with history the evidence shows s1 and s2 relayed (no hand edit) and s3 differs (md5 facts below). The kit materializes no git repository, so P3 does not know the checked artifact of a past
delivery and compares each file with the team's current one (4.3, "no org history"). Two consequences, stated once for the three streams: no
`relayed` finding (0a.3, F-E5-5) arises, so the given delivery of every case is its latest delivery (OQ-2's "else") and a case whose latest
delivery is the injected relayed rework reads `without a verdict (relayed only)`; and memo 1's file is `not as delivered` against that injected
delivery in s1, s2 and s3. The facts that an org history would show instead are pre-registered below as **evidence facts** and asserted on the
kept files (md5 against `memos/versions/INDEX.txt`), not on the product; the two paths the replays cannot take, the given delivery read through a
`relayed` finding (OQ-2) and the `relayed` finding itself (OQ-3), are run on a real git history by `tests/e2e/test_org_growth_0b_given.py` (a synthetic organization with real commits).

**The user's approved runs** (OQ-1, the first live inputs of 0a.5 A2): the rule is `max(budget, ceiling)`, with the ceiling at each hand-down of
the user's requests = the runs those requests had used + what the team still held + the hand-down's budget. s1: no grant; at the human rework
`...-aae2` the user's requests had used 5 runs and held none (7 had come back), so 5 + 12 = 17 (the same at `...-ee21`). s2: at `...-6c4f` they had
used 9 and held none, so 9 + 5 = 14; at `...-367d` they had used 5 and held 2, so 7 + 5 = 12, the budget. s3: at `...-c209` 9 used, none held,
9 + 3 = 12; the grant `...-595d` (root's note, 2 runs, after the user's yes) came when 11 had been used and 1 was held: 12 + 2 = 14. The gate's
figures (e5-gate 4 item 2: 15, 17 and 14 approved) were its own reading and are replaced by these (17, 14 and 14 for memo 1, and 17 for s1's
memo 3, under 0a.5 A2; manager approval of 2026-10-25).

**E5 s1** (`E5-s1`; cases `...-root-f07a`, `...-root-f549`, `...-root-312a`)
- E5S1-1: the record `weekly-meeting-memo` (lead; client root, human; contract v2, playbook v2, budget 12); 3 cases, done 3, none cut; no one-off
  record and no nested service; 6 deliveries: f07a by `...-lead-bb5a`, its human rework `...-root-aae2` by `...-lead-5cbe`, the relayed rework
  `...-root-963a` by `...-lead-592f`, f549 by `...-lead-9525`, 312a by `...-lead-8fdf`, its human rework `...-root-ee21` by `...-lead-1757`; judged
  3 of 6 (aae2: reject `...-root-99d4`; f549: accept `...-root-4265`; ee21: accept `...-root-359a`); first deliveries 1 accepted (f549: "That one
  is right, all the items are there - keep it."), 0 rejected, 2 without a verdict (f07a superseded by the human rework aae2, 312a by the human
  rework ee21), 0 never delivered; 1 case without a verdict, f07a, because its latest delivery is the relayed rework 963a, which carries only the
  assistant's relayed reject `...-root-61fd` (`relayed only`: 1; `unseen relayed`: none; the user's own verdict `...-root-99d4` is on aae2, the
  version she was given: the evidence fact of E5S1-6); 0 verdicts not on a delivery; 0 legacy verdicts (every note carries `source`). The line is
  `judged by the user: 3 of 6 deliveries; without a verdict: 1 case(s) (20261024T030644000395-root-f07a): never counted as accepted (1 with only
  your own relayed verdict); not as delivered: 1 ...`.
- E5S1-2: one escape, R1 = `...-root-99d4` (a human reject; its own `criterion` is C3) on the delivery of aae2, case f07a, signed off by
  lead/reviewer (the latest done result of a direct report before the delivery is `...-lead.reviewer-f2db`): `contract-gap` by rule `answer`
  (the human link `...-root-8376` names C8, which contract v1 of aae2 lacks; the answering contract v2 removes nothing), `rules` `["answer",
  "words"]` (the user's words "Always start the memo" carry a lasting word), `detail` `["20261024T031733594650-root-8376", "C8"]`, `also` none,
  `before_verdict` `...-root-963a` (its done result `...-lead-592f`, 03:15:35, lies between the delivery's, 03:12:27, and the verdict, 03:16:28),
  attribution `not its`. The escape line is `R1 case 20261024T030644000395-root-f07a, signed off by lead/reviewer: contract-gap (the user's answer, link
  20261024T031733594650-root-8376, names C8, which contract v1 of the task did not have); your relayed rework 20261024T031317713451-root-963a delivered
  after it and before the verdict: the user may have judged that version`. Rule 2 cannot match (the relayed rework 963a was sent after the rejected
  task, and no human rework followed it: M-P4-1 n/a (0 of 0)). The verifier line is `lead/reviewer: escapes 0 of 3 judged; not its: 1
  contract-gap; PASS precision 3 of 3; its FAILs before delivery: 0 re-check(s), 0 author rework run(s)` (the recorded health line of the reviewer:
  re-checks after a FAIL 0, author rework runs 0); health for root `escapes 0 of 3 judged (+1 not its: 1 contract-gap)`, for an agent `escapes 0 of
  3 judged`.
- E5S1-3: contract v1 `2026-10-24 03:06 contract v1 (C1, C2, C3, C4, C5, C6, C7)`; playbook v1 `03:06 playbook v1 (root): written by the client (no
  admission needed)`; contract v2 `03:17 contract v2 (root): adds C8: the user's answer to R1: C8 confirmed (link 20261024T031733594650-root-8376)`
  (DR3-1; JSON `basis` `answers`, `answers` `R1`, `confirmed` `[{"id": "C8", "link": "20261024T031733594650-root-8376"}]`, `not_confirmed` `[]`);
  playbook v2 `03:19 playbook v2 (lead): admitted (c) on C8, R1, 20261024T031733594650-root-8376: 1 changed line(s): 1 the cited criteria's own
  words, 0 beyond them` (the one line it adds is `- C8: ` and C8's text, `removed` 0); top-up marks at 03:10 (+12 human rework aae2), 03:13 (+6 your
  relayed rework 963a, your own spend) and 03:25 (+12 human rework ee21); no charter or model mark, and the unknown line.
- E5S1-4: f07a "Memo for meeting 2026-10-05": the user's runs 10 of 17 approved (0.59x), top-ups `+12 human rework ...-aae2, +6 your relayed rework
  ...-963a`, relayed runs 5, total 15 (`your relayed reworks: 5 run(s), your own spend; total 15`), 15 charged runs, `credited` 0; f549: 5 of 12
  (0.42x), top-ups none; 312a: 10 of 17 (0.59x), `+12 human rework ...-ee21`; none cut ("0 case(s) had their window cut").
- E5S1-5: repeat `no (3 judged cases; counted: R1, C8); not counted: R1's reading C3 (not confirmed)` (JSON: `window` f07a, f549, 312a, `subjects`
  `{"R1": 1, "C8": 1}`, `fired` `[]`, `not_counted` `{"R1": ["C3"]}`); cost `no (0 of 3 cases above 1.25x)` (`compared` 3, `skipped` `[]`).
- E5S1-6: evidence facts: the delivered `memos/memo-2026-10-05.md` (md5 `9b0c922458c56a01709a32ed01b48857`) is the version `v2` (`8037193`, committed
  03:11:13Z) of `lead/writer/work/memo-2026-10-05.md`, the checked artifact of aae2's delivery (the result `...-lead-5cbe` lists the file modified at
  03:11:04Z), so nobody edited it by hand; the team's current file is `v3` (`137cfe2`, `da83e824f099c2089c1637de5ba5be84`), written by the relayed
  rework 963a. `memo-2026-10-12.md` (`b0616bd6...`) and `memo-2026-10-19.md` (`098a9fee...`) equal the current files. On the replay (no history):
  `not_as_delivered` `[{"case": f07a, "task": 963a}]` (the newest delivery that lists the file is 963a, a relayed rework, and the walk ends at the
  human rework aae2), nothing voided (963a has no human verdict), `neither` `[]`, `files_error` `""`, and the no-history remark on the line.
- E5S1-7: moved past: none (no task of s1 was blocked).

**E5 s2** (`E5-s2`; cases `...-root-ebe2`, `...-root-bfa8`, `...-root-e9ee`)
- E5S2-1: contract v2, playbook v2, budget 12; 3 cases, done 3, none cut; 6 deliveries: ebe2 by `...-lead-f023`, its human rework `...-root-6c4f` by
  `...-lead-35b2`, the relayed rework `...-root-f3df` by `...-lead-0cc8`, bfa8 by `...-lead-4e2a`, its human rework `...-root-367d` by
  `...-lead-a65c`, e9ee (memo 3, which the team reported done at the end and the assistant never copied to the user) by `...-lead-75c7`; judged 2 of 6 (6c4f:
  reject `...-root-ec12`; 367d: accept `...-root-a539`); first deliveries 0 accepted, 0 rejected, 3 without a verdict (2 superseded: ebe2 by the human
  rework 6c4f, bfa8 by the human rework 367d; e9ee not superseded), 0 never delivered; 2 cases without a verdict, ebe2 (its latest delivery f3df
  carries only the relayed reject `...-root-a9cb`) and e9ee (`relayed only`: 1); 0 verdicts not on a delivery; 0 legacy verdicts; 0 cut.
- E5S2-2: one escape, R1 = `...-root-ec12` (a human reject, own `criterion` C3) on the delivery of 6c4f, case ebe2, signed off by lead/reviewer:
  `contract-gap`, rule `answer` (link `...-root-6162` names C8, which contract v1 lacks), `rules` `["answer", "words"]`, `detail`
  `["20261024T035002043490-root-6162", "C8"]`, `also` none, `before_verdict` `...-root-f3df` (its done result 03:48:25 lies between the delivery's,
  03:45:11, and the verdict, 03:49:10), attribution `not its`; rule 2 cannot match. The verifier line is `lead/reviewer: escapes 0 of 2 judged; not
  its: 1 contract-gap; PASS precision 2 of 2; its FAILs before delivery: 1 re-check(s), 1 author rework run(s)` (recorded health line: re-checks
  after a FAIL 1, author rework runs 1); health for root `escapes 0 of 2 judged (+1 not its: 1 contract-gap)`, for an agent `escapes 0 of 2 judged`.
- E5S2-3: contract v1 `2026-10-24 03:37 contract v1 (C1, C2, C3, C4, C5, C6, C7)`; playbook v1 `03:37 playbook v1 (root): written by the client (no
  admission needed)`; contract v2 `03:50 contract v2 (root): adds C8: the user's answer to R1: C8 confirmed (link 20261024T035002043490-root-6162)`;
  playbook v2 `03:51 playbook v2 (lead): admitted (c) on C8, R1, 20261024T035002043490-root-6162: 1 changed line(s): 1 the cited criteria's own words,
  0 beyond them`; top-up marks at 03:43 (+5 human rework 6c4f), 03:45 (+6 your relayed rework f3df) and 03:55 (+5 human rework 367d); no charter or
  model mark.
- E5S2-4: ebe2 "Memo for the 2026-10-05 team meeting": the user's runs 14 of 14 approved (1.00x), top-ups `+5 human rework ...-6c4f, +6 your relayed
  rework ...-f3df`, relayed runs 5, total 19 (`your relayed reworks: 5 run(s), your own spend; total 19`); bfa8: 10 of 12 (0.83x), `+5 human rework
  ...-367d`; e9ee: 5 of 12 (0.42x), top-ups none; `credited` 0.
- E5S2-5: repeat `n/a (2 of 3 judged cases); not counted: R1's reading C3 (not confirmed)` (`window` `[]`, `subjects` `{}`, `not_counted`
  `{"R1": ["C3"]}`); cost `n/a (2 of 3 judged cases)` (`compared` 3, `skipped` `[]`).
- E5S2-6: evidence facts: the delivered `memo-2026-10-05.md` (`e988abb443ca3d4ee60114243c68ce77`) is `v3` (`e4d0466`, 03:44:08Z), the checked artifact
  of 6c4f's delivery (the result `...-lead-35b2` lists the file modified at 03:43:58Z); the current file is `v4` (`a7722bd`,
  `55c23e3980eac289550e03050bc765df`, 03:47:00Z), written by the relayed rework f3df; `memo-2026-10-12.md` (`084c623c...`) equals the current file.
  On the replay: `not_as_delivered` `[{"case": ebe2, "task": f3df}]`, nothing voided, `neither` `[]`.
- E5S2-7: moved past: none (the writer's blocked `...-lead-d3a1` is released by `...-lead-7713`, which revises it).

**E5 s3** (`E5-s3`; cases `...-root-e268`, `...-root-dd39`, `...-root-e0c8`)
- E5S3-1: contract v2, playbook v2, budget 12; 3 cases, done 3 (e268's latest task is the relayed rework daff, done), none cut; 5 deliveries: e268 by
  `...-lead-30ba`, the relayed rework `...-root-daff` by `...-lead-1a15`, dd39 by `...-lead-9037`, its human rework `...-root-57b3` by
  `...-lead-15b2`, e0c8 (memo 3) by `...-lead-462b`; the human rework `...-root-c209` is **no delivery**: both its results, `...-lead-d8cc` and
  `...-lead-d32d`, are `blocked`; judged 1 of 5 (57b3: accept `...-root-33b9`); first deliveries 0 accepted, 0 rejected, 3 without a verdict (2
  superseded: e268 by the human rework c209, dd39 by the human rework 57b3), 0 never delivered; 2 cases without a verdict, e268 (latest delivery
  daff, only the relayed reject `...-root-5c9c`) and e0c8 (`relayed only`: 1); **1 verdict not on a delivery: `...-root-a6fe`, R1, a human reject
  on c209's blocked result** (e5-gate 4 item 3: the team did not report `done`, so the re-check never ran), under `verdicts not on a delivery (on a
  blocked or failed result, or before the done result): 1 (20261024T042421215723-root-a6fe)`; memo 1 (case e268) is not a judged case; 0 legacy
  verdicts.
- E5S3-2: no escape: `escapes` `[]` and `none (judged: 1 of 5)`; R1 is still the assertion R1 (the first human-tier rejection of the service) and
  the contract v2 answers it (E5S3-3). The verifier line is `lead/reviewer: escapes 0 of 1 judged; PASS precision 1 of 1; its FAILs before delivery:
  1 re-check(s), 1 author rework run(s)` (recorded health line: re-checks after a FAIL 1, author rework runs 1), with no `not its` part; health for
  root `escapes 0 of 1 judged`, with no `not its`.
- E5S3-3: contract v1 `2026-10-24 04:08 contract v1 (C1, C2, C3, C4, C5, C6, C7, C8)`; playbook v1 `04:08 playbook v1 (root): written by the client
  (no admission needed)`; contract v2 `04:25 contract v2 (root): adds C9: the user's answer to R1: C9 confirmed (link
  20261024T042515118836-root-d735)` (the link is the human link on the rejection `...-root-a6fe`, which is not an escape); playbook v2 `04:27
  playbook v2 (lead): admitted (c) on C9, R1, 20261024T042515118836-root-d735: 1 changed line(s): 1 the cited criteria's own words, 0 beyond them`;
  top-up marks at 04:14 (+3 human rework c209), 04:15 (+2 your grant `...-root-595d`), 04:19 (+6 your relayed rework daff) and 04:31 (+5 human rework
  57b3); no charter or model mark.
- E5S3-4: e268 "Memo for the 5 October 2026 weekly": the user's runs 13 of 14 approved (0.93x), top-ups `+3 human rework ...-c209, +2 your grant
  ...-595d, +6 your relayed rework ...-daff`, relayed runs 5, total 18 (`your relayed reworks: 5 run(s), your own spend; total 18`); the 18 charged
  runs include the writer run that was killed (`lead-writer/20261024T041458746130.log`: a lost run is charged, D-E5-3) and `credited` is 0; dd39:
  10 of 12 (0.83x), `+5 human rework ...-57b3`; e0c8: 5 of 12 (0.42x), top-ups none.
- E5S3-5: repeat `n/a (1 of 3 judged cases)` (no `not counted` part: the rejection `...-root-a6fe` belongs to no judged case) and cost `n/a (1
  of 3 judged cases)` (`compared` 3, `skipped` `[]`).
- E5S3-6: evidence facts: the delivered `memo-2026-10-05.md` (`0e54cf01763effec9cdffd0dc78fb8da`) is `v3` (`79e86be`, 04:16:59Z), the writer's own
  rework of c209, which no reviewer checked (the lead's re-check was never delegated, F-E5-2) and which no done result lists as checked: the
  checked artifact of e268's delivery is `v2` and daff's is `v4` (`8c5df76116067327ef79e4d9880240ea`, the current file). It is a team file the
  user was given, not a hand edit (OQ-3: the label is `not as delivered`, which asserts no cause). On the replay: `not_as_delivered`
  `[{"case": e268, "task": daff}]`, nothing voided, `neither` `[]`; `memo-2026-10-12.md` (`2a13fe9a...`) equals the current file.
- E5S3-7: moved past: none. Finding for the manager (OQ-4, decided: no): the writer holds 2 runs (the recorded `status`: `budget=2`) behind its
  blocked task `...-lead-4a85` (memo 3), which `mail.moved_past` does not release and after which nothing was sent to the writer, so no task is
  left blocked and 4.5 lists no agent. Its other blocked tasks are released: `...-lead-0a56` by `...-lead-df89`, `...-lead-bed1` by
  `...-lead-711a`; root's blocked `...-root-c209` by `...-root-daff`, each of which revises its predecessor.

**E5 (all three)**
- E5-all: no charter or model mark and `history` `{known: false, truncated: false, skipped: 0}` (the unknown line, once); `credited` 0 in all nine
  cases; no one-off record and no nested service; every `quality_data` conforms to 9.4 (`test_every_corpus_conforms_to_the_schema` covers the
  three manifests).

**E6** (amendment of 19.5, written for plan commit 50 from `RESEARCH/phase-0a3/e6-gate.md` section 4 and the committed evidence
`studies/E6-org-growth-0a3-recheck/evidence/s1` to `s3`, never from the product's output). Every stream is one service `weekly-memo` (offered by
`lead`, client root, human; contract v1, v2 after the user's answer, with a per-request budget of 16 in s1 and s3 and 12 in s2; playbook v1, v2 after
the lead's revision) with one case per memo the user requested: three in s1 and s3, two in s2 (memo 3 was never requested). Memo 1's chain holds the
facilitator's injected relayed rework (5 runs). The run figures come from a throwaway ledger that reads the kept files and the published counts and
imports no product code (commit 1's, extended to E6), under `b252d77c`'s rules; the structural facts (cases, deliveries, verdicts, links, signers)
are read from the message files, the FAIL counts from the recorded `final-services-progress-status-health.txt` of each stream. Short ids below are
the suffixes of full ids: `...-root-7dcd` is `20261024T153617209573-root-7dcd`.

**What a replay of these files cannot show (kit limit).** Kit limit: the replay has no org git history, so OQ-2's given-delivery path and P3's
`relayed` finding cannot run; with history the evidence shows s2 relayed (no hand edit) and s1 and s3 equal to the team's current files (the md5 facts
of E6S1-6, E6S2-6 and E6S3-6). The kit materializes no git repository, so P3 does not know the checked artifact of a past delivery and compares each
file with the team's current one (4.3, "no org history"). Two consequences, stated once for the three streams: no `relayed` finding (0a.3, F-E5-5)
arises, so the given delivery of every case is its latest delivery (OQ-2's "else"), and in s2 memo 1's file is `not as delivered` against the
injected relayed rework 4ccc and its case reads `without a verdict (relayed only)`; in s1 and s3 the replay and the history agree (memo 1's file is
the current one). The facts that an org history would show for s2 are pre-registered below as **evidence facts** and asserted on the kept files
(md5 against `memos/versions/INDEX.txt`), not on the product; the two paths the replays cannot take are run on a real git history by
`tests/e2e/test_org_growth_0b_given.py`.

**The user's approved runs** (OQ-1, 0a.5 A2): the rule is `max(budget, ceiling)`, with the ceiling at each hand-down of the user's requests = the
runs those requests had used + what the team still held + the hand-down's budget, and the default's 1-run rework with nothing left no approval
(`Case.unapproved_reworks`). s1: at the human rework `...-f06d` the user's requests had used 9 runs and held none (7 had come back), 9 + 7 = 16, the
budget; at `...-b5b1` they had used 14 and held none, so 14 + 5 = 19; memos 2 and 3 stay at the budget 16 (5 + 5 and 7 + 5 are below it). s2: at
`...-99f6` they had used 5, 5 + 5 = 10, below the budget 12; at `...-4ecb` they had used 10 and held none, so 10 + 5 = 15; memo 2 stays at 12. s3: the
human rework `...-bc02` is the default's 1 run with nothing left (the first request handed 16, used 5, and its blocked first result left 11 held: A2
marks it, so it approves nothing); `...-9a5b` had 5 left and used 11 before it; the grant `...-1362` (root's note, 4 runs, after the user's yes) came
with 11 used, 1 held and bc02's run out (11 + 4 = 15), so the approval stays at the budget 16. These are the product's approvals (19, 15 and 16 for
memo 1); they replace e6-gate section 4 item 2's 19, 15 and 22, which were computed under `18c4ffb` (0a.4's B-1 moved s3 to 17 and 0a.5's A2 to
16, 0a.5 section 18 item 1). Lena's own D14 approvals were 17, 15 and 20 (e6-gate 1.4): the alarm reads the product's, so it cannot see s1's 19 runs
against her 17 (F-E6-5) and reads s3's 16 of 16 where she approved 20. Both are findings under the declared limit of 26 (the approved runs are
root's hand-downs, e7-gate 5 item 12), not expectations. In s3 the assistant's "the 16-run cap becomes 20" was its own wording: the product's ceiling
stays 16, because the relayed result had returned the user's runs before the grant. Finding F-E6-6 (not an expectation): s3's accepts `...-root-2b9e`
and `...-root-24bb` were recorded a turn before Lena saw the versions; 4.3 counts them (judged 3 of 6), and 0a.4 fixed the cause for new data.

**E6 s1** (`E6-s1`; cases `...-root-7dcd`, `...-root-cbc2`, `...-root-285b`)
- E6S1-1: the record `weekly-memo` (lead; client root, human; contract v2, playbook v2, budget 16); 3 cases, done 3, none cut; no one-off record and no
  nested service; 8 deliveries: 7dcd by `...-lead-6c73`, its human rework `...-root-f06d` by `...-lead-d80f`, the relayed rework `...-root-3a54` by
  `...-lead-3f72`, the human rework `...-root-b5b1` (sent with `base="delivered"`, its body carries `## Base: the version the client judged`) by
  `...-lead-9260`, cbc2 by `...-lead-64ff`, its human rework `...-root-b0fe` by `...-lead-8613`, 285b by `...-lead-b0f4`, its human rework `...-root-d675`
  by `...-lead-762f`; judged 3 of 8 (f06d: reject `...-root-07a0`; b5b1: accept `...-root-47b9`; b0fe: accept `...-root-def9`); first deliveries 0
  accepted, 0 rejected, 3 without a verdict (7dcd superseded by the human rework f06d, cbc2 by b0fe, 285b by d675), 0 never delivered; the delivery
  of 3a54 carries only the assistant's relayed reject `...-root-da70` and is superseded by the human rework b5b1; 1 case without a verdict, 285b (its
  latest delivery d675, memo 3's rework delivered in turn 12, was never judged: `relayed only` 0, `unseen relayed` none); memo 1 (case 7dcd) is
  judged, since its latest delivery b5b1 was accepted; 0 verdicts not on a delivery; 0 legacy verdicts. The line is `judged by the user: 3 of 8
  deliveries; without a verdict: 1 case(s) (20261024T161027082339-root-285b): never counted as accepted; not as delivered: 0`.
- E6S1-2: one escape, R1 = `...-root-07a0` (a human reject; its own `criterion` is `none`) on the delivery of f06d, case 7dcd, signed off by
  lead/reviewer (the latest done result of a direct report before the delivery is `...-lead.reviewer-8d28`): `contract-gap` by rule `answer` (the human
  link `...-root-c18e` names C8, which contract v1 of f06d lacks; the answering contract v2 removes nothing), `rules` `["answer", "words"]` (the user's
  words "Always start the memo" carry a lasting word), `detail` `["20261024T155254011781-root-c18e", "C8"]`, `also` none, `before_verdict`
  `...-root-3a54` (its done result `...-lead-3f72`, 15:49:59, lies between the delivery's, 15:45:18, and the verdict, 15:51:27), attribution `not its`.
  The escape line is `R1 case 20261024T153617209573-root-7dcd, signed off by lead/reviewer: contract-gap (the user's answer, link
  20261024T155254011781-root-c18e, names C8, which contract v1 of the task did not have); your relayed rework 20261024T154651259477-root-3a54
  delivered after it and before the verdict: the user may have judged that version`. Rule 2 cannot match (the relayed rework 3a54 was sent after the
  rejected task f06d; the human reworks after it, b5b1 here and 9a5b in s3, were accepted, so no escape reads the base clause: M-P4-1 n/a (0 of 0)).
  The verifier line is `lead/reviewer: escapes 0 of 3 judged; not its: 1 contract-gap; PASS precision 3 of 3; its FAILs before delivery: 1
  re-check(s), 1 author rework run(s)` (the recorded health line of the reviewer: re-checks after a FAIL 1, author rework runs 1); health for root
  `escapes 0 of 3 judged (+1 not its: 1 contract-gap)`, for an agent `escapes 0 of 3 judged`.
- E6S1-3: contract v1 `2026-10-24 15:36 contract v1 (C1, C2, C3, C4, C5, C6, C7)`; playbook v1 `15:36 playbook v1 (root): written by the client (no
  admission needed)`; contract v2 `15:52 contract v2 (root): adds C8: the user's answer to R1: C8 confirmed (link 20261024T155254011781-root-c18e)`
  (DR3-1; JSON `basis` `answers`, `answers` `R1`, `confirmed` `[{"id": "C8", "link": "20261024T155254011781-root-c18e"}]`, `not_confirmed` `[]`);
  playbook v2 `15:54 playbook v2 (lead): admitted (c) on C8, R1, 20261024T155254011781-root-c18e: 1 changed line(s): 1 the cited criteria's own words,
  0 beyond them` (the one line it adds is `- C8: ` and C8's text, `removed` 0); top-up marks at 15:42 (+7 human rework f06d), 15:46 (+6 your relayed
  rework 3a54, your own spend), 15:53 (+5 human rework b5b1), 16:05 (+5 human rework b0fe) and 16:14 (+5 human rework d675); no charter or model mark,
  and the unknown line.
- E6S1-4: 7dcd "Memo for 2026-10-05 weekly": the user's runs 19 of 19 approved (1.00x), top-ups `+7 human rework ...-f06d, +6 your relayed rework
  ...-3a54, +5 human rework ...-b5b1`, relayed runs 5, total 24 (`your relayed reworks: 5 run(s), your own spend; total 24`), 24 charged runs,
  `credited` 0; cbc2 "Memo for 2026-10-12 weekly": 10 of 16 (0.63x), `+5 human rework ...-b0fe`; 285b "Memo for 2026-10-19 weekly": 10 of 16 (0.63x), `+5
  human rework ...-d675`; none cut ("0 case(s) had their window cut").
- E6S1-5: two judged cases (7dcd and cbc2) are below the minimum of 3: repeat `n/a (2 of 3 judged cases)` and cost `n/a (2 of 3 judged cases)`
  (JSON repeat: `window` `[]`, `subjects` `{}`, `fired` `[]`, `not_counted` `{}`, because R1's own reading is `none`, which is no id; cost: `judged` 2,
  `compared` 3, `cases` `[]`, `skipped` `[]`).
- E6S1-6: evidence facts: the three delivered memos equal the team's current files: `memo-2026-10-05.md` (md5 `970196fc0da4bfe36f5f5c20beaadf17`) is
  `v5` (`59647dd`, 15:55:12Z), written by the human rework b5b1's "restore judged version, add Summary line" and the checked artifact of b5b1's
  delivery; `memo-2026-10-12.md` (`1b7541202526ab25ee3f8be9c6afa8ee`) is `v3` and `memo-2026-10-19.md` (`8d5ae0769dfedfdc2db2bbe7edcb8bf8`) is `v2`. On the
  replay: `not_as_delivered` `[]`, `neither` `[]`, `files_error` `""`, nothing voided, and the judged line ends `not as delivered: 0` with no
  no-history remark.
- E6S1-7: moved past: none (the writer's blocked `...-lead-dfec` is released by `...-lead-b986` and its blocked `...-lead-a7f6` by `...-lead-340c`,
  each of which revises its predecessor); the recorded `status` shows budget 0 for every agent.

**E6 s2** (`E6-s2`; cases `...-root-1d33`, `...-root-0aff`)
- E6S2-1: contract v2, playbook v2, budget 12; 2 cases, done 2, none cut; 6 deliveries: 1d33 by `...-lead-12d1`, its human reworks `...-root-99f6` by
  `...-lead-831f` and `...-root-4ecb` by `...-lead-b322`, the relayed rework `...-root-4ccc` by `...-lead-3e7e`, 0aff by `...-lead-2e4f`, its human
  rework `...-root-40f3` by `...-lead-5ff1`; judged 1 of 6 (4ecb: reject `...-root-7682`, then the accept `...-root-6271`, Lena's "I'll take it as it is"
  recorded as her accept, on the same delivery: both are counted and the delivery stays an escape); first deliveries 0 accepted, 0 rejected, 2
  without a verdict (1d33 superseded by the human rework 99f6, 0aff by the human rework 40f3), 0 never delivered; 2 cases without a verdict: 1d33
  (its latest delivery 4ccc carries only the relayed reject `...-root-217c`: `relayed only` 1) and 0aff (its latest delivery 40f3, memo 2's rework
  delivered in turn 12, was never judged); 0 verdicts not on a delivery; 0 legacy verdicts. The line is `judged by the user: 1 of 6 deliveries;
  without a verdict: 2 case(s) (20261024T163213630553-root-1d33, 20261024T165226023852-root-0aff): never counted as accepted (1 with only your own
  relayed verdict); not as delivered: 1 ...`.
- E6S2-2: one escape, R1 = `...-root-7682` (a human reject, own `criterion` C3) on the delivery of 4ecb, case 1d33, signed off by lead/reviewer (the
  latest done result of a direct report before the delivery is `...-lead.reviewer-1637`): `contract-gap`, rule `answer` (the human link `...-root-8211`
  names C11, which contract v1 of 4ecb, with C1 to C10, lacks), `rules` `["answer", "words"]`, `detail` `["20261024T165100357598-root-8211", "C11"]`,
  `also` none, `before_verdict` `...-root-4ccc` (its done result `...-lead-3e7e`, 16:48:27, lies between the delivery's, 16:45:05, and the verdict,
  16:50:03), attribution `not its`; the decisive verdict is the reject 7682, not the later accept; rule 2 cannot match. The verifier line is
  `lead/reviewer: escapes 0 of 1 judged; not its: 1 contract-gap; PASS precision 1 of 1; its FAILs before delivery: 0 re-check(s), 0 author rework
  run(s)` (recorded health line: re-checks after a FAIL 0, author rework runs 0); health for root `escapes 0 of 1 judged (+1 not its: 1
  contract-gap)`, for an agent `escapes 0 of 1 judged`.
- E6S2-3: contract v1 `2026-10-24 16:31 contract v1 (C1, C2, C3, C4, C5, C6, C7, C8, C9, C10)`; playbook v1 `16:31 playbook v1 (root): written by the client
  (no admission needed)`; contract v2 `16:51 contract v2 (root): adds C11: the user's answer to R1: C11 confirmed (link 20261024T165100357598-root-8211)`;
  playbook v2 `16:52 playbook v2 (lead): admitted (c) on C11, R1, 20261024T165100357598-root-8211: 1 changed line(s): 1 the cited criteria's own words,
  0 beyond them`; top-up marks at 16:38 (+5 human rework 99f6), 16:42 (+5 human rework 4ecb), 16:46 (+6 your relayed rework 4ccc) and 16:56 (+5 human
  rework 40f3); no charter or model mark.
- E6S2-4: 1d33 "Memo for 2026-10-05 weekly": the user's runs 15 of 15 approved (1.00x), top-ups `+5 human rework ...-99f6, +5 human rework ...-4ecb, +6
  your relayed rework ...-4ccc`, relayed runs 5, total 20 (`your relayed reworks: 5 run(s), your own spend; total 20`); 0aff "Memo for 2026-10-12
  weekly": 10 of 12 (0.83x), `+5 human rework ...-40f3`; `credited` 0.
- E6S2-5: repeat `n/a (1 of 3 judged cases); not counted: R1's reading C3 (not confirmed)` (`window` `[]`, `subjects` `{}`, `not_counted` `{"R1":
  ["C3"]}`: R1's own reading C3, and the human link names C11); cost `n/a (1 of 3 judged cases)` (`compared` 2, `skipped` `[]`).
- E6S2-6: evidence facts: the delivered `memo-2026-10-05.md` (`fa17fa9470b5bafb1ebb9bf7fad3ad94`) is `v3` (`218f4c7`, 16:43:36Z), the checked artifact of
  4ecb's delivery (the result `...-lead-b322` lists the file modified at 16:43:27Z); the current file is `v4` (`b38c26b`,
  `3f7789f5261e97783cd71134a664c251`, 16:47:14Z), written by the relayed rework 4ccc; `memo-2026-10-12.md` (`fd27870dd5d248aa33d528a013459658`) equals
  the current file `v2`. On the replay: `not_as_delivered` `[{"case": 1d33, "task": 4ccc}]` (the newest delivery that lists the file is 4ccc, a relayed
  rework, and the walk ends at the human rework 4ecb), nothing voided (4ccc has no human verdict), `neither` `[]`. With history this would be a
  `relayed` finding that names 4ecb as the delivery Lena was given.
- E6S2-7: moved past: one agent, `lead/writer` (`status`: `budget=2`, so it holds 2 runs): its blocked task `...-lead-ff9d` (memo 2; blocked result
  `...-lead.writer-2ce5`, 16:53:36) is not released (`...-lead-f667`, the next task to the writer, does not revise it) and the lead has sent the writer 1
  task since: `task 20261024T165305744776-lead-ff9d from lead, blocked 2026-10-24 16:53: left blocked: lead has sent lead/writer 1 task(s) since`.
  This is 4.5's positive path on E6's files (the first outside E4).

**E6 s3** (`E6-s3`; cases `...-root-4a3e`, `...-root-833b`, `...-root-430a`)
- E6S3-1: contract v2, playbook v2, budget 16; 3 cases, done 3, none cut; 6 deliveries: 4a3e by `...-lead-74fa` (its first result `...-lead-11cc` is
  `blocked`; the later result 74fa, two seconds after the rework's, is `done`, and the latest result decides), its human rework `...-root-bc02` by
  `...-lead-009a`, the relayed rework `...-root-5d4a` by `...-lead-406b`, the human rework `...-root-9a5b` (sent with `base="delivered"`) by
  `...-lead-6c63`, 833b by `...-lead-faf4`, 430a by `...-lead-5f06`; judged 3 of 6 (bc02: reject `...-root-dd70`; 9a5b: accept `...-root-2b9e`; 833b: accept
  `...-root-24bb`; both accepts were recorded the turn before Lena saw the version, F-E6-6, and 4.3 counts them); first deliveries 1 accepted (833b:
  "Keep it as it is. Lee's swap is an action item, so the table is enough."), 0 rejected, 2 without a verdict (4a3e superseded by the relayed rework
  5d4a, the first task sent after its late result 74fa, and 430a, not superseded), 0 never delivered; 1 case without a verdict, 430a (memo 3 was
  written and reviewed but never copied to Lena: `relayed only` 0); memo 1 (case 4a3e) is judged, since its latest delivery 9a5b was accepted; 0
  verdicts not on a delivery; 0 legacy verdicts. The line is `judged by the user: 3 of 6 deliveries; without a verdict: 1 case(s)
  (20261024T173452118977-root-430a): never counted as accepted; not as delivered: 0`.
- E6S3-2: one escape, R1 = `...-root-dd70` (a human reject, own `criterion` `none`) on the delivery of bc02, case 4a3e, signed off by lead/reviewer
  (the latest done result of a direct report answering a task sent after bc02 is `...-lead.reviewer-7313`, 17:16:36; the reviewer's later result
  `...-lead.reviewer-915f` answers a task sent before bc02): `contract-gap`, rule `answer` (the human link `...-root-1dcf` names C9, which contract v1
  of bc02, with C1 to C8, lacks), `rules` `["answer", "words"]`, `detail` `["20261024T172448264286-root-1dcf", "C9"]`, `also` none, `before_verdict`
  `...-root-5d4a` (its done result `...-lead-406b`, 17:22:16, lies between the delivery's, 17:17:05, and the verdict, 17:23:44), attribution `not
  its`. The verifier line is `lead/reviewer: escapes 0 of 3 judged; not its: 1 contract-gap; PASS precision 3 of 3; its FAILs before delivery: 0
  re-check(s), 0 author rework run(s)` (recorded health line: 0 and 0); health for root `escapes 0 of 3 judged (+1 not its: 1 contract-gap)`, for an
  agent `escapes 0 of 3 judged`.
- E6S3-3: contract v1 `2026-10-24 17:09 contract v1 (C1, C2, C3, C4, C5, C6, C7, C8)`; playbook v1 `17:09 playbook v1 (root): written by the client (no
  admission needed)`; contract v2 `17:24 contract v2 (root): adds C9: the user's answer to R1: C9 confirmed (link 20261024T172448264286-root-1dcf)`;
  playbook v2 `17:26 playbook v2 (lead): admitted (c) on C9, R1, 20261024T172448264286-root-1dcf: 1 changed line(s): 1 the cited criteria's own words,
  0 beyond them`; top-up marks at 17:14 (+1 human rework bc02), 17:19 (+6 your relayed rework 5d4a, your own spend), 17:24 (+1 human rework 9a5b) and
  17:25 (+4 your grant `...-root-1362`); no charter or model mark.
- E6S3-4: 4a3e "Memo for the meeting of 2026-10-05": the user's runs 16 of 16 approved (1.00x), top-ups `+1 human rework ...-bc02, +6 your relayed rework
  ...-5d4a, +1 human rework ...-9a5b, +4 your grant ...-1362`, relayed runs 5, total 21 (`your relayed reworks: 5 run(s), your own spend; total 21`);
  the 21 charged runs include the lead run that was killed with its scheduler (`lead/20261024T171716483127.log`, no `[run finished]`: a lost run is
  charged, D-E5-3) and `credited` is 0; 833b "Memo for the meeting of 2026-10-12": 5 of 16 (0.31x), top-ups none; 430a "Memo for the meeting of
  2026-10-19": 5 of 16 (0.31x), top-ups none.
- E6S3-5: repeat `n/a (2 of 3 judged cases)` (no `not counted` part: R1's own reading is `none`) and cost `n/a (2 of 3 judged cases)` (`compared` 3,
  `skipped` `[]`).
- E6S3-6: evidence facts: the delivered `memo-2026-10-05.md` (`2a906d23378ab5101c30f04ee3868d72`) is `v4` (`eb809c2`, 17:27:01Z), the current file and the
  checked artifact of 9a5b's delivery; `memo-2026-10-12.md` (`daad1ccd09bd49dc51da829ed0c7a205`) equals the current file `v1`; memo 3 was not copied. On the
  replay: `not_as_delivered` `[]`, `neither` `[]`, nothing voided, `files_error` `""`, and no no-history remark.
- E6S3-7: moved past: one agent, `lead/writer` (`status`: `budget=4`, so it holds 4 runs): its blocked task `...-lead-ece1` (memo 2; blocked result
  `...-lead.writer-8726`, 17:31:04) is not released (`...-lead-cf2b`, the next task to the writer, does not revise it) and the lead has sent the writer 1
  task since: `task 20261024T173027536738-lead-ece1 from lead, blocked 2026-10-24 17:31: left blocked: lead has sent lead/writer 1 task(s) since`.

**E6 (all three)**
- E6-all: no charter or model mark and `history` `{known: false, truncated: false, skipped: 0}` (the unknown line, once); `credited` 0 in all eight cases; no
  one-off record and no nested service; every `quality_data` conforms to 9.4 (`test_every_corpus_conforms_to_the_schema` covers the three manifests).

### 19.4 The cost comparison on corpora without run logs (`TESTS/e2e/test_org_growth_0b_costs.py`)

E, E2 and A5 kept no run log, so their runs are checked with `over_cost(case, approved, ratio)`, the per-case predicate `cost_alarm` applies,
over `Case` values that carry the published run counts (their docstrings cite the source lines) as the user's runs (none of their reworks is
relayed: their tier was never recorded, so every task of the chain is the user's) and, as `approved`, `user_approved(case, budget)` of the case
that `CaseHistory.chains(runs=False)` builds from the kept messages. The alarm's state on the files themselves is the one 19.3 states (E: `n/a
(1 of 3 judged cases)` with b495 skipped, E2: `n/a (0 of 0 cases compared)` with its three cases skipped, A5: `n/a (0 of 3 judged cases)` with
f768 skipped).

**Assumption, stated once for the three rows.** With no run log, the runs before each hand-down are read as 0 (`runs=False`), so `user_ceiling`
is the hand-downs less what came back, never more: `user_approved` is a lower bound, and an overrun is read as more likely, never less. The
rows below are therefore the strictest reading these files allow, and still none is over.
- E (`STUDY.md` focus item (c): "R1 8 of 12; R2 17 (12 + 5 rework + 3 + 1 granted = 21 handed out); R3 10 of 12"; contract budget 12): R1 8 of
  12 (0.67x), R2 17 of 17 (1.00x), R3 (blocked, 10 used, 2 still out) 12 of 12 (1.00x): none over (before D-E5-6 R2 read 17 > 15, 1.42x).
- E2 (`evidence/run-counts.txt`: "R1 first pass 9, rework1 5, rework2 5 = 19; R2 5; R3 first pass 6, rework 5 = 11"; contract budget 15): R1 19
  of 20 (0.95x), R2 5 of 15 (0.33x), R3 11 of 15 (0.73x): none over (before: R1 19 > 18.75, 1.27x).
- A5 (`evidence/run-counts.txt`: lead 13, researcher 1, writer 4, factcheck 4 = 22; the head task's budget 22): 22 of 26 (0.85x): not over
  (before: 1.00x).
No replay of the files fires the alarm, so 19.3 E3-9 adds the constructed variant.

### 19.5 E5, E6 and E7, by amendment (plan items FEAT-010, FEAT-012, FEAT-013)

E5's evidence is committed at `3cd28b3` (`studies/E5-org-growth-0a2-recheck/evidence/`, streams `s1`-`s3`), E6's at `fe0c9fd` and E7's at
`3a0bf49`. Their gates exist (`RESEARCH/phase-0a2/e5-gate.md`, `RESEARCH/phase-0a3/e6-gate.md`, `RESEARCH/phase-0a4/e7-gate.md`; all FAIL, which
does not stop these replays: they read the files, not the verdict). Each study's streams join the replays by the same rule: the planner adds the
manifests to the kit (19.1) and, **before any replay test of that study is written**, an amendment to this section pre-registers its
expectations from its gate document and its committed evidence, never from the product's output, with the manager's approval (at least: every
`answers` amendment marked confirmed with its link, or `not confirmed (the link was not recorded)`, with DR3-1's form; the base sections' effect
on the carry-over rule; the P3 notes against the not-as-delivered counts and the `relayed` findings; the `run credit <addr>@<stem>` notes
against the credited counts; the user's runs and approved runs of each case, computed under `b252d77c`'s rules, 0a.5 A2 included). For E7,
at least the e7-gate section 5 items 4-10 per stream, each R1's cause (rule 4, with s1's removed C2), the contract marks (C9 with C2 removed,
C8, C9), s2's `relayed only` and s3's blocked memo 1 (OQ-2 and D4), the heads' first deliveries (e7-gate 5 item 7), `credited` 0, and s2's
writer (OQ-4). A failed pre-registered expectation stops the FEAT (19.3).

E5's and E6's expectations are the lists `E5` and `E6` in 19.3 (plan commits 45 and 50); E7's follow by the same rule.

## 20. The noise study (study G0): protocol and harness

### 20.1 Purpose, place in the sequence, and design

G0 measures how much the same input varies across repeated runs, so later studies can tell a change from noise (go/no-go item 7; the gate's
item 7). It repeats E7's committed script (Lena's lines, the three memos, the facilitator's injected relayed rework of memo 1, the answer
key), because that is the newest validated script for the product G0 measures (0a.3 + 0a.4 + 0a.5 + 0b), and E7's results are then the first
point inside or outside the band. It has no pass rule: it reports values and their spread.

- **Sequence** (D-E5-7, D-E6-8, D-E7-1, D-E7-7). (1) 0a.3, 0a.4 and 0a.5 are merged; (2) 0b is built on them and passes its code review and its
  fail-closed final validation on the current `main`; (3) `e7-gate.md` section 3 answers YES to "may 0b merge?" (it does); (4) 0b merges to
  `main`, and no re-check study runs before the merge; (5) with the owner's OK on its cost (OQ-6, 20.6), the manager starts G0 as a study
  workflow on the merged `main` sha (G0 needs `quality --json`); (6) G0's report closes Phase 0b (the exit criterion's "noise baseline
  measured"; the replays of section 19 are its other half). The build never starts G0.
- **Script pin** (OQ-5, moved to E7 by e7-gate section 5 item 11). G0 pins E7's committed `evidence/protocol.md` (2 609 lines, md5
  `0acc2b4191b8cbfa5f4bb6197b877de1`, as its `protocol.md5` records) and copies E7's turn files, injection and answer key with their md5s.
  E7's script has the 15-turn cap (D-E6-6), so a stream has up to 15 user turns. G0's protocol must also state: whether a version shown with
  its text and a "not delivered yet" statement is a delivery (D8: E7's injection moment and D-E6-8's condition 4 rest on that reading); how
  D-OFFER counts a product line (the PLAN FOR YOU block's budget question, 0a.5 B, is a product text, which D-OFFER reads as no offer by the
  assistant); and that its T-PLAN and T-WARN pins include that line.
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
- **Repeats**: k = 3 valid streams per arm, so 6 streams (Q3, decided by the manager; the owner may raise it). k = 3 is the gate's floor and
  gives a range, not a rate (the gate's item 7). The harness can add streams to an arm afterwards (`run_arm.sh <arm> <k>` starts at the
  arm's next stream number), so thin skill strata can be filled later by the owner's decision.
  Every cell of arm x skill stratum with fewer than 3 streams reports its values and `n/a (k of 3)` for its spread.
- **Validity**: E4's H8 rule and 0a.2's throttle rule (a credited run is not charged and is retried once) as in E5; an invalid stream is
  replaced once per arm with the manager's approval, recorded before it starts.

### 20.2 What the product provides, what the harness provides

| Need | Product (0b and before) | Study harness (`ST/G0-noise-baseline/evidence/harness/`) |
|---|---|---|
| the org, tools, scheduler, run logs with prompts (`# ---- prompt ----`), events | yes | - |
| per-stream counts: cases, deliveries, verdicts, escapes and causes, without a verdict, files not as delivered, moved-past blocks, relayed and credited runs, alarms, timeline | `hirearchy quality --json` at the end of each stream (and after each turn, for the turn table) | records it; re-derives the same counts from the raw files independently and reports every mismatch as a product defect |
| deliverable notes, `progress` flags, refusals | yes (0a.2) | counts them from turn files |
| repeats, arms, HOME preparation, skill md5 checks, model and effort checks, Lena's turn driver, injection | - | `run_arm.sh <arm> <k>` over E7's `run_turn.sh`, `inject_root_rework.py` (with F-E4-9's fixed polling loop), `model_check.sh`, `ambient_context.py`, `skill_check.sh`; it keeps the `; sleep 20` boundary (the amendment to D-E6-3; README's declared limit), without which a scheduler alive at a turn's end dies with the call, and the per-turn ambient snapshots (D-E6-7) |
| assistant-layer measures | - | `extract_mechanical.py` (E5's, with A3 patterns) extended for 20.4 B |
| answer-key scoring, reviewer ambiguity recall, prompt growth | - | `score_memos.py`, `ambiguity_recall.py`, `prompt_sizes.py` |
| the baseline table | - | `aggregate.py` -> `baseline.md` |

The harness is study code, built by the study's setup step from E7's harness (`studies/E7-org-growth-0a4-recheck/evidence/harness/`, its
17-line `MD5SUMS` has md5 `d1f24687c9cd1587466d24db42ce59d0`; copied with md5s recorded), not product code. Before the first stream it must
re-derive E7's published counts from E7's raw evidence (a self-check); a mismatch stops the study.

### 20.3 Procedure per stream

Setup as E5 (sandbox, workspace skill copy with md5, settings md5, safety snapshot before), the arm's HOME (20.1's skill rule), then E5's
turns verbatim, the injection as E5's protocol places it, `quality --json` after each turn and at the end, the copy of the org evidence,
safety snapshot after. The streams of the two arms are interleaved (M0, M1, M0, ...) so that time-of-day and service load do not line up with
an arm.

### 20.4 Measures (per stream; then per arm and per skill stratum: every value, min, median, max; binary ones as `k of n`)

A. **Team layer**: per delivered memo version the answer-key score (decisions n/8, action items n/15, wrong dates, extra rows, Summary
   first); reviewer verdicts (PASS/FAIL, `criteria met n of m`); **reviewer ambiguity recall** (D-E4-5; E5 protocol's D21 copied verbatim:
   k = reviewed versions x ambiguity items the reviewer listed as `ambiguous` on its first review of that version, n = reviewed versions x the
   items they contain), `k of n` per stream and pooled, `n/a (0 of 0)` when none was reviewed (an ambiguity item is contained in a version only as a table row: E5 STUDY,
   Interpretation 6, so G0's verbatim copy of D21 carries that reading), plus per item and version whether the lead
   forwarded it, whether `progress` flagged it and whether the writer left it out of the next version; runs per case; `revise_playbook`
   attempts, refusals and admissions; **owner prompt growth**: the lead's prompt bytes per run (first, max, last, and last minus first) and
   the words of each Reflect section (max), with E3's 20.2 KB -> 29.9 KB and 452-679 words as the reference.
B. **Assistant layer**: skill activation (stratum); per human reject, exactly one yes/no item naming an id before any `define_service`; every
   flagged item asked before delivery (D-E4-5's restated clause 3); relayed reworks sent and how many the user asked for; files not as delivered and
   whether a human-tier verdict followed; verdict recording (delivered versions the user saw against verdicts recorded); results read with
   `inbox` against shell reads, and root's unread count at the end; P2 and P4 refusals met; whether the assistant offers a budget number at
   plan time (a product text is no offer: 20.1); spend requests per memo and the turns they take; copies made while "ask first" showed;
   L-ASIS-type verdicts recorded; schedulers still running at a turn's end, with every `scheduler.signal` and what followed (D-SIGNAL, M-C-8; an
   unexplained `scheduler.signal` is the manager's trigger to reopen M2).
C. **Product layer**: every count of `quality --json`, and the harness's re-derivation; the alarms that fired, each checked against the raw
   files.

### 20.5 Output and use

`baseline.md`: one table per layer, rows = measures, columns = streams grouped by arm and stratum, then min/median/max (or `k of n`); a zero
denominator is `n/a (0 of 0)`. A later study on the same script reads a value inside the band as indistinguishable from noise at this k; no
test of significance is made.

### 20.6 Cost

E7 measured 41, 34 and 40 org runs and 63.46, 51.40 and 62.60 credits for its three streams, with up to 15 user turns each, so 6 streams (k = 3
per arm, Q3) are about 230 org runs plus the assistant sessions, about 355 credits. The owner approved this on 2026-10-25 ("I agree with both
decision.": D-E7-6); the approval covers that cost, and the manager asks again if G0's design needs materially more. G0 does not start without
the owner's yes, and never as part of the build.

## 21. What the 0b study must check (pre-registration input)

- **Deterministic part**: at the study's commit, `TESTS/e2e/test_org_growth_0b_replays.py` and `test_org_growth_0b_costs.py` pass, every
  expectation of 19.3 and 19.4 included (E3-7's firing variant too); the output is kept verbatim.
- **Model set and effort**: every seat claude-sonnet-5.5 at effort high, checked per run log and for the assistant; a seat outside the set
  invalidates the stream (20.1).
- **Runtime**: V3 everywhere; A3 patterns; every org run's `# cwd:` and model lines checked.
- **Arms and strata**: k = 3 valid streams per memory arm (Q3); the skill md5 rule of 20.1 in both arms; skill activation recorded per stream
  before any score is read; cells under 3 streams reported as such.
- **The view is right on live files**: for every stream, every count of `quality --json` equals the harness's re-derivation from the raw files;
  each mismatch is listed with the files that show it.
- **Verdict timing live**: every verdict the view counts follows its delivery's `done` result; every verdict on a blocked or failed result is
  in `not_on_a_delivery`; checked by hand on the raw files.
- **Alarms live**: every alarm that fired is listed with its cases and checked by hand against the raw files; every repeat subject is a
  human-tier link or a human rejection (no relayed reading among them); every cost alarm's user's runs equal the case's charged runs outside the
  relayed intervals plus the user's runs still out, and its approved runs equal the harness's re-derivation from the hand-downs.
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
| plan blocks | 2 plan files (`propose_raw_template_analysis_service.txt`, `propose_filled_template_analysis_service.txt`) and `second_half.json` (2 entries); 0a.3 and 0a.5 already regenerated the others (plan section 4 re-checks the list after the rebase) | 11.1 |
| health, root's text | 0: no golden scenario has a judged delivery, and the escapes segment shows only when `judged > 0` | section 10 (the `not its` split) |
| health, agents' text and review notes | 0 (same reason); the wording is unchanged | section 10 (the numbers) |
| health JSON | every health JSON golden gains `not_its` and `causes_unknown` | `to_dict` |
| dashdata / dashboard | 0 expected (the dashboard shows flags, which keep their wording); any dashdata snapshot that embeds `AgentHealth` JSON changes (checked by the planner) | `to_dict` |
| replays | new goldens in `tests/golden/expected/quality/` for 9.3's samples (E3 full, A5's one-off block, the empty org, the empty service) and E3's `--json` (`e3.json`) | 19.3 E3-5, E3-8, A5-4; 17 item 1 |
| prompts, ORG.md, charters | 0 | agents' prompts are unchanged |
Total (measured, plan PC-8): 15 files regenerated (18 file changes) plus 7 new, counted before any change 0a.3 to 0a.5 made to the same files. Each diff is reviewed and counted in the phase report (08 D1). As built: 17 files regenerated (20 file changes) and 8 new: the plan's 15, 18 and 7, plus `cli/tests/expected/no_command.txt` and
`unknown_command.txt` (regenerated) and `cli/tests/expected/quality.txt` (new), which the new command made necessary (A.5.2).

## 23. Plan items for the planner, and the backlog

Plan items (in this order of FEATs; each FEAT ends with its SCOPED run; 55 commits in 13 FEATs, the plan's numbering; A.5.1 lists what was built, with shas):
1. **FEAT-001 integration** (step 0 without a commit, commits 1-4): the rebase onto `main`, this amendment, and the byte-identical moves that
   make shared rules public: the base-heading constants, `services.criterion_words`, and `contract_of`, `amendment_ids` and `version_in_force`
   in `services.api` (A.4 PC-1).
2. **FEAT-002 runs and cases** (5-9): `RunCounter.stamps` is 0a.3's; the new `Case` fields (`credited`, `top_ups`, `cut`, `runs_unknown` and
   its three reasons), `CaseHistory.chains` and `CaseHistory.one_off_cases` with `DerivedCaseHistory`'s 7th collaborator `CharterReader`.
3. **FEAT-003 deliveries, causes, thresholds** (10-12): `Delivery`, `deliveries_of`, `signer_of` (moved from health with its tests),
   `not_on_a_delivery`, `unjudged_cases` with the given delivery, `cause_of` with `lasting`, `answer_removes` and the `carried=None` fallback,
   `attribution`, `quality_thresholds`.
4. **FEAT-004 history, marks, records, alarms** (13-19): `OrgHistory.changes` + `GitClient.log`, `BarHistory` + `GitBarHistory` (versions that
   do not parse are skipped), `ContractVersions`, contract and playbook marks, `DeliverableChecks(settled=...)` and `written`, `CaseRecords` +
   `DerivedCaseRecords` (one P3 call, per-record `error`, 12.1's read rule, `deliveries()` with its fallback), `repeat_alarm`, `cost_alarm`
   (exact `Fraction` comparison of `user_cost` with `user_approved`; `n/a (0 of 0 cases compared)`), `shown_name` in `__all__`.
5. **FEAT-005 one-off verdicts** (20-23): the `feedback` branch, refusals, `feedback_step` (no leading newline), docstrings and help, the skill's
   step 5.6 (re-planned on `b252d77c`'s SKILL.md, keeping 0a.4's lines 72, 92 and 100 and 0a.5's line 39 word for word).
6. **FEAT-006 the view** (24-32): `QualityReport`, `held_tasks`, `left_blocked`, the renderer (every variant of 9.2, the JSON of 9.4, the empty
   samples of 9.3 as goldens), `FailCounts` + `HealthFailCounts`, `ReadableOrgConfig`, `QualityTools`, `QualityCommand`, the ROOT_INSTRUCTIONS
   line, README section "Quality (phase 0b)" within the README line caps.
7. **FEAT-007 health rebase** (33-36): section 10 (the port, the 5th collaborator, `render_text(causes=...)`, root-only split).
8. **FEAT-008 ride-alongs** (37-39): 11.5 (the flaky golden screen test: find the nondeterminism, make the capture deterministic, no retry),
   11.1, the skill's step 5.1.
9. **FEAT-009 replays E, E2, A5, E3, E4** (40-44): the kit, its manifest, its meta tests, 19.3 (with E3-7's and E3-9's constructed variants
   and E3-8's JSON golden) and 19.4; a failed expectation stops the FEAT and goes to the manager (19.3, "When an expectation fails").
10. **FEAT-010 E5 replays** (45-47), **FEAT-012 E6 replays** (50-52) and **FEAT-013 E7 replays** (53-55): each study's manifests in the kit and
    an amendment to this design (the first commit of the FEAT, with the manager's approval) that pre-registers its expectations from its gate
    and committed evidence, before any replay test of that study (19.5, 27). FEAT-012 and FEAT-013 are no longer conditional (their evidence
    is committed).
11. **FEAT-011 docs** (48-49): ARCHITECTURE (2.2 row 31, section 3's Protocol lists for reflection, progress, snapshots, health's port, the entry
    points, and 3.22's collaborator sentence: `DerivedCaseHistory` takes seven collaborators, as do `DerivedCaseRecords` and
    `FolderDeliverableChecks`, and `OwnerPromptSections` eight; no class of the package takes more; as built, A.5.3 B11.1), README, and amendments to this design for anything the build changed.

Backlog (out of scope, with the reason):
- A one-off verdict settling P3 not-as-delivered notes and one-off client questions (8.5): consistent, but changes 0a.2 behaviour the row does not ask
  for.
- Semantic failure classes beyond `off_spec`, and showing `wasteful` (packs, Phase 3); `period` units, the `external` tier and `timing` (delayed
  oracles) (Phase 3, 4.6).
- A port through which a pack supplies its own lasting words to `cause_of` and its mapping onto `FAILURE_CLASSES` (for example a private
  `CauseVocabulary` of `DerivedCaseRecords`, wired in `app`): Phase 3 owns packs, and 0b adds no port it does not use, so today a pack's
  words would need an edit of the reflection core (DR2-8).
- A full git replay of E4's history (its log text cannot rebuild the repository).
- A replay kit that builds an org git history from the kept versions (`memos/versions/`, the result times), so that the replays of E5, E6 and E7
  can run OQ-2's given-delivery path and P3's `relayed` finding; not built in 0b, because the unit and integration tests run both on a real
  git history and G0 exercises the live path (19.3 E5, kit limit).
- Health reading files not as delivered (it runs per agent and in the review cycle; 10).
- Reading a retired team's run logs for a continued service's old cases (0a.2 section 22; 4.1 marks them instead).
- Refusal counts in the view (the retro brief, Phase 2; `observe` shows them now).
- An org-level criteria library from one-off verdicts (08 section 6: reopens after 0b shows recurring one-off shapes).

## 24. Deviations from 08, go/no-go and the gate (with reasons)

- **D1 (08 3.2; go/no-go item 4's caveat) A contract-gap rule by answer.** 08 types contract-gap by trigger words only, and go/no-go expected
  E3's reject 2 to type as `reviewer-miss`. 0b adds: the client's human-tier answer names a criterion the rejected task's contract lacked, or
  one the rejection's answering contract version removed (a "drop C6" answer). Reason: it is the client's recorded yes, stronger than a
  phrase; without it E3's reject 2 (C11), and E4's s1r/s2r/s3 first rejects, type as a reviewer miss or by an "always" that happens to be
  there, and a removal answer would count against the verifier although the client said the criterion should not be there.
- **D2 (08 3.2) A fixed order of the rules, with `also` and `rules`.** 08 gives the rules as a list. The order of 5.1 makes the type
  deterministic and keeps the gate's pre-registered s2r carry-over; the other matching rules stay visible as disputed causes.
- **D3 (08 3.2) "The reviewer PASSed" read from `done` and the task's contract version.** Parsing review reports would be domain- and
  template-specific; a `done` result asserts every criterion met (`FEEDBACK_HEADER`), so a confirmed link to a carried criterion is a sign-off
  the client contradicts.
- **D4 (08 3.3) Escapes are rejections of `done` deliveries only, recorded after the delivery.** A rejection of a blocked or failed result,
  or one given before the done result, is counted as a verdict not on a delivery: the team did not claim it was done when the user judged.
- **D5 (08 3.3) Stalled is the current state; no event horizon.** `progress`'s stalled state is used instead of stall events, so the 30-day
  horizon does not apply; refusals are not in the view (backlog).
- **D6 (go/no-go item 3; restated by D-E5-6) The user's runs for open and blocked cases.** Go/no-go says "runs used"; 0a.3's `user_cost` (the
  figure `case_total` prints, binding: one rule with `case_total`) adds the user's runs still out while a case is open or blocked, and leaves
  out the assistant's relayed runs, which are shown on their own line with the total (`case_spend`). For a finished case with no relayed
  rework the user's runs, the total and the runs used are equal.
- **D7 (go/no-go section 3, F-E3-10) Health excludes contract-gap and relayed causes, keeps untyped, and reads no deliverable folder.** Untyped
  escapes stay counted so unknown causes are not hidden; files not as delivered are left to the quality view because health runs per agent and in the
  review cycle (cost), so health also counts verdicts the view voids. Retired services' deliveries drop out of health (cases need a live
  contract). The `not its` split is shown to root only (I7), because 08 principle 6 has agents see facts, not targets.
- **D8 (08 3.2) One-off cases are root's tasks only.** 08's "one sender" is applied where a client verdict can exist; agents' delegations are
  not cases.
- **D9 (08 3.2) Failure classes: vocabulary now, one derived class.** Only `off_spec` (reviewer-miss) is derived and shown; the rest are `unclassed`,
  because a class assigned by the assistant would be relayed text. `wasteful` is the failure class of a case the cost alarm counts, by definition: 0b
  neither stores nor shows it as a field (the cost line and `cost.cases` carry no class, 9.4); Phase 3's packs map onto it; showing it is backlog.
  (Design correction, manager decision of 2026-10-25: the earlier text named `wasteful` as derived, but the approved 9.4 schema has nowhere to show it.)
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
  task not released as busy), not a per-task split.
- **D20 (the gate's item 4) A delivery whose file changed keeps a verdict given before the change.** (OQ-3: the file is labelled `not as
  delivered`, P3's words, because the files do not show who changed it; 0a.3's F-E5-5 `relayed` finding is no such change, 4.3.) The gate says a delivered file that differs from the
  team's artifact "counts as neither the team's pass nor its escape". 0b applies that to every verdict given at or after the file's last write,
  and keeps a verdict given before it, because that verdict judged the team's file: in s1r, R1 (18:59:00) judged the memo copied from the
  team's file at 18:46:13, and the file changed at 19:12:45. So s1r's R1 stays an escape (S1R-4). Only the file as it is now is known.
- **D21 (0a 3.1, kept) Legacy verdicts are read as the user's** (`verdict_tier`), and the view marks them as legacy; like every verdict, one
  counts only on the delivery it follows (D4).
- **D22 (the gate's item 2) The playbook diff is in `--json`, not in the text.** The gate asks to show a (c) admission "with its diff beside the
  cited criterion's text". Playbook lines are written by an agent, and I8 keeps agent-written text out of root's prompt, so the MCP and CLI
  text show counts against the cited criteria and the CLI's `--json` carries the changed lines beside the cited criteria's texts. Root can
  already read PLAYBOOK.md through its shell, so the JSON opens no new channel.
- **D23 (the gate's item 6) The writer's held tasks are the two the budget holds on.** The gate says the writer holds 4 runs "behind three
  `blocked` results". One of the three (`...-lead-0d54`) was revised by `...-lead-cc98`, so `mail.moved_past` released it and it holds no run;
  the view lists e679 (left blocked) and 808c (held, nothing sent since). The gate's total of 16 held runs is unchanged.
- **D24 (go/no-go item 6) The CLI's `feedback --source` keeps its default `human`.** Go/no-go item 6 says one-off verdicts carry the
  provenance rules, with `source` defaulting to `relayed`. 0b applies that default where the assistant writes (MCP root `feedback`, whose
  signature already says `source="relayed"`, and `Org.feedback`, stamped by `dispatch.provenance_source`) and keeps the CLI's existing
  `--source human` (`cli/_commands_services.py:143`). Reason: the terminal is the user's own seat, so a verdict typed there is the user's,
  and changing the default would change an existing command for service verdicts too, which row 0b does not ask for (8.1, I6).

## 25. User-visible changes beyond 08 row 0b (named)

Row 0b builds the quality view, one-off cases, the timeline and the noise study. These changes go beyond the row's words; each is either a
binding ride-along or required to build the row:
1. Root's `feedback` accepts one-off tasks (its docstring, its CLI help and a new refusal text for root): required by "cases for one-off tasks
   (root notes)". Its `source` defaults to `relayed` on MCP and `Org`; the CLI keeps its existing default `--source human` (D24).
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

- **The approved runs are root's hand-downs** (e7-gate 5 item 12; F-E6-5, F-E7-5, F-E7-9; D-E6-4 rejected the fix). The approved runs the view and
  the cost alarm compare with are 0a.3's `user_approved`, raised by root's hand-downs. An explicit budget root sets while runs are held, or a
  grant root sends without the user's yes, raises them, so a case can read "within" while the user's own approval is passed (E7 s1 memo 1:
  19 against Lena's 15). 0a.5 A2 closed the default's part: a 1-run default with nothing left no longer raises the approval. Where no run log
  is kept (E, E2, A5) the approved runs are a lower bound (19.4). A relayed rework still unanswered when the user's next request is sent
  leaves its later runs inside the user's interval; the user's runs then exclude at most `relayed_overlap` of them (E4 s1r `...-ed94`: 1).
- **"Without a verdict" never reads `reflection.rated`** (e7-gate 5 item 12; F-E7-4): `rated` counts any tier, and 0a.5 C changed only
  `open_client_items` and `questions_open` to the human tier.

- **Declared provenance.** `source="human"` and the recorded words are the assistant's declaration; the product cannot see the conversation.
  A one-off verdict has no contract to fall back on.
- **Files not as delivered** are known only for the file as it is now, for the newest delivery listing that file name, in a folder a service contract
  names (one-off deliverables elsewhere are not checked), within P3's bounds; a file edited, judged, then rewritten later keeps the verdict.
  Without git, P3 compares with the team's current files, so a rework in progress that changes the team's file in place makes the delivered
  copy show `differs` (0a.2 section 22), and the view then voids the user's verdicts given after the copy's last write; the no-history remark
  says which comparison was made.
- **The carry-over rule over-attributes.** Rule 2 types any rejected non-relayed rework as `relayed-carry-over` once a relayed rework in its
  chain touched an artifact both list, whatever the rejection is about; a one-file deliverable always shares its artifact. The escape then
  leaves health's count (D7). The shared-artifact test reads the team's own `## Artifacts` lists, so a team that lists a file it did not
  change moves blame onto the assistant. The rules that also matched stay in `also` (a `reviewer-miss` stays visible there), G0 re-types every
  carry-over by hand (21), and health does not count carry-overs against the verifier (Q2, decided by the manager: the reviewer is not blamed
  for the assistant's own reworks; untyped escapes stay counted).
- **Run attribution** is window-based (08 3.3): a case cut by a later request gives its later runs to that request; the view counts the cut
  cases. Relayed runs are counted by the relayed task's interval, so a relayed rework running in parallel with another task shares runs.
- **A case with no run log in its window** (4.1 reason 3): a done or failed case whose window is not cut always holds, live, the run that
  wrote its result; one without any is a corpus that kept no run log, or a run that started before the head task arrived (an agent that
  picked the task up during a run it was already in). Its runs are then not attributed to the case: the view marks it `runs not counted (no
  run log in its window)` and the cost alarm skips it, instead of showing 0 runs. The window's start is not moved.
- **A continued service's old cases** (0a.2 5.10) count no runs when their team was retired, because their logs stay in the retired tree; the
  view marks them `runs not counted (...)` by the charter's `created`, and the cost alarm skips them. A charter without `created` (or one that
  does not parse) gives no mark for that reason; such a case then reads `no run log in its window` when it is done or failed and uncut, and
  0 runs otherwise.
- **reviewer-miss** is inferred from `done` and the contract version, not from what the reviewer wrote; a team that reports `done` without a
  check is typed the same way.
- **The words rule** is English and lexical; "never" in "never mind" matches.
- **Cases** exist only for live services (and continued ones); a retired service's history leaves the view and health.
- **Charter and model marks** need git; a retired agent's charter is not followed; at most 40 commits and 5 s of git time per call; a version
  above 64 KiB, not UTF-8 or with a frontmatter that does not parse is not compared, and the change across it is not marked.
- **The noise study** at k = 3 gives a range, not a rate.
- **Agent-client services** never alarm; their counts are hypotheses.
- **Stalled** is a current state, not a history.
- **E, E2, A5** kept no run logs: their done, uncut cases read `runs not counted (no run log in its window)` and the others 0; their spends
  are not derivable from their files (19.4 checks them from published counts), and the held figure is not asserted on them.
- **A one-off verdict on a retired assignee's task** cannot be recorded (ONE-OFF-GONE); the view counts it as without a verdict.
- **Cost of a call**: `quality` runs the P3 checks once (one call: at most 40 git pairs and 5 s of git, about 11 s worst case with its
  subprocess bounds, 0a.2 DR-33/DR-43) and the bar history once (at most 5 s).

## 27. E5, E6 and E7: adoption by amendment, and the definitions most likely to move

The evidence of E5 (`3cd28b3`), E6 (`fe0c9fd`) and E7 (`3a0bf49`) is committed, and their gates exist (all FAIL; 0b may merge under D-E6-8, which
`e7-gate.md` section 3 answers YES). The three studies' findings that touch 0b are settled in A.3 (e5-gate 4 items 1-10, e6-gate 4, e7-gate 5
items 1-14) or are listed below, and each study's replays are pre-registered by an amendment to 19.5 before their tests. The definitions most
likely to move again, with what each study showed:
1. **The carry-over rule (5.1 rule 2)**: E5 is the first live data with P4's base sections; if a `base="delivered"` rework still carries a
   relayed change, the base clause moves.
2. **Reviewer-miss (rule 3)** and **contract-gap by answer (rule 4)**: E5's `answers` amendments and product links are their first live input,
   including any removal-only answer (`define_service(answers=..., remove_acceptance=...)`, whose product link names the removed ids: rule 4's
   `answer_removes`) and any mixed link (rule 3 before rule 4).
3. **Voiding by a file not as delivered (4.3, D20)**: E5 counts P3 notes and files not as delivered; their timing decides whether "edited before the verdict" is the right cut.
4. **Without a verdict and the verdict-after-the-result rule (4.3)**: P2-UNRATED makes root record verdicts; E5's counts of 0a.2 D4's friction,
   and any verdict recorded on a blocked result, may move the per-case reading.
5. **Credited and relayed runs (4.2)**: E5's throttle credits are the first live credits.
6. **Reviewer ambiguity recall (20.4 A)**: G0 copies D21 verbatim (with the table-row reading, 20.4 A); a change there changes G0.
7. **Moved past without a verdict and held tasks (4.5)**: P2's retire gate and continuations may change which blocks stay open.
8. **Continued services' run marks (4.1)**: E5 counts retire/define pairs; their cases test the `created` rule. A live done case with no run
   log in its window (reason 3) would show that a run started before its task arrived, and would move the window's start.
9. **The replays (19.5)**: E5's streams join them with expectations pre-registered by amendment.
10. **E7 adds** (e7-gate 5 item 14): the verdict-after-the-result rule (D4) for an accepted rework whose result is `blocked` (E7 s3 `...-d9bc`);
    first delivery and superseded for a head with a superseding `done` result seconds after its rework's (s1, s2); contract-gap by answer: the
    first live `answer_removes` (s1 removes C2 and adds C9); the user's approved runs (OQ-1): the default's run, a grant without a yes, an
    explicit budget while runs are held; held tasks (OQ-4): s2's writer; the tier, present on delegations without `revises` from `18a4531` on.
11. **E5 and E6 show** (e5-gate 4, e6-gate 4): no human rework followed an injection in E5, so the base clause of rule 2 has no live escape to read
    (E6 s1's `...-b5b1`, s3's `...-9a5b` and E7 s1's `...-066f`, s3's `...-d9bc` are human reworks with `base="delivered"` after a relayed rework; the
    E7 ones were not rejected: e7-gate 5 item 8); E5 s1 R1, s2 R1 and E6/E7's answered
    amendments are rule 4's live inputs; 0 throttles and 0 credits in E5-E7 (a lost run is charged: D-E5-3 defers its credit).

## 28. Owner questions: decided (manager, 2026-10-24; owner may override)

The manager decided the five questions of revision 2 on 2026-10-24 (`RESEARCH/phase-0b/manager-decision-design-loop.md`, that is
`/Volumes/workspace/hirearchy/docs/research/org-growth/phase-0b/manager-decision-design-loop.md`, where step 4 of the design run publishes
`.agents/tasks/`); the design is built to these decisions, and the owner may override any of them. Q4 is reversed by D-E5-6 (below); the
questions the E5 FAIL opened are in 28.1.

- **Q1. Ask after a one-off delivery? Decided (manager, 2026-10-24; owner may override): no extra question.** A one-off verdict is recorded
  only when the user gives one (8.1, the skill's step 5.6 in 8.4 and 11.3). Why: 08's D3 bounds client friction, and one-off cases are a 0b
  measurement, not a gate. Revisit if 0b's data (G0 or live use) shows one-off coverage too thin to use. The alternative was to ask "Keep it,
  or what should change?" after every one-off delivery, as for services, at one question per one-off task.
- **Q2. Which escapes health counts against a verifier? Decided (manager, 2026-10-24; owner may override): as designed.** Untyped escapes
  count against the verifier and stay visible; `relayed-carry-over` escapes do not, nor do `relayed-error` and `contract-gap` ones (D7,
  `reflection.attribution`). Why: the reviewer must not be blamed for the assistant's own reworks. Rule 2's over-attribution stays a declared
  limit (26), checked by hand in G0 (21).
- **Q3. The size of G0? Decided (manager, 2026-10-24; owner may override): k = 3 streams per arm, the gate's floor.** That is 6 streams,
  about 300 org runs plus 6 assistant sessions (20.6); the harness can add streams afterwards (20.1). Why: the cost is the owner's to raise.
  The plan states the G0 run estimate on a line of its own, for the owner's approval before G0 runs.
- **Q4. The cost alarm and the assistant's own spend? Reversed (manager, D-E5-6, 2026-10-24).** The per-case warning (`case_total`, 0a.3) and
  the cost alarm compare the user's runs with the user's approved runs; the assistant's relayed runs, and the total, are shown on their own
  line. Reason: E5 s1, where folding them in led the assistant to ask the user to pay for its own work. (The earlier decision, "as designed":
  the alarm fires on total spend because the user pays for both, is superseded.)
- **Q5. The 3-judged-case minimum for the cost alarm? Decided (manager, 2026-10-24; owner may override): as designed.** The minimum stays
  (08 3.3); `case_total` (0a.3) warns per case on the same rule at 1.0x, and each case line shows its ratio whatever the alarm says (6).

### 28.1 Open after E5: decided by the manager (2026-10-24), updated 2026-10-25

`manager-decision-open-questions.md` decides the seven questions of the E5 amendment; each is "decided (manager, 2026-10-24; owner may override)"
and the build uses the decision.
- **OQ-1: which top-ups are the user's approved runs? Decided: 0a.3's rule, as its design decides it** (`user_approved`, section 3; 0a.5 A2
  amends it). Commit 1 re-pins 0b's figures from the rule as merged (A.3); if the rule leaves a case undecided, the coder sends a warning
  instead of choosing. Live inputs: E7 s2's 1-run default (no longer raises the approval), s1 memo 2's grant without a yes, s1 memo 1's
  explicit `budget: 7` (e7-gate 5 item 5).
- **OQ-2: "without a verdict" on which delivery? Decided: the recommendation.** The latest delivery the user was given: the one whose checked
  artifact equals the deliverable file (0a.3's F-E5-5 `relayed` finding), else the latest delivery; a relayed delivery the user never saw is
  shown apart (4.3, section 3). Reason: E5 showed D18 marking memo 1 "without a verdict" in 3 of 3 streams, although Lena judged the version
  she was given (E6 s2 and E7 s2 repeat it).
- **OQ-3: the label of a delivered file that differs from the team's checked version. Decided: `not as delivered`**, P3's own words, with the
  same counts. Reason: in E5 nobody edited a file by hand, so `hand-edited` would assert a cause the files do not show.
- **OQ-4: list an agent that holds runs behind blocked tasks none of which was moved past? Decided: no** (the section is about blocks moved past).
  If a replay (E5 s3's writer, E7 s2's writer) shows such an agent, the coder records it as a finding for the manager and does not change the section.
- **OQ-5: G0's script pin. Decided, updated by e7-gate 5 item 11: E7's committed protocol and harness** (20.1, 20.2), not E5's or E6's.
- **OQ-6: the G0 run cost. Approved by the owner on 2026-10-25: about 230 org runs and about 355 credits** (20.6). The build never starts G0.
- **OQ-7: the wording of the user's-runs case line and the relayed/total line. Decided: the planner's proposal (9.2), the rule is the manager's.**
  Corrected on 2026-10-25 (D2 of commit 1's approval) where it misstated the rule: the header reads `approved: the contract's {budget} per request,
  or more where your hand-downs raised it (runs used + held + new, at that moment)`, because the approved runs are `max(budget, highest ceiling)`,
  not "the budget plus the top-ups". The wording is a reviewable item for the code review.


## Appendix A. Review resolutions

### A.1 Design review of revision 1 (25 findings: 3 HIGH, 12 MEDIUM, 10 LOW)

Every finding was addressed in revision 2; none was backlogged or declined. No resolution changed what the user sees or how the system
behaves beyond 08 row 0b and the binding gate items: where a finding offered a choice, the behaviour-preserving option was taken (DR-11,
DR-12). This table is kept as written for revision 2; where revision 3 changed a text it cites (for example the moved-past wording of DR-2,
or the A5 runs line of DR-4), A.2 says so.

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

### A.2 Design review of revision 2 (14 findings: 2 HIGH, 6 MEDIUM, 6 LOW) and the manager's decision of 2026-10-24

Every finding is addressed in revision 3 with the reviewer's fix, as the manager's decision directs; none is declined. One part is
backlogged by that decision (DR2-8's port). Where a finding offered a choice, the choice is named below. No resolution changes what the user
sees or how the system behaves beyond 08 row 0b, the binding gate items and the manager's decision.

| Id | Sev. | Resolution | Where |
|---|---|---|---|
| DR2-1 | HIGH | The cost alarm's `n` is the number of compared cases (skipped ones excluded); with `min_judged` met and `n == 0` it reads `n/a (0 of 0 cases compared)` (JSON `state: "n/a"`, `compared: 0`), never `no`; the skipped list shows under every state. The verifier line goes through `ratio`: `escapes n/a (0 of 0) judged`. With no delivery the line reads `verifiers: none (no delivery yet)`. `No cases yet` appears exactly when no agent offers a service (top-level or nested) and root gave no one-off task; a defined service with no request renders its block, pinned as the exact "service defined with no request yet" golden and in I3's parametrized test. A unit test covers 3 judged cases whose runs are all not counted. | 6, 9.2, 9.3, 15 I3, 16, 17, 18.1, 22 |
| DR2-2 | HIGH | A git version of ORG.md or AGENT.md that is not UTF-8 (strict decoding) or whose frontmatter does not parse is not compared, gives no mark for either pair it belongs to and counts once in `skipped` (`... unreadable or not parseable`). 12.1's read rule treats a parse failure like `OSError` at every read `quality` makes (contracts, stored versions, playbook versions, the cases, the P3 call, `runs_unknown`'s charter read), with the repository's `except Exception  # noqa: BLE001` pattern because PyYAML may not be imported outside `kernel` and `blueprint`; `quality` never raises on a file that does not parse. Unit tests per read; an integration test in a git org with an AGENT.md version and an ORG.md that do not parse (defaults note, every count, `2 version(s) not compared`), a working charter and a stored contract version that do not parse. | 4.1, 7, 10, 12.1, 13, 16, 18.1, 18.2, 26 |
| DR2-3 | MEDIUM | Per-id basis parts follow the added-id order (added ids in the version's acceptance order, removed ids in the previous version's order, `amendment_ids`); the legacy basis part is `{id} confirmed (link {link})` / `{id} not confirmed`. The s1r excerpt's v2 mark reads `adds C8, C9; removes C5: C8 not confirmed, C9 confirmed (link ...-1753)` (v3-v5 recomputed with `amendment_ids` and given in brackets). `not counted` shows under every state, `n/a` included, so the repeat line reads `n/a (1 of 3 judged cases); not counted: R1's reading C5 (not confirmed)`; the JSON's `not_counted` is present under every state. Every unbracketed line of the E3, s1r and A5 samples was re-checked against 7 and 9.2. | 6, 7, 9.3, 9.4 |
| DR2-4 | MEDIUM | The answering version of a rejection (`answers` == the rejection's id) gives `answer_removes`; a named criterion that version removed types `contract-gap` by rule `answer` with its own text, never `reviewer-miss`. Rule order: `reviewer-miss` (a named criterion carried and kept) is rule 3, `contract-gap` by answer rule 4, so a mixed link is `reviewer-miss` with `contract-gap` in `also`; the "partition" claim is replaced by this choice and its reason. Unit tests for the removal-only answer and the mixed link; 27 item 2 names both cases; D1 covers removals. No pre-registered expectation changes (none has a carried criterion in its link). | 3, 5.1, 5.2, 5.3, 18.1, 24 D1, 27 |
| DR2-5 | MEDIUM | Option (a): `CaseHistory.chains(owner, service, *, since, runs)` and `CaseHistory.one_off_cases(*, runs=True)` (3 -> 5 methods); `runs=False` reads mail only (no run log, charter or playbook file). `DerivedCaseHistory(catalog, agents, mail, words, timelines, counter, charters: CharterReader)` reads the charters; `DerivedCaseRecords(history, catalog, agents, mail, versions, bars, deliverables)` loses `charters` (7 collaborators). FEAT-7 updates ARCHITECTURE 3.22's collaborator sentence. | 4.1, 10, 12.1, 12.5, 23 |
| DR2-6 | MEDIUM | The first delivery is the case's delivery with the lowest step; `never delivered ({case state})` only when no task of the case was delivered. Unit test: head blocked, rework done. | 4.3, 9.2, 9.4, 18.1 |
| DR2-7 | MEDIUM | New 9.4: a schema table for every object (key, type, empty/null rule, source text), top-level `"schema": 1`, `ratio` as the text's two-decimal string, every case, escape, mark and id without the text's limits, and new `stalled_error`, `fails_error`, `held_error` so "0" and "unknown" differ. The abbreviated sample is removed; the full E3 JSON is the golden `tests/golden/expected/quality/e3.json` (E3-8), whose every count is fixed by the E3 text through 9.4's source column, plus a schema-conformance test for every replay corpus. | 4.2, 9.1, 9.3, 9.4, 18.1, 19.3 E3-8, 22 |
| DR2-8 | MEDIUM | Second option, as the manager directs: the claim that a pack passes its own lasting words with no core edit is removed from 3, 5.1 and 17.4 (and I9's reason no longer calls the vocabularies extension points); `cause_of(lasting=...)` stays for tests; a `CauseVocabulary`-style port for a pack's words and failure-class mapping is in the backlog, because Phase 3 owns packs and 0b adds no port it does not use. | 3, 5.1, 15 I9, 17, 23 |
| DR2-9 | LOW | D24 records the CLI's `--source human` default as a deviation from go/no-go item 6, with its reason; 8.1 and 25 item 1 cite it. | 8.1, 24 D24, 25 |
| DR2-10 | LOW | S2R-1 pins `...; 4 line(s) removed`; the legacy count reads `legacy verdicts (no source: read as the user's, the 0a rule)` and D21 says "read as the user's"; the carry-over text reads `your relayed rework {R} delivered {path} after the delivery the user judged, and the rejected delivery lists it too` (what rule 2 checks). | 5.3, 9.2, 19.3 S2R-1, 24 D21 |
| DR2-11 | LOW | One blank line between blocks and sections, none inside a block (header included), applied to every sample (the empty-org sample gains its blank lines); `open {o} (stalled {s})`; several fired subjects listed in one line, `R` ids then `C` ids by number (also for `counted`); ONE-OFF-UNKNOWN lists root's sent tasks with a result, service and one-off alike; `service=` naming a nested service renders the nested heading and its line; the unknown-service error lists top-level names first, then nested ones; "released" is the budget sense and every task line reads `left blocked: ...` or `blocked, nothing sent since` (E-5, S1R-3, D19, D23 reworded). | 3, 4.5, 6, 8.3, 9.2, 9.3, 13, 19.3, 24 |
| DR2-12 | LOW | First option: a done or failed case whose window is not cut and holds no run log, charged or credited, gets `runs_unknown = "no run log in its window"` (reason 3) and is skipped by the cost alarm. Pre-registered effects: E2's cost reads `n/a (0 of 0 cases compared)` with its three cases skipped (E2-3); E's alarm stays `n/a (1 of 3 judged cases)` and lists b495 skipped (E-2); A5's alarm stays `n/a (0 of 3 judged cases)`, lists f768 skipped, and the A5 sample's runs line reads `runs not counted (no run log in its window)` (A5-2, A5-4). Declared in 26; E5 data that hits it would move the window (27 item 8). | 4.1, 6, 9.3, 16, 19.2, 19.3, 19.4, 26, 27 |
| DR2-13 | LOW | (a) Named criteria whose task's contract version is not stored give `Cause("untyped", "unreadable", ("contract v{n} is not stored",))`, counted, with a unit test. (b) A failed pre-registered expectation stops the FEAT and the coder sends the manager a warning with the id, both values and the files; the coder never edits an expectation, golden or rule to match, and only a manager-approved amendment changes it (19.3, FEAT-6). (c) 11.3 says no line-length rule applies to SKILL.md, only the 125-line cap. | 5.1, 5.3, 11.3, 18.1, 19.3, 23 |
| DR2-14 | LOW | The header names `docs/research/` files by absolute path (`RESEARCH` = `/Volumes/workspace/hirearchy/docs/research/org-growth`); 11, 11.5 and 18.3 give `followups.md` and `test-policy.md` absolutely; E5's path is absolute in the header, 19.5, 23 and 27, and the snapshot records `s1` and `s2` VALID and, at this revision's check, `s3` VALID too. | header, 11, 11.5, 18.3, 19.5, 23, 27 |
| Q1 | decision | Decided (manager, 2026-10-24; owner may override): no extra question after a one-off delivery; a verdict is recorded only when the user gives one. Already the design (8.1, 8.4, 11.3); revisit if one-off coverage proves too thin. | 28 |
| Q2 | decision | Decided: as designed. Untyped escapes count against the verifier and stay visible; relayed carry-overs (and relayed errors and contract gaps) do not. 26 no longer says the question is open. | 26, 28 |
| Q3 | decision | Decided: k = 3 streams per arm (the gate's floor), about 300 org runs; the harness can add streams afterwards; the plan states the G0 run estimate on its own line for the owner's approval before G0 runs. The overview, 20.1, 20.6 and 21 say k = 3. | 1, 20.1, 20.6, 21, 28 |
| Q4 | decision | Decided: as designed. The cost alarm fires on total spend; relayed runs are shown apart. | 6, 28 |
| Q5 | decision | Decided: as designed. The 3-judged-case minimum stays; `case_total` warns per case. | 6, 28 |

### A.3 Review pass 3 (7 LOW), the manager's decisions after E5, E6 and E7, and the rebase onto `main` `b252d77c`

Review pass 3 (`.agents/tasks/design-review.md`, APPROVED, 0 HIGH, 0 MEDIUM, 7 LOW) closed the design loop; the manager's decision
(`RESEARCH/phase-0b/manager-decision-design-loop.md`) made each remaining LOW a binding plan item. This table is written by plan commit 1 with the
decisions that followed. "Built in" names the plan commits (the plan is `.agents/tasks/plan.md`, section 8).

| Id | Resolution | Where | Built in |
|---|---|---|---|
| DR3-1 | An `answers` contract mark runs its per-id parts over `answer_ids` (the added ids, else the removed ids, in `amendment_ids` order), joined to the basis with `: ` and to each other with `, `; `confirmed` and `not_confirmed` cover the same ids | 7, 9.4 | 15 |
| DR3-2 | An id in `answer_removes` is listed only in the `removes` clause; the `did not have` clause lists the other named ids that are not in `carried` | 5.3 | 11, 25 |
| DR3-3 | 9.4: free text an agent wrote appears only in the playbook lines; artifact paths and model names appear as stored, unclipped. An error record has `budget: null`, `alarms: {}`, `history: null`; the conformance test includes one error record | 9.4, 19.3 E3-8 | 27, 42 |
| DR3-4 | `_records.py`'s read helper keeps the catch and words an exception by its type without importing PyYAML: `does not parse ({type})` for a `yaml` module type, `is not UTF-8`, else `cannot be read ({type}: ...)` | 12.1 | 17 |
| DR3-5 | `catalog.criteria` and `chains`/`one_off_cases` failures are tested (labels `the criteria`, `the cases`); `records()` lists services with `catalog.service_names(addr)` | 12.1, 18.1 | 17 |
| DR3-6 | The template's brace rule: a group with `\|` always shows one alternative with its numbers; a group without is shown only when non-empty or non-zero; zero parts inside a shown group are left out; `not counted` ids keep the rejection's recorded order | 9.2 | 18, 25 |
| DR3-7 | Section 28 cites the published copy of the manager's decision, `RESEARCH/phase-0b/manager-decision-design-loop.md` | 28 | 1 |
| D-E5-6 (reverses Q4) | The warning and the alarm compare the user's runs (`user_cost`) with the user's approved runs (`user_approved`); relayed runs and the total on their own line; 9.2's runs lines and the cost FIRES part; 9.4's `user_cost`, `user_approved`, `budget`, `total`; I4; D6; Q4 | 1, 3, 4.2, 6, 9, 15, 24, 28 | 7 (reuse), 18, 25-28, 40-44 |
| D-E5-6, re-pinned | The figures D-E5-6 moves, computed independently from the kept files under `b252d77c`'s rules and approved by the manager on 2026-10-25 (D1: `user_cost`; D2: the corrected header; D3: the renamed keys; D4: the constructed variant `r3-overspend`): 9.3's E3 sample and s1r excerpt, E3-1, E3-6, E3-8, new E3-9, S1R-5, S2R-3, S3-1, 19.4 (E, E2, A5 with the lower-bound assumption). Result: no study corpus fires the cost alarm | 9.3, 19.3, 19.4 | 40-44 |
| e5-gate 4 item 1 (sequencing) | Header, 20.1, 23, 27 rewritten for D-E5-7, D-E6-8, D-E6-9 and D-E7-1 (below) | header, 20.1 | 1 |
| e5-gate 4 item 2 | Settled by D-E5-6 | 6 | 18 |
| e5-gate 4 item 3 | D4 stays: a verdict on a delivered `blocked` result is a verdict not on a delivery; the team did not report `done` (4.3) | 4.3 | 10, FEAT-010, FEAT-013 |
| e5-gate 4 item 4 / OQ-2 | "Without a verdict" is read on the given delivery (section 3, 4.3) | 4.3 | 17 |
| e5-gate 4 item 5 / OQ-3 | A `relayed` finding is not a file not as delivered; the label is `not as delivered` (4.3, 9.2) | 3, 4.3, 9.2 | 16, 17 |
| e5-gate 4 items 6-8 | Carry-over base clause, rule 4's first live inputs, credits and held runs are checked by FEAT-010's pre-registration; OQ-4 stands (no) | 19.5, 27 | FEAT-010 |
| e5-gate 4 items 9-10 | 20.4 B gains five measures; 20.4 A states the table-row reading of D21 | 20.4 | (study) |
| e6-gate 4 (items 1-3) | The merge rule is D-E6-8's; FEAT-012 pre-registers E6's figures under `b252d77c`; the kill replay is not cited as evidence that the kill is fixed; the view's runs line shows the user's approved runs, not the contract's | header, 19.5 | 50-52 |
| D-E6-8, D-E6-9, D-E7-1, D-E7-7 | 0b merges after its fail-closed final validation if `e7-gate.md` section 3 answers YES (it does); this replaces "after E5 (or E6) PASSes" everywhere; G0 starts after the merge with the owner's OK | header, 20.1, 23 | 1 |
| e7-gate 5 item 2 | The rebase target is `b252d77c`; every commit marked `[rebase onto 0a.3]` (5, 7, 16-18, 23, 25-28, 38, 39) is checked against `git diff 18c4ffb b252d77c`/`6618c0d b252d77c` | verification.md | each |
| e7-gate 5 item 3 | SKILL.md: 0b's re-wrap is planned again on `b252d77c`'s file and keeps 0a.4's lines 72, 92 and 100 and 0a.5's line 39 word for word, at 125 lines or fewer | 11.3 | 23, 39 |
| e7-gate 5 items 4-5 | Every figure is computed under `b252d77c`'s rules (0a.4's `_user_back`, `user_granted`; 0a.5 A2); OQ-1's live inputs recorded | 3, 28.1, 19.4 | 1, 40-44 |
| e7-gate 5 item 6 | "Without a verdict" and verdicts not on a delivery: OQ-2 (reads the given delivery), D4 (4.3) | 4.3 | 17, FEAT-013 |
| e7-gate 5 item 7 | First deliveries and supersession: FEAT-013 pins what the view says for the heads of s1 and s2 | 19.5 | 53 |
| e7-gate 5 item 8 | Causes: rule 4's first live `answer_removes` (s1: C2 removed, C9 added): DR3-1's mark and DR3-2's split get their first live input | 5.3, 7 | 15, 25, FEAT-013 |
| e7-gate 5 item 9 | Not-as-delivered counts, credits and the tier: `credited` is 0 per case; counts that read a delegation's tier see it from `18a4531` on | 4.2, 19.5 | FEAT-013 |
| e7-gate 5 item 10 | Held runs: FEAT-013 checks whether s2's writer has a left-blocked task (OQ-4) | 4.5 | FEAT-013 |
| e7-gate 5 item 11 | G0 pins E7's protocol and harness, up to 15 turns, `; sleep 20`, per-turn ambient snapshots, D-SIGNAL and M-C-8, D8's statement; OQ-6 is about 230 runs and 355 credits | 20.1-20.6 | (study) |
| e7-gate 5 item 12 | Declared limits added: the approved runs are root's hand-downs; "without a verdict" never reads `reflection.rated` | 26 | 1 |
| e7-gate 5 item 13 | FEAT-013 (E7 replays, commits 53-55) added; FEAT-012 and FEAT-013 are unconditional | 23 | 53-55 |
| e7-gate 5 item 14 | 27 gains E7's definitions most likely to move | 27 | 1 |
| 0a.5 section 18 | `user_approved`/`user_ceiling` (A2), the overspend sentences, `TOPUP`/`HELD` (A1), `open_client_items` human-tier (C), `still_open` (F-E7-7), the lead prompt (F-E7-8), the budget question (B), SKILL.md line 39: read as 0a.5 states them; D4 does not read `still_open` as the user's accept | 3, 4.3, 8.5, 11.3 | 1 |
| OQ-1 to OQ-7 | Decided by the manager; see 28.1 | 28.1 | 1 |

### A.4 The planner's corrections (no behaviour change unless named)

| Id | Correction | Built in |
|---|---|---|
| PC-1 | `services.api` re-exports `contract_of` (from `_parse.py`) and `amendment_ids` (from `_criteria.py`), and gains `version_in_force(contracts, when) -> Contract \| None`, extracted from `_criteria.in_force`; the late-re-export rule applies: a pure rule that lives in a private module but is exported from `api.py`, and whose module imports types from that `api.py`, is imported at the end of `api.py`, under the comment `# Pure rules re-exported from their modules; they import the types above, so these imports come last.` (`services.api`, `reflection.api`) | 4 |
| PC-2 | `quality` joins `observability/_trace.py:READ_ONLY_TOOLS` and `kiro/_launch.py:READ_ONLY_TOOL_IDS` (pinned equal by `tests/architecture/test_read_only_tool_ids.py`): a `quality` call does not end a request's "waiting on root" span | 29 |
| PC-3 | Health's test worlds get `MailSignedDeliveries(agents, mail)`, the pre-0b delivery rule as a fake; `FixedSignedDeliveries` serves the new unit tests; the delivery-derivation tests move to reflection and `CaseSignedDeliveries` | 34 |
| PC-4 | `Cause` gains the renderer fields `version: int = 0`, `answering: int = 0`, `removes: tuple[str, ...] = ()` (5.3's texts need them); the JSON escape object is unchanged | 11 |
| PC-5 | The CLI prints no reply step after a one-off verdict (`FeedbackCommand.run` prints none for service verdicts; adding one would change the CLI for them) | 21 |
| PC-6 | The first-delivery rule (4.3) is computed by the renderer from `ServiceRecord.deliveries` and tested in `progress` | 25 |
| PC-7 | The quality goldens live in `tests/golden/test_golden_quality.py` (`golden_support.check`), which materializes the corpora with the replay kit; the e2e module asserts the per-id expectations; pre-registered goldens are copied by hand (method P), E3's JSON is generated once and reviewed key by key | 28, 41, 42 |
| PC-8 | Golden counts measured: 15 files regenerated (18 file changes) plus 7 new, before any change 0a.3 to 0a.5 made to the same files; root's and agents' health text goldens 0; plan blocks 3 files | 22 |
| PC-9 | Tests that pin a pre-0b rule are replaced on purpose in their commits (health's relayed-rework and non-service delivery tests, the feedback-for-requests-the-actor-sent test, the plan-checks count test, the help command count, the README health row) | 20, 30, 34, 35, 38 |
| PC-10 | `app/wire_health.py` gains `escape_counter(b) -> MailEscapeCounter`, used by the analyzer's provider and by `wire_progress.py`'s `HealthFailCounts` | 28, 34 |
| PC-11 | The reflection test world passes a `CharterReader` as `DerivedCaseHistory`'s 7th collaborator (the charters of `agents.testing.fs_agents(d.root)` over disk, `d.agents` over memory) | 9 |
| PC-12 | The README section is `## Quality (phase 0b)`, after the last `## Org growth: phase ...` section and before `## Security notes`, at most 30 lines (a new test caps it) | 32 |

### A.5 As built (plan commit 49)

Written after FEAT-001 to FEAT-010 and ARCHITECTURE.md (commit 48). Test runs and SCOPED summaries are in `.agents/tasks/verification.md` (never
committed), not here. Where this appendix differs from an earlier section, this appendix wins. FEAT-012 (E6 replays, commits 50-52) and FEAT-013 (E7
replays, commits 53-55) come after the code-review loop; each adds its pre-registration to 19.5 and its commits to the table below.

#### A.5.1 Commit numbering

The plan's numbering (section 23) held, with these differences: commit 5 was not needed (B2.1), and four commits were added (marked `extra`). 48 plan
commits and 4 extra commits make 52 build commits, on top of the three design revisions.

| Plan # | Commit | Subject | Note |
|---|---|---|---|
| rev 1-3 | `6e88ec1e` | docs(design): phase 0b, the quality view, rule-typed causes, the timeline, one-off cases and the noise study |  |
| rev 1-3 | `37adc6ff` | docs(design): phase 0b revision 2, resolving the 25 design-review findings |  |
| rev 1-3 | `522df84a` | docs(design): phase 0b revision 3, resolving review findings DR2-1 to DR2-14 and recording the manager's Q1-Q5 decisions | design revisions 1-3, rebased onto `b252d77c` |
| 1 | `949f7681` | docs(design): phase 0b amended: review pass 3 (DR3-1 to DR3-7), the planner's corrections, the E5 decision (D-E5-6) and e5-gate section 4, D-E6-8 and e7-gate section 5 |  |
| 2 | `23984bbb` | refactor(services): the base headings of a rework body are constants of services.api |  |
| 3 | `ca4c0ecc` | refactor(services,reflection): P1's own-words rule is services.criterion_words |  |
| 4 | `54bf7548` | refactor(services): contract_of, amendment_ids and version_in_force are public |  |
| 5 | - | - | none: 0a.3 built `RunCounter.stamps` in 4.2's exact form (B2.1) |
| 6 | `62916dde` | feat(reflection): CaseHistory.chains builds a service's cases from the mailboxes, with or without runs |  |
| 7 | `3a54005f` | feat(reflection): a case counts its credited runs, its top-ups and whether its window was cut |  |
| 8 | `b02b8293` | feat(reflection): root's one-off tasks are cases too |  |
| 9 | `4de6b3b8` | feat(reflection,app): a case whose runs cannot be read says why; the case history reads the charters |  |
| 10 | `40e780f1` | feat(reflection): deliveries, the verdicts that count for them, and who signed them off |  |
| 11 | `a10f8ce0` | feat(reflection): every escape gets a cause typed by rule, and one attribution |  |
| 12 | `f7df183a` | feat(reflection): the quality thresholds are tunable defaults from ORG.md |  |
| 13 | `9c13952e` | feat(snapshots): the org's history lists the commits that changed some paths |  |
| 14 | `d760a79d` | feat(reflection,app): charter and model changes come from the org's git history |  |
| 15 | `0c595230` | feat(reflection): contract and playbook marks on the timeline (DR3-1) |  |
| 16 | `eff90753` | feat(reflection): the deliverable checks return the file's write time and the settled findings |  |
| 17 | `37c7294c` | feat(reflection,app): the records of the cases, with typed escapes and the timeline (CaseRecords) |  |
| 18 | `783a4f54` | feat(reflection): the repeat and cost alarms, over the judged cases |  |
| 19 | `4332ba2a` | feat(reflection): shown_name is public |  |
| 20 | `12eaa3fb` | feat(services): root's feedback records the user's verdict on a one-off task |  |
| 21 | `c9e9e879` | feat(reflection,mcp_server): the reply to a one-off verdict names the next step |  |
| 22 | `a811ff59` | docs(mcp_server,services,cli): feedback says it takes one-off tasks |  |
| 23 | `21b7c026` | docs(skill): step 5.6 records a one-off verdict the user states, with no extra question |  |
| 24 | `fb60e4e6` | feat(progress): the tasks a blocked result holds runs on, and those left blocked |  |
| 25 | `29dbd3be` | feat(progress): the text of a service block (DR3-2, DR3-6, PC-6, D-E5-6) |  |
| 26 | `c9614f28` | feat(progress): the header, the one-off block, nested services and the moved-past section |  |
| 27 | `4356dedf` | feat(progress): the same data as JSON (DR3-3, D-E5-6) |  |
| 28 | `a28fcb5a` | feat(progress,app): the quality report over the records, the states, the budgets and the FAILs (PC-10) |  |
| 29 | `0518a483` | feat(mcp_server,app,observability,kiro): root's quality tool, and its line in the instructions (PC-2) |  |
| 30 | `a563fc89` | feat(cli,app): hirearchy quality [service] [--json] (PC-9) |  |
| 31 | `48e6e39f` | test(e2e,reflection,progress): quality on real organizations, files that do not parse, no writes, no domain words |  |
| 32 | `e757c0fb` | docs(readme): the quality view (PC-12) |  |
| 33 | `afd81dc9` | feat(health): the health JSON carries the escapes that are not the verifier's and the causes it could not read |  |
| 34 | `ff695605` | feat(health,app): health counts escapes by their typed cause (PC-3, PC-9, PC-10) |  |
| 35 | `2e122807` | feat(health,mcp_server,cli): root's health shows the escapes that are not the verifier's (PC-9) |  |
| 36 | `879455b8` | test(e2e): the view's verifier counts equal health's (I5) |  |
| 37 | `3d761189` | fix(dashboard): the narrow workflows screen is captured only once its refresh is done |  |
| 38 | `ee310aef` | feat(blueprint): the plan block shows up to 10 service checks |  |
| 39 | `b7d59c74` | docs(skill): step 5.1 reads the result with inbox |  |
| 40 | `a3b68b51` | test(testkit): the kit that builds an organization from a corpus's kept files |  |
| 41 | `08742c9f` | test(e2e,golden): the replays of E, E2 and A5 (19.3 E-1..E-5, E2-1..E2-6, A5-1..A5-4) |  |
| 42 | `be667225` | test(e2e,golden): the replays of E3, its firing variant and its JSON (E3-1..E3-8, DR3-3) |  |
| 43 | `a8dc0a48` | test(e2e): the replays of E4 s1r, s2r and s3 (S1R-1..S1R-5, S2R-1..S2R-3, S3-1..S3-5, E4-all) |  |
| 44 | `76f2ee66` | test(e2e): the cost check on corpora without run logs (19.4 as amended) |  |
| extra | `10c77a10` | fix(reflection): the repeat line lists a rejection's reading that no human link confirms (design 9.3, DR2-3) | the manager's decision of 2026-10-25, option B for S1R-6 (B9.2) |
| extra | `2d2f9c24` | docs(design): wasteful is the cost alarm's class by definition, not a field (design correction) | the manager's decision of 2026-10-25, option A for E3-9's `wasteful` clause (B9.2) |
| extra | `a172a004` | test(e2e): the constructed variant of E3 that fires the cost alarm (E3-9) | E3-9, the constructed variant `r3-overspend`, added by commit 1 (B9.2) |
| 45 | `6c419701` | docs(design): E5's expectations, pre-registered before any E5 replay test |  |
| extra | `91e19597` | test(e2e): OQ-2's given delivery and P3's relayed finding on a real git history | the manager's condition on commit 45: OQ-2's main path and P3's `relayed` finding on a real git history (B10.1) |
| 46 | `f08f5edb` | test(testkit): manifests for E5's streams |  |
| 47 | `da20f537` | test(e2e): the replays of E5's three streams |  |
| 48 | `f8ce0892` | docs(architecture): phase 0b's ports, records and the quality view |  |
| 49 | the commit that adds this appendix | docs(design): phase 0b as built | this appendix, the as-built corrections of 8.2, 11.3, 11.5, 22 and 23, and the header |
| 50-55 | after the code-review loop | E6 and E7 pre-registrations, manifests and replays | FEAT-012 and FEAT-013 |

#### A.5.2 Goldens as built

Against the plan (section 22, PC-8: 15 files regenerated, 18 file changes, 7 new): **17 files regenerated, 20 file changes, 8 new files.** The
differences are three files that the new `quality` command made necessary (B6.4). `git diff --name-status main...HEAD` over the golden paths lists
25 files: `tests/golden/expected` 14 (8 changed, 6 new; 661 insertions, 21 deletions) and the colocated `expected/` and `golden/` directories 11
(9 changed, 2 new). No other golden changed: the dashboard goldens, `surface_manager*`, `surface_worker`, the health text goldens, `messages/*`,
`events/*`, `files/*`, `charters/*` and `prompts/*` are byte-identical to `main`.

| File | Method | Commit | Lines | Why |
|---|---|---|---|---|
| `tests/golden/expected/mcp/surface_root.txt`, `surface_root_unbound.txt`, `surface_root_setup_mode.txt` | G | 22, then 29 | 10 each, then +44 each | root `feedback` docstring (one-off tasks); the `quality` tool and its instructions line |
| `tests/golden/expected/cli/help_feedback.txt` | G | 22 | 1 | the `task_id` help |
| `src/hirearchy/cli/tests/expected/help_feedback.txt` | H | 22 | 1 | same |
| `tests/golden/expected/cli/help.txt` | G | 30 | 4 added, 2 removed | `quality` in the command list |
| `src/hirearchy/cli/tests/expected/help.txt` | H | 30 | same | same |
| `tests/golden/expected/cli/health_json.txt` | G | 33 | +12, -4 | `not_its`, `causes_unknown` in `to_dict` |
| `src/hirearchy/cli/tests/expected/health_json.txt`, `src/hirearchy/health/tests/expected/org_4000.json`, `org_3d.json`, `eng_4000_repr.txt` | H | 33 | the two fields per agent | same |
| `tests/golden/expected/plans/propose_raw_template_analysis_service.txt`, `propose_filled_template_analysis_service.txt` | G | 38 | 1 each | the 6th check is shown |
| `src/hirearchy/blueprint/tests/golden/second_half.json` | H | 38 | 2 | same |
| `src/hirearchy/cli/tests/expected/no_command.txt`, `unknown_command.txt` | H | 30 | 3 | `quality` in the usage line and argparse's choices (**not in the plan**, B6.4) |
| `tests/golden/expected/cli/help_quality.txt` | N | 30 | 8 | new command |
| `src/hirearchy/cli/tests/expected/help_quality.txt` | H (copy of the N output) | 30 | 8 | same |
| `src/hirearchy/cli/tests/expected/quality.txt` | N | 30 | 37 | the colocated suite requires a scenario for every command (**not in the plan**, B6.4) |
| `tests/golden/expected/quality/empty_org.txt` | P | 28 | 7 | 9.3's empty-org sample |
| `tests/golden/expected/quality/empty_service.txt` | P | 28 | 22 | 9.3's empty-service sample |
| `tests/golden/expected/quality/a5_one_off_block.txt` | P | 41 | 18 | A5-4 |
| `tests/golden/expected/quality/e3.txt` | P | 42 | 38 | E3-5 |
| `tests/golden/expected/quality/e3.json` | N, reviewed key by key against 9.4 and the E3 text | 42 | 399 | E3-8 |

Method: G = generated with `HIREARCHY_UPDATE_GOLDEN=1` and reviewed, H = a hand edit of the changed lines, P = pre-registered (copied by hand from this
design, never generated), N = new file generated once.

Count floors raised (`count.txt`, `main` to the build; none lowered, `tests/architecture/baseline_test_count.txt` unchanged): `reflection/tests`
973 to 1306, `progress/tests` 348 to 465, `services/tests` 987 to 1005, `snapshots/tests` 153 to 169, `health/tests` 366 to 381, `mcp_server/tests` 391 to
403, `cli/tests` 344 to 355, `app/tests` 1012 to 1045 (1043 before commit 48, which added the two parametrized ports), `blueprint/tests` 1310 to 1312,
`kiro/tests` 723 to 724, `observability/tests` 597 to 598, `dashboard/tests` 108 to 109, `skill/tests` 131 to 133. `tests/` has no per-directory floor.
`pyproject.toml` and `uv.lock` are unchanged. ROOT_INSTRUCTIONS measures `2597 2674 2814 27 120` (the plan's expectation, base plus 32); SKILL.md has
125 lines.

#### A.5.3 Deviations

Each deviation was recorded in `verification.md` in its FEAT's section; this table is their consolidation. "Section" names the part of this design
that an earlier text states differently; the as-built reading is the one here.

| Id | Deviation | Why | Section |
|---|---|---|---|
| B2.1 | Commit 5 has no commit. | 0a.3 built `RunCounter.stamps` and the uncredited count of `runs_between` in 4.2's exact form, with their tests. | 4.2, 23 item 2 |
| B2.2 | `chains` reads no contract, so the hand-down ceiling it computes starts from 0 where `cases` starts from the contract's budget. `cases(...)` and `chains(since=contract.created, runs=True)` can differ in `user_ceiling` and `unapproved_reworks` for a chain whose head task was handed less than the contract's budget (a 1-run rework of the user is an approval only if the contract's per-request budget leaves no room; code review CR1-1). So the quality records read the cases with `CaseHistory.cases` (the contract's budget), exactly as `case_total` does, and the alarm and the case line share its `user_ceiling` and `user_approved` (test `test_the_record_reads_the_contracts_budget_as_the_approval_of_a_one_run_rework`). `chains` stays in the `runs=False` reads of health's `deliveries`, which print no approved figure. The pre-registered figures of E, E2 and A5 (on `chains(runs=False)`) held. | 0a.3's `_spend` takes the per-request budget; "chains reads no contract" and "cases becomes chains" cannot both hold. | 4.1 |
| B2.3 | The fakes `FixedCaseHistory.chains` and `ListCaseHistory.chains` keep a case with no `started` time or `started >= since`; their `one_off_cases` return the cases with `service == ""`. | The plan did not specify the fakes. | 12.1 |
| B3.1 | `not_on_a_delivery(case, deliveries)` has no `results` parameter. | The deliveries already carry the verdicts that are on a delivery. | 12.1 |
| B3.2 | `unjudged_cases(cases, deliveries, *, relayed_only=False)` returns a tuple of case ids; `unseen_relayed` is derived by the renderer from `Delivery.given`. | A keyword keeps the return type and adds no public name. | 4.3, 12.1 |
| B3.3 | `cause_of` has two keyword-only parameters beyond the plan, `version` (the carried contract version) and `answering` (the answering version). | Only the caller, which reads the stored versions, knows them (PC-4, `contract v{n} is not stored`). | 5.1, 12.1 |
| B3.4 | In `cause_of`, rule 2's judged delivery uses the earliest human-tier verdict after each delivery's `done` result. It differs from `Delivery.counted` only for a delivery whose every human verdict is voided. | `cause_of` does not know a file's edit time. | 5.1 |
| B3.5 | Details the design left open: `Cause.rules` lists only the matching rules 1 to 5 (empty for `untyped`); rule 2 picks the oldest matching relayed rework and the first shared path; `before_verdict` is the latest relayed rework delivered between the result and the verdict; rule 5's `detail` is the vocabulary entry in the order of `lasting`; the link a rule cites is the latest human-tier link note naming its first criterion, else the latest human-tier link note, else the verdict's own note; `Cause.removes` is set only when rule 4 wins. | Choices where 5.1 and 5.3 are silent. | 5.1, 5.3 |
| B3.6 | `QualityThresholds` has two fields the design does not list, `cost_ratio_text` (the ratio as written) and `source` (`defaults`, or `ORG.md` when at least one valid value was read). The `{what}` words of the "is not {what}" notes are `a whole number of at least 1`, `a whole number from 1 to {window}` and `a number above 0`. A `quality:` key with a null value gets the "not a mapping" note. | The header and the notes need them. | 6 |
| B4.1 | `GitClient.log` answers bytes: no path, or a limit below 1, answers `b""` without running git; `OrgHistory.changes` answers `[]` for it. | A negative limit would be git's "no limit". | 12.3 |
| B4.2 | `BarChanges` is defined in `reflection/_ports.py`; its marks are annotations only there (`TYPE_CHECKING`), and `api.py` re-exports it. | `api.py` imports `_deliverables`, which imports `_ports`. | 12.1 |
| B4.3 | The marks carry their words in a `.text` property, `ContractMark.parts` has one `(id, link)` per id of the answer, and `when` is `None` for a version whose file gives no time. An `answers` version is confirmed only by the user's link on the answered rejection, for removed ids as well as added ones. A removed `R<k>` that matches no assertion is shown as the rejection's message id. | DR3-1's tests live in `reflection`; a link on another rejection must not confirm a removal. | 7 |
| B4.4 | `GitBarHistory` returns each file's marks newest first (files in the order asked, ORG.md last). `DerivedCaseRecords` asks `BarHistory.changes` once per `records()` call for every agent and gives each record the marks of its owner's team and ORG.md's (the one-off record: its assignees' teams), so the 40-commit bound is shared. A version that was deleted or is above 64 KiB counts in `skipped`. | One git read per call. | 7, 12.1 |
| B4.5 | A delivery with several files that are not as delivered counts as edited since the earliest known write time (a write time of 0 is ignored; when none is known, nothing is voided). A `relayed` finding sets `Delivery.given` on the delivery it names. | 4.3 left several files open. | 4.3 |
| B4.6 | `records(service)` raises the unknown-service `OrgError` with 13's text itself (top-level names first, then nested). The one-off record is always the last record and is present even when root gave no one-off task; the renderer decides what to print. | `progress` need not repeat the text. | 12.1, 13 |
| B4.7 | The cost alarm skips a case with `runs not counted` before it tests `budget 0`. A one-off record's approved runs use each case's head task budget. | 6 lists the two reasons without an order. | 6 |
| B4.8 | `Case.top_ups` marks take their time from the id of the task or note (`kernel.stamp_of`). A `PlaybookMark` counts the cited criteria from human-tier link notes only (P1's rule). `Rig.findings` in `test_deliverable_checks.py` zeroes `written` (those tests compare whole findings). `written` is set for the kinds `differs`, `relayed` and `unknown` only. | Reading the ids; P1's rule. | 7, 12.1 |
| B5.1 | Two tests that the plan did not name pinned the pre-0b behaviour and were updated: `test_feedback.py::test_only_the_requester_gives_feedback_on_a_service_request` (root's refusal text) and `test_steps.py::test_feedback_step_is_empty_for_a_note_it_cannot_place` (a human reject on root's plain task now has the one-off step). | They pinned what 8 changes. | 8.1, 8.2 |
| B5.2 | 8.2's last sentence ("the CLI prints the same step") is superseded by PC-5; the body is corrected above. | `FeedbackCommand` prints no step for service verdicts. | 8.2 |
| B5.3 | SKILL.md step 5.6: the first line of the step is lengthened; the re-wrap of lines 98-100 is not done. The file keeps 125 lines. | The re-wrap would change 0a.4's line 100, which is kept word for word; SKILL.md has no line-length rule. | 11.3 |
| B6.1 | A shared module `progress/_quality_facts.py` holds `RecordView`, `QualityView`, `MovedPast`, `HeldTask` and the pure fact functions that the text and the JSON both read, so the two cannot disagree. `_quality.py` also has `blocked_listing` and `service_name`. | One reader of each fact. | 12.4 |
| B6.2 | Test names carry the label `not as delivered` in place of `hand-edited`; the plan's `..._has_null_ratio` is `..._has_no_ratio` in the text suite (the JSON null is in `test_null_rules_of_9_4`). | OQ-3. | 9 |
| B6.3 | Choices the design left open: the notices `and {k} earlier case(s), counted above`, `and {k} earlier escape(s)` and `and {k} earlier` (timeline) follow the lines they cut; an id list shows the 10 newest, then `, and {k} more`; a mark whose file gives no time prints `time unknown`; the not-as-delivered and neither lists show the delivery's task id; `unseen_relayed` counts cases; several fired repeat subjects are joined by `; ` and several FIRES cost cases by `, `; the history line reads `none (...)` or `unknown (...)` followed by the remarks, and only the remarks when marks are listed; the `Thresholds:` line reads `from ORG.md quality:` literally; a signer missing from the FAIL counts reads `0 re-check(s), 0 author rework run(s)`; `its FAILs before delivery: unknown ({error})` carries the error; a nested record that cannot be read is `- {service} (offered by {owner}): cannot be read ({error}).`; an agent mailbox that cannot be read is listed in the moved-past section as `{addr}: blocked tasks cannot be read ({error})`. | 9.2 is silent on them. | 9.2 |
| B6.4 | Goldens beyond the plan: `cli/tests/expected/no_command.txt` and `unknown_command.txt` (3 lines) and a new scenario `quality` with `cli/tests/expected/quality.txt` (37 lines). | The colocated suite pins the whole command list and requires a scenario for every command. | 22 |
| B6.5 | `Org.init` makes the organization a git repository, so the fixture of the P golden `empty_service.txt` deletes `.git` (the sample says "no git"). The expected file is the design's sample, unchanged. | A fixture fix, not an edit of an expectation. | 9.3 |
| B6.6 | `FixedQualityReport` renders the real text over the records a test puts in (default thresholds, no stalled state, no FAIL counts, no moved-past section) instead of answering a fixed string. | The contract suite then passes on both implementations. | 12.4 |
| B7.1 | The 13 delivery-derivation tests of `health/tests/test_escapes.py` moved to `test_mail_signed_deliveries.py`, where they pin the fake `MailSignedDeliveries` that the flag and analyzer suites rely on (PC-3); two that pinned the changed behaviour are replaced (PC-9). | The `health/tests` floor holds. | 10 |
| B7.2 | `tests/e2e/test_org_growth_0a.py::test_8_health_counts_the_escape_and_not_the_relayed_rework` pinned the pre-0b rule and is renamed `..._and_types_the_relayed_reworks_as_not_the_verifiers`: the user's reject of a relayed rework is now a judged delivery of type `relayed-error`. | It is the user-visible effect of 10. | 10, 25 |
| B7.3 | `health/_escapes.py` holds `NOT_ITS`, the three cause names in the view's order; an unknown cause follows them in first-seen order. `health/tests/_support.py` gained the shared builders of the two escape test files. | One order for root's health text and the view. | 10 |
| B7.4 | The escapes segment keeps its rule "shown only when `judged > 0`", and `not its` and `causes unknown` show inside it; the e2e check of I5 compares the owner with the escape lines, not with a verifier line, because the view lists no verifier line for an owner that signed alone. | 9.3's s1r sample. | 10, 15 I5 |
| B8.1 | The flaky screen test was fixed in `SRC/dashboard/_widgets.py:NavTable.watch_virtual_size` (`notify_style_update()` drops the cell, row and line caches once the table has measured its columns), not in `_screens.py`, `_worlds.py` or `_app.py`. On the old code 20 of 3 100 captures differed (about 0.65 %), always `narrow-2-workflows`, always with the same cut table; a frame drawn before the table measured its columns stayed cached, so waiting never helped and a user could see it. After the fix, 0 of 300 under the same load, and the deterministic reproduction (a frame drawn just before the measure) went from 20 of 20 differing to 0 of 100, twice. No retry, no marker, no sleep, no golden changed. | The race is inside the app. | 11.5 |
| B8.2 | The new test pins the condition through a host app that is one `NavTable` and a draw queued behind the table's wake-up, not through a capture of the demo screens. | The race cannot be made to happen in a capture without monkeypatching Textual. | 11.5 |
| B8.3 | Plan section 4's three files for commit 38 were checked against the files rebased onto `b252d77c`: no difference. | 0a.3 and 0a.5 regenerated them for the budget text only. | 11.1, 22 |
| B9.1 | The replay kit's `materialize(corpus, root, variant=None, *, manifest=None)` returns `root/org`; deliverables are `root/deliverables` (E4) or the never-created `root/no-deliverables`. The manifest has a `VARIANTS` entry, so it says "constructed". | The kit's own tests; 19.1 asked for the variant to be labelled. | 19.1 |
| B9.2 | FEAT-009 has eight commits, not five. Two pre-registered expectations stopped it and the manager decided on 2026-10-25: S1R-6 follows the design (option B, `10c77a10`: a rejection's own reading that no human link confirms is listed as `not counted`, under every state), and E3-9's `failure_class wasteful` clause is dropped by a design correction (option A, `2d2f9c24`: `wasteful` is the class of a case the cost alarm counts, by definition, and is not a field). E3-9 itself is `a172a004`. No other expectation moved. | The design contradicted itself on `wasteful`; the code differed from 9.3 on the S1R-6 line. | 4.4, 9.3, 19.3 |
| B9.3 | The per-id replay tests passed on arrival (the kit existed from commit 40), so their RED is the missing golden or kit file where there is one; mutations of their expectations each failed exactly one test. E2's kept charters: only the reviewer's is kept. | No RED is possible for a test written after what it tests. | 19.3 |
| B10.1 | One commit beyond the plan, `91e19597`: tests on a real git history for OQ-2's main path (the delivery the user was given) and P3's `relayed` finding. The replay kit has no org git history, so the replays pin the no-git readings and label them "kit limit". | The manager's condition on commit 45. | 19.3, 19.5, 23 backlog |
| B10.2 | The E5 expectation ids are `E5S<n>-k`, seven per stream, grouping the gate's items 2 to 8; the approved runs under 0a.5 A2 are 17, 14 and 14 for memo 1 (17 for s1's memo 3), where e5-gate section 4 item 2 read 15, 17 and 14. All 24 E5 tests passed on arrival: no pre-registered expectation failed. | A.3 and 19.3. | 19.3 |
| B10.3 | OQ-4 on s3: the writer holds 2 runs behind its blocked task `...-lead-4a85`, which `mail.moved_past` does not release, and the lead sent the writer nothing afterwards, so nothing is left blocked and the moved-past section lists no agent. Recorded as a finding for the manager; the section is unchanged. | OQ-4 decided "no". | 4.5, 28.1 |
| B11.1 | `OwnerPromptSections` takes eight collaborators, not seven (0a.5 added the regressions part, and the listing is a collaborator). `DerivedCaseHistory`, `DerivedCaseRecords` and `FolderDeliverableChecks` take seven. ARCHITECTURE.md 3.22 states the real counts. | The plan's sentence predates 0a.5. | 23 item 11 |
| B11.2 | `DerivedQualityReport` takes nine collaborators (12.4 lists them). R7 caps the methods of a Protocol, not constructor parameters. | Each is a narrow port. | 12.4 |
| B11.3 | ARCHITECTURE.md 3.21 (`services`) does not list the new public names of `services.api` (`contract_of`, `amendment_ids`, `version_in_force`, `criterion_words`, the base-heading constants, the one-off refusals in `_feedback.py`). Commit 48's list did not include them. | Out of the plan's scope for commit 48. | 12.2 |
| M1 | Commit messages carry figures that are wrong and are not amended: commit 7 (`984 -> 995`, real 993), 21 (the `cli` and `mcp_server` raises named the wrong way round), 22 (an unfinished phrase in its golden list; real 6 added and 4 removed per `surface_root*`), 26 (`411 -> 435`, `24 added`; real 427 and 16), 30 (`3 new files`; real 4), 33 ("5 below"; real 2). | Commits are never amended. | - |
