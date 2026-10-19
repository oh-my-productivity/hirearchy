"""Contract of ``RunnableQuery``: which agents the scheduler may start, over mailboxes, flag files and budgets on disk and in memory.

``runnable`` (all agents) and ``startable`` (one agent) are the same rule, pinned here by one table: mail that wakes the agent, budget above 0, and no
pause but ``budget`` (which does not count once budget is back). The queries only read: lifting a pause is the scheduler's act."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest

from orgmcp.eligibility import RunnableQuery
from orgmcp.eligibility.testing import IMPLEMENTATIONS, EligibilityWorld

from ._support import implementations

# (mail that wakes, mail that does not wake, budget, flag text or None, runs in flight) -> may it start
TABLE = {
    "mail and budget": (1, 0, 2, None, False, True),
    "a lot of mail": (5, 0, 1, None, False, True),
    "no mail": (0, 0, 2, None, False, False),
    "mail that does not wake": (0, 1, 2, None, False, False),
    "mail that wakes and mail that does not": (1, 1, 2, None, False, True),
    "no budget": (1, 0, 0, None, False, False),
    "negative budget": (1, 0, -1, None, False, False),
    "paused for failures": (1, 0, 2, "failures", False, False),
    "paused by a human": (1, 0, 2, "paused by the user: lunch", False, False),
    "paused by an empty flag": (1, 0, 2, "", False, False),
    "paused for budget, budget is back": (1, 0, 2, "budget", False, True),
    "paused for budget, still none": (1, 0, 0, "budget", False, False),
    "paused for budget, in debt": (1, 0, -3, "budget", False, False),
    "paused for budget, no mail": (0, 0, 2, "budget", False, False),
    "new mail while a run is in flight": (1, 0, 2, None, True, True),
}


@pytest.fixture(params=implementations(IMPLEMENTATIONS[RunnableQuery]))
def w(request: pytest.FixtureRequest, tmp_path: Path) -> EligibilityWorld:
    made = cast(Callable[[Path], EligibilityWorld], request.param)(tmp_path)
    assert isinstance(made.runnable, RunnableQuery)
    return made


def prepare(w: EligibilityWorld, addr: str, row: tuple[int, int, int, str | None, bool, bool]) -> None:
    wakes, held, budget, flag, running, _ = row
    w.agent(addr)
    w.set_budget(addr, budget)
    if running:
        w.mail_to(addr, True)
        w.begin_run(addr)
    for _ in range(wakes):
        w.mail_to(addr, True)
    for _ in range(held):
        w.mail_to(addr, False)
    if flag is not None:
        w.set_flag(addr, flag)


@pytest.mark.parametrize("name", TABLE)
def test_startable_follows_the_table(w: EligibilityWorld, name: str) -> None:
    prepare(w, "ceo", TABLE[name])
    assert w.runnable.startable("ceo") is TABLE[name][5]


@pytest.mark.parametrize("name", TABLE)
def test_runnable_follows_the_same_table(w: EligibilityWorld, name: str) -> None:
    prepare(w, "ceo", TABLE[name])
    assert w.runnable.runnable() == (["ceo"] if TABLE[name][5] else [])


def test_startable_and_runnable_agree_for_every_agent_at_once(w: EligibilityWorld) -> None:
    for n, name in enumerate(TABLE):
        prepare(w, f"ceo/a{n:02d}", TABLE[name])
    startable = [f"ceo/a{n:02d}" for n in range(len(TABLE)) if w.runnable.startable(f"ceo/a{n:02d}")]
    assert w.runnable.runnable() == startable and len(startable) == sum(1 for row in TABLE.values() if row[5])


# ------------------------------------------------------------------------------ the agents


def test_nobody_is_runnable_in_an_empty_organization(w: EligibilityWorld) -> None:
    assert w.runnable.runnable() == []


def test_the_agents_come_parents_before_children(w: EligibilityWorld) -> None:
    for addr in ("ceo/eng", "ceo", "ceo/eng/dev", "cto"):
        prepare(w, addr, TABLE["mail and budget"])
    assert w.runnable.runnable() == ["ceo", "ceo/eng", "ceo/eng/dev", "cto"]


def test_an_agent_that_is_excluded_is_left_out(w: EligibilityWorld) -> None:
    for addr in ("ceo", "ceo/eng", "cto"):
        prepare(w, addr, TABLE["mail and budget"])
    assert w.runnable.runnable(exclude={"ceo/eng"}) == ["ceo", "cto"]


@pytest.mark.parametrize("kind", [list, tuple, set, frozenset])
def test_the_exclusion_is_any_collection(w: EligibilityWorld, kind: type) -> None:
    for addr in ("ceo", "cto"):
        prepare(w, addr, TABLE["mail and budget"])
    assert w.runnable.runnable(exclude=kind(["cto"])) == ["ceo"]


def test_excluding_an_agent_that_is_not_there_changes_nothing(w: EligibilityWorld) -> None:
    prepare(w, "ceo", TABLE["mail and budget"])
    assert w.runnable.runnable(exclude=["ghost"]) == ["ceo"]


def test_an_agent_that_has_no_budget_account_is_not_startable(w: EligibilityWorld) -> None:
    w.mail_to("root", True)
    assert w.runnable.startable("root") is False


def test_an_agent_that_is_not_there_is_not_startable(w: EligibilityWorld) -> None:
    assert w.runnable.startable("ghost") is False


def test_what_was_not_startable_becomes_so_when_budget_is_granted(w: EligibilityWorld) -> None:
    prepare(w, "ceo", TABLE["no budget"])
    assert w.runnable.runnable() == []
    w.set_budget("ceo", 1)
    assert w.runnable.runnable() == ["ceo"]


# ------------------------------------------------------------------------------ read only


def test_the_queries_do_not_lift_a_pause_for_budget(w: EligibilityWorld) -> None:
    prepare(w, "ceo", TABLE["paused for budget, budget is back"])
    w.runnable.runnable()
    w.runnable.startable("ceo")
    assert w.pauses.paused("ceo") == "budget" and w.events.events == []
