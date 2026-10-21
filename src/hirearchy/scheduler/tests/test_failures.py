"""A failed run is counted; at ``max_failures`` in a row the agent is paused and its parent (and the human) told."""

from __future__ import annotations

from hirearchy.access.testing import StaticAccess
from hirearchy.delivery.testing import RecordingDelivery
from hirearchy.eligibility.testing import MemoryFailureCounter, MemoryPauseStore
from hirearchy.kernel import OrgPaths
from hirearchy.kernel.testing import FakeClock, ListEventSink, SequenceIdGenerator
from hirearchy.scheduler._failures import CountingFailures, PausingEscalation
from hirearchy.scheduler.testing import RecordingConsole
from hirearchy.templates.testing import RecordingNotices

from ._support import ROOT_DIR

LOG = ROOT_DIR / "ceo" / "eng" / "runs" / "20260101T000000000000.log"


class World:
    def __init__(self, max_failures: int = 2) -> None:
        clock = FakeClock()
        self.events, self.console, self.notices = ListEventSink(), RecordingConsole(), RecordingNotices()
        self.pauses, self.counter = MemoryPauseStore(self.events), MemoryFailureCounter()
        self.delivery = RecordingDelivery(clock, SequenceIdGenerator(clock))
        self.access = StaticAccess(ROOT_DIR, f"---\nmax_failures: {max_failures}\n---\n# Organization\n")
        escalation = PausingEscalation(self.pauses, self.delivery, self.notices, self.access.settings, OrgPaths(ROOT_DIR))
        self.failures = CountingFailures(self.counter, escalation, self.events, self.console)


def test_a_failure_is_counted_reported_and_does_not_pause_before_the_limit() -> None:
    w = World()
    w.failures.failed("ceo/eng", LOG, ("t1",))
    (event,) = w.events.events
    assert (event.kind, event.trace, event.fields) == ("agent.failure", "t1", {"agent": "ceo/eng", "count": 1})
    assert w.console.lines == [f"ceo/eng: run failed (1 in a row), log: {LOG}"]
    assert w.pauses.paused("ceo/eng") is None and w.delivery.messages == []


def test_at_the_limit_the_agent_is_paused_and_its_manager_and_the_human_are_told() -> None:
    w = World()
    w.failures.failed("ceo/eng", LOG, ("t1",))
    w.failures.failed("ceo/eng", LOG, ("t1",))
    assert w.pauses.paused("ceo/eng") == "failures"
    rel = "ceo/eng/runs/20260101T000000000000.log"
    assert [(m.to, m.title, m.trace) for m in w.delivery.messages] == [("ceo", "ceo/eng keeps failing", "t1"), ("root", "ceo/eng keeps failing", "t1")]
    assert [c for c in w.notices.calls if c[0] == "failures"] == [("failures", ("ceo/eng", 2, rel, False)), ("failures", ("ceo/eng", 2, rel, True))]


def test_the_parent_of_a_top_level_agent_is_the_human_and_is_told_once() -> None:
    w = World(max_failures=1)
    w.failures.failed("ceo", ROOT_DIR / "ceo" / "runs" / "x.log", ())
    assert [m.to for m in w.delivery.messages] == ["root"]
    assert w.notices.calls == [("failures", ("ceo", 1, "ceo/runs/x.log", True))]


def test_success_clears_the_count() -> None:
    w = World()
    w.failures.failed("ceo/eng", LOG, ())
    w.failures.cleared("ceo/eng")
    w.failures.failed("ceo/eng", LOG, ())
    assert w.pauses.paused("ceo/eng") is None
