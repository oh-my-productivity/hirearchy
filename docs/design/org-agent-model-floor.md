# Org-agent model floor and effort (D-E4-9)

Owner decision (2026-10-23, `docs/research/org-growth/phase-0a1/e4-decision.md`, D-E4-9): "claude-sonnet-5.5 is the minimum we can have. it should be
on 'high' effort." Every org agent runs claude-sonnet-5.5 or better at `high` effort or above. Base `3815813`.

## 1. Decisions

1. **One source of truth: `settings`.** A new private module `src/hirearchy/settings/_floor.py`, re-exported by `settings/api.py`, holds the
   floor and every refusal wording. Every refusal point calls it; nobody else knows the allowed ids or the levels.
   - `DEFAULT_ALLOWED_MODELS = ("claude-sonnet-5.5", "claude-opus-5.5")`, `EFFORT_LEVELS = ("high", "xhigh", "max")`.
   - `DEFAULT_EFFORT = "high"` sits in `_config.py` beside `DEFAULT_MODEL`, because `DEFAULT_CONFIG` uses it.
   - Readers: `config_effort(config) -> str`, `config_allowed_models(config) -> tuple[str, ...]`.
   - Checks, each returning `str | None`: `model_floor_problem(config, model)`, `effort_floor_problem(effort)` and
     `config_floor_problem(config, before=None)`.
2. **Effort lives in ORG.md, org-wide.** The key is `effort`, added to `DEFAULT_CONFIG` right after `default_model` with the value `high`, so a
   new ORG.md shows `effort: high`. A null, missing or blank value means `high`. The value is only stripped: `High` is refused, not lowered.
3. **No per-agent effort override.** Reading a charter `effort` would take one line, but setting it would not: `hire` (an MCP signature and the
   surface goldens), the blueprint keys, the charter-rewrite rules and their refusals would all change. The brief admits an override only if it is
   trivial, and it is not.
4. **Widening is additive and human-only.** The ORG.md key `extra_allowed_models` (a list of ids, or one id) adds to the default pair; it can
   never remove it. So `DEFAULT_MODEL` is always allowed, and a test pins `DEFAULT_MODEL in DEFAULT_ALLOWED_MODELS`.
   - The key is not in `DEFAULT_CONFIG`, so a new ORG.md does not advertise it. `health` is the precedent for an optional key.
   - The human edits ORG.md by hand. Root's MCP `write` of ORG.md (the assistant) may not widen it (refusal point 6).
5. **The effective model is checked, not only a given id.** The effective model is the given or charter `model`, else ORG.md's `default_model`,
   else `DEFAULT_MODEL`. This is how "the configured default model" is refused: a hire without a model, or a planned agent without an id, would
   run on that default.

## 2. Wording (exact)

| Id | Text |
|---|---|
| M1 model | `model "<id>" is not allowed for org agents; allowed: claude-sonnet-5.5, claude-opus-5.5 (only the user can widen this set)` (the list is `config_allowed_models`) |
| M2 effort | `effort "<value>" is not allowed for org agents; allowed: high, xhigh, max` |
| M3 default | `default_model: ` + M1 |
| M4 widen | `only the user can widen the allowed models, by editing ORG.md themselves (not allowed now: <ids>)` |
| N note | `Model floor: below the allowed models (claude-sonnet-5.5, claude-opus-5.5): ceo/eng on claude-haiku-4.5, ops on claude-sonnet-4.6. Fix: set model: claude-sonnet-5.5 in each one's AGENT.md (you for your direct reports, the manager for the others); they keep running as they are until then.` |
| P plan | `- Models: claude-sonnet-5.5 (high effort) for every agent`. Mixed: `- Models: claude-opus-5.5 for 1 agent, claude-sonnet-5.5 for 3 agents, all at high effort (<policy>)`. No agents: `- Models: claude-sonnet-5.5 (high effort, no agents yet)` |

## 3. Refusal points

Each point calls `settings`. The wrapper text is in brackets.

1. **Blueprint validation** (`propose_org`, `apply_org`, CLI `plan`/`apply`), in `RuleBlueprintValidator.validate`. The check runs right after
   the `manager-cheap-model` block. Every finding is an error, so `apply` refuses.
   - Code `model-floor`, message M1, at each source of a model: `needs.models.cheap`, `needs.models.strong`, `agents[<addr>]` (an explicit id
     that is not a tier name), and `ORG.md default_model`. The last applies only when some planned agent resolves to the default and no other
     source already names that id.
   - Code `effort-floor`, message M2, at `ORG.md effort`, when the org's effort is below the floor.
2. **`hire`** (MCP, CLI, `Org.hire`, the blueprint applier), in `RuleHiring.hire`, right after the name check:
   - with a model, M1 for the given `model`;
   - without one, M3 for the configured default.
3. **Charter rewrites** (root and managers, `GuardedOrgFileWriter.write_noted`, `AGENT.md`), checked just before `rewrite_charter`. The rewrite is
   refused (`charter of <addr>: ` + M1) when it changes the effective model, whether it sets, changes or unsets it, to one outside the set.
   - A rewrite that leaves the model as it was is admitted, even below the floor (an existing agent).
   - An append never changes the frontmatter.
4. **Org creation** (`Org.init`, CLI `init --model`, MCP `create_org(default_model=)`), in `FsOrgInitializer.init` and `MemoryOrgInitializer.init`,
   before anything is written. They refuse with `cannot create the organization: ` + `config_floor_problem(config)` (M2 or M3).
   - A config that widens the set in the same mapping is admitted. This is the human's Python API, since `create_org` has no such parameter.
5. **Run command** (scheduler, `hirearchy run`), in `KiroRunCommandBuilder.build`, before the profile and the scratch directory are made. An
   ORG.md effort outside the levels raises `KiroRunRefused("kiro: " + M2)`.
   - The run log then says `# failed to start: kiro: effort "low" ...`.
   - A model below the floor is **not** refused here and never substituted.
6. **Root's MCP `write` of ORG.md**, in `GuardedOrgFileWriter.write_noted`, which refuses with `ORG.md: ` + `config_floor_problem(new, before=current)`:
   - M4 when the new text would widen the set;
   - M2 or M3 when the new text changes `effort` or `default_model` to a value outside the floor.

   Values the file already had are tolerated, so root can still edit the rules of an organization made before the floor.

   Items 3 and 6 read the current settings tolerantly: when the current ORG.md has YAML that does not parse (a hand edit slipped), the settings read
   as `{}`, so the built-in set, effort and default model apply. Root can then still repair ORG.md and rewrite charters, as before the floor, and
   the repair is held to the built-in floor (it cannot widen the set or lower the effort or the default model).

## 4. Effort on the command line

The builder reads `ModelResolver.effort()`, a new third method of `access.ModelResolver` that returns `config_effort` of the settings. The builder
already holds the resolver, so neither its constructor nor its wiring changes. The command becomes:

```
<python> -I -S <launch> --start-deadline 60 -- kiro-cli chat --no-interactive --agent <profile> --model <model> --effort <effort> --v3 --require-mcp-startup --output-format stream-json
```

- The scheduler writes the argv verbatim into the run log's `# cmd:` line (`runs.log_invocation`).
- `_launch.py` passes the argv through unchanged, so no launcher change is needed.
- kiro-cli 2.33.0 lists `--effort` in `chat --help`, and the manager verified it with `--v3` (exit 0).
- `--effort` is not added to the readiness `REQUIRED_FLAGS`. That would touch the stub kiro-cli and the readiness fakes that 0a.2's throttle work
  shares, and an older kiro-cli fails visibly: the launcher copies its error into the run log.

## 5. Existing agents

- **Visible.** A new `access.ModelFloorAudit` (`CharterModelFloorAudit`, built from the agent directory, the model resolver and the settings) lists
  every agent whose effective model is outside the allowed set: `below_floor()` returns `(addr, model)` pairs and `note()` returns line N.
  - Root's MCP `status` and `whoami` append N after the scheduler line and before the stale-skill note. The helper is `with_floor_note` in
    `mcp_server/_tools_identity.py`.
  - Agents and the CLI do not show it.
- **Not refused.** Their runs go on with their model and `--effort`, and nothing is substituted. A body-only charter rewrite still works.
- **Not extended.** New hires, plans and model changes are refused (section 3).
- **Hand-edited `effort: low`.** Every run is refused with M2 in its run log (section 3, point 5). The blueprint plan also shows the
  `effort-floor` error.

## 6. Texts

- **SKILL.md** keeps 125 lines and changes 5 lines. 0a.2 changes lines 83-85, 92, 95 and 104-109.
  - Lines 37, 39 and 40 (step 1 item 6) are replaced. Line 38 is kept, because tests pin it.
  - Lines 117-118: "tiered models when asked" becomes "the model floor (nothing below claude-sonnet-5.5)".
- **ROOT_INSTRUCTIONS** (`_instructions.py` file lines 29-30) keeps the same 2 lines, about 60 characters shorter:
  `models (all claude-sonnet-5.5 at high effort; nothing below is available)`.
- **Blueprint comments.** The `_example_texts.py` and `examples/*.yaml` comments, and the examples' `model_policy` value, drop "cheaper".
- **README.** The Models section and the Test section (`HIREARCHY_IT_MODEL`, the count of integration tests) are updated.

## 7. Merging with 0a.2 (`feat/org-growth-phase-0a2`)

These are the places where both branches change the same lines. Whichever lands second resolves them as follows.

- **`mcp_server/_instructions.py`**, which 0a.2 rewraps (file lines 27-30). Resolved text:
  ```
     given, never invent. Default deliverable place: a new `deliverables/` folder here (say so). Also ask: format,
     length, exact checkable criteria, sources/web, workspace and tests (code), budget in runs, models (all claude-sonnet-5.5
     at high effort; nothing below is available), review, approval.
  ```
- **`IdentityTools`/`StatusTools` constructors**, the root branch of `whoami()`/`status()`, `wire_mcp_server.py` (lines 184 and 189) and the
  tool-group tests: keep both new parameters, 0a.2's `deliverables` first. Root's text is `tree/summary`, then the scheduler line, then the
  deliverables note, then the floor note, then the stale-skill note.
- **`surface_root*.txt`**: regenerate after the rebase.
- **Count files**: neither branch raises a `count.txt`. They are floors (`>=`), so they need no change.

## 8. Out of scope

- An effort in the `run.start` event, which would be an event-schema change.
- `--effort` in the readiness check (section 4).
- CLI `status`/`whoami` notes.
- Dashboard marks.
- The E5 harness's own `--effort high` for the assistant seat. The harness sets it.
