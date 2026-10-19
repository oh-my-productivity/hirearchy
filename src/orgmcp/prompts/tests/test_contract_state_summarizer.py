"""Contract of ``StateSummarizer``: the situation of an agent as bullet lines, over agents, mailboxes and settings on disk and in memory.

The text is the contract (it is the ``# Your state`` of every run prompt and the answer of ``whoami``): the lines, their order and their wording."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest

from orgmcp.kernel import OrgError
from orgmcp.prompts import StateSummarizer
from orgmcp.prompts.testing import IMPLEMENTATIONS, PromptsWorld

from ._support import implementations

pytestmark = pytest.mark.xfail(strict=True, reason="red: C-prompts")

ROOT_STATE = [
    "- Address: `root`; parent: `-`; role: human (root of the organization)",
    "- Direct reports: none",
    "- Open tasks assigned to you: none",
    "- Work you delegated that is still outstanding: none",
]
BODY = "## Goal\nWrite the plan.\n\n## Acceptance criteria\nplan.md exists"
QUOTED = ["    > ## Goal", "    > Write the plan.", "    >", "    > ## Acceptance criteria", "    > plan.md exists"]


@pytest.fixture(params=implementations(IMPLEMENTATIONS[StateSummarizer]))
def w(request: pytest.FixtureRequest, tmp_path: Path) -> PromptsWorld:
    made = cast(Callable[[Path], PromptsWorld], request.param)(tmp_path)
    assert isinstance(made.summary, StateSummarizer)
    return made


def state(w: PromptsWorld, addr: str, shown: set[str] | None = None) -> list[str]:
    return w.summary.state_summary(addr, shown).split("\n")


def manager(w: PromptsWorld, addr: str = "ceo", **meta: object) -> None:
    w.agent(addr, {"role": "Chief", "can_hire": True, "max_children": 2, **meta}, "Run it.")


def test_the_root_of_an_empty_organization_has_four_lines(w: PromptsWorld) -> None:
    assert state(w, "root") == ROOT_STATE


def test_an_agent_that_does_not_exist_is_refused(w: PromptsWorld) -> None:
    with pytest.raises(OrgError, match="no such agent: nobody"):
        w.summary.state_summary("nobody")


def test_a_manager_with_no_work(w: PromptsWorld) -> None:
    manager(w)
    w.budget("ceo", 5)
    assert state(w, "ceo") == [
        "- Address: `ceo`; parent: `root`; role: Chief",
        "- Budget: 5 run(s) left (this run already counted). Hiring: allowed (0/2 reports)",
        "- Tools beyond orgmcp: none",
        "- Direct reports: none",
        "- Open tasks assigned to you: none",
        "- Work you delegated that is still outstanding: none",
    ]


def test_an_agent_that_cannot_hire(w: PromptsWorld) -> None:
    w.agent("ceo", {"role": "Worker"}, "Work.")
    assert state(w, "ceo")[1] == "- Budget: 0 run(s) left (this run already counted). Hiring: not allowed"


def test_the_default_number_of_reports_is_five(w: PromptsWorld) -> None:
    w.agent("ceo", {"role": "Chief", "can_hire": True}, "Run it.")
    assert state(w, "ceo")[1].endswith("Hiring: allowed (0/5 reports)")


def test_the_tools_and_the_workspace_are_named(w: PromptsWorld) -> None:
    w.agent("dev", {"role": "Dev", "tools": ["read", "shell"], "workspace": str(w.root / "ws")}, "Code.")
    assert state(w, "dev")[2] == f"- Tools beyond orgmcp: read, shell; workspace: {w.root / 'ws'}"


def test_the_files_part_comes_after_the_tools_for_an_agent_with_a_workspace_and_not_for_one_without(w: PromptsWorld) -> None:
    w.agent("dev", {"role": "Dev", "tools": ["shell"], "workspace": str(w.root / "ws")}, "Code.")
    w.agent("plain", {"role": "Plain"}, "Plain.")
    lines = state(w, "dev")
    assert lines[3] == "- Files:" and lines[2].startswith("- Tools beyond orgmcp: shell")
    assert "- Files:" not in state(w, "plain")


def test_the_reports_are_listed_with_their_numbers_and_the_siblings_by_name(w: PromptsWorld) -> None:
    manager(w, max_children=3)
    w.agent("ceo/eng", {"role": "Engineer"}, "Build.")
    w.agent("ceo/qa", {"role": "QA"}, "Check.")
    w.states.words["ceo/eng"] = "running"
    w.budget("ceo/eng", 2)
    w.send("root", "ceo/eng", "note", "t", "b")
    assert state(w, "ceo")[3:6] == [
        "- Direct reports:",
        "  - ceo/eng [Engineer] running, budget 2, open tasks 0, delegated 0, unread 1",
        "  - ceo/qa [QA] idle, budget 0, open tasks 0, delegated 0, unread 0",
    ]
    assert "- Siblings: ceo/qa" in state(w, "ceo/eng") and not [line for line in state(w, "ceo") if line.startswith("- Siblings")]


def test_the_siblings_of_a_top_level_agent_are_the_other_top_level_agents(w: PromptsWorld) -> None:
    manager(w)
    w.agent("ops", {"role": "Ops"}, "Operate.")
    assert "- Siblings: ops" in state(w, "ceo") and "- Siblings: ceo" in state(w, "ops")


def test_an_open_task_is_quoted_verbatim_below_its_line(w: PromptsWorld) -> None:
    manager(w)
    task = w.send("root", "ceo", "task", "Plan", BODY)
    lines = state(w, "ceo")
    at = lines.index("- Open tasks assigned to you:")
    assert lines[at:at + 7] == ['- Open tasks assigned to you:', f'  - {task.id} "Plan" from root', *QUOTED]


def test_a_task_shown_in_the_new_messages_gets_a_pointer_instead_of_its_text(w: PromptsWorld) -> None:
    manager(w)
    task = w.send("root", "ceo", "task", "Plan", BODY)
    lines = state(w, "ceo", {task.id})
    at = lines.index("- Open tasks assigned to you:")
    assert lines[at + 1:at + 3] == [f'  - {task.id} "Plan" from root', "    (full text: see the new messages below)"]
    assert "Write the plan." not in "\n".join(lines)


def test_an_answered_task_is_no_longer_open(w: PromptsWorld) -> None:
    manager(w)
    task = w.send("root", "ceo", "task", "Plan", BODY)
    w.send("ceo", "root", "result", "Plan", "done", reply_to=task.id, status="done")
    assert "- Open tasks assigned to you: none" in state(w, "ceo")


def test_a_task_reported_blocked_is_listed_with_its_contract_until_it_is_answered_again(w: PromptsWorld) -> None:
    manager(w)
    task = w.send("root", "ceo", "task", "Plan", BODY)
    w.send("ceo", "root", "result", "Plan", "waiting", reply_to=task.id, status="blocked")
    lines = state(w, "ceo")
    at = lines.index("- Tasks you reported blocked (not final):")
    assert lines[at:at + 8] == [
        "- Tasks you reported blocked (not final):",
        f'  - {task.id} "Plan" from root: reported blocked; you may re-report it once the blocker is resolved', *QUOTED,
    ]
    assert lines[at - 1] == "- Open tasks assigned to you: none"


def test_a_blocked_task_shown_in_the_new_messages_gets_the_pointer(w: PromptsWorld) -> None:
    manager(w)
    task = w.send("root", "ceo", "task", "Plan", BODY)
    w.send("ceo", "root", "result", "Plan", "waiting", reply_to=task.id, status="blocked")
    text = w.summary.state_summary("ceo", {task.id})
    assert "Write the plan." not in text and text.count("    (full text: see the new messages below)") == 1


def test_a_delegation_still_outstanding_names_the_state_of_the_report(w: PromptsWorld) -> None:
    manager(w)
    w.agent("ceo/eng", {"role": "Engineer"}, "Build.")
    w.states.words["ceo/eng"] = "running"
    task = w.send("ceo", "ceo/eng", "task", "Build", "b")
    assert state(w, "ceo")[-2:] == ["- Work you delegated that is still outstanding:", f'  - {task.id} "Build" -> ceo/eng (running)']


def test_a_delegation_to_an_agent_that_is_gone_says_so(w: PromptsWorld) -> None:
    manager(w)
    task = w.send("ceo", "ceo/old", "task", "Build", "b")
    assert state(w, "ceo")[-1] == f'  - {task.id} "Build" -> ceo/old (gone)'


def test_root_lists_the_work_it_delegated(w: PromptsWorld) -> None:
    manager(w)
    w.states.words["ceo"] = "pending"
    task = w.send("root", "ceo", "task", "Plan", BODY)
    assert state(w, "root")[1:] == [
        "- Direct reports:",
        "  - ceo [Chief] pending, budget 0, open tasks 1, delegated 0, unread 1",
        "- Open tasks assigned to you: none",
        "- Work you delegated that is still outstanding:",
        f'  - {task.id} "Plan" -> ceo (pending)',
    ]
