"""``MailSignedDeliveries``: the delivery rule health had before phase 0b, kept as the fake of health's own worlds (PC-3).

``MailEscapeCounter`` no longer derives deliveries from messages: ``SignedDeliveries`` gives them (``app`` converts ``reflection``'s). The suites of
``health`` that build their deliveries from messages without a contract (the flags, the analyzer's contract, the re-checks) need a rule that does not
read one, so ``testing.py`` keeps the old one as ``MailSignedDeliveries``: a task of a service whose latest result is ``done``, a relayed rework
and a task of no service left out, a delivery judged by a human-tier verdict after that ``done``, every escape ``untyped`` and counted. These tests
pin the fake, over disk and over memory; the real rule is ``reflection``'s (``test_deliveries.py``) and ``app``'s conversion (``test_signed_deliveries.py``).

The organization is ``root -> ceo`` (the owner of the service) ``-> ceo/eng`` (an author) and ``ceo/chk`` (a checker)."""

from __future__ import annotations

import pytest

from hirearchy.health import AgentHealth
from hirearchy.health.testing import HealthWorld

from ._support import AUTHOR, CHECKER, OWNER, at, deliver, request, verdict


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


def test_a_relayed_rework_and_a_task_of_no_service_are_left_out_by_the_pre_0b_rule(e: HealthWorld) -> None:
    relayed = deliver(e, 10, source="relayed")  # the assistant sent this rework on its own reading
    verdict(e, relayed.request, 30)
    plain = request(e, 50, service=None)
    e.send(OWNER, "root", "result", 56, status="done", reply_to=plain)
    verdict(e, plain, 70)
    assert numbers(e, OWNER) == numbers(e, CHECKER) == (0, 0, 0, 0)
    stamped = deliver(e, 100, source="human")  # the user asked for this one: a delivery
    verdict(e, stamped.request, 130)
    assert numbers(e, OWNER) == (1, 1, 0, 0)


def test_the_fake_types_every_escape_untyped_and_counted_and_knows_nothing_unknown(e: HealthWorld) -> None:
    d = deliver(e, 10)
    verdict(e, d.request, 30)
    h = health(e, OWNER)
    assert (h.escapes, h.judged, h.not_its, h.causes_unknown) == (1, 1, {}, "")
