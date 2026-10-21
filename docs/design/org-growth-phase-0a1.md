# Org growth, Phase 0a.1: the fix batch before Phase 0b (technical design)

Status: design, revision 2 (answers the design review of revision 1: section 20). Branch `feat/org-growth-phase-0a1` off `main` `d8e35f2`;
worktree `/Volumes/workspace/hirearchy/.worktrees/org-growth-0a1`.
Baseline (`.agents/tasks/baseline.md`): 13 749 passed, 4 skipped, 3 deselected, 1 xfailed; mypy strict clean; import-linter 49 + 1 contracts kept;
`skills/hirearchy/SKILL.md` 125 lines.

Sources of truth:
- `/Volumes/workspace/hirearchy/docs/research/org-growth/phase-0a/go-no-go-0b.md` (binding): section 2 items 1-5 and section 5 (decisions); item 6 (study E4) is not built here.
- `studies/E3-org-growth-0a-live/STUDY.md`: findings F-E3-1..11.
- `docs/design/org-growth-phase-0a.md` (the "0a design"): sections 5.2 and 5.3 change (section 16 below).
- `/Volumes/workspace/hirearchy/docs/research/org-growth/08-synthesis.md` ("08"), decisions D1-D5; `.../phase-0a/followups.md` item 1.

`SRC` = `/Volumes/workspace/hirearchy/.worktrees/org-growth-0a1/src/hirearchy`, `TESTS` = `/Volumes/workspace/hirearchy/.worktrees/org-growth-0a1/tests`.
Every function named below was read in the worktree at `d8e35f2`.

## 1. Overview

E3 showed that the 0a code it exercised works, and that three guarantees rested on the assistant following skill text it had loaded. 0a.1
moves those guarantees into data and into the tool replies the assistant reads when it acts, and fixes two older accounting bugs that 0b's
alarms would inherit. Seven work packages:

1. **The client's yes is in the data.** A `criterion` on the rejection itself is always relayed tier; only a `confirms` link note is human
   tier. Rule (c) admits a criterion only when it was added by a root amendment **and** a human-tier link names it. Unconfirmed links and
   amendments are marked "(not confirmed)". Root's `feedback(reject)` reply names the next step; the `define_service` reply after an
   unconfirmed reject says its criteria are not client-confirmed.
2. **Client questions before delivery.** `progress` flags a done result that carries a `Questions for the client:` block; a relayed
   `request(revises=...)` repeats the revised result's questions; templates and skill say "before delivery". Nudges only.
3. **Overspend on runs used.** `reflection.case_spend(case)` (runs used, plus runs still out while open) replaces "runs handed down" in
   the `case_total` warning; 0b's cost alarm reuses it.
4. **Rule (c) visible to the owner.** Reflect step 3, the amendment note and the `revise_playbook` docstring name the confirmed
   amendments; the reject preamble applies to rules without client evidence. Three e2e gate cases.
5. **A superseded `blocked` task stops holding budget.** `mail.moved_past` is the derived test; `budget_to_return` uses it; `progress` says
   "0 returned (kept by <agent>)".
6. **Skill size.** SKILL.md stays at 125 lines; no needle changes.
7. **Stale installed skill.** Root's `whoami` and `status` say when `~/.kiro/skills/hirearchy/SKILL.md` differs from the packaged skill;
   README notes that a global skill shadows a profile's `skill://` resource.

Nothing is stored that was not stored before: no new file, ledger, frontmatter key or MCP argument.

## 2. Technology stack (locked)

Python 3.11, the existing packages only (`mcp`/FastMCP, PyYAML, Textual untouched), uv, pytest, `mypy==2.4.0 --strict`, `import-linter==2.15`,
`scripts/check.sh`. No new runtime dependency, no new package, no new dependency edge (section 12). Strict TDD (R11); one logical change per
commit; `scripts/check.sh` green after each.

## 3. Item 1: the client's yes in the data (F-E3-1, F-E3-6)

### 3.1 Decisions

**Tier of a link (derived).** In `SRC/reflection/_cases.py:DerivedCaseHistory._verdict` the candidates for a verdict's effective link stay
"the verdict note's own `criterion`" and "every link note that replies to it". Their tiers change:
- the verdict note's own `criterion` has tier `"relayed"`, whatever the note's `source` (today: `verdict_tier(note)`, so `human` for E3's
  `af5f`);
- a link note keeps `verdict_tier(link)` (`human` only when root sent it with `source="human"`, which the skill does only after the yes).

The winner rule is unchanged (latest human-tier candidate, else latest of any tier), so `Verdict.links` / `links_tier`, `regressions` and
`Assertion.link` need no code change: E3's R1 becomes `link == "unconfirmed"` and renders "(not confirmed)". The verdict's own tier
(`Verdict.tier`) is unchanged: a rejection is still the user's judgement; only *what it is about* needs the yes. This is 08 4.1.1's "A link
the assistant records without a yes is `relayed`", and section 5 of the go/no-go ("Only a `confirms` link note carries a human-tier link").
It drops 08 4.1.1's other path ("The user's yes stores that link on the verdict as `criterion`, tier `human`"): section 16, item 11.

**Every human-tier link note confirms (derived).** `Verdict` (`SRC/reflection/api.py`) gains
`confirmed: tuple[str, ...] = ()`: the `C<k>` ids named by *every* human-tier link note of the verdict (link notes only, never the
verdict's own `criterion`), in note order, without repeats. `_verdict` fills it from the `links` list it already receives. So a later human
link on the same rejection that names something else does not un-confirm an earlier yes: the brief's "a human-tier `confirms` link note
names it", read literally. The effective link (`links`, used by rule (b) and the lists) keeps its winner rule.

**`define_service` gets no `source` path (decision).** The go/no-go allows a declared `define_service(source=...)` for amendments the user
starts on their own. Not added, because:
- it is declared provenance on the very call the assistant made unasked in E3 T5; E3's assistant passed `source="human"` explicitly on all
  6 `feedback` calls, so a `source` on `define_service` would most likely have been `"human"` there too, reopening F-E3-1;
- section 5's decision says "Rule (c) needs that recorded yes", and only a `confirms` note records one;
- the cost is small: a criterion the user adds outside a rejection still travels with every request, and it admits a revision by rule (b)
  after two confirmed rejections. E2 and E3 had no user-initiated amendment.
Backlogged for after E4 (section 18).

**Confirmed criteria (derived, no ledger).** New pure function in `SRC/reflection/api.py`:

```python
def confirmed_criteria(cases: Sequence[Case]) -> frozenset[str]:
    """The C<k> ids the human client confirmed: every id in ``v.confirmed`` (named by a human-tier link note), over every verdict of
    ``cases`` (pure). A link "the same as R<j>" confirms no criterion by itself; "none" confirms nothing."""
```

New pure function in `SRC/services/api.py` (beside `Criterion`), the single definition of rule (c) eligibility:

```python
def confirmed_amendments(criteria: Sequence[Criterion], confirmed: Collection[str]) -> list[Criterion]:
    """The criteria rule (c) admits, in the order given: added by an amendment of the human client (``amended``) and named by a link the
    client confirmed (``confirmed``: ``ServiceEvidence.confirmed``)."""
```

`Criterion.amended` keeps its meaning (since >= 2, by root, current); its docstring adds "Rule (c) also needs the client's recorded yes:
`confirmed_amendments`."

**Port for `services`.** `ServiceEvidence` (`SRC/services/api.py`) gets a third method, implemented by `CaseServiceEvidence` as
`confirmed_criteria(self._history.cases(owner, service))`:

```python
def confirmed(self, owner: str, service: str) -> frozenset[str]:
    """The criterion ids of this service the human client confirmed with a link (``feedback(confirms=...)``); empty when there are none."""
```

`SRC/services/testing.py:AdmittingServiceEvidence.__init__(self, confirmed: Iterable[str] = ())` returns `frozenset(confirmed)`;
`RefusingServiceEvidence` inherits it (its `__init__` passes `()` to the parent).

### 3.2 The gate (`SRC/reflection/_evidence.py:CaseServiceEvidence.admit`)

- `confirmed = confirmed_criteria(cases)`; `eligible = confirmed_amendments(list(crit.values()), confirmed)`.
- A cited current criterion `x` that is amended but not in `confirmed` adds its subject (as today) and the note
  `{x} was added to the contract by an amendment (v{since}), but the client's yes to it is not recorded (not confirmed)`.
  The note for a non-amended criterion is unchanged.
- Rule (c): `added = [c for c in eligible if c.id in subjects]` (today: every `amended`). Admission detail:
  `cites {ids}, which {client} added to the contract ({versions}) and the client confirmed`.
- `where` (the ids named in G1/G2) becomes `", ".join(c.id for c in eligible) or "none yet"`.
- G1: `(c) it cites a criterion {client} added to the contract by an amendment ({where})` becomes
  `(c) it cites a criterion {client} added to the contract by an amendment the client confirmed ({where})`.
- G2: `the evidence cites no criterion {client} added to the contract by an amendment ({where})` becomes
  `the evidence cites no criterion {client} added to the contract by an amendment the client confirmed ({where})`.
- The module docstring, the `ServiceEvidence.admit` and `ServiceCommands.revise_playbook` docstrings say "(c) it cites a criterion the client
  added by an amendment and confirmed".

Rule (b) is unchanged; it already reads human links only (`Assertion.about`), which now come only from `confirms`.

### 3.3 Marks "(not confirmed)"

- **`services()`** (`SRC/reflection/_reports.py:TextServiceReports._block`): a criterion line of a current amended criterion not in
  `confirmed_criteria(items)` reads `    C9: <text> (amendment, not confirmed)`. Regression lines: no code change (`_assertion_line` already
  marks `unconfirmed`); E3's R1 now reads `R1 (case <id>, about C6 (removed), C3 (removed) (not confirmed)): "..."`.
- **Regression list** in the owner's prompt (`RegressionListSection._line`): no code change; R1 reads `..., about C6 (removed), C3 (removed)
  (not confirmed by the client): "..."`.
- **Amendment note** (`SRC/services/_amend.py:ContractAmender.diff`): signature gains `confirmed: Collection[str]` (package-private Protocol
  `ContractAmendment` in `SRC/services/_protocols.py` follows). Each line under `Acceptance criteria now:` of an amended criterion not in
  `confirmed` ends ` (not confirmed)`. `RuleContractDefiner` (`SRC/services/_define.py`) gets a 13th collaborator `evidence: ServiceEvidence`
  and passes `self._evidence.confirmed(owner, name)`, read before `write_contract`. The mark is advisory, so a failure of that read never
  fails the amendment: on `OrgError` or `OSError` the definer uses `frozenset()` (every amended criterion is then marked "(not confirmed)",
  which errs safe) and writes as usual. `SRC/app/wire_services.py`
  passes `b.get(ServiceEvidence)`, and the `services.testing` world passes its evidence stub. (Item 4 adds one line to the same note, 4.1.)

### 3.4 Replies at the point of action

New `ServiceReports` methods (`SRC/reflection/api.py`; `TextServiceReports` implements them and gets a 5th collaborator
`mail: MailboxReader`, wired in `SRC/app/wire_reflection.py`). They are read-only and never write.

```python
def feedback_step(self, note: Message) -> str:
    """What root does next after recording ``note``, a verdict note: for a human-tier rejection of a service request, the one question naming
    an id and the confirmation call; "" for an accept, a relayed or agent rejection, a link note or a note it cannot place."""

def amendment_step(self, owner: str, service: str) -> str:
    """After root amended the contract of ``owner``'s ``service``: when the latest version added amended criteria the client has not confirmed,
    their ids and, while the latest human-tier rejection of the service has no answer, what records the user's yes; "" when every added
    criterion is confirmed or the service has no human-tier rejection."""
```

`feedback_step(note)` text (one paragraph; `{own}` only when `note.criterion` is set):

```
{own}This rejection is {R}. Next, before define_service: ask the user ONE yes/no question that names what it is about by an id, a criterion ({C ids}) or an earlier rejection ({R ids}), e.g. "About C<k>: add '<the rule in their words>' as a criterion?" or "Same as R<j>: a one-off?". "Always ..." is not their yes: ask anyway. Only after their yes call define_service (when the answer changes the contract), then record the answer: feedback(task_id="{task}", verdict="reject", confirms="{note id}", criterion=["<the id>"], source="human", note="<their answer, verbatim>").
```
- `{own}` = `The criterion on the rejection itself ({note.criterion}) is recorded as not confirmed. `
- `{R}`: the assertion whose `verdict.message.id == note.id`; `{C ids}`: the current criteria, `", "`-joined; `{R ids}`: the other
  assertions' ids, or `none`; `{task}`: `note.reply_to`.
- Placed: the task is the one in `mail.sent(note.sender)` with id `note.reply_to`; the case through `CaseHistory.case_of`; no task, no case or
  no assertion -> `""`.

`amendment_step(owner, service)` text, when a rejection still waits for its yes (DR-1):

```
Not client-confirmed: {A}. Rejection {R} (message {verdict id}) has no recorded yes. The yes is the user's answer to your ONE yes/no question naming {A}; an "Always ..." in the rejection is not it. If you have not asked that question, ask it now and record nothing. Only after they answer yes: feedback(task_id="{task}", verdict="reject", confirms="{verdict id}", criterion=[{A quoted}], source="human", note="<their answer, verbatim>").
```
- `{A}`: the current criteria with `since == contract.version`, `amended`, not in `confirmed_criteria(cases)`; `{A quoted}`: `"C7", "C8"`.
  When `{A}` is empty the step is `""`.
- `{R}`: the latest assertion of `regressions(cases)` (highest verdict message id). No assertion at all: `""` (an amendment outside any
  rejection gets no step). `R.link` is `""` or `"unconfirmed"`: the text above. `R.link` is `"confirmed"` or `"none"` (the latest
  rejection already has the user's answer): the first sentence alone, `Not client-confirmed: {A}.` (DR-14).
- `{task}`: `R.verdict.task_id`; `{verdict id}`: `R.verdict.message.id`. `owner` is resolved with `AgentDirectory.require`.

In the proper flow (question, yes, `define_service`, then `confirms`) the step also appears, because the confirmation follows the
amendment; it then tells the assistant the one call still to make.

MCP (`SRC/mcp_server/_tools_services.py`), root only:
- `feedback` with a verdict: the receipt's `about` part becomes `, about {msg.criterion} (not confirmed)`; then, when non-empty,
  `"\n" + reports.feedback_step(msg)`. The `confirms` receipt is unchanged.
- `define_service` (`_register_client_tools`, `me == ROOT`): the reply, then `"\n" + reports.amendment_step(owner, name)` when non-empty.
- Both tails are computed by one private helper `_step(make: Callable[[], str]) -> str` that returns `""` on `OrgError` or `OSError` (the
  cases or the mail cannot be read). Any other exception propagates: a `ValueError` or `KeyError` there is a bug in the step text and must
  fail the test that hits it (section 10, DR-12).
- Root `feedback` docstring, the sentence from `criterion (reject only)` to the end becomes (columns as today; `"every verdict stays"`
  stays):

```
criterion (reject only): what
the rejection is about, as ids: "C<k>" (a contract criterion, see `services`), "R<k>" (an earlier rejection it
repeats) or "none" (no lasting rule); on the rejection itself it is shown as not confirmed, whatever the source.
confirms: the user's yes. After they answered yes to your one question naming the id, call again with the same
task_id, verdict "reject", confirms=<the rejection's message id>, criterion, source "human" and their answer
verbatim as note: it records the link, not a new verdict, and only this link counts as the client's. Feedback is
for reflection only: it never waives an acceptance criterion or changes the outcome of the request.
```

The `define_service` docstring and the root server instructions (`SRC/mcp_server/_instructions.py`) are unchanged. The docstring is
registered by `_register_client_tools` for root and for every agent client alike (it is in `mcp/surface_manager.txt` too), and the
review's optional sentence would speak of a user to agents; the yes-step travels in the `feedback` reply and the `define_service` reply
instead (section 16, item 13).

**CLI** (`SRC/cli/_commands_services.py:FeedbackCommand`). The terminal is the human's own seat (0a 4.2), so a criterion typed with a
rejection is the user's yes. With `verdict == "reject"`, `--criterion` given, `--confirms` absent and `--source human` (the default), the
command makes two calls, each followed by its own snapshot commit (DR-11):
1. `feedback(..., criterion=args.criterion)` (validates the ids; the verdict carries them, relayed tier); then
   `snapshots().commit(f"root: feedback {msg.id} -> {msg.to}")` and the existing verdict line is printed;
2. `feedback(ROOT, task_id, "reject", note, source="human", criterion=args.criterion, confirms=<msg.id of call 1>)`; then
   `snapshots().commit(f"root: feedback {link.id} -> {link.to}")` and the existing link line is printed
   (`link on {id} -> {owner}: {ids} (message {id}, source human)`).
If call 2 fails, the verdict is already written and committed, its line printed; the error follows (section 10). With `--source relayed`
or with `--confirms` it makes one call and one commit, as today. Help strings unchanged.

### 3.5 SKILL.md step 5.6 (one line; item 6 has the budget)

After `another, make the item the clarification that settles both.` insert: `"Always ..." is not their yes: ask the item first, and never pass
`criterion` on the rejection itself.` (exact wrap in 8.1, replacement S4).

### 3.6 RED tests (item 1)

Unit and contract (new tests; the commit of each is in section 15):
- `SRC/reflection/tests/test_contract_case_history.py`: `test_a_criterion_on_the_rejection_itself_is_relayed_tier` (source human, own
  criterion -> `links_tier == "relayed"`); `test_a_human_confirms_link_wins_over_the_verdicts_own_criterion`;
  `test_every_human_link_note_confirms_what_it_names` (DR-9: two human link notes on one rejection, `C1` then `C2, R1`, then a relayed
  `C3` -> `confirmed == ("C1", "C2")`, while `links == ("C2", "R1")`; the verdict's own `criterion` is never in `confirmed`).
- `SRC/reflection/tests/test_regressions.py`: `test_an_assertion_whose_only_link_is_on_the_verdict_is_unconfirmed`;
  `test_pure_functions.py`: `test_confirmed_criteria_reads_human_links_only` (relayed link, own criterion, `none`, `R<j>` give nothing; two
  verdicts' `confirmed` are united).
- `SRC/services/tests/test_criteria.py`: `test_confirmed_amendments_needs_both` (amended + confirmed; amended only; confirmed v1
  criterion; removed criterion).
- `SRC/services/tests/test_contract_service_evidence.py`: `test_confirmed_is_a_frozenset_of_criterion_ids` (every implementation).
- `SRC/reflection/tests/test_case_service_evidence.py`: `test_rule_c_refuses_an_amendment_without_a_confirmation` (G1 with the
  "(not confirmed)" note and "amendment the client confirmed (none yet)"); `test_rule_c_admits_a_confirmed_amendment` (detail "... and the
  client confirmed"); `test_rule_b_ignores_criteria_given_on_the_verdicts` (two rejects with own `C2` -> G1, not admitted).
- `SRC/reflection/tests/test_reports.py`: `test_an_unconfirmed_amendment_is_marked_in_the_listing`; `test_feedback_step_names_the_ids_and_the_confirmation`;
  `test_feedback_step_says_an_own_criterion_is_not_confirmed`; `test_feedback_step_is_empty_for_accepts_relayed_rejects_and_links`;
  `test_amendment_step_after_an_unconfirmed_reject` (needles `Not client-confirmed: C3`, `Rejection R1 (message {id}) has no recorded yes`,
  `confirms="{id}"`, `an "Always ..." in the rejection is not it`, `ask it now and record nothing`);
  `test_amendment_step_after_a_confirmed_reject_says_only_not_confirmed` (DR-14: exactly `Not client-confirmed: C4.`);
  `test_amendment_step_is_empty_outside_a_rejection_or_when_everything_is_confirmed`.
  `test_contract_service_reports.py` gains the contract cases of both methods (strings only; every implementation).
- `SRC/services/tests/test_amender.py`: `test_the_note_marks_an_unconfirmed_amendment`; `test_contract_service_commands.py`:
  `test_the_amendment_note_reads_the_confirmations` (with `AdmittingServiceEvidence(confirmed=["C7"])`) and
  `test_an_unreadable_confirmation_marks_everything_and_still_amends` (DR-12: an evidence stub whose `confirmed` raises `OrgError`).
- `SRC/mcp_server/tests/test_tools_services.py`: `test_root_feedback_reply_marks_an_own_criterion_and_names_the_next_step`,
  `test_root_define_service_reply_carries_the_amendment_step`, `test_a_failing_step_never_fails_the_call` (scripted reports raise `OrgError`,
  then `OSError`), `test_a_bug_in_a_step_is_not_hidden` (scripted reports raise `ValueError`: the call raises).
- `SRC/cli/tests/test_commands_services.py`: `test_a_criterion_typed_with_a_rejection_is_recorded_as_the_users_link` (two calls; commits
  `root: feedback f-1 -> ceo` then `root: feedback f-2 -> ceo`; two lines); `test_a_failing_confirmation_keeps_the_committed_verdict`
  (the fake refuses call 2: one commit, the verdict line printed, `OrgError` raised); `test_relayed_feedback_keeps_the_criterion_on_the_verdict`.

**Existing tests that D1 rewrites.** Two kinds break, and each gets one rule:
- *A human verdict carries its own `criterion` and the test needs it to count* (rule (b), `Assertion.about`, `link == "confirmed"`, an
  "about C<k>" without the mark). Rule H: record the verdict without `criterion`, then a `confirms` link note with the same ids and
  `source="human"`. Where a test is about the verdict's own criterion (validation F1-F4 at `test_contract_service_commands.py:780-853`,
  stored fields in `kernel/tests/test_message_provenance.py`, `delivery/tests/test_delivery_events.py`,
  `dispatch/tests/test_contract_message_sender.py`, the facades, or how an own link is shown), keep the setup and update only the
  expectation that changes (`relayed`, `(not confirmed)`).
- *A revision cites a `C<k>` that `add_acceptance` added, and no human link names it* (refused from commit 7 on). Rule C: confirm the
  amendment before the revision. Rule F: when the test only needs *a* revision and a first version suffices, use the exempt first version
  instead (define without `playbook`, then `revise_playbook(..., evidence=[])`).
  For Rule C, `TESTS/testkit/services_world.py` gets one helper, used by every Org-API site below:

```python
def confirmed_amendment(org, criterion, topic="confirm", owner="ceo", name="weekly-brief"):
    """The user rejects a fresh delivery, the contract gains ``criterion`` and the user's yes to it is recorded (a ``confirms`` link naming
    its new id): what admits a revision citing it by rule (c). Returns the new id."""
    task = request(org, topic)
    deliver(org, owner, task)
    no = org.feedback(ROOT, task.id, "reject", f"Missing: {criterion}", source="human")
    org.define_service(ROOT, owner, name, add_acceptance=[criterion])
    new = next(c.id for c in reversed(org.runtime.service_catalog.criteria(owner, name)) if c.text == criterion and c.current)
    org.feedback(ROOT, task.id, "reject", "Yes, add it.", source="human", criterion=[new], confirms=no.id)
    return new
```

Known sites (found by grepping `criterion=` on verdicts and every `revise_playbook` / `admit` that cites a `C<k>` added by `add_acceptance`;
the coder runs the suite after commits 6 and 7 and applies the same rules to anything else that fails):

| Site | Rule | Change | Commit |
|---|---|---|---|
| `SRC/reflection/tests/test_case_service_evidence.py:51-55` (`rejected` helper), `:136` and `:295` (direct `note_on` with own `C2` on a case's second verdict) | H | with `source="human"` and a criterion, the helper records the verdict without it and then `note_on(w, task, reply_to=verdict.id, criterion=..., source="human")`; returns `(task, verdict)` as today; the two direct calls do the same. Relayed and agent calls keep the criterion on the verdict | 6 |
| same file `:191-245` (rule (c) and removed-criterion cases) | C | `:191-197` confirms each amended id right after its amendment (`rejected(w, "No week.", criterion="C3")`, later `rejected(w, "No question.", topic="b", criterion="C4")`; the helper turns each into a confirms link); every expected `(c)` clause becomes `amendment the client confirmed ({ids or "none yet"})` and every (c) detail ends `and the client confirmed` | 7 |
| `SRC/reflection/tests/test_contract_case_history.py:244-253` | O | line 252 expects `(own, ("C1",), "relayed")`; line 253 is unchanged | 6 |
| `SRC/reflection/tests/test_reports.py:23-29` (`reject` helper) and `:56-78` | H + O | the helper records a `criterion` as a verdict plus a `confirms` link (so R1 `about C1, C2`, R2 `no lasting rule` and the `(removed)` line stay); a new R6 made with `svc.feedback(..., source="human", criterion=["C2"])` directly expects `about C2 (not confirmed)` | 6 |
| `SRC/reflection/tests/test_prompt_sections.py:319-323` (`reject` helper; used at `:418`, `:442`, `:451`) | H | the same helper change (the lines under test are about a human link: `no lasting rule (the client said so)`, `about C1, C2`, `(removed)`) | 6 |
| `TESTS/golden/test_golden_files.py:159-166` | H | both verdicts lose `criterion`; their two `confirms` calls (`criterion=["C1"]`, `source="human"`, note `"Yes, it is about C1."`) come after the second verdict, before its `clock.tick()`, with no tick between them (DR-6), so the ids of both requests and of every earlier message stay | 6 |
| `TESTS/e2e/test_org_growth_0a.py:144` (chain block 6), `:227` (`test_6`) | H | `n = feedback(B1, "reject", LEE, source="human")`, then `feedback(B1, "reject", "It is about C6 too.", source="human", criterion=["C6"], confirms=n)` | 6 |
| `SRC/mcp_server/tests/test_service_tools.py:170,173` | H | both verdicts get their `C2` link by `confirms` | 6 |
| `SRC/mcp_server/tests/test_service_tools.py:43-46` | O | the reply expects `about C1 (not confirmed)` plus the step (commit 9); `no.criterion == "C1"` stays | 9 |
| `SRC/mcp_server/tests/test_service_tools.py:35` | docstring | the needle becomes `confirms: the user's yes. After they answered yes to your one question naming the id, call again with the same task_id, verdict "reject"` | 9 |
| `SRC/mcp_server/tests/test_tools_services.py:184-185` | O | the exact reply gains ` (not confirmed)` and the scripted step | 9 |
| `SRC/cli/tests/test_commands_services.py:137-143` (`test_feedback_reply_shows_the_message_id`) | O | becomes the two-call case above (`--criterion` with source human); a `--source relayed` variant keeps today's single call | 10 |
| `TESTS/golden/test_golden_events.py:76-82` | F | the first `define_service` loses `playbook=`; the amendment call stays (so `service.define` still carries `amendment: bool`); `revise_playbook(..., "learned something", [])` is the exempt first version, so `service.revise` still has `admitted: str` and `events/line_shapes.txt` stays byte-identical | 7 |
| `SRC/reflection/tests/test_digest.py:75-76` | C | `org.define_service(... add_acceptance=...)` becomes `c3 = confirmed_amendment(org, "Every claim names its source")`; the revision cites `[c3]` | 7 |
| `SRC/reflection/tests/test_prompt_sections.py:202-203`, `:285-286` | C | the same helper before the v2 revision | 7 |
| `SRC/mcp_server/tests/test_service_tools.py:137-138` | C | the same helper, after `svc.end_run("ceo", ok=True)` closes the run the test opened | 7 |
| `SRC/mcp_server/tests/test_service_tools.py:223-225` | C | after the amendment, root confirms it on the test's earlier rejection: `call(root, "feedback", task_id=task.id, verdict="reject", note="Yes.", source="human", criterion=["C3"], confirms=<that rejection's id>)` | 7 |
| `SRC/services/tests/test_playbook.py:16-17` | C | the helper; the inbox assertions then read only the runtime's notes (`n.sender == "runtime"`), and the `org.unread(ROOT)` assertion is adjusted to what the helper adds (its result reaches root's inbox) | 7 |
| `SRC/blueprint/tests/test_role_templates.py:258-263` (`AMBIGUOUS_BULLET`) | template | the constant becomes the bullet of 5.4 | 17 |

E2e (`TESTS/e2e/test_org_growth_0a.py`):
- **`test_7_an_amendment_admits_a_revision_only_once_the_client_confirmed_it`** (rewrite): `chain(w, 4)`; accept A3; request B1, deliver;
  `n2 = feedback(B1, "reject", LEE, source="human")` (no criterion); `reply = define_service(add_acceptance=[added])`. Its assertions land
  with the commit that makes them true (DR-5):
  - commit 7: `C7: {added}` in `reply`; `revise(..., ["C7"])` fails with `C7 was added to the contract by an amendment (v2), but the
    client's yes to it is not recorded (not confirmed)`; then `feedback(B1, "reject", "Yes, add it.", source="human", criterion=["C7"],
    confirms=n2)`; `revise(..., ["C7"])` returns v2 with `admitted: c`, `evidence: [C7]`;
  - commit 8: the lead's amendment note has `C7: {added} (not confirmed)`;
  - commit 9: `reply` has `Not client-confirmed: C7` and `confirms="{n2}"`;
  - commit 13: the item-4 prompt assertion (4.3).
- **`test_11_e3_turn_5_an_unasked_amendment_is_not_the_clients_yes`** (new, commit 12, after everything it asserts exists; E3's C9/C10 are
  C7/C8 here, the world has six v1 criteria): request A1, deliver; `reply = call(root, "feedback", task_id=A1, verdict="reject",
  note=LENA_T5, source="human", criterion=["C6", "C3"])` -> `about C6, C3 (not confirmed)`, `This rejection is R1`, `confirms="{n1}"`; then
  `define_service(remove_acceptance=[CRITERIA[2], CRITERIA[5]], add_acceptance=[SUMMARY_FIRST, DUE_RULE])` -> reply has
  `Not client-confirmed: C7, C8` and `Rejection R1 (message {n1}) has no recorded yes`; `revise(..., ["C7"])` and `revise(..., ["C8"])` are
  refused with the "(not confirmed)" note and `amendment the client confirmed (none yet)`; `call(root, "services")` has
  `R1 (case {A1}, about C6 (removed), C3 (removed) (not confirmed))` and `C7: {SUMMARY_FIRST} (amendment, not confirmed)`; PLAYBOOK.md is
  still v1. The 2 s gap of E3 is not replayed (DR-16): the docstring says why, "E3 amended 2 s after the rejection; nothing here depends on
  the delay (the tier is derived from which note carries the link, not from time), and a real sleep would only slow the test; the frozen
  clock is not used because the team runs in real scheduler subprocesses". Commit 13 adds the item-4 prompt assertions (4.3).
- `test_3` gains its item-4 assertion in commit 13 (4.3).

### 3.7 Goldens (item 1)

- `mcp/surface_root.txt`, `surface_root_unbound.txt`, `surface_root_setup_mode.txt` (3, commit 9): the root `feedback` docstring.
- Expected unchanged (the coder verifies each): `services/services_text_root.txt`, `services/service_and_playbook_files.md` (their scenario
  moves the links to `confirms` calls placed as in 3.6, so ids, R lines "about C1" and the evidence "- C1" stay), `events/line_shapes.txt`
  (scenario changed as in 3.6, Rule F), reflection `services_*` (8) and `cli/services.txt` (both; only a current root-amended criterion
  gets the mark), `cli/define_service_amend_*.txt` (the services-level reply is unchanged), `cli/feedback.txt` (no criterion), the
  dashboard goldens. If one of them still differs, the commit stops until the diff is explained and listed in section 14.

## 4. Item 4: rule (c) visible to the owner, and the adversarial gate test (F-E3-4), after item 1

### 4.1 Changes

- **Reflect step 3, human client, unlocked** (`SRC/reflection/_sections.py:EvidenceReflectSection.section`; new 4th collaborator
  `history: CaseHistory`, wired in `SRC/app/wire_reflection.py:_sections`). The clause `or when it cites a criterion your parent added to
  the contract by an amendment;` becomes `or when it cites a criterion your parent added to the contract by an amendment the client
  confirmed ({eligible});` where, with `E = confirmed_amendments(criteria, confirmed_criteria(cases))` and `U` = the current amended criteria
  not confirmed:
  - `E` empty: `none yet`; one id: `now {id}: a revision citing it is admitted`; several: `now {ids}: a revision citing one of them is admitted`;
  - `U` non-empty appends `; {ids} {is|are} not confirmed yet`.
- **Reject preamble** (lead text for `rejected == "human"`, unlocked): `One rejection is a reason to look, not to change how the team works:`
  becomes `A rule without the client's evidence (step 3) is a reason to look, not to change how the team works:`, and `Revise the playbook
  only as step 3 says, then handle the {what}.` becomes `Revise the playbook when step 3 admits it, then handle the {what}.` The rest is
  unchanged. Locked, relayed and agent texts are unchanged.
- **Amendment note** (`ContractAmender.diff`): when any listed criterion is `amended` and the new contract is not locked (`new.locked` is
  False; on a locked contract `revise_playbook` refuses before the gate, so nothing would be admitted: DR-13), one line before
  `Contract: {where}`:
  `Rule (c): a playbook revision that cites a criterion added by an amendment the client confirmed is admitted; confirmed now: {E ids or "none yet"}. A criterion marked (not confirmed) counts once the client's yes is recorded (it reaches you as a criterion link).`
- **`revise_playbook` docstring** (`_register_owner_tools`): `or when it cites a criterion your parent added to the contract by an amendment;`
  becomes `or when it cites a criterion your parent added to the contract by an amendment the client confirmed (your Reflect section and the
  amendment note name them);`, re-wrapped at today's column.
- ORG.md rule 10 and the lead charter sentence are unchanged (they say "when the client's evidence calls for it", which stays true).

### 4.2 RED tests (item 4)

- `SRC/reflection/tests/test_prompt_sections.py`: `test_step_3_names_the_confirmed_amendments` (none yet / one / several / with unconfirmed);
  `test_the_reject_preamble_speaks_of_rules_without_client_evidence`.
- `SRC/services/tests/test_amender.py`: `test_the_note_names_rule_c_and_the_confirmed_amendments`; `test_no_rule_c_line_without_amendments`
  (also: no line when the amended contract is locked, DR-13).
- `SRC/mcp_server/tests/test_tools_services.py`: `test_revise_playbook_docstring_names_confirmed_amendments`.

### 4.3 The three e2e cases (`TESTS/e2e/test_org_growth_0a.py`)

1. *Relayed wrong rework, then a revision citing it: refused.* `test_3` (exists) gains: the refusal contains `by an amendment the client
   confirmed (none yet)`.
2. *A revision citing an unconfirmed amendment: refused.* `test_11` (3.6) gains: a human rework `request(revises=A1, source="human")`,
   delivered; the lead's prompt for it contains `about C6 (removed), C3 (removed) (not confirmed by the client)` and
   `amendment the client confirmed (none yet; C7, C8 are not confirmed yet)`; the amendment note has `confirmed now: none yet`.
3. *A revision citing a confirmed amendment: admitted.* `test_7` (3.6) gains, after the confirmation: a new request B2, delivered; the lead's
   prompt for it contains `amendment the client confirmed (now C7: a revision citing it is admitted)`; the admitted revision of commit 7
   moves after B2's delivery.

### 4.4 Goldens (item 4)

`prompts/service_owner_reflect.txt` (1: step 3 and the preamble); reflection `sections_history_then_new_request.txt`,
`sections_playbook_and_rejection.txt`, `sections_rejection_and_rework.txt`, `sections_second_playbook_and_new_request.txt` (4: step 3; the
first 3, which have a human rejection, also the preamble); `mcp/surface_manager.txt` (1: the `revise_playbook` docstring). Total 6. How each
is updated: section 14.

## 5. Item 2: client questions before delivery, never answered with a rework (F-E3-2, F-E3-3, F-E3-9)

### 5.1 Parsing (one definition)

New pure function in `SRC/kernel/_text.py`, exported from `SRC/kernel/api.py` (both `progress` and `reflection` need it; `services` would too,
and only the kernel is below all three):

```python
def client_questions(body: str) -> list[str]:
    """The items of the first "Questions for the client:" block of a message body, in order (pure)."""
```

Rules:
- The marker line: stripped of a leading list marker (`-`, `*`, `+` or `•` followed by a space; DR-15), then of leading `#`, `*`, `_` and
  spaces, it starts with `questions for the client` (case-insensitive).
- The rest of that line after the phrase, with `:`, `*`, `_` and spaces stripped, is one item unless it is empty or its first word (split on
  spaces, `;` and `,`, then stripped of `:*_.`) is a "none" word: `none; all settled` and `None.` give no item (DR-15).
- Then the following lines: blank lines right after the marker are skipped; after that a list line (`-`, `*`, `+`, `•` or `1.`/`1)`
  followed by a space) is one item (marker stripped); the block ends at the first blank line, heading (`#`) or non-list line.
- "None" words, compared after lower-casing and stripping a trailing `.`: `none`, `no`, `n/a`, `-`. A list line that is only a none word
  gives no item either.
- Fixtures are E3's three bodies: `msgs/inbox/...lead-1d4c.md` (3 items), `msgs/read/...lead-1a74.md` (2), `msgs/inbox/...lead-dac0.md`
  (`Questions for the client: none.`: 0).

### 5.2 `progress` flag (`SRC/progress/_lines.py:CaseTaskLines.line`)

`CaseTaskLines` gets a 7th collaborator `mail: MailboxReader` (wired in `SRC/app/wire_progress.py`; `progress` already imports `mail`).
The flag is shown when all of these hold:
- `result.status == "done"` and `n = len(client_questions(result.body)) > 0`;
- no task root sent revises this one: `not any(t.type == "task" and t.revises == task.id for t in mail.sent(ROOT))` (one rule for service
  requests and one-off tasks alike, DR-10);
- for a service request, the client has not rated this delivery: `not rated(case, task)` (an unknown case counts as not rated).
The part is `{n} question for the client: ask the user before you copy or deliver` (n == 1) or `{n} questions for the client: ask the user
before you copy or deliver`, appended right after the artifacts part. So a later rework of the task ends the flag for every task, and the
client's verdict ends it for a service request. A one-off task without a rework keeps its flag while `progress` lists it (24 h), because
nothing else records that its questions were asked. `ProgressReporter.progress`'s docstring names it.

### 5.3 Relayed rework reply

New `ServiceReports` method (implemented by `TextServiceReports`, using its `mail`):

```python
def rework_step(self, task: Message) -> str:
    """For a rework root just sent with ``source: relayed``, the client questions of the result it revises; "" otherwise."""
```

Text, when the revised task's latest result in `mail.received(task.sender)` has questions (each clipped to 160 characters with
`clip_line`; at most 5, then `; and {k} more`):

```
{revises}'s result asked the client: {q1}; {q2}. Ask the user these questions, unless the user asked for this change: a rework does not answer them.
```

MCP `_requested` (root only, `revises` set): `"\n" + step` after the case total when non-empty, through `_step` (3.4). No refusal: the rework
is sent first, as today.

### 5.4 Templates

`SRC/roles/manager.md`, the `ambiguous` bullet becomes (one bullet, no new line; body stays <= 50 lines):

```
- Items a verifier lists as `ambiguous` (it cannot tell whether a criterion covers them), and any note of a verifier that a criterion can be read two ways (even one it calls non-blocking), are the client's to decide, not yours: never settle one by including or excluding it. Keep the deliverable as verified and put each item at the top of your report under `Questions for the client:` (one line each: the item, the criterion id, the verifier's words), so they are asked before delivery. Copy every `Questions for the client:` item from your reports' results into your own report the same way; never answer one yourself.
```

`SRC/roles/reviewer.md`, in the "Enumerate independently" bullet, after `never exclude it silently.` insert:
` An item that fits a criterion's words but not its evident purpose (nothing for anyone to do, a restatement, a status) is `ambiguous`: list it, never decide it.`
Domain-neutral; E2 rec 5's memo wording stays out of the template.

SKILL.md 5.2-5.4: replacement S3 (8.1).

### 5.5 RED tests (item 2)

- `SRC/kernel/tests/test_client_questions.py` (new): the three E3 bodies; inline item; heading form with a blank line; "none" words;
  an inline `none; all settled` (0 items) and a bullet-prefixed marker `- Questions for the client:` with two list items (2) (DR-15);
  first block only; no block.
- `SRC/progress/tests/test_lines.py`: `test_a_done_result_with_client_questions_is_flagged`, `..._one_question_is_singular`,
  `test_the_flag_ends_with_a_verdict_or_a_later_rework`, `test_a_one_off_task_keeps_its_flag_until_a_rework_revises_it` (DR-10),
  `test_a_blocked_result_is_not_flagged`.
- `SRC/reflection/tests/test_reports.py`: `test_rework_step_repeats_the_revised_results_questions` (relayed),
  `test_rework_step_is_empty_for_a_human_rework_or_a_result_without_questions`, `test_rework_step_clips_and_counts`; the
  `test_contract_service_reports.py` contract case.
- `SRC/mcp_server/tests/test_tools_services.py`: `test_a_relayed_rework_reply_repeats_the_client_questions`.
- `SRC/blueprint/tests/test_round_f_guidance.py`: `test_manager_asks_before_delivery_and_forwards_two_readings` (phrases `so they are asked
  before delivery`, `can be read two ways`, absent `before the delivery is accepted`; body <= 50 lines);
  `test_reviewer_marks_items_that_miss_a_criterions_purpose_ambiguous` (`fits a criterion's words but not its evident purpose`,
  `list it, never decide it`).
- `SRC/skill/tests/test_skill_org_growth.py`: needles of 8.2.
- **Deterministic e2e** `TESTS/e2e/test_org_growth_0a.py::test_12_a_reviewers_ambiguous_item_reaches_roots_progress_before_delivery`:
  - `TESTS/testkit/fake_agent.py`, service mode, reads `FAKE_AMBIGUOUS` (items separated by `|`; unset = today's behaviour). The last
    report of `FAKE_REPORTS` (the checker) adds one line `Ambiguous: <item>` per item to its summary. On a checker result, the manager copies
    each `Ambiguous: ` line of `msg.body` into its own done summary under `Questions for the client:` as `- <item>` (what `roles/manager.md`
    asks).
  - `run_team(w, env=None)` merges `env` into the runner's environment; `deliver(w, task_id, env=None)` passes it on.
  - With CRITERIA's C5 (`One row for every commitment, including informal ones`): request A1, deliver with
    `FAKE_AMBIGUOUS="Marta keeps the agenda as sent (C5): fits the words, not the purpose"`.
  - Root `progress` has, on A1's line, `1 question for the client: ask the user before you copy or deliver`. The test also asserts that
    `tmp_path / "deliverables"` does not exist, as the go/no-go words it; no actor in the test copies anything, so that check is not
    evidence and the report does not count it as such (DR-16).
  - `request(revises=A1)` without `source`: the reply has `{A1}'s result asked the client: Marta keeps the agenda as sent` and
    `a rework does not answer them`; A1's line now has no flag (a later task revises it). A second rework of A1 with `source="human"` has
    no such text in its reply.

### 5.6 Goldens (item 2)

`charters/apply_service_example.md`, `charters/apply_code_template.md`, `charters/apply_research_example.md` (3: the manager bullet; none
hires a `reviewer.md` role); `SRC/blueprint/tests/golden/second_half.json` (1 file; 8 manager strings and 2 reviewer strings, by the
one-off script of 0a design 13: load, apply the exact text change, assert the counts measured before the change, write
`json.dumps(data, indent=1) + "\n"`; not committed). Total 4 (methods: section 14). Expected unchanged: `cli/progress.txt` and the
progress colocated goldens (no scenario result has the block).

## 6. Item 3: overspend on runs used (F-E3-7)

### 6.1 The one function (home: `reflection`, for 0b's cost alarm)

`SRC/reflection/api.py`:
- `Case` gains `returned: int = 0`: the runs the chain's results carried back (the sum of `budget` of the latest result of each task of the
  chain). It is derived in `DerivedCaseHistory.cases` from the `results` map it already builds.
- New pure function:

```python
def case_spend(case: Case) -> int:
    """The runs a case costs against its contract's per-request budget (pure): the runs its team used, plus, while it is not finished (open or
    blocked), the runs handed down for it that were neither used nor returned (the team may still spend them). ``case_total`` warns on it;
    Phase 0b's cost alarm reads the same number."""
    still_out = 0 if case.state in ("done", "failed") else max(0, case.budget - case.runs - case.returned)
    return case.runs + still_out
```

`TextServiceReports.case_total`: the condition `c.budget > contract.budget` becomes `case_spend(c) > contract.budget`. The text is
unchanged, both the totals sentence and `. This case now exceeds the per-request budget of {budget}: tell the user.`.
`ServiceReports.case_total`'s docstring says "when the runs used, plus the runs still out on an open case, exceed the contract's budget".

E3, with 15 per request: memo 1 (12 used of 21), memo 2 (15 of 25) and memo 3 (14 of 20) are done, so they spend 12, 15 and 14: no warning.
A done case that used 16 of 15 warns. Memo 1 during its rework (7 used, 21 handed down, 8 returned, open) spends 7 + 6 = 13: no warning. With
a 10-run rework (25 handed down) it would spend 17 and warn when the rework is requested, which is when the user must be asked.

### 6.2 RED tests and goldens (item 3)

- `SRC/reflection/tests/test_pure_functions.py`: `test_case_spend_on_e3s_cases` (12/21, 15/25 and 14/20 done -> 12, 15, 14; 16 used done ->
  16); `test_case_spend_counts_runs_still_out_while_open` (7, 21, 8 -> 13; blocked as open); `test_case_spend_never_counts_a_negative_rest`
  (runs > budget).
- `SRC/reflection/tests/test_contract_case_history.py`: `test_a_case_counts_the_runs_its_results_returned`.
- `SRC/reflection/tests/test_reports.py`: `test_case_total_warns_on_spend_not_on_runs_handed_down` (E3 numbers: no warning; 16 of 15: warning).
  The world's results carry their returned runs (`budget`), as the real reporter does.
- Rewritten (D1): `SRC/reflection/tests/test_contract_service_reports.py:105-109`, `SRC/progress/tests/test_services.py:23`,
  `SRC/mcp_server/tests/test_service_tools.py:101-109` (each to an over-budget rework, e.g. a rework handed more than the contract leaves).
- Goldens (4, all colocated, so updated by a hand edit: section 14): progress `all.txt` (2 lines), `task_1_weekly-brief.txt` (1),
  `task_2_weekly-brief.txt` (1) lose `. This case now exceeds the per-request budget of 10: tell the user` (done cases, 3 used of 16 handed
  down, contract 10; `CaseTaskLines` strips the final `.`); reflection `totals_rejected_then_accepted.txt` (2 lines, done, 5 of 16) loses
  `. This case now exceeds the per-request budget of 10: tell the user.`

## 7. Item 5: a superseded `blocked` task stops holding budget (F-E3-11)

### 7.1 Changes

New pure function in `SRC/mail/api.py` (beside `TaskQuery`; reusable by 0b's blocked count):

```python
def moved_past(task: Message, blocked: Message, received: Sequence[Message]) -> bool:
    """Has the assigner of ``task`` moved past it? ``blocked``: its latest result (``blocked``); ``received``: what its assignee received (pure).
    Yes when a later task from the same sender revises ``task``, or revises what ``task`` revised (a second rework of the same delivery), or when
    the sender gave a verdict (a note with ``feedback``) on any task of its chain after ``blocked``."""
```

- Chain: the received tasks from `task.sender` connected to `task` through `revises`, in both directions.
- Later task: `t.id > task.id`, `t.type == "task"`, `t.sender == task.sender`, and `t.revises == task.id` or
  (`task.revises` and `t.revises == task.revises`).
- Verdict: `m.type == "note"`, `m.feedback`, `m.sender == task.sender`, `m.reply_to` in the chain, and `m.id > blocked.id`.

`SRC/budget/_policy.py:ReserveAllocationPolicy.budget_to_return`: the blocked branch becomes
`[t for t in self._tasks.blocked_tasks(actor) if t.id != task.id and not moved_past(t, latest[t.id], received)]`, with
`latest = latest_results(self._mail.sent(actor))` and `received = self._mail.received(actor)`, both read only when that branch is reached.
`TaskQuery` and its fakes are unchanged. The `AllocationPolicy.budget_to_return` docstring says "no other task reported `blocked` that its
assigner has not moved past".

`progress`: the package-private port `RunCounts` (`SRC/progress/_ports.py`) gets
`kept(task, result, team) -> int`. It returns `given - used` when the result is final (done/failed), carried no `budget`, the team is not
empty (the assignee exists) and `used < given`; else 0. `LogRunCounts` shares one private window computation between `runs_text` and `kept`.
`CaseTaskLines.line` appends `0 returned (kept by {task.to})` right after the runs part when `kept > 0`. `runs_text` is unchanged, so the
dashboard (`app/wire_dashdata.py:ProgressRequestFacts`) is unaffected.

### 7.2 RED tests and goldens (item 5)

- `SRC/mail/tests/test_moved_past.py` (new; `SRC/mail/tests/count.txt` raised): superseded by a rework; by a second rework of the same original; a verdict after the block; a
  verdict before the block (not moved past); another sender's task (not); no chain (not).
- `SRC/budget/tests/test_contract_allocation_policy.py` (every implementation; STUDY rec 10's scenario):
  `test_a_blocked_task_superseded_by_a_rework_no_longer_keeps_the_runs` (the rework's `done` returns them),
  `test_a_blocked_task_the_client_gave_a_verdict_on_no_longer_keeps_the_runs` ("delivered as is"),
  `test_a_blocked_task_still_open_to_its_assigner_keeps_the_runs` (today's rule holds).
- `SRC/progress/tests/test_counts.py`: `test_kept_counts_runs_a_final_result_did_not_return`, `test_kept_is_zero_when_runs_came_back_or_the_assignee_is_gone`;
  `test_lines.py`: `test_a_line_says_who_kept_the_runs`.
- Goldens: none expected. Checked: every done/failed line of `cli/progress.txt` and the progress colocated goldens returns runs, except
  "Haunt", whose assignee is retired (empty team, so `kept` is 0). The coder verifies that the progress/cli/messages goldens stay
  byte-identical after `budget_to_return` changes.

## 8. Item 6: SKILL.md size

### 8.1 Budget and replacements

SKILL.md has 125 lines (baseline) and the cap 125 stays. Ten test files assert `<= 125`: `SRC/skill/tests/test_finish_rules.py`,
`test_observe_skill.py`, `test_skill_services.py`, `test_skill_org_growth.py`; `SRC/blueprint/tests/test_apply.py`,
`test_round_f_guidance.py`, `test_round_g_assistant.py`; `SRC/mcp_server/tests/test_blueprint_tools.py`, `test_reclaim_tool.py`; and
`TESTS/e2e/test_round7.py`. Four replacements, net 0. Lines may be long (today up to 204 characters); no test caps width.

| # | Today's lines | Becomes | Lines | Commit |
|---|---|---|---|---|
| S1 | 41-42 (step 1 item 7) | `7. Review by another agent (default yes); approvals (default: the plan before anything starts, and spend beyond budget); progress (default: one line).` | 2 -> 1 | item 2 |
| S2 | 66-67 (step 4, "status?") | ``- "status?": call `progress()` (or `progress(task_id=...)`) and answer in one or two lines (state, runs used of planned, what needs the user), never from memory.`` | 2 -> 1 | item 1 |
| S3 | 94-96 (step 5 items 3-4) | block below | 3 -> 4 | item 2 |
| S4 | 105 (step 5 item 6) | block below | 1 -> 2 | item 1 |

S3:

```
3. A done report's "Questions for the client:" (ambiguous items; `progress` flags them): ask them in plain words, with any question from item 2, in ONE
   message BEFORE you deliver, and copy nothing until they are answered. Never answer one with a rework: it is the user's to answer; if you
   send a PASSed result back anyway, tell the user it was your decision and what it cost.
4. Then copy the deliverable to the requested path (the plan lists this step) and check it exists and matches.
```

S4:

```
   another, make the item the clarification that settles both. "Always ..." is not their yes: ask the item first, and never pass `criterion`
   on the rejection itself. On yes: `define_service(owner, name, add_acceptance=[<the new criterion>])`
```

Each commit is net 0 (item 1: S2 + S4; item 2: S1 + S3), so the file is 125 lines after both. How it was checked: the four replacements were
applied to the worktree file, and `SRC/skill/tests`, `SRC/blueprint/tests/test_round_f_guidance.py`, `test_round_g_assistant.py`,
`test_apply.py`, `SRC/mcp_server/tests/test_blueprint_tools.py`, `test_reclaim_tool.py` and `TESTS/e2e/test_round7.py` were run (189 passed).
The file was then restored (`git status` clean). The texts that S1 and S2 condense are pinned by no test.

### 8.2 Needles

- Changed or removed: **none**. Every raw needle (including the ones with a line break: `"which\ninputs change ..."`,
  `"never poll\n  with `sleep`"`, `'`view="trace"` with\n  the task id'`, `"keep the lead (manager) and\n   the final verifier ..."`,
  `"unverified or partial result (say the task\n   stays open/blocked, not done)"`, `"record\n   `feedback("`) and every flattened needle stays.
- Added: in `SRC/skill/tests/test_skill_org_growth.py`, two new functions (its `count.txt` raised):
  - `test_the_skill_asks_before_the_copy_and_never_answers_a_question_with_a_rework` (item 2): `` "`progress` flags them" ``,
    `"copy nothing until they are answered"`, `"never answer one with a rework"`, `"tell the user it was your decision and what it cost"`,
    `"4. then copy the deliverable"`, plus `<= 125` lines;
  - `test_always_is_not_the_users_yes` (item 1): `'"always ..." is not their yes: ask the item first'`,
    ``"never pass `criterion` on the rejection itself"``, plus `<= 125` lines.

## 9. Item 7: stale installed skill (followups item 1, F-E3-5)

### 9.1 Changes

- `SRC/skill/api.py`: a new Protocol, implemented by `CopySkillInstaller` (`class CopySkillInstaller(SkillInstaller, SkillCheck)`; it
  already holds a `SkillSource` and a `SkillStore`):

```python
@runtime_checkable
class SkillCheck(Protocol):
    def stale(self, dest: Path | None = None) -> Path | None:
        """The installed copy (``<dest>/hirearchy/SKILL.md``; default dest ``~/.kiro/skills``) when it exists and differs from the packaged
        skill; None when nothing is installed, when it is identical, or when either cannot be read (the check never raises)."""
```

  It returns None on `OrgError` (source missing, target not a file), `OSError` and `UnicodeDecodeError`. "The configured install dest": no
  setting stores one (`install-skill --dest` is per call; checked: no environment variable or setting in `SRC`), so the check reads the
  default dest of the `HOME` in force (`FsSkillStore` asks `Environment.home` on every use).
- `SRC/mcp_server/_ports.py`: a private port, because `mcp_server` may not import `skill` (ARCHITECTURE 2.2):

```python
@runtime_checkable
class InstalledSkill(Protocol):
    def stale(self) -> Path | None:
        """The installed assistant skill when it differs from the one this server ships; None otherwise."""
```

- `SRC/mcp_server/_tools_identity.py`: constant
  `STALE_SKILL = "Note: the installed skill at {path} is out of date: run `hirearchy install-skill --force` (tell the user; this session may follow the old text until it is restarted)."`
  `IdentityTools` and `StatusTools` (`_tools_status.py`) get a last constructor parameter `skill: InstalledSkill`. For `me == ROOT` only,
  `whoami` and `status` append `"\n\n" + STALE_SKILL.format(path=p)` when `p = skill.stale()` is not None, in setup mode too (E3's first call
  was in setup mode). Agents never see it.
- `SRC/mcp_server/testing.py`: `FixedInstalledSkill(path: Path | None = None)`.
- `SRC/app/wire_skill.py`: a module function `skill_check(environment: Environment) -> SkillCheck` returns
  `CopySkillInstaller(PackagedSkillSource(package_dir()), FsSkillStore(environment.home))` (no organization needed), and `register`
  provides the port: `b.provide(SkillCheck, lambda b: CopySkillInstaller(b.get(SkillSource), b.get(SkillStore)))`.
  `SRC/app/fields_skill.py:Fields` gains `skill_check: SkillCheck` (DR-7, option (a)): ARCHITECTURE 3.33 lists the new Protocol (commit 22),
  and `app/tests/test_runtime_fields.py` requires a runtime field for every Protocol of section 3 whose step is done (3.33 is
  `A-bootstrap`, done). The field goes in with the provider, in commit 20, so the suite is green before and after the document changes.
- `SRC/app/wire_mcp_server.py:server_factory`: an adapter `PackagedInstalledSkill(InstalledSkill)` in the same module, over
  `wire_skill.skill_check(environment)` with the process's `OsEnvironment` it already builds. It cannot use the runtime field: in setup
  mode no organization is bound, and E3's first `whoami` was in setup mode.
- README "Kiro integration", a new paragraph after "Run it with `kiro-cli chat --agent org-assistant`...":
  `A global skill with the same name (`~/.kiro/skills/hirearchy/SKILL.md`, what `install-skill` writes) shadows a profile's `skill://` resource: kiro loads the global one. After upgrading hirearchy run `hirearchy install-skill --force` (root's `whoami` and `status` say when the installed copy differs from this version), or remove the global copy when a profile should use another one.`
- The root server instructions are unchanged, so `SRC/skill/tests/test_skill_services.py`'s reference-path budget (< 2700, 4b4a005) stays
  green.

### 9.2 RED tests (item 7; never the real `~/.kiro`)

- `SRC/skill/tests/test_contract_skill_check.py` (new; R8; `SRC/skill/testing.py:IMPLEMENTATIONS` gains
  `SkillCheck: [fs_installer, memory_installer]`, harnesses with their own home):
  absent -> None; identical -> None; different -> the target path; target is a directory -> None; packaged skill missing -> None; `dest`
  given -> that target.
- `SRC/mcp_server/tests/test_tools_identity.py` and `test_tools_status.py`: root's `whoami`/`status` end with the note for
  `FixedInstalledSkill(Path("/h/.kiro/skills/hirearchy/SKILL.md"))`; nothing for `FixedInstalledSkill()`; never for an agent; setup mode
  shows it.
- `SRC/mcp_server/tests/test_stale_skill.py` (new, wired application): `monkeypatch.setenv("HOME", str(tmp_path))` (on top of the autouse
  `isolated_kiro`); `build_server(org, ROOT)`; a different `tmp_path/.kiro/skills/hirearchy/SKILL.md` -> whoami and status name it; an
  identical copy -> nothing; none -> nothing.
- `SRC/skill/tests/test_install.py`: `test_readme_says_a_global_skill_shadows_a_profiles_resource`.
- Goldens: none (the autouse `isolated_kiro` fixture gives every unmarked test an empty `HOME`).

## 10. Error handling

| Operation | Failure | Kind | Caller receives | Logged |
|---|---|---|---|---|
| `feedback` / `define_service` / `request` (root MCP) | the step text (`feedback_step`, `amendment_step`, `rework_step`) raises `OrgError` or `OSError` while reading cases or mail | recoverable; the write already happened | the receipt without the step (`_step` returns `""`), so the assistant never retries a recorded verdict | no: the receipt is what was recorded; the step is advice |
| same | the step text raises anything else (`ValueError`, `KeyError`, ...) | fatal: a programming error in the step | the exception (FastMCP's tool error), which a unit test pins (`test_a_bug_in_a_step_is_not_hidden`), so it is found before release rather than hidden in production | the `tool.call` event with `ok: false`, as for every failing tool |
| `feedback` (CLI, composed) | the second (confirms) call fails after the verdict was written and committed (only an I/O error is possible: ids already validated by call 1; `confirms` is the id call 1 returned) | recoverable | the verdict line, then the existing `error: <text>` on stderr, exit 1; the verdict stays (committed); rerun with `--confirms <id> --criterion ...` | as every CLI error |
| `revise_playbook` | refused by the new (c) rule | recoverable | G1/G2 with the "(not confirmed)" note and the confirmed ids | `tool.call` refused event, as today |
| amendment note | `ServiceEvidence.confirmed` raises `OrgError` or `OSError` | recoverable: the mark is advisory | the amendment as usual; the note marks every amended criterion "(not confirmed)" (`frozenset()`), which errs safe; any other exception propagates before the write | no |
| `progress` | parsing a result body | cannot fail (pure, total) | - | - |
| `budget_to_return` | reading mail | unchanged: propagates, as today | the exception | as today |
| `case_total` | none new | - | - | - |
| `whoami` / `status` | the skill check fails | never raises (`SkillCheck.stale` returns None) | the usual text, without the note | no |

## 11. Validation of external inputs

No new MCP or CLI argument; every signature is unchanged (`TESTS/architecture/org_signatures.json` unchanged). New inputs are texts the
runtime reads:

| Input | Required | Rules | On failure |
|---|---|---|---|
| a result body (agent-written) for `client_questions` | no | first block only; items any length; shown in the progress flag as a count only; in `rework_step` each clipped to 160 characters, at most 5 then "and k more" | no block, or a bad one -> 0 items (no flag) |
| the installed `SKILL.md` | no | compared byte for byte with the packaged text; never shown | unreadable or not a file -> no note |
| `owner` of `amendment_step` | yes | resolved with `AgentDirectory.require` | `OrgError` -> no step (section 10) |

## 12. Invariants, ownership and the architecture rules

| Invariant | Owner (layer) | Why there |
|---|---|---|
| Only a `confirms` link note is a human-tier link | `reflection._cases.DerivedCaseHistory._verdict` | the one place a `Verdict` is derived; every reader (gate, lists, alarms) reads `links_tier` |
| Rule (c) = amended and confirmed | `services.confirmed_amendments` (definition), applied by `reflection.CaseServiceEvidence.admit`; `TextServiceReports`, `EvidenceReflectSection` and `ContractAmender.diff` use the same function | one definition for the gate and every text that names it |
| The confirmed set is derived | `reflection.confirmed_criteria`, behind `services.ServiceEvidence.confirmed` | `services` cannot import `reflection` (the 0a pattern) |
| The case's spend measure | `reflection.case_spend` | `case_total` today and 0b's cost alarm tomorrow read one number |
| "Questions for the client" is parsed one way | `kernel.client_questions` | `progress` and `reflection` both read it; only the kernel is below both |
| A blocked task the assigner moved past holds no budget | `budget.ReserveAllocationPolicy`, through the pure `mail.moved_past` | the policy owns the return rule; the predicate is mailbox vocabulary that 0b's blocked count reuses |
| The stale-skill note never breaks a tool | `skill.SkillCheck` (never raises) | the check owns its failure modes |

Rules:
- **R1-R2**: new public names are added in each `api.py` and `__all__`: `kernel.client_questions`; `services.confirmed_amendments`,
  `ServiceEvidence.confirmed`; `reflection.confirmed_criteria`, `case_spend`, `Case.returned`, `Verdict.confirmed`,
  `ServiceReports.feedback_step` / `amendment_step` / `rework_step`; `mail.moved_past`; `skill.SkillCheck`. Implementations stay in
  `_*.py`. The adapter for `mcp_server`'s private port lives in `app`.
- **R3-R5**: no import changes the graph. `reflection` uses `mail`, `services` and `kernel`; `progress` uses `kernel` and `mail`; `budget`
  uses `mail`; `services` uses `kernel`; `skill` uses `kernel`. All of these edges are allowed today. `mcp_server` -> `skill` is not allowed,
  which is why it has its own port. No import-linter contract and no ARCHITECTURE 2.2 row changes.
- **R6**: every new collaborator is typed by a Protocol (`ServiceEvidence` for the definer, `CaseHistory` for the reflect section,
  `MailboxReader` for `TextServiceReports` and `CaseTaskLines`, `InstalledSkill` for the two tool groups).
- **R7**: `ServiceReports` 2 -> 5 methods, `ServiceEvidence` 2 -> 3, `RunCounts` (private) 1 -> 2, `SkillCheck` 1.
- **R8**: contract suites: new `test_contract_skill_check.py`; extended `test_contract_service_evidence.py`, `test_contract_service_reports.py`
  and `test_contract_case_history.py`. Fakes follow in the same commit: `AdmittingServiceEvidence`, `progress.testing.FixedCaseTotals`,
  `mcp_server.testing.ScriptedReports`, `cli/tests/_fakes.py:FakeReadings` (the three new `ServiceReports` methods return `""`),
  `FixedInstalledSkill`. Runtime field: `app/fields_skill.py:skill_check` (9.1).
- **R9**: no new file and no new writer. The only new read outside the org is `~/.kiro/skills/hirearchy/SKILL.md`, through its owner `skill`.
- **R10-R11**: mypy strict; RED -> GREEN -> REFACTOR.
- **R12**: not applicable (D1); goldens are regenerated deliberately (section 14).
- **R13**: no responsibility sentence changes. `skill` "installs the assistant skill file": checking whether the installed copy is this
  version is part of that.
- Derived over stored: all new facts (tiers, confirmed ids, spend, questions, moved past, stale) are computed from files on every read. No
  ledger, no frontmatter key.
- MCP backward compatibility: no new or changed argument; only reply texts and two docstrings.

## 13. Zero denominators

This batch adds no division and no ratio. The new arithmetic is `case_spend` (subtraction, clamped at 0), `kept` (`given - used` only when
`used < given`) and counts (`len`). For Phase 0b, the cost alarm "above 1.25x the approved budget" is to be computed without division as
`4 * case_spend(case) > 5 * budget`. Contract budgets are >= 1 when defined (`_define.py` refuses < 1) and when read
(`_parse.py:contract_of` takes `max(1, ...)`), so even a hand-edited `budget: 0` cannot make a denominator 0. An empty history gives empty
sets and `""` steps, never a ratio.

## 14. Golden impact (estimate; every regenerated diff is explained in its commit and counted in the report)

The brief's rule, `HIREARCHY_UPDATE_GOLDEN=1` on a `-k` subset, exists only for `TESTS/golden/expected/**` (it is read by
`TESTS/golden/golden_support.py` alone). The colocated `expected/` files of `progress` and `reflection` have no update switch, and the
reflection `sections_*` files hold placeholders (`{askN}`, `{resN}`, `{noteN}`) that a write of actual output would destroy. So each file
has its method (DR-3):
- **G**: `HIREARCHY_UPDATE_GOLDEN=1 uv run pytest tests/golden -k <test name>`, then review `git diff`;
- **H**: a hand edit of exactly the changed sentence, keeping every placeholder; the commit message states the edited line count per file;
- **S**: the one-off script of 0a design 13 (load, apply the exact text change, assert the counts measured before the change, write
  `json.dumps(data, indent=1) + "\n"`; the script is not committed).

| Item (commit) | File | Method | Change | Lines |
|---|---|---|---|---|
| 3 (2) | `SRC/progress/tests/expected/all.txt` | H | delete `. This case now exceeds the per-request budget of 10: tell the user` | 2 |
| 3 (2) | `SRC/progress/tests/expected/task_1_weekly-brief.txt`, `task_2_weekly-brief.txt` | H | the same deletion | 1 each |
| 3 (2) | `SRC/reflection/tests/expected/totals_rejected_then_accepted.txt` | H | delete `. This case now exceeds the per-request budget of 10: tell the user.` | 2 |
| 1 (9) | `mcp/surface_root.txt`, `surface_root_unbound.txt`, `surface_root_setup_mode.txt` | G | the root `feedback` docstring (3.4) | the docstring |
| 4 (13) | `prompts/service_owner_reflect.txt` | G | step 3 and the preamble (4.1) | 2 |
| 4 (13) | `SRC/reflection/tests/expected/sections_history_then_new_request.txt`, `sections_playbook_and_rejection.txt`, `sections_rejection_and_rework.txt` | H | step 3 and the preamble | 2 each |
| 4 (13) | `SRC/reflection/tests/expected/sections_second_playbook_and_new_request.txt` | H | step 3 | 1 |
| 4 (13) | `mcp/surface_manager.txt` | G | the `revise_playbook` docstring (4.1) | the docstring |
| 2 (17) | `charters/apply_service_example.md`, `apply_code_template.md`, `apply_research_example.md` | G | the manager bullet (5.4); none of them hires a `reviewer.md` role | 1 each |
| 2 (17) | `SRC/blueprint/tests/golden/second_half.json` | S | 8 manager strings, 2 reviewer strings | - |
| 5, 7 | none | - | - | - |
| | **total** | | | **17 files** |

Test scenarios changed so that their goldens stay byte-identical (3.6): `TESTS/golden/test_golden_events.py` (Rule F:
`events/line_shapes.txt`) and `TESTS/golden/test_golden_files.py` (Rule H, the `confirms` calls placed after the second verdict:
`services/services_text_root.txt`, `services/service_and_playbook_files.md`).

Must stay byte-identical: everything else, in particular `kiro/*`, `plans/*`, `files/*`, `messages/*`, `cli/*` (both `TESTS/golden` and
`SRC/cli/tests/expected`), `events/*`, the dashboard goldens, `services/*`, reflection `services_*` and `digest_*`, the health and templates
goldens. A diff outside the table stops the commit until it is explained or removed.

## 15. Commit plan (each green; `count.txt` raised where tests are added)

1. `docs(design): add org-growth phase 0a.1 design` (this file; revision 2: `docs(design): address 0a.1 design review`).
2. `feat(reflection): case_spend measures runs used plus runs still out` (item 3; `Case.returned`; 4 colocated goldens by H; 3 tests
   rewritten).
3. `feat(mail): moved_past says when an assigner has moved past a blocked task`.
4. `fix(budget): a blocked task its assigner moved past no longer keeps the runs`.
5. `feat(progress): a final result that returned nothing says who kept the runs`.
6. `feat(reflection): a criterion on the rejection itself is relayed; only a confirms link is the client's`. It adds `Verdict.confirmed`,
   `confirmed_criteria` and the `services()` marks, and applies Rule H / O to every site of the 3.6 table marked 6 (the test helpers of
   `test_case_service_evidence.py`, `test_reports.py`, `test_prompt_sections.py`, `test_contract_case_history.py:252`,
   `test_golden_files.py`, e2e chain block 6 and `test_6`, `test_service_tools.py:170,173`).
7. `feat(services): rule (c) admits only amendments the client confirmed`. It adds `confirmed_amendments`, `ServiceEvidence.confirmed`
   (and the fakes), the gate texts and the docstrings; adds `testkit.services_world.confirmed_amendment`; applies Rule C / F to every site
   of the 3.6 table marked 7 (among them `test_golden_events.py`, whose golden stays byte-identical); rewrites e2e `test_7` with its
   commit-7 assertions (refusal, then admission after `confirms`).
8. `feat(services): the amendment note marks amendments the client has not confirmed` (the definer's `ServiceEvidence`, its `frozenset()`
   fallback; `test_7` gains the note mark).
9. `feat(reflection): root's feedback and amendment replies name the next step` (`feedback_step`, `amendment_step`, `_step`; MCP replies and
   the root `feedback` docstring; 3 goldens by G; the table's commit-9 sites; `test_7` gains the reply step).
10. `feat(cli): a criterion typed with a rejection is recorded as the user's confirmed link` (two calls, two commits).
11. `docs(skill): "always" is not the yes; no criterion on the rejection itself` (S2 + S4; needles).
12. `test(e2e): replay E3 turn 5: an unasked amendment is not the client's yes` (`test_11`, with every assertion of 3.6).
13. `feat(reflection): rule (c) is visible to the owner`. It changes step 3, the preamble, the amendment-note line and the `revise_playbook`
    docstring (6 goldens: 2 by G, 4 by H) and adds the item-4 e2e assertions to `test_3`, `test_7` and `test_11` (4.3).
14. `feat(kernel): client_questions reads a result's questions for the client`.
15. `feat(progress): a done result with client questions is flagged before delivery` (`CaseTaskLines` gets `MailboxReader`).
16. `feat(reflection): a relayed rework repeats the client questions of the result it revises` (`rework_step`; MCP request reply).
17. `feat(roles): questions before delivery, two readings forwarded, ambiguous by evident purpose` (4 goldens: 3 by G, 1 by S;
    `AMBIGUOUS_BULLET` updated).
18. `docs(skill): ask before the copy; never answer a client question with a rework` (S1 + S3; needles).
19. `test(e2e): a reviewer's ambiguous item reaches root's progress before delivery` (fake agent `FAKE_AMBIGUOUS`; `test_12`).
20. `feat(skill): SkillCheck says when the installed copy is out of date` (the Protocol, `CopySkillInstaller`, the contract suite,
    `wire_skill.skill_check` and its provider, the runtime field `skill_check`).
21. `feat(mcp_server): root's whoami and status name a stale installed skill`.
22. `docs: README and ARCHITECTURE for phase 0a.1`. This commit adds the Kiro integration paragraph (9.1) and updates the 0a paragraph of
    "Services and reflection" in place (lines 261-263, same 8 lines, so the section stays < 98 lines): rule (c) needs a confirmed amendment,
    and a `criterion` on the rejection is shown "not confirmed". It also updates the ARCHITECTURE section 3 interface blocks of `kernel`,
    `mail`, `services`, `reflection` and `skill` (3.33 gains `SkillCheck`, whose runtime field exists since commit 20).

Items 3 and 5 (commits 2-5), 2 (14-19) and 7 (20-21) are independent of each other; item 1 (6-12) precedes item 4 (13).

## 16. Deviations, with reasons

From the 0a design section 5.2:
1. **A `criterion` given on the verdict note is relayed tier, whatever its `source`.** 0a: the note's tier, so `human` with
   `source="human"`. This drops 5.2's first path for a human link. Reasons: F-E3-1, 08 4.1.1, and go/no-go section 5.
2. **Root's `feedback(reject)` reply carries the next step** (0a 4.1: a receipt only). Reason: E3 shows the skill text alone was not followed
   at the point of action.
3. **CLI `feedback --criterion` on a rejection (source human, no `--confirms`) writes the verdict and a `confirms` link note** (0a 4.2: one
   note). Reason: the terminal user named the criterion themselves, so under the new data rule their yes must be a link note.

From the 0a design section 5.3:

4. **Rule (c), enforceable form: added by a root amendment and named by a human-tier link.** 0a: amended alone, safe because "the skill
   makes it only after the user's yes"; E3 falsified that. As a consequence, an amendment the user makes outside a rejection is not
   (c)-eligible, since there is no `define_service` source path (3.1).
5. **G1, G2 and the (c) admission name "an amendment the client confirmed"** and list the confirmed ids instead of every amended id.

From the 0a design 6.x texts:

6. Reflect step 3 and the human reject preamble (6.2), the amendment note (6.3) and the root `feedback` and `revise_playbook` docstrings
   (6.4) change as in 3.4 and 4.1.
7. `roles/manager.md` (6.6): "before the delivery is accepted" becomes "before delivery", and a verifier's two-readings note is forwarded.
8. SKILL.md (6.8): S1-S4 (section 8).

From 08:

9. **08 4.2 (c) "a contract criterion the client accepted through the contract loop"** is enforced literally, as the recorded yes. Criteria the
   user adds outside a rejection are therefore not (c)-eligible. This is narrower than 08 and is backlogged in 18.
10. **08 4.1.4 "ambiguity goes to the client before delivery"** is met with nudges (the progress flag, the rework reply, templates), not
    refusals (go/no-go section 5; refusals are reserved for after E4).
11. **08 4.1.1 "The user's yes stores that link on the verdict as `criterion`, tier `human`"** no longer exists: a `criterion` on the verdict
    is relayed tier whatever its `source`, and the yes is stored only as a `confirms` link note. Reason: go/no-go section 5 ("Only a
    `confirms` link note carries a human-tier link") and F-E3-1, where the assistant used exactly that path without asking.

From the go/no-go section 2 file scope (placements; the behaviour is the one it asks for):

12. **Item 1's reply texts** are built in `reflection` (`ServiceReports.feedback_step`, `amendment_step`) and appended in
    `mcp_server/_tools_services.py`, not in `services/_feedback.py` and `services/_define.py`. Reason: the texts name regression ids and read
    the cases, which only `reflection` derives and `services` may not import; and a reply text is the MCP surface's (as `case_total` is
    today). Consequence: the CLI's `feedback` and `define-service` print no step; the CLI's user is the human, and its `feedback` composes the
    yes itself (3.4). `services/_define.py` still changes (the amendment note's mark).
13. **The `define_service` docstring is unchanged**, though the go/no-go lists it. Reason: `_register_client_tools` registers one docstring
    for root and for agent clients (it is in `mcp/surface_manager.txt` too), so a sentence about the user's yes would reach agents; the
    yes-step reaches root in the `feedback` reply and, at the E3 T5 failure point, in the `define_service` reply (3.4).
14. **Item 2's parse** is `kernel.client_questions`, not a use of `attention/_text.py:section`. Reason: `reflection` (for `rework_step`) may not
    import `attention` (ARCHITECTURE 2.2), and `progress` and `reflection` must parse one way; only the kernel is below both. `section` reads
    `## ` headings only and would miss E3's inline `Questions for the client: none.` form.
15. **Item 2's reply** is `ServiceReports.rework_step`, appended by MCP `_requested`, not built in `services/_request.py`. Reason: the rework
    reply is already composed there from `ServiceReports.case_total`; `RuleServiceRequester.request` returns the task `Message`, not a reply.

From the brief:

16. **Goldens outside `TESTS/golden/expected`** (8 colocated files) cannot be regenerated with `HIREARCHY_UPDATE_GOLDEN=1`: that switch is
    read only by `TESTS/golden/golden_support.py`. They are updated by a hand edit of exactly the changed sentence (keeping every
    `{askN}`/`{resN}`/`{noteN}` placeholder) or, for `second_half.json`, by the one-off script; each commit states the edited lines
    (section 14).

Not deviations (definitions the go/no-go left open): 08 3.3's cost alarm measures `case_spend`; the item-5 filter is a pure function in
`mail.api`, not a `TaskQuery` change (one of the two options the go/no-go gave).

## 17. What E4 must check

E4 is go/no-go item 6: deterministic tests plus at least 3 live streams with pre-registered pass rules, the workspace skill copy, and fixed
models. In addition, specific to 0a.1:
- **Clause 2:** after every human `feedback(reject)`, does the assistant follow the reply's step: one yes/no item naming a C or R id, asked
  before any `define_service`, and every human-tier link coming from `confirms`? Count the `define_service` calls that come after an
  "Always ..." with no question (T5's pattern), and how often a `criterion` is passed on the rejection itself. Count, too, every
  `hirearchy feedback` the assistant runs through its shell (the CLI composes a human-tier link in one command: section 19); the expected
  number is 0.
- **Clause 3:** for every result that `progress` flagged with "N questions for the client", was each item asked before the copy into
  `deliverables/`? Record whether the assistant read the flag (it read results by shell in E3). Count relayed reworks of a result with
  questions, and whether the reply's nudge changed what the assistant did next.
- **Clause 1:** the facilitator's injected relayed wrong rework is refused. The owner's prompts show the step-3 ids. Record whether the owner
  attempts `revise_playbook` with a confirmed amendment, and whether the gate admits it.
- **No false overspend:** no "exceeds the per-request budget" on a case that spent at most its budget. No "0 returned (kept by ...)" on a
  case whose runs came back. No runs stranded by a superseded `blocked` rework (`status` budgets at the end).
- **Skill:** with a stale global copy present (harness check), root's first `whoami` names it; with no global copy, or an identical one,
  there is no note (the check reads only `~/.kiro/skills/hirearchy/SKILL.md`, never the workspace copy). SKILL.md is the 125-line 0a.1
  text (md5 recorded).
- **Prompt growth:** the lead's prompt size and its Reflect section words, against E3 (20.2-29.9 KB; 452-679 words).
- If clause 2 or 3 still fails in any stream, the enforcement decision of go/no-go item 6 is taken then. It is not taken here.

## 18. Out of scope and backlog

- Out of scope (go/no-go and brief), and not built:
  - the 0b quality view and alarms, and cause typing;
  - one-off verdict notes and item-level playbook operations;
  - the retro brief;
  - any refusal-based enforcement of the assistant's behaviour: `define_service`, `request`, `feedback` and delivery refuse nothing new.
    The one stricter refusal is the existing `revise_playbook` gate's rule (c), which item 1 itself requires ("a revision citing C9/C10
    is refused");
  - "show all plan checks" (F-E3-8), health on typed escapes (F-E3-10), "read results with `inbox`", and owner prompt caps.
- Backlog: a confirmed path for user-initiated amendments, reconsidered after E4. If it is needed, it should reference the user's verbatim
  words rather than a declared tier.

## 19. Risks and known limits

- **Declared provenance remains.** A `confirms` note with `source="human"` is still declared by the assistant. 0a.1 narrows the risk to one
  explicit, separate call that the reply describes; it cannot remove it.
- **The CLI composes the yes in one command.** `hirearchy feedback <task> reject --note ... --criterion C<k>` (source human by default)
  writes the verdict and a human-tier `confirms` link. That is right for the human at the terminal, but any process with shell access can
  run it (E3's assistant used its shell 10 times, for `cp`/`cmp` and reads only). Today the same command already stores a human-tier
  link (on the verdict itself), so the exposure is not new; E4 counts such calls (section 17).
- **Nudges can be ignored.** Items 1 and 2 steer the assistant; they do not enforce. E4 measures this.
- **The amendment note is a snapshot.** In the proper flow (yes, amend, confirm) the note marks the new criterion "(not confirmed)", because
  the confirmation follows it. The owner learns that it is confirmed from the link note and from the next Reflect step 3.
- **`case_spend` while a case is open counts runs a busy owner kept as "still out"**, so it may warn early. That errs towards asking the user.
- **Parsing is textual.** A "Questions for the client" block written in another form is missed (no flag). The manager template fixes the form.

## 20. Review resolution (design review of revision 1, `.agents/tasks/design-review.md`)

| Finding | Severity | Resolution |
|---|---|---|
| DR-1 | MEDIUM | Addressed: the `amendment_step` text is the review's, word for word (3.4); its two new needles are in `test_amendment_step_after_an_unconfirmed_reject` (3.6). The optional `define_service` docstring sentence is declined: the docstring is shared with agent clients (16, item 13). |
| DR-2 | MEDIUM | Addressed: 3.6 classifies every known site by Rule H / O / C / F with its commit, adds the `confirmed_amendment` helper, and extends the grep rule to every revision citing a `C<k>` from `add_acceptance`. `test_golden_events.py` uses the exempt first version, so `events/line_shapes.txt` stays byte-identical (3.7, 14). |
| DR-3 | MEDIUM | Addressed: section 14 has a method per file (G, H, S) with edited line counts; 16, item 16 records that the brief's switch cannot apply to the colocated files. |
| DR-4 | LOW | Addressed: `test_contract_case_history.py:252` now expects `relayed`; `test_service_tools.py:35` and `AMBIGUOUS_BULLET` are in the 3.6 table; the grep sentence is replaced by Rules H and O. |
| DR-5 | LOW | Addressed: 3.6 and 15 say which `test_7` assertions land in commits 7, 8, 9 and 13; `test_11` lands whole in commit 12 and gains item 4's in 13; `test_3`'s in 13. |
| DR-6 | LOW | Addressed: both `confirms` calls come after the second verdict, before its `clock.tick()`, with no tick between (3.6). |
| DR-7 | LOW | Option (a): `skill_check: SkillCheck` in `app/fields_skill.py`, provided by `wire_skill`, in commit 20; the server uses `wire_skill.skill_check(environment)` because setup mode has no organization (9.1). |
| DR-8 | LOW | Addressed: 16, items 11-15. |
| DR-9 | LOW | Chosen: every human-tier link note confirms what it names (`Verdict.confirmed`, 3.1), the brief read literally; unit case `test_every_human_link_note_confirms_what_it_names`. |
| DR-10 | LOW | Addressed: the flag ends when a later root task revises the task, for one-offs too (`CaseTaskLines` reads `MailboxReader`); a one-off without a rework keeps it while listed (5.2); new test. |
| DR-11 | LOW | Addressed: one commit after each CLI call (3.4), tests updated (3.6); the shell route is in 19 and its count in 17. |
| DR-12 | LOW | Addressed: `_step` catches `OrgError` and `OSError` only; the definer falls back to `frozenset()` and writes (3.3, 3.4, 10); two tests pin both. |
| DR-13 | LOW | Addressed: no rule (c) line on a locked contract (4.1, 4.2). |
| DR-14 | LOW | Addressed: `Not client-confirmed: {A}.` alone when the latest rejection already has its answer (3.4); new test. |
| DR-15 | LOW | Addressed: inline none words by first word, bullet-prefixed markers (5.1); both cases in `test_client_questions.py`. |
| DR-16 | LOW | Addressed: "ten test files" (8.1); E4's skill wording (17); `test_11`'s docstring states why the 2 s gap is not replayed (3.6); `test_12`'s deliverables check is not counted as evidence (5.5). |
| Unverified 7 | - | `cli/tests/_fakes.py:FakeReadings` is listed with the fakes (12, R8). |
