"""``wire_budget``: the runtime has the three budget ports, built from the mailboxes, task views, run logs, agents, settings and delivery of the
runtime; and the dashboard's lenient variant reads the same ports through the decorated mailboxes and its own run count."""

from __future__ import annotations

from pathlib import Path

import pytest

from orgmcp.agents import AgentDirectory, CharterReader
from orgmcp.app import Org, wire_budget, wiring
from orgmcp.budget import AllocationPolicy, BudgetQuery, BudgetReclaimer
from orgmcp.budget._policy import ReserveAllocationPolicy
from orgmcp.budget._query import DerivedBudgetQuery
from orgmcp.budget._reclaim import NoteBudgetReclaimer
from ._lenient_org import LenientOrg
from orgmcp.delivery import MessageDelivery
from orgmcp.delivery.testing import RecordingDelivery
from orgmcp.kernel import Message, OrgError
from orgmcp.kernel.testing import FakeClock, SequenceIdGenerator
from orgmcp.mail import MailboxReader, TaskQuery
from orgmcp.mail._tasks import DerivedTaskQuery
from orgmcp.mail.testing import MemoryMailbox
from orgmcp.runs import RunLogReader
from orgmcp.runs.testing import MemoryRuns
from orgmcp.settings import OrgSettings
from orgmcp.settings.testing import MemoryOrgSettings

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


# ------------------------------------------------------------------------------------------------------------------ lenient


def test_the_lenient_runtime_counts_runs_with_the_function_it_is_given_and_reads_the_boxes_of_the_runtime(tmp_path: Path) -> None:
    org = Org.init(tmp_path / "org", "mission")
    org.hire("root", "ceo", "Boss", "text")
    org.send("root", "ceo", "runs", budget=6)
    asked: list[str] = []

    def counted(addr: str) -> int:
        asked.append(addr)
        return 2

    runtime = wire_budget.lenient(org.runtime, counted)
    assert runtime.budget_query.budget("ceo") == 4 and asked == ["ceo"]
    assert isinstance(runtime.allocation_policy, ReserveAllocationPolicy) and isinstance(runtime.budget_reclaimer, NoteBudgetReclaimer)
    assert runtime.allocation_policy.default_budget("ceo") == 3  # 4 left - (0 outstanding + 1), under the default of 10


def test_the_lenient_org_skips_a_message_it_cannot_read_when_it_adds_up_a_budget(tmp_path: Path) -> None:
    org = Org.init(tmp_path / "org", "mission")
    org.hire("root", "ceo", "Boss", "text")
    org.send("root", "ceo", "runs", budget=6)
    (org.root / "ceo" / "inbox" / "20260101T000000000000-root-bad0.md").write_text("---\nfrom: [oops\n---\nx\n", encoding="utf-8")
    with pytest.raises(Exception):  # noqa: B017, PT011 - the plain Org raises on it (yaml error), as it always did
        org.budget("ceo")
    lenient = LenientOrg(org.root)
    assert lenient.budget("ceo") == 6 and lenient.delegable("ceo") == (6, 0, 5)
    assert "ceo/inbox/20260101T000000000000-root-bad0.md" in lenient.bad


def test_the_lenient_org_uses_its_cached_run_count(tmp_path: Path) -> None:
    org = Org.init(tmp_path / "org", "mission")
    org.hire("root", "ceo", "Boss", "text")
    org.send("root", "ceo", "runs", budget=6)
    lenient = LenientOrg(org.root)
    calls: list[str] = []
    real = lenient.runs_used

    def spy(addr: str) -> int:
        calls.append(addr)
        return real(addr)

    lenient.runtime = wire_budget.lenient(lenient.runtime, spy)
    assert lenient.budget("ceo") == 6 and calls == ["ceo"]
