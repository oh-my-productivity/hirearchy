"""Escapes: the deliveries a team signed off that the client rejected after ``done`` (``MailEscapeCounter``, design 5.5).

The organization is ``root -> ceo`` (the owner of the service) ``-> ceo/eng`` (an author) and ``ceo/chk`` (a checker). Times are seconds after the
origin of the worlds; message ids start with their time, so a larger time is a later id. The numbers are read from ``AgentHealth``, over disk and
over memory."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from hirearchy.health import AgentHealth
from hirearchy.health.testing import HealthWorld

from ._support import at, runs

OWNER, AUTHOR, CHECKER = "ceo", "ceo/eng", "ceo/chk"
SERVICE = "weekly-brief"


@pytest.fixture
def e(w: HealthWorld) -> HealthWorld:
    w.agent(CHECKER, 0)
    w.set_budget(CHECKER, 10)
    return w


def health(w: HealthWorld, addr: str) -> AgentHealth:
    return w.analyzer.agent_health(addr, at(10_000))


def numbers(w: HealthWorld, addr: str) -> tuple[int, int, int, int]:
    h = health(w, addr)
    return (h.escapes, h.judged, h.rechecks, h.rework_runs)


@dataclass
class Delivery:
    request: str  # T
    done: str  # D
    author_task: str | None = None
    check_task: str | None = None


def request(w: HealthWorld, when: float, *, source: str | None = None, sender: str = "root", service: str | None = SERVICE, revises: str | None = None) -> str:
    task = w.send(sender, OWNER, "task", when, service=service, source=source, revises=revises)
    w.read(OWNER)
    return task.id


def deliver(w: HealthWorld, when: float, *, team: bool = True, source: str | None = None, check_first: bool = False) -> Delivery:
    """The owner gets a request at ``when``; with ``team`` its author drafts and its checker passes it; then it reports ``done`` (all within 9 s)."""
    t = request(w, when, source=source)
    author = check = None
    if team:
        author = w.send(OWNER, AUTHOR, "task", when + 1).id
        w.send(AUTHOR, OWNER, "result", when + 2, status="done", reply_to=author)
        check = w.send(OWNER, CHECKER, "task", when + 3).id
        w.send(CHECKER, OWNER, "result", when + 4, status="done", reply_to=check)
    d = w.send(OWNER, "root", "result", when + 6, status="done", reply_to=t).id
    return Delivery(t, d, author, check)


def verdict(w: HealthWorld, task_id: str, when: float, kind: str = "reject", *, source: str | None = "human", sender: str = "root") -> str:
    return w.send(sender, OWNER, "note", when, reply_to=task_id, feedback=kind, source=source).id


# ------------------------------------------------------------------------------------------------------------------------ the sign-off


def test_the_sign_off_is_the_last_report_done_before_the_owners_done(e: HealthWorld) -> None:
    d = deliver(e, 10)
    verdict(e, d.request, 30)
    assert numbers(e, CHECKER) == (1, 1, 0, 0)  # the checker passed the delivered version
    assert numbers(e, AUTHOR) == (0, 0, 0, 0)  # the author did not sign it off
    assert numbers(e, OWNER) == (1, 1, 0, 0)  # the owner reported done
    late = e.send(AUTHOR, OWNER, "result", 40, status="done", reply_to=d.author_task)  # a result after the owner's done signs nothing off
    assert late and numbers(e, AUTHOR) == (0, 0, 0, 0)


def test_a_report_that_is_not_done_signs_nothing_off(e: HealthWorld) -> None:
    t = request(e, 10)
    author = e.send(OWNER, AUTHOR, "task", 11).id
    e.send(AUTHOR, OWNER, "result", 12, status="done", reply_to=author)
    check = e.send(OWNER, CHECKER, "task", 13).id
    e.send(CHECKER, OWNER, "result", 14, status="failed", reply_to=check)  # not a done
    e.send(OWNER, "root", "result", 16, status="done", reply_to=t)
    verdict(e, t, 30)
    assert numbers(e, AUTHOR) == (1, 1, 0, 0) and numbers(e, CHECKER) == (0, 0, 0, 0)


def test_the_owner_signs_alone_without_a_report(e: HealthWorld) -> None:
    d = deliver(e, 10, team=False)
    verdict(e, d.request, 30)
    assert numbers(e, OWNER) == (1, 1, 0, 0)  # once, as the owner and as the sign-off
    assert numbers(e, AUTHOR) == numbers(e, CHECKER) == (0, 0, 0, 0)


def test_an_accepted_delivery_is_judged_and_not_an_escape(e: HealthWorld) -> None:
    d = deliver(e, 10)
    verdict(e, d.request, 30, "accept")
    assert numbers(e, CHECKER) == (0, 1, 0, 0) and numbers(e, OWNER) == (0, 1, 0, 0)


def test_a_delivery_without_a_verdict_is_not_judged(e: HealthWorld) -> None:
    deliver(e, 10)
    assert numbers(e, CHECKER) == numbers(e, OWNER) == (0, 0, 0, 0)


def test_a_task_that_is_not_done_is_not_a_delivery(e: HealthWorld) -> None:
    t = request(e, 10)
    e.send(OWNER, "root", "result", 16, status="failed", reply_to=t)
    verdict(e, t, 30)
    assert numbers(e, OWNER) == (0, 0, 0, 0)


def test_a_task_of_no_service_is_not_a_delivery(e: HealthWorld) -> None:
    t = request(e, 10, service=None)
    e.send(OWNER, "root", "result", 16, status="done", reply_to=t)
    verdict(e, t, 30)
    assert numbers(e, OWNER) == (0, 0, 0, 0)


# ------------------------------------------------------------------------------------------------------------------------ what is not judged


def test_a_relayed_rework_is_not_a_delivery(e: HealthWorld) -> None:
    d = deliver(e, 10, source="relayed")  # the assistant sent this rework on its own reading
    verdict(e, d.request, 30)
    assert numbers(e, OWNER) == numbers(e, CHECKER) == (0, 0, 0, 0)
    stamped = deliver(e, 100, source="human")  # the user asked for this one: a delivery
    verdict(e, stamped.request, 130)
    assert numbers(e, OWNER) == (1, 1, 0, 0)


def test_an_agent_clients_verdict_is_not_judged(e: HealthWorld) -> None:
    e.agent("ops", 0)
    e.set_budget("ops", 10)
    d = deliver(e, 10)
    verdict(e, d.request, 30, sender="ops", source=None)
    verdict(e, d.request, 31, sender="ops", source="human")  # an agent cannot claim a source
    assert numbers(e, OWNER) == numbers(e, CHECKER) == (0, 0, 0, 0)


def test_a_relayed_verdict_is_not_judged(e: HealthWorld) -> None:
    d = deliver(e, 10)
    verdict(e, d.request, 30, source="relayed")
    assert numbers(e, OWNER) == (0, 0, 0, 0)


def test_a_verdict_before_the_done_is_not_judged(e: HealthWorld) -> None:
    t = request(e, 10)
    verdict(e, t, 12)  # before the owner's done (a verdict on an earlier delivery of this task)
    e.send(OWNER, "root", "result", 16, status="done", reply_to=t)
    assert numbers(e, OWNER) == (0, 0, 0, 0)


def test_a_verdict_on_another_task_is_not_judged(e: HealthWorld) -> None:
    d = deliver(e, 10)
    other = deliver(e, 100)
    verdict(e, other.request, 130)
    assert d and numbers(e, OWNER) == (1, 1, 0, 0)


# ------------------------------------------------------------------------------------------------------------------------ escapes


def test_an_escape_counts_once_for_the_owner_and_once_for_the_sign_off(e: HealthWorld) -> None:
    d = deliver(e, 10)
    verdict(e, d.request, 30, "accept")
    verdict(e, d.request, 31, "reject")  # one of the human verdicts is a reject: an escape
    verdict(e, d.request, 32, "reject")  # ... however many there are
    assert numbers(e, OWNER) == (1, 1, 0, 0) and numbers(e, CHECKER) == (1, 1, 0, 0)
    assert numbers(e, AUTHOR) == (0, 0, 0, 0)


def test_a_legacy_root_reject_counts_as_human(e: HealthWorld) -> None:
    d = deliver(e, 10)
    verdict(e, d.request, 30, source=None)  # written before sources existed
    assert numbers(e, CHECKER) == (1, 1, 0, 0)


def test_the_top_level_agents_have_only_their_own_deliveries(e: HealthWorld) -> None:
    d = deliver(e, 10)
    verdict(e, d.request, 30)
    e.agent("ops", 0)
    assert numbers(e, "ops") == (0, 0, 0, 0)  # root is no owner


# ------------------------------------------------------------------------------------------------------------------------ re-checks and rework runs


def fail_and_recheck(w: HealthWorld, *, start: float = 100, first_check: str | None = None, sibling: bool = True, via: str | None = None) -> tuple[str, str, str]:
    """The checker passes (reports done) at ``start``; the owner sends the author a rework at ``start + 2`` and the checker a rework at ``start + 5``.
    Returns the ids of the checker's first task, of the author's rework and of the checker's rework."""
    c = w.send(OWNER, CHECKER, "task", start - 5).id
    w.read(CHECKER)
    w.send(CHECKER, OWNER, "result", start, status="done", reply_to=c)
    a = w.send(OWNER, AUTHOR, "task", start - 6).id
    fix = ""
    if sibling:
        fix = w.send(OWNER, AUTHOR, "task", start + 2, revises=a).id
        w.read(AUTHOR)
    again = w.send(OWNER, CHECKER, "task", start + 5, revises=c).id
    w.read(CHECKER)
    return c, fix, again


def test_rechecks_count_a_rework_of_a_done_check_with_a_sibling_author_rework(e: HealthWorld) -> None:
    fail_and_recheck(e)
    assert numbers(e, CHECKER) == (0, 0, 1, 0)
    assert numbers(e, AUTHOR) == (0, 0, 0, 0)


def test_a_recheck_without_a_sibling_rework_in_its_window_is_not_counted(e: HealthWorld) -> None:
    fail_and_recheck(e, sibling=False)
    assert numbers(e, CHECKER) == (0, 0, 0, 0)


def test_a_sibling_rework_before_the_check_was_done_is_outside_the_window(e: HealthWorld) -> None:
    c = e.send(OWNER, CHECKER, "task", 90).id
    a = e.send(OWNER, AUTHOR, "task", 91).id
    e.send(OWNER, AUTHOR, "task", 92, revises=a)  # before the checker's done
    e.send(CHECKER, OWNER, "result", 100, status="done", reply_to=c)
    e.send(OWNER, CHECKER, "task", 105, revises=c)
    assert numbers(e, CHECKER)[2] == 0


def test_client_driven_reworks_are_not_rechecks(e: HealthWorld) -> None:
    first = request(e, 10)
    e.send(OWNER, "root", "result", 20, status="done", reply_to=first)
    c = e.send(OWNER, CHECKER, "task", 90).id
    e.send(CHECKER, OWNER, "result", 95, status="done", reply_to=c)
    a = e.send(OWNER, AUTHOR, "task", 91).id
    request(e, 100, revises=first)  # the client sends the delivery back: the owner holds a client rework while it re-checks
    e.send(OWNER, AUTHOR, "task", 102, revises=a)
    e.send(OWNER, CHECKER, "task", 105, revises=c)
    assert numbers(e, CHECKER)[2] == 0


def test_an_author_sent_back_after_a_check_has_no_rechecks(e: HealthWorld) -> None:
    a = e.send(OWNER, AUTHOR, "task", 80).id
    e.send(AUTHOR, OWNER, "result", 90, status="done", reply_to=a)
    c = e.send(OWNER, CHECKER, "task", 91).id  # a fresh task for the checker, not a rework
    e.send(CHECKER, OWNER, "result", 95, status="failed", reply_to=c)
    e.send(OWNER, AUTHOR, "task", 100, revises=a)
    assert numbers(e, AUTHOR) == (0, 0, 0, 0) and numbers(e, CHECKER) == (0, 0, 0, 0)


def test_rework_runs_count_the_authors_run_windows_between_the_fail_and_the_recheck(e: HealthWorld) -> None:
    fail_and_recheck(e, start=1000)
    runs(e, AUTHOR, 1, first=500)  # before the checker's done
    e.run(AUTHOR, 1001, 1003, "")  # two runs of the author while the rework is being done
    e.run(AUTHOR, 1004, 1004.5, "")
    e.run(AUTHOR, 1010, 1011, "")  # after the recheck was sent
    e.run(CHECKER, 1002, 1003, "")  # not the author's: the checker's own run is no author rework run
    assert numbers(e, CHECKER) == (0, 0, 1, 2)
