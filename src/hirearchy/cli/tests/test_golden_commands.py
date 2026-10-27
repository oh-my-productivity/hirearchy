"""Characterization: the output (standard output, standard error, exit status) of every command line of ``_scenario.SCENARIOS`` is what the flat
``cli.py`` printed, byte for byte. The texts in ``expected/`` were captured from it before the package existed."""

from __future__ import annotations

from pathlib import Path

import pytest

from testkit.cli_world import main

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
    # (mcp serves over stdio: test_mcp_command starts it in a process; acknowledge-playbook needs a covered playbook item: test_service_commands runs it)
    assert set(_scenario.SUBCOMMANDS) - {"mcp", "acknowledge-playbook"} <= used


def test_the_normalizer_hides_the_access_hash_of_a_profile_name(tmp_path: Path) -> None:
    """A confined profile's name ends in ``-x`` and a hash of its rules, which hold the (temporary) path of the organization."""
    normalize = _scenario.normalizer(tmp_path, None)
    one = normalize("wrote ~/.kiro/agents/hirearchy-t-org-1a2b3c-read-write-x0badf00d.json (mcp server: {})")
    two = normalize("wrote ~/.kiro/agents/hirearchy-t-org-4d5e6f-read-write-x9c8b7a65.json (mcp server: {})")
    assert one == two == "wrote ~/.kiro/agents/hirearchy-t-org-<HASH>-read-write-x<ACCESS_HASH>.json (mcp server: {})"
    assert normalize("x0badf00dxx -xyz") == "x0badf00dxx -xyz"  # only a name suffix: -x and exactly 8 hex digits at a word end


def test_the_normalizer_hides_the_kiro_home_of_the_organization(tmp_path: Path) -> None:
    """The kiro home differs by platform (Library/Application Support or .local/state) and by organization (a hash of its path): one placeholder."""
    from testkit.reach.hirearchy.app import wiring

    home = wiring.open_runtime(tmp_path / "org").kiro_places.home()
    normalize = _scenario.normalizer(tmp_path, None)
    assert normalize(f"wrote {home}/agents/hirearchy-t-org-1a2b3c.json") == "wrote <KIRO_HOME>/agents/hirearchy-t-org-<HASH>.json"
