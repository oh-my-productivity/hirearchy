"""The ports of ``attention`` the scheduler asks (``waiting_on_user``, ``open_work``) ask the runnable query of the runtime. The texts, the options and the
decisions are pinned by ``tests/test_finish``, ``test_progress`` and ``test_progress_wait`` (unchanged); here are the seams."""

from __future__ import annotations

from collections.abc import Collection
from pathlib import Path

import pytest

from hirearchy.app import Org, wiring
from hirearchy.attention import Waiting
from hirearchy.eligibility import RunnableQuery
from hirearchy.kernel import ROOT


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


def test_waiting_on_user_is_a_waiting_of_the_package(org: Org) -> None:
    org.delegate(ROOT, "ceo", "Ship it", "Ship", "Shipped", budget=1)
    org.start_run_log("ceo")
    found = org.runtime.waiting_on_user.analyze()
    assert isinstance(found, Waiting) and found.text == 'waiting on you: "Ship it" needs budget (ceo out of runs)'


def test_waiting_on_user_asks_the_runnable_query_of_the_runtime(org: Org) -> None:
    org.delegate(ROOT, "ceo", "Ship it", "Ship", "Shipped", budget=1)
    org.start_run_log("ceo")
    assert org.runtime.waiting_on_user.analyze() is not None
    org.runtime = wiring.open_runtime(org.root, {RunnableQuery: Runnable("ceo")})
    assert org.runtime.waiting_on_user.analyze() is None


def test_nothing_to_do_asks_the_runnable_query_of_the_runtime(org: Org) -> None:
    assert org.runtime.open_work.nothing_to_do() is True
    org.runtime = wiring.open_runtime(org.root, {RunnableQuery: Runnable("ceo")})
    assert org.runtime.open_work.nothing_to_do() is False
