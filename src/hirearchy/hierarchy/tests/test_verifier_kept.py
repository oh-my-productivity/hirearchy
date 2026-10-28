"""VERIFIER-KEPT (design 6.6; owner question Q11): an agent cannot retire a direct report that checks its team's work.

The key is the stored ``kind: verifier`` of the report's charter (an agent from before Phase 2 has none and is not held to it, so existing organizations keep
working); only an agent is held to it: root retires a verifier like any agent (over MCP root's retire is refused in favour of the plan, and the extension's
``retire`` carries the user's approval). Runs over both implementations."""

from __future__ import annotations

from pathlib import Path

import pytest

from hirearchy.hierarchy import Retirement
from hirearchy.hierarchy.testing import IMPLEMENTATIONS, HierarchyWorld
from hirearchy.kernel import OrgError

from ._support import BOSS, make

CHECKER = "ceo/checker"


@pytest.fixture(params=IMPLEMENTATIONS[Retirement], ids=lambda factory: factory.__name__)
def w(request: pytest.FixtureRequest, tmp_path: Path) -> HierarchyWorld:
    made = make(request, tmp_path)
    assert isinstance(made.retirement, Retirement)
    return made


def refusal(w: HierarchyWorld, actor: str, name: str) -> str:
    with pytest.raises(OrgError) as caught:
        w.retirement.retire_team(actor, name, "restructure")
    return str(caught.value)


def test_an_agents_retire_of_a_kind_verifier_report_is_refused_word_for_word(w: HierarchyWorld) -> None:
    w.agent(CHECKER, {"role": "Fact checker", "kind": "verifier"})
    expected = (
        "refused: ceo/checker checks your team's work (Fact checker); removing a check is the user's decision (the retro brief shows them the team). "
        "Nothing was retired."
    )
    assert refusal(w, "ceo", "checker") == expected
    assert refusal(w, "ceo", CHECKER) == expected  # (by its address too)
    assert w.agents.exists(CHECKER) and w.events.events == []  # nothing was retired, nothing was announced


def test_a_verifier_without_a_stored_kind_may_be_retired(w: HierarchyWorld) -> None:
    """GREEN when written (L4): an agent from before Phase 2 has no ``kind``, so existing organizations keep working."""
    w.agent(CHECKER, {"role": "Fact checker"})
    assert w.retirement.retire_team("ceo", "checker", "restructure").addr == CHECKER
    assert not w.agents.exists(CHECKER)


def test_an_agent_may_retire_a_report_of_another_kind(w: HierarchyWorld) -> None:
    """GREEN when written: a worker, a lead or an agent of another kind is retired as before."""
    w.agent("ceo/writer", {"role": "Writer", "kind": "worker"})
    w.agent("ceo/lead", {**BOSS, "kind": "lead"})
    assert w.retirement.retire_team("ceo", "writer", "done").addr == "ceo/writer"
    assert w.retirement.retire_team("ceo", "lead", "done").addr == "ceo/lead"


def test_root_may_retire_a_verifier(w: HierarchyWorld) -> None:
    """GREEN when written: the bound is on an agent's retire, not on the user's (the plan's ``retire`` is the user's decision)."""
    w.agent("lead", {"role": "Lead", "kind": "verifier"})
    assert w.retirement.retire_team("root", "lead", "the user decided").addr == "lead"


def test_a_verifier_deeper_in_the_team_is_kept_with_its_parent(w: HierarchyWorld) -> None:
    """GREEN when written: only a direct report is judged; retiring its parent retires it with the team (the parent's own kind decides)."""
    w.agent("ceo/mgr", BOSS)
    w.agent("ceo/mgr/checker", {"role": "Fact checker", "kind": "verifier"})
    assert w.retirement.retire_team("ceo", "mgr", "restructure").addr == "ceo/mgr"
    assert not w.agents.exists("ceo/mgr/checker")
