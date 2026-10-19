"""Helpers shared by the tests of ``strays`` (no test lives here)."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest

from orgmcp.strays.testing import StraysHarness

def make(request: pytest.FixtureRequest, tmp_path: Path) -> StraysHarness:
    """The fixture body of every contract suite: the harness of one implementation."""
    return cast(Callable[[Path], StraysHarness], request.param)(tmp_path)


def writer(h: StraysHarness, addr: str, tools: list[str] | None = None) -> Path:
    """``addr`` becomes an agent with the built-in ``write`` (or these ``tools``) and a workspace of its own; returns the workspace."""
    ws = h.workspace / addr.replace("/", "-")
    h.put_agent(addr, {"role": "R", "tools": ["write"] if tools is None else tools, "workspace": str(ws)})
    return ws
