# hirearchy refactor — binding principles (decided by the project manager with the user)

User's goal (verbatim): "refactor the whole system respecting TDD and SOLID principles. All classes should implement
and depend on interfaces." and "choose the one that fits extreme organization, well separated responsibilities and
extremely high cohesion and extremely low coupling."

## Structure
1. Package by feature (vertical slices) under `src/hirearchy/<feature>/`. Each feature package has:
   - `api.py`: the ONLY public surface — the `typing.Protocol` interfaces the feature provides, its data types
     (frozen dataclasses where possible) and its exceptions. `__init__.py` re-exports exactly `api`.
   - private implementation modules named `_*.py` (never imported from outside the package, except by the
     composition root).
   - `tests/`: the feature's tests, colocated (high cohesion). The global `tests/` dir shrinks to cross-feature
     end-to-end tests and shared fixtures, and is emptied as features move.
2. `src/hirearchy/kernel/`: the smallest shared vocabulary every feature may use — primitive ports (`Clock`,
   `IdGenerator`, ...), core data types (e.g. `Address`, `Message`), the base error. The kernel imports nothing else
   from hirearchy.
3. Entry points (`cli`, `mcp` server, `scheduler` loop, `dashboard`) are packages too; they depend only on feature
   `api` modules.
4. `src/hirearchy/app/wiring.py` (composition root) is the ONLY module that imports `_` implementation modules and
   constructs concrete classes.
5. `Org` (today's `core.Org`) survives only as a thin backward-compatible facade built by the composition root,
   delegating every method to the feature services. No feature may import it. It exists so the user's running
   orgs, the tests and external callers keep working unchanged.

## SOLID, made checkable
- S: one reason to change per class; a class that needs "and" in its one-sentence responsibility is split.
- O: new behaviour = new implementation of an interface, not edits to callers.
- L: every implementation of an interface passes the SAME contract test suite.
- I: small role interfaces (e.g. a read-only query interface separate from a mutating one); consumers type their
  dependencies with the narrowest interface they use.
- D: every class with behaviour explicitly subclasses at least one Protocol it implements
  (`class FsMessageStore(MessageStore): ...`) and receives every collaborator through its constructor typed by a
  Protocol. No class constructs its collaborators; no module-level singletons except in the composition root.
- Exempt from "implements an interface" (they are data, not behaviour): dataclasses / NamedTuples / enums that only
  hold data, exceptions, and framework subclasses that must inherit a framework type (Textual widgets/screens) —
  but those still depend only on interfaces.

## Enforcement (dev tooling, exact pins)
- `import-linter==2.15`: contracts for (a) layers: entry points → features → kernel; (b) no import of another
  package's `_` modules (only `app.wiring` may); (c) no cycles between features; (d) kernel independent; (e) no
  feature imports the `Org` facade.
- `mypy==2.4.0`: strict on every refactored package (Protocol conformance, no `Any` leaks in APIs).
- A test that walks every class in `src/hirearchy` and asserts each non-exempt class subclasses a Protocol.
- All three run in the default `pytest` run (or a single `uv run` command documented in the README) and must pass.

## TDD
- RED → GREEN → REFACTOR for every new interface and class: write its tests first, watch them fail for the right
  reason, then move/implement the code.
- Interfaces get contract test suites that run against every implementation (filesystem adapter AND an in-memory
  fake), so Liskov is tested, and fakes are trustworthy for unit tests of consumers.
- The existing behaviour tests and golden files are the characterization safety net: green after every step, never
  weakened (move them; adapt imports; do not relax assertions).
- One extraction = one commit (or a few), each leaving the full suite green.

## Behaviour freeze
Pure refactor: no feature, prompt, file-format, MCP tool, CLI or event-schema change. Byte-identical prompts,
ORG.md, message files, kiro profiles, plan blocks, CLI output and tool signatures/docstrings (golden tests prove
it). Anything that should change is listed in the report, not fixed.
