"""``HeldTasks`` and ``OutstandingDelegations``: the task lines of a state summary."""

from __future__ import annotations

import pytest

from pathlib import Path

from orgmcp.agents.testing import MemoryAgents
from orgmcp.kernel import Message
from orgmcp.prompts._ports import DelegationLines, HeldTaskLines
from orgmcp.prompts._tasks import HeldTasks, OutstandingDelegations
from orgmcp.prompts.testing import FixedQuote, FixedStates

from ._support import memory_box

pytestmark = pytest.mark.xfail(strict=True, reason="red: C-prompts")


def at(n: int, sender: str) -> str:
    return f"20260101T0000000000{n:02d}-{sender}-aaaa"


class Desk:
    def __init__(self, tmp_path: Path) -> None:
        self.box, self.tasks = memory_box(tmp_path)
        self.quote = FixedQuote()
        self.held: HeldTaskLines = HeldTasks(self.tasks, self.quote)

    def task(self, n: int, sender: str, to: str, title: str) -> Message:
        msg = Message(sender=sender, to=to, type="task", title=title, body="b", id=at(n, sender))
        self.box.store(msg)
        return msg

    def result(self, n: int, task: Message, status: str) -> Message:
        msg = Message(sender=task.to, to=task.sender, type="result", title="r", body="b", id=at(n, task.to), reply_to=task.id, status=status)
        self.box.store(msg)
        return msg


# ---------------------------------------------------------------------------------------------------------------------- HeldTasks


def test_no_task_no_line(tmp_path: Path) -> None:
    assert Desk(tmp_path).held.lines("ceo", set()) == []


def test_an_open_task_has_a_line_and_its_quote_indented_by_four(tmp_path: Path) -> None:
    d = Desk(tmp_path)
    t = d.task(1, "root", "ceo", "Plan")
    assert d.held.lines("ceo", set()) == [f'  - {t.id} "Plan" from root', "    QUOTE"]
    assert d.quote.asked == [t]


def test_a_task_in_the_new_messages_has_a_pointer_and_is_not_quoted(tmp_path: Path) -> None:
    d = Desk(tmp_path)
    t = d.task(1, "root", "ceo", "Plan")
    assert d.held.lines("ceo", {t.id}) == [f'  - {t.id} "Plan" from root', "    (full text: see the new messages below)"]
    assert d.quote.asked == []


def test_the_open_tasks_come_in_the_order_of_the_query(tmp_path: Path) -> None:
    d = Desk(tmp_path)
    a, b = d.task(1, "root", "ceo", "A"), d.task(2, "root", "ceo", "B")
    assert [line for line in d.held.lines("ceo", set()) if line.startswith("  - ")] == [f'  - {a.id} "A" from root', f'  - {b.id} "B" from root']


def test_a_task_reported_blocked_follows_under_its_own_heading(tmp_path: Path) -> None:
    d = Desk(tmp_path)
    open_ = d.task(1, "root", "ceo", "Open")
    blocked = d.task(2, "root", "ceo", "Stuck")
    d.result(3, blocked, "blocked")
    assert d.held.lines("ceo", set()) == [
        f'  - {open_.id} "Open" from root', "    QUOTE",
        "- Tasks you reported blocked (not final):",
        f'  - {blocked.id} "Stuck" from root: reported blocked; you may re-report it once the blocker is resolved', "    QUOTE",
    ]


def test_a_blocked_task_in_the_new_messages_has_the_pointer(tmp_path: Path) -> None:
    d = Desk(tmp_path)
    blocked = d.task(1, "root", "ceo", "Stuck")
    d.result(2, blocked, "blocked")
    assert d.held.lines("ceo", {blocked.id})[-1] == "    (full text: see the new messages below)"
    assert d.quote.asked == []


def test_a_task_reported_done_is_not_held(tmp_path: Path) -> None:
    d = Desk(tmp_path)
    d.result(2, d.task(1, "root", "ceo", "Done"), "done")
    assert d.held.lines("ceo", set()) == []


# ------------------------------------------------------------------------------------------------------------ OutstandingDelegations


def delegations(d: Desk, agents: MemoryAgents, states: FixedStates) -> DelegationLines:
    return OutstandingDelegations(d.tasks, agents, states)


def test_a_delegation_names_the_state_of_its_report_or_says_it_is_gone(tmp_path: Path) -> None:
    d, states = Desk(tmp_path), FixedStates()
    d.box.agents.put("ceo/eng/AGENT.md", "---\nrole: E\n---\nx\n")
    states.words["ceo/eng"] = "running"
    a, b = d.task(1, "ceo", "ceo/eng", "Build"), d.task(2, "ceo", "ceo/old", "Gone")
    assert delegations(d, d.box.agents, states).lines("ceo") == [
        f'  - {a.id} "Build" -> ceo/eng (running)', f'  - {b.id} "Gone" -> ceo/old (gone)',
    ]


def test_a_delegation_that_was_answered_is_not_outstanding(tmp_path: Path) -> None:
    d = Desk(tmp_path)
    d.result(2, d.task(1, "ceo", "ceo/eng", "Build"), "done")
    assert delegations(d, d.box.agents, FixedStates()).lines("ceo") == []
