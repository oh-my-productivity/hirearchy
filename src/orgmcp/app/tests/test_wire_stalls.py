"""``wire_stalls``: the runtime has the ladder and the nudge ledger, built from the ports of the runtime; and the ladder of the legacy scheduler follows
the runtime in force, with its clock, and keeps its memo of the task views."""

from __future__ import annotations

import dataclasses
import time
from pathlib import Path

import pytest

from orgmcp.agents import AgentDirectory
from orgmcp.app import Org, wire_stalls, wiring
from orgmcp.delivery import MessageDelivery
from orgmcp.delivery.testing import RecordingDelivery
from orgmcp.eligibility import PauseStore
from orgmcp.eligibility.testing import MemoryPauseStore
from orgmcp.kernel import Clock, EventSink, LedgerStore, Message
from orgmcp.kernel.testing import FakeClock, ListEventSink, MemoryLedgerStore, SequenceIdGenerator
from orgmcp.mail import MailboxReader, MailFingerprint, MessageParser, TaskQuery
from orgmcp.mail._tasks import DerivedTaskQuery
from orgmcp.mail.testing import CountingMessageParser, MemoryMailbox
from orgmcp.runs import RunLogReader
from orgmcp.runs.testing import MemoryRuns
from orgmcp.settings import OrgSettings
from orgmcp.settings.testing import MemoryOrgSettings
from orgmcp.stalls import NudgeLedger, StallLadder
from orgmcp.stalls._ladder import EscalationStallLadder
from orgmcp.stalls._nudges import LedgerNudgeLedger
from orgmcp.templates import Notices
from orgmcp.templates.testing import RecordingNotices


def test_the_runtime_has_the_ladder_and_the_nudge_ledger(tmp_path: Path) -> None:
    runtime = wiring.open_runtime(tmp_path)
    assert isinstance(runtime.stall_ladder, EscalationStallLadder) and isinstance(runtime.stall_ladder, StallLadder)
    assert isinstance(runtime.nudge_ledger, LedgerNudgeLedger) and isinstance(runtime.nudge_ledger, NudgeLedger)


def test_building_the_ports_does_no_io(tmp_path: Path) -> None:
    runtime = wiring.open_runtime(tmp_path)
    assert runtime.stall_ladder is not None and runtime.nudge_ledger is not None
    assert list(tmp_path.iterdir()) == []


def test_an_override_replaces_the_port(tmp_path: Path) -> None:
    class Never(StallLadder):
        def check(self) -> list[str]:
            return ["never"]

    fake = Never()
    runtime = wiring.open_runtime(tmp_path, {StallLadder: fake})
    assert runtime.stall_ladder is fake and isinstance(runtime.nudge_ledger, LedgerNudgeLedger)


def test_every_collaborator_of_the_ladder_comes_from_the_runtime(tmp_path: Path) -> None:
    """The whole ladder over fakes: nothing of the organization directory is read or written."""
    clock, box, events = FakeClock(), MemoryMailbox(), ListEventSink()
    box.agents.put("ceo/AGENT.md", "---\nrole: R\n---\nx\n")
    runs, ledgers, delivery, notices = MemoryRuns(clock, tmp_path), MemoryLedgerStore(), RecordingDelivery(clock, SequenceIdGenerator(clock)), RecordingNotices()
    task = Message(sender="root", to="ceo", type="task", title="T", body="g", id="20261018T100000000001-root-aaaa", created=clock.now().isoformat(), trace="tr")
    box.store(task)
    box.begin("ceo")
    box.end("ceo", True)
    runtime = wiring.open_runtime(tmp_path, {
        Clock: clock, AgentDirectory: box.agents, MailboxReader: box, TaskQuery: DerivedTaskQuery(box), MailFingerprint: box,
        PauseStore: MemoryPauseStore(events), RunLogReader: runs, OrgSettings: MemoryOrgSettings("---\nstall_after: 60\n---\n"),
        MessageDelivery: delivery, Notices: notices, EventSink: events, LedgerStore: ledgers,
    })
    clock.advance(60)
    assert runtime.stall_ladder.check() == [f"ceo: reminded about open task {task.id}"]
    assert [(m.to, m.title, m.body, m.trace) for m in delivery.messages] == [("ceo", "reminder: T", f"nudge: {task.id} | T", "tr")]
    assert [e.kind for e in events.events] == ["stall.nudge"] and "nudges" in ledgers.texts
    assert list(tmp_path.iterdir()) == []


def test_the_nudge_ledger_is_the_one_the_ladder_writes(tmp_path: Path) -> None:
    ledgers, clock, events = MemoryLedgerStore(), FakeClock(), ListEventSink()
    box = MemoryMailbox()
    box.agents.put("ceo/AGENT.md", "---\nrole: R\n---\nx\n")
    box.store(Message(sender="root", to="ceo", type="task", title="T", body="g", id="T-1", created=clock.now().isoformat()))
    box.begin("ceo")
    box.end("ceo", True)
    runtime = wiring.open_runtime(tmp_path, {
        Clock: clock, AgentDirectory: box.agents, MailboxReader: box, TaskQuery: DerivedTaskQuery(box), MailFingerprint: box,
        PauseStore: MemoryPauseStore(events), RunLogReader: MemoryRuns(clock, tmp_path), OrgSettings: MemoryOrgSettings("---\n---\n"),
        MessageDelivery: RecordingDelivery(clock, SequenceIdGenerator(clock)), EventSink: events, LedgerStore: ledgers,
    })
    clock.advance(600)
    at = clock.time()  # (delivering the note moves the fake clock on by a microsecond)
    runtime.stall_ladder.check()
    assert runtime.nudge_ledger.entries() == {"T-1": {"step": 0, "at": at}}


# ------------------------------------------------------------------------------ the legacy scheduler's seam


def test_a_clock_made_of_a_function_follows_it() -> None:
    now = [1_800_000_000.0]
    clock = wire_stalls.CallableClock(lambda: now[0])
    assert isinstance(clock, Clock) and clock.time() == 1_800_000_000.0 and clock.now().timestamp() == 1_800_000_000.0
    now[0] += 5
    assert clock.time() == 1_800_000_005.0 and clock.now().timestamp() == 1_800_000_005.0


def test_the_runtime_ports_resolve_each_port_to_its_field(tmp_path: Path) -> None:
    runtime = wiring.open_runtime(tmp_path)
    ports = wire_stalls.RuntimePorts(runtime)
    assert ports.root == runtime.root
    assert ports.get(MailboxReader) is runtime.mailbox and ports.get(Clock) is runtime.clock and ports.get(EventSink) is runtime.events


@pytest.fixture
def org(tmp_path: Path) -> Org:
    made = Org.init(tmp_path / "org", "mission")
    made.hire("root", "ceo", "Chief", "Run it.")
    return made


def test_the_scheduler_ladder_uses_the_clock_it_is_given(org: Org) -> None:
    task = org.delegate("root", "ceo", "T", "g", "a", budget=3)
    org.begin_run("ceo")
    org.end_run("ceo", ok=True)
    now = [time.time()]
    stalls = wire_stalls.RuntimeStalls(lambda: org.runtime, lambda: now[0])
    assert stalls.check() == []
    now[0] += 601
    assert stalls.check() == [f"ceo: reminded about open task {task.id}"]


def test_the_scheduler_ladder_follows_the_runtime_and_keeps_its_memo(org: Org) -> None:
    task = org.delegate("root", "ceo", "T", "g", "a", budget=3)
    org.begin_run("ceo")
    org.end_run("ceo", ok=True)
    stalls = wire_stalls.RuntimeStalls(lambda: org.runtime, time.time)
    assert [t.id for t in stalls.task_view("ceo", "open_tasks")] == [task.id]
    counting = CountingMessageParser()
    org.runtime = wiring.open_runtime(org.root, {MessageParser: counting})  # tests replace the runtime under a running scheduler
    for _ in range(3):
        stalls.task_view("ceo", "open_tasks")
    assert counting.loaded == []  # the mailbox did not change: what was remembered is still good
    org.report("ceo", task.id, "done", "ok")
    assert stalls.task_view("ceo", "open_tasks") == [] and counting.loaded  # a change is read through the ports of the runtime in force


def test_the_scheduler_ladder_asks_the_notices_of_the_runtime_in_force(org: Org) -> None:
    org.delegate("root", "ceo", "T", "g", "a", budget=3)
    org.begin_run("ceo")
    org.end_run("ceo", ok=True)
    notices = RecordingNotices()
    org.runtime = dataclasses.replace(org.runtime, notices=notices)
    now = [time.time() + 601]
    wire_stalls.RuntimeStalls(lambda: org.runtime, lambda: now[0]).check()
    assert [call[0] for call in notices.calls] == ["nudge"]
