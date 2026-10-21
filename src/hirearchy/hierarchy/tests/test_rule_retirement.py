"""``RuleRetirement`` against spies: in which order the team is failed, measured, archived, refunded and announced.

The contract suite (``test_contract_retirement.py``) pins what a caller sees; this file pins the order that keeps a crash from counting a refund
twice, and the injection of every collaborator (the clock, the notices, the budget)."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone

import pytest

from hirearchy.agents.testing import MemoryAgents
from hirearchy.budget.testing import FixedBudget
from hirearchy.delivery import MessageDelivery
from hirearchy.hierarchy import Retired, Retirement
from hirearchy.hierarchy._retirement import RuleRetirement
from hirearchy.kernel import RUNTIME, Message
from hirearchy.kernel.testing import FakeClock, ListEventSink
from hirearchy.mail import TaskQuery
from hirearchy.templates.testing import RecordingNotices

WORKER = "---\nrole: W\n---\n# Role\n"


class Log:
    """The order in which the spies were asked."""

    def __init__(self) -> None:
        self.entries: list[str] = []


class SpyFiles(MemoryAgents):
    def __init__(self, log: Log) -> None:
        super().__init__()
        self.log = log

    def archive(self, addr: str, stamp: str) -> str:
        self.log.entries.append(f"archive {addr} {stamp}")
        return super().archive(addr, stamp)


class SpyDelivery(MessageDelivery):
    def __init__(self, log: Log, fail_on: str = "") -> None:
        self.log = log
        self.fail_on = fail_on
        self.messages: list[Message] = []

    def deliver(self, msg: Message) -> Message:
        if msg.type == self.fail_on:
            raise OSError("disk full")
        self.log.entries.append(f"deliver {msg.type} {msg.sender}->{msg.to}")
        self.messages.append(msg)
        return msg

    def notify(self, to: str, title: str, body: str, wake: bool = True, trace: str | None = None) -> Message:
        raise AssertionError("retirement delivers messages of its own")


class SpyBudget(FixedBudget):
    def __init__(self, log: Log, tasks: TaskQuery, files: MemoryAgents) -> None:
        super().__init__(tasks, files, files)
        self.log = log

    def budget(self, addr: str) -> int | None:
        self.log.entries.append(f"budget {addr}")
        return super().budget(addr)


class Tasks(TaskQuery):
    def __init__(self, open_by_agent: Mapping[str, list[Message]]) -> None:
        self.open_by_agent = open_by_agent

    def open_tasks(self, addr: str) -> list[Message]:
        return list(self.open_by_agent.get(addr, []))

    def outstanding(self, addr: str) -> list[Message]:
        return []

    def blocked_tasks(self, addr: str) -> list[Message]:
        return []


class Rig:
    def __init__(self, open_by_agent: Mapping[str, list[Message]] | None = None, fail_on: str = "") -> None:
        self.log = Log()
        self.files = SpyFiles(self.log)
        for addr in ("ceo", "ceo/mgr", "ceo/mgr/w", "ceo/eng"):
            self.files.put(f"{addr}/AGENT.md", WORKER)
        self.delivery = SpyDelivery(self.log, fail_on)
        self.budget = SpyBudget(self.log, Tasks(open_by_agent or {}), self.files)
        self.budget.held.update({"ceo/mgr": 4, "ceo/mgr/w": 3})
        self.notices = RecordingNotices()
        self.events = ListEventSink()
        self.clock = FakeClock(datetime(2031, 1, 2, 3, 4, 5, tzinfo=timezone.utc))
        self.retirement: Retirement = RuleRetirement(
            self.files, self.files, Tasks(open_by_agent or {}), self.budget, self.delivery, self.notices, self.clock, self.events,
        )


def owed(task_id: str, sender: str, to: str) -> Message:
    return Message(sender=sender, to=to, type="task", title="T", body="b", id=task_id)


def test_the_budget_is_measured_before_the_move_and_the_refund_comes_after_it() -> None:
    rig = Rig()
    assert rig.retirement.retire_team("ceo", "mgr", "why") == Retired("ceo/mgr", 7, "ceo")
    entries = rig.log.entries
    assert sorted(entries[:2]) == ["budget ceo/mgr", "budget ceo/mgr/w"]
    assert entries[2:] == ["archive ceo/mgr 20310102T030405", "deliver note runtime->ceo"]


def test_the_open_tasks_are_failed_before_anything_is_measured() -> None:
    rig = Rig({"ceo/mgr": [owed("t1", "ceo", "ceo/mgr")]})
    rig.retirement.retire_team("ceo", "mgr", "why")
    assert rig.log.entries[0] == "deliver result ceo/mgr->ceo" and rig.log.entries[-1] == "deliver note runtime->ceo"
    assert rig.log.entries.index("archive ceo/mgr 20310102T030405") > rig.log.entries.index("budget ceo/mgr")


def test_a_crash_while_refunding_loses_the_refund_it_does_not_count_it_twice() -> None:
    rig = Rig(fail_on="note")
    with pytest.raises(OSError, match="disk full"):
        rig.retirement.retire_team("ceo", "mgr", "why")
    assert not rig.files.exists("ceo/mgr") and rig.events.events == []  # moved, not announced, not refunded
    assert [m for m in rig.delivery.messages if m.type == "note"] == []


def test_a_parent_that_is_root_is_never_asked_for_a_budget() -> None:
    rig = Rig()
    rig.files.put("lead/AGENT.md", WORKER)
    assert rig.retirement.retire_team("root", "lead", "why") == Retired("lead", 0, None)
    assert rig.log.entries == ["archive lead 20310102T030405"]


def test_a_refund_of_nothing_is_no_note() -> None:
    rig = Rig()
    assert rig.retirement.retire_team("ceo", "eng", "why") == Retired("ceo/eng", 0, None)
    assert [e for e in rig.log.entries if e.startswith("deliver")] == []


def test_the_note_is_written_by_the_notices_it_is_given() -> None:
    rig = Rig()
    rig.retirement.retire_team("ceo", "mgr", "why")
    (note,) = rig.delivery.messages
    assert rig.notices.calls == [("budget_returned", ("ceo/mgr", 7, "ceo", "why"))]
    assert (note.sender, note.to, note.type, note.budget, note.wake, note.title) == (RUNTIME, "ceo", "note", 7, False, "Budget returned from ceo/mgr")
    assert note.body == rig.notices.budget_returned("ceo/mgr", 7, "ceo", "why")


def test_the_archive_stamp_is_the_injected_clock_s() -> None:
    rig = Rig()
    rig.clock.advance(86400)
    rig.retirement.retire("ceo", "eng", "why")
    assert rig.log.entries == ["budget ceo/eng", "archive ceo/eng 20310103T030405"]


def test_a_task_the_team_owes_to_somebody_outside_is_failed_and_one_inside_is_not() -> None:
    outer, inner = owed("out", "ceo", "ceo/mgr"), owed("in", "ceo/mgr", "ceo/mgr/w")
    rig = Rig({"ceo/mgr": [outer], "ceo/mgr/w": [inner]})
    rig.retirement.retire_team("ceo", "mgr", "why")
    (failed,) = [m for m in rig.delivery.messages if m.type == "result"]
    assert (failed.sender, failed.to, failed.reply_to, failed.status, failed.title) == ("ceo/mgr", "ceo", "out", "failed", "T")


def test_a_task_from_an_agent_that_does_not_exist_is_not_answered() -> None:
    rig = Rig({"ceo/mgr": [owed("t", "ghost", "ceo/mgr")]})
    rig.retirement.retire_team("ceo", "mgr", "why")
    assert [m for m in rig.delivery.messages if m.type == "result"] == []


def test_the_event_is_the_last_thing_and_carries_the_whole_team_sorted() -> None:
    rig = Rig()
    rig.retirement.retire_team("ceo", "mgr", "why")
    (event,) = rig.events.events
    assert event.kind == "agent.retire" and rig.log.entries[-1] == "deliver note runtime->ceo"
    assert event.fields["team"] == ["ceo/mgr", "ceo/mgr/w"] and event.fields["returned_budget"] == 7
