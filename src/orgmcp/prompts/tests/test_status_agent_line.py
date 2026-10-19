"""``StatusAgentLine``: where an agent stands on one line - role, state, budget, tasks and mail."""

from __future__ import annotations

import pytest

from pathlib import Path

from orgmcp.budget.testing import FixedBudget
from orgmcp.kernel import Message
from orgmcp.prompts._agent_line import StatusAgentLine
from orgmcp.prompts._ports import AgentLines
from orgmcp.prompts.testing import FixedStates

from ._support import memory_box

pytestmark = pytest.mark.xfail(strict=True, reason="red: C-prompts")


def message(sender: str, to: str, kind: str, n: int, wake: bool = True) -> Message:
    return Message(sender=sender, to=to, type=kind, title="t", body="b", id=f"20260101T0000000000{n:02d}-{sender}-aaaa", wake=wake)


def test_the_line_names_the_agent_its_role_its_state_and_its_numbers(tmp_path: Path) -> None:
    (box, tasks), states = memory_box(tmp_path), FixedStates()
    box.agents.put("ceo/AGENT.md", "---\nrole: Chief\n---\nx\n")
    budgets = FixedBudget(tasks, box.agents, box.agents)
    budgets.held["ceo"] = 7
    states.words["ceo"] = "running"
    box.store(message("root", "ceo", "task", 1))
    box.store(message("root", "ceo", "note", 2))
    box.store(message("root", "ceo", "note", 3, wake=False))
    box.store(message("ceo", "ceo/eng", "task", 4))
    line: AgentLines = StatusAgentLine(box.agents, states, budgets, tasks, box)
    assert line.agent_line("ceo") == "ceo [Chief] running, budget 7, open tasks 1, delegated 1, unread 2"


def test_a_charter_with_no_role_is_a_question_mark_and_a_stranger_is_idle_with_nothing(tmp_path: Path) -> None:
    box, tasks = memory_box(tmp_path)
    box.agents.put("x/AGENT.md", "---\ncan_hire: false\n---\nx\n")
    line = StatusAgentLine(box.agents, FixedStates(), FixedBudget(tasks, box.agents, box.agents), tasks, box)
    assert line.agent_line("x") == "x [?] idle, budget 0, open tasks 0, delegated 0, unread 0"


def test_root_has_no_budget_limit(tmp_path: Path) -> None:
    box, tasks = memory_box(tmp_path)
    line = StatusAgentLine(box.agents, FixedStates(), FixedBudget(tasks, box.agents, box.agents), tasks, box)
    assert line.agent_line("root") == "root [human (root of the organization)] idle, budget None, open tasks 0, delegated 0, unread 0"
