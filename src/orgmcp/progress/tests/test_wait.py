"""``changes`` and ``PollingProgress``: what counts as a change between two looks, and the loop that looks until there is one."""

from __future__ import annotations

from datetime import datetime

import pytest

from orgmcp.kernel.testing import FakeClock
from orgmcp.progress._ports import ProgressText, ProgressView, Snapshot, Snapshots, TaskMark
from orgmcp.progress._wait import FINAL, POLL, PollingProgress, changes
from orgmcp.progress.api import WAIT_MAX
from orgmcp.progress.testing import ScriptedClock


def snap(kind: str = "working", state: str | None = None, needs: dict[str, str] | None = None, alive: bool = True, tid: str = "t") -> Snapshot:
    return Snapshot({tid: TaskMark(kind, "Title", state or kind)}, needs or {}, frozenset({tid} if alive else ()))


class ScriptedSnapshots(Snapshots):
    """The looks, one after the other; the last one stays."""

    def __init__(self, *looks: Snapshot) -> None:
        self.looks, self.taken = list(looks), 0

    def snapshot(self, task_id: str | None) -> Snapshot:
        found = self.looks[min(self.taken, len(self.looks) - 1)]
        self.taken += 1
        return found


class Lines(ProgressText):
    def render(self, task_id: str | None, now: datetime | None) -> str:
        return f"LINES({task_id})"


def waiter(*looks: Snapshot, poll: float = POLL) -> tuple[PollingProgress, ScriptedClock, ScriptedSnapshots]:
    clock = ScriptedClock(FakeClock())
    shots = ScriptedSnapshots(*looks)
    return PollingProgress(Lines(), shots, clock, poll), clock, shots


def test_the_constants() -> None:
    assert (POLL, WAIT_MAX, FINAL) == (2.0, 900, ("done", "failed", "blocked", "stalled"))


def test_it_is_a_progress_view() -> None:
    assert isinstance(waiter(snap())[0], ProgressView)


# ------------------------------------------------------------------------------------------------ changes


def test_nothing_differs_when_nothing_changed() -> None:
    assert changes(snap(), snap(), set()) == ([], set())


@pytest.mark.parametrize("kind", ["done", "failed", "blocked"])
def test_a_task_that_reached_a_final_state_is_reported_with_its_whole_state(kind: str) -> None:
    out, seen = changes(snap("working"), snap(kind, f"{kind}: reason"), set())
    assert out == [f'"Title": working -> {kind}: reason'] and seen == set()


def test_a_task_that_began_waiting_or_working_is_not_a_change() -> None:
    assert changes(snap("working"), snap("waiting", "waiting on x"), set()) == ([], set())
    assert changes(snap("stalled"), snap("working"), set()) == ([], set())


def test_a_stall_is_reported_when_the_next_look_confirms_it() -> None:
    first, seen = changes(snap("working"), snap("stalled", "stalled (x)"), set())
    assert first == [] and seen == {"t"}
    second, seen = changes(snap("working"), snap("stalled", "stalled (x)"), seen)
    assert second == ['"Title": working -> stalled (x)'] and seen == set()


def test_a_task_that_was_not_there_before_is_not_a_change() -> None:
    assert changes(Snapshot({}, {}, frozenset()), snap("done"), set()) == ([], set())


def test_a_new_item_for_the_user_is_reported_with_its_line() -> None:
    before, after = snap(needs={"m1": "one"}), snap(needs={"m1": "one", "m2": "two"})
    assert changes(before, after, set()) == (["new item for you: two"], set())


# ------------------------------------------------------------------------------------------------ the loop


def test_without_a_wait_it_is_the_text_and_nothing_is_looked_at() -> None:
    view, clock, shots = waiter(snap())
    for seconds in (0, -5):
        assert view.progress("t", wait_seconds=seconds) == "LINES(t)"
    assert shots.taken == 0 and clock.sleeps == 0


def test_a_wait_for_nothing_that_moves_returns_at_once() -> None:
    view, clock, _ = waiter(snap("done"))
    assert view.progress(wait_seconds=60) == "Nothing to wait for: no listed task is being worked on right now.\nLINES(None)" and clock.sleeps == 0


def test_a_wait_looks_every_poll_and_returns_the_change_with_the_time_waited() -> None:
    view, clock, _ = waiter(snap("working"), snap("working"), snap("working"), snap("done", "done"))
    assert view.progress(wait_seconds=60) == 'Changed after waiting 6s: "Title": working -> done\nLINES(None)' and clock.slept == [2.0, 2.0, 2.0]


def test_the_last_sleep_is_cut_to_the_time_that_is_left() -> None:
    view, clock, _ = waiter(snap(), poll=4.0)
    assert view.progress(wait_seconds=6).startswith("Waited 6s: no task finished, got blocked or stalled, and nothing new needs you. ")
    assert clock.slept == [4.0, 2.0]


def test_the_wait_is_capped_at_the_longest_honored() -> None:
    view, clock, _ = waiter(snap(), poll=300.0)
    assert view.progress(wait_seconds=5000).startswith("Waited 15m:") and sum(clock.slept) == WAIT_MAX


def test_the_wait_ends_when_nothing_can_run_for_two_looks_in_a_row() -> None:
    view, clock, _ = waiter(snap("blocked", alive=True), snap("blocked", alive=False), snap("blocked", alive=True), snap("blocked", alive=False), snap("blocked", alive=False))
    out = view.progress(wait_seconds=60)
    assert out == (
        "Stopped after waiting 8s: nothing in the org can run any more and no task finished. It needs a decision, budget or a restart (see below).\nLINES(None)"
    )
    assert clock.sleeps == 4  # the first idle look was followed by one that could run again: the count starts over


def test_a_stall_that_lasts_two_looks_is_a_change_not_a_stop() -> None:
    view, clock, _ = waiter(snap("working"), snap("stalled", "stalled (x)", alive=False))
    assert view.progress(wait_seconds=60) == 'Changed after waiting 4s: "Title": working -> stalled (x)\nLINES(None)' and clock.sleeps == 2


def test_the_time_comes_from_the_clock_and_the_loop_never_sleeps_for_real() -> None:
    view, clock, _ = waiter(snap())
    view.progress(wait_seconds=10)
    assert clock.monotonic() == 10.0
