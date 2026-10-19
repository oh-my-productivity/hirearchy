"""Contract of ``OrgTree``: the text of ``status``, over mailboxes and agents on disk and in memory.

The text is the contract (it is golden: the CLI and the MCP tool print it): the root line, then one line per agent, indented by depth, with the
numbers the other features report."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest

from orgmcp.overview import OrgTree
from orgmcp.overview.testing import IMPLEMENTATIONS, OverviewWorld

from ._support import implementations

ROOT_LINE = "root (human): unread 0, delegated 0"

pytestmark = pytest.mark.xfail(strict=True, reason="red: C-overview")


@pytest.fixture(params=implementations(IMPLEMENTATIONS[OrgTree]))
def w(request: pytest.FixtureRequest, tmp_path: Path) -> OverviewWorld:
    made = cast(Callable[[Path], OverviewWorld], request.param)(tmp_path)
    assert isinstance(made.tree, OrgTree)
    return made


def lines(w: OverviewWorld) -> list[str]:
    return w.tree.tree().split("\n")


def test_an_organization_without_agents_is_the_root_line(w: OverviewWorld) -> None:
    assert w.tree.tree() == ROOT_LINE


def test_an_agent_line_names_the_agent_its_role_its_state_and_its_numbers(w: OverviewWorld) -> None:
    w.agent("ceo", "Chief executive")
    assert lines(w) == [ROOT_LINE, "  ceo [Chief executive] idle  budget=0 open=0 delegated=0 unread=0"]


def test_there_are_two_spaces_between_the_state_and_the_budget(w: OverviewWorld) -> None:
    w.agent("ceo", "R")
    w.set_state("ceo", "paused(budget)")
    assert lines(w)[1] == "  ceo [R] paused(budget)  budget=0 open=0 delegated=0 unread=0"


def test_the_state_is_the_word_of_the_state_port(w: OverviewWorld) -> None:
    w.agent("ceo", "R")
    for word in ("running", "pending", "paused(paused by the user: lunch)", "idle"):
        w.set_state("ceo", word)
        assert f"] {word}  budget=" in lines(w)[1]


def test_the_budget_is_the_number_of_runs_the_agent_has_left(w: OverviewWorld) -> None:
    w.agent("ceo", "R")
    w.set_budget("ceo", 14)
    assert " budget=14 " in lines(w)[1]
    w.set_budget("ceo", -2)  # a redelivered run is charged like any run: the budget can be negative
    assert " budget=-2 " in lines(w)[1]


def test_a_charter_without_a_role_shows_a_question_mark(w: OverviewWorld) -> None:
    w.agent("ceo", None)
    assert lines(w)[1].startswith("  ceo [?] idle  ")


def test_open_delegated_and_unread_count_the_tasks_and_the_mail_that_wakes(w: OverviewWorld) -> None:
    w.agent("ceo", "R")
    w.agent("ceo/eng", "R")
    w.delegate("root", "ceo", True)  # open and unread for ceo
    w.delegate("root", "ceo", False)  # open, held without waking: not unread
    w.delegate("ceo", "ceo/eng", True)  # delegated by ceo, open and unread for eng
    w.mail_to("ceo", True)  # unread, no task
    assert lines(w)[1:] == [
        "  ceo [R] idle  budget=0 open=2 delegated=1 unread=2",
        "    eng [R] idle  budget=0 open=1 delegated=0 unread=1",
    ]


def test_the_root_line_counts_what_waits_for_the_human_and_what_the_human_delegated(w: OverviewWorld) -> None:
    w.agent("ceo", "R")
    w.mail_to("root", True)
    w.mail_to("root", True)
    w.mail_to("root", False)
    w.delegate("root", "ceo", True)
    assert lines(w)[0] == "root (human): unread 2, delegated 1"


def test_agents_come_parents_before_children_siblings_sorted_indented_by_depth(w: OverviewWorld) -> None:
    for addr in ("ops", "ceo", "ceo/qa", "ceo/eng", "ceo/eng/dev", "ops/sre"):
        w.agent(addr, "R")
    names = [line.strip().split(" ", 1)[0] for line in lines(w)[1:]]
    assert names == ["ceo", "eng", "dev", "qa", "ops", "sre"]
    assert [len(line) - len(line.lstrip(" ")) for line in lines(w)[1:]] == [2, 4, 6, 4, 2, 4]


def test_the_services_an_agent_offers_follow_its_numbers_by_name(w: OverviewWorld) -> None:
    w.agent("ceo", "R")
    w.agent("ops", "R")
    w.offer("ceo", ["audit", "weekly-brief"])
    assert lines(w)[1:] == [
        "  ceo [R] idle  budget=0 open=0 delegated=0 unread=0 services: audit, weekly-brief",
        "  ops [R] idle  budget=0 open=0 delegated=0 unread=0",
    ]


def test_there_is_no_trailing_newline(w: OverviewWorld) -> None:
    w.agent("ceo", "R")
    assert not w.tree.tree().endswith("\n")


def test_the_tree_is_read_afresh_at_every_call(w: OverviewWorld) -> None:
    w.agent("ceo", "R")
    before = w.tree.tree()
    w.mail_to("ceo", True)
    w.set_budget("ceo", 3)
    assert w.tree.tree() != before and " budget=3 open=0 delegated=0 unread=1" in w.tree.tree()
