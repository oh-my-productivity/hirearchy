"""Rework that comes from the client of a service case is not held against the agent: ``client_rework`` counts it apart from ``rework``.

A rework is a received task with ``revises``. It is the client's when it is a rework request of a service (``service`` set) of a task whose
result was ``done`` already, or when the manager that sent it was itself handling such a client rework (an open task) at the time. A rework in
answer to a failed, blocked or still open task is the manager's own quality control and counts."""

from __future__ import annotations

from orgmcp.health.testing import HealthWorld

from ._support import RED, answer, at, give

pytestmark = RED

ENG = "ceo/eng"


def counts(w: HealthWorld, addr: str, now: float = 1000) -> tuple[int, int]:
    h = w.analyzer.agent_health(addr, at(now))
    return h.rework, h.client_rework


def test_a_rework_request_of_a_service_after_a_delivery_is_the_clients(w: HealthWorld) -> None:
    memo = give(w, "ceo", service="memo")
    answer(w, memo, "done", 20, sender="ceo")
    give(w, "ceo", when=30, revises=memo, service="memo")
    assert counts(w, "ceo") == (0, 1)


def test_the_same_request_after_a_failure_is_the_managers_own_control(w: HealthWorld) -> None:
    memo = give(w, "ceo", service="memo")
    answer(w, memo, "failed", 20, sender="ceo")
    give(w, "ceo", when=30, revises=memo, service="memo")
    assert counts(w, "ceo") == (1, 0)


def test_the_same_request_while_the_task_is_still_open_is_the_managers_own_control(w: HealthWorld) -> None:
    memo = give(w, "ceo", service="memo")
    give(w, "ceo", when=30, revises=memo, service="memo")
    assert counts(w, "ceo") == (1, 0)


def test_a_rework_that_is_not_a_service_request_counts_even_after_a_delivery(w: HealthWorld) -> None:
    job = give(w, "ceo")
    answer(w, job, "done", 20, sender="ceo")
    give(w, "ceo", when=30, revises=job)
    assert counts(w, "ceo") == (1, 0)


def test_a_rework_a_manager_sends_its_team_while_it_holds_a_client_rework_is_a_consequence_of_it(w: HealthWorld) -> None:
    memo = give(w, "ceo", service="memo")
    first = give(w, ENG, when=15, sender="ceo")
    answer(w, first, "done", 18, sender=ENG, to="ceo")
    answer(w, memo, "done", 20, sender="ceo")
    client = give(w, "ceo", when=30, revises=memo, service="memo")  # the client sends the delivery back; ceo holds it open
    give(w, ENG, when=40, revises=first, sender="ceo")  # "check it again"
    assert counts(w, ENG) == (0, 1) and counts(w, "ceo") == (0, 1)
    assert client


def test_once_the_manager_has_answered_the_client_its_reworks_are_its_own_control_again(w: HealthWorld) -> None:
    memo = give(w, "ceo", service="memo")
    first = give(w, ENG, when=15, sender="ceo")
    answer(w, first, "done", 18, sender=ENG, to="ceo")
    answer(w, memo, "done", 20, sender="ceo")
    client = give(w, "ceo", when=30, revises=memo, service="memo")
    answer(w, client, "done", 35, sender="ceo")
    give(w, ENG, when=40, revises=first, sender="ceo")
    assert counts(w, ENG) == (1, 0)


def test_a_rework_the_manager_sent_before_it_held_the_client_rework_is_not_a_consequence(w: HealthWorld) -> None:
    memo = give(w, "ceo", service="memo")
    first = give(w, ENG, when=15, sender="ceo")
    answer(w, first, "done", 18, sender=ENG, to="ceo")
    give(w, ENG, when=19, revises=first, sender="ceo")  # sent before the client's rejection (created at 30)
    answer(w, memo, "done", 20, sender="ceo")
    give(w, "ceo", when=30, revises=memo, service="memo")
    assert counts(w, ENG) == (1, 0)


def test_a_rework_from_the_human_is_never_a_consequence(w: HealthWorld) -> None:
    first = give(w, ENG, when=15)
    give(w, ENG, when=40, revises=first)  # sender root
    assert counts(w, ENG) == (1, 0)


def test_a_rework_from_a_sender_that_no_longer_exists_counts(w: HealthWorld) -> None:
    first = give(w, ENG, when=15)
    w.send("gone", ENG, "task", 40, revises=first, budget=1)
    w.read(ENG)
    assert counts(w, ENG) == (1, 0)


def test_client_reworks_are_not_problems_for_low_quality(w: HealthWorld) -> None:
    for i in range(3):
        memo = give(w, "ceo", when=10 + i, service="memo")
        answer(w, memo, "done", 20 + i, sender="ceo")
        give(w, "ceo", when=30 + i, revises=memo, service="memo")
    h = w.analyzer.agent_health("ceo", at(1000))
    assert (h.rework, h.client_rework, h.tasks_received) == (0, 3, 6) and "low_quality" not in h.flags
