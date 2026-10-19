"""The upkeep of a running scheduler: the heartbeat every ``heartbeat_seconds`` and the pruning of old event-log days once a day, by the cadence clock."""

from __future__ import annotations

from pathlib import Path

import pytest

from orgmcp.access.testing import StaticAccess
from orgmcp.attention.testing import ListHumanQueue
from orgmcp.kernel.testing import FakeClock, ListEventSink
from orgmcp.scheduler import _upkeep
from orgmcp.scheduler._events import SchedulerEvents
from orgmcp.scheduler._run import RunRecord, Standing, UpkeepMemory
from orgmcp.scheduler._upkeep import HeartbeatUpkeep
from orgmcp.scheduler.testing import FixedRunnable, NullSink
from orgmcp.telemetry.testing import MemoryEventRetention

from ._support import ROOT_DIR, a_run


class Kit:
    def __init__(self, config: str = "") -> None:
        self.clock, self.sink, self.queue, self.runnable = FakeClock(), ListEventSink(), ListHumanQueue(), FixedRunnable("ops")
        self.retention = MemoryEventRetention(self.clock, days=["2020-01-01", self.clock.now().strftime("%Y-%m-%d")])
        self.memory = UpkeepMemory()
        access = StaticAccess(ROOT_DIR, f"---\n{config}\n---\n# Organization\n" if config else "---\n---\n# Organization\n")
        self.upkeep = HeartbeatUpkeep(self.clock, access.settings, SchedulerEvents(self.sink), self.retention, self.queue, self.runnable, self.memory)

    def run(self, runs: dict[str, RunRecord] | None = None, blocked: set[str] | None = None) -> None:
        self.upkeep.run(Standing(runs if runs is not None else {}, blocked if blocked is not None else set()), None)

    def kinds(self) -> list[str]:
        return [e.kind for e in self.sink.events]


def test_the_first_pass_sends_the_heartbeat_with_what_runs_what_could_and_what_waits_for_the_user() -> None:
    kit = Kit()
    kit.queue.entries = [("m1", "Needs you: a"), ("m2", "Needs you: b")]
    from orgmcp.processes.testing import FakeProcessTable

    table = FakeProcessTable(kit.clock)
    runs = {"b": a_run(table, kit.clock, "b"), "a": a_run(table, kit.clock, "a")}
    kit.run(runs, {"x"})
    (beat,) = [e for e in kit.sink.events if e.kind == "scheduler.heartbeat"]
    assert beat.fields == {"running": ["a@20260101T000000000000", "b@20260101T000000000000"], "runnable": 1, "waiting_on_you": 2}
    assert (beat.proc, beat.actor) == ("scheduler", "runtime")
    assert kit.runnable.asked == [frozenset({"a", "b", "x"})]  # the agents running or blocked are not runnable


def test_the_heartbeat_comes_again_only_after_heartbeat_seconds() -> None:
    kit = Kit("heartbeat_seconds: 60")
    kit.run()
    kit.clock.advance(59)
    kit.run()
    assert kit.kinds().count("scheduler.heartbeat") == 1
    kit.clock.advance(1)
    kit.run()
    assert kit.kinds().count("scheduler.heartbeat") == 2


def test_the_runnable_agents_are_not_counted_while_no_heartbeat_is_due() -> None:
    kit = Kit("heartbeat_seconds: 60")
    kit.run()
    kit.run()
    assert len(kit.runnable.asked) == 1


def test_old_days_of_the_event_log_are_pruned_once_a_day_and_said() -> None:
    kit = Kit("events_keep_days: 7")
    kit.run()
    assert kit.retention.days == {kit.clock.now().strftime("%Y-%m-%d")}
    (pruned,) = [e for e in kit.sink.events if e.kind == "prune"]
    assert pruned.fields == {"removed_days": ["2020-01-01"]}
    kit.retention.days.add("2019-01-01")
    kit.clock.advance(86399)
    kit.run()
    assert "2019-01-01" in kit.retention.days  # not yet a day
    kit.clock.advance(1)
    kit.run()
    assert "2019-01-01" not in kit.retention.days and kit.kinds().count("prune") == 2


def test_nothing_pruned_is_no_event() -> None:
    kit = Kit()
    kit.retention.days.clear()
    kit.run()
    assert "prune" not in kit.kinds()


def test_what_it_remembers_is_the_memory_it_is_given() -> None:
    kit = Kit()
    kit.run()
    assert kit.memory.heartbeat_at is not None and kit.memory.pruned_at == kit.memory.heartbeat_at


def test_the_version_is_the_installed_one_or_unknown(monkeypatch: pytest.MonkeyPatch) -> None:
    assert _upkeep.package_version() not in ("", "unknown")

    def missing(name: str) -> str:
        raise ModuleNotFoundError(name)

    monkeypatch.setattr("importlib.metadata.version", missing)
    assert _upkeep.package_version() == "unknown"
