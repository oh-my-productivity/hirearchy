"""R6, the "depend on interfaces" half: a class receives its collaborators through its constructor, typed by a Protocol.

``test_constructors_depend_on_protocols`` walks the same classes as the class-interface check (``class_interfaces``: classes with
behaviour outside ``hirearchy.app``, not Protocols, exceptions, framework widgets or pure data) and resolves the annotations of the
constructor's parameters (dataclass fields included). An annotation -- inside ``Optional``/unions/generics/``Callable`` arguments too -- must not
name a concrete ``hirearchy`` class: only Protocols, data (dataclass, ``NamedTuple``, enum, ``TypedDict``, exception) and types that are not
``hirearchy`` classes (builtins, ``pathlib.Path``, ``datetime``, ...). The seeded tests build a package with one violation of each shape.
"""

from __future__ import annotations

import sys
import textwrap
from pathlib import Path
from types import ModuleType

import pytest

import hirearchy
from . import constructor_dependencies as deps

pytestmark = pytest.mark.architecture

BAD_MODULE = '''
from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import NamedTuple, Optional, Protocol


class Store(Protocol):
    def get(self) -> str: ...


class Colour(Enum):
    RED = 1


class Pair(NamedTuple):
    left: str
    right: str


@dataclass(frozen=True)
class Record:
    name: str


class Failure(Exception):
    pass


class FsStore(Store):
    """A concrete class: nobody may name it in a constructor."""

    def get(self) -> str:
        return "fs"


class Good(Store):
    def __init__(self, store: Store, maybe: Store | None, many: list[Store], call: Callable[[Store], Store], where: Path,
                 record: Record, colour: Colour, pair: Pair, error: Failure | None = None, *rest: Mapping[str, Store],
                 **named: Optional[Store]) -> None:
        pass

    def get(self) -> str:
        return "good"


class BadPlain(Store):
    def __init__(self, store: FsStore) -> None:
        pass

    def get(self) -> str:
        return "bad"


class BadOptional(Store):
    def __init__(self, store: Optional[FsStore] = None) -> None:
        pass

    def get(self) -> str:
        return "bad"


class BadUnion(Store):
    def __init__(self, store: Store | FsStore) -> None:
        pass

    def get(self) -> str:
        return "bad"


class BadGeneric(Store):
    def __init__(self, stores: dict[str, list[FsStore]]) -> None:
        pass

    def get(self) -> str:
        return "bad"


class BadCallable(Store):
    def __init__(self, make: Callable[[str], FsStore], use: Callable[[FsStore], None]) -> None:
        pass

    def get(self) -> str:
        return "bad"


class BadType(Store):
    def __init__(self, factory: type[FsStore]) -> None:
        pass

    def get(self) -> str:
        return "bad"


@dataclass
class BadField(Store):
    store: FsStore
    fine: Store

    def get(self) -> str:
        return "bad"


class Outer:
    """No Protocol base: the class-interface check reports it; this check looks only at classes that implement one."""

    def __init__(self, store: FsStore) -> None:
        pass
'''

FAKES_MODULE = '''
from __future__ import annotations

from ._shapes import FsStore, Store


class MemoryStore(Store):
    """A fake scripted through the surface of its sibling: the one place where a concrete class may be named."""

    def __init__(self, sibling: FsStore) -> None:
        pass

    def get(self) -> str:
        return "memory"
'''

BAD_CLASSES = ["BadCallable", "BadField", "BadGeneric", "BadOptional", "BadPlain", "BadType", "BadUnion"]


@pytest.fixture
def bad_package(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    root = tmp_path / "bad_ctor_pkg"
    root.mkdir()
    (root / "__init__.py").write_text("", encoding="utf-8")
    (root / "_shapes.py").write_text(textwrap.dedent(BAD_MODULE), encoding="utf-8")
    (root / "testing.py").write_text(textwrap.dedent(FAKES_MODULE), encoding="utf-8")
    monkeypatch.syspath_prepend(str(tmp_path))
    import importlib

    yield importlib.import_module("bad_ctor_pkg")
    for name in [n for n in sys.modules if n == "bad_ctor_pkg" or n.startswith("bad_ctor_pkg.")]:
        del sys.modules[name]


# ----------------------------------------------------------------------------------------------------------- real code


def test_constructors_depend_on_protocols() -> None:
    offences, counts = deps.survey(hirearchy)
    assert not offences, "a constructor names a concrete class (take the Protocol, and let hirearchy.app pass the implementation):\n  " + \
        "\n  ".join(str(o) for o in offences)
    assert counts.unresolved == [], f"annotations that could not be resolved: {counts.unresolved}"
    assert counts.classes > 300 and counts.parameters > 1000  # the check looks at the whole population, not at nothing


# --------------------------------------------------------------------------------------------- seeded violations: each fails


def test_every_shape_of_a_concrete_dependency_is_flagged(bad_package: ModuleType) -> None:
    offences, _ = deps.survey(bad_package)
    assert sorted({o.cls.rsplit(".", 1)[-1] for o in offences}) == BAD_CLASSES, [str(o) for o in offences]
    assert {o.named for o in offences} == {"bad_ctor_pkg._shapes.FsStore"}


def test_a_compliant_constructor_is_quiet_and_is_counted(bad_package: ModuleType) -> None:
    offences, counts = deps.survey(bad_package)
    assert not any(o.cls.endswith(".Good") for o in offences)
    assert counts.classes >= 8 and counts.parameters >= 13  # Good has 11 parameters on its own


def test_the_offence_names_the_class_the_parameter_and_the_annotation(bad_package: ModuleType) -> None:
    offences, _ = deps.survey(bad_package)
    found = {(o.cls.rsplit(".", 1)[-1], o.parameter) for o in offences}
    assert ("BadPlain", "store") in found and ("BadCallable", "make") in found and ("BadCallable", "use") in found
    assert ("BadField", "store") in found and ("BadField", "fine") not in found
    plain = next(o for o in offences if o.cls.endswith(".BadPlain"))
    assert "BadPlain.__init__(store: " in str(plain) and "FsStore" in str(plain)


def test_a_class_without_a_protocol_is_the_business_of_the_class_interface_check(bad_package: ModuleType) -> None:
    offences, _ = deps.survey(bad_package)
    assert not any(o.cls.endswith(".Outer") for o in offences)


def test_the_in_memory_fakes_of_a_testing_module_may_name_their_siblings(bad_package: ModuleType) -> None:
    offences, _ = deps.survey(bad_package)
    assert not any(o.cls.endswith(".MemoryStore") for o in offences)
    assert deps.EXEMPT_MODULE_NAMES == {"testing"}
