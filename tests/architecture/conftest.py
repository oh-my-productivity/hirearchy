"""Shared fixtures of the architecture tests: the real source tree, the seeded-violation tree, the architecture document."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from .checks import Tree

REPO = Path(__file__).resolve().parents[2]
SRC = REPO / "src" / "orgmcp"
FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def real_tree() -> Tree:
    return Tree(SRC)


@pytest.fixture
def bad_tree(monkeypatch: pytest.MonkeyPatch):
    """``fixtures/bad_pkg``, importable as ``bad_pkg`` for the duration of one test."""
    monkeypatch.syspath_prepend(str(FIXTURES))
    yield Tree(FIXTURES / "bad_pkg")
    for name in [n for n in sys.modules if n == "bad_pkg" or n.startswith("bad_pkg.")]:
        del sys.modules[name]


@pytest.fixture(scope="session")
def architecture_text() -> str:
    return (REPO / "ARCHITECTURE.md").read_text(encoding="utf-8")
