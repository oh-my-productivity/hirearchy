"""The guard of the best-effort phases: a fault is said once per distinct error, recorded as an event at most each minute, and never stops the loop."""

from __future__ import annotations

from orgmcp.kernel.testing import FakeClock, ListEventSink
from orgmcp.scheduler._events import SchedulerEvents
from orgmcp.scheduler._guard import LoggingPhaseGuard
from orgmcp.scheduler._run import GuardMemory
from orgmcp.scheduler.testing import RecordingConsole


def make() -> tuple[LoggingPhaseGuard, RecordingConsole, ListEventSink, FakeClock, GuardMemory]:
    clock, console, sink, memory = FakeClock(), RecordingConsole(), ListEventSink(), GuardMemory()
    return LoggingPhaseGuard(console, SchedulerEvents(sink), clock, memory), console, sink, clock, memory


def fails(message: str):  # type: ignore[no-untyped-def]
    def fn() -> None:
        raise RuntimeError(message)

    return fn


def test_a_phase_that_works_is_run_and_says_nothing() -> None:
    guard, console, sink, _, _ = make()
    done: list[int] = []
    guard.guard("stall check", lambda: done.append(1))
    assert done == [1] and console.lines == [] and sink.events == []


def test_a_failing_phase_is_said_once_however_often_it_fails() -> None:
    guard, console, _, _, _ = make()
    for _ in range(3):
        guard.guard("stall check", fails("kaput"))
    assert console.lines == ["stall check failed (will retry next tick): RuntimeError: kaput"]


def test_another_error_of_the_same_phase_is_said_again() -> None:
    guard, console, _, _, _ = make()
    guard.guard("stall check", fails("one"))
    guard.guard("stall check", fails("two"))
    assert [line.rsplit(": ", 1)[-1] for line in console.lines] == ["one", "two"]


def test_the_same_error_after_the_phase_worked_is_said_again() -> None:
    guard, console, _, _, _ = make()
    guard.guard("stall check", fails("kaput"))
    guard.guard("stall check", lambda: None)
    guard.guard("stall check", fails("kaput"))
    assert len(console.lines) == 2


def test_each_phase_has_its_own_memory() -> None:
    guard, console, _, _, _ = make()
    guard.guard("stall check", fails("kaput"))
    guard.guard("health review", fails("kaput"))
    assert [line.split(" failed")[0] for line in console.lines] == ["stall check", "health review"]


def test_the_error_is_an_event_of_the_scheduler_and_a_persisting_one_is_recorded_every_minute() -> None:
    guard, _, sink, clock, _ = make()
    guard.guard("stall check", fails("kaput"))
    clock.advance(59)
    guard.guard("stall check", fails("kaput"))
    assert [e.kind for e in sink.events] == ["scheduler.error"]
    clock.advance(1)
    guard.guard("stall check", fails("kaput"))
    guard.guard("stall check", fails("other"))  # a changed error is recorded at once
    assert [e.fields["error"] for e in sink.events] == ["RuntimeError: kaput", "RuntimeError: kaput", "RuntimeError: other"]
    first = sink.events[0]
    assert (first.proc, first.actor, first.fields["phase"]) == ("scheduler", "runtime", "stall check")


def test_the_error_of_an_event_is_cut_at_five_hundred_characters() -> None:
    guard, _, sink, _, _ = make()
    guard.guard("stall check", fails("x" * 900))
    error = str(sink.events[0].fields["error"])
    assert len(error) == 500 and error.endswith("…")


def test_what_it_remembers_is_the_memory_it_is_given() -> None:
    guard, _, _, _, memory = make()
    guard.guard("stall check", fails("kaput"))
    assert memory.errors == {"stall check": "RuntimeError: kaput"} and list(memory.emitted) == ["stall check"]
    again = LoggingPhaseGuard(RecordingConsole(), SchedulerEvents(ListEventSink()), FakeClock(), memory)
    again.guard("stall check", fails("kaput"))  # a guard made again over the same memory goes on where the old one was
    assert again._console.lines == []  # type: ignore[attr-defined]
