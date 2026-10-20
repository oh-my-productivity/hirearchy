"""Helpers shared by the tests of ``agents`` (no test lives here)."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest

from orgmcp.agents.testing import AgentsHarness

CHARTER = "---\nrole: Researcher\ntools: [read]\n---\n# Role: Researcher\n\nFind things out.\n"


def make(request: pytest.FixtureRequest, tmp_path: Path) -> AgentsHarness:
    """The fixture body of every contract suite: the harness of one implementation."""
    return cast(Callable[[Path], AgentsHarness], request.param)(tmp_path)


def agent(h: AgentsHarness, addr: str, charter: str = CHARTER) -> None:
    """Make ``addr`` an agent (its directory with an ``AGENT.md``), behind the registry's back."""
    h.put(f"{addr}/AGENT.md", charter)


def message(budget: object = None, *, sender: str = "root", to: str = "ceo", kind: str = "task", extra: str = "") -> str:
    """The text of a message file; ``budget=None`` leaves the key out."""
    lines = [f"from: {sender}", f"to: {to}", f"type: {kind}"]
    if budget is not None:
        lines.append(f"budget: {budget}")
    return "---\n" + "\n".join(lines) + extra + "\n---\nbody\n"
