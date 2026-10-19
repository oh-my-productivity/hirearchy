"""Helpers shared by the tests of ``kiro`` (no test lives here)."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import TypeVar, cast

import pytest

RED = "red: B-kiro"
GOLDEN = Path(__file__).resolve().parent / "golden"
T = TypeVar("T")


def make(request: pytest.FixtureRequest, tmp_path: Path, kind: type[T]) -> T:
    """The fixture body of every contract suite: the harness (or the implementation) of one registered factory."""
    made = cast(Callable[[Path], object], request.param)(tmp_path)
    assert isinstance(made, kind)
    return made


def golden(name: str) -> object:
    """A characterization file captured from the legacy ``scheduler`` functions of ``main``."""
    return json.loads((GOLDEN / name).read_text(encoding="utf-8"))
