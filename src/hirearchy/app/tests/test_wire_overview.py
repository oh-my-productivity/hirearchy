"""``wire_overview``: the runtime has the tree, built from the agents, charters, mailboxes, tasks, budgets, states and services of the runtime."""

from __future__ import annotations

from pathlib import Path

from hirearchy.agents import AgentDirectory, CharterReader
from hirearchy.app import wiring
from hirearchy.budget import BudgetQuery
from hirearchy.budget.testing import FixedBudget
from hirearchy.eligibility import AgentStates
from hirearchy.mail import MailboxReader, TaskQuery
from hirearchy.mail._tasks import DerivedTaskQuery
from hirearchy.mail.testing import MemoryMailbox
from hirearchy.overview import OrgTree
from hirearchy.overview._tree import TextOrgTree
from hirearchy.overview.testing import FixedOrgTree, FixedStates
from hirearchy.services import ServiceCatalog
from hirearchy.services.testing import memory_world


def test_the_runtime_has_the_tree(tmp_path: Path) -> None:
    runtime = wiring.open_runtime(tmp_path)
    assert isinstance(runtime.org_tree, TextOrgTree) and isinstance(runtime.org_tree, OrgTree)


def test_building_the_port_does_no_io(tmp_path: Path) -> None:
    runtime = wiring.open_runtime(tmp_path)
    assert runtime.org_tree is not None
    assert list(tmp_path.iterdir()) == []


def test_an_override_replaces_the_port(tmp_path: Path) -> None:
    fake = FixedOrgTree("x")
    assert wiring.open_runtime(tmp_path, {OrgTree: fake}).org_tree is fake


def test_every_collaborator_of_the_tree_comes_from_the_runtime(tmp_path: Path) -> None:
    """The whole tree over fakes: nothing of the organization directory is read or written."""
    box, states = MemoryMailbox(), FixedStates()
    box.agents.put("ceo/AGENT.md", "---\nrole: Chief\n---\nx\n")
    tasks = DerivedTaskQuery(box)
    budgets = FixedBudget(tasks, box.agents, box.agents)
    budgets.held["ceo"] = 7
    states.words["ceo"] = "running"
    runtime = wiring.open_runtime(tmp_path, {
        AgentDirectory: box.agents, CharterReader: box.agents, MailboxReader: box, TaskQuery: tasks, BudgetQuery: budgets, AgentStates: states,
        ServiceCatalog: memory_world(tmp_path).catalog,
    })
    assert runtime.org_tree.tree() == "\n".join([
        "root (human): unread 0, delegated 0",
        "  ceo [Chief] running  budget=7 open=0 delegated=0 unread=0",
    ])
    assert list(tmp_path.iterdir()) == []

