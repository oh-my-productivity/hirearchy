"""Contract of ``SchedulerCommand``: ``<program> --root <org> run [--max-runs N] [--until-done]``."""

from __future__ import annotations

from pathlib import Path

import pytest

from hirearchy.daemon import SchedulerCommand
from hirearchy.daemon.testing import IMPLEMENTATIONS, CommandWorld

from ._support import build, worlds


@pytest.fixture(params=worlds(IMPLEMENTATIONS[SchedulerCommand]))
def w(request: pytest.FixtureRequest, tmp_path: Path) -> CommandWorld:
    world = build(request, tmp_path, CommandWorld)
    assert isinstance(world.command, SchedulerCommand)
    return world


def test_the_command_runs_the_scheduler_of_the_organization(w: CommandWorld) -> None:
    assert w.command.argv(None, False) == [*w.program, "--root", str(w.root), "run"]


@pytest.mark.parametrize("cap", [0, 1, 3, 250])
def test_a_cap_is_given_as_max_runs(w: CommandWorld, cap: int) -> None:
    assert w.command.argv(cap, False) == [*w.program, "--root", str(w.root), "run", "--max-runs", str(cap)]


def test_until_done_is_given_as_a_flag(w: CommandWorld) -> None:
    assert w.command.argv(None, True) == [*w.program, "--root", str(w.root), "run", "--until-done"]


def test_the_cap_comes_before_until_done(w: CommandWorld) -> None:
    assert w.command.argv(3, True) == [*w.program, "--root", str(w.root), "run", "--max-runs", "3", "--until-done"]


def test_every_answer_is_a_list_of_its_own(w: CommandWorld) -> None:
    first = w.command.argv(None, False)
    first.append("--tampered")
    assert w.command.argv(None, False) == [*w.program, "--root", str(w.root), "run"]
