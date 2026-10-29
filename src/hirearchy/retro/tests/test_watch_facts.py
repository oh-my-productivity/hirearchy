# mypy: ignore-errors
"""D11's watch facts (design 4.3, 10.4; F-P1-5), read over a real organization: an item the watch retired, with its related rejections told apart as direct
ones and refinements, and the retire candidates of Phase 1 10 (a pure rule over the playbook and its watches)."""

from __future__ import annotations

from testkit.e2e_world import build_server
from testkit.reach.hirearchy.core import ROOT, Org
from testkit.services_world import call, confirmed_amendment, define, deliver, request

from hirearchy.retro._readings import d11_playbooks
from hirearchy.retro._views import WatchRetire
from hirearchy.retro._watch_facts import retire_candidates
from hirearchy.services import ItemWatch, Playbook, PlaybookItem

from .test_sources import sources_of

WEEK = "weekly-brief"
INITIALS = "Owners as initials only"  # the client's wording the planted rule carries (C3)
STEPS = "## Steps\n1. Search.\n2. Write.\n3. Check every claim."


def planted(org: Org) -> str:
    """The owner's v1 and a rule P4 that carries the client's confirmed C3. Returns C3."""
    org.revise_playbook("ceo", WEEK, "first", "first draft", [], text=STEPS)
    c3 = confirmed_amendment(org, INITIALS)
    org.revise_playbook("ceo", WEEK, "add", "the client's rule", [c3], kind="rule", then=INITIALS)
    return c3


def rejected(org: Org, topic: str):
    task = request(org, topic)
    deliver(org, "ceo", task)
    return task, org.feedback(ROOT, task.id, "reject", "No.", source="human")


def directly(org: Org, server, c3: str, topic: str) -> None:
    """A rejection about C3 itself: the user's link names it."""
    task, no = rejected(org, topic)
    call(server, "feedback", task_id=task.id, verdict="reject", note="Yes, it is about that.", source="human", criterion=[c3], confirms=no.id)


def refining(org: Org, server, about: str, topic: str, old: str, new: str) -> None:
    """A rejection that the user answers with a version that replaces ``old`` by ``new``: it is about the refinement, not about the criterion the rule carries."""
    task, no = rejected(org, topic)
    call(server, "define_service", owner="ceo", name=WEEK, remove_acceptance=[old], add_acceptance=[new], answers=no.id, about=about, words=f"No: {new}")


def retires(org: Org) -> tuple[WatchRetire, ...]:
    (playbook,) = [p for p in sources_of(org).read(None, None).playbooks if p.service == WEEK]
    return playbook.retires


def test_a_retire_by_two_direct_rejections_names_the_criterion_it_carries(org: Org) -> None:
    define(org)
    server = build_server(org, ROOT)
    c3 = planted(org)
    directly(org, server, c3, "one")
    assert retires(org) == ()  # R2 warns it; the watch has retired nothing yet
    directly(org, server, c3, "two")
    assert retires(org) == (WatchRetire("P4", 3, ("R2", "R3"), "C3"),)
    text = "\n".join(d11_playbooks(sources_of(org).read(None, None).playbooks, ()).details)
    assert "- weekly-brief: P4 retired by the watch in v3: R2, R3 rejected deliveries on C3 it carries." in text


def test_a_retire_by_two_refinements_names_the_answers_that_replaced_the_criterion(org: Org) -> None:
    define(org)
    server = build_server(org, ROOT)
    c3 = planted(org)
    refining(org, server, c3, "one", INITIALS, "Owners in full")  # C3 -> C4
    refining(org, server, "C4", "two", "Owners in full", "Owners with titles")  # C4 -> C5
    assert retires(org) == (WatchRetire("P4", 3, (), "C3", ("R2", "R3"), (("C3", "C4"), ("C4", "C5"))),)
    text = "\n".join(d11_playbooks(sources_of(org).read(None, None).playbooks, ()).details)
    assert (
        "- weekly-brief: P4 retired by the watch in v3 because a refinement of the criterion it carries was rejected (R2, R3: the answers replaced C3 with C4, C4 with C5); "
        "its wording is now only in the contract."
    ) in text


def test_a_retire_by_a_direct_rejection_and_a_refinement_has_both_clauses(org: Org) -> None:
    define(org)
    server = build_server(org, ROOT)
    c3 = planted(org)
    directly(org, server, c3, "one")
    refining(org, server, c3, "two", INITIALS, "Owners in full")
    assert retires(org) == (WatchRetire("P4", 3, ("R2",), "C3", ("R3",), (("C3", "C4"),)),)
    text = "\n".join(d11_playbooks(sources_of(org).read(None, None).playbooks, ()).details)
    assert "P4 retired by the watch in v3: R2 rejected deliveries on C3 it carries; and because a refinement of the criterion it carries was rejected (R3:" in text


def test_the_retire_candidates_are_the_new_items_whose_watch_rests_on_no_regression_assertion_oldest_first() -> None:
    def item(n: int) -> PlaybookItem:
        return PlaybookItem(f"P{n}", "rule", "", "t", "always")

    book = Playbook(version=4, items=(item(1), item(2), item(3), item(4)))
    versions = [Playbook(version=2, why={"P2": ("C1",), "P4": ("R1", "C1")}), Playbook(version=3, why={"P3": ("C2",), "P1": ("C9",)})]
    watches = [
        ItemWatch("P1", "rule", "new", 3), ItemWatch("P2", "rule", "new", 2), ItemWatch("P3", "rule", "new", 3, carried="P9"), ItemWatch("P4", "rule", "new", 2),
    ]
    assert retire_candidates(book, versions, watches) == ("P2", "P1")  # P3 continues another watch, P4 rests on R1
    assert retire_candidates(book, versions, [ItemWatch("P2", "rule", "warning", 2)]) == ()
    assert retire_candidates(Playbook(), [], []) == ()
