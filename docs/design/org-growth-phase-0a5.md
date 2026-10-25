# Org growth, Phase 0a.5: the batch after E7 (technical design)

Status: design, revision 1 (no review yet). Branch `feat/org-growth-phase-0a5` off `main` `3a0bf49` (the E7 study commit; product code identical
to `18a4531`); worktree `/Volumes/workspace/hirearchy/.worktrees/org-growth-0a5`. Baseline at `3a0bf49`: `skills/hirearchy/SKILL.md` has 125 lines
and md5 `fd89a7fda55b8f342cf0306173c363fb`; `ROOT_INSTRUCTIONS` is not edited by this batch (under its 2 700 cap).

Sources of truth, read in full for this design:
- `docs/research/org-growth/phase-0a4/0a5-brief.md` ("the brief") and `docs/research/org-growth/phase-0a4/e7-decision.md` ("the decision";
  binding: D-E7-2 and D-E7-3).
- `docs/research/org-growth/phase-0a4/e7-gate.md` ("the gate"), sections 4 (proposals A, B, C, F-E7-7, F-E7-8) and 5 (what 0b reads).
- `studies/E7-org-growth-0a4-recheck/STUDY.md` (F-E7-1 to F-E7-11) and its `evidence/` (s1, s2, s3; committed in `3a0bf49`, so the replays read
  them from the repository, read-only).
- `docs/design/org-growth-phase-0a4.md` ("0a.4"), `org-growth-phase-0a3.md` ("0a.3": 3, 4.3-4.5, 5, 12, 17), `org-growth-phase-0a2.md` ("0a.2": 6.1-6.3
  for P3 and the settled rule, 20 for D19); `ARCHITECTURE.md` (R1-R13, 2.3, 3.10, 3.22) and `docs/refactor-principles.md`.
- `docs/research/` is untracked and absent from the worktree: it is read at `/Volumes/workspace/hirearchy/docs/research/`.

Abbreviations: `SRC` = `src/hirearchy`, `TESTS` = `tests`, `EV7` = `studies/E7-org-growth-0a4-recheck/evidence`, `EV6` =
`studies/E6-org-growth-0a3-recheck/evidence`, all in the worktree. `#N` is call N of a stream's `assistant-tool-calls.txt`. Ids are shortened to
their last 4 characters where the stream is clear (`c671` = `20261025T075038845671-root-c671`). Every function named below was read in the worktree
at `3a0bf49`. "D" below always means "a human rework handed the default's 1 run while nothing was left of the user's approval" (defined in 3).

## 1. Overview

E7 failed "no regression" in one stream, s2, on spend. Its memo 1 got a human rework (c671) without `budget` while nothing was left of Lena's 12
runs, so the default handed it 1 run. The product counted that run as the user's approval (12 became 13), the top-up asked Lena for only the rest
of the round (1 run), her yes approved 13 in her words and 14 in the product's, and the case ended at 14 with no overspend sentence. The other
items are smaller: a relayed verdict settled a result's questions for the client (C), an accepted `blocked` rework stayed open in the lead's trace
stamping (F-E7-7), two lead prompts after a `blocked` result lost their playbook and regression list (F-E7-8), and no assistant offered the plan's
budget number (B). Everything stays derived: no ledger, no stored state, no new message field, no new event, no new refusal, no new runtime
dependency.

| Item | Decision in this design | Where |
|---|---|---|
| A2 (D-E7-2) | **Ship.** One derived marker, computed where the ceiling is computed (`reflection._cases._spend`): a human rework of 1 run whose `left` at its send, recomputed from the files, was 0 or below. Its term raises no ceiling, and later terms leave its run out of what they count as committed until its result gives it back. Grants (notes) always count. `Case.unapproved_reworks` exposes the marker. | 4.2, 4.3 |
| A1 (D-E7-2) | **Ship.** For a marked rework the top-up counts the rework's own run in the ask and in the grant: `ask = need - budget - spare - held + 1`, `grant = need - budget - held + 1`, with one new sentence in `{left}`. E7 s2 #20 asks for 2 and grants 2. `_default_budget` keeps handing 1 run. | 4.4, 4.5 |
| C (D-E7-2) | **Ship.** `open_client_items` settles a result's items only by a human-tier verdict (or the user's own rework of the task), through `rated(case, task, human=True)`. `delivered_unrated` and progress's `no feedback yet` keep reading any tier. | 5 |
| F-E7-7 (D-E7-2) | **Ship (today's behaviour is not correct).** A `blocked` task its assigner has moved past (`mail.moved_past`: the user's accept after the block is one case) is no longer the assignee's open work. One pure rule, `mail.still_open`, is read by the trace stamper's `open-task` rule and its mirror in `services`. The record stays as the lead wrote it (single writer): the result stays `blocked`, and so do `Case.state` and the progress line. | 6 |
| F-E7-8 (D-E7-2) | **Defect, fixed test-first.** The owner's prompt sections pick "the services it is working on" from `TaskQuery.open_tasks`, which leaves out a task with a `blocked` result. They now read `mail.still_open` too, so a `blocked` request the client has not moved past keeps its `# Playbook` and `# Regression list`. | 7 |
| B (D-E7-3) | **Ship, product form.** When the plan has no error and a service's budget covers one pass and one internal rework but not a client round (the `budget-tight` warning's client-round form), the PLAN FOR YOU block ends with `Use {N} runs per request (covers one round of your questions or a rejection), or keep {M}?`. One pure predicate feeds the warning and the line. SKILL.md line 39 replaces its own offer with what to do on the answer. | 8, 9 |

Out of scope (the decision and the brief): proposal D (rejected), Phase 0b, any study, and the small items D-E7-4 leaves unchanged (F-E7-3, F-E7-5,
F-E7-6, F-E7-9, F-E7-10, F-E7-11).

## 2. Technology stack (locked)

Python 3.11 and the existing packages only (`mcp`/FastMCP, PyYAML; Textual untouched), the standard library, uv, pytest, `mypy==2.4.0 --strict`,
`import-linter==2.15`, `scripts/static_checks.py`, `scripts/check.sh`. No new runtime dependency, no new package, no new dependency edge between
packages (`reflection`, `traces` and `services` already depend on `mail`), no new Protocol method, no new file kind in an organization, no new
message field, no new event kind. One new public pure function (`mail.still_open`), one new `Case` field (`unapproved_reworks`), one new keyword of
`reflection.rated` (`human`). Strict TDD (R11) under the owner's test policy (15).

## 3. Shared definitions (each defined once)

| Name | Home | Definition |
|---|---|---|
| hand-down, ceiling, committed at `h` | `reflection._cases._spend` | As 0a.3 3 and 0a.4 5.2, unchanged: for a hand-down `h` (a user task or a user grant), committed at `h` = the user's charged runs before `h` plus what earlier hand-downs handed down that those runs did not use and their results (before `h`) did not return, at least the runs. |
| left at `h` | `reflection._cases._spend` | `max(per_request, ceiling so far) - committed at h`: what `CaseAllowanceOf.left` returns for a rework sent at `h`, recomputed from the files the case reads now. `per_request` is the current contract's `budget`. |
| D: the default's run with nothing left | `reflection._cases._spend`, exposed as `Case.unapproved_reworks` | A hand-down `h` that is a task with `source == "human"`, a `revises`, `budget == 1`, and left at `h` of 0 or below. Only a human client's case (root) has one. |
| a D's run still out at `h` | `reflection._cases._spend` | 1 for a D sent before `h` unless its latest result came before `h` with `budget >= 1` (it gave its run back), else 0. |
| still open (for its assignee) | `mail.still_open(task, latest, received)` | A received task with no result, or whose latest result is `blocked` and whose assigner has not moved past it (`mail.moved_past`, 0a.1). |
| client-round offer | `blueprint._budgeting.round_offer(total, est_total, round_runs)` | `est_total + round_runs` when `round_runs > 0` and `est_total <= total < est_total + round_runs`, else None: the number the `budget-tight` warning's client-round form gives. |
| human-tier verdict | `kernel.verdict_tier`, `Verdict.tier` | Unchanged: a feedback note root sent with `source="human"` after the user's yes. |

## 4. A (D-E7-2): the 1-run default with nothing left

### 4.1 Decision

Both parts ship, together, and A2 comes first in the build because A1 reads its marker.

The two parts constrain each other through the grant. Under A2 the default's run is no approval, so after the user's yes to A1's ask the product
can only learn that the user approved that run from the grant root then sends: the files hold root's hand-downs and never the user's words
(0a.3 4.3). Three ways to pair them were compared on E7 s2's numbers (the round 5, 9 runs used, 3 held, the rework's 1 run, so A1 asks 2):

| Pairing | What the user approved (A1) | Product's approval after the grant | Team holds | Verdict |
|---|---|---|---|---|
| A2 literal, grant = the round's rest (1) | 14 | 13 | 5 (the round) | rejected: when the team uses the round (14 runs), `OVER_APPROVED` says 14 is "more than the 13 the user approved", which is false |
| A2 lifted by any later user grant in the D's interval, grant 1 | 14 | 14 | 5 | rejected: it reads E7 s2's recorded files (a 1-run grant after Lena's yes to 1 run, approval 13) as 14, so A2 removes nothing in the case that motivated it; and the decision says the default's run "is left out of `user_ceiling`" |
| **A2 literal, grant = the ask (2)** (chosen) | 14 | 14 | 6 (one more than the round) | consistent: the product's approval equals the user's yes in 0a.5 flows, and recorded s2 reads 13, as Lena approved |

The chosen pairing keeps 0a.3 and 0a.4's rule that a grant after the user's yes raises the approval by exactly `{ask}`. Its cost is one run handed
down beyond the round in the D case (Deviation 1). That run is no cost while unused: `user_spend` counts grants only once they are charged. If the
team spends it, the overspend sentence fires, which is then true.

### 4.2 The marker (A2's identification of the default, from the files)

The files hold every fact the default used. The rework's own header holds `budget`, `source` and `revises`. Root's `sent/`, root's received
results and the team's run-log names hold everything that `left` was computed from at its send. `_spend` already walks the hand-downs in id order
and computes "committed at `h`" for each one, and the approval so far is `max(per_request, ceiling so far)`. So the marker is one condition inside
that loop. It needs no stored state and no new message field: `left` at `h` is recomputed from today's files every time the case is read.

Where the recomputed `left` differs from what `_default_budget` saw at the send, it is lower, because "committed at `h`" can only be higher:
- runs of another case that fall in a reopened window are counted (0a.3 limit 2);
- a result that came after `h` is not read at `h`, even when an earlier result of that task (which may have returned runs) existed then (0a.3
  4.3: "can only raise a ceiling");
- the window the case reads now always covers everything before `h`: its end is a result or a task that comes after `h`.

So every real default with nothing left is marked. A 1-run rework sent when exactly 1 run was left can be marked too, which is the conservative
direction: the approval stays lower and the sentence fires sooner (declared limit 2). The one reading the other way is a run credit written after
the rework for a run before it (a throttle credit). There a real default can read as within the approval, and its term then equals the approval and
raises nothing either. An explicit `budget=1` sent while nothing was left is marked, because the files cannot tell it from the default (0a.3 limit 1,
now read the other way; declared limit 1).

**Why a grant root sends after the user's yes still counts.** A grant is root's own act, and root makes it only after asking. SKILL.md line 72 says
to ask before a rework that would pass the approved budget, and the `TOPUP` reply says `Ask the user now ...; on yes, grant N`. The product reads
root's hand-downs as the user's yes, as it reads `source="human"` as root's word (0a.3 4.3). The default's run is the product's own act: nobody asked
anyone, so it carries no yes. Excluding grants would drop the approvals users give (the review's mandatory check 3), so the marker never applies
to a note. A grant root sends without asking (F-E7-5) still counts: that is 0b's OQ-1, not 0a.5.

### 4.3 A2: the ceiling (`SRC/reflection/_cases.py:_spend`, `SRC/reflection/api.py`)

`_spend` gains the keyword `per_request: int` (the current contract's `budget`, which `DerivedCaseHistory.cases` already reads as `contract`) and
returns `_Spend.unapproved: tuple[str, ...]`. The ceiling loop (today's lines 52-58) becomes:

```python
    users = [t for t in tasks if t.source != "relayed"]
    ceiling, unapproved = 0, []
    for h in sorted([*users, *grants], key=lambda m: m.id) if human else []:  # the hand-downs, oldest first
        runs = sum(1 for s in charged if s < h.id[:21] and not in_relayed(s))
        handed = sum(t.budget for t in users if t.id < h.id) + sum(g.budget for g in grants if g.id < h.id)
        back = sum(min(r.budget, t.budget) for t in users if t.id < h.id and (r := results.get(t.id)) is not None and r.id < h.id)
        back += sum(to_user[t.id] for t in tasks if t.id < h.id and (r := results.get(t.id)) is not None and r.id < h.id)
        committed = runs + max(0, handed - runs - back)  # what the user's requests used or the team held just before h
        if h.type == "task" and h.source == "human" and h.revises and h.budget == 1 and max(per_request, ceiling) - committed <= 0:
            unapproved.append(h.id)  # D-E7-2 A2: the default's 1 run with nothing left (or an explicit 1 then): nobody approved it
            continue
        out = sum(1 for d in unapproved if not ((r := results.get(d)) is not None and r.id < h.id and r.budget >= 1))  # their runs not given back
        ceiling = max(ceiling, max(0, committed - out) + h.budget)
```

`committed - out` takes a D's run out of what a later term counts as committed, whether that run is still held or already charged. While the team
still holds an unused run of the other hand-downs, this equals the literal "left out of the `handed` sum" (E7 s2 at its grant: 9 used, 12 - 9
held, so 13 - 1 = 12 either way). It differs only when the D's run and every other held run were used before the later term; there the literal
form would count the D's run again through `runs` (Deviation 2). The `max(0, ...)` is a guard only: `handed - back` holds every D whose run is
still out, so the difference can go below 0 only when runs a relayed result carried back to the user (`to_user`) exceed what the other hand-downs
left out, which no stream had.

`DerivedCaseHistory.cases` passes `per_request=contract.budget` and fills `Case(..., unapproved_reworks=spend.unapproved)`. In
`SRC/reflection/api.py`, `Case` gains a defaulted field (so every hand-built `Case` keeps today's meaning):

```python
    unapproved_reworks: tuple[str, ...] = ()  # D-E7-2 A2: the human reworks handed the default's 1 run while nothing was left (or an explicit 1 then, which the files cannot tell apart), oldest first: no approval of the user's; () for an agent client
```

`user_approved` is unchanged in code. Its docstring adds: "`case.user_ceiling` leaves out the default's 1-run hand-downs with nothing left
(`case.unapproved_reworks`), so only root's own hand-downs raise it (D-E7-2 A2)". `Case.user_ceiling`'s comment adds the same clause. `user_spend`,
`user_cost`, `user_committed`, `user_held`, `case_spend` and the agent client's case are unchanged: A2 changes only the ceiling. `CaseAllowanceOf`
is unchanged in code. After a D its `left` is one lower than at `18a4531`, because the D's run is committed and not approved. Its docstring says so.

`SRC/reflection/_reports.py` is unchanged in code. `case_total` already compares `user_cost` with `user_approved`, so the overspend sentences now
fire on the new approval (4.7). The docstring of `ServiceReports.case_total` (`api.py`) adds: "the default's 1-run hand-down with nothing left is no
approval of the user's (D-E7-2 A2)".

### 4.4 A1: the top-up (`SRC/reflection/_steps.py:_top_up`)

```python
    def _top_up(self, task: Message) -> str:
        case = self._history.case_of(task)
        contract = self._catalog.read_contract(task.to, task.service) if task.service else None
        if case is None or contract is None or case.client_kind != "human":
            return ""
        need = client_round(self._agents, task.to)
        own = 1 if task.id in case.unapproved_reworks else 0  # D-E7-2 A1: the rework's own run is beyond the user's approval too
        if task.budget >= need and not own:
            return ""
        approved = user_approved(case, contract.budget)
        spare = max(0, approved - user_committed(case))  # the case now holds this rework's budget too
        if need - task.budget - spare + own <= 0:
            return ""  # what is approved and unused covers the round: root may grant it without asking
        held = user_held(case, task)
        ask = need - task.budget - spare - held + own
        still = HELD.format(held=held, revised=task.revises) if held else ""
        if ask <= 0:
            return still  # the team holds the rest of the round: nothing to ask the user (D-E6-2)
        left = DEFAULT_RUN if own else SOME_LEFT.format(spare=spare, approved=approved) if spare else NOTHING_LEFT
        return TOPUP.format(
            budget=task.budget, need=need, owner=task.to, left=f"{still} {left}" if still else left, ask=ask, grant=need - task.budget - held + own,
        )
```

The rework reads the marker from its own case and never recomputes it, so there is one definition of D (I-A4). `grant - ask = spare`, as in
0a.3, and in the D case `spare` is 0 (D means nothing was left), so the grant equals the ask (4.1). Without `own` every line computes today's
values, so a rework that is not D keeps today's text byte for byte.

`SRC/services/_request.py:_default_budget` is unchanged in code: with nothing left it still hands 1 run, the minimum a task carries, so the lead
can read the rework. Holding the rework back or refusing it would be a new refusal. Its docstring and its last comment change: "1 when nothing is
left; that run is beyond the user's approval, so the reply's top-up asks for it too (D-E7-2 A1)". Root's `request` tool docstring, the CLI help and
`HELD` are unchanged, so no MCP surface golden moves. `ServiceSteps.rework_step`'s docstring (`api.py`) adds: "when the rework is the default's 1
run with nothing left (`Case.unapproved_reworks`), the top-up asks for that run too, and its grant is what it asks".

### 4.5 Texts

- `TOPUP`, `HELD`, `NOTHING_LEFT`, `SOME_LEFT`: unchanged templates.
- New, `SRC/reflection/_steps.py`: `DEFAULT_RUN = "Nothing was left of the runs the user approved for this case when this rework was sent: its own run is beyond them, and the ask includes it."` It takes `NOTHING_LEFT`'s place in `{left}` for a D, after `HELD` when the team holds runs.
- The overspend sentences (`OVER_CONTRACT`, `OVER_APPROVED`, `RELAYED_*`) are unchanged texts. They print in more cases (4.7).

### 4.6 Code sites

`SRC/reflection/_cases.py` (`_Spend.unapproved`, `_spend(..., per_request)`, the ceiling loop, `cases()` passes `contract.budget` and fills the
field); `SRC/reflection/api.py` (`Case.unapproved_reworks`, the comments and docstrings of `user_ceiling`, `user_approved`, `case_total`,
`rework_step`); `SRC/reflection/_steps.py` (`DEFAULT_RUN`, `_top_up`); `SRC/reflection/_allowance.py` (docstring); `SRC/services/_request.py`
(docstring and comment only). `SRC/reflection/_reports.py`: no code change.

### 4.7 Replays (`TESTS/e2e/test_org_growth_0a5.py`, over the E7 kit of 15)

s2, memo 1. Chain: 3ca4 (budget 12), c671 (human, `revises` 3ca4, budget 1). Grant 68df (1 run, to `lead`, in c671's interval). Results: d5c7
(3ca4, `blocked`, no budget), 64cb (c671, `done`, no budget), a112 (3ca4, `done`, after #24). Runs: 9 before c671 (lead 5, writer 2, reviewer 2),
none between c671 and 68df, 5 from 07:51:41 to 07:53:22. Round of `lead`'s team: 1 + 2 x 2 = 5.

| Moment (cut, inclusive) | At `18a4531` (recorded) | 0a.5 |
|---|---|---|
| just before c671 (`20261025T075038845670`) | `left` 12 - 12 = 0: the default hands 1 | unchanged: `case_allowance.left("lead", SERVICE, 3ca4) == 0` |
| **#20**, c671 sent (`20261025T075038845671`) | approval 13 (ceilings 12, 9 + 3 + 1); committed 13; spare 0; held 13 - 9 - 1 = 3; ask 5 - 1 - 0 - 3 = 1, grant 1. Case total `case total: 9 runs used of 13 handed down (contract: 12 per request)` | c671 is marked (left 0, budget 1): `case.unapproved_reworks == (c671,)`, approval 12. `user_cost` (open) 9 + (13 - 9) = 13 > 12, approval equals the contract, no relayed task, so `OVER_CONTRACT`. own 1: ask 5 - 1 - 0 - 3 + 1 = **2**, grant **2** |
| after the grant 68df (`20261025T075138446837`) | approval 14 | grant term: committed 9 + (13 - 9) = 13, less c671's run still out 1, plus 1: approval **13**; `user_cost` (open) 13: no sentence |
| **#24** (`20261025T075347939000`: 64cb in, a112 not) | approval 14, cost 14: `case total: 14 runs used of 13 handed down (contract: 12 per request)`, no sentence | approval 13, cost 14 (done): `OVER_APPROVED`, with `topped` ", plus 1 approved beyond it" |
| end of the stream | `19 runs used: 14 by the user's requests, 5 by your relayed rework ...-37b7; 19 handed down ...` plus `RELAYED_SPEND` | the same head, then `OVER_APPROVED` (14 of 13), then `RELAYED_SPEND` |

The exact texts the replays assert:
- #20, `service_reports.case_total(c671)`: `case total: 9 runs used of 13 handed down (contract: 12 per request). This case now exceeds the per-request budget of 12: tell the user.`
- #20, `service_steps.rework_step(c671)`: `This rework has 1 run(s), and a rework of this team needs about 5 (1, plus 2 for each agent below lead). The team still holds 3 of the user's runs for 20261025T074451197103-root-3ca4; the rework can use them. Nothing was left of the runs the user approved for this case when this rework was sent: its own run is beyond them, and the ask includes it. Ask the user now for 2 more run(s), with that number; on yes, grant 2: send(to="lead", budget=2, body=<why>) (CLI: hirearchy send lead "<why>" --budget 2).`
- #24, `service_reports.case_total(c671)`: `case total: 14 runs used of 13 handed down (contract: 12 per request). The user's requests now cost 14 runs, more than the 13 the user approved for this case (contract: 12 per request, plus 1 approved beyond it): tell the user.`
- #24: `user_approved(case, 12) == 13`, `user_cost(case) == 14`, `case.user_ceiling == 13`.

What it means live:
- **The recorded flow.** In s2 Lena said yes to "1 more run, which would take this memo to 13" and root granted 1. The product now reads 13, as she
  did, and tells root at #24 that the case passed it. The assistant had said "2 over" by itself in T5.
- **The 0a.5 flow.** The assistant would ask for 2 ("14 against your 12"). On Lena's yes root grants 2 and the approval reads 14. The rework used 5
  runs, so the case ends at 14 of 14, the gate's "With A1, Lena's one yes approves 14". The Summary cell still fails (the gate's common limit).

**E6's numbers move where 0a.4's replays pinned 0a.3's limit 1** (s3, memo 1: 4a3e 16, bc02 human 1, 5d4a relayed 6, 9a5b human 1). The marker reads
the same files differently:
- bc02 is marked: left at its send was 16 - 16 = 0.
- 9a5b is not marked: left was 16 - 11 = 5, with 0a.4's return attribution.

| 0a.4 replay | `18a4531` | 0a.5 | Why |
|---|---|---|---|
| B-1, after bc02 (`20261024T171425096624`) | `user_approved(case, 16) == 17` | **16** | bc02 is the default with nothing left; the step stays the `HELD` sentence (own 1: ask 5 - 1 - 0 - 11 + 1 < 0) |
| B-2, before 9a5b (`20261024T172453163610`) | `left == 6` | **5** | approval 16, committed 11 |
| B-2, at 9a5b (`20261024T172453163611`) | approved - committed `== 5`, `user_spend == 12`, step `""` | **4**, 12, `""` | spare 4 still covers the round with 9a5b's 1 run |

E5's replays (`TESTS/e2e/test_org_growth_0a3.py`) do not move: no E5 human rework carries 1 run (aae2 12, 6c4f 5, c209 3). Neither do E7 s1 and s3,
whose human reworks carry 7, 5, 3, 5 and 7, 5, 5, 5 (STUDY M-A-6).

### 4.8 Zero and empty cases

| Case | Result |
|---|---|
| an agent client | no ceiling, no marker (`unapproved_reworks == ()`); `_top_up` returns `""` (today) |
| a hand-built `Case` | `unapproved_reworks == ()`: today's figures |
| no human rework, or the head | never marked (the head has no `revises`) |
| a human rework of 2 runs or more | never marked: root's explicit hand-down beyond the approval raises it (0a.3 4.3) |
| a 1-run human rework sent with 1 or more left (the default's `min(left, B) == 1`, or an explicit 1 within the approval) | not marked; its term equals the approval and raises nothing (today) |
| a 1-run human rework sent with 0 or less left (the default, or an explicit `budget=1`) | marked: no term of its own; later terms leave its run out until its result gives it back |
| a relayed rework, a rework without `source` (sent before 0a) | never marked (not the default's case: `_default_budget` applies to `source="human"` only) |
| a grant (a note) | never marked; its own term counts its budget |
| two Ds in one chain | both marked; each run counts in `out` while not given back |
| a D whose result came back with `budget >= 1` before a later term | that term leaves nothing out for it |
| `_top_up`, a D whose team holds the whole round without its run (`held >= need`) | `HELD` alone, as today; the case total then says the case exceeds the approval by that run (limit 5) |
| `_top_up`, a D with nothing held | ask = grant = `need` (E7-shaped: 5) |
| `_top_up`, a D of an owner with no agent below (`need` 1) | ask 1, grant 1 (today `""`: the rework's own run is the round, and it is unapproved) |
| `_top_up`, not a D | today's text and numbers, byte for byte |
| `_default_budget` | unchanged: `min(left, B)`, 1 when `left <= 0`, the contract's when `left` is None or unreadable |

### 4.9 Tests to write first (each RED before its code)

- `SRC/reflection/tests/test_cases.py`, fs world with run logs and results (`ceiling_world`, `_support`):
  - nothing left, a 1-run human rework: marked, `user_ceiling == 12`, `user_approved == 12`. This replaces
    `test_limit_1_with_nothing_left_a_rework_of_one_run_raises_the_approval_by_one` (14 Rule A2);
  - then a grant of 2 in its interval: approval 14;
  - the same with the rework's run and every held run charged before the grant: still 14 (Deviation 2);
  - a grant of 1 (E7 s2's): 13, and after 5 charged runs and a `done` result `case_total` prints `OVER_APPROVED` 14 of 13;
  - 1 left: not marked, approval 12;
  - an explicit `budget=1` with nothing left: marked (limit 1);
  - `budget=2` with nothing left: not marked, approval 14;
  - the marked rework's result returns 1 before a later grant: nothing left out at that grant;
  - two Ds in a row: both marked;
  - an agent client and a relayed 1-run rework: not marked;
  - `user_committed`, `user_spend` and `user_held` are unchanged by the marker (the same shapes, compared with a run of the old loop's numbers
    pinned as literals).
- `SRC/reflection/tests/test_pure_functions.py`: a hand-built `Case` has `unapproved_reworks == ()`, so `user_approved` is today's.
- `SRC/reflection/tests/test_steps.py` and `test_contract_service_steps.py`:
  - the D form exactly, with `HELD` in `{left}` (round 5, 2 held: ask 3, grant 3) and without it (ask 5, grant 5);
  - `held >= need`: `HELD` alone;
  - `need` 1 and a D: ask 1;
  - a 1-run rework sent with 1 left: today's text.
- `SRC/mcp_server/tests/test_service_tools.py` and `SRC/cli/tests/test_service_commands.py`: the nothing-left pins take the D form (14 Rule A1).
- `SRC/app/tests/test_wire_cli.py::test_the_request_command_prints_the_step_of_the_runtime` (14 Rule A1).
- Replays: 4.7 (`test_a1_e7_s2_20_...`, `test_a2_e7_s2_24_...`, and the grant's cut), and the three 0a.4 replays changed as 4.7 states.

## 5. C (D-E7-2): only the user's verdict settles a result's questions

### 5.1 Decision

`open_client_items` (`SRC/reflection/api.py`) returns no items for a service request only when the client gave a **human-tier** verdict on that
delivery or on a later rework of it, or when root's own human rework revises that task. This is the rule 0a.1 DR-17, 0a.2 6.1 and 6.3 ("only the
user's own judgement settles a finding") and the protocol's D19 ("no human rework of the task and no human-tier verdict on its delivery") already
state. Today it reads `rated(case, task)`, whose verdicts are of any tier. `delivered_unrated` (P2-UNRATED's gate) and progress's `no feedback
yet` keep any tier: there root's own relayed verdict is meant to count (0a.3's text: "on a relayed rework the user never saw, your own ...
settles it"). Nothing is refused: the change only keeps a path withheld longer.

### 5.2 Code

```python
def rated(case: Case | None, task: Message, *, human: bool = False) -> bool:
    """Has the client given a verdict on this delivery or on a later rework of it? Any tier; with ``human``, only the user's own (``tier ==
    "human"``, D-E7-2 C). An earlier verdict does not count (pure)."""
    if case is None:
        return False
    step = next((i for i, t in enumerate(case.tasks) if t.id == task.id), 0)
    return any(v.step >= step and (not human or v.tier == "human") for v in case.verdicts)
```

`open_client_items`: `(task.service and rated(case, task, human=True))`. Its docstring: "... the user's own rework of the task or the user's
verdict (human tier) on the delivery or on a later rework of it settles questions and notes together; the assistant's own (relayed) rework or
verdict settles neither (0a.1 DR-17; D-E7-2 C)". `questions_open`'s docstring follows. `delivered_unrated` and `SRC/progress/_lines.py` (`no
feedback yet`) call `rated(case, task)` as today. The deliverable checks get the change through `questions_open` (`withheld`). Code sites:
`SRC/reflection/api.py` only.

### 5.3 Replay: E7 s1 6920 (`TESTS/e2e/test_org_growth_0a5.py`)

s1, memo 1. Chain: 5efc (12), 5e3e (human 7), 6920 (relayed 6, the injected task), 066f (human 5, `revises` 5e3e). 6920's result c3d0 is `done`,
`budget: 1`, with 4 items, each naming C6 or C2: 4 questions. Verdicts: R1 #30 (human reject on 5e3e), #39 1b8f (relayed reject on 6920, step 2),
#47 9496 (human accept on 066f, step 3).

| Cut (inclusive) | `18a4531` | 0a.5 |
|---|---|---|
| after #39 (`20261025T071711763028`) | `questions_open(6920, c3d0, case, root_sent) == 0`; 6920's line `... artifacts: lead/writer/work/memo-2026-10-05.md, lead/reviewer/work/review-memo-2026-10-05.md ...` | **4**; the line contains `artifacts withheld (ask first). 4 questions for the client: ask the user before you copy or deliver.` and no `no feedback yet` (`rated` of any tier still holds) |
| after #47 (`20261025T072107513137`) | 0, `artifacts: ...` | 0, `artifacts: lead/writer/work/memo-2026-10-05.md, lead/reviewer/work/review-memo-2026-10-05.md`, no `questions for the client` in 6920's line |

The replay asserts on 6920's own line, the first line of `progress(org, task_id=6920)`. The deliverable note below it depends on whether E7's
sandbox folder exists on the machine, so it is not asserted. E7's copy #46 (07:20:03) took 066f's own result 1c9d, which has no block, so no copy
would have changed (the gate: "decided no cell").

### 5.4 Zero and empty cases

| Case | Result |
|---|---|
| no case (a one-off task, or `case` None) | only a human rework of the task settles (today) |
| no verdict | open (today) |
| only relayed or agent-tier verdicts at or after the task's step | **open** (today: settled) |
| a human verdict at or after the step | settled (today) |
| a human verdict on an earlier step only | open (today) |
| a human rework of another task of the chain (066f revises 5e3e, not 6920) | does not settle 6920 (today's rule, now visible: limit 6) |
| `failed` result, no block, a block of notes only | as today (`ClientItems()`, or notes only and no flag) |
| `delivered_unrated`, `no feedback yet` | any tier, unchanged |

### 5.5 Tests to write first

- `SRC/reflection/tests/test_pure_functions.py`:
  - `rated(case, task, human=True)` per tier (human, relayed, agent) and per step;
  - `rated(case, task)` unchanged (the existing `test_rated_is_unchanged_after_the_move` and `test_a_relayed_verdict_counts_as_rated` stay);
  - `open_client_items` and `questions_open` stay open under a relayed accept and a relayed reject at the task's step and at a later step, and
    settle under a human one.
- `SRC/progress/tests/test_lines.py`: a done result with two questions and a relayed reject shows `artifacts withheld (ask first)` and the flag,
  and no `no feedback yet`.
- `SRC/reflection/tests/test_deliverable_checks.py`: a `differs` file whose newest pair has only a relayed verdict is shown `path withheld: ask
  first`.
- Replay 5.3.

## 6. F-E7-7: a `blocked` rework the user accepted is no longer open work

### 6.1 Who owns the task's state (single writer)

Nothing stores a task's state. It is derived from two kinds of message files, and each kind has one writer:
- **the assignee's results.** Only the lead writes results on a task it received, through `dispatch`'s reporter into `mail` (R9: `mail` owns the
  mailbox files).
- **the assigner's verdicts and reworks.** Only root writes them, through `services` (`feedback`, `request`) and `dispatch`.

`mail` owns the rule that reads both, in its `api.py`: `TaskQuery` derives open tasks, and `moved_past(task, blocked, received)` (0a.1) says
whether the assigner of a `blocked` task has moved past it. `budget.ReserveAllocationPolicy.budget_to_return` reads `moved_past` to stop counting
such a task as busy.

So "closing" the task cannot mean writing anything.
- A `done` result on the lead's behalf would be a report the lead never made, and a second writer of the lead's `sent/`.
- A state file would be stored state.

The fix is in the readers. In s3, after Lena's accept dd46, the budget already treated d9bc as moved past, so the lead's runs could go back. The
trace stamper's `open-task` rule (`traces/_lookup.py:open_task_traces`) and its mirror (`services/_rework.py:_open_trace`) did not: they kept d9bc
open, so the lead held two open traces (09df's case and a443) and its next delegations got `trace_rule: ambiguous` (9838, 59a9, fe01, 7459). Today's
behaviour is therefore a disagreement between readers of the same state, not a design choice.

### 6.2 Decision and rule

New pure function in `SRC/mail/api.py`, beside `moved_past`, exported in `__all__`:

```python
def still_open(task: Message, latest: Message | None, received: Sequence[Message]) -> bool:
    """Does the assignee of ``task`` still owe a report on it (pure)? ``latest``: its latest result, None when it has none; ``received``: what the
    assignee received. Yes without a result, and with a ``blocked`` one its assigner has not moved past (``moved_past``: a later task of the same
    sender revises it or what it revised, or the sender gave a verdict on its chain after the block; the user's accept of what it delivered is one
    such verdict, D-E7-2 F-E7-7). No after a ``done`` or ``failed`` result."""
    if latest is None:
        return True
    return latest.status == "blocked" and not moved_past(task, latest, received)
```

Readers:
- `SRC/traces/_lookup.py:MailboxTraceLookup.open_task_traces`: `received = self._mail.received(a)`, then `[t.trace for t in received if t.type ==
  "task" and still_open(t, latest.get(t.id), received)]`. `TraceLookup.open_task_traces`'s docstring (`traces/api.py`): "... has not finished (no
  result, or a `blocked` one its assigner has not moved past: `mail.still_open`)".
- `SRC/services/_rework.py:ServiceReworkContext._open_trace`: the same expression (it mirrors the stamper's rule, 0a.4 Deviation 10). `_tier` is
  unchanged (limit 8).
- `SRC/reflection/_sections.py` (F-E7-8, 7.2).

The rule is `moved_past`, not only "a human-tier accept" (Deviation 5). It is the one rule the product already has for "the assigner no longer waits
on this blocked task". Narrowing it here would leave the budget and the stamper disagreeing on the same task in the other moved-past shapes: a later
rework, or any verdict after the block. The human accept the decision names is one of those shapes.

What does not change, and why:
- **the record.** d9bc's latest result stays da3c, `blocked`: only the lead writes it.
- **`Case.state`.** It stays `blocked`, and so does the progress line `blocked: Questions for the client:.`. Progress keeps listing the task, since
  blocked tasks are listed always. 0b's view decides how to show such a case (18).
- **`Case.open_tasks` and `user_held`.** 0a.4 B keeps "missing or `blocked`". `moved_past`'s rework branch would close the revised task the
  moment root sends the rework, which is exactly when `user_held` must count it.
- **the lead's state section `Tasks you reported blocked (not final)`** (`prompts/_tasks.py`). It keeps listing every blocked task, so the lead
  still re-reports a head after its rework, which 0b pins (gate 5 item 7).
- **`TaskQuery.open_tasks`** (no result at all). Its callers (attention, retirement, the reporter, the dashboards) count unanswered work.

No refusal is added, and no write.

### 6.3 Code sites

`SRC/mail/api.py` (`still_open`, `__all__`); `SRC/traces/_lookup.py`; `SRC/traces/api.py` (docstring); `SRC/services/_rework.py` (`_open_trace`
and its docstring).

### 6.4 Replay: E7 s3 d9bc (`TESTS/e2e/test_org_growth_0a5.py`)

s3, the lead's received tasks at the cut `20261025T084354396140` (just before 9838), with `inflight={"lead": [dd46, a443]}`, the batch of run
`lead@20261025T084331384527` (its log: "2 message(s)", both from root):
- 09df (17e3 `done`), 62a5 (c2f9 `done`), 5834 (f639 `done`): closed;
- d9bc: latest result da3c (`blocked`, 08:40:45), then dd46 (08:43:26), root's `feedback: accept`, `source: human`, replying to d9bc after da3c;
- a443: no result.

| Reader | `18a4531` | 0a.5 |
|---|---|---|
| `runtime.trace_lookup.open_task_traces("lead")` | `[09df, a443]` (as traces) | `["20261025T084326297193-root-a443"]` |
| `runtime.trace_lookup.context_trace("lead")` | `(None, "ambiguous", ["20261025T082434523661-root-09df", "20261025T084326297193-root-a443"])` (the batch holds both traces too) | `("20261025T084326297193-root-a443", "open-task", [])` |
| `mail.still_open(d9bc, da3c, lead's received)` | (no such function) | False |
| `runtime.rework_context.work_tier("lead")` | None | None (a443 carries no tier: the gate's "they lost no tier") |
| memo 1's `Case.state`; d9bc's progress line | `blocked`; starts `"Memo for 2026-10-05: add Summary line (C9)" [service weekly-meeting-memo v1]: blocked: Questions for the client:.` | unchanged |

Live, 8 of s3's 10 `ambiguous` stamps would have resolved: 9838 and 59a9 to a443, fe01 and 7459 to a74a (each by `open-task`), and the results
answering them (e4c7, 3bcb, 8377, 579e) by `link`. The two runtime notes (8051, 63ed) come before dd46 and stay `ambiguous`.

### 6.5 Zero and empty cases

| Case | `still_open` / `open_task_traces` |
|---|---|
| no result | open (today) |
| `done` or `failed` latest result (also one that superseded a `blocked` one) | closed (today) |
| `blocked`, nothing after it (s1's faaa, before its re-report) | open (today) |
| `blocked`, then a grant note (no `feedback`) | open (today: s1's 0036) |
| `blocked`, then a verdict of its sender on its chain (the user's accept dd46; also a reject or a relayed verdict) | **closed** (today: open) |
| `blocked`, then a later task of its sender that revises it or what it revised | **closed** (today: open; the new task is open in the same trace, so the trace does not change) |
| `blocked`, a verdict before the block, or a verdict or rework from another sender | open (`moved_past`) |
| an agent with no received task; root; the runtime; a non-agent | `[]` (today) |
| a still-open task without a trace | None in the list: the `open-task` rule fails as today |

### 6.6 Tests to write first

- `SRC/mail/tests/test_still_open.py`: every row of 6.5 over plain `Message`s, in the style of `test_moved_past.py`.
- `SRC/traces/tests/test_contract_trace_lookup.py` (every implementation):
  - a `blocked` task whose sender accepted it after the block is not in `open_task_traces`, and `context_trace` then returns the other open
    task's trace with `open-task`;
  - a grant note after the block leaves it open (the existing blocked-task tests stay).
- `SRC/services/tests/test_service_rework_context.py`: `work_tier` with an accepted `blocked` human task and a fresh relayed task in another trace
  gives `relayed`; with the accept missing, two traces, and no batch gives None (as today).
- Replay 6.4.

## 7. F-E7-8: lead prompts after a `blocked` result lost their playbook and regression list

### 7.1 Root cause (a defect)

`SRC/reflection/_sections.py:OwnerPromptSections.prompt_sections` shows `# Playbook` and `# Regression list` for each service in `working =
{t.service for t in self._tasks.open_tasks(addr) if t.service}`. `TaskQuery.open_tasks` is "the tasks `addr` received that it has not answered
with a result", so any result answers, a `blocked` one included.

In s1:
- the lead reported memo 2's human rework faaa `blocked` (ed63, 07:25:52; run `lead@20261025T072530214455`, whose prompt still had both sections);
- root sent the grant 0036 (3 runs, F-E7-5);
- the lead's next runs `lead@20261025T072625893903` (batch: 0036) and `...072718351439` (batch: the reviewer's result 1df0) worked faaa's re-check.

At those two runs the lead had no unanswered task (fb17 had 82a1, faaa had ed63), so `working` was empty. With no new request and no rejection in
the batch there was no digest either, and the sections were `# Your services` alone. Both prompts still said, in `# Your state`, "Tasks you
reported blocked (not final): ... you may re-report it once the blocker is resolved". The lead then re-reported faaa `done` (adc0 supersedes ed63).

The same state is open everywhere else in the product: the trace stamper ("no result or a blocked latest result"), `Case.open_tasks`, `summarize`
("open (incl. blocked)"), and the `ServicePromptSections` docstring ("the playbook of each service it has an open request for"). The reviewer task
076d sent from the first of those runs still quoted R1, but the product's own guarantee had lapsed.

### 7.2 Fix

`working` reads the same rule as the stamper, `mail.still_open`:

```python
        received = self._mail.received(addr)
        latest = latest_results(self._mail.sent(addr))
        working = {t.service for t in received if t.type == "task" and t.service and still_open(t, latest.get(t.id), received)}
```

`OwnerPromptSections` replaces its collaborator `tasks: TaskQuery` with `mail: MailboxReader`, in the same position. It used `TaskQuery` only for
`open_tasks`, and `reflection` already depends on `mail`. Two construction sites follow: `SRC/app/wire_reflection.py:_sections` passes
`b.get(MailboxReader)`, and `SRC/reflection/testing.py:_world` passes `d.mail`. The `TaskQuery` import is removed where it becomes unused.
`ServicePromptSections.prompt_sections`'s docstring (`api.py`): "... the playbook of each service it still owes a report on (no result, or a
`blocked` one its client has not moved past: `mail.still_open`) ...".

A request the client moved past is then not "working", as today. In s3 after dd46, the lead's sections came from a443's open request (the same
service), so nothing changes there.

### 7.3 Replay: E7 s1 (`TESTS/e2e/test_org_growth_0a5.py`)

`runtime.service_prompt_sections.prompt_sections("lead", org.messages("lead", "inflight"))`, in two cases:
- at the cut `20261025T072625893903` with `inflight={"lead": ["20261025T072621895274-root-0036"]}`;
- at the cut `20261025T072718351439` with `inflight={"lead": ["20261025T072718311804-lead.reviewer-1df0"]}`.

In each case the sections contain a line starting `# Playbook: weekly-meeting-memo (` and the line `# Regression list: weekly-meeting-memo (the
client's rejections, verbatim)`, with R1 (case 5efc, verdict 905b). At `18a4531` they contain neither. The kit writes no playbook file, so the
playbook heading reads `v0`. The replay asserts the headings only. Measured live, this makes s1's regression list in lead prompts after the reject
16 of 16 (E7: 14 of 16).

### 7.4 Zero and empty cases

| Case | Sections |
|---|---|
| an agent that owns no service | `""` (today) |
| owned services, no open or blocked request, no new request or rejection in the batch | `# Your services` alone (today) |
| a `blocked` request the client has not moved past, nothing else open | **`# Playbook` and `# Regression list` (when it has assertions) for its service** (today: the listing alone) |
| a `blocked` request the client moved past (an accept, a verdict, a later rework), nothing else open | the listing alone (today) |
| a `blocked` request of a service with no regression yet | `# Playbook` only (the regression section is `""` without assertions, today) |
| a new request or a rejection in the batch | as today (the reflect section and its regression list) |

### 7.5 Tests to write first

- `SRC/reflection/tests/test_prompt_sections.py`:
  - an owner whose only request has a `blocked` result, with a batch holding only a grant note, gets `# Playbook: <svc>` and, after a human
    rejection on an earlier case of the service, `# Regression list: <svc>`;
  - the same request after the client's accept on it after the block gets the listing alone.
- `SRC/app/tests` (the wiring tests that build the sections): `wire_reflection` passes the `MailboxReader`.
- Replay 7.3.

## 8. B (D-E7-3): the plan asks whether to use the plan's number

### 8.1 Decision

When a plan has no error and a service's per-request budget covers one pass and one internal rework but not a round of the user's questions or a
rejection, the PLAN FOR YOU block ends with one line, after `Nothing is created or started until you approve. Reply 'approve', or tell me what to
change.`:

`Use {N} runs per request (covers one round of your questions or a rejection), or keep {M}?`

- **`{N}` is the number the plan's own warning gives:** the estimate plus one client round, `est_total + round_runs`, which is 16 in every E5-E7
  plan (11 + 5). This is how the design reads the brief's "the plan's own estimate number". The estimate alone (11) would contradict the line's own
  "covers one round", and the decision's "up to about 4 more runs per request" is 16 - 12.
- **`{M}` is the service's per-request budget in this plan:** its own `budget`, else the plan's number within the cap. It was 12 in E5-E7.
- **"For a service with a human client"** holds for every blueprint service. Root defines services only for its direct reports
  (`_service_rules.py`: "root defines services only for its direct reports"), so the client is always root, and no further check is needed.
- **When to show it.** The trigger is exactly the `budget-tight` warning's client-round form, read through one predicate (`round_offer`). The
  slack form (`total < ceil(est * 1.10)` with the round covered) gets no line: its round is covered, so the question would be false.
- **Plans with errors** (the `DRAFT - NOT READY` block, which the assistant must not show) get no line.
- **Two or more services carrying the warning** get one line per service, in blueprint order, each naming its service (Deviation 7):
  `Use {N} runs per request for {name} (covers one round of your questions or a rejection), or keep {M}?`.
- **No new refusal, and no change to any issue.** The warning text stays byte-identical (8.4).

### 8.2 Code and texts

- `SRC/blueprint/_budgeting.py`, a module-level pure function beside `SLACK` and `TIGHT`:
  ```python
  def round_offer(total: int, est_total: int, round_runs: int) -> int | None:
      """The plan's number for a service whose per-request budget ``total`` covers one pass and one internal rework (the estimate ``est_total``) but
      not one round of the client's questions or a rejection (``round_runs``): ``est_total + round_runs``; None when ``total`` is below the estimate
      (``budget-low``), already covers the round, or there is no round (no agents). The ``budget-tight`` warning's client-round form and the plan's
      budget question both read it (pure)."""
      return est_total + round_runs if round_runs > 0 and est_total <= total < est_total + round_runs else None
  ```
- `SRC/blueprint/_service_rules.py`: the `elif total < est_total + round_runs:` branch becomes `elif (offer := round_offer(total, est_total,
  round_runs)) is not None:`. Its message uses `{offer}` where it now computes `{est_total + round_runs}`, so the text is byte-identical. The order
  of the checks is unchanged (`budget-cap`, `budget-low`, then the client-round form, then the slack form).
- `SRC/blueprint/_plan_texts.py`:
  ```python
  BUDGET_QUESTION = "Use {n} runs per request (covers one round of your questions or a rejection), or keep {m}?"  # D-E7-3: the block's last line
  BUDGET_QUESTION_FOR = "Use {n} runs per request for {name} (covers one round of your questions or a rejection), or keep {m}?"  # one per service when several
  ```
- `SRC/blueprint/_userplan.py:TextUserPlan.render`: after the final `L.append("Nothing is created ..." if not errs else "Cannot apply yet.")`, `if
  not errs: L += self._budget_question(bp, agents)`. The new method:
  ```python
      def _budget_question(self, bp: Mapping[str, object], agents: Sequence[Agent]) -> list[str]:
          """D-E7-3: the yes/no line that ends the block when a service's budget per request covers one pass and one internal rework but not a round
          of the user's questions or a rejection (``round_offer``, the ``budget-tight`` warning's client-round form): one line, or one per service
          naming it when several do; none for a plain task and without agents."""
          if not services_of(bp) or not agents:
              return []
          est, round_runs = self._budgets.estimate(agents)["total"], self._budgets.client_round(agents)
          offers = [(name, n, m) for name, m in self._budgets.service_budgets(bp, agents).items() if (n := round_offer(m, est, round_runs)) is not None]
          if len(offers) == 1:
              return [BUDGET_QUESTION.format(n=offers[0][1], m=offers[0][2])]
          return [BUDGET_QUESTION_FOR.format(n=n, name=name, m=m) for name, n, m in offers]
  ```
  `service_budgets` computes each service's `total` with the same `estimate`, `client_round` and cap as the rule (`_validator.py` passes
  `estimate(agents)["total"]` to the rules). So the line appears exactly when the warning does, in a plan without errors.
- `BudgetPlanning` (the private Protocol) is unchanged. The `propose_org` reply's `Next:` line is unchanged: what to do with the answer is SKILL.md's
  (9).

E7's three plans (cap 12, budget 12, estimate 11, round 5) carried the warning (STUDY M-B-2: 3 of 3), so under 0a.5 each would end with `Use 16 runs
per request (covers one round of your questions or a rejection), or keep 12?`. E5's blueprint shape (`e5_blueprint` in `test_services.py`) gives the
same line. Over E5-E7 the assistant offered the plan's number in 2 of 9 streams (the gate, B).

### 8.3 Zero and empty cases

| Case | Line |
|---|---|
| a plain task (no services) | none |
| no agents (`client_round` 0; the rule skips the budget checks) | none |
| any error in the plan (the draft heading, `Cannot apply yet.`) | none |
| `total < est` (`budget-low`, an error), `total > cap` (`budget-cap`, an error) | none (the plan has errors) |
| `est <= total < est + round` | the line, with `N = est + round`, `M = total` |
| `total >= est + round` (also the slack form of `budget-tight`) | none |
| no cap and no service budget | none: the default is at least `est + round` (0a.3 5.1) |
| several services, k of them at `est <= total < est + round` | k = 1: the decision's line; k >= 2: k named lines |
| more than `SHOWN_WARNINGS` warnings (the warning itself is cut from the block) | the line still appears |

### 8.4 Why no plan is newly refused and no issue changes

`round_offer` returns a number exactly when today's condition `est_total <= total < est_total + round_runs` holds inside the `elif agents:` branch
(`round_runs >= 1` there). The warning's text, level, code and path are unchanged, so `validate_corpus.json` stays byte-identical. No error is
added, and the block line is text, so `propose_org` and `apply_org` refuse exactly what they refuse today.

### 8.5 Tests and goldens

- `SRC/blueprint/tests/test_budget_planner.py`: `round_offer` for every row of 8.3 that it decides: `(10, 11, 5)` None, `(11, 11, 5)` 16,
  `(12, 11, 5)` 16, `(15, 11, 5)` 16, `(16, 11, 5)` None, `(12, 11, 0)` None.
- `SRC/blueprint/tests/test_services.py`: the existing `E5_TIGHT` texts stay; the warning still fires at `services[...].budget` and at
  `needs.budget_runs`.
- `SRC/blueprint/tests/test_plan_block.py`:
  - E5's blueprint (`e5_blueprint`): the block's last line is `Use 16 runs per request (covers one round of your questions or a rejection), or
    keep 12?`, right after the approve line;
  - a budget of 16: no line;
  - the same blueprint with an error (a missing criterion): no line;
  - a plain task: no line;
  - two services at 12: two named lines.
- `SRC/mcp_server/tests/test_blueprint_tools.py`: in `propose_org`'s text the line comes before the machine-marker line, so the assistant shows it.
- **Goldens:**
  - No existing golden carries the client-round warning: the 4 service templates and the shipped service example cover their round since 0a.3,
    and `second_half.json`'s plans have no `budget-tight` row. So **0 existing plan goldens are regenerated**.
  - **1 new golden** pins the whole reply: `TESTS/golden/test_golden_plans.py::test_propose_org_when_the_cap_keeps_the_service_below_one_client_round`.
    It takes `examples/blueprint-service.yaml` and replaces `budget_runs: 25` and `budget: 24 ` (each once, asserted) with 20. Estimate 17, round
    7, so the block ends with `Use 24 runs per request (covers one round of your questions or a rejection), or keep 20?`, written to
    `plans/example_blueprint-service_cap_20.txt` with `HIREARCHY_UPDATE_GOLDEN=1 uv run pytest tests/golden -k cap_keeps` and reviewed line by line.

## 9. SKILL.md and ROOT_INSTRUCTIONS

One line changes, by replacing text inside it, so the file stays at **125 lines**. 0a.4's lines 72, 92 and 100 are untouched, word for word.
`ROOT_INSTRUCTIONS` (`SRC/mcp_server/_instructions.py`) is not edited: its "settle its warnings (e.g. model policy) with the user" already covers the
question. The installed copy under `~/.kiro/skills/` is never touched. `whoami` and `status` show the stale-skill note to a user whose copy is older,
as for every SKILL.md change.

**Line 39** (section 1, item 6; B). Today:

```
   in one line what that risks and offer them the number the plan's warning gives (they may keep theirs). Nothing below claude-sonnet-5.5 at high effort is available: never offer a cheaper model, tiers to
```

New:

```
   in one line what that risks; the block's last line asks whether to use the plan's number: if they take it, set `needs.budget_runs` and any service `budget` to it and propose again (they may keep theirs). Nothing below claude-sonnet-5.5 at high effort is available: never offer a cheaper model, tiers to
```

Why: the block now asks, and the skill already says to show it exactly (line 48). The assistant's own offer would ask the same question twice, and
the skill did not say what to do with a yes. On a yes, the re-proposed plan (cap and budget 16 for E5-E7's team) carries no client-round warning,
so it has no line. Its new `plan_id` is shown and approved as SKILL.md 2.3 says for any revision.

Needles (`flat()`: lower-cased, whitespace collapsed):
- kept: `say in one line what that risks` (line 38's `say`, then line 39), `per-request budget is the plan's: the estimate + 25%, or more to cover
  one round of the user's questions or a rejection`, `about 2 runs per delegation + 1`, `never offer a cheaper model`, and every needle of lines 72,
  92 and 100 (0a.4 8);
- replaced, deliberately, in `SRC/blueprint/tests/test_round_f_guidance.py::test_skill_sizes_service_budgets_and_reads_the_send_reply`:
  `offer them the number the plan's warning gives` becomes `the block's last line asks whether to use the plan's number: if they take it, set
  \`needs.budget_runs\` and any service \`budget\` to it and propose again`. The docstring names D-E7-3. `grep -rn "offer them"` over
  `src/hirearchy/*/tests tests` finds no other pin.

## 10. Error handling

| Operation | Failure | Recoverable? | Caller receives | Logged |
|---|---|---|---|---|
| `_spend` (the marker, the ceiling) | none new: pure over what `cases()` already read | n/a | the case | none |
| `DerivedCaseHistory.cases` | a contract, a mailbox or a run-log directory cannot be read | as today | `OrgError`/`OSError` propagates as today | as today |
| `case_total` (the sentence on the new approval) | as today | as today | as today (empty for a task with no case or contract) | none |
| `_top_up` (A1) | the case, the contract or a run log cannot be read | yes | `""` through the MCP `_step` and the CLI `_step` (`OrgError`/`OSError`); the request is already sent and committed | the `tool.call` / `cli.command` event, as today |
| `_default_budget` | unchanged: an unreadable record gives the contract's budget | yes | the request is sent | none |
| `open_client_items`, `rated(..., human=True)` | none: pure | n/a | the items | none |
| `progress`, the deliverable checks | as today | as today | as today | as today |
| `still_open` | none: pure | n/a | a bool | none |
| `open_task_traces`, `context_trace`, `_open_trace` | a mailbox cannot be read | as today | as today (the stamper's and `work_tier`'s existing handling; `delegate` sends without a tier on `OrgError`/`OSError`, 0a.4 7.2) | as today |
| `prompt_sections` | a mailbox cannot be read | as today | propagates as `TaskQuery.open_tasks` did (it read the same boxes) | as today |
| `round_offer`, `_budget_question` | none: pure over computed budgets | n/a | lines (possibly none) | none |
| the replays | an evidence file is missing | fatal for the test | `pytest.fail` naming it, never a skip | test output |

## 11. Validation of external inputs

- **Message headers** (`budget`, `source`, `revises`, `status`, `feedback`): written by the runtime. `dispatch` refuses a task budget below 1 and an
  agent's own `source`; `kernel` parses `budget` as an int. The marker reads `budget == 1` as an int, `source == "human"` and a non-empty `revises`.
  A file that does not parse is skipped by the mailbox reader, as today.
- **Verdict tier**: `kernel.verdict_tier` of the note's runtime-stamped `source`. An agent cannot write root's verdict: `dispatch` stamps the sender.
- **`moved_past` inputs**: the assignee's own received box, messages the runtime delivered. A verdict counts only when its sender is the task's
  sender (`moved_past`), so an agent's note cannot close root's task.
- **The contract's `budget`** (`per_request`): at least 1 (`define_service` requires it).
- **Blueprint values** (B): validated by today's rules. The line appears only in a plan without errors, so `N = est + round >= 2` and `M >= est >= 1`
  are plain ints from the planner. A service name in the named form comes from a name that passed `NAME_RE`.
- **The E7 kit** (15): `cut` must be a 21-character stamp, and `inflight` ids must be in the organization at the cut (e5 kit rules).

## 12. Invariants and their owners

| # | Invariant | Owner | Why there |
|---|---|---|---|
| I-A1 | No default hand-down raises `user_approved`. With `left >= 1` it equals the approval (0a.3 I4); with nothing left its 1 run is left out, whether held or charged | `reflection._cases._spend` (the only computation of the ceiling) | D-E7-2 A2; replaces 0a.4 I6's "with nothing left, the floor raises it by 1" |
| I-A2 | A grant (a note root sends) always counts its own amount in the ceiling | `reflection._cases._spend` | the user's yes reaches the files only as root's hand-down (review check 3) |
| I-A3 | After a `TOPUP` and the user's yes, root's grant of `{grant}` raises `user_approved` by exactly `{ask}` (D case included: grant = ask) | `reflection._steps._top_up` with `_cases._spend` | the product's approval equals the user's yes; 0a.3 4.5 and 0a.4 5.3 |
| I-A4 | One definition of D: `Case.unapproved_reworks`, computed in `_spend`; `_top_up` reads it and never recomputes it | `reflection` | A1 and A2 must agree on every rework |
| I-A5 | `user_spend`, `user_cost`, `user_committed`, `user_held`, `case_spend` and an agent client's case total are unchanged by A | `reflection.api` | 0b reuses them (D-E5-6) |
| I-C1 | Only a human-tier verdict, or the user's own rework of the task, settles a result's client items; `delivered_unrated` and `no feedback yet` keep any tier | `reflection.api` (`open_client_items`, `rated`) | 0a.1 DR-17, 0a.2 6.3, D19 |
| I-F1 | A received task is the assignee's open work iff `mail.still_open`; the trace stamper's `open-task` rule, its `services` mirror and the owner's prompt sections read it, and the budget policy's reading (`open_tasks` plus `_blocked_not_moved_past`) agrees with it | `mail` (it derives task state from the messages) | one rule for one state |
| I-F2 | No package writes a result, a state or any file for a task it does not own: the latest result is the assignee's alone | `dispatch` (reporter) and `mail` (R9), unchanged | single writer |
| I-B1 | The plan's budget line appears iff the `budget-tight` warning's client-round form holds for a service and the plan has no error; one predicate feeds both | `blueprint._budgeting.round_offer` | the line must never contradict the warning |
| I-B2 | Every blueprint validates with the same issues as at `3a0bf49` | `blueprint` | no new refusal (review check 2) |
| I-0 | No new refusal, and no new failure of an existing call | every surface | the brief; the review's check 2 |

## 13. Golden impact (expected count)

**Regenerated: 0. New: 1** (`TESTS/golden/expected/plans/example_blueprint-service_cap_20.txt`, 8.5).

Each of these must stay byte-identical, and a commit stops until a diff is explained:
- `TESTS/golden/expected/` (plans, MCP surfaces, CLI, prompts, messages, events, kiro, charters, files, services);
- `SRC/blueprint/tests/golden/second_half.json` and `validate_corpus.json`;
- `SRC/progress/tests/expected/`, `SRC/reflection/tests/expected/` and `SRC/observability/tests/expected/`;
- `TESTS/testkit/expected_dash/`.

The reasons:
- **Plan goldens.** No golden plan has the client-round warning (8.5).
- **MCP surface.** No docstring of a tool changes (4.4).
- **Prompt goldens.** No golden prompt scenario has a `blocked` service request (`grep -n blocked tests/golden/test_golden_prompts.py
  tests/golden/scenarios.py`: only the status error text of `scenarios.py`).
- **`reflection` expected `sections_*`.** No story has a `blocked` result (`grep -n blocked SRC/reflection/tests/_stories.py`: none).
- **The `totals_*` stories and the progress scenario.** Their human reworks carry explicit budgets with runs left. The coder checks each one under
  14 Rule A2 before the A2 commit. Any 1-run human rework sent with nothing left there would be a deliberate regeneration, named with its count in
  the commit body.
- **Events.** `line_shapes.txt` pins key shapes, not trace values.

A deliberate regeneration uses `HIREARCHY_UPDATE_GOLDEN=1 uv run pytest tests/golden -k <test>`, reviews the diff, and names the file and the count
in the commit body.

## 14. Test-site rules (existing tests the changes touch)

- **Rule A2 (approval pins).** Sites: `grep -rnE "user_approved\(|user_ceiling|case_allowance.left|\.left\(" src/hirearchy/*/tests tests`. Every
  pin whose chain holds a human rework of 1 run sent with nothing left changes deliberately, and its docstring names D-E7-2 A2:
  - `SRC/reflection/tests/test_cases.py::test_limit_1_with_nothing_left_a_rework_of_one_run_raises_the_approval_by_one` becomes
    `test_a2_with_nothing_left_a_rework_of_one_run_raises_no_approval` (13 becomes 12);
  - `TESTS/e2e/test_org_growth_0a4.py::test_b1_...` (17 becomes 16), `::test_b2_9a5b_...` (5 becomes 4) and `::test_b2_just_before_9a5b_...`
    (6 becomes 5), each with 4.7's reason.

  Sentence pins (`grep -rnE "exceeds|more than the" src/hirearchy/*/tests tests`) are checked the same way. The MCP nothing-left test asserts its
  case total as a substring, and that substring still holds. The coder re-runs both greps at A2 and lists every kept site in the commit body.
- **Rule A1 (`TOPUP` pins).** Sites: `grep -rn "Ask the user now\|Nothing else is left\|This rework has" src tests`. A pin whose rework is a 1-run
  rework sent with nothing left takes the D form (4.5, `ask` and `grant` per 4.4):
  - `SRC/mcp_server/tests/test_service_tools.py::test_a_user_rework_with_nothing_left_is_sent_with_one_run_and_the_reply_asks_for_the_rest`
    (ask 4 becomes 5, grant 5, `DEFAULT_RUN`);
  - `SRC/cli/tests/test_service_commands.py::test_a_cli_rework_with_nothing_left_is_sent_with_one_run_and_prints_the_top_up` (the same);
  - `SRC/reflection/tests/test_steps.py::test_a_user_rework_of_one_run_asks_for_the_four_more_it_needs` (renamed `..._the_five_...`: ask 5,
    grant 5);
  - `test_steps.py::test_held_runs_that_cover_part_of_the_round_are_in_the_left_part_and_reduce_the_ask_and_the_grant` (contract 3, 1 used: left 0,
    so a D; ask 3, grant 3, `left` = `HELD` + `DEFAULT_RUN`);
  - `SRC/app/tests/test_wire_cli.py::test_the_request_command_prints_the_step_of_the_runtime` (contract 4, none used: left 0, so a D; held 4,
    need 5, so ask 1, grant 1). Its second assertion becomes the D text with `HELD` in `{left}`, and its docstring names D-E7-2 A1.

  Unchanged, checked: `test_steps.py`'s HELD-only tests (held 8 covers the round), the spare test (left 3), the CLI fake pin
  (`test_commands_services.py`, a fake step's text), and `test_service_tools.py`'s HELD test (its reply ends with `HELD`; its case total gains
  `OVER_CONTRACT` before it, and the test's assertions still hold).
- **Rule C.** Sites: `grep -rnE "relayed" src/hirearchy/{reflection,progress}/tests tests/e2e` near `questions_open`, `open_client_items`, `withheld`,
  `questions for the client`. A test whose questions are settled only by a relayed verdict changes to keep them open, and its docstring names
  D-E7-2 C. At `3a0bf49` none is known: the E4-E6 replays (A-1 to A-5, F-E4-4) have no relayed verdict before their cut on the flagged task.
- **Rule F.** `SRC/traces/tests`, `SRC/services/tests/test_service_rework_context.py`: every existing `blocked` test has no verdict or rework after
  the block, so it stays open and stays green. `SRC/reflection/tests/test_prompt_sections.py` and the contract suite of `ServicePromptSections` build
  the sections through `reflection.testing`, whose constructor call follows 7.2.
- **Rule S.** The one replaced needle of 9.
- No assertion is weakened. Each changed expectation names the decision it follows in its docstring.

## 15. Commit plan and test policy

Conventional commits, one logical change each, a failing test first (R11), `count.txt` raised where tests are added.

**FAST, per commit.** The commit's TARGETS, `tests/golden` and `tests/architecture --deselect tests/architecture/test_static_checks.py`, plus
`src/hirearchy/app/tests` when the commit touches `app/`, a Protocol docstring in an `api.py` or the wiring, then `uv run python
scripts/static_checks.py all`. All are run in `/Volumes/workspace/hirearchy/.worktrees/org-growth-0a5` with `UV_LINK_MODE=copy uv run pytest -q ...`.

**SCOPED.** ONE scoped union run at each FEAT's end and at each fix pass: the union of the FEAT's TARGETS plus `tests/e2e tests/golden
tests/architecture src/hirearchy/app/tests`, then `static_checks.py all`.

**FULL.** No full pytest and no `scripts/check.sh` during development. `UV_LINK_MODE=copy bash scripts/check.sh` (about 14 min, timeout 1800000 ms)
runs once, in the final validation, after the rebase onto the current `main`. The merge does not re-run it after a no-op rebase.

**Known flaky tests.** `given_queries-narrow-2-workflows` and the 2.5 s `READINESS_TIMEOUT`: retry the file once and note it.

| # | Commit | TARGETS |
|---|---|---|
| T0 | `test(testkit): the E7 replay kit` (`TESTS/testkit/e7_replay.py`: `EV7 = REPO / "studies" / "E7-org-growth-0a4-recheck" / "evidence"`, `SERVICE_NAME = "weekly-meeting-memo"`, `materialize` = `e5_replay.materialize(..., evidence=EV7, service=SERVICE_NAME)`; `TESTS/meta/test_e7_replay_kit.py`: s2 at c671's cut holds 3ca4 and c671 in root's `sent/`, d5c7 in root's `read/`, the 9 run logs (lead 5, writer 2, reviewer 2) and the contract with `budget: 12`; a missing evidence file fails) | `tests/meta/test_e7_replay_kit.py tests/meta/test_e6_replay_kit.py tests/meta/test_e5_replay_kit.py` |
| A2 | `fix(reflection): the default's 1-run hand-down with nothing left is no approval of the user's` (4.3; Rule A2; replay #24 and the grant's cut; the 0a.4 B-1 and B-2 changes) | `src/hirearchy/reflection/tests src/hirearchy/progress/tests src/hirearchy/mcp_server/tests tests/e2e/test_org_growth_0a5.py tests/e2e/test_org_growth_0a4.py tests/e2e/test_org_growth_0a3.py` |
| A1 | `fix(reflection,services): a top-up after the 1-run default asks for that run too` (4.4, 4.5; Rule A1; replay #20) | `src/hirearchy/reflection/tests src/hirearchy/services/tests src/hirearchy/mcp_server/tests src/hirearchy/cli/tests src/hirearchy/app/tests/test_wire_cli.py tests/e2e/test_org_growth_0a5.py tests/e2e/test_org_growth_0a4.py` |
| C | `fix(reflection): only the user's verdict settles a result's questions for the client` (5; replay 6920) | `src/hirearchy/reflection/tests src/hirearchy/progress/tests tests/e2e/test_org_growth_0a5.py tests/e2e/test_org_growth_0a4.py tests/e2e/test_org_growth_0a2.py tests/e2e/test_org_growth_0a.py` |
| F7 | `fix(mail,traces,services): a blocked task its assigner moved past is no longer open work` (6; replay d9bc) | `src/hirearchy/mail/tests src/hirearchy/traces/tests src/hirearchy/services/tests src/hirearchy/budget/tests tests/e2e/test_org_growth_0a5.py tests/e2e/test_org_growth_0a4.py tests/e2e/test_org_growth_0a3.py` |
| F8 | `fix(reflection,app): a blocked request the owner may still report keeps its playbook and regression list` (7; replay s1) | `src/hirearchy/reflection/tests src/hirearchy/prompts/tests src/hirearchy/app/tests tests/e2e/test_org_growth_0a5.py` |
| B1 | `feat(blueprint): the plan asks whether to use the plan's number when a request's budget covers no client round` (8; the new golden) | `src/hirearchy/blueprint/tests src/hirearchy/mcp_server/tests/test_blueprint_tools.py src/hirearchy/mcp_server/tests/test_tools_blueprint.py` |
| B2 | `docs(skill): the plan's budget question and what to do with the answer` (9, line 39) | `src/hirearchy/skill/tests src/hirearchy/blueprint/tests/test_round_f_guidance.py src/hirearchy/blueprint/tests/test_round_g_assistant.py src/hirearchy/mcp_server/tests/test_reclaim_tool.py` |
| E1 | `docs: README and ARCHITECTURE for phase 0a.5` (README `## Org growth: phase 0a.5` after 0a.4's, from section 1's table, nothing added to `## Services and reflection`; ARCHITECTURE 3.10 `still_open`, 3.14 the open-task rule, 3.22 `Case.unapproved_reworks` and `rated(..., human=)`, 3.32 the plan's budget question) | `src/hirearchy/skill/tests tests/architecture src/hirearchy/blueprint/tests/test_round_g_assistant.py src/hirearchy/blueprint/tests/test_round_f_guidance.py tests/e2e/test_round7.py` |

FEATs, a proposal for the plan: A (T0, A2, A1); C; F (F7, F8, in that order: F8 reads `still_open`); B (B1, B2); docs (E1). Sizes (production
lines, estimates): A about 30, C about 5, F about 20, B about 30, docs about 15.

Testability:
- **unit:** the pure functions (`still_open`, `round_offer`, `rated`, `open_client_items`); `_spend` over fs worlds with run logs and results;
  `_top_up` over the reflection worlds; the sections; the plan block;
- **contract suites:** `ServiceSteps`, `TraceLookup`, `ServicePromptSections`, `CaseAllowance`, over every implementation;
- **end to end:** the E7 replays (4.7, 5.3, 6.4, 7.3) and the changed E6 replays;
- **golden:** one new plan;
- nothing manual, nothing `integration`.

## 16. Deviations from e7-decision.md, e7-gate.md and the brief, with reasons

1. **A1's grant includes the default's run** (in the D case `grant = ask`, so the team holds one run more than the round). The decision fixes the
   ask ("asks for it too") and not the grant. With A2, the grant is the only record of the user's yes to that run. A grant of the round's rest alone
   leaves the approval one below the yes, and when the round is used `OVER_APPROVED` then says something false (4.1). The extra run is no cost
   while unused (limit 3).
2. **A2 leaves the default's run out of what later terms count as committed** (`committed - out`), not only out of their `handed` sum. The two are
   equal while the team holds an unused run of the other hand-downs (E7 s2, E6 s3). The literal form would count the run again once it is charged
   and the other held runs are used, and the default would then raise the approval after all.
3. **The marker reads an explicit `budget=1` sent with nothing left as the default.** The files cannot tell them apart (0a.3 limit 1). The
   decision's rule needs a marker from the files and no stored state.
4. **A2 changes three replays of 0a.4 and one test of 0a.3's limit 1** (4.7, 14 Rule A2). They pinned the growth that A2 removes.
5. **F-E7-7 closes the task by `mail.moved_past`, not only by the user's human-tier accept.** The accept is one of its shapes. It is the one rule
   for "the assigner moved past this blocked task" that the budget already reads, and the stamper and the budget should not disagree on the same
   task. "Closed" applies to the assignee's open work only (the stamper, its mirror, the prompt sections). The record, `Case.state`,
   `Case.open_tasks`, progress and the lead's blocked-task list are unchanged, for the single writer and for 0a.4 B (6.2).
6. **F-E7-8 changes `OwnerPromptSections`'s collaborator** from `TaskQuery` to `MailboxReader`. `TaskQuery` has no view of "blocked and not
   moved past", and adding a Protocol method would ripple into its contract suite, two fakes (`daemon.testing.FixedTasks`,
   `stalls.testing.CountingTasks`) and the facade.
7. **B with two or more services carrying the warning** shows one named line per service. The decision gives the one-service line, which is
   every E5-E7 plan, and a single line cannot carry two pairs of numbers.
8. **B shows no line on a plan with errors.** The draft block is "do not show this to the user".
9. **B reads "the plan's own estimate number" as the warning's number, estimate plus round** (16, not 11). The line says it "covers one round",
   and the decision says "up to about 4 more runs per request".
10. **B's plan goldens:** 0 regenerated and 1 new (8.5), where the brief expected regenerations. No existing golden has the warning.

## 17. Declared limits, out of scope, backlog and risks

Out of scope: proposal D (rejected, D-E6-4), Phase 0b, any study and its protocol, and the items D-E7-4 leaves unchanged.

Declared limits (each pinned by a test where one can show it):
1. An explicit `budget=1` sent while nothing was left is read as the default. If root had the user's yes for it and sent it as the rework's own
   budget, rather than as a grant, the overspend sentence can fire one run early. The product's own flow asks with `TOPUP` and records the yes as a
   grant.
2. The marker recomputes `left` from today's files: a reopened window (0a.3 limit 2), another case's runs, or a result that came later. Each can
   only make it lower than what the default saw. So a 1-run rework sent when exactly 1 run was left can be marked (the approval reads 1 lower, and
   the sentence fires sooner). The reverse needs a run credit written after the rework, and then the unmarked default raises nothing either (4.2).
3. In the D case the team holds one run beyond the round after the grant (Deviation 1). If the team keeps it unused, `user_committed` stays 1
   higher and a later rework's `left` reads 1 lower (conservative, like 0a.4 limits 5 and 6). If the team spends it, `OVER_APPROVED` fires, and it
   is true.
4. A grant root sends without asking (F-E7-5) still raises the approval (0b OQ-1).
5. While a D is open, its run counts in `user_cost`, so the case total says the case exceeds the approval by that run: E7 s2 #20 and E6 s3 #19. With
   A1's ask in the same reply that is the intended message. When the team holds the whole round without that run, the reply is `HELD` plus that
   sentence, and root tells the user that the default's run is beyond their approval.
6. C: a human rework that revises an earlier task of the chain does not settle a later relayed task's questions. 066f revises 5e3e, so 6920 stays
   withheld until the user's verdict at its step or later (#47). The settled rule (0a.1 DR-17) names a human rework of the task itself.
7. F-E7-7: an accepted `blocked` root task stays `blocked` in `progress`, in `Case.state` and in `summarize`'s open count, and progress lists it
   always. Only its assignee can change its record.
8. F-E7-7: `_tier` still reads "not answered finally" (a `blocked` result is not final). A moved-past `blocked` task can give its case's tier when the
   agent acts in that case again with no newer open task there.
9. F-E7-8: the lead's `# Your state` keeps listing every `blocked` task with "you may re-report it", moved past or not.
10. B acts through the assistant showing the block exactly (SKILL.md line 48). E7 s1 dropped the warning block once (F-E7-6). A user's "approve"
    with no answer to the question keeps their number.
11. B: a yes costs one more plan turn (propose again, a new `plan_id`, approve), as the decision says ("one plan-time question").

Backlog:
- progress's listing of a `blocked` root task its client moved past (age it out like a finished task), if 0b's view needs it;
- the lead's blocked-task list for moved-past tasks (it would change the head re-reports 0b pins);
- settling a later relayed task's questions by a human rework of an earlier task of its chain (limit 6), if a study shows a withheld path that held a
  copy;
- splitting `budget-tight` into two codes, if a reader other than the plan needs the client-round form.

Risks:
- The new overspend sentence at a D's send (limit 5) is new text in a reply root already reads. Its wording is today's `OVER_CONTRACT` or
  `OVER_APPROVED`.
- A1 asks the user for one more run than 0a.4 did, in every D case (E6: 1 case in 3 streams, bc02, since 9a5b had 5 left by 0a.4's attribution;
  E7: 1 in 3, c671). The 2 instead of 1 is what the user was in fact over.
- B adds one line to every plan whose cap is below the round (E7: 3 of 3), and a yes adds a turn. It is the owner's decision (D-E7-3), and the
  owner may override it.

## 18. What 0b and G0 must know

0b builds on 0a.5's `main` and re-pins its figures there (D-E7-7). These figures and texts move:

1. **`user_approved` and `user_ceiling` (A2).**
   - E7 s2 memo 1: **14 becomes 13**, Lena's D14 approval.
   - E6 s3 memo 1: 1 less than under `18a4531`'s rules (bc02; 0a.4 B-1 17 becomes 16). FEAT-012's recomputation must use 0a.5's rules.
   - E7 s1 (19, F-E7-9), E7 s3 and every E5 figure do not move: they have no 1-run human rework.
   - Gate 5 item 4's sentence "The view's `{a}` for s2's memo 1 is the product's 14, not Lena's 13" becomes "13, equal to Lena's".
   - Item 5's first input (OQ-1) no longer raises the approval.
   - Item 12's declared limit loses its default part: "a 1-run default with nothing left" no longer raises the approval. An explicit budget set
     while runs are held, and a grant without a yes, still do.
2. **The cost alarm (D-E5-6, `user_cost / user_approved`).** E7 s2 memo 1: **14/13 = 1.08** (was 14/14 = 1.00). It stays below 1.25, so no alarm.
3. **The overspend sentences.**
   - E7 s2 prints `OVER_CONTRACT` at #20 (13 of 12, c671 open), and `OVER_APPROVED` at #24 and on the final total (14 of 13, `topped` ", plus 1
     approved beyond it").
   - E6 s3 prints `OVER_CONTRACT` at #19 (17 of 16, bc02 open).
   - E7's S17-4a ("0 printed") becomes 1 due and printed in s2 on a replay.
4. **`CaseAllowance.left` after a D:** 1 lower. E6 s3 just before 9a5b: 6 becomes 5.
5. **`TOPUP` (A1).** E7 s2 #20: ask 1 becomes **2**, grant 1 becomes **2**, with the new `DEFAULT_RUN` sentence. 0b reads M-A-8 and M-A-9 against
   that `{ask}` and `{grant}`. In a D case the team then holds one run beyond the round (limit 3).
6. **Questions open and withheld paths (C).** A result whose case has only relayed verdicts at or after its step stays flagged. E7 s1 6920 is
   flagged from #39 to #47, where it was settled at #39. 0b's counts that read `questions_open` or `open_client_items` move with it. `rated` without
   `human` and `delivered_unrated` are unchanged, and gate 5 item 12's rule (0b's "without a verdict" never reads `reflection.rated`) still holds.
7. **Open work and trace stamps (F-E7-7).**
   - `mail.still_open(d9bc, ...)` is False after dd46. 0b's D4 may read it as "closed by the client" (gate 5 items 6 and 14).
   - `Case.state` is still `blocked` for s3 memo 1, so D4's input from `reflection` is unchanged. The choice of reading is 0b's.
   - Stamps of new messages change: in an E7-s3-shaped stream, 8 of 10 `ambiguous` stamps become `open-task` or `link`. E7's recorded files keep
     their stamps.
   - The tier is unchanged in E7 (a443 and a74a carry none).
8. **Lead prompts (F-E7-8).** While a `blocked` service request the client has not moved past is the lead's only open work, its prompts carry
   `# Playbook` and `# Regression list`. s1 becomes 16 of 16 (E7: 14 of 16). Lead prompt bytes (S17-6) grow in such runs.
9. **The PLAN FOR YOU block (B).** It gains a last line wherever the client-round `budget-tight` warning holds: E7's three plans (and E5's
   blueprint shape) give `Use 16 runs per request (covers one round of your questions or a rejection), or keep 12?`. G0's protocol must say how D-OFFER counts a product line (the gate,
   B: "D-OFFER reads a product text as no offer"). Its T-PLAN and T-WARN pins must add the line.
10. **SKILL.md.** Line 39 is replaced (9). 125 lines; 0a.4's lines 72, 92 and 100 word for word; a new md5. 0b's re-wrap of lines 98-100 (gate 5
    item 3) must be planned on 0a.5's file and keep line 39's new text. G0's harness pins the new md5.
11. **Replays.**
    - `TESTS/testkit/e7_replay.py` exists (T0). FEAT-013 may reuse it for its manifests; its manifests stay 0b's.
    - `TESTS/e2e/test_org_growth_0a5.py` holds the E7 replays of 4.7, 5.3, 6.4 and 7.3.
    - 0a.4's B-1 and B-2 expectations are 16, 4 and 5 (4.7).
12. **Unchanged, for 0b's re-pinning:** `user_spend`, `user_cost`'s definition, `user_committed`, `user_held`, `case_spend`, `Case.open_tasks`,
    `Case.state`, `delivered_unrated`, `regressions`, every `HEAD`/`HEAD_SPLIT` text, `RELAYED_*`, `HELD`, the `budget-tight` text, and the
    template budgets.
