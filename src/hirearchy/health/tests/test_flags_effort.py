"""The flags about how an agent spends its runs and how its work turns out: ``low_quality``, ``expensive``, ``wasteful``.

Every threshold is pinned at its boundary. Runs that failed (crash, timeout, kiro missing) and runs woken only by runtime notes (stall reminders,
reviews, refunds) are not the agent's doing: they are counted (``failed_runs``, ``runtime_runs``) but left out of the cost and waste statistics."""

from __future__ import annotations

from hirearchy.health.testing import HealthWorld, org_md

from ._support import answer, at, give, runs

ENG = "ceo/eng"
FAILED = "# run of ceo/eng, 1 message(s)\n# senders: root\n\n# exit 1 after 3s\n"
TIMED_OUT = "# run of ceo/eng, 1 message(s)\n# senders: root\n\n# killed after 600s timeout\n\n# exit -9 after 600s\n"
RUNTIME_ONLY = "# run of ceo/eng, 1 message(s)\n# senders: runtime\n\n# exit 0 after 3s\n"


def flags(w: HealthWorld, now: float = 1000) -> dict[str, str]:
    return w.analyzer.agent_health(ENG, at(now)).flags


# ------------------------------------------------------------------------------------------------------------------------ low_quality


def test_low_quality_needs_more_than_half_of_at_least_three_tasks_to_go_wrong(w: HealthWorld) -> None:
    for i, status in enumerate(("failed", "blocked", "done")):
        answer(w, give(w, when=10 + i), status, 50 + i)
    assert flags(w) == {"low_quality": "2 of 3 tasks failed, blocked or were sent back"}


def test_one_task_in_three_going_wrong_is_not_enough(w: HealthWorld) -> None:
    for i, status in enumerate(("failed", "done", "done")):
        answer(w, give(w, when=10 + i), status, 50 + i)
    assert "low_quality" not in flags(w)


def test_exactly_half_is_not_more_than_half(w: HealthWorld) -> None:
    for i, status in enumerate(("failed", "failed", "done", "done")):
        answer(w, give(w, when=10 + i), status, 50 + i)
    assert "low_quality" not in flags(w)


def test_two_tasks_are_too_few_to_judge(w: HealthWorld) -> None:
    for i in range(2):
        answer(w, give(w, when=10 + i), "failed", 50 + i)
    assert "low_quality" not in flags(w)


def test_a_task_sent_back_by_its_manager_counts_as_a_problem(w: HealthWorld) -> None:
    first = give(w, when=10)
    answer(w, first, "done", 20)
    give(w, when=30, revises=first)
    answer(w, give(w, when=40), "failed", 50)
    h = w.analyzer.agent_health(ENG, at(1000))
    assert h.rework == 1 and h.client_rework == 0
    assert h.flags["low_quality"] == "2 of 3 tasks failed, blocked or were sent back"


def test_a_blocked_result_that_was_superseded_is_not_a_problem(w: HealthWorld) -> None:
    for i in range(3):
        task = give(w, when=10 + i)
        answer(w, task, "blocked", 20 + i)
        answer(w, task, "done", 30 + i)
    assert "low_quality" not in flags(w)


def test_the_thresholds_of_org_md_move_the_boundary(w: HealthWorld) -> None:
    for i, status in enumerate(("failed", "done", "done")):
        answer(w, give(w, when=10 + i), status, 50 + i)
    w.configure(org_md(max_problem_ratio=0.3))
    assert "low_quality" in flags(w)
    w.configure(org_md(min_tasks_for_quality=4, max_problem_ratio=0.3))
    assert "low_quality" not in flags(w)


# -------------------------------------------------------------------------------------------------------------------------- expensive


def test_runs_per_completed_task_over_the_limit_is_expensive(w: HealthWorld) -> None:
    answer(w, give(w), "done", 20)
    runs(w, ENG, 6)
    assert flags(w, 2000)["expensive"] == "6.0 runs per completed task (max 5)"


def test_runs_per_completed_task_at_the_limit_is_fine(w: HealthWorld) -> None:
    answer(w, give(w), "done", 20)
    runs(w, ENG, 5)
    assert "expensive" not in flags(w, 2000)


def test_runs_per_task_counts_every_result_not_only_the_done_ones(w: HealthWorld) -> None:
    answer(w, give(w, when=10), "done", 20)
    answer(w, give(w, when=11), "failed", 21)
    runs(w, ENG, 10)
    assert "expensive" not in flags(w, 2000)  # 10 runs / 2 results = 5.0
    runs(w, ENG, 1, first=2000)
    assert "expensive" in flags(w, 3000)


def test_runs_since_the_last_result_on_an_open_task_over_the_limit_are_expensive(w: HealthWorld) -> None:
    give(w, when=10)
    runs(w, ENG, 7)
    assert flags(w, 2000)["expensive"] == "7 runs without a result on an open task (max 6)"


def test_six_runs_without_a_result_are_fine(w: HealthWorld) -> None:
    give(w, when=10)
    runs(w, ENG, 6)
    assert "expensive" not in flags(w, 2000)


def test_only_runs_that_started_after_the_last_result_count(w: HealthWorld) -> None:
    answer(w, give(w, when=10), "done", 150)
    answer(w, give(w, when=11), "done", 160)
    runs(w, ENG, 7)  # starts 100 ... 700: six of them are after the last result (160), one is before it
    give(w, when=170)
    assert "expensive" not in flags(w, 2000)
    runs(w, ENG, 2, first=800)
    assert flags(w, 2000)["expensive"] == "8 runs without a result on an open task (max 6)"


def test_both_reasons_are_given_together(w: HealthWorld) -> None:
    answer(w, give(w, when=10), "done", 20)
    give(w, when=30)
    runs(w, ENG, 9, first=100)
    reason = flags(w, 3000)["expensive"]
    assert reason == "9.0 runs per completed task (max 5); 9 runs without a result on an open task (max 6)"


def test_failed_runs_are_not_charged_to_the_agent(w: HealthWorld) -> None:
    answer(w, give(w), "done", 20)
    runs(w, ENG, 5)
    runs(w, ENG, 3, first=1000, footer=FAILED)
    h = w.analyzer.agent_health(ENG, at(3000))
    assert h.runs_used == 8 and h.failed_runs == 3 and h.runs_per_task == 5.0 and "expensive" not in h.flags


def test_runs_that_only_handled_runtime_notes_are_not_charged_either(w: HealthWorld) -> None:
    answer(w, give(w), "done", 20)
    runs(w, ENG, 5)
    runs(w, ENG, 2, first=1000, footer=RUNTIME_ONLY)
    h = w.analyzer.agent_health(ENG, at(3000))
    assert h.runs_used == 7 and h.runtime_runs == 2 and h.failed_runs == 0 and h.runs_per_task == 5.0 and "expensive" not in h.flags


def test_a_run_that_failed_and_was_runtime_only_is_counted_as_failed(w: HealthWorld) -> None:
    runs(w, ENG, 1, footer="# run of ceo/eng, 1 message(s)\n# senders: runtime\n\n# exit 1 after 3s\n")
    h = w.analyzer.agent_health(ENG, at(3000))
    assert (h.failed_runs, h.runtime_runs) == (1, 0)


def test_runs_without_a_result_ignore_failed_and_runtime_only_runs(w: HealthWorld) -> None:
    give(w, when=10)
    runs(w, ENG, 6)
    runs(w, ENG, 2, first=1000, footer=TIMED_OUT)
    runs(w, ENG, 2, first=1500, footer=RUNTIME_ONLY)
    assert "expensive" not in flags(w, 3000)


# --------------------------------------------------------------------------------------------------------------------------- wasteful


def test_most_of_four_runs_sending_nothing_is_wasteful(w: HealthWorld) -> None:
    runs(w, ENG, 4)
    assert flags(w, 2000) == {"wasteful": "4 of 4 runs sent no message"}
    assert w.analyzer.agent_health(ENG, at(2000)).empty_runs == 4


def test_three_runs_are_too_few_to_judge(w: HealthWorld) -> None:
    runs(w, ENG, 3)
    assert "wasteful" not in flags(w, 2000)


def test_half_the_runs_sending_nothing_is_not_more_than_half(w: HealthWorld) -> None:
    runs(w, ENG, 4)
    w.send(ENG, "root", "note", 120)  # inside the first run (100..150)
    w.send(ENG, "root", "note", 220)  # inside the second (200..250)
    h = w.analyzer.agent_health(ENG, at(2000))
    assert h.empty_runs == 2 and "wasteful" not in h.flags


def test_three_of_four_runs_sending_nothing_is_wasteful(w: HealthWorld) -> None:
    runs(w, ENG, 4)
    w.send(ENG, "root", "note", 120)
    assert flags(w, 2000)["wasteful"] == "3 of 4 runs sent no message"


def test_a_message_sent_at_the_edge_of_a_run_belongs_to_it(w: HealthWorld) -> None:
    runs(w, ENG, 4)
    w.send(ENG, "root", "note", 100)  # the instant the first run began
    w.send(ENG, "root", "note", 250)  # the instant the second run's log was last written
    assert w.analyzer.agent_health(ENG, at(2000)).empty_runs == 2


def test_a_run_in_progress_is_not_empty_yet(w: HealthWorld) -> None:
    runs(w, ENG, 4)
    w.send("root", ENG, "task", 5000)
    w.start_run(ENG)
    h = w.analyzer.agent_health(ENG, at(6000))
    assert h.empty_runs == 3 and "wasteful" in h.flags  # the last log is the run in flight: judged runs are 4, empty ones 3


def test_failed_and_runtime_only_runs_are_neither_empty_nor_judged(w: HealthWorld) -> None:
    runs(w, ENG, 3)
    runs(w, ENG, 4, first=1000, footer=FAILED)
    runs(w, ENG, 4, first=2000, footer=RUNTIME_ONLY)
    h = w.analyzer.agent_health(ENG, at(4000))
    assert h.runs_used == 11 and h.empty_runs == 3 and "wasteful" not in h.flags


def test_the_limits_of_org_md_move_the_boundaries(w: HealthWorld) -> None:
    runs(w, ENG, 3)
    w.configure(org_md(min_runs_for_waste=3))
    assert "wasteful" in flags(w, 2000)
    w.configure(org_md(min_runs_for_waste=3, max_empty_run_ratio=1))
    assert "wasteful" not in flags(w, 2000)
