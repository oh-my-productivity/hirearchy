"""``regressions``: the human-tier rejections of a service, numbered ``R<k>`` by their note ids, with what each is about (pure; design 5.4)."""

from __future__ import annotations

from hirearchy.kernel import Message
from hirearchy.reflection import Case, Verdict, regressions


def stamp(n: int) -> str:
    return f"20260101T0000{n:02d}000000-root-{n:04d}"


def verdict(
    n: int, kind: str = "reject", *, tier: str = "human", links: tuple[str, ...] = (), links_tier: str = "", words: str = "",
) -> Verdict:
    """The verdict whose note has the id number ``n`` (so ids order like ``n``)."""
    note = Message(id=stamp(n), sender="root", to="ceo", type="note", body=words or f"words {n}", feedback=kind)
    return Verdict(kind, words or f"words {n}", None, "T", 0, note, tier=tier, links=links, links_tier=links_tier)


def case(name: str, *verdicts: Verdict) -> Case:
    task = Message(sender="root", to="ceo", type="task", body="b", title=name, id=name)
    return Case(
        id=name, service="s", owner="ceo", tasks=[task], result=None, state="done", playbook=0, used=0, reworks=0, budget=1, runs=1, lessons=[],
        verdicts=list(verdicts), started=None, finished=None,
    )


def test_r_ids_follow_the_note_ids_of_human_rejections_only() -> None:
    late, early, middle = verdict(9), verdict(2), verdict(5)
    accept = verdict(1, "accept")
    found = regressions([case("A", late), case("B", accept, early), case("C", middle)])
    assert [(a.id, a.case, a.verdict.message.id) for a in found] == [
        ("R1", "B", stamp(2)), ("R2", "C", stamp(5)), ("R3", "A", stamp(9)),
    ]
    assert found[0].verdict is early and found[2].verdict is late


def test_relayed_and_agent_rejections_are_not_assertions() -> None:
    cases = [case("A", verdict(1, tier="relayed")), case("B", verdict(2, tier="agent")), case("C", verdict(3), verdict(4, "accept"))]
    assert [(a.id, a.case) for a in regressions(cases)] == [("R1", "C")]
    assert regressions([case("A", verdict(1, tier="relayed"))]) == []


def test_a_reject_then_accept_case_keeps_its_assertion() -> None:
    final_accept = case("A", verdict(1), verdict(2, "accept"))
    other = case("B", verdict(3))
    assert [(a.id, a.case) for a in regressions([final_accept, other])] == [("R1", "A"), ("R2", "B")]


def test_two_rejections_of_one_case_are_two_assertions_with_the_same_case() -> None:
    assert [(a.id, a.case) for a in regressions([case("A", verdict(1), verdict(2))])] == [("R1", "A"), ("R2", "A")]


def test_about_resolves_the_same_as_rj_through_its_links() -> None:
    first = verdict(1, links=("C2", "C1"), links_tier="human")
    second = verdict(2, links=("R1",), links_tier="human")
    third = verdict(3, links=("R2", "C3"), links_tier="human")
    found = regressions([case("A", first), case("B", second), case("C", third)])
    assert [a.about for a in found] == [("C2", "C1"), ("C2", "C1"), ("C2", "C1", "C3")]


def test_a_same_as_link_to_an_assertion_that_is_about_nothing_stays_an_r_id() -> None:
    first = verdict(1)
    second = verdict(2, links=("R1",), links_tier="human")
    found = regressions([case("A", first), case("B", second)])
    assert [(a.about, a.link) for a in found] == [((), ""), (("R1",), "confirmed")]


def test_about_ignores_what_only_the_assistant_linked_and_what_is_not_an_assertion() -> None:
    first = verdict(1, links=("C1",), links_tier="relayed")
    second = verdict(2, links=("R1", "R9", "R2"), links_tier="human")
    found = regressions([case("A", first), case("B", second)])
    assert found[0].about == () and found[1].about == ("R1",)


def test_about_survives_a_cycle_of_r_links() -> None:
    first = verdict(1, links=("R2",), links_tier="human")
    second = verdict(2, links=("R1",), links_tier="human")
    selfie = verdict(3, links=("R3", "C4"), links_tier="human")
    found = regressions([case("A", first), case("B", second), case("C", selfie)])
    assert [a.about for a in found] == [("R2",), ("R1",), ("C4",)]


def test_link_is_confirmed_none_unconfirmed_or_empty() -> None:
    cases = [
        case("A", verdict(1, links=("C1",), links_tier="human")),
        case("B", verdict(2, links=("none",), links_tier="human")),
        case("C", verdict(3, links=("C1",), links_tier="relayed")),
        case("D", verdict(4, links=("none",), links_tier="relayed")),
        case("E", verdict(5)),
    ]
    found = regressions(cases)
    assert [a.link for a in found] == ["confirmed", "none", "unconfirmed", "unconfirmed", ""]
    assert [a.about for a in found] == [("C1",), (), (), (), ()]
