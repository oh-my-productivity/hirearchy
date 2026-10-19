"""The legacy functions of ``scheduler`` and ``progress`` that ask ``attention``: ``waiting_on_user``, ``nothing_to_do``, ``_human_items``, ``_needs_human``
and the check of whether an agent could run. The texts, the options and the decisions are pinned by ``tests/test_finish``, ``test_progress`` and
``test_progress_wait`` (unchanged); here are the seams."""

from __future__ import annotations

import dataclasses
from collections.abc import Collection
from pathlib import Path

import pytest

from orgmcp import progress as progress_module
from orgmcp import scheduler as sched_module
from orgmcp.app import Org
from orgmcp.attention import Waiting
from orgmcp.eligibility import RunnableQuery
from orgmcp.kernel import ROOT

RED = pytest.mark.xfail(strict=True, reason="red: C-attention")


class Runnable(RunnableQuery):
    """What may start is what the test says."""

    def __init__(self, *startable: str) -> None:
        self.startable_agents = set(startable)

    def runnable(self, exclude: Collection[str] = ()) -> list[str]:
        return sorted(self.startable_agents - set(exclude))

    def startable(self, addr: str) -> bool:
        return addr in self.startable_agents


@pytest.fixture
def org(tmp_path: Path) -> Org:
    made = Org.init(tmp_path / "org", "mission")
    made.hire("root", "ceo", "Chief", "Run it.")
    return made


@RED
def test_the_scheduler_exports_the_waiting_of_the_package() -> None:
    assert getattr(sched_module, "Waiting") is Waiting


@RED
def test_waiting_on_user_is_a_waiting_of_the_package(org: Org) -> None:
    org.delegate(ROOT, "ceo", "Ship it", "Ship", "Shipped", budget=1)
    org.start_run_log("ceo")
    found = sched_module.waiting_on_user(org)
    assert isinstance(found, Waiting) and found.text == 'waiting on you: "Ship it" needs budget (ceo out of runs)'


def test_waiting_on_user_asks_the_runnable_query_of_the_runtime_in_force(org: Org) -> None:
    org.delegate(ROOT, "ceo", "Ship it", "Ship", "Shipped", budget=1)
    org.start_run_log("ceo")
    assert sched_module.waiting_on_user(org) is not None
    org.runtime = dataclasses.replace(org.runtime, runnable_query=Runnable("ceo"))
    assert sched_module.waiting_on_user(org) is None


def test_nothing_to_do_asks_the_runnable_query_of_the_runtime_in_force(org: Org) -> None:
    assert sched_module.nothing_to_do(org) is True
    org.runtime = dataclasses.replace(org.runtime, runnable_query=Runnable("ceo"))
    assert sched_module.nothing_to_do(org) is False


@RED
def test_the_helpers_of_the_decision_are_gone_from_the_scheduler() -> None:
    assert not hasattr(sched_module, "_startable") and not hasattr(sched_module, "_names")


def test_human_items_are_the_queue_of_the_package(org: Org) -> None:
    sent = org.send("ceo", ROOT, "I need 2 more runs", title="Budget request")
    assert progress_module._human_items(org) == [
        (sent.id, f'Needs you: note from ceo "Budget request": I need 2 more runs (message {sent.id})')
    ]
    assert progress_module._needs_human(org) == [line for _, line in progress_module._human_items(org)]


@RED
def test_the_progress_checks_whether_an_agent_could_run_through_the_runnable_query(org: Org) -> None:
    org.delegate(ROOT, "ceo", "Ship it", "Ship", "Shipped", budget=1)
    org.start_run_log("ceo")
    assert progress_module._can_run(org, "ceo") is False  # unread, but no runs
    org.runtime = dataclasses.replace(org.runtime, runnable_query=Runnable("ceo"))
    assert progress_module._can_run(org, "ceo") is True


def test_a_running_agent_could_run_whatever_the_runnable_query_says(org: Org) -> None:
    org.delegate(ROOT, "ceo", "Ship it", "Ship", "Shipped", budget=1)
    org.begin_run("ceo")
    org.runtime = dataclasses.replace(org.runtime, runnable_query=Runnable())
    assert progress_module._can_run(org, "ceo") is True
