"""``TextStateSummarizer``: the order of the parts of a state summary and where each part comes from (the roles are fakes here)."""

from __future__ import annotations

from pathlib import Path

import pytest

from orgmcp.budget.testing import FixedBudget
from orgmcp.kernel import OrgError
from orgmcp.prompts._state import TextStateSummarizer
from orgmcp.prompts.testing import FixedAgentLines, FixedDelegations, FixedFiles, FixedHeld

from ._support import memory_box

pytestmark = pytest.mark.xfail(strict=True, reason="red: C-prompts")


class Parts:
    def __init__(self, tmp_path: Path) -> None:
        box, tasks = memory_box(tmp_path)
        self.agents = box.agents
        self.budgets = FixedBudget(tasks, self.agents, self.agents)
        self.files, self.agent_line = FixedFiles(["- Files:", "  - F"]), FixedAgentLines()
        self.held, self.delegations = FixedHeld(["  - T1", "    quoted"]), FixedDelegations(["  - D1"])
        self.summary = TextStateSummarizer(self.agents, self.agents, self.budgets, self.files, self.agent_line, self.held, self.delegations)

    def agent(self, addr: str, text: str) -> None:
        self.agents.put(f"{addr}/AGENT.md", text)


def test_the_lines_of_an_agent_in_order(tmp_path: Path) -> None:
    p = Parts(tmp_path)
    p.agent("ceo", "---\nrole: Chief\ncan_hire: true\nmax_children: 3\ntools: [read]\nworkspace: /ws\n---\nx\n")
    p.agent("ceo/eng", "---\nrole: E\n---\nx\n")
    p.agent("ceo/qa", "---\nrole: Q\n---\nx\n")
    p.agent("ops", "---\nrole: O\n---\nx\n")
    p.budgets.held["ceo"] = 9
    assert p.summary.state_summary("ceo").split("\n") == [
        "- Address: `ceo`; parent: `root`; role: Chief",
        "- Budget: 9 run(s) left (this run already counted). Hiring: allowed (2/3 reports)",
        "- Tools beyond orgmcp: read; workspace: /ws",
        "- Files:", "  - F",
        "- Direct reports:", "  - AGENT-LINE ceo/eng", "  - AGENT-LINE ceo/qa",
        "- Siblings: ops",
        "- Open tasks assigned to you:", "  - T1", "    quoted",
        "- Work you delegated that is still outstanding:", "  - D1",
    ]


def test_the_files_roles_get_the_agent_and_its_charter_meta(tmp_path: Path) -> None:
    p = Parts(tmp_path)
    p.agent("ceo", "---\nrole: Chief\ntools: [shell]\n---\nx\n")
    p.summary.state_summary("ceo")
    assert p.files.asked == [("ceo", {"role": "Chief", "tools": ["shell"]})]


def test_the_shown_ids_reach_the_held_tasks_and_none_means_an_empty_set(tmp_path: Path) -> None:
    p = Parts(tmp_path)
    p.agent("ceo", "---\nrole: Chief\n---\nx\n")
    p.summary.state_summary("ceo", {"a", "b"})
    p.summary.state_summary("ceo")
    assert p.held.asked == [("ceo", {"a", "b"}), ("ceo", frozenset())]


def test_an_agent_with_no_tasks_says_none(tmp_path: Path) -> None:
    p = Parts(tmp_path)
    p.agent("ceo", "---\nrole: Chief\n---\nx\n")
    p.held.found, p.delegations.found = [], []
    lines = p.summary.state_summary("ceo").split("\n")
    assert lines[-2:] == ["- Open tasks assigned to you: none", "- Work you delegated that is still outstanding: none"]


def test_blocked_tasks_follow_the_open_ones_in_the_same_block(tmp_path: Path) -> None:
    p = Parts(tmp_path)
    p.agent("ceo", "---\nrole: Chief\n---\nx\n")
    p.held.found = ["  - T1", "- Tasks you reported blocked (not final):", "  - T2"]
    assert p.summary.state_summary("ceo").split("\n")[-4:-1] == p.held.found


def test_root_has_no_budget_hiring_tools_or_files_and_no_siblings(tmp_path: Path) -> None:
    p = Parts(tmp_path)
    p.agent("ceo", "---\nrole: Chief\n---\nx\n")
    lines = p.summary.state_summary("root").split("\n")
    assert lines[:2] == ["- Address: `root`; parent: `-`; role: human (root of the organization)", "- Direct reports:"]
    assert p.files.asked == [] and not [line for line in lines if line.startswith("- Siblings")]


def test_an_unknown_agent_is_refused_before_any_role_is_asked(tmp_path: Path) -> None:
    p = Parts(tmp_path)
    with pytest.raises(OrgError, match="no such agent: nobody"):
        p.summary.state_summary("nobody")
    assert p.held.asked == [] and p.files.asked == []
