"""The prompts slice of the ``Org`` facade: ``whoami``, ``state_summary`` and ``run_prompt`` (and the private spellings the signature guard keeps) say
what they always said, byte for byte. The snapshots were recorded from the mixin as it was before it moved (green before and after); the golden suite
(``tests/golden``) pins the rest."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from orgmcp.app import Org
from orgmcp.app.tests import _prompt_scenarios as scenarios


# ----------------------------------------------------------------------------------- as it always was (green before and after)


@pytest.mark.parametrize("name", sorted(scenarios.SCENARIOS))
def test_the_text_is_the_recorded_one(name: str, tmp_path: Path) -> None:
    assert scenarios.render(name, tmp_path.resolve()) == (scenarios.SNAPSHOTS / f"{name}.txt").read_text(encoding="utf-8")


def test_there_is_a_snapshot_for_every_scenario_and_no_other() -> None:
    assert sorted(p.stem for p in scenarios.SNAPSHOTS.glob("*.txt")) == sorted(scenarios.SCENARIOS)


@pytest.fixture
def org(tmp_path: Path) -> Org:
    return scenarios.make(tmp_path)


def test_the_unknown_agent_is_refused_by_all_three(org: Org) -> None:
    for name, args in (("whoami", ("nobody",)), ("state_summary", ("nobody",)), ("run_prompt", ("nobody", []))):
        with pytest.raises(Exception, match="no such agent: nobody"):
            getattr(org, name)(*args)


def test_the_private_helpers_of_the_old_mixin_still_answer(org: Org, tmp_path: Path) -> None:
    task = org.delegate("root", "ceo", "Plan", "Make a plan.", "plan.md exists", budget=6)
    private: Any = org  # the helpers are private: the signature guard keeps them, the type does not name them
    assert private._indent("a\nb", 2) == "  a\n  b"
    assert private._agent_line("ceo") == "ceo [Chief executive] pending, budget 6, open tasks 1, delegated 0, unread 1"
    assert private._quote(task) == "> ## Goal\n> Make a plan.\n>\n> ## Acceptance criteria\n> plan.md exists"
    assert private._files_lines("ceo", {}) == []
    assert private._render_in_context("ceo", task) == task.render()
    assert private._upstream("ceo", task) is None
