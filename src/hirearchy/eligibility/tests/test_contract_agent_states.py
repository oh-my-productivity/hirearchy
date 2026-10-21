"""Contract of ``AgentStates``: the state word of an agent, over mailboxes and flag files on disk and in memory.

The precedence is the contract: running beats paused, paused beats pending, pending beats idle. The word is what ``status``, ``progress``,
``observe`` and the dashboard print."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest

from hirearchy.eligibility import AgentStates
from hirearchy.eligibility.testing import IMPLEMENTATIONS, EligibilityWorld

from ._support import implementations


@pytest.fixture(params=implementations(IMPLEMENTATIONS[AgentStates]))
def w(request: pytest.FixtureRequest, tmp_path: Path) -> EligibilityWorld:
    made = cast(Callable[[Path], EligibilityWorld], request.param)(tmp_path)
    assert isinstance(made.states, AgentStates)
    made.agent("ceo")
    made.agent("ceo/eng")
    return made


def test_an_agent_with_nothing_to_do_is_idle(w: EligibilityWorld) -> None:
    assert w.states.state("ceo") == "idle"


def test_mail_that_wakes_it_makes_it_pending(w: EligibilityWorld) -> None:
    w.mail_to("ceo", True)
    assert w.states.state("ceo") == "pending" and w.states.state("ceo/eng") == "idle"


def test_mail_that_does_not_wake_it_leaves_it_idle(w: EligibilityWorld) -> None:
    w.mail_to("ceo", False)
    assert w.states.state("ceo") == "idle"


def test_a_batch_in_flight_is_running(w: EligibilityWorld) -> None:
    w.mail_to("ceo", True)
    w.begin_run("ceo")
    assert w.states.state("ceo") == "running" and w.states.state("ceo/eng") == "idle"


def test_a_pause_shows_its_reason(w: EligibilityWorld) -> None:
    w.pauses.pause("ceo", "failures")
    assert w.states.state("ceo") == "paused(failures)"


def test_an_empty_flag_shows_paused_paused(w: EligibilityWorld) -> None:
    w.set_flag("ceo", "")
    assert w.states.state("ceo") == "paused(paused)"


def test_a_pause_for_budget_is_a_pause_whatever_the_budget(w: EligibilityWorld) -> None:
    w.set_budget("ceo", 5)
    w.pauses.pause("ceo", "budget")
    assert w.states.state("ceo") == "paused(budget)"


def test_a_human_reason_is_shown_whole(w: EligibilityWorld) -> None:
    w.pauses.pause("ceo", "paused by the user: lunch")
    assert w.states.state("ceo") == "paused(paused by the user: lunch)"


def test_paused_beats_pending(w: EligibilityWorld) -> None:
    w.mail_to("ceo", True)
    w.pauses.pause("ceo", "failures")
    assert w.states.state("ceo") == "paused(failures)"


def test_running_beats_paused(w: EligibilityWorld) -> None:
    w.mail_to("ceo", True)
    w.begin_run("ceo")
    w.pauses.pause("ceo", "budget")
    assert w.states.state("ceo") == "running"


def test_running_beats_pending(w: EligibilityWorld) -> None:
    w.mail_to("ceo", True)
    w.begin_run("ceo")
    w.mail_to("ceo", True)
    assert w.states.state("ceo") == "running"


def test_resuming_gives_back_the_state_below(w: EligibilityWorld) -> None:
    w.mail_to("ceo", True)
    w.pauses.pause("ceo", "failures")
    w.pauses.resume("ceo")
    assert w.states.state("ceo") == "pending"


def test_the_state_of_root_follows_the_same_rules(w: EligibilityWorld) -> None:
    assert w.states.state("root") == "idle"
    w.mail_to("root", True)
    assert w.states.state("root") == "pending"
