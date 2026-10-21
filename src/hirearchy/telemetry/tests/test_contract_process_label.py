"""Contract of ``ProcessLabel``: ``cli`` until named; only ``scheduler``, ``mcp`` and ``cli`` are names."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest

from hirearchy.telemetry import ProcessLabel
from hirearchy.telemetry.testing import IMPLEMENTATIONS



@pytest.fixture(params=IMPLEMENTATIONS[ProcessLabel], ids=lambda factory: factory.__name__)
def label(request: pytest.FixtureRequest, tmp_path: Path) -> ProcessLabel:
    made = cast(Callable[[Path], ProcessLabel], request.param)(tmp_path)
    assert isinstance(made, ProcessLabel)
    return made


def test_a_process_is_the_cli_until_it_is_named(label: ProcessLabel) -> None:
    assert label.get() == "cli"


@pytest.mark.parametrize("name", ["scheduler", "mcp", "cli"])
def test_a_known_name_is_kept(label: ProcessLabel, name: str) -> None:
    label.set(name)
    assert label.get() == name


@pytest.mark.parametrize("name", ["", "dashboard", "MCP", "mcp ", "scheduler-2"])
def test_an_unknown_name_means_the_cli(label: ProcessLabel, name: str) -> None:
    label.set("scheduler")
    label.set(name)
    assert label.get() == "cli"


def test_the_last_name_wins(label: ProcessLabel) -> None:
    label.set("scheduler")
    label.set("mcp")
    assert label.get() == "mcp"
