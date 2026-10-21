"""The flags that say an agent needs somebody's attention: ``stuck``, ``out_of_budget``, ``paused`` - and the order of the flags.

Every threshold is pinned at its boundary: a value exactly at the limit is not flagged, one second past it is."""

from __future__ import annotations

from hirearchy.health import FLAGS
from hirearchy.health.testing import HealthWorld

from ._support import at, give, runs

ENG = "ceo/eng"


def flags(w: HealthWorld, now: float, addr: str = ENG) -> dict[str, str]:
    return w.analyzer.agent_health(addr, at(now)).flags


# ------------------------------------------------------------------------------------------------------------------------------ stuck


def test_an_open_task_is_stuck_after_the_threshold_not_at_it(w: HealthWorld) -> None:
    give(w, when=0)
    assert flags(w, 1800) == {}
    assert flags(w, 1801) == {"stuck": "open task is 30m old and nothing is in progress"}


def test_the_age_is_that_of_the_oldest_open_task(w: HealthWorld) -> None:
    give(w, when=0)
    give(w, when=1000)
    assert "stuck" in flags(w, 1801)


def test_it_is_not_stuck_while_something_is_in_progress(w: HealthWorld) -> None:
    give(w, when=0)
    w.send("root", ENG, "note", 2000)  # unread mail that wakes it: a run is coming
    assert "stuck" not in flags(w, 5000)


def test_it_is_not_stuck_while_a_run_is_going(w: HealthWorld) -> None:
    give(w, when=0)
    w.send("root", ENG, "note", 2000)
    w.start_run(ENG)
    assert "stuck" not in flags(w, 5000)


def test_it_is_not_stuck_while_it_waits_for_a_report_from_somebody_it_gave_work_to(w: HealthWorld) -> None:
    give(w, "ceo", when=0)
    assert "stuck" in flags(w, 5000, "ceo")
    w.send("ceo", ENG, "task", 100, budget=1)  # delegated, not yet answered
    assert "stuck" not in flags(w, 5000, "ceo")


def test_mail_that_does_not_wake_the_agent_is_not_in_progress(w: HealthWorld) -> None:
    give(w, when=0)
    w.send("root", ENG, "note", 2000, wake=False)
    assert "stuck" in flags(w, 5000)


# ---------------------------------------------------------------------------------------------------------------------- out_of_budget


def test_no_budget_and_unread_mail_is_out_of_budget(w: HealthWorld) -> None:
    w.set_budget(ENG, 0)
    w.send("root", ENG, "task", 10)
    assert flags(w, 100) == {"out_of_budget": "no budget left but has unread mail or open tasks"}


def test_no_budget_and_an_open_task_is_out_of_budget(w: HealthWorld) -> None:
    w.set_budget(ENG, 0)
    give(w, when=10)
    assert "out_of_budget" in flags(w, 100)


def test_no_budget_and_nothing_to_do_is_fine(w: HealthWorld) -> None:
    w.set_budget(ENG, 0)
    assert flags(w, 100) == {}


def test_budget_left_is_not_out_of_budget(w: HealthWorld) -> None:
    give(w, when=10)
    w.set_budget(ENG, 1)
    assert "out_of_budget" not in flags(w, 100)


def test_a_negative_budget_is_out_of_budget_too(w: HealthWorld) -> None:
    give(w, when=10)
    w.set_budget(ENG, -2)
    assert "out_of_budget" in flags(w, 100)


# -------------------------------------------------------------------------------------------------------------------------------- paused


def test_a_paused_agent_says_why(w: HealthWorld) -> None:
    w.pause(ENG, "failures")
    assert flags(w, 100) == {"paused": "paused: failures"}
    assert w.analyzer.agent_health(ENG, at(100)).state == "paused(failures)"


def test_an_empty_flag_file_still_pauses(w: HealthWorld) -> None:
    w.pause(ENG, "")
    assert flags(w, 100) == {"paused": "paused: paused"}


# -------------------------------------------------------------------------------------------------------------------------- the ranking


def test_the_flags_come_in_the_order_they_are_decided_and_the_worst_is_the_first_of_the_ranking(w: HealthWorld) -> None:
    give(w, when=0)
    w.pause(ENG, "by hand")
    w.set_budget(ENG, 0)
    runs(w, ENG, 7)
    h = w.analyzer.agent_health(ENG, at(100_000))
    assert list(h.flags) == ["stuck", "out_of_budget", "paused", "expensive", "wasteful"]
    assert h.worst_flag == "stuck" and h.worst_flag == next(f for f in FLAGS if f in h.flags)
