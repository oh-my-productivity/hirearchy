"""``wire_budget``: the runtime has the three budget ports, built from the mailboxes, task views, run logs, agents, settings and delivery of the
runtime."""

from __future__ import annotations

from pathlib import Path

import pytest

from hirearchy.agents import AgentDirectory, CharterReader
from hirearchy.app import wiring
from hirearchy.budget import AllocationPolicy, BudgetQuery, BudgetReclaimer
from hirearchy.budget._policy import ReserveAllocationPolicy
from hirearchy.budget._query import DerivedBudgetQuery
from hirearchy.budget._reclaim import NoteBudgetReclaimer
from hirearchy.delivery import MessageDelivery
from hirearchy.delivery.testing import RecordingDelivery
from hirearchy.kernel import Message, OrgError
from hirearchy.kernel.testing import FakeClock, SequenceIdGenerator
from hirearchy.mail import MailboxReader, TaskQuery
from hirearchy.mail._tasks import DerivedTaskQuery
from hirearchy.mail.testing import MemoryMailbox
from hirearchy.runs import RunLogReader
from hirearchy.runs.testing import MemoryRuns
from hirearchy.settings import OrgSettings
from hirearchy.settings.testing import MemoryOrgSettings

CHARTER = "---\nrole: R\ncan_hire: true\n---\nx\n"


def test_the_runtime_has_the_three_budget_ports(tmp_path: Path) -> None:
    runtime = wiring.open_runtime(tmp_path)
    assert isinstance(runtime.budget_query, DerivedBudgetQuery) and isinstance(runtime.budget_query, BudgetQuery)
    assert isinstance(runtime.allocation_policy, ReserveAllocationPolicy) and isinstance(runtime.allocation_policy, AllocationPolicy)
    assert isinstance(runtime.budget_reclaimer, NoteBudgetReclaimer) and isinstance(runtime.budget_reclaimer, BudgetReclaimer)


def test_building_the_ports_does_no_io(tmp_path: Path) -> None:
    runtime = wiring.open_runtime(tmp_path)
    assert runtime.budget_query is not None and runtime.allocation_policy is not None and runtime.budget_reclaimer is not None
    assert list(tmp_path.iterdir()) == []


def test_every_collaborator_comes_from_the_runtime(tmp_path: Path) -> None:
    box = MemoryMailbox()
    box.agents.put("ceo/AGENT.md", CHARTER)
    box.agents.put("ceo/eng/AGENT.md", "---\nrole: R\n---\nx\n")
    runs = MemoryRuns(FakeClock(), tmp_path)
    runs.add_agent("ceo")
    runs.create("ceo")
    settings = MemoryOrgSettings("---\ndefault_budget: 3\n---\nrules\n")
    clock = FakeClock()
    delivery = RecordingDelivery(clock, SequenceIdGenerator(clock))
    overrides: dict[type, object] = {
        MailboxReader: box, TaskQuery: DerivedTaskQuery(box), RunLogReader: runs, AgentDirectory: box.agents,
        CharterReader: box.agents, OrgSettings: settings, MessageDelivery: delivery,
    }
    runtime = wiring.open_runtime(tmp_path, overrides)
    box.store(Message(sender="root", to="ceo", type="note", body="b", budget=5, id="20260101T000000000001-root-aaaa"))
    assert runtime.budget_query.budget("ceo") == 4  # 5 received - 1 run of the fake run logs
    assert runtime.budget_query.grant_hint("ceo").startswith("`ceo` now has 4 run(s)")
    assert runtime.allocation_policy.default_budget("ceo") == 3  # the default_budget of the fake settings
    box.store(Message(sender="ceo", to="ceo/eng", type="note", body="b", budget=1, id="20260101T000000000002-ceo-aaaa"))
    box.store(Message(sender="root", to="ceo/eng", type="note", body="b", budget=2, id="20260101T000000000003-root-aaaa"))
    box.begin("ceo/eng")
    box.end("ceo/eng", True)
    assert runtime.budget_reclaimer.reclaim("ceo", "eng").budget == 3 and [m.budget for m in delivery.messages] == [3]


def test_an_override_replaces_a_port(tmp_path: Path) -> None:
    class Nothing(BudgetQuery):
        def budget(self, addr: str) -> int | None:
            return 41

        def delegable(self, addr: str) -> tuple[int, int, int]:
            return 41, 0, 40

        def grant_hint(self, addr: str) -> str:
            return ""

    fake = Nothing()
    runtime = wiring.open_runtime(tmp_path, {BudgetQuery: fake})
    assert runtime.budget_query is fake
    with pytest.raises(OrgError, match="you have 41 run"):  # the policy is built over the fake
        runtime.allocation_policy.check_allocation("ceo", 41, True)


def test_every_runtime_has_its_own_ports(tmp_path: Path) -> None:
    assert wiring.open_runtime(tmp_path).budget_query is not wiring.open_runtime(tmp_path).budget_query
