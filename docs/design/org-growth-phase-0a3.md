# Org growth, Phase 0a.3: the batch after the E5 FAIL (technical design)

Status: design, revision 1. Branch `feat/org-growth-phase-0a3` off `main` `3cd28b3` (the E5 study commit; product code identical to `6618c0d`);
worktree `/Volumes/workspace/hirearchy/.worktrees/org-growth-0a3`. Baseline at `3cd28b3`: `skills/hirearchy/SKILL.md` 125 lines;
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
   of the case's approved runs; when that is too little, the reply names the top-up to ask for. `Case.relayed_runs` (0b 4.2's definition) and
   `user_spend`, the sibling of `case_spend`, are built here; 0b reuses them.
2. **B (D-E5-2): the plan budget.** For a service (whose client is always the human, root), the plan's Budget line and the `budget-tight`
   warning name the runs of one round of the client's questions or a rejection (5 for E5's team) and the number that covers it (16).
   SKILL.md step 6 tells the assistant to offer that number. `budget-low` is unchanged.
3. **C (D-E5-3): the scheduler outlives the chat call.** First a reproduction with the real kiro-cli 2.33.0 in a `/tmp` sandbox. Then
   `spawn_detached` starts the scheduler through an intermediate process that exits at once, so the scheduler is re-parented and is no
   descendant of root's MCP server; the launcher takes its pid from the scheduler's pid file.
4. **D-E5-5:** the P2-UNRATED text (F-E5-4); the deliverable note after a relayed rework (F-E5-5); the human tier of rework delegations whose
   revised task carries no trace (F-E5-7, a defect: section 7.3); one SKILL.md line for a version the user keeps as it is (L-ASIS).

Everything stays derived: no ledger, no new file kind, no message field, no event field.

## 2. Technology stack (locked)

Python 3.11, the existing packages only (`mcp`/FastMCP, PyYAML; Textual untouched), the standard library (`subprocess`, `os`, `sys` for the
detach), `git` (already required), uv, pytest, `mypy==2.4.0 --strict`, `import-linter==2.15`, `scripts/static_checks.py`, `scripts/check.sh`.
No new runtime dependency, no new package, no new dependency edge between packages: the one cross-package need (services asks reflection for
what is left of a case) is a consumer-owned port in `services/api.py` implemented by `reflection`, the pattern of `JudgedVersions`. Strict TDD
(R11) under the owner's test policy (section 14). kiro-cli 2.33.0 is used only for the manual reproduction of 6.1, never by a test.

## 3. Shared definitions (each defined once)

| Name | Home | Definition |
|---|---|---|
| user task | `reflection` | A task of a case's chain whose `source` is not `relayed`: the head, a `human` rework, or a rework without `source` (sent before 0a). |
| relayed interval | `reflection._cases` | For the chain's task `t` and its successor `next`: the stamps `s` with `t.id[:21] <= s < next.id[:21]`; the last task's interval ends at the window's end, inclusive (0b 4.2). A user interval is the interval of a user task. |
| grant | `reflection._cases` | A note root sent with `budget > 0` to an agent of the owner's subtree, with an id inside the case's run window (progress's grant rule, `progress/_counts.py:LogRunCounts._window`). A **user grant** lies in a user interval. |
| hand-down | `reflection._cases` | A user task (amount: its `budget`) or a user grant (amount: its `budget`). |
| committed at `h` | `reflection._cases` | For a hand-down `h`: the user's charged runs with stamps before `h.id[:21]`, plus what the user tasks and user grants before `h` handed down that those runs did not use and their results (with ids before `h`) did not return, at least 0. |
| ceiling of `h` | `reflection._cases` | committed at `h` plus `h`'s amount: the most the user's requests could cost right after `h`. |
| user's approved runs | `reflection.user_approved` | `max(contract budget, Case.user_ceiling)` (4.3). |
| client round | `reflection._allowance.client_round`, `blueprint._budgeting.BudgetPlanner.client_round` | The runs one round of the client's questions or a rejection takes: the owner reads the client's rework (1), and each agent below the owner gets one rework or re-check delegation of about 2 runs (its run and the run of its manager that processes the result): `1 + 2 * (agents below the owner)`. E5's team (lead, writer, reviewer): 5. It is SKILL.md's "about 2 runs per delegation it requires + 1" with every agent below the owner delegated once. |

## 4. D-E5-1, proposal A: the case total

### 4.1 Decision

Proposal A in full, with its optional part:
- the sentence names the relayed runs apart ("N runs used: U by the user's requests, R by your relayed rework `<id>`"), and still shows the total;
- a separate sentence tells root that the relayed runs are its own spend, to report as such;
- "exceeds ... tell the user" compares the user's spend (`user_spend`) with the user's approved runs (`user_approved`);
- a human rework without `budget` is handed what is left of the approved runs, at most the contract's budget; with 1 or more left but less than
  a client round, the reply names the top-up to ask for; with none left, the request is refused with the same advice (4.5).

`case_spend` stays as it is, word for word: 0b's cost alarm and 0b's invariant I4 read it, and a test pins that `user_spend == case_spend` on
every case without a relayed task.

### 4.2 The data model, in 0b 4.2's form

| Count | Definition | Files | Function |
|---|---|---|---|
| runs | charged run logs of the owner's subtree in the window | `<addr>/runs/*.log` names; credits in each agent's received boxes | `Case.runs` (unchanged; now counted from `RunCounter.stamps`) |
| relayed runs | charged runs whose stamp `s` satisfies `t.id[:21] <= s < next.id[:21]` for a relayed task `t` of the chain (`next` its successor in the chain; the last task's interval ends at the window's end, inclusive) | same | `Case.relayed_runs` (new; 0b 4.2 word for word) |
| relayed returned | the runs the results of the relayed tasks carried back, each at most its own task's budget (the rule of `Case.returned`, restricted to relayed tasks) | client's received boxes (result `budget`) | `Case.relayed_returned` (new) |
| user grants | the budgets of the user grants (section 3) | client's `sent/` (notes) | `Case.user_granted` (new) |
| user ceiling | the highest ceiling over the case's hand-downs (section 3); 0 for a case built by hand | client's `sent/`, received boxes, run log names | `Case.user_ceiling` (new) |
| spend | `case_spend(case)` | as above plus result `budget` headers | unchanged |
| user spend | `case_spend` restricted to the user's requests: the user's charged runs (`runs - relayed_runs`), plus, while the case is not finished (open or blocked), the runs handed down for the user tasks that were neither used by those runs nor returned by those tasks' results (`returned - relayed_returned`) | as spend | `user_spend(case)` (new, pure, `reflection.api`) |
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


def user_committed(case: Case) -> int:
    """What the user's requests used or the team still holds for them, whatever the case's state (pure): what a new rework draws on."""
    runs = case.runs - case.relayed_runs
    budget = sum(t.budget for t in case.tasks if t.source != "relayed") + case.user_granted
    return runs + max(0, budget - runs - (case.returned - case.relayed_returned))


def user_approved(case: Case, budget: int) -> int:
    """The runs the user approved for a case (pure): the contract's per-request ``budget``, raised to the highest ceiling root set for the
    user's requests (``case.user_ceiling``)."""
    return max(budget, case.user_ceiling)
```

### 4.3 Why the approval is the highest ceiling

The files record what root handed down, never what the user said. A rule must therefore read the user's approval from root's hand-downs, and
it must not let the new default hand down more than the user approved. Three readings were compared on E5's chains:

| Reading | s1 T6 (10 user runs) | s2 T5 (14 committed) | A no-budget human rework after 0a.3 |
|---|---|---|---|
| Every human rework's budget and every grant is a top-up | 24: no "exceeds" | 17: no "exceeds" | counts the rework's `left` again: the next default rework is handed runs the user never approved. **Rejected.** |
| Only grants (notes) are top-ups | 12: no "exceeds" | 12: "exceeds" fires on runs Lena funded. **Rejected** (fails s2's T5 line). | correct |
| **The highest ceiling** (chosen) | 17: no "exceeds" | 14: no "exceeds" | correct: a default rework is handed exactly `left`, which raises no ceiling |

The ceiling reading says: a hand-down approves only what it hands beyond what was still committed. A human rework without `budget` is handed
`left = approved - committed`, so its ceiling equals the approval and raises nothing. An explicit `budget` above what is left, or a grant, raises
the approval by exactly the excess: SKILL.md step 4 has root ask the user before it hands down beyond the approved budget, so the product reads
such a hand-down as the user's yes, as it reads `source="human"` as root's word. Taking the highest ceiling (not the latest) keeps a later small
hand-down from lowering the approval.

The computation, in `SRC/reflection/_cases.py:DerivedCaseHistory.cases`, per case, from what the builder already reads (`tasks`, `results`,
`sent`, `team`, the window `start`/`end`) plus one `stamps` call:

```python
stamps = self._counter.stamps(team, start, end)                       # [(stamp, credited)], start = tasks[0].id[:21]
charged = [s for s, credited in stamps if not credited]
bounds = [(t.id[:21], tasks[k + 1].id[:21] if k + 1 < len(tasks) else None) for k, t in enumerate(tasks)]
relayed = [b for t, b in zip(tasks, bounds) if t.source == "relayed"]
def in_relayed(s): return any(lo <= s and (hi is None or s < hi) for lo, hi in relayed)
grants = sorted((m for m in sent if m.type == "note" and m.budget > 0 and m.to in team and m.id[:21] >= start
                 and (end is None or m.id[:21] <= end) and not in_relayed(m.id[:21])), key=lambda m: m.id)
users = [t for t in tasks if t.source != "relayed"]
ceiling = 0
for h in sorted([*users, *grants], key=lambda m: m.id):              # the hand-downs, oldest first
    runs = sum(1 for s in charged if s < h.id[:21] and not in_relayed(s))
    handed = sum(t.budget for t in users if t.id < h.id) + sum(g.budget for g in grants if g.id < h.id)
    back = sum(min(r.budget, t.budget) for t in users if t.id < h.id and (r := results.get(t.id)) is not None and r.id < h.id)
    ceiling = max(ceiling, runs + max(0, handed - runs - back) + h.budget)
```

`Case(..., runs=len(charged), relayed_runs=sum(map(in_relayed, charged)), relayed_returned=<the returned rule over relayed tasks>,
user_granted=sum(g.budget for g in grants), user_ceiling=ceiling)`. `results` is the latest result per task: a task whose latest result came
after `h` counts as not answered at `h` (its budget is still out there), which can only raise a ceiling. The loop is quadratic in the chain's
length, which is a handful of tasks.

**E5's numbers** (from `EV5`, verified against the recorded `case total:` lines):

| Stream, moment | Chain (budget, runs, returned) | runs / relayed / user | ceilings | approved | user spend | "exceeds" |
|---|---|---|---|---|---|---|
| s1 T6 (#28) | f07a (12, 5, 7); aae2 human (12, 5, 7); 963a relayed (6, 5, 1) | 15 / 5 / 10 | 12; 5 + 12 = 17 | 17 | 10 (done) | no (was yes) |
| s2 T5 (#21, right after 6c4f) | ebe2 (12, 9, 3); 6c4f human (5, open) | 9 / 0 / 9 | 12; 9 + 5 = 14 | 14 | 9 + 5 = 14 | no (was yes) |
| s2 T5 (#23, 6c4f done) | the same, 6c4f (5, 5, 0) | 14 / 0 / 14 | 12; 14 | 14 | 14 | no (was yes) |
| s3 final | e268 (12, 9, 3); c209 human (3, blocked); grant 595d (2) in c209's interval; daff relayed (6) | 18 / 5 / 13 | 12; 12; 14 | 14 | 13 | no (was yes) |

s1 reads 17 because E5's aae2 was handed the contract's 12 again by the old default, and the files cannot tell that from an explicit budget;
s2 reads 14 where Lena approved "5 more" (17), because 3 of the 12 were still unused. Neither reading makes "exceeds" fire, and after 0a.3 the
default no longer hands down more than is left, so new chains do not carry either artifact (Deviation 1).

### 4.4 The texts of `case_total` (`SRC/reflection/_reports.py:TextServiceReports.case_total`)

With `c` the case, `B` the current contract's budget, `A = user_approved(c, B)`, `U = user_spend(c)` and `ids` the chain's relayed tasks (oldest
first, joined by `, `; `s` is `"s"` when there are several):

1. Head, **no relayed task** (byte-identical to today): `case total: {c.runs} runs used of {c.budget} handed down (contract: {B} per request)`.
2. Head, **with a relayed task**: `case total: {c.runs} runs used: {c.runs - c.relayed_runs} by the user's requests, {c.relayed_runs} by your
   relayed rework{s} {ids}; {c.budget} handed down (contract: {B} per request)`.
3. When `U > A`:
   - no relayed task and `A == B` (today's case; byte-identical): `This case now exceeds the per-request budget of {B}: tell the user.`
   - otherwise (`OVER_APPROVED`): `The user's requests now cost {U} runs, more than the {A} the user approved for this case (contract: {B} per
     request{topped}): tell the user.` with `topped` = `, plus {A - B} in top-ups` when `A > B`, else empty.
4. When the chain has a relayed task (`RELAYED_SPEND`): `The runs of your relayed rework{s} are your own spend, not the user's: report them to
   the user as yours, and never ask the user to fund them.`

The parts are joined as today: the head, then `. ` and each sentence that applies. E5 s1 T6 becomes:

`case total: 15 runs used: 10 by the user's requests, 5 by your relayed rework 20261024T031317713451-root-963a; 30 handed down (contract: 12 per request). The runs of your relayed rework are your own spend, not the user's: report them to the user as yours, and never ask the user to fund them.`

E5 s2 T5 (#21) becomes `case total: 9 runs used of 17 handed down (contract: 12 per request)` and (#23) `case total: 14 runs used of 17 handed
down (contract: 12 per request)`. The approved number is not in the head: it appears where root needs it, in the overspend sentence and in the
top-up advice of 4.5 (Deviation 4). The sentence is embedded, unchanged in form, by root's `request` reply (`SRC/mcp_server/_tools_services.py:
_requested`) and by every `progress` line of a rework chain (`SRC/progress/_lines.py`, which strips the final `.` and joins with `. `). `status`
embeds no case total (checked: `_tools_status.status` renders the tree, the scheduler line and the P3 note), so `status` changes only through
the deliverable note of 7.2.

`ServiceReports.case_total`'s docstring in `api.py` says so: "...the runs of root's relayed reworks named apart and called root's own spend;
when the user's requests cost more than the user approved (``user_spend`` against ``user_approved``) it adds that the user must be told."

### 4.5 A human rework without `budget`: what is left, and the top-up

**The port** (new, `SRC/services/api.py`, exported; implemented by `reflection`, as `JudgedVersions` is):

```python
@dataclass(frozen=True)
class Allowance:
    """What the user approved for a case and what their requests use or hold (derived; ``reflection`` computes it)."""
    contract: int   # the current contract's budget per request
    approved: int   # the runs the user approved for the case (reflection.user_approved); at least ``contract``
    committed: int  # what the user's requests used or the team still holds for them (reflection.user_committed)
    need: int       # the runs of one client round of the owner's team: 1, plus 2 per agent below the owner
    below: int      # the agents below the owner (the ``need`` reply names them)

    @property
    def left(self) -> int:
        return self.approved - self.committed


@runtime_checkable
class CaseAllowance(Protocol):
    def allowance(self, owner: str, service: str, revises: str) -> Allowance | None:
        """For a rework of ``revises``, a task of a case of ``owner``'s ``service``: what the user approved for the case, what their requests
        used or the team holds, and the runs one client round of the team needs. None when the task is in no case of the service (one sent
        before the service was last defined from scratch) or the service has no contract. ``OrgError``/``OSError`` when a mailbox, a charter
        or a run log directory cannot be read."""
        ...
```

Implementation `SRC/reflection/_allowance.py:CaseAllowanceOf(history: CaseHistory, catalog: ServiceCatalog, agents: AgentDirectory)`:
the case of `history.cases(owner, service)` that holds `revises`, the contract of `catalog.read_contract`, and `client_round(agents, owner) =
1 + 2 * (len(agents.subtree(owner)) - 1)`. The module also holds `client_round` for `_steps.py` (one rule for the request and the reply). The
fake `FixedAllowance(answers: Mapping[str, Allowance | None])` goes in `SRC/services/testing.py` with `IMPLEMENTATIONS[CaseAllowance]`; the
contract suite is `SRC/services/tests/test_contract_case_allowance.py`, re-run from `SRC/reflection/tests/test_contract_case_allowance.py`
over `CaseAllowanceOf` (R8, the pattern of `test_contract_judged_versions.py`).

**The default** (`SRC/services/_request.py:RuleServiceRequester`, 7th collaborator `allowance: CaseAllowance`). The rule lives in `services`
because it is the one layer the MCP tool and the CLI (`hirearchy request --revises`, whose `--source` defaults to `human`) share. The budget
default moves after the `revises` check and after `_base` (P4), so a wrong `revises` or a missing `base` is refused first, as today:

```python
if budget is None:
    budget = self._default_budget(actor, contract, revises, source)

def _default_budget(self, actor, contract, revises, source) -> int:
    if not (actor == ROOT and revises and source == "human"):
        return contract.budget                               # a fresh request, a relayed rework, an agent's request: unchanged
    try:
        allowance = self._allowance.allowance(contract.owner, contract.name, revises)
    except (OrgError, OSError):
        return contract.budget                               # a record that cannot be read: the contract's, as before 0a.3
    if allowance is None:
        return contract.budget
    if allowance.left >= 1:
        return min(allowance.left, contract.budget)          # what is left, never more than a fresh request gets
    raise OrgError(NO_RUNS_LEFT.format(...))
```

The refusal A-NO-RUNS-LEFT (constant `NO_RUNS_LEFT` in `_request.py`):

`refused: the user approved {approved} runs for this case (contract: {contract} per request{topped}) and their requests have used or hold {committed}, so none is left for this rework. A rework of this team needs about {need} (1, plus 2 for each agent below {owner}): ask the user for that many more, with the number; on yes, request it again with budget={need} (CLI: --budget {need}). Nothing was sent.`

`topped` is `, plus {approved - contract} in top-ups` when `approved > contract`. An explicit `budget` is never changed or refused by this rule.

**The top-up advice** (`SRC/reflection/_steps.py:TextServiceSteps.rework_step`, which root's `request` reply already appends after the case
total for every rework root sends). Today it returns `""` for a human rework; it gains this branch for `task.source == "human"` with
`task.service` and `task.revises`:

```python
case, contract = self._history.case_of(task), self._catalog.read_contract(task.to, task.service)
if case is None or contract is None: return ""
need = client_round(self._agents, task.to)
if task.budget >= need: return ""
approved = user_approved(case, contract.budget)
spare = max(0, approved - user_committed(case))      # the case now holds this rework's budget too
ask = need - task.budget - spare
if ask <= 0: return ""                               # root handed less than what is left: it can grant the rest without asking
return TOPUP.format(...)
```

`TOPUP`: `This rework has {budget} run(s), and a rework of this team needs about {need} (1, plus 2 for each agent below {owner}). {left} Ask the user now for {ask} more run(s), with that number; on yes, grant {grant}: send(to="{owner}", budget={grant}, body=<why>).`
with `{left}` = `Nothing else is left of the {approved} runs the user approved for this case.` when `spare == 0`, else `{spare} more of the
{approved} runs the user approved for this case are left.`, and `grant = need - budget`. The grant is a root note to the owner inside the human
rework's interval, so it is a user grant and raises the ceiling by exactly `grant`. The relayed branch (the client questions, 0a.1) is unchanged.
The `ServiceSteps.rework_step` docstring names both branches.

Example (a new-flow s1 after the relayed rework, no grant): approved 12, committed 10, so a Summary rework without `budget` is handed 2 and the
reply says `This rework has 2 run(s), and a rework of this team needs about 5 (1, plus 2 for each agent below lead). Nothing else is left of the
12 runs the user approved for this case. Ask the user now for 3 more run(s), with that number; on yes, grant 3: send(to="lead", budget=3,
body=<why>).`

**Docstrings and help.** Root's `request` tool: `budget: runs handed down (default: the contract's; for a rework the user asked for,
source="human", what is left of the runs the user approved for the case, at most the contract's; the usual reserve rule applies)` and
`the reply then states the case total (runs used by the whole chain, the user's and your relayed reworks' apart, runs handed down, the
contract's budget per request), tells you to inform the user when the user's requests cost more than they approved, and names the top-up to
ask for when a rework the user asked for gets less than it needs`. The agents' `request` docstring is unchanged (agents have no `source`; the
rule does not apply to them). CLI `request --budget`: `runs handed down (default: the contract's; for a rework you asked for, what is left of
the runs you approved for the case)`.

### 4.6 Code sites

- `SRC/reflection/_ports.py`: `RunCounter.stamps`. `SRC/reflection/_runs.py:LogRunCounter.stamps`; `runs_between` counts its uncredited
  stamps. `SRC/reflection/testing.py`: the counter fakes gain `stamps`.
- `SRC/reflection/api.py`: `Case` gains `relayed_runs: int = 0`, `relayed_returned: int = 0`, `user_granted: int = 0`, `user_ceiling: int = 0`
  (defaulted, so every hand-built `Case` keeps today's meaning: approval = contract budget, user spend = case spend); `user_spend`,
  `user_committed`, `user_approved`; the `case_total` and `rework_step` docstrings. `case_spend` untouched.
- `SRC/reflection/_cases.py:DerivedCaseHistory.cases`: the computation of 4.3.
- `SRC/reflection/_reports.py`: `RELAYED_SPEND`, `OVER_APPROVED` and the new `case_total`.
- `SRC/reflection/_allowance.py` (new): `CaseAllowanceOf`, `client_round`. `SRC/reflection/_steps.py`: `TOPUP` and the human branch.
- `SRC/services/api.py`: `Allowance`, `CaseAllowance` (exported). `SRC/services/_request.py`: the 7th collaborator, `_default_budget`,
  `NO_RUNS_LEFT`. `SRC/services/testing.py`: `FixedAllowance`, `IMPLEMENTATIONS[CaseAllowance]`, and the services worlds wire a
  `FixedAllowance({})` (answers None: the contract's budget, today's behaviour) unless a test gives one.
- `SRC/app/fields_services.py`: `case_allowance: CaseAllowance` ("a port of `services` that `reflection` implements: `wire_reflection`
  provides it"). `SRC/app/wire_reflection.py`: `CaseAllowance -> CaseAllowanceOf(b.get(CaseHistory), b.get(ServiceCatalog),
  b.get(AgentDirectory))`. `SRC/app/wire_services.py`: `RuleServiceRequester(..., b.get(JudgedVersions), b.get(CaseAllowance))`.
- `SRC/mcp_server/_tools_services.py`: root's `request` docstring only. `SRC/cli/_commands_services.py`: the `--budget` help only.

### 4.7 Tests to write first (each RED before its code)

- `SRC/reflection/tests/test_run_counter.py`: `stamps` lists the stamps of the inclusive window, sorted, with the credit flag; `runs_between`
  equals the number of uncredited ones.
- `SRC/reflection/tests/test_cases.py`: `relayed_runs` of head, human, relayed (the runs of the last interval); of a relayed rework followed by
  a human one (the interval ends at the next task); 0 without a relayed task; credited runs are in no count. `relayed_returned`,
  `user_granted` (a grant in a relayed interval is not a user grant; one outside the window is not a grant) and `user_ceiling` on the four E5
  shapes of the table in 4.3 (built in an fs world with explicit run logs and results).
- `SRC/reflection/tests/test_pure_functions.py`: `user_spend == case_spend` for every state of a chain without a relayed task (a property over
  the existing fixtures); `user_spend` leaves a relayed task's runs and still-out runs out; `user_committed` ignores the state and counts
  grants; `user_approved` is the contract budget for a hand-built case and the ceiling when it is higher.
- The gate's 7 files: `SRC/reflection/tests/test_contract_service_reports.py` and `test_reports.py` (both forms of the head, both overspend
  sentences, the relayed sentence; no "exceeds" when an explicit human budget raised the approval; "exceeds" when the team ran more runs than
  were handed down for the user's requests); `SRC/progress/tests/test_lines.py` (a multi-sentence total joins with `. ` and no `..`);
  `test_fakes.py` (unchanged: the fake passes text through; kept in the FAST targets); `test_services.py` (the rework of its chain is relayed
  by the facade's default: the relayed form, no "exceeds"; a second test makes the user's requests overspend); `SRC/mcp_server/tests/
  test_service_tools.py` (the rework reply in relayed form; a human rework without `budget` is handed what is left; the `TOPUP` step after
  the case total; `NO_RUNS_LEFT` through MCP); `test_tools_services.py` (the step a fake `ServiceSteps` gives for a human rework is appended
  after the case total, like the relayed one).
- `SRC/services/tests/test_request.py` (over `FixedAllowance`): `min(left, contract)`; `left > contract` gives the contract's; `left <= 0`
  refuses with the exact `NO_RUNS_LEFT`; None and a raising allowance give the contract's; a relayed rework, an agent's rework and a fresh
  request are not asked; an explicit `budget` is kept; the refusals of `revises` and `base` still come first. `test_texts_cli_forms.py`:
  `NO_RUNS_LEFT` gives its CLI form and ends `Nothing was sent.`
- `SRC/services/tests/test_contract_case_allowance.py` (suite) and its re-run in `SRC/reflection/tests/`; `SRC/reflection/tests/test_steps.py`
  and `test_contract_service_steps.py` (the `TOPUP` branch: below the round, at it, with spare runs, none left).
- `SRC/app/tests/test_runtime_fields.py` and a wiring test: the field exists and the requester gets the reflection implementation.
- **Replays** (`TESTS/e2e/test_org_growth_0a3.py`, over the new test-only kit `TESTS/testkit/e5_replay.py` described below):
  - `test_e5_s1_t6_the_case_reads_ten_user_runs_and_five_relayed_without_exceeds`: at #28 (`20261024T031704521000`), `case_total(963a)` is
    the exact s1 text of 4.4, `user_spend == 10`, `relayed_runs == 5`, `user_approved(case, 12) == 17`, and neither "exceeds" nor "tell the user"
    is in it;
  - `test_e5_s2_t5_the_rework_lena_funded_does_not_exceed`: at #21 (right after `...-root-6c4f`) and at #23 (`20261024T034512547000`), the two
    exact s2 texts of 4.4, without "exceeds".

**The replay kit** `TESTS/testkit/e5_replay.py` (test-only): `materialize(stream, cut, dest, *, inflight=None) -> Path` writes an organization
at `dest` holding what `EV5/<stream>` had at the 21-character stamp `cut`: `org-files/ORG.md`; each `org-files/<a-b>-AGENT.md` as
`<a/b>/AGENT.md`; `service/history--SERVICE.v1.md` as `lead/services/weekly-meeting-memo/SERVICE.md`; every file of `msgs/<box>` and
`msgs/<a-b>-<box>` with `id[:21] <= cut` in that box of root or of `a/b`; an empty `<a/b>/runs/<stamp>.log` for every file of `run-logs/<a-b>/`
with `stamp <= cut`. `inflight` moves named message ids of an agent into its `inflight/` box (7.3's replay). A missing evidence file fails the
test (`pytest.fail`), as in `e4_replay.py`. The kit reads the evidence only; 0b's general replay kit (0b 19.1) may absorb it.

### 4.8 Zero and empty cases

- No relayed task: `relayed_runs = relayed_returned = 0`, `user_spend == case_spend`, the head and the overspend sentence are today's bytes.
- A relayed task with no run yet (root just sent it): head form 2 with `0 by your relayed rework <id>`, and the relayed sentence.
- No top-up: `user_ceiling <= B`, so `A == B`; with a relayed task the overspend sentence has no `topped` part.
- No contract budget: impossible for a stored contract (`define_service` requires `budget >= 1`); `user_approved` is a `max`, so a 0 budget
  gives the ceiling; a task with no contract, or of a retired service, gives `""` as today.
- A hand-built `Case` (fakes): the four new fields are 0, so every existing unit test keeps its meaning.
- A case whose runs cannot be read raises as today (no change in 0a.3; 0b adds `runs_unknown`).
- The allowance: no case or no contract gives None (the contract's budget); an owner with no agent below has `need = 1`; `left` exactly 1
  hands down 1 and the step asks for `need - 1`.
- `TOPUP`: a budget at or above the round, or spare runs covering the shortfall, give `""`.

### 4.9 What 0b reuses

`RunCounter.stamps`, `Case.relayed_runs`, `user_spend`, `user_approved` (D-E5-6: 0b's cost alarm compares the user's runs with the user's
approved runs, the rule of 4.4) and the `relayed` finding kind of 7.2, which 0b's hand-edit attribution must not count as a hand edit (0b 4.3
counts only `differs`). 0b's own `Case.credited`, `top_ups`, `cut` and `runs_unknown` are not built here. The names do not collide: 0b's
"approved budget" (the contract's) and `Case.top_ups` (every later budget, by kind) keep their 0b meaning; 0b's amendment decides whether its
view shows `user_approved` beside them.

## 5. D-E5-2, proposal B: the plan budget

### 5.1 Decision

For a service, the plan states the estimate with one client round: the estimate (one pass and one internal rework, unchanged) plus
`client_round` (section 3). In a blueprint every service is offered by the top agent and defined by root (`_service_rules.py`: "root defines
services only for its direct reports"), so every blueprint service has a human client. The `budget-tight` warning gives the number and what
it covers; the Budget line names the round; SKILL.md step 6 tells the assistant to offer the number. Nothing becomes an error.

### 5.2 Code and texts

- `SRC/blueprint/_budgeting.py:BudgetPlanner.client_round(agents) -> int`: `1 + 2 * sum(1 for a in agents if a.parent is not None)`; 0 for no
  agents. Added to the private `BudgetPlanning` Protocol (`_protocols.py`, 5 -> 6 methods). `estimate`, `planned_total`, `service_budget` and
  the default planned budget (`ceil(estimate * 1.25)` within the cap) are unchanged (Deviation 7).
- `SRC/blueprint/_service_rules.py`, the budget check of each service (`total` its budget, `est` the estimate, `r = client_round(agents)`,
  `top` the top agent's name, else `the top agent`):
  1. `total < est`: `budget-low`, unchanged (text and path).
  2. `est <= total < est + r` (new, `budget-tight`): `{total} runs per request covers one pass and one internal rework (the estimate is
     {est}), not a round of your questions or a rejection, which takes about {r} more (1, plus 2 for each agent below {top}): {est + r} per
     request covers one such round`.
  3. otherwise `total < ceil(est * 1.10)` (`budget-tight`, today's text, unchanged): it can fire only when the round is under a tenth of the
     estimate, so no warning of today disappears.
  E5's plan reads: `12 runs per request covers one pass and one internal rework (the estimate is 11), not a round of your questions or a
  rejection, which takes about 5 more (1, plus 2 for each agent below lead): 16 per request covers one such round`.
- `SRC/blueprint/_userplan.py:_user_budget`, services branch: `...; the minimum for one review and rework is {est}, and a round of your
  questions or a rejection takes about {r} more ({est + r} in all). Unspent runs come back to you.` (the clause is left out when `r == 0`). The
  plain-task branch is unchanged.
- `SRC/blueprint/_details.py`, the services header: `Budget per request (your cap: 12), estimate 11 for one pass + one review/rework cycle,
  16 with one round of your questions or a rejection:` (the clause is left out when `r == 0`). The plain branch is unchanged.
- SKILL.md step 6: section 8.

### 5.3 Why no plan is newly refused

`propose_org` and `apply_org` refuse only on issues of level `error`. The only budget errors are `budget-cap` (above the user's cap) and
`budget-low` (below the estimate); both read the unchanged `estimate` and the unchanged planned budget. `client_round` feeds only the two
`warning` texts and the two plan lines. So every blueprint that validates today validates with the same errors. The corpus golden checks it:
its regeneration (section 12) may add or change only rows of level `warning` with code `budget-tight`, and the diff review rejects any other
row.

### 5.4 Tests to write first

- `SRC/blueprint/tests/test_budget_planner.py`: `client_round` is 5 for lead, writer, reviewer; 7 for the research example; counts nested
  agents; 0 for none.
- `SRC/blueprint/tests/test_services.py`: E5's blueprint (cap 12, budget 12) gets exactly the warning text above and no error; a budget equal
  to `est + r` gets no `budget-tight`; a budget below the estimate keeps today's `budget-low` text; the warning's path is
  `services[<name>].budget`.
- `SRC/blueprint/tests/test_plan_block.py`: the services Budget line with E5's numbers; a plain task's Budget line is unchanged.
- `SRC/blueprint/tests/test_resolver.py`, `test_validate_corpus.py` with `_corpus.py`: unchanged code; the corpus golden is regenerated.
- The plan goldens (section 12).

## 6. D-E5-3, proposal C: the scheduler outlives the chat call

### 6.1 The reproduction first (manual, real kiro-cli 2.33.0, before the fix commit and again after it)

Nothing under `~/.kiro` and nothing of the user's org is read or written by these steps: the agent profile is local to the sandbox (kiro-cli
2.33.0 discovers the local agents of the directory it is invoked in, per `kiro-cli agent --help`; the profile goes in `<cwd>/.kiro/agents/`,
and steps 4 and 5 confirm it is found), the MCP server's state goes to a sandbox state directory, the model may use only the hirearchy tools,
and the user's own MCP servers are not loaded. No step lists, opens or hashes anything under `~/.kiro`. kiro-cli keeps its own session record
where it always does; that is kiro-cli's own write, not ours.

1. `SB=/tmp/hirearchy-0a3-detach-$(date +%s)`; `mkdir -p $SB/bin $SB/.kiro/agents $SB/kiro-state`. `WT` is the worktree.
2. An organization with work in flight: `uv --directory $WT run hirearchy --root $SB/org init ...`, then (CLI, as root) hire one agent `ceo`
   and give it one task. The CLI runs with `HIREARCHY_STATE_DIR=$SB/kiro-state`.
3. `$SB/bin/kiro-cli`, a stub for the org's own runs only (no second model call): it answers `--version` (`kiro-cli 2.33.0`), `chat --help`
   (the three V3 flags) and `whoami` as `tests/testkit/fixtures.py:STUB` does, and for `chat` reads stdin, prints the `runStarted` line, sleeps
   60 s, prints `runFinished`.
4. `$SB/.kiro/agents/repro-0a3-<epoch>.json`: `mcpServers.hirearchy = {"command": "uv", "args": ["--directory", WT, "run", "hirearchy", "mcp"],
   "env": {"ORG_ROOT": "$SB/org", "HIREARCHY_STATE_DIR": "$SB/kiro-state", "PATH": "$SB/bin:<the shell's PATH>"}}`, `"tools": ["@hirearchy"]`,
   `"includeMcpJson": false`, `"resources": []`, `"hooks": []`, `"model": "claude-sonnet-5.5"`. Check it with
   `kiro-cli agent validate --path <that file>`.
5. One call, `cd $SB`: `kiro-cli chat --v3 --no-interactive --trust-all-tools --require-mcp-startup --effort high --agent repro-0a3-<epoch>
   "Call the hirearchy tool start once with its defaults, then reply with its result only."` (the flags of E5's `run_turn.sh`, plus
   `--require-mcp-startup`; claude-sonnet-5.5 at high effort, as every seat).
6. The moment it returns, and again 5 s later: is the pid of `$SB/org/.runtime/scheduler.pid` alive (`ps -p`)? Is the run's `child_pid` (its
   `run.start` event) alive? Do `$SB/org/.runtime/events/*/*.jsonl` hold `scheduler.exit` and `run.end`?
7. Clean-up: kill only processes whose command line names `$SB` (the rule of `tests/testkit/kiro_sandbox.py`); after the record is written,
   remove `$SB`.

Expected before the fix (E5 s3's pattern): within about a second of the return, the scheduler and the run are gone, with no `scheduler.exit`
and no `run.end`. After the fix, in a fresh sandbox on the fix commit: both are alive after the return; then `hirearchy --root $SB/org stop`
records `run.end` (`killed: true`) and `scheduler.exit` (`stopped by SIGTERM`). The outcome of both runs (commands, pids, event lines) goes to
`.agents/tasks/repro-detach.md` (not committed) and is summarized in the fix commit's body.

Stop conditions (send `warning`, do not ship C): kiro-cli does not load the local agent (a profile under `~/.kiro/agents` would be needed,
which only the owner may allow); the defect does not reproduce before the fix; or the scheduler still dies after it (kiro-cli then kills by
another mechanism than the process tree, and the design must be redone).

### 6.2 The detach

`ProcessSpawner.spawn_detached` (`SRC/processes/api.py`) changes its contract and return type:

```python
def spawn_detached(self, argv: Sequence[str], *, cwd: Path, env: Mapping[str, str], log: Path) -> int:
    """Start ``argv`` so that it is no descendant of this process: an intermediate process starts it in a session of its own (stdin /dev/null,
    stdout and stderr appended to ``log``, created if missing), reports its pid and exits at once, so it is re-parented (to launchd or init, or
    to the nearest subreaper on Linux) and outlives this process and every process of this process's tree. Returns its pid. ``OSError`` when
    the intermediate cannot be started, fails, or reports no pid within 10 seconds."""
```

`SRC/processes/_detach.py` (new, standard library only, run as a script, never imported):

```python
def main(args: list[str]) -> int:
    """``<log> -- <argv...>``: start argv in a new session with its output appended to log, print its pid, and leave without waiting for it."""
    log, command = args[0], args[2:]
    with open(log, "ab") as out:
        child = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=out, stderr=subprocess.STDOUT, start_new_session=True, close_fds=True)
    sys.stdout.write(f"{child.pid}\n")
    sys.stdout.flush()
    os._exit(0)  # no wait, no clean-up of the Popen object: the child's parent is gone at once
```

`PopenProcessSpawner.spawn_detached` runs `[sys.executable, "-I", str(Path(__file__).with_name("_detach.py")), str(log), "--", *argv]` with
`cwd`, `env`, `stdin=DEVNULL`, `stdout=PIPE`, `stderr=PIPE`, `start_new_session=True`, then `communicate(timeout=10)`: exit 0 and one line that
is a positive integer gives the pid; else `OSError`. The scheduler's stdout and stderr are the log, its stdin is `/dev/null`, and `close_fds`
closes the pipe to us, so `communicate` returns when the intermediate exits and never waits on the scheduler. `-I` keeps the intermediate free
of `PYTHON*` variables and user site packages; the scheduler still gets `env` whole (it is passed to the intermediate and inherited).

`SRC/daemon/_launch.py:DetachedLauncher` drops its `Children` collaborator (7 -> 6) and does:

```python
pid = self._spawner.spawn_detached(argv, cwd=self._site.directory(), env=env, log=log)
return self._watch.await_start(pid, log)
```

`StartupWatch.await_start(pid: int, log: Path) -> int` (private port). `SRC/daemon/_watch.py:PidFileStartupWatch(layout, marker, clock,
inspector: ProcessInspector)`, every 0.05 s for up to 10 s:
1. the pid file names `pid`: return the pid read from the file (that is the scheduler's own record of itself, written by its lock);
2. the process is gone (`inspector.info(pid)` is None or a zombie; `ProcessTableError` counts as not gone): if the exit marker reads `FINISHED`
   it had nothing to do and exited by itself: return `pid`; else raise `OrgError("the scheduler exited at once; {log} ends with:\n{tail}")`
   (the last 5 log lines, as today);
3. after 10 s: return `pid` (a slow start; today's behaviour).

The reported pid is what makes 1 safe against a stale pid file of a dead scheduler and what makes 2 fast (Deviation 11). The exit code is
not known any more (the scheduler is not our child), so the error names none; the exit marker decides "nothing to do" (Deviation 9).
`ChildRegistry` stays and still reaps (nothing is adopted any more; backlog).

Fakes: `FakeProcessTable.spawn_detached` returns the pid of a row with `ours=False` (no zombie: gone when it exits);
`processes.testing._TrackingSpawner`, `ProcessWorld.start_echo` (returns a pid), `daemon.testing.ScriptedSchedulerSpawner` and the
pass-through in `scheduler/testing.py` follow. `ProcessWorld` gains `is_child(pid) -> bool` (real: `os.waitpid(pid, os.WNOHANG)` raising
`ChildProcessError` means no; fake: the row's `ours`). `wire_daemon` builds the launcher without `children` and the watch with the
inspector.

### 6.3 Why it survives the parent's whole process tree being killed

After the intermediate exits, the kernel gives the scheduler a new parent: init (pid 1, launchd on macOS) or, on Linux, the nearest ancestor
marked as a subreaper. Its parent-pid chain then no longer passes through the MCP server, so a kill of the MCP server's descendants (found by
parent pid, the only link E5 found between them: F-E5-2) does not reach it. It leads its own session and process group, so a group or session
signal of the MCP server does not reach it either (already so today). Its runs are its own children in their own sessions, so they are
descendants of the scheduler only. The scheduler holds none of the MCP server's descriptors (stdin `/dev/null`, output to the log, the rest
closed), so the end of the MCP server's stdio cannot reach it. Declared limit: on Linux, an ancestor that is a subreaper (a container init, or
a tool that sets `PR_SET_CHILD_SUBREAPER`) adopts the scheduler and could kill its children on exit; macOS has no subreapers. The reproduction
(6.1) is what shows kiro-cli 2.33.0 on macOS kills by tree and not by another mechanism.

### 6.4 Tests to write first

- `SRC/processes/tests/test_contract_process_spawner.py` (real and fake): a detached process is no child of this process (`is_child` False:
  RED today), leads its own session, appends to its log (waited for, no handle any more), creates a missing log, and a log it cannot open is an
  `OSError` (real) or the fake's scripted failure.
- `SRC/processes/tests/test_popen_process_spawner.py`: the intermediate's failure (a command that does not exist) is an `OSError` naming it;
  the pid it returns is alive and not ours; the intermediate itself is reaped.
- `SRC/daemon/tests/test_startup_watch.py`, `test_detached_launcher.py`, `test_control.py`: the watch over a pid (the cases of today, with the
  new error text without the code; `FINISHED` with a gone process is fine; another marker with a gone process is the error); the launcher
  returns the watch's pid and adopts nothing.
- `TESTS/e2e/test_scheduler_detach.py` (not marked `integration`: no real kiro, about 5 s; the same code on macOS and Linux):
  1. an org (`poll_seconds` 0.05) with a leaf `ceo` and one root task (budget 2);
  2. a stub `kiro-cli` in `tmp/bin`: the readiness answers of `fixtures.STUB`; for `chat`: read stdin, print `runStarted`, sleep 3 s, run
     `testkit/fake_agent.py` with the absolute venv Python (`FAKE_MODE=work`: the leaf reports done), print `runFinished`;
  3. a parent process (`sys.executable tmp/parent.py <org>`, `PATH=tmp/bin:...`, its own session) that calls
     `Org(<org>).runtime.scheduler_control.start(None, True)`, prints the pid and sleeps, as root's MCP server does;
  4. once `run.start` of ceo is in the events (at most 15 s): collect the parent and every descendant by parent pid (`ps -A -o pid=,ppid=`,
     breadth first), SIGTERM them all, 0.2 s later SIGKILL them all (E5 s3's escalation);
  5. within 30 s: a `run.end` of that run with `ok: true`, the task's `done` result, a `scheduler.exit` (finished: no open tasks), and the
     scheduler's pid gone; the scheduler's pid was not among the killed (the failure message lists both sets);
  6. `finally`: kill the scheduler and the run's group if still alive (only pids the test learned).
  Today it fails at step 5 (the scheduler is a child of the parent).

## 7. D-E5-5, the small items

### 7.1 F-E5-4: the P2-UNRATED text

Site: `SRC/services/_define.py:UNRATED`. New text:

```
refused: {n} delivered request(s) of `{name}` have no verdict yet: {tasks}. Record a verdict on each with feedback first: on a delivery the user saw, the user's own, a rejection then its one question (CLI: hirearchy feedback <task id> accept|reject --note ...); on a relayed rework the user never saw, your own, with source="relayed" (CLI: --source relayed), settles it. The contract changes only after the verdicts. Nothing was written.
```

Design D4 already allows it ("any verdict on it or later": `reflection.rated` counts every tier); only the text changes. Derived: nothing new.
Test first: `SRC/services/tests/test_define_gate.py::test_an_amendment_while_a_delivery_has_no_verdict_is_refused_whatever_else_is_passed`
asserts the new text; `test_texts_cli_forms.py` keeps passing (CLI form, ends `Nothing was written.`). `RETIRE_UNRATED` is not changed
(backlog).

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

Texts (`deliverables_note`; a `relayed` finding is a line of its own, never counted in a folder block's `{n} file(s) the team did not deliver
as checked`; `{name}`, `{folder}` and `{path}` through `shown_name`; `s` when several ids):
- folder: `Deliverable folder {folder} ({services}): {name} is the delivery of task {task} as the team checked it; your relayed rework{s} {ids} (your own reading, not the user's) changed the team's copy after that delivery, so the file is not a deviation.`
- file contract: `Deliverable file {path} ({services}): it is the delivery of task {task} as the team checked it; your relayed rework{s} {ids} (your own reading, not the user's) changed the team's copy after that delivery, so the file is not a deviation.`

E5 s1 after the injection reads:

```
Deliverable folder "/tmp/hirearchy-e5-s1-1792811051/deliverables" (service `weekly-meeting-memo`): "memo-2026-10-05.md" is the delivery of task 20261024T031013210098-root-aae2 as the team checked it; your relayed rework 20261024T031317713451-root-963a (your own reading, not the user's) changed the team's copy after that delivery, so the file is not a deviation.
```

Tests first: `SRC/reflection/tests/test_deliverable_checks.py` (fake checked versions: the E5 shape gives `relayed`; a human rework that
differs in between gives `differs` as today; two relayed reworks give both ids; the newest relayed pair equal to the file gives no finding; a
human verdict after the mtime settles it; the file rule's variant); `test_deliverables_note.py` (both texts, several ids, the block count
excludes it, names through `shown_name`); `test_contract_deliverable_checks.py` (the fs world with real git: the E5 shape).

### 7.3 F-E5-7: the missing human tier is a defect

**Finding.** In s3, the lead's first delegations for memo 2, `...-lead-0a56` (writer, 04:28:06) and `...-lead-16f9` (reviewer, 04:28:55), carry
no `trace` (checked in `/tmp/hirearchy-e5-s3-1792814736/org/lead/sent/`). The stamp rule left them `ambiguous`: the `msg.deliver` event of 16f9
has `trace_rule: ambiguous` with candidates `[...-root-e268, ...-root-dd39]`, because the lead still held memo 1's `blocked` task c209 (trace
e268; a blocked result is not final for `open_task_traces`) while it worked on dd39. The rework delegations df89 and caa9 revise 0a56 and 16f9.
`ServiceReworkContext.fields_for` (`SRC/services/_rework.py`) looks for the tier only `if actor != ROOT and task.trace` of the revised task,
so it found none. df89 itself was stamped dd39 by the `batch` rule (its event says `trace_rule: batch`), and the lead's unanswered task in dd39
was 57b3 with `source: human`. The 9 delegations that carry the tier revise tasks that had a trace. So the tier rule of 0a.2 7.6 fails
silently whenever the revised delegation was stamped without a trace: a defect.

**Fix.** When the revised task has no trace, the tier is looked up in the trace of the run's batch:

```python
trace = task.trace or self._batch_trace(actor)
if actor != ROOT and trace: ... self._tier(actor, trace) ...

def _batch_trace(self, actor: str) -> str | None:
    """The one trace of the tasks in ``actor``'s run batch (its ``inflight`` box, the runtime's tasks left out); None for none or several."""
    traces = {m.trace for m in self._mail.messages(actor, "inflight") if m.type == "task" and m.sender != RUNTIME and m.trace}
    return next(iter(traces)) if len(traces) == 1 else None
```

It is the stamper's own `batch` rule applied to the same box, so the delegation and its tier agree. The stamp rule itself is not changed:
`traces` is not among `services`' dependencies, and the stamp affects every message (backlog).

Tests first: `SRC/services/tests/test_service_rework_context.py` (fs and memory worlds): the lead holds a blocked human task of trace A, gets a
fresh task of trace B, delegates W without a trace, then receives the human rework of B in its batch: `fields_for("lead", W.id)` gives
`source: human`; a batch with tasks of two traces gives no tier; a revised task with a trace is unchanged. Replay
`test_e5_s3_the_rework_delegation_of_memo_2_inherits_the_human_tier` (`TESTS/e2e/test_org_growth_0a3.py`): `materialize("s3",
"20261024T043138264197", ..., inflight={"lead": ["20261024T043106950333-root-57b3"]})` and `fields_for("lead", "...-lead-0a56")` is
`{"source": "human"}`.

### 7.4 L-ASIS: one SKILL.md line

Section 8 gives the replaced line. It tells root that when the user keeps the version they have as it is, root records that accept on its task
with `source="human"` and the user's words, also after a reject. Test first: a needle in `SRC/skill/tests/test_skill_org_growth.py`.

## 8. SKILL.md and ROOT_INSTRUCTIONS

SKILL.md stays at 125 lines: both changes replace text inside existing lines.

**Step 6** (section 1, item 6; lines 37-40 today, still 4 lines):

```
6. Budget in runs (each agent wake-up is one run). Default: the estimate + 25%; every agent runs claude-sonnet-5.5 at high effort. A service's per-request
   budget is the plan's estimate + 25% (the lead wakes once per result: about 2 runs per delegation + 1); if the user's cap is lower, say
   in one line what that risks; if the plan warns that the budget does not cover a round of their questions or a rejection, offer them the number it gives
   (they may keep theirs). Nothing below claude-sonnet-5.5 at high effort is available: never offer a cheaper model, tiers to save runs or a lower effort; if the user asks for one, say so in one line.
```

**L-ASIS** (section 5, item 6; line 100 today, still one line):

```
   ("keep it" / "what's wrong"); when they keep the version they have as it is ("I'll take it as it is"), record that accept on its task, `source="human"`, with their words, also after a reject; "deliver as is" or "I'll read it myself" is not an accept: ask, or record nothing yet. A known unmet
```

Every existing needle stays (`per-request budget is the plan's estimate + 25%`, `about 2 runs per delegation + 1`, `say in one line what that
risks`, `"deliver as is" or "i'll read it myself" is not an accept`, `ask, or record nothing yet`). New needles: `offer them the number it
gives` (`SRC/blueprint/tests/test_round_f_guidance.py::test_skill_sizes_service_budgets_and_reads_the_send_reply`) and `record that accept on
its task` (`SRC/skill/tests/test_skill_org_growth.py`). Resulting line count: 125. `ROOT_INSTRUCTIONS` is not edited (2 642 characters at the
reference path).

## 9. Error handling

| Operation | Failure | Recoverable? | Caller receives | Logged |
|---|---|---|---|---|
| `request` (human rework, no `budget`) | the allowance cannot be read (`OrgError`, `OSError`) | yes | the request is sent with the contract's budget (today's default) | the `tool.call` event as today; no extra log |
| `request` | nothing left of the approval | yes (pass `budget`) | `OrgError(NO_RUNS_LEFT)`, nothing sent | `tool.call` with `ok: false` (`ToolRecorder`), as every refusal |
| `request` reply | `rework_step` cannot read the record | yes | the reply without the step (`_step` turns `OrgError`/`OSError` into `""`, as today) | none |
| `case_total` | a mailbox or run log directory cannot be read | as today | the error propagates as today (no change) | as today |
| `spawn_detached` | the intermediate cannot start (`OSError` from `Popen`), exits non-zero, or prints no positive integer within 10 s (killed, then reaped) | yes (try `start` again) | `OSError("could not start <argv[0]> detached: <the intermediate's last stderr line, clipped to 200>")`; the MCP `start` tool returns the tool error | `tool.call` with `ok: false`; the intermediate's stderr is in the message |
| `await_start` | the scheduler is gone without the `FINISHED` marker | yes | `OrgError("the scheduler exited at once; {log} ends with: ...")` | the scheduler's own output is in its log |
| `await_start` | no pid file after 10 s | yes | the pid (today's behaviour) | none |
| deliverable checks | a checked version unknown, git past its bound | yes | as today (`current`, or the pair skipped) | none |
| `fields_for` | a mailbox cannot be read | as today | the error propagates (as today) | as today |
| replays (tests) | an evidence file is missing | no | `pytest.fail` naming it | test output |

## 10. Validation of external inputs

- `request(budget=...)`: optional; an `int` of at least 1, not a `bool` (unchanged); when given, the allowance is not consulted.
- `request(source=...)`: `"human"`, `"relayed"` or None (unchanged); only root's `human` rework gets the new default.
- The intermediate's stdout: required; exactly one line holding a positive integer; anything else is the `OSError` of section 9.
- The pid file: an integer naming the reported pid counts; garbage, another pid or a missing file is waited through (unchanged).
- Blueprint budgets: unchanged validation; `client_round` reads only resolved agents.
- No new external input reaches a stored file: every number above is derived per call.

## 11. Invariants and their owners

| # | Invariant | Owner | Why there |
|---|---|---|---|
| I1 | `case_spend` is unchanged; `user_spend == case_spend` when the chain has no relayed rework | `reflection.api` (pure functions; a property test) | 0b reads `case_spend` (0b I4) |
| I2 | One definition of relayed runs, from one `stamps` call per case | `reflection._cases.DerivedCaseHistory` | 0b 4.2 computes `credited` from the same call |
| I3 | The user's approval is derived from the files, never stored | `reflection` (`user_ceiling`, `user_approved`) | the files are the record (R9, no ledger) |
| I4 | Root's human rework without `budget` never gets more than what is left, nor more than the contract's budget | `services.RuleServiceRequester` | the one layer the MCP tool and the CLI share |
| I5 | No blueprint is newly refused | `blueprint` (only `warning` texts read `client_round`) | errors decide `propose_org` and `apply_org` |
| I6 | A scheduler started detached is no descendant of the process that started it | `processes.PopenProcessSpawner` (the only detached spawner) | `daemon` owns the pid and the watch |
| I7 | A file equal to a checked delivery is never called a deviation because of a later relayed rework | `reflection._deliverable_checks` | P3's one comparison |
| I8 | A rework delegation's tier comes from the runtime's mailboxes, never from the agent | `services._rework` | 0a.2 7.6 |

## 12. Golden impact (expected; each regenerated file is named with its line count in its commit)

Methods: **G** `HIREARCHY_UPDATE_GOLDEN=1 uv run pytest tests/golden -k <test>`, then review `git diff`; **H** a deliberate edit of the
package's expected file (colocated expected files have no switch); **S** a throwaway script (not committed) that writes exactly what the test
compares, then review `git diff`.

| Commit | File | Method | Why |
|---|---|---|---|
| A3 | `SRC/progress/tests/expected/all.txt`, `task_1_weekly-brief.txt`, `task_2_weekly-brief.txt` | H | the scenario's rework (`progress/tests/_scenario.py:119`, the facade's default source) is relayed: head form 2 and the relayed sentence |
| A4 | `TESTS/golden/expected/mcp/surface_root.txt`, `surface_root_unbound.txt`, `surface_root_setup_mode.txt` | G | root `request` docstring (4.5) |
| A4 | `TESTS/golden/expected/cli/help_request.txt`, `SRC/cli/tests/expected/help_request.txt` | G, H | `--budget` help |
| B1 | the 9 service plans of `TESTS/golden/expected/plans/` (`example_blueprint-service.txt`, `propose_{raw,filled}_template_{research,documents,code,analysis}_service.txt`) | G | the Budget line, the Details header, and the new `budget-tight` warning in the block and in the Details: every template's budget (22, 19, 23, 23) is under its estimate plus round (24, 22, 25, 25) |
| B1 | `SRC/blueprint/tests/golden/second_half.json` | S | the same three changes in its 8 service plans; plan ids unchanged (they hash the blueprint) |
| B1 | `SRC/blueprint/tests/golden/validate_corpus.json` | S | about 50 of the 58 `services:*` entries gain the warning, `services:budget-tight` changes its text; no `error` row changes (5.3) |

Distinct regenerated files: **19** (3 progress, 3 MCP, 2 CLI, 9 plans, 2 blueprint JSON). Must stay byte-identical (the commit stops until a
diff is explained): the 10 plain-task plan goldens, `surface_manager*.txt`, `surface_worker.txt`, the reflection `totals_*` (its stories send
human reworks with explicit budgets), every `messages/*`, `events/*`, `kiro/*`, `prompts/*` (the prompt scenario passes `budget=6`),
`cli/progress*`, `cli/status*`, the dashboard and observability goldens.

## 13. Test-site rules (existing tests the new default touches)

- **Rule B.** An existing test that sends root's human rework without `budget` and is not about the default passes the budget it got before
  0a.3 (the contract's) explicitly, so its flow is unchanged. Known sites: `TESTS/e2e/test_org_growth_0a.py:138, 202, 291`,
  `TESTS/e2e/test_org_growth_0a2.py:274`, `SRC/reflection/tests/test_cases.py:64`, `SRC/services/tests/test_contract_service_commands.py:715`,
  `SRC/reflection/tests/test_steps.py:222`. Tests over the services fakes (`mcp_server/tests/test_tools_services.py`, the CLI command tests) are
  not affected.
- **Rule R.** A case-total test whose rework is relayed by default and is about overspend gets `source="human"` or a scenario in which the
  user's requests run more runs than were handed down; one about the relayed form keeps the relayed default.
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
| A2 | `feat(reflection): the user's spend and approved runs of a case` | `src/hirearchy/reflection/tests` |
| A3 | `feat(reflection): the case total names the relayed runs apart and warns on the user's spend` (+ `testkit/e5_replay.py`, the s1 and s2 replays) | `src/hirearchy/reflection/tests src/hirearchy/progress/tests src/hirearchy/mcp_server/tests tests/e2e/test_org_growth_0a3.py` |
| A4 | `feat(services,reflection,app): a rework the user asked for gets what is left of the approved runs` | `src/hirearchy/services/tests src/hirearchy/reflection/tests src/hirearchy/mcp_server/tests src/hirearchy/cli/tests src/hirearchy/app/tests` and the Rule B sites |
| A5 | `feat(reflection): the rework reply names the top-up to ask for` | `src/hirearchy/reflection/tests src/hirearchy/mcp_server/tests` |
| B1 | `feat(blueprint): the plan budget names the client round` | `src/hirearchy/blueprint/tests` |
| B2 | `docs(skill): step 6 offers the number that covers the client round` | `src/hirearchy/skill/tests src/hirearchy/blueprint/tests/test_round_f_guidance.py` |
| C0 | the reproduction of 6.1 before the fix (no commit; `.agents/tasks/repro-detach.md`) | - |
| C1 | `fix(processes,daemon): the scheduler is no descendant of the process that starts it` | `src/hirearchy/processes/tests src/hirearchy/daemon/tests src/hirearchy/scheduler/tests src/hirearchy/app/tests tests/e2e/test_scheduler_detach.py` |
| C2 | the reproduction of 6.1 on C1 (no commit) | - |
| D1 | `fix(services): P2-UNRATED says your own relayed verdict settles a relayed rework the user never saw` | `src/hirearchy/services/tests` |
| D2 | `fix(reflection): the deliverable note names the delivery a later relayed rework changed` | `src/hirearchy/reflection/tests src/hirearchy/progress/tests src/hirearchy/mcp_server/tests` |
| D3 | `fix(services): a rework delegation finds its tier through the run's batch when the revised task has no trace` (+ the s3 replay) | `src/hirearchy/services/tests src/hirearchy/dispatch/tests tests/e2e/test_org_growth_0a3.py` |
| D4 | `docs(skill): root records the user's keep-as-is as their accept` | `src/hirearchy/skill/tests src/hirearchy/blueprint/tests/test_round_f_guidance.py` |
| E1 | `docs: README and ARCHITECTURE for phase 0a.3` (README gains `## Org growth: phase 0a.3` after the 0a.2 section; ARCHITECTURE 3.8, 3.21, 3.22, 3.29 and the Protocol sentence: 0a.3 adds `CaseAllowance`, `ProcessSpawner.spawn_detached` returns a pid, `StartupWatch` takes a pid, the private `RunCounter` and `BudgetPlanning` gain `stamps` and `client_round`) | `src/hirearchy/blueprint/tests/test_round_g_assistant.py src/hirearchy/blueprint/tests/test_examples.py tests/architecture` |

Sizes (production lines, estimates): A about 230, B about 40, C about 110, D about 60. FEATs: A (A1-A5), B (B1-B2), C (C1), D (D1-D4, E1).

**Testability.** Unit: the pure functions, the ceiling (fs worlds with written run logs and results), the request default over
`FixedAllowance`, the step, the blueprint texts, the watch over `FakeProcessTable`, the finding walk over fake checked versions, the tier
over the memory world. Contract suites: `CaseAllowance` (fake and reflection), `ProcessSpawner` (real and fake), `DeliverableChecks`,
`ServiceSteps`, `ReworkContext`. Integration: the fs worlds with real git (7.2), the in-process MCP server (4.5). End to end: the three E5
replays and the tree-kill test. Manual, never in CI: the kiro-cli reproduction.

## 15. Deviations from e5-decision.md and e5-gate.md, with reasons

1. **Top-ups are read by the highest ceiling.** A hand-down approves only what it hands beyond what was still committed. On E5's files a legacy
   explicit budget meant as "N more" reads as fewer approved runs (s2: 14, the gate's reading is 17), and the old default (the contract's 12
   again) reads as approved (s1: 17, the user approved 12 and then about 15). The files hold no record of the user's words; this is the only
   reading that is derivable and never lets the new default hand down runs the user did not approve (4.3). The replays still show no "exceeds".
2. **The default is capped at the contract's budget** (`min(left, contract)`). A rework never gets more than a fresh request would; the rest of
   a larger approval stays approved for later.
3. **With nothing left, the request is refused** (`NO_RUNS_LEFT`) instead of "the reply says so". A task cannot be sent with 0 runs, and
   sending the round anyway would spend runs the user did not approve. The refusal names the top-up and the call that sends it
   (`budget=<need>`); an explicit `budget` is never refused by this rule. The gate said its proposals add no refusal; this one is reachable only
   by omitting `budget` when the approval is spent.
4. **The approved number is not in the head of the sentence.** It is in the overspend sentence and in the top-up advice, where root acts on
   it. The decision's form for the head ("N runs used: U by the user's requests, R by your relayed rework") does not include it, and on legacy
   chains (deviation 1) it would put a number in root's mouth that the user did not say.
5. **The head keeps today's text when the chain has no relayed rework**, and the old overspend sentence is kept when the approval equals the
   contract's budget. Both are then exactly the new rule's meaning, and the golden and test churn stays where the meaning changed.
6. **The client round is "1, plus 2 per agent below the owner"**, SKILL.md's existing rule, and not the estimate's rework sum plus 1. One
   formula serves the plan (blueprint) and the reply (reflection), which cannot share the template model. For E5's team both give 5; for
   the research team it gives 7 instead of 6.
7. **The default planned budget is unchanged** (estimate + 25%). The decision makes the larger budget a suggestion the user may refuse, so it
   is carried by the warning, not imposed by the default. Consequence: the shipped templates and the example (22, 19, 23, 23 runs) now show
   the `budget-tight` warning, because they do not cover a client round; the assistant offers the number.
8. **The `budget-tight` threshold is `max(ceil(estimate * 1.10), estimate + round)`**, so no warning of today disappears.
9. **The startup error no longer names the exit code.** The scheduler is not this process's child, so its code is unknowable; the log tail
   still shows why, and the exit marker decides "it had nothing left to do".
10. **`ChildRegistry` is kept**, though nothing is adopted any more. Removing it is a behaviour-free refactor across `daemon` and `app`; it is
    backlogged.
11. **The launcher's pid comes from the pid file once it names the pid the intermediate reported.** Reading the pid file alone would accept
    a stale file of a dead scheduler and could not tell an exit at once from a slow start.
12. **`RETIRE_UNRATED` is not changed** (F-E5-4 names P2-UNRATED only); the same sentence fits it (backlog).
13. **F-E5-5 covers the file equal to a delivery.** A file equal to no checked version still "differs" from the newest pair, which can be a
    relayed rework's (E5 s3's memo 1, the writer's unreviewed rework); naming the newest delivery that is not relayed is backlogged.
14. **F-E5-7 is fixed at the tier lookup, not at the trace stamp.** `traces` is not a dependency of `services`, and the stamp rule serves every
    message; the fallback applies the stamper's own batch rule.
15. **Correction of the brief:** `status` embeds no case total (4.4); it changes only through the deliverable note.
16. **Beyond 0b 4.2's two names**, 0a.3 adds `Case.relayed_returned`, `user_granted`, `user_ceiling`, `user_committed` and `user_approved`: the
    user's spend needs the relayed tasks' returns, and the warning needs the user's approval. 0b reuses them (4.9).

## 16. What E6 must check

The changed texts are pinned by the exact strings of sections 4.4, 4.5, 5.2, 7.1, 7.2 and 8; E6's protocol amendment cites them.
1. **Deterministic, at the merged sha:** the replays `test_e5_s1_t6_...`, `test_e5_s2_t5_...`, `test_e5_s3_...` and
   `tests/e2e/test_scheduler_detach.py` pass (the decision's replays of s1 T6 for A and of the s3 kill for C).
2. **A, per stream:** every `case total:` line whose chain holds a relayed rework names the relayed runs apart; no "tell the user" fires on
   relayed runs alone; the turns in which the assistant asked the user to fund runs of its own relayed rework (E5 s1: 1; target 0); the turns in
   which it reported relayed runs as its own.
3. **A, the default:** root's human reworks sent without `budget`, with the budget each got and `left` at that moment; `TOPUP` replies, and
   whether the assistant asked the user with that number in the same turn; `NO_RUNS_LEFT` refusals and what followed; grants after a yes.
4. **B:** whether the assistant offered the plan's number at plan time (E5 0 of 3, E4 3 of 3) and what the user answered; the per-request
   budget each stream ran with; spend requests per memo and the turns they took.
5. **C:** schedulers still running when a turn ended (E5 1 of 16), and for each its `scheduler.exit`; runs in flight at a turn's end and their
   `run.end`; any `run.orphan` (E5 1). Every `scheduler.start` has a `scheduler.exit` by the stream's end. On a Linux harness, whether a
   subreaper is an ancestor (6.3's declared limit).
6. **F-E5-4:** relayed verdicts the assistant recorded before an admitted `define_service`, and P2-UNRATED refusals per relayed rework (E5:
   1 each, 3 of 3).
7. **F-E5-5:** after each relayed rework, the deliverable notes: `relayed` lines naming the delivered task, and `differs` lines naming a relayed
   task for a file the user has (E5: 16; target 0 when the file equals a delivery).
8. **F-E5-7:** rework delegations made inside a human rework that carry `source: human`, of all such delegations (E5 9 of 11; target all),
   noting those whose revised task had no trace.
9. **L-ASIS:** keep-as-is answers recorded as a human-tier accept on the kept version's task (E5 0 of 3).
10. **Unchanged guarantees:** P1, P2, P3 and P4 measurements as in E5 (10.5), so that 0a.3 shows no regression in what E5 found working.
11. **Models:** every seat on claude-sonnet-5.5 at high effort, as in E5.

## 17. Out of scope, backlog and risks

Out of scope: proposal D (rejected, D-E5-4); a credit for a run the product lost (deferred, D-E5-3); everything of 0b except what 4.9 lists;
F-E5-6 (no change recommended); F-E5-8 (no product guard).

Backlog: remove `ChildRegistry` and the `Children` port (deviation 10); the same relayed-verdict sentence in `RETIRE_UNRATED` (12); a `differs`
line that names the newest delivery that is not relayed (13); the ambiguous trace stamp of a delegation while the agent holds a blocked task
of another case (14); README's "Services and reflection" wording of the case total, if E6 shows the assistant misreads it.

Risks: the TOPUP advice and the plan's number still act through what the assistant says and the user accepts (LLM behaviour, measured by E6
items 3 and 4); a lead that keeps unreturned runs inflates `user_committed` and so shrinks `left` (conservative); the Linux subreaper limit
(6.3); the reproduction could show another kill mechanism (6.1's stop condition).
