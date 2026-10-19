"""Modules that the import contracts keep out of a feature's tests, reachable as ``testkit.legacy.<module>`` (the module itself, not a copy).

A test moved from ``tests/`` into ``src/orgmcp/<package>/tests/`` (``tools/relocate_tests.py``) still builds its world with the facade
(``orgmcp.core``), the MCP server (``orgmcp.server``), the scheduler and the like, which a package below them may not import
(ARCHITECTURE.md 8.2). The tool writes ``from testkit.legacy.orgmcp.core import ROOT, Org`` instead of ``from orgmcp.core import ROOT, Org``;
``testkit.legacy.<dotted name>`` is an alias of the module ``<dotted name>`` (``yaml``, ``orgmcp.server``, ``orgmcp.app.wiring`` ...): the very
same module object, so ``monkeypatch.setattr(core, ...)`` and ``isinstance`` behave as before. The imports are invisible to import-linter
(``testkit`` is not part of ``orgmcp``), and mypy treats them as ``Any`` (``ignore_missing_imports`` for ``testkit.legacy.*``).

A converted test imports the real API of the package it tests, and this alias goes away with the last test that needs it (step E3).
"""

import importlib
import importlib.abc
import importlib.machinery
import sys
from types import ModuleType

PREFIX = __name__ + "."


class _AliasFinder(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    """Resolves ``testkit.legacy.<name>`` to the module ``<name>`` and keeps that module's own ``__spec__``."""

    def __init__(self) -> None:
        self._specs: dict[str, importlib.machinery.ModuleSpec | None] = {}

    def find_spec(self, fullname: str, path: object = None, target: object = None) -> importlib.machinery.ModuleSpec | None:
        if not fullname.startswith(PREFIX):
            return None
        return importlib.machinery.ModuleSpec(fullname, self, is_package=hasattr(self._real(fullname), "__path__"))

    def _real(self, fullname: str) -> ModuleType:
        return importlib.import_module(fullname[len(PREFIX):])

    def create_module(self, spec: importlib.machinery.ModuleSpec) -> ModuleType:
        module = self._real(spec.name)
        self._specs[spec.name] = module.__spec__
        return module

    def exec_module(self, module: ModuleType) -> None:
        # the import machinery has just replaced module.__spec__ by the alias spec; the module is still the real one: give its spec back
        assert module.__spec__ is not None
        module.__spec__ = self._specs.pop(module.__spec__.name)  # type: ignore[assignment]


if not any(isinstance(finder, _AliasFinder) for finder in sys.meta_path):
    sys.meta_path.insert(0, _AliasFinder())
