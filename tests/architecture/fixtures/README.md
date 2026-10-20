# Seeded violations

`bad_pkg/` is a tiny package that breaks the architecture rules ON PURPOSE. It is never imported by the product and never
collected as tests; `test_architecture.py` runs every checker on it and requires each one to flag its violation (a checker that
cannot fail would prove nothing). `bad_architecture.md` is a package-map table with a responsibility sentence that contains "and".

| Violation | Where | Flagged by |
|---|---|---|
| import of another package's private module | `rogue/_imports_private.py` imports `mail._mailbox` | import-linter contract `private-modules-mail` (`gen_importlinter`) |
| class with behaviour and no Protocol | `rogue/_no_protocol.py::Plain` | `class_interfaces.survey` (the R6 engine of `tests/golden/test_class_interfaces.py`) |
| module-level singleton / mutable state | `rogue/_singleton.py` | `checks.module_singletons` |
| second writer of `ORG.md`, wrong ledger owner | `rogue/_second_writer.py` | `checks.single_writer`, `checks.ledger_names` |
| Protocol with 9 methods | `wide/api.py::Wide` | `checks.protocol_widths` |
| Protocol without contract suite / implementations | `mail/api.py::Mailbox` | `checks.contract_suites` |
| `__init__` exports a name that is not in `api` | `rogue/__init__.py` | `checks.init_reexports` |
| public module and a package outside the map | `rogue/public_module.py`, `wide/` | `checks.package_contents` |
| import that the dependency graph does not allow | `rogue/_imports_private.py` | `checks.imports_against_graph` |
| responsibility with "and" | `bad_architecture.md` | `checks.responsibilities` |
