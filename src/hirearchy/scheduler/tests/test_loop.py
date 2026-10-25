"""The heartbeat loop: the order of a pass, what ``serve`` does in each mode and how it ends, ``run_once``, and the loop over a world."""

from __future__ import annotations

import signal
from collections.abc import Callable, Iterator

import pytest

from hirearchy.attention import Waiting
from hirearchy.daemon import FINISHED
from hirearchy.kernel.testing import FakeClock
from hirearchy.processes.testing import FakeProcessTable
from hirearchy.review import Review
from hirearchy.review.testing import ScriptedHealthReviewer
from hirearchy.scheduler._loop import HeartbeatLoop, PollPacing
from hirearchy.scheduler._phases import GuardedPhase
from hirearchy.scheduler._ports import Lifecycle
from hirearchy.scheduler._run import LoopState, RunRecord, Standing, StopWhen
from hirearchy.scheduler.testing import (
    RecordingPacing, RecordingPhase, RecordingReaper, RecordingSession, RecordingStarter, ScriptedExit, ScriptedWork, build_heartbeat_world,
)
from hirearchy.settings import OrgSettings

from ._support import a_run


class Kit:
    def __init__(self, *reasons: str | None, remains: bool = False, finished: bool = False, waiting: Waiting | None = None) -> None:
        self.journal: list[str] = []
        self.session, self.starter, self.reaper = RecordingSession(self.journal), RecordingStarter(self.journal), RecordingReaper(self.journal)
        self.phases = [RecordingPhase("a", self.journal), RecordingPhase("b", self.journal)]
        self.work, self.exits, self.pacing, self.state = ScriptedWork(remains, finished, waiting), ScriptedExit(*reasons), RecordingPacing(self.journal), LoopState()
        self.loop = HeartbeatLoop(self.session, self.phases, Lifecycle(self.starter, self.reaper), self.work, self.exits, self.pacing, self.state)


@pytest.fixture
def sigterm() -> Iterator[None]:
    old = signal.getsignal(signal.SIGTERM)
    yield
    signal.signal(signal.SIGTERM, old)


def keeping(signum: signal.Signals, disposition: Callable[..., object] | int) -> Iterator[None]:
    found = signal.getsignal(signum)
    signal.signal(signum, disposition)
    yield
    signal.signal(signum, found if found is not None else signal.SIG_DFL)


@pytest.fixture
def sighup_default() -> Iterator[None]:
    """The SIGHUP disposition never comes from the runner (a runner under ``nohup`` starts with it ignored): default, and what was found back."""
    yield from keeping(signal.SIGHUP, signal.SIG_DFL)


@pytest.fixture
def sighup_ignored() -> Iterator[None]:
    yield from keeping(signal.SIGHUP, signal.SIG_IGN)


class SignallingPhase(RecordingPhase):
    """A phase that raises the signals it is given, one per pass, in the pass it runs in."""

    def __init__(self, name: str, journal: list[str], *signals: signal.Signals) -> None:
        super().__init__(name, journal)
        self.signals = list(signals)

    def run(self, standing: Standing, max_runs: int | None) -> None:
        super().run(standing, max_runs)
        if self.signals:
            signal.raise_signal(self.signals.pop(0))


def signalling(kit: Kit, a: tuple[signal.Signals, ...] = (), b: tuple[signal.Signals, ...] = ()) -> HeartbeatLoop:
    """The kit's loop with signals raised from its phases ``a`` and ``b``."""
    phases = [SignallingPhase("a", kit.journal, *a), SignallingPhase("b", kit.journal, *b)]
    return HeartbeatLoop(kit.session, phases, Lifecycle(kit.starter, kit.reaper), kit.work, kit.exits, kit.pacing, kit.state)


# ------------------------------------------------------------------------------ one pass


def test_a_pass_runs_the_phases_in_order_and_answers_whether_work_remains() -> None:
    kit = Kit(remains=True)
    assert kit.loop.tick(3) is True
    assert kit.journal == ["a", "b"] and [m for _, m in kit.phases[0].seen] == [3]
    assert kit.work.asked == [("remains", frozenset(), frozenset(), True)]
    kit.work.remains_answer = False
    assert kit.loop.tick() is False


def test_the_phases_see_the_runs_and_the_blocked_agents_the_loop_owns_and_the_cap() -> None:
    kit = Kit()
    kit.state.blocked.add("ops")
    kit.state.count.total = 2
    kit.loop.tick(2)
    standing = kit.phases[0].seen[0][0]
    assert standing.runs is kit.state.runs and standing.blocked is kit.state.blocked and standing.can_start is False
    kit.loop.tick(3)
    assert kit.phases[0].seen[1][0].can_start is True


def test_a_phase_that_raises_ends_the_pass_with_the_error() -> None:
    kit = Kit()
    kit.phases[0].fail = RuntimeError("kaput")
    with pytest.raises(RuntimeError, match="kaput"):
        kit.loop.tick()
    assert kit.journal == ["a"]


def test_the_phases_of_the_assembled_loop_are_these_in_this_order() -> None:
    names = [(p.name if isinstance(p, GuardedPhase) else type(p).__name__) for p in build_heartbeat_world().loop.phases]
    assert names == [
        "FailureLedgerRepair", "ReapPhase", "orphan check", "FundedResume", "RunLaunch", "stall check", "health review", "event log upkeep",
    ]


# ------------------------------------------------------------------------------ the questions


def test_finished_is_asked_of_the_work_with_the_cap() -> None:
    kit = Kit(finished=True)
    kit.state.count.total = 1
    assert kit.loop.finished(1) is True and kit.loop.finished() is True
    assert [(q, can) for q, _, _, can in kit.work.asked] == [("finished", False), ("finished", True)]


def test_waiting_on_the_user_is_asked_of_the_work() -> None:
    found = Waiting("waiting on you: x", "o")
    kit = Kit(waiting=found)
    assert kit.loop.waiting_on_user() is found and kit.work.asked[0][0] == "waiting"


# ------------------------------------------------------------------------------ acquire, release


def test_acquire_and_release_go_through_the_session_with_how_the_loop_runs() -> None:
    kit = Kit()
    kit.state.mode, kit.state.max_runs, kit.state.exit_reason = "once", 2, "once: one pass done"
    kit.state.count.total = 4
    kit.loop.acquire()
    kit.loop.release()
    assert kit.session.opened == [("once", 2)] and kit.session.closed == [("once: one pass done", 0, 4)]


def test_what_the_loop_owns_is_the_state_it_is_given() -> None:
    kit = Kit()
    assert kit.loop.state is kit.state


# ------------------------------------------------------------------------------ serve


def test_serve_passes_until_the_policy_gives_a_reason_and_pauses_between_the_passes() -> None:
    kit = Kit(None, None, "idle: nothing left to do", remains=True)
    kit.loop.serve(until_idle=True, max_runs=5)
    assert kit.journal == ["open", "a", "b", "pause", "a", "b", "pause", "a", "b", "close"]
    assert kit.session.opened == [("until_idle", 5)] and kit.session.closed == [("idle: nothing left to do", 0, 0)]
    assert kit.state.mode == "until_idle" and kit.state.max_runs == 5 and kit.state.exit_reason == "idle: nothing left to do"
    assert kit.exits.asked == [(StopWhen(idle=True), True)] * 3


@pytest.mark.parametrize(
    ("flags", "mode"), [({"until_done": True}, "until_done"), ({"until_idle": True}, "until_idle"), ({}, "daemon"), ({"until_done": True, "until_idle": True}, "until_done")],
)
def test_the_mode_names_how_it_was_asked_to_stop(flags: dict[str, bool], mode: str) -> None:
    kit = Kit(FINISHED)
    kit.loop.serve(**flags)
    assert kit.session.opened[0][0] == mode and kit.exits.asked[0][0] == StopWhen(flags.get("until_idle", False), flags.get("until_done", False))


def test_an_error_in_a_pass_is_the_exit_reason_and_goes_on_after_the_release() -> None:
    kit = Kit()
    kit.phases[1].fail = RuntimeError("boom")
    with pytest.raises(RuntimeError, match="boom"):
        kit.loop.serve()
    assert kit.session.closed == [("error: RuntimeError: boom", 0, 0)] and kit.journal[-1] == "close"


def test_an_interrupt_ends_the_loop_quietly_with_its_reason() -> None:
    kit = Kit()
    kit.phases[0].fail = KeyboardInterrupt()
    kit.loop.serve()
    assert kit.session.closed == [("interrupted (KeyboardInterrupt)", 0, 0)]


def test_sigterm_ends_the_loop_cleanly_after_the_pass_it_arrives_in(sigterm: None) -> None:
    kit = Kit()
    kit.pacing.on_pause = lambda: signal.raise_signal(signal.SIGTERM)
    kit.loop.serve()
    assert kit.session.closed == [("stopped by SIGTERM", 0, 0)] and kit.pacing.pauses == 1


# ------------------------------------------------------------------------------ scheduler.signal (C2, design 6.2, 6.4)


def test_a_sigterm_is_recorded_at_once_before_the_phase_after_the_one_it_arrives_in(sighup_default: None) -> None:
    """D-E6-3 C2: the record is written in the handler, so a KILL during the grace period of a stop still leaves it."""
    kit = Kit()
    signalling(kit, a=(signal.SIGTERM,)).serve()
    assert kit.journal == ["open", "a", "signal", "b", "pause", "close"]
    assert kit.session.signals == [("SIGTERM", "stop", [])] and kit.session.closed == [("stopped by SIGTERM", 0, 0)]


def test_a_sighup_stops_the_loop_the_same_way(sighup_default: None) -> None:
    kit = Kit()
    signalling(kit, a=(signal.SIGHUP,)).serve()
    assert kit.session.signals == [("SIGHUP", "stop", [])] and kit.session.closed == [("stopped by SIGHUP", 0, 0)]


def test_a_sighup_the_scheduler_was_started_ignoring_is_recorded_ignored_and_the_loop_goes_on(sighup_ignored: None) -> None:
    kit = Kit(None, "idle: nothing left to do")
    signalling(kit, a=(signal.SIGHUP,)).serve()
    assert kit.session.signals == [("SIGHUP", "ignored", [])]
    assert kit.session.closed == [("idle: nothing left to do", 0, 0)] and kit.pacing.pauses == 1


def test_two_signals_are_two_records_and_the_first_names_the_reason(sighup_default: None) -> None:
    kit = Kit()
    signalling(kit, a=(signal.SIGTERM,), b=(signal.SIGHUP,)).serve()
    assert kit.session.signals == [("SIGTERM", "stop", []), ("SIGHUP", "stop", [])]
    assert kit.session.closed == [("stopped by SIGTERM", 0, 0)]


def test_the_runs_in_flight_are_named_in_the_record(sighup_default: None) -> None:
    kit = Kit()
    table = FakeProcessTable()
    kit.state.runs["ops"] = a_run(table, FakeClock(), "ops")
    kit.state.runs["ceo"] = a_run(table, FakeClock(), "ceo")
    signalling(kit, a=(signal.SIGTERM,)).serve()
    (_, _, running) = kit.session.signals[0]
    assert running == sorted(r.run_id for r in kit.state.runs.values()) and len(running) == 2


def test_serve_leaves_the_sigterm_and_sighup_handlers_it_found(sighup_default: None, sigterm: None) -> None:
    kit = Kit(FINISHED)
    before = signal.getsignal(signal.SIGTERM), signal.getsignal(signal.SIGHUP)
    kit.loop.serve()
    assert (signal.getsignal(signal.SIGTERM), signal.getsignal(signal.SIGHUP)) == before


def test_a_record_that_raises_changes_nothing_and_the_loop_still_stops(sighup_default: None) -> None:
    kit = Kit()
    kit.session.fail_signal = RuntimeError("the event log is gone")
    signalling(kit, a=(signal.SIGTERM,)).serve()
    assert kit.session.closed == [("stopped by SIGTERM", 0, 0)]


def test_a_refused_open_is_not_closed() -> None:
    kit = Kit()
    kit.session.fail = RuntimeError("a scheduler is already running")
    with pytest.raises(RuntimeError, match="already running"):
        kit.loop.serve()
    assert kit.session.closed == [] and kit.journal == ["open"]


# ------------------------------------------------------------------------------ run_once


def test_run_once_makes_one_pass_waits_for_the_runs_and_releases() -> None:
    kit = Kit()
    clock = FakeClock()
    kit.state.runs["ceo"] = a_run(FakeProcessTable(clock), clock)
    reaps: list[int] = []

    def reap(runs: dict[str, RunRecord]) -> None:
        reaps.append(1)
        if len(reaps) == 2:
            runs.clear()

    kit.reaper.on_reap = reap
    kit.loop.run_once(max_runs=2)
    assert kit.journal == ["open", "a", "b", "pause", "reap", "pause", "reap", "close"]
    assert kit.session.opened == [("once", 2)] and kit.session.closed == [("once: one pass done", 0, 0)]


def test_run_once_releases_when_the_pass_fails() -> None:
    kit = Kit()
    kit.phases[0].fail = RuntimeError("boom")
    with pytest.raises(RuntimeError):
        kit.loop.run_once()
    assert kit.journal == ["open", "a", "close"]


def test_the_lifecycle_is_reached_through_the_loop() -> None:
    kit = Kit()
    kit.loop.reap()
    kit.loop.start("lead/an")
    assert kit.reaper.reaped == 1 and kit.starter.started == ["lead/an"]


# ------------------------------------------------------------------------------ pacing, and the loop over a world


def test_pacing_waits_poll_seconds_on_its_clock() -> None:
    w = build_heartbeat_world(config="poll_seconds: 7")
    before = w.life.clock.time()
    PollPacing(w.life.access.settings, w.life.clock).pause()
    assert w.life.clock.time() - before == 7


def test_the_assembled_loop_serves_until_done_and_leaves_what_a_finished_scheduler_leaves() -> None:
    w = build_heartbeat_world()
    life = w.life
    life.hire("ceo", 3)
    life.table.will_exit(0, after=5)
    task = life.mail_to("ceo")
    from hirearchy.kernel import Message

    life.box.store(Message(sender="ceo", to="root", type="result", title="re: t", body="ok", reply_to=task.id, status="done",
                           id="20260101T000099000000-ceo-aaaa", created="2026-01-01T00:00:00+00:00"))
    w.loop.serve(until_done=True)
    assert w.marker.read() == FINISHED and w.lock.text is None and w.label.get() == "scheduler" and w.life.count.total == 1
    kinds = [e.kind for e in life.events.events]
    assert kinds[0] == "scheduler.start" and kinds[-1] == "scheduler.exit" and "run.end" in kinds
    assert life.console.lines[-1] == f"scheduler exiting: {FINISHED}"


def test_a_failing_stall_check_or_review_is_said_once_each_and_the_runs_still_start() -> None:
    w = build_heartbeat_world()
    life = w.life
    life.hire("ceo", 3)
    life.mail_to("ceo")
    w.ladder.fail = RuntimeError("kaput")

    class Failing(ScriptedHealthReviewer):
        def review_if_due(self, now):  # type: ignore[no-untyped-def]
            raise RuntimeError("kaput")

    w.ports = w.ports.__class__(**{**w.ports.__dict__, "reviewer": Failing(Review(at=life.clock.now(), runs=0, flagged=0))})
    from hirearchy.scheduler._assembly import assemble_loop

    loop = assemble_loop(w.ports, life.clock, life.clock, life.console, w.state, w.memory)
    loop.tick()
    loop.tick()
    assert len([m for m in life.console.lines if "kaput" in m]) == 2 and life.count.total == 1
    assert [e.fields["phase"] for e in life.events.events if e.kind == "scheduler.error" and "kaput" in str(e.fields["error"])] == ["stall check", "health review"]
