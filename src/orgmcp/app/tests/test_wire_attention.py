"""``wire_attention``: the runtime has the three ports of ``attention``, built from the ports of the runtime; and the objects the legacy functions use follow
the runtime in force (one the dashboard's lenient ``Org`` or a test replaced a part of)."""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from orgmcp.agents import AgentDirectory
from orgmcp.app import Org, wire_attention, wiring
from orgmcp.attention import HumanQueue, OpenWork, Waiting, WaitingOnUser
from orgmcp.attention._queue import InboxHumanQueue
from orgmcp.attention._waiting import RootTaskWaitingOnUser
from orgmcp.attention._work import RunnableOpenWork
from orgmcp.budget import BudgetQuery
from orgmcp.budget.testing import FixedBudget
from orgmcp.dashboard_data import LenientOrg
from orgmcp.eligibility import PauseStore, RunnableQuery
from orgmcp.eligibility.testing import MemoryPauseStore, runnable_over
from orgmcp.kernel import ROOT, RUNTIME, Message
from orgmcp.kernel.testing import ListEventSink
from orgmcp.mail import MailboxReader, TaskQuery
from orgmcp.mail._tasks import DerivedTaskQuery
from orgmcp.mail.testing import MemoryMailbox
from orgmcp.stalls import NudgeLedger
from orgmcp.stalls.testing import MemoryNudges

CHARTER = "---\nrole: R\n---\nx\n"


def test_the_runtime_has_the_three_ports(tmp_path: Path) -> None:
    runtime = wiring.open_runtime(tmp_path)
    assert isinstance(runtime.waiting_on_user, RootTaskWaitingOnUser) and isinstance(runtime.waiting_on_user, WaitingOnUser)
    assert isinstance(runtime.human_queue, InboxHumanQueue) and isinstance(runtime.human_queue, HumanQueue)
    assert isinstance(runtime.open_work, RunnableOpenWork) and isinstance(runtime.open_work, OpenWork)


def test_building_the_ports_does_no_io(tmp_path: Path) -> None:
    runtime = wiring.open_runtime(tmp_path)
    assert runtime.waiting_on_user is not None and runtime.human_queue is not None and runtime.open_work is not None
    assert list(tmp_path.iterdir()) == []


def test_an_override_replaces_a_port(tmp_path: Path) -> None:
    class Idle(OpenWork):
        def nothing_to_do(self) -> bool:
            return True

    fake = Idle()
    runtime = wiring.open_runtime(tmp_path, {OpenWork: fake})
    assert runtime.open_work is fake and isinstance(runtime.human_queue, InboxHumanQueue)


def test_every_runtime_has_its_own_ports(tmp_path: Path) -> None:
    assert wiring.open_runtime(tmp_path).human_queue is not wiring.open_runtime(tmp_path).human_queue


def test_every_collaborator_of_the_decision_comes_from_the_runtime(tmp_path: Path) -> None:
    """The whole decision over fakes: nothing of the organization directory is read or written."""
    box, events = MemoryMailbox(), ListEventSink()
    box.agents.put("ceo/AGENT.md", CHARTER)
    tasks, pauses = DerivedTaskQuery(box), MemoryPauseStore(events)
    budgets = FixedBudget(tasks, box.agents, box.agents)
    task = Message(sender=ROOT, to="ceo", type="task", title="T", body="g", id="20261018T100000000001-root-aaaa", budget=1)
    box.store(task)
    runtime = wiring.open_runtime(tmp_path, {
        AgentDirectory: box.agents, MailboxReader: box, TaskQuery: tasks, PauseStore: pauses, BudgetQuery: budgets,
        RunnableQuery: runnable_over(box.agents, box, pauses, budgets), NudgeLedger: MemoryNudges(box.agents),
    })
    assert runtime.waiting_on_user.analyze() is not None  # root waits for ceo, which has no runs
    assert runtime.waiting_on_user.analyze() == Waiting(
        'waiting on you: "T" needs budget (ceo out of runs)',
        'Your options: grant runs with send(to="ceo", body="<why>", budget=N), then call start(); or accept what exists so far '
        "(the task stays open: tell the user, and stop() the scheduler).",
    )
    assert runtime.open_work.nothing_to_do() is False
    box.store(Message(sender=RUNTIME, to=ROOT, type="note", title="Q", body="really?", id="20261018T100000000002-runtime-aaaa"))
    assert [line for _, line in runtime.human_queue.items()] == ['Needs you: runtime notice "Q": really? (message 20261018T100000000002-runtime-aaaa)']
    assert list(tmp_path.iterdir()) == []


# ------------------------------------------------------------------------------ the objects of the legacy functions


@pytest.fixture
def org(tmp_path: Path) -> Org:
    made = Org.init(tmp_path / "org", "mission")
    made.hire("root", "ceo", "Chief", "Run it.")
    return made


def test_the_legacy_objects_are_the_classes_of_the_package(org: Org) -> None:
    assert isinstance(wire_attention.waiting_on_user_of(org.runtime), RootTaskWaitingOnUser)
    assert isinstance(wire_attention.human_queue_of(org.runtime), InboxHumanQueue)
    assert isinstance(wire_attention.open_work_of(org.runtime), RunnableOpenWork)


def test_the_legacy_queue_reads_the_mailboxes_of_the_runtime_in_force(org: Org) -> None:
    org.send("ceo", ROOT, "kept apart", title="hello")
    other = MemoryMailbox()
    other.store(Message(sender="ceo", to=ROOT, type="note", title="Elsewhere", body="in memory", id="20261018T100000000001-ceo-aaaa"))
    org.runtime = dataclasses.replace(org.runtime, mailbox=other)
    assert [line for _, line in wire_attention.human_queue_of(org.runtime).items()] == [
        'Needs you: note from ceo "Elsewhere": in memory (message 20261018T100000000001-ceo-aaaa)'
    ]


def test_the_legacy_queue_of_a_lenient_org_skips_what_it_cannot_read(org: Org) -> None:
    good = org.send("ceo", ROOT, "I need 2 more runs", title="Budget request")
    (org.root / "inbox" / "20260101T000000000000-ceo-bad0.md").write_text("---\nfrom: [oops\n---\nx\n", encoding="utf-8")
    lenient = LenientOrg(org.root)
    assert [mid for mid, _ in wire_attention.human_queue_of(lenient.runtime).items()] == [good.id]
