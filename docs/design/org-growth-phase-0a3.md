# Org growth, Phase 0a.3: the batch after the E5 FAIL (technical design)

Status: design, revision 2, approved as amended by Appendix A.2, which overrides the body where they differ. Revision 1 (`8a60035`) was reviewed with CHANGES_REQUESTED (3 HIGH, 8 MEDIUM, 10 LOW); every finding is resolved
below, and Appendix A says how. Branch `feat/org-growth-phase-0a3` off `main` `3cd28b3` (the E5 study commit; product code identical to
`6618c0d`); worktree `/Volumes/workspace/hirearchy/.worktrees/org-growth-0a3`. Baseline at `3cd28b3`: `skills/hirearchy/SKILL.md` 125 lines;
`ROOT_INSTRUCTIONS` 2 565 characters raw, 2 642 at the reference path (`/` + 59 `r`, the measure of `skill/tests/test_skill_services.py`), cap 2 700.

Sources of truth (read in full):
- `docs/research/org-growth/phase-0a2/e5-decision.md` (binding scope, D-E5-1 to D-E5-7): "the decision".
- `docs/research/org-growth/phase-0a2/e5-gate.md`, sections 3 and 4: "the gate".
- `studies/E5-org-growth-0a2-recheck/STUDY.md` (F-E5-1 to F-E5-8) and its `evidence/` (s1, s2, s3; committed in `3cd28b3`, so the replays read
  them from the repository, read-only).
- `docs/design/org-growth-phase-0a2.md` ("0a.2 design"), `docs/design/org-agent-model-floor.md`, and the 0b design, read-only:
  `.worktrees/org-growth-0b/docs/design/org-growth-phase-0b.md` revision 3 ("0b", "0b 4.2").
- `ARCHITECTURE.md` (R1-R13, 2.3, 3.8, 3.21, 3.22, 3.29), `docs/refactor-principles.md`, `docs/research/org-growth/phase-0a2/test-policy.md`
  (the owner's binding test policy).

Abbreviations: `SRC` = `src/hirearchy`, `TESTS` = `tests`, `EV5` = `studies/E5-org-growth-0a2-recheck/evidence`, all in the worktree. Every function
named below was read in the worktree at `3cd28b3`.

## 1. Overview

E5 failed "no regression" in 3 of 3 streams on spend and turns, not on memo content. The decision builds three proposals and four small items:

1. **A (D-E5-1): the case total.** The `case total:` sentence names the runs of root's relayed reworks apart from the user's, tells root they
   are its own spend, and warns only when the user's runs exceed what the user approved. A human rework sent without `budget` gets what is left
   of the case's approved runs (at most the contract's budget, and 1 run when nothing is left). When that is less than one round of the team,
   the reply names the top-up to ask for, on the MCP tool and on the CLI. This rule refuses nothing. `Case.relayed_runs` (0b 4.2's definition)
   and `user_spend`, the sibling of `case_spend`, are built here; 0b reuses them. An agent client's case keeps today's text.
2. **B (D-E5-2): the plan budget.** For a service (whose client is always the human, root), the plan's suggested budget per request covers one
   pass, one internal rework and one round of the client's questions or a rejection: the larger of the estimate + 25% and the estimate plus the
   round, within the user's cap (16 for E5's team without a cap). The shipped service templates carry that number. When a cap or an explicit
   budget keeps a service below it, the `budget-tight` warning gives the number and what it covers. SKILL.md step 6 tells the assistant to
   offer it. `budget-low` is unchanged.
3. **C (D-E5-3): the scheduler outlives the chat call.** First a reproduction with the real kiro-cli 2.33.0 in a `/tmp` sandbox, every kiro-cli
   call under a sandbox `KIRO_HOME`. Then `spawn_detached` starts the scheduler through an intermediate process that exits at once, so the
   scheduler is re-parented and is no descendant of root's MCP server; the launcher takes its pid from the scheduler's pid file.
4. **D-E5-5:** the P2-UNRATED text (F-E5-4); the deliverable note after a relayed rework (F-E5-5); the human tier of rework delegations whose
   revised task carries no trace, through the stamper's batch rule (F-E5-7, a defect: section 7.3); one SKILL.md line for a version the user
   keeps as it is (L-ASIS).

Everything stays derived: no ledger, no new file kind, no message field, no event field.

## 2. Technology stack (locked)

Python 3.11, the existing packages only (`mcp`/FastMCP, PyYAML; Textual untouched), the standard library (`subprocess`, `os`, `sys` for the
detach), `git` (already required), uv, pytest, `mypy==2.4.0 --strict`, `import-linter==2.15`, `scripts/static_checks.py`, `scripts/check.sh`.
No new runtime dependency, no new package, no new dependency edge between packages: the one cross-package need (services asks reflection what
is left of a case) is a consumer-owned port in `services/api.py` implemented by `reflection`, the pattern of `JudgedVersions`. Strict TDD (R11)
under the owner's test policy (section 14). Two tools are used by hand only, never by the test suite: kiro-cli 2.33.0 for the reproduction of
6.1, and a Linux container (`docker`, else `podman`) for the Linux run of the tree-kill test (6.4).

## 3. Shared definitions (each defined once)

| Name | Home | Definition |
|---|---|---|
| user task | `reflection` | A task of a case's chain whose `source` is not `relayed`: the head, a `human` rework, or a rework without `source` (sent before 0a). |
| interval | `reflection._cases` | For the chain's task `t` and its successor `next`: the stamps `s` with `t.id[:21] <= s < next.id[:21]`; the last task's interval ends at the window's end, inclusive (0b 4.2). A relayed (user) interval is the interval of a relayed (user) task. |
| grant | `reflection._cases` | A note **the case's client** sent with `budget > 0` to an agent of the owner's subtree, with an id inside the case's run window (progress's grant rule, `progress/_counts.py:LogRunCounts._window`). A **user grant** is a grant of a human client (root) whose id lies in a user interval. An agent client has no user grants. |
| hand-down | `reflection._cases` | A user task (amount: its `budget`) or a user grant (amount: its `budget`). Only a human client's case has hand-downs. |
| committed at `h` | `reflection._cases` | For a hand-down `h`: the user's charged runs with stamps before `h.id[:21]`, plus what the user tasks and user grants before `h` handed down that those runs did not use and their results (with ids before `h`) did not return, at least 0. |
| ceiling of `h` | `reflection._cases` | committed at `h` plus `h`'s amount: the most the user's requests could cost right after `h`. |
| overlapped relayed task | `reflection._cases` | A relayed task of the chain that has a user task after it in the chain, and whose latest result is missing or has an id after its successor's id. Its runs after its successor's send fall in a later interval (0b's split is by send time). |
| relayed overlap | `reflection._cases` | Per overlapped relayed task `t`: `max(0, t.budget + <the client's grants in t's interval> - <what t's latest result returned, at most t.budget> - <charged runs in t's interval>)`, summed over the chain. The most of the relayed tasks' runs that can lie in a user interval. |
| user's approved runs | `reflection.user_approved` | `max(contract budget, Case.user_ceiling)` (4.3). |
| user cost | `reflection.user_cost` | `max(0, user_spend - relayed_overlap)`: the runs the user's requests cost at least. The warning compares it with the approved runs. |
| client round | `reflection._steps.client_round`, `blueprint._budgeting.BudgetPlanner.client_round` | The runs one round of the client's questions or a rejection takes: the owner reads the client's rework (1), and each agent below the owner gets one rework or re-check delegation of about 2 runs (its run and the run of its manager that processes the result): `1 + 2 * (agents below the owner)`. E5's team (lead, writer, reviewer): 5; the four service templates (three agents below the lead): 7. It is SKILL.md's "about 2 runs per delegation it requires + 1" with every agent below the owner delegated once. |

"Overlapped" is used instead of "cut" because 0b's `Case.cut` already means something else (the case window ended at the client's next task
before the final result, 0b 4.1).

## 4. D-E5-1, proposal A: the case total

### 4.1 Decision

Proposal A in full, with its optional part:
- the sentence names the relayed runs apart ("N runs used: U by the user's requests, R by your relayed rework `<id>`"), and still shows the total;
- a separate sentence tells root that the relayed runs are its own spend, to report as such; while a relayed rework has used no run yet, the
  sentence says so instead of printing "0 by your relayed rework";
- "exceeds ... tell the user" compares the user's cost (`user_cost`) with the user's approved runs (`user_approved`);
- a human rework without `budget` is handed what is left of the approved runs, at most the contract's budget. When nothing is left it is
  handed 1 run, the minimum a task carries, so that the owner can read it. When what it got is less than one client round and the approved
  runs not yet used do not cover the rest, the reply names the top-up to ask for (4.5), on the MCP tool and on the CLI. This rule refuses no
  request;
- the case of an agent client (`client_kind == "agent"`) keeps today's text byte for byte.

`case_spend` stays as it is, word for word, and a test pins that `user_spend == case_spend` on every case without a relayed task. 0b's
invariant I4 ("one spend function: `case_spend`, called by `case_total` and `cost_alarm`") no longer holds as written once `case_total` warns
on the user's cost; 0b's amendment restates it under D-E5-6 (4.9).

### 4.2 The data model, in 0b 4.2's form

| Count | Definition | Files | Function |
|---|---|---|---|
| runs | charged run logs of the owner's subtree in the window | `<addr>/runs/*.log` names; credits in each agent's received boxes | `Case.runs` (unchanged; now counted from `RunCounter.stamps`) |
| relayed runs | charged runs whose stamp `s` satisfies `t.id[:21] <= s < next.id[:21]` for a relayed task `t` of the chain (`next` its successor in the chain; the last task's interval ends at the window's end, inclusive) | same | `Case.relayed_runs` (new; 0b 4.2 word for word, for every client kind) |
| relayed returned | the runs the results of the relayed tasks carried back, each at most its own task's budget (the rule of `Case.returned`, restricted to relayed tasks) | client's received boxes (result `budget`) | `Case.relayed_returned` (new) |
| relayed overlap | section 3 | as runs, plus the client's `sent/` and results | `Case.relayed_overlap` (new) |
| user grants | the budgets of the user grants (section 3); 0 for an agent client | client's `sent/` (notes) | `Case.user_granted` (new) |
| user ceiling | the highest ceiling over the case's hand-downs (section 3); 0 for an agent client and for a case built by hand | client's `sent/`, received boxes, run log names | `Case.user_ceiling` (new) |
| spend | `case_spend(case)` | as above plus result `budget` headers | unchanged |
| user spend | `case_spend` restricted to the user's requests: the user's charged runs (`runs - relayed_runs`), plus, while the case is not finished (open or blocked), the runs handed down for the user tasks that were neither used by those runs nor returned by those tasks' results (`returned - relayed_returned`) | as spend | `user_spend(case)` (new, pure, `reflection.api`) |
| user cost | `max(0, user_spend - relayed_overlap)` | as spend | `user_cost(case)` (new, pure) |
| user committed | user spend as if the case were open, with the user grants counted as handed down: what the user's requests used or the team still holds for them | as spend, plus root's notes | `user_committed(case)` (new, pure) |
| user's approved runs | `max(contract budget, Case.user_ceiling)` | current `SERVICE.md` `budget` | `user_approved(case, budget)` (new, pure) |

`RunCounter` (private port, `SRC/reflection/_ports.py`) gains `stamps(team, start, end) -> list[tuple[str, bool]]`: the 21-character stamps of the
team's run logs in the inclusive window, each with whether a run credit names its stem. `runs_between` becomes the count of the uncredited
stamps (no caller changes). `Case.runs` and `relayed_runs` are computed in `DerivedCaseHistory` from one `stamps` call per case. This is 0b
4.2's paragraph; 0b adds `Case.credited` from the same call.

The pure functions, in `SRC/reflection/api.py` (exported in `__all__`):

```python
def user_spend(case: Case) -> int:
    """The runs a case costs the user (pure): ``case_spend`` restricted to the user's requests, the tasks of the chain that are not relayed
    reworks. Equal to ``case_spend`` when the chain has no relayed rework."""
    runs = case.runs - case.relayed_runs
    if case.state in ("done", "failed"):
        return runs
    budget = sum(t.budget for t in case.tasks if t.source != "relayed")
    return runs + max(0, budget - runs - (case.returned - case.relayed_returned))


def user_cost(case: Case) -> int:
    """The runs the user's requests cost at least (pure): ``user_spend`` less the runs of relayed reworks that can lie in a user's interval
    (``case.relayed_overlap``). The warning of ``case_total``, and 0b's cost alarm, compare it with ``user_approved`` (D-E5-6)."""
    return max(0, user_spend(case) - case.relayed_overlap)


def user_committed(case: Case) -> int:
    """What the user's requests used or the team still holds for them, whatever the case's state (pure): what a new rework draws on."""
    runs = case.runs - case.relayed_runs
    budget = sum(t.budget for t in case.tasks if t.source != "relayed") + case.user_granted
    return runs + max(0, budget - runs - (case.returned - case.relayed_returned))


def user_approved(case: Case, budget: int) -> int:
    """The runs the user approved for a case (pure): the contract's per-request ``budget``, raised to the highest ceiling root set for the
    user's requests (``case.user_ceiling``; 0 for an agent client, whose case therefore reads the contract's budget)."""
    return max(budget, case.user_ceiling)
```

### 4.3 Why the approval is the highest ceiling

The files record what root handed down, never what the user said. A rule must therefore read the user's approval from root's hand-downs, and
it must not let the new default hand down more than the user approved. Three readings were compared on E5's chains:

| Reading | s1 T6 (10 user runs) | s2 T5 (14 committed) | A no-budget human rework after 0a.3 |
|---|---|---|---|
| Every human rework's budget and every grant is a top-up | 24: no "exceeds" | 17: no "exceeds" | counts the rework's `left` again: the next default rework is handed runs the user never approved. **Rejected.** |
| Only grants (notes) are top-ups | 12: no "exceeds" | 12: "exceeds" fires on runs Lena funded. **Rejected** (fails s2's T5 line). | correct |
| **The highest ceiling** (chosen) | 17: no "exceeds" | 14: no "exceeds" | correct, within the two declared limits below |

The ceiling reading says: a hand-down approves only what it hands beyond what was still committed. A human rework without `budget` is handed
`left = approved - committed` when `left >= 1`, so its ceiling equals the approval and raises nothing. An explicit `budget` above what is left,
or a grant, raises the approval by exactly the excess: the SKILL.md rule on budget requests (lines 69-72) has root ask the user before it hands down beyond the approved budget, so
the product reads such a hand-down as the user's yes, as it reads `source="human"` as root's word. Taking the highest ceiling (not the latest)
keeps a later small hand-down from lowering the approval.

Two limits of the reading, declared (section 17) and each pinned by a test (4.7):
1. **Nothing left.** The default then hands 1 run, whose ceiling is `committed + 1`, so the approval grows by 1; by more when an attribution
   limit (item 2, or the overlap of 4.8) had already made `committed` exceed the approval. The files cannot tell this 1 run from an explicit
   `budget=1`.
2. **The case window reopens.** A default rework raises no ceiling, unless charged runs of the team fall between the chain's last final result
   and the rework. Today's window rule (`_cases.py`: the window ends at the chain's final result only while that result is the latest; `later`
   looks only after the new last task) then reopens the window to `None`, so another case's runs in that gap count in this case. They count as
   the user's runs and as approved, so no false "exceeds" follows at the rework, but the approved number grows by them. The same window keeps
   counting the other case's later runs in this case, as today's `case.runs` and today's sentence already do. Example: memo 1 is done at `E`;
   memo 2 is requested and runs `k` runs; then memo 1 gets a human rework `h` without `budget`: `ceiling(h) = approved + k`.

The computation, in `SRC/reflection/_cases.py:DerivedCaseHistory.cases`, per case, from what the builder already reads (`tasks`, `results`,
`sent`, `team`, `kind`, the window `start`/`end`) plus one `stamps` call:

```python
human = kind == "human"                                                # the client is root
stamps = self._counter.stamps(team, start, end)                       # [(stamp, credited)], start = tasks[0].id[:21]
charged = [s for s, credited in stamps if not credited]
bounds = [(t.id[:21], tasks[k + 1].id[:21] if k + 1 < len(tasks) else None) for k, t in enumerate(tasks)]

def within(s: str, b: tuple[str, str | None]) -> bool:
    return b[0] <= s and (b[1] is None or s < b[1])

relayed = [b for t, b in zip(tasks, bounds) if t.source == "relayed"]

def in_relayed(s: str) -> bool:
    return any(within(s, b) for b in relayed)

notes = [m for m in sent if m.type == "note" and m.budget > 0 and m.to in team
         and m.id[:21] >= start and (end is None or m.id[:21] <= end)]  # the client's grants
grants = sorted((m for m in notes if human and not in_relayed(m.id[:21])), key=lambda m: m.id)  # the user grants
users = [t for t in tasks if t.source != "relayed"]
ceiling = 0
for h in sorted([*users, *grants], key=lambda m: m.id) if human else []:  # the hand-downs, oldest first
    runs = sum(1 for s in charged if s < h.id[:21] and not in_relayed(s))
    handed = sum(t.budget for t in users if t.id < h.id) + sum(g.budget for g in grants if g.id < h.id)
    back = sum(min(r.budget, t.budget) for t in users if t.id < h.id and (r := results.get(t.id)) is not None and r.id < h.id)
    ceiling = max(ceiling, runs + max(0, handed - runs - back) + h.budget)
overlap = 0
for k, t in enumerate(tasks[:-1]):                                     # relayed runs that can lie in a later user interval
    r = results.get(t.id)
    if t.source != "relayed" or not any(u.source != "relayed" for u in tasks[k + 1:]) or (r is not None and r.id < tasks[k + 1].id):
        continue                                                       # not relayed, no user task after it, or answered before its successor
    funds = t.budget + sum(n.budget for n in notes if within(n.id[:21], bounds[k]))
    ran = sum(1 for s in charged if within(s, bounds[k]))
    overlap += max(0, funds - (min(r.budget, t.budget) if r is not None else 0) - ran)
```

`Case(..., runs=len(charged), relayed_runs=sum(1 for s in charged if in_relayed(s)), relayed_returned=sum(min(r.budget, t.budget) for t in
tasks if t.source == "relayed" and (r := results.get(t.id)) is not None), relayed_overlap=overlap, user_granted=sum(g.budget for g in grants),
user_ceiling=ceiling)`. `results` is the latest result per task: a task whose latest result came after `h` counts as not answered at `h` (its
budget is still out there), which can only raise a ceiling. The loops are quadratic in the chain's length, which is a handful of tasks.

**E5's numbers** (from `EV5`, verified against the recorded `case total:` lines; no E5 chain has an overlapped relayed task, so every
`relayed_overlap` is 0):

| Stream, moment | Chain (budget, runs, returned) | runs / relayed / user | ceilings | approved | user cost | "exceeds" |
|---|---|---|---|---|---|---|
| s1 T6 (#28) | f07a (12, 5, 7); aae2 human (12, 5, 7); 963a relayed (6, 5, 1) | 15 / 5 / 10 | 12; 5 + 12 = 17 | 17 | 10 (done) | no (was yes) |
| s2 T5 (#21, cut at 6c4f's stamp) | ebe2 (12, 9, 3); 6c4f human (5, open) | 9 / 0 / 9 | 12; 9 + 5 = 14 | 14 | 9 + 5 = 14 | no (was yes) |
| s2 T5 (#23, 6c4f done) | the same, 6c4f (5, 5, 0) | 14 / 0 / 14 | 12; 14 | 14 | 14 | no (was yes) |
| s3 final | e268 (12, 9, 3); c209 human (3, blocked); grant 595d (2) in c209's interval; daff relayed (6) | 18 / 5 / 13 | 12; 12; 14 | 14 | 13 | no (was yes) |

s1 reads 17 because E5's aae2 was handed the contract's 12 again by the old default, and the files cannot tell that from an explicit budget;
s2 reads 14 where Lena approved "5 more" (17), because 3 of the 12 were still unused. Neither reading makes "exceeds" fire, and after 0a.3 the
default no longer hands down more than is left, so new chains do not carry either artifact (Deviation 1).

### 4.4 The texts of `case_total` (`SRC/reflection/_reports.py:TextServiceReports.case_total`)

With `c` the case, `B` the current contract's budget, `A = user_approved(c, B)`, `U = user_cost(c)`, `ids` the chain's relayed tasks (oldest
first, joined by `, `), `s` = `"s"` when there are several (else empty), and `has`/`its` = `has`/`its` for one id, `have`/`their` for several:

- Head, form 1 (today's bytes): `case total: {c.runs} runs used of {c.budget} handed down (contract: {B} per request)`.
- Head, form 2 (`HEAD_SPLIT`): `case total: {c.runs} runs used: {c.runs - c.relayed_runs} by the user's requests, {c.relayed_runs} by your
  relayed rework{s} {ids}; {c.budget} handed down (contract: {B} per request)`.
- `OVER_CONTRACT` (today's sentence, unchanged): `This case now exceeds the per-request budget of {B}: tell the user.`
- `OVER_APPROVED`: `The user's requests now cost {U} runs, more than the {A} the user approved for this case (contract: {B} per
  request{topped}): tell the user.` with `topped` = `, plus {A - B} in top-ups` when `A > B`, else empty.
- `RELAYED_SPEND`: `The runs of your relayed rework{s} are your own spend, not the user's: report them to the user as yours, and never ask the
  user to fund them.`
- `RELAYED_NONE_YET`: `Your relayed rework{s} {ids} {has} used no run yet; {its} runs will be your own spend, not the user's: report them to
  the user as yours, and never ask the user to fund them.`

Which parts are printed (joined as today: the head, then `. ` before each sentence that applies, in this order):

| Case | Head | Overspend sentence | Relayed sentence |
|---|---|---|---|
| agent client (`c.client_kind == "agent"`) | form 1 | `OVER_CONTRACT` when `case_spend(c) > B` (today's rule) | none |
| human client, no relayed task, `A == B` | form 1 | `OVER_CONTRACT` when `U > A` (here `U == case_spend(c)`: today's rule) | none |
| human client, no relayed task, `A > B` | form 1 | `OVER_APPROVED` when `U > A` | none |
| human client, relayed task(s), `c.relayed_runs == 0` | form 1 | `OVER_APPROVED` when `U > A` | `RELAYED_NONE_YET` |
| human client, `c.relayed_runs >= 1` | form 2 | `OVER_APPROVED` when `U > A` | `RELAYED_SPEND` |

The first two rows print exactly today's bytes. E5 s1 T6 becomes:

`case total: 15 runs used: 10 by the user's requests, 5 by your relayed rework 20261024T031317713451-root-963a; 30 handed down (contract: 12 per request). The runs of your relayed rework are your own spend, not the user's: report them to the user as yours, and never ask the user to fund them.`

E5 s2 T5 (#21) becomes `case total: 9 runs used of 17 handed down (contract: 12 per request)` and (#23) `case total: 14 runs used of 17 handed
down (contract: 12 per request)`. In s1, the moment root sent its relayed rework (no run yet), the reply would have read:

`case total: 10 runs used of 30 handed down (contract: 12 per request). Your relayed rework 20261024T031317713451-root-963a has used no run yet; its runs will be your own spend, not the user's: report them to the user as yours, and never ask the user to fund them.`

The approved number is not in the head: it appears where root needs it, in the overspend sentence and in the top-up advice of 4.5
(Deviation 4). The sentence is embedded, unchanged in form, by every `request` reply of a rework (`SRC/mcp_server/_tools_services.py:
_requested`, root's and the agents') and by every `progress` line of a rework chain (`SRC/progress/_lines.py`, which strips the final `.` and
joins with `. `). `status` embeds no case total (checked: `_tools_status.status` renders the tree, the scheduler line and the P3 note), so
`status` changes only through the deliverable note of 7.2.

`ServiceReports.case_total`'s docstring in `api.py` gains: "...for a human client, the runs of root's relayed reworks named apart and called
root's own spend; when the user's requests cost more than the user approved (``user_cost`` against ``user_approved``) it adds that the user must
be told. An agent client's case reads as before 0a.3."

### 4.5 A human rework without `budget`: what is left, and the top-up

**The port** (new, `SRC/services/api.py`, exported; implemented by `reflection`, as `JudgedVersions` is):

```python
@runtime_checkable
class CaseAllowance(Protocol):
    def left(self, owner: str, service: str, revises: str) -> int | None:
        """For a rework of ``revises``, a task of a case of ``owner``'s ``service``: what is left of the runs the user approved for that case,
        the approved runs less what the user's requests used or the team still holds for them (0 or below when nothing is left). None when the
        task is in no case of the service (one sent before the service was last defined from scratch), the service has no contract, or the
        case's client is an agent. ``OrgError``/``OSError`` when a contract, a mailbox or a run log directory cannot be read."""
        ...
```

Implementation `SRC/reflection/_allowance.py:CaseAllowanceOf(history: CaseHistory, catalog: ServiceCatalog)`: the case of
`history.cases(owner, service)` that holds `revises` and the contract of `catalog.read_contract(owner, service)`; it returns
`user_approved(case, contract.budget) - user_committed(case)`, or None as the docstring says. The fake `FixedAllowance(answers: Mapping[str,
int | None])` (keyed by `revises`; a missing key is None) goes in `SRC/services/testing.py` with `IMPLEMENTATIONS[CaseAllowance]`; the contract
suite is `SRC/services/tests/test_contract_case_allowance.py`, re-run from `SRC/reflection/tests/test_contract_case_allowance.py` over
`CaseAllowanceOf` (R8, the pattern of `test_contract_judged_versions.py`).

**The default** (`SRC/services/_request.py:RuleServiceRequester`, 7th collaborator `allowance: CaseAllowance`). The rule lives in `services`
because it is the one layer the MCP tool and the CLI (`hirearchy request --revises`, which stamps `source="human"` unless `--source relayed`)
share. Order of the checks in `request`:
1. The explicit-budget check stays where it is today, before `revises`: `if budget is not None and (isinstance(budget, bool) or int(budget) <
   1): raise OrgError("a request needs a budget of at least 1 run")`. Refusal precedence for an explicit budget is unchanged.
2. The `revises` check and `self._base(...)` (P4), unchanged, so a wrong `revises` or a missing `base` is refused first, as today.
3. Only then the default: `if budget is None: budget = self._default_budget(actor, contract, revises, source)`.

```python
def _default_budget(self, actor: str, contract: Contract, revises: str | None, source: str | None) -> int:
    """The budget of a request that names none: the contract's, except for root's rework the user asked for, which gets what is left of
    the runs the user approved for its case (at most the contract's; 1 when nothing is left). Never refuses."""
    if not (actor == ROOT and revises and source == "human"):
        return contract.budget                       # a fresh request, a relayed rework, an agent's request: unchanged
    try:
        left = self._allowance.left(contract.owner, contract.name, revises)
    except (OrgError, OSError):
        return contract.budget                       # a record that cannot be read: the contract's, as before 0a.3
    if left is None:
        return contract.budget
    if left >= 1:
        return min(left, contract.budget)            # what is left, never more than a fresh request gets
    return 1                                         # nothing left: the minimum a task carries; the reply names the top-up (TOPUP)
```

An explicit `budget` is never changed by this rule.

**The top-up advice** (`SRC/reflection/_steps.py:TextServiceSteps.rework_step`, which root's `request` reply already appends after the case
total for every rework root sends, and which the CLI now prints too). Today it returns `""` for a human rework; it gains this branch for
`task.source == "human"` with `task.service` and `task.revises`:

```python
case, contract = self._history.case_of(task), self._catalog.read_contract(task.to, task.service)
if case is None or contract is None or case.client_kind != "human":
    return ""
need = client_round(self._agents, task.to)
if task.budget >= need:
    return ""
approved = user_approved(case, contract.budget)
spare = max(0, approved - user_committed(case))      # the case now holds this rework's budget too
ask = need - task.budget - spare
if ask <= 0:
    return ""                                        # what is approved and unused covers the round: root may grant it without asking
return TOPUP.format(budget=task.budget, need=need, owner=task.to, left=..., ask=ask, grant=need - task.budget)
```

`client_round(agents: AgentDirectory, owner: str) -> int` is a pure function in `_steps.py`: `1 + 2 * (len(agents.subtree(owner)) - 1)`.

`TOPUP`: `This rework has {budget} run(s), and a rework of this team needs about {need} (1, plus 2 for each agent below {owner}). {left} Ask the user now for {ask} more run(s), with that number; on yes, grant {grant}: send(to="{owner}", budget={grant}, body=<why>) (CLI: hirearchy send {owner} "<why>" --budget {grant}).`

with `{left}` = `Nothing else is left of the runs the user approved for this case.` when `spare == 0` (no number: after a 1-run default the
approved number already includes this rework's own run, 4.3 limit 1), else `{spare} more of the {approved} runs the user approved for this case
are left.`. The grant is a root note to the owner inside the human rework's interval, so it is a user grant and raises the ceiling by exactly
`ask` (the `spare` part was approved already). The relayed branch (the client questions, 0a.1) is unchanged.

Examples (a new-flow s1 after the relayed rework, contract 12, no grant, E5's team: `need` 5):
- approved 12, committed 10: the Summary rework without `budget` is handed 2, and the reply says `This rework has 2 run(s), and a rework of this
  team needs about 5 (1, plus 2 for each agent below lead). Nothing else is left of the runs the user approved for this case. Ask the user now
  for 3 more run(s), with that number; on yes, grant 3: send(to="lead", budget=3, body=<why>) (CLI: hirearchy send lead "<why>" --budget 3).`
- approved 12, committed 12: it is handed 1, and the reply says `This rework has 1 run(s), and a rework of this team needs about 5 (1, plus 2
  for each agent below lead). Nothing else is left of the runs the user approved for this case. Ask the user now for 4 more run(s), with that
  number; on yes, grant 4: send(to="lead", budget=4, body=<why>) (CLI: hirearchy send lead "<why>" --budget 4).`

**The CLI.** `SRC/cli/_commands_services.py:RequestCommand` gains a collaborator `steps: Provider[ServiceSteps]` (5 in all; the CLI's cap is 7).
After its line `request <id> -> <owner> (service ..., budget N...)`, when `--revises` was given, it prints `steps().rework_step(msg)` on its own
line when that is not empty, under the rule of the MCP tool's `_step`: an `OrgError` or `OSError` while reading gives nothing (the request is
already sent and committed), any other error propagates. `SRC/app/wire_cli.py` passes `get(ServiceSteps)` (`cli` already imports `reflection`
for `ServiceReports`: no new edge). The CLI therefore shows the top-up advice of a human rework and, for `--source relayed`, the client
questions, exactly as root's MCP reply does. The CLI prints the same root-addressed `TOPUP` and `REWORK` texts on purpose: the CLI's user
is root, and every text carries its CLI form.

**Docstrings and help.**
- Root's `request` tool, the `budget` line: `budget: runs handed down (default: the contract's; for a rework the user asked for, source="human",
  what is left of the runs the user approved for the case, at most the contract's, and 1 when nothing is left; the usual reserve rule applies)`.
- Root's `request` tool, the reply sentence: `the reply then states the case total (runs used by the whole chain, the user's and your relayed
  reworks' apart, runs handed down, the contract's budget per request), tells you to inform the user when the user's requests cost more than
  they approved, and names the top-up to ask for when a rework the user asked for gets less than a round of the team needs`.
- The agents' `request` docstring is unchanged (the default applies to root only).
- CLI `request --budget`: `runs handed down (default: the contract's; for a rework you asked for, what is left of the runs you approved for the
  case, at most the contract's, 1 when none is left)`.
- `ServiceSteps.rework_step` (`SRC/reflection/api.py`): `For a rework root just sent: with source "relayed", the client questions of the revised
  request's latest result; with source "human", the top-up to ask the user for when the rework has less than one client round of the owner's
  team (1, plus 2 per agent below the owner) and the runs the user approved but has not used do not cover it; "" otherwise, and always for an
  agent client's case.`

### 4.6 Code sites

- `SRC/reflection/_ports.py`: `RunCounter.stamps`. `SRC/reflection/_runs.py:LogRunCounter.stamps`; `runs_between` counts its uncredited
  stamps. `RunCounter` has no fake: the reflection worlds use the real `LogRunCounter` (`reflection/testing.py:190`), which
  `test_run_counter.py` covers; none is added.
- `SRC/reflection/api.py`: `Case` gains `relayed_runs: int = 0`, `relayed_returned: int = 0`, `relayed_overlap: int = 0`, `user_granted: int =
  0`, `user_ceiling: int = 0` (defaulted, so every hand-built `Case` keeps today's meaning: approval = contract budget, user spend = case
  spend); `user_spend`, `user_cost`, `user_committed`, `user_approved`; the `case_total` and `rework_step` docstrings. `case_spend` untouched.
- `SRC/reflection/_cases.py:DerivedCaseHistory.cases`: the computation of 4.3 (still six collaborators).
- `SRC/reflection/_reports.py`: `HEAD_SPLIT`, `OVER_CONTRACT`, `OVER_APPROVED`, `RELAYED_SPEND`, `RELAYED_NONE_YET` and the new `case_total`.
- `SRC/reflection/_allowance.py` (new): `CaseAllowanceOf`. `SRC/reflection/_steps.py`: `client_round`, `TOPUP` and the human branch.
- `SRC/services/api.py`: `CaseAllowance` (exported). `SRC/services/_request.py`: the 7th collaborator, the moved default, `_default_budget`.
  `SRC/services/testing.py`: `FixedAllowance`, `IMPLEMENTATIONS[CaseAllowance]`; the services worlds wire `FixedAllowance({})` (every answer
  None: the contract's budget, today's behaviour) unless a test gives one.
- `SRC/app/fields_services.py`: `case_allowance: CaseAllowance` ("a port of `services` that `reflection` implements: `wire_reflection`
  provides it"). `SRC/app/wire_reflection.py`: `CaseAllowance -> CaseAllowanceOf(b.get(CaseHistory), b.get(ServiceCatalog))`.
  `SRC/app/wire_services.py`: `RuleServiceRequester(..., b.get(JudgedVersions), b.get(CaseAllowance))`. `SRC/app/wire_cli.py`: the
  `RequestCommand` line.
- `SRC/mcp_server/_tools_services.py`: root's `request` docstring only. `SRC/cli/_commands_services.py`: `RequestCommand` (the step) and the
  `--budget` help. `SRC/cli/tests/_fakes.py`: `FakeSteps(ServiceSteps)` (a scripted `rework_step` text, or an error to raise).

### 4.7 Tests to write first (each RED before its code)

- `SRC/reflection/tests/test_run_counter.py`: `stamps` lists the stamps of the inclusive window, sorted, with the credit flag; `runs_between`
  equals the number of uncredited ones.
- `SRC/reflection/tests/test_cases.py` (fs world with explicit run logs and results):
  - `relayed_runs` of head, human, relayed (the runs of the last interval); of a relayed rework followed by a human one (the interval ends at
    the next task); 0 without a relayed task; credited runs are in no count;
  - `relayed_returned`; `user_granted` (a grant in a relayed interval is not a user grant; one outside the window is not a grant);
  - `user_ceiling` on the four E5 shapes of the table in 4.3;
  - an agent client's case: `user_granted == user_ceiling == 0` while its inherited relayed rework still gets `relayed_runs` (0b's definition);
  - overlap: a relayed rework R (budget 6, 2 runs in its interval, no result before H) followed by a human rework H, with R's 4 later runs
    written in H's interval: `relayed_overlap == 4`; the same chain with R answered before H: 0; R as the last task: 0;
  - limit 1 (4.3): nothing left, a default rework of 1 run: `user_ceiling == approved + 1`;
  - limit 2 (4.3): memo 1 done at `E`, `k = 4` charged runs written after `E`, then memo 1's human rework `h` with the default budget:
    `user_ceiling == approved + k`, `user_spend` includes the `k` runs, and `case_total` prints no "exceeds".
- `SRC/reflection/tests/test_pure_functions.py`: `user_spend == case_spend` for every state of a chain without a relayed task (a property over
  the existing fixtures); `user_spend` leaves a relayed task's runs and still-out runs out; `user_cost` subtracts `relayed_overlap` and is never
  below 0; `user_committed` ignores the state and counts grants; `user_approved` is the contract budget for a hand-built case and the ceiling
  when it is higher.
- The gate's 7 files:
  - `SRC/reflection/tests/test_contract_service_reports.py` and `test_reports.py`: each row of the table in 4.4, the zero-run relayed case
    (form 1 and `RELAYED_NONE_YET`, never "0 by your relayed rework"), one and several ids (`has`/`its`, `have`/`their`), an agent client's
    case byte-identical to today's text (also with an inherited relayed rework), no "exceeds" when an explicit human budget raised the
    approval, "exceeds" when the team ran more runs than were handed down for the user's requests, the overlap chain above without "exceeds",
    and the same chain with 2 more charged runs in H's interval (beyond `relayed_overlap`) printing `OVER_APPROVED`;
  - `SRC/progress/tests/test_lines.py` (a multi-sentence total joins with `. ` and no `..`); `test_fakes.py` (unchanged: the fake passes text
    through; kept in the FAST targets); `test_services.py` (the rework of its chain is relayed by the facade's default: the relayed form, no
    "exceeds"; a second test makes the user's requests overspend);
  - `SRC/mcp_server/tests/test_service_tools.py` (the rework reply in relayed form; a human rework without `budget` is handed what is left; the
    `TOPUP` step after the case total; nothing left: sent with 1 run, the reply holds the case total and `TOPUP` asking for `need - 1`, nothing
    refused); `test_tools_services.py` (the step a fake `ServiceSteps` gives for a human rework is appended after the case total, like the
    relayed one).
- `SRC/services/tests/test_request.py` (over `FixedAllowance`): `min(left, contract)`; `left > contract` gives the contract's; `left == 1`
  gives 1; `left <= 0` sends 1 run and refuses nothing; None and a raising allowance give the contract's; a relayed rework, an agent's rework
  and a fresh request are not asked (the fake records no call); an explicit `budget` is kept and never asked; an explicit `budget=0` is
  refused before a wrong `revises` (precedence unchanged); the refusals of `revises` and `base` still come before the default is computed.
- `SRC/services/tests/test_contract_case_allowance.py` (suite) and its re-run in `SRC/reflection/tests/`: None for a task in no case, for a
  retired service and for an agent client; `approved - committed` otherwise, also 0 and below.
- `SRC/reflection/tests/test_steps.py` and `test_contract_service_steps.py` (the `TOPUP` branch): below the round with nothing spare (the
  exact text, both `{left}` wordings); at the round; spare runs that cover it (`""`); an owner with no agent below (`need` 1, `""`); an agent
  client's case (`""`); the text carries its CLI form.
- `SRC/cli/tests/test_commands_services.py` (over `FakeServices` and `FakeSteps`): a `--revises` request prints the step's text on the line
  after its own; an empty step prints nothing more; an `OrgError` from the step prints nothing more and exits 0; a fresh request never asks
  for a step. The existing `RequestCommand(...)` constructions gain the new argument.
- `SRC/cli/tests/test_service_commands.py` (a real org, as its other tests): `ceo` with two agents below (`need` 5), the first request's team
  runs all but 1 of the contract's runs, then `hirearchy request weekly-brief --revises <id>`: the line says `budget 1` and the next line is the
  exact `TOPUP` text with its `hirearchy send ceo ...` form.
- `SRC/app/tests/test_runtime_fields.py` and a wiring test: the field exists, the requester gets the reflection implementation, and the CLI's
  `RequestCommand` gets the runtime's `ServiceSteps`.
- **Replays** (`TESTS/e2e/test_org_growth_0a3.py`, over the new test-only kit `TESTS/testkit/e5_replay.py` described below):
  - `test_e5_s1_t6_the_case_reads_ten_user_runs_and_five_relayed_without_exceeds`: at #28 (`20261024T031704521000`), `case_total(963a)` is
    the exact s1 text of 4.4, `user_spend == 10`, `relayed_runs == 5`, `user_approved(case, 12) == 17`, and neither "exceeds" nor "tell the user"
    is in it;
  - `test_e5_s2_t5_the_rework_lena_funded_does_not_exceed`: at #21 (`cut = "20261024T034308207974"`, 6c4f's own stamp, inclusive) and at #23
    (`20261024T034512547000`), the two exact s2 texts of 4.4, without "exceeds".

**The replay kit** `TESTS/testkit/e5_replay.py` (test-only): `materialize(stream, cut, dest, *, inflight=None) -> Path` writes an organization
at `dest` holding what `EV5/<stream>` had at the 21-character stamp `cut`: `org-files/ORG.md`; each `org-files/<a-b>-AGENT.md` as
`<a/b>/AGENT.md`; `service/history--SERVICE.v1.md` as `lead/services/weekly-meeting-memo/SERVICE.md`; every file of `msgs/<box>` and
`msgs/<a-b>-<box>` with `id[:21] <= cut` in that box of root or of `a/b`; an empty `<a/b>/runs/<stamp>.log` for every file of `run-logs/<a-b>/`
with `stamp <= cut`. `inflight` moves named message ids of an agent into its `inflight/` box (7.3's replays). A missing evidence file fails the
test (`pytest.fail`), as in `e4_replay.py`. The kit reads the evidence only; 0b's general replay kit (0b 19.1) may absorb it.

### 4.8 Zero and empty cases

| Computation or text | Zero or empty case | Result |
|---|---|---|
| `relayed_runs`, `relayed_returned`, `relayed_overlap` | no relayed task | 0, 0, 0 |
| `relayed_overlap` | relayed tasks, none overlapped (each answered before its successor, or last, or no user task after it) | 0 |
| `user_granted`, `user_ceiling` | agent client; a case built by hand; `runs=False` (0b, ceiling only) | 0 |
| `user_spend`, `user_cost` | no relayed task | `user_spend == user_cost == case_spend` |
| `user_approved` | no top-up (`user_ceiling <= B`) | `B` |
| `user_approved` | no contract budget | impossible for a stored contract (`define_service` requires `budget >= 1`); a task with no contract, or of a retired service, gets no case total (`""`, as today) |
| head | no relayed task, or a relayed task with no run yet | form 1 (today's bytes) |
| `OVER_CONTRACT` / `OVER_APPROVED` | no top-up and no relayed task | `OVER_CONTRACT` under today's condition: today's bytes |
| `OVER_APPROVED` `topped` | no top-up (`A == B`) with a relayed task | no `topped` part |
| `RELAYED_SPEND` / `RELAYED_NONE_YET` | no relayed task | neither |
| `RELAYED_NONE_YET` | relayed task(s), 0 relayed runs (just sent, or their runs fell in a later interval) | printed instead of form 2 and `RELAYED_SPEND` |
| overlapped relayed task | its runs after the successor's send | counted as the user's in the head (0b's split, unchanged); the overspend sentence compares `user_cost`, which removes up to `relayed_overlap` |
| window reopened by a later rework (4.3 limit 2) | another request's runs after the rework | counted as the user's and not as approved: `OVER_APPROVED` can fire on them, as today's sentence does; not corrected in 0a.3 (0b's window rule) |
| `case_total` | agent client | today's text byte for byte, whatever its relayed reworks |
| `case_total` | runs that cannot be read | raises as today (no change in 0a.3; 0b adds `runs_unknown`) |
| `CaseAllowance.left` | no case, no contract, agent client | None: the contract's budget |
| `_default_budget` | `left >= B`; `1 <= left < B`; `left <= 0` | `B`; `left`; 1 (and `TOPUP` asks for `need - 1`) |
| `client_round` (reflection) | an owner with no agent below | 1, so `TOPUP` never fires (every task carries at least 1 run) |
| `TOPUP` | budget at or above the round; spare runs that cover the shortfall; agent client | `""` |
| `TOPUP` `{left}` | `spare == 0` | the wording without a number |
| CLI step | the step is `""` or cannot be read | nothing printed after the request line |

### 4.9 What 0b reuses

- `RunCounter.stamps`, `Case.relayed_runs` (0b 4.2 word for word), `user_spend`, `user_cost`, `user_approved`, and the `relayed` finding kind of
  7.2, which 0b's hand-edit attribution must not count as a hand edit (0b 4.3 counts only `differs`).
- D-E5-6: 0b's cost alarm compares `user_cost` with `user_approved`, the comparison of `case_total` (its ratio is `user_cost / user_approved`).
  0b's amendment restates I4 as "one comparison: `user_cost` against `user_approved`, read by `case_total` and the cost alarm"; `case_spend`
  stays for 0b's other uses (the total shown on its own line).
- 0b's `runs=False` path (0b 4.1): `user_ceiling` and `relayed_overlap` depend on the run logs and are 0, like `runs` and `relayed_runs`;
  `relayed_returned` and `user_granted` come from the mailboxes only and are always filled.
- An agent client's case: 0a.3 shows it today's text; whether 0b's alarm reads such a case is 0b's decision (its `user_approved` is the
  contract's budget, since `user_ceiling` is 0).
- 0b's own `Case.credited`, `top_ups`, `cut` and `runs_unknown` are not built here. The names do not collide: 0b's "approved budget" (the
  contract's) and `Case.top_ups` (every later budget, by kind) keep their 0b meaning; 0b's amendment decides whether its view shows
  `user_approved` beside them.

## 5. D-E5-2, proposal B: the plan budget

### 5.1 Decision

The decision says that for a service with a human client the estimate per request covers one pass, one internal rework and the client round,
and that the user sees "a larger suggested budget per request, which they may refuse". In a blueprint every service is offered by the top agent
and defined by root (`_service_rules.py`: "root defines services only for its direct reports"), so every blueprint service has a human client.
So:
- **The suggested budget.** A service without its own `budget` gets `max(ceil(estimate * 1.25), estimate + client_round)`, within the user's
  cap. The shipped service templates (and so the service example) carry that number: 24, 22, 25 and 25 runs for research, documents, code and
  analysis (estimates 17, 15, 18, 18; round 7 each), instead of 22, 19, 23 and 23. The user may refuse it: a cap or an explicit `budget` wins.
- **The warning.** When a cap or an explicit budget keeps a service at or above the estimate but below the estimate plus the round, the
  `budget-tight` warning gives the number and what it covers. E5's plan (cap 12, budget 12, estimate 11, round 5) reads `... 16 per request
  covers one such round`.
- **The plan lines.** The Budget line of the user's plan and the services header of the details name the round and the number.
- **SKILL.md step 6** tells the assistant to offer that number (section 8).
- **`budget-low` is unchanged** (text, path and threshold: the estimate), so no plan is newly refused (5.3). `estimate`, `REWORK_RUNS`,
  `planned_total` and every plain-task text are unchanged.

### 5.2 Code and texts

- `SRC/blueprint/_budgeting.py`:
  - `BudgetPlanner.client_round(agents: Sequence[Agent]) -> int`: `1 + 2 * sum(1 for a in agents if a.parent is not None)`; 0 for no agents.
    Added to the private `BudgetPlanning` Protocol (`_protocols.py`, 5 -> 6 methods; R7 allows 8).
  - `service_budget(sv, est_total, cap, *, round_runs: int) -> int` (the keyword is required, so mypy finds a caller that forgets it):
    ```python
    b = sv.get("budget")
    if isinstance(b, int) and not isinstance(b, bool):
        return b
    plan = max(math.ceil(est_total * SLACK), est_total + round_runs)
    return min(plan, cap) if cap is not None else plan
    ```
    Its docstring: `Runs handed down with each request of service ``sv``: its own ``budget``, else the larger of the estimate plus slack and
    the estimate plus one client round (``round_runs``), within the cap.` `service_budgets` passes `round_runs=self.client_round(agents)`.
  - The `estimate` docstring's last paragraph adds: `A service's planned budget also covers one client round (see ``service_budget``).`
- `SRC/blueprint/_service_rules.py`, the budget check of each service (`total` its budget, `est` the estimate, `r = client_round(agents)`,
  `top` the top agent's name, else `the top agent`); `service_budget` is called with `round_runs=r`:
  1. `total < est`: `budget-low`, unchanged (text and path).
  2. `est <= total < est + r` (new text, code `budget-tight`, path `{where}.budget` when the service names its budget, else
     `needs.budget_runs`, the rule `budget-low` already uses): `{total} runs per request covers one pass and one internal rework (the estimate
     is {est}), not a round of your questions or a rejection, which takes about {r} more (1, plus 2 for each agent below {top}): {est + r} per
     request covers one such round`.
  3. otherwise `total < ceil(est * 1.10)` (`budget-tight`, today's text and path, unchanged): it can fire only when the round is under a tenth
     of the estimate, so no warning of today disappears.
  E5's plan reads: `12 runs per request covers one pass and one internal rework (the estimate is 11), not a round of your questions or a
  rejection, which takes about 5 more (1, plus 2 for each agent below lead): 16 per request covers one such round`.
- `SRC/blueprint/_userplan.py:_user_budget`, services branch: `...; the minimum for one review and rework is {est}, and a round of your
  questions or a rejection takes about {r} more ({est + r} in all). Unspent runs come back to you.` (the clause is left out when `r == 0`, which
  happens only without agents). The plain-task branch is unchanged.
- `SRC/blueprint/_details.py`, the services header: `Budget per request (your cap: 12), estimate 11 for one pass + one review/rework cycle,
  16 with one round of your questions or a rejection:` (the clause is left out when `r == 0`). The plain branch is unchanged.
- `SRC/blueprint/_example_texts.py`: `SERVICE_BUDGETS = {"research": 24, "documents": 22, "code": 25, "analysis": 25}`, and the `budget:`
  comment of `SERVICE_TAIL` becomes `# runs handed down with each request; within needs.budget_runs (the cap for ONE request); leave out for the
  plan's number (the estimate + 25%, or + one round of client questions when more)`.
- `TESTS/testkit/blueprint_world.py`: the `bpm.service_budget(s, est_total, cap)` shim gains `round_runs=0` (a test-only default meaning "no
  client round"), so its existing callers keep their meaning.
- SKILL.md step 6: section 8. README (E1), each within its line: line 279's comment `default = estimate + 25%` becomes `default = the plan's
  number (estimate + 25%, or + one client round when more)`, and line 248's `(size a request at the estimate + 25%, about 2 runs per delegation
  + 1)` becomes `(size a request at the plan's number: the estimate + 25%, or + one client round for a service; about 2 runs per delegation +
  1)`, which keeps the needle `estimate + 25%` of `test_round_f_guidance.py:110` and the section's line cap.

### 5.3 Why no plan is newly refused

`propose_org` and `apply_org` refuse only on issues of level `error` (`blueprint/api.py:87`). The only budget errors are `budget-cap` (the
planned budget above the user's cap) and `budget-low` (the planned budget below the estimate).
- `budget-cap` cannot newly fire: the larger default is still `min(plan, cap)`, and an explicit budget is unchanged.
- `budget-low` cannot newly fire: its threshold (the estimate) is unchanged, a default budget only grows, and an explicit budget is unchanged.
- `client_round` otherwise feeds only the `warning` texts and the two plan lines.
- Root has no budget limit (`budget/api.py`: "Root has no limit"), so a larger contract budget cannot make root's later `request` refused
  either; an agent's own reserve is unaffected (agents never get the service default).

So every blueprint that validates today validates with the same errors. The corpus golden checks it: its regeneration (section 12) may add or
change only rows of level `warning` with code `budget-tight`, and the diff review rejects any other row.

### 5.4 Zero and empty cases

- No agents: `client_round` is 0, the budget check is skipped as today (`elif agents:`), and both plan clauses are left out.
- An owner alone (no agent below): the round is 1 (`est + 1`); the lone-manager service of `test_application_steps.py` stays at 5 runs
  (`max(ceil(4 * 1.25), 4 + 1)`).
- No cap: the default is the larger number, uncapped; `budget-tight` cannot fire for it.
- An explicit budget at or above `est + r`: no new warning; below `est`: `budget-low` as today.

### 5.5 Tests to write first

- `SRC/blueprint/tests/test_budget_planner.py`: `client_round` is 5 for lead, writer, reviewer; 7 for each template team; counts nested agents;
  0 for none. `service_budget({}, 17, 25, round_runs=7) == 24`, `({}, 17, 20, round_runs=7) == 20`, `({}, 11, 12, round_runs=5) == 12`,
  `({}, 11, None, round_runs=5) == 16`, `({}, 40, None, round_runs=7) == 50` (the slack is larger), an explicit budget is kept; the existing
  assertions of lines 73-75 pass `round_runs=0` and keep their values.
- `SRC/blueprint/tests/test_services.py`: E5's blueprint (cap 12, budget 12) gets exactly the warning text above at
  `services[weekly-meeting-memo].budget` and no error; the same blueprint without `budget` gets the same text at `needs.budget_runs`; a budget
  equal to `est + r` gets no `budget-tight`; a budget below the estimate keeps today's `budget-low` text; a default without a cap is `est + r`.
  Line 240's comment `default: the estimate + 25% (22)` becomes `default: the estimate plus one client round (24), within the cap of 25`, and
  lines 241-242 call the shim, whose `round_runs=0` keeps their values.
- `SRC/blueprint/tests/test_plan_block.py`: the services Budget line and the Details header with E5's numbers; a plain task's lines unchanged.
- `SRC/blueprint/tests/test_examples.py`: a new test pins `SERVICE_BUDGETS[kind] == service_budget({}, est, cap, round_runs=r)` for each kind,
  so the templates cannot drift from the rule; lines 160 and 233 (the service example's `budget: 22`) follow the template to 24, each naming
  the 0a.3 rule in its docstring.
- `SRC/blueprint/tests/test_resolver.py`, `test_validate_corpus.py` with `_corpus.py`: unchanged code; the corpus golden is regenerated.
- The plan, template and charter goldens (section 12).

## 6. D-E5-3, proposal C: the scheduler outlives the chat call

### 6.1 The reproduction first (manual, real kiro-cli 2.33.0, before the fix commit and again after it)

Nothing under `~/.kiro` and nothing of the user's organization is read or written by these steps:
- Every real kiro-cli call (`whoami`, `agent validate`, `chat`) runs with `KIRO_HOME=$SB/kiro-home`, the variable the product sets for every
  org run (`kiro/_env.py:run_environment`). kiro-cli then keeps its agents, sessions, settings and logs there. The configuration is the one E5's
  org runs used (a per-org kiro home with the user's `HOME`, protocol A3.2). Step 7 checks that kiro-cli honoured the variable (its session
  record is under `$SB/kiro-home`); the procedure cannot watch kiro-cli's own reads without reading `~/.kiro` itself, so for those it relies on
  `KIRO_HOME`, as the product does for every org run. Where kiro-cli keeps its sign-in is its own matter; the procedure never opens it.
- The hirearchy CLI and the MCP server run with `HIREARCHY_STATE_DIR=$SB/kiro-state`, `ORG_ROOT`/`--root` `$SB/org`, and the MCP server with
  `HOME=$SB/home`, so its `whoami`/`status` skill check (`with_stale_skill_note`, which reads `<HOME>/.kiro/skills/hirearchy/SKILL.md`) cannot
  reach the user's skill even if called.
- The profile allows the model one tool, hirearchy's `start`, and loads nothing global (`includeMcpJson`/`includePowers` false, no resources,
  no hooks).
- No step lists, opens or hashes anything under `~/.kiro`, and there is no fallback to it: each stop condition below ends the procedure.

Steps:
1. `SB=/tmp/hirearchy-0a3-detach-$(date +%s)`; `mkdir -p $SB/bin $SB/kiro-home/agents $SB/kiro-state $SB/home`; `touch $SB/.marker`. `WT` is the
   worktree; `uv --directory $WT sync --frozen` has made `$WT/.venv/bin/hirearchy`, which every step below calls directly (no `uv`, so the
   changed `HOME` of the MCP server needs no uv cache).
2. **Stop condition: sign-in.** `KIRO_HOME=$SB/kiro-home kiro-cli whoami` must exit 0. Otherwise stop and send `warning`: the owner decides
   whether a `KIRO_API_KEY` may be used. Never retry with the user's kiro home.
3. An organization with work in flight (`h() { HIREARCHY_STATE_DIR=$SB/kiro-state $WT/.venv/bin/hirearchy "$@"; }`, a shell function, so the
   command works the same in zsh and bash):
   `h init $SB/org --mission "0a.3 detach reproduction (throwaway)" --model claude-sonnet-5.5`;
   `h --root $SB/org hire root ceo --role CEO --charter "Throwaway reproduction agent."`;
   `h --root $SB/org task ceo --title "Reproduction" --goal "Wait." --acceptance "none" --budget 2`.
4. `$SB/bin/kiro-cli`, a stub for the org's own runs only (no second model call): it answers `--version` (`kiro-cli 2.33.0`), `chat --help`
   (the V3 flags, `--require-mcp-startup` included) and `whoami` as `tests/testkit/fixtures.py:STUB` does, and for `chat` reads stdin, prints
   the `runStarted` line, sleeps 60 s, prints `runFinished`. It is on the MCP server's `PATH` only, never on the shell's: the calls of steps 2,
   5 and 6 use the real kiro-cli.
5. The profile `$SB/kiro-home/agents/repro-0a3-<epoch>.json`, in the V3 shape the product writes (`kiro/_profile_document.py:kiro_profile`; V3
   rejects the pre-V3 keys `allowedTools` and `toolsSettings`, so the one-tool rule is a permission rule), with every value written out
   (no shell expansion inside the file):
   ```json
   {
     "name": "repro-0a3-<epoch>",
     "description": "internal: hirearchy 0a.3 detach reproduction; deleted with its sandbox",
     "prompt": "You call the hirearchy tool start once, with its defaults, and reply with its result only.",
     "mcpServers": {"hirearchy": {"command": "<WT>/.venv/bin/hirearchy", "args": ["mcp"],
       "env": {"ORG_ROOT": "<SB>/org", "HIREARCHY_STATE_DIR": "<SB>/kiro-state", "HOME": "<SB>/home", "PATH": "<SB>/bin:<the shell's PATH>"}}},
     "tools": ["@hirearchy"],
     "resources": [],
     "hooks": [],
     "includeMcpJson": false,
     "includePowers": false,
     "permissions": {"rules": [{"capability": "mcp", "match": ["hirearchy/start"], "effect": "allow"}]}
   }
   ```
   **Stop condition: the profile.** `KIRO_HOME=$SB/kiro-home kiro-cli agent validate --path <that file>` must accept it; otherwise stop with
   `warning` and the validator's message.
6. One call, `cd $SB`: `KIRO_HOME=$SB/kiro-home kiro-cli chat --v3 --no-interactive --require-mcp-startup --model claude-sonnet-5.5 --effort high
   --agent repro-0a3-<epoch> "Call the hirearchy tool start once with its defaults, then reply with its result only."` (claude-sonnet-5.5 at high
   effort, as every seat; no trust flag, as the product's own runs: the permission rule allows `start`).
7. **Stop condition: the kiro home.** `find $SB/kiro-home -type f -newer $SB/.marker` must list the call's session record. If it lists none,
   kiro-cli ignored `KIRO_HOME`: stop with `warning` and never repeat the call. **Stop condition: the call.** `$SB/org/.runtime/events/*/*.jsonl`
   must hold a `scheduler.start` of this call; if not (the tool was denied or not called), stop with `warning` and the call's output.
8. The moment the call returns, and again 5 s later: is the pid of `$SB/org/.runtime/scheduler.pid` alive (`ps -o stat= -p <pid>`: nothing or
   `Z...` is gone)? Is the run's `child_pid` (its `run.start` event) alive? Is the MCP server gone (its pid is in its event file name,
   `mcp-<pid>-<ms>.jsonl`)? Do the events hold `scheduler.exit` and `run.end`?
9. Clean-up: kill only the pids this procedure learned (the scheduler's pid file, the run's `child_pid` and `pgid`, the MCP server's pid from
   its event file name) and processes whose command line names `$SB` (the rule of `tests/testkit/kiro_sandbox.py`); after the record is written,
   remove `$SB` (a path that starts with `/tmp/hirearchy-0a3-detach-`).

Expected before the fix (E5 s3's pattern): within about a second of the return, the scheduler and the run are gone, with no `scheduler.exit`
and no `run.end`. After the fix, in a fresh sandbox on the fix commit: both are alive after the return; then `h --root $SB/org stop` records
`run.end` (`killed: true`) and `scheduler.exit` (`stopped by SIGTERM`). The outcome of both runs (commands, pids, event lines, the session
record's path under `$SB/kiro-home`) goes to `.agents/tasks/repro-detach.md` (not committed) and is summarized in the fix commit's body.

Further stop conditions (send `warning`, do not ship C): the defect does not reproduce before the fix (then kiro-cli does not end the server's
descendants by process tree, and the premise of the fix is wrong); or the scheduler still dies after it (kiro-cli kills by another mechanism,
and the design must be redone).

### 6.2 The detach

`ProcessSpawner.spawn_detached` (`SRC/processes/api.py`) changes its contract and return type:

```python
def spawn_detached(self, argv: Sequence[str], *, cwd: Path, env: Mapping[str, str], log: Path) -> int:
    """Start ``argv`` so that it is no descendant of this process: an intermediate process starts it in a session of its own (stdin /dev/null,
    stdout and stderr appended to ``log``, created if missing), reports its pid and exits at once, so it is re-parented (to launchd or init, or
    to the nearest subreaper on Linux) and outlives this process and every process of this process's tree. Returns its pid. ``OSError`` when
    the intermediate cannot be started, fails, or reports no pid within 10 seconds."""
```

`SRC/processes/_detach.py` (new, standard library only; run as a script by `PopenProcessSpawner`, never imported by product code; the
architecture tests import every module, which the `__main__` guard makes harmless):

```python
"""Started as a script by ``PopenProcessSpawner.spawn_detached``: it starts the detached process and exits at once, so that process is
re-parented and is no descendant of the caller."""

from __future__ import annotations

import os
import subprocess
import sys
from typing import NoReturn


def main(args: list[str]) -> NoReturn:
    """``<log> -- <argv...>``: start argv in a new session with stdin /dev/null and its output appended to log, print its pid, and leave
    without waiting for it. Exit 2 on a malformed command line, 1 when argv cannot be started (the reason on stderr)."""
    if len(args) < 3 or args[1] != "--":
        sys.stderr.write("usage: _detach.py <log> -- <argv...>\n")
        sys.stderr.flush()
        os._exit(2)
    log, command = args[0], args[2:]
    try:
        with open(log, "ab") as out:
            child = subprocess.Popen(
                command, stdin=subprocess.DEVNULL, stdout=out, stderr=subprocess.STDOUT, start_new_session=True, close_fds=True,
            )
    except OSError as error:
        sys.stderr.write(f"{error}\n")
        sys.stderr.flush()
        os._exit(1)
    sys.stdout.write(f"{child.pid}\n")
    sys.stdout.flush()
    os._exit(0)  # no wait and no clean-up of the Popen object: the child's parent is gone at once


if __name__ == "__main__":
    main(sys.argv[1:])
```

`PopenProcessSpawner.spawn_detached` runs `[sys.executable, "-I", str(Path(__file__).with_name("_detach.py")), str(log), "--", *argv]` with
`cwd`, `env`, `stdin=DEVNULL`, `stdout=PIPE`, `stderr=PIPE`, `start_new_session=True`, then `communicate(timeout=10)`: exit 0 and one line that
is a positive integer gives the pid; anything else is the `OSError` of section 9 (on a timeout the intermediate is killed and reaped first).
The scheduler's stdout and stderr are the log, its stdin is `/dev/null`, and `close_fds` closes the pipe to us, so `communicate` returns when
the intermediate exits and never waits on the scheduler. `-I` keeps the intermediate free of `PYTHON*` variables and user site packages; the
scheduler still gets `env` whole (it is passed to the intermediate and inherited).

`SRC/daemon/_launch.py:DetachedLauncher` drops its `Children` collaborator (7 -> 6) and does:

```python
pid = self._spawner.spawn_detached(argv, cwd=self._site.directory(), env=env, log=log)
return self._watch.await_start(pid, log)
```

`StartupWatch.await_start(pid: int, log: Path) -> int` (private port). `SRC/daemon/_watch.py:PidFileStartupWatch(layout, marker, clock,
inspector: ProcessInspector)`, every 0.05 s for up to 10 s:
1. the pid file names `pid`: return the pid read from the file (the scheduler's own record of itself, written by its lock);
2. the process is gone (`inspector.info(pid)` is None or a zombie; `ProcessTableError` counts as not gone) and the exit marker is not empty:
   return `pid`. Any marker was written by this scheduler's own clean exit, because `prepare()` clears the marker before every launch
   (`daemon/_site.py`), which is today's "exit 0 with any marker" rule (`_watch.py`) without the exit code;
3. the process is gone and the marker is empty: raise `OrgError("the scheduler exited at once; {log} ends with:\n{tail}")` (the last 5 log
   lines, as today);
4. after 10 s: return `pid` (a slow start; today's behaviour).

The reported pid is what makes 1 safe against a stale pid file of a dead scheduler and what makes 2 and 3 fast (Deviation 11). The exit code is
not known any more (the scheduler is not our child), so the error names none (Deviation 9). `ChildRegistry` stays and still reaps (nothing is
adopted any more; backlog).

Fakes and their users: `FakeProcessTable.spawn_detached` returns the pid of a row with `ours=False` (no zombie: gone when it exits);
`processes.testing._TrackingSpawner`, `ProcessWorld.start_echo` (returns a pid), `daemon.testing.ScriptedSchedulerSpawner` and the pass-through
in `scheduler/testing.py` follow. `SRC/daemon/tests/test_children.py` builds its handles with `table.spawn(argv, cwd=..., env={}, stdin=None,
stdout=None)` instead of `spawn_detached` (the registry adopts handles, which `spawn_detached` no longer returns). `ProcessWorld` gains
`is_child(pid) -> bool` (real: `os.waitpid(pid, os.WNOHANG)` raising `ChildProcessError` means no; fake: the row's `ours`). `wire_daemon`
builds the launcher without `children` and the watch with the inspector.

### 6.3 Why it survives the parent's whole process tree being killed

After the intermediate exits, the kernel gives the scheduler a new parent: init (pid 1, launchd on macOS) or, on Linux, the nearest ancestor
marked as a subreaper. Its parent-pid chain then no longer passes through the MCP server, so a kill of the MCP server's descendants (found by
parent pid, the only link E5 found between them: F-E5-2) does not reach it. It leads its own session and process group, so a group or session
signal of the MCP server does not reach it either (already so today). Its runs are its own children in their own sessions, so they are
descendants of the scheduler only. The scheduler holds none of the MCP server's descriptors (stdin `/dev/null`, output to the log, the rest
closed), so the end of the MCP server's stdio cannot reach it. Declared limit: on Linux, an ancestor of the MCP server that is a subreaper (a
container init, or a tool that sets `PR_SET_CHILD_SUBREAPER`) adopts the scheduler and could kill its children on exit; macOS has no
subreapers. The reproduction (6.1) is what shows kiro-cli 2.33.0 on macOS kills by tree and not by another mechanism.

### 6.4 Tests to write first

- `SRC/processes/tests/test_contract_process_spawner.py` (real and fake): a detached process is no child of this process (`is_child` False:
  RED today), leads its own session, appends to its log (waited for, no handle any more), creates a missing log, and a log it cannot open is an
  `OSError` (real) or the fake's scripted failure.
- `SRC/processes/tests/test_popen_process_spawner.py`: the intermediate's failure (a command that does not exist) is an `OSError` naming it;
  the pid it returns is alive and not ours; the intermediate itself is reaped; a malformed command line of `_detach.py` exits 2.
- `SRC/daemon/tests/test_startup_watch.py`, `test_detached_launcher.py`, `test_control.py`, `test_children.py`: the watch over a pid (the
  cases of today, with the new error text without the code; any marker with a gone process is a clean exit, `FINISHED` and a grace reason
  alike; an empty marker with a gone process is the error; a stale pid file naming another pid is waited through); the launcher returns the
  watch's pid and adopts nothing.
- `TESTS/e2e/test_scheduler_detach.py` (not marked `integration`: no real kiro, about 5 s; one code path for macOS and Linux):
  1. an org (`poll_seconds` 0.05) with a leaf `ceo` and one root task (budget 2);
  2. a stub `kiro-cli` in `tmp/bin`: the readiness answers of `fixtures.STUB`; for `chat`: read stdin, print `runStarted`, sleep 3 s, run
     `testkit/fake_agent.py` with the absolute venv Python (`FAKE_MODE=work`: the leaf reports done), print `runFinished`;
  3. a parent process (`sys.executable tmp/parent.py <org>`, `PATH=tmp/bin:...`, its own session) that calls
     `Org(<org>).runtime.scheduler_control.start(None, True)`, prints the pid and sleeps, as root's MCP server does;
  4. once `run.start` of ceo is in the events (at most 15 s): collect the parent and every descendant by parent pid (`ps -A -o pid=,ppid=`,
     breadth first) and assert that the scheduler's parent pid (`ps -o ppid= -p <scheduler>`) is neither the parent nor one of its
     descendants; then SIGTERM them all, and 0.2 s later SIGKILL them all (E5 s3's escalation);
  5. within 30 s: a `run.end` of that run with `ok: true`, the task's `done` result, a `scheduler.exit` (finished: no open tasks), and the
     scheduler gone (`ps -o stat= -p <pid>` prints nothing, or a state that starts with `Z`: a container's init may not reap at once); the
     scheduler's pid was not among the killed (the failure message lists both sets);
  6. `finally`: kill the scheduler and the run's group if still alive (only pids the test learned).
  Today it fails at step 4 (the scheduler's parent is the parent process). Under a subreaper ancestor of pytest (a container's init) the
  scheduler is that ancestor's child, outside the killed tree, so the test still decides the question; a subreaper inside the killed tree,
  the limit of 6.3, is outside what any test here can show.
- **The Linux run** (required evidence, section 14): the same file in a Linux container, the worktree mounted read-only and copied inside, so
  nothing in the worktree (its macOS `.venv` included) is written:
  ```
  docker run --rm -v "$WT":/w:ro ghcr.io/astral-sh/uv:python3.11-bookworm sh -c '
    (command -v ps && command -v git) >/dev/null || (apt-get update -qq && apt-get install -y -qq procps git) &&
    mkdir /src && tar -C /w --exclude=./.venv --exclude=./.git -cf - . | tar -C /src -xf - && cd /src &&
    uv sync --frozen -q && uv run --frozen pytest -q -p no:cacheprovider tests/e2e/test_scheduler_detach.py'
  ```
  (`podman run` with the same arguments when `docker` cannot reach a daemon). The command, the image digest, `uname -a` inside the container
  and the test's result line go to `.agents/tasks/verification.md`. If neither tool can run a Linux container on this machine, the step stops
  with `warning`: the owner decides whether the `check` job of the merge's CI run (`.github/workflows/ci.yml`, ubuntu-latest, which runs
  `scripts/check.sh` and so this test) may stand in. It is never skipped silently.

## 7. D-E5-5, the small items

### 7.1 F-E5-4: the P2-UNRATED text

Site: `SRC/services/_define.py:UNRATED`. New text:

```
refused: {n} delivered request(s) of `{name}` have no verdict yet: {tasks}. Record a verdict on each with feedback first: on a delivery the user saw, the user's own, a rejection then its one question (CLI: hirearchy feedback <task id> accept|reject --note ...); on a relayed rework the user never saw, your own, with source="relayed" (CLI: --source relayed), settles it. The contract changes only after the verdicts. Nothing was written.
```

Design D4 already allows it ("any verdict on it or later": `reflection.rated` counts every tier); only the text changes. Derived: nothing new.
Zero case: none (the refusal names at least one task, as today). Test first:
`SRC/services/tests/test_define_gate.py::test_an_amendment_while_a_delivery_has_no_verdict_is_refused_whatever_else_is_passed` asserts the new
text; `test_texts_cli_forms.py` keeps passing (it has `CLI: ` and ends `Nothing was written.`). `RETIRE_UNRATED` is not changed (backlog).

### 7.2 F-E5-5: the deliverable note after a relayed rework

Sites: `SRC/reflection/_deliverable_checks.py:_folder_rule` and `_file_rule`; `SRC/reflection/api.py` (`DeliverableFinding` gains
`relayed: tuple[str, ...] = ()`, the kind `relayed`, and the note's texts).

Rule (derived from the candidate pairs and the checked versions P3 already reads, inside P3's bounds of 40 git pairs and 5 s). Walk the pairs of
the file's name newest first, skipping pairs whose checked version is unknown:
- the newest known pair equals the file: no finding (unchanged);
- it differs and its task is not a relayed rework: `differs` from it (unchanged);
- it differs and its task is a relayed rework: go on to older pairs. The first older known pair that equals the file, with only relayed reworks'
  pairs newer than it, gives the finding `relayed` with `task` = that pair's task (the delivery) and `relayed` = the relayed task ids newer than
  it, oldest first. An older known pair of a task that is not a relayed rework, and that differs, ends the walk: `differs` from the newest
  (unchanged). No equal pair: `differs` from the newest (unchanged).

`_file_rule` applies the same walk to its pairs (today it returns no finding when the file equals any of them; it now returns `relayed` in the
case above, and still no finding when a non-relayed newer pair stands between). Settled as `differs` is: a human-tier verdict on the case at
or after the file's mtime. No path is shown, so nothing is withheld.

Texts (`deliverables_note`; `{name}`, `{folder}` and `{path}` through `shown_name`; `s` when several ids):
- folder: `Deliverable folder {folder} ({services}): {name} is the delivery of task {task} as the team checked it; your relayed rework{s} {ids} (your own reading, not the user's) changed the team's copy after that delivery, so the file is not a deviation.`
- file contract: `Deliverable file {path} ({services}): it is the delivery of task {task} as the team checked it; your relayed rework{s} {ids} (your own reading, not the user's) changed the team's copy after that delivery, so the file is not a deviation.`

Placement: a `relayed` finding is a line of its own, in the order of the findings, and is never counted in a folder block's `{n} file(s) the
team did not deliver as checked`. A folder whose findings are all `relayed` gets no block heading (no "0 file(s)" line): only its `relayed`
lines. A folder with no finding prints nothing, as today.

E5 s1 after the injection reads:

```
Deliverable folder "/tmp/hirearchy-e5-s1-1792811051/deliverables" (service `weekly-meeting-memo`): "memo-2026-10-05.md" is the delivery of task 20261024T031013210098-root-aae2 as the team checked it; your relayed rework 20261024T031317713451-root-963a (your own reading, not the user's) changed the team's copy after that delivery, so the file is not a deviation.
```

Tests first: `SRC/reflection/tests/test_deliverable_checks.py` (fake checked versions: the E5 shape gives `relayed`; a human rework that
differs in between gives `differs` as today; two relayed reworks give both ids; the newest relayed pair equal to the file gives no finding; a
human verdict after the mtime settles it; the file rule's variant); `test_deliverables_note.py` (both texts, several ids, the block count
excludes it, a folder with only `relayed` findings has no block heading, names through `shown_name`); `test_contract_deliverable_checks.py`
(the fs world with real git: the E5 shape).

### 7.3 F-E5-7: the missing human tier is a defect

**Finding.** In s3, the lead's first delegations for memo 2, `...-lead-0a56` (writer, 04:28:06) and `...-lead-16f9` (reviewer, 04:28:55), carry
no `trace` (checked in `/tmp/hirearchy-e5-s3-1792814736/org/lead/sent/`). The stamp rule left them `ambiguous`: the `msg.deliver` event of 16f9
has `trace_rule: ambiguous` with candidates `[...-root-e268, ...-root-dd39]`, because the lead still held memo 1's `blocked` task c209 (trace
e268; a blocked result is not final for `open_task_traces`) while it worked on dd39. The rework delegations df89 and caa9 revise 0a56 and 16f9.
`ServiceReworkContext.fields_for` (`SRC/services/_rework.py`) looks for the tier only `if actor != ROOT and task.trace` of the revised task,
so it found none. Both reworks were themselves stamped dd39 by the stamper's `batch` rule (their events say `trace_rule: batch`):
- df89's run `lead@20261024T043107173996` had the batch `["20261024T043106950333-root-57b3"]`, root's human rework task (trace dd39);
- caa9's run `lead@20261024T043159829894` had the batch `["20261024T043159758365-lead.writer-d2ef"]`, the writer's **result** to df89 (trace
  dd39; `run.start` in `EV5/s3/events`).

The lead's unanswered task in dd39 at both moments was 57b3 (`source: human`; answered by `...-lead-15b2` at 04:33:37, after caa9 at 04:32:31),
so `_tier("lead", dd39)` gives `human`. The 9 delegations that carry the tier revise tasks that had a trace. So the tier rule of 0a.2 7.6 fails
silently whenever the revised delegation was stamped without a trace: a defect.

**Fix.** When the revised task has no trace, the tier is looked up in the trace the stamper's `batch` rule gives for the run (the expression
of `traces/_lookup.py:MailboxTraceLookup.context_trace`, which takes the trace of **every** message in `inflight`, results included):

```python
trace = task.trace or self._batch_trace(actor)
if actor != ROOT and trace:  # the tier of the work actor does in that case; never for root, never without a trace
    ... self._tier(actor, trace) ...

def _batch_trace(self, actor: str) -> str | None:
    """The one trace of the messages in ``actor``'s run batch (its ``inflight`` box), the stamper's ``batch`` rule; None for none or several."""
    traces = {m.trace for m in self._mail.messages(actor, "inflight") if m.trace}
    return next(iter(traces)) if len(traces) == 1 else None
```

The stamp rule itself is not changed: `traces` is not among `services`' dependencies, and the stamp affects every message (backlog). Declared
limit: the stamper tries its open-task rule before the batch rule; when, at the rework's time, the agent holds exactly one open trace, the
rework is stamped with it, while this lookup uses the batch's. Both are the same trace unless the batch holds only messages of another case.

Zero cases: an empty `inflight` box, or messages without a trace, give None (no tier, as today); messages of two traces give None; a revised
task with a trace is unchanged; root never gets a tier.

Tests first:
- `SRC/services/tests/test_service_rework_context.py` (fs and memory worlds): the lead holds a blocked human task of trace A, gets a fresh task
  of trace B, delegates W without a trace, then
  - receives the human rework of B in its batch: `fields_for("lead", W.id)` gives `source: human`;
  - has in its batch only a result of trace B (its writer's report): the tier of B's open task, `source: human`;
  - has a batch with messages of two traces: no tier;
  - a revised task with a trace: unchanged.
- Replays in `TESTS/e2e/test_org_growth_0a3.py`:
  - `test_e5_s3_the_rework_delegation_of_memo_2_inherits_the_human_tier`: `materialize("s3", "20261024T043138264197", ...,
    inflight={"lead": ["20261024T043106950333-root-57b3"]})`, then `fields_for("lead", "20261024T042806761805-lead-0a56") == {"source": "human"}`;
  - `test_e5_s3_the_re_check_delegation_of_memo_2_inherits_the_human_tier`: `materialize("s3", "20261024T043231631185", ...,
    inflight={"lead": ["20261024T043159758365-lead.writer-d2ef"]})`, then `fields_for("lead", "20261024T042855998356-lead-16f9") ==
    {"source": "human"}`.

### 7.4 L-ASIS: one SKILL.md line

Section 8 gives the replaced line. It tells root that when the user keeps the version they have as it is, root records that accept on its task
with `source="human"` and the user's words, also after a reject. Test first: a needle in `SRC/skill/tests/test_skill_org_growth.py`.

## 8. SKILL.md and ROOT_INSTRUCTIONS

SKILL.md stays at 125 lines: both changes replace text inside existing lines.

**Step 6** (section 1, item 6; lines 37-40 today, still 4 lines; lines 37 and 40 are unchanged):

```
6. Budget in runs (each agent wake-up is one run). Default: the estimate + 25%; every agent runs claude-sonnet-5.5 at high effort. A service's per-request
   budget is the plan's: the estimate + 25%, or more to cover one round of the user's questions or a rejection (the lead wakes once per result: about 2 runs per delegation + 1); if the user's cap is lower, say
   in one line what that risks and offer them the number the plan's warning gives (they may keep theirs). Nothing below claude-sonnet-5.5 at high effort is available: never offer a cheaper model, tiers to
   save runs or a lower effort; if the user asks for one, say so in one line.
```

**L-ASIS** (section 5, item 6; line 100 today, still one line):

```
   ("keep it" / "what's wrong"); when they keep the version they have as it is ("I'll take it as it is"), record that accept on its task, `source="human"`, with their words, also after a reject; "deliver as is" or "I'll read it myself" is not an accept: ask, or record nothing yet. A known unmet
```

Needles (matched on flattened, lower-cased text, `test_round_f_guidance.py:78-90`, so moving words across line breaks is safe):
- kept: `about 2 runs per delegation + 1`, `say in one line what that risks`, `"deliver as is" or "i'll read it myself" is not an accept`,
  `ask, or record nothing yet`, and every other needle of the two tests;
- replaced, deliberately, in
  `SRC/blueprint/tests/test_round_f_guidance.py::test_skill_sizes_service_budgets_and_reads_the_send_reply`: `per-request budget is the plan's
  estimate + 25%` (no longer true for a service, 5.1) becomes `per-request budget is the plan's: the estimate + 25%, or more to cover one round
  of the user's questions or a rejection`; the test's docstring names D-E5-2;
- new: `offer them the number the plan's warning gives` (the same test) and `record that accept on its task` (`SRC/skill/tests/
  test_skill_org_growth.py`).

Resulting line count: 125. `ROOT_INSTRUCTIONS` is not edited (2 642 characters at the reference path, cap 2 700).

## 9. Error handling

| Operation | Failure | Recoverable? | Caller receives | Logged |
|---|---|---|---|---|
| `request` (root's human rework, no `budget`) | the allowance cannot be read (`OrgError`, `OSError`) | yes | the request is sent with the contract's budget (today's default) | the `tool.call` event as today; no extra log |
| `request` (root's human rework, no `budget`) | nothing left of the approval | yes (the user may top up) | the request is sent with 1 run; the reply carries the case total and `TOPUP` | `tool.call` with `ok: true` |
| `request` | explicit `budget` below 1 or a bool | yes | `OrgError("a request needs a budget of at least 1 run")`, nothing sent, before the `revises` check (today's precedence) | `tool.call` with `ok: false` |
| `request` reply (MCP) | `rework_step` cannot read the record | yes | the reply without the step (`_step` turns `OrgError`/`OSError` into `""`, as today) | none |
| `request` output (CLI) | `rework_step` cannot read the record | yes | the request line only, exit 0 (the request is sent and committed) | the CLI's `cli.command` event as today |
| `request` reply / output | any other error in the step | no (a bug) | the error propagates, as `_step` does today | as today |
| `case_total` | a mailbox or run log directory cannot be read | as today | the error propagates as today (no change) | as today |
| `spawn_detached` | the intermediate cannot start (`OSError` from `Popen`), exits non-zero, or prints no positive integer within 10 s (killed, then reaped) | yes (try `start` again) | `OSError("could not start <argv[0]> detached: <the intermediate's last stderr line, clipped to 200>")`; the MCP `start` tool returns the tool error | `tool.call` with `ok: false`; the intermediate's stderr is in the message |
| `await_start` | the scheduler is gone and the exit marker is empty | yes | `OrgError("the scheduler exited at once; {log} ends with: ...")` | the scheduler's own output is in its log |
| `await_start` | no pid file after 10 s | yes | the pid (today's behaviour) | none |
| deliverable checks | a checked version unknown, git past its bound | yes | as today (`current`, or the pair skipped) | none |
| `fields_for` | a mailbox cannot be read | as today | the error propagates (as today) | as today |
| reproduction (6.1) | sign-in, profile, kiro home or call check fails | n/a (manual) | the step stops with `warning` to the owner | `.agents/tasks/repro-detach.md` |
| Linux run (6.4) | no container runtime works | n/a (manual) | the final validation stops with `warning` | `.agents/tasks/verification.md` |
| replays (tests) | an evidence file is missing | no | `pytest.fail` naming it | test output |

## 10. Validation of external inputs

- `request(budget=...)`: optional; when given, an `int` of at least 1, not a `bool` (unchanged, and checked first); when given, the allowance
  is never consulted.
- `request(source=...)`: `"human"`, `"relayed"` or None (unchanged); only root's `human` rework gets the new default.
- `CaseAllowance.left`: any `int` (0 and below mean nothing left) or None; the requester treats a value below 1 as nothing left.
- The intermediate's stdout: required; exactly one line holding a positive integer; anything else is the `OSError` of section 9.
- `_detach.py`'s command line: `<log> -- <argv...>` with a non-empty argv; anything else exits 2 (the `OSError` above).
- The pid file: an integer naming the reported pid counts; garbage, another pid or a missing file is waited through (unchanged).
- Blueprint budgets: unchanged validation; `client_round` reads only resolved agents.
- No new external input reaches a stored file: every number above is derived per call.

## 11. Invariants and their owners

| # | Invariant | Owner | Why there |
|---|---|---|---|
| I1 | `case_spend` is unchanged; `user_spend == user_cost == case_spend` when the chain has no relayed rework | `reflection.api` (pure functions; a property test) | 0b reads `case_spend` |
| I2 | One definition of relayed runs, from one `stamps` call per case | `reflection._cases.DerivedCaseHistory` | 0b 4.2 computes `credited` from the same call |
| I3 | The user's approval is derived from the files, never stored | `reflection` (`user_ceiling`, `user_approved`) | the files are the record (R9, no ledger) |
| I4 | Root's human rework without `budget` gets `min(left, contract budget)` when `left >= 1`, else 1; the rule refuses nothing | `services.RuleServiceRequester` | the one layer the MCP tool and the CLI share |
| I5 | One comparison decides the overspend sentence: `user_cost` against `user_approved` (0b's alarm reuses it, D-E5-6) | `reflection.api` (the pure functions) and `_reports.py` | one rule for the warning and the alarm |
| I6 | An agent client's case total reads as before 0a.3 | `reflection._reports.TextServiceReports.case_total` (the first branch) | the user's approval exists only for a human client |
| I7 | No blueprint is newly refused | `blueprint` (`client_round` feeds only the default and `warning` texts; `budget-low` reads the unchanged estimate) | errors decide `propose_org` and `apply_org` |
| I8 | A shipped service template's budget equals the plan's number for its team | `blueprint._example_texts.SERVICE_BUDGETS`, pinned by `test_examples.py` | the template is what the assistant offers first |
| I9 | A scheduler started detached is no descendant of the process that started it | `processes.PopenProcessSpawner` (the only detached spawner) | `daemon` owns the pid and the watch |
| I10 | A file equal to a checked delivery is never called a deviation because of a later relayed rework | `reflection._deliverable_checks` | P3's one comparison |
| I11 | A rework delegation's tier comes from the runtime's mailboxes, never from the agent | `services._rework` | 0a.2 7.6 |

## 12. Golden impact (expected; each regenerated file is named with its line count in its commit)

Methods: **G** `HIREARCHY_UPDATE_GOLDEN=1 uv run pytest tests/golden -k <test>`, then review `git diff`; **H** a deliberate edit of the
package's expected file (colocated expected files have no switch); **S** a throwaway script (not committed) that writes exactly what the test
compares, then review `git diff`.

| Commit | File | Method | Why |
|---|---|---|---|
| A3 | `SRC/progress/tests/expected/all.txt`, `task_1_weekly-brief.txt`, `task_2_weekly-brief.txt` | H | the scenario's rework (`progress/tests/_scenario.py:119`, the facade's default source) is relayed: head form 2 and `RELAYED_SPEND`, or form 1 and `RELAYED_NONE_YET` if its interval holds no run |
| A4 | `TESTS/golden/expected/mcp/surface_root.txt`, `surface_root_unbound.txt`, `surface_root_setup_mode.txt` | G | root `request` docstring (4.5) |
| A4 | `TESTS/golden/expected/cli/help_request.txt`, `SRC/cli/tests/expected/help_request.txt` | G, H | `--budget` help |
| B1 | the 9 service plans of `TESTS/golden/expected/plans/` (`example_blueprint-service.txt`, `propose_{raw,filled}_template_{research,documents,code,analysis}_service.txt`) | G | the template budgets (24, 22, 25, 25; the example 24): the Budget line's number, the split lines (e.g. `lead: starts with 24, ... keeps 14 (own 7 + slack 7)`), the playbook's `Request budget`, `budget: N runs per request`, and the plan ids (they hash the blueprint text) |
| B1 | `TESTS/golden/expected/plans/template_{research,documents,code,analysis}_service.yaml` | G | the `budget:` value and its comment |
| B1 | `TESTS/golden/expected/charters/apply_service_example.md` | G | the service example's budget 22 -> 24 and its playbook's budget plan |
| B1 | `SRC/blueprint/tests/golden/second_half.json` | S | the default budgets of its service plans and playbooks (`service_budgets`) |
| B2 | the same 9 service plans | G | the Budget line's round clause and the Details header's clause; no `budget-tight` (each template now covers its round) |
| B2 | `SRC/blueprint/tests/golden/second_half.json` | S | the same two clauses; the new `budget-tight` text where a cap keeps a service below `est + r` |
| B2 | `SRC/blueprint/tests/golden/validate_corpus.json` | S | the new `budget-tight` rows where a cap or an explicit budget keeps a service below `est + r`; no `error` row changes (5.3) |

Distinct regenerated files: **24** (3 progress, 3 MCP, 2 CLI help, 9 plans, 4 template YAMLs, 1 charter, 2 blueprint JSON); the 9 plans and
`second_half.json` are regenerated twice, once per B commit, each diff reviewed. The gate's "about 19" counted the plan goldens only; the
template budgets (D-E5-2's larger suggested budget, Deviation 7) add the 4 template YAMLs and the charter, and A adds 8.

Must stay byte-identical (the commit stops until a diff is explained): the 10 plain-task plan goldens, `charters/apply_research_example.md`,
`surface_manager*.txt`, `surface_worker.txt`, the reflection `totals_*` (its stories send human reworks with explicit budgets), every
`messages/*`, `events/*`, `kiro/*`, `prompts/*` (the prompt scenario passes `budget=6`), `cli/progress*`, `cli/status*`,
`SRC/cli/tests/expected/request.txt` (a fresh request: no step), the dashboard and observability goldens.

## 13. Test-site rules (existing tests the new default touches)

- **Rule B.** The sites are found by a rule the coder re-runs at commit A4, not by a hand list:
  1. candidates: `grep -rnE --include='*.py' -e 'revises=' -e '"--revises"' tests/e2e src/hirearchy/app/tests src/hirearchy/mcp_server/tests
     src/hirearchy/cli/tests src/hirearchy/reflection/tests src/hirearchy/services/tests src/hirearchy/progress/tests`;
  2. for each hit, read the call (multi-line calls and helpers such as `ask_on`, `request(w, ...)` and `reflection/tests/_support.py:rework`
     included) and keep it when it reaches a `RuleServiceRequester` wired with `CaseAllowanceOf` (the `Org` facade, `build_server(org, ...)`,
     `cli(org, ...)`) as root, with `source="human"` (or the CLI's default) and no `budget`/`--budget`. Calls over the services or reflection
     worlds (`FixedAllowance({})`) and over fakes keep the contract's budget and are not affected;
  3. a kept site whose assertions depend on the budget (a budget, a run count, a case total, a step text, or a later flow that spends runs)
     passes the budget it got before 0a.3 (the contract's) explicitly, so its flow is unchanged; a kept site that asserts only that the rework
     is sent or refused stays as it is;
  4. the A4 commit body lists the grep, every kept site and what was done to it.
  Applied to `3cd28b3` the rule keeps: `TESTS/e2e/test_org_growth_0a.py:138, 202, 291`, `TESTS/e2e/test_org_growth_0a2.py:274`,
  `TESTS/e2e/test_no_bypass_0a2.py:503` (3 surfaces, through `ask_on`; it asserts only `not refused_` and one more sent message, so it stays)
  and `SRC/reflection/tests/test_cases.py:64` (the `Org` facade of `testkit.services_world`). Lines 491 and 497 of `test_no_bypass_0a2.py` are
  refused earlier (by `base`) and are not affected. Two sites that revision 1 listed are not Rule B sites, because their worlds wire
  `FixedAllowance({})`: `SRC/services/tests/test_contract_service_commands.py:715` (the services worlds) and
  `SRC/reflection/tests/test_steps.py:222` (the reflection world). The latter is an A5 site: its assertion `rework_step(<human rework>) == ""`
  stays right only while its owner's round fits the budget the rework carries, which A5 states in the test and its docstring.
- **Rule R.** A case-total test whose rework is relayed by default and is about overspend gets `source="human"` and a scenario in which the
  user's requests run more runs than were handed down; one about the relayed form keeps the relayed default (for example
  `reflection/tests/test_contract_service_reports.py::test_a_case_handed_down_more_than_the_contract_gives_says_so`).
- No assertion is weakened: each changed expectation names the 0a.3 rule it follows in the test's docstring.

## 14. Commit plan and test policy

Conventional commits, one logical change each, the suite green after each, a failing test first (R11). `count.txt` files are raised where
tests are added. Per commit, FAST under `test-policy.md` rule 2 (path `.worktrees/org-growth-0a3`):
`UV_LINK_MODE=copy uv run pytest -q <TARGETS> tests/golden tests/architecture --deselect tests/architecture/test_static_checks.py` (plus
`src/hirearchy/app/tests` when the commit touches `app/`, an `api.py` Protocol or the wiring), then `uv run python scripts/static_checks.py all`.
At the end of each FEAT, SCOPED (rule 3): the union of its TARGETS plus `tests/e2e tests/golden tests/architecture src/hirearchy/app/tests`.
The only full run is `scripts/check.sh` once in the final validation.

| # | Commit | TARGETS |
|---|---|---|
| A1 | `feat(reflection): run stamps and the relayed runs of a case (0b 4.2)` | `src/hirearchy/reflection/tests` |
| A2 | `feat(reflection): the user's spend, cost and approved runs of a case` (incl. `relayed_overlap`, `user_ceiling`) | `src/hirearchy/reflection/tests` |
| A3 | `feat(reflection): the case total names the relayed runs apart and warns on the user's cost` (+ `testkit/e5_replay.py`, the s1 and s2 replays) | `src/hirearchy/reflection/tests src/hirearchy/progress/tests src/hirearchy/mcp_server/tests tests/e2e/test_org_growth_0a3.py` |
| A4 | `feat(services,reflection,app): a rework the user asked for gets what is left of the approved runs` | `src/hirearchy/services/tests src/hirearchy/reflection/tests src/hirearchy/mcp_server/tests src/hirearchy/cli/tests src/hirearchy/app/tests` and the Rule B sites |
| A5 | `feat(reflection,cli): the rework reply names the top-up to ask for, on the MCP tool and the CLI` | `src/hirearchy/reflection/tests src/hirearchy/mcp_server/tests src/hirearchy/cli/tests src/hirearchy/app/tests` |
| B1 | `feat(blueprint): a service's suggested budget covers one client round; the templates follow` | `src/hirearchy/blueprint/tests` |
| B2 | `feat(blueprint): the plan and the budget-tight warning name the client round and the number that covers it` | `src/hirearchy/blueprint/tests` |
| B3 | `docs(skill): step 6 offers the number that covers the client round` | `src/hirearchy/skill/tests src/hirearchy/blueprint/tests/test_round_f_guidance.py` |
| C0 | the reproduction of 6.1 before the fix (no commit; `.agents/tasks/repro-detach.md`) | - |
| C1 | `fix(processes,daemon): the scheduler is no descendant of the process that starts it` | `src/hirearchy/processes/tests src/hirearchy/daemon/tests src/hirearchy/scheduler/tests src/hirearchy/app/tests tests/e2e/test_scheduler_detach.py` |
| C2 | the reproduction of 6.1 on C1, and the Linux run of 6.4 (no commit; `.agents/tasks/repro-detach.md`, `.agents/tasks/verification.md`) | - |
| D1 | `fix(services): P2-UNRATED says your own relayed verdict settles a relayed rework the user never saw` | `src/hirearchy/services/tests` |
| D2 | `fix(reflection): the deliverable note names the delivery a later relayed rework changed` | `src/hirearchy/reflection/tests src/hirearchy/progress/tests src/hirearchy/mcp_server/tests` |
| D3 | `fix(services): a rework delegation finds its tier through the run's batch when the revised task has no trace` (+ the two s3 replays) | `src/hirearchy/services/tests src/hirearchy/dispatch/tests tests/e2e/test_org_growth_0a3.py` |
| D4 | `docs(skill): root records the user's keep-as-is as their accept` | `src/hirearchy/skill/tests src/hirearchy/blueprint/tests/test_round_f_guidance.py` |
| E1 | `docs: README and ARCHITECTURE for phase 0a.3` (README gains `## Org growth: phase 0a.3` after the 0a.2 section, and lines 248 and 279 follow 5.2; ARCHITECTURE 3.8, 3.21, 3.22, 3.29 and the Protocol sentence: 0a.3 adds `CaseAllowance`, `RuleServiceRequester` takes seven collaborators, `ProcessSpawner.spawn_detached` returns a pid, `StartupWatch` takes a pid, the private `RunCounter` and `BudgetPlanning` gain `stamps` and `client_round`) | `src/hirearchy/blueprint/tests/test_round_g_assistant.py src/hirearchy/blueprint/tests/test_round_f_guidance.py src/hirearchy/blueprint/tests/test_examples.py src/hirearchy/skill/tests tests/architecture` |

**Final validation** (fail-closed): `scripts/check.sh` once on the branch head; the Linux run of `tests/e2e/test_scheduler_detach.py` (6.4) on
the branch head, recorded in `.agents/tasks/verification.md` with its command, image digest and result line, or the owner's recorded
`warning` answer; SKILL.md at 125 lines or fewer and `ROOT_INSTRUCTIONS` under its cap at the reference path; every regenerated golden named
in its commit with its count, and the total (24 distinct files) stated.

Sizes (production lines, estimates): A about 260, B about 60, C about 110, D about 60. FEATs: A (A1-A5), B (B1-B3), C (C1), D (D1-D4, E1).

**Testability.** Unit: the pure functions, the ceiling and the overlap (fs worlds with written run logs and results), the request default over
`FixedAllowance`, the step, the CLI command over `FakeSteps`, the blueprint numbers and texts, the watch over `FakeProcessTable`, the finding
walk over fake checked versions, the tier over the memory world. Contract suites: `CaseAllowance` (fake and reflection), `ProcessSpawner` (real
and fake), `DeliverableChecks`, `ServiceSteps`, `ReworkContext`. Integration: the fs worlds with real git (7.2), the in-process MCP server
and CLI over a real org (4.5). End to end: the four E5 replays and the tree-kill test (macOS, and Linux in a container). Manual, never in CI:
the kiro-cli reproduction.

## 15. Deviations from e5-decision.md and e5-gate.md, with reasons

1. **Top-ups are read by the highest ceiling.** A hand-down approves only what it hands beyond what was still committed. On E5's files a legacy
   explicit budget meant as "N more" reads as fewer approved runs (s2: 14, the gate's reading is 17), and the old default (the contract's 12
   again) reads as approved (s1: 17, the user approved 12 and then about 15). The files hold no record of the user's words; this is the only
   reading that is derivable and lets the new default hand down no run the user did not approve, within the two declared limits of 4.3. The
   replays still show no "exceeds".
2. **The default is capped at the contract's budget** (`min(left, contract)`). A rework never gets more than a fresh request would; the rest of
   a larger approval stays approved for later.
3. **With nothing left, the rework is sent with 1 run.** The decision says the rework is handed what is left; when nothing is left, that is 0,
   and a task cannot carry 0 runs. 1 run is the minimum that lets the owner read the rework; the reply then says nothing else is left and names
   the top-up (`TOPUP`, "the reply says so and names the top-up"), and nothing is refused (the gate: "none of these adds a refusal"). Its cost:
   the approval grows by that 1 run (4.3 limit 1).
4. **The approved number is not in the head of the sentence.** It is in the overspend sentence and in the top-up advice, where root acts on
   it. The decision's form for the head ("N runs used: U by the user's requests, R by your relayed rework") does not include it, and on legacy
   chains (deviation 1) it would put a number in root's mouth that the user did not say.
5. **The head keeps today's text when the chain has no relayed rework, and while its relayed reworks have used no run** (with
   `RELAYED_NONE_YET` then); the old overspend sentence is kept when the approval equals the contract's budget and no task is relayed. Both are
   then exactly the new rule's meaning, no "0 by your relayed rework" is printed, and the golden and test churn stays where the meaning changed.
6. **The client round is "1, plus 2 per agent below the owner"**, SKILL.md's existing rule, and not the estimate's rework sum plus 1. One
   formula serves the plan (blueprint) and the reply (reflection), which cannot share the template model. For E5's team both give 5; for the
   template teams it gives 7 instead of 6.
7. **The templates' budgets follow the new suggestion, and two files beyond the gate's code sites change** (`blueprint/_details.py`, the
   services header; `blueprint/_example_texts.py`, `SERVICE_BUDGETS` and the template comment). The decision's "larger suggested budget per
   request" is the template's number for most users, who start from `blueprint_example(kind, service=True)`; leaving the templates at today's
   numbers would make every shipped service plan warn against its own budget. Consequence: each template's request costs up to 2-3 more runs
   (22 -> 24, 19 -> 22, 23 -> 25, 23 -> 25), which the user may refuse, and the golden count is 24, not about 19 (section 12).
8. **The `budget-tight` threshold is `max(ceil(estimate * 1.10), estimate + round)`**, so no warning of today disappears.
9. **The startup error no longer names the exit code.** The scheduler is not this process's child, so its code is unknowable; the log tail
   still shows why, and the exit marker decides "it exited by itself".
10. **`ChildRegistry` is kept**, though nothing is adopted any more. Removing it is a behaviour-free refactor across `daemon` and `app`; it is
    backlogged.
11. **The launcher's pid comes from the pid file once it names the pid the intermediate reported.** Reading the pid file alone would accept
    a stale file of a dead scheduler and could not tell an exit at once from a slow start.
12. **`RETIRE_UNRATED` is not changed** (F-E5-4 names P2-UNRATED only); the same sentence fits it (backlog).
13. **F-E5-5 covers the file equal to a delivery.** A file equal to no checked version still "differs" from the newest pair, which can be a
    relayed rework's (E5 s3's memo 1, the writer's unreviewed rework); naming the newest delivery that is not relayed is backlogged.
14. **F-E5-7 is fixed at the tier lookup, not at the trace stamp**, with the stamper's own `batch` expression. `traces` is not a dependency of
    `services`, and the stamp rule serves every message.
15. **Correction of the brief:** `status` embeds no case total (4.4); it changes only through the deliverable note.
16. **Beyond 0b 4.2's two names**, 0a.3 adds `Case.relayed_returned`, `relayed_overlap`, `user_granted`, `user_ceiling`, and the pure
    `user_cost`, `user_committed` and `user_approved`: the user's spend needs the relayed tasks' returns, the warning needs the user's approval,
    and the overlap keeps 0b's send-time split from printing a false "exceeds". 0b reuses them (4.9).
17. **An agent client's case keeps today's text.** The decision speaks of the user's approval, which exists only for a human client; an agent's
    service rework can still be `relayed` (it inherits its tier, `dispatch/_sender.py:provenance_source`), and telling an agent that its
    inherited rework is "your own spend, not the user's" would be wrong.
18. **The CLI prints the rework step.** The decision's "the reply says so and names the top-up" holds on every surface that sends a human
    rework, and the CLI stamps `source="human"` on every `--revises`. The CLI's request output for a rework therefore gains a line (the top-up,
    or the client questions of a relayed rework); a fresh request's output is unchanged.

## 16. What E6 must check

The changed texts are pinned by the exact strings of sections 4.4, 4.5, 5.2, 7.1, 7.2 and 8; E6's protocol amendment cites them, and its new
budget estimate is the plan's number of 5.1.
1. **Deterministic, at the merged sha:** the replays `test_e5_s1_t6_...`, `test_e5_s2_t5_...`, both `test_e5_s3_...` and
   `tests/e2e/test_scheduler_detach.py` pass (the decision's replays of s1 T6 for A and of the s3 kill for C), the latter on macOS and Linux.
2. **A, per stream:** every `case total:` line whose chain holds a relayed rework names the relayed runs apart, or says the relayed rework has
   used no run yet; no "tell the user" fires on relayed runs alone; the turns in which the assistant asked the user to fund runs of its own
   relayed rework (E5 s1: 1; target 0); the turns in which it reported relayed runs as its own; chains with an overlapped relayed task (4.8)
   and chains whose window reopened (4.3 limit 2), with what the sentence said on them and whether it said "exceeds".
3. **A, the default:** root's human reworks sent without `budget`, with the budget each got and `left` at that moment; those sent with 1 run
   because nothing was left, and what followed; `TOPUP` replies, and whether the assistant asked the user with that number in the same turn;
   grants after a yes; on the CLI, the same if any stream uses it.
4. **B:** the per-request budget each plan suggested and each stream ran with; whether the plan warned, and whether the assistant offered the
   plan's number at plan time (E5 0 of 3, E4 3 of 3) and what the user answered; spend requests per memo and the turns they took.
5. **C:** schedulers still running when a turn ended (E5 1 of 16), and for each its `scheduler.exit`; runs in flight at a turn's end and their
   `run.end`; any `run.orphan` (E5 1). Every `scheduler.start` has a `scheduler.exit` by the stream's end. On a Linux harness, whether a
   subreaper is an ancestor of root's MCP server (6.3's declared limit).
6. **F-E5-4:** relayed verdicts the assistant recorded before an admitted `define_service`, and P2-UNRATED refusals per relayed rework (E5:
   1 each, 3 of 3).
7. **F-E5-5:** after each relayed rework, the deliverable notes: `relayed` lines naming the delivered task, and `differs` lines naming a relayed
   task for a file the user has (E5: 16; target 0 when the file equals a delivery).
8. **F-E5-7:** rework delegations made inside a human rework that carry `source: human`, of all such delegations (E5 9 of 11; target all),
   noting those whose revised task had no trace and whether the run's batch held a task or only results.
9. **L-ASIS:** keep-as-is answers recorded as a human-tier accept on the kept version's task (E5 0 of 3).
10. **Unchanged guarantees:** P1, P2, P3 and P4 measurements as in E5 (10.5), so that 0a.3 shows no regression in what E5 found working.
11. **Models:** every seat on claude-sonnet-5.5 at high effort, as in E5.

## 17. Out of scope, declared limits, backlog and risks

Out of scope: proposal D (rejected, D-E5-4); a credit for a run the product lost (deferred, D-E5-3); everything of 0b except what 4.9 lists;
F-E5-6 (no change recommended); F-E5-8 (no product guard).

Declared limits (each stated where it arises, and pinned by a test where one can show it):
1. With nothing left, the default's 1 run raises the approval by 1, by more when an attribution limit had made the user's committed runs
   exceed the approval; the files cannot tell it from an explicit `budget=1` (4.3 limit 1; `test_cases.py`).
2. The case window reopens when a later task joins the chain: another case's runs between the chain's last final result and the rework count
   as the user's and as approved, and the other case's later runs keep counting in this case, as today's `case.runs` and today's sentence
   already do, which can make the overspend sentence fire (4.3 limit 2; `test_cases.py`).
3. Overlapping intervals: an overlapped relayed rework's later runs count as the user's in the head and in `user_committed` (so the default
   can hand down less and `TOPUP` can ask for more than a split by task would); the overspend sentence removes up to `relayed_overlap` of them,
   which can also hide an overrun of that size. The reverse direction is not corrected: a human rework overlapped by a relayed one moves user
   runs into "R by your relayed rework", and `RELAYED_SPEND` then calls them root's (4.8).
4. F-E5-7's lookup uses the stamper's batch rule only; its open-task rule can stamp the rework with another trace when the batch holds only
   messages of another case (7.3).
5. On Linux, a subreaper ancestor of root's MCP server adopts the scheduler (6.3).

Backlog: remove `ChildRegistry` and the `Children` port (deviation 10); the same relayed-verdict sentence in `RETIRE_UNRATED` (12); a `differs`
line that names the newest delivery that is not relayed (13); the ambiguous trace stamp of a delegation while the agent holds a blocked task
of another case (14), or pass the rework's own trace to `ReworkContext.fields_for`; the case window that reopens when a later task joins the
chain (limit 2; 0b's `cut` covers the other direction); a split of relayed runs by task rather than by send time (limit 3); README's
"Services and reflection" wording of the case total, if E6 shows the assistant misreads it.

Risks: the `TOPUP` advice and the plan's number still act through what the assistant says and the user accepts (LLM behaviour, measured by E6
items 3 and 4); a lead that keeps unreturned runs inflates `user_committed` and so shrinks `left` (conservative); the larger template budgets
cost the user up to 3 more runs per request when unspent runs do not come back; the reproduction could show another kill mechanism or a
kiro-cli that ignores `KIRO_HOME` (6.1's stop conditions).

## Appendix A. Review resolutions

### A.1 Design review of revision 1 (21 findings: 3 HIGH, 8 MEDIUM, 10 LOW), all addressed

| # | Sev. | Finding | Resolution |
|---|---|---|---|
| 1 | HIGH | `NO_RUNS_LEFT` is a new refusal | Addressed. The refusal, its tests, its error row and the old Deviation 3 are gone. With nothing left the rework is sent with 1 run and `TOPUP` names the shortfall, with the no-number wording when nothing is spare (4.5); 4.8, 9, 11 I4, 16 item 3, Deviation 3 and declared limit 1 restate it; `test_request.py` pins "`left <= 0` sends 1 run". |
| 2 | HIGH | F-E5-7 fix filtered `inflight` to tasks | Addressed. `_batch_trace` is the stamper's expression over every `inflight` message (7.3); the caa9 replay (`cut` `20261024T043231631185`, `inflight` d2ef, `fields_for(... 16f9) == {"source": "human"}`) and the unit case "the batch holds only a result of trace B" are added. Verified in `EV5/s3/events`: caa9's run batch was the writer's result d2ef, trace dd39. |
| 3 | HIGH | The kiro-cli reproduction reads and writes `~/.kiro` | Addressed (6.1): every real kiro-cli call has `KIRO_HOME=$SB/kiro-home`; a `whoami` stop condition (owner decides on `KIRO_API_KEY`, no fallback); the profile lives in `$SB/kiro-home/agents/`; the session-record check under `$SB/kiro-home`; the sentence about kiro-cli's own write is deleted. One change to the proposed fix: V3 rejects `allowedTools` (`kiro/_profile_document.py`, `test_profile_document_v3.py::test_no_legacy_keys`), so the one-tool restriction is a V3 permission rule (`hirearchy/start`) with `"tools": ["@hirearchy"]`, the product's own shape; the MCP server also gets `HOME=$SB/home`, so even a stray `whoami` cannot read the user's skill. |
| 4 | MEDIUM | "0 by your relayed rework" | Addressed: head form 1 and `RELAYED_NONE_YET` while the relayed runs are 0; form 2 only from 1 run on (4.4 table, 4.8); tests in `test_reports.py`. |
| 5 | MEDIUM | Overlapping intervals | Addressed: `Case.relayed_overlap` (named so because 0b's `Case.cut` means something else) and `user_cost = max(0, user_spend - relayed_overlap)`; both overspend sentences compare `user_cost` with the approval (4.2-4.4); the funds of the overlapped task include the client's grants in its interval, and what its result returned is subtracted. Both directions are declared (17 limit 3); the two tests of the finding are in 4.7. |
| 6 | MEDIUM | "A default rework raises no ceiling" is false when the window reopens | Addressed: 4.3 states the exact limit; 17 declares it with the backlog item; `test_cases.py` pins `user_ceiling == approved + k`, `user_spend` including `k`, and no "exceeds". |
| 7 | MEDIUM | Agent clients unspecified; "grant: a note root sent" | Addressed, with a correction of the premise: an agent's service rework can carry `source: relayed` (inherited tier, `dispatch/_sender.py`), so the fix is not only `user_ceiling = user_granted = 0` for agents (done) but also an agent branch in `case_total` that prints today's text byte for byte (4.4, Deviation 17, I6). Section 3 now says "a note the case's client sent". Tests in `test_reports.py` and `test_cases.py`. |
| 8 | MEDIUM | CLI human rework without `--budget` gets less with no advice | Addressed: the CLI prints `rework_step` after its line under `_step`'s error rule; `TOPUP` carries its CLI form `(CLI: hirearchy send {owner} "<why>" --budget {grant})` (4.5); CLI command test and a real-org CLI test (4.7); `SRC/cli/tests/expected/request.txt` stays (a fresh request). Placed in A5 with the step it prints. |
| 9 | MEDIUM | Deviation 7 narrowed D-E5-2 | Addressed with option (a): the default is `max(ceil(est * 1.25), est + r)` within the cap (5.1, 5.2), and the shipped templates follow (24, 22, 25, 25), pinned by a test (I8). `budget-low` reads the unchanged estimate, so no plan is newly refused (5.3). New Deviation 7 records the two extra files and the cost; the golden count is restated (24). |
| 10 | MEDIUM | Rule B list incomplete | Addressed: Rule B is a grep plus a reading rule, re-run at A4 and recorded in its commit body; `test_no_bypass_0a2.py:503` (3 surfaces) is in the list, and stays as it is because it asserts only that the rework is sent (13). Applying the rule also removed two sites revision 1 had listed (`test_contract_service_commands.py:715`, `reflection/tests/test_steps.py:222`): their worlds wire `FixedAllowance({})`, so A4 does not touch them; the second is an A5 site. |
| 11 | MEDIUM | No Linux run planned | Addressed: a Linux container run of the tree-kill test (read-only mount, copied inside, so the macOS `.venv` is untouched) is required evidence at C2 and in the final validation; a `warning` to the owner if no container runtime works (6.4, 14). The branch is never pushed, so the CI job cannot run before the merge. The subreaper sentence is in 6.4. |
| 12 | LOW | `_detach.py` imported by the architecture tests | Addressed: the module ends with the `__main__` guard; "never imported by product code" (6.2). |
| 13 | LOW | No `RunCounter` fakes | Addressed: 4.6 says none exists or is added; `test_run_counter.py` covers `LogRunCounter.stamps`. |
| 14 | LOW | `await_start` narrowed the clean-exit rule | Addressed: any non-empty marker with a gone process is a clean exit (6.2 step 2); tests for `FINISHED` and a grace reason. |
| 15 | LOW | `daemon/tests/test_children.py` unlisted | Addressed: it builds handles with `table.spawn(...)` (6.2) and is in 6.4's list. |
| 16 | LOW | s2 #21 cut not given as a stamp | Addressed: `cut = "20261024T034308207974"` (4.7). |
| 17 | LOW | 0b I4 and `runs=False` | Addressed: 4.1 and 4.9 restate I4 as one comparison (`user_cost` against `user_approved`) for 0b's amendment, and give the `runs=False` meaning of every new field. |
| 18 | LOW | `Allowance.below` unused | Addressed, further: with the refusal gone, no field of `Allowance` but `left` was used, so the dataclass is removed and the port is `CaseAllowance.left(owner, service, revises)`, which returns an `int` or None (4.5). |
| 19 | LOW | Deliverable note, folder with only relayed findings | Addressed: no block heading; each `relayed` finding is its own line, in the order of the findings (7.2); a test in `test_deliverables_note.py`. |
| 20 | LOW | Zombie scheduler counts as gone | Addressed: `ps -o stat=` prints nothing or a state starting with `Z` (6.4 step 5, and 6.1 step 8). |
| 21 | LOW | Explicit-budget validation position; `rework_step` docstring | Addressed: the explicit check stays before `revises`, only the default moves after `_base` (4.5, 10); the docstring text is given (4.5). |

### A.2 Design review of revision 2 (13 findings: 3 MEDIUM, 10 LOW), binding amendments

The review of revision 2 ended with CHANGES_REQUESTED. The manager closed the design loop by approving revision 2 as amended below
(`.agents/tasks/manager-decision-design-loop.md`). These amendments bind and override the body where the two differ. `{n}` is a number, and
`{s}`, `{has}`, `{it}`, `{its}`, `{Its}` follow the rule of 4.4 (one id: "", "has", "it", "its", "Its"; several: "s", "have", "they", "their",
"Their").

| # | Sev. | Finding | Binding resolution |
|---|---|---|---|
| DR-0a3-1 | MEDIUM | `RELAYED_NONE_YET` ("has used no run yet") is false when the relayed rework's runs fell in a later user interval | `RELAYED_NONE_YET` is printed only when `relayed_overlap == 0`. When `relayed_runs == 0` and `relayed_overlap > 0`, `case_total` prints head form 1 and the new `RELAYED_UNSPLIT`. **P-1:** `Case.unsplit_runs: int = 0` is the charged runs in the intervals of the user tasks after the first relayed task whose term of `relayed_overlap` is above 0 (0 when `relayed_overlap` is 0); it is computed in `_cases.py` in the same loop as `relayed_overlap`: keep the indices `k` whose overlap term is positive, `first = min(...)`, and count the stamps of `charged` that lie in `bounds[j]` for some `j > first` with `tasks[j].source != "relayed"`; on 0b's `runs=False` path it is 0. **P-2, the text of `RELAYED_UNSPLIT`** (`{n}` is `c.unsplit_runs`): `Your relayed rework{s} {ids} {has} no run counted apart: a request of the user's followed before {it} finished, so {its} runs could not be split from the user's interval, which holds {n} run(s) since then, all counted with the user's requests. {Its} runs are your own spend, not the user's: report them to the user as yours, and never ask the user to fund them.` The print rule for a human client with relayed task(s): `relayed_runs == 0` and `relayed_overlap == 0`: form 1 and `RELAYED_NONE_YET`; `relayed_runs == 0` and `relayed_overlap > 0`: form 1 and `RELAYED_UNSPLIT`; `relayed_runs >= 1`: form 2 and `RELAYED_SPEND`. The overspend sentence is unchanged (`OVER_APPROVED` when `U > A`). 4.4's table row for `relayed_runs == 0` and 4.8's row for `RELAYED_NONE_YET` read this way. Tests: `test_cases.py` (`unsplit_runs`), and three cases in `test_reports.py` (R of budget 6 followed by H before any run, 4 runs in H's interval, no result for R: form 1 and `RELAYED_UNSPLIT` with "4 run(s)", never "has used no run yet"; the same chain with R's result returning 6: `RELAYED_NONE_YET`; R alone and just sent: `RELAYED_NONE_YET`). |
| DR-0a3-2 | MEDIUM | `examples/blueprint-service.yaml` sets `budget: 22` itself and is not a listed site | The file is a site of B. Line 13 becomes `  budget_runs: 25   # the user's cap for ONE request; the service below asks for 24`; line 46 becomes `    budget: 24                         # runs per request; leave it out for the plan's number (the estimate + 25%, or + one client round when more)`. The word "cheaper" stays out of the comments (`test_models.py:156-161` scans `examples/*.yaml`). `examples/blueprint-service.yaml` gets no `budget-tight`; its goldens (`plans/example_blueprint-service.txt`, `charters/apply_service_example.md`) show 24; `test_examples.py:233` reads `s.budget == 24` (line 226 passes unchanged) and line 160 replaces `budget: 24` by `budget: 23`. README line 279's sample (`budget: 22`) is an explicit value and may stay. Commits: A0 (this text), B1. |
| DR-0a3-3 | MEDIUM | The reproduction's after-the-fix step calls `hirearchy stop`, which does not exist | The step stops the scheduler through the control the MCP `stop` tool uses (`SchedulerControl.stop(self, wait: float = 15.0) -> str`, `SRC/daemon/api.py:71`): `HIREARCHY_STATE_DIR=$SB/kiro-state $WT/.venv/bin/python -c 'import sys; from hirearchy.app import Org; print(Org(sys.argv[1]).runtime.scheduler_control.stop())' "$SB/org"`. It must record `run.end` (`killed: true`) and `scheduler.exit` (`stopped by SIGTERM`). Clean-up (6.1 step 9) runs after it. Commits: A0 (this text), C0, C2. |
| DR-0a3-4 | LOW | The profile prompt does not say that the hirearchy tools are deferred | The profile's `"prompt"` and the chat input of 6.1 step 6 are both exactly: `The hirearchy tools are deferred: load them with tool_load (tool_ids ["hirearchy::*"]), then call tool_call with tool_id "hirearchy::start" once, with its defaults, and reply with its result only.` Loading all is harmless: the permission rule allows only `hirearchy/start`. Commits: A0 (this text), C0, C2. |
| DR-0a3-5 | LOW | Sites that the commits change are not listed | Added to the commits that change them. B: `blueprint/_protocols.py` (`BudgetPlanning.service_budget` gains `*, round_runs: int` and the 5.2 docstring); `blueprint/tests/test_services.py:99` (`svc_bp` runs on `mutate(svc_bp, lambda b: b["services"][0].update(budget=24))`, the docstring names D-E5-2) and `:487` (`== 24`); `blueprint/tests/test_budget_planner.py:80` (`"b": 24`). C1: the users of the handle that `spawn_detached` returns build it with `table.spawn(...)` or work on the returned pid (`processes/tests/test_fake_process_table.py:109`, `daemon/tests/test_signal_stopper.py:27`, `daemon/tests/test_fakes.py:155, 166`, `daemon/tests/test_pidfile_status.py:109`, `daemon/tests/test_startup_watch.py:43`, `daemon/tests/test_detached_launcher.py:68-71`, `processes/testing.py`, `daemon/testing.py`, `scheduler/testing.py`). D1: `tests/e2e/test_no_bypass_0a2.py:243` asserts the full new P2-UNRATED text and `tests/e2e/test_org_growth_0a2.py:123` its new prefix; both files go into D1's TARGETS (`test_no_bypass_0a2.py:298` and `test_contract_service_commands.py:463` are `RETIRE_UNRATED` and stay). |
| DR-0a3-6 | LOW | The F-E5-5 walk's result shape and the `_entry` branch are not specified | `_folder_rule` and `_file_rule` return `tuple[str, _Pair \| None, tuple[str, ...]]`: the kind, the pair (for `relayed`, the delivery's pair) and the relayed task ids, oldest first (`()` otherwise). `_entry` unpacks the 3-tuple; for `kind == "relayed"` it returns `[]` when `self._settled(entry.mtime_us, [pair.case] if pair.case else [])`, else `[DeliverableFinding(folder, group.services, entry.name, "relayed", task=pair.task.id, relayed=ids, file=single)]`. The `kind` comment in `api.py` gains `relayed`. `_entry` is a site of 7.2. Commit: D2. |
| DR-0a3-7 | LOW | What the case total says after a reopened window is not stated | Stated in 4.8 (a new row), in 17 limit 2 ("can make the overspend sentence fire") and in 16 item 2 ("and whether it said 'exceeds'"). After the reopened window of 4.3 limit 2, `OVER_APPROVED` can fire on another request's later runs: the existing window rule, which is also 0b's, counts them as the user's and not as approved. Not corrected in 0a.3. A test in `test_reports.py` pins it (docstring names declared limit 2 and DR-0a3-7). Commits: A0 (doc), A3 (test). |
| DR-0a3-8 | LOW | SKILL.md's delivery report folds root's relayed runs into the total | SKILL.md line 97 becomes exactly `   (met / unmet), then runs used of planned (with reworks, the case total: "19 runs of the 15 approved per request", your relayed runs apart, as yours). Nothing else.` The needle of `test_round_g_assistant.py:38` is kept; the new needle `your relayed runs apart, as yours` goes in `SRC/skill/tests/test_skill_org_growth.py`; the file stays at 125 lines. Commit: A6. |
| DR-0a3-9 | LOW | A3's progress golden is given as "form 2 ... or form 1" | The scenario (`progress/tests/_scenario.py:119-121`) has one run in the relayed interval, so form 2 applies. The case total in `SRC/progress/tests/expected/all.txt` line 2 and `task_1_weekly-brief.txt` is exactly `case total: 3 runs used: 2 by the user's requests, 1 by your relayed rework 20260101T120440001000-root-001e; 16 handed down (contract: 10 per request). The runs of your relayed rework are your own spend, not the user's: report them to the user as yours, and never ask the user to fund them. (task 20260101T120200002000-root-0015)`, with the line's prefix unchanged; line 3 of `all.txt` and `task_2_weekly-brief.txt` get the same case-total text. Commit: A3. |
| DR-0a3-10 | LOW | 4.3 cites the wrong SKILL.md rule | 4.3 cites the budget-request bullet of SKILL.md (lines 69-72: before a rework that would take the case past the approved per-request budget, ask the user, with the number), not "step 4". Done in the body by A0. |
| DR-0a3-11 | LOW | `topped` calls a head budget above the contract a top-up | `topped` is `, plus {A - B} approved beyond it` when `A > B`, else empty. `OVER_APPROVED` therefore reads `The user's requests now cost {U} runs, more than the {A} the user approved for this case (contract: {B} per request{topped}): tell the user.` Tests: a head with an explicit budget of 15 on a contract of 12, then an overspend (`, plus 3 approved beyond it`). Commits: A0 (this text), A3. |
| DR-0a3-12 | LOW | `case_spend`'s docstring becomes untrue | Option (a): the body stays byte for byte and the docstring becomes **P-3**, exactly: `"""The runs a case costs against its contract's per-request budget (pure): the runs its team used, plus, while it is not finished (open or blocked), the runs handed down for it that were neither used nor returned (the team may still spend them). It is the case's total, the user's requests and root's relayed reworks together: ``case_total`` warns on it for an agent client's case, and D-E5-6 has Phase 0b's cost alarm split it (``user_cost`` against ``user_approved``, the comparison ``case_total`` makes for a human client's case)."""` 4.1's "word for word" holds for the body. Commits: A0 (this text), A2. |
| DR-0a3-13 | LOW | The CLI prints root's advice text to the user | Deliberate: the CLI prints the same root-addressed `TOPUP` and `REWORK` texts as root's MCP reply. The CLI's user is root (the person at the CLI plays the assistant's part), and every text carries its CLI form. Stated in 4.5 ("The CLI"). `test_commands_services.py` asserts that the CLI line equals `rework_step(msg)`. Commits: A0 (doc), A5. |

**Plan-level refinements** (the plan, `.agents/tasks/plan.md` section 2, settles these where the amendments leave a choice):
- **P-4.** The reflection re-run of the `CaseAllowance` suite is `SRC/reflection/tests/test_case_allowance.py`, not `test_contract_case_allowance.py`,
  following `test_case_judged_versions.py`. R8 needs only `SRC/services/tests/test_contract_case_allowance.py`.
- **P-5.** Root's `request` docstring changes in two commits, so that each commit documents what it ships: A4 changes the `budget:` line and the
  case-total reply sentence, without the top-up clause; A5 adds `, and names the top-up to ask for when a rework the user asked for gets less
  than a round of the team needs`. The three MCP surface goldens are regenerated in A4 and again in A5; the distinct golden files stay 24.
- **P-6.** Replay-kit timing: `tests/testkit/e5_replay.py` is created in A3 without `inflight`, and D3 adds the `inflight=` keyword, which only the
  s3 replays use. Each version gets kit tests in `tests/meta/test_e5_replay_kit.py`, the pattern of `tests/meta/test_e4_replay_kit.py`.
- **P-7.** The Linux run (6.4): first the design's command, which mounts the worktree read-only; when `/w` is empty inside the container
  (podman machine shares `/Users` and `/private`, not always `/Volumes`), mount a `git archive HEAD` copy under `/tmp` read-only instead. The
  evidence records which one ran. Both leave the worktree untouched and test the committed HEAD.
