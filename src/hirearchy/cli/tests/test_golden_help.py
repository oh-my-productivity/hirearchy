"""Characterization: the ``--help`` of the program, of each of the 25 commands and of the 4 views of ``obs`` is argparse's text of the flat
``cli.py``, byte for byte (names, flags, help strings and defaults are the interface)."""

from __future__ import annotations

import re

import pytest

from testkit.cli_world import main

from . import _scenario
from ._golden import check


def test_the_program_lists_the_25_commands() -> None:
    text = _scenario.help_text(main)
    assert tuple(re.search(r"\{([a-z,\-]+)\}", text).group(1).split(",")) == _scenario.SUBCOMMANDS  # type: ignore[union-attr]
    check("help.txt", text)


def test_obs_lists_its_4_views() -> None:
    text = _scenario.help_text(main, "obs")
    assert tuple(re.search(r"\{([a-z,]+)\}", text).group(1).split(",")) == _scenario.OBS_VIEWS  # type: ignore[union-attr]


@pytest.mark.parametrize("command", _scenario.SUBCOMMANDS)
def test_help_of_a_command(command: str) -> None:
    check(f"help_{command}.txt", _scenario.help_text(main, command))


@pytest.mark.parametrize("view", _scenario.OBS_VIEWS)
def test_help_of_an_obs_view(view: str) -> None:
    check(f"help_obs_{view}.txt", _scenario.help_text(main, "obs", view))
