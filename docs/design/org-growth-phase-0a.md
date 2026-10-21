# Org growth, Phase 0a: known-cause fixes (technical design)

Status: design, revision 3. Revision 2 resolved the first design review (1 HIGH, 7 MEDIUM, 14 LOW); revision 3 resolves the second (`/Volumes/workspace/hirearchy/.worktrees/org-growth-0a/.agents/tasks/design-review.md`, verdict CHANGES_REQUESTED: 0 HIGH, 2 MEDIUM, 7 LOW findings, LOW 9 with four parts) and applies the manager's decisions on it (size caps kept by condensing; the reviewer's D3 rule; no change to 08's behaviour). Section 18 maps every finding of both reviews to its change.
Branch `feat/org-growth-phase-0a` off `main` `bf4a285`; worktree `/Volumes/workspace/hirearchy/.worktrees/org-growth-0a`. Baseline: 13 149 passed, mypy strict clean, 49+1 import contracts kept.

Source of truth: `/Volumes/workspace/hirearchy/docs/research/org-growth/08-synthesis.md` (v2.1):
- section 8, row "0a. Known-cause fixes";
- the mechanisms in 2, 3.1, 3.2, 4.1, 4.2 (evidence gate, revision-level form only) and 4.4 (authority bound);
- decisions D1-D5 (section 10);
- the must-fix edits M1-M8 of `11-final-verification.md`;
- bullets 1-4 of the minimum viable core in `10-review-design.md`.

Paths below are absolute. `SRC` = `/Volumes/workspace/hirearchy/.worktrees/org-growth-0a/src/hirearchy`, `TESTS` = `/Volumes/workspace/hirearchy/.worktrees/org-growth-0a/tests`.

## 1. Overview

Phase 0a removes the known causes of study E2's failures without adding stored state.

- **Provenance.** Verdicts and assistant-started reworks get a provenance tier, `source: human|relayed`. It is stamped in the message frontmatter by the one sender every message goes through.
- **Client kind.** A service's client kind is derived: `human` when the owner's parent is root.
- **Links.** A client's rejection can be linked to the contract criterion or the earlier rejection it is about. Criteria get stable ids `C<k>`, derived from the contract's history. Regression assertions get ids `R<k>`, derived from the human-tier rejections.
- **Evidence gate.** `revise_playbook` gets a required `evidence` argument and a revision-level gate (rules (b) and (c) of 08 §4.2). The gate is implemented in `reflection` behind a port that `services` owns. It refuses team-only or relayed evidence and gives the owner the question for its client; the skill makes sure that question never becomes a second question to the user.
- **Regression list.** The runtime derives the list and shows it only in the owner's prompt. The manager template copies it into reviewer tasks and forwards a verifier's `ambiguous` items to the client.
- **Skill.** The skill asks the user about `ambiguous` items before delivery, in the one pre-delivery message. It makes one yes/no contract proposal per human rejection, naming the criterion, and folds any conflict of the proposed criterion with an existing one into that item. It asks a separate consistency question only when a contract is defined, or amended outside a rejection.
- **Health.** `low_quality` is rebased on escapes: a human rejection after the team reported `done`. An escape is attributed to the owner and to the report that signed off last, and is always shown next to the checker's re-checks after a FAIL and the author rework runs they cost.
- **Authority bound.** A non-root actor can no longer grant `can_hire: true`, or a `max_children` above its own, at `hire` or by charter rewrite.
- **Playbook leftover.** The default playbook's leftover sentence is removed.

Everything stays derived from files: no new ledger, no new file, no change to the single-writer table (ARCHITECTURE 2.3). New frontmatter fields are written by their existing owners: `mail`, through `delivery`, for messages; `services` for `PLAYBOOK.md`.

## 2. Technology stack (locked)

- Python 3.11 (as today) and the existing packages only: `mcp` (FastMCP), PyYAML, Textual (dashboard, untouched). No new runtime dependency.
- Dev tooling as pinned: pytest, `mypy==2.4.0 --strict`, `import-linter==2.15`, `scripts/check.sh`.
- Architecture rules R1-R13 apply unchanged:
  - new behaviour behind Protocols in the owning package's `api.py`;
  - private `_*.py` implementations;
  - fakes in `testing.py`;
  - contract suites for every new Protocol;
  - construction only in `SRC/app/`;
  - Protocols of at most 8 public methods.
- No new package and no new dependency edge between packages. Every import below is already allowed by `TESTS/architecture/graph.py`, so no import-linter contract changes.

## 3. Data model

### 3.1 Message frontmatter (kernel `Message`)

`SRC/kernel/_message.py:Message` gets two new optional dataclass fields. They are declared right after `feedback` and before `trace`, as `source: str | None = None` and `criterion: str | None = None`, keyword-defaulted like every field after `body`. No call in `src/` or `tests/` passes more than 4 positional arguments to `Message` (checked with an AST scan), so the insertion changes no call.

- **`meta()`** writes them after `feedback` and before `trace`; key order matters for the goldens.
- **`from_parts`** parses them.
- **`render`** shows them after `feedback:` and before the budget part of the header line, only when set (`source: relayed`, `criterion: C6`, ` | `-separated like the other fields).

The recorded compatibility surface changes with them (4.4).

| Field | Type / values | Who may set it | Meaning | Absent |
|---|---|---|---|---|
| `source` | `"human"` or `"relayed"` | root only (enforced by `dispatch`, 5.1) | `human`: the user's own judgement, given through root, with their verbatim words. `relayed`: anything the assistant concluded itself. | see "legacy reading" |
| `criterion` | text: ids joined by `", "`, e.g. `C6`, `C6, R2` or `none` | root only, and only on a verdict note or a link note (enforced by `dispatch`, S3) | what a rejection is about: contract criterion ids `C<k>`, regression assertion ids `R<k>`, or `none` (the client said: no lasting rule) | no link |

Where `source` is written:

- **Verdict note** (`type: note`, `feedback: accept|reject`, sent by root): always stamped from now on. A root `feedback` without `source` is stamped `relayed` (5.1).
- **Link note** (5.2: `type: note`, no `feedback`, `criterion` set, `reply_to` = the id of an earlier verdict note): always stamped, default `relayed`.
- **Rework task from root** (`type: task` with `revises` set, sent through `request(revises=...)` or root's `delegate(revises=...)`): always stamped. The default is `relayed`; it is `human` only when the caller says the user asked for it.
- **Any other root task**: stamped only when the caller passes `source`. A fresh request is the user's ask by the skill's rule 0b, so it stays unstamped and every fresh-request golden stays byte-identical.
- **Messages from agents and from the runtime**: never carry `source` or `criterion`. Agents are refused (S1); the runtime's `notify` does not set them.

**Legacy reading (decision).** A verdict note from root without `source` (every note written before 0a) is read as `human`.

- *Why.* Since study E the skill has recorded feedback only on the user's own judgement, with a rejection's reason in their words (SKILL.md step 5.5), and E2 confirmed it held: 5 of 5 verdicts were Lena's own. Reading them as `relayed` would empty the regression list of every existing service, and that list is the dev set 0a exists to build.
- *Bounded risk.* A legacy note carries no criterion link, so on its own it can originate at most one regression assertion, and no single case ever admits a revision (5.3).
- A legacy root rework task without `source` is read as not relayed. This is the status quo: health already treats it as client-driven.
- An unknown `source` value (a hand-edited file) is read as `relayed`, the safe side.

The `telemetry` event `msg.deliver` gains the keys `source` and `criterion` (both `null` when unset). They are inserted after `feedback` and before `wake` in `SRC/delivery/_pipeline.py`. The text form of `obs events` omits null keys, as it does today.

### 3.2 Derived tiers and client kind (no stored state)

New pure vocabulary goes in the kernel (`SRC/kernel/_message.py`, exported from `SRC/kernel/api.py`). It is shared by `reflection` and `health`, which may not import each other.

```python
SOURCES = ("human", "relayed")

def verdict_tier(note: Message) -> str:
    """The weight class of a client's verdict or link note: "agent" when an agent sent it (its client is an LLM: the note's
    sender is the parent of the service's owner), else its ``source``; a root note without one (written before sources
    existed) is "human", an unknown value "relayed". Only "human" weighs anything in a gate."""

def link_ids(note: Message) -> tuple[str, ...]:
    """The ids in a note's ``criterion`` field, in order, without blanks ("C6, R2" -> ("C6", "R2"))."""
```

The `client_kind` of a service is `"human"` when `parent(owner) == ROOT`, else `"agent"`; `SRC/reflection/_cases.py` already derives `client = parent(owner)`. Only root may set `source`, and a feedback note's sender is always the case's client, so `verdict_tier` and `client_kind` agree on new notes. On legacy agent notes (no `source`) `verdict_tier` returns `agent`, so the two never disagree.

Reflection data (`SRC/reflection/api.py`). New fields are appended with defaults, so every existing constructor call keeps working:

- `Verdict.tier: str = "human"`: `verdict_tier(message)`.
- `Verdict.links: tuple[str, ...] = ()` and `Verdict.links_tier: str = ""`: the effective link (5.2).
  - The candidates are the verdict note's own `criterion` (with the verdict's tier) and every link note that refers to it (with its own tier).
  - The latest `human`-tier candidate wins. Only when there is none does the latest candidate of any tier win.
  - `links_tier` is the tier of the winning candidate (`""` = no link).
- `Case.client_kind: str = "human"`.
- `Case.relayed_reworks: int = 0`: the tasks of the chain after the first with `source == "relayed"`.
- New frozen dataclass `Assertion(id: str, case: str, verdict: Verdict, about: tuple[str, ...], link: str)`: one regression assertion (5.4). `link` is one of:
  - `"confirmed"`: a human-tier link that names ids;
  - `"none"`: a human-tier link `none`, i.e. the client said there is no lasting rule;
  - `"unconfirmed"`: a relayed link;
  - `""`: no link.
- New pure function `regressions(cases: Sequence[Case]) -> list[Assertion]` (5.4).

Only a verdict with `tier == "human"` weighs 1 in the evidence gate (5.3) and in the health escape count (5.5). `relayed` and `agent` weigh 0 there (08 P2: "in every gate").

`Stats` / `summarize` and the per-version line `feedback {a} accept, {r} reject` are **unchanged** (decision). They count every case's final verdict whatever its tier. They are a description shown to the owner and the user, read by no gate, alarm or health rule. Each relayed or agent verdict is labelled in the case lines next to them (6.2, digest). Tier-separated counts belong to the quality view of Phase 0b (15.12).

### 3.3 Stable criterion ids `C<k>` (derived from `SERVICE.md` history)

A contract criterion's id is fixed by the order in which its exact text first appeared across the contract's versions:

1. Walk `history/SERVICE.v1.md ... history/SERVICE.v<n-1>.md` and then the current `SERVICE.md`, in version order.
2. Within each version, walk its `acceptance` list in list order.
3. The first time a text is seen, it gets `C<k>`, with `k` = 1 + the number of distinct texts seen before.

Consequences:

- v1's criteria are `C1..Cn` in their order, so before any amendment the id equals the number the user sees today.
- An amendment that adds a criterion gives it the next free number. Removing a criterion never renumbers the others, and its id is never reused.
- A reworded criterion is a new text, so it gets a new id: a clarification is a different standard. Re-adding an identical text later gives back its original id, because it is the same criterion.
- A full `acceptance=` replacement keeps the ids of the texts it keeps.
- A retired service takes its directory along. A service defined again from scratch starts at `C1`, and its cases start again too (`Contract.created`).
- Missing history files (deleted by hand) are skipped, and ids are derived from the versions that exist. README states this; it is not otherwise defended.

Data (`SRC/services/api.py`):

```python
@dataclass(frozen=True)
class Criterion:
    id: str        # "C<k>"
    text: str      # the criterion, verbatim
    since: int     # the contract version that first had it
    by: str        # who defined that version (its defined_by): "root" for the user's seat
    current: bool  # it is in the latest version given to number_criteria

    @property
    def amended(self) -> bool:
        """Added by an amendment of the human client: first seen in v2 or later, defined by root, still current (rule (c))."""
        return self.since >= 2 and self.by == ROOT and self.current

def number_criteria(versions: Sequence[tuple[int, str, Sequence[str]]]) -> list[Criterion]:
    """(version, defined_by, acceptance) of every contract version, oldest first -> every criterion it ever had, by id (pure)."""

def criteria_of(numbered: Sequence[Criterion], texts: Sequence[str]) -> list[Criterion]:
    """The criteria with these texts, in the order of ``texts`` (a contract's acceptance list); a text ``numbered`` lacks is skipped."""
```

The stored versions are read by a package-private helper, `SRC/services/_criteria.py:stored_versions(store, owner, name) -> list[tuple[int, str, list[str]]]`. It parses `ServiceStore.versions(owner, name, "SERVICE")` with `_parse.contract_of` and takes `(c.version, c.defined_by or "", c.acceptance)`. Both `ContractServiceCatalog.criteria` and `RuleContractDefiner` use it, the definer to number an amendment in memory before writing it (5.8).

Ids are shown wherever criteria are listed (exact formats in 6.3):
- the request body (`- C1: At most 600 words`);
- the `services` listing;
- the `define_service` amendment reply and errors;
- the amendment note to the owner.

Per-request `extra_acceptance` lines get no id (`- this request only: <text>`). They are not contract criteria and cannot be linked.

### 3.4 Regression assertion ids `R<k>`

`R<k>` is the k-th human-tier rejection (`verdict == "reject"` and `tier == "human"`) among all cases of the service, ordered by the feedback note's id (a microsecond timestamp). "All cases" means those `CaseHistory.cases(owner, service)` returns, i.e. since `Contract.created`.

The ids are stable because notes are immutable and a note's tier never changes after it is written: its `source` is fixed, and so is the owner's parent. Reject-then-accept cases keep their assertions.

### 3.5 `PLAYBOOK.md` frontmatter (written by `services`, its single writer)

A version written by `revise_playbook` gains, after `reason`:

```yaml
evidence:          # the ids the owner cited, normalized (5.3); [] allowed only for the exemptions
- C6
admitted: b        # b | c | first | restore  (which rule admitted it)
restores: 1        # only when the content equals an earlier version's (the version restored)
```

- Versions written by `define_service` / `apply_org` (v1 by the client) get no new keys, so the `PLAYBOOK.md` v1 goldens stay byte-identical.
- `services/_parse.py:playbook_of` parses `evidence` (list of str, default `[]`) and `admitted` (str, default `""`) into two new `Playbook` fields with defaults. Legacy versions read as `admitted: ""`.
- `service.revise` events gain the key `admitted` (`"client"` for a v1 written by `define_service`).

### 3.6 Charter frontmatter (no new field)

`hire` now writes `max_children: 0` for every report hired with `can_hire: false`, whoever hires (root included), because the limit means nothing without the right. Existing charters are never rewritten (D2). The authority bound (5.6) uses the existing `can_hire` and `max_children` keys.

### 3.7 Health fields and thresholds

`SRC/health/api.py:AgentHealth` gains four fields, appended with default 0: `escapes`, `judged`, `rechecks`, `rework_runs` (definitions in 5.5).

`HEALTH_DEFAULTS` drops `max_problem_ratio` and `min_tasks_for_quality` and adds `max_escape_ratio: 0.5` and `min_judged_for_quality: 3`. These are tunable defaults with the same numbers as before. They are renamed because the meaning changed: silently reading an org's tuned problem ratio as an escape ratio would be wrong.

An ORG.md that still sets the old keys keeps working. `SettingsHealthThresholds.thresholds()` validates only the keys of `HEALTH_DEFAULTS` and still returns the others in the merged dict, but no rule reads them. README says so.

## 4. Tool signatures

### 4.1 MCP (exact parameter lists; docstrings in 6.4)

New parameters are optional, except `revise_playbook.evidence`, which is required by design (08 §8, M5). Root-only parameters are registered only on root's server (`me == ROOT`), so agents' surfaces do not grow parameters they would only be refused for.

| Tool | Surface | Signature |
|---|---|---|
| `feedback` | root | `feedback(task_id: str, verdict: str, note: str = "", source: str = "relayed", criterion: list[str] \| None = None, confirms: str \| None = None) -> str` |
| `feedback` | agents with reports or `can_hire` | unchanged: `feedback(task_id: str, verdict: str, note: str = "") -> str` |
| `request` | root | `request(service, inputs=None, title="", note="", extra_acceptance=None, budget=None, revises=None, source: str \| None = None) -> str` |
| `request` | agents | unchanged |
| `delegate` | root | `delegate(to, title, goal, acceptance, inputs=None, budget=None, revises=None, source: str \| None = None) -> str` |
| `delegate` | agents | unchanged |
| `revise_playbook` | owners | `revise_playbook(service: str, content: str, reason: str, evidence: list[str]) -> str` (evidence required, may be `[]`) |
| `hire` | everyone | signature unchanged (`max_children: int = 5` stays); docstring changed (6.4) |

Replies:
- `feedback` with a verdict: `feedback {verdict} recorded on {task_id} for {owner} (message {id}, source {source}{, about <ids>}); it does not wake {owner}`.
- `feedback` with `confirms`: `recorded: rejection {confirms} is about {ids} (source {source}; message {id}); it does not wake {owner}`.
- `request` / `delegate`: unchanged texts.
- `revise_playbook`: unchanged text (`playbook of `{service}` is now v{n}; {client} was told without being woken`). The rule that admitted the revision is in the client's note and in the file.

### 4.2 CLI (as root; help strings in 6.5)

- `hirearchy feedback TASK_ID accept|reject [--note T] [--source {human,relayed}] [--criterion ID ...] [--confirms VERDICT_ID]`. `--source` defaults to `human` (the CLI is the human's own terminal); `--criterion` is repeatable. Both replies show the message id, which `--confirms` needs:
  - with a verdict: `feedback {verdict} on {task_id} -> {owner} (message {id}, source {source}{, about <ids>})`;
  - with `--confirms`: `link on {confirms} -> {owner}: {ids} (message {id}, source {source})`.
- `hirearchy request SERVICE ... [--revises TASK_ID] [--source {human,relayed}]`. The default is `human` when `--revises` is given, otherwise the request is not stamped.
- `hirearchy task ... [--revises TASK_ID]` passes `source="human"` when `--revises` is given. No new flag: the human typed it.
- `hirearchy hire PARENT NAME ...` passes `approved=True` (the user's own decision), so the authority bound (5.6) does not apply to it.
- `hirearchy apply` hires through the blueprint applier, which passes `approved=True` for every hire of the applied blueprint (5.6).
- `revise_playbook` gets no CLI equivalent. It is the owner's tool, and the root override is Phase 1 (08 §4.2).

### 4.3 Ports and facade (Python)

| Where | Signature change |
|---|---|
| `dispatch.MessageSender.send` | `+ source: str \| None = None, criterion: str \| None = None` (keyword-only, after `feedback`, before `wake`) |
| `dispatch.TaskAssigner.delegate` | `+ source: str \| None = None` (positional-or-keyword, after `revises`, like the method's other parameters) |
| `services.ServiceCommands.request` | `+ source: str \| None = None` (keyword-only, after `revises`) |
| `services.ServiceCommands.feedback` | `feedback(actor, task_id, verdict, note="", *, source: str \| None = None, criterion: Sequence[str] \| None = None, confirms: str \| None = None) -> Message` |
| `services.ServiceCommands.revise_playbook` | `revise_playbook(actor, service, content, reason, evidence: Sequence[str]) -> int` (required) |
| `services.ServiceStore` | `+ versions(owner, name, kind: str) -> list[tuple[int, JsonObject, str]]` (8th method). `kind` is `"SERVICE"` or `"PLAYBOOK"`, otherwise `ValueError`. Returns `(version, frontmatter, body)` of the kept files in `history/` and then the current file, sorted by the version the frontmatter states (0 when it states none, as `playbook_history` reads it). When two files state one version, the current file wins. Missing files are skipped. |
| `services.ServiceCatalog` | `+ criteria(owner, name) -> list[Criterion]`, `+ playbook_versions(owner, name) -> list[Playbook]` (7 methods) |
| `services.ServiceEvidence` (new) | 2 methods, 5.3 |
| `access` (pure function) | `children_limit(value: object) -> int` (A3) |
| `access.AuthorityPolicy` | `+ check_grant(actor: str, *, grants_hire: bool, max_children: int \| None) -> None` (3 methods) |
| `hierarchy.Hiring.hire` | `+ approved: bool = False` (keyword-only, last) |
| `Org` facade (`SRC/app/_facade_*.py`) | the same parameters, as pure delegation: `send(source, criterion)`, `delegate(source)`, `request(source)`, `feedback(source, criterion, confirms)`, `revise_playbook(..., evidence)`, `hire(approved)`. `TESTS/architecture/facade_cases.py` passes `evidence` in the `revise_playbook` case. |

Package-private Protocols that change with them (`SRC/services/_protocols.py`):
- `PlaybookRevisions.revise_playbook(+evidence)`, `ServiceRequests.request(+source)`, `ClientFeedback.feedback(+source, +criterion, +confirms)`;
- `PlaybookWriter.write(+extra: Mapping[str, object] | None = None)`;
- `RequestBodies.body(contract, criteria: Sequence[Criterion], given, extra, note)`;
- `ContractAmendment` (5.8).

In `SRC/reflection/_ports.py`:
- `RejectedServices.among` now returns `dict[str, str]` (service -> tier, 6.2);
- `ReflectSection.section(..., rejected: str = "", ...)` takes the tier instead of a bool;
- new `RegressionSection` (5.4).

`Org.revise_playbook` without `evidence` raises `TypeError`. This is the one deliberate break of what callers of `Org` can rely on, and README states it.

### 4.4 The recorded compatibility surface (`TESTS/architecture/org_signatures.json`)

`SRC/app/tests/test_facade_signatures.py` compares every `Org` method's parameters (name, kind, default) and `MessageFields` (in order) with `TESTS/architecture/org_signatures.json`. The record is regenerated deliberately (`uv run python -m hirearchy.app.tests._signatures --write`) in the commit that causes each change. Each diff is stated in the phase report (D1).

| Commit (14) | Recorded change |
|---|---|
| 1 (kernel) | `MessageFields`: `source` and `criterion` (`str \| None`, defaulted) inserted after `feedback`, before `trace`. `Message.__init__` gains the same two parameters there. |
| 3 (rework provenance) | `Org.send` + `source=None` (keyword-only, after `feedback`, before `wake`); `Org.delegate` + `source=None` (positional-or-keyword, after `revises`, as `TaskAssigner.delegate`); `Org.request` + `source=None` (keyword-only, after `revises`). |
| 8 (verdict provenance) | `Org.send` + `criterion=None` (after `source`); `Org.feedback` + `source=None`, `criterion=None`, `confirms=None` (keyword-only). |
| 9 (gate) | `Org.revise_playbook` + `evidence` (positional-or-keyword, no default): the break. |
| 15 (hire bound) | `Org.hire` + `approved=False` (keyword-only, after `inputs`). |

The test `test_the_recorded_surface_is_the_98_methods_of_org_and_the_members_of_message` keeps passing, because no method is added or removed.

## 5. Mechanisms

### 5.1 Provenance stamping (owner: `dispatch.RuleMessageSender`)

`SRC/dispatch/_sender.py:RuleMessageSender.send` applies these rules after the existing route checks and before delivery:

1. `source` or `criterion` given and `actor != ROOT` -> `OrgError` S1. `source` given and not in `SOURCES` -> S2.
2. `criterion` given and the message is neither a verdict note (`type == "note"` and `feedback`) nor a link note (`type == "note"`, no `feedback`, `reply_to` set) -> S3.
3. `actor == ROOT`, `source is None`, and the message is a rework (`type == "task"` and `revises`), a verdict note or a link note (`type == "note"` and (`feedback` or `criterion`)) -> `source = "relayed"`.
4. Otherwise the fields go into the `Message` unchanged.

Why the sender owns this: every path that can create these messages passes through it, including the MCP tools, the CLI, the facade's `send`/`delegate`/`request`/`feedback` and the blueprint applier. So "no agent message carries provenance" and "every root verdict, link and rework has one" are enforced in one layer and tested in one contract suite.

The one exception is `Org.deliver(msg)` (`SRC/app/_facade_delivery.py`): raw delivery of a finished `Message`, used by tests and fixtures, which checks nothing by contract ("Policy is checked by the callers"). It stays as it is. A root verdict built through it without `source` reads as legacy `human` (3.1), and no MCP tool or CLI command reaches it.

- `RecordingSender` (`SRC/dispatch/testing.py`) applies the same rules S1-S3 and the relayed default, so it keeps passing the suite. Its docstring changes from "It checks nothing" to "It checks nothing but provenance (S1-S3 and the `relayed` default), which every `MessageSender` applies".
- `RuleTaskAssigner.delegate` forwards `source`; `services/_request.py` forwards it; `services/_feedback.py` forwards `source` and `criterion`.
- A root `Org.send(..., reply_to=<verdict id>, criterion=...)` from Python passes S3 and acts as a link note without `feedback`'s existence checks. The Python API is root's trusted seat, like the CLI; no MCP tool exposes `criterion` outside `feedback`.

Commit split (14): rules 1 and 2 for `source` and rule 3 for reworks come in commit 3. `criterion`, S3 and rule 3 for notes come in commit 8.

### 5.2 Feedback and the reject-to-criterion link (owner: `services.RuleClientFeedback`)

Messages are immutable, and the user's yes to the contract question arrives a turn after the rejection was recorded. The rejection must be recorded at once, so that the owner reflects on it with the rework (E2 rec 2). The link is therefore either given on the verdict itself (when the user already named it) or recorded later by a **link note** that refers to the verdict. Neither creates a second verdict.

`feedback(actor, task_id, verdict, note="", *, source=None, criterion=None, confirms=None)` checks, in this order (the existing checks first, unchanged):

1. Existing: `task_id` is a service request `actor` sent; `verdict` is in `VERDICTS`; a reject needs a note; the note is at most `FEEDBACK_MAX`; the task has a result. The `confirms` path requires `verdict == "reject"` (step 4), so it always needs a note: the user's answer, verbatim.
2. `actor != ROOT` and (`criterion` or `confirms` given) -> F1. (`source` from an agent is refused by the sender, S1.)
3. `criterion` is normalized by `services.api.normalize_links`: each item stripped, upper-cased when it matches `[cr]\d+`, `none` lower-cased, blanks dropped, duplicates dropped keeping order. Then:
   - more than 5 items, or an item that is none of `C<k>`, `R<k>`, `none` -> F3;
   - `none` with another id -> F4;
   - criterion with `verdict == "accept"` -> F2.
4. `confirms` given:
   - it must be the id of a note in `sent(actor)` with `feedback` set and `reply_to == task_id`, else F7;
   - that note's verdict must be `reject`, else F8a; `verdict` must be `reject`, else F8b;
   - `criterion` must be non-empty, else F9.
5. Existence: `ServiceEvidence.links(owner, service, ids, verdict=confirms)` (5.3) returns the ids, or raises F5 (unknown) or F6 (an `R<k>` that is the confirmed rejection itself).
6. Send, `to=task.to` (the owner, as for every verdict), `wake=False`:
   - **without `confirms`**: as today (`type="note"`, title `feedback on "<title>": <verdict>`, `reply_to=task.id`, `feedback=verdict`, body `FEEDBACK_HEADER + "\n\n" + (note or "accepted")`), plus `source=source` and `criterion=", ".join(ids) or None`;
   - **with `confirms`**: a link note (`type="note"`, title `criterion link on "<title>": <ids>`, `reply_to=confirms`, `criterion=", ".join(ids)`, `source=source`). Its body is `LINK_HEADER.format(confirms=confirms) + "\n\n" + note`, with `LINK_HEADER = "The client says what their rejection {confirms} was about, for reflection only: it does not change any task's acceptance criteria or outcome."`.

`reflection/_cases.py` reads link notes as the root notes in `sent(client)` with `criterion` set, no `feedback`, and `reply_to` equal to the id of a verdict note of the case. They set `Verdict.links` / `links_tier` (3.2) and are never verdicts. `MailRejectedServices` ignores them (they have no `feedback`), so they trigger no Reflect section; the owner sees them in its next batch as an ordinary quiet note.

The tier of a link is the tier of the note that carries it. M1's "tier `human` only when the user confirmed it" is the skill's rule for passing `source="human"` with `criterion` (6.8): only when the user named the criterion themselves or said yes to the question naming it.

### 5.3 The revision-level evidence gate

**Port** (`SRC/services/api.py`). It is implemented by `reflection` and wired by `app`, the same pattern as `dispatch.ReworkContext`, which `services` implements: `services` cannot import `reflection`, which derives the cases.

```python
@dataclass(frozen=True)
class Admission:
    rule: str                  # "b" | "c" | "first" | "restore"
    evidence: tuple[str, ...]  # the normalized ids cited
    detail: str                # one line for the client's note, e.g. "C6 failed in 2 cases the client rejected: <id>, <id>"

@runtime_checkable
class ServiceEvidence(Protocol):
    """What the history of a service proves: the ids a client's verdict may name, and whether a playbook revision is admitted."""

    def links(self, owner: str, service: str, ids: Sequence[str], *, verdict: str | None = None) -> tuple[str, ...]:
        """``ids`` (normalized, 5.2) if each is a criterion the contract has had (C<k>), an existing regression assertion (R<k>, not
        the rejection ``verdict`` itself) or ``none``; ``OrgError`` naming the unknown ones and listing the valid ones otherwise."""

    def admit(self, owner: str, service: str, evidence: Sequence[str], reason: str, *, exempt: str | None = None) -> Admission:
        """Judge a revision of ``owner``'s playbook by rules (b) and (c) of the evidence gate; ``exempt`` ("first", "restore"): only
        resolve the ids. ``OrgError`` with the client question when it is refused, or naming unknown ids."""
```

Pure helpers in `SRC/services/api.py`:
- `normalize_evidence(ids: object) -> tuple[str, ...]`, which raises P1 on failure;
- `normalize_links(ids: object) -> tuple[str, ...]`, with the F3/F4 shape checks only;
- constants `EVIDENCE_MAX = 20`, `EVIDENCE_ID_MAX = 80`, `LINKS_MAX = 5`.

**`revise_playbook` order of checks** (`SRC/services/_playbook.py:RulePlaybookReviser`, new collaborator `evidence: ServiceEvidence`):

1. owner (existing);
2. not locked (existing);
3. reason 1-400 characters (existing);
4. `normalize_evidence(evidence)`: a list of strings, each stripped, blanks and duplicates dropped, at most 20 items, each at most 80 characters without whitespace, `c<k>`/`r<k>` upper-cased; otherwise P1;
5. body: cap and non-empty (existing);
6. identical to the current version -> "no change" (existing);
7. exemption:
   - current version 0 -> `exempt="first"`;
   - otherwise, if the content's body equals the body of an earlier version `k` (the latest such `k`, compared like the "no change" check) -> `restores = k`, and `exempt="restore"` when that version's `by` is the client (`parent(actor) or ROOT`);
8. `admission = evidence.admit(actor, service, ids, reason, exempt=exempt)`;
9. write version `n+1` with the frontmatter of 3.5 (`EventedPlaybookWriter.write` gains `extra` and the event field `admitted`), then notify the client (text in 6.1).

**Decisions on exemptions.**
- *The first version (v0 -> v1) is exempt* (`evidence=[]` allowed).
  - There is no standard yet to change (08 P3 is about changing one). v1 records the procedure the team followed, and the contract's criteria still travel with every request.
  - Requiring evidence would leave a service defined without a playbook with none until two human rejections.
  - Most orgs never take this path: a blueprint or `define_service(playbook=...)` writes v1 as the client.
  - The texts that invite v1 (6.2) ask for the steps the team followed, nothing more, and say that a rule drawn from lessons or a relayed rework is not a step. The residual risk is in 17.
- *The first revision of an existing playbook (v1 -> v2) is not exempt.* E2's wrong rule was exactly the lead's first revision of root's v1; exempting it would fail the E2 replay.
- *Restoring a version the client wrote is exempt.* It can only remove owner text and return to the client's own baseline.
- *Restoring an owner-written version is a revision like any other.* A restore can re-introduce a wrong rule: restoring E2's v2 would. It is recorded with `restores: k`.

**Decision on rule (a)** (deterministic `client-check` / `runtime-check` results): *omitted in 0a.*
- No client- or runtime-owned check *result* exists yet. Verifier coverage lines and team-written tests are team text, which 08 P1 and 10's software row classify as hypotheses.
- The runtime does record facts a check could use, such as the artifact word counts `dispatch/_artifacts.py:ArtifactAnnotator` writes into every result. But nothing maps such a fact to a contract criterion (for example `deliverable.max_words`) and records its pass or fail per case. Building that mapping is the oracle work of Phase 3.
- Refusal texts do not mention checks.
- Pack seeds in rule (c) are likewise omitted: no packs exist until Phase 3.

**Algorithm** (`SRC/reflection/_evidence.py:CaseServiceEvidence(ServiceEvidence)`, collaborators `CaseHistory`, `ServiceCatalog`):

```
crit  = catalog.criteria(owner, service)                 # every C<k>, 3.3
cases = history.cases(owner, service)
H     = regressions(cases)                                # R1..Rm, 5.4
client = parent(owner) or ROOT

resolve each cited id x (in order):
  C<k> in crit                                   -> criterion
  R<k>, 1 <= k <= m                              -> assertion H[k-1]
  the message id of a verdict of a case          -> verdict (with its case)
  the id of any task of a case (head or rework)  -> case
  the id of a result of a task of a case         -> lessons
  anything else                                  -> unknown
if any unknown: refuse G0 (lists them and the valid C/R ids)
if exempt: return Admission(exempt, ids, exemption detail)
if client != ROOT: refuse G3                              # agent client: nothing weighs (08 P2)

subjects = {}; cited_cases = {}; notes = []
  criterion c   -> if c.current: subjects += {c.id}
                   else: notes += "C<k> is no longer in the contract: ..."   # weighs nothing, amended or not
  assertion a   -> subjects += {a.id} | {x in a.about with crit[x].current} ; cited_cases += {a.case}
  verdict v     -> if v is H[j] (a human-tier rejection): as assertion H[j]
                   else notes += "verdict <id> is relayed (...)" | "... an agent client's (...)" | "... an accept"
  case k        -> for every a in H with a.case == k: as assertion a
                   none: notes += "case <id> has no rejection by the client" (+ "; <n> of its reworks were relayed (...)")
  lessons       -> notes += "<id> is a result: its lessons are your team's view"

(c): A = [c for c in crit if c.amended and c.id in subjects]
     A non-empty -> Admission("c", ids, "cites <ids>, which <client> added to the contract (v<since>)")
(b): cases_of(X) = { a.case for a in H if X == a.id or X in a.about }
     the first X in sorted(subjects) with |cases_of(X)| >= 2
       -> Admission("b", ids, "<X> failed in <n> cases the client rejected: <case ids, oldest first>")
refuse:
  single = [a for a in H if a.case in cited_cases or any(X in subjects and |cases_of(X)| == 1 for X in {a.id} | a.about)]
  if single: G2 with g = the assertion with the highest note id in single
             (its case, its words, its `about` C ids)
  else:      G1 with notes + one "C<k> is in the contract since v<since>, ..." note per cited current criterion
             that is not (c)-eligible
```

Notes on the algorithm:
- "Independent cases" means different case heads (08 §4.2 (b), M2). Two rejections in one chain are one case.
- Both cases in (b) must be human-tier: relayed and agent-client verdicts weigh 0 (08 P2). So the "at least one human" clause of 08's (b) is always met by construction, and a second, weightless case cannot complete it.
- Only human-tier links count (`a.about`, 5.4). A link the assistant recorded without the user's yes (`relayed`) shows in the list as unconfirmed but proves nothing.
- The gate counts every case of the service for a cited subject, not only the cited cases: the files are the evidence, and the citation says what the revision is about.
- **A criterion the client removed weighs nothing.** A cited `C<k>` that is no longer in the contract adds no subject, only its note. An assertion's `about` keeps only current criteria, and the assertion still counts under its own `R<k>` (a single case, unless another rejection repeats it). A rule built on a criterion the client took out would contradict the client's own amendment. `links` and G0 still accept every id the contract ever had, so a later rejection can name a removed criterion as what it was about.
- **Rule (c), enforceable form.** This interprets 08's "a contract criterion the client accepted through the contract loop". A criterion is (c)-eligible when it is in the current contract and first appeared in a version v2 or later defined by root (`Criterion.amended`).
  - Every amendment is the client's own `define_service` call (only the parent may make it), and the skill makes it only after the user's yes (6.8).
  - v1 criteria are excluded on purpose: they are often assistant-drafted defaults the user approved as part of a plan. E2's criterion 6 ("a date is never invented") was one, and citing it would otherwise admit E2's wrong rule.
- **Agent clients (nested services).** When `client != ROOT`, nothing can admit a revision: every verdict is a hypothesis, and amendments are the agent's own.
  - Such a playbook keeps v1 (written by the client, or first-version exempt) and can be restored to the client's version. This is 08 §3.1's "unsupervised: no learning", applied now because 0a introduces the weights.
  - Blueprint services are always owned by top-level agents (README), so this affects only services a manager defined for its own report.
- The gate judges citations, not the text: a revision citing an amended criterion can still rewrite other steps. That is the stated limit of the revision-level form (M5); item-level gating and the watch are Phase 1.
- **What the refusal question is for.** G1 and G2 give the owner a question to send its client once, and tell it not to wait for an answer (08 §4.2: "the refusal offers the assistant a client question"). For a human client the skill (6.8) never turns that note into a second question to the user:
  - the one yes/no item the assistant already proposes for the rejection answers it;
  - the owner learns the answer from the amendment note and the link note;
  - a proposal that rests on no rejection of the user's is not put to the user at all (D3).

### 5.4 Regression list (derived; owner: `reflection`)

`regressions(cases)` (pure, `SRC/reflection/api.py`):

```
H = [v for c in cases for v in c.verdicts if v.verdict == "reject" and v.tier == "human"], ordered by v.message.id
R<k> = H[k-1]; case(R<k>) = the case it belongs to
human_links(v) = v.links if v.links_tier == "human" else ()
about(v, seen):                                  # what it is about, resolved through "the same as R<j>"
    out = ()
    for x in human_links(v) except "none":
        C<k> -> out += C<k>
        R<j> (j != own, R<j> not in seen) -> a = about(H[j-1], seen + {own}); out += a if a else (R<j>,)
    return out (deduplicated, order kept)
link = "none" if human_links(v) == ("none",) else "confirmed" if human_links(v) else "unconfirmed" if v.links else ""
```

**Rendering in the owner's prompt.**
- *Where it lives.* `SRC/reflection/_sections.py` gets a new private part, `RegressionListSection`, behind a package-private port `RegressionSection` in `SRC/reflection/_ports.py`. It is composed into `OwnerPromptSections` as an 8th constructor collaborator, wired in `SRC/app/wire_reflection.py:_sections`.
- *When it is shown.* For each owned service whose prompt carries its `# Playbook:` or `# Reflect before you start:` section, and whose list is non-empty, the section of 6.2 is appended once. It goes right after the Playbook section, or right before the Reflect section when only that one is shown.
- *Owner-only.* `OwnerPromptSections.prompt_sections` returns `""` for agents without services, so no other agent's prompt changes because of it.
- *Why with the Playbook section.* It is shown there, not only with Reflect (deviation 15.4), because the manager delegates the review in runs that carry no Reflect section.
- *Size.* At most the 12 newest lines are shown, newest last so the ids ascend. The quoted words of each line are clipped to 300 characters. Older lines are named by count in one line at the top of the list and can be read with `services`.

Lines marked "no lasting rule" (`link == "none"`) stay in the list: they are history, and their ids stay stable. The header and the line itself tell the reader not to check them (6.2), because 08 §4.1.2's explicit "no" closes the assertion.

`ServiceReports.services_text` lists the same assertions per service for the client and the owner: all of them, words clipped to 160 characters. That way the assistant can name "R3" in its question (6.3).

### 5.5 Health: escapes and their attribution (owner: `health`)

Escapes are derived from mail and run logs only; health may import kernel, agents, runs, settings, mail, budget and eligibility.
- New package-private port `EscapeCounter` (`SRC/health/_ports.py`): method `counts(addr) -> EscapeCounts`, where `EscapeCounts` is a NamedTuple of the four numbers.
- Implementation `MailEscapeCounter` (`SRC/health/_escapes.py`), with collaborators `AgentDirectory`, `MailboxReader`, `RunLogReader` and `ClientRework`.

Definitions, for an owner `O` (any agent that received service tasks):

- **Delivery.** A service task `T` in `received(O)` (`T.service` set) whose latest result in `sent(O)` (`latest_results`) is `done`, with result `D`.
  - Tasks stamped `source: relayed` are not deliveries for health. The team did what the assistant asked, so a rejection of it is a relayed error (08 §3.2 cause `relayed-error`), not a team miss.
- **Sign-off `S(T)`.** Look at the results `O` received from its direct reports that answer tasks `O` sent with an id after `T.id`. `S(T)` is the sender of the latest `done` result among them with an id before `D.id`. If there is none (the owner did it alone), `S(T) = O`.
  - In the review loop every template prescribes (author, then verifier, then the owner's own check and `done`), this is the verifier that passed the delivered version.
  - With several checkers in sequence it is the last one; without a checker it is the author.
- **Judged.** The delivery is judged when `received(O)` holds a verdict note `V` with `V.reply_to == T.id`, `V.id > D.id` and `verdict_tier(V) == "human"`.
- **Escape.** A judged delivery is an escape when one such `V` is a `reject`.

Per agent `A` with parent `P`:
- **`judged(A)`, `escapes(A)`**: counted over the deliveries of `O = A` (the owner reported `done`) and over the deliveries of `O = P` with `S(T) == A`. Each delivery is counted once per agent.
- **`rechecks(A)`**: the checker's re-checks after a FAIL, M7's FAIL count approximated (15.13). It counts the tasks `R` in `received(A)` such that all of these hold:
  - `R.revises = T'`, where `T'` is a task of `A` whose latest result `D'` is `done`;
  - `R` is not client-driven (`ClientRework.driven`, unchanged);
  - between `D'.id` and `R.id`, `P` sent at least one task with `revises` set to another direct report: the author rework that `A`'s FAIL caused.

  An author sent back after a check has no such sibling rework in its window (its checker got a fresh task, not a rework), so for an author the number stays 0.
- **`rework_runs(A)`**: for each re-check counted in `rechecks(A)`, the runs (run-log windows) that started between `D'` and `R` in the directories of the reports that received such a rework. These are the author rework runs the FAIL cost.

**Flag.** `low_quality` fires when `judged >= min_judged_for_quality` and `escapes / judged > max_escape_ratio`.
- *Reason:* `"{escapes} of {judged} judged deliveries it signed off were rejected by the client after `done` (escapes); {rechecks} re-check(s) after a FAIL, costing {rework_runs} author rework run(s)"`.
- *No longer counted:* `failed`, `blocked` and rework (08 P6: honest `blocked`/`failed` is never penalized).
- *Text report:* for every agent with `judged > 0`, the segment `escapes {e} of {j} judged, re-checks after a FAIL {r} (author rework runs {w})` follows the `rework` part. The FAIL count is therefore always next to the escape count (M7).
- *JSON:* `OrgHealth.to_dict` carries the four numbers for every agent.

`low_quality` therefore needs human verdicts on service deliveries. In an org without services (research, code or analysis one-offs) it no longer fires, and neither does its review note, until Phase 0b gives one-off tasks verdicts. This is intended: the old rule fired on honest `blocked` and client-driven work (E2). README Health says so, and it is in 17.

**Example: E2 replayed under 0a**, i.e. A2 stamped `relayed`.
- The reviewer's deliveries: memo 1's last rework (requested after Lena's rejection), memo 2, memo 3 and memo 3's rework. That is judged 4, escapes 1 (memo 3's Marta row), so no flag.
- Memo 1's assistant-started rework is not a delivery, so Lena's first rejection is not held against the team.
- E2's false alarm ("3 of 5 tasks failed, blocked or were sent back") cannot recur.

With E2's *actual* files (legacy, no stamps), the assistant's rework reads as not relayed (3.1). The reviewer is then judged 5 with 2 escapes: 0.4, still no flag.

### 5.6 Authority bound (owner: `access`; callers `hierarchy`, `orgfiles`)

`SRC/access/api.py` gets:

```python
CHILDREN_LIMIT_ERROR = "max_children must be a whole number >= 0"   # A3

def children_limit(value: object) -> int:
    """``value`` as a report's ``max_children``: an ``int`` (not a ``bool``) >= 0, else ``OrgError`` A3. Numeric strings are refused:
    YAML, the MCP schema and the CLI's argparse all give ints."""

class AuthorityPolicy(Protocol):
    ...  # check_authority, check_inputs unchanged
    def check_grant(self, actor: str, *, grants_hire: bool, max_children: int | None) -> None:
        """A non-root grantor cannot give a report the right to hire (``grants_hire``: the report gets ``can_hire: true`` it did not
        have; A1) nor a ``max_children`` above its own (``max_children``: the value being set, None when it is not changed; A2).
        Root has no bound. ``OrgError`` otherwise."""
```

`SRC/access/_authority.py:CharterAuthorityPolicy.check_grant` (and `StaticAccess`, which delegates to it):

```
if actor == ROOT: return
mine = actor's charter max_children, read as hire's capacity check reads it (int(...), 5 when absent)
if grants_hire: refuse A1
if max_children is not None and max_children > mine: refuse A2 (with n = max_children, mine)
```

The callers decide what is a change. This is the one rule for both paths.

**At `hire`** (`SRC/hierarchy/_hiring.py:RuleHiring.hire`):

```
n = children_limit(max_children)                 # A3, every hirer (root, CLI and blueprint included), before anything else is decided
if not can_hire: n = 0                           # every hirer
if actor != ROOT:
    existing: the hirer's can_hire, capacity (max_children, default 5), check_authority
    if not approved: authority.check_grant(actor, grants_hire=bool(can_hire), max_children=n)
child_meta["max_children"] = n
```

- `approved=True` is passed only by:
  - the blueprint applier: `SRC/blueprint/_team.py:CharterTeamBuilder.build`, for every hire of the blueprint being applied. It is reached from MCP `apply_org`, which requires `approved=True` and the matching `plan_id`, and from CLI `hirearchy apply`, the user at the terminal applying their own file;
  - the CLI `hire` command, the human at the terminal.
- No MCP tool has the parameter, so an agent can never reach the exemption. An architecture test pins this (11, 12.1).
- This is the enforceable form of "unless root or the approved plan granted it for that position". The plan's grant is exercised when the plan is applied. A later hire for the same position by the lead is a new grant, and it is refused.
- At hire, A2 cannot fire for an agent today: a non-root, non-approved hire either grants `can_hire` (A1, checked first) or gets `n = 0`. The call still passes `n`, so the bound holds unchanged if Phase 2's envelope slack ever lets a lead grant within limits.

**On charter rewrite** (`SRC/orgfiles/_writer.py:GuardedOrgFileWriter.write_noted`, in the existing branch `p.name == "AGENT.md" and actor != ROOT`, after the merge and `check_authority`):

```
old  = frontmatter of the existing AGENT.md, or None when there is none
new  = the frontmatter the file will have:
         merged             (a rewrite of an existing file: the existing merge)
         old                (append=True to an existing file: the appended text goes after the old frontmatter, which stays)
         meta               (no file yet)
grants_hire = bool(new.get("can_hire")) and not bool((old or {}).get("can_hire"))
changed     = "max_children" in new and (old is None or new["max_children"] != old.get("max_children"))
authority.check_grant(actor, grants_hire=grants_hire, max_children=children_limit(new["max_children"]) if changed else None)
```

- Only changes are bounded, and A3 runs only on a changed value.
  - A body-only edit keeps a plan-granted `can_hire: true` and a legacy `max_children: 5` above the lead's own limit, even an odd legacy value. E2's charter edit keeps working.
  - Lowering a value is always allowed.
  - An append never changes the frontmatter, so it is never bounded.
- Root's own rewrites (`actor == ROOT`, the CLI) are outside the branch, as today.
- **Existing charters are not rewritten** (D2). A lead whose report already holds `can_hire: true` keeps it.

The refusal texts A1-A3 are in 6.1.

### 5.7 Default playbook leftover (owner: `blueprint`)

In `SRC/blueprint/_playbooks.py:StepsPlaybookWriter.default_playbook` (line 41), the first maker step reads exactly, today:

```
Delegate to {what} with `budget={grant(k)}`: its part of the request, with the criteria it must meet. On this first run delegate only the steps that need nothing from a teammate.
```

It becomes:

```
Delegate to {what} with `budget={grant(k)}`: its part of the request, with the criteria it must meet.
```

The manager template's own sentence ("On the first run delegate in one batch only the steps that need nothing from a teammate (usually the first)") is about the first run of each task, and it stays.

### 5.8 Criterion ids on the amendment path (owner: `services.RuleContractDefiner`)

Today `RuleContractDefiner.define_service` computes `amended_criteria(name, old.acceptance, ...)` and `changes(old, new)` before `write_contract`. The new version's ids exist in no stored file yet, so they are numbered in memory.

```
stored  = stored_versions(self._store, owner, name)                  # 3.3; [] for a first definition
before  = number_criteria(stored)
current = criteria_of(before, old.acceptance)                         # the old contract's criteria with their ids
accept_n = criteria_lines(acceptance, ...)                            # full replacement, as today
         | amendment.amended_criteria(name, current, add, remove)     # errors list `listed(current)`
after   = number_criteria([*stored, (old.version + 1, actor, accept_n)])
ids     = {c.text: c.id for c in after}                               # covers every old and new text
changes = amendment.changes(old, new, ids)
no change -> OrgError("no change: ... Current criteria:\n" + amendment.listed(current))
write; notify(owner, ..., amendment.diff(old, new, changes, where, criteria_of(after, accept_n)))
reply ... "Acceptance criteria now ({n}):\n" + amendment.listed(criteria_of(after, accept_n))
```

`ContractAmendment` (package-private, `SRC/services/_protocols.py`; implementation `SRC/services/_amend.py:ContractAmender`):

```python
def listed(self, criteria: Sequence[Criterion], indent: str = "") -> str:
    """The criteria, one per line: ``{indent}{id}: {text}``."""

def amended_criteria(self, name: str, current: Sequence[Criterion], add: object, remove: object) -> list[str]:
    """The texts of ``current`` without the ``remove`` criteria (exact text) and with the ``add`` ones appended; the errors say why
    not and list ``current`` with ids."""

def changes(self, old: Contract, new: Contract, ids: Mapping[str, str]) -> list[str]:
    """What differs, one line each; criteria as ``{ids[text]}: {text}`` (``ids``: text -> C<k> for every old and new criterion)."""

def diff(self, old: Contract, new: Contract, changes: Sequence[str], where: str, criteria: Sequence[Criterion]) -> str:
    """The note to the owner: who changed the contract, exactly what, every current criterion with its id, and where to read it."""
```

`numbered` is removed; its unit test in `SRC/services/tests/test_amender.py` becomes a test of `listed`, so the count stays. A first definition's reply is unchanged: it lists no criteria today, and `services` shows the ids.

## 6. Exact texts

Placeholders are in `{braces}`; everything else is literal. `{client}` is the owner's parent (`root` for a top-level owner).

### 6.1 Refusals and notes

| Id | Raised by | Text |
|---|---|---|
| S1 | `dispatch` sender | ``only root (the human's seat) records where a verdict, a link or a rework comes from (`source`, `criterion`); agents' messages carry neither`` |
| S2 | `dispatch` sender | `source must be "human" (the user's own judgement, in their own words) or "relayed" (anything you concluded yourself)` |
| S3 | `dispatch` sender | ``criterion goes only on a verdict (a note with `feedback`) or on a link note that replies to one: use `feedback(..., criterion=...)`.`` |
| F1 | `services` feedback | ``criterion and confirms are root's: they record what the human client said a rejection was about. An agent client's verdict is a hypothesis and names no criterion.`` |
| F2 | `services` feedback | ``criterion says what a rejection was about; an accept has none: leave criterion out.`` |
| F3 | `services` feedback | `criterion is 1-5 ids: C<k> (a criterion of the contract, see `services`), R<k> (an earlier rejection this one repeats) or none (the client said there is no lasting rule), e.g. ["C6"]. Not understood: {items}` |
| F4 | `services` feedback | `none stands alone: it records that the client said this rejection is no lasting rule.` |
| F5 | `reflection` `links` | ``unknown criterion or assertion for `{service}`: {ids}. Its criteria: {C ids or "none"}; its regression assertions: {R ids or "none yet"} (see `services`).`` |
| F6 | `reflection` `links` | `{R} is this rejection itself: name the criterion it is about, or the earlier rejection it repeats.` |
| F7 | `services` feedback | ``confirms must be the id of a rejection you recorded on {task_id} (the message id `feedback` returned): {confirms}`` |
| F8a | `services` feedback | `{confirms} is an accept: only a rejection is linked to a criterion.` |
| F8b | `services` feedback | `confirm a rejection with verdict "reject" (the verdict it repeats).` |
| F9 | `services` feedback | ``a confirmation records what the rejection was about: pass criterion (C<k>, R<k> or none).`` |
| P1 | `services` reviser | `evidence is a list of at most 20 ids, each 1-80 characters without spaces: the regression assertions (R<k>), criteria (C<k>), verdict ids and case ids this revision rests on (see the regression list and the digest in your prompt). Pass [] only for the first playbook, or to restore unchanged a version your parent wrote.` |
| G0 | `reflection` gate | ``unknown evidence for `{service}`: {ids}. Evidence is a criterion ({C ids}), a regression assertion ({R ids or "none yet"}), or the id of a verdict or a case of this service: see the regression list and the digest in your prompt. Nothing was written.`` |
| G1 | `reflection` gate | see below |
| G2 | `reflection` gate | see below |
| G3 | `reflection` gate | ``refused: the client of `{service}` is {client}, an agent, so its verdicts are hypotheses and nothing in this service's history can admit a revision (rules (b) and (c) need the human client). Nothing was written. Follow the playbook and the contract; if you think the playbook must change, send {client} (`send`) what you would change and why.`` |
| A1 | `access` | ``you cannot grant `can_hire: true`: only the user (root) or an approved plan gives an agent the right to hire. Hire it with can_hire false, or ask your parent (`send`) with the reason.`` |
| A2 | `access` | ``you cannot give a report max_children {n}: your own limit is {mine}, and a report's may not be above yours. Use at most {mine}, or ask your parent (`send`).`` |
| A3 | `access` | `max_children must be a whole number >= 0` |

**G1** (no client evidence). `{notes}` are joined with `; `, or read `no evidence given` when the list was empty. `{reason}` is clipped to 200 characters.

```
refused: none of this evidence is the client's own: {notes}. A revision is admitted only when (b) the same criterion or regression assertion failed in 2 different cases the client rejected, or (c) it cites a criterion {client} added to the contract by an amendment ({amended C ids or "none yet"}). Your team's lessons, relayed verdicts (the assistant's own reading) and an agent client's verdicts weigh nothing. Nothing was written: follow the playbook and the contract.
If you think the client wants this from now on, send {client} (`send`) this question once, and do not wait for an answer (it reaches you as a contract change or a criterion link): "We would change how we deliver {service}: {reason}. Is that what you want from now on? If yes, please add it to the contract as a criterion."
```

The notes are exactly:
- `case {id} has no rejection by the client`, plus `; {n} of its reworks were relayed (the assistant's own reading)` when it had relayed reworks;
- `verdict {id} is relayed (the assistant's own reading)`;
- `verdict {id} is an agent client's (a hypothesis)`;
- `verdict {id} is an accept`;
- `{id} is a result: its lessons are your team's view`;
- `{C} is in the contract since v{since}, not added by an amendment, and failed in no case the client rejected` (a current criterion that is not (c)-eligible);
- ``{C} is no longer in the contract: cite a current criterion (see `services`)`` (a cited criterion with `current == False`; `links` and G0 accept every id the contract ever had, so the gate must say why such a citation weighs nothing).

**G2** (one case). `g` is the assertion chosen in 5.3. `{case}` is its case, `{words}` its words clipped to 300 characters, and `{criteria}` its `about` C ids joined with ` / `, or `an existing one`.

```
refused: the client rejected this in one case only ({case}), and the evidence cites no criterion {client} added to the contract by an amendment ({amended C ids or "none yet"}). One case is a reason to ask, not to change how the team works: a lasting requirement goes into the contract first. Nothing was written: apply the client's words to the work at hand without changing the playbook.
Send {client} (`send`) this question once, and do not wait for an answer (it reaches you as a contract change or a criterion link): "In case {case} you said: "{words}". Is that a lasting requirement? If yes, which criterion should say it: a new one, or a clarification of {criteria}?" Revise when the answer is in the contract (cite its new criterion), or when a second case shows the same criterion failing.
```

**Client note after an admitted revision** (`SRC/services/_playbook.py`; it replaces today's three lines):

```
{owner} revised the playbook of service `{service}` to v{n}.
Reason: {reason}
Evidence: {ids joined ", " or "none"}; {admission}
File: {path}
```

- `{admission}` is one of:
  - `admitted: {detail}` (rules b and c);
  - `the first playbook (no evidence needed)`;
  - `restores v{k}, which you wrote (no evidence needed)`;
  - `restores v{k}; admitted: {detail}` (an owner-written version).
- The details are `{X} failed in {n} cases the client rejected: {case ids}` (b) and `cites {C ids}, which {client} added to the contract (v{since})` (c).

### 6.2 The owner's prompt (owner-only sections)

**Regression list** (new; 5.4). `{about}` depends on the line's `link`:
- `confirmed`: `, about {about ids joined ", "}`;
- `none`: `, no lasting rule (the client said so): do not check it`;
- `unconfirmed` with the links `("none",)`: `, possibly a one-off (not confirmed by the client)`;
- `unconfirmed` otherwise: `, about {link ids joined ", "} (not confirmed by the client)`;
- `""`: nothing.

```
# Regression list: {service} (the client's rejections, verbatim)
Each line is something the client rejected. Check every delivery of this service against each line, except the lines marked "no lasting rule" (the client said it was a one-off: do not check them), and copy this list verbatim into every review or check task you delegate for it. A line is not a criterion: it becomes one when your parent adds it to the contract, or ends as "no lasting rule".
- {n} older line(s) not shown: `services` lists them all.
- R1, case {case id}, verdict {note id}{about}: "{words}"
```

The "older line(s)" line appears only when more than 12 assertions exist (the newest 12 are shown, newest last).

**Playbook section, no playbook yet** (`QuotedPlaybookSection`; the locked text is unchanged):
- not reflecting: `No playbook yet: plan as usual; when you report this request, write v1 with revise_playbook: the steps your team followed, nothing more (the first version needs no evidence: evidence=[]).`
- reflecting: `No playbook yet: write v1 now from how the team works (Reflect before you start shows the evidence; rules from lessons or relayed verdicts are not steps), then follow it (the first version needs no evidence: evidence=[]).`

**Reflect before you start** (`EvidenceReflectSection`). The texts below replace the current ones. `{agent_client}` is true when `parent(addr) != ROOT`. `{rejected}` is the tier `MailRejectedServices.among` returns for the service: `"human"` if any rejection in the batch is human-tier, else `"relayed"` if any is relayed, else `"agent"`. It is `""` when there is none. Relayed rejections keep triggering the section, because the rework still benefits from the evidence.

- **The rejecter** (used in both lead texts):
  - `human`: `The client rejected a delivery`;
  - `relayed`: `A relayed rejection arrived (the assistant's own reading, not the client's words)`;
  - `agent`: `Your client, an agent, rejected a delivery (its verdict is a hypothesis)`.
- **Lead, unlocked:**
  - `human`: `{rejecter}: check the delivery against its words, the regression list and the contract before you plan the {what}. One rejection is a reason to look, not to change how the team works: your parent asks the client whether it is a lasting requirement, and the answer reaches you as a contract change or a criterion link. Revise the playbook only as step 3 says, then handle the {what}.`
  - `relayed` or `agent`: `{rejecter}: apply what it asks in this {what} where the contract allows it; it is not the client's evidence, so it cannot change the playbook (step 3). Then handle the {what}.`
  - no rejection: `Before working on the new request:` (unchanged).
- **Lead, locked:** `{rejecter}. The contract is locked, so you cannot revise the playbook: apply what the feedback shows, then handle the {what}.` Only the subject changes from today.
- **Step 1** (locked and unlocked): `Look for what repeats, and for anything the client rejected{" (the regression list)" unless agent_client}. A rejection or a failure is enough to look into on its own; a single slow case is not.`
- **Step 2:**
  - unlocked: `When a lesson of yours conflicts with the client's own feedback (not a relayed verdict), the client is right: apply the feedback in this {what}, and change the playbook only as step 3 says (say so in the reason).`
  - locked: `When a lesson of yours conflicts with the client's own feedback (not a relayed verdict), the client is right: follow the feedback.`
- **Step 3** (unlocked):
  - human client: ``If a change to how the team works would prevent it, call `revise_playbook(service, content, reason, evidence)` with the whole new playbook (at most {cap} words): concrete steps (who does what, in which order, which check), not slogans. Name the cases in the reason, and list in `evidence` what it rests on: regression assertions (R<k>), criteria (C<k>), verdict or case ids. It is admitted only when the same criterion or assertion failed in 2 different cases the client rejected, or when it cites a criterion your parent added to the contract by an amendment; your lessons and relayed verdicts (the assistant's own reading) are not evidence. If it is refused, nothing is written: send your parent the refusal's question once and go on with the playbook as it is. The new version applies to this {what}.``
  - agent client: ``Your client is an agent, so nothing in this service's history can admit a playbook revision (only the first version, or restoring a version your parent wrote): apply the evidence when you plan this {what}, and if you think the playbook must change, send your parent (`send`) what you would change and why.``
- **Restore step** (unlocked, `pb.version >= 2`): ``If the current version did worse than an earlier one, restore that one (read {dir}/history/PLAYBOOK.v<k>.md): revise_playbook with its text unchanged; a version your parent wrote needs evidence=[], any other needs evidence like a revision.``
- **`raise_bar` step** (used by the unlocked steps and by the locked step 3):
  - human client (`parent(addr) == ROOT`), locked or not: ``The playbook may raise the bar, never lower it: the acceptance criteria come from the contract and travel with every request. Your parent asks the client whether a rejection is a lasting requirement; do not send it yourself.``
  - agent client: unchanged (``... If the client's feedback is a lasting requirement, also tell your parent (`send`) so it can add it to the contract.``). An agent client reads its owner's notes in its own run and has no skill that asks for it.
  - Why the locked case too: the skill's one yes/no item asks the human client in both cases (a locked contract can still be amended by the client), so a note from the owner is a redundant "Needs you" item either way. The locked sections change in the same commit anyway (lead and step 2 texts).
- The locked step 3 (apart from its `raise_bar` part) and the last step are unchanged.

**Digest** (`SRC/reflection/_digest.py`). `verdict_chain(c, assertions: Mapping[str, str] | None = None)` and `case_line(c, assertions: Mapping[str, str] | None = None)` take the mapping from verdict note id to `R<k>`. `DigestBuilder` builds it from `regressions(items)`; the dashboard (`SRC/app/wire_dashdata.py`) keeps calling `verdict_chain` without it.
- A human-tier rejection with an id reads `reject R1 "<words>"`.
- A relayed verdict reads `reject (relayed) "<words>"` or `accept (relayed)`.
- For a case whose `client_kind` is `agent`, the line says `client feedback (an agent client: hypotheses): ...` instead of `client feedback: ...`.
- The case line's rework part becomes `{n} rework(s), {r} relayed` when `relayed_reworks > 0`.
- The per-version statistics line is unchanged (3.2).

**`report` hint** (`SRC/services/_hints.py`, for an owner reporting `done`/`failed`, unlocked):
- with a playbook: `Lessons recorded: they are your team's view and are shown before the next request. A playbook revision rests on the client's evidence (evidence: rejections R<k>, criteria C<k>), not on lessons.`
- without one: `This service has no playbook yet: write v1 now with revise_playbook: the steps your team followed, nothing more (the first version needs no evidence: evidence=[]). A rule drawn from your lessons or from a relayed rework is not a step: it needs the client's evidence in a later revision.`

### 6.3 Contract listings with ids

- **Request body** (`TextRequestBodies.body`, which receives the criteria): `## Acceptance criteria` lists `- {C id}: {text}` for the contract's current criteria, then `- this request only: {text}` for each `extra_acceptance` line.
- **`services` listing** (`TextServiceReports._block`):
  - the criteria lines become `    {C id}: {text}` (they were `    {i}. {text}`);
  - after the `record:` line, when the service has assertions: `  regression list (the client's rejections):`, then one line per assertion: `    R{k} (case {id}{, about ids | , about ids (not confirmed) | , no lasting rule | , possibly a one-off (not confirmed)}): "{words clipped 160}"`.
- **`define_service` amendment reply:** `Acceptance criteria now ({n}):` followed by `{C id}: {text}` lines (they were `{i}. {text}`). The amendment errors and the "no change" error list the current criteria the same way (`listed`, 5.8).
- **Amendment note to the owner** (`ContractAmender.diff`, 08 §4.1.3 "the owner is shown the full contract on every amendment"):

```
{who} changed the contract of service `{name}` (v{old} -> v{new}). Read it, and follow the new criteria from the next request on:
- acceptance removed: {C id}: {text}
+ acceptance added: {C id}: {text}
{other change lines, unchanged}
Acceptance criteria now:
{C id}: {text}
...
Contract: {where}
```

Inputs, the deliverable and the budget appear as change lines, as today, and in full in the file the note names.

### 6.4 MCP docstrings

`feedback` (root):

```
Tell the owner of a service whether a delivered request was good: verdict "accept" or "reject".

task_id: a service request (or rework) you sent that has a result. note: required for reject (what was wrong),
optional for accept: the user's own words, verbatim. It costs no run and does not wake the owner; it shows up in
the evidence the owner reviews before its next request (and the moment a rejection arrives). Give it on the user's
own judgement of each delivery, also on a rework: every verdict stays in the case's history, the latest one is the
final verdict, and an earlier reject is still shown to the owner with your words. source: "human" only when the
verdict is the user's own judgement and note holds their words; "relayed" (the default) for anything you concluded
yourself: it is shown to the owner but weighs nothing when it revises its playbook. criterion (reject only): what
the rejection is about, as ids: "C<k>" (a contract criterion, see `services`), "R<k>" (an earlier rejection it
repeats) or "none" (no lasting rule); with source "human" only when the user named it or said yes to your
question naming it. confirms: when that yes comes after you recorded the rejection, call again with the same
task_id, verdict "reject", confirms=<the rejection's message id>, criterion, and the user's answer verbatim as
note: it records the link, not a new verdict. Feedback is for reflection only: it never waives an acceptance
criterion or changes the outcome of the request.
```

It keeps today's sentences, so the phrase `"every verdict stays"` that `SRC/mcp_server/tests/test_service_tools.py:21` pins on root's surface stays, lower-case as today. The only change to them is "your own judgement" becoming "the user's own judgement", to match the skill (6.8).

The agents' `feedback` docstring is unchanged.

`request` (root): the existing docstring, plus before `Returns`: `source (with revises): "human" when the user asked for this rework, "relayed" (the default) when it is your own reading; the owner sees which.`

`delegate` (root): the existing docstring, plus after the `revises` sentence: `source (with revises): "human" when the user asked for this rework, "relayed" (the default) when it is your own reading.`

`revise_playbook`:

```
Write the next version of the playbook of a service you offer: how your team delivers it.

Only the owner can; refused when the contract is locked. content: the WHOLE new playbook in markdown (steps: who
does what, in which order, which check; budget plan; pitfalls), at most playbook_max_words (default 1000) words,
and different from the current one. reason: 1-400 characters naming the cases it rests on. evidence (required):
the ids it rests on, from the regression list and the digest in your prompt: "R<k>" (a rejection by the client),
"C<k>" (a contract criterion), verdict ids, case ids. It is admitted only when the same criterion or regression
assertion failed in 2 different cases the client rejected, or when it cites a criterion your parent added to the
contract by an amendment; your lessons, relayed verdicts and an agent client's verdicts are not evidence. Pass
evidence=[] only for the first playbook (the steps your team followed, nothing more), or to restore unchanged a
version your parent wrote. A refusal writes nothing and gives you a question to send your parent once; do not
wait for the answer (it reaches you as a contract change or a criterion link). The old version is archived; your
parent is told quietly. The playbook may raise the bar, never lower it: the acceptance criteria come from the
contract. Returns the new version, which applies from now on.
```

`hire`: the sentence `can_hire: whether the report may build its own team.` becomes `can_hire: whether the report may build its own team; only root (the user) or an approved plan can grant it. max_children: the most direct reports it may have (for an agent hiring: at most its own); a report without can_hire gets 0.` The `hire` tool's text is the same on every surface, so it is worded for both root and agents.

The MCP root server instructions (`SRC/mcp_server/_instructions.py`) are **unchanged**, byte for byte. They are sent on every connection: the formatted text measures 2699 characters today at this machine's pytest path length, against the `< 2700` of `SRC/skill/tests/test_skill_services.py:42` (and `ROOT_INSTRUCTIONS < 2700` in `SRC/mcp_server/tests/test_instructions.py:33`), so no line can grow. The rule "`source="human"` only with the user's own words" lives in the root `feedback` docstring above, which every root surface carries. The instruction part of the three `surface_root*.txt` goldens therefore stays byte-identical; those goldens change only through tool docstrings and parameters (13).

### 6.5 CLI help strings

- `feedback --source {human,relayed}` (default `human`): `human (default): your own judgement; relayed: someone else's reading of the delivery`.
- `feedback --criterion ID` (repeatable): `what a rejection was about: C<k> (a contract criterion), R<k> (an earlier rejection it repeats) or none (no lasting rule)`.
- `feedback --confirms VERDICT_ID`: `record --criterion for an earlier rejection (its message id) instead of a new verdict; --note is your answer`.
- `request --source {human,relayed}`: `who asked for a rework (--revises): human (you, the default) or relayed`.

### 6.6 Manager role template (`/Volumes/workspace/hirearchy/.worktrees/org-growth-0a/src/hirearchy/roles/manager.md`)

Two bullets are appended to `## Verification before you report`, after the `Every done report pastes the verifier's final coverage line verbatim ...` bullet (line 25). The template body grows from 39 to 41 lines, within the `<= 50` of `SRC/blueprint/tests/test_round_f_guidance.py` (`test_manager_says_feedback_never_waives_a_criterion_and_the_lead_does_not_rewrite`), and every phrase that test pins stays.

```
- For a service request your prompt may show a `# Regression list` (the client's rejections, verbatim). Copy it verbatim into every review or check task you delegate for that request: the verifier checks the deliverable against each line that is not marked "no lasting rule", as well as against the criteria, and lists any line it cannot judge as `ambiguous`.
- Items a verifier lists as `ambiguous` (it cannot tell whether a criterion covers them) are the client's to decide, not yours: never settle one by including or excluding it. Keep the deliverable as verified and put each item at the top of your report under `Questions for the client:` (one line each: the item, the criterion id, the verifier's words), so they are asked before the delivery is accepted. Copy every `Questions for the client:` item from your reports' results into your own report the same way; never answer one yourself.
```

The last sentence carries the items up a nested team: a manager whose report is a sub-lead receives them in a report's result, not in a verifier's review (08 §4.1.4: they "travel up and are put to the client before delivery").

### 6.7 ORG.md rule 10 (`SRC/templates/_documents.py:ORG_RULES`)

Today:

```
10. Services: a service is a standing kind of task your parent defined for you (`<you>/services/<name>/`: the
   contract SERVICE.md is your parent's; the playbook PLAYBOOK.md is yours). Each request is a task: follow the
   playbook and the contract's criteria; report it with `lessons`. Improve the playbook with `revise_playbook` when the
   evidence shown before a new request calls for it; never lower the bar (client feedback never waives a criterion),
   and propose contract changes to your parent.
```

New (no braces, so `.format` is unaffected):

```
10. Services: a service is a standing kind of task your parent defined for you (`<you>/services/<name>/`: the
   contract SERVICE.md is your parent's; the playbook PLAYBOOK.md is yours). Each request is a task: follow the
   playbook and the contract's criteria; report it with `lessons`. Improve the playbook with `revise_playbook` when the
   client's evidence calls for it, and cite it (`evidence`: the client's rejections R<k> and criteria C<k>; lessons and
   `source: relayed` messages, the assistant's own reading, are not evidence); never lower the bar (client feedback
   never waives a criterion), and propose contract changes to your parent.
```

Existing orgs get it with `hirearchy upgrade-rules` (README says so). Rules 1-9 are unchanged.

### 6.8 SKILL.md (`/Volumes/workspace/hirearchy/.worktrees/org-growth-0a/skills/hirearchy/SKILL.md`)

**Size budget (decision).** SKILL.md is exactly 125 lines today, and nine tests assert `len(skill.splitlines()) <= 125`:
- `SRC/skill/tests/test_finish_rules.py:10`, `SRC/skill/tests/test_observe_skill.py:9`, `SRC/skill/tests/test_skill_services.py:16`;
- `SRC/blueprint/tests/test_apply.py:201`, `SRC/blueprint/tests/test_round_f_guidance.py:77`, `SRC/blueprint/tests/test_round_g_assistant.py:46`;
- `SRC/mcp_server/tests/test_blueprint_tools.py:225`, `SRC/mcp_server/tests/test_reclaim_tool.py:60`, `TESTS/e2e/test_round7.py:200`.

The cap is **kept**; no limit in any test changes. The 0a guidance is paid for by condensing existing wording, with no existing rule dropped. Where a passage now leans on a tool docstring, that docstring carries it: the `confirms` mechanics are in the root `feedback` docstring (6.4), and "an amendment passes only what changes" in the `define_service` docstring. The result is exactly 125 lines.

How it was checked: the ten replacements below were applied to a copy of today's file, and a script replicated every assertion of the nine tests plus `SRC/skill/tests/test_install.py:test_skill_names_the_final_tools_and_signatures` and `SRC/blueprint/tests/test_round_g_assistant.py:test_old_markers_are_gone_from_the_product_text` (the line count, every raw and flattened needle, the order assertion of `test_skill_services.py:32`, the forbidden strings). Only the three needles listed below failed. The copy was then deleted. Line numbers are today's; the coder applies the replacements bottom-up.

| # | Today's lines | Becomes | Lines |
|---|---|---|---|
| 1 | 11-12 (precondition) | ``Call `whoami` (or `status`). If the hirearchy tools are not available or error out, tell the user plainly why (the error text) and stop.`` | 2 -> 1 |
| 2 | 14-16 | see block A | 3 -> 2 |
| 3 | 19-21 (step 0b) | see block B | 3 -> 2 |
| 4 | 30-32 (step 1 item 2) | see block C | 3 -> 2 |
| 5 | 40-41 (step 1 item 5) | ``5. Code only: workspace (one new project directory), tests, packaging, commits. Default: tests per criterion, uv/pytest for Python, local commits, never push.`` | 2 -> 1 |
| 6 | 52 (step 2 item 1, last line) | see block D: the consistency question | 1 -> 2 |
| 7 | 55-58 (step 2 items 2-3) | see block E | 4 -> 2 |
| 8 | 93 (step 4, last bullet) | see block F: rework provenance | 1 -> 1 |
| 9 | before 100 (step 5) | new item 3, block G: ambiguous items. Old items 3-4 become 4-5, text unchanged | +2 |
| 10 | 103-109 (old step 5 item 5) | new item 6, block H. Old item 6 (lines 110-112) becomes 7, text unchanged | 7 -> 11 |

Net: -1 -1 -1 -1 -1 +1 -2 0 +2 +4 = 0, so the file stays at 125 lines.

Block A (lines 14-16):

```
- Use only the org this server is bound to: never look for other orgs or read `~/.kiro/settings/mcp.json` or any config/credential
  file. No org yet (`whoami` says "Setup"): `create_org(mission=...)` creates one at the bound path (`path=<absolute path>` only if none is bound).
```

Block B (lines 19-21):

```
Before building anything, call `services()`. If one fits, never build a new org or team: `request(service, inputs)` (tell the user
the inputs and the per-request budget in one line; their asking for it within the approved per-request budget is the approval), then `start()`.
```

Block C (lines 30-32):

```
2. Deliverable: format, length limit, where it goes. Default: markdown, <= 1500 words, in a new `deliverables/` folder in the user's
   current directory (absolute path, e.g. `<cwd>/deliverables/<name>.md`); say so plainly: "I'll put it in a new folder called deliverables here".
```

Block D (line 52). This is the consistency question at definition time (08 §4.1.3). "Outside a rejection" covers a new service and an amendment the user asks for on their own; a conflict found for a reject-driven amendment goes into that reject's one item (block H, D3):

```
   writes nothing and returns the PLAN FOR YOU block, Details and a `plan_id`. Before you call it (or `define_service` outside a
   rejection), read the criteria as a set: if two pull against each other, name the pair and ask ONE question that settles it.
```

Block E (lines 55-58):

```
   delivery place, warnings). A services-only plan says "Nothing runs until you ask for a request": after approval, say they can ask any time.
3. Errors: fix the blueprint and propose again; never ask the user to approve a plan with errors. Revise on feedback the same way (a new `plan_id`).
```

Block F (line 93). One rule for every rework root sends: `request(..., revises=...)` and `delegate(..., revises=...)`, step 5 item 2's send-back on the assistant's own reading, and a change the user asks for after item 3:

```
  ("finished") and you sent more work, call `start()` again. Pass source="human" only on a rework the user asked for (the default is relayed).
```

Block G (new step 5 item 3, inserted before today's line 100). It folds item 2's reading question and the verifier's `ambiguous` items into one message (D3: one question before delivery):

```
3. A done report's "Questions for the client:" (ambiguous items): ask them in plain words, with any question from item 2, in ONE
   message BEFORE you deliver.
```

Block H (new step 5 item 6, replacing today's lines 103-109):

```
6. A service request: after the delivery ask ONE short question ("Keep it, or what should change?") and record
   `feedback(task_id, accept|reject, note, source="human")` only on the user's own judgement of the delivered result, in their words
   ("keep it" / "what's wrong"); "deliver as is" or "I'll read it myself" is not an accept: ask, or record nothing yet. A known unmet
   criterion stays unmet: say so; feedback never waives it; reject needs the user's reason in their words. Your own reading is relayed
   (the default). With each human reject propose exactly ONE item they answer yes or no, naming what it is about by the ids `services()`
   shows ("About C6 / the same as R3: a new criterion, C6 clarified as '...', or a one-off?"); if the new criterion would pull against
   another, make the item the clarification that settles both. On yes: `define_service(owner, name, add_acceptance=[<the new criterion>])`
   (and `remove_acceptance` for a clarification), tell the user the resulting criteria, and record the answer as the link with
   `feedback(..., source="human", confirms=<the rejection's message id>)`: criterion = the id the reply gives (an existing one's if
   nothing changes; "none" for a one-off). An owner's note asking if a rejection is lasting is no new question (only your one item per
   reject asks it): read it with `inbox`, go on, and never reply to it or mention it. Never edit SERVICE.md or PLAYBOOK.md yourself.
```

What block H settles:
- **One question per reject (D3, review 2 MEDIUM 2).** The conflict check runs *before* the item is proposed. A proposed criterion that would pull against an existing one (E2: the new "'before Friday' is that Friday" against C6 "a date is never invented") becomes the clarification of that criterion, so the user still answers one yes or no. No consistency question follows a reject-driven amendment. The separate consistency question (block D) is only for definitions and amendments outside a rejection, and it is asked before the `define_service` call rather than after its reply, so no amendment needs undoing.
- **Owner notes (review 2 LOW 5).** `inbox` lists the unread messages for root and marks them read (`SRC/mcp_server/_tools_identity.py:inbox`), so the note leaves "Needs you" and `progress(wait_seconds=N)` stops returning early on it. Never replying saves the owner a run.
- **The link id.** It is the id the `define_service` reply gives the new or clarified criterion (e.g. `C7`). It is the existing criterion's id when the user says the rejection is about it and wants no change, and `none` for a one-off. The call shape (same `task_id`, verdict `reject`, the answer as `note`) is in the root `feedback` docstring.

What was condensed, with the meaning kept:
- the precondition's three bullets and its wording;
- 0b's closing "monitor and finish as below" (the steps follow anyway);
- the deliverable default's word order;
- step 1 item 5's wrap;
- step 2 items 2-3's wording;
- the old service item's "(an amendment: nothing else is retyped; the playbook stays)", now carried by the `define_service` docstring ("AMENDMENT (the service exists): pass only what changes, the rest stays").

The trigger `("always", "never", "from now on")` is removed on purpose: 08 §4.1.1 asks for the item on *every* human reject.

**Needles of `SRC/skill/tests/test_skill_services.py:17-27` replaced** (in commit 18, the only test edits for the skill):

| Old needle | New needle |
|---|---|
| ``"`feedback(task_id, accept\|reject, note)`"`` | ``'`feedback(task_id, accept\|reject, note, source="human")`'`` |
| `'("always", "never", "from now on")'` | `"exactly ONE item they answer yes or no"` |
| `"propose adding it to the contract as a checkable criterion"` | `"make the item the clarification that settles both"` |

Every other needle of the nine tests stays as it is. That includes ``"`define_service(owner, name, add_acceptance=[<the new criterion>])`"``, `"the resulting criteria"`, `"reject needs the user's reason in their words"` and the order assertion `text.index("Reply briefly") < text.index("record\n   `feedback(")`.

The new test `SRC/skill/tests/test_skill_org_growth.py` (raising `SRC/skill/tests/count.txt`) asserts `<= 125` lines and these flattened phrases:
- `'pass source="human" only on a rework the user asked for'`;
- `"your own reading is relayed (the default)"`;
- `"read the criteria as a set"`;
- `'"questions for the client:"'`;
- `"with any question from item 2, in one message before you deliver"`;
- `"confirms=<the rejection's message id>"`;
- `"only your one item per reject asks it"`;
- `"read it with `inbox`, go on, and never reply to it or mention it"`;
- `"make the item the clarification that settles both"`.

After 0a, SKILL.md has no line of headroom (risk in 17).

### 6.9 Health review action (`SRC/templates/_notices.py:REVIEW_ACTIONS["low_quality"]`)

```
"compare `{a}`'s last checks with the client's rejections it let through (escapes, and its re-checks after a FAIL): if you own a "
"service, make sure its review tasks carry the regression list; edit the BODY of `{a}`'s charter (its frontmatter - tools, "
"inputs, model - is kept automatically) only if the same kind of item escaped more than once, or replace it"
```

### 6.10 README (`/Volumes/workspace/hirearchy/.worktrees/org-growth-0a/README.md`)

**Services and reflection.** The section is pinned at `< 90` lines (the text from the heading to `\n## Health`) by `SRC/blueprint/tests/test_examples.py:201` and `SRC/blueprint/tests/test_round_g_assistant.py:105`. It is 88 lines today.

Decision: everything except the new paragraph is edited in place, at no line cost. The new paragraph is condensed to 8 lines, the fewest that carry 0a's user-visible rules at the section's usual width of about 135 characters; with its blank line the section becomes 97 lines. Both caps are raised to the minimum, `< 98`, with the reason "phase 0a documents source, criterion ids, the regression list and the evidence gate". The change is counted in the phase report (D1).
- Not raising the cap would mean cutting the study E/E2 notes, whose phrases these same tests pin.
- This was measured: the edits below were applied to a copy of the README, and the cap and every needle of the README tests (`test_examples.py:186-201`, `test_round_f_guidance.py:readme`, `test_round_g_assistant.py:97-106`) were checked. Only the needle in the next point fails. The copy was then deleted.
- One needle changes, at `test_examples.py:192`: ``"`revise_playbook(service, content, reason)`"`` becomes ``"`revise_playbook(service, content, reason, evidence)`"``.

The edits:
- Tools table:
  - in the root row, `` `feedback(task_id, accept\|reject, note)` `` becomes `` `feedback(task_id, accept\|reject, note)` (root also: `source`, `criterion`, `confirms`) ``;
  - the owner row becomes `` | an agent that owns a service | `services`, `revise_playbook(service, content, reason, evidence)` | ``.
- CLI: the last two lines of the CLI paragraph become:

```
[--title --note --budget --revises --source human|relayed]`; `feedback TASK_ID accept|reject [--note --source human|relayed --criterion ID
--confirms VERDICT_ID]`; `retire-service OWNER NAME --reason T` (the only way to retire one: there is no MCP tool for it).
```

- "What the owner sees": appended to its last line (`alone (... carry the rest).`): `` With them comes `# Regression list: <service>` (phase 0a, below).``
- "Guardrails": unchanged. The gate is in the new paragraph, and its "a lasting requirement from feedback goes to the parent" stays true.
- A new paragraph after "What study E2 changed", with a blank line before it:

```
**What org growth phase 0a changed.** Root's verdicts and reworks carry `source`: `human` (the user's own judgement, in their words) or
`relayed` (the assistant's own reading; the default; notes written before count as `human`). Contract criteria have stable ids
`C1, C2, ...` (by first appearance across `history/`; removing one never renumbers the others; a deleted history file shifts them), and
the human client's rejections are the regression list `R1, R2, ...`, shown only in the owner's prompt and in `services` (a one-off stays
listed, unchecked). `feedback` can name what a rejection is about (`criterion`, or later `confirms`). `revise_playbook` needs `evidence`:
a revision is admitted only when one criterion or assertion failed in two cases the human client rejected, or when it cites a criterion
the user added by an amendment; otherwise it is refused with the question for the client. The first playbook and restoring the client's
version need none; an agent client's service keeps its playbook. `Org.revise_playbook` needs `evidence` too.
```

**Observability, event table.** Two rows change:
- The `msg.deliver` row lists every key the pipeline emits, in its order. Today's row already omits `supersedes` and `feedback`, and this fixes both: `` | `msg.deliver` | every message: `id`, `type`, `from`, `to`, `title`, `status`, `budget`, `reply_to`, `revises`, `supersedes`, `service`, `feedback`, `source`, `criterion`, `wake`, `hops`, `chars`, `trace_rule` (+ `trace_candidates` when ambiguous) | ``.
- The row `` `agent.hire` / `agent.retire`, `service.define` / `service.revise` / `service.retire` | who, what, returned budget `` ends `who, what, returned budget; `service.revise` also `admitted``.

**Health.** The `low_quality` row becomes:

> | `low_quality` | escapes / judged deliveries above the ratio, once enough were judged. A delivery the agent signed off (as the owner that reported `done`, or as the report whose `done` came last before it) is *judged* when the human client gave a verdict after it, and an *escape* when that verdict was a reject. Reworks the assistant started on its own (`source: relayed`) are not judged. The reason always shows the agent's re-checks after a FAIL and the author rework runs they cost. `failed`, `blocked` and rework no longer count, so an org without services (no client verdicts yet) never gets this flag. | `max_escape_ratio` (0.5), `min_judged_for_quality` (3) |

One sentence follows the table: `The keys max_problem_ratio and min_tasks_for_quality are gone; an ORG.md that still sets them is not an error, and no rule reads them.`

**Rules the runtime enforces.** The bullet `Authority only narrows: a parent cannot grant tools, a workspace or inputs it doesn't have.` becomes `Authority only narrows: a parent cannot grant tools, a workspace or inputs it doesn't have, cannot grant can_hire (only root or an approved plan does), and cannot give a report a max_children above its own, at hire or by rewriting the report's charter; a report hired without can_hire gets max_children 0. Existing charters are not rewritten.`

## 7. Changes per package (Protocols, implementations, fakes, wiring)

Rules for every package below:
- Every changed or new public Protocol keeps at most 8 methods (R7).
- Every new Protocol gets a contract suite over every registered implementation (R8).
- Classes subclass the Protocols they implement and take Protocol-typed collaborators (R6).
- Only `SRC/app/wire_*.py` constructs them.
- **Every explicit implementation of a changed Protocol, fakes and test doubles included, is updated in the same commit as the Protocol** (mypy strict flags any that is not). The ones known today are listed in the table below the main one.

| Package (level) | `api.py` | Private implementation | `testing.py` / contract suites |
|---|---|---|---|
| `kernel` | `Message.source`, `Message.criterion` (meta, parse, render); `SOURCES`; `verdict_tier`; `link_ids` | `_message.py` | unit tests in `SRC/kernel/tests/` |
| `delivery` (L4) | none | `_pipeline.py`: `msg.deliver` gains `source`, `criterion` | `SRC/delivery/tests/` event test |
| `dispatch` (L6) | `MessageSender.send(+source, +criterion)`; `TaskAssigner.delegate(+source)` | `_sender.py` (5.1), `_assigner.py` (forwards) | `RecordingSender` applies S1-S3 and the default (docstring 5.1). `test_contract_message_sender.py`: S1, S2, S3; root rework, verdict and link notes stamped `relayed` by default; explicit `human` kept; a fresh root task unstamped; an agent message never stamped. `test_contract_task_assigner.py`: root rework stamped. |
| `services` (L7) | `Criterion`, `number_criteria`, `criteria_of`, `Admission`, `ServiceEvidence` (2 methods), `normalize_evidence`, `normalize_links`, `EVIDENCE_MAX`, `EVIDENCE_ID_MAX`, `LINKS_MAX`, `LINK_HEADER`; `Playbook.evidence`, `Playbook.admitted`; `ServiceStore.versions`; `ServiceCatalog.criteria`, `.playbook_versions`; `ServiceCommands.request(+source)`, `.feedback(+source, +criterion, +confirms)`, `.revise_playbook(+evidence)` | `_criteria.py` (new: `stored_versions`); `_store.py` (`versions`); `_catalog.py`; `_parse.py`; `_feedback.py` (5.2, new collaborator `ServiceEvidence`); `_playbook.py` (5.3, new collaborator `ServiceEvidence`); `_request.py` (forwards `source`; ids in the body); `_define.py` + `_amend.py` (5.8); `_texts.py` (`EventedPlaybookWriter.write(+extra)`, event `admitted`); `_hints.py` (6.2); `_protocols.py` (4.3) | `MemoryServiceStore.versions`. Stubs `AdmittingServiceEvidence` (admits with rule `b`, returns links as given) and `RefusingServiceEvidence(text)` (refuses every non-exempt `admit` with `text`); `IMPLEMENTATIONS[ServiceEvidence] = [admitting, refusing]`; `_world(..., evidence=AdmittingServiceEvidence())`. New `test_contract_service_evidence.py`, generic: exempt returns `Admission(exempt, ids)`; `admit` returns rule `b`/`c` or raises `OrgError`, nothing else; ids come back normalized. Extended: `test_contract_service_store.py` (+`versions`), `test_contract_service_catalog.py` (+`criteria`, `playbook_versions`), `test_contract_service_commands.py` (+F1-F9, P1, exemptions, link notes, frontmatter 3.5, ids in amendment replies and notes). |
| `reflection` (L8) | `Verdict.tier/links/links_tier`; `Case.client_kind/relayed_reworks`; `Assertion`; `regressions` | `_cases.py` (tiers, link notes, client kind, relayed reworks); `_evidence.py` (new: `CaseServiceEvidence(ServiceEvidence)`); `_digest.py` (labels, R ids); `_sections.py` (`RegressionListSection`; `MailRejectedServices` returns tiers; Reflect and Playbook texts); `_reports.py` (ids and the regression list in `services_text`); `_ports.py` (`RegressionSection`; `RejectedServices`, `ReflectSection` signatures) | Builders keep working (new fields have defaults). `evidence_fs` / `evidence_memory` harnesses. `SRC/reflection/tests/test_case_service_evidence.py` re-collects the services suite against `CaseServiceEvidence` (the `test_service_rework_context.py` pattern) and adds the behaviour tests of 12.1. `test_contract_case_history.py` (+tiers, links, client kind). |
| `health` (L7) | `AgentHealth.escapes/judged/rechecks/rework_runs`; `HEALTH_DEFAULTS` keys | `_escapes.py` (new `MailEscapeCounter`); `_ports.py` (`EscapeCounter`, `EscapeCounts`); `_analyzer.py` (new collaborator, new rule); `_render.py` (segment) | `HealthWorld` builds `MailEscapeCounter` over its mail and runs. `test_contract_health_analyzer.py` (+escapes, sign-off, relayed excluded, rechecks, rework runs, blocked/failed not counted); `test_contract_health_thresholds.py` (new keys). |
| `access` (L2) | `children_limit`, `CHILDREN_LIMIT_ERROR`; `AuthorityPolicy.check_grant` | `_authority.py` | `StaticAccess.check_grant` delegates to `CharterAuthorityPolicy`. `test_contract_authority_policy.py`: A1; A2 (above own refused, equal allowed, absent own limit reads 5); `None` = unchanged allowed; root unbounded. Unit tests of `children_limit`: bool, negative, `"3"`, `3.0` refused; `0` and `7` kept. |
| `hierarchy` (L6) | `Hiring.hire(+approved)` (docstring: the bound and the normalization) | `_hiring.py` (5.6) | `test_contract_hiring.py`: A3 for every hirer; `max_children` 0 without `can_hire` (root and non-root); A1 for a non-root hirer; `approved=True` skips only `check_grant`. `testing.py` wrappers forward `approved`. |
| `orgfiles` (L3) | none (the docstring of `OrgFileWriter.write` names the bound) | `_writer.py` (5.6) | `test_contract_org_file_writer.py`: granting `can_hire` refused; raising `max_children` above the writer's refused; a body-only rewrite of a charter whose `max_children` (5) is above the writer's (2) allowed; an odd legacy value kept by a body-only edit allowed; append mode not bounded; the charter unchanged after a refusal. |
| `templates` (L1) | none | `_documents.py` (rule 10), `_notices.py` (`REVIEW_ACTIONS["low_quality"]`) | colocated text goldens |
| `blueprint` (L8) | none | `_team.py` (`approved=True`), `_playbooks.py` (5.7) | `testing.py` hire fakes accept and record `approved` |
| `roles` (package data) | none | `manager.md` (6.6) | charter goldens |
| `mcp_server` (L11) | none | `_tools_services.py` (root variants of `request`/`feedback`, `revise_playbook` evidence, docstrings); `_tools_tasks.py` (root variant of `delegate`); `_tools_hiring.py` (docstring); `_instructions.py` unchanged (6.4) | `testing.py` fakes follow (below); surface goldens |
| `cli` (L12) | none | `_commands_services.py` (feedback, request flags and replies, the feedback replies with the message id); `_commands_org.py` (`hire` passes `approved=True`; `task` passes `source="human"` with `--revises`) | help goldens, colocated CLI goldens; `cli/tests/_fakes.py` follows (below) |
| `app` | `fields_services.Fields.service_evidence: ServiceEvidence` | `wire_reflection.py`: provides `ServiceEvidence` = `CaseServiceEvidence(b.get(CaseHistory), b.get(ServiceCatalog))` and passes `RegressionListSection` to `OwnerPromptSections` in `_sections`. `wire_services.py`: passes `b.get(ServiceEvidence)` to `RulePlaybookReviser` and `RuleClientFeedback`. `wire_health.py`: builds `MailEscapeCounter`. Facades (4.3). | `test_runtime_fields`, wiring tests; `TESTS/architecture/facade_cases.py`; `TESTS/architecture/org_signatures.json` (4.4) |

Explicit implementations that follow the signature changes:

| Changed Protocol | Implementations outside the rule class |
|---|---|
| `MessageSender.send` | `dispatch/testing.py:RecordingSender`; `mcp_server/testing.py:ScriptedSender`; `cli/tests/_fakes.py:FakeOffice`; the `Sender` doubles in `SRC/app/tests` and `SRC/mcp_server/tests` |
| `TaskAssigner.delegate` | `mcp_server/testing.py:ScriptedTasks`; `blueprint/testing.py:RecordingTaskAssigner`, `FlakyTaskAssigner`; `cli/tests/_fakes.py:FakeOffice`; the `Assigner` doubles in the app and mcp tests |
| `Hiring.hire` | `mcp_server/testing.py:ScriptedHiring`; `blueprint/testing.py:RecordingHiring`, `FlakyHiring`; `cli/tests/_fakes.py:FakeOffice`; `hierarchy/testing.py` wrappers; the `Hirer` doubles in the app and mcp tests |
| `ServiceCommands` | `blueprint/testing.py:RecordingServiceCommands`, `FlakyServiceCommands`; `cli/tests/_fakes.py:FakeServices`; the `Commands` doubles in the app and mcp tests |
| `ServiceCatalog`, `ServiceStore` | `cli/tests/_fakes.py:FakeServices`; `services/testing.py:MemoryServiceStore`; the `Catalog` doubles in the app and mcp tests |
| `AuthorityPolicy` | `access/testing.py:StaticAccess` |
| reflection private ports | `MailRejectedServices`, `EvidenceReflectSection`, and the stubs in `SRC/reflection/tests/_support.py` |

Object graph check: `ServiceCommands -> RulePlaybookReviser -> ServiceEvidence -> CaseServiceEvidence -> CaseHistory -> ServiceCatalog / ServiceHints / MailboxReader`. Nothing in that chain needs `ServiceCommands`, so the lazy builder has no cycle.

The responsibility sentences of ARCHITECTURE 2.2 stay true and unchanged:
- the gate is part of "derives the history of service requests ... from the files";
- the bound is part of "knows what each agent was granted".

## 8. File ownership

No new file, directory or ledger. `TESTS/architecture/ownership.py` and the ARCHITECTURE 2.3 table are unchanged.

| New data | File | Writer (single owner) | Read by |
|---|---|---|---|
| `source`, `criterion` | message files `<addr>/{inbox,read,sent}/*.md` | `mail` (stored through `delivery`); values set by `dispatch.RuleMessageSender` | `reflection`, `health`, `kernel.render` |
| link note (`criterion`, `reply_to` = a verdict id) | message files | as above | `reflection._cases` |
| `evidence`, `admitted`, `restores` | `<owner>/services/<name>/PLAYBOOK.md` (+ `history/`) | `services` (`FsServiceStore` via `EventedPlaybookWriter`) | `services._parse` |
| `max_children: 0` without `can_hire` | `<addr>/AGENT.md` | `agents` (`FsAgentRegistry.create`); value decided by `hierarchy` | `hierarchy`, `prompts` |
| `msg.deliver.source/criterion`, `service.revise.admitted` | `.runtime/events/**` | `telemetry` | `observability` |

ARCHITECTURE.md section 3 (the interface blocks of `kernel`, `dispatch`, `services`, `reflection`, `health`, `access`, `hierarchy`) is updated for the changed Protocols in the documentation commit.

## 9. Error handling

All refusals are `OrgError` (a `ValueError`): recoverable by the caller, with nothing written. The text is what the agent or the assistant reads.

- **MCP:** the tool raises and FastMCP returns the error to the caller. The existing recorder (`SRC/mcp_server/_recorder.py`) writes the `tool.call` event as refused, with the text clipped to 500 characters, so `obs metrics` counts it under `top_refusals`. Nothing else is logged.
- **CLI:** the existing error path prints `error: <text>` to stderr and exits 1.
- **Facade:** raises.

| Operation | Failure | Kind | Caller receives |
|---|---|---|---|
| any `send` | agent passes `source`/`criterion`; bad `source` value; `criterion` on a message that is not a verdict or link note | recoverable | S1 / S2 / S3 |
| `feedback` | existing failures | recoverable | existing texts |
| `feedback` | F1-F9 (shape, existence, confirms) | recoverable | F1-F9 |
| `feedback` | the delivery port raises after validation (disk) | fatal for the call | the exception; no partial note (delivery writes the sender's copy first, as today) |
| `revise_playbook` | evidence malformed | recoverable | P1 |
| `revise_playbook` | unknown evidence id | recoverable | G0 |
| `revise_playbook` | the gate refuses | recoverable: the refusal carries the next step (the client question, sent once) | G1 / G2 / G3 |
| `revise_playbook` | reading history or cases fails (I/O) | fatal for the call | the exception; nothing written (the gate runs before the write) |
| `revise_playbook` | the write fails after admission | fatal for the call | the exception; the store writes the archive copy, then the new file, as today |
| `define_service` (amendment) | ids for the new version | cannot fail separately | numbered in memory from files already read (5.8); errors as today, listing ids |
| `hire` | A3 (any hirer) / A1 / A2 (non-root, not approved) | recoverable | the text; nothing created |
| charter `write` | A1 / A2 / A3 (changed values only) | recoverable | the text; the charter unchanged |
| health | a message or run log it cannot use | unchanged behaviour | the escape counter reads the same mailboxes and run logs through the same ports as the analyzer and adds no new failure mode; a feedback note whose `reply_to` names no delivery is ignored |
| criterion ids | missing history files | tolerated | ids from the files that exist (3.3) |

## 10. Validation of external inputs

| Input | Required | Type and limits | On failure |
|---|---|---|---|
| `feedback.source` (root) | optional; default `relayed` (MCP) / `human` (CLI) | `human` or `relayed` | S2 |
| `feedback.criterion` (root) | optional | list of 1-5 strings, each `C<k>`, `R<k>` (case-insensitive) or `none` alone; reject only; must exist | F2-F6 |
| `feedback.confirms` (root) | optional | the id of a reject note the actor sent on `task_id`; needs `criterion`, verdict `reject` and a note (the user's answer) | F7-F9, existing "reject needs a note" |
| `request.source` / `delegate.source` (root) | optional; default `relayed` for a rework, unset otherwise | `human` or `relayed` | S2 |
| `revise_playbook.evidence` | required (may be `[]`) | list of at most 20 strings, each 1-80 characters without whitespace; blanks and duplicates dropped; `[]` admitted only by the exemptions | P1, then G0-G3 |
| `hire.can_hire` | optional, default false | bool | A1 for a non-root, non-approved grant |
| `hire.max_children` | optional, default 5 | an `int` (not `bool`) >= 0, for every hirer, checked first; then stored as 0 without `can_hire` | A3; A2 above a non-root, non-approved hirer's own (unreachable today, 5.6) |
| charter rewrite `can_hire`, `max_children` | as written | compared with the old charter; only a grant of `can_hire` and a changed `max_children` are judged; a changed `max_children` must be an `int` >= 0 | A1 / A2 / A3 |

## 11. Invariants and the layer that owns each

| Invariant | Owner | Why there |
|---|---|---|
| Only root's messages carry `source`/`criterion`; `criterion` only on verdict and link notes; every root verdict, link and rework has a `source` | `dispatch.RuleMessageSender` | every message path passes through it, including the CLI and the blueprint |
| A verdict's tier is a function of the note alone | `kernel.verdict_tier` | shared vocabulary for `reflection` and `health`, which may not import each other |
| A criterion id never changes meaning | `services.number_criteria` (derived from the contract's history, which only `services` writes) | the contract's owner owns its numbering |
| A link names an existing criterion or assertion | `reflection.CaseServiceEvidence.links` (called by `services` feedback) | R ids are derived from the cases, which only `reflection` derives |
| No playbook revision without (b), (c) or an exemption | `services.RulePlaybookReviser` decides the exemptions (its own versions) and calls the gate; `reflection` judges | `services` is the single writer of the playbook and cannot import `reflection` |
| The regression list is shown only to the owner | `reflection.OwnerPromptSections` | it already gates every service section to owners |
| An escape is counted from human-tier verdicts only, never for a relayed rework | `health.MailEscapeCounter` | health derives everything from files; it uses `kernel.verdict_tier` |
| Authority narrows for `can_hire` and `max_children` | `access.AuthorityPolicy.check_grant` (+ `children_limit`), called by `hierarchy` and `orgfiles` | one policy for both paths that grant (today's `check_authority` pattern) |
| The plan/user exemption is unreachable from an agent | `hierarchy.Hiring.hire(approved=...)`. Only `blueprint/_team.py` and `cli/_commands_org.py` pass it, and the `Org` facade forwards it. | no MCP tool exposes the parameter; pinned by the architecture test `TESTS/architecture/test_hire_approval.py` (12.1) |

## 12. Tests

Strict TDD (R11): every item below is written first and seen failing for the right reason.
- Unit tests run against the in-memory worlds.
- Contract suites run against every registered implementation.
- The golden suite and the e2e test cover the wired application.

Tests that assert the old behaviour on purpose are rewritten to the new behaviour in the commit that changes it (D1); none is deleted, so the floors of `TESTS/architecture/test_collected_count.py` hold. Examples: `health/tests/test_flags_effort.py`, `test_health.py` and `test_robustness.py` for the old `low_quality` keys; `services/tests/test_amender.py` for `numbered`; the about 12 tests that hire with `can_hire=True` as a non-root actor, which pass `approved=True`. Every commit that adds tests to a colocated directory raises its `count.txt` (`uv run python -m tests.architecture.collected_count --write`).

**Rule for existing scenarios (review 2 LOW 4).** The new defaults would silently move existing scenarios onto the relayed path, and the real gate would refuse their revisions. So:
- Every test helper and golden scenario that stands for the user's own verdict or rework passes `source="human"`. The relayed path gets its own new tests. The ones known today:
  - reworks, in commit 3: `SRC/reflection/tests/_support.py:rework` (line 79); `TESTS/golden/test_golden_prompts.py:67`; `TESTS/testkit/dash_fixtures.py:170` (a root `delegate(revises=...)`);
  - verdicts, in commit 8: `SRC/reflection/tests/_support.py:rate` (line 68, behind every reflection section and digest golden); `TESTS/golden/test_golden_files.py:54,160`; `TESTS/golden/test_golden_prompts.py:64`; `TESTS/testkit/dash_fixtures.py:168,180`; `SRC/mcp_server/tests/test_service_tools.py:93`; `SRC/app/tests/test_services_facade.py:47`.
- Tests that assert only a tool's reply text may keep the default, because those replies do not depend on the tier. An example is `SRC/mcp_server/tests/test_service_tools.py:31,40` (root MCP `request(revises=...)`).
- With these, `dashboard/tests/golden/*` stays byte-identical (13).
- Every app-level test that revises a playbook past v1 makes the revision admissible, in commit 9: two human-tier rejections in two cases linked to one criterion, or a root amendment cited in `evidence`. The known ones:
  - `TESTS/golden/test_golden_events.py:81` uses the amendment: `org.define_service(ROOT, "ceo", "brief", add_acceptance=["At most 300 words"])` before it, then `evidence=["C2"]`. That gives `service.revise.admitted == "c"` in `events/line_shapes.txt`.
  - `TESTS/golden/test_golden_files.py:162` gets a second case with a human reject linked to `C1`.
  - `SRC/mcp_server/tests/test_service_tools.py:94` does the same, so its `contract v1, playbook v2` assertion holds.
  - `SRC/mcp_server/tests/test_service_tools.py:61` and `:143` (v2 through the owner's MCP server) each cite a root amendment made just before them. `:147` asserts the new `report` hint of 6.2 instead of "Lessons recorded. If they call for a playbook change now, use revise_playbook".
  - `SRC/mcp_server/tests/test_service_tools.py:175` passes `evidence=[]`, so the MCP schema accepts the call and the lock refusal, which is checked before the evidence (5.3, step 2), is still what the test sees.
- A first version passes `evidence=[]`, for example `SRC/app/tests/test_services_facade.py:49` (returns 1) and the MCP calls of `test_service_tools.py:49,128`.
- The unit and contract tests of `services` keep the stub. `services.testing` worlds (and `ReflectionWorld`, which is built on them) default to `AdmittingServiceEvidence`, so `reflection/tests/_support.py:revise` passes `evidence=("R1",)` and keeps working. The real gate is exercised by `SRC/reflection/tests/test_case_service_evidence.py`, which calls `CaseServiceEvidence.links/admit` directly over a `ReflectionWorld`'s history and catalog, and through the wired application by the app tests above, the goldens and the e2e test (12.2).

### 12.1 Unit and contract tests (what each proves)

- **kernel**:
  - `verdict_tier`: root with no `source` -> human; root+human; root+relayed; root+garbage -> relayed; agent -> agent;
  - `link_ids`;
  - `Message` round trip with and without the fields (absent fields leave the file byte-identical);
  - the `render` header;
  - the dataclass field order.
- **dispatch** (contract suite of `MessageSender`, all four worlds):
  - S1 for an agent's `source` and `criterion`; S2; S3 for `criterion` on a task and on a plain note without `reply_to`;
  - root rework, root verdict note and root link note stamped `relayed` by default; explicit `human` kept; a fresh root task unstamped;
  - `TaskAssigner`: root `delegate(revises=...)` stamped; `source="human"` kept.
- **services**:
  - `number_criteria`: v1 order; an amendment appends; removal keeps ids; a reworded text is new; an identical re-added text keeps its id; a full replacement keeps the kept texts' ids; `amended` only for v>=2 by root and current; a version defined by an agent is not amended. `criteria_of` order.
  - `ServiceStore.versions`: history then current, sorted by version, missing files skipped, the current file wins a tie, `ValueError` for another kind.
  - Amendment path (5.8): the reply, the errors and the owner's note carry the ids of the new version; a text added and then removed, then re-added keeps its id; the note lists every current criterion.
  - Feedback: F1-F4 and F7-F9 with `AdmittingServiceEvidence`. F5 and F6 are raised only by the real `links`, so they are tested in `reflection` against `CaseServiceEvidence.links` and end to end through the wired application. Also tested: the link note's frontmatter, body, recipient (`task.to`) and required note; no second verdict; the `ServiceCommands.feedback` docstring keeps "stays in the case" and has no "replaces" (pinned by `SRC/mcp_server/tests/test_service_tools.py:18`).
  - `revise_playbook`: P1; the first-version exemption; the client-version restore exemption with `restores`; an owner-version restore goes to the gate; `RefusingServiceEvidence`'s text passes through unchanged and nothing is written; the frontmatter of 3.5; the client's note (6.1); the event `admitted`.
- **reflection** (`CaseServiceEvidence` over the fs and memory worlds):
  - G0 for every kind of unknown id; G3 for an agent client;
  - (b) admits two human rejections in two cases linked to the same C id, and through "the same as R<j>"; (b) refuses two rejections in one case (G2);
  - relayed and agent rejections do not count (G1 with their notes); an unconfirmed link does not count;
  - (c) admits a cited amended criterion, and also one reached through a cited assertion's `about`; (c) refuses a v1 criterion (G1 note);
  - a cited criterion the client removed (amended or not) adds no subject and gives the note `{C} is no longer in the contract: cite a current criterion (see `services`)`; two human rejections linked only to a removed criterion do not admit by (b);
  - a cited case resolves to its human rejections; a result id gives the lessons note;
  - the question texts carry the reason, or the words clipped as specified; G2 picks the assertion with the highest note id;
  - `links`: F5, F6, `none`.
  - `regressions`: ordering, tiers, `about` resolution with cycles, `link` values (`confirmed`, `none`, `unconfirmed`, `""`).
  - `_cases`: tiers; link notes are not verdicts; the latest human link wins; client kind; relayed reworks.
  - Sections:
    - the regression list appears with the Playbook section, alone before Reflect, never for a non-owner, cut at 12 lines with the "older" line first;
    - "no lasting rule" lines carry "do not check it";
    - the lead texts per tier (human, relayed, agent; locked and unlocked);
    - step 1 without "(the regression list)" for an agent client; steps 2 and 3 for human and agent clients; the restore step; the no-playbook texts;
    - the `raise_bar` step: "do not send it yourself" for a human client (locked and unlocked), today's text for an agent client;
    - `MailRejectedServices` tier precedence.
  - Digest labels and R ids; `services_text` ids and assertions.
- **health** (`MailEscapeCounter` and the analyzer over the memory and fs worlds):
  - sign-off is the last report `done` before the owner's `done`; the owner signs alone when it had no report;
  - a relayed rework is not judged; an agent client's verdict is not judged; a verdict before the `done` is not judged;
  - escapes are counted for the owner and the sign-off, once each;
  - `rechecks` counts only reworks of a `done` task with a sibling rework in the window, client-driven excluded, and stays 0 for an author sent back after a check;
  - `rework_runs` counts the author's run windows between the FAIL and the re-check;
  - `low_quality` needs `min_judged_for_quality`; `failed`/`blocked`/rework no longer flag; an org without service verdicts never flags;
  - the reason text; the render segment only when `judged > 0`; the thresholds with the new keys, and the old keys carried but unread.
- **access**: A1 (`grants_hire`; root exempt); A2 (above own refused; equal allowed; `None` allowed; an absent own limit reads 5); `children_limit` (A3 for bool, negative, numeric string, float).
- **hierarchy**: A3 for root and non-root hirers; normalization to 0 without `can_hire` (root and non-root); A1 at hire for a non-root hirer; `approved=True` skips only the grant check; the existing capacity and authority checks still run.
- **orgfiles**:
  - a rewrite that grants `can_hire` is refused;
  - a rewrite that raises `max_children` above the writer's is refused;
  - a body-only rewrite of a charter whose `max_children` (5) is above the writer's (2) is allowed; so is one whose legacy value is `"x"`;
  - an append to `AGENT.md` is not bounded;
  - the charter is unchanged after a refusal.
- **blueprint**: the default playbook no longer contains the sentence; apply hires with `approved=True` (a plan whose sub-lead has `can_hire` and more children than its lead applies, through MCP `apply_org` and CLI `apply`).
- **architecture** (`TESTS/architecture/test_hire_approval.py`, new): an AST scan of `src/hirearchy/**/*.py`, excluding `tests/` and `testing.py`. Every call of an attribute named `hire` that passes the keyword `approved` is in `blueprint/_team.py`, `cli/_commands_org.py`, or `app/_facade_hierarchy.py` (forwarding its own parameter). No `mcp_server` module passes it.
- **mcp_server / cli**:
  - root variants of `request`, `feedback` and `delegate`; the agents' variants unchanged;
  - `revise_playbook` without `evidence` is a schema error;
  - CLI defaults and replies: `--source human`; `request --revises` stamps human; `task --revises` stamps human; `hire` approved; the `feedback` and `--confirms` replies, each with `(message {id}, source {source})`.
- **templates / roles / skill / README**:
  - string tests that rule 10, the review action, the two manager bullets (with the forwarding sentence) and the SKILL.md passages (6.6-6.9) are present verbatim;
  - the manager body stays at most 50 lines;
  - SKILL.md stays at most 125 lines, with the new needles of 6.8 in `test_skill_org_growth.py` and the three replaced needles of `test_skill_services.py`;
  - the README Services section stays under 98 lines (`test_examples.py:201`, `test_round_g_assistant.py:105`), with the replaced needle of `test_examples.py:192`;
  - the formatted root instructions stay under 2700 characters (unchanged test).

### 12.2 Deterministic end-to-end test: the E2 chain (`/Volumes/workspace/hirearchy/.worktrees/org-growth-0a/tests/e2e/test_org_growth_0a.py`)

No scheduler and no LLM: the team's actions go through the `Org` facade, and the calls under test go through the in-process MCP servers of root and of `lead`. The helpers are `testkit.e2e_world.build_server(org, me)` and the `call` / `fails` helpers, copied from `test_goal_to_delivery.py` into this module as that file does. Health is read with `testkit.e2e_world.agent_health(org, addr)`, i.e. `org.runtime.health_analyzer.agent_health(addr)`.

**Structure.** Every test function builds its own world in its own `tmp_path` and replays what it needs, so each block also runs alone (`-k`). Nothing is shared between test functions, and there is no module-scoped state.
- `world(tmp_path) -> World`: `Org.init`; `org.hire(ROOT, "lead", "Lead", ..., can_hire=True, max_children=3)`; through lead's MCP server, `hire(name="writer", ...)` and `hire(name="reviewer", ...)` (default `max_children=5`); `org.define_service(ROOT, "lead", "meeting-memo", ...)` with six criteria, among them C5 `One row for every commitment, including informal ones` and C6 `A date is never invented`, and a playbook v1 (by root). It returns the org, the two servers and an id map.
- `deliver(w, task_id)`: lead delegates to the writer (who writes `work/memo.md` and reports `done`), then to the reviewer (who reports `done`), then reports `done` to root with `lessons`.
- `chain(w, through: int) -> dict[str, str]`: replays blocks 2 to `through` (the actions only, without their asserts) and returns the ids `A1, A2, N1, A3, B1, ...`. Each block's test calls `chain(w, through=k - 1)` and then runs its own actions and asserts.

Blocks (one test function each, `test_<n>_<name>`):

1. **Hires are bounded.** `lead/writer/AGENT.md` has `can_hire: false`, `max_children: 0`.
2. **Assistant-initiated rework is relayed.** Root `request(meeting-memo, {notes_file: ...})` -> A1; `deliver(A1)`. Root `request(..., revises=A1, note="use none for informal dates")` without `source` -> A2. A2's file has `source: relayed`. `deliver(A2)`.
3. **The E2 v2 rule is refused at zero run cost.** Lead `revise_playbook(content=<v1 + "informal dates are none">, reason="Lesson: informal time references must be none", evidence=[A1])` fails with G1. The refusal contains the note `case A1 has no rejection by the client; 1 of its reworks were relayed (the assistant's own reading)` and the question quoting the reason.
   - With `evidence=["C6"]` it fails with the note that C6 is in the contract since v1 and not added by an amendment.
   - With `evidence=[]` it fails with `no evidence given`.
   - `PLAYBOOK.md` is still v1, and no run log exists for the attempt (it is a tool call).
4. **A human reject names its criterion and reaches the owner's prompt.**
   - Root `feedback(A2, "reject", note="Sam's 'before Friday' has a date: Oct 9.", source="human")` -> note N1 (`source: human`).
   - Root `feedback(A2, "reject", note="It is about C6; no new rule.", source="human", criterion=["C6"], confirms=N1)` -> a link note: no `feedback` field, `reply_to: N1`, `criterion: C6`, `to: lead`. The case still has one verdict.
   - Root `request(..., revises=A2, note=<her corrections>, source="human")` -> A3 (`source: human`).
   - `batch = org.begin_run("lead")`; `org.run_prompt("lead", batch)` contains `# Regression list: meeting-memo (the client's rejections, verbatim)`, ``- R1, case {A1}, verdict {N1}, about C6: "Sam's 'before Friday' has a date: Oct 9."``, the Reflect section and the human lead text `The client rejected a delivery: check the delivery against its words`. `org.end_run("lead", ok=True)`.
   - The writer's prompt, built the same way, contains no `Regression list`.
5. **One case is a question, not a rule.** Lead `revise_playbook(..., evidence=["R1"])` fails with G2, containing `the client rejected this in one case only ({A1})`, `In case {A1} you said: "Sam's 'before Friday' has a date: Oct 9."` and `a clarification of C6`.
6. **A second independent human reject on the same criterion admits a revision.**
   - `deliver(A3)`; root `feedback(A3, "accept", note="This version is right.", source="human")`.
   - Root `request(...)` -> B1; `deliver(B1)`; root `feedback(B1, "reject", note="Lee's 'next week' has a date too.", source="human", criterion=["C6"])` -> R2.
   - Lead `revise_playbook(content=<v1 + the date rule>, reason="C6 failed in A1 and B1", evidence=["C6"])` returns v2.
   - `PLAYBOOK.md` has `admitted: b` and `evidence: [C6]`; root's quiet note contains `admitted: C6 failed in 2 cases the client rejected: {A1}, {B1}`.
7. **A criterion added by amendment admits a revision (rule c).**
   - Root `define_service(owner="lead", name="meeting-memo", add_acceptance=["'before <weekday>' is that weekday's date"])`. The reply lists `C7: 'before <weekday>' is that weekday's date`, and lead's amendment note lists `Acceptance criteria now:` with C1-C7.
   - Lead `revise_playbook(..., evidence=["C7"])` returns v3 with `admitted: c`.
8. **Health counts the escape, not the relayed rework.**
   - `agent_health(org, "lead/reviewer")`: `judged == 2` (A3, B1), `escapes == 1` (B1), `rechecks == 0`, no `low_quality` (2 judged < 3). A2's rejection is not counted.
   - `agent_health(org, "lead")` has the same `judged` and `escapes`.
9. **A non-root lead cannot grant hiring rights.**
   - Lead `hire(name="sub", ..., can_hire=True)` fails with A1.
   - `org.hire("lead", "sub", "Sub-lead", ..., can_hire=True, max_children=1, approved=True)` (the user's own hire, as the CLI does) succeeds.
10. **... nor raise a limit by charter rewrite** (after the hires of block 9):
    - Lead `write(path="lead/writer/AGENT.md", content="---\nrole: Writer\ncan_hire: true\n---\nWrite.")` fails with A1.
    - `write(path="lead/sub/AGENT.md", content="---\nrole: Sub-lead\nmax_children: 5\n---\nLead.")` fails with A2 (`your own limit is 3`).
    - `max_children: 3` succeeds.
    - A body-only rewrite of `lead/sub/AGENT.md` succeeds and keeps `can_hire: true`.

The parts of 08's exit criterion that depend on the LLM assistant and reviewer are outcomes of the live E2-replay study, run as a separate workflow after the merge (D5). These are: one yes/no contract proposal per reject, no second question from the owner's refusal note, and the Marta row asked about before delivery. 12.1 only pins the template and skill texts that ask for them.

## 13. Golden impact (estimate; every regenerated diff is reviewed and its count stated in the phase report, D1)

Goldens are regenerated with `HIREARCHY_UPDATE_GOLDEN=1 uv run pytest tests/golden -k <subset>`, plus the colocated golden tests of the packages named. Each regeneration is in the commit whose change causes it (14). After every regeneration the golden suite runs again without the update flag.

**Top-level `TESTS/golden/expected` (134 files): about 44 change.**

| Files | Changed / total | Why (commit) |
|---|---|---|
| `mcp/surface_*.txt` | 10 / 10 | `hire` docstring on every surface (15); the 3 root surfaces also get the `request`/`delegate` `source` (3) and the `feedback` parameters and docstring (8), while their server-instructions part stays byte-identical (6.4); `surface_manager.txt` also gets `revise_playbook.evidence` (9) |
| `prompts/*.txt` | 7 / 8 | ORG.md rule 10 (11). `service_owner_reflect.txt` also gets the ids (5), the rendered `source` of the rework (3) and of the verdict (8), the Reflect step 3 (9), the regression list, R ids and lead/step texts (10). `service_owner_no_playbook.txt` also gets the ids (5) and the no-playbook texts (9). |
| `files/org_md_*.md` | 2 / 3 | rule 10 (11) |
| `messages/feedback_note.md`, `rendered_inbox.txt`, `service_request_task.md`, `notice_templates.txt` | 4 / 9 | `source` on the verdict (8); criterion ids (5); the `low_quality` action (17) |
| `charters/hire.md`, `apply_service_example.md`, `apply_research_example.md`, `apply_code_template.md` | 4 / 5 | `ceo/eng` `max_children: 5` -> 0 (15); the manager template (12); the playbook leftover and the request ids in `apply_service_example.md` (13, 5) |
| `plans/*` (the 8 `propose_*_service.txt` and `example_blueprint-service.txt`) | 9 / 27 | the playbook leftover (13) |
| `services/service_and_playbook_files.md`, `services_text_root.txt` | 2 / 2 | the scenario's revision cites evidence: a second case with a human reject on C1 and the frontmatter of 3.5 (9); ids and the regression list (5, 10) |
| `cli/help_feedback.txt`, `help_request.txt`, `services.txt`, `obs_events_json.txt`, `health_json.txt` | 5 / 64 | flags (8, 3); ids (5); null `source`/`criterion` keys in `msg.deliver` (2); the four health numbers (17) |
| `events/line_shapes.txt` | 1 / 1 | `msg.deliver.source/criterion` (2); `service.revise.admitted` (9) |

To verify (expected unchanged): `cli/dash_once.txt` and `cli/health.txt`. Their scenarios have no service verdict, so no health segment and no ids.

**Must stay byte-identical** (90 files):
- `kiro/*` (5);
- 18 of the 27 plan files: the 14 non-service ones (8 `propose_*` without `_service`, 4 `template_*.yaml` without `_service`, 2 `example_blueprint-research*`) and the 4 `template_*_service.yaml`, which do not contain the generated playbook;
- `messages/task.md`, `note_with_budget.md`, `result_with_artifacts_and_lessons.md`, `runtime_notice.md`, `runtime_notice_no_wake.md`;
- `charters/hired_agent_layout.txt`, `files/org_layout.txt`, `prompts/files_block_variants.txt`;
- the other 59 CLI outputs: `check*`, `status`, `progress*`, `inbox*`, `obs_now*`, `obs_trace`, `obs_metrics*`, the text forms `obs_events.txt` and `obs_events_of_trace.txt` (they omit null keys), errors, `fresh_*`, the remaining `help_*` (`help_hire.txt` and `help_task.txt` included: no new flag), `dash_once.txt`, `health.txt`.

**Colocated goldens (`SRC/*/tests/expected`, `SRC/*/tests/golden`):**

| Package | Changed / total | Which |
|---|---|---|
| `reflection` | about 17 / 24 | the 7 `sections_*` with a Playbook or Reflect section (texts, regression list, the `raise_bar` step of the 6 that hold it); the 8 `services_*` (ids; regression list where rejections exist); `digest_rejected_then_accepted.txt` (R1); to verify: `digest_eight_long_cases.txt`, `digest_three_playbook_versions.txt` (only if they hold rejections). Unchanged: `totals_*` (4), `sections_owner_without_requests.txt`, `digest_delivered_and_accepted.txt`. |
| `health` | 6 / 6 | `low_quality` gone from the scenarios; the JSON and the `repr` gain the four numbers |
| `templates` | 7 / 45 | `org_rules_*` (5), `review_item_low_quality*.txt` (2) |
| `bootstrap` | 3 / 5 | `org_md_*` (rule 10) |
| `upgrade` | 3 / 6 | `new_org_md.md`, `dry_run_text.txt`, `written_text.txt` (rule 10) |
| `cli` | 11 / 116 | `help_feedback.txt`, `help_request.txt`, `bad_verdict.txt` (its `usage: hirearchy feedback` line gains the new flags, 8), `services.txt`, `feedback.txt` (reply with the message id), `define_service_amend_acceptance.txt`, `define_service_amend_deliverable.txt` (ids), `obs_events_json.txt`, `health_json.txt`, `upgrade_rules_old.txt`, `upgrade_rules_old_dry_run.txt`; to verify: `define_service_error.txt`, `define_service.txt`, `health.txt`, `health_agent.txt` |
| `blueprint` (`golden/second_half.json`, one file) | 1 / 2 | 22 of its strings: the 8 `charters/*/lead` entries get the manager bullets (12); the 10 `plans/*-service/*/details\|propose` entries and the 4 `playbooks/*` entries lose the leftover sentence (13). Its `plan_ids` hash the blueprint only (`_identity.py`) and stay; `validate_corpus.json` stays. |
| `dashboard` (`golden/*.txt`) | 0 / 34 | stays byte-identical, because `TESTS/testkit/dash_fixtures.py` passes `source="human"` (rule in 12): `verdict_chain` without the R mapping renders human verdicts as today, and the contract view lists criteria in its own format. To verify: `wide-3-services-detail.txt`. |
| `observability`, `progress`, `review` | 0 / 98, 0 / 12, 0 / 6 | `messages_*.json` lists its own message fields, and `source`/`criterion` are not added to it in 0a |

`blueprint/tests/golden/second_half.json` has no update flag: `SRC/blueprint/tests/_plans.py` says it was captured from the pre-refactor `blueprint.py`. In commits 12 and 13 it is regenerated by a one-off script that is run once and not committed:
- it loads the JSON;
- it applies the exact text change of the commit to every string: commit 12 inserts the two bullets of 6.6 after the coverage-line bullet; commit 13 deletes ` On this first run delegate only the steps that need nothing from a teammate.`;
- it asserts the number of strings changed (8, then 14);
- it writes `json.dumps(data, indent=1) + "\n"`, which reproduces today's file byte for byte when nothing is changed (checked).

Then `SRC/blueprint/tests/test_charters.py`, `test_contract_blueprint_applier.py`, `test_playbooks.py` and `test_contract_plan_renderer.py` run without changes. The diff is reviewed like any golden.

## 14. Commit plan (conventional commits; one logical change each; `scripts/check.sh` green after each)

Each commit regenerates exactly the goldens and the signature record (4.4) its change causes, and raises the `count.txt` of every colocated test directory it adds tests to.

0. `docs(design): org growth phase 0a` (this file; by the coder step).
1. `feat(kernel): messages carry source and criterion`. The fields at their dataclass position, `SOURCES`, `verdict_tier`, `link_ids`; nothing sets them yet. Record: `MessageFields`, `Message.__init__`. No golden change.
2. `feat(delivery): msg.deliver records source and criterion`. Goldens: `events/line_shapes.txt`, `cli/obs_events_json.txt` (top-level and colocated).
3. `feat(dispatch): root's reworks are stamped relayed unless the user asked for them`. Sender S1/S2 for `source` and the relayed default for reworks; the assigner forwards `source`; `ServiceCommands.request(+source)` and its private Protocol; the facade's `send/delegate/request(+source)`; root MCP `delegate`/`request(source)`; CLI `task --revises` (human) and `request --source`. Record: `Org.send`, `Org.delegate`, `Org.request`. Goldens: `mcp/surface_root*.txt` (3), `cli/help_request.txt` (top-level and colocated), and `prompts/service_owner_reflect.txt` (its scenario's rework passes `source="human"`). Scenario helpers (rule in 12): `SRC/reflection/tests/_support.py:rework`, `TESTS/golden/test_golden_prompts.py:67` and `TESTS/testkit/dash_fixtures.py:170` pass `source="human"`.
4. `feat(services): stable criterion ids derived from the contract history`. `number_criteria`, `criteria_of`, `ServiceStore.versions`, `ServiceCatalog.criteria`, `_criteria.py`. No output change.
5. `feat(services): requests, listings and amendments show criterion ids`. The request body; `services` listing (`reflection/_reports.py`); 5.8 with the full criteria in the owner's note; `ContractAmendment` replaced. Goldens: `messages/service_request_task.md`, `charters/apply_service_example.md`, `prompts/service_owner_*.txt`, `cli/services.txt` (both), `services/services_text_root.txt`, reflection `services_*`, cli `define_service_amend_*`.
6. `feat(reflection): verdict tiers, client kind, links and the regression assertions`. Derived only; no output change.
7. `feat(reflection): the evidence gate behind services' ServiceEvidence port`. Port, stubs, contract suite, `CaseServiceEvidence`, wiring; not used yet.
8. `feat(services): feedback records source, criterion and confirmations`. Sender: `criterion`, S3, the relayed default for verdict and link notes. `feedback`; root MCP (parameters and docstring; the server instructions are unchanged, 6.4) and CLI (flags; replies with the message id); facade `send(+criterion)`, `feedback(...)`. Record: `Org.send`, `Org.feedback`. Goldens: `mcp/surface_root*.txt` (3), `cli/help_feedback.txt` (both), cli `feedback.txt` and `bad_verdict.txt`, `messages/feedback_note.md`, `rendered_inbox.txt`, `prompts/service_owner_reflect.txt` (its scenario's verdict passes `source="human"`). Scenario helpers (rule in 12) pass `source="human"`: `SRC/reflection/tests/_support.py:rate`, `TESTS/golden/test_golden_files.py:54,160`, `TESTS/golden/test_golden_prompts.py:64`, `TESTS/testkit/dash_fixtures.py:168,180`, `SRC/mcp_server/tests/test_service_tools.py:93`, `SRC/app/tests/test_services_facade.py:47`. The dashboard goldens stay byte-identical.
9. `feat(services)!: revise_playbook requires evidence and is gated`. All call sites; Reflect step 3 and the restore step; the no-playbook texts and hints; the client's note; frontmatter; event; facade. Record: `Org.revise_playbook`. Goldens: `mcp/surface_manager.txt`, `prompts/service_owner_*.txt`, `services/service_and_playbook_files.md`, `events/line_shapes.txt`, reflection `sections_*`. Revisions past v1 are made admissible (rule in 12): `TESTS/golden/test_golden_events.py:81` (amendment, `evidence=["C2"]`), `TESTS/golden/test_golden_files.py:162` (a second case), `SRC/mcp_server/tests/test_service_tools.py:61,94,143` (and `:147`'s hint, `:175`'s `evidence=[]`); first versions pass `evidence=[]` (`SRC/app/tests/test_services_facade.py:49`, `test_service_tools.py:49,128`).
10. `feat(reflection): the regression list, tier-aware Reflect texts and labelled verdicts`. `RegressionListSection`, the lead texts and steps 1-2, the `raise_bar` step for human clients, `MailRejectedServices` tiers, digest labels and R ids, the regression list in `services`. Goldens: `prompts/service_owner_reflect.txt`, `services/services_text_root.txt`, reflection `digest_*`, `sections_*`, `services_*`.
11. `feat(templates): ORG.md rule 10 asks for the client's evidence`. Goldens: 7 prompts, 2 ORG.md, bootstrap 3, upgrade 3, templates `org_rules_*` 5, cli `upgrade_rules_old*` 2.
12. `feat(roles): the manager copies the regression list and forwards ambiguous items`. 3 charter goldens; the 8 `charters` strings of `SRC/blueprint/tests/golden/second_half.json` (one-off script, 13).
13. `fix(blueprint): drop the default playbook's first-run leftover`. 9 plans, 1 charter; the 14 `plans`/`playbooks` strings of `SRC/blueprint/tests/golden/second_half.json` (one-off script, 13).
14. `feat(access): grants of can_hire and max_children are bounded by the grantor's`. `children_limit`, `check_grant`; policy only.
15. `feat(hierarchy): hire applies the authority bound; no can_hire means max_children 0`. Blueprint and CLI pass `approved`; `test_hire_approval.py`; the facade. Record: `Org.hire`. Goldens: all 10 MCP surfaces (`hire` docstring), `charters/hire.md`. The about 12 tests that hire with `can_hire=True` as a non-root actor pass `approved=True`.
16. `feat(orgfiles): a charter rewrite cannot grant hiring or raise a report's limit`.
17. `feat(health): low_quality is rebased on escapes, shown with re-checks and author rework runs`. Thresholds, the review action, the rewritten old-rule tests. Goldens: health colocated 6, `messages/notice_templates.txt`, templates `review_item_low_quality*` 2, `cli/health_json.txt` (both).
18. `docs(skill): provenance, the contract question, ambiguous items and consistency`. The ten replacements of 6.8 (125 lines kept); the three replaced needles of `SRC/skill/tests/test_skill_services.py`; the new `SRC/skill/tests/test_skill_org_growth.py` (and its `count.txt`). No size cap changes.
19. `docs: README and ARCHITECTURE for org growth phase 0a`. The README texts of 6.10, including the two event-table rows. The Services-section cap goes from `< 90` to `< 98` in `SRC/blueprint/tests/test_examples.py:201` and `SRC/blueprint/tests/test_round_g_assistant.py:105`, and the needle at `test_examples.py:192` changes (6.10).
20. `test(e2e): replay the E2 chain against the phase 0a mechanisms` (12.2). Every mechanism it exercises already has its unit and contract tests, written first, in its own commit above.

## 15. Deviations from 08, with reasons

1. **Rule (a) is omitted** (5.3). No client- or runtime-owned check *result* exists yet. Runtime facts such as artifact word counts are not mapped to criteria until Phase 3's oracle tiers, and team text must not become ground truth.
2. **Rule (c) is enforced as "first added by an amendment defined by root, still current"**, and pack seeds are omitted (no packs). 08's "accepted through the contract loop" has no stored trace. Every amendment is the client's call, and the skill makes it only after a yes. v1 criteria are excluded because they include assistant defaults (E2 criterion 6).
3. **The link can be stored as a separate link note** (`confirms`), not only "on the verdict". Notes are immutable and the yes comes a turn later. The derived `Verdict` carries the link, so every reader sees it on the verdict.
4. **The regression list is shown with the Playbook section** (and before Reflect when no request is open), not only in the Reflect section, because reviews are delegated in runs without Reflect. It is also listed in `services`, so the assistant can name `R<k>`.
5. **Escapes are attributed structurally**, to the owner and to the last report that reported `done` before the owner's `done`, because a verifier's PASS is free text in 0a.
6. **Relayed reworks are not judged deliveries in health.** This anticipates 08's `relayed-error` cause without building cause typing.
7. **The health threshold keys are renamed** (`max_escape_ratio`, `min_judged_for_quality`), because the meaning changed.
8. **Services whose client is an agent cannot revise their playbook** (G3). This applies 08 P2's weight 0 ahead of Phase 3's "unsupervised" label.
9. **Legacy verdicts read as `human`**, and **the MCP default is `relayed`** (CLI: `human`). 08 does not say; the reasons are in 3.1 and 4.2.
10. **`max_children: 0` for every hire without `can_hire`**, root's included. 08 M6 states it generally, and the limit is meaningless without the right.
11. **Cases stay "tasks sent by the owner's parent"**. 08 §6 notes that the broader case is Phase 0b.
12. **`Stats` and the per-version counts keep counting every final verdict** (3.2). 08 P2 sets weight 0 "in every gate", and these counts gate nothing; each relayed or agent verdict is labelled in the case lines. Tier-separated counts come with Phase 0b's quality view.
13. **M7's "verifier's FAIL count" is approximated by re-checks** (5.5): a rework of a checker's `done` task with a sibling author rework in between, the loop `roles/manager.md` lines 32-34 prescribe. A final FAIL that ends `blocked` gets no re-check and is not counted, because a FAIL is free text in 0a. `rework_runs` is the author runs those FAILs cost, and it stays 0 for authors.
14. **"The owner is shown the full contract on every amendment" (08 §4.1.3)** is met for the criteria, with ids, in the amendment note. Inputs, the deliverable and the budget are shown as change lines and in full in the file the note names.
15. **The refusal's client question** (08 §4.2) is sent by the owner to its client once, without waiting for a reply. For a human client the skill never makes it a separate question to the user. D3 bounds the friction to one yes/no item per human reject, plus one question before delivery, which carries the verifiers' `ambiguous` items and any doubt of the assistant about how to read a criterion (6.8 block G).
    - The item for the rejection already answers a G2 question. A proposal resting on no rejection of the user's is not asked.
    - A conflict between the criterion the item would add and an existing one is folded into that same item, as the clarification that settles both (6.8 block H). So 08 §4.1.3's consistency check costs no second question after a reject-driven amendment.
    - The separate consistency question (08 §4.1.3, "at `define_service`") is asked only before a definition or an amendment made outside a rejection (6.8 block D).
    - For a human client, the owner's `raise_bar` step no longer asks it to send lasting requirements to root (6.2), and the skill reads any such note with `inbox` without replying.
16. **"No lasting rule" assertions stay in the regression list**, marked "do not check it". 08 §4.1.2's explicit "no" closes them, and keeping the lines keeps the R ids stable and the history visible.

## 16. Decisions taken (all open choices resolved)

| # | Choice | Decision | Section |
|---|---|---|---|
| 1 | Where provenance is enforced | the dispatch sender (S1-S3, defaults) | 5.1 |
| 2 | Legacy verdicts | `human`; legacy reworks not relayed; unknown values relayed | 3.1 |
| 3 | Defaults | MCP `feedback.source` `relayed`; root rework `relayed`; CLI `human`; fresh requests unstamped | 3.1, 4 |
| 4 | Root-only parameters | registered on root's surface only; refused at the port for agents | 4.1, 5.1, 5.2 |
| 5 | Dataclass position | `source`, `criterion` after `feedback`, before `trace` | 3.1, 4.4 |
| 6 | Criterion ids | `C<k>` by first appearance in the contract's history; numbered in memory for an amendment | 3.3, 5.8 |
| 7 | Assertion ids | `R<k>` by order of the service's human-tier rejections | 3.4 |
| 8 | Late link | link note via `feedback(..., confirms=...)` with the user's answer as note, to the owner; `none` records "no lasting rule" | 5.2 |
| 9 | Link id after a clarification | the id the `define_service` reply gives the new criterion | 6.8 |
| 10 | Gate location | port in `services`, implementation in `reflection` | 5.3 |
| 11 | Rule (a) | omitted | 5.3 |
| 12 | Rule (c) | amended by root, current | 5.3 |
| 13 | First version | exempt (`evidence=[]`), with texts asking for the steps followed only; v1 -> v2 is not exempt | 5.3, 6.2 |
| 14 | Restore | exempt only for a version the client wrote | 5.3 |
| 15 | Agent clients | no revision admissible; texts say so | 5.3, 6.2 |
| 16 | Admission record | `evidence`, `admitted`, `restores` in `PLAYBOOK.md` | 3.5 |
| 17 | Refusal question | the owner sends it once and does not wait; the skill answers it with the rejection's one item or not at all, reads the note with `inbox` and never replies | 5.3, 6.8 |
| 18 | Reflect texts | lead by rejection tier; relayed rejections still trigger Reflect; step 3 per client kind | 6.2 |
| 19 | Regression list placement | with the Playbook section, else before Reflect; 12 lines; also in `services` | 5.4 |
| 20 | "No lasting rule" lines | kept, marked "do not check it" | 5.4, 6.2 |
| 21 | Counters | `Stats` unchanged | 3.2 |
| 22 | Escape | human-tier reject after `done`, relayed reworks excluded; owner + last sign-off | 5.5 |
| 23 | M7 counterweight | `rechecks` (checker re-checks after a FAIL) and `rework_runs` (author runs) | 5.5 |
| 24 | Authority exemption | `Hiring.hire(approved=True)` from the blueprint applier (MCP `apply_org`, CLI `apply`) and CLI `hire` only; pinned by an architecture test | 5.6 |
| 25 | `max_children` validation | A3 first for every hirer; at rewrite only for a changed value; no numeric strings | 5.6 |
| 26 | Rewrite bound | only changes are bounded; appends never are | 5.6 |
| 27 | Full contract on amendment | the criteria with ids in the owner's note | 6.3 |
| 28 | ORG.md | rule 10 only | 6.7 |
| 29 | `revise_playbook` CLI | none | 4.2 |
| 30 | Consistency question | conflicts of a reject-driven criterion are folded into the reject's one item; a separate question is asked only before a definition or an amendment outside a rejection, before the `define_service` call | 6.8 (blocks D, H), 15.15 |
| 31 | Size budgets | SKILL.md stays at 125 lines by condensing (no cap changes); the root instructions are unchanged (< 2700); the README Services-section cap goes from < 90 to the measured minimum < 98 | 6.4, 6.8, 6.10 |
| 32 | `raise_bar` for a human client | "Your parent asks the client ...; do not send it yourself", locked or not; unchanged for agent clients | 6.2 |
| 33 | CLI feedback replies | both show `(message {id}, source {source})`, so `--confirms` can be used from the terminal | 4.2 |
| 34 | Nested `Questions for the client:` | every manager copies its reports' items into its own report | 6.6 |
| 35 | Cited removed criterion | weighs nothing (no subject, a note saying so); `links` still accepts it | 5.3, 6.1 |
| 36 | Existing scenarios | helpers that stand for the user pass `source="human"`; revisions past v1 cite admissible evidence | 12 |

## 17. Risks and known limits

- **Declared provenance.** `source` is declared by the assistant; the runtime cannot verify that the user spoke (08 3.1). Mitigations: the MCP default is `relayed`, the skill's rule, and the owner sees the stamp.
- **Revision-level gate.** The gate judges citations, not text: a revision that cites an admissible criterion can still rewrite unrelated steps. This is the revision-level limit of M5; Phase 1 itemizes.
- **Ungated v1.** The first version is ungated, so for a service defined without a playbook, an owner can still put a rule drawn from its lessons or from a relayed rework into v1 (E2's wrong-rule path). Mitigations: the v1 texts ask for "the steps your team followed, nothing more" and say such a rule is not a step (6.2); most services get v1 from the blueprint or `define_service(playbook=...)`. The first revision after it is gated. Phase 1's item operations close it.
- **Sign-off heuristic.** It misattributes when checkers run in parallel, or when the owner reworks without a re-check; the escape is still counted for the owner.
- **Re-check proxy.** It undercounts a final FAIL that ends `blocked` (15.13).
- **No flag without services.** `low_quality` no longer fires in orgs without services until Phase 0b gives one-off tasks verdicts. That is intended (README Health); `stuck`, `expensive` and `wasteful` still do.
- **Unasked team proposals.** A team proposal refused for lack of client evidence is not put to the user (D3). It returns only if the user later rejects a delivery for the same reason. Phase 2's retro brief is the channel for such proposals.
- **Prompt size.** Owner prompts grow by up to 15 lines per service with an open request and a non-empty list (heading, instruction line, the "older" line and 12 assertion lines).
- **Outside callers.** `Org.revise_playbook` callers outside the repository break (stated in README).
- **Agent-client playbooks.** A manager's own services keep their first playbook (G3). If that proves too strict in studies, Phase 3's oracle declaration is the place to open it; no setting is added now.
- **Untiered counts.** The per-version counts still mix tiers (15.12), so an owner reading only that line may over-weight a relayed verdict. The case lines label it.
- **No skill headroom.** SKILL.md is at its 125-line cap after 0a. A later phase must condense it again, or raise the cap deliberately with the reason. Some of its wording now leans on tool docstrings (`feedback`'s `confirms`, `define_service`'s amendment), so those docstrings must keep saying it.
- **README section cap.** The Services-section cap of the README tests is raised from < 90 to < 98 (6.10). It still guards against growth beyond what 0a documents.

## 18. Review resolutions

### 18.1 First review (resolved in revision 2)

The first review was written to `/Volumes/workspace/hirearchy/.worktrees/org-growth-0a/.agents/tasks/design-review.md`, where the second review has since replaced it. Every HIGH and MEDIUM finding was addressed, and every LOW one as well. The second review confirmed all 22 as resolved.

| # | Severity | Finding (short) | Resolution |
|---|---|---|---|
| 1 | HIGH | The owner's G1/G2 question has no handling in the skill, so there can be two contract questions per reject; team-only questions add friction D3 does not allow | **Addressed.** SKILL.md step 5 item 6 (6.8) gains the handling. An owner note asking whether a rejection is lasting, or quoting a refusal's question, is never a new question for the user. If it is about a rejection of the user's, the rejection's one yes/no item answers it, and the owner learns the answer from the amendment and the link note, with no reply (which would cost a run). If it rests on no rejection of the user's, the user is not asked and the owner gets no reply. G1/G2 now say to send the question once and not to wait (6.1). The human-reject lead text no longer tells the owner to ask (finding 2). Decisions 16.17; deviation 15.15; risk in 17. The reviewer's alternative (mention team proposals with the next delivery's question) was not taken, because it would add a question D3 does not allow. |
| 2 | MEDIUM | Unchanged Reflect texts contradict the gate, P3, relayed weight 0 and G3 | **Addressed.** 6.2 gives exact new texts for the lead (by rejection tier, locked and unlocked), step 1 (no regression list for agent clients), step 2 (the client's own feedback, applied to this request; the playbook only as step 3 says) and step 3 (a separate text for agent clients). `MailRejectedServices` keeps triggering on relayed rejections and now returns the tier; the port signatures are in 4.3. Golden impact is in 13 (reflection `sections_*`, `prompts/service_owner_reflect.txt`). |
| 3 | MEDIUM | The amendment path cannot get C ids for new texts | **Addressed.** New 5.8: in-memory numbering of the new version before the write, the new `ContractAmendment` signatures (`listed`, `amended_criteria(current: Sequence[Criterion])`, `changes(..., ids)`, `diff(..., criteria)`), and `numbered` removed. `stored_versions` and `criteria_of` are in 3.3; tests in 12.1. |
| 4 | MEDIUM | `org_signatures.json` and the `Message` field order are not addressed | **Addressed.** The dataclass position is in 3.1, and the new 4.4 lists every recorded change per method with the commit that regenerates it. The commit plan (14) assigns each regeneration. |
| 5 | MEDIUM | "No lasting rule" lines are enforced as rules | **Addressed.** The lines are kept. The header excludes them from checking, and the line suffix says "do not check it" (6.2). The manager bullet repeats the exception (6.6). Deviation 15.16. |
| 6 | MEDIUM | `max_children` validation conflicts; A2/A3 unreachable at hire; A3 blocks body-only edits | **Addressed.** One rule in 5.6: `children_limit` (A3) runs first for every hirer, then the normalization, then `check_grant` for non-root, non-approved hirers. At rewrite, A3 runs only on a changed value. Numeric strings are refused. The fact that A2 is unreachable at hire is stated, with the reason. §10 is corrected to match. |
| 7 | MEDIUM | First-version texts invite lesson-based rules into an ungated v1 | **Addressed.** The hint, Playbook and docstring texts now ask for "the steps your team followed, nothing more" and say a rule from lessons or a relayed rework is not a step (6.2, 6.4). The residual risk is in 17. |
| 8 | MEDIUM | The link id after a clarification is ambiguous | **Addressed.** 6.8 says to use the id the `define_service` reply gives the new or clarified criterion (e.g. `"C7"`), an existing criterion's id when the user wants no change, or `"none"`. Decision 16.9. |
| 9 | LOW | The M7 counterweight is a re-check count, and `rework_runs` is mislabelled for authors | **Addressed.** Deviation 15.13. `rechecks` is now defined for checkers by the sibling author rework in the window (0 for authors), `rework_runs` counts author runs, and the labels say so (5.5). |
| 10 | LOW | Golden counts are wrong; files are missing | **Addressed.** 13 is recounted: 134 top-level files with about 44 changing, 9 + 18 of the 27 plan files, 7 of 8 prompts. The colocated cli list now includes `help_request.txt` and `services.txt`, and the to-verify list includes `define_service_error.txt`. |
| 11 | LOW | Commit plan gaps (request `source`, commit 3's scenario) | **Addressed.** Commit 3 now includes `ServiceCommands.request(+source)`, root MCP `request(source)` and CLI `request --source`. The reflect prompt's verdict stamp is regenerated in commit 8 (14). |
| 12 | LOW | Incomplete list of fakes and private Protocols | **Addressed.** 7 states the rule (every explicit implementation is updated in the same commit) and lists the known ones. The private Protocol changes, `OwnerPromptSections`' new collaborator, `case_line` and the `RecordingSender` docstring are named (4.3, 5.1, 5.4, 6.2). |
| 13 | LOW | `Stats` still counts relayed and agent verdicts | **Addressed by decision.** The counts are unchanged and the case lines label the tiers (3.2). Deviation 15.12, risk in 17. |
| 14 | LOW | CLI `apply` is not mentioned; the `approved=True` invariant is unchecked | **Addressed.** CLI `apply` is named in 4.2 and 5.6. The new architecture test `TESTS/architecture/test_hire_approval.py` is in 11 and 12.1. |
| 15 | LOW | `low_quality` no longer fires without services | **Addressed.** Stated in 5.5, in the README Health row (6.10) and in 17. |
| 16 | LOW | The E2 health example holds only for a 0a replay | **Addressed.** 5.5 now says "replayed under 0a (A2 stamped relayed)" and gives the legacy result (judged 5, escapes 2: 0.4, no flag). |
| 17 | LOW | "criterion only on a feedback or link note" is not enforced | **Addressed.** New sender rule S3 (5.1, 6.1, tests in 12.1). The Python `Org.send` route is stated. |
| 18 | LOW | The `confirms` note is ambiguous | **Addressed.** The note is required (the user's answer, verbatim), `or "confirmed"` is dropped, and the link note goes to `task.to` (5.2, 6.4, 6.5, 10). |
| 19 | LOW | e2e structure: order-dependent module world; the health accessor | **Addressed.** Each test builds its own world and replays the chain up to its block (`chain(w, through=k-1)`), so each block runs alone. Health is read through `testkit.e2e_world.agent_health(org, addr)` (12.2). |
| 20 | LOW | The rule (a) rationale is overstated | **Addressed.** Reworded in 5.3 and 15.1: no runtime- or client-owned check *result* exists, and runtime facts such as word counts are not yet mapped to criteria. |
| 21 | LOW | 08 §4.1.3 "full contract on every amendment" is not addressed | **Addressed.** The amendment note lists every current criterion with its id (6.3, 5.8); the scope is stated in deviation 15.14. |
| 22 | LOW | Small ambiguities | **Addressed.** "The quoted words of each line clipped to 300 characters" (5.4). G2's assertion is the one with the highest note id among those of the cited cases or of single-case subjects (5.3). Relayed `none` renders `, possibly a one-off (not confirmed by the client)` (6.2). `ServiceStore.versions` kinds, errors and the body element (4.3). The `hire` docstring is worded for root and agents (6.4). Charter append mode reads the old frontmatter and is never bounded (5.6). The "unknown keys are ignored" wording is corrected (3.7). |

### 18.2 Second review (resolved in revision 3)

Review: `/Volumes/workspace/hirearchy/.worktrees/org-growth-0a/.agents/tasks/design-review.md` (0 HIGH, 2 MEDIUM, 7 LOW; LOW 9 has four parts). Every finding is addressed as the review prescribed, applying the manager's decisions:
- keep the root instructions byte-unchanged;
- keep SKILL.md at or under 125 lines by condensing, raising the cap only if it truly cannot fit;
- adopt the reviewer's D3 rule;
- make no change to 08's approved behaviour.

| # | Severity | Finding (short) | Resolution |
|---|---|---|---|
| 1 | MEDIUM | The SKILL.md additions break the 125-line cap of nine tests, and the root-instructions line breaks the < 2700 budget | **Addressed without raising either cap.** The root instructions are unchanged (6.4); the `source` rule is in the root `feedback` docstring, and the root surfaces change only through docstrings (13). SKILL.md is rewritten by ten exact replacements that keep it at exactly 125 lines (6.8). They condense existing wording (no rule dropped) and lean on the `feedback` and `define_service` docstrings for mechanics. The result was checked against a replica of every assertion of the nine tests plus `test_install.py` and the old-marker test. Three needles of `test_skill_services.py` are replaced, each listed with its replacement (6.8, commit 18), and the new needles go into `test_skill_org_growth.py`. |
| 2 | MEDIUM | The per-amendment consistency question can be a second contract question for one human reject (D3) | **Addressed with the reviewer's rule.** Block H checks the proposed criterion against the others *before* the item is proposed, and makes the item the clarification that settles both, so the user still answers one yes/no. Block D asks a separate consistency question only before a definition or an amendment outside a rejection. It is asked before the `define_service` call rather than after its reply, which is the same rule moved earlier, so no amendment needs undoing. Recorded in 15.15 and decision 30. |
| 3 | LOW | The golden estimate misses `second_half.json` and the dashboard's `wide-3-services-detail.txt`; README's `msg.deliver` row is not in 6.10 | **Addressed.** `blueprint/tests/golden/second_half.json` is in 13 (22 strings: 8 in commit 12, 14 in commit 13). It has no update flag, so 13 gives its one-off regeneration script and the verification that `json.dumps(indent=1)` reproduces it. The dashboard goldens stay byte-identical by LOW 4's rule (`dash_fixtures.py:168,170,180` pass `source="human"`); `wide-3-services-detail.txt` is to verify. The README event table gets the full `msg.deliver` key list, adding the already-missing `supersedes` and `feedback`, and `service.revise`'s `admitted` (6.10). |
| 4 | LOW | The relayed defaults move existing helpers onto the relayed path, and app-level revisions past v1 hit the real gate | **Addressed.** The rule is in 12, with every known file. Reworks pass `source="human"` in commit 3 and verdicts in commit 8. Revisions past v1 become admissible in commit 9: `test_golden_events.py:81` via an amendment and `evidence=["C2"]`, `test_golden_files.py:162` and `test_service_tools.py:94` via a second human case, `test_service_tools.py:61,143` via amendments. `:175` passes `evidence=[]` so the lock refusal still shows. First versions pass `evidence=[]`. 12 also states where the real gate is tested, since `services.testing` and `ReflectionWorld` default to `AdmittingServiceEvidence`. |
| 5 | LOW | `raise_bar` still sends owners' notes to root; the skill does not say how to clear them from "Needs you" | **Addressed.** `raise_bar` for a human client reads "Your parent asks the client whether a rejection is a lasting requirement; do not send it yourself." (6.2). This covers locked contracts too, since the client can still amend a locked contract and the locked sections change in that commit anyway. Agent clients keep today's text. Block H says "read it with `inbox`, go on, and never reply to it or mention it". `inbox` marks root's unread messages read (`_tools_identity.py`), so the note leaves "Needs you". |
| 6 | LOW | The CLI `feedback` reply has no message id for `--confirms` | **Addressed.** Both replies show `(message {id}, source {source})` (4.2); `feedback.txt` changes (13); tested in 12.1. |
| 7 | LOW | `Questions for the client:` stop at the first manager of a nested team | **Addressed.** The manager bullet ends "Copy every `Questions for the client:` item from your reports' results into your own report the same way; never answer one yourself." (6.6). The template stays within its 50-line cap (41 lines). |
| 8 | LOW | G1's criterion note is false for a removed criterion | **Addressed.** A cited criterion that is no longer in the contract gets the note ``{C} is no longer in the contract: cite a current criterion (see `services`)`` and weighs nothing, amended or not. It adds no subject, and an assertion's `about` keeps only current criteria (5.3, 6.1). Unit tests are in 12.1. Decision 35 records why: a rule built on a criterion the client took out contradicts the client. |
| 9a | LOW | F5/F6 cannot come from `AdmittingServiceEvidence` | **Addressed.** 12.1 reads "F1-F4 and F7-F9 with `AdmittingServiceEvidence`; F5 and F6 in `reflection` against `CaseServiceEvidence.links` and end to end". |
| 9b | LOW | `Org.deliver` bypasses the sender | **Addressed.** 5.1 names it as raw delivery for tests and fixtures, reached by no MCP tool or CLI command; a root verdict built through it without `source` reads as legacy `human`. |
| 9c | LOW | The kind of `Org.delegate`'s `source` is unstated | **Addressed.** It is positional-or-keyword after `revises`, in `TaskAssigner.delegate` and `Org.delegate` (4.3, 4.4). |
| 9d | LOW | Item 2's and item 3's pre-delivery questions should be one message | **Addressed.** Block G: "ask them in plain words, with any question from item 2, in ONE message BEFORE you deliver" (6.8; 15.15 counts it as D3's one pre-delivery question). |

### 18.3 Found while resolving the second review

Each of these follows from the same budgets and assertions, so it is fixed here rather than left for a third review:
- **README Services section cap.** `test_examples.py:201` and `test_round_g_assistant.py:105` pin the Services section at < 90 lines; it is 88 today, so the 0a paragraph cannot fit. In-place edits cost no line. The paragraph is condensed to 8 lines, and both caps go to the measured minimum, < 98. Cutting the study notes those tests pin would be the only alternative. The needle `` `revise_playbook(service, content, reason)` `` of `test_examples.py:192` becomes the four-argument form (6.10, commit 19, decision 31, 17).
- **`cli/tests/expected/bad_verdict.txt`** holds the `usage: hirearchy feedback` line, which gains the new flags. It is added to 13 and commit 8.
- **The root `feedback` docstring** keeps today's sentences, so `test_service_tools.py:21`'s lower-case "every verdict stays" holds (6.4). The `ServiceCommands.feedback` docstring keeps "stays in the case" (`:18`, 12.1).
- **The manager template's 50-line cap** (`test_round_f_guidance.py`) is checked: 39 lines become 41 (6.6).

None of these resolutions changes the approved product behaviour of 08 beyond what Phase 0a specifies. The interpretations 08 leaves open are recorded as deviations 15.12-15.16 and decisions 30-36.

