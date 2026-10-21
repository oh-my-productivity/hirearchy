"""Modules that the import contracts keep out of a package's tests, reachable as ``testkit.reach.<module>`` (the module itself, not a copy).

A test colocated in ``src/hirearchy/<package>/tests/`` still needs to build its world with the facade (``hirearchy.core``), the composition root
(``hirearchy.app.wiring``) or PyYAML, which a package below them may not import (ARCHITECTURE.md 8.2). It writes
``from testkit.reach.hirearchy.core import ROOT, Org`` instead of ``from hirearchy.core import ROOT, Org``; ``testkit.reach.<dotted name>`` is an
alias of the module ``<dotted name>`` (``yaml``, ``hirearchy.core``, ``hirearchy.app.wiring`` ...): the very same module object, so ``isinstance``
and identity checks behave as before. The imports are invisible to import-linter (``testkit`` is not part of ``hirearchy``), and mypy treats
them as ``Any`` (``ignore_missing_imports`` for ``testkit.reach.*`` in pyproject.toml).

Prefer the real API of the package under test; reach for this only where the test needs what its layer may not import. Seams of the
runtime are replaced with ``hirearchy.app.wiring.overriding`` or the fixtures of ``testkit``, not by patching modules.
"""

import importlib
import importlib.abc
import importlib.machinery
import sys
from types import ModuleType

PREFIX = __name__ + "."


class _AliasFinder(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    """Resolves ``testkit.reach.<name>`` to the module ``<name>`` and keeps that module's own ``__spec__``."""

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
