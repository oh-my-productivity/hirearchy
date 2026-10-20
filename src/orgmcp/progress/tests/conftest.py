"""The organization of the contract suite: ``ceo`` and ``ceo/eng`` hired, over disk and over memory; and the scenario of the golden texts."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

import pytest

from orgmcp.kernel import ROOT, Message
from orgmcp.progress import ProgressReporter
from orgmcp.progress.testing import IMPLEMENTATIONS, ProgressWorld

from . import _scenario


@pytest.fixture(params=IMPLEMENTATIONS[ProgressReporter], ids=lambda make: make.__name__)
def w(request: pytest.FixtureRequest, tmp_path: Path) -> ProgressWorld:
    """``ceo`` and ``ceo/eng`` exist; nothing else does."""
    made = cast(Callable[[Path], ProgressWorld], request.param)(tmp_path)
    assert isinstance(made.reporter, ProgressReporter)
    made.hire("ceo")
    made.hire("ceo/eng")
    return made


@pytest.fixture
def task(w: ProgressWorld) -> Message:
    """Root gave ``ceo`` the task "Write the report", with 8 runs."""
    return w.delegate(ROOT, "ceo", "Write the report", 8)


@pytest.fixture
def scenario(tmp_path: Path, process_overrides: Any) -> Any:
    """The legacy ``Org`` of ``_scenario.build``; the clock and the ids of the runtimes are fixed for the length of the test."""
    clock = _scenario.install(process_overrides)
    return _scenario.build(tmp_path, clock)
