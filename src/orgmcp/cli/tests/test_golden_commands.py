"""Characterization: the output (standard output, standard error, exit status) of every command line of ``_scenario.SCENARIOS`` is what the flat
``cli.py`` printed, byte for byte. The texts in ``expected/`` were captured from it before the package existed."""

from __future__ import annotations

from pathlib import Path

import pytest

from orgmcp.cli import main

from . import _scenario
from ._golden import EXPECTED, check


@pytest.mark.parametrize("label", sorted(_scenario.SCENARIOS))
def test_the_command_line_prints_what_it_printed(label: str, tmp_path: Path) -> None:
    check(f"{label}.txt", _scenario.execute(label, tmp_path, main))


def test_every_expected_text_has_a_scenario_and_every_scenario_a_text() -> None:
    names = {path.stem for path in EXPECTED.glob("*.txt") if not path.name.startswith("help")}
    assert names == set(_scenario.SCENARIOS)


def test_the_scenarios_cover_every_command() -> None:
    used = {scenario.argv[2] if scenario.argv[:1] == ("--root",) else scenario.argv[0] for scenario in _scenario.SCENARIOS.values() if scenario.argv}
    assert set(_scenario.SUBCOMMANDS) - {"mcp"} <= used  # (mcp serves over stdio: test_mcp_command starts it in a process)
