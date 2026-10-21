"""Contract of ``McpServerLocator``: a ``command`` and its ``args`` that start ``hirearchy mcp``."""

from __future__ import annotations

from pathlib import Path

import pytest

from hirearchy.kiro import McpServerLocator
from hirearchy.kiro.testing import IMPLEMENTATIONS, LocatorHarness

from ._support import make


@pytest.fixture(params=IMPLEMENTATIONS[McpServerLocator], ids=lambda factory: factory.__name__)
def h(request: pytest.FixtureRequest, tmp_path: Path) -> LocatorHarness:
    made = make(request, tmp_path, LocatorHarness)
    assert isinstance(made.locator, McpServerLocator)
    return made


def test_the_command_is_a_program_and_the_arguments_end_in_mcp(h: LocatorHarness) -> None:
    command = h.locator.command()
    assert set(command) == {"command", "args"}
    assert isinstance(command["command"], str) and command["command"]
    args = command["args"]
    assert isinstance(args, list) and all(isinstance(a, str) for a in args) and args[-1] == "mcp"


def test_the_command_is_json_serializable(h: LocatorHarness) -> None:
    import json

    assert json.loads(json.dumps(h.locator.command())) == h.locator.command()


def test_every_call_answers_a_fresh_dictionary(h: LocatorHarness) -> None:
    first = h.locator.command()
    first["command"] = "changed"
    args = first["args"]
    assert isinstance(args, list)
    args.append("extra")
    assert h.locator.command() != first
    assert h.locator.command() == h.locator.command()
    assert h.locator.command()["args"][-1] == "mcp"  # type: ignore[index]
