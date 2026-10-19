"""Helpers shared by the tests of ``access`` (no test lives here)."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest

from orgmcp.access.testing import AccessHarness


def make(request: pytest.FixtureRequest, tmp_path: Path) -> AccessHarness:
    """The fixture body of every contract suite: the harness of one implementation."""
    return cast(Callable[[Path], AccessHarness], request.param)(tmp_path)


def outside(h: AccessHarness, *parts: str) -> Path:
    """A path that is neither inside the organization nor contains it (and does not need to exist)."""
    return h.root.parent / f"{h.root.name}-elsewhere" / Path(*parts)
