"""Contract of ``KiroStateDirs``: the private home and the fresh scratch directory (docs/design/kiro-runtime-v3.md 8.2)."""

from __future__ import annotations

from pathlib import Path

import pytest

from hirearchy.kiro import KiroStateDirs
from hirearchy.kiro.testing import IMPLEMENTATIONS, StateHarness

from ._support import make


@pytest.fixture(params=IMPLEMENTATIONS[KiroStateDirs], ids=lambda factory: factory.__name__)
def h(request: pytest.FixtureRequest, tmp_path: Path) -> StateHarness:
    made = make(request, tmp_path, StateHarness)
    assert isinstance(made.dirs, KiroStateDirs)
    return made


def test_fresh_leaves_an_empty_directory(h: StateHarness) -> None:
    scratch = h.base / "cwd" / "org" / "agent"
    h.dirs.fresh(scratch)
    assert h.is_empty_dir(scratch)


def test_fresh_twice_leaves_an_empty_directory(h: StateHarness) -> None:
    scratch = h.base / "cwd" / "org" / "agent"
    h.dirs.fresh(scratch)
    h.dirs.fresh(scratch)
    assert h.is_empty_dir(scratch)


def test_private_dir_makes_a_private_directory(h: StateHarness) -> None:
    home = h.base / "state" / "home"
    h.dirs.private_dir(home)
    assert h.is_private_dir(home)


def test_private_dir_is_idempotent(h: StateHarness) -> None:
    home = h.base / "state" / "home"
    h.dirs.private_dir(home)
    h.dirs.private_dir(home)
    assert h.is_private_dir(home)
