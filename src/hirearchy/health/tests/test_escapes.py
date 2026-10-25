"""Escapes: the numbers ``MailEscapeCounter`` makes of the signed deliveries it is given (design 5.5, 10), and the re-checks a FAIL cost.

The counter has no rule of its own about what a delivery is: ``SignedDeliveries`` says which deliveries an owner has, who signed them off, whether
the client judged them and, for an escape, its cause and whether that counts against a verifier. Those rules are ``reflection``'s (its tests) and
``app``'s conversion (its tests); here the counter is tested over ``FixedSignedDeliveries``. The re-check tests need messages: they run over the
worlds of ``testing.py`` (disk and memory), whose deliveries are ``MailSignedDeliveries``'s (the pre-0b rule kept as a fake, PC-3).

The organization is ``root -> ceo`` (the owner of the service) ``-> ceo/eng`` (an author) and ``ceo/chk`` (a checker). Times are seconds after the
origin of the worlds; message ids start with their time, so a larger time is a later id. The numbers are read from ``AgentHealth``, over disk and
over memory."""

from __future__ import annotations

from pathlib import Path

import pytest

from hirearchy.health import AgentHealth
from hirearchy.health._ports import EscapeCounts, SignedDelivery
from hirearchy.health.testing import HealthWorld, SignedWorld, fixed_signed_world

from ._support import AUTHOR, CHECKER, OWNER, at, request, runs

COUNTED = ("reviewer-miss", "untyped")  # the causes that count against a verifier (reflection.attribution)


@pytest.fixture
def e(w: HealthWorld) -> HealthWorld:
    w.agent(CHECKER, 0)
    w.set_budget(CHECKER, 10)
    return w


@pytest.fixture
def s(tmp_path: Path) -> SignedWorld:
    world = fixed_signed_world(tmp_path)
    for addr in (OWNER, AUTHOR, CHECKER, "ops"):
        world.agent(addr)
    return world


def health(w: HealthWorld, addr: str) -> AgentHealth:
    return w.analyzer.agent_health(addr, at(10_000))


def numbers(w: HealthWorld, addr: str) -> tuple[int, int, int, int]:
    h = health(w, addr)
    return (h.escapes, h.judged, h.rechecks, h.rework_runs)


def accepted(signer: str) -> SignedDelivery:
    """A delivery the client judged and accepted (no escape, no cause)."""
    return SignedDelivery(signer, True, False, True, "")


def escaped(signer: str, cause: str) -> SignedDelivery:
    """A judged delivery the client rejected, typed ``cause``."""
    return SignedDelivery(signer, True, True, cause in COUNTED, cause)


# ------------------------------------------------------------------------------------------------------------------------ the numbers


def test_counted_causes_are_escapes_and_the_others_are_not_its(s: SignedWorld) -> None:
    s.signed.put(
        OWNER, accepted(OWNER), escaped(OWNER, "reviewer-miss"), escaped(OWNER, "untyped"), escaped(OWNER, "relayed-carry-over"),
        escaped(OWNER, "contract-gap"), escaped(OWNER, "relayed-error"), escaped(OWNER, "contract-gap"),
    )
    counts = s.counter.counts(OWNER)
    assert (counts.escapes, counts.judged) == (2, 7)  # the not-its are judged deliveries, and no escape of the verifier
    assert counts.not_its == (("contract-gap", 2), ("relayed-error", 1), ("relayed-carry-over", 1))  # in the order of the view, whatever the input's
    assert (counts.rechecks, counts.rework_runs, counts.unknown) == (0, 0, "")


def test_a_cause_health_does_not_know_is_a_not_its_too_and_comes_last(s: SignedWorld) -> None:
    s.signed.put(OWNER, escaped(OWNER, "a-later-cause"), escaped(OWNER, "relayed-error"), escaped(OWNER, "another-cause"))
    assert s.counter.counts(OWNER).not_its == (("relayed-error", 1), ("a-later-cause", 1), ("another-cause", 1))


def test_an_accepted_relayed_rework_counts_as_judged(s: SignedWorld) -> None:
    """F-E3-10: the client's accept on a relayed rework is a judged delivery of its case (the rule is reflection's); the counter counts what it is given."""
    s.signed.put(OWNER, accepted(OWNER))
    assert s.counter.counts(OWNER) == EscapeCounts(0, 1, 0, 0)


def test_a_one_off_delivery_counts_as_judged(s: SignedWorld) -> None:
    """A task of root's without a service: its verdict names no criterion, so its escape is ``untyped``, which counts against the assignee."""
    s.signed.put(OWNER, escaped(OWNER, "untyped"))
    assert s.counter.counts(OWNER) == EscapeCounts(1, 1, 0, 0)


def test_reject_then_accept_stays_an_escape(s: SignedWorld) -> None:
    """A delivery the rule calls an escape (a counted reject, however many accepts follow) is one judged delivery and one escape."""
    s.signed.put(OWNER, escaped(OWNER, "untyped"))
    assert s.counter.counts(OWNER) == EscapeCounts(1, 1, 0, 0)
    s.signed.put(OWNER, SignedDelivery(OWNER, False, True, True, "untyped"))  # an escape flag on a delivery nobody judged counts for nothing
    assert s.counter.counts(OWNER) == EscapeCounts(0, 0, 0, 0)


def test_unknown_is_carried(s: SignedWorld) -> None:
    s.signed.put(OWNER, accepted(OWNER), unknown="weekly-brief: SERVICE.md: does not parse (ScannerError)")
    assert s.counter.counts(OWNER).unknown == "weekly-brief: SERVICE.md: does not parse (ScannerError)"
    assert s.counter.counts(CHECKER).unknown == "weekly-brief: SERVICE.md: does not parse (ScannerError)"  # the parent's services are read for a signer
    assert s.counter.counts("ops").unknown == ""
    s.signed.put(CHECKER, unknown="memo: the stored contract versions: is not UTF-8")
    assert s.counter.counts(CHECKER).unknown == "memo: the stored contract versions: is not UTF-8; weekly-brief: SERVICE.md: does not parse (ScannerError)"


def test_the_parent_composition_is_unchanged(s: SignedWorld) -> None:
    s.signed.put(OWNER, accepted(CHECKER), escaped(CHECKER, "reviewer-miss"), accepted(AUTHOR), accepted(OWNER), escaped(OWNER, "contract-gap"))
    s.signed.put(CHECKER, accepted(CHECKER))
    s.signed.put("ops", accepted("ops"))
    # the owner: its own deliveries, whoever signed them off (its parent is root, nobody's owner)
    assert s.counter.counts(OWNER) == EscapeCounts(1, 5, 0, 0, (("contract-gap", 1),), "")
    # a checker: its own deliveries, plus those of its parent that it signed off
    assert s.counter.counts(CHECKER) == EscapeCounts(1, 3, 0, 0)
    assert s.counter.counts(AUTHOR) == EscapeCounts(0, 1, 0, 0)  # only the one it signed off
    assert s.counter.counts("ops") == EscapeCounts(0, 1, 0, 0)  # a top-level agent has only its own


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
