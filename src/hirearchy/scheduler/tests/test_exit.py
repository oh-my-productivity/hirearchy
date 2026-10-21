"""When a serving scheduler stops by itself: idle, finished, or waiting on the user for longer than the grace period (by the cadence clock)."""

from __future__ import annotations

from pathlib import Path

from hirearchy.access.testing import StaticAccess
from hirearchy.attention import Waiting
from hirearchy.daemon import FINISHED
from hirearchy.daemon.testing import MemoryExitMarker
from hirearchy.kernel.testing import FakeClock
from hirearchy.scheduler._exit import GraceExitPolicy, GraceWait
from hirearchy.scheduler._run import GraceMemory, Standing, StopWhen
from hirearchy.scheduler.testing import RecordingConsole, ScriptedGrace, ScriptedWork

from ._support import ROOT_DIR

TEXT = 'waiting on you: "Rework the report" needs budget (ceo out of runs)'
STANDING = Standing({}, set())


def grace(config: str = "", waiting: Waiting | None = None) -> tuple[GraceWait, ScriptedWork, FakeClock, RecordingConsole, GraceMemory]:
    clock, console, memory, work = FakeClock(), RecordingConsole(), GraceMemory(), ScriptedWork(waiting=waiting)
    access = StaticAccess(ROOT_DIR, f"---\n{config}\n---\n# Organization\n" if config else "---\n---\n# Organization\n")
    return GraceWait(work, access.settings, clock, console, memory), work, clock, console, memory


def stuck() -> Waiting:
    return Waiting(TEXT, "Your options: send(...)")


def test_nothing_waiting_for_the_user_is_no_grace_and_starts_no_count() -> None:
    wait, _, _, console, memory = grace()
    assert wait.check(STANDING) == "" and memory.since is None and console.lines == []


def test_the_first_sight_starts_the_count_and_says_how_long() -> None:
    wait, _, clock, console, memory = grace(waiting=stuck())
    assert wait.check(STANDING) == "" and memory.since == clock.time()
    assert console.lines == [f"{TEXT}. Exiting in 300s unless something changes"]


def test_the_reason_comes_when_the_grace_period_has_passed_and_not_before() -> None:
    wait, _, clock, console, _ = grace(waiting=stuck())
    wait.check(STANDING)
    clock.advance(299)
    assert wait.check(STANDING) == ""
    clock.advance(1)
    assert wait.check(STANDING) == TEXT
    assert len(console.lines) == 1  # said once, at the first sight


def test_a_change_of_the_picture_starts_the_count_again() -> None:
    wait, work, clock, _, memory = grace(waiting=stuck())
    wait.check(STANDING)
    clock.advance(250)
    work.waiting_answer = None  # the user acted
    assert wait.check(STANDING) == "" and memory.since is None
    work.waiting_answer = stuck()
    clock.advance(100)
    assert wait.check(STANDING) == "" and memory.since is not None
    clock.advance(299)
    assert wait.check(STANDING) == ""
    clock.advance(2)
    assert wait.check(STANDING) == TEXT


def test_a_stall_the_ladder_may_still_wake_is_not_a_reason_to_exit() -> None:
    wait, _, clock, _, _ = grace(waiting=Waiting(TEXT, "o", settled=False))
    wait.check(STANDING)
    clock.advance(5000)
    assert wait.check(STANDING) == ""


def test_the_grace_period_is_a_setting() -> None:
    wait, _, clock, console, _ = grace("until_done_grace_seconds: 5", waiting=stuck())
    wait.check(STANDING)
    clock.advance(5)
    assert wait.check(STANDING) == TEXT and "Exiting in 5s" in console.lines[0]


def test_the_standing_is_passed_on_to_the_analysis() -> None:
    wait, work, _, _, _ = grace()
    wait.check(Standing({}, {"ceo"}, can_start=False))
    assert work.asked == [("waiting", frozenset(), frozenset({"ceo"}), False)]


# ------------------------------------------------------------------------------ the policy


def policy(finished: bool = False, *reasons: str) -> tuple[GraceExitPolicy, ScriptedWork, ScriptedGrace, MemoryExitMarker, RecordingConsole]:
    work, wait, marker, console = ScriptedWork(finished=finished), ScriptedGrace(*reasons), MemoryExitMarker(), RecordingConsole()
    return GraceExitPolicy(work, wait, marker, console), work, wait, marker, console


def test_a_scheduler_that_was_not_asked_to_stop_never_does_and_asks_nothing() -> None:
    exits, work, wait, marker, console = policy(True, TEXT)
    assert exits.after_tick(StopWhen(), False, STANDING) is None
    assert work.asked == [] and wait.asked == 0 and marker.text is None and console.lines == []


def test_until_idle_stops_when_nothing_is_active() -> None:
    exits, _, _, marker, console = policy()
    assert exits.after_tick(StopWhen(idle=True), True, STANDING) is None
    assert exits.after_tick(StopWhen(idle=True), False, STANDING) == "idle: nothing left to do"
    assert console.lines == ["organization is idle"] and marker.text is None  # the marker is for the exit of until-done


def test_until_done_stops_when_everything_is_finished_and_leaves_the_marker() -> None:
    exits, work, _, marker, console = policy(True)
    assert exits.after_tick(StopWhen(done=True), True, Standing({}, {"ops"}, can_start=False)) == FINISHED
    assert console.lines == [f"scheduler exiting: {FINISHED}"] and marker.read() == FINISHED
    assert work.asked == [("finished", frozenset(), frozenset({"ops"}), False)]


def test_until_done_stops_when_nothing_can_progress_without_the_user_and_leaves_the_reason() -> None:
    exits, _, wait, marker, console = policy(False, TEXT)
    assert exits.after_tick(StopWhen(done=True), True, STANDING) == TEXT
    assert console.lines == [f"scheduler exiting: {TEXT}"] and marker.read() == TEXT and wait.asked == 1


def test_until_done_goes_on_while_there_is_no_reason() -> None:
    exits, _, wait, marker, console = policy(False)
    assert exits.after_tick(StopWhen(done=True), True, STANDING) is None
    assert wait.asked == 1 and marker.text is None and console.lines == []


def test_idle_is_checked_before_finished_and_finished_before_waiting() -> None:
    exits, _, wait, _, _ = policy(True, TEXT)
    assert exits.after_tick(StopWhen(idle=True, done=True), False, STANDING) == "idle: nothing left to do"
    assert exits.after_tick(StopWhen(idle=True, done=True), True, STANDING) == FINISHED and wait.asked == 0
