"""The pre-split of ``core.Org`` (ARCHITECTURE.md 6.4): 20 mixins, one per package ``Org`` delegates to, holding exactly the methods
section 5.3 maps to that package; ``Org`` is their composition and ``core.py`` is a shim without a class body."""

from __future__ import annotations

import ast
import importlib
from pathlib import Path

import pytest

from hirearchy.app.tests import _signatures
from hirearchy.app.tests._mixins import MIXINS

APP = Path(__file__).resolve().parents[1]
CORE = APP.parent / "core.py"

def mixin(module: str, name: str) -> type:
    cls = getattr(importlib.import_module(f"hirearchy.app._facade_{module}"), name)
    assert isinstance(cls, type)
    return cls


def own_members(cls: type) -> set[str]:
    return {n for n, raw in vars(cls).items() if _signatures._function(raw) is not None}


def test_there_are_twenty_mixins_in_twenty_files() -> None:
    assert len(MIXINS) == 20
    assert sorted(p.name for p in APP.glob("_facade_*.py")) == sorted(f"_facade_{m}.py" for m, _, _ in MIXINS)


@pytest.mark.parametrize(("module", "name", "methods"), MIXINS, ids=[m for m, _, _ in MIXINS])
def test_a_mixin_holds_exactly_the_methods_of_its_package(module: str, name: str, methods: str) -> None:
    assert own_members(mixin(module, name)) == set(methods.split())



def test_org_is_the_composition_of_the_mixins_in_the_documented_order() -> None:
    from hirearchy.app.facade import Org

    assert [c.__name__ for c in Org.__mro__[1:-1]] == [name for _, name, _ in MIXINS]
    assert own_members(Org) == set()
    assert Org.__module__ == "hirearchy.app.facade"


def test_the_facade_module_documents_the_mro() -> None:
    doc = importlib.import_module("hirearchy.app.facade").__doc__ or ""
    positions = [doc.find(name) for _, name, _ in MIXINS]
    assert -1 not in positions and positions == sorted(positions)  # every mixin, in the order of the bases


def test_core_py_has_no_class_body_and_gets_org_from_the_facade() -> None:
    tree = ast.parse(CORE.read_text(encoding="utf-8"))
    assert not [n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
    imports = [n for n in tree.body if isinstance(n, ast.ImportFrom) and n.module == "app.facade" and n.level == 1]
    assert imports and "Org" in {a.name for n in imports for a in n.names}


def test_core_org_is_the_facade_org() -> None:
    from hirearchy import core
    from hirearchy.app.facade import Org

    assert vars(core)["Org"] is Org
