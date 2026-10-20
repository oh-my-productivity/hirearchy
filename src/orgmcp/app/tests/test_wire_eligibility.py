"""``wire_eligibility``: the runtime has the four eligibility ports, built from the flag files, the ledger, the mailboxes, the agents and the budgets
of the runtime."""

from __future__ import annotations

import os
from pathlib import Path

from orgmcp.agents import AgentDirectory
from orgmcp.app import wiring
from orgmcp.budget import BudgetQuery
from orgmcp.budget.testing import FixedBudget
from orgmcp.eligibility import AgentStates, FailureCounter, PauseStore, RunnableQuery
from orgmcp.eligibility._failures import LedgerFailureCounter
from orgmcp.eligibility._pause import FsPauseStore
from orgmcp.eligibility._runnable import DerivedRunnableQuery
from orgmcp.eligibility._states import DerivedAgentStates
from orgmcp.eligibility.testing import MemoryFailureCounter, MemoryPauseStore
from orgmcp.kernel import RUNTIME, EventSink, LedgerStore, Message
from orgmcp.kernel.testing import ListEventSink, MemoryLedgerStore
from orgmcp.mail import MailboxReader
from orgmcp.mail._tasks import DerivedTaskQuery
from orgmcp.mail.testing import MemoryMailbox

CHARTER = "---\nrole: R\n---\nx\n"


def test_the_runtime_has_the_four_eligibility_ports(tmp_path: Path) -> None:
    runtime = wiring.open_runtime(tmp_path)
    assert isinstance(runtime.pause_store, FsPauseStore) and isinstance(runtime.pause_store, PauseStore)
    assert isinstance(runtime.failure_counter, LedgerFailureCounter) and isinstance(runtime.failure_counter, FailureCounter)
    assert isinstance(runtime.agent_states, DerivedAgentStates) and isinstance(runtime.agent_states, AgentStates)
    assert isinstance(runtime.runnable_query, DerivedRunnableQuery) and isinstance(runtime.runnable_query, RunnableQuery)


def test_building_the_ports_does_no_io(tmp_path: Path) -> None:
    runtime = wiring.open_runtime(tmp_path)
    assert runtime.pause_store is not None and runtime.failure_counter is not None
    assert runtime.agent_states is not None and runtime.runnable_query is not None
    assert list(tmp_path.iterdir()) == []


def test_every_collaborator_comes_from_the_runtime(tmp_path: Path) -> None:
    box = MemoryMailbox()
    box.agents.put("ceo/AGENT.md", CHARTER)
    events = ListEventSink()
    budgets = FixedBudget(DerivedTaskQuery(box), box.agents, box.agents)
    budgets.held["ceo"] = 2
    ledgers = MemoryLedgerStore()
    overrides: dict[type, object] = {
        MailboxReader: box, AgentDirectory: box.agents, BudgetQuery: budgets, EventSink: events, LedgerStore: ledgers,
    }
    runtime = wiring.open_runtime(tmp_path, overrides)
    box.store(Message(sender=RUNTIME, to="ceo", type="note", body="b", id="20260101T000000000001-runtime-aaaa"))
    assert runtime.agent_states.state("ceo") == "pending" and runtime.runnable_query.runnable() == ["ceo"]
    assert runtime.failure_counter.record("ceo") == 1 and list(ledgers.texts) == ["failures"]
    os.makedirs(tmp_path / "ceo")  # the flag file is on disk: the pause store is the real one over the directory of the runtime
    runtime.pause_store.pause("ceo", "failures", by="runtime")
    assert events.events[0].kind == "agent.pause" and runtime.agent_states.state("ceo") == "paused(failures)"
    assert runtime.runnable_query.runnable() == []


def test_an_override_replaces_a_port(tmp_path: Path) -> None:
    fake = MemoryPauseStore(ListEventSink())
    runtime = wiring.open_runtime(tmp_path, {PauseStore: fake})
    fake.pause("ceo", "budget")
    assert runtime.pause_store is fake and runtime.agent_states.state("ceo") == "paused(budget)"  # the states are built over the fake
    counter = MemoryFailureCounter()
    assert wiring.open_runtime(tmp_path, {FailureCounter: counter}).failure_counter is counter


def test_every_runtime_has_its_own_ports(tmp_path: Path) -> None:
    assert wiring.open_runtime(tmp_path).pause_store is not wiring.open_runtime(tmp_path).pause_store
