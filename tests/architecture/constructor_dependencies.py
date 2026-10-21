"""The constructor-dependency check (rule R6, "depend on interfaces"): what a class may name in the signature of its ``__init__``.

The ENGINE, like ``class_interfaces`` (whose population it shares): ``test_constructor_dependencies.py`` runs it on ``hirearchy`` and on a
seeded package. The classes looked at are those the class-interface check calls compliant -- classes with behaviour, outside ``hirearchy.app``,
that subclass a Protocol; Protocols, exceptions, framework widgets (Textual) and pure data are exempt there and here. For each of them
``typing.get_type_hints(cls.__init__)`` is resolved (dataclass fields are the parameters of the generated ``__init__``), and every class
that an annotation names -- inside ``Optional``/unions, generics, ``type[...]`` and the arguments and result of a ``Callable`` too -- must be:

* a Protocol, or
* data: a dataclass, ``NamedTuple``, ``TypedDict``, enum or exception, or
* not a class of the package under check at all (builtins, ``pathlib.Path``, ``datetime``, ``collections.abc`` ...).

Anything else is a concrete collaborator: the class constructs-by-type what it should receive through an interface, and only the
composition root (``hirearchy.app``) knows which implementation to pass.

Not looked at: the ``testing`` modules. They hold the in-memory fakes, test support that production never imports (the
``no-testing-in-production`` import contract), and a fake is scripted through the surface of its siblings (``FakeClock.advance``,
the ``MemoryAgents`` tree that ``MemoryMailbox`` shares), which is not part of the Protocol it fakes: 30 fakes name a sibling fake.
"""

from __future__ import annotations

import dataclasses
import enum
import importlib
import inspect
import types
import typing
from collections.abc import Iterator
from dataclasses import dataclass, field
from types import ModuleType

from . import class_interfaces

EXEMPT_MODULE_NAMES = frozenset({"testing"})  # see the docstring


@dataclass(frozen=True)
class Offence:
    cls: str  # dotted module + qualname of the class
    parameter: str
    annotation: str  # the annotation as written (resolved), for the message
    named: str  # the concrete class it names

    def __str__(self) -> str:
        return f"{self.cls}.__init__({self.parameter}: {self.annotation}): {self.named} is a concrete class, not a Protocol"


@dataclass
class Counts:
    classes: int = 0
    parameters: int = 0
    unresolved: list[str] = field(default_factory=list)


def is_data(cls: type) -> bool:
    return bool(dataclasses.is_dataclass(cls) or issubclass(cls, (enum.Enum, BaseException)) or typing.is_typeddict(cls)
                or (issubclass(cls, tuple) and hasattr(cls, "_fields")))


def named_classes(annotation: object) -> Iterator[type]:
    """Every class an annotation names, however deep (unions, generics, ``Annotated``, ``type[X]``, ``Callable`` arguments and result)."""
    if isinstance(annotation, (list, tuple)):
        for item in annotation:
            yield from named_classes(item)
        return
    if isinstance(annotation, typing.TypeVar):
        yield from named_classes([annotation.__bound__] if annotation.__bound__ is not None else list(annotation.__constraints__))
        return
    origin = typing.get_origin(annotation)
    if origin is typing.Literal:
        return
    if origin is typing.Annotated:
        yield from named_classes(typing.get_args(annotation)[:1])
        return
    if origin is not None:
        if isinstance(origin, type) and origin is not types.UnionType:
            yield origin
        yield from named_classes(list(typing.get_args(annotation)))
        return
    if isinstance(annotation, type):
        yield annotation


def concrete_classes(annotation: object, root: str) -> list[type]:
    """The classes of package ``root`` that ``annotation`` names and that are neither Protocols nor data."""
    return [c for c in named_classes(annotation)
            if (c.__module__ == root or c.__module__.startswith(root + ".")) and not class_interfaces.is_protocol_class(c) and not is_data(c)]


def own_constructor(cls: type) -> object | None:
    """``cls.__init__`` when it is a Python function that takes arguments (not ``object.__init__``, not the Protocol placeholder)."""
    init = cls.__init__  # type: ignore[misc]
    return init if inspect.isfunction(init) and init.__module__ != "typing" else None


def survey(package: ModuleType) -> tuple[list[Offence], Counts]:
    """({the concrete dependencies named by constructors}, how much was looked at) over the classes of ``package``."""
    offences: list[Offence] = []
    counts = Counts()
    root = package.__name__
    for name in class_interfaces.source_modules(package):
        if name.rsplit(".", 1)[-1] in EXEMPT_MODULE_NAMES:
            continue
        for cls in class_interfaces.classes_of(importlib.import_module(name)):
            if class_interfaces.exemption(cls) is not None or not class_interfaces.subclasses_a_protocol(cls):
                continue
            counts.classes += 1
            init = own_constructor(cls)
            if init is None:
                continue
            qualified = f"{cls.__module__}.{cls.__qualname__}"
            try:
                hints = typing.get_type_hints(init)
            except Exception as error:  # a name that only exists under TYPE_CHECKING, a typo: the check cannot vouch for this class
                counts.unresolved.append(f"{qualified}: {type(error).__name__}: {error}")
                continue
            counts.parameters += max(len(inspect.signature(init).parameters) - 1, 0)
            for parameter, annotation in hints.items():
                if parameter == "return":
                    continue
                offences.extend(Offence(qualified, parameter, _show(annotation), f"{c.__module__}.{c.__qualname__}")
                                for c in concrete_classes(annotation, root))
    return offences, counts


def _show(annotation: object) -> str:
    return annotation.__qualname__ if isinstance(annotation, type) else str(annotation).replace("typing.", "")
