"""The public surface of the ``Org`` facade, as data: every ``Org`` method and ``Message`` member, with kind and parameters.

``tests/architecture/org_signatures.json`` was generated from the ``Org`` that existed before the pre-split (step M2) and guards
every later step: the facade keeps the same names, kinds, parameter names, parameter kinds and defaults (annotations are recorded
for the reader but not compared, so a step may tighten a type). Regenerating the file is a deliberate act that changes what
callers of ``Org`` can rely on, never part of a refactor step::

    uv run python -m hirearchy.app.tests._signatures --write
"""

from __future__ import annotations

import dataclasses
import importlib
import inspect
import json
import sys
from collections.abc import Callable
from pathlib import Path

SIGNATURES = Path(__file__).resolve().parents[4] / "tests" / "architecture" / "org_signatures.json"

Entry = dict[str, object]


def _function(raw: object) -> Callable[..., object] | None:
    if isinstance(raw, (staticmethod, classmethod)):
        return raw.__func__
    if isinstance(raw, property):
        return raw.fget
    return raw if inspect.isfunction(raw) else None


def _kind(raw: object) -> str:
    if isinstance(raw, staticmethod):
        return "staticmethod"
    if isinstance(raw, classmethod):
        return "classmethod"
    return "property" if isinstance(raw, property) else "method"


def _entry(raw: object) -> Entry:
    function = _function(raw)
    assert function is not None
    signature = inspect.signature(function)
    params = [
        {"name": p.name, "kind": p.kind.name, "default": None if p.default is p.empty else repr(p.default)}
        for p in signature.parameters.values()
    ]
    return {"kind": _kind(raw), "params": params, "annotated": str(signature)}


def members(cls: type) -> dict[str, Entry]:
    """Every method, static/class method and property of ``cls`` (inherited ones included), by name; ``__init__`` is the only dunder."""
    found: dict[str, Entry] = {}
    for klass in reversed(cls.__mro__):
        if klass is object:
            continue
        for name, raw in vars(klass).items():
            if _function(raw) is None or (name.startswith("__") and name != "__init__"):
                continue
            found[name] = _entry(raw)
    return dict(sorted(found.items()))


def fields(cls: type) -> list[Entry]:
    return [
        {
            "name": f.name,
            "type": str(f.type),
            "has_default": f.default is not dataclasses.MISSING or f.default_factory is not dataclasses.MISSING,
            "compare": f.compare,
        }
        for f in dataclasses.fields(cls)
    ]


def collect() -> dict[str, object]:
    core = importlib.import_module("hirearchy.core")  # by name: the facade is reached through the compatibility module, not imported upward
    Message, Org = core.Message, core.Org
    return {"Org": members(Org), "Message": members(Message), "MessageFields": fields(Message)}


def comparable(entry: Entry) -> object:
    """What a later step must keep: the kind and the parameters (name, kind, default), not the annotations."""
    return entry["kind"], entry["params"]


def main(argv: list[str]) -> int:
    if argv != ["--write"]:
        print(__doc__)
        return 2
    SIGNATURES.write_text(json.dumps(collect(), indent=1) + "\n", encoding="utf-8")
    print(f"wrote {SIGNATURES}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
